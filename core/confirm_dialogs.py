"""
ARGUS Risk & Wealth — Centralized Confirmation Modals Hub (@st.dialog)
====================================================================
Fornisce modali di sicurezza conformi allo standard istituzionale Bloomberg / Aladdin
per prevenire cancellazioni accidentali, perdite di sessione e distruzione di dati.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ── 1. ELIMINAZIONE SNAPSHOT RISK ENGINE ─────────────────────────
@st.dialog("⚠️ Conferma Eliminazione Snapshot", width="small")
def confirm_delete_snapshot_dialog(engine: Any, run_id: str, port_name: str, port_id: int) -> None:
    """Modale di conferma per l'eliminazione definitiva di un singolo snapshot dal database."""
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Eliminazione Definitiva Snapshot</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler eliminare questo snapshot analitico? L'operazione rimuoverà in modo permanente posizioni calcolate, metriche di rischio e metadati storici dal database.
            </div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 10px 12px; margin-bottom: 16px; font-size: 12px;">
            <div><b>Portafoglio:</b> <span style="color:#58a6ff; font-weight:600;">{port_name}</span></div>
            <div style="margin-top: 4px;"><b>Run ID:</b> <code style="color:#ff9900;">{run_id}</code></div>
            <div style="margin-top: 4px;"><b>Portfolio ID:</b> <code>{port_id}</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_del_snap_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Elimina Snapshot", type="primary", use_container_width=True, key="dlg_del_snap_confirm"):
            from sqlalchemy import text as sqlt

            with engine.begin() as conn:
                snap_id = conn.execute(
                    sqlt("SELECT snapshot_id FROM portfolio_snapshots WHERE run_id = :rid"),
                    {"rid": run_id},
                ).scalar()
                if snap_id:
                    conn.execute(
                        sqlt("DELETE FROM snapshot_positions WHERE snapshot_id = :sid"),
                        {"sid": snap_id},
                    )
                    conn.execute(
                        sqlt("DELETE FROM portfolio_snapshots WHERE snapshot_id = :sid"),
                        {"sid": snap_id},
                    )

                rem_snaps = conn.execute(
                    sqlt("SELECT COUNT(*) FROM portfolio_snapshots WHERE portfolio_id = :pid"),
                    {"pid": port_id},
                ).scalar()
                rem_tx = conn.execute(
                    sqlt("SELECT COUNT(*) FROM transactions WHERE portfolio_id = :pid"),
                    {"pid": port_id},
                ).scalar()
                if rem_snaps == 0 and rem_tx == 0:
                    conn.execute(
                        sqlt("DELETE FROM portfolios WHERE portfolio_id = :pid"),
                        {"pid": port_id},
                    )

            st.toast(f"✅ Snapshot '{run_id}' eliminato con successo!", icon="🗑️")
            st.rerun()


