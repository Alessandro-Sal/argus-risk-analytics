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
    compute_wealth_seasonality_patterns
)
from core.terminal_engine import get_terminal_engine


def test_wealth_temporal_progression():
    engine = get_engine()
    res = compute_wealth_temporal_progression(engine, portfolio_id=1)

    assert "history_df" in res
    assert not res["history_df"].empty
    assert res["months_count"] >= 12
    assert res["final_net_worth_eur"] > 0
    assert "total_growth_eur" in res


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
