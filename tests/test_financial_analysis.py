"""
ARGUS — Risk Analytics Platform
PyTest Suite: Financial Statement Analysis & Corporate Solvency Engine
"""

import pytest
import numpy as np
from core.financial_analysis import (
    compute_altman_z_score,
    compute_dupont_analysis,
    compute_financial_ratios,
    generate_company_financial_statement_analysis
)

def test_altman_z_score_safe_zone():
    res = compute_altman_z_score(
        working_capital=50000000.0,
        retained_earnings=100000000.0,
        ebit=40000000.0,
        market_cap_or_equity=300000000.0,
        sales=250000000.0,
        total_assets=200000000.0,
        total_liabilities=50000000.0,
        is_manufacturing=True
    )
    assert res["z_score"] > 2.99
    assert res["zone"] == "Safe Zone"
    assert "🟢" in res["zone_icon"]


def test_altman_z_score_distress_zone():
    res = compute_altman_z_score(
        working_capital=-20000000.0,
        retained_earnings=-50000000.0,
        ebit=-10000000.0,
        market_cap_or_equity=10000000.0,
        sales=30000000.0,
        total_assets=100000000.0,
        total_liabilities=90000000.0,
        is_manufacturing=True
    )
    assert res["z_score"] < 1.81
    assert res["zone"] == "Distress Zone"
    assert "🔴" in res["zone_icon"]


def test_dupont_analysis_3factor():
    res = compute_dupont_analysis(
        net_income=15000000.0,
        sales=100000000.0,
        total_assets=200000000.0,
        total_equity=80000000.0
    )
    # ROE = 15M / 80M = 18.75%
    assert pytest.approx(res["roe_pct"], 0.01) == 18.75
    assert pytest.approx(res["profit_margin_pct"], 0.01) == 15.0
    assert pytest.approx(res["asset_turnover"], 0.01) == 0.50
    assert pytest.approx(res["equity_multiplier"], 0.01) == 2.50


def test_financial_ratios_math():
    ratios = compute_financial_ratios(
        current_assets=500000.0,
        current_liabilities=250000.0,
        inventory=100000.0,
        cash=150000.0,
        total_debt=400000.0,
        total_equity=600000.0,
        ebit=120000.0,
        interest_expense=20000.0,
        ebitda=150000.0,
        net_income=80000.0,
        sales=1000000.0,
        total_assets=1000000.0
    )
    assert ratios["liquidity"]["current_ratio"] == 2.0
    assert ratios["liquidity"]["quick_ratio"] == 1.6
    assert ratios["solvency"]["debt_to_equity"] == 0.67
    assert ratios["solvency"]["interest_coverage"] == 6.0
    assert ratios["profitability"]["roe_pct"] == 13.33


from unittest.mock import patch, MagicMock


def test_generate_company_financial_statement_analysis():
    with patch("yfinance.Ticker") as mock_ticker:
        mock_instance = MagicMock()
        mock_instance.financials = None
        mock_instance.balance_sheet = None
        mock_instance.cashflow = None
        mock_instance.info = {}
        mock_ticker.return_value = mock_instance

        res = generate_company_financial_statement_analysis(
            ticker="AAPL",
            company_name="Apple Inc.",
            market_cap=3000000000000.0,
            roe_pct=150.0
        )
        assert res["ticker"] == "AAPL"
        assert "altman_z_score" in res
        assert "dupont_analysis" in res
        assert "ratios" in res


def test_compare_multiple_companies():
    from core.financial_analysis import compare_multiple_companies
    with patch("yfinance.Ticker") as mock_ticker:
        mock_instance = MagicMock()
        mock_instance.info = {"longName": "Alphabet Inc.", "marketCap": 2000000000000.0, "trailingPE": 25.0, "roe": 0.25}
        mock_instance.financials = None
        mock_ticker.return_value = mock_instance
        
        comp = compare_multiple_companies(["GOOGL", "AAPL", "MSFT"])
        assert not comp["zscore_table"].empty
        assert not comp["dupont_table"].empty
        assert not comp["ratios_table"].empty
        assert len(comp["zscore_table"]) == 3
        assert "GOOGL" in comp["zscore_table"]["Ticker"].values


def test_compute_dcf_monte_carlo_valuation():
    from core.financial_analysis import compute_dcf_monte_carlo_valuation
    res = compute_dcf_monte_carlo_valuation(
        fcf_base=15000000000.0,
        current_price=150.0,
        shares_outstanding=12000000000.0,
        growth_rate_mean=0.08,
        wacc_mean=0.085,
        n_simulations=500
    )
    assert res["fair_value_median"] > 0
    assert "recommendation" in res
    assert len(res["simulated_fair_values"]) == 500
    assert 0 <= res["prob_undervalued_pct"] <= 100


def test_piotroski_wacc_multiples():
    from core.financial_analysis import compute_piotroski_f_score, compute_wacc_estimation, compute_valuation_multiples_matrix
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_instance = MagicMock()
        mock_instance.info = {
            "longName": "Alphabet Inc.",
            "marketCap": 2000000000000.0,
            "totalDebt": 30000000000.0,
            "beta": 1.05,
            "trailingPE": 24.5,
            "forwardPE": 20.1,
            "pegRatio": 1.2
        }
        mock_instance.financials = None
        mock_instance.cashflow = None
        mock_instance.balance_sheet = None
        mock_ticker.return_value = mock_instance

        f_res = compute_piotroski_f_score("GOOGL")
        assert 0 <= f_res["score"] <= 9
        assert not f_res["details_df"].empty

        w_res = compute_wacc_estimation("GOOGL")
        assert w_res["wacc_pct"] > 0
        assert w_res["cost_of_equity_pct"] > 0

        m_res = compute_valuation_multiples_matrix("GOOGL")
        assert not m_res["multiples_table"].empty


def test_novo_nordisk_target_price_currency_conversion():
    # Novo Nordisk (NOVO-B.CO) price in EUR ~40.44, target mean in DKK ~317.20
    last_price_eur = 40.44
    target_price_dkk = 317.20
    fx_rate_dkk_to_eur = 1.0 / 7.46
    
    target_price_eur = target_price_dkk * fx_rate_dkk_to_eur
    upside_pct = (target_price_eur / last_price_eur - 1) * 100.0
    
    assert 40.0 < target_price_eur < 45.0
    assert -10.0 < upside_pct < 20.0  # Real upside is ~+5.14%, NOT +684%!


