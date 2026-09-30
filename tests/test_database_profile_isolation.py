"""
ARGUS — Risk Analytics Platform
QA & Reliability Automated Test Suite: Database & Profile Selection Isolation
Validates:
1. Switch Sequence Zero Data Leakage (DB_A -> Session Mutation -> DB_B)
2. Roundtrip Integrity (DB_A -> DB_B -> DB_A without state pollution)
3. Cache Poisoning Prevention (Identical query parameters across distinct DBs and profiles)
4. Exception Resilience & Orphan Connection Cleanup (Graceful rollback, dispose teardown, and concurrency)
"""

import os
import shutil
import sys
import tempfile
import threading
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

# Setup Streamlit session_state proxy for headless pytest execution
if not hasattr(st, "session_state") or not isinstance(st.session_state, dict):
    class SessionState(dict):
        def __getattr__(self, item):
            return self.get(item)

        def __setattr__(self, key, value):
            self[key] = value

        def __delattr__(self, item):
            self.pop(item, None)

    st.session_state = SessionState()

from core.fetcher import dispose_engine
from core.wealth.wealth_db import (
    bulk_insert_cashflow_tx,
    create_wealth_portfolio,
    get_physical_assets,
    get_wealth_accounts,
    get_wealth_portfolios,
    init_wealth_db,
    save_physical_asset,
    save_wealth_account,
)
from core.wealth.wealth_engine import compute_consolidated_net_worth
from core.wealth.wealth_reporting_hub import _get_engine_db_key
from core.workspace_context import WorkspaceContext


# ── FIXTURES ─────────────────────────────────────────────────────────


@pytest.fixture
def isolated_session_state():
    """Garantisce un session_state pulito e isolato prima e dopo ogni test."""
    st.session_state.clear()
    with WorkspaceContext._LOCK:
        WorkspaceContext._FALLBACK_STORES.clear()
    yield st.session_state
    st.session_state.clear()
    with WorkspaceContext._LOCK:
        WorkspaceContext._FALLBACK_STORES.clear()


@pytest.fixture
def dual_db_environments():
    """
    Crea due database SQLite fisicamente isolati su percorsi file temporanei distinti
    (DB_A e DB_B) con bootstrap dello schema e teardown garantito dei pool di connessione.
    """
    temp_dir = tempfile.mkdtemp(prefix="argus_qa_isolation_")
    db_a_path = os.path.join(temp_dir, "argus_database_a.db").replace("\\", "/")
    db_b_path = os.path.join(temp_dir, "argus_database_b.db").replace("\\", "/")

    engine_a = create_engine(f"sqlite:///{db_a_path}", echo=False)
    engine_b = create_engine(f"sqlite:///{db_b_path}", echo=False)

    init_wealth_db(engine_a)
    init_wealth_db(engine_b)

    yield {
        "temp_dir": temp_dir,
        "db_a_path": db_a_path,
        "db_b_path": db_b_path,
        "engine_a": engine_a,
        "engine_b": engine_b,
    }

    # Teardown: rilascio di tutti i lock di file SQLite prima della cancellazione cartella
    dispose_engine(engine_a)
    dispose_engine(engine_b)
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


# ── TEST SUITE ───────────────────────────────────────────────────────


