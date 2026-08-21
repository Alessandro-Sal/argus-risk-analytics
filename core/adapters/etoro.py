"""
ARGUS — Risk Analytics Platform
Core Module: eToro CSV Adapter
Parsing e normalizzazione dei report esportati da eToro (Account Statement, Closed Positions, Dividends).
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from core.adapters.isin_resolver import (
    clean_date_value,
    clean_numeric_value,
    resolve_isin_to_ticker,
)

logger = logging.getLogger(__name__)


def _classify_etoro_action(action_or_type: str) -> Optional[str]:
    """Classifica la tipologia di transazione per eToro."""
    act = action_or_type.strip().lower()
    if any(k in act for k in ["dividend", "dividendo", "yield", "payout"]):
        return "dividend"
    if any(k in act for k in ["close", "chiusura", "sell", "vendita", "short", "take profit", "stop loss"]):
        return "sell"
    if any(k in act for k in ["open", "apertura", "buy", "acquisto", "long"]):
        return "buy"
    if any(k in act for k in ["deposit", "deposito", "withdrawal", "prelievo", "fee", "transfer", "rollover"]):
        return None
    return "buy"


def _extract_ticker_from_etoro_details(details: str, isin: Optional[str] = None) -> str:
    """Estrae il ticker azionario o crypto dalla colonna Details/Instrument di eToro."""
    if isin and len(isin) >= 12:
        res = resolve_isin_to_ticker(isin)
        if res and res.upper() not in ["UNKNOWN", "NAN", ""]:
            return res

    d = str(details).strip()
    # Rimuove prefissi comuni come "Buy ", "Sell ", "Open ", "Close "
    for prefix in ["buy ", "sell ", "open ", "close ", "acquisto ", "vendita "]:
        if d.lower().startswith(prefix):
            d = d[len(prefix):].strip()

    # Rimuove suffissi es. " / USD", " / EUR"
    if " / " in d:
        d = d.split(" / ")[0].strip()
    elif "/" in d:
        d = d.split("/")[0].strip()

    # Se c'è uno spazio e un codice ticker tra parentesi es. "Apple Inc (AAPL)"
    if "(" in d and ")" in d:
        inside = d[d.find("(") + 1 : d.find(")")].strip()
        if inside and len(inside) <= 6:
            return inside.upper()

    return resolve_isin_to_ticker(d, fallback_symbol=d)


def _detect_etoro_asset_class(details: str, asset_type: str) -> str:
    """Rileva l'asset class della posizione eToro."""
    comb = f"{details} {asset_type}".lower()
    if any(k in comb for k in ["crypto", "btc", "eth", "sol", "bitcoin", "ethereum", "xrp"]):
        return "crypto"
    if any(k in comb for k in ["etf", "ishares", "vanguard", "invesco", "spdr"]):
        return "etf"
    if any(k in comb for k in ["bond", "treasury", "obbligaz"]):
        return "bond"
    return "stock"


