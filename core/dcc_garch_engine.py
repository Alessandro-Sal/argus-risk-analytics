"""Backward compatibility proxy module for core/dcc_garch_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.volatility.dcc_garch.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.dcc_garch_engine' is deprecated. "
    "Please import from 'core.volatility.dcc_garch' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.volatility.dcc_garch import *  # noqa: F401, F403
