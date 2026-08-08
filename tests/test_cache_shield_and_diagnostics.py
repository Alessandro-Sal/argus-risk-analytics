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
