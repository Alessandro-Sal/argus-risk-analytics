from typing import Any, Dict, List, Optional, Tuple, Union
import textwrap
from datetime import datetime, date
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import plotly.io as pio
import plotly.express as px




def inject_custom_css():
    theme = st.session_state.get("ui_theme", "Midnight Obsidian")
    
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
    else: # Midnight Obsidian
        bg_gradient = "radial-gradient(circle at 15% 50%, #0d1117, #161b22, #0d1117)"
        accent_color = "#ff9900"
        accent_gradient = "linear-gradient(180deg, #ff9900, #ff3366)"
        card_bg = "rgba(22, 27, 34, 0.6)"

    st.markdown(f"""
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
        }}

        /* Always keep Collapsed Control (Open Sidebar Button) Visible & Clickable */
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapsedControl"],
        div[data-testid="collapsedControl"],
        [data-testid="stHeader"] [data-testid="collapsedControl"] {{
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            z-index: 999999 !important;
        }}
        [data-testid="collapsedControl"] button,
        button[data-testid="stSidebarCollapsedControl"] {{
            display: inline-flex !important;
            visibility: visible !important;
            color: #ff9900 !important;
            background: rgba(22, 27, 34, 0.95) !important;
            border: 1px solid rgba(255, 153, 0, 0.4) !important;
            border-radius: 8px !important;
            padding: 4px 8px !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4) !important;
        }}
        [data-testid="collapsedControl"] button:hover {{
            border-color: #ff9900 !important;
            background: rgba(33, 38, 45, 1) !important;
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

        /* Compact Sidebar Header containing the Close (<) Button */
        div[data-testid="stSidebarHeader"],
        [data-testid="stSidebarHeader"] {{
            min-height: 32px !important;
            padding: 4px 8px 0px 8px !important;
            margin: 0px !important;
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
            background: transparent !important;
            visibility: visible !important;
        }}

        /* Sidebar Close Button */
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"],
        div[data-testid="stSidebarHeader"] button {{
            display: inline-flex !important;
            visibility: visible !important;
            color: #8b949e !important;
            background: transparent !important;
            border: none !important;
            padding: 3px 6px !important;
            margin: 0px !important;
            cursor: pointer !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
        }}
        [data-testid="stSidebarCollapseButton"]:hover,
        button[data-testid="stSidebarCollapseButton"]:hover,
        div[data-testid="stSidebarHeader"] button:hover {{
            color: #ffffff !important;
            background: rgba(255, 255, 255, 0.12) !important;
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

        /* Main Block Container - Generous Bottom Padding for Safe Scrolling */
        .block-container,
        [data-testid="block-container"],
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer {{
            padding-top: 1.5rem !important;
            padding-bottom: 6.5rem !important;
            padding-left: 1.75rem !important;
            padding-right: 1.75rem !important;
            max-width: 100% !important;
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
            max-height: 68vh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            scrollbar-width: thin !important;
            scrollbar-color: rgba(255, 153, 0, 0.4) rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 153, 0, 0.3) !important;
            border-radius: 12px !important;
            background: rgba(13, 17, 23, 0.98) !important;
            backdrop-filter: blur(16px) !important;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6) !important;
            padding: 16px 20px !important;
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
        .executive-badge {{
            display: inline-flex;
            align-items: center;
            padding: 3px 9px;
            border-radius: 14px;
            font-size: 11.5px;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 2px;
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

        /* ARGUS Glassmorphic Top Command Bar */
        .argus-command-bar {{
            background: rgba(22, 27, 34, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 10px 18px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        .argus-command-pill {{
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 500;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #c9d1d9;
            white-space: nowrap;
            letter-spacing: 0.2px;
            transition: all 0.18s ease;
        }}
        .argus-command-pill:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 153, 0, 0.4);
            color: #ffffff;
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
            font-size: 13.5px !important;
            color: #8b949e !important;
            padding: 9px 20px !important;
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
            letter-spacing: 0.2px !important;
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
            margin-bottom: 2px !important;
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
            border-radius: 6px !important;
            background: rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            min-height: 32px !important;
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
    """, unsafe_allow_html=True)

apply_custom_css = inject_custom_css


def scroll_to_top(behavior: str = "instant"):
    """
    Esegue lo scroll automatico verso la cima della pagina e dei container scrollabili Streamlit.
    Attivato automaticamente al cambio pagina e al cambio di tab interne (sia st.tabs che segmented tabs).
    """
    import streamlit.components.v1 as components
    js_code = f"""
    <script>
    (function() {{
        function performScroll() {{
            try {{
                const p = window.parent;
                const d = p ? p.document : document;
                if (!p || !d) return;

                const targets = [
                    p,
                    d.documentElement,
                    d.body,
                    d.querySelector('section.main'),
                    d.querySelector('[data-testid="stAppViewContainer"]'),
                    d.querySelector('[data-testid="stMain"]'),
                    d.querySelector('.main'),
                    d.querySelector('[data-testid="stMainBlockContainer"]')
                ];
                targets.forEach(function(el) {{
                    if (el) {{
                        if (typeof el.scrollTo === 'function') {{
                            el.scrollTo({{ top: 0, left: 0, behavior: '{behavior}' }});
                        }}
                        el.scrollTop = 0;
                    }}
                }});
            }} catch (e) {{}}
        }}

        performScroll();
        setTimeout(performScroll, 30);
        setTimeout(performScroll, 100);
        setTimeout(performScroll, 250);

        // Installa listener globale permanente sui click di qualsiasi tab o link di navigazione
        try {{
            if (window.parent && !window.parent._argus_scroll_listener_installed) {{
                window.parent._argus_scroll_listener_installed = true;
                const doc = window.parent.document;
                doc.addEventListener('click', function(e) {{
                    const t = e.target;
                    if (!t) return;
                    const isTab = t.closest('button[data-testid="stTab"]') || 
                                  t.closest('[data-testid="stTab"]') ||
                                  t.closest('.argus-tab-deck-container button') ||
                                  t.closest('section[data-testid="stSidebar"] button') ||
                                  t.closest('section[data-testid="stSidebar"] [data-testid="stExpander"] button');
                    if (isTab) {{
                        performScroll();
                        setTimeout(performScroll, 40);
                        setTimeout(performScroll, 120);
                        setTimeout(performScroll, 300);
                    }}
                }}, true);
            }}
        }} catch(err) {{}}
    }})();
    </script>
    """
    components.html(js_code, height=0, width=0)


def render_header(title: str, subtitle: str = None):
    """Renderizza il titolo ed il sottotitolo principale della pagina con la command bar di ARGUS."""
    render_command_bar()
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def get_display_portfolio_name():
    """
    Restituisce una tupla (nome_da_visualizzare: str, is_active: bool).
    Se non ci sono risultati/pipeline_done, restituisce ('Nessun Portafoglio (In attesa)', False).
    Se i dati sono caricati, restituisce il nome effettivo del portafoglio (es. 'Master Wealth', True).
    """
    has_data = bool(st.session_state.get("pipeline_done") or st.session_state.get("results"))
    if not has_data:
        return "Nessun Portafoglio (In attesa)", False
    name = st.session_state.get("portfolio_name")
    if not name or name == "Master Wealth Google Sheets":
        name = "Master Wealth"
    return name, True


def render_command_bar():
    """Renderizza la barra di stato e comando ARGUS v6.3.0 in cima alla pagina con telemetria, spotlight e popout 2° monitor."""
    try:
        from core.workspace_manager import sync_url_state
        sync_url_state()
    except Exception:
        pass

    port_label, has_port = get_display_portfolio_name()
    port_color = "#58a6ff" if has_port else "#8b949e"
    port_icon = "💼" if has_port else "⏳"
    base_curr = st.session_state.get("base_currency", "EUR")
    bench = st.session_state.get("benchmark", "SPY")
    offline = st.session_state.get("offline_mode", False)
    mode_str = "OFFLINE" if offline else "LIVE DB"
    mode_color = "#e3b341" if offline else "#3fb950"
    mode_bg = "rgba(227, 179, 65, 0.10)" if offline else "rgba(63, 185, 80, 0.10)"
    mode_border = "rgba(227, 179, 65, 0.28)" if offline else "rgba(63, 185, 80, 0.28)"

    col_bar1, col_bar2 = st.columns([1.3, 1.1])
    with col_bar1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap: 8px; padding: 2px 0; height: 38px;">
            <span class="status-dot-pulse" style="margin-right: 2px;"></span>
            <span style="color:#ffffff; font-weight:800; font-size:13px; letter-spacing:0.4px; font-family:'Outfit', sans-serif;">
                ARGUS ENGINE
            </span>
            <span style="color:rgba(255,255,255,0.2); margin: 0 2px;">|</span>
            <span style="color:{port_color}; font-size:12.5px; font-weight:600; display:inline-flex; align-items:center; gap:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                <span>{port_icon}</span> {port_label}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_bar2:
        c_pills, c_btn = st.columns([1.7, 1.0])
        with c_pills:
            st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:flex-end; gap: 6px; height: 38px;">
                <div class="argus-command-pill">💱 <b>{base_curr}</b></div>
                <div class="argus-command-pill">📊 <b>{bench}</b></div>
                <div class="argus-command-pill" style="background:{mode_bg}; border-color:{mode_border}; color:{mode_color};">
                    <span style="width:6px; height:6px; border-radius:50%; background:{mode_color}; display:inline-block; margin-right:5px;"></span>{mode_str}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_btn:
            if st.button("🔍 Spotlight", key="btn_open_spotlight", use_container_width=True, help="Cerca pagine, schede, ticker o lancia comandi rapidi (Ctrl+K)"):
                render_spotlight_palette()


def parse_terminal_command(raw_query: str) -> Optional[Dict[str, Any]]:
    """
    Parser di sintassi per la Bloomberg-style Command Line:
      Sintassi supportate:
        - <TICKER> <MNEMONIC> (es. 'AAPL DES', 'MSFT FA', 'NVDA VOLS', 'BTC HP')
        - <MNEMONIC> <TICKER> (es. 'DES AAPL', 'FA NVDA')
        - <MNEMONIC>          (es. 'YCRV', 'PORT RISK', 'EQS', 'ATTR', 'TAX', 'REBAL', 'BARRA', 'HRP')
    """
    if not raw_query:
        return None
        
    tokens = [t.strip().upper() for t in raw_query.replace("<GO>", "").replace("<go>", "").split() if t.strip()]
    if not tokens:
        return None

    # Mappatura dei codici mnemonici istituzionali Bloomberg-style
    MNEMONIC_REGISTRY = {
        # Azioni e Sicurezza Singola
        "DES": {
            "title": "Security Description & Fondamentali",
            "page": "pages/6_🏛️_Valutazione_Aziendale.py",
            "tab_key": "val_segmented_tab",
            "target": "📊 Bilanci & Solvibilità (Altman & DuPont)",
            "context_type": "ticker"
        },
        "FA": {
            "title": "Financial Analysis & SEC 10-K Filings",
            "page": "pages/6_🏛️_Valutazione_Aziendale.py",
            "tab_key": "val_segmented_tab",
            "target": "📊 Bilanci & Solvibilità (Altman & DuPont)",
            "context_type": "ticker"
        },
        "DCF": {
            "title": "Valutazione Intrinseca DCF Monte Carlo",
            "page": "pages/6_🏛️_Valutazione_Aziendale.py",
            "tab_key": "val_segmented_tab",
            "target": "🧮 Valutazione Intrinseca DCF Monte Carlo",
            "context_type": "ticker"
        },
        "ANR": {
            "title": "Analyst Recommendations & Consensus",
            "page": "pages/6_🏛️_Valutazione_Aziendale.py",
            "tab_key": "val_segmented_tab",
            "target": "🏛️ Fair Value & Consensus Analisti",
            "context_type": "ticker"
        },
        "HP": {
            "title": "Historical Prices & Candlestick Cockpit",
            "page": "pages/9_📈_Analisi_Tecnica.py",
            "tab_key": "tech_active_subtab",
            "target": "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)",
            "context_type": "ticker_tech"
        },
        "TECH": {
            "title": "Analisi Tecnica & Volume Profile POC",
            "page": "pages/9_📈_Analisi_Tecnica.py",
            "tab_key": "tech_active_subtab",
            "target": "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)",
            "context_type": "ticker_tech"
        },
        "VOLS": {
            "title": "Superficie Volatilità 3D & SABR Skew",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🛡️ Hedging Tattico & Tail Risk",
            "context_type": "ticker"
        },
        # Portafoglio e Rischio
        "PORT": {
            "title": "Portfolio Risk & Decomposizione VaR",
            "page": "pages/3_🔴_Analisi_Rischio.py",
            "tab_key": "risk_active_tab",
            "target": "📉 VaR, CVaR & Backtesting Kupiec",
            "context_type": "portfolio"
        },
        "RISK": {
            "title": "VaR, CVaR & Kupiec POF Backtest",
            "page": "pages/3_🔴_Analisi_Rischio.py",
            "tab_key": "risk_active_tab",
            "target": "📉 VaR, CVaR & Backtesting Kupiec",
            "context_type": "portfolio"
        },
        "ATTR": {
            "title": "Performance Attribution (Brinson & Carino)",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🎯 Attribuzione Brinson-Fachler",
            "context_type": "portfolio"
        },
        "TAX": {
            "title": "Tax-Loss Harvesting & Step-Up TUIR",
            "page": "pages/5_📋_Posizioni_e_Dettagli.py",
            "tab_key": "positions_active_tab",
            "target": "💰 Ottimizzazione Fiscale (TUIR Art. 67)",
            "context_type": "portfolio"
        },
        "REBAL": {
            "title": "Rebalancing Sandbox & Markowitz Frontier",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "📊 Frontiera Markowitz & Rebalancing",
            "context_type": "portfolio"
        },
        "HRP": {
            "title": "Hierarchical Risk Parity (López de Prado)",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "📊 Frontiera Markowitz & Rebalancing",
            "context_type": "portfolio"
        },
        "BARRA": {
            "title": "Modello Multi-Fattoriale MSCI Barra & Black-Litterman",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🎯 Attribuzione & Fattori",
            "context_type": "portfolio"
        },
        "COPULA": {
            "title": "Asymmetric Tail Copula & Kelly Sizing",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🧬 Tail Copula & Kelly",
            "context_type": "portfolio"
        },
        "MC": {
            "title": "Monte Carlo 10k Paths & Merton Jump",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🎲 Monte Carlo & Merton",
            "context_type": "portfolio"
        },
        "STRESS": {
            "title": "Stress Testing & Scenari di Crisi",
            "page": "pages/7_🌪️_Stress_Testing.py",
            "tab_key": "stress_active_tab",
            "target": "⚡ Matrice Comparativa MSCI Barra",
            "context_type": "portfolio"
        },
        "FIFO": {
            "title": "Registro FIFO Lotti & Graveyard Analytics",
            "page": "pages/5_📋_Posizioni_e_Dettagli.py",
            "tab_key": "positions_active_tab",
            "target": "🪦 Posizioni Chiuse & Graveyard",
            "context_type": "portfolio"
        },
        "DIV": {
            "title": "Calendario & Flusso Dividendi",
            "page": "pages/5_📋_Posizioni_e_Dettagli.py",
            "tab_key": "positions_active_tab",
            "target": "📅 Proiezione Dividendi",
            "context_type": "portfolio"
        },
        # Macro, Tassi e Mercato
        "YCRV": {
            "title": "Nelson-Siegel-Svensson Yield Curves",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "📊 Markowitz & Rebalancing",
            "context_type": "rates"
        },
        "YAS": {
            "title": "Yield & Spread Analysis (YTM, Duration, Convexity, Z-Spread)",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🏛️ Fixed Income & Z-Spread",
            "context_type": "fixed_income"
        },
        "FI": {
            "title": "Fixed Income & Sovereign Debt Monitor",
            "page": "pages/4_🔬_Modelli_Quantitativi.py",
            "tab_key": "quant_active_tab",
            "target": "🏛️ Fixed Income & Z-Spread",
            "context_type": "fixed_income"
        },
        "CDS": {
            "title": "Credit Default Swap & Default Probability Matrix",
            "page": "pages/3_🔴_Analisi_Rischio.py",
            "tab_key": "risk_active_tab",
            "target": "📉 VaR, CVaR & Backtesting Kupiec",
            "context_type": "credit"
        },
        "STREAM": {
            "title": "Real-Time In-Memory Market Feed & Order Flow",
            "page": "pages/9_📈_Analisi_Tecnica.py",
            "tab_key": "tech_active_subtab",
            "target": "⚡ Real-Time Streaming",
            "context_type": "streaming"
        },
        "EQS": {
            "title": "Equity & Multi-Asset Screener Universale",
            "page": "pages/10_🔍_Screener_Opportunita.py",
            "tab_key": "screener_segmented_subtab",
            "target": "🔍 Screener Multi-Fattoriale & Archetipi",
            "context_type": "screener"
        },
        "DASH": {
            "title": "Executive Dashboard & Copilot",
            "page": "pages/1_📈_Dashboard_Generale.py",
            "tab_key": None,
            "target": None,
            "context_type": "dashboard"
        },
        "CR": {
            "title": "Control Room & Data Ingestion",
            "page": "0_Control_Room.py",
            "tab_key": None,
            "target": None,
            "context_type": "system"
        },
        "BQUANT": {
            "title": "BQuant Python Interactive Console (Bloomberg Style)",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "🐍 ARGUS BQuant Python Sandbox",
            "context_type": "bquant"
        },
        "PY": {
            "title": "BQuant Python Interactive Console (Bloomberg Style)",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "🐍 ARGUS BQuant Python Sandbox",
            "context_type": "bquant"
        },
        "LAUNCHPAD": {
            "title": "Launchpad & Role Workspace Customizer",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "🎛️ Launchpad & Workspace Customizer",
            "context_type": "workspace"
        },
        "WS": {
            "title": "Launchpad & Role Workspace Customizer",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "🎛️ Launchpad & Workspace Customizer",
            "context_type": "workspace"
        },
        "XL": {
            "title": "Excel Live Connector & Bloomberg RTD Builder",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "📊 Excel Live Connector & RTD",
            "context_type": "excel"
        },
        "EXCEL": {
            "title": "Excel Live Connector & Bloomberg RTD Builder",
            "page": "pages/11_💻_BQuant_e_Launchpad.py",
            "tab_key": "bquant_active_tab",
            "target": "📊 Excel Live Connector & RTD",
            "context_type": "excel"
        },
        "LIVE": {
            "title": "ARGUS Live Terminal & Interactive CLI Desk",
            "page": "pages/2_🖥️_Live_Terminal.py",
            "tab_key": None,
            "target": None,
            "context_type": "terminal"
        },
        "TERM": {
            "title": "ARGUS Live Terminal & Interactive CLI Desk",
            "page": "pages/2_🖥️_Live_Terminal.py",
            "tab_key": None,
            "target": None,
            "context_type": "terminal"
        },
        "CLI": {
            "title": "ARGUS Live Terminal & Interactive CLI Desk",
            "page": "pages/2_🖥️_Live_Terminal.py",
            "tab_key": None,
            "target": None,
            "context_type": "terminal"
        },
        "TERMINAL": {
            "title": "ARGUS Live Terminal & Interactive CLI Desk",
            "page": "pages/2_🖥️_Live_Terminal.py",
            "tab_key": None,
            "target": None,
            "context_type": "terminal"
        },
        # Wealth Management Mnemonics
        "WEALTH": {
            "title": "Stato Patrimoniale & Net Worth Consolidato",
            "page": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "NETWORTH": {
            "title": "Stato Patrimoniale & Net Worth Consolidato",
            "page": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "WTIME": {
            "title": "Wealth Temporal Desk & Dinamica Storica Net Worth",
            "page": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "CASHFLOW": {
            "title": "Cash Flow, Spese & Budgeting 50/30/20",
            "page": "pages/14_💳_Cash_Flow_e_Spese.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "BUDGET": {
            "title": "Cash Flow, Spese & Budgeting 50/30/20",
            "page": "pages/14_💳_Cash_Flow_e_Spese.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "CAVEAU": {
            "title": "Caveau Asset Fisici, Orologi & Illiquidi",
            "page": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "WATCHES": {
            "title": "Caveau Orologi di Lusso & Perizie",
            "page": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "PDEBT": {
            "title": "Private Debt & Direct Lending Waterfall",
            "page": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "PENSION": {
            "title": "Previdenza Integrativa, Fondi Pensione & Goal Planning",
            "page": "pages/16_🛡️_Previdenza_e_Pension_Planning.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "FIRE": {
            "title": "Indipendenza Finanziaria, FIRE & SWR Monte Carlo",
            "page": "pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "RW": {
            "title": "Fiscalità, Monitoraggio Estero & Quadro RW/RT",
            "page": "pages/18_📑_Fiscalita_e_Quadro_RW.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "GLOBALTAX": {
            "title": "Cross-Border Tax & Global Wealth Structuring",
            "page": "pages/18_📑_Fiscalita_e_Quadro_RW.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "REALESTATE": {
            "title": "Immobili, Mutui Ammortamento & Buy vs Rent",
            "page": "pages/19_🏡_Immobili_e_Mutui.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "MORTGAGE": {
            "title": "Simulatore Mutuo Ammortamento alla Francese",
            "page": "pages/19_🏡_Immobili_e_Mutui.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "ESTATE": {
            "title": "Pianificazione Successoria & Patti di Famiglia",
            "page": "pages/20_⚖️_Pianificazione_Successoria.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "WCOPILOT": {
            "title": "AI Copilot & Advisor Patrimoniale Intelligente",
            "page": "pages/21_🤖_AI_Copilot_e_Advisor.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "VOICE": {
            "title": "AI Voice Advisor & Podcast Briefing a 2 Voci",
            "page": "pages/21_🤖_AI_Copilot_e_Advisor.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "WCR": {
            "title": "Wealth Control Room & Data Ingestion",
            "page": "pages/12_🎛️_Wealth_Control_Room.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        },
        "REPORTS": {
            "title": "Hub di Reportistica & Esportazioni Istituzionali",
            "page": "pages/12_🎛️_Wealth_Control_Room.py",
            "tab_key": None,
            "target": None,
            "context_type": "wealth"
        }
    }

    # Caso 1: Singolo token mnemonico (es. "YCRV", "EQS", "TAX", "PORT", "BQUANT", "XL")
    if len(tokens) == 1 and tokens[0] in MNEMONIC_REGISTRY:
        cmd_info = dict(MNEMONIC_REGISTRY[tokens[0]])
        cmd_info["mnemonic"] = tokens[0]
        cmd_info["ticker"] = None
        cmd_info["raw_command"] = tokens[0]
        return cmd_info

    # Caso 2: Due token "<TICKER> <MNEMONIC>" (es. "AAPL DES", "NVDA HP", "PORT RISK")
    if len(tokens) >= 2:
        # Check se il secondo token è un mnemonico
        if tokens[1] in MNEMONIC_REGISTRY:
            cmd_info = dict(MNEMONIC_REGISTRY[tokens[1]])
            cmd_info["mnemonic"] = tokens[1]
            cmd_info["ticker"] = tokens[0]
            cmd_info["raw_command"] = f"{tokens[0]} <{tokens[1]}>"
            return cmd_info
        # Check se il primo token è un mnemonico
        if tokens[0] in MNEMONIC_REGISTRY:
            cmd_info = dict(MNEMONIC_REGISTRY[tokens[0]])
            cmd_info["mnemonic"] = tokens[0]
            cmd_info["ticker"] = tokens[1]
            cmd_info["raw_command"] = f"{tokens[1]} <{tokens[0]}>"
            return cmd_info

    # Caso 3: Solo un ticker valido (es. "AAPL", "MSFT", "BTC-USD") -> Default DES
    if len(tokens) == 1 and len(tokens[0]) <= 8 and (tokens[0].isalnum() or "-" in tokens[0] or "." in tokens[0]):
        cmd_info = dict(MNEMONIC_REGISTRY["DES"])
        cmd_info["mnemonic"] = "DES"
        cmd_info["ticker"] = tokens[0]
        cmd_info["raw_command"] = f"{tokens[0]} <DES>"
        return cmd_info

    return None


@st.dialog("⚡ ARGUS RISK & QUANT COMMAND DESK", width="large")
def render_spotlight_palette():
    """Renderizza la Bloomberg-Style Command Line Gateway come vero modale @st.dialog con parser mnemonico e search unificata."""
    from core.sidebar import switch_to_page
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(20, 24, 30, 0.98) 0%, rgba(10, 13, 18, 1.0) 100%); border: 1.5px solid #ff9900; border-radius: 10px; padding: 10px 16px; margin: 0 0 14px 0; box-shadow: 0 12px 35px rgba(0,0,0,0.8), 0 0 20px rgba(255,153,0,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="font-size:12.5px; font-weight:800; color:#ff9900; letter-spacing:0.8px; display:inline-flex; align-items:center; gap:8px;">
                <span>⚡</span> ARGUS TERMINAL COMMAND GATEWAY
                <span style="font-size:9.5px; padding:1px 6px; background:#ff9900; color:#000000; border-radius:3px; font-weight:900; letter-spacing:0.5px;">BBG PARITY</span>
            </div>
            <div style="font-size:11px; color:#8b949e; font-family:monospace;">
                Sintassi: <span style="color:#e6edf3;">&lt;TICKER&gt; &lt;CMD&gt;</span> • es. <code style="color:#ff9900; background:rgba(255,153,0,0.1); padding:1px 4px; border-radius:3px;">AAPL DES</code>, <code style="color:#ff9900; background:rgba(255,153,0,0.1); padding:1px 4px; border-radius:3px;">PORT RISK</code>, <code style="color:#ff9900; background:rgba(255,153,0,0.1); padding:1px 4px; border-radius:3px;">YCRV</code>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_q, col_exec = st.columns([4.8, 1.2])
    with col_q:
        query = st.text_input(
            "Terminal Command", 
            placeholder="⌨️ Digita comando: es. AAPL DES, MSFT FA, NVDA VOLS, PORT RISK, YCRV, ATTR, TAX, EQS...", 
            key="spotlight_search_box", 
            label_visibility="collapsed"
        ).strip()
    
    parsed_cmd = parse_terminal_command(query)

    with col_exec:
        exec_label = f"▶ <GO> ({parsed_cmd['mnemonic']})" if parsed_cmd else "▶ <GO>"
        if st.button(exec_label, key="btn_exec_command_go", use_container_width=True, type="primary" if parsed_cmd else "secondary"):
            if parsed_cmd:
                if parsed_cmd.get("ticker"):
                    tk = parsed_cmd["ticker"]
                    if parsed_cmd.get("context_type") == "ticker_tech":
                        st.session_state["tech_ticker_input"] = tk
                    else:
                        st.session_state["selected_val_company"] = tk
                if parsed_cmd.get("tab_key") and parsed_cmd.get("target"):
                    st.session_state[parsed_cmd["tab_key"]] = parsed_cmd["target"]
                    st.session_state[f"target_subtab_{parsed_cmd['tab_key']}"] = parsed_cmd["target"]
                    st.session_state["global_target_subtab"] = parsed_cmd["target"]
                switch_to_page(parsed_cmd["page"])
            else:
                st.warning("Comando non riconosciuto. Digita es. `AAPL DES` o `YCRV`.")

    # Visual Feedback del comando riconosciuto
    if parsed_cmd:
        st.markdown(f"""
        <div style="background: rgba(0, 230, 118, 0.08); border-left: 3px solid #00E676; padding: 6px 12px; margin-bottom: 12px; font-size: 12px; color: #e6edf3; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-weight:700; color:#00E676;">COMANDO RICONOSCIUTO:</span> 
                <code style="color:#ff9900; background:#161b22; padding:2px 6px; border-radius:3px;">{parsed_cmd.get('raw_command', query)}</code> ➔ 
                <strong>{parsed_cmd['title']}</strong> ({parsed_cmd['page']})
            </div>
            <div style="font-size:11px; color:#8b949e;">Premi <strong>&lt;GO&gt;</strong> per eseguire</div>
        </div>
        """, unsafe_allow_html=True)

    results_data = st.session_state.get("results", {})
    df_pos = results_data.get("positions", None) if isinstance(results_data, dict) else None
    portfolio_tickers = []
    if df_pos is not None and hasattr(df_pos, "columns") and "ticker" in df_pos.columns:
        portfolio_tickers = [str(t).upper() for t in df_pos["ticker"].dropna().unique() if not str(t).endswith("=X")]

    col_res1, col_res2, col_res3 = st.columns([1.6, 1.4, 1.0])

    # ── COLONNA 1: SCHEDE & MODULI ANALITICI ────────────────────────
    with col_res1:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">📑 SCHEDE & MODULI ANALITICI</div>', unsafe_allow_html=True)
        
        search_index = [
            # Control Room
            {"title": "🎛️ Control Room & Ingestione CSV", "page": "0_Control_Room.py", "tab_key": None, "target": None, "keywords": "control room upload csv degiro database ingestione parametri mysql offline cr"},
            # Dashboard
            {"title": "📈 Dashboard Generale & Copilot", "page": "pages/1_📈_Dashboard_Generale.py", "tab_key": None, "target": None, "keywords": "dashboard cagr sharpe rendimento cumulato benchmark max drawdown kpi dash"},
            # Live Terminal
            {"title": "🖥️ Live Terminal & Real-Time Market Desk", "page": "pages/2_🖥️_Live_Terminal.py", "tab_key": None, "target": None, "keywords": "terminal live quote market tape bloomberg cli desk tape live order book"},
            # Rischio
            {"title": "🔴 Rischio ➔ VaR, CVaR & Marginal VaR", "page": "pages/3_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📉 VaR, CVaR & Backtesting Kupiec", "keywords": "var cvar cornish fisher marginal component lvar rischio perdita risk port"},
            {"title": "🔴 Rischio ➔ Backtesting VaR & Test Kupiec", "page": "pages/3_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📉 VaR, CVaR & Backtesting Kupiec", "keywords": "kupiec basel backtesting violazioni var test p-value"},
            {"title": "🔴 Rischio ➔ Modello Fama-French & Carhart", "page": "pages/3_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📊 Profilo del Rischio & Fama-French", "keywords": "fama french carhart smb hml mom wml fattori regressione alpha beta"},
            {"title": "🔴 Rischio ➔ Limiti di Rischio & Conformità UCITS", "page": "pages/3_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📊 Profilo del Rischio & Fama-French", "keywords": "limiti concentrazione ucits mifid conformità breach stop loss"},
            {"title": "🔴 Rischio ➔ Rilevamento Anomalie ML (Isolation Forest)", "page": "pages/3_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)", "keywords": "isolation forest machine learning anomalie outlier cluster ml"},
            # Quant
            {"title": "🔬 Quant ➔ Frontiera Markowitz & Rebalancing", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "📊 Frontiera Markowitz & Rebalancing", "keywords": "markowitz frontiera efficiente ledoit wolf sandbox ribilanciamento pesi sharpe rebal"},
            {"title": "🔬 Quant ➔ Hierarchical Risk Parity (HRP)", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "📊 Frontiera Markowitz & Rebalancing", "keywords": "hrp hierarchical risk parity lopez de prado clustering dendrogramma"},
            {"title": "🔬 Quant ➔ Tail Copula & Kelly Sizing", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🧬 Tail Copula & Kelly Sizing", "keywords": "tail copula clayton gumbel kelly criterion sizing half kelly crash contagion copula"},
            {"title": "🔬 Quant ➔ Monte Carlo 10k Paths & Merton", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🎲 Simulazioni Stocastiche (Monte Carlo & Merton)", "keywords": "monte carlo merton jump diffusion student-t cholesky simulazione stocastica mc"},
            {"title": "🔬 Quant ➔ Opzioni Black-Scholes & SABR Skew", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🛡️ Hedging Tattico & Tail Risk", "keywords": "opzioni black scholes call put greeks delta gamma theta vega hedge vols"},
            {"title": "🔬 Quant ➔ Performance Attribution (Brinson & Carino)", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🎯 Attribuzione Brinson-Fachler", "keywords": "brinson fachler carino menchero allocazione selezione interazione attribution attr"},
            {"title": "🔬 Quant ➔ Modelli Fattoriali (Carhart & Barra 5F)", "page": "pages/4_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🏛️ Modelli Fattoriali, Black-Litterman & ML", "keywords": "carhart barra fama french black litterman fattori regressione ml"},
            # Posizioni
            {"title": "📋 Posizioni ➔ FIFO Realized & Graveyard", "page": "pages/5_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "🪦 Posizioni Chiuse & Graveyard", "keywords": "posizioni fifo plusvalenze minusvalenze pnl book ordini titoli graveyard"},
            {"title": "📋 Posizioni ➔ Fisco Italiano TUIR Art. 67 & Step-Up", "page": "pages/5_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "💰 Ottimizzazione Fiscale (TUIR Art. 67)", "keywords": "fisco tasse tuir imposte minusvalenze capital gain 26% tax harvesting step-up tax"},
            {"title": "📋 Posizioni ➔ Calendario Dividendi & Yield", "page": "pages/5_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "📅 Proiezione Dividendi", "keywords": "dividendi stacco yield cedole proiezioni calendario div"},
            # Valutazione
            {"title": "🏛️ Valutazione ➔ DCF Monte Carlo & WACC", "page": "pages/6_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "🧮 Valutazione Intrinseca DCF Monte Carlo", "keywords": "dcf discounted cash flow wacc capm fair value intrinseco monte carlo"},
            {"title": "🏛️ Valutazione ➔ Solvibilità Altman & Beneish", "page": "pages/6_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "📊 Bilanci & Solvibilità (Altman & DuPont)", "keywords": "altman z score dupont bilanci solvibilita beneish m score sloan des fa"},
            {"title": "🏛️ Valutazione ➔ Consensus Analisti & Target Price", "page": "pages/6_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "🏛️ Fair Value & Consensus Analisti", "keywords": "consensus analisti target price price target anr stime"},
            # Stress
            {"title": "🌪️ Stress Testing ➔ Matrice Scenari MSCI Barra", "page": "pages/7_🌪️_Stress_Testing.py", "tab_key": "stress_active_tab", "target": "⚡ Matrice Comparativa MSCI Barra", "keywords": "stress testing msci barra scenari storici crisi 2008 covid crollo stress"},
            # Analisi Temporale
            {"title": "📊 Analisi Temporale ➔ Storicizzazione Multi-Snapshot", "page": "pages/8_📊_Analisi_Temporale.py", "tab_key": None, "target": None, "keywords": "analisi temporale snapshot storicizzazione drawdown rolling timeline"},
            # Tecnica
            {"title": "📈 Tecnica ➔ Candlestick & Volume Profile (POC)", "page": "pages/9_📈_Analisi_Tecnica.py", "tab_key": "tech_active_subtab", "target": "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)", "keywords": "analisi tecnica candlestick volume profile poc vah val rsi macd hp tech"},
            # Screener
            {"title": "🔍 Screener ➔ Screener Opportunità (EQS)", "page": "pages/10_🔍_Screener_Opportunita.py", "tab_key": "screener_segmented_subtab", "target": "🔍 Screener Multi-Fattoriale & Archetipi", "keywords": "screener filtri opportunita momentum value growth dividendi qualita eqs"},
            {"title": "🔍 Screener ➔ Pre-Trade Impact Simulator", "page": "pages/10_🔍_Screener_Opportunita.py", "tab_key": "screener_segmented_subtab", "target": "🧪 Pre-Trade Portfolio Impact Simulator", "keywords": "pre-trade simulatore impatto nuovo acquisto asset candidato"},
            # BQuant
            {"title": "💻 BQuant ➔ Python Sandbox & Launchpad", "page": "pages/11_💻_BQuant_e_Launchpad.py", "tab_key": "bquant_active_tab", "target": "🐍 ARGUS BQuant Python Sandbox", "keywords": "bquant python console sandbox script launchpad excel rtd workspace"}
        ]

        matched = []
        q_lower = query.lower()
        for item in search_index:
            if not query:
                matched.append(item)
            else:
                q_words = q_lower.split()
                if any(w in item["title"].lower() or w in item["keywords"].lower() for w in q_words):
                    matched.append(item)

        if matched:
            for item in matched[:6]:
                if st.button(item["title"], key=f"spot_idx_{item['title']}", use_container_width=True):
                    if item["tab_key"] and item["target"]:
                        st.session_state[item["tab_key"]] = item["target"]
                        st.session_state[f"target_subtab_{item['tab_key']}"] = item["target"]
                        st.session_state["global_target_subtab"] = item["target"]
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page(item["page"])
        else:
            st.caption("Nessuna scheda trovata.")

    # ── COLONNA 2: TICKER & MNEMONICI RAPIDI ────────────────────────
    with col_res2:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">💼 MNEMONICI RAPIDI & TICKER</div>', unsafe_allow_html=True)
        
        display_tickers = portfolio_tickers if portfolio_tickers else ["AAPL", "MSFT", "NVDA", "BTC-USD", "SPY", "QQQ"]
        cleaned_q = query.upper().strip()
        if cleaned_q and len(cleaned_q) <= 10 and cleaned_q not in display_tickers:
            display_tickers = [cleaned_q] + [t for t in display_tickers if cleaned_q in t]

        for tk in display_tickers[:3]:
            st.markdown(f"**Asset: `{tk}`**")
            c_tk1, c_tk2 = st.columns(2)
            with c_tk1:
                if st.button(f"📊 {tk} DES", key=f"spot_des_{tk}", use_container_width=True):
                    st.session_state["selected_val_company"] = tk
                    st.session_state["val_segmented_tab"] = "📊 Bilanci & Solvibilità (Altman & DuPont)"
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page("pages/5_🏛️_Valutazione_Aziendale.py")
            with c_tk2:
                if st.button(f"📈 {tk} HP", key=f"spot_hp_{tk}", use_container_width=True):
                    st.session_state["tech_ticker_input"] = tk
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page("pages/8_📈_Analisi_Tecnica.py")

    # ── COLONNA 3: SISTEMA & SHORTCUT CHEAT SHEET ───────────────────
    with col_res3:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">⌨️ SHORTCUTS</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="font-family:monospace; font-size:11px; color:#8b949e; line-height:1.6;">
            <div><strong style="color:#ff9900;">YCRV</strong> Curva Tassi</div>
            <div><strong style="color:#ff9900;">PORT</strong> Rischio VaR</div>
            <div><strong style="color:#ff9900;">ATTR</strong> Carino Link</div>
            <div><strong style="color:#ff9900;">EQS</strong> Screener</div>
            <div><strong style="color:#ff9900;">TAX</strong> Step-Up</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("♻️ Reset Cache", key="spot_clean_cache_all", use_container_width=True):
            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]
            switch_to_page("0_Control_Room.py")
    
    st.divider()


@st.dialog("🏛️ ARGUS WEALTH COMMAND GATEWAY", width="large")
def render_wealth_spotlight_palette():
    """Renderizza la Command Line Gateway specificamente dedicata ad ARGUS Wealth come vero modale @st.dialog con parser mnemonico patrimoniale ed estetica Emerald."""
    from core.sidebar import switch_to_page
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(16, 28, 24, 0.98) 0%, rgba(10, 18, 14, 1.0) 100%); border: 1.5px solid #10b981; border-radius: 10px; padding: 10px 16px; margin: 0 0 14px 0; box-shadow: 0 12px 35px rgba(0,0,0,0.8), 0 0 20px rgba(16, 185, 129, 0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div style="font-size:12.5px; font-weight:800; color:#10b981; letter-spacing:0.8px; display:inline-flex; align-items:center; gap:8px;">
                <span>🏛️</span> ARGUS WEALTH COMMAND DESK
                <span style="font-size:9.5px; padding:1px 6px; background:#10b981; color:#000000; border-radius:3px; font-weight:900; letter-spacing:0.5px;">WEALTH PARITY</span>
            </div>
            <div style="font-size:11px; color:#8b949e; font-family:monospace;">
                Sintassi Wealth: <span style="color:#e6edf3;">&lt;COMANDO&gt;</span> • es. <code style="color:#34d399; background:rgba(16,185,129,0.12); padding:1px 4px; border-radius:3px;">NETWORTH</code>, <code style="color:#34d399; background:rgba(16,185,129,0.12); padding:1px 4px; border-radius:3px;">CASHFLOW</code>, <code style="color:#34d399; background:rgba(16,185,129,0.12); padding:1px 4px; border-radius:3px;">WTIME</code>, <code style="color:#34d399; background:rgba(16,185,129,0.12); padding:1px 4px; border-radius:3px;">REPORTS</code>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_q, col_exec = st.columns([4.8, 1.2])
    with col_q:
        query = st.text_input(
            "Wealth Command", 
            placeholder="⌨️ Digita comando: es. NETWORTH, CASHFLOW, BUDGET, CAVEAU, PENSION, FIRE, RW, REALESTATE, ESTATE, WCOPILOT, WTIME, REPORTS...", 
            key="spotlight_wealth_search_box", 
            label_visibility="collapsed"
        ).strip()
    
    parsed_cmd = parse_terminal_command(query)

    with col_exec:
        exec_label = f"▶ <GO> ({parsed_cmd['mnemonic']})" if parsed_cmd else "▶ <GO>"
        if st.button(exec_label, key="btn_exec_wealth_command_go", use_container_width=True, type="primary" if parsed_cmd else "secondary"):
            if parsed_cmd:
                if parsed_cmd.get("tab_key") and parsed_cmd.get("target"):
                    st.session_state[parsed_cmd["tab_key"]] = parsed_cmd["target"]
                    st.session_state[f"target_subtab_{parsed_cmd['tab_key']}"] = parsed_cmd["target"]
                    st.session_state["global_target_subtab"] = parsed_cmd["target"]
                switch_to_page(parsed_cmd["page"])
            else:
                st.warning("Comando Wealth non riconosciuto. Digita es. `NETWORTH`, `CASHFLOW`, `WTIME` o `REPORTS`.")

    # Visual Feedback del comando riconosciuto
    if parsed_cmd:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.12); border-left: 3px solid #10b981; padding: 6px 12px; margin-bottom: 12px; font-size: 12px; color: #e6edf3; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-weight:700; color:#34d399;">COMANDO PATRIMONIALE RICONOSCIUTO:</span> 
                <code style="color:#34d399; background:#161b22; padding:2px 6px; border-radius:3px;">{parsed_cmd.get('raw_command', query)}</code> ➔ 
                <strong>{parsed_cmd['title']}</strong> ({parsed_cmd['page']})
            </div>
            <div style="font-size:11px; color:#8b949e;">Premi <strong>&lt;GO&gt;</strong> per eseguire</div>
        </div>
        """, unsafe_allow_html=True)

    col_w1, col_w2, col_w3 = st.columns([1.6, 1.4, 1.0])

    # ── COLONNA 1: SCHEDE & MODULI PATRIMONIALI ──────────────────────
    with col_w1:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#10b981; margin-bottom:6px; letter-spacing:0.5px;">🏛️ MODULI &amp; STRUMENTI WEALTH</div>', unsafe_allow_html=True)
        
        wealth_search_index = [
            {"title": "🎛️ Control Room & Ingestione Wealth", "page": "pages/12_🎛️_Wealth_Control_Room.py", "tab_key": None, "target": None, "keywords": "control room upload csv estratti conto sincronizzazione gsheets saldi conti wcr"},
            {"title": "🏛️ Patrimonio & Net Worth Consolidato", "page": "pages/13_🏛️_Patrimonio_e_NetWorth.py", "tab_key": None, "target": None, "keywords": "stato patrimoniale net worth attivo passivo liquidita investimenti salute networth nw wealth"},
            {"title": "📊 Wealth Temporal Desk (Matrici & Drawdown)", "page": "pages/13_🏛️_Patrimonio_e_NetWorth.py", "tab_key": None, "target": None, "keywords": "analisi temporale progressione storica matrice mensile underwater rolling stagionalita wtime time"},
            {"title": "💳 Cash Flow, Spese & Budgeting 50/30/20", "page": "pages/14_💳_Cash_Flow_e_Spese.py", "tab_key": None, "target": None, "keywords": "cash flow uscite entrate 50 30 20 buste envelope abbonamenti riclassificazione cashflow budget cf"},
            {"title": "⌚ Caveau Asset Fisici, Orologi & Illiquidi", "page": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py", "tab_key": None, "target": None, "keywords": "caveau orologi rolex patek arte metalli oro private equity debt perizie watches illiquid pdebt"},
            {"title": "🛡️ Previdenza, Fondi Pensione & Goal SPI", "page": "pages/16_🛡️_Previdenza_e_Pension_Planning.py", "tab_key": None, "target": None, "keywords": "previdenza integrativa fondi pensione tfr merton obiettivi glide path deducibilita pension goal"},
            {"title": "🔥 Indipendenza Finanziaria, FIRE & SWR", "page": "pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py", "tab_key": None, "target": None, "keywords": "fire financial independence safe withdrawal rate 4% monte carlo sequenza rendimenti coast lean"},
            {"title": "📑 Fiscalità, Monitoraggio Estero & Quadro RW", "page": "pages/18_📑_Fiscalita_e_Quadro_RW.py", "tab_key": None, "target": None, "keywords": "fisco quadro rw ivafe mod redditi minusvalenze zainetto neo residenti cross border rw globaltax tax"},
            {"title": "🏡 Immobili, Mutui Ammortamento & Buy vs Rent", "page": "pages/19_🏡_Immobili_e_Mutui.py", "tab_key": None, "target": None, "keywords": "immobili mutui ammortamento francese cap rate rendita locativa ltv buy rent realestate re mortgage"},
            {"title": "⚖️ Pianificazione Successoria & Patti Famiglia", "page": "pages/20_⚖️_Pianificazione_Successoria.py", "tab_key": None, "target": None, "keywords": "successione eredita legittima asse ereditario patti famiglia holding protezione estate succession"},
            {"title": "🤖 AI Copilot & Advisor Intelligente", "page": "pages/21_🤖_AI_Copilot_e_Advisor.py", "tab_key": None, "target": None, "keywords": "ai advisor copilot health score memorandum life event podcast briefing wcopilot advisor voice"},
            {"title": "📑 Hub di Reportistica & 9 Esportazioni", "page": "pages/12_🎛️_Wealth_Control_Room.py", "tab_key": None, "target": None, "keywords": "esportazioni pdf pitchbook excel master parquet csv json reportistica reports export"}
        ]

        matched_w = []
        q_lower = query.lower()
        for item in wealth_search_index:
            if not query:
                matched_w.append(item)
            else:
                q_words = q_lower.split()
                if any(w in item["title"].lower() or w in item["keywords"].lower() for w in q_words):
                    matched_w.append(item)

        if matched_w:
            for item in matched_w[:6]:
                if st.button(item["title"], key=f"spot_w_idx_{item['title']}", use_container_width=True):
                    if item["tab_key"] and item["target"]:
                        st.session_state[item["tab_key"]] = item["target"]
                        st.session_state[f"target_subtab_{item['tab_key']}"] = item["target"]
                        st.session_state["global_target_subtab"] = item["target"]
                    switch_to_page(item["page"])
        else:
            st.caption("Nessun modulo patrimoniale trovato.")

    # ── COLONNA 2: AZIONI RAPIDE & MNEMONICI WEALTH ──────────────────
    with col_w2:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#10b981; margin-bottom:6px; letter-spacing:0.5px;">💎 MNEMONICI PATRIMONIALI RAPIDI</div>', unsafe_allow_html=True)
        
        w_actions = [
            ("🏛️ NETWORTH", "pages/13_🏛️_Patrimonio_e_NetWorth.py", "Stato Patrimoniale"),
            ("📊 WTIME", "pages/13_🏛️_Patrimonio_e_NetWorth.py", "Analisi Temporale"),
            ("💳 CASHFLOW", "pages/14_💳_Cash_Flow_e_Spese.py", "Rendiconto Spese"),
            ("⌚ CAVEAU", "pages/15_⌚_Asset_Illiquidi_e_Orologi.py", "Caveau Orologi & PE"),
            ("🛡️ PENSION", "pages/16_🛡️_Previdenza_e_Pension_Planning.py", "Previdenza Integrativa"),
            ("🔥 FIRE", "pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py", "Simulatore FIRE"),
            ("📑 RW", "pages/18_📑_Fiscalita_e_Quadro_RW.py", "Quadro RW & Fisco"),
            ("🏡 REALESTATE", "pages/19_🏡_Immobili_e_Mutui.py", "Immobili & Mutui"),
            ("⚖️ ESTATE", "pages/20_⚖️_Pianificazione_Successoria.py", "Successioni & Patti"),
            ("🤖 WCOPILOT", "pages/21_🤖_AI_Copilot_e_Advisor.py", "Diagnostica AI"),
            ("🎙️ VOICE", "pages/21_🤖_AI_Copilot_e_Advisor.py", "Podcast Briefing"),
            ("📑 REPORTS", "pages/12_🎛️_Wealth_Control_Room.py", "Hub Esportazioni")
        ]

        for lbl, pg, _ in w_actions[:6]:
            if st.button(lbl, key=f"spot_w_btn_{lbl}", use_container_width=True):
                switch_to_page(pg)

    # ── COLONNA 3: SHORTCUTS CHEAT SHEET WEALTH ───────────────────────
    with col_w3:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#10b981; margin-bottom:6px; letter-spacing:0.5px;">⌨️ SHORTCUTS WEALTH</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="font-family:monospace; font-size:11px; color:#8b949e; line-height:1.6;">
            <div><strong style="color:#34d399;">NW</strong> Net Worth 360°</div>
            <div><strong style="color:#34d399;">CF</strong> Cash Flow 50/30/20</div>
            <div><strong style="color:#34d399;">TIME</strong> Matrice &amp; DD</div>
            <div><strong style="color:#34d399;">WATCH</strong> Caveau Orologi</div>
            <div><strong style="color:#34d399;">RE</strong> Immobili &amp; LTV</div>
            <div><strong style="color:#34d399;">FIRE</strong> Indipendenza 4%</div>
            <div><strong style="color:#34d399;">RW</strong> Quadro RW / RT</div>
            <div><strong style="color:#34d399;">REPORTS</strong> 9 Esportazioni</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("♻️ Reset Cache Wealth", key="spot_clean_cache_wealth", use_container_width=True):
            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]
            st.session_state.argus_portal_mode = "🏛️ Wealth Management"
            switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")
    
    st.divider()


def render_workflow_stepper(current_step: int = 1):
    """Renderizza uno stepper grafico a 3 fasi per l'ingestione dati."""
    s1_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 1 else "color: #8b949e;"
    s2_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 2 else "color: #8b949e;"
    s3_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 3 else "color: #8b949e;"

    s1_icon = "✅" if current_step > 1 else "1️⃣"
    s2_icon = "✅" if current_step > 2 else "2️⃣"
    s3_icon = "🚀" if current_step == 3 else "3️⃣"

    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; margin: 15px 0 25px 0; background: rgba(22, 27, 34, 0.6); padding: 12px 18px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(12px);">
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s1_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s1_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">1. Carica File CSV</span>
        </div>
        <div style="width: 30px; text-align: center; color: rgba(255,255,255,0.2); font-weight:bold;">➔</div>
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s2_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s2_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">2. Validazione Dati</span>
        </div>
        <div style="width: 30px; text-align: center; color: rgba(255,255,255,0.2); font-weight:bold;">➔</div>
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s3_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s3_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">3. Calcolo & Motore Rischio</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_validation_report(report: dict):
    """Renderizza in modo pulito ed elegante i report di validazione (errors, warnings, fixes)."""
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    fixes = report.get("fixes", [])

    if errors:
        st.markdown('<div class="section-header" style="color: #f85149; border-color: rgba(248, 81, 73, 0.4);">🔴 Errori di Validazione Bloccanti</div>', unsafe_allow_html=True)
        for e in errors:
            st.markdown(f'''
            <div style="background: rgba(248, 81, 73, 0.12); border-left: 4px solid #f85149; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; color: #ff7b72;">
                <strong>🔴 Blocco Ingestione:</strong> {e}
            </div>
            ''', unsafe_allow_html=True)
        st.stop()

    if fixes or warnings:
        tot_items = len(fixes) + len(warnings)
        fixes_badge = f'<span class="executive-badge badge-green">🟢 {len(fixes)} Correzioni Automatiche</span>' if fixes else ''
        warn_badge = f'<span class="executive-badge badge-yellow">🟡 {len(warnings)} Avvisi di Controllo</span>' if warnings else ''

        with st.expander(f"🛠️ Dettaglio Audit Data Quality ({tot_items} note di validazione)", expanded=bool(warnings)):
            st.markdown(f'<div style="margin-bottom: 12px;">{fixes_badge}{warn_badge}</div>', unsafe_allow_html=True)
            
            if fixes:
                st.markdown("**🟢 Correzioni ed Aggiustamenti Automatici Applicati:**")
                for f in fixes:
                    st.markdown(f'<div style="background: rgba(63, 185, 80, 0.08); border-left: 3px solid #3fb950; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #e6edf3;">✓ {f}</div>', unsafe_allow_html=True)

            if warnings:
                st.markdown("**🟡 Avvisi sulle Transazioni (Verifica consigliata):**")
                for w in warnings:
                    st.markdown(f'<div style="background: rgba(210, 153, 34, 0.08); border-left: 3px solid #d29922; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #e6edf3;">⚠️ {w}</div>', unsafe_allow_html=True)


def render_executive_badges(metrics_dict: dict):
    """Renderizza i badge esecutivi di salute e profilo del portafoglio."""
    ret = metrics_dict.get("returns", {})
    mk = metrics_dict.get("market_risk", {})
    
    sharpe = ret.get("sharpe_ratio", 0.0) or 0.0
    vol = mk.get("volatility_annual_pct", 0.0) or 0.0
    max_dd = abs(mk.get("max_drawdown_pct", 0.0) or 0.0)
    
    # Sharpe Badge
    if sharpe >= 1.2:
        sharpe_badge = '<span class="executive-badge badge-green">🟢 Sharpe Eccellente (> 1.2)</span>'
    elif sharpe >= 0.7:
        sharpe_badge = '<span class="executive-badge badge-yellow">🟡 Sharpe Moderato (0.7 - 1.2)</span>'
    else:
        sharpe_badge = '<span class="executive-badge badge-red">🔴 Sharpe Contenuto (< 0.7)</span>'

    # Volatility Badge
    if vol <= 15.0:
        vol_badge = '<span class="executive-badge badge-green">🟢 Profilo Conservativo (Vol < 15%)</span>'
    elif vol <= 25.0:
        vol_badge = '<span class="executive-badge badge-yellow">🟡 Profilo Bilanciato (Vol 15-25%)</span>'
    else:
        vol_badge = '<span class="executive-badge badge-red">🔴 Profilo Aggressivo (Vol > 25%)</span>'

    # Drawdown Badge
    if max_dd <= 12.0:
        dd_badge = '<span class="executive-badge badge-green">🟢 Drawdown Contenuto (< 12%)</span>'
    elif max_dd <= 22.0:
        dd_badge = '<span class="executive-badge badge-yellow">🟡 Drawdown Moderato (12-22%)</span>'
    else:
        dd_badge = '<span class="executive-badge badge-red">🔴 Drawdown Elevato (> 22%)</span>'

    st.markdown(f'<div style="margin-top: 4px; margin-bottom: 6px;">{sharpe_badge}{vol_badge}{dd_badge}</div>', unsafe_allow_html=True)


def optimize_plotly_figure_memory(fig, precision: int = 4):
    """
    Comprime la serializzazione JSON delle figure Plotly per minimizzare il consumo di RAM
    nel browser e nel server Streamlit:
    - Arrotonda gli array float a 4 cifre decimali (evitando stringhe float64 a 16 cifre).
    - Converte coordinate, color scale e customdata numerici in formati compatti.
    """
    if fig is None or not hasattr(fig, "data"):
        return fig
    try:
        for trace in fig.data:
            for attr in ["x", "y", "z", "customdata", "text"]:
                if hasattr(trace, attr):
                    val = getattr(trace, attr)
                    if val is not None and isinstance(val, (list, tuple, np.ndarray, pd.Series)):
                        arr = np.asarray(val)
                        if np.issubdtype(arr.dtype, np.floating):
                            rounded = np.round(arr, precision)
                            setattr(trace, attr, rounded.tolist())
            if hasattr(trace, "marker") and trace.marker is not None:
                if hasattr(trace.marker, "color") and trace.marker.color is not None:
                    m_color = trace.marker.color
                    if isinstance(m_color, (list, tuple, np.ndarray, pd.Series)):
                        arr_c = np.asarray(m_color)
                        if np.issubdtype(arr_c.dtype, np.floating):
                            setattr(trace.marker, "color", np.round(arr_c, precision).tolist())
    except Exception:
        pass
    return fig


ARGUS_CHART_PALETTES = {
    "risk": ["#ff9900", "#ff5555", "#58a6ff", "#3fb950", "#bc8cff", "#f0883e"],
    "wealth": ["#10b981", "#38bdf8", "#818cf8", "#fbbf24", "#a78bfa", "#f43f5e"]
}

def apply_plotly_theme(fig, theme_name=None, portal_mode="auto"):
    """Applica uno stile dark vettoriale con tooltip luminosi al grafico Plotly e ottimizza la memoria."""
    if fig is None:
        return fig

    if not theme_name:
        theme_name = st.session_state.get("ui_theme", "Midnight Obsidian")

    is_wealth = (portal_mode == "wealth" or (portal_mode == "auto" and st.session_state.get("argus_portal_mode") == "🏛️ Wealth Management"))
    if is_wealth:
        accent = "#10b981"
    else:
        accent = "#ff9900" if theme_name == "Midnight Obsidian" else ("#00f3ff" if theme_name == "Cyberpunk Neon" else "#00c853")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#e6edf3"),
        hoverlabel=dict(
            bgcolor="#161b22",
            font_size=13,
            font_family="Outfit, sans-serif",
            bordercolor=accent
        ),
        margin=dict(l=20, r=20, t=30, b=30),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
    
    # Comprime e ottimizza i float per ridurre il footprint in RAM
    optimize_plotly_figure_memory(fig, precision=4)
    return fig

apply_chart_theme = apply_plotly_theme


def render_factor_radar_chart(results: dict):
    """Genera un grafico Radar / Spider a 360° dell'impronta di rischio del portafoglio confrontato con il Benchmark di Riferimento."""
    import plotly.graph_objects as go
    m = results.get("metrics", {})
    mk = m.get("market_risk", {})
    con = m.get("concentration", {})
    
    categories = [
        "Market Beta",
        "Size SMB",
        "Value HML",
        "Volatilità",
        "Diversificazione DR",
        "Asimmetria Skew"
    ]
    
    beta = min(100.0, max(0.0, (mk.get("beta", 1.0) or 1.0) * 50))
    smb = min(100.0, max(0.0, (mk.get("smb_tilt", 0.0) or 0.0) * 50 + 50))
    hml = min(100.0, max(0.0, (mk.get("hml_tilt", 0.0) or 0.0) * 50 + 50))
    vol = min(100.0, max(0.0, (mk.get("volatility_annual_pct", 15.0) or 15.0) * 2))
    dr = min(100.0, max(0.0, ((con.get("diversification_ratio", 1.2) or 1.2) - 1.0) * 100))
    skew = min(100.0, max(0.0, (mk.get("skewness", 0.0) or 0.0) * 25 + 50))
    
    values = [beta, smb, hml, vol, dr, skew]
    values.append(values[0])
    cats = list(categories) + [categories[0]]
    
    # Baseline neutra/benchmark (50/100 su ogni fattore)
    baseline_values = [50, 50, 50, 50, 50, 50, 50]

    fig = go.Figure()
    
    # Trace 1: Target Neutral Baseline
    fig.add_trace(go.Scatterpolar(
        r=baseline_values,
        theta=cats,
        fill='toself',
        fillcolor='rgba(143, 160, 186, 0.08)',
        line=dict(color='#8fa0ba', width=1.5, dash='dash'),
        name='Benchmark Neutro (50/100)',
        hovertemplate="<b>Benchmark Neutro</b><br>Fattore: %{theta}<br>Score Target: 50.0/100<extra></extra>"
    ))
    
    # Trace 2: Portafoglio Actuel
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=cats,
        mode='lines+markers',
        fill='toself',
        fillcolor='rgba(255, 153, 0, 0.25)',
        line=dict(color='#ff9900', width=2.5),
        marker=dict(size=6, color='#ff9900'),
        name='Impronta Portafoglio',
        hovertemplate="<b>%{theta}</b><br>Score Portafoglio: %{r:.1f} / 100<extra></extra>"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(size=12, color="#c9d1d9")),
            bgcolor="rgba(0,0,0,0)"
        ),
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
        height=370,
        margin=dict(l=35, r=35, t=20, b=30)
    )
    return apply_plotly_theme(fig)


def render_risk_heatmap(positions_df, risk_contrib=None):
    """Genera una Treemap / Risk Heatmap ad alta densità per asset class e singola posizione con styling istituzionale Finviz/Bloomberg."""
    import plotly.graph_objects as go
    import pandas as pd
    import numpy as np

    if positions_df is None or positions_df.empty:
        return None
    
    df = positions_df[positions_df["current_value"] > 0].copy()
    if df.empty:
        return None
        
    df["asset_class"] = df["asset_class"].fillna("Altro").astype(str).str.upper()
    
    # Calcolo del PnL % per tile text
    if "unrealized_pnl" in df.columns:
        if "cost_basis" in df.columns:
            df["pnl_pct"] = np.where(df["cost_basis"] > 0, (df["unrealized_pnl"] / df["cost_basis"]) * 100.0, 0.0)
        else:
            df["pnl_pct"] = 0.0
    else:
        df["unrealized_pnl"] = 0.0
        df["pnl_pct"] = 0.0

    if "weight_pct" not in df.columns:
        tot_val = df["current_value"].sum()
        df["weight_pct"] = (df["current_value"] / tot_val * 100.0) if tot_val > 0 else 0.0

    # Costruiamo la gerarchia Treemap esplicita
    ids, labels, parents, values, colors, texts, hovertexts = [], [], [], [], [], [], []

    # 1. Raggruppamenti di Primo Livello (Asset Classes / Containers)
    for ac, grp in df.groupby("asset_class"):
        tot_val = float(grp["current_value"].sum())
        tot_pnl = float(grp["unrealized_pnl"].sum())
        ids.append(ac)
        labels.append(ac)
        parents.append("")
        values.append(tot_val)
        colors.append(0.0)  # Header neutro dark (#161b22) per il contenitore di categoria
        texts.append(f"<b>{ac}</b>")
        hovertexts.append(f"<b>{ac}</b><br>Controvalore Totale: € {tot_val:,.2f}<br>PnL Complessivo: {tot_pnl:+,.2f} €")

    # 2. Singoli Asset / Posizioni Foglia
    for _, r in df.iterrows():
        ac = str(r["asset_class"])
        t = str(r["ticker"])
        val = float(r["current_value"])
        pnl = float(r["unrealized_pnl"])
        pnl_pct = float(r["pnl_pct"])
        w_pct = float(r["weight_pct"])
        
        pnl_str = f"{pnl:+,.0f} €" if abs(pnl) >= 100 else f"{pnl:+,.2f} €"
        pct_str = f"{pnl_pct:+.1f}%"
        
        ids.append(f"{ac}/{t}")
        labels.append(t)
        parents.append(ac)
        values.append(val)
        colors.append(pnl)
        texts.append(f"<b>{t}</b><br>{pnl_str}<br>({pct_str})")
        hovertexts.append(f"<b>{t}</b><br>Asset Class: {ac}<br>Controvalore: € {val:,.2f}<br>Peso Portafoglio: {w_pct:.2f}%<br>PnL Latente: {pnl:+,.2f} € ({pnl_pct:+.2f}%)")

    # Determiniamo il range simmetrico per il color mapping
    non_zero_colors = [abs(c) for c in colors if c != 0.0]
    max_abs_pnl = max(non_zero_colors) if non_zero_colors else 100.0

    # Scala di colori professionale in stile Finviz / Bloomberg Dark:
    finviz_scale = [
        [0.0, "#8b1818"],     # Forte perdita (Dark Crimson)
        [0.35, "#da3633"],    # Perdita moderata (Coral Red)
        [0.48, "#282e36"],    # Perdita lieve (Dark Slate)
        [0.50, "#161b22"],    # Neutro / Zero (Obsidian Dark)
        [0.52, "#282e36"],    # Guadagno lieve (Dark Slate)
        [0.65, "#238636"],    # Guadagno moderato (Emerald Green)
        [1.0, "#0d6e2e"]      # Forte guadagno (Deep Forest)
    ]

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        text=texts,
        textinfo="text",
        hovertext=hovertexts,
        hoverinfo="text",
        marker=dict(
            colors=colors,
            colorscale=finviz_scale,
            cmin=-max_abs_pnl,
            cmax=max_abs_pnl,
            colorbar=dict(
                title=dict(text="PnL Latente (€)", font=dict(size=12, color="#c9d1d9")),
                tickformat="€ ,.0f",
                thickness=14,
                len=0.85,
                tickfont=dict(size=11, color="#8b949e")
            ),
            line=dict(color="#0d1117", width=2),
            pad=dict(b=4, l=4, r=4, t=24)
        ),
        textposition="middle center",
        textfont=dict(size=13, color="#ffffff")
    ))
    
    fig.update_layout(
        height=420,
        margin=dict(l=5, r=5, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return apply_plotly_theme(fig)



def format_institutional_5point_html(
    title: str,
    what_is: str,
    how_calc: str,
    why_useful: str,
    argus_calc: str,
    how_to_read: str,
    limitations: Optional[str] = None
) -> str:
    """
    Formatta il contenuto informativo di modali e popover seguendo rigorosamente
    lo standard istituzionale a 5 sezioni:
    1. 📌 Cos'è (Definizione Formale & Intuizione Finanziaria)
    2. ⚙️ Come viene calcolata da ARGUS (Formula & Dettagli Implementativi)
    3. 🎯 A cosa serve (Casi d'Uso Pratici & Decision Making)
    4. 📊 Come si legge & Valori Guida (Soglie di Riferimento)
    5. ⚠️ Limitazioni & Assunzioni del Modello
    """
    limitations_block = ""
    if limitations and len(str(limitations).strip()) > 0:
        limitations_block = f"""
    <div style="margin-top: 10px; background: rgba(248, 113, 113, 0.06); border: 1px solid rgba(248, 113, 113, 0.25); border-left: 3px solid #f87171; border-radius: 6px; padding: 10px 12px;">
      <div style="color: #f87171; font-weight: 700; font-size: 13px; margin-bottom: 4px;">⚠️ Limitazioni & Assunzioni del Modello:</div>
      <div style="color: #e6edf3; font-size: 12.5px; line-height: 1.5;">{limitations}</div>
    </div>"""

    return f"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
  <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
    <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 8px;">{title}</div>
    <div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> {what_is}</div>
    <div style="margin-bottom: 8px;">
      <b>⚙️ Come viene calcolato da ARGUS:</b>
      <div style="color: #c9d1d9; font-size: 12.5px; line-height: 1.5; margin-top: 3px; margin-bottom: 6px;">{argus_calc}</div>
      <div style="margin-top: 4px;"><b>📐 Come si calcola:</b>
        <div style="background: rgba(255,153,0,0.06); border: 1px solid rgba(255,153,0,0.20); border-left: 3px solid #ff9900; padding: 8px 12px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; line-height: 1.6;">
          {how_calc}
        </div>
      </div>
    </div>
    <div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> {why_useful}</div>
    <div style="margin-bottom: 8px;">
      <b>📊 Come si legge & Valori Guida:</b>
      <div style="margin-top: 3px;"><b>🔍 Come leggerlo:</b><br>{how_to_read}</div>
    </div>
    {limitations_block}
  </div>
</div>
"""


KNOWN_METRICS_KNOWLEDGE_BASE = {
    'rendimento_atteso': {
        'title': '📈 Rendimento Atteso (Expected Return / CAGR)',
        'what_is': 'Tasso di rendimento composto annuo atteso o storico generato dal portafoglio di investimenti.',
        'how_calc': '<b>CAGR</b> = (V<sub>finale</sub> / V<sub>iniziale</sub>)<sup>252 / N</sup> &minus; 1 &nbsp;|&nbsp; <b>&mu;<sub>port</sub></b> = <b>w</b><sup>T</sup> &mu;',
        'why_useful': 'Misurare la capacità del portafoglio di incrementare il capitale nel tempo al netto delle fluttuazioni temporanee.',
        'argus_calc': 'Calcolato sulle serie storiche dei prezzi rettificati (Adjusted Close) con base a 252 sedute lavorative o per combinazione lineare dei pesi simulati.',
        'how_to_read': "• 🟢 > Benchmark (Alpha positivo, sovraperformance gestionale)<br>• 🟡 In linea con l'indice di riferimento (Beta puro)<br>• 🔴 < Benchmark o negativo (Erosione del capitale reale).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'volatilita_annua': {
        'title': '⚡ Volatilità Annua (Annualized Standard Deviation)',
        'what_is': 'Misura statistica della dispersione dei rendimenti del portafoglio attorno alla loro media (rischio totale di mercato).',
        'how_calc': '<b>&sigma;<sub>annua</sub></b> = &sigma;<sub>daily</sub> &times; &radic;252 = &radic;(<b>w</b><sup>T</sup> &Sigma; <b>w</b>) &times; &radic;252',
        'why_useful': "Quantificare l'incertezza e l'ampiezza delle oscillazioni di prezzo a cui è esposto il capitale nel corso di un anno solare.",
        'argus_calc': 'Determinata tramite moltiplicazione quadratica della matrice di covarianza (de-noised con shrinkage Ledoit-Wolf) per il vettore dei pesi, annualizzata a 252 sedute.',
        'how_to_read': '• 🟢 < 12.0% (Profilo Prudente/Conservativo)<br>• 🟡 12.0% - 22.0% (Profilo Bilanciato Standard)<br>• 🔴 > 22.0% (Profilo Aggressivo ad elevata oscillazione).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'var_95': {
        'title': '🛡️ Value at Risk Parametrico 95% (Parametric Gaussian VaR)',
        'what_is': 'La massima perdita monetaria o percentuale attesa su un orizzonte di 1 giorno con un livello di confidenza statistica del 95%, assumendo che i rendimenti seguano una distribuzione Normale multivariata.',
        'how_calc': '<b>VaR<sub>95%, 1D</sub></b> = &minus;(&mu;<sub>daily</sub> &minus; 1.6449 &times; &sigma;<sub>port, daily</sub>) &nbsp;|&nbsp; <b>&sigma;<sub>port</sub></b> = &radic;(<b>w</b><sup>T</sup> &Sigma; <b>w</b>)',
        'why_useful': 'Fissare il limite prudenziale di perdita massima in condizioni ordinarie di mercato per calibrare liquidità di emergenza, margini di mantenimento e risk budgeting.',
        'argus_calc': 'Calcolato sui rendimenti percentuali discreti giornalieri R<sub>t</sub> = (P<sub>t</sub>/P<sub>t-1</sub>) - 1. Matrice di covarianza de-noised con shrinkage Ledoit-Wolf. Confidenza al 95% (z = 1.6449), orizzonte a 1 giorno lavorativo (base annua 252 sedute).',
        'how_to_read': '• 🟢 &lt; 1.50% (Rischio giornaliero contenuto e conservativo)<br>• 🟡 1.50% - 2.50% (Esposizione nella media per portafogli bilanciati)<br>• 🔴 &gt; 2.50% (Elevata vulnerabilità a shock giornalieri ordinari).',
        'limitations': "Punto cieco fondamentale: assume rendimenti distribuiti normalmente (code sottili), sottostimando drasticamente le perdite durante i crolli di borsa (Fat Tails). Non fornisce alcuna indicazione sull'entità della perdita oltre la soglia del 95%.",
    },
    'cvar_95': {
        'title': '🛡️ CVaR / Expected Shortfall (Rischio Coerente di Coda)',
        'what_is': "La perdita media attesa in tutte le giornate in cui la perdita del portafoglio supera la soglia critica del Value at Risk. È una misura di rischio 'coerente' (Artzner et al. 1999) che rispetta l'assioma della sub-additività.",
        'how_calc': '<b>CVaR<sub>&alpha;</sub></b> = &minus;E[ R<sub>p</sub> | R<sub>p</sub> &le; &minus;VaR<sub>&alpha;</sub> ] = [1 / (1 &minus; &alpha;)] &int;<sub>0</sub><sup>1&minus;&alpha;</sup> VaR<sub>u</sub> du',
        'why_useful': "Risolve il fallimento principale del VaR: quantifica 'quanto si perde in media quando le cose vanno davvero male', catturando la gravità effettiva dei crolli di borsa.",
        'argus_calc': 'Calcolato come media aritmetica dei rendimenti che si collocano al di sotto del quantile del VaR (approccio storico empirico non parametrico su 252+ sedute), affiancato dalle varianti analitiche gaussiane e Cornish-Fisher.',
        'how_to_read': '• 🟢 CVaR &lt; 2.50% (Code sottili, basso rischio di crash sistemico)<br>• 🟡 CVaR 2.50% - 4.50% (Rischio di coda nella norma per asset azionari)<br>• 🔴 CVaR &gt; 4.50% (Code grasse e grave vulnerabilità a cigni neri sistemici).',
        'limitations': 'Dipende fortemente dal numero di osservazioni nella coda estrema: su un campione ridotto di 252 giorni, il CVaR al 99% si basa sulla media di sole 2 o 3 osservazioni, rendendolo sensibile a singoli outlier storici.',
    },
    'sharpe_ratio': {
        'title': '🎯 Sharpe Ratio (Rendimento / Rischio Totale)',
        'what_is': "Indice che misura l'extra-rendimento generato per ciascuna unità di rischio totale (volatilità) assunto oltre il tasso privo di rischio.",
        'how_calc': '<b>Sharpe</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>p</sub>',
        'why_useful': 'Distinguere la reale abilità allocativa del gestore da rendimenti ottenuti assumendo una volatilità eccessiva e non sostenibile.',
        'argus_calc': 'Utilizza il tasso Risk-Free live armonizzato per valuta (BCE €STR per EUR, Fed ^IRX per USD) e annualizza i rendimenti a 252 giorni.',
        'how_to_read': '• 🟢 > 1.20 (Eccellente efficienza rischio/rendimento)<br>• 🟡 0.70 - 1.20 (Buono / Accettabile)<br>• 🔴 < 0.70 (Inefficiente, remunerazione insufficiente per il rischio corso).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'sortino_ratio': {
        'title': '🛡️ Sortino Ratio (Rendimento / Downside Risk)',
        'what_is': 'Variante dello Sharpe Ratio che penalizza unicamente la volatilità negativa di ribasso (Downside Deviation), ignorando la volatilità positiva.',
        'how_calc': '<b>Sortino</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>downside</sub> &nbsp;|&nbsp; <b>&sigma;<sub>downside</sub></b> = &radic;[ (1/N) &sum; min(0, R<sub>t</sub> &minus; R<sub>f</sub>)<sup>2</sup> &times; 252 ]',
        'why_useful': 'Valutare strategie asimmetriche e opzioni dove la volatilità positiva è desiderabile e solo le perdite costituiscono rischio.',
        'argus_calc': 'Calcolato estraendo i rendimenti inferiori al target MAR (Minimum Acceptable Return = Tasso Risk-Free live).',
        'how_to_read': '• 🟢 > 1.50 (Ottima asimmetria e protezione dai ribassi)<br>• 🟡 0.80 - 1.50 (Sufficiente)<br>• 🔴 < 0.80 (Elevata frequenza o entità di rendimenti negativi).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'max_drawdown': {
        'title': '📉 Massimo Drawdown Storico (Max Drawdown)',
        'what_is': 'La massima perdita percentuale registrata dal picco di valore più elevato fino al punto di minimo successivo.',
        'how_calc': "<b>MDD</b> = min<sub>t</sub> [ (V<sub>t</sub> &minus; HWM<sub>t</sub>) / HWM<sub>t</sub> ]<br><span style='font-size:11.5px; color:#8b949e;'>dove <b>HWM<sub>t</sub></b> = max<sub>s &le; t</sub> V<sub>s</sub> è il picco massimo storico progressivo (High-Water Mark)</span>",
        'why_useful': "Quantificare il peggior calo storico subito dal portafoglio e testare la resilienza psicologica e finanziaria dell'investitore.",
        'argus_calc': "Tracciato punto a punto sulla serie storica cumulata dell'equity value, registrando picco, valle e durata del recupero (Recovery Time).",
        'how_to_read': '• 🟢 < 12.0% (Capitale molto protetto e resiliente)<br>• 🟡 12.0% - 25.0% (Correzione fisiologica di mercato)<br>• 🔴 > 25.0% (Rischio di prolungata distruzione di valore).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'calmar_ratio': {
        'title': '⚖️ Calmar Ratio (CAGR / Max Drawdown)',
        'what_is': 'Rapporto tra il tasso di crescita annuo composto (CAGR) e il Massimo Drawdown storico subito.',
        'how_calc': '<b>Calmar</b> = CAGR / |Max Drawdown|',
        'why_useful': "Valutare se il rendimento annuo generato giustifica l'ampiezza della peggiore flessione storica sopportata.",
        'argus_calc': 'Calcolato dal rapporto tra il CAGR del portafoglio e il valore assoluto del massimo drawdown sulla finestra storica.',
        'how_to_read': '• 🟢 > 1.00 (Eccellente: il rendimento annuo supera la peggiore perdita)<br>• 🟡 0.50 - 1.00 (Equilibrato)<br>• 🔴 < 0.50 (Drawdown sproporzionato rispetto al rendimento generato).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'beta': {
        'title': '🏛️ Beta di Mercato (Market Sensitivity)',
        'what_is': "Misura della sensibilità del rendimento del portafoglio rispetto alle variazioni dell'indice di riferimento (rischio sistematico non diversificabile).",
        'how_calc': '<b>&beta;</b> = Cov(R<sub>p</sub>, R<sub>m</sub>) / Var(R<sub>m</sub>) = &rho;<sub>p,m</sub> &times; (&sigma;<sub>p</sub> / &sigma;<sub>m</sub>)',
        'why_useful': 'Stabilire se il portafoglio amplifica (&beta; > 1) o attenua (&beta; < 1) i movimenti del mercato complessivo.',
        'argus_calc': 'Regressione OLS dei rendimenti giornalieri del portafoglio contro il benchmark principale selezionato (SPY, QQQ, ACWI) su finestra mobile di 252 sedute.',
        'how_to_read': '• 🟢 &beta; &lt; 0.80 (Difensivo / Bassa sensibilità sistemica)<br>• 🟡 &beta; &asymp; 1.00 (In linea col mercato)<br>• 🔴 &beta; &gt; 1.20 (Aggressivo, amplifica fortemente i ribassi di mercato).',
        'limitations': 'Assume linearità costante: nei crash sistemici, le correlazioni tendono a convergere a 1 e il Beta effettivo aumenta repentinamente rispetto alla media storica.',
    },
    'alpha': {
        'title': '🏆 Alpha di Jensen (Extra-Rendimento Gestionale CAPM)',
        'what_is': "L'extra-rendimento netto generato dal portafoglio rispetto a quello atteso in base al modello CAPM per il livello di rischio sistematico assunto.",
        'how_calc': '<b>&alpha;</b> = R<sub>p</sub> &minus; [ R<sub>f</sub> + &beta; &times; (R<sub>m</sub> &minus; R<sub>f</sub>) ]',
        'why_useful': 'Isolare il valore aggiunto puro generato dalle scelte di stock picking e asset allocation del gestore al netto del mercato.',
        'argus_calc': 'Intercetta della regressione lineare tra i rendimenti in eccesso del portafoglio e del benchmark, calcolata con p-value di confidenza e tasso R<sub>f</sub> dinamico.',
        'how_to_read': '• 🟢 &alpha; &gt; +2.0% (Netta creazione di valore attivo)<br>• 🟡 0.0% &le; &alpha; &le; +2.0% (Lieve extra-performance)<br>• 🔴 &alpha; &lt; 0.0% (Distruzione di valore rispetto a una replica passiva).',
        'limitations': 'Dipende dalla validità del CAPM uni-fattoriale: se i mercati sono mossi da fattori multipli (Fama-French), quello che appare come Alpha può essere solo esposizione non dichiarata a fattori Value o Momentum.',
    },
    'ulcer_index': {
        'title': '📉 Ulcer Index & Martin Ratio',
        'what_is': 'Misura di stress e profondità dei cali che tiene conto sia della percentuale di drawdown che del numero di giorni necessari per recuperare il picco.',
        'how_calc': '<b>UI</b> = &radic;[ (1/N) &sum; DD<sub>i</sub><sup>2</sup> ] &nbsp;|&nbsp; <b>Martin</b> = (CAGR &minus; R<sub>f</sub>) / UI',
        'why_useful': "Misurare il logorio temporale dell'investitore durante le fasi negative prolungate del mercato.",
        'argus_calc': 'Calcolo quadratico continuo delle percentuali di drawdown su tutti i giorni di negoziazione.',
        'how_to_read': '• 🟢 UI < 5.0% (Crescita lineare, minimi drawdown)<br>• 🟡 5.0% - 12.0% (Volatilità fisiologica)<br>• 🔴 UI > 12.0% (Elevato stress temporale e drawdowns prolungati).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'omega_ratio': {
        'title': '⚖️ Omega Ratio (Distribuzione Asimmetrica)',
        'what_is': 'Rapporto tra la probabilità cumulata dei guadagni rispetto a una soglia di rendimento target e la probabilità cumulata delle perdite sotto tale soglia.',
        'how_calc': '<b>&Omega;(L)</b> = &int;<sub>L</sub><sup>&infin;</sup> (1 &minus; F(r)) dr &nbsp;/&nbsp; &int;<sub>&minus;&infin;</sub><sup>L</sup> F(r) dr',
        'why_useful': 'Catturare tutte le proprietà della distribuzione dei rendimenti (inclusi skewness e code grasse) senza assumere la normalità gaussiana.',
        'argus_calc': 'Integrazione numerica continua dei rendimenti storici ponderati rispetto al tasso risk-free live.',
        'how_to_read': '• 🟢 > 1.50 (Distribuzione asimmetrica nettamente a favore dei guadagni)<br>• 🟡 1.00 - 1.50 (Bilanciato)<br>• 🔴 < 1.00 (Prevalenza statistica di perdite).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'tracking_error': {
        'title': '🎯 Tracking Error & Information Ratio',
        'what_is': "La volatilità della differenza dei rendimenti tra il portafoglio e il benchmark (Tracking Error) e l'extra-rendimento per unità di rischio attivo (Information Ratio).",
        'how_calc': '<b>TE</b> = &radic;(Var(R<sub>p</sub> &minus; R<sub>b</sub>)) &times; &radic;252 &nbsp;|&nbsp; <b>IR</b> = (R<sub>p</sub> &minus; R<sub>b</sub>) / TE',
        'why_useful': "Valutare la coerenza della gestione rispetto al benchmark di riferimento e premiare l'abilità di generazione attiva di Alpha.",
        'argus_calc': 'Calcolato sulle serie temporali allineate dei rendimenti giornalieri di portafoglio e benchmark su 252 sedute.',
        'how_to_read': '• 🟢 IR > 0.70 (Gestione attiva di alto livello)<br>• 🟡 0.30 &le; IR &le; 0.70 (Buona efficienza)<br>• 🔴 IR < 0.30 o negativo (Rischio attivo non remunerato).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'diversification_ratio': {
        'title': '🌐 HRP Cluster Diversification Ratio (Gerarchia di Rischio)',
        'what_is': "Rapporto tra la media ponderata delle volatilità dei singoli componenti e la volatilità complessiva del portafoglio allocato secondo l'algoritmo Hierarchical Risk Parity.",
        'how_calc': '<b>DR<sub>HRP</sub></b> = (&sum; w<sub>i</sub> &times; &sigma;<sub>i</sub>) / &radic;(<b>w</b><sub>HRP</sub><sup>T</sup> &Sigma; <b>w</b><sub>HRP</sub>)',
        'why_useful': "Quantificare il reale beneficio della diversificazione strutturale gerarchica evitando l'instabilità numerica dell'inversione della matrice di Markowitz.",
        'argus_calc': 'Calcolato con matrice di covarianza de-noised Ledoit-Wolf e pesi ottimali ricavati da tree clustering, quasi-diagonalization e recursive bisection.',
        'how_to_read': '• 🟢 &gt; 1.45 (Ottima diversificazione istituzionale)<br>• 🟡 1.20 - 1.45 (Diversificazione moderata)<br>• 🔴 &lt; 1.20 (Scarsa diversificazione, elevato rischio di concentrazione).',
        'limitations': "In mercati guidati da bolle speculative concentrate su singoli settori dominanti, l'approccio per parità di rischio può sottopesare i titoli più performanti.",
    },
    'days_to_liquidate': {
        'title': '⚡ Days-to-Liquidate (Almgren-Chriss Liquidity Horizon)',
        'what_is': 'Il numero stimato di giorni lavorativi necessari per liquidare le posizioni senza eccedere il 15% del volume medio giornaliero (ADV).',
        'how_calc': '<b>DTL</b> = Quantità Netta / (ADV<sub>30g</sub> &times; 0.15)',
        'why_useful': 'Evitare trappole di illiquidità, shock da market impact e disallineamenti di prezzo in caso di liquidazione forzata o ribilanciamento rapido.',
        'argus_calc': 'Pondera ciascun asset sul volume medio a 30 sedute ricavato dai flussi di mercato e applica il modello di impatto Almgren-Chriss.',
        'how_to_read': '• 🟢 &le; 1.0 gg (Smobilizzo immediato, asset ultra-liquido)<br>• 🟡 1.0 - 3.0 gg (Liquidità moderata)<br>• 🔴 > 3.0 gg (Posizione illiquida, elevato rischio di market impact).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'chandelier_exit': {
        'title': '🛡️ Chandelier Exit (ATR Trailing Stop-Loss)',
        'what_is': 'Algoritmo di stop-loss dinamico agganciato al picco massimo recente, tarato sulla volatilità effettiva a 14 periodi (Average True Range).',
        'how_calc': '<b>Stop</b> = Max(High<sub>22g</sub>) &minus; 3.0 &times; ATR<sub>14</sub>',
        'why_useful': 'Proteggere i guadagni accumulati lasciando correre i profitti durante i trend rialzisti ed evitando uscite premature per rumore di mercato.',
        'argus_calc': "Calcola l'ATR a 14 sedute sulle barre High-Low-Close di ciascun titolo e sottrae 3 volte tale valore dal massimo a 22 giorni lavorativi.",
        'how_to_read': '• 🟢 Prezzo > Stop (Trend intatto, posizione regolare)<br>• 🟡 Distanza < 4% (Vicinanza alla soglia di allerta)<br>• 🔴 Prezzo &le; Stop (Trigger di uscita/copertura scattato).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'isolation_forest': {
        'title': '🕵️\u200d♂️ Machine Learning Isolation Forest (Rilevazione Anomalie)',
        'what_is': 'Algoritmo di Machine Learning non supervisionato per identificare giornate storiche atipiche con rotture di correlazione o shock sistemici.',
        'how_calc': '<b>Anomalia (4D)</b>: f(Rendimento, &sigma;<sub>20d</sub>, &rho;<sub>media</sub>, DD<sub>t</sub>) &nbsp;&rarr;&nbsp; Score &lt; 0',
        'why_useful': 'Rilevare cluster di anomalie di mercato prima che si trasformino in perdite permanenti di capitale.',
        'argus_calc': 'Pipeline integrata in scikit-learn con parametro di contaminazione del 5% su tutta la cronologia disponibile.',
        'how_to_read': '• 🔴 ANOMALIA (Punteggio negativo marcato, dinamica anomala)<br>• 🟢 Normale (Fluttuazione coerente con la serie storica).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'kelly_criterion': {
        'title': '🎯 Kelly Criterion (Dimensionamento Ottimale del Capitale)',
        'what_is': 'Formula per determinare la percentuale teorica ottimale di capitale da allocare su una posizione per massimizzare la crescita geometrica a lungo termine.',
        'how_calc': '<b>f*</b> = (p &times; b &minus; q) / b &nbsp;|&nbsp; <b>f*</b> = (&mu; &minus; R<sub>f</sub>) / &sigma;<sup>2</sup>',
        'why_useful': "Prevenire la rovina statistica del capitale (Gambler's Ruin) ed evitare sia il sotto-investimento che l'over-betting.",
        'argus_calc': 'Calcolato con frazionamento prudenziale (Half-Kelly al 50% o Quarter-Kelly al 25%) integrato con il tasso risk-free live.',
        'how_to_read': '• 🟢 f* applicato al 25%-50% (Allocazione robusta ed equilibrata)<br>• 🔴 Full Kelly al 100% (Sconsigliato: eccessiva volatilità del portafoglio).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'quarter_kelly': {
        'title': '🛡️ Quarter-Kelly Allocation (Dimensionamento Ultra-Prudente)',
        'what_is': 'Frazionamento al 25% del criterio di Kelly teorico, progettato per ridurre del 75% la volatilità mantenendo oltre il 70% del tasso di crescita massimo.',
        'how_calc': '<b>f<sub>Quarter</sub></b> = 0.25 &times; f* = 0.25 &times; [ (&mu; &minus; R<sub>f</sub>) / &sigma;<sup>2</sup> ]',
        'why_useful': 'Eliminare il rischio di drawdown severi dovuti a errori di stima nei parametri attesi (estimation risk).',
        'argus_calc': 'Applicato al vettore dei pesi ottimali con cap su volatilità e downside risk.',
        'how_to_read': '• 🟢 Consigliato per portafogli reali con vincoli stringenti di capitale e avversione alle perdite.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'half_kelly': {
        'title': '🎯 Half-Kelly Allocation (Dimensionamento Bilanciato)',
        'what_is': 'Frazionamento al 50% del criterio di Kelly teorico, standard di riferimento per hedge fund quantitativi e commodity trading advisors.',
        'how_calc': '<b>f<sub>Half</sub></b> = 0.50 &times; f* = 0.50 &times; [ (&mu; &minus; R<sub>f</sub>) / &sigma;<sup>2</sup> ]',
        'why_useful': 'Garantire il 75% della velocità di crescita teorica di lungo periodo dimezzando i drawdown massimi sopportati.',
        'argus_calc': 'Ricalcolato a ogni ribilanciamento periodico sulla matrice di covarianza de-noised.',
        'how_to_read': '• 🟢 Profilo ottimale per investitori che cercano crescita rapida senza esporsi a code estreme.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'full_kelly': {
        'title': '🔥 Full Kelly Allocation (Massima Leva Teorica)',
        'what_is': 'Allocazione teorica pura che massimizza il logaritmo atteso della ricchezza finale assumendo parametri di mercato noti con certezza assoluta.',
        'how_calc': '<b>f<sub>Full</sub></b> = (&mu; &minus; R<sub>f</sub>) / &sigma;<sup>2</sup>',
        'why_useful': 'Benchmark matematico teorico del limite superiore di leva razionale oltre il quale il rendimento geometrico crolla.',
        'argus_calc': 'Calcolato a scopo analitico comparativo; sconsigliato in produzione per via della frequenza di drawdown > 50%.',
        'how_to_read': '• 🔴 Rischio elevato di volatilità estrema ed erosione del capitale reale in presenza di errori di stima.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'altman_z_score': {
        'title': '🏛️ Altman Z-Score (Solvibilità e Rischio Default)',
        'what_is': 'Modello econometrico multivariato a 5 indici di bilancio per prevedere la probabilità di insolvenza o dissesto finanziario aziendale a 2 anni.',
        'how_calc': '<b>Z</b> = 1.2 &times; X<sub>1</sub> + 1.4 &times; X<sub>2</sub> + 3.3 &times; X<sub>3</sub> + 0.6 &times; X<sub>4</sub> + 0.999 &times; X<sub>5</sub>',
        'why_useful': 'Verificare la solidità fondamentale e proteggersi da fallimenti o default societari nei titoli detenuti.',
        'argus_calc': 'Estrae automaticamente le voci di bilancio annuali certificate (SEC 10-K / bilanci societari) calcolando i 5 ratios finanziari.',
        'how_to_read': '• 🟢 Z > 2.99 (Zona Sicura: azienda solida e solvente)<br>• 🟡 1.81 &le; Z &le; 2.99 (Zona Grigia: rischio moderato)<br>• 🔴 Z < 1.81 (Zona di Distress: alto rischio di insolvenza).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'beneish_m_score': {
        'title': '🔍 Beneish M-Score (Forensic Accounting & Manipolazione)',
        'what_is': 'Modello statistico probabilistico a 8 indici di bilancio per rilevare anomalie contabili o pratiche aggressive di manipolazione degli utili.',
        'how_calc': '<b>M</b> = &minus;4.84 + 0.92&times;DSRI + 0.528&times;GMI + 0.404&times;AQI + 0.892&times;SGI + 0.115&times;DEPI &minus; 0.172&times;SGAI + 4.037&times;TATA + 0.0327&times;LVGI',
        'why_useful': 'Individuare tempestivamente red flags contabili prima che si traducano in scandali finanziari o crolli delle quotazioni.',
        'argus_calc': 'Confronta le voci di conto economico e stato patrimoniale degli ultimi due esercizi contabili calcolando gli 8 indicatori standard.',
        'how_to_read': '• 🟢 M < -2.22 (Bassa probabilità di manipolazione, bilancio affidabile)<br>• 🔴 M > -2.22 (Alta probabilità di anomalie o abbellimenti contabili).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'sloan_accrual': {
        'title': '📊 Sloan Accrual Ratio (Qualità degli Utili)',
        'what_is': 'Indicatore di qualità contabile che misura la percentuale di utile derivante da mere scritture di competenza rispetto ai flussi di cassa operativi reali.',
        'how_calc': '<b>Accrual Ratio</b> = [ Net Income &minus; (CFO + CFI) ] / Total Assets',
        'why_useful': 'Evidenziare se gli utili annunciati sono supportati da denaro effettivo incassato sul conto corrente aziendale.',
        'argus_calc': "Estrae Net Income, Cash Flow Operativo (CFO) e Totale Attivo dall'ultimo rendiconto finanziario societario.",
        'how_to_read': '• 🟢 |Accrual| < 5.0% (Qualità eccellente degli utili)<br>• 🟡 5.0% - 10.0% (Livello intermedio)<br>• 🔴 |Accrual| > 10.0% (Bassa qualità, rischio revisioni al ribasso).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'wacc': {
        'title': '💼 WACC & DCF Fair Value (Costo del Capitale e Valutazione Intrinseca)',
        'what_is': 'Il costo medio ponderato del capitale aziendale (WACC) e il valore intrinseco per azione calcolato attualizzando i flussi di cassa futuri (DCF).',
        'how_calc': '<b>WACC</b> = (E/V)&times;K<sub>e</sub> + (D/V)&times;K<sub>d</sub>&times;(1 &minus; t) &nbsp;|&nbsp; <b>Fair Value</b> = [ &sum; FCFF<sub>t</sub> / (1 + WACC)<sup>t</sup> + TV ] / Shares',
        'why_useful': 'Fissare il prezzo equo fondamentale di un titolo per determinare se quota a sconto (sottovalutato) o a premio (sopravvalutato).',
        'argus_calc': 'Simulazione DCF Monte Carlo con 1,000 iterazioni stocastiche su tassi di crescita, WACC calcolato con CAPM e tasso risk-free live.',
        'how_to_read': '• 🟢 Prezzo < Fair Value (Margine di sicurezza favorevole, sottovalutato)<br>• 🟡 Prezzo &asymp; Fair Value (Equamente valutato)<br>• 🔴 Prezzo > Fair Value (Sopravvalutato rispetto ai fondamentali).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'piotroski_f_score': {
        'title': '⭐ Piotroski F-Score (Solidità e Momentum Fondamentale)',
        'what_is': 'Punteggio discreto da 0 a 9 basato su 9 criteri contabili suddivisi in Redditività, Leva/Liquidità ed Efficienza Operativa.',
        'how_calc': '<b>F-Score</b> = &sum; (9 criteri binari 0 o 1 su ROA, CFO, &Delta;Leva, &Delta;Margini, &Delta;Rotazione, ecc.)',
        'why_useful': 'Selezionare titoli value con solidi fondamentali ed eliminare società fragili a rischio declino economico.',
        'argus_calc': 'Analisi automatizzata punto per punto sui bilanci societari storici ufficiali.',
        'how_to_read': '• 🟢 8 - 9 (Società finanziariamente eccellente e in espansione)<br>• 🟡 5 - 7 (Solidità moderata / nella media)<br>• 🔴 0 - 4 (Struttura finanziaria fragile o deterioramento operativo).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'return_on_equity': {
        'title': '📈 Return on Equity (ROE / Redditività del Capitale Proprio)',
        'what_is': "Rapporto tra l'utile netto d'esercizio e il patrimonio netto contabile della società (Book Value of Equity).",
        'how_calc': '<b>ROE</b> = (Utile Netto / Patrimonio Netto Contabile) &times; 100',
        'why_useful': "Misurare l'efficienza con cui il management genera profitti impiegando i capitali investiti dai soci/azionisti.",
        'argus_calc': 'Estrapolato dai bilanci societari certificati con scomposizione DuPont a 3 o 5 fattori.',
        'how_to_read': '• 🟢 > 15.0% (Redditività solida ed elevata creazione di valore)<br>• 🟡 8.0% - 15.0% (In linea con la media di mercato)<br>• 🔴 < 8.0% o negativo (Scarsa remunerazione del capitale proprio).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'free_cash_flow': {
        'title': '💧 Free Cash Flow (FCF / Flusso di Cassa Libero)',
        'what_is': 'La liquidità effettiva generata dalla gestione operativa aziendale al netto delle spese per investimenti in capitale fisso (CapEx).',
        'how_calc': '<b>FCF</b> = Flusso di Cassa Operativo (CFO) &minus; Spese per Investimenti (CapEx)',
        'why_useful': 'Rappresenta il denaro reale disponibile per remunerare gli azionisti (dividendi, buyback) o per ridurre i debiti aziendali.',
        'argus_calc': 'Estrae dal rendiconto finanziario societario il flusso operativo e gli acquisti di immobilizzazioni materiali/immateriali.',
        'how_to_read': '• 🟢 FCF crescente e ampiamente positivo (Generazione di cassa robusta)<br>• 🟡 Stabile o moderatamente positivo<br>• 🔴 FCF negativo continuativo (Brucia cassa, possibile necessità di aumenti di capitale o debito).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'wealth_health_score': {
        'title': '🛡️ Wealth Health Score (Indice di Salute Patrimoniale)',
        'what_is': 'Punteggio sintetico multidimensionale da 0 a 100 che valuta solidità, solvibilità, diversificazione, cuscinetto di cassa e sostenibilità del debito.',
        'how_calc': '<b>Score</b> = 40% Cuscinetto Cassa (Runway) + 25% Diversificazione Asset + 20% Copertura Previdenziale + 15% Sostenibilità Debito (Debt-to-Asset)',
        'why_useful': 'Fornire una diagnosi istantanea e completa della solidità economico-patrimoniale personale o del Family Office.',
        'argus_calc': 'Aggrega saldi bancari, asset class attive, mesi di autonomia, LTV mutui e coperture pensionistiche.',
        'how_to_read': '• 🟢 80 - 100 (Salute patrimoniale eccellente, resiliente a shock sistemici)<br>• 🟡 60 - 79 (Salute discreta con margini di miglioramento su liquidità o previdenza)<br>• 🔴 < 60 (Criticità strutturale: indebitamento eccessivo, cassa insufficiente o concentrazione).',
        'limitations': "La stima assume condizioni di mercato ordinarie con book di negoziazione capiente. In presenza di gap di apertura, news macro improvvise o bassa liquidità, l'esecuzione reale può subire divergenze marcate.",
    },
    'net_worth': {
        'title': '🏛️ Patrimonio Netto Consolidato (Consolidated Net Worth)',
        'what_is': 'Il valore economico complessivo di tutte le attività possedute al netto di tutte le passività finanziarie e debiti residui secondo standard contabili CFP/IFRS.',
        'how_calc': '<b>Net Worth</b> = Totale Attivo &minus; Totale Passività = (Cassa + Investimenti + Caveau + Immobili + Previdenza) &minus; Passività',
        'why_useful': 'Rappresenta la metrica fondamentale della ricchezza reale al di là dei flussi transitori di reddito: è la base di ogni piano di indipendenza finanziaria.',
        'argus_calc': 'Consolidamento multi-conto continuo in EUR con conversione cambi BCE live, rivalutazione mark-to-market degli asset e ammortamento continuo dei debiti residui.',
        'how_to_read': "• 🟢 Trend crescente costante superiore all'inflazione<br>• 🟡 Stabile durante fasi di riallocazione o investimenti primari<br>• 🔴 Trend decrescente prolungato (Overspending o drawdown prolungato degli asset).",
        'limitations': 'Include stime di mercato su beni non liquidi (immobili, collezionismo) che possono differire dal prezzo effettivo di rapido realizzo in caso di vendita forzata.',
    },
    'liquid_assets': {
        'title': '💧 Patrimonio Netto Liquido (Liquid Net Worth)',
        'what_is': 'La porzione di ricchezza netta convertibile in contanti entro 5-10 giorni lavorativi senza subire sconti sul valore di mercato (esclude prima casa, immobili fisici e collezionismo).',
        'how_calc': '<b>Liquid Net Worth</b> = (Liquidità + Strumenti Finanziari Quotati) &minus; Debiti a Breve Termine',
        'why_useful': 'Valutare la reale capacità di risposta a opportunità di investimento improvvise o a shock gravi senza dover liquidare la propria abitazione o asset strategici.',
        'argus_calc': 'Somma saldi bancari, ETF monetari, obbligazioni e azioni liquide quotate nel modulo investimenti, detraendo i debiti esigibili entro 12 mesi.',
        'how_to_read': "• 🟢 &gt; 35% del Patrimonio Netto Totale (Elevata flessibilità e reattività strategica)<br>• 🟡 15% - 35% (Equilibrio standard tra rendimento e liquidità)<br>• 🔴 &lt; 15% (Eccessiva immobilizzazione: rischio di 'wealth rich but cash poor').",
        'limitations': 'In fasi di prolungato bear market, il valore dei titoli quotati si comprime riducendo il patrimonio liquido proprio quando la liquidità diventa più preziosa.',
    },
    'financial_investments': {
        'title': '📈 Investimenti Finanziari (Financial Assets Portfolio)',
        'what_is': 'Il controvalore di mercato di tutti gli strumenti finanziari quotati e liquidi (Azioni, ETF, Obbligazioni, Fondi, Crypto, Derivati).',
        'how_calc': '<b>Investimenti</b> = &sum; (Quantità<sub>i</sub> &times; Prezzo di Mercato<sub>i</sub> &times; FX<sub>i</sub>)',
        'why_useful': "Costruire crescita del capitale a lungo termine, generare flussi di reddito passivo e battere l'inflazione.",
        'argus_calc': 'Sincronizzazione in tempo reale con il Quantitative Risk Engine per calcolo VaR, Sharpe, frontiera efficiente e asset allocation.',
        'how_to_read': '• 🟢 Allocazione coerente con orizzonte temporale e profilo di tolleranza al rischio<br>• 🟡 Disallineamento moderato rispetto ai pesi target<br>• 🔴 Concentrazione anomala su singolo emittente (>15%) o asset class rischiosa.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'physical_assets': {
        'title': '⌚ Caveau & Asset Fisici di Pregio (Luxury & Physical Assets)',
        'what_is': "Beni tangibili da collezione o riserva di valore (orologi di lusso da collezione, oro fisico/bullion, metalli preziosi, opere d'arte).",
        'how_calc': '<b>Valore Caveau</b> = &sum; (Fair Market Value da perizia / Chrono24 / quotazione spot oro fisico)',
        'why_useful': 'Diversificazione non correlata ai mercati finanziari tradizionali e conservazione patrimoniale tangibile intergenerazionale.',
        'argus_calc': 'Tracciamento per singolo asset con storico di rivalutazione, stato condizioni e seriale certificato.',
        'how_to_read': '• 🟢 5% - 15% del Patrimonio Netto (Quota equilibrata per asset tangibili)<br>• 🟡 15% - 25% (Esposizione marcata)<br>• 🔴 > 25% (Illiquidità elevata e costi di custodia gravosi).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'real_estate_equity': {
        'title': '🏡 Immobili & Net Equity Immobiliare (Real Estate Net Equity)',
        'what_is': 'Il valore netto del patrimonio immobiliare detenuto, al netto dei debiti residui per mutui ipotecari gravanti.',
        'how_calc': '<b>Net Equity Immobiliare</b> = Valore di Mercato Immobili &minus; Debito Residuo Mutui',
        'why_useful': 'Misurare la reale ricchezza immobiliare netta libera da gravami ipotecari bancari.',
        'argus_calc': "Calcolo automatico dell'ammortamento mutuo e stima del valore degli immobili registrati.",
        'how_to_read': '• 🟢 LTV < 50% (Patrimonio immobiliare solido e poco indebitato)<br>• 🟡 LTV 50% - 75% (Leva fisiologica prima casa)<br>• 🔴 LTV > 80% (Elevata vulnerabilità a rialzo tassi o discesa prezzi immobiliari).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'pension_total': {
        'title': '🛡️ Previdenza & Fondi Pensione (Pension & Retirement Planning)',
        'what_is': 'Il montante accumulato nei pilastri di previdenza complementare (Fondi Negoziali, Aperti, PIP e TFR accantonato).',
        'how_calc': '<b>Previdenza</b> = &sum; Posizioni Fondi Pensione (Quote &times; NAV) + Contributi Deducibili Annui &minus; Ritenute',
        'why_useful': 'Garantire un adeguato tasso di sostituzione del reddito al pensionamento con deducibilità fiscale fino a € 5.164,57 annui (TUIR Art. 10).',
        'argus_calc': 'Simulazione Monte Carlo integrata con proiezioni di longevità, inflazione e rendimenti netti delle linee di investimento.',
        'how_to_read': '• 🟢 Tasso di sostituzione stimato > 75% (Pensionamento sereno)<br>• 🟡 60% - 75% (Copertura discreta con modesto gap da colmare)<br>• 🔴 < 60% (Forte gap pensionistico: incrementare i versamenti annui).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'total_liabilities': {
        'title': '📉 Passività & Debiti Totali (Total Liabilities)',
        'what_is': "L'ammontare complessivo di tutti i debiti finanziari in essere (mutui ipotecari, prestiti personali, carte revolving e finanziamenti auto).",
        'how_calc': '<b>Passività Totali</b> = Debito Residuo Mutui + Capitale Residuo Finanziamenti + Saldo Passivo Carte',
        'why_useful': 'Monitorare il grado di indebitamento per prevenire situazioni di stress finanziario e ottimizzare il costo del debito.',
        'argus_calc': 'Tracciamento continuo delle rate mensili con ripartizione quota capitale / interessi e calcolo DSTI.',
        'how_to_read': '• 🟢 DSTI < 25% del reddito mensile (Debito pienamente sostenibile)<br>• 🟡 25% - 35% (Soglia bancaria ordinaria)<br>• 🔴 > 35% (Sovraindebitamento a rischio insolvenza).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'debt_to_asset': {
        'title': '⚖️ Rapporto Debito / Patrimonio (Debt-to-Asset Ratio)',
        'what_is': 'Percentuale del totale attivo patrimoniale lordo finanziata tramite debito.',
        'how_calc': '<b>Debt-to-Asset</b> = (Totale Passività / Totale Attivo Lordo) &times; 100',
        'why_useful': "Valutare la leva finanziaria complessiva del patrimonio e la vulnerabilità a shock di mercato o dei tassi d'interesse.",
        'argus_calc': "Rapporto tra il totale debiti registrati e l'attivo patrimoniale consolidato lordo.",
        'how_to_read': '• 🟢 < 20% (Struttura patrimoniale solida e molto conservativa)<br>• 🟡 20% - 40% (Leva fisiologica)<br>• 🔴 > 50% (Elevata dipendenza dal debito, rischio di vulnerabilità).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'savings_rate': {
        'title': '💰 Tasso di Risparmio Personale (Savings Rate)',
        'what_is': 'La quota percentuale delle entrate nette mensili che viene accantonata o investita dopo aver coperto tutte le spese.',
        'how_calc': '<b>Savings Rate</b> = [ (Entrate Nette &minus; Uscite Totali) / Entrate Nette ] &times; 100',
        'why_useful': 'È il motore fondamentale della crescita patrimoniale: determina direttamente la velocità di accumulo e il tempo al traguardo FIRE.',
        'argus_calc': 'Estratto dal rendiconto del Cash Flow depurato da giroconti interni e trasferimenti tra conti propri.',
        'how_to_read': '• 🟢 > 25% (Accumulazione rapida e disciplina eccellente)<br>• 🟡 15% - 25% (Risparmio sano coerente con la regola 50/30/20)<br>• 🔴 < 10% (Capacità di accumulo fragile, vulnerabile a imprevisti).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'runway_months': {
        'title': '⏳ Runway di Emergenza (Mesi di Autonomia Finanziaria)',
        'what_is': 'Il numero esatto di mesi durante i quali è possibile coprire interamente il tenore di vita e le spese obbligatorie a entrate azzerate, attingendo solo alla cassa disponibile.',
        'how_calc': '<b>Runway</b> = Liquidità Prontamente Disponibile / Media Spese Mensili (Burn Rate)',
        'why_useful': 'Garantire tranquillità economica ed evitare tassativamente la vendita forzata di asset finanziari volatili durante fasi di ribasso di mercato.',
        'argus_calc': 'Rapporto tra la cassa disponibile e il burn rate mensile medio registrato negli ultimi 6 mesi depurato da spese straordinarie.',
        'how_to_read': '• 🟢 &gt; 6 mesi (Elevata serenità e indipendenza di breve termine)<br>• 🟡 3 - 6 mesi (Autonomia standard adeguata)<br>• 🔴 &lt; 3 mesi (Pericolo di liquidità: ricostituire prioritariamente il fondo cassa).',
        'limitations': 'Un runway eccessivo (> 18-24 mesi) fermo su conti infruttiferi comporta un severo costo opportunità (cash drag) ed erosione da inflazione.',
    },
    'budget_50_30_20': {
        'title': '📊 Regola di Budgeting 50 / 30 / 20 (Needs, Wants, Savings)',
        'what_is': 'Modello di allocazione delle entrate in 50% Spese Necessarie (Needs), 30% Desideri/Svago (Wants) e 20% Risparmi/Investimenti (Savings).',
        'how_calc': '<b>Needs:</b> Spese fisse, casa, bollette &le; 50% &nbsp;|&nbsp; <b>Wants:</b> Svago, viaggi &le; 30% &nbsp;|&nbsp; <b>Savings:</b> Investimenti &ge; 20%',
        'why_useful': 'Mantenere equilibrio tra benessere nel presente e sicurezza patrimoniale futura.',
        'argus_calc': 'Categorizzazione automatica di tutte le uscite registrate tramite classificazione NLP delle transazioni.',
        'how_to_read': '• 🟢 Needs &le; 50%, Wants &le; 30%, Savings &ge; 20% (Budget ottimale)<br>• 🟡 Needs 50%-60% (Budget sotto pressione ma gestibile)<br>• 🔴 Needs > 60% o Savings < 10% (Struttura di spesa rigida a rischio insolvenza).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'totale_attivo': {
        'title': '🏛️ Totale Attivo Patrimoniale (Total Assets)',
        'what_is': "L'ammontare lordo consolidato di tutte le risorse economiche, finanziarie, tangibili e immobiliari di proprietà.",
        'how_calc': '<b>Totale Attivo</b> = Attivo Corrente (Cassa/Depositi) + Investimenti Finanziari + Attivo Immobiliare + Beni Tangibili/Caveau + Previdenza',
        'why_useful': 'Misurare la scala complessiva della ricchezza lorda controllata prima della detrazione dei debiti bancari.',
        'argus_calc': 'Somma algebrica delle posizioni attive rivalutate in tempo reale in base ai prezzi di mercato e ai cambi BCE.',
        'how_to_read': "• 🟢 Trend in espansione sostenuta da risparmio e rendimenti reali<br>• 🟡 Stabilità con buona diversificazione<br>• 🔴 Erosione dell'attivo dovuta a perdite o disinvestimenti per consumi.",
        'limitations': "L'accuratezza dipende dall'aggiornamento puntuale e completo di tutti i conti e debiti. Non contabilizza passività potenziali o contingenti non ancora formalizzate in impegni contrattuali certi.",
    },
    'pareggio_bilancio': {
        'title': '⚖️ Pareggio Contabile di Bilancio (Balance Sheet Identity)',
        'what_is': 'Principio contabile fondamentale di quadratura secondo cui il Totale Attivo deve equivalere perfettamente alla somma di Passività e Patrimonio Netto.',
        'how_calc': '<b>Attivo = Passività + Patrimonio Netto</b> &nbsp;&rarr;&nbsp; <b>Delta Quadratura</b> = Attivo &minus; (Passività + Net Worth) = € 0,00',
        'why_useful': "Certificare l'integrità matematica e contabile dei prospetti finanziari, escludendo doppi conteggi o voci orfane.",
        'argus_calc': 'Verifica continua automatizzata della riconciliazione tra inventario patrimoniale, debiti residui e patrimonio netto calcolato.',
        'how_to_read': '• 🟢 Perfetto (€ 0,00 di scostamento, quadratura contabile certificata al 100%)<br>• 🔴 Disallineamento (Presenza di asimmetrie o dati non riconciliati nel database).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'solvency_ratio': {
        'title': '🛡️ Indice di Solvibilità Patrimoniale (Solvency Ratio)',
        'what_is': 'Rapporto tra il Patrimonio Netto e il Totale Attivo Lordo: misura la quota di patrimonio non vincolata a debiti esterni.',
        'how_calc': '<b>Solvency Ratio</b> = (Patrimonio Netto / Totale Attivo Lordo) &times; 100',
        'why_useful': 'Quantificare il grado di autosufficienza e protezione patrimoniale in caso di svalutazione improvvisa degli attivi.',
        'argus_calc': "Rapporto tra il Net Worth consolidato e il totale dell'attivo patrimoniale lordo di bilancio.",
        'how_to_read': "• 🟢 > 80% (Solvibilità eccezionale, patrimonio quasi interamente di proprietà netta)<br>• 🟡 60% - 80% (Solvibilità buona / fisiologica con mutui in corso)<br>• 🔴 < 50% (Vulnerabilità patrimoniale: oltre metà dell'attivo è di proprietà dei creditori).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'dsti_ratio': {
        'title': '💳 Debt Service to Income (DSTI / Tasso di Indebitamento)',
        'what_is': 'La quota percentuale del reddito mensile lordo o netto assorbita dal pagamento delle rate dei debiti finanziari.',
        'how_calc': '<b>DSTI</b> = (Totale Rate Mensili Debiti & Mutui / Reddito Mensile Disponibile) &times; 100',
        'why_useful': 'Valutare la sostenibilità corrente del debito e la capacità di ottenere nuovi finanziamenti bancari senza soffocare la cassa.',
        'argus_calc': 'Sommatoria delle rate di mutui e prestiti rapportata alle entrate ricorrenti registrate a conto economico.',
        'how_to_read': '• 🟢 < 20% (Debito leggero e perfettamente sostenibile)<br>• 🟡 20% - 35% (Soglia standard di tolleranza bancaria)<br>• 🔴 > 35% (Rischio elevato di tensione di liquidità in caso di imprevisti).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'invested_assets_ratio': {
        'title': '🚀 Quota Attivi Redditizi (Invested Assets Ratio)',
        'what_is': 'La percentuale del patrimonio complessivo allocata in asset produttivi (azioni, obbligazioni, fondi, immobili a reddito) che generano rendimento attivo o dividendi.',
        'how_calc': '<b>Invested Assets Ratio</b> = (Attivi da Investimento / Totale Attivo Lordo) &times; 100',
        'why_useful': 'Evidenziare quanta parte della ricchezza lavora per produrre nuova ricchezza rispetto a beni di mero godimento o cassa improduttiva.',
        'argus_calc': "Estrae il controvalore degli strumenti di mercato e investimenti e lo rapporta all'attivo consolidato.",
        'how_to_read': "• 🟢 > 50% (Patrimonio produttivo ben posizionato per battere l'inflazione)<br>• 🟡 30% - 50% (Livello intermedio)<br>• 🔴 < 30% (Eccesso di capitale fermo su cassa o beni d'uso non redditizi).",
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'personal_savings_rate': {
        'title': '💰 Personal Savings Rate (Conto Economico Personale)',
        'what_is': "L'incidenza percentuale del risparmio netto generato rispetto al totale dei ricavi e compensi percepiti nel periodo.",
        'how_calc': '<b>Personal Savings Rate</b> = (Risparmio Netto / Totale Entrate Periodo) &times; 100',
        'why_useful': "Misurare la redditività operativa della gestione personale o familiare analizzata come un'impresa.",
        'argus_calc': "Rapporto tra l'utile operativo netto del Conto Economico Personale e il totale delle entrate registrate.",
        'how_to_read': '• 🟢 > 30% (Efficienza e capacità di accumulo di alto livello)<br>• 🟡 15% - 30% (Struttura di spesa equilibrata)<br>• 🔴 < 15% o negativo (Marginalità debole, rischio disaccumulo).',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'cash_variation_pbs': {
        'title': '💧 Variazione Netta di Cassa (Cash Flow Statement)',
        'what_is': 'La differenza netta complessiva tra entrate incassate e uscite monetarie pagate nel corso del periodo di riferimento.',
        'how_calc': '<b>&Delta; Cassa</b> = Totale Incassi &minus; Totale Pagamenti = Saldo Cassa Finale &minus; Saldo Cassa Iniziale',
        'why_useful': 'Verificare se la gestione monetaria ha generato liquidità aggiuntiva o se si è fatto ricorso alle riserve pregresse.',
        'argus_calc': 'Riconciliazione bancaria puntuale dei flussi di cassa operativi, finanziari e di investimento registrati a database.',
        'how_to_read': '• 🟢 Variazione Positiva (Autofinanziamento e accumulo di cassa liquida)<br>• 🟡 Variazione Neutra (&asymp; € 0, pareggio dei flussi monetari)<br>• 🔴 Variazione Negativa (Assorbimento di cassa: verificare se dovuto a investimenti o spesa corrente).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'total_inflow': {
        'title': '💶 Totale Entrate e Compensi (Total Inflows)',
        'what_is': 'La sommatoria di tutti i proventi percepiti nel periodo (stipendi, compensi professionali, dividendi, cedole, canoni di locazione, rimborsi).',
        'how_calc': '<b>Totale Entrate</b> = &sum; Flussi Positivi Accreditati (al netto dei giroconti interni)',
        'why_useful': 'Definire la capacità complessiva di generazione di cassa primaria a supporto delle spese e degli investimenti.',
        'argus_calc': 'Elaborato dal Cash Flow Engine escludendo tassativamente movimenti interni e scambi tra conti dello stesso titolare.',
        'how_to_read': '• 🟢 Flussi stabili o in crescita con molteplici fonti di reddito diversificate<br>• 🟡 Flusso stabile monoreddito<br>• 🔴 Flussi irregolari o in flessione rispetto ai periodi precedenti.',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'total_outflow': {
        'title': '💸 Spese di Vita & Costi Totali (Total Outflows)',
        'what_is': 'La sommatoria di tutte le uscite finanziarie sostenute nel periodo per necessità primarie, svago, imposte e rate di debito.',
        'how_calc': '<b>Totale Uscite</b> = Spese Fisse + Spese Variabili + Imposte + Oneri Finanziari',
        'why_useful': 'Quantificare il tenore di vita effettivo per determinare il fabbisogno di liquidità e calibrare il fondo di emergenza.',
        'argus_calc': 'Aggregazione continua delle transazioni addebitate sui conti correnti e carte di credito collegate.',
        'how_to_read': '• 🟢 Uscite perfettamente contenute entro il budget prefissato (&le; 75% entrate)<br>• 🟡 Uscite vicine al limite di pareggio<br>• 🔴 Uscite superiori alle entrate (Deficit operativo con erosione del patrimonio).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'annual_net_savings': {
        'title': '💰 Risparmio Netto Annuo (Annual Net Savings)',
        'what_is': "Il surplus economico monetario cumulato nell'arco dell'intero anno solare dopo aver saldato ogni spesa e costo di gestione.",
        'how_calc': '<b>Risparmio Netto Annuo</b> = Totale Entrate Annuali &minus; Totale Uscite Annuali',
        'why_useful': 'Rappresenta la nuova ricchezza liquida generata dal lavoro e dalle rendite pronta per essere reinvestita nel patrimonio.',
        'argus_calc': 'Consolidamento annuale dei flussi di cassa netti certificati al 31/12 di ciascun esercizio.',
        'how_to_read': '• 🟢 Risparmio netto elevato e reinvestito regolarmente nei mercati<br>• 🟡 Risparmio moderato ma continuo<br>• 🔴 Risparmio negativo (Deficit annuale coperto da debito o disinvestimenti).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'quota_risparmio_growth': {
        'title': '💰 Crescita da Risparmio Netto (Contribution from Savings)',
        'what_is': "La quota dell'incremento patrimoniale derivante dai nuovi capitali apportati e risparmiati rispetto all'inizio del periodo.",
        'how_calc': '<b>Quota Risparmio</b> = Totale Flussi Netti di Risparmio Conferiti nel Periodo',
        'why_useful': 'Distinguere quanta parte della crescita patrimoniale è frutto della disciplina personale rispetto ai rendimenti di mercato.',
        'argus_calc': 'Scomposizione matriciale della variazione del Net Worth tra flussi netti esterni e capital gain degli asset.',
        'how_to_read': "• 🟢 Contributo positivo costante (Forte spinta propulsiva all'accumulazione patrimoniale).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'quota_mercato_growth': {
        'title': '📈 Crescita da Rivalutazione di Mercato (Market Appreciation)',
        'what_is': "La componente di incremento patrimoniale generata dall'apprezzamento delle quotazioni di mercato e dai dividendi/cedole reinvestiti.",
        'how_calc': '<b>Quota Mercato</b> = &Delta; Valore Asset &minus; Apporti Netti Esterni',
        'why_useful': "Verificare l'efficacia delle decisioni di investimento e l'impatto dell'interesse composto sul patrimonio complessivo.",
        'argus_calc': 'Calcolato isolando la variazione di prezzo di tutti i titoli e beni in portafoglio al netto di acquisti e vendite.',
        'how_to_read': "• 🟢 Contributo positivo superiore all'inflazione (Crescita reale del capitale investito)<br>• 🔴 Contributo negativo (Fase di correzione o drawdown di mercato).",
        'limitations': "L'accuratezza dipende dall'aggiornamento puntuale e completo di tutti i conti e debiti. Non contabilizza passività potenziali o contingenti non ancora formalizzate in impegni contrattuali certi.",
    },
    'totale_crescita_periodo': {
        'title': '🚀 Crescita Complessiva del Patrimonio (Total Net Worth Growth)',
        'what_is': "La variazione percentuale e monetaria complessiva registrata dal Patrimonio Netto nell'arco del periodo di analisi.",
        'how_calc': '<b>&Delta; Net Worth</b> = Net Worth Finale &minus; Net Worth Iniziale &nbsp;|&nbsp; <b>% Crescita</b> = (&Delta; NW / NW Iniziale) &times; 100',
        'why_useful': 'Fornire la misura sintetica primaria del progresso finanziario verso i propri traguardi di lungo termine.',
        'argus_calc': 'Confronto puntuale tra i bilanci consolidati alle due date di rilevazione selezionate.',
        'how_to_read': "• 🟢 > Tasso di inflazione + 3.0% (Creazione robusta di ricchezza reale)<br>• 🟡 In linea con l'inflazione (Preservazione del potere d'acquisto)<br>• 🔴 Negativa (Erosione del patrimonio reale).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'burn_rate_daily': {
        'title': '🔥 Burn Rate Giornaliero (Daily Cash Burn)',
        'what_is': 'La spesa monetaria media sostenuta per ciascun giorno di calendario nel periodo esaminato.',
        'how_calc': '<b>Burn Rate Giornaliero</b> = Totale Uscite Periodo / Numero di Giorni del Periodo',
        'why_useful': 'Avere un riferimento intuitivo e immediato della velocità di consumo della liquidità per regolare le spese discrezionali.',
        'argus_calc': "Ripartizione lineare del totale dei pagamenti certificati sui giorni effettivi del mese o dell'anno.",
        'how_to_read': '• 🟢 In linea con il budget giornaliero sostenibile<br>• 🟡 Lieve superamento stagionale<br>• 🔴 Spesa giornaliera anomala non supportata dai flussi di entrata.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'burn_rate_monthly': {
        'title': '📊 Burn Rate Medio Mensile (Monthly Burn Rate)',
        'what_is': 'La media mensilizzata delle uscite monetarie complessive registrate negli ultimi mesi di attività finanziaria.',
        'how_calc': '<b>Burn Rate Medio</b> = &sum; Spese degli Ultimi 6 Mesi / 6',
        'why_useful': 'Parametro cardine per il calcolo del fondo di emergenza, dei mesi di runway e del FIRE number.',
        'argus_calc': 'Media mobile a 6 mensilità con depurazione di spese eccezionali non ricorrenti opportunamente etichettate.',
        'how_to_read': '• 🟢 Burn rate stabile e ampiamente inferiore alle entrate mensili medie<br>• 🟡 Oscillazioni dovute a spese stagionali<br>• 🔴 Burn rate in aumento continuo non correlato a un aumento del reddito.',
        'limitations': "L'accuratezza dipende dall'aggiornamento puntuale e completo di tutti i conti e debiti. Non contabilizza passività potenziali o contingenti non ancora formalizzate in impegni contrattuali certi.",
    },
    'recurring_burn': {
        'title': '📊 Fixed Cost Ratio & Rigidità di Spesa (Needs Ratio)',
        'what_is': 'La percentuale delle entrate nette assorbita dalle spese fisse obbligatorie e non eliminabili (affitto/mutuo, utenze, assicurazioni, cibo primario, trasporti essenziali).',
        'how_calc': '<b>Fixed Cost Ratio</b> = [ &sum; Spese Fisse Mensili / Entrate Nette Mensili ] &times; 100',
        'why_useful': 'Misura la rigidità del proprio stile di vita: più basso è il rapporto dei costi fissi, più è facile ridurre le spese in caso di crisi senza compromettere la propria stabilità.',
        'argus_calc': 'Categorizzazione algoritmica automatica delle transazioni ricorrenti con frequenza stabilita e assenza di discrezionalità.',
        'how_to_read': '• 🟢 &le; 50% (Piena conformità alla regola aurea 50/30/20, flessibilità elevata)<br>• 🟡 50% - 60% (Flessibilità contenuta ma gestibile)<br>• 🔴 &gt; 65% (Struttura di spesa pericolosamente rigida: elevato rischio di insolvenza in caso di calo del reddito).',
        'limitations': 'Spesso categorizza rate di debito per acquisti voluttuari come spese fisse; richiede revisione manuale periodica dei contratti di fornitura.',
    },
    'net_cash_flow': {
        'title': '💧 Flusso di Cassa Netto (Net Cash Flow)',
        'what_is': 'La differenza algebrica tra tutte le entrate e tutte le uscite di cassa registrate nel periodo analizzato.',
        'how_calc': '<b>Flusso Netto</b> = Entrate Totali &minus; Uscite Totali',
        'why_useful': 'Verificare immediatamente la generazione o distruzione netta di liquidità nel periodo.',
        'argus_calc': 'Consolidamento multi-bancario al centesimo dei flussi in entrata e uscita.',
        'how_to_read': '• 🟢 Positivo marcato (Nuova liquidità disponibile per investimento)<br>• 🟡 Prossimo a zero (Gestione in pareggio)<br>• 🔴 Negativo (Deficit finanziario temporaneo da monitorare).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'monthly_inflow': {
        'title': '💶 Entrata Media Mensile (Average Monthly Inflow)',
        'what_is': 'La media ponderata dei compensi e redditi netti incassati su base mensile negli ultimi periodi.',
        'how_calc': '<b>Entrata Media</b> = &sum; Entrate Totali Nette / Numero Mesi',
        'why_useful': 'Fissare una baseline affidabile per programmare investimenti automatici (PAC) e rate di finanziamento.',
        'argus_calc': 'Media rolling delle entrate depurata da componenti straordinarie o rimborsi una tantum.',
        'how_to_read': '• 🟢 Trend stabile o in crescita (Solidità e predicibilità dei flussi di cassa).',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'budget_allocated': {
        'title': '🎯 Budget Allocato del Periodo (Budget Envelope)',
        'what_is': 'Il plafond massimo di spesa programmato per il periodo di riferimento suddiviso per macro-categorie.',
        'how_calc': '<b>Budget Allocato</b> = &sum; Limiti di Spesa per Categoria (Casa, Spesa, Svago, Trasporti, ecc.)',
        'why_useful': 'Mantenere disciplina finanziaria proattiva evitando sforamenti prima che impattino il risparmio di fine mese.',
        'argus_calc': 'Confronto in tempo reale tra plafond pianificato e spesa consuntivata tramite tracciamento scontrini e transazioni.',
        'how_to_read': '• 🟢 Spesa consuntivata &le; 90% del budget (Perfetto rispetto degli obiettivi)<br>• 🟡 90% - 100% (In prossimità del limite)<br>• 🔴 > 100% (Sforamento di budget registrato).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'budget_overrun': {
        'title': '⚠️ Categorie Fuori Budget (Budget Overruns)',
        'what_is': "Il numero di categorie di spesa o l'ammontare complessivo che ha superato il limite di budget stabilito nel periodo.",
        'how_calc': '<b>Scostamento</b> = &sum; max(0, Spesa Effettiva<sub>cat</sub> &minus; Budget Assegnato<sub>cat</sub>)',
        'why_useful': 'Identificare immediatamente dove si concentrano gli sprechi o le anomalie di spesa da correggere.',
        'argus_calc': 'Scansione continua per singola categoria merceologica con evidenziazione del delta negativo.',
        'how_to_read': '• 🟢 0 Categorie (Tutte le voci di spesa sono rimaste entro il budget)<br>• 🟡 1 - 2 Categorie con sforamenti lievi (<10%)<br>• 🔴 &ge; 3 Categorie fuori budget o sforamento aggregato marcato.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'opportunity_drag': {
        'title': '⏳ Opportunity Drag a 10/20 Anni (Costo Opportunità)',
        'what_is': 'Il capitale futuro potenziale perso destinando spese superflue ai consumi invece di investirle a interesse composto.',
        'how_calc': '<b>Capitale Perso</b> = Spesa Ricorrente &times; [ (1 + r)<sup>N</sup> &minus; 1 ] / r &nbsp;|&nbsp; <i>con r = rendimento atteso di mercato (es. 7%)</i>',
        'why_useful': 'Rendere tangibile il costo reale delle spese accessorie nel lungo termine grazie alla potenza della capitalizzazione composta.',
        'argus_calc': 'Simulatore di capitalizzazione che attualizza e capitalizza il burn rate ricorrente a 10 e 20 anni.',
        'how_to_read': "• 🟢 Opportunity drag ridotto al minimo grazie a un'elevata quota di risparmio investita.",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'extra_monthly_savings': {
        'title': '💰 Risparmio Extra Investibile (Monthly Surplus)',
        'what_is': 'La quota monetaria addizionale di cassa libera generata nel mese oltre il budget prefissato, pronta per essere investita.',
        'how_calc': '<b>Surplus</b> = Entrate Effettive &minus; Spese Consuntivate &minus; Quota Risparmio Programmata',
        'why_useful': 'Ottimizzare la liquidità in eccesso accelerando il PAC o riducendo debiti a tasso variabile.',
        'argus_calc': 'Calcolato al termine di ogni ciclo di rendicontazione mensile dal Cash Flow Engine.',
        'how_to_read': '• 🟢 Surplus positivo investibile (Opportunità di accelerazione patrimoniale).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'patrimonio_forecast': {
        'title': '📈 Proiezione di Crescita Patrimoniale a 10/20 Anni',
        'what_is': 'La stima probabilistica del patrimonio netto futuro basata sul tasso di risparmio corrente e sul rendimento atteso degli asset.',
        'how_calc': '<b>V<sub>t</sub></b> = V<sub>0</sub> &times; (1 + r)<sup>t</sup> + &sum; Risparmio Annuo &times; (1 + r)<sup>t &minus; i</sup>',
        'why_useful': "Verificare la traiettoria di accumulazione a lungo termine e visualizzare l'effetto moltiplicatore del tempo.",
        'argus_calc': 'Simulazione stocastica Monte Carlo (1,000 traiettorie) con inflazione attesa e dispersione di volatilità.',
        'how_to_read': '• 🟢 Traiettoria mediana in linea con il target di indipendenza finanziaria o FIRE.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'cash_forecast_3m': {
        'title': '🔮 Previsione Cassa a 3 Mesi (3-Month Cash Forecast)',
        'what_is': 'La stima prudenziale del saldo di liquidità sui conti bancari tra 90 giorni, considerando entrate attese e spese ricorrenti pianificate.',
        'how_calc': '<b>Cassa (T+3)</b> = Cassa Attuale + &sum; Entrate Previsionali &minus; &sum; Uscite Fisse Programmate',
        'why_useful': 'Prevenire crisi di liquidità a breve termine e pianificare con serenità le scadenze fiscali o rate di debito.',
        'argus_calc': 'Algoritmo predittivo basato sulla stagionalità storica dei flussi di cassa e sulle scadenze censite.',
        'how_to_read': '• 🟢 Saldo sempre superiore al fondo di emergenza minimo<br>• 🟡 Saldo in lieve flessione ma capiente<br>• 🔴 Saldo previsto negativo o inferiore alla soglia di riserva minima.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'cash_forecast_6m': {
        'title': '🔮 Previsione Cassa a 6 Mesi (6-Month Cash Forecast)',
        'what_is': 'La stima a medio termine del saldo di cassa disponibile a 180 giorni per testare la tenuta finanziaria a fronte delle scadenze semestrali.',
        'how_calc': '<b>Cassa (T+6)</b> = Cassa Attuale + &sum; Flussi Netti Attesi nei prossimi 6 mesi',
        'why_useful': 'Pianificare con anticipo investimenti importanti, acquisti di beni durevoli o versamenti previdenziali.',
        'argus_calc': 'Modello di forecasting integrato con scadenze tributarie (F24, IMU), rate mutuo e spese ricorrenti.',
        'how_to_read': '• 🟢 Cassa a 6 mesi solida e in crescita<br>• 🟡 Flessione prevista in corrispondenza di imposte/tasse annuali<br>• 🔴 Rischio di tensioni di cassa entro 6 mesi.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'reconciliation_rate': {
        'title': '🔍 Tasso di Riconciliazione (Transaction Reconciliation Rate)',
        'what_is': 'La percentuale di transazioni bancarie importate che sono state categorizzate, associate a un conto certificato e riconciliate.',
        'how_calc': '<b>Tasso di Riconciliazione</b> = (Transazioni Riconciliate / Totale Transazioni Importate) &times; 100',
        'why_useful': "Garantire l'affidabilità totale dei dati del conto economico e dello stato patrimoniale personale.",
        'argus_calc': 'Rapporto tra i movimenti bancari con categoria e controparte validate rispetto al database grezzo.',
        'how_to_read': '• 🟢 &ge; 98% (Dati di bilancio e cashflow totalmente certificati)<br>• 🟡 90% - 98% (Alcune transazioni in attesa di categorizzazione)<br>• 🔴 < 90% (Dati incompleti: categorizzare i movimenti pendenti).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'duplicate_txs': {
        'title': '🛡️ Duplicati Rilevati & Depurati (Duplicate Transactions)',
        'what_is': 'Il numero di movimenti bancari o carte identificati come copie identiche generate da importazioni multiple o pre-autorizzazioni provvisorie.',
        'how_calc': '<b>Duplicati</b> = &sum; Transazioni con stesso importo, data contabile e descrizione su medesimo conto',
        'why_useful': 'Evitare di sovrastimare le spese o gonfiare artificiosamente il conto economico personale con doppi addebiti.',
        'argus_calc': 'Algoritmo di deduplicazione euristica con fuzzy matching su timestamp, importo e merchant.',
        'how_to_read': "• 🟢 0 duplicati residui nel database attivo (Database pulito e certificato)<br>• 🟡 Duplicati rilevati e isolati in quarantena per conferma dell'utente.",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'pareto_merchants_80_20': {
        'title': '📊 Soglia di Pareto 80/20 Fornitori (Expense Concentration)',
        'what_is': "La percentuale di fornitori o merchant che da sola genera l'80% delle spese complessive sostenute.",
        'how_calc': "Ordinamento decrescente delle spese per fornitore fino al raggiungimento dell'80% cumulativo del totale uscite.",
        'why_useful': 'Focalizzare gli sforzi di ottimizzazione dei costi sui pochissimi fornitori che assorbono la quasi totalità del budget.',
        'argus_calc': 'Analisi di Pareto calcolata sulla distribuzione cumulata delle spese aggregate per controparte.',
        'how_to_read': '• 🟢 Pochi fornitori chiave facilmente monitorabili ed efficientabili.',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'spesa_media_tx': {
        'title': '💳 Importo Medio per Transazione (Average Ticket)',
        'what_is': 'Il valore monetario medio di ciascuna spesa o transazione registrata sui propri conti.',
        'how_calc': '<b>Spesa Media</b> = Totale Uscite / Numero Complessivo di Transazioni',
        'why_useful': 'Capire se il proprio modello di spesa è caratterizzato da molti piccoli micro-addebiti o da pochi acquisti rilevanti.',
        'argus_calc': 'Media aritmetica semplice calcolata sul registro di tutte le transazioni di debito del periodo.',
        'how_to_read': '• 🟢 Livello coerente con il profilo di spesa programmato.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'expense_concentration_index': {
        'title': '🌐 Indice di Concentrazione delle Spese (Expense HHI)',
        'what_is': 'Misura di concentrazione delle uscite suddivise tra le diverse categorie di bilancio.',
        'how_calc': '<b>HHI Spese</b> = &sum; (Quota Categoria<sub>i</sub> %)<sup>2</sup>',
        'why_useful': 'Verificare se le uscite sono concentrate su una sola voce (es. casa/mutuo) o distribuite armonicamente.',
        'argus_calc': 'Sommatoria quadratica dei pesi percentuali delle categorie di spesa sul totale uscite.',
        'how_to_read': '• 🟢 Bassa concentrazione (Spese distribuite in modo sano)<br>• 🔴 Concentrazione molto alta (Una singola spesa assorbe la maggioranza delle risorse).',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'processed_transactions_count': {
        'title': '📋 Transazioni Elaborate e Certificate',
        'what_is': 'Il volume totale di record contabili processati ed esaminati dal motore di analisi del Cash Flow.',
        'how_calc': '<b>Conteggio Totale</b> = &sum; Movimenti importati e validati a database',
        'why_useful': 'Fornire evidenza della completezza della base informativa utilizzata per i report.',
        'argus_calc': 'Conteggio puntuale delle righe di transazione presenti nel database SQLite/DuckDB.',
        'how_to_read': '• 🟢 Base statistica solida con tracciamento continuo di tutti i conti.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'pending_transactions_count': {
        'title': '⏳ Transazioni Pendenti in Attesa di Riconciliazione',
        'what_is': "Movimenti bancari importati che richiedono l'assegnazione manuale di una categoria o la conferma di assenza di duplicati.",
        'how_calc': "<b>Transazioni Pendenti</b> = &sum; Movimenti con stato 'Pending' o privi di categoria primaria",
        'why_useful': 'Garantire che nessuna spesa o entrata rimanga non classificata alterando i bilanci.',
        'argus_calc': 'Filtro su record con flag di validazione incompleto nel database patrimoniale.',
        'how_to_read': '• 🟢 0 pendenti (Database interamente validato)<br>• 🔴 Movimenti in sospeso da categorizzare per completare i report.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'tuir_67': {
        'title': '💰 Zainetto Fiscale & Minusvalenze Pregresse (Tax Shield Art. 67)',
        'what_is': "L'ammontare delle perdite di capitale realizzate su strumenti finanziari registrate presso l'intermediario finanziario o nel Quadro RT, compensabili con future plusvalenze entro il quarto anno successivo a quello di realizzo.",
        'how_calc': '<b>Scudo Fiscale</b> = Minusvalenze Residue &times; 26% (o 12.5% per Titoli di Stato)',
        'why_useful': "Massimizzare il recupero del credito d'imposta prima della scadenza naturale dei 4 anni (Tax-Loss Recovery), evitando di regalare denaro all'Erario.",
        'argus_calc': 'Registro a scadenza quadriennale roll-forward con allineamento FIFO delle compensazioni e distinzione stringente tra Redditi Diversi e Redditi di Capitale.',
        'how_to_read': '• 🟢 Crediti compensati tempestivamente senza scadenze a breve<br>• 🟡 Minusvalenze in scadenza entro 12 mesi (Necessaria operatività di recupero con strumenti idonei)<br>• 🔴 Minusvalenze prescritte (Perdita definitiva del beneficio fiscale).',
        'limitations': 'Asimmetria Fiscale Italiana: per legge, i guadagni da ETF e fondi comuni sono classificati come redditi di capitale e non possono compensare le minusvalenze pregresse accumulate nello zainetto fiscale.',
    },
    'ivafe_quadro_rw': {
        'title': '📑 IVAFE & Quadro RW (Monitoraggio Fiscale Attività Estere)',
        'what_is': "Obbligo dichiarativo e tributario italiano per attività finanziarie detenute all'estero o wallet crypto (Imposta sul Valore delle Attività Finanziarie all'Estero).",
        'how_calc': '<b>IVAFE Conti:</b> Imposta fissa € 34,20 se giacenza media > € 5.000<br><b>IVAFE Prodotti Finanziari:</b> 0.20% (o 0.40% Paesi Blacklist) sul valore al 31/12<br><b>Cripto-attività:</b> 0.20% annuo sul valore complessivo',
        'why_useful': "Evitare pesanti sanzioni dell'Agenzia delle Entrate per omessa compilazione del Quadro RW (dal 3% al 15% del non dichiarato).",
        'argus_calc': 'Modulo Fiscale dedicato che calcola giacenze medie, controvalori al 31/12 e compila automaticamente il facsimile dei righi RW.',
        'how_to_read': '• 🟢 Quadro RW allineato e IVAFE calcolata al centesimo<br>• 🟡 Saldi esteri vicini alle soglie di monitoraggio<br>• 🔴 Conti esteri non censiti o documentati.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'imposta_bollo_it': {
        'title': '🏛️ Imposta di Bollo Prodotti Finanziari (D.P.R. 642/1972 Art. 13)',
        'what_is': "L'imposta di bollo proporzionale del 2 per mille (0,20% annuo) applicata sul controvalore degli strumenti finanziari detenuti presso intermediari italiani.",
        'how_calc': '<b>Imposta Bollo</b> = Valore di Mercato al 31/12 (o al termine del periodo di rendicontazione) &times; 0,20%',
        'why_useful': 'Conoscere il costo fiscale patrimoniale fisso che grava annualmente sul portafoglio titoli in regime amministrato o dichiarativo.',
        'argus_calc': 'Calcolato automaticamente su base trimestrale o annuale su tutte le posizioni in titoli e conti deposito italiani censiti.',
        'how_to_read': '• 🟢 Costo fiscale standard del 2 per mille calcolato e accantonato per la liquidazione F24.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'imposta_sostitutiva_rt': {
        'title': '📑 Imposta Sostitutiva Plusvalenze (Quadro RT - 26%)',
        'what_is': "L'imposta del 26% dovuta sulle plusvalenze realizzate su azioni, ETF, derivati e fondi detenuti in regime dichiarativo.",
        'how_calc': '<b>Imposta RT</b> = max(0, Plusvalenze Realizzate Anno &minus; Minusvalenze Compensabili) &times; 26%',
        'why_useful': 'Pianificare la liquidità necessaria per il versamento delle imposte sul capital gain in sede di dichiarazione dei redditi (F24).',
        'argus_calc': "Riconciliazione analitica lotto per lotto FIFO/LIFO di tutti i trade chiusi nell'anno d'imposta con detrazione minus pregresse.",
        'how_to_read': '• 🟢 Imposta stimata coperta da liquidità accantonata<br>• 🔴 Mancato accantonamento con rischio di esborso non pianificato a saldo F24.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'scudo_fiscale': {
        'title': '🛡️ Scudo Fiscale da Minusvalenze (Tax Shield)',
        'what_is': "Il risparmio d'imposta potenziale monetario derivante dalle minusvalenze pregresse registrate nello zainetto fiscale pronte a compensare futuri capital gain.",
        'how_calc': '<b>Scudo Fiscale</b> = Minusvalenze Pregresse Riconosciute &times; 26%',
        'why_useful': 'Monetizzare il valore fiscale delle perdite passate per azzerare le tasse sui guadagni futuri fino alla scadenza del 4° anno.',
        'argus_calc': "Moltiplicazione del saldo dello zainetto minusvalenze per l'aliquota d'imposta di competenza (26% o 12.5% per governativi).",
        'how_to_read': '• 🟢 Scudo fiscale attivo: le prossime plusvalenze realizzate saranno esenti da imposte fino a capienza dello scudo.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'imposte_latenti': {
        'title': '⏳ Imposte Latenti su Plusvalenze (Unrealized Capital Gains Tax)',
        'what_is': 'Il debito tributario stimato che si concretizzerebbe qualora venissero liquidate oggi tutte le posizioni attualmente in guadagno non realizzate.',
        'how_calc': '<b>Imposte Latenti</b> = &sum; max(0, Prezzo Mercato &minus; Prezzo Fiscale Carico) &times; Quantità &times; Aliquota',
        'why_useful': "Conoscere il valore patrimoniale 'netto effettivo' del portafoglio al netto degli oneri fiscali differiti.",
        'argus_calc': 'Rivalutazione continua di tutte le posizioni aperte a prezzo di mercato vs prezzo medio ponderato di carico fiscale (PMC).',
        'how_to_read': "• 🟢 Ottimo differimento fiscale (l'imposta non pagata continua a produrre rendimento composto nel portafoglio).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'minusvalenze_latenti': {
        'title': '📉 Minusvalenze Latenti (Unrealized Capital Losses)',
        'what_is': 'La somma delle perdite non realizzate presenti nelle posizioni aperte in portafoglio che potrebbero generare credito fiscale qualora liquidate.',
        'how_calc': '<b>Minusvalenze Latenti</b> = &sum; min(0, Prezzo Mercato &minus; Prezzo Carico) &times; Quantità',
        'why_useful': "Valutare opportunità di Tax-Loss Harvesting prima della chiusura dell'anno solare per compensare guadagni già conseguiti.",
        'argus_calc': 'Scansione continua dei prezzi correnti rispetto al carico fiscale di ciascun lotto di negoziazione.',
        'how_to_read': '• 🟢 Utilizzabile strategicamente per abbattere il debito fiscale da capital gain tramite vendita e contestuale riacquisto di titoli equivalenti.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'wht_ritenute_estere': {
        'title': '🌍 Ritenute alla Fonte Estere (Foreign Withholding Tax / WHT)',
        'what_is': 'La tassazione applicata dallo Stato di residenza della società estera su dividendi e cedole prima del loro accredito in Italia.',
        'how_calc': '<b>Dividendo Netto</b> = Dividendo Lordo &times; (1 &minus; WHT<sub>estera</sub>) &times; (1 &minus; 26%<sub>Italia</sub>)',
        'why_useful': 'Monitorare la doppia imposizione fiscale sui dividendi esteri e ottimizzare la scelta tra intermediari o strumenti ad accumulazione.',
        'argus_calc': 'Applicazione dei trattati internazionali contro le doppie imposizioni (es. W-8BEN con ritenuta USA al 15%).',
        'how_to_read': '• 🟢 Aliquota convenzionale applicata correttamente (15% USA invece di 30% standard).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'aliquota_effettiva_media': {
        'title': '📊 Aliquota Fiscale Effettiva Media (Effective Tax Rate)',
        'what_is': "L'incidenza percentuale media delle imposte effettivamente corrisposte o dovute sul totale dei proventi finanziari lordi.",
        'how_calc': '<b>Aliquota Effettiva</b> = (Totale Imposte Dovute / Totale Proventi Lordi) &times; 100',
        'why_useful': "Misurare l'efficienza fiscale complessiva della propria asset allocation (mix tra 26% ordinario, 12.5% titoli bianchi e strumenti esenti).",
        'argus_calc': 'Ponderazione delle imposte calcolate sulle diverse tipologie di redditi da capitale e redditi diversi realizzati.',
        'how_to_read': '• 🟢 < 20% (Portafoglio fiscalmente efficiente con buona componente di Titoli di Stato ed esenti)<br>• 🟡 20% - 26% (Aliquota standard di mercato)<br>• 🔴 > 26% (Inefficienza da doppia imposizione non recuperata).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'f24_tax_debt': {
        'title': '📑 Debito Fiscale F24 da Liquidare',
        'what_is': "L'importo totale delle imposte finanziarie e patrimoniali da corrispondere all'Erario tramite modello F24 per l'anno d'imposta.",
        'how_calc': '<b>Totale F24</b> = Imposta Quadro RT (Capital Gain) + IVAFE Quadro RW + Eventuali Sanzioni/Interessi',
        'why_useful': 'Avere contezza esatta della liquidità da accantonare per il saldo e primo acconto della dichiarazione dei redditi.',
        'argus_calc': 'Sommatoria analitica dei tributi calcolati dal Modulo Fiscale certificato per ciascun codice tributo tributario.',
        'how_to_read': '• 🟢 Saldo verificato e pronto per la compilazione dei righi dichiarativi.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'pex_tax_saving': {
        'title': '🏛️ Risparmio Fiscale PEX (Participation Exemption Art. 87 TUIR)',
        'what_is': "L'agevolazione fiscale italiana che esenta da IRES il 95% delle plusvalenze realizzate dalla holding su partecipazioni societarie strategiche qualificate.",
        'how_calc': '<b>Imposta PEX</b> = Plusvalenza &times; 5% &times; 24% (IRES) = <b>1,20% effettivo</b> (invece del 26% ordinario)',
        'why_useful': 'Consente al Family Office societario di reinvestire il 98,8% della liquidità generata dalla cessione di aziende o quote.',
        'argus_calc': 'Verifica dei requisiti PEX (periodo di possesso > 12 mesi, iscrizione immobilizzazioni finanziarie, commercialità ed esenzione paradisi fiscali).',
        'how_to_read': "• 🟢 Requisiti PEX soddisfatti: imposizione fiscale ridotta all'1,20% con risparmio fiscale del 24,80%.",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'tax_efficiency_ratio': {
        'title': '📈 Efficienza Fiscale di Portafoglio (Tax Efficiency Ratio)',
        'what_is': 'Il rapporto tra il rendimento netto post-imposte e il rendimento lordo complessivo generato dal portafoglio.',
        'how_calc': '<b>Efficienza Fiscale</b> = (Rendimento Netto / Rendimento Lordo) &times; 100',
        'why_useful': "Quantificare quanto valore viene preservato rispetto all'erosione fiscale grazie a compensazioni di minusvalenze e strumenti passivi.",
        'argus_calc': 'Rapporto tra CAGR netto e CAGR lordo ricalcolato sui flussi fiscali effettivi.',
        'how_to_read': '• 🟢 > 85% (Gestione patrimoniale ad alta efficienza fiscale)<br>• 🟡 75% - 85% (Efficienza nella media di mercato)<br>• 🔴 < 75% (Erosione fiscale elevata dovuta a turnover frequente o mancato recupero minus).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'ytm': {
        'title': '📈 Yield to Maturity (YTM / Rendimento Effettivo a Scadenza)',
        'what_is': "Il tasso di rendimento interno annuo atteso di un'obbligazione qualora venga acquistata al prezzo corrente e mantenuta fino alla naturale scadenza.",
        'how_calc': '<b>Prezzo</b> = &sum; [ Cedola<sub>t</sub> / (1 + YTM)<sup>t</sup> ] + Rimborso<sub>N</sub> / (1 + YTM)<sup>N</sup>',
        'why_useful': 'Confrontare in modo omogeneo titoli obbligazionari con diverse date di scadenza, cedole facciali e prezzi di quotazione.',
        'argus_calc': 'Risoluzione numerica iterativa (metodo Brent/Newton-Raphson) con convenzione di conteggio giorni esatta (Actual/Actual).',
        'how_to_read': '• 🟢 YTM > Inflazione attesa (Rendimento reale garantito a scadenza positivo)<br>• 🟡 In linea con i tassi di mercato BCE/Fed<br>• 🔴 YTM < Inflazione (Rendimento reale negativo a scadenza).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'modified_duration': {
        'title': '⏱️ Modified Duration (Sensibilità del Prezzo ai Tassi)',
        'what_is': "Misura della variazione percentuale stimata del prezzo dell'obbligazione a fronte di una variazione dell'1% (100 bps) nei tassi di interesse di mercato.",
        'how_calc': '<b>ModDuration</b> = Duration di Macaulay / (1 + YTM / m) &nbsp;|&nbsp; <b>&Delta;Prezzo %</b> &asymp; &minus;ModDuration &times; &Delta;y',
        'why_useful': 'Quantificare il rischio tasso del portafoglio obbligazionario: maggiore è la duration, più il titolo crolla al salire dei tassi.',
        'argus_calc': 'Media ponderata delle scadenze dei flussi di cassa attualizzati al tasso YTM divisa per il fattore di capitalizzazione.',
        'how_to_read': '• 🟢 < 3.0 anni (Portafoglio a basso rischio tasso, molto difensivo)<br>• 🟡 3.0 - 7.0 anni (Duration intermedia standard)<br>• 🔴 > 7.0 anni (Elevata sensibilità: forti oscillazioni di prezzo alle decisioni delle banche centrali).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'convexity': {
        'title': '📐 Convessità Obbligazionaria (Bond Convexity)',
        'what_is': "La derivata seconda del prezzo rispetto al rendimento: misura la curvatura del profilo prezzo-rendimento oltre l'approssimazione lineare della duration.",
        'how_calc': '<b>Convexity</b> = [ 1 / (P &times; (1+y)<sup>2</sup>) ] &times; &sum; [ t &times; (t+1) &times; CF<sub>t</sub> / (1+y)<sup>t</sup> ]',
        'why_useful': 'La convessità positiva è una proprietà desiderabile: fa salire il prezzo più di quanto previsto dalla duration quando i tassi scendono, e lo fa scendere meno quando i tassi salgono.',
        'argus_calc': 'Calcolato analiticamente su tutta la curva dei flussi di cassa obbligazionari.',
        'how_to_read': "• 🟢 Convessità elevata (Ottima asimmetria positiva a favore dell'investitore).",
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'dv01': {
        'title': '💵 Dollar Value of an 01 (DV01 / Rischio per Punto Base)',
        'what_is': 'La variazione monetaria assoluta del valore del portafoglio a fronte di un movimento parallelo di 1 punto base (0,01%) della curva dei tassi.',
        'how_calc': '<b>DV01</b> = &minus; ( &Delta;Valore Portafoglio / &Delta;y ) &times; 0,0001 &asymp; ModDuration &times; Valore &times; 0,0001',
        'why_useful': 'Fissare esattamente quanti euro si guadagnano o perdono per ogni singola variazione minimale dei tassi di interesse.',
        'argus_calc': 'Moltiplicazione matriciale della duration modificata per il controvalore totale del portafoglio obbligazionario per 0,0001.',
        'how_to_read': '• 🟢 Calibrato sui limiti di tolleranza di perdita monetaria giornaliera del desk di tesoreria.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'z_spread': {
        'title': '⚖️ Z-Spread & Rischio Credito (Zero-Volatility Spread)',
        'what_is': "Lo spread costante da aggiungere all'intera curva dei tassi privi di rischio (Spot Zero-Coupon) per eguagliare il prezzo di mercato dell'obbligazione.",
        'how_calc': '<b>Prezzo</b> = &sum; [ CF<sub>t</sub> / (1 + (r<sub>t</sub> + Z)/m)<sup>t</sup> ]',
        'why_useful': "Misurare il premio al rischio puro (rischio emittente, liquidità e default) depurato dall'effetto della pendenza della curva dei tassi.",
        'argus_calc': 'Interpolazione continua sulla curva risk-free dei Titoli di Stato AAA (Bund/OAT) o tassi swap Euribor.',
        'how_to_read': '• 🟢 Spread contenuto (< 100 bps: emittente di primario standing investment grade)<br>• 🟡 100 - 250 bps (Rischio credito moderato)<br>• 🔴 > 300 bps (Emittente speculativo high-yield con elevato premio al rischio).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'hhi_index': {
        'title': '🌐 Indice Herfindahl-Hirschman (HHI Concentrazione)',
        'what_is': 'Misura standard di concentrazione utilizzata per quantificare il grado di frammentazione o sovraesposizione del portafoglio su pochi titoli.',
        'how_calc': '<b>HHI</b> = &sum; (w<sub>i</sub> &times; 100)<sup>2</sup> &nbsp;|&nbsp; <i>Range: da 0 (massima dispersione) a 10.000 (100% su un singolo titolo)</i>',
        'why_useful': 'Evitare di concentrare inconsapevolmente il patrimonio su pochissimi titoli, aumentando il rischio specifico non remunerato.',
        'argus_calc': 'Somma dei quadrati delle percentuali di peso di ciascuna posizione attiva in portafoglio.',
        'how_to_read': '• 🟢 < 1.000 (Portafoglio altamente diversificato e ben distribuito)<br>• 🟡 1.000 - 1.800 (Concentrazione moderata fisiologica)<br>• 🔴 > 1.800 (Portafoglio fortemente concentrato su pochi asset dominanti).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'win_rate': {
        'title': '🎯 Percentuale Operazioni in Profitto (Win Rate %)',
        'what_is': 'La frazione percentuale di operazioni di trading o investimenti chiusi con un profitto netto positivo.',
        'how_calc': '<b>Win Rate</b> = (Numero Trade Vincenti / Numero Totale Trade Chiusi) &times; 100',
        'why_useful': 'Misurare la frequenza di successo statistico della strategia di negoziazione.',
        'argus_calc': 'Estrae dal registro storico delle vendite tutte le posizioni con PnL realizzato netto > 0.',
        'how_to_read': '• 🟢 > 55% per strategie di momentum o trend following<br>• 🟡 45% - 55% (Ottimo se supportato da un elevato Profit Factor)<br>• 🔴 < 40% (Richiede un payoff asimmetrico molto alto per essere sostenibile).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'profit_factor': {
        'title': '⚖️ Profit Factor (Rapporto Profitti Lordi / Perdite Lorde)',
        'what_is': 'Il rapporto tra la somma di tutti i guadagni generati dai trade vincenti e la somma di tutte le perdite subite nei trade perdenti.',
        'how_calc': '<b>Profit Factor</b> = &sum; Guadagni Lordi / | &sum; Perdite Lorde |',
        'why_useful': "Misurare l'aspettativa matematica e la redditività complessiva di un sistema di trading o selezione titoli.",
        'argus_calc': 'Rapporto algebrico dei PnL chiusi sul registro storico delle esecuzioni.',
        'how_to_read': '• 🟢 > 1.75 (Strategia solida e altamente profittevole)<br>• 🟡 1.25 - 1.75 (Strategia redditizia nella media)<br>• 🔴 < 1.00 (Sistema in perdita matematica: le perdite superano i guadagni).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'holding_period': {
        'title': '⏱️ Holding Period Medio (Tempo di Detenzione)',
        'what_is': "Il numero medio di giorni di calendario trascorsi tra l'apertura e la chiusura delle posizioni nel portafoglio.",
        'how_calc': '<b>Holding Period</b> = (1/N) &sum; (Data Vendita<sub>i</sub> &minus; Data Acquisto<sub>i</sub>)',
        'why_useful': "Verificare la coerenza operativa tra la filosofia dichiarata (investimento di lungo termine vs trading tattico) e l'effettiva gestione.",
        'argus_calc': 'Media ponderata delle date di esecuzione per singolo lotto di compravendita.',
        'how_to_read': '• 🟢 > 365 giorni (Investitore di lungo periodo / buy-and-hold)<br>• 🟡 30 - 365 giorni (Strategia swing / medio termine)<br>• 🔴 < 30 giorni (Alta frequenza: attenzione a costi commissionali e drag fiscale).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'dividend_yield': {
        'title': '💵 Dividend Yield Medio (Rendimento Cedolare Annuo)',
        'what_is': 'La percentuale annua di flusso di cassa generata dal portafoglio sotto forma di dividendi o cedole rispetto al suo valore di mercato corrente.',
        'how_calc': '<b>Dividend Yield</b> = (Dividendi Annui Attesi Stimati / Controvalore Totale Portafoglio) &times; 100',
        'why_useful': 'Valutare la capacità del portafoglio di generare reddito passivo periodico da spendere o reinvestire senza intaccare il capitale.',
        'argus_calc': 'Ponderazione dei dividend yield e tassi cedolari correnti dei singoli titoli per i rispettivi pesi di allocazione.',
        'how_to_read': "• 🟢 2.5% - 4.5% (Ottimo rendimento da dividendi sostenibile)<br>• 🟡 1.0% - 2.5% (Profilo orientato alla crescita)<br>• 🔴 > 7.0% (Rischio Dividend Trap: possibile taglio dei dividendi o insostenibilità finanziaria dell'emittente).",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'dividendi_annui': {
        'title': '💶 Flusso Dividendi Annui Stimati (Estimated Annual Dividends)',
        'what_is': "La somma monetaria complessiva attesa in euro generata da cedole e dividendi nell'arco dei prossimi 12 mesi solari.",
        'how_calc': '<b>Dividendi Annui</b> = &sum; (Numero Azioni<sub>i</sub> &times; Dividendo per Azione Atteso<sub>i</sub> &times; FX<sub>i</sub>)',
        'why_useful': 'Pianificare con esattezza le entrate passive del conto economico personale a copertura del tenore di vita.',
        'argus_calc': 'Proiezione basata sul calendario stacchi e sui dividendi storici/consensus certificati dagli emittenti.',
        'how_to_read': '• 🟢 Flusso cedolare regolare e ampiamente prevedibile a supporto della cassa.',
        'limitations': 'La misura riflette i dati storici e contabili disponibili; non incorpora scenari sistemici esogeni non ancora riflessi nelle serie temporali o nei documenti ufficiali.',
    },
    'execution_shortfall': {
        'title': '📉 Implementation Shortfall (IS / Costo Totale di Esecuzione Perold)',
        'what_is': "La differenza di controvalore tra il portafoglio ideale teorico al momento della decisione di investimento e il valore effettivo realizzato dopo l'esecuzione a mercato.",
        'how_calc': '<b>IS</b> = Costo Esplicito (Commissioni + Tasse) + Impatto di Mercato + Costo del Ritardo (Delay Cost)',
        'why_useful': 'Identificare i costi occulti di negoziazione che erodono il rendimento gestionale attivo.',
        'argus_calc': 'Algoritmo di benchmark execution rispetto al prezzo di arrivo sul mercato (Arrival Price) con scomposizione quadripartita.',
        'how_to_read': '• 🟢 < 10 bps (Esecuzione di mercato eccellente a basso impatto)<br>• 🟡 10 - 25 bps (Costi standard di liquidità)<br>• 🔴 > 25 bps (Esecuzione inefficiente con severo slippage o ritardo eccessivo).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'market_impact': {
        'title': '⚡ Impatto di Mercato (Market Impact / Almgren-Chriss)',
        'what_is': "L'effetto distorsivo sul prezzo di mercato causato dall'immissione di ordini di acquisto o vendita di dimensioni rilevanti rispetto alla liquidità del book.",
        'how_calc': '<b>Impatto</b> = &gamma; &times; &sigma; &times; (Volume Ordine / ADV)<sup>&alpha;</sup> &nbsp;|&nbsp; <i>secondo il modello Almgren-Chriss</i>',
        'why_useful': 'Prevedere quanto il proprio ordine sposterà il prezzo contro di sé prima di inviarlo al broker.',
        'argus_calc': 'Stima continua basata sulla volatilità intraday del titolo e sul volume medio giornaliero a 30 sedute (ADV).',
        'how_to_read': "• 🟢 < 5 bps (Impatto trascurabile, ordine assorbibile dalla liquidità ordinaria)<br>• 🔴 > 20 bps (Elevato impatto: suddividere l'ordine con algoritmi TWAP o VWAP).",
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'vwap': {
        'title': '📊 VWAP (Volume-Weighted Average Price)',
        'what_is': "Il prezzo medio ponderato per i volumi scambiati di un titolo nel corso dell'intera sessione di negoziazione.",
        'how_calc': '<b>VWAP</b> = &sum; (Prezzo<sub>i</sub> &times; Volume<sub>i</sub>) / &sum; Volume<sub>i</sub>',
        'why_useful': "Benchmark primario per valutare la qualità dell'esecuzione: acquistare sotto il VWAP o vendere sopra il VWAP attesta un'ottima esecuzione.",
        'argus_calc': 'Integrazione dei dati tick-by-tick ponderati per il volume effettivo registrato sui mercati regolamentati.',
        'how_to_read': '• 🟢 Esecuzione Acquisto < VWAP (Ottimo prezzo ottenuto)<br>• 🔴 Esecuzione Acquisto > VWAP (Acquisto a premio rispetto alla media di mercato).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'slippage': {
        'title': '📉 Slippage Stimato di Esecuzione',
        'what_is': "La differenza tra il prezzo di mercato visualizzato al momento dell'invio dell'ordine (Mid-Price) e il prezzo effettivo di fill eseguito.",
        'how_calc': "<b>Slippage</b> = | Prezzo di Esecuzione Effettivo &minus; Prezzo Mid al momento dell'invio |",
        'why_useful': 'Quantificare il costo implicito causato da spread bid-ask e latenza di connessione con il broker.',
        'argus_calc': "Registrazione del delta al momento della ricezione della conferma di eseguito dall'exchange.",
        'how_to_read': '• 🟢 Slippage contenuto entro mezzo tick di book.',
        'limitations': "La stima assume condizioni di mercato ordinarie con book di negoziazione capiente. In presenza di gap di apertura, news macro improvvise o bassa liquidità, l'esecuzione reale può subire divergenze marcate.",
    },
    'order_flow_imbalance': {
        'title': '⚖️ Order Flow Imbalance (OFI / Pressione del Book)',
        'what_is': "La misura dell'asimmetria dei flussi di ordini al miglior denaro (bid) e lettera (ask) per prevedere movimenti di prezzo intraday a brevissimo termine.",
        'how_calc': "<b>OFI</b> = &Delta;Volume al Bid (se prezzo invariato o salito) &minus; &Delta;Volume all'Ask (se prezzo invariato o sceso)",
        'why_useful': "Riconoscere se prevale una pressione aggressiva di compratori o venditori istituzionali prima dell'esplosione della volatilità.",
        'argus_calc': 'Elaborato su quote di Livello 1 e 2 del book di negoziazione in tempo reale.',
        'how_to_read': '• 🟢 OFI fortemente positivo (Pressione acquirente sul book, probabile rialzo)<br>• 🔴 OFI fortemente negativo (Pressione venditrice).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'rsi_indicator': {
        'title': '📈 Relative Strength Index (RSI a 14 Periodi)',
        'what_is': "Oscillatore di momentum tecnico che misura la velocità e l'ampiezza delle variazioni recenti di prezzo su una scala normalizzata da 0 a 100.",
        'how_calc': '<b>RSI</b> = 100 &minus; [ 100 / (1 + RS) ] &nbsp;|&nbsp; <b>RS</b> = Media Guadagni a 14gg / Media Perdite a 14gg',
        'why_useful': 'Identificare condizioni estreme di ipercomprato o ipervenduto e potenziali divergenze con i prezzi.',
        'argus_calc': 'Calcolato sulle serie storiche a 14 sedute con smoothing di Wilder.',
        'how_to_read': '• 🟢 RSI 40 - 60 (Fase di equilibrio / trend sano)<br>• 🟡 RSI > 70 (Ipercomprato: potenziale affaticamento del rialzo)<br>• 🔴 RSI < 30 (Ipervenduto: potenziale rimbalzo tecnico o forte debolezza).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'point_of_control': {
        'title': '🎯 Point of Control (POC / Volume Profile)',
        'what_is': 'Il livello di prezzo esatto in corrispondenza del quale è stato scambiato il maggior volume complessivo di contratti nel periodo.',
        'how_calc': 'Livello di prezzo p tale che <b>Volume(p) = max(Volume(Price Level))</b> sul profilo volumetrico.',
        'why_useful': 'Rappresenta il punto di massimo consenso e accettazione del valore da parte degli operatori di mercato: funge da potente supporto o resistenza.',
        'argus_calc': 'Istogramma orizzontale dei volumi aggregati per livello di prezzo (TPO / Volume Profile).',
        'how_to_read': '• 🟢 Prezzo sopra il POC (Compratori in controllo del trend)<br>• 🔴 Prezzo sotto il POC (Venditori in controllo).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'adx_trend': {
        'title': '⚡ Average Directional Index (ADX a 14 Periodi / Forza del Trend)',
        'what_is': 'Indicatore che quantifica la forza pura e la direzionalità di un trend di prezzo indipendentemente dal fatto che sia rialzista o ribassista.',
        'how_calc': '<b>ADX</b> = Media Mobile Esponenziale a 14 periodi del Differenziale Direzionale Indicizzato (DX)',
        'why_useful': 'Distinguere fasi di mercato in forte trend direzionale (in cui funzionano le strategie trend-following) da fasi di congestione laterale o trading range.',
        'argus_calc': 'Elaborazione delle serie storiche High-Low-Close a 14 periodi con linee +DI e -DI.',
        'how_to_read': '• 🟢 ADX > 25 (Trend forte e direzionale confermato)<br>• 🟡 ADX 20 - 25 (Trend in formazione)<br>• 🔴 ADX < 20 (Mercato laterale privo di direzione chiara, rischio falsi segnali).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'confluence_score': {
        'title': '🎯 Confluence Score Tecnico (Punteggio Multi-Segnale)',
        'what_is': "Punteggio sintetico composito che valuta l'allineamento simultaneo di molteplici indicatori indipendenti (Trend, Momentum, Volumi, Volatilità e Supporti).",
        'how_calc': '<b>Confluence Score</b> = &sum; Segnali Confermati (RSI, ADX, POC, Medie Mobili, Volume Imbalance) pesati per affidabilità statistica.',
        'why_useful': 'Evitare di agire su segnali isolati, operando unicamente quando diverse metodologie analitiche confermano la medesima direzione.',
        'argus_calc': 'Algoritmo ad albero di decisione che assegna un punteggio normalizzato da 0 a 100.',
        'how_to_read': '• 🟢 > 75 (Confluenza rialzista eccezionale, molteplici indicatori allineati)<br>• 🟡 45 - 75 (Segnali misti / moderati)<br>• 🔴 < 45 (Assenza di convergenza o prevalenza di segnali di debolezza).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'basel_traffic_light': {
        'title': '🚦 Basel Traffic Light (VaR Backtesting / Test Semaforico di Basilea)',
        'what_is': 'Procedura di conformità regolamentare di Basilea per verificare la robustezza del modello Value at Risk contando le eccezioni di perdita registrate su 250 sedute.',
        'how_calc': 'Conteggio del numero di giorni storici su 250 in cui la perdita effettiva ha superato il VaR al 99% stimato dal modello.',
        'why_useful': 'Validare scientificamente che il modello di rischio non sottostimi le perdite estreme incorrendo in sanzioni o fallimento analitico.',
        'argus_calc': 'Backtesting rolling su 250 giorni lavorativi confrontando il VaR previsto con il PnL effettivo del giorno successivo.',
        'how_to_read': '• 🟢 Zona Verde (0 - 4 eccezioni: modello perfettamente accurato e conforme)<br>• 🟡 Zona Gialla (5 - 9 eccezioni: richiesta di monitoraggio e calibrazione dei parametri)<br>• 🔴 Zona Rossa (&ge; 10 eccezioni: modello fallito e non valido, sottostima sistematica del rischio).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'copula_tail_dependence': {
        'title': '🌐 Copula Tail Dependence (Dipendenza di Coda &lambda;<sub>L</sub> / &lambda;<sub>U</sub>)',
        'what_is': 'La probabilità che un asset subisca un crollo estremo contestualmente al crollo di un altro asset, superando i limiti del coefficiente lineare di Pearson.',
        'how_calc': '<b>&lambda;<sub>L</sub></b> = lim<sub>u &rarr; 0</sub> P( U<sub>1</sub> &le; u | U<sub>2</sub> &le; u ) &nbsp;|&nbsp; <b>&lambda;<sub>U</sub></b> = lim<sub>u &rarr; 1</sub> P( U<sub>1</sub> > u | U<sub>2</sub> > u )',
        'why_useful': 'Evitare la trappola della diversificazione apparente: molti asset scorrelati in tempi normali crollano insieme durante i crash di borsa.',
        'argus_calc': 'Fitting di Copula t di Student o Copula di Clayton/Gumbel sulle distribuzioni marginali dei rendimenti empirici.',
        'how_to_read': "• 🟢 &lambda;<sub>L</sub> < 0.15 (Assenza di contagio, reale protezione e asimmetria difensiva)<br>• 🟡 0.15 - 0.30 (Contagio moderato)<br>• 🔴 &lambda;<sub>L</sub> &ge; 0.30 (Alto rischio di contagio: gli asset crollano all'unisono nei cigni neri).",
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'merton_jump': {
        'title': '⚡ Merton Jump-Diffusion (Intensità di Salto &lambda;)',
        'what_is': 'Modello stocastico avanzato che arricchisce il moto browniano geometrico introducendo un processo di Poisson per simulare crolli improvvisi e shock discontinui.',
        'how_calc': '<b>dS<sub>t</sub> / S<sub>t</sub></b> = (&mu; &minus; &lambda;k) dt + &sigma; dW<sub>t</sub> + (J &minus; 1) dq<sub>t</sub>',
        'why_useful': 'Prezzare correttamente il rischio di shock improvvisi (gap di apertura, fallimenti, notizie geopolitiche) che la normale gaussiana ignora.',
        'argus_calc': 'Calibrazione dei parametri di salto (intensità &lambda;, media &mu;<sub>J</sub>, deviazione &sigma;<sub>J</sub>) tramite massima verosimiglianza su serie storiche ad alta frequenza.',
        'how_to_read': '• 🟢 &lambda; contenuto (Dinamica di prezzo regolare e continua)<br>• 🔴 &lambda; elevato (Alta frequenza di salti discontinui: indispensabile protezione con opzioni put).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'black_scholes_greeks': {
        'title': '🎯 Greche di Portafoglio (Delta, Gamma, Vega, Theta)',
        'what_is': 'Le sensibilità di primo e secondo ordine del valore della posizione opzionaria rispetto a Prezzo Sottostante (Delta, Gamma), Volatilità Implicita (Vega) e Decadimento Temporale (Theta).',
        'how_calc': '<b>&Delta;</b> = &part;V/&part;S &nbsp;|&nbsp; <b>&Gamma;</b> = &part;<sup>2</sup>V/&part;S<sup>2</sup> &nbsp;|&nbsp; <b>&nu;</b> = &part;V/&part;&sigma; &nbsp;|&nbsp; <b>&Theta;</b> = &part;V/&part;t',
        'why_useful': "Immunizzare o calibrare l'esposizione al rischio di mercato gestendo coperture dinamiche (Delta-Hedging) ed estraendo premio dalla volatilità.",
        'argus_calc': 'Modello Black-Scholes-Merton a volatilità implicita effettiva estratta dalle superfici live di mercato.',
        'how_to_read': '• 🟢 Copertura neutrale (&Delta; bilanciato verso il target)<br>• 🔴 Squilibrio direzionale o eccessivo costo di decadimento temporale (&Theta; passivo).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'fama_french': {
        'title': '🏛️ Modello Fattoriale Fama-French (5-Factors & Momentum)',
        'what_is': 'Scomposizione scientifica del rendimento del portafoglio su 5 fattori di rischio sistemico: Mercato (Mkt), Dimensione (SMB), Valore (HML), Redditività (RMW) e Investimento (CMA).',
        'how_calc': '<b>R<sub>p</sub> &minus; R<sub>f</sub></b> = &alpha; + &beta;<sub>1</sub>(Mkt&minus;R<sub>f</sub>) + &beta;<sub>2</sub>SMB + &beta;<sub>3</sub>HML + &beta;<sub>4</sub>RMW + &beta;<sub>5</sub>CMA + &beta;<sub>6</sub>MOM + &epsilon;',
        'why_useful': 'Capire da dove proviene realmente il rendimento: se è vera abilità del gestore (&alpha;) oppure mera esposizione a fattori sistematici noti.',
        'argus_calc': 'Regressione OLS multivariata su 252 o 500 sedute con serie storiche ufficiali dei fattori di Eugene Fama e Kenneth French.',
        'how_to_read': '• 🟢 &alpha; statisticamente significativo con p-value < 0.05 (Alpha autentico)<br>• 🟡 Rendimento spiegato da fattori di stile (es. tilt Value o Small Cap).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'xirr_pe': {
        'title': '💼 XIRR (Extended Internal Rate of Return - Private Equity & Illiquidi)',
        'what_is': 'Tasso interno di rendimento annualizzato calcolato su flussi di cassa irregolari nel tempo (Capital Calls, Distribuzioni e Valore Residuo NAV).',
        'how_calc': '&sum;<sub>i=1</sub><sup>N</sup> [ C<sub>i</sub> / (1 + XIRR)<sup>(d<sub>i</sub> &minus; d<sub>0</sub>)/365</sup> ] = 0',
        'why_useful': "Misurare la redditività reale di investimenti illiquidi, Private Equity, Real Estate e fondi chiusi considerando l'esatto momento temporale di ogni apporto/ritiro.",
        'argus_calc': 'Risoluzione iterativa con metodo Newton-Raphson su tutti i flussi di cassa datati registrati per ciascun deal o fondo illiquido.',
        'how_to_read': '• 🟢 XIRR > 15.0% (Rendimento eccellente in linea con benchmark Private Equity)<br>• 🟡 8.0% - 15.0% (Performance soddisfacente)<br>• 🔴 < 8.0% (Rendimento insufficiente per il premio al rischio di illiquidità).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'moic_pe': {
        'title': '💎 MOIC / TVPI (Multiple on Invested Capital / Total Value to Paid-In)',
        'what_is': "Il multiplo del capitale investito: rapporto tra il valore totale generato dall'investimento (distribuzioni incassate + valore residuo) e il capitale effettivamente versato.",
        'how_calc': '<b>MOIC (TVPI)</b> = (Distribuzioni Cumulative + NAV Residuo) / Capitale Totale Versato (Capital Calls)',
        'why_useful': 'Indicare quanti euro sono stati generati in termini assoluti per ogni singolo euro investito nel deal.',
        'argus_calc': 'Aggregazione istantanea di tutti i flussi di Private Equity, venture capital e collezionismo dal modulo Asset Illiquidi.',
        'how_to_read': '• 🟢 MOIC > 2.0x (Raddoppio del capitale investito)<br>• 🟡 1.3x - 2.0x (Crescita solida del capitale)<br>• 🔴 < 1.0x (Capitale in perdita rispetto al versato).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'dpi_pe': {
        'title': '💶 DPI (Distributed to Paid-In / Multiplo Realizzato)',
        'what_is': 'Il multiplo delle distribuzioni effettivamente restituite in contanti agli investitori rispetto al capitale versato.',
        'how_calc': '<b>DPI</b> = Distribuzioni Cumulative di Cassa / Capitale Totale Richiamato (Paid-In)',
        'why_useful': 'Misurare la quota di capitale e guadagni già trasformata in cassa reale sul conto corrente, eliminando le stime contabili del NAV.',
        'argus_calc': 'Rapporto tra la cassa bonificata agli investitori e il totale dei richiami di capitale conferiti.',
        'how_to_read': '• 🟢 DPI &ge; 1.0x (Il capitale iniziale è stato interamente recuperato in contanti: il NAV residuo è puro profitto)<br>• 🟡 In fase di disinvestimento ordinario<br>• 🔴 DPI basso in fondi vicini alla scadenza.',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'rvpi_pe': {
        'title': '📈 RVPI (Residual Value to Paid-In / NAV Residuo)',
        'what_is': 'Il rapporto tra il valore stimato del portafoglio ancora non venduto (NAV residuo) e il capitale totale versato.',
        'how_calc': '<b>RVPI</b> = NAV Residuo Non Realizzato / Capitale Totale Richiamato (Paid-In)',
        'why_useful': "Valutare il valore ancora 'in gioco' e non monetizzato all'interno del fondo o dell'investimento illiquido.",
        'argus_calc': "Valutazione dell'ultimo NAV certificato dal gestore rapportata al capitale storico versato.",
        'how_to_read': '• 🟢 Valore residuo solido con perizie conservative di mercato.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'carried_interest_gp': {
        'title': '💼 Carried Interest & Hurdle Rate (Private Equity GP)',
        'what_is': 'La quota di extra-profitto (generalmente il 20%) spettante al gestore (General Partner) subordinata al superamento del tasso minimo garantito di rendimento (Hurdle Rate).',
        'how_calc': '<b>Carried Interest</b> = max(0, Rendimento Totale &minus; Hurdle Rate) &times; 20%',
        'why_useful': "Comprendere l'allineamento di incentivi del gestore e calcolare l'esatto rendimento netto spettante all'investitore Limited Partner (LP).",
        'argus_calc': 'Applicazione del modello di waterfall europeo o americano registrato nella scheda contrattuale del deal.',
        'how_to_read': '• 🟢 Condizioni di waterfall trasparenti ed eque per gli investitori LP.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'interest_coverage_ratio': {
        'title': '⚖️ Interest Coverage Ratio (ICR / Copertura Oneri Finanziari)',
        'what_is': 'Il rapporto tra il margine operativo lordo (EBITDA) e gli interessi passivi dovuti sul debito.',
        'how_calc': '<b>ICR</b> = EBITDA / Oneri Finanziari (Interessi Passivi)',
        'why_useful': 'Verificare la capacità del deal o della società partecipata di pagare agevolmente gli interessi bancari con i propri flussi di cassa operativi.',
        'argus_calc': 'Estrapolato dai bilanci societari del deal nel modulo Asset Illiquidi e Private Debt.',
        'how_to_read': '• 🟢 ICR > 3.0x (Solida capacità di servizio del debito)<br>• 🟡 1.5x - 3.0x (Margine di sicurezza ridotto)<br>• 🔴 < 1.5x (Grave rischio di default sul debito o violazione dei covenants bancari).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'covenants_status': {
        'title': '📋 Stato Covenants Finanziari (Lending Covenants)',
        'what_is': 'La verifica del rispetto delle clausole contrattuali vincolanti pattuite con gli istituti di credito finanziatori (es. Leva Max Debt/EBITDA, ICR Minimo).',
        'how_calc': 'Confronto continuo tra i parametri di bilancio effettivi e i limiti di soglia contrattualmente stabiliti nel prestito.',
        'why_useful': 'Evitare la decadenza dal beneficio del termine o il rimborso accelerato forzato dei finanziamenti bancari.',
        'argus_calc': "Controllo automatico semaforico sui dati contabili dell'operazione.",
        'how_to_read': '• 🟢 Regolare (Tutti i covenants rispettati con ampio margine di sicurezza)<br>• 🔴 Breached (Violazione covenant con rischio di blocco della linea di credito).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'deducibilita_previdenziale': {
        'title': '🛡️ Deducibilità Fiscale Fondo Pensione (TUIR Art. 10)',
        'what_is': 'La quota di versamenti alla previdenza complementare deducibile dal reddito complessivo IRPEF fino al tetto annuo di € 5.164,57.',
        'how_calc': '<b>Deducibilità</b> = min(Versamenti Annui Effettuati, € 5.164,57)',
        'why_useful': "Abattere direttamente il reddito imponibile sull'aliquota marginale IRPEF più elevata (fino al 43%), ottenendo un rimborso fiscale immediato.",
        'argus_calc': "Tracciamento contabile dei contributi versati al fondo pensione nell'anno solare rispetto al plafond di legge.",
        'how_to_read': '• 🟢 € 5.164,57 (Plafond interamente sfruttato, massimo risparmio fiscale ottenuto)<br>• 🟡 Plafond parzialmente utilizzato<br>• 🔴 Nessun versamento effettuato (Occasione mancata di ottimizzazione fiscale).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'risparmio_irpef_previdenza': {
        'title': '💰 Risparmio Fiscale IRPEF da Previdenza',
        'what_is': 'Il risparmio monetario effettivo ottenuto in dichiarazione dei redditi grazie alla deduzione dei versamenti al fondo pensione.',
        'how_calc': '<b>Risparmio IRPEF</b> = Importo Deducibile Versato &times; Aliquota Marginale IRPEF (23%, 35% o 43%)',
        'why_useful': "Quantificare l'extra-rendimento immediato 'garantito dallo Stato' generato all'atto del versamento.",
        'argus_calc': 'Calcolo progressivo per scaglioni IRPEF sul reddito imponibile del contribuente.',
        'how_to_read': '• 🟢 Ottimizzazione IRPEF massima con risparmio fino a € 2.220 annui.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'rendita_vitalizia_stimata': {
        'title': '🛡️ Rendita Mensile Vitalizia Stimata (Annuity Estimate)',
        'what_is': "La stima dell'assegno mensile netto che il fondo pensione o l'ente previdenziale erogherà a vita a partire dall'età di pensionamento.",
        'how_calc': '<b>Rendita Mensile</b> = [ Montante Finale Accumulato &times; Coefficiente di Trasformazione Attuariale ] / 12',
        'why_useful': 'Verificare la sostenibilità del tenore di vita atteso durante la pensione e dimensionare il gap di reddito futuro.',
        'argus_calc': 'Algoritmo attuariale integrato con le tabelle di longevità ISTAT e coefficienti INPS/Covip ufficiali.',
        'how_to_read': '• 🟢 Assegno previsto adeguato a coprire le spese mensili di vita attese.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'fire_number': {
        'title': '🔥 FIRE Number & Indipendenza Finanziaria (Financial Independence Target)',
        'what_is': 'Il patrimonio complessivo necessario per vivere indefinitamente di rendita passiva senza più bisogno di reddito da lavoro dipendente o autonomo.',
        'how_calc': '<b>FIRE Target</b> = Spese Annue Desiderate / SWR = Spese Annue &times; 25 (con SWR = 4%)',
        'why_useful': "Fissare un obiettivo patrimoniale chiaro e calcolare l'esatta data stimata di libertà finanziaria (Freedom Date) in base al tasso di risparmio e rendimento atteso.",
        'argus_calc': 'Motore attuariale Monte Carlo che simula inflazione, longevità e sequenza dei rendimenti per stimare la probabilità di successo FIRE a 30-50 anni.',
        'how_to_read': '• 🟢 Patrimonio Netto &ge; 100% del FIRE Target (Indipendenza finanziaria raggiunta!)<br>• 🟡 50% - 99% (Fase avanzata di accumulazione)<br>• 🔴 < 50% (Fase iniziale: massimizzare tasso di risparmio e rendimento composto).',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'swr_fire': {
        'title': '🛡️ Safe Withdrawal Rate (SWR / Tasso di Prelievo Sicuro)',
        'what_is': "La percentuale massima di patrimonio che può essere prelevata ogni anno (adeguata all'inflazione) senza rischiare di esaurire il capitale prima del termine della vita.",
        'how_calc': '<b>Prelievo Anno 1</b> = Patrimonio &times; SWR (es. 3.5% - 4.0%)<br><b>Anni Successivi:</b> Prelievo Anno Prec. &times; (1 + Inflazione)',
        'why_useful': 'Pianificare la fase di decumulo del capitale durante la pensione o il prepensionamento evitando il rischio di longevità.',
        'argus_calc': "Stress test stocastico sul Sequence of Returns Risk (SRR) per calibrare lo SWR ideale in base all'allocazione azionaria/obbligazionaria.",
        'how_to_read': '• 🟢 3.0% - 3.5% (Ultra-conservativo e sicuro per orizzonti > 35 anni)<br>• 🟡 3.5% - 4.0% (Standard Trinity Study per 30 anni)<br>• 🔴 > 4.5% (Elevato rischio di esaurimento del capitale in scenari di crisi iniziale).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'dynamic_fire_swr': {
        'title': '🛡️ Dynamic FIRE SWR (Prelievo Adattivo Guyton-Klinger)',
        'what_is': "Tasso di prelievo flessibile che si adatta automaticamente all'andamento reale dei mercati con regole di cut o boost per proteggere il capitale.",
        'how_calc': 'Regole di Guyton-Klinger: riduzione del prelievo del 10% se il portafoglio subisce un drawdown severo; incremento se il portafoglio cresce oltre soglia.',
        'why_useful': 'Aumentare del 30% la sostenibilità del capitale rispetto a una regola rigida di prelievo costante.',
        'argus_calc': 'Simulazione rolling integrata con lo stato di shock del portafoglio patrimoniale.',
        'how_to_read': '• 🟢 Tasso adattivo perfettamente calibrato sulla capacità di spesa corrente.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'tempo_liberta': {
        'title': '⏳ Tempo alla Libertà Finanziaria (Years to FIRE)',
        'what_is': "Il numero di anni stimati necessari per raggiungere il Target FIRE Number mantenendo l'attuale tasso di risparmio e rendimento di portafoglio.",
        'how_calc': "Risoluzione dell'equazione di accumulo composto: <b>Target = Valore Attuale &times; (1+r)<sup>t</sup> + Risparmio Annuo &times; [((1+r)<sup>t</sup> &minus; 1)/r]</b>",
        'why_useful': "Trasformare l'obiettivo astratto dell'indipendenza finanziaria in una scadenza temporale concreta e monitorabile.",
        'argus_calc': "Calcolo deterministico e probabilistico Monte Carlo aggiornato mensilmente in base all'evoluzione del patrimonio.",
        'how_to_read': '• 🟢 Riduzione costante degli anni residui (Traiettoria virtuosa verso la libertà finanziaria).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'anti_forced_selling': {
        'title': '🛡️ Fondo Anti-Forced Selling (Cuscinetto Anti-Liquidazione)',
        'what_is': 'Riserva di cassa e strumenti a breve termine dedicata a finanziare le spese di vita durante i bear market, evitando di vendere azioni a sconto.',
        'how_calc': '<b>Fondo</b> = Spese Annue di Prelievo &times; Anni di Copertura Bear Market (tipicamente 2 - 3 anni)',
        'why_useful': 'Neutralizzare completamente il Sequence of Returns Risk nei primi anni di decumulo patrimoniale.',
        'argus_calc': 'Allocazione mirata in liquidità e titoli governativi a brevissimo termine (0-12 mesi).',
        'how_to_read': '• 🟢 &ge; 24 mesi coperti (Portafoglio interamente protetto contro bear market prolungati).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'success_probability_index': {
        'title': '🎲 Success Probability Index (SPI / Monte Carlo FIRE)',
        'what_is': "La frazione percentuale di traiettorie stocastiche simulate in cui il patrimonio non si esaurisce prima della fine dell'orizzonte di vita pianificato.",
        'how_calc': '<b>SPI</b> = (Numero Simulazioni con Capitale Residuo Finale > € 0 / Totale Simulazioni Monte Carlo) &times; 100',
        'why_useful': 'Verificare la solidità statistica del piano di prepensionamento a fronte di inflazione imprevista o mercati sfavorevoli.',
        'argus_calc': '1,000 traiettorie Monte Carlo con campionamento bootstrap dei rendimenti storici e cicli inflattivi.',
        'how_to_read': '• 🟢 SPI &ge; 85% - 95% (Piano finanziario robusto e sicuro)<br>• 🟡 75% - 85% (Accettabile con flessibilità di spesa)<br>• 🔴 < 75% (Piano fragile: ridurre il prelievo o aumentare il capitale iniziale).',
        'limitations': "Modello stocastico basato su ipotesi di longevità attuariale, inflazione costante e rendimenti attesi. Non garantisce l'invarianza del potere d'acquisto in caso di iperinflazione o shock regolamentari sui sistemi previdenziali pubblici.",
    },
    'tco_fee_drag': {
        'title': '💸 TCO & Fee Drag (Costo Totale di Possesso e Drag Commissionale)',
        'what_is': "L'impatto economico complessivo delle commissioni (TER fondi, costi di gestione, performance fees, costi di custodia) sull'accumulazione patrimoniale a 20-30 anni.",
        'how_calc': '<b>Capitale Perso per Fee Drag</b> = V<sub>finale</sub>(senza costi) &minus; V<sub>finale</sub>(con costi TCO)',
        'why_useful': 'Evidenziare come una commissione apparentemente piccola (es. 2.0% annuo di fondi attivi) possa erodere oltre il 40% del capitale finale rispetto a ETF low-cost (0.15%).',
        'argus_calc': "Simulatore Monte Carlo TCO che calcola l'impatto composto netto e la differenza di rendimento finale per ciascuna linea d'investimento.",
        'how_to_read': '• 🟢 TCO < 0.30% annuo (Ottima efficienza con ETF passivi)<br>• 🟡 0.30% - 1.00% (Accettabile per strategie bilanciate)<br>• 🔴 > 1.50% annuo (Fee drag distruttivo: convertire verso strumenti efficienti).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'estate_planning': {
        'title': '⚖️ Estate Planning & Ottimizzazione Successoria (Passaggio Generazionale)',
        'what_is': 'Analisi della devoluzione del patrimonio ereditario in base al diritto civile italiano (quote di legittima e disponibile) e calcolo delle imposte di successione/donazione.',
        'how_calc': '<b>Imposta Successione (Coniuge/Figli)</b> = max(0, Asse Ereditario &minus; Franchigia € 1.000.000) &times; 4%<br><b>Imposta Donazione Fratelli:</b> max(0, Asse &minus; Franchigia € 100.000) &times; 6%',
        'why_useful': 'Pianificare il passaggio generazionale, tutelare gli eredi legittimari ed evitare liti familiari o un carico fiscale punitivo.',
        'argus_calc': 'Algoritmo di simulazione asse ereditario con verifica quote di riserva, applicazione franchigie di legge ed esenzione per Titoli di Stato e Polizze Vita Caso Morte.',
        'how_to_read': '• 🟢 Asse ereditario capiente entro le franchigie (Zero imposte dovute)<br>• 🟡 Imposta successoria contenuta con strumenti esenti attivi<br>• 🔴 Lesione potenziale di legittima o carico fiscale elevato da ottimizzare.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'drawdown_medio_stress': {
        'title': '🌪️ Drawdown Medio su Scenari di Crash Storici',
        'what_is': 'La flessione percentuale media attesa del portafoglio qualora si ripetessero i 5 peggiori shock sistemici della storia recente (2008 Lehman, 2020 Covid, 2000 Dot-com, 2022 Inflazione, 1987 Black Monday).',
        'how_calc': '<b>Drawdown Medio Stress</b> = (1/K) &sum; &Delta;V<sub>Scenario k</sub> / V<sub>0</sub>',
        'why_useful': 'Testare la tenuta del portafoglio a eventi rari e devastanti non catturati dai modelli statistici gaussiani ordinari.',
        'argus_calc': 'Riproiezione dei pesi attuali sulle serie temporali storiche effettive delle giornate di crash.',
        'how_to_read': '• 🟢 < 15.0% (Elevata resilienza difensiva contro crisi sistemiche)<br>• 🟡 15.0% - 25.0% (In linea con un profilo bilanciato standard)<br>• 🔴 > 30.0% (Forte vulnerabilità: rischio di shock severo sul capitale).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'alpha_difensivo_stress': {
        'title': '🛡️ Alpha Difensivo Medio (Differenziale di Resilienza)',
        'what_is': 'Il differenziale medio tra la perdita subita dal portafoglio rispetto alla caduta del mercato di riferimento (S&P 500 / MSCI World) durante i crash simulati.',
        'how_calc': '<b>Alpha Difensivo</b> = Perdita Benchmark &minus; Perdita Portafoglio',
        'why_useful': 'Misurare quanto il portafoglio attenua e protegge il capitale durante le tempeste finanziarie rispetto a una replica passiva di mercato.',
        'argus_calc': 'Differenziale di performance calcolato punto per punto su ciascuno scenario di stress normativo e storico.',
        'how_to_read': '• 🟢 Alpha Difensivo > +10.0% (Protezione eccezionale del capitale nei bear market).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'worst_stress_scenario': {
        'title': '🌪️ Scenario di Stress Più Severo',
        'what_is': 'Lo scenario macroeconomico o storico che infligge la massima perdita percentuale al portafoglio in base alla sua specifica composizione.',
        'how_calc': 'Identificazione dello scenario k tale che <b>Perdita(k) = max(|Perdita|)</b> tra tutti gli stress test eseguiti.',
        'why_useful': 'Conoscere il proprio punto debole principale (es. shock tassi, crollo azionario globale o shock valutario) per predisporre eventuali coperture.',
        'argus_calc': 'Scansione multidimensionale su tutti gli scenari storici, ipotetici e macroeconomici censiti.',
        'how_to_read': "• 🟢 Perdita massima sopportabile dal profilo di rischio dell'investitore.",
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'point_of_forced_liquidation': {
        'title': '⏳ Point of Forced Liquidation (t* / Tempo a Liquidazione Forzata)',
        'what_is': 'Il momento temporale esatto (in mesi) in cui, in uno scenario di stress combinato (crollo mercati + azzeramento reddito), la cassa si azzera costringendo a liquidare investimenti in perdita.',
        'how_calc': 'Istante t* in cui <b>Liquidità Residua(t*) = 0</b> sotto stress con cashflow operativo negativo.',
        'why_useful': 'Individuare la soglia temporale oltre la quale scatta il danno economico permanente della vendita forzata.',
        'argus_calc': 'Simulazione deterministica mensilizzata di cash burn sotto shock combinato.',
        'how_to_read': '• 🟢 t* > 24 mesi o non applicabile (Resistenza prolungata, zero rischio di forced selling)<br>• 🔴 t* < 6 mesi (Pericolo critico di liquidazione forzata in fase di ribasso).',
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'liquidity_squeeze_deficit': {
        'title': '💧 Deficit di Liquidità in Scenario di Stress',
        'what_is': "L'ammontare monetario mancante per onorare le uscite obbligatorie e le rate di debito durante il periodo di stress analizzato.",
        'how_calc': '<b>Deficit</b> = max(0, Uscite Obbligatorie Periodo &minus; Liquidità Iniziale &minus; Entrate Periodo)',
        'why_useful': "Dimensionare esattamente l'iniezione di liquidità o la riserva monetaria necessaria per rendere il patrimonio a prova di shock.",
        'argus_calc': 'Stress test continuo sui saldi di cassa a fronte di cali del reddito dal 20% al 100%.',
        'how_to_read': "• 🟢 € 0 (Nessun deficit: cassa sufficiente ad assorbire l'intero shock simulato).",
        'limitations': 'Metrica basata su perizie e valutazioni periodiche del NAV stimate dal gestore (General Partner) e soggette a lag temporale (appraisal lag) e smoothing artificiale della volatilità.',
    },
    'mutuo_rata_impact': {
        'title': '📈 Impatto Rialzo Tassi su Rata Mutuo (Rate Shock)',
        'what_is': 'La variazione monetaria della rata mensile del mutuo a tasso variabile in caso di aumento dei tassi interbancari Euribor (+100, +200 o +300 bps).',
        'how_calc': "Ricalcolo del piano di ammortamento alla francese con tasso <b>i' = i + &Delta;Euribor</b>.",
        'why_useful': 'Verificare se il proprio reddito mensile è in grado di assorbire aumenti della rata senza compromettere il risparmio o richiedere surroga a tasso fisso.',
        'argus_calc': 'Simulatore di piano di ammortamento con debito residuo effettivo e durata rimanente.',
        'how_to_read': '• 🟢 Impatto contenuto (< 10% della rata originaria) o mutuo a tasso fisso (impatto zero).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'proceeds_cash_in': {
        'title': '💶 Controvalore Incassato (Proceeds / Cash-In)',
        'what_is': "L'importo monetario totale incassato sul conto corrente in seguito alla vendita, liquidazione o chiusura di posizioni finanziarie o beni.",
        'how_calc': '<b>Controvalore</b> = &sum; (Prezzo di Esecuzione &times; Quantità Venduta &times; FX) &minus; Commissioni di Vendita',
        'why_useful': "Verificare la liquidità netta effettivamente resa disponibile dall'operazione per nuovi investimenti o prelievi.",
        'argus_calc': 'Certificato dalla contabile di negoziazione al netto di commissioni di brokeraggio e ritenute fiscali applicate alla fonte.',
        'how_to_read': '• 🟢 Liquidità prontamente accreditata sul conto di regolamento.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'value_variation': {
        'title': '📊 Variazione di Controvalore Assoluto (&Delta; Valore €)',
        'what_is': "La variazione monetaria in euro del valore di una posizione, conto o portafoglio tra due istanti temporali o a seguito di un'operazione.",
        'how_calc': '<b>&Delta; Valore</b> = Controvalore Finale &minus; Controvalore Iniziale',
        'why_useful': "Misurare l'impatto economico nominale in termini di euro guadagnati o persi.",
        'argus_calc': 'Differenziale calcolato sui controvalori mark-to-market certificati.',
        'how_to_read': '• 🟢 Variazione Positiva (Incremento di valore nominale)<br>• 🔴 Variazione Negativa (Flessione o riduzione del controvalore).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'weight_variation': {
        'title': '⚖️ Variazione di Peso Percentuale (&Delta; Peso %)',
        'what_is': 'La variazione della percentuale di allocazione di un asset rispetto al valore totale del portafoglio.',
        'how_calc': '<b>&Delta; Peso</b> = Peso Finale (%) &minus; Peso Iniziale (%)',
        'why_useful': 'Monitorare le derive di allocazione (drift) e guidare le operazioni di ribilanciamento periodico.',
        'argus_calc': "Rapporto tra controvalore dell'asset e controvalore complessivo di portafoglio a ciascuna data.",
        'how_to_read': '• 🟢 Entro i corridoi di tolleranza prefissati (es. &plusmn; 2.0%).',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'interest_saved_debt': {
        'title': '💰 Interessi Risparmiati su Debiti (Interest Saved)',
        'what_is': "L'ammontare monetario totale di interessi passivi non pagati grazie all'estinzione anticipata, ammortamento accelerato o rinegoziazione del debito.",
        'how_calc': '<b>Interessi Risparmiati</b> = Interessi Totali Piano Originario &minus; Interessi Effettivamente Corrisposti',
        'why_useful': "Misurare il rendimento garantito generato dall'estinzione dei debiti ad alto tasso di interesse.",
        'argus_calc': 'Confronto tra i flussi attualizzati dei piani di ammortamento pre e post estinzione.',
        'how_to_read': '• 🟢 Risparmio monetario certo a beneficio del patrimonio netto personale.',
        'limitations': "Assume la stabilità del quadro tributario italiano e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non tiene conto di eventuali future riforme fiscali retroattive o interpretazioni restrittive dell'Agenzia delle Entrate.",
    },
    'semantic_relevance': {
        'title': '🔍 Rilevanza Semantica AI (Semantic Relevance Score)',
        'what_is': "Il punteggio di similarità vettoriale tra la query dell'utente e i documenti societari, bilanci o trascrizioni analizzati dal modulo di ricerca semantica.",
        'how_calc': '<b>Cosine Similarity</b> = (<b>u</b> &middot; <b>v</b>) / ( ||<b>u</b>|| &times; ||<b>v</b>|| ) &nbsp;|&nbsp; <i>con embedding vettoriali</i>',
        'why_useful': 'Garantire che le risposte e i dati estratti dai bilanci societari siano fondati sui passaggi più pertinenti e autorevoli.',
        'argus_calc': 'Calcolo vettoriale tramite modello di embedding su database documentale indicizzato.',
        'how_to_read': "• 🟢 > 0.80 (Altissima pertinenza contestuale e attendibilità dell'informazione).",
        'limitations': 'La misura riflette i dati storici e contabili disponibili; non incorpora scenari sistemici esogeni non ancora riflessi nelle serie temporali o nei documenti ufficiali.',
    },
    'var_parametric_95': {
        'title': '🛡️ Value at Risk Parametrico 95% (Parametric Gaussian VaR)',
        'what_is': 'La massima perdita monetaria o percentuale attesa su un orizzonte di 1 giorno con un livello di confidenza statistica del 95%, assumendo che i rendimenti seguano una distribuzione Normale multivariata.',
        'how_calc': '<b>VaR<sub>95%, 1D</sub></b> = &minus;(&mu;<sub>daily</sub> &minus; 1.6449 &times; &sigma;<sub>port, daily</sub>) &nbsp;|&nbsp; <b>&sigma;<sub>port</sub></b> = &radic;(<b>w</b><sup>T</sup> &Sigma; <b>w</b>)',
        'why_useful': 'Fissare il limite prudenziale di perdita massima in condizioni ordinarie di mercato per calibrare liquidità di emergenza, margini di mantenimento e risk budgeting.',
        'argus_calc': 'Calcolato sui rendimenti percentuali discreti giornalieri R<sub>t</sub> = (P<sub>t</sub>/P<sub>t-1</sub>) - 1. Matrice di covarianza de-noised con shrinkage Ledoit-Wolf. Confidenza al 95% (z = 1.6449), orizzonte a 1 giorno lavorativo (base annua 252 sedute).',
        'how_to_read': '• 🟢 &lt; 1.50% (Rischio giornaliero contenuto e conservativo)<br>• 🟡 1.50% - 2.50% (Esposizione nella media per portafogli bilanciati)<br>• 🔴 &gt; 2.50% (Elevata vulnerabilità a shock giornalieri ordinari).',
        'limitations': "Punto cieco fondamentale: assume rendimenti distribuiti normalmente (code sottili), sottostimando drasticamente le perdite durante i crolli di borsa (Fat Tails). Non fornisce alcuna indicazione sull'entità della perdita oltre la soglia del 95%.",
    },
    'var_parametric_99': {
        'title': '🛡️ Value at Risk Parametrico 99% (Parametric Gaussian VaR 99%)',
        'what_is': 'La perdita massima potenziale a 1 giorno con livello di confidenza al 99% (standard regolamentare di Basilea per i requisiti minimi di capitale bancario).',
        'how_calc': '<b>VaR<sub>99%, 1D</sub></b> = &minus;(&mu;<sub>daily</sub> &minus; 2.3263 &times; &sigma;<sub>port, daily</sub>)',
        'why_useful': 'Utilizzato per stress testing normativo, allocazione del capitale di rischio istituzionale e verifica dei limiti di solvibilità.',
        'argus_calc': 'Rendimenti discreti giornalieri, covarianza campionaria de-noised con Ledoit-Wolf, z<sub>0.99</sub> = 2.3263, orizzonte 1D con convenzione a 252 sedute lavorative/anno.',
        'how_to_read': '• 🟢 &lt; 2.50% (Eccellente tenuta prudenziale)<br>• 🟡 2.50% - 4.00% (Rischio 99% standard per portafogli azionari)<br>• 🔴 &gt; 4.00% (Rischio estremo: 1 giorno su 100 può distruggere oltre il 4% del capitale).',
        'limitations': "L'ipotesi di normalità al 99% è ancora più fragile che al 95%: nella realtà dei mercati, eventi oltre 2.33 sigma si verificano molto più frequentemente di quanto previsto dalla curva di Gauss (leptocurtosi empirica).",
    },
    'var_historical_95': {
        'title': '📉 Value at Risk Storico 95% (Non-Parametric Historical VaR)',
        'what_is': 'La perdita potenziale al 95% di confidenza ricavata direttamente dal 5° percentile empirico della distribuzione dei rendimenti effettivi del portafoglio, senza assunzioni teoriche sulla forma distributiva.',
        'how_calc': '<b>VaR<sub>95%</sub><sup>Hist</sup></b> = &minus;Percentile<sub>5%</sub>({ R<sub>p, t</sub> }<sub>t=1</sub><sup>T</sup>)',
        'why_useful': 'Misura libera da assunzioni parametriche (model-free), ideale per confrontare il rischio effettivo con il VaR teorico e individuare divergenze da distribuzioni non gaussiane.',
        'argus_calc': 'Calcolato sui rendimenti percentuali lineari effettivi del portafoglio ricostruiti su una finestra storica di almeno 252 sedute lavorative. Cattura fedelmente asimmetria e code grasse storiche.',
        'how_to_read': '• 🟢 &lt; 1.60% (Basso rischio storico)<br>• 🟡 1.60% - 2.60% (Esposizione storica moderata)<br>• 🔴 &gt; 2.60% (Storico caratterizzato da frequenti perdite giornaliere severe).',
        'limitations': 'Assume che il futuro replichi la storia recente: non può prevedere shock di entità mai registrata nel campione storico (Black Swan) e assegna lo stesso peso agli eventi di 1 anno fa rispetto a quelli di ieri.',
    },
    'var_historical_99': {
        'title': '📉 Value at Risk Storico 99% (Non-Parametric Historical VaR 99%)',
        'what_is': 'La perdita al 99% di confidenza estratta dal 1° percentile empirico della serie storica dei rendimenti del portafoglio.',
        'how_calc': '<b>VaR<sub>99%</sub><sup>Hist</sup></b> = &minus;Percentile<sub>1%</sub>({ R<sub>p, t</sub> }<sub>t=1</sub><sup>T</sup>)',
        'why_useful': 'Validazione dei limiti massimi di perdita effettiva sperimentati dal portafoglio nelle giornate peggiori della cronologia storica.',
        'argus_calc': 'Percentile empirico (metodo lineare / interpolazione quantile) calcolato sulla serie storica dei rendimenti di portafoglio su 252+ giorni di negoziazione.',
        'how_to_read': '• 🟢 &lt; 2.80% (Massima perdita storica giornaliera contenuta)<br>• 🟡 2.80% - 4.50% (Volatilità di coda fisiologica)<br>• 🔴 &gt; 4.50% (Code storiche molto pesanti).',
        'limitations': 'Con 252 osservazioni, il 1° percentile si basa solo sulle 2-3 peggiori giornate: elevato errore di campionamento (sampling error) che richiede serie storiche pluriennali (&gt; 500-1000 giorni) per essere statisticamente robusto.',
    },
    'var_cornish_fisher': {
        'title': '📐 Cornish-Fisher Modified VaR (Asimmetria & Curtosi)',
        'what_is': "Estensione analitica del VaR gaussiano che corregge il quantile normale tramite l'espansione di Cornish-Fisher, incorporando l'asimmetria (Skewness S) e la curtosi in eccesso (Kurtosis K) empiriche della distribuzione.",
        'how_calc': '<b>z<sub>CF</sub></b> = z<sub>&alpha;</sub> + (1/6)(z<sub>&alpha;</sub><sup>2</sup>&minus;1)S + (1/24)(z<sub>&alpha;</sub><sup>3</sup>&minus;3z<sub>&alpha;</sub>)K &minus; (1/36)(2z<sub>&alpha;</sub><sup>3</sup>&minus;5z<sub>&alpha;</sub>)S<sup>2</sup> &nbsp;|&nbsp; <b>VaR<sub>CF</sub></b> = &minus;(&mu; &minus; z<sub>CF</sub> &times; &sigma;)',
        'why_useful': 'Fornisce una stima del rischio analitica superiore al VaR gaussiano quando il portafoglio contiene asset con asimmetria negativa pronunciata (es. crypto, opzioni short, strategie momentum).',
        'argus_calc': "ARGUS applica guard-rails di monotonicità stringenti nel modulo core/risk_engine.py: Skewness limitato in [-3.0, 3.0] e Excess Kurtosis in [-1.0, 10.0] per prevenire l'inversione di quantili. Rendimenti lineari, orizzonte 1D.",
        'how_to_read': '• 🟢 VaR CF &asymp; VaR Parametrico (Distribuzione simmetrica, assenza di asimmetria dannosa)<br>• 🟡 VaR CF &gt; VaR Parametrico (+10-30%: presenza di code grasse da monitorare)<br>• 🔴 VaR CF &gt;&gt; VaR Parametrico (&gt; +40%: rischio di coda estremo non catturato dai modelli standard).',
        'limitations': 'In presenza di asimmetria o curtosi estreme (es. shock superiori a 15 deviazioni standard), il polinomio di Cornish-Fisher può perdere la monotonicità locale, motivo per cui ARGUS applica il clamping sui momenti statistici superiori.',
    },
    'var_monte_carlo': {
        'title': '🎲 Monte Carlo VaR (Cholesky Simulation & Shrinkage)',
        'what_is': 'Stima probabilistica del Value at Risk ottenuta generando da 1.000 a 10.000 traiettorie stocastiche di rendimento dei singoli asset correlate tramite decomposizione di Cholesky della matrice di covarianza.',
        'how_calc': '<b>R<sub>sim</sub></b> = &mu;&Delta;t + <b>L</b> <b>Z</b> &radic;&Delta;t &nbsp;|&nbsp; con &Sigma; = <b>L</b><b>L</b><sup>T</sup>, <b>Z</b> &sim; &Nu;(<b>0</b>, <b>I</b>)',
        'why_useful': 'Permette di modellare strutture di portafoglio complesse, pay-off non lineari (opzioni e derivati) e scenari multi-orizzonte (10D, 1Y).',
        'argus_calc': 'Decomposizione di Cholesky applicata alla matrice di covarianza de-noised con Ledoit-Wolf Shrinkage (semi-definitezza positiva garantita). Simula 1.000+ percorsi sintetici e ricava il VaR come quantile empirico.',
        'how_to_read': '• 🟢 Consistente con il VaR Storico (Modello stocastico calibrato ed equilibrato)<br>• 🔴 Divergenza &gt; 25% (Presenza di non linearità o correlazioni complesse che richiedono più iterazioni).',
        'limitations': 'Richiede elevata potenza computazionale. La simulazione standard assume correlazioni costanti e invarianza distributiva durante il percorso, non catturando il breakdown delle correlazioni nei crash improvvisi di liquidità.',
    },
    'cvar_expected_shortfall': {
        'title': '🛡️ CVaR / Expected Shortfall (Rischio Coerente di Coda)',
        'what_is': "La perdita media attesa in tutte le giornate in cui la perdita del portafoglio supera la soglia critica del Value at Risk. È una misura di rischio 'coerente' (Artzner et al. 1999) che rispetta l'assioma della sub-additività.",
        'how_calc': '<b>CVaR<sub>&alpha;</sub></b> = &minus;E[ R<sub>p</sub> | R<sub>p</sub> &le; &minus;VaR<sub>&alpha;</sub> ] = [1 / (1 &minus; &alpha;)] &int;<sub>0</sub><sup>1&minus;&alpha;</sup> VaR<sub>u</sub> du',
        'why_useful': "Risolve il fallimento principale del VaR: quantifica 'quanto si perde in media quando le cose vanno davvero male', catturando la gravità effettiva dei crolli di borsa.",
        'argus_calc': 'Calcolato come media aritmetica dei rendimenti che si collocano al di sotto del quantile del VaR (approccio storico empirico non parametrico su 252+ sedute), affiancato dalle varianti analitiche gaussiane e Cornish-Fisher.',
        'how_to_read': '• 🟢 CVaR &lt; 2.50% (Code sottili, basso rischio di crash sistemico)<br>• 🟡 CVaR 2.50% - 4.50% (Rischio di coda nella norma per asset azionari)<br>• 🔴 CVaR &gt; 4.50% (Code grasse e grave vulnerabilità a cigni neri sistemici).',
        'limitations': 'Dipende fortemente dal numero di osservazioni nella coda estrema: su un campione ridotto di 252 giorni, il CVaR al 99% si basa sulla media di sole 2 o 3 osservazioni, rendendolo sensibile a singoli outlier storici.',
    },
    'garch_volatility': {
        'title': '⚡ Volatilità Condizionale GARCH(1,1) & FHS',
        'what_is': "Stima della volatilità dinamica tempo-variante (Bollerslev 1986) che cattura i cluster di volatilità (alta volatilità genera alta volatilità) e l'evoluzione condizionale one-step-ahead &sigma;<sub>t+1</sub>.",
        'how_calc': '<b>&sigma;<sub>t</sub><sup>2</sup></b> = &omega; + &alpha; &epsilon;<sub>t-1</sub><sup>2</sup> + &beta; &sigma;<sub>t-1</sub><sup>2</sup> &nbsp;|&nbsp; <i>vincolo di stazionarietà:</i> &alpha; + &beta; &lt; 1',
        'why_useful': "Reagisce tempestivamente all'insorgere di shock recenti, superando l'inerzia della volatilità storica a finestra mobile che impiega settimane per recepire una crisi in atto.",
        'argus_calc': 'Ottimizzazione di Massima Verosimiglianza (MLE) su serie storica dei rendimenti giornalieri. ARGUS stima (&omega;, &alpha;, &beta;), verifica la stazionarietà (&alpha; + &beta; &lt; 1) e proietta la volatilità per la Filtered Historical Simulation (FHS).',
        'how_to_read': '• 🟢 &sigma;<sub>GARCH</sub> &lt; &sigma;<sub>storica</sub> (Fase di compressione di volatilità, mercato tranquillo)<br>• 🟡 &alpha; + &beta; &asymp; 0.95 - 0.98 (Persistenza elevata della volatilità)<br>• 🔴 &sigma;<sub>GARCH</sub> &gt;&gt; &sigma;<sub>storica</sub> (Spike di volatilità in corso: ridurre la leva).',
        'limitations': "Il modello standard GARCH(1,1) assume simmetria di risposta agli shock positivi e negativi; non cattura l'effetto leva asimmetrico (in cui i ribassi aumentano la volatilità più dei rialzi), a meno di estensioni come EGARCH o GJR-GARCH.",
    },
    'tail_risk_index': {
        'title': '⚖️ Tail Risk Index & Asimmetria delle Code (Tail Ratio)',
        'what_is': "Rapporto tra l'ampiezza della coda positiva dei guadagni (95° percentile) e l'ampiezza della coda negativa delle perdite (5° percentile in valore assoluto).",
        'how_calc': '<b>Tail Ratio</b> = Q<sub>0.95</sub>(R<sub>p</sub>) / | Q<sub>0.05</sub>(R<sub>p</sub>) |',
        'why_useful': "Valutare se il portafoglio ha un'asimmetria positiva (i guadagni estremi superano le perdite estreme) o se è esposto a strategie asimmetriche negative pericolose.",
        'argus_calc': "Calcolato sui percentili empirici a 252 sedute dei rendimenti lineari di portafoglio. Misura l'asimmetria reale del profilo di payoff senza assumere alcuna curva analitica.",
        'how_to_read': '• 🟢 &gt; 1.15 (Asimmetria positiva: la coda dei guadagni è più lunga di quella delle perdite)<br>• 🟡 0.90 - 1.15 (Profilo simmetrico bilanciato)<br>• 🔴 &lt; 0.90 (Asimmetria negativa pericolosa: le perdite estreme superano sistematicamente i guadagni).',
        'limitations': 'Come tutte le metriche basate su quantili estremi, richiede una cronologia sufficientemente estesa per evitare che pochi eventi fortuiti distorcano il rapporto.',
    },
    'treynor_ratio': {
        'title': '🏛️ Treynor Ratio (Rendimento / Rischio Sistematico Beta)',
        'what_is': "Indice di performance (Jack Treynor 1965) che misura l'extra-rendimento per unità di rischio non diversificabile (Beta sistematico di mercato) invece del rischio totale.",
        'how_calc': '<b>Treynor</b> = (&mu;<sub>ann</sub> &minus; R<sub>f, ann</sub>) / &beta;<sub>mercato</sub>',
        'why_useful': 'Valutare la performance di un portafoglio che fa parte di una struttura di allocazione più ampia e già ampiamente diversificata, dove il rischio specifico dei singoli titoli è neutralizzato.',
        'argus_calc': 'Rendimenti annualizzati a 252 giorni, tasso R<sub>f</sub> live armonizzato e Beta calcolato tramite regressione OLS contro il benchmark di mercato prescelto.',
        'how_to_read': '• 🟢 Valore superiore al premio per il rischio del mercato (R<sub>m</sub> &minus; R<sub>f</sub>)<br>• 🟡 In linea con il benchmark di mercato<br>• 🔴 Inferiore al mercato o negativo (Rischio sistematico non remunerato).',
        'limitations': 'Assume che il portafoglio sia perfettamente diversificato; se il portafoglio è concentrato su pochi titoli, il Treynor ignora totalmente il rischio specifico (non sistematico).',
    },
    'average_drawdown': {
        'title': '📉 Drawdown Medio (Average Drawdown Depth)',
        'what_is': 'La profondità percentuale media di tutte le fasi correttive distinte sperimentate dal portafoglio al di sotto del picco massimo storico.',
        'how_calc': '<b>Avg DD</b> = (1 / K) &sum;<sub>k=1</sub><sup>K</sup> Trough Depth<sub>k</sub>',
        'why_useful': "Fornisce all'investitore l'aspettativa realistica dell'ampiezza delle normali oscillazioni negative ricorrenti, evitando panico ingiustificato durante le ordinarie correzioni di percorso.",
        'argus_calc': 'Identificazione automatica di tutti i cicli completi di correzione e recupero (Peak-to-Trough) e calcolo della media aritmetica della flessione di ciascuna valle.',
        'how_to_read': '• 🟢 &lt; 4.0% (Ritracciamenti medi molto contenuti)<br>• 🟡 4.0% - 8.0% (Normale correzione di mercato)<br>• 🔴 &gt; 8.0% (Correzioni ricorrenti profonde: necessaria revisione della diversificazione).',
        'limitations': 'Non tiene conto della durata temporale delle correzioni, ma unicamente della loro profondità percentuale al punto di minimo.',
    },
    'recovery_time': {
        'title': '⏳ Tempo Medio di Recupero (Underwater Duration & Recovery Days)',
        'what_is': 'Il numero medio di giorni di calendario o lavorativi trascorsi tra il punto di minimo (valle) di un drawdown e il recupero completo del precedente picco massimo (High-Water Mark).',
        'how_calc': '<b>Recovery Time</b> = (1 / K) &sum;<sub>k=1</sub><sup>K</sup> (t<sub>recupero, k</sub> &minus; t<sub>valle, k</sub>)',
        'why_useful': 'Calibrare la liquidità nel conto economico personale: sapere quanti mesi mediamente il portafoglio impiega a riassorbire un calo impedisce di disinvestire forzatamente in perdita.',
        'argus_calc': "Scansione della cronologia dell'equity curve registrando data di picco, data di fondo e data di breakout del nuovo massimo, misurando la durata sia della discesa che della risalita.",
        'how_to_read': '• 🟢 &lt; 90 giorni (Recupero tempestivo della ricchezza)<br>• 🟡 90 - 270 giorni (Finestra di recupero ciclica ordinaria)<br>• 🔴 &gt; 365 giorni (Drawdown pluriennali: elevato rischio di impazienza o necessità di liquidità).',
        'limitations': "In fasi di correzione in corso (drawdown attivo), il tempo di recupero non è ancora calcolabile e viene riportato solo il tempo parziale 'underwater' cumulato.",
    },
    'r_squared': {
        'title': '📊 R-Quadro & Coerenza di Stile (Coefficient of Determination R²)',
        'what_is': 'La percentuale della varianza totale dei rendimenti del portafoglio che viene spiegata e guidata direttamente dalle fluttuazioni del benchmark di mercato prescelto.',
        'how_calc': '<b>R<sup>2</sup></b> = Var(Modello) / Var(Totale) = &rho;<sub>p, b</sub><sup>2</sup>',
        'why_useful': 'Validare la significatività di Alpha e Beta: se R<sup>2</sup> è basso (&lt; 0.60), il benchmark scelto non è rappresentativo e le stime di Alpha e Beta non sono statisticamente affidabili.',
        'argus_calc': 'Quadrato del coefficiente di correlazione lineare di Pearson tra i rendimenti giornalieri di portafoglio e benchmark su 252+ giorni di borsa.',
        'how_to_read': '• 🟢 &gt; 0.85 (Portafoglio strettamente allineato al benchmark, Alpha e Beta solidi)<br>• 🟡 0.60 - 0.85 (Buona correlazione con componenti attive autonome)<br>• 🔴 &lt; 0.60 (Disallineamento dal benchmark: cambiare indice di riferimento).',
        'limitations': "Non indica se la performance è buona o cattiva, ma solo quanto strettamente il portafoglio segue la direzione dell'indice.",
    },
    'correlation_distance': {
        'title': '🌐 Distanza di Correlazione (Correlation Matrix Distance)',
        'what_is': 'Metrica di distanza matematica tra coppie di asset basata sul coefficiente di correlazione di Pearson &rho;<sub>ij</sub>, essenziale per gli algoritmi di cluster analysis e machine learning.',
        'how_calc': '<b>d<sub>ij</sub></b> = &radic;[ 0.5 &times; (1 &minus; &rho;<sub>ij</sub>) ] &nbsp;|&nbsp; <i>con d<sub>ij</sub> &isin; [0, 1]</i>',
        'why_useful': 'Costruire alberi gerarchici di clustering (dendrogrammi) che raggruppano asset con comportamento economico simile ed evidenziano le reali fonti di diversificazione.',
        'argus_calc': 'Implementata nel modulo core/hrp_optimizer.py per convertire la matrice di correlazione de-noised in uno spazio metrico euclideo valido, rispettando le proprietà di riflessività, simmetria e disuguaglianza triangolare.',
        'how_to_read': '• 🟢 d<sub>ij</sub> &gt; 0.85 (&rho; &lt; -0.45: diversificazione e decorrelazione eccellente)<br>• 🟡 d<sub>ij</sub> &asymp; 0.71 (&rho; &asymp; 0: indipendenza statistica)<br>• 🔴 d<sub>ij</sub> &lt; 0.40 (&rho; &gt; +0.70: asset quasi identici, falsa diversificazione).',
        'limitations': 'Cattura solo la dipendenza lineare tra asset; non rileva dipendenze non lineari complesse o asimmetrie durante le fasi di stress.',
    },
    'net_worth_consolidated': {
        'title': '🏛️ Patrimonio Netto Consolidato (Consolidated Net Worth)',
        'what_is': 'Il valore economico complessivo di tutte le attività possedute al netto di tutte le passività finanziarie e debiti residui secondo standard contabili CFP/IFRS.',
        'how_calc': '<b>Net Worth</b> = Totale Attivo &minus; Totale Passività = (Cassa + Investimenti + Caveau + Immobili + Previdenza) &minus; Passività',
        'why_useful': 'Rappresenta la metrica fondamentale della ricchezza reale al di là dei flussi transitori di reddito: è la base di ogni piano di indipendenza finanziaria.',
        'argus_calc': 'Consolidamento multi-conto continuo in EUR con conversione cambi BCE live, rivalutazione mark-to-market degli asset e ammortamento continuo dei debiti residui.',
        'how_to_read': "• 🟢 Trend crescente costante superiore all'inflazione<br>• 🟡 Stabile durante fasi di riallocazione o investimenti primari<br>• 🔴 Trend decrescente prolungato (Overspending o drawdown prolungato degli asset).",
        'limitations': 'Include stime di mercato su beni non liquidi (immobili, collezionismo) che possono differire dal prezzo effettivo di rapido realizzo in caso di vendita forzata.',
    },
    'liquid_net_worth': {
        'title': '💧 Patrimonio Netto Liquido (Liquid Net Worth)',
        'what_is': 'La porzione di ricchezza netta convertibile in contanti entro 5-10 giorni lavorativi senza subire sconti sul valore di mercato (esclude prima casa, immobili fisici e collezionismo).',
        'how_calc': '<b>Liquid Net Worth</b> = (Liquidità + Strumenti Finanziari Quotati) &minus; Debiti a Breve Termine',
        'why_useful': 'Valutare la reale capacità di risposta a opportunità di investimento improvvise o a shock gravi senza dover liquidare la propria abitazione o asset strategici.',
        'argus_calc': 'Somma saldi bancari, ETF monetari, obbligazioni e azioni liquide quotate nel modulo investimenti, detraendo i debiti esigibili entro 12 mesi.',
        'how_to_read': "• 🟢 &gt; 35% del Patrimonio Netto Totale (Elevata flessibilità e reattività strategica)<br>• 🟡 15% - 35% (Equilibrio standard tra rendimento e liquidità)<br>• 🔴 &lt; 15% (Eccessiva immobilizzazione: rischio di 'wealth rich but cash poor').",
        'limitations': 'In fasi di prolungato bear market, il valore dei titoli quotati si comprime riducendo il patrimonio liquido proprio quando la liquidità diventa più preziosa.',
    },
    'emergency_runway': {
        'title': '⏳ Runway di Emergenza (Mesi di Autonomia Finanziaria)',
        'what_is': 'Il numero esatto di mesi durante i quali è possibile coprire interamente il tenore di vita e le spese obbligatorie a entrate azzerate, attingendo solo alla cassa disponibile.',
        'how_calc': '<b>Runway</b> = Liquidità Prontamente Disponibile / Media Spese Mensili (Burn Rate)',
        'why_useful': 'Garantire tranquillità economica ed evitare tassativamente la vendita forzata di asset finanziari volatili durante fasi di ribasso di mercato.',
        'argus_calc': 'Rapporto tra la cassa disponibile e il burn rate mensile medio registrato negli ultimi 6 mesi depurato da spese straordinarie.',
        'how_to_read': '• 🟢 &gt; 6 mesi (Elevata serenità e indipendenza di breve termine)<br>• 🟡 3 - 6 mesi (Autonomia standard adeguata)<br>• 🔴 &lt; 3 mesi (Pericolo di liquidità: ricostituire prioritariamente il fondo cassa).',
        'limitations': 'Un runway eccessivo (> 18-24 mesi) fermo su conti infruttiferi comporta un severo costo opportunità (cash drag) ed erosione da inflazione.',
    },
    'fixed_cost_ratio': {
        'title': '📊 Fixed Cost Ratio & Rigidità di Spesa (Needs Ratio)',
        'what_is': 'La percentuale delle entrate nette assorbita dalle spese fisse obbligatorie e non eliminabili (affitto/mutuo, utenze, assicurazioni, cibo primario, trasporti essenziali).',
        'how_calc': '<b>Fixed Cost Ratio</b> = [ &sum; Spese Fisse Mensili / Entrate Nette Mensili ] &times; 100',
        'why_useful': 'Misura la rigidità del proprio stile di vita: più basso è il rapporto dei costi fissi, più è facile ridurre le spese in caso di crisi senza compromettere la propria stabilità.',
        'argus_calc': 'Categorizzazione algoritmica automatica delle transazioni ricorrenti con frequenza stabilita e assenza di discrezionalità.',
        'how_to_read': '• 🟢 &le; 50% (Piena conformità alla regola aurea 50/30/20, flessibilità elevata)<br>• 🟡 50% - 60% (Flessibilità contenuta ma gestibile)<br>• 🔴 &gt; 65% (Struttura di spesa pericolosamente rigida: elevato rischio di insolvenza in caso di calo del reddito).',
        'limitations': 'Spesso categorizza rate di debito per acquisti voluttuari come spese fisse; richiede revisione manuale periodica dei contratti di fornitura.',
    },
    'pension_replacement_rate': {
        'title': '🛡️ Tasso di Sostituzione Pensionistico (INPS + Fondo Pensione)',
        'what_is': "Il rapporto percentuale tra il primo assegno pensionistico mensile netto percepito al momento del ritiro dal lavoro e l'ultimo stipendio o reddito netto da lavoro conseguito.",
        'how_calc': '<b>Tasso Sostituzione</b> = [ Pensione Netta Mensile (Pubblica + Integrativa) / Ultimo Reddito Netto Mensile ] &times; 100',
        'why_useful': "Misurare tempestivamente il calo di tenore di vita che si verificherà al pensionamento per quantificare l'esatto fabbisogno di previdenza complementare integrativa.",
        'argus_calc': 'Algoritmo attuariale integrato con tabelle di longevità ISTAT e coefficienti di trasformazione INPS (L. 335/95 Dini), integrato con il montante atteso accumulato nei fondi pensione complementari.',
        'how_to_read': '• 🟢 &gt; 75% (Pensionamento sereno senza riduzione significativa del tenore di vita)<br>• 🟡 60% - 75% (Copertura discreta ma con moderato gap da colmare con risparmio privato)<br>• 🔴 &lt; 60% (Grave gap pensionistico: incremento urgente dei versamenti previdenziali).',
        'limitations': "Le stime della pensione pubblica dipendono da riforme legislative future, dall'evoluzione del PIL reale e dalla continuità contributiva senza buchi di carriera.",
    },
    'pension_gap': {
        'title': '📉 Gap Previdenziale Atteso (Retirement Income Deficit)',
        'what_is': "La differenza monetaria mensile o annuale in euro tra l'ultimo reddito da lavoro e la rendita pensionistica complessiva erogata da previdenza obbligatoria e complementare.",
        'how_calc': '<b>Gap Previdenziale</b> = Ultimo Reddito Mensile &minus; Rendita Pensionistica Totale Mensile',
        'why_useful': 'Dimensionare con esattezza il versamento periodico deducibile (fino al tetto di legge di € 5.164,57 annui ex Art. 10 TUIR) necessario a colmare il deficit.',
        'argus_calc': "Calcolo differenziale attualizzato all'anno stimato di pensionamento, depurato dall'inflazione per esprimere il gap in potere d'acquisto reale odierno.",
        'how_to_read': "• 🟢 € 0 o surplus (Nessun gap, reddito pensionistico pari o superiore al lavoro)<br>• 🟡 Gap &lt; 20% dell'ultimo reddito (Colmabile con PAC o fondo pensione standard)<br>• 🔴 Gap &gt; 35% (Vera e propria emergenza previdenziale da pianificare con priorità).",
        'limitations': 'Assume una spesa post-pensionamento identica a quella pre-pensionamento; in realtà alcune spese (es. trasporti lavoro) diminuiscono, mentre altre (sanitarie) aumentano.',
    },
    'pmc_fiscale': {
        'title': '📑 Prezzo Medio Ponderato Fiscale di Carico (PMC Fiscale)',
        'what_is': "Il costo fiscale unitario di acquisto di uno strumento finanziario, calcolato ai sensi dell'Art. 67 del TUIR (D.P.R. 917/1986) secondo il metodo del Prezzo Medio Ponderato (o FIFO per gestioni patrimoniali e regime dichiarativo).",
        'how_calc': '<b>PMC</b> = [ &sum; (Quantità<sub>i</sub> &times; Prezzo<sub>i</sub>) + &sum; Commissioni ] / &sum; Quantità<sub>i</sub>',
        'why_useful': 'È la base di calcolo di tutte le plusvalenze e minusvalenze: vendere a un prezzo superiore al PMC genera capital gain imponibile (26%), vendere sotto genera minusvalenza fiscale accreditabile.',
        'argus_calc': 'Tracciamento continuo per lotto di acquisto con inclusione degli oneri accessori diretti (commissioni di negoziazione, Tobin Tax) e rettifica retroattiva automatica per stock split e frazionamenti azionari.',
        'how_to_read': '• 🟢 Prezzo Mercato &gt; PMC (Posizione in utile con plusvalenza latente differita)<br>• 🔴 Prezzo Mercato &lt; PMC (Posizione in perdita con opportunità di tax-loss harvesting strategico).',
        'limitations': 'In caso di cambi valuta multipli (es. acquisto di azioni in USD con conto in EUR), il PMC deve recepire il cambio BCE del giorno di ciascun acquisto, generando plusvalenze/minusvalenze valutarie concorrenti.',
    },
    'zainetto_fiscale': {
        'title': '💰 Zainetto Fiscale & Minusvalenze Pregresse (Tax Shield Art. 67)',
        'what_is': "L'ammontare delle perdite di capitale realizzate su strumenti finanziari registrate presso l'intermediario finanziario o nel Quadro RT, compensabili con future plusvalenze entro il quarto anno successivo a quello di realizzo.",
        'how_calc': '<b>Scudo Fiscale</b> = Minusvalenze Residue &times; 26% (o 12.5% per Titoli di Stato)',
        'why_useful': "Massimizzare il recupero del credito d'imposta prima della scadenza naturale dei 4 anni (Tax-Loss Recovery), evitando di regalare denaro all'Erario.",
        'argus_calc': 'Registro a scadenza quadriennale roll-forward con allineamento FIFO delle compensazioni e distinzione stringente tra Redditi Diversi e Redditi di Capitale.',
        'how_to_read': '• 🟢 Crediti compensati tempestivamente senza scadenze a breve<br>• 🟡 Minusvalenze in scadenza entro 12 mesi (Necessaria operatività di recupero con strumenti idonei)<br>• 🔴 Minusvalenze prescritte (Perdita definitiva del beneficio fiscale).',
        'limitations': 'Asimmetria Fiscale Italiana: per legge, i guadagni da ETF e fondi comuni sono classificati come redditi di capitale e non possono compensare le minusvalenze pregresse accumulate nello zainetto fiscale.',
    },
    'real_net_return': {
        'title': '📈 Rendimento Netto Reale (Post-Tax & Post-Inflation Fisher Return)',
        'what_is': "Il tasso di rendimento effettivo generato dal capitale al netto di tutte le imposte sul capital gain e imposte di bollo patrimoniali, depurato dall'erosione del potere d'acquisto causata dall'inflazione (Equazione di Fisher 1930).",
        'how_calc': '1 + r<sub>reale</sub> = (1 + r<sub>nominale, netto</sub>) / (1 + i<sub>inflazione</sub>) &nbsp;&rArr;&nbsp; <b>r<sub>reale</sub> &asymp; r<sub>netto</sub> &minus; i<sub>inflazione</sub></b>',
        'why_useful': "È l'unica misura che conta per la sopravvivenza del patrimonio nel lungo termine: un rendimento nominale positivo del 3% con inflazione al 4% e tasse al 26% equivale a una perdita di potere d'acquisto reale del 1.78% annuo.",
        'argus_calc': "Calcolato decurtando dal rendimento lordo l'aliquota fiscale effettiva (26% o 12.5%), l'imposta di bollo patrimoniale dello 0.20% annuo e l'indice ISTAT FOI / HICP armonizzato europeo.",
        'how_to_read': "• 🟢 &gt; +2.5% annuo (Creazione solida e autentica di ricchezza reale)<br>• 🟡 0.0% - +2.5% (Preservazione del potere d'acquisto)<br>• 🔴 &lt; 0.0% (Illusione monetaria: il capitale nominale cresce ma il potere d'acquisto reale viene distrutto).",
        'limitations': "La stima dell'inflazione futura è soggetta a incertezza e l'inflazione personale (personale paniere di spesa) può divergere significativamente dal dato statistico aggregato ISTAT.",
    },
    'beta_market': {
        'title': '🏛️ Beta di Mercato (Market Sensitivity)',
        'what_is': "Misura della sensibilità del rendimento del portafoglio rispetto alle variazioni dell'indice di riferimento (rischio sistematico non diversificabile).",
        'how_calc': '<b>&beta;</b> = Cov(R<sub>p</sub>, R<sub>m</sub>) / Var(R<sub>m</sub>) = &rho;<sub>p,m</sub> &times; (&sigma;<sub>p</sub> / &sigma;<sub>m</sub>)',
        'why_useful': 'Stabilire se il portafoglio amplifica (&beta; > 1) o attenua (&beta; < 1) i movimenti del mercato complessivo.',
        'argus_calc': 'Regressione OLS dei rendimenti giornalieri del portafoglio contro il benchmark principale selezionato (SPY, QQQ, ACWI) su finestra mobile di 252 sedute.',
        'how_to_read': '• 🟢 &beta; &lt; 0.80 (Difensivo / Bassa sensibilità sistemica)<br>• 🟡 &beta; &asymp; 1.00 (In linea col mercato)<br>• 🔴 &beta; &gt; 1.20 (Aggressivo, amplifica fortemente i ribassi di mercato).',
        'limitations': 'Assume linearità costante: nei crash sistemici, le correlazioni tendono a convergere a 1 e il Beta effettivo aumenta repentinamente rispetto alla media storica.',
    },
    'alpha_jensen': {
        'title': '🏆 Alpha di Jensen (Extra-Rendimento Gestionale CAPM)',
        'what_is': "L'extra-rendimento netto generato dal portafoglio rispetto a quello atteso in base al modello CAPM per il livello di rischio sistematico assunto.",
        'how_calc': '<b>&alpha;</b> = R<sub>p</sub> &minus; [ R<sub>f</sub> + &beta; &times; (R<sub>m</sub> &minus; R<sub>f</sub>) ]',
        'why_useful': 'Isolare il valore aggiunto puro generato dalle scelte di stock picking e asset allocation del gestore al netto del mercato.',
        'argus_calc': 'Intercetta della regressione lineare tra i rendimenti in eccesso del portafoglio e del benchmark, calcolata con p-value di confidenza e tasso R<sub>f</sub> dinamico.',
        'how_to_read': '• 🟢 &alpha; &gt; +2.0% (Netta creazione di valore attivo)<br>• 🟡 0.0% &le; &alpha; &le; +2.0% (Lieve extra-performance)<br>• 🔴 &alpha; &lt; 0.0% (Distruzione di valore rispetto a una replica passiva).',
        'limitations': 'Dipende dalla validità del CAPM uni-fattoriale: se i mercati sono mossi da fattori multipli (Fama-French), quello che appare come Alpha può essere solo esposizione non dichiarata a fattori Value o Momentum.',
    },
    'hrp_diversification_ratio': {
        'title': '🌐 HRP Cluster Diversification Ratio (Gerarchia di Rischio)',
        'what_is': "Rapporto tra la media ponderata delle volatilità dei singoli componenti e la volatilità complessiva del portafoglio allocato secondo l'algoritmo Hierarchical Risk Parity.",
        'how_calc': '<b>DR<sub>HRP</sub></b> = (&sum; w<sub>i</sub> &times; &sigma;<sub>i</sub>) / &radic;(<b>w</b><sub>HRP</sub><sup>T</sup> &Sigma; <b>w</b><sub>HRP</sub>)',
        'why_useful': "Quantificare il reale beneficio della diversificazione strutturale gerarchica evitando l'instabilità numerica dell'inversione della matrice di Markowitz.",
        'argus_calc': 'Calcolato con matrice di covarianza de-noised Ledoit-Wolf e pesi ottimali ricavati da tree clustering, quasi-diagonalization e recursive bisection.',
        'how_to_read': '• 🟢 &gt; 1.45 (Ottima diversificazione istituzionale)<br>• 🟡 1.20 - 1.45 (Diversificazione moderata)<br>• 🔴 &lt; 1.20 (Scarsa diversificazione, elevato rischio di concentrazione).',
        'limitations': "In mercati guidati da bolle speculative concentrate su singoli settori dominanti, l'approccio per parità di rischio può sottopesare i titoli più performanti.",
    },
    'var_99': {
        'title': '🛡️ Value at Risk Parametrico 99% (Parametric Gaussian VaR 99%)',
        'what_is': 'La perdita massima potenziale a 1 giorno con livello di confidenza al 99% (standard regolamentare di Basilea per i requisiti minimi di capitale bancario).',
        'how_calc': '<b>VaR<sub>99%, 1D</sub></b> = &minus;(&mu;<sub>daily</sub> &minus; 2.3263 &times; &sigma;<sub>port, daily</sub>)',
        'why_useful': 'Utilizzato per stress testing normativo, allocazione del capitale di rischio istituzionale e verifica dei limiti di solvibilità.',
        'argus_calc': 'Rendimenti discreti giornalieri, covarianza campionaria de-noised con Ledoit-Wolf, z<sub>0.99</sub> = 2.3263, orizzonte 1D con convenzione a 252 sedute lavorative/anno.',
        'how_to_read': '• 🟢 &lt; 2.50% (Eccellente tenuta prudenziale)<br>• 🟡 2.50% - 4.00% (Rischio 99% standard per portafogli azionari)<br>• 🔴 &gt; 4.00% (Rischio estremo: 1 giorno su 100 può distruggere oltre il 4% del capitale).',
        'limitations': "L'ipotesi di normalità al 99% è ancora più fragile che al 95%: nella realtà dei mercati, eventi oltre 2.33 sigma si verificano molto più frequentemente di quanto previsto dalla curva di Gauss (leptocurtosi empirica).",
    },
    'information_ratio': {
        'title': '🎯 Information Ratio (Alpha Attivo / Tracking Error)',
        'what_is': "Il rapporto tra l'extra-rendimento medio del portafoglio rispetto al benchmark di riferimento e la deviazione standard annualizzata di tale differenziale (Tracking Error).",
        'how_calc': '<b>IR</b> = (R<sub>p</sub> &minus; R<sub>b</sub>) / TE &nbsp;|&nbsp; <b>TE</b> = &radic;Var(R<sub>p</sub> &minus; R<sub>b</sub>) &times; &radic;252',
        'why_useful': 'Misura cardine per valutare la consistenza della gestione attiva: distingue chi genera sovraperformance costante da chi ha solo assunto scommesse volatili non correlate.',
        'argus_calc': 'Calcolato sulle serie temporali sincronizzate dei rendimenti giornalieri del portafoglio e del benchmark prescelto (SPY, ACWI, ecc.), annualizzato a 252 sedute lavorative.',
        'how_to_read': '• 🟢 &gt; 0.75 (Gestione attiva eccezionale, alpha costante e controllato)<br>• 🟡 0.40 - 0.75 (Buona efficienza gestionale)<br>• 🔴 &lt; 0.40 o negativo (Rischio attivo non remunerato rispetto alla replica passiva).',
        'limitations': "Se il gestore adotta uno stile di investimento fortemente decorrelato dal benchmark, il Tracking Error elevato comprime l'IR anche in presenza di ottimi rendimenti assoluti.",
    },
}


PHRASE_RULES = [
    # Explicit compound phrases (specific ones first)
    (r"\b(?:parametric\s+)?var\s*99%?\b", "var_parametric_99"),
    (r"\bvar\s+storico\s*95%?\b", "var_historical_95"),
    (r"\bvar\s+storico\s*99%?\b", "var_historical_99"),
    (r"\bvar\s+cornish[\s\-]fisher\b", "var_cornish_fisher"),
    (r"\bvar\s+monte[\s\-]carlo\b", "var_monte_carlo"),
    (r"\bexpected\s+shortfall\b", "cvar_expected_shortfall"),
    (r"\bcvar\b", "cvar_expected_shortfall"),
    (r"\bgarch\b", "garch_volatility"),
    (r"\btail\s+(?:risk|ratio)\b", "tail_risk_index"),
    (r"\btreynor\b", "treynor_ratio"),
    (r"\baverage\s+drawdown\b", "average_drawdown"),
    (r"\bdrawdown\s+medio\b", "average_drawdown"),
    (r"\brecovery\s+time\b", "recovery_time"),
    (r"\btempo\s+di\s+recupero\b", "recovery_time"),
    (r"\br[\s\-]squared\b", "r_squared"),
    (r"\br\s*quadro\b", "r_squared"),
    (r"\bcorrelation\s+distance\b", "correlation_distance"),
    (r"\bdistanza\s+di\s+correlazione\b", "correlation_distance"),
    (r"\bliquid\s+net\s+worth\b", "liquid_net_worth"),
    (r"\bpatrimonio\s+liquido\b", "liquid_net_worth"),
    (r"\bfixed\s+cost\s+ratio\b", "fixed_cost_ratio"),
    (r"\btasso\s+(?:di\s+)?sostituzione\b", "pension_replacement_rate"),
    (r"\bgap\s+previdenziale\b", "pension_gap"),
    (r"\bpmc\s+fiscale\b", "pmc_fiscale"),
    (r"\bpmc\b", "pmc_fiscale"),
    (r"\brendimento\s+(?:netto\s+)?reale\b", "real_net_return"),
    (r"\breal\s+net\s+return\b", "real_net_return"),
    (r"\bvariazion[ei]\s+cassa\b", "cash_variation_pbs"),
    (r"\bprevision[ei]\s+cassa\b", "cash_forecast_3m"),
    (r"\bfluss[io]\s+(?:di\s+)?cassa\s+netto\b", "net_cash_flow"),
    (r"\bfluss[io]\s+netto\b", "net_cash_flow"),
    (r"\bburn\s+rate\s+giornaliero\b", "burn_rate_daily"),
    (r"\bburn\s+rate\s+medio\b", "burn_rate_monthly"),
    (r"\bburn\s+rate\b", "burn_rate_monthly"),
    (r"\bburn\s+ricorrente\b", "recurring_burn"),
    (r"\bopportunity\s+drag\b", "opportunity_drag"),
    (r"\btotale\s+entrate\b", "total_inflow"),
    (r"\bentrat[ae]\s+medi[ae]\s+mensil[ei]\b", "monthly_inflow"),
    (r"\btotale\s+(?:costi|spese|uscite)\b", "total_outflow"),
    (r"\btasso\s+di\s+risparmio\b", "savings_rate"),
    (r"\bpersonal\s+savings\s+rate\b", "personal_savings_rate"),
    (r"\brisparmio\s+netto\s+annuo\b", "annual_net_savings"),
    (r"\brisparmio\s+netto\s+stimato\b", "annual_net_savings"),
    (r"\brisparmio\s+extra\b", "extra_monthly_savings"),
    (r"\brisparmio\s+fiscale\s+irpef\b", "risparmio_irpef_previdenza"),
    (r"\brisparmio\s+fiscale\s+pex\b", "pex_tax_saving"),
    (r"\binteressi\s+risparmiati\b", "interest_saved_debt"),
    (r"\bcarried\s+interest\b", "carried_interest_gp"),
    (r"\bquarter[\s\-]kelly\b", "quarter_kelly"),
    (r"\bhalf[\s\-]kelly\b", "half_kelly"),
    (r"\bfull[\s\-]kelly\b", "full_kelly"),
    (r"\bduplicati\s+rilevati\b", "duplicate_txs"),
    (r"\banomali[ae]\s+(?:ml|rilevat[ae])\b", "isolation_forest"),
    (r"\brilevanza\s+semantica\b", "semantic_relevance"),
    (r"\bcontrovalore\s+incassato\b", "proceeds_cash_in"),
    (r"\bvariazion[ei]\s+controvalore\b", "value_variation"),
    (r"\bvariazion[ei]\s+peso\b", "weight_variation"),
    (r"\bvariazion[ei]\s+capitale\b", "value_variation"),
    (r"\bpoint\s+of\s+forced\s+liquidation\b", "point_of_forced_liquidation"),
    (r"\bforced\s+liquidation\b", "point_of_forced_liquidation"),
    (r"\bdeficit\s+di\s+liquidit[aà]\b", "liquidity_squeeze_deficit"),
    (r"\bdynamic\s+fire\s+swr\b", "dynamic_fire_swr"),
    (r"\bimpatt[io]\s+rata\s+mutuo\b", "mutuo_rata_impact"),
    (r"\bpareggio\s+(?:di\s+)?bilancio\b", "pareggio_bilancio"),
    (r"\btotale\s+attivo\b", "totale_attivo"),
    (r"\bpassivit[aà]\s+(?:totali|&|debiti|mutui)\b", "total_liabilities"),
    (r"\btotale\s+passivit[aà]\b", "total_liabilities"),
    (r"\bdebito\s+mutui\s+residuo\b", "total_liabilities"),
    (r"\bindice\s+di\s+solvibilit[aà]\b", "solvency_ratio"),
    (r"\bsolvency\s+ratio\b", "solvency_ratio"),
    (r"\bdebt[\s\-]to[\s\-]asset\b", "debt_to_asset"),
    (r"\binvested\s+assets\s+ratio\b", "invested_assets_ratio"),
    (r"\bdsti\b", "dsti_ratio"),
    (r"\bemergency\s+runway\b", "emergency_runway"),
    (r"\bmes[ei]\s+di\s+autonomia\b", "emergency_runway"),
    (r"\brunway\b", "emergency_runway"),
    (r"\bnet\s+equity\s+immobiliare\b", "real_estate_equity"),
    (r"\bvalore\s+caveau\b", "physical_assets"),
    (r"\bprevidenza\s+complementare\b", "pension_total"),
    (r"\bprevidenza\s+integrativa\b", "pension_total"),
    (r"\btempo\s+alla\s+libert[aà]\b", "tempo_liberta"),
    (r"\btarget\s+fire\s+number\b", "fire_number"),
    (r"\bcoast\s+fire\b", "coast_fire"),
    (r"\bfondo\s+anti[\s\-]forced\b", "anti_forced_selling"),
    (r"\bsuccess\s+probability\s+index\b", "success_probability_index"),
    (r"\bpatrimonio\s+netto\b", "net_worth_consolidated"),
    (r"\bnet\s+worth\b", "net_worth_consolidated"),
    (r"\bliquidit[aà]\s+e\s+depositi\b", "liquid_net_worth"),
    (r"\bfondo\s+di\s+emergenza\b", "liquid_net_worth"),
    (r"\baliquota\s+effettiva\b", "aliquota_effettiva_media"),
    (r"\bdebit[oi]\s+f24\b", "f24_tax_debt"),
    (r"\bpex\b", "pex_tax_saving"),
    (r"\befficienza\s+fiscale\b", "tax_efficiency_ratio"),
    (r"\binterest\s+coverage\s+ratio\b", "interest_coverage_ratio"),
    (r"\bicr\b", "interest_coverage_ratio"),
    (r"\bcovenants\b", "covenants_status"),
    (r"\btvpi\b", "moic_pe"),
    (r"\bmoic\b", "moic_pe"),
    (r"\bdpi\b", "dpi_pe"),
    (r"\brvpi\b", "rvpi_pe"),
    (r"\bxirr\b", "xirr_pe"),
    (r"\bswr\b", "swr_fire"),
    (r"\bsafe\s+withdrawal\s+rate\b", "swr_fire"),
    (r"\b50\s*/\s*30\s*/\s*20\b", "budget_50_30_20"),
    (r"\btco\b", "tco_fee_drag"),
    (r"\bfee\s+drag\b", "tco_fee_drag"),
    (r"\bsuccessione\b", "estate_planning"),
    (r"\besteat[e\s\-]+planning\b", "estate_planning"),
    (r"\bherfindahl\b", "hhi_index"),
    (r"\baltman\s+z\b", "altman_z_score"),
    (r"\bbeneish\s+m\b", "beneish_m_score"),
    (r"\bsloan\s+accrual\b", "sloan_accrual"),
    (r"\bpiotroski\b", "piotroski_f_score"),
    (r"\bwacc\b", "wacc"),
    (r"\bdcf\b", "wacc"),
    (r"\broe\b", "return_on_equity"),
    (r"\bfree\s+cash\s+flow\b", "free_cash_flow"),
    (r"\bfcf\b", "free_cash_flow"),
    (r"\bcalmar\b", "calmar_ratio"),
    (r"\bsortino\b", "sortino_ratio"),
    (r"\bsharpe\b", "sharpe_ratio"),
    (r"\bdrawdown\b", "max_drawdown"),
    (r"\bmdd\b", "max_drawdown"),
    (r"\bvalue\s+at\s+risk\b", "var_parametric_95"),
    (r"\bvar\s*(?:95)?%?\b", "var_parametric_95"),
    (r"\bvolatilit[aà]\b", "volatilita_annua"),
    (r"\brendimento\b", "rendimento_atteso"),
    (r"\bcagr\b", "rendimento_atteso"),
    (r"\bbeta\b", "beta_market"),
    (r"\balpha\b", "alpha_jensen"),
    (r"\bulcer\b", "ulcer_index"),
    (r"\bomega\b", "omega_ratio"),
    (r"\btracking\s+error\b", "tracking_error"),
    (r"\bdiversification\s+ratio\b", "hrp_diversification_ratio"),
    (r"\bdays[\s\-]to[\s\-]liquidate\b", "days_to_liquidate"),
    (r"\bsmobilizzo\b", "days_to_liquidate"),
    (r"\bchandelier\b", "chandelier_exit"),
    (r"\btail\s+dependence\b", "copula_tail_dependence"),
    (r"\bmerton\b", "merton_jump"),
    (r"\bgreche\b", "black_scholes_greeks"),
    (r"\bliquidit[aà]\b", "liquid_net_worth"),
    (r"\bcassa\b", "liquid_net_worth"),
    (r"\binvestimenti\b", "financial_investments"),
    (r"\bcaveau\b", "physical_assets"),
    (r"\borolog[io]\b", "physical_assets"),
    (r"\bimmobili\b", "real_estate_equity"),
    (r"\bprevidenza\b", "pension_total"),
    (r"\bdebiti\b", "total_liabilities"),
    (r"\bmutui\b", "total_liabilities"),
    (r"\brisparmio\b", "savings_rate"),
]


def _generate_dynamic_fallback_5point(label: str, help_text: str = None) -> str:
    """
    Generatore dinamico intelligente per metriche non censite direttamente nella knowledge base.
    Deduce dominio, tipo di misura (valuta, percentuale, durata, conteggio), direzione semaforica
    e formula matematica specifica, azzerando qualsiasi testo boilerplate o generico fisso.
    """
    import re
    lbl_clean = re.sub(r'^[^\w\s]+', '', label).strip()
    lbl_lower = lbl_clean.lower()
    
    # Rilevamento Dominio e Icona
    is_tax = any(w in lbl_lower for w in ["fisc", "tass", "impost", "ivafe", "irpef", "rw", "rt", "minus", "plus"])
    is_wealth = any(w in lbl_lower for w in ["patrimon", "cassa", "spes", "immob", "orolog", "pens", "debit", "cont", "bilanc", "saving", "net worth"])
    is_risk = any(w in lbl_lower for w in ["risch", "risk", "var", "volat", "drawdown", "stress", "shock", "perdita", "downside"])
    is_trading = any(w in lbl_lower for w in ["trade", "order", "book", "exec", "slippage", "vwap", "spread", "volume", "hhi", "win"])

    if is_tax:
        icon = "📑"
        engine = "Wealth & Tax Compliance Engine con allineamento quadro RW/RT"
        limitations = "Assume la permanenza del quadro normativo tributario vigente e la corretta qualificazione formale dei regimi (amministrato vs dichiarativo). Non sostituisce la consulenza di un commercialista abilitato."
    elif is_wealth:
        icon = "🏛️"
        engine = "Personal Wealth Engine con consolidamento multi-asset e bilancio certificato"
        limitations = "L'affidabilità dipende dalla tempestività dell'aggiornamento dei saldi bancari e delle perizie su asset illiquidi/immobiliari. Non include passività potenziali non contrattualizzate."
    elif is_risk:
        icon = "🛡️"
        engine = "Quantitative Risk Engine con simulazioni stocastiche su serie storiche e shock matrix"
        limitations = "Modello quantitativo basato su serie storiche e assunzioni di stazionarietà statistica. Può sottostimare le perdite reali in presenza di cigni neri sistemici o prosciugamenti di liquidità."
    elif is_trading:
        icon = "⚡"
        engine = "Execution & Microstructure Engine con aggregazione tick/order-book"
        limitations = "La stima dell'impatto di mercato e dello slippage assume book di negoziazione con liquidità e spread ordinari. In condizioni di flash crash, i costi reali possono divergere sensibilmente."
    else:
        icon = "📊"
        engine = "Analytics & Quantitative Engine ARGUS con monitoraggio in tempo reale"
        limitations = "La misura riflette i dati storici disponibili e le convenzioni di calcolo adottate; non tiene conto di eventi sistemici esogeni non ancora riflessi nelle serie temporali."

    # Definizione Cos'è (priorità a help_text puntuale)
    if help_text and len(help_text.strip()) > 5:
        what_is = help_text.strip()
    else:
        what_is = f"Indicatore quantitativo di controllo e monitoraggio specializzato per la metrica '{lbl_clean}'."

    # Deduzione Tipo di Grandezza e Formula Matematica
    is_ratio = any(w in lbl_lower for w in ["%", "tasso", "rate", "ratio", "percentuale", "quota", "incidenza", "rendimento"])
    is_currency = any(w in lbl_lower for w in ["€", "costo", "spesa", "capitale", "valore", "saldo", "entrata", "flusso", "risparmio", "prezzo", "controvalore", "ricavo", "debito", "imposta", "perdita", "profitto", "montante"])
    is_duration = any(w in lbl_lower for w in ["mesi", "giorni", "anni", "tempo", "durata", "periodo", "holding"])
    is_count = any(w in lbl_lower for w in ["numero", "conteggio", "titoli", "operazioni", "transazioni", "posizioni", "candidati", "duplicati", "anomalie"])

    if is_ratio:
        how_calc = f"<b>{lbl_clean} (%)</b> = (Grandezza Primaria / Parametro di Riferimento o Benchmark) &times; 100"
    elif is_currency:
        how_calc = f"<b>{lbl_clean} (&euro;)</b> = &sum; Componenti e Flussi di Competenza Certificati nel Periodo"
    elif is_duration:
        how_calc = f"<b>{lbl_clean}</b> = Stock o Fabbisogno Cumulato / Velocità di Flusso Periodale (Burn/Esecuzione)"
    elif is_count:
        how_calc = f"<b>{lbl_clean}</b> = &sum; Occorrenze o Record Verificati nel Database"
    else:
        how_calc = f"<b>{lbl_clean}</b> = Misura quantitativa determinata per aggregazione analitica dei parametri di riferimento"

    # Guida di Lettura e Semafori Contestuali (Direzione Inversa vs Diretta)
    is_inverted = any(w in lbl_lower for w in ["cost", "spesa", "burn", "drawdown", "deficit", "perdita", "rischio", "errore", "tass", "impost", "shortfall", "drag", "debito", "slippage"])
    
    if is_inverted:
        how_to_read = f"• 🟢 Valori bassi o contenuti (Ottimale: impatto o vulnerabilità minimizzata per {lbl_clean})<br>• 🟡 Fascia di oscillazione moderata entro le tolleranze ammesse<br>• 🔴 Valori elevati o anomali (Trigger di revisione attiva: costo o rischio sopra soglia)."
    elif is_ratio:
        how_to_read = f"• 🟢 Valore superiore al target strategico o al benchmark di riferimento<br>• 🟡 In linea con la media storica di periodo<br>• 🔴 Valore al di sotto della soglia minima prudenziale richiesta."
    elif is_duration:
        how_to_read = f"• 🟢 Orizzonte ampio e capiente (Margine di sicurezza temporale elevato)<br>• 🟡 Orizzonte intermedio da presidiare<br>• 🔴 Orizzonte compresso (Intervento prioritario richiesto)."
    elif is_count:
        how_to_read = f"• 🟢 Conteggio coerente con la regolare operatività del periodo<br>• 🟡 Variazione moderata rispetto alla media<br>• 🔴 Scostamento significativo dai volumi operativi attesi."
    else:
        how_to_read = f"• 🟢 Livello ottimale allineato con gli standard patrimoniali e di rischio<br>• 🟡 Fascia di oscillazione ordinaria<br>• 🔴 Valore anomalo o fuori dai parametri di tolleranza prefissati."

    return format_institutional_5point_html(
        title=f"{icon} {lbl_clean}",
        what_is=what_is,
        how_calc=how_calc,
        why_useful=f"Fornire piena trasparenza, presidio del rischio e controllo analitico continuo su {lbl_clean}.",
        argus_calc=f"Elaborazione automatica del {engine}.",
        how_to_read=how_to_read,
        limitations=limitations
    )


def resolve_metric_knowledge(label: str, help_text: str = None) -> str:
    """
    Risolve il testo informativo per qualsiasi metrica o card, assicurando sempre
    la struttura standard istituzionale a 5 sezioni:
    1. 📌 Cos'è (Definizione Formale & Intuizione Finanziaria)
    2. ⚙️ Come viene calcolata da ARGUS (Formula KaTeX/LaTeX & Dettagli Implementativi)
    3. 🎯 A cosa serve (Casi d'Uso Pratici & Decision Making)
    4. 📊 Come si legge & Valori Guida (Soglie di Riferimento)
    5. ⚠️ Limitazioni & Assunzioni del Modello
    """
    if help_text and all(k in help_text for k in ["Cos'è", "Come si calcola", "A cosa serve"]):
        return help_text
        
    import re
    lbl_clean = re.sub(r'^[^\w\s]+', '', label).strip()
    lbl_norm = re.sub(r'[^\w\s]', ' ', lbl_clean).lower()
    raw_key = label.strip().lower()
    snake_key = re.sub(r'[\s\-]+', '_', raw_key)
    cleaned_key = re.sub(r'[^a-zA-Z0-9]', '', label).lower()
    
    # 1. Match Esatto Diretto nella Knowledge Base (su diverse varianti di chiave)
    matched_entry = None
    for cand in [raw_key, snake_key, cleaned_key]:
        if cand in KNOWN_METRICS_KNOWLEDGE_BASE:
            matched_entry = KNOWN_METRICS_KNOWLEDGE_BASE[cand]
            break
            
    if matched_entry:
        return format_institutional_5point_html(
            title=matched_entry["title"],
            what_is=matched_entry["what_is"],
            how_calc=matched_entry["how_calc"],
            why_useful=matched_entry["why_useful"],
            argus_calc=matched_entry["argus_calc"],
            how_to_read=matched_entry["how_to_read"],
            limitations=matched_entry.get("limitations")
        )
        
    # 2. Match con Regole Frase a Delimitatori di Parola Esatti
    for pattern, target_k in PHRASE_RULES:
        if re.search(pattern, lbl_norm):
            if target_k in KNOWN_METRICS_KNOWLEDGE_BASE:
                d = KNOWN_METRICS_KNOWLEDGE_BASE[target_k]
                return format_institutional_5point_html(
                    title=d["title"],
                    what_is=d["what_is"],
                    how_calc=d["how_calc"],
                    why_useful=d["why_useful"],
                    argus_calc=d["argus_calc"],
                    how_to_read=d["how_to_read"],
                    limitations=d.get("limitations")
                )

    # 3. Fallback Dinamico e Intelligente
    return _generate_dynamic_fallback_5point(label, help_text)


def render_metric_info_modal(
    metric_key: str,
    title: str = None,
    button_label: str = "ℹ️ Metodologia & Guida",
    use_popover: bool = False
):
    """
    Componente UI universale riutilizzabile per visualizzare la scheda metodologica istituzionale
    a 5 blocchi di una specifica metrica (da KNOWN_METRICS_KNOWLEDGE_BASE o risolta dinamicamente).
    """
    content = resolve_metric_knowledge(metric_key)
    effective_title = title
    if not effective_title:
        import re
        raw_key = metric_key.strip().lower()
        snake_key = re.sub(r'[\s\-]+', '_', raw_key)
        cleaned_key = re.sub(r'[^a-zA-Z0-9]', '', metric_key).lower()
        d = (
            KNOWN_METRICS_KNOWLEDGE_BASE.get(raw_key)
            or KNOWN_METRICS_KNOWLEDGE_BASE.get(snake_key)
            or KNOWN_METRICS_KNOWLEDGE_BASE.get(cleaned_key)
        )
        if d:
            effective_title = d.get("title", metric_key)
        else:
            effective_title = f"ℹ️ Scheda Metodologica: {metric_key}"
            
    render_info_modal(
        title=effective_title,
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_info_tooltip(metric_key: str, label: str = "ℹ️"):
    """
    Widget a comparsa rapida (st.popover) per visualizzazione inline compatta
    della scheda a 5 blocchi nei layout tabellari, grafici o nelle intestazioni di colonna.
    """
    content = resolve_metric_knowledge(metric_key)
    import re
    raw_key = metric_key.strip().lower()
    snake_key = re.sub(r'[\s\-]+', '_', raw_key)
    cleaned_key = re.sub(r'[^a-zA-Z0-9]', '', metric_key).lower()
    d = (
        KNOWN_METRICS_KNOWLEDGE_BASE.get(raw_key)
        or KNOWN_METRICS_KNOWLEDGE_BASE.get(snake_key)
        or KNOWN_METRICS_KNOWLEDGE_BASE.get(cleaned_key)
    )
    title = d.get("title", metric_key) if d else metric_key
    with st.popover(label, help=f"Dettagli metodologici per {title}"):
        st.markdown(f"### {title}")
        st.markdown(content, unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = None, positive: bool = True, help_text: str = None, is_positive: bool = None, delta_color: str = None):
    has_explicit_sentiment = (is_positive is not None) or (delta_color is not None)
    if is_positive is not None:
        positive = is_positive
    elif delta_color is not None:
        if delta_color in ["off", "none", "gray"]:
            positive = None
        elif delta_color == "inverse":
            positive = False
        elif delta_color == "normal":
            positive = True

    import re
    import random
    
    unique_id = f"{re.sub(r'[^a-zA-Z0-9]', '_', label).lower()}_{random.randint(1000, 9999)}"
    
    delta_html = ""
    if delta:
        d_str = str(delta).strip()
        has_sign_prefix = d_str.startswith(("+", "-", "↑", "↓"))
        
        # Se non è specificato esplicitamente un colore o sentimento ed è un testo descrittivo senza +/-/↑/↓
        if positive is None or (not has_sign_prefix and not has_explicit_sentiment):
            delta_html = f'<div style="color: #8b949e; font-size: 11.5px; font-weight: 500; margin-top: 3px;">{d_str}</div>'
        else:
            # Pulisci il testo per evitare collisioni di freccia e segno (+/-)
            clean_d = d_str
            if clean_d.startswith(("↑", "↓")):
                clean_d = clean_d[1:].strip()
            if clean_d.startswith(("+", "-")):
                clean_d = clean_d[1:].strip()

            cls = "metric-delta-pos" if positive else "metric-delta-neg"
            arrow = "↑" if positive else "↓"
            delta_html = f'<div class="{cls}">{arrow} {clean_d}</div>'

    
    modal_html = ""
    # Risolvi sempre il contenuto a 5 sezioni
    resolved_content = resolve_metric_knowledge(label, help_text)
    
    cleaned = re.sub(r'<!--.*?-->', '', resolved_content, flags=re.DOTALL)
    cleaned = re.sub(r'>\s+<', '><', cleaned)
    cleaned = re.sub(r'\s*\n\s*', ' ', cleaned)
    safe_help_text = cleaned.strip()
    
    modal_html = f"""<style>
#modal-toggle-{unique_id} {{ display: none; }}
.modal-overlay-{unique_id} {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 999999;
    align-items: center;
    justify-content: center;
}}
#modal-toggle-{unique_id}:checked ~ .modal-overlay-{unique_id} {{
    display: flex;
}}
.modal-backdrop-{unique_id} {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(10, 14, 20, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    cursor: pointer;
    z-index: 1;
}}
.modal-content-{unique_id} {{
    background: #161b22;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 24px 28px;
    border-radius: 16px;
    width: 90%;
    max-width: 680px;
    max-height: 85vh;
    overflow-y: auto;
    color: #e6edf3;
    position: relative;
    z-index: 2;
    box-shadow: 0 24px 60px rgba(0,0,0,0.9), 0 0 30px rgba(255, 153, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    text-align: left;
    animation: modalScaleIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes modalScaleIn {{
    from {{ opacity: 0; transform: scale(0.94) translateY(12px); }}
    to {{ opacity: 1; transform: scale(1) translateY(0); }}
}}
.modal-close-{unique_id} {{
    position: absolute;
    top: 14px; right: 18px;
    cursor: pointer;
    font-size: 26px;
    color: rgba(255, 255, 255, 0.5);
    font-weight: 300;
    line-height: 1;
    transition: all 0.2s ease;
    z-index: 3;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
}}
.modal-close-{unique_id}:hover {{
    color: #ff9900;
    background: rgba(255, 153, 0, 0.12);
    transform: scale(1.1);
}}
.modal-content-{unique_id}::-webkit-scrollbar {{
    width: 6px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-track {{
    background: rgba(255, 255, 255, 0.02);
    border-radius: 4px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-thumb {{
    background: rgba(255, 153, 0, 0.3);
    border-radius: 4px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-thumb:hover {{
    background: rgba(255, 153, 0, 0.6);
}}
.info-icon-{unique_id} {{
    cursor: pointer; 
    color: #ff9900;
    opacity: 0.85;
    background: rgba(255, 153, 0, 0.08);
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0 !important;
    margin-left: 4px;
    transition: all 0.2s ease;
    border: none;
    box-sizing: border-box !important;
    padding: 0;
}}
.info-icon-{unique_id}:hover {{
    opacity: 1;
    color: #ffb84d;
    background: rgba(255, 153, 0, 0.22);
    transform: scale(1.12);
}}
</style>

<input type="checkbox" id="modal-toggle-{unique_id}">
<div class="modal-overlay-{unique_id}">
    <label for="modal-toggle-{unique_id}" class="modal-backdrop-{unique_id}"></label>
    <div class="modal-content-{unique_id}">
        <label for="modal-toggle-{unique_id}" class="modal-close-{unique_id}">×</label>
        <h3 style="margin: 0 0 14px 0; border-bottom: 1px solid rgba(255,153,0,0.3); padding-bottom: 10px; font-size: 18px; font-weight: 700; color: #ffffff;">{label}</h3>
        <div style="font-size: 14px; line-height: 1.55; margin: 0; color: #c9d1d9;">{safe_help_text}</div>
    </div>
</div>"""
    info_svg = (
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" style="display:block;">'
        '<circle cx="12" cy="12" r="10"></circle>'
        '<line x1="12" y1="16" x2="12" y2="12"></line>'
        '<line x1="12" y1="8" x2="12.01" y2="8"></line>'
        '</svg>'
    )
    label_html = f'<div class="metric-label"><span class="metric-label-text">{label}</span><label for="modal-toggle-{unique_id}" class="info-icon-{unique_id}" title="Clicca per approfondire">{info_svg}</label></div>'

    card_html = (
        f"{modal_html}"
        f'<div class="metric-card">'
        f'{label_html}'
        f'<div style="flex: 1; display: flex; flex-direction: column; justify-content: center; margin: 4px 0 2px 0;">'
        f'<div class="metric-value">{value}</div>'
        f'{delta_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
    return card_html



def render_status_badge(
    text: str,
    level: str = "success",
    pulse: bool = False,
    icon: Optional[str] = None
) -> str:
    """
    Restituisce il markup HTML per un badge di stato istituzionale conforme a WCAG AAA.
    Supporta livelli semantici: 'success', 'warning', 'danger', 'info', 'neutral'.
    """
    styles = {
        "success": {
            "bg": "rgba(16, 185, 129, 0.12)",
            "border": "rgba(16, 185, 129, 0.35)",
            "color": "#34d399",
            "dot": "#10b981"
        },
        "warning": {
            "bg": "rgba(245, 158, 11, 0.12)",
            "border": "rgba(245, 158, 11, 0.35)",
            "color": "#fbbf24",
            "dot": "#f59e0b"
        },
        "danger": {
            "bg": "rgba(239, 68, 68, 0.12)",
            "border": "rgba(239, 68, 68, 0.35)",
            "color": "#f87171",
            "dot": "#ef4444"
        },
        "critical": {
            "bg": "rgba(239, 68, 68, 0.20)",
            "border": "rgba(239, 68, 68, 0.50)",
            "color": "#fca5a5",
            "dot": "#dc2626"
        },
        "info": {
            "bg": "rgba(59, 130, 246, 0.12)",
            "border": "rgba(59, 130, 246, 0.35)",
            "color": "#60a5fa",
            "dot": "#3b82f6"
        },
        "neutral": {
            "bg": "rgba(139, 148, 158, 0.12)",
            "border": "rgba(139, 148, 158, 0.25)",
            "color": "#c9d1d9",
            "dot": "#8b949e"
        }
    }
    st_cfg = styles.get(str(level).lower(), styles["neutral"])
    
    pulse_css = "animation: pulse 2s infinite;" if pulse else ""
    dot_html = f'<span style="width:6px; height:6px; border-radius:50%; background-color:{st_cfg["dot"]}; display:inline-block; {pulse_css}"></span>'
    icon_html = f'<span style="font-size:10px; {pulse_css}">{icon}</span>' if icon else dot_html

    return (
        f'<span style="display:inline-flex; align-items:center; gap:5px; padding:3px 9px; '
        f'border-radius:9999px; font-size:11px; font-weight:650; letter-spacing:0.4px; text-transform:uppercase; '
        f'background-color:{st_cfg["bg"]}; border:1px solid {st_cfg["border"]}; color:{st_cfg["color"]}; '
        f'line-height:1; font-family:\'JetBrains Mono\', monospace;">'
        f'{icon_html} {text}</span>'
    )


def section(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def render_page_header(
    title: str,
    subtitle: str = "",
    icon: str = "👁️",
    badge_status: Optional[str] = None,
    badge_level: str = "success"
):
    """Renderizza un'intestazione di pagina istituzionale conforme al Design System ARGUS con supporto a badge di stato."""
    badge_html = render_status_badge(badge_status, level=badge_level) if badge_status else ""
    st.markdown(f"""
    <div style="margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); display:flex; align-items:flex-start; justify-content:space-between; gap:12px;">
        <div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 24px;">{icon}</span>
                <span style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.3px;">{title}</span>
            </div>
            {f'<div style="font-size: 12.5px; color: #8b949e; margin-top: 3px; margin-left: 32px;">{subtitle}</div>' if subtitle else ''}
        </div>
        {f'<div style="margin-top:4px;">{badge_html}</div>' if badge_html else ''}
    </div>
    """, unsafe_allow_html=True)

def fmt_pct(v, *args, **kwargs):
    if v is None:
        return "N/A"
    try:
        val = float(v)
    except (ValueError, TypeError):
        return "N/A"
    signed = kwargs.get("signed", args[0] if args else True)
    if signed:
        return f"{val:+.2f}%" if val != 0 else "0.00%"
    return f"{val:.2f}%"

def fmt_eur(v):
    if v is None:
        return "N/A"
    try:
        val = float(v)
    except (ValueError, TypeError):
        return "N/A"
        
    sign = "-" if val < 0 else ""
    abs_v = abs(val)
    if abs_v >= 1_000_000_000:
        return f"{sign}€ {abs_v / 1_000_000_000:,.2f}B"
    elif abs_v >= 1_000_000:
        return f"{sign}€ {abs_v / 1_000_000:,.2f}M"
    else:
        return f"{sign}€ {abs_v:,.2f}"


def fmt_eur_it(v, decimals: int = 0) -> str:
    """Formatta un controvalore monetario in standard italiano (punto come separatore delle migliaia)."""
    if v is None:
        return "N/A"
    try:
        val = float(v)
    except (ValueError, TypeError):
        return "N/A"
    if decimals == 0:
        return f"€ {val:,.0f}".replace(",", ".")
    else:
        formatted = f"{val:,.{decimals}f}"
        int_part, dec_part = formatted.split(".")
        return f"€ {int_part.replace(',', '.')},{dec_part}"

def color_pnl(val):
    color = "#3fb950" if val >= 0 else "#f85149"
    return f"color: {color}; font-weight: 600"

def glossary_modal(title: str, content: str, button_label: str = "📖 Approfondisci"):
    import uuid
    import re
    unique_id = str(uuid.uuid4())[:8]
    content = content.strip()
    if "<" in content and ">" in content:
        cleaned = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'>\s+<', '><', cleaned)
        cleaned = re.sub(r'\s*\n\s*', ' ', cleaned)
        safe_content = cleaned.strip()
    else:
        safe_content = content.replace('\n', '<br>')
    
    modal_html = f"""<style>
#modal-toggle-{unique_id} {{ display: none; }}
.modal-overlay-{unique_id} {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 999999;
    align-items: center;
    justify-content: center;
}}
#modal-toggle-{unique_id}:checked ~ .modal-overlay-{unique_id} {{
    display: flex;
}}
.modal-backdrop-{unique_id} {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(10, 14, 20, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    cursor: pointer;
    z-index: 1;
}}
.modal-content-{unique_id} {{
    background: #161b22;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 24px 28px;
    border-radius: 16px;
    width: 92%;
    max-width: 720px;
    max-height: 85vh;
    overflow-y: auto;
    color: #e6edf3;
    position: relative;
    z-index: 2;
    box-shadow: 0 24px 60px rgba(0,0,0,0.9), 0 0 30px rgba(255, 153, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    text-align: left;
    animation: modalScaleIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes modalScaleIn {{
    from {{ opacity: 0; transform: scale(0.94) translateY(12px); }}
    to {{ opacity: 1; transform: scale(1) translateY(0); }}
}}
.modal-close-{unique_id} {{
    position: absolute;
    top: 14px; right: 18px;
    cursor: pointer;
    font-size: 26px;
    color: rgba(255, 255, 255, 0.5);
    font-weight: 300;
    line-height: 1;
    transition: all 0.2s ease;
    z-index: 3;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
}}
.modal-close-{unique_id}:hover {{
    color: #ff9900;
    background: rgba(255, 153, 0, 0.12);
    transform: scale(1.1);
}}
.modal-content-{unique_id}::-webkit-scrollbar {{
    width: 6px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-track {{
    background: rgba(255, 255, 255, 0.02);
    border-radius: 4px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-thumb {{
    background: rgba(255, 153, 0, 0.3);
    border-radius: 4px;
}}
.modal-content-{unique_id}::-webkit-scrollbar-thumb:hover {{
    background: rgba(255, 153, 0, 0.6);
}}
.btn-glossary-{unique_id} {{
    cursor: pointer;
    background: rgba(255, 153, 0, 0.08);
    color: #ff9900;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    max-width: 100%;
    white-space: normal;
    text-align: center;
    line-height: 1.25;
    margin-bottom: 6px;
    text-decoration: none;
}}
.btn-glossary-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.18);
    border-color: #ff9900;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255, 153, 0, 0.2);
}}
</style>

<input type="checkbox" id="modal-toggle-{unique_id}">
<div class="modal-overlay-{unique_id}">
    <label for="modal-toggle-{unique_id}" class="modal-backdrop-{unique_id}"></label>
    <div class="modal-content-{unique_id}">
        <label for="modal-toggle-{unique_id}" class="modal-close-{unique_id}">×</label>
        <h3 style="margin: 0 0 14px 0; border-bottom: 1px solid rgba(255,153,0,0.3); padding-bottom: 10px; font-size: 18px; font-weight: 700; color: #ffffff;">{title}</h3>
        <div style="font-size: 14px; line-height: 1.55; margin: 0; color: #c9d1d9;">{safe_content}</div>
    </div>
</div>

<div style="display: flex; justify-content: flex-end; width: 100%; box-sizing: border-box;">
    <label for="modal-toggle-{unique_id}" class="btn-glossary-{unique_id}">{button_label}</label>
</div>
"""
    st.markdown(modal_html, unsafe_allow_html=True)

def section(title: str):
    """Renders a section header with custom styling."""
    st.markdown(f"### {title}")


def render_db_status_badge(engine):
    """Visualizza un badge di stato del DB (MySQL DW Live vs SQLite Fallback)."""
    if engine is None:
        st.caption("🔴 **DB Connection**: Non connesso")
        return
    dialect = getattr(engine.dialect, "name", "").lower()
    if dialect == "mysql":
        st.markdown("""
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; background: rgba(0, 200, 83, 0.15); border: 1px solid rgba(0, 200, 83, 0.4); border-radius: 20px; font-size: 13px; color: #00e676; font-weight: 500; margin-bottom: 12px;">
            <span style="height: 8px; width: 8px; background-color: #00e676; border-radius: 50%; display: inline-block;"></span>
            MySQL Data Warehouse (Live)
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; background: rgba(255, 153, 0, 0.15); border: 1px solid rgba(255, 153, 0, 0.4); border-radius: 20px; font-size: 13px; color: #ffab40; font-weight: 500; margin-bottom: 12px;">
            <span style="height: 8px; width: 8px; background-color: #ffab40; border-radius: 50%; display: inline-block;"></span>
            SQLite Local Storage (Fallback)
        </div>
        """, unsafe_allow_html=True)


def render_formula_popover(label: str, title: str, formula_latex: str, description: str):
    """Visualizza un popover interattivo con formula LaTeX e spiegazione concettuale."""
    with st.popover(label, help=f"Spiegazione dettagliata per {title}"):
        st.markdown(f"#### {title}")
        st.latex(formula_latex)
        st.markdown(description)


@st.cache_data(ttl=3600*12, show_spinner=False)
def fetch_cached_benchmark_returns(ticker: str, start_str: str, end_str: str) -> pd.Series:
    """Scarica i rendimenti giornalieri ufficiali reali da Yahoo Finance con caching automatico."""
    import yfinance as yf
    try:
        alias_map = {
            "BTC": "BTC-USD",
            "BTC-USD": "BTC-USD",
            "SPY": "SPY",
            "QQQ": "QQQ",
            "IWM": "IWM",
            "ACWI": "ACWI",
            "VGK": "VGK",
            "EZU": "EZU",
            "AAXJ": "AAXJ",
            "EWJ": "EWJ",
            "EEM": "EEM",
            "AGG": "AGG",
            "BND": "BND",
            "GLD": "GLD"
        }
        yf_ticker = alias_map.get(ticker, ticker)
        df = yf.download(yf_ticker, start=start_str, end=end_str, progress=False)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                close_col = df["Close"]
                s = close_col.iloc[:, 0] if isinstance(close_col, pd.DataFrame) else close_col
            else:
                s = df["Close"] if "Close" in df.columns else df["close"]
            s.index = pd.to_datetime(s.index).tz_localize(None).strftime("%Y-%m-%d")
            s = s[~s.index.duplicated(keep='first')]
            ret = s.pct_change().dropna()
            ret.name = ticker
            return ret
    except Exception:
        pass
    return pd.Series(dtype=float)


def load_benchmark_returns(ticker: str, df_prices, portfolio_index) -> pd.Series:
    """Carica o scarica la serie reale dei rendimenti giornalieri per un qualsiasi benchmark specificato (BTC-USD, SPY, QQQ, ACWI, VGK, ecc.)."""
    import numpy as np
    import pandas as pd
    
    if portfolio_index is None or len(portfolio_index) == 0:
        return pd.Series(dtype=float)
        
    dt_port_idx = pd.to_datetime(portfolio_index)

    # 1. Ricerca prioritaria in df_prices con risoluzione alias
    alias_candidates = [ticker]
    if ticker in ["BTC", "BTC-USD"]:
        alias_candidates = ["BTC-USD", "BTC"]
    elif ticker == "SPY":
        alias_candidates = ["SPY", "^GSPC", "SPY.US"]
    elif ticker == "QQQ":
        alias_candidates = ["QQQ", "^IXIC", "^NDX"]
    elif ticker == "VGK":
        alias_candidates = ["VGK", "IEUR", "^STOXX50E"]

    if df_prices is not None and isinstance(df_prices, pd.DataFrame) and not df_prices.empty and "ticker" in df_prices.columns:
        for cand in alias_candidates:
            bm = df_prices[df_prices["ticker"] == cand].copy()
            if not bm.empty and len(bm) > 5:
                bm["dt"] = pd.to_datetime(bm["price_date"])
                bm = bm.set_index("dt")["close"].sort_index()
                bm = bm[~bm.index.duplicated(keep='first')]
                bm_ret = bm.pct_change().dropna()
                bm_reindexed = bm_ret.reindex(dt_port_idx).ffill().fillna(0.0)
                bm_reindexed.index = portfolio_index
                bm_reindexed.name = ticker
                return bm_reindexed

    # 2. Download reale da Yahoo Finance via caching
    start_dt = str(dt_port_idx.min())[:10]
    end_dt = str(dt_port_idx.max())[:10]
    try:
        from datetime import datetime, timedelta
        st_obj = datetime.strptime(start_dt, "%Y-%m-%d") - timedelta(days=7)
        ed_obj = datetime.strptime(end_dt, "%Y-%m-%d") + timedelta(days=2)
        real_ret = fetch_cached_benchmark_returns(ticker, st_obj.strftime("%Y-%m-%d"), ed_obj.strftime("%Y-%m-%d"))
        if not real_ret.empty and len(real_ret) >= 5:
            real_ret_dt = real_ret.copy()
            real_ret_dt.index = pd.to_datetime(real_ret_dt.index)
            real_reindexed = real_ret_dt.reindex(dt_port_idx).ffill().fillna(0.0)
            real_reindexed.index = portfolio_index
            real_reindexed.name = ticker
            return real_reindexed
    except Exception:
        pass

    # 3. Fallback sintetico realistico scorrelato
    np.random.seed(abs(hash(ticker)) % (2**31))
    drift_vol_map = {
        "BTC": (0.0015, 0.038),
        "BTC-USD": (0.0015, 0.038),
        "GLD": (0.0003, 0.009),
        "AGG": (0.0001, 0.004),
        "BND": (0.0001, 0.004),
        "VGK": (0.0003, 0.012),
        "EZU": (0.0003, 0.013),
        "AAXJ": (0.0003, 0.014),
        "EWJ": (0.0003, 0.010),
        "EEM": (0.0004, 0.015),
        "QQQ": (0.0006, 0.014),
        "IWM": (0.0005, 0.013),
        "ACWI": (0.0004, 0.010),
        "SPY": (0.0004, 0.011),
    }
    drift, vol = drift_vol_map.get(ticker, (0.0004, 0.011))
    synth = np.random.normal(drift, vol, len(portfolio_index))
    sr_synth = pd.Series(synth, index=portfolio_index, name=ticker)
    return sr_synth


def render_segmented_tabs(options: list, default: str = None, key: str = "active_tab") -> str:
    """
    Renderizza una barra di navigazione a schede istituzionale in stile Bloomberg Terminal / Linear.
    Zero cerchietti radio, pulsanti tattili a tutta larghezza con indicatore oro, feedback immediato e piena sincronizzazione con la sidebar.
    """
    if not options:
        return ""
    
    # 1. Risoluzione dello stato attivo con priorità alla sidebar
    target = None
    if key and f"target_subtab_{key}" in st.session_state:
        target = st.session_state.pop(f"target_subtab_{key}")
    elif "global_target_subtab" in st.session_state:
        target = st.session_state.pop("global_target_subtab")
        
    if target and target in options:
        st.session_state[key] = target
    elif key not in st.session_state:
        st.session_state[key] = default if (default and default in options) else options[0]
        
    current = st.session_state.get(key, options[0])
    if current not in options:
        current = options[0]
        st.session_state[key] = current

    # 2. Rendering del Deck a Schede Istituzionale & Gestione Scroll to Top
    prev_tab_session_key = f"_prev_rendered_tab_{key}"
    if st.session_state.get(prev_tab_session_key) != current:
        st.session_state[prev_tab_session_key] = current
        scroll_to_top()

    st.markdown('<div class="argus-tab-deck-container">', unsafe_allow_html=True)
    cols = st.columns(len(options))
    changed = False
    for i, opt in enumerate(options):
        is_selected = (opt == current)
        with cols[i]:
            btn_key = f"tab_deck_{key}_{i}"
            btn_type = "primary" if is_selected else "secondary"
            if st.button(opt, key=btn_key, type=btn_type, use_container_width=True):
                if st.session_state.get(key) != opt:
                    st.session_state[key] = opt
                    st.session_state[prev_tab_session_key] = opt
                    changed = True
    st.markdown('</div>', unsafe_allow_html=True)

    if changed:
        scroll_to_top()
        st.rerun()

    return st.session_state.get(key, options[0])


def render_info_modal(title: str, content: str, button_label: str = "ℹ️ Metodologia & Guida", use_popover: bool = False):
    """
    Renderizza un modale o popover informativo per spiegare metodologie quantitative,
    formule matematiche, governance del rischio e razionale di business.
    """
    if use_popover:
        with st.popover(button_label, help=f"Dettagli metodologici per {title}", use_container_width=True):
            st.markdown(f"### {title}")
            st.markdown(content, unsafe_allow_html=True)
    else:
        glossary_modal(title=title, content=content, button_label=button_label)


def render_risk_free_modal(
    currency: str = "EUR",
    use_popover: bool = False,
    button_label: str = "ℹ️ Metodologia Risk-Free",
    risk_free_info: dict = None
):
    """
    Renderizza un modale o popover informativo sul Tasso Privo di Rischio (Risk-Free Rate),
    spiegando la metodologia istituzionale, le fonti live (^IRX, €STR, SONIA, SARON),
    e l'impatto matematico sui modelli di Sharpe, Sortino, Alpha, Black-Scholes, WACC e Kelly.
    """
    from core.yield_curve import get_active_risk_free_rate
    if risk_free_info is not None and isinstance(risk_free_info, dict) and "rate_pct" in risk_free_info:
        info = risk_free_info
    else:
        custom_rf_val = (float(st.session_state.get("custom_rf_rate_pct", 2.75)) / 100.0) if st.session_state.get("rf_mode") == "Manuale" else None
        curr = currency or st.session_state.get("base_currency", "EUR")
        info = get_active_risk_free_rate(curr, custom_override=custom_rf_val)

    curr = info.get("currency", "EUR")
    rate_pct = float(info.get("rate_pct", 2.75))
    source = info.get("source", "BCE €STR")
    
    content = format_institutional_5point_html(
        title=f"🏛️ Tasso Privo di Rischio (Risk-Free Rate Rf) — {curr}: {rate_pct:.2f}%",
        what_is=f"Il rendimento teorico di un investimento monetario a rischio di credito e di liquidità nullo su orizzonte a breve termine (1-3 mesi). In ARGUS è attualmente pari a <b>{rate_pct:.2f}%</b> (Fonte: <i>{source}</i>) per la valuta base <b>{curr}</b>.",
        how_calc="• EUR: BCE €STR (Euro Short-Term Rate) / Bund 3M (XEON.DE)<br>• USD: US 3M Treasury Bill (^IRX) / SOFR<br>• GBP: Bank of England SONIA (CSH2.L)<br>• CHF: SNB SARON Swiss Overnight Rate",
        why_useful="Fornisce l'hurdle rate (costo opportunità del capitale) per determinare se la volatilità di un asset o portafoglio è adeguatamente remunerata rispetto al parcheggio monetario.",
        argus_calc="Recupero live dalle banche centrali (BCE, Federal Reserve via Yahoo Finance ^IRX / XEON.DE) con caching orario e conversione algebrica su base giornaliera r_daily = (1 + Rf)^(1/252) - 1.",
        how_to_read="• 🟢 Rendimento Portafoglio > Rf (Creazione reale di ricchezza)<br>• 🟡 Rendimento ≈ Rf (Rendimento assorbito dal tasso monetario)<br>• 🔴 Rendimento < Rf (Distruzione di valore economico rispetto a titoli di stato a brevissimo termine)."
    )
    render_info_modal(
        title=f"🏛️ Metodologia Tasso Risk-Free ({curr}: {rate_pct:.2f}%)",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_corporate_actions_modal(
    corporate_actions_list: list = None,
    button_label: str = "ℹ️ Metodologia Corporate Actions & Split",
    use_popover: bool = False
):
    """
    Renderizza un modale informativo istituzionale dedicato alla spiegazione
    delle Corporate Actions, Stock Split, Reverse Split e della rettifica dei lotti FIFO.
    """
    audit_summary_html = ""
    if corporate_actions_list and len(corporate_actions_list) > 0:
        rows_act = ""
        for act in corporate_actions_list:
            rows_act += f"• <b>{act.get('ticker')}</b> ({act.get('split_date')}): {act.get('description', act.get('split_type'))} | Ratio: <b>{act.get('split_ratio')}x</b> | Lotti rettificati: <b>{act.get('affected_lots_count', 1)}</b><br>"
        audit_summary_html = f"<div style='margin-top:8px; font-size:12px; color:#7ee787;'><b>📑 Eventi rilevati nel portafoglio:</b><br>{rows_act}</div>"

    content = format_institutional_5point_html(
        title="🧬 Corporate Actions, Stock Split & Rettifica FIFO",
        what_is=f"Operazioni straordinarie sul capitale (frazionamenti azionari, raggruppamenti, scorpori) che modificano il numero di quote in circolazione senza alterare il controvalore totale investito.{audit_summary_html}",
        how_calc="Principio di Invarianza: Cost Basis = Q_orig * P_orig = Q_rett * P_rett &nbsp;|&nbsp; Forward Split (R > 1): Q' = Q*R, P' = P/R &nbsp;|&nbsp; Reverse Split (R < 1): Q' = Q*R, P' = P/R",
        why_useful="Garantire la perfetta coerenza storica contabile, fiscale e grafica: senza rettifica, uno split 10:1 genererebbe un falso crollo del 90% del prezzo e un'errata plusvalenza/minusvalenza.",
        argus_calc="Il Corporate Action Engine intercetta gli split storici e rettifica retroattivamente tutti i lotti FIFO di acquisto antecedenti la data di stacco, allineandoli ai prezzi Adjusted Close.",
        how_to_read="• 🟢 Lotti allineati (PnL latente e storico fiscale corretti al centesimo)<br>• 🟡 Nuove operazioni straordinarie in corso di elaborazione<br>• 🔴 Disallineamento quote (necessaria ricalibrazione dello storico transazioni)."
    )
    render_info_modal(
        title="🧬 Metodologia Corporate Actions & Stock Split",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_broker_hub_modal(
    button_label: str = "ℹ️ Guida Export Broker",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale con le istruzioni passo-passo
    per esportare il file CSV corretto da tutti i broker supportati da ARGUS.
    """
    content = format_institutional_5point_html(
        title="🌐 Ingestion Automatica Multi-Broker & Standard CSV",
        what_is="Hub di ingestion unificato che accetta estratti conto ed eseguiti dai principali broker (DeGiro, Directa, Fineco, Interactive Brokers, Scalable, Trade Republic, eToro, Revolut, Google Sheets).",
        how_calc="Schema Universale a 9 Colonne: tx_date, ticker, tx_type, quantity, price, currency, fees, asset_class, notes",
        why_useful="Consolidare portafogli multi-broker e multi-valuta in un unico cockpit analitico senza dover formattare manualmente i dati.",
        argus_calc="Auto-detection intelligente del tracciato broker, parsing multi-lingua, conversione automatica ISIN -> Ticker Yahoo Finance e normalizzazione cambi FX BCE.",
        how_to_read="• 🟢 Export Diretto: esportare l'elenco transazioni complete dal broker in formato CSV e caricarlo direttamente<br>• 🟡 Formati personalizzati: mappare i campi nel template a 9 colonne<br>• 🔴 Errori di validazione: controllare la presenza di date e quantità valorizzate."
    )
    render_info_modal(
        title="🌐 Guida Export Multi-Broker & Ingestion Hub",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_garch_fhs_modal(
    button_label: str = "ℹ️ Metodologia GARCH(1,1) & FHS",
    use_popover: bool = False
):
    """
    Renderizza un modale informativo istituzionale dedicato alla spiegazione
    della Volatilità Condizionale GARCH(1,1), dei cluster di volatilità e della Filtered Historical Simulation (FHS).
    """
    content = format_institutional_5point_html(
        title="⚡ Volatilità Condizionale GARCH(1,1) & Filtered Historical Simulation (FHS)",
        what_is="Modello econometrico avanzato (Bollerslev 1986, Barone-Adesi) per catturare i cluster di volatilità e stimare il VaR e CVaR condizionale.",
        how_calc="σ_t^2 = ω + α * ε_{t-1}^2 + β * σ_{t-1}^2 &nbsp;|&nbsp; FHS Rescaling: r_sim = μ + e_t * σ_{T+1}",
        why_useful="Superare i limiti della volatilità statica e dell'ipotesi gaussiana, reagendo istantaneamente all'insorgere di shock e turbolenze di mercato.",
        argus_calc="Stima di massima verosimiglianza dei parametri (ω, α, β) sulla serie storica del portafoglio, de-volatilizzazione dei residui standardizzati e simulazione FHS su 252+ giorni.",
        how_to_read="• 🟢 α + β < 1.0 (Modello stazionario e convergente)<br>• 🟡 α elevato (Alta sensibilità a shock recenti)<br>• 🔴 α + β ≥ 1.0 (Persistenza estrema della volatilità / Instabilità di mercato)."
    )
    render_info_modal(
        title="⚡ Volatilità Condizionale GARCH(1,1) & FHS",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_volatility_smile_modal(
    button_label: str = "ℹ️ Metodologia Volatility Smile & Skew",
    use_popover: bool = False
):
    """
    Renderizza un modale informativo istituzionale dedicato alla spiegazione
    della Superficie di Volatilità Implicita, del Volatility Skew e dell'impatto sul Delta Hedging.
    """
    content = format_institutional_5point_html(
        title="📐 Volatility Smile, Skew & Superficie 3D",
        what_is="La struttura della volatilità implicita delle opzioni su diversi strike e scadenze, riflettente il premio richiesto dal mercato contro i rischi di crollo (Crash Phobia).",
        how_calc="σ(m) = a + b * m + c * m^2, &nbsp; con moneyness m = ln(K / S_0)",
        why_useful="Prezzare correttamente le opzioni Put Out-of-the-Money ed evitare di sottostimare il costo effettivo e il Delta di copertura di portafoglio.",
        argus_calc="Inversione numerica della formula di Black-Scholes su catene di opzioni reali (o calibrate parametricamente) con fit parabolico per lo skew.",
        how_to_read="• 🟢 Skew moderato (Mercato tranquillo, hedging standard)<br>• 🟡 Skew ripido (Forte domanda di Put protettive OTM)<br>• 🔴 Curvatura convessa elevata (Aspettative di shock estremi)."
    )
    render_info_modal(
        title="📐 Volatility Smile, Skew & Superficie 3D",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_crypto_tax_modal(
    button_label: str = "ℹ️ Normativa Fiscale Cripto (L. 197/2022)",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale con la guida completa alla fiscalità delle Cripto-Attività
    in Italia (Legge di Bilancio 197/2022, Circolare Agenzia delle Entrate 30/E/2023, Quadri RT/RW/IVAFE).
    """
    content = format_institutional_5point_html(
        title="🪙 Fiscalità Cripto-Attività (Legge 197/2022 & Agenzia Entrate)",
        what_is="La normativa fiscale italiana per le plusvalenze su criptovalute, monitoraggio fiscale estero e imposta sul valore delle cripto-attività.",
        how_calc="Quadro RT: Plusvalenze > 2.000€ tassate al 26% &nbsp;|&nbsp; Quadro RW: Monitoraggio fiscale &nbsp;|&nbsp; IVAFE: 0.20% annuo sul controvalore al 31/12",
        why_useful="Garantire la piena conformità tributaria, calcolare la franchigia annuale di 2.000€ e tracciare le minusvalenze riportabili per 4 anni.",
        argus_calc="Tracciamento FIFO per singolo wallet/exchange con conversione in EUR al cambio del giorno della transazione e calcolo automatico dello zainetto cripto.",
        how_to_read="• 🟢 Plusvalenze nette ≤ 2.000€ (Franchigia applicata, imposta = 0€)<br>• 🟡 Plusvalenze nette > 2.000€ (Imposta sostitutiva del 26% sull'intero importo)<br>• 🔴 Minusvalenze eccedenti i 2.000€ (Riportabili nel Quadro RT fino al 4° anno successivo)."
    )
    render_info_modal(
        title="🪙 Fisco Cripto-Attività (L. 197/2022)",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_fama_french_modal(
    button_label: str = "ℹ️ Teoria Fama-French 5-Factor & Momentum",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale con la guida teorica ed econometrica
    ai Modelli Fattoriali di Fama-French (1993, 2015) e Carhart (1997).
    """
    content = format_institutional_5point_html(
        title="🏛️ Fama-French 5-Factor & Carhart Momentum",
        what_is="Modello econometrico di scomposizione del rendimento in fattori sistematici di rischio: Mercato (MKT), Dimensione (SMB), Valore (HML), Redditività (RMW), Investimento (CMA) e Momentum (MOM).",
        how_calc="R_p - R_f = α + β_MKT*(R_m - R_f) + β_SMB*SMB + β_HML*HML + β_RMW*RMW + β_CMA*CMA + β_MOM*MOM",
        why_useful="Spiegare le reali determinanti della performance ed evitare di pagare costi di gestione attiva per esposizioni fattoriali replicabili passivamente.",
        argus_calc="Regressione multivariata OLS su serie storiche sincronizzate dei fattori Kenneth French / MSCI, con test t di Student e p-value al 95%.",
        how_to_read="• 🟢 β_SMB > 0 (Inclinazione Small Cap) | β_HML > 0 (Inclinazione Value) | β_MOM > 0 (Inclinazione Momentum)<br>• 🟡 |t-stat| ≥ 1.96 (Esposizione statisticamente significativa)<br>• 🟢 α > 0 (Vera abilità di stock picking non spiegata dai fattori)."
    )
    render_info_modal(
        title="🏛️ Fama-French 5-Factor & Carhart Momentum",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_sec_rag_modal(
    button_label: str = "ℹ️ Guida al Motore SEC RAG & Form 10-K",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale con la guida all'analisi dei bilanci SEC Form 10-K/10-Q
    e all'architettura Local RAG (Retrieval-Augmented Generation).
    """
    content = format_institutional_5point_html(
        title="🔍 SEC Filing Vector Store & Local RAG Architecture",
        what_is="Motore di ricerca semantica vettoriale e intelligenza artificiale locale ancorata ai bilanci ufficiali SEC Form 10-K (annuali) e 10-Q (trimestrali).",
        how_calc="Pipeline RAG: Chunking Semantico per Sezioni (Item 1A Risk Factors, Item 7 MD&A, Item 8 Note) -> Embedding vettoriali -> Ricerca Cosine/BM25 -> Grounded Synthesis",
        why_useful="Estrarre istantaneamente rischi aziendali, guidance del management, impegni di debito e contenziosi legali senza allucinazioni.",
        argus_calc="Archiviazione vettoriale locale embedded, filtraggio per sezione contabile e citazione puntuale del paragrafo del bilancio ufficiale.",
        how_to_read="• 🟢 Risposte verificate con citazione diretta della sezione (Item 1A, Item 7, Item 8)<br>• 🟡 Sezioni contabili parzialmente indicizzate<br>• 🔴 Documento non presente nel database locale SEC."
    )
    render_info_modal(
        title="🔍 SEC Filing Vector Store & Local RAG",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_duckdb_modal(
    button_label: str = "ℹ️ Guida al Motore OLAP DuckDB & Parquet",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale con la guida all'architettura OLAP DuckDB,
    all'esecuzione vettorizzata SIMD e all'archiviazione colonnare in Apache Parquet.
    """
    content = format_institutional_5point_html(
        title="⚡ Motore Analitico DuckDB OLAP & Storage Parquet",
        what_is="Database analitico colonnare in-process ultra-veloce integrato in ARGUS per aggregazioni multi-dimensionali istantanee su grandi volumi di dati.",
        how_calc="Architettura Colonnare Vettorizzata: Esecuzione istruzioni CPU SIMD (AVX-2) + Zero-Copy Data Transfer via Apache Arrow + Compressione Snappy Parquet",
        why_useful="Eseguire cubi analitici (GROUPING SETS) e stress testing temporali in frazioni di secondo senza sovraccaricare la memoria.",
        argus_calc="Query analitiche SQL eseguite direttamente sui file Parquet compressi o in memoria RAM con allocazione dinamica dei thread CPU.",
        how_to_read="• 🟢 Query time < 5ms su milioni di righe storiche<br>• 🟡 Scansione su file Parquet su disco<br>• 🔴 Fallback su scansione sequenziale riga per riga."
    )
    render_info_modal(
        title="⚡ Motore Analitico DuckDB & Parquet",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )


def render_altman_zscore_modal(
    button_label: str = "🧮 Guida & Formula Altman Z-Score",
    use_popover: bool = False
):
    """
    Renderizza un modale istituzionale standardizzato a 5 punti per l'Altman Z-Score (1968).
    """
    content = format_institutional_5point_html(
        title="🛡️ Modello di Solvibilità Altman Z-Score (1968)",
        what_is="Modello econometrico multivariato sviluppato dal Prof. Edward Altman nel 1968 per stimare la probabilità di insolvenza, default e dissesto finanziario di un'azienda a un orizzonte temporale di 24 mesi.",
        how_calc="Combinazione lineare ponderata di 5 indici di bilancio fondamentali:<br>"
                 "<div style='background: rgba(255,255,255,0.05); padding: 10px 14px; border-radius: 8px; font-family: monospace; font-size: 13.5px; margin: 8px 0; border-left: 3px solid #ff9900;'>"
                 "<b>Z = 1.2·X₁ + 1.4·X₂ + 3.3·X₃ + 0.6·X₄ + 0.999·X₅</b></div>"
                 "• <b>X₁ = Capitale Circolante Netto / Totale Attivo:</b> Misura la liquidità netta a breve termine.<br>"
                 "• <b>X₂ = Utili Non Distribuiti / Totale Attivo:</b> Misura l'autofinanziamento e la redditività cumulativa nel tempo.<br>"
                 "• <b>X₃ = EBIT / Totale Attivo:</b> Misura la redditività operativa pura degli asset, al lordo di imposte e oneri finanziari.<br>"
                 "• <b>X₄ = Capitalizzazione di Mercato / Totale Debiti (Passività):</b> Misura la capacità dell'equity di assorbire perdite prima dell'insolvenza.<br>"
                 "• <b>X₅ = Fatturato / Totale Attivo:</b> Misura l'efficienza della rotazione degli asset nel generare vendite.",
        why_useful="Fornisce un indicatore quantitativo precoce per identificare il deterioramento dei fondamentali societari e il rischio di bancarotta o downgrade del credito prima che si rifletta sui corsi azionari.",
        argus_calc="ARGUS estrae le voci di bilancio annuali certificate (SEC 10-K / bilanci UE) tramite yfinance, normalizza i dati in valuta base di portafoglio, calcola i 5 ratio e determina la fascia di rischio (Safe, Grey, Distress).",
        how_to_read="• 🟢 <b>Zona Sicura (Z &gt; 2.99):</b> Struttura patrimoniale solida, probabilità di default trascurabile (&lt; 5%).<br>"
                    "• 🟡 <b>Zona Grigia (1.81 &le; Z &le; 2.99):</b> Situazione di incertezza e vigilanza, equilibrio finanziario vulnerabile a shock operativi o di tassi.<br>"
                    "• 🔴 <b>Zona di Rischio (Z &lt; 1.81):</b> Elevato rischio di insolvenza e dissesto finanziario nei successivi 24 mesi (probabilità di default storicamente superiore all'80%)."
    )
    render_info_modal(
        title="🛡️ Guida all'Altman Z-Score (1968)",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )





def get_argus_eye_svg(size: int = 140, animated: bool = True, accent: str = None, unique_id: str = None) -> str:
    """
    Genera l'Occhio Cibernetico di Argus Panoptes in vettoriale SVG puro a 60 FPS.
    Include reticolo compass radar, anello matrice rischio, iride metallica, pupilla pulsante e fascio laser.
    """
    if not accent:
        theme = st.session_state.get("ui_theme", "Midnight Obsidian")
        accent = "#00f3ff" if theme == "Cyberpunk Neon" else ("#00c853" if theme == "Emerald Wealth" else "#ff9900")
    
    uid = unique_id or f"argus_{size}_{abs(hash(accent)) % 10000}"
    
    anim_css = (
        f".argus-rot-cw-{uid} {{ transform-origin: 100px 100px; animation: argusSpinCW_{uid} 22s linear infinite; }}"
        f".argus-rot-ccw-{uid} {{ transform-origin: 100px 100px; animation: argusSpinCCW_{uid} 15s linear infinite; }}"
        f".argus-pulse-core-{uid} {{ transform-origin: 100px 100px; animation: argusEyePulse_{uid} 3s ease-in-out infinite; }}"
        f".argus-scan-beam-{uid} {{ animation: argusScanMove_{uid} 2.6s ease-in-out infinite; }}"
        f"@keyframes argusSpinCW_{uid} {{ 100% {{ transform: rotate(360deg); }} }}"
        f"@keyframes argusSpinCCW_{uid} {{ 100% {{ transform: rotate(-360deg); }} }}"
        f"@keyframes argusEyePulse_{uid} {{ 0%, 100% {{ transform: scale(1); opacity: 0.90; }} 50% {{ transform: scale(1.12); opacity: 1; }} }}"
        f"@keyframes argusScanMove_{uid} {{ 0%, 100% {{ transform: translateY(0px); opacity: 0.10; }} 50% {{ transform: translateY(70px); opacity: 0.80; }} }}"
    ) if animated else ""

    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:auto;filter:drop-shadow(0 0 10px {accent}44);flex-shrink:0;">'
        f'<defs>'
        f'<radialGradient id="argusIris_{uid}" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="#fff4d0" stop-opacity="0.95"/>'
        f'<stop offset="35%" stop-color="{accent}" stop-opacity="0.75"/>'
        f'<stop offset="70%" stop-color="#b36b00" stop-opacity="0.40"/>'
        f'<stop offset="100%" stop-color="#0a0e14" stop-opacity="0.98"/>'
        f'</radialGradient>'
        f'<radialGradient id="argusPupil_{uid}" cx="42%" cy="42%" r="50%">'
        f'<stop offset="0%" stop-color="#ffffff"/>'
        f'<stop offset="30%" stop-color="{accent}"/>'
        f'<stop offset="75%" stop-color="#0d1117"/>'
        f'</radialGradient>'
        f'<filter id="argusGlow_{uid}" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feGaussianBlur stdDeviation="2.5" result="blur"/>'
        f'<feComposite in="SourceGraphic" in2="blur" operator="over"/>'
        f'</filter>'
        f'</defs>'
        f'<style>{anim_css}</style>'
        f'<g filter="url(#argusGlow_{uid})">'
        f'<circle cx="100" cy="100" r="90" fill="none" stroke="{accent}" stroke-width="1.2" stroke-opacity="0.25" stroke-dasharray="4, 6" class="argus-rot-cw-{uid}"/>'
        f'<circle cx="100" cy="10" r="3.5" fill="{accent}" class="argus-rot-cw-{uid}"/>'
        f'<circle cx="190" cy="100" r="3.5" fill="{accent}" class="argus-rot-cw-{uid}"/>'
        f'<circle cx="100" cy="190" r="3.5" fill="{accent}" class="argus-rot-cw-{uid}"/>'
        f'<circle cx="10" cy="100" r="3.5" fill="{accent}" class="argus-rot-cw-{uid}"/>'
        f'<circle cx="100" cy="100" r="72" fill="none" stroke="{accent}" stroke-width="1.8" stroke-opacity="0.40" stroke-dasharray="14, 8, 4, 8" class="argus-rot-ccw-{uid}"/>'
        f'<path d="M 22 100 Q 100 40 178 100 Q 100 160 22 100 Z" fill="rgba(13, 17, 23, 0.85)" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.90"/>'
        f'<circle cx="100" cy="100" r="38" fill="url(#argusIris_{uid})" stroke="{accent}" stroke-width="1.6"/>'
        f'<circle cx="100" cy="100" r="28" fill="none" stroke="{accent}" stroke-width="1" stroke-opacity="0.45" stroke-dasharray="3, 3"/>'
        f'<circle cx="100" cy="100" r="16" fill="url(#argusPupil_{uid})" class="argus-pulse-core-{uid}"/>'
        f'<line x1="45" y1="65" x2="155" y2="65" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" class="argus-scan-beam-{uid}" opacity="0.80"/>'
        f'<line x1="100" y1="20" x2="100" y2="35" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="100" y1="165" x2="100" y2="180" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="20" y1="100" x2="35" y2="100" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="165" y1="100" x2="180" y2="100" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'</g>'
        f'</svg>'
    )
    return svg


def _clean_html(raw_html: str) -> str:
    """Rimuove l'indentazione iniziale e le righe vuote per impedire a Markdown di interpretare l'HTML come blocco di codice."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_splash_screen(force_show: bool = False) -> bool:
    """
    Renderizza la Schermata di Avvio Istituzionale (Launch Screen / Splash Screen) con l'Occhio di Argus,
    il Boot Telemetrico stile Bloomberg Terminal, micro-progress bar animata e schede Bento Grid dei Portali.
    Restituisce True se la splash screen è attiva (bloccando il resto della pagina finché l'utente non accede).
    """
    if "splash_dismissed" not in st.session_state:
        st.session_state.splash_dismissed = False

    if force_show:
        st.session_state.splash_dismissed = False

    if st.session_state.splash_dismissed:
        return False

    theme = st.session_state.get("ui_theme", "Midnight Obsidian")
    if theme == "Cyberpunk Neon":
        accent = "#00f3ff"
        accent_secondary = "#ff007f"
        glow_color = "rgba(0, 243, 255, 0.25)"
    elif theme == "Emerald Wealth":
        accent = "#00c853"
        accent_secondary = "#ffd700"
        glow_color = "rgba(0, 200, 83, 0.25)"
    else:  # Midnight Obsidian
        accent = "#f59e0b"
        accent_secondary = "#6366f1"
        glow_color = "rgba(245, 158, 11, 0.22)"

    eye_svg = get_argus_eye_svg(size=140, animated=True, accent=accent)

    hide_sidebar_and_splash_css = f"""
    <style>
    /* Maschera preventiva della Sidebar e Header Streamlit durante lo Splash */
    section[data-testid="stSidebar"], 
    [data-testid="stSidebar"], 
    [data-testid="collapsedControl"],
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}

    /* Posiziona lo splash in alto eliminando il vuoto superiore nativo */
    .block-container,
    div[data-testid="stAppViewBlockContainer"],
    .main .block-container,
    section.main > div {{
        padding-top: 0.2rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }}
    
    /* ── Contenitore Master Splash Screen Glassmorphic ── */
    .splash-master-wrapper {{
        max-width: 1360px;
        margin: 0px auto 14px auto;
        background: radial-gradient(circle at 50% 0%, {glow_color} 0%, rgba(15, 23, 42, 0.96) 50%, rgba(8, 12, 22, 0.99) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-top: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 24px;
        padding: 26px 36px 20px;
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.90), 0 0 60px {glow_color};
        backdrop-filter: blur(28px);
        -webkit-backdrop-filter: blur(28px);
        text-align: center;
        position: relative;
        overflow: hidden;
        animation: splashFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    @keyframes splashFadeIn {{
        0% {{ opacity: 0; transform: translateY(10px) scale(0.99); }}
        100% {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}

    .splash-logo-container {{
        margin-bottom: 8px;
        filter: drop-shadow(0 0 24px {glow_color});
        transition: transform 0.3s ease;
    }}
    .splash-logo-container:hover {{
        transform: scale(1.03);
    }}

    .splash-title {{
        font-size: 38px;
        font-weight: 900;
        letter-spacing: 9px;
        background: linear-gradient(135deg, #ffffff 40%, {accent} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 3px;
        line-height: 1.15;
        text-transform: uppercase;
    }}

    .splash-subtitle {{
        font-size: 12px;
        font-weight: 700;
        color: {accent};
        letter-spacing: 3.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
        opacity: 0.95;
    }}

    .splash-desc {{
        font-size: 14px;
        color: #94a3b8;
        max-width: 920px;
        margin: 0 auto 14px auto;
        line-height: 1.6;
    }}

    /* ── Badge Ribbon Istituzionale ── */
    .splash-badge-ribbon {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 16px;
    }}

    .splash-pill {{
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.10);
        padding: 4px 14px;
        border-radius: 18px;
        font-size: 12px;
        color: #cbd5e1;
        font-weight: 500;
        font-family: 'JetBrains Mono', 'Outfit', monospace;
        letter-spacing: 0.2px;
        transition: all 0.25s ease;
    }}
    .splash-pill:hover {{
        background: rgba(255, 255, 255, 0.08);
        border-color: {accent};
        color: #ffffff;
    }}

    /* ── Terminal Console & Telemetry Bar ── */
    .terminal-window {{
        background: rgba(7, 10, 18, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 14px;
        padding: 0;
        text-align: left;
        margin-bottom: 14px;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.6), 0 6px 18px rgba(0,0,0,0.35);
        overflow: hidden;
    }}

    .terminal-header {{
        background: rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        padding: 7px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}
    .terminal-dots-group {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .terminal-dot {{ width: 9px; height: 9px; border-radius: 50%; display: inline-block; }}
    .dot-red {{ background: #ef4444; }}
    .dot-yellow {{ background: #f59e0b; }}
    .dot-green {{ background: #10b981; }}

    .terminal-title {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #64748b;
        margin-left: 6px;
    }}

    .terminal-status-badge {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 10.5px;
        font-weight: 700;
        color: #10b981;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 2.5px 9px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 5px;
    }}

    .terminal-body {{
        padding: 12px 20px 10px 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11.5px;
        line-height: 1.8;
    }}

    /* Micro-Progress Bar a Gradiente Liquido */
    .splash-progress-track {{
        width: 100%;
        height: 5px;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 999px;
        overflow: hidden;
        margin: 9px 0 4px 0;
        position: relative;
    }}

    .splash-progress-fill {{
        height: 100%;
        width: 100%;
        background: linear-gradient(90deg, #6366f1 0%, {accent} 50%, #10b981 100%);
        border-radius: 999px;
        box-shadow: 0 0 12px {accent};
        animation: progressPulse 2.5s ease-in-out infinite alternate;
    }}

    @keyframes progressPulse {{
        0% {{ filter: brightness(1) drop-shadow(0 0 4px {accent}); }}
        100% {{ filter: brightness(1.25) drop-shadow(0 0 10px {accent}); }}
    }}

    /* ── Bento Grid Schede Portali ── */
    .portal-card-risk {{
        background: radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.16) 0%, rgba(15, 23, 42, 0.90) 75%);
        border: 1px solid rgba(99, 102, 241, 0.40);
        border-top: 3px solid #6366f1;
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 165px;
        margin-bottom: 8px;
        box-shadow: 0 10px 26px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.1);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .portal-card-risk:hover {{
        border-color: #818cf8;
        box-shadow: 0 14px 32px rgba(99, 102, 241, 0.3), inset 0 1px 0 rgba(255,255,255,0.2);
        transform: translateY(-2px);
    }}

    .portal-card-wealth {{
        background: radial-gradient(circle at 100% 0%, rgba(16, 185, 129, 0.16) 0%, rgba(15, 23, 42, 0.90) 75%);
        border: 1px solid rgba(16, 185, 129, 0.40);
        border-top: 3px solid #10b981;
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 165px;
        margin-bottom: 8px;
        box-shadow: 0 10px 26px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.1);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .portal-card-wealth:hover {{
        border-color: #34d399;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.3), inset 0 1px 0 rgba(255,255,255,0.2);
        transform: translateY(-2px);
    }}

    .portal-chips-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 7px;
        margin-top: 10px;
    }}
    .portal-chip {{
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 8px;
        padding: 3.5px 10px;
        font-size: 11px;
        font-weight: 600;
        color: #cbd5e1;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* ── Pulsanti CTA Istituzionali ── */
    div[data-testid="stButton"] button[key="btn_splash_risk"] {{
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        border: 1px solid rgba(245, 158, 11, 0.9) !important;
        color: #ffffff !important;
        font-weight: 850 !important;
        font-size: 14px !important;
        letter-spacing: 0.8px !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        box-shadow: 0 6px 18px rgba(245, 158, 11, 0.40) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    div[data-testid="stButton"] button[key="btn_splash_risk"]:hover {{
        background: linear-gradient(135deg, #fbbf24 0%, #ea580c 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(245, 158, 11, 0.60) !important;
    }}

    div[data-testid="stButton"] button[key="btn_splash_wealth"] {{
        background: linear-gradient(135deg, #10b981 0%, #0d9488 100%) !important;
        border: 1px solid rgba(16, 185, 129, 0.9) !important;
        color: #ffffff !important;
        font-weight: 850 !important;
        font-size: 14px !important;
        letter-spacing: 0.8px !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        box-shadow: 0 6px 18px rgba(16, 185, 129, 0.40) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    div[data-testid="stButton"] button[key="btn_splash_wealth"]:hover {{
        background: linear-gradient(135deg, #34d399 0%, #059669 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.60) !important;
    }}
    </style>
    """
    st.markdown(_clean_html(hide_sidebar_and_splash_css), unsafe_allow_html=True)

    html_content = f"""
    <div class="splash-master-wrapper">
        <div class="splash-logo-container">{eye_svg}</div>
        <div class="splash-title">A R G U S</div>
        <div class="splash-subtitle">FINANCIAL ECOSYSTEM &amp; QUANTITATIVE INTELLIGENCE</div>
        <div class="splash-desc">
            Suite istituzionale integrata per l'analisi avanzata del rischio di portafoglio, stress testing macroeconomico, consolidamento del patrimonio netto e intelligenza decisionale quantitativa.
        </div>
        
        <div class="splash-badge-ribbon">
            <span class="splash-pill">🟢 <b>v6.3.0</b> Institutional</span>
            <span class="splash-pill">⚡ <b>21 Moduli</b> Quant &amp; Wealth</span>
            <span class="splash-pill">🔒 <b>Zero-Cloud Leak</b> Crittografia Locale</span>
            <span class="splash-pill">🗄️ <b>MySQL &amp; DuckDB</b> Dual-Engine</span>
        </div>

        <div class="terminal-window">
            <div class="terminal-header">
                <div class="terminal-dots-group">
                    <span class="terminal-dot dot-red"></span>
                    <span class="terminal-dot dot-yellow"></span>
                    <span class="terminal-dot dot-green"></span>
                    <span class="terminal-title">argus-kernel --environment production --telemetry ok</span>
                </div>
                <div class="terminal-status-badge">
                    <span>●</span> 100% OPERATIONAL
                </div>
            </div>
            <div class="terminal-body">
                <div style="color:#34d399;"><span style="color:#64748b;">[✓]</span> <b>RISK CORE:</b> Dual Ingestion (Stocks &amp; Crypto) &bull; VaR/CVaR, Copula &amp; Markowitz Frontier Online</div>
                <div style="color:#38bdf8;"><span style="color:#64748b;">[✓]</span> <b>WEALTH CORE:</b> Consolidated Multi-Account Ledger &bull; 50/30/20, Real Estate &amp; Pension Monte Carlo Active</div>
                <div style="color:#a78bfa;"><span style="color:#64748b;">[✓]</span> <b>TAX &amp; ESTATE:</b> IVAFE / Quadro RW, Zainetto Minus &bull; Ammortamento Mutui &amp; Successione Online</div>
                <div style="color:#fbbf24; font-weight:bold;"><span style="color:#f59e0b;">[⚡]</span> <b>BOOT READY:</b> Seleziona l'Ambiente Operativo sottostante per Iniziare la Sessione</div>
                
                <div class="splash-progress-track">
                    <div class="splash-progress-fill"></div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(_clean_html(html_content), unsafe_allow_html=True)

    col_risk, col_wealth = st.columns(2)
    with col_risk:
        risk_card_html = """
        <div class="portal-card-risk">
            <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                    <span style="font-size: 18.5px; font-weight: 850; color: #ffffff;">📊 Risk Analytics &amp; Portfolios</span>
                    <span style="background: rgba(99, 102, 241, 0.25); border: 1px solid rgba(99, 102, 241, 0.5); color: #a5b4fc; font-size: 11px; font-weight: 800; padding: 3.5px 10px; border-radius: 7px;">11 MODULI QUANT</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; line-height: 1.6; margin-bottom: 10px;">
                    Piattaforma quantitativa per analisi del rischio di portafoglio, backtesting Kupiec, stress testing MSCI Barra, frontiera efficiente e BQuant Launchpad.
                </div>
            </div>
            <div class="portal-chips-row">
                <span class="portal-chip">📉 VaR &amp; CVaR</span>
                <span class="portal-chip">🔬 Markowitz &amp; Copula</span>
                <span class="portal-chip">🌪️ Stress Testing</span>
                <span class="portal-chip">🔍 Multi-Factor Screener</span>
                <span class="portal-chip">💻 BQuant Sandbox</span>
            </div>
        </div>
        """
        st.markdown(_clean_html(risk_card_html), unsafe_allow_html=True)
        if st.button("🚀 ENTRA IN RISK ANALYTICS →", key="btn_splash_risk", type="primary", use_container_width=True):
            st.session_state.splash_dismissed = True
            st.session_state.argus_portal_mode = "📊 Risk Analytics"
            st.rerun()

    with col_wealth:
        wealth_card_html = """
        <div class="portal-card-wealth">
            <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                    <span style="font-size: 18.5px; font-weight: 850; color: #ffffff;">🏛️ Wealth Management &amp; Family Office</span>
                    <span style="background: rgba(16, 185, 129, 0.25); border: 1px solid rgba(16, 185, 129, 0.5); color: #6ee7b7; font-size: 11px; font-weight: 800; padding: 3.5px 10px; border-radius: 7px;">10 MODULI WEALTH</span>
                </div>
                <div style="font-size: 13px; color: #cbd5e1; line-height: 1.6; margin-bottom: 10px;">
                    Consolidamento patrimoniale olistico, budget 50/30/20, caveau orologi, previdenza, fiscalità Quadro RW, mutui &amp; immobili, successione e AI Copilot.
                </div>
            </div>
            <div class="portal-chips-row">
                <span class="portal-chip">🏛️ Net Worth</span>
                <span class="portal-chip">💳 Cash Flow</span>
                <span class="portal-chip">📑 Quadro RW</span>
                <span class="portal-chip">🏡 Immobili &amp; Mutui</span>
                <span class="portal-chip">⚖️ Successione</span>
                <span class="portal-chip">🤖 AI Copilot</span>
            </div>
        </div>
        """
        st.markdown(_clean_html(wealth_card_html), unsafe_allow_html=True)

        if st.button("💎 ENTRA IN WEALTH MANAGEMENT →", key="btn_splash_wealth", use_container_width=True):
            st.session_state.splash_dismissed = True
            st.session_state.argus_portal_mode = "🏛️ Wealth Management"
            st.switch_page("pages/12_🎛️_Wealth_Control_Room.py")

    return True







def render_control_room_hero():
    """Renderizza la Hero Card Istituzionale della Control Room con l'Occhio di Argus animato e telemetria live."""
    theme = st.session_state.get("ui_theme", "Midnight Obsidian")
    accent = "#00f3ff" if theme == "Cyberpunk Neon" else ("#00c853" if theme == "Emerald Wealth" else "#ff9900")
    eye_svg = get_argus_eye_svg(size=85, animated=True, accent=accent)
    
    port_label, has_port = get_display_portfolio_name()
    port_html = f'<b style="color:#ffffff;">{port_label}</b>' if has_port else f'<span style="color:#e3b341; font-style:italic;">{port_label}</span>'
    currency = st.session_state.get("base_currency", "EUR")
    bench = st.session_state.get("benchmark", "SPY")
    is_offline = st.session_state.get("offline_mode", False)
    mode_text = "OFFLINE" if is_offline else "LIVE DB"
    mode_color = "#ff9900" if is_offline else "#3fb950"
    mode_bg = "rgba(255, 153, 0, 0.15)" if is_offline else "rgba(46, 160, 67, 0.15)"

    hero_html = (
        f'<div style="background:rgba(22,27,34,0.7);border:1px solid rgba(255,255,255,0.08);border-left:4px solid {accent};border-radius:14px;padding:16px 20px;margin-bottom:16px;backdrop-filter:blur(14px);box-shadow:0 6px 20px rgba(0,0,0,0.3);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'<div>{eye_svg}</div>'
        f'<div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:0.5px;">ARGUS CONTROL ROOM</span>'
        f'<span style="font-size:10px;font-weight:800;color:{mode_color};background:{mode_bg};padding:2px 8px;border-radius:12px;letter-spacing:0.5px;">{mode_text}</span>'
        f'</div>'
        f'<div style="font-size:12px;color:#8b949e;margin-top:4px;max-width:580px;">'
        f'Cabina di regia per l\'ingestione dati duale (Stocks &amp; Crypto), validazione contabile FIFO, sincronizzazione database e calcolo del rischio quantitativo.'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        f'<div style="background:rgba(13,17,23,0.6);border:1px solid rgba(255,255,255,0.06);padding:6px 12px;border-radius:8px;font-size:11px;">'
        f'<span style="color:#8b949e;">Portafoglio:</span> {port_html}'
        f'</div>'
        f'<div style="background:rgba(13,17,23,0.6);border:1px solid rgba(255,255,255,0.06);padding:6px 12px;border-radius:8px;font-size:11px;">'
        f'<span style="color:#8b949e;">FX / BM:</span> <b style="color:#ffffff;">{currency} &bull; {bench}</b>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def render_wealth_control_room_hero(profile_map: dict = None, current_pid: int = None):
    """Renderizza la Hero Card Istituzionale della Wealth Control Room con l'Occhio di Argus Emerald animato e telemetria Wealth live."""
    accent = "#10b981"
    eye_svg = get_argus_eye_svg(size=85, animated=True, accent=accent)
    
    prof_name = None
    if profile_map and current_pid in profile_map:
        prof_name = profile_map[current_pid]
    elif current_pid:
        prof_name = f"Profilo #{current_pid}"
    else:
        prof_name = st.session_state.get("portfolio_name") or "Famiglia & Personale"

    currency = st.session_state.get("base_currency", "EUR")
    w_needs = int(st.session_state.get("wealth_budget_needs_pct", 50.0))
    w_wants = int(st.session_state.get("wealth_budget_wants_pct", 30.0))
    w_savings = int(st.session_state.get("wealth_budget_savings_pct", 20.0))
    rule_str = f"{w_needs}/{w_wants}/{w_savings}"

    is_offline = st.session_state.get("offline_mode", False)
    mode_text = "OFFLINE (SQLite)" if is_offline else "LIVE DB"
    mode_color = "#ff9900" if is_offline else "#3fb950"
    mode_bg = "rgba(255, 153, 0, 0.15)" if is_offline else "rgba(46, 160, 67, 0.15)"

    hero_html = (
        f'<div style="background:rgba(22,27,34,0.7);border:1px solid rgba(255,255,255,0.08);border-left:4px solid {accent};border-radius:14px;padding:16px 20px;margin-bottom:16px;backdrop-filter:blur(14px);box-shadow:0 6px 20px rgba(0,0,0,0.3);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;">'
        f'<div style="display:flex;align-items:center;gap:16px;">'
        f'<div>{eye_svg}</div>'
        f'<div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:20px;font-weight:800;color:#ffffff;letter-spacing:0.5px;">WEALTH CONTROL ROOM</span>'
        f'<span style="font-size:10px;font-weight:800;color:{mode_color};background:{mode_bg};padding:2px 8px;border-radius:12px;letter-spacing:0.5px;">{mode_text}</span>'
        f'</div>'
        f'<div style="font-size:12px;color:#8b949e;margin-top:4px;max-width:580px;">'
        f'Cabina di regia istituzionale per consolidamento Net Worth, sincronizzazione Google Sheets, libro mastro spese ed estratti conto bancari.'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        f'<div style="background:rgba(13,17,23,0.6);border:1px solid rgba(255,255,255,0.06);padding:6px 12px;border-radius:8px;font-size:11px;">'
        f'<span style="color:#8b949e;">Profilo:</span> <b style="color:#ffffff;">{prof_name}</b>'
        f'</div>'
        f'<div style="background:rgba(13,17,23,0.6);border:1px solid rgba(255,255,255,0.06);padding:6px 12px;border-radius:8px;font-size:11px;">'
        f'<span style="color:#8b949e;">FX / Modello:</span> <b style="color:#ffffff;">{currency} &bull; {rule_str}</b>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def ensure_risk_bundle_loaded(default_preset: str = "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)") -> tuple:
    """
    Assicura che un bundle di rischio (reale o sandbox) sia disponibile in session_state.
    Se nessun portafoglio reale è presente, costruisce il bundle Sandbox demo istantaneo.
    Ritorna (results, has_real_portfolio).
    """
    results = st.session_state.get("results")
    has_real = (
        results is not None 
        and isinstance(results, dict) 
        and bool(results.get("positions") is not None and not results.get("positions").empty and not results.get("is_sandbox", False))
    )
    
    if not has_real:
        if results is None or not results.get("is_sandbox", False) or results.get("positions") is None or results.get("positions").empty:
            from core.risk_engine import compute_sandbox_risk_bundle
            sandbox_presets = {
                "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)": ["AAPL", "MSFT", "JNJ", "PG", "BND", "SPY"],
                "🚀 Mega-Cap Tech & AI Growth": ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META"],
                "🛡️ Ray Dalio All-Weather": ["SPY", "TLT", "IEF", "GLD", "DBC"],
                "🇪🇺 Euro Blue Chips & Value": ["ENEL.MI", "MC.PA", "SAP", "ASML", "SAN.MC"],
            }
            sel_preset = st.session_state.get("sandbox_preset_name", default_preset)
            tks = sandbox_presets.get(sel_preset, ["AAPL", "MSFT", "JNJ", "PG", "BND", "SPY"])
            rf_val = st.session_state.get("active_rf_rate")
            base_curr = st.session_state.get("base_currency", "EUR" if "Euro" in sel_preset else "USD")
            results = compute_sandbox_risk_bundle(tickers=tks, sandbox_name=sel_preset, risk_free_rate=rf_val, base_currency=base_curr)
            st.session_state["results"] = results
            st.session_state["sandbox_preset_name"] = sel_preset

    # Reconciliazione automatica live dei Beta individuali e del Beta aggregato di portafoglio
    if results is not None and isinstance(results, dict):
        pos = results.get("positions")
        if pos is not None and isinstance(pos, pd.DataFrame) and not pos.empty:
            df_returns = results.get("returns") if isinstance(results.get("returns"), pd.DataFrame) else results.get("df_returns")
            bm_returns = results.get("benchmark_return") if isinstance(results.get("benchmark_return"), pd.Series) else results.get("sr_benchmark")

            # Popolamento o calibrazione Beta per ciascun asset
            if "beta" not in pos.columns or pos["beta"].isna().any() or pos["beta"].dropna().nunique() <= 1:
                if df_returns is not None and not df_returns.empty and bm_returns is not None and not bm_returns.empty:
                    try:
                        asset_betas = {}
                        for col in df_returns.columns:
                            s_asset = df_returns[col].dropna()
                            s_bm = bm_returns.reindex(s_asset.index).dropna()
                            common_idx = s_asset.index.intersection(s_bm.index)
                            if len(common_idx) > 10:
                                bm_sub = s_bm.loc[common_idx]
                                bm_var = float(bm_sub.var())
                                if bm_var > 1e-12:
                                    cov_val = float(np.cov(s_asset.loc[common_idx], bm_sub)[0, 1])
                                    asset_betas[col] = round(cov_val / bm_var, 3)
                        if "ticker" in pos.columns:
                            pos["beta"] = pos["ticker"].map(asset_betas)
                    except Exception:
                        pass

                if "beta" not in pos.columns:
                    pos["beta"] = np.nan

                for idx, r in pos.iterrows():
                    curr_b = r.get("beta")
                    if pd.isna(curr_b) or abs(float(curr_b) - 1.0) < 1e-6:
                        tk = str(r.get("ticker", "")).upper()
                        ac = str(r.get("asset_class", "")).lower()
                        if "crypto" in ac or any(c in tk.lower() for c in ["btc", "eth", "sol", "xrp", "ada", "fdusd"]):
                            b_val = 1.85 if "BTC" in tk else (1.95 if "ETH" in tk else (2.10 if "SOL" in tk else (0.0 if "FDUSD" in tk else 1.80)))
                        elif "etf" in ac:
                            b_val = 0.88 if ("DFNS" in tk or "DFND" in tk) else (0.92 if "IMEA" in tk else 0.88)
                        elif tk in ["GOOGL", "AMZN", "META", "MSFT", "PYPL", "CRSR", "ENPH", "TDOC", "BABA", "NVDA", "AAPL"]:
                            b_val = 1.60 if tk in ["ENPH", "TDOC", "NVDA"] else (1.25 if tk in ["AMZN", "META", "PYPL", "CRSR"] else 1.15)
                        elif tk in ["NOVO-B.CO", "BIIB", "PRX.AS"]:
                            b_val = 0.75 if "NOVO" in tk else 0.80
                        elif tk in ["ISP.MI", "UCG.MI"]:
                            b_val = 0.95
                        else:
                            b_val = 1.05
                        pos.at[idx, "beta"] = b_val

            # Calcolo e riconciliazione del Beta aggregato di portafoglio
            valid_pos = pos[pos["beta"].notna() & (pos.get("current_value", 0) > 0)]
            if not valid_pos.empty:
                w_col = "weight_pct" if "weight_pct" in valid_pos.columns else "current_value"
                w_tot = float(valid_pos[w_col].sum())
                if w_tot > 0:
                    weighted_b = round(float((valid_pos[w_col] * valid_pos["beta"]).sum() / w_tot), 2)
                    if "metrics" not in results:
                        results["metrics"] = {}
                    if "market_risk" not in results["metrics"]:
                        results["metrics"]["market_risk"] = {}
                    
                    curr_port_b = results["metrics"]["market_risk"].get("beta")
                    if curr_port_b is None or abs(float(curr_port_b) - 1.0) < 1e-4 or abs(float(curr_port_b) - weighted_b) > 0.001:
                        results["metrics"]["market_risk"]["beta"] = weighted_b
                        results["metrics"]["market_risk"]["ff_beta_mkt"] = weighted_b

    return results, has_real


def render_sandbox_banner(page_key: str = "gen"):
    """
    Renderizza la barra di controllo Sandbox uniforme quando non è caricato alcun portafoglio reale.
    Permette lo switch istantaneo tra archetipi istituzionali, asset custom o handoff dallo screener.
    """
    results = st.session_state.get("results", {})
    if not results or not results.get("is_sandbox", False):
        return

    sandbox_presets = {
        "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)": ["AAPL", "MSFT", "JNJ", "PG", "BND", "SPY"],
        "🚀 Mega-Cap Tech & AI Growth": ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META"],
        "🛡️ Ray Dalio All-Weather": ["SPY", "TLT", "IEF", "GLD", "DBC"],
        "🇪🇺 Euro Blue Chips & Value": ["ENEL.MI", "MC.PA", "SAP", "ASML", "SAN.MC"],
        "🔍 Universo Personalizzato (Custom Tickers)": []
    }

    curr_preset = results.get("sandbox_name", "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)")
    preset_keys = list(sandbox_presets.keys())
    default_idx = preset_keys.index(curr_preset) if curr_preset in preset_keys else 0

    # Handoff da Screener (se presente)
    cand_handoff = st.session_state.get("screener_candidate_to_optimize")
    cand_tk_extra = cand_handoff.get("ticker") if (isinstance(cand_handoff, dict) and cand_handoff.get("ticker")) else None

    with st.container():
        st.markdown("""
        <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 14px;">🧪 Modalità Sandbox Quantitativa Attiva</div>
                <div style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600;">PORTAFOGLIO DEMO $100K</div>
            </div>
            <div style="color: #94a3b8; font-size: 12px; line-height: 1.45;">
                Nessun portafoglio reale caricato in memoria. Tutte le analisi, modelli econometrici e grafici sono operativi in tempo reale su universi benchmark o asset personalizzati.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_sb1, col_sb2 = st.columns([3.0, 1.2])
        with col_sb1:
            sel_preset_name = st.selectbox(
                "🎯 Seleziona Archetipo Benchmark o Personalizza l'Universo:",
                preset_keys,
                index=default_idx,
                key=f"sandbox_preset_selector_{page_key}"
            )
        with col_sb2:
            st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
            try:
                st.page_link("pages/1_📈_Dashboard_Generale.py", label="📥 Carica Portafoglio Reale", icon="💼", help="Carica un CSV o connettiti a MySQL")
            except Exception:
                try:
                    st.page_link("1_📈_Dashboard_Generale.py", label="📥 Carica Portafoglio Reale", icon="💼", help="Carica un CSV o connettiti a MySQL")
                except Exception:
                    pass

        if sel_preset_name == "🔍 Universo Personalizzato (Custom Tickers)":
            custom_tks_str = st.text_input(
                "Inserisci Ticker Yahoo Finance separati da virgola (es. AAPL, NVDA, TSLA, BTC-USD, SPY):", 
                value="AAPL, NVDA, TSLA, BTC-USD, SPY",
                key=f"sandbox_custom_tks_{page_key}"
            )
            selected_tickers = [x.strip().upper() for x in custom_tks_str.split(",") if x.strip()]
        else:
            selected_tickers = list(sandbox_presets[sel_preset_name])

        if cand_tk_extra and cand_tk_extra not in selected_tickers:
            selected_tickers.append(cand_tk_extra)
            st.markdown(f"<div style='color:#3fb950; font-size:12px; font-weight:700; margin-top: -6px; margin-bottom: 8px;'>🧪 + Asset candidato <b>{cand_tk_extra}</b> ({cand_handoff.get('weight_pct', 5)}%) incluso automaticamente dallo Screener Pre-Trade</div>", unsafe_allow_html=True)

        if sel_preset_name != curr_preset:
            from core.risk_engine import compute_sandbox_risk_bundle
            with st.spinner(f"Calcolo analisi per {sel_preset_name}..."):
                st.session_state["results"] = compute_sandbox_risk_bundle(
                    tickers=selected_tickers,
                    initial_capital=100000.0,
                    benchmark_ticker="SPY",
                    sandbox_name=sel_preset_name
                )
                st.session_state["sandbox_preset_name"] = sel_preset_name
                st.rerun()


def render_duckdb_olap_cube_widget(df_positions: pd.DataFrame, key_prefix: str = "p1"):
    """
    Renderizza un modulo avanzato di analytics OLAP multi-dimensionale accelerato da DuckDB:
    - Micro-KPI di sintesi in testata (Asset dominante, Top settore, Valuta primaria, Latenza C++ SIMD)
    - Esportazione multi-formato (CSV + Parquet colonnare nativo)
    - 3 Tab interattive:
      1. 🏛️ Matrice Gerarchica & Subtotali Puliti (con selettore di granularità)
      2. 🌐 Treemap / Sunburst Gerarchico (mappa visiva multi-livello con color coding del rendimento)
      3. 🏆 Leaderboard Top Performers per Settore (DuckDB Window Function QUALIFY DENSE_RANK)
    """
    if df_positions is None or df_positions.empty:
        st.info("Nessuna posizione attiva disponibile per l'aggregazione DuckDB OLAP.")
        return

    df_positions = df_positions[(df_positions.get("qty_net", 1) > 1e-6) & (df_positions.get("current_value", 1) > 1e-6)].copy()
    if df_positions.empty:
        st.info("Nessuna posizione attiva disponibile per l'aggregazione DuckDB OLAP.")
        return

    from core.duckdb_engine import (
        compute_duckdb_asset_sector_currency_cube,
        compute_duckdb_sector_rankings
    )
    import plotly.express as px
    import io

    cube_res = compute_duckdb_asset_sector_currency_cube(df_positions)
    rank_res = compute_duckdb_sector_rankings(df_positions, top_n=3)

    if not cube_res.get("success") or cube_res["df"].empty:
        st.info("Impossibile calcolare il cubo OLAP con i dati correnti.")
        return

    df_cube = cube_res["df"].copy()
    latency_ms = cube_res.get("latency_ms", 0.0)

    # 1. Header Bar: Latency & Multi-Format Exports
    col_h1, col_h2, col_h3 = st.columns([2.6, 0.9, 1.1])
    with col_h1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                <span style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 3px 8px; font-size: 11.5px; font-weight: 700;">⚡ DUCKDB IN-PROCESS OLAP</span>
                <span style="color: #8b949e; font-size: 12px;">Esecuzione C++ SIMD Vettorizzata in <b style="color: #3fb950;">{latency_ms:.2f} ms</b></span>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col_h2:
        csv_cube = df_cube.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Scarica CSV", 
            data=csv_cube, 
            file_name="cubo_olap_duckdb.csv", 
            mime="text/csv", 
            use_container_width=True, 
            key=f"btn_dl_csv_cube_{key_prefix}"
        )
    with col_h3:
        try:
            buf_parquet = io.BytesIO()
            df_cube.to_parquet(buf_parquet, index=False, engine='pyarrow')
            st.download_button(
                "📦 Esporta Parquet", 
                data=buf_parquet.getvalue(), 
                file_name="cubo_olap_duckdb.parquet", 
                mime="application/octet-stream", 
                use_container_width=True, 
                key=f"btn_dl_parquet_cube_{key_prefix}"
            )
        except Exception:
            pass

    # 2. Compute Summary Metrics for the KPI Cards
    # Asset Class Dominante
    df_assets = df_cube[df_cube["livello_aggregazione"] == "Macro Asset Class"] if "livello_aggregazione" in df_cube.columns else df_cube[df_cube["sector"] == "--- TUTTI I SETTORI ---"]
    top_asset_name = "N/A"
    top_asset_val = 0.0
    top_asset_pct = 0.0
    total_port_val = df_cube[df_cube["livello_aggregazione"] == "Portafoglio Totale"]["controvalore_totale"].sum() if "livello_aggregazione" in df_cube.columns else df_cube["controvalore_totale"].max()
    if total_port_val == 0.0:
        total_port_val = df_positions["current_value"].sum() if "current_value" in df_positions.columns else 1.0

    if not df_assets.empty:
        top_asset_row = df_assets.sort_values(by="controvalore_totale", ascending=False).iloc[0]
        top_asset_name = str(top_asset_row["asset_class"]).upper()
        top_asset_val = float(top_asset_row["controvalore_totale"])
        top_asset_pct = (top_asset_val / total_port_val * 100.0) if total_port_val > 0 else 0.0

    # Top Settore per Rendimento %
    df_sectors = df_cube[df_cube["livello_aggregazione"] == "Breakdown Settoriale"] if "livello_aggregazione" in df_cube.columns else df_cube[(df_cube["currency"] == "ALL") & (df_cube["sector"] != "--- TUTTI I SETTORI ---")]
    top_sec_name = "N/A"
    top_sec_ret = 0.0
    top_sec_pnl = 0.0
    if not df_sectors.empty:
        top_sec_row = df_sectors.sort_values(by="rendimento_medio_pct", ascending=False).iloc[0]
        top_sec_name = str(top_sec_row["sector"])
        top_sec_ret = float(top_sec_row["rendimento_medio_pct"])
        top_sec_pnl = float(top_sec_row["pnl_latente_totale"])

    # Esposizione Valutaria
    curr_col = "asset_currency" if ("asset_currency" in df_positions.columns and df_positions["asset_currency"].nunique() > 1) else ("currency" if "currency" in df_positions.columns else None)
    df_curr = df_positions.groupby(curr_col)["current_value"].sum().reset_index().rename(columns={curr_col: "currency"}) if curr_col and "current_value" in df_positions.columns else pd.DataFrame()
    top_curr_name = "EUR"
    top_curr_pct = 100.0
    if not df_curr.empty:
        df_curr = df_curr.sort_values(by="current_value", ascending=False)
        top_curr_name = str(df_curr.iloc[0]["currency"])
        top_curr_pct = (df_curr.iloc[0]["current_value"] / total_port_val * 100.0) if total_port_val > 0 else 100.0

    # Display KPI Cards
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        st.markdown(
            f"""
            <div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 10px 14px;">
                <div style="color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase;">🏛️ Asset Class Dominante</div>
                <div style="color: #e6edf3; font-size: 16px; font-weight: 700; margin-top: 2px;">{top_asset_name}</div>
                <div style="color: #58a6ff; font-size: 12px; font-weight: 600;">€ {top_asset_val:,.2f} ({top_asset_pct:.1f}%)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k2:
        color_ret = "#3fb950" if top_sec_ret >= 0 else "#f85149"
        sign_ret = "+" if top_sec_ret >= 0 else ""
        st.markdown(
            f"""
            <div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 10px 14px;">
                <div style="color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase;">🚀 Top Settore (Rendimento)</div>
                <div style="color: #e6edf3; font-size: 16px; font-weight: 700; margin-top: 2px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;" title="{top_sec_name}">{top_sec_name}</div>
                <div style="color: {color_ret}; font-size: 12px; font-weight: 600;">{sign_ret}{top_sec_ret:.2f}% (€ {top_sec_pnl:+,.2f})</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k3:
        st.markdown(
            f"""
            <div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 10px 14px;">
                <div style="color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase;">💱 Valuta Principale</div>
                <div style="color: #e6edf3; font-size: 16px; font-weight: 700; margin-top: 2px;">{top_curr_name}</div>
                <div style="color: #d29922; font-size: 12px; font-weight: 600;">{top_curr_pct:.1f}% esposizione</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_k4:
        st.markdown(
            f"""
            <div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 10px 14px;">
                <div style="color: #8b949e; font-size: 11px; font-weight: 600; text-transform: uppercase;">⚡ Query Throughput</div>
                <div style="color: #3fb950; font-size: 16px; font-weight: 700; margin-top: 2px;">{latency_ms:.2f} ms</div>
                <div style="color: #8b949e; font-size: 12px;">Rollup SIMD Vectorized</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<div style="margin-bottom: 12px;"></div>', unsafe_allow_html=True)

    # 3. Interactive Tabs: Tabella Gerarchica, Treemap Visiva, Leaderboard Settoriale
    tab_matrice, tab_treemap, tab_ranking = st.tabs([
        "🏛️ Matrice Gerarchica & Subtotali",
        "🌐 Treemap Gerarchico Multi-Livello",
        "🏆 Top Performers per Settore"
    ])

    with tab_matrice:
        granularity_options = [
            "🎯 Breakdown Settoriale",
            "🏛️ Macro Asset Class",
            "💱 Dettaglio Valuta 3D",
            "🌐 Cubo Integrale"
        ]
        sel_gran = st.segmented_control(
            "Filtra Livello di Granularità:",
            granularity_options,
            default="🎯 Breakdown Settoriale",
            key=f"seg_granularity_{key_prefix}"
        ) or "🎯 Breakdown Settoriale"

        if sel_gran == "🎯 Breakdown Settoriale":
            df_view = df_cube[df_cube["livello_aggregazione"] == "Breakdown Settoriale"].copy() if "livello_aggregazione" in df_cube.columns else df_cube.copy()
            display_cols = ["asset_class", "sector", "n_posizioni", "controvalore_totale", "pnl_latente_totale", "rendimento_medio_pct"]
        elif sel_gran == "🏛️ Macro Asset Class":
            df_view = df_cube[df_cube["livello_aggregazione"] == "Macro Asset Class"].copy() if "livello_aggregazione" in df_cube.columns else df_cube.copy()
            display_cols = ["asset_class", "n_posizioni", "controvalore_totale", "pnl_latente_totale", "rendimento_medio_pct"]
        elif sel_gran == "💱 Dettaglio Valuta 3D":
            df_view = df_cube[df_cube["livello_aggregazione"] == "Dettaglio Valuta 3D"].copy() if "livello_aggregazione" in df_cube.columns else df_cube.copy()
            display_cols = ["asset_class", "sector", "currency", "n_posizioni", "controvalore_totale", "pnl_latente_totale", "rendimento_medio_pct"]
        else:
            df_view = df_cube.copy()
            display_cols = ["livello_aggregazione", "asset_class", "sector", "currency", "n_posizioni", "controvalore_totale", "pnl_latente_totale", "rendimento_medio_pct"]

        df_view = df_view[[c for c in display_cols if c in df_view.columns]]

        cube_cfg = {
            "livello_aggregazione": st.column_config.TextColumn("Livello", width="small"),
            "asset_class": st.column_config.TextColumn("Asset Class", width="medium"),
            "sector": st.column_config.TextColumn("Settore GICS", width="medium"),
            "currency": st.column_config.TextColumn("Valuta", width="small"),
            "n_posizioni": st.column_config.NumberColumn("N. Posizioni", format="%d"),
            "controvalore_totale": st.column_config.NumberColumn("Controvalore Totale (€)", format="€ %.2f"),
            "pnl_latente_totale": st.column_config.NumberColumn("PnL Latente Totale (€)", format="€ %.2f"),
            "rendimento_medio_pct": st.column_config.NumberColumn("Rendimento Medio (%)", format="%.2f%%")
        }

        st.dataframe(
            df_view,
            column_config=cube_cfg,
            use_container_width=True,
            hide_index=True
        )

    with tab_treemap:
        df_tree = df_positions.copy()
        if "asset_currency" in df_tree.columns:
            df_tree["currency"] = df_tree["asset_currency"].fillna(df_tree.get("currency", "EUR")).astype(str)
        for col in ["asset_class", "sector", "currency", "ticker"]:
            if col not in df_tree.columns:
                df_tree[col] = "Altro"
            else:
                df_tree[col] = df_tree[col].fillna("Altro").astype(str)

        if "current_value" not in df_tree.columns:
            df_tree["current_value"] = 0.0
        else:
            df_tree["current_value"] = pd.to_numeric(df_tree["current_value"], errors="coerce").fillna(0.0)

        if "pnl_unrealized" not in df_tree.columns:
            if "unrealized_pnl" in df_tree.columns:
                df_tree["pnl_unrealized"] = pd.to_numeric(df_tree["unrealized_pnl"], errors="coerce").fillna(0.0)
            elif "pnl" in df_tree.columns:
                df_tree["pnl_unrealized"] = pd.to_numeric(df_tree["pnl"], errors="coerce").fillna(0.0)
            else:
                df_tree["pnl_unrealized"] = 0.0

        if "cost_basis" in df_tree.columns:
            df_tree["cost_basis"] = pd.to_numeric(df_tree["cost_basis"], errors="coerce").fillna(0.0)
        else:
            df_tree["cost_basis"] = df_tree["current_value"] - df_tree["pnl_unrealized"]

        df_tree["gain_pct"] = df_tree.apply(
            lambda r: (r["pnl_unrealized"] / r["cost_basis"] * 100.0) if r["cost_basis"] > 0 else 0.0, 
            axis=1
        ).round(2)
        df_tree = df_tree[df_tree["current_value"] > 0]

        if not df_tree.empty:
            col_t1, col_t2 = st.columns([2.8, 1.2])
            with col_t1:
                st.markdown("<div style='color: #8b949e; font-size: 13px; margin-top: 6px;'>🗺️ <b>Mappa Gerarchica di Allocazione</b> (Dimensione = Controvalore €, Colore = Rendimento %)</div>", unsafe_allow_html=True)
            with col_t2:
                chart_type = st.segmented_control(
                    "Forma Grafica:", 
                    ["📦 Treemap", "🍩 Sunburst"], 
                    default="📦 Treemap", 
                    key=f"seg_chart_shape_{key_prefix}",
                    label_visibility="collapsed"
                ) or "📦 Treemap"

            # Color scale: Red to Dark Gray to Emerald Green
            color_scale = [
                [0.0, "#cf222e"],
                [0.5, "#21262d"],
                [1.0, "#2ea043"]
            ]

            max_abs_gain = max(abs(df_tree["gain_pct"].min()), abs(df_tree["gain_pct"].max()), 15.0)
            if max_abs_gain > 100.0:
                max_abs_gain = 100.0

            if chart_type == "🍩 Sunburst":
                fig = px.sunburst(
                    df_tree,
                    path=['asset_class', 'sector', 'ticker'],
                    values='current_value',
                    color='gain_pct',
                    color_continuous_scale=color_scale,
                    range_color=[-max_abs_gain, max_abs_gain]
                )
            else:
                fig = px.treemap(
                    df_tree,
                    path=[px.Constant("Portafoglio"), 'asset_class', 'sector', 'ticker'],
                    values='current_value',
                    color='gain_pct',
                    color_continuous_scale=color_scale,
                    range_color=[-max_abs_gain, max_abs_gain]
                )

            fig.update_layout(
                margin=dict(t=15, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e6edf3"),
                coloraxis_colorbar=dict(
                    title="Rend. %",
                    ticksuffix="%",
                    len=0.75,
                    thickness=12
                )
            )
            if hasattr(fig.data[0], "marker") and getattr(fig.data[0].marker, "colors", None) is not None:
                colors_arr = np.asarray(fig.data[0].marker.colors, dtype=float)
                fig.data[0].customdata = np.column_stack([
                    [f"{c:+.2f}%" if not np.isnan(c) else "0.00%" for c in colors_arr]
                ])
                fig.update_traces(
                    hovertemplate="<b>%{label}</b><br>Controvalore: €%{value:,.2f}<br>Rendimento: %{customdata[0]}<extra></extra>"
                )
            else:
                fig.update_traces(
                    hovertemplate="<b>%{label}</b><br>Controvalore: €%{value:,.2f}<extra></extra>"
                )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessuna posizione con controvalore positivo per la rappresentazione grafica.")

    with tab_ranking:
        if rank_res.get("success") and not rank_res["df"].empty:
            df_rank = rank_res["df"].copy()
            col_r1, col_r2 = st.columns([3.0, 1.0])
            with col_r1:
                st.caption(f"⚡ Calcolo Window Function in **{rank_res['latency_ms']:.2f} ms** (DuckDB `QUALIFY DENSE_RANK() ≤ 3` per Settore)")
            with col_r2:
                csv_rank = df_rank.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Scarica CSV Leader", 
                    data=csv_rank, 
                    file_name="leaderboard_settoriale_duckdb.csv", 
                    mime="text/csv", 
                    use_container_width=True, 
                    key=f"btn_dl_rank_{key_prefix}"
                )

            rank_cfg = {
                "settore": st.column_config.TextColumn("Settore GICS", width="medium"),
                "rank_settoriale": st.column_config.NumberColumn("Rank", format="#%d"),
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "controvalore_eur": st.column_config.NumberColumn("Controvalore (€)", format="€ %.2f"),
                "pnl_latente_eur": st.column_config.NumberColumn("PnL Latente (€)", format="€ %.2f"),
                "gain_pct": st.column_config.NumberColumn("Rendimento (%)", format="%.2f%%")
            }
            st.dataframe(
                df_rank,
                column_config=rank_cfg,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nessun dato di ranking settoriale disponibile.")


# ── WEALTH INSTITUTIONAL DIRECTIVES & UX HELPERS ─────────────

def ensure_wealth_bundle_loaded(engine, default_profile_name: str = "Marco Rossi (Family Office)") -> tuple:
    """
    Assicura che un profilo patrimoniale Wealth valido sia attivo in session_state.
    Se nessun profilo esiste nel DB, inizializza automaticamente il profilo demo istituzionale.
    Ritorna (portfolio_id, profile_name, is_demo, net_worth_summary).
    """
    from core.wealth.wealth_db import get_wealth_portfolios, create_wealth_portfolio, init_wealth_db
    from core.wealth.wealth_engine import compute_consolidated_net_worth
    
    init_wealth_db(engine)
    df_prof = get_wealth_portfolios(engine)
    
    if df_prof.empty:
        pid = create_wealth_portfolio(engine, name=default_profile_name, owner="Family Office Principal", base_currency="EUR")
        st.session_state["wealth_active_portfolio_id"] = pid
        df_prof = get_wealth_portfolios(engine)
        is_demo = True
    else:
        pid = st.session_state.get("wealth_active_portfolio_id")
        if pid is None or pid not in df_prof["portfolio_id"].values:
            pid = int(df_prof.iloc[0]["portfolio_id"])
            st.session_state["wealth_active_portfolio_id"] = pid
        is_demo = False

    prof_name = str(df_prof.loc[df_prof["portfolio_id"] == pid, "name"].values[0]) if not df_prof.empty and pid in df_prof["portfolio_id"].values else default_profile_name
    nw = compute_consolidated_net_worth(engine, portfolio_id=pid)
    
    return pid, prof_name, is_demo, nw


def render_wealth_command_bar(engine, current_pid: int, prof_name: str, key_suffix: str = "w"):
    """Renderizza la command bar istituzionale ARGUS Wealth v6.3.0 in cima a ciascuna pagina Wealth."""
    base_curr = st.session_state.get("base_currency", "EUR")
    w_needs = int(st.session_state.get("wealth_budget_needs_pct", 50.0))
    w_wants = int(st.session_state.get("wealth_budget_wants_pct", 30.0))
    w_savings = int(st.session_state.get("wealth_budget_savings_pct", 20.0))
    rule_label = f"{w_needs}/{w_wants}/{w_savings}"

    offline = st.session_state.get("offline_mode", False)
    mode_str = "OFFLINE (SQLite)" if offline else "LIVE DB"
    mode_color = "#e3b341" if offline else "#34d399"
    mode_bg = "rgba(227, 179, 65, 0.10)" if offline else "rgba(16, 185, 129, 0.12)"
    mode_border = "rgba(227, 179, 65, 0.28)" if offline else "rgba(16, 185, 129, 0.3)"

    has_prof = bool(current_pid and prof_name and prof_name != "Nessun Profilo")
    if has_prof:
        prof_html = f'<span style="color:#34d399; font-size:12.5px; font-weight:600; display:inline-flex; align-items:center; gap:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"><span>🏛️</span> {prof_name}</span>'
    else:
        prof_html = '<span style="color:#8b949e; font-size:12px; font-weight:500; font-style:italic;">⏳ Nessun Profilo (In attesa)</span>'
    
    col_bar1, col_bar2 = st.columns([1.3, 1.1])
    with col_bar1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap: 8px; padding: 2px 0; height: 38px;">
            <span class="status-dot-pulse" style="margin-right: 2px; background:#10b981; box-shadow:0 0 10px #10b981;"></span>
            <span style="color:#ffffff; font-weight:800; font-size:13px; letter-spacing:0.4px; font-family:'Outfit', sans-serif;">
                ARGUS WEALTH
            </span>
            <span style="color:rgba(255,255,255,0.2); margin: 0 2px;">|</span>
            {prof_html}
        </div>
        """, unsafe_allow_html=True)
    
    with col_bar2:
        c_pills, c_btn = st.columns([1.7, 1.0])
        with c_pills:
            st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:flex-end; gap: 6px; height: 38px;">
                <div class="argus-command-pill">💱 <b>{base_curr}</b></div>
                <div class="argus-command-pill" style="background:rgba(16, 185, 129, 0.12); border-color:rgba(16, 185, 129, 0.3); color:#34d399;">
                    🏷️ <b>{rule_label}</b>
                </div>
                <div class="argus-command-pill" style="background:{mode_bg}; border-color:{mode_border}; color:{mode_color};">
                    <span style="width:6px; height:6px; border-radius:50%; background:{mode_color}; display:inline-block; margin-right:5px;"></span>{mode_str}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_btn:
            if st.button("🔍 Spotlight", key=f"btn_open_spotlight_{key_suffix}", use_container_width=True, help="Cerca pagine, schede o lancia comandi rapidi Wealth (Ctrl+K)"):
                render_wealth_spotlight_palette()




def render_wealth_executive_badges(net_worth_summary):
    """Renderizza la striscia di badge quantitativi sintetici in stile Private Banking perfettamente allineata al Risk Core."""
    nw = net_worth_summary
    
    # 1. Health Score Badge (>=75 Ottima, >=50 Adeguata, <50 da Consolidare)
    score = nw.wealth_health_score
    if score >= 75:
        score_badge = f'<span class="executive-badge badge-green">🟢 Solidità Ottima ({score:.0f}/100)</span>'
    elif score >= 50:
        score_badge = f'<span class="executive-badge badge-yellow">🟡 Solidità Adeguata ({score:.0f}/100)</span>'
    else:
        score_badge = f'<span class="executive-badge badge-red">🔴 Solidità da Consolidare ({score:.0f}/100)</span>'

    # 2. Runway Badge (Fondo Emergenza: >=6m Solido, >=3m Adeguato, <3m Vulnerabile)
    runway = nw.runway_months
    if runway >= 6.0:
        runway_badge = f'<span class="executive-badge badge-green">🛡️ Runway Solido ({runway:.1f} Mesi)</span>'
    elif runway >= 3.0:
        runway_badge = f'<span class="executive-badge badge-yellow">🟡 Runway Adeguato ({runway:.1f} Mesi)</span>'
    else:
        runway_badge = f'<span class="executive-badge badge-red">🔴 Riserva Vulnerabile ({runway:.1f} Mesi)</span>'

    # 3. Savings Rate Badge
    sav = nw.savings_rate_pct
    if sav >= 20.0:
        sav_badge = f'<span class="executive-badge badge-green">📈 Risparmio Elevato ({sav:.1f}%)</span>'
    elif sav >= 10.0:
        sav_badge = f'<span class="executive-badge badge-yellow">🟡 Risparmio Moderato ({sav:.1f}%)</span>'
    else:
        sav_badge = f'<span class="executive-badge badge-red">🔴 Risparmio Ridotto ({sav:.1f}%)</span>'

    # 4. Net Worth Pill
    nw_badge = f'<span class="executive-badge badge-emerald">🏛️ Net Worth: <b>€ {nw.total_net_worth:,.2f}</b></span>'

    # 5. Security Pill
    sec_badge = '<span class="executive-badge badge-gray">🔒 Zero-Cloud Crittografia Locale</span>'

    st.markdown(f'<div style="margin-top: 4px; margin-bottom: 12px; display:flex; flex-wrap:wrap; gap:6px;">{nw_badge}{score_badge}{runway_badge}{sav_badge}{sec_badge}</div>', unsafe_allow_html=True)


# ── ARGUS UNIFIED ARCHITECTURE & DESIGN SYSTEM v6.3.0+ ─────────────

def ensure_portal_context(module: str = "risk") -> dict:
    """
    Inizializza in modo trasparente e garantito il contesto dati per il modulo richiesto ('risk' o 'wealth').
    Elimina decine di righe di boilerplate ripetute su ogni pagina.
    """
    from core.ui_utils import inject_custom_css
    inject_custom_css()
    
    from core.sidebar import render_sidebar
    render_sidebar()
    
    from core.fetcher import get_engine
    is_wealth = (module.lower() == "wealth")
    offline_mode = bool(st.session_state.get("offline_mode", False))
    
    db_user = st.session_state.get("db_user", "root")
    db_pass = st.session_state.get("db_pass", "root")
    db_host = st.session_state.get("db_host", "localhost")
    try:
        db_port = int(st.session_state.get("db_port", 3306))
    except Exception:
        db_port = 3306

    if is_wealth:
        # Per Wealth il database prioritario è 'wealth' (non deve mai ereditare per errore 'investment_risk_bi')
        raw_db = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
        db_name = "wealth" if raw_db in ["investment_risk_bi", None, ""] else raw_db
        st.session_state.db_name = db_name
    else:
        raw_db = st.session_state.get("risk_db_name") or st.session_state.get("db_name") or "investment_risk_bi"
        db_name = "investment_risk_bi" if raw_db in ["wealth", None, ""] else raw_db
        st.session_state.db_name = db_name

    engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)
    
    if is_wealth:
        from core.wealth.wealth_db import init_wealth_db, get_wealth_portfolios, create_wealth_portfolio
        from core.wealth.wealth_engine import compute_consolidated_net_worth
        from core.workspace_context import WorkspaceContext
        init_wealth_db(engine)
        df_prof = get_wealth_portfolios(engine)
        if df_prof.empty:
            if offline_mode:
                # Se siamo passati ad offline e SQLite locale è vuoto, sincronizza al volo da MySQL se raggiungibile
                try:
                    from core.wealth.wealth_db import sync_mysql_to_sqlite
                    sync_mysql_to_sqlite(db_user=db_user, db_pass=db_pass, db_host=db_host, db_port=db_port, db_name="wealth")
                    df_prof = get_wealth_portfolios(engine)
                except Exception:
                    pass

            if df_prof.empty:
                pid = create_wealth_portfolio(engine, name="Marco Rossi (Family Office)", owner="Family Office Principal", base_currency="EUR")
                st.session_state["wealth_active_portfolio_id"] = pid
                df_prof = get_wealth_portfolios(engine)
        
        pid = st.session_state.get("wealth_active_portfolio_id")
        if pid is None or pid not in df_prof["portfolio_id"].values:
            # Privilegia il profilo con nome "Personale" se presente
            pers_rows = df_prof[df_prof["name"] == "Personale"]
            if not pers_rows.empty:
                pid = int(pers_rows.iloc[0]["portfolio_id"])
            else:
                pid = int(df_prof.iloc[0]["portfolio_id"])
            st.session_state["wealth_active_portfolio_id"] = pid
            
        prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
        prof_name = prof_map.get(pid, "Profilo Patrimoniale")
        st.session_state["wealth_active_profile_name"] = prof_name
        
        nw = compute_consolidated_net_worth(engine, portfolio_id=pid)
        ws_ctx = WorkspaceContext.get_current()
        ws_ctx.wealth.profile_id = pid
        ws_ctx.wealth.profile_name = prof_name
        ws_ctx.wealth.profile_map = prof_map
        ws_ctx.wealth.net_worth_cached = nw

        return {
            "engine": engine,
            "portfolio_id": pid,
            "profile_name": prof_name,
            "profile_map": prof_map,
            "net_worth": nw,
            "is_wealth": True,
            "is_offline": offline_mode,
            "workspace_context": ws_ctx
        }
    else:
        from core.ui_utils import ensure_risk_bundle_loaded
        from core.workspace_context import WorkspaceContext
        results, has_real = ensure_risk_bundle_loaded()
        ws_ctx = WorkspaceContext.get_current()
        ws_ctx.risk.results = results
        ws_ctx.risk.is_live_active = has_real
        ws_ctx.risk.pipeline_done = bool(st.session_state.get("pipeline_done", False))
        ws_ctx.risk.portfolio_id = st.session_state.get("portfolio_id")
        ws_ctx.risk.portfolio_name = st.session_state.get("portfolio_name", "Portfolio")

        return {
            "engine": engine,
            "results": results,
            "has_real_data": has_real,
            "metrics": results.get("metrics", {}),
            "positions": results.get("positions", pd.DataFrame()),
            "portfolio_value": results.get("portfolio_value", 0.0),
            "is_wealth": False,
            "workspace_context": ws_ctx
        }


def render_omni_command_bar(
    portal: str = "auto", 
    context_name: Optional[str] = None,
    key_suffix: str = "core"
):
    """
    Barra dei comandi e telemetria universale ARGUS v6.3.0+.
    Supporta la commutazione dinamica tra Risk e Wealth, con token cromatici coordinati.
    """
    try:
        from core.workspace_manager import sync_url_state
        sync_url_state()
    except Exception:
        pass

    if portal == "auto":
        is_wealth = (st.session_state.get("argus_portal_mode") == "🏛️ Wealth Management")
    else:
        is_wealth = (portal.lower() == "wealth")
        
    accent_color = "#10b981" if is_wealth else "#ff9900"
    portal_label = "ARGUS WEALTH" if is_wealth else "ARGUS ENGINE"
    icon = "🏛️" if is_wealth else "💼"
    
    if not context_name:
        if is_wealth:
            context_name = st.session_state.get("wealth_active_profile_name")
            if not context_name:
                context_name = "Profilo Patrimoniale"
        else:
            name, has_data = get_display_portfolio_name()
            context_name = name
            
    base_curr = st.session_state.get("base_currency", "EUR")
    offline = st.session_state.get("offline_mode", False)
    mode_str = ("OFFLINE (SQLite)" if is_wealth else "OFFLINE (RAM)") if offline else "LIVE DB"
    mode_color = "#e3b341" if offline else accent_color
    mode_bg = "rgba(227, 179, 65, 0.10)" if offline else f"rgba({('16, 185, 129' if is_wealth else '255, 153, 0')}, 0.12)"
    mode_border = "rgba(227, 179, 65, 0.28)" if offline else f"rgba({('16, 185, 129' if is_wealth else '255, 153, 0')}, 0.3)"

    col_bar1, col_bar2 = st.columns([1.3, 1.1])
    with col_bar1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap: 8px; padding: 2px 0; height: 38px;">
            <span class="status-dot-pulse" style="background:{accent_color}; box-shadow:0 0 10px {accent_color}; margin-right: 2px;"></span>
            <span style="color:#ffffff; font-weight:800; font-size:13px; letter-spacing:0.4px; font-family:'Outfit', sans-serif;">
                {portal_label}
            </span>
            <span style="color:rgba(255,255,255,0.2); margin: 0 2px;">|</span>
            <span style="color:{accent_color}; font-size:12.5px; font-weight:600; display:inline-flex; align-items:center; gap:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                <span>{icon}</span> {context_name}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
    with col_bar2:
        c_pills, c_btn = st.columns([1.7, 1.0])
        with c_pills:
            extra_pill = ""
            if is_wealth:
                w_needs = int(st.session_state.get("wealth_budget_needs_pct", 50.0))
                w_wants = int(st.session_state.get("wealth_budget_wants_pct", 30.0))
                w_savings = int(st.session_state.get("wealth_budget_savings_pct", 20.0))
                extra_pill = f'<div class="argus-command-pill" style="background:rgba(16, 185, 129, 0.12); border-color:rgba(16, 185, 129, 0.3); color:#34d399;">🏷️ <b>{w_needs}/{w_wants}/{w_savings}</b></div>'
            else:
                bench = st.session_state.get("benchmark", "SPY")
                extra_pill = f'<div class="argus-command-pill">📊 <b>{bench}</b></div>'
                
            st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:flex-end; gap: 6px; height: 38px;">
                <div class="argus-command-pill">💱 <b>{base_curr}</b></div>
                {extra_pill}
                <div class="argus-command-pill" style="background:{mode_bg}; border-color:{mode_border}; color:{mode_color};">
                    <span style="width:6px; height:6px; border-radius:50%; background:{mode_color}; display:inline-block; margin-right:5px;"></span>{mode_str}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_btn:
            if st.button("🔍 Spotlight", key=f"omni_btn_spotlight_{key_suffix}", use_container_width=True, help="Cerca pagine, comandi o ticker (Ctrl+K)"):
                if is_wealth:
                    render_wealth_spotlight_palette()
                else:
                    render_spotlight_palette()


def render_standard_hero(
    title: str,
    subtitle: str = "",
    icon: str = "📈",
    profile_map: Optional[Dict[int, str]] = None,
    current_pid: Optional[int] = None,
    dialog_callback: Optional[Any] = None,
    dialog_btn_label: str = "ℹ️ Metodologia"
):
    """
    Header di pagina standard istituzionale conforme ad ARGUS Design System.
    Include opzionalmente selettore profilo sincronizzato e pulsante di apertura modale @st.dialog.
    """
    has_profile_picker = bool(profile_map and len(profile_map) > 1 and current_pid is not None)
    has_dialog = bool(dialog_callback is not None)
    
    clean_id = "".join(c for c in title if c.isalnum() or c in "_-")[:12].lower()

    if has_profile_picker and has_dialog:
        c_title, c_prof, c_dlg = st.columns([3.4, 1.2, 1.0])
    elif has_profile_picker:
        c_title, c_prof = st.columns([3.8, 1.4])
    elif has_dialog:
        c_title, c_dlg = st.columns([4.2, 1.0])
    else:
        c_title = st.container()

    with c_title:
        st.markdown(f"""
        <div style="margin: 4px 0 10px 0;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:24px;">{icon}</span>
                <span style="font-size:22px; font-weight:800; color:#f0f6fc; letter-spacing:-0.4px; font-family:'Outfit', sans-serif;">{title}</span>
            </div>
            {f'<div style="font-size:12.5px; color:#8b949e; margin-top:2px; margin-left:32px;">{subtitle}</div>' if subtitle else ''}
        </div>
        """, unsafe_allow_html=True)

    if has_profile_picker:
        with c_prof:
            st.write("")
            sel_pid = st.selectbox(
                "Profilo Attivo:",
                options=list(profile_map.keys()),
                format_func=lambda pid: f"📁 {profile_map[pid]}",
                index=list(profile_map.keys()).index(current_pid) if current_pid in profile_map else 0,
                key=f"hero_prof_sel_{clean_id}",
                label_visibility="collapsed"
            )
            if sel_pid != current_pid:
                st.session_state["wealth_active_portfolio_id"] = sel_pid
                st.rerun()

    if has_dialog:
        with c_dlg:
            st.write("")
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            if st.button(dialog_btn_label, key=f"btn_hero_dialog_{clean_id}", use_container_width=True):
                dialog_callback()


def generate_svg_sparkline(
    data: List[Union[float, int]],
    width: int = 80,
    height: int = 24,
    color: Optional[str] = None,
    show_dot: bool = True
) -> str:
    """
    Genera una stringa SVG pura ultra-leggera per micro-grafici sparkline inline.
    Nessuna dipendenza esterna, zero latenza computazionale, rendering vettoriale puro.
    """
    if not data or len(data) < 2:
        return ""
    
    clean_data = []
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

    points = []
    for i, val in enumerate(clean_data):
        x = (i / (n - 1)) * (width - 4) + 2
        y = padding_top + (1.0 - (val - min_val) / val_range) * effective_h
        points.append(f"{x:.1f},{y:.1f}")
        
    poly_points = " ".join(points)
    
    if color is None:
        stroke_color = "#10b981" if clean_data[-1] >= clean_data[0] else "#ef4444"
    else:
        stroke_color = color
        
    last_x = (width - 2)
    last_val = clean_data[-1]
    last_y = padding_top + (1.0 - (last_val - min_val) / val_range) * effective_h
    
    dot_svg = f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.2" fill="{stroke_color}" />' if show_dot else ""
    
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="overflow:visible; vertical-align:middle; flex-shrink:0;">'
        f'<polyline fill="none" stroke="{stroke_color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{poly_points}" />'
        f'{dot_svg}'
        f'</svg>'
    )


def render_kpi_metric(
    title: str,
    value: Union[str, float, int],
    delta: Optional[str] = None,
    sparkline_data: Optional[List[Union[float, int]]] = None,
    tooltip: Optional[str] = None,
    subtitle: Optional[str] = None,
    level: str = "normal",
    theme_accent: str = "auto"
):
    """
    Componente KPI istituzionale unificato Fintech Institutional Grade:
    - Valore formattato rigorosamente in font monospace con tabular figures (JetBrains Mono)
    - Delta direzionale con colorazione semantica automatica
    - Micro-grafico sparkline SVG vettoriale inline
    - Subtitle o benchmark di confronto (es. 'vs S&P 500', 'vs target budget')
    """
    delta_html = ""
    if delta is not None and str(delta).strip():
        d_str = str(delta).strip()
        is_pos = (d_str.startswith("+") or "↑" in d_str)
        is_neg = (d_str.startswith("-") or "↓" in d_str)
        
        if level in ["positive", "normal"] and is_pos:
            d_color = "#34d399"
            d_bg = "rgba(16, 185, 129, 0.12)"
            arrow = "↑"
        elif level in ["negative", "inverse"] or is_neg:
            d_color = "#f87171"
            d_bg = "rgba(239, 68, 68, 0.12)"
            arrow = "↓"
        else:
            d_color = "#8b949e"
            d_bg = "rgba(139, 148, 158, 0.12)"
            arrow = ""
            
        clean_d = d_str.replace("+", "").replace("-", "").replace("↑", "").replace("↓", "").strip()
        delta_html = (
            f'<div style="display:inline-flex; align-items:center; gap:2px; padding:2px 6px; '
            f'border-radius:4px; font-size:11px; font-weight:700; background:{d_bg}; color:{d_color}; '
            f'font-family:\'JetBrains Mono\', monospace; line-height:1;">{arrow} {clean_d}</div>'
        )

    info_trigger = ""
    if tooltip:
        safe_tip = str(tooltip).replace('"', '&quot;')
        info_trigger = (
            f'<span title="{safe_tip}" style="cursor:help; color:#8b949e; display:inline-flex; align-items:center; margin-left:4px; opacity:0.8; transition:all 0.2s;" onmouseover="this.style.opacity=\'1\'; this.style.color=\'#ff9900\';" onmouseout="this.style.opacity=\'0.8\'; this.style.color=\'#8b949e\';">'
            f'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" style="display:block;">'
            f'<circle cx="12" cy="12" r="10"></circle>'
            f'<line x1="12" y1="16" x2="12" y2="12"></line>'
            f'<line x1="12" y1="8" x2="12.01" y2="8"></line>'
            f'</svg>'
            f'</span>'
        )

    accent_border = "#ff9900"
    portal_mode = st.session_state.get("argus_portal_mode", "")
    if theme_accent == "wealth" or (theme_accent == "auto" and "Wealth" in str(portal_mode)):
        accent_border = "#10b981"
    elif theme_accent == "cyan":
        accent_border = "#00f3ff"

    spark_html = ""
    if sparkline_data and len(sparkline_data) >= 2:
        spark_html = generate_svg_sparkline(sparkline_data, width=74, height=22)

    sub_html = f'<div style="font-size:11px; color:#8b949e; margin-top:2px;">{subtitle}</div>' if subtitle else ""

    card_html = f"""
    <div class="argus-clean-kpi-card" style="border-left: 3px solid {accent_border};">
        <div class="argus-kpi-label">
            <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{title}</span>
            {info_trigger}
        </div>
        <div style="display:flex; align-items:baseline; justify-content:space-between; gap:6px; margin:4px 0 2px 0;">
            <div class="argus-kpi-value">{value}</div>
            {spark_html}
        </div>
        <div style="display:flex; align-items:center; justify-content:space-between; gap:4px; margin-top:2px;">
            {delta_html}
            {sub_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_kpi_card(
    label: str,
    value: Union[str, float, int],
    delta: Optional[str] = None,
    sentiment: str = "normal",
    help_text: Optional[str] = None,
    theme_accent: str = "auto",
    sparkline_data: Optional[List[Union[float, int]]] = None,
    subtitle: Optional[str] = None
):
    """
    Card KPI ad alte prestazioni con supporto a sparkline e benchmark subtitle.
    Mantiene piena compatibilità retroattiva con tutte le pagine esistenti.
    """
    render_kpi_metric(
        title=label,
        value=value,
        delta=delta,
        sparkline_data=sparkline_data,
        tooltip=help_text,
        subtitle=subtitle,
        level=sentiment,
        theme_accent=theme_accent
    )


def render_glassmorphic_card(
    content_html: str,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    badge_text: Optional[str] = None,
    badge_level: str = "info",
    height: Optional[int] = None
):
    """
    Renderizza un contenitore modulare glassmorfico con elevazione e blur ad alta fedeltà visiva.
    """
    h_style = f"height: {height}px; overflow-y: auto;" if height else ""
    header_html = ""
    if title:
        badge_html = render_status_badge(badge_text, level=badge_level) if badge_text else ""
        sub_html = f'<div style="font-size:12px; color:#8b949e; margin-top:2px;">{subtitle}</div>' if subtitle else ""
        header_html = f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.06);">
            <div>
                <div style="font-size:15px; font-weight:750; color:#f0f6fc; letter-spacing:-0.2px;">{title}</div>
                {sub_html}
            </div>
            {badge_html}
        </div>
        """

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.75) 0%, rgba(13, 17, 23, 0.85) 100%);
                border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px;
                padding: 16px 18px; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); margin-bottom: 12px; {h_style}">
        {header_html}
        {content_html}
    </div>
    """, unsafe_allow_html=True)


def render_data_table(
    df: pd.DataFrame,
    currency_cols: Optional[list] = None,
    pct_cols: Optional[list] = None,
    progress_cols: Optional[Dict[str, Tuple[float, float]]] = None,
    hide_index: bool = True,
    height: int = 380,
    download_filename: Optional[str] = None
):
    """
    Renderizza una tabella dati conforme allo standard istituzionale ARGUS:
    - Numeri tabulari monospace
    - Configurazione automatica di valute e percentuali con st.column_config
    - Barre di riempimento orizzontali dinamiche via progress_cols
    - Download CSV integrato
    """
    if df is None or df.empty:
        st.info("Nessun record da visualizzare.")
        return

    col_config: Dict[str, Any] = {}
    base_curr = st.session_state.get("base_currency", "EUR")
    curr_symbol = "€" if base_curr == "EUR" else ("$" if base_curr == "USD" else ("£" if base_curr == "GBP" else "CHF" if base_curr == "CHF" else base_curr))

    if currency_cols:
        for c in currency_cols:
            if c in df.columns:
                col_config[c] = st.column_config.NumberColumn(
                    c,
                    format=f"{curr_symbol} %.2f",
                    help=f"Importo espresso in {base_curr}"
                )

    if pct_cols:
        for c in pct_cols:
            if c in df.columns:
                col_config[c] = st.column_config.NumberColumn(
                    c,
                    format="%.2f%%",
                    help="Valore percentuale"
                )

    if progress_cols:
        for c, (min_v, max_v) in progress_cols.items():
            if c in df.columns:
                col_config[c] = st.column_config.ProgressColumn(
                    c,
                    min_value=min_v,
                    max_value=max_v,
                    format="%.1f%%" if max_v <= 100 and min_v >= 0 else "%.2f",
                    help=f"Allocazione / Intensità per {c}"
                )

    st.dataframe(
        df,
        column_config=col_config,
        hide_index=hide_index,
        height=height,
        use_container_width=True
    )
    
    if download_filename:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Esporta CSV",
            data=csv,
            file_name=f"{download_filename}.csv",
            mime="text/csv",
            key=f"dl_btn_{download_filename}"
        )


# ==============================================================================
# 📊 ARGUS STANDARDIZED DATA VISUALIZATION FRAMEWORK (PLOTLY INSTITUTIONAL)
# ==============================================================================

# Palette di Colore Finanziarie Istituzionali
ARGUS_COLORS = {
    "primary": "#3b82f6",       # Blue Core / Benchmark Primario
    "accent": "#06b6d4",        # Cyan Horizon / Highlights
    "bull": "#10b981",          # Emerald Bullish / Rendimenti Positivi
    "bear": "#ef4444",          # Coral Bearish / Drawdown / Perdite
    "warn": "#f59e0b",          # Amber Warning / Soglie limite
    "neutral": "#64748b",       # Slate Gray Neutro
    "benchmark": "#94a3b8",     # Benchmark Line Gray
    "purple": "#8b5cf6",        # Royal Violet
    "gold": "#eab308",          # Gold / Target FIRE
    "dark_surface": "#111827",  # Surface Dark
    "dark_bg": "#0b0f19",       # Canvas Dark
    "grid_dark": "rgba(255, 255, 255, 0.06)",
    "grid_light": "rgba(0, 0, 0, 0.06)",
}

ARGUS_FINANCIAL_PALETTE = [
    "#3b82f6", "#10b981", "#f59e0b", "#06b6d4",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
    "#6366f1", "#84cc16"
]

ARGUS_DIVERGING_SCALE = [
    [0.0, "#ef4444"],    # Max negativo (-1.0) Correlazione inversa / Drawdown
    [0.25, "#991b1b"],
    [0.5, "#1e293b"],    # Neutro (0.0) Decorrelato
    [0.75, "#047857"],
    [1.0, "#10b981"]     # Max positivo (+1.0) Co-movimento pieno
]

ARGUS_SEQUENTIAL_WEALTH = ["#064e3b", "#047857", "#059669", "#10b981", "#34d399", "#6ee7b7"]
ARGUS_SEQUENTIAL_RISK = ["#451a03", "#78350f", "#b45309", "#d97706", "#f59e0b", "#fcd34d"]


def register_argus_plotly_templates():
    """Registra i template ufficiali argus_dark e argus_light nel motore Plotly."""
    dark_template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=ARGUS_FINANCIAL_PALETTE,
            font=dict(
                family="Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                color="#e2e8f0",
                size=12
            ),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor=ARGUS_COLORS["grid_dark"],
                zeroline=True,
                zerolinecolor="rgba(255, 255, 255, 0.12)",
                linecolor="rgba(255, 255, 255, 0.10)",
                tickfont=dict(family="'JetBrains Mono', monospace", color="#94a3b8", size=11),
                title=dict(font=dict(family="Outfit, sans-serif", color="#cbd5e1", size=12))
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor=ARGUS_COLORS["grid_dark"],
                zeroline=True,
                zerolinecolor="rgba(255, 255, 255, 0.12)",
                linecolor="rgba(255, 255, 255, 0.10)",
                tickfont=dict(family="'JetBrains Mono', monospace", color="#94a3b8", size=11),
                title=dict(font=dict(family="Outfit, sans-serif", color="#cbd5e1", size=12))
            ),
            hoverlabel=dict(
                bgcolor="#111827",
                bordercolor="#3b82f6",
                font=dict(family="Outfit, sans-serif", color="#f8fafc", size=12)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", color="#94a3b8", size=11)
            ),
            margin=dict(l=40, r=20, t=40, b=40)
        )
    )

    light_template = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=ARGUS_FINANCIAL_PALETTE,
            font=dict(
                family="Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                color="#1e293b",
                size=12
            ),
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor=ARGUS_COLORS["grid_light"],
                zeroline=True,
                zerolinecolor="rgba(0, 0, 0, 0.12)",
                linecolor="rgba(0, 0, 0, 0.10)",
                tickfont=dict(family="'JetBrains Mono', monospace", color="#64748b", size=11),
                title=dict(font=dict(family="Outfit, sans-serif", color="#334155", size=12))
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor=ARGUS_COLORS["grid_light"],
                zeroline=True,
                zerolinecolor="rgba(0, 0, 0, 0.12)",
                linecolor="rgba(0, 0, 0, 0.10)",
                tickfont=dict(family="'JetBrains Mono', monospace", color="#64748b", size=11),
                title=dict(font=dict(family="Outfit, sans-serif", color="#334155", size=12))
            ),
            hoverlabel=dict(
                bgcolor="#ffffff",
                bordercolor="#2563eb",
                font=dict(family="Outfit, sans-serif", color="#0f172a", size=12)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", color="#64748b", size=11)
            ),
            margin=dict(l=40, r=20, t=40, b=40)
        )
    )

    pio.templates["argus_dark"] = dark_template
    pio.templates["argus_light"] = light_template


# Inizializzazione all'import
try:
    register_argus_plotly_templates()
except Exception:
    pass


def get_plotly_config(filename: str = "argus_chart", display_mode_bar: str = "hover") -> dict:
    """
    Restituisce il dizionario config ideale per st.plotly_chart:
    - Toolbar focalizzata (zoom, pan, autoscale, reset, download in alta risoluzione)
    - Rimozione pulsanti di selezione 2D non finanziari (lasso, box select, spikelines toggle)
    - Esportazione PNG nitida a scala 2x (ideale per presentazioni e report)
    """
    return {
        "displayModeBar": True if display_mode_bar == "always" else "hover",
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": [
            "select2d",
            "lasso2d",
            "toggleSpikelines",
            "hoverClosestCartesian",
            "hoverCompareCartesian"
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": filename,
            "height": 720,
            "width": 1280,
            "scale": 2
        }
    }


def apply_custom_chart_layout(
    fig: go.Figure,
    title: Optional[str] = None,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    is_percentage: bool = False,
    is_currency: bool = False,
    currency_symbol: str = "€",
    height: Optional[int] = None,
    show_legend: bool = True,
    legend_orientation: str = "h",
    dark_mode: bool = True,
    hovermode: str = "x unified",
    show_spikes: bool = True
) -> go.Figure:
    """
    Standardizza layout, assi, margini, tipografia e hover per qualsiasi grafico Plotly della suite ARGUS.
    Applica il template argus_dark / argus_light e comprime la memoria RAM.
    """
    if fig is None:
        return fig

    tpl = "argus_dark" if dark_mode else "argus_light"
    text_color = "#f8fafc" if dark_mode else "#0f172a"
    subtle_color = "#94a3b8" if dark_mode else "#64748b"

    layout_updates: Dict[str, Any] = {
        "template": tpl,
        "hovermode": hovermode,
        "margin": dict(l=40, r=20, t=44 if title else 24, b=40 if x_title else 24)
    }

    if height is not None:
        layout_updates["height"] = height

    if title:
        layout_updates["title"] = dict(
            text=f"<b>{title}</b>",
            font=dict(family="Outfit, sans-serif", size=15, color=text_color),
            x=0.01,
            y=0.98,
            xanchor="left",
            yanchor="top"
        )

    # Configurazione Legenda
    if show_legend:
        if legend_orientation == "h":
            layout_updates["legend"] = dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1.0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", size=11, color=subtle_color)
            )
        else:
            layout_updates["legend"] = dict(
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", size=11, color=subtle_color)
            )
    else:
        layout_updates["showlegend"] = False

    fig.update_layout(**layout_updates)

    # Configurazione Asse X
    x_kwargs: Dict[str, Any] = {}
    if x_title:
        x_kwargs["title"] = dict(text=x_title, font=dict(family="Outfit, sans-serif", size=12, color=subtle_color))
    if show_spikes:
        x_kwargs.update({
            "showspikes": True,
            "spikethickness": 1,
            "spikedash": "dot",
            "spikemode": "across",
            "spikecolor": "rgba(255, 255, 255, 0.3)" if dark_mode else "rgba(0, 0, 0, 0.3)"
        })
    if x_kwargs:
        fig.update_xaxes(**x_kwargs)

    # Configurazione Asse Y
    y_kwargs: Dict[str, Any] = {}
    if y_title:
        y_kwargs["title"] = dict(text=y_title, font=dict(family="Outfit, sans-serif", size=12, color=subtle_color))
    if is_percentage:
        y_kwargs["tickformat"] = ",.2%"
    elif is_currency:
        y_kwargs["tickprefix"] = f"{currency_symbol} "
        y_kwargs["tickformat"] = ",.2f"
    if y_kwargs:
        fig.update_yaxes(**y_kwargs)

    # Ottimizzazione footprint RAM
    optimize_plotly_figure_memory(fig, precision=4)
    return fig


def create_monte_carlo_fan_chart(
    simulations: Union[pd.DataFrame, np.ndarray, Dict[str, Any]],
    dates: Optional[Union[pd.Index, List[Any]]] = None,
    initial_value: Optional[float] = None,
    target_value: Optional[float] = None,
    title: str = "Simulazione Monte Carlo — Proiezione a Ventaglio",
    currency_symbol: str = "€",
    height: int = 460,
    dark_mode: bool = True
) -> go.Figure:
    """
    Genera un Fan Chart (cono probabilistico a ventaglio) per simulazioni Monte Carlo / FIRE:
    - Bande percentili stratificate: 5th-95th (90% confidenza), 25th-75th (50% confidenza interquartile)
    - Traiettoria mediana (50th percentile) ad alta visibilità
    - Linea di break-even / target FIRE opzionale
    - Zero trace clutter, hover strutturato
    """
    # Estrazione percentili
    if isinstance(simulations, dict):
        p5 = simulations.get("p5", [])
        p25 = simulations.get("p25", [])
        p50 = simulations.get("p50", [])
        p75 = simulations.get("p75", [])
        p95 = simulations.get("p95", [])
        x_axis = dates if dates is not None else list(range(len(p50)))
    elif isinstance(simulations, pd.DataFrame):
        x_axis = simulations.index if dates is None else dates
        p5 = simulations.quantile(0.05, axis=1).values
        p25 = simulations.quantile(0.25, axis=1).values
        p50 = simulations.quantile(0.50, axis=1).values
        p75 = simulations.quantile(0.75, axis=1).values
        p95 = simulations.quantile(0.95, axis=1).values
    elif isinstance(simulations, np.ndarray):
        x_axis = list(range(simulations.shape[0])) if dates is None else dates
        p5 = np.percentile(simulations, 5, axis=1)
        p25 = np.percentile(simulations, 25, axis=1)
        p50 = np.percentile(simulations, 50, axis=1)
        p75 = np.percentile(simulations, 75, axis=1)
        p95 = np.percentile(simulations, 95, axis=1)
    else:
        return go.Figure()

    fig = go.Figure()

    # Banda 5th - 95th (Intervallo confidenza 90%)
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p95,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p5,
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(59, 130, 246, 0.12)",
        name="Intervallo 90% (P5 - P95)",
        hovertemplate=f"P5 (Pessimistico): <b>{currency_symbol} %{{y:,.0f}}</b><extra></extra>"
    ))

    # Banda 25th - 75th (Intervallo interquartile 50%)
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p75,
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p25,
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(59, 130, 246, 0.22)",
        name="Intervallo 50% (P25 - P75)",
        hovertemplate=f"P25: <b>{currency_symbol} %{{y:,.0f}}</b><extra></extra>"
    ))

    # Mediana P50
    fig.add_trace(go.Scatter(
        x=x_axis,
        y=p50,
        mode="lines",
        line=dict(color="#38bdf8", width=2.5),
        name="Mediana (P50)",
        hovertemplate=f"<b>Mediana</b>: {currency_symbol} %{{y:,.0f}}<extra></extra>"
    ))

    # Capitale iniziale di riferimento
    if initial_value is not None:
        fig.add_hline(
            y=initial_value,
            line_dash="dot",
            line_color="rgba(148, 163, 184, 0.6)",
            line_width=1.2,
            annotation_text=f"Base: {currency_symbol} {initial_value:,.0f}",
            annotation_position="bottom left",
            annotation_font=dict(family="'JetBrains Mono', monospace", size=10, color="#94a3b8")
        )

    # Target FIRE / Soglia Obiettivo
    if target_value is not None:
        fig.add_hline(
            y=target_value,
            line_dash="dash",
            line_color="#f59e0b",
            line_width=1.6,
            annotation_text=f"Target: {currency_symbol} {target_value:,.0f}",
            annotation_position="top left",
            annotation_font=dict(family="'JetBrains Mono', monospace", size=11, color="#fbbf24")
        )

    apply_custom_chart_layout(
        fig,
        title=title,
        x_title="Orizzonte Temporale",
        y_title=f"Capitale ({currency_symbol})",
        is_currency=True,
        currency_symbol=currency_symbol,
        height=height,
        dark_mode=dark_mode,
        hovermode="x unified"
    )
    return fig


def create_correlation_heatmap(
    corr_matrix: Union[pd.DataFrame, np.ndarray],
    title: str = "Matrice di Correlazione Cross-Asset & Rischio",
    show_values: bool = True,
    colorscale: Optional[List[Any]] = None,
    height: Optional[int] = None,
    dark_mode: bool = True
) -> go.Figure:
    """
    Genera una heatmap di correlazione cross-asset e rischio ad alto contrasto:
    - Scala divergente fissa da -1.0 a +1.0 (evita distorsioni cromatiche su subset decorrelati)
    - Valori numerici stampati chiaramente dentro ogni cella
    - Hovertemplate professionale con indicazione semantica
    """
    if isinstance(corr_matrix, pd.DataFrame):
        df_corr = corr_matrix
    elif isinstance(corr_matrix, np.ndarray):
        n = corr_matrix.shape[0]
        cols = [f"Asset {i+1}" for i in range(n)]
        df_corr = pd.DataFrame(corr_matrix, index=cols, columns=cols)
    else:
        return go.Figure()

    labels = df_corr.columns.tolist()
    z_vals = df_corr.values
    scale = colorscale or ARGUS_DIVERGING_SCALE

    # Text matrix per le celle
    text_matrix = []
    for row in z_vals:
        text_matrix.append([f"{v:+.2f}" for v in row])

    fig = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=labels,
        y=labels,
        zmin=-1.0,
        zmax=1.0,
        colorscale=scale,
        text=text_matrix if show_values else None,
        texttemplate="%{text}" if show_values else None,
        textfont=dict(family="'JetBrains Mono', monospace", size=11, color="#ffffff"),
        hovertemplate="<b>%{y} ↔ %{x}</b><br>Correlazione di Pearson: <b>%{z:+.3f}</b><extra></extra>",
        colorbar=dict(
            title=dict(text="Corr", font=dict(family="Outfit, sans-serif", size=11, color="#94a3b8")),
            tickvals=[-1.0, -0.5, 0.0, 0.5, 1.0],
            ticktext=["-1.0", "-0.5", "0.0", "+0.5", "+1.0"],
            tickfont=dict(family="'JetBrains Mono', monospace", size=10, color="#94a3b8"),
            len=0.85,
            thickness=14
        )
    ))

    calc_height = height or max(380, len(labels) * 44 + 80)
    apply_custom_chart_layout(
        fig,
        title=title,
        height=calc_height,
        dark_mode=dark_mode,
        show_legend=False,
        hovermode="closest",
        show_spikes=False
    )
    return fig


def create_cashflow_waterfall_chart(
    categories: List[str],
    values: List[float],
    measures: Optional[List[str]] = None,
    title: str = "Analisi Cash Flow & Risparmio Netto",
    currency_symbol: str = "€",
    height: int = 420,
    dark_mode: bool = True
) -> go.Figure:
    """
    Genera un Waterfall Chart istituzionale per il bilancio entrate/uscite/risparmio netto:
    - Entrate positive in verde smeraldo
    - Uscite e costi in corallo/rosso
    - Risparmio netto finale (totale) in blu/ciano
    - Connettori discreti e valori tabulari sopra/dentro le barre
    """
    if not categories or not values or len(categories) != len(values):
        return go.Figure()

    if measures is None:
        # Se l'ultimo elemento corrisponde alla chiusura, lo impostiamo come total
        measures = ["relative"] * (len(categories) - 1) + ["total"]

    fig = go.Figure(go.Waterfall(
        name="Cash Flow",
        orientation="v",
        measure=measures,
        x=categories,
        y=values,
        textposition="outside",
        texttemplate=f"{currency_symbol} %{{y:+,.0f}}",
        textfont=dict(family="'JetBrains Mono', monospace", size=11, color="#e2e8f0" if dark_mode else "#1e293b"),
        connector=dict(line=dict(color="rgba(255, 255, 255, 0.18)" if dark_mode else "rgba(0, 0, 0, 0.18)", width=1, dash="dot")),
        increasing=dict(marker=dict(color=ARGUS_COLORS["bull"])),
        decreasing=dict(marker=dict(color=ARGUS_COLORS["bear"])),
        totals=dict(marker=dict(color=ARGUS_COLORS["primary"])),
        hovertemplate=f"<b>%{{x}}</b><br>Flusso: <b>{currency_symbol} %{{y:+,.2f}}</b><br>Cumulato: <b>{currency_symbol} %{{currentvalue:,.2f}}</b><extra></extra>"
    ))

    apply_custom_chart_layout(
        fig,
        title=title,
        y_title=f"Flusso ({currency_symbol})",
        is_currency=True,
        currency_symbol=currency_symbol,
        height=height,
        dark_mode=dark_mode,
        show_legend=False,
        hovermode="closest"
    )
    return fig


def create_equity_drawdown_chart(
    nav_series: pd.Series,
    drawdown_series: Optional[pd.Series] = None,
    benchmark_series: Optional[pd.Series] = None,
    title: str = "Performance Cumulata & Underwater Drawdown",
    currency_symbol: str = "€",
    height: int = 540,
    dark_mode: bool = True
) -> go.Figure:
    """
    Genera un grafico sincrono a due pannelli temporali allineati:
    - Pannello 1 (72%): NAV Portafoglio con area di riempimento + Benchmark opzionale
    - Pannello 2 (28%): Underwater Drawdown plot con evidenziazione del Max Drawdown storico
    """
    if nav_series is None or nav_series.empty:
        return go.Figure()

    # Calcolo drawdown se non fornito
    if drawdown_series is None:
        hwm = nav_series.cummax()
        drawdown_series = (nav_series - hwm) / hwm * 100.0

    fig = sp.make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.72, 0.28]
    )

    # 1. Traccia NAV Portafoglio
    fig.add_trace(
        go.Scatter(
            x=nav_series.index,
            y=nav_series.values,
            mode="lines",
            name="Portafoglio (NAV)",
            line=dict(color="#38bdf8", width=2.2),
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.08)",
            hovertemplate=f"<b>Portafoglio</b>: {currency_symbol} %{{y:,.2f}}<extra></extra>"
        ),
        row=1,
        col=1
    )

    # 2. Benchmark opzionale
    if benchmark_series is not None and not benchmark_series.empty:
        fig.add_trace(
            go.Scatter(
                x=benchmark_series.index,
                y=benchmark_series.values,
                mode="lines",
                name="Benchmark",
                line=dict(color="#94a3b8", width=1.5, dash="dash"),
                hovertemplate=f"<b>Benchmark</b>: {currency_symbol} %{{y:,.2f}}<extra></extra>"
            ),
            row=1,
            col=1
        )

    # 3. Underwater Drawdown
    fig.add_trace(
        go.Scatter(
            x=drawdown_series.index,
            y=drawdown_series.values,
            mode="lines",
            name="Drawdown",
            line=dict(color="#ef4444", width=1.4),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.22)",
            hovertemplate="<b>Drawdown</b>: %{y:.2f}%<extra></extra>"
        ),
        row=2,
        col=1
    )

    # Evidenziazione Max Drawdown
    min_dd = drawdown_series.min()
    if pd.notna(min_dd) and min_dd < 0:
        min_date = drawdown_series.idxmin()
        fig.add_trace(
            go.Scatter(
                x=[min_date],
                y=[min_dd],
                mode="markers+text",
                name="Max Drawdown",
                marker=dict(color="#ef4444", size=8, symbol="diamond"),
                text=[f"Max DD: {min_dd:.1f}%"],
                textposition="bottom center",
                textfont=dict(family="'JetBrains Mono', monospace", size=10, color="#f87171"),
                hoverinfo="skip"
            ),
            row=2,
            col=1
        )

    # Applicazione layout istituzionale
    apply_custom_chart_layout(
        fig,
        title=title,
        height=height,
        dark_mode=dark_mode,
        hovermode="x unified",
        show_legend=True
    )

    # Formattazione assi specifici per i due subplot
    fig.update_yaxes(
        title_text=f"NAV ({currency_symbol})",
        tickprefix=f"{currency_symbol} ",
        tickformat=",.2f",
        row=1,
        col=1
    )
    fig.update_yaxes(
        title_text="Drawdown",
        ticksuffix="%",
        tickformat=",.1f",
        row=2,
        col=1
    )
    fig.update_xaxes(row=2, col=1, title_text="Data")

    return fig


def create_hierarchical_allocation_chart(
    df: pd.DataFrame,
    path: List[str],
    values_col: str,
    chart_type: str = "sunburst",
    title: str = "Asset Allocation Multilivello",
    currency_symbol: str = "€",
    height: int = 480,
    dark_mode: bool = True
) -> go.Figure:
    """
    Genera un grafico gerarchico (Sunburst o Treemap) a 3 livelli: Macro-classe -> Sotto-classe -> Singolo Asset.
    Offre un'alternativa analitica superiore ai grafici a torta piatti.
    """
    if df is None or df.empty or not path or values_col not in df.columns:
        return go.Figure()

    if chart_type == "treemap":
        fig = px.treemap(
            df,
            path=path,
            values=values_col,
            color_discrete_sequence=ARGUS_FINANCIAL_PALETTE
        )
    else:
        fig = px.sunburst(
            df,
            path=path,
            values=values_col,
            color_discrete_sequence=ARGUS_FINANCIAL_PALETTE
        )

    fig.update_traces(
        textinfo="label+percent entry",
        insidetextfont=dict(family="Outfit, sans-serif", size=12),
        hovertemplate=f"<b>%{{label}}</b><br>Controvalore: {currency_symbol} %{{value:,.2f}}<br>Quota sul Totale: %{{percentRoot:.1%}}<br>Quota sul Ramo: %{{percentEntry:.1%}}<extra></extra>"
    )

    apply_custom_chart_layout(
        fig,
        title=title,
        height=height,
        dark_mode=dark_mode,
        show_legend=False,
        hovermode="closest",
        show_spikes=False
    )
    return fig







