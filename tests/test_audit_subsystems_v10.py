"""
Unit tests for the 5 Subsystems Audit and Hardening in ARGUS v10.0.0:
1. Navigation & Page Routing
2. Broker Adapters, Deduplication & ISIN/FX
3. Quant Engines & Transparency
4. Italian Tax Compliance (TUIR Art. 44 & 67)
5. AI Advisors & Packaging
"""

import os

import pandas as pd
import pytest
from sqlalchemy import create_engine


# ── 1. NAVIGATION & PAGE ROUTING ─────────────────────────────────────────────
def test_navigation_subsystem_page_routing():
    from components.ui_core.ui_utils import resolve_active_subtab
    from core.workspace_manager import resolve_page_path

    # Resolves canonical paths for shifted/renamed pages
    assert "6_🏛️_Valutazione_Aziendale.py" in resolve_page_path("Valutazione_Aziendale")
    assert "9_📈_Analisi_Tecnica.py" in resolve_page_path("Analisi_Tecnica")
    assert "3_🔴_Analisi_Rischio.py" in resolve_page_path("Analisi_Rischio")
    assert "10_🔍_Screener_Opportunita.py" in resolve_page_path("Screener_Opportunita")

    # Resilient fuzzy matching in subtabs
    options = [
        "📊 Profilo di Rischio & Fama-French",
        "📉 VaR, CVaR & Backtesting Kupiec",
        "🔗 Correlazioni, Liquidità & ATR Chandelier",
    ]
    resolved = resolve_active_subtab(options, default=options[0], key="test_subtab")
    assert resolved in options


# ── 2. BROKER ADAPTERS & ISIN RESOLUTION ─────────────────────────────────────
def test_broker_hub_facade_and_isin_european_resolution():
    # Broker hub facade works cleanly
    from core.broker_hub import SUPPORTED_BROKERS, detect_broker_format, parse_broker_csv
    assert "degiro" in SUPPORTED_BROKERS
    assert callable(parse_broker_csv)

    # ISIN Resolver recognizes common European ETFs
    from core.adapters.isin_resolver import BASE_ISIN_TO_TICKER, resolve_isin_to_ticker
    assert BASE_ISIN_TO_TICKER.get("IE00B4L5Y983") == "SWDA.MI"
    assert BASE_ISIN_TO_TICKER.get("IE00B5BMR087") == "CSSPX.MI"
    assert BASE_ISIN_TO_TICKER.get("LU0290358497") == "XEON.DE"
    assert resolve_isin_to_ticker("IE00B4L5Y983") == "SWDA.MI"


def test_universal_bank_parser_intraday_collision_deduplication():
    from core.wealth.universal_bank_parser import parse_bank_statement_file

    csv_data = """Data;Descrizione;Importo
15/05/2024;Bar Caffetteria Roma;-1.20
15/05/2024;Bar Caffetteria Roma;-1.20
16/05/2024;Supermercato Spesa;-35.50
"""
    res = parse_bank_statement_file(csv_data.encode("utf-8"), filename="estratto.csv", account_name="Conto")
    df = res["df_normalized"]
    assert len(df) == 3
    # Hashes of the two identical transactions must be distinct
    h1 = df.iloc[0]["tx_hash"]
    h2 = df.iloc[1]["tx_hash"]
    assert h1 != h2, "Intra-day identical transactions must have distinct deterministic hashes"


# ── 3. QUANT ENGINES & TRANSPARENCY ──────────────────────────────────────────
def test_personal_balance_sheet_fallback_bridge():
    from core.wealth.personal_balance_sheet import compute_personal_balance_sheet
    from core.wealth.wealth_db import init_wealth_db

    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    # Compute personal balance sheet: should not crash even if links are unconfigured
    res = compute_personal_balance_sheet(engine, portfolio_id=1)
    assert "stato_patrimoniale" in res
    assert "attivo" in res["stato_patrimoniale"]
    assert "passivo" in res["stato_patrimoniale"]


