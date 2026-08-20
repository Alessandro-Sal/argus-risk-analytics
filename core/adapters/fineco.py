"""
ARGUS — Risk Analytics Platform
Core Module: Fineco Bank CSV Adapter
Parsing e normalizzazione dei report esportati da Fineco Bank (Movimenti Conto Trading / Ordini Eseguiti).
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


def _classify_fineco_tx_type(type_and_desc: str) -> Optional[str]:
    """Classifica la tipologia di operazione da Fineco Bank."""
    td = type_and_desc.lower()
    if any(k in td for k in ["dividendo", "cedola", "dividend", "accredito dividendo", "accredito cedola"]):
        return "dividend"
    if any(k in td for k in ["split", "frazionamento"]):
        return "split"
    if any(k in td for k in ["vendi", "vendita", "ven", "sell"]):
        return "sell"
    if any(k in td for k in ["compra", "acquisto", "acq", "buy"]):
        return "buy"
    if any(k in td for k in ["bonifico", "prelievo", "versamento", "imposta", "bollo", "ritenuta"]):
        return None
    return "buy"


def _parse_fineco_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo record da una riga Fineco Bank."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    raw_type = str(row.get(cols["type"], "")).strip().lower() if cols["type"] else ""
    raw_desc = str(row.get(cols["desc"], "")).strip() if cols["desc"] else ""
    type_and_desc = f"{raw_type} {raw_desc}".lower()

    tx_type = _classify_fineco_tx_type(type_and_desc)
    if not tx_type:
        return None

    raw_isin = str(row.get(cols["isin"], "")).strip() if cols["isin"] else ""
    ticker = resolve_isin_to_ticker(raw_isin or raw_desc, fallback_symbol=raw_desc or raw_isin)
    if not ticker or ticker.upper() in ["NAN", "NONE", "UNKNOWN", ""]:
        return None

    qty = abs(clean_numeric_value(row.get(cols["qty"]), default=1.0 if tx_type == "dividend" else 0.0))
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

    asset_class = "etf" if any(k in raw_desc.lower() for k in ["etf", "ucits", "ishares", "vanguard", "lyxor"]) else "stock"

    return {
        "tx_date": tx_date,
        "ticker": ticker,
        "tx_type": tx_type,
        "quantity": qty,
        "price": price,
        "currency": curr,
        "fees": fees,
        "asset_class": asset_class,
        "notes": f"Fineco: {raw_desc or ticker}"
    }


def parse_fineco_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame grezzo esportato da Fineco Bank nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    if any(str(c).startswith("Unnamed") for c in df.columns[:3]):
        for idx, row in df.iterrows():
            row_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
            if any(k in row_str for k in ["data operazione", "data valuta", "isin", "titolo", "descrizione"]):
                df.columns = [str(v).strip().lower() for v in row.values]
                df = df.iloc[idx + 1:].reset_index(drop=True)
                break

    df.columns = df.columns.astype(str).str.strip().str.lower()

    date_col = next((c for c in df.columns if c in ["data operazione", "data valuta", "data", "date"]), None)
    if not date_col:
        date_col = next((c for c in df.columns if "data" in c or "date" in c), None)

    type_col = next((c for c in df.columns if c != date_col and any(k in c for k in ["tipo operazione", "operazione", "tipo", "descrizione operazione"])), None)
    isin_col = next((c for c in df.columns if any(k in c for k in ["isin", "codice titolo", "codice isin", "simbolo", "ticker"])), None)
    desc_col = next((c for c in df.columns if any(k in c for k in ["titolo", "descrizione", "name", "prodotto"])), None)
    qty_col = next((c for c in df.columns if any(k in c for k in ["quantit", "quantita", "q.ta", "volume", "shares"])), None)
    price_col = next((c for c in df.columns if any(k in c for k in ["prezzo", "price", "quotazione", "prezzo medio"])), None)
    amount_col = next((c for c in df.columns if any(k in c for k in ["importo", "controvalore", "totale"])), None)
    fee_col = next((c for c in df.columns if any(k in c for k in ["commission", "spese", "fee", "costi"])), None)
    curr_col = next((c for c in df.columns if any(k in c for k in ["divisa", "valuta", "currency"])), None)

    if not date_col or (not isin_col and not desc_col):
        raise ValueError("Il file non sembra un export valido di Fineco Bank (colonne Data o ISIN/Titolo non trovate).")

    cols = {
        "date": date_col, "type": type_col, "isin": isin_col,
        "desc": desc_col, "qty": qty_col, "price": price_col,
        "amount": amount_col, "fee": fee_col, "curr": curr_col
    }

    records = []
    for _, row in df.iterrows():
        rec = _parse_fineco_row(row, cols)
        if rec:
            records.append(rec)

    if not records:
        raise ValueError("Nessuna transazione valida estratta dal file Fineco Bank.")

    df_out = pd.DataFrame(records)
    return df_out.sort_values(by="tx_date").reset_index(drop=True)
