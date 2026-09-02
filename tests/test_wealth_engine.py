# ============================================================
# tests/test_wealth_engine.py
# Unit tests for ARGUS Wealth Management & Personal Finance
# ============================================================

import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

from core.wealth.wealth_models import (
    WealthAccount,
    PhysicalAssetItem,
    PensionPlanItem,
    CategoryNature,
    GoalCategory,
    WealthGoalItem,
    HeirRelationship,
    EstateHeirItem,
    EstatePlanResult,
    NetWorthSummary,
    AccountType,
    PhysicalAssetCategory
)
from core.wealth.wealth_db import (
    init_wealth_db,
    save_wealth_account,
    get_wealth_accounts,
    insert_cashflow_tx,
    get_cashflow_records,
    save_physical_asset,
    get_physical_assets,
    save_pension_plan,
    get_pension_plans,
    get_wealth_categories,
    get_wealth_portfolios,
    create_wealth_portfolio,
    delete_wealth_portfolio,
    clear_wealth_cashflow,
    clear_wealth_snapshots,
    clear_wealth_accounts,
    reset_wealth_portfolio_data,
    reset_all_wealth_database,
    cleanup_empty_wealth_portfolios,
    save_wealth_goal,
    get_wealth_goals,
    delete_wealth_goal
)
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_cashflow_analytics,
    compute_wealth_health_score,
    simulate_pension_projection,
    compute_goal_based_monte_carlo,
    compute_dynamic_glide_path,
    compute_portfolio_tco_and_fee_drag,
    compute_advanced_estate_planning,
    compute_tax_smart_rebalancing_watchdog,
    compute_real_estate_net_equity_and_ltv,
    generate_advisory_pitchbook_html,
    generate_advisory_pitchbook_pdf,
    compute_ai_quarterly_wealth_review,
    compute_family_office_multi_entity_consolidation,
    compute_sequence_of_returns_risk_engine
)
from core.wealth.wealth_importer import (
    parse_universal_statement,
    auto_categorize_transactions
)


from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine():
    """Crea un database SQLite in-memory per i test unitari di Wealth."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_wealth_db(eng)
    return eng



def test_wealth_db_init_and_categories(sqlite_engine):
    """Verifica l'inizializzazione corretta e le categorie di default."""
    df_cats = get_wealth_categories(sqlite_engine)
    assert not df_cats.empty
    assert len(df_cats) >= 15
    assert "Spesa Alimentare & Supermercato" in df_cats["name"].values
    assert "Stipendio / Compensi" in df_cats["name"].values


def test_wealth_accounts_crud(sqlite_engine):
    """Verifica inserimento e lettura conti."""
    aid = save_wealth_account(sqlite_engine, {
        "name": "Conto Intesa",
        "account_type": "checking",
        "institution": "Intesa Sanpaolo",
        "balance": 5000.0,
        "iban": "IT12345"
    })
    assert aid > 0
    df = get_wealth_accounts(sqlite_engine)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Conto Intesa"
    assert df.iloc[0]["balance"] == 5000.0


def test_cashflow_tx_and_balance_update(sqlite_engine):
    """Verifica che una transazione di spesa scali correttamente il saldo del conto."""
    aid = save_wealth_account(sqlite_engine, {
        "name": "Conto Spese",
        "account_type": "checking",
        "institution": "Banca",
        "balance": 1000.0
    })
    
    df_cats = get_wealth_categories(sqlite_engine)
    cat_id = int(df_cats[df_cats["flow_type"] == "expense"].iloc[0]["category_id"])

    tx_id = insert_cashflow_tx(sqlite_engine, {
        "account_id": aid,
        "category_id": cat_id,
        "tx_date": "2026-08-30",
        "amount": 250.0,
        "direction": "outflow",
        "merchant": "Supermercato Esselunga"
    })
    assert tx_id > 0

    df_acc = get_wealth_accounts(sqlite_engine)
    assert df_acc.iloc[0]["balance"] == 750.0

    df_tx = get_cashflow_records(sqlite_engine)
    assert len(df_tx) == 1
    assert df_tx.iloc[0]["merchant"] == "Supermercato Esselunga"


def test_physical_assets_and_luxury_watches(sqlite_engine):
    """Verifica inserimento e calcolo pnl orologi di lusso."""
    wid = save_physical_asset(sqlite_engine, {
        "name": "Rolex Submariner",
        "asset_category": "luxury_watches",
        "brand_or_location": "Rolex",
        "purchase_price": 9000.0,
        "current_market_value": 13000.0,
        "reference_number": "126610LN"
    })
    assert wid > 0

    df_w = get_physical_assets(sqlite_engine)
    assert len(df_w) == 1
    assert df_w.iloc[0]["unrealized_pnl"] == 4000.0
    assert round(df_w.iloc[0]["unrealized_pnl_pct"], 1) == 44.4


def test_consolidated_net_worth_calculation(sqlite_engine):
    """Verifica il calcolo aggregato del Patrimonio Netto."""
    save_wealth_account(sqlite_engine, {
        "name": "Liquidità",
        "account_type": "checking",
        "balance": 10000.0
    })
    save_physical_asset(sqlite_engine, {
        "name": "Rolex Daytona",
        "asset_category": "luxury_watches",
        "purchase_price": 20000.0,
        "current_market_value": 30000.0
    })
    save_pension_plan(sqlite_engine, {
        "plan_name": "Fondo Cometa",
        "provider": "Cometa",
        "accumulated_value": 15000.0
    })

    nw = compute_consolidated_net_worth(sqlite_engine)
    assert nw.liquid_cash == 10000.0
    assert nw.physical_assets == 30000.0
    assert nw.pension_total == 15000.0
    assert nw.total_net_worth == 55000.0
    assert nw.wealth_health_score > 0.0


def test_pension_monte_carlo_simulation():
    """Verifica il simulatore Monte Carlo per la pensione."""
    res = simulate_pension_projection(
        current_pot=10000,
        monthly_contrib=300,
        years_to_retirement=20,
        expected_return_pct=6.0,
        volatility_pct=8.0
    )
    assert res["real_pot_median"] > 10000
    assert res["estimated_monthly_annuity_real"] > 0
    assert res["total_contributions"] == (10000 + 300 * 240)


