"""Intraday Optimal Liquidation & VWAP/TWAP Slicing Engine with Square-Root Impact.

Extends Almgren & Chriss (2001) and Gatheral (2010) institutional execution framework:
1. Nonlinear Temporary Market Impact (Square-Root Law):
       h(v_k) = eta * sigma_daily * S_0 * (v_k / V_k)^0.5
2. Linear Permanent Market Impact:
       g(v_k) = gamma * sigma_daily * S_0 * (v_k / ADV)
3. Intraday U-Shaped Market Volume Profile across N trading intervals.
4. Compares three institutional algorithms:
   - Almgren-Chriss Risk-Averse Trajectory (hyperbolic sinh urgency trajectory)
   - Dynamic Intraday VWAP with Percentage-of-Volume (POV) cap
   - Uniform TWAP Benchmark
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class OptimalLiquidationConfig:
    """Configuration for Intraday Optimal Liquidation & Algorithmic Slicing."""

    ticker: str = "ENI.MI"
    order_shares: float = 250_000.0
    spot_price: float = 14.80
    adv_shares: float = 5_000_000.0
    daily_volatility: float = 0.018
    bid_ask_spread_bps: float = 4.0
    temp_impact_eta: float = 0.14
    perm_impact_gamma: float = 0.08
    risk_aversion_lambda: float = 2.5e-6
    horizon_hours: float = 6.5
    n_slices: int = 13
    max_pov_cap: float = 0.15  # 15% maximum participation rate


class OptimalLiquidationEngine:
    """Institutional Execution Desk Engine for Almgren-Chriss, VWAP & TWAP Slicing."""

    def __init__(self, config: OptimalLiquidationConfig | None = None) -> None:
        self.config = config or OptimalLiquidationConfig()

    def generate_intraday_volume_profile(self) -> np.ndarray:
        """Generate realistic U-shaped intraday market volume distribution across N bins."""
        n = max(int(self.config.n_slices), 2)
        u = np.linspace(-1.0, 1.0, n)
        # Quadratic + exponential tail boost for opening and closing auctions
        raw_weights = 1.0 + 1.35 * (u**2) + 0.45 * np.exp(-4.0 * (1.0 - np.abs(u)))
        weights = raw_weights / np.sum(raw_weights)
        # Scale by fraction of full trading day (6.5h standard)
        day_fraction = min(max(self.config.horizon_hours / 6.5, 0.10), 1.0)
        return weights * (self.config.adv_shares * day_fraction)

    def _compute_almgren_chriss_trades(self, n: int, x0: float) -> tuple[np.ndarray, float]:
        """Compute risk-averse hyperbolic inventory and trade schedule."""
        cfg = self.config
        dt = max(cfg.horizon_hours / 6.5, 0.05) / n
        sigma_abs = cfg.daily_volatility * cfg.spot_price
        # Effective linearized urgency kappa for sinh trajectory
        eta_eff = max(
            cfg.temp_impact_eta * sigma_abs / max(cfg.adv_shares * dt, 1.0),
            1e-10,
        )
        kappa = math.sqrt(max(cfg.risk_aversion_lambda * (sigma_abs**2) / eta_eff, 1e-8))
        total_t = n * dt

        times = np.linspace(0.0, total_t, n + 1)
        if kappa * total_t > 50.0:
            inv = x0 * np.exp(-kappa * times)
            inv[-1] = 0.0
        elif kappa * total_t < 1e-4:
            inv = np.linspace(x0, 0.0, n + 1)
        else:
            inv = x0 * np.sinh(kappa * (total_t - times)) / math.sinh(kappa * total_t)

        trades = np.maximum(-np.diff(inv), 0.0)
        if np.sum(trades) > 0:
            trades = trades * (x0 / np.sum(trades))
        return trades, float(kappa)

    def _compute_vwap_pov_trades(
        self, market_vols: np.ndarray, x0: float
    ) -> np.ndarray:
        """Compute intraday VWAP schedule with maximum Percentage-of-Volume (POV) cap."""
        vol_shares = market_vols / np.sum(market_vols)
        desired_trades = x0 * vol_shares
        cap_shares = market_vols * max(self.config.max_pov_cap, 0.01)

        trades = np.minimum(desired_trades, cap_shares)
        residual = x0 - float(np.sum(trades))
        if residual > 1e-6:
            # Redistribute residual across bins that still have capacity, or proportionally
            headroom = np.maximum(cap_shares - trades, 0.0)
            if float(np.sum(headroom)) >= residual:
                trades += residual * (headroom / np.sum(headroom))
            else:
                trades = desired_trades  # Order exceeds total POV capacity over horizon
        return trades

    def _evaluate_schedule_metrics(
        self, trades: np.ndarray, market_vols: np.ndarray
    ) -> dict[str, Any]:
        """Evaluate nonlinear Square-Root temporary impact, permanent impact, and timing risk."""
        cfg = self.config
        n = len(trades)
        dt = max(cfg.horizon_hours / 6.5, 0.05) / n
        s0 = cfg.spot_price
        x0 = max(cfg.order_shares, 1.0)
        notional = x0 * s0
        sigma_daily = cfg.daily_volatility

        # Remaining inventory at end of each slice
        inventory = np.maximum(x0 - np.cumsum(trades), 0.0)
        pov_rates = trades / np.maximum(market_vols, 1.0)

        # 1. Half-spread cost (EUR)
        half_spread_per_share = 0.5 * (cfg.bid_ask_spread_bps * 1e-4) * s0
        spread_cost_eur = float(np.sum(trades * half_spread_per_share))

        # 2. Nonlinear Square-Root temporary impact: eta * sigma * S0 * sqrt(v_k / V_k)
        temp_impact_per_share = (
            cfg.temp_impact_eta * sigma_daily * s0 * np.sqrt(np.maximum(pov_rates, 0.0))
        )
        temp_cost_eur = float(np.sum(trades * temp_impact_per_share))

        # 3. Linear permanent impact: gamma * sigma * S0 * (v_k / ADV) affecting subsequent slices
        perm_price_drop_step = (
            cfg.perm_impact_gamma * sigma_daily * s0 * (trades / max(cfg.adv_shares, 1.0))
        )
        cum_perm_drop = np.cumsum(perm_price_drop_step)
        # Average price drop during slice k is cum_perm_drop[k-1] + 0.5 * step[k]
        prev_cum_drop = np.concatenate([[0.0], cum_perm_drop[:-1]])
        effective_perm_drop = prev_cum_drop + 0.5 * perm_price_drop_step
        perm_cost_eur = float(np.sum(trades * effective_perm_drop))

        expected_cost_eur = spread_cost_eur + temp_cost_eur + perm_cost_eur
        expected_cost_bps = (expected_cost_eur / max(notional, 1.0)) * 10_000.0

        # 4. Execution Timing Variance: sigma^2 * S0^2 * dt * sum(x_k^2)
        variance_eur2 = float(
            ((sigma_daily * s0) ** 2) * dt * np.sum(inventory**2)
        )
        timing_std_eur = math.sqrt(max(variance_eur2, 0.0))
        timing_std_bps = (timing_std_eur / max(notional, 1.0)) * 10_000.0

        # 5. Mean-Variance Utility Objective (EUR)
        utility_cost_eur = expected_cost_eur + cfg.risk_aversion_lambda * variance_eur2

        return {
            "expected_cost_eur": round(expected_cost_eur, 2),
            "expected_cost_bps": round(expected_cost_bps, 2),
            "spread_cost_bps": round((spread_cost_eur / max(notional, 1.0)) * 10_000.0, 2),
            "temporary_impact_bps": round((temp_cost_eur / max(notional, 1.0)) * 10_000.0, 2),
            "permanent_impact_bps": round((perm_cost_eur / max(notional, 1.0)) * 10_000.0, 2),
            "timing_risk_std_eur": round(timing_std_eur, 2),
            "timing_risk_std_bps": round(timing_std_bps, 2),
            "risk_adjusted_utility_eur": round(utility_cost_eur, 2),
            "max_pov_rate_pct": round(float(np.max(pov_rates)) * 100.0, 2),
            "avg_pov_rate_pct": round(float(np.mean(pov_rates)) * 100.0, 2),
            "inventory_path": [round(float(x), 1) for x in [x0, *inventory.tolist()]],
            "marginal_impact_bps": [
                round(float(imp / s0 * 10_000.0), 2) for imp in temp_impact_per_share
            ],
            "pov_rates_pct": [round(float(p * 100.0), 2) for p in pov_rates],
        }

    def compute_schedule(self) -> dict[str, Any]:
        """Compute and compare Optimal Almgren-Chriss, Dynamic VWAP, and TWAP trajectories."""
        cfg = self.config
        n = max(int(cfg.n_slices), 2)
        x0 = float(cfg.order_shares)
        notional_eur = x0 * cfg.spot_price

        market_vols = self.generate_intraday_volume_profile()
        vol_shares_pct = (market_vols / np.sum(market_vols)) * 100.0

        trades_opt, urgency_kappa = self._compute_almgren_chriss_trades(n, x0)
        trades_vwap = self._compute_vwap_pov_trades(market_vols, x0)
        trades_twap = np.full(n, x0 / n)

        metrics_opt = self._evaluate_schedule_metrics(trades_opt, market_vols)
        metrics_vwap = self._evaluate_schedule_metrics(trades_vwap, market_vols)
        metrics_twap = self._evaluate_schedule_metrics(trades_twap, market_vols)

        # Build slice-by-slice schedule table
        slices_table: list[dict[str, Any]] = []
        start_minutes = 9 * 60  # 09:00 market open
        step_minutes = int(round((cfg.horizon_hours * 60.0) / n))

        for k in range(n):
            m_start = start_minutes + k * step_minutes
            m_end = m_start + step_minutes
            label = f"{m_start // 60:02d}:{m_start % 60:02d}-{m_end // 60:02d}:{m_end % 60:02d}"
            slices_table.append(
                {
                    "slice_index": k + 1,
                    "time_bucket": label,
                    "market_volume_shares": round(float(market_vols[k]), 0),
                    "market_volume_share_pct": round(float(vol_shares_pct[k]), 2),
                    "optimal_shares": round(float(trades_opt[k]), 1),
                    "vwap_shares": round(float(trades_vwap[k]), 1),
                    "twap_shares": round(float(trades_twap[k]), 1),
                    "inventory_optimal": metrics_opt["inventory_path"][k + 1],
                    "inventory_vwap": metrics_vwap["inventory_path"][k + 1],
                    "inventory_twap": metrics_twap["inventory_path"][k + 1],
                    "optimal_pov_pct": metrics_opt["pov_rates_pct"][k],
                    "optimal_marginal_impact_bps": metrics_opt["marginal_impact_bps"][k],
                }
            )

        # Recommend strategy minimizing risk-adjusted utility cost
        candidates = [
            ("Almgren-Chriss Optimal (IS)", metrics_opt["risk_adjusted_utility_eur"]),
            ("Dynamic Intraday VWAP (POV-Capped)", metrics_vwap["risk_adjusted_utility_eur"]),
            ("Uniform TWAP Benchmark", metrics_twap["risk_adjusted_utility_eur"]),
        ]
        recommended_algo = min(candidates, key=lambda item: item[1])[0]

        return {
            "ticker": cfg.ticker,
            "order_shares": round(x0, 0),
            "spot_price": round(cfg.spot_price, 4),
            "order_notional_eur": round(notional_eur, 2),
            "adv_shares": round(cfg.adv_shares, 0),
            "order_pct_of_adv": round((x0 / max(cfg.adv_shares, 1.0)) * 100.0, 2),
            "urgency_parameter_kappa": round(urgency_kappa, 4),
            "recommended_algorithm": recommended_algo,
            "strategies": {
                "almgren_chriss_optimal": metrics_opt,
                "dynamic_vwap": metrics_vwap,
                "uniform_twap": metrics_twap,
            },
            "intraday_schedule": slices_table,
        }


def compute_optimal_execution_schedule(
    ticker: str = "ENI.MI",
    order_shares: float = 250_000.0,
    spot_price: float = 14.80,
    adv_shares: float = 5_000_000.0,
    daily_volatility: float = 0.018,
    bid_ask_spread_bps: float = 4.0,
    temp_impact_eta: float = 0.14,
    perm_impact_gamma: float = 0.08,
    risk_aversion_lambda: float = 2.5e-6,
    horizon_hours: float = 6.5,
    n_slices: int = 13,
    max_pov_cap: float = 0.15,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    config = OptimalLiquidationConfig(
        ticker=ticker,
        order_shares=order_shares,
        spot_price=spot_price,
        adv_shares=adv_shares,
        daily_volatility=daily_volatility,
        bid_ask_spread_bps=bid_ask_spread_bps,
        temp_impact_eta=temp_impact_eta,
        perm_impact_gamma=perm_impact_gamma,
        risk_aversion_lambda=risk_aversion_lambda,
        horizon_hours=horizon_hours,
        n_slices=n_slices,
        max_pov_cap=max_pov_cap,
    )
    engine = OptimalLiquidationEngine(config=config)
    return engine.compute_schedule()


def render_optimal_liquidation_lab(
    positions: Any = None,
    default_ticker: str = "ENI.MI",
    key_prefix: str = "opt_liq",
) -> None:
    """Render interactive Bloomberg-grade Almgren-Chriss Optimal Liquidation Trajectory & Market Impact Lab."""
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st
    from plotly.subplots import make_subplots

    from core.ui_utils import apply_plotly_theme, metric_card

    st.markdown(
        """
        <div style="background: linear-gradient(90deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.85) 100%);
                    border: 1px solid rgba(255, 153, 0, 0.35); border-left: 4px solid #ff9900;
                    border-radius: 8px; padding: 12px 18px; margin-top: 10px; margin-bottom: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="font-size: 15px; font-weight: 700; color: #f0f6fc;">
              ⚡ Almgren-Chriss (2001) Optimal Liquidation Trajectory & Market Impact Lab
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px;
                           border-radius: 12px; background: rgba(255,255,255,0.06); color: #8b949e;
                           border: 1px solid rgba(255,255,255,0.08);">Institutional Execution</span>
              <span style="font-size: 11.5px; font-weight: 600; padding: 2px 10px; border-radius: 12px;
                           background: #ff990022; color: #ff9900; border: 1px solid #ff990055;">
                Square-Root Law • Hyperbolic Sinh • U-Profile
              </span>
            </div>
          </div>
          <div style="font-size: 13px; color: #8b949e; line-height: 1.45; margin-top: 4px;">
            Schedulazione ottima dell'inventario residuo \\(x(t) = X_0 \\frac{\\sinh(\\kappa(T - t))}{\\sinh(\\kappa T)}\\)
            in presenza di impatto temporaneo sublineare (\\(\\sim \\sqrt{v_k / V_k}\\)), impatto permanente e rischio di timing.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Parameter extraction from positions or default inputs
    pos_df = positions if isinstance(positions, pd.DataFrame) and not positions.empty else None
    available_tickers = []
    if pos_df is not None and "ticker" in pos_df.columns:
        available_tickers = [t for t in pos_df["ticker"].dropna().unique().tolist() if str(t).strip()]

    c_in1, c_in2, c_in3, c_in4 = st.columns([1.5, 1.2, 1.2, 1.2])

    with c_in1:
        if available_tickers:
            sel_idx = 0
            if default_ticker in available_tickers:
                sel_idx = available_tickers.index(default_ticker)
            ticker_val = st.selectbox("Ticker Asset:", available_tickers, index=sel_idx, key=f"{key_prefix}_ticker")
        else:
            ticker_val = st.text_input("Ticker Asset:", value=default_ticker, key=f"{key_prefix}_ticker")

    # Extract default quantities and price if ticker exists in pos_df
    def_shares = 100_000.0
    def_price = 15.0
    if pos_df is not None and "ticker" in pos_df.columns and ticker_val:
        row_match = pos_df[pos_df["ticker"] == ticker_val]
        if not row_match.empty:
            if "qty_net" in row_match.columns:
                val_q = float(row_match["qty_net"].iloc[0])
                if val_q > 0:
                    def_shares = val_q
            if "last_price" in row_match.columns:
                val_p = float(row_match["last_price"].iloc[0])
                if val_p > 0:
                    def_price = val_p

    min_shares = 0.0001
    max_shares = 50_000_000.0
    safe_shares = max(min_shares, min(float(def_shares), max_shares))
    step_shares = 1.0 if safe_shares < 1000.0 else (100.0 if safe_shares < 100_000.0 else 10_000.0)

    min_price = 0.0001
    max_price = 1_000_000.0
    safe_price = max(min_price, min(float(def_price), max_price))
    step_price = 0.01 if safe_price < 10.0 else 1.0

    min_adv = 100.0
    max_adv = 500_000_000.0

    # Auto-update inputs when ticker selection changes
    prev_tk_key = f"{key_prefix}_prev_ticker"
    if st.session_state.get(prev_tk_key) != ticker_val:
        st.session_state[prev_tk_key] = ticker_val
        st.session_state[f"{key_prefix}_shares"] = float(safe_shares)
        st.session_state[f"{key_prefix}_price"] = float(safe_price)

    # Guard against any stale session_state value outside bounds
    sh_k = f"{key_prefix}_shares"
    if sh_k in st.session_state:
        try:
            st.session_state[sh_k] = max(min_shares, min(float(st.session_state[sh_k]), max_shares))
        except (ValueError, TypeError):
            st.session_state[sh_k] = safe_shares

    px_k = f"{key_prefix}_price"
    if px_k in st.session_state:
        try:
            st.session_state[px_k] = max(min_price, min(float(st.session_state[px_k]), max_price))
        except (ValueError, TypeError):
            st.session_state[px_k] = safe_price

    with c_in2:
        order_shares_val = st.number_input(
            "Quote da Smobilizzare (X₀):",
            min_value=min_shares,
            max_value=max_shares,
            value=float(safe_shares),
            step=float(step_shares),
            key=sh_k,
        )

    with c_in3:
        spot_price_val = st.number_input(
            "Prezzo Spot (€):",
            min_value=min_price,
            max_value=max_price,
            value=float(safe_price),
            step=float(step_price),
            key=px_k,
        )

    safe_adv = max(min_adv, min(max(float(order_shares_val * 20.0), 2_000_000.0), max_adv))
    step_adv = 10_000.0 if safe_adv < 1_000_000.0 else 500_000.0
    adv_k = f"{key_prefix}_adv"
    if adv_k in st.session_state:
        try:
            st.session_state[adv_k] = max(min_adv, min(float(st.session_state[adv_k]), max_adv))
        except (ValueError, TypeError):
            st.session_state[adv_k] = safe_adv

    with c_in4:
        adv_val = st.number_input(
            "ADV Medio (Quote/giorno):",
            min_value=min_adv,
            max_value=max_adv,
            value=float(safe_adv),
            step=float(step_adv),
            key=adv_k,
        )

    with st.expander("🛠️ Parametri Avanzati di Microstruttura & Urgenza (Almgren-Chriss)", expanded=False):
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        with c_p1:
            vol_daily_pct = st.slider("Volatilità Giornaliera (%):", 0.5, 8.0, 1.8, 0.1, key=f"{key_prefix}_vol")
        with c_p2:
            spread_bps = st.slider("Bid-Ask Spread (bps):", 1.0, 50.0, 4.0, 0.5, key=f"{key_prefix}_spread")
        with c_p3:
            lambda_choices = [
                ("1e-7 (Quasi Neutrale)", 1.0e-7),
                ("5e-7 (Bassa Avversione)", 5.0e-7),
                ("1e-6 (Bilanciata)", 1.0e-6),
                ("2.5e-6 (Istituzionale Standard)", 2.5e-6),
                ("5e-6 (Alta Urgenza)", 5.0e-6),
                ("1e-5 (Stress Liquidazione)", 1.0e-5),
            ]
            sel_lambda_label = st.selectbox(
                "Avversione al Rischio (λ):",
                [item[0] for item in lambda_choices],
                index=3,
                key=f"{key_prefix}_lambda",
            )
            lambda_val = dict(lambda_choices).get(sel_lambda_label, 2.5e-6)
        with c_p4:
            pov_cap_pct = st.slider("POV Cap Massimo (%):", 5, 40, 15, 1, key=f"{key_prefix}_pov")

        c_t1, c_t2, c_t3, c_t4 = st.columns(4)
        with c_t1:
            horizon_hrs = st.slider("Orizzonte Trading (ore):", 1.0, 8.5, 6.5, 0.5, key=f"{key_prefix}_hrs")
        with c_t2:
            slices_num = st.slider("Numero Tranche (N):", 6, 26, 13, 1, key=f"{key_prefix}_slices")
        with c_t3:
            eta_val = st.number_input("Coeff. Temp Impact (η):", 0.01, 1.0, 0.14, 0.01, key=f"{key_prefix}_eta")
        with c_t4:
            gamma_val = st.number_input("Coeff. Perm Impact (γ):", 0.01, 1.0, 0.08, 0.01, key=f"{key_prefix}_gamma")

    # 2. Compute Trajectories & Metrics
    config = OptimalLiquidationConfig(
        ticker=str(ticker_val),
        order_shares=float(order_shares_val),
        spot_price=float(spot_price_val),
        adv_shares=float(adv_val),
        daily_volatility=float(vol_daily_pct / 100.0),
        bid_ask_spread_bps=float(spread_bps),
        temp_impact_eta=float(eta_val),
        perm_impact_gamma=float(gamma_val),
        risk_aversion_lambda=float(lambda_val),
        horizon_hours=float(horizon_hrs),
        n_slices=int(slices_num),
        max_pov_cap=float(pov_cap_pct / 100.0),
    )
    engine = OptimalLiquidationEngine(config=config)
    res = engine.compute_schedule()

    opt_res = res["strategies"]["almgren_chriss_optimal"]
    vwap_res = res["strategies"]["dynamic_vwap"]
    twap_res = res["strategies"]["uniform_twap"]

    kappa = float(res["urgency_parameter_kappa"])
    half_life_hrs = (math.log(2.0) / kappa) if kappa > 1e-6 else horizon_hrs
    half_life_str = f"{half_life_hrs:.2f}h ({int(half_life_hrs * 60)} min)" if half_life_hrs < 10.0 else ">10h"

    # Fire-sale cost (1 single slice execution at open)
    mkt_vols = engine.generate_intraday_volume_profile()
    v_open = max(float(mkt_vols[0]), 1.0)
    x0 = float(order_shares_val)
    s0 = float(spot_price_val)
    notional = x0 * s0
    vol_daily = float(vol_daily_pct / 100.0)

    spread_cost_fs = 0.5 * (float(spread_bps) * 1e-4) * s0 * x0
    temp_cost_fs = float(eta_val) * vol_daily * s0 * math.sqrt(max(x0 / v_open, 0.0)) * x0
    perm_cost_fs = float(gamma_val) * vol_daily * s0 * (x0 / max(float(adv_val), 1.0)) * x0
    fire_sale_cost_eur = spread_cost_fs + temp_cost_fs + perm_cost_fs
    fire_sale_cost_bps = (fire_sale_cost_eur / max(notional, 1.0)) * 10_000.0
    friction_saved_eur = max(fire_sale_cost_eur - opt_res["expected_cost_eur"], 0.0)

    # 3. High-Impact KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        metric_card(
            "Strategia Consigliata",
            res["recommended_algorithm"].split(" ")[0],
            res["recommended_algorithm"],
            positive=True,
        )
    with k2:
        metric_card(
            "Costo Almgren-Chriss",
            f"{opt_res['expected_cost_bps']:.1f} bps",
            f"€ {opt_res['expected_cost_eur']:,.2f}",
            positive=opt_res["expected_cost_bps"] < 15.0,
        )
    with k3:
        metric_card(
            "Risparmio vs Fire-Sale",
            f"€ {friction_saved_eur:,.2f}",
            f"-{(friction_saved_eur / max(fire_sale_cost_eur, 1.0)) * 100.0:.1f}% impatto",
            positive=True,
        )
    with k4:
        metric_card(
            "Half-Life Liquidazione (t½)",
            half_life_str,
            f"Urgenza κ = {kappa:.4f}/h",
            positive=half_life_hrs < horizon_hrs,
        )
    with k5:
        metric_card(
            "Rischio Timing (σ_T)",
            f"{opt_res['timing_risk_std_bps']:.1f} bps",
            f"± € {opt_res['timing_risk_std_eur']:,.2f}",
            positive=opt_res["timing_risk_std_bps"] < 25.0,
        )

    # 4. Dual-Axis Interactive Trajectory Chart
    sched_items = res["intraday_schedule"]
    time_labels = [item["time_bucket"] for item in sched_items]
    inv_opt = opt_res["inventory_path"][1:]
    inv_vwap = vwap_res["inventory_path"][1:]
    inv_twap = twap_res["inventory_path"][1:]

    mkt_volumes = [item["market_volume_shares"] for item in sched_items]
    trades_opt_list = [item["optimal_shares"] for item in sched_items]
    trades_vwap_list = [item["vwap_shares"] for item in sched_items]

    fig_traj = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[
            "Traiettoria Inventario Residuo x(t) & Profilo a U dei Volumi",
            "Scomposizione Analitica Costi & Rischio (bps)",
        ],
        column_widths=[0.62, 0.38],
        specs=[[{"secondary_y": True}, {"secondary_y": False}]],
    )

    # Subplot 1: Right Y - Market Volume Bars
    fig_traj.add_trace(
        go.Bar(
            x=time_labels,
            y=mkt_volumes,
            name="Volume Mercato Intraday (U-Shape)",
            marker_color="rgba(140, 160, 185, 0.15)",
            showlegend=True,
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    # Subplot 1: Left Y - Inventory lines
    fig_traj.add_trace(
        go.Scatter(
            x=time_labels,
            y=inv_opt,
            name="Almgren-Chriss x(t) [Sinh]",
            mode="lines+markers",
            line=dict(color="#ff9900", width=3),
            marker=dict(size=6, color="#ff9900"),
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig_traj.add_trace(
        go.Scatter(
            x=time_labels,
            y=inv_vwap,
            name="Dynamic VWAP (POV Cap)",
            mode="lines",
            line=dict(color="#38bdf8", width=2, dash="dash"),
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    fig_traj.add_trace(
        go.Scatter(
            x=time_labels,
            y=inv_twap,
            name="Uniform TWAP Benchmark",
            mode="lines",
            line=dict(color="#a855f7", width=1.5, dash="dot"),
        ),
        row=1,
        col=1,
        secondary_y=False,
    )

    # Subplot 2: Cost Breakdown Bar Chart
    strats = ["Almgren-Chriss", "Dynamic VWAP", "Uniform TWAP", "Fire-Sale (1-Shot)"]
    spread_costs = [
        opt_res["spread_cost_bps"],
        vwap_res["spread_cost_bps"],
        twap_res["spread_cost_bps"],
        round((spread_cost_fs / max(notional, 1.0)) * 10_000.0, 2),
    ]
    temp_costs = [
        opt_res["temporary_impact_bps"],
        vwap_res["temporary_impact_bps"],
        twap_res["temporary_impact_bps"],
        round((temp_cost_fs / max(notional, 1.0)) * 10_000.0, 2),
    ]
    perm_costs = [
        opt_res["permanent_impact_bps"],
        vwap_res["permanent_impact_bps"],
        twap_res["permanent_impact_bps"],
        round((perm_cost_fs / max(notional, 1.0)) * 10_000.0, 2),
    ]
    timing_risks = [
        opt_res["timing_risk_std_bps"],
        vwap_res["timing_risk_std_bps"],
        twap_res["timing_risk_std_bps"],
        0.0,
    ]

    fig_traj.add_trace(
        go.Bar(name="Half-Spread (bps)", x=strats, y=spread_costs, marker_color="#64748b"),
        row=1,
        col=2,
    )
    fig_traj.add_trace(
        go.Bar(name="Impatto Temporaneo (bps)", x=strats, y=temp_costs, marker_color="#f59e0b"),
        row=1,
        col=2,
    )
    fig_traj.add_trace(
        go.Bar(name="Impatto Permanente (bps)", x=strats, y=perm_costs, marker_color="#ef4444"),
        row=1,
        col=2,
    )
    fig_traj.add_trace(
        go.Bar(name="Timing Risk StdDev (bps)", x=strats, y=timing_risks, marker_color="#3b82f6"),
        row=1,
        col=2,
    )

    fig_traj.update_layout(
        barmode="stack",
        height=440,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified",
    )
    fig_traj.update_yaxes(title_text="Quote Residue", secondary_y=False, row=1, col=1)
    fig_traj.update_yaxes(title_text="Volume Mercato", secondary_y=True, showgrid=False, row=1, col=1)
    fig_traj.update_yaxes(title_text="Costo / Rischio (bps)", row=1, col=2)

    apply_plotly_theme(fig_traj)
    st.plotly_chart(fig_traj, use_container_width=True, key=f"{key_prefix}_chart")

    # 5. Schedulazione Dettagliata per Tranche
    with st.expander("📋 Tabella Dettagliata delle Tranche & Profilo di Partecipazione (POV)", expanded=False):
        df_sched = pd.DataFrame(sched_items)
        df_sched_disp = df_sched[[
            "slice_index",
            "time_bucket",
            "optimal_shares",
            "inventory_optimal",
            "optimal_pov_pct",
            "optimal_marginal_impact_bps",
            "vwap_shares",
            "twap_shares",
            "market_volume_shares",
        ]].rename(
            columns={
                "slice_index": "Tranche #",
                "time_bucket": "Fascia Oraria",
                "optimal_shares": "Tranche Ottima (Quote)",
                "inventory_optimal": "Inventario Residuo",
                "optimal_pov_pct": "POV Rate (%)",
                "optimal_marginal_impact_bps": "Marginal Impact (bps)",
                "vwap_shares": "VWAP (Quote)",
                "twap_shares": "TWAP (Quote)",
                "market_volume_shares": "Volume Mercato Stimato",
            }
        )
        st.dataframe(df_sched_disp, use_container_width=True, hide_index=True)

        csv_data = df_sched_disp.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Esporta Schedulazione Algoritmica (CSV)",
            data=csv_data,
            file_name=f"ARGUS_Optimal_Liquidation_{ticker_val}.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv_btn",
        )

