"""
tests/test_bloomberg_terminal_features.py
Unit tests for Institutional Bloomberg Terminal Parity enhancements (Phase 1).
"""

import pytest
import numpy as np
import pandas as pd

from core.yield_curve import (
    _nelson_siegel_svensson_basis,
    evaluate_nelson_siegel_svensson_curve,
    fit_nelson_siegel_svensson_curve,
    compute_key_rate_durations,
    get_institutional_yield_curve,
)
from core.attribution import (
    compute_brinson_attribution,
    compute_carino_multi_period_attribution,
    compute_karnosky_singer_currency_attribution,
)
from core.risk_engine import (
    compute_marginal_and_component_var,
    compute_liquidity_adjusted_var,
)
from core.ui_utils import parse_terminal_command


# ── 1. TEST NELSON-SIEGEL-SVENSSON (NSS) & KEY RATE DURATIONS ───────

def test_nelson_siegel_svensson_fitting_and_evaluation():
    maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
    # Simulated yield curve with double humps
    true_params = {
        "beta0": 0.040,
        "beta1": -0.015,
        "beta2": 0.010,
        "beta3": -0.005,
        "tau1": 1.5,
        "tau2": 6.0
    }
    simulated_yields = evaluate_nelson_siegel_svensson_curve(maturities, true_params)
    assert len(simulated_yields) == len(maturities)
    assert np.all(simulated_yields > 0)

    # Test Basis functions
    f1, f2, f3 = _nelson_siegel_svensson_basis(maturities, 1.5, 6.0)
    assert len(f1) == len(maturities)
    assert len(f2) == len(maturities)
    assert len(f3) == len(maturities)

    # Test Fitting
    fit_res = fit_nelson_siegel_svensson_curve(maturities, simulated_yields)
    assert "beta0" in fit_res
    assert "beta3" in fit_res
    assert "r_squared" in fit_res
    assert fit_res["r_squared"] > 0.95
    assert fit_res["rmse"] < 0.005


def test_key_rate_durations():
    # 5-Year bond with annual 4% coupon and face value 100
    t_cf = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    c_cf = np.array([4.0, 4.0, 4.0, 4.0, 104.0])
    ns_params = {"beta0": 0.035, "beta1": -0.01, "beta2": 0.005, "tau": 1.5}

    krd_res = compute_key_rate_durations(t_cf, c_cf, ns_params)
    assert "key_rate_durations" in krd_res
    assert "effective_duration" in krd_res
    assert krd_res["effective_duration"] > 3.5  # Typical ~4.3Y for a 5Y 4% bond
    assert sum(krd_res["key_rate_durations"].values()) == pytest.approx(krd_res["effective_duration"], abs=1e-3)


def test_institutional_yield_curve_svensson_integration():
    curve_eur = get_institutional_yield_curve("EUR")
    assert "svensson_params" in curve_eur
    assert "svensson_rate_pct" in curve_eur["df_curve"].columns
    assert len(curve_eur["df_curve"]) == 11


# ── 2. TEST CARINO MULTI-PERIOD ATTRIBUTION & KARNOSKY-SINGER ────────

def test_carino_multi_period_attribution_zero_residual():
    # Simulate 3 sub-periods
    period_1 = {
        "portfolio_return_pct": 2.5,
        "benchmark_return_pct": 1.8,
        "attribution_df": pd.DataFrame([
            {"sector": "Technology", "weight_portfolio_pct": 40.0, "weight_benchmark_pct": 30.0, "allocation_effect_pct": 0.30, "selection_effect_pct": 0.35, "interaction_effect_pct": 0.05},
            {"sector": "Financials", "weight_portfolio_pct": 20.0, "weight_benchmark_pct": 15.0, "allocation_effect_pct": -0.05, "selection_effect_pct": 0.04, "interaction_effect_pct": 0.01}
        ])
    }
    period_2 = {
        "portfolio_return_pct": -1.2,
        "benchmark_return_pct": -0.8,
        "attribution_df": pd.DataFrame([
            {"sector": "Technology", "weight_portfolio_pct": 42.0, "weight_benchmark_pct": 30.0, "allocation_effect_pct": -0.15, "selection_effect_pct": -0.20, "interaction_effect_pct": -0.05},
            {"sector": "Financials", "weight_portfolio_pct": 18.0, "weight_benchmark_pct": 15.0, "allocation_effect_pct": 0.02, "selection_effect_pct": -0.02, "interaction_effect_pct": 0.0}
        ])
    }
    period_3 = {
        "portfolio_return_pct": 3.8,
        "benchmark_return_pct": 2.4,
        "attribution_df": pd.DataFrame([
            {"sector": "Technology", "weight_portfolio_pct": 45.0, "weight_benchmark_pct": 30.0, "allocation_effect_pct": 0.50, "selection_effect_pct": 0.70, "interaction_effect_pct": 0.20},
            {"sector": "Financials", "weight_portfolio_pct": 15.0, "weight_benchmark_pct": 15.0, "allocation_effect_pct": 0.0, "selection_effect_pct": 0.0, "interaction_effect_pct": 0.0}
        ])
    }

    res = compute_carino_multi_period_attribution([period_1, period_2, period_3])
    assert "linked_attribution_df" in res
    assert "summary" in res
    assert res["summary"]["residual_error_bps"] < 1.0  # Residual must be near zero
    assert not res["linked_attribution_df"].empty


