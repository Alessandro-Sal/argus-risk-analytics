"""
tests/test_realistic_portfolio_generator.py
============================================================
ARGUS Risk Analytics Platform — Quantitative Simulation Tests
Verifies mathematical integrity, cash solvency, calendar rules,
French mortgage amortization, dividend consistency, and database
schema compliance across all user archetypes.
============================================================
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scripts.generate_realistic_portfolio import (
    ARCHETYPES,
    MarketCalendarHelper,
    FrenchMortgageEngine,
    CashLedger,
    PriceAndDividendEngine,
    PortfolioSimulationEngine,
    verify_simulation_invariants,
    populate_argus_database,
    export_simulation_to_files
)
from core.wealth.wealth_db import init_wealth_db


# ─────────────────────────────────────────────────────────────
# 1. Test del Calendario di Negoziazione
# ─────────────────────────────────────────────────────────────

def test_market_calendar_helper():
    """Verifica che i weekend e le festività borsistiche siano correttamente esclusi."""
    # Sabato e Domenica
    saturday = datetime(2024, 6, 15)
    sunday = datetime(2024, 6, 16)
    monday = datetime(2024, 6, 17)
    assert MarketCalendarHelper.is_weekend(saturday) is True
    assert MarketCalendarHelper.is_weekend(sunday) is True
    assert MarketCalendarHelper.is_weekend(monday) is False

    # Festività (Capodanno, Natale)
    new_year = datetime(2024, 1, 1)
    christmas = datetime(2024, 12, 25)
    assert MarketCalendarHelper.is_market_holiday(new_year) is True
    assert MarketCalendarHelper.is_market_holiday(christmas) is True

    # Next trading day
    next_td = MarketCalendarHelper.get_next_trading_day(saturday)
    assert next_td.weekday() == 0  # Deve slittare al Lunedì
    assert MarketCalendarHelper.is_trading_day(next_td) is True


# ─────────────────────────────────────────────────────────────
# 2. Test Motore Ammortamento Mutuo alla Francese
# ─────────────────────────────────────────────────────────────

def test_french_mortgage_mathematics():
    """Verifica la correttezza matematica della rata costante e decrescita del debito."""
    principal = 300000.0
    annual_rate = 3.0  # 3% annuo
    years = 20

    pmt = FrenchMortgageEngine.compute_pmt(principal, annual_rate, years)
    assert pmt > 0
    # Per €300k al 3% su 20 anni, la rata teorica è ~€1.663,82
    assert 1650.0 < pmt < 1680.0

    # Test singola rata
    p_part, i_part, new_bal = FrenchMortgageEngine.generate_installment(principal, pmt, annual_rate)
    assert round(p_part + i_part, 2) == round(pmt, 2)
    assert i_part == round(principal * (0.03 / 12.0), 2)  # €750.00 di interessi al mese 1
    assert new_bal < principal
    assert new_bal == round(principal - p_part, 2)

    # Verifica decrescita monotona su 12 rate successive
    curr_debt = principal
    for _ in range(12):
        p, i, next_debt = FrenchMortgageEngine.generate_installment(curr_debt, pmt, annual_rate)
        assert next_debt < curr_debt
        curr_debt = next_debt
    assert curr_debt < principal


# ─────────────────────────────────────────────────────────────
# 3. Test Cash Ledger & Invariante di Solvibilità
# ─────────────────────────────────────────────────────────────

def test_cash_ledger_solvency():
    """Verifica che il cash ledger prevenga saldi negativi e mantenga il buffer di sicurezza."""
    ledger = CashLedger(checking=1000.0, savings=2000.0, emergency=5000.0, brokerage=500.0)

    # Accredito
    ledger.credit_checking(500.0)
    assert ledger.checking == 1500.0

    # Addebito consentito
    debited = ledger.debit_checking(300.0)
    assert debited == 300.0
    assert ledger.checking == 1200.0

    # Tentativo di overdraft: non può scendere sotto zero
    debited_excess = ledger.debit_checking(5000.0)
    assert debited_excess == 1200.0
    assert ledger.checking == 0.0

    # Trasferimento a brokerage rispettando il buffer di 500€
    ledger.credit_checking(2000.0)
    transferred = ledger.transfer_checking_to_brokerage(3000.0)
    # Available = 2000 - 500 = 1500€
    assert transferred == 1500.0
    assert ledger.checking == 500.0
    assert ledger.brokerage == 2000.0


# ─────────────────────────────────────────────────────────────
# 4. Test Simulazione dei 3 Archetipi
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("archetype_key", ["young_accumulator", "fire_decumulation", "hnwi_family"])
def test_archetypes_simulation_integrity(archetype_key):
    """Verifica che tutti e 3 gli archetipi rispettino gli invarianti finanziari e contabili."""
    engine = PortfolioSimulationEngine(offline=True, seed=42)
    res = engine.simulate(archetype_key, years=2)

    # 1. Invarianti generali
    verify_simulation_invariants(res)

    # 2. DataFrame non vuoti
    assert not res.trading_transactions_df.empty
    assert not res.wealth_accounts_df.empty
    assert not res.wealth_cashflow_df.empty
    assert not res.wealth_snapshots_df.empty

    # 3. Solvibilità conti di liquidità
    for _, r in res.wealth_accounts_df.iterrows():
        acc_type = r.get("account_type", r.get("type"))
        if acc_type in ("checking", "savings", "emergency_fund", "brokerage_cash"):
            assert r["balance"] >= 0.0, f"Saldo negativo su {r['name']}: {r['balance']}"

    # 4. Specificità per archetipo
    if archetype_key == "young_accumulator":
        # Zero debiti e zero immobili
        assert res.summary_stats["final_mortgage_remaining"] == 0.0
        assert res.wealth_physical_assets_df.empty
        # Portafoglio deve includere crypto
        crypto_txs = res.trading_transactions_df[res.trading_transactions_df["asset_class"] == "Crypto"]
        assert not crypto_txs.empty

    elif archetype_key == "fire_decumulation":
        # Alta componente obbligazionaria o dividendi
        bnd_txs = res.trading_transactions_df[res.trading_transactions_df["ticker"] == "BND"]
        assert not bnd_txs.empty
        # Dividendi incassati
        assert res.summary_stats["total_dividends_count"] > 0
        # Patrimonio elevato
        assert res.summary_stats["final_net_worth"] > 1_000_000.0

    elif archetype_key == "hnwi_family":
        # Mutuo francese attivo
        assert res.archetype.has_mortgage is True
        assert 0 < res.summary_stats["final_mortgage_remaining"] < res.archetype.mortgage_principal
        # Asset fisici di pregio (orologi, oro, immobili)
        assert not res.wealth_physical_assets_df.empty
        watches = res.wealth_physical_assets_df[res.wealth_physical_assets_df["category"] == "luxury_watches"]
        assert not watches.empty
        gold = res.wealth_physical_assets_df[res.wealth_physical_assets_df["category"] == "precious_metals"]
        assert not gold.empty
        # Fondo pensione al tetto di deducibilità
        assert not res.wealth_pension_plans_df.empty
        assert pytest.approx(res.wealth_pension_plans_df.iloc[0]["tax_deductible_annual"], abs=0.1) == 5164.57


# ─────────────────────────────────────────────────────────────
# 5. Test Conformità Schema CSV Standard
# ─────────────────────────────────────────────────────────────

def test_trading_csv_schema_compliance():
    """Verifica la perfetta aderenza a docs/CSV_Format_Specification.md."""
    engine = PortfolioSimulationEngine(offline=True, seed=42)
    res = engine.simulate("young_accumulator", years=1)
    df_tx = res.trading_transactions_df

    required_cols = [
        "tx_date", "ticker", "tx_type", "quantity", "price",
        "currency", "fees", "asset_class", "notes"
    ]
    for col in required_cols:
        assert col in df_tx.columns, f"Colonna mancante: {col}"

    # Tipi operativi consentiti
    allowed_types = {"buy", "sell", "dividend", "split"}
    assert set(df_tx["tx_type"].unique()).issubset(allowed_types)

    # Dividendi: quantity == 1.0 e price > 0
    div_rows = df_tx[df_tx["tx_type"] == "dividend"]
    if not div_rows.empty:
        assert (div_rows["quantity"] == 1.0).all()
        assert (div_rows["price"] > 0).all()


# ─────────────────────────────────────────────────────────────
# 6. Test Popolamento Database SQLite Idempotente
# ─────────────────────────────────────────────────────────────

def test_database_population_in_sqlite():
    """Verifica l'inserimento atomico e privo di errori nel DB relazionale locale."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_argus_sim.db"

        # Crea schema di base SQLite
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                owner VARCHAR(100) NOT NULL,
                base_currency VARCHAR(3) NOT NULL,
                created_at DATETIME NOT NULL,
                description TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE assets (
                asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(200),
                asset_class VARCHAR(50) NOT NULL,
                currency VARCHAR(3) NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                asset_id INTEGER NOT NULL,
                tx_date DATE NOT NULL,
                tx_type VARCHAR(20) NOT NULL,
                quantity NUMERIC(18, 8) NOT NULL,
                price NUMERIC(18, 6) NOT NULL,
                currency VARCHAR(3) NOT NULL,
                fees NUMERIC(10, 4) NOT NULL,
                notes VARCHAR(255),
                FOREIGN KEY(portfolio_id) REFERENCES portfolios (portfolio_id),
                FOREIGN KEY(asset_id) REFERENCES assets (asset_id)
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner TEXT NOT NULL DEFAULT 'user',
                base_currency TEXT NOT NULL DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_portfolio_risk_links (
                wealth_portfolio_id INTEGER NOT NULL,
                risk_portfolio_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (wealth_portfolio_id, risk_portfolio_id)
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                flow_type TEXT NOT NULL,
                nature TEXT NOT NULL DEFAULT 'essential_need'
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL DEFAULT 'checking',
                institution TEXT NOT NULL DEFAULT 'Banca',
                currency TEXT NOT NULL DEFAULT 'EUR',
                balance REAL NOT NULL DEFAULT 0.0,
                is_active INTEGER NOT NULL DEFAULT 1,
                iban TEXT,
                notes TEXT,
                portfolio_id INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_cashflow (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                tx_date DATE NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                direction TEXT NOT NULL,
                merchant TEXT,
                notes TEXT,
                is_recurring INTEGER NOT NULL DEFAULT 0,
                payment_method TEXT NOT NULL DEFAULT 'Carta / Bonifico',
                tags TEXT,
                portfolio_id INTEGER DEFAULT 1,
                FOREIGN KEY (account_id) REFERENCES wealth_accounts(account_id),
                FOREIGN KEY (category_id) REFERENCES wealth_categories(category_id)
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_physical_assets (
                asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                asset_category TEXT NOT NULL DEFAULT 'luxury_watches',
                brand_or_location TEXT,
                model_or_specs TEXT,
                reference_number TEXT,
                purchase_price REAL NOT NULL DEFAULT 0.0,
                current_market_value REAL NOT NULL DEFAULT 0.0,
                valuation_date DATE,
                notes TEXT,
                portfolio_id INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_pension_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                plan_type TEXT NOT NULL DEFAULT 'fondo_pensione_aperto',
                accumulated_value REAL NOT NULL DEFAULT 0.0,
                monthly_employee_contrib REAL NOT NULL DEFAULT 0.0,
                monthly_employer_contrib REAL NOT NULL DEFAULT 0.0,
                tax_deductible_annual REAL NOT NULL DEFAULT 0.0,
                notes TEXT,
                portfolio_id INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE wealth_networth_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL DEFAULT 1,
                snapshot_date DATE NOT NULL,
                snapshot_name TEXT DEFAULT 'Snapshot Patrimoniale',
                total_net_worth REAL NOT NULL,
                liquid_assets REAL NOT NULL DEFAULT 0.0,
                financial_investments REAL NOT NULL DEFAULT 0.0,
                physical_assets_total REAL NOT NULL DEFAULT 0.0,
                watches_total REAL NOT NULL DEFAULT 0.0,
                real_estate_total REAL NOT NULL DEFAULT 0.0,
                pension_total REAL NOT NULL DEFAULT 0.0,
                total_liabilities REAL NOT NULL DEFAULT 0.0,
                monthly_income_avg REAL NOT NULL DEFAULT 0.0,
                monthly_expense_avg REAL NOT NULL DEFAULT 0.0,
                savings_rate_pct REAL NOT NULL DEFAULT 0.0,
                emergency_runway_months REAL NOT NULL DEFAULT 0.0,
                wealth_health_score REAL NOT NULL DEFAULT 0.0
            );
        """)
        # Pre-popola una categoria per soddisfare il foreign key
        conn.execute("INSERT INTO wealth_categories (category_id, name, flow_type) VALUES (1, 'Stipendio', 'income')")
        conn.commit()
        conn.close()

        # Esegui simulazione
        sim_eng = PortfolioSimulationEngine(offline=True, seed=42)
        res = sim_eng.simulate("hnwi_family", years=1)

        # Primo popolamento
        out1 = populate_argus_database(res, sqlite_path=str(db_path))
        assert out1["status"] == "SUCCESS"

        # Verifica conteggi
        conn_check = sqlite3.connect(str(db_path))
        n_tx = conn_check.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        n_cf = conn_check.execute("SELECT COUNT(*) FROM wealth_cashflow").fetchone()[0]
        n_pa = conn_check.execute("SELECT COUNT(*) FROM wealth_physical_assets").fetchone()[0]
        assert n_tx > 0
        assert n_cf > 0
        assert n_pa > 0

        # Secondo popolamento (idempotenza)
        out2 = populate_argus_database(res, sqlite_path=str(db_path))
        assert out2["status"] == "SUCCESS"
        n_tx_after = conn_check.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert n_tx_after == n_tx  # Non duplicato
        conn_check.close()
