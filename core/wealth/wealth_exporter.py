# ============================================================
# core/wealth/wealth_exporter.py
# ARGUS Wealth — Institutional Multi-Tab Excel Master Dossier Exporter
# ============================================================

import io
import math
import numpy as np
import pandas as pd
import xlsxwriter
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Engine

from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_cashflow_analytics,
    simulate_pension_projection,
    compute_fire_analytics,
    compute_fiscal_analytics,
    compute_mortgage_amortization,
    compute_real_estate_roi,
    compute_estate_planning_analytics,
    compute_ai_wealth_diagnostics
)
from core.wealth.wealth_db import (
    get_wealth_accounts,
    get_cashflow_records,
    get_physical_assets,
    get_pension_plans,
    get_wealth_portfolios,
    get_linked_risk_portfolios_summary
)


def _safe_num(val, default=0.0) -> float:
    """Conversione sicura in float per evitare errori NaN o Inf in openpyxl/xlsxwriter."""
    if val is None or pd.isna(val):
        return default
    try:
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval) or np.isnan(fval) or np.isinf(fval):
            return default
        return fval
    except Exception:
        return default


def export_wealth_master_excel_workbook(engine: Engine, portfolio_id: int = 1) -> io.BytesIO:
    """
    Genera un Master Dossier Excel (.xlsx) a 10 fogli istituzionale per Family Office & Private Banking:
    1. Executive Summary & Net Worth (Stato Patrimoniale Consolidato)
    2. Cash Flow & 50-30-20 (Libro Mastro Spese ed Entrate)
    3. Conti Correnti & Depositi (Anagrafica e Saldi)
    4. Caveau, Orologi & Fisici (Inventario e Valutazioni)
    5. Previdenza Integrativa (Fondi Pensione e Deducibilità)
    6. Indipendenza & FIRE (Roadmap e Safe Withdrawal Rate)
    7. Fiscalità & Quadro RW (Monitoraggio Fiscale e Minusvalenze)
    8. Immobili & Mutui (Piano Ammortamento & Cap Rate)
    9. Successione & Eredi (Quote di Legittima e Franchigie)
    10. AI Diagnostics & Rebalance (Colli di Bottiglia e Ribilanciamento)
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'nan_inf_to_errors': True})

    # ── FORMATI GRAFICI ISTITUZIONALI (Midnight Obsidian & Navy Blue) ──
    f_hdr_navy = workbook.add_format({
        'bold': True, 'bg_color': '#0f172a', 'font_color': '#ffffff',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
    })
    f_hdr_emerald = workbook.add_format({
        'bold': True, 'bg_color': '#064e3b', 'font_color': '#ffffff',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11
    })
    f_title = workbook.add_format({
        'bold': True, 'font_size': 14, 'font_color': '#0f172a'
    })
    f_subtitle = workbook.add_format({
        'italic': True, 'font_size': 10, 'font_color': '#64748b'
    })
    f_bold = workbook.add_format({'bold': True})
    f_currency = workbook.add_format({'num_format': '€ #,##0.00'})
    f_bold_currency = workbook.add_format({'bold': True, 'num_format': '€ #,##0.00', 'bg_color': '#f1f5f9'})
    f_pct = workbook.add_format({'num_format': '0.00%'})
    f_bold_pct = workbook.add_format({'bold': True, 'num_format': '0.00%'})
    f_date = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})

    # ── RECUPERO DATI CORE WEALTH ──
    from core.wealth.wealth_engine import (
        compute_consolidated_net_worth,
        compute_cashflow_analytics,
        simulate_pension_projection,
        compute_fire_analytics,
        compute_fiscal_analytics,
        compute_mortgage_amortization,
        compute_real_estate_roi,
        compute_estate_planning_analytics,
        compute_ai_wealth_diagnostics
    )
    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)
    df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
    df_phys = get_physical_assets(engine, portfolio_id=portfolio_id)
    df_pens = get_pension_plans(engine, portfolio_id=portfolio_id)
    df_prof = get_wealth_portfolios(engine)
    prof_name = "Personale"
    if not df_prof.empty and portfolio_id in df_prof["portfolio_id"].values:
        prof_name = str(df_prof.loc[df_prof["portfolio_id"] == portfolio_id, "name"].values[0])

    fiscal = compute_fiscal_analytics(engine, portfolio_id=portfolio_id)
    estate = compute_estate_planning_analytics(net_worth_summary=nw)
    ai_diag = compute_ai_wealth_diagnostics(engine, portfolio_id=portfolio_id)
    _, df_risk_linked = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=portfolio_id)


    # ── SHEET 1: EXECUTIVE SUMMARY & NET WORTH ───────────────────
    ws1 = workbook.add_worksheet("1_Executive_NetWorth")
    ws1.write("A1", f"ARGUS WEALTH MANAGEMENT — STATO PATRIMONIALE CONSOLIDATO", f_title)
    ws1.write("A2", f"Profilo: {prof_name.upper()} | Data Generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}", f_subtitle)

    headers1 = ["Macro Classe di Attivo", "Dettaglio Componente", "Valore Attuale (€)", "Peso sul Patrimonio (%)", "Liquidabilità / Profilo Rischio"]
    for c, h in enumerate(headers1):
        ws1.write(3, c, h, f_hdr_navy)

    rows1 = [
        ("Liquidità & Riserve", "Conti Correnti & Depositi a Vista", nw.liquid_cash, (nw.liquid_cash / (nw.total_net_worth or 1)), "Immediata (T+0) / Risk-Free"),
        ("Investimenti Finanziari", "Portafogli Titoli, ETF & Crypto (Risk Link)", nw.financial_investments, (nw.financial_investments / (nw.total_net_worth or 1)), "Alta (T+2) / Market Volatility"),
        ("Caveau & Beni Reali", "Orologi di Lusso, Oro da Investimento & Immobili", nw.physical_assets, (nw.physical_assets / (nw.total_net_worth or 1)), "Bassa / Illiquido da Collezione"),
        ("Previdenza Integrativa", "Fondi Pensione Aperti, PIP & TFR", nw.pension_total, (nw.pension_total / (nw.total_net_worth or 1)), "Vincolata al Pensionamento / Protetto TUIR"),
    ]
    for r_idx, (cat, det, val, weight, liq) in enumerate(rows1, start=4):
        ws1.write(r_idx, 0, cat)
        ws1.write(r_idx, 1, det)
        ws1.write(r_idx, 2, _safe_num(val), f_currency)
        ws1.write(r_idx, 3, _safe_num(weight), f_pct)
        ws1.write(r_idx, 4, liq)

    ws1.write(8, 0, "TOTALE ATTIVO PATRIMONIALE", f_bold)
    ws1.write(8, 1, "Consolidato Lordo", f_bold)
    ws1.write(8, 2, _safe_num(nw.total_net_worth + nw.total_liabilities), f_bold_currency)
    ws1.write(8, 3, 1.0, f_bold_pct)
    ws1.write(8, 4, "Consolidato", f_bold)

    ws1.write(9, 0, "Passività & Debiti Residui", f_bold)
    ws1.write(9, 1, "Mutui e Finanziamenti", f_bold)
    ws1.write(9, 2, _safe_num(nw.total_liabilities), f_currency)
    ws1.write(9, 3, _safe_num(nw.total_liabilities / (nw.total_net_worth or 1)), f_pct)
    ws1.write(9, 4, "Debito Finanziario")

    ws1.write(10, 0, "PATRIMONIO NETTO EFFETTIVO (NET WORTH)", f_bold)
    ws1.write(10, 1, "Attivo Netto Consolidato", f_bold)
    ws1.write(10, 2, _safe_num(nw.total_net_worth), f_bold_currency)
    ws1.write(10, 3, 1.0, f_bold_pct)
    ws1.write(10, 4, f"Health Score: {nw.wealth_health_score:.0f}/100", f_bold)

    ws1.autofit()

    # ── SHEET 2: CASH FLOW & 50/30/20 ────────────────────────────
    ws2 = workbook.add_worksheet("2_Cash_Flow_Ledger")
    ws2.write("A1", "LIBRO MASTRO CASSA & ANALISI FLUSSI FINANZIARI", f_title)
    ws2.write("A2", "Storico Transazioni e Classificazione Regola 50/30/20", f_subtitle)

    headers2 = ["ID Tx", "Data", "Conto / Metodo", "Direzione", "Importo (€)", "Categoria", "Natura (50/30/20)", "Esercente / Note"]
    for c, h in enumerate(headers2):
        ws2.write(3, c, h, f_hdr_emerald)

    if not df_cf.empty:
        for r_idx, (_, row) in enumerate(df_cf.iterrows(), start=4):
            ws2.write(r_idx, 0, int(row.get("tx_id", r_idx)))
            ws2.write(r_idx, 1, str(row.get("tx_date", ""))[:10], f_date)
            ws2.write(r_idx, 2, str(row.get("payment_method", "Bonifico / Carta")))
            ws2.write(r_idx, 3, str(row.get("direction", "outflow")).upper())
            ws2.write(r_idx, 4, _safe_num(row.get("amount", 0.0)), f_currency)
            ws2.write(r_idx, 5, str(row.get("category_name", "Generale")))
            ws2.write(r_idx, 6, str(row.get("nature", "Necessità Primaria")))
            ws2.write(r_idx, 7, str(row.get("merchant", "") or row.get("notes", "")))
    ws2.autofit()

    # ── SHEET 3: CONTI CORRENTI & DEPOSITI ───────────────────────
    ws3 = workbook.add_worksheet("3_Conti_e_Banche")
    ws3.write("A1", "ANAGRAFICA CONTI CORRENTI, DEPOSITI & BROKER", f_title)

    headers3 = ["ID Conto", "Nome Conto", "Istituto Bancario", "Tipo Conto", "IBAN / Riferimento", "Saldo Live (€)", "Valuta", "Domiciliazione Fiscale"]
    for c, h in enumerate(headers3):
        ws3.write(3, c, h, f_hdr_navy)

    if not df_acc.empty:
        for r_idx, (_, row) in enumerate(df_acc.iterrows(), start=4):
            iban = str(row.get("iban", "") or "").upper()
            is_foreign = bool(iban and not iban.startswith("IT"))
            ws3.write(r_idx, 0, int(row.get("account_id", r_idx)))
            ws3.write(r_idx, 1, str(row.get("name", "")))
            ws3.write(r_idx, 2, str(row.get("institution", "")))
            ws3.write(r_idx, 3, str(row.get("account_type", "")))
            ws3.write(r_idx, 4, iban if iban else "N/D")
            ws3.write(r_idx, 5, _safe_num(row.get("balance", 0.0)), f_currency)
            ws3.write(r_idx, 6, str(row.get("currency", "EUR")))
            ws3.write(r_idx, 7, "Estero (Quadro RW / IVAFE)" if is_foreign else "Italia (Imposta Bollo)")
    ws3.autofit()

    # ── SHEET 4: CAVEAU & BENI FISICI ────────────────────────────
    ws4 = workbook.add_worksheet("4_Caveau_Asset_Fisici")
    ws4.write("A1", "INVENTARIO CAVEAU, OROLOGI DI LUSSO & METALLI", f_title)

    headers4 = ["ID Asset", "Nome Asset", "Categoria", "Brand / Localizzazione", "Modello / Referenza", "Prezzo Acquisto (€)", "Valore di Mercato Live (€)", "Plusvalenza / Minus (€)", "Rendimento %"]
    for c, h in enumerate(headers4):
        ws4.write(3, c, h, f_hdr_navy)

    if not df_phys.empty:
        for r_idx, (_, row) in enumerate(df_phys.iterrows(), start=4):
            cost = _safe_num(row.get("purchase_price", 0.0))
            mkt = _safe_num(row.get("current_market_value", 0.0))
            gain = mkt - cost
            gain_pct = (gain / cost) if cost > 0 else 0.0
            ws4.write(r_idx, 0, int(row.get("asset_id", r_idx)))
            ws4.write(r_idx, 1, str(row.get("name", "")))
            ws4.write(r_idx, 2, str(row.get("asset_category", "")))
            ws4.write(r_idx, 3, str(row.get("brand_or_location", "")))
            ws4.write(r_idx, 4, str(row.get("reference_number", "") or row.get("model_or_specs", "")))
            ws4.write(r_idx, 5, cost, f_currency)
            ws4.write(r_idx, 6, mkt, f_currency)
            ws4.write(r_idx, 7, gain, f_currency)
            ws4.write(r_idx, 8, gain_pct, f_pct)
    ws4.autofit()

    # ── SHEET 5: PREVIDENZA INTEGRATIVA ──────────────────────────
    ws5 = workbook.add_worksheet("5_Previdenza_Fondi_Pensione")
    ws5.write("A1", "FONDI PENSIONE & PREVIDENZA COMPLEMENTARE (TUIR ART. 51)", f_title)

    headers5 = ["ID Piano", "Nome Fondo", "Gestore / Provider", "Linea Investimento", "Montante Maturato (€)", "Versamento Dipendente (€/m)", "Versamento Datore (€/m)", "Tetto Deducibile Residuo (€)"]
    for c, h in enumerate(headers5):
        ws5.write(3, c, h, f_hdr_emerald)

    if not df_pens.empty:
        for r_idx, (_, row) in enumerate(df_pens.iterrows(), start=4):
            contrib_ann = (_safe_num(row.get("monthly_employee_contrib", 0.0)) + _safe_num(row.get("monthly_employer_contrib", 0.0))) * 12.0
            resid_deduct = max(0.0, 5164.57 - contrib_ann)
            ws5.write(r_idx, 0, int(row.get("plan_id", r_idx)))
            ws5.write(r_idx, 1, str(row.get("plan_name", "")))
            ws5.write(r_idx, 2, str(row.get("provider", "")))
            ws5.write(r_idx, 3, str(row.get("investment_line", "")))
            ws5.write(r_idx, 4, _safe_num(row.get("accumulated_value", 0.0)), f_currency)
            ws5.write(r_idx, 5, _safe_num(row.get("monthly_employee_contrib", 0.0)), f_currency)
            ws5.write(r_idx, 6, _safe_num(row.get("monthly_employer_contrib", 0.0)), f_currency)
            ws5.write(r_idx, 7, resid_deduct, f_currency)
    ws5.autofit()

    # ── SHEET 6: FISCALITÀ & QUADRO RW ───────────────────────────
    ws6 = workbook.add_worksheet("6_Fiscalita_Quadro_RW")
    ws6.write("A1", "PROSPETTO DI MONITORAGGIO FISCALE & QUADRO RW/RT", f_title)

    headers6 = ["Rigo Quadro RW", "Descrizione Intermediario", "Codice Investimento", "Codice Stato Estero", "Valore Finale al 31/12 (€)", "IVAFE Dovuta (€)", "Solo Monitoraggio"]
    for c, h in enumerate(headers6):
        ws6.write(3, c, h, f_hdr_navy)

    for r_idx, rw_row in enumerate(fiscal["quadro_rw_rows"], start=4):
        ws6.write(r_idx, 0, str(rw_row["rigo"]))
        ws6.write(r_idx, 1, str(rw_row["descrizione"]))
        ws6.write(r_idx, 2, int(rw_row["codice_investimento"]))
        ws6.write(r_idx, 3, str(rw_row["codice_stato_estero"]))
        ws6.write(r_idx, 4, _safe_num(rw_row["valore_finale"]), f_currency)
        ws6.write(r_idx, 5, _safe_num(rw_row["ivafe_dovuta"]), f_currency)
        ws6.write(r_idx, 6, str(rw_row["monitoraggio_solo"]))
    ws6.autofit()

    # ── SHEET 7: SUCCESSIONE & ASSE EREDITARIO ───────────────────
    ws7 = workbook.add_worksheet("7_Pianificazione_Successoria")
    ws7.write("A1", "MAPPATURA ASSE EREDITARIO & QUOTE DI LEGITTIMA (C.C.)", f_title)

    headers7 = ["Soggetto Erede", "Valore Quota Spettante (€)", "Franchigia di Legge (€)", "Base Imponibile Netta (€)", "Aliquota Imposta", "Imposta di Successione Dovuta (€)"]
    for c, h in enumerate(headers7):
        ws7.write(3, c, h, f_hdr_navy)

    for r_idx, t_row in enumerate(estate["tax_heirs"], start=4):
        ws7.write(r_idx, 0, str(t_row["erede"]))
        ws7.write(r_idx, 1, _safe_num(t_row["quota_valore"]), f_currency)
        ws7.write(r_idx, 2, _safe_num(t_row["franchigia"]), f_currency)
        ws7.write(r_idx, 3, _safe_num(t_row["base_imponibile"]), f_currency)
        ws7.write(r_idx, 4, str(t_row["aliquota"]))
        ws7.write(r_idx, 5, _safe_num(t_row["imposta_dovuta"]), f_currency)
    ws7.autofit()

    # ── SHEET 8: AI DIAGNOSTICS & REBALANCING ────────────────────
    ws8 = workbook.add_worksheet("8_AI_Diagnostics_Rebalance")
    ws8.write("A1", "DIAGNOSTICA AI & ORDINI DI RIBILANCIAMENTO ASSET ALLOCATION", f_title)

    ws8.write(3, 0, "Asset Class", f_hdr_emerald)
    ws8.write(3, 1, "Allocazione Attuale", f_hdr_emerald)
    ws8.write(3, 2, "Allocazione Target", f_hdr_emerald)
    ws8.write(3, 3, "Scostamento Drift", f_hdr_emerald)
    ws8.write(3, 4, "Azione Suggerita", f_hdr_emerald)
    ws8.write(3, 5, "Importo Operazione (€)", f_hdr_emerald)

    for r_idx, reb in enumerate(ai_diag["rebalance_orders"], start=4):
        ws8.write(r_idx, 0, str(reb["asset_class"]))
        ws8.write(r_idx, 1, str(reb["allocazione_attuale"]))
        ws8.write(r_idx, 2, str(reb["allocazione_target"]))
        ws8.write(r_idx, 3, str(reb["scostamento"]))
        ws8.write(r_idx, 4, str(reb["azione_suggerita"]))
        ws8.write(r_idx, 5, _safe_num(reb["importo_ribilanciamento"]), f_currency)
    ws8.autofit()

    workbook.close()
    output.seek(0)
    return output
