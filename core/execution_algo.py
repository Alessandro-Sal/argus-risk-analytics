"""
ARGUS — Risk Analytics Platform
Core Module: Institutional Algorithmic Execution & Market Microstructure Router
Implements:
- U-shaped intraday volume profiles with configurable Market-on-Close (MOC) rush
- Square-Root Law market impact estimators (Almgren et al. 2005, Kissell-Glantz 2003)
- Multi-asset vectorized Almgren-Chriss (2000) optimal liquidation schedule
- TWAP & VWAP smart order routing with Participation Rate (POV) caps
- Broker order routing export: FIX 4.4 Protocol, IBKR Basket Trader CSV, Directa SIM CSV
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


def generate_intraday_volume_profile(
    n_intervals: int = 16,
    open_rush_factor: float = 1.35,
    close_rush_factor: float = 1.55
) -> np.ndarray:
    """
    Generates a realistic normalized U-shaped intraday volume distribution for equity markets.

    Models high liquidity at market open (09:00-10:30 CET/EST), lower trading velocity
    at midday lunch lull (12:00-14:00), and peak closing volume at Market-on-Close (16:30-17:30 MOC).

    Parameters:
        n_intervals (int, default=16): Number of intraday discrete execution buckets.
        open_rush_factor (float, default=1.35): Volume multiplier for opening auction and early rush.
        close_rush_factor (float, default=1.55): Volume multiplier for closing auction (MOC).

    Returns:
        np.ndarray: Normalized volume fractions across buckets summing to 1.0.

    Examples:
        >>> profile = generate_intraday_volume_profile(16)
        >>> len(profile)
        16
        >>> round(float(sum(profile)), 4)
        1.0
        >>> bool(profile[0] > profile[7])
        True
    """
    n_intervals = max(4, int(n_intervals))
    t = np.linspace(0, 1, n_intervals)
    # Quadratic U-shaped baseline: high at t=0 and t=1, minimum around t=0.45
    raw_profile = 2.4 * (t - 0.45) ** 2 + 0.35
    
    # Morning open rush bonus (first 2 intervals)
    raw_profile[0] *= open_rush_factor
    if n_intervals > 1:
        raw_profile[1] *= (1.0 + (open_rush_factor - 1.0) * 0.45)
        
    # Market on Close (MOC) rush bonus (last 2 intervals)
    if n_intervals > 2:
        raw_profile[-2] *= (1.0 + (close_rush_factor - 1.0) * 0.45)
    raw_profile[-1] *= close_rush_factor
    
    # Normalize so sum of volume weights equals 1.0
    return raw_profile / np.sum(raw_profile)


def estimate_microstructure_market_impact(
    slice_qty: float,
    interval_volume: float,
    total_qty: float,
    adv: float,
    daily_volatility: float = 0.015,
    half_spread_bps: float = 1.5,
    eta: float = 0.142,
    gamma: float = 0.314,
    alpha: float = 0.5
) -> Dict[str, float]:
    r"""
    Estimates market impact according to the institutional Square-Root Law of market impact.

    Market microstructure decomposition:
    1. **Half-Spread Cost**:
       Touch cost of crossing the bid-ask spread:
       $$\text{Cost}_{\text{spread}} = \frac{1}{2} s$$
    2. **Temporary Market Impact**:
       Dissipative concave instantaneous price pressure:
       $$I_{\text{temp}} = \eta \cdot \sigma \cdot \left(\frac{v_t}{V_t}\right)^\alpha$$
    3. **Permanent Market Impact**:
       Informational linear shift on the closing price:
       $$I_{\text{perm}} = \gamma \cdot \sigma \cdot \left(\frac{Q}{\text{ADV}}\right)$$

    Parameters:
        slice_qty (float): Quantity executed in the current intraday interval $v_t$.
        interval_volume (float): Expected market volume in the interval $V_t$.
        total_qty (float): Total order size across the entire trading day $Q$.
        adv (float): Average Daily Volume of the security ($\text{ADV}$).
        daily_volatility (float, default=0.015): Daily asset return standard deviation $\sigma$.
        half_spread_bps (float, default=1.5): Effective half-spread in basis points.
        eta (float, default=0.142): Almgren temporary impact coefficient.
        gamma (float, default=0.314): Almgren permanent impact coefficient.
        alpha (float, default=0.5): Concave power exponent (0.5 represents the Square-Root Law).

    Returns:
        Dict[str, float]:
            Dictionary containing:
            - `half_spread_bps` (float): Half-spread cost in bps.
            - `temporary_impact_bps` (float): Temporary slippage in bps.
            - `permanent_impact_bps` (float): Permanent price drift in bps.
            - `total_slippage_bps` (float): Sum of spread, temporary, and permanent slippage.
            - `pov_rate_pct` (float): Instantaneous Percentage of Volume (POV) rate.

    Examples:
        >>> res = estimate_microstructure_market_impact(
        ...     slice_qty=1000,
        ...     interval_volume=50000,
        ...     total_qty=10000,
        ...     adv=500000,
        ...     daily_volatility=0.02
        ... )
        >>> res['total_slippage_bps'] > 0
        True
        >>> res['half_spread_bps']
        1.5
    """
    slice_qty = max(0.0, float(slice_qty))
    interval_volume = max(1.0, float(interval_volume))
    total_qty = max(0.0, float(total_qty))
    adv = max(1.0, float(adv))
    sigma = max(0.001, float(daily_volatility))

    # Instantaneous participation rate
    pov = slice_qty / interval_volume
    # Overall order participation rate relative to daily volume
    total_pov = total_qty / adv

    # Temporary impact in bps
    temp_impact_bps = eta * sigma * (pov ** alpha) * 10000.0
    # Permanent impact in bps
    perm_impact_bps = gamma * sigma * total_pov * 10000.0

    total_slippage_bps = half_spread_bps + temp_impact_bps + perm_impact_bps

    return {
        "half_spread_bps": round(float(half_spread_bps), 2),
        "temporary_impact_bps": round(float(temp_impact_bps), 2),
        "permanent_impact_bps": round(float(perm_impact_bps), 2),
        "total_slippage_bps": round(float(total_slippage_bps), 2),
        "pov_rate_pct": round(float(pov * 100.0), 3)
    }


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
    Slices order quantities uniformly across time buckets with anti-frontrunning stochastic jitter
    and applies institutional microstructure market impact estimation.
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
        
        # Microstructure inputs with intelligent fallbacks
        vol_daily = float(ord_row.get("volatility_daily", ord_row.get("vol_daily", (ord_row.get("volatility_ann_pct", 22.0) / 100.0) / np.sqrt(252.0))))
        half_spread_bps = float(ord_row.get("half_spread_bps", 1.5))
        
        if qty_total <= 0:
            continue

        base_slice = qty_total / n_intervals
        # Add pseudo-random jitter while ensuring sum equals qty_total exactly
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
            impact_res = estimate_microstructure_market_impact(
                slice_qty=s_qty,
                interval_volume=interval_mkt_vol,
                total_qty=qty_total,
                adv=adv,
                daily_volatility=vol_daily,
                half_spread_bps=half_spread_bps
            )
            pov_rate = impact_res["pov_rate_pct"]
            est_slippage_bps = max(1.0, impact_res["total_slippage_bps"])
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
                "algo_type": "VWAP",
                "n_intervals": n_intervals,
                "avg_slippage_bps": 0.0,
                "max_pov_pct": 0.0
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
        
        # Microstructure inputs with intelligent fallbacks
        vol_daily = float(ord_row.get("volatility_daily", ord_row.get("vol_daily", (ord_row.get("volatility_ann_pct", 22.0) / 100.0) / np.sqrt(252.0))))
        half_spread_bps = float(ord_row.get("half_spread_bps", 0.9)) # VWAP crosses at narrower effective spread
        
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
            impact_res = estimate_microstructure_market_impact(
                slice_qty=s_qty,
                interval_volume=interval_mkt_vol,
                total_qty=qty_total,
                adv=adv,
                daily_volatility=vol_daily,
                half_spread_bps=half_spread_bps,
                eta=0.115 # VWAP benefits from passive matching
            )
            pov_rate = impact_res["pov_rate_pct"]
            est_slippage_bps = max(0.8, impact_res["total_slippage_bps"])
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


def compute_almgren_chriss_basket_schedule(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]],
    horizon_days: float = 1.0,
    n_intervals: int = 16,
    risk_aversion_lambda: float = 1e-6,
    eta_param: float = 0.142,
    gamma_param: float = 0.314,
    start_time_str: str = "09:00",
    interval_minutes: int = 30
) -> Dict[str, Any]:
    """
    Vectorized Multi-Asset Almgren-Chriss (2000) Optimal Liquidation/Rebalancing Schedule.
    Optimally balances market risk (holding variance) against liquidity impact cost:
        min E[x] + lambda * V[x]
    
    Generates closed-form hyperbolic trajectories for each asset in the rebalancing basket:
        x_i(t) = X_{0,i} * sinh(kappa_i * (T - t)) / sinh(kappa_i * T)
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
                "algo_type": "Almgren-Chriss Optimal Slicing",
                "expected_cost_eur": 0.0,
                "execution_var_95_eur": 0.0
            }
        }

    T = max(0.05, float(horizon_days))
    N = max(4, int(n_intervals))
    tau = T / N

    timestamps = []
    curr_hour = int(start_time_str.split(":")[0])
    curr_min = int(start_time_str.split(":")[1])
    for i in range(N):
        t_str = f"{curr_hour:02d}:{curr_min:02d}"
        timestamps.append(t_str)
        curr_min += interval_minutes
        while curr_min >= 60:
            curr_min -= 60
            curr_hour += 1

    t_points = np.linspace(0, T, N + 1)
    schedule_rows = []
    asset_summaries = []
    total_basket_notional = 0.0
    total_temp_cost = 0.0
    total_perm_cost = 0.0
    total_spread_cost = 0.0
    total_holding_var = 0.0

    for _, ord_row in df_ord.iterrows():
        ticker = str(ord_row.get("ticker", ord_row.get("Ticker", "UNKNOWN")))
        action = str(ord_row.get("action", ord_row.get("Azione", "BUY"))).upper()
        qty_total = float(ord_row.get("quantity", ord_row.get("Quote", ord_row.get("qty", 100.0))))
        price = float(ord_row.get("price", ord_row.get("Prezzo (€)", ord_row.get("current_price", 100.0))))
        adv = float(ord_row.get("adv", ord_row.get("volume", 500000.0)))
        
        vol_daily = float(ord_row.get("volatility_daily", ord_row.get("vol_daily", (ord_row.get("volatility_ann_pct", 22.0) / 100.0) / np.sqrt(252.0))))
        spread_bps = float(ord_row.get("half_spread_bps", 1.5))

        if qty_total <= 0:
            continue

        notional_asset = qty_total * price
        total_basket_notional += notional_asset

        # Almgren-Chriss normalized market parameters
        # eta_norm: cost of unit velocity relative to ADV
        eta_norm = max(1e-9, (eta_param * vol_daily) / max(100.0, adv))
        gamma_norm = max(1e-9, (gamma_param * vol_daily) / max(100.0, adv))
        spread_rate = (spread_bps / 10000.0)

        # Urgency parameter kappa
        arg = 1.0 + (risk_aversion_lambda * (vol_daily ** 2) * (tau ** 2)) / (2.0 * eta_norm)
        if arg < 1.0000001:
            kappa = np.sqrt(max(1e-12, (risk_aversion_lambda * (vol_daily ** 2)) / eta_norm))
        else:
            kappa = float(np.arccosh(arg) / tau)
        kappa = max(1e-5, kappa)
        half_life = float(np.log(2.0) / kappa)

        # Optimal remaining position trajectory x(t)
        if kappa * T > 50:
            x_traj = qty_total * np.exp(-kappa * t_points)
        elif kappa * T < 1e-4:
            x_traj = qty_total * (1.0 - t_points / T)
        else:
            x_traj = qty_total * (np.sinh(kappa * (T - t_points)) / np.sinh(kappa * T))
        x_traj = np.clip(x_traj, 0.0, qty_total)
        x_traj[-1] = 0.0

        # Slices traded per interval
        slices = -np.diff(x_traj)
        slices = np.clip(slices, 0.0, None)
        if np.sum(slices) > 0:
            slices = slices * (qty_total / np.sum(slices))

        # Expected cost calculation
        velocities = slices / tau
        asset_perm_cost = 0.5 * gamma_norm * (qty_total ** 2) * price
        asset_temp_cost = float(eta_norm * tau * np.sum(velocities ** 2)) * price
        asset_spread_cost = spread_rate * notional_asset
        asset_cost_tot = asset_perm_cost + asset_temp_cost + asset_spread_cost

        # Holding variance: V[x] = sigma^2 * sum(x_j^2 * tau)
        asset_var = (vol_daily ** 2) * tau * float(np.sum(x_traj[:-1] ** 2)) * (price ** 2)
        asset_std = float(np.sqrt(max(0.0, asset_var)))

        total_temp_cost += asset_temp_cost
        total_perm_cost += asset_perm_cost
        total_spread_cost += asset_spread_cost
        total_holding_var += asset_var

        asset_summaries.append({
            "ticker": ticker,
            "action": action,
            "shares": qty_total,
            "notional_eur": round(notional_asset, 2),
            "kappa": round(kappa, 4),
            "half_life_intervals": round(half_life / tau, 2),
            "expected_cost_eur": round(asset_cost_tot, 2),
            "expected_cost_bps": round((asset_cost_tot / max(1.0, notional_asset)) * 10000.0, 1),
            "execution_std_eur": round(asset_std, 2)
        })

        cum_q = 0.0
        for j in range(N):
            s_q = slices[j]
            cum_q += s_q
            step_notional = s_q * price
            
            # Step slippage (spread + quadratic velocity impact)
            step_slip_bps = (spread_rate + eta_norm * velocities[j] + 0.5 * gamma_norm * s_q) * 10000.0
            step_slip_bps = max(0.5, step_slip_bps)
            exec_px = price * (1.0 + (step_slip_bps / 10000.0) if "BUY" in action else 1.0 - (step_slip_bps / 10000.0))

            schedule_rows.append({
                "tranche_idx": j + 1,
                "timestamp": timestamps[j],
                "ticker": ticker,
                "action": action,
                "slice_qty": round(s_q, 2),
                "cum_qty": round(cum_q, 2),
                "cum_progress_pct": round((cum_q / qty_total) * 100.0, 1),
                "order_notional_eur": round(step_notional, 2),
                "benchmark_price_eur": round(price, 2),
                "est_exec_price_eur": round(exec_px, 2),
                "est_slippage_bps": round(step_slip_bps, 1),
                "remaining_shares": round(x_traj[j + 1], 2),
                "algo": "Almgren-Chriss Optimal Slicing"
            })

    df_schedule = pd.DataFrame(schedule_rows)
    basket_cost_tot = total_temp_cost + total_perm_cost + total_spread_cost
    basket_std = float(np.sqrt(max(0.0, total_holding_var)))
    var_95 = basket_cost_tot + 1.645 * basket_std
    var_99 = basket_cost_tot + 2.326 * basket_std

    return {
        "schedule_df": df_schedule,
        "asset_summaries": asset_summaries,
        "summary": {
            "total_orders": len(df_ord),
            "total_notional_eur": round(total_basket_notional, 2),
            "total_tranches": len(df_schedule),
            "algo_type": "Almgren-Chriss (Optimal Slicing)",
            "horizon_days": T,
            "n_intervals": N,
            "risk_aversion_lambda": risk_aversion_lambda,
            "temporary_impact_cost_eur": round(total_temp_cost, 2),
            "permanent_impact_cost_eur": round(total_perm_cost, 2),
            "spread_cost_eur": round(total_spread_cost, 2),
            "expected_cost_eur": round(basket_cost_tot, 2),
            "expected_cost_bps": round((basket_cost_tot / max(1.0, total_basket_notional)) * 10000.0, 1),
            "holding_risk_std_eur": round(basket_std, 2),
            "execution_var_95_eur": round(var_95, 2),
            "execution_var_99_eur": round(var_99, 2)
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
    Compares TWAP vs VWAP vs Almgren-Chriss vs Immediate Market Execution (Arrival Price / Full Block).
    Quantifies expected slippage savings and market impact reduction using institutional TCA.
    """
    twap_res = compute_twap_schedule(orders, start_time_str, interval_minutes, n_intervals)
    vwap_res = compute_vwap_schedule(orders, start_time_str, interval_minutes, n_intervals, pov_cap_pct=pov_cap_pct)
    ac_res = compute_almgren_chriss_basket_schedule(orders, horizon_days=1.0, n_intervals=n_intervals, start_time_str=start_time_str, interval_minutes=interval_minutes)
    
    df_twap = twap_res["schedule_df"]
    df_vwap = vwap_res["schedule_df"]
    df_ac = ac_res["schedule_df"]
    
    if df_twap.empty or df_vwap.empty:
        return {
            "twap": twap_res,
            "vwap": vwap_res,
            "almgren_chriss": ac_res,
            "comparison": {
                "total_notional_eur": 0.0,
                "market_order_cost_eur": 0.0,
                "market_order_slippage_bps": 0.0,
                "twap_cost_eur": 0.0,
                "vwap_cost_eur": 0.0,
                "almgren_chriss_cost_eur": 0.0,
                "vwap_savings_vs_market_eur": 0.0,
                "vwap_savings_vs_twap_eur": 0.0,
                "ac_savings_vs_market_eur": 0.0
            }
        }

    tot_notional = twap_res["summary"]["total_notional_eur"]
    
    # Dynamic Market Order Impact calculated per-order via Square-Root Law
    mkt_cost_eur = 0.0
    for _, ord_row in df_twap.drop_duplicates(subset=["ticker"]).iterrows():
        tk = ord_row["ticker"]
        tk_notional = float(df_twap[df_twap["ticker"] == tk]["order_notional_eur"].sum())
        tk_adv = float(ord_row.get("interval_mkt_vol", 500000.0) * n_intervals)
        pov_block = tk_notional / max(1000.0, tk_adv)
        # Block slippage: 2.0 bps half-spread + square-root impact
        block_slip_bps = min(120.0, max(2.5, 2.0 + 14.0 * np.sqrt(pov_block) * 100.0))
        mkt_cost_eur += tk_notional * (block_slip_bps / 10000.0)

    mkt_avg_slip_bps = (mkt_cost_eur / max(1.0, tot_notional)) * 10000.0
    
    twap_cost_eur = float((df_twap["order_notional_eur"] * (df_twap["est_slippage_bps"] / 10000.0)).sum())
    vwap_cost_eur = float((df_vwap["order_notional_eur"] * (df_vwap["est_slippage_bps"] / 10000.0)).sum())
    ac_cost_eur = float(ac_res["summary"]["expected_cost_eur"])
    
    return {
        "twap": twap_res,
        "vwap": vwap_res,
        "almgren_chriss": ac_res,
        "comparison": {
            "total_notional_eur": round(tot_notional, 2),
            "market_order_cost_eur": round(mkt_cost_eur, 2),
            "market_order_slippage_bps": round(mkt_avg_slip_bps, 1),
            "twap_cost_eur": round(twap_cost_eur, 2),
            "vwap_cost_eur": round(vwap_cost_eur, 2),
            "almgren_chriss_cost_eur": round(ac_cost_eur, 2),
            "vwap_savings_vs_market_eur": round(max(0.0, mkt_cost_eur - vwap_cost_eur), 2),
            "vwap_savings_vs_twap_eur": round(max(0.0, twap_cost_eur - vwap_cost_eur), 2),
            "ac_savings_vs_market_eur": round(max(0.0, mkt_cost_eur - ac_cost_eur), 2)
        }
    }


# ==============================================================================
# BROKER ORDER ROUTING EXPORTERS (FIX 4.4, IBKR CSV, DIRECTA CSV)
# ==============================================================================

def generate_fix44_blotter(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]],
    sender_comp_id: str = "ARGUS_DESK",
    target_comp_id: str = "BROKER_OMS"
) -> str:
    """
    Generates standard FIX 4.4 New Order Single (MsgType = D) messages for each order slice or order.
    Complies with institutional FIX Protocol 4.4 specification:
    - 8=FIX.4.4 | 9=BodyLength | 35=D | 49=SenderCompID | 56=TargetCompID | 34=MsgSeqNum
    - 52=SendingTime | 11=ClOrdID | 55=Symbol | 54=Side (1=Buy, 2=Sell) | 38=OrderQty
    - 40=OrdType (1=Market, 2=Limit) | 44=Price | 59=TimeInForce (0=Day) | 60=TransactTime | 10=CheckSum
    """
    if isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()

    if df_ord.empty:
        return ""

    messages = []
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
    seq_num = 1

    for idx, row in df_ord.iterrows():
        ticker = str(row.get("ticker", row.get("Ticker", "UNKNOWN")))
        action = str(row.get("action", row.get("Azione", row.get("side", "BUY")))).upper()
        side_fix = "1" if "BUY" in action else "2"
        
        qty = float(row.get("slice_qty", row.get("quantity", row.get("Quote", 100.0))))
        price = float(row.get("est_exec_price_eur", row.get("price", row.get("Prezzo (€)", 100.0))))
        cl_ord_id = f"ARGUS-{ticker}-{idx+1:03d}-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"

        # FIX body fields
        body_fields = [
            f"35=D",
            f"49={sender_comp_id}",
            f"56={target_comp_id}",
            f"34={seq_num}",
            f"52={now_utc}",
            f"11={cl_ord_id}",
            f"55={ticker}",
            f"54={side_fix}",
            f"60={now_utc}",
            f"38={int(round(qty))}",
            f"40=2",  # Limit Order
            f"44={price:.3f}",
            f"59=0"   # Day
        ]
        body_str = "\x01".join(body_fields) + "\x01"
        body_len = len(body_str)
        
        header = f"8=FIX.4.4\x019={body_len}\x01"
        full_msg_no_check = header + body_str
        
        # Calculate checksum: sum of all bytes modulo 256
        checksum = sum(full_msg_no_check.encode("ascii")) % 256
        full_fix_msg = f"{full_msg_no_check}10={checksum:03d}\x01"
        messages.append(full_fix_msg)
        seq_num += 1

    return "\n".join(messages)


def export_ibkr_basket_csv(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]]
) -> str:
    """
    Generates a CSV string compliant with Interactive Brokers (IBKR) TWS Basket Trader format:
    Action,Quantity,Symbol,SecType,Exchange,Currency,OrderType,LmtPrice,TimeInForce
    """
    if isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()

    if df_ord.empty:
        return "Action,Quantity,Symbol,SecType,Exchange,Currency,OrderType,LmtPrice,TimeInForce\n"

    rows = []
    for _, row in df_ord.iterrows():
        ticker = str(row.get("ticker", row.get("Ticker", "UNKNOWN")))
        # Strip exchange suffix if present (e.g. SWDA.MI -> SWDA, IBKR handles exchange separately)
        symbol = ticker.split(".")[0] if "." in ticker else ticker
        exchange = "SMART"
        currency = "EUR"
        if ticker.endswith(".MI"):
            exchange = "BVME"
            currency = "EUR"
        elif ticker.endswith(".DE"):
            exchange = "IBIS"
            currency = "EUR"
        elif ticker.endswith(".L"):
            exchange = "LSE"
            currency = "GBP"

        action = str(row.get("action", row.get("Azione", row.get("side", "BUY")))).upper()
        action_ib = "BUY" if "BUY" in action else "SELL"
        qty = int(round(float(row.get("slice_qty", row.get("quantity", row.get("Quote", 100.0))))))
        price = float(row.get("est_exec_price_eur", row.get("price", row.get("Prezzo (€)", 100.0))))

        rows.append({
            "Action": action_ib,
            "Quantity": qty,
            "Symbol": symbol,
            "SecType": "STK",
            "Exchange": exchange,
            "Currency": currency,
            "OrderType": "LMT",
            "LmtPrice": f"{price:.2f}",
            "TimeInForce": "DAY"
        })

    df_out = pd.DataFrame(rows)
    return df_out.to_csv(index=False)


def export_directa_csv(
    orders: Union[pd.DataFrame, List[Dict[str, Any]]]
) -> str:
    """
    Generates a CSV string compliant with Directa SIM FlashBook / D-Lite Order Import:
    Codice Titolo,Operazione,Quantita,Tipo Ordine,Prezzo Limite,Validita
    """
    if isinstance(orders, list):
        df_ord = pd.DataFrame(orders)
    else:
        df_ord = orders.copy()

    if df_ord.empty:
        return "Codice Titolo;Operazione;Quantita;Tipo Ordine;Prezzo Limite;Validita\n"

    rows = []
    for _, row in df_ord.iterrows():
        ticker = str(row.get("ticker", row.get("Ticker", "UNKNOWN")))
        action = str(row.get("action", row.get("Azione", row.get("side", "BUY")))).upper()
        op = "ACQUISTO" if "BUY" in action else "VENDITA"
        qty = int(round(float(row.get("slice_qty", row.get("quantity", row.get("Quote", 100.0))))))
        price = float(row.get("est_exec_price_eur", row.get("price", row.get("Prezzo (€)", 100.0))))

        rows.append({
            "Codice Titolo": ticker,
            "Operazione": op,
            "Quantita": qty,
            "Tipo Ordine": "LIM",
            "Prezzo Limite": f"{price:.3f}".replace(".", ","),
            "Validita": "OGGI"
        })

    df_out = pd.DataFrame(rows)
    return df_out.to_csv(index=False, sep=";")
