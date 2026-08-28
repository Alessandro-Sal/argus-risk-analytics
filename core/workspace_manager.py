"""
ARGUS — Risk Analytics Platform
Core Module: Workspace & Multi-Tab State Manager
Provides full session state persistence across browser tabs, windows, and multi-monitor setups
using high-performance binary snapshot caching (pickle) and URL query parameters.
"""

import streamlit as st
import pandas as pd
import pickle
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


WORKSPACE_CACHE_PKL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "active_session_full.pkl"
)
WORKSPACE_CACHE_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "last_session_snapshot.json"
)

# Mappa canonica per i percorsi delle pagine Streamlit
PAGE_ROUTE_MAP = {
    "0_Control_Room": "0_Control_Room.py",
    "1_Dashboard_Generale": "pages/1_📈_Dashboard_Generale.py",
    "2_Live_Terminal": "pages/2_🖥️_Live_Terminal.py",
    "3_Analisi_Rischio": "pages/3_🔴_Analisi_Rischio.py",
    "4_Modelli_Quantitativi": "pages/4_🔬_Modelli_Quantitativi.py",
    "5_Posizioni_e_Dettagli": "pages/5_📋_Posizioni_e_Dettagli.py",
    "6_Valutazione_Aziendale": "pages/6_🏛️_Valutazione_Aziendale.py",
    "7_Stress_Testing": "pages/7_🌪️_Stress_Testing.py",
    "8_Analisi_Temporale": "pages/8_📊_Analisi_Temporale.py",
    "9_Analisi_Tecnica": "pages/9_📈_Analisi_Tecnica.py",
    "10_Screener_Opportunita": "pages/10_🔍_Screener_Opportunita.py",
    "11_BQuant_e_Launchpad": "pages/11_💻_BQuant_e_Launchpad.py",
    # Legacy & name-based aliases
    "Live_Terminal": "pages/2_🖥️_Live_Terminal.py",
    "Analisi_Rischio": "pages/3_🔴_Analisi_Rischio.py",
    "Modelli_Quantitativi": "pages/4_🔬_Modelli_Quantitativi.py",
    "Posizioni_e_Dettagli": "pages/5_📋_Posizioni_e_Dettagli.py",
    "Valutazione_Aziendale": "pages/6_🏛️_Valutazione_Aziendale.py",
    "Stress_Testing": "pages/7_🌪️_Stress_Testing.py",
    "Analisi_Temporale": "pages/8_📊_Analisi_Temporale.py",
    "Analisi_Tecnica": "pages/9_📈_Analisi_Tecnica.py",
    "Screener_Opportunita": "pages/10_🔍_Screener_Opportunita.py",
    "BQuant_e_Launchpad": "pages/11_💻_BQuant_e_Launchpad.py",
}


def resolve_page_path(page_key: str) -> str:
    """Risolve il percorso del file di pagina Streamlit in modo robusto."""
    if page_key in PAGE_ROUTE_MAP:
        return PAGE_ROUTE_MAP[page_key]
    for k, v in PAGE_ROUTE_MAP.items():
        if k in page_key or page_key in v:
            return v
    if page_key.endswith(".py"):
        return page_key if page_key.startswith("pages/") or page_key.startswith("0_") else f"pages/{page_key}"
    return "0_Control_Room.py"


def get_url_param(param_name: str, default: Any = None) -> Any:
    """Legge un parametro dai query params dell'URL in modo sicuro e retrocompatibile."""
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get(param_name, default)
            return val if val is not None else default
    except Exception:
        pass
    return default


def set_url_params(**kwargs):
    """Aggiorna i parametri query dell'URL in modo sicuro senza rompere lo stato."""
    try:
        if hasattr(st, "query_params"):
            for k, v in kwargs.items():
                if v is not None and str(v).strip() != "":
                    st.query_params[k] = str(v)
                elif k in st.query_params:
                    del st.query_params[k]
    except Exception:
        pass


