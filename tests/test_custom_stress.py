import pandas as pd
import numpy as np

def simulate_stress_test(portfolio_value, port_beta, benchmark_shock, assets_data):
    port_shock_pct = port_beta * (benchmark_shock / 100)
    port_loss_eur = port_shock_pct * portfolio_value
    
    simulated_assets = []
    for asset in assets_data:
        ticker = asset["ticker"]
        curr_val = asset["current_value"]
        weight = asset["weight_pct"]
        beta = asset["beta"]
        
        asset_shock = beta * (benchmark_shock / 100)
        asset_loss = asset_shock * curr_val
        
        simulated_assets.append({
            "ticker": ticker,
            "weight": weight,
            "current_value": curr_val,
            "beta": beta,
            "shock_pct": asset_shock * 100,
            "loss_eur": asset_loss
        })
        
    return port_shock_pct, port_loss_eur, simulated_assets

def test_stress_test_linearity_math():
    # Portfolio of 3 assets
    portfolio_value = 100000.0  # €100,000
    benchmark_shock = -20.0     # -20%
    
    assets_data = [
        {"ticker": "AAPL", "weight_pct": 50.0, "current_value": 50000.0, "beta": 1.2},
        {"ticker": "KO", "weight_pct": 30.0, "current_value": 30000.0, "beta": 0.6},
        {"ticker": "ISP.MI", "weight_pct": 20.0, "current_value": 20000.0, "beta": 1.5}
    ]
    
    # Portfolio Beta is the weighted average of individual Betas
    # port_beta = 0.5 * 1.2 + 0.3 * 0.6 + 0.2 * 1.5 = 0.6 + 0.18 + 0.3 = 1.08
    port_beta = 1.08
    
    port_shock, port_loss, sim_assets = simulate_stress_test(
        portfolio_value, port_beta, benchmark_shock, assets_data
    )
    
    # Portfolio shock should be: 1.08 * -20% = -21.6% (-0.216)
    assert abs(port_shock - (-0.216)) < 1e-7
    # Portfolio loss should be: -0.216 * 100,000 = -21,600 €
    assert abs(port_loss - (-21600.0)) < 1e-7
    
    # Individual asset checks
    # AAPL: shock = 1.2 * -20% = -24% (-0.24). Loss = -0.24 * 50,000 = -12,000 €
    assert abs(sim_assets[0]["shock_pct"] - (-24.0)) < 1e-7
    assert abs(sim_assets[0]["loss_eur"] - (-12000.0)) < 1e-7
    
    # KO: shock = 0.6 * -20% = -12% (-0.12). Loss = -0.12 * 30,000 = -3,600 €
    assert abs(sim_assets[1]["shock_pct"] - (-12.0)) < 1e-7
    assert abs(sim_assets[1]["loss_eur"] - (-3600.0)) < 1e-7
    
    # ISP.MI: shock = 1.5 * -20% = -30% (-0.30). Loss = -0.30 * 20,000 = -6,000 €
    assert abs(sim_assets[2]["shock_pct"] - (-30.0)) < 1e-7
    assert abs(sim_assets[2]["loss_eur"] - (-6000.0)) < 1e-7
    
    # Sum of individual losses must exactly equal portfolio loss
    sum_individual_losses = sum(a["loss_eur"] for a in sim_assets)
    assert abs(sum_individual_losses - port_loss) < 1e-7
