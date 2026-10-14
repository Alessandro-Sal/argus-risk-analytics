"""
Unit tests for core/config_manager.py, core/auth_manager.py, and user_integrations in Supabase.
Verifica:
1. Risoluzione configurazione con fallback gerarchico (st.secrets > os.environ > .env).
2. Autenticazione nativa Supabase Auth e session state hardening.
3. Risoluzione credenziali Google Sheets Zero-File in memoria.
4. CRUD tabella user_integrations per Supabase.
"""
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st
from sqlalchemy import create_engine

from core.auth_manager import AuthManager
from core.config_manager import (
    get_gcp_service_account_dict,
    get_setting,
    get_supabase_anon_key,
    get_supabase_url,
    is_auth_required,
    is_guest_demo_enabled,
    is_streamlit_cloud,
)
from core.supabase_cloud import (
    generate_supabase_schema_sql,
    get_supabase_client,
    get_user_integration,
    save_user_integration,
)
from gsheets_sync_subproject.sync_google_sheets import resolve_google_credentials


class TestConfigManager:
    def test_get_setting_fallback_hierarchy(self, monkeypatch):
        # 1. Fallback to default
        monkeypatch.delenv("ARGUS_TEST_VAR", raising=False)
        assert get_setting("ARGUS_TEST_VAR", default="fallback") == "fallback"

        # 2. Env variable takes precedence over default
        monkeypatch.setenv("ARGUS_TEST_VAR", "from_env")
        assert get_setting("ARGUS_TEST_VAR", default="fallback") == "from_env"

        # 3. Streamlit secrets takes precedence over env
        fake_secrets = {"ARGUS_TEST_VAR": "from_secrets"}
        monkeypatch.setattr(st, "secrets", fake_secrets, raising=False)
        assert get_setting("ARGUS_TEST_VAR", default="fallback") == "from_secrets"

    def test_get_setting_type_casting(self, monkeypatch):
        monkeypatch.setenv("ARGUS_BOOL_VAR", "true")
        assert get_setting("ARGUS_BOOL_VAR", cast_type=bool) is True

        monkeypatch.setenv("ARGUS_BOOL_VAR", "0")
        assert get_setting("ARGUS_BOOL_VAR", cast_type=bool) is False

        monkeypatch.setenv("ARGUS_INT_VAR", "42")
        assert get_setting("ARGUS_INT_VAR", cast_type=int) == 42

    def test_is_streamlit_cloud_detection(self, monkeypatch):
        monkeypatch.delenv("STREAMLIT_RUNTIME_ENV", raising=False)
        monkeypatch.delenv("IS_STREAMLIT_CLOUD", raising=False)

        # In local test environment
        assert is_streamlit_cloud() is False

        # When running on Streamlit Cloud
        monkeypatch.setenv("IS_STREAMLIT_CLOUD", "true")
        assert is_streamlit_cloud() is True

    def test_get_gcp_service_account_dict_from_secrets(self, monkeypatch):
        creds = {"type": "service_account", "project_id": "test-p", "private_key": "k", "client_email": "e"}
        fake_secrets = {"gcp_service_account": creds}
        monkeypatch.setattr(st, "secrets", fake_secrets, raising=False)

        res = get_gcp_service_account_dict()
        assert res == creds


class TestAuthManager:
    def test_session_state_lifecycle(self):
        st.session_state.clear()
        assert AuthManager.is_authenticated() is False
        assert AuthManager.get_current_user() is None

        session_data = {
            "ok": True,
            "user_id": "test-uuid-1234",
            "email": "test@argus.cloud",
            "username": "tester",
            "display_name": "Test User",
            "role": "user",
            "access_token": "jwt-token-xyz",
            "refresh_token": "refresh-token-xyz",
            "expires_at": int(time.time()) + 3600,
        }
        AuthManager.apply_session(session_data)
        assert AuthManager.is_authenticated() is True

        current = AuthManager.get_current_user()
        assert current["user_id"] == "test-uuid-1234"
        assert current["role"] == "user"
        assert st.session_state.argus_session["access_token"] == "jwt-token-xyz"

        # Test logout
        AuthManager.logout()
        assert AuthManager.is_authenticated() is False
        assert "argus_session" not in st.session_state

    def test_guest_demo_login(self):
        st.session_state.clear()
        AuthManager.login_guest_demo()
        assert AuthManager.is_authenticated() is True
        assert st.session_state.argus_auth_role == "guest_demo"
        assert st.session_state.offline_mode is True

    def test_auth_guard_authenticated(self):
        st.session_state.clear()
        st.session_state["argus_auth_verified"] = True
        assert AuthManager.auth_guard(show_login_if_unauth=False) is True


