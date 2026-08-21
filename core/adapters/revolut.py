"""
ARGUS — Risk Analytics Platform
Core Module: Revolut Trading CSV Adapter
Parsing e normalizzazione dei report esportati dalla sezione Trading/Investimenti di Revolut.
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


def _classify_revolut_tx_type(raw_type: str) -> Optional[str]:
    """Classifica la tipologia di transazione per Revolut Trading."""
    t = raw_type.strip().lower()
    if any(k in t for k in ["dividend", "dividendo", "div", "yield"]):
        return "dividend"
    if any(k in t for k in ["sell", "vendita", "sell - market", "sell - limit"]):
        return "sell"
    if any(k in t for k in ["buy", "acquisto", "buy - market", "buy - limit", "recurring buy"]):
        return "buy"
    if any(k in t for k in ["split", "stock split"]):
        return "split"
    if any(k in t for k in ["fee", "custody", "custodia", "topup", "deposit", "withdrawal", "transfer"]):
        return None
    return "buy"


def _detect_revolut_asset_class(ticker: str, desc: str) -> str:
    """Rileva l'asset class della posizione Revolut."""
    comb = f"{ticker} {desc}".lower()
    if any(k in comb for k in ["crypto", "btc", "eth", "sol", "doge", "xrp", "crypto"]):
        return "crypto"
    if any(k in comb for k in ["etf", "ishares", "vanguard", "spdr", "invesco", "wisdomtree"]):
        return "etf"
    if any(k in comb for k in ["bond", "treasury"]):
        return "bond"
    return "stock"


def _parse_revolut_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo record da una riga Revolut Trading."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    raw_type = str(row.get(cols["type"], "")).strip() if cols["type"] else ""
    tx_type = _classify_revolut_tx_type(raw_type)
    if not tx_type:
        return None

    raw_ticker = str(row.get(cols["ticker"], "")).strip() if cols["ticker"] else ""
    raw_desc = str(row.get(cols["desc"], "")).strip() if cols["desc"] else ""
    raw_isin = str(row.get(cols["isin"], "")).strip() if cols["isin"] else ""

    identifier = raw_isin or raw_ticker or raw_desc
    ticker = resolve_isin_to_ticker(identifier, fallback_symbol=raw_ticker or raw_desc)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return None

    qty = abs(clean_numeric_value(row.get(cols["shares"]), default=1.0 if tx_type == "dividend" else 0.0))
    price = abs(clean_numeric_value(row.get(cols["price"]), default=0.0))
    amount = abs(clean_numeric_value(row.get(cols["amount"]), default=0.0))

    if tx_type == "dividend":
        qty = 1.0
        price = amount if amount > 0 else price
    elif price == 0.0 and qty > 0 and amount > 0:
        price = amount / qty
    elif qty == 0.0 and price > 0 and amount > 0:
        qty = amount / price

    if qty == 0.0 and tx_type != "dividend":
        return None

    fee = abs(clean_numeric_value(row.get(cols["fee"]), default=0.0)) if cols["fee"] else 0.0
    curr = str(row.get(cols["currency"], "USD")).strip().upper() if cols["currency"] else "USD"
    if not curr or curr in ["NAN", "NONE", ""]:
        curr = "USD"

    asset_class = _detect_revolut_asset_class(ticker, raw_desc)

    return {
        "tx_date": tx_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fee,
        "asset_class": asset_class,
        "notes": f"Revolut: {raw_desc or ticker}"
    }


def parse_revolut_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame esportato da Revolut Trading nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    def find_col(*aliases) -> Optional[str]:
        for col in df.columns:
            for alias in aliases:
                if alias in col:
                    return col
        return None

    cols = {
        "date": find_col("date", "data", "time", "timestamp"),
        "type": find_col("type", "tipo", "transaction type", "action"),
        "ticker": find_col("ticker", "symbol", "simbolo", "asset", "product"),
        "desc": find_col("description", "descrizione", "name", "nome"),
        "isin": find_col("isin"),
        "shares": find_col("quantity", "shares", "quantità", "quantita", "units"),
        "price": find_col("price per share", "price", "prezzo", "rate"),
        "amount": find_col("total amount", "amount", "importo", "value", "controvalore", "total"),
        "fee": find_col("fee", "fees", "commissioni", "fx fee"),
        "currency": find_col("currency", "valuta", "divisa"),
    }

    normalized_rows = []
    for _, row in df.iterrows():
        try:
            rec = _parse_revolut_row(row, cols)
            if rec:
                normalized_rows.append(rec)
        except Exception as e:
            logger.debug(f"[Revolut Adapter] Errore parsing riga: {e}")
            continue

    if not normalized_rows:
        return pd.DataFrame()

    res = pd.DataFrame(normalized_rows)
    res = res.sort_values(by=["tx_date", "tx_type"]).reset_index(drop=True)
    return res
