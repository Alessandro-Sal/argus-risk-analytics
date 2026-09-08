# ============================================================
# tests/test_personal_balance_sheet.py
# ARGUS — Tests for Personal Balance Sheet & Financial Statements
# ============================================================

import pytest
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

from core.wealth.personal_balance_sheet import compute_personal_balance_sheet
from core.fetcher import get_engine


def test_personal_balance_sheet_real_db():
    """Verifica il calcolo del bilancio personale sul database di produzione/locale."""
    engine = get_engine()
    res = compute_personal_balance_sheet(engine, portfolio_id=1, year=2026)

    assert "stato_patrimoniale" in res
    assert "conto_economico" in res
    assert "indici_bilancio" in res

    sp = res["stato_patrimoniale"]
    tot_attivo = sp["attivo"]["totale_attivo"]
    tot_passivo = sp["passivo"]["totale_passivo"]
    patrimonio_netto = sp["patrimonio_netto"]["totale_patrimonio_netto"]
    tot_pareggio = sp["pareggio"]["totale_pareggio"]

    # 1. Quadratura contabile perfetta: Attivo == Passivo + Patrimonio Netto
    assert sp["pareggio"]["is_quadrato"] is True
    assert abs(tot_attivo - (tot_passivo + patrimonio_netto)) < 0.01
    assert abs(tot_attivo - tot_pareggio) < 0.01

    # 2. Sezioni Attivo
    assert len(sp["attivo"]["sezioni"]) >= 4
    for sez in sp["attivo"]["sezioni"]:
        assert "codice" in sez
        assert "titolo" in sez
        assert "totale" in sez
        assert "incidenza_pct" in sez

    # 3. Conto Economico 2026
    ce = res["conto_economico"]
    assert ce["anno"] == 2026
    assert ce["totale_entrate"] > 0
    assert ce["totale_uscite"] > 0
    expected_savings = round(ce["totale_entrate"] - ce["totale_uscite"], 2)
    assert abs(ce["risparmio_netto"] - expected_savings) < 0.01
    assert "allocazione_capitale" in ce
    assert "waterfall_data" in ce

    # 4. Indici di bilancio
    ind = res["indici_bilancio"]
    assert "solvency_ratio" in ind
    assert "debt_to_assets" in ind
    assert "emergency_runway" in ind
    assert "savings_rate" in ind
    assert "dsti" in ind
    assert "invested_assets_ratio" in ind
    assert "overall_rating" in ind

    assert ind["solvency_ratio"]["status"] in ["OPTIMAL", "ACCEPTABLE", "WARNING"]
    assert ind["debt_to_assets"]["status"] in ["OPTIMAL", "ACCEPTABLE", "WARNING"]
    assert ind["emergency_runway"]["status"] in ["OPTIMAL", "ACCEPTABLE", "WARNING"]


def test_personal_balance_sheet_multi_year():
    """Verifica il calcolo del bilancio su anni storici diversi."""
    engine = get_engine()
    res_2025 = compute_personal_balance_sheet(engine, portfolio_id=1, year=2025)
    res_2024 = compute_personal_balance_sheet(engine, portfolio_id=1, year=2024)

    assert res_2025["conto_economico"]["anno"] == 2025
    assert res_2024["conto_economico"]["anno"] == 2024

    assert res_2025["conto_economico"]["totale_entrate"] > 0
    assert res_2024["conto_economico"]["totale_entrate"] > 0
    assert res_2025["stato_patrimoniale"]["pareggio"]["is_quadrato"] is True
    assert res_2024["stato_patrimoniale"]["pareggio"]["is_quadrato"] is True


def test_personal_balance_sheet_empty_mock_db():
    """Verifica resilienza del motore su un database completamente vuoto (zero division test)."""
    from core.wealth.wealth_db import init_wealth_db
    mock_engine = create_engine("sqlite:///:memory:")
    init_wealth_db(mock_engine)

    res = compute_personal_balance_sheet(mock_engine, portfolio_id=999, year=2026)

    assert res["stato_patrimoniale"]["attivo"]["totale_attivo"] == 0.0
    assert res["stato_patrimoniale"]["passivo"]["totale_passivo"] == 0.0
    assert res["stato_patrimoniale"]["patrimonio_netto"]["totale_patrimonio_netto"] == 0.0
    assert res["stato_patrimoniale"]["pareggio"]["is_quadrato"] is True
    assert res["conto_economico"]["totale_entrate"] == 0.0
    assert res["conto_economico"]["totale_uscite"] == 0.0
    assert res["indici_bilancio"]["solvency_ratio"]["valore"] == 100.0

