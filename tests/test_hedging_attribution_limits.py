"""
ARGUS — Risk Analytics Platform
Unit Tests for Hedging, Brinson Attribution, and Risk Limits Engines
"""

import pytest
import pandas as pd
import numpy as np

from core.hedging import compute_beta_neutral_hedge
from core.attribution import compute_brinson_attribution
from core.risk_limits import check_risk_limits


@pytest.fixture
def mock_results():
    positions_data = [
        {"ticker": "GOOGL", "qty_net": 28, "current_value": 7794.88, "unrealized_pnl_pct": 12.5, "sector": "Technology", "country": "USA"},
        {"ticker": "ISP.MI", "qty_net": 701, "current_value": 4402.98, "unrealized_pnl_pct": 8.0, "sector": "Financials", "country": "Italy"},
        {"ticker": "NOVO-B.CO", "qty_net": 96, "current_value": 4112.93, "unrealized_pnl_pct": 5.2, "sector": "Healthcare", "country": "Denmark"},
        {"ticker": "BABA", "qty_net": 45, "current_value": 4497.73, "unrealized_pnl_pct": -3.1, "sector": "Consumer Discretionary", "country": "China"},
    ]
    df_pos = pd.DataFrame(positions_data)
    return {
        "positions": df_pos,
        "portfolio_beta": 1.15,
        "var_95_hist": 0.025,
        "var_99_hist": 0.038,
        "cum_return_pct": 14.2,
        "benchmark_cum_return_pct": 10.0,
        "diversification_ratio": 1.35,
        "hhi": 0.12
    }


def test_hedging_engine(mock_results):
    res = compute_beta_neutral_hedge(mock_results, target_beta=0.0, hedge_ticker="SH")
    assert res["portfolio_value"] > 0
    assert res["current_beta"] == 1.15
    assert res["target_beta"] == 0.0
    assert res["hedge_value_eur"] > 0
    assert res["hedge_shares"] > 0
    assert res["instrument_ticker"] == "SH"


def test_brinson_attribution_engine(mock_results):
    attr = compute_brinson_attribution(mock_results)
    assert "summary" in attr
    assert "attribution_df" in attr
    df = attr["attribution_df"]
    assert not df.empty
    assert "allocation_effect_pct" in df.columns
    assert "selection_effect_pct" in df.columns
    assert "interaction_effect_pct" in df.columns
    assert attr["summary"]["portfolio_return_pct"] == 14.2


def test_risk_limits_engine(mock_results):
    limits = check_risk_limits(mock_results)
    assert "compliance_pct" in limits
    assert "evaluations" in limits
    assert limits["total_rules"] == 6
    assert limits["pass_count"] + limits["warning_count"] + limits["breach_count"] == 6
    assert isinstance(limits["evaluations"], pd.DataFrame)
