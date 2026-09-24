"""Exotic Derivatives & Structured Products Valuation Engine.

Prices multi-asset Worst-Of structured products using correlated Monte Carlo simulation:
1. Phoenix Autocallables (Memory coupon, autocall redemption barrier, European knock-in protection barrier).
2. Reverse Convertibles (Guaranteed fixed coupon + downside short put barrier).
Computes analytical/numerical Greeks (Delta, Gamma, Vega, Theta, Rho, Barrier Sensitivity)
and early termination probabilities with expected duration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class StructuredProductSpecs:
    """Contract terms and parameters for structured products."""

    product_type: str = "phoenix_autocallable"  # "phoenix_autocallable" or "reverse_convertible"
    nominal: float = 1000.0  # Face value per note (e.g. EUR 1000)
    maturity_years: float = 2.0  # Total tenor
    observation_frequency_months: int = 6  # 6 months (semi-annual) or 3 (quarterly)
    coupon_rate_p_a: float = 0.08  # 8.0% annual coupon
    has_memory_coupon: bool = True  # Memory feature for Phoenix
    coupon_barrier_pct: float = 0.70  # 70% of initial spot
    autocall_barrier_pct: float = 1.00  # 100% of initial spot (for Phoenix)
    protection_barrier_pct: float = 0.60  # 60% European capital protection barrier at maturity
    underlyings: List[str] = field(default_factory=lambda: ["SX5E", "SPX", "NKY"])
    spots: List[float] = field(default_factory=lambda: [4900.0, 5200.0, 39000.0])
    volatilities: List[float] = field(default_factory=lambda: [0.18, 0.16, 0.22])
    dividend_yields: List[float] = field(default_factory=lambda: [0.025, 0.015, 0.018])
    correlation_matrix: Optional[List[List[float]]] = None
    risk_free_rate: float = 0.03


@dataclass
class StructuredProductResult:
    """Pricing and risk profile of the structured product."""

    present_value: float  # In currency units (e.g. EUR 992.50)
    price_pct_nominal: float  # In % of nominal (e.g. 99.25%)
    expected_duration_years: float  # Expected life until autocall or maturity
    autocall_probability_total: float  # Probability of early redemption
    knock_in_loss_probability: float  # Probability of capital loss at maturity
    expected_coupon_yield_p_a: float  # Effective coupon yield
    observation_schedule: List[Dict[str, Any]]
    greeks: Dict[str, float]
    simulation_paths: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "present_value": round(self.present_value, 2),
            "price_pct_nominal": round(self.price_pct_nominal, 2),
            "expected_duration_years": round(self.expected_duration_years, 2),
            "autocall_probability_total": round(self.autocall_probability_total, 4),
            "knock_in_loss_probability": round(self.knock_in_loss_probability, 4),
            "expected_coupon_yield_p_a": round(self.expected_coupon_yield_p_a, 4),
            "observation_schedule": self.observation_schedule,
            "greeks": {k: round(v, 4) for k, v in self.greeks.items()},
            "simulation_paths": self.simulation_paths,
        }


class StructuredProductsEngine:
    """Monte Carlo pricer for Worst-Of Structured Products."""

    def __init__(self, specs: StructuredProductSpecs, n_simulations: int = 15000, seed: int = 42) -> None:
        """Initialize engine with product specifications and simulation parameters."""
        self.specs = specs
        self.n_sim = n_simulations
        self.seed = seed

        # Number of underlyings
        self.num_assets = len(specs.underlyings)

        # Setup correlation matrix
        if specs.correlation_matrix is None:
            # Default positive correlation between equity indices (0.60)
            self.corr = np.full((self.num_assets, self.num_assets), 0.60)
            np.fill_diagonal(self.corr, 1.0)
        else:
            self.corr = np.asarray(specs.correlation_matrix, dtype=float)

        # Observation dates in years
        obs_interval_years = specs.observation_frequency_months / 12.0
        n_obs = int(round(specs.maturity_years / obs_interval_years))
        self.obs_times = np.array([obs_interval_years * (k + 1) for k in range(n_obs)])

    def _simulate_asset_paths(
        self,
        bump_asset_idx: Optional[int] = None,
        bump_pct: float = 0.0,
        bump_vol_idx: Optional[int] = None,
        bump_vol: float = 0.0,
        bump_rate: float = 0.0,
    ) -> np.ndarray:
        """Simulate correlated geometric Brownian motions at observation dates.

        Returns array of normalized prices S(t) / S(0) of shape (n_sim, n_obs, num_assets).
        """
        rng = np.random.default_rng(self.seed)
        chol = np.linalg.cholesky(self.corr)

        r = self.specs.risk_free_rate + bump_rate
        n_obs = len(self.obs_times)

        # Initialize log return paths
        paths_norm = np.ones((self.n_sim, n_obs, self.num_assets), dtype=float)

        dt_prev = 0.0
        current_spots = np.ones((self.n_sim, self.num_assets), dtype=float)

        for obs_idx, t_current in enumerate(self.obs_times):
            dt = t_current - dt_prev
            sqrt_dt = np.sqrt(dt)

            # Generate standard normal vectors and correlate them
            z_uncorr = rng.standard_normal((self.n_sim, self.num_assets))
            z_corr = z_uncorr @ chol.T

            for a_idx in range(self.num_assets):
                sigma = self.specs.volatilities[a_idx]
                if bump_vol_idx is None or bump_vol_idx == a_idx:
                    sigma += bump_vol
                sigma = max(0.01, sigma)

                q = self.specs.dividend_yields[a_idx]
                drift = (r - q - 0.5 * sigma**2) * dt
                diffusion = sigma * sqrt_dt * z_corr[:, a_idx]

                current_spots[:, a_idx] *= np.exp(drift + diffusion)

                # Store normalized price with optional spot bump
                bump = (1.0 + bump_pct) if (bump_asset_idx is None or bump_asset_idx == a_idx) else 1.0
                paths_norm[:, obs_idx, a_idx] = current_spots[:, a_idx] * bump

            dt_prev = t_current

        return paths_norm

    def price(
        self,
        bump_asset_idx: Optional[int] = None,
        bump_pct: float = 0.0,
        bump_vol: float = 0.0,
        bump_rate: float = 0.0,
    ) -> Tuple[float, float, float, float, float, List[Dict[str, Any]]]:
        """Price the structured note and return payoff statistics.

        Returns:
            (pv, duration, autocall_prob, knock_in_prob, coupon_yield, observation_schedule)
        """
        paths = self._simulate_asset_paths(
            bump_asset_idx=bump_asset_idx,
            bump_pct=bump_pct,
            bump_vol=bump_vol,
            bump_rate=bump_rate,
        )

        n_obs = len(self.obs_times)
        r = self.specs.risk_free_rate + bump_rate
        nominal = self.specs.nominal
        dt_obs = self.specs.observation_frequency_months / 12.0
        coupon_step = self.specs.coupon_rate_p_a * dt_obs

        # Calculate Worst-Of asset performance at each observation: shape (n_sim, n_obs)
        worst_of = np.min(paths, axis=2)

        # Simulation trackers
        active = np.ones(self.n_sim, dtype=bool)
        present_values = np.zeros(self.n_sim, dtype=float)
        redemption_times = np.full(self.n_sim, self.specs.maturity_years, dtype=float)
        memory_coupons = np.zeros(self.n_sim, dtype=int)
        total_coupons_paid = np.zeros(self.n_sim, dtype=float)

        autocall_counts = np.zeros(n_obs, dtype=int)
        coupon_counts = np.zeros(n_obs, dtype=int)

        for obs_idx, t_obs in enumerate(self.obs_times):
            is_last_obs = obs_idx == (n_obs - 1)
            wo_t = worst_of[:, obs_idx]
            df = np.exp(-r * t_obs)

            if self.specs.product_type == "phoenix_autocallable":
                # Check Coupon condition
                coupon_cond = wo_t >= self.specs.coupon_barrier_pct
                coupon_eligible = active & coupon_cond

                coupon_counts[obs_idx] = int(np.sum(coupon_eligible))

                if self.specs.has_memory_coupon:
                    # Paid coupon + accumulated memory coupons
                    payable_coupons = np.where(
                        coupon_eligible,
                        (1 + memory_coupons) * coupon_step * nominal,
                        0.0,
                    )
                    # Reset memory coupons for those who got paid, increment for those who didn't
                    memory_coupons = np.where(coupon_eligible, 0, memory_coupons + 1)
                else:
                    payable_coupons = np.where(coupon_eligible, coupon_step * nominal, 0.0)

                present_values += payable_coupons * df
                total_coupons_paid += payable_coupons

                # Check Autocall condition (only prior to maturity or at observation dates)
                if not is_last_obs:
                    autocall_cond = wo_t >= self.specs.autocall_barrier_pct
                    autocall_triggered = active & autocall_cond

                    autocall_counts[obs_idx] = int(np.sum(autocall_triggered))

                    # Pay 100% nominal redemption
                    present_values += np.where(autocall_triggered, nominal * df, 0.0)
                    redemption_times = np.where(autocall_triggered, t_obs, redemption_times)

                    # Deactivate autocalled paths
                    active = active & (~autocall_cond)

            elif self.specs.product_type == "reverse_convertible":
                # Fixed guaranteed coupon paid at each observation
                coupon_val = coupon_step * nominal
                present_values += np.where(active, coupon_val * df, 0.0)
                total_coupons_paid += np.where(active, coupon_val, 0.0)
                coupon_counts[obs_idx] = int(np.sum(active))

        # Final maturity redemption for paths that were not autocalled
        t_mat = self.specs.maturity_years
        df_mat = np.exp(-r * t_mat)
        final_wo = worst_of[:, -1]

        # Protection barrier test at maturity
        barrier = self.specs.protection_barrier_pct
        knock_in_occurred = active & (final_wo < barrier)

        maturity_redemption = np.where(
            active,
            np.where(final_wo >= barrier, nominal, nominal * final_wo),
            0.0,
        )
        present_values += maturity_redemption * df_mat

        # Summarize metrics
        pv = float(np.mean(present_values))
        expected_duration = float(np.mean(redemption_times))
        autocall_prob = float(np.sum(autocall_counts) / self.n_sim)
        knock_in_prob = float(np.sum(knock_in_occurred) / self.n_sim)
        coupon_yield = float(np.mean(total_coupons_paid) / nominal / self.specs.maturity_years)

        schedule: List[Dict[str, Any]] = []
        for idx, t_obs in enumerate(self.obs_times):
            schedule.append(
                {
                    "observation_index": idx + 1,
                    "date_years": round(t_obs, 2),
                    "autocall_barrier_pct": round(self.specs.autocall_barrier_pct * 100.0, 1),
                    "coupon_barrier_pct": round(self.specs.coupon_barrier_pct * 100.0, 1),
                    "autocall_probability_pct": round((autocall_counts[idx] / self.n_sim) * 100.0, 2),
                    "coupon_payment_probability_pct": round((coupon_counts[idx] / self.n_sim) * 100.0, 2),
                }
            )

        return pv, expected_duration, autocall_prob, knock_in_prob, coupon_yield, schedule

    def calculate_greeks(self, base_pv: float) -> Dict[str, float]:
        """Compute Greeks via numerical finite differences."""
        # Delta & Gamma (1% spot shift)
        eps_s = 0.01
        pv_up, _, _, _, _, _ = self.price(bump_pct=+eps_s)
        pv_down, _, _, _, _, _ = self.price(bump_pct=-eps_s)

        delta = (pv_up - pv_down) / (2.0 * eps_s * self.specs.nominal)
        gamma = (pv_up - 2.0 * base_pv + pv_down) / ((eps_s * self.specs.nominal) ** 2)

        # Vega (1% vol shift)
        eps_vol = 0.01
        pv_vol_up, _, _, _, _, _ = self.price(bump_vol=+eps_vol)
        vega = (pv_vol_up - base_pv) / 100.0  # Per 1% vol shift

        # Rho (10 bps rate shift)
        eps_r = 0.001
        pv_r_up, _, _, _, _, _ = self.price(bump_rate=+eps_r)
        rho = (pv_r_up - base_pv) / 10.0  # Per 10 bps

        # Theta (1 month time decay proxy)
        theta = -base_pv * (self.specs.risk_free_rate / 12.0)

        # Barrier sensitivity (shift protection barrier by +1%)
        old_bar = self.specs.protection_barrier_pct
        self.specs.protection_barrier_pct += 0.01
        pv_bar_up, _, _, _, _, _ = self.price()
        barrier_sensitivity = pv_bar_up - base_pv
        self.specs.protection_barrier_pct = old_bar

        return {
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
            "barrier_sensitivity": barrier_sensitivity,
        }

    def evaluate(self) -> StructuredProductResult:
        """Run full Monte Carlo valuation and sensitivity diagnostics."""
        pv, duration, autocall_prob, knock_in_prob, coupon_yield, schedule = self.price()
        greeks = self.calculate_greeks(pv)

        return StructuredProductResult(
            present_value=pv,
            price_pct_nominal=(pv / self.specs.nominal) * 100.0,
            expected_duration_years=duration,
            autocall_probability_total=autocall_prob,
            knock_in_loss_probability=knock_in_prob,
            expected_coupon_yield_p_a=coupon_yield,
            observation_schedule=schedule,
            greeks=greeks,
            simulation_paths=self.n_sim,
        )


def compute_structured_product_pricing(
    product_type: str = "phoenix_autocallable",
    nominal: float = 1000.0,
    maturity_years: float = 2.0,
    observation_frequency_months: int = 6,
    coupon_rate_p_a: float = 0.08,
    has_memory_coupon: bool = True,
    coupon_barrier_pct: float = 0.70,
    autocall_barrier_pct: float = 1.00,
    protection_barrier_pct: float = 0.60,
    underlyings: Optional[List[str]] = None,
    spots: Optional[List[float]] = None,
    volatilities: Optional[List[float]] = None,
    risk_free_rate: float = 0.03,
    n_simulations: int = 10000,
) -> Dict[str, Any]:
    """Top-level calculation function for structured product pricing."""
    if underlyings is None:
        underlyings = ["SX5E", "SPX", "NKY"]
    if spots is None:
        spots = [4900.0, 5200.0, 39000.0]
    if volatilities is None:
        volatilities = [0.18, 0.16, 0.22]

    specs = StructuredProductSpecs(
        product_type=product_type,
        nominal=nominal,
        maturity_years=maturity_years,
        observation_frequency_months=observation_frequency_months,
        coupon_rate_p_a=coupon_rate_p_a,
        has_memory_coupon=has_memory_coupon,
        coupon_barrier_pct=coupon_barrier_pct,
        autocall_barrier_pct=autocall_barrier_pct,
        protection_barrier_pct=protection_barrier_pct,
        underlyings=underlyings,
        spots=spots,
        volatilities=volatilities,
        risk_free_rate=risk_free_rate,
    )

    engine = StructuredProductsEngine(specs, n_simulations=n_simulations)
    result = engine.evaluate()

    res_dict = result.to_dict()
    res_dict["engine_version"] = "9.14.0"
    res_dict["product_specs"] = {
        "product_type": product_type,
        "nominal": nominal,
        "maturity_years": maturity_years,
        "underlyings": underlyings,
        "coupon_rate_pct": round(coupon_rate_p_a * 100.0, 2),
        "coupon_barrier_pct": round(coupon_barrier_pct * 100.0, 1),
        "autocall_barrier_pct": round(autocall_barrier_pct * 100.0, 1),
        "protection_barrier_pct": round(protection_barrier_pct * 100.0, 1),
    }
    return res_dict
