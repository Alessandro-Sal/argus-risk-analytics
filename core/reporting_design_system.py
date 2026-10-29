"""Backward compatibility proxy module for core/reporting_design_system.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.design_system.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.reporting_design_system' is deprecated. "
    "Please import from 'core.reporting.design_system' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.design_system import *  # noqa: F401, F403
