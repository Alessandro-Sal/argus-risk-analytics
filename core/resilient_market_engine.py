# ==============================================================================
# core/resilient_market_engine.py
# ARGUS — Enterprise SRE Market Data Resilience Engine
# Features:
#   - Circuit Breaker a 3 Stati (CLOSED, OPEN, HALF_OPEN) con Fast-Fail
#   - Exponential Backoff con Full Jitter & rispetto di Retry-After
#   - Multi-Source Fallback Hierarchy (Yahoo -> Stooq -> Offline Parquet/SQLite)
#   - Staleness & Market Calendar Detector con Metadata Envelopes
#   - Pre-configured Circuit Breakers per provider di mercato
# ==============================================================================

import io
import time
import random
import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Generic
from pathlib import Path

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger("ARGUS.ResilientMarketEngine")


# ── 1. GESTIONE STATI CIRCUIT BREAKER ──────────────────────────────────────────

class CircuitState(Enum):
    CLOSED = "CLOSED"        # Operativo: il traffico passa
    OPEN = "OPEN"            # Guasto: fast-fail immediato su fallback
    HALF_OPEN = "HALF_OPEN"  # Test di recupero: consente una richiesta pilota


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3          # N. errori consecutivi per aprire il circuito
    recovery_timeout_sec: float = 60.0   # Tempo di attesa in stato OPEN prima di tentare HALF_OPEN
    half_open_success_needed: int = 2   # Successi consecutivi in HALF_OPEN per chiudere il circuito


