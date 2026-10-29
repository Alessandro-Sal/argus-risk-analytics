"""Backward compatibility proxy module for core/regime_switching.py.

Deprecated: This quantitative/reporting module has been consolidated into core.regime.switching.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.regime_switching' is deprecated. "
    "Please import from 'core.regime.switching' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.regime.switching import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.regime.switching")
    return getattr(mod, name)
