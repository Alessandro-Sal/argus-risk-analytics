"""
ARGUS — Risk Analytics Platform
Core Module: Trade Republic CSV Adapter
Parsing e normalizzazione dei report esportati da Trade Republic (Estratti Conto / Transazioni / PAC).
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


def _classify_tr_tx_type(type_and_name: str) -> Optional[str]:
    """Classifica il tipo di operazione per Trade Republic."""
    tn = type_and_name.lower()
    if any(k in tn for k in ["dividend", "dividende", "dividendo", "ausschüttung", "cedola", "distribution"]):
        return "dividend"
    if any(k in tn for k in ["split", "frazionamento", "aktienteilung", "raggruppamento", "reverse split", "fusione", "merger", "spinoff", "scissione"]):
        return "split"
    if any(k in tn for k in ["sell", "verkauf", "vendita"]):
        return "sell"
    if any(k in tn for k in ["buy", "kauf", "acquisto", "savings_plan", "savings plan", "sparplan", "pac", "order"]):
        return "buy"
    if any(k in tn for k in ["deposit", "einzahlung", "versamento", "interest", "zinsen", "interessi"]):
        return None
    return "buy"


def _parse_tr_row(row: pd.Series, cols: Dict[str, Optional[str]]) -> Optional[Dict[str, Any]]:
    """Estrae e normalizza un singolo record da una riga Trade Republic."""
    raw_date = row.get(cols["date"])
    tx_date = clean_date_value(raw_date)
    if not tx_date:
        return None

    raw_type = str(row.get(cols["type"], "")).strip().lower() if cols["type"] else ""
    raw_name = str(row.get(cols["name"], "")).strip() if cols["name"] else ""
    type_and_name = f"{raw_type} {raw_name}".lower()

    tx_type = _classify_tr_tx_type(type_and_name)
    if not tx_type:
        return None

    raw_isin = str(row.get(cols["isin"], "")).strip() if cols["isin"] else ""
    ticker = resolve_isin_to_ticker(raw_isin or raw_name, fallback_symbol=raw_name or raw_isin)
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

    fees = abs(clean_numeric_value(row.get(cols["fee"]), default=1.0 if tx_type in ["buy", "sell"] else 0.0)) if cols["fee"] else 0.0
    curr = "EUR"
    asset_class = "crypto" if "crypto" in type_and_name or "bitcoin" in type_and_name or "ethereum" in type_and_name else (
        "etf" if any(k in raw_name.lower() for k in ["etf", "ucits", "ishares", "vanguard", "core"]) else "stock"
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
        "notes": f"Trade Republic: {raw_name or ticker}"
    }


def parse_traderepublic_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalizza un DataFrame grezzo esportato da Trade Republic nello standard ARGUS."""
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()

    date_col = next((c for c in df.columns if any(k in c for k in ["timestamp", "date", "datum", "data"])), None)
    type_col = next((c for c in df.columns if any(k in c for k in ["type", "typ", "tipo", "action", "activity"])), None)
    isin_col = next((c for c in df.columns if any(k in c for k in ["isin", "wkn", "identifier", "ticker"])), None)
    name_col = next((c for c in df.columns if any(k in c for k in ["name", "wertpapier", "titolo", "title", "description"])), None)
    shares_col = next((c for c in df.columns if any(k in c for k in ["shares", "stueck", "stück", "quantit", "quantity", "anzahl"])), None)
    price_col = next((c for c in df.columns if any(k in c for k in ["price", "kurs", "prezzo", "share_price"])), None)
    amount_col = next((c for c in df.columns if any(k in c for k in ["amount", "betrag", "importo", "total", "controvalore"])), None)
    fee_col = next((c for c in df.columns if any(k in c for k in ["fee", "gebuehr", "gebühr", "spese", "commission"])), None)

    if not date_col or (not isin_col and not name_col):
        raise ValueError("Il file non sembra un export valido di Trade Republic (colonne Data o ISIN/Nome mancanti).")

    cols = {
        "date": date_col, "type": type_col, "isin": isin_col, "name": name_col,
        "shares": shares_col, "price": price_col, "amount": amount_col, "fee": fee_col
    }

    records = []
    for _, row in df.iterrows():
        rec = _parse_tr_row(row, cols)
        if rec:
            records.append(rec)

    if not records:
        raise ValueError("Nessuna transazione valida estratta dal file Trade Republic.")

    df_out = pd.DataFrame(records)
    return df_out.sort_values(by="tx_date").reset_index(drop=True)
