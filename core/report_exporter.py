"""ARGUS — Institutional Report Exporter Proxy (core/report_exporter.py).

Relocated to core.reporting.report_exporter for architectural modularity.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.report_exporter' is deprecated. "
    "Please import from 'core.reporting.report_exporter' or 'core.reporting' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.report_exporter import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.reporting.report_exporter")
    return getattr(mod, name)
