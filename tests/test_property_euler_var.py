# ============================================================
# tests/test_property_euler_var.py
# ARGUS — Property-Based Testing: Euler Risk Decomposition
# Validates mathematical invariant: sum(PCTR_i) == 100% and sum(Component_VaR) == Portfolio_VaR
# ============================================================

import pytest
import numpy as np
import pandas as pd
from hypothesis import given, settings, strategies as st
from core.risk_engine import compute_marginal_and_component_var


@st.composite
def portfolio_and_returns_strategy(draw):
    """Genera stocasticamente un universo di N asset (2-6) con T giorni di rendimenti (60-180) e pesi casuali."""
    n_assets = draw(st.integers(min_value=2, max_value=6))
    n_days = draw(st.integers(min_value=60, max_value=180))
    tickers = [f"ASSET_{i}" for i in range(n_assets)]

    # 1. Matrice di covarianza semi-definita positiva garantita: Sigma = A @ A.T + diag(eps)
    A = draw(st.lists(
        st.lists(st.floats(min_value=-0.04, max_value=0.04, allow_nan=False, allow_infinity=False), min_size=n_assets, max_size=n_assets),
        min_size=n_assets, max_size=n_assets
    ))
    A_mat = np.array(A)
    sigma = A_mat @ A_mat.T + np.eye(n_assets) * 1e-4

    # 2. Genera rendimenti correlati con media zero
    L = np.linalg.cholesky(sigma)
    z = np.random.randn(n_days, n_assets)
    returns_arr = z @ L.T
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    df_returns = pd.DataFrame(returns_arr, index=dates, columns=tickers)

    # 3. Pesi positivi casuali (somma normalizzata a 1.0)
    raw_weights = draw(st.lists(st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=n_assets, max_size=n_assets))
    w_sum = sum(raw_weights)
    norm_weights = [w / w_sum for w in raw_weights]

    tot_val = draw(st.floats(min_value=20_000.0, max_value=2_000_000.0, allow_nan=False, allow_infinity=False))

    df_positions = pd.DataFrame({
        "ticker": tickers,
        "weight_pct": [w * 100.0 for w in norm_weights],
        "current_value": [w * tot_val for w in norm_weights],
        "qty_net": [10.0] * n_assets
    })

    conf = draw(st.sampled_from([0.90, 0.95, 0.99]))
    horizon = draw(st.integers(min_value=1, max_value=10))

    return df_returns, df_positions, conf, tot_val, horizon


@settings(max_examples=35, deadline=None)
@given(portfolio_and_returns_strategy())
def test_hypothesis_euler_theorem_invariant(data):
    """
    INVARIANTE MATEMATICA DI EULERO:
    La somma dei Component VaR di tutti i singoli titoli DEVE coincidere con
    il VaR complessivo di portafoglio, e la somma dei PCTR deve fare 100%.
    """
    df_returns, df_positions, conf, tot_val, horizon = data

    res = compute_marginal_and_component_var(
        df_returns=df_returns,
        df_positions=df_positions,
        confidence_level=conf,
        total_portfolio_value=tot_val,
        time_horizon=horizon
    )

    assert res["euler_check_passed"] is True, f"Verifica Eulero fallita! Residuo: {res['euler_residual']}"

    decomp = res["decomposition_df"]
    assert not decomp.empty

    total_port_var_amount = res["portfolio_var_amount"]
    sum_component_var_amount = float(decomp["component_var_amount"].sum())

    # Errore relativo di riconciliazione monetaria < 0.2%
    rel_error = abs(sum_component_var_amount - total_port_var_amount) / max(1.0, total_port_var_amount)
    assert rel_error < 2e-3, f"Errore relativo di quadratura monetaria troppo alto: {rel_error:.6f}"

    # Somma percentuali di contributo al rischio (PCTR) == 100% (+- 0.25%)
    sum_risk_pct = float(decomp["risk_contribution_pct"].sum())
    assert abs(sum_risk_pct - 100.0) < 0.25, f"La somma dei PCTR non fa 100%: {sum_risk_pct:.3f}%"
