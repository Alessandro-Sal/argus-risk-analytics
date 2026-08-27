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
    assert "HEALTH" in res_health.output_text


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

    # Watchlist ADD and DEL
    res_add = engine.execute_command("WL ADD TSLA", mock_session_context)
    assert res_add.status == "SUCCESS"
    assert "TSLA" in engine.custom_watchlist

    res_del = engine.execute_command("WL DEL TSLA", mock_session_context)
    assert res_del.status == "SUCCESS"
    assert "TSLA" not in engine.custom_watchlist

    # Terminal command PORT LIVE
    res_port = engine.execute_command("PORT LIVE", mock_session_context)
    assert res_port.status == "SUCCESS"
    assert "PORT LIVE" in res_port.output_text or "REAL-TIME" in res_port.output_text
    assert "AAPL" in res_port.output_text

    # Batch parallel quote fetching
    from core.terminal_engine import fetch_multiple_live_quotes, convert_to_eur, detect_currency, get_fx_rate_to_eur
    batch_res = fetch_multiple_live_quotes(["AAPL", "MSFT", "NVDA"], max_workers=3)
    assert len(batch_res) == 3
    assert "AAPL" in batch_res and batch_res["AAPL"]["last_price"] > 0
    assert "MSFT" in batch_res and batch_res["MSFT"]["last_price"] > 0
    assert "NVDA" in batch_res and batch_res["NVDA"]["last_price"] > 0


def test_terminal_engine_multi_currency_conversion():
    from core.terminal_engine import convert_to_eur, detect_currency, get_fx_rate_to_eur

    # 1. DKK (Danish Krone, es. NOVO-B.CO)
    assert detect_currency("NOVO-B.CO", "DKK") == "DKK"
    assert detect_currency("NOVO-B.CO") == "DKK"
    fx_dkk = get_fx_rate_to_eur("DKK")
    assert 0.12 < fx_dkk < 0.15  # ~0.134
    eur_p, orig_s, curr_sym = convert_to_eur(300.25, "DKK", "NOVO-B.CO")
    assert 38.0 < eur_p < 43.0  # 300.25 DKK ~ 40.24 EUR
    assert "DKK" in orig_s
    assert "DKK" in curr_sym

    # 2. USD (es. AAPL)
    assert detect_currency("AAPL", "USD") == "USD"
    fx_usd = get_fx_rate_to_eur("USD")
    assert 0.85 < fx_usd < 0.98
    eur_usd, orig_usd, sym_usd = convert_to_eur(100.0, "USD", "AAPL")
    assert 85.0 < eur_usd < 98.0
    assert sym_usd == "$"

    # 3. EUR (es. ISP.MI)
    assert detect_currency("ISP.MI", "EUR") == "EUR"
    eur_eur, orig_eur, sym_eur = convert_to_eur(3.85, "EUR", "ISP.MI")
    assert eur_eur == 3.85
    assert sym_eur == "€"

    # 4. GBP (es. AZN.L)
    assert detect_currency("AZN.L", "GBP") == "GBP"
    fx_gbp = get_fx_rate_to_eur("GBP")
    assert 1.10 < fx_gbp < 1.25
    eur_gbp, _, sym_gbp = convert_to_eur(100.0, "GBP", "AZN.L")
    assert 110.0 < eur_gbp < 125.0
    assert sym_gbp == "£"

    # 5. SEK & CHF
    assert detect_currency("VOLV-B.ST") == "SEK"
    assert detect_currency("NESN.SW") == "CHF"
    eur_sek, _, _ = convert_to_eur(1000.0, "SEK", "VOLV-B.ST")
    assert 80.0 < eur_sek < 100.0
    eur_chf, _, _ = convert_to_eur(100.0, "CHF", "NESN.SW")
    assert 100.0 < eur_chf < 115.0


