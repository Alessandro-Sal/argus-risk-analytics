"""
Unit & Integration Tests for core/multi_portfolio.py
"""

import pytest
import pandas as pd
import numpy as np
import os
import shutil
from core.multi_portfolio import (
    save_portfolio_profile,
    list_saved_portfolio_profiles,
    load_portfolio_profile,
    delete_saved_portfolio_profile,
    compute_multi_portfolio_comparison,
    consolidate_multi_portfolios,
    PORTFOLIOS_DIR
)


@pytest.fixture(autouse=True)
def setup_teardown_test_dir():
    os.makedirs(PORTFOLIOS_DIR, exist_ok=True)
    yield
    # Cleanup only test files
    for fname in ["Test_Port_A.pkl", "Test_Port_B.pkl", "Test_Port_C.pkl"]:
        p = os.path.join(PORTFOLIOS_DIR, fname)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


@pytest.fixture
def mock_port_a():
    dates = pd.date_range("2023-01-01", periods=60, freq="B")
    np.random.seed(1)
    r = pd.Series(np.random.normal(0.001, 0.01, 60), index=dates)
    return {
        "portfolio_value": 50000.0,
        "positions": [
            {"ticker": "AAPL", "shares": 200, "market_value": 30000.0, "total_cost": 25000.0, "weight": 0.60, "sector": "Tech"},
            {"ticker": "MSFT", "shares": 50, "market_value": 20000.0, "total_cost": 18000.0, "weight": 0.40, "sector": "Tech"}
        ],
        "metrics": {"cagr": 0.15, "volatility": 0.14, "sharpe_ratio": 1.10, "var_95": 0.015, "max_drawdown": 0.05},
        "returns": r
    }


@pytest.fixture
def mock_port_b():
    dates = pd.date_range("2023-01-01", periods=60, freq="B")
    np.random.seed(2)
    r = pd.Series(np.random.normal(0.0005, 0.008, 60), index=dates)
    return {
        "portfolio_value": 50000.0,
        "positions": [
            {"ticker": "AAPL", "shares": 100, "market_value": 15000.0, "total_cost": 14000.0, "weight": 0.30, "sector": "Tech"},
            {"ticker": "BND", "shares": 400, "market_value": 35000.0, "total_cost": 34000.0, "weight": 0.70, "sector": "Bonds"}
        ],
        "metrics": {"cagr": 0.08, "volatility": 0.07, "sharpe_ratio": 1.25, "var_95": 0.009, "max_drawdown": 0.03},
        "returns": r
    }


def test_save_and_list_portfolio_profile(mock_port_a, mock_port_b):
    assert save_portfolio_profile("Test_Port_A", mock_port_a, tag="Growth") is True
    assert save_portfolio_profile("Test_Port_B", mock_port_b, tag="Defensive") is True
    
    profiles = list_saved_portfolio_profiles()
    names = [p["name"] for p in profiles]
    assert "Test_Port_A" in names
    assert "Test_Port_B" in names


def test_load_and_delete_portfolio_profile(mock_port_a):
    save_portfolio_profile("Test_Port_C", mock_port_a, tag="Test")
    loaded = load_portfolio_profile("Test_Port_C")
    assert loaded is not None
    assert loaded["portfolio_value"] == 50000.0
    assert loaded["tag"] == "Test"
    
    assert delete_saved_portfolio_profile("Test_Port_C") is True
    assert load_portfolio_profile("Test_Port_C") is None


def test_compute_multi_portfolio_comparison(mock_port_a, mock_port_b):
    save_portfolio_profile("Test_Port_A", mock_port_a, tag="Growth")
    save_portfolio_profile("Test_Port_B", mock_port_b, tag="Defensive")
    
    df_comp = compute_multi_portfolio_comparison(["Test_Port_A", "Test_Port_B"])
    assert not df_comp.empty
    assert len(df_comp) == 2
    assert "Quota Wealth (%)" in df_comp.columns
    assert "Sharpe Ratio" in df_comp.columns


def test_consolidate_multi_portfolios(mock_port_a, mock_port_b):
    save_portfolio_profile("Test_Port_A", mock_port_a, tag="Growth")
    save_portfolio_profile("Test_Port_B", mock_port_b, tag="Defensive")
    
    merged = consolidate_multi_portfolios(["Test_Port_A", "Test_Port_B"])
    assert merged is not None
    assert merged["portfolio_value"] == 100000.0
    
    # AAPL era presente in entrambi: 200 + 100 = 300 quote, market value 30000 + 15000 = 45000
    pos_records = merged["positions"].to_dict("records") if isinstance(merged["positions"], pd.DataFrame) else merged["positions"]
    pos_dict = {p["ticker"]: p for p in pos_records}
    assert "AAPL" in pos_dict
    assert pos_dict["AAPL"]["shares"] == 300
    assert pos_dict["AAPL"]["market_value"] == 45000.0
    assert "BND" in pos_dict
    assert "MSFT" in pos_dict
    
    # Pesi normalizzati
    total_weights = sum(p["weight"] for p in pos_records)
    assert pytest.approx(total_weights, abs=1e-3) == 1.0
    assert merged["metrics"]["sharpe_ratio"] > 0.0


