"""
ARGUS — Risk Analytics Platform
Unit Tests for Tax Optimization & Tax-Loss Harvesting Engine
"""

import pytest
import pandas as pd
from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate

def test_get_asset_tax_rate():
    assert get_asset_tax_rate("Equity", "GOOGL") == 0.26
    assert get_asset_tax_rate("Government Bond", "BTP-1FE27") == 0.125
    assert get_asset_tax_rate("ETF", "BTP-ITALIA") == 0.125
    assert get_asset_tax_rate("Crypto", "BTC-USD") == 0.26

def test_tax_engine_calculation():
    positions_data = [
        {"ticker": "GOOGL", "asset_class": "Equity", "qty_net": 10, "cost_basis": 1000.0, "unrealized_pnl": 500.0, "realized_pnl": 200.0},
        {"ticker": "BABA", "asset_class": "Equity", "qty_net": 20, "cost_basis": 2000.0, "unrealized_pnl": -300.0, "realized_pnl": 0.0},
        {"ticker": "BTP", "asset_class": "Government Bond", "qty_net": 100, "cost_basis": 10000.0, "unrealized_pnl": -50.0, "realized_pnl": 100.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}
    
    tax_res = compute_tax_and_harvesting(results)
    summary = tax_res["summary"]
    
    assert summary["total_realized_gain_eur"] == 300.0
    assert summary["net_realized_pnl_eur"] == 300.0
    assert summary["estimated_tax_due_eur"] > 0
    
    df_harvest = tax_res["harvesting_opportunities"]
    assert not df_harvest.empty
    assert "potential_tax_saving_eur" in df_harvest.columns
