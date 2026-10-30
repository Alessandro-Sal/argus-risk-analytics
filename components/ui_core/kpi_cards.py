"""
ARGUS Institutional KPI Cards & Financial State Badges
======================================================
Standardized visual metrics, delta indicators, vector sparklines, and status badges
aligned with docs/DESIGN.md and institutional FinTech specifications.
"""

from __future__ import annotations

import logging
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import streamlit as st

logger = logging.getLogger("argus.kpi_cards")


def generate_svg_sparkline(
    data: Sequence[Union[float, int]],
    width: int = 80,
    height: int = 24,
    color: Optional[str] = None,
) -> str:
    """
    Genera una stringa SVG pura ultra-leggera per micro-grafici sparkline inline.
    Nessuna dipendenza esterna, zero latenza computazionale, rendering vettoriale puro.
    """
    if not data or len(data) < 2:
        return ""

    clean_data: List[float] = []
    for x in data:
        try:
            val = float(x)
            if not np.isnan(val) and not np.isinf(val):
                clean_data.append(val)
        except (ValueError, TypeError):
            continue

    if len(clean_data) < 2:
        return ""

    min_val = min(clean_data)
    max_val = max(clean_data)
    val_range = max_val - min_val
    if val_range == 0:
        val_range = 1.0

    padding_top = 2
    padding_bottom = 2
    effective_h = height - padding_top - padding_bottom
    n = len(clean_data)

    points: List[str] = []
    for i, val in enumerate(clean_data):
        x = (i / (n - 1)) * (width - 4) + 2
        y = padding_top + (1.0 - (val - min_val) / val_range) * effective_h
        points.append(f"{x:.1f},{y:.1f}")

    poly_points = " ".join(points)

    if color is None:
        stroke_color = "#10b981" if clean_data[-1] >= clean_data[0] else "#ef4444"
    else:
        stroke_color = color

    last_x = width - 2
    last_val = clean_data[-1]
    last_y = padding_top + (1.0 - (last_val - min_val) / val_range) * effective_h

    dot_svg = (
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.2" fill="{stroke_color}" '
        f'style="filter: drop-shadow(0 0 2px {stroke_color});" />'
    )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="overflow:visible; vertical-align:middle; flex-shrink:0;">'
        f'<polyline fill="none" stroke="{stroke_color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{poly_points}" />'
        f"{dot_svg}"
        f"</svg>"
    )


def render_status_badge(
    text: str,
    level: str = "success",
    pulse: bool = False,
    icon: Optional[str] = None,
    tooltip: Optional[str] = None,
) -> str:
    """
    Badge semantico compatto di livello istituzionale (Real Data, Sandbox, Synced, Offline).
    Restituisce HTML sicuro o renderizza inline.
    """
    level_lower = (level or "info").lower()
    if level_lower in ["success", "green", "bull", "real"]:
        bg = "rgba(16, 185, 129, 0.15)"
        border = "rgba(16, 185, 129, 0.35)"
        color = "#10b981"
        default_icon = "●"
    elif level_lower in ["warning", "warn", "gold", "amber", "sandbox", "simulated"]:
        bg = "rgba(245, 158, 11, 0.15)"
        border = "rgba(245, 158, 11, 0.35)"
        color = "#f59e0b"
        default_icon = "▲"
    elif level_lower in ["danger", "error", "red", "bear", "offline"]:
        bg = "rgba(239, 68, 68, 0.15)"
        border = "rgba(239, 68, 68, 0.35)"
        color = "#ef4444"
        default_icon = "■"
    elif level_lower in ["info", "blue", "cyan", "synced"]:
        bg = "rgba(6, 182, 212, 0.15)"
        border = "rgba(6, 182, 212, 0.35)"
        color = "#06b6d4"
        default_icon = "◆"
    else:
        bg = "rgba(100, 116, 139, 0.15)"
        border = "rgba(100, 116, 139, 0.30)"
        color = "#94a3b8"
        default_icon = "○"

    display_icon = icon if icon is not None else default_icon
    pulse_class = " argus-pulse" if pulse else ""
    title_attr = f' title="{tooltip}"' if tooltip else ""

    return (
        f'<span class="argus-badge{pulse_class}"{title_attr} style="'
        f"display: inline-flex; align-items: center; gap: 5px; "
        f"background: {bg}; border: 1px solid {border}; color: {color}; "
        f"font-family: 'Outfit', sans-serif; font-size: 11px; font-weight: 700; "
        f'padding: 3px 9px; border-radius: 12px; letter-spacing: 0.5px; text-transform: uppercase;">'
        f'<span style="font-size: 9px;">{display_icon}</span>'
        f"<span>{text}</span>"
        f"</span>"
    )


