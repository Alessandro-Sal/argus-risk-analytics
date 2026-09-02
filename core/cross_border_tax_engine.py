# ============================================================
# core/cross_border_tax_engine.py
# ARGUS — Cross-Border Tax & Global Wealth Structuring Engine
# Confronto regimi fiscali HNWI: Italia, Svizzera, Lussemburgo, UK, UAE
# ============================================================

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def get_international_tax_jurisdictions() -> Dict[str, Dict[str, Any]]:
    """Restituisce le specifiche fiscali e i regimi speciali per le giurisdizioni primarie."""
    return {
        "IT_ORDINARY": {
            "name": "Italia (Regime Ordinario TUIR)",
            "country": "Italia",
            "capital_gain_tax_pct": 26.0,
            "dividend_tax_pct": 26.0,
            "wealth_tax_ivafe_pct": 0.20,
            "inheritance_tax_direct_pct": 4.0,
            "inheritance_allowance_eur": 1000000.0,
            "flat_tax_annual_eur": 0.0,
            "foreign_income_exemption": False,
            "description": "Regime standard con imposta sostitutiva del 26% su capital gain e dividendi, IVAFE 0.20% su asset esteri e imposta successione 4% oltre 1M€."
        },
        "IT_NEO_RESIDENTI": {
            "name": "Italia (Art. 24-bis TUIR Neo-Residenti)",
            "country": "Italia",
            "capital_gain_tax_pct": 0.0,  # Esente su redditi di fonte estera
            "dividend_tax_pct": 0.0,      # Esente su dividendi esteri
            "wealth_tax_ivafe_pct": 0.0,  # Esenzione totale IVAFE / IVIE
            "inheritance_tax_direct_pct": 0.0, # Esente su patrimonio estero
            "inheritance_allowance_eur": 100000000.0,
            "flat_tax_annual_eur": 100000.0, # 100k€/anno (200k€ per nuove adesioni)
            "foreign_income_exemption": True,
            "description": "Imposta forfettaria annuale sostitutiva su tutti i redditi e capitali generati all'estero, esenzione totale da IVAFE, IVIE e successione estera (durata 15 anni)."
        },
        "CH_ZUG": {
            "name": "Svizzera (Cantone Zugo / Zurigo)",
            "country": "Svizzera",
            "capital_gain_tax_pct": 0.0,  # 0% su capital gain privato mobiliare
            "dividend_tax_pct": 22.0,     # Aliquota effettiva con computo federale/cantonale
            "wealth_tax_ivafe_pct": 0.25, # Imposta sulla sostanza cantonale (~0.25%)
            "inheritance_tax_direct_pct": 0.0, # 0% per discendenti diretti in maggioranza cantoni
            "inheritance_allowance_eur": 100000000.0,
            "flat_tax_annual_eur": 0.0,
            "foreign_income_exemption": False,
            "description": "0% capital gain su investimenti mobiliari privati, 0% successione linea retta a Zugo/Svitto/Zurigo, modesta imposta patrimoniale sulla sostanza."
        },
        "LUX_SOPARFI": {
            "name": "Lussemburgo (Holding SOPARFI)",
            "country": "Lussemburgo",
            "capital_gain_tax_pct": 0.0,  # Participation Exemption su partecipazioni qualificate
            "dividend_tax_pct": 0.0,      # Esenzione dividendi infragruppo UE/DTT
            "wealth_tax_ivafe_pct": 0.05, # NWT (Net Wealth Tax) minima
            "inheritance_tax_direct_pct": 0.0,
            "inheritance_allowance_eur": 100000000.0,
            "flat_tax_annual_eur": 4815.0, # Tassa patrimoniale minima holding
            "foreign_income_exemption": True,
            "description": "Veicolo societario holding istituzionale con regime Participation Exemption (Direttiva Madre-Figlia UE), azzeramento ritenute su dividendi in uscita verso paesi DTT."
        },
        "UAE_DUBAI": {
            "name": "Emirati Arabi Uniti (Dubai / ADGM Zero-Tax)",
            "country": "UAE",
            "capital_gain_tax_pct": 0.0,
            "dividend_tax_pct": 0.0,
            "wealth_tax_ivafe_pct": 0.0,
            "inheritance_tax_direct_pct": 0.0,
            "inheritance_allowance_eur": 100000000.0,
            "flat_tax_annual_eur": 0.0,
            "foreign_income_exemption": True,
            "description": "0% imposta personale sui redditi, 0% capital gain, 0% imposta patrimoniale e successoria con protezione fiduciaria DIFC/ADGM Foundation."
        }
    }


