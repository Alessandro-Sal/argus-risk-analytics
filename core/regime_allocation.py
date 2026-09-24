# ============================================================
# core/regime_allocation.py
# ARGUS — Quantitative Risk Analytics & Portfolio Engineering
# Regime-Conditional Adaptive Allocation (HMM Markov-Switching Overlay)
# ============================================================

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from core.advanced_quant import solve_spinu_risk_budgeting
from core.regime_switching import compute_market_regime_states


def detect_asset_characters(returns_df: pd.DataFrame) -> Dict[str, str]:
    """
    Classifica gli asset in 'risk_on' o 'defensive' basandosi su volatilità storica
    e correlazione con il mercato aggregato.
    """
    market_proxy = returns_df.mean(axis=1)
    characters = {}
    vols = returns_df.std() * np.sqrt(252.0)
    median_vol = float(vols.median())

    for col in returns_df.columns:
        col_lower = str(col).lower()
        if any(term in col_lower for term in ["bond", "gov", "bnd", "bil", "ief", "tlt", "cash", "gold", "gld", "shv"]):
            characters[col] = "defensive"
        elif any(term in col_lower for term in ["spy", "qqq", "equity", "stock", "vti", "msci"]):
            characters[col] = "risk_on"
        else:
            corr = float(returns_df[col].corr(market_proxy))
            vol = float(vols[col])
            # Se la volatilità è significativamente inferiore alla mediana o correlazione <= 0.2
            if vol < median_vol * 0.75 or corr < 0.20:
                characters[col] = "defensive"
            else:
                characters[col] = "risk_on"
    return characters


