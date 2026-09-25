"""Comprehensive Test Suite for Release v9.17.0 Institutional Engines & API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from core.alm_ldi_engine import compute_alm_ldi_immunization
from core.cds_tranche_engine import compute_cds_and_tranche_pricing
from core.executive_board_pack_engine import generate_executive_board_pack
from core.isda_simm_engine import compute_isda_simm_margin
from core.market_making_vpin_engine import compute_market_making_and_vpin
from core.rough_vol_svi_engine import compute_rough_vol_svi_surface


def test_isda_simm_v26_and_umr_threshold() -> None:
    """Verify ISDA SIMM v2.6 cross-risk-class aggregation, UMR €50M check & CCP MVA savings."""
    res = compute_isda_simm_margin(funding_spread_bps=150.0, mpor_days=10)
    assert res["model_version"] == "ISDA SIMM v2.6"
    assert res["total_simm_initial_margin_eur"] > 0.0
    assert res["gross_undiversified_simm_eur"] >= res["total_simm_initial_margin_eur"]
    assert res["cross_class_diversification_benefit_pct"] > 0.0
    assert res["ccp_cleared_equivalent_im_eur"] < res["total_simm_initial_margin_eur"]
    assert res["annual_ccp_mva_savings_eur"] > 0.0
    assert len(res["risk_class_breakdown"]) == 6


def test_alm_ldi_immunization_and_cashflow_matching_lp() -> None:
    """Verify ALM Funding Ratio, Surplus-at-Risk 99%, LDI Swap overlay & HiGHS LP cash-flow matching."""
    res = compute_alm_ldi_immunization(
        asset_portfolio_eur=140_000_000.0,
        asset_modified_duration=8.5,
        discount_rate=0.035,
    )
    assert res["pv_liabilities_eur"] > 0.0
    assert res["funding_ratio_pct"] > 0.0
    assert res["surplus_at_risk_99_eur"] > 0.0
    lp = res["cashflow_matching_lp"]
    assert lp["lp_converged"] is True
    assert lp["dedicated_bond_portfolio_cost_eur"] > 0.0
    assert len(lp["bond_allocations"]) >= 5


def test_rough_vol_rbergomi_and_svi_arbitrage_free() -> None:
    """Verify Rough Bergomi power-law ATM skew & Gatheral SVI Durrleman butterfly density g(k) >= 0."""
    res = compute_rough_vol_svi_surface(hurst_h=0.10, svi_b=0.18, svi_rho=-0.60, svi_sigma=0.15)
    assert res["hurst_exponent_h"] == 0.10
    assert res["fractal_dimension_d"] == 1.90
    assert res["butterfly_arbitrage_free"] is True
    assert res["calendar_spread_arbitrage_free"] is True
    assert res["totally_arbitrage_free_surface"] is True
    assert abs(res["short_end_skew_1m"]) > abs(res["one_year_skew_12m"])


def test_single_name_cds_and_itraxx_cdo_tranches() -> None:
    """Verify ISDA Standard CDS bootstrapping, upfront, CS01 & 1F Gaussian Copula CDO tranches."""
    res = compute_cds_and_tranche_pricing(
        notional_eur=10_000_000.0,
        recovery_rate=0.40,
        five_year_spread_bps=120.0,
        copula_correlation_rho=0.30,
    )
    assert res["five_year_par_spread_bps"] == 120.0
    assert res["cs01_eur_per_bp"] > 0.0
    assert res["isda_upfront_eur"] > 0.0  # 120 bps > 100 bps standard coupon
    tranches = res["synthetic_cdo_tranches"]
    assert len(tranches) == 5
    # Equity tranche [0-3%] must have higher expected loss and spread than Senior [9-12%]
    assert tranches[0]["expected_loss_pct"] > tranches[3]["expected_loss_pct"]
    assert tranches[0]["fair_running_spread_bps"] > tranches[3]["fair_running_spread_bps"]


def test_avellaneda_stoikov_market_making_and_vpin_hawkes() -> None:
    """Verify Avellaneda-Stoikov inventory reservation price & VPIN/Hawkes toxicity metrics."""
    res_long = compute_market_making_and_vpin(mid_price=40.0, inventory_q=2_000.0)
    res_short = compute_market_making_and_vpin(mid_price=40.0, inventory_q=-2_000.0)
    # Long inventory skews reservation price downward; short inventory skews upward
    assert res_long["reservation_price"] < 40.0 < res_short["reservation_price"]
    assert res_long["optimal_bid_price"] < res_long["reservation_price"] < res_long["optimal_ask_price"]
    assert 0.0 <= res_long["current_vpin_score"] <= 1.0
    assert 0.0 < res_long["hawkes_branching_ratio_eta"] < 1.0


def test_executive_cro_board_pack_generator() -> None:
    """Verify 1-Click Executive CRO & Investment Committee Board-Pack JSON + HTML5 dossier."""
    bp = generate_executive_board_pack(portfolio_name="Test Mandate", nav_eur=150_000_000.0)
    assert bp["app_version"] == "9.17.0"
    assert bp["nav_eur"] == 150_000_000.0
    assert len(bp["cro_prescriptions"]) >= 3
    assert "<!DOCTYPE html>" in bp["board_pack_html"]


def test_v917_api_endpoints_integration() -> None:
    """Verify FastAPI v9.17.0 health version and all 6 new REST endpoints."""
    client = TestClient(app)

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["version"] == "9.17.0"

    r1 = client.post("/api/v1/margin/isda-simm", json={"funding_spread_bps": 140.0})
    assert r1.status_code == 200
    assert "total_simm_initial_margin_eur" in r1.json()

    r2 = client.post("/api/v1/wealth/alm-ldi", json={"asset_portfolio_eur": 130_000_000.0})
    assert r2.status_code == 200
    assert "funding_ratio_pct" in r2.json()

    r3 = client.post("/api/v1/pricing/rough-vol-svi", json={"hurst_h": 0.12})
    assert r3.status_code == 200
    assert r3.json()["totally_arbitrage_free_surface"] is True

    r4 = client.post("/api/v1/credit/cds-tranches", json={"five_year_spread_bps": 110.0})
    assert r4.status_code == 200
    assert "synthetic_cdo_tranches" in r4.json()

    r5 = client.post("/api/v1/execution/market-making-vpin", json={"inventory_q": 1000.0})
    assert r5.status_code == 200
    assert "reservation_price" in r5.json()

    r6 = client.post("/api/v1/reporting/executive-board-pack", json={"nav_eur": 100_000_000.0})
    assert r6.status_code == 200
    assert "board_pack_html" in r6.json()
