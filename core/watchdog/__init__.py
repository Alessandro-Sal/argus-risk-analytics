"""
core/watchdog/__init__.py
ARGUS — Event-Driven Risk Watchdog & Notification Hub.
"""

from core.watchdog.risk_watchdog import (
    DEFAULT_RAF_LIMITS,
    NotificationHub,
    RiskAlert,
    RiskWatchdogService,
    evaluate_risk_appetite_framework,
)

__all__ = [
    "DEFAULT_RAF_LIMITS",
    "NotificationHub",
    "RiskAlert",
    "RiskWatchdogService",
    "evaluate_risk_appetite_framework",
]
