"""
Unit tests for ARGUS WorkspaceContext, State Management, Domain Flushing and Reactive Total Wealth Consolidation.
"""

import os
import pytest
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

from core.workspace_context import (
    WorkspaceContext,
    RiskSubContext,
    WealthSubContext,
    UIViewState,
    prune_stale_session_caches,
    SESSIONS_CACHE_DIR
)
from core.wealth.wealth_db import (
    init_wealth_db,
    create_wealth_portfolio,
    set_linked_risk_portfolios
)
from core.wealth.wealth_engine import compute_consolidated_net_worth


def test_workspace_context_initialization():
    """Verifica l'inizializzazione corretta e i valori di default tipizzati."""
    ctx = WorkspaceContext(session_id="test_init_session")
    assert ctx.session_id == "test_init_session"
    assert ctx.risk.portfolio_name == "Nessun Portafoglio"
    assert ctx.risk.base_currency == "EUR"
    assert ctx.risk.get_total_equity() == 0.0
    assert ctx.wealth.profile_id == 1
    assert isinstance(ctx.ui, UIViewState)

    # Test get_total_equity con DataFrame di posizioni
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 45000.0},
        {"ticker": "MSFT", "current_value": 55000.0}
    ])
    ctx.risk.results = {"positions": df_pos}
    assert ctx.risk.get_total_equity() == 100000.0

    # Test fallback con metrics dict
    ctx.risk.results = {"metrics": {"portfolio_value": 85000.0}}
    assert ctx.risk.get_total_equity() == 85000.0


def test_domain_flushing_and_orphan_key_purging(monkeypatch):
    """
    Verifica che flush_risk_domain elimini deterministicamente:
    1. Le chiavi primarie del portafoglio (results, portfolio_id, ecc.)
    2. Tutti i widget analitici orfani (ta_target_*, tech_*, time_*, screener_*, stress_*)
    3. Preservi le credenziali DB e i flag di configurazione globale.
    """
    # Creiamo un finto st.session_state (dizionario isolato)
    fake_session = {
        # Core keys
        "results": {"positions": pd.DataFrame()},
        "portfolio_id": 42,
        "portfolio_name": "Tech Portfolio",
        "run_id": "RUN-2026-TEST",
        "pipeline_done": True,
        "fetch_report": {"success": ["AAPL"]},
        # Orphan analytical widget keys
        "ta_target_ticker": "NVDA",
        "tech_active_subtab": "RSI & MACD",
        "tech_active_subtab_selectbox": "RSI & MACD",
        "time_active_tab": "Annual Returns",
        "screener_segmented_subtab": "Value Screen",
        "stress_scenarios_selected": ["Covid Crash"],
        "quant_frontier_selected_point": 3,
        "target_subtab_tech_active": "Overview",
        # Unrelated system keys that MUST be preserved
        "db_user": "argus_admin",
        "db_host": "localhost",
        "offline_mode": True,
        "wealth_active_portfolio_id": 1
    }

    # Monkeypatching di _get_st_session_state
    monkeypatch.setattr(WorkspaceContext, "_get_st_session_state", classmethod(lambda cls: fake_session))

    ctx = WorkspaceContext.get_current(session_id="test_flush_session")
    assert ctx.risk.portfolio_id == 42
    assert ctx.risk.portfolio_name == "Tech Portfolio"

    # Esegui il flush
    ctx.flush_risk_domain()

    # Verifica rimozione chiavi core
    for k in ["results", "portfolio_id", "portfolio_name", "run_id", "pipeline_done", "fetch_report"]:
        assert k not in fake_session

    # Verifica rimozione chiavi orfane
    for k in [
        "ta_target_ticker", "tech_active_subtab", "tech_active_subtab_selectbox",
        "time_active_tab", "screener_segmented_subtab", "stress_scenarios_selected",
        "quant_frontier_selected_point", "target_subtab_tech_active"
    ]:
        assert k not in fake_session

    # Verifica conservazione impostazioni di sistema
    assert fake_session["db_user"] == "argus_admin"
    assert fake_session["db_host"] == "localhost"
    assert fake_session["offline_mode"] is True
    assert fake_session["wealth_active_portfolio_id"] == 1
    assert fake_session.get("session_cleared") is True


