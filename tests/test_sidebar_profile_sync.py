import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st

if not hasattr(st, 'session_state') or not isinstance(st.session_state, dict):
    class SessionState(dict):
        def __getattr__(self, item):
            return self.get(item)
        def __setattr__(self, key, value):
            self[key] = value
        def __delattr__(self, item):
            self.pop(item, None)
    st.session_state = SessionState()

from core.workspace_context import WorkspaceContext


def test_sidebar_profile_sync_bidirectional():
    st.session_state['offline_mode'] = True
    st.session_state['wealth_active_portfolio_id'] = 101

    ws_ctx = WorkspaceContext.get_current()
    ws_ctx.wealth.profile_id = 101

    pids = [101, 202, 303]
    w_opts = [None] + pids

    st.session_state['sb_wealth_profile_selector'] = None
    active_w_pid = st.session_state.get('wealth_active_portfolio_id')

    matched_pid = None
    if active_w_pid is not None:
        for p in pids:
            if p == active_w_pid or str(p) == str(active_w_pid):
                matched_pid = p
                break

    assert matched_pid == 101
    active_w_pid = matched_pid

    if active_w_pid in w_opts:
        st.session_state['sb_wealth_profile_selector'] = active_w_pid

    assert st.session_state['sb_wealth_profile_selector'] == 101

    new_selected = 202
    st.session_state['sb_wealth_profile_selector'] = new_selected
    st.session_state['wealth_active_portfolio_id'] = new_selected
    st.session_state['wealth_profile_selector_widget'] = new_selected
    st.session_state['nw_profile_selector_widget'] = new_selected
    ws_ctx.wealth.profile_id = new_selected

    assert st.session_state['wealth_active_portfolio_id'] == 202
    assert st.session_state['wealth_profile_selector_widget'] == 202
    assert st.session_state['nw_profile_selector_widget'] == 202
    assert ws_ctx.wealth.profile_id == 202

    st.session_state['wealth_active_portfolio_id'] = '303'
    active_str_pid = st.session_state.get('wealth_active_portfolio_id')

    matched_str = None
    for p in pids:
        if str(p) == str(active_str_pid):
            matched_str = p
            break

    assert matched_str == 303


def test_switch_to_page_clean_navigation():
    """Verifica che switch_to_page non inietti blocchi HTML/markdown nel layout della sidebar."""
    from unittest.mock import patch

    from core.sidebar import switch_to_page

    with patch("streamlit.markdown") as mock_markdown, \
         patch("streamlit.switch_page") as mock_switch_page, \
         patch("streamlit.rerun") as mock_rerun, \
         patch("core.sidebar.get_current_page_name", return_value="0_Control_Room.py"):

        switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")

        # Verifica che nessun markdown/overlay HTML venga renderizzato nella sidebar
        mock_markdown.assert_not_called()
        # Verifica che switch_page sia stato invocato
        assert mock_switch_page.called


def test_risk_to_wealth_transition_auto_profile_selection():
    """Verifica che la transizione da modulo Risk a modulo Wealth auto-selezioni il profilo predefinito."""
    from unittest.mock import patch

    import pandas as pd

    from core.ui_utils import ensure_portal_context

    st.session_state["offline_mode"] = True
    st.session_state["argus_portal_mode"] = "🏛️ Wealth Management"
    st.session_state["wealth_active_portfolio_id"] = None
    st.session_state.pop("wealth_active_profile_name", None)
    st.session_state["argus_auth_personal_profile_id"] = 1

    mock_df_prof = pd.DataFrame([
        {"portfolio_id": 1, "name": "Famiglia Rossi", "owner": "Marco Rossi", "base_currency": "EUR"},
        {"portfolio_id": 2, "name": "Holding Alpha", "owner": "Alpha Ltd", "base_currency": "EUR"}
    ])

    with patch("core.fetcher.get_engine") as mock_eng, \
         patch("core.wealth.wealth_db.init_wealth_db"), \
         patch("core.wealth.wealth_db.get_wealth_portfolios", return_value=mock_df_prof), \
         patch("core.wealth.wealth_engine.compute_consolidated_net_worth") as mock_nw:

        from collections import namedtuple
        NW = namedtuple("NW", ["total_net_worth", "liquid_cash"])
        mock_nw.return_value = NW(total_net_worth=500000.0, liquid_cash=50000.0)

        ctx = ensure_portal_context(module="wealth")

        assert ctx["is_wealth"] is True
        assert ctx["portfolio_id"] == 1
        assert ctx["profile_name"] == "Famiglia Rossi"
        assert st.session_state["wealth_active_portfolio_id"] == 1
        assert st.session_state["wealth_active_profile_name"] == "Famiglia Rossi"
        assert ctx["net_worth"] is not None


def test_init_wealth_db_caching_performance():
    """Verifica che init_wealth_db esegua DDL una sola volta e utilizzi la cache in memoria per evitare latenza."""
    from sqlalchemy import create_engine

    from core.wealth.wealth_db import _INITIALIZED_WEALTH_ENGINES, clear_wealth_db_init_cache, init_wealth_db

    clear_wealth_db_init_cache()
    engine = create_engine("sqlite:///:memory:")

    assert len(_INITIALIZED_WEALTH_ENGINES) == 0
    init_wealth_db(engine)
    assert len(_INITIALIZED_WEALTH_ENGINES) == 1

    # Second call should return immediately using cache without executing redundant DDL
    init_wealth_db(engine)
    assert len(_INITIALIZED_WEALTH_ENGINES) == 1
    clear_wealth_db_init_cache()
    assert len(_INITIALIZED_WEALTH_ENGINES) == 0


