import pandas as pd
import numpy as np
import pytest
from core.risk_engine import _compute_efficient_frontier

def test_compute_efficient_frontier_scipy():
    # Mock return series for 3 assets
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    
    ret_a = np.random.normal(0.001, 0.01, 100)
    ret_b = np.random.normal(-0.0005, 0.015, 100)
    ret_c = np.random.normal(0.0002, 0.005, 100)
    
    df_returns = pd.DataFrame({
        "AAPL": ret_a,
        "MSFT": ret_b,
        "GOOG": ret_c
    }, index=dates)
    
    # Mock positions DataFrame
    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 10.0, "weight_pct": 33.3},
        {"ticker": "MSFT", "qty_net": 15.0, "weight_pct": 33.3},
        {"ticker": "GOOG", "qty_net": 8.0, "weight_pct": 33.4}
    ])
    
    res = _compute_efficient_frontier(df_returns, df_positions)
    
    assert res is not None
    assert "max_sharpe" in res
    assert "min_vol" in res
    assert "tickers" in res
    
    max_sharpe_weights = res["max_sharpe"]["weights"]
    min_vol_weights = res["min_vol"]["weights"]
    
    assert len(max_sharpe_weights) == 3
    assert len(min_vol_weights) == 3
    assert pytest.approx(sum(max_sharpe_weights)) == 1.0
    assert pytest.approx(sum(min_vol_weights)) == 1.0
    
    # Verify bounds (long-only)
    for w in max_sharpe_weights:
        assert 0.0 <= w <= 1.0
    for w in min_vol_weights:
        assert 0.0 <= w <= 1.0
