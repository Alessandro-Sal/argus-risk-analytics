"""Bayesian Black-Litterman Portfolio Optimization Engine (Idzorek 2005 & He-Litterman).

Combines reverse-optimized market equilibrium priors with subjective investor views
(both absolute and relative) using Bayesian updating, confidence-weighted uncertainty
covariance Omega, and quadratic portfolio weight optimization with realistic constraints.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import optimize


@dataclass
class BlackLittermanView:
    """Investor view specification (absolute or relative)."""

    view_type: str  # "absolute" or "relative"
    assets: List[str]  # Asset names involved
    weights: List[float]  # Pick weights in P matrix (e.g. [1.0] for absolute or [1.0, -1.0] for relative)
    expected_return: float  # Stated expected return or outperformance (q)
    confidence: float = 0.60  # Subjective confidence between 0.01 and 0.99 (Idzorek method)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize view to dict."""
        return {
            "view_type": self.view_type,
            "assets": self.assets,
            "weights": self.weights,
            "expected_return": round(float(self.expected_return), 4),
            "confidence": round(float(self.confidence), 4),
        }


@dataclass
class BlackLittermanReport:
    """Full optimization report containing equilibrium, views, posterior returns, and optimal allocations."""

    assets: List[str]
    market_weights: Dict[str, float]
    equilibrium_returns: Dict[str, float]
    posterior_returns: Dict[str, float]
    optimal_weights: Dict[str, float]
    active_weights: Dict[str, float]
    portfolio_metrics: Dict[str, float]
    views_applied: List[Dict[str, Any]]
    posterior_covariance: List[List[float]]
    summary_table: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "assets": self.assets,
            "market_weights": self.market_weights,
            "equilibrium_returns": self.equilibrium_returns,
            "posterior_returns": self.posterior_returns,
            "optimal_weights": self.optimal_weights,
            "active_weights": self.active_weights,
            "portfolio_metrics": self.portfolio_metrics,
            "views_applied": self.views_applied,
            "posterior_covariance": self.posterior_covariance,
            "summary_table": self.summary_table,
        }


