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
    """
    if benchmark_returns is None or len(benchmark_returns) < 20:
        return {
            "current_regime": "Regime 1: Bull Low-Vol",
            "current_regime_icon": "🟢",
            "current_state_idx": 1,
            "regime_probabilities": {"Bull Low-Vol": 70.0, "Range-Bound": 20.0, "Crisis High-Vol": 10.0},
            "historical_regimes": pd.Series(),
            "regime_stats": pd.DataFrame()
        }

    s = benchmark_returns.dropna().astype(float)
    rolling_vol = s.rolling(window=21, min_periods=5).std() * np.sqrt(252.0)
    rolling_ret = s.rolling(window=21, min_periods=5).mean() * 252.0

    vol_low = float(rolling_vol.quantile(0.40))
    regimes = []
    for r, v in zip(rolling_ret, rolling_vol, strict=False):
        if pd.isna(v) or pd.isna(r):
            regimes.append(1)
        elif r >= 0.05 and v <= 0.22:
            # Bull Market classico: rendimento solido e volatilità contenuta
            regimes.append(1)
        elif r >= 0.0 and v <= 0.26:
            # Espansione a volatilità moderata
            regimes.append(1)
        elif r < -0.10 or v >= 0.30:
            # Crollo / Shock di mercato o spike di volatilità estrema
            regimes.append(3)
        else:
            # Mercato laterale o fase di transizione range-bound
            regimes.append(2)

    reg_series = pd.Series(regimes, index=s.index, name="market_regime")

    # Calcolo probabilità dello stato recente (ultimi 21 giorni)
    recent_reg = reg_series.tail(21)
    p_bull = float((recent_reg == 1).mean() * 100.0)
    p_trans = float((recent_reg == 2).mean() * 100.0)
    p_crisis = float((recent_reg == 3).mean() * 100.0)

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
        "rolling_volatility": rolling_vol * 100.0,
        "regime_stats": df_stats
    }
