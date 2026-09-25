"""Hull-White Short Rate & Longstaff-Schwartz Bermudan Swaptions Engine.

Implements:
1. One-Factor Gaussian Hull-White (1990) Short Rate Model:
   dr_t = [theta(t) - a * r_t] dt + sigma * dW_t
   with exact initial yield curve fitting and analytical zero-coupon bond prices P(t, T) = A(t,T) exp(-B(t,T) r_t).
2. Longstaff & Schwartz (2001) Least Squares Monte Carlo (LSMC) backward induction
   with polynomial basis functions for Bermudan Swaptions and Callable Bonds.
3. Decomposition of Bermudan value into European benchmark value + Early Exercise Premium,
   exercise probabilities across dates, and interest rate sensitivity Greeks (DV01, Vega).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class HullWhiteSpecs:
    """Model and contract specifications for Hull-White Bermudan Swaption."""

    notional: float = 10_000_000.0
    strike_rate: float = 0.030  # 3.0% fixed strike rate
    swap_maturity_years: float = 5.0  # Underlying swap end date (e.g. 5Y)
    bermudan_exercise_years: List[float] = field(default_factory=lambda: [1.0, 2.0, 3.0, 4.0])
    is_payer: bool = True  # True = Payer swaption (right to pay fixed), False = Receiver
    mean_reversion_a: float = 0.05  # Speed of mean reversion 'a'
    short_rate_vol_sigma: float = 0.010  # Short rate normal volatility (e.g. 100 bps)
    initial_short_rate: float = 0.030  # Flat or initial instantaneous forward rate f(0, t)
    yield_curve_slope: float = 0.001  # Upward slope of initial curve


@dataclass
class HullWhiteResult:
    """Valuation report for Bermudan Swaption and Callable Bond."""

    bermudan_swaption_pv_eur: float
    european_swaption_pv_eur: float
    early_exercise_premium_eur: float
    bermudan_price_bps: float
    callable_bond_pv_eur: float
    straight_bond_pv_eur: float
    embedded_call_option_eur: float
    exercise_schedule: List[Dict[str, Any]]
    rate_greeks: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "bermudan_swaption_pv_eur": round(self.bermudan_swaption_pv_eur, 2),
            "european_swaption_pv_eur": round(self.european_swaption_pv_eur, 2),
            "early_exercise_premium_eur": round(self.early_exercise_premium_eur, 2),
            "bermudan_price_bps": round(self.bermudan_price_bps, 2),
            "callable_bond_pv_eur": round(self.callable_bond_pv_eur, 2),
            "straight_bond_pv_eur": round(self.straight_bond_pv_eur, 2),
            "embedded_call_option_eur": round(self.embedded_call_option_eur, 2),
            "exercise_schedule": self.exercise_schedule,
            "rate_greeks": {k: round(v, 2) for k, v in self.rate_greeks.items()},
        }


class HullWhiteEngine:
    """1-Factor Hull-White LSMC Engine for Bermudan Swaptions and Callable Bonds."""

    def __init__(self, specs: HullWhiteSpecs, n_paths: int = 4000, seed: int = 42) -> None:
        """Initialize Hull-White engine."""
        self.specs = specs
        self.n_paths = n_paths
        self.seed = seed

    def zero_rate_0(self, t: float, rate_shift: float = 0.0) -> float:
        """Initial market zero rate z(0, t)."""
        return self.specs.initial_short_rate + rate_shift + self.specs.yield_curve_slope * np.log1p(t)

    def discount_0(self, t: float, rate_shift: float = 0.0) -> float:
        """Initial market discount factor P(0, t)."""
        if t <= 0.0:
            return 1.0
        return float(np.exp(-self.zero_rate_0(t, rate_shift) * t))

    def inst_forward_0(self, t: float, rate_shift: float = 0.0) -> float:
        """Instantaneous forward rate f(0, t) = -d/dt ln P(0, t)."""
        eps = 1e-4
        return -(np.log(self.discount_0(t + eps, rate_shift)) - np.log(self.discount_0(max(0.0, t - eps), rate_shift))) / (2.0 * eps)

    def hw_bond_price(
        self,
        t: float,
        T: float,
        r_t: np.ndarray,
        rate_shift: float = 0.0,
        vol_shift: float = 0.0,
    ) -> np.ndarray:
        """Analytical zero-coupon bond price P(t, T) given short rate state r(t) under Hull-White.

        P(t, T) = A(t, T) * exp(-B(t, T) * r(t))
        B(t, T) = (1 - exp(-a * (T - t))) / a
        ln A(t, T) = ln(P(0, T) / P(0, t)) + B(t, T) * f(0, t) - (sigma^2 / (4a)) * (1 - exp(-2*a*t)) * B(t, T)^2
        """
        if T <= t:
            return np.ones_like(r_t)

        a = max(1e-4, self.specs.mean_reversion_a)
        sigma = max(1e-4, self.specs.short_rate_vol_sigma + vol_shift)

        b_tt = (1.0 - np.exp(-a * (T - t))) / a
        p_0t = self.discount_0(t, rate_shift)
        p_0T = self.discount_0(T, rate_shift)
        f_0t = self.inst_forward_0(t, rate_shift)

        ln_a = np.log(p_0T / p_0t) + b_tt * f_0t - (sigma**2 / (4.0 * a)) * (1.0 - np.exp(-2.0 * a * t)) * (b_tt**2)
        return np.exp(ln_a - b_tt * r_t)

    def _simulate_short_rate_paths(
        self, time_grid: np.ndarray, rate_shift: float = 0.0, vol_shift: float = 0.0
    ) -> np.ndarray:
        """Simulate Hull-White short rate r(t) = x(t) + alpha(t) where dx(t) = -a x(t) dt + sigma dW_t."""
        rng = np.random.default_rng(self.seed)
        a = max(1e-4, self.specs.mean_reversion_a)
        sigma = max(1e-4, self.specs.short_rate_vol_sigma + vol_shift)

        n_steps = len(time_grid)
        r_paths = np.zeros((self.n_paths, n_steps), dtype=float)

        # alpha(t) = f(0, t) + (sigma^2 / (2 * a^2)) * (1 - exp(-a * t))^2
        def alpha_fn(t_val: float) -> float:
            return self.inst_forward_0(t_val, rate_shift) + (sigma**2 / (2.0 * a**2)) * ((1.0 - np.exp(-a * t_val)) ** 2)

        x_curr = np.zeros(self.n_paths, dtype=float)
        r_paths[:, 0] = alpha_fn(time_grid[0])

        for idx in range(1, n_steps):
            dt = time_grid[idx] - time_grid[idx - 1]
            t_curr = time_grid[idx]
            # Exact Ornstein-Uhlenbeck transition for x(t)
            exp_adt = np.exp(-a * dt)
            var_x = (sigma**2 / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * dt))
            z = rng.standard_normal(self.n_paths)
            x_curr = x_curr * exp_adt + np.sqrt(max(1e-12, var_x)) * z
            r_paths[:, idx] = x_curr + alpha_fn(t_curr)

        return r_paths

    def swap_intrinsic_payoff(
        self,
        t_ex: float,
        r_t: np.ndarray,
        rate_shift: float = 0.0,
        vol_shift: float = 0.0,
    ) -> np.ndarray:
        """Calculate intrinsic value of exercising the swap at time t_ex across all simulated paths."""
        maturity = self.specs.swap_maturity_years
        if t_ex >= maturity:
            return np.zeros_like(r_t)

        # Annual coupon payment dates from t_ex + 1.0 up to maturity
        pay_dates = np.arange(t_ex + 1.0, maturity + 0.01, 1.0)
        if len(pay_dates) == 0:
            pay_dates = np.array([maturity])

        annuity = np.zeros_like(r_t)
        for t_pay in pay_dates:
            tau = 1.0
            annuity += tau * self.hw_bond_price(t_ex, float(t_pay), r_t, rate_shift, vol_shift)

        p_end = self.hw_bond_price(t_ex, maturity, r_t, rate_shift, vol_shift)
        # Floating leg value at reset date t_ex: Notional * (1 - P(t_ex, T_end))
        val_float = self.specs.notional * (1.0 - p_end)
        val_fixed = self.specs.notional * self.specs.strike_rate * annuity

        if self.specs.is_payer:
            swap_npv = val_float - val_fixed
        else:
            swap_npv = val_fixed - val_float

        return np.maximum(0.0, swap_npv)

    def price_bermudan_lsmc(
        self, rate_shift: float = 0.0, vol_shift: float = 0.0
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Run Longstaff-Schwartz Least Squares Monte Carlo backward induction."""
        ex_dates = sorted([t for t in self.specs.bermudan_exercise_years if 0.0 < t < self.specs.swap_maturity_years])
        if not ex_dates:
            ex_dates = [1.0, 2.0, 3.0, 4.0]

        time_grid = np.array([0.0] + ex_dates, dtype=float)
        r_paths = self._simulate_short_rate_paths(time_grid, rate_shift, vol_shift)

        n_ex = len(ex_dates)
        # Compute intrinsic payoffs at all exercise dates: shape (n_paths, n_ex)
        intrinsic_mat = np.zeros((self.n_paths, n_ex), dtype=float)
        for j, t_ex in enumerate(ex_dates):
            intrinsic_mat[:, j] = self.swap_intrinsic_payoff(t_ex, r_paths[:, j + 1], rate_shift, vol_shift)

        # European swaption value (only exercising at the first exercise date T_1)
        t_first = ex_dates[0]
        r_avg_0_1 = 0.5 * (r_paths[:, 0] + r_paths[:, 1])
        df_0_1 = np.exp(-r_avg_0_1 * t_first)
        european_pv = float(np.mean(intrinsic_mat[:, 0] * df_0_1))

        # Backward induction for Bermudan Swaption
        cashflow = intrinsic_mat[:, -1].copy()
        exercise_idx = np.where(cashflow > 0, n_ex - 1, -1)

        for j in range(n_ex - 2, -1, -1):
            t_curr = ex_dates[j]
            t_next = ex_dates[j + 1]
            dt = t_next - t_curr

            # Discount cashflow one step back from t_{j+1} to t_j
            r_step = 0.5 * (r_paths[:, j + 1] + r_paths[:, j + 2])
            df_step = np.exp(-r_step * dt)
            cashflow = cashflow * df_step

            imm_ex = intrinsic_mat[:, j]
            itm_mask = imm_ex > 0.0

            if np.sum(itm_mask) > 15:
                r_itm = r_paths[itm_mask, j + 1]
                y_itm = cashflow[itm_mask]
                # Polynomial basis: [1, r, r^2, r^3]
                X = np.column_stack([np.ones_like(r_itm), r_itm, r_itm**2, r_itm**3])
                coeffs, _, _, _ = np.linalg.lstsq(X, y_itm, rcond=None)
                continuation_est = X @ coeffs

                # Exercise where immediate payoff exceeds estimated continuation value
                ex_now_itm = imm_ex[itm_mask] > continuation_est
                full_ex_mask = np.zeros(self.n_paths, dtype=bool)
                full_ex_mask[itm_mask] = ex_now_itm

                cashflow = np.where(full_ex_mask, imm_ex, cashflow)
                exercise_idx = np.where(full_ex_mask, j, exercise_idx)

        # Discount from first exercise date T_1 back to t=0
        bermudan_pv = float(np.mean(cashflow * df_0_1))
        bermudan_pv = max(european_pv, bermudan_pv)

        schedule: List[Dict[str, Any]] = []
        for j, t_ex in enumerate(ex_dates):
            ex_prob = float(np.mean(exercise_idx == j))
            avg_intr = float(np.mean(intrinsic_mat[:, j]))
            schedule.append(
                {
                    "exercise_date_years": round(t_ex, 2),
                    "underlying_swap_tenor_years": round(self.specs.swap_maturity_years - t_ex, 2),
                    "expected_intrinsic_eur": round(avg_intr, 2),
                    "optimal_exercise_prob_pct": round(ex_prob * 100.0, 2),
                }
            )

        return bermudan_pv, european_pv, schedule

    def evaluate(self) -> HullWhiteResult:
        """Evaluate Bermudan Swaption, Callable Bond, and Interest Rate Greeks."""
        berm_pv, euro_pv, schedule = self.price_bermudan_lsmc()
        early_ex_prem = max(0.0, berm_pv - euro_pv)

        # Straight bond vs Callable bond valuation
        maturity = int(round(self.specs.swap_maturity_years))
        coupon = self.specs.strike_rate
        straight_pv = 0.0
        for t_k in range(1, maturity + 1):
            straight_pv += self.specs.notional * coupon * self.discount_0(float(t_k))
        straight_pv += self.specs.notional * self.discount_0(float(maturity))

        callable_pv = straight_pv - berm_pv

        # Rate Greeks via finite differences (10 bps rate shift, 10 bps vol shift)
        berm_up, _, _ = self.price_bermudan_lsmc(rate_shift=+0.0010)
        berm_dn, _, _ = self.price_bermudan_lsmc(rate_shift=-0.0010)
        dv01 = (berm_up - berm_dn) / 20.0  # Per 1 bp shift

        berm_vol_up, _, _ = self.price_bermudan_lsmc(vol_shift=+0.0010)
        normal_vega = (berm_vol_up - berm_pv) / 10.0  # Per 1 bp normal vol

        return HullWhiteResult(
            bermudan_swaption_pv_eur=berm_pv,
            european_swaption_pv_eur=euro_pv,
            early_exercise_premium_eur=early_ex_prem,
            bermudan_price_bps=(berm_pv / self.specs.notional) * 10000.0,
            callable_bond_pv_eur=callable_pv,
            straight_bond_pv_eur=straight_pv,
            embedded_call_option_eur=berm_pv,
            exercise_schedule=schedule,
            rate_greeks={
                "dv01_eur_per_bp": dv01,
                "normal_vega_eur_per_bp": normal_vega,
            },
        )


