# ============================================================
# core/yield_curve.py
# ARGUS — Risk Analytics & BI Platform
# Dynamic Risk-Free Rate Engine & Institutional Yield Curve Ingestion
# Supports: EUR (€STR/Bund), USD (SOFR/^IRX 3M Treasury), GBP (SONIA), CHF (SARON)
# ============================================================

import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from core.cache_shield import get_cached_ticker_history

# ── Tassi Istituzionali di Riferimento (Fallback Prudenziale) ─
INSTITUTIONAL_BENCHMARK_RATES: Dict[str, Dict[str, Any]] = {
    "EUR": {
        "default_rate": 0.0275,  # 2.75% BCE Deposit Facility / €STR
        "ticker_proxy": "XEON.DE",
        "benchmark_name": "BCE €STR / Euro Short-Term Rate",
        "description": "Tasso overnight privo di rischio dell'Area Euro (€STR / BCE Deposit Rate)."
    },
    "USD": {
        "default_rate": 0.0435,  # 4.35% US 3-Month Treasury Bill / SOFR
        "ticker_proxy": "^IRX",
        "benchmark_name": "US 3-Month Treasury Bill (^IRX)",
        "description": "Rendimento annualizzato dei Buoni del Tesoro USA a 13 settimane (3M T-Bill)."
    },
    "GBP": {
        "default_rate": 0.0475,  # 4.75% BoE SONIA / UK 3M Gilt
        "ticker_proxy": "CSH2.L",
        "benchmark_name": "Bank of England SONIA Benchmark",
        "description": "Sterling Overnight Index Average (SONIA) del Regno Unito."
    },
    "CHF": {
        "default_rate": 0.0100,  # 1.00% SNB SARON
        "ticker_proxy": None,
        "benchmark_name": "Swiss National Bank SARON",
        "description": "Swiss Average Rate Overnight (SARON) della Banca Nazionale Svizzera."
    },
}

_YIELD_CACHE: Dict[str, Dict[str, Any]] = {}


def get_default_risk_free_rate(currency: str = "EUR") -> float:
    """Restituisce il tasso di default istituzionale per la valuta specificata."""
    c_upper = str(currency or "EUR").strip().upper()
    info = INSTITUTIONAL_BENCHMARK_RATES.get(c_upper, INSTITUTIONAL_BENCHMARK_RATES["EUR"])
    return float(info["default_rate"])


def _extract_rate_from_proxy_history(ticker: str, benchmark_name: str, force_refresh: bool) -> tuple[Optional[float], Optional[str]]:
    """Estrae la stima del tasso live dal proxy di mercato (ticker Yahoo Finance)."""
    try:
        df = get_cached_ticker_history(ticker, ttl_seconds=43200, force_refresh=force_refresh)
        if df is None or df.empty or "Close" not in df.columns:
            return None, None

        last_val = float(df["Close"].dropna().iloc[-1])

        # ^IRX restituisce direttamente il rendimento percentuale (es. 4.35 per 4.35%)
        if ticker == "^IRX" and 0.0 <= last_val <= 25.0:
            rate = last_val / 100.0
            return rate, f"Live Market: US 3-Month Treasury Bill (^IRX: {last_val:.2f}%)"

        # XEON.DE / CSH2.L: stima del rendimento rolling annualizzato sui prezzi dell'ETF monetario
        if len(df) >= 30:
            closes = df["Close"].dropna()
            days = (closes.index[-1] - closes.index[0]).days if hasattr(closes.index, "days") else 30
            if days > 15:
                tot_ret = (closes.iloc[-1] / closes.iloc[0]) - 1.0
                ann_ret = (1.0 + tot_ret) ** (365.0 / max(1, days)) - 1.0
                if 0.005 <= ann_ret <= 0.10:
                    return float(ann_ret), f"Live Market: {benchmark_name} ({ann_ret * 100.0:.2f}%)"
    except Exception:
        pass
    return None, None