class BlackLittermanEngine:
    """Black-Litterman model implementation with Idzorek confidence weighting."""

    def __init__(
        self,
        assets: List[str],
        cov_matrix: Union[np.ndarray, pd.DataFrame, List[List[float]]],
        market_weights: Optional[Union[np.ndarray, Dict[str, float], List[float]]] = None,
        risk_aversion: float = 3.0,
        tau: float = 0.05,
        risk_free_rate: float = 0.02,
    ) -> None:
        """Initialize Black-Litterman engine.

        Args:
            assets: List of asset symbols/names.
            cov_matrix: NxN historical covariance matrix of asset returns.
            market_weights: Market capitalization portfolio weights (summing to 1).
            risk_aversion: Market risk aversion parameter lambda = (E[Rm] - Rf) / sigma_m^2.
            tau: Scalar representing uncertainty in the prior equilibrium estimate (typically 0.025 - 0.05).
            risk_free_rate: Annual risk-free interest rate.
        """
        self.assets = list(assets)
        self.n = len(self.assets)
        self.risk_aversion = float(risk_aversion)
        self.tau = float(tau)
        self.risk_free_rate = float(risk_free_rate)

        # Parse covariance matrix
        if isinstance(cov_matrix, pd.DataFrame):
            self.sigma = cov_matrix.loc[self.assets, self.assets].values.astype(float)
        else:
            self.sigma = np.asarray(cov_matrix, dtype=float)

        if self.sigma.shape != (self.n, self.n):
            raise ValueError(f"Covariance matrix shape {self.sigma.shape} does not match {self.n} assets.")

        # Parse market equilibrium weights
        if market_weights is None:
            self.w_mkt = np.ones(self.n, dtype=float) / self.n
        elif isinstance(market_weights, dict):
            self.w_mkt = np.array([market_weights.get(a, 1.0 / self.n) for a in self.assets], dtype=float)
            self.w_mkt /= np.sum(self.w_mkt)
        else:
            self.w_mkt = np.asarray(market_weights, dtype=float)
            self.w_mkt /= np.sum(self.w_mkt)

    def implied_equilibrium_returns(self) -> np.ndarray:
        """Calculate market implied equilibrium returns: Pi = lambda * Sigma * w_mkt."""
        return self.risk_aversion * (self.sigma @ self.w_mkt)

    def build_views_matrices(
        self, views: List[BlackLittermanView]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Construct P (pick matrix), q (views return vector), and Omega (uncertainty covariance).

        Uses Idzorek (2005) mapping where view variance is scaled inversely by confidence:
        Omega_k = (P_k * (tau * Sigma) * P_k^T) * ((1 - conf_k) / conf_k).
        """
        k = len(views)
        if k == 0:
            return np.zeros((0, self.n)), np.zeros(0), np.zeros((0, 0))

        p_mat = np.zeros((k, self.n), dtype=float)
        q_vec = np.zeros(k, dtype=float)
        omega_diag = np.zeros(k, dtype=float)

        tau_sigma = self.tau * self.sigma

        for idx, view in enumerate(views):
            q_vec[idx] = view.expected_return
            # Map weights to asset columns
            for asset_sym, w in zip(view.assets, view.weights):
                if asset_sym in self.assets:
                    col_idx = self.assets.index(asset_sym)
                    p_mat[idx, col_idx] = float(w)

            # View variance using Idzorek confidence weighting
            p_k = p_mat[idx, :]
            var_view = float(p_k @ tau_sigma @ p_k.T)
            conf = min(0.999, max(0.001, view.confidence))
            # If conf = 0.50, scale factor is 1.0. If conf = 0.90, scale factor is 0.11 (high confidence).
            scale = (1.0 - conf) / conf
            omega_diag[idx] = max(1e-7, var_view * scale)

        omega_mat = np.diag(omega_diag)
        return p_mat, q_vec, omega_mat

    def calculate_posterior(
        self, views: Optional[List[BlackLittermanView]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute Bayesian posterior expected returns E[R] and posterior covariance M.

        E[R] = [(tau * Sigma)^-1 + P^T * Omega^-1 * P]^-1 * [(tau * Sigma)^-1 * Pi + P^T * Omega^-1 * q]
        M = Sigma + [(tau * Sigma)^-1 + P^T * Omega^-1 * P]^-1
        """
        pi = self.implied_equilibrium_returns()

        if not views:
            # Without views, posterior returns equal equilibrium returns
            return pi, self.sigma

        p_mat, q_vec, omega_mat = self.build_views_matrices(views)
        tau_sigma = self.tau * self.sigma

        inv_tau_sigma = np.linalg.pinv(tau_sigma)
        inv_omega = np.linalg.pinv(omega_mat)

        # Precision of posterior estimate
        post_precision = inv_tau_sigma + (p_mat.T @ inv_omega @ p_mat)
        post_cov_est = np.linalg.pinv(post_precision)

        # Posterior expected returns
        er = post_cov_est @ (inv_tau_sigma @ pi + p_mat.T @ inv_omega @ q_vec)

        # Total posterior covariance matrix: M = Sigma + post_cov_est
        m_cov = self.sigma + post_cov_est

        return er, m_cov

    def optimize_portfolio(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        long_only: bool = True,
        max_weight: float = 0.40,
    ) -> np.ndarray:
        """Find optimal portfolio weights maximizing mean-variance utility:

        max w^T E[R] - 0.5 * lambda * w^T Sigma w  s.t. sum(w) = 1, 0 <= w_i <= max_weight.
        """
        n = len(expected_returns)

        def objective(w: np.ndarray) -> float:
            port_ret = float(w @ expected_returns)
            port_var = float(w @ cov_matrix @ w)
            utility = port_ret - 0.5 * self.risk_aversion * port_var
            return -utility  # Minimize negative utility

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0 if long_only else -max_weight, max_weight) for _ in range(n)]

        w0 = np.ones(n) / n
        res = optimize.minimize(
            objective,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 100, "ftol": 1e-7},
        )

        if res.success:
            w_opt = res.x
            w_opt = np.maximum(0.0 if long_only else -max_weight, w_opt)
            return w_opt / np.sum(w_opt)
        return self.w_mkt.copy()

    def generate_report(
        self,
        views: Optional[List[BlackLittermanView]] = None,
        long_only: bool = True,
        max_weight: float = 0.40,
    ) -> BlackLittermanReport:
        """Generate comprehensive Black-Litterman optimization report."""
        if views is None:
            views = []

        pi = self.implied_equilibrium_returns()
        er, m_cov = self.calculate_posterior(views)
        w_opt = self.optimize_portfolio(er, m_cov, long_only=long_only, max_weight=max_weight)

        active_weights = w_opt - self.w_mkt

        # Portfolio metrics
        opt_exp_return = float(w_opt @ er)
        opt_volatility = float(np.sqrt(w_opt @ m_cov @ w_opt))
        opt_sharpe = (opt_exp_return - self.risk_free_rate) / max(1e-4, opt_volatility)

        mkt_exp_return = float(self.w_mkt @ pi)
        mkt_volatility = float(np.sqrt(self.w_mkt @ self.sigma @ self.w_mkt))
        mkt_sharpe = (mkt_exp_return - self.risk_free_rate) / max(1e-4, mkt_volatility)

        # Tracking error & Information Ratio
        te = float(np.sqrt(active_weights @ self.sigma @ active_weights))
        ir = (opt_exp_return - mkt_exp_return) / max(1e-4, te) if te > 1e-4 else 0.0

        summary_table: List[Dict[str, Any]] = []
        for i, a in enumerate(self.assets):
            summary_table.append(
                {
                    "asset": a,
                    "market_weight_pct": round(float(self.w_mkt[i]) * 100.0, 2),
                    "equilibrium_return_pct": round(float(pi[i]) * 100.0, 2),
                    "posterior_return_pct": round(float(er[i]) * 100.0, 2),
                    "optimal_weight_pct": round(float(w_opt[i]) * 100.0, 2),
                    "active_tilt_pct": round(float(active_weights[i]) * 100.0, 2),
                }
            )

        return BlackLittermanReport(
            assets=self.assets,
            market_weights={a: round(float(w), 4) for a, w in zip(self.assets, self.w_mkt)},
            equilibrium_returns={a: round(float(r), 4) for a, r in zip(self.assets, pi)},
            posterior_returns={a: round(float(r), 4) for a, r in zip(self.assets, er)},
            optimal_weights={a: round(float(w), 4) for a, w in zip(self.assets, w_opt)},
            active_weights={a: round(float(w), 4) for a, w in zip(self.assets, active_weights)},
            portfolio_metrics={
                "portfolio_expected_return": round(opt_exp_return, 4),
                "portfolio_volatility": round(opt_volatility, 4),
                "portfolio_sharpe": round(opt_sharpe, 4),
                "benchmark_expected_return": round(mkt_exp_return, 4),
                "benchmark_volatility": round(mkt_volatility, 4),
                "benchmark_sharpe": round(mkt_sharpe, 4),
                "tracking_error": round(te, 4),
                "information_ratio": round(ir, 4),
            },
            views_applied=[v.to_dict() for v in views],
            posterior_covariance=[
                [round(float(c), 6) for c in row] for row in m_cov
            ],
            summary_table=summary_table,
        )


