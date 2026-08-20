import pandas as pd
import numpy as np
from datetime import datetime

def _normalize_asset_class(ac_raw: str, ticker: str = "") -> str:
    """Normalizza la classe di attivo in etichette istituzionali standard in italiano."""
    if not ac_raw:
        ac_raw = ""
    s = str(ac_raw).lower().strip()
    t = str(ticker).upper().strip()
    
    if "etf" in s or "etf" in t or t in ["CSPX", "VWCE", "IEMG", "AGGH", "EIMI", "MEUD", "XEON", "NDIA.L"]:
        return "ETF & Fondi"
    elif "crypto" in s or "btc" in t or "eth" in t or "crypto" in t:
        return "Criptovalute"
    elif "bond" in s or "fixed" in s or "obbligaz" in s or "btp" in s or "bot" in s or "treasury" in s:
        return "Obbligazioni (Bond)"
    elif "commodit" in s or "gold" in s or "oil" in s or "materie" in s:
        return "Materie Prime"
    elif "cash" in s or "liquid" in s:
        return "Liquidità"
    else:
        return "Azioni (Equity)"


def _normalize_sector(sec_raw: str, ticker: str = "", ac_normalized: str = "Azioni (Equity)") -> str:
    """Normalizza il settore economico secondo la classificazione GICS standard in italiano."""
    if not sec_raw:
        sec_raw = ""
    s = str(sec_raw).lower().strip()
    t = str(ticker).upper().strip()
    
    if "tech" in s or "inform" in s or "semiconductor" in s or "software" in s:
        return "Tecnologia"
    elif "finan" in s or "bank" in s or "banc" in s or "assicur" in s or "insurance" in s:
        return "Servizi Finanziari"
    elif "health" in s or "pharma" in s or "salute" in s or "biotech" in s or "medical" in s:
        return "Salute & Pharma"
    elif "cyclical" in s or "discretionary" in s or "voluttuari" in s or "automotive" in s or "auto" in s or "beni di consumo" in s:
        return "Beni di Consumo"
    elif "staples" in s or "defensive" in s or "necessit" in s or "food" in s or "beverage" in s:
        return "Beni di Prima Necessità"
    elif "communi" in s or "telecom" in s or "media" in s:
        return "Comunicazioni & Media"
    elif "industr" in s or "manifatt" in s or "aerospace" in s:
        return "Industria & Manifattura"
    elif "energ" in s or "oil" in s or "gas" in s or "petrol" in s:
        return "Energia & Petroliferi"
    elif "utilit" in s or "rinnovabil" in s or "electric" in s or "green" in s:
        return "Utilities & Rinnovabili"
    elif "real estate" in s or "immobil" in s or "reit" in s:
        return "Immobiliare (REIT)"
    elif "mater" in s or "chemical" in s or "mining" in s or "metalli" in s:
        return "Materiali di Base"
    elif "emerging" in s or "emergenti" in s:
        return "Mercati Emergenti"
    elif "bond" in s or "obbligaz" in s or "treasury" in s or "gov" in s:
        return "Titoli di Stato & Corporate"
    else:
        return "Azionario Diversificato"


