# ==============================================================================
# tests/test_ui_ux_overhaul.py
# ARGUS Risk Analytics — UI/UX & Terminal Ergonomics Suite Tests
# ==============================================================================
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from components.action_drawers import (
    render_lot_inspector_dialog,
    render_order_blotter_dialog,
    render_risk_decomposition_dialog,
)
from components.command_palette import CATALOG_PAGES, CATALOG_SCENARIOS, HOTKEY_JS_SNIPPET
from core.chart_framework import ObsidianTheme, apply_argus_theme, lttb_downsample


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
    assert 'version = "9.11.0"' in toml_text


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
    assert styled_fig.layout.xaxis.spikemode == "across+toaxis"


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


def test_action_drawers_dynamic_portfolio_binding():
    """Verifica che i drawer modali si leghino dinamicamente alle posizioni effettive del portafoglio."""
    from components.action_drawers import _get_active_portfolio_context

    custom_pos = pd.DataFrame([
        {"ticker": "ENEL.MI", "qty_net": 100, "last_price": 6.80, "current_value": 680.0, "asset_class": "Equity"},
        {"ticker": "ISP.MI", "qty_net": 200, "last_price": 3.40, "current_value": 680.0, "asset_class": "Equity"},
        {"ticker": "BTP-10Y", "qty_net": 10, "last_price": 100.50, "current_value": 1005.0, "asset_class": "Fixed Income / Bond"},
    ])

    df_pos, res, tot_val, port_name = _get_active_portfolio_context(positions=custom_pos)
    assert len(df_pos) == 3
    assert set(df_pos["ticker"].tolist()) == {"ENEL.MI", "ISP.MI", "BTP-10Y"}
    assert tot_val == 2365.0


def test_order_blotter_crypto_and_no_shorting():
    """Verifica che il blotter ordini gestisca le crypto in modo frazionato e non generi vendite superiori alle quote possedute."""
    from unittest.mock import MagicMock, patch

    from components.action_drawers import render_order_blotter_dialog

    pos = pd.DataFrame([
        {"ticker": "BTC-EUR", "qty_net": 0.0848, "last_price": 65530.66, "current_value": 5557.0, "asset_class": "Crypto", "wacp": 75000.0},
        {"ticker": "GOOGL", "qty_net": 10.0, "last_price": 158.55, "current_value": 1585.5, "asset_class": "Equity", "wacp": 140.0},
    ])

    fn = getattr(render_order_blotter_dialog, "__wrapped__", render_order_blotter_dialog)
    with patch("streamlit.dataframe") as mock_df, \
         patch("streamlit.columns", side_effect=lambda x: [MagicMock()] * (len(x) if isinstance(x, list) else x)), \
         patch("streamlit.caption"), patch("streamlit.markdown"), patch("streamlit.info"), \
         patch("streamlit.divider"), patch("streamlit.radio"), patch("streamlit.button"), \
         patch("streamlit.metric"):
        fn(portfolio_value=7142.5, positions=pos)
        assert mock_df.called
        df_result = mock_df.call_args[0][0]

        btc_row = df_result[df_result["Ticker"] == "BTC-EUR"]
        assert not btc_row.empty
        btc_order = btc_row.iloc[0]
        assert btc_order["Azione"] == "SELL"
        # La quantità venduta deve essere frazionata e rigorosamente <= a quanto posseduto (0.0848)
        qty_sold = float(btc_order["Quantità"])
        assert 0.0 < qty_sold <= 0.0848
        assert btc_order["Controvalore"] < 5557.0
        assert "IT_BTC-EUR_01" not in btc_order["ISIN"]

