# ============================================================
# tests/test_universal_broker_importer.py
# Unit tests for Universal Broker Importer & Reconciler
# ============================================================

import io
import time

import pandas as pd
import pytest

from core.fetcher import get_engine
from core.wealth.universal_broker_importer import (
    BROKER_SIGNATURES,
    detect_broker_and_format,
    ingest_broker_transactions,
    parse_universal_broker_file,
)


def test_detect_broker_signatures():
    # Directa sample
    df_dir = pd.DataFrame(columns=["Data Operazione", "Tipo Operazione", "Titolo", "ISIN", "Quantità", "Prezzo", "Controvalore"])
    assert detect_broker_and_format(df_dir, "Directa SIM nota informativa eseguiti") == "DIRECTA"

    # Fineco sample
    df_fin = pd.DataFrame(columns=["Data Operazione", "Dossier Titoli", "Titolo", "ISIN", "Eseguito", "Prezzo Eseguito", "Commissioni"])
    assert detect_broker_and_format(df_fin, "Fineco Bank movimenti titoli dossier") == "FINECO"

    # Degiro sample
    df_deg = pd.DataFrame(columns=["Data", "Ora", "Prodotto", "ISIN", "Descrizione", "Variazione", "Corso", "Valore Locale", "Costi di transazione"])
    assert detect_broker_and_format(df_deg, "Degiro flatex transactions export") == "DEGIRO"

    # Scalable sample
    df_sca = pd.DataFrame(columns=["Date", "Type", "Security Name", "ISIN", "Shares", "Execution Price", "Total Amount"])
    assert detect_broker_and_format(df_sca, "Scalable Capital order transactions") == "SCALABLE"

    # Trade Republic sample
    df_tr = pd.DataFrame(columns=["Timestamp", "Type", "Asset", "ISIN", "Units", "Price", "Amount"])
    assert detect_broker_and_format(df_tr, "Trade Republic activity statement") == "TRADE_REPUBLIC"

    # IBKR sample
    df_ib = pd.DataFrame(columns=["Symbol", "Date/Time", "Quantity", "T. Price", "C. Price", "Proceeds", "Comm/Fee"])
    assert detect_broker_and_format(df_ib, "Interactive Brokers activity statement trades") == "IBKR"


def test_parse_directa_csv():
    csv_data = """Data;Tipo Operazione;Titolo;ISIN;Quantità;Prezzo;Controvalore;Commissioni
15/01/2026;ACQUISTO;ISHARES CORE MSCI WORLD;IE00B4L5Y983;10;95,50;955,00;5,00
16/01/2026;VENDITA;APPLE INC;US0378331005;5;220,00;1.100,00;6,00
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="eseguiti_directa.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "DIRECTA"
    assert len(df) == 2
    assert df.iloc[0]["isin"] in ["IE00B4L5Y983", "US0378331005"]
    assert df["total_eur"].sum() == 2055.0


def test_parse_fineco_csv():
    csv_data = """Data Operazione;Operazione;Titolo;ISIN;Quantità;Prezzo;Controvalore Euro;Spese
20/01/2026;Acquisto;VANGUARD S&P 500;IE00B3XXRP09;15;88,20;1323,00;2,95
22/01/2026;Dividendo;VANGUARD S&P 500;IE00B3XXRP09;0;0;45,50;0,00
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="fineco_trading.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "FINECO"
    assert len(df) == 2
    assert "BUY" in df["tx_type"].values
    assert "DIVIDEND" in df["tx_type"].values


def test_parse_degiro_csv():
    csv_data = """Data,Ora,Prodotto,ISIN,Descrizione,Variazione,Corso,Valore locale,Valore,Costi di transazione
10-02-2026,14:30,MICROSOFT,US5949181045,Acquisto 2 Microsoft,2,410.50,-821.00,-821.00,1.00
11-02-2026,15:00,TESLA,US88160R1014,Vendita 1 Tesla,-1,250.00,250.00,250.00,1.00
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="Account_Degiro.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "DEGIRO"
    assert len(df) == 2
    assert "BUY" in df["tx_type"].values
    assert "SELL" in df["tx_type"].values


def test_parse_scalable_csv():
    csv_data = """Date;Type;Security Name;ISIN;Shares;Price;Total
2026-02-15;Buy;Amundi Prime Global;LU2089238203;20;32.50;650.00
2026-02-18;Distribution;Amundi Prime Global;LU2089238203;0;0;12.40
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="scalable_export.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "SCALABLE"
    assert len(df) == 2


def test_parse_trade_republic_csv():
    csv_data = """Timestamp,Type,Asset,ISIN,Units,Price,Amount
2026-01-10 10:00:00,Buy,NVIDIA CORP,US67066G1040,5,120.50,602.50
2026-01-20 12:00:00,Dividend,NVIDIA CORP,US67066G1040,0,0,8.20
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="trade_republic.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "TRADE_REPUBLIC"
    assert len(df) == 2


def test_parse_ibkr_csv():
    csv_data = """Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee
IBIT,2026-02-01 16:00:00,50,42.00,42.00,-2100.00,1.50
VWCE,2026-02-05 11:30:00,10,118.00,118.00,-1180.00,2.00
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="U1234567_Activity_Statement.csv")
    assert meta["success"] is True
    assert meta["broker_key"] == "IBKR"
    assert len(df) == 2


def test_ingest_broker_transactions_dry_run_and_deduplication():
    engine = get_engine()
    unique_suffix = f"{int(time.time() * 1000) % 10000000:07d}"
    unique_isin = f"IT00{unique_suffix}"
    unique_qty = round(10.0 + (int(unique_suffix) % 50), 2)

    csv_data = f"""Data;Tipo Operazione;Titolo;ISIN;Quantità;Prezzo;Controvalore;Commissioni
01/03/2026;ACQUISTO;UNIQUE TEST ASSET {unique_suffix};{unique_isin};{unique_qty};15,50;{unique_qty * 15.5:.2f};3,00
"""
    df, meta = parse_universal_broker_file(csv_data.encode("utf-8"), filename="directa_test.csv")
    assert len(df) == 1

    # Dry-run
    res_dry = ingest_broker_transactions(engine, df, portfolio_id=1, dry_run=True)
    assert res_dry["new_assets"] >= 0

    # Ingestion reale
    res_real = ingest_broker_transactions(engine, df, portfolio_id=1, dry_run=False)
    assert res_real["inserted"] == 1

    # Seconda ingestion (deduplicazione idempotente)
    res_dup = ingest_broker_transactions(engine, df, portfolio_id=1, dry_run=False)
    assert res_dup["inserted"] == 0
    assert res_dup["skipped_duplicates"] == 1
