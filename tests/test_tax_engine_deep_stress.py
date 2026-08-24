"""
ARGUS — Risk Analytics Platform
Comprehensive Deep Stress & Boundary Tests for Tax Suite
"""

import pytest
import pandas as pd
import numpy as np
from core.tax_engine import (
    get_asset_tax_rate,
    is_etf,
    compute_tax_and_harvesting,
    compute_zainetto_timeline,
    generate_tax_loss_harvesting_strategy,
    compute_riforma_fiscale_comparison,
    compute_modello_redditi_pf,
    compute_withholding_tax_analysis,
    simulate_fifo_lot_sale,
)


def test_asset_tax_rate_and_etf_classification_deep():
    # Government bonds and state obligations
    assert get_asset_tax_rate("Government Bond", "BTP-1AG34") == 0.125
    assert get_asset_tax_rate("Bond", "BOT-12M") == 0.125
    assert get_asset_tax_rate("Fixed Income", "US-TREASURY-10Y") == 0.125
    assert get_asset_tax_rate("Obbligazioni di Stato", "OAT-FR") == 0.125
    
    # Equities, Corporate Bonds, Crypto
    assert get_asset_tax_rate("Equity", "AAPL") == 0.26
    assert get_asset_tax_rate("Corporate Bond", "ENI-CORP-28") == 0.26
    assert get_asset_tax_rate("Crypto", "ETH-USD") == 0.26
    assert get_asset_tax_rate("Commodity", "GLD") == 0.26
    assert get_asset_tax_rate("", "") == 0.26

    # ETF detection
    assert is_etf("ETF", "VWCE") is True
    assert is_etf("Equity ETF", "CSSPX.MI") is True
    assert is_etf("Equity", "CSPX") is True
    assert is_etf("Equity", "XEON") is True
    assert is_etf("Equity", "AAPL") is False
    assert is_etf("Government Bond", "BTP-1FE27") is False


def test_riforma_fiscale_all_scenarios():
    # Scenario A: Portfolio with ONLY ETF gains and large prior minusvalenze
    results_etf_only = {
        "positions": pd.DataFrame([
            {"ticker": "VWCE", "asset_class": "ETF", "current_value": 50000.0, "realized_pnl": 10000.0, "unrealized_pnl": 5000.0}
        ])
    }
    comp_a = compute_riforma_fiscale_comparison(results_etf_only, custom_zainetto_eur=5000.0)
    # Current regime: cannot offset ETF gain -> 10,000 * 0.26 = 2,600 €
    assert comp_a["current_regime"]["tax_due_eur"] == 2600.0
    assert comp_a["current_regime"]["minus_applied_eur"] == 0.0
    # Reformed regime: offsets 5,000 € -> taxable = 5,000 € -> tax = 1,300 €
    assert comp_a["reformed_regime"]["tax_due_eur"] == 1300.0
    assert comp_a["reformed_regime"]["minus_applied_eur"] == 5000.0
    assert comp_a["comparison"]["net_tax_savings_eur"] == 1300.0

    # Scenario B: Portfolio with zero gains
    results_empty = {"positions": pd.DataFrame()}
    comp_empty = compute_riforma_fiscale_comparison(results_empty, custom_zainetto_eur=2000.0)
    assert comp_empty["current_regime"]["tax_due_eur"] == 0.0
    assert comp_empty["reformed_regime"]["tax_due_eur"] == 0.0
    assert comp_empty["comparison"]["net_tax_savings_eur"] == 0.0


def test_modello_redditi_pf_boundary_conditions():
    # Test IVAFE under exemption threshold (< 12 €)
    pos_low_val = pd.DataFrame([
        {"ticker": "AAPL", "asset_class": "Equity", "cost_basis_eur": 1000.0, "current_value": 2000.0, "realized_pnl": 100.0}
    ])
    res_low = {"positions": pos_low_val}
    pf_low = compute_modello_redditi_pf(res_low, prior_minus_custom_eur=0.0)
    # 2000 * 0.002 = 4.00 € (< 12 € threshold)
    assert pf_low["summary"]["totale_ivafe_rw_eur"] == 0.0
    assert pf_low["summary"]["esenzione_ivafe_applicata"] is True

    # Test IVAFE above exemption threshold (> 12 €)
    pos_high_val = pd.DataFrame([
        {"ticker": "AAPL", "asset_class": "Equity", "cost_basis_eur": 10000.0, "current_value": 20000.0, "realized_pnl": 500.0}
    ])
    res_high = {"positions": pos_high_val}
    pf_high = compute_modello_redditi_pf(res_high, prior_minus_custom_eur=0.0)
    # 20000 * 0.002 = 40.00 € (>= 12 €)
    assert pf_high["summary"]["totale_ivafe_rw_eur"] == 40.0
    assert pf_high["summary"]["esenzione_ivafe_applicata"] is False

    # Test Italian asset (.MI) exclusion from Quadro RW
    pos_italian = pd.DataFrame([
        {"ticker": "ENEL.MI", "asset_class": "Equity", "cost_basis_eur": 5000.0, "current_value": 6000.0, "realized_pnl": 500.0}
    ])
    res_it = {"positions": pos_italian}
    pf_it = compute_modello_redditi_pf(res_it)
    # Italian tickers listed on Borsa Italiana should not appear in Quadro RW
    assert pf_it["df_quadro_rw"].empty


