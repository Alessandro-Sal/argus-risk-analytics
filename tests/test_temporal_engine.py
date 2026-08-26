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


def test_compute_side_by_side_comparison():
    from core.temporal_engine import compute_side_by_side_comparison
    df_a = pd.DataFrame({
        "ticker": ["AAPL", "NVDA", "BTC"],
        "asset_class": ["Stock", "Stock", "Crypto"],
        "qty_net": [10.0, 5.0, 0.5],
        "current_value": [1500.0, 600.0, 30000.0],
        "weight_pct": [4.67, 1.87, 93.46]
    })
    df_b = pd.DataFrame({
        "ticker": ["AAPL", "NVDA", "ETH"],
        "asset_class": ["Stock", "Stock", "Crypto"],
        "qty_net": [8.0, 5.0, 5.0],
        "current_value": [1200.0, 600.0, 10000.0],
        "weight_pct": [10.17, 5.08, 84.75]
    })

    comp = compute_side_by_side_comparison(df_a, df_b)
    assert not comp["df_merged"].empty
    assert comp["tot_val_a"] == 32100.0
    assert comp["tot_val_b"] == 11800.0
    assert comp["delta_nav"] > 0
    assert comp["turnover_pct"] > 0
    assert comp["new_entries_count"] == 1 # BTC
    assert comp["closed_entries_count"] == 1 # ETH


def test_reconstruct_point_in_time_portfolio():
    from core.temporal_engine import reconstruct_point_in_time_portfolio
    dates = pd.date_range(start="2023-01-01", end="2024-12-31", freq="B")
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0.0005, 0.01, len(dates)), index=dates)
    returns_df = pd.DataFrame({
        "AAPL": np.random.normal(0.0006, 0.012, len(dates)),
        "NVDA": np.random.normal(0.0008, 0.015, len(dates))
    }, index=dates)
    pos_today = pd.DataFrame({
        "ticker": ["AAPL", "NVDA"],
        "current_value": [5000.0, 5000.0],
        "weight_pct": [50.0, 50.0],
        "last_price": [150.0, 100.0]
    })

    target_dt = dates[150]
    res = reconstruct_point_in_time_portfolio(pos_today, sr_port, returns_df, target_dt)
    assert not res["df_positions"].empty
    assert res["total_value"] > 0
    assert "sharpe_ratio" in res["metrics"]
    assert "volatility_ann_pct" in res["metrics"]


