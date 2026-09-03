# ============================================================
# 0_Control_Room.py (Main Entry Point)
# ARGUS Risk Analytics & Wealth Ecosystem | Control Room v6.3.0
# ============================================================

import sys
from pathlib import Path

# Ensure root directory is in sys.path for 'core' module imports
_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

import streamlit as st

is_splash_active = not st.session_state.get("splash_dismissed", False)

st.set_page_config(
    page_title="Control Room | ARGUS Risk Analytics",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="collapsed" if is_splash_active else "expanded"
)

if is_splash_active:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"], [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    </style>
    """, unsafe_allow_html=True)


import pandas as pd
import numpy as np
import datetime
import json
import os
import re
import requests

from core.validator import validate_csv
from core.fetcher import fetch_and_store, get_engine
from core.risk_engine import compute_risk
from core.db_exporter import save_snapshot_to_db
import core.ui_utils
import core.duckdb_engine as duckdb_engine
import core.adapters.broker_hub as broker_hub
from core.ui_utils import (
    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_workflow_stepper,
    render_command_bar,
    render_validation_report,
    glossary_modal,
    render_info_modal,
    render_splash_screen,
    render_control_room_hero,
    get_display_portfolio_name,
    render_broker_hub_modal,
    render_duckdb_modal,
)
import core.multi_portfolio
from core.multi_portfolio import (
    save_portfolio_profile,
    list_saved_portfolio_profiles,
    load_portfolio_profile,
    delete_saved_portfolio_profile,
    compute_multi_portfolio_comparison,
    consolidate_multi_portfolios,
)
from core.diagnostics import (
    run_system_health_check,
    optimize_database_storage,
    clean_expired_cache_records,
    reindex_databases,
)
from core.cache_shield import clear_cache

inject_custom_css()

# ── Splash Screen (All'avvio) ─────────────────────────────────
if render_splash_screen():
    st.stop()

# ── Sidebar (Caricata solo dopo l'accesso al terminale) ───────
from core.sidebar import render_sidebar
render_sidebar()

# Fetch parameters safely from session_state
offline_mode = st.session_state.get("offline_mode", False)
db_host = st.session_state.get("db_host", "localhost")
try:
    db_port = int(st.session_state.get("db_port", 3306))
except Exception:
    db_port = 3306
db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_name = st.session_state.get("db_name", "investment_risk_bi")
portfolio_name = st.session_state.get("portfolio_name", "")
run_name = st.session_state.get("run_name", "")

benchmark = st.session_state.get("benchmark", "SPY")

# ── Funzioni di Supporto Database ─────────────────────────────

@st.cache_resource(show_spinner=False)
def get_db_engine(user, password, host, port, db):
    return get_engine(user=user, password=password, host=host, port=port, db=db)


def get_analysis_history(engine):
    """Recupera la lista degli snapshot storici salvati nel database per il richiamo rapido."""
    if engine is None:
        return []
    from sqlalchemy import text as sqlt
    try:
        with engine.connect() as conn:
            rows = conn.execute(sqlt("""
                SELECT 
                    s.snapshot_id,
                    s.calc_date,
                    s.run_id,
                    s.run_name,
                    s.portfolio_id,
                    p.name as port_name,
                    s.total_value,
                    s.cagr_pct,
                    s.sharpe_ratio,
                    s.max_drawdown_pct,
                    s.var_95_pct
                FROM portfolio_snapshots s
                JOIN portfolios p ON s.portfolio_id = p.portfolio_id
                ORDER BY s.calc_date DESC
                LIMIT 50
            """)).fetchall()
            return rows
    except Exception:
        return []

# ── Main layout Top ──────────────────────────────────────────

render_command_bar()
render_control_room_hero()

engine_sidebar = None
db_error = None
if not offline_mode:
    try:
        engine_sidebar = get_db_engine(db_user, db_pass, db_host, db_port, db_name)
    except Exception as e:
        db_error = e

# ── SEZIONE: Storico Analisi (Recall da Database) ────────────

with st.expander(f"📚 Storico Snapshot & Recall Analisi ({st.session_state.get('db_name', 'investment_risk_bi')})", expanded=not st.session_state.get("pipeline_done")):
    if offline_mode:
        st.info("ℹ️ **Modalità Offline Attiva.** Lo storico delle analisi salvate nel Database non è disponibile in questa modalità In-Memory. Disattiva la modalità offline nella barra laterale a sinistra per connetterti a MySQL e visualizzare lo storico.")
    elif db_error:
        st.warning(f"⚠️ **Accesso al Database non riuscito.**\n\nVerifica host, porta, utente e password nella barra laterale a sinistra per connetterti al Database `{db_name}`. Errore: `{db_error}`")
    elif engine_sidebar:
        history = get_analysis_history(engine_sidebar)
        if not history:
            st.info(f"Nessuna analisi salvata nel Database '{st.session_state.get('db_name', 'investment_risk_bi')}'. Carica un CSV, un Preset o sincronizza Google Sheets per salvare la prima analisi!")
        else:
            st.caption(f"Sfoglia gli snapshot salvati nel database **`{st.session_state.get('db_name', 'investment_risk_bi')}`** per ricaricarli istantaneamente nella Dashboard senza ri-elaborare i prezzi storici.")
            
            # ── BARRA DI RICERCA & FILTRI DINAMICI ──
            col_search, col_port_filter, col_sort = st.columns([2.2, 1.4, 1.4])
            
            with col_search:
                search_query = st.text_input(
                    "🔍 Cerca Analisi (Nome, Tipologia, Data, ID):",
                    placeholder="es. Crypto, Automatic, 2026-08, ANI...",
                    key="hist_search_query"
                ).strip().lower()
                
            unique_ports = sorted(list({r.port_name for r in history if r.port_name and str(r.port_name).strip()}))
            with col_port_filter:
                selected_port_filter = st.selectbox(
                    "💼 Filtra Portafoglio:",
                    options=["Tutti i Portafogli"] + unique_ports,
                    key="hist_port_filter"
                )
                
            with col_sort:
                sort_mode = st.selectbox(
                    "⚡ Ordina per:",
                    options=[
                        "📅 Più recenti",
                        "📅 Meno recenti",
                        "📈 CAGR (Decrescente)",
                        "⚡ Sharpe (Decrescente)",
                        "💰 Valore € (Decrescente)"
                    ],
                    key="hist_sort_mode"
                )

            # Applicazione filtri
            filtered_history = []
            for r in history:
                p_name = r.port_name if (r.port_name and str(r.port_name).strip()) else "Portafoglio Quantitativo"
                r_name = r.run_name if getattr(r, 'run_name', None) else "Analisi Standard"
                dt_str = r.calc_date.strftime("%Y-%m-%d %H:%M")
                
                # Filtro Portafoglio
                if selected_port_filter != "Tutti i Portafogli" and p_name != selected_port_filter:
                    continue
                    
                # Filtro Testuale
                if search_query:
                    search_corpus = f"{p_name} {r_name} {dt_str} {r.run_id}".lower()
                    if search_query not in search_corpus:
                        continue
                        
                filtered_history.append(r)

            # Ordinamento
            if sort_mode == "📅 Più recenti":
                filtered_history.sort(key=lambda x: x.calc_date, reverse=True)
            elif sort_mode == "📅 Meno recenti":
                filtered_history.sort(key=lambda x: x.calc_date, reverse=False)
            elif sort_mode == "📈 CAGR (Decrescente)":
                filtered_history.sort(key=lambda x: float(x.cagr_pct) if x.cagr_pct is not None else -999.0, reverse=True)
            elif sort_mode == "⚡ Sharpe (Decrescente)":
                filtered_history.sort(key=lambda x: float(x.sharpe_ratio) if x.sharpe_ratio is not None else -999.0, reverse=True)
            elif sort_mode == "💰 Valore € (Decrescente)":
                filtered_history.sort(key=lambda x: float(x.total_value) if getattr(x, 'total_value', None) is not None else -999.0, reverse=True)

            if not filtered_history:
                st.warning("🔍 Nessuna analisi salvata corrisponde ai filtri di ricerca impostati. Prova a reimpostare i criteri.")
            else:
                st.markdown(f"<div style='font-size: 11.5px; color: #8b949e; margin-bottom: 6px;'>🎯 Trovati <b>{len(filtered_history)}</b> snapshot su {len(history)} totali</div>", unsafe_allow_html=True)
                
                history_rows = []
                options_map = {}
                for r in filtered_history:
                    dt_str = r.calc_date.strftime("%Y-%m-%d %H:%M")
                    n_str = r.run_name if getattr(r, 'run_name', None) else "Analisi Standard"
                    tot_val = float(r.total_value) if getattr(r, 'total_value', None) is not None else 0.0
                    cagr_val = f"{float(r.cagr_pct):+.2f}%" if getattr(r, 'cagr_pct', None) is not None else "N/A"
                    sharpe_val = f"{float(r.sharpe_ratio):.2f}" if getattr(r, 'sharpe_ratio', None) is not None else "N/A"
                    max_dd_val = f"{float(r.max_drawdown_pct):.2f}%" if getattr(r, 'max_drawdown_pct', None) is not None else "N/A"
                    
                    p_name_display = r.port_name if (r.port_name and str(r.port_name).strip()) else "Portafoglio Quantitativo"
                    history_rows.append({
                        "Data Esecuzione": dt_str,
                        "Portafoglio": p_name_display,
                        "Tipologia": n_str,
                        "Valore (€)": tot_val,
                        "CAGR": cagr_val,
                        "Sharpe": sharpe_val,
                        "Max Drawdown": max_dd_val,
                        "Run ID": r.run_id
                    })
                    
                    # Etichetta formattata pulita con separatore punto centrale
                    label = f"{dt_str} · {p_name_display} · {n_str} (CAGR: {cagr_val} | Sharpe: {sharpe_val})"
                    options_map[label] = r
                
                df_hist = pd.DataFrame(history_rows)
                
                # Tabella riassuntiva formattata con selezione visiva
                st.dataframe(
                    df_hist.style.format({"Valore (€)": "€ {:,.2f}"}),
                    use_container_width=True,
                    height=160,
                    hide_index=True
                )
                
                scelta = st.selectbox(
                    "🎯 Seleziona l'Analisi da Ricaricare:",
                    options=list(options_map.keys()),
                    key="select_history_run",
                    help="Seleziona la sessione di calcolo da ripristinare nella Dashboard."
                )
                
                sel_row = options_map[scelta]
                sel_dt = sel_row.calc_date.strftime("%d/%m/%Y alle %H:%M")
                sel_port = sel_row.port_name if sel_row.port_name else "Portafoglio Quantitativo"
                sel_run_name = sel_row.run_name if sel_row.run_name else "Analisi Standard"
                sel_cagr = f"{float(sel_row.cagr_pct):+.2f}%" if sel_row.cagr_pct is not None else "N/A"
                sel_sharpe = f"{float(sel_row.sharpe_ratio):.2f}" if sel_row.sharpe_ratio is not None else "N/A"
                sel_dd = f"{float(sel_row.max_drawdown_pct):.2f}%" if getattr(sel_row, 'max_drawdown_pct', None) is not None else "N/A"
                sel_val = f"€ {float(sel_row.total_value):,.2f}" if getattr(sel_row, 'total_value', None) is not None else "N/A"

                # ── CARD DI ANTEPRIMA SNAPSHOT SELEZIONATO ──
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 18px; margin: 10px 0 16px 0; box-shadow: 0 4px 16px rgba(0,0,0,0.25);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <div style="font-weight: 700; font-size: 14.5px; color: #ffffff; display: flex; align-items: center; gap: 8px;">
                            <span>💼 {sel_port}</span>
                            <span style="font-size: 11px; color: #8b949e; font-weight: normal;">({sel_run_name})</span>
                        </div>
                        <span style="background: rgba(88, 166, 255, 0.12); color: #58a6ff; border: 1px solid rgba(88, 166, 255, 0.3); border-radius: 6px; padding: 2px 8px; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 600;">
                            ID: {sel_row.run_id}
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; text-align: center;">
                        <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04);">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600; text-transform: uppercase;">Controvalore</div>
                            <div style="font-size: 14px; font-weight: 800; color: #ffffff; font-family: 'JetBrains Mono', monospace;">{sel_val}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04);">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600; text-transform: uppercase;">CAGR %</div>
                            <div style="font-size: 14px; font-weight: 800; color: {'#3fb950' if '+' in sel_cagr else '#f85149'}; font-family: 'JetBrains Mono', monospace;">{sel_cagr}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04);">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600; text-transform: uppercase;">Sharpe Ratio</div>
                            <div style="font-size: 14px; font-weight: 800; color: #58a6ff; font-family: 'JetBrains Mono', monospace;">{sel_sharpe}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04);">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600; text-transform: uppercase;">Max Drawdown</div>
                            <div style="font-size: 14px; font-weight: 800; color: #f85149; font-family: 'JetBrains Mono', monospace;">{sel_dd}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_load, col_del = st.columns([3.2, 1.1])
                with col_load:
                    btn_load = st.button("⚡ Ricarica Analisi in Dashboard", type="primary", use_container_width=True, key="btn_load_hist_analysis")
                with col_del:
                    btn_del = st.button("🗑️ Elimina Snapshot", type="secondary", use_container_width=True, key="btn_del_hist_analysis", help="Elimina questo singolo snapshot dal database.")
                
                if btn_load:
                    with st.spinner(f"Ricalcolo rapido dell'analisi {sel_row.run_id}..."):
                        rf_val = st.session_state.get("active_rf_rate")
                        base_curr = st.session_state.get("base_currency", "EUR")
                        from sqlalchemy import text as sqlt
                        target_pid = sel_row.portfolio_id
                        try:
                            with engine_sidebar.connect() as conn:
                                tx_cnt = conn.execute(sqlt("SELECT COUNT(*) FROM transactions WHERE portfolio_id = :pid"), {"pid": target_pid}).scalar()
                                if not tx_cnt or tx_cnt == 0:
                                    # Cerca se le transazioni sono archiviate sotto un altro ID con lo stesso nome
                                    alt_pid = conn.execute(sqlt("""
                                        SELECT t.portfolio_id 
                                        FROM transactions t 
                                        JOIN portfolios p ON t.portfolio_id = p.portfolio_id 
                                        WHERE p.name = :pname 
                                        GROUP BY t.portfolio_id 
                                        ORDER BY COUNT(*) DESC LIMIT 1
                                    """), {"pname": sel_row.port_name}).scalar()
                                    if alt_pid:
                                        target_pid = int(alt_pid)
                        except Exception:
                            pass

                        results = compute_risk(target_pid, engine_sidebar, benchmark_ticker=benchmark, risk_free_rate=rf_val, base_currency=base_curr)
                        st.session_state["pipeline_done"]  = True
                        st.session_state["portfolio_id"]   = target_pid
                        st.session_state["portfolio_name"] = sel_row.port_name
                        st.session_state["engine"]         = engine_sidebar
                        st.session_state["results"]        = results
                        st.session_state["run_id"]         = sel_row.run_id
                        st.session_state["fetch_report"]   = {"success": [], "skipped": [], "rows_written": 0, "errors": []}
                        from core.workspace_manager import save_session_snapshot_to_cache
                        save_session_snapshot_to_cache()
                    st.success(f"Analisi {sel_row.run_id} ricaricata con successo!")
                    try:
                        st.switch_page("pages/1_📈_Dashboard_Generale.py")
                    except Exception:
                        st.rerun()
                
                if btn_del:
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

# ── BANNER SESSIONE ATTIVA & RESET ──────────────────────────
if st.session_state.get("pipeline_done"):
    col_act1, col_act2 = st.columns([3.2, 1.2])
    with col_act1:
        st.markdown(f"""
        <div style="background: rgba(88, 166, 255, 0.1); border: 1px solid rgba(88, 166, 255, 0.3); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; display:flex; align-items:center; gap:10px;">
            <span style="font-size:18px;">📌</span>
            <div style="font-size:12.5px; color:#c9d1d9;">
                <b>Analisi Attiva in Sessione:</b> <span style="color:#58a6ff; font-weight:700;">{st.session_state.get('portfolio_name', 'Portafoglio')}</span> &nbsp;|&nbsp; 
                <b>Run ID:</b> <code style="color:#ff9900;">{st.session_state.get('run_id', 'N/A')}</code> &nbsp;|&nbsp; 
                <span style="color:#3fb950;">I dati sono caricati e disponibili su tutte le 10 schede analitiche.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_act2:
        if st.button("🔄 Reset / Nuova Analisi", type="secondary", use_container_width=True, help="Azzera lo stato corrente della sessione per caricare o elaborare un nuovo portafoglio."):
            from core.workspace_manager import clear_session_cache
            clear_session_cache()
            for key in ["pipeline_done", "portfolio_id", "results", "run_id", "fetch_report"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["session_cleared"] = True
            st.rerun()

# ── COMMAND TABS DELLA CONTROL ROOM ──────────────────────────

tab_ingest, tab_wealth, tab_isin_mapping, tab_diagnostics, tab_duckdb = st.tabs([
    "🚀 1. Ingestione Dati & Calcolo Pipeline",
    "🗂️ 2. Total Wealth Hub (Multi-Portafoglio)",
    "🏷️ 3. Anagrafica & Mappatura ISIN / Ticker DB",
    "🩺 4. Telemetria di Sistema & Storage Profiler",
    "⚡ 5. Motore Analitico Embedded DuckDB (OLAP & SQL)"
])

# =============================================================
# TAB 1: INGESTIONE DATI & CALCOLO PIPELINE
# =============================================================
with tab_ingest:
    
    current_wf_step = 1
    if st.session_state.get("pipeline_done"):
        current_wf_step = 3

    section("① Carica la Sorgente Dati (Multi-Broker Ingestion Hub, CSV Standard o Google Sheets)")

    template_csv = """tx_date,ticker,tx_type,quantity,price,currency,fees,asset_class,notes
2021-03-15,AAPL,buy,10,121.03,USD,1.50,stock,Esempio acquisto
2021-06-01,VWRL.L,buy,5,89.20,GBP,0.00,etf,
2022-01-10,BTC-USD,buy,0.05,41800.00,USD,2.00,crypto,
2022-08-20,AAPL,sell,5,162.50,USD,1.50,stock,Presa profitto
2023-03-01,AAPL,dividend,0,0.23,USD,0.00,stock,Dividendo Q1"""

    col_ds_sel, col_ds_modal, col_ds_tpl = st.columns([2.6, 1.0, 1.0])
    with col_ds_sel:
        data_source = st.selectbox(
            "Sorgente Dati / Piattaforma Broker",
            options=[
                "⚡ Auto-Detect Broker (Riconoscimento Automatico Formato)",
                "📄 CSV Standard (Template ARGUS)",
                "🟡 DeGiro (Export Transazioni)",
                "🔵 Directa SIM (Ordini Eseguiti / Estratto Conto)",
                "🔴 Fineco Bank (Movimenti Conto Trading)",
                "🟠 Interactive Brokers - IBKR (Activity Statement / Trades)",
                "🟢 Trade Republic (Transazioni / PAC)",
                "🔷 Scalable Capital (Transazioni / Baader Bank)",
                "🟩 eToro (Account Statement / Closed Trades)",
                "🟪 Revolut Trading (Estratto Conto Transazioni)",
                "🌐 Google Sheets Live Sync"
            ],
            help="Seleziona il broker da cui proviene il file CSV oppure usa 'Auto-Detect' per il riconoscimento automatico intelligente."
        )
    with col_ds_modal:
        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
        render_broker_hub_modal(use_popover=False)
    with col_ds_tpl:
        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
        st.download_button(
            "⬇️ Template CSV",
            data=template_csv,
            file_name="template_portfolio.csv",
            mime="text/csv",
            use_container_width=True,
            help="Scarica il file CSV di esempio con lo schema standard ARGUS a 9 colonne."
        )

    uploaded_file = None
    df_raw = None

    if data_source == "🌐 Google Sheets Live Sync":
        st.markdown("##### 🌐 Sincronizzazione Diretta Google Sheets (Service Account)")
        st.caption("Estrai automaticamente le transazioni sia dall'azionario che dalle criptovalute, separando i portafogli su DB e registrandoli nel Total Wealth Hub.")
        
        gs_mode_label = st.radio(
            "Modalità di Estrazione Google Sheets:",
            [
                "⚡ Sincronizzazione Completa (Stocks + Crypto separati)",
                "📈 Solo Stocks (History B/S Stocks)",
                "🪙 Solo Crypto (History B/S Crypto)",
                "⚙️ Personalizzato"
            ],
            horizontal=True
        )
        
        gs_name = st.text_input("Nome/ID dello Spreadsheet Google Sheets:", value="My All financial Statements")
        
        mode_param = "both"
        stocks_tab_val = "History B/S Stocks"
        crypto_tab_val = "History B/S Crypto"
        custom_tab_val = "History B/S Stocks"
        custom_pname_val = "Wealth Custom Portfolio"
        
        if gs_mode_label == "⚡ Sincronizzazione Completa (Stocks + Crypto separati)":
            mode_param = "both"
            col_gs1, col_gs2 = st.columns(2)
            stocks_tab_val = col_gs1.text_input("Nome Tab Stocks/ETF:", value="History B/S Stocks")
            crypto_tab_val = col_gs2.text_input("Nome Tab Crypto:", value="History B/S Crypto")
            st.info("💡 I portafogli verranno creati come **`Wealth Stocks Portfolio`** e **`Wealth Crypto Portfolio`**, con snapshot indipendenti su DB e registrazione automatica nel Total Wealth Hub.")
        elif gs_mode_label == "📈 Solo Stocks (History B/S Stocks)":
            mode_param = "stocks"
            stocks_tab_val = st.text_input("Nome Tab Stocks/ETF:", value="History B/S Stocks")
        elif gs_mode_label == "🪙 Solo Crypto (History B/S Crypto)":
            mode_param = "crypto"
            crypto_tab_val = st.text_input("Nome Tab Crypto:", value="History B/S Crypto")
        else:
            mode_param = "custom"
            col_c1, col_c2 = st.columns(2)
            custom_tab_val = col_c1.text_input("Nome del Tab:", value="History B/S Stocks")
            custom_pname_val = col_c2.text_input("Nome Portafoglio su DB:", value="Wealth Custom Portfolio")
        
        btn_gs_sync = st.button("🔄 Avvia Sincronizzazione Live Google Sheets", type="primary", use_container_width=True)
        if btn_gs_sync:
            with st.spinner("⏳ Connessione a Google Sheets ed esecuzione ETL in corso..."):
                try:
                    import importlib
                    import core.db_exporter
                    importlib.reload(core.db_exporter)
                    import core.risk_engine
                    importlib.reload(core.risk_engine)
                    import gsheets_sync_subproject.sync_google_sheets
                    importlib.reload(gsheets_sync_subproject.sync_google_sheets)
                    from gsheets_sync_subproject.sync_google_sheets import run_daily_pipeline

                    res_tuple = run_daily_pipeline(
                        spreadsheet_identifier=gs_name,
                        mode=mode_param,
                        stocks_tab=stocks_tab_val,
                        crypto_tab=crypto_tab_val,
                        custom_tab=custom_tab_val,
                        custom_portfolio_name=custom_pname_val,
                        return_results=True
                    )
                    if isinstance(res_tuple, tuple) and len(res_tuple) >= 5 and res_tuple[0]:
                        success, res_sync, run_id_sync, p_name_sync, f_rep = res_tuple[0:5]
                        dual_info = res_tuple[5] if len(res_tuple) > 5 else None

                        st.session_state["results"] = res_sync
                        st.session_state["pipeline_done"] = True
                        st.session_state["portfolio_name"] = p_name_sync or "Google Sheets Portfolio"
                        st.session_state["run_id"] = run_id_sync
                        st.session_state["fetch_report"] = f_rep
                        st.session_state.pop("session_cleared", None)
                        
                        if dual_info and "stocks" in dual_info and "crypto" in dual_info:
                            st.session_state["gs_dual_sync_success"] = {
                                "stocks_name": dual_info["stocks"]["portfolio_name"],
                                "crypto_name": dual_info["crypto"]["portfolio_name"],
                                "run_id": run_id_sync
                            }
                            st.success(f"✅ Sincronizzazione duale completata! Creati **{dual_info['stocks']['portfolio_name']}** e **{dual_info['crypto']['portfolio_name']}** su DB e registrati nel Total Wealth Hub.")
                        else:
                            st.success(f"✅ Sincronizzazione completata! Portafoglio **{p_name_sync}** caricato in sessione (Run ID: `{run_id_sync}`).")
                        st.rerun()
                    elif res_tuple is True:
                        st.success("✅ Sincronizzazione con Google Sheets completata con successo!")
                        st.rerun()
                except Exception as ex:
                    st.error(f"❌ Errore durante la sincronizzazione Google Sheets: {ex}")
    else:
        uploaded_file = st.file_uploader(
            "Trascina qui il tuo file CSV esportato dal broker (o usa il template ARGUS):",
            type=["csv"],
            help="Carica il file in formato CSV. L'Auto-Detector riconoscerà automaticamente la struttura del broker."
        )
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file, dtype=str)
            st.session_state.pop("session_cleared", None)
            if not st.session_state.get("portfolio_name") or st.session_state.get("portfolio_name") == "Nessun Portafoglio (In attesa)":
                auto_name = os.path.splitext(uploaded_file.name)[0].replace("_", " ").replace("-", " ").title()
                st.session_state["portfolio_name"] = auto_name

    if st.session_state.get("pipeline_done"):
        current_wf_step = 3
    elif df_raw is not None:
        current_wf_step = 2
    else:
        current_wf_step = 1

    render_workflow_stepper(current_wf_step)

    # ── STEP 2: Validazione Dati & Data Health HUD ───────────────
    if df_raw is not None:
        broker_key_map = {
            "⚡ Auto-Detect Broker (Riconoscimento Automatico Formato)": "auto",
            "📄 CSV Standard (Template ARGUS)": "standard",
            "🟡 DeGiro (Export Transazioni)": "degiro",
            "🔵 Directa SIM (Ordini Eseguiti / Estratto Conto)": "directa",
            "🔴 Fineco Bank (Movimenti Conto Trading)": "fineco",
            "🟠 Interactive Brokers - IBKR (Activity Statement / Trades)": "ibkr",
            "🟢 Trade Republic (Transazioni / PAC)": "traderepublic",
            "🔷 Scalable Capital (Transazioni / Baader Bank)": "scalable",
            "🟩 eToro (Account Statement / Closed Trades)": "etoro",
            "🟪 Revolut Trading (Estratto Conto Transazioni)": "revolut"
        }
        selected_broker_key = broker_key_map.get(data_source, "auto")

        if selected_broker_key != "standard":
            from core.adapters.broker_hub import parse_broker_csv
            try:
                with st.spinner("⏳ Analisi struttura broker e normalizzazione ISIN via Multi-Broker Hub..."):
                    df_raw, detected_key, b_report = parse_broker_csv(df_raw, broker_key=selected_broker_key)
                
                b_name = b_report.get("broker_name", detected_key.title())
                b_icon = b_report.get("broker_icon", "📄")
                if b_report.get("is_auto_detected"):
                    st.success(f"✅ Formato riconosciuto automaticamente: **{b_icon} {b_name}** ({b_report.get('rows_parsed', 0)} transazioni convertite con successo).")
                else:
                    st.success(f"✅ File **{b_icon} {b_name}** convertito con successo ({b_report.get('rows_parsed', 0)} transazioni normalizzate).")
            except Exception as e:
                st.error(f"❌ Errore durante il parsing del file broker: {e}")
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

        # Mini Asset Class Breakdown Pills
        if "asset_class" in df_clean.columns:
            ac_counts = df_clean["asset_class"].fillna("other").value_counts().to_dict()
            ac_pills = " ".join([
                f'<span class="argus-asset-pill" style="border-color:rgba(88,166,255,0.3); color:#58a6ff;">● {ac.upper()}: <b>{cnt}</b> tx</span>'
                for ac, cnt in ac_counts.items()
            ])
            st.markdown(f"""
            <div style="background: rgba(13, 17, 23, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 8px 12px; margin: 8px 0 12px 0; display:flex; align-items:center; gap: 8px; flex-wrap:wrap;">
                <span style="font-size:11px; font-weight:700; color:#8b949e; text-transform:uppercase; letter-spacing:0.4px;">Asset Allocation Rilevata:</span>
                {ac_pills}
            </div>
            """, unsafe_allow_html=True)

        with st.expander("🔍 Ispeziona Anteprima Dati Validati", expanded=False):
            df_display = df_clean.copy()
            if "tx_date" in df_display.columns:
                df_display["tx_date"] = df_display["tx_date"].dt.strftime("%Y-%m-%d")
            df_display_renamed = df_display.rename(columns={
                "tx_date": "Data Operazione",
                "ticker": "Ticker / ISIN",
                "tx_type": "Tipo Operazione",
                "quantity": "Quantità",
                "price": "Prezzo (€)",
                "currency": "Valuta",
                "fees": "Commissioni (€)",
                "asset_class": "Classe Asset",
                "notes": "Note"
            })
            st.dataframe(df_display_renamed, use_container_width=True, height=200)

        # Mappatura ISIN / Yahoo Ticker
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
        
        from core.fetcher import _get_config_file_path
        cfg_path_ing = _get_config_file_path()
        loaded_mapping = {}
        if cfg_path_ing.exists():
            try:
                with open(cfg_path_ing, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    loaded_mapping = config_data.get("ticker_mapping", {})
            except Exception:
                pass

        if engine_sidebar is not None:
            try:
                with engine_sidebar.connect() as conn:
                    db_maps = conn.execute(sqlt("SELECT input_ticker, yfinance_ticker FROM asset_mapping")).fetchall()
                    for r_m in db_maps:
                        loaded_mapping[str(r_m[0]).strip().upper()] = str(r_m[1]).strip().upper()
            except Exception:
                pass

        if unmapped_isins:
            missing_isins = [i for i in unmapped_isins if not loaded_mapping.get(i)]
            if missing_isins:
                st.warning(f"⚠️ Rilevati {len(missing_isins)} ISIN non mappati ai ticker Yahoo Finance.")
                mapping_data = []
                for isin in missing_isins:
                    nome_prodotto = df_clean.loc[df_clean["ticker"] == isin, "notes"].dropna().unique()
                    nome = nome_prodotto[0] if len(nome_prodotto) > 0 else "Sconosciuto"
                    suggerimento = fetch_yahoo_ticker_for_isin(isin)
                    mapping_data.append({"ISIN": isin, "Nome Prodotto": nome, "Yahoo Ticker": suggerimento})
                
                mapping_df = pd.DataFrame(mapping_data)
                edited_mapping_df = st.data_editor(mapping_df, use_container_width=True, hide_index=True, key="new_mapping")
                
                if st.button("💾 Salva Nuova Mappatura nel DB & Config", type="primary", key="save_new_mapping"):
                    new_mapping = dict(zip(edited_mapping_df["ISIN"], edited_mapping_df["Yahoo Ticker"]))
                    new_mapping = {k: v.strip().upper() for k, v in new_mapping.items() if v and v.strip()}
                    if new_mapping:
                        config_data = {}
                        if cfg_path_ing.exists():
                            try:
                                with open(cfg_path_ing, "r", encoding="utf-8") as f: config_data = json.load(f)
                            except Exception: pass
                        if "ticker_mapping" not in config_data: config_data["ticker_mapping"] = {}
                        config_data["ticker_mapping"].update(new_mapping)
                        with open(cfg_path_ing, "w", encoding="utf-8") as f: json.dump(config_data, f, indent=4)
                        
                        if engine_sidebar is not None:
                            try:
                                with engine_sidebar.begin() as conn:
                                    for isin_k, yf_v in new_mapping.items():
                                        if engine_sidebar.dialect.name == "sqlite":
                                            conn.execute(sqlt("""
                                                INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                                VALUES (:input_ticker, :yfinance_ticker, :description)
                                                ON CONFLICT(input_ticker) DO UPDATE SET yfinance_ticker = excluded.yfinance_ticker
                                            """), {"input_ticker": isin_k, "yfinance_ticker": yf_v, "description": "Ingestione CSV"})
                                        else:
                                            conn.execute(sqlt("""
                                                INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                                VALUES (:input_ticker, :yfinance_ticker, :description)
                                                ON DUPLICATE KEY UPDATE yfinance_ticker = VALUES(yfinance_ticker)
                                            """), {"input_ticker": isin_k, "yfinance_ticker": yf_v, "description": "Ingestione CSV"})
                            except Exception: pass
                            
                        st.success("Mappatura salvata con successo nel DB e in Config!")
                        st.rerun()

        # ── STEP 3: Elaborazione Dati e Calcolo Rischio ───────────────
        section("③ Elaborazione Dati e Calcolo Rischio")

        if not st.session_state.get("pipeline_done"):
            col_cfg1, col_cfg2 = st.columns([2.5, 1.5])
            with col_cfg1:
                custom_pname = st.text_input(
                    "Nome del Portafoglio da Salvare:",
                    value=st.session_state.get("portfolio_name") or "Portafoglio Quantitativo",
                    help="Nome descrittivo con cui salvare questo portafoglio nel Database e nel Total Wealth Hub."
                )
                if custom_pname:
                    st.session_state["portfolio_name"] = custom_pname.strip()
            with col_cfg2:
                benchmark = st.selectbox(
                    "Benchmark di Mercato:",
                    options=["SPY", "VWCE.DE", "^GSPC", "QQQ", "IEI"],
                    index=0,
                    help="Indice/ETF di confronto per il calcolo di Beta, Alpha e correlazione."
                )

            st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True)
            run_fetch = st.button("🚀 Avvia Analisi Quantitativa ARGUS", type="primary", use_container_width=True, key="btn_run_argus_pipeline")

            if run_fetch:
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
                    p_name_final = st.session_state.get("portfolio_name") or "Portafoglio Quantitativo"
                    
                    if not offline_mode:
                        from sqlalchemy import text as sqlt
                        from core.db_exporter import get_or_create_portfolio_id
                        with engine.begin() as conn:
                            portfolio_id = get_or_create_portfolio_id(
                                conn,
                                name=p_name_final,
                                owner="streamlit_user",
                                base_currency=st.session_state.get("base_currency", "EUR")
                            )
                            conn.execute(sqlt("DELETE FROM transactions WHERE portfolio_id = :pid"), {"pid": portfolio_id})

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

                    rf_val = st.session_state.get("active_rf_rate")
                    base_curr = st.session_state.get("base_currency", "EUR")

                    if offline_mode:
                        fetch_report, df_tx, df_prices = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
                        results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark, df_tx=df_tx, df_prices=df_prices, risk_free_rate=rf_val, base_currency=base_curr)
                    else:
                        fetch_report = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
                        results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark, risk_free_rate=rf_val, base_currency=base_curr)

                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    run_id = f"ANL-{timestamp_str}"
                    
                    if not offline_mode:
                        save_snapshot_to_db(results, engine, portfolio_id, run_id, run_name)

                    st.session_state["pipeline_done"]  = True
                    st.session_state["portfolio_id"]   = portfolio_id
                    st.session_state["portfolio_name"] = p_name_final
                    st.session_state["engine"]         = engine
                    st.session_state["fetch_report"]   = fetch_report
                    st.session_state["results"]        = results
                    st.session_state["run_id"]         = run_id
                    from core.workspace_manager import save_session_snapshot_to_cache
                    save_session_snapshot_to_cache()
                    st.rerun()

        else:
            fr = st.session_state.get("fetch_report", {})
            res = st.session_state.get("results", {})
            m = res.get("metrics", {})
            ret = m.get("returns", {})
            mk = m.get("market_risk", {})
            var_m = m.get("var_models", {})

            # ── EXECUTIVE COCKPIT SUMMARY CARD ────────────────────────
            cagr_v = ret.get('cagr_pct', 0.0)
            cagr_color = "#3fb950" if cagr_v >= 0 else "#f85149"
            
            sharpe_v = ret.get('sharpe_ratio')
            if sharpe_v is None:
                sharpe_v = mk.get('sharpe_ratio', 0.0)
            sharpe_color = "#3fb950" if sharpe_v >= 1.0 else ("#ff9900" if sharpe_v >= 0.5 else "#f85149")
            
            vol_ann_v = mk.get('volatility_annual_pct', 0.0)
            max_dd_v = mk.get('max_drawdown_pct', 0.0)
            
            var_95_v = mk.get('var_95')
            if var_95_v is None:
                var_95_v = var_m.get('hist_var_95', 0.0)
            if var_95_v is not None and 0 < abs(var_95_v) < 0.1:
                var_95_v = var_95_v * 100
            var_95_v = var_95_v if var_95_v is not None else 0.0
            
            p_val = ret.get('portfolio_value', 0.0)
            n_tickers_ok = len(fr.get('success', [])) if fr.get('success') else len(s.get('tickers', []))

            st.markdown(f"""
            <div style="background: rgba(22, 27, 34, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(63, 185, 80, 0.35); border-left: 4px solid #3fb950; border-radius: 14px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);">
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom: 14px;">
                    <div>
                        <div style="font-size: 17px; font-weight:800; color:#ffffff; letter-spacing:0.3px;">🎉 Analisi Quantitativa Completata con Successo</div>
                        <div style="font-size: 11.5px; color:#8b949e; margin-top:2px;">Portafoglio <b>{st.session_state.get('portfolio_name')}</b> sincronizzato ed indicizzato a storico.</div>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <span class="argus-command-pill" style="border-color: rgba(63, 185, 80, 0.5); color: #3fb950; font-weight:700;">RUN: {st.session_state.get('run_id', 'N/A')}</span>
                        <span class="argus-command-pill" style="border-color: rgba(88, 166, 255, 0.4); color: #58a6ff;">VALORE: € {p_val:,.2f}</span>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px;">
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">CAGR ANNUO</div>
                        <div style="font-size:17px; font-weight:800; color:{cagr_color};">{cagr_v:+.2f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">SHARPE RATIO</div>
                        <div style="font-size:17px; font-weight:800; color:{sharpe_color};">{sharpe_v:.2f}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">VOLATILITÀ ANNUA</div>
                        <div style="font-size:17px; font-weight:800; color:#58a6ff;">{vol_ann_v:.2f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">MAX DRAWDOWN</div>
                        <div style="font-size:17px; font-weight:800; color:#f85149;">{max_dd_v:.2f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">VaR 95% (1-DAY)</div>
                        <div style="font-size:17px; font-weight:800; color:#e3b341;">{var_95_v:.2f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; text-align:center;">
                        <div style="font-size:10px; font-weight:600; color:#8b949e;">TICKER ONLINE</div>
                        <div style="font-size:17px; font-weight:800; color:#3fb950;">{n_tickers_ok}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if fr.get("errors"):
                for e in fr["errors"]:
                    st.markdown(f'<div class="error-box">🔴 {e}</div>', unsafe_allow_html=True)

            # Fast Navigation Ribbon
            st.markdown("##### 🧭 Navigazione Rapida Moduli Analitici")
            nav_c1, nav_c2, nav_c3, nav_c4 = st.columns(4)
            with nav_c1:
                st.page_link("pages/1_📈_Dashboard_Generale.py", label="📈 Executive Cockpit ➔", use_container_width=True)
            with nav_c2:
                st.page_link("pages/2_🖥️_Live_Terminal.py", label="🖥️ Live Terminal OMS ➔", use_container_width=True)
            with nav_c3:
                st.page_link("pages/3_🔴_Analisi_Rischio.py", label="🔴 Analisi Rischio & VaR ➔", use_container_width=True)
            with nav_c4:
                st.page_link("pages/4_🔬_Modelli_Quantitativi.py", label="🔬 Modelli Quantitativi ➔", use_container_width=True)

            nav_r2_1, nav_r2_2, nav_r2_3, nav_r2_4 = st.columns(4)
            with nav_r2_1:
                st.page_link("pages/5_📋_Posizioni_e_Dettagli.py", label="📋 Posizioni & Fisco ➔", use_container_width=True)
            with nav_r2_2:
                st.page_link("pages/6_🏛️_Valutazione_Aziendale.py", label="🏛️ Valutazione Fair Value ➔", use_container_width=True)
            with nav_r2_3:
                st.page_link("pages/7_🌪️_Stress_Testing.py", label="🌪️ Stress Testing Macro ➔", use_container_width=True)
            with nav_r2_4:
                st.page_link("pages/10_🔍_Screener_Opportunita.py", label="🔍 Screener & Pre-Trade ➔", use_container_width=True)

            with st.expander("🔄 Opzioni di Ricalcolo / Modifica Parametri", expanded=False):
                col_re1, col_re2 = st.columns([2, 1])
                with col_re1:
                    new_bm = st.selectbox("Cambia Benchmark:", options=["SPY", "VWCE.DE", "^GSPC", "QQQ", "IEI"], index=0, key="recalc_bm")
                with col_re2:
                    st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
                    if st.button("⚡ Ricalcola Analisi", type="secondary", use_container_width=True, key="btn_recalc_now"):
                        st.session_state["pipeline_done"] = False
                        st.session_state["session_cleared"] = False
                        st.rerun()


# =============================================================
# TAB 2: TOTAL WEALTH HUB & MULTI-PORTAFOGLIO
# =============================================================
with tab_wealth:
    section("🗂️ Total Wealth Hub & Gestione Multi-Portafoglio")
    st.caption("Gestisci più conti o strategie contemporaneamente (es. Crescita, Dividendi, Previdenza, Crypto), confrontali affiancati e consolidali in un unico Portafoglio Master.")

    render_info_modal(
        title="Come Funziona il Total Wealth Hub (Multi-Account)",
        content="""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🎯 Visione Olistica del Patrimonio</b><br>
  Gli investitori gestiscono spesso posizioni frammentate tra broker diversi o conti a finalità distinte (Crescita Tech, Dividendi, Pensione). Il Total Wealth Hub consente di salvare e consolidare questi profili in una singola analisi unificata.
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">1. Salvataggio Profili Multipli</div>
  <div>Permette di etichettare lo stato di analisi corrente con un nome e una strategia specifica (es. <i>Portafoglio Core</i>, <i>Satellite Crypto</i>, <i>ETF Passive</i>).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">2. Consolidamento Master Portfolio</div>
  <div>Selezionando 2 o più portafogli salvati, ARGUS:
    <br>• Aggrega le posizioni sommando le quote e ricalcolando il prezzo medio ponderato di carico (WACP).
    <br>• Fonde le serie storiche dei rendimenti ponderate per il rispettivo controvalore patrimoniale.
    <br>• Calcola istantaneamente il nuovo VaR 95%, Sharpe Ratio, Volatilità e diversificazione globale.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">3. Scorecard Comparativa</div>
  <div>Confronta affiancati i portafogli per rendimento (CAGR), volatilità, Sharpe Ratio, drawdown e massima posizione di rischio.</div>
</div>

</div>
""",
        button_label="📖 Guida al Multi-Portafoglio"
    )

    # 1. Box Salvataggio Portafoglio Attivo
    has_active_res = st.session_state.get("results") is not None and isinstance(st.session_state.get("results"), dict)

    with st.expander("💾 Salva Portafoglio Attivo nel Registro Multi-Account", expanded=False):
        if not has_active_res:
            st.info("Esegui prima un'analisi per salvare il portafoglio corrente nel registro.")
        else:
            col_s_name, col_s_tag, col_s_btn = st.columns([3, 2, 2])
            with col_s_name:
                save_name_in = st.text_input("Nome Portafoglio / Conto:", value=st.session_state.get("portfolio_name", "Portafoglio_1"), key="mp_save_name")
            with col_s_tag:
                save_tag_in = st.selectbox("Tag Strategia:", ["Crescita (Growth)", "Dividendi & Rendita", "Previdenza / Pensione", "Core / Satellite", "Crypto & Speculativo", "Generale"], key="mp_save_tag")
            with col_s_btn:
                st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
                if st.button("💾 Salva nel Registro", type="primary", use_container_width=True, key="btn_save_mp"):
                    if save_portfolio_profile(save_name_in.strip(), st.session_state["results"], tag=save_tag_in):
                        st.success(f"Portafoglio '{save_name_in}' salvato con successo nel registro multi-account!")
                        st.rerun()
                    else:
                        st.error("Errore durante il salvataggio del profilo.")

    # 2. Elenco Portafogli e Azioni di Consolidamento
    saved_profiles = list_saved_portfolio_profiles()
    if saved_profiles:
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        
        # Intestazione e Barra di Controllo Unificata
        col_t_title, col_t_actions = st.columns([3, 4])
        with col_t_title:
            st.markdown(f"##### 📋 Portafogli Registrati <span style='font-size:13px; color:#8b949e; font-weight:normal;'>({len(saved_profiles)} disponibili)</span>", unsafe_allow_html=True)
        
        selected_for_merge = []
        
        with col_t_actions:
            col_btn_merge, col_btn_comp = st.columns(2)
            with col_btn_merge:
                btn_merge = st.button("🔗 Consolida in Master Wealth", type="primary", use_container_width=True, key="btn_merge_master", help="Fonde i portafogli selezionati tramite checkbox in un unico Master Wealth")
            with col_btn_comp:
                btn_comp = st.button("📊 Scorecard Comparativa", use_container_width=True, key="btn_comp_portfolios", help="Visualizza la tabella comparativa dei portafogli")
        
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)

        for p in saved_profiles:
            with st.container():
                st.markdown("""
                <div style="background: rgba(22, 27, 34, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;">
                """, unsafe_allow_html=True)
                
                c_chk, c_meta, c_val, c_kpi, c_load, c_del = st.columns([0.35, 2.5, 2.0, 2.6, 1.3, 0.65])
                
                with c_chk:
                    st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True)
                    chk = st.checkbox(" ", key=f"chk_mp_{p['name']}", value=False, label_visibility="collapsed")
                    if chk:
                        selected_for_merge.append(p["name"])
                
                with c_meta:
                    st.markdown(f"""
                    <div style="font-weight: 700; font-size: 14.5px; color: #f0f6fc; margin-bottom: 2px;">{p['name']}</div>
                    <div><span style="font-size: 11px; background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid rgba(88,166,255,0.25); padding: 1px 7px; border-radius: 10px; font-weight: 600;">{p['tag']}</span></div>
                    """, unsafe_allow_html=True)
                    
                with c_val:
                    st.markdown(f"""
                    <div style="font-size: 14.5px; font-weight: 700; color: #ffb74d;">€ {p['portfolio_value']:,.2f}</div>
                    <div style="font-size: 11px; color: #8b949e;">📦 <b>{p['asset_count']}</b> posizioni aperte</div>
                    """, unsafe_allow_html=True)
                    
                with c_kpi:
                    cagr_color = "#3fb950" if p['cagr_pct'] >= 0 else "#f85149"
                    st.markdown(f"""
                    <div style="font-size: 12.5px; color: #c9d1d9;">📈 Sharpe: <b style="color: #58a6ff;">{p['sharpe_ratio']:.2f}</b> &nbsp;|&nbsp; CAGR: <b style="color: {cagr_color};">{p['cagr_pct']:+.1f}%</b></div>
                    <div style="font-size: 11px; color: #8b949e;">🛡️ VaR 95%: <b>{p['var_95_pct']:.2f}%</b> &nbsp;|&nbsp; MaxDD: <b>{p['max_dd_pct']:.1f}%</b></div>
                    """, unsafe_allow_html=True)
                    
                with c_load:
                    st.markdown('<div style="height: 2px;"></div>', unsafe_allow_html=True)
                    if st.button("📂 Carica", key=f"btn_load_{p['name']}", use_container_width=True, help=f"Imposta '{p['name']}' come portafoglio attivo"):
                        prof_data = load_portfolio_profile(p["name"])
                        if prof_data:
                            loaded_res = prof_data.get("results_full") or prof_data
                            st.session_state["results"] = loaded_res
                            st.session_state["pipeline_done"] = True
                            st.session_state["portfolio_name"] = p["name"]
                            st.session_state["run_id"] = f"LOAD-{p['name'][:10]}"
                            from core.workspace_manager import save_session_snapshot_to_cache
                            save_session_snapshot_to_cache()
                            st.success(f"Portafoglio '{p['name']}' caricato con successo!")
                            try:
                                st.switch_page("pages/1_📈_Dashboard_Generale.py")
                            except Exception:
                                st.rerun()
                                
                with c_del:
                    st.markdown('<div style="height: 2px;"></div>', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"btn_del_{p['name']}", use_container_width=True, help="Elimina dal registro"):
                        delete_saved_portfolio_profile(p["name"])
                        st.rerun()
                        
                st.markdown("</div>", unsafe_allow_html=True)

        n_sel = len(selected_for_merge)
        if n_sel > 0:
            st.markdown(f"<div style='font-size: 12px; color: #8b949e; margin-top: 4px;'>🎯 Portafogli selezionati per fusione o confronto: <b style='color: #ff9900;'>{n_sel}</b> su {len(saved_profiles)}</div>", unsafe_allow_html=True)

        if btn_merge:
            if len(selected_for_merge) < 2:
                st.warning("⚠️ Seleziona almeno **2 portafogli** tramite le caselle di spunta per creare il Master Wealth.")
            else:
                with st.spinner("Consolidamento delle posizioni e ricalcolo quantitativo del Master Portfolio..."):
                    merged_res = consolidate_multi_portfolios(selected_for_merge)
                    if merged_res:
                        st.session_state["results"] = merged_res
                        st.session_state["pipeline_done"] = True
                        st.session_state["portfolio_name"] = merged_res["portfolio_name"]
                        st.session_state["run_id"] = merged_res["run_id"]
                        from core.workspace_manager import save_session_snapshot_to_cache
                        save_session_snapshot_to_cache()
                        st.success("Master Portfolio consolidato con successo! Reindirizzamento...")
                        try:
                            st.switch_page("pages/1_📈_Dashboard_Generale.py")
                        except Exception:
                            st.rerun()
                    else:
                        st.error("Impossibile consolidare i portafogli selezionati.")

        if btn_comp or st.session_state.get("show_mp_comparison"):
            st.session_state["show_mp_comparison"] = True
            st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
            st.markdown("##### 📊 Scorecard Comparativa Multi-Portafoglio")
            target_comp = selected_for_merge if selected_for_merge else [p["name"] for p in saved_profiles]
            df_comp = compute_multi_portfolio_comparison(target_comp)
            if not df_comp.empty:
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun profilo salvato finora. Esegui un'analisi e usa il modulo sopra per salvare il tuo primo portafoglio!")


# =============================================================
# TAB 3: ANAGRAFICA & MAPPATURA ISIN / TICKER DB
# =============================================================
with tab_isin_mapping:
    section("🏷️ Anagrafica & Mappatura ISIN / Ticker nel Database (asset_mapping)")
    
    col_head_map1, col_head_map2 = st.columns([3.2, 1.1])
    with col_head_map1:
        st.caption("Gestisci l'anagrafica centralizzata di conversione tra codici ISIN bancari / Ticker locali e simboli Yahoo Finance. Le mappature vengono salvate sia nella tabella SQL **`asset_mapping`** che nel file di configurazione.")
    with col_head_map2:
        glossary_modal("ℹ️ Guida alla Mappatura ISIN / Ticker", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. TABELLA DB ASSET MAPPING -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📌 1. Tabella DB Centralizzata (asset_mapping)</div>
  <div style="margin-bottom: 6px;"><b>Cos'è:</b> Il dizionario anagrafico che converte i codici ISIN bancari internazionali (es. <code>IE00B4L5Y983</code>) e i ticker proprietari broker (es. <code>BIT:ISP</code>) nei simboli standard Yahoo Finance (<code>SWDA.MI</code>, <code>ISP.MI</code>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Schema di Risoluzione:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>ISIN / Broker Code</b> &rarr; <b>Asset Mapping SQL</b> &rarr; <b>Yahoo Finance Ticker</b>
    </div>
  </div>
  <div><b>🎯 A cosa serve:</b> Garantisce il download automatico a latenza zero delle serie storiche dei prezzi anche per file CSV esportati da banche italiane ed europee.</div>
</div>

<!-- 2. RISOLUZIONE AUTOMATICA -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔍 2. Risoluzione Intelligente & Ricerca Live</div>
  <div style="margin-bottom: 6px;"><b>Autocompletamento:</b> Inserendo un codice ISIN, ARGUS interroga le API di ricerca per identificare automaticamente la borsa di quotazione principale (Milano <code>.MI</code>, Francoforte <code>.DE</code>, Londra <code>.L</code>, NYSE/NASDAQ).</div>
  <div><b>Persistenza:</b> Ogni nuova mappatura inserita viene salvata istantaneamente sia nel Database SQL che nel file locale <code>config.json</code>.</div>
</div>

</div>
""", button_label="💡 Come funziona la Mappatura ISIN?")

    from core.fetcher import _get_config_file_path
    cfg_file = _get_config_file_path()
    
    # 1. Carica Mappature dal Database (tabella asset_mapping) e da config.json
    db_mapping_dict = {}
    engine_curr = st.session_state.get("engine") or engine_sidebar
    
    if engine_curr is not None:
        try:
            from core.models import Base
            Base.metadata.create_all(engine_curr)
            with engine_curr.connect() as conn:
                res_map = conn.execute(sqlt("SELECT input_ticker, yfinance_ticker, description FROM asset_mapping")).fetchall()
                for r in res_map:
                    db_mapping_dict[str(r[0]).strip().upper()] = {
                        "input_ticker": str(r[0]).strip().upper(),
                        "yfinance_ticker": str(r[1]).strip().upper(),
                        "description": str(r[2] or "DB Record")
                    }
        except Exception:
            pass
            
    # Merge con config.json
    cfg_mapping_dict = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
                for k, v in cfg_data.get("ticker_mapping", {}).items():
                    k_clean = str(k).strip().upper()
                    cfg_mapping_dict[k_clean] = str(v).strip().upper()
                    if k_clean not in db_mapping_dict:
                        db_mapping_dict[k_clean] = {
                            "input_ticker": k_clean,
                            "yfinance_ticker": str(v).strip().upper(),
                            "description": "Config JSON"
                        }
        except Exception:
            pass

    # Metriche Anagrafica
    m_c1, m_c2, m_c3 = st.columns(3)
    with m_c1:
        metric_card("Totale ISIN / Ticker Mappati", f"{len(db_mapping_dict)}", "Anagrafica attiva", positive=True)
    with m_c2:
        db_rec_count = len([v for v in db_mapping_dict.values() if v.get('description') != 'Config JSON'])
        metric_card("Tabella DB `asset_mapping`", f"{db_rec_count} Record", "SQLite / MySQL", positive=True)
    with m_c3:
        metric_card("File config.json", f"{len(cfg_mapping_dict)} Voci", str(cfg_file.name), positive=True)

    st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
    
    # 2. Tool di Risoluzione Rapida & Aggiunta Singolo ISIN
    with st.expander("🔍 Risolutore Istantaneo Singolo ISIN / Ticker (Yahoo Search API)", expanded=True):
        col_res1, col_res2, col_res3 = st.columns([1.5, 1.5, 1.8])
        with col_res1:
            input_isin_code = st.text_input("Codice ISIN o Ticker Locale (Input):", placeholder="es. IE00B4L5Y983 o BIT:ISP", key="input_isin_code_m").strip().upper()
        with col_res2:
            input_asset_desc = st.text_input("Descrizione / Nome Strumento:", placeholder="es. iShares Core MSCI World", key="input_asset_desc_m").strip()
        with col_res3:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                btn_resolve_isin = st.button("🔎 Risolvi Yahoo", use_container_width=True, key="btn_resolve_isin_m")
            with col_b2:
                btn_add_manual = st.button("➕ Inserisci Mappatura", type="primary", use_container_width=True, key="btn_add_manual_m")

        if btn_resolve_isin and input_isin_code:
            with st.spinner(f"Ricerca ticker Yahoo per {input_isin_code}..."):
                try:
                    url_srch = f"https://query2.finance.yahoo.com/v1/finance/search?q={input_isin_code}"
                    res_srch = requests.get(url_srch, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
                    quotes = res_srch.get('quotes', [])
                    if quotes:
                        sug_sym = quotes[0].get('symbol', '')
                        long_name = quotes[0].get('longname', quotes[0].get('shortname', ''))
                        st.success(f"🎯 Risolto con successo: **`{sug_sym}`** {f'({long_name})' if long_name else ''}")
                        st.session_state["suggested_yf_val"] = sug_sym
                        if not input_asset_desc and long_name:
                            st.session_state["suggested_yf_name"] = long_name
                    else:
                        st.warning(f"Nessun ticker trovato automaticamente per '{input_isin_code}'. Inseriscilo manualmente.")
                except Exception as e_srch:
                    st.error(f"Errore durante la ricerca online: {e_srch}")

        # Se cliccato Inserisci o risolto
        if btn_add_manual and input_isin_code:
            final_yf_ticker = st.session_state.get("suggested_yf_val") or input_isin_code
            desc_val = input_asset_desc or st.session_state.get("suggested_yf_name", "Manuale")
            
            # 1. Salva su DB
            if engine_curr is not None:
                try:
                    with engine_curr.begin() as conn:
                        if engine_curr.dialect.name == "sqlite":
                            conn.execute(sqlt("""
                                INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                VALUES (:input_ticker, :yfinance_ticker, :description)
                                ON CONFLICT(input_ticker) DO UPDATE SET
                                    yfinance_ticker = excluded.yfinance_ticker,
                                    description = excluded.description
                            """), {"input_ticker": input_isin_code, "yfinance_ticker": final_yf_ticker, "description": desc_val})
                        else:
                            conn.execute(sqlt("""
                                INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                VALUES (:input_ticker, :yfinance_ticker, :description)
                                ON DUPLICATE KEY UPDATE
                                    yfinance_ticker = VALUES(yfinance_ticker),
                                    description = VALUES(description)
                            """), {"input_ticker": input_isin_code, "yfinance_ticker": final_yf_ticker, "description": desc_val})
                except Exception as e_db:
                    st.warning(f"Nota DB: {e_db}")

            # 2. Salva su config.json
            cfg_save_data = {}
            if cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        cfg_save_data = json.load(f)
                except Exception:
                    pass
            if "ticker_mapping" not in cfg_save_data:
                cfg_save_data["ticker_mapping"] = {}
            cfg_save_data["ticker_mapping"][input_isin_code] = final_yf_ticker
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg_save_data, f, indent=4)
                
            st.success(f"✅ Mappatura **{input_isin_code} ➔ {final_yf_ticker}** registrata nel DB e nel Config!")
            if "suggested_yf_val" in st.session_state: del st.session_state["suggested_yf_val"]
            if "suggested_yf_name" in st.session_state: del st.session_state["suggested_yf_name"]
            st.rerun()

    # 3. Tabella Anagrafica Completa (Data Editor)
    st.markdown("##### 📋 Anagrafica Mappature Attive (Tabella Database & Config)")
    df_mappings = pd.DataFrame(list(db_mapping_dict.values()))
    if not df_mappings.empty:
        df_mappings = df_mappings[["input_ticker", "yfinance_ticker", "description"]].rename(columns={
            "input_ticker": "ISIN / Ticker Input",
            "yfinance_ticker": "Ticker Yahoo Finance",
            "description": "Descrizione / Strumento"
        }).sort_values("ISIN / Ticker Input")
    else:
        df_mappings = pd.DataFrame(columns=["ISIN / Ticker Input", "Ticker Yahoo Finance", "Descrizione / Strumento"])

    edited_mappings_df = st.data_editor(
        df_mappings,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="editor_isin_mappings"
    )

    col_save_m1, col_save_m2, col_save_m3 = st.columns([1.5, 1.5, 1.2])
    with col_save_m1:
        if st.button("💾 Salva Tutte le Modifiche nel DB & Config", type="primary", use_container_width=True, key="btn_save_all_mappings"):
            if not edited_mappings_df.empty:
                clean_json_map = {}
                db_recs = []
                for _, r in edited_mappings_df.iterrows():
                    in_t = str(r.get("ISIN / Ticker Input", "")).strip().upper()
                    yf_t = str(r.get("Ticker Yahoo Finance", "")).strip().upper()
                    d_t = str(r.get("Descrizione / Strumento", "")).strip()
                    if in_t and yf_t and in_t != "NAN":
                        clean_json_map[in_t] = yf_t
                        db_recs.append({"input_ticker": in_t, "yfinance_ticker": yf_t, "description": d_t})

                # Scrittura config.json
                cfg_obj = {}
                if cfg_file.exists():
                    try:
                        with open(cfg_file, "r", encoding="utf-8") as f: cfg_obj = json.load(f)
                    except Exception: pass
                cfg_obj["ticker_mapping"] = clean_json_map
                with open(cfg_file, "w", encoding="utf-8") as f:
                    json.dump(cfg_obj, f, indent=4)

                # Scrittura Database
                if engine_curr is not None and db_recs:
                    try:
                        with engine_curr.begin() as conn:
                            conn.execute(sqlt("DELETE FROM asset_mapping"))
                            for rec in db_recs:
                                conn.execute(sqlt("""
                                    INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                    VALUES (:input_ticker, :yfinance_ticker, :description)
                                """), rec)
                    except Exception as e_dbs:
                        st.warning(f"Nota aggiornamento DB: {e_dbs}")

                st.success("✅ Tutte le modifiche sono state allineate su Database (`asset_mapping`) e `config.json`!")
                st.rerun()

    with col_save_m2:
        if st.button("🔄 Sincronizza config.json ➔ Tabella DB", use_container_width=True, key="btn_sync_cfg_to_db"):
            if cfg_file.exists() and engine_curr is not None:
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f: cfg_d = json.load(f)
                    tk_map = cfg_d.get("ticker_mapping", {})
                    with engine_curr.begin() as conn:
                        for k, v in tk_map.items():
                            k_c = str(k).strip().upper()
                            v_c = str(v).strip().upper()
                            if k_c and v_c and k_c != "NAN":
                                if engine_curr.dialect.name == "sqlite":
                                    conn.execute(sqlt("""
                                        INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                        VALUES (:input_ticker, :yfinance_ticker, :description)
                                        ON CONFLICT(input_ticker) DO UPDATE SET yfinance_ticker = excluded.yfinance_ticker
                                    """), {"input_ticker": k_c, "yfinance_ticker": v_c, "description": "Sincronizzato da config.json"})
                                else:
                                    conn.execute(sqlt("""
                                        INSERT INTO asset_mapping (input_ticker, yfinance_ticker, description)
                                        VALUES (:input_ticker, :yfinance_ticker, :description)
                                        ON DUPLICATE KEY UPDATE yfinance_ticker = VALUES(yfinance_ticker)
                                    """), {"input_ticker": k_c, "yfinance_ticker": v_c, "description": "Sincronizzato da config.json"})
                    st.success(f"✅ Sincronizzate con successo {len(tk_map)} mappature nella tabella DB `asset_mapping`!")
                    st.rerun()
                except Exception as e_syn:
                    st.error(f"Errore sincronizzazione: {e_syn}")

    with col_save_m3:
        csv_map_bytes = edited_mappings_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Esporta CSV Mappature",
            data=csv_map_bytes,
            file_name="asset_mapping_argus.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_mappings_csv"
        )


