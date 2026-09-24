"""Heston Stochastic Volatility FFT Calibration Engine (Carr-Madan 1999).

Provides analytical characteristic functions, Carr-Madan Fast Fourier Transform (FFT)
for fast cross-strike European option pricing, Feller condition verification,
and L-BFGS-B / SLSQP surface calibration against market implied volatilities.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import optimize
from scipy.stats import norm


@dataclass
class HestonParameters:
    """Parameters of the Heston (1993) Stochastic Volatility Model.

    dS_t = (r - q) S_t dt + sqrt(v_t) S_t dW_t^S
    dv_t = kappa * (theta - v_t) dt + sigma_v * sqrt(v_t) dW_t^v
    corr(dW_t^S, dW_t^v) = rho
    """

    v0: float = 0.04  # Initial instantaneous variance (e.g. 0.2^2)
    kappa: float = 2.0  # Mean reversion speed
    theta: float = 0.04  # Long-term variance
    sigma_v: float = 0.3  # Volatility of variance (vol of vol)
    rho: float = -0.7  # Correlation between asset and variance brownian motions
    feller_condition_met: bool = field(init=False)
    feller_ratio: float = field(init=False)

    def __post_init__(self) -> None:
        """Validate parameters and compute Feller condition metrics."""
        denom = 2.0 * self.kappa * self.theta
        self.feller_ratio = (self.sigma_v**2) / denom if denom > 1e-12 else 999.0
        # Feller condition: 2 * kappa * theta > sigma_v^2 (i.e. feller_ratio < 1.0)
        self.feller_condition_met = denom > (self.sigma_v**2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary."""
        return {
            "v0": float(self.v0),
            "kappa": float(self.kappa),
            "theta": float(self.theta),
            "sigma_v": float(self.sigma_v),
            "rho": float(self.rho),
            "feller_condition_met": bool(self.feller_condition_met),
            "feller_ratio": round(float(self.feller_ratio), 4),
            "feller_comment": "Strictly positive variance process"
            if self.feller_condition_met
            else "Variance can touch zero (Feller condition violated)",
        }


