"""
tests/test_bitemporal_engine.py
Test suite per il modulo Bitemporal Persistence Engine, Audit Trail Crittografico e Time-Travel Query.
"""

from datetime import datetime
import pytest
import pandas as pd
import numpy as np

from core.bitemporal_engine import BitemporalLedgerEngine, HAS_DUCKDB
from core.universal_ledger import UniversalLedgerEngine


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_bitemporal_engine_initialization_and_schema():
    """Verifica che lo schema DDL bitemporale venga creato correttamente in DuckDB."""
    engine = BitemporalLedgerEngine(db_path=":memory:")
    assert engine.con is not None

    tables = engine.con.execute("SHOW TABLES;").fetchdf()["name"].tolist()
    assert "audit_decision_log" in tables
    assert "bitemporal_transactions" in tables
    assert "bitemporal_asset_appraisals" in tables
    assert "bitemporal_position_snapshots" in tables


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_late_arriving_event_and_audit_replay():
    """
    Verifica il caso cardine dei fatti tardivi (Late-Arriving Data):
    Dividendo pagato il 15 Marzo ma comunicato dal broker il 20 Marzo.
    - Query con System Time al 18 Marzo: il dividendo NON deve apparire (Audit Replay).
    - Query con System Time al 21 Marzo: il dividendo DEVE apparire (Economic Truth).
    """
    engine = BitemporalLedgerEngine(db_path=":memory:")
    engine.seed_demonstration_scenario(portfolio_id="AUDIT_TEST_PORTFOLIO")

    # 1. Audit Replay: cosa sapeva il comitato rischi il 18 Marzo alle 10:00?
    df_known_march18 = engine.time_travel_query(
        portfolio_id="AUDIT_TEST_PORTFOLIO",
        as_at_valid_time="2026-03-15 23:59:59",
        as_of_system_time="2026-03-18 10:00:00"
    )
    assert not df_known_march18.empty
    assert "TX_DIV_VWCE_004" not in df_known_march18["tx_business_id"].values
    assert len(df_known_march18) == 3  # Solo Cash In, BTP Buy, VWCE Buy

    # 2. Economic Truth: cosa sappiamo oggi rispetto al 15 Marzo?
    df_known_march21 = engine.time_travel_query(
        portfolio_id="AUDIT_TEST_PORTFOLIO",
        as_at_valid_time="2026-03-15 23:59:59",
        as_of_system_time="2026-03-21 10:00:00"
    )
    assert not df_known_march21.empty
    assert "TX_DIV_VWCE_004" in df_known_march21["tx_business_id"].values
    assert len(df_known_march21) == 4

    div_row = df_known_march21[df_known_march21["tx_business_id"] == "TX_DIV_VWCE_004"].iloc[0]
    assert div_row["operation_type"] == "DIVIDEND"
    assert div_row["asset_id"] == "VWCE.DE"


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_historical_correction_preserves_history():
    """
    Verifica che una rettifica retroattiva chiuda la versione precedente
    senza cancellarla fisicamente dal database (intervalli sys_from e sys_to).
    """
    engine = BitemporalLedgerEngine(db_path=":memory:")
    pid = "CORRECTION_TEST"

    # Inserimento transazione iniziale (al 2026-02-01)
    engine.record_transaction(
        tx_business_id="TX_TEST_001",
        portfolio_id=pid,
        asset_id="AAPL",
        operation_type="BUY",
        quantity=100.0,
        unit_price=150.0,
        valid_from="2026-02-01 10:00:00",
        recorded_by="INITIAL_IMPORT",
        custom_sys_from="2026-02-01 10:05:00"
    )

    # Correzione eseguita il 2026-02-10 (nuovo prezzo 148.0)
    engine.correct_historical_transaction(
        tx_business_id="TX_TEST_001",
        new_quantity=100.0,
        new_unit_price=148.0,
        reason="Rettifica prezzo eseguito da broker",
        actor_id="USER:Trader",
        custom_sys_from="2026-02-10 12:00:00"
    )

    # Nel database fisico devono esistere ENTRAMBE le righe
    all_rows = engine.con.execute(
        "SELECT row_uuid, quantity, unit_price, sys_op_type, sys_from, sys_to FROM bitemporal_transactions WHERE tx_business_id = 'TX_TEST_001' ORDER BY sys_from ASC"
    ).df()
    assert len(all_rows) == 2

    # Prima versione chiusa a sys_to = 2026-02-10 12:00:00
    row_old = all_rows.iloc[0]
    assert row_old["sys_op_type"] == "INSERT"
    assert row_old["unit_price"] == 150.0
    assert str(row_old["sys_to"]).startswith("2026-02-10 12:00:00")

    # Nuova versione attiva aperta con sys_from = 2026-02-10 12:00:00
    row_new = all_rows.iloc[1]
    assert row_new["sys_op_type"] == "CORRECTION"
    assert row_new["unit_price"] == 148.0
    assert str(row_new["sys_from"]).startswith("2026-02-10 12:00:00")
    assert str(row_new["sys_to"]).startswith("9999-12-31")

    # Query al 5 Febbraio con stato di conoscenza del 5 Febbraio
    df_past = engine.time_travel_query(pid, "2026-02-05 12:00:00", "2026-02-05 12:00:00")
    assert df_past.iloc[0]["unit_price"] == 150.0

    # Query al 5 Febbraio con stato di conoscenza odierno (post-10 Febbraio)
    df_current = engine.time_travel_query(pid, "2026-02-05 12:00:00", "2026-02-15 12:00:00")
    assert df_current.iloc[0]["unit_price"] == 148.0


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_cryptographic_hash_chain_and_tamper_detection():
    """
    Verifica che l'audit trail ad append-only hash chain garantisca l'integrità
    e rilevi istantaneamente qualsiasi manomissione fisica di un record.
    """
    engine = BitemporalLedgerEngine(db_path=":memory:")
    
    # Registra 5 decisioni sequenziali
    for i in range(1, 6):
        engine.log_decision(
            decision_type=f"DECISION_TYPE_{i}",
            entity_id="FAMILY_OFFICE_ALPHA",
            actor_id=f"ACTOR_{i}",
            rationale=f"Motivazione compliance step {i}",
            payload={"step": i, "weight": i * 0.1}
        )

    # 1. Verifica iniziale: deve essere integra al 100%
    is_valid, msg, count = engine.verify_audit_chain_integrity()
    assert is_valid is True
    assert count == 5

    # 2. Simulazione di attacco / manomissione diretta su DB
    # Modifichiamo il payload della decisione #3
    engine.con.execute("""
        UPDATE audit_decision_log 
        SET canonical_payload_json = '{"step":3,"weight":0.999}' 
        WHERE sequence_id = 3
    """)

    # 3. L'audit deve fallire rilevando la contraffazione
    is_valid_hacked, msg_hacked, seq_hacked = engine.verify_audit_chain_integrity()
    assert is_valid_hacked is False
    assert seq_hacked == 3
    assert "Manomissione rilevata" in msg_hacked


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_merkle_root_generation_and_determinism():
    """Verifica il calcolo deterministico e la sensibilità del Merkle Tree."""
    records_1 = [
        {"tx_id": "TX1", "qty": 100, "price": 50.0},
        {"tx_id": "TX2", "qty": 200, "price": 25.0},
        {"tx_id": "TX3", "qty": 50, "price": 10.0}
    ]
    records_2 = list(reversed(records_1))  # Stessi record ordine inverso
    records_tampered = [
        {"tx_id": "TX1", "qty": 100, "price": 50.0},
        {"tx_id": "TX2", "qty": 200, "price": 25.01},  # Alterato 1 centesimo
        {"tx_id": "TX3", "qty": 50, "price": 10.0}
    ]

    root_1 = BitemporalLedgerEngine.generate_merkle_root(records_1)
    root_2 = BitemporalLedgerEngine.generate_merkle_root(records_2)
    root_tampered = BitemporalLedgerEngine.generate_merkle_root(records_tampered)

    assert len(root_1) == 64
    # Invarianza all'ordine di inserimento (grazie a sorting interno deterministico)
    assert root_1 == root_2
    # Sensibilità alla minima variazione di 1 centesimo
    assert root_1 != root_tampered


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_detect_retroactive_drifts():
    """Verifica l'identificazione forense dei drift tra due stati di conoscenza."""
    engine = BitemporalLedgerEngine(db_path=":memory:")
    engine.seed_demonstration_scenario("DRIFT_PORTFOLIO")

    # Confronto tra prima dell'arrivo del dividendo (18 Marzo) e dopo (21 Marzo) per la data 15 Marzo
    drift = engine.detect_retroactive_drifts(
        portfolio_id="DRIFT_PORTFOLIO",
        as_at_valid_time="2026-03-15 23:59:59",
        sys_time_before="2026-03-18 10:00:00",
        sys_time_after="2026-03-21 10:00:00"
    )

    assert drift["has_drift"] is True
    assert drift["new_transactions_count"] == 1
    assert drift["new_transactions"][0]["tx_business_id"] == "TX_DIV_VWCE_004"


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_universal_ledger_sync_bridge():
    """Verifica il ponte di sincronizzazione tra UniversalLedgerEngine e BitemporalLedgerEngine."""
    u_engine = UniversalLedgerEngine(db_path=":memory:")
    b_engine = BitemporalLedgerEngine(db_path=":memory:")

    df_tx = pd.DataFrame([
        {"Date": "2024-01-10", "Ticker": "AAPL", "Type": "BUY", "Shares": 10.0, "Price": 150.0, "Commission": 2.0, "Currency": "EUR"},
        {"Date": "2024-02-15", "Ticker": "VWCE.DE", "Type": "BUY", "Shares": 50.0, "Price": 100.0, "Commission": 3.0, "Currency": "EUR"}
    ])

    inserted = u_engine.ingest_trading_transactions(df_tx, entity_id="BRIDGE_TEST")
    assert inserted == 2

    # Sincronizza nel motore bitemporale
    synced = u_engine.sync_to_bitemporal_engine(b_engine, entity_id="BRIDGE_TEST")
    assert synced == 2

    # Verifica presenza nel bitemporale
    df_bt = b_engine.time_travel_query("BRIDGE_TEST", "2024-03-01 00:00:00")
    assert len(df_bt) == 2
    assert set(df_bt["asset_id"].tolist()) == {"AAPL", "VWCE.DE"}

    # Verifica integrità della catena decisionale generata
    is_valid, _, cnt = b_engine.verify_audit_chain_integrity()
    assert is_valid is True
    assert cnt >= 1


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_ingest_portfolio_dataframe_and_available_portfolios():
    """Verifica l'ingestione diretta di un DataFrame utente e la scoperta dei portafogli."""
    b_engine = BitemporalLedgerEngine(db_path=":memory:")
    
    # Inizialmente vuoto o solo demo
    assert b_engine.get_available_portfolios() == []
    
    # Ingestione DataFrame con schema standard ARGUS
    df_user = pd.DataFrame([
        {"tx_date": "2025-01-15 10:00:00", "ticker": "CSSPX.MI", "tx_type": "buy", "quantity": 20.0, "price": 450.0, "currency": "EUR", "fees": 5.0},
        {"tx_date": "2025-02-20 11:00:00", "ticker": "MEUD.PA", "tx_type": "buy", "quantity": 100.0, "price": 80.0, "currency": "EUR", "fees": 3.0},
        {"tx_date": "2025-03-01 09:30:00", "ticker": "CSSPX.MI", "tx_type": "dividend", "quantity": 20.0, "price": 2.5, "currency": "EUR", "fees": 0.0},
    ])
    
    rows = b_engine.ingest_portfolio_dataframe(df_user, portfolio_id="PORTAFOGLIO_ALESSANDRO")
    assert rows == 3
    
    # Verifica elenco portafogli disponibili
    available = b_engine.get_available_portfolios()
    assert "PORTAFOGLIO_ALESSANDRO" in available
    
    # Verifica query time-travel prima e dopo il dividendo
    # 1. Al 25 Febbraio (prima del dividendo del 1 Marzo)
    df_feb = b_engine.time_travel_query("PORTAFOGLIO_ALESSANDRO", "2025-02-25 23:59:59")
    # Include: 1 Cash Init + 2 Buy = 3 transazioni
    assert len(df_feb) == 3
    assert set(df_feb["asset_id"].tolist()) == {"EUR_CASH", "CSSPX.MI", "MEUD.PA"}
    
    # 2. Al 5 Marzo (dopo il dividendo)
    df_mar = b_engine.time_travel_query("PORTAFOGLIO_ALESSANDRO", "2025-03-05 23:59:59")
    assert len(df_mar) == 4
    
    # 3. Ricostruzione contabile Point-in-Time
    recon = b_engine.reconstruct_portfolio_at_times("PORTAFOGLIO_ALESSANDRO", "2025-03-05 23:59:59")
    assert recon["portfolio_id"] == "PORTAFOGLIO_ALESSANDRO"
    assert recon["positions_count"] == 2  # CSSPX e MEUD
    assert recon["cash_balance_eur"] > 0
    assert recon["total_book_value_eur"] > 0
    
    # 4. Verifica integrità crittografica della catena
    is_valid, msg, cnt = b_engine.verify_audit_chain_integrity()
    assert is_valid is True
    assert cnt >= 1


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_ingest_gsheets_portfolio_and_time_travel():
    """Verifica l'ingestione e la ricostruzione bitemporale di portafogli strutturati da Google Sheets."""
    b_engine = BitemporalLedgerEngine(db_path=":memory:")
    b_engine.seed_demonstration_scenario()
    
    # DataFrame con schema tipico restituito dall'ETL Google Sheets / Multi-Portfolio
    df_gsheets = pd.DataFrame([
        {
            "tx_id": 1,
            "tx_date": "2024-03-10",
            "tx_type": "BUY",
            "quantity": 10.0,
            "price": 150.0,
            "currency": "EUR",
            "fees": 2.5,
            "ticker": "AAPL",
            "asset_class": "stock",
            "notes": "Total GSheet (Stocks): 1502.50 EUR"
        },
        {
            "tx_id": 2,
            "tx_date": "2024-05-15",
            "tx_type": "BUY",
            "quantity": 5.0,
            "price": 300.0,
            "currency": "EUR",
            "fees": 3.0,
            "ticker": "MSFT",
            "asset_class": "stock",
            "notes": "Total GSheet (Stocks): 1503.00 EUR"
        },
        {
            "tx_id": 3,
            "tx_date": "2024-08-20",
            "tx_type": "BUY",
            "quantity": 0.5,
            "price": 50000.0,
            "currency": "EUR",
            "fees": 15.0,
            "ticker": "BTC-EUR",
            "asset_class": "crypto",
            "notes": "Total GSheet (Crypto): 25015.00 EUR"
        },
        {
            "tx_id": 4,
            "tx_date": "2024-11-01",
            "tx_type": "DIVIDEND",
            "quantity": 10.0,
            "price": 1.25,
            "currency": "EUR",
            "fees": 0.0,
            "ticker": "AAPL",
            "asset_class": "stock",
            "notes": "Dividendo Q3 AAPL"
        }
    ])
    
    # Ingestione portafoglio Google Sheets Master
    pname_master = "Master Wealth Google Sheets"
    cnt_master = b_engine.ingest_portfolio_dataframe(df_gsheets, portfolio_id=pname_master, recorded_by="GSHEETS_LIVE_SYNC")
    assert cnt_master == 4
    
    # Ingestione sotto-portafoglio Crypto separato
    df_crypto_sub = df_gsheets[df_gsheets["asset_class"] == "crypto"].copy()
    pname_crypto = "Wealth Crypto Portfolio"
    cnt_crypto = b_engine.ingest_portfolio_dataframe(df_crypto_sub, portfolio_id=pname_crypto, recorded_by="GSHEETS_CRYPTO")
    assert cnt_crypto == 1
    
    # Verifica elenco portafogli disponibili contemporaneamente
    available = b_engine.get_available_portfolios()
    assert "DEMO_FAMILY_OFFICE" in available
    assert pname_master in available
    assert pname_crypto in available
    
    # Ricostruzione Point-in-Time al 1 Giugno 2024 (prima di BTC e del dividendo AAPL)
    recon_jun = b_engine.reconstruct_portfolio_at_times(pname_master, "2024-06-01 23:59:59")
    assert recon_jun["portfolio_id"] == pname_master
    assert recon_jun["positions_count"] == 2  # Solo AAPL e MSFT
    tickers_jun = {p["asset_id"] for p in recon_jun["positions"]}
    assert tickers_jun == {"AAPL", "MSFT"}
    assert recon_jun["cash_balance_eur"] > 0
    assert recon_jun["total_book_value_eur"] > 0
    
    # Ricostruzione Point-in-Time a fine anno 2024 (tutti gli asset inclusi)
    recon_dec = b_engine.reconstruct_portfolio_at_times(pname_master, "2024-12-31 23:59:59")
    assert recon_dec["positions_count"] == 3  # AAPL, MSFT, BTC-EUR
    tickers_dec = {p["asset_id"] for p in recon_dec["positions"]}
    assert tickers_dec == {"AAPL", "MSFT", "BTC-EUR"}
    
    # Sigillo Merkle Tree su transazioni Google Sheets
    txs_master = b_engine.con.execute(
        "SELECT * FROM bitemporal_transactions WHERE portfolio_id = ? AND sys_to = ?::TIMESTAMP",
        [pname_master, b_engine.INFINITY_TIMESTAMP]
    ).fetchdf()
    merkle_seal = b_engine.generate_merkle_root(txs_master.to_dict(orient="records"))
    assert len(merkle_seal) == 64
    assert all(c in "0123456789abcdef" for c in merkle_seal)
    
    # Catena crittografica SHA-256 integra
    is_valid, msg, block_cnt = b_engine.verify_audit_chain_integrity()
    assert is_valid is True
    assert block_cnt >= 5


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_bitemporal_reconstruction_fifo_sales():
    """Verifica che vendite parziali deducano correttamente il PMC e il costo secondo logica FIFO."""
    b_engine = BitemporalLedgerEngine(db_path=":memory:")
    
    df_lots = pd.DataFrame([
        # Lotto 1: 10 quote a 100 EUR = 1000 EUR
        {"date": "2024-01-01", "action": "BUY", "quantity": 10.0, "price": 100.0, "currency": "EUR", "fees": 0.0, "ticker": "TEST"},
        # Lotto 2: 10 quote a 200 EUR = 2000 EUR
        {"date": "2024-01-02", "action": "BUY", "quantity": 10.0, "price": 200.0, "currency": "EUR", "fees": 0.0, "ticker": "TEST"},
        # Vendita: 5 quote (consuma 5 quote dal lotto 1 a 100 EUR)
        {"date": "2024-01-03", "action": "SELL", "quantity": 5.0, "price": 250.0, "currency": "EUR", "fees": 0.0, "ticker": "TEST"},
    ])
    
    b_engine.ingest_portfolio_dataframe(df_lots, portfolio_id="FIFO_TEST")
    recon = b_engine.reconstruct_portfolio_at_times("FIFO_TEST", "2024-01-04")
    
    assert recon["positions_count"] == 1
    pos = recon["positions"][0]
    # Rimanenti: 5 quote lotto 1 (5*100=500) + 10 quote lotto 2 (10*200=2000) = 2500 EUR
    # Totale quote: 15. PMC atteso = 2500 / 15 = 166.67 EUR
    assert pos["shares"] == 15.0
    assert pos["cost_value_eur"] == 2500.0
    assert pos["wacp_eur"] == 166.67


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_stable_sorting_intraday_trades_eliminates_phantom_holdings():
    """
    Verifica che operazioni intraday dello stesso giorno (es. BUY 100 -> SELL 100 -> BUY 200 -> SELL 200)
    preservino il loro ordine relativo tramite stable sort e che la posizione finale si azzeri a 0 titoli
    senza generare posizioni fantasma.
    """
    b_engine = BitemporalLedgerEngine(db_path=":memory:")
    
    df_intraday = pd.DataFrame([
        {"tx_date": "2023-12-08", "ticker": "USDT-EUR", "tx_type": "buy", "quantity": 1074.92, "price": 0.930302, "fees": 0.0},
        {"tx_date": "2023-12-08", "ticker": "USDT-EUR", "tx_type": "sell", "quantity": 1074.92, "price": 0.929725, "fees": 0.0},
        {"tx_date": "2023-12-08", "ticker": "USDT-EUR", "tx_type": "buy", "quantity": 1098.41, "price": 0.930135, "fees": 0.0},
        {"tx_date": "2023-12-08", "ticker": "USDT-EUR", "tx_type": "sell", "quantity": 1098.41, "price": 0.929735, "fees": 0.0},
    ])
    
    b_engine.ingest_portfolio_dataframe(df_intraday, portfolio_id="INTRADAY_ZERO_TEST")
    recon = b_engine.reconstruct_portfolio_at_times("INTRADAY_ZERO_TEST", "2023-12-09 00:00:00")
    
    # Nessun titolo residuo aperto
    assert recon["positions_count"] == 0
    assert len(recon["positions"]) == 0
    assert recon["positions_cost_eur"] == 0.0


