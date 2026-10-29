"""Backward compatibility proxy module for core/execution_algo_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.execution.tca.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.execution_algo_engine' is deprecated. "
    "Please import from 'core.execution.tca' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.execution.tca import *  # noqa: F401, F403
