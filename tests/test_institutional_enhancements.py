# ============================================================
# tests/test_institutional_enhancements.py
# ARGUS — Unit Tests for Institutional Front-Office & Wealth Enhancements
# ============================================================

import numpy as np
import pandas as pd
import pytest

from core.fixed_income import compute_portfolio_fixed_income_analytics
from core.risk_engine import (
    compute_carhart_4factor_exposures,
    compute_fama_french_5factor_exposures,
    compute_fama_french_exposures,
    compute_portfolio_liquidity_risk,
)
from core.tax_engine import compute_tax_loss_harvesting_opportunities
from core.wealth.tbs_monte_carlo import compute_stochastic_cash_flow_decumulation

# ────────────────────────────────────────────────────────────
# 1. REAL FAMA-FRENCH & CARHART MULTIFACTOR EXPOSURES
# ────────────────────────────────────────────────────────────


def test_fama_french_3factor_exposures_integration():
    """Verifica che il modello Fama-French a 3 fattori utilizzi fattori reali e restituisca t-stat ed R2."""
    dates = pd.date_range("2024-01-01", periods=120, freq="B")
    np.random.seed(42)
    sr_returns = pd.Series(np.random.normal(0.0004, 0.012, 120), index=dates)

    res = compute_fama_french_exposures(sr_returns)
    assert "alpha" in res
    assert "beta_mkt" in res
    assert "beta_smb" in res
    assert "beta_hml" in res
    assert "r_squared" in res
    assert "adj_r_squared" in res
    assert "alpha_t_stat" in res
    assert "systematic_risk_pct" in res
    assert isinstance(res["df_factors"], pd.DataFrame)
    assert len(res["df_factors"]) == 3
    assert set(res["df_factors"]["factor"]) == {"Mkt-RF", "SMB", "HML"}


def test_carhart_4factor_and_5factor_exposures():
    """Verifica i modelli Carhart a 4 fattori e Fama-French a 5 fattori + Momentum."""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(101)
    sr_returns = pd.Series(np.random.normal(0.0005, 0.015, 100), index=dates)

    res_4f = compute_carhart_4factor_exposures(sr_returns)
    assert "beta_wml" in res_4f
    assert len(res_4f["df_factors"]) == 4

    res_5f = compute_fama_french_5factor_exposures(sr_returns)
    assert "beta_rmw" in res_5f
    assert "beta_cma" in res_5f
    assert "beta_mom" in res_5f
    assert len(res_5f["df_factors"]) == 6


# ────────────────────────────────────────────────────────────
# 2. PORTFOLIO FIXED INCOME & ALM ANALYTICS ENGINE
# ────────────────────────────────────────────────────────────


def test_portfolio_fixed_income_analytics_with_bonds():
    """Verifica l'aggregazione di Duration, DV01 e scenari di rotazione curva per portafogli obbligazionari."""
    df_pos = pd.DataFrame([
        {
            "ticker": "BTP-10Y",
            "name": "BTP 3.85% 2034",
            "asset_class": "Bond",
            "current_value": 50000.0,
            "face_value": 100.0,
            "coupon_rate": 0.0385,
            "maturity_years": 8.5,
            "market_price": 101.20,
        },
        {
            "ticker": "AGG",
            "name": "iShares Core US Aggregate Bond",
            "asset_class": "ETF",
            "current_value": 30000.0,
        },
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "asset_class": "Equity",
            "current_value": 20000.0,
        },
    ])

    res = compute_portfolio_fixed_income_analytics(df_pos)
    assert res["has_fixed_income"] is True
    assert res["total_portfolio_value"] == 100000.0
    assert res["fixed_income_value"] == 80000.0
    assert res["fixed_income_weight_pct"] == 80.0
    assert res["weighted_mod_duration"] > 0.0
    assert res["portfolio_dv01"] > 0.0
    assert "Bull_Steepener" in res["curve_stress_scenarios"]
    assert "Parallel_+100bps" in res["curve_stress_scenarios"]
    assert len(res["fi_positions_breakdown"]) == 2


