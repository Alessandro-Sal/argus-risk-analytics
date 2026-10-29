"""Backward compatibility proxy module for core/wealth/wealth_temporal_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.temporal.wealth_temporal_engine.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.wealth.wealth_temporal_engine' is deprecated. "
    "Please import from 'core.temporal.wealth_temporal_engine' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.temporal.wealth_temporal_engine import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.temporal.wealth_temporal_engine")
    return getattr(mod, name)