def test_universal_statement_parser():
    """Verifica il parsing di un file CSV bancario generico."""
    csv_data = """Data;Importo;Descrizione
2026-08-01;2500.00;Accredito Stipendio
2026-08-02;-85.50;Esselunga Spesa Alimentare
2026-08-03;-45.00;Ristorante Pizzeria Da Mario
"""
    import io
    buf = io.StringIO(csv_data)
    df_clean, errs = parse_universal_statement(buf, "estratto.csv")
    assert not errs
    assert len(df_clean) == 3
    assert df_clean.iloc[0]["direction"] == "inflow"
    assert df_clean.iloc[1]["direction"] == "outflow"
    assert df_clean.iloc[1]["amount"] == 85.50



def test_wealth_snapshot_save_and_recall(sqlite_engine):
    """Verifica il salvataggio su DB e il richiamo dello snapshot patrimoniale."""
    from datetime import date
    from core.wealth.wealth_snapshot import (
        save_wealth_snapshot_to_db,
        get_wealth_snapshots_history,
        load_wealth_snapshot_details,
        delete_wealth_snapshot
    )

    save_wealth_account(sqlite_engine, {
        "name": "Conto Fineco",
        "account_type": "checking",
        "balance": 12000.0
    })
    save_physical_asset(sqlite_engine, {
        "name": "Rolex GMT Batman",
        "asset_category": "luxury_watches",
        "purchase_price": 10000.0,
        "current_market_value": 15000.0
    })

    # 1. Salva snapshot con run_id e run_name
    snap_id = save_wealth_snapshot_to_db(
        sqlite_engine,
        run_name="Test Snapshot Ingestion 1",
        run_id="RUN-WLT-TEST-001",
        notes="Test note",
        portfolio_id=1
    )
    assert snap_id > 0

    # Salva un secondo snapshot nello stesso giorno (multi-ingestion)
    snap_id_2 = save_wealth_snapshot_to_db(
        sqlite_engine,
        run_name="Test Snapshot Ingestion 2",
        run_id="RUN-WLT-TEST-002",
        portfolio_id=1
    )
    assert snap_id_2 > snap_id

    # 2. Leggi cronologia snapshot
    df_hist = get_wealth_snapshots_history(sqlite_engine, portfolio_id=1)
    assert not df_hist.empty
    assert len(df_hist) == 2
    assert "RUN-WLT-TEST-001" in df_hist["run_id"].values
    assert "RUN-WLT-TEST-002" in df_hist["run_id"].values
    assert "portfolio_name" in df_hist.columns

    # 3. Richiama dettagli snapshot
    details = load_wealth_snapshot_details(sqlite_engine, snap_id)
    assert details is not None
    assert details["snapshot_name"] == "Test Snapshot Ingestion 1"
    assert details["run_id"] == "RUN-WLT-TEST-001"
    assert details["details"]["summary"]["total_net_worth"] == 27000.0
    assert len(details["details"]["accounts"]) >= 1

    # 4. Elimina snapshot
    deleted = delete_wealth_snapshot(sqlite_engine, snap_id)
    assert deleted is True
    delete_wealth_snapshot(sqlite_engine, snap_id_2)
    df_after = get_wealth_snapshots_history(sqlite_engine, portfolio_id=1)
    assert df_after.empty


def test_wealth_portfolios_crud_and_lifecycle(sqlite_engine):
    """Verifica creazione, elenco ed eliminazione di profili/portafogli patrimoniali."""
    # 1. Elenco di default
    df_p = get_wealth_portfolios(sqlite_engine)
    assert not df_p.empty
    assert "Personale" in df_p["name"].values

    # 2. Crea nuovo profilo
    new_pid = create_wealth_portfolio(sqlite_engine, "Holding Famiglia", "Profilo investimenti e immobili")
    assert new_pid > 1

    df_p2 = get_wealth_portfolios(sqlite_engine)
    assert len(df_p2) >= 2
    assert "Holding Famiglia" in df_p2["name"].values

    # 3. Elimina profilo
    del_ok = delete_wealth_portfolio(sqlite_engine, new_pid)
    assert del_ok is True
    df_p3 = get_wealth_portfolios(sqlite_engine)
    assert "Holding Famiglia" not in df_p3["name"].values


def test_clear_cashflow_and_reset_portfolio_data(sqlite_engine):
    """Verifica svuotamento transazioni e reset dati del portafoglio."""
    # Crea conto e transazioni
    aid = save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Revolut Test",
        "institution": "Revolut",
        "account_type": "checking",
        "balance": 5000.0
    })
    insert_cashflow_tx(sqlite_engine, {
        "portfolio_id": 1,
        "account_id": aid,
        "category_id": 1,
        "tx_date": "2026-08-01",
        "amount": 250.0,
        "direction": "outflow",
        "merchant": "Ristorante Test"
    })
    insert_cashflow_tx(sqlite_engine, {
        "portfolio_id": 1,
        "account_id": aid,
        "category_id": 1,
        "tx_date": "2026-08-05",
        "amount": 100.0,
        "direction": "outflow",
        "merchant": "Supermercato Test"
    })

    df_cf = get_cashflow_records(sqlite_engine, portfolio_id=1)
    assert len(df_cf) == 2

    # Svuota solo il libro mastro
    cleared = clear_wealth_cashflow(sqlite_engine, portfolio_id=1)
    assert cleared == 2
    df_cf_after = get_cashflow_records(sqlite_engine, portfolio_id=1)
    assert df_cf_after.empty

    # Il conto deve essere ancora presente
    df_accs = get_wealth_accounts(sqlite_engine, portfolio_id=1)
    assert not df_accs.empty

    # Test svuotamento solo conti
    del_accs_cnt = clear_wealth_accounts(sqlite_engine, portfolio_id=1)
    assert del_accs_cnt >= 1
    df_accs_after_clear = get_wealth_accounts(sqlite_engine, portfolio_id=1)
    assert df_accs_after_clear.empty

    # Ricrea per testare reset totale
    aid2 = save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Intesa Test",
        "institution": "Intesa",
        "account_type": "checking",
        "balance": 3000.0
    })
    # Reset totale
    reset_res = reset_wealth_portfolio_data(sqlite_engine, portfolio_id=1, keep_accounts=False)
    assert reset_res["accounts_deleted"] >= 1
    df_accs_reset = get_wealth_accounts(sqlite_engine, portfolio_id=1)
    assert df_accs_reset.empty


