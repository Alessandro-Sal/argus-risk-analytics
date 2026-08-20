"""
Unit tests for Local RAG & SEC Filing Vector Store (core/sec_rag_engine.py).
"""

import pytest

from core.sec_rag_engine import (
    LocalFilingVectorStore,
    _tokenize,
    index_ticker_sec_filings,
    query_sec_filings_rag,
)


def test_tokenize():
    tokens = _tokenize("The Company's revenue grew significantly in 2024!")
    assert "company" in tokens
    assert "revenue" in tokens
    assert "grew" in tokens
    assert "the" not in tokens  # Stopword


def test_local_vector_store_indexing_and_search():
    store = LocalFilingVectorStore()
    store.add_documents([
        {
            "ticker": "TEST",
            "section": "Item 1A: Risk Factors",
            "content": "Supply chain disruption in East Asia could impact hardware manufacturing.",
        },
        {
            "ticker": "TEST",
            "section": "Item 7: MD&A",
            "content": "Services revenue reached an all-time record with gross margin expansion.",
        },
    ])

    # Ricerca per supply chain
    results = store.search("supply chain manufacturing", ticker_filter="TEST", top_k=1)
    assert len(results) == 1
    top_chunk, score = results[0]
    assert top_chunk["section"] == "Item 1A: Risk Factors"
    assert score > 0.0


def test_index_ticker_sec_filings():
    cnt_aapl = index_ticker_sec_filings("AAPL")
    cnt_nvda = index_ticker_sec_filings("NVDA")
    assert cnt_aapl >= 4
    assert cnt_nvda >= 4


def test_query_sec_filings_rag_grounded_answer():
    res = query_sec_filings_rag("AAPL", "What are the supply chain and antitrust risks?")
    assert res["found"] is True
    assert res["ticker"] == "AAPL"
    assert res["top_relevance_pct"] > 50.0
    assert len(res["citations"]) > 0

    # Verifica presenza del testo sintetizzato
    assert "AAPL" in res["answer"]


def test_query_sec_filings_rag_with_section_filter():
    res = query_sec_filings_rag(
        "NVDA",
        "Data Center revenue and operating margins",
        section_filter="Item 7",
        top_k=2,
    )
    assert res["found"] is True
    assert len(res["citations"]) > 0
    for cit in res["citations"]:
        assert "Item 7" in cit["section"]


def test_query_sec_filings_rag_empty_inputs():
    res_empty = query_sec_filings_rag("", "")
    assert res_empty["found"] is False

    res_no_match = query_sec_filings_rag("AAPL", "xyz_quantum_superconducting_anomaly_9999")
    assert res_no_match["found"] is False
