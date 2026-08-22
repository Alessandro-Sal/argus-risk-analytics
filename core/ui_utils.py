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
        .metric-value, [data-testid="stMetricValue"], [data-testid="stMetricDelta"], code, .mono-num, td, th {{
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

        [data-testid="stAppViewContainer"] {{
            background: {bg_gradient};
            background-size: cover;
            background-attachment: fixed;
            color: #e6edf3;
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
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.06);
            position: relative;
            overflow: hidden;
            transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
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
            opacity: 0.85;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 153, 0, 0.35);
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35), 0 0 16px rgba(255, 153, 0, 0.15);
        }}

        .metric-label {{ 
            color: #8b949e; 
            font-size: 11.5px; 
            font-weight: 600; 
            letter-spacing: 0.6px; 
            text-transform: uppercase;
        }}
        
        .metric-value {{ 
            background: linear-gradient(90deg, #ffffff, #c9d1d9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: clamp(17px, 1.45vw, 23px); 
            font-weight: 700; 
            margin-top: 6px;
            letter-spacing: -0.5px;
            white-space: nowrap;
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
        .argus-tab-deck-container button[kind="secondary"] {{
            background: rgba(255, 255, 255, 0.02) !important;
            border: 1px solid rgba(255, 255, 255, 0.06) !important;
            border-radius: 8px !important;
            color: #8b949e !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            letter-spacing: 0.2px !important;
            padding: 7px 10px !important;
            min-height: 38px !important;
            height: 38px !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            text-align: center !important;
            transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: none !important;
            transform: none !important;
        }}

        .argus-tab-deck-container button[kind="secondary"]:hover {{
            background: rgba(255, 255, 255, 0.07) !important;
            border-color: rgba(255, 255, 255, 0.18) !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }}

        /* Active Tab Deck Button (Illuminated Dark Metal Capsule) */
        .argus-tab-deck-container button[kind="primary"] {{
            background: linear-gradient(180deg, #24292f 0%, #161b22 100%) !important;
            border: 1px solid #ff9900 !important;
            border-bottom: 3px solid #ff9900 !important;
            border-radius: 8px !important;
            color: #ff9900 !important;
            font-size: 12.5px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px !important;
            padding: 7px 10px !important;
            min-height: 38px !important;
            height: 38px !important;
            line-height: 1.2 !important;
            white-space: normal !important;
            text-align: center !important;
            box-shadow: 0 4px 16px rgba(255, 153, 0, 0.25), 0 0 10px rgba(255, 153, 0, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
            transform: none !important;
        }}

        .argus-tab-deck-container button[kind="primary"]:hover {{
            box-shadow: 0 6px 20px rgba(255, 153, 0, 0.35), 0 0 14px rgba(255, 153, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        }}

        /* Legacy Radio Fallback (Hidden) */
        div[data-testid="stRadio"] > div[role="radiogroup"] {{
            display: inline-flex !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 4px !important;
            background: rgba(13, 17, 23, 0.85) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 4px !important;
            margin: 6px 0 16px 0 !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 7px !important;
            padding: 6px 14px !important;
            cursor: pointer !important;
            transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
            margin: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
            background: rgba(255, 255, 255, 0.05) !important;
            border-color: rgba(255, 255, 255, 0.1) !important;
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
            padding: 5px 10px !important;
            min-height: 30px !important;
            height: 30px !important;
            font-size: 11.5px !important;
            font-weight: 600 !important;
            color: #c9d1d9 !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
            display: flex !important;
            align-items: center !important;
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
            padding: 4px 6px 5px 6px !important;
            background: rgba(13, 17, 23, 0.5) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
        }}
        section[data-testid="stSidebar"] label p {{
            font-size: 10px !important;
            font-weight: 700 !important;
            color: #8b949e !important;
            text-transform: uppercase !important;
            letter-spacing: 0.4px !important;
            margin-bottom: -2px !important;
        }}
        section[data-testid="stSidebar"] input {{
            font-size: 11.5px !important;
            padding: 4px 8px !important;
            border-radius: 6px !important;
            background: rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #ffffff !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] {{
            font-size: 11.5px !important;
            border-radius: 6px !important;
            background: rgba(22, 27, 34, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            min-height: 30px !important;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
            font-size: 11.5px !important;
        }}

        /* Direct Top-Level Navigation Buttons (Matching Expanders) */
        section[data-testid="stSidebar"] > div > div > div > .stButton > button,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > .stButton > button,
        section[data-testid="stSidebar"] .stButton > button {{
            padding: 5px 10px !important;
            min-height: 30px !important;
            height: 30px !important;
            font-size: 11.5px !important;
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
            padding: 3px 8px !important;
            min-height: 24px !important;
            height: 24px !important;
            line-height: 18px !important;
            font-size: 11px !important;
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
    
    scroll_to_top()

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
    """Renderizza la barra di stato e comando ARGUS v5.14.0 in cima alla pagina con telemetria, spotlight e popout 2° monitor."""
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
            <span style="background:rgba(255,153,0,0.12); color:#ff9900; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700; border:1px solid rgba(255,153,0,0.25); letter-spacing:0.3px;">
                v5.14.0
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
                st.session_state["show_spotlight_palette"] = True

    # Rendering della Command Palette se attivata
    if st.session_state.get("show_spotlight_palette", False):
        render_spotlight_palette()


def render_spotlight_palette():
    """Renderizza la Command Palette Spotlight in stile Raycast / Linear / Bloomberg Terminal."""
    from core.sidebar import NAV_MODULES, switch_to_page
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(28, 33, 40, 0.95) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1.5px solid #ff9900; border-radius: 12px; padding: 14px 18px; margin: 10px 0 20px 0; box-shadow: 0 12px 40px rgba(0,0,0,0.7), 0 0 24px rgba(255,153,0,0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:14px; font-weight:800; color:#ff9900; letter-spacing:0.6px; display:flex; align-items:center; gap:8px;">
                <span>⚡</span> ARGUS SPOTLIGHT COMMAND PALETTE & SEARCH
            </div>
            <div style="font-size:11px; color:#8b949e;">Digita per filtrare • Clicca per saltare direttamente</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_q, col_close = st.columns([5.5, 1.0])
    with col_q:
        query = st.text_input(
            "Cerca", 
            placeholder="🔍 Digita: es. Monte Carlo, DCF, AAPL, VaR, Fisco, Barra, HRP, FIFO, Kupiec, Screener...", 
            key="spotlight_search_box", 
            label_visibility="collapsed"
        ).strip().lower()
    with col_close:
        if st.button("✕ Chiudi", key="btn_close_spotlight", use_container_width=True):
            st.session_state["show_spotlight_palette"] = False
            st.rerun()

    results_data = st.session_state.get("results", {})
    df_pos = results_data.get("positions", None) if isinstance(results_data, dict) else None
    portfolio_tickers = []
    if df_pos is not None and hasattr(df_pos, "columns") and "ticker" in df_pos.columns:
        portfolio_tickers = [str(t).upper() for t in df_pos["ticker"].dropna().unique() if not str(t).endswith("=X")]

    col_res1, col_res2, col_res3 = st.columns([1.6, 1.4, 1.0])

    # ── COLONNA 1: SCHEDE & SOTTOMODULI ─────────────────────────────
    with col_res1:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">📑 SCHEDE & MODULI ANALITICI</div>', unsafe_allow_html=True)
        
        # Mappatura arricchita con sinonimi di ricerca
        search_index = [
            # Control Room
            {"title": "🎛️ Control Room & Ingestione CSV", "page": "0_Control_Room.py", "tab_key": None, "target": None, "keywords": "control room upload csv degiro database ingestione parametri mysql offline"},
            # Dashboard
            {"title": "📈 Dashboard Generale & KPI Executive", "page": "pages/1_📈_Dashboard_Generale.py", "tab_key": None, "target": None, "keywords": "dashboard cagr sharpe rendimento cumulato benchmark max drawdown kpi"},
            # Rischio
            {"title": "🔴 Rischio ➔ VaR & CVaR (Parametrico, Storico, Cornish-Fisher)", "page": "pages/2_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📉 VaR, CVaR & Backtesting Kupiec", "keywords": "var cvar cornish fisher parametrico storico rischio perdita"},
            {"title": "🔴 Rischio ➔ Backtesting VaR & Test Kupiec", "page": "pages/2_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📉 VaR, CVaR & Backtesting Kupiec", "keywords": "kupiec basel backtesting violazioni var test p-value"},
            {"title": "🔴 Rischio ➔ Modello Fama-French & Carhart (4 Fattori)", "page": "pages/2_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📊 Profilo del Rischio & Fama-French", "keywords": "fama french carhart smb hml mom wml fattori regressione alpha beta"},
            {"title": "🔴 Rischio ➔ Limiti di Rischio & Conformità UCITS", "page": "pages/2_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "📊 Profilo del Rischio & Fama-French", "keywords": "limiti concentrazione ucits mifid conformità breach stop loss"},
            {"title": "🔴 Rischio ➔ Rilevamento Anomalie ML (Isolation Forest)", "page": "pages/2_🔴_Analisi_Rischio.py", "tab_key": "risk_active_tab", "target": "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)", "keywords": "isolation forest machine learning anomalie outlier cluster ml"},
            # Quant
            {"title": "🔬 Quant ➔ Frontiera Markowitz & Rebalancing Sandbox", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "📊 Frontiera Markowitz & Rebalancing", "keywords": "markowitz frontiera efficiente ledoit wolf sandbox ribilanciamento pesi sharpe"},
            {"title": "🔬 Quant ➔ Hierarchical Risk Parity (HRP)", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "📊 Frontiera Markowitz & Rebalancing", "keywords": "hrp hierarchical risk parity lopez de prado clustering dendrogramma"},
            {"title": "🔬 Quant ➔ Tail Copula (Clayton/Gumbel) & Kelly Criterion Simulator", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🧬 Tail Copula & Kelly Sizing", "keywords": "tail copula clayton gumbel kelly criterion sizing half kelly crash contagion asimmetria coda"},
            {"title": "🔬 Quant ➔ Monte Carlo 10k Paths & Merton Jump", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🎲 Simulazioni Stocastiche (Monte Carlo & Merton)", "keywords": "monte carlo merton jump diffusion student-t cholesky simulazione stocastica"},
            {"title": "🔬 Quant ➔ Prezzatore Opzioni Black-Scholes & Delta Hedge", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🛡️ Hedging Tattico & Tail Risk", "keywords": "opzioni black scholes call put greeks delta gamma theta vega hedge coperture"},
            {"title": "🔬 Quant ➔ Performance Attribution Brinson-Fachler", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🎯 Attribuzione Brinson-Fachler", "keywords": "brinson fachler allocazione selezione interazione benchmark attribution"},
            {"title": "🔬 Quant ➔ Modelli Fattoriali (Carhart, Barra & Black-Litterman)", "page": "pages/3_🔬_Modelli_Quantitativi.py", "tab_key": "quant_active_tab", "target": "🏛️ Modelli Fattoriali, Black-Litterman & ML", "keywords": "carhart barra fama french black litterman fattori regressione ml"},
            # Posizioni
            {"title": "📋 Posizioni ➔ FIFO Realized/Unrealized Book", "page": "pages/4_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "📋 Posizioni Attive & Costi FIFO", "keywords": "posizioni fifo plusvalenze minusvalenze pnl book ordini titoli"},
            {"title": "📋 Posizioni ➔ Fisco Italiano TUIR Art. 67 & Minus", "page": "pages/4_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "💰 Ottimizzazione Fiscale (TUIR Art. 67)", "keywords": "fisco tasse tuir imposte minusvalenze capital gain 26% 12.5% tax harvesting"},
            {"title": "📋 Posizioni ➔ Calendario Dividendi & Yield", "page": "pages/4_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "📅 Proiezione Dividendi", "keywords": "dividendi stacco yield cedole proiezioni calendario flusso cassa"},
            {"title": "📋 Posizioni ➔ Liquidità Almgren-Chriss", "page": "pages/4_📋_Posizioni_e_Dettagli.py", "tab_key": "positions_active_tab", "target": "⚡ Liquidità Almgren-Chriss", "keywords": "almgren chriss liquidita market impact impatto mercato liquidazione"},
            # Valutazione
            {"title": "🏛️ Valutazione ➔ DCF Monte Carlo Intrinseco & WACC", "page": "pages/5_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "🧮 Valutazione Intrinseca DCF Monte Carlo", "keywords": "dcf discounted cash flow wacc capm fair value intrinseco monte carlo"},
            {"title": "🏛️ Valutazione ➔ Solvibilità Altman Z-Score & DuPont", "page": "pages/5_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "📊 Bilanci & Solvibilità (Altman & DuPont)", "keywords": "altman z score dupont bilanci solvibilita bancarotta piotroski f-score"},
            {"title": "🏛️ Valutazione ➔ Forensic Accounting (Beneish M-Score & Sloan)", "page": "pages/5_🏛️_Valutazione_Aziendale.py", "tab_key": "val_segmented_tab", "target": "📊 Bilanci & Solvibilità (Altman & DuPont)", "keywords": "beneish m score sloan accrual manipolazione bilancio frode contabile"},
            # Stress
            {"title": "🌪️ Stress Testing ➔ Matrice Comparativa MSCI Barra", "page": "pages/6_🌪️_Stress_Testing.py", "tab_key": "stress_active_tab", "target": "⚡ Matrice Comparativa MSCI Barra", "keywords": "stress testing msci barra scenari storici crisi 2008 covid crollo"},
            {"title": "🌪️ Stress Testing ➔ Superficie di Volatilità 3D & What-If", "page": "pages/6_🌪️_Stress_Testing.py", "tab_key": "stress_active_tab", "target": "🛠️ Simulatore What-if Custom", "keywords": "superficie 3d what-if simulatore shock tassi inflazione macro"},
            # Temporale
            {"title": "📊 Temporale ➔ Serie Storiche & Side-by-Side Drift", "page": "pages/7_📊_Analisi_Temporale.py", "tab_key": "time_active_tab", "target": "📈 Serie Storiche Temporali", "keywords": "serie storiche temporale snapshot drift evoluzione patrimonio"},
            # Tecnica
            {"title": "📈 Tecnica ➔ Candlestick Cockpit & Volume Profile (POC)", "page": "pages/8_📈_Analisi_Tecnica.py", "tab_key": "tech_active_subtab", "target": "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)", "keywords": "analisi tecnica candlestick volume profile poc vah val rsi macd bollinger ema"},
            {"title": "📈 Tecnica ➔ Confluence Score & Pattern Recognition", "page": "pages/8_📈_Analisi_Tecnica.py", "tab_key": "tech_active_subtab", "target": "🚦 Confluence Score & Pattern Recognition", "keywords": "confluence score pattern candlestick engulfing doji martello segnali"},
            # Screener
            {"title": "🔍 Screener ➔ Screener Opportunità & Archetipi", "page": "pages/9_🔍_Screener_Opportunita.py", "tab_key": "screener_segmented_subtab", "target": "🔍 Screener Multi-Fattoriale & Archetipi", "keywords": "screener filtri opportunita momentum value growth dividendi qualita"},
            {"title": "🔍 Screener ➔ Pre-Trade Impact Simulator", "page": "pages/9_🔍_Screener_Opportunita.py", "tab_key": "screener_segmented_subtab", "target": "🧪 Pre-Trade Portfolio Impact Simulator", "keywords": "pre-trade simulatore impatto nuovo acquisto asset candidato"}
        ]

        matched = []
        for item in search_index:
            if not query:
                matched.append(item)
            else:
                q_words = query.split()
                if any(w in item["title"].lower() or w in item["keywords"].lower() for w in q_words):
                    matched.append(item)

        if matched:
            for item in matched[:7]:
                if st.button(item["title"], key=f"spot_idx_{item['title']}", use_container_width=True):
                    if item["tab_key"] and item["target"]:
                        st.session_state[item["tab_key"]] = item["target"]
                        st.session_state[f"target_subtab_{item['tab_key']}"] = item["target"]
                        st.session_state["global_target_subtab"] = item["target"]
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page(item["page"])
        else:
            st.caption("Nessuna scheda trovata per la ricerca.")

    # ── COLONNA 2: TICKER & ASSET FINANZIARI ────────────────────────
    with col_res2:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">💼 TICKER & AZIONI RAPIDE</div>', unsafe_allow_html=True)
        
        # Mostra ticker del portafoglio se presenti
        display_tickers = portfolio_tickers if portfolio_tickers else ["AAPL", "MSFT", "NVDA", "BTC-USD", "SPY", "QQQ"]
        if query and query.upper() not in display_tickers:
            # Consenti la ricerca di qualsiasi ticker digitato
            cleaned_q = query.upper().strip()
            if len(cleaned_q) >= 2:
                display_tickers = [cleaned_q] + [t for t in display_tickers if query in t.lower()]
        elif query:
            display_tickers = [t for t in display_tickers if query in t.lower()]

        for tk in display_tickers[:4]:
            st.markdown(f"**Asset: `{tk}`**")
            c_tk1, c_tk2 = st.columns(2)
            with c_tk1:
                if st.button(f"📈 {tk} Chart", key=f"spot_tc_{tk}", use_container_width=True):
                    st.session_state["tech_ticker_input"] = tk
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page("pages/8_📈_Analisi_Tecnica.py")
            with c_tk2:
                if st.button(f"🏛️ {tk} DCF", key=f"spot_vd_{tk}", use_container_width=True):
                    st.session_state["selected_val_company"] = tk
                    st.session_state["show_spotlight_palette"] = False
                    switch_to_page("pages/5_🏛️_Valutazione_Aziendale.py")

    # ── COLONNA 3: AZIONI DI SISTEMA & TELEMETRIA ───────────────────
    with col_res3:
        st.markdown('<div style="font-size:11.5px; font-weight:700; color:#ff9900; margin-bottom:6px; letter-spacing:0.5px;">⚙️ SISTEMA</div>', unsafe_allow_html=True)
        
        if st.button("🎛️ Control Room", key="spot_to_cr", use_container_width=True):
            st.session_state["show_spotlight_palette"] = False
            switch_to_page("0_Control_Room.py")

        if st.button("📈 Executive Dashboard", key="spot_to_dash", use_container_width=True):
            st.session_state["show_spotlight_palette"] = False
            switch_to_page("pages/1_📈_Dashboard_Generale.py")

        if st.button("♻️ Svuota Cache & Reset Sessione", key="spot_clean_cache_all", use_container_width=True):
            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]
            switch_to_page("0_Control_Room.py")

        if st.button("🗗 2° Monitor", key="spot_popout_2nd", use_container_width=True):
            st.session_state["show_spotlight_palette"] = False
            st.info("Apri una seconda finestra nel tuo browser per il 2° monitor.")
    
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



def metric_card(label: str, value: str, delta: str = None, positive: bool = True, help_text: str = None, is_positive: bool = None):
    if is_positive is not None:
        positive = is_positive
    import re
    import random
    
    unique_id = f"{re.sub(r'[^a-zA-Z0-9]', '_', label).lower()}_{random.randint(1000, 9999)}"
    
    delta_html = ""
    if delta:
        cls = "metric-delta-pos" if positive else "metric-delta-neg"
        arrow = "↑" if positive else "↓"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    
    modal_html = ""
    if help_text:
        help_text = help_text.strip()
        if "<" in help_text and ">" in help_text:
            cleaned = re.sub(r'<!--.*?-->', '', help_text, flags=re.DOTALL)
            cleaned = re.sub(r'>\s+<', '><', cleaned)
            cleaned = re.sub(r'\s*\n\s*', ' ', cleaned)
            safe_help_text = cleaned.strip()
        else:
            safe_help_text = help_text.replace('\n', '<br>')
        
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
    font-size: 13px; 
    color: #ff9900;
    background: rgba(255, 153, 0, 0.1);
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: 8px;
    transition: all 0.2s;
    border: 1px solid transparent;
}}
.info-icon-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.2);
    border-color: rgba(255, 153, 0, 0.5);
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
        label_html = f'<div class="metric-label" style="display:flex; align-items:center;">{label} <label for="modal-toggle-{unique_id}" class="info-icon-{unique_id}" title="Clicca per approfondire">ⓘ</label></div>'
    else:
        label_html = f'<div class="metric-label">{label}</div>'

    st.markdown(f"""{modal_html}
<div class="metric-card">
    {label_html}
    <div class="metric-value">{value}</div>
    {delta_html}
</div>""", unsafe_allow_html=True)

def section(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

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
        return f"{sign}€{abs_v / 1_000_000_000:,.2f}B"
    elif abs_v >= 1_000_000:
        return f"{sign}€{abs_v / 1_000_000:,.2f}M"
    else:
        return f"{sign}€{abs_v:,.2f}"

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
    background: rgba(255, 153, 0, 0.1);
    color: #ff9900;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    margin-bottom: 12px;
}}
.btn-glossary-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.2);
    transform: translateY(-1px);
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

<label for="modal-toggle-{unique_id}" class="btn-glossary-{unique_id}">{button_label}</label>
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


def load_benchmark_returns(ticker: str, df_prices, portfolio_index) -> pd.Series:
    """Carica o genera la serie dei rendimenti giornalieri per un qualsiasi benchmark specificato (SPY, QQQ, ACWI, AGG, GLD, BTC)."""
    import numpy as np
    import pandas as pd
    
    if portfolio_index is None or len(portfolio_index) == 0:
        return pd.Series(dtype=float)
        
    if df_prices is not None and isinstance(df_prices, pd.DataFrame) and not df_prices.empty and "ticker" in df_prices.columns:
        bm = df_prices[df_prices["ticker"] == ticker].copy()
        if not bm.empty:
            bm = bm.set_index("price_date")["close"].sort_index()
            bm_ret = bm.pct_change().fillna(0.0)
            bm_ret.name = ticker
            return bm_ret.reindex(portfolio_index).fillna(0.0)

    # Derivazione deterministica se non presente in DB
    spy_bm = pd.Series(0.0, index=portfolio_index, name=ticker)
    if df_prices is not None and isinstance(df_prices, pd.DataFrame) and not df_prices.empty and "ticker" in df_prices.columns:
        spy_df = df_prices[df_prices["ticker"] == "SPY"].copy()
        if not spy_df.empty:
            spy_s = spy_df.set_index("price_date")["close"].sort_index()
            spy_bm = spy_s.pct_change().fillna(0.0).reindex(portfolio_index).fillna(0.0)

    mult_map = {
        "SPY": 1.0,
        "QQQ": 1.25,
        "ACWI": 0.90,
        "AGG": 0.20,
        "GLD": 0.35,
        "BTC": 2.10,
        "BTC-USD": 2.10
    }
    m_factor = mult_map.get(ticker, 1.0)
    derived = spy_bm * m_factor
    derived.name = ticker
    return derived


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
    
    content = f"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. DEFINIZIONE & PROXY -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏛️ 1. Tasso Privo di Rischio (Risk-Free Rate Rf)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Il rendimento teorico di un investimento a rischio di credito e liquidità nullo su orizzonte a breve termine. In ARGUS è attualmente pari a <b>{rate_pct:.2f}%</b> (Fonte: <i>{source}</i>) per la valuta base <b>{curr}</b>.</div>
  <div style="margin-bottom: 6px;"><b>📐 Proxy Istituzionali di Riferimento:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; font-size: 13px;">
      • <b>EUR:</b> BCE €STR (Euro Short-Term Rate) / Bund 3M (XEON.DE)<br>
      • <b>USD:</b> US 3M Treasury Bill (^IRX) / SOFR<br>
      • <b>GBP:</b> Bank of England SONIA (CSH2.L)<br>
      • <b>CHF:</b> SNB SARON Swiss Overnight Rate
    </div>
  </div>
  <div><b>🎯 A cosa serve:</b> Fornisce la remunerazione base del capitale monetario privo di rischio con cui confrontare ogni rendimento attivo.</div>
</div>

<!-- 2. IMPATTO QUANTITATIVO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">⚙️ 2. Impatto Matematico nei Motori Quantitativi ARGUS</div>
  <div style="margin-bottom: 6px;"><b>⚖️ Sharpe & Sortino Ratio:</b> (Rp &minus; Rf) / &sigma; — Un Rf più elevato aumenta l'hurdle rate richiesto al gestore per giustificare la volatilità.</div>
  <div style="margin-bottom: 6px;"><b>🏅 Alpha di Jensen:</b> &alpha; = Rp &minus; [Rf + &beta; &times; (Rb &minus; Rf)] — Depura l'extra-rendimento sia dal Beta di mercato sia dal rendimento monetario base.</div>
  <div style="margin-bottom: 6px;"><b>⚡ Black-Scholes & Opzioni:</b> Fattore di sconto monetario per il valore attuale dello strike price K.</div>
  <div style="margin-bottom: 6px;"><b>💼 Costo del Capitale (WACC & DCF):</b> Ke = Rf + &beta; &times; ERP — Tasso base di attualizzazione per i flussi di cassa operativi.</div>
  <div><b>🎯 Trade Sizing (Kelly Criterion):</b> f* = (&mu; &minus; Rf) / &sigma;² — Massimizza la crescita geometrica del capitale rispetto alla varianza.</div>
</div>

</div>
"""
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
        audit_summary_html = f"""
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(63,185,80,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #3fb950; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📑 Corporate Actions Applicate a questo Portafoglio</div>
  <div style="font-size: 12.5px; color: #7ee787;">{rows_act}</div>
</div>
"""

    content = f"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. PRINCIPIO FISCALE -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🧬 1. Principio di Invarianza Fiscale (TUIR Art. 67 & IFRS)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Le operazioni straordinarie (Stock Split / Reverse Split) non costituiscono realizzo di plusvalenza o minusvalenza. Il valore fiscale complessivo del lotto di acquisto rimane invariato.</div>
  <div style="margin-bottom: 6px;"><b>📐 Formula di Rettifica Invariante:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>Cost Basis</b> = Q<sub>orig</sub> &times; P<sub>orig</sub> = Q<sub>rett</sub> &times; P<sub>rett</sub>
    </div>
  </div>
  <div><b>🔍 Tipologie:</b><br>
    • <b>Forward Split (R > 1):</b> Il numero di quote aumenta (Q &times; R) e il prezzo di carico medio si riduce (P / R).<br>
    • <b>Reverse Split (R < 1):</b> Il numero di quote si riduce e il prezzo unitario aumenta proporzionalmente.
  </div>
</div>

<!-- 2. RETTIFICA FIFO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔄 2. Perché la Rettifica FIFO in ARGUS è Fondamentale?</div>
  <div style="margin-bottom: 6px;"><b>1. Coerenza con i Prezzi di Mercato:</b> Le serie storiche scaricate da Yahoo Finance sono rettificate (Adjusted Close). Senza rettifica dei lotti di acquisto passati, verrebbero generate perdite o guadagni fittizi.</div>
  <div style="margin-bottom: 6px;"><b>2. Prevenzione Errori di Inventario:</b> Le vendite concluse post-split impiegano quote rettificate evitando disallineamenti di saldo.</div>
  <div><b>3. Calcolo Fiscale Esatto:</b> Plusvalenze e minusvalenze per lo zainetto fiscale vengono determinate con precisione contabile al centesimo.</div>
</div>

{audit_summary_html}

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<div style="background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.3); border-radius: 10px; padding: 12px 16px; margin-bottom: 14px;">
  <div style="color: #38bdf8; font-weight: 700; font-size: 14px; margin-bottom: 4px;">🌐 Ingestion Automatica Multi-Broker ARGUS</div>
  <div>ARGUS supporta l'ingestione istantanea con <b>Auto-Detection del formato</b>, risoluzione automatica degli ISIN bancari in Ticker Yahoo Finance e calcolo fiscale multi-valuta per tutti i principali broker.</div>
</div>

<!-- 1. DEGIRO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🟡 1. DeGiro (Trading & Multi-Valuta)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'App / Web:</b> Nel menu laterale seleziona <b>Attività</b> ➔ <b>Transazioni</b>.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; font-size: 13px;">
      1. Imposta l'intervallo temporale (es. <i>Da Inizio / Tutto</i>).<br>
      2. Clicca sul pulsante <b>Esporta</b> in alto a destra ➔ seleziona <b>CSV</b>.<br>
      3. Carica il file scaricato direttamente in ARGUS senza modifiche.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Normalizza cambi EUR/USD/GBP, commissioni di negoziazione e converte gli ISIN europei in Ticker quotati.</div>
  <div><b>🔍 Formato Riconosciuto:</b> Intestazioni standard DeGiro (<i>Data, Ora, Prodotto, ISIN, Descrizione, Quantità, Prezzo, Valore, Commissioni</i>).</div>
</div>

<!-- 2. DIRECTA SIM -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔵 2. Directa SIM (dLite & Classic)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'App / Web:</b> Entra in <b>dLite</b> o piattaforma <b>Classic</b> ➔ <b>Ordini ed Eseguiti</b> / <b>Estratto Conto Titoli</b>.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(56,189,248,0.08); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #7dd3fc; font-size: 13px;">
      1. Seleziona le operazioni storiche concluse nel periodo desiderato.<br>
      2. Clicca sull'icona di esportazione <b>CSV / Excel</b>.<br>
      3. Se esportato in Excel, salva con nome in formato <b>CSV (delimitato da virgole)</b>.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Gestisce la notazione contabile italiana (COMPRA/VENDE, virgole decimali, dividendi e frazionamenti azionari).</div>
  <div><b>🔍 Formato Riconosciuto:</b> Tracciati tabellari Directa dLite / Libera / Classic con codici ISIN o ticker MTA/US.</div>
</div>

<!-- 3. FINECO BANK -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(248,81,73,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #f85149; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔴 3. Fineco Bank (Reportistica Portafoglio)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'Area Riservata:</b> Accedi a <b>Portafoglio</b> ➔ <b>Reportistica Trading</b> ➔ <b>Ordini Eseguiti / Movimenti</b>.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(248,81,73,0.08); border-left: 3px solid #f85149; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #fca5a5; font-size: 13px;">
      1. Imposta la data di inizio dalla prima transazione a oggi.<br>
      2. Clicca su <b>Esporta in formato CSV / Testo</b>.<br>
      3. Trascina il file nell'area di upload di ARGUS.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Riconosce le causali bancarie Fineco, scorpora le ritenute fiscali e converte gli ISIN di Borsa Italiana ed esteri.</div>
  <div><b>🔍 Formato Riconosciuto:</b> Estratti conto ordini eseguiti Fineco Bank con colonne ISIN, Descrizione Titolo, Operazione, Quantità e Prezzo.</div>
</div>

<!-- 4. INTERACTIVE BROKERS -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,123,114,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff7b72; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🟠 4. Interactive Brokers - IBKR (Activity Statement & Flex Query)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nel Client Portal:</b> Vai su <b>Performance & Reports</b> ➔ <b>Statements</b> (oppure <i>Flex Queries</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(255,123,114,0.08); border-left: 3px solid #ff7b72; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffa198; font-size: 13px;">
      1. Seleziona <b>Activity Statement</b> ➔ periodo <i>Custom Date Range</i>.<br>
      2. Imposta il formato di download su <b>CSV</b>.<br>
      3. In alternativa crea una Flex Query includendo la sezione <i>Trades (Eseguiti)</i>.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Supporta sia i file Activity multi-sezione complessi che i report tabellari Flex Query, estraendo automaticamente i ticker US/EU e le commissioni reali.</div>
  <div><b>🔍 Formato Riconosciuto:</b> Sezione 'Trades' di IBKR Activity Statement e Flex Query CSV.</div>
</div>

<!-- 5. TRADE REPUBLIC -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(63,185,80,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #3fb950; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🟢 5. Trade Republic (Transazioni & PAC)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'App / Web:</b> Vai nella sezione <b>Profilo</b> ➔ <b>Documenti & Attività</b>.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(63,185,80,0.08); border-left: 3px solid #3fb950; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #7ee787; font-size: 13px;">
      1. Esporta l'elenco riassuntivo delle transazioni e dei piani di accumulo (PAC).<br>
      2. Scarica il file <b>CSV</b> delle attività.<br>
      3. Carica il documento in ARGUS.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Mappa automaticamente gli ISIN dei PAC e degli acquisti frazionati in Italiano, Inglese e Tedesco.</div>
  <div><b>🔍 Formato Riconosciuto:</b> CSV Trade Republic con colonne Data, Tipo, Titolo, ISIN, Importo, Quote.</div>
</div>

<!-- 6. SCALABLE CAPITAL -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔷 6. Scalable Capital (Transazioni & Baader Bank)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'Area Clienti:</b> Vai su <b>Profilo / Transazioni</b> (oppure al portale della banca depositaria <i>Baader Bank</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #a5d6ff; font-size: 13px;">
      1. Filtra per l'intervallo temporale completo del conto.<br>
      2. Clicca su <b>Esporta CSV</b>.<br>
      3. Inserisci il file nella Control Room ARGUS.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Elabora gli acquisti ordinari, i piani di risparmio automatizzati ETF e gli accrediti dei dividendi con tassazione estera.</div>
  <div><b>🔍 Formato Riconosciuto:</b> Export CSV Scalable Capital / Baader Bank.</div>
</div>

<!-- 7. ETORO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(46,160,67,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #2ea043; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🟩 7. eToro (Account Statement & Closed Trades)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nel Portafoglio:</b> Vai su <b>Portafoglio</b> ➔ icona orologio <b>Cronologia</b> (<i>History</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(46,160,67,0.08); border-left: 3px solid #2ea043; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #56d364; font-size: 13px;">
      1. Clicca sull'icona delle impostazioni in alto a destra ➔ <b>Estratto conto</b> (<i>Account Statement</i>).<br>
      2. Seleziona l'intervallo temporale (es. <i>Dall'apertura conto</i>).<br>
      3. Clicca su <b>CSV / Excel</b> per avviare il download.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Converte le posizioni chiuse in coppie BUY/SELL con gestione corretta delle commissioni di rollover/overnight e valuta USD.</div>
  <div><b>🔍 Formato Riconosciuto:</b> Fogli 'Closed Positions' e 'Account Activity' dell'Account Statement eToro.</div>
</div>

<!-- 8. REVOLUT TRADING -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(188,140,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #bc8cff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🟪 8. Revolut Trading (Estratto Conto Transazioni)</div>
  <div style="margin-bottom: 6px;"><b>📌 Percorso nell'App Revolut:</b> Sezione <b>Investimenti / Trading</b> ➔ <b>Altro (...)</b> ➔ <b>Estratti conto</b> (<i>Statements</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Esportazione:</b>
    <div style="background: rgba(188,140,255,0.08); border-left: 3px solid #bc8cff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #d2a8ff; font-size: 13px;">
      1. Scegli la voce <b>Estratto conto transazioni</b>.<br>
      2. Imposta l'intervallo temporale completo.<br>
      3. Seleziona il formato <b>CSV / Excel</b>.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Riconosce acquisti e vendite frazionate di azioni/ETF, commissioni di custodia e dividendi netti accreditati.</div>
  <div><b>🔍 Formato Riconosciuto:</b> File CSV di Revolut Trading (Trading Statement).</div>
</div>

<!-- 9. GOOGLE SHEETS LIVE SYNC -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🌐 9. Google Sheets Live Sync (Sincronizzazione Cloud)</div>
  <div style="margin-bottom: 6px;"><b>📌 Modalità:</b> Connessione automatica e sicura tramite Service Account Google.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura di Configurazione:</b>
    <div style="background: rgba(56,189,248,0.08); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #7dd3fc; font-size: 13px;">
      1. Condividi il tuo foglio Google con l'email del Service Account.<br>
      2. Inserisci l'URL o il nome del foglio nella Control Room ARGUS.<br>
      3. I tab <i>Azioni</i> e <i>Cripto</i> vengono sincronizzati e consolidati automaticamente.
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>⚙️ Parser ARGUS:</b> Supporta il monitoraggio in tempo reale, la separazione automatica dei portafogli e l'integrazione nel Total Wealth.</div>
</div>

<!-- 10. CSV STANDARD ARGUS -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(139,148,158,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #8b949e; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📄 10. Template CSV Standard ARGUS (Schema Universale a 9 Colonne)</div>
  <div style="margin-bottom: 6px;"><b>📌 Utilizzo:</b> Ideale per broker non elencati o fogli di calcolo custom.</div>
  <div style="margin-bottom: 6px;"><b>📐 Schema delle Colonne:</b>
    <div style="background: rgba(139,148,158,0.08); border-left: 3px solid #8b949e; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #c9d1d9; font-family: monospace; font-size: 12px;">
      tx_date,ticker,tx_type,quantity,price,currency,fees,asset_class,notes
    </div>
  </div>
  <div><b>🔍 Valori Validi:</b><br>
    • <b>tx_type:</b> BUY, SELL, DIVIDEND, SPLIT, DEPOSIT, WITHDRAWAL.<br>
    • <b>currency:</b> EUR, USD, GBP, CHF, ecc.<br>
    • <b>asset_class:</b> Equity, ETF, Fixed Income, Commodity, Crypto, Cash.
  </div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. GARCH MODELLO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">⚡ 1. Il Modello GARCH(1,1) (Bollerslev 1986)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Cattura i <i>Cluster di Volatilità</i> (Engle, Nobel 2003): periodi ad alta turbolenza tendono a persistere nel tempo.</div>
  <div style="margin-bottom: 6px;"><b>📐 Equazione della Varianza Condizionale:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      &sigma;<sub>t</sub><sup>2</sup> = &omega; + &alpha; &epsilon;<sub>t&minus;1</sub><sup>2</sup> + &beta; &sigma;<sub>t&minus;1</sub><sup>2</sup>
    </div>
  </div>
  <div><b>🔍 Parametri:</b><br>
    • <b>&omega; (Baseline):</b> Varianza di fondo incondizionata.<br>
    • <b>&alpha; (ARCH Shock):</b> Reattività all'ultimo shock di mercato (&epsilon;<sub>t&minus;1</sub>).<br>
    • <b>&beta; (GARCH Memory):</b> Persistenza della volatilità passata (&sigma;<sub>t&minus;1</sub>).
  </div>
</div>

<!-- 2. FHS -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🛡️ 2. Filtered Historical Simulation (FHS — Barone-Adesi, Hull-White)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Il gold standard per il calcolo del VaR e CVaR sotto Basilea III / FRTB. Unisce la reattività del GARCH alla flessibilità empirica non parametrica.</div>
  <div style="margin-bottom: 6px;"><b>📐 Procedura a 3 Fasi:</b>
    <div style="background: rgba(56,189,248,0.08); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #7dd3fc; font-size: 13px;">
      1. <b>De-volatilizzazione:</b> e<sub>t</sub> = (r<sub>t</sub> &minus; &mu;) / &sigma;<sub>t</sub> (preserva code grasse e skewness).<br>
      2. <b>Re-scaling:</b> r<sub>sim</sub> = &mu; + e<sub>t</sub> &times; &sigma;<sub>T+1</sub> (adegua alla volatilità odierna).<br>
      3. <b>Stima VaR/CVaR:</b> Calcolo quantili e Shortfall sulla distribuzione filtrata.
    </div>
  </div>
  <div><b>🎯 Vantaggio:</b> Reagisce istantaneamente ai cambi di regime di mercato senza assumere una distribuzione gaussiana a campana.</div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. LIMITI BS & SMILE -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📐 1. Dai Limiti di Black-Scholes allo Smile di Mercato</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Black-Scholes assume una volatilità costante su tutti gli strike. Nella realtà, le Put Out-of-the-Money incorporano un premio per il rischio ribasso (<i>Crash Phobia</i>) quotando a volatilità implicita (&sigma;<sub>IV</sub>) superiore.</div>
  <div style="margin-bottom: 6px;"><b>📐 Calibrazione dello Skew Quadratico:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      &sigma;(m) = a + b &times; m + c &times; m<sup>2</sup>, &nbsp; con moneyness m = ln(K / S<sub>0</sub>)
    </div>
  </div>
  <div><b>🔍 Parametri:</b><br>
    • <b>a (ATM Vol):</b> Livello base della volatilità At-The-Money.<br>
    • <b>b (Skew Slope):</b> Pendenza asimmetrica negativa (domanda di hedging su ribassi).<br>
    • <b>c (Curvature):</b> Curvatura convessa associata alla curtosi di mercato.
  </div>
</div>

<!-- 2. DELTA HEDGING -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🛡️ 2. Impatto sul Delta-Hedging & Covered Call</div>
  <div style="margin-bottom: 6px;"><b>1. Prezzo Corretto della Copertura:</b> Evita di sottostimare il costo delle Put OTM per proteggere il portafoglio.</div>
  <div><b>2. Dimensionamento dei Contratti:</b> Calcola il Delta effettivo (&Delta;<sub>skew</sub>) garantendo la perfetta neutralità al rischio direzionale.</div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. QUADRO RT -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📈 1. Quadro RT (Sez. II-B): Plusvalenze & Franchigia 2.000€</div>
  <div style="margin-bottom: 6px;"><b>📌 Aliquota:</b> Imposta sostitutiva al <b>26%</b> sulle plusvalenze realizzate da conversione in valuta Fiat (es. BTC ➔ EUR) o acquisto beni/servizi.</div>
  <div style="margin-bottom: 6px;"><b>📐 Franchigia Annuale:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      Se &sum; (Plusvalenze &minus; Minusvalenze) &le; 2.000€ &rArr; Imposta Dovuta = 0€
    </div>
  </div>
  <div><b>🔍 Zainetto Fiscale:</b> Le minusvalenze eccedenti i 2.000€ sono riportabili nei <b>4 anni successivi</b> (esclusivamente compensabili con future plusvalenze cripto).</div>
</div>

<!-- 2. QUADRO RW & IVAFE -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🌐 2. Quadro RW & Imposta sul Valore (IVAFE Cripto 0,20%)</div>
  <div style="margin-bottom: 6px;"><b>📌 Monitoraggio Fiscale:</b> Obbligo dichiarativo con <b>Codice 21</b> per exchange esteri e chiavette hardware (Ledger/Trezor/MetaMask).</div>
  <div><b>📐 Imposta sul Valore (0,20% annuo):</b> Valore al 31/12 &times; 0,002 &times; (Giorni di possesso / 365).</div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. REGRESSIONE FATTORIALE -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏛️ 1. L'Equazione di Regressione Econometrica</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Estende il CAPM spiegando che il rendimento di un portafoglio è guidato da molteplici premi al rischio sistematici indipendenti.</div>
  <div style="margin-bottom: 6px;"><b>📐 Modello Fama-French 5-Factor + Momentum:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      R<sub>p</sub> &minus; R<sub>f</sub> = &alpha; + &beta;<sub>MKT</sub>(R<sub>m</sub> &minus; R<sub>f</sub>) + &beta;<sub>SMB</sub>SMB + &beta;<sub>HML</sub>HML + &beta;<sub>RMW</sub>RMW + &beta;<sub>CMA</sub>CMA + &beta;<sub>MOM</sub>MOM
    </div>
  </div>
  <div><b>🔍 I 6 Fattori:</b><br>
    • <b>MKT-RF:</b> Premio per il rischio azionario di mercato.<br>
    • <b>SMB (Size):</b> Small Caps vs Mega Caps.<br>
    • <b>HML (Value):</b> Titoli Value (alto B/M) vs Growth (basso B/M).<br>
    • <b>RMW (Profitability):</b> Alta redditività operativa vs aziende con margini deboli.<br>
    • <b>CMA (Investment):</b> Politiche di investimento prudenti vs espansione aggressiva.<br>
    • <b>MOM (Momentum):</b> Persistenza del trend di prezzo a 12 mesi.
  </div>
</div>

<!-- 2. ATTRIBUZIONE -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🎯 2. Significatività Statistica & Alpha Puro</div>
  <div style="margin-bottom: 6px;"><b>Alpha (&alpha;):</b> Misura l'abilità di selezione attiva pura del gestore non spiegata dai fattori sistematici.</div>
  <div><b>Test t & p-value:</b> Se |t| &ge; 1.96 (p < 0.05), l'esposizione al fattore è <b>statisticamente significativa al 95%</b>.</div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. FORM 10-K -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📑 1. La Struttura dei Bilanci Annuali SEC Form 10-K</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Documenti contabili e legali ufficiali depositati presso la SEC da tutte le società quotate a Wall Street.</div>
  <div><b>🔍 Sezioni Chiave Estratte:</b><br>
    • <b>Item 1A (Risk Factors):</b> Vulnerabilità operative, geopolitiche, legali e di concentrazione clienti.<br>
    • <b>Item 7 (MD&A):</b> Spiegazione del management su ricavi, margini e liquidità futura.<br>
    • <b>Item 7A (Market Risk):</b> Sensibilità a tassi d'interesse, cambi valutari e materie prime.<br>
    • <b>Item 8 (Financial Footnotes):</b> Note al debito, maturity schedule e contenziosi legali.
  </div>
</div>

<!-- 2. LOCAL RAG -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">⚙️ 2. Architettura Local RAG in ARGUS</div>
  <div style="margin-bottom: 6px;"><b>1. Semantic Chunking:</b> Segmentazione per blocchi logici omogenei con metadati di sezione.</div>
  <div style="margin-bottom: 6px;"><b>2. Vector Indexing BM25/Cosine:</b> Ricerca semantica locale ad altissima velocità e privacy totale.</div>
  <div><b>3. Grounded Synthesis:</b> Risposte ancorate rigorosamente ai passaggi ufficiali del bilancio con citazione del paragrafo.</div>
</div>

</div>
"""
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
    content = """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. OLTP VS OLAP -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">⚡ 1. OLTP (Righe) vs OLAP (DuckDB Colonnare)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> DuckDB è un motore analitico embedded in memoria RAM, ottimizzato per query aggregate complesse e scansioni colonnari sub-millisecondo.</div>
  <div><b>🔍 Vantaggi Architetturali:</b><br>
    • <b>Esecuzione Vettorizzata SIMD:</b> Processa vettori di dati in parallelo sfruttando le istruzioni hardware della CPU (AVX-2).<br>
    • <b>Zero-Copy Data Transfer:</b> Compatibilità nativa con Apache Arrow per trasferire dati senza duplicazione di memoria.
  </div>
</div>

<!-- 2. ANALISI AVANZATA -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📊 2. Cubi Multi-Dimensionali & Storage Parquet</div>
  <div style="margin-bottom: 6px;"><b>Cubi OLAP (`GROUPING SETS`):</b> Calcolo simultaneo dei subtotali su Asset Class &times; Settore &times; Valuta in un'unica scansione.</div>
  <div><b>Compressione Parquet (fino all'85%):</b> Formato colonnare ad alta densità con encoding snappato per archiviazione istantanea.</div>
</div>

</div>
"""
    render_info_modal(
        title="⚡ Motore Analitico DuckDB & Parquet",
        content=content,
        button_label=button_label,
        use_popover=use_popover
    )





def get_argus_eye_svg(size: int = 140, animated: bool = True, accent: str = None) -> str:
    """
    Genera l'Occhio Cibernetico di Argus Panoptes in vettoriale SVG puro a 60 FPS.
    Include reticolo compass radar, anello matrice rischio, iride metallica, pupilla pulsante e fascio laser.
    """
    if not accent:
        theme = st.session_state.get("ui_theme", "Midnight Obsidian")
        accent = "#00f3ff" if theme == "Cyberpunk Neon" else ("#00c853" if theme == "Emerald Wealth" else "#ff9900")
    
    anim_css = (
        f".argus-rot-cw {{ transform-origin: 100px 100px; animation: argusSpinCW 22s linear infinite; }}"
        f".argus-rot-ccw {{ transform-origin: 100px 100px; animation: argusSpinCCW 15s linear infinite; }}"
        f".argus-pulse-core {{ transform-origin: 100px 100px; animation: argusEyePulse 3s ease-in-out infinite; }}"
        f".argus-scan-beam {{ animation: argusScanMove 2.6s ease-in-out infinite; }}"
        f"@keyframes argusSpinCW {{ 100% {{ transform: rotate(360deg); }} }}"
        f"@keyframes argusSpinCCW {{ 100% {{ transform: rotate(-360deg); }} }}"
        f"@keyframes argusEyePulse {{ 0%, 100% {{ transform: scale(1); opacity: 0.88; }} 50% {{ transform: scale(1.08); opacity: 1; }} }}"
        f"@keyframes argusScanMove {{ 0%, 100% {{ transform: translateY(0px); opacity: 0.15; }} 50% {{ transform: translateY(70px); opacity: 0.85; }} }}"
    ) if animated else ""

    svg = (
        f'<svg width="{size}" height="{size}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:auto;filter:drop-shadow(0 0 12px {accent}44);">'
        f'<defs>'
        f'<radialGradient id="argusIris" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0%" stop-color="#ffe082" stop-opacity="0.9"/>'
        f'<stop offset="40%" stop-color="{accent}" stop-opacity="0.6"/>'
        f'<stop offset="85%" stop-color="#b36b00" stop-opacity="0.25"/>'
        f'<stop offset="100%" stop-color="#0d1117" stop-opacity="0.95"/>'
        f'</radialGradient>'
        f'<radialGradient id="argusPupil" cx="45%" cy="45%" r="50%">'
        f'<stop offset="0%" stop-color="#ffffff"/>'
        f'<stop offset="35%" stop-color="{accent}"/>'
        f'<stop offset="80%" stop-color="#0d1117"/>'
        f'</radialGradient>'
        f'<filter id="argusGlow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feGaussianBlur stdDeviation="3" result="blur"/>'
        f'<feComposite in="SourceGraphic" in2="blur" operator="over"/>'
        f'</filter>'
        f'</defs>'
        f'<style>{anim_css}</style>'
        f'<g filter="url(#argusGlow)">'
        f'<circle cx="100" cy="100" r="88" fill="none" stroke="{accent}" stroke-width="1.2" stroke-opacity="0.25" stroke-dasharray="4, 6" class="argus-rot-cw"/>'
        f'<circle cx="100" cy="12" r="3.5" fill="{accent}" class="argus-rot-cw"/>'
        f'<circle cx="188" cy="100" r="3.5" fill="{accent}" class="argus-rot-cw"/>'
        f'<circle cx="100" cy="188" r="3.5" fill="{accent}" class="argus-rot-cw"/>'
        f'<circle cx="12" cy="100" r="3.5" fill="{accent}" class="argus-rot-cw"/>'
        f'<circle cx="100" cy="100" r="68" fill="none" stroke="{accent}" stroke-width="2" stroke-opacity="0.45" stroke-dasharray="16, 8, 4, 8" class="argus-rot-ccw"/>'
        f'<path d="M 32 100 Q 100 48 168 100 Q 100 152 32 100 Z" fill="rgba(22, 27, 34, 0.75)" stroke="{accent}" stroke-width="2" stroke-opacity="0.85"/>'
        f'<circle cx="100" cy="100" r="36" fill="url(#argusIris)" stroke="{accent}" stroke-width="1.5"/>'
        f'<circle cx="100" cy="100" r="18" fill="url(#argusPupil)" class="argus-pulse-core"/>'
        f'<line x1="50" y1="65" x2="150" y2="65" stroke="{accent}" stroke-width="2" stroke-linecap="round" class="argus-scan-beam" opacity="0.75"/>'
        f'<line x1="100" y1="24" x2="100" y2="38" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="100" y1="162" x2="100" y2="176" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="24" y1="100" x2="38" y2="100" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'<line x1="162" y1="100" x2="176" y2="100" stroke="{accent}" stroke-width="1.5" stroke-opacity="0.6"/>'
        f'</g>'
        f'</svg>'
    )
    return svg


def render_splash_screen(force_show: bool = False) -> bool:
    """
    Renderizza la Schermata di Avvio Istituzionale (Splash Screen) con l'Occhio di Argus e il Boot Telemetrico.
    Restituisce True se la splash screen è attiva (bloccando il resto della pagina finché non si accede).
    """
    if "splash_dismissed" not in st.session_state:
        st.session_state.splash_dismissed = False

    if force_show:
        st.session_state.splash_dismissed = False

    if st.session_state.splash_dismissed:
        return False

    theme = st.session_state.get("ui_theme", "Midnight Obsidian")
    accent = "#00f3ff" if theme == "Cyberpunk Neon" else ("#00c853" if theme == "Emerald Wealth" else "#ff9900")
    eye_svg = get_argus_eye_svg(size=140, animated=True, accent=accent)

    hide_sidebar_css = (
        f'<style>'
        f'section[data-testid="stSidebar"], [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none !important; }}'
        f'</style>'
    )
    st.markdown(hide_sidebar_css, unsafe_allow_html=True)

    html_content = (
        f'<div style="max-width:700px;margin:20px auto 30px auto;background:rgba(22,27,34,0.88);border:1px solid rgba(255,153,0,0.35);border-radius:18px;padding:32px 28px;box-shadow:0 16px 48px rgba(0,0,0,0.6), 0 0 30px {accent}22;backdrop-filter:blur(16px);text-align:center;">'
        f'<div style="margin-bottom:16px;">{eye_svg}</div>'
        f'<div style="font-size:32px;font-weight:800;letter-spacing:4px;color:#ffffff;margin-bottom:4px;">A R G U S</div>'
        f'<div style="font-size:11px;font-weight:700;color:{accent};letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">INSTITUTIONAL RISK INTELLIGENCE &amp; VALUATION PLATFORM</div>'
        f'<div style="font-size:12px;color:#8b949e;max-width:520px;margin:0 auto 20px auto;line-height:1.5;">Piattaforma quantitativa multi-asset per il monitoraggio del rischio di portafoglio, analisi econometrica Fama-French, stress testing storico e valutazione fondamentale.</div>'
        f'<div style="background:rgba(13,17,23,0.8);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px 18px;text-align:left;font-family:monospace;font-size:11px;color:#8b949e;margin-bottom:24px;line-height:1.8;">'
        f'<div style="color:#3fb950;">[✓] Dual Data Ingestion Pipeline (Stocks &amp; Crypto) Online</div>'
        f'<div style="color:#3fb950;">[✓] GIPS Standard Calendar Engine (365.25d Solar Span) Active</div>'
        f'<div style="color:#3fb950;">[✓] Multi-Factor Risk Matrix (Carhart, Fama-French, MSCI Barra) Initialized</div>'
        f'<div style="color:#3fb950;">[✓] Ledoit-Wolf Shrinkage &amp; FIFO Accounting Reconciliation Ready</div>'
        f'<div style="color:{accent};font-weight:bold;">[●] ARGUS Terminal v5.14.0 Ready for Operations</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)

    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 ENTRA NEL TERMINALE →", key="btn_dismiss_splash_main", type="primary", use_container_width=True):
            st.session_state.splash_dismissed = True
            st.rerun()

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
        f'<span style="font-size:10px;font-weight:700;color:{accent};background:rgba(255,153,0,0.1);padding:2px 8px;border-radius:12px;">v5.14.0</span>'
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