def compute_closed_trades_journal(
    df_tx: pd.DataFrame = None,
    df_prices: pd.DataFrame = None,
    df_positions: pd.DataFrame = None,
    is_sandbox: bool = False
) -> dict:
    """
    Analizza lo storico delle transazioni (df_tx) ed estrae con precisione contabile FIFO:
    1. Registro dei singoli lotti chiusi (Closed Trades Journal) con data acquisto/vendita,
       prezzo di carico/scarico, PnL monetario (€) e percentuale (%), Holding Period (giorni) ed esito.
    2. Sintesi aggregata per strumento (Graveyard / Posizioni Chiuse o Parzialmente Chiuse).
    3. Metriche quantitative di performance sulle operazioni chiuse:
       - PnL Realizzato Totale (€)
       - Win Rate (%)
       - Profit Factor (Guadagni Lordi / Perdite Lorde)
       - Payoff Ratio & Average Win / Loss (€)
       - Holding Period Medio (giorni lavorativi)
       - Miglior Trade & Peggior Trade Realizzato
    """
    # ── 1. GESTIONE SANDBOX / DATI VUOTI ─────────────────────────────────────
    if df_tx is None or df_tx.empty:
        if is_sandbox or (df_positions is not None and not df_positions.empty and "is_sandbox" in str(df_positions)):
            return _generate_sandbox_closed_trades()
        else:
            return _empty_closed_trades_result()

    # Normalizza colonne
    df = df_tx.copy()
    if "tx_type" not in df.columns or "quantity" not in df.columns or "price" not in df.columns:
        return _empty_closed_trades_result()

    df["tx_type_clean"] = df["tx_type"].astype(str).str.lower().str.strip()
    df["tx_date"] = pd.to_datetime(df["tx_date"])
    df = df.sort_values(["tx_date", "tx_id"] if "tx_id" in df.columns else ["tx_date"])

    # Dizionario prezzi FX se disponibili
    fx_dict = {}
    if df_prices is not None and not df_prices.empty and "ticker" in df_prices.columns and "close" in df_prices.columns:
        for fx_tk in df_prices[df_prices["ticker"].str.endswith("=X")]["ticker"].unique():
            s_fx = df_prices[df_prices["ticker"] == fx_tk].set_index("price_date")["close"].sort_index().ffill()
            fx_dict[fx_tk] = s_fx

    closed_lots = []
    asset_summaries = {}

    # Metadata map per Ticker
    meta_map = {}
    for ticker, grp in df.groupby("ticker"):
        first_row = grp.iloc[0]
        raw_ac = first_row.get("asset_class", "Equity")
        raw_sec = first_row.get("gics_sector", first_row.get("sector", "Azionario Diversificato"))
        norm_ac = _normalize_asset_class(raw_ac, ticker)
        norm_sec = _normalize_sector(raw_sec, ticker, norm_ac)
        meta_map[ticker] = {
            "asset_class": norm_ac,
            "sector": norm_sec,
            "country": first_row.get("country", "Global"),
            "currency": str(first_row.get("currency", first_row.get("asset_currency", "EUR"))).upper()
        }

    # ── 2. MOTORE FIFO PER OGNI TICKER ───────────────────────────────────────
    for ticker, grp in df.groupby("ticker"):
        meta = meta_map.get(ticker, {})
        cur = meta.get("currency", "EUR")
        fx_tk = f"{cur}EUR=X"
        fx_series = fx_dict.get(fx_tk, None)

        queue = []  # [{ "date": date, "qty": qty, "price_eur": px_eur, "price_orig": px, "tx_id": id }]
        ticker_closed_lots = []
        dividends_collected = 0.0
        total_qty_sold = 0.0
        total_cost_sold_eur = 0.0
        total_proceeds_eur = 0.0
        first_buy_date = None
        last_sell_date = None

        for _, row in grp.iterrows():
            tx_t = row["tx_type_clean"]
            qty = float(row["quantity"])
            tx_d = row["tx_date"]
            tx_id = row.get("tx_id", None)
            orig_price = float(row["price"])

            # Calcolo tasso di cambio EUR
            fx_rate = 1.0
            if cur not in ["EUR", "", "NAN", "NONE"] and fx_series is not None and not fx_series.empty:
                try:
                    idx = fx_series.index.get_indexer([tx_d], method='ffill')[0]
                    fx_rate = float(fx_series.iloc[idx]) if idx >= 0 else float(fx_series.iloc[0])
                except Exception:
                    pass

            price_eur = orig_price * fx_rate

            if tx_t in ["buy", "acquisto", "b"]:
                if first_buy_date is None:
                    first_buy_date = tx_d
                queue.append({
                    "date": tx_d,
                    "qty": qty,
                    "price_eur": price_eur,
                    "price_orig": orig_price,
                    "tx_id": tx_id
                })

            elif tx_t in ["sell", "vendita", "s"]:
                last_sell_date = tx_d
                qty_to_sell = qty

                while qty_to_sell > 1e-9 and queue:
                    lot = queue[0]
                    lot_qty = lot["qty"]
                    buy_px_eur = lot["price_eur"]
                    buy_d = lot["date"]

                    matched_qty = min(lot_qty, qty_to_sell)
                    cost_basis_eur = matched_qty * buy_px_eur
                    proceeds_eur = matched_qty * price_eur
                    pnl_eur = proceeds_eur - cost_basis_eur
                    pnl_pct = ((price_eur - buy_px_eur) / buy_px_eur * 100.0) if buy_px_eur > 0 else 0.0
                    holding_days = max(0, (tx_d - buy_d).days)

                    outcome = "🟢 WIN" if pnl_eur > 0.01 else ("🔴 LOSS" if pnl_eur < -0.01 else "🟡 BREAKEVEN")

                    lot_record = {
                        "ticker": ticker,
                        "asset_class": meta.get("asset_class", "Equity"),
                        "sector": meta.get("sector", "Diversified"),
                        "country": meta.get("country", "Global"),
                        "buy_date": buy_d.strftime("%Y-%m-%d"),
                        "sell_date": tx_d.strftime("%Y-%m-%d"),
                        "qty": round(matched_qty, 6),
                        "buy_price_eur": round(buy_px_eur, 4),
                        "sell_price_eur": round(price_eur, 4),
                        "cost_basis_eur": round(cost_basis_eur, 2),
                        "proceeds_eur": round(proceeds_eur, 2),
                        "realized_pnl_eur": round(pnl_eur, 2),
                        "realized_pnl_pct": round(pnl_pct, 2),
                        "holding_days": int(holding_days),
                        "outcome": outcome,
                    }
                    closed_lots.append(lot_record)
                    ticker_closed_lots.append(lot_record)

                    total_qty_sold += matched_qty
                    total_cost_sold_eur += cost_basis_eur
                    total_proceeds_eur += proceeds_eur

                    if lot_qty <= qty_to_sell + 1e-9:
                        qty_to_sell -= lot_qty
                        queue.pop(0)
                    else:
                        lot["qty"] -= qty_to_sell
                        qty_to_sell = 0.0

            elif tx_t in ["dividend", "cedola", "div", "d"]:
                dividends_collected += price_eur

        # Se ci sono state vendite, crea la riga di riepilogo asset
        qty_remaining = sum(l["qty"] for l in queue)
        if total_qty_sold > 0:
            tot_pnl_eur = total_proceeds_eur - total_cost_sold_eur
            tot_pnl_pct = (tot_pnl_eur / total_cost_sold_eur * 100.0) if total_cost_sold_eur > 0 else 0.0
            avg_holding = np.mean([l["holding_days"] for l in ticker_closed_lots]) if ticker_closed_lots else 0

            status_str = "🪦 Chiusa al 100%" if qty_remaining < 1e-6 else "⚡ Smobilizzo Parziale"

            asset_summaries[ticker] = {
                "ticker": ticker,
                "asset_class": meta.get("asset_class", "Equity"),
                "sector": meta.get("sector", "Diversified"),
                "country": meta.get("country", "Global"),
                "status": status_str,
                "qty_sold": round(total_qty_sold, 4),
                "qty_remaining": round(qty_remaining, 4),
                "avg_buy_price_eur": round(total_cost_sold_eur / total_qty_sold, 2) if total_qty_sold > 0 else 0.0,
                "avg_sell_price_eur": round(total_proceeds_eur / total_qty_sold, 2) if total_qty_sold > 0 else 0.0,
                "cost_basis_eur": round(total_cost_sold_eur, 2),
                "proceeds_eur": round(total_proceeds_eur, 2),
                "realized_pnl_eur": round(tot_pnl_eur, 2),
                "realized_pnl_pct": round(tot_pnl_pct, 2),
                "dividends_eur": round(dividends_collected, 2),
                "total_profit_eur": round(tot_pnl_eur + dividends_collected, 2),
                "first_buy_date": first_buy_date.strftime("%Y-%m-%d") if first_buy_date else "N/A",
                "last_sell_date": last_sell_date.strftime("%Y-%m-%d") if last_sell_date else "N/A",
                "avg_holding_days": int(round(avg_holding)),
                "outcome": "🟢 WIN" if tot_pnl_eur > 0.01 else ("🔴 LOSS" if tot_pnl_eur < -0.01 else "🟡 BREAKEVEN")
            }

    df_lots = pd.DataFrame(closed_lots)
    df_assets = pd.DataFrame(list(asset_summaries.values()))

    # Se non ci sono lotti chiusi, ritorna vuoto
    if df_lots.empty:
        return _empty_closed_trades_result()

    return _build_metrics_from_dataframes(df_lots, df_assets)


