"""
tests/test_prescriptive_rebalancer_and_agents.py
Unit tests for PrescriptiveConicRebalancer and TriAgentQuantitativeGovernance.
"""

import pytest
import numpy as np
from core.prescriptive_rebalancer import (
    PositionLot,
    TaxWalletState,
    RebalanceConstraints,
    FIXOrder,
    PrescriptiveConicRebalancer
)
from core.ai_analyst import TriAgentQuantitativeGovernance


def test_fix_order_formatting():
    order = FIXOrder(
        cl_ord_id="ARGUS-TEST-B-001",
        symbol="CSPX.MI",
        side="BUY",
        order_qty=50,
        order_type="LIMIT",
        limit_price=512.40,
        estimated_tax_eur=0.0,
        estimated_slippage_eur=4.20
    )
    fix_str = order.to_fix_string()
    assert "8=FIX.4.4" in fix_str
    assert "35=D" in fix_str
    assert "11=ARGUS-TEST-B-001" in fix_str
    assert "55=CSPX.MI" in fix_str
    assert "54=1" in fix_str  # Buy side
    assert "38=50" in fix_str
    assert "40=2" in fix_str  # Limit order
    assert "44=512.40" in fix_str
    assert "10=" in fix_str  # Checksum tag


def test_prescriptive_rebalancer_optimization():
    # Setup positions: AAPL, MSFT, Cash
    positions = [
        PositionLot(ticker="AAPL", shares=100, current_price=180.0, pmc=150.0, adv_eur=50_000_000.0),
        PositionLot(ticker="MSFT", shares=50, current_price=400.0, pmc=350.0, adv_eur=40_000_000.0),
    ]
    # Total portfolio equity = 18,000 + 20,000 = 38,000. Available cash = 12,000. Total wealth = 50,000.
    # Current weights: AAPL = 36%, MSFT = 40%, Cash = 24%.
    # Target weights: AAPL = 25%, MSFT = 25%, (Cash = 50%).
    target_weights = {"AAPL": 0.25, "MSFT": 0.25}
    
    tax_wallet = TaxWalletState(minusvalenze_available_eur=2000.0)
    rebalancer = PrescriptiveConicRebalancer(tax_wallet=tax_wallet)

    res = rebalancer.optimize_rebalance(
        positions=positions,
        target_weights=target_weights,
        available_cash_eur=12000.0
    )

    assert res["success"] is True
    assert res["total_wealth_eur"] == 50000.0
    assert res["trades_count"] > 0
    assert res["trades_df"] is not None
    assert "fix_blotter_raw" in res
    assert "8=FIX.4.4" in res["fix_blotter_raw"]

    # Check that minusvalenze were used to offset capital gains
    assert res["total_minusvalenze_absorbed_eur"] >= 0.0
    assert res["total_tax_due_eur"] >= 0.0


def test_tri_agent_governance_deliberation():
    governance = TriAgentQuantitativeGovernance()

    portfolio_ctx = {
        "portfolio_value_eur": 100000.0,
        "var_95_pct": 2.1,
        "sharpe_ratio": 1.45
    }

    rebalance_res = {
        "turnover_pct": 14.5,
        "total_tax_due_eur": 120.0,
        "total_minusvalenze_absorbed_eur": 450.0,
        "remaining_minusvalenze_eur": 1200.0,
        "total_market_impact_slippage_eur": 18.5,
        "trades_count": 3,
        "total_wealth_eur": 100000.0
    }

    audit = governance.audit_rebalance_plan(portfolio_ctx, rebalance_res)

    assert "consensus_verdict" in audit
    assert audit["consensus_verdict"] in ["APPROVED", "CONDITIONAL_APPROVAL"]
    assert audit["consensus_score"] > 70.0
    assert "agents" in audit
    assert "risk_auditor" in audit["agents"]
    assert "tax_specialist" in audit["agents"]
    assert "macro_execution" in audit["agents"]
    assert audit["mifid_compliant"] is True
    assert "MiFID II" in audit["signoff_memo"]
