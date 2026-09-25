"""Institutional Test Suite for ARGUS v9.14.0 Major Release.

Covers:
1. Bilateral XVA & Counterparty Credit Risk Engine (CVA, DVA, FVA, MVA, KVA, CSA Netting)
2. Heston Stochastic Volatility Carr-Madan FFT Option Pricing & Calibration Engine
3. Bayesian Black-Litterman Portfolio Optimization Engine with Idzorek Confidence Weighting
4. Basel III Liquidity Risk Engine (LCR, NSFR, HQLA Caps & Cash Flow Stress Ladder)
5. Exotic Derivatives & Worst-Of Structured Products Engine (Phoenix Autocallable & Greeks)
6. Regulatory PRIIPs KID (SRI, VEV, Performance Scenarios) & SFDR ESG (Annex I PAI Table)
7. Headless REST API v9.14.0 Endpoints Integration
"""

import numpy as np
import pytest

from core.basel_liquidity_engine import (
    BaselLiquidityEngine,
    CashFlowItem,
    HQLAComponent,
    compute_basel_liquidity_ratios,
)
from core.black_litterman_engine import (
    BlackLittermanEngine,
    BlackLittermanView,
    compute_black_litterman_allocation,
)
from core.heston_fft_engine import (
    HestonFFTEngine,
    HestonParameters,
    compute_heston_surface_and_calibration,
)
from core.regulatory_reporting_engine import (
    RegulatoryReportingEngine,
    compute_regulatory_dossier,
)
from core.structured_products_engine import (
    StructuredProductsEngine,
    StructuredProductSpecs,
    compute_structured_product_pricing,
)
from core.xva_engine import (
    CSAAgreement,
    TradeItem,
    XVAEngine,
    compute_xva_metrics,
)

# ── Test 1: Bilateral XVA & Counterparty Risk ─────────────────────────

def test_xva_engine_counterparty_risk():
    """Verifies Bilateral XVA calculation, CSA netting set collateralization, and exposure profiles."""
    csa = CSAAgreement(
        has_csa=True,
        threshold_eur=200_000.0,
        mta_eur=50_000.0,
        mpor_days=10,
    )
    trades = [
        TradeItem(
            trade_id="IRS_01",
            symbol="EUR_SWAP_5Y",
            asset_class="IR_SWAP",
            notional_eur=10_000_000.0,
            maturity_years=5.0,
            mtm_eur=75_000.0,
            volatility_annual=0.15,
        ),
        TradeItem(
            trade_id="FX_FWD_01",
            symbol="EUR_USD_1Y",
            asset_class="FX_FORWARD",
            notional_eur=5_000_000.0,
            maturity_years=1.0,
            mtm_eur=-30_000.0,
            volatility_annual=0.12,
        ),
        TradeItem(
            trade_id="OPT_01",
            symbol="SX5E_OPT_2Y",
            asset_class="EQUITY_OPTION",
            notional_eur=2_000_000.0,
            maturity_years=2.0,
            mtm_eur=120_000.0,
            volatility_annual=0.22,
        ),
    ]

    engine = XVAEngine(
        risk_free_rate=0.025,
        counterparty_hazard_rate=0.015,
        own_hazard_rate=0.008,
        funding_spread_bps=45.0,
    )

    report = engine.calculate_xva(trades, csa)

    assert report.portfolio_mtm_eur == 165_000.0
    assert report.cva_eur > 0.0
    assert report.dva_eur > 0.0
    assert report.fva_eur != 0.0
    assert report.mva_eur >= 0.0
    assert report.kva_eur >= 0.0
    assert len(report.exposure_profile_df) > 0
    assert len(report.xva_summary_df) > 0
    assert report.eepe_eur > 0.0

    # Top-level helper test
    res = compute_xva_metrics()
    assert "total_xva_eur" in res
    assert "exposure_profile" in res
    assert len(res["exposure_profile"]) > 0


# ── Test 2: Heston FFT Option Pricing & Calibration ───────────────────

def test_heston_fft_option_pricing_and_calibration():
    """Verifies Carr-Madan FFT option pricer, Feller condition, and volatility surface."""
    params = HestonParameters(
        v0=0.04,
        kappa=2.5,
        theta=0.04,
        sigma_v=0.30,
        rho=-0.70,
    )

    # 2 * 2.5 * 0.04 = 0.20 > 0.30^2 = 0.09 -> Feller satisfied
    assert params.feller_condition_met is True
    assert params.feller_ratio < 1.0

    engine = HestonFFTEngine(s0=100.0, r=0.03, q=0.0)

    strikes = [80.0, 90.0, 100.0, 110.0, 120.0]
    call_prices = engine.price_options_fft(t=1.0, strikes=strikes, params=params)

    # Monotonicity check: call price must decrease with strike
    for i in range(len(call_prices) - 1):
        assert call_prices[i] >= call_prices[i + 1]

    # Put-Call Parity check at ATM (K=100, T=1)
    call_atm = engine.price_call(t=1.0, strike=100.0, params=params)
    put_atm = engine.price_put(t=1.0, strike=100.0, params=params)
    parity_diff = abs((call_atm - put_atm) - (100.0 - 100.0 * np.exp(-0.03 * 1.0)))
    assert parity_diff < 0.10

    # Top-level calibration and surface check
    top_res = compute_heston_surface_and_calibration(s0=100.0)
    assert top_res["feller_test"]["satisfied"] is True
    assert len(top_res["volatility_surface"]["surface_points"]) > 0
    assert "rmse" in top_res["calibration"]


