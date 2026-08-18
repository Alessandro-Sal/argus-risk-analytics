import pytest
import pandas as pd
from gsheets_sync_subproject.sync_google_sheets import (
    normalize_gsheet_columns,
    DEFAULT_STOCKS_TAB,
    DEFAULT_CRYPTO_TAB,
    DEFAULT_STOCKS_PORTFOLIO,
    DEFAULT_CRYPTO_PORTFOLIO
)


def test_normalize_gsheet_columns_stocks():
    raw_df = pd.DataFrame([
        {"Date": "15/01/2021", "Security": "AAPL", "Action": "Buy", "Quantity": "10", "Type": "Stock", "Total": "1805.00", "Currency": "EUR"},
        {"Date": "02/03/2021", "Security": "INTC", "Action": "Dividend", "Quantity": "1", "Type": "Stock", "Total": "0.81", "Currency": "EUR"},
        {"Date": "10/05/2021", "Security": "BIT:ISP", "Action": "Buy", "Quantity": "500", "Type": "Stock", "Total": "1150.00", "Currency": "EUR"}
    ])

    normalized = normalize_gsheet_columns(raw_df, is_crypto=False)
    
    assert "tx_date" in normalized.columns
    assert "ticker" in normalized.columns
    assert "tx_type" in normalized.columns
    assert "quantity" in normalized.columns
    assert "price" in normalized.columns
    assert "currency" in normalized.columns
    assert "asset_class" in normalized.columns
    assert len(normalized) == 3
    assert normalized.iloc[1]["quantity"] == 1.0
    assert normalized.iloc[2]["ticker"] == "ISP.MI"
    assert normalized.iloc[0]["asset_class"] == "stock"


def test_normalize_gsheet_columns_crypto():
    raw_crypto_df = pd.DataFrame([
        {"Date": "2022-01-10", "Security": "BTC", "Action": "Buy", "Quantity": "0.045231", "Type": "Crypto", "Total": "1850.50", "Currency": "EUR"},
        {"Date": "2022-04-15", "Security": "ETH", "Action": "Acquisto", "Quantity": "1.250000", "Type": "Crypto", "Total": "3200.00", "Currency": "EUR"},
        {"Date": "2022-08-20", "Security": "SOL-EUR", "Action": "Staking", "Quantity": "15.5", "Type": "Crypto", "Total": "0.0", "Currency": "EUR"},
        {"Date": "2023-01-05", "Security": "CASH EUR", "Action": "Deposit", "Quantity": "1", "Type": "Cash", "Total": "500.00"}
    ])

    normalized = normalize_gsheet_columns(raw_crypto_df, is_crypto=True)
    
    # CASH EUR must be filtered out
    assert len(normalized) == 3
    assert normalized.iloc[0]["ticker"] == "BTC-EUR"
    assert normalized.iloc[0]["asset_class"] == "crypto"
    assert round(normalized.iloc[0]["quantity"], 6) == 0.045231
    assert normalized.iloc[1]["ticker"] == "ETH-EUR"
    assert normalized.iloc[1]["tx_type"] == "buy"
    assert normalized.iloc[2]["ticker"] == "SOL-EUR"
    assert normalized.iloc[2]["tx_type"] == "buy"


def test_gsheets_constants():
    assert DEFAULT_STOCKS_TAB == "History B/S Stocks"
    assert DEFAULT_CRYPTO_TAB == "History B/S Crypto"
    assert DEFAULT_STOCKS_PORTFOLIO == "Wealth Stocks Portfolio"
    assert DEFAULT_CRYPTO_PORTFOLIO == "Wealth Crypto Portfolio"


def test_user_crypto_sheet_columns_a_to_h():
    """Test con la struttura esatta colonne A-H e notazione europea del foglio History B/S Crypto."""
    raw_crypto_df = pd.DataFrame([
        {"Date": "28/12/2021", "Security": "Cash", "Action": "Deposit", "Quantity": "294,6", "Price": "x", "Price£": "€1,00", "Price$/Price£ - Comm": "x", "Total": "€294,60"},
        {"Date": "28/12/2021", "Security": "BTC", "Action": "Buy", "Quantity": "0,00232238", "Price": "x", "Price£": "€43.059,27", "Price$/Price£ - Comm": "x", "Total": "€100,00"},
        {"Date": "12/08/2022", "Security": "ETH", "Action": "Withdrawal", "Quantity": "0,0001", "Price": "x", "Price£": "-", "Price$/Price£ - Comm": "x", "Total": "-"},
        {"Date": "08/12/2023", "Security": "USDT", "Action": "Buy", "Quantity": "1.074,92", "Price": "x", "Price£": "€0,93", "Price$/Price£ - Comm": "x", "Total": "€1.000,00"},
        {"Date": "23/01/2026", "Security": "ADA", "Action": "Buy", "Quantity": "6,806173", "Price": "x", "Price£": "€0,00", "Price$/Price£ - Comm": "x", "Total": "€0,00"},
        {"Date": "29/01/2026", "Security": "BTC", "Action": "Buy", "Quantity": "0,004253", "Price": "€ 300,00", "Price£": "€ 70.545,74", "Price$/Price£ - Comm": "$0,00", "Total": "€ 300,00"},
        {"Date": "04/06/2026", "Security": "SOL", "Action": "Buy", "Quantity": "3", "Price": "€ 200,00", "Price£": "€ 58,85", "Price$/Price£ - Comm": "$0,00", "Total": "€ 200,00"}
    ])

    norm = normalize_gsheet_columns(raw_crypto_df, is_crypto=True)
    
    # 2 rows (Cash Deposit and ETH Withdrawal) must be skipped -> 5 valid market trades
    assert len(norm) == 5
    
    # Row 1: BTC Buy
    btc_row = norm.iloc[0]
    assert btc_row["ticker"] == "BTC-EUR"
    assert btc_row["tx_type"] == "buy"
    assert round(btc_row["quantity"], 8) == 0.00232238
    assert round(btc_row["price"], 2) == 43059.28
    
    # Row 2: USDT Buy with thousand separator
    usdt_row = norm.iloc[1]
    assert usdt_row["ticker"] == "USDT-EUR"
    assert round(usdt_row["quantity"], 2) == 1074.92
    assert round(usdt_row["price"] * usdt_row["quantity"], 2) == 1000.00

    # Row 3: ADA Airdrop / free reward
    ada_row = norm.iloc[2]
    assert ada_row["ticker"] == "ADA-EUR"
    assert round(ada_row["quantity"], 6) == 6.806173
    assert ada_row["price"] > 0

    # Row 4: BTC 2026 with € currency symbol in numbers
    btc_2026 = norm.iloc[3]
    assert btc_2026["ticker"] == "BTC-EUR"
    assert round(btc_2026["quantity"], 6) == 0.004253
    assert round(btc_2026["price"], 2) == 70538.44


