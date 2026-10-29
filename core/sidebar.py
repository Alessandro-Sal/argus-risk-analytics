"""Backward compatibility proxy module for core/sidebar.py.

Deprecated: This visual UI module has been relocated to components.ui_core.sidebar.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.sidebar' is deprecated. "
    "Please import from 'components.ui_core.sidebar' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.sidebar import *  # noqa: F401, F403