def test_portfolio_fixed_income_empty_or_equity_only():
    """Verifica il fallback per portafogli senza posizioni a reddito fisso."""
    df_pos = pd.DataFrame([
        {"ticker": "NVDA", "name": "Nvidia Corp", "asset_class": "Equity", "current_value": 50000.0},
        {"ticker": "MSFT", "name": "Microsoft", "asset_class": "Equity", "current_value": 50000.0},
    ])

    res = compute_portfolio_fixed_income_analytics(df_pos)
    assert res["has_fixed_income"] is False
    assert res["portfolio_dv01"] == 0.0
    assert res["weighted_mod_duration"] == 0.0


# ────────────────────────────────────────────────────────────
# 3. ENDOGENOUS LIQUIDITY RISK & DAYS TO LIQUIDATE (DTL)
# ────────────────────────────────────────────────────────────


def test_portfolio_liquidity_risk_dtl_and_lvar():
    """Verifica il calcolo di DTL, Amihud ratio, Liquidity Tiers e L-VaR endogeno."""
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "name": "Apple Inc", "current_value": 80000.0},
        {"ticker": "SMALL-ILLIQUID", "name": "Small Illiquid Asset", "current_value": 20000.0},
    ])

    res = compute_portfolio_liquidity_risk(df_pos, participation_rate=0.10, portfolio_var_99_pct=3.0)
    assert res["total_portfolio_value"] == 100000.0
    assert res["weighted_dtl_days"] > 0.0
    assert res["max_dtl_days"] > 0.0
    assert "liquidity_tiers_pct" in res
    assert res["endogenous_lvar_99_eur"] >= res["unadjusted_var_99_eur"]
    assert len(res["positions_liquidity_breakdown"]) == 2
    assert "amihud_illiquidity_ratio" in res["positions_liquidity_breakdown"][0]


# ────────────────────────────────────────────────────────────
# 4. PROACTIVE TAX-LOSS HARVESTING & MINUSVALENZE OPTIMIZER
# ────────────────────────────────────────────────────────────


def test_tax_loss_harvesting_opportunities():
    """Verifica lo screener delle perdite latenti, calcolo tax alpha e assegnazione proxy sostitutivi."""
    df_pos = pd.DataFrame([
        {
            "ticker": "SWDA.MI",
            "name": "iShares Core MSCI World",
            "current_value": 30000.0,
            "current_price": 85.0,
            "avg_cost": 95.0,
            "quantity": 350.0,
            "asset_class": "ETF",
        },
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "current_value": 25000.0,
            "current_price": 220.0,
            "avg_cost": 180.0,
            "quantity": 113.6,
            "asset_class": "Equity",
        },
    ])

    tax_ledger = {"minusvalenze_per_anno": {2022: 1500.0, 2023: 500.0}}
    res = compute_tax_loss_harvesting_opportunities(df_pos, tax_ledger=tax_ledger, current_year=2026)

    assert res["has_harvesting_opportunities"] is True
    assert res["count_loss_positions"] == 1
    assert res["total_harvestable_losses_eur"] > 0.0
    assert res["total_potential_tax_savings_eur"] > 0.0
    assert res["opportunities"][0]["suggested_substitute_ticker"] == "LCWD.MI"
    assert res["opportunities"][0]["substitute_correlation"] >= 0.98


# ────────────────────────────────────────────────────────────
# 5. STOCHASTIC CASH FLOW & WEALTH DECUMULATION (TBS-MC)
# ────────────────────────────────────────────────────────────


def test_stochastic_cash_flow_decumulation():
    """Verifica la simulazione Monte Carlo su solvibilità a ciclo di vita e percentili patrimoniali."""
    res = compute_stochastic_cash_flow_decumulation(
        initial_liquid_wealth=150000.0,
        annual_income=60000.0,
        annual_expenses=32000.0,
        current_age=40,
        retirement_age=67,
        terminal_age=85,
        num_simulations=500,
        random_seed=42,
    )

    assert "total_ruin_probability_pct" in res
    assert "point_of_maximum_fragility_age" in res
    assert "recommended_annual_spending_eur" in res
    assert isinstance(res["timeline_df"], pd.DataFrame)
    assert len(res["timeline_df"]) == (85 - 40 + 1)
    assert "net_worth_p50" in res["timeline_df"].columns
    assert "net_worth_p10" in res["timeline_df"].columns
    assert "net_worth_p90" in res["timeline_df"].columns
