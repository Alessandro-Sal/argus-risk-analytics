"""
Unit and integration tests for Multi-Broker Ingestion Hub and broker adapters.
"""

import pandas as pd
import pytest

from core.adapters.broker_hub import (
    SUPPORTED_BROKERS,
    detect_broker_format,
    parse_broker_csv,
)
from core.adapters.degiro import parse_degiro_transactions
from core.adapters.directa import parse_directa_transactions
from core.adapters.fineco import parse_fineco_transactions
from core.adapters.ibkr import parse_ibkr_transactions
from core.adapters.isin_resolver import (
    BASE_ISIN_TO_TICKER,
    clean_date_value,
    clean_numeric_value,
    resolve_isin_to_ticker,
)
from core.adapters.scalable import parse_scalable_transactions
from core.adapters.traderepublic import parse_traderepublic_transactions
from core.validator import validate_csv

# ── 1. TEST ISIN RESOLVER & CLEANING UTILITIES ────────────────────────────────

def test_isin_resolver_dictionary():
    """Verifica che i codici ISIN più diffusi siano risolti correttamente."""
    assert resolve_isin_to_ticker("IE00B4L5Y983") == "SWDA.MI"
    assert resolve_isin_to_ticker("IE00B3RBWM25") == "VWCE.MI"
    assert resolve_isin_to_ticker("US0378331005") == "AAPL"
    assert resolve_isin_to_ticker("US67066G1040") == "NVDA"
    assert resolve_isin_to_ticker("IT0000072618") == "ISP.MI"
    assert resolve_isin_to_ticker("MSFT") == "MSFT"


def test_clean_numeric_value():
    """Verifica la normalizzazione dei numeri in formato EU, US e negativi."""
    assert clean_numeric_value("1.234,56") == 1234.56
    assert clean_numeric_value("1,234.56") == 1234.56
    assert clean_numeric_value("150,25") == 150.25
    assert clean_numeric_value("(50.00)") == -50.0
    assert clean_numeric_value("-100,50") == -100.50
    assert clean_numeric_value("€ 2.500,00") == 2500.0
    assert clean_numeric_value(None, default=0.0) == 0.0


def test_clean_date_value():
    """Verifica la normalizzazione delle date in ISO YYYY-MM-DD."""
    assert clean_date_value("15/01/2024") == "2024-01-15"
    assert clean_date_value("2024-01-15") == "2024-01-15"
    assert clean_date_value("15.01.2024") == "2024-01-15"
    assert clean_date_value("2024-01-15 14:30:00") == "2024-01-15"


# ── 2. TEST DIRECTA SIM ADAPTER ───────────────────────────────────────────────

def test_directa_adapter_parsing():
    """Testa il parsing di un export ordini di Directa SIM."""
    raw_df = pd.DataFrame([
        {
            "Data": "15/03/2023",
            "Ora": "10:15:00",
            "Operazione": "COMPRA",
            "Titolo": "ISHARES CORE MSCI WORLD",
            "Simbolo": "IE00B4L5Y983",
            "Quantità": "10",
            "Prezzo": "75,50",
            "Controvalore": "755,00",
            "Commissioni": "5,00",
            "Divisa": "EUR"
        },
        {
            "Data": "20/06/2023",
            "Ora": "15:30:00",
            "Operazione": "VENDE",
            "Titolo": "ISHARES CORE MSCI WORLD",
            "Simbolo": "IE00B4L5Y983",
            "Quantità": "5",
            "Prezzo": "80,00",
            "Controvalore": "400,00",
            "Commissioni": "5,00",
            "Divisa": "EUR"
        },
        {
            "Data": "10/09/2023",
            "Ora": "09:00:00",
            "Operazione": "DIVIDENDO",
            "Titolo": "INTESA SANPAOLO",
            "Simbolo": "IT0000072618",
            "Quantità": "1",
            "Prezzo": "150,00",
            "Controvalore": "150,00",
            "Commissioni": "0,00",
            "Divisa": "EUR"
        }
    ])

    df_clean = parse_directa_transactions(raw_df)
    assert len(df_clean) == 3
    assert df_clean.iloc[0]["ticker"] == "SWDA.MI"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[0]["quantity"] == 10.0
    assert df_clean.iloc[0]["price"] == 75.50
    assert df_clean.iloc[0]["fees"] == 5.0

    assert df_clean.iloc[1]["tx_type"] == "sell"
    assert df_clean.iloc[1]["quantity"] == 5.0

    assert df_clean.iloc[2]["ticker"] == "ISP.MI"
    assert df_clean.iloc[2]["tx_type"] == "dividend"
    assert df_clean.iloc[2]["price"] == 150.0

    # Validazione tramite core.validator
    df_val, rep = validate_csv(df_clean)
    assert df_val is not None
    assert len(rep["errors"]) == 0


