import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core.temporal_engine import (
    compute_monthly_return_matrix,
    compute_rolling_risk_metrics,
    compute_underwater_drawdowns,
    compute_seasonality_patterns,
)


def test_compute_monthly_return_matrix():
    dates = pd.date_range(start="2023-01-01", end="2024-12-31", freq="B")
    np.random.seed(42)
    sr_returns = pd.Series(np.random.normal(0.0005, 0.01, len(dates)), index=dates)

    df_mat = compute_monthly_return_matrix(sr_returns)
    assert not df_mat.empty
    assert "YTD" in df_mat.columns
    assert "Gen" in df_mat.columns
    assert "Dic" in df_mat.columns
    assert 2023 in df_mat.index
    assert 2024 in df_mat.index


def test_compute_rolling_risk_metrics():
    dates = pd.date_range(start="2023-01-01", end="2024-12-31", freq="B")
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0.0006, 0.012, len(dates)), index=dates)
    sr_bm = pd.Series(np.random.normal(0.0004, 0.010, len(dates)), index=dates)

    df_roll = compute_rolling_risk_metrics(sr_port, sr_bm, window=60)
    assert not df_roll.empty
    assert "Rolling_Vol_Ann" in df_roll.columns
    assert "Rolling_Sharpe" in df_roll.columns
    assert "Rolling_Beta" in df_roll.columns
    assert "Rolling_Correlation" in df_roll.columns
    assert "Rolling_Tracking_Error" in df_roll.columns


def test_compute_underwater_drawdowns():
    dates = pd.date_range(start="2023-01-01", end="2024-12-31", freq="B")
    np.random.seed(42)
    # create artificial drawdown
    raw_rets = np.random.normal(0.0005, 0.01, len(dates))
    raw_rets[100:130] = -0.015 # deep drop
    sr_port = pd.Series(raw_rets, index=dates)

    res = compute_underwater_drawdowns(sr_port)
    assert "cumulative_nav" in res
    assert "hwm" in res
    assert "drawdown_series" in res
    assert res["max_drawdown_pct"] > 5.0
    assert res["ulcer_index"] > 0.0
    assert not res["top_episodes"].empty
    assert "max_drawdown_pct" in res["top_episodes"].columns
    assert "recovery_days" in res["top_episodes"].columns


def test_compute_seasonality_patterns():
    dates = pd.date_range(start="2023-01-01", end="2024-12-31", freq="B")
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0.0005, 0.01, len(dates)), index=dates)

    res = compute_seasonality_patterns(sr_port)
    assert "day_stats" in res
    assert "month_stats" in res
    assert len(res["day_stats"]) == 5
    assert len(res["month_stats"]) == 12
    assert "Mean_Pct" in res["day_stats"].columns
    assert "Win_Rate" in res["day_stats"].columns
