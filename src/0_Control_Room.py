# ============================================================
# 0_Control_Room.py (Main Entry Point)
# ARGUS Risk Analytics Platform — Control Room
# ============================================================

import sys
from pathlib import Path

# Ensure root directory is in sys.path for 'core' module imports
_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

import streamlit as st
import pandas as pd
from core.validator import validate_csv
from core.fetcher import fetch_and_store, get_engine
from core.risk_engine import compute_risk
from core.db_exporter import save_snapshot_to_db
import importlib
import core.ui_utils
importlib.reload(core.ui_utils)
from core.ui_utils import inject_custom_css, section, metric_card, fmt_eur, fmt_pct, render_workflow_stepper, render_command_bar, render_validation_report
import datetime

# ── Config pagina ────────────────────────────────────────────

st.set_page_config(
    page_title="Control Room | ARGUS Risk Analytics",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# ── Sidebar ──────────────────────────────────────────────────

from core.sidebar import render_sidebar
render_sidebar()

# Fetch parameters from session_state
offline_mode = st.session_state.offline_mode
db_host = st.session_state.db_host
db_port = st.session_state.db_port
db_user = st.session_state.db_user
db_pass = st.session_state.db_pass
db_name = st.session_state.db_name
portfolio_name = st.session_state.portfolio_name
run_name = st.session_state.run_name
benchmark = st.session_state.benchmark

def get_db_engine(user, password, host, port, db):
    return get_engine(user, password, host, port, db)

def get_analysis_history(engine):
    from sqlalchemy import text as sqlt
    try:
        with engine.begin() as conn:
            res = conn.execute(sqlt("SHOW TABLES LIKE 'portfolio_snapshots'")).fetchone()
            if not res:
                return []
            
            rows = conn.execute(sqlt("""
                SELECT s.run_id, s.run_name, s.calc_date, p.name as port_name, s.portfolio_id, s.cagr_pct, s.sharpe_ratio
                FROM portfolio_snapshots s
                JOIN portfolios p ON s.portfolio_id = p.portfolio_id
                ORDER BY s.calc_date DESC
                LIMIT 50
            """)).fetchall()
            return rows
    except Exception as e:
        import streamlit as st
        st.error(f"Errore caricamento storico: {e}")
        return []

# ── Main layout ──────────────────────────────────────────────

st.title("🎛️ Control Room & Data Ingestion")
st.caption("Centro di controllo per l'ingestione dati, la validazione CSV, la gestione del database ed il lancio del motore di rischio.")
st.divider()

engine_sidebar = None
db_error = None
try:
    engine_sidebar = get_db_engine(db_user, db_pass, db_host, int(db_port), db_name)
except Exception as e:
    db_error = e

# ── SEZIONE: Storico Analisi (Recall) ────────────────────────
with st.expander(f"📚 Richiama uno Storico Analisi dal Database ({st.session_state.get('db_name', 'investment_risk_bi')})", expanded=not st.session_state.get("pipeline_done")):
    if offline_mode:
        st.info("ℹ️ **Modalità Offline Attiva.** Lo storico delle analisi salvate nel Database non è disponibile in questa modalità. Disattiva la modalità offline nella barra laterale per abilitare il salvataggio ed il richiamo delle analisi storiche.")
    elif db_error:
        st.warning("⚠️ **Accesso al Database richiesto.**\n\nPer abilitare lo Storico Analisi e salvare i risultati, inserisci la tua password di MySQL nella barra laterale a sinistra e premi Invio.")
    elif engine_sidebar:
        history = get_analysis_history(engine_sidebar)
        if not history:
            st.info(f"Nessuna analisi salvata nel Database '{st.session_state.get('db_name', 'investment_risk_bi')}'. Carica un CSV e avvia la pipeline per crearne una!")
        else:
            st.markdown(f"Seleziona un'analisi salvata nel database **`{st.session_state.get('db_name', 'investment_risk_bi')}`** per ricaricarla istantaneamente nella Dashboard senza ri-elaborare il CSV.")
            
            history_rows = []
            options_map = {}
            for r in history:
                dt_str = r.calc_date.strftime("%Y-%m-%d %H:%M")
                n_str = r.run_name if getattr(r, 'run_name', None) else "Analisi Standard"
                cagr_val = f"{r.cagr_pct:+.2f}%" if r.cagr_pct is not None else "N/A"
                sharpe_val = f"{r.sharpe_ratio:.2f}" if r.sharpe_ratio is not None else "N/A"
                
                history_rows.append({
                    "Data & Ora": dt_str,
                    "Portafoglio": r.port_name,
                    "Nome Run": n_str,
                    "CAGR %": cagr_val,
                    "Sharpe Ratio": sharpe_val,
                    "Run ID": r.run_id
                })
                
                label = f"📅 {dt_str} | 💼 {r.port_name} ({n_str}) | 📈 CAGR: {cagr_val} | ⚡ Sharpe: {sharpe_val} | ID: {r.run_id}"
                options_map[label] = r
            
            df_hist = pd.DataFrame(history_rows)
            st.dataframe(df_hist, use_container_width=True, height=160)
            
            scelta = st.selectbox("🎯 Seleziona l'Analisi da Ricaricare:", list(options_map.keys()))
            
            col_load, col_del = st.columns([3, 1])
            with col_load:
                btn_load = st.button("🔄 Carica Analisi Selezionata in Dashboard", type="primary", use_container_width=True)
            with col_del:
                btn_del = st.button("🗑️ Elimina Questa Singola Analisi", type="secondary", use_container_width=True)
            
            if btn_load:
                sel_row = options_map[scelta]
                with st.spinner(f"Ricalcolo rapido dell'analisi {sel_row.run_id}..."):
                    results = compute_risk(sel_row.portfolio_id, engine_sidebar, benchmark_ticker=benchmark)
                    st.session_state["pipeline_done"]  = True
                    st.session_state["portfolio_id"]   = sel_row.portfolio_id
                    st.session_state["portfolio_name"] = sel_row.port_name
                    st.session_state["engine"]         = engine_sidebar
                    st.session_state["results"]        = results
                    st.session_state["run_id"]         = sel_row.run_id
                    st.session_state["fetch_report"]   = {"success": [], "skipped": [], "rows_written": 0, "errors": []}
                st.success(f"Analisi {sel_row.run_id} ricaricata con successo!")
                try:
                    st.switch_page("pages/1_📈_Dashboard_Generale.py")
                except Exception:
                    st.rerun()
            
            if btn_del:
                sel_row = options_map[scelta]
                from sqlalchemy import text as sqlt
                with engine_sidebar.begin() as conn:
                    snap_id = conn.execute(sqlt("SELECT snapshot_id FROM portfolio_snapshots WHERE run_id = :rid"), {"rid": sel_row.run_id}).scalar()
                    if snap_id:
                        conn.execute(sqlt("DELETE FROM snapshot_positions WHERE snapshot_id = :sid"), {"sid": snap_id})
                        conn.execute(sqlt("DELETE FROM portfolio_snapshots WHERE snapshot_id = :sid"), {"sid": snap_id})
                    
                    rem_snaps = conn.execute(sqlt("SELECT COUNT(*) FROM portfolio_snapshots WHERE portfolio_id = :pid"), {"pid": sel_row.portfolio_id}).scalar()
                    rem_tx = conn.execute(sqlt("SELECT COUNT(*) FROM transactions WHERE portfolio_id = :pid"), {"pid": sel_row.portfolio_id}).scalar()
                    if rem_snaps == 0 and rem_tx == 0:
                        conn.execute(sqlt("DELETE FROM portfolios WHERE portfolio_id = :pid"), {"pid": sel_row.portfolio_id})

                st.success(f"Singola analisi `{sel_row.run_id}` eliminata con successo dal Database `{st.session_state.get('db_name')}`!")
                st.rerun()

st.divider()

# ── BANNER SESSIONE ATTIVA & RESET ──────────────────────────
if st.session_state.get("pipeline_done"):
    col_act1, col_act2 = st.columns([3, 1.2])
    with col_act1:
        st.info(f"📌 **Analisi Attiva in Sessione**: **{st.session_state.get('portfolio_name', 'Portafoglio')}** (Run ID: `{st.session_state.get('run_id', 'N/A')}`). I tuoi dati sono pronti nelle schede della Dashboard.")
    with col_act2:
        if st.button("🔄 Reset / Carica Nuova Analisi", type="secondary", use_container_width=True, help="Azzera lo stato corrente della sessione per consentire il caricamento di un nuovo file CSV."):
            for key in ["pipeline_done", "portfolio_id", "results", "run_id", "fetch_report"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# ── WORKFLOW STEPPER ─────────────────────────────────────────

current_wf_step = 1
if st.session_state.get("pipeline_done"):
    current_wf_step = 3

# ── STEP 1: Upload CSV ───────────────────────────────────────

section("① Carica il file CSV")

data_source = st.radio(
    "Sorgente Dati",
    options=["CSV Standard (Template)", "Degiro (Export Transazioni)"],
    horizontal=True,
    help="Scegli 'Degiro' se stai caricando il file Transazioni.csv nativo scaricato dal broker."
)

col_upload, col_template = st.columns([3, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Trascina qui il tuo file CSV",
        type=["csv"],
        help="Carica il file in base alla sorgente selezionata."
    )

with col_template:
    template_csv = """tx_date,ticker,tx_type,quantity,price,currency,fees,asset_class,notes
2021-03-15,AAPL,buy,10,121.03,USD,1.50,stock,Esempio acquisto
2021-06-01,VWRL.L,buy,5,89.20,GBP,0.00,etf,
2022-01-10,BTC-USD,buy,0.05,41800.00,USD,2.00,crypto,
2022-08-20,AAPL,sell,5,162.50,USD,1.50,stock,Presa profitto
2023-03-01,AAPL,dividend,0,0.23,USD,0.00,stock,Dividendo Q1"""
    if data_source == "CSV Standard (Template)":
        st.download_button(
            "⬇️ Scarica template",
            data=template_csv,
            file_name="template_portfolio.csv",
            mime="text/csv",
            use_container_width=True
        )

if uploaded_file and not st.session_state.get("pipeline_done"):
    current_wf_step = 2

render_workflow_stepper(current_wf_step)

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file, dtype=str)

    if data_source == "Degiro (Export Transazioni)":
        from core.adapters.degiro import parse_degiro_transactions
        try:
            with st.spinner("⏳ Analisi ISIN tramite Yahoo Finance in corso... (potrebbe richiedere fino a 30 secondi per portafogli grandi)"):
                df_raw = parse_degiro_transactions(df_raw)
            st.success("✅ File Degiro riconosciuto e convertito con successo.")
        except Exception as e:
            st.error(f"Errore nel parsing del file Degiro: {e}")
            st.stop()

    section("② Validazione Dati & Data Health HUD")
    df_clean, report = validate_csv(df_raw)

    render_validation_report(report)

    s = report["stats"]
    
    # Data Health Summary Grid
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Righe Valide", f"{s['total_rows']}", help_text="Numero totale di transazioni valide nel file.")
    with c2: metric_card("Ticker Unici", f"{len(s['tickers'])}", help_text="Numero di asset finanziari distinti identificati.")
    with c3: metric_card("Valute Rilevate", f"{len(s['currencies'])}", help_text="Valute delle transazioni (EUR, USD, GBP, ecc.).")
    with c4: metric_card("Data Inizio", f"{s['date_range'][0]}", help_text="Data della prima transazione a storico.")
    with c5: metric_card("Data Fine", f"{s['date_range'][1]}", help_text="Data dell'ultima transazione a storico.")

    with st.expander("🔍 Ispeziona Anteprima Dati Validati", expanded=False):
        df_display = df_clean.copy()
        if "tx_date" in df_display.columns:
            df_display["tx_date"] = df_display["tx_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(df_display, use_container_width=True, height=220)

    import re
    import json
    import os
    import requests
    
    @st.cache_data(show_spinner=False)
    def fetch_yahoo_ticker_for_isin(isin: str) -> str:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            data = res.json()
            quotes = data.get('quotes', [])
            if quotes:
                return quotes[0].get('symbol', "")
        except Exception:
            pass
        return ""

    ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
    unmapped_isins = [t for t in s["tickers"] if ISIN_PATTERN.match(t)]
    
    loaded_mapping = {}
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)
                loaded_mapping = config_data.get("ticker_mapping", {})
        except Exception:
            pass

    with st.expander("⚙️ Gestisci Mappatura ISIN salvata (Verifica o Modifica)"):
        if loaded_mapping:
            st.info("Qui puoi verificare ed eventualmente correggere le mappature salvate in precedenza.")
            saved_mapping_df = pd.DataFrame([{"ISIN": k, "Yahoo Ticker": v} for k, v in loaded_mapping.items()])
            edited_saved_mapping_df = st.data_editor(saved_mapping_df, use_container_width=True, hide_index=True, num_rows="dynamic", key="saved_mapping")
            
            if st.button("💾 Aggiorna Mappature Esistenti", key="update_saved_mapping"):
                updated_mapping = dict(zip(edited_saved_mapping_df["ISIN"], edited_saved_mapping_df["Yahoo Ticker"]))
                updated_mapping = {k: v.strip().upper() for k, v in updated_mapping.items() if str(k).strip() and str(v).strip()}
                
                config_data = {}
                if os.path.exists("config.json"):
                    with open("config.json", "r") as f:
                        config_data = json.load(f)
                        
                config_data["ticker_mapping"] = updated_mapping
                with open("config.json", "w") as f:
                    json.dump(config_data, f, indent=4)
                st.success("Mappatura aggiornata con successo!")
                st.rerun()
        else:
            st.write("Nessuna mappatura salvata finora.")

    if unmapped_isins:
        missing_isins = [i for i in unmapped_isins if not loaded_mapping.get(i)]
        
        if missing_isins:
            st.warning(f"⚠️ Sono stati rilevati {len(missing_isins)} nuovi ISIN non mappati ai ticker di Yahoo Finance. Senza mappatura l'app userà solo il prezzo d'acquisto (niente dati storici).")
            st.info("I Ticker suggeriti sono stati trovati automaticamente su Yahoo Finance. Controllali, modificali se preferisci un'altra borsa (es. .MI per Milano) e poi salva.")
            
            mapping_data = []
            for isin in missing_isins:
                nome_prodotto = df_clean.loc[df_clean["ticker"] == isin, "notes"].dropna().unique()
                nome = nome_prodotto[0] if len(nome_prodotto) > 0 else "Sconosciuto"
                suggerimento = fetch_yahoo_ticker_for_isin(isin)
                
                mapping_data.append({
                    "ISIN": isin, 
                    "Nome Prodotto": nome,
                    "Yahoo Ticker": suggerimento
                })
                
            mapping_df = pd.DataFrame(mapping_data)
            edited_mapping_df = st.data_editor(mapping_df, use_container_width=True, hide_index=True, key="new_mapping")
            
            if st.button("💾 Salva Nuova Mappatura", type="primary", key="save_new_mapping"):
                new_mapping = dict(zip(edited_mapping_df["ISIN"], edited_mapping_df["Yahoo Ticker"]))
                new_mapping = {k: v.strip().upper() for k, v in new_mapping.items() if v and v.strip()}
                
                if new_mapping:
                    config_data = {}
                    if os.path.exists("config.json"):
                        try:
                            with open("config.json", "r") as f:
                                config_data = json.load(f)
                        except Exception:
                            pass
                            
                    if "ticker_mapping" not in config_data:
                        config_data["ticker_mapping"] = {}
                        
                    config_data["ticker_mapping"].update(new_mapping)
                    
                    with open("config.json", "w") as f:
                        json.dump(config_data, f, indent=4)
                        
                    st.success("Mappatura salvata! Verrà applicata all'avvio della pipeline.")
                    st.rerun()

    section("③ Elaborazione Dati e Calcolo Rischio")

    col_btn, col_auto = st.columns([3, 2])
    with col_btn:
        run_fetch = st.button("🚀 Avvia Analisi Quantitativa ARGUS", type="primary", use_container_width=True)
    with col_auto:
        auto_run = st.checkbox("⚡ Esecuzione Automatica", value=True, help="Esegue automaticamente l'analisi non appena il file CSV viene caricato e validato.")

    should_run = run_fetch or (auto_run and not st.session_state.get("pipeline_done"))

    if should_run or st.session_state.get("pipeline_done"):
        if should_run:
            if not offline_mode:
                try:
                    engine = get_db_engine(db_user, db_pass, db_host, int(db_port), db_name)
                except Exception as e:
                    st.error(f"Connessione MySQL fallita: {e}")
                    st.stop()
            else:
                engine = None
                portfolio_id = 999999

            with st.spinner("⏳ Sincronizzazione dati di mercato (Yahoo Finance) e calcolo metriche di rischio..."):
                if not offline_mode:
                    from sqlalchemy import text as sqlt
                    with engine.begin() as conn:
                        conn.execute(sqlt("""
                            INSERT INTO portfolios (name, owner, base_currency, created_at)
                            VALUES (:name, 'streamlit_user', :base_currency, NOW())
                        """), {
                            "name": portfolio_name,
                            "base_currency": st.session_state.get("base_currency", "EUR")
                        })
                        portfolio_id = conn.execute(sqlt("SELECT LAST_INSERT_ID()")).scalar()

                        for _, row in df_clean.iterrows():
                            conn.execute(sqlt("""
                                INSERT INTO assets (ticker, name, asset_class, currency)
                                VALUES (:ticker, :ticker, :asset_class, :currency)
                                ON DUPLICATE KEY UPDATE name=VALUES(name), asset_class=VALUES(asset_class), currency=VALUES(currency)
                            """), {
                                "ticker":      row["ticker"],
                                "asset_class": "stock" if pd.isna(row.get("asset_class")) else row.get("asset_class"),
                                "currency":    row["currency"],
                            })
                            asset_id = conn.execute(
                                sqlt("SELECT asset_id FROM assets WHERE ticker=:t"),
                                {"t": row["ticker"]}
                            ).scalar()

                            conn.execute(sqlt("""
                                INSERT INTO transactions
                                    (portfolio_id, asset_id, tx_date, tx_type,
                                     quantity, price, currency, fees, notes)
                                VALUES
                                    (:pid, :aid, :tx_date, :tx_type,
                                     :quantity, :price, :currency, :fees, :notes)
                            """), {
                                "pid":      portfolio_id,
                                "aid":      asset_id,
                                "tx_date":  str(row["tx_date"])[:10],
                                "tx_type":  row["tx_type"],
                                "quantity": float(row["quantity"]),
                                "price":    float(row["price"]),
                                "currency": row["currency"],
                                "fees":     0.0 if pd.isna(row.get("fees")) else float(row["fees"]),
                                "notes":    None if pd.isna(row.get("notes")) else row.get("notes"),
                            })

                if offline_mode:
                    fetch_report, df_tx, df_prices = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
                    results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark, df_tx=df_tx, df_prices=df_prices)
                else:
                    fetch_report = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
                    results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark)

                timestamp_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                run_id = f"ANL-{timestamp_str}"
                
                if not offline_mode:
                    save_snapshot_to_db(results, engine, portfolio_id, run_id, run_name)

                st.session_state["pipeline_done"]  = True
                st.session_state["portfolio_id"]   = portfolio_id
                st.session_state["engine"]         = engine
                st.session_state["fetch_report"]   = fetch_report
                st.session_state["results"]        = results
                st.session_state["run_id"]         = run_id

        fr = st.session_state["fetch_report"]
        res = st.session_state.get("results", {})
        m = res.get("metrics", {})
        ret = m.get("returns", {})
        mk = m.get("market_risk", {})

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        
        # Summary Glass Card
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 14px; padding: 20px; margin-bottom: 20px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px;">
                <span style="font-size: 16px; font-weight:700; color:#ffffff;">🎉 Analisi Completata con Successo</span>
                <span class="argus-command-pill" style="border-color: rgba(63, 185, 80, 0.4); color: #3fb950;">RUN: {st.session_state.get('run_id', 'N/A')}</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 10px;">
                <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                    <div style="font-size:11px; color:#8b949e;">TICKER SCARICATI</div>
                    <div style="font-size:18px; font-weight:700; color:#3fb950;">{len(fr.get('success', []))}</div>
                </div>
                <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                    <div style="font-size:11px; color:#8b949e;">CAGR ANNUO</div>
                    <div style="font-size:18px; font-weight:700; color:#ffffff;">{ret.get('cagr_pct', 0.0):.2f}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                    <div style="font-size:11px; color:#8b949e;">SHARPE RATIO</div>
                    <div style="font-size:18px; font-weight:700; color:#ff9900;">{mk.get('sharpe_ratio', 0.0):.2f}</div>
                </div>
                <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                    <div style="font-size:11px; color:#8b949e;">MAX DRAWDOWN</div>
                    <div style="font-size:18px; font-weight:700; color:#f85149;">{mk.get('max_drawdown_pct', 0.0):.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if fr.get("errors"):
            for e in fr["errors"]:
                st.markdown(f'<div class="error-box">🔴 {e}</div>', unsafe_allow_html=True)

        col_nav1, col_nav2 = st.columns([3, 2])
        with col_nav1:
            if st.button("📈 APRI EXECUTIVE COCKPIT ➔", type="primary", use_container_width=True, key="go_to_dashboard"):
                try:
                    st.switch_page("pages/1_📈_Dashboard_Generale.py")
                except Exception:
                    st.info("Seleziona la pagina '1_📈_Dashboard_Generale' dal menu laterale a sinistra.")
