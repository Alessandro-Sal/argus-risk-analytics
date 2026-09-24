"""
tests/test_v913_institutional_suite.py
Institutional Test Suite for ARGUS v9.13.0 Major Release:
1. FRTB Standardized Approach (BCBS 365 / Basel IV)
2. SABR Model Calibration & Dupire Local Volatility Surface (PDE)
3. NGFS Phase IV Climate Transition & Physical Risk Stress Engine
4. Multi-Venue Smart Order Router & MiFID II RTS 28 Best Execution
5. Private Markets Cash Flow Pacing (Takahashi-Alexander) & Geltner De-smoothing
6. Interactive Macro War Room & Systemic Correlation Breakdown
7. Headless REST API v9.13.0 Endpoints Integration
"""

import numpy as np
import pandas as pd
import pytest

# ── Test 1: FRTB Standardized Approach (BCBS 365) ────────────────────

def test_frtb_standardized_approach():
    from core.frtb_engine import FrtbStandardizedEngine, compute_frtb_capital_charges

    engine = FrtbStandardizedEngine(total_portfolio_value=100_000_000.0)
    rep_med = engine.calculate_capital_requirements(correlation_scenario="MEDIUM")
    rep_high = engine.calculate_capital_requirements(correlation_scenario="HIGH")
    rep_low = engine.calculate_capital_requirements(correlation_scenario="LOW")

    # Assertions on capital charges
    assert rep_med.total_frtb_capital_charge_eur > 0
    assert rep_med.sbm_total_charge_eur > 0
    assert rep_med.drc_total_charge_eur > 0
    assert rep_med.rrao_total_charge_eur > 0
    assert rep_med.capital_ratio_pct > 0.0

    # High correlation scenario should produce equal or higher SBM charge due to correlation aggregation
    assert rep_high.sbm_total_charge_eur >= rep_low.sbm_total_charge_eur * 0.90

    # Functional API check
    api_res = compute_frtb_capital_charges(total_portfolio_value=50_000_000.0)
    assert "total_frtb_capital_charge_eur" in api_res
    assert "sbm_breakdown_by_risk_class" in api_res
    assert len(api_res["sbm_breakdown_by_risk_class"]) > 0


# ── Test 2: SABR Model & Dupire Local Vol Surface ────────────────────

def test_sabr_and_dupire_local_vol():
    from core.sabr_local_vol_engine import (
        DupireLocalVolEngine,
        SabrModel,
        compute_sabr_and_local_vol_surface,
    )

    sabr = SabrModel(alpha=0.20, beta=0.70, rho=-0.30, nu=0.40)
    # ATM Volatility
    vol_atm = sabr.implied_vol(f=100.0, k=100.0, t=1.0)
    assert 0.05 < vol_atm < 0.60

    # Skew: OTM Put (K=90) should have higher vol than OTM Call (K=110) for negative rho
    vol_put = sabr.implied_vol(f=100.0, k=90.0, t=1.0)
    vol_call = sabr.implied_vol(f=100.0, k=110.0, t=1.0)
    assert vol_put > vol_call

    # Calibration test
    strikes = [80.0, 90.0, 100.0, 110.0, 120.0]
    market_vols = [0.24, 0.22, 0.20, 0.19, 0.185]
    calibrated = SabrModel.calibrate(f=100.0, t=1.0, strikes=strikes, market_vols=market_vols, beta=0.70)
    assert calibrated.alpha > 0.0
    assert -0.99 <= calibrated.rho <= 0.99
    assert calibrated.nu >= 0.01

    # Dupire PDE Inversion test
    strikes_grid = [80.0, 90.0, 100.0, 110.0, 120.0]
    maturities_grid = [0.5, 1.0, 2.0]
    implied_surface = np.array([
        [0.25, 0.22, 0.20, 0.19, 0.18],
        [0.24, 0.21, 0.195, 0.185, 0.18],
        [0.23, 0.20, 0.19, 0.18, 0.175],
    ])
    dupire = DupireLocalVolEngine(strikes=strikes_grid, maturities=maturities_grid, implied_vol_surface=implied_surface)
    local_surf = dupire.compute_local_vol_surface(f0=100.0)
    assert local_surf.shape == (3, 5)
    assert np.all(local_surf > 0.0)

    # Functional helper check
    res = compute_sabr_and_local_vol_surface(f0=100.0, strikes=strikes_grid, maturities=maturities_grid)
    assert "calibrated_sabr_parameters" in res
    assert "local_vol_surface_pct" in res


