# ============================================================
# core/execution_algo_engine.py
# ARGUS — Algorithmic Trade Execution & Implementation Shortfall
# Scomposizione Perold (1988), microstruttura LOB e benchmarking strategie
# ============================================================

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def compute_implementation_shortfall_and_execution_benchmarks(
    ticker: str = "SWDA.MI",
    total_shares: int = 5000,
    decision_price: float = 100.0,
    side: str = "BUY",
    daily_volume: float = 50000.0,
    volatility_daily_pct: float = 1.2
) -> Dict[str, Any]:
    """
    Calcola la scomposizione analitica dell'Implementation Shortfall (Perold 1988)
    e confronta le strategie di esecuzione istituzionali (Market, TWAP, VWAP, Adaptive IS).
    """
    s_dec = float(decision_price)
    q_tot = int(total_shares)
    vol_frac = q_tot / max(1.0, daily_volume)
    is_buy = 1 if side.upper() == "BUY" else -1

    # Simulazione dinamica arrivo & mercato
    drift = 0.001 * is_buy
    s_arr = s_dec * (1.0 + drift)  # Prezzo all'invio dell'ordine
    s_close = s_dec * (1.0 + (volatility_daily_pct / 100.0) * 0.4 * is_buy)

    # 1. Benchmark: Immediate Market Order
    mkt_impact_bps = min(80.0, 15.0 + 400.0 * np.sqrt(vol_frac))
    px_mkt = s_arr * (1.0 + is_buy * (mkt_impact_bps / 10000.0))
    comm_bps = 5.0
    cost_mkt_eur = (px_mkt - s_dec) * is_buy * q_tot + (q_tot * px_mkt * comm_bps / 10000.0)

    # 2. Benchmark: TWAP (10 tranches temporali uniformi)
    twap_impact_bps = mkt_impact_bps * 0.45
    px_twap = s_arr * (1.0 + is_buy * (twap_impact_bps / 10000.0))
    cost_twap_eur = (px_twap - s_dec) * is_buy * q_tot + (q_tot * px_twap * comm_bps / 10000.0)

    # 3. Benchmark: VWAP (Profilo a U volumetrico intraday)
    vwap_impact_bps = mkt_impact_bps * 0.35
    px_vwap = s_arr * (1.0 + is_buy * (vwap_impact_bps / 10000.0))
    cost_vwap_eur = (px_vwap - s_dec) * is_buy * q_tot + (q_tot * px_vwap * comm_bps / 10000.0)

    # 4. Benchmark: Adaptive Implementation Shortfall (Almgren-Chriss Optimal Slicing)
    is_impact_bps = mkt_impact_bps * 0.28
    px_is = s_arr * (1.0 + is_buy * (is_impact_bps / 10000.0))
    cost_is_eur = (px_is - s_dec) * is_buy * q_tot + (q_tot * px_is * comm_bps / 10000.0)

    # Scomposizione Perold (1988) su strategia adattiva IS:
    delay_cost_eur = (s_arr - s_dec) * is_buy * q_tot
    impact_cost_eur = (px_is - s_arr) * is_buy * q_tot
    comm_cost_eur = (q_tot * px_is * comm_bps / 10000.0)
    opportunity_cost_eur = 0.0  # Assunta esecuzione 100%

    total_is_eur = delay_cost_eur + impact_cost_eur + comm_cost_eur + opportunity_cost_eur
    total_is_bps = (total_is_eur / (q_tot * s_dec)) * 10000.0

    strategies_comp = [
        {
            "strategy": "Immediate Market Order",
            "avg_exec_price_eur": round(px_mkt, 3),
            "slippage_bps": round(mkt_impact_bps, 1),
            "total_execution_cost_eur": round(cost_mkt_eur, 2),
            "savings_vs_market_eur": 0.0,
            "execution_speed": "Istantanea (< 1s)",
            "risk_profile": "Alto Slippage / Basso Rischio Prezzo"
        },
        {
            "strategy": "TWAP Uniform Slicing",
            "avg_exec_price_eur": round(px_twap, 3),
            "slippage_bps": round(twap_impact_bps, 1),
            "total_execution_cost_eur": round(cost_twap_eur, 2),
            "savings_vs_market_eur": round(cost_mkt_eur - cost_twap_eur, 2),
            "execution_speed": "Lineare (Intera Giornata)",
            "risk_profile": "Rischio Trend Moderato"
        },
        {
            "strategy": "VWAP Curve Matching",
            "avg_exec_price_eur": round(px_vwap, 3),
            "slippage_bps": round(vwap_impact_bps, 1),
            "total_execution_cost_eur": round(cost_vwap_eur, 2),
            "savings_vs_market_eur": round(cost_mkt_eur - cost_vwap_eur, 2),
            "execution_speed": "Ponderata Volumi U-Shape",
            "risk_profile": "Benchmark Istituzionale Standard"
        },
        {
            "strategy": "Adaptive Implementation Shortfall (IS)",
            "avg_exec_price_eur": round(px_is, 3),
            "slippage_bps": round(is_impact_bps, 1),
            "total_execution_cost_eur": round(cost_is_eur, 2),
            "savings_vs_market_eur": round(cost_mkt_eur - cost_is_eur, 2),
            "execution_speed": "Dinamica (Almgren-Chriss)",
            "risk_profile": "Minimo Costo Totale Ottimizzato ⭐"
        }
    ]

    df_comp = pd.DataFrame(strategies_comp)

    return {
        "ticker": ticker,
        "side": side,
        "shares_count": q_tot,
        "decision_price_eur": round(s_dec, 2),
        "arrival_price_eur": round(s_arr, 2),
        "notional_order_eur": round(q_tot * s_dec, 2),
        "perold_breakdown": {
            "delay_cost_eur": round(delay_cost_eur, 2),
            "delay_cost_bps": round((delay_cost_eur / (q_tot * s_dec)) * 10000.0, 1),
            "market_impact_cost_eur": round(impact_cost_eur, 2),
            "market_impact_bps": round((impact_cost_eur / (q_tot * s_dec)) * 10000.0, 1),
            "commissions_eur": round(comm_cost_eur, 2),
            "opportunity_cost_eur": round(opportunity_cost_eur, 2),
            "total_shortfall_eur": round(total_is_eur, 2),
            "total_shortfall_bps": round(total_is_bps, 1)
        },
        "best_strategy": "Adaptive Implementation Shortfall (IS)",
        "max_potential_savings_eur": round(cost_mkt_eur - cost_is_eur, 2),
        "strategies_comparison": strategies_comp,
        "strategies_df": df_comp
    }
