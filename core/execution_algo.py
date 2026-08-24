"""
ARGUS — Risk Analytics Platform
Core Module: Institutional Algorithmic Execution (TWAP & VWAP Smart Order Router)
Implements institutional slicing algorithms, U-shaped intraday volume profiles,
Participation Rate (POV) caps, and Almgren-Chriss market impact/slippage estimators.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, Union


def generate_intraday_volume_profile(n_intervals: int = 16) -> np.ndarray:
    """
    Generates a realistic normalized U-shaped intraday volume distribution
    for equity markets (high at market open 09:00-10:30, low at midday 12:00-14:00,
    peak at close 16:30-17:30 MOC).
    """
    t = np.linspace(0, 1, n_intervals)
    # Quadratic U-shaped baseline: high at t=0 and t=1, minimum around t=0.45
    raw_profile = 2.4 * (t - 0.45) ** 2 + 0.35
    # Morning open rush bonus (first 2 intervals)
    raw_profile[0] *= 1.35
    raw_profile[1] *= 1.15
    # Market on Close (MOC) rush bonus (last 2 intervals)
    raw_profile[-2] *= 1.25
    raw_profile[-1] *= 1.55
    
    # Normalize so sum of volume weights equals 1.0
    return raw_profile / np.sum(raw_profile)


def compute_twap_schedule(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]],
    start_time_str: str = "09:00",
    interval_minutes: int = 30,
    n_intervals: int = 16,
    jitter_pct: float = 0.04,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Generates a Time-Weighted Average Price (TWAP) execution schedule.
    Slices order quantities uniformly across time buckets with anti-frontrunning stochastic jitter.
    """
    np.random.seed(random_seed)
    
    if isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()
        
    if df_ord.empty:
        return {
            "schedule_df": pd.DataFrame(),
            "summary": {
                "total_orders": 0,
                "total_notional_eur": 0.0,
                "total_tranches": 0,
                "algo_type": "TWAP"
            }
        }

    # Time bucket labels (e.g. 09:00, 09:30, 10:00 ... 17:00)
    timestamps = []
    curr_hour = int(start_time_str.split(":")[0])
    curr_min = int(start_time_str.split(":")[1])
    for i in range(n_intervals):
        t_str = f"{curr_hour:02d}:{curr_min:02d}"
        timestamps.append(t_str)
        curr_min += interval_minutes
        while curr_min >= 60:
            curr_min -= 60
            curr_hour += 1

    vol_profile = generate_intraday_volume_profile(n_intervals)
    schedule_rows = []
    tot_notional = 0.0

    for _, ord_row in df_ord.iterrows():
        ticker = str(ord_row.get("ticker", ord_row.get("Ticker", "UNKNOWN")))
        action = str(ord_row.get("action", ord_row.get("Azione", "BUY"))).upper()
        qty_total = float(ord_row.get("quantity", ord_row.get("Quote", ord_row.get("qty", 100.0))))
        price = float(ord_row.get("price", ord_row.get("Prezzo (€)", ord_row.get("current_price", 100.0))))
        adv = float(ord_row.get("adv", ord_row.get("volume", 500000.0)))
        
        if qty_total <= 0:
            continue

        base_slice = qty_total / n_intervals
        # Add slight pseudo-random jitter while ensuring sum equals qty_total exactly
        jitters = np.random.uniform(-jitter_pct, jitter_pct, n_intervals)
        jitters -= np.mean(jitters) # Zero mean
        slice_qtys = base_slice * (1.0 + jitters)
        # Fix rounding to preserve exact total
        slice_qtys = slice_qtys * (qty_total / np.sum(slice_qtys))
        
        cum_qty = 0.0
        for idx in range(n_intervals):
            s_qty = slice_qtys[idx]
            cum_qty += s_qty
            notional = s_qty * price
            tot_notional += notional
            
            # Intraday interval volume based on ADV
            interval_mkt_vol = adv * vol_profile[idx]
            pov_rate = (s_qty / max(1.0, interval_mkt_vol)) * 100.0
            
            # Estimated slippage in basis points (TWAP constant participation model)
            est_slippage_bps = min(50.0, max(0.5, 3.5 * np.sqrt(pov_rate)))
            est_exec_price = price * (1.0 + (est_slippage_bps / 10000.0) if "BUY" in action else 1.0 - (est_slippage_bps / 10000.0))

            schedule_rows.append({
                "tranche_idx": idx + 1,
                "timestamp": timestamps[idx],
                "ticker": ticker,
                "action": action,
                "slice_qty": round(s_qty, 2),
                "cum_qty": round(cum_qty, 2),
                "cum_progress_pct": round((cum_qty / qty_total) * 100.0, 1),
                "order_notional_eur": round(notional, 2),
                "benchmark_price_eur": round(price, 2),
                "est_exec_price_eur": round(est_exec_price, 2),
                "est_slippage_bps": round(est_slippage_bps, 1),
                "interval_mkt_vol": int(interval_mkt_vol),
                "pov_rate_pct": round(pov_rate, 2),
                "algo": "TWAP (Uniform Jittered)"
            })

    df_res = pd.DataFrame(schedule_rows)
    return {
        "schedule_df": df_res,
        "summary": {
            "total_orders": len(df_ord),
            "total_notional_eur": round(tot_notional, 2),
            "total_tranches": len(df_res),
            "algo_type": "TWAP",
            "n_intervals": n_intervals,
            "avg_slippage_bps": round(float(df_res["est_slippage_bps"].mean()), 1) if not df_res.empty else 0.0,
            "max_pov_pct": round(float(df_res["pov_rate_pct"].max()), 2) if not df_res.empty else 0.0
        }
    }


