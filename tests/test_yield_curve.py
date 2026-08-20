# ============================================================
# tests/test_yield_curve.py
# Unit & Integration Tests for Yield Curve & Dynamic Risk-Free Rate Engine
# ============================================================

import numpy as np
import pandas as pd
import pytest

from core.advanced_quant import compute_kelly_criterion_sizing
from core.financial_analysis import compute_wacc_estimation
from core.options_hedging import black_scholes_pricing, compute_portfolio_delta_hedge
from core.risk_engine import _calc_return_metrics, compute_sandbox_risk_bundle
from core.yield_curve import (
    INSTITUTIONAL_BENCHMARK_RATES,
    fetch_live_risk_free_rate,
    get_active_risk_free_rate,
    get_daily_risk_free_rate,
    get_default_risk_free_rate,
)


def test_default_risk_free_rates_coverage():
    """Verifica che i tassi benchmark di default per tutte le valute principali siano configurati correttamente."""
    for curr in ["EUR", "USD", "GBP", "CHF"]:
        r = get_default_risk_free_rate(curr)
        assert isinstance(r, float)
        assert 0.005 <= r <= 0.10  # Tassi compresi tra 0.5% e 10%

    # Fallback su valuta sconosciuta
    assert get_default_risk_free_rate("XYZ") == INSTITUTIONAL_BENCHMARK_RATES["EUR"]["default_rate"]


def test_fetch_live_risk_free_rate_structure():
    """Verifica che la chiamata a fetch_live_risk_free_rate restituisca un contratto valido."""
    res_eur = fetch_live_risk_free_rate("EUR")
    assert res_eur["currency"] == "EUR"
    assert "rate" in res_eur
    assert "rate_pct" in res_eur
    assert "source" in res_eur
    assert "benchmark_name" in res_eur
    assert isinstance(res_eur["rate"], float)
    assert res_eur["rate"] > 0

    res_usd = fetch_live_risk_free_rate("USD")
    assert res_usd["currency"] == "USD"
    assert res_usd["rate"] > 0


def test_active_risk_free_rate_override():
    """Verifica l'applicazione dell'override manuale utente."""
    # Senza override: usa live/default
    auto_info = get_active_risk_free_rate("EUR", custom_override=None)
    assert auto_info["is_manual_override"] is False

    # Con override al 4.5%
    manual_info = get_active_risk_free_rate("EUR", custom_override=0.045)
    assert manual_info["is_manual_override"] is True
    assert manual_info["rate"] == 0.045
    assert manual_info["rate_pct"] == 4.5
    assert "Override Manuale" in manual_info["source"]


def test_daily_risk_free_conversion():
    """Verifica la conversione da annuo a giornaliero."""
    annual_rate = 0.0252
    daily_rate = get_daily_risk_free_rate(annual_rate, trading_days=252)
    assert np.isclose(daily_rate, 0.0001)

    assert get_daily_risk_free_rate(0.0) == 0.0
    assert get_daily_risk_free_rate(-0.05) == 0.0


def test_sharpe_ratio_sensitivity_to_risk_free_rate():
    """
    Verifica che un aumento del tasso risk-free riduca monotonicamente
    lo Sharpe Ratio a parità di serie di rendimenti.
    """
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    daily_rets = pd.Series(0.0008 + np.random.normal(0, 0.01, 100), index=dates)
    bm_rets = pd.Series(0.0005 + np.random.normal(0, 0.008, 100), index=dates)
    df_pos = pd.DataFrame([{"current_value": 100000.0, "cost_basis": 90000.0, "unrealized_pnl": 10000.0, "realized_pnl": 0.0, "total_return": 10000.0, "dividends_total": 0.0}])

    res_low_rf = _calc_return_metrics(daily_rets, bm_rets, pd.DataFrame(), df_pos, risk_free_rate=0.01)
    res_high_rf = _calc_return_metrics(daily_rets, bm_rets, pd.DataFrame(), df_pos, risk_free_rate=0.05)

    assert res_low_rf["sharpe_ratio"] > res_high_rf["sharpe_ratio"]
    assert res_low_rf["risk_free_rate_pct"] == 1.0
    assert res_high_rf["risk_free_rate_pct"] == 5.0


def test_sandbox_bundle_with_dynamic_rf():
    """Verifica che compute_sandbox_risk_bundle integri correttamente il tasso risk-free specificato."""
    bundle = compute_sandbox_risk_bundle(
        tickers=["AAPL", "MSFT", "BND"],
        risk_free_rate=0.035,
        base_currency="USD"
    )
    assert "risk_free" in bundle
    assert bundle["risk_free"]["rate"] == 0.035
    assert bundle["metrics"]["returns"]["risk_free_rate_pct"] == 3.5


def test_wacc_and_options_dynamic_rf():
    """Verifica che WACC e Black-Scholes utilizzino il tasso risk-free dinamico."""
    # WACC
    wacc_res_3 = compute_wacc_estimation("AAPL", rf_rate=0.03)
    wacc_res_5 = compute_wacc_estimation("AAPL", rf_rate=0.05)
    assert wacc_res_5["wacc_pct"] > wacc_res_3["wacc_pct"]
    assert wacc_res_3["risk_free_rate_pct"] == 3.0
    assert wacc_res_5["risk_free_rate_pct"] == 5.0

    # Black-Scholes Call pricing (all'aumentare di r, il prezzo della Call sale e della Put scende)
    call_low_r = black_scholes_pricing(S=100, K=100, T=1.0, r=0.01, sigma=0.20, option_type="call")
    call_high_r = black_scholes_pricing(S=100, K=100, T=1.0, r=0.06, sigma=0.20, option_type="call")
    assert call_high_r["price"] > call_low_r["price"]

    # Delta Hedge
    hedge_res = compute_portfolio_delta_hedge(portfolio_value=100000, portfolio_beta=1.0, risk_free_rate=0.04)
    assert hedge_res["risk_free_rate_pct"] == 4.0


def test_kelly_criterion_with_dynamic_rf():
    """Verifica il calcolo di Kelly con tasso risk-free personalizzato."""
    np.random.seed(42)
    df_ret = pd.DataFrame({
        "ASSET_A": np.random.normal(0.001, 0.01, 50),
        "ASSET_B": np.random.normal(0.0005, 0.015, 50)
    })
    df_kelly = compute_kelly_criterion_sizing(df_ret, risk_free_rate=0.02)
    assert not df_kelly.empty
    assert "Half-Kelly (Target)" in df_kelly.columns
    assert "Full Kelly" in df_kelly.columns
