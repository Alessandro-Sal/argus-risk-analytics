"""
ARGUS — Risk Analytics & Quantitative Platform
Core Module: Sidebar & Institutional Navigation Rail v6.3.0
Argus Institutional Risk & Wealth Analytics Platform
Provides top-level execution mode configuration, zero-recalc session persistence,
and direct hierarchical navigation with exact sub-tab binding.
"""

import streamlit as st
import os
import socket
import sys
from core.workspace_manager import ensure_session_restored


# Moduli Risk Analytics (11 Pagine Istituzionali)
NAV_MODULES_RISK = [
    {
        "title": "Control Room & Setup",
        "icon": "🎛️",
        "page_file": "0_Control_Room.py",
        "key": "0_Control_Room",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Dashboard Generale",
        "icon": "📈",
        "page_file": "pages/1_📈_Dashboard_Generale.py",
        "key": "1_Dashboard_Generale",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Live Terminal & Desk",
        "icon": "🖥️",
        "page_file": "pages/2_🖥️_Live_Terminal.py",
        "key": "2_Live_Terminal",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Analisi del Rischio",
        "icon": "🔴",
        "page_file": "pages/3_🔴_Analisi_Rischio.py",
        "key": "3_Analisi_Rischio",
        "has_subtabs": True,
        "tab_key": "risk_active_tab",
        "subtabs": [
            {"label": "📊 Profilo di Rischio", "target": "📊 Profilo del Rischio & Fama-French"},
            {"label": "📉 VaR & Backtesting", "target": "📉 VaR, CVaR & Backtesting Kupiec"},
            {"label": "🔗 Correlazioni & ATR", "target": "🔗 Correlazioni, Liquidità & ATR Chandelier"},
            {"label": "🕵️‍♂️ Rilevatore Anomalie", "target": "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)"}
        ]
    },
    {
        "title": "Modelli Quantitativi",
        "icon": "🔬",
        "page_file": "pages/4_🔬_Modelli_Quantitativi.py",
        "key": "4_Modelli_Quantitativi",
        "has_subtabs": True,
        "tab_key": "quant_active_tab",
        "subtabs": [
            {"label": "📊 Frontiera Markowitz", "target": "📊 Markowitz & Rebalancing"},
            {"label": "🤖 AI Reinforcement", "target": "🤖 AI Reinforcement Learning"},
            {"label": "🧬 Copula & Kelly", "target": "🧬 Tail Copula & Kelly"},
            {"label": "🎲 Monte Carlo & Merton", "target": "🎲 Monte Carlo & Merton"},
            {"label": "🛡️ Hedging & Opzioni", "target": "🛡️ Hedging & Opzioni"},
            {"label": "🎯 Performance & Fattori", "target": "🎯 Attribuzione & Fattori"},
            {"label": "🏛️ Fixed Income & Curve", "target": "🏛️ Fixed Income & Z-Spread"}
        ]
    },
    {
        "title": "Posizioni & Fisco",
        "icon": "📋",
        "page_file": "pages/5_📋_Posizioni_e_Dettagli.py",
        "key": "5_Posizioni_e_Dettagli",
        "has_subtabs": True,
        "tab_key": "positions_active_tab",
        "subtabs": [
            {"label": "📋 Posizioni Attive", "target": "📋 Posizioni Attive & Costi FIFO"},
            {"label": "🪦 Posizioni Chiuse", "target": "🪦 Posizioni Chiuse & Graveyard"},
            {"label": "📅 Flusso Dividendi", "target": "📅 Proiezione Dividendi"},
            {"label": "💰 Efficienza Fiscale", "target": "💰 Ottimizzazione Fiscale (TUIR Art. 67)"},
            {"label": "⚡ Liquidità & Routing", "target": "⚡ Liquidità & Smart Order Router"}
        ]
    },
    {
        "title": "Valutazione Aziendale",
        "icon": "🏛️",
        "page_file": "pages/6_🏛️_Valutazione_Aziendale.py",
        "key": "6_Valutazione_Aziendale",
        "has_subtabs": True,
        "tab_key": "val_segmented_tab",
        "subtabs": [
            {"label": "🏛️ Fair Value & Consensus", "target": "🏛️ Fair Value & Consensus Analisti"},
            {"label": "💼 Private Equity", "target": "💼 Private Equity & Waterfall"},
            {"label": "📊 Bilanci & Solvibilità", "target": "📊 Bilanci & Solvibilità (Altman & DuPont)"},
            {"label": "🧮 Modello DCF", "target": "🧮 Valutazione Intrinseca DCF Monte Carlo"}
        ]
    },
    {
        "title": "Stress Testing",
        "icon": "🌪️",
        "page_file": "pages/7_🌪️_Stress_Testing.py",
        "key": "7_Stress_Testing",
        "has_subtabs": True,
        "tab_key": "stress_active_tab",
        "subtabs": [
            {"label": "⚡ Scenari MSCI Barra", "target": "⚡ Matrice Comparativa MSCI Barra"},
            {"label": "🏛️ Crisi Storiche", "target": "🏛️ Analisi Scenari Storici Dettagliata"},
            {"label": "🛠️ Simulatore What-if", "target": "🛠️ Simulatore What-if Custom"}
        ]
    },
    {
        "title": "Analisi Temporale",
        "icon": "📊",
        "page_file": "pages/8_📊_Analisi_Temporale.py",
        "key": "8_Analisi_Temporale",
        "has_subtabs": True,
        "tab_key": "time_active_tab",
        "subtabs": [
            {"label": "📈 Curva & Underwater", "target": "📈 Curva Cumulata & Drawdown Underwater"},
            {"label": "🗓️ Matrice Mensile", "target": "🗓️ Matrice Rendimenti Mensili & Annuali"},
            {"label": "🌊 Rolling Metrics", "target": "🌊 Rischio Mobile Dinamico (Rolling Metrics)"},
            {"label": "📊 Stagionalità", "target": "📊 Stagionalità & Pattern Calendari"},
            {"label": "⚖️ Confronto Side-by-Side", "target": "⚖️ Confronto Side-by-Side & Snapshot DB"}
        ]
    },
    {
        "title": "Analisi Tecnica",
        "icon": "📈",
        "page_file": "pages/9_📈_Analisi_Tecnica.py",
        "key": "9_Analisi_Tecnica",
        "has_subtabs": True,
        "tab_key": "tech_active_subtab",
        "subtabs": [
            {"label": "📊 Cockpit Grafico", "target": "📊 Cockpit & Candlestick"},
            {"label": "🧱 Volume Profile", "target": "🧱 Volume Profile Dettaglio"},
            {"label": "🚦 Confluence Score", "target": "🚦 Confluence Score"},
            {"label": "⏳ Trend Multi-Timeframe", "target": "⏳ Trend Multi-Timeframe"},
            {"label": "⚡ Dati Real-Time", "target": "⚡ Real-Time Streaming"}
        ]
    },
    {
        "title": "Screener Opportunità",
        "icon": "🔍",
        "page_file": "pages/10_🔍_Screener_Opportunita.py",
        "key": "10_Screener_Opportunita",
        "has_subtabs": True,
        "tab_key": "screener_segmented_subtab",
        "subtabs": [
            {"label": "🔍 Screener & Filtri", "target": "🔍 Screener Multi-Fattoriale & Archetipi"},
            {"label": "🧪 Pre-Trade Simulator", "target": "🧪 Pre-Trade Portfolio Impact Simulator"},
            {"label": "📊 Radar Comparativo", "target": "📊 Radar Comparativo Multi-Titolo"},
            {"label": "💾 Watchlist & Segnali", "target": "💾 Watchlist & Segnali Operativi"}
        ]
    },
    {
        "title": "BQuant & Launchpad",
        "icon": "💻",
        "page_file": "pages/11_💻_BQuant_e_Launchpad.py",
        "key": "11_BQuant_e_Launchpad",
        "has_subtabs": True,
        "tab_key": "bquant_active_tab",
        "subtabs": [
            {"label": "🐍 Python Sandbox", "target": "🐍 ARGUS BQuant Python Sandbox"},
            {"label": "🎛️ Launchpad Workspace", "target": "🎛️ Launchpad & Workspace Customizer"},
            {"label": "📊 Excel Connector", "target": "📊 Excel Live Connector & RTD"}
        ]
    }
]

