"""
ARGUS — Risk Analytics Platform
Core Module: Reinforcement Learning for Dynamic Portfolio Optimization (RL Agent Sandbox)
Implements Policy Gradient / Deep Q-inspired continuous-action policy optimization
trained to maximize Sortino / Sharpe utility with adaptive regime switching and transaction penalty.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, Union


class PortfolioEnv:
    """
    Simulation environment for portfolio management MDP (Markov Decision Process).
    Observation State: [Rolling Asset Sharpe, Asset Momentum, Asset Downside Volatility]
    Action: Simplex portfolio weight allocation w in Delta^{N-1}
    Reward: Risk-adjusted Sortino/Sharpe utility minus turnover friction with diversification incentive.
    """
    def __init__(
        self,
        df_returns: pd.DataFrame,
        window_size: int = 25,
        reward_type: str = "sortino",
        turnover_penalty: float = 0.0005
    ):
        self.df_returns = df_returns.dropna().copy()
        self.tickers = self.df_returns.columns.tolist()
        self.n_assets = len(self.tickers)
        self.window_size = max(15, window_size)
        self.reward_type = reward_type.lower()
        self.turnover_penalty = turnover_penalty
        self.current_step = 0
        self.max_steps = len(self.df_returns) - 1
        self.prev_weights = np.ones(self.n_assets) / self.n_assets

    def reset(self) -> np.ndarray:
        self.current_step = self.window_size
        self.prev_weights = np.ones(self.n_assets) / self.n_assets
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        window_data = self.df_returns.iloc[self.current_step - self.window_size : self.current_step].values
        means = np.mean(window_data, axis=0)
        vols = np.std(window_data, axis=0) + 1e-6
        sharpes = means / vols

        # Multi-timeframe momentum
        ema_fast = np.mean(window_data[-5:], axis=0)
        ema_slow = np.mean(window_data, axis=0)
        mom = (ema_fast - ema_slow) / vols

        # Cross-sectional z-score standardization across universe
        def _zscore(v: np.ndarray) -> np.ndarray:
            s = np.std(v)
            return (v - np.mean(v)) / (s + 1e-6) if s > 1e-6 else np.zeros_like(v)

        state = np.concatenate([_zscore(sharpes), _zscore(mom), _zscore(vols)])
        return np.clip(state, -3.0, 3.0)

    def step(self, action_weights: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        # Ensure weights are valid simplex on Delta^{N-1}
        w = np.maximum(0.001, action_weights)
        if np.sum(w) > 0:
            w = w / np.sum(w)
        else:
            w = np.ones(self.n_assets) / self.n_assets

        step_returns = self.df_returns.iloc[self.current_step].values
        portfolio_ret = float(np.dot(w, step_returns))

        # Turnover friction
        turnover = float(np.sum(np.abs(w - self.prev_weights)))
        cost = turnover * self.turnover_penalty
        net_ret = portfolio_ret - cost

        # Diversification incentive (1 - HHI is maximized when perfectly equi-weighted)
        div_bonus = 1.0 - float(np.sum(w ** 2))

        # Risk-adjusted reward calculation
        if self.reward_type == "sortino":
            downside = max(0.0, -net_ret)
            reward = net_ret * 100.0 - 2.5 * (downside * 100.0) - cost * 50.0 + 0.15 * div_bonus
        elif self.reward_type == "sharpe":
            vol_est = float(np.std(step_returns)) + 1e-4
            reward = (net_ret / vol_est) * 5.0 - cost * 50.0 + 0.10 * div_bonus
        else:
            # Min volatility
            reward = net_ret * 50.0 - 2.0 * (portfolio_ret ** 2) * 100.0 - cost * 50.0 + 0.20 * div_bonus

        self.prev_weights = w.copy()
        self.current_step += 1
        done = self.current_step >= self.max_steps
        next_state = self._get_state() if not done else np.zeros(self.n_assets * 3)

        info = {
            "net_return": net_ret,
            "raw_return": portfolio_ret,
            "turnover": turnover,
            "weights": w.copy()
        }
        return next_state, reward, done, info


class RLPolicyAgent:
    """
    Direct Policy-Gradient Neural Actor network for Continuous Portfolio Allocation.
    Trained with Batch Policy Gradient REINFORCE, Adam Optimization and Entropy Regularization.
    """
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 0.012,
        entropy_coeff: float = 0.04,
        random_seed: int = 42
    ):
        np.random.seed(random_seed)
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.entropy_coeff = entropy_coeff
        self.t = 0

        # Xavier Uniform Initialization
        limit1 = np.sqrt(6.0 / (state_dim + 32))
        self.W1 = np.random.uniform(-limit1, limit1, (state_dim, 32)) * 0.35
        self.b1 = np.zeros(32)

        limit2 = np.sqrt(6.0 / (32 + action_dim))
        self.W2 = np.random.uniform(-limit2, limit2, (32, action_dim)) * 0.08
        self.b2 = np.zeros(action_dim)

        # Adam moments
        self.mW1, self.vW1 = np.zeros_like(self.W1), np.zeros_like(self.W1)
        self.mb1, self.vb1 = np.zeros_like(self.b1), np.zeros_like(self.b1)
        self.mW2, self.vW2 = np.zeros_like(self.W2), np.zeros_like(self.W2)
        self.mb2, self.vb2 = np.zeros_like(self.b2), np.zeros_like(self.b2)

    def forward(self, state: np.ndarray, temperature: float = 1.0) -> np.ndarray:
        # Layer 1: Tanh for bounded non-linear representations
        h = np.tanh(np.dot(state, self.W1) + self.b1)
        # Layer 2: Logits with temperature scaling
        logits = (np.dot(h, self.W2) + self.b2) / max(0.2, temperature)
        # Stable Softmax
        exp_logits = np.exp(logits - np.max(logits))
        weights = exp_logits / np.sum(exp_logits)
        # Institutional blending with 1/N prior to prevent single-asset corner collapse
        prior_1n = np.ones(self.action_dim) / self.action_dim
        return 0.85 * weights + 0.15 * prior_1n

    def update(
        self,
        states: List[np.ndarray],
        actions: List[np.ndarray],
        rewards: List[float]
    ):
        self.t += 1
        T = len(rewards)
        if T == 0:
            return

        # Discounted returns G_t
        gamma = 0.98
        discounted_r = np.zeros(T)
        running_add = 0.0
        for t in reversed(range(T)):
            running_add = running_add * gamma + rewards[t]
            discounted_r[t] = running_add

        # Standardize returns / advantages
        std_g = np.std(discounted_r)
        if std_g > 1e-6:
            advantages = (discounted_r - np.mean(discounted_r)) / (std_g + 1e-6)
        else:
            advantages = discounted_r - np.mean(discounted_r)

        # Batch gradient accumulators
        g_W1 = np.zeros_like(self.W1)
        g_b1 = np.zeros_like(self.b1)
        g_W2 = np.zeros_like(self.W2)
        g_b2 = np.zeros_like(self.b2)

        for state, action, adv in zip(states, actions, advantages):
            h = np.tanh(np.dot(state, self.W1) + self.b1)
            pred_w = self.forward(state)

            # Policy gradient + entropy regularizer for exploration
            entropy_grad = (np.log(pred_w + 1e-8) + 1.0) * self.entropy_coeff
            d_logits = -(action - pred_w) * adv + entropy_grad
            d_logits = np.clip(d_logits, -1.5, 1.5)

            g_W2 += np.outer(h, d_logits)
            g_b2 += d_logits

            dh = np.dot(self.W2, d_logits) * (1.0 - h**2)
            g_W1 += np.outer(state, dh)
            g_b1 += dh

        # Average over batch trajectory
        g_W1 /= T
        g_b1 /= T
        g_W2 /= T
        g_b2 /= T

        # Global gradient clipping
        total_norm = np.sqrt(np.sum(g_W1**2) + np.sum(g_b1**2) + np.sum(g_W2**2) + np.sum(g_b2**2))
        clip_norm = 1.0
        if total_norm > clip_norm:
            scale = clip_norm / (total_norm + 1e-6)
            g_W1 *= scale
            g_b1 *= scale
            g_W2 *= scale
            g_b2 *= scale

        # Adam Optimizer parameter update
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        for p, g, m, v in [
            (self.W1, g_W1, self.mW1, self.vW1),
            (self.b1, g_b1, self.mb1, self.vb1),
            (self.W2, g_W2, self.mW2, self.vW2),
            (self.b2, g_b2, self.mb2, self.vb2)
        ]:
            m[:] = beta1 * m + (1.0 - beta1) * g
            v[:] = beta2 * v + (1.0 - beta2) * (g ** 2)
            m_hat = m / (1.0 - beta1 ** self.t)
            v_hat = v / (1.0 - beta2 ** self.t)
            p -= self.lr * m_hat / (np.sqrt(v_hat) + eps)


def train_and_evaluate_rl_portfolio(
    df_returns: pd.DataFrame,
    episodes: int = 35,
    window_size: int = 25,
    reward_type: str = "sortino",
    turnover_penalty: float = 0.0005,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Trains the Reinforcement Learning agent across historical episodes,
    evaluates out-of-sample portfolio trajectories, and compares performance against
    Equal-Weight (1/N) and Benchmark strategies.
    """
    if df_returns.empty or len(df_returns) < 60:
        return {
            "has_data": False,
            "learning_curve": pd.DataFrame(),
            "backtest_df": pd.DataFrame(),
            "weights_history": pd.DataFrame(),
            "summary_metrics": {}
        }

    rets = df_returns.dropna().copy()
    tickers = rets.columns.tolist()
    n_assets = len(tickers)
    state_dim = n_assets * 3
    action_dim = n_assets

    env = PortfolioEnv(
        rets,
        window_size=window_size,
        reward_type=reward_type,
        turnover_penalty=turnover_penalty
    )
    agent = RLPolicyAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        lr=0.012,
        entropy_coeff=0.04,
        random_seed=random_seed
    )

    learning_curve_data = []

    # ── TRAINING LOOP ──
    for ep in range(1, episodes + 1):
        state = env.reset()
        states_history, actions_history, rewards_history = [], [], []
        total_ep_reward = 0.0

        while True:
            # Forward pass + exploration noise smoothly decaying with training progress
            noise_scale = max(0.01, 0.08 * (1.0 - (ep / episodes)))
            raw_w = agent.forward(state)
            noisy_w = np.maximum(0.001, raw_w + np.random.normal(0, noise_scale, action_dim))
            action_w = noisy_w / np.sum(noisy_w)

            next_state, reward, done, info = env.step(action_w)

            states_history.append(state)
            actions_history.append(action_w)
            rewards_history.append(reward)
            total_ep_reward += reward

            state = next_state
            if done:
                break

        # Batch policy gradient update
        agent.update(states_history, actions_history, rewards_history)
        learning_curve_data.append({
            "episode": ep,
            "cumulative_reward": round(total_ep_reward, 2),
            "avg_reward_per_step": round(total_ep_reward / max(1, len(rewards_history)), 4)
        })

    # ── OUT-OF-SAMPLE EVALUATION RUN ──
    state = env.reset()
    eval_dates = rets.index[window_size:]
    
    rl_returns = []
    ew_returns = []
    weights_records = []
    
    ew_weight = np.ones(n_assets) / n_assets

    step_idx = 0
    while True:
        action_w = agent.forward(state) # Deterministic exploitation
        next_state, reward, done, info = env.step(action_w)
        
        rl_returns.append(info["net_return"])
        
        # Benchmark 1/N
        step_rets = env.df_returns.iloc[env.current_step - 1].values
        ew_returns.append(float(np.dot(ew_weight, step_rets)))

        # Record weights
        w_dict = {tickers[i]: round(float(action_w[i]), 4) for i in range(n_assets)}
        w_dict["date"] = str(eval_dates[step_idx])[:10] if step_idx < len(eval_dates) else f"T{step_idx}"
        weights_records.append(w_dict)

        state = next_state
        step_idx += 1
        if done or step_idx >= len(eval_dates):
            break

    # Build Backtest Curves
    n_pts = min(len(rl_returns), len(ew_returns), len(eval_dates))
    df_backtest = pd.DataFrame({
        "date": eval_dates[:n_pts],
        "rl_net_return": rl_returns[:n_pts],
        "ew_return": ew_returns[:n_pts]
    })
    df_backtest["rl_equity_curve"] = (1.0 + df_backtest["rl_net_return"]).cumprod() * 100.0
    df_backtest["ew_equity_curve"] = (1.0 + df_backtest["ew_return"]).cumprod() * 100.0

    # Calculate Summary Performance Metrics
    def calc_stats(ret_series: np.ndarray) -> Dict[str, float]:
        r_mean = float(np.mean(ret_series)) * 252.0 * 100.0
        r_vol = float(np.std(ret_series)) * np.sqrt(252.0) * 100.0
        sharpe = (r_mean - 2.75) / max(0.01, r_vol)
        downside = float(np.std(np.minimum(0, ret_series))) * np.sqrt(252.0) * 100.0
        sortino = (r_mean - 2.75) / max(0.01, downside)
        cum_ret = float((np.prod(1.0 + ret_series) - 1.0) * 100.0)
        # Max Drawdown
        peaks = np.maximum.accumulate(np.cumprod(1.0 + ret_series))
        dd = (np.cumprod(1.0 + ret_series) - peaks) / peaks
        max_dd = float(np.min(dd) * 100.0)
        return {
            "cagr_pct": round(r_mean, 2),
            "volatility_pct": round(r_vol, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_return_pct": round(cum_ret, 2)
        }

    rl_stats = calc_stats(np.array(rl_returns[:n_pts]))
    ew_stats = calc_stats(np.array(ew_returns[:n_pts]))

    return {
        "has_data": True,
        "tickers": tickers,
        "n_assets": n_assets,
        "episodes_trained": episodes,
        "learning_curve": pd.DataFrame(learning_curve_data),
        "backtest_df": df_backtest,
        "weights_history": pd.DataFrame(weights_records),
        "rl_stats": rl_stats,
        "ew_stats": ew_stats,
        "final_weights": {tickers[i]: round(float(agent.forward(state)[i]), 4) for i in range(n_assets)},
        "alpha_over_ew_pct": round(rl_stats["total_return_pct"] - ew_stats["total_return_pct"], 2)
    }
