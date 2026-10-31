# ==============================================================================
# core/wealth/wealth_watchdog.py
# ARGUS — Backward Compatibility Shim for core.watchdog.wealth_watchdog
# ==============================================================================

from core.watchdog.wealth_watchdog import (
    WatchdogAlert,
    WealthWatchdog,
    render_wealth_watchdog_banner,
)

__all__ = [
    "WatchdogAlert",
    "WealthWatchdog",
    "render_wealth_watchdog_banner",
]
