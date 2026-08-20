"""
ARGUS — Risk Analytics Platform
Multi-Broker Adapters & Ingestion Hub
"""

from core.adapters.broker_hub import (
    SUPPORTED_BROKERS,
    detect_broker_format,
    parse_broker_csv,
)
from core.adapters.degiro import parse_degiro_transactions
from core.adapters.directa import parse_directa_transactions
from core.adapters.fineco import parse_fineco_transactions
from core.adapters.ibkr import parse_ibkr_transactions
from core.adapters.isin_resolver import (
    clean_date_value,
    clean_numeric_value,
    resolve_isin_to_ticker,
)
from core.adapters.scalable import parse_scalable_transactions
from core.adapters.traderepublic import parse_traderepublic_transactions

__all__ = [
    "SUPPORTED_BROKERS",
    "detect_broker_format",
    "parse_broker_csv",
    "resolve_isin_to_ticker",
    "clean_numeric_value",
    "clean_date_value",
    "parse_degiro_transactions",
    "parse_directa_transactions",
    "parse_fineco_transactions",
    "parse_ibkr_transactions",
    "parse_traderepublic_transactions",
    "parse_scalable_transactions",
]
