"""
Unit tests for GARCH(1,1) Conditional Volatility Engine & Filtered Historical Simulation (FHS).
"""

import numpy as np
import pandas as pd
import pytest

from core.garch_engine import (
    compute_filtered_historical_simulation,
    compute_garch_fhs_bundle,
    fit_garch11,
    forecast_garch_volatility,
)
from core.risk_engine import compute_sandbox_risk_bundle


@pytest.fixture
def sample_returns_series():
    """Genera una serie storica sintetica di rendimenti giornalieri (500 giorni)."""
    np.random.seed(42)
    n = 500
    eps = np.random.normal(0, 0.012, n)
    # Crea un cluster di volatilità a metà serie
    eps[200:250] *= 2.5
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(eps, index=dates, name="portfolio_return")


def test_fit_garch11_basic(sample_returns_series):
    res = fit_garch11(sample_returns_series)
    assert res["converged"] in [True, False]
    assert res["omega"] > 0
    assert res["alpha"] >= 0
    assert res["beta"] >= 0
    assert res["persistence"] < 1.0
    assert res["unconditional_variance"] > 0
    assert res["current_annual_vol_pct"] > 0
    assert res["next_day_annual_vol_pct"] > 0
    assert len(res["sigma_series"]) == len(sample_returns_series)
    assert len(res["standardized_residuals"]) == len(sample_returns_series)


def test_standardized_residuals_properties(sample_returns_series):
    res = fit_garch11(sample_returns_series)
    e = res["standardized_residuals"].dropna()
    # I residui standardizzati dovrebbero avere media vicina a 0 e deviazione standard vicina a 1
    assert abs(e.mean()) < 0.25
    assert 0.7 < e.std() < 1.3


def test_forecast_garch_volatility_term_structure(sample_returns_series):
    res = fit_garch11(sample_returns_series)
    df_term = forecast_garch_volatility(res, horizon=30)
    assert len(df_term) == 30
    assert "horizon_days" in df_term.columns
    assert "forecast_annual_vol_pct" in df_term.columns

    # Asintoticamente la previsione deve avvicinarsi alla volatilità di lungo termine
    uncond_vol = res["unconditional_annual_vol_pct"]
    last_forecast = df_term["forecast_annual_vol_pct"].iloc[-1]
    first_forecast = df_term["forecast_annual_vol_pct"].iloc[0]

    # Se il primo forecast dista da uncond_vol, l'ultimo deve essere più vicino
    if abs(first_forecast - uncond_vol) > 0.1:
        assert abs(last_forecast - uncond_vol) <= abs(first_forecast - uncond_vol)


def test_compute_filtered_historical_simulation(sample_returns_series):
    fhs = compute_filtered_historical_simulation(sample_returns_series, horizon=1)
    var_95 = fhs["var_fhs"]["var_fhs_95"]
    var_99 = fhs["var_fhs"]["var_fhs_99"]
    cvar_95 = fhs["cvar_fhs"]["cvar_fhs_95"]
    cvar_99 = fhs["cvar_fhs"]["cvar_fhs_99"]

    assert var_95 > 0
    assert var_99 > var_95
    assert cvar_95 >= var_95
    assert cvar_99 >= var_99


def test_garch_fhs_bundle(sample_returns_series):
    bundle = compute_garch_fhs_bundle(sample_returns_series, total_value=100000.0, horizon=1)
    assert "fit" in bundle
    assert "fhs" in bundle
    assert "term_structure" in bundle
    assert "dynamic_bands" in bundle
    assert "kpis" in bundle

    kpis = bundle["kpis"]
    assert kpis["var_fhs_95_pct"] > 0
    assert kpis["var_fhs_95_eur"] > 0
    assert kpis["cvar_fhs_95_pct"] >= kpis["var_fhs_95_pct"]


def test_garch_short_series_graceful():
    """Serie con meno di 30 punti deve gestire il fallback in modo robusto."""
    short_series = pd.Series([0.01, -0.02, 0.005, 0.015, -0.01])
    res = fit_garch11(short_series)
    assert res["converged"] is False
    assert res["next_day_annual_vol_pct"] > 0

    bundle = compute_garch_fhs_bundle(short_series, total_value=50000.0)
    assert bundle["kpis"]["var_fhs_95_pct"] > 0


def test_risk_engine_integration_garch():
    """Verifica che compute_sandbox_risk_bundle includa il bundle garch_fhs."""
    sb_bundle = compute_sandbox_risk_bundle("balanced_growth")
    assert "garch_fhs" in sb_bundle
    garch_res = sb_bundle["garch_fhs"]
    assert "fit" in garch_res
    assert "kpis" in garch_res
    assert garch_res["kpis"]["var_fhs_95_pct"] > 0
