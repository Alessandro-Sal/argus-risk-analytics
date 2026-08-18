# ============================================================
# core/options_hedging.py
# ARGUS — Risk Analytics & BI Platform
# Black-Scholes Model, Option Greeks & Portfolio Delta Hedging
# ============================================================

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import scipy.stats as stats


def black_scholes_pricing(
    S: float,
    K: float,
    T: float,
    r: float = 0.035,
    sigma: float = 0.20,
    option_type: str = "put"
) -> Dict[str, Any]:
    """
    Calcola il prezzo analitico e i 5 Greci di un'opzione Europea secondo il modello di Black-Scholes-Merton (1973).

    Parametri:
    - S: Prezzo spot sottostante
    - K: Strike price
    - T: Tempo alla scadenza in anni (es. 0.25 per 3 mesi)
    - r: Tasso d'interesse privo di rischio annuale (es. 0.035 per 3.5%)
    - sigma: Volatilità implicita annualizzata (es. 0.20 per 20%)
    - option_type: 'call' o 'put'
    """
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {
            "price": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0
        }

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    pdf_d1 = stats.norm.pdf(d1)
    cdf_d1 = stats.norm.cdf(d1)
    cdf_d2 = stats.norm.cdf(d2)

    cdf_minus_d1 = stats.norm.cdf(-d1)
    cdf_minus_d2 = stats.norm.cdf(-d2)

    # 1. Prezzo Opzione
    if option_type.lower() == "call":
        price = float(S * cdf_d1 - K * np.exp(-r * T) * cdf_d2)
        delta = float(cdf_d1)
        rho = float(K * T * np.exp(-r * T) * cdf_d2 / 100.0)
        theta = float((- (S * pdf_d1 * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * cdf_d2) / 365.0)
    else:  # Put
        price = float(K * np.exp(-r * T) * cdf_minus_d2 - S * cdf_minus_d1)
        delta = float(cdf_d1 - 1.0)
        rho = float(- K * T * np.exp(-r * T) * cdf_minus_d2 / 100.0)
        theta = float((- (S * pdf_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * cdf_minus_d2) / 365.0)

    # Gamma e Vega sono identici per Call e Put
    gamma = float(pdf_d1 / (S * sigma * np.sqrt(T)))
    vega = float(S * pdf_d1 * np.sqrt(T) / 100.0)  # Variazione prezzo per 1% di volatilità

    return {
        "price": float(max(0.0, price)),
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "rho": rho,
        "d1": float(d1),
        "d2": float(d2)
    }


def compute_portfolio_delta_hedge(
    portfolio_value: float,
    portfolio_beta: float,
    benchmark_spot: float = 500.0,
    contract_multiplier: int = 100,
    target_hedge_pct: float = 100.0,
    strike_otm_pct: float = 5.0,
    expiry_months: float = 3.0,
    implied_vol: float = 0.18,
    risk_free_rate: float = 0.035
) -> Dict[str, Any]:
    """
    Calcola la strategia ottimale di Delta-Hedging con opzioni Put sul benchmark (es. SPY / SPX)
    per proteggere il valore del portafoglio azionario.
    """
    T = expiry_months / 12.0
    K = benchmark_spot * (1.0 - (strike_otm_pct / 100.0))  # Strike OTM

    put_metrics = black_scholes_pricing(
        S=benchmark_spot,
        K=K,
        T=T,
        r=risk_free_rate,
        sigma=implied_vol,
        option_type="put"
    )

    put_price = put_metrics["price"]
    put_delta = abs(put_metrics["delta"])  # Delta di una Put è negativo, prendiamo il modulo

    # Delta di portafoglio rispetto al benchmark
    portfolio_delta_euros = portfolio_value * portfolio_beta * (target_hedge_pct / 100.0)
    contract_notional_delta = benchmark_spot * contract_multiplier * put_delta

    contracts_needed = int(np.ceil(portfolio_delta_euros / max(1.0, contract_notional_delta))) if contract_notional_delta > 0 else 0
    total_hedge_cost = contracts_needed * put_price * contract_multiplier
    cost_pct_of_portfolio = (total_hedge_cost / max(1.0, portfolio_value)) * 100.0

    return {
        "contracts_needed": contracts_needed,
        "contract_multiplier": contract_multiplier,
        "strike_price": float(K),
        "put_price": float(put_price),
        "total_hedge_cost": float(total_hedge_cost),
        "cost_pct_of_portfolio": float(cost_pct_of_portfolio),
        "put_delta": float(put_metrics["delta"]),
        "put_gamma": float(put_metrics["gamma"]),
        "put_theta_daily": float(put_metrics["theta"]),
        "put_vega": float(put_metrics["vega"]),
        "protected_value": float(portfolio_value * (target_hedge_pct / 100.0))
    }


def compute_covered_call_yield_enhancement(
    positions_df: pd.DataFrame,
    otm_pct: float = 5.0,
    expiry_months: float = 1.0,
    implied_vol: float = 0.25,
    risk_free_rate: float = 0.035
) -> pd.DataFrame:
    """
    Calcola la strategia di Covered Call Writing (vendita di Call Out-of-The-Money) per generare
    rendimento passivo (premio opzioni) su ciascuna posizione azionaria in portafoglio.
    """
    if positions_df.empty or "last_price" not in positions_df.columns:
        return pd.DataFrame()

    results = []
    T = expiry_months / 12.0

    for _, row in positions_df[positions_df["qty_net"] > 0].iterrows():
        ticker = row.get("ticker", "N/A")
        price = float(row.get("last_price", 0.0) or 0.0)
        qty = float(row.get("qty_net", 0.0) or 0.0)

        if price <= 0 or qty <= 0:
            continue

        K = price * (1.0 + (otm_pct / 100.0))
        call_res = black_scholes_pricing(S=price, K=K, T=T, r=risk_free_rate, sigma=implied_vol, option_type="call")

        call_premium_per_share = call_res["price"]
        total_premium_income = call_premium_per_share * qty
        monthly_yield_pct = (call_premium_per_share / price) * 100.0
        annualized_yield_pct = monthly_yield_pct * (12.0 / expiry_months)

        results.append({
            "ticker": ticker,
            "prezzo_spot": price,
            "strike_call_otm": K,
            "premio_per_azione": call_premium_per_share,
            "incasso_premio_totale": total_premium_income,
            "extra_rendimento_mensile_pct": monthly_yield_pct,
            "extra_rendimento_annuo_pct": annualized_yield_pct,
            "delta_call": call_res["delta"]
        })

    return pd.DataFrame(results)
