import pytest
import pandas as pd
from core.closed_trades import compute_closed_trades_journal

def test_closed_trades_empty_and_sandbox():
    res_empty = compute_closed_trades_journal(pd.DataFrame(), is_sandbox=False)
    assert res_empty["has_closed_trades"] is False
    assert res_empty["total_realized_pnl_eur"] == 0.0

    res_sandbox = compute_closed_trades_journal(pd.DataFrame(), is_sandbox=True)
    assert res_sandbox["has_closed_trades"] is True
    assert res_sandbox["total_closed_trades"] > 0
    assert not res_sandbox["df_closed_lots"].empty
    assert not res_sandbox["df_closed_assets"].empty

def test_closed_trades_fifo_matching():
    df_tx = pd.DataFrame([
        {"tx_id": 1, "ticker": "AAPL", "tx_date": "2024-01-10", "tx_type": "buy", "quantity": 10, "price": 150.0, "currency": "EUR"},
        {"tx_id": 2, "ticker": "AAPL", "tx_date": "2024-02-10", "tx_type": "buy", "quantity": 10, "price": 160.0, "currency": "EUR"},
        {"tx_id": 3, "ticker": "AAPL", "tx_date": "2024-03-10", "tx_type": "sell", "quantity": 15, "price": 180.0, "currency": "EUR"},
        {"tx_id": 4, "ticker": "MSFT", "tx_date": "2024-01-15", "tx_type": "buy", "quantity": 5, "price": 300.0, "currency": "EUR"},
        {"tx_id": 5, "ticker": "MSFT", "tx_date": "2024-04-15", "tx_type": "sell", "quantity": 5, "price": 280.0, "currency": "EUR"},
    ])

    res = compute_closed_trades_journal(df_tx=df_tx)
    assert res["has_closed_trades"] is True
    assert res["total_closed_trades"] == 3  # AAPL lot 1 (10), AAPL lot 2 (5), MSFT lot 1 (5)
    
    # AAPL lot 1: 10 * (180 - 150) = +300
    # AAPL lot 2: 5 * (180 - 160) = +100
    # MSFT lot 1: 5 * (280 - 300) = -100
    # Totale = +300 + 100 - 100 = +300
    assert res["total_realized_pnl_eur"] == 300.0
    assert res["n_winning_trades"] == 2
    assert res["n_losing_trades"] == 1
    assert res["win_rate_pct"] == pytest.approx(66.67, 0.1)
    assert res["gross_profit_eur"] == 400.0
    assert res["gross_loss_eur"] == 100.0
    assert res["profit_factor"] == 4.0

    df_lots = res["df_closed_lots"]
    assert len(df_lots) == 3
    assert set(df_lots["outcome"].unique()) == {"🟢 WIN", "🔴 LOSS"}
