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
                    "tax_rate_pct": round(rate * 100.0, 1),
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

    # 2. Yearly Tax Breakdown (Cronistoria Fiscale per Anno Solare con Regola ETF e Conversione FX)
    df_yearly = pd.DataFrame()
    df_tx = results.get("df_tx", pd.DataFrame())
    portfolio_id = results.get("portfolio_id")

    if (df_tx is None or df_tx.empty) and db_engine is not None and portfolio_id is not None:
        try:
            from sqlalchemy import text
            query = text("""
                SELECT t.tx_id, t.tx_date, t.tx_type, t.quantity, t.price, t.currency, a.ticker, a.asset_class
                FROM transactions t
                JOIN assets a ON t.asset_id = a.asset_id
                WHERE t.portfolio_id = :pid
                ORDER BY t.tx_date ASC
            """)
            with db_engine.connect() as conn:
                df_tx = pd.read_sql(query, conn, params={"pid": portfolio_id})
        except Exception:
            df_tx = pd.DataFrame()

    if df_tx is not None and not df_tx.empty:
        try:
            df_tx = df_tx.copy()
            df_tx['tx_date'] = pd.to_datetime(df_tx['tx_date'])
            df_tx['year'] = df_tx['tx_date'].dt.year

            # Mappa tassi di cambio storici da df_prices se disponibili
            df_prices = results.get("df_prices", pd.DataFrame())
            fx_dict = {}
            if not df_prices.empty and "ticker" in df_prices.columns and "close" in df_prices.columns:
                fx_tickers = [t for t in df_prices["ticker"].unique() if str(t).endswith("=X")]
                for fxt in fx_tickers:
                    sub = df_prices[df_prices["ticker"] == fxt].sort_values("price_date")
                    fx_dict[fxt] = pd.Series(sub["close"].values, index=pd.to_datetime(sub["price_date"]))

            yearly_stats = {}
            for ticker, grp in df_tx.groupby('ticker'):
                queue = []
                grp = grp.sort_values(["tx_date", "tx_id"] if "tx_id" in grp.columns else ["tx_date"])
                
                for _, row in grp.iterrows():
                    txtype = str(row['tx_type']).lower().strip()
                    qty = float(row['quantity'])
                    raw_price = float(row['price'])
                    yr = int(row['year'])
                    ac = str(row.get('asset_class', 'Stock'))
                    
                    # Conversione valuta transazione in EUR
                    tx_curr = str(row.get("currency", "EUR")).upper().strip()
                    fx_rate = 1.0
                    if tx_curr not in ["EUR", "", "NAN", "NONE"]:
                        fx_pair = f"{tx_curr}EUR=X"
                        if fx_pair in fx_dict:
                            try:
                                idx = fx_dict[fx_pair].index.get_indexer([row["tx_date"]], method='ffill')[0]
                                if idx >= 0:
                                    fx_rate = float(fx_dict[fx_pair].iloc[idx])
                            except Exception:
                                pass
                        elif tx_curr == "USD":
                            fx_rate = 0.92
                        elif tx_curr == "GBP":
                            fx_rate = 1.17
                        elif tx_curr == "CHF":
                            fx_rate = 1.05

                    price = raw_price * fx_rate
                    
                    if yr not in yearly_stats:
                        yearly_stats[yr] = {'gains_diversi': 0.0, 'gains_etf': 0.0, 'losses': 0.0, 'dividends': 0.0}
                        
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

            # Calcolo unificato anno per anno con deduzione FIFO delle minusvalenze pregresse (TUIR Art. 68 c. 5)
            y_rows = []
            buckets_tracking = []
            
            for yr, s in sorted(yearly_stats.items()):
                g_div = float(s['gains_diversi'])
                g_etf = float(s['gains_etf'])
                losses = float(s['losses'])
                net_diversi = g_div - losses
                
                prior_deducted = 0.0
                if net_diversi > 0:
                    excess_gain = net_diversi
                    for b in buckets_tracking:
                        if b["residual"] > 1e-6 and yr <= b["expiry_year"]:
                            offset_amt = min(excess_gain, b["residual"])
                            b["compensated"] += offset_amt
                            b["residual"] -= offset_amt
                            prior_deducted += offset_amt
                            excess_gain -= offset_amt
                            if excess_gain <= 1e-6:
                                break
                    taxable_diversi = excess_gain
                else:
                    net_loss = abs(net_diversi)
                    if net_loss > 1e-2:
                        buckets_tracking.append({
                            "origin_year": yr,
                            "expiry_year": yr + 4,
                            "initial": round(net_loss, 2),
                            "compensated": 0.0,
                            "residual": round(net_loss, 2)
                        })
                    taxable_diversi = 0.0

                tax_diversi = taxable_diversi * 0.26
                tax_etf = g_etf * 0.26
                tax_total = tax_diversi + tax_etf
                active_zainetto = sum(b["residual"] for b in buckets_tracking if yr <= b["expiry_year"])
                
                y_rows.append({
                    "year": yr,
                    "realized_gain_diversi_eur": round(g_div, 2),
                    "realized_gain_etf_eur": round(g_etf, 2),
                    "realized_gain_eur": round(g_div + g_etf, 2),
                    "realized_loss_eur": round(losses, 2),
                    "prior_minus_deducted_eur": round(prior_deducted, 2),
                    "taxable_base_eur": round(taxable_diversi, 2),
                    "net_pnl_eur": round(g_div + g_etf - losses, 2),
                    "dividends_eur": round(s['dividends'], 2),
                    "estimated_tax_due_eur": round(tax_total, 2),
                    "estimated_tax_eur": round(tax_total, 2),
                    "tax_credit_zainetto_eur": round(active_zainetto, 2)
                })
            df_yearly = pd.DataFrame(y_rows)
        except Exception:
            df_yearly = pd.DataFrame()

    # 3. Zainetto Fiscale Multianno & Scadenze Quadriennali (TUIR Art. 68 c. 5)
    df_zainetto_timeline = compute_zainetto_timeline(df_yearly)

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
    elif not df_yearly.empty:
        # Quando "Tutti gli Anni" è selezionato, somma le imposte effettive e mostra lo zainetto attivo corrente
        current_active_zainetto = float(df_zainetto_timeline["residual_active_eur"].sum()) if not df_zainetto_timeline.empty else 0.0
        summary = {
            "total_realized_gain_diversi_eur": round(float(df_yearly["realized_gain_diversi_eur"].sum()), 2),
            "total_realized_gain_etf_eur": round(float(df_yearly["realized_gain_etf_eur"].sum()), 2),
            "total_realized_gain_eur": round(float(df_yearly["realized_gain_eur"].sum()), 2),
            "total_realized_loss_eur": round(float(df_yearly["realized_loss_eur"].sum()), 2),
            "net_realized_pnl_eur": round(float(df_yearly["net_pnl_eur"].sum()), 2),
            "estimated_tax_due_eur": round(float(df_yearly["estimated_tax_due_eur"].sum()), 2),
            "tax_credit_zainetto_eur": round(current_active_zainetto, 2),
            "potential_tax_savings_eur": round(potential_savings, 2)
        }

    return {
        "summary": summary,
        "harvesting_opportunities": df_harvest,
        "harvesting_candidates": df_harvest,
        "yearly_breakdown": df_yearly,
        "tax_by_year": df_yearly,
        "zainetto_timeline": df_zainetto_timeline
    }


