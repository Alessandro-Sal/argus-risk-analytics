"""Backward compatibility proxy module for core/excel_generator.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.excel.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.excel_generator' is deprecated. "
    "Please import from 'core.reporting.excel' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.excel import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.reporting.excel")
    return getattr(mod, name)
