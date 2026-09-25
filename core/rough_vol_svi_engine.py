"""Rough Volatility (Rough Bergomi H ~ 0.10) & Gatheral SVI Arbitrage-Free Surface Engine.

Implements:
1. Gatheral (2004, 2014) Raw SVI total implied variance parameterization:
       w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))
2. Durrleman's Butterfly Arbitrage Condition g(k) >= 0 across log-moneyness k = ln(K / F)
   and Calendar Spread Arbitrage Condition dw(k, T)/dT >= 0.
3. Rough Bergomi (Bayer, Friz & Gatheral 2016) fractional volatility model with Hurst
   exponent H in (0.05, 0.25), capturing power-law ATM skew explosion S(T) ~ T^{H - 1/2}.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SviParameters:
    """Gatheral Raw SVI parameters and Rough Bergomi Hurst exponent."""

    a: float = 0.012
    b: float = 0.185
    rho: float = -0.62
    m: float = -0.02
    sigma: float = 0.14
    hurst_h: float = 0.10
    eta_vol_of_vol: float = 1.85
    atm_base_vol: float = 0.20


class RoughVolSviEngine:
    """Rough Bergomi & SVI Arbitrage-Free Volatility Surface Engine."""

    def __init__(self, params: SviParameters | None = None) -> None:
        self.params = params or SviParameters()

    def svi_total_variance(self, k: np.ndarray | float, maturity: float = 1.0) -> np.ndarray:
        """Compute SVI total implied variance w(k, T) scaled with Rough Bergomi term skew."""
        p = self.params
        k_arr = np.asarray(k, dtype=float)
        t_eff = max(float(maturity), 1.0 / 365.0)

        # Rough Bergomi power-law scaling of effective wing slope b(T)
        rough_skew_scale = (t_eff ** (p.hurst_h + 0.5)) / max(1.0 ** (p.hurst_h + 0.5), 1e-6)
        b_t = p.b * rough_skew_scale
        a_t = max(p.a * t_eff, 1e-5)

        rad = np.sqrt((k_arr - p.m) ** 2 + (p.sigma**2))
        w = a_t + b_t * (p.rho * (k_arr - p.m) + rad)
        return np.maximum(w, 1e-6)

    def durrleman_butterfly_density(
        self, k: np.ndarray, maturity: float = 1.0
    ) -> np.ndarray:
        """Compute Durrleman's (2010) butterfly arbitrage function g(k); g(k) >= 0 guarantees no butterfly arbitrage."""
        dk = 1e-4
        w = self.svi_total_variance(k, maturity)
        w_plus = self.svi_total_variance(k + dk, maturity)
        w_minus = self.svi_total_variance(k - dk, maturity)

        w_prime = (w_plus - w_minus) / (2.0 * dk)
        w_double_prime = (w_plus - 2.0 * w + w_minus) / (dk**2)

        term1 = (1.0 - (k * w_prime) / (2.0 * w)) ** 2
        term2 = (w_prime**2) / 4.0 * (1.0 / w + 0.25)
        term3 = 0.5 * w_double_prime
        return term1 - term2 + term3

    def rough_bergomi_atm_skew(self, maturity: float) -> float:
        """Compute analytical Rough Bergomi ATM implied volatility skew d(sigma_imp)/dk at k=0."""
        p = self.params
        t_eff = max(float(maturity), 1.0 / 365.0)
        # Power-law scaling ~ rho * eta / (2 * H + 1) * T^(H - 0.5)
        coeff = (p.rho * p.eta_vol_of_vol) / (2.0 * p.hurst_h + 1.0)
        return float(coeff * (t_eff ** (p.hurst_h - 0.5)) * 0.22)

    def build_surface_and_diagnostics(
        self,
        maturities: list[float] | None = None,
        k_grid: list[float] | None = None,
    ) -> dict[str, Any]:
        """Generate full SVI + Rough Bergomi volatility surface and verify arbitrage-free conditions."""
        if maturities is None:
            maturities = [1 / 12, 0.25, 0.50, 1.0, 2.0]
        if k_grid is None:
            k_grid = [-0.30, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30]

        k_arr = np.array(k_grid, dtype=float)
        surface_rows: list[dict[str, Any]] = []
        min_durrleman_g = 999.0
        calendar_violations = 0
        prev_w: np.ndarray | None = None

        for t in sorted(maturities):
            w_t = self.svi_total_variance(k_arr, maturity=t)
            iv_pct = np.sqrt(w_t / max(t, 1e-6)) * 100.0
            g_t = self.durrleman_butterfly_density(k_arr, maturity=t)
            min_durrleman_g = min(min_durrleman_g, float(np.min(g_t)))

            if prev_w is not None:
                calendar_violations += int(np.sum(w_t < prev_w - 1e-6))
            prev_w = w_t

            atm_skew_rbergomi = self.rough_bergomi_atm_skew(t)
            classical_heston_skew = float(
                (self.params.rho * self.params.eta_vol_of_vol * 0.15)
                / (1.0 + 1.5 * t)
            )

            row: dict[str, Any] = {
                "maturity_years": round(t, 4),
                "tenor_label": f"{int(round(t * 12))}M" if t < 1.0 else f"{t:.1f}Y",
                "atm_implied_vol_pct": round(float(iv_pct[len(k_arr) // 2]), 2),
                "rough_bergomi_atm_skew": round(atm_skew_rbergomi, 4),
                "classical_markov_skew": round(classical_heston_skew, 4),
                "min_durrleman_density_g": round(float(np.min(g_t)), 4),
            }
            for k_val, iv_val in zip(k_arr, iv_pct):
                row[f"k_{k_val:+.2f}_vol_pct"] = round(float(iv_val), 2)
            surface_rows.append(row)

        butterfly_free = min_durrleman_g >= 0.0
        calendar_free = calendar_violations == 0

        return {
            "hurst_exponent_h": round(self.params.hurst_h, 4),
            "fractal_dimension_d": round(2.0 - self.params.hurst_h, 4),
            "svi_rho_correlation": round(self.params.rho, 4),
            "svi_wing_slope_b": round(self.params.b, 4),
            "min_durrleman_density_g": round(min_durrleman_g, 4),
            "butterfly_arbitrage_free": butterfly_free,
            "calendar_spread_arbitrage_free": calendar_free,
            "totally_arbitrage_free_surface": butterfly_free and calendar_free,
            "short_end_skew_1m": round(self.rough_bergomi_atm_skew(1 / 12), 4),
            "one_year_skew_12m": round(self.rough_bergomi_atm_skew(1.0), 4),
            "skew_power_law_exponent": round(self.params.hurst_h - 0.5, 4),
            "surface_term_structure": surface_rows,
        }


def compute_rough_vol_svi_surface(
    hurst_h: float = 0.10,
    svi_a: float = 0.012,
    svi_b: float = 0.185,
    svi_rho: float = -0.62,
    svi_sigma: float = 0.14,
    eta_vol_of_vol: float = 1.85,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    params = SviParameters(
        a=svi_a,
        b=svi_b,
        rho=svi_rho,
        sigma=svi_sigma,
        hurst_h=hurst_h,
        eta_vol_of_vol=eta_vol_of_vol,
    )
    engine = RoughVolSviEngine(params=params)
    return engine.build_surface_and_diagnostics()
