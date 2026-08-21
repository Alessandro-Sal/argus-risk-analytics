import pytest
import pandas as pd
from sqlalchemy import create_engine, text
from core.db_exporter import ensure_snapshot_tables, get_all_snapshots_history, get_snapshot_positions_by_id

def test_history_analytics_functions():
    # Create SQLite in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    ensure_snapshot_tables(engine)
    
    # Insert test data
    with engine.begin() as conn:
        # Insert test portfolio & snapshots
        conn.execute(text("INSERT INTO portfolios (portfolio_id, name, owner, base_currency, created_at) VALUES (1, 'Test Portfolio', 'test_owner', 'EUR', CURRENT_TIMESTAMP)"))
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


def test_save_snapshot_to_db_full_metrics():
    from core.db_exporter import save_snapshot_to_db
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE portfolios (portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, owner TEXT, base_currency TEXT, created_at TIMESTAMP)"))
        conn.execute(text("INSERT INTO portfolios (portfolio_id, name) VALUES (1, 'Main Fund')"))

    dummy_positions = pd.DataFrame([
        {
            "ticker": "AAPL",
            "asset_class": "stock",
            "sector": "Technology",
            "country": "USA",
            "currency": "USD",
            "qty_net": 150.0,
            "avg_cost": 170.0,
            "cost_basis": 25500.0,
            "last_price": 220.0,
            "current_value": 33000.0,
            "unrealized_pnl": 7500.0,
            "realized_pnl": 1200.0,
            "dividends_total": 350.0,
            "yield_on_cost_pct": 1.85,
            "weight_pct": 60.0,
            "days_to_liquidate": 1.0,
            "trailing_pe": 32.5,
            "forward_pe": 28.0,
            "price_to_book": 45.0,
            "dividend_yield": 0.55,
            "roe": 1.45,
            "target_mean_price": 240.0,
            "peg_ratio": 2.1
        },
        {
            "ticker": "MSFT",
            "asset_class": "stock",
            "sector": "Technology",
            "country": "USA",
            "currency": "USD",
            "qty_net": 50.0,
            "avg_cost": 380.0,
            "cost_basis": 19000.0,
            "last_price": 440.0,
            "current_value": 22000.0,
            "unrealized_pnl": 3000.0,
            "realized_pnl": 0.0,
            "dividends_total": 180.0,
            "yield_on_cost_pct": 1.20,
            "weight_pct": 40.0,
            "days_to_liquidate": 1.0,
            "trailing_pe": 35.0,
            "forward_pe": 30.0,
            "price_to_book": 12.0,
            "dividend_yield": 0.75,
            "roe": 0.38,
            "target_mean_price": 480.0,
            "peg_ratio": 2.4
        }
    ])

    results = {
        "portfolio_value": 55000.0,
        "benchmark": "SPY",
        "positions": dummy_positions,
        "metrics": {
            "returns": {
                "portfolio_value": 55000.0,
                "cost_basis_total": 44500.0,
                "unrealized_pnl_total": 10500.0,
                "realized_pnl_total": 1200.0,
                "total_pnl": 11700.0,
                "total_pnl_pct": 26.29,
                "cagr_pct": 18.50,
                "sharpe_ratio": 1.65,
                "sortino_ratio": 2.10,
                "calmar_ratio": 1.80,
                "alpha_pct": 4.25,
                "information_ratio": 0.85,
                "dividends_total": 530.0
            },
            "market_risk": {
                "volatility_annual_pct": 15.20,
                "volatility_daily_pct": 0.95,
                "max_drawdown_pct": -12.40,
                "var_95": -1.85,
                "cvar_95": -2.60,
                "var_cf_95": -1.95,
                "cvar_cf_95": -2.75,
                "ulcer_index": 3.45,
                "skewness": -0.35,
                "kurtosis": 3.80,
                "r_squared_pct": 82.5,
                "ff_alpha_pct": 3.15,
                "ff_beta_mkt": 0.92,
                "smb_tilt": -0.15,
                "hml_tilt": -0.30,
                "var_exceptions_count": 4,
                "benchmark_ticker": "SPY"
            },
            "concentration": {
                "hhi_index": 0.5200,
                "diversification_ratio": 1.35
            },
            "ai_insights": {
                "montecarlo": {
                    "expected_return_1y_pct": 16.50,
                    "var_95_simulated_pct": -14.20
                },
                "asset_clusters": [
                    {"ticker": "AAPL", "volatility": 0.18, "cluster": 1},
                    {"ticker": "MSFT", "volatility": 0.16, "cluster": 1}
                ]
            }
        },
        "risk_free": {"rate_pct": 3.15, "currency": "EUR"},
        "yield_curve_params": {"beta0": 3.20, "beta1": -0.50, "beta2": 1.10, "tau": 1.85},
        "options_hedging": {
            "covered_call": {
                "incasso_eseguibile_eur": 1450.0,
                "contratti_eseguibili": 1
            }
        },
        "stress_tests": {
            "COVID-19 Crash (Feb-Mar 2020)": {"portfolio_loss_eur": -8500.0, "details": {"AAPL": {"beta": 1.15}, "MSFT": {"beta": 0.95}}},
            "Lehman Brothers (Sep-Nov 2008)": {"portfolio_loss_eur": -12000.0},
            "Tech & Rate Shock (Gen-Ott 2022)": {"portfolio_loss_eur": -7500.0}
        }
    }

    # Execute save to DB
    success = save_snapshot_to_db(results, engine, portfolio_id=1, run_id="RUN-TEST-001", run_name="Quantitative Risk Audit")
    assert success is True

    # Retrieve and verify historical snapshot with all new quantitative fields
    df_history = get_all_snapshots_history(engine, portfolio_name="Main Fund")
    assert len(df_history) >= 1
    row = df_history.iloc[0]
    assert row["run_id"] == "RUN-TEST-001"
    assert row["total_value"] == 55000.0
    assert row["ff_alpha_pct"] == 3.15
    assert row["ff_beta_mkt"] == 0.92
    assert row["cvar_95_pct"] == -2.60
    assert row["var_cf_95_pct"] == -1.95
    assert row["ulcer_index"] == 3.45
    assert row["skewness"] == -0.35
    assert row["kurtosis"] == 3.80
    assert row["ns_beta0"] == 3.20
    assert row["covered_call_income_eur"] == 1450.0
    assert row["covered_call_contracts"] == 1
    assert row["cost_basis_total"] == 44500.0
    assert row["unrealized_pnl_total"] == 10500.0

    # Retrieve and verify stored positions details
    snap_id = row["snapshot_id"]
    df_positions_db = get_snapshot_positions_by_id(engine, snapshot_id=snap_id)
    assert len(df_positions_db) == 2
    aapl_row = df_positions_db[df_positions_db["ticker"] == "AAPL"].iloc[0]
    assert aapl_row["sector"] == "Technology"
    assert aapl_row["country"] == "USA"
    assert aapl_row["currency"] == "USD"
    assert aapl_row["cost_basis"] == 25500.0
    assert aapl_row["realized_pnl"] == 1200.0
    assert aapl_row["yield_on_cost_pct"] == 1.85

