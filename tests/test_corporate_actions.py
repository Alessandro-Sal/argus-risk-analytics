"""
Unit and integration tests for core/corporate_actions.py and stock split adjustments.
"""

import pandas as pd
import pytest

from core.closed_trades import compute_closed_trades_journal
from core.corporate_actions import (
    KNOWN_HISTORICAL_SPLITS,
    adjust_transactions_for_splits,
    fetch_stock_splits,
    verify_split_accounting_invariance,
)
from core.risk_engine import _fifo_engine
from core.validator import validate_csv


def test_known_historical_splits_structure():
    """Verifica che la tabella di split noti contenga ticker e date formattate correttamente."""
    assert "NVDA" in KNOWN_HISTORICAL_SPLITS
    assert "AAPL" in KNOWN_HISTORICAL_SPLITS
    assert "TSLA" in KNOWN_HISTORICAL_SPLITS

    nvda_splits = KNOWN_HISTORICAL_SPLITS["NVDA"]
    assert any(s["ratio"] == 10.0 and "2024" in s["date"] for s in nvda_splits)

    aapl_splits = KNOWN_HISTORICAL_SPLITS["AAPL"]
    assert any(s["ratio"] == 4.0 and "2020" in s["date"] for s in aapl_splits)


def test_fetch_stock_splits_fallback():
    """Verifica il recupero degli split per NVDA e AAPL anche in modalità offline/fallback."""
    sp_nvda = fetch_stock_splits("NVDA")
    assert not sp_nvda.empty
    assert any(pytest.approx(r, abs=1e-2) == 10.0 for r in sp_nvda.values)

    sp_aapl = fetch_stock_splits("AAPL")
    assert not sp_aapl.empty
    assert any(pytest.approx(r, abs=1e-2) == 4.0 for r in sp_aapl.values)


def test_split_accounting_invariance_math():
    """Verifica l'invarianza del Cost Basis (Q_orig * P_orig = Q_adj * P_adj)."""
    res_fwd = verify_split_accounting_invariance(qty_before=10.0, price_before=500.0, split_ratio=10.0)
    assert res_fwd["is_invariant"] is True
    assert res_fwd["qty_after"] == 100.0
    assert res_fwd["price_after"] == 50.0
    assert res_fwd["cost_before"] == res_fwd["cost_after"] == 5000.0

    res_rev = verify_split_accounting_invariance(qty_before=100.0, price_before=5.0, split_ratio=0.1)
    assert res_rev["is_invariant"] is True
    assert res_rev["qty_after"] == 10.0
    assert res_rev["price_after"] == 50.0
    assert res_rev["cost_before"] == res_rev["cost_after"] == 500.0


def test_adjust_transactions_for_splits_forward():
    """Testa la rettifica di acquisti ante-split (NVDA 10:1 split del 2024-06-10)."""
    tx_data = [
        {"tx_id": 1, "tx_date": "2024-01-15", "ticker": "NVDA", "tx_type": "buy", "quantity": 10.0, "price": 500.0, "currency": "USD"},
        {"tx_id": 2, "tx_date": "2024-07-01", "ticker": "NVDA", "tx_type": "buy", "quantity": 20.0, "price": 120.0, "currency": "USD"},
    ]
    df_tx = pd.DataFrame(tx_data)

    custom_splits = {
        "NVDA": [{"date": "2024-06-10", "ratio": 10.0, "desc": "10:1 Forward Split"}]
    }

    df_adj, audit = adjust_transactions_for_splits(df_tx, auto_fetch=False, custom_splits=custom_splits)

    assert len(audit) == 1
    assert audit[0]["ticker"] == "NVDA"
    assert audit[0]["split_ratio"] == 10.0
    assert audit[0]["shares_before"] == 10.0
    assert audit[0]["shares_after"] == 100.0

    # Lotto 1 ante-split: 10 quote @ 500$ -> 100 quote @ 50$ (costo totale = 5.000$)
    lot1 = df_adj.iloc[0]
    assert lot1["quantity"] == 100.0
    assert lot1["price"] == 50.0
    assert lot1["quantity"] * lot1["price"] == 5000.0

    # Lotto 2 post-split: invariato (20 quote @ 120$)
    lot2 = df_adj.iloc[1]
    assert lot2["quantity"] == 20.0
    assert lot2["price"] == 120.0