# ── Test 3: NGFS Climate Stress Engine ───────────────────────────────

def test_ngfs_climate_stress_engine():
    from core.climate_stress_engine import NgfsClimateStressEngine, compute_ngfs_climate_stress

    engine = NgfsClimateStressEngine()
    # Test Orderly Net Zero 2050
    res_orderly = engine.evaluate_portfolio_stress(scenario_name="Net Zero 2050 (Orderly)", target_year=2030)
    assert res_orderly.portfolio_loss_pct < 0.0  # Loss is negative PnL
    assert res_orderly.portfolio_waci_tco2e_per_meur > 0.0
    assert res_orderly.transition_risk_loss_eur > 0.0

    # Test Hot House World: physical risk should dominate
    res_hothouse = engine.evaluate_portfolio_stress(scenario_name="Current Policies (Hot House World)", target_year=2050)
    assert res_hothouse.physical_risk_loss_eur > res_orderly.physical_risk_loss_eur
    assert res_hothouse.temperature_anomaly_celsius >= 2.5

    # Functional API check
    api_res = compute_ngfs_climate_stress(scenario_name="Delayed Transition (Disorderly)", target_year=2035)
    assert "portfolio_loss_pct" in api_res
    assert "holdings_breakdown" in api_res
    assert len(api_res["holdings_breakdown"]) > 0


# ── Test 4: Smart Order Router & MiFID II RTS 28 ─────────────────────

def test_smart_order_router_and_mifid_rts28():
    from core.smart_order_router import SmartOrderRouterEngine, compute_smart_order_routing

    sor = SmartOrderRouterEngine()
    route_res = sor.route_order(symbol="SAP.DE", side="BUY", total_quantity=10000, urgency="HIGH")

    assert route_res.executed_quantity == 10000
    assert len(route_res.fills) > 0
    assert route_res.average_fill_price > 0.0
    assert route_res.effective_spread_bps >= 0.0
    assert route_res.price_improvement_eur >= 0.0

    # MiFID II RTS 28 reporting verification
    rts28_df = sor.generate_mifid_rts28_report()
    assert len(rts28_df) == 5  # Top 5 liquidity venues
    assert "Venue Name" in rts28_df.columns
    assert "Volume %" in rts28_df.columns
    assert "Passive Orders %" in rts28_df.columns
    assert "Aggressive Orders %" in rts28_df.columns

    # Functional API
    func_res = compute_smart_order_routing(symbol="NVDA", side="SELL", quantity=2500)
    assert func_res["executed_quantity"] == 2500
    assert "rts28_report" in func_res


# ── Test 5: Private Markets Pacing & De-smoothing ────────────────────

def test_private_markets_pacing_and_desmoothing():
    from core.wealth.private_markets_engine import (
        EconometricDesmoother,
        TakahashiAlexanderPacingModel,
        compute_private_markets_analytics,
    )

    pacing = TakahashiAlexanderPacingModel(fund_life_years=10, growth_rate=0.12)
    fund_rep = pacing.simulate_fund(commitment_eur=10_000_000.0)

    # Fund lifecycle metrics
    assert fund_rep.total_commitment_eur == 10_000_000.0
    assert fund_rep.final_tvpi > 1.0  # Profitable fund
    assert fund_rep.final_dpi > 0.90  # Substantial cash returned by year 10
    assert fund_rep.peak_capital_deficit_eur > 0.0
    assert 1 <= fund_rep.j_curve_trough_year <= 5
    assert fund_rep.pme_kaplan_schoar > 0.50

    # Geltner-Fisher de-smoothing test
    # Create smoothed returns with artificial positive autocorrelation
    np.random.seed(42)
    true_innovations = np.random.normal(0.02, 0.06, 30)
    rho = 0.55
    smoothed = np.zeros(30)
    smoothed[0] = true_innovations[0]
    for t in range(1, 30):
        smoothed[t] = (1 - rho) * true_innovations[t] + rho * smoothed[t - 1]

    ds_res = EconometricDesmoother.desmooth_returns(pd.Series(smoothed), rho_override=rho)
    assert ds_res.desmoothed_annual_vol_pct > ds_res.observed_annual_vol_pct
    assert ds_res.volatility_understatement_ratio > 1.0

    # Functional API check
    func_res = compute_private_markets_analytics(commitment_eur=5_000_000.0, observed_returns=list(smoothed))
    assert func_res["tvpi"] > 1.0
    assert func_res["desmoothing"]["understatement_ratio"] > 1.0


