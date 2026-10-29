"""Backward compatibility proxy module for core/bitemporal_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.temporal.bitemporal_engine.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.bitemporal_engine' is deprecated. "
    "Please import from 'core.temporal.bitemporal_engine' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.temporal.bitemporal_engine import *  # noqa: F401, F403
