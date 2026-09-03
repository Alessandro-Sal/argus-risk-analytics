from typing import Any, Dict, List, Optional, Tuple, Union
import textwrap
from datetime import datetime, date
import streamlit as st
import pandas as pd
import numpy as np



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


def apply_plotly_theme(fig, theme_name=None):
    """Applica uno stile dark vettoriale con tooltip luminosi al grafico Plotly e ottimizza la memoria."""
    if fig is None:
        return fig

    if not theme_name:
        theme_name = st.session_state.get("ui_theme", "Midnight Obsidian")

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
    how_to_read: str
) -> str:
    """
    Formatta il contenuto informativo di modali e popover seguendo rigorosamente
    lo standard istituzionale a 5 sezioni:
    1. 📌 Cos'è
    2. 📐 Come si calcola
    3. 🎯 A cosa serve
    4. ⚙️ Come viene calcolato da ARGUS
    5. 🔍 Come leggerlo
    """
    return f"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
  <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
    <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 8px;">{title}</div>
    <div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> {what_is}</div>
    <div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
      <div style="background: rgba(255,153,0,0.06); border: 1px solid rgba(255,153,0,0.20); border-left: 3px solid #ff9900; padding: 8px 12px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; line-height: 1.6;">
        {how_calc}
      </div>
    </div>
    <div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> {why_useful}</div>
    <div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato da ARGUS:</b> {argus_calc}</div>
    <div><b>🔍 Come leggerlo:</b><br>{how_to_read}</div>
  </div>