# Moduli Wealth Management (Control Room & Ingestion, Patrimonio, Cash Flow, Orologi, Pensione)
NAV_MODULES_WEALTH = [
    {
        "title": "Control Room & Ingestion",
        "icon": "🎛️",
        "page_file": "pages/12_🎛️_Wealth_Control_Room.py",
        "key": "12_Wealth_Control_Room",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Patrimonio & Net Worth",
        "icon": "🏛️",
        "page_file": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
        "key": "13_Patrimonio_e_NetWorth",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Cash Flow & Spese",
        "icon": "💳",
        "page_file": "pages/14_💳_Cash_Flow_e_Spese.py",
        "key": "14_Cash_Flow_e_Spese",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Asset Illiquidi & Orologi",
        "icon": "⌚",
        "page_file": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py",
        "key": "15_Asset_Illiquidi_e_Orologi",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Previdenza & Pensione",
        "icon": "🛡️",
        "page_file": "pages/16_🛡️_Previdenza_e_Pension_Planning.py",
        "key": "16_Previdenza_e_Pension_Planning",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Indipendenza & FIRE",
        "icon": "🔥",
        "page_file": "pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py",
        "key": "17_Indipendenza_Finanziaria_e_FIRE",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Fiscalità & Quadro RW",
        "icon": "📑",
        "page_file": "pages/18_📑_Fiscalita_e_Quadro_RW.py",
        "key": "18_Fiscalita_e_Quadro_RW",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Immobili & Mutui",
        "icon": "🏡",
        "page_file": "pages/19_🏡_Immobili_e_Mutui.py",
        "key": "19_Immobili_e_Mutui",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "Pianificazione Successoria",
        "icon": "⚖️",
        "page_file": "pages/20_⚖️_Pianificazione_Successoria.py",
        "key": "20_Pianificazione_Successoria",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    },
    {
        "title": "AI Copilot & Advisor",
        "icon": "🤖",
        "page_file": "pages/21_🤖_AI_Copilot_e_Advisor.py",
        "key": "21_AI_Copilot_e_Advisor",
        "has_subtabs": False,
        "tab_key": None,
        "subtabs": []
    }
]



NAV_MODULES = NAV_MODULES_RISK




def get_current_page_name() -> str:
    """Rileva con precisione il file della pagina Streamlit attualmente in esecuzione."""
    try:
        import inspect
        for frame in inspect.stack():
            fname = frame.filename.replace("\\", "/")
            if "pages/" in fname or "0_Control_Room.py" in fname:
                return os.path.basename(fname)
    except Exception:
        pass
    return os.path.basename(sys.argv[0]) if sys.argv else ""


def switch_to_page(target_page_file: str):
    """
    Esegue la navigazione fluida e istantanea senza errori o flash transitori:
    - Se siamo già sulla pagina di destinazione, esegue st.rerun() per riflettere il tab aggiornato.
    - Se siamo su un'altra pagina, calcola la rotta canonica esatta ed esegue st.switch_page() direttamente.
    """
    cur_page = get_current_page_name()
    target_clean = os.path.basename(target_page_file)
    
    # Se siamo già sulla stessa pagina, basta il rerun
    if target_clean == cur_page or (("0_Control_Room" in target_clean) and ("0_Control_Room" in cur_page)):
        st.rerun()
        return

    # Percorso canonico risolto da workspace_manager
    from core.workspace_manager import resolve_page_path
    resolved = resolve_page_path(target_page_file)
    
    try:
        st.switch_page(resolved)
        return
    except Exception:
        pass

    # Fallback deterministico secondario
    fallback = "0_Control_Room.py" if "0_Control_Room" in target_clean else f"pages/{target_clean}"
    if fallback != resolved:
        try:
            st.switch_page(fallback)
            return
        except Exception:
            pass

    st.rerun()


