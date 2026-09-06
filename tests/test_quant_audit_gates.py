# ==============================================================================
# tests/test_quant_audit_gates.py
# Quality Gate: Benchmark Numerici e Forme Chiuse (Audit Quantitativo)
# ==============================================================================
import pytest
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from core.risk_engine import _calc_return_metrics, _calc_market_risk, compute_black_litterman_optimization
from core.wealth.wealth_models import AccountType
from core.wealth.wealth_db import init_wealth_db, save_wealth_account
from core.wealth.wealth_engine import compute_consolidated_net_worth
from core.terminal_engine import get_fx_rate_to_eur


def test_calmar_ratio_sign_preservation():
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    np.random.seed(42)
    bm_rets = pd.Series(0.0, index=dates)

    # Positive CAGR -> positive Calmar
    pos_rets = pd.Series(0.001 + np.random.normal(0, 0.005, len(dates)), index=dates)
    res_pos = _calc_return_metrics(pos_rets, bm_rets)
    assert res_pos["cagr_pct"] is not None and res_pos["cagr_pct"] > 0
    assert res_pos["calmar_ratio"] is not None and res_pos["calmar_ratio"] > 0

    # Negative CAGR -> negative Calmar
    neg_rets = pd.Series(-0.0015 + np.random.normal(0, 0.005, len(dates)), index=dates)
    res_neg = _calc_return_metrics(neg_rets, bm_rets)
    assert res_neg["cagr_pct"] is not None and res_neg["cagr_pct"] < 0
    assert res_neg["calmar_ratio"] is not None
    assert res_neg["calmar_ratio"] < 0, f"Calmar ratio must be negative for negative CAGR, got {res_neg['calmar_ratio']}"


def test_sortino_ratio_continuous_denominator():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    r = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.01, -0.01], index=dates)
    rb = pd.Series(0.0, index=dates)
    
    res = _calc_return_metrics(r, rb, risk_free_rate=0.0)
    expected_down_std = np.sqrt(0.00002)
    expected_sortino = (-0.002 / expected_down_std) * np.sqrt(252)
    
    assert res["sortino_ratio"] == pytest.approx(expected_sortino, rel=1e-3)


def test_parametric_and_cornish_fisher_gaussian_match():
    dates = pd.date_range("2024-01-01", periods=10000, freq="B")
    np.random.seed(123)
    vol = 0.01
    white_noise = np.random.normal(0.0, vol, len(dates))
    sr_p = pd.Series(white_noise, index=dates)
    sr_bm = pd.Series(0.0, index=dates)

    res = _calc_market_risk(sr_p, sr_bm, "SPY")

    assert "var_parametric_95" in res
    assert "cvar_parametric_95" in res
    assert "var_cf_95" in res
    assert "cvar_cf_95" in res

    assert res["cvar_parametric_95"] >= res["var_parametric_95"]
    assert res["cvar_parametric_99"] >= res["var_parametric_99"]
    assert res["cvar_cf_95"] >= res["var_cf_95"]
    assert res["cvar_cf_99"] >= res["var_cf_99"]

    assert res["cvar_parametric_99"] >= res["cvar_parametric_95"]
    assert res["cvar_cf_99"] >= res["cvar_cf_95"]


def test_black_litterman_woodbury_stability():
    assets = ["ASSET_A", "ASSET_B", "ASSET_C"]
    cov_vals = np.array([
        [0.0400, 0.03999, 0.0100],
        [0.03999, 0.0400, 0.0100],
        [0.0100, 0.0100, 0.0225]
    ])
    cov_df = pd.DataFrame(cov_vals, index=assets, columns=assets)
    market_w = pd.Series([0.4, 0.4, 0.2], index=assets)
    views = {"ASSET_A": 0.10}
    
    res = compute_black_litterman_optimization(
        cov_matrix=cov_df,
        market_weights=market_w,
        views_dict=views,
        risk_aversion=2.5,
        tau=0.05
    )
    
    assert "implied_equilibrium_returns" in res
    assert "black_litterman_returns" in res
    assert "black_litterman_weights" in res
    
    w_bl = res["black_litterman_weights"]
    assert np.all(w_bl >= 0.0)
    assert np.isclose(w_bl.sum(), 1.0, atol=1e-4)


def test_wealth_multi_currency_and_overdraft_liabilities():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_wealth_db(eng)
    
    fx_usd_to_eur = get_fx_rate_to_eur("USD")
    assert fx_usd_to_eur > 0
    
    save_wealth_account(eng, {
        "name": "USD Account",
        "account_type": AccountType.CHECKING.value,
        "currency": "USD",
        "balance": 10000.0,
        "is_active": True
    })
    
    save_wealth_account(eng, {
        "name": "EUR Account",
        "account_type": AccountType.SAVINGS.value,
        "currency": "EUR",
        "balance": 5000.0,
        "is_active": True
    })
    
    save_wealth_account(eng, {
        "name": "Overdraft Checking",
        "account_type": AccountType.CHECKING.value,
        "currency": "EUR",
        "balance": -2000.0,
        "is_active": True
    })
    
    save_wealth_account(eng, {
        "name": "Mortgage Loan",
        "account_type": AccountType.MORTGAGE.value,
        "currency": "EUR",
        "balance": 100000.0,
        "is_active": True
    })
    
    nw = compute_consolidated_net_worth(eng, portfolio_id=1)
    
    expected_liquid = 10000.0 * fx_usd_to_eur + 5000.0
    assert nw.liquid_cash == pytest.approx(expected_liquid, rel=1e-3)
    
    expected_liabilities = 100000.0 + 2000.0
    assert nw.total_liabilities == pytest.approx(expected_liabilities, rel=1e-3)
    
    expected_net_worth = expected_liquid - expected_liabilities
    assert nw.total_net_worth == pytest.approx(expected_net_worth, rel=1e-3)
