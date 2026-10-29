"""Backward compatibility proxy module for core/pdf_generator.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.pdf.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.pdf_generator' is deprecated. "
    "Please import from 'core.reporting.pdf' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.pdf import *  # noqa: F401, F403
from core.reporting.pdf import _generate_legacy_pure_pdf  # noqa: F401
