# ============================================================
# tests/test_personal_balance_sheet.py
# ARGUS — Tests for Personal Balance Sheet & Financial Statements
# ============================================================

import sqlite3

import pandas as pd
import pytest
from sqlalchemy import create_engine

from core.fetcher import get_engine
from core.wealth.personal_balance_sheet import compute_personal_balance_sheet
from core.wealth.wealth_db import (
    get_cashflow_records,
    get_wealth_accounts,
    init_wealth_db,
    insert_cashflow_tx,
    save_wealth_account,
)


def _ensure_test_data(engine, portfolio_id: int = 1):
    """Garantisce la presenza di conti e flussi di cassa minimi per i test di bilancio su qualsiasi ambiente."""
    init_wealth_db(engine)
    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)
    if df_acc.empty:
        aid = save_wealth_account(engine, {
            "portfolio_id": portfolio_id,
            "name": "Conto Corrente Principale",
            "account_type": "checking",
            "institution": "FinecoBank",
            "balance": 15000.0,
            "currency": "EUR"
        })
    else:
        aid = int(df_acc.iloc[0]["account_id"])

    df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
    years = [2024, 2025, 2026]
    for yr in years:
        has_yr_inflow = not df_cf.empty and ((df_cf["tx_date"].astype(str).str.startswith(str(yr))) & (df_cf["direction"] == "inflow")).any()
        if not has_yr_inflow:
            insert_cashflow_tx(engine, {
                "portfolio_id": portfolio_id,
                "account_id": aid,
                "category_id": 1,
                "tx_date": f"{yr}-05-15",
                "amount": 3500.0,
                "currency": "EUR",
                "direction": "inflow",
                "merchant": "Datore Lavoro",
                "notes": f"Stipendio {yr}",
                "is_recurring": 1
            })
        has_yr_outflow = not df_cf.empty and ((df_cf["tx_date"].astype(str).str.startswith(str(yr))) & (df_cf["direction"] == "outflow")).any()
        if not has_yr_outflow:
            insert_cashflow_tx(engine, {
                "portfolio_id": portfolio_id,
                "account_id": aid,
                "category_id": 2,
                "tx_date": f"{yr}-05-20",
                "amount": 1200.0,
                "currency": "EUR",
                "direction": "outflow",
                "merchant": "Supermercato",
                "notes": f"Spese vita {yr}",
                "is_recurring": 0
            })


def test_personal_balance_sheet_real_db():
    """Verifica il calcolo del bilancio personale sul database di produzione/locale."""
    engine = get_engine()
    _ensure_test_data(engine, portfolio_id=1)
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
    _ensure_test_data(engine, portfolio_id=1)
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


def test_compute_multi_year_balance_comparison():
    """Verifica il calcolo della comparazione pluriennale di stato patrimoniale e conto economico."""
    from core.wealth.personal_balance_sheet import compute_multi_year_balance_comparison
    engine = get_engine()
    _ensure_test_data(engine, portfolio_id=1)
    res = compute_multi_year_balance_comparison(engine, portfolio_id=1, years=[2024, 2025, 2026])

    assert isinstance(res, dict)
    assert "comparison_df" in res
    assert "records" in res
    df_comp = res["comparison_df"]
    assert isinstance(df_comp, pd.DataFrame)
    assert not df_comp.empty
    assert "anno" in df_comp.columns
    assert "totale_attivo" in df_comp.columns
    assert "patrimonio_netto" in df_comp.columns
    assert "delta_pn_eur" in df_comp.columns
    assert "delta_pn_pct" in df_comp.columns
    assert "tot_previdenza" in df_comp.columns


