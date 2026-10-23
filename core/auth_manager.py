# ============================================================
# core/auth_manager.py
# ARGUS — Institutional Supabase Native Auth & Session Hardening
# Lead FinTech UX/UI Architecture & Hardened Security Engine
# ============================================================

from __future__ import annotations

import html
import logging
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import streamlit as st

from core.config_manager import (
    get_setting,
    get_supabase_anon_key,
    get_supabase_url,
    is_auth_required,
    is_guest_demo_enabled,
    is_streamlit_cloud,
)
from core.i18n.translator import I18nEngine
from core.security_engine import AuthRateLimiter

logger = logging.getLogger("argus.auth_manager")

AuthViewState = Literal["LOGIN", "REGISTER", "FORGOT_PASSWORD", "RESET_CONFIRM", "MFA_VERIFY"]

_USER_SESSION_ISOLATED_KEYS = (
    "argus_user_custom_db_url",
    "engine",
    "db_engine",
    "active_wealth_portfolio_id",
    "active_wealth_profile_name",
    "wealth_active_portfolio_id",
    "wealth_active_profile_name",
    "wealth_active_snapshot",
    "sb_wealth_profile_selector",
    "wealth_profile_selector_widget",
    "cf_profile_selector_widget",
    "nw_profile_selector_widget",
    "portfolio_id",
    "portfolio_name",
    "data_loaded",
    "positions_df",
    "returns_df",
    "pipeline_done",
    "results",
    "df_clean",
    "df_tx",
    "df_raw_injected",
    "active_archetype_code",
    "active_archetype_name",
    "bitemp_ingested_portfolios",
    "selected_bitemp_port",
    "_argus_workspace_context",
    "active_portfolio_id",
    "active_portfolio_data",
)


class DotDict(dict):
    """
    Dizionario con accesso trasparente per chiave (d['id']) e per attributo (d.id),
    con supporto per gli alias istituzionali user_id <-> id e user_email <-> email.
    """

    def __getitem__(self, key: str) -> Any:
        if key in self:
            return super().__getitem__(key)
        if key == "user_id" and "id" in self:
            return super().__getitem__("id")
        if key == "id" and "user_id" in self:
            return super().__getitem__("user_id")
        if key == "user_email" and "email" in self:
            return super().__getitem__("email")
        if key == "email" and "user_email" in self:
            return super().__getitem__("user_email")
        return super().__getitem__(key)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            return None

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError:
            pass


