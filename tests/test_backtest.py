import numpy as np
import pandas as pd

def compute_backtest_metrics(ret_series, risk_free_rate=0.035):
    # Cumulative return
    cum_ret = (1 + ret_series).prod() - 1
    
    # CAGR
    n_days = len(ret_series)
    years = n_days / 252
    cagr = (1 + cum_ret) ** (1 / years) - 1 if years > 0 else 0.0
    
    # Volatility
    vol = ret_series.std() * np.sqrt(252)
    
    # Sharpe Ratio
    excess = ret_series - (risk_free_rate / 252)
    sharpe = (excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
    
    # Max Drawdown
    cum = (1 + ret_series).cumprod()
    roll_mx = cum.cummax()
    max_dd = ((cum - roll_mx) / roll_mx).min()
    
    return {
        "cum_return": cum_ret,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd
    }

def test_backtest_compounding_math():
    # Mock return series: 252 days of a constant 0.1% daily return
    returns = pd.Series([0.001] * 252)
    
    metrics = compute_backtest_metrics(returns)
    
    # 1. Cumulative returns compounded: (1.001)^252 - 1 = 28.6%
    expected_cum = (1.001) ** 252 - 1
    assert abs(metrics["cum_return"] - expected_cum) < 1e-7
    
    # 2. Since length is exactly 252 days (1 year), CAGR should equal Cumulative Return
    assert abs(metrics["cagr"] - metrics["cum_return"]) < 1e-7
    
    # 3. Constant return means standard deviation is approximately 0 (accounting for floating point limits)
    assert abs(metrics["volatility"]) < 1e-12

    
    # 4. Constant positive return with 0 standard deviation -> Sharpe is 0 due to 0 division check
    assert metrics["sharpe"] == 0.0
    
    # 5. Since returns are always positive, cumulative value is monotonically increasing
    # So max drawdown must be exactly 0
    assert metrics["max_drawdown"] == 0.0

def test_backtest_drawdown_calculation():
    # 3 days: day 1 +10%, day 2 -20%, day 3 +10%
    returns = pd.Series([0.10, -0.20, 0.10])
    
    metrics = compute_backtest_metrics(returns)
    
    # Cumulative series:
    # Start: 1.0
    # Day 1: 1.10
    # Day 2: 1.10 * 0.80 = 0.88
    # Day 3: 0.88 * 1.10 = 0.968
    # Max cumulative peak was at Day 1: 1.10
    # Lowest point relative to peak was at Day 2: (0.88 - 1.10) / 1.10 = -20%
    # So max drawdown should be exactly -20% (-0.20)
    assert abs(metrics["max_drawdown"] - (-0.20)) < 1e-7