def compute_zainetto_timeline(df_yearly: pd.DataFrame, current_year: int = None) -> pd.DataFrame:
    """
    Simula la cronistoria e la scadenza quadriennale dello Zainetto Fiscale (TUIR Art. 68 c. 5).
    Le minusvalenze generate nell'anno T sono compensabili con plusvalenze da redditi diversi
    fino al 31 dicembre dell'anno T+4.
    """
    if df_yearly is None or df_yearly.empty:
        return pd.DataFrame(columns=[
            "origin_year", "expiry_year", "initial_minus_eur", 
            "compensated_eur", "residual_active_eur", "expired_eur", 
            "years_to_expiry", "status", "urgency"
        ])

    import datetime
    if current_year is None:
        current_year = datetime.date.today().year

    # Creazione bucket cronologici
    buckets = []
    sorted_df = df_yearly.sort_values("year").copy()

    for _, row in sorted_df.iterrows():
        yr = int(row["year"])
        gains_div = float(row.get("realized_gain_diversi_eur", 0.0))
        losses = float(row.get("realized_loss_eur", 0.0))
        
        if gains_div >= losses:
            # Plusvalenze dell'anno coprono le minusvalenze dell'anno stesso
            excess_gain = gains_div - losses
            # L'eccesso di plusvalenza compensa i bucket pregressi aperti in ordine FIFO
            for b in buckets:
                if b["residual"] > 1e-6 and yr <= b["expiry_year"]:
                    offset_amt = min(excess_gain, b["residual"])
                    b["compensated"] += offset_amt
                    b["residual"] -= offset_amt
                    excess_gain -= offset_amt
                    if excess_gain <= 1e-6:
                        break
        else:
            # Le minusvalenze superano le plusvalenze dell'anno: si genera un nuovo bucket netto
            net_new_minus = losses - gains_div
            if net_new_minus > 1e-2:
                buckets.append({
                    "origin_year": yr,
                    "expiry_year": yr + 4,
                    "initial": round(net_new_minus, 2),
                    "compensated": 0.0,
                    "residual": round(net_new_minus, 2)
                })

    # Costruzione tabella di stato finale
    timeline_rows = []
    for b in buckets:
        orig = b["origin_year"]
        exp = b["expiry_year"]
        init = round(b["initial"], 2)
        comp = round(b["compensated"], 2)
        res = round(b["residual"], 2)
        
        is_expired = current_year > exp and res > 1e-2
        expired_amt = res if is_expired else 0.0
        active_res = 0.0 if is_expired else res
        years_left = max(0, exp - current_year)

        if comp >= init - 1e-2:
            status = "✅ Totalmente Compensato"
            urgency = "LOW"
        elif is_expired:
            status = f"🔴 Prescritto (Scaduto il 31/12/{exp})"
            urgency = "EXPIRED"
        elif years_left == 0:
            status = f"🔥 In Scadenza Imminente (31/12/{exp})"
            urgency = "CRITICAL"
        elif years_left == 1:
            status = f"⚠️ In Scadenza (31/12/{exp} - 1 anno)"
            urgency = "HIGH"
        else:
            status = f"🟢 Attivo (Scade il 31/12/{exp})"
            urgency = "MEDIUM"

        timeline_rows.append({
            "origin_year": orig,
            "expiry_year": exp,
            "initial_minus_eur": init,
            "compensated_eur": comp,
            "residual_active_eur": round(active_res, 2),
            "expired_eur": round(expired_amt, 2),
            "years_to_expiry": years_left,
            "status": status,
            "urgency": urgency
        })

    return pd.DataFrame(timeline_rows)