# ── Test 3: Bayesian Black-Litterman Portfolio Optimization ───────────

def test_bayesian_black_litterman_optimization():
    """Verifies equilibrium returns, Idzorek view confidence weighting, and optimal tilts."""
    assets = ["US_Equities", "EU_Equities", "Gov_Bonds", "Gold"]
    cov = np.array([
        [0.0256, 0.0210, -0.0020, 0.0010],
        [0.0210, 0.0324, -0.0015, 0.0015],
        [-0.0020, -0.0015, 0.0036, 0.0005],
        [0.0010, 0.0015, 0.0005, 0.0225],
    ])
    mkt_w = {"US_Equities": 0.50, "EU_Equities": 0.25, "Gov_Bonds": 0.15, "Gold": 0.10}

    engine = BlackLittermanEngine(
        assets=assets,
        cov_matrix=cov,
        market_weights=mkt_w,
        risk_aversion=3.0,
        tau=0.05,
        risk_free_rate=0.02,
    )

    # Implied equilibrium returns Pi
    pi = engine.implied_equilibrium_returns()
    assert len(pi) == 4
    assert pi[0] > pi[2]  # Equities have higher equilibrium return than bonds

    # Views: US will return 10% (confidence 80%), Gold will outperform Gov_Bonds by 4% (confidence 70%)
    views = [
        BlackLittermanView("absolute", ["US_Equities"], [1.0], 0.10, confidence=0.80),
        BlackLittermanView("relative", ["Gold", "Gov_Bonds"], [1.0, -1.0], 0.04, confidence=0.70),
    ]

    report = engine.generate_report(views=views, long_only=True, max_weight=0.55)

    assert sum(report.optimal_weights.values()) == pytest.approx(1.0, abs=1e-3)
    assert report.portfolio_metrics["portfolio_sharpe"] > 0.0
    assert report.portfolio_metrics["tracking_error"] >= 0.0
    assert len(report.summary_table) == 4

    # Top-level calculation
    top_res = compute_black_litterman_allocation()
    assert "optimal_weights" in top_res
    assert "portfolio_metrics" in top_res


# ── Test 4: Basel III Liquidity Standards (LCR & NSFR) ────────────────

def test_basel_iii_liquidity_ratios_and_stress_ladder():
    """Verifies HQLA haircuts & caps, LCR ratio, NSFR ratio, and dynamic cash flow ladder."""
    hqla = [
        HQLAComponent("L1_CASH", "cash", "1", 20_000_000.0, 0.0),
        HQLAComponent("L1_SOV", "sovereign_l1", "1", 50_000_000.0, 0.0),
        HQLAComponent("L2A_CORP", "corp_bond_l2a", "2A", 25_000_000.0, 0.15),
        HQLAComponent("L2B_EQ", "qualifying_equities", "2B", 10_000_000.0, 0.50),
    ]
    outflows = [
        CashFlowItem("OUT_RETAIL", "retail_deposits", 60_000_000.0, 0.05),  # 3M
        CashFlowItem("OUT_WHOLESALE", "wholesale", 20_000_000.0, 1.00),     # 20M
    ]
    inflows = [
        CashFlowItem("IN_LOANS", "maturing_loans", 10_000_000.0, 1.00),     # 10M
    ]

    engine = BaselLiquidityEngine()
    total_hqla, l1, l2a, l2b, ded = engine.calculate_hqla(hqla)

    assert l1 == 70_000_000.0
    assert l2a == 25_000_000.0 * 0.85
    assert l2b == 10_000_000.0 * 0.50
    assert total_hqla > 0.0

    lcr_res = engine.calculate_lcr(hqla, outflows, inflows)
    assert lcr_res["lcr_compliant"] is True
    assert lcr_res["lcr_ratio_pct"] >= 100.0

    ladder, survival_days = engine.compute_stress_ladder(initial_cash=total_hqla)
    assert len(ladder) > 0
    assert survival_days > 0

    # Top-level calculation
    top_res = compute_basel_liquidity_ratios()
    assert top_res["lcr_compliant"] is True
    assert top_res["nsfr_compliant"] is True
    assert top_res["survival_horizon_days"] > 0


# ── Test 5: Structured Products Pricing & Greeks ──────────────────────

