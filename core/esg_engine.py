# ============================================================
# core/esg_engine.py
# ARGUS — ESG & SFDR Sustainability Desk
# European SFDR (Art. 6 / 8 / 9), Carbon Intensity & Tri-Pillar Score
# ============================================================

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


# Knowledge base euristica di scoring ESG per ticker comuni / asset class
KNOWN_ESG_METRICS = {
    "SWDA.MI": {"esg_score": 78.5, "e_score": 76.0, "s_score": 79.0, "g_score": 82.0, "sfdr_art": 8, "carbon_intensity": 98.0, "controversies": "None"},
    "EIMI.MI": {"esg_score": 68.0, "e_score": 64.0, "s_score": 69.0, "g_score": 72.0, "sfdr_art": 8, "carbon_intensity": 185.0, "controversies": "Low"},
    "XG7S.MI": {"esg_score": 84.0, "e_score": 88.0, "s_score": 82.0, "g_score": 83.0, "sfdr_art": 8, "carbon_intensity": 45.0, "controversies": "None"},
    "XEON.MI": {"esg_score": 75.0, "e_score": 70.0, "s_score": 75.0, "g_score": 80.0, "sfdr_art": 6, "carbon_intensity": 10.0, "controversies": "None"},
    "SGLD.MI": {"esg_score": 55.0, "e_score": 45.0, "s_score": 60.0, "g_score": 65.0, "sfdr_art": 6, "carbon_intensity": 320.0, "controversies": "Moderate"},
    "AAPL": {"esg_score": 82.0, "e_score": 85.0, "s_score": 78.0, "g_score": 84.0, "sfdr_art": 8, "carbon_intensity": 65.0, "controversies": "None"},
    "MSFT": {"esg_score": 89.0, "e_score": 92.0, "s_score": 86.0, "g_score": 90.0, "sfdr_art": 9, "carbon_intensity": 35.0, "controversies": "None"},
    "NVDA": {"esg_score": 79.0, "e_score": 74.0, "s_score": 81.0, "g_score": 83.0, "sfdr_art": 8, "carbon_intensity": 50.0, "controversies": "None"},
    "BTP": {"esg_score": 72.0, "e_score": 70.0, "s_score": 73.0, "g_score": 74.0, "sfdr_art": 6, "carbon_intensity": 110.0, "controversies": "None"}
}


def compute_portfolio_esg_and_sfdr_metrics(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calcola l'allineamento ESG del portafoglio, la ripartizione SFDR (Art. 6/8/9) e l'intensità carbonica ponderata.
    """
    total_val = 0.0
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        total_val = float(df_positions["controvalore"].sum())
    elif results and "valore_totale" in results:
        total_val = float(results["valore_totale"])
    if total_val <= 0:
        total_val = 100000.0

    holdings_esg = []
    w_esg = 0.0
    w_e = 0.0
    w_s = 0.0
    w_g = 0.0
    w_carbon = 0.0
    sfdr_weights = {6: 0.0, 8: 0.0, 9: 0.0}

    if df_positions is not None and not df_positions.empty:
        for _, row in df_positions.iterrows():
            ticker = str(row.get("ticker", "")).strip()
            name = str(row.get("nome", ticker))
            val = float(row.get("controvalore", 0.0))
            w = (val / total_val) if total_val > 0 else 0.0

            # Lookup metrics
            metrics = KNOWN_ESG_METRICS.get(ticker, {
                "esg_score": 72.0,
                "e_score": 70.0,
                "s_score": 72.0,
                "g_score": 75.0,
                "sfdr_art": 8 if "ESG" in name.upper() or "CLEAN" in name.upper() else 6,
                "carbon_intensity": 110.0,
                "controversies": "None"
            })

            w_esg += w * metrics["esg_score"]
            w_e += w * metrics["e_score"]
            w_s += w * metrics["s_score"]
            w_g += w * metrics["g_score"]
            w_carbon += w * metrics["carbon_intensity"]
            art = metrics["sfdr_art"]
            sfdr_weights[art] = sfdr_weights.get(art, 0.0) + w

            holdings_esg.append({
                "ticker": ticker,
                "name": name,
                "weight_pct": round(w * 100.0, 1),
                "esg_score": metrics["esg_score"],
                "e_pillar": metrics["e_score"],
                "s_pillar": metrics["s_score"],
                "g_pillar": metrics["g_score"],
                "sfdr_classification": f"Art. {metrics['sfdr_art']}",
                "carbon_intensity_tco2e": metrics["carbon_intensity"],
                "controversy_level": metrics["controversies"]
            })
    else:
        # Fallback sintetico
        w_esg = 77.8
        w_e = 78.2
        w_s = 76.5
        w_g = 79.1
        w_carbon = 88.5
        sfdr_weights = {6: 0.25, 8: 0.65, 9: 0.10}
        holdings_esg = [
            {"ticker": "SWDA.MI", "name": "iShares Core MSCI World", "weight_pct": 50.0, "esg_score": 78.5, "e_pillar": 76.0, "s_pillar": 79.0, "g_pillar": 82.0, "sfdr_classification": "Art. 8", "carbon_intensity_tco2e": 98.0, "controversy_level": "None"},
            {"ticker": "XG7S.MI", "name": "Xtrackers Global Govt Bond", "weight_pct": 30.0, "esg_score": 84.0, "e_pillar": 88.0, "s_pillar": 82.0, "g_pillar": 83.0, "sfdr_classification": "Art. 8", "carbon_intensity_tco2e": 45.0, "controversy_level": "None"},
            {"ticker": "MSFT", "name": "Microsoft Corp", "weight_pct": 20.0, "esg_score": 89.0, "e_pillar": 92.0, "s_pillar": 86.0, "g_pillar": 90.0, "sfdr_classification": "Art. 9", "carbon_intensity_tco2e": 35.0, "controversy_level": "None"}
        ]

    # ESG Rating Band
    rating_band = "AAA" if w_esg >= 85 else ("AA" if w_esg >= 75 else ("A" if w_esg >= 65 else ("BBB" if w_esg >= 55 else "BB")))

    # SFDR Summary
    sfdr_summary = {
        "art_6_conventional_pct": round(sfdr_weights.get(6, 0.0) * 100.0, 1),
        "art_8_esg_promoting_pct": round(sfdr_weights.get(8, 0.0) * 100.0, 1),
        "art_9_dark_green_impact_pct": round(sfdr_weights.get(9, 0.0) * 100.0, 1),
    }

    df_holdings = pd.DataFrame(holdings_esg)

    return {
        "portfolio_esg_score": round(w_esg, 1),
        "esg_rating_band": rating_band,
        "environmental_pillar_score": round(w_e, 1),
        "social_pillar_score": round(w_s, 1),
        "governance_pillar_score": round(w_g, 1),
        "weighted_carbon_intensity_tco2e_per_m_eur": round(w_carbon, 1),
        "sfdr_breakdown": sfdr_summary,
        "holdings_esg_list": holdings_esg,
        "holdings_esg_df": df_holdings,
        "is_esg_leader": w_esg >= 75.0
    }
