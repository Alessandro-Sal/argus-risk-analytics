# ============================================================
# tests/test_terminal_engine.py
# ARGUS — Unit Tests for Live Terminal Engine & Interactive CLI Desk
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.terminal_engine import (
    ArgusTerminalEngine,
    TerminalCommandResult,
    OMSOrder,
    get_terminal_engine
)


@pytest.fixture
def mock_session_context():
    """Genera un contesto di sessione con posizioni, rendimenti e risultati realistici."""
    df_pos = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "NVDA", "SPY"],
        "company_name": ["Apple Inc.", "Microsoft Corp.", "Nvidia Corp.", "SPDR S&P 500"],
        "sector": ["Technology", "Technology", "Technology", "Index ETF"],
        "quantity": [50.0, 30.0, 40.0, 100.0],
        "buy_price": [180.0, 350.0, 110.0, 450.0],
        "wacp": [180.0, 350.0, 110.0, 450.0],
        "current_price": [225.0, 415.0, 128.0, 520.0],
        "market_value": [11250.0, 12450.0, 5120.0, 52000.0],
        "pnl": [2250.0, 1950.0, 720.0, 7000.0],
        "pnl_pct": [25.0, 18.57, 16.36, 15.56],
        "argus_score": [88.5, 91.2, 85.0, 78.0],
        "piotroski_score": [8, 9, 7, 6],
        "altman_z_score": [4.2, 5.1, 6.3, 3.1]
    })

    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    ret_data = {
        "AAPL": np.random.normal(0.0008, 0.015, len(dates)),
        "MSFT": np.random.normal(0.0007, 0.014, len(dates)),
        "NVDA": np.random.normal(0.0015, 0.028, len(dates)),
        "SPY": np.random.normal(0.0005, 0.010, len(dates))
    }
    df_ret = pd.DataFrame(ret_data, index=dates)

    results = {
        "cagr": 16.4,
        "volatility": 14.2,
        "sharpe": 1.25,
        "sortino": 1.78,
        "beta": 1.05,
        "max_drawdown": -7.8,
        "historical_var_95": 1.85,
        "cvar_95": 2.70,
        "health_score": 88
    }

    return {
        "df_positions": df_pos,
        "df_returns": df_ret,
        "df_prices": pd.DataFrame(),
        "results": results
    }


def test_terminal_engine_help_and_system_commands(mock_session_context):
    engine = ArgusTerminalEngine()
    
    # HELP
    res_help = engine.execute_command("HELP", mock_session_context)
    assert res_help.status == "INFO"
    assert "ARGUS INSTITUTIONAL TERMINAL" in res_help.output_text

    # PING
    res_ping = engine.execute_command("PING", mock_session_context)
    assert res_ping.status == "SUCCESS"
    assert "PONG!" in res_ping.output_text

    # TOP / STATUS
    res_top = engine.execute_command("TOP", mock_session_context)
    assert res_top.status == "SUCCESS"
    assert "ARGUS SYSTEM TELEMETRY" in res_top.output_text

    # HISTORY
    res_hist = engine.execute_command("HISTORY", mock_session_context)
    assert res_hist.status == "INFO"
    assert "COMMAND HISTORY" in res_hist.output_text

    # CLEAR
    res_clear = engine.execute_command("CLEAR", mock_session_context)
    assert res_clear.status == "INFO"
    assert len(engine.output_buffer) == 0


def test_terminal_engine_quant_commands(mock_session_context):
    engine = ArgusTerminalEngine()

    # VAR 95
    res_var95 = engine.execute_command("VAR 95", mock_session_context)
    assert res_var95.status == "SUCCESS"
    assert "VALUE AT RISK" in res_var95.output_text
    assert "95%" in res_var95.output_text

    # VAR 99
    res_var99 = engine.execute_command("VAR 99", mock_session_context)
    assert res_var99.status == "SUCCESS"
    assert "99%" in res_var99.output_text

    # SHARPE & SORTINO
    res_sharpe = engine.execute_command("SHARPE", mock_session_context)
    assert res_sharpe.status == "SUCCESS"
    assert "1.25" in res_sharpe.output_text

    res_sortino = engine.execute_command("SORTINO", mock_session_context)
    assert res_sortino.status == "SUCCESS"
    assert "1.78" in res_sortino.output_text

    # KELLY
    res_kelly = engine.execute_command("KELLY", mock_session_context)
    assert res_kelly.status == "SUCCESS"
    assert "KELLY CRITERION" in res_kelly.output_text

    # HEALTH
    res_health = engine.execute_command("HEALTH", mock_session_context)
    assert res_health.status == "SUCCESS"
    assert "HEALTH & SOLVENCY" in res_health.output_text


def test_terminal_engine_correlation(mock_session_context):
    engine = ArgusTerminalEngine()
    
    res_corr = engine.execute_command("CORR AAPL MSFT", mock_session_context)
    assert res_corr.status == "SUCCESS"
    assert "CORRELATION ANALYSIS: AAPL vs MSFT" in res_corr.output_text
    assert "Pearson" in res_corr.output_text


