"""Backward compatibility proxy module for core/executive_board_pack_engine.py.

Deprecated: This quantitative/reporting module has been consolidated into core.reporting.board_pack.
Importing from this path is deprecated and will be removed in a future release.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.executive_board_pack_engine' is deprecated. "
    "Please import from 'core.reporting.board_pack' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.reporting.board_pack import *  # noqa: F401, F403
