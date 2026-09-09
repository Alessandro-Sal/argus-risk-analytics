# ============================================================
# tests/test_tax_engine_normative_audit.py
# ARGUS — Unit Tests for Tax Engine Normative & Accounting Hardening
# Verifies Italian Fiscal Framework Compliance (TUIR Artt. 44, 67, 68, L. 197/2022, L. 213/2023)
# ============================================================

import pytest
import pandas as pd
import numpy as np

from core.tax_engine import (
    compute_modello_redditi_pf,
    compute_withholding_tax_analysis,
    is_etf,
    get_asset_tax_rate
)
from core.tax_aware_rebalancer import TaxAwarePortfolioRebalancer, FrictionConfig
from core.prescriptive_rebalancer import (
    PrescriptiveConicRebalancer,
    PositionLot,
    TaxWalletState
)


# ── 1. TEST ASIMMETRIA ETF NEI REBALANCER (TUIR Art. 44 vs 67) ──

def test_rebalancer_etf_asymmetry_tax_aware_rebalancer():
    """
    Verifica che il ribilanciatore rispetti l'asimmetria fiscale italiana:
    - Vendita ETF in guadagno: genera Redditi di Capitale (Art. 44) -> NON assorbe minusvalenze.
    - Vendita Azione in guadagno: genera Redditi Diversi (Art. 67) -> ASSORBE minusvalenze.
    """
    holdings_data = [
        {"ticker": "VWCE.DE", "asset_class": "ETF", "market_value": 10000.0},
        {"ticker": "AAPL", "asset_class": "Equity", "market_value": 10000.0},
    ]
    df_holdings = pd.DataFrame(holdings_data)

    # Caso A: Ribilanciamento riduce solo l'ETF (vendita ETF in guadagno stimato)
    # L'investitore ha 2.000€ di minusvalenze pregresse
    target_weights_etf_sell = {"VWCE.DE": 0.20, "AAPL": 0.80}
    plan_etf = TaxAwarePortfolioRebalancer.compute_full_rebalance_plan(
        current_holdings=df_holdings,
        target_weights=target_weights_etf_sell,
        total_portfolio_value=20000.0,
        existing_minusvalenze=2000.0
    )
    
    # Per VWCE (ETF venduto), le minusvalenze NON devono essere intaccate
    assert plan_etf["remaining_minusvalenze_eur"] == 2000.0
    # L'imposta stimata deve essere maggiore di zero (26% sul capital gain stimato dell'ETF)
    assert plan_etf["estimated_tax_eur"] > 0.0

    # Caso B: Ribilanciamento riduce solo l'Azione AAPL (vendita Equity in guadagno)
    target_weights_stock_sell = {"VWCE.DE": 0.80, "AAPL": 0.20}
    plan_stock = TaxAwarePortfolioRebalancer.compute_full_rebalance_plan(
        current_holdings=df_holdings,
        target_weights=target_weights_stock_sell,
        total_portfolio_value=20000.0,
        existing_minusvalenze=2000.0
    )
    
    # Per AAPL (Azione venduta), le minusvalenze devono essere consumate
    assert plan_stock["remaining_minusvalenze_eur"] < 2000.0
    # L'imposta stimata su AAPL deve essere zero se il guadagno stimato (6000 * 0.15 = 900) è coperto da 2000€ di minus
    assert plan_stock["estimated_tax_eur"] == 0.0


