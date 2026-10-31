"""
Unit and integration tests for ARGUS Headless REST API endpoints.
Tests:
- GET /health
- POST /api/v1/risk/metrics
- POST /api/v1/optimize/hrp
- POST /api/v1/ledger/timetravel
"""

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Returns a test client for the FastAPI application."""
    return TestClient(app)


def test_health_endpoint(client):
    """Verifies that the /health endpoint returns valid system metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "10.0.0"
    assert "engine" in data
    assert isinstance(data["duckdb_available"], bool)
    assert "timestamp" in data


def test_risk_metrics_endpoint_success(client):
    """Verifies calculating Cornish-Fisher VaR/CVaR, Sharpe, and Volatility."""
    np.random.seed(42)
    # Generate 100 pseudo-random daily returns with slight negative skew
    returns = list(np.random.normal(0.0005, 0.012, 100))

    payload = {
        "returns": returns,
        "risk_free_rate": 0.0275,
        "confidence_levels": [0.95, 0.99]
    }
    response = client.post("/api/v1/risk/metrics", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check risk and return keys
    assert "var_historical" in data
    assert "cvar_historical" in data
    assert "var_parametric" in data
    assert "cvar_parametric" in data
    assert "var_cornish_fisher" in data
    assert "cvar_cornish_fisher" in data

    assert "sharpe_ratio" in data
    assert "sortino_ratio" in data
    assert "volatility_annual" in data
    assert data["volatility_annual"] > 0.0
    assert "max_drawdown" in data
    assert data["max_drawdown"] <= 0.0
    assert "skewness" in data
    assert "kurtosis" in data


def test_risk_metrics_validation_error(client):
    """Verifies that fewer than 2 return observations trigger a 422 error."""
    payload = {
        "returns": [0.01],  # Only 1 observation
        "risk_free_rate": 0.0275
    }
    response = client.post("/api/v1/risk/metrics", json=payload)
    assert response.status_code == 422


def test_hrp_optimization_endpoint_success(client):
    """Verifies Hierarchical Risk Parity allocation for multi-asset returns."""
    np.random.seed(123)
    n_days = 60
    r_aapl = np.random.normal(0.001, 0.015, n_days).tolist()
    r_msft = np.random.normal(0.0008, 0.014, n_days).tolist()
    r_bnd = np.random.normal(0.0002, 0.003, n_days).tolist()

    payload = {
        "asset_returns": {
            "AAPL": r_aapl,
            "MSFT": r_msft,
            "BND": r_bnd
        },
        "linkage_method": "single"
    }

    response = client.post("/api/v1/optimize/hrp", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "weights" in data
    weights = data["weights"]
    assert len(weights) == 3
    assert set(weights.keys()) == {"AAPL", "MSFT", "BND"}

    # Weights must sum to approximately 1.0
    total_weight = sum(weights.values())
    assert total_weight == pytest.approx(1.0, abs=1e-4)

    # Low-volatility bond should receive higher weight than high-vol equities in HRP
    assert weights["BND"] > weights["AAPL"]

    assert "expected_return_pct" in data
    assert "volatility_annual_pct" in data
    assert "sharpe_ratio" in data
    assert "sorted_assets" in data
    assert len(data["sorted_assets"]) == 3


def test_hrp_optimization_insufficient_assets(client):
    """Verifies that requesting HRP with only 1 asset triggers a 422 error."""
    payload = {
        "asset_returns": {
            "AAPL": [0.01, -0.02, 0.015, 0.004]
        },
        "linkage_method": "single"
    }
    response = client.post("/api/v1/optimize/hrp", json=payload)
    assert response.status_code == 422


def test_timetravel_endpoint_success(client):
    """Verifies bitemporal point-in-time reconstruction with Merkle seal."""
    payload = {
        "portfolio_id": "DEMO_FAMILY_OFFICE",
        "as_of_valid_time": "2026-03-31T23:59:59",
        "as_of_system_time": "9999-12-31T23:59:59",
        "seed_demo": True
    }

    response = client.post("/api/v1/ledger/timetravel", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["portfolio_id"] == "DEMO_FAMILY_OFFICE"
    assert "positions" in data
    assert len(data["positions"]) > 0

    first_pos = data["positions"][0]
    assert "ticker" in first_pos
    assert "total_shares" in first_pos
    assert "current_nav" in first_pos

    assert data["total_portfolio_nav"] > 0.0
    # Merkle root should be a 64-character hex string
    assert "merkle_root" in data
    assert len(data["merkle_root"]) == 64


def test_wealth_networth_endpoint_success(client):
    """Verifies that the wealth net worth endpoint returns consolidated metrics."""
    response = client.get("/api/v1/wealth/networth")
    assert response.status_code == 200
    data = response.json()
    assert "total_net_worth" in data
    assert "liquid_cash" in data
    assert "financial_investments" in data
    assert "solvency_ratio" in data


def test_unified_cross_asset_stress_endpoint(client):
    res = client.post(
        "/api/v1/stress/unified-cross-asset",
        json={
            "preset_key": "stagflation_2026",
            "wealth_snapshot": {"liquid_investments": 500000.0, "real_estate": 300000.0, "net_worth": 800000.0},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "evaluation" in data


def test_crypto_tax_report_endpoint(client):
    res = client.post(
        "/api/v1/tax/crypto-report",
        json={
            "tax_year": 2024,
            "positions": [
                {"ticker": "BTC-USD", "asset_class": "crypto", "current_value": 15000.0, "cost_basis": 10000.0}
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["tax_year"] == 2024


def test_cross_border_tax_comparison_endpoint(client):
    res = client.post(
        "/api/v1/tax/cross-border-comparison",
        json={
            "total_wealth_eur": 2000000.0,
            "annual_capital_gain_eur": 100000.0,
            "annual_foreign_income_eur": 50000.0,
            "estate_succession_eur": 2000000.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "comparison" in data
    assert "lowest_tax_jurisdiction" in data["comparison"]


def test_pension_deduction_optimizer_endpoint(client):
    res = client.post(
        "/api/v1/tax/pension-deduction-optimizer",
        json={
            "tax_year": 2025,
            "taxable_income_eur": 65000.0,
            "current_contributions_eur": 2000.0,
            "additional_voluntary_eur": 3164.57,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["tax_savings_irpef_eur"] > 0


def test_fiscal_reform_2026_endpoint(client):
    res = client.post(
        "/api/v1/tax/fiscal-reform-2026",
        json={
            "portfolio_value_eur": 500000.0,
            "unrealized_gains_eur": 50000.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "simulation" in data

def test_quadro_rw_ivafe_endpoint(client):
    res = client.post(
        "/api/v1/tax/quadro-rw-ivafe",
        json={
            "foreign_financial_assets_eur": 150000.0,
            "foreign_real_estate_eur": 300000.0,
            "foreign_crypto_eur": 25000.0,
            "days_held": 365,
            "tax_year": 2025,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ivafe_due_eur"] > 0
    assert data["ivie_due_eur"] > 0
    assert data["must_fill_quadro_rw"] is True


def test_history_730_endpoint(client):
    res = client.post(
        "/api/v1/tax/history-730",
        json={"portfolio_id": 1, "tax_year": 2024},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("success", "warning")
    assert "declarations" in data


def test_pension_glidepath_endpoint(client):
    res = client.post(
        "/api/v1/wealth/pension-glidepath",
        json={
            "current_age": 35,
            "retirement_age": 67,
            "current_pot_eur": 35000.0,
            "monthly_contribution_eur": 450.0,
            "target_retirement_pot_eur": 500000.0,
            "n_sims": 100,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "glidepath" in data or "trajectories" in data or "goal" in data or "success_probability" in data


def test_fire_simulation_endpoint(client):
    res = client.post(
        "/api/v1/wealth/fire-simulation",
        json={
            "net_worth_eur": 450000.0,
            "annual_spending_eur": 24000.0,
            "safe_withdrawal_rate_pct": 3.75,
            "expected_return_pct": 6.5,
            "inflation_pct": 2.0,
            "horizon_years": 25,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["fire_number_regular_eur"] > 0
    assert "fire_attained_pct" in data
    assert "coast_fire_target_eur" in data


def test_succession_plan_endpoint(client):
    res = client.post(
        "/api/v1/wealth/succession-plan",
        json={
            "family_members": [
                {"name": "Coniuge", "relation": "coniuge", "age": 55},
                {"name": "Figlio 1", "relation": "figlio", "age": 28},
                {"name": "Figlio 2", "relation": "figlio", "age": 24},
            ],
            "real_estate_val": 800000.0,
            "financial_val": 1200000.0,
            "business_val": 500000.0,
            "exempt_bonds_val": 200000.0,
            "life_insurance_val": 150000.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "strategies" in data
    assert "Regime Ordinario" in data["strategies"]
