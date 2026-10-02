# ==============================================================================
# tests/test_institutional_frontiers.py
# ARGUS — Unit Tests for Notification Sentinel, FX Overlay & EMSX FIX Blotter
# ==============================================================================

import pandas as pd
import pytest

from core.fx_overlay_engine import (
    calculate_currency_exposure,
    compute_forward_points_and_carry,
    optimize_minimum_variance_hedge_ratio,
)
from core.trade_staging_blotter import (
    StagedOrder,
    simulate_fix_routing,
    stage_orders_from_portfolio,
)
from core.watchdog.unified_notification_center import get_unified_compliance_notifications
from core.wealth.unified_stress_bridge import (
    MacroFactorShock,
    map_global_macro_preset_to_factor_shock,
)


def test_unified_notification_center_risk_and_macro():
    """Verifica la raccolta unificata di alert di rischio, limiti e macro shock."""
    mock_risk_data = {
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "current_value": 85000.0, "qty_net": 100},
            {"ticker": "MSFT", "current_value": 15000.0, "qty_net": 50},
        ]),
        "var_95_hist": 0.045,  # 4.5% > limit 3.0% (Breach)
        "portfolio_beta": 1.45,  # 1.45 > limit 1.25 (Breach)
    }

    res = get_unified_compliance_notifications(risk_data=mock_risk_data)
    assert res["total_count"] >= 2
    assert res["critical_count"] >= 1
    titles = [n.title for n in res["notifications"]]
    assert any("Violazione" in t for t in titles)


def test_unified_notification_center_wealth_alerts():
    """Verifica l'aggregazione degli alert Wealth Watchdog."""
    mock_wealth_snapshot = {
        "total_net_worth": 300000.0,
        "liquid_cash": 4000.0,
        "financial_investments": 100000.0,
        "real_estate_total": 200000.0,
        "total_liabilities": 50000.0,
        "runway_months": 1.2,  # Critico (< 3 mesi)
        "monthly_expenses": 3000.0,
    }

    res = get_unified_compliance_notifications(wealth_snapshot=mock_wealth_snapshot)
    assert res["total_count"] >= 1
    severities = [n.severity for n in res["notifications"]]
    assert "CRITICAL" in severities


def test_fx_overlay_engine_calculations():
    """Verifica il calcolo dell'esposizione FX, hedge ratio ottimale e parità CIP dei tassi forward."""
    mock_pos = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 60000.0, "asset_currency": "USD"},
        {"ticker": "SWDA.MI", "current_value": 40000.0, "asset_currency": "EUR"},
    ])

    exp = calculate_currency_exposure(mock_pos, base_currency="EUR")
    assert exp["total_portfolio_eur"] == 100000.0
    assert exp["foreign_exposure_eur"] == 60000.0
    assert exp["foreign_exposure_pct"] == 60.0

    # Minimum-Variance Hedge Ratio
    asset_ret = pd.Series([0.01, -0.02, 0.015, -0.005, 0.02] * 10)
    fx_ret = pd.Series([-0.005, 0.01, -0.008, 0.003, -0.01] * 10)
    opt = optimize_minimum_variance_hedge_ratio(asset_ret, fx_ret)
    assert 0.0 <= opt["optimal_hedge_ratio"] <= 1.2
    assert opt["vol_optimal_pct"] <= opt["vol_unhedged_pct"]

    # CIP Forward Carry Cost
    cip = compute_forward_points_and_carry(
        spot_rate=1.0850,
        base_rate=0.0325,
        foreign_rate=0.0475,
        tenor_days=90,
        notional_foreign=60000.0,
    )
    assert cip["forward_rate"] > 0
    assert cip["carry_cost_bps"] < 0  # EURIBOR < SOFR -> carry discount
    assert cip["annual_cost_eur"] > 0


def test_trade_staging_blotter_and_fix_routing():
    """Verifica la generazione ordini EMSX, la serializzazione FIX 4.4 e il calcolo TCA."""
    mock_pos = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 50000.0, "qty_net": 100, "last_price": 220.0},
        {"ticker": "BTP", "current_value": 50000.0, "qty_net": 500, "last_price": 100.0},
    ])

    staged = stage_orders_from_portfolio(mock_pos, portfolio_value=100000.0)
    assert len(staged) >= 2
    tickers = [o.symbol for o in staged]
    assert "AAPL" in tickers

    # Simulazione Routing FIX
    sim = simulate_fix_routing(staged, execution_algo="TWAP")
    assert sim["total_notional_executed"] > 0
    assert sim["total_friction_saved_eur"] >= 0
    assert sim["orders_count"] == len(staged)

    # Validazione protocollo FIX 4.4 nel log
    fix_log = sim["fix_stream_log"]
    assert "8=FIX.4.4" in fix_log
    assert "35=D" in fix_log  # NewOrderSingle
    assert "35=8" in fix_log  # ExecutionReport
    assert "10=" in fix_log  # CheckSum