def compute_hull_white_swaptions(
    notional: float = 10_000_000.0,
    strike_rate: float = 0.030,
    swap_maturity_years: float = 5.0,
    bermudan_exercise_years: Optional[List[float]] = None,
    is_payer: bool = True,
    mean_reversion_a: float = 0.05,
    short_rate_vol_sigma: float = 0.010,
    initial_short_rate: float = 0.030,
    n_paths: int = 3000,
) -> Dict[str, Any]:
    """Top-level calculation function for Hull-White Bermudan Swaptions & Callable Bonds."""
    if bermudan_exercise_years is None:
        bermudan_exercise_years = [1.0, 2.0, 3.0, 4.0]

    specs = HullWhiteSpecs(
        notional=notional,
        strike_rate=strike_rate,
        swap_maturity_years=swap_maturity_years,
        bermudan_exercise_years=bermudan_exercise_years,
        is_payer=is_payer,
        mean_reversion_a=mean_reversion_a,
        short_rate_vol_sigma=short_rate_vol_sigma,
        initial_short_rate=initial_short_rate,
    )
    engine = HullWhiteEngine(specs=specs, n_paths=n_paths)
    res = engine.evaluate()
    res_dict = res.to_dict()
    res_dict["engine_version"] = "9.15.0"
    return res_dict