def test_reset_all_wealth_database_and_cleanup(sqlite_engine):
    """Verifica il reset totale incondizionato e la pulizia profili vuoti."""
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Test Global",
        "institution": "Banca Global",
        "account_type": "checking",
        "balance": 5000.0
    })
    save_physical_asset(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Rolex Submariner",
        "asset_category": "luxury_watches",
        "purchase_price": 8000.0,
        "current_market_value": 11000.0
    })
    
    # Crea un profilo con nome valido ed uno con nome vuoto
    pid_valid = create_wealth_portfolio(sqlite_engine, "Profilo B", "Desc")
    assert pid_valid >= 1

    # Esegui reset totale globale
    res_glob = reset_all_wealth_database(sqlite_engine)
    assert "wealth_accounts" in res_glob
    assert "wealth_physical_assets" in res_glob

    # Verifica che le tabelle siano vuote
    assert get_wealth_accounts(sqlite_engine).empty
    assert get_physical_assets(sqlite_engine).empty

    # Pulizia profili vuoti
    n_cleaned = cleanup_empty_wealth_portfolios(sqlite_engine)
    assert n_cleaned >= 0


def test_dynamic_risk_portfolio_linkage(sqlite_engine):
    """Verifica il collegamento dinamico dei portafogli dal modulo Risk al modulo Wealth."""
    from sqlalchemy import text as sqlt
    from core.wealth.wealth_db import (
        get_available_risk_portfolios,
        set_linked_risk_portfolios,
        get_linked_risk_portfolios,
        get_linked_risk_portfolios_summary,
        save_wealth_snapshot_to_db,
        load_wealth_snapshot_details
    )

    # Crea tabelle portfolios e portfolio_snapshots se non esistono nel mock SQLite
    with sqlite_engine.begin() as conn:
        conn.execute(sqlt("""
            CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'user',
                base_currency TEXT NOT NULL DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(sqlt("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                calc_date DATE NOT NULL,
                run_id TEXT,
                run_name TEXT,
                total_value REAL NOT NULL
            );
        """))
        # Inserisci due portafogli risk
        conn.execute(sqlt("INSERT INTO portfolios (portfolio_id, name) VALUES (101, 'Risk Stocks Growth'), (102, 'Risk Crypto Moon')"))
        r1, r2 = 101, 102
        
        # Aggiungi snapshot con valori
        conn.execute(sqlt("""
            INSERT INTO portfolio_snapshots (portfolio_id, calc_date, run_id, run_name, total_value)
            VALUES (:pid, '2026-08-30', 'RUN-RSK-001', 'Growth Run', 150000.0)
        """), {"pid": r1})
        conn.execute(sqlt("""
            INSERT INTO portfolio_snapshots (portfolio_id, calc_date, run_id, run_name, total_value)
            VALUES (:pid, '2026-08-30', 'RUN-RSK-002', 'Crypto Run', 50000.0)
        """), {"pid": r2})

    # 1. Recupera portafogli disponibili
    df_avail = get_available_risk_portfolios(sqlite_engine)
    assert not df_avail.empty
    assert r1 in df_avail["portfolio_id"].values
    assert r2 in df_avail["portfolio_id"].values

    # 2. Collega entrambi al Profilo Wealth #1
    set_linked_risk_portfolios(sqlite_engine, wealth_portfolio_id=1, risk_portfolio_ids=[r1, r2])
    linked_ids = get_linked_risk_portfolios(sqlite_engine, wealth_portfolio_id=1)
    assert linked_ids == [r1, r2]

    # 3. Verifica riepilogo
    tot_val, df_summary = get_linked_risk_portfolios_summary(sqlite_engine, wealth_portfolio_id=1)
    assert tot_val == 200000.0

    assert len(df_summary) == 2

    # 4. Calcolo Net Worth consolidato
    nw = compute_consolidated_net_worth(sqlite_engine, portfolio_id=1)
    assert nw.financial_investments == 200000.0

    # 5. Salva snapshot e verifica che linked_risk_portfolios sia serializzato
    snap_id = save_wealth_snapshot_to_db(sqlite_engine, snapshot_name="Snap Con Risk Links", portfolio_id=1)
    details = load_wealth_snapshot_details(sqlite_engine, snap_id)
    assert details is not None
    assert len(details["details"]["linked_risk_portfolios"]) == 2

    # 6. Rimuovi un portafoglio dal link (solo r1 attivo)
    set_linked_risk_portfolios(sqlite_engine, wealth_portfolio_id=1, risk_portfolio_ids=[r1])
    nw_single = compute_consolidated_net_worth(sqlite_engine, portfolio_id=1)
    assert nw_single.financial_investments == 150000.0


