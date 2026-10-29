"""Backward compatibility proxy module for core/confirm_dialogs.py.

Deprecated: This visual UI module has been relocated to components.ui_core.confirm_dialogs.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.confirm_dialogs' is deprecated. "
    "Please import from 'components.ui_core.confirm_dialogs' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.confirm_dialogs import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("components.ui_core.confirm_dialogs")
    return getattr(mod, name)
