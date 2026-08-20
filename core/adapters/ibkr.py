"""
ARGUS — Risk Analytics Platform
Core Module: Interactive Brokers (IBKR) CSV Adapter
Parsing e normalizzazione dei report esportati da Interactive Brokers (Activity Statement / Trades Report).
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from core.adapters.isin_resolver import (
    clean_date_value,
    clean_numeric_value,
    resolve_isin_to_ticker,
)

logger = logging.getLogger(__name__)


def _classify_ibkr_asset_class(raw_cat: str) -> str:
    """Mappa la categoria di strumento IBKR in una classe standard ARGUS."""
    cat = raw_cat.lower()
    if "crypto" in cat:
        return "crypto"
    if any(k in cat for k in ["etf", "fund"]):
        return "etf"
    if "bond" in cat:
        return "bond"
    return "stock"


def _parse_ibkr_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo trade da una riga IBKR."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    raw_sym = str(row.get(cols["symbol"], "")).strip().upper()
    if not raw_sym or raw_sym in ["NAN", "NONE", "TOTAL", "SUBTOTAL", ""]:
        return None

    ticker = resolve_isin_to_ticker(raw_sym, fallback_symbol=raw_sym)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return None

    raw_qty = clean_numeric_value(row.get(cols["qty"]), default=0.0)
    if raw_qty == 0.0:
        return None

    tx_type = "buy" if raw_qty > 0 else "sell"
    qty = abs(raw_qty)
    price = abs(clean_numeric_value(row.get(cols["price"]), default=0.0))
    fees = abs(clean_numeric_value(row.get(cols["fee"]), default=0.0)) if cols["fee"] else 0.0
    curr = str(row.get(cols["curr"], "USD")).strip().upper() if cols["curr"] else "USD"
    if not curr or curr in ["NAN", "NONE", ""]:
        curr = "USD"

    raw_cat = str(row.get(cols["cat"], "")).strip() if cols["cat"] else ""
    asset_class = _classify_ibkr_asset_class(raw_cat)

    return {
        "tx_date": tx_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fees,
        "asset_class": asset_class,
        "notes": f"IBKR: {ticker}"
    }


def _extract_records_from_ibkr_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Estrae e mappa le colonne IBKR nei campi standard ARGUS."""
    date_col = next((c for c in df.columns if any(k in c for k in ["date/time", "date", "trade date", "data"])), None)
    symbol_col = next((c for c in df.columns if any(k in c for k in ["symbol", "ticker", "financial instrument", "isin"])), None)
    qty_col = next((c for c in df.columns if any(k in c for k in ["quantity", "shares", "qty", "volume"])), None)
    price_col = next((c for c in df.columns if any(k in c for k in ["t. price", "trade price", "tradeprice", "price", "prezzo"])), None)
    fee_col = next((c for c in df.columns if any(k in c for k in ["comm/fee", "commission", "ibcommission", "fee", "spese"])), None)
    curr_col = next((c for c in df.columns if any(k in c for k in ["currencyprimary", "currency", "currency (base)", "valuta"])), None)
    cat_col = next((c for c in df.columns if any(k in c for k in ["asset category", "assetclass", "security type"])), None)

    if not date_col or not symbol_col or not qty_col:
        raise ValueError("Il file non sembra un export valido di Interactive Brokers (colonne Date, Symbol o Quantity mancanti).")

    cols = {
        "date": date_col, "symbol": symbol_col, "qty": qty_col,
        "price": price_col, "fee": fee_col, "curr": curr_col, "cat": cat_col
    }

    records = []
    for _, row in df.iterrows():
        rec = _parse_ibkr_row(row, cols)
        if rec:
            records.append(rec)

    if not records:
        raise ValueError("Nessuna transazione valida estratta dal file Interactive Brokers.")

    df_out = pd.DataFrame(records)
    return df_out.sort_values(by="tx_date").reset_index(drop=True)


def _parse_ibkr_activity_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Estrae e normalizza le righe della sezione 'Trades' dall'Activity Statement IBKR."""
    first_col = df.columns[0]
    trades_df = df[df[first_col].astype(str).str.strip() == "Trades"].copy()

    header_row = trades_df[trades_df.iloc[:, 1].astype(str).str.strip() == "Header"]
    if header_row.empty:
        headers = [str(v).strip().lower() for v in trades_df.iloc[0].values]
        data_df = trades_df.iloc[1:].copy()
    else:
        headers = [str(v).strip().lower() for v in header_row.iloc[0].values]
        data_df = trades_df[trades_df.iloc[:, 1].astype(str).str.strip().isin(["Data", "Order"])].copy()

    data_df.columns = headers[:len(data_df.columns)]
    return _extract_records_from_ibkr_dataframe(data_df)


def parse_ibkr_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame grezzo esportato da Interactive Brokers (IBKR) nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    first_col = df.columns[0]
    trades_rows = df[df[first_col].astype(str).str.strip() == "Trades"]

    if not trades_rows.empty:
        return _parse_ibkr_activity_statement(df)

    df.columns = df.columns.astype(str).str.strip().str.lower()
    return _extract_records_from_ibkr_dataframe(df)
