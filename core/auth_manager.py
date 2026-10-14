# ============================================================
# core/auth_manager.py
# ARGUS — Institutional Supabase Native Auth & Session Hardening
# Hardening con Supabase Auth SDK, Session State Guard & RLS
# ============================================================

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import streamlit as st

from core.config_manager import (
    get_setting,
    get_supabase_anon_key,
    get_supabase_url,
    is_auth_required,
    is_guest_demo_enabled,
    is_streamlit_cloud,
)

logger = logging.getLogger("argus.auth_manager")

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
    def login(cls, email_or_username: str, password: str) -> Dict[str, Any]:
        """
        Autentica l'utente tramite Supabase Auth nativo (sign_in_with_password).
        Supporta mapping automatico username -> email ed effettua fallback a DB locale se offline.
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
                    role = "owner" if email.lower() in ("owner@argus.cloud", "alessandro@argus.cloud") else "user"
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
                        "expires_at": getattr(sess, "expires_at", int(time.time()) + 3600),
                    }
                    cls.apply_session(session_data)
                    return session_data
            except Exception as ex_supa:
                err_str = str(ex_supa)
                logger.info("Tentativo Supabase Auth SDK fallito o utente non ancora su Auth: %s", err_str)
                # Se è un errore esplicito di credenziali errate da Supabase Auth
                if "invalid login credentials" in err_str.lower() or "invalid_grant" in err_str.lower():
                    # Verifica se l'utente esiste nella tabella argus_users o se è la password DB
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
                    "expires_at": int(time.time()) + 86400,
                    "custom_db_url": fallback_res.get("custom_db_url", ""),
                }
                cls.apply_session(sess_info)
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
        """
        raw_identity = (email_or_username or "").strip()
        pwd = (password or "").strip()
        name = (display_name or raw_identity).strip()

        if not raw_identity or not pwd:
            return {"ok": False, "error": "Compila tutti i campi obbligatori."}
        if len(pwd) < 6:
            return {"ok": False, "error": "La password deve contenere almeno 6 caratteri."}

        email = raw_identity
        if "@" not in email:
            email = f"{email.lower()}@argus.cloud"

        client = cls.get_supabase_client()
        anon_key = get_supabase_anon_key()
        supa_url = get_supabase_url()

        if client is not None and anon_key and supa_url and "dummy" not in anon_key:
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
                    if sess:
                        cls.apply_session(session_data)
                    return session_data
            except Exception as ex_reg:
                logger.warning("Supabase Auth sign_up exception: %s", ex_reg)

        # Fallback registrazione su DB SQL locale/cloud (argus_users)
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
    def apply_session(cls, auth_res: Dict[str, Any]) -> None:
        """Salva in `st.session_state` l'oggetto sessione: access_token, user_id, user_email, expires_at."""
        for k in _USER_SESSION_ISOLATED_KEYS:
            st.session_state.pop(k, None)

        role = auth_res.get("role", "user")
        uname = auth_res.get("username", "user")
        user_id = str(auth_res.get("user_id", ""))
        email = auth_res.get("email", "")
        token = auth_res.get("access_token", "")
        expires = auth_res.get("expires_at", int(time.time()) + 3600)

        # Hardened session dictionary
        st.session_state.argus_session = {
            "user_id": user_id,
            "user_email": email,
            "access_token": token,
            "refresh_token": auth_res.get("refresh_token", ""),
            "expires_at": expires,
            "role": role,
            "username": uname,
            "display_name": auth_res.get("display_name", uname),
        }

        st.session_state.argus_auth_verified = True
        st.session_state.argus_auth_role = role
        st.session_state.argus_auth_user = uname
        st.session_state.argus_auth_user_id = user_id
        st.session_state.argus_auth_email = email
        st.session_state.argus_auth_display_name = auth_res.get("display_name", uname)
        st.session_state.argus_user_custom_db_url = auth_res.get("custom_db_url", "")

        # Personal profile ID default: 1 per il titolare, None per consentire isolamento
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
            st.cache_resource.clear()
        except Exception:
            pass

    @classmethod
    def logout(cls) -> None:
        """Esegue il logout da Supabase Auth e azzera completamente la sessione Streamlit."""
        try:
            client = cls.get_supabase_client()
            if client is not None:
                client.auth.sign_out()
        except Exception:
            pass

        for k in list(st.session_state.keys()):
            if k.startswith("argus_auth_") or k.startswith("argus_session") or k in _USER_SESSION_ISOLATED_KEYS:
                st.session_state.pop(k, None)

        st.session_state["argus_auth_verified"] = False
        st.session_state["splash_dismissed"] = False
        st.session_state["_app_initialized"] = False

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

    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """Restituisce le informazioni sull'utente autenticato nella sessione corrente."""
        if not cls.is_authenticated():
            return None
        return st.session_state.get("argus_session") or {
            "user_id": st.session_state.get("argus_auth_user_id"),
            "user_email": st.session_state.get("argus_auth_email"),
            "username": st.session_state.get("argus_auth_user"),
            "role": st.session_state.get("argus_auth_role", "user"),
            "display_name": st.session_state.get("argus_auth_display_name", "Utente"),
            "access_token": "",
        }

    @classmethod
    def is_authenticated(cls) -> bool:
        """Verifica se la sessione corrente è attiva, valida e non scaduta."""
        if not st.session_state.get("argus_auth_verified", False):
            return False

        sess = st.session_state.get("argus_session")
        if isinstance(sess, dict) and "expires_at" in sess:
            exp = sess["expires_at"]
            if exp and int(exp) > 0 and int(time.time()) > int(exp):
                # Token scaduto: tenta il refresh automatico
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
        # Se il login non è richiesto (sviluppo locale senza ARGUS_REQUIRE_LOGIN)
        if not is_auth_required():
            if not st.session_state.get("argus_auth_verified", False):
                st.session_state["argus_auth_verified"] = True
                st.session_state["argus_auth_role"] = "owner"
                st.session_state["argus_auth_user"] = "alessandro"
                st.session_state["argus_auth_display_name"] = "Alessandro (Locale)"
                st.session_state["argus_auth_personal_profile_id"] = 1
            return True

        # Se già autenticato
        if cls.is_authenticated():
            return True

        if show_login_if_unauth:
            # Nasconde la sidebar Streamlit per protezione dati
            from components.splash import auto_collapse_sidebar

            auto_collapse_sidebar()
            cls.render_login_ui()
            st.stop()

        return False

    @classmethod
    def render_login_ui(cls) -> None:
        """Renderizza l'interfaccia grafica istituzionale di autenticazione ARGUS."""
        try:
            from core.ui_utils import get_argus_eye_svg

            eye_svg = get_argus_eye_svg(size=64, animated=True, accent="#f59e0b", unique_id="auth_mgr_gate_eye")
        except Exception:
            eye_svg = "🏛️"

        supa_url = get_supabase_url()
        proj_ref = supa_url.replace("https://", "").split(".")[0] if supa_url else "cloud"
        cloud_badge = f"🟢 Supabase Cloud ({proj_ref[:8]}…)" if supa_url else "💾 Vault Sicuro"

        st.markdown(
            f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap');

            /* Nasconde Sidebar e Toolbar di Streamlit */
            header[data-testid="stHeader"],
            [data-testid="stHeader"],
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
            button[data-testid="stSidebarCollapsedControl"] {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                width: 0px !important;
                height: 0px !important;
                pointer-events: none !important;
                position: absolute !important;
                top: -9999px !important;
                left: -9999px !important;
            }}

            .block-container,
            div[data-testid="stAppViewBlockContainer"],
            .main .block-container {{
                padding-top: 1.5rem !important;
                padding-bottom: 1.5rem !important;
                max-width: 1040px !important;
                min-height: 90vh !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
            }}

            div[data-testid="stVerticalBlockBorderWrapper"] {{
                background: radial-gradient(900px circle at 50% 0%, rgba(26, 36, 54, 0.94) 0%, rgba(13, 19, 32, 0.98) 65%, rgba(6, 9, 16, 0.99) 100%) !important;
                border: 1px solid rgba(245, 158, 11, 0.32) !important;
                border-radius: 20px !important;
                padding: 24px 28px !important;
                box-shadow: 0 24px 64px rgba(0, 0, 0, 0.85), 0 0 40px rgba(245, 158, 11, 0.08) !important;
            }}

            div[data-testid="stForm"] {{
                border: none !important;
                padding: 0 !important;
                background: transparent !important;
            }}

            button[data-baseweb="tab"] {{
                font-family: 'Outfit', sans-serif !important;
                font-size: 14px !important;
                font-weight: 700 !important;
                padding: 9px 16px !important;
            }}
            </style>

            <div style="text-align:center; max-width:680px; margin: 0 auto 16px auto;">
                <div style="display:flex; justify-content:center; margin-bottom:8px; filter:drop-shadow(0 0 24px rgba(245,158,11,0.45));">
                    {eye_svg}
                </div>
                <div style="font-family:'Outfit',sans-serif; font-size:34px; font-weight:900; letter-spacing:10px;
                            background:linear-gradient(180deg,#ffffff 20%,#fde68a 68%,#f59e0b 100%);
                            -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1.15;">
                    ARGUS
                </div>
                <div style="font-family:'Outfit',sans-serif; font-size:11.5px; font-weight:800; color:#f59e0b;
                            letter-spacing:3.5px; text-transform:uppercase; margin:4px 0 12px 0;">
                    INSTITUTIONAL RISK &amp; WEALTH INTELLIGENCE • SUPABASE AUTH VAULT
                </div>
                <div style="display:flex; justify-content:center; gap:8px; flex-wrap:wrap;">
                    <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#34d399;
                                 background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.30);
                                 padding:3px 10px; border-radius:999px;">{cloud_badge}</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#fbbf24;
                                 background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.30);
                                 padding:3px 10px; border-radius:999px;">🛡️ Supabase JWT / RLS Protection</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#818cf8;
                                 background:rgba(99,102,241,0.14); border:1px solid rgba(99,102,241,0.30);
                                 padding:3px 10px; border-radius:999px;">👥 Multi-Tenant Zero-Leakage</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols = st.columns([0.8, 2.0, 0.8])
        col_c = cols[1] if len(cols) >= 3 else (cols[0] if len(cols) > 0 else st.container())
        with col_c:
            with st.container(border=True):
                tab_login, tab_reg, tab_guest = st.tabs(
                    [
                        "🔐 Accedi",
                        "➕ Nuovo Account",
                        "🚀 Demo Sandbox",
                    ]
                )

                with tab_login:
                    st.markdown(
                        "<div style='font-size:12.5px; color:#94a3b8; margin-bottom:12px;'>"
                        "Inserisci le tue credenziali Supabase Auth o il tuo account per accedere allo spazio patrimoniale privato."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    with st.form("argus_auth_login_form_unified", clear_on_submit=False, border=False):
                        user_in = st.text_input(
                            "Email o Username",
                            key="auth_login_email_input",
                            placeholder="es. owner@argus.cloud, alessandro, marco@email.com...",
                            help="Per il Titolare: inserisci 'alessandro' o 'owner@argus.cloud' + password.",
                        )
                        pass_in = st.text_input(
                            "Password",
                            type="password",
                            key="auth_login_pass_input",
                            placeholder="Inserisci la tua password personale...",
                        )
                        btn_login = st.form_submit_button(
                            "🔓 Accedi al Vault ARGUS",
                            type="primary",
                            use_container_width=True,
                        )
                    if btn_login:
                        res = cls.login(user_in, pass_in)
                        if res.get("ok"):
                            st.success(f"✅ Benvenuto, **{res.get('display_name', user_in)}**! Caricamento workspace...")
                            st.rerun()
                        else:
                            st.error(f"❌ Accesso fallito: {res.get('error', 'Credenziali errate.')}")

                    st.markdown(
                        """
                        <div style="margin-top:12px; padding:9px 12px; border-radius:10px;
                                    background:rgba(15,23,42,0.65); border:1px solid rgba(148,163,184,0.16);
                                    font-size:11.5px; color:#94a3b8; line-height:1.45;">
                            <b style="color:#f8fafc;">📌 Profili di Accesso Disponibili:</b><br>
                            • 👑 <b>Titolare (Owner)</b>: Username <code>alessandro</code> o <code>owner@argus.cloud</code> con accesso completo.<br>
                            • 👤 <b>Utente Privato</b>: Iscriviti nella tab <b>➕ Nuovo Account</b> per uno spazio isolato da RLS.<br>
                            • 🧪 <b>Recruiter / Tester</b>: Esplora l'app a 1-click dalla tab <b>🚀 Demo Sandbox</b>.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with tab_reg:
                    st.markdown(
                        "<div style='font-size:12.5px; color:#94a3b8; margin-bottom:12px;'>"
                        "Crea un account privato: i tuoi conti, portafogli e transazioni saranno protetti a livello di database e invisibili agli altri utenti."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    with st.form("argus_auth_register_form_unified", clear_on_submit=False, border=False):
                        r_email = st.text_input("Email o Username univoco *", key="auth_reg_email_in", placeholder="es. marco@gmail.com o marco")
                        r_name = st.text_input("Nome Completo *", key="auth_reg_name_in", placeholder="es. Marco Rossi")
                        r_pwd = st.text_input("Password (min. 6 caratteri) *", type="password", key="auth_reg_pwd_in")
                        btn_reg = st.form_submit_button(
                            "✨ Registra Account & Accedi",
                            type="primary",
                            use_container_width=True,
                        )
                    if btn_reg:
                        res_reg = cls.sign_up(r_email, r_pwd, display_name=r_name)
                        if res_reg.get("ok"):
                            st.success(f"🎉 Account per **{r_name or r_email}** creato con successo!")
                            st.rerun()
                        else:
                            st.error(f"❌ Errore creazione account: {res_reg.get('error')}")

                with tab_guest:
                    st.markdown(
                        "<div style='font-size:12.5px; color:#94a3b8; margin-bottom:12px;'>"
                        "Accesso rapido a 1-click in ambiente <b>Sandbox Isolato</b>: esplora la suite completa di Risk Analytics e Wealth Intelligence con scenari sintetici pre-caricati senza toccare i dati di produzione."
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("🚀 Entra in Modalità Demo Ospite (1-Click)", type="primary", use_container_width=True, key="btn_guest_demo_auth"):
                        cls.login_guest_demo()
                        st.success("✅ Ambiente Demo Sandbox attivato!")
                        st.rerun()