def compute_cross_border_wealth_tax_comparison(
    total_wealth_eur: float = 10000000.0,
    annual_capital_gain_eur: float = 400000.0,
    annual_foreign_income_eur: float = 250000.0,
    estate_succession_eur: float = 10000000.0
) -> Dict[str, Any]:
    """
    Simula e confronta il carico fiscale totale annuo e successorio tra le diverse giurisdizioni patrimoniali.
    """
    jur_data = get_international_tax_jurisdictions()
    comparison_rows = []

    for j_key, j in jur_data.items():
        # Imposta su Capital Gain
        cgt = annual_capital_gain_eur * (j["capital_gain_tax_pct"] / 100.0)
        # Imposta su Dividendi / Rendite
        div_tax = annual_foreign_income_eur * (j["dividend_tax_pct"] / 100.0)
        # Imposta Patrimoniale (IVAFE / Sostanza / NWT)
        wealth_tax = total_wealth_eur * (j["wealth_tax_ivafe_pct"] / 100.0)
        # Forfait
        flat_tax = j["flat_tax_annual_eur"]

        # Totale Imposte Correnti Annue
        total_annual_tax = cgt + div_tax + wealth_tax + flat_tax
        effective_annual_rate_pct = (total_annual_tax / max(1.0, annual_capital_gain_eur + annual_foreign_income_eur)) * 100.0

        # Imposta di Successione Stimata
        taxable_estate = max(0.0, estate_succession_eur - j["inheritance_allowance_eur"])
        estate_tax = taxable_estate * (j["inheritance_tax_direct_pct"] / 100.0)

        comparison_rows.append({
            "jurisdiction_key": j_key,
            "name": j["name"],
            "country": j["country"],
            "annual_cgt_eur": round(cgt, 2),
            "annual_income_tax_eur": round(div_tax, 2),
            "annual_wealth_tax_eur": round(wealth_tax, 2),
            "annual_flat_tax_eur": round(flat_tax, 2),
            "total_annual_tax_eur": round(total_annual_tax, 2),
            "effective_annual_tax_rate_pct": round(effective_annual_rate_pct, 2),
            "estimated_estate_succession_tax_eur": round(estate_tax, 2),
            "description": j["description"]
        })

    df_comp = pd.DataFrame(comparison_rows)

    # Identificazione soluzione con massimo risparmio rispetto a IT Ordinario
    it_ord_tax = next((r["total_annual_tax_eur"] for r in comparison_rows if r["jurisdiction_key"] == "IT_ORDINARY"), 0.0)
    for r in comparison_rows:
        r["annual_savings_vs_it_ordinary_eur"] = round(it_ord_tax - r["total_annual_tax_eur"], 2)

    best = min(comparison_rows, key=lambda x: x["total_annual_tax_eur"])

    return {
        "simulated_wealth_eur": round(total_wealth_eur, 2),
        "annual_capital_gain_eur": round(annual_capital_gain_eur, 2),
        "annual_income_eur": round(annual_foreign_income_eur, 2),
        "simulated_estate_eur": round(estate_succession_eur, 2),
        "lowest_tax_jurisdiction": best["name"],
        "max_annual_tax_savings_eur": round(it_ord_tax - best["total_annual_tax_eur"], 2),
        "comparison_list": comparison_rows,
        "comparison_df": df_comp
    }
