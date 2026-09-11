"""
ARGUS — Quantitative Risk & Wealth Intelligence Platform
Automated QA Suite: Empty State (Phase B), Demo Portfolio (Phase B), and Session Reset Cycle.
Tests robustness across standalone and portfolio-dependent modules under zero-data, demo-loaded, and reset states.
"""

from datetime import date, datetime
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
import streamlit as st

from core.fetcher import get_engine
from core.onboarding_guard import ensure_portfolio_loaded, render_empty_state_screen, empty_state_guard
from core.unified_demo_seeder import seed_unified_demo_scenario
from core.wealth.wealth_db import (
    init_wealth_db,
    get_wealth_portfolios,
    get_wealth_accounts,
    get_physical_assets,
    get_pension_plans,
    get_cashflow_records
)
from core.wealth.wealth_engine import compute_consolidated_net_worth


class StreamlitStopInvoked(Exception):
    """Simulates st.stop() interruption cleanly in headless test environment."""
    pass


# ==========================================================================
# FASE A: TEST A PORTAFOGLIO ASSENTE (EMPTY STATE / ZERO DATA)
# ==========================================================================

@pytest.mark.qa
def test_phase_a_empty_state_guard_blocks_risk_module():
    """Verifica che un modulo Risk dipendente sollevi st.stop() in assenza di portafoglio."""
    st.session_state.clear()
    st.session_state["session_cleared"] = True

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        with pytest.raises(StreamlitStopInvoked):
            ensure_portfolio_loaded(module_type="risk")


@pytest.mark.qa
def test_phase_a_empty_state_guard_blocks_wealth_module():
    """Verifica che un modulo Wealth dipendente sollevi st.sop() in assenza di dati/profilo attivo."""
    st.session_state.clear()
    st.session_state["session_cleared"] = True

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        with pytest.raises(StreamlitStopInvoked):
            ensure_portfolio_loaded(module_type="wealth")


@pytest.mark.qa
def test_phase_a_empty_state_guard_blocks_any_module():
    """Verifica che la safe-guard con module_type='any' sollevi st.sop() a sessione vuota."""
    st.session_state.clear()
    st.session_state["session_cleared"] = True

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        with pytest.raises(StreamlitStopInvoked):
            ensure_portfolio_loaded(module_type="any")


@pytest.mark.qa
def test_phase_a_standalone_modules_function_without_portfolio():
    """Verifica che i motori di calcolo standalone operino correttamente senza portafoglio caricato."""
    # 1. Calcolatore Sandbox Risk Engine
    from core.risk_engine import compute_sandbox_risk_bundle
    sandbox_bundle = compute_sandbox_risk_bundle(tickers=["AAPL", "MSFT"], sandbox_name="Test Standalone")
    assert sandbox_bundle is not None
    assert "positions" in sandbox_bundle
    assert len(sandbox_bundle["positions"]) == 2

    # 2. Simulatore Previdenza / Pensione (Pagina 16)
    from core.wealth.wealth_engine import simulate_pension_projection
    pension_sim = simulate_pension_projection(
        current_pot=25000.0,
        monthly_contrib=400.0,
        years_to_retirement=30,
        expected_return_pct=4.5
    )
    assert pension_sim is not None
    assert pension_sim["nominal_pot_median"] > 25000.0
    assert pension_sim["estimated_monthly_annuity_real"] > 0

    # 3. Calcolatore Mutui e Immobiliare (Pagina 19)
    from core.wealth.wealth_engine import compute_mortgage_amortization, compute_real_estate_roi
    mortgage_plan = compute_mortgage_amortization(
        principal=240000.0,
        annual_rate=3.2,
        duration_years=25
    )
    assert mortgage_plan is not None
    assert mortgage_plan["monthly_payment"] > 0
    assert mortgage_plan["total_interest"] > 0

    roi_plan = compute_real_estate_roi(
        property_val=300000.0,
        down_payment=60000.0,
        monthly_rent=1200.0
    )
    assert roi_plan is not None
    assert roi_plan.get("gross_yield_pct", 0.0) > 0

    # 4. Modelli di Pricing Obbligazionario (Fixed Income)
    from core.fixed_income import compute_bond_analytics
    bond_res = compute_bond_analytics(
        face_value=100.0,
        coupon_rate=0.035,
        maturity_years=10.0,
        market_price=98.5
    )
    assert bond_res is not None
    assert bond_res["modified_duration"] > 0


# ==============================================================================
# FASE B: TEST POST-CARICAMENTO PORTAFOGLIO DEMO (5 PILASTRI)
# ==============================================================================

