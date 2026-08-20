"""
ARGUS — Risk Analytics Platform
Core Module: ISIN Resolver & Universal Data Cleaning Utilities
Gestione e risoluzione dei codici ISIN in Ticker Yahoo Finance e normalizzazione di date e valori numerici.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Tabella di mappatura locale predefinita per gli ISIN più diffusi
BASE_ISIN_TO_TICKER: Dict[str, str] = {
    # ETF UCITS Comuni su Borsa Italiana / Xetra / Euronext
    "IE00B4L5Y983": "SWDA.MI",  # iShares Core MSCI World (Borsa Italiana)
    "IE00B3RBWM25": "VWCE.MI",  # Vanguard FTSE All-World (Borsa Italiana)
    "IE00B5BMR087": "CSSPX.MI", # iShares Core S&P 500 (Borsa Italiana)
    "IE00B1XNHC34": "INRG.MI",  # iShares Global Clean Energy
    "LU1681043599": "AMEM.MI",  # Amundi MSCI Emerging Markets
    "IE00B4K48X80": "IMEA.SW",  # iShares Core MSCI Europe
    "IE00BZCQB185": "NDIA.L",   # iShares MSCI India
    "IE000YYE6WK5": "DFEN.DE",  # VanEck Defense UCITS ETF
    "IE000U9ODG19": "DFND.PA",  # HANetf Future of Defence
    "DE0005190003": "BMW.DE",   # BMW AG
    "IT0000072618": "ISP.MI",   # Intesa Sanpaolo
    "IT0003132476": "ENI.MI",   # Eni SpA
    "IT0003128367": "ENEL.MI",  # Enel SpA
    "IT0004176001": "RACE.MI",  # Ferrari NV
    "NL0011585146": "FERG.L",   # Ferguson
    "NL0011821202": "INGA.AS",  # ING Groep

    # Stock USA Popolari
    "US0378331005": "AAPL",
    "US5949181045": "MSFT",
    "US0231351067": "AMZN",
    "US88160R1014": "TSLA",
    "US02079K1079": "GOOGL",
    "US02079K3059": "GOOG",
    "US30303M1027": "META",
    "US67066G1040": "NVDA",
    "US01609W1027": "BABA",
    "US4581401001": "INTC",
    "US69608A1088": "PLTR",
    "US70450Y1038": "PYPL",
    "US7475251036": "QCOM",
    "US1912161007": "KO",
    "US00206R1023": "T",
    "DK0062498333": "NOV.DE",  # Novo Nordisk (EUR listing)
}

# Cache in memoria durante la sessione
_MEMORY_ISIN_CACHE: Dict[str, str] = {}


def get_config_file_path() -> Path:
    """Restituisce il percorso del file di configurazione config.json."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root_dir / "config" / "config.json",
        Path.cwd() / "config" / "config.json",
        Path.cwd() / "config.json",
        root_dir / "config.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def load_persistent_ticker_mapping() -> Dict[str, str]:
    """Carica la mappatura ISIN -> Ticker salvata nel file di configurazione."""
    mapping = dict(BASE_ISIN_TO_TICKER)
    cfg_file = get_config_file_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                saved = data.get("ticker_mapping", {})
                for k, v in saved.items():
                    if k and v and str(k).upper() != "NAN":
                        mapping[str(k).strip().upper()] = str(v).strip().upper()
        except Exception as e:
            logger.warning(f"Impossibile leggere il file config.json: {e}")
    return mapping


def save_isin_to_config(isin: str, ticker: str) -> None:
    """Salva una nuova associazione ISIN -> Ticker nel file config.json."""
    cfg_file = get_config_file_path()
    try:
        data: Dict[str, Any] = {}
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        if "ticker_mapping" not in data:
            data["ticker_mapping"] = {}

        data["ticker_mapping"][isin.strip().upper()] = ticker.strip().upper()

        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.warning(f"Impossibile salvare l'associazione ISIN nel config.json: {e}")


