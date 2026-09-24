# ============================================================
# core/wealth/total_wealth_reverse_stress.py
# ARGUS — Total Wealth Reverse Stress Testing Engine
# Multi-Asset Solvency & Ruin Shock Optimization (EBA / Solvency II Framework)
# ============================================================

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

# Matrice di covarianza macroeconomica empirica per i 5 fattori di ricchezza:
# 1. Liquid Markets (Equities/Bonds/Funds)
# 2. Real Estate (Residenziale/Commerciale)
# 3. Corporate Equity (PMI / Private Equity)
# 4. Illiquid / Luxury / Collectibles
# 5. Debt Service / Liabilities Shock (Euribor / Spread)
WEALTH_FACTOR_NAMES = [
    "liquid_markets",
    "real_estate",
    "corporate_equity",
    "illiquid_luxury",
    "debt_liabilities",
]

# Volatilità annua tipica di ciascun fattore
WEALTH_FACTOR_VOLS = np.array([0.18, 0.08, 0.25, 0.12, 0.15])

# Matrice di correlazione plausibile durante stress sistemici
WEALTH_CORR_MATRIX = np.array([
    [ 1.00,  0.45,  0.70,  0.30,  0.35],  # Liquid Markets
    [ 0.45,  1.00,  0.50,  0.25,  0.40],  # Real Estate
    [ 0.70,  0.50,  1.00,  0.35,  0.45],  # Corporate Equity
    [ 0.30,  0.25,  0.35,  1.00,  0.15],  # Illiquid
    [ 0.35,  0.40,  0.45,  0.15,  1.00],  # Debt Liabilities
])

# Covarianza = Vol_i * Vol_j * Corr_ij
WEALTH_COV_MATRIX = np.outer(WEALTH_FACTOR_VOLS, WEALTH_FACTOR_VOLS) * WEALTH_CORR_MATRIX


