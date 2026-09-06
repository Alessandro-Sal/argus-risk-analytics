# ============================================================
# tests/test_backup_engine.py
# Unit tests for ARGUS Backup Engine, Disaster Recovery & Deduplication
# ============================================================

import gzip
import os
import sqlite3
import tempfile
import time
from pathlib import Path
import pandas as pd
import pytest
from sqlalchemy import create_engine

from core.backup_engine import (
    verify_db_integrity,
    perform_hot_backup,
    restore_snapshot,
    list_available_backups,
    prune_old_backups,
)
from core.wealth.wealth_validator import compute_tx_hash
from core.wealth.wealth_db import (
    init_wealth_db,
    save_wealth_account,
    get_wealth_accounts,
    insert_cashflow_tx,
    get_cashflow_records,
)
from core.wealth.wealth_importer import bulk_import_statement


@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "test_argus.db"
        backup_dir = base / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Inizializza un database SQLite con dati di prova
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, balance REAL);")
        cursor.execute("INSERT INTO users (name, balance) VALUES ('Alessandro', 50000.0);")
        cursor.execute("INSERT INTO users (name, balance) VALUES ('Investor_B', 12500.5);")
        conn.commit()
        conn.close()

        yield {"db_path": db_path, "backup_dir": backup_dir, "base": base}


def test_verify_db_integrity(temp_env):
    """Verifica l'integrità strutturale di un database valido e di uno corrotto o mancante."""
    db_path = temp_env["db_path"]
    assert verify_db_integrity(db_path) is True

    # File inesistente
    non_existent = temp_env["base"] / "ghost.db"
    assert verify_db_integrity(non_existent) is False

    # File corrotto con byte casuali
    corrupt_path = temp_env["base"] / "corrupt.db"
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT_A_SQLITE_HEADER_CORRUPTED_BYTES_123456789")
    assert verify_db_integrity(corrupt_path) is False


def test_perform_hot_backup_and_restore(temp_env):
    """Verifica l'intero ciclo di vita: Hot Backup atomico, compressione e restore disaster recovery."""
    db_path = temp_env["db_path"]
    backup_dir = temp_env["backup_dir"]

    # 1. Esegui hot backup
    archive_path = perform_hot_backup(db_path=db_path, backup_dir=backup_dir, max_retention_days=30)
    assert archive_path.exists()
    assert archive_path.name.endswith(".db.gz")
    assert archive_path.stat().st_size > 0

    # 2. Modifica il DB originale (simula perdita o corruzione)
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM users WHERE name = 'Investor_B';")
    conn.execute("UPDATE users SET balance = 0.0 WHERE name = 'Alessandro';")
    conn.commit()
    conn.close()

    # Verifica stato alterato
    conn_mod = sqlite3.connect(str(db_path))
    cnt = conn_mod.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
    conn_mod.close()
    assert cnt == 1

    # 3. Ripristina da snapshot
    success = restore_snapshot(archive_path, target_db_path=db_path)
    assert success is True

    # 4. Verifica che i dati originali siano stati ripristinati perfettamente
    conn_restored = sqlite3.connect(str(db_path))
    rows = conn_restored.execute("SELECT name, balance FROM users ORDER BY id ASC;").fetchall()
    conn_restored.close()

    assert len(rows) == 2
    assert rows[0][0] == "Alessandro"
    assert rows[0][1] == 50000.0
    assert rows[1][0] == "Investor_B"
    assert rows[1][1] == 12500.5


def test_restore_snapshot_corrupted_archive_fallback(temp_env):
    """Verifica che il ripristino da un archivio corrotto fallisca in sicurezza preservando il DB target."""
    db_path = temp_env["db_path"]
    corrupt_archive = temp_env["backup_dir"] / "fake_backup.db.gz"

    # Scrivi un file gzip contenente dati non SQLite
    with gzip.open(corrupt_archive, "wb") as f:
        f.write(b"NOT A VALID SQLITE DATABASE FILE CONT")

    with pytest.raises(RuntimeError):
        restore_snapshot(corrupt_archive, target_db_path=db_path)

    # Il DB originale deve essere intatto
    assert verify_db_integrity(db_path) is True
    conn = sqlite3.connect(str(db_path))
    cnt = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
    conn.close()
    assert cnt == 2


