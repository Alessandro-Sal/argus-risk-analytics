# ============================================================
# core/crypto_provider.py
# ARGUS — Risk Analytics & BI Platform
# Resilient Multi-Exchange Crypto Market Data Engine
# Providers: Binance Public REST, Kraken Public REST, CoinGecko REST
# Optional: CCXT unified framework
# ============================================================

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Mappatura dei simboli comuni verso gli ID CoinGecko
COINGECKO_IDS: Dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "DOGE": "dogecoin",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "SEI": "sei-network",
    "FDUSD": "first-digital-usd",
    "USDT": "tether",
    "USDC": "usd-coin",
    "SUI": "sui",
    "NEAR": "near",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "ICP": "internet-computer",
    "ATOM": "cosmos",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
}

# Mappatura per Kraken pair nomenclature
KRAKEN_PAIRS: Dict[str, str] = {
    "BTC-EUR": "XBTEUR",
    "ETH-EUR": "XETHZEUR",
    "SOL-EUR": "SOLEUR",
    "ADA-EUR": "ADAEUR",
    "DOT-EUR": "DOTEUR",
    "XRP-EUR": "XXRPZEUR",
    "BTC-USD": "XBTUSD",
    "ETH-USD": "XETHZUSD",
}


def is_crypto_symbol(ticker: str) -> bool:
    """Verifica se il ticker rappresenta un asset crittografico."""
    t = str(ticker or "").strip().upper()
    if t.endswith("-EUR") or t.endswith("-USD") or t.endswith("-USDT"):
        base = t.split("-")[0]
        if base in COINGECKO_IDS or base in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "SEI", "FDUSD"]:
            return True
    if "/" in t:
        base = t.split("/")[0]
        if base in COINGECKO_IDS:
            return True
    if t in COINGECKO_IDS:
        return True
    return False


def normalize_crypto_pair(ticker: str) -> Tuple[str, str]:
    """Scompone un ticker come 'BTC-EUR' o 'BTC/EUR' in ('BTC', 'EUR')."""
    t = str(ticker or "").strip().upper()
    if "-" in t:
        parts = t.split("-")
        return parts[0], parts[1]
    if "/" in t:
        parts = t.split("/")
        return parts[0], parts[1]
    return t, "EUR"


def fetch_binance_ohlcv(base: str, quote: str = "EUR", limit: int = 1000, timeout: float = 5.0) -> Optional[pd.DataFrame]:
    """
    Scarica le candele giornaliere da Binance Public Market Data API.
    Se la coppia diretta in EUR non esiste, tenta la coppia in USDT e converte.
    """
    base = base.upper()
    quote = quote.upper()
    direct_symbol = f"{base}{quote}"

    url = f"https://api.binance.com/api/v3/klines?symbol={direct_symbol}&interval=1d&limit={limit}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return _parse_binance_klines(data)
    except Exception:
        pass

    # Tentativo con coppia USDT se quote == EUR e coppia diretta fallita (es. SEI, FDUSD)
    if quote == "EUR":
        usdt_symbol = f"{base}USDT"
        url_usdt = f"https://api.binance.com/api/v3/klines?symbol={usdt_symbol}&interval=1d&limit={limit}"
        url_eurusdt = "https://api.binance.com/api/v3/klines?symbol=EURUSDT&interval=1d&limit={limit}"
        try:
            r_asset = requests.get(url_usdt, headers=HEADERS, timeout=timeout)
            r_fx = requests.get(url_eurusdt, headers=HEADERS, timeout=timeout)
            if r_asset.status_code == 200:
                df_asset = _parse_binance_klines(r_asset.json())
                if df_asset is not None and not df_asset.empty:
                    if r_fx.status_code == 200:
                        df_fx = _parse_binance_klines(r_fx.json())
                        if df_fx is not None and not df_fx.empty:
                            # Converte i prezzi USD/USDT in EUR dividendo per EURUSDT
                            fx_series = df_fx["close"].reindex(df_asset.index, method="ffill")
                            fx_series = fx_series.fillna(1.08)  # fallback exchange rate
                            for col in ["open", "high", "low", "close"]:
                                df_asset[col] = df_asset[col] / fx_series
                    return df_asset
        except Exception:
            pass

    return None


