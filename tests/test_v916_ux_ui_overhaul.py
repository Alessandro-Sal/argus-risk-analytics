"""Comprehensive Test Suite for v9.16.0 Institutional Terminal UX/UI Overhaul."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from fastapi.testclient import TestClient

from api.main import app
from core.ux_institutional_hub import (
    APP_VERSION,
    build_telemetry_ribbon_state,
    compute_executive_traffic_light_radar,
    compute_scenario_delta_comparison,
    extract_live_portfolio_binding,
    style_institutional_chart,
)


def test_app_version_sync_and_control_room_splash() -> None:
    """Verify APP_VERSION is 9.16.0 and Control Room no longer hardcodes 9.7.0."""
    assert APP_VERSION == "9.17.0"
    ctrl_room_text = Path("src/0_Control_Room.py").read_text(encoding="utf-8")
    assert "render_argus_splash(app_version=APP_VERSION)" in ctrl_room_text
    assert 'render_argus_splash(app_version="9.7.0")' not in ctrl_room_text


def test_telemetry_ribbon_state_extraction_and_regimes() -> None:
    """Verify Pillar 2: Global Telemetry Top-Ribbon state extraction and regime classification."""
    mock_positions = pd.DataFrame(
        {
            "ticker": ["SWDA.MI", "EIMI.MI"],
            "qty_net": [1000.0, 2000.0],
            "last_price": [95.0, 32.5],
            "current_value": [95_000.0, 65_000.0],
        }
    )
    session_normal = {
        "active_portfolio_name": "Family Office Mandato Alpha",
        "last_results": {
            "positions": mock_positions,
            "var_99_pct": 1.65,
            "sharpe_ratio": 1.85,
            "annual_volatility_pct": 11.2,
        },
    }
    tel = build_telemetry_ribbon_state(session_state_dict=session_normal, page_badge="QUANT LAB")
    assert tel["app_version"] == "9.17.0"
    assert tel["nav_eur"] == 160_000.0
    assert tel["var_99_eur"] == round(160_000.0 * 0.0165, 2)
    assert "BULL / NORMAL" in tel["regime_label"]

    session_crisis = {
        "last_results": {
            "total_value": 500_000.0,
            "var_99_pct": 3.80,
            "annual_volatility_pct": 28.5,
        }
    }
    tel_crisis = build_telemetry_ribbon_state(session_state_dict=session_crisis)
    assert "STRESS / HIGH VOL" in tel_crisis["regime_label"]


def test_live_portfolio_auto_binding_extraction() -> None:
    """Verify Pillar 3: 1-Click Live Portfolio Auto-Binding extracts top position and vol."""
    pos_df = pd.DataFrame(
        {
            "ticker": ["MSFT", "ASML.AS"],
            "qty_net": [200.0, 500.0],
            "last_price": [410.0, 890.0],
            "current_value": [82_000.0, 445_000.0],
        }
    )
    rets_df = pd.DataFrame(
        {
            "MSFT": [0.01, -0.01, 0.015, -0.005, 0.02],
            "ASML.AS": [0.02, -0.018, 0.025, -0.012, 0.015],
        }
    )
    bind = extract_live_portfolio_binding(
        session_state_dict={"last_results": {"positions": pos_df, "returns": rets_df}}
    )
    assert bind["has_live_portfolio"] is True
    assert bind["top_ticker"] == "ASML.AS"
    assert bind["top_spot_price"] == 890.0
    assert bind["top_shares"] == 500.0
    assert bind["total_nav_eur"] == 527_000.0
    assert 0.005 <= bind["daily_volatility"] <= 0.06


def test_style_institutional_chart_ergonomics() -> None:
    """Verify Pillar 4: Unified Institutional Plotly Styling & magnetic crosshairs."""
    fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[10, 20, 15], name="Test Series"))
    styled = style_institutional_chart(fig, title="Test Institutional Chart", height=410)
    assert styled.layout.height == 410
    assert styled.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert styled.layout.hovermode == "x unified"
    assert "Test Institutional Chart" in styled.layout.title.text


def test_scenario_pin_and_delta_comparator() -> None:
    """Verify Pillar 5: Scenario Pin & Delta Comparator side-by-side calculation."""
    baseline = {"Sharpe Ratio": 1.20, "VaR 99% (bps)": 180.0, "CET1 Ratio (%)": 11.0}
    current = {"Sharpe Ratio": 1.50, "VaR 99% (bps)": 150.0, "CET1 Ratio (%)": 10.2}
    hib = {"Sharpe Ratio": True, "VaR 99% (bps)": False, "CET1 Ratio (%)": True}

    res = compute_scenario_delta_comparison(baseline, current, hib)
    assert res["has_baseline"] is True
    assert res["metrics_count"] == 3
    assert res["improved_count"] == 2  # Sharpe increased (+), VaR decreased (-)
    by_name = {r["metric"]: r for r in res["comparisons"]}
    assert by_name["Sharpe Ratio"]["status"] == "IMPROVED"
    assert by_name["VaR 99% (bps)"]["status"] == "IMPROVED"
    assert by_name["CET1 Ratio (%)"]["status"] == "DEGRADED"


def test_executive_traffic_light_cro_radar() -> None:
    """Verify Pillar 6: 6-Pillar Executive CRO Traffic-Light Radar Pass/Warning/Breach logic."""
    radar_green = compute_executive_traffic_light_radar()
    assert radar_green["pass_count"] == 6
    assert radar_green["breach_count"] == 0
    assert "GREEN" in radar_green["overall_status"]

    radar_breach = compute_executive_traffic_light_radar(
        metrics_override={"var_99_daily_pct": 3.40, "basel_lcr_pct": 88.0}
    )
    assert radar_breach["breach_count"] >= 2
    assert "RED" in radar_breach["overall_status"]


def test_v916_api_endpoints_and_version() -> None:
    """Verify FastAPI v9.16.0 health version and new UX/UI endpoints."""
    client = TestClient(app)

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["version"] == "9.17.0"

    r_radar = client.post("/api/v1/ux/executive-radar", json={"metrics_override": {"basel_lcr_pct": 135.0}})
    assert r_radar.status_code == 200
    assert len(r_radar.json()["pillars"]) == 6

    r_delta = client.post(
        "/api/v1/ux/scenario-delta",
        json={
            "baseline_metrics": {"NPV": 100.0},
            "current_metrics": {"NPV": 125.0},
            "higher_is_better_map": {"NPV": True},
        },
    )
    assert r_delta.status_code == 200
    assert r_delta.json()["improved_count"] == 1