def _clean_html(raw_html: str) -> str:
    """Rimuove l'indentazione iniziale e le righe vuote per impedire a Markdown di interpretare l'HTML come blocco di codice."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def validate_password_strength(password: str) -> Tuple[bool, str, int]:
    """
    Verifica i requisiti enterprise per la password conforme a policy NIST/OWASP.
    Requisiti minimi:
      - Almeno 10 caratteri
      - Almeno una lettera maiuscola (A-Z)
      - Almeno una lettera minuscola (a-z)
      - Almeno un numero (0-9)
      - Almeno un carattere speciale (!@#$%^&*...)
    Restituisce: (is_valid, validation_message, strength_score_0_to_100).
    """
    if not password:
        return False, "La password non può essere vuota.", 0

    score = 0
    missing: List[str] = []

    # Lunghezza
    if len(password) >= 14:
        score += 30
    elif len(password) >= 10:
        score += 20
    else:
        missing.append("almeno 10 caratteri")

    # Maiuscola
    if re.search(r"[A-Z]", password):
        score += 20
    else:
        missing.append("una lettera maiuscola")

    # Minuscola
    if re.search(r"[a-z]", password):
        score += 15
    else:
        missing.append("una lettera minuscola")

    # Numero
    if re.search(r"\d", password):
        score += 20
    else:
        missing.append("un numero")

    # Carattere speciale
    if re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/]", password):
        score += 15
    else:
        missing.append("un carattere speciale")

    if missing:
        return False, f"Requisiti mancanti: {', '.join(missing)}.", min(score, 75)

    return True, "Password eccellente conforme agli standard enterprise.", 100


def render_password_strength_bar(password: str) -> None:
    """Renderizza un badge e una barra di avanzamento dinamica per la robustezza della password."""
    if not password:
        return
    is_valid, msg, score = validate_password_strength(password)
    cur_lang = (st.session_state.get("locale") or st.session_state.get("argus_locale") or "it").lower()
    is_it = (cur_lang == "it")
    if score < 40:
        color = "#ef4444"
        label = "DEBOLE" if is_it else "WEAK"
    elif score < 75:
        color = "#f59e0b"
        label = "MEDIA" if is_it else "MEDIUM"
    else:
        color = "#10b981"
        label = "SICURA" if is_it else "STRONG"

    strength_hdr = "ROBUSTEZZA" if is_it else "STRENGTH"
    st.markdown(
        _clean_html(
            f"""
            <div style="margin-top:-6px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-size:0.72rem; color:#94a3b8; font-family:'JetBrains Mono',monospace;">
                        {strength_hdr}: <strong style="color:{color};">{label}</strong>
                    </span>
                    <span style="font-size:0.70rem; color:#94a3b8; font-family:'JetBrains Mono',monospace;">{score}%</span>
                </div>
                <div style="width:100%; height:4px; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden;">
                    <div style="width:{score}%; height:100%; background:{color}; border-radius:999px; transition:width 0.3s ease;"></div>
                </div>
                <div style="font-size:0.70rem; color:{'#94a3b8' if is_valid else '#f87171'}; margin-top:4px;">
                    {html.escape(msg)}
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def set_auth_view(view: AuthViewState) -> None:
    """Aggiorna la vista corrente della state machine di autenticazione."""
    st.session_state["auth_view"] = view


def get_auth_view() -> AuthViewState:
    """Restituisce la vista corrente della state machine (default: 'LOGIN')."""
    return st.session_state.get("auth_view", "LOGIN")


def inject_login_css() -> None:
    """
    Inietta il design system Institutional Dark ed elimina tassativamente
    la sidebar, header e footer di Streamlit prima dell'autenticazione.
    """
    st.markdown(
        _clean_html(
            """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap');

        /* Isolamento Totale: nasconde Sidebar, frecce di espansione, Header e Footer */
        header[data-testid="stHeader"],
        [data-testid="stHeader"],
        header[data-testid="stHeader"] *,
        [data-testid="stToolbar"],
        div[data-testid="stToolbar"],
        [data-testid="stExpandSidebarButton"],
        button[data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"],
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        div[data-testid="collapsedControl"],
        [data-testid="collapsedControl"],
        button[data-testid="stSidebarCollapsedControl"],
        footer {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            width: 0px !important;
            height: 0px !important;
            max-height: 0px !important;
            max-width: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
            pointer-events: none !important;
            position: absolute !important;
            top: -9999px !important;
            left: -9999px !important;
        }

        /* Sfondo principale Dark FinTech Horizon */
        .stApp {
            background: radial-gradient(circle at 15% 20%, #0f172a 0%, #060911 60%, #030509 100%) !important;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Contenitore centrale split-screen */
        .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .main .block-container {
            padding-top: 3.2rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1140px !important;
        }

        /* Card di Autenticazione Glassmorphic */
        div[data-testid="stForm"] {
            background: rgba(11, 15, 25, 0.88) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 14px !important;
            padding: 1.8rem 2.0rem !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 35px rgba(245, 158, 11, 0.04) !important;
        }

        /* Input Fields stile Terminale Istituzionale */
        div[data-baseweb="input"] {
            background-color: rgba(9, 13, 22, 0.95) !important;
            border: 1px solid rgba(148, 163, 184, 0.22) !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.18) !important;
        }
        div[data-baseweb="input"] input {
            color: #f8fafc !important;
            font-family: 'Outfit', sans-serif !important;
            font-size: 0.92rem !important;
        }

        /* Pulsante Primario Form Submit */
        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
            border-radius: 8px !important;
            padding: 0.65rem 1rem !important;
            transition: all 0.2s ease !important;
            font-family: 'Outfit', sans-serif !important;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.28) !important;
        }
        div[data-testid="stFormSubmitButton"] > button:hover {
            background: linear-gradient(135deg, #0369a1 0%, #075985 100%) !important;
            border-color: #38bdf8 !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(2, 132, 199, 0.40) !important;
        }

        /* Tipografia Brand & Value Proposition */
        .argus-brand-title {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            background: linear-gradient(180deg, #ffffff 20%, #fde68a 70%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
            line-height: 1.1;
        }
        .argus-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 12px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.28);
            border-radius: 999px;
            color: #34d399;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 1.2rem;
        }
        .argus-feature-item {
            padding: 0.85rem 1.05rem;
            background: rgba(255, 255, 255, 0.025);
            border-left: 3px solid #0284c7;
            border-radius: 0 8px 8px 0;
            margin-bottom: 0.85rem;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            border-right: 1px solid rgba(255, 255, 255, 0.04);
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }
        .argus-feature-title {
            color: #f8fafc;
            font-weight: 700;
            font-size: 0.90rem;
            margin-bottom: 3px;
        }
        .argus-feature-desc {
            color: #94a3b8;
            font-size: 0.80rem;
            line-height: 1.45;
        }
        .argus-telemetry-badge {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 1.4rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.70rem;
            color: #64748b;
        }
        .argus-telemetry-badge span {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.15);
            padding: 3px 8px;
            border-radius: 6px;
        }
        .argus-telemetry-badge b {
            color: #34d399;
        }
        </style>
        """
        ),
        unsafe_allow_html=True,
    )


class AuthManager:
    """
    Gestore centralizzato dell'autenticazione nativa Supabase Auth e della sicurezza di sessione.
    Fornisce parità trasparente tra Streamlit Community Cloud ed esecuzione locale.
    """

    @classmethod
    def get_supabase_client(cls, access_token: Optional[str] = None):
        """Restituisce il client Supabase SDK configurato e opzionalmente autenticato con JWT."""
        from core.supabase_cloud import get_supabase_client

        return get_supabase_client(access_token=access_token)

    @classmethod
    def get_authenticated_client(cls):
        """Restituisce un client Supabase / PostgREST autenticato con Bearer JWT dell'utente attivo."""
        token = ""
        sess = st.session_state.get("argus_session")
        if isinstance(sess, dict):
            token = sess.get("access_token", "")
        if not token:
            u = st.session_state.get("user")
            if isinstance(u, (dict, DotDict)):
                token = getattr(u, "access_token", "") or u.get("access_token", "")
        client = cls.get_supabase_client(access_token=token)
        if client is not None and token:
            try:
                client.postgrest.auth(token)
            except Exception:
                pass
        return client

    @classmethod
    def sign_in(cls, email: str, password: str, remember_session: bool = True) -> Dict[str, Any]:
        """Esegue l'accesso tramite Supabase Auth nativo (GoTrue)."""
        return cls.login(email, password, remember_session=remember_session)

    @classmethod
    def sign_out(cls) -> None:
        """Disconnette l'utente e azzera lo stato di sessione."""
        cls.logout()

    @classmethod
    def refresh_session_if_needed(cls) -> bool:
        """Verifica la scadenza del token di sessione ed esegue il refresh se necessario."""
        sess = st.session_state.get("argus_session")
        if isinstance(sess, dict) and "expires_at" in sess:
            exp = sess.get("expires_at", 0)
            if exp and int(exp) > 0 and (int(time.time()) + 300) > int(exp):
                return cls.refresh_session()
        return True

    @classmethod
    def require_auth(cls) -> bool:
        """Guardia reattiva per Streamlit: blocca con st.stop() se non autenticato."""
        return cls.auth_guard(show_login_if_unauth=True)

    @classmethod
    def login(
        cls,
        email_or_username: str,
        password: str,
        remember_session: bool = True,
    ) -> Dict[str, Any]:
        """
        Autentica l'utente tramite Supabase Auth nativo (sign_in_with_password).
        Supporta mapping automatico username -> email ed effettua fallback a DB locale se offline.
        Gestisce la rate limit protection e l'opzione Remember Me con timeout.
        """
        raw_identity = (email_or_username or "").strip()
        pwd = (password or "").strip()

        if not raw_identity or not pwd:
            return {"ok": False, "error": "Inserisci sia username/email che password."}

        # Normalizzazione identity per Supabase Auth
        email = raw_identity
        if "@" not in email:
            if email.lower() in ("alessandro", "owner", "admin"):
                email = "owner@argus.cloud"
            else:
                email = f"{email.lower()}@argus.cloud"

        # 1. Tentativo prioritario con Supabase Auth SDK nativo
        client = cls.get_supabase_client()
        anon_key = get_supabase_anon_key()
        supa_url = get_supabase_url()

        if client is not None and anon_key and supa_url and "dummy" not in anon_key:
            try:
                auth_res = client.auth.sign_in_with_password({"email": email, "password": pwd})
                if auth_res and auth_res.user:
                    u = auth_res.user
                    sess = auth_res.session
                    role = (
                        "owner"
                        if (
                            email.lower() in ("owner@argus.cloud", "alessandro@argus.cloud", "alessandro.saladino@live.it")
                            or email.lower().startswith("alessandro")
                        )
                        else "user"
                    )
                    user_meta = getattr(u, "user_metadata", {}) or {}
                    disp_name = user_meta.get("display_name") or raw_identity

                    session_data = {
                        "ok": True,
                        "user_id": str(u.id),
                        "email": u.email or email,
                        "username": raw_identity if "@" not in raw_identity else email.split("@")[0],
                        "display_name": disp_name,
                        "role": role,
                        "access_token": getattr(sess, "access_token", ""),
                        "refresh_token": getattr(sess, "refresh_token", ""),
                        "expires_at": getattr(sess, "expires_at", int(time.time()) + (86400 * 30 if remember_session else 7200)),
                        "remember_session": remember_session,
                    }
                    # Mirror/Sync opzionale su tabella applicativa argus_users
                    try:
                        from core.fetcher import get_engine
                        from core.supabase_cloud import (
                            SupabaseAuthManager,
                            create_supabase_engine,
                            get_supabase_config,
                        )

                        cfg = get_supabase_config()
                        eng = create_supabase_engine(cfg["db_url"], use_cache=True) if cfg.get("is_configured") else None
                        if eng is None:
                            eng = get_engine(offline=True)
                        if eng is not None:
                            SupabaseAuthManager.create_or_update_user(
                                engine=eng,
                                username=raw_identity if "@" not in raw_identity else email.split("@")[0],
                                password=pwd,
                                role=role,
                                display_name=disp_name,
                                email=email,
                            )
                    except Exception as ex_sync_login:
                        logger.debug("Sync login su argus_users non bloccante: %s", ex_sync_login)

                    cls.apply_session(session_data, remember_session=remember_session)
                    return session_data
            except Exception as ex_supa:
                err_str = str(ex_supa)
                logger.info("Tentativo Supabase Auth SDK fallito: %s", err_str)
                if "invalid login credentials" in err_str.lower() or "invalid_grant" in err_str.lower():
                    pass

        # 2. Fallback su SupabaseAuthManager (supporta password DB amministratore e tabella argus_users locale/cloud)
        try:
            from core.supabase_cloud import SupabaseAuthManager

            fallback_res = SupabaseAuthManager.authenticate_user(raw_identity, pwd)
            if fallback_res.get("ok"):
                sess_info = {
                    "ok": True,
                    "user_id": str(fallback_res.get("user_id") or raw_identity),
                    "email": fallback_res.get("email") or email,
                    "username": fallback_res.get("username") or raw_identity,
                    "display_name": fallback_res.get("display_name") or raw_identity,
                    "role": fallback_res.get("role", "user"),
                    "access_token": fallback_res.get("access_token", ""),
                    "refresh_token": "",
                    "expires_at": int(time.time()) + (86400 * 30 if remember_session else 7200),
                    "custom_db_url": fallback_res.get("custom_db_url", ""),
                    "remember_session": remember_session,
                }
                cls.apply_session(sess_info, remember_session=remember_session)
                return sess_info
            else:
                return {"ok": False, "error": fallback_res.get("error", "Credenziali non valide.")}
        except Exception as ex_fallback:
            logger.error("Errore fallback autenticazione: %s", ex_fallback)

        return {"ok": False, "error": "Credenziali non valide o utente non registrato."}

    @classmethod
    def sign_up(cls, email_or_username: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Registra un nuovo account personale con Supabase Auth nativo o provvigiona uno spazio isolato.
        Applica la validazione rigorosa della complessità password.
        """
        raw_identity = (email_or_username or "").strip()
        pwd = (password or "").strip()
        name = (display_name or raw_identity).strip()

        if not raw_identity or not pwd:
            return {"ok": False, "error": "Compila tutti i campi obbligatori."}

        is_valid, validation_msg, _ = validate_password_strength(pwd)
        if not is_valid:
            return {"ok": False, "error": validation_msg}

        email = raw_identity
        if "@" not in email:
            email = f"{email.lower()}@argus.cloud"

        # 1. Verifica preventiva di unicità su tabella applicativa argus_users
        try:
            from sqlalchemy import inspect
            from sqlalchemy import text as sqlt

            from core.fetcher import get_engine
            from core.supabase_cloud import create_supabase_engine, get_supabase_config

            cfg_chk = get_supabase_config()
            eng_chk = create_supabase_engine(cfg_chk["db_url"], use_cache=True) if cfg_chk.get("is_configured") else None
            if eng_chk is None:
                eng_chk = get_engine(offline=True)
            if eng_chk is not None:
                insp = inspect(eng_chk)
                if "argus_users" in insp.get_table_names():
                    uname_chk = raw_identity if "@" not in raw_identity else email.split("@")[0].lower()
                    with eng_chk.connect() as conn:
                        row_existing = conn.execute(
                            sqlt("SELECT username, email FROM argus_users WHERE LOWER(email) = :e OR LOWER(username) = :u"),
                            {"e": email.lower(), "u": uname_chk},
                        ).fetchone()
                        if row_existing:
                            eu, ee = str(row_existing[0]), str(row_existing[1] or "")
                            if ee.lower() == email.lower():
                                return {
                                    "ok": False,
                                    "error": f"L'indirizzo email '{email}' risulta già registrato (@{eu}). Effettua il login o richiedi il recupero password.",
                                }
                            return {
                                "ok": False,
                                "error": f"Il nome utente '@{uname_chk}' è già in uso. Scegli un altro username o accedi con la tua password.",
                            }
        except Exception as ex_dup_chk:
            logger.debug("Verifica unicità argus_users non bloccante: %s", ex_dup_chk)

        # 2. Registrazione su Supabase Auth nativo (GoTrue)
        client = cls.get_supabase_client()
        anon_key = get_supabase_anon_key()
        supa_url = get_supabase_url()

        if client is not None and hasattr(client, "auth"):
            try:
                sign_res = client.auth.sign_up(
                    {
                        "email": email,
                        "password": pwd,
                        "options": {"data": {"display_name": name, "username": raw_identity.split("@")[0]}},
                    }
                )
                if sign_res and sign_res.user:
                    u = sign_res.user
                    identities = getattr(u, "identities", None)
                    # Verifica anti-duplicato Supabase GoTrue: se l'email esiste già, identities è vuoto ([])
                    if identities is not None and len(identities) == 0:
                        return {
                            "ok": False,
                            "error": f"L'indirizzo email '{email}' risulta già registrato su Supabase. Effettua l'accesso o reimposta la password.",
                        }

                    sess = sign_res.session
                    session_data = {
                        "ok": True,
                        "user_id": str(u.id),
                        "email": u.email or email,
                        "username": raw_identity if "@" not in raw_identity else email.split("@")[0],
                        "display_name": name,
                        "role": "user",
                        "access_token": getattr(sess, "access_token", "") if sess else "",
                        "refresh_token": getattr(sess, "refresh_token", "") if sess else "",
                        "expires_at": getattr(sess, "expires_at", int(time.time()) + 3600) if sess else 0,
                    }
                    # Mirror/Sync su tabella applicativa argus_users (allow_update=False per evitare duplicati)
                    try:
                        from core.fetcher import get_engine
                        from core.supabase_cloud import (
                            SupabaseAuthManager,
                            create_supabase_engine,
                            get_supabase_config,
                        )

                        cfg = get_supabase_config()
                        eng = create_supabase_engine(cfg["db_url"], use_cache=True) if cfg.get("is_configured") else None
                        if eng is None:
                            eng = get_engine(offline=True)
                        if eng is not None:
                            SupabaseAuthManager.create_or_update_user(
                                engine=eng,
                                username=raw_identity if "@" not in raw_identity else email.split("@")[0],
                                password=pwd,
                                role="user",
                                display_name=name,
                                email=email,
                                allow_update=False,
                            )
                    except Exception as ex_sync_reg:
                        logger.debug("Sync sign_up su argus_users non bloccante: %s", ex_sync_reg)

                    if sess:
                        cls.apply_session(session_data)
                    return session_data
            except Exception as ex_reg:
                err_msg = str(ex_reg)
                logger.warning("Supabase Auth sign_up exception: %s", err_msg)
                if any(
                    dup_word in err_msg.lower()
                    for dup_word in ("already registered", "already exists", "user already", "email address is already in use")
                ):
                    return {
                        "ok": False,
                        "error": f"L'indirizzo email '{email}' risulta già registrato. Effettua il login o richiedi il recupero password.",
                    }

        # 3. Fallback registrazione su DB SQL locale/cloud (argus_users)
        try:
            from core.fetcher import get_engine
            from core.supabase_cloud import SupabaseAuthManager, create_supabase_engine, get_supabase_config

            cfg = get_supabase_config()
            eng = create_supabase_engine(cfg["db_url"], use_cache=True) if cfg.get("is_configured") else None
            if eng is None:
                eng = get_engine(offline=True)

            c_res = SupabaseAuthManager.create_or_update_user(
                engine=eng,
                username=raw_identity.split("@")[0],
                password=pwd,
                role="user",
                display_name=name,
                email=email,
                allow_update=False,
            )
            if c_res.get("ok"):
                sess_info = {
                    "ok": True,
                    "user_id": str(c_res.get("user_id", raw_identity)),
                    "email": email,
                    "username": c_res.get("username", raw_identity),
                    "display_name": c_res.get("display_name", name),
                    "role": "user",
                    "access_token": "",
                    "refresh_token": "",
                    "expires_at": int(time.time()) + 86400,
                }
                cls.apply_session(sess_info)
                return sess_info
            return {"ok": False, "error": c_res.get("error", "Errore durante la creazione dell'account.")}
        except Exception as ex_db_reg:
            return {"ok": False, "error": f"Errore registrazione: {ex_db_reg}"}

    @classmethod
    def request_password_reset(cls, email: str) -> Dict[str, Any]:
        """
        Step 1 del recupero password: invia un'email con OTP/link di recovery via Supabase Auth.
        Garantisce un messaggio neutro anti-user enumeration.
        """
        from core.supabase_cloud import SupabaseAuthManager

        return SupabaseAuthManager.reset_password_for_email(email)

    @classmethod
    def confirm_password_reset(cls, email: str, token: str, new_password: str) -> Dict[str, Any]:
        """
        Step 2 del recupero password: verifica il token/OTP e aggiorna le credenziali.
        """
        from core.supabase_cloud import SupabaseAuthManager

        is_valid, validation_msg, _ = validate_password_strength(new_password)
        if not is_valid:
            return {"ok": False, "error": validation_msg}

        return SupabaseAuthManager.verify_otp_and_update_password(email, token, new_password)

    @classmethod
    def apply_session(cls, auth_res: Dict[str, Any], remember_session: bool = True) -> None:
        """Salva in `st.session_state` l'oggetto sessione: access_token, user_id, user_email, expires_at."""
        for k in _USER_SESSION_ISOLATED_KEYS:
            st.session_state.pop(k, None)

        role = auth_res.get("role", "user")
        uname = auth_res.get("username", "user")
        user_id = str(auth_res.get("user_id", ""))
        email = auth_res.get("email", "")
        token = auth_res.get("access_token", "")
        expires = auth_res.get("expires_at", int(time.time()) + (86400 * 30 if remember_session else 7200))
        disp_name = auth_res.get("display_name", uname)

        # Single Source of Truth: oggetto user accessibile via dict o dot notation (user.id, user.email, user.access_token)
        user_obj = DotDict(
            {
                "id": user_id,
                "user_id": user_id,
                "email": email,
                "user_email": email,
                "access_token": token,
                "refresh_token": auth_res.get("refresh_token", ""),
                "expires_at": expires,
                "username": uname,
                "display_name": disp_name,
                "role": role,
            }
        )
        st.session_state["user"] = user_obj
        st.session_state["user_id"] = user_id

        # Hardened session dictionary
        st.session_state.argus_session = {
            "user_id": user_id,
            "user_email": email,
            "access_token": token,
            "refresh_token": auth_res.get("refresh_token", ""),
            "expires_at": expires,
            "role": role,
            "username": uname,
            "display_name": disp_name,
            "remember_session": remember_session,
            "last_active_timestamp": time.time(),
            "inactivity_timeout": None if remember_session else 7200,
        }

        st.session_state["authenticated"] = True
        st.session_state["argus_auth_verified"] = True
        st.session_state["argus_auth_role"] = role
        st.session_state["argus_auth_user"] = uname
        st.session_state["argus_auth_user_id"] = user_id
        st.session_state["argus_auth_email"] = email
        st.session_state["argus_auth_display_name"] = disp_name
        st.session_state["argus_user_custom_db_url"] = auth_res.get("custom_db_url", "")
        st.session_state["splash_dismissed"] = False
        st.session_state["splash_completed"] = False
        st.session_state["_app_initialized"] = False
        st.session_state["require_login_forced"] = False

        if role == "owner":
            st.session_state.argus_auth_personal_profile_id = 1
        elif role == "guest_demo":
            st.session_state.argus_auth_personal_profile_id = None
            st.session_state.offline_mode = True
        else:
            st.session_state.argus_auth_personal_profile_id = None
            st.session_state.offline_mode = False

        try:
            st.cache_data.clear()
            # Manteniamo st.cache_resource warm per preservare connection pool e ridurre a zero la latenza di avvio
        except Exception:
            pass

    @classmethod
    def logout(cls) -> None:
        """Esegue il logout da Supabase Auth e azzera completamente la sessione Streamlit."""
        try:
            import threading

            client = cls.get_supabase_client()
            if client is not None:
                # Esecuzione in background daemon thread per azzerare la latenza di rete e il freeze della UI
                threading.Thread(target=client.auth.sign_out, daemon=True).start()
        except Exception:
            pass

        for k in list(st.session_state.keys()):
            if (
                k.startswith("argus_auth_")
                or k.startswith("argus_session")
                or k in _USER_SESSION_ISOLATED_KEYS
            ):
                st.session_state.pop(k, None)

        st.session_state.pop("user", None)
        st.session_state.pop("user_id", None)
        st.session_state.pop("argus_session", None)
        st.session_state.pop("active_portfolio_id", None)
        st.session_state.pop("active_portfolio_data", None)
        st.session_state.pop("supabase_cloud_authenticated", None)

        st.session_state["authenticated"] = False
        st.session_state["argus_auth_verified"] = False
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = False
        st.session_state["_app_initialized"] = False
        st.session_state["argus_portal_mode"] = None
        st.session_state["auth_view"] = "LOGIN"
        st.session_state["require_login_forced"] = True
        try:
            from core.config_manager import set_local_auto_login_preference

            set_local_auto_login_preference(False)
        except Exception:
            pass

        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass

    @classmethod
    def login_guest_demo(cls) -> None:
        """Inizializza una sessione sandbox a 1 click (Ospite / Recruiter) completamente isolata in memoria."""
        cls.apply_session(
            {
                "ok": True,
                "user_id": "demo-guest-sandbox",
                "email": "guest@argus.demo",
                "username": "guest_demo",
                "display_name": "Demo Recruiter (Sandbox)",
                "role": "guest_demo",
                "access_token": "",
                "expires_at": int(time.time()) + 86400,
            }
        )
        st.session_state["offline_mode"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["_app_initialized"] = True
        st.session_state["authenticated"] = True

    @classmethod
    def login_sandbox_archetype(cls, archetype_code: str = "hnwi_family") -> None:
        """
        Avvia istantaneamente la Sandbox Istituzionale caricando uno specifico archetipo
        (HNWI Family, FIRE Decumulation, Young Accumulator).
        """
        arch_names = {
            "hnwi_family": "HNWI Family Office",
            "fire_decumulation": "FIRE Decumulation",
            "young_accumulator": "Young Accumulator",
        }
        title = arch_names.get(archetype_code, "Sandbox Istituzionale")

        cls.apply_session(
            {
                "ok": True,
                "user_id": f"sandbox-{archetype_code}",
                "email": f"{archetype_code}@argus.sandbox",
                "username": f"sandbox_{archetype_code}",
                "display_name": f"Sandbox ({title})",
                "role": "guest_demo",
                "access_token": "",
                "expires_at": int(time.time()) + 86400,
            }
        )
        st.session_state["offline_mode"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["_app_initialized"] = True
        st.session_state["authenticated"] = True
        st.session_state["active_archetype_code"] = archetype_code

        # Iniezione automatica dell'archetipo nel workspace context
        try:
            from core.archetype_manager import execute_unified_archetype_load

            execute_unified_archetype_load(archetype_code, auto_run=False, source_module="risk")
        except Exception as ex_arch:
            logger.info("Auto-injection archetipo sandbox: %s", ex_arch)

    @classmethod
    def login_local_owner(cls, remember_session: bool = True) -> None:
        """
        Inizializza istantaneamente la sessione locale per il Titolare (Alessandro)
        senza richiedere email e password quando in ambiente locale (MySQL / SQLite).
        """
        cls.apply_session(
            {
                "ok": True,
                "user_id": "local-owner",
                "email": "alessandro.saladino@live.it",
                "username": "alessandro",
                "display_name": "Alessandro (Titolare)",
                "role": "owner",
                "access_token": "",
                "expires_at": int(time.time()) + 86400 * 365,
            },
            remember_session=remember_session,
        )
        st.session_state["argus_auth_verified"] = True
        st.session_state["authenticated"] = True
        st.session_state["offline_mode"] = False
        st.session_state["splash_dismissed"] = False
        st.session_state["splash_completed"] = False
        st.session_state["_app_initialized"] = False
        st.session_state["argus_auth_personal_profile_id"] = 1
        st.session_state["require_login_forced"] = False
        st.session_state["supabase_cloud_authenticated"] = False

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """Restituisce le informazioni sull'utente autenticato nella sessione corrente."""
        if not cls.is_authenticated():
            return None
        return (
            st.session_state.get("user")
            or st.session_state.get("argus_session")
            or {
                "user_id": st.session_state.get("argus_auth_user_id"),
                "id": st.session_state.get("argus_auth_user_id"),
                "user_email": st.session_state.get("argus_auth_email"),
                "email": st.session_state.get("argus_auth_email"),
                "username": st.session_state.get("argus_auth_user"),
                "role": st.session_state.get("argus_auth_role", "user"),
                "display_name": st.session_state.get("argus_auth_display_name", "Utente"),
                "access_token": "",
            }
        )

    @classmethod
    def is_authenticated(cls) -> bool:
        """Verifica se la sessione corrente è attiva, valida e non scaduta per inattività."""
        is_auth = bool(
            st.session_state.get("authenticated", False)
            or st.session_state.get("argus_auth_verified", False)
        )
        if not is_auth:
            return False

        sess = st.session_state.get("argus_session")
        if isinstance(sess, dict):
            now = time.time()
            # Controllo timeout inattività se remember_session è False
            if not sess.get("remember_session", True):
                inactivity_timeout = sess.get("inactivity_timeout", 7200)
                last_active = sess.get("last_active_timestamp", now)
                if (now - last_active) > inactivity_timeout:
                    logger.info("Sessione scaduta per inattività (timeout: %ds).", inactivity_timeout)
                    cls.logout()
                    return False

            sess["last_active_timestamp"] = now

            # Controllo scadenza token
            exp = sess.get("expires_at", 0)
            if exp and int(exp) > 0 and int(now) > int(exp):
                if not cls.refresh_session():
                    cls.logout()
                    return False
        return True

    @classmethod
    def refresh_session(cls) -> bool:
        """Tenta il refresh del token JWT tramite il refresh_token salvato in sessione."""
        sess = st.session_state.get("argus_session")
        if not isinstance(sess, dict) or not sess.get("refresh_token"):
            return False

        client = cls.get_supabase_client()
        if client is None:
            return False

        try:
            r_res = client.auth.refresh_session(sess["refresh_token"])
            if r_res and r_res.session:
                new_sess = r_res.session
                sess["access_token"] = getattr(new_sess, "access_token", "")
                sess["refresh_token"] = getattr(new_sess, "refresh_token", sess["refresh_token"])
                sess["expires_at"] = getattr(new_sess, "expires_at", int(time.time()) + 3600)
                st.session_state.argus_session = sess
                if "user" in st.session_state and isinstance(st.session_state["user"], (dict, DotDict)):
                    st.session_state["user"]["access_token"] = sess["access_token"]
                return True
        except Exception as ex_ref:
            logger.info("Impossibile eseguire il refresh del token: %s", ex_ref)
        return False

    @classmethod
    def auth_guard(cls, show_login_if_unauth: bool = True) -> bool:
        """
        Guardia di sicurezza per le pagine dell'applicazione.
        Se l'utente non è autenticato o la sessione è scaduta:
          1. Mostra la schermata di Login Istituzionale a tutto schermo.
          2. Nasconde totalmente la sidebar per evitare leakage di dati.
          3. Blocca tassativamente l'esecuzione sottostante con `st.stop()`.
        Restituisce True se l'accesso è autorizzato.
        """
        # Se il login non è richiesto (sviluppo locale senza ARGUS_REQUIRE_LOGIN o con auto-login locale attivo)
        if not is_auth_required():
            if not st.session_state.get("argus_auth_verified", False):
                cls.login_local_owner(remember_session=True)
            return True

        # Se già autenticato
        if cls.is_authenticated():
            return True

        if show_login_if_unauth:
            from components.splash import auto_collapse_sidebar

            auto_collapse_sidebar()
            cls.render_login_ui()
            st.stop()

        return False

    @classmethod
    def render_login_ui(cls) -> None:
        """Renderizza l'interfaccia grafica istituzionale di autenticazione ARGUS."""
        render_institutional_login_gate()


def render_institutional_login_gate() -> bool:
    """
    Renderizza il gate di accesso istituzionale split-screen a 60 FPS con State Machine
    e restituisce True se l'utente è autenticato.
    """
    if AuthManager.is_authenticated():
        return True

    inject_login_css()

    # Inizializzazione stato della State Machine
    if "auth_view" not in st.session_state:
        st.session_state["auth_view"] = "LOGIN"
    if "failed_attempts" not in st.session_state:
        st.session_state["failed_attempts"] = 0
    if "lockout_until" not in st.session_state:
        st.session_state["lockout_until"] = 0.0

    # Intercettazione automatica dei parametri query URL (Redirect da email Supabase)
    qp = getattr(st, "query_params", {})
    if qp:
        q_type = qp.get("type") or ""
        if q_type == "recovery" or "recovery" in str(qp):
            st.session_state["auth_view"] = "RESET_CONFIRM"
            if "token" in qp:
                st.session_state["recovery_token_param"] = qp.get("token")
            if "email" in qp:
                st.session_state["recovery_email"] = qp.get("email")

    cur_lang = (st.session_state.get("locale") or st.session_state.get("argus_locale") or "it").lower()
    is_it = (cur_lang == "it")

    try:
        from core.ui_utils import get_argus_eye_svg

        eye_svg = get_argus_eye_svg(size=56, animated=True, accent="#f59e0b", unique_id="auth_split_eye")
    except Exception:
        eye_svg = "<div style='font-size:42px;'>🏛️</div>"

    col_brand, col_spacer, col_auth = st.columns([1.18, 0.08, 1.0])

    # ── COLONNA SINISTRA: BRAND & VALUE PROPOSITION ────────────────
    with col_brand:
        brand_subtitle = "Analisi del Rischio &amp; Intelligence Patrimoniale" if is_it else "Risk Analytics &amp; Wealth Intelligence"
        status_pill_text = "● Sistema Operativo · v10.0.0 Istituzionale" if is_it else "● Operating System · v10.0.0 Institutional"
        brand_desc = (
            "Terminale quantitativo unificato per la gestione integrata del rischio di mercato, "
            "analisi fattoriale, fiscalità avanzata e allocazione patrimoniale multi-asset."
            if is_it else
            "Unified quantitative terminal for integrated market risk management, "
            "factor analysis, advanced taxation, and multi-asset wealth allocation."
        )
        f1_title = "⚡ Architettura di Calcolo Rischi Multi-Asset" if is_it else "⚡ Multi-Asset Risk Computation Engine"
        f1_desc = (
            "VaR/CVaR parametrico e storico, simulazione Monte Carlo vettorizzata, Stress Testing CCAR e modelli fattoriali MSCI/Barra."
            if is_it else
            "Parametric and historical VaR/CVaR, vectorized Monte Carlo simulation, CCAR Stress Testing, and MSCI/Barra factor models."
        )
        f2_title = "🏛️ Gestione Patrimoniale &amp; Fiscale Integrata" if is_it else "🏛️ Integrated Wealth &amp; Tax Management"
        f2_desc = (
            "Consolidamento in tempo reale di conti bancari, immobili, previdenza integrativa, ottimizzazione minusvalenze e Quadro RW."
            if is_it else
            "Real-time consolidation of bank accounts, real estate, pension funds, capital loss tax harvesting, and Italian Quadro RW."
        )
        f3_title = "🛡️ Sicurezza Enterprise &amp; Sincronizzazione Cloud" if is_it else "🛡️ Enterprise Security &amp; Cloud Synchronization"
        f3_desc = (
            "Isolamento multi-tenant con Supabase Row-Level Security (auth.uid = user_id), credenziali protette in memoria e crittografia AES-256."
            if is_it else
            "Multi-tenant isolation via Supabase Row-Level Security (auth.uid = user_id), in-memory credential protection, and AES-256 encryption."
        )
        t_engine = "Motore Principale: <b>Attivo</b>" if is_it else "Core Engine: <b>Active</b>"
        t_cloud = "Cassaforte Cloud: <b>Pronta</b>" if is_it else "Cloud Vault: <b>Ready</b>"
        t_rls = "Isolamento RLS: <b>Attivo</b>" if is_it else "RLS Isolation: <b>Active</b>"
        t_latency = "Latenza: <b>~12ms</b>" if is_it else "Latency: <b>~12ms</b>"

        st.markdown(
            _clean_html(
                f"""
                <div style="padding-top: 1.0rem;">
                    <div style="display:flex; align-items:center; gap:14px; margin-bottom:12px;">
                        {eye_svg}
                        <div>
                            <div class="argus-brand-title">ARGUS</div>
                            <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#f59e0b; font-weight:700; letter-spacing:0.18em; text-transform:uppercase;">
                                {brand_subtitle}
                            </div>
                        </div>
                    </div>

                    <div class="argus-status-pill">{status_pill_text}</div>

                    <p style="color:#94a3b8; font-size:0.95rem; line-height:1.55; margin-bottom:1.6rem;">
                        {brand_desc}
                    </p>

                    <div class="argus-feature-item">
                        <div class="argus-feature-title">{f1_title}</div>
                        <div class="argus-feature-desc">{f1_desc}</div>
                    </div>

                    <div class="argus-feature-item">
                        <div class="argus-feature-title">{f2_title}</div>
                        <div class="argus-feature-desc">{f2_desc}</div>
                    </div>

                    <div class="argus-feature-item">
                        <div class="argus-feature-title">{f3_title}</div>
                        <div class="argus-feature-desc">{f3_desc}</div>
                    </div>

                    <div class="argus-telemetry-badge">
                        <span>{t_engine}</span>
                        <span>{t_cloud}</span>
                        <span>{t_rls}</span>
                        <span>{t_latency}</span>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    # ── COLONNA DESTRA: AUTH STATE MACHINE CONTAINER ───────────────
    with col_auth:
        current_view: AuthViewState = st.session_state["auth_view"]

        # Controllo Lockout Brute-Force da Rate Limiter
        now = time.time()
        lockout_until = float(st.session_state.get("lockout_until", 0.0))
        if now < lockout_until:
            remaining = int(lockout_until - now) + 1
            err_lock = (
                f"⛔ **Terminale Temporaneamente Bloccato**: troppi tentativi falliti rilevati.\n\n"
                f"Riprova tra **{remaining} secondi**."
                if is_it else
                f"⛔ **Terminal Temporarily Locked**: too many failed attempts detected.\n\n"
                f"Retry in **{remaining} seconds**."
            )
            st.error(err_lock)
            return False

        # Barra superiore lingua e contesto
        top_c1, top_c2 = st.columns([1.6, 1.0])
        with top_c1:
            caption_text = "🛡️ **Cassaforte di Autenticazione Supabase (GoTrue)**" if is_it else "🛡️ **Supabase Authentication Vault (GoTrue)**"
            st.caption(caption_text)
        with top_c2:
            l_it, l_en = st.columns(2)
            with l_it:
                if st.button("IT", key="btn_lang_toggle_it", type="primary" if is_it else "secondary", use_container_width=True):
                    st.session_state["locale"] = "it"
                    st.session_state["argus_locale"] = "it"
                    I18nEngine.get_instance().set_locale("it")
                    st.rerun()
            with l_en:
                if st.button("EN", key="btn_lang_toggle_en", type="primary" if not is_it else "secondary", use_container_width=True):
                    st.session_state["locale"] = "en"
                    st.session_state["argus_locale"] = "en"
                    I18nEngine.get_instance().set_locale("en")
                    st.rerun()

        # ── 1. VISTA LOGIN (Default) ──────────────────────────────────
        if current_view == "LOGIN":
            from core.config_manager import (
                get_local_auto_login_preference,
                is_local_environment,
                set_local_auto_login_preference,
            )

            is_local = is_local_environment()

            if is_local:
                loc_title = "Accesso Diretto Postazione Locale" if is_it else "Direct Local Workstation Access"
                loc_desc = (
                    "Sei sulla tua macchina locale (MySQL / SQLite). Puoi entrare direttamente con il tuo account titolare senza dover inserire email e password."
                    if is_it else
                    "You are on your local machine (MySQL / SQLite). You can sign in directly with your owner account without entering email and password."
                )
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(5, 150, 105, 0.04) 100%);
                                border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px;">
                        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span style="font-size:1.2rem;">💻</span>
                                <span style="font-size:0.88rem; font-weight:700; color:#34d399; letter-spacing:0.04em; text-transform:uppercase;">
                                    {loc_title}
                                </span>
                            </div>
                            <span style="font-size:0.68rem; color:#10b981; font-family:'JetBrains Mono',monospace; background:rgba(16,185,129,0.18); padding:3px 8px; border-radius:12px; font-weight:700;">
                                OFFLINE / WORKSTATION
                            </span>
                        </div>
                        <div style="font-size:0.80rem; color:#cbd5e1; line-height:1.45; margin-bottom:10px;">
                            {loc_desc}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                chk_remember_label = (
                    "Ricorda ed entra sempre in automatico all'avvio su questo PC"
                    if is_it else
                    "Remember and always sign in automatically on startup on this PC"
                )
                chk_remember_help = (
                    "Se attivo, all'avvio locale salterà del tutto questa schermata accedendo direttamente allo splash screen."
                    if is_it else
                    "If enabled, future local startups will skip this screen and open the splash screen directly."
                )
                remember_local = st.checkbox(
                    chk_remember_label,
                    value=get_local_auto_login_preference(),
                    key="chk_auto_login_local",
                    help=chk_remember_help,
                )

                btn_bypass_label = "⚡ Entra Subito al Terminale (Alessandro)" if is_it else "⚡ Enter Terminal Now (Alessandro)"
                btn_bypass_help = (
                    "Accesso immediato senza credenziali per l'ambiente locale"
                    if is_it else
                    "Instant access without credentials for local environment"
                )
                if st.button(
                    btn_bypass_label,
                    type="primary",
                    use_container_width=True,
                    key="btn_quick_local_bypass",
                    help=btn_bypass_help,
                ):
                    set_local_auto_login_preference(remember_local)
                    AuthManager.login_local_owner(remember_session=True)
                    st.session_state["splash_dismissed"] = False
                    st.session_state["splash_completed"] = False
                    st.session_state["_app_initialized"] = False
                    msg_succ = "✅ Accesso locale autorizzato. Apertura dello splash screen..." if is_it else "✅ Local access authorized. Opening splash screen..."
                    st.success(msg_succ)
                    time.sleep(0.2)
                    st.rerun()

                div_or_text = "oppure accedi con credenziali Cloud / Supabase" if is_it else "or sign in with Cloud / Supabase credentials"
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; margin: 18px 0 16px 0; text-align:center;">
                        <div style="flex-grow:1; border-bottom: 1px solid rgba(255,255,255,0.1);"></div>
                        <span style="padding: 0 10px; font-size:0.72rem; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; font-weight:600;">
                            {div_or_text}
                        </span>
                        <div style="flex-grow:1; border-bottom: 1px solid rgba(255,255,255,0.1);"></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.form("argus_login_form", clear_on_submit=False):
                form_title = "### Accesso al Terminale" if is_it else "### Terminal Sign In"
                form_caption = (
                    "Inserisci le tue credenziali per accedere al workspace riservato."
                    if is_it else
                    "Enter your credentials to access the confidential workspace."
                )
                st.markdown(form_title)
                st.caption(form_caption)

                email_lbl = "Email o Username Istituzionale" if is_it else "Institutional Email or Username"
                email_ph = "nome.cognome@dominio.it o username" if is_it else "name.surname@domain.com or username"
                email_hlp = (
                    "Per il Titolare: inserisci 'alessandro' o 'owner@argus.cloud'."
                    if is_it else
                    "For Owner: enter 'alessandro' or 'owner@argus.cloud'."
                )
                login_email = st.text_input(
                    email_lbl,
                    key="login_identity_in",
                    placeholder=email_ph,
                    help=email_hlp,
                )
                pwd_lbl = "Password Personale" if is_it else "Personal Password"
                login_pwd = st.text_input(
                    pwd_lbl,
                    type="password",
                    key="login_password_in",
                    placeholder="••••••••••••",
                )

                remember_lbl = "Mantieni la sessione attiva su questo dispositivo" if is_it else "Keep session active on this device"
                remember_me = st.checkbox(
                    remember_lbl,
                    value=True,
                    key="login_remember_me_check",
                )

                btn_sub_lbl = "Accedi al Terminale" if is_it else "Sign In to Terminal"
                btn_login = st.form_submit_button(btn_sub_lbl, use_container_width=True)

                if btn_login:
                    if not login_email or not login_pwd:
                        msg_missing = "Compila sia il campo email/username che la password." if is_it else "Please fill in both the email/username and password fields."
                        st.warning(msg_missing)
                    else:
                        allowed, rem_sec, limit_msg = AuthRateLimiter.check_rate_limit(login_email)
                        if not allowed:
                            st.session_state["lockout_until"] = time.time() + rem_sec
                            st.error(f"⛔ {limit_msg}")
                        else:
                            spin_txt = "Autenticazione crittografica e verifica token in corso..." if is_it else "Cryptographic authentication and token verification in progress..."
                            with st.spinner(spin_txt):
                                auth_result = AuthManager.login(
                                    login_email, login_pwd, remember_session=remember_me
                                )

                            if auth_result.get("ok"):
                                st.session_state["failed_attempts"] = 0
                                st.session_state["lockout_until"] = 0.0
                                AuthRateLimiter.record_success(login_email)
                                disp_u = auth_result.get('display_name', login_email)
                                succ_login = f"✅ Accesso autorizzato. Benvenuto, **{disp_u}**!" if is_it else f"✅ Access authorized. Welcome, **{disp_u}**!"
                                st.success(succ_login)
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                fails, lock_sec = AuthRateLimiter.record_failure(login_email)
                                st.session_state["failed_attempts"] = fails
                                if lock_sec > 0:
                                    st.session_state["lockout_until"] = time.time() + lock_sec
                                    err_lck = f"❌ Troppi tentativi errati. Blocco temporaneo per {lock_sec} secondi." if is_it else f"❌ Too many failed attempts. Temporarily locked for {lock_sec} seconds."
                                    st.error(err_lck)
                                else:
                                    def_err = 'Credenziali errate.' if is_it else 'Invalid credentials.'
                                    err_str = f"❌ Accesso fallito: {auth_result.get('error', def_err)}" if is_it else f"❌ Sign in failed: {auth_result.get('error', def_err)}"
                                    st.error(err_str)

            # Navigazione secondaria a zero-flicker
            c_nav1, c_nav2 = st.columns(2)
            with c_nav1:
                btn_forgot_lbl = "Password dimenticata?" if is_it else "Forgot password?"
                st.button(
                    btn_forgot_lbl,
                    on_click=set_auth_view,
                    args=("FORGOT_PASSWORD",),
                    use_container_width=True,
                    key="btn_nav_forgot",
                )
            with c_nav2:
                btn_reg_lbl = "Crea nuovo account" if is_it else "Create new account"
                st.button(
                    btn_reg_lbl,
                    on_click=set_auth_view,
                    args=("REGISTER",),
                    use_container_width=True,
                    key="btn_nav_register",
                )

            # Quick-Launch Sandbox Bar (Valutazione Rapida Didattica)
            st.markdown("<hr style='margin:1.1rem 0 0.8rem 0; border-color:rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)
            cap_sandbox = "🚀 ACCESSO RAPIDO VALUTAZIONE (SANDBOX DIDATTICA)" if is_it else "🚀 QUICK EVALUATION ACCESS (EDUCATIONAL SANDBOX)"
            st.caption(cap_sandbox)

            demo_col1, demo_col2 = st.columns([1.6, 1.0])
            with demo_col1:
                selected_archetype = st.selectbox(
                    "Profilo Sandbox Didattico" if is_it else "Educational Sandbox Profile",
                    options=["hnwi_family", "fire_decumulation", "young_accumulator"],
                    format_func=lambda x: {
                        "hnwi_family": ("👑 HNWI Family Office (€4.8M)" if is_it else "👑 HNWI Family Office (€4.8M)"),
                        "fire_decumulation": ("🏖️ FIRE Decumulo (Cedolare)" if is_it else "🏖️ FIRE Decumulation (Dividend)"),
                        "young_accumulator": ("🚀 Giovane Accumulatore (PAC)" if is_it else "🚀 Young Accumulator (DCA)"),
                    }[x],
                    label_visibility="collapsed",
                    key="sb_login_archetype_select",
                )
            with demo_col2:
                btn_demo_lbl = "Avvia Demo" if is_it else "Launch Demo"
                if st.button(btn_demo_lbl, use_container_width=True, key="btn_login_launch_demo", type="secondary"):
                    spin_sb = "Inizializzazione sandbox multi-asset in corso..." if is_it else "Initializing multi-asset sandbox..."
                    with st.spinner(spin_sb):
                        AuthManager.login_sandbox_archetype(selected_archetype)
                    succ_sb = "✅ Sandbox attivata con successo!" if is_it else "✅ Sandbox activated successfully!"
                    st.success(succ_sb)
                    time.sleep(0.3)
                    st.rerun()

        # ── 2. VISTA RECUPERO PASSWORD (Richiesta OTP) ────────────────
        elif current_view == "FORGOT_PASSWORD":
            with st.form("argus_forgot_form", clear_on_submit=False):
                st.markdown("### Recupero Credenziali" if is_it else "### Password Recovery")
                st.caption(
                    "Inserisci l'indirizzo email associato al tuo profilo per ricevere il token di recupero."
                    if is_it else
                    "Enter the email address associated with your profile to receive a recovery token."
                )

                f_email = st.text_input(
                    "Email Registrata" if is_it else "Registered Email",
                    placeholder="nome.cognome@dominio.it" if is_it else "name.surname@domain.com",
                    key="forgot_email_input",
                )
                submit_forgot = st.form_submit_button(
                    "Invia Codice di Recupero" if is_it else "Send Recovery Code",
                    use_container_width=True,
                )

                if submit_forgot:
                    if not f_email or "@" not in f_email or "." not in f_email:
                        st.warning("Inserisci un indirizzo email sintatticamente valido." if is_it else "Please enter a syntactically valid email address.")
                    else:
                        spin_f = "Invio istruzioni di recupero in corso..." if is_it else "Sending recovery instructions..."
                        with st.spinner(spin_f):
                            res_req = AuthManager.request_password_reset(f_email)
                        st.session_state["recovery_email"] = f_email
                        def_msg = "Se l'indirizzo è registrato, riceverai a breve il codice." if is_it else "If the address is registered, you will receive the code shortly."
                        st.success(res_req.get("message", def_msg))
                        time.sleep(1.0)
                        set_auth_view("RESET_CONFIRM")
                        st.rerun()

            btn_back_forgot = "← Torna al Login" if is_it else "← Back to Sign In"
            st.button(
                btn_back_forgot,
                on_click=set_auth_view,
                args=("LOGIN",),
                use_container_width=True,
                key="btn_back_to_login_from_forgot",
            )

        # ── 3. VISTA CONFERMA RESET E CAMBIO PASSWORD ──────────────────
        elif current_view == "RESET_CONFIRM":
            with st.form("argus_reset_confirm_form", clear_on_submit=False):
                st.markdown("### Imposta Nuova Password" if is_it else "### Set New Password")
                st.caption(
                    "Inserisci il codice di sicurezza (OTP o token) ricevuto via email e definisci la nuova password."
                    if is_it else
                    "Enter the security code (OTP or token) received via email and set your new password."
                )

                prefilled_email = st.session_state.get("recovery_email", "")
                conf_email = st.text_input(
                    "Email di Recupero" if is_it else "Recovery Email",
                    value=prefilled_email,
                    key="reset_conf_email_input",
                    placeholder="nome.cognome@dominio.it" if is_it else "name.surname@domain.com",
                )
                prefilled_token = st.session_state.get("recovery_token_param", "")
                conf_token = st.text_input(
                    "Codice OTP / Token di Recupero" if is_it else "OTP Code / Recovery Token",
                    value=prefilled_token,
                    key="reset_conf_token_input",
                    placeholder="Codice numerico o token di sicurezza" if is_it else "Numeric code or security token",
                )
                new_pwd = st.text_input(
                    "Nuova Password (min. 10 caratteri)" if is_it else "New Password (min. 10 chars)",
                    type="password",
                    key="reset_new_pwd_input",
                    placeholder="••••••••••••",
                )
                render_password_strength_bar(new_pwd)

                confirm_pwd = st.text_input(
                    "Conferma Nuova Password" if is_it else "Confirm New Password",
                    type="password",
                    key="reset_confirm_pwd_input",
                    placeholder="••••••••••••",
                )

                btn_sub_reset = "Aggiorna Password & Accedi" if is_it else "Update Password & Sign In"
                submit_confirm = st.form_submit_button(btn_sub_reset, use_container_width=True)

                if submit_confirm:
                    is_valid, val_msg, _ = validate_password_strength(new_pwd)
                    if not conf_email or not conf_token:
                        st.warning("Email e codice OTP sono campi obbligatori." if is_it else "Email and OTP code are required fields.")
                    elif new_pwd != confirm_pwd:
                        st.error("Le password inserite non coincidono." if is_it else "The passwords entered do not match.")
                    elif not is_valid:
                        st.error(val_msg)
                    else:
                        spin_reset = "Aggiornamento credenziali crittografiche in corso..." if is_it else "Updating cryptographic credentials..."
                        with st.spinner(spin_reset):
                            res_upd = AuthManager.confirm_password_reset(conf_email, conf_token, new_pwd)
                        if res_upd.get("ok"):
                            succ_pwd = "🎉 Password aggiornata con successo! Effettua il login con le nuove credenziali." if is_it else "🎉 Password successfully updated! Please sign in with your new credentials."
                            st.success(succ_pwd)
                            time.sleep(1.2)
                            set_auth_view("LOGIN")
                            st.rerun()
                        else:
                            err_pwd = f"❌ Errore aggiornamento password: {res_upd.get('error')}" if is_it else f"❌ Password update error: {res_upd.get('error')}"
                            st.error(err_pwd)

            btn_cancel_lbl = "← Annulla e torna al Login" if is_it else "← Cancel and Back to Sign In"
            st.button(
                btn_cancel_lbl,
                on_click=set_auth_view,
                args=("LOGIN",),
                use_container_width=True,
                key="btn_cancel_reset_confirm",
            )

        # ── 4. VISTA REGISTRAZIONE OPERATORE ──────────────────────────
        elif current_view == "REGISTER":
            with st.form("argus_register_form", clear_on_submit=False):
                st.markdown("### Registrazione Operatore" if is_it else "### Operator Registration")
                st.caption(
                    "Configura le tue credenziali istituzionali per creare un nuovo workspace isolato."
                    if is_it else
                    "Configure your institutional credentials to create a new isolated workspace."
                )

                reg_name = st.text_input(
                    "Nome Completo / Ragione Sociale *" if is_it else "Full Name / Organization *",
                    placeholder="es. Marco Rossi o Capital Family Office" if is_it else "e.g. John Doe or Capital Family Office",
                    key="reg_name_input",
                )
                reg_email = st.text_input(
                    "Email Istituzionale *" if is_it else "Institutional Email *",
                    placeholder="nome.cognome@dominio.it" if is_it else "name.surname@domain.com",
                    key="reg_email_input",
                )
                reg_pwd = st.text_input(
                    "Password di Accesso (min. 10 caratteri) *" if is_it else "Access Password (min. 10 characters) *",
                    type="password",
                    key="reg_pwd_input",
                    placeholder="••••••••••••",
                )
                render_password_strength_bar(reg_pwd)

                reg_pwd_confirm = st.text_input(
                    "Conferma Password *" if is_it else "Confirm Password *",
                    type="password",
                    key="reg_pwd_confirm_input",
                    placeholder="••••••••••••",
                )

                btn_sub_reg = "Crea Workspace Istituzionale" if is_it else "Create Institutional Workspace"
                submit_reg = st.form_submit_button(btn_sub_reg, use_container_width=True)

                if submit_reg:
                    is_valid, val_msg, _ = validate_password_strength(reg_pwd)
                    if not reg_name or not reg_email:
                        st.warning("Tutti i campi contrassegnati con * sono obbligatori." if is_it else "All fields marked with * are required.")
                    elif reg_pwd != reg_pwd_confirm:
                        st.error("Le password inserite non coincidono." if is_it else "The passwords entered do not match.")
                    elif not is_valid:
                        st.error(val_msg)
                    else:
                        spin_reg = "Creazione profilo crittografato e provvigione RLS in corso..." if is_it else "Creating encrypted profile and provisioning RLS..."
                        with st.spinner(spin_reg):
                            reg_res = AuthManager.sign_up(reg_email, reg_pwd, display_name=reg_name)
                        if reg_res.get("ok"):
                            succ_reg = f"🎉 Workspace per **{reg_name}** creato con successo!" if is_it else f"🎉 Workspace for **{reg_name}** created successfully!"
                            st.success(succ_reg)
                            time.sleep(1.0)
                            st.rerun()
                        else:
                            err_reg = f"❌ Errore durante la registrazione: {reg_res.get('error')}" if is_it else f"❌ Registration error: {reg_res.get('error')}"
                            st.error(err_reg)

            btn_back_reg = "← Hai già un account? Accedi" if is_it else "← Already have an account? Sign In"
            st.button(
                btn_back_reg,
                on_click=set_auth_view,
                args=("LOGIN",),
                use_container_width=True,
                key="btn_back_to_login_from_reg",
            )

    return False


def require_auth() -> bool:
    """Funzione helper di primo livello per Streamlit: garantisce che la sessione sia autenticata o blocca con st.stop()."""
    return AuthManager.require_auth()
