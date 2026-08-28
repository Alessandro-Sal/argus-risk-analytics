"""
ARGUS — Risk Analytics Platform
Core Module: Directa SIM CSV Adapter
Parsing e normalizzazione dei report esportati da Directa SIM (Ordini Eseguiti / Estratto Conto).
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


def _classify_directa_tx_type(raw_type: str) -> Optional[str]:
    """Classifica la tipologia di operazione da Directa SIM."""
    rt = str(raw_type).strip().lower()
    if any(k in rt for k in ["dividendo", "cedola", "dividend", "accredito div"]) or rt == "div":
        return "dividend"
    if any(k in rt for k in ["split", "frazionamento", "raggruppamento", "reverse split", "fusione", "incorporazione", "scambio", "merger", "scissione", "spinoff"]):
        return "split"
    if any(k in rt for k in ["vende", "vendita", "sell", "ven"]) or rt == "v":
        return "sell"
    if any(k in rt for k in ["compra", "acquisto", "buy", "acq"]) or rt == "c":
        return "buy"
    if any(k in rt for k in ["bonifico", "prelievo", "versamento", "imposta", "bollo"]):
        return None
    return "buy"


def _parse_directa_row(row: pd.Series, cols: Dict[str, Optional[str]], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo record da una riga Directa SIM."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    tx_type = _classify_directa_tx_type(row.get(cols["type"], "buy"))
    if not tx_type:
        return None

    raw_sym = str(row.get(cols["ticker"], "")).strip() if cols["ticker"] else ""
    raw_desc = str(row.get(cols["desc"], "")).strip() if cols["desc"] else ""
    ticker = resolve_isin_to_ticker(raw_sym or raw_desc, fallback_symbol=raw_sym or raw_desc)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return None

    qty = abs(clean_numeric_value(row.get(cols["qty"]), default=1.0 if tx_type == "dividend" else 0.0))
    price = abs(clean_numeric_value(row.get(cols["price"]), default=0.0))

    if tx_type == "dividend" and price == 0.0:
        val_col = next((c for c in df.columns if any(k in c for k in ["controvalore", "importo", "totale"])), None)
        if val_col:
            price = abs(clean_numeric_value(row.get(val_col), default=0.0))
        qty = 1.0

    if qty == 0.0 and tx_type != "dividend":
        return None

    fees = abs(clean_numeric_value(row.get(cols["fee"]), default=0.0)) if cols["fee"] else 0.0
    curr = str(row.get(cols["curr"], "EUR")).strip().upper() if cols["curr"] else "EUR"
    if not curr or curr in ["NAN", "NONE", ""]:
        curr = "EUR"

    asset_class = "etf" if any(k in raw_desc.lower() for k in ["etf", "ucits", "ishares", "vanguard"]) else "stock"

    return {
        "tx_date": tx_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fees,
        "asset_class": asset_class,
        "notes": f"Directa: {raw_desc or ticker}"
    }


def parse_directa_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame grezzo esportato da Directa SIM nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    date_col = next((c for c in df.columns if c in ["data", "date", "giorno"] or "data operazione" in c), None)
    if not date_col:
        date_col = next((c for c in df.columns if "data" in c or "date" in c), None)

    type_col = next((c for c in df.columns if c != date_col and any(k in c for k in ["operazione", "tipo operazione", "tipo", "type", "segno"])), None)
    ticker_col = next((c for c in df.columns if any(k in c for k in ["simbolo", "ticker", "codice", "isin"])), None)
    desc_col = next((c for c in df.columns if any(k in c for k in ["titolo", "descrizione", "name", "prodotto"])), None)
    qty_col = next((c for c in df.columns if any(k in c for k in ["quantit", "quantita", "q.ta", "qty", "volume"])), None)
    price_col = next((c for c in df.columns if any(k in c for k in ["prezzo", "price", "quotazione", "prezzo medio"])), None)
    fee_col = next((c for c in df.columns if any(k in c for k in ["commission", "spese", "fee", "costi"])), None)
    curr_col = next((c for c in df.columns if any(k in c for k in ["divisa", "valuta", "currency"])), None)

    if not date_col or (not ticker_col and not desc_col):
        raise ValueError("Il file non sembra un export valido di Directa SIM (colonne Data o Simbolo/Titolo non trovate).")

    cols = {
        "date": date_col, "type": type_col, "ticker": ticker_col,
        "desc": desc_col, "qty": qty_col, "price": price_col,
        "fee": fee_col, "curr": curr_col
    }

    records = []
    for _, row in df.iterrows():
        rec = _parse_directa_row(row, cols, df)
        if rec:
            records.append(rec)

    if not records:
        raise ValueError("Nessuna transazione valida estratta dal file Directa SIM.")

    df_out = pd.DataFrame(records)
    return df_out.sort_values(by="tx_date").reset_index(drop=True)
