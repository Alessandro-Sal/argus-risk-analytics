"""
ARGUS — Risk Analytics & Quantitative Platform
Core Module: Sidebar & Institutional Navigation Rail v5.14.0
Provides top-level execution mode configuration, zero-recalc session persistence,
and direct hierarchical navigation with exact sub-tab binding.
"""

import streamlit as st
import os
import socket
import sys
from core.workspace_manager import ensure_session_restored


# Definizione dei moduli workspace: Control Room e Dashboard sono 1-click (senza tendina), gli altri hanno schede interne esatte
NAV_MODULES = [
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
        "title": "Analisi del Rischio",
        "icon": "🔴",
        "page_file": "pages/2_🔴_Analisi_Rischio.py",
        "key": "2_Analisi_Rischio",
        "has_subtabs": True,
        "tab_key": "risk_active_tab",
        "subtabs": [
            {"label": "📊 Profilo & Fama-French", "target": "📊 Profilo del Rischio & Fama-French"},
            {"label": "📉 VaR & Test Kupiec", "target": "📉 VaR, CVaR & Backtesting Kupiec"},
            {"label": "🔗 Correlazioni & ATR", "target": "🔗 Correlazioni, Liquidità & ATR Chandelier"},
            {"label": "🕵️ Anomalie ML", "target": "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)"}
        ]
    },
    {
        "title": "Modelli Quantitativi",
        "icon": "🔬",
        "page_file": "pages/3_🔬_Modelli_Quantitativi.py",
        "key": "3_Modelli_Quantitativi",
        "has_subtabs": True,
        "tab_key": "quant_active_tab",
        "subtabs": [
            {"label": "📊 Markowitz & Rebalancing", "target": "📊 Frontiera Markowitz & Rebalancing"},
            {"label": "🧬 Tail Copula & Kelly", "target": "🧬 Tail Copula & Kelly Sizing"},
            {"label": "🎲 Monte Carlo & Merton", "target": "🎲 Simulazioni Stocastiche (Monte Carlo & Merton)"},
            {"label": "🛡️ Hedging & Tail Risk", "target": "🛡️ Hedging Tattico & Tail Risk"},
            {"label": "🎯 Attribuzione Brinson", "target": "🎯 Attribuzione Brinson-Fachler"},
            {"label": "🏛️ Black-Litterman & ML", "target": "🏛️ Modelli Fattoriali, Black-Litterman & ML"}
        ]
    },
    {
        "title": "Posizioni & Fisco",
        "icon": "📋",
        "page_file": "pages/4_📋_Posizioni_e_Dettagli.py",
        "key": "4_Posizioni_e_Dettagli",
        "has_subtabs": True,
        "tab_key": "positions_active_tab",
        "subtabs": [
            {"label": "📋 Posizioni & Costi FIFO", "target": "📋 Posizioni Attive & Costi FIFO"},
            {"label": "🪦 Posizioni Chiuse & Graveyard", "target": "🪦 Posizioni Chiuse & Graveyard"},
            {"label": "📅 Proiezione Dividendi", "target": "📅 Proiezione Dividendi"},
            {"label": "💰 Ottimizzazione Fiscale", "target": "💰 Ottimizzazione Fiscale (TUIR Art. 67)"},
            {"label": "⚡ Liquidità Almgren-Chriss", "target": "⚡ Liquidità Almgren-Chriss"}
        ]
    },
    {
        "title": "Valutazione Aziendale",
        "icon": "🏛️",
        "page_file": "pages/5_🏛️_Valutazione_Aziendale.py",
        "key": "5_Valutazione_Aziendale",
        "has_subtabs": True,
        "tab_key": "val_segmented_tab",
        "subtabs": [
            {"label": "🏛️ Fair Value & Consensus", "target": "🏛️ Fair Value & Consensus Analisti"},
            {"label": "💼 Private Equity Waterfall", "target": "💼 Private Equity & Waterfall"},
            {"label": "📊 Altman Z & DuPont", "target": "📊 Bilanci & Solvibilità (Altman & DuPont)"},
            {"label": "🧮 Intrinseco DCF MC", "target": "🧮 Valutazione Intrinseca DCF Monte Carlo"}
        ]
    },
    {
        "title": "Stress Testing",
        "icon": "🌪️",
        "page_file": "pages/6_🌪️_Stress_Testing.py",
        "key": "6_Stress_Testing",
        "has_subtabs": True,
        "tab_key": "stress_active_tab",
        "subtabs": [
            {"label": "⚡ Matrice MSCI Barra", "target": "⚡ Matrice Comparativa MSCI Barra"},
            {"label": "🏛️ Scenari Storici", "target": "🏛️ Analisi Scenari Storici Dettagliata"},
            {"label": "🛠️ Simulatore What-if", "target": "🛠️ Simulatore What-if Custom"}
        ]
    },
    {
        "title": "Analisi Temporale",
        "icon": "📊",
        "page_file": "pages/7_📊_Analisi_Temporale.py",
        "key": "7_Analisi_Temporale",
        "has_subtabs": True,
        "tab_key": "time_active_tab",
        "subtabs": [
            {"label": "📈 Serie Storiche", "target": "📈 Serie Storiche Temporali"},
            {"label": "⚖️ Confronto Side-by-Side", "target": "⚖️ Confronto Affiancato (Side-by-Side)"},
            {"label": "🗃️ Registro Snapshot", "target": "🗃️ Registro Completo Snapshot Storici"}
        ]
    },
    {
        "title": "Analisi Tecnica",
        "icon": "📈",
        "page_file": "pages/8_📈_Analisi_Tecnica.py",
        "key": "8_Analisi_Tecnica",
        "has_subtabs": True,
        "tab_key": "tech_active_subtab",
        "subtabs": [
            {"label": "📊 Cockpit & Candlestick", "target": "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)"},
            {"label": "🧱 Volume Profile Dettaglio", "target": "🧱 Distribuzione Analitica Volume Profile"},
            {"label": "🚦 Confluence Score", "target": "🚦 Confluence Score & Pattern Recognition"},
            {"label": "⏳ Trend Multi-Timeframe", "target": "⏳ Trend Multi-Timeframe Alignment (1D / 1W)"}
        ]
    },
    {
        "title": "Screener Opportunità",
        "icon": "🔍",
        "page_file": "pages/9_🔍_Screener_Opportunita.py",
        "key": "9_Screener_Opportunita",
        "has_subtabs": True,
        "tab_key": "screener_segmented_subtab",
        "subtabs": [
            {"label": "🔍 Screener & Archetipi", "target": "🔍 Screener Multi-Fattoriale & Archetipi"},
            {"label": "🧪 Pre-Trade Simulator", "target": "🧪 Pre-Trade Portfolio Impact Simulator"},
            {"label": "📊 Radar Multi-Titolo", "target": "📊 Radar Comparativo Multi-Titolo"},
            {"label": "💾 Watchlist & Segnali", "target": "💾 Watchlist & Segnali Operativi"}
        ]
    }
]


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
    Esegue la navigazione senza errori:
    - Se siamo già sulla pagina di destinazione, esegue st.rerun() per riflettere il tab aggiornato.
    - Se siamo su un'altra pagina, esegue st.switch_page() gestendo i percorsi Streamlit.
    """
    cur_page = get_current_page_name()
    target_clean = os.path.basename(target_page_file)
    
    # Se siamo già sulla stessa pagina, basta il rerun
    if target_clean == cur_page or (("0_Control_Room" in target_clean) and ("0_Control_Room" in cur_page)):
        st.rerun()
        return

    # Percorsi di fallback per st.switch_page
    from core.workspace_manager import resolve_page_path
    resolved = resolve_page_path(target_page_file)
    
    variants = []
    if "0_Control_Room" in target_clean:
        variants = [
            "0_Control_Room.py",
            "src/0_Control_Room.py",
            resolved,
            target_page_file
        ]
    else:
        variants = [
            f"pages/{target_clean}",
            f"src/pages/{target_clean}",
            resolved,
            target_page_file,
            target_clean
        ]

    for v in variants:
        try:
            st.switch_page(v)
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
    """Renderizza la Sidebar Istituzionale v5.14.0 con Modalità Esecuzione in alto e Navigation Rail ad albero."""
    ensure_session_restored()

    current_page = get_current_page_name()

    with st.sidebar:
        # Header del Brand ARGUS
        st.markdown("""
        <div style="display:flex; align-items:center; gap: 8px; margin-bottom: 8px; padding: 2px 0;">
            <span style="font-size: 22px;">👁️</span>
            <div>
                <div style="font-size: 14.5px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; line-height: 1.1;">ARGUS</div>
                <div style="font-size: 9.5px; font-weight: 600; color: #8b949e; letter-spacing: 0.4px;">INSTITUTIONAL RISK INTELLIGENCE</div>
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

        with st.expander("⚙️ Parametri Engine & DB", expanded=False):
            st.toggle("Modalità Offline (Senza DB)", value=st.session_state.offline_mode, key="sb_offline_toggle")

            if not st.session_state.offline_mode:
                st.markdown('<div style="font-size:10px; font-weight:700; color:#ff9900; letter-spacing:0.5px; text-transform:uppercase; margin: 4px 0 2px;">Connessione MySQL</div>', unsafe_allow_html=True)
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
                current_db = st.session_state.get("db_name", "wealth")
                db_idx = db_options.index(current_db) if current_db in ["wealth", "investment_risk_bi"] else db_options.index("Custom...")
                sel_db = st.selectbox("Database Schema", db_options, index=db_idx, key="sb_db_select")
                if sel_db == "Custom...":
                    custom_db = st.text_input("Nome DB Custom", value="" if current_db in ["wealth", "investment_risk_bi"] else current_db, key="sb_custom_db").strip()
                    if custom_db:
                        st.session_state.db_name = custom_db
            else:
                st.info("☁️ **Modalità In-Memory**: i calcoli avvengono in RAM/Cache senza connessione MySQL.")

            st.markdown('<div style="font-size:10px; font-weight:700; color:#ff9900; letter-spacing:0.5px; text-transform:uppercase; margin: 8px 0 2px;">Profilo & Benchmark</div>', unsafe_allow_html=True)
            st.text_input("Nome Portafoglio", value=st.session_state.portfolio_name, key="sb_port_name")
            
            col_curr, col_bench = st.columns([1.1, 1.9])
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

        st.markdown('<div class="sidebar-section-header" style="margin-top: 18px; margin-bottom: 8px; font-size: 10px; font-weight: 800; color: #8b949e; text-transform: uppercase; letter-spacing: 0.8px;">NAVIGAZIONE WORKSPACE</div>', unsafe_allow_html=True)

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

        # ── 2. RENDERING MODULI NAVIGAZIONE ─────────────────────────────
        for mod in NAV_MODULES:
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
                                st.session_state["global_target_subtab"] = sub["target"]
                            switch_to_page(mod["page_file"])

        st.divider()

        # ── 3. PULIZIA CACHE & RESET SESSIONE ─────────────────────────
        if st.button("♻️ Svuota Cache & Reset Sessione", use_container_width=True):
            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]
            st.session_state["session_cleared"] = True
            modules_to_reload = [m for m in sys.modules if m.startswith('core.')]
            for m in modules_to_reload:
                try:
                    del sys.modules[m]
                except Exception:
                    pass
            switch_to_page("0_Control_Room.py")

        if st.button("👁️ Schermata di Avvio (Splash)", key="btn_sidebar_show_splash", use_container_width=True):
            st.session_state["splash_dismissed"] = False
            try:
                st.switch_page("0_Control_Room.py")
            except Exception:
                st.rerun()

        st.markdown("""
        <div style="text-align: center; padding: 10px 0 2px; border-top: 1px solid rgba(255,255,255,0.06); margin-top: 10px;">
            <div style="font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 0.5px;">ARGUS RISK INTELLIGENCE</div>
            <div style="font-size: 10px; font-weight: 600; color: #ff9900; margin-top: 2px;">Versione 5.15.0 Institutional Engine</div>
        </div>
        """, unsafe_allow_html=True)
