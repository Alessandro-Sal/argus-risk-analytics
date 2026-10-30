"""
ARGUS Institutional Theme Engine & Unified CSS Injection
=========================================================
Centralized style architecture aligned with docs/DESIGN.md and .streamlit/config.toml:
- Single-point injection with session caching to prevent layout shifts & font FOUC
- Dynamic theme resolution (Midnight Obsidian, Cyberpunk Neon, Emerald Wealth)
- Full-spectrum institutional CSS: Glassmorphism, high-density data tables, telemetry ribbons,
  monospace numerical typography, and smooth transitions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger("argus.theme")

THEME_CONFIGS: Dict[str, Dict[str, str]] = {
    "Midnight Obsidian": {
        "name": "Midnight Obsidian",
        "bg_gradient": "radial-gradient(circle at 15% 50%, #0d1117, #161b22, #0d1117)",
        "accent_color": "#ff9900",
        "accent_gradient": "linear-gradient(180deg, #ff9900, #ff3366)",
        "card_bg": "rgba(22, 27, 34, 0.6)",
        "border_color": "rgba(255, 255, 255, 0.08)",
        "text_primary": "#e6edf3",
        "text_muted": "#8b949e",
    },
    "Cyberpunk Neon": {
        "name": "Cyberpunk Neon",
        "bg_gradient": "radial-gradient(circle at 15% 50%, #050811, #0a1124, #050811)",
        "accent_color": "#00f3ff",
        "accent_gradient": "linear-gradient(180deg, #00f3ff, #00ff66)",
        "card_bg": "rgba(10, 17, 36, 0.7)",
        "border_color": "rgba(0, 243, 255, 0.15)",
        "text_primary": "#f0f6fc",
        "text_muted": "#8b949e",
    },
    "Emerald Wealth": {
        "name": "Emerald Wealth",
        "bg_gradient": "radial-gradient(circle at 15% 50%, #06140e, #0d281c, #06140e)",
        "accent_color": "#00c853",
        "accent_gradient": "linear-gradient(180deg, #00c853, #ffd700)",
        "card_bg": "rgba(13, 40, 28, 0.7)",
        "border_color": "rgba(16, 185, 129, 0.15)",
        "text_primary": "#e6edf3",
        "text_muted": "#8b949e",
    },
}


def get_active_theme_config() -> Dict[str, str]:
    """Restituisce i token grafici per il tema attivo in session_state."""
    theme_name = st.session_state.get("ui_theme", "Midnight Obsidian") if hasattr(st, "session_state") else "Midnight Obsidian"
    return THEME_CONFIGS.get(theme_name, THEME_CONFIGS["Midnight Obsidian"])

def inject_custom_css(force: bool = False) -> None:
    """Inietta il foglio di stile CSS istituzionale garantendo zero duplicazioni nel medesimo run e persistenza continua nei rerun."""
    theme = st.session_state.get("ui_theme", "Midnight Obsidian") if hasattr(st, "session_state") else "Midnight Obsidian"

    # Anti-duplicazione nel MEDESIMO run di esecuzione (senza bloccare i rerun successivi)
    # Streamlit resetta ctx.cursors = {} all'inizio di ogni singolo run/rerun in ScriptRunContext.reset()
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        if ctx is not None and hasattr(ctx, "cursors") and isinstance(ctx.cursors, dict):
            if not force and ctx.cursors.get("_argus_css_injected_in_run", False):
                return
            ctx.cursors["_argus_css_injected_in_run"] = True
    except Exception:
        pass

    try:
        from components.ui_core.loading_states import inject_loading_css
        inject_loading_css()
    except Exception:
        pass

    if theme == "Cyberpunk Neon":
        bg_gradient = "radial-gradient(circle at 15% 50%, #050811, #0a1124, #050811)"
        accent_color = "#00f3ff"
        accent_gradient = "linear-gradient(180deg, #00f3ff, #00ff66)"
        card_bg = "rgba(10, 17, 36, 0.7)"
    elif theme == "Emerald Wealth":
        bg_gradient = "radial-gradient(circle at 15% 50%, #06140e, #0d281c, #06140e)"
        accent_color = "#00c853"
        accent_gradient = "linear-gradient(180deg, #00c853, #ffd700)"
        card_bg = "rgba(13, 40, 28, 0.7)"
    else:  # Midnight Obsidian
        bg_gradient = "radial-gradient(circle at 15% 50%, #0d1117, #161b22, #0d1117)"
        accent_color = "#ff9900"
        accent_gradient = "linear-gradient(180deg, #ff9900, #ff3366)"
        card_bg = "rgba(22, 27, 34, 0.6)"

    st.markdown(
        f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            letter-spacing: -0.01em;
        }}

        /* Monospace Tabular Figures for All Quantitative Values */
        .metric-value, [data-testid="stMetricValue"], [data-testid="stMetricDelta"], code, .mono-num, td.mono-num, th.mono-num {{
            font-family: 'JetBrains Mono', 'Outfit', monospace !important;
            font-feature-settings: "tnum" 1, "zero" 1 !important;
        }}

        /* High-Density Institutional Data Grids */
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            background: rgba(13, 17, 23, 0.6) !important;
        }}
        [data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {{
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 12px !important;
            font-feature-settings: "tnum" 1, "zero" 1 !important;
            padding: 4px 8px !important;
        }}
        [data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th {{
            font-family: 'Outfit', sans-serif !important;
            font-size: 11px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            color: #8b949e !important;
            background: rgba(22, 27, 34, 0.8) !important;
        }}

        /* Institutional Tax & Risk Badges */
        .argus-badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 12px;
            letter-spacing: 0.4px;
            text-transform: uppercase;
        }}
        .argus-badge-tax-oicr {{
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .argus-badge-tax-cg {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .argus-badge-risk-alert {{
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        /* Responsive Ergonomics for Glassmorphic Modals, Ribbons & Small Screens */
        @media (max-width: 768px) {{
            [class*="modal-content-"], [class*="bento-modal-content-"] {{
                width: 95vw !important;
                max-width: 95vw !important;
                max-height: 85vh !important;
                padding: 16px 18px !important;
                overflow-y: auto !important;
            }}
            .institutional-telemetry-ribbon {{
                padding: 8px 12px !important;
            }}
            .institutional-telemetry-ribbon > div {{
                flex-wrap: wrap !important;
                gap: 6px !important;
            }}
            .bento-kpi-card {{
                padding: 12px 14px !important;
            }}
        }}

        /* Institutional Skeleton Shimmer Loaders (Anti-CLS Layout Stability) */
        @keyframes argus-shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}
        .argus-skeleton {{
            background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%);
            background-size: 200% 100%;
            animation: argus-shimmer 1.8s infinite ease-in-out;
            border-radius: 6px;
        }}
        .argus-skeleton-card {{
            border: 1px solid rgba(255, 255, 255, 0.06);
            background: rgba(17, 24, 39, 0.5);
            border-radius: 10px;
            padding: 16px;
            height: 105px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}


        /* Institutional Typography Hierarchy */
        h1, [data-testid="stHeading"] h1, [data-testid="stHeader"] h1 {{
            font-size: 1.85rem !important;
            font-weight: 750 !important;
            letter-spacing: -0.5px !important;
            line-height: 1.25 !important;
        }}
        h2, [data-testid="stHeading"] h2 {{
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.3px !important;
        }}
        h3, [data-testid="stHeading"] h3 {{
            font-size: 1.25rem !important;
            font-weight: 650 !important;
        }}
        h4, [data-testid="stHeading"] h4 {{
            font-size: 1.05rem !important;
            font-weight: 650 !important;
        }}

        /* Compact Institutional Dividers */
        hr, [data-testid="stDivider"], hr[data-testid="stDivider"] {{
            margin-top: 8px !important;
            margin-bottom: 12px !important;
            border-color: rgba(255, 255, 255, 0.08) !important;
            padding: 0 !important;
        }}
        div:has(> hr), div:has(> [data-testid="stDivider"]) {{
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }}

        /* ── Above-the-fold Viewport Optimization (Zero Dead Space) ── */
        header[data-testid="stHeader"],
        [data-testid="stHeader"] {{
            background: transparent !important;
            background-color: transparent !important;
            color: #ffffff !important;
            height: 0px !important;
            min-height: 0px !important;
            max-height: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            border: none !important;
            overflow: hidden !important;
            pointer-events: none !important;
            z-index: 99 !important;
        }}

        /* Comprehensive Removal of Streamlit Deploy Button & Top Decoration ONLY */
        [data-testid="stDecoration"],
        .stDeployButton,
        [data-testid="stDeployButton"],
        .stAppDeployButton,
        button[title="Deploy"],
        div:has(> .stDeployButton) {{
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            height: 0px !important;
            width: 0px !important;
            pointer-events: none !important;
        }}

        /* Ensure Streamlit Toolbar is transparent and allows collapsedControl to show */
        header[data-testid="stHeader"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        div[data-testid="stToolbar"] {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            height: 0px !important;
            min-height: 0px !important;
        }}

        /* Mantieni il controllo di apertura sidebar (Panel Dock Expand) sempre visibile a sidebar chiusa */
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapsedControl"],
        div[data-testid="collapsedControl"],
        [data-testid="stExpandSidebarButton"],
        button[data-testid="stExpandSidebarButton"],
        [data-testid="stHeader"] [data-testid="collapsedControl"],
        [data-testid="stHeader"] [data-testid="stExpandSidebarButton"] {{
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            position: fixed !important;
            top: 6px !important;
            left: 8px !important;
            z-index: 999999 !important;
        }}
        [data-testid="collapsedControl"] button,
        button[data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"],
        button[data-testid="stExpandSidebarButton"] {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            visibility: visible !important;
            color: #ff9900 !important;
            background: rgba(22, 27, 34, 0.95) !important;
            border: 1px solid rgba(255, 153, 0, 0.4) !important;
            border-radius: 8px !important;
            padding: 4px 6px !important;
            width: 32px !important;
            height: 32px !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4) !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        [data-testid="collapsedControl"] button svg,
        button[data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stExpandSidebarButton"] svg,
        button[data-testid="stExpandSidebarButton"] svg {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] button::after,
        button[data-testid="stSidebarCollapsedControl"]::after,
        [data-testid="stExpandSidebarButton"]::after,
        button[data-testid="stExpandSidebarButton"]::after {{
            content: "" !important;
            display: block !important;
            width: 18px !important;
            height: 18px !important;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff9900' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2'%3E%3C/rect%3E%3Cpath d='M9 3v18'%3E%3C/path%3E%3Cpath d='m14 9 3 3-3 3'%3E%3C/path%3E%3C/svg%3E") center / 18px 18px no-repeat !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="collapsedControl"] button:hover,
        [data-testid="stExpandSidebarButton"]:hover,
        button[data-testid="stExpandSidebarButton"]:hover {{
            border-color: #ff9900 !important;
            background: rgba(33, 38, 45, 1) !important;
            box-shadow: 0 0 12px rgba(255, 153, 0, 0.35) !important;
        }}
        [data-testid="collapsedControl"] button:hover::after,
        button[data-testid="stSidebarCollapsedControl"]:hover::after,
        [data-testid="stExpandSidebarButton"]:hover::after,
        button[data-testid="stExpandSidebarButton"]:hover::after {{
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2'%3E%3C/rect%3E%3Cpath d='M9 3v18'%3E%3C/path%3E%3Cpath d='m14 9 3 3-3 3'%3E%3C/svg%3E") !important;
        }}

        /* Hide Streamlit Raw Page Nav (replaced by institutional tree rail) */
        [data-testid="stSidebarNav"] {{
            display: none !important;
            height: 0px !important;
            max-height: 0px !important;
            padding: 0px !important;
            margin: 0px !important;
            visibility: hidden !important;
            overflow: hidden !important;
        }}

        /* Header compatto della sidebar con pulsante di chiusura (Modern Panel Dock) */
        [data-testid="stSidebarHeader"],
        div[data-testid="stSidebarHeader"] {{
            min-height: 34px !important;
            padding: 4px 8px 0px 8px !important;
            margin: 0px !important;
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
            background: transparent !important;
            visibility: visible !important;
        }}

        /* Modern Panel Dock Collapse Button (Sostituisce il default <<) */
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"],
        div[data-testid="stSidebarCollapseButton"] button,
        div[data-testid="stSidebarHeader"] button {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            visibility: visible !important;
            opacity: 1 !important;
            color: #8b949e !important;
            background: rgba(22, 27, 34, 0.7) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            padding: 4px !important;
            width: 28px !important;
            height: 28px !important;
            margin: 0px !important;
            cursor: pointer !important;
            border-radius: 6px !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
        }}
        [data-testid="stSidebarCollapseButton"] svg,
        button[data-testid="stSidebarCollapseButton"] svg,
        div[data-testid="stSidebarCollapseButton"] button svg,
        div[data-testid="stSidebarHeader"] button svg {{
            display: none !important;
        }}
        [data-testid="stSidebarCollapseButton"]::after,
        button[data-testid="stSidebarCollapseButton"]::after,
        div[data-testid="stSidebarCollapseButton"] button::after,
        div[data-testid="stSidebarHeader"] button::after {{
            content: "" !important;
            display: block !important;
            width: 16px !important;
            height: 16px !important;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238b949e' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2'%3E%3C/rect%3E%3Cpath d='M9 3v18'%3E%3C/path%3E%3Cpath d='m16 15-3-3 3-3'%3E%3C/path%3E%3C/svg%3E") center / 16px 16px no-repeat !important;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stSidebarCollapseButton"]:hover,
        button[data-testid="stSidebarCollapseButton"]:hover,
        div[data-testid="stSidebarHeader"] button:hover {{
            color: #ff9900 !important;
            background: rgba(255, 153, 0, 0.15) !important;
            border-color: rgba(255, 153, 0, 0.4) !important;
            box-shadow: 0 0 10px rgba(255, 153, 0, 0.25) !important;
        }}
        [data-testid="stSidebarCollapseButton"]:hover::after,
        button[data-testid="stSidebarCollapseButton"]:hover::after,
        div[data-testid="stSidebarHeader"] button:hover::after {{
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ff9900' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2'%3E%3C/rect%3E%3Cpath d='M9 3v18'%3E%3C/path%3E%3Cpath d='m16 15-3-3 3-3'%3E%3C/svg%3E") !important;
        }}

        /* Institutional Segmented Controls (Never Wrap & Expand Buttons) */
        [data-testid="stSegmentedControl"],
        div[data-testid="stSegmentedControl"] > div {{
            display: flex !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
        }}
        [data-testid="stSegmentedControl"] button {{
            white-space: nowrap !important;
            text-overflow: ellipsis !important;
        }}

        /* Main Block Container - Generous Bottom Padding & Zero Top Dead Space */
        .block-container,
        [data-testid="block-container"],
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        div[data-testid="stAppViewBlockContainer"],
        section.main,
        section[data-testid="stMain"],
        section.main > div {{
            padding-top: 0.15rem !important;
            padding-bottom: 6.5rem !important;
            padding-left: 1.75rem !important;
            padding-right: 1.75rem !important;
            margin-top: 0px !important;
            max-width: 100% !important;
        }}

        /* Zero out invisible elements causing 1rem flex gap in stVerticalBlock */
        div[data-testid="stElementContainer"]:has(style:only-child),
        div[data-testid="stElementContainer"]:has(> div > style:only-child),
        div[data-testid="stElementContainer"]:has(#argus-cmd-palette-anchor),
        div[data-testid="stElementContainer"]:has(.argus-cmd-palette-anchor),
        div[data-testid="stElementContainer"]:empty {{
            display: none !important;
            height: 0px !important;
            min-height: 0px !important;
            max-height: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        /* Pull component iframe out of flow to prevent 1rem vertical gap */
        div[data-testid="stElementContainer"]:has(iframe[title*="components.html"]),
        div[data-testid="stCustomComponentV1"]:has(iframe) {{
            position: absolute !important;
            top: -9999px !important;
            left: -9999px !important;
            width: 0px !important;
            height: 0px !important;
            overflow: hidden !important;
            pointer-events: none !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        /* Tighten gap between command bar and first section/card */
        .stMainBlockContainer > [data-testid="stVerticalBlock"]:first-child,
        div[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlock"]:first-child {{
            gap: 6px !important;
        }}

        /* Tighten Sidebar Container */
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"] {{
            padding-top: 0px !important;
            margin-top: 0px !important;
        }}

        section[data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"],
        [data-testid="stSidebarUserContent"],
        section[data-testid="stSidebar"] .stSidebarContent,
        section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
            padding-top: 0.25rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            margin-top: 0px !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]:first-child,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{
            padding-top: 0px !important;
            margin-top: 0px !important;
            gap: 6px !important;
        }}

        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:first-child {{
            padding-top: 0px !important;
            margin-top: 0px !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: {bg_gradient};
            background-size: cover;
            background-attachment: fixed;
            color: #e6edf3;
        }}

        /* Seamless Non-wrapping Segmented Controls across all viewports */
        div[data-testid="stSegmentedControl"],
        [data-testid="stSegmentedControl"] > div,
        [data-testid="stSegmentedControl"] [role="radiogroup"] {{
            display: flex !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
        }}
        div[data-testid="stSegmentedControl"] button,
        [data-testid="stSegmentedControl"] button {{
            white-space: nowrap !important;
            flex: 1 1 auto !important;
            padding-left: 6px !important;
            padding-right: 6px !important;
            min-width: 0 !important;
            font-size: 12.5px !important;
        }}

        /* Native Streamlit Metric Cards - Linear / Terminal Glass Deck */
        [data-testid="stMetric"] {{
            background: {card_bg} !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
            backdrop-filter: blur(16px) !important;
            -webkit-backdrop-filter: blur(16px) !important;
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-2px) !important;
            border-color: rgba(255, 153, 0, 0.35) !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), 0 0 16px rgba(255, 153, 0, 0.12) !important;
        }}
        [data-testid="stMetricLabel"] p {{
            color: #8b949e !important;
            font-size: 11.5px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.6px !important;
        }}
        [data-testid="stMetricValue"] div {{
            color: #ffffff !important;
            font-size: 25px !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
        }}

        /* Metric Cards */
        .metric-card {{
            background: {card_bg};
            background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(13, 17, 23, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 12px 14px;
            position: relative;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            overflow: hidden !important;
            min-height: 104px !important;
            box-sizing: border-box !important;
            display: flex !important;
            flex-direction: column !important;
        }}

        .metric-card::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: {accent_gradient};
            box-shadow: 0 0 10px {accent_color};
            opacity: 0.9;
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 153, 0, 0.35);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35), 0 0 16px rgba(255, 153, 0, 0.15);
        }}

        .metric-label {{ 
            color: #94a3b8; 
            font-size: 11px; 
            font-weight: 650; 
            letter-spacing: 0.4px; 
            text-transform: uppercase;
            line-height: 1.2;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 4px !important;
            width: 100% !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
        }}
        .metric-label-text {{
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }}
        
        .metric-value {{ 
            background: linear-gradient(90deg, #ffffff 0%, #e2e8f0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: clamp(20px, 1.6vw, 26px); 
            font-weight: 800; 
            margin: 0;
            letter-spacing: -0.5px;
            line-height: 1.15;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}



        .metric-delta-pos {{
            color: #10b981 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            margin-top: 4px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
        }}

        .metric-delta-neg {{
            color: #ef4444 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            margin-top: 4px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
        }}

        .metric-delta-neutral {{
            color: #8b949e !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            margin-top: 4px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            line-height: 1.2 !important;
        }}

        /* ARGUS Clean Standard KPI Card (Zero Inline Styles) */
        .argus-clean-kpi-card {{
            background: linear-gradient(135deg, rgba(22, 27, 34, 0.85) 0%, rgba(13, 17, 23, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 12px 14px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
            min-height: 104px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .argus-clean-kpi-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        }}
        .argus-kpi-label {{
            color: #8b949e;
            font-size: 11px;
            font-weight: 650;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            line-height: 1.2;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 4px;
        }}
        .argus-kpi-value {{
            font-family: 'JetBrains Mono', monospace !important;
            font-feature-settings: "tnum" 1, "zero" 1 !important;
            font-size: clamp(20px, 1.5vw, 25px);
            font-weight: 800;
            color: #f0f6fc;
            margin: 4px 0 2px 0;
            letter-spacing: -0.5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}


        /* Streamlit Main Canvas Controls & Input Fields */
        [data-testid="stMain"] [data-baseweb="select"] > div {{
            background: rgba(22, 27, 34, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
            transition: all 0.18s ease !important;
        }}
        [data-testid="stMain"] [data-baseweb="select"] > div:hover {{
            border-color: rgba(255, 153, 0, 0.5) !important;
        }}
        [data-testid="stMain"] input {{
            background: rgba(22, 27, 34, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            color: #ffffff !important;
        }}
        [data-testid="stMain"] [data-testid="stDataFrame"] {{
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        }}

        /* Main Canvas Expanders */
        [data-testid="stMain"] [data-testid="stExpander"] {{
            background: rgba(22, 27, 34, 0.55) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(12px) !important;
            margin-top: 18px !important;
            margin-bottom: 16px !important;
        }}
        [data-testid="stMain"] [data-testid="stExpander"] summary {{
            font-weight: 600 !important;
            font-size: 13px !important;
            color: #e6edf3 !important;
            padding: 8px 14px !important;
        }}

        /* Popover scrolling & viewport constraints */
        [data-testid="stPopoverBody"], [data-testid="stPopoverContent"], div[data-testid="stPopoverBody"] {{
            max-height: 72vh !important;
            min-width: min(500px, 94vw) !important;
            max-width: min(580px, 96vw) !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-width: thin !important;
            scrollbar-color: rgba(255, 153, 0, 0.4) rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 153, 0, 0.3) !important;
            border-radius: 12px !important;
            background: rgba(13, 17, 23, 0.98) !important;
            backdrop-filter: blur(16px) !important;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6) !important;
            padding: 14px 16px !important;
        }}
        [data-testid="stPopoverBody"]::-webkit-scrollbar {{
            width: 6px;
        }}
        [data-testid="stPopoverBody"]::-webkit-scrollbar-track {{
            background: rgba(22, 27, 34, 0.6);
            border-radius: 4px;
        }}
        [data-testid="stPopoverBody"]::-webkit-scrollbar-thumb {{
            background: rgba(255, 153, 0, 0.4);
            border-radius: 4px;
        }}
        [data-testid="stPopoverBody"]::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 153, 0, 0.7);
        }}

        /* Executive Health Badges */
        .executive-badges-container {{
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
            align-items: center !important;
            margin-top: 6px !important;
            margin-bottom: 14px !important;
            line-height: normal !important;
        }}
        .executive-badge {{
            display: inline-flex;
            align-items: center;
            padding: 3px 9px;
            border-radius: 14px;
            font-size: 11.5px;
            font-weight: 600;
            margin-right: 0px;
            margin-bottom: 0px;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .badge-green {{ background: rgba(63, 185, 80, 0.12); color: #3fb950; border-color: rgba(63, 185, 80, 0.25); }}
        .badge-yellow {{ background: rgba(210, 153, 34, 0.12); color: #d29922; border-color: rgba(210, 153, 34, 0.25); }}
        .badge-red {{ background: rgba(248, 81, 73, 0.12); color: #f85149; border-color: rgba(248, 81, 73, 0.25); }}
        .badge-blue {{ background: rgba(56, 189, 248, 0.12); color: #38bdf8; border-color: rgba(56, 189, 248, 0.25); }}
        .badge-purple {{ background: rgba(167, 139, 250, 0.12); color: #a78bfa; border-color: rgba(167, 139, 250, 0.25); }}
        .badge-gray {{ background: rgba(255, 255, 255, 0.05); color: #94a3b8; border-color: rgba(255, 255, 255, 0.10); }}
        .badge-emerald {{ background: rgba(16, 185, 129, 0.14); color: #34d399; border-color: rgba(16, 185, 129, 0.30); }}

        /* Institutional Telemetry Ribbon Global Spacing */
        .institutional-telemetry-ribbon {{
            margin-top: 6px !important;
            margin-bottom: 14px !important;
            clear: both !important;
        }}


        /* Section Header */
        .section-header {{
            font-size: 20px; 
            font-weight: 700; 
            color: #ffffff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding-bottom: 10px; 
            margin: 32px 0 18px 0;
            position: relative;
            letter-spacing: -0.3px;
        }}
        .section-header::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 48px;
            height: 2px;
            background: {accent_color};
            box-shadow: 0 0 10px {accent_color};
        }}

        /* Glowing Status Pulse Dot */
        @keyframes pulse-green {{
            0% {{ box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.7); }}
            70% {{ box-shadow: 0 0 0 8px rgba(63, 185, 80, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(63, 185, 80, 0); }}
        }}
        .status-dot-pulse {{
            width: 8px;
            height: 8px;
            background-color: #3fb950;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse-green 2s infinite;
        }}

        /* ARGUS Glassmorphic Top Command Bar & Alignment */
        .argus-command-bar {{
            background: rgba(22, 27, 34, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 8px 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}

        /* Top Command Bar Containers - Zero Gap & Pixel-Perfect Vertical Centering */
        div[class*="st-key-argus_top_command_bar_container"],
        div[class*="st-key-argus_wealth_command_bar_container"],
        div[class*="st-key-argus_omni_command_bar_container"] {{
            margin-top: 0px !important;
            margin-bottom: 2px !important;
            padding: 0px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stHorizontalBlock"] {{
            align-items: center !important;
            gap: 8px !important;
            width: 100% !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stColumn"],
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stColumn"],
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stColumn"] {{
            display: flex !important;
            align-items: center !important;
            min-height: 32px !important;
            height: 32px !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stColumn"] > div,
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stColumn"] > div,
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stColumn"] > div {{
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            height: 32px !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stElementContainer"],
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stElementContainer"],
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stElementContainer"] {{
            width: 100% !important;
            margin: 0px !important;
            padding: 0px !important;
            display: flex !important;
            align-items: center !important;
            height: 32px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stMarkdownContainer"],
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stMarkdownContainer"],
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stMarkdownContainer"] {{
            width: 100% !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stMarkdownContainer"] > p,
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stMarkdownContainer"] > p,
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stMarkdownContainer"] > p {{
            margin: 0px !important;
            padding: 0px !important;
            line-height: 1 !important;
        }}

        .argus-command-pills-cluster {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-end !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            height: 32px !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            margin: 0px !important;
            padding: 0px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }}

        /* Command Bar Buttons & Popovers Matching Pill Density & Height */
        div[class*="st-key-argus_top_command_bar_container"] button,
        div[class*="st-key-argus_wealth_command_bar_container"] button,
        div[class*="st-key-argus_omni_command_bar_container"] button,
        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stPopover"],
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stPopover"],
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stPopover"],
        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stPopover"] button,
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stPopover"] button,
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stPopover"] button {{
            height: 32px !important;
            min-height: 32px !important;
            max-height: 32px !important;
            padding: 0px 8px !important;
            font-size: 11.5px !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            line-height: 30px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0px !important;
            white-space: nowrap !important;
            width: 100% !important;
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            color: #c9d1d9 !important;
            transition: all 0.18s ease !important;
        }}

        div[class*="st-key-argus_top_command_bar_container"] button:hover,
        div[class*="st-key-argus_wealth_command_bar_container"] button:hover,
        div[class*="st-key-argus_omni_command_bar_container"] button:hover,
        div[class*="st-key-argus_top_command_bar_container"] [data-testid="stPopover"] button:hover,
        div[class*="st-key-argus_wealth_command_bar_container"] [data-testid="stPopover"] button:hover,
        div[class*="st-key-argus_omni_command_bar_container"] [data-testid="stPopover"] button:hover {{
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 153, 0, 0.45) !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
        }}

        .argus-command-pill {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 32px !important;
            min-height: 32px !important;
            padding: 0px 8px !important;
            border-radius: 6px !important;
            font-size: 11.5px !important;
            font-weight: 500 !important;
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #c9d1d9 !important;
            white-space: nowrap !important;
            letter-spacing: 0.2px !important;
            line-height: 30px !important;
            box-sizing: border-box !important;
            transition: all 0.18s ease !important;
        }}
        .argus-command-pill:hover {{
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 153, 0, 0.4) !important;
            color: #ffffff !important;
        }}

        /* Streamlit Tabs Customization - Glassmorphism Dock */
        [data-baseweb="tab-list"] {{
            display: flex !important;
            gap: 8px !important;
            background: linear-gradient(180deg, rgba(22, 27, 34, 0.85) 0%, rgba(13, 17, 23, 0.95) 100%) !important;
            padding: 6px !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(16px) !important;
            margin-bottom: 20px !important;
        }}
        [data-baseweb="tab"] {{
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 12.5px !important;
            color: #8b949e !important;
            padding: 8px 13px !important;
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
            letter-spacing: 0.2px !important;
            white-space: nowrap !important;
        }}
        [data-baseweb="tab"]:hover {{
            color: #f0f6fc !important;
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
            transform: translateY(-1px) !important;
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            background: linear-gradient(135deg, rgba(255, 153, 0, 0.22) 0%, rgba(255, 179, 71, 0.12) 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border: 1px solid {accent_color} !important;
            box-shadow: 0 0 16px rgba(255, 153, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
            transform: translateY(0) !important;
        }}
        [data-baseweb="tab-highlight"] {{
            background-color: {accent_color} !important;
            height: 3px !important;
            border-radius: 2px !important;
        }}

        /* ARGUS Institutional Tab Deck (Bloomberg / Linear Terminal Grade) */
        .argus-tab-deck-container {{
            background: linear-gradient(180deg, rgba(22, 27, 34, 0.85) 0%, rgba(13, 17, 23, 0.95) 100%) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 12px !important;
            padding: 5px 6px !important;
            margin: 6px 0 20px 0 !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
            backdrop-filter: blur(20px) !important;
        }}

        .argus-tab-deck-container div[data-testid="column"] {{
            padding: 0 3px !important;
        }}

        /* Inactive Tab Deck Button */
        .argus-tab-deck-container button[kind="secondary"],
        .argus-tab-deck-container button[data-testid="baseButton-secondary"] {{
            background: rgba(22, 27, 34, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            color: #8b949e !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            letter-spacing: 0.1px !important;
            padding: 4px 8px !important;
            min-height: 42px !important;
            height: 42px !important;
            max-height: 42px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            text-align: center !important;
            transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: none !important;
            transform: none !important;
        }}

        .argus-tab-deck-container button[kind="secondary"]:hover,
        .argus-tab-deck-container button[data-testid="baseButton-secondary"]:hover {{
            background: rgba(255, 255, 255, 0.08) !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }}

        /* Active Tab Deck Button (Illuminated Dark Metal Capsule) */
        .argus-tab-deck-container button[kind="primary"],
        .argus-tab-deck-container button[data-testid="baseButton-primary"] {{
            background: linear-gradient(180deg, #24292f 0%, #161b22 100%) !important;
            border: 1px solid #ff9900 !important;
            border-bottom: 3px solid #ff9900 !important;
            border-radius: 8px !important;
            color: #ff9900 !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            letter-spacing: 0.2px !important;
            padding: 4px 8px !important;
            min-height: 42px !important;
            height: 42px !important;
            max-height: 42px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            text-align: center !important;
            box-shadow: 0 4px 16px rgba(255, 153, 0, 0.25), 0 0 10px rgba(255, 153, 0, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
            transform: none !important;
        }}

        .argus-tab-deck-container button[kind="primary"]:hover,
        .argus-tab-deck-container button[data-testid="baseButton-primary"]:hover {{
            background: linear-gradient(180deg, #2d333b 0%, #1c2128 100%) !important;
            box-shadow: 0 6px 20px rgba(255, 153, 0, 0.35), 0 0 14px rgba(255, 153, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
            color: #ffb74d !important;
        }}

        /* Institutional Radio Buttons Styling */
        div[data-testid="stRadio"] > div[role="radiogroup"] {{
            display: flex !important;
            flex-direction: column !important;
            align-items: stretch !important;
            gap: 6px !important;
            background: transparent !important;
            border: none !important;
            padding: 2px 0 !important;
            margin: 6px 0 16px 0 !important;
            width: 100% !important;
        }}

        /* Horizontal Radios */
        div[data-testid="stRadio"] > div[role="radiogroup"][style*="flex-direction: row"],
        div[data-testid="stRadio"] > div[role="radiogroup"][aria-orientation="horizontal"] {{
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            background: rgba(13, 17, 23, 0.85) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 4px !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
            background: rgba(22, 27, 34, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 8px !important;
            padding: 8px 14px !important;
            cursor: pointer !important;
            transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"][style*="flex-direction: row"] > label,
        div[data-testid="stRadio"] > div[role="radiogroup"][aria-orientation="horizontal"] > label {{
            background: transparent !important;
            border: 1px solid transparent !important;
            width: auto !important;
            padding: 6px 14px !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
            background: rgba(255, 255, 255, 0.06) !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
        }}



        /* 100% Elimination of Radio Circles, Inputs & Dots */
        div[data-testid="stRadio"] [role="radiogroup"] input[type="radio"],
        div[data-testid="stRadio"] [role="radiogroup"] input[type="radio"] ~ div,
        div[data-testid="stRadio"] [role="radiogroup"] label > div:not([data-testid="stMarkdownContainer"]):not(:has([data-testid="stMarkdownContainer"])),
        div[data-testid="stRadio"] [role="radiogroup"] label > div:first-child:not([data-testid="stMarkdownContainer"]),
        div[data-testid="stRadio"] [role="radiogroup"] label > span,
        div[data-testid="stRadio"] [role="radiogroup"] svg,
        div[data-testid="stRadio"] [role="radiogroup"] div[aria-hidden="true"],
        div[data-testid="stRadio"] [data-testid="stRadioOption"] > div:first-child {{
            display: none !important;
            width: 0 !important;
            height: 0 !important;
            min-width: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
            opacity: 0 !important;
            visibility: hidden !important;
            pointer-events: none !important;
            position: absolute !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label [data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] > div[role="radiogroup"] > label p {{
            color: #8b949e !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            letter-spacing: 0.2px !important;
            margin: 0 !important;
            padding: 0 !important;
            transition: color 0.18s ease !important;
            white-space: nowrap !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover [data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover p {{
            color: #ffffff !important;
        }}

        /* Active Segment Styling (Glowing Institutional Capsule) */
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {{
            background: linear-gradient(180deg, #21262d 0%, #161b22 100%) !important;
            border: 1px solid rgba(255, 153, 0, 0.7) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 12px rgba(255, 153, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) [data-testid="stMarkdownContainer"] p,
        div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) p {{
            color: #ff9900 !important;
            font-weight: 700 !important;
            text-shadow: 0 0 8px rgba(255, 153, 0, 0.3) !important;
        }}

        /* Streamlit Buttons Micro-Animations */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4), 0 0 12px {accent_color}33 !important;
        }}

        /* Hide Streamlit Default Raw Sidebar Nav (Replacing with Institutional Tree Rail) */
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        /* Institutional Sidebar Tree Navigation Styles */
        .sidebar-section-header {{
            font-size: 10px !important;
            font-weight: 800 !important;
            color: #8b949e !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            margin: 18px 0 8px 4px !important;
            padding: 4px 0 2px 0 !important;
            line-height: 14px !important;
            display: block !important;
            box-sizing: border-box !important;
        }}

        /* Clean Institutional Sidebar Navigation with Balanced 6px Gap */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"],
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 6px !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {{
            margin-bottom: 0px !important;
            margin-top: 0px !important;
        }}
        section[data-testid="stSidebar"] .stButton {{
            margin: 0px !important;
            padding: 0px !important;
        }}

        section[data-testid="stSidebar"] [data-testid="stExpander"] {{
            background: rgba(22, 27, 34, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 7px !important;
            margin: 2px 0 !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] details {{
            padding: 0 !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
            padding: 7px 12px !important;
            min-height: 36px !important;
            height: auto !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #c9d1d9 !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
            display: flex !important;
            align-items: center !important;
            white-space: nowrap !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {{
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            margin: 0 !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
            background: rgba(255, 255, 255, 0.06) !important;
            color: #ffffff !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
            color: #ff9900 !important;
            background: rgba(255, 153, 0, 0.09) !important;
            border-left: 3px solid #ff9900 !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
            padding: 6px 8px 6px 8px !important;
            background: rgba(13, 17, 23, 0.5) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
        }}
        section[data-testid="stSidebar"] label p {{
            font-size: 10.5px !important;
            font-weight: 700 !important;
            color: #8b949e !important;
            text-transform: uppercase !important;
            letter-spacing: 0.4px !important;
            margin-bottom: 4px !important;
            margin-top: 2px !important;
            white-space: nowrap !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stCheckbox"] label p,
        section[data-testid="stSidebar"] [data-testid="stToggle"] label p,
        section[data-testid="stSidebar"] label[data-baseweb="checkbox"] p {{
            font-size: 11px !important;
            font-weight: 600 !important;
            color: #c9d1d9 !important;
            text-transform: none !important;
            letter-spacing: 0.2px !important;
            white-space: normal !important;
            word-break: normal !important;
            overflow-wrap: break-word !important;
            line-height: 1.3 !important;
        }}
        section[data-testid="stSidebar"] input {{
            font-size: 12px !important;
            padding: 5px 8px !important;
            border-radius: 6px !important;
            background: rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #ffffff !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] {{
            font-size: 12px !important;
            border-radius: 8px !important;
            background: rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            min-height: 38px !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            min-height: 38px !important;
            align-items: center !important;
            border-radius: 8px !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
            font-size: 12px !important;
        }}

        /* Direct Top-Level Navigation Buttons (Matching Expanders) */
        section[data-testid="stSidebar"] > div > div > div > .stButton > button,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > .stButton > button,
        section[data-testid="stSidebar"] .stButton > button {{
            padding: 7px 12px !important;
            min-height: 36px !important;
            height: 36px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            margin: 2px 0 !important;
            border-radius: 7px !important;
            background: rgba(22, 27, 34, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #c9d1d9 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            transform: none !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}
        section[data-testid="stSidebar"] > div > div > div > .stButton > button:hover,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > .stButton > button:hover,
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255, 255, 255, 0.06) !important;
            border-color: rgba(255, 255, 255, 0.15) !important;
            color: #ffffff !important;
            box-shadow: none !important;
            transform: none !important;
        }}
        /* Direct Active Top-Level Button */
        section[data-testid="stSidebar"] > div > div > div > .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > .stButton > button[kind="primary"],
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background: rgba(255, 153, 0, 0.12) !important;
            border: 1px solid rgba(255, 153, 0, 0.35) !important;
            border-left: 3px solid #ff9900 !important;
            color: #ff9900 !important;
            font-weight: 700 !important;
        }}

        /* Sub-tab Buttons inside Expanders */
        section[data-testid="stSidebar"] [data-testid="stExpander"] button,
        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stBaseButton-secondary"],
        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stBaseButton-primary"] {{
            padding: 4px 10px !important;
            min-height: 26px !important;
            height: 26px !important;
            line-height: 20px !important;
            font-size: 11.5px !important;
            font-weight: 500 !important;
            margin: 1px 0 !important;
            border-radius: 5px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            color: #8b949e !important;
            text-align: left !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            transform: none !important;
            transition: all 0.15s ease !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            display: flex !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] button:hover,
        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stBaseButton-secondary"]:hover {{
            background: rgba(255, 255, 255, 0.05) !important;
            color: #ffffff !important;
            border-color: rgba(255, 255, 255, 0.08) !important;
            box-shadow: none !important;
            transform: none !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] button[kind="primary"],
        section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stBaseButton-primary"] {{
            background: rgba(255, 153, 0, 0.14) !important;
            border: 1px solid rgba(255, 153, 0, 0.3) !important;
            border-left: 3px solid #ff9900 !important;
            color: #ff9900 !important;
            font-weight: 700 !important;
        }}

        /* Control Room Source Tiles & Presets */
        .argus-source-tile {{
            background: rgba(22, 27, 34, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px 16px;
            transition: all 0.2s ease;
            backdrop-filter: blur(12px);
        }}
        .argus-source-tile:hover {{
            border-color: rgba(255, 153, 0, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
        }}
        .argus-preset-card {{
            background: linear-gradient(180deg, rgba(22, 27, 34, 0.85) 0%, rgba(13, 17, 23, 0.95) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
        }}
        .argus-preset-card:hover {{
            border-color: rgba(88, 166, 255, 0.4);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        }}
        .argus-asset-pill {{
            display: inline-block;
            font-size: 10.5px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #c9d1d9;
            padding: 2px 8px;
            border-radius: 10px;
            margin: 2px 3px 2px 0;
        }}

        /* Wealth KPI Metric Cards */
        .wealth-kpi-card {{
            background: rgba(22, 27, 34, 0.75) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-top: 3px solid #10b981 !important;
            border-radius: 12px !important;
            padding: 14px 16px !important;
            transition: all 0.25s ease !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
            min-height: 100px !important;
        }}
        .wealth-kpi-card:hover {{
            border-color: rgba(16, 185, 129, 0.6) !important;
            box-shadow: 0 6px 22px rgba(16, 185, 129, 0.2) !important;
            transform: translateY(-2px) !important;
        }}
        .wealth-kpi-header {{
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            margin-bottom: 6px !important;
        }}
        .wealth-kpi-title {{
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.8px !important;
            color: #94a3b8 !important;
        }}
        .wealth-kpi-val {{
            font-family: 'JetBrains Mono', 'Roboto Mono', monospace !important;
            font-size: 22px !important;
            font-weight: 800 !important;
            color: #ffffff !important;
            letter-spacing: -0.5px !important;
            margin-bottom: 6px !important;
        }}
        .wealth-kpi-pill {{
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            color: #34d399 !important;
            background: rgba(16, 185, 129, 0.12) !important;
            padding: 2px 8px !important;
            border-radius: 6px !important;
            border: 1px solid rgba(16, 185, 129, 0.25) !important;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header, [data-testid="stHeader"] {{ visibility: visible !important; display: block !important; }}
        [data-testid="collapsedControl"] {{ visibility: visible !important; display: block !important; z-index: 999999 !important; }}

        /* Zero-height wrapper for background JS runners */
        iframe[data-testid="stCustomComponentV1"],
        div[data-testid="stCustomComponentV1"],
        div:has(> iframe[height="0"]) {{
            display: none !important;
            height: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
        }}
    </style>
    """,
        unsafe_allow_html=True,
    )
    if hasattr(st, "session_state"):
        st.session_state.pop("_argus_css_injected_theme", None)


apply_custom_css = inject_custom_css


