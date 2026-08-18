"""
Tests for core/screener_engine.py
Verifies Multi-Factor Screener and Pre-Trade Impact Simulator
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch
from core.screener_engine import (
    MARKET_UNIVERSES,
    _compute_rsi,
    apply_strategy_preset,
    fetch_screener_universe_data,
    simulate_pre_trade_impact
)


def test_market_universes_structure():
    assert len(MARKET_UNIVERSES) >= 4
    for name, data in MARKET_UNIVERSES.items():
        assert "description" in data
        assert "tickers" in data
        assert len(data["tickers"]) > 0


def test_compute_rsi():
    # Constant series -> RSI = 50
    s_flat = pd.Series([10.0] * 30)
    assert _compute_rsi(s_flat, 14) == 50.0

    # Steadily increasing series -> RSI close to 100
    s_up = pd.Series(np.linspace(10, 50, 30))
    rsi_up = _compute_rsi(s_up, 14)
    assert rsi_up > 80.0

    # Steadily decreasing series -> RSI close to 0
    s_down = pd.Series(np.linspace(50, 10, 30))
    rsi_down = _compute_rsi(s_down, 14)
    assert rsi_down < 20.0


def test_apply_strategy_presets():
    df_sample = pd.DataFrame([
        {
            "ticker": "GARP1", "peg_ratio": 1.1, "roe_pct": 18.0, "upside_pct": 12.0, "trailing_pe": 25.0,
            "dividend_yield_pct": 1.0, "altman_z_score": 3.2, "debt_to_equity": 0.5, "price_to_book": 3.5,
            "volatility_ann_pct": 20.0, "beta": 1.0, "sharpe_ratio": 1.2, "price_to_sma200_pct": 5.0, "rsi_14": 55.0, "perf_1y_pct": 15.0
        },
        {
            "ticker": "DIV1", "peg_ratio": 2.2, "roe_pct": 8.0, "upside_pct": 2.0, "trailing_pe": 14.0,
            "dividend_yield_pct": 4.5, "altman_z_score": 2.8, "debt_to_equity": 0.9, "price_to_book": 1.5,
            "volatility_ann_pct": 14.0, "beta": 0.7, "sharpe_ratio": 0.9, "price_to_sma200_pct": 2.0, "rsi_14": 50.0, "perf_1y_pct": 6.0
        },
        {
            "ticker": "VAL1", "peg_ratio": 1.8, "roe_pct": 10.0, "upside_pct": 20.0, "trailing_pe": 12.0,
            "dividend_yield_pct": 3.0, "altman_z_score": 2.5, "debt_to_equity": 1.2, "price_to_book": 1.2,
            "volatility_ann_pct": 18.0, "beta": 0.8, "sharpe_ratio": 0.8, "price_to_sma200_pct": -1.0, "rsi_14": 42.0, "perf_1y_pct": -2.0
        }
    ])

    res_garp = apply_strategy_preset(df_sample, "garp")
    assert "GARP1" in res_garp["ticker"].values

    res_div = apply_strategy_preset(df_sample, "dividend_fortress")
    assert "DIV1" in res_div["ticker"].values

    res_val = apply_strategy_preset(df_sample, "deep_value")
    assert "VAL1" in res_val["ticker"].values

    res_vol = apply_strategy_preset(df_sample, "low_volatility")
    assert "DIV1" in res_vol["ticker"].values


def test_simulate_pre_trade_impact():
    df_pos = pd.DataFrame({
        "ticker": ["AAPL", "MSFT"],
        "current_value": [5000.0, 5000.0]
    })

    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    p_aapl = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, len(dates))))
    p_msft = 100 * np.exp(np.cumsum(np.random.normal(0.0006, 0.014, len(dates))))
    p_jnj = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.009, len(dates))))
    p_spy = 100 * np.exp(np.cumsum(np.random.normal(0.0004, 0.010, len(dates))))

    def mock_hist(ticker, **kwargs):
        tk = str(ticker).upper()
        if tk == "AAPL": return pd.DataFrame({"close": p_aapl}, index=dates)
        elif tk == "MSFT": return pd.DataFrame({"close": p_msft}, index=dates)
        elif tk == "JNJ": return pd.DataFrame({"close": p_jnj}, index=dates)
        elif tk == "SPY": return pd.DataFrame({"close": p_spy}, index=dates)
        return pd.DataFrame({"close": p_spy}, index=dates)

    with patch("core.screener_engine.get_cached_ticker_history", side_effect=mock_hist):
        res = simulate_pre_trade_impact(
            current_positions_df=df_pos,
            candidate_ticker="JNJ",
            candidate_weight_pct=10.0,
            benchmark_ticker="SPY"
        )

        assert res["valid"] is True
        assert res["candidate_ticker"] == "JNJ"
        assert res["simulated_weight_pct"] == 10.0
        assert "metrics_comparison" in res
        assert "Volatilità Annua (%)" in res["metrics_comparison"]
        assert "Sharpe Ratio" in res["metrics_comparison"]
        assert "Beta di Portafoglio" in res["metrics_comparison"]
        assert "Diversification Ratio" in res["metrics_comparison"]
        assert isinstance(res["weights_table"], pd.DataFrame)


def test_compute_market_and_watchlist_alerts():
    from core.screener_engine import compute_market_and_watchlist_alerts
    
    df_sample = pd.DataFrame([
        {"ticker": "OVERSOLD1", "name": "Solid Co", "rsi_14": 28.0, "altman_z_score": 3.4, "upside_pct": 5.0, "trailing_pe": 20.0, "perf_1y_pct": 5.0, "debt_to_equity": 0.4},
        {"ticker": "VALUE1", "name": "Cheap Co", "rsi_14": 50.0, "altman_z_score": 2.2, "upside_pct": 22.0, "trailing_pe": 12.0, "perf_1y_pct": -2.0, "debt_to_equity": 0.8},
        {"ticker": "MOM1", "name": "Growth Star", "rsi_14": 62.0, "altman_z_score": 3.0, "upside_pct": 10.0, "trailing_pe": 35.0, "perf_1y_pct": 45.0, "debt_to_equity": 0.5},
        {"ticker": "RISK1", "name": "Levered Co", "rsi_14": 45.0, "altman_z_score": 1.2, "upside_pct": 0.0, "trailing_pe": 15.0, "perf_1y_pct": -10.0, "debt_to_equity": 3.5}
    ])
    
    alerts = compute_market_and_watchlist_alerts(df_sample)
    assert len(alerts) >= 4
    badges = [a["badge"] for a in alerts]
    assert any("OVERSOLD" in b for b in badges)
    assert any("DEEP VALUE" in b for b in badges)
    assert any("MOMENTUM" in b for b in badges)
    assert any("SOLVENCY" in b for b in badges)


def test_generate_asset_factsheet_pdf():
    from core.pdf_generator import generate_asset_factsheet_pdf
    
    sample_asset = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "last_price": 185.50,
        "target_mean_price": 210.00,
        "upside_pct": 13.20,
        "trailing_pe": 28.5,
        "peg_ratio": 1.8,
        "price_to_book": 8.5,
        "dividend_yield_pct": 0.65,
        "roe_pct": 35.0,
        "altman_z_score": 4.2,
        "piotroski_score": 8,
        "beta": 1.05,
        "volatility_ann_pct": 22.5,
        "sharpe_ratio": 1.25,
        "rsi_14": 55.0,
        "argus_score": 82.5
    }
    
    pdf_bytes = generate_asset_factsheet_pdf(sample_asset)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 200
    assert pdf_bytes.startswith(b"%PDF-1.4")

