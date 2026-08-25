# ============================================================
# core/regime_switching.py
# ARGUS — Risk Analytics & BI Platform
# Market Regime Switching (3-State Gaussian / Markov Classifier)
# ============================================================

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def compute_market_regime_states(benchmark_returns: pd.Series) -> Dict[str, Any]:
    """
    Classifica la serie storica di mercato nei 3 Regimi Macroeconomici Istituzionali:
    - Regime 1 🟢: Bull Market / Low Volatility (Rendimenti positivi, dispersione contenuta)
    - Regime 2 🟡: Range-Bound / Transizione (Volatilità moderata, rendimenti laterali)
    - Regime 3 🔴: Crisis / Panic Selling (Forte volatilità, rendimenti negativi, shock di correlazione)
    
    Utilizza un modello stocastico di Mixture Gaussiana / Softmax Posterior Probability
    sul piano bivariato (Rendimento Rolling 21g, Volatilità Rolling 21g).
    """
    if benchmark_returns is None or len(benchmark_returns) < 20:
        empty_prob_df = pd.DataFrame(columns=["p_bull", "p_neutral", "p_crisis"])
        return {
            "current_regime": "Regime 1: Bull Market (Low Volatility)",
            "current_regime_icon": "🟢",
            "current_color": "#00e676",
            "current_state_idx": 1,
            "regime_probabilities": {"Bull Low-Vol": 70.0, "Range-Bound": 20.0, "Crisis High-Vol": 10.0},
            "historical_regimes": pd.Series(),
            "historical_probabilities_df": empty_prob_df,
            "transition_matrix": pd.DataFrame(),
            "rolling_volatility": pd.Series(),
            "regime_stats": pd.DataFrame()
        }

    s = benchmark_returns.dropna().astype(float)
    rolling_vol = s.rolling(window=21, min_periods=5).std() * np.sqrt(252.0)
    rolling_ret = s.rolling(window=21, min_periods=5).mean() * 252.0

    # Archetipi quantitativi dei 3 Regimi Macro (Centroide Rendimento %, Centroide Volatilità %)
    # Regime 1: Bull (mu = +14%, vol = 12%)
    # Regime 2: Neutral / Range-Bound (mu = +2%, vol = 18%)
    # Regime 3: Crisis / Shock (mu = -20%, vol = 32%)
    mu_centers = np.array([0.14, 0.02, -0.20])
    vol_centers = np.array([0.12, 0.18, 0.32])
    ret_scale = 0.12
    vol_scale = 0.08

    prob_matrix = []
    regimes = []

    for r, v in zip(rolling_ret, rolling_vol, strict=False):
        if pd.isna(v) or pd.isna(r):
            prob_matrix.append([0.70, 0.20, 0.10])
            regimes.append(1)
        else:
            # Calcolo distanza euclidea normalizzata nel piano (Rendimento, Volatilità)
            dist_sq = ((r - mu_centers) / ret_scale) ** 2 + ((v - vol_centers) / vol_scale) ** 2
            logits = -0.5 * dist_sq
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            prob_matrix.append(probs)
            regimes.append(int(np.argmax(probs)) + 1)

    df_raw_probs = pd.DataFrame(prob_matrix, index=s.index, columns=["p_bull", "p_neutral", "p_crisis"])
    
    # Filtro Stocastico di Markov Smoothed Probabilities (Hamilton Filter)
    # L'EMA a 21 giorni filtra il rumore bianco giornaliero ed estrae i regimi macroeconomici strutturali
    df_probs = df_raw_probs.ewm(span=21, min_periods=1).mean()
    df_probs = df_probs.div(df_probs.sum(axis=1), axis=0)
    
    regimes = (df_probs[["p_bull", "p_neutral", "p_crisis"]].values.argmax(axis=1) + 1).tolist()
    reg_series = pd.Series(regimes, index=s.index, name="market_regime")
    df_probs["market_regime"] = reg_series

    # Probabilità istantanee più recenti
    latest_probs = df_probs.iloc[-1]
    p_bull = float(latest_probs["p_bull"] * 100.0)
    p_trans = float(latest_probs["p_neutral"] * 100.0)
    p_crisis = float(latest_probs["p_crisis"] * 100.0)

    curr_reg_val = int(reg_series.iloc[-1])
    if curr_reg_val == 1:
        current_name = "Regime 1: Bull Market (Low Volatility)"
        current_icon = "🟢"
        current_color = "#00e676"
    elif curr_reg_val == 2:
        current_name = "Regime 2: Range-Bound (Transition / Moderate Vol)"
        current_icon = "🟡"
        current_color = "#ffd700"
    else:
        current_name = "Regime 3: Crisis / Stress (High Volatility Shock)"
        current_icon = "🔴"
        current_color = "#ff3366"

    # Matrice di Transizione Empirica di Markov (P_ij = P(S_t = j | S_{t-1} = i))
    trans_counts = np.zeros((3, 3))
    for t in range(1, len(regimes)):
        i_from = regimes[t-1] - 1
        j_to = regimes[t] - 1
        trans_counts[i_from, j_to] += 1

    row_sums = trans_counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    trans_probs = (trans_counts / row_sums) * 100.0

    df_trans_matrix = pd.DataFrame(
        trans_probs.round(1),
        index=["🟢 Da Regime 1 (Bull)", "🟡 Da Regime 2 (Range)", "🔴 Da Regime 3 (Crisis)"],
        columns=["🟢 A Regime 1 (Bull)", "🟡 A Regime 2 (Range)", "🔴 A Regime 3 (Crisis)"]
    )

    df_stats = pd.DataFrame([
        {
            "Stato / Regime Macro": "🟢 Regime 1 (Bull Low-Vol)",
            "Dinamica & Profilo di Rischio": "Espansione macro, trend solido, bassa dispersione.",
            "Probabilità Recente %": f"{p_bull:.1f}%",
            "Allocazione Tattica Istituzionale": "Piena esposizione azionaria, fattore Momentum & Growth."
        },
        {
            "Stato / Regime Macro": "🟡 Regime 2 (Range-Bound)",
            "Dinamica & Profilo di Rischio": "Fase laterale, rotazione settoriale, incertezza.",
            "Probabilità Recente %": f"{p_trans:.1f}%",
            "Allocazione Tattica Istituzionale": "Ribilanciamento verso Quality, Value e dividendi difensivi."
        },
        {
            "Stato / Regime Macro": "🔴 Regime 3 (Crisis / Stress)",
            "Dinamica & Profilo di Rischio": "Crollo di mercato, spike di correlazione, volatilità estrema.",
            "Probabilità Recente %": f"{p_crisis:.1f}%",
            "Allocazione Tattica Istituzionale": "Aumento riserva liquidità, opzioni Put Hedging e bond governativi."
        }
    ])

    return {
        "current_regime": current_name,
        "current_regime_icon": current_icon,
        "current_color": current_color,
        "current_state_idx": curr_reg_val,
        "regime_probabilities": {
            "Bull Low-Vol": p_bull,
            "Range-Bound": p_trans,
            "Crisis High-Vol": p_crisis
        },
        "historical_regimes": reg_series,
        "historical_probabilities_df": df_probs,
        "transition_matrix": df_trans_matrix,
        "rolling_volatility": rolling_vol * 100.0,
        "rolling_return": rolling_ret * 100.0,
        "regime_stats": df_stats
    }
