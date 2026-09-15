"""
tests/test_phase3_services_and_api.py
Automated test suite for ARGUS Phase 3:
1. RebalancingService application layer facade (autonomous, tax_aware, prescriptive, heuristic).
2. ArgusSessionManager type-safe state contracts, validation, and fallback operations.
3. Headless FastAPI endpoint POST /api/v1/rebalance.
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.services.rebalancing_service import RebalancingService
from core.session_manager import ArgusSessionKeys, ArgusSessionManager

# ==============================================================================
# 1. TEST REBALANCING SERVICE APPLICATION FACADE
# ==============================================================================

def test_rebalancing_service_autonomous():
    """Verifica che RebalancingService esegua correttamente la strategia autonomous."""
    positions = pd.DataFrame([
        {"ticker": "SWDA.MI", "qty_net": 100, "current_price": 100.0, "pmc": 80.0, "asset_class": "ETF", "current_value": 10000.0, "controvalore": 10000.0},
        {"ticker": "ISP.MI", "qty_net": 1000, "current_price": 4.0, "pmc": 3.0, "asset_class": "Equity", "current_value": 4000.0, "controvalore": 4000.0},
        {"ticker": "XEON.MI", "qty_net": 50, "current_price": 140.0, "pmc": 138.0, "asset_class": "ETF", "current_value": 7000.0, "controvalore": 7000.0},
    ])
    target_weights = {"SWDA.MI": 0.40, "ISP.MI": 0.20, "XEON.MI": 0.40}

    res = RebalancingService.execute_rebalance(
        positions=positions,
        target_weights=target_weights,
        strategy="autonomous",
        minusvalenze_available=300.0,
        metadata={"risk_profile": "Moderate"},
    )

    assert res["status"] == "COMPLETED"
    assert res["strategy"] == "autonomous"
    assert "orders" in res
    assert isinstance(res["orders"], list)
    assert len(res["orders"]) > 0
    assert "summary" in res
    assert "tax_report" in res
    assert "compliance" in res
    assert "is_mifid_compliant" in res["compliance"]
    assert "status" in res["compliance"]


def test_rebalancing_service_polymorphic_strategies():
    """Verifica che RebalancingService supporti input via dict e le altre strategie."""
    dict_positions = [
        {"ticker": "AAPL", "shares": 50, "current_price": 200.0, "pmc": 180.0, "asset_class": "Equity"},
        {"ticker": "MSFT", "shares": 25, "current_price": 400.0, "pmc": 350.0, "asset_class": "Equity"},
    ]
    target_weights = {"AAPL": 0.60, "MSFT": 0.40}

    # 1. Tax Aware
    res_tax = RebalancingService.execute_rebalance(
        positions=dict_positions,
        target_weights=target_weights,
        strategy="tax_aware",
        minusvalenze_available=150.0,
    )
    assert res_tax["status"] == "COMPLETED"
    assert res_tax["strategy"] == "tax_aware"
    assert len(res_tax["orders"]) == 2

    # 2. Heuristic
    res_heur = RebalancingService.execute_rebalance(
        positions=dict_positions,
        target_weights=target_weights,
        strategy="heuristic",
    )
    assert res_heur["status"] == "COMPLETED"
    assert res_heur["strategy"] == "heuristic"
    assert len(res_heur["orders"]) == 2

    # 3. Prescriptive
    res_presc = RebalancingService.execute_rebalance(
        positions=dict_positions,
        target_weights=target_weights,
        strategy="prescriptive",
    )
    assert res_presc["status"] == "COMPLETED"
    assert res_presc["strategy"] == "prescriptive"


# ==============================================================================
# 2. TEST ARGUS SESSION STATE MANAGER
# ==============================================================================

def test_session_manager_initialization_and_accessors():
    """Verifica l'inizializzazione atomica, default e validazioni di ArgusSessionManager."""
    ArgusSessionManager.reset_session()
    ArgusSessionManager.ensure_initialized()

    # Valuta base
    assert ArgusSessionManager.get_base_currency() == "EUR"
    ArgusSessionManager.set_base_currency("usd")
    assert ArgusSessionManager.get_base_currency() == "USD"
    with pytest.raises(ValueError):
        ArgusSessionManager.set_base_currency("BITCOIN")

    # Profilo di rischio
    assert ArgusSessionManager.get_risk_profile() == "Moderate"
    ArgusSessionManager.set_risk_profile("aggressive")
    assert ArgusSessionManager.get_risk_profile() == "Aggressive"
    with pytest.raises(ValueError):
        ArgusSessionManager.set_risk_profile("SuperYolo")

    # Portfolio ID
    assert ArgusSessionManager.get_portfolio_id() == 1
    ArgusSessionManager.set_portfolio_id(42)
    assert ArgusSessionManager.get_portfolio_id() == 42

    # Minusvalenze
    assert ArgusSessionManager.get_minusvalenze_available() == 0.0
    ArgusSessionManager.set_minusvalenze_available(1250.50)
    assert ArgusSessionManager.get_minusvalenze_available() == 1250.50

    # Salvataggio e recupero esito ribilanciamento
    sample_res = {"strategy": "autonomous", "summary": {"turnover": 15.0}}
    ArgusSessionManager.save_rebalance_result(sample_res)
    last_res = ArgusSessionManager.get_last_rebalance_result()
    assert last_res is not None
    assert last_res["strategy"] == "autonomous"
    assert "timestamp_utc" in last_res

    # Gestione active positions
    df_sample = pd.DataFrame([{"ticker": "NVDA", "shares": 10}])
    ArgusSessionManager.set_active_positions(df_sample)
    retrieved_df = ArgusSessionManager.get_active_positions()
    assert len(retrieved_df) == 1
    assert retrieved_df.iloc[0]["ticker"] == "NVDA"


# ==============================================================================
# 3. TEST HEADLESS FASTAPI REST ENDPOINTS
# ==============================================================================

def test_api_rebalance_endpoint():
    """Verifica l'endpoint POST /api/v1/rebalance con TestClient."""
    client = TestClient(app)

    payload = {
        "holdings": [
            {"ticker": "SWDA.MI", "shares": 100, "current_price": 100.0, "pmc": 80.0, "asset_class": "ETF"},
            {"ticker": "ISP.MI", "shares": 1000, "current_price": 4.0, "pmc": 3.0, "asset_class": "Equity"}
        ],
        "target_weights": {"SWDA.MI": 0.50, "ISP.MI": 0.50},
        "strategy": "autonomous",
        "minusvalenze_available": 500.0,
        "max_turnover_pct": 30.0,
        "min_trade_eur": 100.0,
        "cash_injection": 0.0
    }

    response = client.post("/api/v1/rebalance", json=payload)
    assert response.status_code == 200, f"Error: {response.text}"

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["strategy"] == "autonomous"
    assert "orders" in data
    assert isinstance(data["orders"], list)
    assert len(data["orders"]) > 0
    assert "summary" in data
    assert "tax_report" in data
    assert "compliance" in data


def test_api_rebalance_validation_error():
    """Verifica che un payload non valido (senza holdings) restituisca 422 Unprocessable Entity."""
    client = TestClient(app)
    bad_payload = {
        "holdings": [],  # Min length 1
        "target_weights": {"SWDA.MI": 1.0}
    }
    response = client.post("/api/v1/rebalance", json=bad_payload)
    assert response.status_code == 422
