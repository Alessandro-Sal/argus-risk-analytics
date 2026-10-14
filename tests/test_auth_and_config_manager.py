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
