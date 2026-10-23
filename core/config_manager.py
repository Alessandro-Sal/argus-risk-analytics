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

_DOTENV_CACHE: Optional[Dict[str, Optional[str]]] = None
_DOTENV_MTIME: float = 0.0


def invalidate_dotenv_cache() -> None:
    """Invalida la cache in memoria del file .env per forzare la rilettura alle prossime chiamate."""
    global _DOTENV_CACHE, _DOTENV_MTIME
    _DOTENV_CACHE = None
    _DOTENV_MTIME = 0.0


def _get_dotenv_cache() -> Dict[str, Optional[str]]:
    """Restituisce il dizionario parsed di .env con caching in memoria ad alta velocità (validato tramite mtime)."""
    global _DOTENV_CACHE, _DOTENV_MTIME
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        _DOTENV_CACHE = {}
        return _DOTENV_CACHE

    try:
        mtime = env_path.stat().st_mtime
    except Exception:
        mtime = 0.0

    if _DOTENV_CACHE is None or mtime != _DOTENV_MTIME:
        try:
            from dotenv import dotenv_values

            _DOTENV_CACHE = dict(dotenv_values(env_path))
            _DOTENV_MTIME = mtime
        except Exception:
            _DOTENV_CACHE = {}
    return _DOTENV_CACHE


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
            # Fallback a caricamento diretto da cache in memoria del file .env
            d_vals = _get_dotenv_cache()
            if key in d_vals and d_vals[key] is not None and str(d_vals[key]).strip() != "":
                val = d_vals[key]
                os.environ[key] = str(val)

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
        clean = str(url).strip().rstrip("/")
        if clean.endswith("/rest/v1"):
            clean = clean[:-8].rstrip("/")
        return clean
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


def get_local_auto_login_preference() -> bool:
    """Restituisce True se l'utente ha salvato la preferenza di accesso locale immediato."""
    if not is_local_environment():
        return False
    try:
        pref_file = Path(__file__).resolve().parent.parent / "data" / ".argus_local_session.json"
        if pref_file.exists():
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return bool(data.get("auto_login", False))
    except Exception:
        pass
    return False


def set_local_auto_login_preference(enabled: bool) -> None:
    """Salva o rimuove la preferenza di accesso rapido locale su file persistente."""
    if not is_local_environment():
        return
    try:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        pref_file = data_dir / ".argus_local_session.json"
        if enabled:
            with open(pref_file, "w", encoding="utf-8") as f:
                json.dump({"auto_login": True, "user": "alessandro"}, f, indent=2)
        elif pref_file.exists():
            pref_file.unlink(missing_ok=True)
    except Exception as ex:
        logger.warning("Impossibile salvare la preferenza locale: %s", ex)


def is_auth_required() -> bool:
    """
    Determina se il login è obbligatorio all'avvio.
    Ritorna True se `ARGUS_REQUIRE_LOGIN` è impostato a 'true' (o su Streamlit Cloud con credenziali attive),
    oppure se è stato forzato un logout esplicito da sessione.
    Se in ambiente locale l'utente ha attivato l'accesso rapido locale permanente, ritorna False.
    """
    try:
        import streamlit as st

        if st.session_state.get("require_login_forced", False):
            return True
    except Exception:
        pass

    if is_local_environment() and get_local_auto_login_preference():
        return False

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
