"""
Unit Tests for Algorithmic Execution, Market Impact, TCA Framework & Broker Interfaces
Covers:
- Microstructure Square-Root Law market impact
- Multi-Asset Almgren-Chriss basket optimal scheduling
- Broker Order Exporters (FIX 4.4, IBKR CSV, Directa CSV)
- Pre-Trade TCA & Execution VaR (95%/99%)
- Post-Trade TCA & Perold (1988) Implementation Shortfall reconciliation
"""

import pytest
import numpy as np
import pandas as pd
from core.execution_algo import (
    generate_intraday_volume_profile,
    estimate_microstructure_market_impact,
    compute_twap_schedule,
    compute_vwap_schedule,
    compute_almgren_chriss_basket_schedule,
    generate_fix44_blotter,
    export_ibkr_basket_csv,
    export_directa_csv
)
from core.execution_algo_engine import (
    compute_broker_commissions,
    compute_implementation_shortfall_and_execution_benchmarks,
    compute_pre_trade_tca,
    compute_post_trade_tca
)


def test_microstructure_square_root_impact():
    # Low volatility asset vs high volatility asset
    low_vol_res = estimate_microstructure_market_impact(
        slice_qty=1000, interval_volume=50000, total_qty=10000, adv=500000,
        daily_volatility=0.010, half_spread_bps=1.5
    )
    high_vol_res = estimate_microstructure_market_impact(
        slice_qty=1000, interval_volume=50000, total_qty=10000, adv=500000,
        daily_volatility=0.030, half_spread_bps=1.5
    )
    
    assert high_vol_res["temporary_impact_bps"] > low_vol_res["temporary_impact_bps"]
    assert high_vol_res["permanent_impact_bps"] > low_vol_res["permanent_impact_bps"]
    assert high_vol_res["total_slippage_bps"] > low_vol_res["total_slippage_bps"]
    assert low_vol_res["half_spread_bps"] == 1.5


def test_almgren_chriss_basket_schedule_and_invariance():
    orders = [
        {"ticker": "SWDA.MI", "action": "BUY", "quantity": 5000.0, "price": 100.0, "adv": 200000.0, "volatility_daily": 0.012},
        {"ticker": "EIMI.MI", "action": "SELL", "quantity": 10000.0, "price": 30.0, "adv": 300000.0, "volatility_daily": 0.016}
    ]
    
    ac_res = compute_almgren_chriss_basket_schedule(orders, horizon_days=1.0, n_intervals=16, risk_aversion_lambda=1e-5)
    df_sched = ac_res["schedule_df"]
    
    assert not df_sched.empty
    assert len(df_sched) == 32 # 16 intervals * 2 orders
    
    # Check quantity preservation for both assets
    swda_qty = df_sched[df_sched["ticker"] == "SWDA.MI"]["slice_qty"].sum()
    eimi_qty = df_sched[df_sched["ticker"] == "EIMI.MI"]["slice_qty"].sum()
    assert pytest.approx(swda_qty, 0.05) == 5000.0
    assert pytest.approx(eimi_qty, 0.05) == 10000.0
    
    # Check risk metrics
    summary = ac_res["summary"]
    assert summary["expected_cost_eur"] > 0
    assert summary["execution_var_95_eur"] >= summary["expected_cost_eur"]
    assert summary["execution_var_99_eur"] >= summary["execution_var_95_eur"]


