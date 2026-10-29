"""Backward compatibility proxy module for core/exporter.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.csv_exporter.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.exporter' is deprecated. "
    "Please import from 'core.reporting.csv_exporter' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.csv_exporter import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.reporting.csv_exporter")
    return getattr(mod, name)
