# ============================================================
# core/options_workbench.py
# ARGUS — Multi-Leg Options Strategy Workbench & Payoff Engine
# Iron Condor, Collar, Spreads, Straddle & 2D/3D Greeks Decay
# ============================================================

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy.stats import norm


def _bs_price_and_greeks(
    spot: float, strike: float, t: float, r: float, sigma: float, option_type: str = "call"
) -> Dict[str, float]:
    """Calcola prezzo Black-Scholes e greche fondamentali (Delta, Gamma, Theta, Vega)."""
    if t <= 0.0001:
        if option_type == "call":
            val = max(0.0, spot - strike)
            delta = 1.0 if spot > strike else 0.0
        else:
            val = max(0.0, strike - spot)
            delta = -1.0 if spot < strike else 0.0
        return {"price": val, "delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d1 = (np.log(spot / strike) + (r + 0.5 * sigma ** 2) * t) / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)

    pdf_d1 = norm.pdf(d1)
    cdf_d1 = norm.cdf(d1)
    cdf_d2 = norm.cdf(d2)

    if option_type == "call":
        price = spot * cdf_d1 - strike * np.exp(-r * t) * cdf_d2
        delta = cdf_d1
        theta = (- (spot * pdf_d1 * sigma) / (2 * np.sqrt(t)) - r * strike * np.exp(-r * t) * cdf_d2) / 365.0
    else:
        cdf_minus_d1 = norm.cdf(-d1)
        cdf_minus_d2 = norm.cdf(-d2)
        price = strike * np.exp(-r * t) * cdf_minus_d2 - spot * cdf_minus_d1
        delta = cdf_d1 - 1.0
        theta = (- (spot * pdf_d1 * sigma) / (2 * np.sqrt(t)) + r * strike * np.exp(-r * t) * cdf_minus_d2) / 365.0

    gamma = pdf_d1 / (spot * sigma * np.sqrt(t))
    vega = (spot * np.sqrt(t) * pdf_d1) / 100.0

    return {
        "price": float(price),
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega)
    }


def get_options_strategy_presets() -> List[str]:
    """Elenco dei preset di strategie in opzioni supportate."""
    return [
        "Protective Collar",
        "Iron Condor",
        "Bull Call Spread",
        "Bear Put Spread",
        "Long Straddle",
        "Covered Call"
    ]


