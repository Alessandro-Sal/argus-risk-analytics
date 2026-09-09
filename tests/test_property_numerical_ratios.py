# ============================================================
# tests/test_property_numerical_ratios.py
# ARGUS — Property-Based Testing: Financial Ratios Robustness
# Tests Sharpe, Sortino, VaR Cornish-Fisher under zero-variance, jumps, and extreme draws
# ============================================================

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, settings, strategies as st
from core.risk_engine import _calc_return_metrics, _calc_market_risk


@st.composite
def extreme_returns_strategy(draw):
    """Genera serie storiche sintetiche con casi limite: costanti, salti estremi, valori tutti negativi/positivi."""
    n_days = draw(st.integers(min_value=5, max_value=200))
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")

    mode = draw(st.sampled_from(["flat", "extreme_jumps", "all_negative", "all_positive", "normal"]))

    if mode == "flat":
        vals = np.zeros(n_days)
    elif mode == "extreme_jumps":
        vals = draw(st.lists(st.floats(min_value=-0.70, max_value=2.0, allow_nan=False, allow_infinity=False), min_size=n_days, max_size=n_days))
    elif mode == "all_negative":
        vals = draw(st.lists(st.floats(min_value=-0.15, max_value=-0.0001, allow_nan=False, allow_infinity=False), min_size=n_days, max_size=n_days))
    elif mode == "all_positive":
        vals = draw(st.lists(st.floats(min_value=0.0001, max_value=0.15, allow_nan=False, allow_infinity=False), min_size=n_days, max_size=n_days))
    else:
        vals = np.random.randn(n_days) * 0.01

    rf = draw(st.floats(min_value=0.0, max_value=0.08, allow_nan=False, allow_infinity=False))
    return pd.Series(vals, index=dates), rf


@settings(max_examples=40, deadline=None)
@given(extreme_returns_strategy())
def test_hypothesis_risk_ratios_no_nan_or_inf(data):
    """
    GARANZIA DI STABILITÀ NUMERICA:
    Nessuna metrica di rischio o rendimento deve MAI restituire NaN o +/-Inf,
    nemmeno sotto condizioni di varianza zero o crash sistemico istantaneo.
    """
    sr_returns, rf = data
    sr_benchmark = pd.Series(0.0005, index=sr_returns.index)

    # 1. Test Return Metrics (Sharpe, Sortino, Calmar, Alpha, IR)
    ret_res = _calc_return_metrics(sr_returns, sr_benchmark, risk_free_rate=rf)

    for metric in ["sharpe_ratio", "sortino_ratio", "information_ratio", "total_return_pct"]:
        val = ret_res.get(metric)
        if val is not None:
            assert not np.isnan(val), f"La metrica {metric} ha prodotto NaN!"
            assert not np.isinf(val), f"La metrica {metric} ha prodotto +/-Inf!"

    # 2. Test Market Risk (VaR 95%, CVaR 95%, Cornish-Fisher)
    risk_res = _calc_market_risk(sr_returns, sr_benchmark, "BENCHMARK", risk_free_rate=rf)

    assert not np.isnan(risk_res["volatility_annual_pct"])
    assert not np.isnan(risk_res["var_95"])
    assert not np.isnan(risk_res["cvar_95"])
    assert not np.isnan(risk_res["var_cf_95"])

    # Proprietà ordinale del VaR: il CVaR (Expected Shortfall) DEVE essere sempre >= del VaR
    assert risk_res["cvar_95"] >= risk_res["var_95"] - 1e-4, (
        f"Violazione ordinale: CVaR ({risk_res['cvar_95']}) < VaR ({risk_res['var_95']})"
    )