def test_unified_stress_bridge_fallback_transparency():
    from core.wealth.unified_stress_bridge import MacroFactorShock, UnifiedCrossAssetStressEngine

    # Empty positions -> should trigger fallback and flag is_fallback_proxy=True
    engine = UnifiedCrossAssetStressEngine(portfolio_positions=pd.DataFrame(), factor_betas=pd.DataFrame())
    shock = MacroFactorShock(scenario_name="Test Shock", equity_mkt_pct=-0.20)
    snap = {"liquid_investments": 50000.0, "cash_and_equivalents": 5000.0}
    res = engine.evaluate_integrated_shock(shock, snap)
    assert res["is_fallback_proxy"] is True


# ── 4. ITALIAN TAX COMPLIANCE ────────────────────────────────────────────────
def test_italian_tax_etf_classification_and_whitelist():
    from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate, is_etf

    # UCITS ETF recognition regardless of exchange suffixes
    assert is_etf("stock", "SWDA.MI") is True
    assert is_etf("equity", "CSSPX.MI") is True
    assert is_etf("", "VWCE.MI") is True
    assert is_etf("stock", "ISAC.L") is True
    assert is_etf("equity", "XEON.DE") is True
    assert is_etf("equity", "AAPL") is False
    assert is_etf("stock", "ISP.MI") is False

    # White List 12.5% vs 26%
    assert get_asset_tax_rate("Government Bond", "BTP-3.5-2034") == 0.125
    assert get_asset_tax_rate("BTP", "IT0005436693") == 0.125
    assert get_asset_tax_rate("Equity", "ISP.MI") == 0.26

    # Test White List capital gain taxed at 12.5% and not 26%
    positions = pd.DataFrame([
        {"ticker": "BTP-2034", "asset_class": "BTP", "pnl_realized": 1000.0, "pnl_unrealized": 0.0},
        {"ticker": "AAPL", "asset_class": "Equity", "pnl_realized": 1000.0, "pnl_unrealized": 0.0},
    ])
    res = compute_tax_and_harvesting({"positions": positions})
    summary = res["summary"]
    # BTP 1000 @ 12.5% = 125€; AAPL 1000 @ 26% = 260€; Total tax due = 385€
    assert summary["estimated_tax_due_eur"] == 385.0


def test_etf_unrealized_losses_harvesting_eligibility():
    from core.tax_engine import compute_tax_and_harvesting

    # ETF in loss: generates eligible tax loss harvesting candidate under Italian law
    positions = pd.DataFrame([
        {"ticker": "SWDA.MI", "asset_class": "ETF", "pnl_realized": 0.0, "pnl_unrealized": -500.0},
    ])
    res = compute_tax_and_harvesting({"positions": positions})
    harvest_df = res["harvesting_opportunities"]
    assert not harvest_df.empty
    assert harvest_df.iloc[0]["ticker"] == "SWDA.MI"
    assert "Minusvalenza" in harvest_df.iloc[0]["qualifying_type"]


# ── 5. AI ADVISORS & PACKAGING ───────────────────────────────────────────────
def test_sec_rag_engine_synthetic_boilerplate_flag():
    from core.sec_rag_engine import query_sec_filings_rag

    # Unindexed ticker -> flagged as synthetic boilerplate
    res = query_sec_filings_rag("XYZ_NON_EXISTENT", "Che rischi competitivi ci sono?")
    assert res["is_synthetic_boilerplate"] is True
    assert "PROFILO DIDATTICO STANDARD" in res["answer"]


def test_ai_analyst_cache_and_unified_key():
    from core.ai_analyst import _get_cached_llm_response, _resolve_unified_api_key, _set_cached_llm_response

    # Cache mechanism works
    test_prompt = "Spiegami il rischio del portafoglio"
    _set_cached_llm_response(test_prompt, "gemini-test", "Risposta di test in cache.")
    cached = _get_cached_llm_response(test_prompt, "gemini-test")
    assert cached == "Risposta di test in cache."

    # Unified key resolution
    key = _resolve_unified_api_key("custom-key-123")
    assert key == "custom-key-123"