def test_fire_analytics_and_wealth_stress_testing(sqlite_engine):
    """Verifica il calcolo analitico del FIRE e dello stress testing patrimoniale."""
    from core.wealth.wealth_models import NetWorthSummary
    from core.wealth.wealth_engine import compute_fire_analytics, compute_wealth_stress_test

    mock_summary = NetWorthSummary(
        total_net_worth=100000.0,
        liquid_cash=20000.0,
        financial_investments=60000.0,
        physical_assets=15000.0,
        pension_total=5000.0,
        luxury_watches_total=5000.0,
        precious_metals_total=10000.0,
        monthly_burn_rate=2000.0,
        runway_months=10.0
    )

    mock_cf = {
        "avg_monthly_expense": 2000.0,
        "net_savings": 1000.0,
        "monthly_summary": [1, 2, 3]
    }

    # 1. Test FIRE Analytics
    fire_res = compute_fire_analytics(mock_summary, mock_cf, current_age=30, swr_pct=4.0, exp_return_pct=7.0, inflation_pct=2.0)
    assert fire_res["fire_number"] == 600000.0 # 24000 / 0.04
    assert fire_res["lean_fire_number"] == 420000.0
    assert fire_res["fat_fire_number"] == 810000.0
    assert fire_res["years_to_fire"] is not None
    assert fire_res["fire_age"] is not None
    assert fire_res["fire_age"] >= 30
    assert len(fire_res["proj_years"]) == len(fire_res["proj_cap"])

    # 2. Test Wealth Stress Testing
    stress_2008 = compute_wealth_stress_test(mock_summary, scenario="crisis_2008")
    assert stress_2008["stressed_net_worth"] < mock_summary.total_net_worth
    assert stress_2008["pnl_impact"] < 0
    assert stress_2008["stressed_runway_months"] == 10.0 # Cash non toccato da 2008

    stress_stag = compute_wealth_stress_test(mock_summary, scenario="stagflation")
    assert stress_stag["stressed_runway_months"] < 10.0 # Burn rate aumentato del 25%

    stress_job = compute_wealth_stress_test(mock_summary, scenario="job_loss")
    assert stress_job["stressed_liquid"] == 8000.0 # 20000 - (2000 * 6)


def test_compute_fiscal_analytics(sqlite_engine):
    """Verifica il calcolo di IVAFE, bollo italiano, minusvalenze e quadro RW."""
    from core.wealth.wealth_engine import compute_fiscal_analytics

    # Inserisci un conto estero e uno italiano
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Revolut Vault",
        "account_type": "savings",
        "institution": "Revolut Bank",
        "balance": 8000.0,
        "iban": "LT123456789"
    })
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Intesa C/C",
        "account_type": "checking",
        "institution": "Intesa Sanpaolo",
        "balance": 6000.0,
        "iban": "IT987654321"
    })

    res = compute_fiscal_analytics(sqlite_engine, portfolio_id=1)
    assert res["total_foreign_assets"] >= 8000.0
    assert res["total_domestic_assets"] >= 6000.0
    assert res["total_ivafe"] == 34.20 # Conto estero > 5000 euro
    assert res["total_bollo"] == 34.20 # Conto italiano > 5000 euro
    assert res["total_minusvalenze"] > 0
    assert res["tax_shield_potential"] == round(res["total_minusvalenze"] * 0.26, 2)
    assert len(res["quadro_rw_rows"]) >= 1


def test_compute_mortgage_amortization():
    """Verifica il piano di ammortamento alla francese e l'estinzione anticipata."""
    from core.wealth.wealth_engine import compute_mortgage_amortization

    mort = compute_mortgage_amortization(
        principal=100000.0,
        annual_rate=3.0,
        duration_years=20,
        extra_monthly_payment=50.0
    )
    assert mort["monthly_payment"] > 0
    assert mort["total_interest"] > 0
    assert mort["effective_total_interest"] < mort["total_interest"]
    assert mort["interest_saved"] > 0
    assert mort["months_saved"] > 0
    assert len(mort["schedule"]) == 240
    assert len(mort["rate_shocks"]) == 3


def test_compute_real_estate_roi():
    """Verifica i calcoli di redditività immobiliare e Cash-on-Cash Return."""
    from core.wealth.wealth_engine import compute_real_estate_roi

    roi = compute_real_estate_roi(
        property_val=200000.0,
        down_payment=50000.0,
        mortgage_rate=3.0,
        mortgage_years=25,
        monthly_rent=900.0,
        condo_fees_monthly=50.0,
        imu_annual=600.0,
        maintenance_pct=1.0,
        tax_regime="cedolare_21"
    )
    assert roi["gross_yield_pct"] == 5.4 # 10800 / 200000
    assert roi["cap_rate_pct"] > 0
    assert roi["noi"] > 0
    assert roi["initial_cash_invested"] > 50000.0
    assert "cash_on_cash_pct" in roi


def test_compute_buy_vs_rent_comparison():
    """Verifica il modello comparativo Buy vs Rent."""
    from core.wealth.wealth_engine import compute_buy_vs_rent_comparison

    bvr = compute_buy_vs_rent_comparison(
        property_val=200000.0,
        down_payment=40000.0,
        mortgage_rate=3.0,
        mortgage_years=25,
        monthly_rent=750.0,
        investment_return_rate=0.07,
        inflation_rate=0.02,
        years_horizon=25
    )
    assert len(bvr["buy_equity_trajectory"]) == 25
    assert len(bvr["rent_invested_trajectory"]) == 25
    assert bvr["final_buy_net_worth"] > 0
    assert bvr["final_rent_net_worth"] > 0
    assert bvr["winner"] in ["Acquisto (Buy)", "Affitto + Investimento (Rent)"]


def test_compute_estate_planning_analytics():
    """Verifica le quote di legittima del Codice Civile e il calcolo franchigie successorie."""
    from core.wealth.wealth_models import NetWorthSummary
    from core.wealth.wealth_engine import compute_estate_planning_analytics

    mock_nw = NetWorthSummary(
        total_net_worth=1500000.0,
        liquid_cash=200000.0,
        financial_investments=800000.0,
        physical_assets=400000.0,
        pension_total=100000.0,
        luxury_watches_total=50000.0,
        precious_metals_total=50000.0,
        monthly_burn_rate=3000.0,
        runway_months=66.0
    )

    # Coniuge + 2 Figli (art. 542 c.c.: 25% Coniuge, 50% Figli, 25% Disponibile)
    estate = compute_estate_planning_analytics(
        net_worth_summary=mock_nw,
        children_count=2,
        has_spouse=True
    )
    assert estate["legittima_coniuge_pct"] == 25.0
    assert estate["legittima_figli_tot_pct"] == 50.0
    assert estate["disponibile_pct"] == 25.0
    assert estate["val_legittima_coniuge"] == 375000.0
    assert estate["val_legittima_per_figlio"] == 375000.0
    assert estate["val_disponibile"] == 375000.0
    assert estate["total_exempt_assets"] > 0
    # Coniuge e ciascun figlio hanno € 375k < € 1M di franchigia -> imposta dovuta = 0
    assert estate["is_under_exempt_threshold"] is True
    assert estate["total_succession_tax"] == 0.0


