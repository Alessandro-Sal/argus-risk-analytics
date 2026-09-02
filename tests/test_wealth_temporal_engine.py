# ============================================================
# tests/test_wealth_temporal_engine.py
# Unit tests for ARGUS Wealth Temporal Analytics & Modals
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.fetcher import get_engine
from core.wealth.wealth_temporal_engine import (
    compute_wealth_temporal_progression,
    compute_wealth_monthly_matrix,
    compute_wealth_rolling_metrics,
    compute_wealth_underwater_drawdowns,
    compute_wealth_seasonality_patterns,
    compute_wealth_growth_attribution,
    compute_wealth_benchmark_comparison
)
from core.terminal_engine import get_terminal_engine


def test_wealth_temporal_progression():
    engine = get_engine()
    res = compute_wealth_temporal_progression(engine, portfolio_id=1, timeframe_months=12)
    assert res["months_count"] == 13

    res24_real = compute_wealth_temporal_progression(engine, portfolio_id=1, timeframe_months=24, adjust_inflation=True)
    assert res24_real["is_inflation_adjusted"] is True
    assert res24_real["months_count"] == 25


def test_wealth_growth_attribution():
    engine = get_engine()
    res = compute_wealth_growth_attribution(engine, portfolio_id=1, timeframe_months=24)
    assert "attribution_df" in res
    assert not res["attribution_df"].empty
    assert "cumulative_savings_eur" in res
    assert "cumulative_market_pnl_eur" in res
    assert "savings_share_pct" in res
    assert "market_share_pct" in res


def test_wealth_benchmark_comparison():
    engine = get_engine()
    res = compute_wealth_benchmark_comparison(engine, portfolio_id=1, timeframe_months=24)
    assert "comparison_df" in res
    assert not res["comparison_df"].empty
    assert "nw_cumulative_return_pct" in res
    assert "bm_cumulative_return_pct" in res
    assert "outperformance_pct" in res
    assert "wealth_beta" in res
    assert res["wealth_beta"] > 0


def test_wealth_monthly_matrix():
    engine = get_engine()
    df_matrix = compute_wealth_monthly_matrix(engine, portfolio_id=1)

    assert not df_matrix.empty
    assert "Gen" in df_matrix.columns
    assert "Dic" in df_matrix.columns
    assert "Totale Annuo (€)" in df_matrix.columns


def test_wealth_rolling_metrics():
    engine = get_engine()
    df_roll = compute_wealth_rolling_metrics(engine, portfolio_id=1, window_months=6)

    assert not df_roll.empty
    assert "Net_Worth_EUR" in df_roll.columns
    assert "Rolling_Growth_Pct" in df_roll.columns
    assert "Rolling_Wealth_Vol_Pct" in df_roll.columns


def test_wealth_underwater_drawdowns():
    engine = get_engine()
    res = compute_wealth_underwater_drawdowns(engine, portfolio_id=1)

    assert "underwater_df" in res
    assert not res["underwater_df"].empty
    assert "max_drawdown_pct" in res
    assert "episodes_df" in res
    assert not res["episodes_df"].empty


def test_wealth_seasonality_patterns():
    engine = get_engine()
    res = compute_wealth_seasonality_patterns(engine, portfolio_id=1)

    assert "seasonality_df" in res
    assert len(res["seasonality_df"]) == 12
    assert res["best_accumulation_month"] is not None
    assert res["heaviest_spending_month"] is not None


def test_wealth_time_terminal_command():
    term = get_terminal_engine()
    ctx = {"engine": get_engine()}

    res = term.execute_command("WEALTH TIME", ctx)
    assert res.status == "SUCCESS"
    assert "WEALTH TEMPORAL ANALYTICS" in res.output_text

