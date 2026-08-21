"""
ARGUS — Risk Analytics Platform
Core Module: Multi-Broker Ingestion Hub & Auto-Detector
Orchestratore universale per l'ingestione, il rilevamento automatico del formato e la normalizzazione da molteplici broker.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from core.adapters.degiro import parse_degiro_transactions
from core.adapters.directa import parse_directa_transactions
from core.adapters.etoro import parse_etoro_transactions
from core.adapters.fineco import parse_fineco_transactions
from core.adapters.ibkr import parse_ibkr_transactions
from core.adapters.revolut import parse_revolut_transactions
from core.adapters.scalable import parse_scalable_transactions
from core.adapters.traderepublic import parse_traderepublic_transactions

logger = logging.getLogger(__name__)

SUPPORTED_BROKERS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "name": "CSV Standard ARGUS",
        "icon": "📄",
        "desc": "Template nativo a 9 colonne (tx_date, ticker, tx_type, quantity, price, currency, fees, asset_class, notes).",
        "sample_columns": ["tx_date", "ticker", "tx_type", "quantity", "price", "currency"]
    },
    "degiro": {
        "name": "DeGiro",
        "icon": "🟡",
        "desc": "Export Transazioni da Attività > Transazioni (IT/EN/NL). Riconosce ISIN e calcola il cambio valuta.",
        "sample_columns": ["data", "ora", "prodotto", "isin", "quantità", "prezzo", "valuta"]
    },
    "directa": {
        "name": "Directa SIM",
        "icon": "🔵",
        "desc": "Export Ordini Eseguiti o Estratto Conto Titoli dalle piattaforme dLite o Classic.",
        "sample_columns": ["data", "ora", "operazione", "titolo", "simbolo", "quantità", "prezzo", "commissioni"]
    },
    "fineco": {
        "name": "Fineco Bank",
        "icon": "🔴",
        "desc": "Report Movimenti Conto Trading, Ordini Eseguiti e Rendiconto Fiscale.",
        "sample_columns": ["data operazione", "tipo operazione", "descrizione", "codice isin", "quantità", "prezzo"]
    },
    "ibkr": {
        "name": "Interactive Brokers (IBKR)",
        "icon": "🟠",
        "desc": "Activity Statement CSV (sezione Trades) o Trades Report esportato da Client Portal / TWS.",
        "sample_columns": ["trades", "date/time", "symbol", "quantity", "t. price", "comm/fee"]
    },
    "traderepublic": {
        "name": "Trade Republic",
        "icon": "🟢",
        "desc": "Export estratto conto, transazioni e ordini PAC (Savings Plan) in formato CSV.",
        "sample_columns": ["timestamp", "type", "isin", "name", "shares", "price", "fee"]
    },
    "scalable": {
        "name": "Scalable Capital",
        "icon": "🔷",
        "desc": "Export transazioni Baader Bank / Scalable Broker per compravendite, dividendi e PAC ETF.",
        "sample_columns": ["date", "type", "security", "isin", "shares", "price", "amount"]
    },
    "etoro": {
        "name": "eToro",
        "icon": "🟩",
        "desc": "Estratto Conto / Account Statement e Closed Positions esportati da eToro.",
        "sample_columns": ["position id", "action", "details", "units", "open rate", "close rate", "amount"]
    },
    "revolut": {
        "name": "Revolut Trading",
        "icon": "🟣",
        "desc": "Export transazioni e ordini della sezione Trading / Investimenti di Revolut.",
        "sample_columns": ["date", "ticker", "type", "quantity", "price per share", "total amount", "currency"]
    }
}


def _match_broker_signatures(cols_lower: list, cols_joined: str, first_col_values: list) -> Optional[str]:
    """Identifica il broker sulla base di firme e parole chiave nelle colonne."""
    std_required = {"tx_date", "ticker", "tx_type", "quantity", "price"}
    if std_required.issubset(set(cols_lower)):
        return "standard"

    if any("trades" in v for v in first_col_values) or any(k in cols_joined for k in ["t. price", "tradeprice", "comm/fee", "currencyprimary"]):
        return "ibkr"

    if any("isin" in c for c in cols_lower) and any(k in cols_joined for k in ["prodotto", "product", "costi di transazione", "transaction costs", "valuta autoconversione"]):
        return "degiro"

    if any(k in cols_joined for k in ["operazione", "tipo operazione"]) and any(k in cols_joined for k in ["simbolo", "controvalore", "prezzo eseguito", "mercato", "divisa"]):
        return "directa"

    if any(k in cols_joined for k in ["data operazione", "data valuta"]) and any(k in cols_joined for k in ["codice isin", "codice titolo", "importo in euro", "tipo operazione"]):
        return "fineco"

    if any(k in cols_joined for k in ["security", "bezeichnung", "kurswert", "ausführungskurs", "transaktionsart", "scalable"]):
        return "scalable"

    if any(k in cols_joined for k in ["timestamp", "wertpapier", "gebuehr", "gebühr", "traderepublic", "trade republic"]):
        return "traderepublic"

    if any(k in cols_joined for k in ["position id", "open rate", "close rate", "take profit", "stop loss rate", "realized equity change", "etoro"]):
        return "etoro"

    if any(k in cols_joined for k in ["price per share", "total amount", "revolut"]) or ("ticker" in cols_joined and "price" in cols_joined and ("fx rate" in cols_joined or "amount" in cols_joined)):
        return "revolut"

    if "isin" in cols_joined and any(k in cols_joined for k in ["name", "shares", "stueck", "stück"]):
        return "traderepublic"

    if "isin" in cols_joined and ("shares" in cols_joined or "quantità" in cols_joined or "quantity" in cols_joined):
        return "traderepublic" if ("fees" in cols_joined or "fee" in cols_joined) else "degiro"

    return None


def detect_broker_format(df_raw: pd.DataFrame) -> str:
    """
    Analizza la struttura del DataFrame, i nomi delle colonne e i primi record
    per identificare automaticamente il broker di provenienza.
    """
    if df_raw is None or len(df_raw.columns) == 0:
        return "standard"

    cols_lower = [str(c).strip().lower() for c in df_raw.columns]
    cols_joined = " ".join(cols_lower)
    first_col_values = [str(v).strip().lower() for v in df_raw.iloc[:15, 0].values if pd.notna(v)] if not df_raw.empty else []

    detected = _match_broker_signatures(cols_lower, cols_joined, first_col_values)
    return detected if detected else "standard"


def _dispatch_parser(df_raw: pd.DataFrame, broker_key: str) -> pd.DataFrame:
    """Invia il DataFrame al parser specifico per il broker indicato."""
    if broker_key == "degiro":
        return parse_degiro_transactions(df_raw)
    if broker_key == "directa":
        return parse_directa_transactions(df_raw)
    if broker_key == "fineco":
        return parse_fineco_transactions(df_raw)
    if broker_key == "ibkr":
        return parse_ibkr_transactions(df_raw)
    if broker_key == "traderepublic":
        return parse_traderepublic_transactions(df_raw)
    if broker_key == "scalable":
        return parse_scalable_transactions(df_raw)
    if broker_key == "etoro":
        return parse_etoro_transactions(df_raw)
    if broker_key == "revolut":
        return parse_revolut_transactions(df_raw)
    return df_raw.copy()


def parse_broker_csv(
    df_raw: pd.DataFrame,
    broker_key: str = "auto"
) -> Tuple[pd.DataFrame, str, Dict[str, Any]]:
    """
    Esegue il parsing e la normalizzazione del DataFrame grezzo utilizzando il parser appropriato.
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame(), "standard", {"status": "empty", "rows_parsed": 0}

    detected_key = detect_broker_format(df_raw) if (broker_key == "auto" or not broker_key) else broker_key.lower().strip()
    logger.info(f"Avvio parsing con adapter broker: {detected_key}")

    try:
        df_parsed = _dispatch_parser(df_raw, detected_key)
        report = {
            "status": "success",
            "broker_key": detected_key,
            "broker_name": SUPPORTED_BROKERS.get(detected_key, {}).get("name", detected_key.title()),
            "broker_icon": SUPPORTED_BROKERS.get(detected_key, {}).get("icon", "📄"),
            "rows_raw": len(df_raw),
            "rows_parsed": len(df_parsed),
            "is_auto_detected": (broker_key == "auto")
        }
        return df_parsed, detected_key, report
    except Exception as e:
        logger.error(f"Errore durante il parsing del broker {detected_key}: {e}", exc_info=True)
        b_name = SUPPORTED_BROKERS.get(detected_key, {}).get("name", detected_key)
        raise ValueError(f"Errore durante l'elaborazione del file con il parser {b_name}: {e}") from e
