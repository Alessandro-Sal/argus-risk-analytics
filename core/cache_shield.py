# ============================================================
# core/cache_shield.py
# ARGUS — Risk Analytics & BI Platform
# Multi-Tier Caching & Rate-Limit Shield for yfinance API
# (Tier 1: Fast RAM LRU Cache | Tier 2: Persistent SQLite 24h TTL)
# ============================================================

import os
import time
import json
import sqlite3
import random
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np


CACHE_DB_PATH = Path("data") / "yfinance_cache.db"
DEFAULT_TTL_SECONDS = 86400  # 24 Ore di validità

# In-memory L1 cache dictionary
_L1_CACHE: Dict[str, Tuple[float, Any]] = {}


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
            payload TEXT,
            cached_at REAL,
            ttl_seconds REAL
        )
    """)
    conn.commit()
    return conn


def get_cached_ticker_history(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Recupera i dati storici dei prezzi con scudo multi-livello anti-429 Rate Limiting:
    1. Controllo L1 RAM Cache (istantaneo < 1ms)
    2. Controllo L2 SQLite Cache con TTL 24h
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
            return df_cached.copy()

    # 2. Tier 2: L2 SQLite Cache su Disco
    conn = _get_cache_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT payload, cached_at, ttl_seconds FROM yfinance_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cur.fetchone()
        if row and not force_refresh:
            payload_json, cached_at, row_ttl = row
            if (now - cached_at) < row_ttl:
                df_disk = pd.read_json(payload_json)
                if not df_disk.empty:
                    _L1_CACHE[cache_key] = (cached_at, df_disk)
                    return df_disk.copy()
    except Exception:
        pass

    # 3. Tier 3: Fetch con Rate-Limit Shield & Exponential Backoff
    df_downloaded = _fetch_yfinance_history_safe(clean_ticker, start_date, end_date)

    if df_downloaded is not None and not df_downloaded.empty:
        # Salva in L1 e L2
        _L1_CACHE[cache_key] = (now, df_downloaded)
        try:
            payload_str = df_downloaded.to_json(date_format="iso")
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO yfinance_cache (cache_key, ticker, data_type, payload, cached_at, ttl_seconds)
                VALUES (?, ?, 'history', ?, ?, ?)
            """, (cache_key, clean_ticker, payload_str, now, ttl_seconds))
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
            df_fallback = pd.read_json(row[0])
            if not df_fallback.empty:
                return df_fallback.copy()
    except Exception:
        pass

    return pd.DataFrame()


def _fetch_yfinance_history_safe(ticker: str, start_date: Optional[str], end_date: Optional[str]) -> Optional[pd.DataFrame]:
    """Scarica i prezzi da yfinance con fallback trasparente a Crypto Multi-Exchange Engine per crypto."""
    import yfinance as yf

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Polite throttling per evitare spike di traffico simultanei
            time.sleep(random.uniform(0.05, 0.15))
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
                return df
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "429" in err_msg or "rate limit" in err_msg:
                # Exponential backoff con jitter casuale
                sleep_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)
            else:
                break

    # Fallback su Crypto Multi-Exchange Provider (Binance, Kraken, CoinGecko)
    try:
        from core.crypto_provider import is_crypto_symbol, fetch_crypto_history_unified
        if is_crypto_symbol(ticker):
            df_crypto = fetch_crypto_history_unified(ticker, start_date=start_date, end_date=end_date)
            if df_crypto is not None and not df_crypto.empty:
                return df_crypto
    except Exception:
        pass

    return None



def get_cached_ticker_info(
    ticker: str,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    force_refresh: bool = False
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
        cur.execute(
            "SELECT payload, cached_at, ttl_seconds FROM yfinance_cache WHERE cache_key = ?",
            (cache_key,)
        )
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
                            "shares": getattr(fi, "shares", None)
                        }
                except Exception:
                    pass
                    
            if info_data:
                _L1_CACHE[cache_key] = (now, info_data)
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT OR REPLACE INTO yfinance_cache (cache_key, ticker, data_type, payload, cached_at, ttl_seconds)
                        VALUES (?, ?, 'info', ?, ?, ?)
                    """, (cache_key, clean_ticker, json.dumps(info_data), now, ttl_seconds))
                    conn.commit()
                except Exception:
                    pass
                return info_data
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "429" in err_msg or "rate limit" in err_msg:
                time.sleep((2 ** attempt) + random.uniform(0.1, 0.3))
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
        "shield_version": "2.0 (Dual-Tier LRU + SQLite)"
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
