# ============================================================
# tests/test_crypto_provider.py
# ARGUS — Unit tests for Resilient Multi-Exchange Crypto Provider
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.crypto_provider import (
    is_crypto_symbol,
    normalize_crypto_pair,
    fetch_binance_ohlcv,
    fetch_kraken_ohlcv,
    fetch_coingecko_ohlcv,
    fetch_crypto_history_unified
)
from core.cache_shield import get_cached_ticker_history


def test_is_crypto_symbol_detection():
    """Verifica il riconoscimento accurato dei simboli crypto vs azionari."""
    assert is_crypto_symbol("BTC-EUR") is True
    assert is_crypto_symbol("ETH-USD") is True
    assert is_crypto_symbol("SOL-EUR") is True
    assert is_crypto_symbol("SEI-EUR") is True
    assert is_crypto_symbol("FDUSD-EUR") is True
    assert is_crypto_symbol("BTC/EUR") is True
    assert is_crypto_symbol("ETH") is True
    
    assert is_crypto_symbol("AAPL") is False
    assert is_crypto_symbol("MSFT") is False
    assert is_crypto_symbol("SPY") is False
    assert is_crypto_symbol("ISP.MI") is False


def test_normalize_crypto_pair():
    """Verifica la scomposizione in valuta base e quotazione."""
    base, quote = normalize_crypto_pair("BTC-EUR")
    assert base == "BTC" and quote == "EUR"

    base2, quote2 = normalize_crypto_pair("ETH/USD")
    assert base2 == "ETH" and quote2 == "USD"

    base3, quote3 = normalize_crypto_pair("SOL")
    assert base3 == "SOL" and quote3 == "EUR"


def test_fetch_binance_ohlcv_btc():
    """Verifica il download e il parsing delle candele da Binance per BTC."""
    df = fetch_binance_ohlcv("BTC", "EUR", limit=10)
    if df is not None:
        assert isinstance(df, pd.DataFrame)
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in df.columns
        assert len(df) > 0
        assert df["close"].iloc[-1] > 1000.0


def test_fetch_crypto_history_unified_cascade():
    """Verifica la pipeline unificata con fallback per BTC-EUR e token altcoin."""
    df_btc = fetch_crypto_history_unified("BTC-EUR")
    assert df_btc is not None and not df_btc.empty
    assert "close" in df_btc.columns

    df_sei = fetch_crypto_history_unified("SEI-EUR")
    assert df_sei is not None and not df_sei.empty
    assert "close" in df_sei.columns
    assert df_sei["close"].iloc[-1] > 0.0


def test_cache_shield_integration_with_crypto():
    """Verifica che il Cache Shield sfrutti il provider crypto per ticker non trovati su Yahoo."""
    df_cached = get_cached_ticker_history("SEI-EUR", ttl_seconds=3600, force_refresh=True)
    assert df_cached is not None and not df_cached.empty
    assert "close" in df_cached.columns
