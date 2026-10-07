# ============================================================
# core/michaud_resampling.py
# ARGUS — Risk Analytics & Wealth Intelligence Ecosystem
# Michaud Resampled Efficient Frontier Engine (Richard Michaud 1998)
# ============================================================

r"""
Michaud Resampled Efficient Frontier (REF) Portfolio Optimization Engine.

Implements Richard & Robert Michaud's (1998) resampling methodology.
Classical Markowitz mean-variance optimization is an "error maximizer"
because it treats empirical estimates of expected returns $\hat{\mu}$ and
covariances $\hat{\Sigma}$ as true parameters, leading to extreme, unstable,
and poorly diversified corner solutions.

The Michaud Resampling Algorithm:
1. Estimate empirical $\hat{\mu}$ and $\hat{\Sigma}$ from historical returns.
2. For $b = 1, \dots, B$ simulation trials:
   a. Resample $T$ returns from $\mathcal{N}(\hat{\mu}_{daily}, \hat{\Sigma}_{daily})$.
   b. Compute resampled mean $\mu^{(b)}$ and covariance $\Sigma^{(b)}$.
   c. Solve mean-variance optimization across $K$ target return/rank points.
   d. Record optimal weight vectors $w_k^{(b)}$ for $k = 1, \dots, K$.
3. Average weights across all resamples for each rank:
   $$\bar{w}_k = \frac{1}{B} \sum_{b=1}^B w_k^{(b)}$$
4. Evaluate $\bar{w}_k$ using the original parameters $\hat{\mu}, \hat{\Sigma}$.

Benefits:
- Eliminates non-intuitive knife-edge corner portfolios.
- Substantially higher out-of-sample Sharpe ratios and diversification.
- Robust against estimation error in small samples.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger("argus.michaud")


def _regularize_covariance(cov_matrix: np.ndarray, min_eigenval: float = 1e-7) -> np.ndarray:
    """Garantisce che la matrice di covarianza sia simmetrica e definita positiva (PSD)."""
    cov_sym = 0.5 * (cov_matrix + cov_matrix.T)
    vals, vecs = np.linalg.eigh(cov_sym)
    vals = np.maximum(vals, min_eigenval)
    return vecs @ np.diag(vals) @ vecs.T


def _solve_markowitz_point(
    mu: np.ndarray,
    cov: np.ndarray,
    target_return: float,
    n_assets: int,
    bounds: List[Tuple[float, float]],
) -> np.ndarray:
    """Risolve un singolo punto di portafoglio a minima varianza per un rendimento target."""
    w0 = np.ones(n_assets) / n_assets

    def obj(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    def grad(w: np.ndarray) -> np.ndarray:
        return 2.0 * (cov @ w)

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "eq", "fun": lambda w: np.dot(w, mu) - target_return},
    ]

    res = minimize(
        obj,
        w0,
        jac=grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 150, "ftol": 1e-6},
    )

    if res.success:
        w = np.maximum(res.x, 0.0)
        return w / np.sum(w)
    
    # Fallback su target inequality se equality fallisce
    constraints_ineq = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: np.dot(w, mu) - target_return},
    ]
    res2 = minimize(
        obj,
        w0,
        jac=grad,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints_ineq,
        options={"maxiter": 150, "ftol": 1e-6},
    )
    if res2.success:
        w = np.maximum(res2.x, 0.0)
        return w / np.sum(w)

    return w0


def _solve_min_var(cov: np.ndarray, n_assets: int, bounds: List[Tuple[float, float]]) -> np.ndarray:
    """Risolve il portafoglio a varianza minima globale (GMV)."""
    w0 = np.ones(n_assets) / n_assets
    res = minimize(
        lambda w: float(w @ cov @ w),
        w0,
        jac=lambda w: 2.0 * (cov @ w),
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}],
        options={"maxiter": 150, "ftol": 1e-7},
    )
    w = np.maximum(res.x, 0.0) if res.success else w0
    return w / np.sum(w)


def compute_michaud_resampled_frontier(
    df_returns: pd.DataFrame,
    n_samples: int = 100,
    n_frontier_points: int = 20,
    sample_size: Optional[int] = None,
    seed: Optional[int] = 42,
    risk_free_rate: float = 0.03,
) -> Dict[str, Any]:
    r"""
    Calcola la Frontiera Efficiente Ricampionata di Michaud (1998) con bootstrap Monte Carlo.

    Parametri:
        df_returns (pd.DataFrame): Serie storica dei rendimenti giornalieri degli asset.
        n_samples (int): Numero di simulazioni di ricampionamento (default: 100).
        n_frontier_points (int): Numero di punti/portafogli sulla frontiera (default: 20).
        sample_size (Optional[int]): Lunghezza campionaria simulata (default: len(df_returns)).
        seed (Optional[int]): Random seed per determinismo e riproducibilità.
        risk_free_rate (float): Tasso privo di rischio annuo per calcolo Sharpe (default: 0.03).

    Ritorna:
        Dict[str, Any]:
            Dizionario contenente la frontiera ricampionata, pesi aggregati, metriche
            di diversificazione HHI, e confronto con la frontiera classica di Markowitz.
    """
    if df_returns.empty or df_returns.shape[1] < 2:
        raise ValueError("df_returns deve contenere almeno 2 asset e una serie storica valida.")

    clean_returns = df_returns.dropna().copy()
    assets = list(clean_returns.columns)
    n_assets = len(assets)
    n_obs = len(clean_returns)
    sim_t = sample_size or max(n_obs, 252)

    if seed is not None:
        np.random.seed(seed)

    # 1. Parametri empirici originali annualizzati (252 giorni lavorativi)
    mu_daily = clean_returns.mean().values
    cov_daily = clean_returns.cov().values
    cov_daily_reg = _regularize_covariance(cov_daily)

    mu_annual = mu_daily * 252.0
    cov_annual = cov_daily_reg * 252.0

    bounds = [(0.0, 1.0) for _ in range(n_assets)]

    # 2. Frontiera Classica di Markowitz
    w_min_var_orig = _solve_min_var(cov_annual, n_assets, bounds)
    r_min_orig = float(np.dot(w_min_var_orig, mu_annual))
    r_max_orig = float(np.max(mu_annual))

    if r_max_orig <= r_min_orig:
        r_max_orig = r_min_orig + 0.05

    target_returns_orig = np.linspace(r_min_orig, r_max_orig, n_frontier_points)
    classic_weights_list = []
    classic_vols = []
    classic_returns = []

    for tr in target_returns_orig:
        w_p = _solve_markowitz_point(mu_annual, cov_annual, tr, n_assets, bounds)
        classic_weights_list.append(w_p)
        vol = float(np.sqrt(w_p @ cov_annual @ w_p))
        ret = float(np.dot(w_p, mu_annual))
        classic_vols.append(vol)
        classic_returns.append(ret)

    # 3. Michaud Resampling Simulation Loop
    # Matrice di accumulo pesi: [n_frontier_points, n_assets]
    resampled_weights_accum = np.zeros((n_frontier_points, n_assets))
    valid_samples = 0

    for _ in range(n_samples):
        # Campionamento multivariato da N(mu_daily, cov_daily)
        sim_returns = np.random.multivariate_normal(mu_daily, cov_daily_reg, size=sim_t)
        mu_b_daily = np.mean(sim_returns, axis=0)
        cov_b_daily = np.cov(sim_returns, rowvar=False)
        cov_b_daily_reg = _regularize_covariance(cov_b_daily)

        mu_b_ann = mu_b_daily * 252.0
        cov_b_ann = cov_b_daily_reg * 252.0

        w_min_b = _solve_min_var(cov_b_ann, n_assets, bounds)
        r_min_b = float(np.dot(w_min_b, mu_b_ann))
        r_max_b = float(np.max(mu_b_ann))

        if r_max_b <= r_min_b:
            r_max_b = r_min_b + 0.05

        targets_b = np.linspace(r_min_b, r_max_b, n_frontier_points)

        for k, tr_b in enumerate(targets_b):
            w_kb = _solve_markowitz_point(mu_b_ann, cov_b_ann, tr_b, n_assets, bounds)
            resampled_weights_accum[k] += w_kb

        valid_samples += 1

    # 4. Media dei pesi per ogni punto di rango k (Michaud Averaging)
    resampled_weights_avg = resampled_weights_accum / max(1, valid_samples)
    for k in range(n_frontier_points):
        tot_w = np.sum(resampled_weights_avg[k])
        if tot_w > 0:
            resampled_weights_avg[k] /= tot_w

    # 5. Valutazione della Frontiera Ricampionata sui parametri originali
    resampled_frontier_pts = []
    resampled_vols = []
    resampled_returns = []
    resampled_sharpes = []
    resampled_hhi_list = []

    for k in range(n_frontier_points):
        w_k = resampled_weights_avg[k]
        vol_k = float(np.sqrt(w_k @ cov_annual @ w_k))
        ret_k = float(np.dot(w_k, mu_annual))
        sharpe_k = float((ret_k - risk_free_rate) / max(1e-6, vol_k))
        hhi_k = float(np.sum(w_k ** 2))

        resampled_vols.append(vol_k)
        resampled_returns.append(ret_k)
        resampled_sharpes.append(sharpe_k)
        resampled_hhi_list.append(hhi_k)

        resampled_frontier_pts.append({
            "rank": k,
            "expected_return_pct": round(ret_k * 100.0, 3),
            "volatility_annual_pct": round(vol_k * 100.0, 3),
            "sharpe_ratio": round(sharpe_k, 3),
            "herfindahl_index": round(hhi_k, 4),
            "effective_constituents": round(1.0 / max(1e-4, hhi_k), 2),
            "weights": {assets[i]: round(float(w_k[i]), 5) for i in range(n_assets)},
        })

    # Portafogli chiave sulla Frontiera Ricampionata
    best_sharpe_idx = int(np.argmax(resampled_sharpes))
    min_vol_idx = int(np.argmin(resampled_vols))

    msr_weights = resampled_weights_avg[best_sharpe_idx]
    gmv_weights = resampled_weights_avg[min_vol_idx]

    # Portafogli chiave sulla Frontiera Classica
    classic_sharpes = [
        (classic_returns[i] - risk_free_rate) / max(1e-6, classic_vols[i])
        for i in range(n_frontier_points)
    ]
    classic_best_idx = int(np.argmax(classic_sharpes))
    classic_msr_weights = classic_weights_list[classic_best_idx]

    # Calcolo Diversification Index (HHI)
    classic_msr_hhi = float(np.sum(classic_msr_weights ** 2))
    resampled_msr_hhi = float(np.sum(msr_weights ** 2))

    df_msr_comparison = pd.DataFrame({
        "Asset": assets,
        "Michaud Resampled %": np.round(msr_weights * 100.0, 2),
        "Markowitz Classic %": np.round(classic_msr_weights * 100.0, 2),
    })

    return {
        "n_assets": n_assets,
        "assets": assets,
        "n_samples": valid_samples,
        "n_frontier_points": n_frontier_points,
        "risk_free_rate": risk_free_rate,
        # Frontiera Ricampionata
        "resampled_frontier": resampled_frontier_pts,
        "resampled_vols_pct": [round(v * 100.0, 3) for v in resampled_vols],
        "resampled_returns_pct": [round(r * 100.0, 3) for r in resampled_returns],
        "resampled_sharpes": [round(s, 3) for s in resampled_sharpes],
        # Frontiera Classica
        "classic_vols_pct": [round(v * 100.0, 3) for v in classic_vols],
        "classic_returns_pct": [round(r * 100.0, 3) for r in classic_returns],
        "classic_sharpes": [round(s, 3) for s in classic_sharpes],
        # Portafogli Ottimali MSR (Max Sharpe Ratio)
        "resampled_max_sharpe": {
            "expected_return_pct": round(resampled_returns[best_sharpe_idx] * 100.0, 2),
            "volatility_annual_pct": round(resampled_vols[best_sharpe_idx] * 100.0, 2),
            "sharpe_ratio": round(resampled_sharpes[best_sharpe_idx], 3),
            "herfindahl_index": round(resampled_msr_hhi, 4),
            "effective_constituents": round(1.0 / max(1e-4, resampled_msr_hhi), 2),
            "weights": {assets[i]: round(float(msr_weights[i]), 4) for i in range(n_assets)},
        },
        "classic_max_sharpe": {
            "expected_return_pct": round(classic_returns[classic_best_idx] * 100.0, 2),
            "volatility_annual_pct": round(classic_vols[classic_best_idx] * 100.0, 2),
            "sharpe_ratio": round(classic_sharpes[classic_best_idx], 3),
            "herfindahl_index": round(classic_msr_hhi, 4),
            "effective_constituents": round(1.0 / max(1e-4, classic_msr_hhi), 2),
            "weights": {assets[i]: round(float(classic_msr_weights[i]), 4) for i in range(n_assets)},
        },
        # Portafoglio GMV (Global Minimum Variance)
        "resampled_min_var": {
            "expected_return_pct": round(resampled_returns[min_vol_idx] * 100.0, 2),
            "volatility_annual_pct": round(resampled_vols[min_vol_idx] * 100.0, 2),
            "sharpe_ratio": round(resampled_sharpes[min_vol_idx], 3),
            "weights": {assets[i]: round(float(gmv_weights[i]), 4) for i in range(n_assets)},
        },
        "df_comparison": df_msr_comparison,
        "diversification_gain_pct": round((1.0 - (resampled_msr_hhi / max(1e-4, classic_msr_hhi))) * 100.0, 1),
    }
