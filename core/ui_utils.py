"""Backward compatibility proxy module for core/ui_utils.py.

Deprecated: This visual UI module has been relocated to components.ui_core.ui_utils.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.ui_utils' is deprecated. "
    "Please import from 'components.ui_core.ui_utils' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.ui_utils import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("components.ui_core.ui_utils")
    return getattr(mod, name)
