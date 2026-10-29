"""Backward compatibility proxy module for core/loading_states.py.

Deprecated: This visual UI module has been relocated to components.ui_core.loading_states.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.loading_states' is deprecated. "
    "Please import from 'components.ui_core.loading_states' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.loading_states import *  # noqa: F401, F403
