"""Backward compatibility proxy module for core/html_exporter.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.html.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.html_exporter' is deprecated. "
    "Please import from 'core.reporting.html' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.html import *  # noqa: F401, F403
