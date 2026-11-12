"""
Unit tests for Portfolio Selector and Active Session State Synchronization.
Verifies Single Source of Truth (SSOT) alignment between sidebar selector,
command bars/headers, WorkspaceContext, and active portfolio state.
"""

import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class MockStreamlitSessionState(dict):
    """Simulates Streamlit's session_state object supporting attr and dict access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit with an isolated session state dict."""
    st_mock = MagicMock()
    fake_state = MockStreamlitSessionState()
    st_mock.session_state = fake_state
    st_mock.selectbox = MagicMock()
    return st_mock, fake_state


def test_portfolio_selector_sync_with_active_portfolio(monkeypatch, mock_streamlit):
    st_mock, fake_state = mock_streamlit
    monkeypatch.setattr("streamlit.session_state", fake_state)

    # Import target modules
    import core.workspace.context as ctx_mod
    from core.workspace.context import render_portfolio_selector

    # Pre-populate session state with active portfolio "Master Wealth" (id=1)
    fake_state["active_portfolio_id"] = "1"
    fake_state["portfolio_id"] = 1
    fake_state["portfolio_name"] = "Master Wealth Google Sheets"
    fake_state["pipeline_done"] = True
    fake_state["results"] = {"positions": pd.DataFrame()}
    # Crucially, suppose the widget key was previously initialized to None
    fake_state["sb_unified_portfolio_selector"] = None

    # Mock _fetch_user_portfolios_cached to return a couple portfolios
    mock_portfolios = [
        {"portfolio_id": 1, "name": "Master Wealth Google Sheets", "base_currency": "EUR"},
        {"portfolio_id": 2, "name": "Crypto Assets", "base_currency": "EUR"},
    ]
    monkeypatch.setattr(ctx_mod, "_fetch_user_portfolios_cached", lambda *args, **kwargs: mock_portfolios)

    # Capture what st.selectbox receives
    captured_kwargs = {}
    def fake_selectbox(label, options, index=0, format_func=None, key=None, help=None, on_change=None):
        captured_kwargs["label"] = label
        captured_kwargs["options"] = options
        captured_kwargs["index"] = index
        captured_kwargs["format_func"] = format_func
        captured_kwargs["key"] = key
        return options[index]

    monkeypatch.setattr(ctx_mod.st, "selectbox", fake_selectbox)

    # Render selector
    selected = render_portfolio_selector(key="sb_unified_portfolio_selector")

    # Verification:
    # 1. Widget state MUST be updated to 1, NOT left at None!
    assert fake_state["sb_unified_portfolio_selector"] == 1
    # 2. Index in selectbox MUST point to option 1, not 0 (None)
    assert captured_kwargs["index"] == captured_kwargs["options"].index(1)
    # 3. Formatted display of option 1
    fmt_str = captured_kwargs["format_func"](1)
    assert "Master Wealth" in fmt_str
    assert fmt_str != "-- Seleziona Portafoglio --"


def test_portfolio_selector_resolves_from_name_when_id_missing(monkeypatch, mock_streamlit):
    st_mock, fake_state = mock_streamlit
    monkeypatch.setattr("streamlit.session_state", fake_state)

    import core.workspace.context as ctx_mod
    from core.workspace.context import render_portfolio_selector

    # In this scenario, only portfolio_name is in session_state, active_portfolio_id is None
    fake_state["portfolio_name"] = "Master Wealth"
    fake_state["pipeline_done"] = True
    fake_state["results"] = {"positions": pd.DataFrame()}

    mock_portfolios = [
        {"portfolio_id": 10, "name": "Portafoglio Principale", "base_currency": "EUR"},
        {"portfolio_id": 25, "name": "Master Wealth Google Sheets", "base_currency": "EUR"},
    ]
    monkeypatch.setattr(ctx_mod, "_fetch_user_portfolios_cached", lambda *args, **kwargs: mock_portfolios)

    captured_kwargs = {}
    def fake_selectbox(label, options, index=0, format_func=None, key=None, help=None, on_change=None):
        captured_kwargs["options"] = options
        captured_kwargs["index"] = index
        return options[index]

    monkeypatch.setattr(ctx_mod.st, "selectbox", fake_selectbox)

    render_portfolio_selector(key="sb_unified_portfolio_selector")

    # Name "Master Wealth" matches "Master Wealth Google Sheets" (id=25)
    assert fake_state["sb_unified_portfolio_selector"] == 25
    assert fake_state["portfolio_id"] == 25
    assert fake_state["active_portfolio_id"] == "25"
    assert captured_kwargs["index"] == captured_kwargs["options"].index(25)


def test_portfolio_selector_injects_active_session_portfolio_if_missing_from_db(monkeypatch, mock_streamlit):
    st_mock, fake_state = mock_streamlit
    monkeypatch.setattr("streamlit.session_state", fake_state)

    import core.workspace.context as ctx_mod
    from core.workspace.context import render_portfolio_selector

    # Active virtual consolidation in session
    fake_state["portfolio_name"] = "Consolidato Custom Foobar"
    fake_state["pipeline_done"] = True
    fake_state["results"] = {"positions": pd.DataFrame([{"ticker": "AAPL"}])}

    # DB only contains 2 unrelated portfolios
    mock_portfolios = [
        {"portfolio_id": 100, "name": "DB Portfolio A", "base_currency": "EUR"},
        {"portfolio_id": 200, "name": "DB Portfolio B", "base_currency": "EUR"},
    ]
    monkeypatch.setattr(ctx_mod, "_fetch_user_portfolios_cached", lambda *args, **kwargs: mock_portfolios)

    captured_kwargs = {}
    def fake_selectbox(label, options, index=0, format_func=None, key=None, help=None, on_change=None):
        captured_kwargs["options"] = options
        captured_kwargs["index"] = index
        captured_kwargs["format_func"] = format_func
        return options[index]

    monkeypatch.setattr(ctx_mod.st, "selectbox", fake_selectbox)

    render_portfolio_selector(key="sb_unified_portfolio_selector")

    # The active session portfolio must have been inserted into options
    assert fake_state["sb_unified_portfolio_selector"] is not None
    active_opt = fake_state["sb_unified_portfolio_selector"]
    assert captured_kwargs["index"] == captured_kwargs["options"].index(active_opt)
    fmt = captured_kwargs["format_func"](active_opt)
    assert "Consolidato Custom Foobar" in fmt
