"""
Unit tests for core/workspace_manager.py
Tests URL Query Parameter state synchronization, session snapshot caching/restoration,
and in-app workspace tab management.
"""

import os
import json
import pandas as pd
import pytest
import streamlit as st

from core.workspace_manager import (
    get_url_param,
    set_url_params,
    save_session_snapshot_to_cache,
    try_restore_session_from_cache,
    sync_url_state,
    get_workspace_tabs,
    register_workspace_tab,
    close_workspace_tab,
    set_active_workspace,
    WORKSPACE_CACHE_PKL
)


def test_url_params_helper():
    """Test safe read and write of query parameters."""
    set_url_params(ticker="AAPL", test_mode="1")
    assert get_url_param("ticker") == "AAPL"
    assert get_url_param("test_mode") == "1"
    assert get_url_param("non_existent", "default_val") == "default_val"


def test_workspace_tab_lifecycle():
    """Test adding, switching, and closing workspace tabs."""
    # Reset session tabs
    if "workspace_tabs" in st.session_state:
        del st.session_state["workspace_tabs"]
    if "active_workspace_id" in st.session_state:
        del st.session_state["active_workspace_id"]

    tabs = get_workspace_tabs()
    assert len(tabs) >= 1

    # Register new tab
    register_workspace_tab("test_tech_nvda", "📈 NVDA · Tecnico", "8_Analisi_Tecnica", {"ticker": "NVDA"})
    tabs_after = get_workspace_tabs()
    assert any(t["id"] == "test_tech_nvda" for t in tabs_after)
    assert st.session_state.active_workspace_id == "test_tech_nvda"

    # Switch active tab
    set_active_workspace("main_portfolio")
    assert st.session_state.active_workspace_id == "main_portfolio"

    # Close unpinned tab
    close_workspace_tab("test_tech_nvda")
    tabs_closed = get_workspace_tabs()
    assert not any(t["id"] == "test_tech_nvda" for t in tabs_closed)


def test_session_snapshot_save_and_restore(tmp_path):
    """Test saving session snapshot to disk cache and restoring it."""
    test_df = pd.DataFrame([
        {"ticker": "NVDA", "asset_class": "Stock", "weight_pct": 50.0, "qty_net": 10, "current_value": 1200.0},
        {"ticker": "AAPL", "asset_class": "Stock", "weight_pct": 50.0, "qty_net": 10, "current_value": 2200.0}
    ])

    st.session_state["results"] = {
        "positions": test_df,
        "metrics": {"cagr_pct": 22.5, "sharpe_ratio": 1.45, "var_95_pct": 5.2}
    }
    st.session_state["portfolio_name"] = "TechGrowth"
    st.session_state["run_id"] = "TEST_RUN_101"

    # Save to cache
    save_session_snapshot_to_cache()
    assert os.path.exists(WORKSPACE_CACHE_PKL)

    # Clear memory
    del st.session_state["results"]
    assert "results" not in st.session_state

    # Restore from cache
    restored = try_restore_session_from_cache()
    assert restored is True
    assert "results" in st.session_state
    assert isinstance(st.session_state["results"]["positions"], pd.DataFrame)
    assert len(st.session_state["results"]["positions"]) == 2
    assert st.session_state.get("portfolio_name") == "TechGrowth"


def test_sync_url_state():
    """Test sync_url_state execution without errors."""
    st.session_state["results"] = {
        "positions": pd.DataFrame([{"ticker": "MSFT", "weight_pct": 100.0}]),
        "metrics": {}
    }
    st.session_state["portfolio_name"] = "Portfolio Alpha"
    st.session_state["run_id"] = "ALPHA_RUN"

    sync_url_state()
    assert get_url_param("portfolio") == "Portfolio Alpha"
    assert get_url_param("run_id") == "ALPHA_RUN"


def test_resolve_page_path():
    """Test mapping and resolution of page filepaths for st.page_link."""
    from core.workspace_manager import resolve_page_path
    assert resolve_page_path("8_Analisi_Tecnica") == "pages/8_📈_Analisi_Tecnica.py"
    assert resolve_page_path("1_Dashboard_Generale") == "pages/1_📈_Dashboard_Generale.py"
    assert resolve_page_path("0_Control_Room") == "0_Control_Room.py"
    assert resolve_page_path("pages/2_🔴_Analisi_Rischio.py") == "pages/2_🔴_Analisi_Rischio.py"
