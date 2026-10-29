"""Backward compatibility proxy module for core/mip_rebalancer.py.

Deprecated: This rebalancing engine has been consolidated into core.rebalancing.mip.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.mip_rebalancer' is deprecated. "
    "Please import from 'core.rebalancing.mip' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.rebalancing.mip import *  # noqa: F401, F403