@pytest.mark.qa
def test_phase_b_seed_unified_demo_scenario_integrity():
    """Verifica l'integrità matematica e quantitativa del caricamento del portafoglio demo."""
    demo_bundle = seed_unified_demo_scenario(target_portfolio_name="DEMO_FAMILY_OFFICE")
    assert demo_bundle is not None

    # Verifica posizioni Risk
    positions = demo_bundle.get("positions")
    assert isinstance(positions, pd.DataFrame)
    assert len(positions) == 4
    assert set(positions["ticker"]) == {"VWCE.DE", "AAPL", "ASML.AS", "BTP_10Y"}
    assert positions["current_value"].sum() > 200000.0

    # Verifica metriche quantitative
    metrics = demo_bundle.get("metrics", {})
    mk = metrics.get("market_risk", {})
    assert mk.get("volatility_annual_pct", 0.0) > 5.0
    assert mk.get("var_parametric_95", 0.0) > 0.0
    assert mk.get("cvar_95", 0.0) > 0.0
    assert mk.get("beta", 0.0) > 0.0

    # Verifica Wealth Snapshot a 5 Pilastri
    ws = demo_bundle.get("wealth_snapshot", {})
    assert ws.get("liquid_cash", 0.0) == 95000.0
    assert ws.get("financial_investments", 0.0) == 214950.0
    assert ws.get("physical_assets", 0.0) == 674500.0
    assert ws.get("pension_total", 0.0) == 38000.0
    assert ws.get("liabilities_total", 0.0) == 220000.0
    assert ws.get("total_assets", 0.0) == 1022450.0
    assert ws.get("total_net_worth", 0.0) == 802450.0
    assert ws.get("wealth_health_score", 0.0) >= 85.0

    # Verifica persistenza e calcolo nel database SQLite
    engine = get_engine(database="wealth", offline=True)
    init_wealth_db(engine)
    df_prof = get_wealth_portfolios(engine)
    assert not df_prof.empty
    demo_profiles = df_prof[df_prof["name"] == "DEMO_FAMILY_OFFICE"]
    assert not demo_profiles.empty
    demo_pid = int(demo_profiles.iloc[0]["portfolio_id"])

    df_acc = get_wealth_accounts(engine, portfolio_id=demo_pid)
    assert len(df_acc) >= 3
    df_phys = get_physical_assets(engine, portfolio_id=demo_pid)
    assert len(df_phys) >= 2
    df_pens = get_pension_plans(engine, portfolio_id=demo_pid)
    assert len(df_pens) >= 1

    nw = compute_consolidated_net_worth(engine, portfolio_id=demo_pid)
    assert nw.total_net_worth > 500000.0
    assert nw.liquid_cash > 0.0
    assert nw.physical_assets > 500000.0


@pytest.mark.qa
def test_phase_b_ensure_portfolio_loaded_unblocks_all_modules():
    """Verifica che la safe-guard si sblocchi istantaneamente dopo il seed del portafoglio demo."""
    demo_bundle = seed_unified_demo_scenario(target_portfolio_name="DEMO_FAMILY_OFFICE")
    st.session_state["results"] = demo_bundle
    st.session_state["pipeline_done"] = True
    st.session_state["session_cleared"] = False

    # Risk Module Check (non deve chiamare st.stop)
    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        results_out, has_real = ensure_portfolio_loaded(module_type="risk")
        assert results_out is not None
        assert "positions" in results_out
        assert len(results_out["positions"]) == 4

    # Wealth Module Check (non deve chiamare st.stop)
    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        wealth_ok = ensure_portfolio_loaded(module_type="wealth")
        assert wealth_ok is True

    # Any Module Check (non deve chiamare st.stop)
    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        any_out, ok_flag = ensure_portfolio_loaded(module_type="any")
        assert any_out is not None


# =========================================================================
# FASE B.3: TEST CICLO DI RESET & IDEMPOTENZA (DEMO -> VUOTO -> DEMO)
# ==========================================================================

@pytest.mark.qa
def test_reset_cycle_returns_to_empty_state_and_is_idempotent():
    """Verifica che la transizione Demo -> Reset -> Demo sia pulita, priva di residui e idempotente."""
    # 1. Carica Demo
    seed_unified_demo_scenario(target_portfolio_name="DEMO_FAMILY_OFFICE")
    st.session_state["session_cleared"] = False

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        res, _ = ensure_portfolio_loaded(module_type="risk")
        assert res is not None

    # 2. Esegui Reset Completo di Sessione
    st.session_state["results"] = None
    st.session_state["session_cleared"] = True
    st.session_state["pipeline_done"] = False
    st.session_state["wealth_active_portfolio_id"] = None

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        with pytest.raises(StreamlitStopInvoked):
            ensure_portfolio_loaded(module_type="risk")

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        with pytest.raises(StreamlitStopInvoked):
            ensure_portfolio_loaded(module_type="wealth")

    # 3. Ricarica Demo (Idempotenza del secondo caricamento)
    seed_unified_demo_scenario(target_portfolio_name="DEMO_FAMILY_OFFICE")
    st.session_state["session_cleared"] = False

    with patch("streamlit.stop", side_effect=StreamlitStopInvoked):
        res2, _ = ensure_portfolio_loaded(module_type="risk")
        assert res2 is not None
        wealth_ok2 = ensure_portfolio_loaded(module_type="wealth")
        assert wealth_ok2 is True


# =========================================================================
# TEST RESILIENWA SU DATAFRAME VUOTI / ZERO DATA
# =========================================================================

