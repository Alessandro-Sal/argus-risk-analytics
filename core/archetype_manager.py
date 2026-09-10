"""
core/archetype_manager.py
ARGUS Institutional — Unified Cross-Module Archetype & Scenario Manager

Permette il caricamento e la sincronizzazione 1-click di scenari didattici e archetipi
realistici simultaneamente sia per il modulo Risk Analytics che per il modulo Wealth Management.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional



def execute_unified_archetype_load(
    arch_code: str,
    auto_run: bool = False,
    source_module: str = "risk"
) -> Dict[str, Any]:
    """
    Esegue la simulazione quantitativa realistica e inietta l'archetipo sia su SQLite
    che su MySQL (se connesso), allineando simultaneamente lo stato di Risk Analytics
    e Wealth Management.
    """
    from scripts.generate_realistic_portfolio import PortfolioSimulationEngine, populate_argus_database
    from core.fetcher import get_engine
    from core.wealth.wealth_db import init_wealth_db, sync_wealth_tables_between_engines
    from core.models import Base

    sim_eng = PortfolioSimulationEngine(offline=True, seed=42)
    res_arch = sim_eng.simulate(arch_code, years=3)
    
    # 1. Popolamento database SQLite locale
    db_res = populate_argus_database(res_arch, sqlite_path="data/argus_local.db")
    risk_pid = db_res["risk_portfolio_id"]
    wealth_pid = db_res["wealth_profile_id"]

    # 2. Se MySQL è attivo e non siamo in offline_mode, sincronizza anche su MySQL
    is_offline = bool(st.session_state.get("offline_mode", False))
    if not is_offline:
        try:
            active_db = st.session_state.get("db_name") or st.session_state.get("wealth_db_name") or "wealth"
            db_u = st.session_state.get("db_user", "root")
            db_p = st.session_state.get("db_pass", "root")
            db_h = st.session_state.get("db_host", "localhost")
            db_port = int(st.session_state.get("db_port", 3306))

            eng_mysql = get_engine(db_u, db_p, db_h, db_port, active_db, database=active_db, offline=False)
            eng_sqlite = get_engine(offline=True, sqlite_path="data/argus_local.db")
            
            Base.metadata.create_all(eng_mysql)
            init_wealth_db(eng_mysql)
            sync_wealth_tables_between_engines(eng_sqlite, eng_mysql)
        except Exception:
            # Continua in ogni caso con SQLite locale se MySQL ha generato un errore
            pass

    # 3. Aggiorna Session State per Risk Analytics
    st.session_state["df_raw_injected"] = res_arch.trading_transactions_df
    st.session_state["portfolio_name"] = f"Archetipo: {res_arch.archetype.name}"
    st.session_state["portfolio_id"] = risk_pid
    st.session_state["active_archetype_code"] = arch_code
    st.session_state["active_archetype_name"] = res_arch.archetype.name
    st.session_state["active_archetype_tx_count"] = len(res_arch.trading_transactions_df)
    st.session_state["active_archetype_db_ids"] = db_res
    st.session_state["keep_archetype_expander_open"] = True
    st.session_state["archetype_just_injected"] = True

    # 4. Aggiorna Session State per Wealth Management
    st.session_state["wealth_active_portfolio_id"] = wealth_pid
    st.session_state["wealth_active_profile_name"] = f"Patrimonio {res_arch.archetype.name}"
    st.session_state.pop("wealth_profile_selector_widget", None)
    st.session_state.pop("cf_profile_selector_widget", None)
    st.session_state.pop("wealth_active_snapshot", None)

    # 5. Pulisce cache pipeline precedenti
    st.session_state.pop("session_cleared", None)
    st.session_state.pop("pipeline_done", None)
    st.session_state.pop("results", None)
    st.session_state.pop("fetch_report", None)

    if auto_run:
        st.session_state["auto_run_pipeline_requested"] = True

    # 6. Invalidazione cache Streamlit
    try:
        st.cache_data.clear()
    except Exception:
        pass

    return db_res


def clear_unified_archetype():
    """
    Rimuove l'archetipo attivo e ripulisce le chiavi di sessione per entrambi i moduli.
    """
    keys_to_clear = [
        "df_raw_injected",
        "active_archetype_code",
        "active_archetype_name",
        "active_archetype_tx_count",
        "active_archetype_db_ids",
        "keep_archetype_expander_open",
        "archetype_just_injected",
        "auto_run_pipeline_requested",
        "pipeline_done",
        "results",
        "fetch_report",
        "wealth_active_snapshot",
        "wealth_profile_selector_widget",
        "cf_profile_selector_widget"
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state["portfolio_name"] = ""
    st.session_state["wealth_active_portfolio_id"] = None

    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.rerun()


def render_unified_archetype_hud(current_module: str = "risk"):
    """
    Renderizza il banner HUD istituzionale quando uno scenario didattico è attivo in sessione,
    offrendo navigazione rapida 1-click tra il modulo Risk e il modulo Wealth.
    """
    active_code = st.session_state.get("active_archetype_code")
    if not active_code:
        return

    active_name = st.session_state.get("active_archetype_name", "Scenario")
    tx_count = st.session_state.get("active_archetype_tx_count", 0)
    db_ids = st.session_state.get("active_archetype_db_ids", {})
    r_id = db_ids.get("risk_portfolio_id", st.session_state.get("portfolio_id", 1))
    w_id = db_ids.get("wealth_profile_id", st.session_state.get("wealth_active_portfolio_id", 1))

    st.markdown(f"""
    <div style="background: rgba(46, 160, 67, 0.14); border: 1px solid rgba(46, 160, 67, 0.4); border-left: 4px solid #2ea043; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <div style="font-weight: 700; color: #3fb950; font-size: 14.5px;">
                    ✅ Scenario Didattico Attivo: <b>{active_name}</b> (Sincronizzato Cross-Modulo)
                </div>
                <div style="color: #c9d1d9; font-size: 12px; margin-top: 3px;">
                    • <b>{tx_count} transazioni</b> simulate | 📊 Trading Portfolio: <code>#{r_id}</code> • 🏛️ Wealth Profile: <code>#{w_id}</code><br>
                    • Portafoglio quantitativo e patrimonio multi-asset caricati contemporaneamente su <b>Risk Analytics</b> e <b>Wealth Management</b>.
                </div>
            </div>
            <span class="argus-command-pill" style="border-color: rgba(46,160,67,0.5); color: #3fb950; font-weight:700;">UNIFIED ECOSYSTEM ATTIVO</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if current_module == "risk":
        col_act1, col_act2, col_act3 = st.columns([2.2, 1.8, 1.2])
        with col_act1:
            if st.button("🚀 Avvia Subito Analisi Quantitativa ARGUS", key="btn_hud_run_risk", type="primary", use_container_width=True):
                st.session_state["auto_run_pipeline_requested"] = True
                st.rerun()
        with col_act2:
            if st.button("🏛️ Esplora Patrimonio & Net Worth", key="btn_hud_goto_wealth", type="secondary", use_container_width=True):
                st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")
        with col_act3:
            if st.button("🗑️ Rimuovi Scenario", key="btn_hud_clear_risk", type="secondary", use_container_width=True):
                clear_unified_archetype()
    else:
        col_act1, col_act2, col_act3 = st.columns([2.2, 1.8, 1.2])
        with col_act1:
            if st.button("🏛️ Esplora Patrimonio & Net Worth", key="btn_hud_w_goto_nw", type="primary", use_container_width=True):
                st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")
        with col_act2:
            if st.button("📊 Vai ad Analisi Rischio & Portafoglio", key="btn_hud_w_goto_risk", type="secondary", use_container_width=True):
                st.switch_page("0_Control_Room.py")
        with col_act3:
            if st.button("🗑️ Rimuovi Scenario", key="btn_hud_clear_wealth", type="secondary", use_container_width=True):
                clear_unified_archetype()

    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)