def test_withholding_tax_multi_country():
    # Test all distinct jurisdictions and their specific rates
    pos_multi = pd.DataFrame([
        {"ticker": "AAPL", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},        # US 15%
        {"ticker": "BMW.DE", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},       # DE 26.375%
        {"ticker": "MC.PA", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},        # FR 12.8%
        {"ticker": "NESN.SW", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},      # CH 35%
        {"ticker": "NOVO-B.CO", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},    # DK 27%
        {"ticker": "SHEL.L", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},       # UK 0%
        {"ticker": "ENI.MI", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 100.0},       # IT 0% foreign WHT
        {"ticker": "VWCE", "asset_class": "ETF", "current_value": 10000.0, "dividends_total": 100.0},           # UCITS ETF
    ])
    wht_res = compute_withholding_tax_analysis({"positions": pos_multi})
    df_wht = wht_res["df_withholding"]
    assert len(df_wht) == 8

    # Check effective rates:
    # US: 100 * 0.15 = 15 WHT, 85 * 0.26 = 22.1 IT -> Total = 37.1%
    row_us = df_wht[df_wht["ticker"] == "AAPL"].iloc[0]
    assert pytest.approx(row_us["aliquota_effettiva_combinata_pct"], 0.01) == 37.10

    # UK: 100 * 0 = 0 WHT, 100 * 0.26 = 26 IT -> Total = 26.0%
    row_uk = df_wht[df_wht["ticker"] == "SHEL.L"].iloc[0]
    assert pytest.approx(row_uk["aliquota_effettiva_combinata_pct"], 0.01) == 26.00

    # CH: 100 * 0.35 = 35 WHT, 65 * 0.26 = 16.9 IT -> Total = 51.9%
    row_ch = df_wht[df_wht["ticker"] == "NESN.SW"].iloc[0]
    assert pytest.approx(row_ch["aliquota_effettiva_combinata_pct"], 0.01) == 51.90


def test_simulate_fifo_lot_sale_deep_multi_tranche():
    # Multi-tranche purchase history with partial sells
    pos_data = pd.DataFrame([
        {"ticker": "MSFT", "asset_class": "Equity", "qty_net": 150.0, "current_price": 400.0, "cost_basis_eur": 300.0}
    ])
    tx_data = pd.DataFrame([
        {"ticker": "MSFT", "tx_type": "buy", "quantity": 50.0, "price": 200.0, "tx_date": "2023-01-15"},
        {"ticker": "MSFT", "tx_type": "buy", "quantity": 50.0, "price": 300.0, "tx_date": "2023-06-20"},
        {"ticker": "MSFT", "tx_type": "buy", "quantity": 100.0, "price": 350.0, "tx_date": "2024-02-10"},
        {"ticker": "MSFT", "tx_type": "sell", "quantity": 50.0, "price": 380.0, "tx_date": "2024-05-01"}, # Consumes the first 50 @ 200
    ])
    results = {"positions": pos_data, "df_tx": tx_data}

    # Now open lots remaining should be:
    # 50 @ 300
    # 100 @ 350
    # Let's simulate selling 75 shares @ 420.0
    sim = simulate_fifo_lot_sale(results, ticker="MSFT", qty_to_sell=75.0, sale_price=420.0)
    
    assert sim["qty_requested_to_sell"] == 75.0
    assert sim["sale_price_eur"] == 420.0
    assert sim["total_proceeds_eur"] == 75.0 * 420.0 # 31,500.0
    
    # 50 shares from lot 2 @ 300 (Cost = 15,000, Proceeds = 21,000, PnL = +6,000)
    # 25 shares from lot 3 @ 350 (Cost = 8,750, Proceeds = 10,500, PnL = +1,750)
    # Total cost basis discharged = 23,750.0
    # Total PnL = 7,750.0
    assert pytest.approx(sim["total_cost_discharged_eur"], 0.01) == 23750.0
    assert pytest.approx(sim["total_realized_pnl_eur"], 0.01) == 7750.0
    assert pytest.approx(sim["estimated_tax_due_eur"], 0.01) == 7750.0 * 0.26 # 2,015.0
    assert sim["residual_shares"] == 75.0
    assert len(sim["df_affected_lots"]) == 2
