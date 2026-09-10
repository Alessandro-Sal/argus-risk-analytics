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
from typing import Optional, List, Dict, Any
from core.workspace_manager import ensure_session_restored


@st.cache_data(ttl=30, show_spinner=False)
def _get_available_mysql_dbs(host: str, port: int, user: str, password: str) -> list:
    """Rileva dinamicamente i database utente attivi su MySQL escludendo gli schemi di sistema."""
    try:
        from sqlalchemy import create_engine, text
        import pymysql
        sys_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/"
        eng = create_engine(sys_url, connect_args={"connect_timeout": 2})
        with eng.connect() as conn:
            res = conn.execute(text("SHOW DATABASES;"))
            ignored = {"information_schema", "mysql", "performance_schema", "sys"}
            dbs = [row[0] for row in res if row[0] not in ignored]
            return dbs
    except Exception:
        return []


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
        "has_subtabs": True,
        "tab_key": "wealth_cr_active_tab",
        "subtabs": [
            {"label": "📥 Data Pipeline", "target": "📥 Data Pipeline & Ingestion"},
            {"label": "⚙️ Gestione Conti", "target": "⚙️ Gestione Conti & Categorie"},
            {"label": "📑 Hub Reportistica", "target": "📑 Hub Reportistica & Esportazioni"}
        ]
    },
    {
        "title": "Patrimonio & Net Worth",
        "icon": "🏛️",
        "page_file": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
        "key": "13_Patrimonio_e_NetWorth",
        "has_subtabs": True,
        "tab_key": "wealth_nw_active_tab",
        "subtabs": [
            {"label": "🌐 Bilancio & Allocazione", "target": "🏛️ Bilancio & Allocazione"},
            {"label": "📜 Stato Patrimoniale", "target": "📋 Stato Patrimoniale & Conti"},
            {"label": "⏳ Wealth Temporal", "target": "📊 Wealth Temporal Desk"},
            {"label": "🏛️ Family Office", "target": "🏢 Family Office & Holding"},
            {"label": "💱 Rischio FX & Brinson", "target": "💱 Rischio FX & Attribuzione Brinson"},
            {"label": "🌪️ Stress Testing", "target": "🌪️ Global Wealth Stress-Testing"}
        ]
    },
    {
        "title": "Cash Flow & Spese",
        "icon": "💳",
        "page_file": "pages/14_💳_Cash_Flow_e_Spese.py",
        "key": "14_Cash_Flow_e_Spese",
        "has_subtabs": True,
        "tab_key": "wealth_cf_active_tab",
        "subtabs": [
            {"label": "🌊 Flusso Sankey", "target": "🌊 Sankey & Flussi"},
            {"label": "📈 Trend & Mensile", "target": "📊 Trend & Stagionalità MoM"},
            {"label": "🏬 Commercianti", "target": "🏷️ Top Merchant & Pareto (80/20)"},
            {"label": "✉️ Budget & Buste", "target": "🎯 Budget vs Consuntivo (Envelope)"},
            {"label": "📅 Abbonamenti", "target": "🔁 Abbonamenti & Costi Fissi"},
            {"label": "🛠️ Simulatore What-if", "target": "🔄 Ottimizzazione PAC & What-If"},
            {"label": "🔮 Previsioni & Anomalie", "target": "🔮 Previsione Cassa & Anomalie"},
            {"label": "📑 Registro Movimenti", "target": "📜 Libro Mastro & Inserimento"}
        ]
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
        "has_subtabs": True,
        "tab_key": "wealth_fire_active_tab",
        "subtabs": [
            {"label": "🔥 Calcolatore FIRE", "target": "🔥 Calcolatore FIRE & SWR"},
            {"label": "🌪️ Stress Testing", "target": "🌪️ Stress Testing & Crisi"},
            {"label": "🎯 Obiettivi di Vita", "target": "🎯 Obiettivi & Merton Model"},
            {"label": "⏳ Sequence of Returns", "target": "⏳ Sequence of Returns (SRR)"},
            {"label": "💸 Fee Drag & TCO", "target": "💸 Fee Drag & TCO"}
        ]
    },
    {
        "title": "Fiscalità & Quadro RW",
        "icon": "📑",
        "page_file": "pages/18_📑_Fiscalita_e_Quadro_RW.py",
        "key": "18_Fiscalita_e_Quadro_RW",
        "has_subtabs": True,
        "tab_key": "wealth_tax_active_tab",
        "subtabs": [
            {"label": "📑 Monitoraggio RW", "target": "📑 Monitoraggio Quadro RW"},
            {"label": "🪦 Zainetto Minusvalenze", "target": "🪦 Zainetto Fiscale Minusvalenze"},
            {"label": "🌾 Tax-Loss Harvesting", "target": "🌾 Tax-Loss Harvesting"},
            {"label": "⚖️ Asset Location", "target": "⚖️ Asset Location & Split Fiscale"},
            {"label": "🛡️ Ottimizzazione", "target": "🛡️ Strategie di Ottimizzazione"},
            {"label": "🌐 Cross-Border", "target": "🌐 Cross-Border & Doppia Imposizione"}
        ]
    },
    {
        "title": "Immobili & Mutui",
        "icon": "🏡",
        "page_file": "pages/19_🏡_Immobili_e_Mutui.py",
        "key": "19_Immobili_e_Mutui",
        "has_subtabs": True,
        "tab_key": "wealth_re_active_tab",
        "subtabs": [
            {"label": "🏡 Net Home Equity", "target": "🏡 Net Equity & Composizione"},
            {"label": "📉 Piani Ammortamento", "target": "📉 Piani Ammortamento & Mutui"},
            {"label": "📈 Rendita Locazioni", "target": "📈 Redditività da Locazione"},
            {"label": "⚖️ Buy vs Rent", "target": "⚖️ Buy vs Rent Analyzer"}
        ]
    },
    {
        "title": "Pianificazione Successoria",
        "icon": "⚖️",
        "page_file": "pages/20_⚖️_Pianificazione_Successoria.py",
        "key": "20_Pianificazione_Successoria",
        "has_subtabs": True,
        "tab_key": "wealth_estate_active_tab",
        "subtabs": [
            {"label": "📊 Quote Legittima", "target": "📊 Quote Ereditarie & Legittima"},
            {"label": "💰 Imposte Successione", "target": "💰 Calcolo Imposte Successione"},
            {"label": "🛡️ Protezione Patrimonio", "target": "🛡️ Strumenti di Protezione Patrimoniale"},
            {"label": "📜 Patto di Famiglia", "target": "📜 Patto di Famiglia & Governance"}
        ]
    },
    {
        "title": "AI Copilot & Advisor",
        "icon": "🤖",
        "page_file": "pages/21_🤖_AI_Copilot_e_Advisor.py",
        "key": "21_AI_Copilot_e_Advisor",
        "has_subtabs": True,
        "tab_key": "wealth_copilot_active_tab",
        "subtabs": [
            {"label": "🔍 Diagnosi Olistica", "target": "🔍 Diagnosi Olistica"},
            {"label": "⚖️ Rebalancing Watchdog", "target": "⚖️ Rebalancing Watchdog"},
            {"label": "🎯 Life Goal Planner", "target": "🎯 Life Goal Planner"},
            {"label": "📑 Quarterly Review", "target": "📑 Quarterly Wealth Review"},
            {"label": "💬 Chat Advisor", "target": "💬 Chat Finanziaria"},
            {"label": "🎙️ Voice Briefing", "target": "🎙️ Voice Briefing"}
        ]
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


def init_settings_session_state(is_wealth_mode: bool = False) -> None:
    """Inizializza tutte le chiavi di sessione relative alle impostazioni con fallback robusti."""
    # ── Impostazioni Globali ──────────────────────────────────────
    if "base_currency" not in st.session_state: st.session_state.base_currency = "EUR"
    if "confidence_level" not in st.session_state: st.session_state.confidence_level = 0.95
    if "locale" not in st.session_state: st.session_state.locale = "it"
    if "accounting_notation" not in st.session_state: st.session_state.accounting_notation = "standard"
    if "data_environment" not in st.session_state: st.session_state.data_environment = "Auto (Ibrido)"
    if "offline_mode" not in st.session_state: st.session_state.offline_mode = False
    if "ui_theme" not in st.session_state: st.session_state.ui_theme = "Midnight Obsidian"

    # Inizializzazione protetta chiavi widget
    if st.session_state.get("sb_base_currency") is None: st.session_state.sb_base_currency = st.session_state.base_currency
    if st.session_state.get("sb_confidence_level") is None: st.session_state.sb_confidence_level = st.session_state.confidence_level
    if st.session_state.get("sb_locale_select") is None: st.session_state.sb_locale_select = st.session_state.locale
    if st.session_state.get("sb_accounting_select") is None: st.session_state.sb_accounting_select = st.session_state.accounting_notation

    # DB Connection & Sync Defaults
    if "db_host" not in st.session_state: st.session_state.db_host = os.getenv("STREAMLIT_DB_HOST", "localhost")
    if "db_port" not in st.session_state: st.session_state.db_port = _detect_default_port(st.session_state.db_host, 3306)
    if "db_user" not in st.session_state: st.session_state.db_user = os.getenv("STREAMLIT_DB_USER", "root")
    if "db_pass" not in st.session_state: st.session_state.db_pass = os.getenv("STREAMLIT_DB_PASS", "root")
    if "db_name" not in st.session_state: st.session_state.db_name = os.getenv("STREAMLIT_DB_NAME", "wealth")
    if "wealth_db_name" not in st.session_state: st.session_state.wealth_db_name = st.session_state.db_name
    if "risk_db_name" not in st.session_state: st.session_state.risk_db_name = st.session_state.db_name

    # ── Parametri Specifici Risk Analytics ────────────────────────
    if "risk_estimation_method" not in st.session_state: st.session_state.risk_estimation_method = "Parametrico (Cornish-Fisher)"
    if "risk_lookback_period" not in st.session_state: st.session_state.risk_lookback_period = "Ultimo Anno (252g)"
    if "risk_decay_factor" not in st.session_state: st.session_state.risk_decay_factor = 0.94
    if "benchmark" not in st.session_state: st.session_state.benchmark = "SPY"
    if "rf_mode" not in st.session_state: st.session_state.rf_mode = "Auto (Live Market)"
    if "custom_rf_rate_pct" not in st.session_state: st.session_state.custom_rf_rate_pct = 2.75

    # ── Parametri Specifici Wealth Management ─────────────────────
    if "wealth_planning_horizon_years" not in st.session_state: st.session_state.wealth_planning_horizon_years = 25
    if "wealth_expected_return_pct" not in st.session_state: st.session_state.wealth_expected_return_pct = 6.50
    if "wealth_inflation_rate_pct" not in st.session_state: st.session_state.wealth_inflation_rate_pct = 2.00
    if "wealth_tax_regime" not in st.session_state: st.session_state.wealth_tax_regime = "Ordinario (26%)"
    if "wealth_stress_scenario" not in st.session_state: st.session_state.wealth_stress_scenario = "Base (Nessuno Shock)"
    if "wealth_budget_preset" not in st.session_state: st.session_state.wealth_budget_preset = "50/30/20 Standard"
    if "wealth_budget_needs_pct" not in st.session_state: st.session_state.wealth_budget_needs_pct = 50.0
    if "wealth_budget_wants_pct" not in st.session_state: st.session_state.wealth_budget_wants_pct = 30.0
    if "wealth_budget_savings_pct" not in st.session_state: st.session_state.wealth_budget_savings_pct = 20.0
    if "wealth_fire_swr" not in st.session_state: st.session_state.wealth_fire_swr = 4.0
    if "wealth_target_retirement_age" not in st.session_state: st.session_state.wealth_target_retirement_age = 67
    if "wealth_pension_deduction_limit" not in st.session_state: st.session_state.wealth_pension_deduction_limit = 5164.57
    if "portfolio_name" not in st.session_state: st.session_state.portfolio_name = "Master Wealth" if is_wealth_mode else "Portafoglio Principale"
    if "run_name" not in st.session_state: st.session_state.run_name = ""


def reset_settings_to_defaults(module: Optional[str] = None) -> None:
    """Ripristina i parametri di calcolo e configurazione ai valori predefiniti istituzionali."""
    target_keys = []
    if module in (None, "global"):
        target_keys.extend([
            "base_currency", "confidence_level", "locale", "accounting_notation",
            "data_environment", "sb_base_currency", "sb_confidence_level",
            "sb_locale_select", "sb_accounting_select", "sb_data_environment"
        ])
    if module in (None, "risk"):
        target_keys.extend([
            "risk_estimation_method", "risk_lookback_period", "risk_decay_factor",
            "benchmark", "rf_mode", "custom_rf_rate_pct",
            "sb_risk_method", "sb_risk_lookback", "sb_risk_decay",
            "sb_bench_select", "sb_custom_bench", "sb_rf_mode", "sb_custom_rf"
        ])
    if module in (None, "wealth"):
        target_keys.extend([
            "wealth_planning_horizon_years", "wealth_expected_return_pct",
            "wealth_inflation_rate_pct", "wealth_tax_regime", "wealth_stress_scenario",
            "wealth_budget_preset", "wealth_budget_needs_pct", "wealth_budget_wants_pct",
            "wealth_budget_savings_pct", "wealth_fire_swr", "wealth_target_retirement_age",
            "sb_wealth_horizon", "sb_wealth_exp_return", "sb_wealth_inflation",
            "sb_wealth_tax_regime", "sb_wealth_stress", "sb_wealth_preset_sel",
            "sb_wb_needs", "sb_wb_wants", "sb_wb_savings", "sb_wealth_swr_input", "sb_wealth_age_input"
        ])
    for k in target_keys:
        st.session_state.pop(k, None)
    
    init_settings_session_state(is_wealth_mode=(module == "wealth"))
    try:
        st.toast("✅ Impostazioni ripristinate ai valori predefiniti!", icon="🔄")
    except Exception:
        pass
    st.rerun()


SETTINGS_SIDEBAR_CSS = """
<style>
/* ── ARGUS SETTINGS SIDEBAR STYLING ── */

/* Status Card HUD */
section[data-testid="stSidebar"] .argus-hud-card {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 8px;
    padding: 8px 10px;
    margin: 2px 0 10px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

section[data-testid="stSidebar"] .argus-hud-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

section[data-testid="stSidebar"] .argus-hud-db {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
    flex: 1;
}

section[data-testid="stSidebar"] .argus-hud-db-icon {
    font-size: 11px;
    flex-shrink: 0;
}

section[data-testid="stSidebar"] .argus-hud-db-name {
    font-size: 11.5px;
    font-weight: 700;
    color: #e2e8f0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 140px;
    display: inline-block;
}

section[data-testid="stSidebar"] .argus-hud-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 9.5px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 9999px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    flex-shrink: 0;
}

section[data-testid="stSidebar"] .argus-hud-status-badge.live {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

section[data-testid="stSidebar"] .argus-hud-status-badge.offline {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

section[data-testid="stSidebar"] .argus-hud-status-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    display: inline-block;
}

section[data-testid="stSidebar"] .argus-hud-status-badge.live .argus-hud-status-dot {
    background: #10b981;
    box-shadow: 0 0 5px #10b981;
}

section[data-testid="stSidebar"] .argus-hud-status-badge.offline .argus-hud-status-dot {
    background: #38bdf8;
    box-shadow: 0 0 5px #38bdf8;
}

section[data-testid="stSidebar"] .argus-hud-chips {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    padding-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

section[data-testid="stSidebar"] .argus-hud-chip {
    font-size: 10px;
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 4px;
    padding: 2px 4px;
    white-space: nowrap;
    flex: 1;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
}

section[data-testid="stSidebar"] .argus-hud-chip strong {
    color: #f1f5f9;
    font-weight: 600;
}

/* Tabs inside Sidebar */
section[data-testid="stSidebar"] div[data-testid="stTabs"] button[role="tab"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 6px 8px !important;
    flex: 1 1 0 !important;
    text-align: center !important;
}

/* Segmented Control flex distribution & responsive buttons */
section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] {
    width: 100% !important;
    margin-bottom: 6px !important;
}

section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] > div {
    display: flex !important;
    width: 100% !important;
    gap: 2px !important;
}

section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] button {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    padding: 3px 5px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: nowrap !important;
}

/* Widget Labels in Settings */
section[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p {
    font-size: 10.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.35px !important;
    color: #94a3b8 !important;
    margin-bottom: 2px !important;
}

/* Compact Widget Margins */
section[data-testid="stSidebar"] .stSelectbox,
section[data-testid="stSidebar"] .stTextInput,
section[data-testid="stSidebar"] .stNumberInput,
section[data-testid="stSidebar"] .stSlider {
    margin-bottom: 6px !important;
}

/* Real Return Card */
section[data-testid="stSidebar"] .argus-real-return-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 6px 8px;
    margin-top: 14px;
    text-align: center;
}

/* Sleek Divider */
section[data-testid="stSidebar"] .argus-sidebar-divider {
    margin: 10px 0 8px 0;
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
"""


def render_settings_status_hud(current_module: str = "risk") -> None:
    """Renderizza un badge HUD orizzontale compatto a 2 righe ad alta scannabilità sullo stato del sistema."""
    is_wealth = (current_module == "wealth")
    is_off = bool(st.session_state.get("offline_mode", False))
    db_name = st.session_state.get("db_name", "wealth")
    
    if is_off:
        db_label = "SQLite Locale" if is_wealth else "Memoria RAM"
        status_badge = "Offline"
        status_cls = "offline"
    else:
        db_label = db_name
        status_badge = "Live"
        status_cls = "live"
        
    curr = st.session_state.get("base_currency", "EUR")
    if is_wealth:
        spec_text = f"{st.session_state.get('wealth_planning_horizon_years', 25)}y"
        spec_icon = "⏳"
    else:
        conf_pct = int(round(float(st.session_state.get("confidence_level", 0.95)) * 100))
        spec_text = f"{conf_pct}%"
        spec_icon = "🎯"

    data_env = str(st.session_state.get("data_environment", "Auto (Ibrido)"))
    if "Auto" in data_env:
        env_short = "Auto"
    elif "Yahoo" in data_env:
        env_short = "Yahoo"
    elif "DuckDB" in data_env:
        env_short = "DuckDB"
    elif "SQLite" in data_env:
        env_short = "SQLite"
    else:
        env_short = data_env[:6]

    st.markdown(f"""
    <div class="argus-hud-card">
        <div class="argus-hud-header">
            <div class="argus-hud-db" title="{db_name}">
                <span class="argus-hud-db-icon">🗄️</span>
                <span class="argus-hud-db-name">{db_label}</span>
            </div>
            <span class="argus-hud-status-badge {status_cls}">
                <span class="argus-hud-status-dot"></span>
                {status_badge}
            </span>
        </div>
        <div class="argus-hud-chips">
            <span class="argus-hud-chip" title="Valuta Base">💱 <strong>{curr}</strong></span>
            <span class="argus-hud-chip" title="{'Orizzonte Temporale' if is_wealth else 'Confidenza VaR'}">{spec_icon} <strong>{spec_text}</strong></span>
            <span class="argus-hud-chip" title="Sorgente Dati">📡 <strong>{env_short}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_settings_sidebar(current_module: str = "risk") -> None:
    """
    Renderizza l'area 'Impostazioni & Configurazione Engine' contestuale, modulare e compatta.
    - current_module: 'risk' (pagine 0-11) o 'wealth' (pagine 12-21)
    Organizzata in due tab distinti (Globale vs Modulo Corrente) con segmented controls e prevenzione troncamenti.
    """
    init_settings_session_state(is_wealth_mode=(current_module == "wealth"))
    is_wealth = (current_module == "wealth")
    badge_module = "🏛️ Wealth" if is_wealth else "📊 Risk"

    with st.expander(f"⚙️ Impostazioni ({badge_module})", expanded=False):
        # 0. Iniezione CSS dedicato
        st.markdown(SETTINGS_SIDEBAR_CSS, unsafe_allow_html=True)

        # 1. Status HUD sintetico a 2 righe con prevenzione overflow
        render_settings_status_hud(current_module=current_module)

        # 2. Separazione contestuale in due Tab puliti
        tab_global, tab_mod = st.tabs(["🌐 Globale", f"{badge_module}"])

        # ── TAB 1: SISTEMA & WORKSPACE GLOBALE ────────────────────────
        with tab_global:
            # 1. Valuta Base con segmented control compatto
            curr_opts = ["EUR", "USD", "CHF", "GBP"]
            curr_active = st.session_state.get("base_currency", "EUR")
            curr_default = curr_active if curr_active in curr_opts else "EUR"
            if st.session_state.get("sb_base_currency") not in curr_opts:
                st.session_state.sb_base_currency = curr_default
            sel_curr = st.segmented_control(
                "Valuta Base",
                curr_opts,
                default=curr_default,
                key="sb_base_currency",
                help="Valuta contabile e di reporting per il calcolo di controvalori e VaR."
            )
            if sel_curr:
                st.session_state.base_currency = sel_curr
            else:
                st.session_state.base_currency = curr_default
                st.session_state.sb_base_currency = curr_default

            # 2. Livello di Confidenza VaR
            conf_opts = [0.90, 0.95, 0.99]
            conf_active = float(st.session_state.get("confidence_level", 0.95))
            conf_default = conf_active if conf_active in conf_opts else 0.95
            if st.session_state.get("sb_confidence_level") not in conf_opts:
                st.session_state.sb_confidence_level = conf_default
            sel_conf = st.segmented_control(
                "Livello Confidenza (VaR)",
                conf_opts,
                default=conf_default,
                format_func=lambda x: f"{int(round(x * 100))}%",
                key="sb_confidence_level",
                help="Livello di confidenza statistica per il calcolo di VaR e Expected Shortfall (CVaR)."
            )
            if sel_conf is not None:
                st.session_state.confidence_level = float(sel_conf)
            else:
                st.session_state.confidence_level = conf_default
                st.session_state.sb_confidence_level = conf_default

            # 3. Lingua & Notazione Contabile in colonne bilanciate con segmented control
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                lang_opts = ["it", "en"]
                curr_lang = st.session_state.get("locale", "it")
                lang_default = curr_lang if curr_lang in lang_opts else "it"
                if st.session_state.get("sb_locale_select") not in lang_opts:
                    st.session_state.sb_locale_select = lang_default
                sel_lang = st.segmented_control(
                    "Lingua",
                    lang_opts,
                    default=lang_default,
                    format_func=lambda x: "🇮🇹 IT" if x == "it" else "🇬🇧 EN",
                    key="sb_locale_select",
                    help="Lingua interfaccia e localizzazione date/numeri."
                )
                if sel_lang:
                    st.session_state.locale = sel_lang
                else:
                    st.session_state.locale = lang_default
                    st.session_state.sb_locale_select = lang_default

            with col_g2:
                notat_opts = ["standard", "parentheses"]
                curr_notat = st.session_state.get("accounting_notation", "standard")
                notat_default = curr_notat if curr_notat in notat_opts else "standard"
                if st.session_state.get("sb_accounting_select") not in notat_opts:
                    st.session_state.sb_accounting_select = notat_default
                sel_notat = st.segmented_control(
                    "Notazione",
                    notat_opts,
                    default=notat_default,
                    format_func=lambda x: "Standard" if x == "standard" else "Wall St",
                    key="sb_accounting_select",
                    help="Standard: -€1.000 | Wall St: (€1.000) per valori negativi."
                )
                if sel_notat:
                    st.session_state.accounting_notation = sel_notat
                else:
                    st.session_state.accounting_notation = notat_default
                    st.session_state.sb_accounting_select = notat_default

            # 4. Sorgente Dati su larghezza intera (zero troncamenti)
            env_opts = ["Auto (Ibrido)", "Live Yahoo Finance", "DuckDB Veloce", "Local SQLite"]
            curr_env = st.session_state.get("data_environment", "Auto (Ibrido)")
            env_idx = env_opts.index(curr_env) if curr_env in env_opts else 0
            sel_env = st.selectbox(
                "Sorgente Dati",
                env_opts,
                index=env_idx,
                key="sb_data_environment",
                help="Engine di ingestion e storage per le serie storiche di prezzo."
            )
            st.session_state.data_environment = sel_env

            # 5. Modalità Offline Toggle
            off_lbl = "Modalità Offline (SQLite Locale)" if is_wealth else "Modalità Offline (RAM)"
            off_hlp = "Usa il database locale embedded SQLite (data/argus_local.db) senza dipendere da MySQL." if is_wealth else "Simulazione in memoria RAM con dataset sintetici senza dipendenze esterne."
            sel_off = st.toggle(
                off_lbl,
                value=bool(st.session_state.get("offline_mode", False)),
                key="sb_offline_toggle",
                help=off_hlp
            )
            st.session_state.offline_mode = sel_off

            # 6. Connessione & Schema Database (sub-expander collassabile)
            if not st.session_state.offline_mode:
                with st.expander("🔌 Connessione & Schema Database", expanded=False):
                    col_h, col_p = st.columns([2, 1.2])
                    with col_h:
                        st.session_state.db_host = st.text_input("Host", value=st.session_state.db_host, key="sb_db_host")
                    with col_p:
                        st.session_state.db_port = int(st.number_input("Port", value=st.session_state.db_port, step=1, key="sb_db_port"))

                    col_u, col_pw = st.columns(2)
                    with col_u:
                        st.session_state.db_user = st.text_input("User", value=st.session_state.db_user, key="sb_db_user")
                    with col_pw:
                        st.session_state.db_pass = st.text_input("Password", type="password", value=st.session_state.db_pass, key="sb_db_pass")

                    active_db = st.session_state.get("db_name", "wealth")
                    found_dbs = _get_available_mysql_dbs(st.session_state.db_host, st.session_state.db_port, st.session_state.db_user, st.session_state.db_pass)

                    db_options = []
                    base_defaults = ["wealth", "wealth_app", "wealth_data", "investment_risk_bi"]
                    for d in base_defaults:
                        if d in found_dbs and d not in db_options: db_options.append(d)
                    for d in found_dbs:
                        if d not in db_options: db_options.append(d)
                    for d in base_defaults:
                        if d not in db_options: db_options.append(d)
                    if active_db and active_db not in db_options and active_db != "Custom...":
                        db_options.append(active_db)
                    db_options.append("Custom...")

                    db_idx = db_options.index(active_db) if active_db in db_options else (len(db_options) - 1)
                    sel_db = st.selectbox("Database Schema", db_options, index=db_idx, key="sb_db_select")
                    if sel_db == "Custom...":
                        custom_db = st.text_input("Nome DB Custom", value=active_db if active_db not in db_options[:-1] else "", key="sb_custom_db", placeholder="es. family_office_db").strip()
                        if custom_db:
                            st.session_state.db_name = custom_db
                            st.session_state.wealth_db_name = custom_db
                            st.session_state.risk_db_name = custom_db
                    else:
                        st.session_state.db_name = sel_db
                        st.session_state.wealth_db_name = sel_db
                        st.session_state.risk_db_name = sel_db

                    if is_wealth:
                        if st.button("📥 Allinea DB Locale SQLite", key="sb_btn_sync_sqlite", use_container_width=True, help="Copia tutti i dati e movimenti da MySQL al database locale SQLite per lavorare offline."):
                            try:
                                from core.wealth.wealth_db import sync_mysql_to_sqlite
                                sync_res = sync_mysql_to_sqlite(st.session_state.db_user, st.session_state.db_pass, st.session_state.db_host, st.session_state.db_port, st.session_state.db_name)
                                st.success(f"Allineati {sync_res.get('wealth_cashflow', 0)} movimenti e {sync_res.get('wealth_accounts', 0)} conti in SQLite!")
                            except Exception as ex:
                                st.error(f"Errore sincronizzazione: {ex}")

        # ── TAB 2: PARAMETRI VERTICALI DI MODULO ──────────────────────
        with tab_mod:
            if not is_wealth:
                # ── PARAMETRI SPECIFICI RISK ANALYTICS ──
                st.session_state.portfolio_name = st.text_input(
                    "Nome Portafoglio",
                    value=st.session_state.get("portfolio_name", "Portafoglio Principale"),
                    key="sb_port_name"
                )

                method_opts = [
                    "Parametrico (Cornish-Fisher)",
                    "Storico (Historical Simulation)",
                    "Monte Carlo (Geometric Brownian)"
                ]
                curr_method = st.session_state.get("risk_estimation_method", "Parametrico (Cornish-Fisher)")
                m_idx = method_opts.index(curr_method) if curr_method in method_opts else 0
                sel_method = st.selectbox(
                    "Metodo Stima VaR",
                    method_opts,
                    index=m_idx,
                    key="sb_risk_method",
                    help="Algoritmo di calcolo per Value at Risk ed Expected Shortfall."
                )
                st.session_state.risk_estimation_method = sel_method

                lb_opts = ["Ultimo Anno (252g)", "Ultimi 3 Anni (756g)", "Ultimi 5 Anni (1260g)", "Storico Completo"]
                curr_lb = st.session_state.get("risk_lookback_period", "Ultimo Anno (252g)")
                lb_idx = lb_opts.index(curr_lb) if curr_lb in lb_opts else 0
                sel_lb = st.selectbox(
                    "Lookback Period",
                    lb_opts,
                    index=lb_idx,
                    key="sb_risk_lookback",
                    help="Finestra temporale storica utilizzata per calcolare volatilità e covarianze."
                )
                st.session_state.risk_lookback_period = sel_lb

                col_r1, col_r2 = st.columns([1.1, 0.9])
                with col_r1:
                    bench_options = ["SPY", "QQQ", "VWRL.L", "^GSPC", "^STOXX50E", "VWCE.MI", "URTH", "BTC-USD", "Custom..."]
                    current_bench = st.session_state.get("benchmark", "SPY")
                    b_idx = bench_options.index(current_bench) if current_bench in bench_options[:-1] else bench_options.index("Custom...")
                    sel_b = st.selectbox("Benchmark", bench_options, index=b_idx, key="sb_bench_select")
                    if sel_b == "Custom...":
                        cust_b = st.text_input("Ticker Custom", value="" if current_bench in bench_options[:-1] else current_bench, key="sb_custom_bench").strip().upper()
                        if cust_b: st.session_state.benchmark = cust_b
                    else:
                        st.session_state.benchmark = sel_b

                with col_r2:
                    curr_decay = float(st.session_state.get("risk_decay_factor", 0.94))
                    sel_decay = st.slider(
                        "Decay (λ)",
                        min_value=0.80,
                        max_value=0.99,
                        value=curr_decay,
                        step=0.01,
                        key="sb_risk_decay",
                        help="Fattore di decadimento esponenziale EWMA per ponderare i rendimenti più recenti."
                    )
                    st.session_state.risk_decay_factor = sel_decay

                # Risk-Free Rate
                from core.yield_curve import get_active_risk_free_rate
                col_rf_m, col_rf_v = st.columns([1.2, 1.0])
                with col_rf_m:
                    rf_mode_opts = ["Auto (Live Market)", "Manuale"]
                    rf_idx = 0 if st.session_state.get("rf_mode", "Auto (Live Market)") == "Auto (Live Market)" else 1
                    sel_rf_m = st.selectbox("Modalità Rf", rf_mode_opts, index=rf_idx, key="sb_rf_mode")
                    st.session_state.rf_mode = sel_rf_m
                with col_rf_v:
                    if st.session_state.rf_mode == "Manuale":
                        sel_rf_v = st.number_input(
                            "Tasso %",
                            min_value=0.0,
                            max_value=25.0,
                            value=float(st.session_state.get("custom_rf_rate_pct", 2.75)),
                            step=0.25,
                            format="%.2f",
                            key="sb_custom_rf"
                        )
                        st.session_state.custom_rf_rate_pct = sel_rf_v
                    else:
                        custom_rf_dec = None
                        active_rf_info = get_active_risk_free_rate(currency=st.session_state.base_currency, custom_override=custom_rf_dec)
                        st.text_input("Tasso Live", value=f"{active_rf_info.get('rate_pct', 2.75):.2f}%", disabled=True)

                from core.ui_utils import render_risk_free_modal
                render_risk_free_modal(currency=st.session_state.base_currency, use_popover=True, button_label="ℹ️ Info Metodologia Risk-Free")

            else:
                # ── PARAMETRI SPECIFICI WEALTH MANAGEMENT ──
                st.session_state.portfolio_name = st.text_input(
                    "Nome Profilo",
                    value=st.session_state.get("portfolio_name", "Master Wealth"),
                    key="sb_port_name"
                )

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    curr_horizon = int(st.session_state.get("wealth_planning_horizon_years", 25))
                    sel_horizon = st.slider("Orizzonte (Anni)", min_value=5, max_value=50, value=curr_horizon, step=1, key="sb_wealth_horizon")
                    st.session_state.wealth_planning_horizon_years = sel_horizon
                with col_w2:
                    curr_exp_ret = float(st.session_state.get("wealth_expected_return_pct", 6.50))
                    sel_exp_ret = st.slider("Rend. Nominale (%)", min_value=0.0, max_value=15.0, value=curr_exp_ret, step=0.25, key="sb_wealth_exp_return")
                    st.session_state.wealth_expected_return_pct = sel_exp_ret

                col_w3, col_w4 = st.columns([1.1, 0.9])
                with col_w3:
                    curr_infl = float(st.session_state.get("wealth_inflation_rate_pct", 2.00))
                    sel_infl = st.slider("Inflazione (%)", min_value=0.0, max_value=10.0, value=curr_infl, step=0.25, key="sb_wealth_inflation")
                    st.session_state.wealth_inflation_rate_pct = sel_infl
                with col_w4:
                    real_ret = sel_exp_ret - sel_infl
                    real_col = "#34d399" if real_ret >= 0 else "#f87171"
                    st.markdown(f"""
                    <div class="argus-real-return-card">
                        <div style="font-size:9.5px; color:#94a3b8; text-transform:uppercase; font-weight:700;">Rendimento Reale</div>
                        <div style="font-size:12.5px; font-weight:700; color:{real_col};">{real_ret:+.2f}% / anno</div>
                    </div>
                    """, unsafe_allow_html=True)

                tax_regimes = ["Ordinario (26%)", "Riforma Unificata 2026 (26%)", "Agevolato Titoli Stato (12.5%)", "Dichiarativo / Quadro RW"]
                t_idx = tax_regimes.index(st.session_state.get("wealth_tax_regime", "Ordinario (26%)")) if st.session_state.get("wealth_tax_regime") in tax_regimes else 0
                sel_tax = st.selectbox("Regime Fiscale", tax_regimes, index=t_idx, key="sb_wealth_tax_regime")
                st.session_state.wealth_tax_regime = sel_tax

                stress_scenarios = [
                    "Base (Nessuno Shock)",
                    "Stagflazione & Crisi Energetica",
                    "Crisi Immobiliare & Stretta Creditizia",
                    "Cigno Nero Sistemico (-40%)",
                    "Shock Reddituale & Spesa Improvvisa"
                ]
                curr_stress = st.session_state.get("wealth_stress_scenario", "Base (Nessuno Shock)")
                s_idx = stress_scenarios.index(curr_stress) if curr_stress in stress_scenarios else 0
                sel_stress = st.selectbox("Stress Scenario", stress_scenarios, index=s_idx, key="sb_wealth_stress")
                st.session_state.wealth_stress_scenario = sel_stress

                # Regola Budget & FIRE
                preset_options = ["50/30/20 Standard", "40/20/40 Aggressivo FIRE", "60/25/15 Prudenziale", "30/15/55 Super Frugale", "Personalizzato (Custom %)"]
                preset_map = {
                    "50/30/20 Standard": (50.0, 30.0, 20.0),
                    "40/20/40 Aggressivo FIRE": (40.0, 20.0, 40.0),
                    "60/25/15 Prudenziale": (60.0, 25.0, 15.0),
                    "30/15/55 Super Frugale": (30.0, 15.0, 55.0),
                }
                current_preset = st.session_state.get("wealth_budget_preset", "50/30/20 Standard")
                p_idx = preset_options.index(current_preset) if current_preset in preset_options else 0
                sel_preset = st.selectbox("Modello di Budget", preset_options, index=p_idx, key="sb_wealth_preset_sel")
                if sel_preset in preset_map and sel_preset != st.session_state.get("_prev_wealth_preset"):
                    p_n, p_w, p_s = preset_map[sel_preset]
                    st.session_state.wealth_budget_preset = sel_preset
                    st.session_state.wealth_budget_needs_pct = p_n
                    st.session_state.wealth_budget_wants_pct = p_w
                    st.session_state.wealth_budget_savings_pct = p_s
                    st.session_state["_prev_wealth_preset"] = sel_preset

                col_n, col_w, col_s = st.columns(3)
                with col_n:
                    n_val = st.number_input("Needs %", min_value=5.0, max_value=90.0, value=float(st.session_state.get("wealth_budget_needs_pct", 50.0)), step=5.0, format="%.0f", key="sb_wb_needs")
                with col_w:
                    w_val = st.number_input("Wants %", min_value=0.0, max_value=90.0, value=float(st.session_state.get("wealth_budget_wants_pct", 30.0)), step=5.0, format="%.0f", key="sb_wb_wants")
                with col_s:
                    s_val = st.number_input("Savings %", min_value=0.0, max_value=90.0, value=float(st.session_state.get("wealth_budget_savings_pct", 20.0)), step=5.0, format="%.0f", key="sb_wb_savings")
                st.session_state.wealth_budget_needs_pct = n_val
                st.session_state.wealth_budget_wants_pct = w_val
                st.session_state.wealth_budget_savings_pct = s_val

                col_swr, col_age = st.columns(2)
                with col_swr:
                    swr_val = st.number_input("SWR FIRE %", min_value=1.5, max_value=8.0, value=float(st.session_state.get("wealth_fire_swr", 4.0)), step=0.1, format="%.1f", key="sb_wealth_swr_input")
                    st.session_state.wealth_fire_swr = swr_val
                with col_age:
                    age_val = st.number_input("Età Target", min_value=30, max_value=75, value=int(st.session_state.get("wealth_target_retirement_age", 67)), step=1, key="sb_wealth_age_input")
                    st.session_state.wealth_target_retirement_age = age_val

                with st.popover("ℹ️ Guida Metodologica Wealth", use_container_width=True):
                    st.markdown("""
                    **🏛️ Modello di Pianificazione Patrimoniale ARGUS**
                    * **50% Bisogni (Needs)**: Casa, mutuo/affitto, utenze, spesa alimentare, salute.
                    * **30% Svago (Wants)**: Viaggi, ristoranti, hobby.
                    * **20% Risparmio (Savings)**: PAC azionario/obbligazionario, fondi pensione.
                    * **SWR (Safe Withdrawal Rate)**: Prelievo annuo sostenibile per 30+ anni (Trinity Study).
                    * **Deducibilità Pensione**: Fino a **€ 5.164,57** annui deducibili IRPEF (art. 51 TUIR).
                    """)

        # ── MICRO-AZIONI & MANUTENZIONE ─────────────────────────
        st.markdown('<hr class="argus-sidebar-divider">', unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Reset", key="sb_btn_reset_defaults", use_container_width=True, help="Ripristina i parametri di calcolo e workspace ai valori predefiniti istituzionali."):
                reset_settings_to_defaults(module=current_module)
        with col_btn2:
            if st.button("🧹 Svuota Cache", key="sb_btn_clean_cache_light", use_container_width=True, help="Invalida la cache di calcolo e memoria per forzare il ricalcolo immediato."):
                st.cache_data.clear()
                st.cache_resource.clear()
                try:
                    from core.cache_shield import clear_cache as clear_shield_cache
                    clear_shield_cache("history")
                except Exception:
                    pass
                try:
                    from core.workspace_manager import clear_session_cache
                    clear_session_cache()
                except Exception:
                    pass
                try:
                    st.toast("⚡ Cache dati e pricing svuotata con successo!", icon="🧹")
                except Exception:
                    pass
                st.rerun()


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
        init_settings_session_state(is_wealth_mode=is_wealth_mode)

        # Sincronizzazione globale unificata: Risk e Wealth condividono sempre lo stesso database attivo
        active_unified_db = st.session_state.get("db_name") or st.session_state.get("wealth_db_name") or st.session_state.get("risk_db_name") or "wealth"
        st.session_state.db_name = active_unified_db
        st.session_state.wealth_db_name = active_unified_db
        st.session_state.risk_db_name = active_unified_db

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
                target_db = st.session_state.sb_db_select
                st.session_state.db_name = target_db
                st.session_state.wealth_db_name = target_db
                st.session_state.risk_db_name = target_db
            elif "sb_custom_db" in st.session_state and st.session_state.sb_custom_db.strip():
                target_db = st.session_state.sb_custom_db.strip()
                st.session_state.db_name = target_db
                st.session_state.wealth_db_name = target_db
                st.session_state.risk_db_name = target_db

        if "sb_bench_select" in st.session_state:
            if st.session_state.sb_bench_select != "Custom...":
                st.session_state.benchmark = st.session_state.sb_bench_select
            elif "sb_custom_bench" in st.session_state and st.session_state.sb_custom_bench:
                st.session_state.benchmark = st.session_state.sb_custom_bench

        if st.session_state.get("sb_base_currency"):
            st.session_state.base_currency = st.session_state.sb_base_currency
        else:
            st.session_state.sb_base_currency = st.session_state.get("base_currency", "EUR")

        if st.session_state.get("sb_confidence_level") is not None:
            try:
                st.session_state.confidence_level = float(st.session_state.sb_confidence_level)
            except (ValueError, TypeError):
                st.session_state.confidence_level = 0.95
                st.session_state.sb_confidence_level = 0.95
        else:
            st.session_state.sb_confidence_level = float(st.session_state.get("confidence_level", 0.95))

        if st.session_state.get("sb_locale_select"):
            loc_val = str(st.session_state.sb_locale_select).lower()
            st.session_state.locale = "en" if ("en" in loc_val or "english" in loc_val) else "it"
        else:
            st.session_state.sb_locale_select = st.session_state.get("locale", "it")

        if st.session_state.get("sb_accounting_select"):
            acc_val = str(st.session_state.sb_accounting_select).lower()
            st.session_state.accounting_notation = "parentheses" if ("parentheses" in acc_val or "wall" in acc_val) else "standard"
        else:
            st.session_state.sb_accounting_select = st.session_state.get("accounting_notation", "standard")

        if st.session_state.get("sb_data_environment"):
            st.session_state.data_environment = st.session_state.sb_data_environment

        if st.session_state.get("sb_risk_method"):
            st.session_state.risk_estimation_method = st.session_state.sb_risk_method
        if st.session_state.get("sb_risk_lookback"):
            st.session_state.risk_lookback_period = st.session_state.sb_risk_lookback
        if st.session_state.get("sb_risk_decay") is not None:
            try:
                st.session_state.risk_decay_factor = float(st.session_state.sb_risk_decay)
            except (ValueError, TypeError):
                st.session_state.risk_decay_factor = 0.94

        if st.session_state.get("sb_wealth_horizon") is not None:
            try:
                st.session_state.wealth_planning_horizon_years = int(st.session_state.sb_wealth_horizon)
            except (ValueError, TypeError):
                st.session_state.wealth_planning_horizon_years = 25
        if st.session_state.get("sb_wealth_exp_return") is not None:
            try:
                st.session_state.wealth_expected_return_pct = float(st.session_state.sb_wealth_exp_return)
            except (ValueError, TypeError):
                st.session_state.wealth_expected_return_pct = 6.50
        if st.session_state.get("sb_wealth_inflation") is not None:
            try:
                st.session_state.wealth_inflation_rate_pct = float(st.session_state.sb_wealth_inflation)
            except (ValueError, TypeError):
                st.session_state.wealth_inflation_rate_pct = 2.00
        if st.session_state.get("sb_wealth_stress"):
            st.session_state.wealth_stress_scenario = st.session_state.sb_wealth_stress

        if st.session_state.get("sb_port_name"):
            st.session_state.portfolio_name = st.session_state.sb_port_name

        if st.session_state.get("sb_wb_needs") is not None:
            try:
                st.session_state.wealth_budget_needs_pct = float(st.session_state.sb_wb_needs)
            except (ValueError, TypeError):
                pass
        if st.session_state.get("sb_wb_wants") is not None:
            try:
                st.session_state.wealth_budget_wants_pct = float(st.session_state.sb_wb_wants)
            except (ValueError, TypeError):
                pass
        if st.session_state.get("sb_wb_savings") is not None:
            try:
                st.session_state.wealth_budget_savings_pct = float(st.session_state.sb_wb_savings)
            except (ValueError, TypeError):
                pass
        if st.session_state.get("sb_wealth_swr_input") is not None:
            try:
                st.session_state.wealth_fire_swr = float(st.session_state.sb_wealth_swr_input)
            except (ValueError, TypeError):
                st.session_state.wealth_fire_swr = 4.0
        if st.session_state.get("sb_wealth_age_input") is not None:
            try:
                st.session_state.wealth_target_retirement_age = int(st.session_state.sb_wealth_age_input)
            except (ValueError, TypeError):
                st.session_state.wealth_target_retirement_age = 67
        if st.session_state.get("sb_wealth_tax_regime"):
            st.session_state.wealth_tax_regime = st.session_state.sb_wealth_tax_regime

        from core.yield_curve import get_active_risk_free_rate
        if "rf_mode" not in st.session_state: st.session_state.rf_mode = "Auto (Live Market)"
        if "custom_rf_rate_pct" not in st.session_state: st.session_state.custom_rf_rate_pct = 2.75

        if st.session_state.get("sb_rf_mode"):
            st.session_state.rf_mode = st.session_state.sb_rf_mode
        if st.session_state.get("sb_custom_rf") is not None:
            try:
                st.session_state.custom_rf_rate_pct = float(st.session_state.sb_custom_rf)
            except (ValueError, TypeError):
                st.session_state.custom_rf_rate_pct = 2.75

        custom_rf_dec = (st.session_state.custom_rf_rate_pct / 100.0) if st.session_state.rf_mode != "Auto (Live Market)" else None
        active_rf_info = get_active_risk_free_rate(currency=st.session_state.base_currency, custom_override=custom_rf_dec)
        st.session_state.active_rf_rate = active_rf_info["rate"]
        st.session_state.active_rf_info = active_rf_info

        # Rileva cambio di database o offline_mode per invalidare cache e profili orfani
        curr_active_db = st.session_state.get("wealth_db_name" if is_wealth_mode else "risk_db_name", st.session_state.get("db_name"))
        curr_offline = bool(st.session_state.get("offline_mode", False))
        prev_active_db = st.session_state.get("_prev_active_db")
        prev_offline = st.session_state.get("_prev_offline_mode")

        if prev_active_db is not None and (prev_active_db != curr_active_db or prev_offline != curr_offline):
            st.session_state["wealth_active_portfolio_id"] = None
            st.session_state.pop("wealth_profile_selector_widget", None)
            st.session_state.pop("cf_profile_selector_widget", None)
            st.session_state.pop("wealth_active_snapshot", None)
            try:
                st.cache_data.clear()
            except Exception:
                pass

        st.session_state["_prev_active_db"] = curr_active_db
        st.session_state["_prev_offline_mode"] = curr_offline

        from core.ui_utils import get_display_portfolio_name
        port_label, has_port = get_display_portfolio_name()
        port_text_style = "color:#ffffff; font-weight:700;" if has_port else "color:#e3b341; font-style:italic; font-weight:600;"
        active_port_label = port_label if len(port_label) <= 26 else f"{port_label[:24]}..."

        if is_wealth_mode:
            w_needs = int(st.session_state.wealth_budget_needs_pct)
            w_wants = int(st.session_state.wealth_budget_wants_pct)
            w_savings = int(st.session_state.wealth_budget_savings_pct)
            w_rule_label = f"{w_needs}/{w_wants}/{w_savings}"
            is_offline = st.session_state.offline_mode
            w_status_badge = (
                '<span style="font-size:10px; font-weight:800; color:#ff9900; background:rgba(255, 153, 0, 0.15); padding: 2px 7px; border-radius:12px; letter-spacing:0.5px;">🟡 OFFLINE</span>'
                if is_offline else
                '<span style="font-size:10px; font-weight:800; color:#34d399; background:rgba(16, 185, 129, 0.20); padding: 2px 7px; border-radius:12px; letter-spacing:0.5px;">🟢 LIVE DB</span>'
            )
            w_db_label = "SQLite Locale" if is_offline else f"{st.session_state.db_name}"
            
            st.markdown(f"""
            <div style="background:rgba(16, 185, 129, 0.10); border:1px solid rgba(16, 185, 129, 0.35); border-radius:10px; padding: 10px 12px; margin-bottom: 8px; backdrop-filter: blur(10px);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:10px; font-weight:700; color:#8b949e; letter-spacing:0.6px; text-transform:uppercase;">Portale Attivo</span>
                    {w_status_badge}
                </div>
                <div style="font-size:11.5px; color:#ffffff; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom: 4px;">
                    🏛️ Wealth &amp; Personal Finance
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:10.5px; color:#8b949e; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 5px;">
                    <span>🗄️ <b style="color:#c9d1d9;">{w_db_label}</b></span>
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

        # ── 3. PARAMETRI ENGINE & IMPOSTAZIONI CONTESTUALI ────────────
        current_mod_key = "wealth" if is_wealth_mode else "risk"
        render_settings_sidebar(current_module=current_mod_key)

        # ── 4. PULIZIA CACHE & RESET SESSIONE ─────────────────────────
        if st.button("♻️ Svuota Cache & Reset Sessione", use_container_width=True, help="Elimina tutti i risultati di calcolo, la cache di mercato e i dati caricati, mantenendo le configurazioni di sistema e database."):
            # Rileva esattamente se l'utente si trova nel modulo Wealth o Risk
            cur_p = get_current_page_name()
            in_wealth = is_wealth_mode or any(w in cur_p for w in ["12_", "13_", "14_", "15_", "16_", "17_", "18_", "19_", "20_", "21_"])

            from core.workspace_manager import clear_session_cache
            from core.workspace_context import WorkspaceContext
            from core.archetype_manager import clear_unified_archetype

            # 1. Pulisce cache Streamlit, memoria L1 e persistenza L2
            clear_session_cache()
            st.cache_data.clear()
            st.cache_resource.clear()
            try:
                from core.cache_shield import clear_cache as clear_disk_cache
                clear_disk_cache()
            except Exception:
                pass

            # 2. Reset dominio e archetipi
            try:
                WorkspaceContext.get_current().flush_risk_domain()
            except Exception:
                pass
            try:
                clear_unified_archetype()
            except Exception:
                pass

            # 3. Pulisce Session State preservando configurazioni di sistema e database
            preserved_keys = {
                "splash_dismissed", "sidebar_expanded", "theme", "argus_portal_mode",
                "base_currency", "confidence_level", "locale", "accounting_notation",
                "data_environment", "offline_mode", "db_host", "db_port", "db_user",
                "db_pass", "db_name", "wealth_db_name", "risk_db_name",
                "risk_estimation_method", "risk_lookback_period", "risk_decay_factor",
                "benchmark", "rf_mode", "custom_rf_rate_pct",
                "wealth_planning_horizon_years", "wealth_expected_return_pct",
                "wealth_inflation_rate_pct", "wealth_tax_regime", "wealth_stress_scenario",
                "wealth_budget_preset", "wealth_budget_needs_pct", "wealth_budget_wants_pct",
                "wealth_budget_savings_pct", "wealth_fire_swr", "wealth_target_retirement_age",
                "wealth_pension_deduction_limit",
                "sb_base_currency", "sb_confidence_level", "sb_locale_select",
                "sb_accounting_select", "sb_data_environment", "sb_offline_toggle",
                "sb_db_host", "sb_db_port", "sb_db_user", "sb_db_pass", "sb_db_select",
                "sb_risk_method", "sb_risk_lookback", "sb_risk_decay", "sb_bench_select",
                "sb_rf_mode", "sb_wealth_horizon", "sb_wealth_exp_return", "sb_wealth_inflation",
                "sb_wealth_tax_regime", "sb_wealth_stress", "sb_wealth_preset_sel",
                "sb_wb_needs", "sb_wb_wants", "sb_wb_savings", "sb_wealth_swr_input", "sb_wealth_age_input"
            }

            for k in list(st.session_state.keys()):
                if k not in preserved_keys:
                    del st.session_state[k]

            st.session_state["session_cleared"] = True
            st.session_state["results"] = None
            st.session_state["portfolio_name"] = "Portafoglio Principale" if not in_wealth else "Master Wealth"
            st.session_state["active_portfolio_id"] = None
            st.session_state["selected_portfolio_id"] = None
            st.session_state["wealth_active_portfolio_id"] = None
            st.session_state["pipeline_done"] = False

            try:
                st.toast("⚡ Sessione e Cache completamente ripristinate!", icon="♻️")
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
