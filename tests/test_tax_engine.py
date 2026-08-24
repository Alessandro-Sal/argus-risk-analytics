"""
ARGUS — Risk Analytics Platform
Unit Tests for Tax Optimization & Tax-Loss Harvesting Engine
"""

import pytest
import pandas as pd
from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate

def test_get_asset_tax_rate():
    assert get_asset_tax_rate("Equity", "GOOGL") == 0.26
    assert get_asset_tax_rate("Government Bond", "BTP-1FE27") == 0.125
    assert get_asset_tax_rate("ETF", "BTP-ITALIA") == 0.125
    assert get_asset_tax_rate("Crypto", "BTC-USD") == 0.26

def test_tax_engine_calculation():
    positions_data = [
        {"ticker": "GOOGL", "asset_class": "Equity", "qty_net": 10, "cost_basis": 1000.0, "unrealized_pnl": 500.0, "realized_pnl": 200.0},
        {"ticker": "BABA", "asset_class": "Equity", "qty_net": 20, "cost_basis": 2000.0, "unrealized_pnl": -300.0, "realized_pnl": 0.0},
        {"ticker": "BTP", "asset_class": "Government Bond", "qty_net": 100, "cost_basis": 10000.0, "unrealized_pnl": -50.0, "realized_pnl": 100.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}
    
    tax_res = compute_tax_and_harvesting(results)
    summary = tax_res["summary"]
    
    assert summary["total_realized_gain_eur"] == 300.0
    assert summary["net_realized_pnl_eur"] == 300.0
    df_harvest = tax_res["harvesting_opportunities"]
    assert not df_harvest.empty
    assert "potential_tax_saving_eur" in df_harvest.columns


def test_compute_zainetto_timeline():
    from core.tax_engine import compute_zainetto_timeline

    # Scenario: 2022 Loss -> 2024 Partial Gain -> 2026 (Current)
    df_yearly = pd.DataFrame([
        {"year": 2022, "realized_gain_diversi_eur": 1000.0, "realized_loss_eur": 5000.0},
        {"year": 2023, "realized_gain_diversi_eur": 0.0, "realized_loss_eur": 2000.0},
        {"year": 2024, "realized_gain_diversi_eur": 3000.0, "realized_loss_eur": 0.0},
        {"year": 2025, "realized_gain_diversi_eur": 0.0, "realized_loss_eur": 0.0},
        {"year": 2026, "realized_gain_diversi_eur": 0.0, "realized_loss_eur": 0.0},
    ])

    df_timeline = compute_zainetto_timeline(df_yearly, current_year=2026)
    assert not df_timeline.empty
    assert len(df_timeline) == 2  # 2 buckets generated (2022 and 2023)
    
    row_2022 = df_timeline[df_timeline["origin_year"] == 2022].iloc[0]
    assert row_2022["initial_minus_eur"] == 4000.0
    assert row_2022["compensated_eur"] == 3000.0
    assert row_2022["residual_active_eur"] == 1000.0
    assert row_2022["expiry_year"] == 2026
    assert row_2022["years_to_expiry"] == 0
    assert row_2022["urgency"] == "CRITICAL"

    row_2023 = df_timeline[df_timeline["origin_year"] == 2023].iloc[0]
    assert row_2023["initial_minus_eur"] == 2000.0
    assert row_2023["compensated_eur"] == 0.0
    assert row_2023["residual_active_eur"] == 2000.0
    assert row_2023["expiry_year"] == 2027
    assert row_2023["years_to_expiry"] == 1
    assert row_2023["urgency"] == "HIGH"


def test_compute_riforma_fiscale_comparison():
    from core.tax_engine import compute_riforma_fiscale_comparison
    
    positions_data = [
        {"ticker": "AAPL", "asset_class": "Equity", "qty_net": 10, "cost_basis_eur": 1500.0, "current_value": 2000.0, "realized_pnl": 500.0, "unrealized_pnl": 500.0},
        {"ticker": "CSPX", "asset_class": "ETF", "qty_net": 20, "cost_basis_eur": 8000.0, "current_value": 10000.0, "realized_pnl": 2000.0, "unrealized_pnl": 2000.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}
    
    comp = compute_riforma_fiscale_comparison(results, custom_zainetto_eur=1000.0)
    assert "current_regime" in comp
    assert "reformed_regime" in comp
    assert "comparison" in comp
    # In Reformed regime, the full 1000€ minus is applied to total gains (500 + 2000 = 2500)
    assert comp["reformed_regime"]["minus_applied_eur"] == 1000.0
    assert comp["comparison"]["net_tax_savings_eur"] > 0


def test_compute_modello_redditi_pf():
    from core.tax_engine import compute_modello_redditi_pf
    
    positions_data = [
        {"ticker": "AAPL", "asset_class": "Equity", "cost_basis_eur": 1000.0, "current_value": 1500.0, "realized_pnl": 200.0},
        {"ticker": "BTC", "asset_class": "Crypto", "cost_basis_eur": 2000.0, "current_value": 3000.0, "realized_pnl": 0.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}
    
    modello = compute_modello_redditi_pf(results, tax_year=2026, prior_minus_custom_eur=100.0)
    assert "df_quadro_rt" in modello
    assert "df_quadro_rw" in modello
    df_rt = modello["df_quadro_rt"]
    df_rw = modello["df_quadro_rw"]
    assert not df_rt.empty
    assert not df_rw.empty
    assert "RT21" in df_rt["rigo"].values
    assert "RT26" in df_rt["rigo"].values
    assert any("069" in str(cp) for cp in df_rw["codice_paese"])


def test_compute_withholding_tax_analysis():
    from core.tax_engine import compute_withholding_tax_analysis
    
    positions_data = [
        {"ticker": "AAPL", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 300.0, "dividend_yield_pct": 3.0},
        {"ticker": "ALV.DE", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 500.0, "dividend_yield_pct": 5.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}
    
    wht_res = compute_withholding_tax_analysis(results)
    df_wht = wht_res["df_withholding"]
    assert not df_wht.empty
    assert len(df_wht) == 2
    assert "aliquota_effettiva_combinata_pct" in df_wht.columns
    # US effective rate ~ 37.1% (15% US + 26% on net)
    aapl_row = df_wht[df_wht["ticker"] == "AAPL"].iloc[0]
    assert 37.0 <= aapl_row["aliquota_effettiva_combinata_pct"] <= 37.2


def test_simulate_fifo_lot_sale():
    from core.tax_engine import simulate_fifo_lot_sale
    
    positions_data = [
        {"ticker": "NVDA", "asset_class": "Equity", "qty_net": 100.0, "current_price": 120.0, "cost_basis_eur": 80.0}
    ]
    tx_data = [
        {"ticker": "NVDA", "tx_type": "buy", "quantity": 40.0, "price": 60.0, "tx_date": "2024-01-10"},
        {"ticker": "NVDA", "tx_type": "buy", "quantity": 60.0, "price": 93.33, "tx_date": "2024-06-15"}
    ]
    results = {"positions": pd.DataFrame(positions_data), "df_tx": pd.DataFrame(tx_data)}
    
    sim = simulate_fifo_lot_sale(results, ticker="NVDA", qty_to_sell=50.0, sale_price=120.0)
    assert sim["qty_requested_to_sell"] == 50.0
    assert sim["total_proceeds_eur"] == 6000.0 # 50 * 120
    assert len(sim["df_affected_lots"]) == 2 # 40 from lot 1 + 10 from lot 2
    assert sim["realized_pnl_eur"] > 0
    assert sim["residual_shares"] == 50.0


