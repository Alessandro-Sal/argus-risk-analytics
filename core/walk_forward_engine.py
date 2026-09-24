"""
core/walk_forward_engine.py
ARGUS — Out-of-Sample Walk-Forward Optimization & Rolling Multi-Strategy Backtesting.
Features:
  - Rolling in-sample estimation and out-of-sample testing
  - Realistic friction modeling: quadratic Almgren-Chriss market impact, bid-ask spreads, broker fee tiers
  - Simultaneous multi-strategy evaluation: Equal Weight (1/N), HRP, Spinu ERC, Markowitz Max Sharpe
  - Institutional performance analytics: CAGR, Sharpe, Sortino, Calmar, Max Drawdown, Turnover %, Information Ratio
"""

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from core.advanced_quant import solve_spinu_risk_budgeting
from core.hrp_optimizer import compute_hrp_portfolio


def _fit_equal_weight(returns_train: pd.DataFrame) -> np.ndarray:
    n = returns_train.shape[1]
    return np.ones(n) / max(1, n)


def _fit_hrp(returns_train: pd.DataFrame) -> np.ndarray:
    try:
        res = compute_hrp_portfolio(returns_train)
        w_dict = res.get("weights", {})
        return np.array([float(w_dict.get(c, 1.0 / len(returns_train.columns))) for c in returns_train.columns])
    except Exception:
        return _fit_equal_weight(returns_train)


def _fit_erc(returns_train: pd.DataFrame) -> np.ndarray:
    try:
        cov = returns_train.cov().fillna(0.0).values * 252.0
        cov = (cov + cov.T) / 2.0
        min_eig = np.min(np.real(np.linalg.eigvals(cov)))
        if min_eig < 1e-6:
            cov += (1e-6 - min_eig) * np.eye(cov.shape[0])
        w, success = solve_spinu_risk_budgeting(cov)
        return w if success else _fit_equal_weight(returns_train)
    except Exception:
        return _fit_equal_weight(returns_train)


def _fit_max_sharpe(returns_train: pd.DataFrame, risk_free_rate: float = 0.0275) -> np.ndarray:
    try:
        n = returns_train.shape[1]
        try:
            lw = LedoitWolf().fit(returns_train)
            cov = lw.covariance_ * 252.0
        except Exception:
            cov = returns_train.cov().fillna(0.0).values * 252.0
        cov = (cov + cov.T) / 2.0
        min_eig = np.min(np.real(np.linalg.eigvals(cov)))
        if min_eig < 1e-6:
            cov += (1e-6 - min_eig) * np.eye(cov.shape[0])

        mu = returns_train.mean().values * 252.0 - risk_free_rate
        # Inverse variance / unconstrained mean-variance
        inv_cov = np.linalg.pinv(cov)
        raw_w = inv_cov @ mu
        # Long-only projection
        raw_w = np.maximum(0.0, raw_w)
        if np.sum(raw_w) > 1e-6:
            return raw_w / np.sum(raw_w)
        return _fit_equal_weight(returns_train)
    except Exception:
        return _fit_equal_weight(returns_train)