def test_terminal_engine_advanced_features(mock_session_context):
    from core.terminal_engine import get_terminal_engine
    engine = get_terminal_engine()

    # 1. NEWS command
    res_news = engine.execute_command("NEWS AAPL", mock_session_context)
    assert res_news.status in ("SUCCESS", "INFO")
    assert "NEWS" in res_news.output_text or "FINANCIAL NEWS" in res_news.output_text

    # 2. SHOCK command
    res_shock = engine.execute_command("SHOCK -5%", mock_session_context)
    assert res_shock.status == "SUCCESS"
    assert "STRESS TEST" in res_shock.output_text
    assert "-5.0%" in res_shock.output_text

    # 3. SNAP command
    res_snap = engine.execute_command("SNAP", mock_session_context)
    assert res_snap.status == "SUCCESS"
    assert "ARGUS LIVE MARKET PRICING SNAPSHOT" in res_snap.output_text
    assert "AAPL" in res_snap.output_text

    # 4. CORR MATRIX command
    res_cmat = engine.execute_command("CORR MATRIX", mock_session_context)
    assert res_cmat.status == "SUCCESS"
    assert "CORRELATION MATRIX" in res_cmat.output_text


def test_pre_trade_risk_evaluation():
    from core.terminal_engine import evaluate_pre_trade_risk, DeskRiskLimits

    limits = DeskRiskLimits(
        max_daily_loss_eur=5000.0,
        max_single_asset_weight=0.25,
        max_order_notional_eur=50000.0
    )

    # 1. Normal order passes
    res_ok = evaluate_pre_trade_risk(
        ticker="AAPL", side="BUY", qty=50, price_eur=200.0,
        current_portfolio_notional=100000.0, current_asset_notional=5000.0,
        current_day_pnl_eur=500.0, limits=limits
    )
    assert res_ok.passed is True
    assert res_ok.status == "APPROVED"

    # 2. Circuit Breaker triggered on BUY
    res_cb = evaluate_pre_trade_risk(
        ticker="AAPL", side="BUY", qty=50, price_eur=200.0,
        current_portfolio_notional=100000.0, current_asset_notional=5000.0,
        current_day_pnl_eur=-5500.0, limits=limits
    )
    assert res_cb.passed is False
    assert res_cb.status == "BLOCKED"
    assert "CIRCUIT BREAKER" in res_cb.reasons[0]

    # Circuit breaker does not block SELL
    res_sell = evaluate_pre_trade_risk(
        ticker="AAPL", side="SELL", qty=50, price_eur=200.0,
        current_portfolio_notional=100000.0, current_asset_notional=10000.0,
        current_day_pnl_eur=-5500.0, limits=limits
    )
    assert res_sell.passed is True

    # 3. Max single order notional exceeded
    res_huge = evaluate_pre_trade_risk(
        ticker="MSFT", side="BUY", qty=500, price_eur=400.0,
        current_portfolio_notional=1000000.0, current_asset_notional=10000.0,
        current_day_pnl_eur=0.0, limits=limits
    )
    assert res_huge.passed is False
    assert res_huge.status == "BLOCKED"
    assert "NOZIONALE" in res_huge.reasons[0]

    # 4. Concentration limit warning
    res_conc = evaluate_pre_trade_risk(
        ticker="NVDA", side="BUY", qty=100, price_eur=300.0,
        current_portfolio_notional=100000.0, current_asset_notional=10000.0,
        current_day_pnl_eur=0.0, limits=limits
    )
    assert res_conc.status == "WARNING"
    assert res_conc.post_trade_weight_pct > 25.0


def test_pnl_attribution_computation():
    from core.terminal_engine import compute_pnl_attribution

    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 100, "asset_currency": "USD", "current_price": 200.0},
        {"ticker": "ENI.MI", "qty_net": 500, "asset_currency": "EUR", "current_price": 14.50}
    ])
    all_quotes = {
        "AAPL": {"last_price": 210.0, "prev_close": 200.0, "currency": "USD"},
        "ENI.MI": {"last_price": 15.00, "prev_close": 14.50, "currency": "EUR"},
        "EURUSD=X": {"last_price": 1.10, "prev_close": 1.08}
    }

    attrib = compute_pnl_attribution(df_pos, all_quotes)
    assert "price_effect_eur" in attrib
    assert "fx_effect_eur" in attrib
    assert "total_day_pnl" in attrib
    assert len(attrib["by_asset"]) == 2
    # Check that EUR asset has 0 fx effect
    eni_row = next(r for r in attrib["by_asset"] if r["ticker"] == "ENI.MI")
    assert eni_row["fx_effect_eur"] == 0.0
    assert eni_row["price_effect_eur"] > 0