def test_karnosky_singer_currency_attribution():
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 60000.0, "currency": "USD"},
        {"ticker": "ASML", "current_value": 40000.0, "currency": "EUR"},
    ])
    fx_returns = {"USD": 0.02, "EUR": 0.0}
    local_returns = {"USD": 0.08, "EUR": 0.05}

    ks_res = compute_karnosky_singer_currency_attribution(
        df_positions=df_pos,
        fx_returns=fx_returns,
        local_asset_returns=local_returns,
        benchmark_currency_weights={"USD": 0.50, "EUR": 0.50}
    )
    assert "summary" in ks_res
    assert "currency_df" in ks_res
    assert ks_res["summary"]["total_currency_effect_pct"] != 0.0


# ── 3. TEST MARGINAL & COMPONENT VAR (EULER DECOMPOSITION) ───────────

def test_marginal_and_component_var_euler():
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=200, freq="B")
    ret_a = np.random.normal(0.0005, 0.015, size=200)
    ret_b = 0.6 * ret_a + np.random.normal(0.0002, 0.010, size=200)
    df_returns = pd.DataFrame({"AAPL": ret_a, "MSFT": ret_b}, index=dates)

    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 60000.0, "qty_net": 300},
        {"ticker": "MSFT", "current_value": 40000.0, "qty_net": 100}
    ])

    var_res = compute_marginal_and_component_var(
        df_returns=df_returns,
        df_positions=df_positions,
        confidence_level=0.95,
        total_portfolio_value=100000.0
    )
    assert var_res["euler_check_passed"] is True
    assert var_res["portfolio_var_amount"] > 0
    decomp_df = var_res["decomposition_df"]
    assert len(decomp_df) == 2
    assert "marginal_var_pct" in decomp_df.columns
    assert "component_var_amount" in decomp_df.columns
    assert decomp_df["risk_contribution_pct"].sum() == pytest.approx(100.0, abs=1e-1)


def test_liquidity_adjusted_var():
    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 80000.0},
        {"ticker": "BTC-USD", "current_value": 20000.0}
    ])
    lvar_res = compute_liquidity_adjusted_var(
        df_positions=df_positions,
        portfolio_var_pct=2.5,
        total_portfolio_value=100000.0,
        liquidation_horizon_days=5
    )
    assert lvar_res["lvar_amount"] > lvar_res["unadjusted_var_amount"]
    assert lvar_res["liquidity_cost_amount"] > 0
    assert lvar_res["lvar_premium_pct"] > 0


# ── 4. TEST BLOOMBERG COMMAND LINE PARSER ────────────────────────────

def test_parse_terminal_command_mnemonics():
    # Single mnemonic
    cmd_ycrv = parse_terminal_command("YCRV")
    assert cmd_ycrv is not None
    assert cmd_ycrv["mnemonic"] == "YCRV"
    assert cmd_ycrv["context_type"] == "rates"

    # Ticker + Mnemonic
    cmd_aapl_des = parse_terminal_command("AAPL DES")
    assert cmd_aapl_des is not None
    assert cmd_aapl_des["ticker"] == "AAPL"
    assert cmd_aapl_des["mnemonic"] == "DES"

    # Mnemonic + Ticker
    cmd_fa_nvda = parse_terminal_command("FA NVDA")
    assert cmd_fa_nvda is not None
    assert cmd_fa_nvda["ticker"] == "NVDA"
    assert cmd_fa_nvda["mnemonic"] == "FA"

    # Portfolio Command
    cmd_port_risk = parse_terminal_command("PORT RISK")
    assert cmd_port_risk is not None
    assert cmd_port_risk["mnemonic"] == "RISK"

    # Screener
    cmd_eqs = parse_terminal_command("EQS")
    assert cmd_eqs is not None
    assert cmd_eqs["mnemonic"] == "EQS"

    # Bare Ticker fallback to DES
    cmd_msft = parse_terminal_command("MSFT")
    assert cmd_msft is not None
    assert cmd_msft["ticker"] == "MSFT"
    assert cmd_msft["mnemonic"] == "DES"

    # Empty
    assert parse_terminal_command("") is None
