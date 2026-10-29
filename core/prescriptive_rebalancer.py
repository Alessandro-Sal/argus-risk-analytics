"""Backward compatibility proxy module for core/prescriptive_rebalancer.py.

Deprecated: This rebalancing engine has been consolidated into core.rebalancing.prescriptive.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.prescriptive_rebalancer' is deprecated. "
    "Please import from 'core.rebalancing.prescriptive' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.rebalancing.prescriptive import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.rebalancing.prescriptive")
    return getattr(mod, name)