@dataclass
class HestonCalibrationResult:
    """Output results of Heston surface calibration."""

    parameters: HestonParameters
    rmse: float
    mae: float
    pricing_comparison: List[Dict[str, Any]]
    calibration_time_seconds: float
    iterations: int
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize calibration results."""
        return {
            "parameters": self.parameters.to_dict(),
            "rmse": round(float(self.rmse), 6),
            "mae": round(float(self.mae), 6),
            "pricing_comparison": self.pricing_comparison,
            "calibration_time_seconds": round(float(self.calibration_time_seconds), 4),
            "iterations": int(self.iterations),
            "success": bool(self.success),
        }


def _bs_call_price(s0: float, k: float, t: float, r: float, q: float, sigma: float) -> float:
    """Analytical Black-Scholes call price."""
    if t <= 1e-6 or sigma <= 1e-6:
        return max(0.0, s0 * np.exp(-q * t) - k * np.exp(-r * t))
    d1 = (np.log(s0 / k) + (r - q + 0.5 * sigma**2) * t) / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    return float(s0 * np.exp(-q * t) * norm.cdf(d1) - k * np.exp(-r * t) * norm.cdf(d2))


def _bs_implied_vol(
    price: float, s0: float, k: float, t: float, r: float, q: float = 0.0
) -> float:
    """Invert Black-Scholes formula using Brent method to obtain implied volatility."""
    intrinsic = max(0.0, s0 * np.exp(-q * t) - k * np.exp(-r * t))
    if price <= intrinsic + 1e-6:
        return 0.001

    def objective(sig: float) -> float:
        return _bs_call_price(s0, k, t, r, q, sig) - price

    try:
        # Bracket between 0.001 (0.1%) and 4.0 (400%)
        return float(optimize.brentq(objective, 0.001, 4.0, maxiter=80))
    except Exception:
        return 0.20  # Fallback reasonable default


class HestonFFTEngine:
    """Carr-Madan (1999) Fast Fourier Transform engine for Heston (1993) model."""

    def __init__(self, s0: float = 100.0, r: float = 0.03, q: float = 0.0) -> None:
        """Initialize Heston FFT engine with spot and rate parameters."""
        self.s0 = float(s0)
        self.r = float(r)
        self.q = float(q)

    def characteristic_function(
        self, u: Union[complex, np.ndarray], t: float, params: HestonParameters
    ) -> Union[complex, np.ndarray]:
        """Lord-Kahl / Albrecher stable characteristic function of log(S_T).

        Uses the formulation without branch-cut discontinuity:
        phi(u) = E[exp(i * u * ln(S_T))]
        """
        i = 1j
        v0 = params.v0
        kappa = params.kappa
        theta = params.theta
        sigma = params.sigma_v
        rho = params.rho
        r = self.r
        q = self.q

        # Log asset spot
        x0 = np.log(self.s0)

        # Drift under risk-neutral measure
        drift = (r - q) * t

        # Characteristic function terms
        d = np.sqrt((kappa - i * rho * sigma * u) ** 2 + (sigma**2) * (i * u + u**2))
        g = (kappa - i * rho * sigma * u - d) / (kappa - i * rho * sigma * u + d)

        exp_neg_dt = np.exp(-d * t)
        c = (kappa * theta / (sigma**2)) * (
            (kappa - i * rho * sigma * u - d) * t - 2.0 * np.log((1.0 - g * exp_neg_dt) / (1.0 - g))
        )
        d_term = ((kappa - i * rho * sigma * u - d) / (sigma**2)) * (
            (1.0 - exp_neg_dt) / (1.0 - g * exp_neg_dt)
        )

        return np.exp(c + d_term * v0 + i * u * (x0 + drift))

    def price_options_fft(
        self,
        t: float,
        strikes: Union[List[float], np.ndarray],
        params: HestonParameters,
        alpha: float = 1.5,
        n: int = 4096,
        eta: float = 0.25,
    ) -> np.ndarray:
        """Carr-Madan FFT European Call option pricer for an array of strikes.

        Args:
            t: Time to maturity (years).
            strikes: Target strike prices.
            params: Heston model parameters.
            alpha: Carr-Madan damping factor (typically 1.5).
            n: Number of grid points (power of 2, e.g. 4096).
            eta: Grid spacing in frequency domain.

        Returns:
            np.ndarray of option call prices corresponding to input strikes.
        """
        strikes_arr = np.asarray(strikes, dtype=float)
        if t <= 1e-6:
            return np.maximum(0.0, self.s0 - strikes_arr)

        # Carr-Madan grid definition
        lambda_val = (2.0 * np.pi) / (n * eta)
        b = 0.5 * n * lambda_val

        # Frequency array v_j = j * eta for j = 0..N-1
        j = np.arange(n)
        v = j * eta

        # Simpson rule weights: 1/3 for ends, alternating 4/3 and 2/3
        simpson_weights = np.ones(n)
        simpson_weights[0] = 1.0 / 3.0
        simpson_weights[1::2] = 4.0 / 3.0
        simpson_weights[2::2] = 2.0 / 3.0
        simpson_weights[-1] = 1.0 / 3.0

        # Modified characteristic function: psi(v) = exp(-r*T) * phi(v - (alpha + 1)*i) / (alpha^2 + alpha - v^2 + i*(2*alpha + 1)*v)
        i = 1j
        u = v - (alpha + 1.0) * i
        phi_u = self.characteristic_function(u, t, params)

        denom = alpha**2 + alpha - v**2 + i * (2.0 * alpha + 1.0) * v
        psi = np.exp(-self.r * t) * phi_u / denom

        # Discounted Fourier integrand
        fft_input = np.exp(i * b * v) * psi * eta * simpson_weights
        # Perform Fast Fourier Transform
        fft_output = np.fft.fft(fft_input).real

        # Log-strike grid: k_u = -b + lambda * u
        k_grid = -b + lambda_val * j
        strikes_grid = np.exp(k_grid)

        # Raw Carr-Madan call prices on the grid
        c_grid = (np.exp(-alpha * k_grid) / np.pi) * fft_output

        # Interpolate call prices at the requested strikes
        call_prices = np.interp(strikes_arr, strikes_grid, c_grid)

        # Enforce no-arbitrage lower bound (intrinsic value)
        intrinsic = np.maximum(0.0, self.s0 * np.exp(-self.q * t) - strikes_arr * np.exp(-self.r * t))
        return np.maximum(intrinsic, call_prices)

    def price_call(self, t: float, strike: float, params: HestonParameters) -> float:
        """Price a single European call option."""
        return float(self.price_options_fft(t, [strike], params)[0])

    def price_put(self, t: float, strike: float, params: HestonParameters) -> float:
        """Price a single European put option via put-call parity."""
        call_val = self.price_call(t, strike, params)
        put_val = call_val - self.s0 * np.exp(-self.q * t) + strike * np.exp(-self.r * t)
        return float(max(0.0, put_val))

    def compute_volatility_surface(
        self,
        params: HestonParameters,
        maturities: Optional[List[float]] = None,
        strikes: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Compute complete implied volatility surface across strikes and maturities."""
        if maturities is None:
            maturities = [0.25, 0.5, 1.0, 2.0]
        if strikes is None:
            strikes = [
                round(self.s0 * m, 2)
                for m in [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]
            ]

        surface_points: List[Dict[str, Any]] = []
        iv_matrix: List[List[float]] = []

        for t in maturities:
            t_ivs: List[float] = []
            prices = self.price_options_fft(t, strikes, params)
            for k, pr in zip(strikes, prices):
                iv = _bs_implied_vol(pr, self.s0, k, t, self.r, self.q)
                t_ivs.append(round(iv, 4))
                surface_points.append(
                    {
                        "maturity_years": round(t, 2),
                        "strike": round(k, 2),
                        "moneyness": round(k / self.s0, 3),
                        "call_price": round(float(pr), 4),
                        "implied_vol": round(iv, 4),
                    }
                )
            iv_matrix.append(t_ivs)

        return {
            "maturities": maturities,
            "strikes": strikes,
            "iv_matrix": iv_matrix,
            "surface_points": surface_points,
            "parameters": params.to_dict(),
        }

    def calibrate(
        self,
        market_quotes: List[Dict[str, Any]],
        initial_guess: Optional[HestonParameters] = None,
    ) -> HestonCalibrationResult:
        """Calibrate Heston model parameters (v0, kappa, theta, sigma_v, rho) against market quotes.

        Args:
            market_quotes: List of dicts with {"strike": float, "maturity": float, "market_price": float (or "implied_vol": float)}.
            initial_guess: Initial parameter estimate (default standard equity parameters).

        Returns:
            HestonCalibrationResult with optimized parameters, fit error, and diagnostics.
        """
        start_time = time.perf_counter()

        if initial_guess is None:
            initial_guess = HestonParameters(
                v0=0.04, kappa=1.5, theta=0.04, sigma_v=0.3, rho=-0.6
            )

        # Prepare market quotes (convert IV to price if price missing)
        clean_quotes: List[Dict[str, float]] = []
        for q_item in market_quotes:
            k = float(q_item["strike"])
            t = float(q_item["maturity"])
            if "market_price" in q_item:
                p = float(q_item["market_price"])
            elif "implied_vol" in q_item:
                p = _bs_call_price(self.s0, k, t, self.r, self.q, float(q_item["implied_vol"]))
            else:
                continue
            clean_quotes.append({"strike": k, "maturity": t, "market_price": p})

        if not clean_quotes:
            # Fallback if no quotes provided
            clean_quotes = [
                {"strike": self.s0 * 0.9, "maturity": 1.0, "market_price": 16.5},
                {"strike": self.s0 * 1.0, "maturity": 1.0, "market_price": 9.2},
                {"strike": self.s0 * 1.1, "maturity": 1.0, "market_price": 4.1},
            ]

        # Optimization bounds: v0 > 0, kappa > 0, theta > 0, sigma_v > 0, -1 <= rho <= 1
        bounds = [
            (0.005, 0.50),  # v0
            (0.1, 8.0),  # kappa
            (0.005, 0.50),  # theta
            (0.05, 1.20),  # sigma_v
            (-0.95, 0.0),  # rho (negative for equities)
        ]

        x0 = [
            initial_guess.v0,
            initial_guess.kappa,
            initial_guess.theta,
            initial_guess.sigma_v,
            initial_guess.rho,
        ]

        # Group quotes by maturity to reuse FFT pricing across strikes
        mat_map: Dict[float, List[Tuple[int, float, float]]] = {}
        for idx, item in enumerate(clean_quotes):
            mat_map.setdefault(item["maturity"], []).append((idx, item["strike"], item["market_price"]))

        iterations_count = 0

        def loss_fn(x: np.ndarray) -> float:
            nonlocal iterations_count
            iterations_count += 1
            params = HestonParameters(
                v0=max(1e-4, x[0]),
                kappa=max(1e-4, x[1]),
                theta=max(1e-4, x[2]),
                sigma_v=max(1e-4, x[3]),
                rho=min(0.999, max(-0.999, x[4])),
            )

            sq_err = 0.0
            for t_mat, quote_list in mat_map.items():
                strikes_t = [k for _, k, _ in quote_list]
                model_prices = self.price_options_fft(t_mat, strikes_t, params, n=2048)
                for (_, _, mkt_p), mod_p in zip(quote_list, model_prices):
                    sq_err += (mod_p - mkt_p) ** 2

            # Feller condition penalty soft constraint
            if 2.0 * params.kappa * params.theta <= params.sigma_v**2:
                violation = params.sigma_v**2 - 2.0 * params.kappa * params.theta
                sq_err += 5.0 * violation

            return float(sq_err)

        res = optimize.minimize(
            loss_fn,
            x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 60, "ftol": 1e-5},
        )

        calibrated_params = HestonParameters(
            v0=float(res.x[0]),
            kappa=float(res.x[1]),
            theta=float(res.x[2]),
            sigma_v=float(res.x[3]),
            rho=float(res.x[4]),
        )

        # Generate comparison table
        pricing_comp: List[Dict[str, Any]] = []
        errors: List[float] = []

        for item in clean_quotes:
            t = item["maturity"]
            k = item["strike"]
            mkt_p = item["market_price"]
            mod_p = self.price_call(t, k, calibrated_params)
            err = mod_p - mkt_p
            errors.append(err)
            pricing_comp.append(
                {
                    "maturity": round(t, 2),
                    "strike": round(k, 2),
                    "market_price": round(mkt_p, 4),
                    "model_price": round(mod_p, 4),
                    "error": round(err, 4),
                    "abs_rel_error_pct": round(abs(err) / max(0.01, mkt_p) * 100.0, 2),
                }
            )

        rmse = float(np.sqrt(np.mean(np.square(errors)))) if errors else 0.0
        mae = float(np.mean(np.abs(errors))) if errors else 0.0
        duration = time.perf_counter() - start_time

        return HestonCalibrationResult(
            parameters=calibrated_params,
            rmse=rmse,
            mae=mae,
            pricing_comparison=pricing_comp,
            calibration_time_seconds=duration,
            iterations=iterations_count,
            success=bool(res.success),
        )


