"""
Unit & Integration Tests for core/ai_analyst.py
"""

import pytest
import pandas as pd
import numpy as np
from core.ai_analyst import (
    _extract_portfolio_summary_context,
    _generate_deterministic_memorandum,
    generate_portfolio_narrative_memorandum,
    query_argus_assistant
)


@pytest.fixture
def dummy_results():
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    np.random.seed(42)
    r1 = np.random.normal(0.001, 0.015, 100)
    r2 = np.random.normal(0.0008, 0.012, 100)
    df_ret = pd.DataFrame({"AAPL": r1, "MSFT": r2}, index=dates)
    
    positions = [
        {"ticker": "AAPL", "market_value": 60000.0, "weight": 0.60, "pnl_pct": 0.15, "shares": 300},
        {"ticker": "MSFT", "market_value": 40000.0, "weight": 0.40, "pnl_pct": 0.10, "shares": 100}
    ]
    
    metrics = {
        "portfolio_value": 100000.0,
        "cagr": 0.18,
        "total_return": 0.25,
        "volatility": 0.16,
        "sharpe_ratio": 1.12,
        "sortino_ratio": 1.45,
        "max_drawdown": 0.08,
        "var_95": 0.018,
        "var_cf_95": 0.018,
        "cvar_95": 0.026,
        "beta": 1.05,
        "diversification_ratio": 1.35,
        "hhi": 0.52
    }
    
    return {
        "portfolio_value": 100000.0,
        "metrics": metrics,
        "positions": positions,
        "returns": df_ret,
        "benchmark": "SPY",
        "market_regime": {"current_regime": "Bull Low-Vol"},
        "advisor_score": 82
    }


def test_extract_portfolio_summary_context(dummy_results):
    ctx = _extract_portfolio_summary_context(dummy_results)
    assert ctx["portfolio_value_eur"] == 100000.0
    assert ctx["cagr_pct"] == 18.0
    assert ctx["volatility_pct"] == 16.0
    assert ctx["sharpe_ratio"] == 1.12
    assert len(ctx["top_holdings"]) == 2
    assert ctx["market_regime"] == "Bull Low-Vol"


def test_generate_deterministic_memorandum(dummy_results):
    ctx = _extract_portfolio_summary_context(dummy_results)
    memo = _generate_deterministic_memorandum(ctx)
    assert "full_text" in memo
    assert "Sintesi Esecutiva" in memo["full_text"]
    assert "Profilo di Rischio" in memo["full_text"]
    assert "Raccomandazioni Tattiche" in memo["full_text"]
    assert memo["engine"] == "ARGUS Quant NLG (Offline Deterministic)"


def test_generate_portfolio_narrative_memorandum_offline(dummy_results):
    memo = generate_portfolio_narrative_memorandum(dummy_results, provider="offline")
    assert memo is not None
    assert len(memo["full_text"]) > 100
    assert "100,000.00" in memo["full_text"]


def test_query_argus_assistant_offline_intents(dummy_results):
    ans_var = query_argus_assistant("Qual è il mio VaR 95%?", dummy_results, provider="offline")
    assert "Value at Risk" in ans_var or "VaR" in ans_var

    ans_sharpe = query_argus_assistant("Mostrami lo Sharpe Ratio", dummy_results, provider="offline")
    assert "Sharpe" in ans_sharpe

    ans_pos = query_argus_assistant("Quali sono i titoli?", dummy_results, provider="offline")
    assert "AAPL" in ans_pos
    assert "MSFT" in ans_pos

    ans_rebal = query_argus_assistant("Consigli operativi e ribilanciamento", dummy_results, provider="offline")
    assert "Ribilanciamento" in ans_rebal or "Tattiche" in ans_rebal

    ans_empty = query_argus_assistant("", dummy_results)
    assert "Inserisci una domanda" in ans_empty
