"""
tests/test_universal_ledger_engine.py
Test suite per il modulo Universal One-Ledger Engine (DuckDB & PyArrow).
"""

import os
import pytest
import pandas as pd
import numpy as np

from core.universal_ledger import UniversalLedgerEngine, HAS_DUCKDB, HAS_PYARROW


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_universal_ledger_initialization_and_schema():
    """Verifica che lo schema DDL del One-Ledger venga creato correttamente."""
    engine = UniversalLedgerEngine(db_path=":memory:")
    assert engine.con is not None

    # Verifica presenza tabelle
    tables = engine.con.execute("SHOW TABLES;").fetchdf()["name"].tolist()
    assert "dim_entity" in tables
    assert "dim_asset_master" in tables
    assert "fact_ledger_entry" in tables


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_trading_transactions_ingestion_and_wacp():
    """Verifica l'ingestione di compravendite e il calcolo esatto del WACP/PMC."""
    engine = UniversalLedgerEngine(db_path=":memory:")

    # Creiamo un dataset di transazioni con acquisti multipli e vendita parziale
    # Acquisto 1: 10 azioni AAPL a 150 EUR
    # Acquisto 2: 10 azioni AAPL a 170 EUR -> PMC medio prima della vendita = (1500 + 1700)/20 = 160 EUR
    # Vendita: 5 azioni AAPL a 200 EUR -> rimangono 15 azioni con PMC 160 EUR
    # Acquisto 3: 100 quote VWCE.DE a 100 EUR
    df_tx = pd.DataFrame([
        {"Date": "2024-01-10", "Ticker": "AAPL", "Type": "BUY", "Shares": 10.0, "Price": 150.0, "Commission": 2.0, "Currency": "EUR"},
        {"Date": "2024-02-15", "Ticker": "AAPL", "Type": "BUY", "Shares": 10.0, "Price": 170.0, "Commission": 2.0, "Currency": "EUR"},
        {"Date": "2024-03-01", "Ticker": "AAPL", "Type": "SELL", "Shares": 5.0, "Price": 200.0, "Commission": 2.0, "Currency": "EUR"},
        {"Date": "2024-03-10", "Ticker": "VWCE.DE", "Type": "BUY", "Shares": 100.0, "Price": 100.0, "Commission": 5.0, "Currency": "EUR"}
    ])

    inserted = engine.ingest_trading_transactions(df_tx, entity_id="TEST_FAMILY")
    assert inserted == 4

    # Calcolo consistenze
    open_pos = engine.get_open_positions_with_wacp(entity_id="TEST_FAMILY")
    assert not open_pos.empty
    assert len(open_pos) == 2

    # Verifica AAPL
    aapl_row = open_pos[open_pos["asset_id"] == "AAPL"].iloc[0]
    assert pytest.approx(aapl_row["shares"], rel=1e-3) == 15.0
    # WACP con commissioni:
    # Lot 1: 1500 + 2 = 1502
    # Lot 2: 1700 + 2 = 1702
    # Tot = 3204 / 20 = 160.20 EUR
    assert pytest.approx(aapl_row["pmc_base_eur"], rel=1e-2) == 160.20

    # Verifica VWCE.DE
    vwce_row = open_pos[open_pos["asset_id"] == "VWCE.DE"].iloc[0]
    assert pytest.approx(vwce_row["shares"], rel=1e-3) == 100.0
    assert pytest.approx(vwce_row["pmc_base_eur"], rel=1e-2) == 100.05


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_wealth_items_ingestion_and_balance_sheet():
    """Verifica l'ingestione di conti correnti, immobili e mutui con quadratura di bilancio."""
    engine = UniversalLedgerEngine(db_path=":memory:")

    df_accounts = pd.DataFrame([
        {"account_name": "Conto Corrente Fineco", "balance": 25000.0, "currency": "EUR"},
        {"account_name": "Conto Deposito BBVA", "balance": 15000.0, "currency": "EUR"}
    ])

    df_real_estate = pd.DataFrame([
        {"property_name": "Appartamento Milano", "estimated_value": 350000.0}
    ])

    df_mortgages = pd.DataFrame([
        {"mortgage_name": "Mutuo Intesa Prima Casa", "outstanding_debt": 180000.0}
    ])

    # Transazione mobiliare
    df_tx = pd.DataFrame([
        {"Date": "2024-01-01", "Ticker": "BTP_3.5_2034", "Type": "BUY", "Shares": 50000.0, "Price": 1.0, "Commission": 10.0, "Currency": "EUR"}
    ])
    engine.ingest_trading_transactions(df_tx, entity_id="ENT_MASTER")
    engine.ingest_wealth_items(df_accounts, df_mortgages, df_real_estate, entity_id="ENT_MASTER")

    bs = engine.get_consolidated_balance_sheet(entity_id="ENT_MASTER")

    assert pytest.approx(bs["liquid_investments_eur"], rel=1e-2) == 50010.0
    assert pytest.approx(bs["cash_and_equivalents_eur"], rel=1e-2) == 40000.0
    assert pytest.approx(bs["liquid_assets_total_eur"], rel=1e-2) == 90010.0
    assert pytest.approx(bs["real_estate_assets_eur"], rel=1e-2) == 350000.0
    assert pytest.approx(bs["total_assets_eur"], rel=1e-2) == 440010.0
    assert pytest.approx(bs["mortgage_liabilities_eur"], rel=1e-2) == 180000.0
    # Net Worth = 440010 - 180000 = 260010 EUR
    assert pytest.approx(bs["consolidated_net_worth_eur"], rel=1e-2) == 260010.0


@pytest.mark.skipif(not HAS_DUCKDB or not HAS_PYARROW, reason="DuckDB o PyArrow non disponibili")
def test_arrow_zero_copy_and_olap_queries():
    """Verifica l'interoperabilità zero-copy con PyArrow e le aggregazioni OLAP."""
    engine = UniversalLedgerEngine(db_path=":memory:")

    df_tx = pd.DataFrame([
        {"Date": "2024-01-01", "Ticker": "BTC-EUR", "Type": "BUY", "Shares": 0.5, "Price": 40000.0, "Commission": 10.0, "Currency": "EUR"},
        {"Date": "2024-01-05", "Ticker": "ETH-EUR", "Type": "BUY", "Shares": 5.0, "Price": 2200.0, "Commission": 5.0, "Currency": "EUR"}
    ])
    engine.ingest_trading_transactions(df_tx, entity_id="ENT_CRYPTO")

    # Estrazione PyArrow Table
    arrow_table = engine.get_arrow_table("fact_ledger_entry")
    assert arrow_table is not None
    assert arrow_table.num_rows == 2
    assert "net_amount_base_eur" in arrow_table.column_names

    # Query OLAP con aggregazione per asset_class
    olap_df = engine.execute_raw_olap_query("""
        SELECT a.asset_class, COUNT(*) as tx_count, SUM(l.net_amount_base_eur) as total_volume
        FROM fact_ledger_entry l
        JOIN dim_asset_master a ON l.asset_id = a.asset_id
        GROUP BY a.asset_class;
    """)
    assert not olap_df.empty
    assert olap_df.iloc[0]["asset_class"] == "CRYPTO"
    assert olap_df.iloc[0]["tx_count"] == 2