def _build_metrics_from_dataframes(df_lots: pd.DataFrame, df_assets: pd.DataFrame) -> dict:
    """Calcola le metriche aggregate da lotti chiusi e asset summary."""
    total_realized_pnl = float(df_lots["realized_pnl_eur"].sum())
    total_cost_basis = float(df_lots["cost_basis_eur"].sum())
    total_proceeds = float(df_lots["proceeds_eur"].sum())
    total_pnl_pct = (total_realized_pnl / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0

    total_closed_trades = len(df_lots)
    winning_trades = df_lots[df_lots["realized_pnl_eur"] > 0.01]
    losing_trades = df_lots[df_lots["realized_pnl_eur"] < -0.01]
    breakeven_trades = df_lots[(df_lots["realized_pnl_eur"] >= -0.01) & (df_lots["realized_pnl_eur"] <= 0.01)]

    n_win = len(winning_trades)
    n_loss = len(losing_trades)
    n_be = len(breakeven_trades)

    win_rate_pct = (n_win / total_closed_trades * 100.0) if total_closed_trades > 0 else 0.0

    gross_profit = float(winning_trades["realized_pnl_eur"].sum()) if not winning_trades.empty else 0.0
    gross_loss = abs(float(losing_trades["realized_pnl_eur"].sum())) if not losing_trades.empty else 0.0

    profit_factor = (gross_profit / gross_loss) if gross_loss > 1e-6 else (99.9 if gross_profit > 0 else 0.0)

    avg_win_eur = float(winning_trades["realized_pnl_eur"].mean()) if not winning_trades.empty else 0.0
    avg_loss_eur = abs(float(losing_trades["realized_pnl_eur"].mean())) if not losing_trades.empty else 0.0
    payoff_ratio = (avg_win_eur / avg_loss_eur) if avg_loss_eur > 1e-6 else (99.9 if avg_win_eur > 0 else 0.0)

    avg_holding_days = float(df_lots["holding_days"].mean()) if not df_lots.empty else 0.0

    best_idx = df_lots["realized_pnl_eur"].idxmax() if not df_lots.empty else None
    worst_idx = df_lots["realized_pnl_eur"].idxmin() if not df_lots.empty else None

    best_trade = df_lots.loc[best_idx].to_dict() if best_idx is not None else {}
    worst_trade = df_lots.loc[worst_idx].to_dict() if worst_idx is not None else {}

    # Dividendi totali incassati su posizioni chiuse
    total_divs = float(df_assets["dividends_eur"].sum()) if not df_assets.empty and "dividends_eur" in df_assets.columns else 0.0

    # ── 1. Curva Cumulativa di PnL Realizzato
    df_cum_curve = compute_cumulative_realized_curve(df_lots)

    # ── 2. Matrice Trading Calendar Mensile
    calendar_data = compute_monthly_trading_calendar(df_lots)

    # ── 3. Scomposizione per Settore & Asset Class
    breakdown_data = compute_sector_asset_class_breakdown(df_lots)

    return {
        "has_closed_trades": True,
        "total_realized_pnl_eur": round(total_realized_pnl, 2),
        "total_realized_pnl_pct": round(total_pnl_pct, 2),
        "total_cost_basis_eur": round(total_cost_basis, 2),
        "total_proceeds_eur": round(total_proceeds, 2),
        "total_dividends_eur": round(total_divs, 2),
        "total_profit_net_eur": round(total_realized_pnl + total_divs, 2),
        "total_closed_trades": total_closed_trades,
        "n_winning_trades": n_win,
        "n_losing_trades": n_loss,
        "n_breakeven_trades": n_be,
        "win_rate_pct": round(win_rate_pct, 2),
        "profit_factor": round(profit_factor, 2),
        "gross_profit_eur": round(gross_profit, 2),
        "gross_loss_eur": round(gross_loss, 2),
        "avg_win_eur": round(avg_win_eur, 2),
        "avg_loss_eur": round(avg_loss_eur, 2),
        "payoff_ratio": round(payoff_ratio, 2),
        "avg_holding_days": int(round(avg_holding_days)),
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "df_closed_lots": df_lots.sort_values("sell_date", ascending=False),
        "df_closed_assets": df_assets.sort_values("realized_pnl_eur", ascending=False),
        "df_cumulative_curve": df_cum_curve,
        "calendar_data": calendar_data,
        "breakdown_data": breakdown_data
    }


def compute_cumulative_realized_curve(df_lots: pd.DataFrame) -> pd.DataFrame:
    """Genera la serie storica cumulativa del PnL realizzato nel tempo con High-Water Mark."""
    if df_lots is None or df_lots.empty:
        return pd.DataFrame()
    
    df_sorted = df_lots.sort_values("sell_date", ascending=True).copy()
    df_sorted["sell_date"] = pd.to_datetime(df_sorted["sell_date"])
    
    # Aggrega per data per avere un punto temporale univoco
    daily_pnl = df_sorted.groupby("sell_date").agg({
        "realized_pnl_eur": "sum",
        "ticker": lambda x: ", ".join(x.unique()[:3])
    }).reset_index()
    
    daily_pnl["realized_pnl_eur"] = daily_pnl["realized_pnl_eur"].round(2)
    daily_pnl["cum_realized_pnl_eur"] = daily_pnl["realized_pnl_eur"].cumsum().round(2)
    daily_pnl["high_water_mark_eur"] = daily_pnl["cum_realized_pnl_eur"].cummax().round(2)
    daily_pnl["drawdown_eur"] = (daily_pnl["cum_realized_pnl_eur"] - daily_pnl["high_water_mark_eur"]).round(2)
    daily_pnl["sell_date_str"] = daily_pnl["sell_date"].dt.strftime("%Y-%m-%d")
    
    return daily_pnl


def compute_monthly_trading_calendar(df_lots: pd.DataFrame) -> dict:
    """Calcola la matrice di performance mese x anno per le posizioni chiuse."""
    if df_lots is None or df_lots.empty:
        return {"df_pivot": pd.DataFrame(), "monthly_records": []}
    
    df = df_lots.copy()
    df["sell_date_dt"] = pd.to_datetime(df["sell_date"])
    df["year"] = df["sell_date_dt"].dt.year
    df["month"] = df["sell_date_dt"].dt.month
    
    month_names = {
        1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu",
        7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
    }
    df["month_name"] = df["month"].map(month_names)
    
    # Raggruppamento per Anno e Mese
    grp = df.groupby(["year", "month", "month_name"]).agg(
        pnl_eur=("realized_pnl_eur", "sum"),
        trades_count=("ticker", "count"),
        win_count=("realized_pnl_eur", lambda x: (x > 0.01).sum())
    ).reset_index()
    
    grp["win_rate"] = (grp["win_count"] / grp["trades_count"] * 100.0).round(1)
    
    # Pivot table Anno x Mese
    pivot = grp.pivot(index="year", columns="month_name", values="pnl_eur").fillna(0.0)
    
    # Ordina colonne mesi
    ordered_cols = [month_names[m] for m in range(1, 13) if month_names[m] in pivot.columns]
    pivot = pivot[ordered_cols]
    pivot["Totale Anno (€)"] = pivot.sum(axis=1)
    
    return {
        "df_pivot": pivot.sort_index(ascending=False),
        "monthly_records": grp.to_dict(orient="records")
    }


def compute_sector_asset_class_breakdown(df_lots: pd.DataFrame) -> dict:
    """Scompone il PnL realizzato per settore economico e asset class."""
    if df_lots is None or df_lots.empty:
        return {"df_by_sector": pd.DataFrame(), "df_by_asset_class": pd.DataFrame()}
    
    df = df_lots.copy()
    if "sector" not in df.columns:
        df["sector"] = "Azionario Diversificato"
    if "asset_class" not in df.columns:
        df["asset_class"] = "Azioni (Equity)"
        
    df["asset_class"] = df.apply(lambda r: _normalize_asset_class(r.get("asset_class", ""), r.get("ticker", "")), axis=1)
    df["sector"] = df.apply(lambda r: _normalize_sector(r.get("sector", ""), r.get("ticker", ""), r.get("asset_class", "")), axis=1)
    
    by_sector = df.groupby("sector").agg(
        pnl_eur=("realized_pnl_eur", "sum"),
        proceeds_eur=("proceeds_eur", "sum"),
        trades_count=("ticker", "count"),
        win_trades=("realized_pnl_eur", lambda x: (x > 0.01).sum())
    ).reset_index()
    by_sector["win_rate_pct"] = (by_sector["win_trades"] / by_sector["trades_count"] * 100.0).round(1)
    by_sector = by_sector.sort_values("pnl_eur", ascending=False)
    
    by_asset_class = df.groupby("asset_class").agg(
        pnl_eur=("realized_pnl_eur", "sum"),
        proceeds_eur=("proceeds_eur", "sum"),
        trades_count=("ticker", "count"),
        win_trades=("realized_pnl_eur", lambda x: (x > 0.01).sum())
    ).reset_index()
    by_asset_class["win_rate_pct"] = (by_asset_class["win_trades"] / by_asset_class["trades_count"] * 100.0).round(1)
    by_asset_class = by_asset_class.sort_values("pnl_eur", ascending=False)
    
    return {
        "df_by_sector": by_sector,
        "df_by_asset_class": by_asset_class
    }


def _empty_closed_trades_result() -> dict:
    """Ritorna struttura vuota se non sono presenti operazioni chiuse."""
    return {
        "has_closed_trades": False,
        "total_realized_pnl_eur": 0.0,
        "total_realized_pnl_pct": 0.0,
        "total_cost_basis_eur": 0.0,
        "total_proceeds_eur": 0.0,
        "total_dividends_eur": 0.0,
        "total_profit_net_eur": 0.0,
        "total_closed_trades": 0,
        "n_winning_trades": 0,
        "n_losing_trades": 0,
        "n_breakeven_trades": 0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "gross_profit_eur": 0.0,
        "gross_loss_eur": 0.0,
        "avg_win_eur": 0.0,
        "avg_loss_eur": 0.0,
        "payoff_ratio": 0.0,
        "avg_holding_days": 0,
        "best_trade": {},
        "worst_trade": {},
        "df_closed_lots": pd.DataFrame(),
        "df_closed_assets": pd.DataFrame(),
        "df_cumulative_curve": pd.DataFrame(),
        "calendar_data": {"df_pivot": pd.DataFrame(), "monthly_records": []},
        "breakdown_data": {"df_by_sector": pd.DataFrame(), "df_by_asset_class": pd.DataFrame()}
    }


def _generate_sandbox_closed_trades() -> dict:
    """Genera uno storico realistico di trade chiusi per la modalità Sandbox/Demo."""
    lots = [
        {
            "ticker": "TSLA", "asset_class": "Equity", "sector": "Consumer Cyclical", "country": "USA",
            "buy_date": "2024-02-15", "sell_date": "2024-08-20", "qty": 45.0,
            "buy_price_eur": 182.40, "sell_price_eur": 235.80, "cost_basis_eur": 8208.0, "proceeds_eur": 10611.0,
            "realized_pnl_eur": 2403.0, "realized_pnl_pct": 29.28, "holding_days": 187, "outcome": "🟢 WIN"
        },
        {
            "ticker": "NVDA", "asset_class": "Equity", "sector": "Technology", "country": "USA",
            "buy_date": "2024-01-10", "sell_date": "2024-06-18", "qty": 30.0,
            "buy_price_eur": 54.20, "sell_price_eur": 118.50, "cost_basis_eur": 1626.0, "proceeds_eur": 3555.0,
            "realized_pnl_eur": 1929.0, "realized_pnl_pct": 118.63, "holding_days": 160, "outcome": "🟢 WIN"
        },
        {
            "ticker": "BND", "asset_class": "Fixed Income", "sector": "Bonds & Treasuries", "country": "USA",
            "buy_date": "2023-11-05", "sell_date": "2024-04-12", "qty": 110.0,
            "buy_price_eur": 76.50, "sell_price_eur": 72.80, "cost_basis_eur": 8415.0, "proceeds_eur": 8008.0,
            "realized_pnl_eur": -407.0, "realized_pnl_pct": -4.84, "holding_days": 159, "outcome": "🔴 LOSS"
        },
        {
            "ticker": "ENEL.MI", "asset_class": "Equity", "sector": "Utilities", "country": "Italy",
            "buy_date": "2023-09-20", "sell_date": "2024-05-30", "qty": 800.0,
            "buy_price_eur": 5.90, "sell_price_eur": 6.75, "cost_basis_eur": 4720.0, "proceeds_eur": 5400.0,
            "realized_pnl_eur": 680.0, "realized_pnl_pct": 14.41, "holding_days": 253, "outcome": "🟢 WIN"
        },
        {
            "ticker": "PYPL", "asset_class": "Equity", "sector": "Financial Services", "country": "USA",
            "buy_date": "2024-03-01", "sell_date": "2024-07-15", "qty": 60.0,
            "buy_price_eur": 63.40, "sell_price_eur": 58.10, "cost_basis_eur": 3804.0, "proceeds_eur": 3486.0,
            "realized_pnl_eur": -318.0, "realized_pnl_pct": -8.36, "holding_days": 136, "outcome": "🔴 LOSS"
        }
    ]

    assets = [
        {
            "ticker": "TSLA", "asset_class": "Equity", "sector": "Consumer Cyclical", "country": "USA",
            "status": "🪦 Chiusa al 100%", "qty_sold": 45.0, "qty_remaining": 0.0,
            "avg_buy_price_eur": 182.40, "avg_sell_price_eur": 235.80, "cost_basis_eur": 8208.0, "proceeds_eur": 10611.0,
            "realized_pnl_eur": 2403.0, "realized_pnl_pct": 29.28, "dividends_eur": 0.0, "total_profit_eur": 2403.0,
            "first_buy_date": "2024-02-15", "last_sell_date": "2024-08-20", "avg_holding_days": 187, "outcome": "🟢 WIN"
        },
        {
            "ticker": "NVDA", "asset_class": "Equity", "sector": "Technology", "country": "USA",
            "status": "⚡ Smobilizzo Parziale", "qty_sold": 30.0, "qty_remaining": 20.0,
            "avg_buy_price_eur": 54.20, "avg_sell_price_eur": 118.50, "cost_basis_eur": 1626.0, "proceeds_eur": 3555.0,
            "realized_pnl_eur": 1929.0, "realized_pnl_pct": 118.63, "dividends_eur": 12.50, "total_profit_eur": 1941.50,
            "first_buy_date": "2024-01-10", "last_sell_date": "2024-06-18", "avg_holding_days": 160, "outcome": "🟢 WIN"
        },
        {
            "ticker": "ENEL.MI", "asset_class": "Equity", "sector": "Utilities", "country": "Italy",
            "status": "🪦 Chiusa al 100%", "qty_sold": 800.0, "qty_remaining": 0.0,
            "avg_buy_price_eur": 5.90, "avg_sell_price_eur": 6.75, "cost_basis_eur": 4720.0, "proceeds_eur": 5400.0,
            "realized_pnl_eur": 680.0, "realized_pnl_pct": 14.41, "dividends_eur": 180.0, "total_profit_eur": 860.0,
            "first_buy_date": "2023-09-20", "last_sell_date": "2024-05-30", "avg_holding_days": 253, "outcome": "🟢 WIN"
        },
        {
            "ticker": "PYPL", "asset_class": "Equity", "sector": "Financial Services", "country": "USA",
            "status": "🪦 Chiusa al 100%", "qty_sold": 60.0, "qty_remaining": 0.0,
            "avg_buy_price_eur": 63.40, "avg_sell_price_eur": 58.10, "cost_basis_eur": 3804.0, "proceeds_eur": 3486.0,
            "realized_pnl_eur": -318.0, "realized_pnl_pct": -8.36, "dividends_eur": 0.0, "total_profit_eur": -318.0,
            "first_buy_date": "2024-03-01", "last_sell_date": "2024-07-15", "avg_holding_days": 136, "outcome": "🔴 LOSS"
        },
        {
            "ticker": "BND", "asset_class": "Fixed Income", "sector": "Bonds & Treasuries", "country": "USA",
            "status": "⚡ Smobilizzo Parziale", "qty_sold": 110.0, "qty_remaining": 50.0,
            "avg_buy_price_eur": 76.50, "avg_sell_price_eur": 72.80, "cost_basis_eur": 8415.0, "proceeds_eur": 8008.0,
            "realized_pnl_eur": -407.0, "realized_pnl_pct": -4.84, "dividends_eur": 65.0, "total_profit_eur": -342.0,
            "first_buy_date": "2023-11-05", "last_sell_date": "2024-04-12", "avg_holding_days": 159, "outcome": "🔴 LOSS"
        }
    ]

    return _build_metrics_from_dataframes(pd.DataFrame(lots), pd.DataFrame(assets))
