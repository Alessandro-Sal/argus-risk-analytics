"""ARGUS — Unified Volatility and Tail Risk Modeling Package."""
from core.volatility.dcc_garch import DCCGarchEngine, DCCGarchResult, compute_dcc_garch_extreme_risk
from core.volatility.garch import compute_filtered_historical_simulation, compute_garch_fhs_bundle, fit_garch11

__all__ = [
    "fit_garch11",
    "compute_filtered_historical_simulation",
    "compute_garch_fhs_bundle",
    "DCCGarchEngine",
    "DCCGarchResult",
    "compute_dcc_garch_extreme_risk",
]
