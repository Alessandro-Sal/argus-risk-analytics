# Core module
__version__ = "9.4.0"


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
