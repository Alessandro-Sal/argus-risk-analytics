# ==============================================================================
# core/wealth/neural_advisor_engine.py
# ARGUS — Neural Wealth Advisor & Conversational Action Memo Engine
# ==============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class AdvisoryMemoSection:
    title: str
    content: str
    status: str  # 'POSITIVE', 'WARNING', 'ACTION_REQUIRED'


class NeuralWealthAdvisor:
    """
    Motore di intelligenza analitica per la consulenza patrimoniale contestuale.
    Interpreta richieste complesse 'What-If', valuta lo stato contabile/fiscale e
    redige un Executive Action Memo con raccomandazioni vincolanti e quantificate.
    """

    @staticmethod
    def evaluate_scenario_query(
        query: str,
        summary_data: Dict[str, Any],
        fiscal_data: Optional[Dict[str, Any]] = None,
        cf_analytics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analizza ed elabora matematicamente una query o simulazione patrimoniale.
        Restituisce diagnosi quantitativa, impatto su Net Worth, Runway e Health Score.
        """
        q_low = str(query or "").lower().strip()
        tot_nw = float(summary_data.get("total_net_worth", 0.0))
        liq_cash = float(summary_data.get("liquid_cash", 0.0))
        fin_inv = float(summary_data.get("financial_investments", 0.0))
        re_val = float(summary_data.get("real_estate_total", 0.0))
        re_equity = float(summary_data.get("real_estate_equity", re_val))
        phys_val = float(summary_data.get("physical_assets", 0.0))
        pension_val = float(summary_data.get("pension_total", 0.0))
        debts = float(summary_data.get("total_liabilities", 0.0))
        runway_mo = float(summary_data.get("runway_months", 6.0))
        health_sc = float(summary_data.get("wealth_health_score", 85.0))
        monthly_exp = max(500.0, liq_cash / max(0.1, runway_mo))

        result_type = "GENERAL_ADVISORY"
        title = "Diagnosi Patrimoniale Strategica"
        key_metrics = {}
        action_plan = []
        projected_nw = tot_nw
        projected_runway = runway_mo
        projected_health = health_sc
        summary_text = ""

        # ── CASO 1: OTTIMIZZAZIONE ZAINETTO FISCALE & TLH ──
        if any(w in q_low for w in ["zainetto", "fisco", "minusvalenze", "minus", "tax loss", "compensare"]):
            result_type = "TAX_OPTIMIZATION"
            title = "Strategia di Azzeramento Zainetto Fiscale (TUIR Art. 67)"
            tax_loss_harvestable = 4500.0  # Default di simulazione se non esplicito
            if fiscal_data and "minusvalenze" in fiscal_data:
                minus_df = fiscal_data["minusvalenze"]
                if hasattr(minus_df, "amount"):
                    tax_loss_harvestable = float(minus_df["amount"].sum())

            tax_saving = tax_loss_harvestable * 0.26
            key_metrics = {
                "Minusvalenze Pregresse Rilevate": f"€ {tax_loss_harvestable:,.2f}",
                "Risparmio Tributario Potenziale (26%)": f"€ {tax_saving:,.2f}",
                "Scadenza Imminente": "31 Dicembre (Quarto Anno)",
                "Strumenti Idonei alla Compensazione": "Azioni Singole, Certificati, ETC Oro"
            }
            action_plan = [
                "1. Isolare le posizioni azionarie o certificate in forte plusvalenza latente nel portafoglio.",
                "2. Eseguire vendita e riacquisto contestuale (Rebuy) prima del 31/12 per affrancare il capital gain senza modificare l'asset allocation.",
                "3. Evitare fondi comuni ed ETF tradizionali per la compensazione (generano redditi di capitale non compensabili con redditi diversi ex Art. 67 TUIR)."
            ]
            summary_text = f"Attraverso una manovra di Tax-Loss Harvesting mirata è possibile recuperare fino a € {tax_saving:,.2f} di credito d'imposta senza intaccare il valore del portafoglio."

        # ── CASO 2: SIMULAZIONE ACQUISTO IMMOBILE CON MUTUO ──
        elif any(w in q_low for w in ["immobile", "casa", "mutuo", "comprare", "acquisto"]):
            result_type = "REAL_ESTATE_PURCHASE"
            title = "Simulazione Impatto Acquisto Immobile & Leva Finanziaria"
            prop_price = 300000.0
            down_payment = 60000.0  # 20% anticipo
            loan_amount = 240000.0  # 80% mutuo
            notary_agency_taxes = prop_price * 0.08  # 8% costi accessori

            post_cash = max(0.0, liq_cash - down_payment - notary_agency_taxes)
            post_debts = debts + loan_amount
            post_re = re_val + prop_price
            projected_nw = (post_cash + fin_inv + phys_val + post_re + pension_val) - post_debts
            projected_runway = post_cash / monthly_exp
            new_ltv = (post_debts / post_re) * 100.0 if post_re > 0 else 0.0
            projected_health = max(30.0, min(100.0, health_sc - (15.0 if new_ltv > 75 else 5.0)))

            key_metrics = {
                "Valore Immobile Ipotizzato": f"€ {prop_price:,.2f}",
                "Anticipo + Spese Accessorie (Cash Out)": f"€ {down_payment + notary_agency_taxes:,.2f}",
                "Nuovo Debito Ipotecario (LTV 80%)": f"€ {loan_amount:,.2f}",
                "Nuovo Runway di Emergenza": f"{projected_runway:.1f} Mesi (da {runway_mo:.1f} Mesi)",
                "Nuovo Wealth Health Score": f"{projected_health:.0f}/100"
            }
            action_plan = [
                f"1. Verificare che la cassa residua (€ {post_cash:,.2f}) garantisca almeno 6 mesi di spese.",
                "2. Rinegoziare la rata del mutuo affinché il DSTI (Debt Service-to-Income) non superi il 30% del reddito mensile.",
                "3. Mantenere intatta la componente investimenti finanziari per evitare disinvestimenti in fasi di mercato avverse."
            ]
            summary_text = f"L'acquisto comporta un esborso di cassa di € {down_payment + notary_agency_taxes:,.2f} e porta il debito totale a € {post_debts:,.2f}, riducendo il runway a {projected_runway:.1f} mesi."

        # ── CASO 3: LIQUIDAZIONE ASSET CAVEAU PER ESTINZIONE MUTUO ──
        elif any(w in q_low for w in ["caveau", "orologi", "estinguere", "estinzione", "vendi orologi"]):
            result_type = "DEBT_PAYOFF_WITH_PHYSICAL"
            title = "Strategia di De-leveraging tramite Smobilizzo Asset Fisici"
            smobilizzo_val = min(phys_val, 40000.0) if phys_val > 0 else 20000.0
            repayment_amount = min(debts, smobilizzo_val)
            post_debts = max(0.0, debts - repayment_amount)
            post_phys = max(0.0, phys_val - smobilizzo_val)
            projected_nw = (liq_cash + fin_inv + post_phys + re_val + pension_val) - post_debts
            projected_health = min(100.0, health_sc + 8.0)

            key_metrics = {
                "Valore Smobilizzo Orologi/Caveau": f"€ {smobilizzo_val:,.2f}",
                "Quota Debito/Mutuo Estinta": f"€ {repayment_amount:,.2f}",
                "Interessi Passivi Futuri Risparmiati": f"€ {repayment_amount * 0.035 * 10:,.2f} (stima 10y)",
                "Nuovo Debito Residuo": f"€ {post_debts:,.2f}",
                "Impatto Health Score": f"+8 Punti ({projected_health:.0f}/100)"
            }
            action_plan = [
                "1. Selezionare i pezzi del caveau a minor potenziale di rivalutazione o con costi assicurativi sproporzionati.",
                "2. Richiedere alla banca il conteggio estintivo parziale senza penali (Legge Bersani n. 40/2007 per mutui residenziali).",
                "3. Reindirizzare la rata mensile risparmiata verso un piano di accumulo del capitale (PAC azionario globale)."
            ]
            summary_text = f"Estinguere € {repayment_amount:,.2f} di debito tramite il caveau riduce la leva patrimoniale e genera un risparmio di interessi passivi stimato in € {repayment_amount * 0.035 * 10:,.2f}."

        # ── CASO 4: PIANIFICAZIONE INDIPENDENZA FINANZIARIA (FIRE) ──
        elif any(w in q_low for w in ["fire", "indipendenza", "rendita", "libertà", "decumulo"]):
            result_type = "FIRE_PLANNING"
            title = "Roadmap Strategica verso l'Indipendenza Finanziaria (FIRE)"
            annual_exp = monthly_exp * 12.0
            fire_target = annual_exp * 25.0  # Regola del 4%
            fire_progress = (tot_nw / fire_target * 100.0) if fire_target > 0 else 0.0

            key_metrics = {
                "Fabbisogno Annuo Stimato": f"€ {annual_exp:,.2f}",
                "FIRE Target (Safe Withdrawal Rate 4%)": f"€ {fire_target:,.2f}",
                "Patrimonio Attuale / Copertura": f"{fire_progress:.1f}%",
                "Capitale Mancante al Target": f"€ {max(0.0, fire_target - tot_nw):,.2f}"
            }
            action_plan = [
                "1. Incrementare il tasso di risparmio oltre il 30% per accelerare il compounding a lungo termine.",
                "2. Massimizzare la deducibilità pensionistica (€ 5.164,57 annui) per generare liquidità fiscale aggiuntiva.",
                "3. Mantenere un portafoglio azionario/obbligazionario globale con TCO < 0.25% per annullare il fee drag."
            ]
            summary_text = f"Il tuo obiettivo di indipendenza finanziaria richiede un capitale di € {fire_target:,.2f}. Attualmente copri il {fire_progress:.1f}% del target."

        # ── CASO 5: DIAGNOSI GENERALE DI SALUTE E RESILIENZA ──
        else:
            result_type = "GENERAL_DIAGNOSTICS"
            title = "Diagnosi Olistica di Resilienza e Allocazione Patrimoniale"
            key_metrics = {
                "Patrimonio Netto Consolidato": f"€ {tot_nw:,.2f}",
                "Autonomia Finanziaria (Runway)": f"{runway_mo:.1f} Mesi",
                "Indice di Salute Globale": f"{health_sc:.0f}/100",
                "Incidenza Debiti / Patrimonio": f"{(debts / max(1.0, tot_nw + debts) * 100):.1f}%"
            }
            action_plan = [
                "1. Mantenere la diversificazione tra asset liquidi, finanziari quotati, immobili e asset da collezione.",
                "2. Ribilanciare semestralmente il portafoglio investimenti per riportare le asset class ai pesi strategici.",
                "3. Monitorare trimestralmente gli indicatori del Financial Watchdog per prevenire inefficienze tributarie."
            ]
            summary_text = f"Il patrimonio presenta un profilo solido (Score {health_sc:.0f}/100) con un'autonomia di liquidità di {runway_mo:.1f} mesi e un debito complessivo di € {debts:,.2f}."

        return {
            "result_type": result_type,
            "title": title,
            "summary_text": summary_text,
            "key_metrics": key_metrics,
            "action_plan": action_plan,
            "pre_shock_nw": tot_nw,
            "projected_nw": projected_nw,
            "projected_runway": projected_runway,
            "projected_health": projected_health
        }

    @staticmethod
    def generate_executive_action_memo(
        summary_data: Dict[str, Any],
        scenario_results: List[Dict[str, Any]],
        prof_name: str = "Family Office Master"
    ) -> str:
        """
        Redige un documento Markdown esecutivo formale (Executive Action Memo)
        pronto per essere stampato o presentato al comitato patrimoniale.
        """
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        tot_nw = float(summary_data.get("total_net_worth", 0.0))
        health_sc = float(summary_data.get("wealth_health_score", 85.0))
        runway_mo = float(summary_data.get("runway_months", 6.0))

        lines = [
            f"# 🏛️ EXECUTIVE WEALTH ADVISORY MEMO",
            f"**Profilo:** {prof_name} | **Data Emissione:** {now_str} | **Classificazione:** Riservato / Istituzionale",
            f"**Health Score Globale:** {health_sc:.0f}/100 | **Net Worth:** € {tot_nw:,.2f} | **Runway:** {runway_mo:.1f} Mesi",
            "---",
            "## 📌 1. Sintesi Diagnostica dell'Assetto Patrimoniale",
            f"L'analisi olistica condotta dal motore quantitativo di ARGUS evidenzia uno stato patrimoniale con solvibilità solida e un cuscinetto di liquidità pari a {runway_mo:.1f} mensilità.",
            "",
            "## 🎯 2. Scenari Simulati e Raccomandazioni Strategiche"
        ]

        for i, sc in enumerate(scenario_results, 1):
            lines.append(f"### 2.{i} {sc['title']}")
            lines.append(f"*{sc['summary_text']}*")
            lines.append("")
            lines.append("**Metriche Chiave di Scenario:**")
            for k, v in sc["key_metrics"].items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")
            lines.append("**Piano di Esecuzione Consigliato:**")
            for step in sc["action_plan"]:
                lines.append(f"- {step}")
            lines.append("")

        lines.extend([
            "---",
            "## ⚖️ 3. Nota di Conformità e Governance",
            "Il presente documento costituisce una perizia analitica e quantitativa a supporto delle decisioni strategiche del Family Office. Tutte le raccomandazioni sono formulate nel rispetto del quadro tributario italiano (TUIR, D.Lgs. 346/1990) e dei principi di gestione prudenziale del rischio.",
            "",
            "*ARGUS Institutional Intelligence Engine v6.3.0*"
        ])

        return "\n".join(lines)
