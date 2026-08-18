"""
ARGUS — Risk Analytics Platform
Unit Tests for 3D Surface Stress Testing, MSCI Barra Multi-Factor Model, and ML Volatility/Distress Classifier
"""

import pytest
import numpy as np
import pandas as pd

from core.risk_engine import compute_3d_stress_surface, compute_msci_barra_multifactor_model
from core.financial_analysis import predict_ml_distress_and_volatility


def test_compute_3d_stress_surface():
    pos_data = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 50000.0, "qty_net": 100, "asset_class": "Equity"},
        {"ticker": "AGGH.MI", "current_value": 30000.0, "qty_net": 300, "asset_class": "Bond"}
    ])
    
    res = compute_3d_stress_surface(pos_data)
    assert "rate_grid" in res
    assert "vol_grid" in res
    assert "z_pnl_eur" in res
    assert "worst_pnl_eur" in res
    assert res["worst_pnl_eur"] <= 0.0


def test_compute_msci_barra_multifactor_model():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    sr_p = pd.Series(np.random.normal(0.0005, 0.015, 100), index=dates)
    sr_m = pd.Series(np.random.normal(0.0004, 0.012, 100), index=dates)

    res = compute_msci_barra_multifactor_model(sr_p, sr_m)
    assert "factor_betas" in res
    assert "MKT" in res["factor_betas"]
    assert "r_squared" in res
    assert 0.0 <= res["r_squared"] <= 1.0


def test_predict_ml_distress_and_volatility():
    dates = pd.date_range("2023-01-01", periods=50, freq="B")
    df_prices = pd.DataFrame({
        "close": np.linspace(100, 150, 50) + np.random.normal(0, 2, 50)
    }, index=dates)

    ratios = {
        "altman_z": 3.2,
        "piotroski_f": 8,
        "current_ratio": 2.1,
        "debt_equity": 0.4,
        "net_margin": 18.5
    }

    res = predict_ml_distress_and_volatility(df_prices, company_ratios=ratios)
    assert "distress_probability_pct" in res
    assert "predicted_volatility_30d_pct" in res
    assert "risk_level" in res
    assert "verdict" in res
    assert "feature_importance_df" in res
    assert not res["feature_importance_df"].empty
