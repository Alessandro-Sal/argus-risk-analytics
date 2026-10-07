# ============================================================
# tests/test_michaud_and_api_expansion.py
# ARGUS — Unit tests for Michaud Resampling & API Expansion
# ============================================================

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.compliance_gate import PreTradeComplianceConfig, PreTradeOrderRequest, PreTradeRiskGate
from core.macro_stress_engine import evaluate_macro_stress_scenario, get_standard_macro_scenarios
from core.michaud_resampling import compute_michaud_resampled_frontier


@pytest.fixture
def sample_returns():
    """Generates realistic daily returns for 4 assets over 252 days."""
    np.random.seed(42)
    tickers = ["AAPL", "MSFT", "BND", "GLD"]
    mean_daily = np.array([0.0008, 0.0007, 0.0001, 0.0003])
    cov_daily = np.array([
        [0.00040, 0.00025, 0.00001, 0.00005],
        [0.00025, 0.00038, 0.00002, 0.00004],
        [0.00001, 0.00002, 0.00008, 0.00001],
        [0.00005, 0.00004, 0.00001, 0.00020],
    ])
    ret_matrix = np.random.multivariate_normal(mean_daily, cov_daily, size=252)
    return pd.DataFrame(ret_matrix, columns=tickers)


def test_michaud_resampled_frontier_basic(sample_returns):
    """Verifies that Michaud resampling converges and produces valid probabilities."""
    res = compute_michaud_resampled_frontier(
        sample_returns,
        n_samples=30,
        n_frontier_points=12,
        seed=42,
        risk_free_rate=0.03,
    )

    assert "resampled_frontier" in res
    assert len(res["resampled_frontier"]) == 12
    assert res["n_assets"] == 4
    assert res["assets"] == ["AAPL", "MSFT", "BND", "GLD"]

    # Verifica che la somma dei pesi sia 1 per ogni punto della frontiera
    for pt in res["resampled_frontier"]:
        w_dict = pt["weights"]
        sum_w = sum(w_dict.values())
        assert pytest.approx(sum_w, rel=1e-3) == 1.0
        assert pt["expected_return_pct"] > -50.0
        assert pt["volatility_annual_pct"] > 0.0
        assert pt["effective_constituents"] >= 1.0


def test_michaud_msr_and_gmv(sample_returns):
    """Verifies Max Sharpe and Min Variance portfolio properties on the resampled curve."""
    res = compute_michaud_resampled_frontier(
        sample_returns,
        n_samples=25,
        n_frontier_points=10,
        seed=42,
    )

    msr = res["resampled_max_sharpe"]
    gmv = res["resampled_min_var"]

    assert msr["sharpe_ratio"] >= gmv["sharpe_ratio"]
    assert gmv["volatility_annual_pct"] <= msr["volatility_annual_pct"]
    assert sum(msr["weights"].values()) == pytest.approx(1.0, rel=1e-3)
    assert sum(gmv["weights"].values()) == pytest.approx(1.0, rel=1e-3)


def test_michaud_diversification_gain(sample_returns):
    """Verifies that Michaud reduces weight concentration (lower HHI, higher diversification)."""
    res = compute_michaud_resampled_frontier(
        sample_returns,
        n_samples=30,
        n_frontier_points=10,
        seed=42,
    )

    # In campioni reali, il ricampionamento attenua i picchi di concentrazione
    assert res["resampled_max_sharpe"]["effective_constituents"] >= 1.5
    assert not res["df_comparison"].empty


def test_michaud_input_validation():
    """Verifies error handling on empty or invalid return inputs."""
    with pytest.raises(ValueError):
        compute_michaud_resampled_frontier(pd.DataFrame())

    with pytest.raises(ValueError):
        compute_michaud_resampled_frontier(pd.DataFrame({"ONLY_ONE": [0.01, 0.02]}))


def test_api_pre_trade_compliance_endpoint():
    """Verifies POST /api/v1/compliance/pre-trade-check via FastAPI TestClient."""
    client = TestClient(app)
    payload = {
        "orders": [
            {
                "order_id": "ORD-001",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 100.0,
                "limit_price": 180.0,
                "market_price": 180.0,
            },
            {
                "order_id": "ORD-002",
                "symbol": "SANCTIONED_OIL",
                "side": "BUY",
                "quantity": 10.0,
                "limit_price": 50.0,
            },
        ],
        "current_cash": 50000.0,
        "max_order_value_eur": 500000.0,
        "restricted_symbols": ["SANCTIONED_OIL"],
    }
    response = client.post("/api/v1/compliance/pre-trade-check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "9.19.0"
    assert data["orders_evaluated"] == 2
    assert data["all_approved"] is False  # second order is sanctioned
    assert len(data["batch_audit_seal"]) == 64  # SHA-256


def test_api_macro_scenarios_2026_endpoint():
    """Verifies POST /api/v1/stress/macro-scenarios-2026 via FastAPI TestClient."""
    client = TestClient(app)
    payload = {
        "scenario_key": "Global_Tariff_War_2026",
        "positions": [
            {"symbol": "SPY", "current_value": 60000.0, "asset_class": "equity"},
            {"symbol": "BND", "current_value": 40000.0, "asset_class": "bonds"},
        ],
    }
    response = client.post("/api/v1/stress/macro-scenarios-2026", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "9.19.0"
    sc_eval = data["scenario_evaluation"]
    assert sc_eval["scenario_key"] == "Global_Tariff_War_2026"
    assert sc_eval["portfolio_return_pct"] < 0.0


def test_api_michaud_resampling_endpoint():
    """Verifies POST /api/v1/optimization/michaud-resampled via FastAPI TestClient."""
    client = TestClient(app)
    np.random.seed(123)
    ret_dict = {
        "A": np.random.normal(0.001, 0.02, 60).tolist(),
        "B": np.random.normal(0.0005, 0.01, 60).tolist(),
    }
    payload = {
        "returns": ret_dict,
        "n_samples": 20,
        "n_frontier_points": 8,
        "risk_free_rate": 0.02,
    }
    response = client.post("/api/v1/optimization/michaud-resampled", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "9.19.0"
    assert "resampled_max_sharpe" in data
    assert "resampled_frontier" in data


def test_api_cro_institutional_dossier_download():
    """Verifies GET /api/v1/reporting/cro-institutional-dossier produces a valid ZIP response."""
    client = TestClient(app)
    response = client.get("/api/v1/reporting/cro-institutional-dossier")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert len(response.content) > 1000  # ZIP file bytes
