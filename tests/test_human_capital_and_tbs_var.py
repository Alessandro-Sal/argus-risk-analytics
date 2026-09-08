"""
tests/test_human_capital_and_tbs_var.py
Unit tests for HumanCapitalEngine and HolisticBalanceSheetEngine (TBS-VaR).
"""

import pytest
import numpy as np
from core.wealth.human_capital_engine import (
    LaborIncomeProfile,
    TotalBalanceSheetState,
    HumanCapitalEngine,
    HolisticBalanceSheetEngine,
)


def test_human_capital_engine_valuation():
    engine = HumanCapitalEngine(base_risk_free_rate=0.03, equity_risk_premium=0.05)
    
    # Profile 1: Tech worker with high beta
    profile_tech = LaborIncomeProfile(
        current_annual_net_income=60000.0,
        years_to_retirement=25,
        income_growth_rate=0.02,
        industry_sector="Technology",
        sector_beta=1.2,
        unemployment_risk_premium=0.015,
    )
    res_tech = engine.compute_human_capital_valuation(profile_tech)
    
    assert res_tech["human_capital_pv"] > 0
    assert res_tech["quasi_equity_weight"] == pytest.approx(0.9, abs=1e-3)
    assert res_tech["quasi_bond_weight"] == pytest.approx(0.1, abs=1e-3)
    assert len(res_tech["annual_cashflows_projection"]) == 25
    assert res_tech["quasi_equity_amount"] + res_tech["quasi_bond_amount"] == pytest.approx(res_tech["human_capital_pv"], abs=1e-3)

    # Profile 2: Civil servant (tenured government employee)
    profile_gov = LaborIncomeProfile(
        current_annual_net_income=35000.0,
        years_to_retirement=20,
        income_growth_rate=0.01,
        industry_sector="Public Sector",
        sector_beta=0.05,
        unemployment_risk_premium=0.005,
    )
    res_gov = engine.compute_human_capital_valuation(profile_gov)
    
    assert res_gov["human_capital_pv"] > 0
    # beta=0.05 -> 0.05 * 0.75 = 0.0375 quasi equity, 0.9625 quasi bond
    assert res_gov["quasi_bond_weight"] > 0.95
    assert res_gov["quasi_equity_weight"] < 0.05


def test_human_capital_engine_zero_years():
    engine = HumanCapitalEngine()
    profile_retired = LaborIncomeProfile(
        current_annual_net_income=50000.0,
        years_to_retirement=0,
        income_growth_rate=0.0,
        industry_sector="Retired",
        sector_beta=0.0,
    )
    res = engine.compute_human_capital_valuation(profile_retired)
    assert res["human_capital_pv"] == 0.0
    assert res["quasi_equity_amount"] == 0.0
    assert res["quasi_bond_amount"] == 0.0


def test_holistic_balance_sheet_var_calculation():
    holistic_engine = HolisticBalanceSheetEngine(risk_free_rate=0.03, equity_risk_premium=0.05)
    
    profile = LaborIncomeProfile(
        current_annual_net_income=50000.0,
        years_to_retirement=20,
        income_growth_rate=0.02,
        industry_sector="Technology",
        sector_beta=1.1,
    )

    weights = np.array([0.6, 0.4])
    cov_matrix = np.array([
        [0.0004, 0.0001],
        [0.0001, 0.0002]
    ])

    state_variable = TotalBalanceSheetState(
        liquid_portfolio_value=200000.0,
        liquid_portfolio_weights=weights,
        liquid_covariance_matrix=cov_matrix,
        real_estate_value=350000.0,
        real_estate_volatility=0.08,
        real_estate_beta=0.3,
        mortgage_debt_outstanding=150000.0,
        mortgage_duration=8.0,
        is_variable_rate=True,
        annual_unavoidable_expenses=30000.0,
        labor_profile=profile,
    )

    res_var = holistic_engine.compute_total_balance_sheet_var(state_variable, confidence=0.95, horizon_years=1.0)

    assert "total_net_worth_eur" in res_var
    assert "tbs_var_eur" in res_var
    assert "tbs_cvar_eur" in res_var
    assert res_var["total_assets_with_hc_eur"] > 200000.0 + 350000.0
    assert res_var["debt_stress_component_eur"] > 0.0  # 150000 * 8.0 * 0.02 = 24000
    assert res_var["debt_stress_component_eur"] == pytest.approx(24000.0, abs=1e-2)
    assert res_var["tbs_cvar_eur"] > res_var["tbs_var_eur"]
    assert res_var["emergency_runway_months"] > 0
    assert res_var["weights_breakdown"]["human_capital_pct"] > 0
    assert res_var["sector_hedging_needed"] is True
    assert res_var["recommended_sector_underweight_eur"] > 0


def test_holistic_balance_sheet_fixed_debt():
    holistic_engine = HolisticBalanceSheetEngine()
    profile = LaborIncomeProfile(
        current_annual_net_income=40000.0,
        years_to_retirement=15,
        income_growth_rate=0.01,
        industry_sector="Healthcare",
        sector_beta=0.3,
    )

    state_fixed = TotalBalanceSheetState(
        liquid_portfolio_value=100000.0,
        liquid_portfolio_weights=np.array([1.0]),
        liquid_covariance_matrix=np.array([[0.0002]]),
        real_estate_value=250000.0,
        real_estate_volatility=0.06,
        real_estate_beta=0.2,
        mortgage_debt_outstanding=80000.0,
        mortgage_duration=5.0,
        is_variable_rate=False,  # Fixed rate
        annual_unavoidable_expenses=24000.0,
        labor_profile=profile,
    )

    res_fixed = holistic_engine.compute_total_balance_sheet_var(state_fixed)
    assert res_fixed["debt_stress_component_eur"] == 0.0
    assert res_fixed["tbs_var_eur"] > 0.0
    # Beta is 0.3, so sector_hedging_needed should be False
    assert res_fixed["sector_hedging_needed"] is False
    assert res_fixed["recommended_sector_underweight_eur"] == 0.0