def test_market_catalysts_and_place_order():
    from core.terminal_engine import fetch_market_catalysts, get_terminal_engine

    # 1. Fetch catalysts
    cats = fetch_market_catalysts(["AAPL", "NVDA"])
    assert len(cats) >= 2
    assert any(c["category"] in ("MACRO", "CENTRAL BANK") for c in cats)
    assert any(c["ticker"] in ("AAPL", "NVDA") for c in cats)

    # 2. Place order through terminal engine
    engine = get_terminal_engine()
    ok, msg, order = engine.place_order("AAPL", "BUY", 20, "MKT")
    assert ok is True
    assert order is not None
    assert order.ticker == "AAPL"
    assert order.side == "BUY"
    assert order.status == "FILLED"
    assert order in engine.oms_blotter

    # Sliced TWAP order
    ok_twap, msg_twap, order_twap = engine.place_order("MSFT", "BUY", 100, "TWAP", duration_min=30)
    assert ok_twap is True
    assert order_twap.status == "SLICING"
    assert order_twap.slices_count > 1


def test_terminal_engine_portfolio_linkage(mock_session_context):
    engine = ArgusTerminalEngine()
    ctx = dict(mock_session_context)
    ctx["portfolio_name"] = "Wealth Institutional Alpha"

    # 1. HELP displays connected portfolio header
    res_help = engine.execute_command("HELP", ctx)
    assert res_help.status == "INFO"
    assert "CONNESSO AL PORTAFOGLIO" in res_help.output_text
    assert "Wealth Institutional Alpha" in res_help.output_text

    # 2. PORT LIVE displays connected portfolio name
    res_port = engine.execute_command("PORT LIVE", ctx)
    assert res_port.status == "SUCCESS"
    assert "PORTFOLIO LIVE PRICING" in res_port.output_text
    assert "Wealth Institutional Alpha" in res_port.output_text

    # 3. PORT RISK displays connected portfolio metrics
    res_risk = engine.execute_command("PORT RISK", ctx)
    assert res_risk.status == "SUCCESS"
    assert "Wealth Institutional Alpha" in res_risk.output_text
    assert "CAGR" in res_risk.output_text

    # 4. REBAL displays drift analysis and rebalancing action
    res_rebal = engine.execute_command("REBAL", ctx)
    assert res_rebal.status == "SUCCESS"
    assert "REBALANCING DESK" in res_rebal.output_text
    assert "DRIFT %" in res_rebal.output_text

    # 5. DIVIDENDS displays cash flow projection
    res_div = engine.execute_command("DIVIDENDS", ctx)
    assert res_div.status == "SUCCESS"
    assert "DIVIDEND & CASH FLOW" in res_div.output_text

    # 6. QUOTE on a portfolio holding displays the PORTFOLIO HOLDING box
    res_q_aapl = engine.execute_command("QUOTE AAPL", ctx)
    assert res_q_aapl.status == "SUCCESS"
    assert "PORTFOLIO HOLDING" in res_q_aapl.output_text
    assert "shares" in res_q_aapl.output_text

    # 7. DES, FA, VOLS without args default to top holding
    res_des_top = engine.execute_command("DES", ctx)
    assert res_des_top.status == "SUCCESS"
    # Top asset by value is SPY (52,000 EUR)
    assert "SPY" in res_des_top.output_text or "AAPL" in res_des_top.output_text

    # 8. CLOSE command executes a SELL market order on OMS
    res_close = engine.execute_command("CLOSE AAPL", ctx)
    assert res_close.status == "SUCCESS"
    assert "PORTFOLIO POSITION CLOSE" in res_close.output_text
    assert "AAPL" in res_close.output_text
    assert any(o.ticker == "AAPL" and o.side == "SELL" for o in engine.oms_blotter)





