import pandas as pd
import pytest
from core.validator import validate_csv

def test_validate_csv_success():
    # Arrange
    data = {
        "tx_date": ["2023-01-01", "2023-01-15"],
        "ticker": ["AAPL", "MSFT"],
        "tx_type": ["buy", "sell"],
        "quantity": ["10", "5"],
        "price": ["150.0", "250.0"],
        "currency": ["USD", "USD"]
    }
    df_raw = pd.DataFrame(data)

    # Act
    df_clean, report = validate_csv(df_raw)

    # Assert
    assert df_clean is not None
    assert len(report["errors"]) == 0
    assert len(df_clean) == 2
    assert df_clean.iloc[0]["tx_date"] == pd.to_datetime("2023-01-01")
    assert df_clean.iloc[0]["quantity"] == 10.0

def test_validate_csv_missing_columns():
    # Arrange
    data = {
        "tx_date": ["2023-01-01"],
        "ticker": ["AAPL"],
        # Missing tx_type, quantity, price, currency
    }
    df_raw = pd.DataFrame(data)

    # Act
    df_clean, report = validate_csv(df_raw)

    # Assert
    assert df_clean is None
    assert len(report["errors"]) > 0
    assert "Colonne obbligatorie mancanti" in report["errors"][0]

def test_validate_csv_invalid_date():
    # Arrange
    data = {
        "tx_date": ["not-a-date"],
        "ticker": ["AAPL"],
        "tx_type": ["buy"],
        "quantity": ["10"],
        "price": ["150.0"],
        "currency": ["USD"]
    }
    df_raw = pd.DataFrame(data)

    # Act
    df_clean, report = validate_csv(df_raw)

    # Assert
    assert df_clean is None
    assert len(report["errors"]) > 0
    assert "Formato data non riconoscibile" in report["errors"][0]
