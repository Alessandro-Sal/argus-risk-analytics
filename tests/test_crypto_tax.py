"""
Unit tests for Crypto Tax Engine (L. 197/2022, Circolare AdE 30/E/2023, Quadri RT/RW/IVAFE).
"""

import pandas as pd

from core.crypto_tax_engine import (
    compute_crypto_tax_report,
    is_crypto_asset,
)


def test_is_crypto_asset():
    assert is_crypto_asset("Crypto", "BTC-EUR") is True
    assert is_crypto_asset("Criptovaluta", "ETH-USD") is True
    assert is_crypto_asset("Token", "SOL") is True
    assert is_crypto_asset("Equity", "AAPL") is False
    assert is_crypto_asset("ETF", "VWCE.DE") is False
    assert is_crypto_asset("Bond", "BTP-2030") is False


def test_crypto_tax_threshold_below_2000():
    """Verifica che plusvalenze nette inferiori o uguali a 2.000€ siano esenti da imposta sostitutiva."""
    results = {
        "positions": pd.DataFrame(),
        "df_tx": pd.DataFrame([
            {"tx_id": 1, "tx_date": "2024-01-10", "tx_type": "buy", "quantity": 0.1, "price": 40000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
            {"tx_id": 2, "tx_date": "2024-06-15", "tx_type": "sell", "quantity": 0.1, "price": 55000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
        ]),
    }
    # Gain: 0.1 * (55000 - 40000) = 1.500€ <= 2.000€
    report = compute_crypto_tax_report(results, tax_year=2024)
    summary = report["summary"]

    assert summary["total_realized_gains_eur"] == 1500.0
    assert summary["total_tax_due_rt_eur"] == 0.0
    assert bool(report["df_rt"].iloc[0]["threshold_exempt"]) is True


def test_crypto_tax_threshold_above_2000():
    """Verifica che plusvalenze nette superiori a 2.000€ siano tassate all'aliquota del 26%."""
    results = {
        "positions": pd.DataFrame(),
        "df_tx": pd.DataFrame([
            {"tx_id": 1, "tx_date": "2024-01-10", "tx_type": "buy", "quantity": 0.2, "price": 40000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
            {"tx_id": 2, "tx_date": "2024-06-15", "tx_type": "sell", "quantity": 0.2, "price": 60000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
        ]),
    }
    # Gain: 0.2 * (60000 - 40000) = 4.000€ > 2.000€
    report = compute_crypto_tax_report(results, tax_year=2024)
    summary = report["summary"]

    assert summary["total_realized_gains_eur"] == 4000.0
    assert summary["total_tax_due_rt_eur"] == 4000.0 * 0.26
    assert bool(report["df_rt"].iloc[0]["threshold_exempt"]) is False


def test_crypto_separate_zainetto_deduction():
    """Verifica che le minusvalenze cripto pregresse vengano dedotte dalle plusvalenze cripto."""
    results = {
        "positions": pd.DataFrame(),
        "df_tx": pd.DataFrame([
            # 2023: perdita di 1.500€
            {"tx_id": 1, "tx_date": "2023-01-10", "tx_type": "buy", "quantity": 1.0, "price": 20000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
            {"tx_id": 2, "tx_date": "2023-05-15", "tx_type": "sell", "quantity": 1.0, "price": 18500.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
            # 2024: guadagno di 4.000€ -> al netto di 1.500€ = 2.500€ (> 2.000€)
            {"tx_id": 3, "tx_date": "2024-01-10", "tx_type": "buy", "quantity": 1.0, "price": 30000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
            {"tx_id": 4, "tx_date": "2024-09-15", "tx_type": "sell", "quantity": 1.0, "price": 34000.0, "currency": "EUR", "ticker": "BTC-EUR", "asset_class": "Crypto"},
        ]),
    }
    report = compute_crypto_tax_report(results)
    df_rt = report["df_rt"]

    # Nel 2024: plusvalenza 4.000 - minusvalenza dedotta 1.500 = base imponibile 2.500
    row_2024 = df_rt[df_rt["year"] == 2024].iloc[0]
    assert row_2024["prior_crypto_minus_deducted_eur"] == 1500.0
    assert row_2024["taxable_base_rt_eur"] == 2500.0
    assert row_2024["tax_due_rt_eur"] == 2500.0 * 0.26


def test_crypto_quadro_rw_and_ivafe():
    """Verifica la compilazione del Quadro RW con Codice 21 e il calcolo dell'IVAFE allo 0,20%."""
    results = {
        "positions": pd.DataFrame([
            {
                "ticker": "BTC-EUR",
                "asset_class": "Crypto",
                "qty_net": 0.5,
                "cost_basis": 20000.0,
                "current_value": 30000.0,
                "pnl_unrealized": 10000.0,
            },
            {
                "ticker": "ETH-EUR",
                "asset_class": "Crypto",
                "qty_net": 5.0,
                "cost_basis": 10000.0,
                "current_value": 15000.0,
                "pnl_unrealized": 5000.0,
            },
        ]),
        "df_tx": pd.DataFrame(),
    }
    report = compute_crypto_tax_report(results)
    df_rw = report["df_rw"]
    summary = report["summary"]

    assert not df_rw.empty
    assert len(df_rw) == 2
    assert (df_rw["codice_investimento"] == "21").all()
    assert (df_rw["quota_possesso_pct"] == 100.0).all()

    # IVAFE totale: (30000 + 15000) * 0.002 = 90.00€
    assert summary["total_crypto_portfolio_val_eur"] == 45000.0
    assert summary["total_ivafe_rw_eur"] == 90.0


def test_crypto_dynamic_fx_conversion():
    """Verifica che transazioni in USD utilizzino i tassi di cambio storici dinamici forniti da df_prices."""
    df_prices = pd.DataFrame([
        {"ticker": "USDEUR=X", "price_date": pd.to_datetime("2024-01-10"), "close": 0.90},
        {"ticker": "USDEUR=X", "price_date": pd.to_datetime("2024-06-15"), "close": 0.95},
    ])
    results = {
        "positions": pd.DataFrame(),
        "df_prices": df_prices,
        "df_tx": pd.DataFrame([
            # Buy 1 BTC @ 40,000 USD on 2024-01-10 -> cost in EUR = 40,000 * 0.90 = 36,000 EUR
            {"tx_id": 1, "tx_date": "2024-01-10", "tx_type": "buy", "quantity": 1.0, "price": 40000.0, "currency": "USD", "ticker": "BTC-USD", "asset_class": "Crypto"},
            # Sell 1 BTC @ 50,000 USD on 2024-06-15 -> revenue in EUR = 50,000 * 0.95 = 47,500 EUR
            # Realized Gain in EUR = 47,500 - 36,000 = 11,500 EUR
            {"tx_id": 2, "tx_date": "2024-06-15", "tx_type": "sell", "quantity": 1.0, "price": 50000.0, "currency": "USD", "ticker": "BTC-USD", "asset_class": "Crypto"},
        ]),
    }
    report = compute_crypto_tax_report(results, tax_year=2024)
    summary = report["summary"]

    assert summary["total_realized_gains_eur"] == 11500.0
    assert summary["total_tax_due_rt_eur"] == 11500.0 * 0.26
