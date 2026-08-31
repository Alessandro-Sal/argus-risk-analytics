# ============================================================
# src/pages/12_🎛️_Wealth_Control_Room.py
# ARGUS Wealth Management — Dedicated Control Room & Ingestion Hub
# ============================================================

import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime, date

import importlib
import core.ui_utils
import core.wealth.wealth_db
import core.wealth.wealth_sync
import core.wealth.wealth_engine
importlib.reload(core.ui_utils)
importlib.reload(core.wealth.wealth_db)
importlib.reload(core.wealth.wealth_sync)
importlib.reload(core.wealth.wealth_engine)

from core.fetcher import get_engine
from core.ui_utils import (
    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_wealth_control_room_hero
)
from core.wealth.wealth_engine import compute_consolidated_net_worth
from core.sidebar import render_sidebar

from core.wealth.wealth_db import (
    init_wealth_db,
    get_wealth_accounts,
    save_wealth_account,
    delete_wealth_account,
    deduplicate_wealth_accounts,
    get_wealth_categories,
    save_wealth_category,
    get_cashflow_records,
    save_physical_asset,
    save_pension_plan,
    get_wealth_portfolios,
    create_wealth_portfolio,
    delete_wealth_portfolio,
    cleanup_empty_wealth_portfolios,
    clear_wealth_cashflow,
    clear_wealth_snapshots,
    clear_wealth_accounts,
    reset_wealth_portfolio_data,
    reset_all_wealth_database,
    save_wealth_snapshot_to_db,
    get_wealth_snapshots_history,
    delete_wealth_snapshot,
    load_wealth_snapshot_details,
    get_available_risk_portfolios,
    get_linked_risk_portfolios,
    set_linked_risk_portfolios,
    get_linked_risk_portfolios_summary
)


from core.wealth.wealth_importer import (
    parse_universal_statement,
    auto_categorize_transactions,
    bulk_import_statement
)
from core.wealth.wealth_validator import (
    validate_cashflow_df,
    validate_physical_assets_df,
    validate_accounts_df,
    validate_pension_df
)
from core.wealth.wealth_sync import (
    sync_expenses_tracker_2026_from_gsheets,
    sync_all_historical_expenses_from_gsheets
)


# ── CONFIGURAZIONE PAGINA & SIDEBAR ─────────────────────────
st.set_page_config(page_title="Wealth Control Room | ARGUS", page_icon="🎛️", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

# Connessione Database Wealth
db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "investment_risk_bi")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
init_wealth_db(engine)

