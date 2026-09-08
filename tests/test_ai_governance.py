"""
Unit tests for AI Governance, MiFID II Guardrails, Numerical Grounding and Dynamic Voice Engine.
"""

import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

from core.ai_analyst import (
    MIFID_II_DISCLAIMER,
    UNIFIED_MIFID_SYSTEM_PROMPT,
    _extract_portfolio_summary_context,
    _generate_deterministic_memorandum,
    generate_portfolio_narrative_memorandum,
    query_argus_assistant,
    verify_metric_grounding
)
from core.sec_rag_engine import (
    chunk_financial_section,
    expand_query_with_financial_lexicon,
    index_ticker_sec_filings,
    query_sec_filings_rag
)
from core.voice_advisor_engine import generate_ai_voice_executive_briefing
from core.wealth.neural_advisor_engine import NeuralWealthAdvisor
from core.wealth.wealth_db import init_wealth_db, save_wealth_account


@pytest.fixture
def dummy_results_with_wealth():
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    np.random.seed(42)
    r1 = np.random.normal(0.001, 0.015, 100)
    df_ret = pd.DataFrame({"AAPL": r1}, index=dates)

    positions = [
        {"ticker": "AAPL", "market_value": 100000.0, "weight": 1.0, "pnl_pct": 0.15, "shares": 500}
    ]
    metrics = {
        "portfolio_value": 100000.0,
        "cagr": 0.12,
        "total_return": 0.20,
        "volatility": 0.15,
        "sharpe_ratio": 1.25,
        "sortino_ratio": 1.50,
        "max_drawdown": 0.09,
        "var_95": 0.019,
        "var_cf_95": 0.019,
        "cvar_95": 0.028,
        "beta": 1.02,
        "diversification_ratio": 1.0,
        "hhi": 1.0
    }
    return {
        "portfolio_value": 100000.0,
        "metrics": metrics,
        "positions": positions,
        "returns": df_ret,
        "benchmark": "SPY",
        "market_regime": {"current_regime": "Bull Low-Vol"},
        "advisor_score": 85,
        "wealth_context": {
            "total_net_worth": 250000.0,
            "liquid_cash": 35000.0,
            "runway_months": 11.5,
            "pension_total": 45000.0,
            "real_estate_equity": 120000.0,
            "tax_loss_harvestable": 3200.0
        }
    }


def test_mifid_disclaimer_presence_in_all_memorandums(dummy_results_with_wealth):
    # 1. Deterministic Memorandum
    ctx = _extract_portfolio_summary_context(dummy_results_with_wealth)
    memo = _generate_deterministic_memorandum(ctx)
    assert "MiFID II" in memo["full_text"]
    assert "CONSOB" in memo["full_text"]

    # 2. Narrative Memorandum Offline
    narrative = generate_portfolio_narrative_memorandum(dummy_results_with_wealth, provider="offline")
    assert "MiFID II" in narrative["full_text"]

    # 3. Copilot Assistant Query
    ans = query_argus_assistant("Qual è il mio VaR?", dummy_results_with_wealth, provider="offline")
    assert "MiFID II" in ans
    assert "CONSOB" in ans

    # 4. Neural Wealth Advisor Memo
    summary_data = {
        "total_net_worth": 250000.0,
        "liquid_cash": 35000.0,
        "runway_months": 11.5,
        "wealth_health_score": 85.0
    }
    sc_res = NeuralWealthAdvisor.evaluate_scenario_query("diagnosi", summary_data)
    action_memo = NeuralWealthAdvisor.generate_executive_action_memo(summary_data, [sc_res])
    assert "MiFID II" in action_memo


def test_wealth_context_enrichment(dummy_results_with_wealth):
    ctx = _extract_portfolio_summary_context(dummy_results_with_wealth)
    assert ctx["net_worth_eur"] == 250000.0
    assert ctx["liquid_cash_eur"] == 35000.0
    assert ctx["runway_months"] == 11.5
    assert ctx["pension_val_eur"] == 45000.0
    assert ctx["tax_loss_harvestable_eur"] == 3200.0


def test_numerical_grounding_verification(dummy_results_with_wealth):
    ctx = _extract_portfolio_summary_context(dummy_results_with_wealth)
    text = f"Il portafoglio ha un valore di € {ctx['portfolio_value_eur']} con Sharpe {ctx['sharpe_ratio']} e disclaimer MiFID II."
    grounding = verify_metric_grounding(text, ctx)
    assert grounding["mifid_disclaimer_present"] is True
    assert grounding["context_portfolio_value"] == 100000.0
    assert grounding["grounding_passed"] is True


def test_sec_rag_semantic_chunking():
    # Long text with 6 sentences
    text = (
        "First sentence on revenue growth. "
        "Second sentence on operating margin expansion. "
        "Third sentence on international sales performance. "
        "Fourth sentence on semiconductor supply chain constraints. "
        "Fifth sentence on long-term unsecured note maturities. "
        "Sixth sentence on capital expenditure outlook."
    )
    chunks = chunk_financial_section(text, "TEST", "ITEM_1", "Item 1: Overview")
    # With 6 sentences and window=3, step=2:
    # chunk 0: [0, 1, 2]
    # chunk 1: [2, 3, 4] -> overlap at sentence 2!
    # chunk 2: [4, 5]
    assert len(chunks) >= 2
    for c in chunks:
        assert c["ticker"] == "TEST"
        assert c["section_key"] == "ITEM_1"
        assert len(c["content"]) > 30


def test_sec_rag_financial_lexicon_query_expansion():
    q_italian = "quali sono i rischi di fornitura e debito"
    expanded = expand_query_with_financial_lexicon(q_italian)
    assert "supply" in expanded or "chain" in expanded
    assert "debt" in expanded or "notes" in expanded

    # Unrelated queries should not get corrupted
    q_unknown = "quantum_unknown_token_123"
    assert expand_query_with_financial_lexicon(q_unknown) == q_unknown


def test_dynamic_voice_executive_briefing():
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)
    save_wealth_account(engine, {
        "portfolio_id": 1,
        "name": "Conto Liquidita",
        "institution": "Banca Nazionale",
        "account_type": "checking",
        "balance": 25000.0,
        "currency": "EUR"
    })

    briefing = generate_ai_voice_executive_briefing(engine, portfolio_id=1, client_name="Famiglia Verdi")
    assert briefing["mifid_compliance_verified"] is True
    assert "Famiglia Verdi" in briefing["title"]
    assert len(briefing["dialogue_script"]) >= 4
    assert any("MiFID" in d["text"] for d in briefing["dialogue_script"])
    assert briefing["word_count"] > 100
    assert briefing["total_net_worth_eur"] >= 25000.0