class CircuitBreaker:
    """
    Circuit Breaker Thread-Safe conforme a Martin Fowler / Netflix Hystrix pattern.
    Evita il sovraccarico di endpoint in errore (429/503) garantendo il Fast-Fail.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """Determina se la richiesta può essere inviata al provider esterno."""
        with self._lock:
            now = time.time()
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if (now - self.last_state_change) >= self.config.recovery_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    logger.warning(f"⚠️ [CircuitBreaker:{self.name}] Transizione verso HALF_OPEN (sonda di recupero)")
                    return True
                return False  # Fast-Fail: circuito ancora aperto
            elif self.state == CircuitState.HALF_OPEN:
                return True
            return False

    def record_success(self):
        """Registra un esito positivo consolidando o ripristinando il circuito."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_success_needed:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = time.time()
                    logger.info(f"✅ [CircuitBreaker:{self.name}] Servizio ripristinato: circuito tornato CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self, error_info: str = ""):
        """Registra un fallimento; al superamento della soglia apre il circuito."""
        with self._lock:
            self.failure_count += 1
            now = time.time()
            if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = now
                self.success_count = 0
                logger.error(
                    f"🛑 [CircuitBreaker:{self.name}] SOGLIA CRITICA RAGGIUNTA ({self.failure_count} errori). "
                    f"Circuito OPEN per {self.config.recovery_timeout_sec}s. Causa: {error_info}"
                )

    def reset(self):
        """Ripristina manualmente il circuito allo stato CLOSED."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_state_change = time.time()


# Singleton breakers di sistema preconfigurati
yahoo_circuit_breaker = CircuitBreaker("YahooFinance", CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=45.0))
stooq_circuit_breaker = CircuitBreaker("Stooq", CircuitBreakerConfig(failure_threshold=2, recovery_timeout_sec=30.0))
fred_circuit_breaker = CircuitBreaker("FRED", CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=45.0))
ecb_circuit_breaker = CircuitBreaker("ECB", CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=45.0))
crypto_circuit_breaker = CircuitBreaker("CryptoExchanges", CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=30.0))
isin_circuit_breaker = CircuitBreaker("YahooISIN", CircuitBreakerConfig(failure_threshold=3, recovery_timeout_sec=30.0))


# ── 2. RETRY POLICY CON FULL JITTER ───────────────────────────────────────────

@dataclass
class RetryPolicy:
    """
    Politica di retry con backoff esponenziale e Full Jitter (AWS Architecture pattern).
    Supporta il parsing dinamico dell'header HTTP 'Retry-After'.
    """
    max_retries: int = 3
    base_delay_sec: float = 0.5
    max_delay_sec: float = 8.0
    retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)

    def calculate_backoff(self, attempt: int, retry_after: Optional[float] = None) -> float:
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.max_delay_sec)
        # Full Jitter AWS Formula: t = random(0.1, min(max_delay, base * 2^attempt))
        calculated = min(self.max_delay_sec, self.base_delay_sec * (2 ** attempt))
        return random.uniform(0.1, calculated)


# ── 3. DATA ENVELOPE & STALENESS DETECTOR ──────────────────────────────────────

class FreshnessLevel(Enum):
    LIVE_REALTIME = "LIVE_REALTIME"
    END_OF_DAY_FRESH = "END_OF_DAY_FRESH"
    MARKET_CLOSED_BENIGN = "MARKET_CLOSED_BENIGN"
    STALE_WARNING = "STALE_WARNING"
    OFFLINE_EMERGENCY = "OFFLINE_EMERGENCY"


@dataclass
class MarketDataEnvelope:
    """Busta di trasporto dati con tracciabilità dell'origine e livello di freschezza."""
    ticker: str
    data: pd.DataFrame
    source: str
    freshness: FreshnessLevel
    as_of_date: str
    latency_ms: float
    is_fallback: bool
    warning_msg: Optional[str] = None


class MarketFreshnessEvaluator:
    """Verifica l'obsolescenza dei prezzi sincronizzandosi con il calendario di mercato."""

    @staticmethod
    def evaluate(df: pd.DataFrame, ticker: str, is_crypto: bool = False) -> Tuple[FreshnessLevel, str]:
        if df is None or df.empty:
            return FreshnessLevel.OFFLINE_EMERGENCY, "N/A"

        try:
            if isinstance(df.index, pd.DatetimeIndex):
                last_dt = pd.to_datetime(df.index[-1]).date()
            elif "date" in df.columns:
                last_dt = pd.to_datetime(df["date"].iloc[-1]).date()
            else:
                last_dt = date.today()
        except Exception:
            last_dt = date.today()

        today = date.today()
        as_of_str = last_dt.strftime("%Y-%m-%d")

        if is_crypto:
            delta_days = (today - last_dt).days
            if delta_days == 0:
                return FreshnessLevel.LIVE_REALTIME, as_of_str
            elif delta_days == 1:
                return FreshnessLevel.END_OF_DAY_FRESH, as_of_str
            else:
                return FreshnessLevel.STALE_WARNING, as_of_str

        # Per Equity/Bond/FX: esclusione di weekend e orari di chiusura
        weekday = today.weekday()
        if weekday == 5:  # Sabato
            expected_date = today - timedelta(days=1)
        elif weekday == 6:  # Domenica
            expected_date = today - timedelta(days=2)
        elif weekday == 0 and datetime.now().hour < 10:  # Lunedì prima dell'apertura
            expected_date = today - timedelta(days=3)
        else:
            expected_date = today - timedelta(days=1)

        if last_dt >= today:
            return FreshnessLevel.LIVE_REALTIME, as_of_str
        elif last_dt >= expected_date:
            return FreshnessLevel.END_OF_DAY_FRESH, as_of_str
        elif weekday in (5, 6) and (today - last_dt).days <= 3:
            return FreshnessLevel.MARKET_CLOSED_BENIGN, as_of_str
        else:
            return FreshnessLevel.STALE_WARNING, as_of_str


# ── 4. CONNETTORE FALLBACK GRATUITO: STOOQ DATA PROVIDER ───────────────────────

class StooqDataProvider:
    """Connettore ad alta affidabilità per dati storici giornalieri mondiali senza API Key."""

    BASE_URL = "https://stooq.com/q/d/l/"

    @staticmethod
    def _map_ticker(ticker: str) -> str:
        clean = ticker.strip().upper()
        if clean in ["SPY", "^GSPC"]: return "^spx"
        if clean in ["QQQ", "^IXIC"]: return "^ndx"
        if clean.endswith("=X"):
            return clean[:-2].lower()
        if clean.endswith(".MI"):
            return f"{clean[:-3].lower()}.it"
        if clean.endswith(".DE"):
            return f"{clean[:-3].lower()}.de"
        if clean.endswith(".PA"):
            return f"{clean[:-3].lower()}.fr"
        if clean.endswith(".L"):
            return f"{clean[:-2].lower()}.uk"
        if not "." in clean and not "-" in clean and not "=" in clean:
            return f"{clean.lower()}.us"
        return clean.lower()

    @classmethod
    def fetch_history(
        cls,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeout: float = 6.0
    ) -> Optional[pd.DataFrame]:
        stooq_sym = cls._map_ticker(ticker)
        url = f"{cls.BASE_URL}?s={stooq_sym}&i=d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200 and resp.text and "Date,Open,High,Low,Close" in resp.text:
                df = pd.read_csv(io.StringIO(resp.text))
                if not df.empty and "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df = df.rename(columns={
                        "Date": "date", "Open": "open", "High": "high",
                        "Low": "low", "Close": "close", "Volume": "volume"
                    }).set_index("date").sort_index()
                    if start_date:
                        df = df[df.index >= pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df.index <= pd.to_datetime(end_date)]
                    if not df.empty:
                        return df
        except Exception as e:
            logger.debug(f"Stooq download failed for {ticker}: {e}")
        return None


# ── 5. RESILIENT MARKET DATA FETCHER (FACADE CENTRALE) ─────────────────────────