@pytest.mark.skipif(not HAS_DUCKDB, reason="DuckDB non installato nell'ambiente")
def test_peak_cash_deficit_model_prevents_artificial_inflation():
    """
    Verifica che il modello Peak Cash Deficit inietti esattamente il fabbisogno reale di cassa
    senza moltiplicare forfettariamente per 110% tutti gli acquisti lordi della storia del portafoglio.
    """
    b_engine = BitemporalLedgerEngine(db_path=":memory:")
    
    # Esempio: Compra 100 a 100 (€ 10.000), vende a 120 (€ 12.000), ricompra con il ricavato 100 a 110 (€ 11.000)
    # Totale acquisti lordi: € 21.000. Il vecchio modello iniettava € 23.100.
    # Il deficit massimo reale è € 10.000 (all'acquisto iniziale).
    df_reinvest = pd.DataFrame([
        {"tx_date": "2024-01-01", "ticker": "ASSET_A", "tx_type": "buy", "quantity": 100.0, "price": 100.0, "fees": 0.0},
        {"tx_date": "2024-01-10", "ticker": "ASSET_A", "tx_type": "sell", "quantity": 100.0, "price": 120.0, "fees": 0.0},
        {"tx_date": "2024-01-20", "ticker": "ASSET_B", "tx_type": "buy", "quantity": 100.0, "price": 110.0, "fees": 0.0},
    ])
    
    b_engine.ingest_portfolio_dataframe(df_reinvest, portfolio_id="REINVEST_TEST")
    recon = b_engine.reconstruct_portfolio_at_times("REINVEST_TEST", "2024-01-25 00:00:00")
    
    # Posizione aperta: 100 ASSET_B a 110 = 11.000 EUR
    assert recon["positions_count"] == 1
    assert recon["positions_cost_eur"] == 11000.0
    
    # Saldo cassa residuo: 10.000 (capitale iniziale iniettato) - 10.000 + 12.000 - 11.000 = 1.000 EUR (profitto netto)
    assert recon["cash_balance_eur"] == 1000.0
    
    # Valore contabile book: Cassa (€ 1.000) + Costo Posizioni (€ 11.000) = € 12.000
    assert recon["total_book_value_eur"] == 12000.0