def compute_heston_surface_and_calibration(
    s0: float = 100.0,
    r: float = 0.03,
    q: float = 0.0,
    market_quotes: Optional[List[Dict[str, Any]]] = None,
    custom_params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Top-level calculation function for Heston FFT calibration and volatility surface.

    Args:
        s0: Spot asset price.
        r: Risk-free rate.
        q: Dividend yield.
        market_quotes: Optional list of market option quotes for calibration.
        custom_params: Optional dict with manual heston parameters (v0, kappa, theta, sigma_v, rho).

    Returns:
        Dictionary with calibration results, volatility surface, and parameter diagnostics.
    """
    engine = HestonFFTEngine(s0=s0, r=r, q=q)

    # Use custom or calibrated parameters
    if custom_params is not None:
        params = HestonParameters(
            v0=float(custom_params.get("v0", 0.04)),
            kappa=float(custom_params.get("kappa", 2.0)),
            theta=float(custom_params.get("theta", 0.04)),
            sigma_v=float(custom_params.get("sigma_v", 0.3)),
            rho=float(custom_params.get("rho", -0.7)),
        )
        calibration_data = {
            "parameters": params.to_dict(),
            "status": "manual_parameters_applied",
            "rmse": 0.0,
        }
    else:
        # Generate synthetic market quotes if none provided (e.g. S&P 500 smile)
        if not market_quotes:
            base_params = HestonParameters(v0=0.04, kappa=2.2, theta=0.04, sigma_v=0.35, rho=-0.65)
            market_quotes = []
            for t_mat in [0.5, 1.0]:
                for k_pct in [0.85, 0.95, 1.00, 1.05, 1.15]:
                    strike_val = s0 * k_pct
                    p = engine.price_call(t_mat, strike_val, base_params)
                    # Add subtle realistic market noise
                    p_noisy = max(0.05, p + np.random.normal(0.0, 0.03))
                    market_quotes.append({"strike": strike_val, "maturity": t_mat, "market_price": p_noisy})

        calib_res = engine.calibrate(market_quotes)
        params = calib_res.parameters
        calibration_data = calib_res.to_dict()

    surface = engine.compute_volatility_surface(params)

    return {
        "engine_version": "9.14.0",
        "spot_price": float(s0),
        "risk_free_rate": float(r),
        "dividend_yield": float(q),
        "heston_parameters": params.to_dict(),
        "feller_test": {
            "satisfied": params.feller_condition_met,
            "feller_ratio": params.feller_ratio,
            "2_kappa_theta": round(2.0 * params.kappa * params.theta, 6),
            "sigma_v_squared": round(params.sigma_v**2, 6),
        },
        "volatility_surface": surface,
        "calibration": calibration_data,
    }