def _detect_default_port(host, default_port=3306):
    if "STREAMLIT_DB_PORT" in os.environ:
        try:
            return int(os.environ["STREAMLIT_DB_PORT"])
        except ValueError:
            pass
    if host in ["localhost", "127.0.0.1"]:
        for p in [3306, 3307]:
            try:
                with socket.create_connection((host, p), timeout=0.2):
                    return p
            except OSError:
                pass
    return default_port


def render_sidebar():
    """Renderizza la Sidebar Istituzionale v6.3.0 con Modalità Esecuzione in alto e Navigation Rail ad albero."""
    ensure_session_restored()

    current_page = get_current_page_name()

    with st.sidebar:
        # Zero Dead-Space Top Padding Override with Preserved Toggle Buttons
        st.markdown("""
        <style>
            header[data-testid="stHeader"],
            [data-testid="stHeader"] {
                background: transparent !important;
                background-color: transparent !important;
                color: #ffffff !important;
                z-index: 99 !important;
            }

            /* Comprehensive Removal of Streamlit Deploy Button & Top Decoration ONLY */
            [data-testid="stDecoration"],
            .stDeployButton,
            [data-testid="stDeployButton"],
            .stAppDeployButton,
            button[title="Deploy"],
            div:has(> .stDeployButton) {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                height: 0px !important;
                width: 0px !important;
                pointer-events: none !important;
            }

            /* Ensure Streamlit Toolbar is transparent and allows collapsedControl to show */
            header[data-testid="stHeader"],
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            div[data-testid="stToolbar"] {
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
            }

            /* Always keep Collapsed Control (Open Sidebar Button) Visible & Clickable */
            [data-testid="collapsedControl"],
            button[data-testid="stSidebarCollapsedControl"],
            div[data-testid="collapsedControl"],
            [data-testid="stHeader"] [data-testid="collapsedControl"] {
                display: flex !important;
                visibility: visible !important;
                opacity: 1 !important;
                cursor: pointer !important;
                pointer-events: auto !important;
                z-index: 999999 !important;
            }
            [data-testid="collapsedControl"] button,
            button[data-testid="stSidebarCollapsedControl"] {
                display: inline-flex !important;
                visibility: visible !important;
                color: #ff9900 !important;
                background: rgba(22, 27, 34, 0.95) !important;
                border: 1px solid rgba(255, 153, 0, 0.4) !important;
                border-radius: 8px !important;
                padding: 4px 8px !important;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4) !important;
            }
            [data-testid="collapsedControl"] button:hover {
                border-color: #ff9900 !important;
                background: rgba(33, 38, 45, 1) !important;
            }

            /* Hide Streamlit Raw Page Nav */
            [data-testid="stSidebarNav"] {
                display: none !important;
                height: 0px !important;
                max-height: 0px !important;
                padding: 0px !important;
                margin: 0px !important;
                visibility: hidden !important;
                overflow: hidden !important;
            }

            /* Compact Sidebar Header with Close (<) Button */
            div[data-testid="stSidebarHeader"],
            [data-testid="stSidebarHeader"] {
                min-height: 32px !important;
                padding: 4px 8px 0px 8px !important;
                margin: 0px !important;
                display: flex !important;
                justify-content: flex-end !important;
                align-items: center !important;
                background: transparent !important;
                visibility: visible !important;
            }

            /* Sidebar Close Button */
            [data-testid="stSidebarCollapseButton"],
            button[data-testid="stSidebarCollapseButton"],
            div[data-testid="stSidebarHeader"] button {
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
            }
            [data-testid="stSidebarCollapseButton"]:hover,
            button[data-testid="stSidebarCollapseButton"]:hover,
            div[data-testid="stSidebarHeader"] button:hover {
                color: #ffffff !important;
                background: rgba(255, 255, 255, 0.12) !important;
            }

            section[data-testid="stSidebar"],
            [data-testid="stSidebar"] {
                padding-top: 0px !important;
                margin-top: 0px !important;
            }

            section[data-testid="stSidebar"] > div:first-child,
            [data-testid="stSidebarContent"],
            [data-testid="stSidebarUserContent"],
            section[data-testid="stSidebar"] .stSidebarContent,
            section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
                padding-top: 0.25rem !important;
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                margin-top: 0px !important;
            }

            section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]:first-child,
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
                padding-top: 0px !important;
                margin-top: 0px !important;
                gap: 6px !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"]:first-child {
                padding-top: 0px !important;
                margin-top: 0px !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # Rilevamento portale attivo (Wealth vs Risk)
        cur_page_name = get_current_page_name()
        in_wealth_page = any(w in cur_page_name for w in ["12_", "13_", "14_", "15_", "16_", "17_", "18_", "19_", "20_", "21_"])
        if "argus_portal_mode" not in st.session_state:
            st.session_state.argus_portal_mode = "🏛️ Wealth Management" if in_wealth_page else "📊 Risk Analytics"
        elif in_wealth_page and st.session_state.argus_portal_mode != "🏛️ Wealth Management":
            st.session_state.argus_portal_mode = "🏛️ Wealth Management"
        elif not in_wealth_page and any(w in cur_page_name for w in ["0_", "1_", "2_", "3_", "4_", "5_", "6_", "7_", "8_", "9_", "10_", "11_"]) and st.session_state.argus_portal_mode != "📊 Risk Analytics":
            st.session_state.argus_portal_mode = "📊 Risk Analytics"

        is_wealth_mode = (st.session_state.argus_portal_mode == "🏛️ Wealth Management") or in_wealth_page

        # Header del Brand ARGUS con Logo Vettoriale Dinamico (Stesso Occhio della Control Room)
        theme = st.session_state.get("ui_theme", "Midnight Obsidian")
        if is_wealth_mode:
            accent = "#10b981"  # Smeraldo Wealth identico alla Wealth Control Room
            brand_title = "ARGUS WEALTH"
            brand_sub = "WEALTH & PERSONAL FINANCE"
        else:
            accent = "#00f3ff" if theme == "Cyberpunk Neon" else ("#00c853" if theme == "Emerald Wealth" else "#ff9900")
            brand_title = "ARGUS"
            brand_sub = "INSTITUTIONAL RISK INTELLIGENCE"

        from core.ui_utils import get_argus_eye_svg
        eye_sidebar_svg = get_argus_eye_svg(size=32, animated=True, accent=accent, unique_id=f"sb_brand_eye_{'wealth' if is_wealth_mode else 'risk'}")
        
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap: 10px; margin-bottom: 8px; padding: 2px 0;">
            <div style="flex-shrink: 0; display: flex; align-items: center;">{eye_sidebar_svg}</div>
            <div>
                <div style="font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.8px; line-height: 1.1;">{brand_title}</div>
                <div style="font-size: 9px; font-weight: 700; color: {accent}; letter-spacing: 0.5px; text-transform: uppercase;">{brand_sub}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── 1. MODALITÀ DI ESECUZIONE & ENGINE PARAMETERS (IN ALTO) ─────
        if "offline_mode" not in st.session_state: st.session_state.offline_mode = False
        if "db_host" not in st.session_state: st.session_state.db_host = os.getenv("STREAMLIT_DB_HOST", "localhost")
        if "db_port" not in st.session_state: st.session_state.db_port = _detect_default_port(st.session_state.db_host, 3306)
        if "db_user" not in st.session_state: st.session_state.db_user = os.getenv("STREAMLIT_DB_USER", "root")
        if "db_pass" not in st.session_state: st.session_state.db_pass = os.getenv("STREAMLIT_DB_PASS", "root")
        if "db_name" not in st.session_state: st.session_state.db_name = os.getenv("STREAMLIT_DB_NAME", "wealth")
        if "portfolio_name" not in st.session_state: st.session_state.portfolio_name = "Master Wealth"
        if "run_name" not in st.session_state: st.session_state.run_name = ""
        if "benchmark" not in st.session_state: st.session_state.benchmark = "SPY"
        if "base_currency" not in st.session_state: st.session_state.base_currency = "EUR"
        if "ui_theme" not in st.session_state: st.session_state.ui_theme = "Midnight Obsidian"

        # Wealth Specific Settings Defaults
        if "wealth_budget_preset" not in st.session_state: st.session_state.wealth_budget_preset = "50/30/20 Standard"
        if "wealth_budget_needs_pct" not in st.session_state: st.session_state.wealth_budget_needs_pct = 50.0
        if "wealth_budget_wants_pct" not in st.session_state: st.session_state.wealth_budget_wants_pct = 30.0
        if "wealth_budget_savings_pct" not in st.session_state: st.session_state.wealth_budget_savings_pct = 20.0
        if "wealth_fire_swr" not in st.session_state: st.session_state.wealth_fire_swr = 4.0
        if "wealth_target_retirement_age" not in st.session_state: st.session_state.wealth_target_retirement_age = 67
        if "wealth_tax_regime" not in st.session_state: st.session_state.wealth_tax_regime = "Ordinario (26%)"
        if "wealth_pension_deduction_limit" not in st.session_state: st.session_state.wealth_pension_deduction_limit = 5164.57

        # Sincronizzazione reattiva immediata prima del rendering del badge
        if "sb_offline_toggle" in st.session_state:
            st.session_state.offline_mode = st.session_state.sb_offline_toggle

        if "sb_db_host" in st.session_state:
            st.session_state.db_host = st.session_state.sb_db_host

        if "sb_db_port" in st.session_state:
            st.session_state.db_port = int(st.session_state.sb_db_port)

        if "sb_db_user" in st.session_state:
            st.session_state.db_user = st.session_state.sb_db_user

        if "sb_db_pass" in st.session_state:
            st.session_state.db_pass = st.session_state.sb_db_pass

        if "sb_db_select" in st.session_state:
            if st.session_state.sb_db_select != "Custom...":
                st.session_state.db_name = st.session_state.sb_db_select
            elif "sb_custom_db" in st.session_state and st.session_state.sb_custom_db:
                st.session_state.db_name = st.session_state.sb_custom_db

        if "sb_bench_select" in st.session_state:
            if st.session_state.sb_bench_select != "Custom...":
                st.session_state.benchmark = st.session_state.sb_bench_select
            elif "sb_custom_bench" in st.session_state and st.session_state.sb_custom_bench:
                st.session_state.benchmark = st.session_state.sb_custom_bench

        if "sb_base_currency" in st.session_state:
            st.session_state.base_currency = st.session_state.sb_base_currency

        if "sb_port_name" in st.session_state:
            st.session_state.portfolio_name = st.session_state.sb_port_name

        if "sb_wb_needs" in st.session_state:
            st.session_state.wealth_budget_needs_pct = float(st.session_state.sb_wb_needs)
        if "sb_wb_wants" in st.session_state:
            st.session_state.wealth_budget_wants_pct = float(st.session_state.sb_wb_wants)
        if "sb_wb_savings" in st.session_state:
            st.session_state.wealth_budget_savings_pct = float(st.session_state.sb_wb_savings)
        if "sb_wealth_swr_input" in st.session_state:
            st.session_state.wealth_fire_swr = float(st.session_state.sb_wealth_swr_input)
        if "sb_wealth_age_input" in st.session_state:
            st.session_state.wealth_target_retirement_age = int(st.session_state.sb_wealth_age_input)
        if "sb_wealth_tax_regime" in st.session_state:
            st.session_state.wealth_tax_regime = st.session_state.sb_wealth_tax_regime

        from core.yield_curve import get_active_risk_free_rate
        if "rf_mode" not in st.session_state: st.session_state.rf_mode = "Auto (Live Market)"
        if "custom_rf_rate_pct" not in st.session_state: st.session_state.custom_rf_rate_pct = 2.75

        if "sb_rf_mode" in st.session_state:
            st.session_state.rf_mode = st.session_state.sb_rf_mode
        if "sb_custom_rf" in st.session_state:
            st.session_state.custom_rf_rate_pct = float(st.session_state.sb_custom_rf)

        custom_rf_dec = (st.session_state.custom_rf_rate_pct / 100.0) if st.session_state.rf_mode != "Auto (Live Market)" else None
        active_rf_info = get_active_risk_free_rate(currency=st.session_state.base_currency, custom_override=custom_rf_dec)
        st.session_state.active_rf_rate = active_rf_info["rate"]
        st.session_state.active_rf_info = active_rf_info

        from core.ui_utils import get_display_portfolio_name
        port_label, has_port = get_display_portfolio_name()
        port_text_style = "color:#ffffff; font-weight:700;" if has_port else "color:#e3b341; font-style:italic; font-weight:600;"
        active_port_label = port_label if len(port_label) <= 26 else f"{port_label[:24]}..."

        if is_wealth_mode:
            w_needs = int(st.session_state.wealth_budget_needs_pct)
            w_wants = int(st.session_state.wealth_budget_wants_pct)
            w_savings = int(st.session_state.wealth_budget_savings_pct)
            w_rule_label = f"{w_needs}/{w_wants}/{w_savings}"
            
            st.markdown(f"""
            <div style="background:rgba(16, 185, 129, 0.10); border:1px solid rgba(16, 185, 129, 0.35); border-radius:10px; padding: 10px 12px; margin-bottom: 8px; backdrop-filter: blur(10px);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:10px; font-weight:700; color:#8b949e; letter-spacing:0.6px; text-transform:uppercase;">Portale Attivo</span>
                    <span style="font-size:10px; font-weight:800; color:#34d399; background:rgba(16, 185, 129, 0.20); padding: 2px 7px; border-radius:12px; letter-spacing:0.5px;">
                        🏛️ WEALTH
                    </span>
                </div>
                <div style="font-size:11.5px; color:#ffffff; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom: 4px;">
                    🏛️ Wealth &amp; Personal Finance
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10.5px; color:#8b949e; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 5px;">
                    <span>🗄️ <b style="color:#c9d1d9;">{st.session_state.db_name}</b></span>
                    <span>💱 <b style="color:#c9d1d9;">{st.session_state.base_currency}</b> &bull; 🏷️ <b style="color:#34d399;">{w_rule_label}</b></span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#8b949e; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 4px; margin-top: 4px;">
                    <span>🔥 SWR <b style="color:#f59e0b;">{st.session_state.wealth_fire_swr:.1f}%</b></span>
                    <span style="color:#8b949e; font-size:9.5px;">🎯 Pensione: <b style="color:#38bdf8;">{st.session_state.wealth_target_retirement_age}a</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            is_offline = st.session_state.offline_mode
            status_bg = "rgba(255, 153, 0, 0.08)" if is_offline else "rgba(35, 134, 54, 0.10)"
            status_border = "rgba(255, 153, 0, 0.35)" if is_offline else "rgba(46, 160, 67, 0.35)"
            status_badge_bg = "rgba(255, 153, 0, 0.15)" if is_offline else "rgba(46, 160, 67, 0.20)"
            status_badge_color = "#ff9900" if is_offline else "#3fb950"
            status_text = "OFFLINE" if is_offline else "LIVE DB"
            status_icon = "🟡" if is_offline else "🟢"
            active_db_label = "In-Memory" if is_offline else f"{st.session_state.db_name}"

            st.markdown(f"""
            <div style="background:{status_bg}; border:1px solid {status_border}; border-radius:10px; padding: 10px 12px; margin-bottom: 8px; backdrop-filter: blur(10px);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:10px; font-weight:700; color:#8b949e; letter-spacing:0.6px; text-transform:uppercase;">Stato Engine</span>
                    <span style="font-size:10px; font-weight:800; color:{status_badge_color}; background:{status_badge_bg}; padding: 2px 7px; border-radius:12px; letter-spacing:0.5px;">
                        {status_icon} {status_text}
                    </span>
                </div>
                <div style="font-size:11.5px; {port_text_style} white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom: 4px;">
                    💼 {active_port_label}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10.5px; color:#8b949e; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 5px;">
                    <span>🗄️ <b style="color:#c9d1d9;">{active_db_label}</b></span>
                    <span>💱 <b style="color:#c9d1d9;">{st.session_state.base_currency}</b> &bull; 🎯 <b style="color:#c9d1d9;">{st.session_state.benchmark}</b></span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#8b949e; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 4px; margin-top: 4px;">
                    <span>🏛️ Risk-Free <b style="color:#ff9900;">{active_rf_info['rate_pct']:.2f}%</b></span>
                    <span style="color:#8b949e; font-size:9.5px;">{active_rf_info['currency']} ({'Live' if active_rf_info.get('is_live') else 'BCE/Fed'})</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-header" style="margin-top: 10px; margin-bottom: 4px; font-size: 10px; font-weight: 800; color: #8b949e; text-transform: uppercase; letter-spacing: 0.8px;">CAMBIA AMBIENTE</div>', unsafe_allow_html=True)

        # Switch rapido tra i due moduli
        if is_wealth_mode:
            if st.button("📊 Passa a Risk Analytics", key="sb_btn_switch_to_risk", use_container_width=True):
                st.session_state.argus_portal_mode = "📊 Risk Analytics"
                switch_to_page("0_Control_Room.py")
        else:
            if st.button("🏛️ Passa a Wealth Management", key="sb_btn_switch_to_wealth", use_container_width=True):
                st.session_state.argus_portal_mode = "🏛️ Wealth Management"
                switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")

        active_nav_modules = NAV_MODULES_WEALTH if is_wealth_mode else NAV_MODULES_RISK

        st.markdown('<div class="sidebar-section-header" style="margin-top: 10px; margin-bottom: 8px; font-size: 10px; font-weight: 800; color: #8b949e; text-transform: uppercase; letter-spacing: 0.8px;">NAVIGAZIONE WORKSPACE</div>', unsafe_allow_html=True)


        def _is_mod_active(mod_dict: dict, cur_page_str: str) -> bool:
            import re
            cur_c = re.sub(r'[^a-zA-Z0-9]', '', os.path.basename(cur_page_str)).lower()
            mod_c = re.sub(r'[^a-zA-Z0-9]', '', os.path.basename(mod_dict["page_file"])).lower()
            key_c = re.sub(r'[^a-zA-Z0-9]', '', mod_dict.get("key", "")).lower()

            if "0controlroom" in mod_c or "0controlroom" in key_c:
                return ("0controlroom" in cur_c) or ("pages" not in cur_page_str.lower() and (cur_c == "" or "controlroom" in cur_c or "app" in cur_c))
            
            if mod_c and cur_c:
                if mod_c == cur_c:
                    return True
                mod_num = "".join(filter(str.isdigit, mod_c[:3]))
                cur_num = "".join(filter(str.isdigit, cur_c[:3]))
                if mod_num and cur_num and mod_num == cur_num:
                    return True
                if key_c and key_c in cur_c:
                    return True
                if mod_c in cur_c or cur_c in mod_c:
                    return True
            return False

        # ── 1.1 SINCRONIZZAZIONE BIDIREZIONALE SUBTABS ───────────────
        for mod_item in active_nav_modules:
            if mod_item.get("has_subtabs") and mod_item.get("tab_key"):
                tk = mod_item["tab_key"]
                sb_k = f"{tk}_selectbox"
                tgt_k = f"target_subtab_{tk}"
                if tgt_k in st.session_state and st.session_state[tgt_k]:
                    st.session_state[tk] = st.session_state[tgt_k]
                    st.session_state[sb_k] = st.session_state[tgt_k]
                elif sb_k in st.session_state and st.session_state[sb_k]:
                    st.session_state[tk] = st.session_state[sb_k]
                elif tk in st.session_state and st.session_state[tk]:
                    st.session_state[sb_k] = st.session_state[tk]

        # ── 2. RENDERING MODULI NAVIGAZIONE ─────────────────────────────
        for mod in active_nav_modules:
            is_active = _is_mod_active(mod, current_page)


            # Se il modulo non ha sotto-schede (Control Room e Dashboard), renderizza un pulsante diretto a 1 riga
            if not mod["has_subtabs"]:
                btn_prefix = "● " if is_active else "  "
                btn_label = f"{btn_prefix}{mod['icon']} {mod['title']}"
                btn_type = "primary" if is_active else "secondary"
                if st.button(
                    btn_label, 
                    key=f"nav_direct_{mod['key']}", 
                    use_container_width=True,
                    type=btn_type
                ):
                    switch_to_page(mod["page_file"])
            else:
                # Moduli con schede interne: expander compatto aperto solo se la pagina è attiva
                active_icon_prefix = "● " if is_active else ""
                expander_label = f"{active_icon_prefix}{mod['icon']}  {mod['title']}"
                with st.expander(expander_label, expanded=is_active):
                    current_active_target = st.session_state.get(mod["tab_key"]) if mod["tab_key"] else None

                    for idx, sub in enumerate(mod["subtabs"]):
                        sub_btn_key = f"nav_sub_{mod['key']}_{sub['label']}"
                        is_sub_active = is_active and (current_active_target == sub["target"] or (not current_active_target and idx == 0))
                        prefix = "▶ " if is_sub_active else "   "
                        
                        if st.button(
                            f"{prefix}{sub['label']}", 
                            key=sub_btn_key, 
                            use_container_width=True,
                            type="primary" if is_sub_active else "secondary"
                        ):
                            if mod["tab_key"] and sub["target"]:
                                st.session_state[mod["tab_key"]] = sub["target"]
                                st.session_state[f"target_subtab_{mod['tab_key']}"] = sub["target"]
                                st.session_state[f"{mod['tab_key']}_selectbox"] = sub["target"]
                                st.session_state["global_target_subtab"] = sub["target"]
                            switch_to_page(mod["page_file"])

        st.divider()

        # ── 3. PARAMETRI ENGINE & DB (CONFIGURAZIONE DINAMICA) ────────
        with st.expander("⚙️ Impostazioni", expanded=False):
            st.toggle("Modalità Offline (Senza DB)", value=st.session_state.offline_mode, key="sb_offline_toggle")

            if not st.session_state.offline_mode:
                hdr_color = "#34d399" if is_wealth_mode else "#ff9900"
                st.markdown(f'<div style="font-size:10px; font-weight:700; color:{hdr_color}; letter-spacing:0.5px; text-transform:uppercase; margin: 4px 0 2px;">Connessione MySQL</div>', unsafe_allow_html=True)
                col_h, col_p = st.columns([2, 1.2])
                with col_h:
                    st.text_input("Host", value=st.session_state.db_host, key="sb_db_host")
                with col_p:
                    st.number_input("Port", value=st.session_state.db_port, step=1, key="sb_db_port")
                
                col_u, col_pw = st.columns(2)
                with col_u:
                    st.text_input("User", value=st.session_state.db_user, key="sb_db_user")
                with col_pw:
                    st.text_input("Password", type="password", value=st.session_state.db_pass, key="sb_db_pass")
                
                db_options = ["wealth", "investment_risk_bi", "Custom..."]
                current_db = st.session_state.get("db_name", "wealth" if is_wealth_mode else "investment_risk_bi")
                db_idx = db_options.index(current_db) if current_db in ["wealth", "investment_risk_bi"] else db_options.index("Custom...")
                sel_db = st.selectbox("Database Schema", db_options, index=db_idx, key="sb_db_select")
                if sel_db == "Custom...":
                    custom_db = st.text_input("Nome DB Custom", value="" if current_db in ["wealth", "investment_risk_bi"] else current_db, key="sb_custom_db").strip()
                    if custom_db:
                        st.session_state.db_name = custom_db
            else:
                st.info("☁️ **Modalità In-Memory**: i calcoli avvengono in RAM/Cache senza connessione MySQL.")

            if is_wealth_mode:
                # ── WEALTH & PERSONAL FINANCE SETTINGS ──
                st.markdown('<div style="font-size:10px; font-weight:700; color:#34d399; letter-spacing:0.5px; text-transform:uppercase; margin: 8px 0 2px;">Profilo & Valuta Wealth</div>', unsafe_allow_html=True)
                col_wp, col_wcurr = st.columns([1.5, 1.5])
                with col_wp:
                    st.text_input("Nome Profilo", value=st.session_state.portfolio_name, key="sb_port_name")
                with col_wcurr:
                    curr_options = ["EUR", "USD", "GBP", "CHF"]
                    curr_current = st.session_state.get("base_currency", "EUR")
                    curr_idx = curr_options.index(curr_current) if curr_current in curr_options else 0
                    st.selectbox("Valuta", curr_options, index=curr_idx, key="sb_base_currency")

                st.markdown('<div style="font-size:10px; font-weight:700; color:#34d399; letter-spacing:0.5px; text-transform:uppercase; margin: 8px 0 2px;">⚖️ Regola di Budget & Risparmio</div>', unsafe_allow_html=True)
                preset_options = [
                    "50/30/20 Standard",
                    "40/20/40 Aggressivo FIRE",
                    "60/25/15 Prudenziale",
                    "30/15/55 Super Frugale",
                    "Personalizzato (Custom %)"
                ]
                preset_map = {
                    "50/30/20 Standard": (50.0, 30.0, 20.0),
                    "40/20/40 Aggressivo FIRE": (40.0, 20.0, 40.0),
                    "60/25/15 Prudenziale": (60.0, 25.0, 15.0),
                    "30/15/55 Super Frugale": (30.0, 15.0, 55.0),
                }

                current_preset = st.session_state.get("wealth_budget_preset", "50/30/20 Standard")
                p_idx = preset_options.index(current_preset) if current_preset in preset_options else 0
                
                sel_preset = st.selectbox("Modello di Ripartizione", preset_options, index=p_idx, key="sb_wealth_preset_sel")
                if sel_preset in preset_map and sel_preset != st.session_state.get("_prev_wealth_preset"):
                    p_n, p_w, p_s = preset_map[sel_preset]
                    st.session_state.wealth_budget_preset = sel_preset
                    st.session_state.wealth_budget_needs_pct = p_n
                    st.session_state.wealth_budget_wants_pct = p_w
                    st.session_state.wealth_budget_savings_pct = p_s
                    st.session_state["_prev_wealth_preset"] = sel_preset

                col_n, col_w, col_s = st.columns(3)
                with col_n:
                    n_val = st.number_input("Needs %", min_value=5.0, max_value=90.0, value=float(st.session_state.wealth_budget_needs_pct), step=5.0, key="sb_wb_needs")
                with col_w:
                    w_val = st.number_input("Wants %", min_value=0.0, max_value=90.0, value=float(st.session_state.wealth_budget_wants_pct), step=5.0, key="sb_wb_wants")
                with col_s:
                    s_val = st.number_input("Savings %", min_value=0.0, max_value=90.0, value=float(st.session_state.wealth_budget_savings_pct), step=5.0, key="sb_wb_savings")
                
                st.session_state.wealth_budget_needs_pct = n_val
                st.session_state.wealth_budget_wants_pct = w_val
                st.session_state.wealth_budget_savings_pct = s_val
                
                total_alloc = n_val + w_val + s_val
                if abs(total_alloc - 100.0) < 0.01:
                    st.caption(f"🟢 **Allocazione 100% Bilanciata** ({n_val:.0f}% Bisogni / {w_val:.0f}% Svago / {s_val:.0f}% Risparmio)")
                else:
                    st.caption(f"⚠️ **Totale: {total_alloc:.0f}%** (La somma ideale è 100%)")

                st.markdown('<div style="font-size:10px; font-weight:700; color:#34d399; letter-spacing:0.5px; text-transform:uppercase; margin: 12px 0 4px;">🔥 Parametri FIRE & Previdenza</div>', unsafe_allow_html=True)
                col_swr, col_age = st.columns(2)
                with col_swr:
                    swr_val = st.number_input("SWR FIRE %", min_value=1.5, max_value=8.0, value=float(st.session_state.get("wealth_fire_swr", 4.0)), step=0.1, key="sb_wealth_swr_input")
                    st.session_state.wealth_fire_swr = swr_val
                with col_age:
                    age_val = st.number_input("Età Target", min_value=30, max_value=75, value=int(st.session_state.get("wealth_target_retirement_age", 67)), step=1, key="sb_wealth_age_input")
                    st.session_state.wealth_target_retirement_age = age_val

                st.markdown('<div style="font-size:10px; font-weight:700; color:#34d399; letter-spacing:0.5px; text-transform:uppercase; margin: 12px 0 4px;">🏛️ Fisco & Deducibilità</div>', unsafe_allow_html=True)
                tax_regimes = ["Ordinario (26%)", "Riforma Unificata 2026 (26%)", "Agevolato Titoli Stato (12.5%)", "Dichiarativo / Quadro RW"]
                t_idx = tax_regimes.index(st.session_state.get("wealth_tax_regime", "Ordinario (26%)")) if st.session_state.get("wealth_tax_regime") in tax_regimes else 0
                sel_tax = st.selectbox("Regime Fiscale Predefinito", tax_regimes, index=t_idx, key="sb_wealth_tax_regime")
                st.session_state.wealth_tax_regime = sel_tax

                with st.popover("ℹ️ Guida Metodologica Wealth", use_container_width=True):
                    st.markdown("""
                    **🏛️ Modello di Pianificazione Patrimoniale ARGUS**
                    * **50% Bisogni Primari (Needs)**: Casa, mutuo/affitto, utenze, spesa alimentare, trasporti essenziali, salute.
                    * **30% Desideri & Svago (Wants)**: Ristoranti, viaggi, shopping, abbonamenti streaming, hobby.
                    * **20% Risparmio & Investimenti (Savings)**: PAC azionario/obbligazionario, fondi pensione, incremento liquidità.
                    * **Safe Withdrawal Rate (SWR)**: Percentuale annua prelevabile dal patrimonio investito per sostenere le spese per 30+ anni (Trinity Study).
                    * **Deducibilità Fondo Pensione**: Fino a **€ 5.164,57** annui deducibili dall'imponibile IRPEF (art. 51 TUIR).
                    """)

            else:
                # ── RISK & QUANT SPECIFIC SETTINGS ──
                st.markdown('<div style="font-size:10px; font-weight:700; color:#ff9900; letter-spacing:0.5px; text-transform:uppercase; margin: 8px 0 2px;">Profilo & Benchmark</div>', unsafe_allow_html=True)
                st.text_input("Nome Portafoglio", value=st.session_state.portfolio_name, key="sb_port_name")
                
                col_curr, col_bench = st.columns([1.3, 1.7])
                with col_curr:
                    curr_options = ["EUR", "USD", "GBP", "CHF"]
                    curr_current = st.session_state.get("base_currency", "EUR")
                    curr_idx = curr_options.index(curr_current) if curr_current in curr_options else 0
                    st.selectbox("Valuta", curr_options, index=curr_idx, key="sb_base_currency")
                
                with col_bench:
                    bench_options = ["SPY", "QQQ", "VWRL.L", "^GSPC", "^STOXX50E", "VWCE.MI", "URTH", "BTC-USD", "Custom..."]
                    current_bench = st.session_state.get("benchmark", "SPY")
                    b_idx = bench_options.index(current_bench) if current_bench in bench_options[:-1] else bench_options.index("Custom...")
                    sel_b = st.selectbox("Benchmark", bench_options, index=b_idx, key="sb_bench_select")
                
                if sel_b == "Custom...":
                    cust_b = st.text_input("Ticker Benchmark Custom", value="" if current_bench in bench_options[:-1] else current_bench, key="sb_custom_bench").strip().upper()
                    if cust_b:
                        st.session_state.benchmark = cust_b

                st.markdown('<div style="font-size:10px; font-weight:700; color:#ff9900; letter-spacing:0.5px; text-transform:uppercase; margin: 8px 0 2px;">Tasso Privo di Rischio (Risk-Free)</div>', unsafe_allow_html=True)
                col_rf_m, col_rf_v = st.columns([1.3, 1.0])
                with col_rf_m:
                    rf_mode_opts = ["Auto (Live Market)", "Manuale"]
                    rf_mode_idx = 0 if st.session_state.rf_mode == "Auto (Live Market)" else 1
                    st.selectbox("Modalità Rf", rf_mode_opts, index=rf_mode_idx, key="sb_rf_mode")

                with col_rf_v:
                    if st.session_state.rf_mode == "Manuale":
                        st.number_input("Tasso %", min_value=0.0, max_value=25.0, value=float(st.session_state.custom_rf_rate_pct), step=0.25, key="sb_custom_rf")
                    else:
                        st.text_input("Tasso Live", value=f"{active_rf_info['rate_pct']:.2f}%", disabled=True)

                from core.ui_utils import render_risk_free_modal
                render_risk_free_modal(currency=st.session_state.base_currency, use_popover=True, button_label="ℹ️ Info Metodologia Risk-Free")

        # ── 4. PULIZIA CACHE & RESET SESSIONE ─────────────────────────
        if st.button("♻️ Svuota Cache & Reset Sessione", use_container_width=True):
            # Rileva esattamente se l'utente si trova nel modulo Wealth o Risk
            cur_p = get_current_page_name()
            in_wealth = is_wealth_mode or any(w in cur_p for w in ["12_", "13_", "14_", "15_", "16_", "17_", "18_", "19_", "20_", "21_"])


            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            st.cache_data.clear()
            st.cache_resource.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]

            st.session_state["session_cleared"] = True
            st.session_state["results"] = None
            st.session_state["portfolio_name"] = None
            st.session_state["active_portfolio_id"] = None
            st.session_state["selected_portfolio_id"] = None
            st.session_state["wealth_active_portfolio_id"] = None
            st.session_state["pipeline_done"] = False

            modules_to_reload = [m for m in sys.modules if m.startswith('core.')]
            for m in modules_to_reload:
                try:
                    del sys.modules[m]
                except Exception:
                    pass

            if in_wealth:
                st.session_state["argus_portal_mode"] = "🏛️ Wealth Management"
                switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")
            else:
                st.session_state["argus_portal_mode"] = "📊 Risk Analytics"
                switch_to_page("0_Control_Room.py")


        if st.button("👁️ Schermata di Avvio (Splash)", key="btn_sidebar_show_splash", use_container_width=True):
            st.session_state["splash_dismissed"] = False
            try:
                st.switch_page("0_Control_Room.py")
            except Exception:
                st.rerun()

        st.markdown("""
        <div style="text-align: center; padding: 10px 0 2px; border-top: 1px solid rgba(255,255,255,0.06); margin-top: 10px;">
            <div style="font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 0.5px;">ARGUS RISK & WEALTH INTELLIGENCE</div>
            <div style="font-size: 10px; font-weight: 600; color: #ff9900; margin-top: 2px;">v6.3.0 Institutional Ecosystem</div>
        </div>
        """, unsafe_allow_html=True)
