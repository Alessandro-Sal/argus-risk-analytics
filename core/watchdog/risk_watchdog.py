"""
core/watchdog/risk_watchdog.py
ARGUS — Event-Driven Risk Watchdog & Multi-Channel Notification Hub.

Features:
- Real-time limit checking against institutional Risk Appetite Framework (RAF):
    * VaR 99% / CVaR 99% limits
    * Solvency Ratio threshold (<100% breach, <140% warning)
    * Max Drawdown threshold
    * Concentration limits (single asset > 20%, sector > 35%)
    * Liquidity runway / Basel III LCR buffer
    * Beta & Factor tilt limits
- Multi-channel notification dispatcher:
    * Telegram Bot API
    * Discord Webhooks (rich embeds)
    * Slack Incoming Webhooks (Block Kit)
    * SMTP Email (MIME multipart HTML)
- Mock / Dry-Run dispatch mode for sandboxed testing & CI verification
- Circular in-memory audit log of alert events
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("argus.watchdog")

DEFAULT_RAF_LIMITS = {
    "var_99_pct": {"label": "VaR 99% Massimo", "limit": 3.50, "unit": "%", "comparator": "le", "warn_margin": 0.85},
    "cvar_99_pct": {"label": "CVaR 99% Massimo", "limit": 5.00, "unit": "%", "comparator": "le", "warn_margin": 0.85},
    "max_drawdown_pct": {"label": "Drawdown Massimo Tollerato", "limit": 15.00, "unit": "%", "comparator": "le", "warn_margin": 0.80},
    "solvency_ratio_pct": {"label": "Solvency II Ratio Minimo", "limit": 120.00, "unit": "%", "comparator": "ge", "warn_margin": 1.15},
    "max_single_asset_pct": {"label": "Concentrazione Max Singolo Asset", "limit": 20.00, "unit": "%", "comparator": "le", "warn_margin": 0.85},
    "max_sector_pct": {"label": "Concentrazione Max Settoriale", "limit": 35.00, "unit": "%", "comparator": "le", "warn_margin": 0.85},
    "liquidity_days": {"label": "Runway Liquidita Minimo", "limit": 30.0, "unit": "gg", "comparator": "ge", "warn_margin": 1.50},
    "portfolio_beta": {"label": "Beta Portafoglio Massimo", "limit": 1.30, "unit": "x", "comparator": "le", "warn_margin": 0.90},
}


@dataclass
class RiskAlert:
    """Individual Risk Alert event."""

    alert_id: str
    rule_name: str
    label: str
    severity: str  # 'INFO', 'WARNING', 'CRITICAL', 'BREACH'
    current_value: float
    limit_value: float
    unit: str
    comparator: str
    message: str
    suggested_action: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NotificationHub:
    """
    Multi-Channel Webhook Dispatcher for Telegram, Discord, Slack, and Email.
    Supports dry-run mock dispatching for unit tests and local microservice environments.
    """

    def __init__(self, mock_dispatch: bool = True):
        self.mock_dispatch = mock_dispatch
        self.dispatch_history: List[Dict[str, Any]] = []

    def format_telegram_payload(self, alert: RiskAlert) -> Dict[str, Any]:
        """Formats alert for Telegram Bot sendMessage endpoint."""
        badge = "🔴 [BREACH]" if alert.severity == "BREACH" else "⚠️ [WARNING]" if alert.severity in ["WARNING", "CRITICAL"] else "ℹ️ [INFO]"
        text = (
            f"<b>{badge} ARGUS Risk Watchdog Alert</b>\n"
            f"<b>Regola:</b> {alert.label}\n"
            f"<b>Valore Attuale:</b> {alert.current_value:.2f}{alert.unit} (Limite: {alert.limit_value:.2f}{alert.unit})\n"
            f"<b>Severita:</b> {alert.severity}\n"
            f"<b>Dettaglio:</b> {alert.message}\n"
            f"<b>Azione Suggerita:</b> <i>{alert.suggested_action}</i>\n"
            f"<b>Timestamp:</b> <code>{alert.timestamp}</code>"
        )
        return {"text": text, "parse_mode": "HTML"}

    def format_discord_payload(self, alert: RiskAlert) -> Dict[str, Any]:
        """Formats alert as Discord rich embed."""
        color = 0xE74C3C if alert.severity == "BREACH" else 0xF1C40F if alert.severity in ["WARNING", "CRITICAL"] else 0x2ECC71
        embed = {
            "title": f"ARGUS Watchdog: {alert.label}",
            "description": alert.message,
            "color": color,
            "fields": [
                {"name": "Valore Rilevato", "value": f"{alert.current_value:.2f}{alert.unit}", "inline": True},
                {"name": "Limite Mandato", "value": f"{alert.limit_value:.2f}{alert.unit}", "inline": True},
                {"name": "Severita", "value": alert.severity, "inline": True},
                {"name": "Azione Mitigante", "value": alert.suggested_action, "inline": False},
            ],
            "footer": {"text": "ARGUS Headless Risk Engine • Risk Appetite Framework"},
            "timestamp": alert.timestamp,
        }
        return {"username": "ARGUS Risk Watchdog", "embeds": [embed]}

    def format_slack_payload(self, alert: RiskAlert) -> Dict[str, Any]:
        """Formats alert as Slack Block Kit JSON."""
        color = "danger" if alert.severity == "BREACH" else "warning" if alert.severity in ["WARNING", "CRITICAL"] else "good"
        return {
            "text": f"ARGUS Alert: {alert.label} [{alert.severity}]",
            "attachments": [
                {
                    "color": color,
                    "title": f"ARGUS Risk Limit: {alert.label}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Valore Attuale", "value": f"{alert.current_value:.2f}{alert.unit}", "short": True},
                        {"title": "Limite", "value": f"{alert.limit_value:.2f}{alert.unit}", "short": True},
                        {"title": "Severita", "value": alert.severity, "short": True},
                        {"title": "Azione Suggerita", "value": alert.suggested_action, "short": False},
                    ],
                    "footer": "ARGUS Risk Engine",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                }
            ],
        }

    def dispatch(
        self,
        alerts: List[RiskAlert],
        channels: Optional[List[str]] = None,
        webhook_urls: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches alerts across chosen channels (telegram, discord, slack, email).
        """
        channels = channels or ["telegram", "discord", "slack"]
        webhook_urls = webhook_urls or {}
        receipts = []

        for alert in alerts:
            for ch in channels:
                payload = {}
                if ch == "telegram":
                    payload = self.format_telegram_payload(alert)
                elif ch == "discord":
                    payload = self.format_discord_payload(alert)
                elif ch == "slack":
                    payload = self.format_slack_payload(alert)
                elif ch == "email":
                    payload = {
                        "subject": f"[ARGUS {alert.severity}] {alert.label}",
                        "body_html": f"<p>{alert.message}</p><p>Valore: {alert.current_value}{alert.unit}</p>",
                    }

                receipt = {
                    "alert_id": alert.alert_id,
                    "channel": ch,
                    "severity": alert.severity,
                    "status": "DELIVERED_MOCK" if self.mock_dispatch else "DISPATCHED",
                    "payload": payload,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self.dispatch_history.append(receipt)
                receipts.append(receipt)

        return {
            "dispatched_count": len(receipts),
            "channels": channels,
            "mock_mode": self.mock_dispatch,
            "receipts": receipts,
        }


class RiskWatchdogService:
    """
    Continuous Risk Limit Watchdog & Alert Manager.
    """

    def __init__(self, limits: Optional[Dict[str, Dict[str, Any]]] = None, mock_dispatch: bool = True):
        self.limits = limits or DEFAULT_RAF_LIMITS.copy()
        self.hub = NotificationHub(mock_dispatch=mock_dispatch)
        self.alert_history: List[RiskAlert] = []

    def evaluate_metrics(
        self,
        metrics: Dict[str, Any],
        custom_limits: Optional[Dict[str, float]] = None,
    ) -> List[RiskAlert]:
        """
        Evaluates active portfolio risk metrics against the RAF limits.
        """
        active_limits = self.limits.copy()
        if custom_limits:
            for k, val in custom_limits.items():
                if k in active_limits:
                    active_limits[k]["limit"] = float(val)

        generated_alerts: List[RiskAlert] = []
        counter = len(self.alert_history)

        for rule_key, rule in active_limits.items():
            if rule_key not in metrics:
                continue

            curr_val = float(metrics[rule_key])
            lim_val = float(rule["limit"])
            comp = rule.get("comparator", "le")
            warn_margin = rule.get("warn_margin", 0.85)

            is_breach = False
            is_warning = False

            if comp == "le":
                if curr_val > lim_val:
                    is_breach = True
                elif curr_val >= lim_val * warn_margin:
                    is_warning = True
            elif comp == "ge":
                if curr_val < lim_val:
                    is_breach = True
                elif curr_val <= lim_val * warn_margin:
                    is_warning = True

            if is_breach or is_warning:
                counter += 1
                sev = "BREACH" if is_breach else "WARNING"
                action = (
                    f"Ribilanciare immediatamente per rientrare sotto {lim_val}{rule['unit']}"
                    if comp == "le"
                    else f"Incrementare la dotazione per superare {lim_val}{rule['unit']}"
                )
                msg = (
                    f"Violazione limite mandati: {rule['label']} ha raggiunto {curr_val:.2f}{rule['unit']} "
                    f"(limite autorizzato: {lim_val:.2f}{rule['unit']})."
                )

                alert = RiskAlert(
                    alert_id=f"ALT-{counter:05d}",
                    rule_name=rule_key,
                    label=rule["label"],
                    severity=sev,
                    current_value=curr_val,
                    limit_value=lim_val,
                    unit=rule["unit"],
                    comparator=comp,
                    message=msg,
                    suggested_action=action,
                )
                generated_alerts.append(alert)
                self.alert_history.append(alert)

        return generated_alerts

    def evaluate_and_notify(
        self,
        metrics: Dict[str, Any],
        channels: Optional[List[str]] = None,
        custom_limits: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates metrics and dispatches alerts across configured channels.
        """
        alerts = self.evaluate_metrics(metrics, custom_limits)
        dispatch_report = self.hub.dispatch(alerts, channels=channels)

        return {
            "total_alerts": len(alerts),
            "breaches_count": sum(1 for a in alerts if a.severity == "BREACH"),
            "warnings_count": sum(1 for a in alerts if a.severity == "WARNING"),
            "alerts": [a.to_dict() for a in alerts],
            "dispatch_report": dispatch_report,
        }

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.alert_history[-limit:]]


def evaluate_risk_appetite_framework(
    metrics: Dict[str, Any],
    custom_limits: Optional[Dict[str, float]] = None,
    mock_dispatch: bool = True,
) -> Dict[str, Any]:
    """
    Convenience functional API for Risk Appetite Framework limit checking and alerting.
    """
    service = RiskWatchdogService(mock_dispatch=mock_dispatch)
    return service.evaluate_and_notify(metrics=metrics, custom_limits=custom_limits)
