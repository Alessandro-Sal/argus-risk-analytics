"""
ARGUS — Quantitative Risk Analytics & Wealth Intelligence Ecosystem
Core Package Initialization with PEP 562 Lazy Loading.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

__version__ = "10.0.0"

if TYPE_CHECKING:
    from core.duckdb_engine import (
        compute_duckdb_asset_sector_currency_cube,
        compute_duckdb_sector_rankings,
        compute_duckdb_temporal_snapshot_analytics,
    )
    from core.metadata_resolver import resolve_asset_metadata
    from core.report_exporter import (
        generate_excel_report,
        generate_institutional_audit_dossier,
        generate_pdf_factsheet,
    )
    from core.temporal_engine import (
        compute_monthly_return_matrix,
        compute_rolling_risk_metrics,
        compute_seasonality_patterns,
        compute_side_by_side_comparison,
        compute_underwater_drawdowns,
        reconstruct_point_in_time_portfolio,
    )

_LAZY_EXPORTS: dict[str, str] = {
    "compute_duckdb_asset_sector_currency_cube": "core.duckdb_engine",
    "compute_duckdb_sector_rankings": "core.duckdb_engine",
    "compute_duckdb_temporal_snapshot_analytics": "core.duckdb_engine",
    "resolve_asset_metadata": "core.metadata_resolver",
    "generate_excel_report": "core.report_exporter",
    "generate_institutional_audit_dossier": "core.report_exporter",
    "generate_pdf_factsheet": "core.report_exporter",
    "compute_monthly_return_matrix": "core.temporal_engine",
    "compute_rolling_risk_metrics": "core.temporal_engine",
    "compute_seasonality_patterns": "core.temporal_engine",
    "compute_side_by_side_comparison": "core.temporal_engine",
    "compute_underwater_drawdowns": "core.temporal_engine",
    "reconstruct_point_in_time_portfolio": "core.temporal_engine",
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


__all__ = ["__version__"] + list(_LAZY_EXPORTS.keys())
