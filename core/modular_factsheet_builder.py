"""Backward compatibility proxy module for core/modular_factsheet_builder.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.factsheet.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.modular_factsheet_builder' is deprecated. "
    "Please import from 'core.reporting.factsheet' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.factsheet import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.reporting.factsheet")
    return getattr(mod, name)
