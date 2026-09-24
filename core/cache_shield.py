# ============================================================
# core/cache_shield.py
# ARGUS — Risk Analytics & BI Platform
# Multi-Tier Caching & Rate-Limit Shield for yfinance API
# (Tier 1: Fast RAM LRU Cache | Tier 2: Persistent SQLite 24h TTL)
# ============================================================

import io
import json
import os
import random
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    import pyarrow as pa
    import pyarrow.feather as feather
    HAS_PYARROW = True
except ImportError:
    pa = None
    feather = None
    HAS_PYARROW = False

CACHE_DB_PATH = Path("data") / "yfinance_cache.db"
DEFAULT_TTL_SECONDS = 86400  # 24 Ore di validità

# In-memory L1 cache dictionary
_L1_CACHE: Dict[str, Tuple[float, Any]] = {}


def _df_to_binary_payload(df: pd.DataFrame) -> bytes:
    """Serializza un DataFrame in formato binario compatto Apache Arrow Feather ad alte prestazioni."""
    if not HAS_PYARROW:
        return df.to_json(date_format="iso").encode("utf-8")

    buf = io.BytesIO()
    df_to_write = df.copy()
    if isinstance(df_to_write.index, pd.DatetimeIndex):
        df_to_write = df_to_write.reset_index()
    feather.write_feather(df_to_write, buf, compression="zstd")
    return buf.getvalue()


def _binary_payload_to_df(payload: Union[bytes, str]) -> pd.DataFrame:
    """Deserializza automaticamente sia buffer binari Arrow Feather che stringhe legacy JSON."""
    if payload is None:
        return pd.DataFrame()

    if isinstance(payload, str):
        try:
            df = pd.read_json(io.StringIO(payload))
            if not df.empty:
                for c in ["date", "Date", "price_date"]:
                    if c in df.columns:
                        df[c] = pd.to_datetime(df[c])
                        df = df.set_index(c)
                        break
            return df
        except Exception:
            return pd.DataFrame()

    if isinstance(payload, bytes):
        if payload.strip().startswith((b"{", b"[")):
            try:
                text_payload = payload.decode("utf-8", errors="ignore")
                return pd.read_json(io.StringIO(text_payload))
            except Exception:
                pass

        if HAS_PYARROW:
            try:
                buf = io.BytesIO(payload)
                df = feather.read_feather(buf)
                for c in ["date", "Date", "price_date", "index"]:
                    if c in df.columns:
                        try:
                            df[c] = pd.to_datetime(df[c])
                            df = df.set_index(c)
                            break
                        except Exception:
                            pass
                return df
            except Exception:
                pass

    return pd.DataFrame()


def _get_cache_connection() -> sqlite3.Connection:
    """Restituisce una connessione SQLite thread-safe per il Tier 2 di cache su disco."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB_PATH), check_same_thread=False, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
    except Exception:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yfinance_cache (
            cache_key TEXT PRIMARY KEY,
            ticker TEXT,
            data_type TEXT,
            payload BLOB,
            cached_at REAL,
            ttl_seconds REAL
        )
    """)
    conn.commit()
    return conn


def _normalize_history_df(df: pd.DataFrame) -> pd.DataFrame:
    """Garantisce che il DataFrame storico abbia indice DatetimeIndex tz-naive e normalizzato a livello giornaliero."""
    if df is None or df.empty:
        return df
    if hasattr(df.index, "tz") and df.index.tz is not None:
        try:
            df.index = df.index.tz_localize(None)
        except Exception:
            try:
                df.index = df.index.tz_convert(None)
            except Exception:
                pass
    try:
        df.index = df.index.normalize()
    except Exception:
        pass
    if getattr(df.index, "has_duplicates", False):
        df = df[~df.index.duplicated(keep="last")]
    return df