# ── Test 6: Interactive Macro War Room & Correlation Breakdown ───────

def test_macro_war_room_and_correlation_breakdown():
    from core.macro_war_room import (
        AssetSensitivityProfile,
        MacroShockScenario,
        MacroWarRoomEngine,
        compute_macro_war_room_stress,
    )

    assets = [
        AssetSensitivityProfile("EQ", "Equity Global", "EQUITY", 1_000_000.0, equity_beta=1.2, annual_vol_pct=20.0),
        AssetSensitivityProfile("FI", "Bonds 10Y", "FIXED_INCOME", 1_000_000.0, duration=8.0, annual_vol_pct=6.0),
        AssetSensitivityProfile("COMM", "Commodities", "COMMODITY", 500_000.0, commodity_beta=1.0, annual_vol_pct=25.0),
    ]

    engine = MacroWarRoomEngine(panic_correlation=0.85)

    # 1. Base simulation with moderate shock
    scen = MacroShockScenario(
        parallel_rates_bps=100.0,
        equity_shock_pct=-15.0,
        correlation_breakdown_lambda=0.0,  # Base correlation
    )
    res_base = engine.run_simulation(assets, scen)

    # 2. Panic simulation with correlation breakdown lambda = 0.8
    scen_panic = MacroShockScenario(
        parallel_rates_bps=100.0,
        equity_shock_pct=-15.0,
        correlation_breakdown_lambda=0.80,
    )
    res_panic = engine.run_simulation(assets, scen_panic)

    # In panic, stressed volatility should exceed base volatility due to correlation breakdown
    assert res_panic.stressed_portfolio_vol_pct > res_base.stressed_portfolio_vol_pct
    assert res_panic.diversification_loss_pct > 0.0
    assert res_panic.stressed_var_99_10d_eur > res_base.stressed_var_99_10d_eur
    assert res_panic.liquidity_margin_drain_eur > 0.0

    # Functional API check
    func_res = compute_macro_war_room_stress()
    assert "total_pnl_eur" in func_res
    assert "diversification_loss_pct" in func_res
    assert "stressed_correlation_matrix" in func_res


# ── Test 7: Headless REST API v9.13.0 Endpoints ──────────────────────

def test_v913_rest_api_endpoints():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)

    # Check health version is 9.13.0 or 9.14.0
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["version"] in ["9.13.0", "9.14.0"]

    # 1. FRTB SBM
    frtb_resp = client.post("/api/v1/risk/frtb-sbm", json={"total_portfolio_value": 25_000_000.0})
    assert frtb_resp.status_code == 200
    assert "total_frtb_capital_charge_eur" in frtb_resp.json()

    # 2. SABR Vol
    sabr_resp = client.post("/api/v1/pricing/sabr-vol", json={"f0": 100.0, "beta": 0.70})
    assert sabr_resp.status_code == 200
    assert "calibrated_sabr_parameters" in sabr_resp.json()

    # 3. Climate NGFS
    clim_resp = client.post("/api/v1/stress/climate-ngfs", json={"scenario_name": "Net Zero 2050 (Orderly)", "target_year": 2030})
    assert clim_resp.status_code == 200
    assert "portfolio_loss_pct" in clim_resp.json()

    # 4. Smart Order Routing
    sor_resp = client.post("/api/v1/execution/smart-route", json={"symbol": "SAP.DE", "side": "BUY", "quantity": 1000})
    assert sor_resp.status_code == 200
    assert "average_fill_price" in sor_resp.json()

    # 5. Private Markets
    pm_resp = client.post("/api/v1/wealth/private-markets", json={"commitment_eur": 2_000_000.0, "fund_life_years": 10})
    assert pm_resp.status_code == 200
    assert "tvpi" in pm_resp.json()

    # 6. Macro War Room
    mw_resp = client.post("/api/v1/stress/macro-war-room", json={"scenario_params": {"parallel_rates_bps": 120.0}})
    assert mw_resp.status_code == 200
    assert "diversification_loss_pct" in mw_resp.json()
