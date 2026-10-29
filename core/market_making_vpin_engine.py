"""Backward compatibility proxy module for core/market_making_vpin_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.execution.market_making.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.market_making_vpin_engine' is deprecated. "
    "Please import from 'core.execution.market_making' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.execution.market_making import *  # noqa: F401, F403
