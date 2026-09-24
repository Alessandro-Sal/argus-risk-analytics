"""
ARGUS — Unit Tests: Terminal Ergonomics & Visual Foundation (Sprint 1 & Sprint 3)
Verifica della persistenza uirevision, cross-chart cursor spikes, skeleton loaders,
e dell'inferenza automatica in render_institutional_datagrid.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from core.chart_framework import apply_argus_theme
from core.ui_utils import (
    render_institutional_datagrid,
    render_skeleton_cards,
    render_skeleton_chart,
    render_skeleton_table,
)


def test_apply_argus_theme_uirevision_and_spikes():
    """Verifica che apply_argus_theme configuri correttamente uirevision e spikelines sincronizzate."""
    fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[10, 20, 15]))
    fig = apply_argus_theme(
        fig,
        title="Test Synchronized Viewport",
        show_spikes=True,
        uirevision="custom_viewport_key",
    )
    assert fig.layout.uirevision == "custom_viewport_key"
    assert fig.layout.hovermode == "x unified"
    assert fig.layout.xaxis.showspikes is True
    assert fig.layout.xaxis.spikemode == "across+toaxis"
    assert fig.layout.xaxis.spikesnap == "cursor"


def test_institutional_datagrid_column_inference(monkeypatch):
    """Verifica che render_institutional_datagrid inferisca correttamente colonne contabili e percentuali."""
    df = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "BND"],
        "Controvalore (€)": [15000.50, 22000.00, 8500.25],
        "Peso (%)": [0.33, 0.48, 0.19],
        "PnL Latente (€)": [1200.5, -450.2, 50.0],
        "Volatilità Annua": [0.24, 0.22, 0.06],
    })

    captured_call = {}

    def mock_render_table_with_export(*args, **kwargs):
        captured_call.update(kwargs)

    monkeypatch.setattr("core.ui_export_utils.render_table_with_export", mock_render_table_with_export)

    render_institutional_datagrid(df, title="Test Portafoglio")

    assert captured_call["table_title"] == "Test Portafoglio"
    assert "Controvalore (€)" in captured_call["currency_cols"]
    assert "PnL Latente (€)" in captured_call["currency_cols"]
    assert "Volatilità Annua" in captured_call["pct_cols"]
    assert "Peso (%)" in captured_call["progress_cols"]
