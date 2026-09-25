"""Comprehensive test suite for ARGUS Release v9.18.0 Institutional UX/UI & Visual Quant Canvas."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from core.ux_institutional_hub import (
    APP_VERSION,
    apply_macro_shock_to_inputs,
    build_bento_kpi_card_html,
    build_sr117_audit_record,
    build_svg_sparkline,
    get_active_macro_shock,
    get_density_mode_css,
    resolve_terminal_command,
)
from core.ux_quant_canvas import (
    build_alm_cashflow_and_surplus_chart,
    build_avellaneda_stoikov_microstructure_chart,
    build_cds_bootstrap_and_tranche_chart,
    build_isda_simm_waterfall_and_umr_chart,
    build_svi_3d_surface_and_density_chart,
)


def test_v918_app_version_and_command_bar_resolver() -> None:
    """Verify APP_VERSION is 9.18.0 and Bloomberg <GO> command bar resolves exact and fuzzy commands."""
    assert APP_VERSION == "9.18.0"

    simm_cmd = resolve_terminal_command("SIMM <GO>")
    assert simm_cmd["matched"] is True
    assert simm_cmd["command_key"] == "SIMM"
    assert "7_🌪️_Stress_Testing.py" in simm_cmd["target_page"]

    svi_cmd = resolve_terminal_command("svi")
    assert svi_cmd["matched"] is True
    assert svi_cmd["command_key"] == "SVI"

    shock_cmd = resolve_terminal_command("SHOCK 2008 <GO>")
    assert shock_cmd["matched"] is True
    assert shock_cmd["macro_shock"] == "GFC_2008"


def test_v918_global_macro_shock_broadcast_synchronizer() -> None:
    """Verify cross-page macro shock broadcast modifies engine inputs deterministically."""
    base = {
        "discount_rate": 0.034,
        "index_spread_bps": 100.0,
        "annual_vol": 0.15,
        "asset_value": 100_000_000.0,
    }
    normal = apply_macro_shock_to_inputs(base, session_state_dict={"global_macro_shock": "NONE"})
    assert normal["macro_shock_active"] is False
    assert normal["index_spread_bps"] == 100.0

    stag = apply_macro_shock_to_inputs(base, session_state_dict={"global_macro_shock": "STAGFLATION_SHOCK"})
    assert stag["macro_shock_active"] is True
    assert stag["discount_rate"] > base["discount_rate"]
    assert stag["index_spread_bps"] == 260.0
    assert stag["annual_vol"] > base["annual_vol"]
    assert stag["asset_value"] < base["asset_value"]


def test_v918_bento_kpi_cards_and_svg_sparklines() -> None:
    """Verify SVG micro-sparklines and Bento KPI HTML cards with limit bars & provenance badges."""
    svg = build_svg_sparkline([10.0, 12.5, 11.8, 15.2], color="#10b981")
    assert "<svg" in svg and "<polyline" in svg

    html = build_bento_kpi_card_html(
        title="ISDA SIMM Initial Margin",
        value="€ 38.4M",
        delta_label="Diversification: -28.4%",
        provenance="GLOBAL SHOCK OVERRIDE",
        limit_utilization_pct=76.8,
        sparkline_values=[30.0, 32.0, 35.5, 38.4],
        accent_color="#3b82f6",
    )
    assert "argus-bento-card" in html
    assert "GLOBAL SHOCK OVERRIDE" in html
    assert "76.8%" in html
    assert "<svg" in html


def test_v918_sr117_audit_record_and_adaptive_density_css() -> None:
    """Verify deterministic SHA-256 audit trail record and density CSS modes."""
    rec1 = build_sr117_audit_record(
        engine_name="Rough Bergomi SVI",
        model_version="9.18.0",
        latex_formulas=[r"w(k) = a + b(\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2})"],
        inputs_dict={"h": 0.10, "rho": -0.62},
        outputs_dict={"min_g": 0.142},
    )
    rec2 = build_sr117_audit_record(
        engine_name="Rough Bergomi SVI",
        model_version="9.18.0",
        latex_formulas=[r"w(k) = a + b(\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2})"],
        inputs_dict={"h": 0.10, "rho": -0.62},
        outputs_dict={"min_g": 0.142},
    )
    assert len(rec1["sha256_audit_hash"]) == 64
    assert rec1["sha256_audit_hash"] == rec2["sha256_audit_hash"]

    desk_css = get_density_mode_css("COMPACT_DESK")
    board_css = get_density_mode_css("BOARDROOM")
    assert "1.35rem" in desk_css
    assert "1.85rem" in board_css


def test_v918_visual_quant_canvas_3d_and_2d_figures() -> None:
    """Verify all 5 Visual Quant Canvas Plotly figure builders produce valid traces."""
    fig_3d, fig_dens = build_svi_3d_surface_and_density_chart(
        {"calibrated_params": {"a": 0.015, "b": 0.18, "rho": -0.6, "m": 0.01, "sigma": 0.15}, "maturity_years": 0.25},
        {"hurst_h": 0.10},
    )
    assert len(fig_3d.data) == 1
    assert fig_3d.data[0].type == "surface"
    assert len(fig_dens.data) >= 2

    fig_simm = build_isda_simm_waterfall_and_umr_chart(
        {
            "risk_class_breakdown": {"IR": {"total_margin": 22_000_000.0}, "Equity": {"total_margin": 14_000_000.0}},
            "standalone_sum_eur": 36_000_000.0,
            "total_simm_im_eur": 28_500_000.0,
            "ccp_cleared_im_eur": 19_200_000.0,
            "umr_threshold_eur": 50_000_000.0,
        }
    )
    assert any(tr.type == "waterfall" for tr in fig_simm.data)

    fig_alm = build_alm_cashflow_and_surplus_chart({})
    assert len(fig_alm.data) == 3

    fig_cds, fig_tr = build_cds_bootstrap_and_tranche_chart({}, {})
    assert len(fig_cds.data) == 2
    assert len(fig_tr.data) == 2

    fig_mm = build_avellaneda_stoikov_microstructure_chart({"mid_price": 100.0, "inventory_units": 1500.0})
    assert len(fig_mm.data) == 3


def test_v918_api_command_dispatch_endpoint() -> None:
    """Verify FastAPI /api/v1/ux/command-dispatch endpoint."""
    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/ux/command-dispatch",
        json={"command": "SHOCK 2008 <GO>", "base_inputs": {"index_spread_bps": 100.0}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "9.18.0"
    assert data["command_resolution"]["command_key"] == "SHOCK 2008"
    assert data["shocked_inputs"]["macro_shock_active"] is True
    assert data["shocked_inputs"]["index_spread_bps"] == 450.0


def test_v918_telemetry_ribbon_html_no_codeblock_indentation() -> None:
    """Ensure build_telemetry_ribbon_html never contains blank lines or 4-space CommonMark code blocks."""
    from core.ux_institutional_hub import build_telemetry_ribbon_html, build_telemetry_ribbon_state

    tel = build_telemetry_ribbon_state(page_badge="CONTROL ROOM & EXECUTIVE LAUNCHPAD")
    html_no_shock = build_telemetry_ribbon_html(tel, {"is_active": False, "label": "NONE"})
    assert "\n" not in html_no_shock
    assert "NAV:" in html_no_shock and "BULL / NORMAL" in html_no_shock

    html_shock = build_telemetry_ribbon_html(tel, {"is_active": True, "label": "GFC 2008"})
    assert "\n" not in html_shock
    assert "⚡ SHOCK: GFC 2008" in html_shock

