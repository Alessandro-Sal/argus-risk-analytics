import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.title("👁️ ARGUS\nRisk Analytics")
        st.caption("Risk Intelligence & Portfolio Analytics")
        
        st.divider()
        st.subheader("⚙️ Modalità di Esecuzione")
        
        # Inizializza lo stato se non esiste
        if "offline_mode" not in st.session_state: st.session_state.offline_mode = False
        import os
        import socket
        
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

        if "db_host" not in st.session_state: st.session_state.db_host = os.getenv("STREAMLIT_DB_HOST", "localhost")
        if "db_port" not in st.session_state: st.session_state.db_port = _detect_default_port(st.session_state.db_host, 3306)
        if "db_user" not in st.session_state: st.session_state.db_user = os.getenv("STREAMLIT_DB_USER", "root")
        if "db_pass" not in st.session_state: st.session_state.db_pass = os.getenv("STREAMLIT_DB_PASS", "root")
        if "db_name" not in st.session_state: st.session_state.db_name = os.getenv("STREAMLIT_DB_NAME", "investment_risk_bi")
        if "portfolio_name" not in st.session_state: st.session_state.portfolio_name = "My Portfolio"
        if "run_name" not in st.session_state: st.session_state.run_name = ""
        if "benchmark" not in st.session_state: st.session_state.benchmark = "SPY"

        offline_mode = st.toggle("Modalità Offline (In-Memory)", value=st.session_state.offline_mode, help="Analizza il portafoglio senza connetterti al database. I dati andranno persi alla chiusura.")
        st.session_state.offline_mode = offline_mode

        if not offline_mode:
            with st.expander("🔗 Connessione MySQL & Database", expanded=False):
                db_host = st.text_input("Host", value=st.session_state.db_host)
                db_port = st.number_input("Port", value=st.session_state.db_port, step=1)
                db_user = st.text_input("User", value=st.session_state.db_user)
                db_pass = st.text_input("Password", type="password", value=st.session_state.db_pass)
                
                # Selezione Database Target (investment_risk_bi, wealth, Custom...)
                db_options = ["investment_risk_bi", "wealth", "Custom..."]
                current_db = st.session_state.get("db_name", "investment_risk_bi")
                if current_db in ["investment_risk_bi", "wealth"]:
                    db_idx = db_options.index(current_db)
                else:
                    db_idx = db_options.index("Custom...")

                selected_db = st.selectbox("Database Target", db_options, index=db_idx, help="Seleziona il database MySQL di destinazione: investment_risk_bi (standard), wealth (Google Sheets), o Custom.")
                if selected_db == "Custom...":
                    db_name = st.text_input("Nome Database Custom", value="" if current_db in ["investment_risk_bi", "wealth"] else current_db).strip()
                    if not db_name:
                        db_name = "investment_risk_bi"
                else:
                    db_name = selected_db

                st.session_state.db_host = db_host
                st.session_state.db_port = db_port
                st.session_state.db_user = db_user
                st.session_state.db_pass = db_pass
                st.session_state.db_name = db_name
        else:
            st.info("☁️ **Modalità Offline attiva.**\nSalvataggio su database disabilitato.")

        st.divider()
        st.subheader("📋 Parametri Portafoglio")
        portfolio_name = st.text_input("Nome portafoglio", value=st.session_state.portfolio_name)
        run_name = st.text_input("Nome Analisi (opzionale)", value=st.session_state.run_name)
        
        bench_options = ["SPY", "QQQ", "VWRL.L", "^GSPC", "^STOXX50E", "VWCE.MI", "URTH", "BTC-USD", "Custom..."]
        current_benchmark = st.session_state.get("benchmark", "SPY")
        
        if current_benchmark in bench_options[:-1]:
            default_idx = bench_options.index(current_benchmark)
        else:
            default_idx = bench_options.index("Custom...")
            
        selected_bench = st.selectbox(
            "Benchmark", 
            bench_options, 
            index=default_idx, 
            help="L'indice di mercato usato per calcolare l'Alpha e il Beta del tuo portafoglio."
        )
        
        if selected_bench == "Custom...":
            custom_ticker = st.text_input(
                "Inserisci Ticker Benchmark Custom (Yahoo Finance)", 
                value="" if current_benchmark in bench_options[:-1] else current_benchmark,
                help="Inserisci un ticker valido di Yahoo Finance, es. ^IXIC (Nasdaq) o IWDA.AS (MSCI World)"
            ).strip().upper()
            benchmark = custom_ticker if custom_ticker else "SPY"
        else:
            benchmark = selected_bench
        
        st.session_state.portfolio_name = portfolio_name
        st.session_state.run_name = run_name
        st.session_state.benchmark = benchmark

        base_currency = st.selectbox(
            "Valuta Base Portafoglio", 
            ["EUR", "USD", "GBP", "CHF"], 
            index=["EUR", "USD", "GBP", "CHF"].index(st.session_state.get("base_currency", "EUR")),
            help="La valuta di riferimento in cui convertire tutti i valori e i PnL del portafoglio."
        )
        st.session_state.base_currency = base_currency

        ui_theme = st.selectbox(
            "Tema Visuale Dashboard",
            ["Midnight Obsidian", "Cyberpunk Neon", "Emerald Wealth"],
            index=["Midnight Obsidian", "Cyberpunk Neon", "Emerald Wealth"].index(st.session_state.get("ui_theme", "Midnight Obsidian")),
            help="Personalizza l'estetica visiva e la palette di colori dell'interfaccia."
        )
        st.session_state.ui_theme = ui_theme




        st.divider()
        st.subheader("🧹 Manutenzione")
        if st.button("♻️ Svuota Cache", help="Usa questo pulsante se i dati sembrano bloccati o se hai aggiornato i file interni (svuota cache di memoria e riavvia)"):
            st.cache_data.clear()
            # Clear Python module cache to force reload of core modules (like degiro)
            import sys
            modules_to_reload = [m for m in sys.modules if m.startswith('core.')]
            for m in modules_to_reload:
                del sys.modules[m]
            st.success("Cache svuotata con successo!")
            st.rerun()

        st.divider()
        st.caption("ARGUS v2.0 · Risk Intelligence Platform")