def compute_tax_loss_harvesting_strategy(
    results: Dict[str, Any],
    custom_zainetto_eur: float = None
) -> Dict[str, Any]:
    """
    Motore di Ottimizzazione Fiscale & Tax-Loss Harvesting Wizard (TUIR Art. 67).
    
    Identifica con precisione:
    1. Strategie di Step-Up Fiscale a imposta 0€:
       Vendere e ricomprare posizioni in utile (Redditi Diversi: azioni singole, bond, ETC) per
       consumare le minusvalenze pregresse accumulate nello Zainetto Fiscale, alzando il prezzo di carico
       senza pagare capital gain e risparmiando il 26% sulle future plusvalenze.
    2. Opportunità di Tax-Loss Harvesting su posizioni in perdita:
       Monetizzare perdite latenti per azzerare le imposte sui capital gain realizzati nell'anno corrente.
    """
    pos = results.get("positions", pd.DataFrame())
    if pos is None or pos.empty:
        return {
            "has_recommendations": False,
            "df_step_up": pd.DataFrame(),
            "df_harvest_loss": pd.DataFrame(),
            "total_tax_savings_eur": 0.0,
            "total_minus_consumable_eur": 0.0,
            "summary": {}
        }

    # Stima minusvalenze disponibili nello zainetto
    tax_res = compute_tax_and_harvesting(results) if results else {}
    df_timeline = tax_res.get("zainetto_timeline", pd.DataFrame())
    active_minus = float(df_timeline["residual_active_eur"].sum()) if isinstance(df_timeline, pd.DataFrame) and not df_timeline.empty and "residual_active_eur" in df_timeline.columns else 0.0
    
    if custom_zainetto_eur is not None and custom_zainetto_eur >= 0:
        available_zainetto = float(custom_zainetto_eur)
    else:
        available_zainetto = active_minus

    step_up_rows = []
    loss_harvest_rows = []

    remaining_zainetto = available_zainetto

    for _, row in pos.iterrows():
        ticker = str(row.get("ticker", ""))
        ac = str(row.get("asset_class", "Equity"))
        qty = float(row.get("qty_net", row.get("quantity", 0.0)) or 0.0)
        curr_price = float(row.get("current_price", row.get("price", 0.0)) or 0.0)
        cost_basis_eur = float(row.get("cost_basis_eur", row.get("cost_basis", 0.0)) or 0.0)
        unrealized_pnl = float(row.get("unrealized_pnl", row.get("pnl_unrealized", 0.0)) or 0.0)
        unrealized_pct = float(row.get("unrealized_pnl_pct", 0.0) or 0.0)
        
        etf_flag = is_etf(ac, ticker)
        tax_rate = get_asset_tax_rate(ac, ticker)

        # 1. Candidato Step-Up Fiscale (Utile su Redditi Diversi: NON ETF)
        if unrealized_pnl > 10.0 and not etf_flag and qty > 0 and curr_price > 0:
            consumable_gain = min(unrealized_pnl, remaining_zainetto) if remaining_zainetto > 0 else unrealized_pnl
            tax_saved = consumable_gain * tax_rate
            
            step_up_rows.append({
                "ticker": ticker,
                "asset_class": ac,
                "qty_held": round(qty, 4),
                "current_price_eur": round(curr_price, 2),
                "unrealized_gain_eur": round(unrealized_pnl, 2),
                "unrealized_gain_pct": round(unrealized_pct, 2),
                "consumable_minus_eur": round(consumable_gain, 2),
                "tax_saving_eur": round(tax_saved, 2),
                "action": "🎯 Vendi & Ricompra (Step-Up a 0€ Imposta)",
                "rationale": f"Monetizza € {consumable_gain:,.2f} di plusvalenza compensandola al 100% con lo zainetto. Il prezzo di carico sale a € {curr_price:.2f} con 0€ di tasse."
            })
            if remaining_zainetto > 0:
                remaining_zainetto = max(0.0, remaining_zainetto - consumable_gain)

        # 2. Candidato Tax-Loss Harvesting (Perdite Latenti)
        elif unrealized_pnl < -10.0 and qty > 0:
            loss_amt = abs(unrealized_pnl)
            potential_tax_shield = loss_amt * tax_rate
            
            loss_harvest_rows.append({
                "ticker": ticker,
                "asset_class": ac,
                "qty_held": round(qty, 4),
                "current_price_eur": round(curr_price, 2),
                "unrealized_loss_eur": round(unrealized_pnl, 2),
                "unrealized_loss_pct": round(unrealized_pct, 2),
                "loss_to_harvest_eur": round(loss_amt, 2),
                "tax_shield_created_eur": round(potential_tax_shield, 2),
                "action": "✂️ Vendi per Raccolta Minusvalenze",
                "rationale": f"Genera € {loss_amt:,.2f} di nuove minusvalenze per schermare future plusvalenze e ridurre il carico fiscale di € {potential_tax_shield:,.2f}."
            })

    df_step_up = pd.DataFrame(step_up_rows)
    if not df_step_up.empty:
        df_step_up = df_step_up.sort_values(by="tax_saving_eur", ascending=False)

    df_harvest = pd.DataFrame(loss_harvest_rows)
    if not df_harvest.empty:
        df_harvest = df_harvest.sort_values(by="tax_shield_created_eur", ascending=False)

    tot_tax_saved = float(df_step_up["tax_saving_eur"].sum()) if not df_step_up.empty else 0.0
    tot_minus_consumed = float(df_step_up["consumable_minus_eur"].sum()) if not df_step_up.empty else 0.0
    tot_shield_created = float(df_harvest["tax_shield_created_eur"].sum()) if not df_harvest.empty else 0.0

    return {
        "has_recommendations": (not df_step_up.empty or not df_harvest.empty),
        "df_step_up": df_step_up,
        "df_harvest_loss": df_harvest,
        "available_zainetto_eur": round(available_zainetto, 2),
        "total_minus_consumed_eur": round(tot_minus_consumed, 2),
        "total_tax_savings_eur": round(tot_tax_saved, 2),
        "total_tax_shield_created_eur": round(tot_shield_created, 2),
        "summary": {
            "n_step_up_candidates": len(df_step_up),
            "n_loss_candidates": len(df_harvest),
            "estimated_net_benefit_eur": round(tot_tax_saved + tot_shield_created, 2)
        }
    }

