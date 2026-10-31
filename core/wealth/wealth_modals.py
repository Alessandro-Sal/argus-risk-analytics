"""ARGUS — Compatibility Proxy for Wealth Methodology Modals.

Relocated to components.ui_core.dialogs_and_drawers for clean headless architecture.
core/wealth is 100% UI-free and headless.
All functions are re-exported here for 100% backward compatibility.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'core.wealth.wealth_modals' is deprecated. "
    "Please import from 'components.ui_core.dialogs_and_drawers' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from components.ui_core.dialogs_and_drawers import (  # noqa: F401
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

__all__ = [
    "render_wealth_methodology_modal",
    "render_balance_sheet_methodology_modal",
    "render_budget_rule_methodology_modal",
    "render_illiquids_methodology_modal",
    "render_goal_methodology_modal",
    "render_real_estate_methodology_modal",
    "render_fiscal_methodology_modal",
    "render_succession_methodology_modal",
    "render_ai_health_score_modal",
]
