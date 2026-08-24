import pytest
import pandas as pd
from sqlalchemy import create_engine, text
from core.fetcher import _upsert_asset, _store_prices, _store_isin_price
from core.risk_engine import _compute_returns
from core.models import Base

def test_sqlite_upsert_and_store_prices():
    # Arrange: SQLite in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    df_clean = pd.DataFrame([{
        "tx_date": "2023-01-10",
        "ticker": "AAPL",
        "tx_type": "buy",
        "quantity": 10.0,
        "price": 150.0,
        "currency": "USD",
        "asset_class": "stock"
    }])

    # Act: Upsert asset in SQLite
    mock_info = {
        "longName": "Apple Inc.",
        "currency": "USD",
        "sector": "Technology",
        "country": "United States",
        "trailingPE": 28.5
    }
    
    asset_id = _upsert_asset("AAPL", None, df_clean, engine, info=mock_info)
    assert asset_id is not None

    # Upsert again to test ON CONFLICT DO UPDATE SET in SQLite
    mock_info["trailingPE"] = 30.0
    asset_id_updated = _upsert_asset("AAPL", None, df_clean, engine, info=mock_info)
    assert asset_id_updated == asset_id

    # Verify updated PE in DB
    with engine.connect() as conn:
        pe = conn.execute(text("SELECT trailing_pe FROM assets WHERE ticker = 'AAPL'")).scalar()
        assert float(pe) == 30.0

    # Store prices with INSERT OR IGNORE in SQLite
    hist_df = pd.DataFrame([
        {"Close": 150.0, "Volume": 1000000},
        {"Close": 152.0, "Volume": 1100000}
    ], index=pd.to_datetime(["2023-01-10", "2023-01-11"]))
    
    rows_written = _store_prices(hist_df, asset_id, engine)
    assert rows_written == 2

    # Store again: should ignore duplicates thanks to INSERT OR IGNORE
    rows_written_again = _store_prices(hist_df, asset_id, engine)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM market_prices WHERE asset_id = :aid"), {"aid": asset_id}).scalar()
        assert count == 2

    # Test ISIN storage on SQLite
    df_isin = pd.DataFrame([{
        "tx_date": "2023-01-15",
        "ticker": "IT0005432109",
        "tx_type": "buy",
        "quantity": 1000.0,
        "price": 99.5,
        "currency": "EUR",
        "asset_class": "bond"
    }])
    report = {"skipped": []}
    _store_isin_price("IT0005432109", df_isin, engine, report)
    
    with engine.connect() as conn:
        isin_count = conn.execute(text("SELECT COUNT(*) FROM assets WHERE ticker = 'IT0005432109'")).scalar()
        assert isin_count == 1


def test_data_quality_gate_stale_prices():
    # Arrange: positions with active ticker
    df_positions = pd.DataFrame([{
        "ticker": "STALE_ASSET",
        "qty_net": 10.0,
        "weight_pct": 100.0,
        "asset_currency": "EUR"
    }])
    
    # 15 consecutive days with flat prices (diff == 0)
    dates = pd.date_range("2023-01-01", periods=15, freq="D")
    df_prices = pd.DataFrame({
        "price_date": dates,
        "ticker": "STALE_ASSET",
        "close": 100.0
    })
    
    df_tx = pd.DataFrame([{
        "tx_date": "2023-01-01",
        "ticker": "STALE_ASSET",
        "currency": "EUR"
    }])
    
    warnings = []
    _compute_returns(df_positions, df_prices, df_tx, warnings_list=warnings)
    
    # Assert: Data Quality Alert generated
    assert any("Data Quality Alert" in w and "STALE_ASSET" in w for w in warnings)