def test_custom_sandbox_macro_shock():
    """Verifica la gestione del preset CUSTOM_SANDBOX nel ponte macro."""
    shock = map_global_macro_preset_to_factor_shock("CUSTOM_SANDBOX")
    assert isinstance(shock, MacroFactorShock)
    assert shock.equity_mkt_pct != 0.0


def test_unified_notification_center_standby_and_activation():
    """Verifica che senza alcuna analisi attiva il sentinel rimanga in standby e si attivi solo dopo il caricamento."""
    from core.watchdog.unified_notification_center import check_active_analysis

    # 1. Nessun dato -> Standby
    assert check_active_analysis(risk_data=None, wealth_snapshot=None) is False
    assert check_active_analysis(risk_data={}, wealth_snapshot={}) is False
    res_standby = get_unified_compliance_notifications(risk_data=None, wealth_snapshot=None)
    assert res_standby["has_active_analysis"] is False
    assert res_standby["total_count"] == 0
    assert len(res_standby["notifications"]) == 0

    # 2. Risk bundle con posizioni -> Attivo
    risk_active = {
        "positions": pd.DataFrame([{"ticker": "SPY", "current_value": 10000.0, "qty_net": 20}]),
        "var_95_hist": 0.02,
    }
    assert check_active_analysis(risk_data=risk_active) is True
    res_active = get_unified_compliance_notifications(risk_data=risk_active)
    assert res_active["has_active_analysis"] is True

    # 3. Wealth snapshot con patrimonio -> Attivo
    wealth_active = {"total_net_worth": 250000.0, "liquid_cash": 15000.0}
    assert check_active_analysis(wealth_snapshot=wealth_active) is True
    res_wealth = get_unified_compliance_notifications(wealth_snapshot=wealth_active)
    assert res_wealth["has_active_analysis"] is True


def test_master_wealth_risk_limits_and_pre_allerta():
    """Verifica che i limiti di rischio leggano correttamente le metriche annidate e distinguano Pre-Allerta da Violazione."""
    from core.risk_limits import check_risk_limits

    mock_bundle = {
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "current_value": 15000.0, "qty_net": 100, "sector": "Technology"},
            {"ticker": "MSFT", "current_value": 15000.0, "qty_net": 80, "sector": "Technology"},
            {"ticker": "SWDA.MI", "current_value": 18000.0, "qty_net": 200, "sector": "Broad Market"},
            {"ticker": "GOOGL", "current_value": 16000.0, "qty_net": 100, "sector": "Communications"},
            {"ticker": "AMZN", "current_value": 18000.0, "qty_net": 100, "sector": "Consumer Discretionary"},
            {"ticker": "ISP.MI", "current_value": 18000.0, "qty_net": 1000, "sector": "Financials"},
        ]),
        "metrics": {
            "market_risk": {"var_95": 2.48, "beta": 1.12},
            "concentration": {"diversification_ratio": 1.45, "hhi_index": 0.068},
        },
    }

    # 1. Verifica estrazione corretta da check_risk_limits
    evals = check_risk_limits(mock_bundle)
    df_evals = evals["evaluations"]
    dr_row = df_evals[df_evals["key"] == "min_diversification_ratio"].iloc[0]
    assert dr_row["current_value"] == 1.45
    assert dr_row["status"] == "PASS"

    beta_row = df_evals[df_evals["key"] == "max_beta"].iloc[0]
    assert beta_row["current_value"] == 1.12
    assert beta_row["status"] == "WARNING"

    # 2. Verifica formattazione nel notification center: WARNING deve essere Pre-Allerta, non Violazione
    notifs = get_unified_compliance_notifications(risk_data=mock_bundle)
    assert notifs["critical_count"] == 0
    beta_notif = next(n for n in notifs["notifications"] if "Beta" in n.title)
    assert "Pre-Allerta" in beta_notif.title
    assert "Violazione" not in beta_notif.title
    assert "riduzione tattica" in beta_notif.suggested_action


