"""Backward compatibility proxy module for core/ux_quant_canvas.py.

Deprecated: This visual UI module has been relocated to components.ui_core.ux_quant_canvas.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.ux_quant_canvas' is deprecated. "
    "Please import from 'components.ui_core.ux_quant_canvas' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.ux_quant_canvas import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("components.ui_core.ux_quant_canvas")
    return getattr(mod, name)
