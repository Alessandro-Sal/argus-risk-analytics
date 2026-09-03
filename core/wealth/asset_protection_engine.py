# ==============================================================================
# core/wealth/asset_protection_engine.py
# ARGUS — Asset Protection, Trust & Holding (Società Semplice) Simulator
# ==============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class ProtectionVehicleAnalysis:
    vehicle_name: str
    legal_basis: str
    protection_score: float  # 0 to 100
    creditor_shield_level: str  # 'ELEVATO', 'MEDIO', 'TOTALE'
    tax_efficiency_rating: str
    setup_cost_range_eur: str
    annual_maintenance_eur: str
    key_advantages: List[str]
    critical_vulnerabilities: List[str]
    recommended_use_case: str


class AssetProtectionEngine:
    """
    Motore attuariale e giuridico per la protezione patrimoniale e la segregazione dei rischi.
    Analizza comparativamente:
    1. Persona Fisica (Nessuna protezione)
    2. Fondo Patrimoniale (Art. 167 c.c.)
    3. Trust Interno / Istituzionale (Convenzione dell'Aja 1985)
    4. Società Semplice (S.s.) / Holding Familiare con PEX
    """

    @staticmethod
    def evaluate_protection_matrix(summary_data: Dict[str, Any]) -> Dict[str, Any]:
        tot_nw = float(summary_data.get("total_net_worth", 0.0))
        re_val = float(summary_data.get("real_estate_total", 0.0))
        fin_inv = float(summary_data.get("financial_investments", 0.0))
        phys_val = float(summary_data.get("physical_assets", 0.0))

        # 1. Fondo Patrimoniale
        fp = ProtectionVehicleAnalysis(
            vehicle_name="🏛️ Fondo Patrimoniale (Art. 167 c.c.)",
            legal_basis="Codice Civile Italiano (Artt. 167-171 c.c.)",
            protection_score=65.0,
            creditor_shield_level="MEDIO",
            tax_efficiency_rating="NEUTRO (Tassazione IRPEF ordinaria)",
            setup_cost_range_eur="€ 1.500 - € 3.500 (Atto Notarile)",
            annual_maintenance_eur="€ 0 (Nessun obbligo di bilancio)",
            key_advantages=[
                "Impignorabilità dei beni per debiti estranei ai bisogni della famiglia (Art. 170 c.c.).",
                "Semplicità di costituzione con atto pubblico notarile.",
                "Nessun costo di gestione contabile annuale."
            ],
            critical_vulnerabilities=[
                "Revocatoria ordinaria esperibile dai creditori entro 5 anni (Art. 2901 c.c.).",
                "Inefficace per debiti tributari o professionali ritenuti strumentali al tenore di vita familiare.",
                "Applicabile unicamente a persone sposate / unite civilmente."
            ],
            recommended_use_case="Protezione della prima casa e di immobili di famiglia da rischi professionali ordinari."
        )

        # 2. Trust Istituzionale / Familiare
        trust = ProtectionVehicleAnalysis(
            vehicle_name="🛡️ Trust Familiare (Convenzione Aja 1985)",
            legal_basis="Legge 364/1989 & Convenzione dell'Aja 1° Luglio 1985",
            protection_score=92.0,
            creditor_shield_level="TOTALE (Segregazione Patrimoniale Piena)",
            tax_efficiency_rating="OTTIMA (Cass. SS.UU. n. 8053/2020: imposte fisse all'apporto)",
            setup_cost_range_eur="€ 5.000 - € 15.000 (Atto Istitutivo + Dotazione)",
            annual_maintenance_eur="€ 2.000 - € 5.000 (Compenso Trustee / Rendiconto)",
            key_advantages=[
                "Segregazione assoluta: i beni in trust non appartengono più al disponente né al trustee.",
                "Impenetrabilità dai creditori personali di disponente e beneficiari post-revocatoria.",
                "Flessibilità successoria totale senza blocchi ereditari in caso di premorienza.",
                "Fiscalità agevolata all'atto di apporto con imposte fisse di registro e ipocatastali."
            ],
            critical_vulnerabilities=[
                "Costi di gestione del trustee professionale e redazione del rendiconto annuale.",
                "Rischio di nullità (*Sham Trust*) se il disponente mantiene il controllo totale dei beni.",
                "Azione revocatoria nei primi 5 anni dalla costituzione."
            ],
            recommended_use_case="Tutela di patrimoni complessi (> € 1.000.000), protezione soggetti fragili e passaggio generazionale blindato."
        )

        # 3. Società Semplice (S.s.) / Holding di Famiglia
        ss = ProtectionVehicleAnalysis(
            vehicle_name="🏢 Società Semplice (S.s.) / Holding Familiare",
            legal_basis="Codice Civile (Artt. 2251-2290 c.c.) & Regime PEX Art. 87 TUIR",
            protection_score=85.0,
            creditor_shield_level="ELEVATO (Schermatura Quote & Intrasferibilità)",
            tax_efficiency_rating="ECCELLENTE (PEX 95% esenzione plusvalenze/dividendi)",
            setup_cost_range_eur="€ 2.500 - € 6.000 (Atto Costitutivo Notarile)",
            annual_maintenance_eur="€ 500 - € 1.500 (Gestione contabile minima)",
            key_advantages=[
                "Intrasferibilità delle quote ai creditori particolari del socio (non possono pignorare i beni sociali).",
                "Regime PEX (Partecipation Exemption): 95% esenzione sulle plusvalenze e dividendi societari.",
                "Donazione della nuda proprietà delle quote ai figli con riserva di usufrutto e controllo totale ai genitori.",
                "Esenzione da imposta di successione ex Art. 3 c. 4-ter D.Lgs. 346/1990 per controllo mantenuto a 5 anni."
            ],
            critical_vulnerabilities=[
                "Non può svolgere attività commerciale diretta (solo gestione statica di partecipazioni e immobili).",
                "Responsabilità illimitata dei soci amministratori verso i debiti contratti dalla società stessa."
            ],
            recommended_use_case="Holding patrimoniale per gestione di portafogli titoli consistenti, immobili a reddito e patti di famiglia."
        )

        comparison_df = pd.DataFrame([
            {
                "Veicolo": "Persona Fisica (Standard)",
                "Punteggio Tutela": "20 / 100",
                "Protezione Creditori": "Nessuna (Responsabilità illimitata ex Art. 2740 c.c.)",
                "Efficienza Fiscale": "Standard (26% Capital Gain / IRPEF fino a 43%)",
                "Costo Costituzione": "€ 0",
                "Costo Annuo": "€ 0",
                "Flessibilità Successoria": "Bassa (Apertura ordinaria successione e legittima)"
            },
            {
                "Veicolo": "Fondo Patrimoniale",
                "Punteggio Tutela": "65 / 100",
                "Protezione Creditori": "Media (Solo debiti estranei alla famiglia)",
                "Efficienza Fiscale": "Neutro (IRPEF ordinaria dei coniugi)",
                "Costo Costituzione": "€ 2.500",
                "Costo Annuo": "€ 0",
                "Flessibilità Successoria": "Media"
            },
            {
                "Veicolo": "Società Semplice (S.s.)",
                "Punteggio Tutela": "85 / 100",
                "Protezione Creditori": "Elevata (Beni sociali protetti dai creditori dei soci)",
                "Efficienza Fiscale": "Eccellente (PEX 95% e successione agevolata)",
                "Costo Costituzione": "€ 3.500",
                "Costo Annuo": "€ 800",
                "Flessibilità Successoria": "Massima (Usufrutto quote e governance blindata)"
            },
            {
                "Veicolo": "Trust Familiare",
                "Punteggio Tutela": "92 / 100",
                "Protezione Creditori": "Totale (Segregazione assoluta del fondo in trust)",
                "Efficienza Fiscale": "Ottima (Imposte fisse all'apporto)",
                "Costo Costituzione": "€ 8.000",
                "Costo Annuo": "€ 2.500",
                "Flessibilità Successoria": "Totale (Disposizioni fiduciarie personalizzate)"
            }
        ])

        # Calcolo risparmio fiscale potenziale tramite Holding S.s. (PEX)
        annual_divs = fin_inv * 0.03
        tax_pf = annual_divs * 0.26
        tax_pex = annual_divs * 0.05 * 0.24  # 5% imponibile a IRES 24% = 1.2% effettivo
        tax_savings_annual = max(0.0, tax_pf - tax_pex)

        return {
            "fondo_patrimoniale": fp,
            "trust": trust,
            "societa_semplice": ss,
            "comparison_df": comparison_df,
            "estimated_annual_pex_savings": round(tax_savings_annual, 2)
        }
