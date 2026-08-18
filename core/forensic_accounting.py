# ============================================================
# core/forensic_accounting.py
# ARGUS — Risk Analytics & BI Platform
# Forensic Accounting: Beneish M-Score (1999) & Sloan Accruals (1996)
# ============================================================

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


def compute_beneish_m_score(
    dsri: float = 1.0,
    gmi: float = 1.0,
    aqi: float = 1.0,
    sgi: float = 1.0,
    depi: float = 1.0,
    sgai: float = 1.0,
    lvgi: float = 1.0,
    tata: float = 0.0
) -> Dict[str, Any]:
    """
    Calcola il Beneish M-Score (1999) per valutare la probabilità di manipolazione contabile/frode di bilancio.

    Formula dell'M-Score a 8 Variabili:
    M-Score = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI +
              0.115*DEPI - 0.172*SGAI + 4.037*TATA + 0.0327*LVGI

    Interpretazione:
    - M-Score > -1.78 : 🔴 Rischio Manipolazione (Probable Manipulator)
    - M-Score <= -1.78: 🟢 Bilancio Conforme e Naturale (Non-Manipulator)
    """
    m_score = (
        -4.84
        + (0.920 * dsri)
        + (0.528 * gmi)
        + (0.404 * aqi)
        + (0.892 * sgi)
        + (0.115 * depi)
        - (0.172 * sgai)
        + (4.037 * tata)
        + (0.0327 * lvgi)
    )

    # Calibrazione econometrica della probabilità di manipolazione ancorata alla soglia critica M = -1.78
    # Per M <= -1.78 (es. -2.12), la probabilità di frode è bassa (< 25%); per M > -1.78 sale verso 50%-99%
    import scipy.stats as stats
    z_score = (m_score - (-1.78)) / 0.50
    manipulation_prob = float(stats.norm.cdf(z_score) * 100.0)
    manipulation_prob = min(99.9, max(0.1, manipulation_prob))

    if m_score > -1.78:
        verdict = "Rischio Manipolazione Contabile (M > -1.78)"
        status = "🔴 Elevato Rischio"
        icon = "🔴"
    else:
        verdict = "Bilancio Genuino e Conforme (M <= -1.78)"
        status = "🟢 Sicuro"
        icon = "🟢"

    indices_df = pd.DataFrame([
        {"Indice": "DSRI (Days Sales in Receivables)", "Valore": f"{dsri:.2f}", "Benchmark Normale": "<= 1.05", "Descrizione": "Crescita anomala dei crediti commerciali vs ricavi."},
        {"Indice": "GMI (Gross Margin Index)", "Valore": f"{gmi:.2f}", "Benchmark Normale": "<= 1.00", "Descrizione": "Deterioramento della marginalità lorda."},
        {"Indice": "AQI (Asset Quality Index)", "Valore": f"{aqi:.2f}", "Benchmark Normale": "<= 1.00", "Descrizione": "Capitalizzazione anomala di costi intangibili non operativi."},
        {"Indice": "SGI (Sales Growth Index)", "Valore": f"{sgi:.2f}", "Benchmark Normale": "<= 1.15", "Descrizione": "Tasso di espansione accelerato del fatturato."},
        {"Indice": "DEPI (Depreciation Index)", "Valore": f"{depi:.2f}", "Benchmark Normale": "<= 1.00", "Descrizione": "Rallentamento artificioso dei piani di ammortamento."},
        {"Indice": "SGAI (Sales General & Admin Index)", "Valore": f"{sgai:.2f}", "Benchmark Normale": "<= 1.00", "Descrizione": "Crescita dei costi commerciali e amministrativi."},
        {"Indice": "LVGI (Leverage Index)", "Valore": f"{lvgi:.2f}", "Benchmark Normale": "<= 1.05", "Descrizione": "Incremento dell'indebitamento strutturale totale."},
        {"Indice": "TATA (Total Accruals to Total Assets)", "Valore": f"{tata:.3f}", "Benchmark Normale": "<= 0.05", "Descrizione": "Differenza tra utile contabile e flusso di cassa reale."}
    ])

    return {
        "m_score": float(m_score),
        "verdict": verdict,
        "status": status,
        "icon": icon,
        "manipulation_probability_pct": manipulation_prob,
        "indices_df": indices_df,
        "is_manipulator": m_score > -1.78
    }


def compute_sloan_accrual_ratio(
    net_income: float,
    operating_cash_flow: float,
    total_assets: float
) -> Dict[str, Any]:
    """
    Calcola l'Accrual Ratio di Richard Sloan (1996) per quantificare la qualità degli utili.

    Formula:
    Accrual Ratio = (Net Income - Operating Cash Flow) / Total Assets

    Interpretazione:
    - Ratio <= -0.05: 🟢🟢 Utili di altissima qualità (Cash Flow > Net Income)
    - Ratio tra -0.05 e +0.10: 🟢 Utili sani e stabili
    - Ratio > +0.10: 🔴 Utili di bassa qualità (basati su scritture contabili e crediti)
    """
    if total_assets <= 0:
        total_assets = 1.0

    accruals = net_income - operating_cash_flow
    accrual_ratio = accruals / total_assets

    if accrual_ratio > 0.10:
        quality = "Bassa Qualità (Utili da Crediti / Accruals Eccessivi)"
        badge = "🔴 Bassa Qualità"
    elif accrual_ratio <= -0.05:
        quality = "Eccellente Qualità (Cash Flow Reale Superiore all'Utile Netto)"
        badge = "🟢🟢 Eccellente"
    else:
        quality = "Buona Qualità (Cash Flow e Utili Allineati)"
        badge = "🟢 Stabile"

    return {
        "accrual_ratio": float(accrual_ratio),
        "accrual_ratio_pct": float(accrual_ratio * 100.0),
        "quality": quality,
        "badge": badge,
        "total_accruals": float(accruals)
    }