# ── 2. RESET SESSIONE ATTIVA (CONTROL ROOM) ──────────────────────
@st.dialog("⚠️ Conferma Reset Sessione", width="small")
def confirm_reset_session_dialog(portfolio_name: str = "", run_id: str = "") -> None:
    """Modale di sicurezza per azzerare lo stato di calcolo corrente in memoria RAM."""
    p_name = portfolio_name or st.session_state.get("portfolio_name", "Portafoglio")
    r_id = run_id or st.session_state.get("run_id", "N/A")
    st.markdown(
        f"""
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">Azzeramento Sessione Attiva</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Vuoi scaricare l'analisi corrente dalla memoria RAM per elaborare un nuovo portafoglio? I dati precedentemente archiviati nel Database SQLite rimarranno intatti.
            </div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 10px 12px; margin-bottom: 16px; font-size: 12px;">
            <div><b>Portafoglio:</b> <span style="color:#58a6ff; font-weight:600;">{p_name}</span></div>
            <div style="margin-top: 4px;"><b>Run ID:</b> <code style="color:#ff9900;">{r_id}</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_reset_sess_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔄 Conferma Reset", type="primary", use_container_width=True, key="dlg_reset_sess_confirm"):
            from core.workspace_context import WorkspaceContext
            from core.workspace_manager import clear_session_cache

            for k in [
                "df_raw_injected",
                "active_archetype_code",
                "active_archetype_name",
                "active_archetype_tx_count",
                "active_archetype_db_ids",
                "keep_archetype_expander_open",
                "archetype_just_injected",
                "auto_run_pipeline_requested",
                "df_clean",
                "selected_bitemp_port",
            ]:
                st.session_state.pop(k, None)
            clear_session_cache()
            WorkspaceContext.sanitize_risk_portfolio_state(preserve_db_creds=True)
            st.toast("✅ Sessione azzerata con successo!", icon="🔄")
            st.rerun()


# ── 3. ELIMINAZIONE PROFILO SALVATO (MULTI-PORTAFOGLIO) ──────────
@st.dialog("⚠️ Conferma Eliminazione Profilo", width="small")
def confirm_delete_portfolio_profile_dialog(profile_name: str) -> None:
    """Modale di conferma per eliminare un profilo multi-portafoglio salvato su disco."""
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Eliminazione Profilo Salvato</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler eliminare dal registro il profilo <b>{profile_name}</b>? Il file di configurazione JSON verrà rimosso in modo irreversibile.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_del_prof_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Elimina Profilo", type="primary", use_container_width=True, key="dlg_del_prof_confirm"):
            from core.multi_portfolio import delete_saved_portfolio_profile

            delete_saved_portfolio_profile(profile_name)
            st.toast(f"✅ Profilo '{profile_name}' eliminato con successo!", icon="🗑️")
            st.rerun()


# ── 4. SVUOTAMENTO CACHE MULTI-TIER L1 & L2 ───────────────────────
@st.dialog("⚠️ Conferma Svuotamento Cache", width="small")
def confirm_flush_cache_dialog() -> None:
    """Modale di sicurezza per lo svuotamento integrale della cache multi-tier."""
    st.markdown(
        """
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Svuotamento Integrale Cache Multi-Tier</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Verranno eliminati sia gli oggetti in memoria RAM L1 che tutti i record su disco SQLite L2. Alla prossima esecuzione tutti i dati di mercato dovranno essere riscaricati dai provider.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_flush_cache_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🗑️ Svuota Tutta la Cache", type="primary", use_container_width=True, key="dlg_flush_cache_confirm"):
            from core.fetcher import clear_cache

            cleared_n = clear_cache()
            st.toast(f"✅ Cache svuotata con successo ({cleared_n} record rimossi)!", icon="🧹")
            st.rerun()


# ── 5. ELIMINAZIONE PROFILO PATRIMONIALE WEALTH ──────────────────
@st.dialog("⚠️ ATTENZIONE: Eliminazione Profilo Patrimoniale", width="small")
def confirm_delete_wealth_portfolio_dialog(
    engine: Any,
    portfolio_id: int,
    profile_name: str,
    remaining_ids: list[int] | None = None,
) -> None:
    """Modale con avvertimento critico per l'eliminazione a cascata di un profilo patrimoniale."""
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.12); border-left: 4px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 800; color: #f87171; letter-spacing: 0.3px;">OPERAZIONE DISTRUTTIVA IRREVERSIBILE</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.45;">
                Stai per eliminare il profilo patrimoniale <b>{profile_name}</b> (ID: {portfolio_id}).<br>
                Tutti i <b>conti bancari, depositi, immobili, piani previdenziali, flussi di cassa, scadenze e snapshot</b> collegati verranno <span style="color:#ef4444; font-weight:700;">cancellati definitivamente</span> dal database locale.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_del_wprof_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Elimina Profilo Definitivamente", type="primary", use_container_width=True, key="dlg_del_wprof_confirm"):
            from core.wealth.wealth_db import delete_wealth_portfolio

            delete_wealth_portfolio(engine, portfolio_id)
            if remaining_ids:
                st.session_state["wealth_active_portfolio_id"] = remaining_ids[0]
            else:
                st.session_state.pop("wealth_active_portfolio_id", None)
            st.toast(f"✅ Profilo '{profile_name}' eliminato con successo.", icon="🗑️")
            st.rerun()


