import pandas as pd
import numpy as np
from datetime import datetime

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
        meta_map[ticker] = {
            "asset_class": first_row.get("asset_class", "Equity"),
            "sector": first_row.get("gics_sector", first_row.get("sector", "Diversified")),
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
        "df_closed_assets": df_assets.sort_values("realized_pnl_eur", ascending=False)
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
        "df_closed_assets": pd.DataFrame()
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