class ResilientMarketDataFetcher:
    """
    Motore Unificato di Ingestione Dati Finanziari con:
    - Circuit Breakers dedicati per sorgente (Yahoo, Stooq, Binance, FRED)
    - Fallback a caldo automatico multilivello
    - Cache Parquet offline indicizzata
    - Confezionamento trasparente in MarketDataEnvelope
    """

    def __init__(self, storage_dir: str = "data/market_lake"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.retry_policy = RetryPolicy()

    def _load_offline_parquet(self, ticker: str) -> Optional[pd.DataFrame]:
        clean_name = ticker.replace("/", "_").replace("^", "_").replace(":", "_")
        file_path = self.storage_dir / f"{clean_name}.parquet"
        if file_path.exists():
            try:
                df = pd.read_parquet(file_path)
                return df
            except Exception as e:
                logger.warning(f"Errore lettura parquet locale {file_path}: {e}")
        return None

    def _save_offline_parquet(self, ticker: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        clean_name = ticker.replace("/", "_").replace("^", "_").replace(":", "_")
        file_path = self.storage_dir / f"{clean_name}.parquet"
        try:
            df.to_parquet(file_path, compression="snappy")
        except Exception as e:
            logger.debug(f"Impossibile archiviare parquet {file_path}: {e}")

    def fetch_price_history(
        self,
        ticker: str,
        start_date: Optional[str] = "2020-01-01",
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> MarketDataEnvelope:
        clean_ticker = str(ticker).strip().upper()
        t0 = time.time()
        is_crypto = "-" in clean_ticker or "/" in clean_ticker

        # ── TENTATIVO 1: CACHE SHIELD ESISTENTE (L1/L2) ──────────────────────
        if not force_refresh:
            try:
                from core.cache_shield import get_cached_ticker_history
                df_cache = get_cached_ticker_history(clean_ticker, start_date=start_date, end_date=end_date)
                if df_cache is not None and not df_cache.empty:
                    freshness, as_of = MarketFreshnessEvaluator.evaluate(df_cache, clean_ticker, is_crypto)
                    if freshness in (FreshnessLevel.LIVE_REALTIME, FreshnessLevel.END_OF_DAY_FRESH, FreshnessLevel.MARKET_CLOSED_BENIGN):
                        return MarketDataEnvelope(
                            ticker=clean_ticker,
                            data=df_cache,
                            source="CacheShield (L1/L2)",
                            freshness=freshness,
                            as_of_date=as_of,
                            latency_ms=round((time.time() - t0) * 1000, 2),
                            is_fallback=False
                        )
            except Exception:
                pass

        # ── TENTATIVO 2: YAHOO FINANCE (se circuito permesso) ─────────────────
        if yahoo_circuit_breaker.allow_request():
            for attempt in range(self.retry_policy.max_retries):
                try:
                    import yfinance as yf
                    time.sleep(random.uniform(0.04, 0.08))
                    yf_t = yf.Ticker(clean_ticker)
                    kwargs = {}
                    if start_date: kwargs["start"] = start_date
                    if end_date: kwargs["end"] = end_date
                    if not kwargs: kwargs["period"] = "2y"

                    df = yf_t.history(**kwargs)
                    if df is not None and not df.empty:
                        df.columns = [c.lower() for c in df.columns]
                        yahoo_circuit_breaker.record_success()
                        self._save_offline_parquet(clean_ticker, df)
                        freshness, as_of = MarketFreshnessEvaluator.evaluate(df, clean_ticker, is_crypto)
                        return MarketDataEnvelope(
                            ticker=clean_ticker,
                            data=df,
                            source="YahooFinance (Primary)",
                            freshness=freshness,
                            as_of_date=as_of,
                            latency_ms=round((time.time() - t0) * 1000, 2),
                            is_fallback=False
                        )
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                        sleep_time = self.retry_policy.calculate_backoff(attempt)
                        logger.warning(f"Throttling Yahoo 429 su {clean_ticker}, backoff {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                    else:
                        break
            yahoo_circuit_breaker.record_failure(f"Errore persistente su {clean_ticker}")

        # ── TENTATIVO 3: STOOQ FREE FALLBACK (per non-crypto) ─────────────────
        if not is_crypto and stooq_circuit_breaker.allow_request():
            try:
                df_stooq = StooqDataProvider.fetch_history(clean_ticker, start_date=start_date, end_date=end_date)
                if df_stooq is not None and not df_stooq.empty:
                    stooq_circuit_breaker.record_success()
                    self._save_offline_parquet(clean_ticker, df_stooq)
                    freshness, as_of = MarketFreshnessEvaluator.evaluate(df_stooq, clean_ticker, is_crypto)
                    return MarketDataEnvelope(
                        ticker=clean_ticker,
                        data=df_stooq,
                        source="Stooq (Secondary Fallback)",
                        freshness=freshness,
                        as_of_date=as_of,
                        latency_ms=round((time.time() - t0) * 1000, 2),
                        is_fallback=True,
                        warning_msg="Dati acquisiti da Stooq per indisponibilità temporanea del provider primario."
                    )
            except Exception as e_stooq:
                stooq_circuit_breaker.record_failure(str(e_stooq))

        # ── TENTATIVO 4: OFFLINE COLD STORAGE (Parquet / SQLite Fallback) ──────
        df_local = self._load_offline_parquet(clean_ticker)
        if df_local is not None and not df_local.empty:
            freshness, as_of = MarketFreshnessEvaluator.evaluate(df_local, clean_ticker, is_crypto)
            return MarketDataEnvelope(
                ticker=clean_ticker,
                data=df_local,
                source="Local Parquet Lake (Offline)",
                freshness=FreshnessLevel.OFFLINE_EMERGENCY,
                as_of_date=as_of,
                latency_ms=round((time.time() - t0) * 1000, 2),
                is_fallback=True,
                warning_msg=f"⚠️ Connettività esterna non disponibile. Prezzi storici offline fermi al {as_of}."
            )

        # Ultimo tentativo: prova a leggere qualunque dato scaduto dalla cache SQLite
        try:
            from core.cache_shield import _get_cache_connection
            conn = _get_cache_connection()
            cur = conn.cursor()
            cur.execute("SELECT payload FROM yfinance_cache WHERE ticker = ? AND data_type = 'history' ORDER BY cached_at DESC LIMIT 1", (clean_ticker,))
            row = cur.fetchone()
            if row:
                df_stale = pd.read_json(row[0])
                if not df_stale.empty:
                    freshness, as_of = MarketFreshnessEvaluator.evaluate(df_stale, clean_ticker, is_crypto)
                    return MarketDataEnvelope(
                        ticker=clean_ticker,
                        data=df_stale,
                        source="SQLite Expired Cache (Emergency)",
                        freshness=FreshnessLevel.OFFLINE_EMERGENCY,
                        as_of_date=as_of,
                        latency_ms=round((time.time() - t0) * 1000, 2),
                        is_fallback=True,
                        warning_msg=f"⚠️ Prezzi di emergenza estratti dalla cache locale (datazione: {as_of})."
                    )
        except Exception:
            pass

        return MarketDataEnvelope(
            ticker=clean_ticker,
            data=pd.DataFrame(),
            source="None",
            freshness=FreshnessLevel.OFFLINE_EMERGENCY,
            as_of_date="N/A",
            latency_ms=round((time.time() - t0) * 1000, 2),
            is_fallback=True,
            warning_msg=f"Errore critico: impossibile reperire dati per {clean_ticker} su nessun provider."
        )


# ── 6. DECORATORE REUSABILE PER ENDPOINT E CHIAMATE GENERICHE ──────────────────

def with_circuit_breaker(
    breaker: CircuitBreaker,
    retry_policy: Optional[RetryPolicy] = None,
    fallback_fn: Optional[Callable[..., Any]] = None
):
    """
    Decoratore SRE per funzioni di fetch di rete.
    Integra circuit breaking, retry con jitter e invocazione automatica di fallback.
    """
    policy = retry_policy or RetryPolicy()

    def decorator(func: Callable[..., Any]):
        def wrapper(*args, **kwargs):
            if not breaker.allow_request():
                logger.warning(f"🛑 [Fast-Fail] Circuito {breaker.name} OPEN. Esecuzione fallback immediato.")
                if fallback_fn:
                    return fallback_fn(*args, **kwargs)
                return None

            for attempt in range(policy.max_retries):
                try:
                    res = func(*args, **kwargs)
                    breaker.record_success()
                    return res
                except requests.exceptions.RequestException as req_err:
                    status_code = getattr(getattr(req_err, "response", None), "status_code", None)
                    retry_after = None
                    if req_err.response is not None:
                        ra_hdr = req_err.response.headers.get("Retry-After")
                        if ra_hdr and ra_hdr.isdigit():
                            retry_after = float(ra_hdr)

                    if status_code in policy.retryable_status_codes:
                        wait_t = policy.calculate_backoff(attempt, retry_after)
                        logger.warning(f"⚠️ [{breaker.name}] Errore HTTP {status_code}. Backoff {wait_t:.2f}s...")
                        time.sleep(wait_t)
                    else:
                        breaker.record_failure(str(req_err))
                        break
                except Exception as ex:
                    breaker.record_failure(str(ex))
                    break

            breaker.record_failure("Tentativi di retry esauriti.")
            if fallback_fn:
                return fallback_fn(*args, **kwargs)
            return None
        return wrapper
    return decorator