# =============================================================
# TAB 4: TELEMETRIA DI SISTEMA & STORAGE PROFILER
# =============================================================
with tab_diagnostics:
    section("🩺 Diagnostica di Sistema, Memoria DB & Multi-Tier Cache Shield")
    
    col_head_diag1, col_head_diag2 = st.columns([3.2, 1.1])
    with col_head_diag1:
        st.caption("Profilazione avanzata dello storage su disco, memoria RAM di processo, integrità database e benchmark latenza dei 26 motori quantitativi.")
    with col_head_diag2:
        glossary_modal("ℹ️ Guida alla Diagnostica & Storage Profiler", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. STORAGE & MEMORIA -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🩺 1. Profiler di Memoria, DB & Multi-Tier Cache Shield</div>
  <div style="margin-bottom: 6px;"><b>Cos'è:</b> Il centro di diagnostica che monitora l'occupazione fisica del database SQL, la memoria RAM (RSS), la frammentazione su disco e la cache multi-tier anti-rate limit.</div>
  <div><b>🎯 Obiettivo:</b> Garantire prestazioni sub-millisecondo per tutti i 26 motori quantitativi senza memory leak.</div>
</div>

<!-- 2. AZIONI 1-CLICK -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(56,189,248,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #38bdf8; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📐 2. Azioni di Manutenzione 1-Click</div>
  <div style="background: rgba(56,189,248,0.08); border-left: 3px solid #38bdf8; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #7dd3fc; font-size: 12.5px; line-height: 1.45;">
    • <b>VACUUM & Compatta DB:</b> Rilascia lo spazio su disco dei record cancellati.<br>
    • <b>Pulisci Cache Scaduta:</b> Rimuove i prezzi storici più vecchi del TTL di 24h.<br>
    • <b>Reindicizza DB:</b> Rigenera gli indici B-Tree per query istantanee.
  </div>
  <div><b>🔍 Come leggerlo:</b> Stato <i>🟢 Integro (100% Operativo)</i> e frammentazione &lt; 5% indicano un ambiente ad efficienza massima.</div>
</div>

</div>
""", button_label="💡 Come funziona la Diagnostica?")

    diag_res = run_system_health_check(st.session_state.get("results"))
    cache_st = diag_res["cache_metrics"]
    storage_st = diag_res["storage_profile"]

    # KPI Cards Superiori
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        metric_card(
            "Stato Piattaforma",
            diag_res["overall_status"],
            f"{diag_res['health_score']:.0f}% Efficienza",
            positive=True
        )
    with col_d2:
        metric_card(
            "Storage Totale Disco",
            f"{storage_st['total_storage_mb']:.2f} MB",
            f"{storage_st['reclaimable_kb']} KB compattabili",
            positive=(storage_st['reclaimable_kb'] == 0)
        )
    with col_d3:
        metric_card(
            "Memoria RAM Processo",
            f"{storage_st['process_ram_mb']:.1f} MB",
            f"Oggetti Sessione: {storage_st['session_objects_ram_kb']:.1f} KB",
            positive=True
        )
    with col_d4:
        metric_card(
            "Multi-Tier Cache Shield",
            f"{cache_st['l2_disk_entries']} Voci SQLite",
            f"{cache_st['payload_size_kb']} KB salvati (TTL 24h)",
            positive=True
        )

    st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)

    # Tabs Tematiche per Diagnostica
    tab_diag_db, tab_diag_cache, tab_diag_lat = st.tabs([
        "🗄️ Storage & Memoria DB (Footprint)",
        "🛡️ Multi-Tier Cache Shield (Yahoo Finance)",
        "⚡ Benchmark Latenza Motori Quantitativi"
    ])

    with tab_diag_db:
        col_chart, col_maint = st.columns([1.6, 1.4])
        
        with col_chart:
            st.markdown("##### 📊 Ripartizione Storage per Tabella / File")
            df_tb = storage_st["table_breakdown"]
            if not df_tb.empty and "Spazio Reale (Bytes)" in df_tb.columns:
                import plotly.express as px
                fig_donut = px.pie(
                    df_tb,
                    names="Tabella / Risorsa",
                    values="Spazio Reale (Bytes)",
                    hole=0.45,
                    color_discrete_sequence=["#ff9900", "#58a6ff", "#3fb950", "#d29922", "#a371f7", "#f85149"]
                )
                fig_donut.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hoverinfo="label+value+percent",
                    marker=dict(line=dict(color="#161b22", width=2))
                )
                fig_donut.update_layout(
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=240,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#c9d1d9", size=11)
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Nessuna tabella presente nei database locali.")

        with col_maint:
            st.markdown("##### 🛠️ Strumenti di Manutenzione 1-Click")
            st.markdown('<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:12px; margin-bottom:10px;">', unsafe_allow_html=True)
            
            c_btn_vac, c_btn_clean = st.columns(2)
            with c_btn_vac:
                if st.button("🧹 VACUUM & Compatta DB", use_container_width=True, help="Esegue VACUUM su tutti i file SQLite recuperando lo spazio dei record cancellati", key="diag_btn_vacuum"):
                    opt_res = optimize_database_storage()
                    st.success(f"Compattazione completata! Recuperati: {opt_res['reclaimed_kb']} KB.")
                    st.rerun()
                    
            with c_btn_clean:
                if st.button("⚡ Pulisci Cache Scaduta", use_container_width=True, help="Elimina solo i record di prezzo e info più vecchi di 24 ore", key="diag_btn_clean_cache"):
                    del_cnt = clean_expired_cache_records()
                    st.success(f"Pulizia cache completata! Eliminati {del_cnt} record scaduti.")
                    st.rerun()
                    
            if st.button("🔄 Rigenera Indici B-Tree (Reindex)", use_container_width=True, help="Rigenera gli indici su ticker e data per accelerare le query storiche", key="diag_btn_reindex"):
                if reindex_databases():
                    st.success("Reindicizzazione completata con successo!")
                    st.rerun()
                else:
                    st.error("Errore durante la reindicizzazione.")
                    
            st.markdown(f"""
            <div style="font-size:11.5px; color:#8b949e; margin-top:8px;">
            • <b>Integrità Totale:</b> <span style="color:#3fb950;">{storage_st['integrity_summary']}</span><br>
            • <b>Profili Multi-Portafoglio:</b> {storage_st['multi_portfolios_count']} file ({storage_st['multi_portfolios_kb']} KB)
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("##### 📋 Dettaglio Volumi e Tabelle nel Database")
        if not df_tb.empty:
            st.dataframe(
                df_tb[["Contenitore", "Tabella / Risorsa", "N° Record", "Dimensione Stimata", "Stato Integrità", "Categoria"]],
                use_container_width=True,
                hide_index=True
            )

    with tab_diag_cache:
        col_c_left, col_c_right = st.columns([1.5, 1.5])
        with col_c_left:
            st.markdown("##### 🛡️ Parametri Operativi Cache Multi-Tier")
            st.markdown(f"""
            * **Stato Scudo Anti-429**: `{cache_st['status']}`
            * **Architettura Caching**: `{cache_st['shield_version']}`
            * **Oggetti in RAM L1 (Fast Cache)**: `{cache_st['l1_memory_items']}`
            * **Record su Disco SQLite (Tier 2)**: `{cache_st['l2_disk_entries']}`
            * **Ticker Distinti in Cache**: `{cache_st['distinct_tickers']}`
            * **Spazio Occupato da Payload JSON**: `{cache_st['payload_size_kb']} KB`
            """)
        with col_c_right:
            st.markdown("##### 🧹 Azioni Rapide Cache")
            st.warning("Lo svuotamento totale della cache richiederà di riscaricare i dati di mercato da Yahoo Finance alla prossima esecuzione.")
            if st.button("🗑️ Svuota Interamente Cache L1 & L2", type="secondary", use_container_width=True, key="diag_btn_flush_all_cache"):
                cleared_n = clear_cache()
                st.success(f"Cache svuotata! Rimossi {cleared_n} record.")
                st.rerun()

    with tab_diag_lat:
        st.markdown("##### ⚡ Latenza Algoritmi Quantitativi (Millisecondi)")
        st.dataframe(diag_res["engine_benchmarks"], use_container_width=True, hide_index=True)
        
        st.markdown("##### 🖥️ Specifiche Ambiente di Esecuzione")
        env_dict = diag_res["environment"]
        st.markdown(f"""
        * **Python Version**: `{env_dict['python_version']}`
        * **Piattaforma OS**: `{env_dict['os_platform']}`
        * **NumPy Version**: `{env_dict['numpy_version']}`
        * **Pandas Version**: `{env_dict['pandas_version']}`
        * **Determinismo Seed Stocastico**: `{'🟢 Confermato (Numpy 100% Deterministico)' if diag_res['seed_deterministic'] else '🔴 Non Deterministico'}`
        """)

# =============================================================
# TAB 5: MOTORE ANALITICO EMBEDDED DUCKDB (OLAP & SQL SANDBOX)
# =============================================================
with tab_duckdb:
    col_d_title, col_d_modal = st.columns([3.5, 1.2])
    with col_d_title:
        st.markdown("### ⚡ Motore Analitico In-Process DuckDB & Accelerazione Parquet")
        st.caption("Interrogazione SQL analitica (OLAP) in-memory a latenza sub-millisecondo, aggregazioni multi-dimensionali ed esportazione colonnare Apache Parquet.")
    with col_d_modal:
        st.markdown('<div style="margin-top: 8px;"></div>', unsafe_allow_html=True)
        render_duckdb_modal(button_label="ℹ️ Guida al Motore DuckDB & Parquet", use_popover=False)

    duck_info = duckdb_engine.get_duckdb_system_info()

    # Prepara DataFrames di contesto
    pos_df = st.session_state.get("positions_df")
    tx_df = st.session_state.get("transactions_df")

    # Fallback se non ancora caricato
    if pos_df is None or pos_df.empty:
        pos_df = pd.DataFrame([
            {"ticker": "AAPL", "asset_name": "Apple Inc.", "asset_class": "Stock", "sector": "Technology", "currency": "USD", "current_value": 2200.0, "weight_pct": 20.0, "pnl_pct": 14.5},
            {"ticker": "MSFT", "asset_name": "Microsoft Corp.", "asset_class": "Stock", "sector": "Technology", "currency": "USD", "current_value": 4400.0, "weight_pct": 40.0, "pnl_pct": 22.1},
            {"ticker": "NVDA", "asset_name": "NVIDIA Corp.", "asset_class": "Stock", "sector": "Technology", "currency": "USD", "current_value": 1250.0, "weight_pct": 11.4, "pnl_pct": 68.3},
            {"ticker": "RACE.MI", "asset_name": "Ferrari N.V.", "asset_class": "Stock", "sector": "Consumer Cyclical", "currency": "EUR", "current_value": 2100.0, "weight_pct": 19.1, "pnl_pct": 8.4},
            {"ticker": "BTC-USD", "asset_name": "Bitcoin USD", "asset_class": "Crypto", "sector": "Digital Assets", "currency": "USD", "current_value": 1050.0, "weight_pct": 9.5, "pnl_pct": -4.2}
        ])

    if tx_df is None or tx_df.empty:
        tx_df = pd.DataFrame([
            {"tx_date": "2023-01-15", "ticker": "AAPL", "tx_type": "BUY", "quantity": 10, "price": 135.0, "currency": "USD", "fees": 1.5},
            {"tx_date": "2023-04-20", "ticker": "MSFT", "tx_type": "BUY", "quantity": 10, "price": 280.0, "currency": "USD", "fees": 1.5},
            {"tx_date": "2023-09-10", "ticker": "NVDA", "tx_type": "BUY", "quantity": 10, "price": 420.0, "currency": "USD", "fees": 2.0},
            {"tx_date": "2024-02-01", "ticker": "RACE.MI", "tx_type": "BUY", "quantity": 5, "price": 320.0, "currency": "EUR", "fees": 2.5},
            {"tx_date": "2024-06-15", "ticker": "BTC-USD", "tx_type": "BUY", "quantity": 0.02, "price": 62000.0, "currency": "USD", "fees": 3.0}
        ])

    context_tables = {
        "positions": pos_df,
        "transactions": tx_df
    }

    pq_stats = duckdb_engine.get_parquet_compression_ratio(pos_df)

    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        metric_card("Stato Motore DuckDB", f"v{duck_info['version']}", duck_info["engine_mode"], True)
    with col_k2:
        metric_card("SIMD Vectorization", duck_info["vectorization"], f"{duck_info['threads']} Core Paralleli", True)
    with col_k3:
        metric_card("Compressione Parquet", f"{pq_stats['space_saved_pct']:.1f}%", f"{pq_stats['parquet_bytes']} B vs {pq_stats['csv_bytes']} B CSV", True)
    with col_k4:
        metric_card("Tabelle In-Memory", f"{len(context_tables)} Registrate", "positions, transactions", True)

    st.markdown("---")

    st.markdown("#### ⚡ 1. Preset di Analisi OLAP Istituzionale (1-Click SQL):")
    st.caption("Seleziona una delle pipeline analitiche preconfigurate per eseguire all'istante aggregazioni complesse.")

    presets = duckdb_engine.get_preset_olap_queries()
    preset_cols = st.columns(4)

    if "current_duck_sql" not in st.session_state:
        st.session_state["current_duck_sql"] = presets["cube_exposure"]["sql"]

    with preset_cols[0]:
        if st.button("📦 Cubo Multi-Dimensionale", use_container_width=True, help=presets["cube_exposure"]["description"]):
            st.session_state["current_duck_sql"] = presets["cube_exposure"]["sql"]
    with preset_cols[1]:
        if st.button("🏆 Ranking & QUALIFY", use_container_width=True, help=presets["sector_ranking"]["description"]):
            st.session_state["current_duck_sql"] = presets["sector_ranking"]["sql"]
    with preset_cols[2]:
        if st.button("💰 Storico Volumi & Mese", use_container_width=True, help=presets["monthly_tx_rollup"]["description"]):
            st.session_state["current_duck_sql"] = presets["monthly_tx_rollup"]["sql"]
    with preset_cols[3]:
        if st.button("📊 Matrice Rischio FX", use_container_width=True, help=presets["fx_exposure_matrix"]["description"]):
            st.session_state["current_duck_sql"] = presets["fx_exposure_matrix"]["sql"]

    st.markdown("#### 💻 2. Console SQL Interattiva (Interactive SQL Sandbox):")
    st.caption("Scrivi ed esegui qualsiasi query SQL sulle tabelle in-memory `positions` e `transactions`.")

    custom_sql = st.text_area(
        "Editor Query SQL (DuckDB Engine):",
        value=st.session_state["current_duck_sql"],
        height=140,
        key="duckdb_sql_editor_area"
    )

    col_btn_run, col_btn_pq = st.columns([2.5, 1.5])
    with col_btn_run:
        btn_run_sql = st.button("⚡ Esegui Query SQL (DuckDB Engine)", type="primary", use_container_width=True)
    with col_btn_pq:
        pq_bytes = duckdb_engine.export_portfolio_to_parquet(pos_df)
        st.download_button(
            label="📦 Scarica Portafoglio in Apache Parquet (.parquet)",
            data=pq_bytes,
            file_name="argus_portfolio_master.parquet",
            mime="application/octet-stream",
            use_container_width=True
        )

    if btn_run_sql or "last_duck_res" not in st.session_state:
        res = duckdb_engine.run_duckdb_olap_query(custom_sql, context_dfs=context_tables)
        st.session_state["last_duck_res"] = res

    last_res = st.session_state.get("last_duck_res")
    if last_res:
        if last_res["success"]:
            st.success(f"⚡ Query eseguita con successo in **{last_res['latency_ms']:.3f} ms** | Restituite **{last_res['row_count']} righe**.")
            st.dataframe(last_res["df"], use_container_width=True)
        else:
            st.error(f"❌ Errore durante l'esecuzione della query SQL: {last_res['error']}")
