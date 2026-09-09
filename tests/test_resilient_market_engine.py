# ============================================================
# tests/test_resilient_market_engine.py
# ARGUS — Unit Tests for Enterprise SRE Market Data Resilience Engine
# ============================================================

import time
import io
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import requests

from core.resilient_market_engine import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    RetryPolicy,
    FreshnessLevel,
    MarketFreshnessEvaluator,
    MarketDataEnvelope,
    StooqDataProvider,
    ResilientMarketDataFetcher,
    with_circuit_breaker,
)


class TestCircuitBreaker(unittest.TestCase):
    """Test unitari per la macchina a stati finiti del Circuit Breaker."""

    def setUp(self):
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_sec=0.2,  # 200ms per test rapido
            half_open_success_needed=2
        )
        self.cb = CircuitBreaker("TestProvider", self.config)

    def test_initial_state_closed(self):
        self.assertEqual(self.cb.state, CircuitState.CLOSED)
        self.assertTrue(self.cb.allow_request())

    def test_failure_threshold_opens_circuit(self):
        self.cb.record_failure("err1")
        self.assertEqual(self.cb.state, CircuitState.CLOSED)
        self.cb.record_failure("err2")
        self.assertEqual(self.cb.state, CircuitState.CLOSED)
        
        # Terzo errore apre il circuito
        self.cb.record_failure("err3")
        self.assertEqual(self.cb.state, CircuitState.OPEN)
        self.assertFalse(self.cb.allow_request())  # Fast-Fail

    def test_recovery_transition_to_half_open_and_closed(self):
        # Forza apertura
        for _ in range(3):
            self.cb.record_failure("err")
        self.assertEqual(self.cb.state, CircuitState.OPEN)

        # Attende scadenza del timeout di recupero
        time.sleep(0.25)
        self.assertTrue(self.cb.allow_request())
        self.assertEqual(self.cb.state, CircuitState.HALF_OPEN)

        # 1° successo in half-open mantiene half-open
        self.cb.record_success()
        self.assertEqual(self.cb.state, CircuitState.HALF_OPEN)

        # 2° successo chiude definitivamente il circuito
        self.cb.record_success()
        self.assertEqual(self.cb.state, CircuitState.CLOSED)
        self.assertTrue(self.cb.allow_request())

    def test_half_open_failure_reopens_immediately(self):
        for _ in range(3):
            self.cb.record_failure("err")
        time.sleep(0.25)
        self.cb.allow_request()
        self.assertEqual(self.cb.state, CircuitState.HALF_OPEN)

        # Un fallimento durante la prova pilota riapre subito il circuito
        self.cb.record_failure("probe_error")
        self.assertEqual(self.cb.state, CircuitState.OPEN)
        self.assertFalse(self.cb.allow_request())


class TestRetryPolicy(unittest.TestCase):
    """Test per la politica di backoff esponenziale con Full Jitter."""

    def setUp(self):
        self.policy = RetryPolicy(base_delay_sec=0.5, max_delay_sec=5.0)

    def test_retry_after_header_respected(self):
        backoff = self.policy.calculate_backoff(attempt=0, retry_after=3.5)
        self.assertEqual(backoff, 3.5)

    def test_jittered_backoff_bounds(self):
        for attempt in range(5):
            delay = self.policy.calculate_backoff(attempt)
            max_expected = min(5.0, 0.5 * (2 ** attempt))
            self.assertGreaterEqual(delay, 0.1)
            self.assertLessEqual(delay, max_expected + 0.001)


class TestMarketFreshnessEvaluator(unittest.TestCase):
    """Test per la classificazione dell'obsolescenza dei prezzi sincronizzata col calendario di borsa."""

    def test_empty_dataframe(self):
        freshness, as_of = MarketFreshnessEvaluator.evaluate(pd.DataFrame(), "AAPL")
        self.assertEqual(freshness, FreshnessLevel.OFFLINE_EMERGENCY)
        self.assertEqual(as_of, "N/A")

    def test_today_price_is_realtime(self):
        today = date.today()
        df = pd.DataFrame(
            {"close": [150.0, 155.0]},
            index=pd.DatetimeIndex([today - timedelta(days=1), today])
        )
        freshness, as_of = MarketFreshnessEvaluator.evaluate(df, "AAPL")
        self.assertEqual(freshness, FreshnessLevel.LIVE_REALTIME)
        self.assertEqual(as_of, today.strftime("%Y-%m-%d"))

    def test_crypto_staleness(self):
        today = date.today()
        # Crypto 5 giorni fa è stale
        df = pd.DataFrame(
            {"close": [50000.0]},
            index=pd.DatetimeIndex([today - timedelta(days=5)])
        )
        freshness, _ = MarketFreshnessEvaluator.evaluate(df, "BTC-EUR", is_crypto=True)
        self.assertEqual(freshness, FreshnessLevel.STALE_WARNING)


class TestStooqDataProvider(unittest.TestCase):
    """Test per il provider gratuito Stooq."""

    def test_ticker_mapping(self):
        self.assertEqual(StooqDataProvider._map_ticker("SPY"), "^spx")
        self.assertEqual(StooqDataProvider._map_ticker("QQQ"), "^ndx")
        self.assertEqual(StooqDataProvider._map_ticker("AAPL"), "aapl.us")
        self.assertEqual(StooqDataProvider._map_ticker("ISP.MI"), "isp.it")
        self.assertEqual(StooqDataProvider._map_ticker("BMW.DE"), "bmw.de")
        self.assertEqual(StooqDataProvider._map_ticker("EURUSD=X"), "eurusd")

    @patch("requests.get")
    def test_fetch_history_success(self, mock_get):
        csv_sample = (
            "Date,Open,High,Low,Close,Volume\n"
            "2024-01-02,180.0,182.0,179.0,181.5,50000000\n"
            "2024-01-03,181.5,183.0,180.5,182.0,45000000\n"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = csv_sample
        mock_get.return_value = mock_resp

        df = StooqDataProvider.fetch_history("AAPL", start_date="2024-01-01")
        self.assertIsNotNone(df)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("close", df.columns)
        self.assertEqual(df["close"].iloc[-1], 182.0)


class TestResilienceDecorator(unittest.TestCase):
    """Test per il decoratore @with_circuit_breaker."""

    def test_decorator_invokes_fallback_when_open(self):
        cb = CircuitBreaker("DecTest", CircuitBreakerConfig(failure_threshold=1))
        cb.record_failure("error")
        self.assertEqual(cb.state, CircuitState.OPEN)

        def fallback():
            return "FALLBACK_CALLED"

        @with_circuit_breaker(cb, fallback_fn=fallback)
        def primary_api():
            return "PRIMARY_CALLED"

        result = primary_api()
        self.assertEqual(result, "FALLBACK_CALLED")


if __name__ == "__main__":
    unittest.main()
