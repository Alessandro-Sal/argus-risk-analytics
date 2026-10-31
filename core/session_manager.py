"""ARGUS — Compatibility Proxy for session_manager.

Relocated to core.workspace.session for clean modular workspace architecture.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'session_manager' is deprecated. Please import from 'core.workspace.session' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.workspace.session import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.workspace.session")
    return getattr(mod, name)
