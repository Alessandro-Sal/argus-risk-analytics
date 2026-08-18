# ============================================================
# tests/test_technical_analysis.py
# ARGUS — Risk Analytics Platform
# Unit Tests for Technical Analysis, Volume Profile & Confluence Engine
# ============================================================

import pytest
import pandas as pd
import numpy as np

from core.technical_analysis import (
    compute_technical_indicators,
    compute_volume_profile,
    detect_candlestick_patterns,
    compute_technical_confluence_score,
    compute_multi_timeframe_analysis
)


@pytest.fixture
def mock_price_df():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.015, 100)
    prices = 100.0 * np.exp(np.cumsum(returns))
    
    highs = prices * 1.01
    lows = prices * 0.99
    opens = lows + (highs - lows) * 0.5
    volumes = np.random.randint(1000, 50000, 100)

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes
    }, index=dates)


def test_compute_technical_indicators(mock_price_df):
    res = compute_technical_indicators(mock_price_df)
    
    assert "df_indicators" in res
    assert not res["df_indicators"].empty
    assert "last_close" in res
    assert "rsi_latest" in res
    assert 0.0 <= res["rsi_latest"] <= 100.0
    assert "last_ema20" in res
    assert "last_ema50" in res
    assert "last_sma200" in res
    assert "is_bollinger_squeeze" in res
    assert "adx_latest" in res
    assert res["adx_latest"] >= 0.0


def test_compute_volume_profile(mock_price_df):
    res = compute_volume_profile(mock_price_df, n_bins=15)
    
    assert "df_profile" in res
    assert not res["df_profile"].empty
    assert len(res["df_profile"]) == 15
    assert "poc_price" in res
    assert "vah_price" in res
    assert "val_price" in res
    assert res["val_price"] <= res["poc_price"] <= res["vah_price"]
    assert res["total_volume"] > 0


def test_detect_candlestick_patterns(mock_price_df):
    patterns = detect_candlestick_patterns(mock_price_df)
    assert isinstance(patterns, list)
    if patterns:
        assert "pattern" in patterns[0]
        assert "bias" in patterns[0]
        assert "date" in patterns[0]


def test_compute_technical_confluence_score(mock_price_df):
    res = compute_technical_confluence_score(mock_price_df)
    
    assert "score" in res
    assert 0.0 <= res["score"] <= 100.0
    assert "verdict" in res
    assert "verdict_icon" in res
    assert "factors" in res
    assert isinstance(res["factors"], list)
    assert len(res["factors"]) >= 4


def test_compute_multi_timeframe_analysis(mock_price_df):
    res = compute_multi_timeframe_analysis(mock_price_df)
    
    assert "trend_daily" in res
    assert "trend_weekly" in res
    assert "is_aligned" in res
    assert isinstance(res["is_aligned"], bool)
    assert "alignment_text" in res
