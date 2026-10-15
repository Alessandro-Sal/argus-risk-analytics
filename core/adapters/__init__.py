"""
ARGUS — Risk Analytics Platform
Multi-Broker Adapters & Ingestion Hub
PEP 562 Lazy Package Loading.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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
    from core.data_quality_gate import (
        AssetClass,
        CanonicalTradeRecord,
        DataQualityGate,
        QualityGateReport,
        TransactionType,
    )

_LAZY_EXPORTS: dict[str, str] = {
    "SUPPORTED_BROKERS": "core.adapters.broker_hub",
    "detect_broker_format": "core.adapters.broker_hub",
    "parse_broker_csv": "core.adapters.broker_hub",
    "resolve_isin_to_ticker": "core.adapters.isin_resolver",
    "clean_numeric_value": "core.adapters.isin_resolver",
    "clean_date_value": "core.adapters.isin_resolver",
    "parse_degiro_transactions": "core.adapters.degiro",
    "parse_directa_transactions": "core.adapters.directa",
    "parse_fineco_transactions": "core.adapters.fineco",
    "parse_ibkr_transactions": "core.adapters.ibkr",
    "parse_traderepublic_transactions": "core.adapters.traderepublic",
    "parse_scalable_transactions": "core.adapters.scalable",
    "DataQualityGate": "core.data_quality_gate",
    "CanonicalTradeRecord": "core.data_quality_gate",
    "QualityGateReport": "core.data_quality_gate",
    "TransactionType": "core.data_quality_gate",
    "AssetClass": "core.data_quality_gate",
}


def __getattr__(name: str) -> Any:
    target_mod = _LAZY_EXPORTS.get(name)
    if target_mod:
        try:
            mod = importlib.import_module(target_mod)
            val = getattr(mod, name)
            globals()[name] = val
            return val
        except (ImportError, AttributeError):
            if name in ("DataQualityGate", "CanonicalTradeRecord", "QualityGateReport", "TransactionType", "AssetClass"):
                return None
            raise
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))


__all__ = list(_LAZY_EXPORTS.keys())
