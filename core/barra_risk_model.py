"""Backward compatibility proxy module for core/barra_risk_model.py.

Deprecated: This quantitative/reporting module has been consolidated into core.quant.barra_model.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.barra_risk_model' is deprecated. "
    "Please import from 'core.quant.barra_model' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.quant.barra_model import *  # noqa: F401, F403
