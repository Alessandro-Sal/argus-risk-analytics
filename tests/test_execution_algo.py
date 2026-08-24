"""
ARGUS — Risk Analytics Platform
Unit Tests for TWAP & VWAP Algorithmic Execution Smart Router
"""

import pytest
import pandas as pd
import numpy as np
from core.execution_algo import (
    generate_intraday_volume_profile,
    compute_twap_schedule,
    compute_vwap_schedule,
    compare_execution_strategies
)


def test_volume_profile_normalized_u_shape():
    profile = generate_intraday_volume_profile(16)
    assert len(profile) == 16
    assert pytest.approx(float(np.sum(profile)), 1e-6) == 1.0
    # U-shape check: Morning and Close volume should be higher than midday
    assert profile[0] > profile[7]
    assert profile[-1] > profile[7]


def test_twap_schedule_preserves_total_quantity():
    orders = [
        {"ticker": "AAPL", "action": "BUY", "quantity": 1000.0, "price": 200.0, "adv": 50000000.0},
        {"ticker": "NVDA", "action": "SELL", "quantity": 500.0, "price": 120.0, "adv": 40000000.0}
    ]
    twap_res = compute_twap_schedule(orders, n_intervals=16)
    df_sched = twap_res["schedule_df"]
    
    assert not df_sched.empty
    assert len(df_sched) == 32 # 16 tranches * 2 tickers
    
    aapl_slices = df_sched[df_sched["ticker"] == "AAPL"]["slice_qty"].sum()
    nvda_slices = df_sched[df_sched["ticker"] == "NVDA"]["slice_qty"].sum()
    
    assert pytest.approx(aapl_slices, 0.05) == 1000.0
    assert pytest.approx(nvda_slices, 0.05) == 500.0
    assert twap_res["summary"]["algo_type"] == "TWAP"


def test_vwap_schedule_and_pov_cap():
    orders = [
        {"ticker": "MSFT", "action": "BUY", "quantity": 2000.0, "price": 400.0, "adv": 20000000.0}
    ]
    vwap_res = compute_vwap_schedule(orders, n_intervals=16, pov_cap_pct=0.10)
    df_sched = vwap_res["schedule_df"]
    
    assert not df_sched.empty
    assert len(df_sched) == 16
    assert pytest.approx(df_sched["slice_qty"].sum(), 0.05) == 2000.0
    
    # Check that highest volume interval gets the largest slice
    max_vol_idx = df_sched["interval_mkt_vol"].idxmax()
    min_vol_idx = df_sched["interval_mkt_vol"].idxmin()
    assert df_sched.loc[max_vol_idx, "slice_qty"] > df_sched.loc[min_vol_idx, "slice_qty"]


def test_compare_execution_strategies():
    orders = [
        {"ticker": "ENEL.MI", "action": "BUY", "quantity": 10000.0, "price": 7.0, "adv": 15000000.0}
    ]
    comp = compare_execution_strategies(orders)
    assert "twap" in comp
    assert "vwap" in comp
    assert "comparison" in comp
    assert comp["comparison"]["total_notional_eur"] == 70000.0
    assert comp["comparison"]["vwap_cost_eur"] <= comp["comparison"]["market_order_cost_eur"]
