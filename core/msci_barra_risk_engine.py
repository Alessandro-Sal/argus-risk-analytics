"""Backward compatibility proxy module for core/msci_barra_risk_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.quant.msci_barra.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.msci_barra_risk_engine' is deprecated. "
    "Please import from 'core.quant.msci_barra' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.quant.msci_barra import *  # noqa: F401, F403