def test_terminal_engine_bloomberg_mnemonics(mock_session_context):
    engine = ArgusTerminalEngine()

    # AAPL DES
    res_des = engine.execute_command("AAPL DES", mock_session_context)
    assert res_des.status == "SUCCESS"
    assert "AAPL" in res_des.output_text
    assert "Apple Inc." in res_des.output_text

    # AAPL FA
    res_fa = engine.execute_command("AAPL FA", mock_session_context)
    assert res_fa.status == "SUCCESS"
    assert "FUNDAMENTAL ANALYSIS: AAPL" in res_fa.output_text

    # AAPL VOLS
    res_vols = engine.execute_command("AAPL VOLS", mock_session_context)
    assert res_vols.status == "SUCCESS"
    assert "VOLATILITY SURFACE" in res_vols.output_text

    # PORT RISK
    res_port = engine.execute_command("PORT RISK", mock_session_context)
    assert res_port.status == "SUCCESS"
    assert "PORTFOLIO RISK & PERFORMANCE" in res_port.output_text

    # YAS
    res_yas = engine.execute_command("YAS", mock_session_context)
    assert res_yas.status == "SUCCESS"
    assert "FIXED INCOME & SOVEREIGN YIELD CURVE" in res_yas.output_text

    # TAX
    res_tax = engine.execute_command("TAX", mock_session_context)
    assert res_tax.status == "SUCCESS"
    assert "FISCO ITALIANO" in res_tax.output_text


def test_terminal_engine_oms_trading(mock_session_context):
    engine = ArgusTerminalEngine()

    # BUY Order
    res_buy = engine.execute_command("BUY 100 AAPL @ 220.00", mock_session_context)
    assert res_buy.status == "SUCCESS"
    assert "OMS EXECUTION CONFIRMATION" in res_buy.output_text
    assert len(engine.oms_blotter) == 1
    assert engine.oms_blotter[0].ticker == "AAPL"
    assert engine.oms_blotter[0].side == "BUY"

    # TWAP Sliced Order
    res_twap = engine.execute_command("TWAP 500 MSFT 30MIN", mock_session_context)
    assert res_twap.status == "SUCCESS"
    assert "ALGORITHMIC TWAP" in res_twap.output_text
    assert len(engine.oms_blotter) == 2
    assert engine.oms_blotter[0].order_type == "TWAP"

    # BLOTTER
    res_blotter = engine.execute_command("BLOTTER", mock_session_context)
    assert res_blotter.status == "SUCCESS"
    assert "ORDER ID" in res_blotter.output_text
    assert "AAPL" in res_blotter.output_text

    # CANCEL Order
    target_id = engine.oms_blotter[0].order_id
    res_cancel = engine.execute_command(f"CANCEL {target_id}", mock_session_context)
    assert res_cancel.status == "SUCCESS"
    assert "annullato con successo" in res_cancel.output_text
    assert engine.oms_blotter[0].status == "CANCELLED"


def test_terminal_engine_sql_and_eqs(mock_session_context):
    engine = ArgusTerminalEngine()

    # SQL
    res_sql = engine.execute_command("SQL SELECT ticker, market_value, pnl_pct FROM df_positions WHERE pnl_pct > 20", mock_session_context)
    assert res_sql.status == "SUCCESS"
    assert "DUCKDB SQL EXECUTED" in res_sql.output_text
    assert "AAPL" in res_sql.output_text

    # EQS
    res_eqs = engine.execute_command("EQS piotroski >= 7", mock_session_context)
    assert res_eqs.status == "SUCCESS"
    assert "EQS MATCHES" in res_eqs.output_text


def test_terminal_engine_ring_buffer():
    engine = ArgusTerminalEngine()
    buf = engine.get_or_create_ring_buffer("NVDA", capacity=200)
    assert buf is not None
    assert buf.ticker == "NVDA"
    stats = buf.get_summary_statistics()
    assert "last_price" in stats
    assert "vwap" in stats


def test_terminal_engine_live_quote_and_watchlist(mock_session_context):
    from core.terminal_engine import fetch_live_ticker_quote
    engine = ArgusTerminalEngine()

    # Direct fetch_live_ticker_quote
    q_aapl = fetch_live_ticker_quote("AAPL")
    assert q_aapl["ticker"] == "AAPL"
    assert q_aapl["last_price"] > 0
    assert "change_pct" in q_aapl

    # Terminal command QUOTE AAPL
    res_q = engine.execute_command("QUOTE AAPL", mock_session_context)
    assert res_q.status == "SUCCESS"
    assert "AAPL" in res_q.output_text
    assert "LAST PRICE" in res_q.output_text

    # Terminal command WATCHLIST
    res_wl = engine.execute_command("WATCHLIST", mock_session_context)
    assert res_wl.status == "SUCCESS"
    assert "WATCHLIST" in res_wl.output_text
    assert "LAST PRICE" in res_wl.output_text

