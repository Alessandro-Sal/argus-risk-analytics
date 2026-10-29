"""Backward compatibility proxy module for core/smart_order_router.py.

Deprecated: This quantitative/reporting module has been consolidated into core.execution.smart_router.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.smart_order_router' is deprecated. "
    "Please import from 'core.execution.smart_router' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.execution.smart_router import *  # noqa: F401, F403
