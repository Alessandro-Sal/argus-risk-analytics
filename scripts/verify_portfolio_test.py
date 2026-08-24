"""
ARGUS Verification & Precision Audit Script
Senior Functional Analyst & QA Calculations Specialist
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.validator import validate_csv
from core.fetcher import fetch_and_store
from core.risk_engine import compute_risk
from core.tax_engine import compute_tax_and_harvesting
from core.corporate_actions import adjust_transactions_for_splits

def run_verification():
    csv_path = "data/test_portfolio.csv"
    print("=" * 80)
    print("1. INGESTION & DATA VALIDATION AUDIT")
    print("=" * 80)
    df_raw = pd.read_csv(csv_path)
    print(f"File caricato: {csv_path} | Totale righe grezze: {len(df_raw)}")
    
    df_clean, val_report = validate_csv(df_raw)
    print(f"Validazione superata: {val_report['stats']['is_valid']}")
    print(f"Errori bloccanti: {len(val_report['errors'])}")
    print(f"Warning: {len(val_report['warnings'])}")
    for w in val_report['warnings']:
        print(f"  [WARN] {w}")
    print(f"Fixes applicati: {len(val_report['fixes'])}")
    for f in val_report['fixes']:
        print(f"  [FIX] {f}")
    print(f"Asset Classes rilevate: {val_report['stats']['asset_classes']}")
    print(f"Tickers ({len(val_report['stats']['tickers'])}): {val_report['stats']['tickers']}")

    print("\n" + "=" * 80)
    print("2. INDEPENDENT FIFO & INVENTORY CALCULATION (MANUAL MODEL)")
    print("=" * 80)
    
    # Check corporate actions
    df_adj, split_audit = adjust_transactions_for_splits(df_clean, auto_fetch=True)
    print(f"Rettifiche Stock Splits applicate da corporate actions engine ({len(split_audit)}):")
    for sp in split_audit:
        print(f"  [SPLIT] {sp.get('ticker')}: ratio {sp.get('split_ratio', sp.get('ratio'))} in data {sp.get('split_date', sp.get('date'))} (operazioni ante-split rettificate: {sp.get('affected_transactions_count', sp.get('affected_transactions'))})")
    
    # Manual FIFO engine per ticker (in local currency)
    manual_inventory = {}
    for ticker, grp in df_adj.groupby("ticker"):
        grp_sorted = grp.sort_values(["tx_date"]).reset_index(drop=True)
        lots = [] # [qty, price, currency]
        realized_pnl_local = 0.0
        dividends_local = 0.0
        curr = grp_sorted.iloc[0]["currency"]
        asset_class = grp_sorted.iloc[0]["asset_class"]
        
        for _, row in grp_sorted.iterrows():
            ttype = row["tx_type"].lower().strip()
            qty = float(row["quantity"])
            price = float(row["price"])
            
            if ttype == "buy":
                lots.append([qty, price])
            elif ttype == "sell":
                rem_sell = qty
                while rem_sell > 1e-9 and lots:
                    l_qty, l_price = lots[0]
                    if l_qty <= rem_sell + 1e-9:
                        realized_pnl_local += l_qty * (price - l_price)
                        rem_sell -= l_qty
                        lots.pop(0)
                    else:
                        realized_pnl_local += rem_sell * (price - l_price)
                        lots[0][0] -= rem_sell
                        rem_sell = 0.0
            elif ttype == "dividend":
                dividends_local += price
                
        tot_qty = sum(l[0] for l in lots)
        tot_cost = sum(l[0] * l[1] for l in lots)
        avg_cost_local = (tot_cost / tot_qty) if tot_qty > 1e-9 else 0.0
        
        manual_inventory[ticker] = {
            "ticker": ticker,
            "asset_class": asset_class,
            "currency": curr,
            "qty_net": round(tot_qty, 6),
            "avg_cost_local": round(avg_cost_local, 4),
            "cost_basis_local": round(tot_cost, 2),
            "realized_pnl_local": round(realized_pnl_local, 2),
            "dividends_local": round(dividends_local, 2),
        }

    df_manual = pd.DataFrame(list(manual_inventory.values())).sort_values("ticker").reset_index(drop=True)
    print("\n[MANUAL MODEL] Inventario Posizioni e Risultati FIFO:")
    print(df_manual.to_string(index=False))

    print("\n" + "=" * 80)
    print("3. ESECUZIONE PIPELINE QUANTITATIVA ARGUS (ENGINE RUN)")
    print("=" * 80)
    
    # Run fetch_and_store in offline/in-memory mode
    fetch_report, df_tx_res, df_prices_res = fetch_and_store(df_clean, engine=None, portfolio_id=1, benchmark_ticker="SPY")
    print(f"Prezzi scaricati con successo per {len(fetch_report['success'])} strumenti.")
    if fetch_report['errors']:
        print(f"Errori fetch: {fetch_report['errors']}")
        
    # Run compute_risk
    results = compute_risk(
        portfolio_id=1,
        engine=None,
        benchmark_ticker="SPY",
        df_tx=df_tx_res,
        df_prices=df_prices_res,
        base_currency="EUR"
    )
    
    df_pos_argus = results["positions"].sort_values("ticker").reset_index(drop=True)
    m = results["metrics"]
    ret = m["returns"]
    mk = m["market_risk"]
    con = m["concentration"]
    
    print("\n" + "=" * 80)
    print("4. COMPARAZIONE SIDE-BY-SIDE: MODELLO MANUALE vs ARGUS ENGINE")
    print("=" * 80)
    
    comp_rows = []
    for _, man_row in df_manual.iterrows():
        tk = man_row["ticker"]
        arg_row = df_pos_argus[df_pos_argus["ticker"] == tk]
        if not arg_row.empty:
            a_r = arg_row.iloc[0]
            qty_diff = man_row["qty_net"] - a_r["qty_net"]
            comp_rows.append({
                "Ticker": tk,
                "Valuta": man_row["currency"],
                "Qty Manuale": man_row["qty_net"],
                "Qty ARGUS": a_r["qty_net"],
                "Delta Qty": round(qty_diff, 6),
                "Avg Cost (EUR)": round(a_r["avg_cost"], 4),
                "Cost Basis (EUR)": round(a_r["cost_basis"], 2),
                "Last Price (EUR)": round(a_r["last_price"], 4),
                "Current Val (EUR)": round(a_r["current_value"], 2),
                "Unrealized PnL (EUR)": round(a_r["unrealized_pnl"], 2),
                "Realized PnL (EUR)": round(a_r["realized_pnl"], 2),
                "Dividends (EUR)": round(a_r["dividends_total"], 2),
                "Peso %": round(a_r["weight_pct"], 2),
                "Match Qty": "[OK]" if abs(qty_diff) < 1e-4 else "[MISMATCH]"
            })
            
    df_comp = pd.DataFrame(comp_rows)
    print(df_comp.to_string(index=False))

    print("\n" + "=" * 80)
    print("5. VERIFICA METRICHE AGGREGATE E DATA QUALITY GATES")
    print("=" * 80)
    
    print(f"Valore Totale Portafoglio:       {ret.get('portfolio_value', df_pos_argus['current_value'].sum()):,.2f} EUR")
    print(f"Base di Costo Totale:            {df_pos_argus['cost_basis'].sum():,.2f} EUR")
    print(f"PnL Latente Totale:              {df_pos_argus['unrealized_pnl'].sum():,.2f} EUR")
    print(f"PnL Realizzato Totale:           {df_pos_argus['realized_pnl'].sum():,.2f} EUR")
    print(f"Dividendi Incassati Totali:      {df_pos_argus['dividends_total'].sum():,.2f} EUR")
    print(f"Rendimento Totale:               {ret.get('total_return_pct'):.2f}%")
    print(f"CAGR:                            {ret.get('cagr_pct'):.2f}%")
    print(f"Volatilita Annualizzata:         {mk.get('volatility_annual_pct'):.2f}%")
    print(f"Sharpe Ratio:                    {ret.get('sharpe_ratio'):.4f}")
    print(f"Sortino Ratio:                   {ret.get('sortino_ratio'):.4f}")
    print(f"Max Drawdown:                    {mk.get('max_drawdown_pct'):.2f}%")
    print(f"VaR 95% (Storico):               {mk.get('var_95'):.2f}%")
    print(f"VaR 95% (Cornish-Fisher):        {mk.get('var_cf_95'):.2f}%")
    print(f"CVaR 95% (Expected Shortfall):   {mk.get('cvar_95'):.2f}%")
    print(f"Indice di Concentrazione HHI:    {con.get('hhi'):.2f}")
    print(f"Diversification Ratio:           {con.get('diversification_ratio', 0.0):.4f}")
    
    print("\nWarnings & Data Quality Alerts generati dal motore:")
    for w in results.get("warnings", []):
        print(f"  [ALERT] {w}")

    print("\n" + "=" * 80)
    print("6. VERIFICA FISCALE TUIR ART. 67 (TAX ENGINE AUDIT)")
    print("=" * 80)
    tax_res = compute_tax_and_harvesting(results)
    tax_sum = tax_res.get("summary", {})
    print(f"Plusvalenze Realizzate Redditi Diversi: {tax_sum.get('total_realized_gain_diversi_eur', 0.0):,.2f} EUR")
    print(f"Plusvalenze Realizzate ETF (Capitale):  {tax_sum.get('total_realized_gain_etf_eur', 0.0):,.2f} EUR")
    print(f"Minusvalenze Realizzate (Perdite):      {tax_sum.get('total_realized_loss_eur', 0.0):,.2f} EUR")
    print(f"Imposta Totale Stimata:                 {tax_sum.get('estimated_tax_due_eur', 0.0):,.2f} EUR")
    print(f"Credito d'Imposta Zainetto Fiscale:     {tax_sum.get('tax_credit_zainetto_eur', 0.0):,.2f} EUR")
    print(f"Potenziale Risparmio Tax-Loss Harvest:  {tax_sum.get('potential_tax_savings_eur', 0.0):,.2f} EUR")

if __name__ == "__main__":
    run_verification()
