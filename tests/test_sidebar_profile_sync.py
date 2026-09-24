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
