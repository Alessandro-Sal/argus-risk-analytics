"""
ARGUS — Risk Analytics Platform
Core Module: Unified & Isolated Workspace Context Engine
Thread-safe, multi-tenant ready, with deterministic lifecycle and zero cross-contamination.
"""

import glob
import json
import logging
import os
import pickle
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

try:
    import streamlit as st
except ImportError:
    st = None

logger = logging.getLogger("argus.workspace")


def _safe_log_audit(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
) -> None:
    """Helper difensivo per registrare audit log senza fallire in ambienti di test headless."""
    try:
        from core.diagnostics import log_audit_event

        log_audit_event(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            status=status,
            user_id="workspace_engine",
        )
    except Exception as ex:
        logger.debug("Silenced audit log error: %s", ex)


# ── STORAGE PATHS & CONSTANTS ────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_CACHE_DIR = os.path.join(BASE_DIR, "data", "cache", "sessions")
LEGACY_CACHE_PKL = os.path.join(BASE_DIR, "data", "cache", "active_session_full.pkl")
LEGACY_CACHE_JSON = os.path.join(BASE_DIR, "data", "cache", "last_session_snapshot.json")

# Prefissi o chiavi di widget di pagina da bonificare al cambio portafoglio/analisi Risk
RISK_ORPHAN_PREFIXES = (
    "ta_",
    "ta_target_",
    "tech_",
    "time_",
    "screener_",
    "stress_",
    "quant_",
    "bquant_",
    "frontier_",
    "black_litterman_",
    "opt_weights_",
    "subtab_",
    "target_subtab_",
    "mc_adv_",
    "rl_",
    "wfo_",
    "barra_",
    "dcc_",
    "sabr_",
    "heston_",
    "bl_",
    "cached_screener_",
    "triagent_",
    "filter_gy_",
    "filter_div_",
    "filter_scorecard_",
    "sel_lot_",
    "selectbox_dcf_",
    "selectbox_p_",
    "search_bl_",
    "search_kelly_",
    "filter_cov_",
    "fi_preset_",
    "ff_model_",
)

RISK_ORPHAN_EXACT_KEYS = {
    "ta_target_ticker",
    "tech_active_subtab",
    "tech_active_subtab_selectbox",
    "time_active_tab",
    "time_active_tab_selectbox",
    "screener_segmented_subtab",
    "screener_segmented_subtab_selectbox",
    "active_opt_weights",
    "quant_frontier_selected_point",
    "black_litterman_views",
    "stress_scenarios_selected",
    "custom_stress_multiplier",
    "bquant_active_cell",
    "sandbox_preset_name",
    "triagent_last_results",
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
    "sel_tape_ticker_page2",
    "inp_port_table_search",
    "filter_main_pos_ac",
    "search_div_table",
    "radio_dcf_search",
    "radio_p_search",
    "select_history_run",
    "hist_port_filter",
    "bl_view_asset",
    "sel_lot_sizing_ticker",
    "selectbox_dcf_portfolio",
    "selectbox_p_portfolio",
}

# Alias retrocompatibili
ANALYTICAL_ORPHAN_PREFIXES = RISK_ORPHAN_PREFIXES
ANALYTICAL_EXACT_KEYS = RISK_ORPHAN_EXACT_KEYS

# Prefissi e chiavi di widget/filtri del modulo Wealth da bonificare al cambio profilo
WEALTH_ORPHAN_PREFIXES = (
    "cf_",
    "master_pbs_",
    "pension_",
    "fiscal_",
    "estate_",
    "fire_",
    "wealth_nw_",
    "wealth_cf_",
    "wealth_tax_",
    "wealth_estate_",
    "wealth_copilot_",
    "wealth_fire_",
    "wealth_re_",
    "alloc_",
    "pipe_csv_cf_",
    "pipe_up_accs",
    "pipe_gsheet_",
    "sel_mod_acc_",
)

WEALTH_ORPHAN_EXACT_KEYS = {
    "wealth_active_snapshot",
    "triagent_last_results",
    "cf_account_selector_widget",
    "cf_year_selector_widget",
    "cf_month_selector_widget",
    "cf_upload_target_acc",
    "master_pbs_year_selector",
    "sankey_flow_dropdown_picker",
    "env_status_filter_select",
    "alloc_dim_selector_seg",
    "alloc_chart_view_mode_seg",
    "toggle_pbs_preview_p13",
    "toggle_ts_preview_p13",
    "wealth_temporal_view_style",
    "wealth_select_snapshot_recall",
    "wealth_hist_port_filter",
    "nw_stress_scen_picker",
    "sp_mat_slider",
}

WEALTH_ROUTING_KEYS = {
    "wealth_active_portfolio_id",
    "wealth_active_profile_name",
    "sb_wealth_profile_selector",
    "wealth_profile_selector_widget",
    "nw_profile_selector_widget",
    "cf_profile_selector_widget",
    "pension_profile_selector_widget",
    "fiscal_profile_selector_widget",
    "estate_profile_selector_widget",
    "ai_profile_selector_widget",
}


def get_canonical_db_fingerprint(engine: Any) -> str:
    """
    Genera un fingerprint deterministico e canonico per l'engine database attivo.
    Risolve path assoluti canonici per SQLite, connection URI univoci per MySQL/PostgreSQL,
    e gestisce mock/test engines senza collisioni di cache.
    """
    if engine is None:
        return "none:unbound"
    try:
        url = getattr(engine, "url", None)
        if url is None:
            return f"mock:{id(engine)}"

        driver = getattr(url, "drivername", "unknown") or "unknown"

        # Gestione SQLite (Normalizzazione path canonico per evitare discrepanze relative/assolute)
        if "sqlite" in driver:
            db_path = getattr(url, "database", None)
            if not db_path or db_path == ":memory:":
                return f"sqlite:memory:{id(engine)}"
            try:
                norm_path = os.path.realpath(os.path.abspath(db_path)).replace("\\", "/")
            except Exception:
                norm_path = str(db_path).replace("\\", "/")
            return f"sqlite://{norm_path}"

        # Gestione MySQL / PostgreSQL / RDBMS di rete
        user = getattr(url, "username", "anon") or "anon"
        host = getattr(url, "host", "localhost") or "localhost"
        port = getattr(url, "port", 3306) or 3306
        dbname = getattr(url, "database", "default") or "default"
        return f"{driver}://{user}@{host}:{port}/{dbname}"
    except Exception:
        return f"fallback:{id(engine)}"


# ── DOMAIN SUB-CONTEXT DATACLASSES ────────────────────────────


@dataclass
class RiskSubContext:
    """Modello fortemente tipizzato per il dominio Risk & Portfolio Analytics."""

    portfolio_id: Optional[int] = None
    portfolio_name: str = "Nessun Portafoglio"
    run_id: str = "IDLE"
    base_currency: str = "EUR"
    benchmark: str = "SPY"
    risk_free_rate: float = 0.03
    pipeline_done: bool = False
    results: Optional[Dict[str, Any]] = None
    fetch_report: Optional[Dict[str, Any]] = None
    is_live_active: bool = False
    is_sandbox: bool = False
    last_calculated_at: Optional[datetime] = None

    def get_total_equity(self) -> float:
        """Calcola deterministicamente il valore aggregato del portafoglio in memoria."""
        if self.results and isinstance(self.results, dict):
            pos = self.results.get("positions")
            if isinstance(pos, pd.DataFrame) and not pos.empty and "current_value" in pos.columns:
                try:
                    return float(pos["current_value"].sum())
                except Exception:
                    pass
            metrics = self.results.get("metrics", {})
            if isinstance(metrics, dict) and "portfolio_value" in metrics:
                try:
                    return float(metrics["portfolio_value"])
                except Exception:
                    pass
            if "portfolio_value" in self.results:
                try:
                    return float(self.results["portfolio_value"])
                except Exception:
                    pass
        return 0.0


