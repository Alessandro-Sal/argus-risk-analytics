"""
tests/test_msci_barra_risk_engine.py
Unit tests for BarraMultiAssetRiskEngine (MSCI Barra Multi-Asset GEM3/USE4 Standard).
"""

import pytest
import numpy as np
from core.msci_barra_risk_engine import (
    BarraMultiAssetRiskEngine,
    AssetFactorProfile,
    STYLE_FACTORS,
    GICS_SECTORS
)


def test_barra_risk_engine_euler_decomposition():
    engine = BarraMultiAssetRiskEngine()
    
    # 4 distinct assets across different sectors and styles
    profiles = [
        engine.estimate_default_exposures_for_ticker("AAPL", name="Apple Inc", weight=0.40, current_value=40000.0),
        engine.estimate_default_exposures_for_ticker("BTP-10Y", name="BTP 10Y", weight=0.30, current_value=30000.0),
        engine.estimate_default_exposures_for_ticker("XOM", name="ExxonMobil", weight=0.15, current_value=15000.0),
        engine.estimate_default_exposures_for_ticker("JNJ", name="Johnson & Johnson", weight=0.15, current_value=15000.0),
    ]

    res = engine.decompose_portfolio_factor_risk(profiles)

    assert "volatility_total_annual" in res
    assert res["volatility_total_annual"] > 0
    assert res["volatility_factor_annual"] > 0
    assert res["volatility_specific_annual"] > 0

    # 1. Test Orthogonal Variance Decomposition: Total_Var = Factor_Var + Specific_Var
    var_tot = res["volatility_total_annual"] ** 2
    var_fact = res["volatility_factor_annual"] ** 2
    var_spec = res["volatility_specific_annual"] ** 2
    assert var_tot == pytest.approx(var_fact + var_spec, rel=1e-4)

    # 2. Test Percent Contributions sum to 100%
    assert res["factor_risk_contribution_pct"] + res["specific_risk_contribution_pct"] == pytest.approx(100.0, abs=1e-3)

    # 3. Test Euler's Theorem on Asset PCTR: Sum(PCTR_i) == 100%
    assert res["euler_sum_pctr"] == pytest.approx(100.0, abs=1e-3)

    # 4. Check Asset-Level DataFrame
    df_assets = res["asset_risk_df"]
    assert len(df_assets) == 4
    assert np.sum(df_assets["pctr_total"]) == pytest.approx(100.0, abs=1e-3)

    # 5. Check Factor-Level DataFrame
    df_factors = res["factor_attribution_df"]
    assert not df_factors.empty
    assert "factor_pctr" in df_factors.columns
    # Sum of factor PCTR should equal factor_risk_contribution_pct
    assert np.sum(df_factors["factor_pctr"]) == pytest.approx(res["factor_risk_contribution_pct"], abs=1e-3)


def test_barra_single_asset_portfolio():
    engine = BarraMultiAssetRiskEngine()
    profile = [engine.estimate_default_exposures_for_ticker("MSFT", weight=1.0, current_value=100000.0)]
    res = engine.decompose_portfolio_factor_risk(profile)

    assert res["euler_sum_pctr"] == pytest.approx(100.0, abs=1e-3)
    assert len(res["asset_risk_df"]) == 1
    assert res["asset_risk_df"].iloc[0]["pctr_total"] == pytest.approx(100.0, abs=1e-3)
    assert res["active_style_tilts"]["Size"] > 0


def test_barra_empty_portfolio():
    engine = BarraMultiAssetRiskEngine()
    res = engine.decompose_portfolio_factor_risk([])
    assert "error" in res
