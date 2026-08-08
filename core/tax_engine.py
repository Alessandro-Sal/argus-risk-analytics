"""
ARGUS — Risk Analytics Platform
Core Module: Tax Optimization & Tax-Loss Harvesting Engine
Italian Fiscal Framework (TUIR Art. 67 - Regime Amministrato/Dichiarativo)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

TAX_RATES = {
    "Government Bond": 0.125,
    "BTP": 0.125,
    "BOT": 0.125,
    "Treasury": 0.125,
    "Equity": 0.26,
    "ETF": 0.26,
    "Crypto": 0.26,
    "Corporate Bond": 0.26,
    "Default": 0.26,
}

def get_asset_tax_rate(asset_class: str, ticker: str = "") -> float:
    """Returns applicable tax rate (12.5% for government bonds, 26% for equities/ETFs/crypto)."""
    if not asset_class:
        asset_class = ""
    ac_lower = str(asset_class).lower()
    t_upper = str(ticker).upper()
    
    if "gov" in ac_lower or "btp" in ac_lower or "bot" in ac_lower or "treasury" in ac_lower or "stato" in ac_lower or "BTP" in t_upper or "BOT" in t_upper:
        return 0.125
    return 0.26

def is_etf(asset_class: str, ticker: str = "") -> bool:
    """Returns True if asset is an ETF (Reddito di Capitale in Italy)."""
    ac_lower = str(asset_class).lower()
    t_upper = str(ticker).upper()
    return "etf" in ac_lower or "etf" in t_upper or t_upper in ["CSPX", "VWCE", "IEMG", "AGGH", "EIMI", "MEUD", "XEON"]

def compute_tax_and_harvesting(
    results: Dict[str, Any],
    db_engine = None,
    tax_year: int = None
) -> Dict[str, Any]:
    """
    Computes overall and yearly tax liabilities on realized capital gains and identifies Tax-Loss Harvesting opportunities.
    
    Italian Tax Regulations (TUIR Art. 67):
      - ETF Gains = Redditi di Capitale (Taxed at 26%, CANNOT be offset by past capital losses).
      - Stock/Bond Gains = Redditi Diversi (Taxed at 26% / 12.5%, CAN be offset by past capital losses).
      - ETF Losses & Stock Losses = Capital Losses (Zainetto Fiscale, valid 4 years).
    """
    pos = results.get("positions", pd.DataFrame())
    
    # 1. Open positions analysis & Tax-Loss Harvesting
    tot_gain_diversi, tot_gain_etf, tot_loss, tot_tax_due = 0.0, 0.0, 0.0, 0.0
    harvest_rows = []

    if not pos.empty:
        for _, row in pos.iterrows():
            ticker = row.get("ticker", "")
            ac = row.get("asset_class", "")
            pnl_unrealized = float(row.get("pnl_unrealized", row.get("unrealized_pnl", 0.0)) or 0.0)
            pnl_realized = float(row.get("pnl_realized", row.get("realized_pnl", 0.0)) or 0.0)
            
            rate = get_asset_tax_rate(ac, ticker)
            etf_flag = is_etf(ac, ticker)

            if pnl_realized > 0:
                if etf_flag:
                    tot_gain_etf += pnl_realized
                else:
                    tot_gain_diversi += pnl_realized
            elif pnl_realized < 0:
                tot_loss += abs(pnl_realized)

            # Tax Loss Harvesting Candidate: Unrealized loss on non-ETF asset (Reddito Diverso)
            if pnl_unrealized < 0 and not etf_flag:
                harvest_rows.append({
                    "ticker": ticker,
                    "asset_class": ac,
                    "pnl_unrealized": round(pnl_unrealized, 2),
                    "potential_tax_saving_eur": round(abs(pnl_unrealized) * rate, 2),
                    "tax_rate_pct": f"{rate * 100:.1f}%",
                    "qualifying_type": "Redditi Diversi (Compensabile)"
                })

    df_harvest = pd.DataFrame(harvest_rows)
    if not df_harvest.empty:
        df_harvest = df_harvest.sort_values(by="potential_tax_saving_eur", ascending=False)

    # Offset rules: Minusvalenze can ONLY offset Redditi Diversi (stocks/bonds), NOT ETF gains!
    net_diversi = tot_gain_diversi - tot_loss
    tax_due_diversi = max(0.0, net_diversi * 0.26) if net_diversi > 0 else 0.0
    tax_due_etf = tot_gain_etf * 0.26
    
    total_tax_due = tax_due_diversi + tax_due_etf
    tax_credit = abs(net_diversi) if net_diversi < 0 else 0.0
    potential_savings = float(df_harvest["potential_tax_saving_eur"].sum()) if not df_harvest.empty else 0.0

    summary = {
        "total_realized_gain_diversi_eur": round(tot_gain_diversi, 2),
        "total_realized_gain_etf_eur": round(tot_gain_etf, 2),
        "total_realized_gain_eur": round(tot_gain_diversi + tot_gain_etf, 2),
        "total_realized_loss_eur": round(tot_loss, 2),
        "net_realized_pnl_eur": round(tot_gain_diversi + tot_gain_etf - tot_loss, 2),
        "estimated_tax_due_eur": round(total_tax_due, 2),
        "tax_credit_zainetto_eur": round(tax_credit, 2),
        "potential_tax_savings_eur": round(potential_savings, 2)
    }

    # 2. Yearly Tax Breakdown (Cronistoria Fiscale per Anno Solare con Regola ETF)
    df_yearly = pd.DataFrame()
    if db_engine is not None:
        try:
            query = """
                SELECT t.tx_id, t.tx_date, t.tx_type, t.quantity, t.price, t.currency, a.ticker, a.asset_class
                FROM transactions t
                JOIN assets a ON t.asset_id = a.asset_id
                ORDER BY t.tx_date ASC
            """
            df_tx = pd.read_sql(query, db_engine)
            if not df_tx.empty:
                df_tx['tx_date'] = pd.to_datetime(df_tx['tx_date'])
                df_tx['year'] = df_tx['tx_date'].dt.year

                yearly_stats = {}
                for ticker, grp in df_tx.groupby('ticker'):
                    queue = []
                    for _, row in grp.iterrows():
                        txtype = str(row['tx_type']).lower().strip()
                        qty = float(row['quantity'])
                        price = float(row['price'])
                        yr = int(row['year'])
                        ac = str(row['asset_class'])
                        
                        if yr not in yearly_stats:
                            yearly_stats[yr] = {'gains_diversi': 0.0, 'gains_etf': 0.0, 'losses': 0.0, 'dividends': 0.0}
                            
                        rate = get_asset_tax_rate(ac, ticker)
                        etf_flag = is_etf(ac, ticker)
                        
                        if txtype == 'buy':
                            queue.append([qty, price])
                        elif txtype == 'sell':
                            qty_to_sell = qty
                            while qty_to_sell > 1e-9 and queue:
                                lot_qty, lot_price = queue[0]
                                if lot_qty <= qty_to_sell + 1e-9:
                                    pnl = lot_qty * (price - lot_price)
                                    qty_to_sell -= lot_qty
                                    queue.pop(0)
                                else:
                                    pnl = qty_to_sell * (price - lot_price)
                                    queue[0][0] -= qty_to_sell
                                    qty_to_sell = 0.0
                                
                                if pnl > 0:
                                    if etf_flag:
                                        yearly_stats[yr]['gains_etf'] += pnl
                                    else:
                                        yearly_stats[yr]['gains_diversi'] += pnl
                                else:
                                    yearly_stats[yr]['losses'] += abs(pnl)
                        elif txtype == 'dividend':
                            yearly_stats[yr]['dividends'] += price

                y_rows = []
                for yr, s in sorted(yearly_stats.items()):
                    net_diversi = s['gains_diversi'] - s['losses']
                    tax_diversi = max(0.0, net_diversi * 0.26) if net_diversi > 0 else 0.0
                    tax_etf = s['gains_etf'] * 0.26
                    tax_total = tax_diversi + tax_etf
                    zainetto = abs(net_diversi) if net_diversi < 0 else 0.0
                    
                    y_rows.append({
                        "year": yr,
                        "realized_gain_diversi_eur": round(s['gains_diversi'], 2),
                        "realized_gain_etf_eur": round(s['gains_etf'], 2),
                        "realized_gain_eur": round(s['gains_diversi'] + s['gains_etf'], 2),
                        "realized_loss_eur": round(s['losses'], 2),
                        "net_pnl_eur": round(s['gains_diversi'] + s['gains_etf'] - s['losses'], 2),
                        "dividends_eur": round(s['dividends'], 2),
                        "estimated_tax_due_eur": round(tax_total, 2),
                        "estimated_tax_eur": round(tax_total, 2),
                        "tax_credit_zainetto_eur": round(zainetto, 2)
                    })
                df_yearly = pd.DataFrame(y_rows)
        except Exception:
            df_yearly = pd.DataFrame()

    # Filter summary by specific tax_year if requested
    if tax_year is not None and not df_yearly.empty and tax_year in df_yearly["year"].values:
        yr_row = df_yearly[df_yearly["year"] == tax_year].iloc[0]
        summary = {
            "total_realized_gain_diversi_eur": float(yr_row["realized_gain_diversi_eur"]),
            "total_realized_gain_etf_eur": float(yr_row["realized_gain_etf_eur"]),
            "total_realized_gain_eur": float(yr_row["realized_gain_eur"]),
            "total_realized_loss_eur": float(yr_row["realized_loss_eur"]),
            "net_realized_pnl_eur": float(yr_row["net_pnl_eur"]),
            "estimated_tax_due_eur": float(yr_row["estimated_tax_due_eur"]),
            "tax_credit_zainetto_eur": float(yr_row["tax_credit_zainetto_eur"]),
            "potential_tax_savings_eur": round(potential_savings, 2)
        }

    return {
        "summary": summary,
        "harvesting_opportunities": df_harvest,
        "harvesting_candidates": df_harvest,
        "yearly_breakdown": df_yearly,
        "tax_by_year": df_yearly
    }