def _parse_binance_klines(klines: List[List[Any]]) -> Optional[pd.DataFrame]:
    """Converte l'array klines di Binance in un DataFrame OHLCV indicizzato per Data."""
    try:
        records = []
        for k in klines:
            # k[0] = open_time (ms), k[1]=open, k[2]=high, k[3]=low, k[4]=close, k[5]=volume
            dt = pd.to_datetime(k[0], unit="ms").floor("D")
            records.append({
                "date": dt,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        if records:
            df = pd.DataFrame(records).drop_duplicates(subset=["date"]).set_index("date").sort_index()
            return df
    except Exception:
        pass
    return None


def fetch_kraken_ohlcv(base: str, quote: str = "EUR", timeout: float = 5.0) -> Optional[pd.DataFrame]:
    """Scarica le candele giornaliere da Kraken Public Market Data API."""
    pair_key = f"{base.upper()}-{quote.upper()}"
    kraken_pair = KRAKEN_PAIRS.get(pair_key, f"{base.upper()}{quote.upper()}")
    url = f"https://api.kraken.com/0/public/OHLC?pair={kraken_pair}&interval=1440"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            res_dict = data.get("result", {})
            for k, val in res_dict.items():
                if k != "last" and isinstance(val, list) and len(val) > 0:
                    records = []
                    for row in val:
                        # row[0] = time (s), 1=open, 2=high, 3=low, 4=close, 6=volume
                        dt = pd.to_datetime(row[0], unit="s").floor("D")
                        records.append({
                            "date": dt,
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": float(row[6]),
                        })
                    if records:
                        return pd.DataFrame(records).drop_duplicates(subset=["date"]).set_index("date").sort_index()
    except Exception:
        pass
    return None


def fetch_coingecko_ohlcv(base: str, quote: str = "eur", days: int = 730, timeout: float = 6.0) -> Optional[pd.DataFrame]:
    """Scarica i prezzi storici da CoinGecko (supporta oltre 10.000 token)."""
    coin_id = COINGECKO_IDS.get(base.upper(), base.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={quote.lower()}&days={days}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])
            if prices:
                df_p = pd.DataFrame(prices, columns=["ts", "close"])
                df_p["date"] = pd.to_datetime(df_p["ts"], unit="ms").dt.floor("D")
                df_p = df_p.drop_duplicates(subset=["date"]).set_index("date")

                if volumes:
                    df_v = pd.DataFrame(volumes, columns=["ts", "volume"])
                    df_v["date"] = pd.to_datetime(df_v["ts"], unit="ms").dt.floor("D")
                    df_v = df_v.drop_duplicates(subset=["date"]).set_index("date")
                    df_p["volume"] = df_v["volume"]
                else:
                    df_p["volume"] = 0.0

                df_p["open"] = df_p["close"]
                df_p["high"] = df_p["close"]
                df_p["low"] = df_p["close"]
                return df_p[["open", "high", "low", "close", "volume"]].sort_index()
    except Exception:
        pass
    return None


def fetch_crypto_history_unified(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Pipeline multi-exchange per dati storici crypto con architettura a cascata:
    1. Binance (L1 Spot Engine)
    2. Kraken (L2 Institutional Euro Books)
    3. CoinGecko (L3 Universal Altcoin Engine)
    """
    base, quote = normalize_crypto_pair(ticker)

    # 1. Tentativo con Binance
    df = fetch_binance_ohlcv(base, quote)

    # 2. Tentativo con Kraken
    if df is None or df.empty:
        df = fetch_kraken_ohlcv(base, quote)

    # 3. Tentativo con CoinGecko
    if df is None or df.empty:
        df = fetch_coingecko_ohlcv(base, quote)

    if df is not None and not df.empty:
        if start_date:
            df = df[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df.index <= pd.to_datetime(end_date)]
        return df

    return None
