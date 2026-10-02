"""
Unit tests for ARGUS Centralized Confirmation Dialogs Hub
==========================================================
Verifica che tutte le funzioni di cancellazione, eliminazione, reset e pulizia
siano protette dai modali di conferma e conformi all'architettura istituzionale.
"""

from unittest.mock import MagicMock

import core.confirm_dialogs as cd


def _unwrap(func):
    """Estrae la funzione sottostante bypassando il wrapper browser di @st.dialog."""
    return getattr(func, "__wrapped__", func)


def test_confirm_dialogs_exports():
    """Verifica che tutte le funzioni modali di sicurezza siano esportate correttamente."""
    expected_dialogs = [
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
    ]

    for name in expected_dialogs:
        assert hasattr(cd, name), f"La funzione modale '{name}' deve essere esportata da core.confirm_dialogs"
        fn = getattr(cd, name)
        assert callable(fn), f"'{name}' deve essere un callable"


def test_confirm_delete_snapshot_dialog_render(monkeypatch):
    """Verifica il rendering e la logica del modale di conferma cancellazione snapshot."""
    import streamlit as st

    mock_engine = MagicMock()
    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_delete_snapshot_dialog)
    fn(mock_engine, "RUN-TEST-001", "Portafoglio Alpha", 101)

    combined_html = " ".join(rendered_markdowns)
    assert "RUN-TEST-001" in combined_html
    assert "Portafoglio Alpha" in combined_html
    assert "101" in combined_html


def test_confirm_reset_session_dialog_render(monkeypatch):
    """Verifica il rendering del modale di reset sessione attiva."""
    import streamlit as st

    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_reset_session_dialog)
    fn(portfolio_name="Master Wealth", run_id="OAD-MW-2026")

    combined_html = " ".join(rendered_markdowns)
    assert "Master Wealth" in combined_html
    assert "OAD-MW-2026" in combined_html


def test_confirm_delete_wealth_portfolio_dialog_render(monkeypatch):
    """Verifica il modale di cancellazione profilo patrimoniale con avvertimento critico."""
    import streamlit as st

    mock_engine = MagicMock()
    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_delete_wealth_portfolio_dialog)
    fn(mock_engine, 42, "Holding Famiglia Rossi")

    combined_html = " ".join(rendered_markdowns)
    assert "Holding Famiglia Rossi" in combined_html
    assert "42" in combined_html
    assert "OPERAZIONE DISTRUTTIVA IRREVERSIBILE" in combined_html


def test_confirm_delete_wealth_account_dialog_render(monkeypatch):
    """Verifica il modale di eliminazione conto bancario con saldo."""
    import streamlit as st

    mock_engine = MagicMock()
    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_delete_wealth_account_dialog)
    fn(mock_engine, 99, "Conto Corrente Premium", "Fineco Bank", 45000.0)

    combined_html = " ".join(rendered_markdowns)
    assert "Conto Corrente Premium" in combined_html
    assert "Fineco Bank" in combined_html
    assert "45,000.00" in combined_html


def test_confirm_delete_wealth_goal_dialog_render(monkeypatch):
    """Verifica il modale di eliminazione obiettivo FIRE."""
    import streamlit as st

    mock_engine = MagicMock()
    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_delete_wealth_goal_dialog)
    fn(mock_engine, 7, "Fondo Pensione Integrativo", 150000.0)

    combined_html = " ".join(rendered_markdowns)
    assert "Fondo Pensione Integrativo" in combined_html
    assert "150,000.00" in combined_html


def test_confirm_clear_watchlist_dialog_render(monkeypatch):
    """Verifica il modale di svuotamento watchlist screener."""
    import streamlit as st

    rendered_markdowns = []
    monkeypatch.setattr(st, "markdown", lambda content, unsafe_allow_html=False: rendered_markdowns.append(content))
    monkeypatch.setattr(st, "columns", lambda spec: (MagicMock(), MagicMock()))
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)

    fn = _unwrap(cd.confirm_clear_watchlist_dialog)
    fn(15)

    combined_html = " ".join(rendered_markdowns)
    assert "15 titoli" in combined_html
