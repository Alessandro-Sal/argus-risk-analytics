import numpy as np
import pandas as pd
import pytest

from core.options_hedging import (
    black_scholes_pricing,
    compute_covered_call_yield_enhancement,
    compute_portfolio_delta_hedge,
)
from core.regime_switching import compute_market_regime_states


def test_market_regime_states():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    ret = pd.Series(np.random.normal(0.001, 0.008, 100), index=dates)

    res = compute_market_regime_states(ret)
    assert res is not None
    assert "current_regime" in res
    assert "regime_probabilities" in res
    assert res["current_state_idx"] in [1, 2, 3]


def test_black_scholes_pricing_call_put_parity():
    S = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.20

    call = black_scholes_pricing(S=S, K=K, T=T, r=r, sigma=sigma, option_type="call")
    put = black_scholes_pricing(S=S, K=K, T=T, r=r, sigma=sigma, option_type="put")

    # Put-Call Parity: C - P = S - K * exp(-r*T)
    lhs = call["price"] - put["price"]
    rhs = S - K * np.exp(-r * T)
    assert np.isclose(lhs, rhs, atol=1e-3)

    # Greci: Call Delta in (0, 1), Put Delta in (-1, 0)
    assert 0.0 < call["delta"] < 1.0
    assert -1.0 < put["delta"] < 0.0
    assert call["gamma"] > 0
    assert call["vega"] > 0


def test_portfolio_delta_hedge_and_covered_call():
    hedge = compute_portfolio_delta_hedge(
        portfolio_value=100000.0,
        portfolio_beta=1.20,
        benchmark_spot=500.0
    )
    assert hedge["contracts_needed"] > 0
    assert hedge["total_hedge_cost"] > 0

    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "last_price": 200.0, "qty_net": 100},
        {"ticker": "MSFT", "last_price": 400.0, "qty_net": 50}
    ])
    cov_call = compute_covered_call_yield_enhancement(df_pos)
    assert not cov_call.empty
    assert len(cov_call) == 2
    assert "incasso_premio_totale" in cov_call.columns