# ── PROFILI PATRIMONIALI (MULTI-PORTFOLIO) ───────────────────
df_profiles = get_wealth_portfolios(engine)
profile_map = {row["portfolio_id"]: row["name"] for _, row in df_profiles.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")
if current_pid is not None and current_pid not in profile_map:
    current_pid = None
    st.session_state["wealth_active_portfolio_id"] = None


active_p_name = profile_map.get(current_pid, "Nessun Profilo") if current_pid else "Nessun Profilo"
render_wealth_command_bar(engine, current_pid=current_pid or 1, prof_name=active_p_name, key_suffix="p12")

# ── HERO & COCKPIT HEADER BAR ───────────────────────────────

st.markdown("""
<style>
/* Header Cockpit Card */
.wealth-cockpit-header {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(15, 23, 42, 0.92) 55%, rgba(6, 78, 59, 0.20) 100%);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-left: 5px solid #10b981;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 14px;
    backdrop-filter: blur(16px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.wealth-cockpit-title {
    font-size: 21px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}
.wealth-pill-badge {
    background: rgba(16, 185, 129, 0.20);
    color: #34d399;
    font-size: 10.5px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 12px;
    border: 1px solid rgba(16, 185, 129, 0.45);
    letter-spacing: 0.5px;
}
.wealth-cockpit-sub {
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.4;
}

/* Wealth KPI Metric Cards */
.wealth-kpi-card {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(16, 185, 129, 0.22);
    border-top: 3px solid #10b981;
    border-radius: 12px;
    padding: 14px 16px;
    transition: all 0.25s ease;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    min-height: 100px;
}
.wealth-kpi-card:hover {
    border-color: rgba(16, 185, 129, 0.6);
    box-shadow: 0 6px 22px rgba(16, 185, 129, 0.2);
    transform: translateY(-2px);
}
.wealth-kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.wealth-kpi-title {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #94a3b8;
}
.wealth-kpi-val {
    font-family: 'JetBrains Mono', 'Roboto Mono', monospace;
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
}
.wealth-kpi-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 600;
    color: #34d399;
    background: rgba(16, 185, 129, 0.12);
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid rgba(16, 185, 129, 0.25);
}
</style>
""", unsafe_allow_html=True)


render_wealth_control_room_hero(profile_map=profile_map, current_pid=current_pid)

# ── SELETTORE PROFILO & TOOLBAR IN LINEA ─────────────────────
p_bar_c1, p_bar_c2, p_bar_c3, p_bar_c4 = st.columns([3.2, 1.1, 1.1, 1.4])
with p_bar_c1:
    opts = [None] + list(profile_map.keys())
    curr_idx = opts.index(current_pid) if current_pid in opts else 0
    selected_pid = st.selectbox(
        "💼 Profilo Patrimoniale Attivo:",
        options=opts,
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {profile_map[pid]} (ID #{pid})",
        index=curr_idx,
        key="wealth_profile_selector_widget"
    )
    if selected_pid != current_pid:
        st.session_state["wealth_active_portfolio_id"] = selected_pid
        st.rerun()

with p_bar_c2:
    st.write("")
    with st.popover("➕ Nuovo", use_container_width=True):
        st.markdown("##### ➕ Crea Profilo Patrimoniale")
        new_p_name = st.text_input("Nome Profilo *", placeholder="es. Famiglia, Holding, P.IVA...")
        new_p_desc = st.text_input("Descrizione (opzionale)", placeholder="Spese e patrimonio familiare")
        if st.button("Crea Profilo", type="primary", use_container_width=True, key="btn_create_prof_pop"):
            if new_p_name.strip():
                try:
                    n_pid = create_wealth_portfolio(engine, new_p_name.strip(), new_p_desc.strip() if new_p_desc else None)
                    st.session_state["wealth_active_portfolio_id"] = n_pid
                    st.success(f"Profilo '{new_p_name.strip()}' selezionato ed attivo!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Impossibile creare il profilo: {ex}")


with p_bar_c3:
    st.write("")
    if current_pid is not None and len(profile_map) > 1:
        if st.button("🗑️ Elimina", type="secondary", use_container_width=True, key="btn_del_prof_pop"):
            delete_wealth_portfolio(engine, current_pid)
            remaining = [p for p in profile_map.keys() if p != current_pid]
            st.session_state["wealth_active_portfolio_id"] = remaining[0] if remaining else None
            st.warning("Profilo eliminato con successo.")
            st.rerun()
    elif current_pid is not None:
        st.button("🔒 Unico", disabled=True, use_container_width=True, help="Non puoi eliminare l'unico profilo presente. Creane prima un altro con ➕ Nuovo.")


with p_bar_c4:
    st.write("")
    if current_pid is not None:
        if st.button("🏛️ Vai al Net Worth →", type="secondary", use_container_width=True, key="btn_goto_nw_top"):
            st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")

if current_pid is None:
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">👋 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0;">Seleziona un profilo dal menu a tendina in alto (es. <b>Personale</b>) oppure creane uno nuovo con <b>➕ Nuovo</b> per iniziare.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── BANNER FEEDBACK SINCRONIZZAZIONE O SNAPSHOT ATTIVO ───────
if "wealth_sync_feedback" in st.session_state and st.session_state["wealth_sync_feedback"]:
    fb = st.session_state["wealth_sync_feedback"]
    fb_c1, fb_c2 = st.columns([5, 1])
    with fb_c1:
        st.success(f"""
        🚀 **Sincronizzazione Google Sheets Eseguita con Successo!**
        - 📜 **Transazioni Elaborate**: `{fb.get('total_transactions_synced', 0):,}`
        - 🏦 **Conti Aggiornati**: `{fb.get('accounts_count', 0)}` ({', '.join(fb.get('accounts_list', []))})
        - 📸 **Snapshot Automatico Generato**: ID `#{fb.get('snapshot_id', '-')}` (*{fb.get('snapshot_name', '')}*)
        """)
    with fb_c2:
        st.write("")
        if st.button("✖ Chiudi", key="btn_close_sync_fb_main"):
            st.session_state.pop("wealth_sync_feedback", None)
            st.rerun()

if "wealth_active_snapshot" in st.session_state and st.session_state["wealth_active_snapshot"]:
    act_snap = st.session_state["wealth_active_snapshot"]
    st.info(f"""
    📸 **Visualizzazione Snapshot Storico Attivo**: **"{act_snap.get('snapshot_name', 'Senza Nome')}"** del **{act_snap.get('snapshot_date')}** 
    (Patrimonio Netto Consolidato: **{fmt_eur(act_snap.get('total_net_worth', 0.0))}**).
    """)
    if st.button("🔄 Ripristina Dati Live / Esci da Snapshot Storico", type="secondary", key="btn_exit_wealth_snap"):
        st.session_state.pop("wealth_active_snapshot", None)
        st.rerun()

# ── TOP KPI METRIC STRIP ────────────────────────────────────
df_accs = get_wealth_accounts(engine, portfolio_id=current_pid)
df_txs = get_cashflow_records(engine, portfolio_id=current_pid)
df_snaps = get_wealth_snapshots_history(engine, portfolio_id=current_pid)

tot_cash = float(df_accs[df_accs["balance"] > 0]["balance"].sum()) if not df_accs.empty else 0.0
tot_tx_count = len(df_txs) if not df_txs.empty else 0
tot_acc_count = len(df_accs) if not df_accs.empty else 0
last_tx_date = str(df_txs["tx_date"].max()) if not df_txs.empty else "Nessuna"
tot_snaps_count = len(df_snaps) if not df_snaps.empty else 0

nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

st.markdown("<div style='margin-top: 10px; margin-bottom: 18px;'>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)


with k1:
    st.markdown(f"""
    <div class="wealth-kpi-card">
        <div class="wealth-kpi-header">
            <span class="wealth-kpi-title">Liquidità Consolidata</span>
            <span>💧</span>
        </div>
        <div class="wealth-kpi-val">{fmt_eur(tot_cash)}</div>
        <div class="wealth-kpi-pill">🏦 {tot_acc_count} Conti Attivi</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="wealth-kpi-card">
        <div class="wealth-kpi-header">
            <span class="wealth-kpi-title">Libro Mastro Cassa</span>
            <span>📜</span>
        </div>
        <div class="wealth-kpi-val">{tot_tx_count:,}</div>
        <div class="wealth-kpi-pill">💳 Movimenti Registrati</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="wealth-kpi-card">
        <div class="wealth-kpi-header">
            <span class="wealth-kpi-title">Ultima Registrazione</span>
            <span>📅</span>
        </div>
        <div class="wealth-kpi-val">{last_tx_date}</div>
        <div class="wealth-kpi-pill">⚡ Data Valuta</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="wealth-kpi-card">
        <div class="wealth-kpi-header">
            <span class="wealth-kpi-title">Snapshot Storici</span>
            <span>📸</span>
        </div>
        <div class="wealth-kpi-val">{tot_snaps_count} Snapshot</div>
        <div class="wealth-kpi-pill">📁 Profilo #{current_pid}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── SEZIONE: Storico Snapshot & Recall Analisi (Stile Risk Module) ────
with st.expander("📚 Storico Snapshot & Recall Analisi Patrimoniale", expanded=bool(st.session_state.get("wealth_active_snapshot"))):
    df_all_snaps = get_wealth_snapshots_history(engine)
    if df_all_snaps.empty:
        st.info("ℹ️ Nessuno snapshot patrimoniale salvato. Carica un estratto conto CSV, sincronizza Google Sheets o inserisci i saldi per registrare il primo snapshot!")
    else:
        st.caption("Sfoglia gli snapshot storici salvati nel database per ricaricare istantaneamente lo stato del patrimonio netto in un dato momento senza ricalcoli.")

        col_search, col_port_filter, col_sort = st.columns([2.2, 1.4, 1.4])
        with col_search:
            search_query = st.text_input(
                "🔍 Cerca Snapshot (Nome, ID, Data):",
                placeholder="es. GSheets, Fineco, 2026-08, RUN-WLT...",
                key="wealth_hist_search_query"
            ).strip().lower()

        unique_ports = sorted(list({str(r) for r in df_all_snaps["portfolio_name"].dropna().unique() if str(r).strip()}))
        with col_port_filter:
            selected_port_filter = st.selectbox(
                "💼 Filtra Profilo:",
                options=["Tutti i Profili"] + unique_ports,
                key="wealth_hist_port_filter"
            )

        with col_sort:
            sort_mode = st.selectbox(
                "⚡ Ordina per:",
                options=[
                    "📅 Più recenti",
                    "📅 Meno recenti",
                    "💰 Net Worth (Decrescente)",
                    "💧 Liquidità (Decrescente)",
                    "🛡️ Health Score (Decrescente)"
                ],
                key="wealth_hist_sort_mode"
            )

        # Filtraggio
        filtered_df = df_all_snaps.copy()
        if selected_port_filter != "Tutti i Profili":
            filtered_df = filtered_df[filtered_df["portfolio_name"] == selected_port_filter]

        if search_query:
            filtered_df = filtered_df[
                filtered_df.apply(
                    lambda row: search_query in f"{row.get('snapshot_name', '')} {row.get('snapshot_date', '')} {row.get('run_id', '')} {row.get('portfolio_name', '')} {row.get('notes', '')}".lower(),
                    axis=1
                )
            ]

        # Ordinamento
        if sort_mode == "📅 Più recenti":
            filtered_df = filtered_df.sort_values(by=["snapshot_date", "snapshot_id"], ascending=[False, False])
        elif sort_mode == "📅 Meno recenti":
            filtered_df = filtered_df.sort_values(by=["snapshot_date", "snapshot_id"], ascending=[True, True])
        elif sort_mode == "💰 Net Worth (Decrescente)":
            filtered_df = filtered_df.sort_values(by="total_net_worth", ascending=False)
        elif sort_mode == "💧 Liquidità (Decrescente)":
            filtered_df = filtered_df.sort_values(by="liquid_assets", ascending=False)
        elif sort_mode == "🛡️ Health Score (Decrescente)":
            filtered_df = filtered_df.sort_values(by="wealth_health_score", ascending=False)

        if filtered_df.empty:
            st.warning("🔍 Nessuno snapshot corrisponde ai criteri di ricerca impostati.")
        else:
            st.markdown(f"<div style='font-size: 11.5px; color: #8b949e; margin-bottom: 6px;'>🎯 Trovati <b>{len(filtered_df)}</b> snapshot su {len(df_all_snaps)} totali</div>", unsafe_allow_html=True)

            snap_options = {}
            for _, r in filtered_df.iterrows():
                sid = int(r["snapshot_id"])
                dt_str = str(r["snapshot_date"])
                p_name_display = r.get("portfolio_name") or f"Profilo #{r.get('portfolio_id', 1)}"
                s_name = r.get("snapshot_name") or "Snapshot Standard"
                tot_nw_val = float(r.get("total_net_worth", 0.0))
                liq_val = float(r.get("liquid_assets", 0.0))
                run_id_val = r.get("run_id") or f"ID #{sid}"
                
                label = f"{dt_str} · {p_name_display} · {s_name} (Net Worth: {fmt_eur(tot_nw_val)} | Cassa: {fmt_eur(liq_val)} | {run_id_val})"
                snap_options[label] = sid

            selected_snap_label = st.selectbox(
                "📸 Seleziona lo Snapshot da richiamare o gestire:",
                options=list(snap_options.keys()),
                key="wealth_select_snapshot_recall"
            )
            sel_sid = snap_options[selected_snap_label]

            col_recall, col_del_snap, col_goto_dash = st.columns([2.5, 1.3, 1.8])
            with col_recall:
                if st.button("⚡ Carica Snapshot & Visualizza Analisi", type="primary", use_container_width=True, key="btn_recall_snap_action"):
                    snap_data = load_wealth_snapshot_details(engine, sel_sid)
                    if snap_data:
                        st.session_state["wealth_active_snapshot"] = snap_data
                        st.session_state["wealth_active_portfolio_id"] = snap_data.get("portfolio_id", 1)
                        st.success(f"✅ Snapshot '{snap_data.get('snapshot_name')}' ({snap_data.get('snapshot_date')}) caricato con successo!")
                        st.rerun()
                    else:
                        st.error("Errore nel caricamento del payload dello snapshot.")

            with col_del_snap:
                if st.button("🗑️ Elimina Snapshot", type="secondary", use_container_width=True, key="btn_del_snap_action"):
                    if delete_wealth_snapshot(engine, sel_sid):
                        if st.session_state.get("wealth_active_snapshot", {}).get("snapshot_id") == sel_sid:
                            st.session_state.pop("wealth_active_snapshot", None)
                        st.warning("Snapshot eliminato con successo dal database.")
                        st.rerun()

            with col_goto_dash:
                if st.button("🏛️ Vai alla Dashboard Net Worth →", type="secondary", use_container_width=True, key="btn_goto_nw_from_recall"):
                    st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")
            # Tabella di riepilogo
            with st.expander("📋 Mostra Tabella Dettagliata Snapshot"):
                disp_df = filtered_df[[
                    "snapshot_id", "snapshot_date", "portfolio_name", "snapshot_name", "run_id",
                    "total_net_worth", "liquid_assets", "financial_investments", "physical_assets_total",
                    "pension_total", "total_liabilities", "wealth_health_score"
                ]].copy()
                disp_df.columns = [
                    "ID", "Data", "Profilo", "Nome Snapshot", "Run ID",
                    "Net Worth (€)", "Liquidità (€)", "Investimenti (€)", "Asset Caveau (€)",
                    "Previdenza (€)", "Passività (€)", "Health Score"
                ]
                st.dataframe(disp_df, use_container_width=True, hide_index=True)


# ── STRUTTURA A TAB ORGANIZZATA & PULITA ────────────────────
tab_pipeline, tab_mgmt = st.tabs([
    "🚀 1. Pipeline Ingestione & Calcolo Wealth (Processo Guidato)",
    "🏦 2. Gestione Conti, Portafogli Risk & Categorie"
])



# =============================================================
# TAB 1: PIPELINE GUIDATA A STEP
# =============================================================
with tab_pipeline:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(99, 102, 241, 0.06) 100%); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-weight:800; color:#34d399; font-size:14px; text-transform:uppercase; letter-spacing:0.5px;">🚀 Pipeline di Ingestione & Calcolo Patrimoniale</span>
                <p style="font-size:12px; color:#94a3b8; margin: 4px 0 0 0;">
                    Processo guidato a step per caricare estratti conto bancari, sincronizzare Google Sheets o registrare asset e consolidare automaticamente il Net Worth.
                </p>
            </div>
            <div style="font-size:12px; color:#cbd5e1; background:rgba(255,255,255,0.06); padding:5px 12px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);">
                Profilo Attivo: <b style="color:#34d399;">{profile_map.get(current_pid, 'Principale')} (ID #{current_pid})</b>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 1: SORGENTE DATI & FILE ────────────────────────
    section("① Scegli la Sorgente Dati")
    
    src_options = [
        "🌐 Google Sheets — Sincronizzazione Veloce 2026 ('Expenses Tracker 2026' & 'Net Worth OGGI')",
        "🌐 Google Sheets — Archivio Storico Multi-Anno (2021 – 2026, oltre 4.000 transazioni)",
        "💳 Estratto Conto Bancario / CSV Spese (Intesa, Revolut, Fineco, N26, template)",
        "🏦 Saldi & Conti Bancari (CSV / Template)",
        "⌚ Caveau Orologi, Immobili & Metalli Preziosi (CSV / Template)",
        "🛡️ Piani Previdenziali & Fondi Pensione (CSV / Template)"
    ]
    
    src_selected_label = st.selectbox(
        "Sorgente Dati / Formato di Ingestione:",
        options=src_options,
        key="wealth_pipeline_src_selectbox"
    )

    uploaded_data_df = None
    target_account_id = None
    gsheet_name_val = "My All financial Statements"
    multi_years_val = [2021, 2022, 2023, 2024, 2025, 2026]
    is_ready_for_step2 = False

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    if src_selected_label.startswith("🌐 Google Sheets — Sincronizzazione Veloce"):
        col_gq1, col_gq2 = st.columns([3, 1])
        with col_gq1:
            gsheet_name_val = st.text_input("Nome Spreadsheet Google Sheets:", value="My All financial Statements", key="pipe_gsheet_quick_name")
        with col_gq2:
            st.write("")
            st.write("")
            st.caption("✅ Lettura automatica di 'Expenses Tracker 2026'")
        is_ready_for_step2 = True

    elif src_selected_label.startswith("🌐 Google Sheets — Archivio Storico"):
        col_gm1, col_gm2 = st.columns([2.5, 2])
        with col_gm1:
            gsheet_name_val = st.text_input("Nome Spreadsheet Google Sheets:", value="My All financial Statements", key="pipe_gsheet_multi_name")
        with col_gm2:
            multi_years_val = st.multiselect(
                "Anni da sincronizzare:",
                options=[2021, 2022, 2023, 2024, 2025, 2026],
                default=[2021, 2022, 2023, 2024, 2025, 2026],
                key="pipe_gsheet_multi_years"
            )
        is_ready_for_step2 = bool(multi_years_val)

    elif src_selected_label.startswith("💳 Estratto Conto Bancario"):
        tcol1, tcol2 = st.columns([3, 1.5])
        with tcol1:
            if not df_accs.empty:
                acc_dict = {f"{r['name']} ({r['institution']}) — Saldo: {fmt_eur(r['balance'])}": r["account_id"] for _, r in df_accs.iterrows()}
                sel_acc_label = st.selectbox("Conto di Destinazione transazioni:", list(acc_dict.keys()), key="pipe_csv_cf_acc_select")
                target_account_id = acc_dict[sel_acc_label]
            else:
                st.warning("⚠️ Nessun conto bancario presente. Creane uno nella Tab 2 prima di importare transazioni.")
                target_account_id = None
        with tcol2:
            st.write("")
            if os.path.exists("data/wealth/template_cashflow_spese.csv"):
                with open("data/wealth/template_cashflow_spese.csv", "rb") as f:
                    st.download_button("📥 Scarica Template CSV", f, file_name="template_cashflow_spese.csv", mime="text/csv", use_container_width=True)

        uploaded_file = st.file_uploader("Carica Estratto Conto Bancario (.csv, .xlsx, .xls):", type=["csv", "xlsx", "xls"], key="pipe_up_cf")
        if uploaded_file and target_account_id:
            df_parsed, errs = parse_universal_statement(uploaded_file, uploaded_file.name)
            if errs:
                for e in errs: st.error(e)
            elif df_parsed is not None and not df_parsed.empty:
                is_val, val_errs, df_clean = validate_cashflow_df(df_parsed)
                if val_errs:
                    for ve in val_errs[:5]: st.warning(f"⚠️ {ve}")
                uploaded_data_df = auto_categorize_transactions(df_clean, engine)
                is_ready_for_step2 = True

    elif src_selected_label.startswith("🏦 Saldi & Conti"):
        tcol1, tcol2 = st.columns([3, 1.5])
        with tcol1:
            up_acc = st.file_uploader("Carica File Saldi Conti (.csv):", type=["csv"], key="pipe_up_accs")
        with tcol2:
            st.write("")
            if os.path.exists("data/wealth/template_conti_bancari.csv"):
                with open("data/wealth/template_conti_bancari.csv", "rb") as f:
                    st.download_button("📥 Scarica Template Conti", f, file_name="template_conti_bancari.csv", mime="text/csv", use_container_width=True)
        if up_acc:
            df_a_raw = pd.read_csv(up_acc)
            is_val, val_errs, df_a_clean = validate_accounts_df(df_a_raw)
            if not df_a_clean.empty:
                uploaded_data_df = df_a_clean
                is_ready_for_step2 = True

    elif src_selected_label.startswith("⌚ Caveau Orologi"):
        tcol1, tcol2 = st.columns([3, 1.5])
        with tcol1:
            up_phys = st.file_uploader("Carica File Orologi & Caveau (.csv):", type=["csv"], key="pipe_up_phys")
        with tcol2:
            st.write("")
            if os.path.exists("data/wealth/template_orologi_asset_fisici.csv"):
                with open("data/wealth/template_orologi_asset_fisici.csv", "rb") as f:
                    st.download_button("📥 Scarica Template Caveau", f, file_name="template_orologi_asset_fisici.csv", mime="text/csv", use_container_width=True)
        if up_phys:
            df_p_raw = pd.read_csv(up_phys)
            is_val, val_errs, df_p_clean = validate_physical_assets_df(df_p_raw)
            if not df_p_clean.empty:
                uploaded_data_df = df_p_clean
                is_ready_for_step2 = True

    elif src_selected_label.startswith("🛡️ Piani Previdenziali"):
        tcol1, tcol2 = st.columns([3, 1.5])
        with tcol1:
            up_pens = st.file_uploader("Carica File Previdenza & Pensione (.csv):", type=["csv"], key="pipe_up_pens")
        with tcol2:
            st.write("")
            if os.path.exists("data/wealth/template_fondi_pensione.csv"):
                with open("data/wealth/template_fondi_pensione.csv", "rb") as f:
                    st.download_button("📥 Scarica Template Pensione", f, file_name="template_fondi_pensione.csv", mime="text/csv", use_container_width=True)
        if up_pens:
            df_pen_raw = pd.read_csv(up_pens)
            is_val, val_errs, df_pen_clean = validate_pension_df(df_pen_raw)
            if not df_pen_clean.empty:
                uploaded_data_df = df_pen_clean
                is_ready_for_step2 = True

    st.divider()

    # ── STEP 2: ANTEPRIMA, VALIDAZIONE & PARAMETRI RUN ──────
    section("② Validazione Dati, Parametri Snapshot & Multi-Portafoglio")
    
    default_snap_label = f"Ingestione {src_selected_label.split('—')[0].strip()} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    col_p1, col_p2, col_p3 = st.columns([2.5, 1.3, 2.2])
    with col_p1:
        run_snap_name = st.text_input("🏷️ Nome Snapshot / Ingestione:", value=default_snap_label, key="pipe_input_snap_name")
    with col_p2:
        run_snap_date = st.date_input("📅 Data Riferimento:", value=date.today(), key="pipe_input_snap_date")
    with col_p3:
        run_snap_notes = st.text_input("📝 Note Snapshot:", placeholder="es. Aggiornamento Q3, Chiusura mese...", key="pipe_input_snap_notes")

    # Anteprima Tabellare se file caricato
    if uploaded_data_df is not None and not uploaded_data_df.empty:
        st.markdown(f"**📋 Anteprima Dati Riconosciuti ({len(uploaded_data_df)} Record):**")
        st.dataframe(uploaded_data_df.head(8), use_container_width=True, hide_index=True)
    elif src_selected_label.startswith("🌐 Google Sheets"):
        st.info("ℹ️ I dati verranno estratti, validati e categorizzati direttamente dalle schede dello spreadsheet durante l'esecuzione.")

    # ── SEZIONE MULTI-PORTAFOGLIO RISK ──────────────────────
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    st.markdown("##### 🔗 Multi-Portafoglio Risk Analytics (Investimenti Finanziari)")
    st.caption("Seleziona uno o più portafogli dal modulo Risk per aggregare e consolidare il controvalore di azioni, ETF, obbligazioni e crypto nel Net Worth:")

    currently_linked_risk = get_linked_risk_portfolios(engine, wealth_portfolio_id=current_pid)
    df_avail_risk = get_available_risk_portfolios(engine, exclude_wealth_portfolio_id=current_pid)


    if df_avail_risk.empty:
        st.info("ℹ️ Nessun portafoglio calcolato presente nel database collegato. Vai nel modulo Risk Analytics per importare e calcolare i tuoi titoli.")
    else:
        risk_opt_map = {
            int(r["portfolio_id"]): f"ID #{r['portfolio_id']} · {r['name']} — {fmt_eur(r['latest_value'])}"
            for _, r in df_avail_risk.iterrows()
        }
        all_risk_ids = list(risk_opt_map.keys())

        # Bottoni Rapidi Selezione Multi-Portafoglio
        col_m_all, col_m_none, col_m_space = st.columns([1.8, 1.8, 2.4])
        with col_m_all:
            if st.button("🌟 Seleziona Tutti (Multi-Portafoglio)", type="secondary", use_container_width=True, key=f"btn_sel_all_risk_{current_pid}"):
                set_linked_risk_portfolios(engine, current_pid, all_risk_ids)
                st.rerun()
        with col_m_none:
            if st.button("🚫 Solo Transazionale (€ 0,00)", type="secondary", use_container_width=True, key=f"btn_sel_none_risk_{current_pid}"):
                set_linked_risk_portfolios(engine, current_pid, [])
                st.rerun()

        def_linked = [pid for pid in currently_linked_risk if pid in risk_opt_map]
        
        pipe_sel_risk = st.multiselect(
            "Portafogli Risk Analytics selezionati per questo Profilo:",
            options=all_risk_ids,
            format_func=lambda x: risk_opt_map[x],
            default=def_linked,
            key=f"pipe_risk_multisel_{current_pid}",
            help="Puoi selezionare più portafogli per calcolare il controvalore complessivo aggregato."
        )
        
        if sorted(pipe_sel_risk) != sorted(currently_linked_risk):
            set_linked_risk_portfolios(engine, current_pid, pipe_sel_risk)

        # Statistiche Multi-Portafoglio in tempo reale
        tot_risk_val_live, df_linked_live = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=current_pid)
        if not df_linked_live.empty:
            df_disp_live = df_linked_live.copy()
            df_disp_live["Peso (%)"] = (df_disp_live["latest_value"] / tot_risk_val_live * 100.0) if tot_risk_val_live > 0 else 0.0
            
            st.markdown(f"""
            <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px; padding: 10px 16px; margin: 8px 0 14px 0; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#818cf8; font-size:13px;">💼 Multi-Portafoglio Consolidato: {len(df_disp_live)} Portafogli Collegati</span>
                <span style="font-size:14px; font-weight:800; color:#ffffff; font-family:'JetBrains Mono', monospace;">Totale Investimenti: {fmt_eur(tot_risk_val_live)}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                df_disp_live[["portfolio_id", "name", "base_currency", "last_calc_date", "latest_value", "Peso (%)"]].rename(columns={
                    "portfolio_id": "ID Portafoglio",
                    "name": "Nome Portafoglio",
                    "base_currency": "Valuta",
                    "last_calc_date": "Ultimo Snapshot",
                    "latest_value": "Valore (€)",
                    "Peso (%)": "Peso (%)"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.caption("💳 Nessun portafoglio Risk collegato: Profilo impostato come 'Solo Transazionale' (Investimenti = € 0,00).")

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
    st.divider()


    # ── STEP 3: ESEGUI INGESTIONE & AUTO-SNAPSHOT ────────────
    section("③ Esecuzione Pipeline & Generazione Snapshot")

    # 1. Deck di Riepilogo Configurazione Pre-Esecuzione
    p_name_cur = profile_map.get(current_pid, f"Profilo #{current_pid}")
    tot_risk_disp = fmt_eur(tot_risk_val_live) if tot_risk_val_live > 0 else "€ 0,00 (Solo Transazionale)"
    risk_ports_cnt_str = f"{len(df_linked_live)} Portafogli ({tot_risk_disp})" if not df_linked_live.empty else "Nessuno (Solo Cassa & Conti)"

    st.markdown(f"""
    <div style="background: rgba(13, 17, 23, 0.75); border: 1px solid rgba(255, 153, 0, 0.25); border-radius: 12px; padding: 16px 20px; margin-bottom: 18px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #ff9900; margin-bottom: 10px;">
            ⚡ Riepilogo Configurazione Pipeline Pronta per il Calcolo
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; font-size: 13px;">
            <div>
                <span style="color: #8b949e;">📁 Profilo Destinazione:</span><br/>
                <b style="color: #ffffff;">{p_name_cur}</b> <span style="color: #ff9900; font-size: 11px;">(ID #{current_pid})</span>
            </div>
            <div>
                <span style="color: #8b949e;">📥 Sorgente Dati:</span><br/>
                <b style="color: #ffffff;">{src_selected_label.split('(')[0].strip()}</b>
            </div>
            <div>
                <span style="color: #8b949e;">💼 Multi-Portafoglio Risk:</span><br/>
                <b style="color: #60a5fa;">{risk_ports_cnt_str}</b>
            </div>
            <div>
                <span style="color: #8b949e;">📸 Snapshot Risultante:</span><br/>
                <b style="color: #10b981;">{run_snap_name}</b> <span style="color: #8b949e; font-size: 11px;">({run_snap_date})</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn_run, col_btn_nw = st.columns([2.5, 1.5])
    with col_btn_run:
        btn_run_pipeline = st.button(
            "🚀 ESEGUI INGESTIONE & GENERA SNAPSHOT PATRIMONIALE",
            type="primary",
            use_container_width=True,
            disabled=not is_ready_for_step2,
            key="btn_run_wealth_pipeline_master"
        )
    with col_btn_nw:
        if st.button("🏛️ Vai al Patrimonio & Net Worth →", type="secondary", use_container_width=True, key="btn_goto_nw_from_pipe"):
            st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")

    if not is_ready_for_step2:
        st.caption("ℹ️ Completa lo **Step ①** (carica il file o verifica lo spreadsheet) per abilitare l'esecuzione.")

    if btn_run_pipeline:
        with st.status("🚀 Esecuzione Pipeline Wealth & Consolidamento in corso...", expanded=True) as status_box:
            s_id = None
            tot_synced_cnt = 0
            
            st.write("📡 **Fase 1/4**: Connessione e lettura della sorgente dati...")
            if src_selected_label.startswith("🌐 Google Sheets — Sincronizzazione Veloce"):
                sync_res = sync_expenses_tracker_2026_from_gsheets(
                    engine,
                    spreadsheet_name=gsheet_name_val,
                    worksheet_name="Expenses Tracker 2026",
                    portfolio_id=current_pid
                )
                tot_synced_cnt = sync_res.get("total_transactions_synced", 0)
                s_id = sync_res.get("snapshot_id")

            elif src_selected_label.startswith("🌐 Google Sheets — Archivio Storico"):
                sync_res = sync_all_historical_expenses_from_gsheets(
                    engine,
                    spreadsheet_name=gsheet_name_val,
                    years=multi_years_val,
                    portfolio_id=current_pid
                )
                tot_synced_cnt = sync_res.get("total_transactions_synced", 0)
                s_id = sync_res.get("snapshot_id")

            elif src_selected_label.startswith("💳 Estratto Conto Bancario"):
                st.write("📊 **Fase 2/4**: Categorizzazione semantica transazioni ed eliminazione duplicati...")
                tot_synced_cnt = bulk_import_statement(engine, target_account_id, uploaded_data_df, portfolio_id=current_pid)
                st.write("🏦 **Fase 3/4**: Consolidamento saldi e patrimonio...")
                s_id = save_wealth_snapshot_to_db(
                    engine,
                    run_name=run_snap_name,
                    notes=run_snap_notes,
                    snapshot_date_val=run_snap_date,
                    portfolio_id=current_pid
                )

            elif src_selected_label.startswith("🏦 Saldi & Conti"):
                st.write("🏦 **Fase 2/4**: Aggiornamento saldi bancari...")
                for _, row in uploaded_data_df.iterrows():
                    r_dict = row.to_dict()
                    r_dict["portfolio_id"] = current_pid
                    save_wealth_account(engine, r_dict)
                tot_synced_cnt = len(uploaded_data_df)
                st.write("📸 **Fase 3/4**: Calcolo Patrimonio Netto...")
                s_id = save_wealth_snapshot_to_db(
                    engine,
                    run_name=run_snap_name,
                    notes=run_snap_notes,
                    snapshot_date_val=run_snap_date,
                    portfolio_id=current_pid
                )

            elif src_selected_label.startswith("⌚ Caveau Orologi"):
                st.write("⌚ **Fase 2/4**: Censimento asset fisici e orologi...")
                for _, row in uploaded_data_df.iterrows():
                    r_dict = row.to_dict()
                    r_dict["portfolio_id"] = current_pid
                    save_physical_asset(engine, r_dict)
                tot_synced_cnt = len(uploaded_data_df)
                st.write("📸 **Fase 3/4**: Aggiornamento Snapshot...")
                s_id = save_wealth_snapshot_to_db(
                    engine,
                    run_name=run_snap_name,
                    notes=run_snap_notes,
                    snapshot_date_val=run_snap_date,
                    portfolio_id=current_pid
                )

            elif src_selected_label.startswith("🛡️ Piani Previdenziali"):
                st.write("🛡️ **Fase 2/4**: Aggiornamento piani previdenziali...")
                for _, row in uploaded_data_df.iterrows():
                    r_dict = row.to_dict()
                    r_dict["portfolio_id"] = current_pid
                    save_pension_plan(engine, r_dict)
                tot_synced_cnt = len(uploaded_data_df)
                st.write("📸 **Fase 3/4**: Aggiornamento Snapshot...")
                s_id = save_wealth_snapshot_to_db(
                    engine,
                    run_name=run_snap_name,
                    notes=run_snap_notes,
                    snapshot_date_val=run_snap_date,
                    portfolio_id=current_pid
                )

            st.write(f"📸 **Fase 4/4**: Generazione Snapshot #{s_id} e ricalcolo indici 50/30/20...")
            status_box.update(label="🎉 Pipeline completata con successo!", state="complete", expanded=False)

            if "sync_res" in locals() and isinstance(sync_res, dict):
                fb_payload = dict(sync_res)
                fb_payload["status"] = "success"
                fb_payload["snapshot_id"] = s_id
                fb_payload["snapshot_name"] = sync_res.get("snapshot_name") or run_snap_name
                fb_payload["total_transactions_synced"] = tot_synced_cnt
                fb_payload["total_records"] = tot_synced_cnt
                st.session_state["wealth_sync_feedback"] = fb_payload
            else:
                st.session_state["wealth_sync_feedback"] = {
                    "status": "success",
                    "snapshot_id": s_id,
                    "snapshot_name": run_snap_name,
                    "total_transactions_synced": tot_synced_cnt,
                    "total_records": tot_synced_cnt,
                    "accounts_count": len(df_accs) if not df_accs.empty else 6,
                    "accounts_list": df_accs["name"].tolist() if not df_accs.empty else []
                }
            st.rerun()





# =============================================================
# TAB 2: GESTIONE CONTI, PORTAFOGLI RISK & CATEGORIE
# =============================================================
with tab_mgmt:
    subtab_accs, tab_risk_sub, subtab_cats = st.tabs([
        "🏦 Anagrafica Conti Bancari",
        "🔗 Portafogli Risk Analytics",
        "🏷️ Categorie & Regola 50/30/20"
    ])

    # ── SUBTAB A: ANAGRAFICA CONTI ──────────────────────────
    with subtab_accs:
        tab_acc_c1, tab_acc_c2 = st.columns([3, 1.2])
        with tab_acc_c1:
            st.markdown(f"##### 🏦 Conti Bancari del Profilo '{profile_map.get(current_pid, 'Principale')}'")
            st.caption("Visualizza i saldi correnti, gestisci l'IBAN e attiva/disattiva conti.")
        with tab_acc_c2:
            with st.popover("➕ Aggiungi Conto", use_container_width=True):
                st.markdown("##### ➕ Nuovo Conto Bancario")
                with st.form("form_new_acc_tab2"):
                    n_name = st.text_input("Nome Conto *", placeholder="es. Intesa Sanpaolo")
                    n_inst = st.text_input("Istituto / Banca *", placeholder="es. Intesa Sanpaolo, Revolut")
                    n_type = st.selectbox("Tipo di Conto *", [
                        ("checking", "Conto Corrente"),
                        ("savings", "Conto Deposito"),
                        ("emergency_fund", "Fondo Emergenza"),
                        ("credit_card", "Carta di Credito (Passività)"),
                        ("loan", "Prestito Personale (Passività)"),
                        ("mortgage", "Mutuo Casa (Passività)"),
                        ("brokerage_cash", "Liquidità Broker / Titoli")
                    ], format_func=lambda x: x[1])
                    n_bal = st.number_input("Saldo Attuale (€) *", value=0.0, step=100.0)
                    n_iban = st.text_input("IBAN (Opzionale)")
                    n_notes = st.text_input("Note")
                    
                    if st.form_submit_button("Salva Conto", type="primary"):
                        if n_name and n_inst:
                            save_wealth_account(engine, {
                                "portfolio_id": current_pid,
                                "name": n_name,
                                "institution": n_inst,
                                "account_type": n_type[0],
                                "balance": n_bal,
                                "iban": n_iban,
                                "notes": n_notes,
                                "is_active": 1
                            })
                            st.success(f"Conto '{n_name}' salvato con successo!")
                            st.rerun()

        df_accs_view = get_wealth_accounts(engine, portfolio_id=current_pid)
        if not df_accs_view.empty:
            st.dataframe(
                df_accs_view[["account_id", "name", "institution", "account_type", "currency", "balance", "iban", "is_active"]].rename(columns={
                    "account_id": "ID",
                    "name": "Nome Conto",
                    "institution": "Banca / Istituto",
                    "account_type": "Tipo",
                    "currency": "Valuta",
                    "balance": "Saldo Attuale (€)",
                    "iban": "IBAN",
                    "is_active": "Attivo"
                }),
                use_container_width=True,
                hide_index=True
            )

            with st.expander("✏️ Gestisci / Elimina / Disattiva Singolo Conto"):
                acc_options = {r["account_id"]: f"{r['name']} ({r['institution']}) — Saldo: €{r['balance']:,.2f}" for _, r in df_accs_view.iterrows()}
                sel_del_id = st.selectbox("Seleziona Conto da Modificare:", options=list(acc_options.keys()), format_func=lambda x: acc_options[x], key="sel_mod_acc_tab2")
                
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("🗑️ Elimina Definitivamente Conto", type="primary", use_container_width=True, key="btn_confirm_del_acc_tab2"):
                        delete_wealth_account(engine, sel_del_id)
                        st.warning(f"Conto #{sel_del_id} eliminato con successo.")
                        st.rerun()
                with dc2:
                    is_currently_active = bool(df_accs_view[df_accs_view["account_id"] == sel_del_id]["is_active"].iloc[0])
                    toggle_label = "⏸️ Disattiva Conto" if is_currently_active else "▶️ Riattiva Conto"
                    if st.button(toggle_label, use_container_width=True, key="btn_toggle_active_acc_tab2"):
                        acc_row = df_accs_view[df_accs_view["account_id"] == sel_del_id].iloc[0]
                        save_wealth_account(engine, {
                            "account_id": sel_del_id,
                            "portfolio_id": current_pid,
                            "name": acc_row["name"],
                            "institution": acc_row["institution"],
                            "account_type": acc_row["account_type"],
                            "balance": float(acc_row["balance"]),
                            "is_active": 0 if is_currently_active else 1,
                            "iban": acc_row.get("iban"),
                            "notes": str(acc_row.get("notes", ""))
                        })
                        st.info(f"Stato conto #{sel_del_id} aggiornato.")
                        st.rerun()
        else:
            st.info("Nessun conto bancario censito in questo profilo.")

    # ── SUBTAB B: PORTAFOGLI RISK ANALYTICS ─────────────────
    with tab_risk_sub:
        st.markdown(f"##### 🔗 Portafogli Risk Analytics Collegati al Profilo '{profile_map.get(current_pid, 'Principale')}'")
        st.caption("Collega uno o più portafogli titoli, ETF o crypto del modulo Risk per sommare il loro controvalore agli investimenti finanziari del Net Worth.")

        df_risk_avail = get_available_risk_portfolios(engine, exclude_wealth_portfolio_id=current_pid)
        currently_linked_ids = get_linked_risk_portfolios(engine, wealth_portfolio_id=current_pid)


        if df_risk_avail.empty:
            st.info("ℹ️ Nessun portafoglio censito nel database collegato. Vai nella **Control Room del Rischio** per importare il tuo primo portafoglio titoli o crypto!")
        else:
            risk_options = {}
            for _, r in df_risk_avail.iterrows():
                pid = int(r["portfolio_id"])
                p_val = float(r["latest_value"])
                dt_calc = str(r["last_calc_date"]) if pd.notnull(r["last_calc_date"]) else "Nessun calcolo"
                risk_options[pid] = f"ID #{pid} · {r['name']} — Valore: {fmt_eur(p_val)} (Ultimo: {dt_calc})"

            has_active_links = len(currently_linked_ids) > 0
            profile_mode_choice = st.radio(
                "Modalità Operativa Investimenti per questo Profilo:",
                [
                    ("transational_only", "🚫 Solo Transazionale & Cassa (Nessun portafoglio titoli / Investimenti = € 0,00)"),
                    ("linked_risk", "🔗 Profilo con Investimenti (Collega uno o più portafogli dal modulo Risk Analytics)")
                ],
                format_func=lambda x: x[1],
                index=1 if has_active_links else 0,
                key=f"wealth_mgmt_profile_mode_radio_{current_pid}"
            )

            if profile_mode_choice[0] == "transational_only":
                st.markdown("""
                <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 14px 18px; margin: 12px 0;">
                    <span style="font-weight:700; color:#34d399; font-size:13.5px;">💳 Modalità Solo Transazionale Attiva</span>
                    <p style="font-size:12px; color:#94a3b8; margin: 6px 0 0 0;">
                        Questo profilo gestisce unicamente flussi di spesa/entrata, liquidità e 50/30/20. Gli investimenti finanziari restano a € 0,00.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                if has_active_links:
                    if st.button("🚫 Conferma e Scollega Portafogli Risk", type="primary", key=f"btn_confirm_trans_mgmt_{current_pid}"):
                        set_linked_risk_portfolios(engine, current_pid, [])
                        st.success("✅ Profilo impostato in modalità Solo Transazionale!")
                        st.rerun()
            else:
                default_selected = [pid for pid in currently_linked_ids if pid in risk_options]
                col_sel_r, col_save_r = st.columns([3.2, 1.8])
                with col_sel_r:
                    selected_risk_pids = st.multiselect(
                        "Seleziona i Portafogli Risk da collegare:",
                        options=list(risk_options.keys()),
                        format_func=lambda x: risk_options[x],
                        default=default_selected,
                        key=f"wealth_risk_mgmt_multisel_{current_pid}"
                    )
                with col_save_r:
                    st.write("")
                    st.write("")
                    bcol1, bcol2 = st.columns(2)
                    with bcol1:
                        if st.button("💾 Salva Link", type="primary", use_container_width=True, key=f"btn_save_risk_mgmt_{current_pid}"):
                            set_linked_risk_portfolios(engine, current_pid, selected_risk_pids)
                            st.success(f"✅ Collegati {len(selected_risk_pids)} portafogli Risk!")
                            st.rerun()
                    with bcol2:
                        if st.button("🗑️ Scollega", type="secondary", use_container_width=True, key=f"btn_clear_risk_mgmt_{current_pid}"):
                            set_linked_risk_portfolios(engine, current_pid, [])
                            st.warning("Portafogli Risk scollegati.")
                            st.rerun()

                tot_risk_val, df_linked_summary = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=current_pid)
                st.markdown(f"##### 📊 Investimenti Consolidati: **{fmt_eur(tot_risk_val)}**")
                if not df_linked_summary.empty:
                    df_disp_link = df_linked_summary.copy()
                    df_disp_link["Peso (%)"] = (df_disp_link["latest_value"] / tot_risk_val * 100.0) if tot_risk_val > 0 else 0.0
                    st.dataframe(
                        df_disp_link[["portfolio_id", "name", "base_currency", "last_calc_date", "latest_value", "Peso (%)"]].rename(columns={
                            "portfolio_id": "ID Portafoglio Risk",
                            "name": "Nome Portafoglio",
                            "base_currency": "Valuta",
                            "last_calc_date": "Ultimo Snapshot Calcolato",
                            "latest_value": "Controvalore (€)",
                            "Peso (%)": "Peso su Investimenti (%)"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )

    # ── SUBTAB C: CATEGORIE 50/30/20 ─────────────────────────
    with subtab_cats:
        st.markdown("##### 🏷️ Categorie Standard & Regola 50/30/20")
        st.caption("Tutte le spese ed entrate sono mappate semanticamente secondo il framework di pianificazione finanziaria istituzionale:")

        r_c1, r_c2, r_c3 = st.columns(3)
        with r_c1:
            st.markdown("""
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 14px;">
                <b style="color: #f87171;">🔴 50% — Bisogni Primari (Needs)</b><br>
                <span style="font-size:12px; color:#cbd5e1;">Spese essenziali non negoziabili: Casa, Affitto, Utenze, Spesa Supermercato, Trasporti, Tasse e Salute.</span>
            </div>
            """, unsafe_allow_html=True)
        with r_c2:
            st.markdown("""
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 14px;">
                <b style="color: #fbbf24;">🟡 30% — Desideri & Stile di Vita (Wants)</b><br>
                <span style="font-size:12px; color:#cbd5e1;">Spese discrezionali: Ristoranti, Viaggi, Shopping, Abbonamenti, Svago e Tempo Libero.</span>
            </div>
            """, unsafe_allow_html=True)
        with r_c3:
            st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 14px;">
                <b style="color: #34d399;">🟢 20% — Risparmio & Investimenti (Savings)</b><br>
                <span style="font-size:12px; color:#cbd5e1;">Accantonamenti patrimoniali: Investimenti Titoli/ETF, Criptovalute, Fondo Pensione e Fondo Emergenza.</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        df_cats = get_wealth_categories(engine)
        if not df_cats.empty:
            st.dataframe(
                df_cats[["category_id", "icon", "name", "flow_type", "nature", "color", "is_system"]].rename(columns={
                    "category_id": "ID",
                    "icon": "Icona",
                    "name": "Nome Categoria",
                    "flow_type": "Flusso (Entrata/Uscita)",
                    "nature": "Natura 50/30/20",
                    "color": "Colore",
                    "is_system": "Sistema"
                }),
                use_container_width=True,
                hide_index=True
            )

