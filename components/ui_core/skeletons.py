"""
ARGUS Institutional Skeleton Loaders & Transition State Engine
==============================================================
Provides high-performance, non-blocking skeleton shimmer animations and state barriers:
- Anti-CLS (Cumulative Layout Shift) container dimension locks
- Pre-render skeleton cards, tables, and chart placeholders
- Graceful transition overlays and debounced computation triggers
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Sequence, Union

import streamlit as st

# Re-export core primitives from loading_states for unified single-module access
from components.ui_core.loading_states import (
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

logger = logging.getLogger("argus.skeletons")


def render_skeleton_cards(n_cards: int = 4) -> None:
    """Renderizza placeholder scheletrati per KPI Cards in griglia orizzontale."""
    cols = st.columns(n_cards)
    for c in cols:
        with c:
            st.markdown(
                """
                <div class="argus-skeleton" style="height: 92px; border-radius: 10px; margin-bottom: 8px;"></div>
                """,
                unsafe_allow_html=True,
            )


def render_skeleton_table(n_rows: int = 5, n_cols: int = 4) -> None:
    """Renderizza placeholder scheletrato per tabelle dati e datagrid."""
    render_table_skeleton(rows=n_rows, cols=n_cols)


def render_skeleton_chart(height: int = 340, title: str = "Caricamento Grafico...") -> None:
    """Renderizza placeholder scheletrato per visualizzazioni grafiche Plotly."""
    render_chart_skeleton(height=height, title=title)


__all__ = [
    "AtomicViewSlot",
    "atomic_computation",
    "computation_barrier",
    "debounce_trigger",
    "inject_loading_css",
    "is_computing",
    "render_chart_skeleton",
    "render_dashboard_skeleton",
    "render_kpi_skeleton",
    "render_table_skeleton",
    "render_transition_overlay",
    "set_computing_state",
    "switch_to_page_with_transition",
    "render_skeleton_cards",
    "render_skeleton_table",
    "render_skeleton_chart",
]
