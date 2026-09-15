"""
tests/test_phase2_performance_engine.py
Automated test suite for ARGUS Phase 2 Architecture & Engine Hardening:
1. CacheShield Apache Arrow Feather L2 binary serialization and round-trip.
2. Hardened Black-Litterman SLSQP Quadratic Programming optimizer with long-only constraints and omega ill-conditioning.
3. Unified RebalancingEngine architecture, strategy dispatching, and TUIR Art. 44 vs 67 compliance.
4. UI Export Toolbar fragment isolation.
"""

import io
import os
import sqlite3

import numpy as np
import pandas as pd
import pytest

from core.cache_shield import (
    HAS_PYARROW,
    _binary_payload_to_df,
    _df_to_binary_payload,
    _get_cache_connection,
    clear_cache,
    get_cache_stats,
)
from core.rebalancing import (
    AssetHolding,
    PlannedOrder,
    RebalanceResult,
    RebalancingContext,
    RebalancingEngine,
    RebalancingMode,
    TaxCategory,
)
from core.risk_engine import compute_black_litterman_optimization
from core.ui_export_utils import render_export_toolbar

# ==============================================================================
# 1. TEST CACHE SHIELD ARROW FEATHER L2 BINARY SERIALIZATION
# ==============================================================================

def test_cache_shield_feather_binary_roundtrip():
    """Verifica che _df_to_binary_payload e _binary_payload_to_df preservino i dati via Feather."""
    dates = pd.date_range("2025-01-01", periods=100, freq="B")
    df_orig = pd.DataFrame(
        {
            "close": np.random.randn(100).cumsum() + 100.0,
            "volume": np.random.randint(1000, 50000, size=100),
            "ticker": ["VWCE.MI"] * 100,
        },
        index=dates,
    )
    df_orig.index.name = "Date"

    payload = _df_to_binary_payload(df_orig)
    assert isinstance(payload, bytes), "Il payload deve essere un buffer binario (bytes)"
    assert len(payload) > 0

    df_restored = _binary_payload_to_df(payload)
    assert isinstance(df_restored, pd.DataFrame), "Il dato deserializzato deve essere un DataFrame"
    assert len(df_restored) == len(df_orig), "Il numero di righe deve corrispondere"
    assert "close" in df_restored.columns
    assert np.allclose(df_restored["close"].values, df_orig["close"].values)

    # Verifica compatibilità retroattiva con payload JSON legacy
    json_payload = df_orig.to_json(date_format="iso")
    df_from_json = _binary_payload_to_df(json_payload)
    assert isinstance(df_from_json, pd.DataFrame)
    assert len(df_from_json) == len(df_orig)
    assert np.allclose(df_from_json["close"].values, df_orig["close"].values)


def test_cache_shield_db_binary_storage():
    """Verifica che la tabella SQLite salvi e recuperi il payload binario Feather."""
    clear_cache()
    conn = _get_cache_connection()
    
    dates = pd.date_range("2025-01-01", periods=10, freq="B")
    df_test = pd.DataFrame({"price": [10.0, 11.5, 12.0, 11.8, 12.2, 12.5, 13.0, 12.8, 13.2, 13.5]}, index=dates)
    payload = _df_to_binary_payload(df_test)

    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO yfinance_cache (cache_key, ticker, data_type, payload, cached_at, ttl_seconds) VALUES (?, ?, ?, ?, ?, ?)",
        ("test_key_binary", "TEST.MI", "history", sqlite3.Binary(payload), 1000.0, 86400.0),
    )
    conn.commit()

    cur.execute("SELECT payload FROM yfinance_cache WHERE cache_key = 'test_key_binary'")
    row = cur.fetchone()
    assert row is not None
    loaded_payload = row[0]
    df_loaded = _binary_payload_to_df(loaded_payload)
    assert len(df_loaded) == 10
    assert np.allclose(df_loaded["price"].values, df_test["price"].values)
    
    stats = get_cache_stats()
    assert stats["l2_disk_entries"] >= 1
    clear_cache()


# ==============================================================================
# 2. TEST HARDENED BLACK-LITTERMAN SLSQP QUADRATIC PROGRAMMING
# ==============================================================================

def test_black_litterman_slsqp_long_only_optimization():
    """
    Verifica che il nuovo solutore SLSQP Quadratic Programming produca pesi
    esattamente long-only (w >= 0, sum(w) == 1) anche in presenza di viste estreme.
    """
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    weights_eq = pd.Series([0.25, 0.25, 0.25, 0.25], index=tickers)
    cov_matrix = pd.DataFrame(
        [
            [0.040, 0.015, 0.012, 0.010],
            [0.015, 0.035, 0.014, 0.011],
            [0.012, 0.014, 0.030, 0.009],
            [0.010, 0.011, 0.009, 0.025],
        ],
        index=tickers,
        columns=tickers,
    )
    # Viste estreme per verificare che i pesi non vadano short
    views = {"AAPL": 0.35, "MSFT": -0.10}

    res = compute_black_litterman_optimization(
        cov_matrix=cov_matrix,
        market_weights=weights_eq,
        views_dict=views,
        tau=0.05,
        risk_aversion=2.5,
    )

    bl_weights = res["black_litterman_weights"].values
    assert len(bl_weights) == len(tickers)

    # Verifica vincoli Hard: w_i >= 0 e sum(w_i) == 1.0
    assert np.all(bl_weights >= -1e-6), f"Pesi strettamente non negativi: {bl_weights}"
    assert np.isclose(np.sum(bl_weights), 1.0, atol=1e-4), f"Somma pesi = 1.0: {np.sum(bl_weights)}"

    # Verifica rendimenti a posteriori
    assert "black_litterman_returns" in res
    assert len(res["black_litterman_returns"]) == len(tickers)


