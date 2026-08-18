import numpy as np

def test_monte_carlo_var_bounds():
    # Simulated final portfolio values (10000 paths)
    np.random.seed(42)
    final_values = np.random.normal(loc=1.08, scale=0.15, size=10000) # mean 8% CAGR, 15% Vol
    
    var_95_mc = (1 - np.percentile(final_values, 5)) * 100
    var_99_mc = (1 - np.percentile(final_values, 1)) * 100
    expected_return_1y = (np.mean(final_values) - 1) * 100
    
    # 1. 99% VaR must be strictly greater than 95% VaR (higher tail risk confidence)
    assert var_99_mc > var_95_mc
    
    # 2. VaR percentages should be positive or reasonable
    assert var_95_mc > -100
    assert var_99_mc > -100
    
    # 3. Expected return should match the simulation mean
    assert abs(expected_return_1y - 8.0) < 1.0 # close to 8%


def test_run_advanced_monte_carlo_simulation():
    import pandas as pd
    from core.risk_engine import run_advanced_monte_carlo_simulation
    
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    df_ret = pd.DataFrame({
        "AAPL": np.random.normal(0.001, 0.015, 100),
        "MSFT": np.random.normal(0.0008, 0.012, 100)
    }, index=dates)
    
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 10, "current_value": 1500.0},
        {"ticker": "MSFT", "qty_net": 5, "current_value": 1500.0}
    ])
    
    dummy_results = {
        "positions": df_pos,
        "metrics": {"historical_returns": df_ret}
    }
    
    res = run_advanced_monte_carlo_simulation(dummy_results, horizon_days=126, volatility_multiplier=1.2, distribution_type="student_t", n_simulations=500)
    
    assert res["initial_portfolio_value"] == 3000.0
    assert res["horizon_days"] == 126
    assert len(res["p50_path"]) == 127
    assert res["var_99_pct"] > res["var_95_pct"]
    assert res["cvar_95_pct"] >= res["var_95_pct"]
    assert 0 <= res["prob_profit_pct"] <= 100
