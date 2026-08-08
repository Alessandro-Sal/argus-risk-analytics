import pytest
import pandas as pd
from sqlalchemy import create_engine, text
from core.db_exporter import ensure_snapshot_tables, get_all_snapshots_history, get_snapshot_positions_by_id

def test_history_analytics_functions():
    # Create SQLite in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    
    # Create tables
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                owner TEXT,
                base_currency TEXT,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE portfolio_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                calc_date TIMESTAMP,
                run_id TEXT,
                run_name TEXT,
                portfolio_id INTEGER,
                total_value REAL,
                total_pnl REAL,
                cagr_pct REAL,
                sharpe_ratio REAL,
                max_drawdown_pct REAL,
                var_95_pct REAL,
                hhi_index REAL,
                mc_expected_return_1y REAL,
                mc_var_95 REAL,
                sortino_ratio REAL,
                calmar_ratio REAL,
                alpha_pct REAL,
                information_ratio REAL,
                r_squared_pct REAL,
                opt_max_sharpe_ratio REAL,
                opt_max_sharpe_return REAL,
                opt_max_sharpe_risk REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE assets (
                asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                name TEXT,
                currency TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE snapshot_positions (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER,
                ticker TEXT,
                asset_class TEXT,
                qty_net REAL,
                avg_cost REAL,
                last_price REAL,
                current_value REAL,
                unrealized_pnl REAL,
                weight_pct REAL
            )
        """))
        
        # Insert test portfolio & snapshots
        conn.execute(text("INSERT INTO portfolios (portfolio_id, name) VALUES (1, 'Test Portfolio')"))
        conn.execute(text("""
            INSERT INTO portfolio_snapshots 
            (snapshot_id, calc_date, run_id, run_name, portfolio_id, total_value, total_pnl, cagr_pct, sharpe_ratio)
            VALUES (101, '2026-07-01 10:00:00', 'RUN-1', 'Initial Run', 1, 10000.0, 500.0, 10.5, 1.25)
        """))
        conn.execute(text("""
            INSERT INTO portfolio_snapshots 
            (snapshot_id, calc_date, run_id, run_name, portfolio_id, total_value, total_pnl, cagr_pct, sharpe_ratio)
            VALUES (102, '2026-07-24 10:00:00', 'RUN-2', 'Latest Run', 1, 12000.0, 1500.0, 12.0, 1.45)
        """))
        
        conn.execute(text("""
            INSERT INTO snapshot_positions (snapshot_id, ticker, asset_class, current_value, weight_pct)
            VALUES (101, 'AAPL', 'stock', 5000.0, 50.0)
        """))
        conn.execute(text("""
            INSERT INTO snapshot_positions (snapshot_id, ticker, asset_class, current_value, weight_pct)
            VALUES (102, 'AAPL', 'stock', 6000.0, 50.0)
        """))

    # Test get_all_snapshots_history
    df_hist = get_all_snapshots_history(engine, portfolio_name='Test Portfolio')
    assert len(df_hist) == 2
    assert df_hist.iloc[0]["run_id"] == "RUN-1"
    assert df_hist.iloc[1]["total_value"] == 12000.0
    
    # Test get_snapshot_positions_by_id
    df_pos = get_snapshot_positions_by_id(engine, snapshot_id=102)
    assert len(df_pos) == 1
    assert df_pos.iloc[0]["ticker"] == "AAPL"
    assert df_pos.iloc[0]["current_value"] == 6000.0
