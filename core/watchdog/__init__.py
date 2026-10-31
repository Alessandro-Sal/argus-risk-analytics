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
from core.watchdog.unified_notification_center import (
    UnifiedNotification,
    check_active_analysis,
    get_unified_compliance_notifications,
)
from core.watchdog.wealth_watchdog import (
    WatchdogAlert,
    WealthWatchdog,
    render_wealth_watchdog_banner,
)

__all__ = [
    "DEFAULT_RAF_LIMITS",
    "NotificationHub",
    "RiskAlert",
    "RiskWatchdogService",
    "evaluate_risk_appetite_framework",
    "UnifiedNotification",
    "check_active_analysis",
    "get_unified_compliance_notifications",
    "WatchdogAlert",
    "WealthWatchdog",
    "render_wealth_watchdog_banner",
]