def _search_yahoo_isin(clean_isin: str) -> Optional[str]:
    """Interroga l'endpoint di ricerca Yahoo Finance per un codice ISIN."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={clean_isin}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            if quotes and len(quotes) > 0:
                symbol = quotes[0].get("symbol", "").strip().upper()
                if symbol:
                    return symbol
    except Exception as ex:
        logger.debug(f"Ricerca Yahoo Finance fallita per ISIN {clean_isin}: {ex}")
    return None


def resolve_isin_to_ticker(isin: str, fallback_symbol: Optional[str] = None) -> str:
    """
    Risolve un codice ISIN nel corrispondente Ticker Yahoo Finance.
    Controlla in ordine: cache in memoria, config.json/dizionario base, API Yahoo Finance.
    """
    if not isin or pd.isna(isin):
        return str(fallback_symbol).strip().upper() if fallback_symbol else "UNKNOWN"

    clean_isin = str(isin).strip().upper()
    if clean_isin in ["NAN", "NONE", "NULL", ""]:
        return str(fallback_symbol).strip().upper() if fallback_symbol else "UNKNOWN"

    # 1. Controllo cache in memoria
    if clean_isin in _MEMORY_ISIN_CACHE:
        return _MEMORY_ISIN_CACHE[clean_isin]

    # 2. Controllo configurazione persistente
    persistent_map = load_persistent_ticker_mapping()
    if clean_isin in persistent_map:
        res = persistent_map[clean_isin]
        _MEMORY_ISIN_CACHE[clean_isin] = res
        return res

    # Se clean_isin non ha il formato di un ISIN (12 caratteri alfanumerici), consideralo un ticker
    if not re.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$", clean_isin):
        _MEMORY_ISIN_CACHE[clean_isin] = clean_isin
        return clean_isin

    # 3. Interrogazione Yahoo Finance Search API
    yahoo_sym = _search_yahoo_isin(clean_isin)
    if yahoo_sym:
        _MEMORY_ISIN_CACHE[clean_isin] = yahoo_sym
        save_isin_to_config(clean_isin, yahoo_sym)
        return yahoo_sym

    # 4. Fallback sul simbolo opzionale fornito dal broker
    if fallback_symbol and str(fallback_symbol).strip().upper() not in ["", "NAN", "NONE"]:
        resolved = str(fallback_symbol).strip().upper()
        _MEMORY_ISIN_CACHE[clean_isin] = resolved
        return resolved

    return clean_isin


def _parse_clean_float(s: str, is_negative: bool, default: float) -> float:
    """Esegue la conversione numerica finale gestendo virgole e punti."""
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")

    try:
        res = float(s)
        return -res if is_negative else res
    except ValueError:
        return default


def clean_numeric_value(val: Any, default: float = 0.0) -> float:
    """
    Normalizza e converte valori numerici da diversi formati internazionali:
    - Formato europeo: '1.234,56' o '1234,56' -> 1234.56
    - Formato anglosassone: '1,234.56' -> 1234.56
    - Parentesi per negativi: '(150.00)' -> -150.00
    - Simboli di valuta: '€ 150,00' o '$ 100.50' -> 150.0 o 100.5
    """
    if val is None or pd.isna(val):
        return default

    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return default

    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    elif s.endswith("-"):
        is_negative = True
        s = s[:-1].strip()

    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return default

    return _parse_clean_float(s, is_negative, default)


def clean_date_value(val: Any) -> str:
    """
    Normalizza una data in formato ISO 'YYYY-MM-DD'.
    Supporta: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, DD.MM.YYYY, timestamp ISO con ore.
    """
    if val is None or pd.isna(val):
        return ""

    s = str(val).strip()
    if not s:
        return ""

    if " " in s:
        s = s.split(" ")[0]
    elif "T" in s:
        s = s.split("T")[0]

    # Se è già in formato ISO YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return s