def test_prescriptive_rebalancer_etf_asymmetry():
    """
    Verifica che PrescriptiveConicRebalancer non compensi minusvalenze con plusvalenze da ETF.
    """
    # 1. Posizione ETF in utile
    etf_pos = PositionLot(
        ticker="SWDA.MI",
        shares=100.0,
        current_price=100.0,
        pmc=70.0, # +3000€ unrealized gain
        asset_class="ETF"
    )
    # 2. Posizione Equity in utile
    stock_pos = PositionLot(
        ticker="ENEL.MI",
        shares=1000.0,
        current_price=10.0,
        pmc=7.0, # +3000€ unrealized gain
        asset_class="Equity"
    )

    wallet_with_minus = TaxWalletState(minusvalenze_available_eur=5000.0)
    rebalancer = PrescriptiveConicRebalancer(tax_wallet=wallet_with_minus)

    # Ribilanciamento che forza la vendita di ETF
    res_etf = rebalancer.optimize_rebalance(
        positions=[etf_pos],
        target_weights={"SWDA.MI": 0.20}, # Forza vendita parziale
        available_cash_eur=0.0
    )
    # L'imposta su ETF venduto deve essere calcolata e nessuna minusvalenza assorbita
    assert res_etf["total_tax_due_eur"] > 0.0
    assert res_etf["total_minusvalenze_absorbed_eur"] == 0.0

    # Ribilanciamento che forza la vendita di Azione
    wallet_stock = TaxWalletState(minusvalenze_available_eur=5000.0)
    rebalancer_stock = PrescriptiveConicRebalancer(tax_wallet=wallet_stock)
    res_stock = rebalancer_stock.optimize_rebalance(
        positions=[stock_pos],
        target_weights={"ENEL.MI": 0.20}, # Forza vendita parziale
        available_cash_eur=0.0
    )
    # L'imposta sull'azione deve essere azzerata e le minusvalenze assorbite
    assert res_stock["total_tax_due_eur"] == 0.0
    assert res_stock["total_minusvalenze_absorbed_eur"] > 0.0


# ── 2. TEST QUADRO RM (DIVIDENDI ESTERI SENZA SOSTITUTO) & BLACKLIST IVAFE ──

def test_compute_modello_redditi_pf_quadro_rm():
    """
    Verifica la corretta generazione del Quadro RM (Sezione V - rigo RM12)
    per dividendi azionari esteri percepiti su intermediario non residente (es. IBKR/Degiro).
    """
    positions_data = [
        {"ticker": "MSFT", "asset_class": "Equity", "current_value": 20000.0, "dividends_total": 500.0, "dividend_yield_pct": 2.5},
        {"ticker": "ISP.MI", "asset_class": "Equity", "current_value": 10000.0, "dividends_total": 400.0, "dividend_yield_pct": 4.0}, # Titolo italiano
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}

    modello = compute_modello_redditi_pf(results, tax_year=2025)
    assert "df_quadro_rm" in modello
    df_rm = modello["df_quadro_rm"]
    assert not df_rm.empty

    # Verifica righi RM12
    r_lordo = df_rm[df_rm["rigo"] == "RM12_A"].iloc[0]["valore_eur"]
    r_wht = df_rm[df_rm["rigo"] == "RM12_B"].iloc[0]["valore_eur"]
    r_netto = df_rm[df_rm["rigo"] == "RM12_C"].iloc[0]["valore_eur"]
    r_imposta = df_rm[df_rm["rigo"] == "RM12_E"].iloc[0]["valore_eur"]

    # MSFT genera 500€ lordi, WHT USA 15% (75€), Netto frontiera 425€, Imposta 26% = 110.50€
    # ISP.MI è escluso perché titolo italiano
    assert r_lordo == 500.0
    assert r_wht == 75.0
    assert r_netto == 425.0
    assert round(r_imposta, 2) == round(425.0 * 0.26, 2)
    assert modello["summary"]["imposta_sostitutiva_rm_eur"] == round(425.0 * 0.26, 2)


