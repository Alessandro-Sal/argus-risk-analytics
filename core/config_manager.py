# ============================================================
# core/config_manager.py
# ARGUS — Unified Configuration & Environment Manager
# Parità Locale / Streamlit Cloud con Fallback Dinamico
# ============================================================

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("argus.config_manager")

# Progetto Supabase Default (AWS EU-West-1 Ireland)
DEFAULT_SUPABASE_PROJECT_REF = "qsexxzbhtocxvyaijngb"
DEFAULT_SUPABASE_POOLER_HOST = "aws-0-eu-west-1.pooler.supabase.com"
DEFAULT_SUPABASE_POOLER_PORT = 6543
DEFAULT_SUPABASE_URL = f"https://{DEFAULT_SUPABASE_PROJECT_REF}.supabase.co"


def is_streamlit_cloud() -> bool:
    """
    Rileva in modo deterministico se l'applicazione sta girando su Streamlit Community Cloud.
    Verifica variabili d'ambiente di sistema, percorsi mount di container e presenza di secrets cloud.
    """
    if os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud" or os.getenv("IS_STREAMLIT_CLOUD", "").lower() in ("true", "1"):
        return True

    # Percorso standard di mount dei repository su Streamlit Community Cloud
    if os.path.exists("/mount/src") or os.path.exists("/app"):
        # Se siamo in container cloud linux senza file system locale windows
        if os.name != "nt":
            return True

    try:
        import streamlit as st

        if hasattr(st, "secrets") and len(st.secrets) > 0:
            # Se ci sono secrets configurati e non esiste il file locale .env, probabilmente siamo su cloud
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if not env_path.exists():
                return True
    except Exception:
        pass

    return False


def is_local_environment() -> bool:
    """Restituisce True se l'applicazione è in esecuzione in ambiente locale desktop/sviluppo."""
    return not is_streamlit_cloud()


def get_setting(key: str, default: Any = None, cast_type: Optional[type] = None) -> Any:
    """
    Risolve una chiave di configurazione con il seguente ordine rigoroso di priorità:
      1. `st.secrets` (priorità assoluta per runtime Streamlit Cloud)
      2. `os.environ` / file `.env` locale (caricato con python-dotenv)
      3. Valore `default`
    
    Supporta sia chiavi top-level (es. 'SUPABASE_URL') sia chiavi innestate in sezioni
    TOML (es. 'supabase.url', 'supabase.anon_key', 'gcp_service_account').
    """
    val = None

    # 1. Tentativo da Streamlit Secrets
    try:
        import streamlit as st

        if hasattr(st, "secrets") and st.secrets is not None:
            # 1.1 Chiave esatta top-level
            if key in st.secrets:
                val = st.secrets[key]
            # 1.2 Chiave minuscola top-level
            elif key.lower() in st.secrets:
                val = st.secrets[key.lower()]
            # 1.3 Sezione [supabase]
            elif key.startswith("SUPABASE_") and "supabase" in st.secrets and isinstance(st.secrets["supabase"], dict):
                sub_k = key[len("SUPABASE_") :].lower()
                if sub_k in st.secrets["supabase"]:
                    val = st.secrets["supabase"][sub_k]
                elif key in st.secrets["supabase"]:
                    val = st.secrets["supabase"][key]
            # 1.4 Chiave con notazione a punto (es. "section.subkey")
            elif "." in key:
                parts = key.split(".", 1)
                sec = parts[0]
                sub = parts[1]
                if sec in st.secrets and isinstance(st.secrets[sec], dict):
                    if sub in st.secrets[sec]:
                        val = st.secrets[sec][sub]
                    elif sub.lower() in st.secrets[sec]:
                        val = st.secrets[sec][sub.lower()]
    except Exception:
        pass

    # 2. Tentativo da os.environ / .env
    if val is None or str(val).strip() == "":
        env_val = os.getenv(key)
        if env_val is not None and str(env_val).strip() != "":
            val = env_val
        else:
            # Fallback a caricamento diretto da .env se non ancora presente in os.environ
            try:
                from dotenv import dotenv_values

                env_path = Path(__file__).resolve().parent.parent / ".env"
                if env_path.exists():
                    d_vals = dotenv_values(env_path)
                    if key in d_vals and d_vals[key] is not None and str(d_vals[key]).strip() != "":
                        val = d_vals[key]
                        os.environ[key] = str(val)
            except Exception:
                pass

    if val is None or (isinstance(val, str) and str(val).strip() == ""):
        return default

    # Casting facoltativo del tipo
    if cast_type is not None:
        try:
            if cast_type is bool:
                return str(val).strip().lower() in ("true", "1", "t", "yes", "y", "enabled")
            return cast_type(val)
        except Exception:
            return default

    return val


