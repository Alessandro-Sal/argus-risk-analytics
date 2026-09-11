# ==============================================================================
# tests/test_data_quality_gate.py
# Unit tests for ARGUS DataQualityGate & Pydantic Validation Middleware
# ==============================================================================

from datetime import date, timedelta
import pandas as pd
import pytest
pydantic = pytest.importorskip("pydantic")
from pydantic import ValidationError

from core.data_quality_gate import (
    CanonicalTradeRecord,
    DataQualityGate,
    QualityGateReport,
    TransactionType,
)
from core.adapters.broker_hub import parse_broker_csv


def test_canonical_trade_record_valid():
    """Verifica che un record corretto venga validato e tipizzato con precisione."""
    rec = CanonicalTradeRecord(
        broker="InteractiveBrokers",
        portfolio_id=1,
        tx_date=date(2026, 1, 15),
        ticker="AAPL",
        tx_type=TransactionType.BUY,
        quantity=10.5,
        price=150.0,
        currency="USD",
        fees=1.0,
        notes="Purchase trade"
    )
    assert rec.ticker == "AAPL"
    assert rec.quantity == 10.5
    assert rec.price == 150.0
    assert rec.currency == "USD"
    assert len(rec.canonical_hash) == 64


def test_canonical_trade_record_flexible_inputs():
    """Verifica la normalizzazione flessibile di stringhe per date e tipologie di operazione."""
    rec = CanonicalTradeRecord(
        broker="Fineco",
        portfolio_id=1,
        tx_date="15/01/2026",
        ticker="  swda.mi  ",
        tx_type="ACQUISTO",
        quantity="50",
        price="95.50",
        currency="eur"
    )
    assert rec.tx_date == date(2026, 1, 15)
    assert rec.ticker == "SWDA.MI"
    assert rec.tx_type == TransactionType.BUY
    assert rec.quantity == 50.0
    assert rec.price == 95.50
    assert rec.currency == "EUR"


def test_canonical_trade_record_validation_errors():
    """Verifica che dati anomali o corrotti sollevino eccezioni di validazione."""
    # Data futura non ammessa
    future_date = date.today() + timedelta(days=5)
    with pytest.raises(ValidationError):
        CanonicalTradeRecord(
            broker="Generic",
            tx_date=future_date,
            ticker="AAPL",
            tx_type="buy",
            quantity=10,
            price=100
        )

    # Prezzo zero su acquisto
    with pytest.raises(ValidationError):
        CanonicalTradeRecord(
            broker="Generic",
            tx_date="2026-01-10",
            ticker="AAPL",
            tx_type="buy",
            quantity=10,
            price=0.0
        )

    # Quantità zero o negativa
    with pytest.raises(ValidationError):
        CanonicalTradeRecord(
            broker="Generic",
            tx_date="2026-01-10",
            ticker="AAPL",
            tx_type="buy",
            quantity=-5.0,
            price=100
        )

    # Ticker non valido
    with pytest.raises(ValidationError):
        CanonicalTradeRecord(
            broker="Generic",
            tx_date="2026-01-10",
            ticker="NAN",
            tx_type="buy",
            quantity=5.0,
            price=100
        )


def test_canonical_hash_invariance():
    """Verifica che l'hash SHA-256 sia insensibile a maiuscole, spazi e formati numerici equivalenti."""
    r1 = CanonicalTradeRecord(
        broker="degiro",
        portfolio_id=1,
        tx_date="2026-05-10",
        ticker="vwce.mi",
        tx_type="buy",
        quantity=100.0,
        price=115.50,
        currency="EUR"
    )
    r2 = CanonicalTradeRecord(
        broker="  DeGiro  ",
        portfolio_id=1,
        tx_date="10/05/2026",
        ticker="VWCE.MI",
        tx_type="ACQUISTO",
        quantity=100,
        price=115.5,
        currency="eur"
    )
    assert r1.canonical_hash == r2.canonical_hash


def test_data_quality_gate_processing_and_deduplication():
    """Verifica la deduplicazione automatica di record identici all'interno del batch."""
    df_raw = pd.DataFrame([
        {
            "tx_date": "2026-02-10",
            "ticker": "AAPL",
            "tx_type": "buy",
            "quantity": 10.0,
            "price": 180.0,
            "currency": "USD"
        },
        {
            # Duplicato esatto
            "tx_date": "2026-02-10",
            "ticker": "AAPL",
            "tx_type": "buy",
            "quantity": 10.0,
            "price": 180.0,
            "currency": "USD"
        },
        {
            # Secondo trade diverso
            "tx_date": "2026-02-11",
            "ticker": "MSFT",
            "tx_type": "buy",
            "quantity": 5.0,
            "price": 400.0,
            "currency": "USD"
        }
    ])

    gate = DataQualityGate()
    df_clean, report = gate.process(df_raw, broker_name="test_broker", portfolio_id=1)

    assert report.is_valid is True
    assert report.total_raw_rows == 3
    assert report.valid_rows_count == 2
    assert report.duplicates_suppressed == 1
    assert len(df_clean) == 2
    assert "tx_hash" in df_clean.columns


