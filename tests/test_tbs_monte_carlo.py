"""
tests/test_tbs_monte_carlo.py
Unit tests for Total Balance Sheet Lifetime Monte Carlo Simulation Engine.
"""

import pytest
import numpy as np
from core.wealth.tbs_monte_carlo import (
    TBSLifecycleConfig,
    TBSMonteCarloEngine
)


def test_tbs_monte_carlo_baseline():
    cfg = TBSLifecycleConfig(
        current_age=30,
        retirement_age=65,
        terminal_age=85,
        current_annual_net_income=50000.0,
        annual_living_expenses=25000.0,
        initial_liquid_wealth=80000.0,
        num_simulations=500,
        random_seed=42
    )
    engine = TBSMonteCarloEngine(cfg)
    res = engine.simulate_lifetime_solvency()

    assert "total_ruin_probability_pct" in res
    assert 0.0 <= res["total_ruin_probability_pct"] <= 100.0
    assert "timeline_df" in res
    df = res["timeline_df"]

    # Total years = 85 - 30 = 55. Number of rows = 56 (including t=0)
    assert len(df) == 56
    assert df["age"].iloc[0] == 30
    assert df["age"].iloc[-1] == 85

    # Check percentile monotonicity: P10 <= P25 <= P50 <= P75 <= P90
    for idx, row in df.iterrows():
        assert row["net_worth_p10"] <= row["net_worth_p25"] + 1e-3
        assert row["net_worth_p25"] <= row["net_worth_p50"] + 1e-3
        assert row["net_worth_p50"] <= row["net_worth_p75"] + 1e-3
        assert row["net_worth_p75"] <= row["net_worth_p90"] + 1e-3

    assert res["median_terminal_net_worth_eur"] > 0


def test_tbs_monte_carlo_high_fragility_scenario():
    # Extreme expense scenario: expenses exceed income with low liquid wealth
    cfg = TBSLifecycleConfig(
        current_age=40,
        retirement_age=65,
        terminal_age=80,
        current_annual_net_income=30000.0,
        annual_living_expenses=60000.0,  # Huge deficit
        initial_liquid_wealth=20000.0,
        initial_mortgage_debt=150000.0,
        num_simulations=400,
        random_seed=42
    )
    engine = TBSMonteCarloEngine(cfg)
    res = engine.simulate_lifetime_solvency()

    assert res["total_ruin_probability_pct"] > 50.0
    assert res["spending_adjustment_needed"] is True
    assert res["recommended_spending_cut_eur"] > 0
    assert res["recommended_annual_spending_eur"] < 60000.0
