"""
Tests for ARGUS v9.10.0:
- Spinu (2013) Convex Potential Risk Budgeting & Equal Risk Contribution
- EBA / BCE Regulatory Reverse Stress Testing (Mahalanobis Distance & Chi-squared Plausibility)
- Gatheral SVI Arbitrage-Free Volatility Surface & Durrleman Density Checks
- Institutional 2-Page Factsheet PDF Generator
- Headless FastAPI REST Endpoints
"""

import numpy as np
import pandas as pd
import pytest

from core.advanced_quant import (
    compute_equal_risk_contribution_portfolio,
    compute_risk_budgeting_portfolio,
    solve_spinu_risk_budgeting,
)
from core.macro_stress_engine import compute_reverse_stress_test
from core.pdf_generator import generate_institutional_portfolio_factsheet_pdf
from core.volatility_surface import (
    build_svi_volatility_surface,
    check_svi_butterfly_arbitrage,
    fit_svi_smile,
    raw_svi_total_variance,
)


@pytest.fixture
def synthetic_asset_returns() -> pd.DataFrame:
    """Creates synthetic return series for 3 assets."""
    np.random.seed(42)
    n_days = 250
    ret_spy = np.random.normal(0.0005, 0.012, n_days)
    ret_tlt = np.random.normal(0.0001, 0.006, n_days)
    ret_gld = np.random.normal(0.0003, 0.009, n_days)
    return pd.DataFrame({"SPY": ret_spy, "TLT": ret_tlt, "GLD": ret_gld})


# ============================================================
# 1. Spinu (2013) Convex Risk Budgeting & ERC Tests
# ============================================================

def test_spinu_convex_solver_convergence():
    """Verify Spinu solver converges and satisfies risk budget proportions."""
    cov = np.array([
        [0.04, 0.005, 0.01],
        [0.005, 0.02, 0.002],
        [0.01, 0.002, 0.03],
    ])
    w, success = solve_spinu_risk_budgeting(cov)
    assert success is True
    assert np.isclose(np.sum(w), 1.0)
    assert np.all(w > 0.0)
    assert w[1] > w[0]

    port_var = float(w.T @ cov @ w)
    rc = w * (cov @ w)
    rc_pct = rc / port_var
    assert np.allclose(rc_pct, 1.0 / 3.0, atol=1e-3)


def test_spinu_custom_risk_budgeting(synthetic_asset_returns):
    """Verify arbitrary risk budget allocation."""
    budgets = {"SPY": 0.60, "TLT": 0.20, "GLD": 0.20}
    res = compute_risk_budgeting_portfolio(synthetic_asset_returns, risk_budgets=budgets)

    assert res["success"] is True
    assert set(res["weights"].keys()) == {"SPY", "TLT", "GLD"}
    assert np.isclose(sum(res["weights"].values()), 1.0, atol=1e-3)

    rc_pct = res["risk_contributions_pct"]
    assert np.isclose(rc_pct["SPY"], 60.0, atol=5.0)
    assert np.isclose(rc_pct["TLT"], 20.0, atol=5.0)
    assert np.isclose(rc_pct["GLD"], 20.0, atol=5.0)


def test_erc_retrocompatibility(synthetic_asset_returns):
    """Verify compute_equal_risk_contribution_portfolio wrapper."""
    res = compute_equal_risk_contribution_portfolio(synthetic_asset_returns)
    assert res["success"] is True
    assert np.isclose(sum(res["weights"].values()), 1.0, atol=1e-3)
    for val in res["risk_contributions_pct"].values():
        assert np.isclose(val, 33.33, atol=2.0)


# ============================================================
# 2. Regulatory Reverse Stress Testing Tests
# ============================================================

def test_reverse_stress_testing_solver():
    """Verify minimum Mahalanobis distance solver and output structure."""
    df_pos = pd.DataFrame([
        {"ticker": "SWDA.MI", "current_value": 600000.0, "asset_class": "Equity"},
        {"ticker": "XEON.MI", "current_value": 300000.0, "asset_class": "Bond"},
        {"ticker": "GLD", "current_value": 100000.0, "asset_class": "Commodities"},
    ])

    res = compute_reverse_stress_test(
        target_loss_pct=15.0,
        df_positions=df_pos,
        portfolio_value=1_000_000.0,
    )

    assert res["target_loss_pct"] == 15.0
    assert res["target_loss_eur"] == 150000.0
    assert res["mahalanobis_distance"] > 0.0
    assert 0.0 <= res["p_value_chi2"] <= 1.0
    assert "plausibility_rating" in res
    assert "severity_badge" in res
    assert "shocks_by_factor" in res
    assert "equity_mkt" in res["shocks_by_factor"]
    assert "yield_10y" in res["shocks_by_factor"]
    assert res["shocks_by_factor"]["equity_mkt"] < 0.0

    assert "break_even_solutions" in res
    assert "pure_equity_crash_pct" in res["break_even_solutions"]
    assert res["break_even_solutions"]["pure_equity_crash_pct"] < 0.0


# ============================================================
# 3. Gatheral SVI Volatility Surface Tests
# ============================================================

def test_svi_raw_total_variance():
    """Test raw SVI total variance function."""
    k = np.array([-0.2, -0.1, 0.0, 0.1, 0.2])
    params = {"a": 0.04, "b": 0.1, "rho": -0.4, "m": 0.02, "sigma": 0.1}
    w = raw_svi_total_variance(k, **params)
    assert len(w) == 5
    assert np.all(w > 0.0)


