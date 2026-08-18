import numpy as np
import scipy.stats as stats

def calculate_risk_metrics(returns, conf_level=0.95, holding_period=1, total_value=100000):
    r = np.array(returns)
    alpha = 1 - conf_level
    z = stats.norm.ppf(alpha)
    
    # 1. Historical VaR (1d)
    threshold_hist_1d = np.percentile(r, alpha * 100)
    var_hist_1d = abs(threshold_hist_1d)
    
    # 2. Parametric VaR (1d)
    mean_daily = r.mean()
    std_daily = r.std()
    var_param_1d = abs(mean_daily + z * std_daily)
    
    # 3. Cornish-Fisher VaR (1d)
    skewness = stats.skew(r) if len(r) > 2 else 0.0
    kurtosis = stats.kurtosis(r) if len(r) > 2 else 0.0
    z_cf = z + (1/6)*(z**2 - 1)*skewness + (1/24)*(z**3 - 3*z)*kurtosis - (1/36)*(2*z**3 - 5*z)*(skewness**2)
    var_cf_1d = abs(mean_daily + z_cf * std_daily)
    
    # 4. Expected Shortfall / CVaR Storico (1g)
    tail_returns = r[r <= threshold_hist_1d]
    cvar_hist_1d = abs(tail_returns.mean()) if len(tail_returns) > 0 else var_hist_1d
    
    # Scaling
    sqrt_t = np.sqrt(holding_period)
    
    return {
        "var_hist": var_hist_1d * sqrt_t * total_value,
        "var_param": var_param_1d * sqrt_t * total_value,
        "var_cf": var_cf_1d * sqrt_t * total_value,
        "cvar_hist": cvar_hist_1d * sqrt_t * total_value
    }

def test_var_cvar_base():
    # Mock data: normal returns centered around 0 with std of 1%
    np.random.seed(42)
    mock_returns = np.random.normal(0, 0.01, 1000)
    
    metrics = calculate_risk_metrics(mock_returns, conf_level=0.95, holding_period=1, total_value=100000)
    
    # Since normal distribution has skew ~ 0 and kurtosis ~ 0:
    # Parametric and Cornish-Fisher VaR should be very close.
    assert abs(metrics["var_param"] - metrics["var_cf"]) < 1000  # less than 1% of total value difference
    
    # Historical CVaR should be larger than Historical VaR (tail average is worse than tail boundary)
    assert metrics["cvar_hist"] > metrics["var_hist"]
    
    # 10-day VaR should be larger than 1-day VaR
    metrics_10d = calculate_risk_metrics(mock_returns, conf_level=0.95, holding_period=10, total_value=100000)
    assert metrics_10d["var_hist"] > metrics["var_hist"]
    
    # Scaling factor should be exactly sqrt(10)
    expected_ratio = np.sqrt(10)
    actual_ratio = metrics_10d["var_hist"] / metrics["var_hist"]
    assert abs(actual_ratio - expected_ratio) < 1e-5
