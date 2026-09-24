"""
tests/test_v912_institutional_suite.py
ARGUS — Unit & Integration Test Suite for v9.12.0 Institutional Upgrades:
1. Barra-Style Structural Multi-Asset Risk Model (core/barra_risk_model.py)
2. Solvency II Standard Formula & SCR Engine (core/solvency2_engine.py)
3. DCC-GARCH Dynamic Conditional Correlation & Vine Copula (core/dcc_garch_engine.py)
4. Mock FIX 4.4 Engine & L2 Depth-of-Market Simulator (core/fix_engine.py)
5. Family Office Generational Wealth Succession Optimizer (core/wealth/succession_optimizer.py)
6. Event-Driven Risk Watchdog & Multi-Channel Notification Hub (core/watchdog/risk_watchdog.py)
7. Fast-API Headless REST API v9.12.0 Endpoints
"""

import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from api.main import create_app
from core.barra_risk_model import StructuralBarraRiskModel, compute_barra_structural_risk
from core.dcc_garch_engine import DCCGarchEngine, compute_dcc_garch_extreme_risk
from core.fix_engine import (
    TAG_CHECK_SUM,
    TAG_CL_ORD_ID,
    TAG_MSG_TYPE,
    DepthOfMarketSimulator,
    FIXMessage,
    compute_fix_checksum,
    execute_mock_fix_order,
)
from core.solvency2_engine import (
    Solvency2AssetPosition,
    Solvency2Engine,
    compute_solvency2_standard_formula,
)
from core.watchdog.risk_watchdog import (
    NotificationHub,
    RiskWatchdogService,
    evaluate_risk_appetite_framework,
)
from core.wealth.succession_optimizer import (
    ConsolidatedEstateInput,
    FamilyOfficeSuccessionOptimizer,
    FamilyProfileInput,
    compute_family_succession_optimization,
)

# ============================================================
# 1. Barra Structural Multi-Asset Risk Model Tests
# ============================================================


def test_barra_structural_risk_model_decomposition():
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=100, freq="B")
    tickers = ["AAPL", "MSFT", "BTP10Y", "XOM", "JNJ"]
    returns_df = pd.DataFrame(
        np.random.normal(0.0004, 0.015, (100, 5)),
        index=dates,
        columns=tickers,
    )

    model = StructuralBarraRiskModel()
    model.fit_from_returns(returns_df)

    assert model.structural_cov_df is not None
    assert model.loadings_df is not None
    assert model.structural_cov_df.shape == (5, 5)

    # Weights
    weights = {"AAPL": 0.25, "MSFT": 0.25, "BTP10Y": 0.20, "XOM": 0.15, "JNJ": 0.15}
    benchmark_weights = {"AAPL": 0.20, "MSFT": 0.20, "BTP10Y": 0.20, "XOM": 0.20, "JNJ": 0.20}

    res = model.decompose_risk(weights, benchmark_weights=benchmark_weights)

    # 1. Total variance == Factor variance + Specific variance
    var_tot = res.total_variance_annual
    var_fact = res.systematic_variance_annual
    var_spec = res.specific_variance_annual
    assert var_tot == pytest.approx(var_fact + var_spec, rel=1e-4)

    # 2. Contributions sum to 100%
    assert res.systematic_risk_pct + res.specific_risk_pct == pytest.approx(100.0, abs=1e-3)

    # 3. Euler Sum PCTR == 100%
    assert res.euler_sum_pctr == pytest.approx(100.0, abs=1e-3)

    # 4. Tracking Error is positive
    assert res.active_risk_tracking_error is not None
    assert res.active_risk_tracking_error > 0.0

    # 5. Functional wrapper test
    fn_res = compute_barra_structural_risk(returns_df, weights=weights)
    assert fn_res["volatility_total_annual"] > 0.0
    assert fn_res["euler_sum_pctr"] == pytest.approx(100.0, abs=1e-3)


# ============================================================
# 2. Solvency II Standard Formula & SCR Engine Tests
# ============================================================


