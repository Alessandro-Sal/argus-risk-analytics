import io
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from core.ingestion_utils import read_tabular_stream
from core.wealth.universal_bank_parser import reconcile_internal_transfers
from core.wealth.wealth_db import (
    init_wealth_db,
    save_wealth_account,
    get_wealth_accounts,
    bulk_insert_cashflow_tx,
    get_cashflow_records
)


def test_read_tabular_stream_delimiters():
    # 1. Comma separated
    csv_comma = "Date,Description,Amount\n2026-01-15,Stipendio,2500.00\n2026-01-16,Spesa,50.00"
    df_comma = read_tabular_stream(csv_comma.encode("utf-8"), filename="test.csv")
    assert len(df_comma) == 2
    assert "Description" in df_comma.columns
    assert df_comma.iloc[0]["Description"] == "Stipendio"

    # 2. Semicolon separated (European CSV)
    csv_semi = "Data;Descrizione;Importo\n15/01/2026;Bonifico Stipendio;2500,00\n16/01/2026;Supermercato;45,50"
    df_semi = read_tabular_stream(csv_semi.encode("utf-8"), filename="estratto_conto.csv")
    assert len(df_semi) == 2
    assert "Descrizione" in df_semi.columns
    assert df_semi.iloc[1]["Descrizione"] == "Supermercato"

    # 3. Tab separated
    tsv_data = "Date\tMerchant\tValue\n2026-02-01\tAmazon\t29.99\n2026-02-02\tNetflix\t17.99"
    df_tsv = read_tabular_stream(tsv_data.encode("utf-8"), filename="export.tsv")
    assert len(df_tsv) == 2
    assert "Merchant" in df_tsv.columns
    assert df_tsv.iloc[0]["Merchant"] == "Amazon"


def test_read_tabular_stream_encodings():
    # Latin-1 with accented characters
    text_latin1 = "Data,Causale,Importo\n2026-03-01,Caffè e Tè,-3.50\n2026-03-02,Société Générale,150.00"
    bytes_latin1 = text_latin1.encode("latin-1")
    df_latin1 = read_tabular_stream(bytes_latin1, filename="bank_latin1.csv")
    assert len(df_latin1) == 2
    assert df_latin1.iloc[0]["Causale"] == "Caffè e Tè"


def test_reconcile_internal_transfers():
    # Setup dataframe with 2 matching transactions across 2 accounts within 1 day
    txs = pd.DataFrame([
        {
            "date": "2026-01-10",
            "account_name": "Conto Corrente Intesa",
            "amount": 1000.0,
            "direction": "outflow",
            "description": "Giroconto vs BBVA",
            "is_transfer": 0
        },
        {
            "date": "2026-01-11",
            "account_name": "Conto Deposito BBVA",
            "amount": 1000.0,
            "direction": "inflow",
            "description": "Accredito da Intesa",
            "is_transfer": 0
        },
        {
            "date": "2026-01-12",
            "account_name": "Conto Corrente Intesa",
            "amount": 50.0,
            "direction": "outflow",
            "description": "Spesa Esselunga",
            "is_transfer": 0
        }
    ])

    reconciled_df, pairs_cnt = reconcile_internal_transfers(txs, max_days_diff=2)
    assert pairs_cnt == 1
    assert len(reconciled_df) == 3
    # The first two movements should be recognized as internal transfer
    assert reconciled_df.iloc[0]["is_transfer"] == 1
    assert reconciled_df.iloc[0]["direction"] == "transfer"
    assert reconciled_df.iloc[1]["is_transfer"] == 1
    assert reconciled_df.iloc[1]["direction"] == "transfer"
    # Esselunga remains regular outflow
    assert reconciled_df.iloc[2]["is_transfer"] == 0
    assert reconciled_df.iloc[2]["direction"] == "outflow"


def test_bulk_insert_cashflow_tx_idempotence():
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    # Crea un conto con saldo iniziale 1000.0
    acc_id = save_wealth_account(engine, {
        "portfolio_id": 1,
        "name": "Conto Test Ingestion",
        "institution": "Banca Test",
        "account_type": "checking",
        "balance": 1000.0,
        "currency": "EUR"
    })

    records = [
        {
            "portfolio_id": 1,
            "account_id": acc_id,
            "category_id": 1,
            "tx_date": "2026-01-15",
            "amount": 200.0,
            "direction": "outflow",
            "merchant": "Euronics",
            "notes": "Acquisto monitor",
            "tx_hash": "hash_euronics_001"
        },
        {
            "portfolio_id": 1,
            "account_id": acc_id,
            "category_id": 1,
            "tx_date": "2026-01-16",
            "amount": 500.0,
            "direction": "inflow",
            "merchant": "Bonifico Cliente",
            "notes": "Consulenza",
            "tx_hash": "hash_inflow_002"
        },
        # Intra-batch duplicate of the first record
        {
            "portfolio_id": 1,
            "account_id": acc_id,
            "category_id": 1,
            "tx_date": "2026-01-15",
            "amount": 200.0,
            "direction": "outflow",
            "merchant": "Euronics",
            "notes": "Acquisto monitor",
            "tx_hash": "hash_euronics_001"
        }
    ]

    # Primo inserimento: 2 record unici inseriti, 1 duplicato intra-batch scartato
    ins_cnt, dup_cnt = bulk_insert_cashflow_tx(engine, records, deduplicate=True)
    assert ins_cnt == 2
    assert dup_cnt == 1

    # Verifica saldo: 1000.0 - 200.0 + 500.0 = 1300.0
    accs = get_wealth_accounts(engine)
    assert accs.loc[accs["account_id"] == acc_id, "balance"].iloc[0] == 1300.0

    # Secondo inserimento degli stessi record (simula re-upload dello stesso file)
    ins_cnt2, dup_cnt2 = bulk_insert_cashflow_tx(engine, records, deduplicate=True)
    assert ins_cnt2 == 0
    assert dup_cnt2 == 3

    # Il saldo NON deve cambiare
    accs_after = get_wealth_accounts(engine)
    assert accs_after.loc[accs_after["account_id"] == acc_id, "balance"].iloc[0] == 1300.0

    # I record nel libro mastro devono rimanere 2
    cf_records = get_cashflow_records(engine, account_id=acc_id)
    assert len(cf_records) == 2
