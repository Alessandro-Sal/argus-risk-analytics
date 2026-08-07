import pytest
import numpy as np
import pandas as pd

# Nota: per testare in modo completo risk_engine.py sarebbe necessario 
# fare mocking del database (SQLAlchemy) e dei DataFrame storici.
# Qui aggiungiamo un test matematico di base per verificare che l'ambiente pytest funzioni.

def test_dummy_math():
    """Un test segnaposto per assicurarsi che pytest sia configurato correttamente."""
    returns = pd.Series([0.01, -0.02, 0.03, -0.01])
    assert returns.mean() == pytest.approx(0.0025)
    assert len(returns) == 4

from core.risk_engine import _fifo_engine

def test_fifo_engine_basic_buy():
    # Arrange
    data = {
        "tx_date": ["2023-01-01"],
        "tx_type": ["buy"],
        "quantity": [10.0],
        "price": [100.0],
        "tx_id": [1]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 10.0
    assert res["avg_cost"] == 100.0
    assert res["realized_pnl"] == 0.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_partial_sell():
    # Arrange
    data = {
        "tx_date": ["2023-01-01", "2023-01-02"],
        "tx_type": ["buy", "sell"],
        "quantity": [10.0, 4.0],
        "price": [100.0, 150.0],
        "tx_id": [1, 2]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 6.0
    assert res["avg_cost"] == 100.0
    # 4 * (150 - 100) = 200
    assert res["realized_pnl"] == 200.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_multiple_lots():
    # Arrange
    # Buy 5 @ 100 (cost 500)
    # Buy 5 @ 120 (cost 600)
    # Sell 7 @ 150 -> consumes 5 @ 100 and 2 @ 120
    # Realized: 5 * (150 - 100) + 2 * (150 - 120) = 250 + 60 = 310
    # Remaining: 3 @ 120, avg cost should be 120.0
    data = {
        "tx_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "tx_type": ["buy", "buy", "sell"],
        "quantity": [5.0, 5.0, 7.0],
        "price": [100.0, 120.0, 150.0],
        "tx_id": [1, 2, 3]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 3.0
    assert res["avg_cost"] == 120.0
    assert res["realized_pnl"] == 310.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_with_dividends():
    # Arrange
    data = {
        "tx_date": ["2023-01-01", "2023-02-01"],
        "tx_type": ["buy", "dividend"],
        "quantity": [10.0, 1.0],
        "price": [100.0, 25.0],
        "tx_id": [1, 2]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 10.0
    assert res["avg_cost"] == 100.0
    assert res["realized_pnl"] == 0.0
    assert res["dividends_total"] == 25.0

