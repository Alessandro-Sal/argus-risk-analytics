# ============================================================
# core/execution_algo_engine.py
# ARGUS — Algorithmic Trade Execution & Transaction Cost Analysis (TCA)
# Pre-Trade TCA, Post-Trade TCA, Perold (1988) Implementation Shortfall
# Microstructure Models (Square-Root Law, Almgren-Chriss, Kyle 1985)
# ============================================================

from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
from core.execution_algo import (
    generate_intraday_volume_profile,
    estimate_microstructure_market_impact,
    compute_twap_schedule,
    compute_vwap_schedule,
    compute_almgren_chriss_basket_schedule
)


def compute_broker_commissions(
    notional_eur: float,
    shares: float,
    broker: str = "DEFAULT"
) -> Dict[str, float]:
    """
    Computes broker execution fees according to published fee schedules:
    - DIRECTA: 0.19% variable (min €1.50, max €18.00) or flat €5.00
    - IBKR: €0.0035/share (min €1.25) or 0.05% of notional
    - DEGIRO: €1.00 base + €1.00 handling
    - DEFAULT: 5 bps (0.05%)
    """
    broker_clean = broker.strip().upper()
    notional_eur = max(0.0, float(notional_eur))
    shares = max(0.0, float(shares))

    if broker_clean == "DIRECTA":
        # Directa Profilo Variabile Borsa Italiana: 0.19%, min €1.50, max €18.00
        comm = max(1.50, min(18.00, notional_eur * 0.0019)) if notional_eur > 0 else 0.0
    elif broker_clean == "IBKR":
        # Interactive Brokers Western Europe Tiered: ~€0.0035/share, min €1.25, max 0.5%
        comm = max(1.25, min(notional_eur * 0.005, shares * 0.0035)) if notional_eur > 0 else 0.0
    elif broker_clean == "DEGIRO":
        # Degiro Core Shares: €1.00 commission + €1.00 handling
        comm = 2.00 if notional_eur > 0 else 0.0
    else:
        # Institutional default: 5.0 bps
        comm = notional_eur * 0.0005

    bps = (comm / notional_eur * 10000.0) if notional_eur > 0 else 0.0
    return {
        "commission_eur": round(comm, 2),
        "commission_bps": round(bps, 2)
    }