def test_broker_order_routing_exporters():
    orders = [
        {"ticker": "ENEL.MI", "action": "BUY", "quantity": 2500, "price": 6.85, "est_exec_price_eur": 6.86},
        {"ticker": "ISP.MI", "action": "SELL", "quantity": 5000, "price": 3.42, "est_exec_price_eur": 3.415}
    ]
    
    # 1. FIX 4.4 format
    fix_raw = generate_fix44_blotter(orders)
    assert "8=FIX.4.4" in fix_raw
    assert "35=D" in fix_raw
    assert "55=ENEL.MI" in fix_raw
    assert "54=1" in fix_raw # Buy
    assert "54=2" in fix_raw # Sell
    assert "10=" in fix_raw  # Checksum tag
    
    # 2. IBKR Basket Trader CSV
    ibkr_csv = export_ibkr_basket_csv(orders)
    assert "Action,Quantity,Symbol,SecType,Exchange,Currency,OrderType,LmtPrice,TimeInForce" in ibkr_csv
    assert "ENEL" in ibkr_csv
    assert "BVME" in ibkr_csv
    assert "BUY" in ibkr_csv
    assert "SELL" in ibkr_csv
    
    # 3. Directa SIM CSV
    directa_csv = export_directa_csv(orders)
    assert "Codice Titolo;Operazione;Quantita;Tipo Ordine;Prezzo Limite;Validita" in directa_csv
    assert "ENEL.MI" in directa_csv
    assert "ACQUISTO" in directa_csv
    assert "VENDITA" in directa_csv


def test_pre_trade_tca_decomposition():
    orders = [
        {"ticker": "SWDA.MI", "action": "BUY", "quantity": 2000, "price": 100.0, "adv": 100000.0, "volatility_daily": 0.012}
    ]
    
    # Test different broker commissions
    tca_directa = compute_pre_trade_tca(orders, broker="DIRECTA")
    tca_ibkr = compute_pre_trade_tca(orders, broker="IBKR")
    
    assert tca_directa["summary"]["total_notional_eur"] == 200000.0
    assert tca_directa["summary"]["commissions_eur"] > 0
    assert tca_directa["summary"]["spread_cost_eur"] > 0
    assert tca_directa["summary"]["temp_impact_eur"] > 0
    assert tca_directa["summary"]["perm_impact_eur"] > 0
    assert tca_directa["summary"]["execution_var_95_eur"] > tca_directa["summary"]["total_expected_cost_eur"]
    
    ci = tca_directa["summary"]["confidence_intervals"]
    assert ci["p10_eur"] <= ci["p50_eur"] <= ci["p90_eur"]
    
    # Compare broker commissions
    assert tca_directa["summary"]["broker_selected"] == "DIRECTA"
    assert tca_ibkr["summary"]["broker_selected"] == "IBKR"


def test_post_trade_tca_reconciliation():
    executed_trades = [
        {"timestamp": "09:15", "shares": 1000, "price": 100.20},
        {"timestamp": "10:30", "shares": 1500, "price": 100.40},
        {"timestamp": "14:00", "shares": 2500, "price": 100.30}
    ]
    
    tca_post = compute_post_trade_tca(
        executed_trades=executed_trades,
        decision_price=100.00,
        arrival_price=100.10,
        side="BUY",
        market_vwap=100.35,
        market_close=100.50,
        total_ordered_shares=5000,
        commissions_paid_eur=25.0
    )
    
    summary = tca_post["summary"]
    assert summary["total_shares_filled"] == 5000
    assert summary["fill_rate_pct"] == 100.0
    assert pytest.approx(summary["avg_execution_price_eur"], 0.01) == 100.31
    assert summary["execution_quality_score"] > 0
    assert "EXCELLENT" in summary["execution_rating"] or "GOOD" in summary["execution_rating"]
    
    # Benchmarks
    benchmarks = tca_post["slippage_benchmarks"]
    assert benchmarks["vs_arrival_price"]["slippage_eur"] > 0 # Executed above arrival for BUY
    # Since avg exec is 100.31 and market VWAP is 100.35, we beat the market VWAP!
    assert benchmarks["vs_market_vwap"]["outperformed_vwap"] is True
    
    # Perold breakdown consistency
    pb = tca_post["perold_breakdown"]
    total_is_reconstructed = pb["delay_cost_eur"] + pb["market_impact_eur"] + pb["commissions_eur"] + pb["opportunity_cost_eur"]
    assert pytest.approx(pb["total_implementation_shortfall_eur"], 0.01) == total_is_reconstructed