def fetch_live_risk_free_rate(
    currency: str = "EUR",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Recupera il tasso d'interesse privo di rischio (Risk-Free Rate) aggiornato per la valuta base.
    Utilizza lo scudo di caching a 2 livelli e ripiega in modo trasparente sui tassi ufficiali
    delle Banche Centrali (BCE, FED, BoE, SNB) in caso di mancata risposta del provider.

    Parameters:
    -----------
    currency : str
        Codice valuta ISO (es. 'EUR', 'USD', 'GBP', 'CHF').
    force_refresh : bool
        Se True, bypassa la cache in memoria.

    Returns:
    --------
    dict con 'currency', 'rate' (float decimale), 'rate_pct' (in %), 'source', 'is_live', 'as_of_date'.
    """
    c_upper = str(currency or "EUR").strip().upper()
    if c_upper not in INSTITUTIONAL_BENCHMARK_RATES:
        c_upper = "EUR"

    now = time.time()
    cache_key = f"rf_{c_upper}"

    # Controllo cache in memoria (validità 12 ore)
    if not force_refresh and cache_key in _YIELD_CACHE:
        cached_entry = _YIELD_CACHE[cache_key]
        if (now - cached_entry.get("_cached_at", 0)) < 43200:
            return cached_entry["data"].copy()

    meta = INSTITUTIONAL_BENCHMARK_RATES[c_upper]
    default_rate = meta["default_rate"]
    ticker = meta.get("ticker_proxy")
    today_str = datetime.now().strftime("%Y-%m-%d")

    live_rate, live_source = (None, None)
    if ticker:
        live_rate, live_source = _extract_rate_from_proxy_history(ticker, meta["benchmark_name"], force_refresh)

    is_live = live_rate is not None and not np.isnan(live_rate)
    final_rate = live_rate if is_live else default_rate
    source_name = live_source if is_live else f"{meta['benchmark_name']} (Benchmark Istituzionale)"

    result = {
        "currency": c_upper,
        "rate": round(float(final_rate), 4),
        "rate_pct": round(float(final_rate) * 100.0, 2),
        "source": source_name,
        "benchmark_name": meta["benchmark_name"],
        "description": meta["description"],
        "is_live": is_live,
        "as_of_date": today_str,
        "default_rate_pct": round(default_rate * 100.0, 2)
    }

    _YIELD_CACHE[cache_key] = {
        "_cached_at": now,
        "data": result
    }

    return result


def get_active_risk_free_rate(
    currency: str = "EUR",
    custom_override: Optional[float] = None
) -> Dict[str, Any]:
    """
    Restituisce la configurazione attiva del tasso risk-free, applicando l'eventuale override manuale.
    """
    if custom_override is not None and not np.isnan(custom_override) and custom_override >= 0.0:
        c_upper = str(currency or "EUR").strip().upper()
        return {
            "currency": c_upper,
            "rate": round(float(custom_override), 4),
            "rate_pct": round(float(custom_override) * 100.0, 2),
            "source": f"Override Manuale Utente ({custom_override * 100.0:.2f}%)",
            "benchmark_name": "Personalizzato",
            "description": "Tasso impostato manualmente dall'utente nella configurazione.",
            "is_live": False,
            "is_manual_override": True,
            "as_of_date": datetime.now().strftime("%Y-%m-%d"),
            "default_rate_pct": round(get_default_risk_free_rate(c_upper) * 100.0, 2)
        }

    live_info = fetch_live_risk_free_rate(currency)
    live_info["is_manual_override"] = False
    return live_info


def get_daily_risk_free_rate(
    annual_rate: float,
    trading_days: int = 252
) -> float:
    """Converte un tasso risk-free annuo nel corrispondente tasso giornaliero."""
    if annual_rate <= 0:
        return 0.0
    return float(annual_rate / max(1, trading_days))
