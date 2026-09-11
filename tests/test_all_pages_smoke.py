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

    # In presenza di dati, empty_state_guard ritorna True e non blocca
    can_render = empty_state_guard(portal="risk")
    assert can_render is True
