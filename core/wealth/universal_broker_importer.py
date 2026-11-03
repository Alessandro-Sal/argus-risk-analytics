"""
ARGUS — Universal Broker Ingestion & Normalization Engine
=========================================================
Drag & Drop CSV/XLSX parser for major Italian and European brokers:
- Directa SIM (Movimenti / Eseguiti)
- FinecoBank (Dossier Titoli / Trading & Movimenti Titoli)
- Degiro (Account Statement / Transactions Export)
- Scalable Capital (Securities Transactions CSV)
- Trade Republic (Activity & Transactions CSV)
- Interactive Brokers (IBKR Activity Statement / Flex Query Trades)

Features:
- Automatic broker signature detection
- Multi-delimiter & European comma decimal normalization
- Automatic ticker & ISIN extraction
- Idempotent SHA-256 deduplication
- Automatic asset resolution and insertion into 'assets' & 'transactions'
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)

# ── BROKER SIGNATURE DEFINITIONS ──────────────────────────────
BROKER_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "DIRECTA": {
        "name": "Directa SIM",
        "keywords": ["directa", "nota informativa", "eseguiti", "tipo operazione", "segno", "commissioni"],
        "detect_cols": ["operazione", "data valuta", "prezzo", "quantità", "isin", "titolo", "eseguito"],
    },
    "FINECO": {
        "name": "FinecoBank",
        "keywords": ["fineco", "dossier titoli", "compravendita titoli", "eseguito", "movimenti titoli"],
        "detect_cols": ["data operazione", "titolo", "isin", "quantità", "prezzo", "commissioni", "controvalore"],
    },
    "DEGIRO": {
        "name": "Degiro",
        "keywords": ["degiro", "corso", "variazione", "valore locale", "costi di transazione", "flatex"],
        "detect_cols": ["data", "ora", "prodotto", "isin", "descrizione", "valore"],
    },
    "SCALABLE": {
        "name": "Scalable Capital",
        "keywords": ["scalable", "security name", "execution price", "total amount", "shares"],
        "detect_cols": ["date", "type", "isin", "shares", "price", "total"],
    },
    "TRADE_REPUBLIC": {
        "name": "Trade Republic",
        "keywords": ["trade republic", "settlement date", "order type", "units", "shares"],
        "detect_cols": ["timestamp", "type", "isin", "units", "price", "amount"],
    },
    "IBKR": {
        "name": "Interactive Brokers (IBKR)",
        "keywords": ["interactive brokers", "ibkr", "statement", "trades", "realized p/l", "proceeds"],
        "detect_cols": ["symbol", "date/time", "quantity", "t. price", "c. price", "proceeds", "comm/fee"],
    },
}


def _clean_numeric(val: Any) -> float:
    """Normalizza numeri in float gestendo sia virgola italiana che punto decimale."""
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("€", "").replace("$", "").replace("£", "").replace(" ", "")
    if not s or s.lower() in ["nan", "none", "null", "-", "--"]:
        return 0.0
    # Gestione formato italiano (1.234,56) vs US (1,234.56)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            # es. 1.250,50
            s = s.replace(".", "").replace(",", ".")
        else:
            # es. 1,250.50
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_date_safe(val: Any) -> Optional[str]:
    """Converte date in stringa ISO YYYY-MM-DD."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    # Se datetime o timestamp
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.isoformat()
    # Pulisci orari se presenti (es. 2024-01-15 14:30:00 -> 2024-01-15)
    s_clean = s.split(" ")[0].split("T")[0]
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s_clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _compute_tx_hash(broker: str, tx_date: str, isin_or_ticker: str, tx_type: str, shares: float, price: float, total: float) -> str:
    """Genera un hash SHA-256 univoco per deduplicazione idempotente."""
    raw = f"{broker.upper()}_{tx_date}_{isin_or_ticker.upper()}_{tx_type.upper()}_{shares:.6f}_{price:.6f}_{total:.2f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def detect_broker_and_format(df_raw: pd.DataFrame, file_text_sample: str = "") -> str:
    """Riconosce automaticamente il broker analizzando header di colonna e testo grezzo."""
    text_lower = (file_text_sample or "").lower()
    cols_lower = [str(c).lower().strip() for c in df_raw.columns]

    scores: Dict[str, int] = dict.fromkeys(BROKER_SIGNATURES, 0)

    for b_key, b_info in BROKER_SIGNATURES.items():
        # Punteggio parole chiave nel testo o nome file
        for kw in b_info["keywords"]:
            if kw in text_lower:
                scores[b_key] += 3

        # Punteggio colonne rilevate
        for d_col in b_info["detect_cols"]:
            if any(d_col in c for c in cols_lower):
                scores[b_key] += 2

    best_match = max(scores, key=lambda k: scores[k])
    if scores[best_match] >= 2:
        return best_match
    return "GENERIC_BROKER"