class TestDatabaseProfileIsolation:
    """Suite di affidabilità per la validazione dell'isolamento dei dati e del lifecycle DB/Profili."""

    def test_switch_sequence_zero_data_leakage(self, isolated_session_state, dual_db_environments):
        """
        1. SEQUENZA DI SWITCH (DB_A -> Modifica in sessione -> Switch a DB_B):
        Verifica che nessun dato (anagrafico, contabile, analitico o di snapshot) di DB_A
        sia presente in DB_B né persista nelle chiavi di sessione e memoria applicativa.
        """
        engine_a = dual_db_environments["engine_a"]
        engine_b = dual_db_environments["engine_b"]

        # Step 1: Popolamento dati specifici su DB_A
        pid_a = create_wealth_portfolio(engine_a, name="Alpha Family Office", owner="User Alpha")
        aid_a = save_wealth_account(
            engine_a,
            {
                "portfolio_id": pid_a,
                "name": "Banca Alpha Private",
                "account_type": "checking",
                "balance": 150000.0,
            },
        )
        save_physical_asset(
            engine_a,
            {
                "portfolio_id": pid_a,
                "name": "Villa Alpha Lago",
                "asset_category": "real_estate",
                "purchase_price": 400000.0,
                "current_market_value": 450000.0,
            },
        )

        nw_a = compute_consolidated_net_worth(engine_a, portfolio_id=pid_a)
        assert nw_a.total_net_worth == 600000.0

        # Step 2: Caricamento dello stato attivo in Streamlit Session e WorkspaceContext per DB_A
        st.session_state["db_name"] = "database_a"
        st.session_state["engine"] = engine_a
        st.session_state["db_engine"] = engine_a
        st.session_state["wealth_active_portfolio_id"] = pid_a
        st.session_state["wealth_active_profile_name"] = "Alpha Family Office"
        st.session_state["wealth_active_snapshot"] = {"total_net_worth": 600000.0, "client": "Alpha"}
        st.session_state["portfolio_id"] = 101
        st.session_state["portfolio_name"] = "Alpha Risk Portfolio"
        st.session_state["results"] = {"positions": pd.DataFrame([{"ticker": "AAPL", "current_value": 10000.0}])}
        st.session_state["pipeline_done"] = True

        # Widget orfani analitici
        st.session_state["ta_target_ticker"] = "AAPL"
        st.session_state["screener_segmented_subtab"] = "Value Screener"
        st.session_state["active_opt_weights"] = [0.5, 0.5]
        st.session_state["stress_scenarios_selected"] = ["2008 Lehman Crash"]

        ws = WorkspaceContext.get_current()
        ws.wealth.profile_id = pid_a
        ws.wealth.profile_name = "Alpha Family Office"
        ws.risk.portfolio_id = 101
        ws.risk.results = st.session_state["results"]

        # Step 3: Esecuzione switch atomico verso DB_B con monitoraggio di dispose()
        with patch.object(engine_a, "dispose", wraps=engine_a.dispose) as spy_dispose:
            WorkspaceContext.execute_database_switch(new_db="database_b", offline_mode=True)
            # Verifica che il connection pool del vecchio engine sia stato dismesso
            assert spy_dispose.call_count >= 1

        # Step 4: Verifica bonifica completa dello stato di sessione (Zero In-Memory Residuals)
        assert st.session_state.get("engine") is None
        assert st.session_state.get("db_engine") is None
        assert st.session_state.get("wealth_active_portfolio_id") is None
        assert st.session_state.get("wealth_active_profile_name") is None
        assert "wealth_active_snapshot" not in st.session_state
        assert "results" not in st.session_state
        assert "portfolio_id" not in st.session_state
        assert "portfolio_name" not in st.session_state
        assert "pipeline_done" not in st.session_state

        # Verifica eliminazione di tutti i widget orfani analitici
        assert "ta_target_ticker" not in st.session_state
        assert "screener_segmented_subtab" not in st.session_state
        assert "active_opt_weights" not in st.session_state
        assert "stress_scenarios_selected" not in st.session_state

        # Verifica allineamento puntatori DB al nuovo database
        assert st.session_state.get("db_name") == "database_b"
        assert st.session_state.get("wealth_db_name") == "database_b"
        assert st.session_state.get("risk_db_name") == "database_b"
        assert st.session_state.get("offline_mode") is True

        # Verifica reset all'interno dell'istanza WorkspaceContext
        assert ws.wealth.profile_id is None
        assert ws.wealth.profile_name == "Nessun Profilo Selezionato"
        assert ws.risk.results is None
        assert ws.risk.portfolio_id is None

        # Step 5: Popolamento DB_B con entità differenti
        pid_b = create_wealth_portfolio(engine_b, name="Beta Capital Partner", owner="User Beta")
        aid_b = save_wealth_account(
            engine_b,
            {
                "portfolio_id": pid_b,
                "name": "Banca Beta Liquidity",
                "account_type": "checking",
                "balance": 75000.0,
            },
        )

        # Step 6: Assert sull'isolamento del Database B (Zero Cross-Contamination)
        df_accounts_b = get_wealth_accounts(engine_b, portfolio_id=pid_b)
        assert len(df_accounts_b) == 1
        assert df_accounts_b.iloc[0]["name"] == "Banca Beta Liquidity"
        assert "Banca Alpha Private" not in df_accounts_b["name"].values

        df_assets_b = get_physical_assets(engine_b, portfolio_id=pid_b)
        assert df_assets_b.empty  # Nessun asset di Alpha deve esistere in Beta

        df_portfolios_b = get_wealth_portfolios(engine_b)
        assert "Alpha Family Office" not in df_portfolios_b["name"].values
        assert "Beta Capital Partner" in df_portfolios_b["name"].values

        nw_b = compute_consolidated_net_worth(engine_b, portfolio_id=pid_b)
        assert nw_b.total_net_worth == 75000.0
        assert nw_b.liquid_cash == 75000.0

    def test_switch_roundtrip_integrity(self, isolated_session_state, dual_db_environments):
        """
        2. RITORNO ALLO STATO INIZIALE (Switch DB_A -> DB_B -> DB_A):
        Verifica che l'andata e ritorno tra database multipli non corrompa né alteri i dati di DB_A,
        e che la riattivazione del profilo originale ripristini uno stato coerente e intatto.
        """
        engine_a = dual_db_environments["engine_a"]
        engine_b = dual_db_environments["engine_b"]

        # Step 1: Stato iniziale consolidato su DB_A
        pid_a = create_wealth_portfolio(engine_a, name="Holding Lombardia", owner="Lombardia Group")
        save_wealth_account(
            engine_a,
            {
                "portfolio_id": pid_a,
                "name": "Intesa Sanpaolo Wealth",
                "balance": 280000.0,
            },
        )
        save_physical_asset(
            engine_a,
            {
                "portfolio_id": pid_a,
                "name": "Capannone Industriale",
                "asset_category": "real_estate",
                "purchase_price": 500000.0,
                "current_market_value": 520000.0,
            },
        )
        initial_nw_a = compute_consolidated_net_worth(engine_a, portfolio_id=pid_a)
        assert initial_nw_a.total_net_worth == 800000.0

        # Step 2: Switch a DB_B ed esecuzione operazioni di scrittura e calcolo
        WorkspaceContext.execute_database_switch(new_db="database_b")
        pid_b = create_wealth_portfolio(engine_b, name="Startup Liguria", owner="Liguria Partner")
        aid_b = save_wealth_account(
            engine_b,
            {
                "portfolio_id": pid_b,
                "name": "Fineco Startup Account",
                "balance": 35000.0,
            },
        )
        # Inserimento transazione di cashflow su DB_B
        bulk_insert_cashflow_tx(
            engine_b,
            [
                {
                    "portfolio_id": pid_b,
                    "account_id": aid_b,
                    "category_id": 1,
                    "tx_date": date.today(),
                    "amount": 5000.0,
                    "direction": "inflow",
                    "merchant": "Cliente Tech",
                }
            ],
        )
        nw_b = compute_consolidated_net_worth(engine_b, portfolio_id=pid_b)
        assert nw_b.total_net_worth == 40000.0

        # Step 3: Switch di ritorno verso DB_A
        WorkspaceContext.execute_database_switch(new_db="database_a")

        # Verifica pulizia prima del ri-caricamento
        assert st.session_state.get("wealth_active_portfolio_id") is None
        assert st.session_state.get("db_name") == "database_a"

        # Re-selezione deterministica del profilo originario su DB_A
        st.session_state["engine"] = engine_a
        st.session_state["db_engine"] = engine_a
        WorkspaceContext.switch_wealth_profile(new_pid=pid_a, profile_name="Holding Lombardia")

        # Step 4: Asserzioni rigorose di integrità su DB_A dopo il roundtrip
        # Nessun record di DB_B deve essere finito in DB_A
        accounts_a = get_wealth_accounts(engine_a, portfolio_id=pid_a)
        assert len(accounts_a) == 1
        assert accounts_a.iloc[0]["name"] == "Intesa Sanpaolo Wealth"
        assert "Fineco Startup Account" not in accounts_a["name"].values

        portfolios_a = get_wealth_portfolios(engine_a)
        assert "Startup Liguria" not in portfolios_a["name"].values
        assert "Holding Lombardia" in portfolios_a["name"].values

        # Il Net Worth deve corrispondere al centesimo al valore pre-switch
        recalculated_nw_a = compute_consolidated_net_worth(engine_a, portfolio_id=pid_a)
        assert recalculated_nw_a.total_net_worth == initial_nw_a.total_net_worth == 800000.0
        assert recalculated_nw_a.liquid_cash == 280000.0
        assert recalculated_nw_a.real_estate_total == 520000.0

    def test_cache_poisoning_prevention_cross_database(self, isolated_session_state, dual_db_environments):
        """
        3. CACHE POISONING: Cross-Database con medesimi parametri di query.
        Verifica che una funzione in cache invocata con lo stesso portfolio_id (es. pid=1)
        su due database distinti generi cache-key differenti grazie al binding di db_key,
        e che execute_database_switch invalidi la cache evitando letture stantie.
        """
        engine_a = dual_db_environments["engine_a"]
        engine_b = dual_db_environments["engine_b"]

        key_a = _get_engine_db_key(engine_a)
        key_b = _get_engine_db_key(engine_b)

        # Le chiavi di isolamento DB devono essere uniche e non collidere
        assert key_a != key_b
        assert "argus_database_a.db" in key_a
        assert "argus_database_b.db" in key_b

        # Creiamo su entrambi i database un profilo con portfolio_id analogo (pid=1 o specifico)
        pid_a = create_wealth_portfolio(engine_a, name="Alpha Profile Identical ID")
        save_wealth_account(engine_a, {"portfolio_id": pid_a, "name": "Account Alpha", "balance": 999000.0})

        pid_b = create_wealth_portfolio(engine_b, name="Beta Profile Identical ID")
        save_wealth_account(engine_b, {"portfolio_id": pid_b, "name": "Account Beta", "balance": 111000.0})

        # Definiamo una funzione con caching identica a quelle del sistema
        call_tracker = {"calls": 0}

        @st.cache_data(ttl=60, show_spinner=False)
        def _get_cached_net_worth_metric(_engine, target_pid: int, db_key: str = ""):
            call_tracker["calls"] += 1
            nw = compute_consolidated_net_worth(_engine, portfolio_id=target_pid)
            return float(nw.total_net_worth)

        # Esecuzione query 1 su DB_A con target_pid=1
        res_a1 = _get_cached_net_worth_metric(engine_a, 1, db_key=key_a)
        assert res_a1 == 999000.0
        assert call_tracker["calls"] == 1

        # Seconda esecuzione identica su DB_A -> deve restituire la cache (call_tracker non incrementa)
        res_a2 = _get_cached_net_worth_metric(engine_a, 1, db_key=key_a)
        assert res_a2 == 999000.0
        assert call_tracker["calls"] == 1

        # Esecuzione su DB_B con IDENTICI parametri di business (target_pid=1) ma diverso db_key
        res_b1 = _get_cached_net_worth_metric(engine_b, 1, db_key=key_b)
        assert res_b1 == 111000.0
        assert res_b1 != res_a1
        # La chiamata deve aver calcolato il dato di DB_B senza poisoning da DB_A
        assert call_tracker["calls"] == 2

        # Ri-lettura su DB_A -> il dato di DB_A non deve essere stato sovrascritto
        res_a3 = _get_cached_net_worth_metric(engine_a, 1, db_key=key_a)
        assert res_a3 == 999000.0
        assert call_tracker["calls"] == 2

        # Invocazione di execute_database_switch -> deve svuotare le cache di processo
        with patch.object(st.cache_data, "clear", wraps=st.cache_data.clear) as spy_clear:
            WorkspaceContext.execute_database_switch(new_db="database_b")
            assert spy_clear.call_count >= 1

    def test_cache_poisoning_prevention_intra_database_profile_switch(self, isolated_session_state, dual_db_environments):
        """
        3B. CACHE POISONING: Switch di Profilo all'interno dello stesso Database.
        Verifica che lo switch tra Profili azzeri lo snapshot storico in sessione (wealth_active_snapshot),
        sincronizzi i widget di tutte le pagine ed eviti che un profilo mostri i dati dell'altro.
        """
        engine_a = dual_db_environments["engine_a"]

        pid_1 = create_wealth_portfolio(engine_a, name="Profilo Uno - Mario")
        pid_2 = create_wealth_portfolio(engine_a, name="Profilo Due - Laura")

        # Impostiamo stato attivo per Mario
        WorkspaceContext.switch_wealth_profile(new_pid=pid_1, profile_name="Profilo Uno - Mario")
        st.session_state["wealth_active_snapshot"] = {
            "portfolio_id": pid_1,
            "owner": "Mario",
            "net_worth": 500000.0,
            "calculated_at": "2026-09-30T10:00:00",
        }

        assert st.session_state["wealth_active_portfolio_id"] == pid_1
        assert st.session_state["wealth_active_snapshot"]["owner"] == "Mario"

        # Switch al Profilo Due - Laura
        WorkspaceContext.switch_wealth_profile(new_pid=pid_2, profile_name="Profilo Due - Laura")

        # Verifica che lo snapshot di Mario sia stato epurato
        assert "wealth_active_snapshot" not in st.session_state
        assert st.session_state["wealth_active_portfolio_id"] == pid_2
        assert st.session_state["wealth_active_profile_name"] == "Profilo Due - Laura"

        # Verifica sincronizzazione di tutti i widget di pagina
        assert st.session_state["sb_wealth_profile_selector"] == pid_2
        assert st.session_state["wealth_profile_selector_widget"] == pid_2
        assert st.session_state["nw_profile_selector_widget"] == pid_2
        assert st.session_state["cf_profile_selector_widget"] == pid_2
        assert st.session_state["pension_profile_selector_widget"] == pid_2
        assert st.session_state["fiscal_profile_selector_widget"] == pid_2
        assert st.session_state["estate_profile_selector_widget"] == pid_2
        assert st.session_state["ai_profile_selector_widget"] == pid_2

        # Assegniamo un nuovo snapshot per Laura
        st.session_state["wealth_active_snapshot"] = {
            "portfolio_id": pid_2,
            "owner": "Laura",
            "net_worth": 750000.0,
        }

        # Switch di ritorno a Mario
        WorkspaceContext.switch_wealth_profile(new_pid=pid_1, profile_name="Profilo Uno - Mario")

        # Verifica che lo snapshot di Laura sia stato rimosso
        assert "wealth_active_snapshot" not in st.session_state
        assert st.session_state["wealth_active_portfolio_id"] == pid_1
        assert st.session_state["wealth_profile_selector_widget"] == pid_1

    def test_switch_exception_resilience_and_orphan_cleanup(self, isolated_session_state, dual_db_environments):
        """
        4. CONCORRENZA / ROLLBACK: Simulazione di errore a metà switch.
        Verifica che in caso di eccezione durante il teardown o la connessione al nuovo DB:
        - Il vecchio engine venga comunque dismesso senza connessioni o lock orfani.
        - Lo stato di sessione non rimanga corrotto con handle aperti o puntatori a metà.
        - Il sistema ritorni a uno stato safe e consistente.
        """
        engine_a = dual_db_environments["engine_a"]

        # Popolamento stato iniziale
        st.session_state["engine"] = engine_a
        st.session_state["db_engine"] = engine_a
        st.session_state["db_name"] = "database_a"
        st.session_state["wealth_active_portfolio_id"] = 42

        # Simuliamo un'eccezione a metà switch (es. fallimento durante la pulizia cache su disco)
        with patch("core.cache_shield.clear_cache", side_effect=OSError("Disk lock simulation")):
            with patch.object(engine_a, "dispose", wraps=engine_a.dispose) as spy_dispose:
                # execute_database_switch deve catturare l'eccezione non-fatale senza interrompere il teardown
                WorkspaceContext.execute_database_switch(new_db="database_corrupt", offline_mode=False)

                # Verifica che dispose dell'engine precedente sia stato comunque chiamato
                assert spy_dispose.call_count >= 1

        # Verifica che i puntatori all'engine siano stati azzerati e non rimangano socket appesi
        assert st.session_state.get("engine") is None
        assert st.session_state.get("db_engine") is None
        assert st.session_state.get("wealth_active_portfolio_id") is None
        assert st.session_state.get("wealth_active_profile_name") is None

        # Simuliamo un errore fatale al momento della creazione del nuovo engine (es. timeout di rete)
        def _failing_get_engine(*args, **kwargs):
            raise OperationalError("Can't connect to MySQL server on '192.168.1.99' (10060)", params=None, orig=None)

        with patch("core.fetcher.get_engine", side_effect=_failing_get_engine):
            # Simuliamo la logica di fallback del chiamante (come in core/sidebar.py e core/ui_utils.py)
            fallback_triggered = False
            try:
                from core.fetcher import get_engine
                new_eng = get_engine(host="192.168.1.99", db="non_existent")
            except OperationalError:
                # Safe recovery: rollback su SQLite locale offline
                fallback_triggered = True
                new_eng = create_engine(f"sqlite:///{dual_db_environments['db_a_path']}")
                st.session_state["offline_mode"] = True
                st.session_state["engine"] = new_eng
                st.session_state["db_engine"] = new_eng

            assert fallback_triggered is True
            assert st.session_state["offline_mode"] is True
            assert st.session_state["engine"] is not None
            # Verifica che il fallback funzioni regolarmente
            portfolios = get_wealth_portfolios(st.session_state["engine"])
            assert not portfolios.empty
            dispose_engine(new_eng)

    def test_concurrent_switching_thread_safety(self, isolated_session_state, dual_db_environments):
        """
        4B. CONCORRENZA: Simulazione di chiamate simultanee di switch DB e Profili.
        Verifica che WorkspaceContext._LOCK garantisca la thread-safety e scongiuri race conditions.
        """
        engine_a = dual_db_environments["engine_a"]
        engine_b = dual_db_environments["engine_b"]

        errors = []

        def worker_db_switch(db_id: int):
            try:
                target_db = f"test_db_{db_id}"
                WorkspaceContext.execute_database_switch(new_db=target_db)
            except Exception as e:
                errors.append(e)

        def worker_profile_switch(pid: int):
            try:
                WorkspaceContext.switch_wealth_profile(new_pid=pid, profile_name=f"Profile_{pid}")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t1 = threading.Thread(target=worker_db_switch, args=(i % 2,))
            t2 = threading.Thread(target=worker_profile_switch, args=(i,))
            threads.extend([t1, t2])

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Nessun thread deve sollevare eccezioni o causare deadlock
        assert len(errors) == 0

        # Il contesto finale deve essere consistente
        ws = WorkspaceContext.get_current()
        assert ws is not None
        assert isinstance(ws.version, int)
        assert ws.version > 1
