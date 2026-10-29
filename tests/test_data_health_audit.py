import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from core.database_migration_manager import DatabaseMigrationManager
from core.diagnostics import (
    reconcile_and_clean_database,
    run_deep_data_health_audit,
)


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_audit_on_non_existent_db():
    res = run_deep_data_health_audit("data/non_existent_random_db_xyz.db")
    assert res["health_score"] == 100.0
    assert res["status"] == "HEALTHY"
    assert res["orphan_records_count"] == 0
    assert res["demo_residuals_count"] == 0


def test_reconcile_on_non_existent_db():
    res = reconcile_and_clean_database("data/non_existent_random_db_xyz.db", dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["pre_health_score"] == 100.0


def test_audit_and_reconcile_workflow(temp_db_path):
    # 1. Initialize schema via DatabaseMigrationManager
    mgr = DatabaseMigrationManager(temp_db_path)
    mgr.migrate()

    # 2. Check fresh migrated DB is healthy
    fresh_audit = run_deep_data_health_audit(temp_db_path)
    assert fresh_audit["health_score"] == 100.0
    assert fresh_audit["status"] == "HEALTHY"

    # 3. Inject dirty data: demo profiles, orphan cashflow, inconsistent cashflow, tombstones
    conn = sqlite3.connect(temp_db_path)
    cur = conn.cursor()

    # Inject demo profile
    cur.execute("""
        INSERT INTO wealth_profiles (profile_id, name, owner)
        VALUES (999001, 'DEMO_FAMILY_OFFICE', 'Demo User');
    """)
    cur.execute("""
        INSERT INTO portfolios (portfolio_id, name, owner)
        VALUES (999001, 'DEMO_PORTFOLIO', 'Demo User');
    """)

    # Inject valid account
    cur.execute("""
        INSERT INTO wealth_accounts (account_id, name, balance)
        VALUES (101, 'Conto Reale', 50000.0);
    """)

    # Inject orphan cashflow (referencing non-existent account 9999)
    cur.execute("""
        INSERT INTO wealth_cashflow (account_id, category_id, amount, direction, tx_date)
        VALUES (9999, 1, 1500.0, 'inflow', '2026-05-10');
    """)

    # Inject inconsistent cashflow (invalid direction)
    cur.execute("""
        INSERT INTO wealth_cashflow (account_id, category_id, amount, direction, tx_date)
        VALUES (101, 1, -250.0, 'UNKNOWN_DIR', '2026-05-12');
    """)

    # Inject old tombstone
    old_time = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO tombstone_deletions (entity_type, entity_id, user_id, workspace_id, deleted_at)
        VALUES ('wealth_accounts', '888', 'user', 'default', ?);
    """, (old_time,))

    conn.commit()
    conn.close()

    # 4. Run audit and assert anomalies detected
    dirty_audit = run_deep_data_health_audit(temp_db_path)
    assert dirty_audit["health_score"] < 100.0
    assert dirty_audit["demo_residuals_count"] > 0
    assert dirty_audit["orphan_records_count"] > 0
    assert dirty_audit["inconsistencies_count"] > 0
    assert len(dirty_audit["anomalies"]) >= 3

    # 5. Run dry-run reconcile: nothing modified
    dry_run_res = reconcile_and_clean_database(temp_db_path, dry_run=True)
    assert dry_run_res["success"] is True
    assert dry_run_res["dry_run"] is True
    assert dry_run_res["cleaned_demo_records"] > 0
    assert dry_run_res["vacuum_executed"] is False

    # Verify data wasn't changed by dry run
    post_dry_audit = run_deep_data_health_audit(temp_db_path)
    assert post_dry_audit["health_score"] == dirty_audit["health_score"]

    # 6. Run actual reconcile
    clean_res = reconcile_and_clean_database(temp_db_path, dry_run=False, purge_tombstones_older_than_days=90)
    assert clean_res["success"] is True
    assert clean_res["dry_run"] is False
    assert clean_res["cleaned_demo_records"] > 0
    assert clean_res["cleaned_orphan_records"] > 0
    assert clean_res["reconciled_inconsistencies"] > 0
    assert clean_res["purged_tombstones"] == 1
    assert clean_res["vacuum_executed"] is True
    assert clean_res["post_health_score"] == 100.0

    # 7. Verify post-clean state
    final_audit = run_deep_data_health_audit(temp_db_path)
    assert final_audit["health_score"] == 100.0
    assert final_audit["status"] == "HEALTHY"
    assert final_audit["demo_residuals_count"] == 0
    assert final_audit["orphan_records_count"] == 0
    assert final_audit["inconsistencies_count"] == 0
