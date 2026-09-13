"""
ARGUS — Application Service Layer: Risk & Optimization Service.
Headless orchestration of quantitative market risk, Cornish-Fisher VaR/CVaR,
and Hierarchical Risk Parity (HRP) portfolio optimization.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from core.hrp_optimizer import compute_hrp_portfolio
from core.risk_engine import _calc_market_risk, _calc_return_metrics


class RiskService:
    """Headless application service for risk calculations and portfolio optimization."""

    @staticmethod
    def compute_risk_metrics(
        returns: List[float],
        benchmark_returns: Optional[List[float]] = None,
        risk_free_rate: float = 0.0275,
        confidence_levels: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Calcola le metriche istituzionali di rischio e rendimento:
        VaR/CVaR (Storico, Parametrico, Cornish-Fisher), Volatilità, Sharpe, Sortino, Max Drawdown.
        """
        sr_portfolio = pd.Series(returns, dtype=float).dropna()
        if len(sr_portfolio) < 2:
            raise ValueError("Return series must contain at least 2 non-null observations.")

        if benchmark_returns is not None:
            sr_bm = pd.Series(benchmark_returns, dtype=float).reindex(sr_portfolio.index).fillna(0.0)
        else:
            sr_bm = pd.Series(0.0, index=sr_portfolio.index)

        mkt_risk = _calc_market_risk(
            sr_portfolio=sr_portfolio,
            sr_benchmark=sr_bm,
            benchmark_ticker="BENCHMARK",
            risk_free_rate=risk_free_rate
        )

        ret_metrics = _calc_return_metrics(
            sr_portfolio=sr_portfolio,
            sr_benchmark=sr_bm,
            risk_free_rate=risk_free_rate
        )

        var_raw = mkt_risk.get("var", {})
        cvar_raw = mkt_risk.get("cvar", {})

        var_hist = {f"{k}%": v for k, v in var_raw.items() if not k.startswith("var_parametric") and not k.startswith("var_cf")}
        cvar_hist = {f"{k}%": v for k, v in cvar_raw.items() if not k.startswith("cvar_parametric") and not k.startswith("cvar_cf")}

        var_param = {k.replace("var_parametric_", "") + "%": v for k, v in var_raw.items() if k.startswith("var_parametric_")}
        cvar_param = {k.replace("cvar_parametric_", "") + "%": v for k, v in cvar_raw.items() if k.startswith("cvar_parametric_")}

        var_cf = {k.replace("var_cf_", "") + "%": v for k, v in var_raw.items() if k.startswith("var_cf_")}
        cvar_cf = {k.replace("cvar_cf_", "") + "%": v for k, v in cvar_raw.items() if k.startswith("cvar_cf_")}

        vol_pct = float(mkt_risk.get("volatility_annual_pct", 0.0))

        return {
            "var_historical": var_hist,
            "cvar_historical": cvar_hist,
            "var_parametric": var_param,
            "cvar_parametric": cvar_param,
            "var_cornish_fisher": var_cf,
            "cvar_cornish_fisher": cvar_cf,
            "sharpe_ratio": float(ret_metrics.get("sharpe", 0.0)),
            "sortino_ratio": float(ret_metrics.get("sortino", 0.0)),
            "max_drawdown": float(ret_metrics.get("max_drawdown", 0.0)),
            "volatility_annual": round(vol_pct / 100.0, 6),
            "volatility_annual_pct": round(vol_pct, 4),
            "cagr": ret_metrics.get("cagr"),
            "skewness": float(mkt_risk.get("skewness", 0.0)),
            "kurtosis": float(mkt_risk.get("kurtosis", 0.0)),
        }

    @staticmethod
    def optimize_hrp(
        asset_returns: Dict[str, List[float]],
        linkage_method: str = "single"
    ) -> Dict[str, Any]:
        """Esegue l'ottimizzazione di portafoglio Hierarchical Risk Parity (López de Prado)."""
        if not asset_returns or len(asset_returns) < 2:
            raise ValueError("At least two asset return series are required for portfolio optimization.")

        df_returns = pd.DataFrame(asset_returns).dropna(axis=0, how="any")
        if df_returns.shape[0] < 5:
            df_returns = pd.DataFrame(asset_returns).fillna(0.0)

        result = compute_hrp_portfolio(df_returns, linkage_method=linkage_method)
        if not result or "weights" not in result:
            raise RuntimeError("HRP optimization could not converge on provided asset returns.")

        return {
            "weights": {k: round(float(v), 6) for k, v in result["weights"].items()},
            "expected_return_pct": round(float(result.get("expected_return_pct", 0.0)), 4),
            "volatility_annual_pct": round(float(result.get("volatility_annual_pct", 0.0)), 4),
            "sharpe_ratio": round(float(result.get("sharpe_ratio", 0.0)), 4),
            "sorted_assets": result.get("sorted_assets", list(asset_returns.keys())),
        }

    @staticmethod
    def run_monte_carlo(
        results_dict: Dict[str, Any],
        horizon_days: int = 252,
        volatility_multiplier: float = 1.0,
        drift_shift_pct: float = 0.0,
        distribution_type: str = "gaussian",
        n_simulations: int = 3000,
        seed: int = 42
    ) -> Dict[str, Any]:
        """Esegue la simulazione stocastica Monte Carlo multivariata del portafoglio."""
        from core.risk_engine import run_advanced_monte_carlo_simulation
        return run_advanced_monte_carlo_simulation(
            results_dict=results_dict,
            horizon_days=horizon_days,
            volatility_multiplier=volatility_multiplier,
            drift_shift_pct=drift_shift_pct,
            distribution_type=distribution_type,
            n_simulations=n_simulations,
            seed=seed
        )

