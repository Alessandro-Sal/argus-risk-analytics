# ============================================================
# tests/test_new_quant_features.py
# ARGUS — Risk Analytics Platform
# Unit Tests for Carhart 4-Factor, ATR Chandelier Exit & Macro Stress
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.risk_engine import (
    compute_carhart_4factor_exposures,
    compute_atr_chandelier_exits,
    compute_custom_macro_stress
)

def test_carhart_4factor_exposures():
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.015, 100))
    res = compute_carhart_4factor_exposures(returns)
    
    assert "alpha" in res
    assert "beta_mkt" in res
    assert "beta_smb" in res
    assert "beta_hml" in res
    assert "beta_wml" in res
    assert 0.0 <= res["r_squared"] <= 1.0


def test_atr_chandelier_exits():
    dates = pd.date_range("2024-01-01", periods=30)
    prices_data = []
    for d in dates:
        prices_data.append({
            "ticker": "AAPL",
            "price_date": d,
            "close": 150.0 + np.random.normal(0, 2),
            "high": 152.0,
            "low": 148.0
        })
    df_prices = pd.DataFrame(prices_data)
    df_positions = pd.DataFrame([{"ticker": "AAPL", "last_price": 150.0}])

    res = compute_atr_chandelier_exits(df_prices, df_positions, period=14, multiplier=3.0)
    
    assert "summary" in res
    assert "stop_triggered_count" in res
    assert len(res["summary"]) == 1
    assert res["summary"][0]["chandelier_stop"] < 152.0


def test_custom_macro_stress():
    df_positions = pd.DataFrame([
        {"ticker": "GOOGL", "current_value": 10000.0, "asset_class": "Equity"},
        {"ticker": "BND", "current_value": 5000.0, "asset_class": "Bond"}
    ])

    res = compute_custom_macro_stress(
        df_positions,
        rate_shock_bps=100,
        fx_shock_pct=-5.0,
        oil_shock_pct=20.0,
        equity_shock_pct=-10.0
    )

    assert "portfolio_val_before" in res
    assert res["portfolio_val_before"] == 15000.0
    assert not res["details_df"].empty
    assert len(res["details_df"]) == 2