def render_state_badge(
    mode: str = "real",
    label: Optional[str] = None,
    pulse: bool = False,
) -> None:
    """Renderizza direttamente uno Streamlit state badge istituzionale."""
    mode_l = mode.lower()
    if mode_l in ["real", "real_data", "live"]:
        html = render_status_badge(label or "LIVE REAL DATA", level="success", pulse=pulse, icon="⚡")
    elif mode_l in ["sandbox", "demo", "simulated"]:
        html = render_status_badge(label or "SANDBOX DEMO", level="warning", pulse=False, icon="🧪")
    elif mode_l in ["synced", "cloud"]:
        html = render_status_badge(label or "CLOUD SYNCED", level="info", pulse=False, icon="☁️")
    elif mode_l in ["offline", "local"]:
        html = render_status_badge(label or "LOCAL OFFLINE", level="danger", pulse=False, icon="💾")
    else:
        html = render_status_badge(label or mode.upper(), level="neutral", pulse=pulse)
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_metric(
    title: str,
    value: Union[str, float, int],
    delta: Optional[str] = None,
    sparkline_data: Optional[Sequence[Union[float, int]]] = None,
    tooltip: Optional[str] = None,
    subtitle: Optional[str] = None,
    level: str = "normal",
    theme_accent: str = "auto",
) -> None:
    """
    Componente KPI istituzionale unificato Fintech Institutional Grade:
    - Valore formattato rigorosamente in font monospace con tabular figures (JetBrains Mono)
    - Delta direzionale con colorazione semantica automatica
    - Micro-grafico sparkline SVG vettoriale inline
    - Bordo attivo glassmorphism coerente con Obsidian Dark Theme
    """
    d_html = ""
    if delta is not None and str(delta).strip():
        d_str = str(delta).strip()
        is_neg = d_str.startswith("-") or "loss" in d_str.lower() or "down" in d_str.lower()
        is_pos = d_str.startswith("+") or "gain" in d_str.lower() or "up" in d_str.lower()

        if is_pos:
            d_color = "#10b981"
            d_bg = "rgba(16, 185, 129, 0.12)"
            arrow = "▲"
        elif is_neg:
            d_color = "#ef4444"
            d_bg = "rgba(239, 68, 68, 0.12)"
            arrow = "▼"
        else:
            d_color = "#8b949e"
            d_bg = "rgba(139, 148, 158, 0.12)"
            arrow = "●"

        clean_d = d_str.lstrip("+-▲▼").strip()
        d_html = (
            f'<div style="display:inline-flex; align-items:center; gap:3px; background:{d_bg}; '
            f'color:{d_color}; font-size:11px; font-weight:700; font-family:\'JetBrains Mono\', monospace; '
            f'padding:2px 7px; border-radius:6px; margin-top:4px;">'
            f"<span>{arrow}</span><span>{clean_d}</span></div>"
        )

    spark_html = ""
    if sparkline_data and len(sparkline_data) >= 2:
        spark_html = generate_svg_sparkline(sparkline_data, width=70, height=22)

    sub_html = (
        f'<div style="font-size:11px; color:#6e7681; margin-top:3px; font-family:\'Outfit\', sans-serif;">{subtitle}</div>'
        if subtitle
        else ""
    )

    tooltip_html = (
        f'<span title="{tooltip}" style="cursor:help; font-size:12px; color:#8b949e; margin-left:4px;">ⓘ</span>'
        if tooltip
        else ""
    )

    accent_border = "#ff9900" if theme_accent == "auto" else theme_accent
    if level == "danger":
        accent_border = "#ef4444"
    elif level == "success":
        accent_border = "#10b981"
    elif level == "warning":
        accent_border = "#f59e0b"

    html = f"""
    <div class="bento-kpi-card" style="
        background: rgba(22, 27, 34, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid {accent_border};
        border-radius: 10px;
        padding: 14px 16px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, border-color 0.15s ease;
        margin-bottom: 8px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-family:'Outfit', sans-serif; font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:0.6px; color:#8b949e;">
                {title} {tooltip_html}
            </div>
            {spark_html}
        </div>
        <div style="font-family:'JetBrains Mono', monospace; font-size:22px; font-weight:800; color:#f0f6fc; margin-top:6px; letter-spacing:-0.5px;">
            {value}
        </div>
        {d_html}
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_card(
    label: str,
    value: Union[str, float, int],
    delta: Optional[str] = None,
    subtitle: Optional[str] = None,
    sparkline_data: Optional[Sequence[Union[float, int]]] = None,
    tooltip: Optional[str] = None,
    theme_accent: str = "auto",
) -> None:
    """Alias compatibile per render_kpi_metric."""
    render_kpi_metric(
        title=label,
        value=value,
        delta=delta,
        sparkline_data=sparkline_data,
        tooltip=tooltip,
        subtitle=subtitle,
        theme_accent=theme_accent,
    )


def render_glassmorphic_card(
    title: str,
    body_html: str,
    badge_text: Optional[str] = None,
    badge_level: str = "info",
    accent_color: str = "#ff9900",
) -> None:
    """Container a scatola nera glassmorphic istituzionale per tabelle o sezioni descrittive."""
    badge_html = render_status_badge(badge_text, level=badge_level) if badge_text else ""
    html = f"""
    <div style="
        background: rgba(22, 27, 34, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 2px solid {accent_color};
        border-radius: 12px;
        padding: 16px 20px;
        backdrop-filter: blur(14px);
        margin-bottom: 12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="font-family:'Outfit', sans-serif; font-size:14px; font-weight:700; color:#f0f6fc; letter-spacing:0.3px;">
                {title}
            </div>
            {badge_html}
        </div>
        <div>
            {body_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    positive: Optional[bool] = True,
    help_text: Optional[str] = None,
    is_positive: Optional[bool] = None,
    delta_color: Optional[str] = None,
) -> None:
    """Card metrica retrocompatibile a standard Obsidian con help popover pulito."""
    render_kpi_metric(
        title=label,
        value=value,
        delta=delta,
        tooltip=re.sub(r"<[^>]+>", "", help_text) if help_text else None,
        level="success" if (positive is True or is_positive is True) else ("danger" if (positive is False or is_positive is False) else "normal"),
    )
