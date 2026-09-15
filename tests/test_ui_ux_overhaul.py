# ==============================================================================
# tests/test_ui_ux_overhaul.py
# ARGUS Risk Analytics — UI/UX & Terminal Ergonomics Suite Tests
# ==============================================================================
import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from components.command_palette import CATALOG_PAGES, CATALOG_SCENARIOS, HOTKEY_JS_SNIPPET
from components.action_drawers import (
    render_order_blotter_dialog,
    render_lot_inspector_dialog,
    render_risk_decomposition_dialog,
)
from core.chart_framework import apply_argus_theme, lttb_downsample, ObsidianTheme


def test_command_palette_catalog_completeness():
    """Verifica che il catalogo della Command Palette contenga tutte le 22 pagine canoniche."""
    assert len(CATALOG_PAGES) == 22, f"Attese 22 pagine nel catalogo, trovate {len(CATALOG_PAGES)}"
    
    # Verifica che la Control Room e le pagine chiave siano mappate
    page_files = [p["file"] for p in CATALOG_PAGES]
    assert "0_Control_Room.py" in page_files
    assert "pages/1_📈_Dashboard_Generale.py" in page_files
    assert "pages/5_📋_Posizioni_e_Dettagli.py" in page_files
    assert "pages/7_🌪️_Stress_Testing.py" in page_files
    assert "pages/18_📑_Fiscalita_e_Quadro_RW.py" in page_files
    assert "pages/21_🤖_AI_Copilot_e_Advisor.py" in page_files


def test_command_palette_scenarios_and_hotkey():
    """Verifica che siano presenti gli scenari macro e lo snippet di intercettazione Ctrl+K."""
    assert len(CATALOG_SCENARIOS) >= 4
    scenario_codes = [s["code"] for s in CATALOG_SCENARIOS]
    assert "LEHMAN_2008" in scenario_codes
    assert "COVID_2020" in scenario_codes

    assert "keydown" in HOTKEY_JS_SNIPPET
    assert "ctrlKey" in HOTKEY_JS_SNIPPET
    assert "findTriggerButton" in HOTKEY_JS_SNIPPET
    assert "getRootWindow" in HOTKEY_JS_SNIPPET


def test_desktop_packaging_includes_components():
    """Verifica che argus_desktop.spec e build_desktop_app includano il modulo components."""
    with open("argus_desktop.spec", "r", encoding="utf-8") as f:
        spec_text = f.read()
    assert "components" in spec_text
    assert "collect_submodules(\"components\")" in spec_text

    with open("pyproject.toml", "r", encoding="utf-8") as f:
        toml_text = f.read()
    assert 'version = "9.7.0"' in toml_text


def test_action_drawers_callables():
    """Verifica che i drawer modali siano funzioni invocabili conformi a Streamlit."""
    assert callable(render_order_blotter_dialog)
    assert callable(render_lot_inspector_dialog)
    assert callable(render_risk_decomposition_dialog)


def test_chart_framework_unified_hover_and_spikes():
    """Verifica che il Design System dei grafici applichi spikelines e hovermode x unified."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[10, 20, 15], mode="lines"))
    
    styled_fig = apply_argus_theme(
        fig,
        title="Test Chart Ergonomics",
        x_title="Date",
        y_title="NAV (€)",
        hovermode="x unified",
        show_spikes=True,
    )
    
    assert styled_fig.layout.hovermode == "x unified"
    assert styled_fig.layout.xaxis.showspikes is True
    assert styled_fig.layout.xaxis.spikemode == "across"


def test_lttb_downsampling_performance_and_integrity():
    """Verifica che l'algoritmo LTTB downsample una serie densa preservando forma e boundary."""
    n = 5000
    x = np.arange(n)
    y = np.sin(x / 50.0) + np.random.normal(0, 0.05, n)
    
    x_sampled, y_sampled = lttb_downsample(x, y, n_buckets=500)
    assert len(x_sampled) == 500
    assert len(y_sampled) == 500
    # Verifica preservazione estremi
    assert x_sampled[0] == x[0]
    assert x_sampled[-1] == x[-1]
