"""
Unit tests for Kenneth French Factor Library & Fama-French Multifactors Engine.
"""

import numpy as np
import pandas as pd

from core.factor_library import (
    _generate_synthetic_benchmark_factors,
    compute_fama_french_factor_model,
    fetch_kenneth_french_factors,
)


def test_generate_synthetic_benchmark_factors():
    df = _generate_synthetic_benchmark_factors("2022-01-01", "2023-12-31")
    assert not df.empty
    expected_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM", "RF"]
    for col in expected_cols:
        assert col in df.columns
    assert len(df) > 400


def test_fetch_kenneth_french_factors():
    df = fetch_kenneth_french_factors(use_cache=True)
    assert not df.empty
    assert "Mkt-RF" in df.columns
    assert "SMB" in df.columns
    assert "HML" in df.columns


def test_compute_fama_french_factor_model_3factor():
    dates = pd.date_range("2023-01-01", "2024-01-01", freq="B")
    np.random.seed(42)
    sr_p = pd.Series(np.random.normal(0.0005, 0.012, len(dates)), index=dates)

    res = compute_fama_french_factor_model(sr_p, model_type="3_factor")
    assert res["model_type"] == "3_factor"
    assert "alpha_annualized" in res
    assert "r_squared" in res
    assert res["r_squared"] >= 0.0

    df_factors = res["df_factors"]
    assert not df_factors.empty
    assert len(df_factors) == 3
    assert set(df_factors["factor"]) == {"Mkt-RF", "SMB", "HML"}


def test_compute_fama_french_factor_model_5factor_mom():
    factors_df = _generate_synthetic_benchmark_factors("2022-01-01", "2024-06-30")

    # Costruiamo un portafoglio con esposizioni note: 1.2 Mkt + 0.4 SMB - 0.3 HML + 0.5 MOM + 2% Alpha
    sr_p = (
        1.2 * factors_df["Mkt-RF"]
        + 0.4 * factors_df["SMB"]
        - 0.3 * factors_df["HML"]
        + 0.5 * factors_df["MOM"]
        + factors_df["RF"]
        + (0.02 / 252.0)
    )

    res = compute_fama_french_factor_model(sr_p, model_type="5_factor_mom", factors_df=factors_df)
    assert res["model_type"] == "5_factor_mom"
    assert res["r_squared"] > 0.95

    df_factors = res["df_factors"].set_index("factor")
    assert abs(df_factors.loc["Mkt-RF", "beta"] - 1.2) < 0.05
    assert abs(df_factors.loc["SMB", "beta"] - 0.4) < 0.05
    assert abs(df_factors.loc["HML", "beta"] - (-0.3)) < 0.05
    assert abs(df_factors.loc["MOM", "beta"] - 0.5) < 0.05

    # Test significatività
    assert bool(df_factors.loc["Mkt-RF", "is_significant"]) is True

    # Test factor attribution
    attrib = res["factor_attribution"]
    assert "Alpha" in attrib
    assert "Mkt-RF" in attrib

    # Test rolling betas
    rolling_df = res["rolling_betas"]
    assert not rolling_df.empty
    assert "Mkt-RF" in rolling_df.columns


def test_compute_fama_french_factor_model_empty_and_short_series():
    empty_res = compute_fama_french_factor_model(pd.Series(dtype=float))
    assert empty_res["observations"] == 0
    assert empty_res["r_squared"] == 0.0

    short_sr = pd.Series([0.01, -0.02, 0.03], index=pd.date_range("2024-01-01", periods=3))
    short_res = compute_fama_french_factor_model(short_sr)
    assert short_res["observations"] == 0
