"""
ARGUS — Financial Modeling & Dynamic Excel Generator
Core Module: Interactive What-If Portfolio Simulator with Native ListObject Tables
Generates fully recalculating .xlsx models with active formulas, data bars, and dynamic totals.
"""

import io
import math
import numpy as np
import pandas as pd
import xlsxwriter
from typing import Optional


def _safe_num(val, default=0.0) -> float:
    """Conversione numerica sicura che previene crash su NaN o Inf nei writer Excel."""
    if val is None or pd.isna(val):
        return default
    try:
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval) or np.isnan(fval) or np.isinf(fval):
            return default
        return fval
    except Exception:
        return default


def generate_excel_in_memory(df: pd.DataFrame) -> io.BytesIO:
    """
    Genera un modello interattivo What-If e di allocazione portafoglio in memoria.
    Include tabelle native Excel (ListObject), formule dinamiche di ricalcolo,
    celle di input per scenari di stress e formattazione condizionale a barre dati.
    """
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        df = df[(df.get("qty_net", 1) > 1e-6) & (df.get("current_value", 1) > 1e-6)].copy()
    else:
        df = pd.DataFrame([
            {"ticker": "AAPL", "asset_class": "Equity", "gics_sector": "Technology", "qty_net": 10.0, "avg_cost": 150.0, "last_price": 180.0, "current_value": 1800.0, "weight_pct": 60.0},
            {"ticker": "MSFT", "asset_class": "Equity", "gics_sector": "Technology", "qty_net": 5.0, "avg_cost": 300.0, "last_price": 240.0, "current_value": 1200.0, "weight_pct": 40.0}
        ])

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'nan_inf_to_errors': True})

    # ── FORMATI GRAFICI OBSIDIAN SOVEREIGN ──────────────────────
    f_title = workbook.add_format({'bold': True, 'font_size': 13, 'font_color': '#0F172A'})
    f_subtitle = workbook.add_format({'font_size': 9, 'font_color': '#64748B'})
    f_kpi_lbl = workbook.add_format({'bold': True, 'font_size': 8, 'font_color': '#64748B', 'bg_color': '#F8FAFC', 'border': 1, 'align': 'center'})
    f_kpi_val = workbook.add_format({'bold': True, 'font_size': 11, 'num_format': '€ #,##0.00', 'bg_color': '#F8FAFC', 'border': 1, 'align': 'center', 'font_color': '#0F172A'})
    f_currency = workbook.add_format({'num_format': '€ #,##0.00'})
    f_bold_currency = workbook.add_format({'bold': True, 'num_format': '€ #,##0.00'})
    f_pct = workbook.add_format({'num_format': '0.00%'})
    f_bold_pct = workbook.add_format({'bold': True, 'num_format': '0.00%'})
    f_bold = workbook.add_format({'bold': True})
    f_input = workbook.add_format({'bg_color': '#FEF3C7', 'border': 1, 'num_format': '0.00%', 'align': 'right'})

    # ── FOGLIO 1: DATI PORTAFOGLIO & ALLOCAZIONE NATIVA ─────────
    ws_data = workbook.add_worksheet("Dati Portafoglio")

    ws_data.write("A1", "ARGUS — REGISTRO POSIZIONI & ALLOCAZIONE ATTIVA", f_title)
    ws_data.write("A2", "Tabella nativa con calcolo dinamico di controvalori e pesi percentuali.", f_subtitle)

    start_row = 3
    data_rows = []
    for _, row in df.iterrows():
        tk = str(row.get('ticker', ''))
        ac = str(row.get('asset_class', 'Equity') or 'Equity')
        sec = str(row.get('gics_sector', 'Diversified') or 'Diversified')
        qty = _safe_num(row.get('qty_net', 0.0))
        cost = _safe_num(row.get('avg_cost', 0.0))
        px = _safe_num(row.get('last_price', 0.0))
        cv = _safe_num(row.get('current_value', 0.0))
        wp = _safe_num(row.get('weight_pct', 0.0)) / 100.0
        yoc = _safe_num(row.get('yield_on_cost_pct', 0.0)) / 100.0
        dtl = _safe_num(row.get('days_to_liquidate', 1.0))
        data_rows.append([tk, ac, sec, qty, cost, px, cv, wp, yoc, dtl])

    columns_spec_data = [
        {'header': 'Ticker'},
        {'header': 'Asset Class'},
        {'header': 'Settore'},
        {'header': 'Quantità', 'format': workbook.add_format({'num_format': '#,##0'})},
        {'header': 'Prezzo Medio', 'format': f_currency},
        {'header': 'Ultimo Prezzo', 'format': f_currency},
        {'header': 'Valore Attuale', 'format': f_currency},
        {'header': 'Peso', 'format': f_pct},
        {'header': 'Yield on Cost %', 'format': f_pct},
        {'header': 'Giorni Liquidazione (ADV)', 'format': workbook.add_format({'num_format': '0.0'})}
    ]

    ws_data.add_table(start_row, 0, start_row + len(data_rows), len(columns_spec_data) - 1, {
        'name': 'TablePositions',
        'data': data_rows,
        'columns': columns_spec_data,
        'style': 'TableStyleMedium9',
        'total_row': True
    })

    # Data Bar su colonna Peso
    last_row_data = start_row + len(data_rows)
    ws_data.conditional_format(start_row + 1, 7, last_row_data, 7, {
        'type': 'data_bar',
        'bar_color': '#38BDF8',
        'bar_solid': True
    })
    ws_data.autofit()

    # ── FOGLIO 2: SIMULATORE WHAT-IF DINAMICO ───────────────────
    ws_sim = workbook.add_worksheet("Simulatore What-If")

    ws_sim.write("A1", "ARGUS — SIMULATORE DI SCENARI & WHAT-IF DINAMICO", f_title)
    ws_sim.write("A2", "Inserisci una percentuale di shock (es. -10% o +5%) nelle celle evidenziate per ricalcolare il modello in tempo reale.", f_subtitle)

    # Top KPI Banner dinamico
    ws_sim.write("A4", "VALORE ATTUALE", f_kpi_lbl)
    ws_sim.write_formula("A5", "=SUM(TableWhatIf[Valore Originale])", f_kpi_val)

    ws_sim.write("C4", "VALORE SIMULATO", f_kpi_lbl)
    ws_sim.write_formula("C5", "=SUM(TableWhatIf[Valore Simulato])", f_kpi_val)

    ws_sim.write("E4", "IMPATTO TOTALE (€)", f_kpi_lbl)
    ws_sim.write_formula("E5", "=SUM(TableWhatIf[Impatto (€)])", f_kpi_val)

    ws_sim.write("G4", "RENDIMENTO SHOCK %", f_kpi_lbl)
    ws_sim.write_formula("G5", "=IF(A5>0, E5/A5, 0)", workbook.add_format({'bold': True, 'font_size': 11, 'num_format': '0.00%', 'bg_color': '#F8FAFC', 'border': 1, 'align': 'center'}))

    sim_start_row = 7
    sim_rows = []
    for _, row in df.iterrows():
        tk = str(row.get('ticker', ''))
        sec = str(row.get('gics_sector', 'Diversified') or 'Diversified')
        cv = _safe_num(row.get('current_value', 0.0))
        # [Ticker, Settore, Valore Originale, Shock % Input, Valore Simulato placeholder, Impatto placeholder]
        sim_rows.append([tk, sec, cv, 0.0, cv, 0.0])

    num_sim_rows = len(sim_rows)
    columns_spec_sim = [
        {'header': 'Ticker'},
        {'header': 'Settore'},
        {'header': 'Valore Originale', 'format': f_currency},
        {'header': 'Shock % (Input)', 'format': f_input},
        {'header': 'Valore Simulato', 'format': f_currency},
        {'header': 'Impatto (€)', 'format': f_currency}
    ]

    ws_sim.add_table(sim_start_row, 0, sim_start_row + num_sim_rows, len(columns_spec_sim) - 1, {
        'name': 'TableWhatIf',
        'data': sim_rows,
        'columns': columns_spec_sim,
        'style': 'TableStyleMedium2',
        'total_row': True
    })

    # Iniezione formule dinamiche riga per riga
    for i in range(num_sim_rows):
        r = sim_start_row + 1 + i
        excel_row = r + 1  # 1-indexed per Excel
        # Valore Simulato = Valore Originale * (1 + Shock)
        ws_sim.write_formula(r, 4, f"=C{excel_row}*(1+D{excel_row})", f_currency)
        # Impatto = Valore Simulato - Valore Originale
        ws_sim.write_formula(r, 5, f"=E{excel_row}-C{excel_row}", f_currency)

    # Totale riga di chiusura della tabella
    tot_row_idx = sim_start_row + num_sim_rows + 1
    ws_sim.write(tot_row_idx, 1, "TOTALE", f_bold)
    ws_sim.write_formula(tot_row_idx, 2, f"=SUM(C{sim_start_row+2}:C{tot_row_idx})", f_bold_currency)
    ws_sim.write_formula(tot_row_idx, 4, f"=SUM(E{sim_start_row+2}:E{tot_row_idx})", f_bold_currency)
    ws_sim.write_formula(tot_row_idx, 5, f"=SUM(F{sim_start_row+2}:F{tot_row_idx})", f_bold_currency)

    # Formattazione condizionale su Impatto (€)
    ws_sim.conditional_format(sim_start_row + 1, 5, sim_start_row + num_sim_rows, 5, {
        'type': 'cell',
        'criteria': '<',
        'value': 0,
        'format': workbook.add_format({'bg_color': '#FEE2E2', 'font_color': '#991B1B'})
    })

    ws_sim.autofit()
    workbook.close()
    output.seek(0)
    return output
