"""Schwartz (1997) / Gibson-Schwartz (1990) 2-Factor Commodity Futures & Convenience Yield Engine.

Models spot commodity price S_t and stochastic instantaneous net convenience yield delta_t:
    dS_t / S_t = (r - delta_t) dt + sigma_1 dW_1^Q
    ddelta_t   = [kappa (alpha_star - delta_t)] dt + sigma_2 dW_2^Q
    dW_1^Q dW_2^Q = rho dt

Provides closed-form futures term structure F(S_0, delta_0, T), seasonality adjustment,
Contango/Backwardation regime classification, roll yield decomposition, term volatility
structure, and Kirk (1995) calendar/storage spread option pricing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class CommodityModelParams:
    """Parameters for the 2-Factor Gibson-Schwartz (1990) / Schwartz (1997) model."""

    commodity_name: str = "Brent Crude Oil (ICE)"
    spot_price: float = 82.50
    initial_convenience_yield: float = 0.085
    long_run_convenience_yield: float = 0.045
    mean_reversion_speed: float = 1.45
    spot_volatility: float = 0.32
    convenience_yield_volatility: float = 0.24
    correlation: float = 0.65
    risk_free_rate: float = 0.035
    storage_cost_rate: float = 0.025
    market_price_of_convenience_risk: float = 0.15
    seasonality_amplitude: float = 0.018
    seasonality_peak_fraction: float = 0.75  # Q3/Q4 seasonal peak


class SchwartzCommodityEngine:
    """Institutional 2-Factor Commodity Term Structure & Spread Option Engine."""

    def __init__(self, params: CommodityModelParams | None = None) -> None:
        self.params = params or CommodityModelParams()

    @property
    def alpha_star(self) -> float:
        """Risk-neutral long-run mean convenience yield: alpha* = alpha - lambda * sigma_2 / kappa."""
        p = self.params
        kappa = max(p.mean_reversion_speed, 1e-6)
        return p.long_run_convenience_yield - (
            p.market_price_of_convenience_risk * p.convenience_yield_volatility / kappa
        )

    def b_factor(self, maturity: float) -> float:
        """Sensitivity factor B(T) = (1 - exp(-kappa * T)) / kappa."""
        if maturity <= 0.0:
            return 0.0
        kappa = max(self.params.mean_reversion_speed, 1e-6)
        return (1.0 - math.exp(-kappa * maturity)) / kappa

    def a_factor(self, maturity: float) -> float:
        """Closed-form intercept A(T) in log-futures price ln F(S, delta, T) = ln S + A(T) - B(T)*delta."""
        if maturity <= 0.0:
            return 0.0
        p = self.params
        kappa = max(p.mean_reversion_speed, 1e-6)
        s1 = p.spot_volatility
        s2 = p.convenience_yield_volatility
        rho = np.clip(p.correlation, -0.999, 0.999)
        r = p.risk_free_rate
        a_star = self.alpha_star

        term1 = (r - a_star + 0.5 * (s2**2) / (kappa**2) - (rho * s1 * s2) / kappa) * maturity
        term2 = 0.25 * (s2**2) * (1.0 - math.exp(-2.0 * kappa * maturity)) / (kappa**3)
        term3 = (a_star * kappa + rho * s1 * s2 - (s2**2) / kappa) * (
            1.0 - math.exp(-kappa * maturity)
        ) / (kappa**2)
        return float(term1 + term2 + term3)

    def futures_price(self, maturity: float, include_seasonality: bool = True) -> float:
        """Compute analytical 2-factor futures price F(S_0, delta_0, T)."""
        if maturity <= 0.0:
            return float(self.params.spot_price)
        p = self.params
        a_t = self.a_factor(maturity)
        b_t = self.b_factor(maturity)
        base_f = p.spot_price * math.exp(a_t - b_t * p.initial_convenience_yield)
        if include_seasonality and abs(p.seasonality_amplitude) > 1e-8:
            seasonal_factor = math.exp(
                p.seasonality_amplitude
                * math.cos(2.0 * math.pi * (maturity - p.seasonality_peak_fraction))
            )
            return float(base_f * seasonal_factor)
        return float(base_f)

    def futures_volatility(self, maturity: float) -> float:
        """Instantaneous volatility sigma_F(T) of the futures contract maturing at T."""
        if maturity <= 0.0:
            return float(self.params.spot_volatility)
        p = self.params
        b_t = self.b_factor(maturity)
        s1 = p.spot_volatility
        s2 = p.convenience_yield_volatility
        rho = np.clip(p.correlation, -0.999, 0.999)
        var_f = max(s1**2 + (s2**2) * (b_t**2) - 2.0 * rho * s1 * s2 * b_t, 1e-8)
        return float(math.sqrt(var_f))

    def expected_convenience_yield(self, maturity: float) -> float:
        """Expected convenience yield E^Q[delta_T] at horizon T."""
        if maturity <= 0.0:
            return float(self.params.initial_convenience_yield)
        kappa = max(self.params.mean_reversion_speed, 1e-6)
        w = math.exp(-kappa * maturity)
        return float(self.params.initial_convenience_yield * w + self.alpha_star * (1.0 - w))

    def price_calendar_spread_option(
        self,
        t1: float = 0.25,
        t2: float = 1.00,
        strike_spread: float = 0.0,
        is_call: bool = True,
    ) -> dict[str, float]:
        """Price a Calendar / Storage Spread Option max(F(t, T2) - F(t, T1) - K, 0) via Kirk's approximation."""
        t_exp = max(min(t1, t2), 1.0 / 365.0)
        f1 = self.futures_price(t1, include_seasonality=True)
        f2 = self.futures_price(t2, include_seasonality=True)
        vol1 = self.futures_volatility(t1)
        vol2 = self.futures_volatility(t2)

        # Correlation between two futures maturities under 2-factor Schwartz model
        b1 = self.b_factor(t1)
        b2 = self.b_factor(t2)
        p = self.params
        s1, s2, rho = p.spot_volatility, p.convenience_yield_volatility, p.correlation
        cov_12 = s1**2 - rho * s1 * s2 * (b1 + b2) + (s2**2) * b1 * b2
        corr_12 = float(np.clip(cov_12 / max(vol1 * vol2, 1e-8), -0.999, 0.999))

        denom = max(f1 + strike_spread, 1e-4)
        w1 = f1 / denom
        sigma_kirk = math.sqrt(
            max(vol2**2 + (vol1 * w1) ** 2 - 2.0 * corr_12 * vol2 * vol1 * w1, 1e-8)
        )
        f_ratio = max(f2 / denom, 1e-6)
        d1 = (math.log(f_ratio) + 0.5 * (sigma_kirk**2) * t_exp) / (
            sigma_kirk * math.sqrt(t_exp)
        )
        d2 = d1 - sigma_kirk * math.sqrt(t_exp)
        df = math.exp(-p.risk_free_rate * t_exp)

        if is_call:
            price = df * (f2 * float(norm.cdf(d1)) - denom * float(norm.cdf(d2)))
        else:
            price = df * (denom * float(norm.cdf(-d2)) - f2 * float(norm.cdf(-d1)))

        return {
            "t1_years": round(t1, 4),
            "t2_years": round(t2, 4),
            "f1_price": round(f1, 4),
            "f2_price": round(f2, 4),
            "calendar_spread_val": round(f2 - f1, 4),
            "strike_spread": round(strike_spread, 4),
            "kirk_composite_vol_pct": round(sigma_kirk * 100.0, 2),
            "futures_correlation": round(corr_12, 4),
            "option_price": round(max(price, 0.0), 4),
        }

    def analyze_term_structure(
        self, maturities: list[float] | None = None
    ) -> dict[str, Any]:
        """Build full commodity futures curve, roll yield profile, and storage spread valuation."""
        if maturities is None:
            maturities = [
                1 / 12,
                0.25,
                0.50,
                0.75,
                1.0,
                1.5,
                2.0,
                3.0,
                4.0,
                5.0,
            ]

        p = self.params
        spot = p.spot_price
        curve_nodes: list[dict[str, float | str]] = []

        for t in sorted(maturities):
            f_unadj = self.futures_price(t, include_seasonality=False)
            f_seas = self.futures_price(t, include_seasonality=True)
            cost_of_carry_f = spot * math.exp((p.risk_free_rate + p.storage_cost_rate) * t)
            roll_yield_ann = math.log(spot / max(f_seas, 1e-6)) / max(t, 1e-6)
            vol_f = self.futures_volatility(t)
            exp_cy = self.expected_convenience_yield(t)

            curve_nodes.append(
                {
                    "maturity_years": round(t, 4),
                    "tenor_label": f"{int(round(t * 12))}M" if t < 1.0 else f"{t:.1f}Y",
                    "futures_price_seasonal": round(f_seas, 4),
                    "futures_price_structural": round(f_unadj, 4),
                    "cost_of_carry_benchmark": round(cost_of_carry_f, 4),
                    "expected_convenience_yield_pct": round(exp_cy * 100.0, 2),
                    "implied_roll_yield_ann_pct": round(roll_yield_ann * 100.0, 2),
                    "term_volatility_pct": round(vol_f * 100.0, 2),
                    "basis_vs_spot": round(f_seas - spot, 4),
                }
            )

        f_front = float(curve_nodes[0]["futures_price_seasonal"])
        f_1y = self.futures_price(1.0, include_seasonality=False)
        f_long = float(curve_nodes[-1]["futures_price_seasonal"])

        slope_front_1y = f_1y - spot
        slope_1y_long = f_long - f_1y

        if slope_front_1y < -0.25 and slope_1y_long < 0.25:
            regime = "BACKWARDATION"
        elif slope_front_1y > 0.25 and slope_1y_long > -0.25:
            regime = "CONTANGO"
        elif (slope_front_1y * slope_1y_long) < 0:
            regime = "HUMPED / TRANSITIONAL"
        else:
            regime = "FLAT"

        spread_opt = self.price_calendar_spread_option(
            t1=0.25, t2=1.0, strike_spread=0.0, is_call=True
        )

        return {
            "commodity_name": p.commodity_name,
            "spot_price": round(spot, 4),
            "initial_convenience_yield_pct": round(p.initial_convenience_yield * 100.0, 2),
            "long_run_convenience_yield_pct": round(p.long_run_convenience_yield * 100.0, 2),
            "risk_neutral_alpha_star_pct": round(self.alpha_star * 100.0, 2),
            "mean_reversion_speed_kappa": round(p.mean_reversion_speed, 4),
            "half_life_months": round(
                (math.log(2.0) / max(p.mean_reversion_speed, 1e-6)) * 12.0, 2
            ),
            "market_regime": regime,
            "front_month_price": round(f_front, 4),
            "one_year_futures_price": round(f_1y, 4),
            "long_end_futures_price": round(f_long, 4),
            "one_year_roll_yield_pct": round(math.log(spot / max(f_1y, 1e-6)) * 100.0, 2),
            "calendar_spread_option_3m_12m": spread_opt,
            "term_structure": curve_nodes,
        }


def compute_commodity_term_structure(
    commodity_name: str = "Brent Crude Oil (ICE)",
    spot_price: float = 82.50,
    initial_convenience_yield: float = 0.085,
    long_run_convenience_yield: float = 0.045,
    mean_reversion_speed: float = 1.45,
    spot_volatility: float = 0.32,
    convenience_yield_volatility: float = 0.24,
    correlation: float = 0.65,
    risk_free_rate: float = 0.035,
    storage_cost_rate: float = 0.025,
    seasonality_amplitude: float = 0.018,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    params = CommodityModelParams(
        commodity_name=commodity_name,
        spot_price=spot_price,
        initial_convenience_yield=initial_convenience_yield,
        long_run_convenience_yield=long_run_convenience_yield,
        mean_reversion_speed=mean_reversion_speed,
        spot_volatility=spot_volatility,
        convenience_yield_volatility=convenience_yield_volatility,
        correlation=correlation,
        risk_free_rate=risk_free_rate,
        storage_cost_rate=storage_cost_rate,
        seasonality_amplitude=seasonality_amplitude,
    )
    engine = SchwartzCommodityEngine(params=params)
    return engine.analyze_term_structure()