@dataclass
class WealthSubContext:
    """Modello fortemente tipizzato per il dominio Wealth Management."""

    profile_id: Optional[int] = None
    profile_name: str = "Nessun Profilo Selezionato"
    profile_map: Dict[int, str] = field(default_factory=dict)
    linked_risk_ids: List[int] = field(default_factory=list)
    net_worth_cached: Optional[Any] = None
    include_live_risk: bool = True
    last_consolidated_at: Optional[datetime] = None


@dataclass
class UIViewState:
    """Isolamento dello stato di navigazione, filtri e tab per pagina."""

    page_subtabs: Dict[str, str] = field(default_factory=dict)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    target_tickers: Dict[str, str] = field(default_factory=dict)
    selected_scenarios: List[str] = field(default_factory=list)

    def clear_page(self, page_id: str):
        self.page_subtabs.pop(page_id, None)
        self.target_tickers.pop(page_id, None)
        self.active_filters = {k: v for k, v in self.active_filters.items() if not k.startswith(f"{page_id}_")}

    def clear_all(self):
        self.page_subtabs.clear()
        self.active_filters.clear()
        self.target_tickers.clear()
        self.selected_scenarios.clear()


# ── UNIFIED WORKSPACE CONTEXT CLASS ───────────────────────────


class WorkspaceContext:
    """
    Contesto unificato e isolato per sessione utente / tab browser.
    Elimina la dipendenza da oltre 250 chiavi globali non coordinate in st.session_state
    fornendo una facciata bidirezionale trasparente e retrocompatibile al 100%.
    """

    _LOCK = threading.RLock()
    NAMESPACE_KEY = "_ARGUS_WORKSPACE_CONTEXT_"
    SESSION_UUID_KEY = "_ARGUS_SESSION_UUID_"
    _FALLBACK_STORES: Dict[str, "WorkspaceContext"] = {}

    def __init__(self, session_id: Optional[str] = None):
        self.session_id: str = session_id or str(uuid.uuid4())
        self.user_id: str = "default_user"
        self.workspace_id: str = "default"
        self.risk: RiskSubContext = RiskSubContext()
        self.wealth: WealthSubContext = WealthSubContext()
        self.ui: UIViewState = UIViewState()
        self.is_dirty: bool = False
        self.created_at: datetime = datetime.now()
        self.last_synced_at: Optional[datetime] = None
        self.version: int = 1

    @classmethod
    def _get_st_session_state(cls) -> Optional[Any]:
        """Recupera in modo sicuro st.session_state se disponibile nel contesto d'esecuzione."""
        try:
            import streamlit as st

            if hasattr(st, "session_state"):
                return st.session_state
        except Exception:
            pass
        return None

    @classmethod
    def get_current(cls, session_id: Optional[str] = None) -> "WorkspaceContext":
        """
        Recupera o istanzia il WorkspaceContext corrente.
        Se Streamlit è attivo, memorizza e sincronizza in st.session_state.
        In test headless o script CLI, ricorre a uno store thread-safe isolato.
        """
        st_state = cls._get_st_session_state()
        with cls._LOCK:
            if st_state is not None:
                # Modalità Streamlit attiva
                if cls.NAMESPACE_KEY in st_state:
                    ctx: WorkspaceContext = st_state[cls.NAMESPACE_KEY]
                    ctx.sync_from_legacy_session_state()
                    return ctx

                # Inizializzazione UUID di sessione
                sid = session_id or st_state.get(cls.SESSION_UUID_KEY)
                if not sid:
                    sid = str(uuid.uuid4())
                    st_state[cls.SESSION_UUID_KEY] = sid

                ctx = cls(session_id=sid)
                ctx.sync_from_legacy_session_state()
                st_state[cls.NAMESPACE_KEY] = ctx
                return ctx
            else:
                # Modalità Headless / Pytest fallback
                sid = session_id or "default_headless_session"
                if sid not in cls._FALLBACK_STORES:
                    cls._FALLBACK_STORES[sid] = cls(session_id=sid)
                return cls._FALLBACK_STORES[sid]

    # ── BIDIRECTIONAL SYNC WITH LEGACY ST.SESSION_STATE ───────

    def sync_from_legacy_session_state(self):
        """Assorbe mutazioni apportate direttamente alle chiavi legacy di st.session_state."""
        st_state = self._get_st_session_state()
        if st_state is None:
            return

        with self._LOCK:
            # Sincronizzazione Dominio Risk
            if "results" in st_state and st_state["results"] is not None:
                self.risk.results = st_state["results"]
                self.risk.is_live_active = True
                if isinstance(st_state["results"], dict):
                    pos = st_state["results"].get("positions")
                    if pos is not None and not (hasattr(pos, "empty") and pos.empty):
                        st_state.pop("session_cleared", None)
                        st_state["session_cleared"] = False
            elif "results" in st_state and st_state["results"] is None and not self.risk.results:
                self.risk.results = None
                self.risk.is_live_active = False

            if "portfolio_id" in st_state:
                self.risk.portfolio_id = st_state.get("portfolio_id")
            elif "active_portfolio_id" in st_state and st_state["active_portfolio_id"]:
                self.risk.portfolio_id = st_state.get("active_portfolio_id")

            if "active_portfolio_data" in st_state and st_state["active_portfolio_data"] is not None and not self.risk.results:
                self.risk.results = st_state["active_portfolio_data"]
                self.risk.is_live_active = True

            if "portfolio_name" in st_state:
                self.risk.portfolio_name = st_state.get("portfolio_name", "Nessun Portafoglio")
            if "run_id" in st_state:
                self.risk.run_id = st_state.get("run_id", "IDLE")
            if "base_currency" in st_state:
                self.risk.base_currency = st_state.get("base_currency", "EUR")
            if "benchmark" in st_state:
                self.risk.benchmark = st_state.get("benchmark", "SPY")
            if "active_rf_rate" in st_state and st_state["active_rf_rate"] is not None:
                try:
                    self.risk.risk_free_rate = float(st_state["active_rf_rate"])
                except Exception:
                    pass
            if "pipeline_done" in st_state:
                self.risk.pipeline_done = bool(st_state.get("pipeline_done", False))
            if "fetch_report" in st_state:
                self.risk.fetch_report = st_state.get("fetch_report")

            # Sincronizzazione Dominio Wealth
            if "wealth_active_portfolio_id" in st_state:
                self.wealth.profile_id = st_state.get("wealth_active_portfolio_id")
            else:
                self.wealth.profile_id = None
            if "wealth_active_profile_name" in st_state:
                self.wealth.profile_name = st_state.get("wealth_active_profile_name", "Nessun Profilo Selezionato")
            else:
                self.wealth.profile_name = "Nessun Profilo Selezionato"

    def sync_to_legacy_session_state(self):
        """Propaga lo stato tipizzato alle chiavi legacy di st.session_state per garantire retrocompatibilità."""
        st_state = self._get_st_session_state()
        if st_state is None:
            return

        with self._LOCK:
            st_state["results"] = self.risk.results
            st_state["portfolio_id"] = self.risk.portfolio_id
            st_state["active_portfolio_id"] = str(self.risk.portfolio_id) if self.risk.portfolio_id is not None else None
            st_state["active_portfolio_data"] = self.risk.results
            st_state["portfolio_name"] = self.risk.portfolio_name
            st_state["run_id"] = self.risk.run_id
            st_state["base_currency"] = self.risk.base_currency
            st_state["benchmark"] = self.risk.benchmark
            st_state["active_rf_rate"] = self.risk.risk_free_rate
            st_state["pipeline_done"] = self.risk.pipeline_done
            st_state["fetch_report"] = self.risk.fetch_report

            if self.risk.results is not None and isinstance(self.risk.results, dict):
                pos = self.risk.results.get("positions")
                if pos is not None and not (hasattr(pos, "empty") and pos.empty):
                    st_state.pop("session_cleared", None)
                    st_state["session_cleared"] = False

            st_state["wealth_active_portfolio_id"] = self.wealth.profile_id
            st_state["wealth_active_profile_name"] = self.wealth.profile_name

    # ── DOMAIN FLUSHING & GHOST STATE ELIMINATION ──────────────

    def flush_risk_domain(self, preserve_db_creds: bool = True):
        """
        Azzera deterministicamente lo stato analitico del modulo Risk.
        Elimina tutte le chiavi orfane di widget analitici (ta_*, tech_*, time_*, ecc.)
        scongiurando eccezioni e contaminazione dati al cambio o reset del portafoglio.
        """
        with self._LOCK:
            self.risk = RiskSubContext()
            self.ui.clear_all()

            st_state = self._get_st_session_state()
            if st_state is not None:
                # 1. Rimozione delle chiavi di stato primarie
                for key in [
                    "results",
                    "portfolio_id",
                    "active_portfolio_id",
                    "active_portfolio_data",
                    "portfolio_name",
                    "run_id",
                    "pipeline_done",
                    "fetch_report",
                    "sandbox_preset_name",
                    "df_positions",
                    "df_raw_injected",
                    "active_archetype_code",
                    "active_archetype_name",
                    "active_archetype_tx_count",
                    "active_archetype_db_ids",
                    "archetype_just_injected",
                    "keep_archetype_expander_open",
                    "selected_portfolio",
                    "current_portfolio_id",
                    "selected_bitemp_port",
                    "last_rebalance_result",
                    "active_quant_tab",
                    "is_sandbox",
                    "is_demo",
                ]:
                    if key in st_state:
                        del st_state[key]
                st_state["session_cleared"] = True

                # 2. Scansione ed eliminazione deterministica dei widget analitici orfani
                keys_to_purge: Set[str] = set()
                for key in list(st_state.keys()):
                    if key in ANALYTICAL_EXACT_KEYS:
                        keys_to_purge.add(key)
                    elif any(key.startswith(pfx) for pfx in ANALYTICAL_ORPHAN_PREFIXES):
                        keys_to_purge.add(key)

                for key in keys_to_purge:
                    try:
                        del st_state[key]
                    except Exception:
                        pass

            self.version += 1
            self.is_dirty = True
            self.clear_persisted_cache()

    @classmethod
    def sanitize_wealth_profile_state(cls, preserve_routing_keys: bool = True) -> None:
        """
        Esegue la bonifica mirata di filtri, conti, anni fiscali e selezioni orfane al cambio profilo Wealth.
        Scongiura la permanenza di ID conto, anni o selezioni del profilo precedente.
        """
        try:
            import streamlit as st
        except ImportError:
            return
        st_state = getattr(st, "session_state", None)
        if st_state is None:
            return

        with cls._LOCK:
            keys_to_purge: Set[str] = set()
            for key in list(st_state.keys()):
                if preserve_routing_keys and key in WEALTH_ROUTING_KEYS:
                    continue
                if not preserve_routing_keys and key in WEALTH_ROUTING_KEYS:
                    keys_to_purge.add(key)
                elif key in WEALTH_ORPHAN_EXACT_KEYS:
                    keys_to_purge.add(key)
                elif any(key.startswith(pfx) for pfx in WEALTH_ORPHAN_PREFIXES):
                    if preserve_routing_keys and key.endswith("_profile_selector_widget"):
                        continue
                    keys_to_purge.add(key)

            for key in keys_to_purge:
                try:
                    del st_state[key]
                except Exception:
                    st_state.pop(key, None)

            logger.debug(
                "Sanitized wealth profile state (purged %d orphan keys, preserve_routing=%s)",
                len(keys_to_purge),
                preserve_routing_keys,
            )

            # Invalida cache dati di processo
            try:
                st.cache_data.clear()
            except Exception:
                pass

    @classmethod
    def sanitize_risk_portfolio_state(cls, preserve_db_creds: bool = True) -> None:
        """
        Esegue la bonifica completa di modelli quantitativi, ticker, array di pesi e widget analitici orfani
        prima di ricalcolare o ricaricare un'analisi di portafoglio Risk.
        """
        try:
            import streamlit as st
        except ImportError:
            return
        st_state = getattr(st, "session_state", None)
        if st_state is None:
            return

        with cls._LOCK:
            keys_to_purge: Set[str] = set()
            for key in list(st_state.keys()):
                if key in RISK_ORPHAN_EXACT_KEYS:
                    keys_to_purge.add(key)
                elif any(key.startswith(pfx) for pfx in RISK_ORPHAN_PREFIXES):
                    keys_to_purge.add(key)

            for key in keys_to_purge:
                try:
                    del st_state[key]
                except Exception:
                    st_state.pop(key, None)

            logger.debug(
                "Sanitized risk portfolio state (purged %d orphan keys, preserve_db_creds=%s)",
                len(keys_to_purge),
                preserve_db_creds,
            )

            try:
                ws = cls.get_current()
                ws.flush_risk_domain(preserve_db_creds=preserve_db_creds)
            except Exception:
                pass

    def flush_wealth_domain(self):
        """Azzera deterministicamente lo stato del modulo Wealth e tutti i relativi widget."""
        with self._LOCK:
            self.wealth = WealthSubContext()
            self.sanitize_wealth_profile_state(preserve_routing_keys=False)
            st_state = self._get_st_session_state()
            if st_state is not None:
                for key in WEALTH_ROUTING_KEYS:
                    st_state.pop(key, None)
                st_state["wealth_active_portfolio_id"] = None
                st_state["wealth_active_profile_name"] = None
            self.version += 1
            self.is_dirty = True

    @classmethod
    def switch_wealth_profile(
        cls, new_pid: Optional[int], profile_name: Optional[str] = None, force: bool = False
    ) -> None:
        """
        Commuta in sicurezza il profilo patrimoniale attivo, sincronizzando tutti i widget
        di selezione e resettando lo snapshot storico per evitare data leakage tra profili.
        """
        try:
            import streamlit as st
        except ImportError:
            return

        st_state = getattr(st, "session_state", None)
        if st_state is None:
            return

        with cls._LOCK:
            curr_pid = st_state.get("wealth_active_portfolio_id")
            old_name = st_state.get("wealth_active_profile_name")
            if not force and curr_pid == new_pid and new_pid is not None:
                if profile_name and st_state.get("wealth_active_profile_name") != profile_name:
                    st_state["wealth_active_profile_name"] = profile_name
                logger.debug("Idempotent profile switch skipped for PID %s", new_pid)
                return

            logger.info(
                "Initiating Wealth profile switch: PID %s ('%s') -> PID %s ('%s') [force=%s]",
                curr_pid,
                old_name,
                new_pid,
                profile_name or "N/A",
                force,
            )

            # 1. Sanitizzazione atomica dei filtri e selezioni orfane del profilo precedente
            cls.sanitize_wealth_profile_state(preserve_routing_keys=True)
            try:
                from core.ui_lifecycle import teardown_view_state

                teardown_view_state(reason="wealth_profile_switch")
            except Exception:
                pass

            # 2. Sincronizzazione atomica dello stato attivo primario (single source of truth)
            st_state["wealth_active_portfolio_id"] = new_pid

            # 3. Sincronizzazione difensiva di tutti i selettori di pagina e sidebar:
            # Se un widget è già stato istanziato nel run corrente (es. la sidebar viene sempre renderizzata
            # prima del corpo pagina o dei modal/picker), Streamlit vieta l'assegnazione diretta
            # sollevando StreamlitAPIException. Il valore viene comunque recepito al successivo ciclo
            # di esecuzione (st.rerun()) tramite wealth_active_portfolio_id.
            for wk in WEALTH_ROUTING_KEYS:
                if wk in ("wealth_active_portfolio_id", "wealth_active_profile_name"):
                    continue
                try:
                    st_state[wk] = new_pid
                except Exception:
                    pass

            # 4. Reset dello snapshot storico e dell'advisor copilot per impedire bleed tra profili
            st_state.pop("wealth_active_snapshot", None)
            st_state.pop("triagent_last_results", None)

            # 5. Invalidazione atomica della cache di processo Streamlit per prevenire calcoli e PDF stantii cross-profilo
            try:
                st.cache_data.clear()
            except Exception:
                pass

            if profile_name:
                st_state["wealth_active_profile_name"] = profile_name
            elif new_pid is None:
                st_state.pop("wealth_active_profile_name", None)

            try:
                ws = cls.get_current()
                ws.wealth.profile_id = new_pid
                if profile_name:
                    ws.wealth.profile_name = profile_name
                ws.wealth.net_worth_cached = None
                ws.version += 1
            except Exception:
                pass

            logger.info(
                "Wealth profile switch completed: active PID is now %s ('%s')",
                new_pid,
                profile_name or "N/A",
            )
            _safe_log_audit(
                action="PROFILE_SWITCH",
                entity_type="wealth_profile",
                entity_id=str(new_pid) if new_pid is not None else "NONE",
                details={
                    "old_profile_id": curr_pid,
                    "old_profile_name": old_name,
                    "new_profile_id": new_pid,
                    "new_profile_name": profile_name,
                    "force": force,
                },
            )

    @classmethod
    def switch_profile_context(
        cls,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        target_portfolio_id: Optional[Union[str, int]] = None,
        is_demo: bool = False,
    ) -> "WorkspaceContext":
        """
        Commuta atomicamente il contesto tenant/profilo (SSOT).
        - Invalida tutte le chiavi orfane di portafoglio, analisi e demo sia lato Risk che Wealth.
        - Purga la cache L1/L2 in cache_shield.py e le viste singleton in duckdb_engine.py.
        - Invalida la cache di processo Streamlit (st.cache_data).
        - Riconfigura WorkspaceContext con i nuovi metadati tenant isolati.
        """
        with cls._LOCK:
            ctx = cls.get_current()
            ctx.flush_risk_domain()
            ctx.flush_wealth_domain()

            # Pulisci cache di calcolo C++ e OLAP
            try:
                from core.cache_shield import clear_cache

                clear_cache()
            except Exception:
                pass

            try:
                from core.duckdb_engine import reset_shared_duckdb_views

                reset_shared_duckdb_views()
            except Exception:
                pass

            try:
                import streamlit as st

                if hasattr(st, "cache_data"):
                    st.cache_data.clear()
            except Exception:
                pass

            # Riassegna identificativi tenant
            if user_id is not None:
                ctx.user_id = str(user_id)
            if workspace_id is not None:
                ctx.workspace_id = str(workspace_id)
            ctx.risk.is_sandbox = is_demo
            if target_portfolio_id is not None:
                ctx.risk.portfolio_id = target_portfolio_id

            ctx.is_dirty = True
            ctx.version += 1
            ctx.sync_to_legacy_session_state()

            _safe_log_audit(
                action="PROFILE_CONTEXT_SWITCH",
                entity_type="workspace_context",
                entity_id=str(target_portfolio_id) if target_portfolio_id is not None else "NONE",
                details={
                    "user_id": ctx.user_id,
                    "workspace_id": ctx.workspace_id,
                    "target_portfolio_id": target_portfolio_id,
                    "is_demo": is_demo,
                },
            )
            return ctx

    @classmethod
    def execute_database_switch(cls, new_db: str, offline_mode: Optional[bool] = None) -> None:
        """
        Esegue il teardown atomico dello stato applicativo, della cache e dei connection pool
        quando l'utente seleziona un nuovo schema database o commuta la modalità offline/online.
        """
        try:
            import streamlit as st
        except ImportError:
            return

        st_state = getattr(st, "session_state", None)
        if st_state is None:
            return

        with cls._LOCK:
            old_db = st_state.get("db_name")
            old_offline = st_state.get("offline_mode")
            logger.info(
                "Initiating Database switch: '%s' (offline=%s) -> '%s' (offline=%s)",
                old_db,
                old_offline,
                new_db,
                offline_mode,
            )

            # 1. Dispose del Connection Pool attivo per rilasciare socket MySQL e lock SQLite
            disposed_fps: List[str] = []
            try:
                from core.fetcher import dispose_engine

                eng1 = st_state.get("engine")
                eng2 = st_state.get("db_engine")
                if eng1 is not None:
                    try:
                        disposed_fps.append(get_canonical_db_fingerprint(eng1))
                    except Exception:
                        pass
                    dispose_engine(eng1)
                if eng2 is not None and eng2 is not eng1:
                    try:
                        disposed_fps.append(get_canonical_db_fingerprint(eng2))
                    except Exception:
                        pass
                    dispose_engine(eng2)
            except Exception:
                pass
            st_state["engine"] = None
            st_state["db_engine"] = None

            # 2. Svuotamento completo delle cache Streamlit (process-level)
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass

            # 3. Svuotamento della cache su disco
            try:
                from core.cache_shield import clear_cache as clear_disk_cache

                clear_disk_cache()
            except Exception:
                pass

            # 4. Sanitizzazione profonda di tutti i domini
            cls.sanitize_risk_portfolio_state(preserve_db_creds=True)
            cls.sanitize_wealth_profile_state(preserve_routing_keys=False)
            try:
                from core.ui_lifecycle import teardown_view_state

                teardown_view_state(force=True, reason="database_switch")
            except Exception:
                pass

            # 5. Flush dei domini in WorkspaceContext
            try:
                ws = cls.get_current()
                ws.flush_wealth_domain()
                ws.flush_risk_domain()
            except Exception:
                pass

            # 6. Bonifica deterministica delle chiavi di sessione
            keys_to_purge = [
                "wealth_active_portfolio_id",
                "wealth_active_profile_name",
                "wealth_active_snapshot",
                "portfolio_id",
                "portfolio_name",
                "results",
                "pipeline_done",
                "last_pipeline_hash",
                "fetch_report",
                "sandbox_preset_name",
            ] + list(WEALTH_ROUTING_KEYS)
            for k in keys_to_purge:
                st_state.pop(k, None)

            st_state["wealth_active_portfolio_id"] = None
            st_state["wealth_active_profile_name"] = None

            # 7. Assegnazione atomica dei nuovi puntatori
            if new_db:
                st_state["db_name"] = new_db
                st_state["wealth_db_name"] = new_db
                st_state["risk_db_name"] = new_db

            if offline_mode is not None:
                st_state["offline_mode"] = bool(offline_mode)

            logger.info(
                "Database switch completed successfully: active DB is now '%s' (offline=%s, pools_disposed=%d)",
                new_db,
                st_state.get("offline_mode"),
                len(disposed_fps),
            )
            _safe_log_audit(
                action="DATABASE_SWITCH",
                entity_type="database",
                entity_id=new_db,
                details={
                    "old_db": old_db,
                    "new_db": new_db,
                    "old_offline": old_offline,
                    "new_offline": st_state.get("offline_mode"),
                    "disposed_pools": disposed_fps,
                },
            )

    # ── REACTIVE TOTAL WEALTH CONSOLIDATION BRIDGE ─────────────

    def get_consolidated_equity_for_wealth(self, engine, linked_risk_ids: Optional[List[int]] = None) -> float:
        """
        Riconciliazione reattiva: integra in tempo reale il valore del portafoglio Risk
        attivo in memoria senza costringere a salvare prima uno snapshot su database.
        Se vi sono altri portafogli Risk collegati non in memoria, ne aggrega lo snapshot DB.
        """
        with self._LOCK:
            self.sync_from_legacy_session_state()
            from core.wealth.wealth_db import get_available_risk_portfolios, get_linked_risk_portfolios

            w_pid = self.wealth.profile_id
            if w_pid is None:
                return 0.0
            active_links = linked_risk_ids if linked_risk_ids is not None else get_linked_risk_portfolios(engine, w_pid)
            if not active_links:
                return 0.0

            live_pid = self.risk.portfolio_id
            live_equity = self.risk.get_total_equity() if (self.risk.is_live_active and self.risk.results) else 0.0

            # Caso 1: il portafoglio in memoria è l'unico collegato o fa parte dei collegati
            total_consolidated = 0.0
            db_pids_to_query = list(active_links)

            if live_pid is not None and live_pid in active_links and live_equity > 0:
                # Utilizziamo il controvalore live per questo portfolio_id
                total_consolidated += live_equity
                db_pids_to_query = [pid for pid in active_links if pid != live_pid]

            # Caso 2: Interroga gli snapshot su DB per gli altri portafogli collegati
            if db_pids_to_query:
                try:
                    df_all = get_available_risk_portfolios(engine)
                    if not df_all.empty and "portfolio_id" in df_all.columns:
                        df_sub = df_all[df_all["portfolio_id"].isin(db_pids_to_query)]
                        if not df_sub.empty and "latest_value" in df_sub.columns:
                            total_consolidated += float(df_sub["latest_value"].sum())
                except Exception:
                    pass

            return round(total_consolidated, 2)

    # ── MULTI-SESSION PERSISTENCE & CACHE ISOLATION ────────────

    def get_session_cache_path(self) -> str:
        """Restituisce il percorso del file di cache binaria isolato per la sessione corrente."""
        os.makedirs(SESSIONS_CACHE_DIR, exist_ok=True)
        safe_sid = "".join(c for c in self.session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(SESSIONS_CACHE_DIR, f"session_{safe_sid}.pkl")

    def save_session_cache(self) -> bool:
        """Salva lo stato corrente sia nella cache isolata per sessione sia nel fallback legacy."""
        with self._LOCK:
            if not self.risk.results:
                self.sync_from_legacy_session_state()
            if not self.risk.results or not isinstance(self.risk.results, dict):
                return False

            st_state = self._get_st_session_state()
            current_db_name = None
            current_engine = None
            if st_state is not None:
                current_db_name = (
                    st_state.get("db_name")
                    or st_state.get("wealth_db_name")
                    or st_state.get("risk_db_name")
                )
                current_engine = st_state.get("engine") or st_state.get("db_engine")

            db_meta = {
                "db_name": current_db_name,
                "db_fingerprint": get_canonical_db_fingerprint(current_engine),
            }

            bundle = {
                "session_id": self.session_id,
                "version": self.version,
                "saved_at": datetime.now().isoformat(),
                "database": db_meta,
                "risk": {
                    "results": self.risk.results,
                    "portfolio_id": self.risk.portfolio_id,
                    "portfolio_name": self.risk.portfolio_name,
                    "run_id": self.risk.run_id,
                    "base_currency": self.risk.base_currency,
                    "benchmark": self.risk.benchmark,
                    "risk_free_rate": self.risk.risk_free_rate,
                    "pipeline_done": self.risk.pipeline_done,
                },
                "wealth": {
                    "profile_id": self.wealth.profile_id,
                    "profile_name": self.wealth.profile_name,
                    "linked_risk_ids": self.wealth.linked_risk_ids,
                },
                "ui": {
                    "page_subtabs": self.ui.page_subtabs,
                    "active_filters": self.ui.active_filters,
                    "target_tickers": self.ui.target_tickers,
                },
            }

            try:
                # 1. Salva cache isolata per sessione
                session_path = self.get_session_cache_path()
                with open(session_path, "wb") as f:
                    pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

                # 2. Salva fallback legacy per garantire compatibilità con finestre esterne / desktop
                os.makedirs(os.path.dirname(LEGACY_CACHE_PKL), exist_ok=True)
                legacy_bundle = {
                    "results": self.risk.results,
                    "portfolio_name": self.risk.portfolio_name,
                    "run_id": self.risk.run_id,
                    "base_currency": self.risk.base_currency,
                    "benchmark": self.risk.benchmark,
                    "saved_at": datetime.now().isoformat(),
                    "database": db_meta,
                }
                with open(LEGACY_CACHE_PKL, "wb") as lf:
                    pickle.dump(legacy_bundle, lf, protocol=pickle.HIGHEST_PROTOCOL)

                # 3. Snapshot JSON sintetico
                try:
                    pos = self.risk.results.get("positions", pd.DataFrame())
                    pos_rec = pos.to_dict(orient="records") if isinstance(pos, pd.DataFrame) else []
                    json_meta = {
                        "session_id": self.session_id,
                        "saved_at": datetime.now().isoformat(),
                        "run_id": self.risk.run_id,
                        "portfolio_name": self.risk.portfolio_name,
                        "database": db_meta,
                        "metrics": self.risk.results.get("metrics", {}),
                        "positions": pos_rec,
                    }
                    with open(LEGACY_CACHE_JSON, "w", encoding="utf-8") as jf:
                        json.dump(json_meta, jf, ensure_ascii=False, default=str)
                except Exception:
                    pass

                self.last_synced_at = datetime.now()
                self.is_dirty = False
                return True
            except Exception:
                return False

    def restore_session_cache(self, force: bool = False) -> bool:
        """Ripristina lo stato dal file isolato di sessione o dal fallback legacy."""
        with self._LOCK:
            st_state = self._get_st_session_state()
            if st_state is not None and st_state.get("session_cleared", False) and not force:
                return False

            current_db_name = None
            if st_state is not None:
                current_db_name = (
                    st_state.get("db_name")
                    or st_state.get("wealth_db_name")
                    or st_state.get("risk_db_name")
                )

            # 1. Tenta prima dal file specifico della sessione
            session_path = self.get_session_cache_path()
            if os.path.exists(session_path):
                try:
                    with open(session_path, "rb") as f:
                        bundle = pickle.load(f)
                    if bundle and isinstance(bundle, dict):
                        saved_db = (
                            bundle.get("database", {}).get("db_name")
                            if isinstance(bundle.get("database"), dict)
                            else None
                        )
                        if not force and saved_db and current_db_name and saved_db != current_db_name:
                            # Protezione anti-contaminazione: rifiuta caricamento cross-database
                            return False

                        r_data = bundle.get("risk", {})
                        if r_data.get("results"):
                            self.risk.results = r_data.get("results")
                            self.risk.portfolio_id = r_data.get("portfolio_id")
                            self.risk.portfolio_name = r_data.get("portfolio_name", "Portfolio")
                            self.risk.run_id = r_data.get("run_id", "RESTORED")
                            self.risk.base_currency = r_data.get("base_currency", "EUR")
                            self.risk.benchmark = r_data.get("benchmark", "SPY")
                            self.risk.risk_free_rate = r_data.get("risk_free_rate", 0.03)
                            self.risk.pipeline_done = r_data.get("pipeline_done", True)
                            self.risk.is_live_active = True

                        w_data = bundle.get("wealth", {})
                        if w_data:
                            self.wealth.profile_id = w_data.get("profile_id", None)
                            self.wealth.profile_name = w_data.get("profile_name", "Nessun Profilo Selezionato")
                            self.wealth.linked_risk_ids = w_data.get("linked_risk_ids", [])

                        ui_data = bundle.get("ui", {})
                        if ui_data:
                            self.ui.page_subtabs = ui_data.get("page_subtabs", {})
                            self.ui.active_filters = ui_data.get("active_filters", {})
                            self.ui.target_tickers = ui_data.get("target_tickers", {})

                        self.sync_to_legacy_session_state()
                        return True
                except Exception:
                    pass

            # 2. Fallback su file legacy se il file di sessione non esiste
            if os.path.exists(LEGACY_CACHE_PKL):
                try:
                    with open(LEGACY_CACHE_PKL, "rb") as lf:
                        legacy_bundle = pickle.load(lf)
                    if legacy_bundle and isinstance(legacy_bundle, dict) and "results" in legacy_bundle:
                        saved_db = (
                            legacy_bundle.get("database", {}).get("db_name")
                            if isinstance(legacy_bundle.get("database"), dict)
                            else None
                        )
                        if not force and saved_db and current_db_name and saved_db != current_db_name:
                            return False

                        self.risk.results = legacy_bundle.get("results")
                        self.risk.portfolio_name = legacy_bundle.get("portfolio_name", "Portfolio")
                        self.risk.run_id = legacy_bundle.get("run_id", "RESTORED")
                        self.risk.base_currency = legacy_bundle.get("base_currency", "EUR")
                        self.risk.benchmark = legacy_bundle.get("benchmark", "SPY")
                        self.risk.pipeline_done = True
                        self.risk.is_live_active = True
                        self.sync_to_legacy_session_state()
                        return True
                except Exception:
                    pass

            return False

    def export_session_snapshot(self) -> Dict[str, Any]:
        """
        Esporta lo stato completo del WorkspaceContext in un dizionario JSON-serializzabile puro.
        Ideale per backup deterministico, audit contabile o condivisione multi-dispositivo senza pickle.
        """
        with self._LOCK:
            if not self.risk.results:
                self.sync_from_legacy_session_state()
            pos = (
                self.risk.results.get("positions")
                if (self.risk.results and isinstance(self.risk.results, dict))
                else None
            )
            pos_records = pos.to_dict(orient="records") if isinstance(pos, pd.DataFrame) else []

            df_tx = (
                self.risk.results.get("df_tx") if (self.risk.results and isinstance(self.risk.results, dict)) else None
            )
            tx_records = df_tx.to_dict(orient="records") if isinstance(df_tx, pd.DataFrame) else []

            metrics = (
                self.risk.results.get("metrics", {})
                if (self.risk.results and isinstance(self.risk.results, dict))
                else {}
            )

            return {
                "schema_version": "9.0.0",
                "session_id": self.session_id,
                "exported_at": datetime.now().isoformat(),
                "risk": {
                    "portfolio_id": self.risk.portfolio_id,
                    "portfolio_name": self.risk.portfolio_name,
                    "run_id": self.risk.run_id,
                    "base_currency": self.risk.base_currency,
                    "benchmark": self.risk.benchmark,
                    "risk_free_rate": self.risk.risk_free_rate,
                    "pipeline_done": self.risk.pipeline_done,
                    "is_live_active": self.risk.is_live_active,
                    "metrics": metrics,
                    "positions": pos_records,
                    "transactions": tx_records,
                },
                "wealth": {
                    "profile_id": self.wealth.profile_id,
                    "profile_name": self.wealth.profile_name,
                    "linked_risk_ids": self.wealth.linked_risk_ids,
                },
                "ui": {
                    "page_subtabs": dict(self.ui.page_subtabs),
                    "active_filters": dict(self.ui.active_filters),
                    "target_tickers": dict(self.ui.target_tickers),
                    "selected_scenarios": list(self.ui.selected_scenarios),
                },
            }

    def import_session_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """
        Ripristina lo stato completo del WorkspaceContext da uno snapshot JSON validato.
        Garantisce compatibilità e isolamento senza passare da serializzazione binaria.
        """
        if not snapshot or not isinstance(snapshot, dict):
            return False

        with self._LOCK:
            risk_data = snapshot.get("risk", {})
            self.risk.portfolio_id = risk_data.get("portfolio_id")
            self.risk.portfolio_name = risk_data.get("portfolio_name", "Portfolio")
            self.risk.run_id = risk_data.get("run_id", "RESTORED")
            self.risk.base_currency = risk_data.get("base_currency", "EUR")
            self.risk.benchmark = risk_data.get("benchmark", "SPY")
            self.risk.risk_free_rate = float(risk_data.get("risk_free_rate", 0.03))
            self.risk.pipeline_done = bool(risk_data.get("pipeline_done", True))
            self.risk.is_live_active = bool(risk_data.get("is_live_active", True))

            # Ricostruzione risultati analitici
            pos_records = risk_data.get("positions", [])
            tx_records = risk_data.get("transactions", [])
            df_pos = pd.DataFrame(pos_records) if pos_records else pd.DataFrame()
            df_tx = pd.DataFrame(tx_records) if tx_records else pd.DataFrame()

            self.risk.results = {
                "positions": df_pos,
                "df_tx": df_tx,
                "metrics": risk_data.get("metrics", {}),
                "portfolio_name": self.risk.portfolio_name,
                "base_currency": self.risk.base_currency,
                "benchmark": self.risk.benchmark,
            }
            if not df_pos.empty or risk_data.get("metrics"):
                self.risk.is_live_active = True
                self.risk.pipeline_done = True

            wealth_data = snapshot.get("wealth", {})
            self.wealth.profile_id = wealth_data.get("profile_id", None)
            self.wealth.profile_name = wealth_data.get("profile_name", "Nessun Profilo Selezionato")
            self.wealth.linked_risk_ids = wealth_data.get("linked_risk_ids", [])

            ui_data = snapshot.get("ui", {})
            self.ui.page_subtabs = ui_data.get("page_subtabs", {})
            self.ui.active_filters = ui_data.get("active_filters", {})
            self.ui.target_tickers = ui_data.get("target_tickers", {})
            self.ui.selected_scenarios = ui_data.get("selected_scenarios", [])

            self.version += 1
            self.is_dirty = True
            self.sync_to_legacy_session_state()
            return True

    def clear_persisted_cache(self):
        """Elimina il file di cache associato a questa sessione."""
        with self._LOCK:
            path = self.get_session_cache_path()
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


def prune_stale_session_caches(max_age_hours: int = 24):
    """Elimina i file di cache delle sessioni orfane non modificate da più di `max_age_hours` ore."""
    if not os.path.exists(SESSIONS_CACHE_DIR):
        return
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    for p in glob.glob(os.path.join(SESSIONS_CACHE_DIR, "session_*.pkl")):
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except Exception:
            pass


def set_active_portfolio(portfolio_id: Union[str, int], engine: Optional[Any] = None) -> bool:
    """
    Imposta e sincronizza il portafoglio attivo come Single Source of Truth globale
    condivisa istantaneamente da tutti i motori applicativi (Risk Engine, Live Terminal, Wealth Engine).
    1. Recupera metadati, transazioni e posizioni del portafoglio per l'utente loggato.
    2. Popola atomicamente st.session_state['active_portfolio_id'], ['active_portfolio_data'],
       ['portfolio_id'], ['portfolio_name'], ['results'], e WorkspaceContext.
    3. Invalida le cache di calcolo per forzare il ricalcolo immediato su tutti i moduli.
    """
    try:
        import streamlit as st
    except ImportError:
        st = None

    if portfolio_id is None:
        return False

    # 1. Risoluzione engine
    if engine is None and st is not None:
        engine = st.session_state.get("engine")
    if engine is None:
        try:
            from core.fetcher import get_engine

            offline = bool(st.session_state.get("offline_mode", False)) if st else False
            db_name = st.session_state.get("db_name", "wealth") if st else "wealth"
            engine = get_engine(database=db_name, offline=offline)
        except Exception as e_eng:
            logger.error("Impossibile ottenere l'engine DB in set_active_portfolio: %s", e_eng)
            return False

    # 2. Query del portafoglio su DB (con isolamento utente)
    from sqlalchemy import text as sqlt

    port_meta = None
    target_pid = int(portfolio_id) if str(portfolio_id).isdigit() else portfolio_id

    try:
        with engine.connect() as conn:
            p_row = conn.execute(
                sqlt("SELECT * FROM portfolios WHERE portfolio_id = :pid"),
                {"pid": target_pid},
            ).mappings().fetchone()
            if p_row:
                port_meta = dict(p_row)
    except Exception as e_q:
        logger.warning("Query portafoglio %s fallita: %s", portfolio_id, e_q)

    port_name = port_meta.get("name", f"Portafoglio #{portfolio_id}") if port_meta else f"Portafoglio #{portfolio_id}"
    base_curr = port_meta.get("base_currency", "EUR") if port_meta else "EUR"

    # 3. Calcolo o recupero posizioni & metriche (Priorità 1: Snapshot DB a latenza sub-secondo)
    results_bundle = None
    try:
        from core.db_exporter import get_snapshot_positions_by_id

        with engine.connect() as conn:
            snap_row = conn.execute(
                sqlt(
                    "SELECT * FROM portfolio_snapshots WHERE portfolio_id = :pid ORDER BY calc_date DESC, snapshot_id DESC LIMIT 1"
                ),
                {"pid": target_pid},
            ).mappings().fetchone()
        if snap_row:
            sid = snap_row.get("snapshot_id")
            df_pos = get_snapshot_positions_by_id(engine, sid)
            tot_val = float(snap_row.get("total_value") or 0.0)
            results_bundle = {
                "portfolio_id": target_pid,
                "portfolio_name": port_name,
                "base_currency": base_curr,
                "computed_at": str(snap_row.get("calc_date")),
                "total_value": tot_val,
                "portfolio_value": tot_val,
                "positions": df_pos if df_pos is not None else pd.DataFrame(),
                "metrics": {
                    "returns": {
                        "total_value": tot_val,
                        "cagr_pct": float(snap_row.get("cagr_pct") or 0.0),
                        "sharpe_ratio": float(snap_row.get("sharpe_ratio") or 0.0),
                        "total_pnl": float(snap_row.get("total_pnl") or 0.0),
                    },
                    "market_risk": {
                        "volatility_annual_pct": float(snap_row.get("volatility_annual_pct") or 0.0),
                        "max_drawdown_pct": float(snap_row.get("max_drawdown_pct") or 0.0),
                        "var_95": float(snap_row.get("var_95_pct") or 0.0),
                        "cvar_95": float(snap_row.get("cvar_95_pct") or 0.0),
                        "beta": float(snap_row.get("ff_beta_mkt") or 1.0),
                    },
                },
            }
    except Exception as e_snap:
        logger.debug("Recupero snapshot DB veloce fallito: %s", e_snap)

    if results_bundle is None:
        try:
            from core.risk_engine import compute_risk

            rf_val = st.session_state.get("active_rf_rate", 0.03) if st else 0.03
            bm = st.session_state.get("benchmark", "SPY") if st else "SPY"
            results_bundle = compute_risk(
                target_pid, engine, benchmark_ticker=bm, risk_free_rate=rf_val, base_currency=base_curr
            )
        except Exception as e_calc:
            logger.info("compute_risk su portafoglio %s non riuscito: %s", target_pid, e_calc)

    if results_bundle is None:
        results_bundle = {
            "portfolio_id": target_pid,
            "portfolio_name": port_name,
            "base_currency": base_curr,
            "total_value": 0.0,
            "portfolio_value": 0.0,
            "positions": pd.DataFrame(),
            "metrics": {"returns": {"total_value": 0.0}, "market_risk": {}},
        }

    # 4. Aggiornamento unificato Single Source of Truth
    if st is not None:
        st.session_state["active_portfolio_id"] = str(portfolio_id)
        st.session_state["active_portfolio_data"] = results_bundle
        st.session_state["portfolio_id"] = target_pid
        st.session_state["portfolio_name"] = port_name
        st.session_state["results"] = results_bundle
        st.session_state["pipeline_done"] = True
        st.session_state["session_cleared"] = False
        st.session_state["base_currency"] = base_curr

        try:
            from core.session_manager import ArgusSessionManager

            ArgusSessionManager.set_portfolio_id(target_pid if isinstance(target_pid, int) else 1)
            pos_df = results_bundle.get("positions")
            if isinstance(pos_df, pd.DataFrame):
                ArgusSessionManager.set_active_positions(pos_df)
        except Exception:
            pass

    # 5. Sincronizzazione WorkspaceContext
    ws_ctx = WorkspaceContext.get_current()
    ws_ctx.risk.portfolio_id = target_pid
    ws_ctx.risk.portfolio_name = port_name
    ws_ctx.risk.results = results_bundle
    ws_ctx.risk.pipeline_done = True
    ws_ctx.risk.is_live_active = True
    ws_ctx.risk.base_currency = base_curr
    ws_ctx.wealth.linked_risk_ids = [target_pid] if isinstance(target_pid, int) else []
    ws_ctx.version += 1
    ws_ctx.is_dirty = True

    try:
        from core.workspace_manager import save_session_snapshot_to_cache

        save_session_snapshot_to_cache()
    except Exception:
        pass

    # 6. Invalidazione deterministica cache
    if st is not None:
        try:
            st.cache_data.clear()
        except Exception:
            pass

    return True


def _fetch_user_portfolios(
    _engine: Any, engine_key: str, uid: Optional[str], uname: str, role: str
) -> List[Dict[str, Any]]:
    from sqlalchemy import text as sqlt

    with _engine.connect() as conn:
        cols_raw = conn.execute(sqlt("SELECT * FROM portfolios LIMIT 0")).keys()
        has_uid = "user_id" in cols_raw
        has_owner = "owner" in cols_raw

        if role == "owner" or (not has_uid and not has_owner):
            q = "SELECT portfolio_id, name, base_currency FROM portfolios ORDER BY portfolio_id ASC"
            rows = conn.execute(sqlt(q)).mappings().fetchall()
        elif has_uid and uid and uid != "local-owner":
            q = "SELECT portfolio_id, name, base_currency FROM portfolios WHERE user_id = :uid ORDER BY portfolio_id ASC"
            rows = conn.execute(sqlt(q), {"uid": uid}).mappings().fetchall()
            if not rows and has_owner:
                q = "SELECT portfolio_id, name, base_currency FROM portfolios WHERE LOWER(TRIM(owner)) = LOWER(TRIM(:u)) ORDER BY portfolio_id ASC"
                rows = conn.execute(sqlt(q), {"u": uname}).mappings().fetchall()
        elif has_owner:
            q = "SELECT portfolio_id, name, base_currency FROM portfolios WHERE LOWER(TRIM(owner)) = LOWER(TRIM(:u)) ORDER BY portfolio_id ASC"
            rows = conn.execute(sqlt(q), {"u": uname}).mappings().fetchall()
        else:
            rows = []
        return [dict(r) for r in rows]


if st is not None and hasattr(st, "cache_data"):
    _fetch_user_portfolios_cached = st.cache_data(ttl=60, show_spinner=False)(_fetch_user_portfolios)
else:
    _fetch_user_portfolios_cached = _fetch_user_portfolios


def render_portfolio_selector(
    key: str = "global_active_portfolio_selector",
    label: str = "💼 Portafoglio Attivo",
    help_text: str = "Seleziona il portafoglio: sincronizza istantaneamente Risk Engine, Live Terminal e Wealth Engine.",
    only_if_multiple: bool = False,
    show_fallback: bool = False,
) -> Optional[Any]:
    """
    Componente UI universale per la selezione del portafoglio attivo (Single Source of Truth).
    Mostra i soli portafogli appartenenti all'utente loggato.
    Un cambio di selezione qui allinea istantaneamente Risk Engine, Live Terminal e Wealth Engine.
    """
    try:
        import streamlit as st
    except ImportError:
        return None

    # Recupera l'elenco dei portafogli appartenenti all'utente
    engine = st.session_state.get("engine")
    if engine is None:
        try:
            from core.fetcher import get_engine

            offline = bool(st.session_state.get("offline_mode", False))
            db_name = st.session_state.get("db_name", "wealth")
            engine = get_engine(database=db_name, offline=offline)
        except Exception:
            engine = None

    portfolios_list: List[Dict[str, Any]] = []
    if engine is not None:
        try:
            user = st.session_state.get("user")
            uid = user.id if user and hasattr(user, "id") else st.session_state.get("argus_auth_user_id")
            uname = (
                user.username
                if user and hasattr(user, "username")
                else st.session_state.get("argus_auth_user", "alessandro")
            )
            role = user.role if user and hasattr(user, "role") else st.session_state.get("argus_auth_role", "owner")
            eng_key = f"{getattr(engine, 'url', '')}_{st.session_state.get('db_name')}"
            portfolios_list = _fetch_user_portfolios_cached(
                engine, eng_key, str(uid) if uid else None, str(uname), str(role)
            )
        except Exception as e_fetch:
            logger.debug("Fetch portfolio list in selector notice: %s", e_fetch)

    # Se nessun portafoglio presente nel database ma presente in session_state
    if not portfolios_list:
        current_pid = st.session_state.get("active_portfolio_id") or st.session_state.get("portfolio_id")
        current_name = st.session_state.get("portfolio_name", "Nessun portafoglio")
        if current_pid:
            portfolios_list = [
                {
                    "portfolio_id": current_pid,
                    "name": current_name,
                    "base_currency": st.session_state.get("base_currency", "EUR"),
                }
            ]

    # Nessun portafoglio disponibile: non renderizzare sporcizia a schermo a meno che esplicitamente richiesto
    if not portfolios_list:
        if show_fallback:
            st.markdown(
                f"""
                <div style="font-size:11.5px; line-height:1.3; color:#94a3b8; padding:6px 8px; margin:4px 0 6px 0; border-radius:6px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); display:block;">
                    <b>{label}</b>: <span style="color:#f59e0b;">Nessun portafoglio caricato</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return None

    # Se richiesto solo per multi-portafoglio e ce n'è al più uno, non renderizzare widget ridondanti
    if only_if_multiple and len(portfolios_list) <= 1:
        return portfolios_list[0]["portfolio_id"]

    # Mappatura e selezione (include placeholder None per evitare cambi forzati all'avvio)
    p_options = [None] + [p["portfolio_id"] for p in portfolios_list]
    p_format = {p["portfolio_id"]: f"💼 {p['name']} (#{p['portfolio_id']})" for p in portfolios_list}
    p_format[None] = "-- Seleziona Portafoglio --"

    active_id = st.session_state.get("active_portfolio_id") or st.session_state.get("portfolio_id")
    cur_idx = 0
    if active_id is not None:
        for idx, pid in enumerate(p_options):
            if pid is not None and str(pid) == str(active_id):
                cur_idx = idx
                break

    def _on_port_selector_change():
        sel_val = st.session_state.get(key)
        if sel_val is not None and str(sel_val) != str(st.session_state.get("active_portfolio_id")):
            set_active_portfolio(sel_val, engine=engine)

    selected_pid = st.selectbox(
        label,
        options=p_options,
        index=cur_idx,
        format_func=lambda x: p_format.get(x, f"Portafoglio #{x}"),
        key=key,
        help=help_text,
        on_change=_on_port_selector_change,
    )

    return selected_pid


# ── EXPORTS DI STATE MANAGEMENT & UI LIFECYCLE ───────────────────────
def switch_profile_context(
    user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    target_portfolio_id: Optional[Union[str, int]] = None,
    is_demo: bool = False,
) -> WorkspaceContext:
    """Helper module-level per commutare deterministicamente il contesto di profilo/workspace."""
    return WorkspaceContext.switch_profile_context(
        user_id=user_id,
        workspace_id=workspace_id,
        target_portfolio_id=target_portfolio_id,
        is_demo=is_demo,
    )


try:
    from core.ui_lifecycle import (  # noqa: F401
        get_active_context_salt,
        get_ui_lifecycle_telemetry,
        get_widget_key,
        teardown_view_state,
    )
except Exception:
    pass


