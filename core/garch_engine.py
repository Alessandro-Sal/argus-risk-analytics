"""Backward compatibility proxy module for core/garch_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.volatility.garch.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.garch_engine' is deprecated. "
    "Please import from 'core.volatility.garch' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.volatility.garch import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.volatility.garch")
    return getattr(mod, name)
