"""ARGUS — Unified Market Regime Detection & Adaptive Allocation Package."""
from core.regime.allocation import compute_regime_conditional_allocation, detect_asset_characters
from core.regime.hmm import compute_hmm_market_regime_detection
from core.regime.switching import compute_market_regime_states

__all__ = [
    "compute_hmm_market_regime_detection",
    "compute_market_regime_states",
    "detect_asset_characters",
    "compute_regime_conditional_allocation",
]
