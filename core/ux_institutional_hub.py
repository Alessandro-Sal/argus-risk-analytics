"""Backward compatibility proxy module for core.ux_institutional_hub.

Deprecated: Core headless calculation/telemetry has been relocated to core.institutional_telemetry,
and visual UI components have been relocated to components.ui_core.ux_institutional_hub.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.ux_institutional_hub' is deprecated. "
    "Please import from 'core.institutional_telemetry' (for headless computation) "
    "or 'components.ui_core.ux_institutional_hub' (for UI components) instead.",
    DeprecationWarning,
    stacklevel=2,
)

from core.institutional_telemetry import *  # noqa: F401, F403, I001
from components.ui_core.ux_institutional_hub import *  # noqa: F401, F403, I001
