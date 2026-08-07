"""
ARGUS — Risk Analytics Platform
Core Module: Hedging Engine (Beta-Neutral & Tail Risk Protection)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

# Standard Market Prices for popular Inverse ETFs / Hedging instruments
HEDGE_INSTRUMENTS = {
    "SH": {"name": "ProShares Short S&P500", "underlying": "S&P 500", "beta_mult": -1.0, "price_approx": 14.50},
    "PSQ": {"name": "ProShares Short QQQ", "underlying": "NASDAQ 100", "beta_mult": -1.0, "price_approx": 10.20},
    "DOG": {"name": "ProShares Short Dow30", "underlying": "Dow Jones Industrial", "beta_mult": -1.0, "price_approx": 31.80},
    "VIXY": {"name": "ProShares VIX Short-Term Futures", "underlying": "S&P 500 VIX", "beta_mult": -2.5, "price_approx": 12.40},
}

def compute_beta_neutral_hedge(
    results: Dict[str, Any],
    target_beta: float = 0.0,
    hedge_ticker: str = "SH"
) -> Dict[str, Any]:
    """
    Computes exact trade parameters required to hedge portfolio Beta down to target_beta.
    
    Formula:
      Required Hedge Value H = - (Portfolio_Beta - Target_Beta) * Portfolio_Value / Hedge_Beta_Multiplier
      Required Shares = round(|H| / Hedge_Price)
    """
    pos = results.get("positions", pd.DataFrame())
    if pos.empty or "current_value" not in pos.columns:
        return {
            "portfolio_value": 0.0,
            "current_beta": 1.0,
            "target_beta": target_beta,
            "hedge_value_eur": 0.0,
            "hedge_shares": 0,
            "instrument": HEDGE_INSTRUMENTS.get(hedge_ticker, {})
        }

    active_pos = pos[pos["qty_net"] > 0] if "qty_net" in pos.columns else pos
    port_val = float(active_pos["current_value"].sum())
    
    # Portfolio Beta vs Benchmark
    curr_beta = float(results.get("portfolio_beta", 1.0) or 1.0)
    
    inst = HEDGE_INSTRUMENTS.get(hedge_ticker, HEDGE_INSTRUMENTS["SH"])
    beta_mult = inst["beta_mult"]
    hedge_price = inst["price_approx"]
    
    # Beta difference to hedge
    beta_delta = curr_beta - target_beta
    
    if abs(beta_delta) < 0.01 or port_val <= 0:
        hedge_val = 0.0
        shares = 0
    else:
        # Hedge Value in EUR
        hedge_val = (beta_delta * port_val) / abs(beta_mult)
        shares = int(np.round(hedge_val / hedge_price)) if hedge_price > 0 else 0

    # Tail Risk Option / Stop Protection based on VaR 99%
    var_99_pct = float(results.get("var_99_hist", 0.03) or 0.03)
    tail_risk_eur = port_val * var_99_pct

    return {
        "portfolio_value": port_val,
        "current_beta": round(curr_beta, 3),
        "target_beta": round(target_beta, 3),
        "beta_delta": round(beta_delta, 3),
        "hedge_value_eur": round(hedge_val, 2),
        "hedge_shares": max(0, shares),
        "instrument_ticker": hedge_ticker,
        "instrument_name": inst["name"],
        "instrument_underlying": inst["underlying"],
        "instrument_price": hedge_price,
        "tail_risk_var99_eur": round(tail_risk_eur, 2),
        "new_hedged_beta": round(target_beta if shares > 0 else curr_beta, 3)
    }