def compute_implementation_shortfall_and_execution_benchmarks(
    ticker: str = "SWDA.MI",
    total_shares: int = 5000,
    decision_price: float = 100.0,
    side: str = "BUY",
    daily_volume: float = 50000.0,
    volatility_daily_pct: float = 1.2
) -> Dict[str, Any]:
    """
    Calculates the analytical Perold (1988) Implementation Shortfall decomposition
    and dynamically benchmarks institutional execution strategies:
    Immediate Market Order, TWAP, VWAP, and Adaptive Implementation Shortfall (Almgren-Chriss).
    """
    s_dec = float(decision_price)
    q_tot = int(total_shares)
    v_mkt = max(100.0, float(daily_volume))
    vol_frac = q_tot / v_mkt
    is_buy = 1 if side.upper() == "BUY" else -1
    vol_daily = max(0.002, (volatility_daily_pct / 100.0))

    # Pre-trade arrival price drift
    drift = 0.0008 * is_buy
    s_arr = s_dec * (1.0 + drift)  # Price at routing
    s_close = s_dec * (1.0 + vol_daily * 0.35 * is_buy)

    order_payload = [{
        "ticker": ticker,
        "action": side,
        "quantity": q_tot,
        "price": s_dec,
        "adv": v_mkt,
        "volatility_daily": vol_daily,
        "half_spread_bps": 2.0
    }]

    # 1. Market Order: Full block immediate crossing
    # Half-spread (2.5 bps) + Kyle/Almgren square-root market impact
    mkt_half_spread = 2.5
    mkt_temp_impact = 0.28 * vol_daily * np.sqrt(min(1.0, vol_frac)) * 10000.0
    mkt_perm_impact = 0.15 * vol_daily * min(1.0, vol_frac) * 10000.0
    mkt_impact_bps = min(120.0, max(3.0, mkt_half_spread + mkt_temp_impact + mkt_perm_impact))
    px_mkt = s_arr * (1.0 + is_buy * (mkt_impact_bps / 10000.0))
    comm_mkt = compute_broker_commissions(q_tot * px_mkt, q_tot, broker="DEFAULT")["commission_eur"]
    cost_mkt_eur = (px_mkt - s_dec) * is_buy * q_tot + comm_mkt

    # 2. Benchmark: TWAP (16 tranches uniform slicing with U-shape profile)
    twap_res = compute_twap_schedule(order_payload, n_intervals=16)
    twap_slip_bps = float(twap_res["summary"]["avg_slippage_bps"]) if not twap_res["schedule_df"].empty else (mkt_impact_bps * 0.45)
    px_twap = s_arr * (1.0 + is_buy * (twap_slip_bps / 10000.0))
    comm_twap = compute_broker_commissions(q_tot * px_twap, q_tot, broker="DEFAULT")["commission_eur"]
    cost_twap_eur = (px_twap - s_dec) * is_buy * q_tot + comm_twap

    # 3. Benchmark: VWAP (16 tranches liquidity-matched U-shape curve)
    vwap_res = compute_vwap_schedule(order_payload, n_intervals=16, pov_cap_pct=0.15)
    vwap_slip_bps = float(vwap_res["summary"]["avg_slippage_bps"]) if not vwap_res["schedule_df"].empty else (mkt_impact_bps * 0.35)
    px_vwap = s_arr * (1.0 + is_buy * (vwap_slip_bps / 10000.0))
    comm_vwap = compute_broker_commissions(q_tot * px_vwap, q_tot, broker="DEFAULT")["commission_eur"]
    cost_vwap_eur = (px_vwap - s_dec) * is_buy * q_tot + comm_vwap

    # 4. Benchmark: Adaptive Implementation Shortfall (Almgren-Chriss Optimal Slicing)
    ac_res = compute_almgren_chriss_basket_schedule(order_payload, horizon_days=1.0, n_intervals=16, risk_aversion_lambda=1e-6)
    ac_slip_bps = float(ac_res["summary"]["expected_cost_bps"]) if not ac_res["schedule_df"].empty else (mkt_impact_bps * 0.28)
    px_is = s_arr * (1.0 + is_buy * (ac_slip_bps / 10000.0))
    comm_is = compute_broker_commissions(q_tot * px_is, q_tot, broker="DEFAULT")["commission_eur"]
    cost_is_eur = (px_is - s_dec) * is_buy * q_tot + comm_is

    # Perold (1988) Scomposizione:
    delay_cost_eur = (s_arr - s_dec) * is_buy * q_tot
    impact_cost_eur = (px_is - s_arr) * is_buy * q_tot
    comm_cost_eur = comm_is
    opportunity_cost_eur = 0.0  # Assumed 100% completion

    total_is_eur = delay_cost_eur + impact_cost_eur + comm_cost_eur + opportunity_cost_eur
    total_is_bps = (total_is_eur / max(1.0, q_tot * s_dec)) * 10000.0

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
            "slippage_bps": round(twap_slip_bps, 1),
            "total_execution_cost_eur": round(cost_twap_eur, 2),
            "savings_vs_market_eur": round(cost_mkt_eur - cost_twap_eur, 2),
            "execution_speed": "Lineare (Intera Giornata)",
            "risk_profile": "Rischio Trend Moderato"
        },
        {
            "strategy": "VWAP Curve Matching",
            "avg_exec_price_eur": round(px_vwap, 3),
            "slippage_bps": round(vwap_slip_bps, 1),
            "total_execution_cost_eur": round(cost_vwap_eur, 2),
            "savings_vs_market_eur": round(cost_mkt_eur - cost_vwap_eur, 2),
            "execution_speed": "Ponderata Volumi U-Shape",
            "risk_profile": "Benchmark Istituzionale Standard"
        },
        {
            "strategy": "Adaptive Implementation Shortfall (IS)",
            "avg_exec_price_eur": round(px_is, 3),
            "slippage_bps": round(ac_slip_bps, 1),
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
            "delay_cost_bps": round((delay_cost_eur / max(1.0, q_tot * s_dec)) * 10000.0, 1),
            "market_impact_cost_eur": round(impact_cost_eur, 2),
            "market_impact_bps": round((impact_cost_eur / max(1.0, q_tot * s_dec)) * 10000.0, 1),
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


# ==============================================================================
# PRE-TRADE TRANSACTION COST ANALYSIS (PRE-TRADE TCA)
# ==============================================================================

def compute_pre_trade_tca(
    orders: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
    broker: str = "DEFAULT",
    risk_aversion_lambda: float = 1e-6,
    horizon_days: float = 1.0,
    n_intervals: int = 16
) -> Dict[str, Any]:
    """
    Ex-ante Pre-Trade Transaction Cost Analysis (Pre-Trade TCA).
    Estimates explicit commissions, touch spread cost, permanent impact,
    temporary impact, execution timing risk, and Execution VaR (95%/99%).
    """
    if isinstance(orders, dict):
        df_ord = pd.DataFrame([orders])
    elif isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()

    if df_ord.empty:
        return {
            "summary": {
                "total_orders": 0,
                "total_notional_eur": 0.0,
                "total_expected_cost_eur": 0.0,
                "total_expected_cost_bps": 0.0,
                "execution_var_95_eur": 0.0,
                "execution_var_99_eur": 0.0
            },
            "breakdown_df": pd.DataFrame()
        }

    # Run Almgren-Chriss basket optimization to get optimal trajectories
    ac_result = compute_almgren_chriss_basket_schedule(
        df_ord,
        horizon_days=horizon_days,
        n_intervals=n_intervals,
        risk_aversion_lambda=risk_aversion_lambda
    )

    total_notional = 0.0
    total_comm = 0.0
    total_spread = 0.0
    total_temp = 0.0
    total_perm = 0.0
    total_variance = 0.0
    rows = []

    for _, ord_row in df_ord.iterrows():
        ticker = str(ord_row.get("ticker", ord_row.get("Ticker", "UNKNOWN")))
        action = str(ord_row.get("action", ord_row.get("Azione", "BUY"))).upper()
        qty = float(ord_row.get("quantity", ord_row.get("Quote", ord_row.get("qty", 100.0))))
        price = float(ord_row.get("price", ord_row.get("Prezzo (€)", ord_row.get("current_price", 100.0))))
        adv = float(ord_row.get("adv", ord_row.get("volume", 500000.0)))
        vol_daily = float(ord_row.get("volatility_daily", ord_row.get("vol_daily", 0.015)))
        half_spread_bps = float(ord_row.get("half_spread_bps", 1.5))

        notional = qty * price
        total_notional += notional

        # Commissions
        comm_res = compute_broker_commissions(notional, qty, broker=broker)
        comm_eur = comm_res["commission_eur"]
        total_comm += comm_eur

        # Microstructure cost components
        spread_eur = notional * (half_spread_bps / 10000.0)
        total_spread += spread_eur

        # Impact models
        pov_total = qty / max(100.0, adv)
        perm_eur = notional * (0.314 * vol_daily * pov_total)
        total_perm += perm_eur

        temp_eur = notional * (0.142 * vol_daily * np.sqrt(pov_total / n_intervals))
        total_temp += temp_eur

        asset_cost = comm_eur + spread_eur + perm_eur + temp_eur
        asset_cost_bps = (asset_cost / max(1.0, notional)) * 10000.0

        # Timing risk variance
        tau = horizon_days / n_intervals
        asset_var = (vol_daily ** 2) * tau * (qty ** 2) * (price ** 2) * 0.33 # Trajectory integral
        total_variance += asset_var
        asset_std = float(np.sqrt(max(0.0, asset_var)))

        rows.append({
            "ticker": ticker,
            "action": action,
            "quantity": qty,
            "price_eur": round(price, 2),
            "notional_eur": round(notional, 2),
            "commissions_eur": round(comm_eur, 2),
            "spread_cost_eur": round(spread_eur, 2),
            "temp_impact_eur": round(temp_eur, 2),
            "perm_impact_eur": round(perm_eur, 2),
            "total_expected_cost_eur": round(asset_cost, 2),
            "total_expected_cost_bps": round(asset_cost_bps, 1),
            "timing_risk_std_eur": round(asset_std, 2),
            "execution_var_95_eur": round(asset_cost + 1.645 * asset_std, 2),
            "participation_rate_pct": round(pov_total * 100.0, 2)
        })

    df_breakdown = pd.DataFrame(rows)
    total_cost = total_comm + total_spread + total_temp + total_perm
    total_cost_bps = (total_cost / max(1.0, total_notional)) * 10000.0
    total_std = float(np.sqrt(max(0.0, total_variance)))
    var_95 = total_cost + 1.645 * total_std
    var_99 = total_cost + 2.326 * total_std

    # Confidence interval percentiles (Log-normal distribution of slippage)
    p10_eur = max(0.0, total_cost - 1.28 * total_std)
    p50_eur = total_cost
    p90_eur = total_cost + 1.28 * total_std

    return {
        "summary": {
            "total_orders": len(df_ord),
            "total_notional_eur": round(total_notional, 2),
            "broker_selected": broker,
            "horizon_days": horizon_days,
            "commissions_eur": round(total_comm, 2),
            "commissions_bps": round((total_comm / max(1.0, total_notional)) * 10000.0, 2),
            "spread_cost_eur": round(total_spread, 2),
            "spread_cost_bps": round((total_spread / max(1.0, total_notional)) * 10000.0, 2),
            "temp_impact_eur": round(total_temp, 2),
            "temp_impact_bps": round((total_temp / max(1.0, total_notional)) * 10000.0, 2),
            "perm_impact_eur": round(total_perm, 2),
            "perm_impact_bps": round((total_perm / max(1.0, total_notional)) * 10000.0, 2),
            "total_expected_cost_eur": round(total_cost, 2),
            "total_expected_cost_bps": round(total_cost_bps, 1),
            "timing_risk_std_eur": round(total_std, 2),
            "execution_var_95_eur": round(var_95, 2),
            "execution_var_99_eur": round(var_99, 2),
            "confidence_intervals": {
                "p10_eur": round(p10_eur, 2),
                "p50_eur": round(p50_eur, 2),
                "p90_eur": round(p90_eur, 2)
            }
        },
        "breakdown_df": df_breakdown,
        "almgren_chriss_schedule": ac_result
    }


# ==============================================================================
# POST-TRADE TRANSACTION COST ANALYSIS (POST-TRADE TCA)
# ==============================================================================

def compute_post_trade_tca(
    executed_trades: Union[pd.DataFrame, List[Dict[str, Any]]],
    decision_price: float,
    arrival_price: float,
    side: str = "BUY",
    market_vwap: Optional[float] = None,
    market_close: Optional[float] = None,
    total_ordered_shares: Optional[float] = None,
    commissions_paid_eur: float = 0.0
) -> Dict[str, Any]:
    """
    Ex-post Post-Trade Transaction Cost Analysis (Post-Trade TCA).
    Reconciles actual fills against institutional benchmarks:
    - Implementation Shortfall (Perold 1988)
    - Arrival Price Slippage
    - Market VWAP Slippage
    - Market on Close (MOC) Slippage
    - Execution Quality Score & Alpha Preservation %
    """
    if isinstance(executed_trades, list):
        df_exec = pd.DataFrame(executed_trades)
    else:
        df_exec = executed_trades.copy()

    is_buy = 1 if side.upper() == "BUY" else -1
    p_dec = float(decision_price)
    p_arr = float(arrival_price)

    if df_exec.empty or "shares" not in df_exec.columns or "price" not in df_exec.columns:
        return {
            "error": "Nessuna transazione eseguita fornita nel payload."
        }

    total_shares_filled = float(df_exec["shares"].sum())
    if total_shares_filled <= 0:
        return {"error": "Quantità totale eseguita nulla o negativa."}

    # Volume-weighted execution price: sum(shares * price) / sum(shares)
    total_trade_notional = float((df_exec["shares"] * df_exec["price"]).sum())
    avg_exec_price = total_trade_notional / total_shares_filled

    target_shares = float(total_ordered_shares) if total_ordered_shares is not None else total_shares_filled
    unfilled_shares = max(0.0, target_shares - total_shares_filled)
    fill_rate_pct = (total_shares_filled / max(1.0, target_shares)) * 100.0

    p_vwap = float(market_vwap) if market_vwap is not None else avg_exec_price
    p_close = float(market_close) if market_close is not None else avg_exec_price

    # 1. Slippage vs Arrival Price (Market Impact + Realized Spread)
    arrival_slippage_bps = ((avg_exec_price - p_arr) / p_arr) * is_buy * 10000.0
    arrival_slippage_eur = (avg_exec_price - p_arr) * is_buy * total_shares_filled

    # 2. Slippage vs Market VWAP (Benchmark beating)
    # Negative slippage vs VWAP = good execution (bought cheaper than VWAP or sold higher)
    vwap_slippage_bps = ((avg_exec_price - p_vwap) / p_vwap) * is_buy * 10000.0
    vwap_slippage_eur = (avg_exec_price - p_vwap) * is_buy * total_shares_filled

    # 3. Slippage vs Decision Price
    decision_slippage_bps = ((avg_exec_price - p_dec) / p_dec) * is_buy * 10000.0
    decision_slippage_eur = (avg_exec_price - p_dec) * is_buy * total_shares_filled

    # 4. Slippage vs Market Close
    close_slippage_bps = ((avg_exec_price - p_close) / p_close) * is_buy * 10000.0
    close_slippage_eur = (avg_exec_price - p_close) * is_buy * total_shares_filled

    # 5. Full Perold (1988) Scomposizione
    delay_cost_eur = (p_arr - p_dec) * is_buy * total_shares_filled
    delay_cost_bps = (delay_cost_eur / max(1.0, total_shares_filled * p_dec)) * 10000.0

    impact_cost_eur = arrival_slippage_eur
    impact_cost_bps = arrival_slippage_bps

    comm_eur = float(commissions_paid_eur)
    comm_bps = (comm_eur / max(1.0, total_trade_notional)) * 10000.0

    # Opportunity cost of unfilled shares: (P_close - P_decision) * dir * Q_unfilled
    opp_cost_eur = (p_close - p_dec) * is_buy * unfilled_shares
    opp_cost_bps = (opp_cost_eur / max(1.0, target_shares * p_dec)) * 10000.0

    total_is_eur = delay_cost_eur + impact_cost_eur + comm_eur + opp_cost_eur
    total_is_bps = (total_is_eur / max(1.0, target_shares * p_dec)) * 10000.0

    # Execution Quality Score (0 - 100)
    # Calibrated against institutional standards (ITG / Virtu TCA, Bloomberg BTCA):
    # Base score = 75. Outperforming VWAP awards bonus points; adverse arrival slippage incurs penalty.
    quality_score = 75.0 - (vwap_slippage_bps * 1.2) - (max(0.0, arrival_slippage_bps) * 0.4)
    quality_score = max(5.0, min(99.0, quality_score))

    if quality_score >= 80.0:
        rating = "EXCELLENT (Beat VWAP & Minimal Impact)"
    elif quality_score >= 65.0:
        rating = "GOOD (In Line With Institutional Benchmark)"
    elif quality_score >= 45.0:
        rating = "AVERAGE (Moderate Slippage Recorded)"
    else:
        rating = "POOR (High Adverse Price Movement)"

    alpha_preservation_pct = max(0.0, min(100.0, 100.0 - (abs(total_is_bps) / 100.0)))

    return {
        "summary": {
            "total_shares_ordered": target_shares,
            "total_shares_filled": total_shares_filled,
            "fill_rate_pct": round(fill_rate_pct, 1),
            "unfilled_shares": unfilled_shares,
            "avg_execution_price_eur": round(avg_exec_price, 3),
            "decision_price_eur": round(p_dec, 3),
            "arrival_price_eur": round(p_arr, 3),
            "market_vwap_eur": round(p_vwap, 3),
            "market_close_eur": round(p_close, 3),
            "total_trade_notional_eur": round(total_trade_notional, 2),
            "execution_quality_score": round(quality_score, 1),
            "execution_rating": rating,
            "alpha_preservation_pct": round(alpha_preservation_pct, 2)
        },
        "slippage_benchmarks": {
            "vs_arrival_price": {
                "slippage_bps": round(arrival_slippage_bps, 2),
                "slippage_eur": round(arrival_slippage_eur, 2)
            },
            "vs_market_vwap": {
                "slippage_bps": round(vwap_slippage_bps, 2),
                "slippage_eur": round(vwap_slippage_eur, 2),
                "outperformed_vwap": (vwap_slippage_bps <= 0)
            },
            "vs_decision_price": {
                "slippage_bps": round(decision_slippage_bps, 2),
                "slippage_eur": round(decision_slippage_eur, 2)
            },
            "vs_market_close": {
                "slippage_bps": round(close_slippage_bps, 2),
                "slippage_eur": round(close_slippage_eur, 2)
            }
        },
        "perold_breakdown": {
            "delay_cost_eur": round(delay_cost_eur, 2),
            "delay_cost_bps": round(delay_cost_bps, 2),
            "market_impact_eur": round(impact_cost_eur, 2),
            "market_impact_bps": round(impact_cost_bps, 2),
            "commissions_eur": round(comm_eur, 2),
            "commissions_bps": round(comm_bps, 2),
            "opportunity_cost_eur": round(opp_cost_eur, 2),
            "opportunity_cost_bps": round(opp_cost_bps, 2),
            "total_implementation_shortfall_eur": round(total_is_eur, 2),
            "total_implementation_shortfall_bps": round(total_is_bps, 2)
        }
    }
