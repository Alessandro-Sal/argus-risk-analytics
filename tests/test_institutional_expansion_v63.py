# ============================================================
# tests/test_institutional_expansion_v63.py
# Unit tests for ARGUS v6.3.0 Expansion
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.private_debt_engine import (
    get_standard_private_debt_deals,
    compute_private_debt_waterfall_and_covenants
)
from core.execution_algo_engine import (
    compute_implementation_shortfall_and_execution_benchmarks
)
from core.cross_border_tax_engine import (
    get_international_tax_jurisdictions,
    compute_cross_border_wealth_tax_comparison
)
from core.hmm_regime_engine import (
    compute_hmm_market_regime_detection
)
from core.voice_advisor_engine import (
    generate_ai_voice_executive_briefing
)
from core.terminal_engine import get_terminal_engine
from core.fetcher import get_engine


def test_private_debt_waterfall_and_covenants():
    deals = get_standard_private_debt_deals()
    assert len(deals) >= 2

    res = compute_private_debt_waterfall_and_covenants(deal_data=deals[0], ebitda_stress_pct=-10.0)
    assert res["total_facility_eur"] > 0
    assert "credit_metrics" in res
    assert "leverage_net_debt_ebitda" in res["credit_metrics"]
    assert not res["tranches_df"].empty


def test_execution_algo_implementation_shortfall():
    res = compute_implementation_shortfall_and_execution_benchmarks(
        ticker="SWDA.MI",
        total_shares=5000,
        decision_price=100.0,
        side="BUY"
    )
    assert res["shares_count"] == 5000
    assert "perold_breakdown" in res
    assert res["perold_breakdown"]["total_shortfall_eur"] > 0
    assert len(res["strategies_comparison"]) == 4


def test_cross_border_tax_comparison():
    jurs = get_international_tax_jurisdictions()
    assert "IT_ORDINARY" in jurs
    assert "IT_NEO_RESIDENTI" in jurs
    assert "CH_ZUG" in jurs
    assert "UAE_DUBAI" in jurs

    res = compute_cross_border_wealth_tax_comparison(
        total_wealth_eur=10000000.0,
        annual_capital_gain_eur=400000.0,
        annual_foreign_income_eur=250000.0
    )
    assert res["simulated_wealth_eur"] == 10000000.0
    assert res["max_annual_tax_savings_eur"] > 0
    assert not res["comparison_df"].empty


def test_hmm_market_regime_detection():
    np.random.seed(42)
    fake_ret = pd.Series(np.random.normal(0.0005, 0.012, 252))
    res = compute_hmm_market_regime_detection(sr_returns=fake_ret, n_states=3)

    assert res["current_regime_id"] in (0, 1, 2)
    assert len(res["state_profiles"]) == 3
    assert "tactical_recommendation" in res
    assert res["transition_matrix_pct_df"].shape == (3, 3)


def test_voice_advisor_executive_briefing():
    engine = get_engine()
    res = generate_ai_voice_executive_briefing(engine, portfolio_id=1, client_name="Test FO")

    assert res["estimated_duration_seconds"] > 0
    assert len(res["dialogue_script"]) >= 4
    assert len(res["full_text_transcript"]) > 50


def test_v63_terminal_commands():
    term = get_terminal_engine()
    ctx = {
        "df_positions": pd.DataFrame([{"ticker": "SWDA.MI", "controvalore": 100000.0}]),
        "results": {"valore_totale": 100000.0}
    }

    # PDEBT
    r1 = term.execute_command("PDEBT", ctx)
    assert r1.status == "SUCCESS"
    assert "PRIVATE DEBT" in r1.output_text

    # ALGO EXEC
    r2 = term.execute_command("ALGO EXEC", ctx)
    assert r2.status == "SUCCESS"
    assert "IMPLEMENTATION SHORTFALL" in r2.output_text

    # GLOBAL TAX
    r3 = term.execute_command("GLOBAL TAX", ctx)
    assert r3.status == "SUCCESS"
    assert "CROSS-BORDER TAX" in r3.output_text

    # HMM
    r4 = term.execute_command("HMM", ctx)
    assert r4.status == "SUCCESS"
    assert "HIDDEN MARKOV" in r4.output_text

    # VOICE BRIEF
    r5 = term.execute_command("VOICE BRIEF", ctx)
    assert r5.status == "SUCCESS"
    assert "VOICE EXECUTIVE" in r5.output_text
