"""
ARGUS — State Management & UI Lifecycle Automated QA Test Suite
==============================================================
Validates:
1. Dynamic Widget Key Salting (Scope isolation, profile binding, DB binding, versioning)
2. Atomic Page Navigation Teardown (Previous page widgets wiped, system keys preserved)
3. Profile Switch Teardown & Salt Invalidation (Orphan filter cleanup, calculation purge)
4. Hard Reset & Database Switch Teardown (Pool disposal, cache clearing, credential preservation)
5. Pre-Render Synchronization Guarantee (Zero ghost metrics across transition frames)
"""

import os
import sys
from unittest.mock import MagicMock, Mock

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
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

from core.ui_lifecycle import (
    PAGE_WIDGET_PREFIXES,
    SYSTEM_PERSISTENT_KEYS,
    TRANSIENT_ANALYTICAL_KEYS,
    get_active_context_salt,
    get_ui_lifecycle_telemetry,
    get_widget_key,
    normalize_page_identifier,
    teardown_view_state,
)
from core.workspace_context import WorkspaceContext


@pytest.fixture(autouse=True)
def clean_lifecycle_session():
    """Garantisce un session_state pulito prima e dopo ciascun test di lifecycle."""
    st.session_state.clear()
    with WorkspaceContext._LOCK:
        WorkspaceContext._FALLBACK_STORES.clear()
    yield
    st.session_state.clear()
    with WorkspaceContext._LOCK:
        WorkspaceContext._FALLBACK_STORES.clear()


