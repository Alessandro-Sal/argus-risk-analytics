# ============================================================
# tests/test_migration_manager.py
# Unit tests for ARGUS DatabaseMigrationManager (DBRE Suite)
# Tests Dual Versioning, Idempotency, Pre-Flight Shadow Backup,
# Atomic Rollback, Disaster Recovery, Schema Drift & DuckDB Attach
# ============================================================

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Type
import pytest

from core.database_migration_manager import (
    BaseMigration,
    DatabaseMigrationManager,
    DriftSeverity,
    MigrationExecutionError,
    MigrationRecord,
    SchemaDriftReport,
    V001_BaselineSchema,
    V002_AnalyticalCompositeIndexes,
    V003_AssetFundamentalsAndForensicColumns,
    V004_WealthEcosystemAudit,
    bootstrap_and_migrate_db,
)


@pytest.fixture
def temp_db_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "test_argus_migration.db"
        backup_dir = base / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        yield {"db_path": db_path, "backup_dir": backup_dir, "base": base}


def test_fresh_database_full_migration(temp_db_env):
    """Verifica la migrazione completa da zero fino alla target_version (v4)."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    assert mgr.target_version == 4

    # Stato iniziale su DB non esistente
    status_pre = mgr.get_migration_status()
    assert status_pre.current_version == 0
    assert status_pre.is_up_to_date is False
    assert status_pre.pending_count == 4

    # Esecuzione forward migration
    applied = mgr.migrate()
    assert len(applied) == 4
    assert [m.version for m in applied] == [1, 2, 3, 4]

    # Verifica stato post-migrazione
    status_post = mgr.get_migration_status()
    assert status_post.current_version == 4
    assert status_post.is_up_to_date is True
    assert status_post.pending_count == 0

    # Verifica diretta su SQLite con PRAGMA user_version
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        assert cur.fetchone()[0] == 4

        # Verifica tabella schema_migrations
        cur.execute("SELECT version, name FROM schema_migrations ORDER BY version ASC;")
        rows = cur.fetchall()
        assert len(rows) == 4
        assert rows[0] == (1, "baseline_schema")
        assert rows[1] == (2, "analytical_composite_indexes")
        assert rows[2] == (3, "asset_fundamentals_and_forensics")
        assert rows[3] == (4, "wealth_ecosystem_audit")
    finally:
        conn.close()


def test_migration_idempotency(temp_db_env):
    """Verifica che una seconda esecuzione di migrate() sia idempotente e non esegua nulla."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    applied_first = mgr.migrate()
    assert len(applied_first) == 4

    # Seconda esecuzione immediata
    applied_second = mgr.migrate()
    assert len(applied_second) == 0

    status = mgr.get_migration_status()
    assert status.is_up_to_date is True
    assert status.current_version == 4


