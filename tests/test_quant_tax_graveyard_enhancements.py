import pytest
import pandas as pd
import numpy as np
from core.closed_trades import (
    compute_closed_trades_journal,
    compute_cumulative_realized_curve,
    compute_monthly_trading_calendar,
    compute_sector_asset_class_breakdown
)
from core.tax_engine import compute_tax_loss_harvesting_strategy
from core.advanced_quant import compute_interactive_trade_kelly, compute_tail_copula_matrix


def test_closed_trades_enhancements_sandbox():
    res = compute_closed_trades_journal(is_sandbox=True)
    assert res["has_closed_trades"] is True
    
    # 1. Cumulative curve
    df_cum = res.get("df_cumulative_curve")
    assert isinstance(df_cum, pd.DataFrame)
    assert not df_cum.empty
    assert "cum_realized_pnl_eur" in df_cum.columns
    assert "high_water_mark_eur" in df_cum.columns
    assert "drawdown_eur" in df_cum.columns

    # 2. Monthly Trading Calendar
    cal = res.get("calendar_data")
    assert isinstance(cal, dict)
    df_piv = cal.get("df_pivot")
    assert isinstance(df_piv, pd.DataFrame)
    assert not df_piv.empty

    # 3. Sector & Asset Class Breakdown
    bd = res.get("breakdown_data")
    assert isinstance(bd, dict)
    df_sec = bd.get("df_by_sector")
    df_ac = bd.get("df_by_asset_class")
    assert isinstance(df_sec, pd.DataFrame)
    assert isinstance(df_ac, pd.DataFrame)
    assert not df_sec.empty
    assert not df_ac.empty


def test_tax_loss_harvesting_wizard():
    pos_data = pd.DataFrame([
        {
            "ticker": "AAPL", "asset_class": "Equity", "qty_net": 10.0,
            "current_price": 200.0, "cost_basis_eur": 1500.0,
            "unrealized_pnl": 500.0, "unrealized_pnl_pct": 33.33
        },
        {
            "ticker": "BABA", "asset_class": "Equity", "qty_net": 20.0,
            "current_price": 80.0, "cost_basis_eur": 2000.0,
            "unrealized_pnl": -400.0, "unrealized_pnl_pct": -20.0
        },
        {
            "ticker": "VWCE.DE", "asset_class": "ETF", "qty_net": 15.0,
            "current_price": 110.0, "cost_basis_eur": 1500.0,
            "unrealized_pnl": 150.0, "unrealized_pnl_pct": 10.0
        }
    ])
    results = {"positions": pos_data}
    
    wiz = compute_tax_loss_harvesting_strategy(results, custom_zainetto_eur=1000.0)
    assert wiz["has_recommendations"] is True
    
    df_step = wiz["df_step_up"]
    assert not df_step.empty
    assert "VWCE.DE" not in df_step["ticker"].values
    assert "AAPL" in df_step["ticker"].values
    assert wiz["total_tax_savings_eur"] > 0

    df_loss = wiz["df_harvest_loss"]
    assert not df_loss.empty
    assert "BABA" in df_loss["ticker"].values


def test_interactive_trade_kelly():
    k_res = compute_interactive_trade_kelly(
        win_rate_pct=60.0,
        payoff_ratio=2.0,
        portfolio_capital_eur=100000.0,
        stop_loss_pct=5.0
    )
    assert k_res["full_kelly_pct"] == pytest.approx(40.0, 0.1)
    assert k_res["half_kelly_pct"] == pytest.approx(20.0, 0.1)
    assert k_res["quarter_kelly_pct"] == pytest.approx(10.0, 0.1)
    assert k_res["risk_half_eur"] == pytest.approx(20000.0, 1.0)
    assert k_res["pos_size_half_eur"] > 0
    assert k_res["edge_pct"] == pytest.approx(80.0, 0.1)
