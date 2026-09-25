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