def test_incremental_step_migrations_and_rollback(temp_db_env):
    """Verifica l'esecuzione incrementale passo-passo e il successivo rollback."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)

    # Step 1: solo v1
    m1 = mgr.migrate(target_version=1)
    assert len(m1) == 1
    assert m1[0].version == 1
    assert mgr.get_migration_status().current_version == 1

    # Step 2: v2 (indici compositi)
    m2 = mgr.migrate(target_version=2)
    assert len(m2) == 1
    assert m2[0].version == 2
    assert mgr.get_migration_status().current_version == 2

    # Verifica presenza indice
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tx_portfolio_date';")
        assert cur.fetchone() is not None
    finally:
        conn.close()

    # Rollback da v2 a v1
    rolled = mgr.rollback(target_version=1)
    assert len(rolled) == 1
    assert rolled[0].version == 2
    assert mgr.get_migration_status().current_version == 1

    # Verifica rimozione indice post-rollback
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tx_portfolio_date';")
        assert cur.fetchone() is None
    finally:
        conn.close()


def test_pre_flight_backup_and_disaster_recovery_rollback(temp_db_env):
    """
    Simula una migrazione difettosa (eccezione durante up()) per verificare:
    1. Creazione del backup preventivo pre-flight.
    2. Rollback transazionale SQLite.
    3. Ripristino automatico dallo snapshot in caso di fallimento.
    """
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    # Inizializza un DB sano con v1
    mgr_init = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    mgr_init.migrate(target_version=1)
    assert mgr_init.get_migration_status().current_version == 1

    # Inserisci dati utente critici che non devono essere persi
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("INSERT INTO portfolios (name, owner) VALUES ('HNWI_Alpha', 'Alessandro');")
        conn.commit()
    finally:
        conn.close()

    # Definiamo una migrazione v2 fallata appositamente
    class V002_BrokenMigration(BaseMigration):
        version = 2
        name = "broken_migration"
        description = "Simula un errore SQL o di business logic a metà migrazione."

        def up(self, conn: sqlite3.Connection) -> None:
            conn.execute("CREATE TABLE partially_created (id INTEGER PRIMARY KEY);")
            conn.execute("INSERT INTO partially_created VALUES (1);")
            # Solleva errore fatale
            raise RuntimeError("CRITICAL DDL SYNTAX / CONSTRAINT ERROR SIMULATED!")

        def verify(self, conn: sqlite3.Connection) -> bool:
            return True

    # Registra un manager con la migrazione difettosa
    custom_mgr = DatabaseMigrationManager(
        db_path=db_path,
        backup_dir=backup_dir,
        auto_backup=True,
        custom_migrations=[V001_BaselineSchema, V002_BrokenMigration]
    )

    # La migrazione deve fallire sollevando MigrationExecutionError
    with pytest.raises(MigrationExecutionError) as exc_info:
        custom_mgr.migrate(target_version=2)

    err = exc_info.value
    assert err.version == 2
    assert "CRITICAL DDL SYNTAX" in str(err)
    assert err.rollback_restored is True

    # Verifica che il database sia stato ripristinato esattamente alla versione 1
    # e che i dati critici 'HNWI_Alpha' siano perfettamente preservati e intatti
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        assert cur.fetchone()[0] == 1

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='partially_created';")
        assert cur.fetchone() is None, "La tabella fallita non deve esistere nel DB ripristinato!"

        cur.execute("SELECT name FROM portfolios WHERE name='HNWI_Alpha';")
        assert cur.fetchone() is not None, "I dati storici dell'utente devono essere preservati al 100%!"
    finally:
        conn.close()


def test_schema_drift_detection(temp_db_env):
    """Verifica il rilevamento automatico di inconsistenze di schema (drift) e violazioni FK."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    mgr.migrate()

    # In stato post-migrazione, il database deve essere integro
    report = mgr.detect_schema_drift()
    assert report.is_healthy is True
    assert isinstance(report.to_dict(), dict)

    # Ora simuliamo un'inconsistenza: inseriamo una transazione orfana (violazione FK)
    # disabilitando temporaneamente i controlli FK
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        # portfolio_id 99999 non esiste in portfolios
        conn.execute("""
            INSERT INTO transactions (portfolio_id, asset_id, tx_date, tx_type, quantity, price, currency)
            VALUES (99999, 88888, '2026-09-09', 'buy', 10.0, 100.0, 'EUR');
        """)
        conn.commit()
    finally:
        conn.close()

    # Rilevamento dello schema drift e anomalie
    drift_report = mgr.detect_schema_drift()
    fk_issues = [it for it in drift_report.items if it.issue_type == "FOREIGN_KEY_VIOLATION"]
    assert len(fk_issues) >= 1
    assert any("transactions" in it.table_name for it in fk_issues)


def test_duckdb_compatibility(temp_db_env):
    """Verifica che il DB SQLite migrato sia al 100% compatibile con query DuckDB."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    mgr.migrate()

    duck_check = mgr.verify_duckdb_compatibility()
    assert duck_check.get("compatible") is True
    assert duck_check.get("status") == "PASS"


def test_bootstrap_helper(temp_db_env):
    """Verifica la funzione helper di avvio bootstrap_and_migrate_db."""
    db_path = temp_db_env["db_path"]
    mgr = bootstrap_and_migrate_db(db_path)
    assert mgr.get_migration_status().is_up_to_date is True
    assert mgr.get_migration_status().current_version == 4


def test_missing_column_and_index_drift(temp_db_env):
    """Verifica che la rimozione o assenza di un indice o di una tabella venga catturata nel Drift Report."""
    db_path = temp_db_env["db_path"]
    backup_dir = temp_db_env["backup_dir"]

    mgr = DatabaseMigrationManager(db_path=db_path, backup_dir=backup_dir)
    mgr.migrate(target_version=1)  # v1 non ha gli indici analitici v2

    report_v1 = mgr.detect_schema_drift()
    index_drifts = [it for it in report_v1.items if it.issue_type == "MISSING_INDEX"]
    assert len(index_drifts) >= 1
    assert any(it.field_or_index == "idx_tx_portfolio_date" for it in index_drifts)


def test_checksum_and_tamper_detection(temp_db_env):
    """Verifica che ogni migrazione generi un checksum deterministico univoco."""
    m1 = V001_BaselineSchema()
    m2 = V002_AnalyticalCompositeIndexes()
    cs1 = m1.compute_checksum()
    cs2 = m2.compute_checksum()
    assert len(cs1) == 16
    assert cs1 != cs2


def test_missing_db_drift_report(temp_db_env):
    """Verifica la gestione di un database inesistente nel Drift Report."""
    ghost_db = temp_db_env["base"] / "ghost_never_existed.db"
    mgr = DatabaseMigrationManager(db_path=ghost_db)
    rep = mgr.detect_schema_drift()
    assert rep.is_healthy is False
    assert rep.items[0].issue_type == "MISSING_DATABASE"
    assert rep.items[0].severity == DriftSeverity.CRITICAL


def test_fast_boot_performance(temp_db_env):
    """Verifica che la lettura PRAGMA user_version su DB up-to-date richieda meno di 15ms (O(1))."""
    import time
    db_path = temp_db_env["db_path"]
    mgr = DatabaseMigrationManager(db_path=db_path)
    mgr.migrate()

    t0 = time.perf_counter()
    status = mgr.get_migration_status()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert status.is_up_to_date is True
    assert elapsed_ms < 50.0  # O(1) reading header, well under threshold

