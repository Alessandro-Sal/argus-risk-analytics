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
    assert "bento-modal-overlay" in html
    assert "bento-modal-toggle" in html
    assert "bento-info-icon" in html
    assert "bento-modal-content" in html

    from core.ui_utils import resolve_metric_knowledge

    bento_titles = [
        "Hurst H & Fractal Dim.",
        "Durrleman Butterfly Min g(k)",
        "ATM Skew 1M (rBergomi)",
        "ATM Skew 12M (1 Anno)",
        "ISDA Upfront (vs 100bps)",
        "CS01 (Credit Spread 01)",
        "Jump-to-Default (JTD Net)",
        "Equity Tranche [0-3%]",
        "ISDA SIMM Initial Margin",
        "Utilizzo Soglia UMR (€50M)",
        "IM Equivalente CCP (LCH/Eurex)",
        "Risparmio Annuo MVA (CCP vs CSA)",
        "Reservation Price r(s,q,t)",
        "Quote Ottime Bid / Ask",
        "VPIN Order-Flow Toxicity",
        "Hawkes Branching Ratio (α/β)",
        "ALM Funding Ratio",
        "Duration Gap (A vs L)",
        "LDI Receiver Swap 20Y",
        "Surplus-at-Risk 99% (1Y)",
    ]
    for bt in bento_titles:
        resolved = resolve_metric_knowledge(bt)
        assert len(resolved) > 2000, f"Card '{bt}' resolved text too short: {len(resolved)}"
        assert "Cos'è" in resolved or "Cosa" in resolved, f"Missing section 1 in '{bt}'"
        assert "Calcolo" in resolved or "calcolat" in resolved, f"Missing section 2 in '{bt}'"
        assert "Come si legge" in resolved or "Valori Guida" in resolved, f"Missing section 4 in '{bt}'"


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


def test_v918_cro_radar_shock_reactivity_and_readiness_score() -> None:
    """Verify compute_executive_traffic_light_radar reacts to Global Macro Shock presets."""
    from core.ux_institutional_hub import compute_executive_traffic_light_radar

    base_radar = compute_executive_traffic_light_radar(session_state_dict={"global_macro_shock": "NONE"})
    assert base_radar["readiness_score"] >= 90
    assert base_radar["breach_count"] == 0
    assert all("utilization_pct" in p and "sparkline" in p and "reg_framework" in p for p in base_radar["pillars"])

    gfc_radar = compute_executive_traffic_light_radar(session_state_dict={"global_macro_shock": "GFC_2008"})
    assert gfc_radar["readiness_score"] < base_radar["readiness_score"]
    assert gfc_radar["breach_count"] >= 2


def test_v918_master_wealth_portfolio_synchronization_and_board_pack_scaling() -> None:
    """Verify Master Wealth (Stocks + Crypto, € 64,233.31) synchronizes top badges, CRO Radar, and Board-Pack euro prescriptions."""
    from core.executive_board_pack_engine import ExecutiveBoardPackEngine
    from core.ux_institutional_hub import compute_executive_traffic_light_radar

    master_wealth_results = {
        "portfolio_value": 64233.31,
        "metrics": {
            "var_95": -0.025,            # 2.50% daily VaR 95% -> 3.45% VaR 99% (BREACH vs 2.50% limit)
            "volatility_annual": 0.285,  # > 25% Vol (Profilo Aggressivo -> SRI 5/7 WARNING)
            "max_drawdown": -0.242,      # > 22% Drawdown
            "sharpe_ratio": 0.17,        # < 0.70 Sharpe Contenuto (WARNING)
            "total_value": 64233.31,
        },
        "positions": [
            {"ticker": "BTC-USD", "market_value": 25000.0},
            {"ticker": "NVDA", "market_value": 20000.0},
            {"ticker": "SPY", "market_value": 19233.31},
        ],
    }

    mw_radar = compute_executive_traffic_light_radar(
        session_state_dict={"global_macro_shock": "NONE"},
        risk_data=master_wealth_results,
    )
    assert abs(mw_radar["nav_eur"] - 64233.31) < 0.01
    assert mw_radar["breach_count"] >= 1
    assert mw_radar["warning_count"] >= 2
    assert mw_radar["readiness_score"] < 75

    engine = ExecutiveBoardPackEngine(
        portfolio_name="Master Wealth (Stocks + Crypto)",
        nav_eur=mw_radar["nav_eur"],
        risk_data=master_wealth_results,
        session_state_dict={"global_macro_shock": "NONE"},
    )
    bp = engine.generate_board_pack()
    # Verify Board-Pack euro prescriptions scale proportionally to € 64,233.31 (neither € 95M nor € 151M)
    assert any("14,131" in str(p.get("action", "")) for p in bp["cro_prescriptions"])
    assert any("49,092" in str(p.get("action", "")) for p in bp["cro_prescriptions"])
    assert "95,536,044" not in bp["board_pack_html"]
    assert "151,428,360" not in bp["board_pack_html"]
    import base64

    assert "RX-CRO-01" in bp["board_pack_html"]
    assert base64.b64decode(bp["board_pack_pdf_base64"]).startswith(b"%PDF")
    assert "RX-CRO-01" in bp["board_pack_audit_json"]

    from core.pdf_generator import generate_institutional_portfolio_factsheet_pdf
    from core.report_exporter import generate_institutional_audit_dossier

    factsheet_pdf = generate_institutional_portfolio_factsheet_pdf(
        portfolio_name="Master Wealth (Stocks + Crypto)",
        risk_data=master_wealth_results,
        base_currency="EUR",
    )
    assert factsheet_pdf.startswith(b"%PDF")

    audit_dossier_pdf = generate_institutional_audit_dossier(
        results=master_wealth_results,
        portfolio_name="Master Wealth (Stocks + Crypto)",
    )
    assert audit_dossier_pdf.startswith(b"%PDF")