@pytest.mark.qa
def test_database_and_calculation_resilience_on_empty_structures():
    """Verifica che le funzioni DB e motore non generino eccezioni non gestite su strutture vuote."""
    engine = get_engine(database="wealth", offline=True)
    init_wealth_db(engine)

    # Richiesta conti su ID inesistente
    df_empty_acc = get_wealth_accounts(engine, portfolio_id=999999)
    assert isinstance(df_empty_acc, pd.DataFrame)

    # Richiesta transazioni cashflow su ID inesistente
    df_empty_cf = get_cashflow_records(engine, portfolio_id=999999)
    assert isinstance(df_empty_cf, pd.DataFrame)

    # Calcolo Net Worth su ID inesistente/vuoto
    nw_empty = compute_consolidated_net_worth(engine, portfolio_id=999999)
    assert nw_empty.total_net_worth == 0.0 or isinstance(nw_empty.total_net_worth, float)


@pytest.mark.qa
def test_wealth_module_does_not_auto_select_first_profile():
    """Verifica che al caricamento del modulo Wealth nessun profilo venga imposto automaticamente se non scelto."""
    from core.ui_utils import ensure_portal_context
    from core.wealth.wealth_db import create_wealth_portfolio

    st.session_state["offline_mode"] = True
    st.session_state["db_name"] = "wealth"
    st.session_state["wealth_active_portfolio_id"] = None
    st.session_state.pop("wealth_active_profile_name", None)

    engine = get_engine(database="wealth", offline=True)
    init_wealth_db(engine)
    create_wealth_portfolio(engine, name="Test Profilo Alpha")
    create_wealth_portfolio(engine, name="Test Profilo Beta")

    with patch("core.sidebar.render_sidebar"):
        ctx = ensure_portal_context(module="wealth")

    assert ctx["portfolio_id"] is None
    assert ctx["profile_name"] is None
    assert ctx["net_worth"] is None
    assert st.session_state.get("wealth_active_portfolio_id") is None
    assert len(ctx["profile_map"]) >= 2


@pytest.mark.qa
def test_session_reset_then_risk_then_wealth_selection_flow():
    """
    Test di regressione per il flusso segnalato dall'utente:
    1. Esegue il reset di sessione completo
    2. Naviga nel modulo Risk senza caricare alcun portafoglio
    3. Entra nel modulo Wealth: verifica che nessun profilo (ID #1 o altro) venga selezionato automaticamente.
    """
    from core.sidebar import _execute_full_session_reset, render_sidebar
    from core.ui_utils import ensure_portal_context
    from core.onboarding_guard import ensure_portfolio_loaded
    from core.workspace_context import WorkspaceContext

    # 1. Reset di sessione completo
    with patch("streamlit.rerun"), patch("streamlit.switch_page"):
        _execute_full_session_reset(is_wealth_mode=False)

    assert st.session_state.get("wealth_active_portfolio_id") is None
    ws_ctx = WorkspaceContext.get_current()
    assert ws_ctx.wealth.profile_id is None

    # 2. Entra nel modulo Risk senza caricare dati
    st.session_state["argus_portal_mode"] = "📊 Risk Analytics"
    with patch("streamlit.stop"), patch("core.onboarding_guard.render_empty_state_screen"):
        ensure_portfolio_loaded(module_type="risk")

    assert st.session_state.get("wealth_active_portfolio_id") is None
    assert WorkspaceContext.get_current().wealth.profile_id is None

    # 3. Entra nel modulo Wealth
    st.session_state["argus_portal_mode"] = "🏛️ Wealth Management"
    with patch("core.sidebar.render_sidebar"):
        ctx = ensure_portal_context(module="wealth")

    assert ctx["portfolio_id"] is None
    assert ctx["profile_name"] is None
    assert st.session_state.get("wealth_active_portfolio_id") is None
    assert WorkspaceContext.get_current().wealth.profile_id is None


def test_splash_screen_not_active_on_cold_start_or_risk_launch():
    """Verifica che al primo avvio del modulo Risk lo splash screen non si attivi automaticamente provocando sfarfallii."""
    from unittest.mock import MagicMock
    from core.ui_utils import render_splash_screen

    # 1. Cold start: session_state vuoto senza 'splash_dismissed'
    st.session_state.clear()
    assert "splash_dismissed" not in st.session_state

    # 2. Control Room calcola is_splash_active
    is_splash_active = not st.session_state.get("splash_dismissed", True)
    assert is_splash_active is False, "Al cold start is_splash_active deve essere False!"

    # 3. render_splash_screen() deve restituire False senza bloccare il caricamento
    with patch("streamlit.markdown"), patch("streamlit.columns"):
        is_active = render_splash_screen()
    assert is_active is False
    assert st.session_state.get("splash_dismissed") is True

    # 4. Richiesta esplicita manuale da sidebar ("Schermata di Avvio")
    st.session_state["splash_dismissed"] = False
    with patch("streamlit.markdown"), patch("streamlit.columns", return_value=(MagicMock(), MagicMock())):
        is_active_manual = render_splash_screen()
    assert is_active_manual is True, "Se richiesto esplicitamente lo splash deve attivarsi!"