def test_solvency2_standard_formula_scr():
    positions = [
        Solvency2AssetPosition("EQ1", "Allianz SE", "equity_type1", 1_000_000.0, "EUR", 0.0, 2),
        Solvency2AssetPosition("EQ2", "China Tech", "equity_type2", 500_000.0, "USD", 0.0, 3),
        Solvency2AssetPosition("BOND1", "Bund 10Y", "bond", 2_000_000.0, "EUR", 8.5, 0),
        Solvency2AssetPosition("BOND2", "Corporate BBB", "bond", 1_000_000.0, "EUR", 5.0, 3),
        Solvency2AssetPosition("PROP1", "Milano Office", "property", 800_000.0, "EUR", 0.0, 2),
        Solvency2AssetPosition("CASH1", "Depo BNP", "cash", 700_000.0, "EUR", 0.25, 1),
    ]

    engine = Solvency2Engine(symmetric_equity_adjustment=0.02)
    report = engine.compute_scr(
        positions=positions,
        eligible_own_funds=3_500_000.0,
        technical_provisions=2_000_000.0,
    )

    # Checks
    assert report.eligible_own_funds == 3_500_000.0
    assert report.scr_total > 0.0
    assert report.bscr > 0.0
    assert report.scr_market_total > 0.0

    # Sub-modules
    assert report.scr_market_submodules["equity"] > 0.0
    assert report.scr_market_submodules["property"] == pytest.approx(800_000.0 * 0.25, rel=1e-4)
    assert report.scr_market_submodules["spread"] > 0.0
    assert report.market_diversification_benefit > 0.0

    # Solvency Ratio
    expected_ratio = (3_500_000.0 / report.scr_total) * 100.0
    assert report.solvency_ratio_pct == pytest.approx(expected_ratio, rel=1e-4)
    assert report.solvency_health in ["OPTIMAL (>160%)", "ADEQUATE (100-160%)", "CRITICAL (<100%)"]

    # QRT compliance
    assert report.qrt_s25_01["template"] == "S.25.01.21"
    assert report.qrt_s26_01["template"] == "S.26.01.01"

    # Functional API
    fn_out = compute_solvency2_standard_formula(
        portfolio_assets=[{"name": "EQ", "asset_type": "equity_type1", "value": 500_000.0}],
        eligible_own_funds=1_000_000.0,
    )
    assert fn_out["scr_total"] > 0.0
    assert fn_out["solvency_ratio_pct"] > 100.0


# ============================================================
# 3. DCC-GARCH & Vine Copula Dynamic Tail Risk Tests
# ============================================================


def test_dcc_garch_and_vine_copula():
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=60, freq="B")
    ret_df = pd.DataFrame(
        {
            "ASSET1": np.random.normal(0.0005, 0.015, 60),
            "ASSET2": np.random.normal(0.0003, 0.012, 60),
            "ASSET3": np.random.normal(0.0002, 0.008, 60),
        },
        index=dates,
    )

    engine = DCCGarchEngine(n_mc_sims=1000)
    engine.fit(ret_df)

    assert engine.dcc_alpha >= 0.0
    assert engine.dcc_beta >= 0.0
    assert engine.dcc_alpha + engine.dcc_beta < 1.0

    res = engine.forecast_risk(weights={"ASSET1": 0.4, "ASSET2": 0.4, "ASSET3": 0.2})

    # Covariances and correlations
    assert res.forecast_correlation_t1.shape == (3, 3)
    assert np.allclose(np.diag(res.forecast_correlation_t1.values), 1.0)
    assert res.dynamic_var_99_t1 > 0.0
    assert res.dynamic_cvar_99_t1 >= res.dynamic_var_99_t1
    assert res.tail_dependence_lower >= 0.0

    # Functional API
    fn_dcc = compute_dcc_garch_extreme_risk(ret_df, n_mc_sims=500)
    assert fn_dcc["dynamic_var_99_t1"] > 0.0


# ============================================================
# 4. Mock FIX 4.4 Engine & L2 DOM Simulator Tests
# ============================================================