def _parse_etoro_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """
    Estrae uno o due record (nel caso di Closed Positions con Open Date e Close Date distinte)
    da una riga eToro.
    """
    records = []
    raw_action = str(row.get(cols["action"], "")).strip() if cols["action"] else ""
    raw_details = str(row.get(cols["details"], "")).strip() if cols["details"] else ""
    raw_isin = str(row.get(cols["isin"], "")).strip() if cols["isin"] else ""
    raw_asset_type = str(row.get(cols["asset_type"], "")).strip() if cols["asset_type"] else ""

    ticker = _extract_ticker_from_etoro_details(raw_details or raw_action, raw_isin)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return []

    asset_class = _detect_etoro_asset_class(raw_details or raw_action, raw_asset_type)
    curr = str(row.get(cols["currency"], "USD")).strip().upper() if cols["currency"] else "USD"
    if not curr or curr in ["NAN", "NONE", ""]:
        curr = "USD"

    qty = abs(clean_numeric_value(row.get(cols["units"]), default=0.0)) if cols["units"] else 0.0
    open_rate = abs(clean_numeric_value(row.get(cols["open_rate"]), default=0.0)) if cols["open_rate"] else 0.0
    close_rate = abs(clean_numeric_value(row.get(cols["close_rate"]), default=0.0)) if cols["close_rate"] else 0.0
    amount = abs(clean_numeric_value(row.get(cols["amount"]), default=0.0)) if cols["amount"] else 0.0
    fee = abs(clean_numeric_value(row.get(cols["fee"]), default=0.0)) if cols["fee"] else 0.0

    # Caso 1: È un dividendo
    if _classify_etoro_action(raw_action or raw_details) == "dividend":
        tx_date = clean_date_value(row.get(cols["date"]) or row.get(cols["close_date"]) or row.get(cols["open_date"]))
        if tx_date:
            div_amount = amount or abs(clean_numeric_value(row.get(cols["profit"]), default=0.0)) if cols["profit"] else amount
            records.append({
                "tx_date": tx_date,
                "ticker": ticker,
                "tx_type": "dividend",
                "quantity": 1.0,
                "price": div_amount,
                "currency": curr,
                "fees": fee,
                "asset_class": asset_class,
                "notes": f"eToro Dividend: {raw_details or ticker}"
            })
        return records

    # Caso 2: È una Closed Position con Open Date e Close Date (genera un Buy e un Sell)
    open_date = clean_date_value(row.get(cols["open_date"])) if cols["open_date"] else None
    close_date = clean_date_value(row.get(cols["close_date"])) if cols["close_date"] else None

    if open_date and close_date and open_rate > 0 and close_rate > 0:
        if qty == 0.0 and amount > 0:
            qty = amount / open_rate

        if qty > 0:
            # Transazione Buy iniziale
            records.append({
                "tx_date": open_date,
                "ticker": ticker,
                "tx_type": "buy",
                "quantity": qty,
                "price": open_rate,
                "currency": curr,
                "fees": fee / 2.0 if fee > 0 else 0.0,
                "asset_class": asset_class,
                "notes": f"eToro Open: {raw_details or ticker}"
            })
            # Transazione Sell successiva
            records.append({
                "tx_date": close_date,
                "ticker": ticker,
                "tx_type": "sell",
                "quantity": qty,
                "price": close_rate,
                "currency": curr,
                "fees": fee / 2.0 if fee > 0 else 0.0,
                "asset_class": asset_class,
                "notes": f"eToro Close: {raw_details or ticker}"
            })
        return records

    # Caso 3: Record singolo di transazione
    single_date = clean_date_value(row.get(cols["date"]) or row.get(cols["open_date"]) or row.get(cols["close_date"]))
    if not single_date:
        return []

    tx_type = _classify_etoro_action(raw_action or raw_details)
    if not tx_type:
        return []

    price = open_rate or close_rate
    if price == 0.0 and qty > 0 and amount > 0:
        price = amount / qty
    elif qty == 0.0 and price > 0 and amount > 0:
        qty = amount / price

    if qty == 0.0:
        return []

    records.append({
        "tx_date": single_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fee,
        "asset_class": asset_class,
        "notes": f"eToro: {raw_details or ticker}"
    })
    return records


def parse_etoro_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame esportato da eToro nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    # Mappatura flessibile delle intestazioni di colonna eToro
    def find_col(*aliases) -> Optional[str]:
        for col in df.columns:
            for alias in aliases:
                if alias in col:
                    return col
        return None

    cols = {
        "date": find_col("date", "data", "timestamp"),
        "open_date": find_col("open date", "data apertura", "open time", "opened"),
        "close_date": find_col("close date", "data chiusura", "close time", "closed"),
        "action": find_col("action", "azione", "type", "tipo"),
        "details": find_col("details", "dettagli", "instrument", "strumento", "name", "nome", "item"),
        "isin": find_col("isin"),
        "asset_type": find_col("asset type", "asset class", "tipo asset"),
        "units": find_col("units", "unità", "unita", "shares", "quantità", "quantita", "amount (shares)"),
        "open_rate": find_col("open rate", "prezzo apertura", "open price", "rate"),
        "close_rate": find_col("close rate", "prezzo chiusura", "close price"),
        "amount": find_col("amount", "importo", "invested", "investito", "total"),
        "profit": find_col("profit", "profitto", "p/l", "realized"),
        "fee": find_col("spread", "fee", "fees", "commissioni", "roll fee", "overnight"),
        "currency": find_col("currency", "valuta", "divisa"),
    }

    normalized_rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        try:
            records = _parse_etoro_row(row, cols)
            if records:
                normalized_rows.extend(records)
        except Exception as e:
            logger.debug(f"[eToro Adapter] Errore parsing riga: {e}")
            continue

    if not normalized_rows:
        return pd.DataFrame()

    res = pd.DataFrame(normalized_rows)
    # Ordinamento cronologico
    res = res.sort_values(by=["tx_date", "tx_type"]).reset_index(drop=True)
    return res