# ── 3. TEST FINECO BANK ADAPTER ───────────────────────────────────────────────

def test_fineco_adapter_parsing():
    """Testa il parsing di un export movimenti Fineco Bank."""
    raw_df = pd.DataFrame([
        {
            "Data Operazione": "10/01/2024",
            "Data Valuta": "12/01/2024",
            "Tipo Operazione": "Acquisto",
            "Descrizione": "APPLE INC",
            "Codice ISIN": "US0378331005",
            "Quantità": "15",
            "Prezzo": "180,50",
            "Importo in Euro": "2.707,50",
            "Divisa": "USD",
            "Commissioni": "2,95"
        },
        {
            "Data Operazione": "15/04/2024",
            "Data Valuta": "17/04/2024",
            "Tipo Operazione": "Accredito Dividendo",
            "Descrizione": "APPLE INC",
            "Codice ISIN": "US0378331005",
            "Quantità": "1",
            "Prezzo": "0,00",
            "Importo in Euro": "25,50",
            "Divisa": "USD",
            "Commissioni": "0,00"
        }
    ])

    df_clean = parse_fineco_transactions(raw_df)
    assert len(df_clean) == 2
    assert df_clean.iloc[0]["ticker"] == "AAPL"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[0]["quantity"] == 15.0
    assert df_clean.iloc[0]["price"] == 180.50

    assert df_clean.iloc[1]["tx_type"] == "dividend"
    assert df_clean.iloc[1]["price"] == 25.50

    df_val, rep = validate_csv(df_clean)
    assert df_val is not None
    assert len(rep["errors"]) == 0


# ── 4. TEST INTERACTIVE BROKERS (IBKR) ADAPTER ───────────────────────────────

def test_ibkr_adapter_parsing_flat():
    """Testa il parsing di un export piatto IBKR."""
    raw_df = pd.DataFrame([
        {
            "Date/Time": "2024-02-01, 15:30:00",
            "Symbol": "NVDA",
            "Quantity": "20",
            "T. Price": "600.00",
            "Comm/Fee": "-1.00",
            "CurrencyPrimary": "USD",
            "Asset Category": "Stocks"
        },
        {
            "Date/Time": "2024-03-01, 16:00:00",
            "Symbol": "NVDA",
            "Quantity": "-10",
            "T. Price": "800.00",
            "Comm/Fee": "-1.00",
            "CurrencyPrimary": "USD",
            "Asset Category": "Stocks"
        }
    ])

    df_clean = parse_ibkr_transactions(raw_df)
    assert len(df_clean) == 2
    assert df_clean.iloc[0]["ticker"] == "NVDA"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[0]["quantity"] == 20.0

    assert df_clean.iloc[1]["tx_type"] == "sell"
    assert df_clean.iloc[1]["quantity"] == 10.0
    assert df_clean.iloc[1]["fees"] == 1.0


def test_ibkr_activity_statement_parsing():
    """Testa il parsing di un Activity Statement multi-sezione IBKR."""
    raw_df = pd.DataFrame([
        ["Trades", "Header", "DataDiscriminator", "Asset Category", "Currency", "Symbol", "Date/Time", "Quantity", "T. Price", "Comm/Fee"],
        ["Trades", "Data", "Order", "Stocks", "USD", "MSFT", "2024-01-10", "10", "380.00", "-1.50"],
        ["Trades", "Data", "Order", "Stocks", "USD", "MSFT", "2024-05-10", "-5", "420.00", "-1.50"]
    ])

    df_clean = parse_ibkr_transactions(raw_df)
    assert len(df_clean) == 2
    assert df_clean.iloc[0]["ticker"] == "MSFT"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[1]["tx_type"] == "sell"


# ── 5. TEST TRADE REPUBLIC ADAPTER ───────────────────────────────────────────

