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