def test_compute_ai_wealth_diagnostics_and_tear_sheet(sqlite_engine):
    """Verifica la diagnostica AI e la generazione dell'Executive Tear Sheet HTML."""
    from core.wealth.wealth_engine import compute_ai_wealth_diagnostics, generate_executive_tear_sheet_html

    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Principale",
        "account_type": "checking",
        "institution": "Intesa",
        "balance": 15000.0
    })

    ai_res = compute_ai_wealth_diagnostics(sqlite_engine, portfolio_id=1)
    assert "health_score" in ai_res
    assert "bottlenecks" in ai_res
    assert isinstance(ai_res["bottlenecks"], list)
    assert "current_allocation" in ai_res
    assert "rebalance_orders" in ai_res

    # Test Tear Sheet HTML
    html = generate_executive_tear_sheet_html(sqlite_engine, portfolio_id=1)
    assert "<!DOCTYPE html>" in html
    assert "ARGUS WEALTH MANAGEMENT" in html
    assert "Patrimonio Netto" in html


def test_export_wealth_master_excel_workbook(sqlite_engine):
    """Verifica la generazione del Dossier Master Excel a 10 fogli."""
    from core.wealth.wealth_exporter import export_wealth_master_excel_workbook

    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Intesa Sanpaolo",
        "account_type": "checking",
        "institution": "Intesa",
        "balance": 25000.0,
        "currency": "EUR"
    })
    save_physical_asset(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Daytona Platinum",
        "asset_category": "luxury_watches",
        "purchase_price": 40000.0,
        "current_market_value": 75000.0
    })

    excel_buf = export_wealth_master_excel_workbook(sqlite_engine, portfolio_id=1)
    assert excel_buf is not None
    excel_bytes = excel_buf.getvalue()
    assert len(excel_bytes) > 2000
    # Verifica che sia un file zip/xlsx valido (PK header: 0x50, 0x4B)
    assert excel_bytes.startswith(b'PK')


def test_compute_recurring_subscriptions_analytics():
    """Verifica il motore Subscription Sentinel e il calcolo del drag da costo opportunità."""
    from core.wealth.wealth_engine import compute_recurring_subscriptions_analytics

    # Test con DataFrame vuoto (fallback simulato attivo)
    res_empty = compute_recurring_subscriptions_analytics(pd.DataFrame())
    assert "subscriptions" in res_empty
    assert res_empty["total_monthly_burn"] >= 0.0

    # Test con transazioni reali di spesa
    df_sample = pd.DataFrame([
        {"tx_date": "2026-01-15", "amount": 17.99, "tx_type": "expense", "category_name": "Streaming", "merchant": "Netflix"},
        {"tx_date": "2026-02-15", "amount": 17.99, "tx_type": "expense", "category_name": "Streaming", "merchant": "Netflix"},
        {"tx_date": "2026-03-15", "amount": 17.99, "tx_type": "expense", "category_name": "Streaming", "merchant": "Netflix"},
        {"tx_date": "2026-01-10", "amount": 10.99, "tx_type": "expense", "category_name": "Musica", "merchant": "Spotify"},
        {"tx_date": "2026-02-10", "amount": 10.99, "tx_type": "expense", "category_name": "Musica", "merchant": "Spotify"},
    ])

    res = compute_recurring_subscriptions_analytics(df_sample)
    assert res["count"] == 2
    assert res["total_monthly_burn"] == pytest.approx(17.99 + 10.99, 0.01)
    assert res["total_annual_burn"] == pytest.approx((17.99 + 10.99) * 12, 0.01)
    assert res["opportunity_cost_10y"] > res["total_annual_burn"] * 10  # Capitalizzazione al 7% annuo
    assert res["opportunity_cost_20y"] > res["opportunity_cost_10y"]


def test_compute_cashflow_forecast_and_anomalies():
    """Verifica il rilevamento anomalie Z-Score e la previsione di liquidità rolling a 3/6 mesi."""
    from core.wealth.wealth_engine import compute_cashflow_forecast_and_anomalies

    df_tx = pd.DataFrame([
        {"tx_date": "2026-01-05", "amount": 50.0, "category_name": "Spesa", "merchant": "Conad", "tx_type": "expense"},
        {"tx_date": "2026-01-12", "amount": 55.0, "category_name": "Spesa", "merchant": "Conad", "tx_type": "expense"},
        {"tx_date": "2026-01-19", "amount": 48.0, "category_name": "Spesa", "merchant": "Conad", "tx_type": "expense"},
        {"tx_date": "2026-01-26", "amount": 350.0, "category_name": "Spesa", "merchant": "Maxi Spesa Anomala", "tx_type": "expense"}
    ])

    res = compute_cashflow_forecast_and_anomalies(df_tx, current_liquid_cash=12000.0)
    assert res["current_liquidity"] == 12000.0
    assert len(res["forecast_timeline"]) == 6
    assert res["projected_liquidity_3m"] > 0
    assert res["projected_liquidity_6m"] > 0
    assert res["anomalies_count"] >= 1


