import numpy as np
import pandas as pd
import pytest

from core.hrp_optimizer import compute_hrp_portfolio


def test_compute_hrp_portfolio_basic():
    # Creazione serie rendimenti sintetici di test per 4 asset
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=100, freq="B")
    ret_a = np.random.normal(0.0008, 0.012, 100)
    ret_b = np.random.normal(0.0005, 0.015, 100)
    ret_c = 0.8 * ret_a + np.random.normal(0.0, 0.005, 100)
    ret_d = np.random.normal(0.0002, 0.008, 100)

    df_ret = pd.DataFrame({
        "AAPL": ret_a,
        "MSFT": ret_b,
        "GOOGL": ret_c,
        "BOND": ret_d
    }, index=dates)

    res = compute_hrp_portfolio(df_ret)
    assert res is not None
    assert "weights" in res
    assert "expected_return_pct" in res
    assert "volatility_annual_pct" in res
    assert "sharpe_ratio" in res

    # I pesi devono sommare a 1.0
    weights = res["weights"]
    assert len(weights) == 4
    assert np.isclose(sum(weights.values()), 1.0, atol=1e-4)

    # L'asset con minor varianza (BOND) deve avere un'allocazione significativa
    assert weights["BOND"] > 0.15


def test_compute_hrp_portfolio_empty():
    res = compute_hrp_portfolio(pd.DataFrame())
    assert res == {}
