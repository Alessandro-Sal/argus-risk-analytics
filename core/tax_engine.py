"""
ARGUS — Risk Analytics Platform
Core Module: Tax Optimization & Tax-Loss Harvesting Engine
Italian Fiscal Framework (TUIR Art. 67 - Regime Amministrato/Dichiarativo)
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union

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
    """Returns applicable tax rate (12.5% for sovereign/whitelist government bonds, 26% for equities/ETFs/crypto)."""
    if not asset_class:
        asset_class = ""
    ac_lower = str(asset_class).lower()
    t_upper = str(ticker).upper()
    
    gov_keywords = ["gov", "btp", "bot", "treasury", "stato", "sovereign", "titolo di stato", "bund", "oat", "bonos", "gilt"]
    if any(k in ac_lower for k in gov_keywords):
        return 0.125
    
    gov_ticker_prefixes = ["BTP", "BOT", "CCT", "CTZ", "TREASURY", "UST", "BUND", "OAT", "BONOS", "GILT", "US-TREASURY"]
    if any(p in t_upper for p in gov_ticker_prefixes):
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
                        fx_pair_inv = f"EUR{tx_curr}=X"
                        if fx_pair in fx_dict:
                            try:
                                idx = fx_dict[fx_pair].index.get_indexer([row["tx_date"]], method='ffill')[0]
                                if idx >= 0:
                                    fx_rate = float(fx_dict[fx_pair].iloc[idx])
                            except Exception:
                                pass
                        elif fx_pair_inv in fx_dict:
                            try:
                                idx = fx_dict[fx_pair_inv].index.get_indexer([row["tx_date"]], method='ffill')[0]
                                if idx >= 0:
                                    inv_r = float(fx_dict[fx_pair_inv].iloc[idx])
                                    if inv_r > 0:
                                        fx_rate = 1.0 / inv_r
                            except Exception:
                                pass
                        else:
                            fallback_map = {
                                "USD": 0.92, "GBP": 1.17, "CHF": 1.06, "DKK": 0.134,
                                "SEK": 0.088, "NOK": 0.086, "JPY": 0.0062, "CAD": 0.68,
                                "AUD": 0.61, "HKD": 0.118, "SGD": 0.69, "CNY": 0.128, "MXN": 0.051
                            }
                            fx_rate = fallback_map.get(tx_curr, 1.0)

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

    REPLACEMENT_PROXIES = {
        "AAPL": "MSFT (Proxy Tech Mega-Cap)",
        "NVDA": "AMD / SMH (Proxy Semiconduttori)",
        "MSFT": "GOOGL / QQQ (Proxy Cloud & Software)",
        "AMZN": "META / XLY (Proxy Consumer & Cloud)",
        "GOOGL": "META / MSFT (Proxy AI & Advertising)",
        "TSLA": "RIVN / XLY (Proxy EV & Auto)",
        "ENEL.MI": "IBE.MC (Iberdrola / Utilities Europa)",
        "ISP.MI": "UCG.MI (UniCredit / Banche Italia)",
        "UCG.MI": "ISP.MI (Intesa Sanpaolo / Banche Italia)",
        "ENI.MI": "TTE.PA (TotalEnergies / Oil & Gas)",
        "BND": "AGGH / IEAC (Proxy Obbligazionario)",
        "TLT": "IEF / VGEA (Proxy Treasury / Gov)",
        "BTC": "ETH / SOL (Proxy Crypto Major)",
        "ETH": "BTC / SOL (Proxy Crypto Smart Contracts)",
    }

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
        proxy_asset = REPLACEMENT_PROXIES.get(ticker, f"Attendi 31 Giorni o ETF Settoriale ({ac})")

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
                "action": "🎯 Vendi & Ricompra (Step-Up 0€ Tasse)",
                "replacement_proxy": "Riacquisto Immediato stesso Ticker",
                "rationale": f"Monetizza € {consumable_gain:,.2f} di plusvalenza compensandola al 100% con lo zainetto. Il prezzo di carico sale a € {curr_price:.2f} con 0€ di imposta."
            })
            if remaining_zainetto > 0:
                remaining_zainetto = max(0.0, remaining_zainetto - consumable_gain)

        # 2. Candidato Tax-Loss Harvesting (Perdite Latenti)
        elif unrealized_pnl < -10.0 and qty > 0:
            loss_amt = abs(unrealized_pnl)
            potential_tax_shield = loss_amt * tax_rate
            order_notional = qty * curr_price
            
            loss_harvest_rows.append({
                "ticker": ticker,
                "asset_class": ac,
                "qty_held": round(qty, 4),
                "current_price_eur": round(curr_price, 2),
                "order_notional_eur": round(order_notional, 2),
                "unrealized_loss_eur": round(unrealized_pnl, 2),
                "unrealized_loss_pct": round(unrealized_pct, 2),
                "loss_to_harvest_eur": round(loss_amt, 2),
                "tax_shield_created_eur": round(potential_tax_shield, 2),
                "action": "✂️ SELL HARVEST (Monetizza Minus)",
                "replacement_proxy": proxy_asset,
                "rationale": f"Vendi {qty:,.2f} quote per generare € {loss_amt:,.2f} di credito fiscale nello zainetto (€ {potential_tax_shield:,.2f} risparmio netto). Re-investi in {proxy_asset}."
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


# Institutional Alias for Frontend & Module Imports
generate_tax_loss_harvesting_strategy = compute_tax_loss_harvesting_strategy


# ══════════════════════════════════════════════════════════════════════════════
# 1. SIMULATORE RIFORMA FISCALE (ARMONIZZAZIONE ETF & COMPENSAZIONE TOTALE)
# ══════════════════════════════════════════════════════════════════════════════

def compute_riforma_fiscale_comparison(
    results: Dict[str, Any],
    tax_year: Optional[int] = None,
    custom_zainetto_eur: Optional[float] = None
) -> Dict[str, Any]:
    """
    Confronta il carico fiscale tra il Regime TUIR Attuale (asimmetrico: Plusvalenze ETF non compensabili)
    e il Regime Post-Riforma Fiscale Armonizzata (Tutte le plusvalenze compensano le minusvalenze).
    """
    tax_res = compute_tax_and_harvesting(results, tax_year=tax_year)
    tax_sum = tax_res.get("summary", {})
    
    gain_diversi = float(tax_sum.get("total_realized_gain_diversi_eur", 0.0))
    gain_etf = float(tax_sum.get("total_realized_gain_etf_eur", 0.0))
    losses = float(tax_sum.get("total_realized_loss_eur", 0.0))
    
    if custom_zainetto_eur is not None and custom_zainetto_eur >= 0:
        available_minus = losses + float(custom_zainetto_eur)
    else:
        available_minus = losses + float(tax_sum.get("tax_credit_zainetto_eur", 0.0))

    # ── 1. REGIME ATTUALE (TUIR Art. 67) ──
    net_diversi_curr = gain_diversi - available_minus
    taxable_diversi_curr = max(0.0, net_diversi_curr)
    tax_due_diversi_curr = taxable_diversi_curr * 0.26
    
    # ETF tassati SEMPRE al 26% senza compensazione
    tax_due_etf_curr = gain_etf * 0.26
    total_tax_current = tax_due_diversi_curr + tax_due_etf_curr
    residual_minus_current = abs(net_diversi_curr) if net_diversi_curr < 0 else 0.0

    # ── 2. REGIME RIFORMA FISCALE (Armonizzato) ──
    total_gain_unified = gain_diversi + gain_etf
    net_unified = total_gain_unified - available_minus
    taxable_unified = max(0.0, net_unified)
    total_tax_reformed = taxable_unified * 0.26
    residual_minus_reformed = abs(net_unified) if net_unified < 0 else 0.0

    # Risparmio Fiscale e Tax Drag
    tax_savings = max(0.0, total_tax_current - total_tax_reformed)
    tax_drag_pct = round((tax_savings / max(1.0, total_gain_unified)) * 100.0, 2) if total_gain_unified > 0 else 0.0

    return {
        "current_regime": {
            "gain_diversi_eur": round(gain_diversi, 2),
            "gain_etf_eur": round(gain_etf, 2),
            "total_gain_eur": round(gain_diversi + gain_etf, 2),
            "minus_applied_eur": round(min(gain_diversi, available_minus), 2),
            "taxable_base_eur": round(taxable_diversi_curr + gain_etf, 2),
            "tax_due_eur": round(total_tax_current, 2),
            "residual_minus_eur": round(residual_minus_current, 2),
            "effective_tax_rate_pct": round((total_tax_current / max(1.0, total_gain_unified)) * 100.0, 2) if total_gain_unified > 0 else 0.0
        },
        "reformed_regime": {
            "total_gain_eur": round(total_gain_unified, 2),
            "minus_applied_eur": round(min(total_gain_unified, available_minus), 2),
            "taxable_base_eur": round(taxable_unified, 2),
            "tax_due_eur": round(total_tax_reformed, 2),
            "residual_minus_eur": round(residual_minus_reformed, 2),
            "effective_tax_rate_pct": round((total_tax_reformed / max(1.0, total_gain_unified)) * 100.0, 2) if total_gain_unified > 0 else 0.0
        },
        "comparison": {
            "net_tax_savings_eur": round(tax_savings, 2),
            "tax_drag_etf_asymmetry_eur": round(tax_due_etf_curr - max(0.0, (gain_etf - max(0.0, available_minus - gain_diversi))) * 0.26, 2),
            "tax_drag_pct": tax_drag_pct,
            "minus_utilization_improvement_eur": round(min(total_gain_unified, available_minus) - min(gain_diversi, available_minus), 2)
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. PROSPETTO PRECOMPILATO MODELLO REDDITI PF (QUADRO RT & QUADRO RW)
# ══════════════════════════════════════════════════════════════════════════════

def compute_modello_redditi_pf(
    results: Dict[str, Any],
    tax_year: Optional[int] = None,
    db_engine = None,
    prior_minus_custom_eur: Optional[float] = None
) -> Dict[str, Any]:
    """
    Genera i righi precompilati conformi al Modello Redditi Persone Fisiche (Regime Dichiarativo):
    - Quadro RT (Sezione II - Plusvalenze su partecipazioni non qualificate / titoli esteri / crypto)
    - Quadro RW (Monitoraggio fiscale attività patrimoniali e finanziarie estere & IVAFE)
    """
    pos = results.get("positions", pd.DataFrame())
    df_tx = results.get("df_tx", pd.DataFrame())
    
    # ── QUADRO RT (Sezione II) ──
    tax_res = compute_tax_and_harvesting(results, db_engine=db_engine, tax_year=tax_year)
    tax_sum = tax_res.get("summary", {})
    
    total_proceeds = 0.0
    total_cost_basis = 0.0
    
    if df_tx is not None and not df_tx.empty:
        df_tx_calc = df_tx.copy()
        if "tx_date" in df_tx_calc.columns:
            df_tx_calc["year"] = pd.to_datetime(df_tx_calc["tx_date"]).dt.year
            if tax_year is not None:
                df_tx_calc = df_tx_calc[df_tx_calc["year"] == int(tax_year)]
                
        sells = df_tx_calc[df_tx_calc["tx_type"].astype(str).str.lower() == "sell"]
        if not sells.empty:
            total_proceeds = float((sells["quantity"] * sells["price"]).sum())
            total_cost_basis = max(0.0, total_proceeds - float(tax_sum.get("net_realized_pnl_eur", 0.0)))
    else:
        gain = float(tax_sum.get("total_realized_gain_diversi_eur", 0.0))
        loss = float(tax_sum.get("total_realized_loss_eur", 0.0))
        total_proceeds = max(gain, 1000.0) * 1.5
        total_cost_basis = total_proceeds - (gain - loss)

    net_pnl = float(tax_sum.get("total_realized_gain_diversi_eur", 0.0)) - float(tax_sum.get("total_realized_loss_eur", 0.0))
    plusv_lorda = max(0.0, net_pnl)
    minusv_anno = abs(net_pnl) if net_pnl < 0 else 0.0
    
    prior_minus = float(prior_minus_custom_eur) if prior_minus_custom_eur is not None else float(tax_sum.get("tax_credit_zainetto_eur", 0.0))
    minus_dedotta = min(plusv_lorda, prior_minus)
    imponibile_netto = max(0.0, plusv_lorda - minus_dedotta)
    imposta_sostitutiva = imponibile_netto * 0.26
    minus_riportabile = (prior_minus - minus_dedotta) + minusv_anno

    rt_rows = [
        {"rigo": "RT21", "descrizione": "Totale dei corrispettivi derivanti dalle cessioni a titolo oneroso", "valore_eur": round(total_proceeds, 2)},
        {"rigo": "RT22", "descrizione": "Totale dei costi fiscalmente rilevanti o valori d'acquisto (FIFO)", "valore_eur": round(total_cost_basis, 2)},
        {"rigo": "RT23", "descrizione": "Differenza positiva (Plusvalenze realizzate nell'anno fiscale)", "valore_eur": round(plusv_lorda, 2)},
        {"rigo": "RT24", "descrizione": "Eccedenza di minusvalenze da esercizi precedenti dedotta nell'anno", "valore_eur": round(minus_dedotta, 2)},
        {"rigo": "RT25", "descrizione": "Minusvalenze residue non compensate da riportare agli anni successivi", "valore_eur": round(minus_riportabile, 2)},
        {"rigo": "RT26", "descrizione": "Imposta sostitutiva dovuta al 26% (da versare con Modello F24)", "valore_eur": round(imposta_sostitutiva, 2)},
    ]
    df_rt = pd.DataFrame(rt_rows)

    # ── QUADRO RW (Monitoraggio Fiscale Attività Estere & IVAFE) ──
    rw_rows = []
    if not pos.empty:
        for idx, row in pos.iterrows():
            ticker = str(row.get("ticker", ""))
            ac = str(row.get("asset_class", "Equity"))
            val_eur = float(row.get("current_value", row.get("current_value_eur", 0.0)) or 0.0)
            cost_eur = float(row.get("cost_basis_eur", row.get("cost_basis", val_eur)) or val_eur)
            
            if val_eur <= 0.01:
                continue

            # Determinazione Codice Paese e Codice Investimento
            t_up = ticker.upper()
            if "BTC" in t_up or "ETH" in t_up or "SOL" in t_up or "ADA" in t_up or "CRYPTO" in str(ac).upper():
                cod_inv = "21 (Cripto-attività)"
                cod_paese = "000 (Decentralizzato)"
                ivafe_rate = 0.002
            elif ".DE" in t_up or ".F" in t_up:
                cod_inv = "1 (Titoli esteri / Fondi)"
                cod_paese = "018 (Germania)"
                ivafe_rate = 0.002
            elif ".PA" in t_up:
                cod_inv = "1 (Titoli esteri / Fondi)"
                cod_paese = "041 (Francia)"
                ivafe_rate = 0.002
            elif ".SW" in t_up or ".VX" in t_up:
                cod_inv = "1 (Titoli esteri / Fondi)"
                cod_paese = "080 (Svizzera)"
                ivafe_rate = 0.002
            elif ".CO" in t_up:
                cod_inv = "1 (Titoli esteri / Fondi)"
                cod_paese = "024 (Danimarca)"
                ivafe_rate = 0.002
            elif ".L" in t_up:
                cod_inv = "1 (Titoli esteri / Fondi)"
                cod_paese = "071 (Regno Unito)"
                ivafe_rate = 0.002
            elif ".MI" in t_up:
                # Titoli italiani quotati su Borsa Italiana: esenti da Quadro RW se presso intermediario residente
                continue
            else:
                cod_inv = "1 (Titoli esteri / Azioni)"
                cod_paese = "069 (Stati Uniti d'America)"
                ivafe_rate = 0.002

            ivafe_val = val_eur * ivafe_rate
            rw_rows.append({
                "rigo": f"RW{len(rw_rows) + 1}",
                "ticker": ticker,
                "asset_class": ac,
                "codice_investimento": cod_inv,
                "codice_paese": cod_paese,
                "quota_possesso_pct": 100.0,
                "giorni_detenzione": 365,
                "valore_iniziale_eur": round(cost_eur, 2),
                "valore_finale_eur": round(val_eur, 2),
                "ivafe_calcolata_eur": round(ivafe_val, 2)
            })

    df_rw = pd.DataFrame(rw_rows)
    tot_ivafe = float(df_rw["ivafe_calcolata_eur"].sum()) if not df_rw.empty else 0.0
    tot_ivafe_due = tot_ivafe if tot_ivafe >= 12.0 else 0.0 # Esenzione per importi inferiori a 12€

    return {
        "df_quadro_rt": df_rt,
        "df_quadro_rw": df_rw,
        "summary": {
            "imposta_sostitutiva_rt_eur": round(imposta_sostitutiva, 2),
            "totale_ivafe_rw_eur": round(tot_ivafe_due, 2),
            "totale_debito_dichiarativo_eur": round(imposta_sostitutiva + tot_ivafe_due, 2),
            "minusvalenze_riportabili_eur": round(minus_riportabile, 2),
            "esenzione_ivafe_applicata": (tot_ivafe < 12.0 and tot_ivafe > 0.0)
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. ANALIZZATORE WITHHOLDING TAX DIVIDENDI ESTERI (DOPPIA IMPOSIZIONE)
# ══════════════════════════════════════════════════════════════════════════════

def compute_withholding_tax_analysis(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcola l'impatto della Withholding Tax (WHT) sui dividendi esteri, l'aliquota combinata effettiva
    con la ritenuta italiana al 26% sul netto frontiera, e il Tax Drag rispetto a un ETF UCITS ad accumulazione.
    """
    pos = results.get("positions", pd.DataFrame())
    if pos.empty:
        return {
            "df_withholding": pd.DataFrame(),
            "summary": {
                "total_gross_dividends_eur": 0.0,
                "total_foreign_wht_eur": 0.0,
                "total_italian_tax_eur": 0.0,
                "total_tax_paid_eur": 0.0,
                "total_net_dividends_eur": 0.0,
                "weighted_effective_tax_pct": 0.0,
                "total_tax_drag_vs_accumulating_eur": 0.0
            }
        }

    WHT_RATES = {
        "US": (0.15, "USA (Trattato W-8BEN: 15%)"),
        "DE": (0.26375, "Germania (26.375% con SolZ)"),
        "FR": (0.128, "Francia (Convenzione: 12.8%)"),
        "CH": (0.35, "Svizzera (Verrechnungssteuer: 35%)"),
        "DK": (0.27, "Danimarca (Udbytteskat: 27%)"),
        "UK": (0.00, "Regno Unito (0% WHT)"),
        "IT": (0.00, "Italia (0% WHT, 26% Sostitutiva)"),
        "DEFAULT": (0.15, "Convenzione OCSE Standard (15%)")
    }

    div_rows = []
    tot_gross, tot_wht, tot_it, tot_net, tot_drag = 0.0, 0.0, 0.0, 0.0, 0.0

    for _, row in pos.iterrows():
        ticker = str(row.get("ticker", ""))
        ac = str(row.get("asset_class", "Equity"))
        val_eur = float(row.get("current_value", row.get("current_value_eur", 0.0)) or 0.0)
        div_hist = float(row.get("dividends_total", 0.0) or 0.0)
        div_yield_pct = float(row.get("dividend_yield", row.get("dividend_yield_pct", 0.0)) or 0.0)
        
        # Stima dividendo annuo se storico assente
        if div_hist > 0:
            est_gross_div = div_hist
        elif div_yield_pct > 0 and val_eur > 0:
            est_gross_div = val_eur * (div_yield_pct / 100.0)
        else:
            continue

        t_up = ticker.upper()
        if is_etf(ac, ticker):
            country_code = "IT"
            wht_rate, wht_label = 0.0, "ETF UCITS (Esente WHT diretta)"
        elif ".DE" in t_up or ".F" in t_up:
            country_code = "DE"
            wht_rate, wht_label = WHT_RATES["DE"]
        elif ".PA" in t_up:
            country_code = "FR"
            wht_rate, wht_label = WHT_RATES["FR"]
        elif ".SW" in t_up or ".VX" in t_up:
            country_code = "CH"
            wht_rate, wht_label = WHT_RATES["CH"]
        elif ".CO" in t_up:
            country_code = "DK"
            wht_rate, wht_label = WHT_RATES["DK"]
        elif ".L" in t_up:
            country_code = "UK"
            wht_rate, wht_label = WHT_RATES["UK"]
        elif ".MI" in t_up:
            country_code = "IT"
            wht_rate, wht_label = WHT_RATES["IT"]
        else:
            country_code = "US"
            wht_rate, wht_label = WHT_RATES["US"]

        foreign_wht_paid = est_gross_div * wht_rate
        net_frontier = est_gross_div - foreign_wht_paid
        italian_tax_paid = net_frontier * 0.26
        total_tax_paid = foreign_wht_paid + italian_tax_paid
        net_received = est_gross_div - total_tax_paid
        
        effective_rate = (total_tax_paid / est_gross_div) * 100.0 if est_gross_div > 0 else 26.0

        # Confronto con ETF UCITS ad accumulazione (WHT interna 15% su USA + 0% imposta immediata fino a vendita)
        ucits_internal_tax = est_gross_div * 0.15 if country_code == "US" else est_gross_div * wht_rate
        tax_drag_vs_acc = max(0.0, total_tax_paid - ucits_internal_tax)

        tot_gross += est_gross_div
        tot_wht += foreign_wht_paid
        tot_it += italian_tax_paid
        tot_net += net_received
        tot_drag += tax_drag_vs_acc

        div_rows.append({
            "ticker": ticker,
            "asset_class": ac,
            "paese_regime": wht_label,
            "dividendo_lordo_eur": round(est_gross_div, 2),
            "ritenuta_estera_wht_eur": round(foreign_wht_paid, 2),
            "aliquota_wht_pct": round(wht_rate * 100.0, 1),
            "netto_frontiera_eur": round(net_frontier, 2),
            "imposta_italiana_26_eur": round(italian_tax_paid, 2),
            "totale_imposte_eur": round(total_tax_paid, 2),
            "dividendo_netto_incassato_eur": round(net_received, 2),
            "aliquota_effettiva_combinata_pct": round(effective_rate, 2),
            "tax_drag_vs_accumulo_eur": round(tax_drag_vs_acc, 2)
        })

    df_div = pd.DataFrame(div_rows)
    if not df_div.empty:
        df_div = df_div.sort_values(by="dividendo_lordo_eur", ascending=False)

    tot_tax_paid = tot_wht + tot_it
    weighted_eff_rate = (tot_tax_paid / tot_gross) * 100.0 if tot_gross > 0 else 0.0

    return {
        "df_withholding": df_div,
        "summary": {
            "total_gross_dividends_eur": round(tot_gross, 2),
            "total_foreign_wht_eur": round(tot_wht, 2),
            "total_italian_tax_eur": round(tot_it, 2),
            "total_tax_paid_eur": round(tot_wht + tot_it, 2),
            "total_net_dividends_eur": round(tot_net, 2),
            "weighted_effective_tax_pct": round(weighted_eff_rate, 2),
            "total_tax_drag_vs_accumulating_eur": round(tot_drag, 2)
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. SIMULATORE PRE-TRADE "TAX-SMART LOT SIZING" (LOTTI FIFO PUNTUALI)
# ══════════════════════════════════════════════════════════════════════════════

def simulate_fifo_lot_sale(
    results: Dict[str, Any],
    ticker: str,
    qty_to_sell: float,
    sale_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Simulatore Pre-Trade avanzato di vendita per lotti FIFO:
    Identifica esattamente quali lotti di acquisto storici verranno scaricati,
    il PnL realizzato per ciascun lotto e il relativo debito fiscale o credito generato.
    """
    pos = results.get("positions", pd.DataFrame())
    df_tx = results.get("df_tx", pd.DataFrame())
    
    ticker_pos = pos[pos["ticker"] == ticker] if not pos.empty and "ticker" in pos.columns else pd.DataFrame()
    curr_mkt_price = float(ticker_pos["current_price"].values[0]) if not ticker_pos.empty and "current_price" in ticker_pos.columns else 100.0
    total_qty_held = float(ticker_pos["qty_net"].values[0]) if not ticker_pos.empty and "qty_net" in ticker_pos.columns else 0.0
    ac = str(ticker_pos["asset_class"].values[0]) if not ticker_pos.empty and "asset_class" in ticker_pos.columns else "Equity"
    
    exec_price = float(sale_price) if (sale_price is not None and sale_price > 0) else curr_mkt_price
    tax_rate = get_asset_tax_rate(ac, ticker)
    etf_flag = is_etf(ac, ticker)

    # Ricostruzione della coda dei lotti d'acquisto FIFO aperti
    open_lots = []
    if df_tx is not None and not df_tx.empty and "ticker" in df_tx.columns:
        sub_tx = df_tx[df_tx["ticker"] == ticker].sort_values(["tx_date", "tx_id"] if "tx_id" in df_tx.columns else ["tx_date"])
        for _, tx in sub_tx.iterrows():
            ttype = str(tx.get("tx_type", "buy")).lower().strip()
            tqty = float(tx.get("quantity", 0.0))
            tprice = float(tx.get("price", 0.0))
            tdate = str(tx.get("tx_date", ""))[:10]
            
            if ttype == "buy":
                open_lots.append({"date": tdate, "qty": tqty, "price": tprice})
            elif ttype == "sell":
                q_rem = tqty
                while q_rem > 1e-9 and open_lots:
                    if open_lots[0]["qty"] <= q_rem + 1e-9:
                        q_rem -= open_lots[0]["qty"]
                        open_lots.pop(0)
                    else:
                        open_lots[0]["qty"] -= q_rem
                        q_rem = 0.0

    # Fallback sintetico se non ci sono transazioni storiche nel database
    if not open_lots and total_qty_held > 0:
        cost_basis = float(ticker_pos["cost_basis_eur"].values[0]) if "cost_basis_eur" in ticker_pos.columns else exec_price * 0.90
        open_lots.append({"date": "Lotto Aperto (Storico)", "qty": total_qty_held, "price": cost_basis})

    # Simulazione scarico FIFO
    target_sell = min(float(qty_to_sell), total_qty_held) if total_qty_held > 0 else float(qty_to_sell)
    remaining_to_sell = target_sell
    
    affected_lots = []
    total_proceeds = target_sell * exec_price
    total_cost_discharged = 0.0
    total_realized_pnl = 0.0

    for lot in open_lots:
        if remaining_to_sell <= 1e-9:
            break
        
        lot_qty = lot["qty"]
        lot_price = lot["price"]
        lot_date = lot["date"]
        
        qty_from_lot = min(lot_qty, remaining_to_sell)
        lot_proceeds = qty_from_lot * exec_price
        lot_cost = qty_from_lot * lot_price
        lot_pnl = lot_proceeds - lot_cost
        lot_tax = max(0.0, lot_pnl * tax_rate) if lot_pnl > 0 else 0.0
        
        total_cost_discharged += lot_cost
        total_realized_pnl += lot_pnl
        remaining_to_sell -= qty_from_lot

        affected_lots.append({
            "data_lotto": lot_date,
            "quote_scaricate": round(qty_from_lot, 4),
            "prezzo_carico_lotto_eur": round(lot_price, 2),
            "prezzo_vendita_eur": round(exec_price, 2),
            "controvalore_lotto_eur": round(lot_proceeds, 2),
            "costo_fiscale_lotto_eur": round(lot_cost, 2),
            "pnl_lotto_eur": round(lot_pnl, 2),
            "pnl_lotto_pct": round(((exec_price - lot_price) / max(0.01, lot_price)) * 100.0, 2),
            "imposta_stimata_eur": round(lot_tax, 2),
            "tipo_reddito": "Redditi di Capitale (Non Compensabile)" if (etf_flag and lot_pnl > 0) else "Redditi Diversi (Compensabile)"
        })

    df_affected = pd.DataFrame(affected_lots)
    realized_tax_due = max(0.0, total_realized_pnl * tax_rate) if total_realized_pnl > 0 else 0.0
    minusvalenza_generata = abs(total_realized_pnl) if total_realized_pnl < 0 else 0.0
    
    residual_shares = max(0.0, total_qty_held - target_sell)
    residual_val = residual_shares * curr_mkt_price

    return {
        "ticker": ticker,
        "asset_class": ac,
        "qty_requested_to_sell": round(target_sell, 4),
        "sale_price_eur": round(exec_price, 2),
        "total_proceeds_eur": round(total_proceeds, 2),
        "total_cost_discharged_eur": round(total_cost_discharged, 2),
        "total_realized_pnl_eur": round(total_realized_pnl, 2),
        "realized_pnl_eur": round(total_realized_pnl, 2),
        "realized_pnl_pct": round((total_realized_pnl / max(1.0, total_cost_discharged)) * 100.0, 2) if total_cost_discharged > 0 else 0.0,
        "applicable_tax_rate_pct": round(tax_rate * 100.0, 1),
        "estimated_tax_due_eur": round(realized_tax_due, 2),
        "minusvalenza_generata_eur": round(minusvalenza_generata, 2),
        "is_etf": etf_flag,
        "residual_shares": round(residual_shares, 4),
        "residual_value_eur": round(residual_val, 2),
        "df_affected_lots": df_affected
    }
