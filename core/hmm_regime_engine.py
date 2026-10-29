"""Backward compatibility proxy module for core/hmm_regime_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.regime.hmm.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.hmm_regime_engine' is deprecated. "
    "Please import from 'core.regime.hmm' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.regime.hmm import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.regime.hmm")
    return getattr(mod, name)
