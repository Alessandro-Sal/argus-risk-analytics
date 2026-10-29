"""Backward compatibility proxy module for core/execution_algo.py.

Deprecated: This quantitative/reporting module has been consolidated into core.execution.algo.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.execution_algo' is deprecated. "
    "Please import from 'core.execution.algo' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.execution.algo import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.execution.algo")
    return getattr(mod, name)