def get_supabase_url() -> str:
    """Restituisce l'URL del progetto Supabase (es. 'https://qsexxzbhtocxvyaijngb.supabase.co')."""
    url = get_setting("SUPABASE_URL", "")
    if url:
        return str(url).strip().rstrip("/")
    ref = get_setting("SUPABASE_PROJECT_REF", DEFAULT_SUPABASE_PROJECT_REF)
    return f"https://{ref}.supabase.co"


def get_supabase_anon_key() -> str:
    """Restituisce la chiave anon / public di Supabase."""
    return str(get_setting("SUPABASE_ANON_KEY", "")).strip()


def get_supabase_service_role_key() -> Optional[str]:
    """Restituisce la chiave service_role di Supabase (se configurata per script di backend)."""
    key = get_setting("SUPABASE_SERVICE_ROLE_KEY", "")
    return str(key).strip() if key else None


def get_supabase_db_password() -> str:
    """Restituisce la password del database PostgreSQL Supabase."""
    return str(get_setting("SUPABASE_DB_PASSWORD", "")).strip()


def get_supabase_db_url() -> str:
    """Restituisce l'URI completo di connessione PostgreSQL Supabase."""
    url = str(get_setting("SUPABASE_DB_URL", "")).strip()
    if url:
        return url
    pwd = get_supabase_db_password()
    if pwd:
        from core.supabase_cloud import build_supabase_db_url

        ref = get_setting("SUPABASE_PROJECT_REF", DEFAULT_SUPABASE_PROJECT_REF)
        host = get_setting("SUPABASE_POOLER_HOST", DEFAULT_SUPABASE_POOLER_HOST)
        return build_supabase_db_url(project_ref=ref, db_password=pwd, pooler_host=host)
    return ""


def is_auth_required() -> bool:
    """
    Determina se il login è obbligatorio all'avvio.
    Ritorna True se `ARGUS_REQUIRE_LOGIN` è impostato a 'true' (o su Streamlit Cloud con credenziali attive).
    """
    req = get_setting("ARGUS_REQUIRE_LOGIN", default=None)
    if req is not None:
        return str(req).strip().lower() in ("true", "1", "yes", "y")
    return is_streamlit_cloud()


def is_guest_demo_enabled() -> bool:
    """Verifica se la modalità Demo Ospite (Sandbox a 1 click) è abilitata."""
    return get_setting("ARGUS_ENABLE_GUEST_DEMO", default=True, cast_type=bool)


def get_gcp_service_account_dict() -> Optional[Dict[str, Any]]:
    """
    Recupera le credenziali del Service Account Google (GCP / Google Sheets) direttamente in memoria.
    Cerca con fallback in:
      1. `st.secrets["gcp_service_account"]` (formato TOML dict)
      2. `st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]` (stringa JSON o dict)
      3. `os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]`
    Restituisce None se non presente in memoria.
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and st.secrets is not None:
            if "gcp_service_account" in st.secrets:
                val = st.secrets["gcp_service_account"]
                return dict(val) if isinstance(val, dict) else json.loads(str(val))
            if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
                val = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
                return json.loads(str(val)) if isinstance(val, str) else dict(val)
    except Exception as e:
        logger.debug("Lettura credenziali GCP da st.secrets non riuscita: %s", e)

    env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            return json.loads(env_json.strip())
        except Exception as e:
            logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON presente in env ma JSON non valido: %s", e)

    return None