def test_adjust_transactions_with_explicit_split_row():
    """Testa la presenza di una riga esplicita tx_type='split' nel dataset delle transazioni."""
    tx_data = [
        {"tx_id": 1, "tx_date": "2023-01-10", "ticker": "CUSTOM", "tx_type": "buy", "quantity": 50.0, "price": 100.0, "currency": "EUR"},
        {"tx_id": 2, "tx_date": "2023-06-01", "ticker": "CUSTOM", "tx_type": "split", "quantity": 2.0, "price": 2.0, "currency": "EUR"},
        {"tx_id": 3, "tx_date": "2023-08-01", "ticker": "CUSTOM", "tx_type": "sell", "quantity": 40.0, "price": 60.0, "currency": "EUR"},
    ]
    df_tx = pd.DataFrame(tx_data)

    df_adj, audit = adjust_transactions_for_splits(df_tx, auto_fetch=False)

    assert len(audit) == 1
    assert audit[0]["split_ratio"] == 2.0
    # La riga split viene assorbita e rimossa da df_clean_fifo
    assert len(df_adj) == 2

    # Il primo lotto ora ha 100 quote @ 50€
    assert df_adj.iloc[0]["quantity"] == 100.0
    assert df_adj.iloc[0]["price"] == 50.0


def test_fifo_engine_with_post_split_sales():
    """
    Testa l'esecuzione del motore FIFO su un ciclo completo di Split e Vendita parziale post-split:
    - Compra 10 azioni @ 500$
    - Split 10:1 (diventano 100 azioni @ 50$)
    - Vende 40 azioni @ 70$
    - Saldo residuo atteso: 60 azioni @ 50$ (WACP = 50$), PnL Realizzato = 40 * (70 - 50) = 800$
    """
    tx_data = [
        {"tx_id": 1, "tx_date": "2024-01-15", "ticker": "NVDA", "tx_type": "buy", "quantity": 10.0, "price": 500.0, "currency": "EUR"},
        {"tx_id": 2, "tx_date": "2024-07-01", "ticker": "NVDA", "tx_type": "sell", "quantity": 40.0, "price": 70.0, "currency": "EUR"},
    ]
    df_tx = pd.DataFrame(tx_data)

    custom_splits = {
        "NVDA": [{"date": "2024-06-10", "ratio": 10.0, "desc": "10:1 Forward Split"}]
    }

    df_adj, _ = adjust_transactions_for_splits(df_tx, auto_fetch=False, custom_splits=custom_splits)

    fifo_res = _fifo_engine(df_adj)

    assert fifo_res["qty_net"] == 60.0
    assert pytest.approx(fifo_res["avg_cost"], abs=1e-4) == 50.0
    assert pytest.approx(fifo_res["realized_pnl"], abs=1e-2) == 800.0


def test_closed_trades_journal_with_split():
    """Verifica che il registro Graveyard calcoli correttamente i lotti chiusi post-split."""
    tx_data = [
        {"tx_id": 1, "tx_date": "2024-01-15", "ticker": "NVDA", "tx_type": "buy", "quantity": 10.0, "price": 500.0, "currency": "EUR"},
        {"tx_id": 2, "tx_date": "2024-07-01", "ticker": "NVDA", "tx_type": "sell", "quantity": 50.0, "price": 80.0, "currency": "EUR"},
    ]
    df_tx = pd.DataFrame(tx_data)
    custom_splits = {
        "NVDA": [{"date": "2024-06-10", "ratio": 10.0, "desc": "10:1 Forward Split"}]
    }
    df_adj, _ = adjust_transactions_for_splits(df_tx, auto_fetch=False, custom_splits=custom_splits)

    ct_res = compute_closed_trades_journal(df_tx=df_adj)

    assert ct_res["total_closed_trades"] == 1
    assert pytest.approx(ct_res["total_realized_pnl_eur"], abs=1e-2) == 1500.0  # 50 * (80 - 50) = 1500
    assert ct_res["win_rate_pct"] == 100.0