def test_quadro_rw_blacklist_higher_rate():
    """
    Verifica l'applicazione dell'aliquota IVAFE maggiorata allo 0,40% (4 per mille)
    per attività finanziarie in Paesi Black List (L. 213/2023).
    """
    positions_data = [
        {"ticker": "HOLDING_PANAMA", "asset_class": "Equity", "cost_basis_eur": 50000.0, "current_value": 100000.0},
        {"ticker": "AAPL", "asset_class": "Equity", "cost_basis_eur": 10000.0, "current_value": 20000.0},
    ]
    df_pos = pd.DataFrame(positions_data)
    results = {"positions": df_pos}

    modello = compute_modello_redditi_pf(results, tax_year=2025)
    df_rw = modello["df_quadro_rw"]
    assert not df_rw.empty

    row_panama = df_rw[df_rw["ticker"] == "HOLDING_PANAMA"].iloc[0]
    # IVAFE = 100.000€ * 0.40% = 400.00€
    assert row_panama["ivafe_calcolata_eur"] == 400.0
    assert "BlackList 0.40%" in str(row_panama["codice_paese"])

    row_aapl = df_rw[df_rw["ticker"] == "AAPL"].iloc[0]
    # IVAFE = 20.000€ * 0.20% = 40.00€
    assert row_aapl["ivafe_calcolata_eur"] == 40.0


# ── 3. TEST WEALTH ENGINE QUADRO RW & GIACENZA MEDIA ──

def test_wealth_engine_giacenza_media_and_monitoring_thresholds():
    """
    Verifica le soglie normative del monitoraggio fiscale su conti correnti esteri:
    - Giacenza media > 5.000€ -> IVAFE 34,20€, monitoraggio_solo = 'No'
    - Giacenza media <= 5.000€ ma Picco > 15.000€ -> IVAFE 0€, monitoraggio_solo = 'Sì (Picco > 15k)'
    - Giacenza media <= 5.000€ e Picco <= 15.000€ -> IVAFE 0€, monitoraggio_solo = 'Esonerato (Sotto soglie)'
    """
    from core.wealth.wealth_engine import compute_fiscal_analytics
    from unittest.mock import MagicMock, patch

    mock_accounts = pd.DataFrame([
        {
            "account_id": 1,
            "portfolio_id": 1,
            "name": "Revolut LT High Average",
            "institution": "Revolut",
            "iban": "LT1234567890",
            "balance": 8000.0,
            "giacenza_media": 6500.0,
            "max_balance": 9000.0
        },
        {
            "account_id": 2,
            "portfolio_id": 1,
            "name": "Degiro Cash High Peak Low Avg",
            "institution": "Degiro",
            "iban": "DE9876543210",
            "balance": 3000.0,
            "giacenza_media": 3200.0,
            "max_balance": 18000.0
        },
        {
            "account_id": 3,
            "portfolio_id": 1,
            "name": "Wise Low Balance",
            "institution": "Wise",
            "iban": "BE1122334455",
            "balance": 1200.0,
            "giacenza_media": 1100.0,
            "max_balance": 4000.0
        }
    ])

    fake_engine = MagicMock()
    with patch("core.wealth.wealth_engine.get_wealth_accounts", return_value=mock_accounts), \
         patch("core.wealth.wealth_engine.get_linked_risk_portfolios_summary", return_value=(pd.DataFrame(), pd.DataFrame())), \
         patch("core.wealth.wealth_engine.compute_consolidated_net_worth") as mock_nw:
        
        mock_nw.return_value.financial_investments = 0.0
        res = compute_fiscal_analytics(fake_engine, portfolio_id=1)

        # Solo il conto 1 supera la giacenza media di 5k -> totale IVAFE = 34.20€
        assert res["total_ivafe"] == 34.20

        rw_map = {r["descrizione"]: r for r in res["quadro_rw_rows"]}
        
        # Conto 1: IVAFE dovuta
        c1 = rw_map["Revolut — Revolut LT High Average"]
        assert c1["ivafe_dovuta"] == 34.20
        assert c1["monitoraggio_solo"] == "No"

        # Conto 2: Solo monitoraggio per picco > 15k
        c2 = rw_map["Degiro — Degiro Cash High Peak Low Avg"]
        assert c2["ivafe_dovuta"] == 0.0
        assert "Sì (Picco > 15k)" in c2["monitoraggio_solo"]

        # Conto 3: Esonerato sotto soglia
        c3 = rw_map["Wise — Wise Low Balance"]
        assert c3["ivafe_dovuta"] == 0.0
        assert "Esonerato" in c3["monitoraggio_solo"]
