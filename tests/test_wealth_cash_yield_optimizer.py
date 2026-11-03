"""
ARGUS Wealth - Unit Tests for Cash Yield Optimizer & Liquidity Opportunity Cost Engine
======================================================================================
"""

import pytest
from sqlalchemy import create_engine

from core.wealth.cash_yield_optimizer import (
    BENCHMARKS,
    compute_cash_yield_optimization,
)
from core.wealth.wealth_db import (
    init_wealth_db,
    save_wealth_account,
)


@pytest.fixture
def test_db_engine():
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)
    return engine


def test_benchmarks_integrity():
    assert "bot_12m" in BENCHMARKS
    assert "etf_monetary_xeon" in BENCHMARKS
    assert "bce_deposit_rate" in BENCHMARKS
    assert BENCHMARKS["bot_12m"]["tax_rate_pct"] == 12.5
    assert BENCHMARKS["bot_12m"]["net_yield_pct"] > 2.5


def test_cash_yield_optimization_with_mock_accounts(test_db_engine):
    # Setup accounts
    save_wealth_account(test_db_engine, {
        "portfolio_id": 1,
        "name": "Conto Principale Intesa",
        "account_type": "checking",
        "balance": 25000.0,
        "currency": "EUR",
        "institution": "Intesa Sanpaolo",
        "interest_rate": 0.05,
    })
    save_wealth_account(test_db_engine, {
        "portfolio_id": 1,
        "name": "Conto Deposito Libero",
        "account_type": "savings",
        "balance": 15000.0,
        "currency": "EUR",
        "institution": "Banca Progetto",
        "interest_rate": 1.50,
    })

    res = compute_cash_yield_optimization(
        test_db_engine,
        portfolio_id=1,
        emergency_months=6,
        custom_monthly_expenses=2000.0,
    )

    assert res["total_liquid_cash_eur"] == 40000.0
    assert res["monthly_expenses_eur"] == 2000.0
    assert res["runway_months"] == 20.0

    # Tranches:
    # Op: 2 months = 4.000€
    # Em: 4 months = 8.000€
    # Excess: 40.000 - 12.000 = 28.000€
    assert res["tranches"]["operational"] == 4000.0
    assert res["tranches"]["emergency"] == 8000.0
    assert res["tranches"]["excess"] == 28000.0

    # Opportunity cost should be positive and significant
    assert res["annual_opportunity_cost_eur"] > 500.0
    assert res["five_year_projected_loss_eur"] > 2500.0
    assert len(res["recommendations"]) == 3
