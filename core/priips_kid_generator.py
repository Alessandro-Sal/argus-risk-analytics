"""Backward compatibility proxy module for core/priips_kid_generator.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.priips.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.priips_kid_generator' is deprecated. "
    "Please import from 'core.reporting.priips' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.priips import *  # noqa: F401, F403
