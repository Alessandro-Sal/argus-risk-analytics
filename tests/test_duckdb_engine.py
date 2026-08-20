"""
Unit tests for DuckDB In-Process OLAP Query Engine & Parquet Storage (core/duckdb_engine.py).
"""

import pandas as pd
import pytest

from core.duckdb_engine import (
    export_portfolio_to_parquet,
    get_duckdb_system_info,
    get_in_memory_duckdb_connection,
    get_parquet_compression_ratio,
    get_preset_olap_queries,
    is_duckdb_available,
    run_duckdb_olap_query,
)


@pytest.fixture
def sample_portfolio_dfs():
    pos_df = pd.DataFrame([
        {
            "ticker": "AAPL",
            "asset_name": "Apple Inc.",
            "asset_class": "Stock",
            "sector": "Technology",
            "currency": "USD",
            "current_value": 2200.0,
            "weight_pct": 20.0,
            "pnl_pct": 14.5,
        },
        {
            "ticker": "MSFT",
            "asset_name": "Microsoft Corp.",
            "asset_class": "Stock",
            "sector": "Technology",
            "currency": "USD",
            "current_value": 4400.0,
            "weight_pct": 40.0,
            "pnl_pct": 22.1,
        },
        {
            "ticker": "NVDA",
            "asset_name": "NVIDIA Corp.",
            "asset_class": "Stock",
            "sector": "Technology",
            "currency": "USD",
            "current_value": 1250.0,
            "weight_pct": 11.4,
            "pnl_pct": 68.3,
        },
        {
            "ticker": "RACE.MI",
            "asset_name": "Ferrari N.V.",
            "asset_class": "Stock",
            "sector": "Consumer Cyclical",
            "currency": "EUR",
            "current_value": 2100.0,
            "weight_pct": 19.1,
            "pnl_pct": 8.4,
        },
    ])

    tx_df = pd.DataFrame([
        {"tx_date": "2023-01-15", "ticker": "AAPL", "tx_type": "BUY", "quantity": 10, "price": 135.0, "currency": "USD", "fees": 1.5},
        {"tx_date": "2023-04-20", "ticker": "MSFT", "tx_type": "BUY", "quantity": 10, "price": 280.0, "currency": "USD", "fees": 1.5},
    ])

    return {"positions": pos_df, "transactions": tx_df}


def test_duckdb_system_info():
    info = get_duckdb_system_info()
    assert "version" in info
    assert "engine_mode" in info
    assert "vectorization" in info
    assert is_duckdb_available() is True


def test_in_memory_duckdb_connection_and_table_registration(sample_portfolio_dfs):
    con = get_in_memory_duckdb_connection(sample_portfolio_dfs)
    assert con is not None
    res = con.execute("SELECT COUNT(*) AS total FROM positions").fetchone()
    assert res[0] == 4


def test_run_duckdb_olap_query_presets(sample_portfolio_dfs):
    presets = get_preset_olap_queries()
    assert "cube_exposure" in presets
    assert "sector_ranking" in presets
    assert "monthly_tx_rollup" in presets
    assert "fx_exposure_matrix" in presets

    # Esegui query aggregazione
    res_cube = run_duckdb_olap_query(presets["cube_exposure"]["sql"], context_dfs=sample_portfolio_dfs)
    assert res_cube["success"] is True
    assert res_cube["latency_ms"] >= 0.0
    assert res_cube["row_count"] > 0
    assert not res_cube["df"].empty

    # Esegui ranking con window function
    res_rank = run_duckdb_olap_query(presets["sector_ranking"]["sql"], context_dfs=sample_portfolio_dfs)
    assert res_rank["success"] is True
    assert "rank_settoriale_best" in res_rank["df"].columns


def test_export_portfolio_to_parquet_and_stats(sample_portfolio_dfs):
    pos_df = sample_portfolio_dfs["positions"]
    pq_bytes = export_portfolio_to_parquet(pos_df)
    assert len(pq_bytes) > 0
    assert pq_bytes[:4] == b"PAR1"  # Magic bytes di Apache Parquet

    stats = get_parquet_compression_ratio(pos_df)
    assert stats["csv_bytes"] > 0
    assert stats["parquet_bytes"] > 0


def test_run_duckdb_olap_query_syntax_error_handling(sample_portfolio_dfs):
    bad_res = run_duckdb_olap_query("SELECT invalid_column_xyz FROM non_existing_table", context_dfs=sample_portfolio_dfs)
    assert bad_res["success"] is False
    assert bad_res["error"] is not None
    assert bad_res["row_count"] == 0

    empty_res = run_duckdb_olap_query("")
    assert empty_res["success"] is False