def test_compute_tax_loss_harvesting_and_latent_taxes(sqlite_engine):
    """Verifica il calcolo delle imposte latenti su plusvalenze, harvesting e deduzione IRPEF."""
    from core.wealth.wealth_engine import compute_tax_loss_harvesting_and_latent_taxes

    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Directa Trading",
        "account_type": "brokerage",
        "institution": "Directa",
        "balance": 100000.0,
        "currency": "EUR"
    })

    res = compute_tax_loss_harvesting_and_latent_taxes(sqlite_engine, portfolio_id=1)
    assert res["total_financial_investments"] == 100000.0
    assert res["total_latent_tax_liability"] > 0
    assert res["net_worth_post_latent_tax"] < res["net_worth_pre_tax"]
    assert "harvesting_opportunities" in res
    assert len(res["harvesting_opportunities"]) >= 1
    
    # Test IRPEF deduction
    irpef = res["irpef_pension_optimization"]
    assert irpef["deduction_ceiling"] == 5164.57
    assert irpef["tax_refund_scaglione_43"] > irpef["tax_refund_scaglione_35"]
    assert irpef["tax_refund_scaglione_35"] > irpef["tax_refund_scaglione_23"]


def test_compute_wealth_risk_integrated_analytics(sqlite_engine):
    """Verifica il ponte Wealth ⇄ Risk: Liquidity-at-Risk, Net Worth-at-Risk e Dynamic SWR."""
    from core.wealth.wealth_engine import compute_wealth_risk_integrated_analytics

    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Fineco Banking",
        "account_type": "checking",
        "institution": "Fineco",
        "balance": 18000.0,
        "currency": "EUR"
    })
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Interactive Brokers",
        "account_type": "brokerage",
        "institution": "IBKR",
        "balance": 85000.0,
        "currency": "EUR"
    })

    res = compute_wealth_risk_integrated_analytics(sqlite_engine, wealth_portfolio_id=1)
    
    # Check Liquidity-at-Risk
    lar = res["liquidity_at_risk"]
    assert lar["current_runway_months"] >= 0
    assert lar["risk_adjusted_runway_target_months"] >= 6.0
    assert "forced_selling_risk_level" in lar

    # Check Net Worth-at-Risk Scenarios
    nwar = res["net_worth_at_risk_scenarios"]
    assert len(nwar) == 4
    for sc in nwar:
        assert "net_worth_post_shock" in sc
        assert "perdita_patrimonio_eur" in sc
        assert "impatto_pct" in sc

    # Check Dynamic SWR
    swr = res["dynamic_fire_swr"]
    assert 3.0 <= swr["dynamic_swr_pct"] <= 4.5
    assert swr["annual_safe_income_eur"] > 0
    assert swr["monthly_safe_budget_eur"] == pytest.approx(swr["annual_safe_income_eur"] / 12.0, 0.01)


def test_compute_cashflow_analytics_strict_transfers_exclusion():
    """Verifica che i giroconti e trasferimenti interni NON siano conteggiati come entrate né uscite."""
    from core.wealth.wealth_engine import (
        compute_cashflow_analytics,
        compute_merchant_pareto_analytics,
        compute_seasonality_matrix,
        compute_envelope_budget_analytics,
        compute_cashflow_whatif_reinvestment
    )

    df_test = pd.DataFrame([
        {"tx_date": "2026-01-10", "direction": "inflow", "amount": 2500.0, "nature": "income", "category_name": "Stipendio", "merchant": "Azienda SpA"},
        {"tx_date": "2026-01-15", "direction": "outflow", "amount": 800.0, "nature": "need", "category_name": "Casa & Affitto", "merchant": "Proprietario"},
        {"tx_date": "2026-01-18", "direction": "outflow", "amount": 200.0, "nature": "want", "category_name": "Ristoranti", "merchant": "Pizzeria"},
        # Giroconto 1: direction transfer
        {"tx_date": "2026-01-20", "direction": "transfer", "amount": 500.0, "nature": "transfer", "category_name": "Giroconti & Trasferimenti Interni", "merchant": "ISP to Revolut"},
        # Giroconto 2: direction outflow ma categoria giroconto
        {"tx_date": "2026-01-22", "direction": "outflow", "amount": 1000.0, "nature": "transfer", "category_name": "Giroconti & Trasferimenti Interni", "merchant": "Giroconto Conto Deposito"},
        # Giroconto 3: direction inflow ma categoria trasferimento
        {"tx_date": "2026-01-22", "direction": "inflow", "amount": 1000.0, "nature": "transfer", "category_name": "Trasferimento Interno", "merchant": "Accredito da Conto Corrente"}
    ])

    cf_res = compute_cashflow_analytics(df_test)
    # Entrate reali devono essere ESATTAMENTE 2500 (non 3500)
    assert cf_res["total_inflow"] == 2500.0
    # Uscite reali devono essere ESATTAMENTE 1000 (800 + 200, non 2500)
    assert cf_res["total_outflow"] == 1000.0
    # Risparmio netto deve essere 1500 (2500 - 1000)
    assert cf_res["net_savings"] == 1500.0
    # Tasso di risparmio 60%
    assert cf_res["savings_rate_pct"] == 60.0
    # Giroconti totali tracciati
    assert cf_res["total_transfers"] == 2500.0

    # Test Pareto: i giroconti non devono apparire tra i merchant di spesa
    pareto = compute_merchant_pareto_analytics(df_test)
    assert pareto["total_outflow"] == 1000.0
    assert len(pareto["merchants"]) == 2
    merch_names = list(pareto["merchants"]["clean_merchant"])
    assert "ISP to Revolut" not in merch_names
    assert "Giroconto Conto Deposito" not in merch_names

    # Test Seasonality: solo 2 categorie reali
    seas = compute_seasonality_matrix(df_test)
    assert "Giroconti & Trasferimenti Interni" not in seas.index
    assert "Trasferimento Interno" not in seas.index
    assert seas["Totale Anno"].sum() == 1000.0

    # Test Envelope: solo 2 categorie reali
    env = compute_envelope_budget_analytics(df_test)
    assert len(env) == 2
    assert "Giroconti & Trasferimenti Interni" not in list(env["category_name"])

    # Test What-If Reinvestment
    whatif = compute_cashflow_whatif_reinvestment(100.0, annual_return_rate=0.07, max_years=10)
    assert whatif["val_10y"] > 12000.0 # 100*120 + compounding
    assert len(whatif["timeline"]) == 10