def test_traderepublic_adapter_parsing():
    """Testa il parsing di un export Trade Republic (PAC e acquisti)."""
    raw_df = pd.DataFrame([
        {
            "Timestamp": "2023-05-02T10:00:00.000Z",
            "Type": "Savings Plan",
            "ISIN": "IE00B4L5Y983",
            "Name": "iShares Core MSCI World UCITS ETF",
            "Shares": "1,5",
            "Price": "78,20",
            "Amount": "-117,30",
            "Fee": "0,00"
        },
        {
            "Timestamp": "2023-08-15T14:20:00.000Z",
            "Type": "Dividend",
            "ISIN": "US0378331005",
            "Name": "Apple Inc.",
            "Shares": "1",
            "Price": "12,50",
            "Amount": "12,50",
            "Fee": "0,00"
        }
    ])

    df_clean = parse_traderepublic_transactions(raw_df)
    assert len(df_clean) == 2
    assert df_clean.iloc[0]["ticker"] == "SWDA.MI"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[0]["quantity"] == 1.5
    assert df_clean.iloc[0]["price"] == 78.20

    assert df_clean.iloc[1]["ticker"] == "AAPL"
    assert df_clean.iloc[1]["tx_type"] == "dividend"
    assert df_clean.iloc[1]["price"] == 12.50


# ── 6. TEST SCALABLE CAPITAL ADAPTER ──────────────────────────────────────────

def test_scalable_adapter_parsing():
    """Testa il parsing di un export Scalable Capital."""
    raw_df = pd.DataFrame([
        {
            "Date": "2023-04-01",
            "Type": "Orderausführung Kauf",
            "Security": "Vanguard FTSE All-World",
            "ISIN": "IE00B3RBWM25",
            "Shares": "2,0",
            "Price": "100,00",
            "Amount": "200,00",
            "Fee": "0,99"
        }
    ])

    df_clean = parse_scalable_transactions(raw_df)
    assert len(df_clean) == 1
    assert df_clean.iloc[0]["ticker"] == "VWCE.MI"
    assert df_clean.iloc[0]["tx_type"] == "buy"
    assert df_clean.iloc[0]["quantity"] == 2.0
    assert df_clean.iloc[0]["price"] == 100.0
    assert df_clean.iloc[0]["fees"] == 0.99


# ── 7. TEST BROKER HUB AUTO-DETECTION & DISPATCH ──────────────────────────────

def test_broker_hub_auto_detection():
    """Verifica il corretto auto-riconoscimento dei formati per ciascun broker."""
    # Standard
    df_std = pd.DataFrame(columns=["tx_date", "ticker", "tx_type", "quantity", "price"])
    assert detect_broker_format(df_std) == "standard"

    # Directa
    df_dir = pd.DataFrame(columns=["Data", "Ora", "Operazione", "Simbolo", "Quantità", "Prezzo", "Controvalore"])
    assert detect_broker_format(df_dir) == "directa"

    # Fineco
    df_fin = pd.DataFrame(columns=["Data Operazione", "Data Valuta", "Tipo Operazione", "Codice ISIN", "Quantità", "Importo in Euro"])
    assert detect_broker_format(df_fin) == "fineco"

    # IBKR
    df_ib = pd.DataFrame(columns=["Date/Time", "Symbol", "Quantity", "T. Price", "Comm/Fee"])
    assert detect_broker_format(df_ib) == "ibkr"

    # Trade Republic
    df_tr = pd.DataFrame(columns=["Timestamp", "Type", "ISIN", "Name", "Shares", "Price", "Fee"])
    assert detect_broker_format(df_tr) == "traderepublic"

    # Scalable
    df_sc = pd.DataFrame(columns=["Date", "Type", "Security", "ISIN", "Shares", "Price", "Amount"])
    assert detect_broker_format(df_sc) == "scalable"

    # DeGiro
    df_deg = pd.DataFrame(columns=["Data", "Ora", "Prodotto", "ISIN", "Quantità", "Prezzo", "Costi di transazione"])
    assert detect_broker_format(df_deg) == "degiro"


def test_parse_broker_csv_auto_pipeline():
    """Testa l'intera pipeline di parsing con rilevamento automatico."""
    raw_df = pd.DataFrame([
        {
            "Data": "15/03/2023",
            "Ora": "10:15:00",
            "Operazione": "COMPRA",
            "Titolo": "ISHARES CORE MSCI WORLD",
            "Simbolo": "IE00B4L5Y983",
            "Quantità": "10",
            "Prezzo": "75,50",
            "Controvalore": "755,00",
            "Commissioni": "5,00",
            "Divisa": "EUR"
        }
    ])

    df_parsed, detected_key, report = parse_broker_csv(raw_df, broker_key="auto")
    assert detected_key == "directa"
    assert report["is_auto_detected"] is True
    assert report["rows_parsed"] == 1
    assert df_parsed.iloc[0]["ticker"] == "SWDA.MI"
