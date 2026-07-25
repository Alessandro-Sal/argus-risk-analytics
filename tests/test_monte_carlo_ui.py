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
