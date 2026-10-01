"""
ARGUS — Loading & Transition States Automated QA Test Suite
===========================================================
Validates:
1. Concurrency Locking & Input Disabling (is_computing, set_computing_state)
2. Debounce Triggering & Double-Click Protection
3. computation_barrier Context Manager (Lifecycle, exception resilience, container clearing)
4. @atomic_computation Decorator
5. AtomicViewSlot (Empty -> Skeleton -> Render)
6. Shimmer Skeletons & Transition Overlay Rendering
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

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

from core.loading_states import (
    AtomicViewSlot,
    atomic_computation,
    computation_barrier,
    debounce_trigger,
    inject_loading_css,
    is_computing,
    render_chart_skeleton,
    render_dashboard_skeleton,
    render_kpi_skeleton,
    render_table_skeleton,
    render_transition_overlay,
    set_computing_state,
    switch_to_page_with_transition,
)


@pytest.fixture(autouse=True)
def clean_loading_session():
    """Garantisce un session_state pulito prima e dopo ciascun test."""
    st.session_state.clear()
    yield
    st.session_state.clear()


class TestLoadingStatesArchitecture:
    """Suite di test per la validazione di loading states, skeleton e locking di computazione."""

    def test_is_computing_and_set_computing_state(self):
        """Verifica il corretto tracciamento dei flag di calcolo attivo sia locale che globale."""
        assert is_computing() is False
        assert is_computing("opt_engine") is False

        # Attiva lock per calcolo specifico
        set_computing_state("opt_engine", True)
        assert is_computing("opt_engine") is True
        assert is_computing() is True  # Global computing active

        # Un altro calcolo non attivo
        assert is_computing("monte_carlo") is False

        # Rilascio lock
        set_computing_state("opt_engine", False)
        assert is_computing("opt_engine") is False
        assert is_computing() is False

    def test_debounce_trigger_rapid_clicks_guard(self):
        """Verifica che il debounce blocchi click multipli e ravvicinati entro il cooldown."""
        key = "btn_submit_order"
        
        # 1. Primo click consentito
        assert debounce_trigger(key, cooldown_seconds=1.0) is True

        # 2. Secondo click immediato (bloccato)
        assert debounce_trigger(key, cooldown_seconds=1.0) is False

        # 3. Terzo click dopo finta avanzata temporale
        with patch("core.loading_states.time.time", return_value=time.time() + 2.0):
            assert debounce_trigger(key, cooldown_seconds=1.0) is True

    def test_computation_barrier_lifecycle_and_exception_resilience(self):
        """Verifica che computation_barrier attivi il lock e garantisca il rilascio in caso di eccezione."""
        mock_container = MagicMock()

        assert is_computing("heavy_task") is False

        # Esecuzione standard
        with computation_barrier(
            key="heavy_task",
            label="Calcolo frontiera...",
            container=mock_container,
            skeleton_type="chart",
        ):
            assert is_computing("heavy_task") is True
            assert is_computing() is True
            assert mock_container.empty.call_count >= 1

        # Post-esecuzione: lock rilasciato e container ripulito per il render
        assert is_computing("heavy_task") is False
        assert is_computing() is False
        assert mock_container.empty.call_count >= 2

        # Resilienza a eccezioni
        try:
            with computation_barrier(key="failing_task", label="Calcolo fallito..."):
                assert is_computing("failing_task") is True
                raise RuntimeError("Simulated Computation Crash")
        except RuntimeError:
            pass

        # Il lock DEVE essere rilasciato anche dopo crash
        assert is_computing("failing_task") is False
        assert is_computing() is False

    def test_atomic_computation_decorator(self):
        """Verifica che @atomic_computation incapsuli la funzione con il lock."""
        @atomic_computation(key="decorated_calc", label="Decorated running...")
        def sample_calc(x, y):
            assert is_computing("decorated_calc") is True
            return x + y

        assert is_computing("decorated_calc") is False
        res = sample_calc(10, 20)
        assert res == 30
        assert is_computing("decorated_calc") is False

    def test_atomic_view_slot_lifecycle(self):
        """Verifica il comportamento del gestore di slot atomico."""
        mock_empty = MagicMock()
        with patch("streamlit.empty", return_value=mock_empty):
            slot = AtomicViewSlot(key="test_slot")
            
            # Svuotamento
            slot.clear()
            assert mock_empty.empty.call_count == 1

            # Montaggio skeleton
            slot.mount_skeleton(skeleton_type="kpi", count=3)
            assert mock_empty.empty.call_count >= 2

            # Render definitivo
            def fake_render(text):
                return f"rendered: {text}"

            result = slot.render(fake_render, "final_data")
            assert result == "rendered: final_data"

    def test_skeleton_and_overlay_rendering(self):
        """Verifica che le funzioni di rendering HTML iniettino i mockup visivi corretti."""
        with patch("streamlit.markdown") as spy_md:
            inject_loading_css()
            assert spy_md.call_count >= 1

            render_kpi_skeleton(count=3)
            render_table_skeleton(rows=3, cols=2)
            render_chart_skeleton(height=300)
            render_dashboard_skeleton()
            render_transition_overlay(title="Loading Test", subtitle="Subtitle Test")

            assert spy_md.call_count >= 6