def test_validator_csv_with_split_type():
    """Verifica che il validator accetti file CSV con righe di tipo 'split'."""
    raw_df = pd.DataFrame([
        {"tx_date": "2024-01-01", "ticker": "AAPL", "tx_type": "buy", "quantity": 10, "price": 150.0, "currency": "USD"},
        {"tx_date": "2024-05-01", "ticker": "AAPL", "tx_type": "split", "quantity": 2, "price": 2, "currency": "USD"},
    ])
    df_clean, report = validate_csv(raw_df)
    assert df_clean is not None
    assert len(report["errors"]) == 0
    assert "split" in df_clean["tx_type"].values


def test_reverse_split_and_cost_basis_invariance():
    """Verifica la corretta gestione di un Reverse Stock Split (raggruppamento 1:8 come GE)."""
    tx_data = [
        {"tx_id": 1, "tx_date": "2021-01-15", "ticker": "GE", "tx_type": "buy", "quantity": 80.0, "price": 12.5, "currency": "EUR"},
        {"tx_id": 2, "tx_date": "2021-09-01", "ticker": "GE", "tx_type": "sell", "quantity": 5.0, "price": 110.0, "currency": "EUR"},
    ]
    df_tx = pd.DataFrame(tx_data)
    custom_splits = {
        "GE": [{"date": "2021-08-02", "ratio": 0.125, "desc": "1:8 Reverse Split"}]
    }
    df_adj, audit = adjust_transactions_for_splits(df_tx, auto_fetch=False, custom_splits=custom_splits)

    assert len(audit) == 1
    assert audit[0]["shares_before"] == 80.0
    assert audit[0]["shares_after"] == 10.0
    assert audit[0]["split_type"] == "Reverse Split / Raggruppamento"

    fifo_res = _fifo_engine(df_adj)
    # 80 quote @ 12.5€ (1000€) -> 10 quote @ 100€ (1000€)
    # Vendita 5 quote @ 110€ -> PnL realizzato = 5 * (110 - 100) = 50€
    assert fifo_res["qty_net"] == 5.0
    assert pytest.approx(fifo_res["avg_cost"], abs=1e-4) == 100.0
    assert pytest.approx(fifo_res["realized_pnl"], abs=1e-2) == 50.0


def test_explicit_corporate_actions_aliases():
    """Verifica che tutte le tipologie di corporate actions (fusione, raggruppamento, spinoff) siano accettate."""
    from core.adapters.directa import _classify_directa_tx_type
    from core.adapters.fineco import _classify_fineco_tx_type
    from core.adapters.scalable import _classify_scalable_tx_type
    from core.adapters.traderepublic import _classify_tr_tx_type
    from core.adapters.revolut import _classify_revolut_tx_type

    assert _classify_directa_tx_type("Frazionamento / Split") == "split"
    assert _classify_directa_tx_type("Raggruppamento Azionario") == "split"
    assert _classify_directa_tx_type("Fusione per Incorporazione") == "split"
    assert _classify_directa_tx_type("Scissione / Spinoff") == "split"

    assert _classify_fineco_tx_type("Raggruppamento azioni") == "split"
    assert _classify_fineco_tx_type("Scambio azioni per fusione") == "split"

    assert _classify_scalable_tx_type("Aktienteilung / Split") == "split"
    assert _classify_tr_tx_type("Aktienteilung") == "split"
    assert _classify_revolut_tx_type("Stock Split") == "split"

