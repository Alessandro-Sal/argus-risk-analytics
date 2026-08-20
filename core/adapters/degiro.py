"""
ARGUS — Risk Analytics Platform
Core Module: DeGiro CSV Adapter
Parsing e normalizzazione dei report esportati da DeGiro (Transazioni).
"""

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from core.adapters.isin_resolver import (
    clean_date_value,
    clean_numeric_value,
    resolve_isin_to_ticker,
)

logger = logging.getLogger(__name__)


def _locate_degiro_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Identifica le colonne chiave nel file esportato da DeGiro."""
    date_col = next((c for c in df.columns if c in ["data", "date"]), None)
    product_col = next((c for c in df.columns if c in ["prodotto", "product"]), None)
    isin_col = next((c for c in df.columns if "isin" in c), None)
    qty_col = next((c for c in df.columns if "quantit" in c or "quantity" in c), None)
    price_col = next((c for c in df.columns if c in ["prezzo", "price", "quotazione"]), None)

    currency_col = None
    if price_col:
        price_idx = df.columns.get_loc(price_col)
        if price_idx + 1 < len(df.columns):
            currency_col = df.columns[price_idx + 1]

    fees_col = next((c for c in df.columns if any(k in c for k in ["costi di transazione", "commissioni", "transaction costs", "fee"])), None)
    return date_col, product_col, isin_col, qty_col, price_col, currency_col, fees_col


def _clean_numeric_series(series: Optional[pd.Series], length: int) -> pd.Series:
    """Pulisce una serie numerica da stringhe con separatori europei."""
    if series is None or series.empty:
        return pd.Series([0.0] * length)
    return series.apply(clean_numeric_value)


def parse_degiro_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Legge il dataframe grezzo esportato da Degiro (Transazioni)
    e lo formatta nello standard compatibile con il validator.py del progetto.
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.lower()

    date_col, product_col, isin_col, qty_col, price_col, currency_col, fees_col = _locate_degiro_columns(df)

    if not all([date_col, product_col, isin_col]):
        raise ValueError("Il file non sembra un export valido delle Transazioni Degiro. Mancano colonne chiave (Data, Prodotto, ISIN).")

    df_out = pd.DataFrame()
    df_out["tx_date"] = df[date_col].apply(clean_date_value)
    df_out["ticker"] = df[isin_col].apply(lambda isin: resolve_isin_to_ticker(isin, fallback_symbol=isin))

    qty_series = _clean_numeric_series(df[qty_col], len(df)) if qty_col else pd.Series([0.0] * len(df))
    price_series = _clean_numeric_series(df[price_col], len(df)) if price_col else pd.Series([0.0] * len(df))
    fees_series = _clean_numeric_series(df[fees_col], len(df)) if fees_col else pd.Series([0.0] * len(df))

    conditions = [
        qty_series > 0,
        qty_series < 0,
        df[product_col].astype(str).str.lower().str.contains("dividend|dividendo", na=False)
    ]
    choices = ["buy", "sell", "dividend"]
    df_out["tx_type"] = np.select(conditions, choices, default="unknown")

    mask_valid = df_out["tx_type"] != "unknown"
    df_out = df_out[mask_valid].copy()
    qty_series = qty_series[mask_valid]
    price_series = price_series[mask_valid]
    fees_series = fees_series[mask_valid]
    df = df[mask_valid].copy()

    df_out["quantity"] = qty_series.abs()
    df_out["price"] = price_series
    df_out["currency"] = df[currency_col].astype(str).str.strip().str.upper() if currency_col else "EUR"
    df_out["fees"] = fees_series.abs()
    df_out["asset_class"] = None
    df_out["notes"] = df[product_col]

    return df_out.reset_index(drop=True)
