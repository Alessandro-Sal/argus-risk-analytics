"""Backward compatibility proxy module for core/wealth/tax_history_ui.py.

Deprecated: This visual UI module has been relocated to components.ui_core.tax_history_ui.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.wealth.tax_history_ui' is deprecated. "
    "Please import from 'components.ui_core.tax_history_ui' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.tax_history_ui import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("components.ui_core.tax_history_ui")
    return getattr(mod, name)