def compute_total_wealth_reverse_stress(
    balance_sheet: Dict[str, float],
    target_type: str = "solvency",
    target_threshold: float = 0.60,
    custom_cov_matrix: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Risolve il problema di Reverse Stress Testing sul Patrimonio Globale:
    determina lo shock multi-fattoriale più verosimile (minima distanza di Mahalanobis)
    che porta il bilancio familiare/HNWI al superamento della soglia critica.

    Parametri:
    -----------
    balance_sheet : Dict[str, float]
        Dizionario con valori in EUR:
        - 'liquid_assets': patrimonio finanziario liquido
        - 'real_estate': immobili
        - 'corporate_equity': partecipazioni aziendali
        - 'illiquid_assets': arte, orologi, collezionismo
        - 'total_liabilities': mutui, debiti finanziari
    target_type : str
        'solvency' (Debt-to-Assets ratio >= target_threshold, es. 0.60)
        'ruin' (Perdita di Net Worth >= target_threshold, es. 0.50 = -50% Net Worth)
    target_threshold : float
        Soglia di fallimento/crisi.
    custom_cov_matrix : Optional[np.ndarray]
        Matrice di covarianza (5x5).

    Ritorna:
    --------
    Dict[str, Any] con dettagli dello shock ottimale, plausibilità statistica,
    perdite per comparto e raccomandazioni di salvaguardia patrimoniale.
    """
    # Estrazione e validazione voci di bilancio
    liquid = max(0.0, float(balance_sheet.get("liquid_assets", 0.0)))
    re = max(0.0, float(balance_sheet.get("real_estate", 0.0)))
    corp = max(0.0, float(balance_sheet.get("corporate_equity", 0.0)))
    illiq = max(0.0, float(balance_sheet.get("illiquid_assets", 0.0)))
    debt = max(0.0, float(balance_sheet.get("total_liabilities", 0.0)))

    initial_assets = liquid + re + corp + illiq
    if initial_assets <= 0.0:
        raise ValueError("Gli asset totali devono essere maggiori di zero.")

    initial_net_worth = initial_assets - debt
    initial_da_ratio = debt / initial_assets if initial_assets > 0 else 0.0

    # Covarianza e Inversa
    cov = custom_cov_matrix if custom_cov_matrix is not None else WEALTH_COV_MATRIX
    try:
        inv_cov = np.linalg.pinv(cov)
    except Exception:
        inv_cov = np.eye(5) / 0.04

    # Obiettivo: minimizzare Mahalanobis distance s^T * inv_cov * s
    def objective(s: np.ndarray) -> float:
        return float(s.T @ inv_cov @ s)

    # Gradient analitico
    def obj_grad(s: np.ndarray) -> np.ndarray:
        return 2.0 * (inv_cov @ s)

    # Vincoli di rottura
    # s = [s_liquid, s_re, s_corp, s_illiq, s_debt]
    if target_type == "solvency":
        # Target: Debt(s) / Assets(s) >= target_threshold
        # Equivalent: Debt(s) - target_threshold * Assets(s) >= 0
        def constraint_fun(s: np.ndarray) -> float:
            post_assets = (
                liquid * (1.0 + s[0])
                + re * (1.0 + s[1])
                + corp * (1.0 + s[2])
                + illiq * (1.0 + s[3])
            )
            post_debt = debt * (1.0 + s[4])
            return float(post_debt - target_threshold * max(100.0, post_assets))

    else:  # 'ruin' (Net Worth loss)
        # Target: initial_net_worth - post_net_worth >= target_threshold * initial_net_worth
        # Equivalent: post_net_worth <= initial_net_worth * (1.0 - target_threshold)
        def constraint_fun(s: np.ndarray) -> float:
            post_assets = (
                liquid * (1.0 + s[0])
                + re * (1.0 + s[1])
                + corp * (1.0 + s[2])
                + illiq * (1.0 + s[3])
            )
            post_debt = debt * (1.0 + s[4])
            post_nw = post_assets - post_debt
            nw_ruin_level = initial_net_worth * (1.0 - target_threshold)
            return float(nw_ruin_level - post_nw)

    # Bounds: contrazioni ragionevoli (-90% per asset, +100% per debito)
    bounds = [
        (-0.90, 0.20),   # liquid
        (-0.70, 0.20),   # real estate
        (-0.95, 0.20),   # corporate equity
        (-0.80, 0.20),   # illiquid
        (0.00, 1.00),    # debt cost hike
    ]

    # Tentativi di ottimizzazione con multi-start
    best_res = None
    best_dist = float("inf")

    x0_candidates = [
        np.array([-0.30, -0.15, -0.40, -0.10, 0.20]),
        np.array([-0.50, -0.30, -0.60, -0.25, 0.40]),
        np.array([-0.70, -0.45, -0.80, -0.40, 0.50]),
    ]

    for x0 in x0_candidates:
        res = minimize(
            objective,
            x0,
            jac=obj_grad,
            method="SLSQP",
            bounds=bounds,
            constraints={"type": "ineq", "fun": constraint_fun},
            options={"maxiter": 200, "ftol": 1e-6},
        )
        if res.success and constraint_fun(res.x) >= -1e-4:
            dist = np.sqrt(max(0.0, float(res.fun)))
            if dist < best_dist:
                best_dist = dist
                best_res = res

    # Se SLSQP non trova una soluzione fattibile esatta, fallback euristico sulla traiettoria di gradiente
    if best_res is None or not best_res.success:
        scale = 1.0
        # Calcolo shock proporzionale alla sensibilità
        sensitivities = np.array([liquid, re, corp, illiq, debt])
        if sensitivities.sum() > 0:
            sens_norm = sensitivities / sensitivities.sum()
        else:
            sens_norm = np.array([0.3, 0.2, 0.3, 0.1, 0.1])
        s_base = np.array([-0.5 * sens_norm[0], -0.3 * sens_norm[1], -0.6 * sens_norm[2], -0.2 * sens_norm[3], 0.3 * sens_norm[4]])
        for factor in np.linspace(0.5, 3.0, 50):
            s_cand = np.clip(s_base * factor, [-0.90, -0.70, -0.95, -0.80, 0.0], [0.20, 0.20, 0.20, 0.20, 1.0])
            if constraint_fun(s_cand) >= 0.0:
                opt_s = s_cand
                break
        else:
            opt_s = s_base * 2.0
        best_dist = float(np.sqrt(max(0.0, opt_s.T @ inv_cov @ opt_s)))
    else:
        opt_s = best_res.x

    # Risultati post-stress
    shock_dict = {
        "liquid_markets_pct": round(float(opt_s[0]) * 100.0, 2),
        "real_estate_pct": round(float(opt_s[1]) * 100.0, 2),
        "corporate_equity_pct": round(float(opt_s[2]) * 100.0, 2),
        "illiquid_luxury_pct": round(float(opt_s[3]) * 100.0, 2),
        "debt_liabilities_pct": round(float(opt_s[4]) * 100.0, 2),
    }

    post_liquid = liquid * (1.0 + opt_s[0])
    post_re = re * (1.0 + opt_s[1])
    post_corp = corp * (1.0 + opt_s[2])
    post_illiq = illiq * (1.0 + opt_s[3])
    post_debt = debt * (1.0 + opt_s[4])

    post_assets = post_liquid + post_re + post_corp + post_illiq
    post_nw = post_assets - post_debt
    post_da_ratio = post_debt / post_assets if post_assets > 0 else 1.0

    loss_liquid = liquid - post_liquid
    loss_re = re - post_re
    loss_corp = corp - post_corp
    loss_illiq = illiq - post_illiq
    debt_increase = post_debt - debt
    total_nw_loss = initial_net_worth - post_nw

    breakdown_loss = {
        "liquid_markets_loss_eur": round(loss_liquid, 2),
        "real_estate_loss_eur": round(loss_re, 2),
        "corporate_equity_loss_eur": round(loss_corp, 2),
        "illiquid_luxury_loss_eur": round(loss_illiq, 2),
        "debt_increase_eur": round(debt_increase, 2),
        "total_net_worth_loss_eur": round(total_nw_loss, 2),
    }

    # Identificazione fattore più vulnerabile (massima perdita EUR)
    losses_by_asset = {
        "Corporate Equity": loss_corp,
        "Liquid Markets": loss_liquid,
        "Real Estate": loss_re,
        "Debito & Mutui": debt_increase,
        "Illiquid / Luxury": loss_illiq,
    }
    most_vulnerable = max(losses_by_asset, key=losses_by_asset.get)

    # Probabilità empirica associata a Mahalanobis distance D_M (chi2 con 5 gradi di libertà)
    # oppure normale standard equivalente
    p_exceed = 1.0 - stats.chi2.cdf(best_dist ** 2, df=5)
    return_period_years = int(1.0 / max(1e-5, p_exceed))

    # Raccomandazioni istituzionali
    recommendations = []
    if debt > 0 and (debt_increase > total_nw_loss * 0.20 or post_da_ratio > 0.50):
        recommendations.append(
            f"Fissare cap o rifinanziare il debito (LTV attuale: {initial_da_ratio*100:.1f}% -> post-stress: {post_da_ratio*100:.1f}%)."
        )
    if loss_corp > total_nw_loss * 0.35:
        recommendations.append(
            "Elevata concentrazione in Corporate/Private Equity. Istituire hedging con opzioni o diversificazione in liquidità difensiva."
        )
    if loss_liquid > total_nw_loss * 0.30:
        recommendations.append(
            "Incrementare l'allocazione a decorrelatori istituzionali (Treasuries a breve, Gold, Managed Futures)."
        )
    if not recommendations:
        recommendations.append(
            "Struttura patrimoniale resiliente: mantenere un buffer di liquidità pari ad almeno 18 mesi di servizio del debito."
        )

    return {
        "target_type": target_type,
        "target_threshold": target_threshold,
        "mahalanobis_distance": round(best_dist, 3),
        "implied_probability_pct": round(float(p_exceed * 100.0), 4),
        "return_period_years": return_period_years,
        "factor_shocks": shock_dict,
        "pre_stress_balance_sheet": {
            "total_assets_eur": round(initial_assets, 2),
            "total_liabilities_eur": round(debt, 2),
            "net_worth_eur": round(initial_net_worth, 2),
            "debt_to_assets_pct": round(initial_da_ratio * 100.0, 2),
        },
        "post_stress_balance_sheet": {
            "total_assets_eur": round(post_assets, 2),
            "total_liabilities_eur": round(post_debt, 2),
            "net_worth_eur": round(post_nw, 2),
            "debt_to_assets_pct": round(post_da_ratio * 100.0, 2),
        },
        "breakdown_loss": breakdown_loss,
        "most_vulnerable_factor": most_vulnerable,
        "recommendations": recommendations,
    }
