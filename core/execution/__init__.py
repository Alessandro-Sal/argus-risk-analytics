"""ARGUS — Algorithmic Trade Execution, TCA & Market Microstructure Package."""
from core.execution.algo import (
    compute_almgren_chriss_basket_schedule,
    compute_twap_schedule,
    compute_vwap_schedule,
    estimate_microstructure_market_impact,
    generate_intraday_volume_profile,
)
from core.execution.market_making import compute_market_making_and_vpin
from core.execution.smart_router import compute_smart_order_routing
from core.execution.tca import (
    compute_broker_commissions,
    compute_implementation_shortfall_and_execution_benchmarks,
)

__all__ = [
    "generate_intraday_volume_profile",
    "compute_twap_schedule",
    "compute_vwap_schedule",
    "compute_almgren_chriss_basket_schedule",
    "estimate_microstructure_market_impact",
    "compute_broker_commissions",
    "compute_implementation_shortfall_and_execution_benchmarks",
    "compute_smart_order_routing",
    "compute_market_making_and_vpin",
]