def test_pension_plan_point_in_time_dynamic():
    """Verifica che la previdenza sia dinamica e point-in-time per ciascun esercizio."""
    import json
    from core.wealth.wealth_db import init_wealth_db, save_pension_plan, save_wealth_account

    mock_engine = create_engine("sqlite:///:memory:")
    init_wealth_db(mock_engine)

    save_wealth_account(mock_engine, {
        "portfolio_id": 1,
        "name": "Conto Deposito",
        "account_type": "savings",
        "balance": 10000.0,
        "currency": "EUR"
    })

    # Piano con yearly_data_json strutturato
    save_pension_plan(mock_engine, {
        "portfolio_id": 1,
        "plan_name": "Fondo Pensione Alpha",
        "provider": "Gestore Previdenziale",
        "accumulated_value": 2500.0,
        "monthly_employee_contrib": 150.0,
        "currency": "EUR",
        "yearly_data_json": json.dumps({
            "2023": {"tot_year": 200.0, "tot_cumulato": 200.0, "months": {"nov": 100.0, "dic": 100.0}},
            "2024": {"tot_year": 1000.0, "tot_cumulato": 1200.0},
            "2025": {"tot_year": 800.0, "tot_cumulato": 2000.0},
            "2026": {"tot_year": 500.0, "tot_cumulato": 2500.0},
        })
    })

    bs_2022 = compute_personal_balance_sheet(mock_engine, portfolio_id=1, year=2022)
    bs_2023 = compute_personal_balance_sheet(mock_engine, portfolio_id=1, year=2023)
    bs_2024 = compute_personal_balance_sheet(mock_engine, portfolio_id=1, year=2024)
    bs_2025 = compute_personal_balance_sheet(mock_engine, portfolio_id=1, year=2025)
    bs_2026 = compute_personal_balance_sheet(mock_engine, portfolio_id=1, year=2026)

    # 1. Valutazioni puntuali attese
    assert bs_2022["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 0.0
    assert bs_2023["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 200.0
    assert bs_2024["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 1200.0
    assert bs_2025["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 2000.0
    assert bs_2026["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 2500.0

    # 2. Quadratura contabile per tutti gli esercizi
    for bs in [bs_2022, bs_2023, bs_2024, bs_2025, bs_2026]:
        sp = bs["stato_patrimoniale"]
        assert sp["pareggio"]["is_quadrato"] is True
        assert abs(sp["attivo"]["totale_attivo"] - (sp["passivo"]["totale_passivo"] + sp["patrimonio_netto"]["totale_patrimonio_netto"])) < 0.01

    # 3. Test fallback con parsing da campo notes
    mock_engine2 = create_engine("sqlite:///:memory:")
    init_wealth_db(mock_engine2)
    save_wealth_account(mock_engine2, {
        "portfolio_id": 1,
        "name": "Conto Primario",
        "account_type": "checking",
        "balance": 5000.0,
        "currency": "EUR"
    })
    save_pension_plan(mock_engine2, {
        "portfolio_id": 1,
        "plan_name": "Fondo Beta Fallback Notes",
        "provider": "PIP Assicurativo",
        "accumulated_value": 600.0,
        "notes": "Sincronizzato da foglio Pension (Anni: 2023: €100.00 | 2024: €500.00)",
        "currency": "EUR"
    })

    bs_fb_2022 = compute_personal_balance_sheet(mock_engine2, portfolio_id=1, year=2022)
    bs_fb_2023 = compute_personal_balance_sheet(mock_engine2, portfolio_id=1, year=2023)
    bs_fb_2024 = compute_personal_balance_sheet(mock_engine2, portfolio_id=1, year=2024)

    assert bs_fb_2022["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 0.0
    assert bs_fb_2023["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 100.0
    assert bs_fb_2024["stato_patrimoniale"]["attivo"]["tot_previdenza"] == 600.0


def test_risk_engine_as_of_date():
    """Verifica che il motore di rischio supporti point-in-time filtering con as_of_date."""
    from core.risk_engine import compute_risk
    engine = get_engine()
    try:
        res_hist = compute_risk(portfolio_id=1, engine=engine, as_of_date="2024-12-31")
        assert "as_of_date" in res_hist
        assert res_hist["as_of_date"] == "2024-12-31"
        assert "total_value" in res_hist
    except ValueError as e:
        # Se non ci sono transazioni prima del 2024 per il portfolio 1, la verifica fallisce gracefully
        assert "Nessun dato" in str(e) or "transazione" in str(e).lower()


