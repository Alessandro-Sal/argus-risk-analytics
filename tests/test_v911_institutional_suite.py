# ============================================================
# tests/test_v911_institutional_suite.py
# ARGUS — Unit & Integration Test Suite for v9.11.0 Institutional Upgrades
# ============================================================

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from core.mip_rebalancer import solve_mip_rebalance
from core.pdf_generator import generate_regulatory_stress_testing_dossier_pdf
from core.regime_allocation import compute_regime_conditional_allocation
from core.services.rebalancing_service import RebalancingService
from core.walk_forward_engine import run_walk_forward_backtest
from core.wealth.total_wealth_reverse_stress import compute_total_wealth_reverse_stress


@pytest.fixture
def synthetic_returns_df() -> pd.DataFrame:
    """Generates synthetic daily returns for 4 assets over 400 trading days."""
    np.random.seed(42)
    n_days = 400
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_days)]
    r_spy = np.random.normal(0.0005, 0.012, n_days)
    r_qqq = np.random.normal(0.0007, 0.016, n_days)
    r_tlt = np.random.normal(0.0001, 0.008, n_days)
    r_gld = np.random.normal(0.0003, 0.009, n_days)
    return pd.DataFrame(
        {"SPY": r_spy, "QQQ": r_qqq, "TLT": r_tlt, "GLD": r_gld},
        index=dates,
    )


# ── PILLAR 1: WALK-FORWARD MULTI-STRATEGY ROLLING ENGINE ─────────────

def test_walk_forward_backtest_execution(synthetic_returns_df):
    """Verifies walk-forward backtest across supported allocation strategies."""
    for strat in ["equal_weight", "hrp", "erc"]:
        res = run_walk_forward_backtest(
            returns_df=synthetic_returns_df,
            strategy_name=strat,
            train_window_days=150,
            test_window_days=50,
            rebalance_cost_bps=10.0,
            slippage_bps=5.0,
            bid_ask_bps=5.0,
        )
        assert "cumulative_returns" in res
        assert "drawdown_series" in res
        assert "summary_table" in res
        assert "params" in res
        assert len(res["rebalance_dates"]) > 0
        assert not res["summary_table"].empty
        assert res["params"]["total_friction_bps"] == 20.0
        # Check cumulative returns are valid floats
        assert not res["cumulative_returns"].isna().any().any()


# ── PILLAR 2: REGIME-CONDITIONAL ADAPTIVE ALLOCATION ─────────────────

def test_regime_conditional_allocation(synthetic_returns_df):
    """Verifies regime detection and adaptive risk budgeting under Bull/Crisis states."""
    # Automatic detection
    res_auto = compute_regime_conditional_allocation(synthetic_returns_df)
    assert res_auto["current_regime"] in ["Bull", "Neutral", "Crisis"]
    assert "regime_probabilities" in res_auto
    assert len(res_auto["adaptive_weights"]) == 4
    assert np.isclose(sum(res_auto["adaptive_weights"].values()), 1.0, atol=1e-2)

    # Forced Crisis Regime
    res_crisis = compute_regime_conditional_allocation(
        synthetic_returns_df,
        current_regime="Crisis",
        crisis_equity_haircut=0.50,
    )
    assert res_crisis["current_regime"] == "Crisis"
    # Defensive assets (TLT/GLD) should have increased weight relative to equities
    weights = res_crisis["adaptive_weights"]
    assert weights["TLT"] + weights["GLD"] > 0.30
    assert res_crisis["turnover"] >= 0.0


# ── PILLAR 3: TOTAL WEALTH REVERSE STRESS TESTING ────────────────────

def test_total_wealth_reverse_stress():
    """Verifies solvency ruin and net worth ruin optimization with Mahalanobis distance."""
    bs = {
        "liquid_assets": 500000.0,
        "real_estate": 1000000.0,
        "corporate_equity": 400000.0,
        "illiquid_assets": 100000.0,
        "total_liabilities": 600000.0,
    }

    # Solvency Target (Debt-to-Assets >= 60%)
    res_solv = compute_total_wealth_reverse_stress(bs, target_type="solvency", target_threshold=0.60)
    assert res_solv["target_type"] == "solvency"
    assert res_solv["mahalanobis_distance"] > 0.0
    assert res_solv["post_stress_balance_sheet"]["debt_to_assets_pct"] >= 59.9
    assert res_solv["most_vulnerable_factor"] in [
        "Corporate Equity", "Liquid Markets", "Real Estate", "Debito & Mutui", "Illiquid / Luxury"
    ]
    assert len(res_solv["recommendations"]) > 0

    # Net Worth Ruin Target (>= 50% loss)
    res_ruin = compute_total_wealth_reverse_stress(bs, target_type="ruin", target_threshold=0.50)
    assert res_ruin["target_type"] == "ruin"
    initial_nw = res_ruin["pre_stress_balance_sheet"]["net_worth_eur"]
    post_nw = res_ruin["post_stress_balance_sheet"]["net_worth_eur"]
    assert (initial_nw - post_nw) >= initial_nw * 0.49


# ── PILLAR 4: MIP CARDINALITY & LOT-SIZING REBALANCER ───────────────