def compute_black_litterman_allocation(
    assets: Optional[List[str]] = None,
    cov_matrix: Optional[List[List[float]]] = None,
    market_weights: Optional[Dict[str, float]] = None,
    views_data: Optional[List[Dict[str, Any]]] = None,
    risk_aversion: float = 3.0,
    tau: float = 0.05,
    risk_free_rate: float = 0.02,
    long_only: bool = True,
    max_weight: float = 0.40,
) -> Dict[str, Any]:
    """Top-level calculation function for Black-Litterman optimization.

    Args:
        assets: Asset names list (defaults to standard multi-asset universe).
        cov_matrix: NxN annual covariance matrix.
        market_weights: Market portfolio weights dictionary.
        views_data: List of investor views dicts.
        risk_aversion: Risk aversion parameter lambda.
        tau: Prior uncertainty scalar.
        risk_free_rate: Risk free rate.
        long_only: If True, enforce no short selling (w >= 0).
        max_weight: Maximum allowed weight per asset.

    Returns:
        Structured dictionary containing full Black-Litterman results.
    """
    if assets is None:
        assets = ["US_Equities", "EU_Equities", "EM_Equities", "Gov_Bonds", "Corp_Bonds", "Gold"]

    n = len(assets)

    if cov_matrix is None:
        # Default realistic covariance matrix
        volatilities = np.array([0.16, 0.18, 0.22, 0.05, 0.08, 0.15])
        corr = np.array(
            [
                [1.00, 0.78, 0.65, -0.20, 0.25, 0.05],
                [0.78, 1.00, 0.70, -0.15, 0.30, 0.10],
                [0.65, 0.70, 1.00, -0.10, 0.35, 0.15],
                [-0.20, -0.15, -0.10, 1.00, 0.45, 0.20],
                [0.25, 0.30, 0.35, 0.45, 1.00, 0.10],
                [0.05, 0.10, 0.15, 0.20, 0.10, 1.00],
            ]
        )
        cov = np.outer(volatilities, volatilities) * corr
    else:
        cov = np.asarray(cov_matrix, dtype=float)

    if market_weights is None:
        market_weights = {
            "US_Equities": 0.40,
            "EU_Equities": 0.20,
            "EM_Equities": 0.10,
            "Gov_Bonds": 0.15,
            "Corp_Bonds": 0.10,
            "Gold": 0.05,
        }

    # Parse views
    views_list: List[BlackLittermanView] = []
    if views_data:
        for v in views_data:
            views_list.append(
                BlackLittermanView(
                    view_type=v.get("view_type", "absolute"),
                    assets=v["assets"],
                    weights=v.get("weights", [1.0]),
                    expected_return=float(v["expected_return"]),
                    confidence=float(v.get("confidence", 0.60)),
                )
            )
    else:
        # Realistic default views:
        # 1. Absolute view: US Equities will return 9.5% with 70% confidence
        # 2. Relative view: EM Equities will outperform EU Equities by 3.0% with 65% confidence
        views_list = [
            BlackLittermanView(
                view_type="absolute",
                assets=["US_Equities"],
                weights=[1.0],
                expected_return=0.095,
                confidence=0.70,
            ),
            BlackLittermanView(
                view_type="relative",
                assets=["EM_Equities", "EU_Equities"],
                weights=[1.0, -1.0],
                expected_return=0.030,
                confidence=0.65,
            ),
        ]

    engine = BlackLittermanEngine(
        assets=assets,
        cov_matrix=cov,
        market_weights=market_weights,
        risk_aversion=risk_aversion,
        tau=tau,
        risk_free_rate=risk_free_rate,
    )

    report = engine.generate_report(views=views_list, long_only=long_only, max_weight=max_weight)
    res_dict = report.to_dict()
    res_dict["engine_version"] = "9.14.0"
    return res_dict
