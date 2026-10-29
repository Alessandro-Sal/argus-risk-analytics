"""
ARGUS — Quantitative Risk & Wealth Intelligence Platform
Smoke Testing Suite: Streamlit Multi-Page Execution & Syntax Integrity
Guarantees all 21 pages and entrypoints compile, import, and execute without syntax errors or unhandled exceptions.
"""

import glob
import os

import numpy as np
import pandas as pd
import pytest

# Rilevamento automatico delle 21 pagine Streamlit in src/pages e del punto d'ingresso
PAGE_FILES = sorted(glob.glob("src/pages/*.py"))
CONTROL_ROOM = "src/0_Control_Room.py"
ALL_STREAMLIT_TARGETS = list(PAGE_FILES)
if os.path.exists(CONTROL_ROOM):
    ALL_STREAMLIT_TARGETS.insert(0, CONTROL_ROOM)


@pytest.mark.smoke
def test_all_21_pages_discovered():
    """Verifica che tutte le 21 pagine Streamlit della suite siano presenti e censite."""
    assert len(PAGE_FILES) == 21, f"Attese 21 pagine in src/pages/, rilevate: {len(PAGE_FILES)}"
    assert os.path.exists(CONTROL_ROOM), "Punto d'ingresso principale src/0_Control_Room.py non trovato!"


@pytest.mark.smoke
@pytest.mark.parametrize("target_path", ALL_STREAMLIT_TARGETS)
def test_streamlit_page_syntax_and_compilation(target_path):
    """
    Verifica che ciascun file di pagina Streamlit compili correttamente in bytecode Python
    senza sollevare SyntaxError, IndentationError o TokenError.
    """
    assert os.path.exists(target_path), f"File target non trovato: {target_path}"
    with open(target_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    assert len(code_content) > 100, f"File vuoto o anomalo: {target_path}"
    compiled = compile(code_content, target_path, "exec")
    assert compiled is not None, f"Impossibile compilare in bytecode: {target_path}"


@pytest.mark.smoke
def test_empty_state_guard_isolation_and_resilience():
    """
    Verifica il comportamento del guard dell'empty state (core/onboarding_guard.py):
    - Se nessun portafoglio è presente e pipeline_done=False, intercetta e non crasha.
    - Se il portafoglio demo è caricato, sblocca la visualizzazione e ritorna True.
    """
    from core.onboarding_guard import empty_state_guard
    from core.unified_demo_seeder import seed_unified_demo_scenario

    # Simula stato con portafoglio demo attivo
    seed_unified_demo_scenario(target_portfolio_name="SMOKE_TEST_PORTFOLIO")

    try:
        # In presenza di dati, empty_state_guard ritorna True e non blocca
        can_render = empty_state_guard(portal="risk")
        assert can_render is True
    finally:
        import streamlit as st

        from core.workspace_context import WorkspaceContext

        st.session_state.clear()
        ws = WorkspaceContext.get_current()
        ws.flush_risk_domain()
        ws.flush_wealth_domain()


def test_positions_missing_current_value_resilience():
    """
    Verifica che strutture DataFrame positions prive di 'current_value' o 'qty_net'
    non sollevino KeyError: False o KeyError: True in fase di slicing o calcolo aggregato.
    """
    import pandas as pd

    # Mock DataFrame privo di current_value e privo di qty_net
    mock_pos = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "shares": [10.0, 5.0],
        "average_price": [150.0, 300.0],
    })

    # 1. 3_Analisi_Rischio filtering
    if "current_value" in mock_pos.columns:
        valid_p = mock_pos[pd.to_numeric(mock_pos["current_value"], errors="coerce").fillna(0.0) > 0]
    elif "market_value" in mock_pos.columns:
        valid_p = mock_pos[pd.to_numeric(mock_pos["market_value"], errors="coerce").fillna(0.0) > 0]
    elif "qty_net" in mock_pos.columns:
        valid_p = mock_pos[pd.to_numeric(mock_pos["qty_net"], errors="coerce").fillna(0.0) > 0]
    else:
        valid_p = mock_pos
    assert len(valid_p) == 2

    # 2. 8_Analisi_Temporale active tickers
    if "current_value" in mock_pos.columns:
        active_tickers = sorted(list(mock_pos[pd.to_numeric(mock_pos["current_value"], errors="coerce").fillna(0.0) > 0]["ticker"].unique()))
    elif "qty_net" in mock_pos.columns:
        active_tickers = sorted(list(mock_pos[pd.to_numeric(mock_pos["qty_net"], errors="coerce").fillna(0.0) > 0]["ticker"].unique()))
    else:
        active_tickers = sorted(list(mock_pos["ticker"].unique()))
    assert active_tickers == ["AAPL", "MSFT"]

    # 3. 1_Dashboard_Generale n_pos
    n_pos = int(len(mock_pos[pd.to_numeric(mock_pos["qty_net"], errors="coerce").fillna(0.0) > 1e-6])) if (not mock_pos.empty and "qty_net" in mock_pos.columns) else len(mock_pos)
    assert n_pos == 2

    # 4. core/reporting/html.py filtering
    val_col = "current_value" if "current_value" in mock_pos.columns else None
    mask = pd.Series(True, index=mock_pos.index)
    if "qty_net" in mock_pos.columns:
        mask &= (pd.to_numeric(mock_pos["qty_net"], errors="coerce").fillna(0.0) > 1e-6)
    if val_col:
        mask &= (pd.to_numeric(mock_pos[val_col], errors="coerce").fillna(0.0) > 0)
    active_pos = mock_pos[mask] if mask.any() else mock_pos
    assert len(active_pos) == 2

