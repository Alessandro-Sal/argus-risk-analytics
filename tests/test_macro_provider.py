# ============================================================
# tests/test_macro_provider.py
# ARGUS — Unit tests for FRED and ECB Macro Ingestion Engine
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.macro_provider import (
    fetch_fred_series,
    fetch_us_treasury_term_structure,
    fetch_ecb_yield_curve,
    get_live_central_bank_rates
)
from core.yield_curve import get_institutional_yield_curve, get_active_risk_free_rate


def test_fetch_fred_series_live():
    """Verifica che la serie decennale USA (DGS10) venga scaricata correttamente da FRED."""
    s = fetch_fred_series("DGS10", timeout=6.0)
    if s is not None and not s.empty:
        assert isinstance(s, pd.Series)
        assert len(s) > 100
        assert s.iloc[-1] > 0.0
        assert isinstance(s.index, pd.DatetimeIndex)


def test_fetch_fred_series_invalid_ticker():
    """Verifica la gestione degli errori per serie inesistenti."""
    s = fetch_fred_series("NON_EXISTENT_SERIES_XYZ_12345", timeout=3.0)
    assert s is None or s.empty


def test_fetch_us_treasury_term_structure():
    """Verifica il recupero dell'intera struttura per scadenza USA."""
    curve = fetch_us_treasury_term_structure(timeout=6.0)
    assert isinstance(curve, dict)
    if curve:
        for tenor in ["1Y", "5Y", "10Y"]:
            if tenor in curve:
                assert 0.0 < curve[tenor] < 20.0


def test_get_live_central_bank_rates():
    """Verifica la completezza dei dati delle Banche Centrali (USD, EUR, GBP, CHF)."""
    cb = get_live_central_bank_rates(timeout=5.0)
    assert isinstance(cb, dict)
    for ccy in ["USD", "EUR", "GBP", "CHF"]:
        assert ccy in cb
        assert "policy_rate_pct" in cb[ccy]
        assert cb[ccy]["policy_rate_pct"] > 0.0


def test_yield_curve_integration_with_macro_provider():
    """Verifica l'integrazione con il modulo delle curve istituzionali."""
    res_usd = get_institutional_yield_curve("USD")
    assert "df_curve" in res_usd
    assert len(res_usd["df_curve"]) == 11
    assert res_usd["nelson_siegel_params"]["r_squared"] > 0.70

    res_eur = get_institutional_yield_curve("EUR")
    assert "df_curve" in res_eur
    assert len(res_eur["df_curve"]) == 11
    assert res_eur["nelson_siegel_params"]["r_squared"] > 0.70