def save_session_snapshot_to_cache():
    """
    Salva l'intero bundle di sessione (risultati completi, DataFrame, Serie e metadati)
    per renderlo accessibile istantaneamente a qualunque nuova scheda o finestra del browser.
    """
    try:
        results = st.session_state.get("results")
        if not results or not isinstance(results, dict):
            return

        os.makedirs(os.path.dirname(WORKSPACE_CACHE_PKL), exist_ok=True)

        session_bundle = {
            "results": results,
            "portfolio_name": st.session_state.get("portfolio_name", "Portfolio"),
            "run_id": st.session_state.get("run_id", "ACTIVE"),
            "base_currency": st.session_state.get("base_currency", "EUR"),
            "benchmark": st.session_state.get("benchmark", "SPY"),
            "offline_mode": st.session_state.get("offline_mode", False),
            "db_host": st.session_state.get("db_host", "localhost"),
            "db_port": st.session_state.get("db_port", 3306),
            "db_user": st.session_state.get("db_user", "root"),
            "db_pass": st.session_state.get("db_pass", "root"),
            "db_name": st.session_state.get("db_name", "investment_risk_bi"),
            "saved_at": datetime.now().isoformat()
        }

        # Salvataggio binario ad altissima fedeltà
        with open(WORKSPACE_CACHE_PKL, "wb") as f:
            pickle.dump(session_bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Salvataggio JSON leggero secondario
        try:
            pos = results.get("positions", pd.DataFrame())
            pos_records = pos.to_dict(orient="records") if isinstance(pos, pd.DataFrame) else []
            json_meta = {
                "saved_at": datetime.now().isoformat(),
                "run_id": st.session_state.get("run_id", "ACTIVE"),
                "portfolio_name": st.session_state.get("portfolio_name", "Portfolio"),
                "metrics": results.get("metrics", {}),
                "positions": pos_records
            }
            with open(WORKSPACE_CACHE_JSON, "w", encoding="utf-8") as jf:
                json.dump(json_meta, jf, ensure_ascii=False, default=str)
        except Exception:
            pass

    except Exception:
        pass


def clear_session_cache():
    """Elimina i file di snapshot di sessione su disco per un reset pulito."""
    for path in [WORKSPACE_CACHE_PKL, WORKSPACE_CACHE_JSON]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def try_restore_session_from_cache(force: bool = False) -> bool:
    """
    Ripristina la sessione completa da cache se aperta da una nuova scheda browser o dopo un reload,
    evitando la richiesta di ricaricare il file CSV.
    """
    if "results" in st.session_state and st.session_state["results"] is not None:
        return True

    if st.session_state.get("session_cleared", False) and not force:
        return False

    # Se ci troviamo nella Control Room e l'analisi non è stata avviata in questa sessione,
    # non ripristiniamo automaticamente analisi residue da disco
    try:
        import inspect
        for frame in inspect.stack():
            fname = frame.filename.replace("\\", "/")
            if "0_Control_Room.py" in fname and not force and not st.session_state.get("pipeline_done", False):
                return False
    except Exception:
        pass

    # 1. Prova prima dal bundle binario pickle (fedeltà 100%)
    if os.path.exists(WORKSPACE_CACHE_PKL):
        try:
            with open(WORKSPACE_CACHE_PKL, "rb") as f:
                session_bundle = pickle.load(f)

            if session_bundle and isinstance(session_bundle, dict) and "results" in session_bundle:
                for k, v in session_bundle.items():
                    if k == "saved_at":
                        continue
                    if k not in st.session_state or st.session_state[k] is None:
                        st.session_state[k] = v
                return True
        except Exception:
            pass

    # 2. Fallback da JSON se pickle non disponibile
    if os.path.exists(WORKSPACE_CACHE_JSON):
        try:
            with open(WORKSPACE_CACHE_JSON, "r", encoding="utf-8") as jf:
                data = json.load(jf)

            if data and data.get("positions"):
                pos_df = pd.DataFrame(data["positions"])
                metrics = data.get("metrics", {})
                st.session_state["results"] = {
                    "positions": pos_df,
                    "metrics": metrics,
                    "portfolio_return": pd.Series(dtype=float),
                    "benchmark_return": pd.Series(dtype=float),
                    "returns": pd.DataFrame(),
                    "stress_tests": {},
                    "optimization": {},
                    "warnings": []
                }
                st.session_state["run_id"] = data.get("run_id", "RESTORED")
                st.session_state["portfolio_name"] = data.get("portfolio_name", "Portfolio")
                return True
        except Exception:
            pass

    return False


def ensure_session_restored():
    """Funzione di guardia da chiamare all'avvio di ogni pagina per garantire che la sessione sia attiva."""
    try_restore_session_from_cache()
    sync_url_state()


def sync_url_state():
    """
    Sincronizza lo stato dell'URL con la sessione corrente.
    Se la sessione è vuota, tenta il ripristino dai parametri URL o dalla cache su disco.
    """
    if "results" not in st.session_state or st.session_state["results"] is None:
        try_restore_session_from_cache()

    if "results" in st.session_state and st.session_state["results"] is not None:
        save_session_snapshot_to_cache()
        port_name = st.session_state.get("portfolio_name", "Portfolio")
        run_id = st.session_state.get("run_id", "ACTIVE")
        set_url_params(portfolio=port_name, run_id=run_id)


# ── WORKSPACE TABS IN-APP (BARRA DELLE SCHEDE TERMINALE) ────────────────────────

DEFAULT_WORKSPACE_TABS = [
    {"id": "ws_dashboard", "title": "Dashboard Generale", "page": "1_Dashboard_Generale", "icon": "📈", "pinned": True},
    {"id": "ws_terminal", "title": "Live Terminal", "page": "2_Live_Terminal", "icon": "🖥️", "pinned": False},
    {"id": "ws_risk", "title": "Analisi Rischio", "page": "3_Analisi_Rischio", "icon": "🔴", "pinned": False},
    {"id": "ws_models", "title": "Modelli Quant", "page": "4_Modelli_Quantitativi", "icon": "🔬", "pinned": False},
    {"id": "ws_pos", "title": "Posizioni & Fisco", "page": "5_Posizioni_e_Dettagli", "icon": "📋", "pinned": False},
    {"id": "ws_val", "title": "Valutazione Aziendale", "page": "6_Valutazione_Aziendale", "icon": "🏛️", "pinned": False},
    {"id": "ws_stress", "title": "Stress Testing", "page": "7_Stress_Testing", "icon": "🌪️", "pinned": False},
    {"id": "ws_time", "title": "Analisi Temporale", "page": "8_Analisi_Temporale", "icon": "📊", "pinned": False},
    {"id": "ws_tech", "title": "Analisi Tecnica", "page": "9_Analisi_Tecnica", "icon": "📈", "pinned": False},
    {"id": "ws_screener", "title": "Screener Opportunità", "page": "10_Screener_Opportunita", "icon": "🔍", "pinned": False}
]


def init_workspace_state():
    """Inizializza la lista delle schede workspace predefinite."""
    if "workspace_tabs" not in st.session_state:
        st.session_state.workspace_tabs = list(DEFAULT_WORKSPACE_TABS)
    if "active_workspace_id" not in st.session_state:
        st.session_state.active_workspace_id = "ws_dashboard"


def get_workspace_tabs() -> List[Dict[str, Any]]:
    """Restituisce l'elenco delle schede workspace correnti."""
    init_workspace_state()
    return st.session_state.workspace_tabs


def register_workspace_tab(tab_id: str, title: str, page_name: str, params: dict = None, icon: str = "📑", pinned: bool = False):
    """Aggiunge o attiva una scheda workspace."""
    init_workspace_state()
    tabs = st.session_state.workspace_tabs

    existing = next((t for t in tabs if t["id"] == tab_id), None)
    if existing:
        existing["title"] = title
        existing["params"] = params or {}
        existing["icon"] = icon
    else:
        tabs.append({
            "id": tab_id,
            "title": title,
            "page": page_name,
            "params": params or {},
            "icon": icon,
            "pinned": pinned
        })

    st.session_state.active_workspace_id = tab_id


def close_workspace_tab(tab_id: str):
    """Chiude una scheda workspace (a meno che non sia pinnata o sia l'unica rimasta)."""
    init_workspace_state()
    tabs = st.session_state.workspace_tabs
    if len(tabs) <= 1:
        return

    st.session_state.workspace_tabs = [t for t in tabs if t["id"] != tab_id or t.get("pinned", False)]
    if st.session_state.active_workspace_id == tab_id:
        st.session_state.active_workspace_id = st.session_state.workspace_tabs[0]["id"]


def set_active_workspace(tab_id: str):
    """Imposta la scheda workspace attiva."""
    init_workspace_state()
    st.session_state.active_workspace_id = tab_id
