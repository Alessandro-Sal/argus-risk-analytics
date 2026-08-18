"""
Unit & Integration Tests for core/advanced_quant.py
"""

import pytest
import pandas as pd
import numpy as np
from core.advanced_quant import (
    compute_tail_copula_matrix,
    compute_kelly_criterion_sizing,
    compute_equal_risk_contribution_portfolio
)


@pytest.fixture
def sample_returns():
    dates = pd.date_range("2023-01-01", periods=150, freq="B")
    np.random.seed(42)
    # 3 asset correlati con shock di coda
    cov = np.array([
        [0.0004, 0.00025, 0.0001],
        [0.00025, 0.00035, 0.00015],
        [0.0001, 0.00015, 0.0002]
    ])
    mean = np.array([0.0008, 0.0006, 0.0003])
    raw = np.random.multivariate_normal(mean, cov, size=150)
    
    # Inietta un paio di shock congiunti
    raw[10] = [-0.04, -0.035, -0.025]
    raw[50] = [-0.05, -0.045, -0.03]
    
    return pd.DataFrame(raw, index=dates, columns=["AAPL", "MSFT", "BND"])


def test_compute_tail_copula_matrix(sample_returns):
    res = compute_tail_copula_matrix(sample_returns, quantile_threshold=0.05)
    assert "lambda_lower_df" in res
    assert "lambda_upper_df" in res
    assert "asymmetry_df" in res
    
    df_l = res["lambda_lower_df"]
    assert df_l.shape == (3, 3)
    assert np.allclose(np.diag(df_l), 1.0)
    assert (df_l.values >= 0.0).all() and (df_l.values <= 1.0).all()
    assert res["mean_tail_dependence"] >= 0.0


def test_compute_tail_copula_empty():
    res = compute_tail_copula_matrix(pd.DataFrame())
    assert res["lambda_lower_df"].empty
    assert res["contagion_pairs"] == []


def test_compute_kelly_criterion_sizing(sample_returns):
    cur_weights = {"AAPL": 0.50, "MSFT": 0.30, "BND": 0.20}
    df_kelly = compute_kelly_criterion_sizing(sample_returns, current_weights=cur_weights, risk_free_rate=0.02)
    
    assert not df_kelly.empty
    assert len(df_kelly) == 3
    assert "Ticker" in df_kelly.columns
    assert "Half-Kelly (Target)" in df_kelly.columns
    assert "Full Kelly" in df_kelly.columns
    assert "Stato Allocazione" in df_kelly.columns


def test_compute_equal_risk_contribution_portfolio(sample_returns):
    res = compute_equal_risk_contribution_portfolio(sample_returns)
    assert res["success"] is True
    weights = res["weights"]
    assert len(weights) == 3
    assert pytest.approx(sum(weights.values()), abs=1e-3) == 1.0
    for t, w in weights.items():
        assert w > 0.0
    
    # Verifica che le risk contributions % siano circa pari (100 / 3 ≈ 33.3%)
    rc_pct = res["risk_contributions_pct"]
    for t, r in rc_pct.items():
        assert pytest.approx(r, abs=12.0) == 33.33
    
    assert res["volatility"] > 0.0
    assert res["sharpe_ratio"] != 0.0


def test_compute_equal_risk_contribution_empty():
    res = compute_equal_risk_contribution_portfolio(pd.DataFrame())
    assert res["success"] is False
    assert res["weights"] == {}
