# ==============================================================================
# core/wealth/asset_protection_engine.py
# ARGUS — Asset Protection, Trust, Holding (S.s.) & Generational Transfer Optimizer
# Normative: Codice Civile (Artt. 536-564, 768-bis, 1923, 2251 c.c.)
# Fiscalita: D.Lgs. 346/1990 (TUS), D.Lgs. 347/1990 (Ipo-Catastale), D.P.R. 131/1986 (TUR)
# ==============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# ── STRUTTURE DATI VEICOLI DI PROTEZIONE ─────────────────────

@dataclass
class ProtectionVehicleAnalysis:
    vehicle_name: str
    legal_basis: str
    protection_score: float  # 0 to 100
    creditor_shield_level: str  # 'MEDIO', 'ELEVATO', 'TOTALE'
    tax_efficiency_rating: str
    setup_cost_range_eur: str
    annual_maintenance_eur: str
    key_advantages: List[str]
    critical_vulnerabilities: List[str]
    recommended_use_case: str


# ── STRUTTURE DATI PIANIFICAZIONE SUCCESSORIA HNWI ───────────

@dataclass
class FamilyHeir:
    name: str
    relationship: str  # 'coniuge', 'figlio', 'ascendente', 'fratello_sorella', 'altro'
    is_disabled_l104: bool = False  # Portatore di handicap grave ex L. 104/1992 (franchigia € 1.5M)
    donations_received_in_life: float = 0.0  # Donazioni dirette o indirette già ricevute
    testamentary_bequest_eur: float = 0.0   # Valore attribuito nel testamento simulato
    is_business_successor: bool = False     # Assegnatario designato dell'azienda/holding di famiglia


@dataclass
class FamilyProfile:
    has_spouse: bool = True
    children_count: int = 2
    has_ascendants: bool = False
    has_siblings: bool = False
    disabled_children_count: int = 0
    disabled_other_heirs_count: int = 0
    custom_heirs: List[FamilyHeir] = field(default_factory=list)


@dataclass
class StatutoryShareItem:
    heir_name: str
    relationship: str
    statutory_pct: float
    statutory_value_eur: float
    tax_allowance_eur: float
    tax_rate_pct: float
    imposta_successione_eur: float
    is_legitimate_heir: bool  # True se legittimario con quota di riserva ex lege


@dataclass
class SuccessionSharesResult:
    relictum_gross_eur: float
    liabilities_deductible_eur: float
    relictum_net_eur: float
    donatum_total_eur: float
    fictitious_reunion_estate_eur: float  # Asse ereditario ex art. 556 c.c.
    quota_desc: str
    disponibile_pct: float
    disponibile_eur: float
    legitimate_shares: List[StatutoryShareItem]
    total_legitimate_eur: float
    is_legitimate_injured: bool = False
    total_reduction_due_eur: float = 0.0
    reduction_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PlanningLevers:
    life_insurance_allocation_eur: float = 0.0       # Polizze Vita Ramo I / III (esenti art. 12 TUS)
    holding_family_ss_equity_eur: float = 0.0        # Quota trasferita in Holding Familiare / S.s.
    patto_di_famiglia_eligible: bool = False         # Trasferimento controllo art. 768-bis & 3 c. 4-ter TUS (0% imposta)
    bare_ownership_donation_re_eur: float = 0.0      # Valore immobili donati in nuda proprietà con riserva di usufrutto
    donor_age: int = 70                              # Età del disponente/donante (per tabella usufrutto D.P.R. 131/1986)
    joint_account_cash_eur: float = 0.0              # Liquidità in conto corrente cointestato a firma disgiunta
    joint_account_presumption_pct: float = 50.0      # Quota presunta caduta in successione (50% ex art. 1298 c.c.)
    is_first_home_applicable: bool = True            # Almeno un erede ha requisiti prima casa (€ 200 fisse ipo+cat)


