import numpy as np

def calculate_diversification_ratio(weights, individual_vols, portfolio_vol):
    weighted_vol = np.sum(weights * individual_vols)
    return (weighted_vol / portfolio_vol) if portfolio_vol > 0 else 1.0

def test_diversification_ratio_math():
    # Portfolio of 2 assets
    weights = np.array([0.5, 0.5])
    individual_vols = np.array([0.20, 0.30])  # 20% and 30% volatility
    
    # Scenario A: Perfect correlation, no diversification
    # portfolio vol = 25% (exactly the weighted average)
    port_vol_a = 0.25
    dr_a = calculate_diversification_ratio(weights, individual_vols, port_vol_a)
    assert abs(dr_a - 1.0) < 1e-7
    
    # Scenario B: High diversification (negative correlation)
    # portfolio vol = 15% (lower than both individual vols!)
    port_vol_b = 0.15
    dr_b = calculate_diversification_ratio(weights, individual_vols, port_vol_b)
    # DR should be: 0.25 / 0.15 = 1.6666667
    assert abs(dr_b - 1.6666667) < 1e-6
