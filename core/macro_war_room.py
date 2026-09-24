"""
core/macro_war_room.py
ARGUS — Interactive Macro War Room & Correlation Breakdown Stress Engine.
Institutional Macro Risk & Stress Testing Standard.

References:
- Rebonato (2010): "Coherent Stress Testing: A Bayesian Approach to the Analysis of Financial Stress".
- Cont (2001): "Empirical properties of asset returns: stylized facts and statistical issues" (Correlation breakdown during market panics).
- Engle (2002): Dynamic Conditional Correlation (DCC-GARCH) breakdown under systemic liquidity drain.

Features:
- Multi-lever Macro Shock Constructor:
  * Parallel rate shift & yield curve twist (flattening / steepening)
  * Inflation surge (CPI shock & real rate compression)
  * Commodity / Energy shock (Brent crude oil +/- %)
  * Foreign Exchange shock (EUR/USD, USD/JPY)
  * Equity indices & Sector drawdowns
  * Credit spread widening (IG & HY OAS in bps)
- Systemic Correlation Breakdown Engine:
  * In normal regimes: assets show diversification benefits.
  * In systemic stress: cross-asset correlations collapse toward 1 (equicorrelation panic matrix):
    R_stressed = (1 - lambda) * R_base + lambda * R_panic, where rho_panic >= 0.85
    Sigma_stressed = D_stressed @ R_stressed @ D_stressed
- Asset Sensitivity & PnL Attribution (Duration, Convexity, Beta, Spread Duration, FX/Commodity Beta)
- Liquidity Drain & Variation Margin Call simulation
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass
class MacroShockScenario:
    """Multi-lever macro-economic and financial market stress scenario."""

    scenario_name: str = "Stagflationary Energy Shock & Rate Spike"
    parallel_rates_bps: float = 150.0  # +150 bps parallel shift
    slope_twist_bps: float = -50.0  # 2Y-10Y curve inversion / flattening
    inflation_shock_pct: float = 3.5  # +3.5% CPI surge
    oil_shock_pct: float = 40.0  # +40% oil spike
    fx_usd_pct: float = 5.0  # USD appreciation vs EUR (+5%)
    equity_shock_pct: float = -20.0  # -20% broad market drawdown
    credit_spread_widening_bps: float = 250.0  # +250 bps OAS widening
    correlation_breakdown_lambda: float = 0.60  # 0.0 = historical corr, 1.0 = full panic equicorrelation
    vol_surge_factor: float = 1.50  # 50% volatility spike under panic


@dataclass
class AssetSensitivityProfile:
    """Asset exposure and sensitivity parameters to macro factors."""

    asset_id: str
    name: str
    asset_class: str  # "EQUITY", "FIXED_INCOME", "COMMODITY", "REAL_ESTATE", "CASH_FX", "CREDIT"
    market_value_eur: float
    duration: float = 0.0  # Effective duration for fixed income / credit
    convexity: float = 0.0
    equity_beta: float = 1.0  # Market beta
    credit_spread_duration: float = 0.0
    fx_exposure: float = 0.0  # Fraction exposed to USD
    commodity_beta: float = 0.0
    annual_vol_pct: float = 15.0


@dataclass
class MacroWarRoomResult:
    """Comprehensive multi-lever stress testing & correlation breakdown analysis."""

    scenario_name: str
    portfolio_initial_value_eur: float
    portfolio_stressed_value_eur: float
    portfolio_total_pnl_eur: float
    portfolio_total_pnl_pct: float
    factor_pnl_attribution: Dict[str, float]
    base_portfolio_vol_pct: float
    stressed_portfolio_vol_pct: float
    diversification_loss_pct: float  # Vol increase purely driven by correlation breakdown
    base_var_99_10d_eur: float
    stressed_var_99_10d_eur: float
    liquidity_margin_drain_eur: float
    asset_pnl_breakdown_df: pd.DataFrame
    stressed_correlation_matrix: pd.DataFrame


class MacroWarRoomEngine:
    """
    Simulates macroeconomic systemic shocks and systemic correlation breakdowns.
    """

    def __init__(self, panic_correlation: float = 0.85):
        """
        Args:
            panic_correlation: Limiting correlation of all risky asset pairs during systemic contagion.
        """
        self.rho_panic = float(np.clip(panic_correlation, 0.50, 0.98))

    def stress_correlation_matrix(
        self,
        base_correlation: np.ndarray,
        lambda_breakdown: float = 0.50,
    ) -> np.ndarray:
        """
        Blends historical correlation with systemic equicorrelation matrix.
        R_stressed = (1 - lambda) * R_base + lambda * R_panic
        """
        n = base_correlation.shape[0]
        lam = float(np.clip(lambda_breakdown, 0.0, 1.0))

        # Panic equicorrelation matrix with 1 on diagonal and rho_panic off-diagonal
        r_panic = np.full((n, n), self.rho_panic)
        np.fill_diagonal(r_panic, 1.0)

        # Convex combination
        r_stressed = (1.0 - lam) * base_correlation + lam * r_panic

        # Ensure positive semi-definiteness via spectral clipping
        eigvals, eigvecs = np.linalg.eigh(r_stressed)
        eigvals = np.maximum(eigvals, 1e-6)
        r_psd = eigvecs @ np.diag(eigvals) @ eigvecs.T

        # Re-normalize diagonal to exactly 1.0
        d_inv = 1.0 / np.sqrt(np.diag(r_psd))
        r_stressed = np.diag(d_inv) @ r_psd @ np.diag(d_inv)
        np.fill_diagonal(r_stressed, 1.0)

        return r_stressed

    def run_simulation(
        self,
        assets: List[AssetSensitivityProfile],
        scenario: MacroShockScenario,
        base_correlation: Optional[np.ndarray] = None,
    ) -> MacroWarRoomResult:
        """
        Executes full macro shock and correlation breakdown simulation.
        """
        if not assets:
            raise ValueError("Assets list cannot be empty.")

        n = len(assets)
        total_mv = sum(a.market_value_eur for a in assets)
        if total_mv <= 0:
            raise ValueError("Total portfolio market value must be positive.")

        weights = np.array([a.market_value_eur / total_mv for a in assets])
        base_vols = np.array([a.annual_vol_pct / 100.0 for a in assets])

        # If base correlation is not provided, generate a plausible default
        if base_correlation is None or base_correlation.shape != (n, n):
            base_corr = np.eye(n)
            for i in range(n):
                for j in range(i + 1, n):
                    # Cross asset correlation is lower, same asset class higher
                    if assets[i].asset_class == assets[j].asset_class:
                        base_corr[i, j] = base_corr[j, i] = 0.55
                    elif "CASH" in assets[i].asset_class or "CASH" in assets[j].asset_class:
                        base_corr[i, j] = base_corr[j, i] = 0.05
                    else:
                        base_corr[i, j] = base_corr[j, i] = 0.25
        else:
            base_corr = base_correlation.copy()

        # 1. PnL Simulation per asset across macro shock levers
        dr = scenario.parallel_rates_bps / 10000.0
        dtwist = scenario.slope_twist_bps / 10000.0
        d_cpi = scenario.inflation_shock_pct / 100.0
        d_oil = scenario.oil_shock_pct / 100.0
        d_fx = scenario.fx_usd_pct / 100.0
        d_eq = scenario.equity_shock_pct / 100.0
        d_cs = scenario.credit_spread_widening_bps / 10000.0

        pnl_records = []
        factor_pnl = {
            "rates_parallel": 0.0,
            "curve_twist": 0.0,
            "inflation": 0.0,
            "oil_energy": 0.0,
            "fx_usd": 0.0,
            "equity_beta": 0.0,
            "credit_spread": 0.0,
        }

        for a in assets:
            # Rates: -Duration * dr + 0.5 * Convexity * dr^2
            pnl_rates = (-a.duration * dr + 0.5 * a.convexity * (dr**2)) * a.market_value_eur
            # Curve twist affects long-duration or fixed income assets (tilt factor)
            twist_mult = (a.duration - 5.0) / 10.0 if a.duration > 0 else 0.0
            pnl_twist = -twist_mult * dtwist * a.market_value_eur
            # Inflation impact on real assets vs nominal bonds
            if a.asset_class in ["COMMODITY", "REAL_ESTATE"]:
                pnl_infl = (d_cpi * 0.8) * a.market_value_eur
            elif a.asset_class in ["FIXED_INCOME", "CREDIT"]:
                pnl_infl = (-d_cpi * a.duration * 0.5) * a.market_value_eur
            else:
                pnl_infl = (-d_cpi * 0.2) * a.market_value_eur

            # Commodity/Oil shock
            pnl_oil = (a.commodity_beta * d_oil) * a.market_value_eur
            # FX shock
            pnl_fx = (a.fx_exposure * d_fx) * a.market_value_eur
            # Equity shock
            pnl_eq = (a.equity_beta * d_eq) * a.market_value_eur if a.equity_beta != 0.0 else 0.0
            # Credit spread shock
            pnl_cs = (-a.credit_spread_duration * d_cs) * a.market_value_eur

            total_asset_pnl = pnl_rates + pnl_twist + pnl_infl + pnl_oil + pnl_fx + pnl_eq + pnl_cs
            stressed_mv = max(0.0, a.market_value_eur + total_asset_pnl)

            pnl_records.append({
                "asset_id": a.asset_id,
                "name": a.name,
                "asset_class": a.asset_class,
                "market_value_eur": round(a.market_value_eur, 2),
                "stressed_market_value_eur": round(stressed_mv, 2),
                "total_pnl_eur": round(total_asset_pnl, 2),
                "pnl_pct": round((total_asset_pnl / a.market_value_eur) * 100.0, 2) if a.market_value_eur > 0 else 0.0,
                "pnl_rates_eur": round(pnl_rates, 2),
                "pnl_twist_eur": round(pnl_twist, 2),
                "pnl_inflation_eur": round(pnl_infl, 2),
                "pnl_oil_eur": round(pnl_oil, 2),
                "pnl_fx_eur": round(pnl_fx, 2),
                "pnl_equity_eur": round(pnl_eq, 2),
                "pnl_credit_eur": round(pnl_cs, 2),
            })

            factor_pnl["rates_parallel"] += pnl_rates
            factor_pnl["curve_twist"] += pnl_twist
            factor_pnl["inflation"] += pnl_infl
            factor_pnl["oil_energy"] += pnl_oil
            factor_pnl["fx_usd"] += pnl_fx
            factor_pnl["equity_beta"] += pnl_eq
            factor_pnl["credit_spread"] += pnl_cs

        asset_df = pd.DataFrame(pnl_records)
        total_pnl = sum(r["total_pnl_eur"] for r in pnl_records)
        stressed_total_mv = total_mv + total_pnl
        pnl_pct = (total_pnl / total_mv) * 100.0

        # 2. Covariance & Correlation Breakdown Stress
        # Base covariance
        cov_base = np.diag(base_vols) @ base_corr @ np.diag(base_vols)
        base_port_var = float(weights @ cov_base @ weights)
        base_port_vol = float(np.sqrt(max(1e-8, base_port_var)))

        # Stressed vols (scaled up by vol_surge_factor linked to lambda)
        surge = 1.0 + (scenario.vol_surge_factor - 1.0) * scenario.correlation_breakdown_lambda
        stressed_vols = base_vols * surge

        # Stressed correlation
        stressed_corr = self.stress_correlation_matrix(base_corr, scenario.correlation_breakdown_lambda)
        cov_stressed = np.diag(stressed_vols) @ stressed_corr @ np.diag(stressed_vols)
        stressed_port_var = float(weights @ cov_stressed @ weights)
        stressed_port_vol = float(np.sqrt(max(1e-8, stressed_port_var)))

        # Counterfactual: Stressed vols with UNCHANGED base correlation (isolates pure correlation effect)
        cov_vol_only = np.diag(stressed_vols) @ base_corr @ np.diag(stressed_vols)
        vol_only_port_vol = float(np.sqrt(max(1e-8, weights @ cov_vol_only @ weights)))
        diversification_loss = (stressed_port_vol - vol_only_port_vol) * 100.0

        # 3. VaR 99% 10-day (10-day scaling factor sqrt(10/252))
        z_99 = 2.3263
        t_10d = np.sqrt(10.0 / 252.0)
        base_var_99 = total_mv * base_port_vol * z_99 * t_10d
        stressed_var_99 = stressed_total_mv * stressed_port_vol * z_99 * t_10d

        # 4. Liquidity & Variation Margin Drain projection
        # Derivative/derivative-like margin calls jump proportionally to volatility surge and negative pnl
        margin_drain = abs(min(0.0, total_pnl)) * 0.25 + total_mv * (surge - 1.0) * 0.05

        names = [a.asset_id for a in assets]
        corr_df = pd.DataFrame(stressed_corr, index=names, columns=names).round(3)

        return MacroWarRoomResult(
            scenario_name=scenario.scenario_name,
            portfolio_initial_value_eur=round(total_mv, 2),
            portfolio_stressed_value_eur=round(stressed_total_mv, 2),
            portfolio_total_pnl_eur=round(total_pnl, 2),
            portfolio_total_pnl_pct=round(pnl_pct, 2),
            factor_pnl_attribution={k: round(v, 2) for k, v in factor_pnl.items()},
            base_portfolio_vol_pct=round(base_port_vol * 100.0, 2),
            stressed_portfolio_vol_pct=round(stressed_port_vol * 100.0, 2),
            diversification_loss_pct=round(diversification_loss, 2),
            base_var_99_10d_eur=round(base_var_99, 2),
            stressed_var_99_10d_eur=round(stressed_var_99, 2),
            liquidity_margin_drain_eur=round(margin_drain, 2),
            asset_pnl_breakdown_df=asset_df,
            stressed_correlation_matrix=corr_df,
        )


def compute_macro_war_room_stress(
    assets_data: Optional[List[Dict[str, Any]]] = None,
    scenario_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience functional API for Interactive Macro War Room & Correlation Breakdown.
    """
    # Sample default institutional balance sheet if none provided
    if not assets_data:
        assets = [
            AssetSensitivityProfile(
                asset_id="EQ_TECH",
                name="Global Tech & AI Equity",
                asset_class="EQUITY",
                market_value_eur=3_500_000.0,
                duration=0.0,
                equity_beta=1.35,
                fx_exposure=0.60,
                annual_vol_pct=22.0,
            ),
            AssetSensitivityProfile(
                asset_id="FI_SOV_10Y",
                name="Euro Sovereign Bonds 10Y",
                asset_class="FIXED_INCOME",
                market_value_eur=4_000_000.0,
                duration=8.5,
                convexity=80.0,
                equity_beta=0.0,
                fx_exposure=0.0,
                annual_vol_pct=6.5,
            ),
            AssetSensitivityProfile(
                asset_id="CR_IG_CORP",
                name="US Investment Grade Corporate",
                asset_class="CREDIT",
                market_value_eur=2_000_000.0,
                duration=6.0,
                convexity=45.0,
                credit_spread_duration=5.8,
                fx_exposure=1.0,
                annual_vol_pct=8.0,
            ),
            AssetSensitivityProfile(
                asset_id="COMM_ENERGY",
                name="Commodities & Energy Transition",
                asset_class="COMMODITY",
                market_value_eur=1_000_000.0,
                duration=0.0,
                commodity_beta=1.20,
                fx_exposure=0.80,
                annual_vol_pct=25.0,
            ),
            AssetSensitivityProfile(
                asset_id="RE_COMMERCIAL",
                name="European Prime Real Estate",
                asset_class="REAL_ESTATE",
                market_value_eur=2_500_000.0,
                duration=3.0,
                equity_beta=0.40,
                annual_vol_pct=11.0,
            ),
        ]
    else:
        assets = [
            AssetSensitivityProfile(
                asset_id=str(d.get("asset_id", f"A_{i}")),
                name=str(d.get("name", f"Asset {i}")),
                asset_class=str(d.get("asset_class", "EQUITY")),
                market_value_eur=float(d.get("market_value_eur", 100_000.0)),
                duration=float(d.get("duration", 0.0)),
                convexity=float(d.get("convexity", 0.0)),
                equity_beta=float(d.get("equity_beta", 1.0)),
                credit_spread_duration=float(d.get("credit_spread_duration", 0.0)),
                fx_exposure=float(d.get("fx_exposure", 0.0)),
                commodity_beta=float(d.get("commodity_beta", 0.0)),
                annual_vol_pct=float(d.get("annual_vol_pct", 15.0)),
            )
            for i, d in enumerate(assets_data)
        ]

    sc_dict = scenario_params or {}
    scenario = MacroShockScenario(
        scenario_name=str(sc_dict.get("scenario_name", "Global Stagflation & Correlation Shock")),
        parallel_rates_bps=float(sc_dict.get("parallel_rates_bps", 150.0)),
        slope_twist_bps=float(sc_dict.get("slope_twist_bps", -50.0)),
        inflation_shock_pct=float(sc_dict.get("inflation_shock_pct", 3.5)),
        oil_shock_pct=float(sc_dict.get("oil_shock_pct", 40.0)),
        fx_usd_pct=float(sc_dict.get("fx_usd_pct", 5.0)),
        equity_shock_pct=float(sc_dict.get("equity_shock_pct", -20.0)),
        credit_spread_widening_bps=float(sc_dict.get("credit_spread_widening_bps", 250.0)),
        correlation_breakdown_lambda=float(sc_dict.get("correlation_breakdown_lambda", 0.60)),
        vol_surge_factor=float(sc_dict.get("vol_surge_factor", 1.50)),
    )

    engine = MacroWarRoomEngine()
    res = engine.run_simulation(assets=assets, scenario=scenario)

    return {
        "scenario_name": res.scenario_name,
        "initial_value_eur": res.portfolio_initial_value_eur,
        "stressed_value_eur": res.portfolio_stressed_value_eur,
        "total_pnl_eur": res.portfolio_total_pnl_eur,
        "total_pnl_pct": res.portfolio_total_pnl_pct,
        "factor_attribution": res.factor_pnl_attribution,
        "base_vol_pct": res.base_portfolio_vol_pct,
        "stressed_vol_pct": res.stressed_portfolio_vol_pct,
        "diversification_loss_pct": res.diversification_loss_pct,
        "base_var_99_10d_eur": res.base_var_99_10d_eur,
        "stressed_var_99_10d_eur": res.stressed_var_99_10d_eur,
        "liquidity_margin_drain_eur": res.liquidity_margin_drain_eur,
        "assets_breakdown": res.asset_pnl_breakdown_df.to_dict(orient="records"),
        "stressed_correlation_matrix": res.stressed_correlation_matrix.to_dict(),
    }