def test_svi_durrleman_arbitrage_check():
    """Verify butterfly arbitrage detection (Durrleman condition g(k) >= 0)."""
    k = np.linspace(-0.5, 0.5, 50)
    params_good = {"a": 0.04, "b": 0.1, "rho": -0.3, "m": 0.0, "sigma": 0.1}
    is_arb_free, min_g = check_svi_butterfly_arbitrage(k, **params_good)
    assert is_arb_free is True
    assert min_g >= 0.0

    params_bad = {"a": -0.5, "b": 0.01, "rho": 0.0, "m": 0.0, "sigma": 0.1}
    is_arb_free_bad, _ = check_svi_butterfly_arbitrage(k, **params_bad)
    assert is_arb_free_bad is False


def test_svi_surface_builder():
    """Test full multi-expiry SVI surface calibration."""
    expiries = [0.25, 0.50, 1.0]
    strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
    market_vols = {
        0.25: [0.24, 0.21, 0.18, 0.16, 0.15],
        0.50: [0.23, 0.20, 0.18, 0.165, 0.155],
        1.0: [0.22, 0.20, 0.185, 0.17, 0.16],
    }

    surface = build_svi_volatility_surface(
        spot=100.0,
        r=0.045,
        base_atm_iv=0.18,
        expiries_months=[1.0, 3.0, 6.0, 12.0],
    )

    assert surface["spot"] == 100.0
    assert len(surface["svi_models"]) == 4
    for smile in surface["svi_models"].values():
        assert smile["is_arbitrage_free"] is True
        assert smile["r_squared"] >= 0.0
    assert surface["all_arbitrage_free"] is True


# ============================================================
# 4. Institutional 2-Page Factsheet PDF Generator Tests
# ============================================================

def test_generate_institutional_portfolio_factsheet_pdf():
    """Verify institutional factsheet PDF generation and byte size."""
    mock_risk_data = {
        "positions": pd.DataFrame([
            {"ticker": "SWDA.MI", "current_value": 300000.0, "unrealized_pnl": 25000.0, "asset_class": "Equity"},
            {"ticker": "XEON.MI", "current_value": 200000.0, "unrealized_pnl": 5000.0, "asset_class": "Bond"},
        ]),
        "metrics": {
            "market_risk": {
                "var_cf_95_pct": 1.55,
                "cvar_cf_95_pct": 2.30,
                "var_cf_99_pct": 2.80,
                "cvar_cf_99_pct": 3.90,
                "volatility_annual_pct": 10.5,
                "max_drawdown_pct": 7.2,
                "skewness": -0.20,
                "kurtosis": 1.50,
            },
            "returns": {
                "cagr_pct": 8.5,
                "sharpe_ratio": 1.15,
                "sortino_ratio": 1.55,
            },
        },
    }
    pdf_bytes = generate_institutional_portfolio_factsheet_pdf(
        portfolio_name="TEST_ALPHA_MANDATE",
        risk_data=mock_risk_data,
        base_currency="EUR",
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 8000


# ============================================================
# 5. Headless REST API Endpoints Tests
# ============================================================

def test_api_endpoints_via_testclient():
    """Verify all new REST endpoints via FastAPI TestClient."""
    from fastapi.testclient import TestClient

    from api.main import app

    if app is None:
        pytest.skip("FastAPI not installed")

    client = TestClient(app)

    # 1. Health check (version 9.10.0)
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "9.16.0"

    # 2. Risk Parity / ERC endpoint
    erc_payload = {
        "asset_returns": {
            "SPY": [0.01, -0.015, 0.008, 0.002, -0.005, 0.004, -0.002],
            "TLT": [-0.002, 0.005, -0.001, 0.003, 0.001, -0.001, 0.002],
            "GLD": [0.003, -0.002, 0.004, -0.001, 0.002, 0.001, -0.001],
        },
        "risk_budgets": {"SPY": 0.5, "TLT": 0.3, "GLD": 0.2},
    }
    erc_resp = client.post("/api/v1/optimize/erc", json=erc_payload)
    assert erc_resp.status_code == 200
    erc_data = erc_resp.json()
    assert "weights" in erc_data
    assert "SPY" in erc_data["weights"]
    assert erc_data["status"] == "optimal"

    # 3. Regulatory Reverse Stress Testing endpoint
    rev_payload = {
        "target_loss_pct": 12.5,
        "asset_weights": {"EQUITY": 0.70, "BONDS": 0.20, "COMMODITIES": 0.10},
        "portfolio_value": 500000.0,
    }
    rev_resp = client.post("/api/v1/risk/reverse-stress", json=rev_payload)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["target_loss_pct"] == 12.5
    assert rev_data["target_loss_eur"] == 62500.0
    assert "mahalanobis_distance" in rev_data
    assert "shocks_by_factor" in rev_data

    # 4. Fixed Income Analytics endpoint
    fi_payload = {
        "face_value": 100.0,
        "coupon_rate": 0.0385,
        "maturity_years": 10.0,
        "market_price": 98.50,
        "coupon_frequency": 2,
    }
    fi_resp = client.post("/api/v1/fixed-income/analytics", json=fi_payload)
    assert fi_resp.status_code == 200
    fi_data = fi_resp.json()
    assert "ytm_pct" in fi_data
    assert "modified_duration" in fi_data
    assert "convexity" in fi_data
    assert fi_data["modified_duration"] > 0.0

    # 5. Institutional Factsheet PDF Download endpoint
    pdf_resp = client.get("/api/v1/reports/factsheet?portfolio_name=TestMandate&total_value=250000")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 5000
