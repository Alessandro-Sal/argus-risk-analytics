import pytest
import pandas as pd
import numpy as np
from core.risk_engine import compute_merton_jump_diffusion_simulation
from core.financial_analysis import detect_portfolio_anomalies_isolation_forest

def test_compute_merton_jump_diffusion_simulation():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    sr_p = pd.Series(np.random.normal(0.0005, 0.01, 100), index=dates)

    res = compute_merton_jump_diffusion_simulation(
        sr_portfolio=sr_p,
        n_sims=100,
        time_horizon_days=63,
        lambda_j=2.0,
        mu_j=-0.10,
        sigma_j=0.04
    )

    assert "p50" in res
    assert len(res["p50"]) == 64
    assert res["var_99_jump_pct"] > 0
    assert res["cvar_99_jump_pct"] >= res["var_99_jump_pct"]
    assert res["mean_jumps_per_year"] >= 0

def test_detect_portfolio_anomalies_isolation_forest():
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    df_returns = pd.DataFrame({
        "Asset1": np.random.normal(0.001, 0.01, 100),
        "Asset2": np.random.normal(0.0005, 0.012, 100)
    }, index=dates)

    df_returns.iloc[20] = [-0.08, -0.09]
    df_returns.iloc[50] = [+0.07, +0.08]

    res = detect_portfolio_anomalies_isolation_forest(df_returns=df_returns, contamination=0.05)

    assert "full_results_df" in res
    assert "anomaly_df" in res
    assert res["total_days"] == 100
    assert res["anomaly_count"] > 0
    assert len(res["anomaly_df"]) == res["anomaly_count"]

def test_detect_portfolio_anomalies_isolation_forest_empty_and_nan_fallback():
    # Test con dataframe vuoto e NaN sparsi
    res_empty = detect_portfolio_anomalies_isolation_forest(df_returns=pd.DataFrame(), contamination=0.05)
    assert res_empty["total_days"] > 0

    df_nan = pd.DataFrame({
        "Asset1": [np.nan, 0.01, np.nan, -0.02, 0.03],
        "Asset2": [0.02, np.nan, 0.01, np.nan, -0.01]
    }, index=pd.date_range("2024-01-01", periods=5, freq="B"))
    res_nan = detect_portfolio_anomalies_isolation_forest(df_returns=df_nan, contamination=0.05)
    assert res_nan["total_days"] > 0
