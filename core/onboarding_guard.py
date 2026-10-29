"""Backward compatibility proxy module for core/onboarding_guard.py.

Deprecated: This visual UI module has been relocated to components.ui_core.onboarding_guard.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.onboarding_guard' is deprecated. "
    "Please import from 'components.ui_core.onboarding_guard' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.onboarding_guard import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("components.ui_core.onboarding_guard")
    return getattr(mod, name)