def test_wealth_goals_crud(sqlite_engine):
    """Test inserimento, lettura, aggiornamento ed eliminazione obiettivi di vita."""
    init_wealth_db(sqlite_engine)
    gid = save_wealth_goal(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Acquisto Casa",
        "category": GoalCategory.REAL_ESTATE.value,
        "target_amount": 200000.0,
        "target_date": "2032-12-31",
        "current_amount": 30000.0,
        "monthly_contribution": 800.0,
        "priority": "high",
        "risk_tolerance": "moderate",
        "notes": "Target anticipo mutuo e ristrutturazione"
    })
    assert gid > 0

    df_g = get_wealth_goals(sqlite_engine, portfolio_id=1)
    assert not df_g.empty
    assert len(df_g) == 1
    row = df_g.iloc[0]
    assert row["name"] == "Acquisto Casa"
    assert row["target_amount"] == 200000.0

    # Aggiornamento
    save_wealth_goal(sqlite_engine, {
        "goal_id": gid,
        "portfolio_id": 1,
        "name": "Acquisto Casa Modificato",
        "target_amount": 220000.0,
        "target_date": "2032-12-31",
        "current_amount": 35000.0,
        "monthly_contribution": 900.0
    })
    df_g2 = get_wealth_goals(sqlite_engine, portfolio_id=1)
    assert df_g2.iloc[0]["target_amount"] == 220000.0
    assert df_g2.iloc[0]["name"] == "Acquisto Casa Modificato"

    # Eliminazione
    res_del = delete_wealth_goal(sqlite_engine, gid)
    assert res_del is True
    df_g3 = get_wealth_goals(sqlite_engine, portfolio_id=1)
    assert df_g3.empty


def test_compute_goal_based_monte_carlo_engine():
    """Test del motore stocastico Merton Jump-Diffusion per Goal-Based Planning."""
    res = compute_goal_based_monte_carlo(
        current_amount=20000.0,
        monthly_contribution=500.0,
        target_amount=100000.0,
        years=10.0,
        mean_annual_return=0.07,
        annual_volatility=0.15,
        n_simulations=1000
    )
    assert "spi_pct" in res
    assert 0.0 <= res["spi_pct"] <= 100.0
    assert res["p50_median_final"] > 20000.0
    assert res["p95_final"] >= res["p50_median_final"] >= res["p5_final"]
    assert "timeline_df" in res
    assert not res["timeline_df"].empty
    assert res["recommended_monthly_contribution"] > 0.0


def test_compute_dynamic_glide_path_engine():
    """Test della curva sigmoidea di de-risking lungo l'orizzonte temporale."""
    gp_start = compute_dynamic_glide_path(years_to_target=20.0, total_horizon_years=20.0, risk_profile="moderate")
    gp_end = compute_dynamic_glide_path(years_to_target=1.0, total_horizon_years=20.0, risk_profile="moderate")

    # A inizio orizzonte l'azionario deve essere alto (~80%)
    assert gp_start["current_allocation"]["equity_pct"] > 70.0
    # A fine orizzonte l'azionario deve scendere (~20%)
    assert gp_end["current_allocation"]["equity_pct"] < 35.0
    # Obbligazioni + liquidità devono salire
    assert gp_end["current_allocation"]["bonds_pct"] + gp_end["current_allocation"]["cash_pct"] > 60.0
    assert not gp_start["glide_path_timeline"].empty


def test_compute_portfolio_tco_and_fee_drag_engine():
    """Test del calcolo del Total Cost of Ownership e dell'erosione da costi (Fee Drag)."""
    df_pos = pd.DataFrame([
        {"symbol": "VWCE.DE", "name": "Vanguard FTSE All-World", "asset_class": "etf", "market_value": 70000.0},
        {"symbol": "LU123456", "name": "Fondo Attivo Bilanciato", "asset_class": "mutual_fund", "market_value": 30000.0}
    ])
    tco = compute_portfolio_tco_and_fee_drag(
        df_positions=df_pos,
        initial_wealth=100000.0,
        monthly_contribution=500.0,
        holding_years=[5, 10, 20, 30]
    )
    assert tco["weighted_average_ter_pct"] > 0.0
    assert tco["drag_10y_eur"] > 0.0
    assert tco["drag_30y_eur"] > tco["drag_10y_eur"]
    assert len(tco["comparison_table"]) == 4
    assert not tco["breakdown_df"].empty


def test_compute_advanced_estate_planning_engine():
    """Test della pianificazione successoria secondo la normativa italiana D.Lgs. 346/1990."""
    nw_mock = NetWorthSummary(
        total_net_worth=2500000.0,
        liquid_cash=300000.0,
        financial_investments=1200000.0,
        real_estate_total=1000000.0,
        pension_total=200000.0,  # Esente ex lege
        total_liabilities=100000.0
    )
    heirs = [
        {"name": "Coniuge", "relationship": "spouse", "is_disabled": False, "assigned_share_pct": 50.0},
        {"name": "Figlio 1", "relationship": "child", "is_disabled": False, "assigned_share_pct": 50.0}
    ]

    res = compute_advanced_estate_planning(
        summary=nw_mock,
        heirs=heirs,
        exempt_assets_manual=0.0,
        real_estate_value=1000000.0,
        prima_casa_heir=True
    )

    assert res["gross_estate"] > 0.0
    assert res["exempt_assets"] >= 200000.0  # Fondo pensione escluso
    assert res["legitimate_quota_pct"] == 66.67
    assert res["disposable_quota_pct"] == 33.33
    assert res["mortgage_cadastral_tax_eur"] == 400.0  # Prima casa fissa 200+200
    assert len(res["heir_breakdown"]) == 2
    # Ciascun erede eredita ~1.15M, con franchigia 1.0M -> base imponibile ~150k -> imposta 4% = ~6k
    for h in res["heir_breakdown"]:
        assert h["franchise_eur"] == 1000000.0
        assert h["tax_rate_pct"] == 4.0