class TestUILifecycleArchitecture:
    """Suite di test per la validazione del teardown e della sanificazione dello stato UI."""

    def test_normalize_page_identifier(self):
        """Verifica la corretta normalizzazione dei nomi pagina contenenti emoji e percorsi."""
        assert normalize_page_identifier("14_💳_Cash_Flow_e_Spese.py") == "14_Cash_Flow_e_Spese"
        assert normalize_page_identifier("pages/13_🏛️_Patrimonio_e_NetWorth.py") == "13_Patrimonio_e_NetWorth"
        assert normalize_page_identifier("src/0_Control_Room.py") == "0_Control_Room"
        assert normalize_page_identifier("21_🤖_AI_Copilot_e_Advisor.py") == "21_AI_Copilot_e_Advisor"
        assert normalize_page_identifier("") == ""

    def test_dynamic_widget_salting_isolation(self):
        """Verifica che get_widget_key muti deterministicamente al variare del contesto."""
        st.session_state["_ui_lifecycle_active_page"] = "14_💳_Cash_Flow_e_Spese.py"
        st.session_state["wealth_active_portfolio_id"] = 101
        st.session_state["db_name"] = "test_wealth_db"
        st.session_state["_ui_lifecycle_salt_version"] = 1

        key_pid101 = get_widget_key("cf_account_selector", scope="auto")
        assert "cf_account_selector" in key_pid101
        assert "pr_101" in key_pid101
        assert "14_Cash_Flow_e_Spese" in key_pid101

        # Idempotenza sulla medesima schermata e profilo
        key_pid101_bis = get_widget_key("cf_account_selector", scope="auto")
        assert key_pid101 == key_pid101_bis

        # Switch profilo -> La chiave muta garantendo rimontaggio da zero del componente
        st.session_state["wealth_active_portfolio_id"] = 102
        key_pid102 = get_widget_key("cf_account_selector", scope="auto")
        assert key_pid102 != key_pid101
        assert "pr_102" in key_pid102

        # Switch database -> La chiave muta determinando nuovo db_hash
        st.session_state["db_name"] = "other_database"
        key_db2 = get_widget_key("cf_account_selector", scope="auto")
        assert key_db2 != key_pid102

        # Incremento salt version -> La chiave muta anche a parità di parametri
        st.session_state["_ui_lifecycle_salt_version"] = 2
        key_v2 = get_widget_key("cf_account_selector", scope="auto")
        assert key_v2 != key_db2
        assert "v2" in key_v2

    def test_teardown_view_state_page_navigation(self):
        """Verifica che la navigazione da Pagina A a Pagina B distrugga i widget di A preservando il sistema."""
        # Setup: Pagina 14 (Cash Flow)
        st.session_state["_ui_lifecycle_active_page"] = "14_💳_Cash_Flow_e_Spese.py"
        st.session_state["wealth_active_portfolio_id"] = 55
        st.session_state["db_host"] = "127.0.0.1"
        st.session_state["theme"] = "dark"
        st.session_state["base_currency"] = "EUR"

        # Widget e filtri proprietari di Pagina 14
        st.session_state["cf_account_selector_widget"] = "Fineco Conto"
        st.session_state["cf_year_selector_widget"] = "2026"
        st.session_state["sankey_flow_dropdown_picker"] = "Totale"
        st.session_state["inp_port_table_search"] = "Search Term Old Page"

        # Simula navigazione a Pagina 13 (Patrimonio & Net Worth)
        res = teardown_view_state(target_page="pages/13_🏛️_Patrimonio_e_NetWorth.py")

        assert res["status"] == "success"
        assert res["transition_type"] == "page_navigation"
        assert res["active_page"] == "13_Patrimonio_e_NetWorth"

        # Verifica bonifica: i widget di Pagina 14 e le ricerche temporanee devono essere eliminati
        assert "cf_account_selector_widget" not in st.session_state
        assert "cf_year_selector_widget" not in st.session_state
        assert "sankey_flow_dropdown_picker" not in st.session_state
        assert "inp_port_table_search" not in st.session_state

        # Verifica preservazione: le configurazioni di sistema e i puntatori di dominio rimangono intatti
        assert st.session_state["db_host"] == "127.0.0.1"
        assert st.session_state["theme"] == "dark"
        assert st.session_state["base_currency"] == "EUR"
        assert st.session_state["wealth_active_portfolio_id"] == 55

    def test_teardown_view_state_profile_switch(self):
        """Verifica che lo switch di profilo distrugga calcoli e filtri orfani incrementando il salt."""
        st.session_state["_ui_lifecycle_active_page"] = "13_🏛️_Patrimonio_e_NetWorth.py"
        st.session_state["_ui_lifecycle_active_profile"] = 10
        st.session_state["wealth_active_portfolio_id"] = 20  # Nuovo profilo
        st.session_state["_ui_lifecycle_salt_version"] = 1

        # Risultati analitici calcolati sul profilo 10
        st.session_state["wealth_active_snapshot"] = {"total_wealth": 500000.0}
        st.session_state["triagent_last_results"] = {"rebalance_ready": True}
        st.session_state["results"] = {"var_95": 0.04}
        st.session_state["pipeline_done"] = True

        # Widget orfani del profilo 10
        st.session_state["master_pbs_year_selector"] = "2025"
        st.session_state["nw_stress_scen_picker"] = "Stagflazione"
        st.session_state["custom_widget__pr_10"] = "Old Value"

        res = teardown_view_state(target_page="13_🏛️_Patrimonio_e_NetWorth.py")

        assert res["transition_type"] == "profile_switch"
        assert st.session_state["_ui_lifecycle_salt_version"] == 2

        # Verifica che tutti i residui del profilo 10 siano svaniti
        assert "wealth_active_snapshot" not in st.session_state
        assert "triagent_last_results" not in st.session_state
        assert "results" not in st.session_state
        assert "pipeline_done" not in st.session_state
        assert "master_pbs_year_selector" not in st.session_state
        assert "nw_stress_scen_picker" not in st.session_state
        assert "custom_widget__pr_10" not in st.session_state

    def test_teardown_view_state_hard_reset_and_db_switch(self):
        """Verifica il teardown atomico totale a seguito di cambio Database o Hard Reset."""
        mock_engine = MagicMock()
        st.session_state["engine"] = mock_engine
        st.session_state["db_engine"] = mock_engine
        st.session_state["db_host"] = "mysql-cluster"
        st.session_state["db_user"] = "argus_admin"
        st.session_state["db_name"] = "db_alpha"
        st.session_state["theme"] = "dark"
        st.session_state["_ui_lifecycle_active_db"] = "db_alpha"

        # Stato volatile sparso
        st.session_state["results"] = {"alpha": 1.2}
        st.session_state["wealth_active_portfolio_id"] = 42
        st.session_state["cf_account_selector_widget"] = "Carta Oro"

        # Trigger Hard Reset manuale
        res = teardown_view_state(force=True, reason="manual_full_reset")

        assert res["transition_type"] == "database_or_hard_reset"
        assert st.session_state.get("engine") is None
        assert st.session_state.get("db_engine") is None
        assert "results" not in st.session_state
        assert "wealth_active_portfolio_id" not in st.session_state
        assert "cf_account_selector_widget" not in st.session_state

        # Credenziali e impostazioni di sistema rigorosamente preservate
        assert st.session_state["db_host"] == "mysql-cluster"
        assert st.session_state["db_user"] == "argus_admin"
        assert st.session_state["theme"] == "dark"

    def test_pre_render_synchronization_guarantee(self):
        """Verifica che lo stato sia ripulito prima che una vista visualizzi dati fantasma."""
        st.session_state["_ui_lifecycle_active_page"] = "0_Control_Room.py"
        st.session_state["_ui_lifecycle_active_profile"] = 1
        st.session_state["results"] = {"sharpe": 2.1, "portfolio_id": 1}

        # Simula utente che richiede cambio profilo prima del render
        st.session_state["portfolio_id"] = 2
        teardown_view_state(reason="profile_switch")

        # La vista che sta per renderizzare non deve trovare i risultati del profilo 1
        assert "results" not in st.session_state
        telemetry = get_ui_lifecycle_telemetry()
        assert telemetry["active_profile"] == 2
