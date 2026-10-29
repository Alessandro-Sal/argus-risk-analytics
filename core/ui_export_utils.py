"""Backward compatibility proxy module for core/ui_export_utils.py.

Deprecated: This visual UI module has been relocated to components.ui_core.ui_export_utils.
Importing from this path is deprecated and will be removed in a future major version.
"""
from __future__ import annotations

import sys
import warnings
from typing import Any

warnings.warn(
    "Importing from 'core.ui_export_utils' is deprecated. "
    "Please import from 'components.ui_core.ui_export_utils' instead.",
    DeprecationWarning,
    stacklevel=2,
)

import components.ui_core.ui_export_utils as _export_target
from components.ui_core.ui_export_utils import *  # noqa: F401, F403


class _ExportProxy(sys.modules[__name__].__class__):
    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        try:
            setattr(_export_target, name, value)
        except Exception:
            pass
        if "components.ui_core.ui_utils" in sys.modules:
            try:
                mod_utils = sys.modules["components.ui_core.ui_utils"]
                if hasattr(mod_utils, name):
                    setattr(mod_utils, name, value)
            except Exception:
                pass

    def __getattr__(self, name: str) -> Any:
        return getattr(_export_target, name)


sys.modules[__name__].__class__ = _ExportProxy
