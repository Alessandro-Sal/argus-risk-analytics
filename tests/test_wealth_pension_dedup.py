# ============================================================
# tests/test_wealth_pension_dedup.py
# Unit tests for pension plan deduplication, deletion, and Net Worth integrity
# ============================================================

import json

from sqlalchemy import create_engine

from core.wealth.wealth_db import (
    deduplicate_pension_plans,
    delete_pension_plan,
    get_pension_plans,
    init_wealth_db,
    save_pension_plan,
)
from core.wealth.wealth_engine import compute_consolidated_net_worth


def test_pension_plan_save_and_delete():
    """Verifica il salvataggio e la cancellazione singola di un fondo pensione."""
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    pid = save_pension_plan(engine, {
        "portfolio_id": 1,
        "plan_name": "Credemvita Previdenza",
        "provider": "Credemvita S.p.A.",
        "accumulated_value": 3916.31,
        "monthly_employee_contrib": 138.18,
        "tax_deductible_annual": 1243.62,
    })
    assert pid is not None

    df = get_pension_plans(engine, portfolio_id=1)
    assert len(df) == 1
    assert df.iloc[0]["plan_name"] == "Credemvita Previdenza"

    ok = delete_pension_plan(engine, pid)
    assert ok is True

    df_after = get_pension_plans(engine, portfolio_id=1)
    assert df_after.empty


def test_pension_plan_deduplication_and_net_worth_integrity():
    """
    Simula lo scenario reale in cui esistevano contemporaneamente due piani per lo stesso fondo:
    1. 'Fondo Pensione Integrativo (GSheets)' con € 4,056.46
    2. 'Credemvita Previdenza' con € 3,916.31
    Verifica che deduplicate_pension_plans mantenga il piano aggiornato,
    standardizzi la denominazione su 'Credemvita Previdenza' ed elimini il duplicato obsoleto,
    garantendo che il Net Worth consolidato non raddoppi il montante.
    """
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    # Inserimento del piano storico da GSheets
    id1 = save_pension_plan(engine, {
        "portfolio_id": 1,
        "plan_name": "Fondo Pensione Integrativo (GSheets)",
        "provider": "Fondo Aperto / PIP",
        "accumulated_value": 4056.46,
        "monthly_employee_contrib": 138.38,
        "tax_deductible_annual": 1383.77,
        "investment_line": "Azionario / Crescita",
        "yearly_data_json": json.dumps({"2026": {"tot_year": 1383.77, "tot_cumulato": 4056.46}}),
    })

    # Inserimento del secondo piano censito con nome Credemvita
    id2 = save_pension_plan(engine, {
        "portfolio_id": 1,
        "plan_name": "Credemvita Previdenza",
        "provider": "Credemvita S.p.A.",
        "accumulated_value": 3916.31,
        "monthly_employee_contrib": 138.18,
        "tax_deductible_annual": 1243.62,
        "investment_line": "Credemvita Azionario / Crescita",
        "yearly_data_json": json.dumps({"2026": {"tot_year": 1243.62, "tot_cumulato": 3916.31}}),
    })

    # Prima della deduplicazione: due piani presenti, montante raddoppiato (€ 7,972.77)
    df_before = get_pension_plans(engine, portfolio_id=1)
    assert len(df_before) == 2
    assert round(df_before["accumulated_value"].sum(), 2) == 7972.77

    nw_before = compute_consolidated_net_worth(engine, portfolio_id=1)
    assert round(nw_before.pension_total, 2) == 7972.77

    # Esecuzione deduplicazione automatica
    res = deduplicate_pension_plans(engine, portfolio_id=1)
    assert res["deduplicated"] is True
    assert id1 in [res["retained_id"]] or id2 in [res["retained_id"]]
    assert len(res["deleted_ids"]) == 1

    # Dopo la deduplicazione: esattamente un piano, valore corretto (€ 4,056.46), nome canonico 'Credemvita Previdenza'
    df_after = get_pension_plans(engine, portfolio_id=1)
    assert len(df_after) == 1
    retained = df_after.iloc[0]
    assert retained["plan_name"] == "Credemvita Previdenza"
    assert retained["provider"] == "Credemvita S.p.A."
    assert round(retained["accumulated_value"], 2) == 4056.46

    # Verifica Net Worth consolidato: nessun raddoppio
    nw_after = compute_consolidated_net_worth(engine, portfolio_id=1)
    assert round(nw_after.pension_total, 2) == 4056.46
    assert round(nw_after.total_net_worth, 2) == 4056.46
