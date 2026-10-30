"""
ARGUS Unified Dialogs & Action Drawers Hub
==========================================
Single entrypoint consolidating all modal workflows under native Streamlit @st.dialog:
- Pre-Trade Execution & Staging Blotter Drawers (from components/action_drawers.py)
- Institutional Confirmation Dialogs (from components/ui_core/confirm_dialogs.py)
- Wealth & Financial Planning Methodology Modals (from core/wealth/wealth_modals.py)
- 5-Block CFA/FRM Educational Modal Engine (replaces legacy HTML/CSS checkbox hacks)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Sequence

import streamlit as st

# 1. Action Drawers
from components.action_drawers import (
    render_lot_inspector_dialog,
    render_order_blotter_dialog,
    render_risk_decomposition_dialog,
)

# 2. Confirmation Dialogs
from components.ui_core.confirm_dialogs import (
    confirm_clear_watchlist_dialog,
    confirm_delete_portfolio_profile_dialog,
    confirm_delete_snapshot_dialog,
    confirm_delete_wealth_account_dialog,
    confirm_delete_wealth_goal_dialog,
    confirm_delete_wealth_portfolio_dialog,
    confirm_delete_wealth_snapshot_dialog,
    confirm_flush_cache_dialog,
    confirm_reset_bquant_snippet_dialog,
    confirm_reset_session_dialog,
    confirm_reset_spotlight_cache_dialog,
    confirm_unlink_risk_portfolio_dialog,
)

# 3. Wealth Methodology Modals
from core.wealth.wealth_modals import (
    render_ai_health_score_modal,
    render_balance_sheet_methodology_modal,
    render_budget_rule_methodology_modal,
    render_fiscal_methodology_modal,
    render_goal_methodology_modal,
    render_illiquids_methodology_modal,
    render_real_estate_methodology_modal,
    render_succession_methodology_modal,
    render_wealth_methodology_modal,
)

logger = logging.getLogger("argus.dialogs")


# ── 4. CFA/FRM 5-Block Educational Dialog Engine ──────────────────────────────
@st.dialog("📚 Metodologia & Specifiche Quantitative (CFA / FRM)", width="large")
def render_institutional_educational_dialog(
    title: str,
    what_is: str,
    formula: Optional[str] = None,
    interpretation: Optional[str] = None,
    implementation: Optional[str] = None,
    limitations: Optional[str] = None,
    code_reference: Optional[str] = None,
) -> None:
    """
    Modale educativo istituzionale strutturato sui 5 blocchi prescritti in docs/DESIGN.md:
    1. Cos'è (Definizione & Intuizione Finanziaria)
    2. Formula Matematica (LaTeX / KaTeX)
    3. Come Interpretarlo & Benchmark Istituzionali
    4. Implementazione nel Codice & Metodologia
    5. Limiti, Trappole & Falsi Segnali
    """
    st.subheader(f"📌 {title}")

    st.markdown("#### 1. Definizione Formale & Intuizione")
    st.markdown(what_is)

    if formula:
        st.markdown("#### 2. Formula Matematica")
        st.latex(formula)

    if interpretation:
        st.markdown("#### 3. Interpretazione & Benchmark Istituzionali")
        st.markdown(interpretation)

    if implementation or code_reference:
        st.markdown("#### 4. Metodologia nel Codice")
        if implementation:
            st.markdown(implementation)
        if code_reference:
            st.caption(f"📁 Modulo di riferimento: `{code_reference}`")

    if limitations:
        st.markdown("#### 5. Limiti & Assunzioni di Stress")
        st.warning(limitations)


__all__ = [
    # Action Drawers
    "render_order_blotter_dialog",
    "render_lot_inspector_dialog",
    "render_risk_decomposition_dialog",
    # Confirmation Dialogs
    "confirm_delete_snapshot_dialog",
    "confirm_reset_session_dialog",
    "confirm_delete_portfolio_profile_dialog",
    "confirm_flush_cache_dialog",
    "confirm_delete_wealth_portfolio_dialog",
    "confirm_delete_wealth_snapshot_dialog",
    "confirm_delete_wealth_account_dialog",
    "confirm_unlink_risk_portfolio_dialog",
    "confirm_delete_wealth_goal_dialog",
    "confirm_clear_watchlist_dialog",
    "confirm_reset_spotlight_cache_dialog",
    "confirm_reset_bquant_snippet_dialog",
    # Wealth Modals
    "render_wealth_methodology_modal",
    "render_balance_sheet_methodology_modal",
    "render_budget_rule_methodology_modal",
    "render_illiquids_methodology_modal",
    "render_goal_methodology_modal",
    "render_real_estate_methodology_modal",
    "render_fiscal_methodology_modal",
    "render_succession_methodology_modal",
    "render_ai_health_score_modal",
    # Educational Engine
    "render_institutional_educational_dialog",
]
