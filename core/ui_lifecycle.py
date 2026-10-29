"""Backward compatibility proxy module for core/ui_lifecycle.py.

Deprecated: This visual UI module has been relocated to components.ui_core.ui_lifecycle.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.ui_lifecycle' is deprecated. "
    "Please import from 'components.ui_core.ui_lifecycle' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.ui_lifecycle import *  # noqa: F401, F403