def test_v918_kb_resolution_and_sr117_drawers_alignment():
    """Verify that all regulatory stress testing, capital, ESG, and execution metrics resolve to exact KB entries."""
    from core.ui_utils import KNOWN_METRICS_KNOWLEDGE_BASE, resolve_metric_knowledge
    from core.ux_institutional_hub import build_sr117_audit_record

    audit_labels = [
        "Capitale Regolamentare K_IRB",
        "Expected Loss (EL Basilea IRB)",
        "Credit VaR 99.9% (1Y Migration)",
        "Incremental Risk Charge (IRC)",
        "Stress Capital Buffer (SCB)",
        "CET1 Ratio Iniziale",
        "Min CET1 (Severely Adverse)",
        "Perdite Credito Cumulate 9Q",
        "Requisito FRTB Totale",
        "SBM Total Charge",
        "Default Risk Charge (DRC)",
        "Residual Risk (RRAO)",
        "Solvency Ratio",
        "Solvency II SCR Ratio",
        "Requisito SCR Totale",
        "Eligible Own Funds",
        "Intensità WACI Portafoglio",
        "Rischio di Transizione",
        "Rischio Fisico (Danni)",
        "Perdita Climatica Totale",
        "Total Net XVA",
        "Credit Valuation Adj (CVA)",
        "Debit Valuation Adj (DVA)",
        "Funding Valuation Adj (FVA)",
        "PnL Portafoglio Macro",
        "Volatilità Stressata",
        "Perdita di Diversificazione",
        "Drenaggio Liquidità / Margin Call",
        "Summary Risk Indicator (SRI)",
        "PRIIPs VEV (Volatilità)",
        "Classificazione SFDR",
        "Allineamento Tassonomia UE",
        "Regime Struttura a Termine",
        "Futures 1 Anno F(0, 1Y)",
        "Roll Yield Implicito (1Y)",
        "Implementation Shortfall (AC Optimal)",
        "Dynamic VWAP (POV-Capped)",
        "Controvalore Ordine & % ADV",
        "Distanza di Mahalanobis",
        "Days to Liquidate (Medio)",
    ]

    for lbl in audit_labels:
        html_out = resolve_metric_knowledge(lbl)
        # Must contain standard institutional 5-section headers
        assert "📌 Cos'è" in html_out
        assert "⚙️ Come viene calcolat" in html_out or "⚙️ Formula" in html_out
        assert "🎯 A cosa serve" in html_out
        assert "📊 Come si legge" in html_out
        assert "⚠️ Limitazioni" in html_out
        # Must match an exact knowledge base entry title, not the generic dynamic fallback
        matched_title = any(v.get("title", "") in html_out for v in KNOWN_METRICS_KNOWLEDGE_BASE.values())
        assert matched_title, f"Label '{lbl}' failed to match an exact KB entry!"

    # Test SR 11-7 Drawers generation
    rec_frtb = build_sr117_audit_record(
        engine_name="FRTB Basel IV Standardized Approach (BCBS 365 / CRR III) Engine",
        model_version="v9.18.0",
        latex_formulas=[r"K_{\text{FRTB}} = \max [ K_{\text{SBM}} ] + K_{\text{DRC}}"],
        inputs_dict={"trading_val_eur": 50_000_000.0},
        outputs_dict={"total_frtb_charge_eur": 1_250_000.0},
        regulatory_refs=["BCBS 365", "CRR III"],
    )
    assert rec_frtb["engine_name"] == "FRTB Basel IV Standardized Approach (BCBS 365 / CRR III) Engine"
    assert len(rec_frtb["sha256_audit_hash"]) == 64
    assert "BCBS 365" in rec_frtb["regulatory_references"]

    rec_ccar = build_sr117_audit_record(
        engine_name="Fed CCAR & EBA 9-Quarter Supervisory CET1 Stress Engine",
        model_version="v9.18.0",
        latex_formulas=[r"\text{CET1}_{t+1} = \frac{\text{CET1}_t + \text{PPNR}_t - \text{Losses}_t}{\text{RWA}_t}"],
        inputs_dict={"initial_cet1_pct": 14.5},
        outputs_dict={"scb_pct": 2.50},
        regulatory_refs=["Fed CCAR", "EBA Methodology"],
    )
    assert rec_ccar["engine_name"] == "Fed CCAR & EBA 9-Quarter Supervisory CET1 Stress Engine"
    assert len(rec_ccar["sha256_audit_hash"]) == 64