def get_cached_ticker_history(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Recupera i dati storici dei prezzi con scudo multi-livello anti-429 Rate Limiting:
    1. Controllo L1 RAM Cache (istantaneo < 1ms)
    2. Controllo L2 SQLite Cache con Arrow Feather binario e TTL 24h
    3. Chiamata protetta a yfinance con exponential backoff in caso di rate limit
    4. Fallback offline seamless in caso di mancata connessione.
    """
    clean_ticker = str(ticker).strip().upper()
    cache_key = f"hist_{clean_ticker}_{start_date}_{end_date}"
    now = time.time()

    # 1. Tier 1: L1 RAM Cache
    if not force_refresh and cache_key in _L1_CACHE:
        timestamp, df_cached = _L1_CACHE[cache_key]
        if (now - timestamp) < ttl_seconds and isinstance(df_cached, pd.DataFrame) and not df_cached.empty:
            return _normalize_history_df(df_cached.copy())

    # 2. Tier 2: L2 SQLite Cache su Disco
    conn = _get_cache_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT payload, cached_at, ttl_seconds FROM yfinance_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        if row and not force_refresh:
            payload_data, cached_at, row_ttl = row
            if (now - cached_at) < row_ttl:
                df_disk = _binary_payload_to_df(payload_data)
                if not df_disk.empty:
                    df_disk = _normalize_history_df(df_disk)
                    _L1_CACHE[cache_key] = (cached_at, df_disk)
                    return df_disk.copy()
    except Exception:
        pass

    # 3. Tier 3: Fetch con Rate-Limit Shield & Exponential Backoff
    df_downloaded = _fetch_yfinance_history_safe(clean_ticker, start_date, end_date)

    if df_downloaded is not None and not df_downloaded.empty:
        df_downloaded = _normalize_history_df(df_downloaded)
        # Salva in L1 e L2
        _L1_CACHE[cache_key] = (now, df_downloaded)
        try:
            payload_bin = _df_to_binary_payload(df_downloaded)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO yfinance_cache (cache_key, ticker, data_type, payload, cached_at, ttl_seconds)
                VALUES (?, ?, 'history', ?, ?, ?)
            """,
                (cache_key, clean_ticker, sqlite3.Binary(payload_bin) if isinstance(payload_bin, bytes) else payload_bin, now, ttl_seconds),
            )
            conn.commit()
        except Exception:
            pass
        return df_downloaded.copy()

    # 4. Fallback: Se la rete fallisce o restituisce 429, usa il dato in cache anche se scaduto
    try:
        cur = conn.cursor()
        cur.execute("SELECT payload FROM yfinance_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        if row:
            df_fallback = _binary_payload_to_df(row[0])
            if not df_fallback.empty:
                return _normalize_history_df(df_fallback.copy())
    except Exception:
        pass

    return pd.DataFrame()


def _fetch_yfinance_history_safe(
    ticker: str, start_date: Optional[str], end_date: Optional[str]
) -> Optional[pd.DataFrame]:
    """Scarica i prezzi da yfinance con Circuit Breaker e fallback a Stooq (equities/FX) e Crypto Engine."""
    import yfinance as yf

    try:
        from core.resilient_market_engine import StooqDataProvider, stooq_circuit_breaker, yahoo_circuit_breaker
    except ImportError:
        yahoo_circuit_breaker = None
        StooqDataProvider = None
        stooq_circuit_breaker = None

    yf_success = False
    if yahoo_circuit_breaker is None or yahoo_circuit_breaker.allow_request():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Polite throttling per evitare spike di traffico simultanei
                time.sleep(random.uniform(0.04, 0.10))
                yf_obj = yf.Ticker(ticker)
                kwargs = {}
                if start_date:
                    kwargs["start"] = start_date
                if end_date:
                    kwargs["end"] = end_date
                if not kwargs:
                    kwargs["period"] = "2y"

                df = yf_obj.history(**kwargs)
                if df is not None and not df.empty:
                    # Normalizza le colonne in minuscolo
                    df.columns = [c.lower() for c in df.columns]
                    if yahoo_circuit_breaker:
                        yahoo_circuit_breaker.record_success()
                    yf_success = True
                    return df
            except Exception as e:
                err_msg = str(e).lower()
                if "too many requests" in err_msg or "429" in err_msg or "rate limit" in err_msg:
                    # Exponential backoff con jitter casuale
                    sleep_time = (2**attempt) + random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
                else:
                    break

        if not yf_success and yahoo_circuit_breaker:
            yahoo_circuit_breaker.record_failure(f"Fallimento yfinance per {ticker}")

    # Fallback 1: Crypto Multi-Exchange Provider (Binance, Kraken, CoinGecko)
    try:
        from core.crypto_provider import fetch_crypto_history_unified, is_crypto_symbol

        if is_crypto_symbol(ticker):
            df_crypto = fetch_crypto_history_unified(ticker, start_date=start_date, end_date=end_date)
            if df_crypto is not None and not df_crypto.empty:
                return df_crypto
    except Exception:
        pass

    # Fallback 2: Stooq Free Historical Data Provider per non-crypto (azioni, ETF, indici, cambi FX)
    try:
        from core.crypto_provider import is_crypto_symbol

        is_crypto = is_crypto_symbol(ticker)
    except Exception:
        is_crypto = "-" in ticker or "/" in ticker

    if not is_crypto and StooqDataProvider and (stooq_circuit_breaker is None or stooq_circuit_breaker.allow_request()):
        try:
            df_stooq = StooqDataProvider.fetch_history(ticker, start_date=start_date, end_date=end_date)
            if df_stooq is not None and not df_stooq.empty:
                if stooq_circuit_breaker:
                    stooq_circuit_breaker.record_success()
                return df_stooq
        except Exception as e_stooq:
            if stooq_circuit_breaker:
                stooq_circuit_breaker.record_failure(str(e_stooq))

    return None


def get_cached_ticker_info(
    ticker: str, ttl_seconds: float = DEFAULT_TTL_SECONDS, force_refresh: bool = False
) -> Dict[str, Any]:
    """Recupera i metadati aziendali (settore, multipli, bilanci) con cache SQLite."""
    clean_ticker = str(ticker).strip().upper()
    cache_key = f"info_{clean_ticker}"
    now = time.time()

    # L1 RAM Cache
    if not force_refresh and cache_key in _L1_CACHE:
        timestamp, info_cached = _L1_CACHE[cache_key]
        if (now - timestamp) < ttl_seconds and isinstance(info_cached, dict) and info_cached:
            return info_cached

    # L2 SQLite Cache
    conn = _get_cache_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT payload, cached_at, ttl_seconds FROM yfinance_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        if row and not force_refresh:
            payload_json, cached_at, row_ttl = row
            if (now - cached_at) < row_ttl:
                info_disk = json.loads(payload_json)
                _L1_CACHE[cache_key] = (cached_at, info_disk)
                return info_disk
    except Exception:
        pass

    # Fetch yfinance info
    import yfinance as yf

    info_data = {}
    for attempt in range(2):
        try:
            time.sleep(random.uniform(0.04, 0.12))
            yf_obj = yf.Ticker(clean_ticker)
            info_data = yf_obj.info or {}

            # Se yf.info è vuoto o fallisce, prova fast_info come fallback leggero
            if not info_data or len(info_data) < 4:
                try:
                    fi = yf_obj.fast_info
                    if fi:
                        info_data = {
                            "shortName": clean_ticker,
                            "currentPrice": getattr(fi, "last_price", getattr(fi, "previous_close", None)),
                            "regularMarketPrice": getattr(fi, "last_price", getattr(fi, "previous_close", None)),
                            "marketCap": getattr(fi, "market_cap", None),
                            "currency": getattr(fi, "currency", "USD"),
                            "fiftyDayAverage": getattr(fi, "fifty_day_average", None),
                            "twoHundredDayAverage": getattr(fi, "two_hundred_day_average", None),
                            "shares": getattr(fi, "shares", None),
                        }
                except Exception:
                    pass

            if info_data:
                _L1_CACHE[cache_key] = (now, info_data)
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO yfinance_cache (cache_key, ticker, data_type, payload, cached_at, ttl_seconds)
                        VALUES (?, ?, 'info', ?, ?, ?)
                    """,
                        (cache_key, clean_ticker, json.dumps(info_data), now, ttl_seconds),
                    )
                    conn.commit()
                except Exception:
                    pass
                return info_data
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "429" in err_msg or "rate limit" in err_msg:
                time.sleep((2**attempt) + random.uniform(0.1, 0.3))
            else:
                break

    # Fallback to existing disk info
    try:
        cur = conn.cursor()
        cur.execute("SELECT payload FROM yfinance_cache WHERE cache_key = ?", (cache_key,))
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
    except Exception:
        pass

    return {}


def get_cache_stats() -> Dict[str, Any]:
    """Restituisce statistiche operative e metriche di salute della cache di sistema."""
    conn = _get_cache_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM yfinance_cache")
    total_entries, distinct_tickers = cur.fetchone()

    cur.execute("SELECT SUM(LENGTH(payload)) FROM yfinance_cache")
    size_bytes = cur.fetchone()[0] or 0

    db_size_kb = 0.0
    if CACHE_DB_PATH.exists():
        db_size_kb = os.path.getsize(CACHE_DB_PATH) / 1024.0

    return {
        "l1_memory_items": len(_L1_CACHE),
        "l2_disk_entries": total_entries,
        "distinct_tickers": distinct_tickers,
        "payload_size_kb": round(size_bytes / 1024.0, 2),
        "db_file_size_kb": round(db_size_kb, 2),
        "status": "🟢 Active & Shielded",
        "shield_version": "2.0 (Dual-Tier LRU + SQLite)",
    }


def clear_cache(data_type: Optional[str] = None) -> int:
    """Svuota la cache L1 e L2 (opzionalmente filtrata per tipo 'history' o 'info')."""
    global _L1_CACHE
    _L1_CACHE.clear()

    conn = _get_cache_connection()
    cur = conn.cursor()
    if data_type:
        cur.execute("DELETE FROM yfinance_cache WHERE data_type = ?", (data_type,))
    else:
        cur.execute("DELETE FROM yfinance_cache")
    deleted = cur.rowcount
    conn.commit()
    return deleted