def test_mock_fix_engine_and_l2_dom():
    # 1. Test CheckSum
    raw_header = b"8=FIX.4.49=4235=A49=SENDER56=TARGET34=1"
    chk = compute_fix_checksum(raw_header)
    assert len(chk) == 3
    assert chk.isdigit()

    # 2. Test Message Encode/Decode
    msg = FIXMessage(msg_type="D")
    msg.set(TAG_CL_ORD_ID, "ORD-999")
    encoded = msg.encode(delimiter="|")
    assert "8=FIX.4.4|" in encoded
    assert "35=D|" in encoded
    assert "11=ORD-999|" in encoded
    assert f"{TAG_CHECK_SUM}=" in encoded

    decoded = FIXMessage.decode(encoded, delimiter="|")
    assert decoded.msg_type == "D"
    assert decoded.get(TAG_CL_ORD_ID) == "ORD-999"

    # 3. Test L2 DOM Simulator & Execution
    sim = DepthOfMarketSimulator(symbol="SWDA.MI", initial_mid=100.0, tick_size=0.01)
    book = sim.get_order_book()
    assert len(book.bids) == 10
    assert len(book.asks) == 10
    assert book.bids[0].price < book.asks[0].price

    # Market Buy that walks top 2 levels
    top_ask_vol = book.asks[0].volume
    order_qty = top_ask_vol + 200
    tca = sim.execute_order("CL-001", side="BUY", qty=order_qty, order_type="MARKET")

    assert tca.status == "FILLED"
    assert tca.filled_qty == order_qty
    assert tca.execution_vwap >= tca.arrival_price
    assert tca.implementation_shortfall_eur >= 0.0
    assert len(tca.execution_reports) >= 2  # New + at least one Fill

    # Functional API
    fn_fix = execute_mock_fix_order("CSPX.L", side="SELL", qty=500, mid_price=500.0)
    assert fn_fix["status"] == "FILLED"
    assert fn_fix["filled_qty"] == 500
    assert len(fn_fix["fix_raw_reports"]) >= 2


# ============================================================
# 5. Family Office Generational Succession Optimizer Tests
# ============================================================


def test_family_office_succession_optimizer():
    estate = ConsolidatedEstateInput(
        liquid_investments_eur=4_000_000.0,
        operating_business_equity_eur=8_000_000.0,
        real_estate_properties_eur=3_000_000.0,
        alternative_investments_eur=1_000_000.0,
    )
    family = FamilyProfileInput(num_children=2, has_spouse=True, annual_family_consumption_eur=100_000.0)

    optimizer = FamilyOfficeSuccessionOptimizer(n_mc_sims=300)
    report = optimizer.simulate(estate, family)

    assert report.initial_estate_total_eur == 16_000_000.0
    assert len(report.strategies) == 5
    assert "Regime Ordinario" in report.strategies
    assert "Holding Familiare (PEX & Patto di Famiglia)" in report.strategies

    ord_strat = report.strategies["Regime Ordinario"]
    holding_strat = report.strategies["Holding Familiare (PEX & Patto di Famiglia)"]
    hybrid_strat = report.strategies["Ottimizzazione Ibrida (Patto + PPLI + Trust)"]

    # Holding & Hybrid should have positive Tax Alpha vs Regime Ordinario
    assert holding_strat.tax_alpha_eur > 0.0
    assert hybrid_strat.tax_alpha_eur > 0.0
    assert hybrid_strat.protection_score > ord_strat.protection_score

    # Functional API
    fn_succ = compute_family_succession_optimization(
        liquid_investments_eur=2_000_000.0,
        operating_business_equity_eur=4_000_000.0,
        real_estate_properties_eur=1_000_000.0,
        alternative_investments_eur=0.0,
    )
    assert fn_succ["initial_estate_total_eur"] == 7_000_000.0
    assert len(fn_succ["summary_table"]) == 5


# ============================================================
# 6. Event-Driven Risk Watchdog & Notification Hub Tests
# ============================================================


