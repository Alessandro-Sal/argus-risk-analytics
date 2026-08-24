"""
ARGUS — Risk Analytics Platform
Unit Tests for Reinforcement Learning Dynamic Portfolio Optimization
"""

import pytest
import pandas as pd
import numpy as np
from core.reinforcement_learning import (
    PortfolioEnv,
    RLPolicyAgent,
    train_and_evaluate_rl_portfolio
)


def test_rl_environment_step_and_reward():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    data = {
        "AAPL": np.random.normal(0.0005, 0.015, 100),
        "MSFT": np.random.normal(0.0004, 0.012, 100),
        "BND": np.random.normal(0.0001, 0.003, 100),
    }
    df_rets = pd.DataFrame(data, index=dates)
    
    env = PortfolioEnv(df_rets, window_size=20, reward_type="sortino")
    state = env.reset()
    assert len(state) == 3 * 3 # 3 features * 3 assets = 9
    
    action = np.array([0.5, 0.3, 0.2])
    next_state, reward, done, info = env.step(action)
    
    assert len(next_state) == 9
    assert isinstance(reward, float)
    assert not done
    assert "net_return" in info
    assert "weights" in info


def test_rl_policy_agent_forward_simplex():
    agent = RLPolicyAgent(state_dim=9, action_dim=3)
    dummy_state = np.random.randn(9)
    weights = agent.forward(dummy_state)
    
    assert len(weights) == 3
    assert np.all(weights >= 0)
    assert pytest.approx(float(np.sum(weights)), 1e-5) == 1.0


def test_train_and_evaluate_rl_portfolio():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=120, freq="B")
    data = {
        "NVDA": np.random.normal(0.001, 0.02, 120),
        "JNJ": np.random.normal(0.0002, 0.008, 120),
        "TLT": np.random.normal(-0.0001, 0.006, 120),
    }
    df_rets = pd.DataFrame(data, index=dates)
    
    rl_res = train_and_evaluate_rl_portfolio(df_rets, episodes=10, window_size=20)
    assert rl_res["has_data"] is True
    assert not rl_res["learning_curve"].empty
    assert not rl_res["backtest_df"].empty
    assert "rl_equity_curve" in rl_res["backtest_df"].columns
    assert "ew_equity_curve" in rl_res["backtest_df"].columns
    assert "rl_stats" in rl_res
    assert "ew_stats" in rl_res
    assert "final_weights" in rl_res
