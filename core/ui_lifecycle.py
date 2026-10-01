"""
ARGUS — State Management & UI Lifecycle Architecture
====================================================
Unified Hard Reset, State Sanitization, Dynamic Widget Key Salting, and View Teardown.

This module guarantees strict isolation of application and UI state across:
1. Screen & Page Navigation (Pages 0 through 21)
2. Profile & Workspace Switches (Wealth Profiles and Risk Portfolios)
3. Database & Environment Switches (Online MySQL / Offline SQLite)
4. Manual Session Resets

Design Principles:
- Single Source of Truth for lifecycle markers (_ui_lifecycle_active_page, etc.)
- Zero Ghost State: Purges volatile models, temporary filters, and orphaned widget keys.
- Dynamic Key Salting: Automatically generates context-aware widget keys to force
  Streamlit to unmount stale components and remount fresh instances with proper defaults.
- Pre-Render Data Synchronization: Guarantees that data recalculation and state teardown
  occur BEFORE visual components mount, eliminating UI frame flickering and data bleed.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
from typing import Any, Dict, List, MutableMapping, Optional, Set, Tuple

logger = logging.getLogger("argus.ui_lifecycle")

# ── 1. STATE CATEGORIZATION & REGISTRY ─────────────────────────────

# Chiavi infrastrutturali e di configurazione globale che DEVONO SOPRAVVIVERE
# a qualsiasi teardown (navigazione pagina, switch profilo, o switch database).
SYSTEM_PERSISTENT_KEYS: Set[str] = {
    # Core UI Infrastructure
    "splash_dismissed",
    "sidebar_expanded",
    "theme",
    "argus_portal_mode",
    "_app_initialized",
    "session_cleared",
    # Global Currency & Localization
    "base_currency",
    "confidence_level",
    "locale",
    "accounting_notation",
    "data_environment",
    "offline_mode",
    # Database Credentials & Canonical Configuration
    "db_host",
    "db_port",
    "db_user",
    "db_pass",
    "db_name",
    "wealth_db_name",
    "risk_db_name",
    # Global Risk Engine Settings
    "risk_estimation_method",
    "risk_lookback_period",
    "risk_decay_factor",
    "benchmark",
    "rf_mode",
    "custom_rf_rate_pct",
    # Global Wealth Planning Parameters
    "wealth_planning_horizon_years",
    "wealth_expected_return_pct",
    "wealth_inflation_rate_pct",
    "wealth_tax_regime",
    "wealth_stress_scenario",
    "wealth_budget_preset",
    "wealth_budget_needs_pct",
    "wealth_budget_wants_pct",
    "wealth_budget_savings_pct",
    "wealth_fire_swr",
    "wealth_target_retirement_age",
    "wealth_pension_deduction_limit",
    # Sidebar Widget Keys (prevent input resets in settings modal and sidebar controls)
    "sb_base_currency",
    "sb_confidence_level",
    "sb_locale_select",
    "sb_accounting_select",
    "sb_data_environment",
    "sb_offline_toggle",
    "sb_db_host",
    "sb_db_port",
    "sb_db_user",
    "sb_db_pass",
    "sb_db_select",
    "sb_risk_method",
    "sb_risk_lookback",
    "sb_risk_decay",
    "sb_bench_select",
    "sb_rf_mode",
    "sb_wealth_horizon",
    "sb_wealth_exp_return",
    "sb_wealth_inflation",
    "sb_wealth_tax_regime",
    "sb_wealth_stress",
    "sb_wealth_preset_sel",
    "sb_wb_needs",
    "sb_wb_wants",
    "sb_wb_savings",
    "sb_wealth_swr_input",
    "sb_wealth_age_input",
    "sb_wealth_profile_selector",
    # Active Connection Pool Handles (preserved across page navigation, disposed on DB switch)
    "engine",
    "db_engine",
    # Workspace Context Singleton handles
    "_ARGUS_WORKSPACE_CONTEXT_",
    "_ARGUS_SESSION_UUID_",
    # UI Lifecycle Internal Markers
    "_ui_lifecycle_active_page",
    "_ui_lifecycle_active_profile",
    "_ui_lifecycle_active_db",
    "_ui_lifecycle_render_seq",
    "_ui_lifecycle_salt_version",
}

# Chiavi di instradamento del contesto di dominio attivo (profilo / portafoglio)
DOMAIN_ROUTING_KEYS: Set[str] = {
    # Wealth routing
    "wealth_active_portfolio_id",
    "wealth_active_profile_name",
    # Risk routing
    "portfolio_id",
    "portfolio_name",
    "active_portfolio_id",
    "selected_portfolio_id",
}

# Chiavi analitiche volatili e buffer di calcolo in memoria che devono essere
# azzerate all'evento di switch per prevenire contaminazioni o frame con dati obsoleti.
WEALTH_TRANSIENT_KEYS: Set[str] = {
    "wealth_active_snapshot",
    "triagent_last_results",
}

RISK_TRANSIENT_KEYS: Set[str] = {
    "results",
    "pipeline_done",
    "last_pipeline_hash",
    "fetch_report",
    "sandbox_preset_name",
    "cached_screener_df",
    "last_screened_universe_key",
    "last_screened_universe",
    "last_bquant_result",
    "screener_candidate_to_optimize",
    "rl_portfolio_results",
    "wfo_last_result",
    "barra_last_result",
    "dcc_last_result",
    "sabr_last_result",
    "heston_last_result",
    "bl_last_result",
}

TRANSIENT_ANALYTICAL_KEYS: Set[str] = WEALTH_TRANSIENT_KEYS | RISK_TRANSIENT_KEYS

# Prefissi di widget proprietari di ciascuna schermata (Pages 0 - 21)
# Utilizzati per purgare deterministicamente lo stato dei widget della pagina precedente al cambio vista.
PAGE_WIDGET_PREFIXES: Dict[str, Tuple[str, ...]] = {
    "0_Control_Room": ("cr_", "inp_port_", "sel_cr_", "file_uploader_"),
    "1_Dashboard_Generale": ("dash_", "p1_", "kpi_"),
    "2_Live_Terminal": ("live_", "tape_", "sel_tape_", "p2_"),
    "3_Analisi_Rischio": ("risk_", "var_", "cvar_", "p3_"),
    "4_Modelli_Quantitativi": ("quant_", "frontier_", "bl_", "rl_", "p4_"),
    "5_Posizioni_e_Dettagli": ("pos_", "filter_main_pos_", "search_div_", "p5_"),
    "6_Valutazione_Aziendale": ("dcf_", "radio_dcf_", "selectbox_dcf_", "p6_"),
    "7_Stress_Testing": ("stress_", "custom_stress_", "p7_"),
    "8_Analisi_Temporale": ("time_", "hist_port_", "select_history_", "p8_"),
    "9_Analisi_Tecnica": ("tech_", "candlestick_", "p9_"),
    "10_Screener_Opportunita": ("screener_", "radar_", "p10_"),
    "11_BQuant_e_Launchpad": ("bquant_", "sandbox_", "launchpad_", "p11_"),
    "12_Wealth_Control_Room": ("wealth_cr_", "pipe_csv_", "pipe_up_", "pipe_gsheet_", "sel_mod_acc_", "p12_"),
    "13_Patrimonio_e_NetWorth": ("wealth_nw_", "alloc_", "master_pbs_", "nw_stress_", "toggle_pbs_", "toggle_ts_", "p13_"),
    "14_Cash_Flow_e_Spese": ("wealth_cf_", "cf_", "sankey_", "p14_"),
    "15_Asset_Illiquidi_e_Orologi": ("wealth_illiquid_", "asset_illiquid_", "watch_", "p15_"),
    "16_Previdenza_e_Pension_Planning": ("wealth_pension_", "pension_", "p16_"),
    "17_Indipendenza_Finanziaria_e_FIRE": ("wealth_fire_", "fire_", "srr_", "p17_"),
    "18_Fiscalita_e_Quadro_RW": ("wealth_tax_", "fiscal_", "rw_", "zainetto_", "p18_"),
    "19_Immobili_e_Mutui": ("wealth_re_", "re_", "mutuo_", "p19_"),
    "20_Pianificazione_Successoria": ("wealth_estate_", "estate_", "legittima_", "p20_"),
    "21_AI_Copilot_e_Advisor": ("wealth_copilot_", "ai_", "triagent_", "p21_"),
}


# ── 2. HELPER FUNCTIONS & CANONICAL NAMESPACES ─────────────────────

def _get_session_state() -> Optional[MutableMapping[str, Any]]:
    """Recupera in modo difensivo st.session_state (supporta anche mock di test)."""
    try:
        import streamlit as st
        return getattr(st, "session_state", None)
    except Exception:
        return None


def normalize_page_identifier(page_file_or_name: Optional[str]) -> str:
    """
    Normalizza qualsiasi percorso file o nome pagina (con directory, emoji o estensioni)
    in un identificatore canonico 'N_NomePagina' (es. '14_Cash_Flow_e_Spese').
    """
    if not page_file_or_name:
        return ""
    base = os.path.basename(str(page_file_or_name).replace("\\", "/"))
    if base.endswith(".py"):
        base = base[:-3]
    # Rimuove emoji e caratteri speciali preservando alfanumerici e underscore
    parts = base.split("_")
    cleaned_parts: List[str] = []
    for p in parts:
        if p.isdigit():
            cleaned_parts.append(p)
        else:
            clean_sub = "".join(c for c in p if c.isalnum())
            if clean_sub:
                cleaned_parts.append(clean_sub)
    return "_".join(cleaned_parts)


def get_active_page_name() -> str:
    """Rileva con precisione il nome della pagina attiva corrente."""
    st_state = _get_session_state()
    if st_state is not None and st_state.get("_ui_lifecycle_active_page"):
        return str(st_state["_ui_lifecycle_active_page"])
    try:
        from core.sidebar import get_current_page_name
        p = get_current_page_name()
        if p and not any(ign in p for ign in ("pytest", "main.py", "__main__")):
            return p
    except Exception:
        pass
    return "0_Control_Room.py"


def get_active_context_salt(scope: str = "auto", page: Optional[str] = None) -> str:
    """
    Calcola un salt deterministico basato sul contesto attivo (pagina, database, profilo, versione).
    """
    st_state = _get_session_state() or {}
    resolved_page = page or get_active_page_name()
    page_id = normalize_page_identifier(resolved_page) or "global"
    
    # Risoluzione profilo attivo (Wealth o Risk)
    pid = st_state.get("wealth_active_portfolio_id")
    if pid is None:
        pid = st_state.get("portfolio_id")
    pid_str = str(pid) if pid is not None else "0"

    # Risoluzione fingerprint DB (combina engine URL/handle canonico e nome DB attivo)
    from core.workspace_context import get_canonical_db_fingerprint
    eng = st_state.get("engine") or st_state.get("db_engine")
    db_raw = st_state.get("db_name") or st_state.get("wealth_db_name") or "default"
    db_fp = f"{get_canonical_db_fingerprint(eng)}::{db_raw}"
    db_hash = hashlib.md5(db_fp.encode("utf-8")).hexdigest()[:6]

    v = int(st_state.get("_ui_lifecycle_salt_version", 1))

    if scope == "page":
        return f"pg_{page_id}"
    elif scope == "profile":
        return f"pg_{page_id}__pr_{pid_str}"
    elif scope == "db":
        return f"pg_{page_id}__db_{db_hash}"
    else:  # "auto"
        return f"pg_{page_id}__db_{db_hash}__pr_{pid_str}__v{v}"


def get_widget_key(
    base_key: str,
    scope: str = "auto",
    salt: Optional[str] = None,
    page: Optional[str] = None,
) -> str:
    """
    Genera una chiave dinamica univoca per widget Streamlit, iniettando un salt deterministico
    derivato dal contesto attivo (pagina, DB, profilo, versione teardown).

    Vantaggi architetturali:
    1. Forza Streamlit a dismettere lo stato del widget precedente quando il profilo o il DB muta,
       evitando il crash per indice fuori range o l'uso involontario di selezioni stantìe.
    2. Rende la UI immune da memory leak e interferenze cross-pagina.
    3. Conserva l'input dell'utente durante i normali rerun sulla stessa pagina/profilo.

    Esempio di utilizzo:
        st.selectbox("Conto:", options, key=get_widget_key("cf_acc_picker"))
    """
    if salt is None:
        salt = get_active_context_salt(scope=scope, page=page)
    return f"{base_key}__{salt}"


# ── 3. UNIFIED ATOMIC TEARDOWN CONTROLLER ──────────────────────────

def teardown_view_state(
    target_page: Optional[str] = None,
    force: bool = False,
    reason: str = "lifecycle",
) -> Dict[str, Any]:
    """
    Esegue il teardown atomico e la bonifica dello stato applicativo e della UI.
    Riconosce automaticamente il tipo di transizione:
    - Transizione Database: Dispose pool connessioni, flush cache processo & disco, wipe totale transient.
    - Transizione Profilo: Flush snapshot, wipe modelli analitici, bonifica filtri/widget orfani, incremento salt.
    - Transizione Pagina: Purge selettivo dei widget della pagina precedente, reset filtri di ricerca volatili.

    Parametri:
    - target_page: file o identificativo della pagina di destinazione (se None, rileva la corrente).
    - force: se True, forza un hard reset completo mantenendo solo le credenziali di sistema.
    - reason: etichetta descrittiva del trigger (es. 'navigation', 'profile_switch', 'database_switch').

    Ritorna:
        Dizionario con metriche sull'operazione (tipo transizione, chiavi epurate, tempo).
    """
    st_state = _get_session_state()
    if st_state is None:
        return {"purged_keys_count": 0, "status": "no_session"}

    if target_page is None:
        target_page = get_active_page_name()
    norm_target = normalize_page_identifier(target_page)

    last_page = st_state.get("_ui_lifecycle_active_page")
    last_norm = normalize_page_identifier(last_page) if last_page else ""
    last_pid = st_state.get("_ui_lifecycle_active_profile")
    last_db = st_state.get("_ui_lifecycle_active_db")

    curr_pid = st_state.get("wealth_active_portfolio_id")
    if curr_pid is None:
        curr_pid = st_state.get("portfolio_id")
    curr_db = st_state.get("db_name")

    # Rilevamento delle condizioni di transizione
    is_db_transition = bool(last_db is not None and curr_db is not None and curr_db != last_db)
    is_profile_transition = bool(last_pid is not None and curr_pid is not None and curr_pid != last_pid)
    is_page_transition = bool(norm_target and last_norm and norm_target != last_norm)

    purged_keys: List[str] = []
    transition_type = "none"

    # CASO 1: HARD RESET o SWITCH DATABASE
    if force or is_db_transition or reason in ("database_switch", "manual_full_reset"):
        transition_type = "database_or_hard_reset"
        logger.info(
            "Executing Hard Reset Teardown [reason='%s', force=%s, db: '%s' -> '%s']",
            reason,
            force,
            last_db,
            curr_db,
        )

        # 1. Dispose pool di connessioni se switch DB o full reset
        try:
            from core.fetcher import dispose_engine
            eng1 = st_state.get("engine")
            eng2 = st_state.get("db_engine")
            if eng1 is not None:
                dispose_engine(eng1)
            if eng2 is not None and eng2 is not eng1:
                dispose_engine(eng2)
        except Exception:
            pass
        if force or reason == "manual_full_reset":
            st_state["engine"] = None
            st_state["db_engine"] = None

        # 2. Svuotamento cache Streamlit e cache su disco
        try:
            import streamlit as st
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        try:
            from core.cache_shield import clear_cache as clear_shield_cache
            clear_shield_cache()
        except Exception:
            pass

        # 3. Incremento del salt version per invalidare tutti i widget montati
        curr_ver = int(st_state.get("_ui_lifecycle_salt_version", 1))
        st_state["_ui_lifecycle_salt_version"] = curr_ver + 1

        # 4. Epura tutte le chiavi eccetto SYSTEM_PERSISTENT_KEYS
        all_keys = list(st_state.keys())
        for k in all_keys:
            if k not in SYSTEM_PERSISTENT_KEYS:
                st_state.pop(k, None)
                purged_keys.append(k)

        # 5. Flush dei domini di WorkspaceContext
        try:
            from core.workspace_context import WorkspaceContext
            ws = WorkspaceContext.get_current()
            ws.flush_wealth_domain()
            ws.flush_risk_domain()
        except Exception:
            pass

        # Rimozione esplicita delle chiavi di routing orfane dopo il flush dei domini
        for rk in DOMAIN_ROUTING_KEYS:
            st_state.pop(rk, None)

    # CASO 2: SWITCH PROFILO / WORKSPACE
    elif is_profile_transition or reason in ("profile_switch", "wealth_profile_switch"):
        transition_type = "profile_switch"
        logger.info(
            "Executing Profile Switch Teardown [reason='%s', pid: '%s' -> '%s']",
            reason,
            last_pid,
            curr_pid,
        )

        # Incremento salt version per rigenerare le chiavi dinamiche dei widget
        curr_ver = int(st_state.get("_ui_lifecycle_salt_version", 1))
        st_state["_ui_lifecycle_salt_version"] = curr_ver + 1

        # Invalida cache dati di processo
        try:
            import streamlit as st
            st.cache_data.clear()
        except Exception:
            pass

        # Rilevamento dominio di switch: se esplicitato dal chiamante rispetta la segregazione,
        # altrimenti esegue bonifica analitica unificata di entrambi i domini.
        is_wealth_domain = (reason == "wealth_profile_switch")
        is_risk_domain = (reason == "risk_portfolio_switch")

        from core.workspace_context import (
            ANALYTICAL_EXACT_KEYS,
            ANALYTICAL_ORPHAN_PREFIXES,
            WEALTH_ORPHAN_EXACT_KEYS,
            WEALTH_ORPHAN_PREFIXES,
        )

        if is_wealth_domain and not is_risk_domain:
            target_transient = WEALTH_TRANSIENT_KEYS
            target_exact = WEALTH_ORPHAN_EXACT_KEYS
            target_prefixes = WEALTH_ORPHAN_PREFIXES
        elif is_risk_domain and not is_wealth_domain:
            target_transient = RISK_TRANSIENT_KEYS
            target_exact = ANALYTICAL_EXACT_KEYS
            target_prefixes = ANALYTICAL_ORPHAN_PREFIXES
        else:
            target_transient = TRANSIENT_ANALYTICAL_KEYS
            target_exact = WEALTH_ORPHAN_EXACT_KEYS | ANALYTICAL_EXACT_KEYS
            target_prefixes = WEALTH_ORPHAN_PREFIXES + ANALYTICAL_ORPHAN_PREFIXES

        # Purge selettivo dei risultati analitici e modelli in memoria
        for tk in target_transient:
            if tk in st_state:
                st_state.pop(tk, None)
                purged_keys.append(tk)

        for k in list(st_state.keys()):
            if k in SYSTEM_PERSISTENT_KEYS or k in DOMAIN_ROUTING_KEYS:
                continue
            # Verifica prefissi orfani o widget salted con vecchio ID profilo
            if (
                k in target_exact
                or any(k.startswith(pfx) for pfx in target_prefixes)
                or (last_pid is not None and f"__pr_{last_pid}" in k)
            ):
                st_state.pop(k, None)
                purged_keys.append(k)

    # CASO 3: NAVIGAZIONE TRA PAGINE
    elif is_page_transition:
        transition_type = "page_navigation"
        logger.debug(
            "Executing Page Navigation Teardown [from: '%s' -> to: '%s']",
            last_norm,
            norm_target,
        )

        # Identifica i prefissi proprietari della pagina precedente
        prev_prefixes = PAGE_WIDGET_PREFIXES.get(last_norm, ())
        target_prefixes = PAGE_WIDGET_PREFIXES.get(norm_target, ())

        for k in list(st_state.keys()):
            if k in SYSTEM_PERSISTENT_KEYS or k in DOMAIN_ROUTING_KEYS:
                continue
            # Purge se appartiene esplicitamente ai prefissi della pagina precedente
            if any(k.startswith(pfx) for pfx in prev_prefixes):
                # Preserva se per caso appartiene anche alla nuova pagina
                if not any(k.startswith(pfx) for pfx in target_prefixes):
                    st_state.pop(k, None)
                    purged_keys.append(k)
            # Purge se contiene il salt esplicito della pagina precedente
            elif f"__pg_{last_norm}" in k:
                st_state.pop(k, None)
                purged_keys.append(k)
            # Purge di input di ricerca temporanei cross-page
            elif k in (
                "inp_port_table_search",
                "search_div_table",
                "radio_dcf_search",
                "radio_p_search",
                "hist_port_filter",
                "wealth_hist_port_filter",
            ):
                st_state.pop(k, None)
                purged_keys.append(k)

    # Aggiornamento atomico dei marker di lifecycle nello stato di sessione con i valori post-teardown
    curr_pid_final = st_state.get("wealth_active_portfolio_id")
    if curr_pid_final is None:
        curr_pid_final = st_state.get("portfolio_id")
    curr_db_final = st_state.get("db_name")

    st_state["_ui_lifecycle_active_page"] = target_page
    st_state["_ui_lifecycle_active_profile"] = curr_pid_final
    st_state["_ui_lifecycle_active_db"] = curr_db_final
    st_state["_ui_lifecycle_render_seq"] = int(st_state.get("_ui_lifecycle_render_seq", 0)) + 1

    return {
        "status": "success",
        "transition_type": transition_type,
        "purged_keys_count": len(purged_keys),
        "purged_keys": purged_keys,
        "active_page": norm_target,
        "active_profile": curr_pid_final,
        "active_db": curr_db_final,
    }


def get_ui_lifecycle_telemetry() -> Dict[str, Any]:
    """Restituisce le metriche correnti del ciclo di vita della UI per diagnostica e audit."""
    st_state = _get_session_state() or {}
    return {
        "active_page": st_state.get("_ui_lifecycle_active_page"),
        "active_profile": st_state.get("_ui_lifecycle_active_profile"),
        "active_db": st_state.get("_ui_lifecycle_active_db"),
        "salt_version": st_state.get("_ui_lifecycle_salt_version", 1),
        "render_seq": st_state.get("_ui_lifecycle_render_seq", 0),
        "total_session_keys": len(st_state),
    }
