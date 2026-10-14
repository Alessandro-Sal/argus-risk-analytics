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
    sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "supabase_reset_and_rls.sql")
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