def test_black_litterman_ill_conditioned_omega():
    """Verifica che viste multiple o con varianze estreme vengano regolarizzate senza crash."""
    tickers = ["A", "B"]
    weights_eq = pd.Series([0.5, 0.5], index=tickers)
    # Matrice di covarianza con correlazione quasi perfetta (0.9999)
    cov_matrix = pd.DataFrame(
        [[0.04, 0.03999], [0.03999, 0.04]],
        index=tickers,
        columns=tickers,
    )
    views = {"A": 0.05, "B": 0.05}

    res = compute_black_litterman_optimization(
        cov_matrix=cov_matrix,
        market_weights=weights_eq,
        views_dict=views,
        tau=0.05,
        risk_aversion=2.5,
    )

    bl_weights = res["black_litterman_weights"].values
    assert np.all(bl_weights >= -1e-6)
    assert np.isclose(np.sum(bl_weights), 1.0, atol=1e-4)


# ==============================================================================
# 3. TEST UNIFIED REBALANCING ENGINE & STRATEGIES
# ==============================================================================

def test_rebalancing_engine_autonomous_strategy():
    """Verifica RebalancingEngine con strategia 'autonomous' e conformità TUIR."""
    holdings = [
        AssetHolding(ticker="SWDA.MI", shares=100, current_price=100.0, pmc=80.0, asset_class="ETF"),
        AssetHolding(ticker="ISP.MI", shares=1000, current_price=4.0, pmc=3.0, asset_class="Equity"),
        AssetHolding(ticker="XEON.MI", shares=50, current_price=140.0, pmc=138.0, asset_class="ETF"),
    ]
    # Valore totale = 100*100 + 1000*4 + 50*140 = 10000 + 4000 + 7000 = 21000 EUR
    context = RebalancingContext(
        holdings=holdings,
        target_weights={"SWDA.MI": 0.40, "ISP.MI": 0.20, "XEON.MI": 0.40},
        minusvalenze_available=500.0,
        min_trade_eur=100.0,
    )

    engine = RebalancingEngine(strategy="autonomous")
    result = engine.execute(context)

    assert isinstance(result, RebalanceResult)
    assert result.strategy_name == "autonomous"
    assert len(result.orders) > 0
    assert result.summary["portfolio_total_value_eur"] == pytest.approx(21000.0, abs=1.0)
    assert "tax_report" in result.__dict__
    assert result.tax_report["initial_minusvalenze_eur"] == 500.0
    
    # Verifica che gli ETF abbiano classificazione Redditi di Capitale
    for order in result.orders:
        if "SWDA.MI" in order.ticker or "XEON.MI" in order.ticker:
            if order.action == "SELL" and order.realized_gain > 0:
                assert "REDDITI_CAPITALE" in order.tax_category


def test_rebalancing_engine_heuristic_and_tax_aware_strategies():
    """Verifica RebalancingEngine per le strategie 'heuristic' e 'tax_aware'."""
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 50, "last_price": 200.0, "current_value": 10000.0, "weight_pct": 50.0, "asset_class": "Equity"},
        {"ticker": "MSFT", "qty_net": 25, "last_price": 400.0, "current_value": 10000.0, "weight_pct": 50.0, "asset_class": "Equity"},
    ])
    
    # 1. Heuristic
    ctx_heuristic = RebalancingContext(
        holdings=df_pos,
        target_weights={"AAPL": 0.70, "MSFT": 0.30},
        total_portfolio_value=20000.0,
    )
    res_heuristic = RebalancingEngine.rebalance(ctx_heuristic, strategy=RebalancingMode.HEURISTIC.value)
    assert res_heuristic.strategy_name == "heuristic"
    assert len(res_heuristic.orders) == 2
    actions = {o.ticker: o.action for o in res_heuristic.orders}
    assert actions["AAPL"] == "BUY"
    assert actions["MSFT"] == "SELL"

    # 2. Tax-Aware
    ctx_tax_aware = RebalancingContext(
        holdings=df_pos,
        target_weights={"AAPL": 0.60, "MSFT": 0.40},
        total_portfolio_value=20000.0,
        minusvalenze_available=200.0,
    )
    res_tax_aware = RebalancingEngine.rebalance(ctx_tax_aware, strategy="tax_aware")
    assert res_tax_aware.strategy_name == "tax_aware"
    assert "total_friction_cost_eur" in res_tax_aware.summary


# ==============================================================================
# 4. TEST STREAMLIT EXPORT TOOLBAR FRAGMENT ISOLATION
# ==============================================================================

def test_export_toolbar_fragment_wrapper():
    """Verifica che render_export_toolbar sia callable ed esposta per l'isolamento dei re-run."""
    assert callable(render_export_toolbar)
    import streamlit as st

    if hasattr(st, "fragment"):
        assert callable(render_export_toolbar)
