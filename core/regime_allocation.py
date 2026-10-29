"""Backward compatibility proxy module for core/regime_allocation.py.

Deprecated: This quantitative/reporting module has been consolidated into core.regime.allocation.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.regime_allocation' is deprecated. "
    "Please import from 'core.regime.allocation' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.regime.allocation import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.regime.allocation")
    return getattr(mod, name)
