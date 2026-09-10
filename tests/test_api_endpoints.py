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
    assert data["version"] == "8.4.0"
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
