import io
import math
import numpy as np
import pandas as pd
import xlsxwriter

def _safe_num(val, default=0.0) -> float:
    """Safe conversion to float preventing NaN or Inf values from crashing Excel writers."""
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
    Generates a structured, styled What-If Investment Portfolio Simulator Excel file in memory.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of active portfolio positions containing tickers, asset classes, sectors, values, etc.
        
    Returns
    -------
    io.BytesIO
        Memory stream containing the generated XLSX file.
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'nan_inf_to_errors': True})
    
    # Design Styles & Formats
    format_header = workbook.add_format({
        'bold': True, 
        'bg_color': '#1f497d', 
        'font_color': 'white', 
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    format_currency = workbook.add_format({'num_format': '€ #,##0.00'})
    format_pct = workbook.add_format({'num_format': '0.00%'})
    format_input = workbook.add_format({
        'bg_color': '#ffffcc', 
        'border': 1, 
        'num_format': '0.00%',
        'align': 'right'
    })
    format_title = workbook.add_format({
        'bold': True, 
        'font_size': 14, 
        'font_color': '#1f497d'
    })
    format_bold = workbook.add_format({'bold': True})
    format_bold_currency = workbook.add_format({'bold': True, 'num_format': '€ #,##0.00'})
    format_bold_pct = workbook.add_format({'bold': True, 'num_format': '0.00%'})
    
    # ─── SHEET 1: PORTFOLIO DATA ──────────────────────────────────
    ws_data = workbook.add_worksheet("Dati Portafoglio")
    
    headers = ["Ticker", "Asset Class", "Settore", "Quantità", "Prezzo Medio", "Ultimo Prezzo", "Valore Attuale", "Peso", "Yield on Cost %", "Giorni Liquidazione (ADV)"]
    for col_num, header in enumerate(headers):
        ws_data.write(0, col_num, header, format_header)
        
    for row_num, (_, row_data) in enumerate(df.iterrows()):
        r = row_num + 1
        ws_data.write(r, 0, str(row_data.get('ticker', '')))
        ws_data.write(r, 1, str(row_data.get('asset_class', 'None') or 'None'))
        ws_data.write(r, 2, str(row_data.get('gics_sector', 'None') or 'None'))
        ws_data.write(r, 3, _safe_num(row_data.get('qty_net', 0.0)))
        ws_data.write(r, 4, _safe_num(row_data.get('avg_cost', 0.0)), format_currency)
        ws_data.write(r, 5, _safe_num(row_data.get('last_price', 0.0)), format_currency)
        ws_data.write(r, 6, _safe_num(row_data.get('current_value', 0.0)), format_currency)
        
        # Division by 100 to show percentage correctly in Excel format (0.00%)
        weight = _safe_num(row_data.get('weight_pct', 0.0)) / 100.0
        ws_data.write(r, 7, weight, format_pct)
        
        yoc = _safe_num(row_data.get('yield_on_cost_pct', 0.0)) / 100.0
        ws_data.write(r, 8, yoc, format_pct)
        ws_data.write(r, 9, _safe_num(row_data.get('days_to_liquidate', 1.0)))
        
    ws_data.autofit()

    
    # ─── SHEET 2: WHAT-IF SIMULATOR ──────────────────────────────────
    ws_sim = workbook.add_worksheet("Simulatore What-If")
    
    ws_sim.write("A1", "Simulatore di Scenari (Stress Test)", format_title)
    ws_sim.write("A2", "Inserisci una percentuale di shock (es. -10% o 5%) nelle celle gialle per vedere l'impatto sul portafoglio.")
    
    sim_headers = ["Ticker", "Settore", "Valore Originale", "Shock % (Input)", "Valore Simulato", "Impatto (€)"]
    for col_num, header in enumerate(sim_headers):
        ws_sim.write(4, col_num, header, format_header)
        
    row_offset = 5
    num_rows = len(df)
    
    for i, (_, row_data) in enumerate(df.iterrows()):
        r = i + row_offset
        ws_sim.write(r, 0, str(row_data.get('ticker', '')))
        ws_sim.write(r, 1, str(row_data.get('gics_sector', 'None') or 'None'))
        ws_sim.write(r, 2, _safe_num(row_data.get('current_value', 0.0)), format_currency)
        
        # Cella input (gialla) - Valore di default 0%
        ws_sim.write(r, 3, 0.0, format_input)
        
        # Valore simulato = Valore Originale * (1 + Shock)
        excel_row = r + 1
        ws_sim.write_formula(r, 4, f"=C{excel_row}*(1+D{excel_row})", format_currency)
        
        # Impatto = Valore Simulato - Valore Originale
        ws_sim.write_formula(r, 5, f"=E{excel_row}-C{excel_row}", format_currency)
        
    last_row = row_offset + num_rows
    
    # Totals Row
    ws_sim.write(last_row, 1, "TOTALE", format_bold)
    ws_sim.write_formula(last_row, 2, f"=SUM(C6:C{last_row})", format_bold_currency)
    ws_sim.write_formula(last_row, 4, f"=SUM(E6:E{last_row})", format_bold_currency)
    ws_sim.write_formula(last_row, 5, f"=SUM(F6:F{last_row})", format_bold_currency)
    
    # Total Simulated Return Row
    ws_sim.write(last_row + 2, 1, "Rendimento Simulato", format_bold)
    # Total Impact / Total Original
    ws_sim.write_formula(last_row + 2, 2, f"=F{last_row+1}/C{last_row+1}", format_bold_pct)
    
    ws_sim.autofit()
    workbook.close()
    
    output.seek(0)
    return output
