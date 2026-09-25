"""Comprehensive Test Suite for v9.15.0 Institutional Engines & FastAPI Endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from core.ccar_stress_engine import compute_ccar_capital_stress
from core.commodity_engine import compute_commodity_term_structure
from core.credit_portfolio_engine import compute_credit_portfolio_risk
from core.hull_white_engine import compute_hull_white_swaptions
from core.multicurve_engine import compute_multicurve_bootstrapping
from core.optimal_liquidation_engine import compute_optimal_execution_schedule


def test_multicurve_ois_bootstrapping_and_basis() -> None:
    """Verify post-LIBOR dual-curve OIS discounting vs forward projection bootstrapping."""
    res = compute_multicurve_bootstrapping(
        currency="EUR",
        notional=10_000_000.0,
        irs_fixed_rate=0.031,
        irs_maturity_years=5.0,
    )
    assert res["currency"] == "EUR"
    irs = res["irs_valuation"]
    assert 1.0 < float(irs["par_swap_rate_pct"]) < 8.0
    assert float(irs["dv01_eur"]) > 0.0
    assert "multicurve_npv_eur" in irs
    tbs = res["basis_swap_valuation"]
    assert float(tbs["fair_basis_spread_3m_vs_6m_bps"]) > 0.0
    assert len(res["ois_curve_nodes"]) >= 5


def test_hull_white_bermudan_swaption_and_callable() -> None:
    """Verify 1-Factor Gaussian Hull-White analytical bond pricing & LSMC Bermudan Swaption."""
    res = compute_hull_white_swaptions(
        notional=10_000_000.0,
        strike_rate=0.030,
        swap_maturity_years=5.0,
        is_payer=True,
        mean_reversion_a=0.05,
        short_rate_vol_sigma=0.01,
        initial_short_rate=0.030,
        n_paths=1500,
    )
    assert float(res["bermudan_swaption_pv_eur"]) > 0.0
    assert float(res["european_swaption_pv_eur"]) > 0.0
    assert float(res["bermudan_swaption_pv_eur"]) >= float(res["european_swaption_pv_eur"])
    assert float(res["early_exercise_premium_eur"]) >= 0.0
    assert float(res["callable_bond_pv_eur"]) <= float(res["straight_bond_pv_eur"])
    assert float(res["embedded_call_option_eur"]) >= 0.0


def test_credit_portfolio_vasicek_and_creditmetrics() -> None:
    """Verify CreditMetrics 8x8 rating migration & Basel II/III IRB Vasicek formula."""
    res = compute_credit_portfolio_risk(n_simulations=3000)
    assert float(res["total_ead_eur"]) > 0.0
    assert float(res["expected_loss_eur"]) > 0.0
    assert float(res["vasicek_irb_capital_999_eur"]) > 0.0
    assert float(res["vasicek_rwa_eur"]) > 0.0
    assert float(res["creditmetrics_var_999_eur"]) >= float(res["creditmetrics_var_99_eur"])
    assert float(res["creditmetrics_es_999_eur"]) >= float(res["creditmetrics_var_999_eur"])
    assert len(res["obligor_contributions"]) >= 5


def test_schwartz_commodity_term_structure_and_spread() -> None:
    """Verify Gibson-Schwartz 2-factor futures curve, Backwardation/Contango & Kirk spread option."""
    res_back = compute_commodity_term_structure(
        spot_price=85.0,
        initial_convenience_yield=0.12,
        long_run_convenience_yield=0.06,
        risk_free_rate=0.03,
        storage_cost_rate=0.02,
        seasonality_amplitude=0.0,
    )
    assert res_back["market_regime"] == "BACKWARDATION"
    assert res_back["one_year_futures_price"] < 85.0
    assert res_back["one_year_roll_yield_pct"] > 0.0
    assert res_back["calendar_spread_option_3m_12m"]["option_price"] >= 0.0

    res_cont = compute_commodity_term_structure(
        spot_price=85.0,
        initial_convenience_yield=-0.04,
        long_run_convenience_yield=-0.02,
        risk_free_rate=0.04,
        storage_cost_rate=0.03,
        seasonality_amplitude=0.0,
    )
    assert res_cont["market_regime"] == "CONTANGO"
    assert res_cont["one_year_futures_price"] > 85.0


def test_optimal_liquidation_sqrt_impact_and_vwap() -> None:
    """Verify Almgren-Chriss Square-Root temporary impact, U-shaped volume & POV-capped VWAP."""
    res = compute_optimal_execution_schedule(
        ticker="ENI.MI",
        order_shares=250_000.0,
        spot_price=14.80,
        adv_shares=5_000_000.0,
        n_slices=13,
        max_pov_cap=0.15,
    )
    assert res["order_notional_eur"] == 250_000.0 * 14.80
    strats = res["strategies"]
    for key in ("almgren_chriss_optimal", "dynamic_vwap", "uniform_twap"):
        assert strats[key]["expected_cost_bps"] > 0.0
        assert strats[key]["timing_risk_std_bps"] >= 0.0
        assert strats[key]["inventory_path"][0] == 250_000.0
        assert abs(strats[key]["inventory_path"][-1]) < 1.0
    assert len(res["intraday_schedule"]) == 13


def test_ccar_9quarter_capital_stress_trajectory() -> None:
    """Verify Fed CCAR / EBA 9-quarter CET1 capital stress across Baseline, Adverse, Severely Adverse."""
    res = compute_ccar_capital_stress(
        initial_cet1_capital_eur_m=14_200.0,
        initial_rwa_eur_m=100_000.0,
        total_loan_book_eur_m=145_000.0,
    )
    scens = res["scenarios"]
    base_min = scens["baseline"]["minimum_stressed_cet1_ratio_pct"]
    adv_min = scens["adverse"]["minimum_stressed_cet1_ratio_pct"]
    sev_min = scens["severely_adverse"]["minimum_stressed_cet1_ratio_pct"]

    assert base_min > adv_min > sev_min
    assert len(scens["severely_adverse"]["trajectory"]) == 9
    assert res["required_stress_capital_buffer_scb_pct"] >= 2.5


def test_v915_api_endpoints_integration() -> None:
    """Verify all 6 new v9.15.0 REST API routes and OpenAPI version 9.15.0."""
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["version"] == "9.17.0"

    r1 = client.post("/api/v1/pricing/multicurve", json={"currency": "EUR", "notional": 5_000_000.0})
    assert r1.status_code == 200
    assert "irs_valuation" in r1.json()

    r2 = client.post("/api/v1/pricing/hull-white", json={"n_paths": 1000})
    assert r2.status_code == 200
    assert "bermudan_swaption_pv_eur" in r2.json()

    r3 = client.post("/api/v1/risk/credit-portfolio", json={"n_simulations": 2000})
    assert r3.status_code == 200
    assert "vasicek_irb_capital_999_eur" in r3.json()

    r4 = client.post("/api/v1/pricing/commodity", json={"spot_price": 80.0})
    assert r4.status_code == 200
    assert "term_structure" in r4.json()

    r5 = client.post("/api/v1/execution/optimal-liquidation", json={"order_shares": 100_000.0})
    assert r5.status_code == 200
    assert "strategies" in r5.json()

    r6 = client.post("/api/v1/stress/ccar-capital", json={"initial_cet1_capital_eur_m": 15_000.0})
    assert r6.status_code == 200
    assert "scenarios" in r6.json()
