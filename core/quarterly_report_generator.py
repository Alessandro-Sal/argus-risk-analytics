"""Backward compatibility proxy module for core/quarterly_report_generator.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.quarterly.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.quarterly_report_generator' is deprecated. "
    "Please import from 'core.reporting.quarterly' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.quarterly import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.reporting.quarterly")
    return getattr(mod, name)
