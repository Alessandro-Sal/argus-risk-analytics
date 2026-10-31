"""ARGUS — Compatibility Proxy for workspace_context.

Relocated to core.workspace.context for clean modular workspace architecture.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'workspace_context' is deprecated. Please import from 'core.workspace.context' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.workspace.context import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.workspace.context")
    return getattr(mod, name)