def test_list_and_prune_backups(temp_env):
    """Verifica l'elenco dei backup e il pruning automatico per anzianità."""
    backup_dir = temp_env["backup_dir"]
    db_path = temp_env["db_path"]

    # Crea 2 backup
    b1 = perform_hot_backup(db_path=db_path, backup_dir=backup_dir)
    time.sleep(1.1)
    b2 = perform_hot_backup(db_path=db_path, backup_dir=backup_dir)

    backups = list_available_backups(backup_dir)
    assert len(backups) >= 2
    assert "filename" in backups[0]
    assert "size_kb" in backups[0]
    assert "created_at" in backups[0]

    # Simula anzianità di b1 impostando mtime a 45 giorni fa
    old_time = time.time() - (45 * 86400)
    os.utime(str(b1), (old_time, old_time))

    pruned = prune_old_backups(backup_dir, max_retention_days=30)
    assert pruned == 1
    assert not b1.exists()
    assert b2.exists()


def test_compute_tx_hash_determinism():
    """Verifica che compute_tx_hash produca un hash SHA-256 canonico, deterministico e insensibile a maiuscole/spazi."""
    h1 = compute_tx_hash(
        account_ref="Revolut Main",
        tx_date="2026-08-15",
        amount=120.50,
        direction="outflow",
        merchant="Apple Store"
    )
    h2 = compute_tx_hash(
        account_ref="  revolut main  ",
        tx_date="2026-08-15",
        amount=120.5,
        direction="OUTFLOW",
        merchant="apple store"
    )
    h3 = compute_tx_hash(
        account_ref="Revolut Main",
        tx_date="2026-08-15",
        amount=120.51,  # Importo differente
        direction="outflow",
        merchant="Apple Store"
    )

    assert len(h1) == 64
    assert h1 == h2  # Stesso hash deterministico
    assert h1 != h3  # Modifica importo genera hash diverso


def test_cashflow_deduplication_and_idempotency():
    """Verifica che il ricaricamento di estratti conto con righe identiche sia idempotente."""
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    # 1. Crea conto di prova
    acc_id = save_wealth_account(engine, {
        "name": "Conto Deduplica",
        "institution": "Banca Intesa",
        "account_type": "checking",
        "balance": 1000.0
    })

    # 2. Prepara un batch di transazioni con tx_hash
    tx_hash_1 = compute_tx_hash(acc_id, "2026-08-01", 100.0, "outflow", "Amazon Prime")
    tx_hash_2 = compute_tx_hash(acc_id, "2026-08-02", 50.0, "outflow", "Bar Roma")

    df_tx = pd.DataFrame([
        {
            "category_id": 1,
            "tx_date": "2026-08-01",
            "amount": 100.0,
            "direction": "outflow",
            "merchant": "Amazon Prime",
            "notes": "Abbonamento annuale",
            "payment_method": "Carta di Credito",
            "tx_hash": tx_hash_1
        },
        {
            "category_id": 1,
            "tx_date": "2026-08-02",
            "amount": 50.0,
            "direction": "outflow",
            "merchant": "Bar Roma",
            "notes": "Colazione",
            "payment_method": "Bancomat",
            "tx_hash": tx_hash_2
        }
    ])

    # Primo import
    c1 = bulk_import_statement(engine, account_id=acc_id, df_categorized=df_tx)
    assert c1 == 2

    # Verifica saldo: 1000 - 100 - 50 = 850
    accounts = get_wealth_accounts(engine)
    acc_row = accounts[accounts["account_id"] == acc_id].iloc[0]
    assert acc_row["balance"] == 850.0

    # Secondo import IDENTICO (simula re-upload dello stesso estratto conto)
    c2 = bulk_import_statement(engine, account_id=acc_id, df_categorized=df_tx)
    assert c2 == 0  # Tutte e due le transazioni scartate per deduplicazione

    # Il saldo NON deve essere decurtato una seconda volta!
    accounts_after = get_wealth_accounts(engine)
    acc_row_after = accounts_after[accounts_after["account_id"] == acc_id].iloc[0]
    assert acc_row_after["balance"] == 850.0

    # Il numero di record nel libro mastro deve rimanere 2
    records = get_cashflow_records(engine, account_id=acc_id)
    assert len(records) == 2