def test_risk_watchdog_and_notification_hub():
    watchdog = RiskWatchdogService(mock_dispatch=True)

    # Portfolio metrics that violate VaR 99% and Solvency Ratio
    metrics = {
        "var_99_pct": 4.20,             # Limit is 3.50% -> BREACH
        "cvar_99_pct": 5.80,            # Limit is 5.00% -> BREACH
        "max_drawdown_pct": 13.50,       # Limit is 15.0% (warn at 12%) -> WARNING
        "solvency_ratio_pct": 95.0,      # Limit is 120% (ge) -> BREACH
        "max_single_asset_pct": 12.0,    # Normal
        "portfolio_beta": 1.10,          # Normal
    }

    eval_res = watchdog.evaluate_and_notify(
        metrics=metrics,
        channels=["telegram", "discord", "slack", "email"],
    )

    assert eval_res["total_alerts"] >= 3
    assert eval_res["breaches_count"] >= 2
    assert eval_res["warnings_count"] >= 1
    assert eval_res["dispatch_report"]["dispatched_count"] >= 12  # 3 alerts * 4 channels
    assert eval_res["dispatch_report"]["mock_mode"] is True

    # Test individual payload formats
    hub = NotificationHub(mock_dispatch=True)
    alert = eval_res["alerts"][0]
    from core.watchdog.risk_watchdog import RiskAlert
    alert_obj = RiskAlert(**alert)

    tg_payload = hub.format_telegram_payload(alert_obj)
    assert "<b>" in tg_payload["text"]
    assert tg_payload["parse_mode"] == "HTML"

    dc_payload = hub.format_discord_payload(alert_obj)
    assert "embeds" in dc_payload
    assert len(dc_payload["embeds"]) == 1

    slack_payload = hub.format_slack_payload(alert_obj)
    assert "attachments" in slack_payload

    # Functional API
    fn_wd = evaluate_risk_appetite_framework(metrics=metrics)
    assert fn_wd["total_alerts"] >= 3


# ============================================================
# 7. FastAPI v9.12.0 Endpoints Test
# ============================================================


def test_v912_rest_api_endpoints():
    app = create_app()
    client = TestClient(app)

    # Health check version
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["version"] == "9.12.0"

    # Barra Risk endpoint
    r_barra = client.post(
        "/api/v1/risk/barra",
        json={
            "returns": {
                "AAPL": [0.01, -0.02, 0.015, -0.005, 0.02] * 10,
                "MSFT": [0.008, -0.015, 0.012, -0.003, 0.018] * 10,
            }
        },
    )
    assert r_barra.status_code == 200
    assert "volatility_total_annual" in r_barra.json()

    # Solvency II SCR endpoint
    r_s2 = client.post(
        "/api/v1/risk/solvency2-scr",
        json={
            "positions": [
                {"name": "Equities", "asset_type": "equity_type1", "value": 1_000_000.0},
                {"name": "Bonds", "asset_type": "bond", "value": 2_000_000.0, "duration": 6.0},
            ],
            "eligible_own_funds": 2_000_000.0,
        },
    )
    assert r_s2.status_code == 200
    assert "solvency_ratio_pct" in r_s2.json()

    # FIX Order endpoint
    r_fix = client.post(
        "/api/v1/execution/fix/order",
        json={"symbol": "SWDA.MI", "side": "BUY", "qty": 500, "order_type": "MARKET"},
    )
    assert r_fix.status_code == 200
    assert r_fix.json()["status"] == "FILLED"

    # Succession Optimization endpoint
    r_succ = client.post(
        "/api/v1/wealth/succession-optimization",
        json={"liquid_investments_eur": 3_000_000.0, "operating_business_equity_eur": 5_000_000.0},
    )
    assert r_succ.status_code == 200
    assert "recommended_strategy" in r_succ.json()

    # Watchdog endpoint
    r_wd = client.post(
        "/api/v1/watchdog/check",
        json={"metrics": {"var_99_pct": 4.5, "solvency_ratio_pct": 80.0}},
    )
    assert r_wd.status_code == 200
    assert r_wd.json()["breaches_count"] >= 1

    # Watchdog alerts history
    r_wda = client.get("/api/v1/watchdog/alerts")
    assert r_wda.status_code == 200
    assert isinstance(r_wda.json(), list)