def compute_regime_conditional_allocation(
    returns_df: pd.DataFrame,
    base_weights: Optional[Dict[str, float]] = None,
    current_regime: Optional[str] = None,
    crisis_equity_haircut: float = 0.40,
    risk_free_rate: float = 0.02,
) -> Dict[str, Any]:
    """
    Calcola l'allocazione adattiva condizionata ai regimi macroeconomici latenti.

    Parametri:
    -----------
    returns_df : pd.DataFrame
        Matrice dei rendimenti storici con colonne = asset.
    base_weights : Optional[Dict[str, float]]
        Allocazione di partenza (se None, si assume pari peso 1/N).
    current_regime : Optional[str]
        Forzatura manuale del regime ('Bull', 'Neutral', 'Crisis') oppure rilevamento automatico HMM.
    crisis_equity_haircut : float
        Percentuale di riduzione del budget di rischio per asset rischiosi in caso di crisi (default 40%).
    risk_free_rate : float
        Tasso privo di rischio annuo.

    Ritorna:
    --------
    Dict[str, Any] contenente:
      - current_regime: str ('Bull', 'Neutral', 'Crisis')
      - regime_probabilities: Dict[str, float]
      - base_weights: Dict[str, float]
      - adaptive_weights: Dict[str, float]
      - weight_changes: Dict[str, float]
      - turnover: float
      - asset_characters: Dict[str, str]
      - regime_expected_metrics: Dict[str, float]
      - explanation: str
    """
    if returns_df is None or returns_df.empty:
        raise ValueError("returns_df non puo essere vuoto.")

    cols = list(returns_df.columns)
    n = len(cols)
    if n == 0:
        raise ValueError("returns_df deve contenere almeno 1 asset.")

    # Base weights
    if base_weights is None:
        bw = np.array([1.0 / n] * n)
    else:
        bw = np.array([base_weights.get(c, 1.0 / n) for c in cols], dtype=float)
        if bw.sum() > 0:
            bw = bw / bw.sum()
        else:
            bw = np.array([1.0 / n] * n)

    base_weights_dict = {col: float(bw[i]) for i, col in enumerate(cols)}

    # Rilevamento regime di mercato
    market_proxy = returns_df.mean(axis=1)
    regime_res = compute_market_regime_states(market_proxy)
    raw_probs = regime_res.get("regime_probabilities", {"Bull Low-Vol": 60.0, "Range-Bound": 30.0, "Crisis High-Vol": 10.0})

    # Normalizza probabilità
    p_bull = float(raw_probs.get("Bull Low-Vol", 50.0)) / 100.0
    p_neutral = float(raw_probs.get("Range-Bound", 30.0)) / 100.0
    p_crisis = float(raw_probs.get("Crisis High-Vol", 20.0)) / 100.0
    total_p = p_bull + p_neutral + p_crisis
    if total_p > 0:
        p_bull /= total_p
        p_neutral /= total_p
        p_crisis /= total_p
    else:
        p_bull, p_neutral, p_crisis = 0.5, 0.3, 0.2

    # Determinazione regime dominante se non forzato
    if current_regime is None:
        if p_crisis > 0.40:
            detected_regime = "Crisis"
        elif p_bull >= p_neutral:
            detected_regime = "Bull"
        else:
            detected_regime = "Neutral"
    else:
        detected_regime = str(current_regime).capitalize()
        if "Crisis" in detected_regime or "Shock" in detected_regime:
            detected_regime = "Crisis"
            p_crisis, p_bull, p_neutral = 0.80, 0.05, 0.15
        elif "Bull" in detected_regime:
            detected_regime = "Bull"
            p_bull, p_neutral, p_crisis = 0.80, 0.15, 0.05
        else:
            detected_regime = "Neutral"
            p_neutral, p_bull, p_crisis = 0.70, 0.20, 0.10

    # Classificazione asset
    characters = detect_asset_characters(returns_df)

    # Matrice di covarianza robusta Ledoit-Wolf
    clean_rets = returns_df.dropna().values
    if len(clean_rets) > n + 5:
        try:
            cov = LedoitWolf().fit(clean_rets).covariance_
        except Exception:
            cov = np.cov(clean_rets, rowvar=False)
    else:
        cov = np.cov(clean_rets, rowvar=False) if len(clean_rets) > 1 else np.eye(n) * 0.0004

    # Calcolo dei budget di rischio adattivi (Spinu Risk Budgeting)
    # Base risk budgets = base weights
    risk_budgets = bw.copy()

    # Modulazione dei budget in base al regime
    # Bull: sovrappesiamo risk_on (+20%), riduciamo defensive
    # Crisis: tagliamo risk_on con haircut = crisis_equity_haircut * p_crisis, sovrappesiamo defensive
    # Neutral: bilanciato
    for i, col in enumerate(cols):
        is_risk_on = (characters[col] == "risk_on")
        if detected_regime == "Bull":
            if is_risk_on:
                risk_budgets[i] *= (1.0 + 0.25 * p_bull)
            else:
                risk_budgets[i] *= max(0.2, (1.0 - 0.20 * p_bull))
        elif detected_regime == "Crisis":
            if is_risk_on:
                haircut = min(0.85, crisis_equity_haircut * (0.6 + p_crisis))
                risk_budgets[i] *= (1.0 - haircut)
            else:
                boost = 1.0 + (0.50 + p_crisis)
                risk_budgets[i] *= boost
        else:  # Neutral
            # Nessuna modifica estrema, piccolo tilt verso defensive se p_crisis è in aumento
            if is_risk_on:
                risk_budgets[i] *= (1.0 - 0.10 * p_crisis)
            else:
                risk_budgets[i] *= (1.0 + 0.10 * p_crisis)

    # Normalizzazione dei budget di rischio
    if risk_budgets.sum() > 0:
        risk_budgets = risk_budgets / risk_budgets.sum()
    else:
        risk_budgets = np.array([1.0 / n] * n)

    # Risoluzione Spinu ERC / Risk Budgeting
    try:
        w_res, success = solve_spinu_risk_budgeting(cov, risk_budgets)
        adaptive_w = w_res if success and w_res is not None else risk_budgets.copy()
    except Exception:
        # Fallback sicuro: linear weighting
        adaptive_w = risk_budgets.copy()

    adaptive_w = np.clip(adaptive_w, 0.0, 1.0)
    if adaptive_w.sum() > 0:
        adaptive_w = adaptive_w / adaptive_w.sum()

    adaptive_weights_dict = {col: round(float(adaptive_w[i]), 4) for i, col in enumerate(cols)}
    weight_changes_dict = {col: round(float(adaptive_w[i] - bw[i]), 4) for i, col in enumerate(cols)}
    turnover = float(np.sum(np.abs(adaptive_w - bw)) / 2.0)

    # Metriche attese sotto il regime
    # Annualized mean & vol
    mean_rets = returns_df.mean().values * 252.0
    if detected_regime == "Crisis":
        # Sotto crisi, rendimenti attesi compressi e vol aumentata
        mean_adj = mean_rets - 0.15
        vol_scale = 1.5
    elif detected_regime == "Bull":
        mean_adj = mean_rets + 0.05
        vol_scale = 0.85
    else:
        mean_adj = mean_rets
        vol_scale = 1.0

    port_ret_base = float(np.dot(bw, mean_adj))
    port_vol_base = float(np.sqrt(np.dot(bw, np.dot(cov * 252.0, bw))) * vol_scale)

    port_ret_adapt = float(np.dot(adaptive_w, mean_adj))
    port_vol_adapt = float(np.sqrt(np.dot(adaptive_w, np.dot(cov * 252.0, adaptive_w))) * vol_scale)

    sharpe_base = (port_ret_base - risk_free_rate) / max(0.01, port_vol_base)
    sharpe_adapt = (port_ret_adapt - risk_free_rate) / max(0.01, port_vol_adapt)

    # Drawdown stimato (Cornish-Fisher / parametric)
    cvar95_base = port_ret_base / 252.0 - 2.33 * (port_vol_base / np.sqrt(252.0))
    cvar95_adapt = port_ret_adapt / 252.0 - 2.33 * (port_vol_adapt / np.sqrt(252.0))

    explanation = (
        f"Regime rilevato: {detected_regime.upper()} (Probabilità: Bull {p_bull*100:.1f}%, "
        f"Neutral {p_neutral*100:.1f}%, Crisis {p_crisis*100:.1f}%). "
    )
    if detected_regime == "Crisis":
        explanation += (
            f"Applicato haircut prudenziale del {crisis_equity_haircut*100:.0f}% sugli asset Risk-On. "
            f"Il portafoglio adattivo riduce la volatilità attesa da {port_vol_base*100:.2f}% a {port_vol_adapt*100:.2f}% "
            f"con un turnover del {turnover*100:.1f}%."
        )
    elif detected_regime == "Bull":
        explanation += (
            f"Sovrappesati gli asset Risk-On per catturare il momentum positivo. "
            f"Sharpe ratio stimato: {sharpe_adapt:.2f} (vs {sharpe_base:.2f} base)."
        )
    else:
        explanation += (
            "Regime neutrale di consolidamento: allocazione ribilanciata per minimizzare la dispersione del rischio."
        )

    return {
        "current_regime": detected_regime,
        "regime_probabilities": {
            "Bull": round(p_bull * 100.0, 2),
            "Neutral": round(p_neutral * 100.0, 2),
            "Crisis": round(p_crisis * 100.0, 2),
        },
        "base_weights": base_weights_dict,
        "adaptive_weights": adaptive_weights_dict,
        "weight_changes": weight_changes_dict,
        "turnover": round(turnover, 4),
        "asset_characters": characters,
        "risk_budgets": {col: round(float(risk_budgets[i]), 4) for i, col in enumerate(cols)},
        "metrics_comparison": {
            "base_expected_return": round(port_ret_base * 100.0, 2),
            "base_expected_vol": round(port_vol_base * 100.0, 2),
            "base_sharpe": round(sharpe_base, 2),
            "adaptive_expected_return": round(port_ret_adapt * 100.0, 2),
            "adaptive_expected_vol": round(port_vol_adapt * 100.0, 2),
            "adaptive_sharpe": round(sharpe_adapt, 2),
            "turnover_pct": round(turnover * 100.0, 2),
        },
        "explanation": explanation,
    }