def _read_broker_dataframe(file_bytes_or_buffer: Any, filename: str = "") -> Tuple[pd.DataFrame, str]:
    """Legge un file CSV, TSV o XLSX restituendo il DataFrame e un campione di testo."""
    if isinstance(file_bytes_or_buffer, bytes):
        raw_bytes = file_bytes_or_buffer
    elif hasattr(file_bytes_or_buffer, "read"):
        raw_bytes = file_bytes_or_buffer.read()
    else:
        raw_bytes = b""

    # Campione testo iniziale per sniff
    sample_text = raw_bytes[:4096].decode("utf-8", errors="ignore")

    # Gestione Excel
    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(raw_bytes))
        return df, sample_text

    # Sniffing separatore CSV/TSV
    sep = ","
    if ";" in sample_text and sample_text.count(";") > sample_text.count(","):
        sep = ";"
    elif "\t" in sample_text and sample_text.count("\t") > sample_text.count(","):
        sep = "\t"

    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), sep=sep, skipinitialspace=True, dtype=str)
    except Exception:
        # Fallback senza separatore esplicito
        df = pd.read_csv(io.BytesIO(raw_bytes), engine="python", dtype=str)

    return df, sample_text


# ── SPECIFIC BROKER PARSERS ───────────────────────────────────

