"""Avellaneda-Stoikov (2008) Market-Making & Hawkes / VPIN Order-Flow Toxicity Engine.

Implements:
1. Avellaneda & Stoikov (2008) Optimal High-Frequency Market-Making:
   - Reservation (Indifference) Price:
         r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
   - Optimal Bid/Ask Spread:
         delta_a + delta_b = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + gamma / kappa)
2. Easley, Lopez de Prado & O'Hara (2012) VPIN (Volume-Synchronized Probability of Informed Trading)
   across volume buckets to detect toxic order flow and adverse selection.
3. Self-Exciting Hawkes Process intensity lambda_t = mu + sum alpha * exp(-beta * (t - t_i))
   with branching ratio alpha / beta for Flash-Crash early warning.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


class MarketMakingVpinEngine:
    """Institutional Market-Making Quotes & Order-Flow Toxicity (VPIN / Hawkes) Engine."""

    def __init__(
        self,
        symbol: str = "STM.MI",
        mid_price: float = 38.50,
        inventory_q: float = 1_500.0,
        risk_aversion_gamma: float = 0.08,
        volatility_sigma: float = 0.022,
        order_book_density_kappa: float = 1.65,
        time_remaining_fraction: float = 0.50,
        hawkes_mu: float = 1.2,
        hawkes_alpha: float = 0.85,
        hawkes_beta: float = 1.40,
    ) -> None:
        self.symbol = symbol
        self.mid_price = mid_price
        self.inventory_q = inventory_q
        self.risk_aversion_gamma = risk_aversion_gamma
        self.volatility_sigma = volatility_sigma
        self.order_book_density_kappa = order_book_density_kappa
        self.time_remaining_fraction = time_remaining_fraction
        self.hawkes_mu = hawkes_mu
        self.hawkes_alpha = hawkes_alpha
        self.hawkes_beta = max(hawkes_beta, hawkes_alpha + 0.05)

    def compute_avellaneda_stoikov_quotes(self) -> dict[str, Any]:
        """Compute Reservation Price r(s, q, t), Optimal Spread, and Bid/Ask quotes across inventory grid."""
        s = self.mid_price
        q = self.inventory_q
        gamma = max(self.risk_aversion_gamma, 1e-5)
        sigma_abs = self.volatility_sigma * s
        kappa = max(self.order_book_density_kappa, 0.1)
        tau = max(self.time_remaining_fraction, 0.01)

        # Normalize inventory q into standard round lots (100 shares)
        q_lots = q / 100.0
        reservation_price = s - q_lots * gamma * (sigma_abs**2) * tau
        optimal_total_spread = gamma * (sigma_abs**2) * tau + (2.0 / gamma) * math.log(1.0 + gamma / kappa)

        optimal_bid = reservation_price - 0.5 * optimal_total_spread
        optimal_ask = reservation_price + 0.5 * optimal_total_spread
        skew_bps = ((reservation_price - s) / max(s, 1e-6)) * 10_000.0
        spread_bps = (optimal_total_spread / max(s, 1e-6)) * 10_000.0

        # Inventory sensitivity curve from -10 to +10 lots
        q_grid_lots = np.linspace(-10.0, 10.0, 11)
        inventory_curve = []
        for ql in q_grid_lots:
            r_px = s - ql * gamma * (sigma_abs**2) * tau
            inventory_curve.append(
                {
                    "inventory_shares": round(float(ql * 100.0), 0),
                    "reservation_price": round(float(r_px), 4),
                    "optimal_bid": round(float(r_px - 0.5 * optimal_total_spread), 4),
                    "optimal_ask": round(float(r_px + 0.5 * optimal_total_spread), 4),
                    "mid_price": round(s, 4),
                }
            )

        return {
            "symbol": self.symbol,
            "mid_price": round(s, 4),
            "current_inventory_shares": round(q, 0),
            "reservation_price": round(reservation_price, 4),
            "optimal_bid_price": round(optimal_bid, 4),
            "optimal_ask_price": round(optimal_ask, 4),
            "optimal_spread_eur": round(optimal_total_spread, 4),
            "optimal_spread_bps": round(spread_bps, 2),
            "inventory_skew_bps": round(skew_bps, 2),
            "inventory_quote_schedule": inventory_curve,
        }

    def compute_vpin_and_hawkes_toxicity(self) -> dict[str, Any]:
        """Simulate 20 volume buckets for VPIN toxicity and Hawkes self-exciting intensity."""
        rng = np.random.default_rng(42)
        n_buckets = 20
        branching_ratio = self.hawkes_alpha / max(self.hawkes_beta, 1e-6)

        vpin_series: list[dict[str, float | int | str]] = []
        imbalances: list[float] = []
        intensity = self.hawkes_mu

        for b in range(1, n_buckets + 1):
            # Inject order-flow burst around bucket 14-17 proportional to branching ratio
            burst = 0.35 * branching_ratio if 13 <= b <= 17 else 0.0
            buy_share = float(np.clip(0.50 + burst + rng.normal(0.0, 0.12), 0.08, 0.94))
            sell_share = 1.0 - buy_share
            imb = abs(buy_share - sell_share)
            imbalances.append(imb)

            vpin_rolling = float(np.mean(imbalances[max(0, len(imbalances) - 8) :]))
            intensity = (
                self.hawkes_mu
                + (intensity - self.hawkes_mu) * math.exp(-self.hawkes_beta * 0.5)
                + self.hawkes_alpha * (1.0 + 2.2 * imb)
            )
            vpin_series.append(
                {
                    "volume_bucket": b,
                    "buy_volume_pct": round(buy_share * 100.0, 1),
                    "sell_volume_pct": round(sell_share * 100.0, 1),
                    "order_imbalance_pct": round(imb * 100.0, 1),
                    "vpin_toxicity": round(vpin_rolling, 4),
                    "hawkes_intensity_lambda": round(intensity, 3),
                }
            )

        current_vpin = float(vpin_series[-1]["vpin_toxicity"])
        peak_vpin = max(float(item["vpin_toxicity"]) for item in vpin_series)

        if peak_vpin >= 0.45 or branching_ratio >= 0.75:
            toxicity_regime = "CRITICAL - FLASH CRASH / ADVERSE SELECTION ALERT"
        elif peak_vpin >= 0.30 or branching_ratio >= 0.55:
            toxicity_regime = "ELEVATED - WIDEN QUOTES & REDUCE INVENTORY"
        else:
            toxicity_regime = "BENIGN - NORMAL TWO-SIDED LIQUIDITY PROVISION"

        return {
            "current_vpin_score": round(current_vpin, 4),
            "peak_vpin_score": round(peak_vpin, 4),
            "hawkes_branching_ratio_eta": round(branching_ratio, 4),
            "hawkes_stationary_intensity": round(
                self.hawkes_mu / max(1.0 - branching_ratio, 0.05), 3
            ),
            "toxicity_regime": toxicity_regime,
            "vpin_bucket_series": vpin_series,
        }


def compute_market_making_and_vpin(
    symbol: str = "STM.MI",
    mid_price: float = 38.50,
    inventory_q: float = 1_500.0,
    risk_aversion_gamma: float = 0.08,
    volatility_sigma: float = 0.022,
    order_book_density_kappa: float = 1.65,
    hawkes_alpha: float = 0.85,
    hawkes_beta: float = 1.40,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    engine = MarketMakingVpinEngine(
        symbol=symbol,
        mid_price=mid_price,
        inventory_q=inventory_q,
        risk_aversion_gamma=risk_aversion_gamma,
        volatility_sigma=volatility_sigma,
        order_book_density_kappa=order_book_density_kappa,
        hawkes_alpha=hawkes_alpha,
        hawkes_beta=hawkes_beta,
    )
    quotes = engine.compute_avellaneda_stoikov_quotes()
    tox = engine.compute_vpin_and_hawkes_toxicity()
    return {**quotes, **tox}
