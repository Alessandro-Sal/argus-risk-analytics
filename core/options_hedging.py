# ============================================================
# core/options_hedging.py
# ARGUS — Risk Analytics & BI Platform
# Black-Scholes Model, Option Greeks & Portfolio Delta Hedging
# ============================================================

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import scipy.stats as stats
from core.yield_curve import get_default_risk_free_rate, get_active_risk_free_rate


def black_scholes_pricing(
    S: float,
    K: float,
    T: float,
    r: float = None,
    sigma: float = 0.20,
    option_type: str = "put"
) -> Dict[str, Any]:
    """
    Calcola il prezzo analitico e i 5 Greci di un'opzione Europea secondo il modello di Black-Scholes-Merton (1973).

    Parametri:
    - S: Prezzo spot sottostante
    - K: Strike price
    - T: Tempo alla scadenza in anni (es. 0.25 per 3 mesi)
    - r: Tasso d'interesse privo di rischio annuale (se None, recuperato dinamicamente)
    - sigma: Volatilità implicita annualizzata (es. 0.20 per 20%)
    - option_type: 'call' o 'put'
    """
    if r is None:
        r = get_default_risk_free_rate("USD")

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
    risk_free_rate: float = None,
    use_skew_calibration: bool = True
) -> Dict[str, Any]:
    """
    Calcola la strategia ottimale di Delta-Hedging con opzioni Put sul benchmark (es. SPY / SPX)
    per proteggere il valore del portafoglio azionario, supportando la calibrazione dello Skew reale.
    """
    if risk_free_rate is None:
        risk_free_rate = get_default_risk_free_rate("USD")

    T = expiry_months / 12.0
    K = benchmark_spot * (1.0 - (strike_otm_pct / 100.0))  # Strike OTM

    # Calcolo IV con o senza Volatility Skew
    if use_skew_calibration:
        from core.volatility_surface import build_volatility_surface
        surface = build_volatility_surface(spot=benchmark_spot, r=risk_free_rate, base_atm_iv=implied_vol)
        m_key = f"{int(round(expiry_months))}M" if f"{int(round(expiry_months))}M" in surface["smile_models"] else "3M"
        smile_model = surface["smile_models"].get(m_key, list(surface["smile_models"].values())[0])
        effective_iv = smile_model["eval_func"](K)
    else:
        effective_iv = implied_vol

    # Prezzatura Put con IV effettiva
    put_metrics = black_scholes_pricing(
        S=benchmark_spot,
        K=K,
        T=T,
        r=risk_free_rate,
        sigma=effective_iv,
        option_type="put"
    )

    # Prezzatura Put piatta per confronto
    flat_put_metrics = black_scholes_pricing(
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

    # Calcolo costo piatto teorico per confronto
    flat_contracts = int(np.ceil(portfolio_delta_euros / max(1.0, benchmark_spot * contract_multiplier * abs(flat_put_metrics["delta"])))) if abs(flat_put_metrics["delta"]) > 0 else 0
    flat_total_cost = flat_contracts * flat_put_metrics["price"] * contract_multiplier
    skew_cost_premium_eur = total_hedge_cost - flat_total_cost

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
        "protected_value": float(portfolio_value * (target_hedge_pct / 100.0)),
        "risk_free_rate_pct": round(risk_free_rate * 100.0, 2),
        "effective_iv_pct": float(effective_iv * 100.0),
        "base_atm_iv_pct": float(implied_vol * 100.0),
        "skew_spread_iv_pct": float((effective_iv - implied_vol) * 100.0),
        "flat_put_price": float(flat_put_metrics["price"]),
        "flat_total_cost": float(flat_total_cost),
        "skew_cost_premium_eur": float(skew_cost_premium_eur),
        "use_skew_calibration": use_skew_calibration
    }


def compute_covered_call_yield_enhancement(
    positions_df: pd.DataFrame,
    otm_pct: float = 5.0,
    expiry_months: float = 1.0,
    implied_vol: float = 0.25,
    risk_free_rate: float = None,
    use_skew_calibration: bool = True,
    contract_multiplier: int = 100,
    vol_map: Optional[dict] = None
) -> pd.DataFrame:
    """
    Calcola la strategia di Covered Call Writing (vendita di Call Out-of-The-Money) per generare
    rendimento passivo (premio opzioni) su ciascuna posizione azionaria in portafoglio,
    supportando sia il modello frazionario teorico sia la discretizzazione a contratti eseguibili interi (es. 100 azioni/contratto).
    """
    if risk_free_rate is None:
        risk_free_rate = get_default_risk_free_rate("USD")

    if positions_df.empty or "last_price" not in positions_df.columns:
        return pd.DataFrame()

    results = []
    T = expiry_months / 12.0
    v_map = vol_map or {}

    for _, row in positions_df[positions_df["qty_net"] > 0].iterrows():
        ticker = row.get("ticker", "N/A")
        price = float(row.get("last_price", 0.0) or 0.0)
        qty = float(row.get("qty_net", 0.0) or 0.0)

        if price <= 0 or qty <= 0:
            continue

        asset_base_iv = float(v_map.get(ticker, implied_vol))
        if asset_base_iv <= 0.01:
            asset_base_iv = implied_vol

        K = price * (1.0 + (otm_pct / 100.0))

        if use_skew_calibration:
            from core.volatility_surface import build_volatility_surface
            surf_asset = build_volatility_surface(spot=price, r=risk_free_rate, base_atm_iv=asset_base_iv)
            smile_model = surf_asset["smile_models"].get("1M", list(surf_asset["smile_models"].values())[0])
            effective_call_iv = smile_model["eval_func"](K)
        else:
            effective_call_iv = asset_base_iv

        call_res = black_scholes_pricing(S=price, K=K, T=T, r=risk_free_rate, sigma=effective_call_iv, option_type="call")

        call_premium_per_share = call_res["price"]
        total_premium_income = call_premium_per_share * qty
        monthly_yield_pct = (call_premium_per_share / price) * 100.0
        annualized_yield_pct = monthly_yield_pct * (12.0 / expiry_months)

        # Discretizzazione contratti eseguibili reali (multiplo di 100)
        contracts_tradable = int(qty // max(1, contract_multiplier))
        covered_shares = contracts_tradable * contract_multiplier
        uncovered_shares = max(0.0, qty - covered_shares)
        executable_premium_income = contracts_tradable * call_premium_per_share * contract_multiplier

        results.append({
            "ticker": ticker,
            "quantita_totale": qty,
            "prezzo_spot": price,
            "strike_call_otm": K,
            "iv_effettiva_pct": effective_call_iv * 100.0,
            "premio_per_azione": call_premium_per_share,
            "incasso_premio_totale": total_premium_income,
            "contratti_eseguibili": contracts_tradable,
            "quote_coperte": covered_shares,
            "quote_scoperte": uncovered_shares,
            "incasso_eseguibile_eur": executable_premium_income,
            "extra_rendimento_mensile_pct": monthly_yield_pct,
            "extra_rendimento_annuo_pct": annualized_yield_pct,
            "delta_call": call_res["delta"]
        })

    return pd.DataFrame(results)
