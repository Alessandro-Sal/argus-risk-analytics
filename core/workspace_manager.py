"""ARGUS — Compatibility Proxy for workspace_manager.

Relocated to core.workspace.manager for clean modular workspace architecture.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'workspace_manager' is deprecated. Please import from 'core.workspace.manager' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.workspace.manager import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.workspace.manager")
    return getattr(mod, name)
