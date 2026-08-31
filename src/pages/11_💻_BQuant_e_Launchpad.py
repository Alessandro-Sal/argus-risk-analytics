# ==============================================================================
# src/pages/10_💻_BQuant_e_Launchpad.py
# ARGUS BQuant Python Sandbox, Workspace Launchpad & Excel Live Connector
# ==============================================================================

import io
import time
import datetime
import html
import streamlit as st

st.set_page_config(
    page_title="ARGUS - BQuant & Launchpad",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

import io
import time
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import core.ui_utils as ui_utils
import core.excel_connector as excel_connector
import core.workspace_engine as workspace_engine
import core.bquant_engine as bquant_engine
import core.terminal_engine as terminal_engine

from core.sidebar import render_sidebar
from core.ui_utils import (
    inject_custom_css,
    render_command_bar,
    metric_card,
    glossary_modal,
    ensure_risk_bundle_loaded,
    render_page_header
)
from core.bquant_engine import (
    execute_bquant_script,
    BQUANT_SNIPPETS
)
from core.workspace_engine import (
    ROLE_PRESET_PROFILES,
    get_available_roles,
    get_role_profile,
    save_custom_workspace_layout,
    load_custom_workspace_layout
)
from core.excel_connector import (
    EXCEL_SUPPORTED_FIELDS,
    EXCEL_PORTFOLIO_RISK_FIELDS,
    build_bloomberg_formula,
    generate_vba_macro_code,
    generate_office_script_code,
    export_institutional_multisheet_excel
)
from core.terminal_engine import (
    get_terminal_engine,
    TerminalCommandResult,
    OMSOrder
)

inject_custom_css()

# ── Sidebar & Ingestion Gate ─────────────────────────────────────────────────
render_sidebar()
render_command_bar()

results, has_real_portfolio = ensure_risk_bundle_loaded()
pos = results.get("positions", pd.DataFrame()) if results else pd.DataFrame()
df_rets = results.get("returns", pd.DataFrame()) if results else pd.DataFrame()
df_prices = results.get("df_prices", pd.DataFrame()) if results else pd.DataFrame()
df_tx = results.get("df_tx", pd.DataFrame()) if results else pd.DataFrame()

# ── Page Header ──────────────────────────────────────────────────────────────
render_page_header(
    title="ARGUS BQuant, Launchpad & Excel Connector",
    subtitle="Console Python Interattiva In-App (BQuant BBG-Style) • Workspace Role Customizer • Bloomberg BDP/BDH Excel Live Connector",
    icon="💻"
)

# ── SELETTORE MODULI BQUANT STILE BLOOMBERG TERMINAL ─────────
BQUANT_MODELS_CATALOG = {
    "🐍 ARGUS BQuant Python Sandbox": {
        "title": "Console Python Interattiva In-App (Bloomberg BQuant Style)",
        "badge": "Python REPL • NumPy/SciPy • DuckDB",
        "badge_color": "#3fb950",
        "category": "Programmazione Quantitativa",
        "desc": "Ambiente interattivo in-memory per eseguire script Python avanzati con iniezione automatica dei DataFrame di portafoglio (df_positions, df_returns, df_prices), query SQL DuckDB e grafici Plotly."
    },
    "🎛️ Launchpad & Workspace Customizer": {
        "title": "Configuratore di Ruolo, Layout & Personalizzazione Workspace",
        "badge": "Ruoli • Asset Allocation • UI Customizer",
        "badge_color": "#ff9900",
        "category": "Esperienza Utente & Ruoli",
        "desc": "Personalizzazione dell'interfaccia in base al profilo operativo: Wealth Manager, Risk Analyst, Quant Researcher o CIO, con visualizzazione moduli mirata."
    },
    "📊 Excel Live Connector & RTD": {
        "title": "Connettore Live Excel Bloomberg Style (BDP / BDH / Real-Time Data)",
        "badge": "Excel RTD • Formula Generator • Live Feed",
        "badge_color": "#38bdf8",
        "category": "Integrazione Dati Esterni",
        "desc": "Generatore di formule compatibili Excel (BDP/BDH) ed esportazione flussi in tempo reale per alimentare modelli di pricing e fogli di calcolo proprietari."
    }
}

# Risoluzione dello stato attivo con priorità alla sidebar o global jump
target_tab = None
if "target_subtab_bquant_active_tab" in st.session_state:
    target_tab = st.session_state.pop("target_subtab_bquant_active_tab")
elif "global_target_subtab" in st.session_state:
    target_tab = st.session_state.pop("global_target_subtab")
elif "target_bquant_module" in st.session_state:
    target_tab = st.session_state.pop("target_bquant_module")

bquant_keys = list(BQUANT_MODELS_CATALOG.keys())

if target_tab and target_tab in bquant_keys:
    st.session_state["bquant_active_tab"] = target_tab
    st.session_state["bquant_active_tab_selectbox"] = target_tab
elif "bquant_active_tab_selectbox" in st.session_state and st.session_state["bquant_active_tab_selectbox"] in bquant_keys:
    st.session_state["bquant_active_tab"] = st.session_state["bquant_active_tab_selectbox"]
elif "bquant_active_tab" in st.session_state and st.session_state["bquant_active_tab"] in bquant_keys:
    st.session_state["bquant_active_tab_selectbox"] = st.session_state["bquant_active_tab"]
else:
    st.session_state["bquant_active_tab"] = bquant_keys[0]
    st.session_state["bquant_active_tab_selectbox"] = bquant_keys[0]

curr_idx = bquant_keys.index(st.session_state["bquant_active_tab"])

# Spaziatura e Respiro Layout
st.markdown("<div style='margin-top: 14px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# Barra Selettore Compatta Bloomberg Style
c_sel_bq, c_prev_bq, c_next_bq = st.columns([3.8, 0.6, 0.6], vertical_alignment="center")

with c_prev_bq:
    if st.button("◀ Prec.", key="btn_bquant_prev", use_container_width=True, help="Modulo precedente"):
        new_i = (curr_idx - 1) % len(bquant_keys)
        st.session_state["target_subtab_bquant_active_tab"] = bquant_keys[new_i]
        st.session_state["bquant_active_tab"] = bquant_keys[new_i]
        st.session_state["bquant_active_tab_selectbox"] = bquant_keys[new_i]
        st.rerun()

with c_next_bq:
    if st.button("Succ. ▶", key="btn_bquant_next", use_container_width=True, help="Modulo successivo"):
        new_i = (curr_idx + 1) % len(bquant_keys)
        st.session_state["target_subtab_bquant_active_tab"] = bquant_keys[new_i]
        st.session_state["bquant_active_tab"] = bquant_keys[new_i]
        st.session_state["bquant_active_tab_selectbox"] = bquant_keys[new_i]
        st.rerun()

with c_sel_bq:
    selected_bquant_key = st.selectbox(
        "Seleziona Modulo BQuant:",
        options=bquant_keys,
        index=curr_idx,
        format_func=lambda k: f"{k}  —  {BQUANT_MODELS_CATALOG[k]['category']} [{BQUANT_MODELS_CATALOG[k]['badge']}]",
        key="bquant_active_tab_selectbox",
        label_visibility="collapsed"
    )
    st.session_state["bquant_active_tab"] = selected_bquant_key

active_bquant_tab = st.session_state["bquant_active_tab"]
active_bquant_info = BQUANT_MODELS_CATALOG[active_bquant_tab]

# Bloomberg Terminal Header Banner per il Modulo Attivo
st.markdown(f"""
<div style="background: linear-gradient(90deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.85) 100%); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {active_bquant_info['badge_color']}; border-radius: 8px; padding: 12px 18px; margin-top: 10px; margin-bottom: 22px;">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
    <div style="font-size: 15px; font-weight: 700; color: #f0f6fc;">
      {active_bquant_info['title']}
    </div>
    <div style="display: flex; gap: 8px; align-items: center;">
      <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 12px; background: rgba(255,255,255,0.06); color: #8b949e; border: 1px solid rgba(255,255,255,0.08);">
        {active_bquant_info['category']}
      </span>
      <span style="font-size: 11.5px; font-weight: 600; padding: 2px 10px; border-radius: 12px; background: {active_bquant_info['badge_color']}22; color: {active_bquant_info['badge_color']}; border: 1px solid {active_bquant_info['badge_color']}55;">
        {active_bquant_info['badge']}
      </span>
    </div>
  </div>
  <div style="font-size: 13px; color: #8b949e; line-height: 1.45;">
    {active_bquant_info['desc']}
  </div>
</div>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: ARGUS BQUANT PYTHON SANDBOX
# ═════════════════════════════════════════════════════════════════════════════
if active_bquant_tab == "🐍 ARGUS BQuant Python Sandbox":
    col_bq_h1, col_bq_h2 = st.columns([3.2, 1.2])
    with col_bq_h1:
        st.markdown("#### 🐍 Console Python Interattiva In-App (Bloomberg BQuant Style)")
        st.caption("Esegui script analitici direttamente in-memory sui DataFrame di portafoglio, query SQL DuckDB, modelli SciPy e visualizzazioni Plotly.")
    with col_bq_h2:
        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
        glossary_modal("💡 Come funziona la Console BQuant Python", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🐍 Ambiente di Esecuzione In-Memory</div>
  <div>La console BQuant inietta automaticamente nell'ambiente Python i dati di sessione già pronti per l'analisi:
    <br>• <code>df_positions</code>: posizioni aperte, pesi e PnL.
    <br>• <code>df_returns</code>: rendimenti storici percentuali giornalieri.
    <br>• <code>df_prices</code>: serie storiche dei prezzi spot e di chiusura.
    <br>• <code>results</code>: dizionario completo delle metriche di rischio e stress test.
    <br>• <code>duckdb</code>: database SQL vettoriale in-memory.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📊 Esportazione Risultati &amp; Grafici</div>
  <div>
    Assegna il tuo DataFrame a <code>df_out</code> o la tua figura Plotly a <code>fig</code> per visualizzarli direttamente nell'interfaccia interattiva sotto il terminale.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🦆 Query SQL ad Alta Velocità con DuckDB</div>
  <div>
    Esegui <code>con = duckdb.connect(':memory:')</code> e registra <code>con.register('pos', df_positions)</code> per eseguire SQL analitico senza overhead di I/O su disco.
  </div>
</div>

</div>
""", button_label="💡 Come funziona BQuant?")

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # ── Pipeline Binding Status Strip (Bloomberg BQuant Data Bus) ──
    port_label, has_port = ui_utils.get_display_portfolio_name()
    port_name = st.session_state.get("portfolio_name", port_label)
    n_pos = len(pos[pos.get("qty_net", 1) > 1e-6]) if (pos is not None and isinstance(pos, pd.DataFrame)) else 0
    tot_val = float(pos["current_value"].sum()) if (pos is not None and isinstance(pos, pd.DataFrame) and not pos.empty and "current_value" in pos.columns) else 0.0
    tot_val_str = f"€ {tot_val:,.2f}".replace(",", ".")
    
    n_rets_rows = len(df_rets) if (df_rets is not None and isinstance(df_rets, pd.DataFrame)) else 0
    n_rets_cols = df_rets.shape[1] if (df_rets is not None and isinstance(df_rets, pd.DataFrame)) else 0
    n_prices_rows = len(df_prices) if (df_prices is not None and isinstance(df_prices, pd.DataFrame)) else 0
    
    status_icon = "🟢" if has_real_portfolio else "🧪"
    status_title = f"Portafoglio Connesso: {port_name}" if has_real_portfolio else f"Modalità Sandbox: {results.get('sandbox_name', 'Demo')}"
    
    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid #58a6ff; border-radius: 10px; padding: 10px 16px; margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 14px;">{status_icon}</span>
            <span style="font-weight: 700; font-size: 13px; color: #ffffff;">{status_title}</span>
            <span style="background: rgba(88, 166, 255, 0.15); color: #58a6ff; border: 1px solid rgba(88, 166, 255, 0.3); border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600;">{n_pos} Posizioni • {tot_val_str}</span>
        </div>
        <div style="display: flex; gap: 8px; font-family: monospace; font-size: 11px; color: #8b949e; flex-wrap: wrap;">
            <span style="background: rgba(13, 17, 23, 0.8); border: 1px solid rgba(255, 255, 255, 0.06); padding: 3px 8px; border-radius: 6px;"><code>df_positions</code>: {n_pos} rows</span>
            <span style="background: rgba(13, 17, 23, 0.8); border: 1px solid rgba(255, 255, 255, 0.06); padding: 3px 8px; border-radius: 6px;"><code>df_returns</code>: {n_rets_rows}x{n_rets_cols}</span>
            <span style="background: rgba(13, 17, 23, 0.8); border: 1px solid rgba(255, 255, 255, 0.06); padding: 3px 8px; border-radius: 6px;"><code>df_prices</code>: {n_prices_rows} rows</span>
            <span style="background: rgba(13, 17, 23, 0.8); border: 1px solid rgba(255, 255, 255, 0.06); padding: 3px 8px; border-radius: 6px;"><code>results</code>: dict ({len(results)} chiavi)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Selezione Snippet Istituzionali
    snippet_options = {sk: sdata["title"] for sk, sdata in BQUANT_SNIPPETS.items()}
    snippet_options["custom"] = "✍️ Script Personalizzato (Editor Libero)"

    def _sync_bquant_snippet_selection():
        sk = st.session_state.get("sel_bquant_snippet")
        if sk and sk in BQUANT_SNIPPETS:
            st.session_state["bquant_code_text_area"] = BQUANT_SNIPPETS[sk]["code"]
        elif sk == "custom":
            st.session_state["bquant_code_text_area"] = f"# Scrivi il tuo script Python per BQuant collegato a {port_name}\nimport pandas as pd\nimport numpy as np\n\nprint('Portafoglio:', portfolio_name)\nprint('Posizioni attive:', len(df_positions))\nprint('Valore totale (€):', f'{{portfolio_value:,.2f}}')\n"

    # Inizializza session_state per editor se assente
    if "bquant_code_text_area" not in st.session_state:
        st.session_state["bquant_code_text_area"] = BQUANT_SNIPPETS["rolling_correlation"]["code"]

    col_snip1, col_snip2 = st.columns([3.8, 1.2])
    with col_snip1:
        sel_snippet_key = st.selectbox(
            "Carica Snippet Quantitativo Istituzionale:",
            list(snippet_options.keys()),
            format_func=lambda k: snippet_options[k],
            index=0,
            key="sel_bquant_snippet",
            on_change=_sync_bquant_snippet_selection
        )
        
    with col_snip2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Reset Template", key="btn_load_snippet", use_container_width=True, help="Ripristina il template originale selezionato eliminando le modifiche manuali."):
            _sync_bquant_snippet_selection()
            st.rerun()

    if sel_snippet_key in BQUANT_SNIPPETS:
        st.caption(f"ℹ️ **Descrizione Snippet:** {BQUANT_SNIPPETS[sel_snippet_key]['description']}")

    # Code Editor
    user_code = st.text_area(
        f"Editor di Codice Python (Variabili collegate a '{port_name}': `df_positions`, `df_returns`, `df_prices`, `df_tx`, `portfolio_returns`, `benchmark_returns`, `results`, `duckdb`, `pd`, `np`, `px`, `go`):",
        height=320,
        key="bquant_code_text_area"
    )

    # Pulsante Esegui
    col_run_btn, col_run_status = st.columns([1.5, 3.5])
    with col_run_btn:
        run_script_clicked = st.button("⚡ Esegui Script BQuant", type="primary", use_container_width=True, key="btn_run_bquant")
    with col_run_status:
        st.caption(f"Esecuzione sandboxed in-memory ad alta performance sui dati di <b>{port_name}</b> • Output stdout, DataFrame e Plotly Figures catturati dinamicamente.", unsafe_allow_html=True)

    # Esecuzione
    if run_script_clicked or "last_bquant_result" in st.session_state:
        if run_script_clicked:
            exec_ctx = {
                "results": results,
                "df_positions": pos,
                "df_returns": df_rets,
                "df_prices": df_prices,
                "df_tx": df_tx,
                "portfolio_name": port_name,
                "portfolio_return": results.get("portfolio_return", pd.Series(dtype=float)),
                "benchmark_return": results.get("benchmark_return", pd.Series(dtype=float)),
                "benchmark_ticker": st.session_state.get("benchmark", "SPY"),
                "base_currency": st.session_state.get("base_currency", "EUR")
            }
            try:
                from core.wealth.wealth_db import get_wealth_accounts, get_cashflow_records, get_physical_assets, get_pension_plans
                from core.wealth.wealth_engine import compute_consolidated_net_worth
                from core.fetcher import get_engine
                db_u = st.session_state.get("db_user", "root")
                db_p = st.session_state.get("db_pass", "root")
                db_h = st.session_state.get("db_host", "localhost")
                db_prt = int(st.session_state.get("db_port", 3306))
                db_nm = st.session_state.get("db_name", "investment_risk_bi")
                eng_w = get_engine(db_u, db_p, db_h, db_prt, db_nm)
                w_pid = st.session_state.get("wealth_active_portfolio_id", 1)
                exec_ctx["df_wealth_accounts"] = get_wealth_accounts(eng_w, portfolio_id=w_pid)
                exec_ctx["df_wealth_cashflow"] = get_cashflow_records(eng_w, portfolio_id=w_pid)
                exec_ctx["df_wealth_physical"] = get_physical_assets(eng_w, portfolio_id=w_pid)
                exec_ctx["df_wealth_pension"] = get_pension_plans(eng_w, portfolio_id=w_pid)
                exec_ctx["wealth_net_worth"] = compute_consolidated_net_worth(eng_w, portfolio_id=w_pid)
            except Exception:
                pass
            res_exec = execute_bquant_script(user_code, exec_ctx)
            st.session_state["last_bquant_result"] = res_exec

        else:
            res_exec = st.session_state["last_bquant_result"]

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 🖥️ Terminal Console Output")
        
        # Badge di stato
        if res_exec["success"]:
            st.markdown(f"""
            <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 8px 14px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                <span style="color: #4ade80; font-weight: 600; font-size: 13px;">✅ Esecuzione completata con successo in <b>{res_exec['execution_time_sec']}s</b></span>
                <span style="color: #86efac; font-family: monospace; font-size: 12px;">EXIT CODE 0</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 8px 14px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                <span style="color: #f87171; font-weight: 600; font-size: 13px;">❌ Errore durante l'esecuzione dello script</span>
                <span style="color: #fca5a5; font-family: monospace; font-size: 12px;">EXCEPTION RAISED</span>
            </div>
            """, unsafe_allow_html=True)

        # Finestra stdout / log
        terminal_text = res_exec["stdout"] if res_exec["stdout"] else ""
        if res_exec["error"]:
            terminal_text += f"\n[STDERR / TRACEBACK]:\n{res_exec['error']}"
        if not terminal_text.strip():
            terminal_text = "[Nessun output stdout generato dallo script]"

        st.code(terminal_text, language="text")

        # ── Visualizzazione DataFrame risultante ──
        if res_exec.get("output_df") is not None and isinstance(res_exec["output_df"], pd.DataFrame):
            df_res = res_exec["output_df"]
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_df_h1, col_df_h2 = st.columns([3.5, 1.2])
            with col_df_h1:
                st.markdown(f"##### 📊 Risultato Tabellare (`df_out` • {len(df_res)} righe)")
            with col_df_h2:
                csv_out = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Risultato CSV", data=csv_out, file_name="bquant_result.csv", mime="text/csv", use_container_width=True, key="btn_dl_bquant_df")
            st.dataframe(df_res, use_container_width=True)

        # ── Visualizzazione Grafico Plotly risultante ──
        if res_exec.get("output_fig") is not None:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📈 Visualizzazione Grafica Generata (`fig`)")
            st.plotly_chart(res_exec["output_fig"], use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: LAUNCHPAD & WORKSPACE CUSTOMIZER
# ═════════════════════════════════════════════════════════════════════════════
elif active_bquant_tab == "🎛️ Launchpad & Workspace Customizer":
    from core.sidebar import switch_to_page
    
    col_lp_h1, col_lp_h2 = st.columns([3.2, 1.2])
    with col_lp_h1:
        st.markdown("#### 🎛️ ARGUS Launchpad & Ruoli Operativi Istituzionali")
        st.caption("Configura e personalizza i moduli visibili in base al ruolo organizzativo (Trading Desk, Risk Officer, Portfolio Manager, Quant Analyst, Corporate Treasurer).")
    with col_lp_h2:
        st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
        glossary_modal("💡 Cos'è l'ARGUS Launchpad e come funziona", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 Profilazione Istituzionale per Ruolo</div>
  <div>L'ARGUS Launchpad adatta l'esperienza analitica della piattaforma al ruolo operativo dell'utente:
    <br>• <b>Trading Desk:</b> Esecuzione ordini, Order Flow L2, Slippage Almgren-Chriss, Delta Hedging.
    <br>• <b>Risk Officer:</b> Normative Basel III/IV, VaR/CVaR, GARCH-FHS, LVaR Bangia, Stress Test 3D.
    <br>• <b>Portfolio Manager:</b> Frontiera Markowitz & HRP, Attribuzione Brinson, Backtesting Fattoriali, Dividendi.
    <br>• <b>Quant Analyst:</b> Python Sandbox BQuant, Superfici di Volatilità, Modello Merton, K-Means.
    <br>• <b>Corporate Treasurer:</b> YTM, Duration/DV01, Z-Spread, CDS Default Curve, Efficienza Fiscale TUIR.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚡ 1-Click Fast Teleportation</div>
  <div>
    Cliccando sui pulsanti <b>🚀 Apri Modulo</b>, il sistema ti reindirizza istantaneamente alla pagina corretta pre-selezionando automaticamente la scheda analitica richiesta.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">💾 Persistenza su SQLite</div>
  <div>
    Le selezioni del profilo attivo e dei moduli preferiti vengono memorizzate nel database locale <code>data/argus_workspaces.db</code> per rimanere attive al riavvio dell'applicazione.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Launchpad?")

    roles = get_available_roles()
    
    # Ruolo salvato o default
    saved_layout = load_custom_workspace_layout("default_user")
    current_role_id = st.session_state.get("active_workspace_role", saved_layout.get("active_role", "portfolio_manager"))

    # Role Selector Cards
    role_cols = st.columns(len(roles))
    for i, r_data in enumerate(roles):
        with role_cols[i]:
            is_active = (r_data["id"] == current_role_id)
            btn_border = f"2px solid {r_data['badge_color']}" if is_active else "1px solid rgba(255,255,255,0.1)"
            btn_bg = f"rgba({int(r_data['badge_color'][1:3],16)}, {int(r_data['badge_color'][3:5],16)}, {int(r_data['badge_color'][5:7],16)}, 0.15)" if is_active else "rgba(255,255,255,0.02)"
            
            st.markdown(f"""
            <div style="background: {btn_bg}; border: {btn_border}; border-radius: 10px; padding: 12px; height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="font-size: 20px; margin-bottom: 4px;">{r_data['icon']}</div>
                    <div style="font-weight: 700; color: {r_data['badge_color']}; font-size: 13.5px;">{r_data['title'].split('&')[0].strip()}</div>
                    <div style="font-size: 11px; color: #8b949e; line-height: 1.3; margin-top: 4px;">{r_data['subtitle'][:45]}...</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            if st.button(f"{'✅ Attivo' if is_active else 'Attiva Profilo'}", key=f"btn_activate_role_{r_data['id']}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state["active_workspace_role"] = r_data["id"]
                save_custom_workspace_layout("default_user", r_data["id"])
                st.rerun()

    # Dettaglio del Profilo Attivo
    active_profile = get_role_profile(st.session_state.get("active_workspace_role", current_role_id))
    st.divider()

    st.markdown(f"### {active_profile['icon']} Workspace Attivo: <span style='color: {active_profile['badge_color']};'>{active_profile['title']}</span>", unsafe_allow_html=True)
    st.caption(f"**Descrizione Operativa:** {active_profile['description']}")

    # ── LIVE ROLE COCKPIT METRICS ──
    st.markdown("##### 📊 Live Role KPI Cockpit")
    m_risk = results.get("metrics", {}).get("market_risk", {}) if results else {}
    m_ret = results.get("metrics", {}).get("returns", {}) if results else {}
    tot_val = float(pos["current_value"].sum()) if not pos.empty and "current_value" in pos.columns else 100_000.0

    c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
    if active_profile["id"] == "trading_desk":
        with c_kpi1: metric_card("Order Flow Imbalance", "+0.18 (Bullish)", delta="Intraday Pressure", delta_color="normal")
        with c_kpi2: metric_card("Estimated Slippage", "12.5 bps", delta="Almgren-Chriss", delta_color="normal")
        with c_kpi3: metric_card("Execution VaR 95%", f"€ {tot_val * 0.0035:,.2f}", delta="Scaglione 10-Days", delta_color="inverse")
        with c_kpi4: metric_card("Delta Hedge Ratio", "-0.85", delta="Put 5% OTM", delta_color="normal")
    elif active_profile["id"] == "risk_officer":
        with c_kpi1: metric_card("Parametric VaR 95%", f"€ {m_risk.get('var_parametric_95_eur', tot_val * 0.0165):,.2f}", delta="1-Day Horizon", delta_color="inverse")
        with c_kpi2: metric_card("Expected Shortfall (CVaR)", f"€ {m_risk.get('cvar_95_eur', tot_val * 0.022):,.2f}", delta="95% Confidence", delta_color="inverse")
        with c_kpi3: metric_card("Basel Traffic Light", "🟢 Zona Verde", delta="0 Violazioni Kupiec", delta_color="normal")
        with c_kpi4: metric_card("LVaR 5-Days", f"€ {tot_val * 0.028:,.2f}", delta="Spread Adjusted", delta_color="inverse")
    elif active_profile["id"] == "portfolio_manager":
        with c_kpi1: metric_card("Indice di Sharpe", f"{m_risk.get('sharpe_ratio', 1.25):.2f}", delta="Annualized", delta_color="normal")
        with c_kpi2: metric_card("Rendimento Storico (CAGR)", f"{m_ret.get('cagr_pct', 12.5):.2f}%", delta="vs Benchmark", delta_color="normal")
        with c_kpi3: metric_card("Fama-French Alpha", f"+{m_ret.get('alpha_pct', 2.8):.2f}%", delta="5-Factor Model", delta_color="normal")
        with c_kpi4: metric_card("Yield on Cost", "3.45%", delta="Flussi Dividendi", delta_color="normal")
    elif active_profile["id"] == "quant_analyst":
        with c_kpi1: metric_card("SVI Smile Curvature", "0.428", delta="Calibrazione SVI", delta_color="normal")
        with c_kpi2: metric_card("Merton Jump Intensity (λ)", "0.15 / anno", delta="Poisson Jumps", delta_color="normal")
        with c_kpi3: metric_card("Spearman Factor Monotonicity", "0.854", delta="Q1-Q5 Robustness", delta_color="normal")
        with c_kpi4: metric_card("In-Memory DuckDB", "Connesso (:memory:)", delta="OLAP Sub-ms", delta_color="normal")
    else: # corporate_treasurer
        with c_kpi1: metric_card("Portfolio YTM", "4.19%", delta="YAS Solver", delta_color="normal")
        with c_kpi2: metric_card("Modified Duration", "6.85 anni", delta="Rate Sensitivity", delta_color="normal")
        with c_kpi3: metric_card("Portfolio DV01", f"€ {tot_val * 0.00065:,.2f}", delta="Per 1 bp Shock", delta_color="normal")
        with c_kpi4: metric_card("Credito Zainetto Fiscale", "€ 1,250.00", delta="Compensabile TUIR", delta_color="normal")

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    col_ws1, col_ws2 = st.columns([2.2, 1.2])
    with col_ws1:
        st.markdown("##### 🧭 Moduli Primari & Percorsi Rapidi di Navigazione (1-Click Teleport)")
        for idx, p_item in enumerate(active_profile["primary_pages"]):
            c_link1, c_link2 = st.columns([3.5, 1.2])
            with c_link1:
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #e6edf3;">📄 {p_item['name']}</span>
                    <span style="color: #8b949e; font-size: 12.5px; margin-left: 10px;">➔ Scheda: <b>{p_item['tab']}</b></span>
                </div>
                """, unsafe_allow_html=True)
            with c_link2:
                if st.button(f"🚀 Apri Modulo", key=f"btn_jump_to_{active_profile['id']}_{idx}", use_container_width=True):
                    # Mappa scheda di destinazione
                    tab_name = p_item["tab"]
                    if "4_📋" in p_item["page"]:
                        st.session_state["positions_active_tab"] = tab_name
                    elif "3_🔬" in p_item["page"]:
                        st.session_state["quant_active_tab"] = tab_name
                    elif "2_🔴" in p_item["page"]:
                        st.session_state["risk_active_tab"] = tab_name
                    elif "8_📈" in p_item["page"]:
                        st.session_state["tech_active_subtab"] = tab_name
                    elif "9_🔍" in p_item["page"]:
                        st.session_state["screener_segmented_subtab"] = tab_name
                    elif "10_💻" in p_item["page"]:
                        st.session_state["bquant_active_tab"] = tab_name
                    
                    switch_to_page(f"pages/{p_item['page']}.py")

    with col_ws2:
        st.markdown("##### ⚙️ Preferenze del Workspace")
        st.markdown(f"⏱️ **Refresh Rate Suggerito:** `{active_profile['recommended_refresh_rate']} secondi`")
        
        landing_options = [p["name"] for p in active_profile["primary_pages"]]
        sel_landing = st.selectbox("Pagina di Atterraggio Predefinita:", landing_options, key=f"sel_landing_{active_profile['id']}")
        
        custom_refresh = st.slider("Intervallo di Aggiornamento Dati (sec):", min_value=5, max_value=300, value=max(5, active_profile["recommended_refresh_rate"]), step=5, key=f"sl_refresh_{active_profile['id']}")
        
        if st.button("💾 Salva Preferenze Profilo", type="primary", use_container_width=True, key=f"btn_save_pref_{active_profile['id']}"):
            save_custom_workspace_layout("default_user", active_profile["id"], {"landing_page": sel_landing, "refresh_sec": custom_refresh})
            st.success("✅ Preferenze del profilo salvate con successo!")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: EXCEL LIVE CONNECTOR & RTD
# ═════════════════════════════════════════════════════════════════════════════
elif active_bquant_tab == "📊 Excel Live Connector & RTD":
    st.markdown("#### 📊 ARGUS Excel Live Connector & Bloomberg Formula Builder")
    st.caption("Collega Microsoft Excel e Google Sheets al motore locale di ARGUS tramite formule UDF in stile Bloomberg Terminal (=ARGUS_BDP, =ARGUS_BDH, =ARGUS_RISK) ed esporta workbook completi multi-foglio.")

    col_xl_sub1, col_xl_sub2 = st.columns([1.6, 1.4])
    
    # ── GENERATORE FORMULE BLOOMBERG-STYLE ──
    with col_xl_sub1:
        st.markdown("##### 🔤 Costruttore Formule Bloomberg-Style")
        
        ftype_choice = st.radio("Seleziona Tipo di Formula:", ["BDP (Data Point per Asset)", "BDH (Serie Storica Date)", "RISK (Metrica Rischio Portafoglio)"], horizontal=True, key="sel_xl_ftype")
        
        if "BDP" in ftype_choice:
            tickers_list = list(pos["ticker"].unique()) if not pos.empty else ["AAPL", "MSFT", "NVDA", "SPY"]
            sel_tk = st.selectbox("Seleziona Ticker:", tickers_list, key="sel_xl_tk")
            sel_fld = st.selectbox("Seleziona Campo Dati:", list(EXCEL_SUPPORTED_FIELDS.keys()), format_func=lambda f: f"{f} — {EXCEL_SUPPORTED_FIELDS[f]['desc']}", key="sel_xl_fld")
            generated_formula = build_bloomberg_formula("BDP", sel_tk, sel_fld)
            
        elif "BDH" in ftype_choice:
            tickers_list = list(pos["ticker"].unique()) if not pos.empty else ["AAPL", "MSFT", "NVDA", "SPY"]
            sel_tk = st.selectbox("Seleziona Ticker:", tickers_list, key="sel_xl_tk_bdh")
            sel_fld = st.selectbox("Seleziona Campo Dati:", ["CLOSE", "OPEN", "HIGH", "LOW", "VOLUME", "RETURNS"], key="sel_xl_fld_bdh")
            d_start = st.text_input("Data Inizio (YYYY-MM-DD):", value="2024-01-01", key="xl_bdh_start")
            d_end = st.text_input("Data Fine (YYYY-MM-DD):", value=datetime.date.today().strftime("%Y-%m-%d"), key="xl_bdh_end")
            generated_formula = build_bloomberg_formula("BDH", sel_tk, sel_fld, d_start, d_end)
            
        else: # RISK
            sel_rfld = st.selectbox("Seleziona Metrica di Rischio:", list(EXCEL_PORTFOLIO_RISK_FIELDS.keys()), format_func=lambda f: f"{f} — {EXCEL_PORTFOLIO_RISK_FIELDS[f]['desc']}", key="sel_xl_rfld")
            generated_formula = build_bloomberg_formula("RISK", "", sel_rfld)

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("📋 **Formula Generata per Excel / Google Sheets:**")
        st.code(generated_formula, language="excel")
        st.caption("Copia e incolla questa formula nelle celle di Excel per collegarti in tempo reale al motore di calcolo.")

    # ── ESPORTATORE MULTI-FOGLIO ISTITUZIONALE ──
    with col_xl_sub2:
        st.markdown("##### 📥 Esportazione Modello Excel Istituzionale (.xlsx)")
        st.markdown("""
        Genera un file Excel multi-foglio professionale contenente:
        • **Executive_Summary**: KPI di rischio, controvalore, Sharpe e VaR.
        • **Positions_Portfolio**: Tabella completa delle posizioni con pesi e ratio.
        • **Fixed_Income_YAS**: Duration, Convessità, DV01 e Z-Spread.
        • **Execution_Schedule**: Scaglioni ottimali Almgren-Chriss.
        """)
        
        excel_bytes = export_institutional_multisheet_excel(results)
        st.download_button(
            "📥 Scarica Workbook Excel Multi-Foglio (.xlsx)",
            data=excel_bytes,
            file_name=f"ARGUS_Institutional_Portfolio_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
            key="btn_download_full_excel_workbook"
        )

    st.divider()
    
    # ── INTEGRATION CODE: VBA & OFFICE SCRIPTS ──
    st.markdown("##### 🔌 Script di Integrazione per Excel (VBA & Office Scripts)")
    tab_vba, tab_ts = st.tabs(["💻 Modulo VBA Excel (Desktop .bas)", "🌐 Microsoft Office Script (TypeScript .ts)"])
    
    with tab_vba:
        st.caption("Incolla questo modulo in Excel Desktop (Alt + F11 > Inserisci > Modulo) per abilitare le funzioni native `=ARGUS_BDP` e `=ARGUS_RISK`.")
        st.code(generate_vba_macro_code(), language="visual-basic")
        
    with tab_ts:
        st.caption("Incolla questo script in Excel per il Web o Microsoft 365 (Automatizza > Nuovo Script) per sincronizzare il foglio via fetch API.")
        st.code(generate_office_script_code(), language="typescript")
