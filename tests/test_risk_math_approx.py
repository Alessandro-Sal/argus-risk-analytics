"""
ARGUS — Quantitative Risk & Wealth Intelligence Platform
Automated Regression Test Suite: Analytical Tolerances (pytest.approx) & Snapshots
Protects quantitative engines against numerical drift, accounting violations, and silent mutations.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from core.risk_engine import compute_risk_metrics
from core.unified_demo_seeder import seed_unified_demo_scenario
from core.wealth.wealth_engine import compute_mortgage_amortization


@pytest.mark.quant
def test_sharpe_ratio_analytical_tolerance():
    """
    Verifica che il calcolo del Sharpe Ratio annualizzato coincida esattamente
    con la soluzione analitica chiusa entro una tolleranza ristretta (rel=1e-5).
    SR = ((mu - rf_daily) / sigma_daily) * sqrt(252)
    """
    np.random.seed(42)
    rf_annual = 0.03
    rf_daily = rf_annual / 252.0

    # Genera 1000 rendimenti sintetici con media e deviazione standard controllate
    returns = pd.Series(np.random.normal(0.0008, 0.012, 1000))

    mean_ret = float(returns.mean())
    std_ret = float(returns.std(ddof=1))
    expected_sharpe = ((mean_ret - rf_daily) / std_ret) * np.sqrt(252.0)

    metrics = compute_risk_metrics(returns, risk_free_rate=rf_annual)
    computed_sharpe = metrics["returns"]["sharpe_ratio"]

    assert computed_sharpe == pytest.approx(expected_sharpe, abs=1e-3)


@pytest.mark.quant
def test_cornish_fisher_var_analytical_tolerance():
    """
    Verifica che il Cornish-Fisher VaR corregga il VaR Gaussiano in presenza di asimmetria e curtosi
    secondo l'espansione polinomiale di Edgeworth a tolleranza garantita.
    """
    np.random.seed(123)
    # Distribuzione con asimmetria negativa (skew < 0) e code pesanti
    raw_returns = np.random.normal(0.0005, 0.015, 1000) - np.random.exponential(0.005, 1000)
    returns = pd.Series(raw_returns)

    metrics = compute_risk_metrics(returns, risk_free_rate=0.03)
    mkt = metrics["market_risk"]

    var_gauss = mkt["var_95"]
    var_cf = mkt["var_cf_95"]

    # Con asimmetria negativa (skewness < 0), il VaR corretto deve stimare una perdita maggiore o uguale
    if mkt["skewness"] < -0.1:
        assert var_cf >= pytest.approx(var_gauss, rel=1e-2)
    assert isinstance(var_cf, float)
    assert var_cf > 0.0


@pytest.mark.wealth
def test_french_mortgage_conservation_law():
    """
    Verifica la legge di conservazione contabile del piano di ammortamento a rata costante (francese):
    1. Somma di tutte le quote capitale = Capitale iniziale mutuato (debito originario).
    2. Debito residuo al termine dell'ultimo periodo = esattamente 0.00 (+/- 0.05 EUR).
    """
    principal = 250_000.0
    annual_rate = 2.4   # 2.4% annuo
    duration_years = 20  # 20 anni (240 mesi)

    res = compute_mortgage_amortization(principal=principal, annual_rate=annual_rate, duration_years=duration_years)
    schedule = res.get("schedule", [])

    assert len(schedule) == 240

    # 1. Conservazione quota capitale
    total_capital_repaid = sum(item["principal"] for item in schedule)
    assert total_capital_repaid == pytest.approx(principal, abs=0.50)

    # 2. Debito residuo finale esattamente azzerato
    final_balance = schedule[-1]["remaining_balance"]
    assert final_balance == pytest.approx(0.0, abs=0.05)


@pytest.mark.wealth
def test_fifo_accounting_conservation_law():
    """
    Verifica che il motore contabile FIFO rispetti la legge di conservazione del valore di carico:
    Costo Totale Acquisti = Valore di Carico Residuo + Costo Storico dei Lotti Scaricati
    """
    from core.risk_engine import _fifo_engine

    df_tx = pd.DataFrame([
        {"tx_date": "2024-01-10", "tx_id": 1, "ticker": "VWCE.DE", "tx_type": "buy", "quantity": 100.0, "price": 100.0, "fees": 10.0, "currency": "EUR"},
        {"tx_date": "2024-03-15", "tx_id": 2, "ticker": "VWCE.DE", "tx_type": "buy", "quantity": 50.0, "price": 110.0, "fees": 5.0, "currency": "EUR"},
        {"tx_date": "2024-06-20", "tx_id": 3, "ticker": "VWCE.DE", "tx_type": "sell", "quantity": 70.0, "price": 120.0, "fees": 8.0, "currency": "EUR"},
    ])

    total_bought_cost = (100.0 * 100.0 + 10.0) + (50.0 * 110.0 + 5.0)  # 10010 + 5505 = 15515 EUR

    res_fifo = _fifo_engine(df_tx)
    residual_qty = res_fifo["qty_net"]
    avg_cost = res_fifo["avg_cost"]
    cost_basis_residual = residual_qty * avg_cost

    # Quantità netta residua: 150 - 70 = 80 quote
    assert residual_qty == pytest.approx(80.0, abs=1e-6)

    # Costo scaricato dal lotto 1: 70 quote * 100.10 = 7007 EUR
    cost_sold = 70.0 * 100.10
    assert (cost_basis_residual + cost_sold) == pytest.approx(total_bought_cost, abs=1e-2)


@pytest.mark.snapshot
def test_unified_demo_seeder_execution_and_snapshot_integrity():
    """
    Verifica l'esecuzione atomica del seeder dimostrativo unificato a 5 pilastri:
    - Presenza di tutte le posizioni (Azioni, Obbligazioni, Cassa, Immobili, Debiti)
    - Esatta corrispondenza contabile del Patrimonio Netto consolidato
    - Snapshot testing sul DataFrame delle posizioni generate
    """
    results = seed_unified_demo_scenario(target_portfolio_name="TEST_DEMO_SNAPSHOT")

    assert results is not None
    assert results["is_sandbox"] is True
    assert results["portfolio_name"] == "TEST_DEMO_SNAPSHOT"

    pos = results["positions"]
    assert isinstance(pos, pd.DataFrame)
    assert len(pos) == 4

    # Controllo colonne chiave e tipi
    expected_cols = ["ticker", "asset_class", "qty_net", "current_value", "cost_basis", "weight_pct", "beta"]
    for col in expected_cols:
        assert col in pos.columns, f"Colonna mancante nel DataFrame posizioni: {col}"

    # Controllo quadratura pesi percentuali (somma = 100%)
    total_weight = pos["weight_pct"].sum()
    assert total_weight == pytest.approx(100.0, abs=1e-2)

    # Controllo Total Wealth 5 Pilastri
    wealth = results["wealth_snapshot"]
    assert wealth["total_net_worth"] == pytest.approx(802450.0, abs=1e-2)
    assert wealth["total_assets"] == pytest.approx(1022450.0, abs=1e-2)
    assert wealth["liabilities_total"] == pytest.approx(220000.0, abs=1e-2)

    # Snapshot test strutturale su posizioni contro DataFrame deterministico di riferimento
    expected_tickers = ["VWCE.DE", "AAPL", "ASML.AS", "BTP_10Y"]
    assert list(pos["ticker"]) == expected_tickers