# ── 6. ELIMINAZIONE SNAPSHOT PATRIMONIALE WEALTH ─────────────────
@st.dialog("⚠️ Conferma Eliminazione Snapshot Patrimoniale", width="small")
def confirm_delete_wealth_snapshot_dialog(
    engine: Any,
    snapshot_id: int,
    snapshot_name: str = "",
    snapshot_date: str = "",
) -> None:
    """Modale di conferma per eliminare un singolo snapshot Net Worth dal database."""
    name_str = snapshot_name or f"Snapshot #{snapshot_id}"
    date_str = f"({snapshot_date})" if snapshot_date else ""
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Eliminazione Snapshot Patrimoniale</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler eliminare lo snapshot <b>{name_str}</b> {date_str}? L'operazione rimuoverà la fotografia storica del patrimonio netto e non potrà essere annullata.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_del_wsnap_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Elimina Snapshot", type="primary", use_container_width=True, key="dlg_del_wsnap_confirm"):
            from core.wealth.wealth_db import delete_wealth_snapshot

            if delete_wealth_snapshot(engine, snapshot_id):
                if st.session_state.get("wealth_active_snapshot", {}).get("snapshot_id") == snapshot_id:
                    st.session_state.pop("wealth_active_snapshot", None)
                st.toast("✅ Snapshot patrimoniale eliminato dal database.", icon="🗑️")
            else:
                st.error("Errore durante l'eliminazione dello snapshot.")
            st.rerun()


# ── 7. ELIMINAZIONE CONTO BANCARIO / DEPOSITO WEALTH ──────────────
@st.dialog("⚠️ Conferma Eliminazione Conto", width="small")
def confirm_delete_wealth_account_dialog(
    engine: Any,
    account_id: int,
    account_name: str = "",
    institution: str = "",
    balance: float = 0.0,
) -> None:
    """Modale di sicurezza per eliminare definitivamente un conto bancario o deposito titoli."""
    from core.ui_utils import fmt_eur

    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Eliminazione Definitiva Conto</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Stai per eliminare il conto <b>{account_name}</b> ({institution}) con saldo attuale di <b>{fmt_eur(balance)}</b>.<br>
                Tutti i movimenti e le transazioni associate a questo conto verranno eliminati.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_del_acc_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Elimina Conto Definitivamente", type="primary", use_container_width=True, key="dlg_del_acc_confirm"):
            from core.wealth.wealth_db import delete_wealth_account

            delete_wealth_account(engine, account_id)
            st.toast(f"✅ Conto '{account_name}' eliminato con successo.", icon="🗑️")
            st.rerun()


