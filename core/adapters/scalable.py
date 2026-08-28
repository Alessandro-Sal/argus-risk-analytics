"""
ARGUS — Risk Analytics Platform
Core Module: Scalable Capital CSV Adapter
Parsing e normalizzazione dei report esportati da Scalable Capital / Baader Bank.
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


def _classify_scalable_tx_type(type_and_sec: str) -> Optional[str]:
    """Classifica la tipologia di transazione per Scalable Capital."""
    ts = type_and_sec.lower()
    if any(k in ts for k in ["dividend", "dividende", "dividendo", "ausschüttung", "ertrag", "cedola"]):
        return "dividend"
    if any(k in ts for k in ["split", "frazionamento", "aktienteilung", "raggruppamento", "reverse split", "fusione", "merger", "spinoff", "scissione"]):
        return "split"
    if any(k in ts for k in ["sell", "verkauf", "vendita", "orderausführung verkauf"]):
        return "sell"
    if any(k in ts for k in ["buy", "kauf", "acquisto", "sparplan", "savings", "orderausführung kauf"]):
        return "buy"
    if any(k in ts for k in ["einzahlung", "auszahlung", "deposit", "withdrawal", "zinsen", "interest"]):
        return None
    return "buy"


def _parse_scalable_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo record da una riga Scalable Capital."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    raw_type = str(row.get(cols["type"], "")).strip().lower() if cols["type"] else ""
    raw_sec = str(row.get(cols["sec"], "")).strip() if cols["sec"] else ""
    type_and_sec = f"{raw_type} {raw_sec}".lower()

    tx_type = _classify_scalable_tx_type(type_and_sec)
    if not tx_type:
        return None

    raw_isin = str(row.get(cols["isin"], "")).strip() if cols["isin"] else ""
    ticker = resolve_isin_to_ticker(raw_isin or raw_sec, fallback_symbol=raw_sec or raw_isin)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return None

    qty = abs(clean_numeric_value(row.get(cols["shares"]), default=1.0 if tx_type == "dividend" else 0.0))
    price = abs(clean_numeric_value(row.get(cols["price"]), default=0.0))

    if (price == 0.0 or tx_type == "dividend") and cols["amount"]:
        imp = abs(clean_numeric_value(row.get(cols["amount"]), default=0.0))
        if tx_type == "dividend":
            price = imp
            qty = 1.0
        elif qty > 0 and price == 0.0:
            price = imp / qty

    if qty == 0.0 and tx_type != "dividend":
        return None

    fees = abs(clean_numeric_value(row.get(cols["fee"]), default=0.0)) if cols["fee"] else 0.0
    curr = str(row.get(cols["curr"], "EUR")).strip().upper() if cols["curr"] else "EUR"
    if not curr or curr in ["NAN", "NONE", ""]:
        curr = "EUR"

    asset_class = "crypto" if "crypto" in type_and_sec else (
        "etf" if any(k in raw_sec.lower() for k in ["etf", "ucits", "ishares", "vanguard", "xtrackers", "amundi"]) else "stock"
    )

    return {
        "tx_date": tx_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fees,
        "asset_class": asset_class,
        "notes": f"Scalable: {raw_sec or ticker}"
    }


def parse_scalable_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame grezzo esportato da Scalable Capital nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    date_col = next((c for c in df.columns if any(k in c for k in ["date", "datum", "data", "buchungstag", "valuta"])), None)
    type_col = next((c for c in df.columns if any(k in c for k in ["type", "typ", "tipo", "transaktionsart", "order type"])), None)
    isin_col = next((c for c in df.columns if any(k in c for k in ["isin", "wkn", "identifier", "ticker"])), None)
    sec_col = next((c for c in df.columns if any(k in c for k in ["security", "wertpapier", "name", "titolo", "bezeichnung"])), None)
    shares_col = next((c for c in df.columns if any(k in c for k in ["shares", "stueck", "stück", "quantit", "quantity", "anzahl", "nominale"])), None)
    price_col = next((c for c in df.columns if any(k in c for k in ["price", "kurs", "prezzo", "ausführungskurs"])), None)
    amount_col = next((c for c in df.columns if any(k in c for k in ["amount", "betrag", "importo", "total", "kurswert"])), None)
    fee_col = next((c for c in df.columns if any(k in c for k in ["fee", "gebuehr", "gebühr", "kosten", "spese", "commission"])), None)
    curr_col = next((c for c in df.columns if any(k in c for k in ["currency", "währung", "valuta", "divisa"])), None)

    if not date_col or (not isin_col and not sec_col):
        raise ValueError("Il file non sembra un export valido di Scalable Capital (colonne Data o ISIN/Security mancanti).")

    cols = {
        "date": date_col, "type": type_col, "isin": isin_col, "sec": sec_col,
        "shares": shares_col, "price": price_col, "amount": amount_col,
        "fee": fee_col, "curr": curr_col
    }

    records = []
    for _, row in df.iterrows():
        rec = _parse_scalable_row(row, cols)
        if rec:
            records.append(rec)

    if not records:
        raise ValueError("Nessuna transazione valida estratta dal file Scalable Capital.")

    df_out = pd.DataFrame(records)
    return df_out.sort_values(by="tx_date").reset_index(drop=True)
