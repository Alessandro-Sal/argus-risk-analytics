"""Backward compatibility proxy module for core.ux_institutional_hub.

Deprecated: Core headless calculation/telemetry has been relocated to core.institutional_telemetry,
and visual UI components have been relocated to components.ui_core.ux_institutional_hub.
"""
from __future__ import annotations

import sys
import warnings
from typing import Any

warnings.warn(
    "Importing from 'core.ux_institutional_hub' is deprecated. "
    "Please import from 'core.institutional_telemetry' (for headless computation) "
    "or 'components.ui_core.ux_institutional_hub' (for UI components) instead.",
    DeprecationWarning,
    stacklevel=2,
)

import components.ui_core.ux_institutional_hub as _ui_target
import core.institutional_telemetry as _telemetry_target
from components.ui_core.ux_institutional_hub import *  # noqa: F401, F403, I001
from core.institutional_telemetry import *  # noqa: F401, F403, I001


class _UxHubProxy(sys.modules[__name__].__class__):
    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if hasattr(_ui_target, name) or name == "st":
            try:
                setattr(_ui_target, name, value)
            except Exception:
                pass
        if hasattr(_telemetry_target, name):
            try:
                setattr(_telemetry_target, name, value)
            except Exception:
                pass

    def __getattr__(self, name: str) -> Any:
        if hasattr(_ui_target, name):
            return getattr(_ui_target, name)
        return getattr(_telemetry_target, name)


sys.modules[__name__].__class__ = _UxHubProxy
