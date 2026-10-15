"""
ARGUS — Application Services Layer
Decoupled, headless business logic facades consumable by both FastAPI REST endpoints and Streamlit UI.
PEP 562 Lazy Package Loading.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.services.rebalancing_service import RebalancingService
    from core.services.risk_service import RiskService
    from core.services.tax_service import TaxService
    from core.services.wealth_service import WealthService

_LAZY_EXPORTS: dict[str, str] = {
    "RebalancingService": "core.services.rebalancing_service",
    "RiskService": "core.services.risk_service",
    "TaxService": "core.services.tax_service",
    "WealthService": "core.services.wealth_service",
}


def __getattr__(name: str) -> Any:
    target_mod = _LAZY_EXPORTS.get(name)
    if target_mod:
        mod = importlib.import_module(target_mod)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))


__all__ = ["RebalancingService", "RiskService", "TaxService", "WealthService"]