def test_gsheets_dual_portfolios_consolidation():
    """Testa specificamente la fusione di un portafoglio Stocks e di un portafoglio Crypto derivati da GSheets."""
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    np.random.seed(42)
    
    port_stocks = {
        "portfolio_value": 75000.0,
        "positions": [
            {"ticker": "VWRL.L", "shares": 500, "market_value": 50000.0, "total_cost": 45000.0, "weight": 0.6667, "sector": "ETF", "asset_class": "etf"},
            {"ticker": "ISP.MI", "shares": 10000, "market_value": 25000.0, "total_cost": 22000.0, "weight": 0.3333, "sector": "Financials", "asset_class": "stock"}
        ],
        "metrics": {"cagr": 0.12, "volatility": 0.15, "sharpe_ratio": 0.80, "var_95": 0.018, "max_drawdown": 0.08},
        "returns": pd.Series(np.random.normal(0.0005, 0.009, 100), index=dates)
    }
    
    port_crypto = {
        "portfolio_value": 25000.0,
        "positions": [
            {"ticker": "BTC-EUR", "shares": 0.5, "market_value": 20000.0, "total_cost": 15000.0, "weight": 0.80, "sector": "Crypto", "asset_class": "crypto"},
            {"ticker": "ETH-EUR", "shares": 2.5, "market_value": 5000.0, "total_cost": 4000.0, "weight": 0.20, "sector": "Crypto", "asset_class": "crypto"}
        ],
        "metrics": {"cagr": 0.35, "volatility": 0.45, "sharpe_ratio": 0.78, "var_95": 0.045, "max_drawdown": 0.22},
        "returns": pd.Series(np.random.normal(0.0012, 0.025, 100), index=dates)
    }
    
    save_portfolio_profile("Wealth_Stocks_Test", port_stocks, tag="Azionario & ETF")
    save_portfolio_profile("Wealth_Crypto_Test", port_crypto, tag="Crypto Assets")
    
    master = consolidate_multi_portfolios(["Wealth_Stocks_Test", "Wealth_Crypto_Test"])
    assert master is not None
    assert master["portfolio_value"] == 100000.0
    
    # Check positions
    pos_records = master["positions"].to_dict("records") if isinstance(master["positions"], pd.DataFrame) else master["positions"]
    pos_map = {p["ticker"]: p for p in pos_records}
    assert "VWRL.L" in pos_map
    assert "BTC-EUR" in pos_map
    assert pos_map["BTC-EUR"]["market_value"] == 20000.0
    assert pytest.approx(pos_map["BTC-EUR"]["weight"], abs=1e-3) == 0.20
    assert pytest.approx(pos_map["VWRL.L"]["weight"], abs=1e-3) == 0.50
    assert pos_map["BTC-EUR"]["country"] == "Globale"
    assert pos_map["BTC-EUR"]["gics_sector"] == "Criptovalute"
    
    # Cleanup
    delete_saved_portfolio_profile("Wealth_Stocks_Test")
    delete_saved_portfolio_profile("Wealth_Crypto_Test")


def test_resolve_asset_metadata_comprehensive():
    from core.multi_portfolio import resolve_asset_metadata
    
    # Crypto
    c_btc, s_btc = resolve_asset_metadata("BTC-EUR", asset_class="crypto")
    assert c_btc == "Globale"
    assert s_btc == "Criptovalute"
    
    # Italian Stock
    c_isp, s_isp = resolve_asset_metadata("ISP.MI", asset_class="stock")
    assert c_isp == "Italia"
    assert s_isp == "Servizi Finanziari"
    
    # Danish Stock
    c_novo, s_novo = resolve_asset_metadata("NOVO-B.CO", asset_class="stock")
    assert c_novo == "Danimarca"
    assert s_novo == "Salute & Pharma"
    
    # Chinese Stock
    c_baba, s_baba = resolve_asset_metadata("BABA", asset_class="stock")
    assert c_baba == "Cina"
    assert s_baba == "Beni di Consumo"
    
    # US Stock
    c_goog, s_goog = resolve_asset_metadata("GOOGL", asset_class="stock", yf_country="United States", yf_sector="Communication Services")
    assert c_goog == "Stati Uniti"
    assert s_goog == "Comunicazioni & Media"
    
    # Emerging Market ETF
    c_ndia, s_ndia = resolve_asset_metadata("NDIA.L", asset_class="etf")
    assert c_ndia == "India"
    assert s_ndia == "ETF Mercati Emergenti"


