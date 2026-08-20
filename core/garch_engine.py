"""
ARGUS — Risk Analytics Platform
Core Module: GARCH(1,1) Conditional Volatility & Filtered Historical Simulation (FHS)
Modellazione econometrica della volatilità dinamica e simulazione storica filtrata per VaR e CVaR a code spesse.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

TRADING_DAYS_YEAR = 252


def _garch11_log_likelihood(params: np.ndarray, eps: np.ndarray, initial_var: float) -> float:
    """
    Calcola la Negative Log-Likelihood gaussiana per il modello GARCH(1,1).
    params: [omega, alpha, beta]
    """
    omega, alpha, beta = params
    t_len = len(eps)
    sigma2 = np.empty(t_len)
    sigma2[0] = initial_var

    for t in range(1, t_len):
        sigma2[t] = omega + alpha * (eps[t - 1] ** 2) + beta * sigma2[t - 1]
        if sigma2[t] <= 1e-12:
            sigma2[t] = 1e-12

    ll = -0.5 * np.sum(np.log(2.0 * np.pi) + np.log(sigma2) + (eps ** 2) / sigma2)
    return -float(ll) if np.isfinite(ll) else 1e10


def fit_garch11(returns: pd.Series) -> Dict[str, Any]:
    """
    Calibra un modello GARCH(1,1) sui rendimenti giornalieri tramite Maximum Likelihood Estimation (MLE).

    sigma_t^2 = omega + alpha * eps_{t-1}^2 + beta * sigma_{t-1}^2

    Returns
    -------
    Dict[str, Any]
        Dizionario contenente i parametri calibrati (omega, alpha, beta, mu),
        persistenza, varianza di lungo termine, half-life, serie delle deviazioni standard
        condizionali sigma_t e serie dei residui standardizzati e_t.
    """
    s_ret = returns.dropna().astype(float)
    if len(s_ret) < 30:
        logger.warning("Serie storica troppo breve per GARCH(1,1) (<30 osservazioni). Utilizzo parametri di fallback.")
        mu_fallback = float(s_ret.mean()) if not s_ret.empty else 0.0
        var_fallback = float(s_ret.var()) if len(s_ret) > 1 else 0.0001
        if var_fallback <= 1e-12:
            var_fallback = 0.0001
        alpha_fb, beta_fb = 0.08, 0.88
        omega_fb = var_fallback * (1.0 - alpha_fb - beta_fb)
        sigmas = pd.Series(np.sqrt(var_fallback), index=s_ret.index)
        std_resids = (s_ret - mu_fallback) / sigmas
        return {
            "converged": False,
            "mu": mu_fallback,
            "omega": omega_fb,
            "alpha": alpha_fb,
            "beta": beta_fb,
            "persistence": alpha_fb + beta_fb,
            "unconditional_variance": var_fallback,
            "unconditional_annual_vol_pct": np.sqrt(var_fallback * TRADING_DAYS_YEAR) * 100.0,
            "current_daily_vol": np.sqrt(var_fallback),
            "current_annual_vol_pct": np.sqrt(var_fallback * TRADING_DAYS_YEAR) * 100.0,
            "next_day_variance": var_fallback,
            "next_day_vol": np.sqrt(var_fallback),
            "next_day_annual_vol_pct": np.sqrt(var_fallback * TRADING_DAYS_YEAR) * 100.0,
            "half_life_days": np.log(0.5) / np.log(alpha_fb + beta_fb),
            "sigma_series": sigmas,
            "standardized_residuals": std_resids,
            "log_likelihood": 0.0,
            "aic": 0.0,
            "bic": 0.0
        }

    r_vals = s_ret.values
    mu = float(np.mean(r_vals))
    eps = r_vals - mu
    sample_var = float(np.var(eps, ddof=1))
    if sample_var <= 1e-12:
        sample_var = 0.0001

    # Stima iniziale dei parametri
    alpha_0 = 0.08
    beta_0 = 0.88
    omega_0 = sample_var * (1.0 - alpha_0 - beta_0)
    init_params = np.array([omega_0, alpha_0, beta_0])

    bounds = [
        (1e-9, sample_var * 2.0),  # omega
        (1e-4, 0.40),              # alpha (shock ARCH)
        (0.40, 0.98)               # beta (persistenza GARCH)
    ]
    constraints = [
        {"type": "ineq", "fun": lambda p: 0.9999 - (p[1] + p[2])}  # alpha + beta < 1
    ]

    opt_res = minimize(
        _garch11_log_likelihood,
        init_params,
        args=(eps, sample_var),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 200, "ftol": 1e-7}
    )

    if opt_res.success and np.isfinite(opt_res.fun):
        omega, alpha, beta = opt_res.x
        converged = True
        nll = float(opt_res.fun)
    else:
        # Fallback a valori robusti di letteratura
        alpha, beta = 0.08, 0.88
        omega = sample_var * (1.0 - alpha - beta)
        converged = False
        nll = _garch11_log_likelihood(np.array([omega, alpha, beta]), eps, sample_var)

    persistence = float(alpha + beta)
    persistence = min(persistence, 0.9999)
    uncond_var = float(omega / max(1.0 - persistence, 1e-6))
    uncond_ann_vol = float(np.sqrt(uncond_var * TRADING_DAYS_YEAR) * 100.0)

    # Ricostruzione della serie storica di varianza condizionale sigma_t^2
    t_len = len(eps)
    sigma2 = np.empty(t_len)
    sigma2[0] = sample_var
    for t in range(1, t_len):
        sigma2[t] = omega + alpha * (eps[t - 1] ** 2) + beta * sigma2[t - 1]

    sigma_series = pd.Series(np.sqrt(sigma2), index=s_ret.index)
    std_residuals = pd.Series(eps / sigma_series.values, index=s_ret.index)

    # Previsione varianza a T+1
    next_day_var = float(omega + alpha * (eps[-1] ** 2) + beta * sigma2[-1])
    next_day_vol = float(np.sqrt(next_day_var))
    next_day_ann_vol = float(next_day_vol * np.sqrt(TRADING_DAYS_YEAR) * 100.0)

    # Half-life dello shock di volatilità in giorni: ln(0.5) / ln(alpha + beta)
    half_life = float(np.log(0.5) / np.log(persistence)) if persistence < 0.9999 else 999.0

    k_params = 3
    aic = 2.0 * k_params + 2.0 * nll
    bic = k_params * np.log(t_len) + 2.0 * nll

    return {
        "converged": converged,
        "mu": mu,
        "omega": float(omega),
        "alpha": float(alpha),
        "beta": float(beta),
        "persistence": persistence,
        "unconditional_variance": uncond_var,
        "unconditional_annual_vol_pct": uncond_ann_vol,
        "current_daily_vol": float(sigma_series.iloc[-1]),
        "current_annual_vol_pct": float(sigma_series.iloc[-1] * np.sqrt(TRADING_DAYS_YEAR) * 100.0),
        "next_day_variance": next_day_var,
        "next_day_vol": next_day_vol,
        "next_day_annual_vol_pct": next_day_ann_vol,
        "half_life_days": half_life,
        "sigma_series": sigma_series,
        "standardized_residuals": std_residuals,
        "log_likelihood": -nll,
        "aic": aic,
        "bic": bic
    }


def forecast_garch_volatility(fit_res: Dict[str, Any], horizon: int = 30) -> pd.DataFrame:
    """
    Calcola la struttura a termine (Term Structure) della volatilità attesa per k = 1..horizon giorni.

    sigma_{T+k}^2 = V_L + (alpha + beta)^k * (sigma_{T+1}^2 - V_L)
    """
    v_l = fit_res["unconditional_variance"]
    next_var = fit_res["next_day_variance"]
    p = fit_res["persistence"]

    days = list(range(1, horizon + 1))
    var_forecasts = []
    ann_vols = []

    for k in days:
        var_k = v_l + (p ** (k - 1)) * (next_var - v_l)
        vol_k_ann = np.sqrt(max(var_k, 1e-10) * TRADING_DAYS_YEAR) * 100.0
        var_forecasts.append(var_k)
        ann_vols.append(vol_k_ann)

    return pd.DataFrame({
        "horizon_days": days,
        "forecast_variance": var_forecasts,
        "forecast_annual_vol_pct": ann_vols
    })


def compute_filtered_historical_simulation(
    returns: pd.Series,
    fit_res: Optional[Dict[str, Any]] = None,
    alpha_levels: Optional[List[float]] = None,
    horizon: int = 1
) -> Dict[str, Any]:
    """
    Esegue la Filtered Historical Simulation (FHS) scalando i residui empirici standardizzati
    per la volatilità condizionale prevista al giorno T+1 (Hull & White 1998, Barone-Adesi 1999).

    r_{sim, i} = mu + e_i * sigma_{T+1} * sqrt(horizon)
    """
    if alpha_levels is None:
        alpha_levels = [0.05, 0.01]

    if fit_res is None:
        fit_res = fit_garch11(returns)

    std_resids = fit_res["standardized_residuals"].dropna().values
    if len(std_resids) == 0:
        std_resids = np.array([0.0])

    mu = fit_res["mu"]
    next_vol = fit_res["next_day_vol"]
    scale_factor = next_vol * np.sqrt(horizon)

    # Generazione distribuzione simulata FHS
    simulated_returns = mu * horizon + std_resids * scale_factor

    var_results: Dict[str, float] = {}
    cvar_results: Dict[str, float] = {}

    for a in alpha_levels:
        conf_pct = int((1.0 - a) * 100)
        q_val = float(np.percentile(simulated_returns, a * 100))
        var_val = abs(q_val)
        var_results[f"var_fhs_{conf_pct}"] = var_val

        tail = simulated_returns[simulated_returns <= q_val]
        cvar_val = abs(float(np.mean(tail))) if len(tail) > 0 else var_val
        cvar_results[f"cvar_fhs_{conf_pct}"] = cvar_val

    return {
        "simulated_returns": simulated_returns,
        "var_fhs": var_results,
        "cvar_fhs": cvar_results,
        "horizon": horizon,
        "sample_size": len(simulated_returns)
    }


def compute_garch_fhs_bundle(
    returns: pd.Series,
    total_value: float = 100000.0,
    horizon: int = 1
) -> Dict[str, Any]:
    """
    Costruisce il bundle diagnostico completo GARCH(1,1) e FHS integrato per la UI di ARGUS.
    """
    s_ret = returns.dropna().astype(float)
    fit_res = fit_garch11(s_ret)
    fhs_res = compute_filtered_historical_simulation(s_ret, fit_res=fit_res, horizon=horizon)
    term_structure = forecast_garch_volatility(fit_res, horizon=30)

    # Calcolo bande dinamiche di VaR GARCH(1,1) al 95% e 99% lungo la serie storica
    sigmas = fit_res["sigma_series"]
    mu = fit_res["mu"]
    var95_dynamic = -(mu - 1.644853 * sigmas)
    var99_dynamic = -(mu - 2.326348 * sigmas)

    df_dynamic_var = pd.DataFrame({
        "return": s_ret,
        "sigma_daily": sigmas,
        "sigma_annual_pct": sigmas * np.sqrt(TRADING_DAYS_YEAR) * 100.0,
        "var95_dynamic_pct": var95_dynamic * 100.0,
        "var99_dynamic_pct": var99_dynamic * 100.0
    }, index=s_ret.index)

    # Confronto monetario VaR FHS vs Storico Classico
    var95_pct = fhs_res["var_fhs"].get("var_fhs_95", 0.0)
    var99_pct = fhs_res["var_fhs"].get("var_fhs_99", 0.0)
    cvar95_pct = fhs_res["cvar_fhs"].get("cvar_fhs_95", 0.0)
    cvar99_pct = fhs_res["cvar_fhs"].get("cvar_fhs_99", 0.0)

    return {
        "fit": fit_res,
        "fhs": fhs_res,
        "term_structure": term_structure,
        "dynamic_bands": df_dynamic_var,
        "kpis": {
            "current_annual_vol_pct": fit_res["current_annual_vol_pct"],
            "unconditional_annual_vol_pct": fit_res["unconditional_annual_vol_pct"],
            "next_day_annual_vol_pct": fit_res["next_day_annual_vol_pct"],
            "persistence": fit_res["persistence"],
            "half_life_days": fit_res["half_life_days"],
            "alpha_arch": fit_res["alpha"],
            "beta_garch": fit_res["beta"],
            "omega": fit_res["omega"],
            "var_fhs_95_pct": var95_pct * 100.0,
            "var_fhs_95_eur": var95_pct * total_value,
            "var_fhs_99_pct": var99_pct * 100.0,
            "var_fhs_99_eur": var99_pct * total_value,
            "cvar_fhs_95_pct": cvar95_pct * 100.0,
            "cvar_fhs_95_eur": cvar95_pct * total_value,
            "cvar_fhs_99_pct": cvar99_pct * 100.0,
            "cvar_fhs_99_eur": cvar99_pct * total_value,
        }
    }
