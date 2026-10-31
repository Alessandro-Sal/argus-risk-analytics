"""ARGUS — Compatibility Proxy for workspace_engine.

Relocated to core.workspace.engine for clean modular workspace architecture.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'workspace_engine' is deprecated. Please import from 'core.workspace.engine' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.workspace.engine import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.workspace.engine")
    return getattr(mod, name)
