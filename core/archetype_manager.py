"""ARGUS — Compatibility Proxy for archetype_manager.

Relocated to core.workspace.demo_seeder for clean modular workspace architecture.
All functions and symbols are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'archetype_manager' is deprecated. Please import from 'core.workspace.demo_seeder' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.workspace.demo_seeder import *  # noqa: F401, F403


def __getattr__(name: str):
    import importlib

    mod = importlib.import_module("core.workspace.demo_seeder")
    return getattr(mod, name)
