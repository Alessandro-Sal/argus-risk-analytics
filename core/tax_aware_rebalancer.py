"""Backward compatibility proxy module for core/tax_aware_rebalancer.py.

Deprecated: This rebalancing engine has been consolidated into core.rebalancing.tax_aware.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.tax_aware_rebalancer' is deprecated. "
    "Please import from 'core.rebalancing.tax_aware' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.rebalancing.tax_aware import *  # noqa: F401, F403