class TestUserIntegrationsAndGSheets:
    def test_user_integrations_in_schema_sql(self):
        sql = generate_supabase_schema_sql()
        assert "user_integrations" in sql.lower()
        assert "auth.uid() = user_id" in sql.lower()
        assert "unique(user_id, provider)" in sql.lower()

    def test_save_and_get_user_integration_in_db(self):
        engine = create_engine("sqlite:///:memory:")
        provider = "google_sheets"
        payload = {"type": "service_account", "client_email": "test@service.account"}

        ok = save_user_integration(provider, payload, user_id="user-123", engine=engine)
        assert ok is True

        record = get_user_integration(provider, user_id="user-123", engine=engine)
        assert record is not None
        assert record["provider"] == provider
        assert record["config_data"]["client_email"] == "test@service.account"

    def test_resolve_google_credentials_in_memory_direct(self):
        direct_creds = {
            "type": "service_account",
            "project_id": "test-direct",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC3x...\n-----END PRIVATE KEY-----\n",
            "client_email": "direct@example.com",
        }
        creds, source = resolve_google_credentials(creds_dict=direct_creds)
        assert creds == direct_creds
        assert "In-Memory" in source


class TestAuthHardeningAndUX:
    def test_validate_password_strength(self):
        from core.auth_manager import validate_password_strength

        # Troppo corta (< 10 caratteri)
        ok, msg, score = validate_password_strength("Short1!")
        assert ok is False
        assert score < 100

        # Manca maiuscola
        ok, msg, score = validate_password_strength("lowercase123!@#")
        assert ok is False
        assert "maiuscola" in msg

        # Manca minuscola
        ok, msg, score = validate_password_strength("UPPERCASE123!@#")
        assert ok is False
        assert "minuscola" in msg

        # Manca numero
        ok, msg, score = validate_password_strength("NoNumbersHere!@#")
        assert ok is False
        assert "numero" in msg

        # Manca carattere speciale
        ok, msg, score = validate_password_strength("PlainAlphaNumeric2026")
        assert ok is False
        assert "speciale" in msg

        # Password valida conforme enterprise
        ok, msg, score = validate_password_strength("ArgusEnterprise#2026")
        assert ok is True
        assert score == 100

    def test_auth_rate_limiter_exponential_backoff(self):
        from core.security_engine import AuthRateLimiter

        identity = "test_brute_force_user@argus.cloud"
        AuthRateLimiter.reset(identity)

        # 4 tentativi non causano lockout
        for _ in range(4):
            fails, lock_sec = AuthRateLimiter.record_failure(identity)
            assert lock_sec == 0

        allowed, rem, msg = AuthRateLimiter.check_rate_limit(identity)
        assert allowed is True

        # Il 5° tentativo innesca il blocco temporale (lockout >= 30s)
        fails, lock_sec = AuthRateLimiter.record_failure(identity)
        assert fails == 5
        assert lock_sec >= 30

        allowed, rem, msg = AuthRateLimiter.check_rate_limit(identity)
        assert allowed is False
        assert rem > 0

        # Il successo azzera il lockout
        AuthRateLimiter.record_success(identity)
        allowed, rem, msg = AuthRateLimiter.check_rate_limit(identity)
        assert allowed is True

    def test_auth_view_state_machine(self):
        from core.auth_manager import get_auth_view, set_auth_view

        st.session_state.clear()
        assert get_auth_view() == "LOGIN"

        set_auth_view("FORGOT_PASSWORD")
        assert get_auth_view() == "FORGOT_PASSWORD"

        set_auth_view("RESET_CONFIRM")
        assert get_auth_view() == "RESET_CONFIRM"

        set_auth_view("REGISTER")
        assert get_auth_view() == "REGISTER"

    def test_password_reset_flow(self, monkeypatch):
        st.session_state.clear()
        res_req = AuthManager.request_password_reset("client@institutional.bank")
        assert res_req["ok"] is True
        assert "riceverai" in res_req["message"].lower()

        # Rifiuta password debole nel reset confirm
        res_bad = AuthManager.confirm_password_reset("client@institutional.bank", "123456", "weak")
        assert res_bad["ok"] is False

        # Verifica che un token fittizio venga rifiutato con messaggio opportuno
        res_invalid = AuthManager.confirm_password_reset("client@institutional.bank", "invalid_fake_token", "ArgusSecure#2026")
        assert res_invalid["ok"] is False
        assert "non valido" in res_invalid["error"].lower() or "scaduto" in res_invalid["error"].lower()

        # Verifica il flusso completo di conferma con token validato da Supabase Auth
        class MockAuth:
            def verify_otp(self, params):
                class MockSession:
                    access_token = "mock-tok"
                class MockAuthResponse:
                    session = MockSession()
                    user = {"id": "mock-user"}
                return MockAuthResponse()

            def update_user(self, attributes):
                return {"ok": True}

        class MockClient:
            auth = MockAuth()

        from core import supabase_cloud
        monkeypatch.setattr(AuthManager, "get_supabase_client", lambda access_token=None: MockClient())
        monkeypatch.setattr(supabase_cloud, "get_supabase_client", lambda access_token=None: MockClient())

        res_ok = AuthManager.confirm_password_reset("client@institutional.bank", "123456", "ArgusSecure#2026")
        assert res_ok["ok"] is True

    def test_sandbox_archetype_launch(self):
        st.session_state.clear()
        AuthManager.login_sandbox_archetype("hnwi_family")
        assert AuthManager.is_authenticated() is True
        assert st.session_state.argus_auth_role == "guest_demo"
        assert st.session_state.offline_mode is True
        assert st.session_state.active_archetype_code == "hnwi_family"

    def test_prevent_duplicate_email_registration(self, monkeypatch):
        st.session_state.clear()
        from sqlalchemy import create_engine

        from core.supabase_cloud import SupabaseAuthManager

        test_eng = create_engine("sqlite:///:memory:")
        SupabaseAuthManager.ensure_users_table(test_eng)

        # 1. Registra un primo utente
        res1 = SupabaseAuthManager.create_or_update_user(
            engine=test_eng,
            username="investitore_alpha",
            password="ArgusEnterprise#2026",
            display_name="Mario Rossi",
            email="mario.rossi@argus.cloud",
            allow_update=False,
        )
        assert res1["ok"] is True

        # 2. Tentativo con la STESSA email ma username diverso: deve essere bloccato
        res_dup_email = SupabaseAuthManager.create_or_update_user(
            engine=test_eng,
            username="investitore_beta",
            password="ArgusEnterprise#2026",
            display_name="Mario Clone",
            email="mario.rossi@argus.cloud",
            allow_update=False,
        )
        assert res_dup_email["ok"] is False
        assert "già associato" in res_dup_email["error"].lower()

        # 3. Tentativo con lo STESSO username ma email diversa: deve essere bloccato
        res_dup_user = SupabaseAuthManager.create_or_update_user(
            engine=test_eng,
            username="investitore_alpha",
            password="ArgusEnterprise#2026",
            display_name="Nuovo Mario",
            email="nuova.email@argus.cloud",
            allow_update=False,
        )
        assert res_dup_user["ok"] is False
        assert "già in uso" in res_dup_user["error"].lower()

        # 4. Verifica anti-duplicato GoTrue Auth (identities vuoto o eccezione already registered)
        class MockUserDup:
            identities = []  # GoTrue returns empty identities for duplicate emails

        class MockAuthDup:
            def sign_up(self, params):
                class MockRes:
                    user = MockUserDup()
                    session = None
                return MockRes()

        class MockClientDup:
            auth = MockAuthDup()

        monkeypatch.setattr(AuthManager, "get_supabase_client", lambda access_token=None: MockClientDup())
        monkeypatch.setattr("core.config_manager.get_supabase_anon_key", lambda: "mock_anon_key_valid")
        monkeypatch.setattr("core.config_manager.get_supabase_url", lambda: "https://mock.supabase.co")

        res_gotrue_dup = AuthManager.sign_up("mario.rossi@argus.cloud", "ArgusEnterprise#2026", "Mario Rossi")
        assert res_gotrue_dup["ok"] is False
        assert "già registrato" in res_gotrue_dup["error"].lower()

    def test_logout_flow_and_landing_on_login_gate(self):
        from core.config_manager import is_auth_required
        from core.supabase_cloud import logout_argus_user

        # 1. Autentica una sessione
        AuthManager.login_sandbox_archetype("hnwi_family")
        assert AuthManager.is_authenticated() is True

        # 2. Esegui il logout
        logout_argus_user()

        # 3. Verifica che lo stato sia completamente resettato alla vista LOGIN
        assert AuthManager.is_authenticated() is False
        assert st.session_state.get("auth_view") == "LOGIN"
        assert st.session_state.get("splash_dismissed") is True
        assert st.session_state.get("require_login_forced") is True
        assert is_auth_required() is True

