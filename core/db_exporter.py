"""Backward compatibility proxy module for core/db_exporter.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.db_exporter.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.db_exporter' is deprecated. "
    "Please import from 'core.reporting.db_exporter' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting import db_exporter as _target_module
from core.reporting.db_exporter import *  # noqa: F401, F403


def __getattr__(name: str):
    return getattr(_target_module, name)