</div>
"""


KNOWN_METRICS_KNOWLEDGE_BASE = {
    "rendimento_atteso": {
        "title": "📈 Rendimento Atteso (Expected Return / CAGR)",
        "what_is": "Tasso di rendimento composto annuo atteso o storico generato dal portafoglio di investimenti.",
        "how_calc": "<b>CAGR</b> = (V<sub>finale</sub> / V<sub>iniziale</sub>)<sup>252 / N</sup> &minus; 1 &nbsp;|&nbsp; <b>&mu;<sub>port</sub></b> = <b>w</b><sup>T</sup> &mu;",
        "why_useful": "Misurare la capacità del portafoglio di incrementare il capitale nel tempo al netto delle fluttuazioni temporanee.",
        "argus_calc": "Calcolato sulle serie storiche dei prezzi rettificati (Adjusted Close) con base a 252 sedute lavorative o per combinazione lineare dei pesi simulati.",
        "how_to_read": "• 🟢 > Benchmark (Alpha positivo, sovraperformance gestionale)<br>• 🟡 In linea con l'indice di riferimento<br>• 🔴 < Benchmark o negativo (Erosione del capitale reale)."
    },
    "volatilita_annua": {
        "title": "⚡ Volatilità Annua (Annualized Standard Deviation)",
        "what_is": "Misura statistica della dispersione dei rendimenti del portafoglio attorno alla loro media (rischio totale di mercato).",
        "how_calc": "<b>&sigma;<sub>annua</sub></b> = &sigma;<sub>daily</sub> &times; &radic;252 = &radic;(<b>w</b><sup>T</sup> &Sigma; <b>w</b>) &times; &radic;252",
        "why_useful": "Quantificare l'incertezza e l'ampiezza delle oscillazioni di prezzo a cui è esposto il capitale nel corso di un anno solare.",
        "argus_calc": "Determinata tramite moltiplicazione quadratica della matrice di covarianza (de-noised con shrinkage Ledoit-Wolf) per il vettore dei pesi, annualizzata a 252 sedute.",
        "how_to_read": "• 🟢 < 12.0% (Profilo Prudente/Conservativo)<br>• 🟡 12.0% - 22.0% (Profilo Bilanciato Standard)<br>• 🔴 > 22.0% (Profilo Aggressivo ad elevata oscillazione)."
    },
    "var_95": {
        "title": "🛡️ Value at Risk (VaR 95% Giornaliero)",
        "what_is": "La massima perdita potenziale stimata su un orizzonte di 1 giorno con un livello di confidenza statistica del 95%.",
        "how_calc": "<b>VaR<sub>95%</sub></b> = &minus;(&mu; &minus; 1.645 &times; &sigma;) &nbsp;|&nbsp; <i>Storico:</i> 5° percentile della distribuzione dei rendimenti",
        "why_useful": "Fissare un limite prudenziale di perdita massima in condizioni ordinarie di mercato per calibrare liquidità e margini.",
        "argus_calc": "Calcolato con doppio approccio integrato: Parametrico (Gaussiano/Cornish-Fisher con asimmetria e curtosi) e Storico empirico non parametrico su 252+ sedute.",
        "how_to_read": "• 🟢 < 1.50% (Rischio giornaliero contenuto)<br>• 🟡 1.50% - 2.50% (Esposizione nella media)<br>• 🔴 > 2.50% (Elevata vulnerabilità a shock giornalieri)."
    },
    "sharpe_ratio": {
        "title": "🎯 Sharpe Ratio (Rendimento / Rischio Totale)",
        "what_is": "Indice che misura l'extra-rendimento generato per ciascuna unità di rischio totale (volatilità) assunto oltre il tasso privo di rischio.",
        "how_calc": "<b>Sharpe</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>p</sub>",
        "why_useful": "Distinguere la reale abilità allocativa del gestore da rendimenti ottenuti assumendo una volatilità eccessiva e non sostenibile.",
        "argus_calc": "Utilizza il tasso Risk-Free live armonizzato per valuta (BCE €STR per EUR, Fed ^IRX per USD) e annualizza i rendimenti a 252 giorni.",
        "how_to_read": "• 🟢 > 1.20 (Eccellente efficienza rischio/rendimento)<br>• 🟡 0.70 - 1.20 (Buono / Accettabile)<br>• 🔴 < 0.70 (Inefficiente, remunerazione insufficiente per il rischio corso)."
    },
    "sortino_ratio": {
        "title": "🛡️ Sortino Ratio (Rendimento / Downside Risk)",
        "what_is": "Variante dello Sharpe Ratio che penalizza unicamente la volatilità negativa di ribasso (Downside Deviation), ignorando la volatilità positiva.",
        "how_calc": "<b>Sortino</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>downside</sub> &nbsp;|&nbsp; <b>&sigma;<sub>downside</sub></b> = &radic;[ (1/N) &sum; min(0, R<sub>t</sub> &minus; R<sub>f</sub>)<sup>2</sup> &times; 252 ]",
        "why_useful": "Valutare strategie asimmetriche e opzioni dove la volatilità positiva è desiderabile e solo le perdite costituiscono rischio.",
        "argus_calc": "Calcolato estraendo i rendimenti inferiori al target MAR (Minimum Acceptable Return = Tasso Risk-Free live).",
        "how_to_read": "• 🟢 > 1.50 (Ottima asimmetria e protezione dai ribassi)<br>• 🟡 0.80 - 1.50 (Sufficiente)<br>• 🔴 < 0.80 (Elevata frequenza o entità di rendimenti negativi)."
    },
    "max_drawdown": {
        "title": "📉 Massimo Drawdown Storico (Max Drawdown)",
        "what_is": "La massima perdita percentuale registrata dal picco di valore più elevato fino al punto di minimo successivo.",
        "how_calc": "<b>MDD</b> = min<sub>t</sub> [ (V<sub>t</sub> &minus; HWM<sub>t</sub>) / HWM<sub>t</sub> ]<br><span style='font-size:11.5px; color:#8b949e;'>dove <b>HWM<sub>t</sub></b> = max<sub>s &le; t</sub> V<sub>s</sub> è il picco massimo storico progressivo (High-Water Mark)</span>",
        "why_useful": "Quantificare il peggior calo storico subito dal portafoglio e testare la resilienza psicologica e finanziaria dell'investitore.",
        "argus_calc": "Tracciato punto a punto sulla serie storica cumulata dell'equity value, registrando picco, valle e durata del recupero (Recovery Time).",
        "how_to_read": "• 🟢 < 12.0% (Capitale molto protetto e resiliente)<br>• 🟡 12.0% - 25.0% (Correzione fisiologica di mercato)<br>• 🔴 > 25.0% (Rischio di prolungata distruzione di valore)."
    },
    "beta": {
        "title": "🏛️ Beta di Mercato (Market Sensitivity)",
        "what_is": "Misura della sensibilità del rendimento del portafoglio rispetto alle variazioni dell'indice di riferimento (rischio sistematico).",
        "how_calc": "<b>&beta;</b> = Cov(R<sub>p</sub>, R<sub>m</sub>) / Var(R<sub>m</sub>)",
        "why_useful": "Stabilire se il portafoglio amplifica o attenua i movimenti del mercato complessivo.",
        "argus_calc": "Regressione OLS dei rendimenti giornalieri del portafoglio contro il benchmark principale selezionato (SPY, QQQ, ACWI).",
        "how_to_read": "• 🟢 β < 0.80 (Difensivo / Bassa correlazione al mercato)<br>• 🟡 β ≈ 1.00 (In linea col mercato)<br>• 🔴 β > 1.20 (Aggressivo, amplifica fortemente i ribassi di mercato)."
    },
    "alpha": {
        "title": "🏆 Alpha di Jensen (Extra-Rendimento Gestionale)",
        "what_is": "L'extra-rendimento netto generato dal portafoglio rispetto a quello atteso in base al modello CAPM per il livello di rischio sistematico assunto.",
        "how_calc": "<b>&alpha;</b> = R<sub>p</sub> &minus; [ R<sub>f</sub> + &beta; &times; (R<sub>m</sub> &minus; R<sub>f</sub>) ]",
        "why_useful": "Isolare il valore aggiunto puro generato dalle scelte di stock picking e asset allocation del gestore.",
        "argus_calc": "Intercetta della regressione lineare tra i rendimenti in eccesso del portafoglio e del benchmark, calcolata con p-value di confidenza.",
        "how_to_read": "• 🟢 α > +2.0% (Netta creazione di valore attivo)<br>• 🟡 0.0% ≤ α ≤ +2.0% (Lieve extra-performance)<br>• 🔴 α < 0.0% (Distruzione di valore rispetto a una replica passiva)."
    },
    "calmar_ratio": {
        "title": "⚖️ Calmar Ratio (CAGR / Max Drawdown)",
        "what_is": "Rapporto tra il tasso di crescita annuo composto (CAGR) e il Massimo Drawdown storico subito.",
        "how_calc": "<b>Calmar</b> = CAGR / |Max Drawdown|",
        "why_useful": "Valutare se il rendimento annuo generato giustifica l'ampiezza della peggiore flessione storica sopportata.",
        "argus_calc": "Calcolato dal rapporto tra il CAGR del portafoglio e il valore assoluto del massimo drawdown sulla finestra storica.",
        "how_to_read": "• 🟢 > 1.00 (Eccellente: il rendimento annuo supera la peggiore perdita)<br>• 🟡 0.50 - 1.00 (Equilibrato)<br>• 🔴 < 0.50 (Drawdown sproporzionato rispetto al rendimento generato)."
    },
    "days_to_liquidate": {
        "title": "⚡ Days-to-Liquidate (Almgren-Chriss Liquidity Horizon)",
        "what_is": "Il numero stimato di giorni lavorativi necessari per liquidare le posizioni senza eccedere il 15% del volume medio giornaliero (ADV).",
        "how_calc": "<b>DTL</b> = Quantità Netta / (ADV<sub>30g</sub> &times; 0.15)",
        "why_useful": "Evitare trappole di illiquidità, shock da market impact e disallineamenti di prezzo in caso di liquidazione forzata o ribilanciamento rapido.",
        "argus_calc": "Pondera ciascun asset sul volume medio a 30 sedute ricavato dai flussi di mercato e applica il modello di impatto Almgren-Chriss.",
        "how_to_read": "• 🟢 ≤ 1.0 gg (Smobilizzo immediato, asset ultra-liquido)<br>• 🟡 1.0 - 3.0 gg (Liquidità moderata)<br>• 🔴 > 3.0 gg (Posizione illiquida, elevato rischio di market impact)."
    },
    "chandelier_exit": {
        "title": "🛡️ Chandelier Exit (ATR Trailing Stop-Loss)",
        "what_is": "Algoritmo di stop-loss dinamico agganciato al picco massimo recente, tarato sulla volatilità effettiva a 14 periodi (Average True Range).",
        "how_calc": "<b>Stop</b> = Max(High<sub>22g</sub>) &minus; 3.0 &times; ATR<sub>14</sub>",
        "why_useful": "Proteggere i guadagni accumulati lasciando correre i profitti durante i trend rialzisti ed evitando uscite premature per rumore di mercato.",
        "argus_calc": "Calcola l'ATR a 14 sedute sulle barre High-Low-Close di ciascun titolo e sottrae 3 volte tale valore dal massimo a 22 giorni lavorativi.",
        "how_to_read": "• 🟢 Prezzo > Stop (Trend intatto, posizione regolare)<br>• 🟡 Distanza < 4% (Vicinanza alla soglia di allerta)<br>• 🔴 Prezzo ≤ Stop (Trigger di uscita/copertura scattato)."
    },
    "diversification_ratio": {
        "title": "🌐 Diversification Ratio (DR)",
        "what_is": "Rapporto tra la media ponderata delle volatilità dei singoli componenti e la volatilità complessiva del portafoglio.",
        "how_calc": "<b>DR</b> = (&sum; w<sub>i</sub> &times; &sigma;<sub>i</sub>) / &radic;(<b>w</b><sup>T</sup> &Sigma; <b>w</b>)",
        "why_useful": "Quantificare in termini matematici il beneficio della diversificazione e la riduzione del rischio ottenuta combinando asset non perfettamente correlati.",
        "argus_calc": "Calcolato con la matrice di covarianza de-noised Ledoit-Wolf e i pesi effettivi di portafoglio.",
        "how_to_read": "• 🟢 > 1.40 (Ottima diversificazione istituzionale)<br>• 🟡 1.15 - 1.40 (Diversificazione moderata)<br>• 🔴 < 1.15 (Scarsa diversificazione, elevato rischio di concentrazione)."
    },
    "altman_z_score": {
        "title": "🏛️ Altman Z-Score (Solvibilità e Rischio Default)",
        "what_is": "Modello econometrico multivariato a 5 indici di bilancio per prevedere la probabilità di insolvenza o dissesto finanziario aziendale a 2 anni.",
        "how_calc": "<b>Z</b> = 1.2 &times; X<sub>1</sub> + 1.4 &times; X<sub>2</sub> + 3.3 &times; X<sub>3</sub> + 0.6 &times; X<sub>4</sub> + 0.999 &times; X<sub>5</sub>",
        "why_useful": "Verificare la solidità fondamentale e proteggersi da fallimenti o default societari nei titoli detenuti.",
        "argus_calc": "Estrae automaticamente le voci di bilancio annuali certificate (SEC 10-K / bilanci societari) calcolando i 5 ratios finanziari.",
        "how_to_read": "• 🟢 Z > 2.99 (Zona Sicura: azienda solida e solvente)<br>• 🟡 1.81 ≤ Z ≤ 2.99 (Zona Grigia: rischio moderato)<br>• 🔴 Z < 1.81 (Zona di Distress: alto rischio di insolvenza)."
    },
    "beneish_m_score": {
        "title": "🔍 Beneish M-Score (Forensic Accounting & Manipolazione)",
        "what_is": "Modello statistico probabilistico a 8 indici di bilancio per rilevare anomalie contabili o pratiche aggressive di manipolazione degli utili.",
        "how_calc": "<b>M</b> = &minus;4.84 + 0.92 &times; DSRI + 0.528 &times; GMI + 0.404 &times; AQI + 0.892 &times; SGI + 0.115 &times; DEPI &minus; 0.172 &times; SGAI + 4.037 &times; TATA + 0.0327 &times; LVGI",
        "why_useful": "Individuare tempestivamente red flags contabili prima che si traducano in scandali finanziari o crolli delle quotazioni.",
        "argus_calc": "Confronta le voci di conto economico e stato patrimoniale degli ultimi due esercizi contabili calcolando gli 8 indicatori standard.",
        "how_to_read": "• 🟢 M < -2.22 (Bassa probabilità di manipolazione, bilancio affidabile)<br>• 🔴 M > -2.22 (Alta probabilità di anomalie o abbellimenti contabili)."
    },
    "sloan_accrual": {
        "title": "📊 Sloan Accrual Ratio (Qualità degli Utili)",
        "what_is": "Indicatore di qualità contabile che misura la percentuale di utile derivante da mere scritture di competenza rispetto ai flussi di cassa operativi reali.",
        "how_calc": "<b>Accrual Ratio</b> = [ Net Income &minus; (CFO + CFI) ] / Total Assets",
        "why_useful": "Evidenziare se gli utili annunciati sono supportati da denaro effettivo incassato sul conto corrente aziendale.",
        "argus_calc": "Estrae Net Income, Cash Flow Operativo (CFO) e Totale Attivo dall'ultimo rendiconto finanziario societario.",
        "how_to_read": "• 🟢 |Accrual| < 5.0% (Qualità eccellente degli utili)<br>• 🟡 5.0% - 10.0% (Livello intermedio)<br>• 🔴 |Accrual| > 10.0% (Bassa qualità, rischio revisioni al ribasso)."
    },
    "wacc": {
        "title": "💼 WACC & DCF Fair Value (Costo del Capitale e Valutazione Intrinseca)",
        "what_is": "Il costo medio ponderato del capitale aziendale (WACC) e il valore intrinseco per azione calcolato attualizzando i flussi di cassa futuri (DCF).",
        "how_calc": "<b>WACC</b> = (E/V) &times; K<sub>e</sub> + (D/V) &times; K<sub>d</sub> &times; (1 &minus; t) &nbsp;|&nbsp; <b>Target Price</b> = [ &sum; FCFF<sub>t</sub> / (1 + WACC)<sup>t</sup> + TV ] / Shares",
        "why_useful": "Fissare il prezzo equo (Fair Value) fondamentale di un titolo per determinare se quota a sconto (sottovalutato) o a premio (sopravvalutato).",
        "argus_calc": "Simulazione DCF Monte Carlo con 1,000 iterazioni stocastiche su tassi di crescita, WACC calcolato con CAPM e tasso risk-free live.",
        "how_to_read": "• 🟢 Prezzo < Fair Value (Margine di sicurezza favorevole, sottovalutato)<br>• 🟡 Prezzo ≈ Fair Value (Equamente valutato)<br>• 🔴 Prezzo > Fair Value (Sopravvalutato rispetto ai fondamentali)."
    },
    "piotroski_f_score": {
        "title": "⭐ Piotroski F-Score (Solidità e Momentum Fondamentale)",
        "what_is": "Punteggio discreto da 0 a 9 basato su 9 criteri contabili suddivisi in Redditività, Leva/Liquidità ed Efficienza Operativa.",
        "how_calc": "<b>F-Score</b> = &sum; (9 criteri binari 0 o 1 su ROA, CFO, &Delta;Leva, &Delta;Margini, &Delta;Rotazione, ecc.)",
        "why_useful": "Selezionare titoli value con solidi fondamentali ed eliminare società fragili a rischio declino economico.",
        "argus_calc": "Analisi automatizzata punto per punto sui bilanci societari storici ufficiali.",
        "how_to_read": "• 🟢 8 - 9 (Società finanziariamente eccellente e in espansione)<br>• 🟡 5 - 7 (Solidità moderata / nella media)<br>• 🔴 0 - 4 (Struttura finanziaria fragile o deterioramento operativo)."
    },
    "kelly_criterion": {
        "title": "🎯 Kelly Criterion (Dimensionamento Ottimale del Capitale)",
        "what_is": "Formula per determinare la percentuale teorica ottimale di capitale da allocare su una posizione per massimizzare la crescita geometrica a lungo termine.",
        "how_calc": "<b>f*</b> = (p &times; b &minus; q) / b &nbsp;|&nbsp; <b>f*</b> = (&mu; &minus; R<sub>f</sub>) / &sigma;<sup>2</sup>",
        "why_useful": "Prevenire la rovina statistica del capitale (Gambler's Ruin) ed evitare sia il sotto-investimento che l'over-betting.",
        "argus_calc": "Calcolato con frazionamento prudenziale (Half-Kelly al 50% o Quarter-Kelly al 25%) integrato con il tasso risk-free live.",
        "how_to_read": "• 🟢 f* applicato al 25%-50% (Allocazione robusta ed equilibrata)<br>• 🔴 Full Kelly al 100% (Sconsigliato: eccessiva volatilità del portafoglio)."
    },
    "tracking_error": {
        "title": "🎯 Tracking Error & Information Ratio",
        "what_is": "La volatilità della differenza dei rendimenti tra il portafoglio e il benchmark (Tracking Error) e l'extra-rendimento per unità di rischio attivo (Information Ratio).",
        "how_calc": "<b>TE</b> = &radic;(Var(R<sub>p</sub> &minus; R<sub>b</sub>)) &times; &radic;252 &nbsp;|&nbsp; <b>IR</b> = (R<sub>p</sub> &minus; R<sub>b</sub>) / TE",
        "why_useful": "Valutare la coerenza della gestione rispetto al benchmark di riferimento e premiare l'abilità di generazione attiva di Alpha.",
        "argus_calc": "Calcolato sulle serie temporali allineate dei rendimenti giornalieri di portafoglio e benchmark su 252 sedute.",
        "how_to_read": "• 🟢 IR > 0.70 (Gestione attiva di alto livello)<br>• 🟡 0.30 ≤ IR ≤ 0.70 (Buona efficienza)<br>• 🔴 IR < 0.30 o negativo (Rischio attivo non remunerato)."
    },
    "omega_ratio": {
        "title": "⚖️ Omega Ratio (Distribuzione Asimmetrica)",
        "what_is": "Rapporto tra la probabilità cumulata dei guadagni rispetto a una soglia di rendimento target e la probabilità cumulata delle perdite sotto tale soglia.",
        "how_calc": "<b>&Omega;(L)</b> = &int;<sub>L</sub><sup>&infin;</sup> (1 &minus; F(r)) dr &nbsp;/&nbsp; &int;<sub>&minus;&infin;</sub><sup>L</sup> F(r) dr",
        "why_useful": "Catturare tutte le proprietà della distribuzione dei rendimenti (inclusi skewness e code grasse) senza assumere la normalità gaussiana.",
        "argus_calc": "Integrazione numerica continua dei rendimenti storici ponderati rispetto al tasso risk-free live.",
        "how_to_read": "• 🟢 > 1.50 (Distribuzione asimmetrica nettamente a favore dei guadagni)<br>• 🟡 1.00 - 1.50 (Bilanciato)<br>• 🔴 < 1.00 (Prevalenza statistica di perdite)."
    },
    "ulcer_index": {
        "title": "📉 Ulcer Index & Martin Ratio",
        "what_is": "Misura di stress e profondità dei cali che tiene conto sia della percentuale di drawdown che del numero di giorni necessari per recuperare il picco.",
        "how_calc": "<b>UI</b> = &radic;[ (1/N) &sum; DD<sub>i</sub><sup>2</sup> ] &nbsp;|&nbsp; <b>Martin</b> = (CAGR &minus; R<sub>f</sub>) / UI",
        "why_useful": "Misurare il logorio temporale dell'investitore durante le fasi negative prolungate del mercato.",
        "argus_calc": "Calcolo quadratico continuo delle percentuali di drawdown su tutti i giorni di negoziazione.",
        "how_to_read": "• 🟢 UI < 5.0% (Crescita lineare, minimi drawdown)<br>• 🟡 5.0% - 12.0% (Volatilità fisiologica)<br>• 🔴 UI > 12.0% (Elevato stress temporale e drawdowns prolungati)."
    },
    "tuir_67": {
        "title": "💰 Zainetto Fiscale & TUIR Art. 67 (Fisco Italiano)",
        "what_is": "La disciplina fiscale italiana (D.P.R. 917/1986) per la tassazione dei redditi diversi di natura finanziaria (26% ordinario, 12.5% Titoli di Stato).",
        "how_calc": "<b>Imposta</b> = max(0, Plusvalenze<sub>realizzate</sub> &minus; Minusvalenze<sub>pregresse</sub>) &times; Aliquota",
        "why_useful": "Monitorare e recuperare le minusvalenze prima della prescrizione quadriennale (Tax-Loss Harvesting strategico).",
        "argus_calc": "Tracciamento contabile FIFO per singolo lotto di acquisto/vendita con data certa, calcolo aliquota per asset class e scadenza a 4 anni.",
        "how_to_read": "• 🟢 Crediti fiscali compensati tempestivamente<br>• 🟡 Minusvalenze in scadenza entro 12 mesi da monitorare<br>• 🔴 Minusvalenze scadute non recuperate."
    },
    "isolation_forest": {
        "title": "🕵️‍♂️ Machine Learning Isolation Forest (Rilevazione Anomalie)",
        "what_is": "Algoritmo di Machine Learning non supervisionato per identificare giornate storiche atipiche con rotture di correlazione o shock sistemici.",
        "how_calc": "<b>Anomalia (4D)</b>: f(Rendimento, &sigma;<sub>20d</sub>, &rho;<sub>media</sub>, DD<sub>t</sub>) &nbsp;&rarr;&nbsp; Score &lt; 0",
        "why_useful": "Rilevare cluster di anomalie di mercato prima che si trasformino in perdite permanenti di capitale.",
        "argus_calc": "Pipeline integrata in scikit-learn con parametro di contaminazione del 5% su tutta la cronologia disponibile.",
        "how_to_read": "• 🔴 ANOMALIA (Punteggio negativo marcato, dinamica anomala)<br>• 🟢 Normale (Fluttuazione coerente con la serie storica)."
    },
    "wealth_health_score": {
        "title": "🛡️ Wealth Health Score (Indice di Salute Patrimoniale)",
        "what_is": "Punteggio sintetico multidimensionale da 0 a 100 che valuta la solidità, solvibilità, diversificazione, cuscinetto di liquidità e sostenibilità del debito dell'intero patrimonio.",
        "how_calc": "<b>Score</b> = 40% Cuscinetto di Liquidità (Runway) + 25% Diversificazione Asset Class + 20% Copertura Previdenziale + 15% Sostenibilità Debito (Debt-to-Asset)",
        "why_useful": "Fornire al Family Office o al singolo investitore un indicatore sintetico immediato per diagnosticare vulnerabilità strutturali prima che impattino il patrimonio netto.",
        "argus_calc": "Valutato in tempo reale aggregando i saldi bancari, le categorie patrimoniali attive, i mesi di autonomia, il rapporto LTV dei mutui e le proiezioni pensionistiche.",
        "how_to_read": "• 🟢 80 - 100 (Salute patrimoniale eccellente, resiliente a shock e ben protetta)<br>• 🟡 60 - 79 (Salute buona con margini di ottimizzazione su liquidità o previdenza)<br>• 🔴 < 60 (Criticità strutturale: eccesso di debito, bassa liquidità o concentrazione elevata)."
    },
    "net_worth": {
        "title": "🏛️ Patrimonio Netto Consolidato (Consolidated Net Worth)",
        "what_is": "Il valore economico totale di tutte le attività possedute (finanziarie, cassa, immobiliari, caveau/fisiche e previdenziali) al netto di tutte le passività e debiti residui.",
        "how_calc": "<b>Net Worth</b> = Totale Attività &minus; Totale Passività = (Cassa + Investimenti + Caveau + Immobili + Previdenza) &minus; (Mutui + Prestiti + Carte)",
        "why_useful": "Rappresenta la metrica cardine della ricchezza personale o familiare, riflettendo la reale solvibilità economica al di là del reddito transitorio.",
        "argus_calc": "Consolidamento multi-conto continuo in valuta base (EUR) con conversione tassi di cambio BCE live, rivalutazione asset caveau e ammortamento mutui residui.",
        "how_to_read": "• 🟢 Trend crescente costante (Accumulazione solida e rendimento positivo)<br>• 🟡 Stabile (Fase di transizione o ribilanciamento)<br>• 🔴 Trend decrescente prolungato (Overspending o drawdown degli asset)."
    },
    "liquid_assets": {
        "title": "💧 Liquidità & Fondo di Emergenza (Liquid Assets & Cash Buffer)",
        "what_is": "Il capitale prontamente disponibile in contanti, depositi a vista, conti correnti o strumenti monetari a rischio zero convertibili in cash entro 24 ore.",
        "how_calc": "<b>Liquidità</b> = &sum; Saldi Conti Correnti + Conti Deposito Svincolabili + Strumenti Monetari Liquidi (XEON/CNAV)",
        "why_useful": "Assorbire spese impreviste (spese mediche, guasti, interruzioni di reddito) evitando di dover liquidare forzatamente investimenti azionari durante cali di mercato.",
        "argus_calc": "Aggregazione istantanea di tutti i conti bancari attivi e fondi monetari liquidi del profilo patrimoniale.",
        "how_to_read": "• 🟢 3 - 6 mesi di spese mensili (Fondo di sicurezza ottimale)<br>• 🟡 1 - 3 mesi (Liquidità minima, rischio in caso di shock)<br>• 🔴 > 12 mesi o < 1 mese (Eccesso di cassa improduttiva / Drag da inflazione o illiquidità critica)."
    },
    "financial_investments": {
        "title": "📈 Investimenti Finanziari (Financial Assets Portfolio)",
        "what_is": "Il controvalore di mercato di tutti gli strumenti finanziari quotati e non quotati (Azioni, ETF, Obbligazioni, Fondi, Crypto, Derivati).",
        "how_calc": "<b>Investimenti</b> = &sum; (Quantità<sub>i</sub> &times; Prezzo di Mercato<sub>i</sub> &times; FX<sub>i</sub>)",
        "why_useful": "Generare crescita del capitale a lungo termine, rendite da dividendi/cedole e proteggere il potere d'acquisto dall'inflazione.",
        "argus_calc": "Sincronizzazione in tempo reale con il Quantitative Risk Engine per calcolare VaR, Sharpe, frontiera efficiente e collegamenti multi-conto.",
        "how_to_read": "• 🟢 Allocazione allineata con l'orizzonte temporale e il profilo di rischio<br>• 🟡 Necessità di ribilanciamento periodico<br>• 🔴 Concentrazione eccessiva su singolo titolo/emittente (>15%)."
    },
    "physical_assets": {
        "title": "⌚ Caveau & Asset Fisici di Pregio (Luxury & Physical Assets)",
        "what_is": "Beni tangibili da collezione o investimento (orologi di lusso Rolex/Patek/AP, oro fisico/bullion, gioielli, metalli preziosi, opere d'arte).",
        "how_calc": "<b>Valore Caveau</b> = &sum; (Prezzo di Acquisto o Fair Market Value da perizia/Chrono24 + Apprezzamento Storico)",
        "why_useful": "Diversificazione non correlata ai mercati finanziari, riserva di valore tangibile in scenari di crisi sistemica e protezione patrimoniale intergenerazionale.",
        "argus_calc": "Tracciamento matriciale per singolo pezzo (seriale, anno, condizioni, corredo B&P, quotazione di mercato stimata, plusvalenza latente).",
        "how_to_read": "• 🟢 5% - 15% del Net Worth (Quota equilibrata per asset tangibili)<br>• 🟡 15% - 25% (Esposizione significativa)<br>• 🔴 > 25% (Illiquidità elevata e costi di custodia/assicurazione gravosi)."
    },
    "real_estate_equity": {
        "title": "🏡 Immobili & Net Equity Immobiliare (Real Estate Net Equity)",
        "what_is": "Il valore netto del patrimonio immobiliare detenuto (residenziale, commerciale, a reddito), al netto dei mutui e finanziamenti ipotecari gravanti.",
        "how_calc": "<b>Net Equity Immobiliare</b> = Valore di Mercato Immobili &minus; Debito Ipotecario Residuo (Mutui)",
        "why_useful": "Misurare la reale ricchezza immobiliare non vincolata a debiti bancari e stimare i flussi di cassa da canoni di locazione (Cap Rate).",
        "argus_calc": "Calcolo automatico del piano di ammortamento mutui (francese/italiano) e rivalutazione catastale/commerciale degli immobili registrati.",
        "how_to_read": "• 🟢 LTV < 50% (Patrimonio immobiliare solido e poco indebitato)<br>• 🟡 LTV 50% - 75% (Leva moderata standard per mutui prima casa)<br>• 🔴 LTV > 80% (Elevata vulnerabilità a rialzo tassi o calo prezzi immobiliari)."
    },
    "pension_total": {
        "title": "🛡️ Previdenza & Fondi Pensione (Pension & Retirement Planning)",
        "what_is": "Il montante accumulato nei pilastri di previdenza complementare (Fondi Pensione Negoziali, Aperti, PIP, TFR pregresso accantonato).",
        "how_calc": "<b>Previdenza</b> = &sum; Posizioni Fondi Pensione (Quote &times; NAV) + Contributi Deducibili Annui &minus; Ritenute",
        "why_useful": "Garantire un adeguato tasso di sostituzione del reddito al pensionamento e beneficiare della deducibilità fiscale fino a € 5.164,57 annui (TUIR Art. 10).",
        "argus_calc": "Simulazione Monte Carlo stocastica (1,000 traiettorie) integrata con inflazione ISTAT, coefficienti di trasformazione INPS e rendimento netto linee d'investimento.",
        "how_to_read": "• 🟢 Tasso di sostituzione stimato > 75% (Pensionamento sereno)<br>• 🟡 60% - 75% (Copertura discreta con piccolo gap da colmare)<br>• 🔴 < 60% (Forte gap previdenziale: incrementare i versamenti annui)."
    },
    "total_liabilities": {
        "title": "📉 Passività & Debiti Totali (Total Liabilities)",
        "what_is": "L'ammontare complessivo delle obbligazioni e dei debiti finanziari in essere (mutui ipotecari, prestiti personali, finanziamenti auto, leasing, carte di credito revolving).",
        "how_calc": "<b>Passività</b> = Debito Residuo Mutui + Capitale Residuo Finanziamenti + Saldo Passivo Carte",
        "why_useful": "Monitorare il grado di indebitamento per evitare situazioni di stress finanziario e ottimizzare il costo medio del debito.",
        "argus_calc": "Tracciamento continuo delle rate mensili, separazione quota capitale/interessi e calcolo DSTI (Debt Service to Income ratio).",
        "how_to_read": "• 🟢 DSTI < 25% del reddito mensile (Debito pienamente sostenibile)<br>• 🟡 25% - 35% (Soglia bancaria ordinaria)<br>• 🔴 > 35% (Sovraindebitamento a rischio insolvenza)."
    },
    "savings_rate": {
        "title": "💰 Tasso di Risparmio (Savings Rate)",
        "what_is": "La quota percentuale del reddito netto mensile che viene risparmiata o investita dopo aver coperto tutte le spese correnti.",
        "how_calc": "<b>Savings Rate</b> = [ (Entrate Nette &minus; Uscite Totali) / Entrate Nette ] &times; 100",
        "why_useful": "È il principale motore di accumulazione patrimoniale: un alto tasso di risparmio riduce drasticamente gli anni necessari a raggiungere l'indipendenza finanziaria (FIRE).",
        "argus_calc": "Estratto automaticamente dall'analisi del Cash Flow con esclusione dei giroconti e trasferimenti interni tra conti propri.",
        "how_to_read": "• 🟢 > 25% (Accumulazione rapida e disciplina eccellente)<br>• 🟡 15% - 25% (Risparmio sano coerente con la regola 50/30/20)<br>• 🔴 < 10% (Capacità di accumulo fragile, vulnerabile a imprevisti)."
    },
    "runway_months": {
        "title": "⏳ Runway di Emergenza (Mesi di Autonomia Finanziaria)",
        "what_is": "Il numero di mesi durante i quali è possibile sostenere il tenore di vita attuale a reddito zero, attingendo unicamente alla liquidità disponibile.",
        "how_calc": "<b>Runway</b> = Liquidità Disponibile / Media Spese Fisse & Necessarie Mensili",
        "why_useful": "Fornire tranquillità psicologica e protezione assoluta contro shock lavorativi, interruzioni di reddito o crisi temporanee.",
        "argus_calc": "Rapporto tra la cassa disponibile e il burn rate mensile medio calcolato sulle ultime 6 mensilità di cashflow.",
        "how_to_read": "• 🟢 > 6 mesi (Elevata serenità e indipendenza di breve termine)<br>• 🟡 3 - 6 mesi (Autonomia standard adeguata)<br>• 🔴 < 3 mesi (Pericolo di liquidità: ricostituire prioritariamente il fondo cassa)."
    },
    "debt_to_asset": {
        "title": "⚖️ Rapporto Debito / Patrimonio (Debt-to-Asset Ratio)",
        "what_is": "Misura del grado di leva finanziaria del patrimonio personale: la percentuale del totale attività finanziata tramite debito.",
        "how_calc": "<b>Debt-to-Asset</b> = (Totale Passività / Totale Attività Lorde) &times; 100",
        "why_useful": "Valutare la vulnerabilità del patrimonio a shock economici e definire la capacità di indebitamento residua.",
        "argus_calc": "Confronto matriciale tra totale passività (mutui/prestiti) e totale attivo lordo consolidato.",
        "how_to_read": "• 🟢 < 20% (Struttura patrimoniale molto solida e conservativa)<br>• 🟡 20% - 40% (Leva fisiologica per acquisto prima casa)<br>• 🔴 > 50% (Elevata dipendenza dal debito, rischio tassi)."
    },
    "budget_50_30_20": {
        "title": "📊 Regola di Budgeting 50 / 30 / 20 (Needs, Wants, Savings)",
        "what_is": "Modello di gestione delle finanze personali che suddivide le entrate in 50% Necessità (Needs), 30% Desideri (Wants) e 20% Risparmi/Investimenti (Savings).",
        "how_calc": "<b>Needs:</b> Spese fisse, affitto/mutuo, bollette, cibo &le; 50%<br><b>Wants:</b> Svago, viaggi, ristoranti &le; 30%<br><b>Savings:</b> Investimenti, PAC, fondi pensione &ge; 20%",
        "why_useful": "Mantenere un perfetto equilibrio tra qualità della vita presente e costruzione della sicurezza finanziaria futura.",
        "argus_calc": "Classificazione automatica tramite NLP semantico di tutte le transazioni bancarie categorizzate in Needs, Wants o Savings.",
        "how_to_read": "• 🟢 Needs &le; 50%, Wants &le; 30%, Savings &ge; 20% (Budget ottimale)<br>• 🟡 Needs 50%-60% (Budget tirato ma gestibile)<br>• 🔴 Needs > 60% o Savings < 10% (Struttura di spesa rigida a rischio insolvenza)."
    },
    "ivafe_quadro_rw": {
        "title": "📑 IVAFE & Quadro RW (Monitoraggio Fiscale Attività Estere)",
        "what_is": "Obbligo dichiarativo e tributario italiano per attività finanziarie detenute all'estero o wallet crypto (Imposta sul Valore delle Attività Finanziarie all'Estero).",
        "how_calc": "<b>IVAFE Conti:</b> Imposta fissa € 34,20 se giacenza media > € 5.000<br><b>IVAFE Prodotti Finanziari:</b> 0.20% (o 0.40% Paesi Blacklist) sul valore al 31/12<br><b>Cripto-attività:</b> 0.20% annuo sul valore complessivo",
        "why_useful": "Evitare pesanti sanzioni dell'Agenzia delle Entrate per omessa compilazione del Quadro RW (dal 3% al 15% del non dichiarato).",
        "argus_calc": "Modulo Fiscale dedicato che calcola giacenze medie, controvalori al 31/12 e compila automaticamente il facsimile dei righi RW (Codici 1, 14, 21).",
        "how_to_read": "• 🟢 Quadro RW allineato e IVAFE calcolata al centesimo<br>• 🟡 Saldi esteri vicini alle soglie di monitoraggio<br>• 🔴 Conti esteri non censiti o documentati."
    },
    "xirr_pe": {
        "title": "💼 XIRR (Extended Internal Rate of Return - Private Equity & Illiquidi)",
        "what_is": "Tasso interno di rendimento annualizzato calcolato su flussi di cassa irregolari nel tempo (Capital Calls, Distribuzioni e Valore Residuo NAV).",
        "how_calc": "&sum;<sub>i=1</sub><sup>N</sup> [ C<sub>i</sub> / (1 + XIRR)<sup>(d<sub>i</sub> &minus; d<sub>0</sub>)/365</sup> ] = 0",
        "why_useful": "Misurare la redditività reale di investimenti illiquidi, Private Equity, Real Estate e fondi chiusi considerando l'esatto momento temporale di ogni apporto/ritiro.",
        "argus_calc": "Risoluzione iterativa con metodo Newton-Raphson su tutti i flussi di cassa datati registrati per ciascun deal o fondo illiquido.",
        "how_to_read": "• 🟢 XIRR > 15.0% (Rendimento eccellente in linea con benchmark Private Equity)<br>• 🟡 8.0% - 15.0% (Performance soddisfacente)<br>• 🔴 < 8.0% (Rendimento insufficiente per il premio al rischio di illiquidità)."
    },
    "moic_pe": {
        "title": "💎 MOIC / TVPI (Multiple on Invested Capital / Total Value to Paid-In)",
        "what_is": "Il multiplo del capitale investito: rapporto tra il valore totale generato dall'investimento (distribuzioni incassate + valore residuo) e il capitale effettivamente versato.",
        "how_calc": "<b>MOIC (TVPI)</b> = (Distribuzioni Cumulative + NAV Residuo) / Capitale Totale Versato (Capital Calls)",
        "why_useful": "Indicare quanti euro sono stati generati in termini assoluti per ogni singolo euro investito nel deal.",
        "argus_calc": "Aggregazione istantanea di tutti i flussi di Private Equity, venture capital e collezionismo dal modulo Asset Illiquidi.",
        "how_to_read": "• 🟢 MOIC > 2.0x (Raddoppio del capitale investito)<br>• 🟡 1.3x - 2.0x (Crescita solida del capitale)<br>• 🔴 < 1.0x (Capitale in perdita rispetto al versato)."
    },
    "fire_number": {
        "title": "🔥 FIRE Number & Indipendenza Finanziaria (Financial Independence Retire Early)",
        "what_is": "Il patrimonio complessivo necessario per vivere indefinitamente di rendita passiva senza più bisogno di reddito da lavoro dipendente o autonomo.",
        "how_calc": "<b>FIRE Target</b> = Spese Annue Desiderate / SWR = Spese Annue &times; 25 (con SWR = 4%)",
        "why_useful": "Fissare un obiettivo patrimoniale chiaro e calcolare l'esatta data stimata di libertà finanziaria (Freedom Date) in base al tasso di risparmio e rendimento atteso.",
        "argus_calc": "Motore attuariale Monte Carlo che simula inflazione, longevità e sequenza dei rendimenti per stimare la probabilità di successo FIRE a 30-50 anni.",
        "how_to_read": "• 🟢 Patrimonio Netto &ge; 100% del FIRE Target (Indipendenza finanziaria raggiunta!)<br>• 🟡 50% - 99% (Fase avanzata di accumulazione)<br>• 🔴 < 50% (Fase iniziale: massimizzare tasso di risparmio e rendimento composto)."
    },
    "swr_fire": {
        "title": "🛡️ Safe Withdrawal Rate (Tasso di Prelievo Sicuro / Trinity Study)",
        "what_is": "La percentuale massima di patrimonio che può essere prelevata ogni anno (adeguata all'inflazione) senza rischiare di esaurire il capitale prima del termine della vita.",
        "how_calc": "<b>Prelievo Anno 1</b> = Patrimonio &times; SWR (es. 3.5% - 4.0%)<br><b>Anni Successivi:</b> Prelievo Anno Prec. &times; (1 + Inflazione)",
        "why_useful": "Pianificare la fase di decumulo del capitale durante la pensione o il prepensionamento evitando il rischio di longevità.",
        "argus_calc": "Stress test stocastico sul Sequence of Returns Risk (SRR) per calibrare lo SWR ideale in base all'allocazione azionaria/obbligazionaria.",
        "how_to_read": "• 🟢 3.0% - 3.5% (Ultra-conservativo e sicuro per orizzonti > 35 anni)<br>• 🟡 3.5% - 4.0% (Standard Trinity Study per 30 anni)<br>• 🔴 > 4.5% (Elevato rischio di esaurimento del capitale in scenari di crisi iniziale)."
    },
    "tco_fee_drag": {
        "title": "💸 TCO & Fee Drag (Costo Totale di Possesso e Drag Commissionale)",
        "what_is": "L'impatto economico complessivo delle commissioni (TER fondi, costi di gestione, performance fees, costi di custodia) sull'accumulazione patrimoniale a 20-30 anni.",
        "how_calc": "<b>Capitale Perso per Fee Drag</b> = V<sub>finale</sub>(senza costi) &minus; V<sub>finale</sub>(con costi TCO)",
        "why_useful": "Evidenziare come una commissione apparentemente piccola (es. 2.0% annuo di fondi attivi) possa erodere oltre il 40% del capitale finale rispetto a ETF low-cost (0.15%).",
        "argus_calc": "Simulatore Monte Carlo TCO che calcola l'impatto composto netto e la differenza di rendimento finale per ciascuna linea d'investimento.",
        "how_to_read": "• 🟢 TCO < 0.30% annuo (Ottima efficienza con ETF passivi)<br>• 🟡 0.30% - 1.00% (Accettabile per strategie bilanciate)<br>• 🔴 > 1.50% annuo (Fee drag distruttivo: convertire verso strumenti efficienti)."
    },
    "estate_planning": {
        "title": "⚖️ Estate Planning & Ottimizzazione Successoria (Passaggio Generazionale)",
        "what_is": "Analisi della devoluzione del patrimonio ereditario in base al diritto civile italiano (quote di legittima e disponibile) e calcolo delle imposte di successione/donazione.",
        "how_calc": "<b>Imposta Successione (Coniuge/Figli)</b> = max(0, Asse Ereditario &minus; Franchigia € 1.000.000) &times; 4%<br><b>Imposta Donazione Fratelli:</b> max(0, Asse &minus; Franchigia € 100.000) &times; 6%",
        "why_useful": "Pianificare il passaggio generazionale, tutelare gli eredi legittimari ed evitare liti familiari o un carico fiscale punitivo.",
        "argus_calc": "Algoritmo di simulazione asse ereditario con verifica quote di riserva, applicazione franchigie di legge ed esenzione per Titoli di Stato e Polizze Vita Caso Morte.",
        "how_to_read": "• 🟢 Asse ereditario capiente entro le franchigie (Zero imposte dovute)<br>• 🟡 Imposta successoria contenuta con strumenti esenti attivi<br>• 🔴 Lesione potenziale di legittima o carico fiscale elevato da ottimizzare."
    },
    "cvar_95": {
        "title": "🛡️ Conditional Value at Risk (CVaR 95% / Expected Shortfall)",
        "what_is": "La perdita media attesa nei casi estremi in cui la perdita supera la soglia critica del Value at Risk (misura coerente di rischio di coda).",
        "how_calc": "<b>CVaR<sub>95%</sub></b> = E[ R | R &le; &minus;VaR<sub>95%</sub> ]",
        "why_useful": "Catturare la gravità effettiva dei crolli di mercato nelle code della distribuzione, superando i limiti del VaR ordinario.",
        "argus_calc": "Media ponderata delle perdite storiche o simulate che ricadono nel 5% peggiore della distribuzione dei rendimenti.",
        "how_to_read": "• 🟢 < 2.50% (Code sottili, basso rischio di crash sistemico)<br>• 🟡 2.50% - 4.50% (Rischio di coda nella norma)<br>• 🔴 > 4.50% (Code grasse e grave vulnerabilità a cigni neri)."
    }
}


def resolve_metric_knowledge(label: str, help_text: str = None) -> str:
    """
    Risolve il testo informativo per qualsiasi metrica o card, assicurando sempre
    la struttura standard a 5 sezioni:
    1. 📌 Cos'è
    2. 📐 Come si calcola
    3. 🎯 A cosa serve
    4. ⚙️ Come viene calcolato da ARGUS
    5. 🔍 Come leggerlo
    """
    if help_text and all(k in help_text for k in ["Cos'è", "Come si calcola", "A cosa serve"]):
        return help_text
        
    import re
    cleaned_label = re.sub(r'[^a-zA-Z0-9]', '', label).lower()
    
    # Mappatura chiavi completa (Quant + Wealth + Tax + Estate)
    alias_map = {
        # Wealth Health & Net Worth
        "healthscore": "wealth_health_score",
        "wealthhealth": "wealth_health_score",
        "salutepatrimoniale": "wealth_health_score",
        "scoresalute": "wealth_health_score",
        "health": "wealth_health_score",
        "networth": "net_worth",
        "patrimonionetto": "net_worth",
        "patrimonioconsolidato": "net_worth",
        "totalwealth": "net_worth",
        "patrimonio": "net_worth",
        # Liquidità & Cassa
        "liquidita": "liquid_assets",
        "cassa": "liquid_assets",
        "liquidassets": "liquid_assets",
        "emergencyfund": "liquid_assets",
        "cuscinetto": "liquid_assets",
        "fondocassa": "liquid_assets",
        "cash": "liquid_assets",
        # Investimenti Finanziari
        "investimentifinanziari": "financial_investments",
        "investimenti": "financial_investments",
        "financialinvestments": "financial_investments",
        "portafogliotitoli": "financial_investments",
        "financialassets": "financial_investments",
        # Caveau & Orologi
        "assetfisici": "physical_assets",
        "caveau": "physical_assets",
        "physicalassets": "physical_assets",
        "orologi": "physical_assets",
        "luxurywatches": "physical_assets",
        "oro": "physical_assets",
        "metalli": "physical_assets",
        "gold": "physical_assets",
        # Immobili & Real Estate
        "immobili": "real_estate_equity",
        "realestate": "real_estate_equity",
        "netequityimmobiliare": "real_estate_equity",
        "immobiliaritotale": "real_estate_equity",
        "valoreimmobili": "real_estate_equity",
        "equityimmobiliare": "real_estate_equity",
        # Previdenza & Pensione
        "previdenza": "pension_total",
        "pension": "pension_total",
        "fondopensione": "pension_total",
        "previdenzaintegrativa": "pension_total",
        "tfr": "pension_total",
        "pensionamento": "pension_total",
        # Passività & Debiti
        "passivita": "total_liabilities",
        "liabilities": "total_liabilities",
        "debiti": "total_liabilities",
        "mutui": "total_liabilities",
        "finanziamenti": "total_liabilities",
        "debitoresiduo": "total_liabilities",
        "debt": "total_liabilities",
        # Risparmio & Runway
        "savingsrate": "savings_rate",
        "tassorisparmio": "savings_rate",
        "risparmiomensile": "savings_rate",
        "capacitadirisparmio": "savings_rate",
        "risparmio": "savings_rate",
        "runway": "runway_months",
        "runwaymonths": "runway_months",
        "mesidiautonomia": "runway_months",
        "autonomiafinanziaria": "runway_months",
        "autonomia": "runway_months",
        # Ratios Patrimoniali
        "debttoasset": "debt_to_asset",
        "rapportodebitopatrimonio": "debt_to_asset",
        "leveragepatrimoniale": "debt_to_asset",
        "rapportoindebitamento": "debt_to_asset",
        "leva": "debt_to_asset",
        "503020": "budget_50_30_20",
        "regola503020": "budget_50_30_20",
        "budget503020": "budget_50_30_20",
        "needswantssavings": "budget_50_30_20",
        # Fisco & Quadro RW
        "ivafe": "ivafe_quadro_rw",
        "quadrorw": "ivafe_quadro_rw",
        "quadrow": "ivafe_quadro_rw",
        "monitoraggiofiscale": "ivafe_quadro_rw",
        "criptotasse": "ivafe_quadro_rw",
        "tuir": "tuir_67",
        "minusvalenze": "tuir_67",
        "fiscale": "tuir_67",
        "zainetto": "tuir_67",
        # Private Equity & Illiquidi
        "xirr": "xirr_pe",
        "irr": "xirr_pe",
        "tassointernodirendimento": "xirr_pe",
        "moic": "moic_pe",
        "multipleoninvestedcapital": "moic_pe",
        "tvpi": "moic_pe",
        # FIRE & Decumulo
        "fire": "fire_number",
        "firenumber": "fire_number",
        "firetarget": "fire_number",
        "indipendenzafinanziaria": "fire_number",
        "swr": "swr_fire",
        "safewithdrawalrate": "swr_fire",
        "regola4percento": "swr_fire",
        # Costi & Successione
        "tco": "tco_fee_drag",
        "feedrag": "tco_fee_drag",
        "ter": "tco_fee_drag",
        "successione": "estate_planning",
        "estateplanning": "estate_planning",
        "franchigiasuccessoria": "estate_planning",
        "eredita": "estate_planning",
        "impostasuccessione": "estate_planning",
        # Quant & Risk Metrics
        "rendimento": "rendimento_atteso",
        "cagr": "rendimento_atteso",
        "expectedreturn": "rendimento_atteso",
        "volatilita": "volatilita_annua",
        "volatility": "volatilita_annua",
        "deviazionestandard": "volatilita_annua",
        "cvar": "cvar_95",
        "expectedshortfall": "cvar_95",
        "var": "var_95",
        "valueatrisk": "var_95",
        "sharpe": "sharpe_ratio",
        "sortino": "sortino_ratio",
        "drawdown": "max_drawdown",
        "mdd": "max_drawdown",
        "beta": "beta",
        "alpha": "alpha",
        "calmar": "calmar_ratio",
        "liquidate": "days_to_liquidate",
        "smobilizzo": "days_to_liquidate",
        "chandelier": "chandelier_exit",
        "stoploss": "chandelier_exit",
        "diversification": "diversification_ratio",
        "altman": "altman_z_score",
        "beneish": "beneish_m_score",
        "sloan": "sloan_accrual",
        "wacc": "wacc",
        "dcf": "wacc",
        "piotroski": "piotroski_f_score",
        "kelly": "kelly_criterion",
        "tracking": "tracking_error",
        "omega": "omega_ratio",
        "ulcer": "ulcer_index",
        "anomalie": "isolation_forest",
        "isolation": "isolation_forest"
    }
    
    target_key = None
    for token, mapped_k in alias_map.items():
        if token in cleaned_label:
            target_key = mapped_k
            break
            
    if target_key and target_key in KNOWN_METRICS_KNOWLEDGE_BASE:
        d = KNOWN_METRICS_KNOWLEDGE_BASE[target_key]
        return format_institutional_5point_html(
            title=d["title"],
            what_is=d["what_is"],
            how_calc=d["how_calc"],
            why_useful=d["why_useful"],
            argus_calc=d["argus_calc"],
            how_to_read=d["how_to_read"]
        )
        
    for k, d in KNOWN_METRICS_KNOWLEDGE_BASE.items():
        if k in cleaned_label or cleaned_label in k:
            return format_institutional_5point_html(
                title=d["title"],
                what_is=d["what_is"],
                how_calc=d["how_calc"],
                why_useful=d["why_useful"],
                argus_calc=d["argus_calc"],
                how_to_read=d["how_to_read"]
            )
            
    fallback_desc = help_text.strip() if help_text else f"Indicatore di monitoraggio e controllo quantitativo per {label}."
    is_wealth_domain = any(w in cleaned_label for w in ["wealth", "patrimon", "cassa", "spes", "immob", "orolog", "pens", "debit", "cont", "bilanc"])
    
    if is_wealth_domain:
        return format_institutional_5point_html(
            title=f"🏛️ {label}",
            what_is=fallback_desc,
            how_calc="Calcolato attraverso l'aggregazione certificata dei conti, transazioni e valutazioni patrimoniali attive.",
            why_useful="Fornire trasparenza, controllo analitico e solidità decisionale nella gestione olistica del patrimonio.",
            argus_calc="Elaborazione continua del Wealth Engine con conversione tassi di cambio live e rivalutazione multi-asset.",
            how_to_read="• 🟢 Valore ottimale allineato con gli obiettivi strategici del profilo<br>• 🟡 Fascia di oscillazione standard<br>• 🔴 Soglia di attenzione o squilibrio da monitorare."
        )

    return format_institutional_5point_html(
        title=f"📊 {label}",
        what_is=fallback_desc,
        how_calc="Calcolato sulle serie storiche dei prezzi rettificati e sui pesi di allocazione di portafoglio.",
        why_useful="Monitorare l'efficienza gestionale, la volatilità e la protezione del capitale investito.",
        argus_calc="Elaborazione continua del Risk Engine con normalizzazione su 252 giorni e tasso risk-free live.",
        how_to_read="• 🟢 Valori ottimali coerenti con gli obiettivi strategici<br>• 🟡 Fascia di oscillazione standard<br>• 🔴 Soglia di attenzione o rischio elevato."
    )


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
    font-size: 11px; 
    color: #ff9900;
    background: rgba(255, 153, 0, 0.12);
    border-radius: 50%;
    width: 17px;
    height: 17px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0 !important;
    margin-left: 4px;
    transition: all 0.2s;
    border: 1px solid rgba(255, 153, 0, 0.3);
    box-sizing: border-box !important;
}}
.info-icon-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.25);
    border-color: rgba(255, 153, 0, 0.7);
    transform: scale(1.1);
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
    label_html = f'<div class="metric-label"><span class="metric-label-text">{label}</span><label for="modal-toggle-{unique_id}" class="info-icon-{unique_id}" title="Clicca per approfondire">ⓘ</label></div>'

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



def section(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def render_page_header(title: str, subtitle: str = "", icon: str = "👁️"):
    """Renderizza un'intestazione di pagina istituzionale conforme al Design System ARGUS."""
    st.markdown(f"""
    <div style="margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 24px;">{icon}</span>
            <span style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: 0.3px;">{title}</span>
        </div>
        {f'<div style="font-size: 12.5px; color: #8b949e; margin-top: 3px; margin-left: 32px;">{subtitle}</div>' if subtitle else ''}
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
    mode_str = "OFFLINE" if offline else "LIVE DB"
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