def test_compute_tax_smart_rebalancing_watchdog(sqlite_engine):
    """Test del Watchdog di Ribilanciamento, Drift Monitor e Cash Drag Alert."""
    init_wealth_db(sqlite_engine)
    # Salviamo conto con eccesso di liquidità
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Corrente Principale",
        "account_type": AccountType.CHECKING.value,
        "balance": 150000.0,
        "institution": "Banca Intesa"
    })
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Risparmio",
        "account_type": AccountType.SAVINGS.value,
        "balance": 50000.0,
        "institution": "Directa"
    })

    watchdog = compute_tax_smart_rebalancing_watchdog(sqlite_engine, portfolio_id=1)
    assert "drift_table" in watchdog
    assert not watchdog["drift_df"].empty
    assert watchdog["total_investable_assets_eur"] == 200000.0
    # 200k liquidità vs 10% target -> Cash Drag Alert
    assert watchdog["cash_drag_alert"] is True
    assert watchdog["excess_cash_eur"] > 0.0
    assert watchdog["critical_drifts_count"] > 0


def test_compute_real_estate_net_equity_and_ltv(sqlite_engine):
    """Test del calcolo dell'Home Equity e del Loan-to-Value (LTV %)."""
    init_wealth_db(sqlite_engine)
    # Immobile da 300.000€
    save_physical_asset(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Appartamento Centro",
        "asset_category": PhysicalAssetCategory.REAL_ESTATE.value,
        "current_market_value": 300000.0,
        "purchase_price": 270000.0,
        "brand_or_location": "Milano"
    })
    # Mutuo residuo da 180.000€
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Mutuo Prima Casa",
        "account_type": AccountType.MORTGAGE.value,
        "balance": -180000.0,
        "institution": "Crédit Agricole"
    })

    re_summary = compute_real_estate_net_equity_and_ltv(sqlite_engine, portfolio_id=1)
    assert re_summary["total_property_market_value"] == 300000.0
    assert re_summary["total_mortgage_debt_remaining"] == 180000.0
    # Net Equity = 300k - 180k = 120.000€
    assert re_summary["net_home_equity_eur"] == 120000.0
    # LTV = 180k / 300k = 60.0%
    assert re_summary["weighted_ltv_pct"] == 60.0
    assert re_summary["property_count"] == 1
    assert re_summary["mortgage_count"] == 1
    assert re_summary["estimated_monthly_mortgage_payment"] > 0.0


def test_generate_advisory_pitchbook_pdf_engine(sqlite_engine):
    """Test della generazione del report Pitchbook Multipagina (HTML e PDF binario)."""
    init_wealth_db(sqlite_engine)
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Corrente",
        "account_type": AccountType.CHECKING.value,
        "balance": 25000.0,
        "institution": "Fineco"
    })
    save_wealth_goal(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Fondo Emergenza",
        "category": GoalCategory.EMERGENCY_BUFFER.value,
        "target_amount": 30000.0,
        "target_date": "2027-12-31",
        "current_amount": 25000.0,
        "monthly_contribution": 200.0
    })

    html_str = generate_advisory_pitchbook_html(sqlite_engine, portfolio_id=1)
    assert "ARGUS" in html_str
    assert "Executive Wealth Pitchbook" in html_str
    assert "Fondo Emergenza" in html_str

    pdf_bytes = generate_advisory_pitchbook_pdf(sqlite_engine, portfolio_id=1)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF")


def test_compute_ai_quarterly_wealth_review(sqlite_engine):
    """Test della generazione del report narrativo trimestrale per Family Office e Clienti."""
    init_wealth_db(sqlite_engine)
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Corrente",
        "account_type": AccountType.CHECKING.value,
        "balance": 80000.0,
        "institution": "Fineco"
    })

    review = compute_ai_quarterly_wealth_review(sqlite_engine, portfolio_id=1, quarter="Q1 2026")
    assert review["quarter"] == "Q1 2026"
    assert "full_markdown" in review
    assert "Relazione Trimestrale" in review["full_markdown"]
    assert len(review["tactical_recommendations"]) > 0
    assert review["consolidated_kpis"]["net_worth"] == 80000.0


def test_compute_family_office_multi_entity_consolidation(sqlite_engine):
    """Test del Consolidatore Family Office Multi-Entity con elisione infragruppo e PEX 1.2%."""
    init_wealth_db(sqlite_engine)
    save_wealth_account(sqlite_engine, {
        "portfolio_id": 1,
        "name": "Conto Holding",
        "account_type": AccountType.CHECKING.value,
        "balance": 500000.0,
        "institution": "Intesa Sanpaolo"
    })

    fo = compute_family_office_multi_entity_consolidation(sqlite_engine, portfolio_id=1)
    assert fo["consolidated_family_office_net_worth"] > 0.0
    assert fo["entities_count"] >= 4
    assert fo["eliminated_intercompany_amount_eur"] > 0.0
    assert "tax_efficiency_pex" in fo
    assert fo["tax_efficiency_pex"]["annual_tax_saving_eur"] > 0.0
    assert fo["tax_efficiency_pex"]["tax_saving_pct"] > 90.0  # PEX 1.2% vs 26% IRPEF


def test_compute_sequence_of_returns_risk_engine():
    """Test del simulatore di decumulo 30y e Sequence of Returns Risk (SRR)."""
    res = compute_sequence_of_returns_risk_engine(
        initial_wealth=1000000.0,
        annual_withdrawal=40000.0,
        early_shock_pct=-25.0,
        cash_buffer_years=2.5,
        max_years=30
    )

    assert res["initial_wealth_eur"] == 1000000.0
    assert res["initial_swr_pct"] == 4.0
    assert res["cash_buffer_recommended_eur"] == 100000.0  # 40k * 2.5
    assert "trajectory_df" in res
    assert not res["trajectory_df"].empty
    assert not res["constant_result"]["is_ruined"]
    assert res["constant_result"]["final_wealth"] > 1000000.0
    # Lo scenario con buffer protettivo estende la sopravvivenza o previene la rovina rispetto allo scenario sprotetto
    assert (res["early_crash_with_buffer_result"]["ruin_year"] or 99) > (res["early_crash_result"]["ruin_year"] or 0)










