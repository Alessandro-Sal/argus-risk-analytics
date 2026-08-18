import os
import pandas as pd
from sqlalchemy import create_engine, text
import xlsxwriter
from datetime import datetime

EXPORT_DIR = "exports"

def generate_what_if_model():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    file_path = os.path.join(EXPORT_DIR, "WhatIf_Model.xlsx")
    
    from dotenv import load_dotenv
    load_dotenv()
    db_pass = os.getenv("DB_PASS", "")
    print("Connessione al database...")
    engine = create_engine(f"mysql+pymysql://root:{db_pass}@localhost:3306/investment_risk_bi")
    
    # 1. Trova l'ultimo snapshot_id
    with engine.connect() as conn:
        res = conn.execute(text("SELECT snapshot_id, run_id FROM portfolio_snapshots ORDER BY calc_date DESC LIMIT 1")).fetchone()
        if not res:
            print("Nessun portafoglio o snapshot trovato nel database.")
            return
        
        snapshot_id = res[0]
        run_id = res[1]
        
    print(f"Esportazione posizioni per la run: {run_id}")
    
    # 2. Estrai le posizioni
    query = f"""
    SELECT p.ticker, p.asset_class, a.gics_sector, p.qty_net, p.avg_cost, p.last_price, p.current_value, p.weight_pct
    FROM snapshot_positions p
    LEFT JOIN assets a ON p.ticker = a.ticker
    WHERE p.snapshot_id = {snapshot_id}
    ORDER BY p.current_value DESC
    """
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("Nessuna posizione attiva trovata.")
        return
        
    # 3. Creazione Excel
    workbook = xlsxwriter.Workbook(file_path)
    
    # Formati
    format_header = workbook.add_format({'bold': True, 'bg_color': '#1f497d', 'font_color': 'white', 'border': 1})
    format_currency = workbook.add_format({'num_format': '€ #,##0.00'})
    format_pct = workbook.add_format({'num_format': '0.00%'})
    format_input = workbook.add_format({'bg_color': '#ffffcc', 'border': 1, 'num_format': '0.00%'})
    
    # --- FOGLIO 1: POSIZIONI REALI ---
    ws_data = workbook.add_worksheet("Dati Portafoglio")
    
    # Headers
    headers = ["Ticker", "Asset Class", "Settore", "Quantità", "Prezzo Medio", "Ultimo Prezzo", "Valore Attuale", "Peso"]
    for col_num, data in enumerate(headers):
        ws_data.write(0, col_num, data, format_header)
        
    # Dati
    for row_num, row_data in df.iterrows():
        ws_data.write(row_num + 1, 0, row_data['ticker'])
        ws_data.write(row_num + 1, 1, row_data['asset_class'])
        ws_data.write(row_num + 1, 2, row_data['gics_sector'])
        ws_data.write(row_num + 1, 3, row_data['qty_net'])
        ws_data.write(row_num + 1, 4, row_data['avg_cost'], format_currency)
        ws_data.write(row_num + 1, 5, row_data['last_price'], format_currency)
        ws_data.write(row_num + 1, 6, row_data['current_value'], format_currency)
        ws_data.write(row_num + 1, 7, row_data['weight_pct'], format_pct)
        
    ws_data.autofit()
    
    # --- FOGLIO 2: SIMULATORE WHAT-IF ---
    ws_sim = workbook.add_worksheet("Simulatore What-If")
    
    # Titoli
    ws_sim.write("A1", "Simulatore di Scenari (Stress Test)", workbook.add_format({'bold': True, 'font_size': 14}))
    ws_sim.write("A2", "Inserisci una percentuale di shock (es. -10% o 5%) nelle celle gialle per vedere l'impatto sul portafoglio.")
    
    # Headers Simulatore
    sim_headers = ["Ticker", "Settore", "Valore Originale", "Shock % (Input)", "Valore Simulato", "Impatto (€)"]
    for col_num, data in enumerate(sim_headers):
        ws_sim.write(4, col_num, data, format_header)
        
    totale_originale = 0
    row_offset = 5
    
    for i, row_data in df.iterrows():
        row_idx = i + row_offset
        ws_sim.write(row_idx, 0, row_data['ticker'])
        ws_sim.write(row_idx, 1, row_data['gics_sector'])
        ws_sim.write(row_idx, 2, row_data['current_value'], format_currency)
        
        # Cella input (gialla) - Valore di default 0%
        ws_sim.write(row_idx, 3, 0.0, format_input)
        
        # Valore simulato = Valore Originale * (1 + Shock)
        ws_sim.write_formula(row_idx, 4, f"=C{row_idx+1}*(1+D{row_idx+1})", format_currency)
        
        # Impatto = Valore Simulato - Valore Originale
        ws_sim.write_formula(row_idx, 5, f"=E{row_idx+1}-C{row_idx+1}", format_currency)
        
        totale_originale += row_data['current_value']
        
    last_row = row_offset + len(df)
    
    # Totali
    ws_sim.write(last_row + 1, 1, "TOTALE", format_header)
    ws_sim.write_formula(last_row + 1, 2, f"=SUM(C6:C{last_row})", format_currency)
    ws_sim.write_formula(last_row + 1, 4, f"=SUM(E6:E{last_row})", format_currency)
    ws_sim.write_formula(last_row + 1, 5, f"=SUM(F6:F{last_row})", format_currency)
    
    # Performance Simulata Totale
    ws_sim.write(last_row + 3, 1, "Rendimento Simulata", format_header)
    ws_sim.write_formula(last_row + 3, 2, f"=F{last_row+2}/C{last_row+2}", format_pct)
    
    ws_sim.autofit()
    
    workbook.close()
    print(f"Modello generato con successo: {file_path}")

if __name__ == "__main__":
    generate_what_if_model()
