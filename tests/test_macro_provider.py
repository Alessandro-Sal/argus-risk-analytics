# ============================================================
# tests/test_macro_provider.py
# ARGUS — Fast, Deterministic Unit tests for FRED and ECB Macro Ingestion
# Fully isolated from live internet dependencies with realistic fixture mocks
# ============================================================

import io
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
import numpy as np

from core.macro_provider import (
    fetch_fred_series,
    fetch_us_treasury_term_structure,
    fetch_ecb_yield_curve,
    get_live_central_bank_rates,
    FRED_TREASURY_SERIES,
    ECB_YIELD_TENORS
)
from core.yield_curve import get_institutional_yield_curve, get_active_risk_free_rate


@pytest.fixture(autouse=True)
def mock_macro_network_requests():
    """
    Mock automatico per requests.get in test_macro_provider.
    Previene chiamate di rete esterne, eliminando oltre 140 secondi di latenza
    e prevenendo flaky tests su rate-limit / downtime di FRED e BCE.
    """
    def mocked_get(url, *args, **kwargs):
        resp = MagicMock()
        url_str = str(url)

        # 1. Caso Ticker Inesistente
        if "NON_EXISTENT_SERIES" in url_str:
            resp.status_code = 404
            resp.text = ""
            return resp

        # 2. Endpoint FRED Public CSV
        if "fred.stlouisfed.org" in url_str:
            dates = pd.date_range("2024-01-01", periods=120, freq="B").strftime("%Y-%m-%d")
            # Simula tassi realistici tra 3.5% e 4.5%
            values = np.linspace(3.8, 4.3, len(dates))
            csv_lines = ["DATE,VALUE"] + [f"{d},{v:.4f}" for d, v in zip(dates, values)]
            resp.status_code = 200
            resp.text = "\n".join(csv_lines)
            return resp

        # 3. Endpoint ECB SDMX
        if "data-api.ecb.europa.eu" in url_str:
            resp.status_code = 200
            resp.text = "KEY,FREQ,REF_AREA,CURRENCY,TENOR,OBS_VALUE\nYC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y,D,U2,EUR,10Y,2.75\n"
            return resp

        resp.status_code = 200
        resp.text = ""
        return resp

    with patch("requests.get", side_effect=mocked_get) as _mock:
        yield _mock


def test_fetch_fred_series_mocked():
    """Verifica che la serie decennale USA (DGS10) venga decodificata con indice DatetimeIndex e valori validi."""
    s = fetch_fred_series("DGS10", timeout=1.0)
    assert s is not None and not s.empty
    assert isinstance(s, pd.Series)
    assert len(s) == 120
    assert 3.0 < s.iloc[-1] < 5.0
    assert isinstance(s.index, pd.DatetimeIndex)


def test_fetch_fred_series_invalid_ticker():
    """Verifica la gestione degli errori per serie inesistenti."""
    s = fetch_fred_series("NON_EXISTENT_SERIES_XYZ_12345", timeout=1.0)
    assert s is None or s.empty


def test_fetch_us_treasury_term_structure():
    """Verifica il recupero dell'intera struttura per scadenza USA."""
    curve = fetch_us_treasury_term_structure(timeout=1.0)
    assert isinstance(curve, dict)
    assert len(curve) == len(FRED_TREASURY_SERIES)
    for tenor in ["1Y", "5Y", "10Y"]:
        assert tenor in curve
        assert 0.0 < curve[tenor] < 20.0


def test_fetch_ecb_yield_curve():
    """Verifica il recupero della curva dei rendimenti BCE."""
    curve = fetch_ecb_yield_curve(timeout=1.0)
    assert isinstance(curve, dict)
    assert len(curve) > 0
    for tenor in curve:
        assert 0.0 < curve[tenor] < 10.0


def test_get_live_central_bank_rates():
    """Verifica la completezza dei dati delle Banche Centrali (USD, EUR, GBP, CHF)."""
    cb = get_live_central_bank_rates(timeout=1.0)
    assert isinstance(cb, dict)
    for ccy in ["USD", "EUR", "GBP", "CHF"]:
        assert ccy in cb
        assert "policy_rate_pct" in cb[ccy]
        assert cb[ccy]["policy_rate_pct"] > 0.0


def test_yield_curve_integration_with_macro_provider():
    """Verifica l'integrazione con il modulo delle curve istituzionali (calibrazione Nelson-Siegel)."""
    res_usd = get_institutional_yield_curve("USD")
    assert "df_curve" in res_usd
    assert len(res_usd["df_curve"]) == 11
    assert res_usd["nelson_siegel_params"]["r_squared"] > 0.50

    res_eur = get_institutional_yield_curve("EUR")
    assert "df_curve" in res_eur
    assert len(res_eur["df_curve"]) == 11
    assert res_eur["nelson_siegel_params"]["r_squared"] > 0.50