def build_options_strategy_payoff(
    strategy_name: str = "Iron Condor",
    underlying_price: float = 100.0,
    strike_offset_pct: float = 5.0,
    iv: float = 0.20,
    days_to_exp: int = 45,
    contracts: int = 1,
    risk_free_rate: float = 0.035
) -> Dict[str, Any]:
    """
    Costruisce la struttura multi-gamba, calcola greche e profili di payoff a scadenza e anticipati.
    """
    s0 = float(underlying_price)
    t_years = max(0.001, days_to_exp / 365.0)
    multiplier = contracts * 100

    legs = []
    # Definizione gambe in base al preset
    if strategy_name == "Iron Condor":
        # Buy Put OTM-far, Sell Put OTM, Sell Call OTM, Buy Call OTM-far
        k_put_long = s0 * (1 - 2 * strike_offset_pct / 100.0)
        k_put_short = s0 * (1 - strike_offset_pct / 100.0)
        k_call_short = s0 * (1 + strike_offset_pct / 100.0)
        k_call_long = s0 * (1 + 2 * strike_offset_pct / 100.0)

        legs = [
            {"type": "put", "action": "BUY", "strike": k_put_long, "qty": contracts},
            {"type": "put", "action": "SELL", "strike": k_put_short, "qty": contracts},
            {"type": "call", "action": "SELL", "strike": k_call_short, "qty": contracts},
            {"type": "call", "action": "BUY", "strike": k_call_long, "qty": contracts}
        ]
    elif strategy_name == "Protective Collar":
        # Long Stock + Long Put OTM + Short Call OTM
        k_put = s0 * (1 - strike_offset_pct / 100.0)
        k_call = s0 * (1 + strike_offset_pct / 100.0)
        legs = [
            {"type": "stock", "action": "BUY", "strike": s0, "qty": contracts},
            {"type": "put", "action": "BUY", "strike": k_put, "qty": contracts},
            {"type": "call", "action": "SELL", "strike": k_call, "qty": contracts}
        ]
    elif strategy_name == "Bull Call Spread":
        k1 = s0 * (1 - strike_offset_pct / 200.0)
        k2 = s0 * (1 + strike_offset_pct / 100.0)
        legs = [
            {"type": "call", "action": "BUY", "strike": k1, "qty": contracts},
            {"type": "call", "action": "SELL", "strike": k2, "qty": contracts}
        ]
    elif strategy_name == "Bear Put Spread":
        k1 = s0 * (1 + strike_offset_pct / 200.0)
        k2 = s0 * (1 - strike_offset_pct / 100.0)
        legs = [
            {"type": "put", "action": "BUY", "strike": k1, "qty": contracts},
            {"type": "put", "action": "SELL", "strike": k2, "qty": contracts}
        ]
    elif strategy_name == "Long Straddle":
        legs = [
            {"type": "call", "action": "BUY", "strike": s0, "qty": contracts},
            {"type": "put", "action": "BUY", "strike": s0, "qty": contracts}
        ]
    else:  # Covered Call
        k_call = s0 * (1 + strike_offset_pct / 100.0)
        legs = [
            {"type": "stock", "action": "BUY", "strike": s0, "qty": contracts},
            {"type": "call", "action": "SELL", "strike": k_call, "qty": contracts}
        ]

    # Prezzatura delle gambe e aggregazione greche
    total_net_cost = 0.0
    agg_delta = 0.0
    agg_gamma = 0.0
    agg_theta = 0.0
    agg_vega = 0.0

    legs_enriched = []
    for leg in legs:
        l_type = leg["type"]
        l_act = leg["action"]
        k = leg["strike"]
        sign = 1 if l_act == "BUY" else -1

        if l_type == "stock":
            px = s0
            d = 1.0
            g, th, v = 0.0, 0.0, 0.0
        else:
            bs = _bs_price_and_greeks(s0, k, t_years, risk_free_rate, iv, l_type)
            px = bs["price"]
            d, g, th, v = bs["delta"], bs["gamma"], bs["theta"], bs["vega"]

        net_px = sign * px
        total_net_cost += net_px * multiplier
        agg_delta += sign * d * multiplier
        agg_gamma += sign * g * multiplier
        agg_theta += sign * th * multiplier
        agg_vega += sign * v * multiplier

        legs_enriched.append({
            "leg_type": l_type.upper(),
            "action": l_act,
            "strike_eur": round(k, 2),
            "premium_unit_eur": round(px, 2),
            "delta": round(d * sign, 3),
            "gamma": round(g * sign, 4),
            "theta": round(th * sign, 2),
            "vega": round(v * sign, 2)
        })

    # Range prezzi spot per il payoff (da -30% a +30%)
    spots = np.linspace(s0 * 0.70, s0 * 1.30, 80)
    payoffs_expiry = []
    payoffs_mid = []

    t_mid = t_years / 2.0

    for s in spots:
        pnl_exp = 0.0
        pnl_mid = 0.0
        for leg in legs:
            l_type = leg["type"]
            l_act = leg["action"]
            k = leg["strike"]
            sign = 1 if l_act == "BUY" else -1

            if l_type == "stock":
                val_exp = s - s0
                val_mid = s - s0
            elif l_type == "call":
                val_exp = max(0.0, s - k) - (_bs_price_and_greeks(s0, k, t_years, risk_free_rate, iv, "call")["price"])
                val_mid = (_bs_price_and_greeks(s, k, t_mid, risk_free_rate, iv, "call")["price"]) - (_bs_price_and_greeks(s0, k, t_years, risk_free_rate, iv, "call")["price"])
            else:
                val_exp = max(0.0, k - s) - (_bs_price_and_greeks(s0, k, t_years, risk_free_rate, iv, "put")["price"])
                val_mid = (_bs_price_and_greeks(s, k, t_mid, risk_free_rate, iv, "put")["price"]) - (_bs_price_and_greeks(s0, k, t_years, risk_free_rate, iv, "put")["price"])

            pnl_exp += sign * val_exp * multiplier
            pnl_mid += sign * val_mid * multiplier

        payoffs_expiry.append(pnl_exp)
        payoffs_mid.append(pnl_mid)

    df_payoff = pd.DataFrame({
        "spot_price": spots,
        "pnl_expiry_eur": payoffs_expiry,
        "pnl_mid_term_eur": payoffs_mid
    })

    max_profit = float(np.max(payoffs_expiry))
    max_loss = float(np.min(payoffs_expiry))

    # Individuazione Breakevens
    zero_crossings = []
    for i in range(len(payoffs_expiry) - 1):
        if (payoffs_expiry[i] <= 0 and payoffs_expiry[i+1] > 0) or (payoffs_expiry[i] >= 0 and payoffs_expiry[i+1] < 0):
            zero_crossings.append(round(spots[i], 2))

    return {
        "strategy_name": strategy_name,
        "underlying_price": s0,
        "days_to_expiration": days_to_exp,
        "net_debit_credit_eur": round(total_net_cost, 2),
        "is_credit_strategy": total_net_cost < 0,
        "max_profit_eur": round(max_profit, 2),
        "max_loss_eur": round(max_loss, 2),
        "breakeven_points": zero_crossings,
        "greeks": {
            "net_delta": round(agg_delta, 2),
            "net_gamma": round(agg_gamma, 4),
            "net_theta_per_day": round(agg_theta, 2),
            "net_vega_per_pct": round(agg_vega, 2)
        },
        "legs": legs_enriched,
        "payoff_df": df_payoff
    }
