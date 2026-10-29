"""Backward compatibility proxy module for core/autonomous_rebalancer.py.

Deprecated: This rebalancing engine has been consolidated into core.rebalancing.autonomous.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.autonomous_rebalancer' is deprecated. "
    "Please import from 'core.rebalancing.autonomous' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.rebalancing.autonomous import *  # noqa: F401, F403
