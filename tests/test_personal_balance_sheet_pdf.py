# ============================================================
# tests/test_personal_balance_sheet_pdf.py
# ARGUS — Unit Tests for Personal Balance Sheet PDF & HTML Export Engine
# ============================================================

from unittest.mock import patch
import pytest
from core.fetcher import get_engine
from core.wealth.personal_balance_sheet import (
    compute_personal_balance_sheet,
    generate_personal_balance_sheet_html,
    generate_personal_balance_sheet_pdf,
    generate_personal_balance_sheet_tearsheet_html,
    generate_personal_balance_sheet_tearsheet_pdf,
)


@pytest.fixture(scope="module")
def engine():
    return get_engine()


def test_generate_personal_balance_sheet_html(engine):
    html = generate_personal_balance_sheet_html(engine, portfolio_id=1)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "ARGUS WEALTH MANAGEMENT" in html
    assert "ATTIVO (IMPIEGHI)" in html
    assert "PASSIVO" in html
    assert "PATRIMONIO NETTO" in html
    assert "CONTO ECONOMICO DI GESTIONE" in html
    assert "INDICI DI BILANCIO" in html
    assert "Solvibilit" in html
    assert "BILANCIO COMPARATIVO PLURIENNALE" in html
    assert "Pagina 1 di 4" in html
    assert "Pagina 4 di 4" in html


def test_generate_personal_balance_sheet_tearsheet_html(engine):
    html = generate_personal_balance_sheet_tearsheet_html(engine, portfolio_id=1)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Tear-Sheet Contabile" in html
    assert "ATTIVO PATRIMONIALE" in html
    assert "Conto Economico" in html
    assert "CFP Standards" in html


def test_generate_personal_balance_sheet_pdf(engine):
    pdf = generate_personal_balance_sheet_pdf(engine, portfolio_id=1)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 10000
    assert pdf.startswith(b"%PDF-")


def test_generate_personal_balance_sheet_tearsheet_pdf(engine):
    pdf = generate_personal_balance_sheet_tearsheet_pdf(engine, portfolio_id=1)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000
    assert pdf.startswith(b"%PDF-")


def test_personal_balance_sheet_reportlab_fallback(engine):
    with patch("core.wealth.personal_balance_sheet._convert_html_to_pdf", return_value=None):
        pdf = generate_personal_balance_sheet_pdf(engine, portfolio_id=1)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        assert pdf.startswith(b"%PDF-")


def test_personal_balance_sheet_tearsheet_reportlab_fallback(engine):
    with patch("core.wealth.personal_balance_sheet._convert_html_to_pdf", return_value=None):
        pdf = generate_personal_balance_sheet_tearsheet_pdf(engine, portfolio_id=1)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        assert pdf.startswith(b"%PDF-")
