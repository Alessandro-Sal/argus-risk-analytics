# ==============================================================================
# tests/test_advanced_institutional_suite.py
# ARGUS — Unit tests for Neural Advisor, Asset Protection, Glide Path & Tax Rebalancer
# ==============================================================================

import pytest
import pandas as pd
from core.wealth.neural_advisor_engine import NeuralWealthAdvisor
from core.wealth.asset_protection_engine import AssetProtectionEngine
from core.wealth.glidepath_engine import DynamicGlidePathEngine, LifeGoal
from core.tax_aware_rebalancer import TaxAwarePortfolioRebalancer, FrictionConfig


def test_neural_advisor_scenario_evaluation():
    mock_summary = {
        "total_net_worth": 600000.0,
        "liquid_cash": 60000.0,
        "financial_investments": 300000.0,
        "real_estate_total": 200000.0,
        "physical_assets": 40000.0,
        "pension_total": 50000.0,
        "total_liabilities": 50000.0,
        "wealth_health_score": 88.0,
        "runway_months": 12.0
    }

    # Query 1: Fisco
    res_tax = NeuralWealthAdvisor.evaluate_scenario_query("ottimizza zainetto fiscale", mock_summary)
    assert res_tax["result_type"] == "TAX_OPTIMIZATION"
    assert len(res_tax["action_plan"]) > 0

    # Query 2: Real estate
    res_re = NeuralWealthAdvisor.evaluate_scenario_query("compra casa con mutuo", mock_summary)
    assert res_re["result_type"] == "REAL_ESTATE_PURCHASE"
    assert res_re["projected_nw"] > 0

    # Memo generation
    memo_md = NeuralWealthAdvisor.generate_executive_action_memo(mock_summary, [res_tax, res_re])
    assert "EXECUTIVE WEALTH ADVISORY MEMO" in memo_md
    assert "Diagnostica" in memo_md


def test_asset_protection_engine():
    mock_summary = {
        "total_net_worth": 1200000.0,
        "real_estate_total": 600000.0,
        "financial_investments": 500000.0,
        "physical_assets": 100000.0
    }
    res = AssetProtectionEngine.evaluate_protection_matrix(mock_summary)
    assert "fondo_patrimoniale" in res
    assert "trust" in res
    assert "societa_semplice" in res
    assert res["trust"].protection_score >= 90.0
    assert not res["comparison_df"].empty
    assert res["estimated_annual_pex_savings"] >= 0.0


def test_dynamic_glidepath_engine():
    goal = LifeGoal(
        goal_id="g1",
        name="Università Figli",
        target_amount=100000.0,
        horizon_years=10,
        initial_capital=20000.0,
        monthly_contribution=500.0
    )
    res = DynamicGlidePathEngine.compute_goal_glide_path(goal)
    assert res["success_probability_pct"] >= 50.0
    assert res["expected_final_value"] > goal.initial_capital
    assert res["plot_figure"] is not None
    assert len(res["glide_path_df"]) == 11


def test_tax_aware_rebalancer():
    mock_holdings = pd.DataFrame([
        {"ticker": "SWDA.MI", "market_value": 70000.0},
        {"ticker": "EIMI.MI", "market_value": 10000.0},
        {"ticker": "XEON.DE", "market_value": 20000.0}
    ])
    target_weights = {
        "SWDA.MI": 0.60,  # Riduzione da 70k a 60k
        "EIMI.MI": 0.20,  # Incremento da 10k a 20k
        "XEON.DE": 0.20   # Invariato a 20k
    }
    total_val = 100000.0

    # 1. Full Rebalance
    full_res = TaxAwarePortfolioRebalancer.compute_full_rebalance_plan(
        mock_holdings, target_weights, total_val, existing_minusvalenze=1000.0
    )
    assert not full_res["trade_execution_list_df"].empty
    assert full_res["gross_turnover_eur"] > 0
    assert full_res["total_commissions_eur"] > 0

    # 2. Zero-Tax Cashflow Rebalance
    cf_res = TaxAwarePortfolioRebalancer.compute_zero_tax_cashflow_rebalance(
        mock_holdings, target_weights, total_val, monthly_inflow_eur=1500.0
    )
    assert not cf_res["cashflow_plan_df"].empty
    assert cf_res["months_to_full_alignment"] > 0