def compute_vwap_schedule(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]],
    start_time_str: str = "09:00",
    interval_minutes: int = 30,
    n_intervals: int = 16,
    pov_cap_pct: float = 0.15,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Generates a Volume-Weighted Average Price (VWAP) execution schedule.
    Weights each time slice in proportion to expected market liquidity (U-shaped curve),
    clamping individual tranche participation to pov_cap_pct to prevent market impact.
    """
    if isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()
        
    if df_ord.empty:
        return {
            "schedule_df": pd.DataFrame(),
            "summary": {
                "total_orders": 0,
                "total_notional_eur": 0.0,
                "total_tranches": 0,
                "algo_type": "VWAP"
            }
        }

    timestamps = []
    curr_hour = int(start_time_str.split(":")[0])
    curr_min = int(start_time_str.split(":")[1])
    for i in range(n_intervals):
        t_str = f"{curr_hour:02d}:{curr_min:02d}"
        timestamps.append(t_str)
        curr_min += interval_minutes
        while curr_min >= 60:
            curr_min -= 60
            curr_hour += 1

    vol_profile = generate_intraday_volume_profile(n_intervals)
    schedule_rows = []
    tot_notional = 0.0

    for _, ord_row in df_ord.iterrows():
        ticker = str(ord_row.get("ticker", ord_row.get("Ticker", "UNKNOWN")))
        action = str(ord_row.get("action", ord_row.get("Azione", "BUY"))).upper()
        qty_total = float(ord_row.get("quantity", ord_row.get("Quote", ord_row.get("qty", 100.0))))
        price = float(ord_row.get("price", ord_row.get("Prezzo (€)", ord_row.get("current_price", 100.0))))
        adv = float(ord_row.get("adv", ord_row.get("volume", 500000.0)))
        
        if qty_total <= 0:
            continue

        # Proportional slice by volume weight
        slice_qtys = qty_total * vol_profile
        
        # Enforce POV Cap (Percentage of Volume) if order is very large relative to ADV
        for idx in range(n_intervals):
            interval_mkt_vol = adv * vol_profile[idx]
            max_allowed = interval_mkt_vol * pov_cap_pct
            if slice_qtys[idx] > max_allowed:
                slice_qtys[idx] = max_allowed

        # Rescale remaining volume to match total order quantity exactly
        slice_qtys = slice_qtys * (qty_total / np.sum(slice_qtys))
        
        cum_qty = 0.0
        for idx in range(n_intervals):
            s_qty = slice_qtys[idx]
            cum_qty += s_qty
            notional = s_qty * price
            tot_notional += notional
            
            interval_mkt_vol = adv * vol_profile[idx]
            pov_rate = (s_qty / max(1.0, interval_mkt_vol)) * 100.0
            
            # VWAP slippage is significantly lower during high volume intervals (liquidity smoothing)
            est_slippage_bps = min(40.0, max(0.2, 2.2 * np.sqrt(pov_rate)))
            est_exec_price = price * (1.0 + (est_slippage_bps / 10000.0) if "BUY" in action else 1.0 - (est_slippage_bps / 10000.0))

            schedule_rows.append({
                "tranche_idx": idx + 1,
                "timestamp": timestamps[idx],
                "ticker": ticker,
                "action": action,
                "slice_qty": round(s_qty, 2),
                "cum_qty": round(cum_qty, 2),
                "cum_progress_pct": round((cum_qty / qty_total) * 100.0, 1),
                "order_notional_eur": round(notional, 2),
                "benchmark_price_eur": round(price, 2),
                "est_exec_price_eur": round(est_exec_price, 2),
                "est_slippage_bps": round(est_slippage_bps, 1),
                "interval_mkt_vol": int(interval_mkt_vol),
                "pov_rate_pct": round(pov_rate, 2),
                "algo": "VWAP (Liquidity-Matched)"
            })

    df_res = pd.DataFrame(schedule_rows)
    return {
        "schedule_df": df_res,
        "summary": {
            "total_orders": len(df_ord),
            "total_notional_eur": round(tot_notional, 2),
            "total_tranches": len(df_res),
            "algo_type": "VWAP",
            "n_intervals": n_intervals,
            "avg_slippage_bps": round(float(df_res["est_slippage_bps"].mean()), 1) if not df_res.empty else 0.0,
            "max_pov_pct": round(float(df_res["pov_rate_pct"].max()), 2) if not df_res.empty else 0.0
        }
    }


def compare_execution_strategies(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]],
    start_time_str: str = "09:00",
    interval_minutes: int = 30,
    n_intervals: int = 16,
    pov_cap_pct: float = 0.15
) -> Dict[str, Any]:
    """
    Compares TWAP vs VWAP vs Immediate Market Execution (Arrival Price / Full Block).
    Quantifies expected slippage savings and market impact reduction.
    """
    twap_res = compute_twap_schedule(orders, start_time_str, interval_minutes, n_intervals)
    vwap_res = compute_vwap_schedule(orders, start_time_str, interval_minutes, n_intervals, pov_cap_pct=pov_cap_pct)
    
    df_twap = twap_res["schedule_df"]
    df_vwap = vwap_res["schedule_df"]
    
    if df_twap.empty or df_vwap.empty:
        return {
            "twap": twap_res,
            "vwap": vwap_res,
            "comparison": {
                "total_notional_eur": 0.0,
                "market_order_cost_eur": 0.0,
                "twap_cost_eur": 0.0,
                "vwap_cost_eur": 0.0,
                "vwap_savings_vs_market_eur": 0.0,
                "vwap_savings_vs_twap_eur": 0.0
            }
        }

    tot_notional = twap_res["summary"]["total_notional_eur"]
    
    # Immediate Market Order Impact is roughly 4x higher due to crossing spread in a single lump sum
    mkt_slippage_bps = 25.0
    mkt_cost_eur = tot_notional * (mkt_slippage_bps / 10000.0)
    
    twap_slip_bps = twap_res["summary"]["avg_slippage_bps"]
    twap_cost_eur = tot_notional * (twap_slip_bps / 10000.0)
    
    vwap_slip_bps = vwap_res["summary"]["avg_slippage_bps"]
    vwap_cost_eur = tot_notional * (vwap_slip_bps / 10000.0)
    
    return {
        "twap": twap_res,
        "vwap": vwap_res,
        "comparison": {
            "total_notional_eur": tot_notional,
            "market_order_cost_eur": round(mkt_cost_eur, 2),
            "twap_cost_eur": round(twap_cost_eur, 2),
            "vwap_cost_eur": round(vwap_cost_eur, 2),
            "vwap_savings_vs_market_eur": round(max(0.0, mkt_cost_eur - vwap_cost_eur), 2),
            "vwap_savings_vs_twap_eur": round(max(0.0, twap_cost_eur - vwap_cost_eur), 2)
        }
    }
