import pytest
import pandas as pd
import numpy as np
from core.ui_utils import (
    generate_svg_sparkline,
    render_status_badge,
    render_kpi_metric,
    render_kpi_card,
    render_glassmorphic_card,
    render_page_header,
    render_data_table
)

def test_generate_svg_sparkline_valid():
    data = [10.0, 12.5, 11.0, 14.2, 13.8, 16.0]
    svg = generate_svg_sparkline(data, width=80, height=24)
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "polyline" in svg
    assert "points=" in svg
    assert "circle" in svg
    assert "#10b981" in svg

def test_generate_svg_sparkline_downtrend():
    data = [20.0, 18.0, 15.0, 12.0]
    svg = generate_svg_sparkline(data, width=80, height=24)
    assert "#ef4444" in svg

def test_generate_svg_sparkline_flat():
    data = [10.0, 10.0, 10.0]
    svg = generate_svg_sparkline(data, width=80, height=24)
    assert "<svg" in svg

def test_generate_svg_sparkline_edge_cases():
    assert generate_svg_sparkline([]) == ""
    assert generate_svg_sparkline([5.0]) == ""
    assert generate_svg_sparkline([np.nan, np.nan]) == ""
    assert generate_svg_sparkline([10.0, np.nan, 15.0]) != ""

def test_render_status_badge_levels():
    badge_suc = render_status_badge("OPERATIVO", level="success")
    assert "OPERATIVO" in badge_suc
    assert "#34d399" in badge_suc

    badge_dang = render_status_badge("CRITICO", level="danger")
    assert "CRITICO" in badge_dang
    assert "#f87171" in badge_dang

    badge_warn = render_status_badge("ATTENZIONE", level="warning")
    assert "ATTENZIONE" in badge_warn
    assert "#fbbf24" in badge_warn

    badge_info = render_status_badge("INFO", level="info")
    assert "INFO" in badge_info
    assert "#60a5fa" in badge_info

    badge_pulse = render_status_badge("LIVE", level="success", pulse=True, icon="⚡")
    assert "animation: pulse" in badge_pulse
    assert "⚡" in badge_pulse

def test_render_kpi_metric_and_card_callable():
    render_kpi_metric(
        title="Sharpe Ratio",
        value="1.84",
        delta="+0.24",
        sparkline_data=[1.4, 1.5, 1.6, 1.7, 1.84],
        tooltip="Rapporto rendimento/volatilità",
        subtitle="vs SPY (1.10)",
        level="positive"
    )
    render_kpi_card(
        label="Drawdown Max",
        value="-8.42%",
        delta="-1.20%",
        sentiment="negative",
        help_text="Massima perdita storica",
        sparkline_data=[-5.0, -6.2, -8.42],
        subtitle="Soglia limite: -15%"
    )

def test_render_glassmorphic_card_callable():
    render_glassmorphic_card(
        content_html="<div>Test Content</div>",
        title="Asset Allocation Reale",
        subtitle="Scomposizione per classe",
        badge_text="CONFORME UCITS",
        badge_level="success"
    )

def test_render_page_header_callable():
    render_page_header(
        title="Trading Desk & OMS",
        subtitle="Order Routing TWAP / VWAP",
        icon="🖥️",
        badge_status="MKT OPEN",
        badge_level="success"
    )

def test_render_data_table_with_progress_cols():
    df = pd.DataFrame({
        "Asset": ["AAPL", "MSFT", "NVDA"],
        "Prezzo": [180.5, 420.0, 115.2],
        "Allocazione": [40.0, 35.0, 25.0]
    })
    render_data_table(
        df,
        currency_cols=["Prezzo"],
        progress_cols={"Allocazione": (0.0, 100.0)},
        download_filename="test_export"
    )