def test_structured_products_pricing_and_greeks():
    """Verifies Worst-Of Phoenix Autocallable pricing, Greeks sensitivities, and early redemption probabilities."""
    specs = StructuredProductSpecs(
        product_type="phoenix_autocallable",
        nominal=1000.0,
        maturity_years=2.0,
        observation_frequency_months=6,
        coupon_rate_p_a=0.08,
        has_memory_coupon=True,
        coupon_barrier_pct=0.70,
        autocall_barrier_pct=1.00,
        protection_barrier_pct=0.60,
        underlyings=["SX5E", "SPX"],
        spots=[4000.0, 5000.0],
        volatilities=[0.18, 0.16],
        risk_free_rate=0.03,
    )

    engine = StructuredProductsEngine(specs, n_simulations=4000, seed=123)
    res = engine.evaluate()

    assert 800.0 < res.present_value < 1200.0
    assert 0.0 < res.expected_duration_years <= 2.0
    assert 0.0 <= res.autocall_probability_total <= 1.0
    assert 0.0 <= res.knock_in_loss_probability <= 1.0
    assert len(res.observation_schedule) == 4

    # Greeks validation
    assert isinstance(res.greeks["delta"], float)
    assert isinstance(res.greeks["vega"], float)
    assert isinstance(res.greeks["barrier_sensitivity"], float)

    # Top level calculation
    top_res = compute_structured_product_pricing(n_simulations=2000)
    assert "present_value" in top_res
    assert "greeks" in top_res


# ── Test 6: PRIIPs KID & SFDR Reporting Engine ────────────────────────

def test_regulatory_priips_kid_and_sfdr_reporting():
    """Verifies Cornish-Fisher VEV, SRI matrix, PRIIPs performance scenarios, and SFDR PAI table."""
    engine = RegulatoryReportingEngine()

    rng = np.random.default_rng(99)
    daily_rets = list(rng.normal(0.0004, 0.012, 1000))

    vev = engine.compute_vev(daily_rets)
    assert 0.05 < vev < 0.35

    mrm = engine.determine_mrm(vev)
    assert 1 <= mrm <= 7

    crm = engine.determine_crm("BBB")
    assert crm == 3

    sri = engine.compute_sri(mrm, crm)
    assert 1 <= sri <= 7

    scenarios = engine.compute_performance_scenarios(
        investment_amount=10000.0,
        expected_annual_return=0.07,
        annual_volatility=0.16,
        rhp_years=5.0,
    )
    assert "favourable" in scenarios
    assert "moderate" in scenarios
    assert "unfavourable" in scenarios
    assert "stress" in scenarios

    # Favourable terminal value > Moderate > Unfavourable > Stress
    rhp_key = "5_years"
    assert scenarios["favourable"][rhp_key]["terminal_value_eur"] > scenarios["moderate"][rhp_key]["terminal_value_eur"]
    assert scenarios["moderate"][rhp_key]["terminal_value_eur"] > scenarios["unfavourable"][rhp_key]["terminal_value_eur"]
    assert scenarios["unfavourable"][rhp_key]["terminal_value_eur"] > scenarios["stress"][rhp_key]["terminal_value_eur"]

    pai_table = engine.build_sfdr_pai_table()
    assert len(pai_table) == 14

    top_dossier = compute_regulatory_dossier()
    assert top_dossier["priips_kid"]["sri_score"] in range(1, 8)
    assert len(top_dossier["sfdr_disclosures"]["pai_indicators"]) == 14


# ── Test 7: Headless REST API v9.14.0 Endpoints ───────────────────────

def test_v914_rest_api_endpoints():
    """Verifies all 6 new v9.14.0 endpoints via FastAPI TestClient."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    # Health check
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["version"] == "9.15.0"

    # 1. XVA
    r_xva = client.post("/api/v1/risk/xva", json={})
    assert r_xva.status_code == 200
    assert "cva_eur" in r_xva.json()

    # 2. Heston
    r_heston = client.post("/api/v1/pricing/heston", json={"s0": 100.0})
    assert r_heston.status_code == 200
    assert "heston_parameters" in r_heston.json()

    # 3. Black-Litterman
    r_bl = client.post("/api/v1/optimize/black-litterman", json={})
    assert r_bl.status_code == 200
    assert "optimal_weights" in r_bl.json()

    # 4. Basel Liquidity
    r_basel = client.post("/api/v1/risk/basel-liquidity", json={})
    assert r_basel.status_code == 200
    assert "lcr_ratio_pct" in r_basel.json()

    # 5. Structured Products
    r_struct = client.post("/api/v1/pricing/structured-products", json={"n_simulations": 2000})
    assert r_struct.status_code == 200
    assert "present_value" in r_struct.json()

    # 6. PRIIPs & SFDR
    r_reg = client.post("/api/v1/regulatory/priips-sfdr", json={})
    assert r_reg.status_code == 200
    assert "priips_kid" in r_reg.json()
    assert "sfdr_disclosures" in r_reg.json()
