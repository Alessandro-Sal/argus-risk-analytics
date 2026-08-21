# ============================================================
# tests/test_cache_shield_and_diagnostics.py
# ARGUS — Risk Analytics & BI Platform
# Unit Tests for Multi-Tier Caching, Rate-Limit Shield & Diagnostics Cockpit
# ============================================================

import os
import time
import pytest
import pandas as pd
import numpy as np
from core.cache_shield import (
    get_cached_ticker_history,
    get_cached_ticker_info,
    get_cache_stats,
    clear_cache
)
from core.diagnostics import run_system_health_check


def test_cache_shield_operations():
    """Verifica il funzionamento del tier di caching multi-livello RAM e SQLite."""
    # Svuota cache iniziale
    clear_cache()
    
    # Simula salvataggio di un dataframe fittizio
    stats_before = get_cache_stats()
    assert "l1_memory_items" in stats_before
    assert "l2_disk_entries" in stats_before
    assert stats_before["status"] == "🟢 Active & Shielded"

    # Test cache info
    info = get_cached_ticker_info("AAPL", ttl_seconds=10)
    assert isinstance(info, dict)

    # Svuotamento cache
    del_count = clear_cache()
    assert isinstance(del_count, int)


def test_system_diagnostics_health_check():
    """Verifica il benchmark di latenza e l'integrità dei motori computazionali."""
    diag = run_system_health_check()
    assert diag["overall_status"].startswith("🟢")
    assert diag["health_score"] == 100.0
    assert diag["seed_deterministic"] is True
    assert "total_diagnostic_latency_ms" in diag
    assert isinstance(diag["engine_benchmarks"], pd.DataFrame)
    assert not diag["engine_benchmarks"].empty
    assert "engine" in diag["engine_benchmarks"].columns
    assert "latency_ms" in diag["engine_benchmarks"].columns
    assert "storage_profile" in diag
    assert "process_ram_mb" in diag["storage_profile"]


def test_storage_and_memory_profiler_operations():
    """Verifica il profiler di memoria DB, vacuum, pulizia cache e reindexing."""
    from core.diagnostics import (
        get_detailed_storage_and_memory_profile,
        optimize_database_storage,
        clean_expired_cache_records,
        reindex_databases
    )
    prof = get_detailed_storage_and_memory_profile()
    assert "total_storage_mb" in prof
    assert "total_records" in prof
    assert "process_ram_mb" in prof
    assert isinstance(prof["table_breakdown"], pd.DataFrame)

    # Test vacuum optimization
    opt = optimize_database_storage()
    assert "reclaimed_kb" in opt

    # Test clean expired
    cleaned = clean_expired_cache_records()
    assert isinstance(cleaned, int)

    # Test reindex
    reidx = reindex_databases()
    assert reidx is True


def test_sqlite_wal_pragmas():
    """Verifica che le connessioni SQLite abilitino la modalità WAL e timeout anti-lock."""
    from core.cache_shield import _get_cache_connection
    from core.fetcher import get_engine
    from sqlalchemy import text

    # Verifica connessione diretta cache SQLite
    conn = _get_cache_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    jmode = cur.fetchone()[0].lower()
    assert jmode == "wal"

    cur.execute("PRAGMA busy_timeout;")
    btimeout = int(cur.fetchone()[0])
    assert btimeout >= 5000
    conn.close()

    # Verifica SQLAlchemy engine fallback locale
    engine = get_engine("user", "pass", "invalid_host_fallback_test", db="test_db")
    if engine.dialect.name == "sqlite":
        with engine.connect() as s_conn:
            res_wal = s_conn.execute(text("PRAGMA journal_mode;")).scalar()
            assert str(res_wal).lower() == "wal"

