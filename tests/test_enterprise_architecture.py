"""
tests/test_enterprise_architecture.py
ARGUS — Verification Suite for Enterprise Architecture Overhaul:
1. Single Source of Truth (Risk-Wealth Engine Alignment)
2. Supabase Auth, DotDict & Session Contract
3. Multi-Tenant User Isolation Context
4. In-Memory GSheet Client & Secrets Resolution
5. Supabase Reset SQL Script Validity
"""

import json
import os

import pandas as pd
import pytest
import streamlit as st
from sqlalchemy import create_engine

from core.auth_manager import AuthManager, DotDict
from core.session_manager import ArgusSessionKeys, ArgusSessionManager
from core.wealth.wealth_db import _get_active_user_isolation_context, init_wealth_db
from core.wealth.wealth_engine import compute_consolidated_net_worth
from core.wealth.wealth_sync import get_gspread_client
from core.workspace_context import WorkspaceContext, set_active_portfolio


def test_dot_dict_access_and_aliasing():
    """Verifica che DotDict supporti attributi, chiavi e gli alias id/user_id ed email/user_email."""
    d = DotDict({"id": "uuid-123", "email": "trader@argus.cloud", "role": "user"})
    
    # Accesso per attributo
    assert d.id == "uuid-123"
    assert d.email == "trader@argus.cloud"
    assert d.role == "user"
    assert d.non_existent is None
    
    # Accesso per chiave
    assert d["id"] == "uuid-123"
    assert d["user_id"] == "uuid-123"
    assert d["email"] == "trader@argus.cloud"
    assert d["user_email"] == "trader@argus.cloud"


def test_single_source_of_truth_wealth_risk_alignment():
    """
    Verifica che il Wealth Engine legga direttamente il controvalore da st.session_state['active_portfolio_data']
    senza disallineamenti tra Risk e Wealth.
    """
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    # Impostiamo active_portfolio_data in session_state
    positions_df = pd.DataFrame([
        {"ticker": "NVDA", "current_value": 75000.0, "market_value": 75000.0},
        {"ticker": "BTC", "current_value": 25000.0, "market_value": 25000.0},
    ])
    st.session_state["active_portfolio_id"] = 99
    st.session_state["active_portfolio_data"] = {
        "portfolio": {"portfolio_id": 99, "name": "Active Quant Alpha"},
        "positions": positions_df,
        "equity": 100000.0,
    }

    # Calcolo net worth consolidato
    summary = compute_consolidated_net_worth(engine, portfolio_id=99)
    assert summary.financial_investments == 100000.0
    assert summary.total_net_worth == 100000.0


def test_active_user_isolation_context_with_auth():
    """Verifica che _get_active_user_isolation_context riconosca st.session_state['user']."""
    st.session_state.clear()
    user = DotDict({
        "id": "tenant-uuid-456",
        "username": "client_alpha",
        "email": "client@bank.com",
        "role": "user"
    })
    st.session_state["user"] = user

    uname, disp, enforce = _get_active_user_isolation_context()
    assert uname == "client_alpha"
    assert enforce is True


def test_session_manager_reexports():
    """Verifica che ArgusSessionManager esporti correttamente i metodi e le chiavi del portafoglio attivo."""
    assert hasattr(ArgusSessionKeys, "ACTIVE_PORTFOLIO_ID")
    assert hasattr(ArgusSessionKeys, "ACTIVE_PORTFOLIO_DATA")
    assert hasattr(ArgusSessionManager, "get_active_portfolio_id")
    assert hasattr(ArgusSessionManager, "set_active_portfolio")
    assert hasattr(ArgusSessionManager, "render_portfolio_selector")


def test_supabase_reset_script_integrity():
    """Verifica che lo script SQL di reset contenga TRUNCATE CASCADE, RLS policy e user_integrations."""
    sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql", "01_supabase_schema_and_rls.sql")
    assert os.path.exists(sql_path)
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    assert "TRUNCATE TABLE" in sql
    assert "CASCADE;" in sql
    assert "public.user_integrations" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "auth.uid() = user_id" in sql
    assert "tenant_isolation_policy" in sql


def test_get_available_local_sqlite_dbs():
    """Verifica che il rilevatore di database SQLite identifichi argus_local.db, escluda i cache DB e fornisca metadati."""
    from core.supabase_cloud import get_available_local_sqlite_dbs

    dbs = get_available_local_sqlite_dbs()
    assert len(dbs) > 0

    # argus_local.db deve essere presente e marcato come predefinito
    default_db = next((d for d in dbs if d["is_default"]), None)
    assert default_db is not None
    assert "argus_local.db" in default_db["path"]
    assert default_db["tables_count"] > 0
    assert "portfolios" in default_db["tables"]
    assert "wealth_accounts" in default_db["tables"]

    # I database di cache devono essere esclusi
    for d in dbs:
        assert "cache" not in d["filename"].lower()


def test_get_available_mysql_dbs_info():
    """Verifica che il rilevatore di schemi MySQL elenchi i database escludendo quelli di sistema."""
    from core.supabase_cloud import get_available_mysql_dbs_info

    dbs = get_available_mysql_dbs_info()
    # In ambiente di sviluppo locale MySQL è attivo
    assert isinstance(dbs, list)
    if dbs:
        db_names = [d["name"] for d in dbs]
        # Nessuno schema di sistema deve essere esposto
        for sys_schema in ["information_schema", "mysql", "performance_schema", "sys"]:
            assert sys_schema not in db_names
        # Ogni entry deve avere i campi standard
        for d in dbs:
            assert "tables_count" in d
            assert "estimated_rows" in d
            assert "tables" in d
            assert d["type"] == "mysql"


def test_local_mode_cloud_authentication_gate():
    """
    Verifica che l'accesso locale workstation sia isolato e che la connessione
    a Supabase Cloud rimanga bloccata finché non viene fornito un token JWT Supabase valido.
    """
    from core.auth_manager import AuthManager
    from core.supabase_cloud import get_active_account_badge_info, is_supabase_cloud_authenticated

    # 1. Accesso locale workstation (1-click owner)
    AuthManager.login_local_owner(remember_session=True)
    assert st.session_state["authenticated"] is True
    assert st.session_state["user_id"] == "local-owner"
    assert st.session_state.get("supabase_cloud_authenticated") is False

    # Cloud deve risultare NON autenticato
    assert is_supabase_cloud_authenticated() is False

    badge = get_active_account_badge_info()
    assert badge["badge_label"] == "👑 OWNER (LOCALE)"
    assert "Cloud Protetto" in badge["isolation_desc"]

    # 2. Simulazione autenticazione remota Supabase Cloud riuscita
    st.session_state["supabase_cloud_authenticated"] = True
    st.session_state["user"] = DotDict({
        "id": "4fb12819-68c7-4d92-98b0-5e10014b0402",
        "user_id": "4fb12819-68c7-4d92-98b0-5e10014b0402",
        "email": "alessandro.saladino@live.it",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "role": "owner",
        "username": "alessandro",
        "display_name": "Alessandro (Titolare)",
    })

    assert is_supabase_cloud_authenticated() is True
    badge_cloud = get_active_account_badge_info()
    assert badge_cloud["badge_label"] == "👑 OWNER (CLOUD)"
    assert "Accesso Completo Cloud" in badge_cloud["isolation_desc"]

    # 3. Disconnessione Cloud / Ritorno a Solo Locale
    AuthManager.login_local_owner(remember_session=True)
    assert is_supabase_cloud_authenticated() is False
    badge_local = get_active_account_badge_info()
    assert badge_local["badge_label"] == "👑 OWNER (LOCALE)"