def _parse_directa(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Directa SIM."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    # Trova colonne chiave
    c_date = next((col_map[c] for c in col_map if "data" in c), None)
    c_type = next((col_map[c] for c in col_map if ("operazione" in c or "tipo" in c) and "data" not in c), None)
    c_desc = next((col_map[c] for c in col_map if "descrizione" in c or "titolo" in c), None)
    c_isin = next((col_map[c] for c in col_map if "isin" in c), None)
    c_qty = next((col_map[c] for c in col_map if "quantit" in c or "qta" in c), None)
    c_price = next((col_map[c] for c in col_map if "prezzo" in c or "corso" in c), None)
    c_tot = next((col_map[c] for c in col_map if "controvalore" in c or "totale" in c or "importo" in c), None)
    c_fee = next((col_map[c] for c in col_map if "commission" in c or "spese" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        raw_type = str(row.get(c_type, "")).strip().upper()
        tx_type = "BUY"
        if any(w in raw_type for w in ["VENDITA", "SELL", "VEND"]):
            tx_type = "SELL"
        elif any(w in raw_type for w in ["DIVIDEND", "CEDOLA", "DIV"]):
            tx_type = "DIVIDEND"
        elif any(w in raw_type for w in ["COMMISSION", "SPESA", "IMPOSTA"]):
            tx_type = "FEE"

        desc = str(row.get(c_desc, "")).strip() if c_desc else ""
        isin = str(row.get(c_isin, "")).strip().upper() if c_isin else ""
        if not isin or isin == "NAN":
            # Estrai eventuale ISIN da descrizione (es. 2 lettere + 10 alfanumerici)
            m_isin = re.search(r"\b([A-Z]{2}[A-Z0-9]{10})\b", desc)
            isin = m_isin.group(1) if m_isin else ""

        qty = abs(_clean_numeric(row.get(c_qty))) if c_qty else 0.0
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_tot))) if c_tot else (qty * price)
        fee = abs(_clean_numeric(row.get(c_fee))) if c_fee else 0.0

        if qty == 0.0 and tot > 0 and price > 0:
            qty = tot / price
        elif price == 0.0 and qty > 0 and tot > 0:
            price = tot / qty

        # Ticker fallback
        ticker = isin[:8] if isin else (desc.split(" ")[0] if desc else "ASSET")

        tx_hash = _compute_tx_hash("DIRECTA", t_date, isin or ticker, tx_type, qty, price, tot)
        txs.append({
            "broker": "Directa SIM",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": ticker,
            "isin": isin,
            "security_name": desc or ticker,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": fee,
            "notes": f"Directa: {raw_type} {desc}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


def _parse_fineco(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Fineco Trading / Dossier Titoli."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    c_date = next((col_map[c] for c in col_map if "data" in c and "valuta" not in c), None) or next((col_map[c] for c in col_map if "data" in c), None)
    c_type = next((col_map[c] for c in col_map if ("operazione" in c or "tipo" in c) and "data" not in c), None)
    c_desc = next((col_map[c] for c in col_map if "titolo" in c or "descrizione" in c), None)
    c_isin = next((col_map[c] for c in col_map if "isin" in c), None)
    c_qty = next((col_map[c] for c in col_map if "quantit" in c or "n. pezzi" in c), None)
    c_price = next((col_map[c] for c in col_map if "prezzo" in c or "corso" in c), None)
    c_tot = next((col_map[c] for c in col_map if "controvalore" in c or "importo" in c or "totale" in c), None)
    c_fee = next((col_map[c] for c in col_map if "commission" in c or "spese" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        raw_type = str(row.get(c_type, "")).strip().upper()
        desc = str(row.get(c_desc, "")).strip() if c_desc else ""
        isin = str(row.get(c_isin, "")).strip().upper() if c_isin else ""
        if not isin or isin == "NAN":
            m_isin = re.search(r"\b([A-Z]{2}[A-Z0-9]{10})\b", desc)
            isin = m_isin.group(1) if m_isin else ""

        tx_type = "BUY"
        if any(w in raw_type or w in desc.upper() for w in ["VENDITA", "SELL"]):
            tx_type = "SELL"
        elif any(w in raw_type or w in desc.upper() for w in ["DIVIDEND", "CEDOLA"]):
            tx_type = "DIVIDEND"

        qty = abs(_clean_numeric(row.get(c_qty))) if c_qty else 0.0
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_tot))) if c_tot else (qty * price)
        fee = abs(_clean_numeric(row.get(c_fee))) if c_fee else 0.0

        if qty == 0.0 and tot > 0 and price > 0:
            qty = tot / price
        elif price == 0.0 and qty > 0 and tot > 0:
            price = tot / qty

        ticker = isin[:8] if isin else (desc.split(" ")[0] if desc else "ASSET")
        tx_hash = _compute_tx_hash("FINECO", t_date, isin or ticker, tx_type, qty, price, tot)
        txs.append({
            "broker": "FinecoBank",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": ticker,
            "isin": isin,
            "security_name": desc or ticker,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": fee,
            "notes": f"Fineco: {raw_type} {desc}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


def _parse_degiro(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Degiro (Account / Transazioni)."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    c_date = next((col_map[c] for c in col_map if "data" in c or "date" in c), None)
    c_desc = next((col_map[c] for c in col_map if "prodotto" in c or "product" in c or "descrizione" in c), None)
    c_isin = next((col_map[c] for c in col_map if "isin" in c), None)
    c_qty = next((col_map[c] for c in col_map if "variazione" in c or "quantit" in c or "shares" in c), None)
    c_price = next((col_map[c] for c in col_map if "corso" in c or "prezzo" in c or "price" in c), None)
    c_tot = next((col_map[c] for c in col_map if "valore locale" in c or "valore" in c or "totale" in c), None)
    c_fee = next((col_map[c] for c in col_map if "costi" in c or "fee" in c or "commission" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        desc = str(row.get(c_desc, "")).strip() if c_desc else ""
        isin = str(row.get(c_isin, "")).strip().upper() if c_isin else ""
        raw_qty = _clean_numeric(row.get(c_qty)) if c_qty else 0.0

        tx_type = "BUY" if raw_qty >= 0 else "SELL"
        if "dividend" in desc.lower() or "cedola" in desc.lower():
            tx_type = "DIVIDEND"

        qty = abs(raw_qty)
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_tot))) if c_tot else (qty * price)
        fee = abs(_clean_numeric(row.get(c_fee))) if c_fee else 0.0

        ticker = isin[:8] if isin else (desc.split(" ")[0] if desc else "ASSET")
        tx_hash = _compute_tx_hash("DEGIRO", t_date, isin or ticker, tx_type, qty, price, tot)
        txs.append({
            "broker": "Degiro",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": ticker,
            "isin": isin,
            "security_name": desc or ticker,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": fee,
            "notes": f"Degiro: {desc}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


def _parse_scalable(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Scalable Capital."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    c_date = next((col_map[c] for c in col_map if "date" in c or "datum" in c), None)
    c_type = next((col_map[c] for c in col_map if "type" in c or "typ" in c), None)
    c_desc = next((col_map[c] for c in col_map if "security" in c or "name" in c or "wertpapier" in c), None)
    c_isin = next((col_map[c] for c in col_map if "isin" in c), None)
    c_qty = next((col_map[c] for c in col_map if "shares" in c or "units" in c or "stück" in c), None)
    c_price = next((col_map[c] for c in col_map if "price" in c or "kurs" in c), None)
    c_tot = next((col_map[c] for c in col_map if "total" in c or "amount" in c or "betrag" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        raw_type = str(row.get(c_type, "")).strip().upper()
        desc = str(row.get(c_desc, "")).strip() if c_desc else ""
        isin = str(row.get(c_isin, "")).strip().upper() if c_isin else ""

        tx_type = "BUY"
        if any(w in raw_type for w in ["SELL", "VERKAUF", "VENDITA"]):
            tx_type = "SELL"
        elif any(w in raw_type for w in ["DIVIDEND", "DISTRIBUTION", "AUSSCHÜTTUNG"]):
            tx_type = "DIVIDEND"

        qty = abs(_clean_numeric(row.get(c_qty))) if c_qty else 0.0
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_tot))) if c_tot else (qty * price)

        ticker = isin[:8] if isin else (desc.split(" ")[0] if desc else "ASSET")
        tx_hash = _compute_tx_hash("SCALABLE", t_date, isin or ticker, tx_type, qty, price, tot)
        txs.append({
            "broker": "Scalable Capital",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": ticker,
            "isin": isin,
            "security_name": desc or ticker,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": 0.0,
            "notes": f"Scalable: {raw_type} {desc}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


def _parse_trade_republic(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Trade Republic."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    c_date = next((col_map[c] for c in col_map if "date" in c or "timestamp" in c or "datum" in c), None)
    c_type = next((col_map[c] for c in col_map if "type" in c or "typ" in c), None)
    c_desc = next((col_map[c] for c in col_map if "name" in c or "asset" in c or "titel" in c), None)
    c_isin = next((col_map[c] for c in col_map if "isin" in c), None)
    c_qty = next((col_map[c] for c in col_map if "units" in c or "shares" in c or "anzahl" in c), None)
    c_price = next((col_map[c] for c in col_map if "price" in c or "kurs" in c), None)
    c_tot = next((col_map[c] for c in col_map if "amount" in c or "betrag" in c or "total" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        raw_type = str(row.get(c_type, "")).strip().upper()
        desc = str(row.get(c_desc, "")).strip() if c_desc else ""
        isin = str(row.get(c_isin, "")).strip().upper() if c_isin else ""

        tx_type = "BUY"
        if any(w in raw_type for w in ["SELL", "VERKAUF"]):
            tx_type = "SELL"
        elif any(w in raw_type for w in ["DIVIDEND", "ZINS", "INTEREST"]):
            tx_type = "DIVIDEND"

        qty = abs(_clean_numeric(row.get(c_qty))) if c_qty else 0.0
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_tot))) if c_tot else (qty * price)

        ticker = isin[:8] if isin else (desc.split(" ")[0] if desc else "ASSET")
        tx_hash = _compute_tx_hash("TRADE_REPUBLIC", t_date, isin or ticker, tx_type, qty, price, tot)
        txs.append({
            "broker": "Trade Republic",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": ticker,
            "isin": isin,
            "security_name": desc or ticker,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": 1.0,  # Trade Republic 1€ standard fee
            "notes": f"Trade Republic: {raw_type} {desc}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


def _parse_ibkr(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parser per esportazioni Interactive Brokers (IBKR Trades)."""
    txs = []
    col_map = {str(c).strip().lower(): c for c in df.columns}

    c_sym = next((col_map[c] for c in col_map if "symbol" in c), None)
    c_date = next((col_map[c] for c in col_map if "date" in c), None)
    c_qty = next((col_map[c] for c in col_map if "quantity" in c or "qty" in c), None)
    c_price = next((col_map[c] for c in col_map if "t. price" in c or "price" in c), None)
    c_proceeds = next((col_map[c] for c in col_map if "proceeds" in c), None)
    c_fee = next((col_map[c] for c in col_map if "comm" in c or "fee" in c), None)

    for _, row in df.iterrows():
        t_date = _parse_date_safe(row.get(c_date)) if c_date else None
        if not t_date:
            continue

        raw_sym = str(row.get(c_sym, "")).strip().upper() if c_sym else ""
        if not raw_sym or raw_sym in ["HEADER", "DATA", "TOTAL"]:
            continue

        raw_qty = _clean_numeric(row.get(c_qty)) if c_qty else 0.0
        tx_type = "BUY" if raw_qty >= 0 else "SELL"
        qty = abs(raw_qty)
        price = abs(_clean_numeric(row.get(c_price))) if c_price else 0.0
        tot = abs(_clean_numeric(row.get(c_proceeds))) if c_proceeds else (qty * price)
        fee = abs(_clean_numeric(row.get(c_fee))) if c_fee else 0.0

        tx_hash = _compute_tx_hash("IBKR", t_date, raw_sym, tx_type, qty, price, tot)
        txs.append({
            "broker": "Interactive Brokers",
            "tx_date": t_date,
            "tx_type": tx_type,
            "ticker": raw_sym,
            "isin": "",
            "security_name": raw_sym,
            "shares": qty,
            "price": price,
            "total_eur": tot,
            "currency": "EUR",
            "fees": fee,
            "notes": f"IBKR: {raw_sym}".strip(),
            "tx_hash": tx_hash,
        })
    return txs


# ── UNIVERSAL ENTRYPOINT ──────────────────────────────────────

def parse_universal_broker_file(file_bytes_or_buffer: Any, filename: str = "") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Riconosce ed estrae le transazioni di compravendita titoli, dividendi e commissioni
    da un file esportato da qualunque dei 6 principali broker supportati.
    """
    df_raw, sample_text = _read_broker_dataframe(file_bytes_or_buffer, filename=filename)
    if df_raw.empty:
        return pd.DataFrame(), {"success": False, "error": "File vuoto o formato non valido", "broker": "UNKNOWN"}

    broker_detected = detect_broker_and_format(df_raw, file_text_sample=sample_text)

    txs: List[Dict[str, Any]] = []
    if broker_detected == "DIRECTA":
        txs = _parse_directa(df_raw)
    elif broker_detected == "FINECO":
        txs = _parse_fineco(df_raw)
    elif broker_detected == "DEGIRO":
        txs = _parse_degiro(df_raw)
    elif broker_detected == "SCALABLE":
        txs = _parse_scalable(df_raw)
    elif broker_detected == "TRADE_REPUBLIC":
        txs = _parse_trade_republic(df_raw)
    elif broker_detected == "IBKR":
        txs = _parse_ibkr(df_raw)
    else:
        # Fallback generico: tenta Directa poi Fineco
        txs = _parse_directa(df_raw) or _parse_fineco(df_raw)

    if not txs:
        # Se ancora vuoto, tenta un mapping flessibile basato su colonne euristiche
        txs = _parse_directa(df_raw)

    df_norm = pd.DataFrame(txs)
    if not df_norm.empty:
        df_norm = df_norm.sort_values(by="tx_date", ascending=False).reset_index(drop=True)

    broker_label = BROKER_SIGNATURES.get(broker_detected, {}).get("name", "Broker Universale")
    metadata = {
        "success": not df_norm.empty,
        "broker_key": broker_detected,
        "broker_name": broker_label,
        "total_rows": len(df_norm),
        "total_volume_eur": float(df_norm["total_eur"].sum()) if not df_norm.empty else 0.0,
        "unique_assets": int(df_norm["ticker"].nunique()) if not df_norm.empty else 0,
    }
    return df_norm, metadata


# ── DATABASE INGESTION & RECONCILIATION ────────────────────────

def ingest_broker_transactions(
    engine: Engine,
    df_txs: pd.DataFrame,
    portfolio_id: int = 1,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Ingerisce le transazioni normalizzate nel database 'transactions' e 'assets'
    con risoluzione automatica delle anagrafiche e deduplicazione deterministica.
    """
    if df_txs is None or df_txs.empty:
        return {"inserted": 0, "skipped_duplicates": 0, "new_assets": 0}

    inserted = 0
    skipped = 0
    new_assets = 0

    with engine.begin() as conn:
        # 0. Verifica e risolve portfolio_id valido per FK
        chk_pid = conn.execute(
            text("SELECT portfolio_id FROM portfolios WHERE portfolio_id = :pid"),
            {"pid": portfolio_id},
        ).scalar()
        if not chk_pid:
            first_pid = conn.execute(text("SELECT portfolio_id FROM portfolios ORDER BY portfolio_id ASC LIMIT 1")).scalar()
            if first_pid:
                portfolio_id = first_pid

        # 1. Carica gli asset esistenti per mappare ticker/isin -> asset_id
        res_assets = conn.execute(text("SELECT asset_id, ticker, name FROM assets")).fetchall()
        asset_map = {row[1].upper(): row[0] for row in res_assets}

        # 2. Carica hash o transazioni esistenti per il portfolio per evitare duplicati
        existing_txs = conn.execute(
            text("SELECT tx_date, tx_type, quantity, price, notes FROM transactions WHERE portfolio_id = :pid"),
            {"pid": portfolio_id},
        ).fetchall()

        # Set di impronte digitali per deduplicazione veloce
        existing_signatures = set()
        for r in existing_txs:
            s_date = str(r[0])
            s_type = str(r[1]).upper()
            s_shares = float(r[2])
            s_price = float(r[3])
            existing_signatures.add(f"{s_date}_{s_type}_{s_shares:.4f}_{s_price:.4f}")

        for _, row in df_txs.iterrows():
            t_date = str(row["tx_date"])
            t_type = str(row["tx_type"]).upper()
            t_shares = float(row["shares"])
            t_price = float(row["price"])
            t_tot = float(row["total_eur"])
            t_fee = float(row.get("fees", 0.0) or 0.0)
            t_notes = str(row.get("notes", ""))
            t_isin = str(row.get("isin", "")).strip().upper()
            t_ticker = str(row.get("ticker", "")).strip().upper() or (t_isin[:8] if t_isin else "ASSET")
            t_name = str(row.get("security_name", "")).strip() or t_ticker

            # Controllo duplicato
            sig = f"{t_date}_{t_type}_{t_shares:.4f}_{t_price:.4f}"
            if sig in existing_signatures:
                skipped += 1
                continue

            # Risolvi o crea Asset
            asset_id = asset_map.get(t_ticker) or (asset_map.get(t_isin) if t_isin else None)
            if not asset_id and not dry_run:
                # Inserisci nuovo asset
                res_ins = conn.execute(
                    text(
                        """
                        INSERT INTO assets (ticker, name, asset_class, currency)
                        VALUES (:ticker, :name, :asset_class, :currency)
                        """
                    ),
                    {
                        "ticker": t_ticker,
                        "name": t_name,
                        "asset_class": "Equity" if "ETF" not in t_name.upper() else "ETF",
                        "currency": "EUR",
                    },
                )
                asset_id = res_ins.lastrowid
                asset_map[t_ticker] = asset_id
                new_assets += 1
            elif not asset_id and dry_run:
                asset_id = 999999
                new_assets += 1

            if not dry_run:
                conn.execute(
                    text(
                        """
                        INSERT INTO transactions (portfolio_id, asset_id, tx_date, tx_type, quantity, price, currency, fees, notes)
                        VALUES (:pid, :aid, :t_date, :t_type, :quantity, :price, :curr, :fees, :notes)
                        """
                    ),
                    {
                        "pid": portfolio_id,
                        "aid": asset_id,
                        "t_date": t_date,
                        "t_type": t_type,
                        "quantity": t_shares,
                        "price": t_price,
                        "curr": "EUR",
                        "fees": t_fee,
                        "notes": t_notes,
                    },
                )
                existing_signatures.add(sig)
                inserted += 1

    return {
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "new_assets": new_assets,
    }



# ── STREAMLIT UI WIDGET ───────────────────────────────────────

def render_universal_broker_importer_tab(
    engine: Engine,
    portfolio_id: int = 1,
    prof_name: str = "Family Office Master",
):
    """
    Componente UI interattivo per Streamlit: Drag & Drop broker universale,
    anteprima dei dati con chip/badge e ingestione idempotente nel libro mastro.
    """
    import streamlit as st

    from core.ui_utils import fmt_eur, metric_card, section

    st.markdown(
        """
    <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(99, 102, 241, 0.06) 100%);
                border: 1px solid rgba(245, 158, 11, 0.3); border-left: 4px solid #f59e0b;
                border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="font-weight: 800; color: #fbbf24; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">
                    📥 Import Universale Broker Drag & Drop
                </span>
                <p style="font-size: 12px; color: #94a3b8; margin: 4px 0 0 0;">
                    Riconoscimento automatico del formato e ingestione transazioni per <b>Directa SIM, Fineco, Degiro, Scalable Capital, Trade Republic e Interactive Brokers</b>.
                </p>
            </div>
            <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                ⚡ 6 Broker Riconosciuti
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Broker Badges Ribbon
    st.markdown(
        """
    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
        <span style="background: rgba(30, 58, 138, 0.35); border: 1px solid #3b82f6; color: #93c5fd; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">🦁 Directa SIM</span>
        <span style="background: rgba(185, 28, 28, 0.3); border: 1px solid #ef4444; color: #fca5a5; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">🏛️ FinecoBank</span>
        <span style="background: rgba(234, 88, 12, 0.3); border: 1px solid #f97316; color: #fdba74; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">🇳🇱 Degiro</span>
        <span style="background: rgba(13, 148, 136, 0.3); border: 1px solid #14b8a6; color: #5eead4; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">📱 Scalable Capital</span>
        <span style="background: rgba(100, 116, 139, 0.35); border: 1px solid #94a3b8; color: #f1f5f9; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">🖤 Trade Republic</span>
        <span style="background: rgba(168, 85, 247, 0.3); border: 1px solid #c084fc; color: #e9d5ff; padding: 4px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;">🌐 Interactive Brokers</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    uploaded_broker_file = st.file_uploader(
        "Trascina qui il file esportato dal tuo broker (CSV o XLSX):",
        type=["csv", "xlsx", "xls", "txt"],
        key=f"universal_broker_file_uploader_{portfolio_id}",
        help="Carica il file senza modificare le colonne. L'algoritmo rileverà automaticamente la firma del broker.",
    )

    if uploaded_broker_file:
        raw_bytes = uploaded_broker_file.getvalue()
        df_parsed, meta = parse_universal_broker_file(raw_bytes, filename=uploaded_broker_file.name)

        if not meta["success"] or df_parsed.empty:
            st.error(f"❌ Impossibile estrarre transazioni dal file: {meta.get('error', 'Formato non supportato')}")
            return

        # ── KPI METRICS ──
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Broker Rilevato", meta["broker_name"], delta="Firma Verificata", delta_color="normal")
        with c2:
            metric_card("Transazioni", f"{meta['total_rows']:,}", delta="Eseguiti Estratti", delta_color="normal")
        with c3:
            metric_card("Controvalore Netto", fmt_eur(meta["total_volume_eur"]), delta="Volume Totale", delta_color="normal")
        with c4:
            metric_card("Asset Coinvolti", f"{meta['unique_assets']} Ticker", delta="Titoli/ETF/Bond", delta_color="normal")

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
        section("📋 Anteprima Transazioni Normalizzate")

        # Visualizzazione formattata
        df_disp = df_parsed.copy()
        df_disp["total_eur"] = df_disp["total_eur"].apply(lambda v: fmt_eur(v))
        df_disp["price"] = df_disp["price"].apply(lambda v: f"€ {v:,.4f}" if v > 0 else "-")
        df_disp["fees"] = df_disp["fees"].apply(lambda v: fmt_eur(v) if v > 0 else "€ 0,00")

        cols_order = ["tx_date", "broker", "tx_type", "ticker", "isin", "security_name", "shares", "price", "total_eur", "fees"]
        valid_cols = [c for c in cols_order if c in df_disp.columns]
        st.dataframe(df_disp[valid_cols], use_container_width=True, hide_index=True)

        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
        col_act1, col_act2 = st.columns(2)

        with col_act1:
            if st.button("🧪 Simula Importazione (Dry Run)", use_container_width=True, key=f"btn_dry_run_broker_{portfolio_id}"):
                res_sim = ingest_broker_transactions(engine, df_parsed, portfolio_id=portfolio_id, dry_run=True)
                st.info(
                    f"💡 **Esito Simulazione**: {res_sim['inserted']} transazioni nuove pronte all'inserimento, "
                    f"{res_sim['skipped_duplicates']} duplicate già esistenti, "
                    f"{res_sim['new_assets']} nuovi titoli da censire in anagrafica."
                )

        with col_act2:
            if st.button("🚀 Esegui Importazione a Libro Mastro", type="primary", use_container_width=True, key=f"btn_exec_broker_import_{portfolio_id}"):
                with st.spinner("Registrazione transazioni e risoluzione anagrafiche in corso..."):
                    res_exec = ingest_broker_transactions(engine, df_parsed, portfolio_id=portfolio_id, dry_run=False)
                    st.success(
                        f"✅ **Importazione completata con successo!**\n\n"
                        f"- Transazioni registrate: **{res_exec['inserted']}**\n"
                        f"- Transazioni duplicate ignorate: **{res_exec['skipped_duplicates']}**\n"
                        f"- Nuovi asset censiti in anagrafica: **{res_exec['new_assets']}**"
                    )
                    st.balloons()