@dataclass
class OptimizationComparisonResult:
    # Scenario Ante-Pianificazione (Status Quo)
    ante_relictum_taxable_eur: float
    ante_estate_tax_eur: float
    ante_mortgage_cadastral_tax_eur: float
    ante_total_taxes_eur: float
    ante_liquidity_required_eur: float
    ante_protection_score: float

    # Scenario Post-Ottimizzazione (Pianificazione Attiva)
    post_relictum_taxable_eur: float
    post_estate_tax_eur: float
    post_mortgage_cadastral_tax_eur: float
    post_total_taxes_eur: float
    post_liquidity_required_eur: float
    post_protection_score: float

    # Delta & Metriche di Efficienza
    tax_savings_eur: float
    tax_savings_pct: float
    immediate_liquidity_generated_eur: float
    reduction_risk_mitigated: bool
    liquidity_coverage_ratio: float  # Liquidità disponibile immediata / imposte totali post

    # Dettagli comparativi
    breakdown_ante: Dict[str, Any]
    breakdown_post: Dict[str, Any]
    levers_applied: Dict[str, Any]
    executive_recommendations: List[str]


# ── GENERATIONAL TRANSFER OPTIMIZER & SUCCESSION ENGINE ──────

class GenerationalTransferOptimizer:
    """
    Motore quantitativo e normativo istituzionale per Family Office e HNWI.
    Implementa:
    1. Riunione Fittizia dell'Asse Ereditario (Art. 556 c.c.): Relictum - Debiti + Donatum.
    2. Quote di Riserva e Disponibile (Artt. 536-544 c.c.) per tutte le combinazioni di eredi.
    3. Imposte di Successione (D.Lgs. 346/1990) con 4 scaglioni e franchigie ordinarie / L. 104.
    4. Imposte Ipotecarie e Catastali (D.Lgs. 347/1990) con opzione Prima Casa.
    5. Tabella Ministeriale Usufrutto Vitalizio / Nuda Proprietà (D.P.R. 131/1986).
    6. Valutazione Patto di Famiglia (Art. 768-bis c.c. & Art. 3 c. 4-ter TUS).
    7. Simulatore di Ottimizzazione Dinamica Ante vs. Post Pianificazione.
    """

    @staticmethod
    def get_usufruct_and_bare_ownership_shares(donor_age: int) -> Tuple[float, float]:
        """
        Restituisce la percentuale di Usufrutto e Nuda Proprietà in base all'eta del donante/usufruttuario
        secondo la tabella ministeriale attuariale (D.P.R. 131/1986 - TUR).
        Ritorna: (quota_usufrutto_pct, quota_nuda_proprieta_pct) normalizzati (somma = 1.0).
        """
        age = max(0, int(donor_age))
        if age <= 20:
            return 0.95, 0.05
        elif age <= 30:
            return 0.90, 0.10
        elif age <= 40:
            return 0.85, 0.15
        elif age <= 50:
            return 0.80, 0.20
        elif age <= 60:
            return 0.75, 0.25
        elif age <= 65:
            return 0.65, 0.35
        elif age <= 70:
            return 0.50, 0.50
        elif age <= 75:
            return 0.40, 0.60
        elif age <= 80:
            return 0.30, 0.70
        elif age <= 85:
            return 0.20, 0.80
        elif age <= 90:
            return 0.15, 0.85
        else:
            return 0.10, 0.90

    @staticmethod
    def compute_relictum_donatum_balance(
        relictum_gross: float,
        liabilities: float,
        donatum: float
    ) -> Dict[str, float]:
        """
        Calcola l'asse di riunione fittizia ex Art. 556 c.c.
        Formula: Asse Ereditario = max(0, Relictum - Debiti) + Donatum.
        I debiti non possono ridurre il donatum al di sotto dello zero del relictum (Cass. 12919/2012).
        """
        r_gross = max(0.0, float(relictum_gross))
        liab = max(0.0, float(liabilities))
        don = max(0.0, float(donatum))

        r_net = max(0.0, r_gross - liab)
        estate_total = r_net + don

        return {
            "relictum_gross_eur": round(r_gross, 2),
            "liabilities_deductible_eur": round(liab, 2),
            "relictum_net_eur": round(r_net, 2),
            "donatum_total_eur": round(don, 2),
            "fictitious_reunion_estate_eur": round(estate_total, 2)
        }

    @classmethod
    def compute_statutory_shares(
        cls,
        estate_total: float,
        family_profile: FamilyProfile
    ) -> SuccessionSharesResult:
        """
        Determina le quote di riserva (Legittima) e la quota Disponibile ex Artt. 536-544 c.c.
        Gestisce rigorosamente tutte le combinazioni del Codice Civile italiano.
        """
        w = max(0.0, float(estate_total))
        sp = family_profile.has_spouse
        ch_count = max(0, int(family_profile.children_count))
        asc = family_profile.has_ascendants
        dis_ch = min(ch_count, max(0, int(family_profile.disabled_children_count)))

        items: List[StatutoryShareItem] = []

        if sp and ch_count == 0 and not asc:
            # Art. 540 c.c.: Solo Coniuge -> 50% Legittima, 50% Disponibile
            disp_pct = 50.0
            desc = "Solo Coniuge (Art. 540 c.c.): 50% Legittima Coniuge, 50% Quota Disponibile (+ Diritto Abitazione)."
            val_sp = w * 0.50
            items.append(StatutoryShareItem(
                heir_name="Coniuge Superstite",
                relationship="coniuge",
                statutory_pct=50.0,
                statutory_value_eur=round(val_sp, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_sp - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))

        elif sp and ch_count == 1:
            # Art. 542 c. 1 c.c.: Coniuge + 1 Figlio -> 1/3 Coniuge, 1/3 Figlio, 1/3 Disponibile
            disp_pct = 33.3334
            desc = "Coniuge + 1 Figlio (Art. 542 c. 1 c.c.): 1/3 Coniuge, 1/3 Figlio, 1/3 Disponibile."
            val_sp = w * (1.0 / 3.0)
            val_ch = w * (1.0 / 3.0)
            allowance_ch = 1500000.0 if dis_ch > 0 else 1000000.0

            items.append(StatutoryShareItem(
                heir_name="Coniuge Superstite",
                relationship="coniuge",
                statutory_pct=33.33,
                statutory_value_eur=round(val_sp, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_sp - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))
            items.append(StatutoryShareItem(
                heir_name="Figlio Unico" + (" (Portatore Handicap L. 104)" if dis_ch > 0 else ""),
                relationship="figlio",
                statutory_pct=33.33,
                statutory_value_eur=round(val_ch, 2),
                tax_allowance_eur=allowance_ch,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_ch - allowance_ch) * 0.04, 2),
                is_legitimate_heir=True
            ))

        elif sp and ch_count >= 2:
            # Art. 542 c. 2 c.c.: Coniuge + 2+ Figli -> 1/4 Coniuge, 1/2 Figli (diviso n_figli), 1/4 Disponibile
            disp_pct = 25.0
            desc = f"Coniuge + {ch_count} Figli (Art. 542 c. 2 c.c.): 25% Coniuge, 50% Figli ({round(50.0/ch_count, 2)}% cad.), 25% Disponibile."
            val_sp = w * 0.25
            val_per_child = (w * 0.50) / ch_count

            items.append(StatutoryShareItem(
                heir_name="Coniuge Superstite",
                relationship="coniuge",
                statutory_pct=25.0,
                statutory_value_eur=round(val_sp, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_sp - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))
            for i in range(1, ch_count + 1):
                is_dis = (i <= dis_ch)
                allowance = 1500000.0 if is_dis else 1000000.0
                items.append(StatutoryShareItem(
                    heir_name=f"Figlio #{i}" + (" (Handicap L. 104)" if is_dis else ""),
                    relationship="figlio",
                    statutory_pct=round(50.0 / ch_count, 2),
                    statutory_value_eur=round(val_per_child, 2),
                    tax_allowance_eur=allowance,
                    tax_rate_pct=4.0,
                    imposta_successione_eur=round(max(0.0, val_per_child - allowance) * 0.04, 2),
                    is_legitimate_heir=True
                ))

        elif not sp and ch_count == 1:
            # Art. 537 c. 1 c.c.: Solo 1 Figlio -> 50% Figlio, 50% Disponibile
            disp_pct = 50.0
            desc = "Solo 1 Figlio (Art. 537 c. 1 c.c.): 50% Figlio, 50% Quota Disponibile."
            val_ch = w * 0.50
            allowance = 1500000.0 if dis_ch > 0 else 1000000.0

            items.append(StatutoryShareItem(
                heir_name="Figlio Unico" + (" (Portatore Handicap L. 104)" if dis_ch > 0 else ""),
                relationship="figlio",
                statutory_pct=50.0,
                statutory_value_eur=round(val_ch, 2),
                tax_allowance_eur=allowance,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_ch - allowance) * 0.04, 2),
                is_legitimate_heir=True
            ))

        elif not sp and ch_count >= 2:
            # Art. 537 c. 2 c.c.: Solo 2+ Figli -> 2/3 Figli diviso in parti uguali, 1/3 Disponibile
            disp_pct = 33.3333
            desc = f"Solo {ch_count} Figli (Art. 537 c. 2 c.c.): 2/3 Figli ({round(66.67/ch_count, 2)}% cad.), 1/3 Quota Disponibile."
            val_per_child = (w * (2.0 / 3.0)) / ch_count

            for i in range(1, ch_count + 1):
                is_dis = (i <= dis_ch)
                allowance = 1500000.0 if is_dis else 1000000.0
                items.append(StatutoryShareItem(
                    heir_name=f"Figlio #{i}" + (" (Handicap L. 104)" if is_dis else ""),
                    relationship="figlio",
                    statutory_pct=round(66.6667 / ch_count, 2),
                    statutory_value_eur=round(val_per_child, 2),
                    tax_allowance_eur=allowance,
                    tax_rate_pct=4.0,
                    imposta_successione_eur=round(max(0.0, val_per_child - allowance) * 0.04, 2),
                    is_legitimate_heir=True
                ))

        elif sp and ch_count == 0 and asc:
            # Art. 544 c. 1 c.c.: Coniuge + Ascendenti -> 1/2 Coniuge, 1/4 Ascendenti, 1/4 Disponibile
            disp_pct = 25.0
            desc = "Coniuge + Ascendenti in vita (Art. 544 c.c.): 50% Coniuge, 25% Ascendenti, 25% Disponibile."
            val_sp = w * 0.50
            val_asc = w * 0.25

            items.append(StatutoryShareItem(
                heir_name="Coniuge Superstite",
                relationship="coniuge",
                statutory_pct=50.0,
                statutory_value_eur=round(val_sp, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_sp - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))
            items.append(StatutoryShareItem(
                heir_name="Ascendenti (Genitori)",
                relationship="ascendente",
                statutory_pct=25.0,
                statutory_value_eur=round(val_asc, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_asc - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))

        elif not sp and ch_count == 0 and asc:
            # Art. 538 c.c.: Solo Ascendenti -> 1/3 Ascendenti, 2/3 Disponibile
            disp_pct = 66.6667
            desc = "Solo Ascendenti (Art. 538 c.c.): 1/3 Ascendenti, 2/3 Quota Disponibile."
            val_asc = w * (1.0 / 3.0)

            items.append(StatutoryShareItem(
                heir_name="Ascendenti (Genitori)",
                relationship="ascendente",
                statutory_pct=33.33,
                statutory_value_eur=round(val_asc, 2),
                tax_allowance_eur=1000000.0,
                tax_rate_pct=4.0,
                imposta_successione_eur=round(max(0.0, val_asc - 1000000.0) * 0.04, 2),
                is_legitimate_heir=True
            ))

        else:
            # Nessun legittimario ex art. 536 c.c. (Eventuali fratelli o terzi)
            disp_pct = 100.0
            desc = "Nessun Legittimario Primario (Artt. 536 c.c.): 100% Asse Ereditario Disponibile."
            if family_profile.has_siblings:
                desc += " In assenza di testamento, succedono i Fratelli (6% con franchigia € 100.000)."

        tot_legitimate_eur = sum(item.statutory_value_eur for item in items)
        val_disp_eur = w * (disp_pct / 100.0)

        return SuccessionSharesResult(
            relictum_gross_eur=0.0,
            liabilities_deductible_eur=0.0,
            relictum_net_eur=0.0,
            donatum_total_eur=0.0,
            fictitious_reunion_estate_eur=w,
            quota_desc=desc,
            disponibile_pct=round(disp_pct, 2),
            disponibile_eur=round(val_disp_eur, 2),
            legitimate_shares=items,
            total_legitimate_eur=round(tot_legitimate_eur, 2)
        )

    @classmethod
    def check_reduction_risk(
        cls,
        shares_result: SuccessionSharesResult,
        custom_heirs: List[FamilyHeir],
        disponibile_assigned_to_third_parties_eur: float = 0.0
    ) -> Dict[str, Any]:
        """
        Simula l'azione di riduzione (Artt. 553-564 c.c.):
        Verifica se donazioni pregresse o disposizioni testamentarie ledono la quota di riserva dei legittimari.
        """
        injury_detected = False
        total_injury = 0.0
        details = []

        heir_map = {h.name.lower(): h for h in custom_heirs}

        for share in shares_result.legitimate_shares:
            h_obj = heir_map.get(share.heir_name.lower())
            received_tot = 0.0
            if h_obj:
                received_tot = h_obj.donations_received_in_life + h_obj.testamentary_bequest_eur

            if not custom_heirs:
                received_tot = share.statutory_value_eur

            deficit = share.statutory_value_eur - received_tot
            if deficit > 1.0:
                injury_detected = True
                total_injury += deficit
                details.append({
                    "legittimario": share.heir_name,
                    "relazione": share.relationship,
                    "quota_riserva_dovuta_eur": round(share.statutory_value_eur, 2),
                    "valore_effettivo_ricevuto_eur": round(received_tot, 2),
                    "lesione_legittima_eur": round(deficit, 2),
                    "azione_esperibile": "Azione di Riduzione ex Art. 553 c.c."
                })

        return {
            "is_legitimate_injured": injury_detected,
            "total_injury_eur": round(total_injury, 2),
            "injured_heirs_count": len(details),
            "reduction_breakdown": details,
            "remedies": [
                "Conguaglio pecuniario contestuale all'apertura della successione.",
                "Stipula di Patto di Famiglia ex art. 768-bis c.c. con rinuncia/liquidazione della quota.",
                "Attivazione di Polizza Vita a beneficio del legittimario non appagato per provvista liquida."
            ] if injury_detected else ["Nessuna lesione di legittima rilevata. Asse ereditario conforme."]
        }

    @classmethod
    def simulate_generational_plan(
        cls,
        baseline_assets: Dict[str, float],
        liabilities: float,
        donatum: float,
        family_profile: FamilyProfile,
        levers: PlanningLevers
    ) -> OptimizationComparisonResult:
        """
        Esegue la simulazione quantitativa comparativa tra:
        - SCENARIO ANTE-PIANIFICAZIONE (Inerzia / Status Quo)
        - SCENARIO POST-OTTIMIZZAZIONE (Active HNWI Estate Planning)
        """
        re_val = max(0.0, float(baseline_assets.get("real_estate_total", 0.0)))
        fin_val = max(0.0, float(baseline_assets.get("financial_investments", 0.0)))
        cash_val = max(0.0, float(baseline_assets.get("liquidity_cash", 0.0)))
        biz_val = max(0.0, float(baseline_assets.get("business_equity", 0.0)))
        phys_val = max(0.0, float(baseline_assets.get("physical_assets", 0.0)))

        # ── 1. SCENARIO ANTE-PIANIFICAZIONE ─────────────────────────
        relictum_gross_ante = re_val + fin_val + cash_val + biz_val + phys_val
        liab = max(0.0, float(liabilities))
        relictum_net_ante = max(0.0, relictum_gross_ante - liab)
        fict_reunion_ante = relictum_net_ante + donatum

        # Quote di legittima teoriche
        shares_ante = cls.compute_statutory_shares(fict_reunion_ante, family_profile)

        # Base imponibile di successione Ante
        gov_bonds_exempt_ante = fin_val * 0.15
        taxable_relictum_ante = max(0.0, relictum_gross_ante - liab - gov_bonds_exempt_ante)

        ante_estate_tax = 0.0
        n_recipients = len(shares_ante.legitimate_shares)
        if n_recipients > 0:
            for item in shares_ante.legitimate_shares:
                heir_taxable = (item.statutory_pct / 100.0) * taxable_relictum_ante
                taxable_base = max(0.0, heir_taxable - item.tax_allowance_eur)
                ante_estate_tax += taxable_base * (item.tax_rate_pct / 100.0)
        else:
            ante_estate_tax = taxable_relictum_ante * 0.08

        # Imposte Ipotecarie (2%) e Catastali (1%) Ante su immobili
        if re_val > 0:
            if levers.is_first_home_applicable:
                ante_mortgage_cadastral = 400.0  # € 200 + € 200 fisse
            else:
                ante_mortgage_cadastral = re_val * 0.03  # 2% ipotecaria + 1% catastale
        else:
            ante_mortgage_cadastral = 0.0

        ante_total_taxes = ante_estate_tax + ante_mortgage_cadastral
        ante_liquidity_req = ante_total_taxes + (relictum_gross_ante * 0.015)
        ante_prot_score = 25.0

        # ── 2. SCENARIO POST-OTTIMIZZAZIONE ─────────────────────────
        # Leva 1: Polizze Vita Ramo I / III (esenti art. 12 TUS)
        life_ins_alloc = min(fin_val + cash_val, max(0.0, levers.life_insurance_allocation_eur))

        # Leva 2: Holding Familiare / Società Semplice (S.s.) / Patto di Famiglia
        holding_alloc = min(biz_val, max(0.0, levers.holding_family_ss_equity_eur))
        holding_exempt = holding_alloc if levers.patto_di_famiglia_eligible else (holding_alloc * 0.50)

        # Leva 3: Donazione Nuda Proprietà Immobili con Usufrutto Vitalizio
        re_donation_alloc = min(re_val, max(0.0, levers.bare_ownership_donation_re_eur))
        usufruct_pct, bare_pct = cls.get_usufruct_and_bare_ownership_shares(levers.donor_age)
        bare_ownership_val = re_donation_alloc * bare_pct
        re_remaining_in_succession = re_val - re_donation_alloc

        # Leva 4: Conto Corrente Cointestato a firma disgiunta
        joint_cash = min(cash_val, max(0.0, levers.joint_account_cash_eur))
        cash_excluded_by_joint = joint_cash * (1.0 - (levers.joint_account_presumption_pct / 100.0))

        # Ricalcolo Relictum Post
        fin_in_succession_post = max(0.0, fin_val - life_ins_alloc)
        cash_in_succession_post = max(0.0, cash_val - cash_excluded_by_joint)
        biz_in_succession_post = max(0.0, biz_val - holding_exempt)
        gov_bonds_exempt_post = fin_in_succession_post * 0.15

        relictum_gross_post = (
            re_remaining_in_succession +
            fin_in_succession_post +
            cash_in_succession_post +
            biz_in_succession_post +
            phys_val
        )
        relictum_net_post = max(0.0, relictum_gross_post - liab)
        taxable_relictum_post = max(0.0, relictum_net_post - gov_bonds_exempt_post)

        post_estate_tax = 0.0
        if n_recipients > 0:
            for item in shares_ante.legitimate_shares:
                heir_taxable_post = (item.statutory_pct / 100.0) * taxable_relictum_post
                bare_share_per_heir = bare_ownership_val / max(1, family_profile.children_count) if item.relationship == "figlio" else 0.0
                residual_allowance = max(0.0, item.tax_allowance_eur - bare_share_per_heir)
                taxable_base_post = max(0.0, heir_taxable_post - residual_allowance)
                post_estate_tax += taxable_base_post * (item.tax_rate_pct / 100.0)
        else:
            post_estate_tax = taxable_relictum_post * 0.08

        if re_remaining_in_succession > 0:
            if levers.is_first_home_applicable:
                post_mortgage_cadastral = 400.0
            else:
                post_mortgage_cadastral = re_remaining_in_succession * 0.03
        else:
            post_mortgage_cadastral = 0.0

        post_total_taxes = post_estate_tax + post_mortgage_cadastral
        post_liquidity_req = post_total_taxes + (relictum_gross_post * 0.010)

        # Liquidità immediata generata a favore degli eredi (Polizze vita + Conto cointestato)
        immediate_liq = life_ins_alloc + cash_excluded_by_joint

        # Protection Score Post
        prot_score_post = 25.0
        if life_ins_alloc > 0:
            prot_score_post += 20.0
        if holding_alloc > 0:
            prot_score_post += 25.0
        if levers.patto_di_famiglia_eligible:
            prot_score_post += 15.0
        if re_donation_alloc > 0:
            prot_score_post += 10.0
        prot_score_post = min(95.0, prot_score_post)

        tax_savings = max(0.0, ante_total_taxes - post_total_taxes)
        tax_savings_pct = (tax_savings / ante_total_taxes * 100.0) if ante_total_taxes > 0 else 0.0
        lcr = (immediate_liq / post_total_taxes) if post_total_taxes > 0 else 999.0

        recommendations = []
        if life_ins_alloc > 0:
            recommendations.append(
                f"🛡️ **Polizza Vita Ramo I/III (€ {life_ins_alloc:,.0f})**: Capitale segregato esente da imposta ex art. 12 TUS, impignorabile ex art. 1923 c.c. e liquidabile agli eredi entro 30 giorni."
            )
        if re_donation_alloc > 0:
            recommendations.append(
                f"🏡 **Donazione Nuda Proprietà (€ {re_donation_alloc:,.0f})**: All'età di {levers.donor_age} anni, usufrutto riservato al {usufruct_pct*100:.0f}%, base imponibile ridotta al {bare_pct*100:.0f}% (€ {bare_ownership_val:,.0f}). Consolidamento automatico esente alla morte."
            )
        if holding_alloc > 0 and levers.patto_di_famiglia_eligible:
            recommendations.append(
                f"🏛️ **Patto di Famiglia (Art. 768-bis c.c.)**: Esenzione integrale al 100% da imposta per trasferimento del controllo (€ {holding_alloc:,.0f}) ex art. 3 c. 4-ter TUS con blindatura da future liti ereditarie."
            )
        if joint_cash > 0:
            recommendations.append(
                f"💳 **Cointestazione a Firma Disgiunta (€ {joint_cash:,.0f})**: Presunzione di contitolarità al 50% ex art. 1298 c.c. Mantiene disponibilità immediata di cassa per le prime spese successorie."
            )
        if not recommendations:
            recommendations.append("Attivare le leve di pianificazione (Polizze, Nuda Proprietà o Patto di Famiglia) per simulare l'abbattimento fiscale.")

        return OptimizationComparisonResult(
            ante_relictum_taxable_eur=round(taxable_relictum_ante, 2),
            ante_estate_tax_eur=round(ante_estate_tax, 2),
            ante_mortgage_cadastral_tax_eur=round(ante_mortgage_cadastral, 2),
            ante_total_taxes_eur=round(ante_total_taxes, 2),
            ante_liquidity_required_eur=round(ante_liquidity_req, 2),
            ante_protection_score=round(ante_prot_score, 1),
            post_relictum_taxable_eur=round(taxable_relictum_post, 2),
            post_estate_tax_eur=round(post_estate_tax, 2),
            post_mortgage_cadastral_tax_eur=round(post_mortgage_cadastral, 2),
            post_total_taxes_eur=round(post_total_taxes, 2),
            post_liquidity_required_eur=round(post_liquidity_req, 2),
            post_protection_score=round(prot_score_post, 1),
            tax_savings_eur=round(tax_savings, 2),
            tax_savings_pct=round(tax_savings_pct, 1),
            immediate_liquidity_generated_eur=round(immediate_liq, 2),
            reduction_risk_mitigated=levers.patto_di_famiglia_eligible,
            liquidity_coverage_ratio=round(min(999.0, lcr), 2),
            breakdown_ante={
                "relictum_gross": relictum_gross_ante,
                "liabilities": liab,
                "re_value": re_val,
                "fin_value": fin_val,
                "cash_value": cash_val,
                "business_value": biz_val
            },
            breakdown_post={
                "relictum_gross": relictum_gross_post,
                "re_remaining": re_remaining_in_succession,
                "fin_remaining": fin_in_succession_post,
                "cash_remaining": cash_in_succession_post,
                "business_remaining": biz_in_succession_post
            },
            levers_applied={
                "life_insurance": life_ins_alloc,
                "bare_ownership_donation": re_donation_alloc,
                "bare_ownership_net_base": bare_ownership_val,
                "holding_family_equity": holding_alloc,
                "patto_di_famiglia": levers.patto_di_famiglia_eligible,
                "joint_account_cash": joint_cash
            },
            executive_recommendations=recommendations
        )

    @classmethod
    def generate_executive_succession_memo(
        cls,
        comparison: OptimizationComparisonResult,
        family_profile: FamilyProfile
    ) -> str:
        """
        Genera un Executive Succession Memorandum istituzionale formattato in Markdown, pronto per il Family Office.
        """
        memo = f"""# 🏛️ MEMORANDUM ISTITUZIONALE DI PIANIFICAZIONE SUCCESSORIA & ASSET PROTECTION
**Data di Elaborazione:** {pd.Timestamp.now().strftime('%d/%m/%Y')}
**Destinatario:** Family Office / Disponente Patrimoniale HNWI
**Riferimenti Giuridici:** Codice Civile (Artt. 536-564, 768-bis, 1923), D.Lgs. 346/1990 (TUS), D.Lgs. 347/1990

---

## 1. Executive Summary & Confronto Scenari

| Metrica Chiave | Scenario Ante-Pianificazione | Scenario Post-Ottimizzazione | Delta / Risparmio Generato |
| :--- | :--- | :--- | :--- |
| **Imposta di Successione** | € {comparison.ante_estate_tax_eur:,.2f} | € {comparison.post_estate_tax_eur:,.2f} | - € {comparison.ante_estate_tax_eur - comparison.post_estate_tax_eur:,.2f} |
| **Imposte Ipo-Catastali** | € {comparison.ante_mortgage_cadastral_tax_eur:,.2f} | € {comparison.post_mortgage_cadastral_tax_eur:,.2f} | - € {comparison.ante_mortgage_cadastral_tax_eur - comparison.post_mortgage_cadastral_tax_eur:,.2f} |
| **Carico Tributario Totale** | **€ {comparison.ante_total_taxes_eur:,.2f}** | **€ {comparison.post_total_taxes_eur:,.2f}** | **- € {comparison.tax_savings_eur:,.2f} ({comparison.tax_savings_pct:.1f}%)** |
| **Liquidità Richiesta agli Eredi** | € {comparison.ante_liquidity_required_eur:,.2f} | € {comparison.post_liquidity_required_eur:,.2f} | Fabbisogno cassa abbattuto |
| **Liquidità Immediata Disponibile** | € 0,00 | € {comparison.immediate_liquidity_generated_eur:,.2f} | Polizze vita svincolate dal blocco bancario |
| **Indice Tutela Patrimoniale** | {comparison.ante_protection_score:.0f} / 100 | **{comparison.post_protection_score:.0f} / 100** | Segregazione e scudo revocatoria rafforzati |

---

## 2. Leve di Ottimizzazione Attivate

"""
        for rec in comparison.executive_recommendations:
            memo += f"- {rec}\n"

        memo += f"""
---

## 3. Conformità al Codice Civile e Gestione Rischio Riduzione
- **Struttura Familiare:** Coniuge: {'Presente' if family_profile.has_spouse else 'Assente'} | Figli: {family_profile.children_count} | Figli Disabili L. 104: {family_profile.disabled_children_count}
- **Scudo Legittima:** {'Attivo e blindato tramite Patto di Famiglia (Art. 768-quater c.c.)' if comparison.reduction_risk_mitigated else 'Monitoraggio quote raccomandato in sede testamentaria'}.
- **Copertura Fabbisogno Fiscale:** Indice LCR pari a **{comparison.liquidity_coverage_ratio:.2f}x** il carico tributario post-ottimizzazione.
"""
        return memo


# ── MOTORE ASSET PROTECTION GENERALE (ESTENSIONE) ────────────

class AssetProtectionEngine:
    """
    Motore attuariale e giuridico per la protezione patrimoniale e la segregazione dei rischi.
    Analizza comparativamente:
    1. Persona Fisica (Nessuna protezione)
    2. Fondo Patrimoniale (Art. 167 c.c.)
    3. Trust Interno / Istituzionale (Convenzione dell'Aja 1985)
    4. Società Semplice (S.s.) / Holding Familiare con PEX
    5. Polizze Vita Ramo I / Ramo III (Art. 1923 c.c.)
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
                "Regime PEX (Participation Exemption): 95% esenzione sulle plusvalenze e dividendi societari.",
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
                "Punteggio Tutela": "25 / 100",
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
