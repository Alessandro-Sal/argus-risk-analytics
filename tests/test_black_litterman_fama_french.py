import pytest
import pandas as pd
import numpy as np
from core.risk_engine import compute_black_litterman_optimization, compute_fama_french_exposures

def test_compute_black_litterman_optimization():
    assets = ["AAPL", "MSFT", "GOOGL"]
    cov_data = np.array([
        [0.04, 0.015, 0.01],
        [0.015, 0.035, 0.012],
        [0.01, 0.012, 0.03]
    ])
    cov_df = pd.DataFrame(cov_data, index=assets, columns=assets)
    weights = pd.Series([0.4, 0.4, 0.2], index=assets)

    views = {"AAPL": 0.12}
    res = compute_black_litterman_optimization(cov_df, weights, views)
    
    assert "implied_equilibrium_returns" in res
    assert "black_litterman_returns" in res
    assert "black_litterman_weights" in res
    assert len(res["black_litterman_weights"]) == 3
    assert abs(res["black_litterman_weights"].sum() - 1.0) < 1e-4

def test_compute_fama_french_exposures():
    sr_returns = pd.Series(np.random.normal(0.0005, 0.01, 100), index=pd.date_range("2026-01-01", periods=100))
    res = compute_fama_french_exposures(sr_returns)

    assert "alpha" in res
    assert "beta_mkt" in res
    assert "beta_smb" in res
    assert "beta_hml" in res
    assert "r_squared" in res