def test_data_quality_gate_short_position_warning():
    """Verifica il tracciamento di anomalie di inventario quando le vendite eccedono gli acquisti."""
    df_raw = pd.DataFrame([
        {
            "tx_date": "2026-03-01",
            "ticker": "NVDA",
            "tx_type": "buy",
            "quantity": 10.0,
            "price": 120.0,
            "currency": "USD"
        },
        {
            "tx_date": "2026-03-05",
            "ticker": "NVDA",
            "tx_type": "sell",
            "quantity": 15.0,  # Vendita di 15 quote avendone comprate solo 10
            "price": 130.0,
            "currency": "USD"
        }
    ])

    gate = DataQualityGate(reject_on_short_sell=False)
    df_clean, report = gate.process(df_raw, broker_name="test_broker")

    assert report.is_valid is True
    assert len(report.semantic_warnings) >= 1
    assert any("Vendita di 15.0000 quote eccede la disponibilità" in w for w in report.semantic_warnings)


def test_broker_hub_parse_with_quality_gate():
    """Verifica l'integrazione di DataQualityGate all'interno del broker_hub."""
    df_raw = pd.DataFrame({
        "tx_date": ["2026-01-10", "2026-01-12"],
        "ticker": ["AAPL", "GOOGL"],
        "tx_type": ["buy", "buy"],
        "quantity": [10.0, 20.0],
        "price": [150.0, 140.0],
        "currency": ["USD", "USD"]
    })

    df_parsed, detected_key, report = parse_broker_csv(df_raw, broker_key="standard", apply_quality_gate=True)

    assert detected_key == "standard"
    assert report["quality_gate"]["is_valid"] is True
    assert report["quality_gate"]["valid_rows_count"] == 2


def test_market_data_quality_gate_alignment_and_ffill():
    """Verifica l'allineamento su asse feriale continuativo e forward-fill fino a 5 giorni."""
    from core.data_quality_gate import MarketDataQualityGate

    # Serie con buco feriale (es. martedì e mercoledì mancanti per festività estera)
    dates = ["2026-01-05", "2026-01-08", "2026-01-09"]  # Lunedì, Giovedì, Venerdì
    df_p = pd.DataFrame({
        "price_date": dates * 2,
        "ticker": ["AAPL"] * 3 + ["ENI.MI"] * 3,
        "close": [150.0, 155.0, 156.0, 14.0, 14.2, 14.3]
    })

    gate = MarketDataQualityGate(min_history_days=2, max_ffill_days=5)
    pivot, report = gate.validate_and_align_prices(df_p, required_tickers={"AAPL", "ENI.MI"})

    assert report.is_valid is True
    assert "AAPL" in pivot.columns
    assert "ENI.MI" in pivot.columns
    # Il martedì 2026-01-06 deve essere presente e valorizzato tramite forward fill dal lunedì
    ts_tue = pd.Timestamp("2026-01-06")
    assert ts_tue in pivot.index
    assert pivot.loc[ts_tue, "AAPL"] == 150.0


def test_market_data_quality_gate_stale_and_jump_detection():
    """Verifica il rilevamento di serie stantie e salti anomali di rendimento."""
    from core.data_quality_gate import MarketDataQualityGate

    # Genera 15 giorni con prezzo costante (stale) e un salto estremo finale (+50%)
    dates = pd.date_range("2026-01-01", periods=25, freq="B")
    prices = [100.0] * 15 + [100.0, 101.0, 100.5, 100.8, 100.2, 100.1, 100.3, 100.2, 100.4, 180.0]

    df_p = pd.DataFrame({
        "price_date": dates,
        "ticker": ["FLAT_CORP"] * len(dates),
        "close": prices
    })

    gate = MarketDataQualityGate(min_history_days=10, max_stale_streak=10, z_score_jump_threshold=3.0)
    pivot, report = gate.validate_and_align_prices(df_p, required_tickers={"FLAT_CORP"})

    assert report.is_valid is True
    assert "FLAT_CORP" in report.stale_price_tickers
    assert report.stale_price_tickers["FLAT_CORP"] >= 10
    # Verifica anomalia di rendimento rilevata
    assert len(report.abnormal_returns) >= 1
    assert any(a["ticker"] == "FLAT_CORP" for a in report.abnormal_returns)
