import pytest
import pandas as pd
from gsheets_sync_subproject.sync_google_sheets import normalize_gsheet_columns

def test_normalize_gsheet_columns():
    raw_df = pd.DataFrame([
        {"Date": "15/01/2021", "Security": "AAPL", "Action": "Buy", "Quantity": "10", "Type": "Stock", "Total": "1805.00"},
        {"Date": "02/03/2021", "Security": "INTC", "Action": "Dividend", "Quantity": "1", "Type": "Stock", "Total": "0.81"}
    ])

    normalized = normalize_gsheet_columns(raw_df)
    
    assert "tx_date" in normalized.columns
    assert "ticker" in normalized.columns
    assert "tx_type" in normalized.columns
    assert "quantity" in normalized.columns
    assert "price" in normalized.columns
    assert "currency" in normalized.columns
    assert len(normalized) == 2
    assert normalized.iloc[1]["quantity"] == 1.0
