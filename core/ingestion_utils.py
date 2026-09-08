# ==============================================================================
# core/ingestion_utils.py
# ARGUS — Universal Tabular Ingestion Utilities
# Resilient Encoding, Delimiter & File Format Sniffer for Financial Datasets
# ==============================================================================

import io
import logging
from pathlib import Path
from typing import Any, List, Optional, Union

import pandas as pd

logger = logging.getLogger("argus.ingestion_utils")

SUPPORTED_ENCODINGS: List[str] = [
    "utf-8-sig",
    "utf-8",
    "latin-1",
    "cp1252",
    "iso-8859-1",
]

COMMON_DELIMITERS: List[str] = [";", ",", "\t", "|"]


def read_tabular_stream(
    file_bytes_or_buffer: Union[bytes, io.BytesIO, io.StringIO, str, Any],
    filename: str = ""
) -> pd.DataFrame:
    """
    Legge resilientemente flussi tabulari (CSV, TSV, XLSX, XLS) da memoria o disco.
    Applica auto-detection su formati binari Excel, encoding multipli e separatori europei/anglosassoni.
    """
    if file_bytes_or_buffer is None:
        return pd.DataFrame()

    raw_bytes: Optional[bytes] = None
    decoded_text: Optional[str] = None

    # Normalizzazione dell'input in bytes o stringa
    if isinstance(file_bytes_or_buffer, bytes):
        raw_bytes = file_bytes_or_buffer
    elif isinstance(file_bytes_or_buffer, io.BytesIO):
        raw_bytes = file_bytes_or_buffer.getvalue()
    elif isinstance(file_bytes_or_buffer, io.StringIO):
        decoded_text = file_bytes_or_buffer.getvalue()
    elif isinstance(file_bytes_or_buffer, str):
        p = Path(file_bytes_or_buffer)
        if p.exists() and p.is_file():
            filename = filename or p.name
            with open(p, "rb") as f:
                raw_bytes = f.read()
        else:
            decoded_text = file_bytes_or_buffer
    elif hasattr(file_bytes_or_buffer, "read"):
        content = file_bytes_or_buffer.read()
        if hasattr(file_bytes_or_buffer, "seek"):
            file_bytes_or_buffer.seek(0)
        if isinstance(content, bytes):
            raw_bytes = content
        else:
            decoded_text = str(content)

    fn_lower = (filename or "").lower()

    # 1. Riconoscimento file Excel (XLSX / XLS) tramite estensione o magic numbers
    is_excel = fn_lower.endswith((".xlsx", ".xls", ".xlsm"))
    if not is_excel and raw_bytes and len(raw_bytes) >= 8:
        # PK\x03\x04 (ZIP / XLSX) oppure \xd0\xcf\x11\xe0 (OLE Compound Document / XLS)
        if raw_bytes.startswith(b"PK\x03\x04") or raw_bytes.startswith(b"\xd0\xcf\x11\xe0"):
            is_excel = True

    if is_excel:
        excel_buf = io.BytesIO(raw_bytes) if raw_bytes else io.BytesIO(decoded_text.encode("latin-1"))
        try:
            df = pd.read_excel(excel_buf, dtype=str)
        except Exception:
            excel_buf.seek(0)
            df = pd.read_excel(excel_buf, engine="openpyxl", dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    # 2. Decodifica testo per CSV/TSV con sniffer di codifica
    if decoded_text is None:
        if not raw_bytes:
            return pd.DataFrame()
        for enc in SUPPORTED_ENCODINGS:
            try:
                decoded_text = raw_bytes.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if decoded_text is None:
            decoded_text = raw_bytes.decode("utf-8", errors="replace")

    lines = [l for l in decoded_text.splitlines() if l.strip()]
    if not lines:
        return pd.DataFrame()

    # 3. Individuazione riga di header e sniffer del delimitatore
    header_idx = 0
    candidate_keywords = [
        "data", "date", "ticker", "simbolo", "isin", "operazione",
        "importo", "amount", "quantità", "quantity", "shares", "prezzo", "price",
        "descrizione", "description", "causale", "saldo", "balance"
    ]
    for i, line in enumerate(lines[:20]):
        line_low = line.lower()
        if any(kw in line_low for kw in candidate_keywords):
            header_idx = i
            break

    sub_text = "\n".join(lines[header_idx:])
    sample_lines = lines[header_idx: min(header_idx + 15, len(lines))]
    sample_joined = "\n".join(sample_lines)

    delim_counts = {sep: sample_joined.count(sep) for sep in COMMON_DELIMITERS}
    best_sep = max(delim_counts, key=delim_counts.get) if max(delim_counts.values()) > 0 else ","

    try:
        df = pd.read_csv(io.StringIO(sub_text), sep=best_sep, dtype=str, on_bad_lines="skip")
    except Exception:
        try:
            df = pd.read_csv(io.StringIO(sub_text), sep=None, engine="python", dtype=str, on_bad_lines="skip")
        except Exception as ex:
            logger.warning(f"Fallback reading tabular stream: {ex}")
            df = pd.read_csv(io.StringIO(decoded_text), dtype=str, on_bad_lines="skip")

    df.columns = [str(c).strip() for c in df.columns]
    return df