def test_reactive_total_wealth_consolidation(monkeypatch):
    """
    Verifica che compute_consolidated_net_worth incorpori reattivamente
    il valore live in memoria del portafoglio titoli senza forzare uno snapshot su DB.
    """
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    w_pid = create_wealth_portfolio(engine, name="Marco Rossi Test", owner="Marco", base_currency="EUR")
    # Colleghiamo il risk_portfolio_id = 99
    set_linked_risk_portfolios(engine, w_pid, [99])

    # Simuliamo un portafoglio live in WorkspaceContext con ID 99 e valore €250,000
    df_live_pos = pd.DataFrame([
        {"ticker": "ETF_WORLD", "current_value": 150000.0},
        {"ticker": "ETF_EMERGING", "current_value": 100000.0}
    ])
    live_risk_results = {
        "positions": df_live_pos,
        "metrics": {"portfolio_value": 250000.0}
    }

    mock_state = {
        "results": live_risk_results,
        "portfolio_id": 99,
        "portfolio_name": "Global Equity Live",
        "pipeline_done": True
    }
    monkeypatch.setattr(WorkspaceContext, "_get_st_session_state", classmethod(lambda cls: mock_state))

    ws_ctx = WorkspaceContext.get_current(session_id="test_reactive_nw")
    ws_ctx.risk.portfolio_id = 99
    ws_ctx.risk.results = live_risk_results
    ws_ctx.risk.is_live_active = True

    # Calcolo Net Worth consolidato
    nw = compute_consolidated_net_worth(engine, portfolio_id=w_pid)

    # In assenza di conti bancari o asset fisici, il totale investimenti finanziari deve riflettere il live risk!
    assert nw.financial_investments == 250000.0
    assert nw.total_net_worth == 250000.0


def test_session_cache_isolation_and_persistence():
    """Verifica che sessioni distinte scrivano su percorsi di cache isolati senza collisioni."""
    ctx_a = WorkspaceContext(session_id="user_alpha_123")
    ctx_b = WorkspaceContext(session_id="user_beta_456")

    path_a = ctx_a.get_session_cache_path()
    path_b = ctx_b.get_session_cache_path()

    assert path_a != path_b
    assert "user_alpha_123" in path_a
    assert "user_beta_456" in path_b

    # Salva sessione A
    ctx_a.risk.results = {"positions": pd.DataFrame([{"ticker": "AAPL", "current_value": 1000.0}])}
    ctx_a.risk.portfolio_name = "Alpha Portfolio"
    assert ctx_a.save_session_cache() is True
    assert os.path.exists(path_a)

    # Salva sessione B con contenuto differente
    ctx_b.risk.results = {"positions": pd.DataFrame([{"ticker": "TSLA", "current_value": 5000.0}])}
    ctx_b.risk.portfolio_name = "Beta Portfolio"
    assert ctx_b.save_session_cache() is True
    assert os.path.exists(path_b)

    # Ripristina sessione A in un nuovo contesto con session_id A
    restored_a = WorkspaceContext(session_id="user_alpha_123")
    assert restored_a.restore_session_cache(force=True) is True
    assert restored_a.risk.portfolio_name == "Alpha Portfolio"

    # Ripristina sessione B in un nuovo contesto con session_id B
    restored_b = WorkspaceContext(session_id="user_beta_456")
    assert restored_b.restore_session_cache(force=True) is True
    assert restored_b.risk.portfolio_name == "Beta Portfolio"

    # Cleanup file di test
    ctx_a.clear_persisted_cache()
    ctx_b.clear_persisted_cache()
    assert not os.path.exists(path_a)
    assert not os.path.exists(path_b)


def test_session_snapshot_json_export_and_import():
    """Verifica l'esportazione e l'importazione deterministica di snapshot di sessione in formato JSON."""
    ctx = WorkspaceContext(session_id="export_test_uuid")
    ctx.risk.portfolio_id = 99
    ctx.risk.portfolio_name = "Quant Snapshot Portfolio"
    ctx.risk.benchmark = "IWDA.AS"
    ctx.risk.base_currency = "EUR"
    ctx.risk.risk_free_rate = 0.025
    ctx.ui.page_subtabs = {"tech_page": "Bollinger Bands"}
    ctx.ui.active_filters = {"date_range": "3Y"}

    df_pos = pd.DataFrame([
        {"ticker": "NVDA", "quantity": 100.0, "current_value": 12000.0},
        {"ticker": "MSFT", "quantity": 50.0, "current_value": 20000.0}
    ])
    ctx.risk.results = {
        "positions": df_pos,
        "metrics": {"portfolio_value": 32000.0, "sharpe_ratio": 1.45}
    }

    # 1. Esportazione dello snapshot
    snapshot = ctx.export_session_snapshot()

    assert isinstance(snapshot, dict)
    assert snapshot["schema_version"] == "9.0.0"
    assert snapshot["risk"]["portfolio_name"] == "Quant Snapshot Portfolio"
    assert snapshot["risk"]["benchmark"] == "IWDA.AS"
    assert len(snapshot["risk"]["positions"]) == 2
    assert snapshot["ui"]["active_filters"]["date_range"] == "3Y"

    # 2. Importazione in un contesto vuoto
    new_ctx = WorkspaceContext(session_id="import_target_uuid")
    success = new_ctx.import_session_snapshot(snapshot)

    assert success is True
    assert new_ctx.risk.portfolio_name == "Quant Snapshot Portfolio"
    assert new_ctx.risk.benchmark == "IWDA.AS"
    assert new_ctx.risk.risk_free_rate == 0.025
    assert new_ctx.risk.is_live_active is True
    assert isinstance(new_ctx.risk.results["positions"], pd.DataFrame)
    assert len(new_ctx.risk.results["positions"]) == 2
    assert new_ctx.ui.active_filters.get("date_range") == "3Y"
    assert new_ctx.risk.get_total_equity() == 32000.0