# ── 8. SCOLLEGAMENTO PORTAFOGLIO RISK DA WEALTH ──────────────────
@st.dialog("⚠️ Conferma Scollegamento Portafogli Risk", width="small")
def confirm_unlink_risk_portfolio_dialog(engine: Any, portfolio_id: int) -> None:
    """Modale di conferma per scollegare i portafogli quantitativi dal profilo Wealth."""
    st.markdown(
        """
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">Scollegamento Portafogli Finanziari</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                I portafogli quantitativi non saranno più aggregati nel patrimonio complessivo di questo profilo. I portafogli originali rimarranno intatti nel motore di rischio.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_unlink_risk_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🗑️ Scollega Portafogli", type="primary", use_container_width=True, key="dlg_unlink_risk_confirm"):
            from core.wealth.wealth_db import set_linked_risk_portfolios

            set_linked_risk_portfolios(engine, portfolio_id, [])
            st.toast("✅ Portafogli Risk scollegati dal profilo.", icon="🔗")
            st.rerun()


# ── 9. ELIMINAZIONE OBIETTIVO FINANZIARIO (FIRE GOAL) ─────────────
@st.dialog("⚠️ Conferma Rimozione Obiettivo FIRE", width="small")
def confirm_delete_wealth_goal_dialog(
    engine: Any,
    goal_id: int,
    goal_name: str = "",
    target_amount: float = 0.0,
) -> None:
    """Modale di sicurezza per rimuovere un obiettivo di vita o target FIRE."""
    from core.ui_utils import fmt_eur

    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Rimozione Obiettivo Finanziario</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler rimuovere l'obiettivo <b>#{goal_id} - {goal_name}</b> (Target: <b>{fmt_eur(target_amount)}</b>)? La pianificazione Monte Carlo e le scadenze relative verranno rimosse.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key=f"dlg_del_goal_cancel_{goal_id}"):
            st.rerun()
    with col_ok:
        if st.button("🔴 Rimuovi Obiettivo", type="primary", use_container_width=True, key=f"dlg_del_goal_confirm_{goal_id}"):
            from core.wealth.wealth_db import delete_wealth_goal

            delete_wealth_goal(engine, goal_id)
            st.toast(f"✅ Obiettivo #{goal_id} rimosso con successo.", icon="🗑️")
            st.rerun()


# ── 10. SVUOTAMENTO WATCHLIST SCREENER ────────────────────────────
@st.dialog("⚠️ Conferma Svuotamento Watchlist", width="small")
def confirm_clear_watchlist_dialog(count: int = 0) -> None:
    """Modale di sicurezza per svuotare l'universo dei titoli monitorati nella Watchlist."""
    st.markdown(
        f"""
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #f87171;">Svuotamento Watchlist Opportunità</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler eliminare tutti i <b>{count} titoli</b> attualmente salvati nella tua Watchlist di monitoraggio?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_clear_wl_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🗑️ Svuota Watchlist", type="primary", use_container_width=True, key="dlg_clear_wl_confirm"):
            st.session_state.screener_watchlist = []
            st.toast("✅ Watchlist svuotata con successo.", icon="🗑️")
            st.rerun()


# ── 11. RESET CACHE DA SPOTLIGHT PALETTE ─────────────────────────
@st.dialog("⚠️ Conferma Reset Cache di Sessione", width="small")
def confirm_reset_spotlight_cache_dialog(portal_mode: str = "risk") -> None:
    """Modale di conferma per il reset cache avviato dalla Bloomberg-style Spotlight Palette."""
    is_wealth = portal_mode == "wealth"
    mode_text = "Wealth Management" if is_wealth else "Risk & Quantitative Analytics"
    st.markdown(
        f"""
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">Reset Cache &amp; Ricaricamento Desk</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Vuoi cancellare la cache di memoria per il portale <b>{mode_text}</b> e ripristinare lo stato iniziale della sessione?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_spot_reset_cancel"):
            st.rerun()
    with col_ok:
        if st.button("♻️ Conferma Reset Cache", type="primary", use_container_width=True, key="dlg_spot_reset_confirm"):
            from core.ui_utils import switch_to_page
            from core.workspace_manager import clear_session_cache

            clear_session_cache()
            st.cache_data.clear()
            for k in list(st.session_state.keys()):
                if k not in ["splash_dismissed"]:
                    del st.session_state[k]

            if is_wealth:
                st.session_state.argus_portal_mode = "🏛️ Wealth Management"
                switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")
            else:
                switch_to_page("0_Control_Room.py")


# ── 12. RESET TEMPLATE SNIPPET BQUANT ─────────────────────────────
@st.dialog("⚠️ Conferma Ripristino Template", width="small")
def confirm_reset_bquant_snippet_dialog(snippet_name: str = "") -> None:
    """Modale di sicurezza per ripristinare il codice Python originale di uno snippet BQuant."""
    s_name = snippet_name or "selezionato"
    st.markdown(
        f"""
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">Ripristino Codice Originale</div>
            <div style="font-size: 11.5px; color: #cbd5e1; margin-top: 4px; line-height: 1.4;">
                Sei sicuro di voler ripristinare il template <b>{s_name}</b>? Eventuali modifiche e algoritmi personalizzati scritti nell'editor verranno sovrascritti.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c, col_ok = st.columns([1, 1.2])
    with col_c:
        if st.button("Annulla", use_container_width=True, key="dlg_bquant_reset_cancel"):
            st.rerun()
    with col_ok:
        if st.button("🔄 Ripristina Template", type="primary", use_container_width=True, key="dlg_bquant_reset_confirm"):
            st.session_state["bquant_reset_confirmed"] = True
            st.rerun()
