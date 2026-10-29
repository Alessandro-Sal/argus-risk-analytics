"""Backward compatibility proxy module for core/rebalancer.py.

Deprecated: This rebalancing engine has been consolidated into core.rebalancing.heuristic.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.rebalancer' is deprecated. "
    "Please import from 'core.rebalancing.heuristic' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.rebalancing.heuristic import *  # noqa: F401, F403