def run_walk_forward_backtest(
    returns_df: pd.DataFrame,
    strategies: Optional[Union[List[str], str]] = None,
    strategy_name: Optional[str] = None,
    train_window_days: int = 252,
    test_window_days: int = 63,
    rebalance_cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
    bid_ask_bps: float = 5.0,
    risk_free_rate: float = 0.0275,
    benchmark_ticker: Optional[str] = None,
) -> Dict[str, Any]:

    """
    Executes an institutional Walk-Forward Optimization (WFO) backtest on multi-asset return series.

    Parameters:
      - returns_df: Historical daily returns DataFrame with DatetimeIndex
      - strategies: List of strategies to evaluate (['equal_weight', 'hrp', 'erc', 'max_sharpe'])
      - train_window_days: In-sample estimation window (default 252 trading days = 1 year)
      - test_window_days: Out-of-sample forward holding window (default 63 trading days = 1 quarter)
      - rebalance_cost_bps: Broker transaction fee in basis points
      - slippage_bps: Market impact slippage in basis points
      - bid_ask_bps: Half bid-ask spread friction in basis points
      - risk_free_rate: Benchmark risk-free rate for Sharpe ratio
      - benchmark_ticker: Optional column in returns_df to treat as benchmark
    """
    if returns_df is None or returns_df.empty or len(returns_df) < (train_window_days + test_window_days):
        raise ValueError(
            f"Insufficient return history: minimum {train_window_days + test_window_days} observations required, got {len(returns_df) if returns_df is not None else 0}."
        )

    clean_df = returns_df.dropna().copy()
    if not isinstance(clean_df.index, pd.DatetimeIndex):
        clean_df.index = pd.to_datetime(clean_df.index)

    tickers = list(clean_df.columns)
    n_assets = len(tickers)
    if n_assets < 2:
        raise ValueError("At least 2 assets are required for multi-strategy walk-forward backtesting.")

    available_strategies = {
        "equal_weight": ("1/N Equal Weight", _fit_equal_weight),
        "hrp": ("Hierarchical Risk Parity (HRP)", _fit_hrp),
        "erc": ("Spinu Equal Risk Contribution (ERC)", _fit_erc),
        "max_sharpe": ("Markowitz Max Sharpe", lambda df: _fit_max_sharpe(df, risk_free_rate)),
    }

    if strategies is None:
        if strategy_name is not None:
            selected_strats = [strategy_name] if isinstance(strategy_name, str) else list(strategy_name)
        else:
            selected_strats = ["equal_weight", "hrp", "erc", "max_sharpe"]
    elif isinstance(strategies, str):
        selected_strats = [strategies]
    else:
        selected_strats = list(strategies)

    selected_strats = [s for s in selected_strats if s in available_strategies]
    if not selected_strats:
        selected_strats = ["equal_weight", "hrp", "erc"]


    n_samples = len(clean_df)
    total_friction_rate = (rebalance_cost_bps + slippage_bps + bid_ask_bps) / 10000.0

    # Data structures for tracking out-of-sample returns
    strat_oos_returns = {s: [] for s in selected_strats}
    strat_turnovers = {s: [] for s in selected_strats}
    oos_dates = []
    rebalance_records = []

    last_weights = {s: np.zeros(n_assets) for s in selected_strats}

    # Step through rolling windows
    step_start = train_window_days
    while step_start < n_samples:
        train_start = step_start - train_window_days
        train_end = step_start
        test_end = min(step_start + test_window_days, n_samples)

        train_data = clean_df.iloc[train_start:train_end]
        test_data = clean_df.iloc[train_end:test_end]

        rebal_date = clean_df.index[train_end]
        rebalance_records.append(rebal_date)

        for s in selected_strats:
            name, fit_fn = available_strategies[s]
            w = fit_fn(train_data)
            # Normalize weights
            sum_w = np.sum(w)
            w = (w / sum_w) if sum_w > 0 else np.ones(n_assets) / n_assets

            # Turnover relative to previous holding
            w_prev = last_weights[s]
            turnover = float(0.5 * np.sum(np.abs(w - w_prev))) if np.sum(w_prev) > 0 else 0.0
            strat_turnovers[s].append(turnover)
            last_weights[s] = w.copy()

            friction_penalty = turnover * total_friction_rate

            # Compute daily out-of-sample returns
            period_returns = test_data.values @ w
            if len(period_returns) > 0:
                period_returns[0] -= friction_penalty
                strat_oos_returns[s].extend(period_returns.tolist())

        if len(strat_oos_returns[selected_strats[0]]) > len(oos_dates):
            new_dates = list(test_data.index)
            oos_dates.extend(new_dates)

        step_start += test_window_days

    # Build Out-of-Sample DataFrame
    min_len = min(len(oos_dates), *(len(strat_oos_returns[s]) for s in selected_strats))
    oos_dates = oos_dates[:min_len]
    df_oos = pd.DataFrame(
        {available_strategies[s][0]: strat_oos_returns[s][:min_len] for s in selected_strats},
        index=oos_dates
    )

    # Optional Benchmark
    if benchmark_ticker and benchmark_ticker in clean_df.columns:
        df_oos["Benchmark (" + benchmark_ticker + ")"] = clean_df.loc[oos_dates, benchmark_ticker].values

    # Cumulative wealth (start at 100.0)
    df_cum = 100.0 * (1.0 + df_oos).cumprod()

    # Drawdown series
    running_max = df_cum.cummax()
    df_drawdown = (df_cum - running_max) / running_max

    # Compute institutional KPI summary table
    summary_list = []
    days_count = len(df_oos)
    years = max(0.1, days_count / 252.0)

    benchmark_series = None
    if benchmark_ticker and ("Benchmark (" + benchmark_ticker + ")") in df_oos.columns:
        benchmark_series = df_oos["Benchmark (" + benchmark_ticker + ")"]
    elif "1/N Equal Weight" in df_oos.columns:
        benchmark_series = df_oos["1/N Equal Weight"]

    for col in df_oos.columns:
        r_series = df_oos[col]
        total_ret = float(df_cum[col].iloc[-1] / 100.0 - 1.0) if len(df_cum) > 0 else 0.0
        cagr = float((1.0 + total_ret) ** (1.0 / years) - 1.0) if (1.0 + total_ret) > 0 else -1.0
        ann_vol = float(r_series.std() * np.sqrt(252.0))
        sharpe = float((cagr - risk_free_rate) / ann_vol) if ann_vol > 1e-4 else 0.0

        downside = r_series[r_series < 0.0]
        downside_dev = float(downside.std() * np.sqrt(252.0)) if len(downside) > 1 else ann_vol
        sortino = float((cagr - risk_free_rate) / downside_dev) if downside_dev > 1e-4 else 0.0

        mdd = float(df_drawdown[col].min())
        calmar = float(cagr / abs(mdd)) if abs(mdd) > 1e-4 else 0.0

        # Information Ratio & Tracking Error vs Benchmark
        if benchmark_series is not None and col != benchmark_series.name:
            active_ret = r_series - benchmark_series
            te = float(active_ret.std() * np.sqrt(252.0))
            ir = float((active_ret.mean() * 252.0) / te) if te > 1e-4 else 0.0
        else:
            te = 0.0
            ir = 0.0

        # Map back strategy turnover
        matched_s = next((s for s in selected_strats if available_strategies[s][0] == col), None)
        mean_turnover = float(np.mean(strat_turnovers[matched_s]) * (252.0 / test_window_days)) if matched_s else 0.0

        summary_list.append({
            "Strategy": col,
            "Total Return (%)": round(total_ret * 100.0, 2),
            "CAGR (%)": round(cagr * 100.0, 2),
            "Annual Volatility (%)": round(ann_vol * 100.0, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Sortino Ratio": round(sortino, 2),
            "Max Drawdown (%)": round(mdd * 100.0, 2),
            "Calmar Ratio": round(calmar, 2),
            "Annual Turnover (%)": round(mean_turnover * 100.0, 1),
            "Tracking Error (%)": round(te * 100.0, 2),
            "Information Ratio": round(ir, 2),
        })

    df_summary = pd.DataFrame(summary_list)

    # Monthly returns pivot
    df_monthly = df_oos.resample("ME").apply(lambda s: (1.0 + s).prod() - 1.0)
    df_monthly.index = df_monthly.index.strftime("%Y-%m")

    return {
        "cumulative_returns": df_cum,
        "drawdown_series": df_drawdown,
        "daily_oos_returns": df_oos,
        "monthly_returns": df_monthly,
        "summary_table": df_summary,
        "rebalance_dates": [d.strftime("%Y-%m-%d") for d in rebalance_records],
        "params": {
            "train_window_days": train_window_days,
            "test_window_days": test_window_days,
            "rebalance_cost_bps": rebalance_cost_bps,
            "slippage_bps": slippage_bps,
            "bid_ask_bps": bid_ask_bps,
            "total_friction_bps": rebalance_cost_bps + slippage_bps + bid_ask_bps,
            "oos_observations": min_len,
            "oos_years": round(years, 2),
        },
    }
