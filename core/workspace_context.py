"""
ARGUS — Risk Analytics Platform
Core Module: Unified & Isolated Workspace Context Engine
Thread-safe, multi-tenant ready, with deterministic lifecycle and zero cross-contamination.
"""

import os
import glob
import json
import time
import uuid
import pickle
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
import pandas as pd


# ── STORAGE PATHS & CONSTANTS ────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_CACHE_DIR = os.path.join(BASE_DIR, "data", "cache", "sessions")
LEGACY_CACHE_PKL = os.path.join(BASE_DIR, "data", "cache", "active_session_full.pkl")
LEGACY_CACHE_JSON = os.path.join(BASE_DIR, "data", "cache", "last_session_snapshot.json")

# Prefissi o chiavi di widget di pagina da bonificare al cambio portafoglio/analisi
ANALYTICAL_ORPHAN_PREFIXES = (
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
    "target_subtab_"
)

ANALYTICAL_EXACT_KEYS = {
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
    "sandbox_preset_name"
}


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
    profile_id: Optional[int] = 1
    profile_name: str = "Profilo Principale"
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
            elif "results" in st_state and st_state["results"] is None and not self.risk.results:
                self.risk.results = None
                self.risk.is_live_active = False

            if "portfolio_id" in st_state:
                self.risk.portfolio_id = st_state.get("portfolio_id")
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
            if "wealth_active_profile_name" in st_state:
                self.wealth.profile_name = st_state.get("wealth_active_profile_name", "Profilo Principale")

    def sync_to_legacy_session_state(self):
        """Propaga lo stato tipizzato alle chiavi legacy di st.session_state per garantire retrocompatibilità."""
        st_state = self._get_st_session_state()
        if st_state is None:
            return

        with self._LOCK:
            st_state["results"] = self.risk.results
            st_state["portfolio_id"] = self.risk.portfolio_id
            st_state["portfolio_name"] = self.risk.portfolio_name
            st_state["run_id"] = self.risk.run_id
            st_state["base_currency"] = self.risk.base_currency
            st_state["benchmark"] = self.risk.benchmark
            st_state["active_rf_rate"] = self.risk.risk_free_rate
            st_state["pipeline_done"] = self.risk.pipeline_done
            st_state["fetch_report"] = self.risk.fetch_report

            if self.wealth.profile_id is not None:
                st_state["wealth_active_portfolio_id"] = self.wealth.profile_id
            if self.wealth.profile_name:
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
                for key in ["results", "portfolio_id", "portfolio_name", "run_id", "pipeline_done", "fetch_report", "sandbox_preset_name"]:
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

    def flush_wealth_domain(self):
        """Azzera deterministicamente lo stato del modulo Wealth."""
        with self._LOCK:
            self.wealth = WealthSubContext()
            st_state = self._get_st_session_state()
            if st_state is not None:
                for key in ["wealth_profile_selector_widget", "wealth_active_profile_name"]:
                    if key in st_state:
                        del st_state[key]
            self.version += 1
            self.is_dirty = True

    # ── REACTIVE TOTAL WEALTH CONSOLIDATION BRIDGE ─────────────

    def get_consolidated_equity_for_wealth(
        self,
        engine,
        linked_risk_ids: Optional[List[int]] = None
    ) -> float:
        """
        Riconciliazione reattiva: integra in tempo reale il valore del portafoglio Risk
        attivo in memoria senza costringere a salvare prima uno snapshot su database.
        Se vi sono altri portafogli Risk collegati non in memoria, ne aggrega lo snapshot DB.
        """
        with self._LOCK:
            self.sync_from_legacy_session_state()
            from core.wealth.wealth_db import get_linked_risk_portfolios, get_available_risk_portfolios

            w_pid = self.wealth.profile_id or 1
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

            bundle = {
                "session_id": self.session_id,
                "version": self.version,
                "saved_at": datetime.now().isoformat(),
                "risk": {
                    "results": self.risk.results,
                    "portfolio_id": self.risk.portfolio_id,
                    "portfolio_name": self.risk.portfolio_name,
                    "run_id": self.risk.run_id,
                    "base_currency": self.risk.base_currency,
                    "benchmark": self.risk.benchmark,
                    "risk_free_rate": self.risk.risk_free_rate,
                    "pipeline_done": self.risk.pipeline_done
                },
                "wealth": {
                    "profile_id": self.wealth.profile_id,
                    "profile_name": self.wealth.profile_name,
                    "linked_risk_ids": self.wealth.linked_risk_ids
                },
                "ui": {
                    "page_subtabs": self.ui.page_subtabs,
                    "active_filters": self.ui.active_filters,
                    "target_tickers": self.ui.target_tickers
                }
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
                    "saved_at": datetime.now().isoformat()
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
                        "metrics": self.risk.results.get("metrics", {}),
                        "positions": pos_rec
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

            # 1. Tenta prima dal file specifico della sessione
            session_path = self.get_session_cache_path()
            if os.path.exists(session_path):
                try:
                    with open(session_path, "rb") as f:
                        bundle = pickle.load(f)
                    if bundle and isinstance(bundle, dict):
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
                            self.wealth.profile_id = w_data.get("profile_id", 1)
                            self.wealth.profile_name = w_data.get("profile_name", "Profilo Principale")
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
            pos = self.risk.results.get("positions") if (self.risk.results and isinstance(self.risk.results, dict)) else None
            pos_records = pos.to_dict(orient="records") if isinstance(pos, pd.DataFrame) else []

            df_tx = self.risk.results.get("df_tx") if (self.risk.results and isinstance(self.risk.results, dict)) else None
            tx_records = df_tx.to_dict(orient="records") if isinstance(df_tx, pd.DataFrame) else []

            metrics = self.risk.results.get("metrics", {}) if (self.risk.results and isinstance(self.risk.results, dict)) else {}

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
                    "transactions": tx_records
                },
                "wealth": {
                    "profile_id": self.wealth.profile_id,
                    "profile_name": self.wealth.profile_name,
                    "linked_risk_ids": self.wealth.linked_risk_ids
                },
                "ui": {
                    "page_subtabs": dict(self.ui.page_subtabs),
                    "active_filters": dict(self.ui.active_filters),
                    "target_tickers": dict(self.ui.target_tickers),
                    "selected_scenarios": list(self.ui.selected_scenarios)
                }
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
                "benchmark": self.risk.benchmark
            }
            if not df_pos.empty or risk_data.get("metrics"):
                self.risk.is_live_active = True
                self.risk.pipeline_done = True

            wealth_data = snapshot.get("wealth", {})
            self.wealth.profile_id = wealth_data.get("profile_id", 1)
            self.wealth.profile_name = wealth_data.get("profile_name", "Profilo Principale")
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