def test_mip_rebalance_solver_and_service():
    """Verifies discrete lot sizing and cardinality constraints in MILP solver and service."""
    holdings = {"AAPL": 10.0, "MSFT": 5.0, "GOOGL": 2.0, "AMZN": 0.0}
    prices = {"AAPL": 150.0, "MSFT": 300.0, "GOOGL": 120.0, "AMZN": 130.0}
    target_w = {"AAPL": 0.40, "MSFT": 0.30, "GOOGL": 0.15, "AMZN": 0.15}

    # Max cardinality = 3, lot sizes
    res_mip = solve_mip_rebalance(
        current_holdings=holdings,
        current_prices=prices,
        target_weights=target_w,
        total_capital=5000.0,
        max_cardinality=3,
        lot_sizes={"AAPL": 2, "MSFT": 1, "GOOGL": 5, "AMZN": 5},
    )
    assert res_mip["status"] in ["OPTIMAL", "FEASIBLE"]
    assert res_mip["cardinality"] <= 3
    # Check AAPL is multiple of 2
    assert res_mip["optimal_shares"]["AAPL"] % 2 == 0
    # Check GOOGL and AMZN are multiples of 5
    assert res_mip["optimal_shares"]["GOOGL"] % 5 == 0
    assert res_mip["optimal_shares"]["AMZN"] % 5 == 0

    # Test integration in RebalancingService
    positions = [
        {"ticker": "AAPL", "shares": 10.0, "current_price": 150.0, "pmc": 140.0},
        {"ticker": "MSFT", "shares": 5.0, "current_price": 300.0, "pmc": 280.0},
    ]
    service_res = RebalancingService.execute_rebalance(
        positions=positions,
        target_weights={"AAPL": 0.60, "MSFT": 0.40},
        strategy="mip_cardinality",
        total_portfolio_value=3000.0,
    )
    assert service_res["strategy"] == "MIP Cardinality & Lot-Sizing"
    assert "mip_details" in service_res
    assert service_res["status"] == "COMPLETED"


# ── PILLAR 5: FASTAPI ASYNC JOB QUEUE & REST ENDPOINTS ───────────────

def test_fastapi_async_job_queue_and_endpoints(synthetic_returns_df):
    """Verifies background job submission, retrieval, and synchronous REST endpoints."""
    app = create_app()
    client = TestClient(app)

    # 1. Health check
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    # 2. Async Job Submission
    r_sub = client.post(
        "/api/v1/jobs/submit",
        json={"task_type": "test_echo", "payload": {"symbol": "BTC", "size": 1.5}},
    )
    assert r_sub.status_code == 200
    job_id = r_sub.json()["job_id"]
    assert r_sub.json()["status"] == "PENDING"

    # 3. Retrieve Job
    r_get = client.get(f"/api/v1/jobs/{job_id}")
    assert r_get.status_code == 200
    assert r_get.json()["job_id"] == job_id
    assert r_get.json()["status"] in ["PENDING", "RUNNING", "COMPLETED"]

    # 4. List Jobs
    r_list = client.get("/api/v1/jobs")
    assert r_list.status_code == 200
    assert any(j["job_id"] == job_id for j in r_list.json())

    # 5. REST: Reverse Stress
    r_rev = client.post(
        "/api/v1/risk/total-wealth-reverse-stress",
        json={"balance_sheet": {"liquid_assets": 600000.0, "total_liabilities": 300000.0}},
    )
    assert r_rev.status_code == 200
    assert "mahalanobis_distance" in r_rev.json()

    # 6. REST: MIP Rebalance
    r_mip = client.post(
        "/api/v1/rebalance/mip",
        json={
            "current_holdings": {"AAPL": 10.0, "MSFT": 5.0},
            "current_prices": {"AAPL": 150.0, "MSFT": 300.0},
            "target_weights": {"AAPL": 0.50, "MSFT": 0.50},
            "total_capital": 3000.0,
        },
    )
    assert r_mip.status_code == 200
    assert r_mip.json()["status"] in ["OPTIMAL", "FEASIBLE"]


# ── PILLAR 6: REGULATORY STRESS TESTING DOSSIER PDF (4 PAGES) ─────────

def test_regulatory_stress_testing_dossier_pdf():
    """Verifies generation of 4-page regulatory stress testing dossier PDF."""
    stress_data = {
        "portfolio_nav": 2000000.0,
        "worst_loss_pct": -26.50,
        "worst_loss_eur": 530000.0,
        "stressed_solvency_ratio_pct": 65.0,
        "reverse_stress": {
            "mahalanobis_distance": 3.92,
            "implied_probability_pct": 0.038,
            "return_period_years": 70,
            "factor_shocks": {
                "liquid_markets_pct": -45.0,
                "real_estate_pct": -20.0,
                "corporate_equity_pct": -65.0,
                "debt_liabilities_pct": 15.0,
                "illiquid_luxury_pct": -15.0,
            },
        },
    }
    pdf_bytes = generate_regulatory_stress_testing_dossier_pdf(
        portfolio_name="Institutional Sovereign Mandate",
        stress_data=stress_data,
        base_currency="EUR",
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000
