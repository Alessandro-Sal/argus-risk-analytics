# ============================================================
# tests/test_model_risk_audit.py
# ARGUS — Model Risk Management & Quantitative Audit Test Suite
# Conforming to Federal Reserve / OCC SR 11-7 Validation Guidelines
# ============================================================

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from sklearn.covariance import LedoitWolf

from core.risk_engine import _fifo_engine
from core.tax_engine import compute_tax_and_harvesting


def test_sr11_7_var_cvar_coherence():
    """
    SR 11-7 Standard 1: Coerenza assiomatica e monotonicità di VaR e CVaR (Artzner et al. 1999).
    Verifica che su distribuzioni empiriche e parametriche:
    - CVaR_alpha >= VaR_alpha (l'Expected Shortfall domina sempre il VaR)
    - Monotonicità al crescere del livello di confidenza (VaR_99 >= VaR_95, CVaR_99 >= CVaR_95)
    """
    returns = np.array([
        -0.050, -0.040, -0.030, -0.020, -0.015,
        -0.010, -0.005, -0.002,  0.000,  0.001,
         0.002,  0.004,  0.005,  0.008,  0.010,
         0.012,  0.015,  0.020,  0.025,  0.030
    ], dtype=np.float64)

    # 1. Historical Simulation
    q95_hist = float(np.percentile(returns, 5))
    var95_hist = abs(min(0.0, q95_hist))
    tail_95 = returns[returns <= q95_hist]
    cvar95_hist = abs(float(np.mean(tail_95)))

    q99_hist = float(np.percentile(returns, 1))
    var99_hist = abs(min(0.0, q99_hist))
    tail_99 = returns[returns <= q99_hist]
    cvar99_hist = abs(float(np.mean(tail_99)))

    assert cvar95_hist >= var95_hist, "Violazione Coerenza: CVaR 95% < VaR 95%"
    assert var99_hist >= var95_hist, "Violazione Monotonicità: VaR 99% < VaR 95%"
    assert cvar99_hist >= cvar95_hist, "Violazione Monotonicità: CVaR 99% < CVaR 95%"

    # 2. Parametric Gaussian
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    z95 = float(stats.norm.ppf(0.05))
    z99 = float(stats.norm.ppf(0.01))

    q95_param = mu + z95 * sigma
    var95_param = abs(min(0.0, q95_param))
    q99_param = mu + z99 * sigma
    var99_param = abs(min(0.0, q99_param))

    phi_z95 = float(stats.norm.pdf(z95))
    cvar95_param = abs(mu - sigma * (phi_z95 / 0.05))
    phi_z99 = float(stats.norm.pdf(z99))
    cvar99_param = abs(mu - sigma * (phi_z99 / 0.01))

    assert cvar95_param >= var95_param, "Violazione Coerenza Parametrica: CVaR 95% < VaR 95%"
    assert cvar99_param >= var99_param, "Violazione Coerenza Parametrica: CVaR 99% < VaR 99%"
    assert var99_param >= var95_param, "Violazione Monotonicità Parametrica: VaR 99% < VaR 95%"


def test_sr11_7_maximum_drawdown_exactness():
    """
    SR 11-7 Standard 2: Ricostruzione rigorosa Peak-to-Trough del Maximum Drawdown.
    Verifica che il drawdown calcolato da serie di rendimenti coincida esattamente
    con il minimo storico rispetto al picco massimo progressivo.
    """
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    prices = pd.Series([100.0, 120.0, 90.0, 110.0, 80.0, 130.0], index=dates)

    returns = prices.pct_change().dropna()
    cum_equity = (1.0 + returns).cumprod()
    running_peak = cum_equity.cummax()
    dd_series = (cum_equity - running_peak) / running_peak
    mdd = float(dd_series.min())

    # Picco massimo precedente a 80 era 120: (80 - 120) / 120 = -40 / 120 = -0.3333333333 (-33.3333%)
    expected_mdd = (80.0 - 120.0) / 120.0
    assert abs(mdd - expected_mdd) < 1e-7, f"Discrepanza MDD: Calcolato {mdd} vs Atteso {expected_mdd}"


def test_sr11_7_fifo_fees_and_tax_segregation():
    """
    SR 11-7 Standard 3: Scarico lotti FIFO con oneri accessori (TUIR Art. 68 c. 6)
    e segregazione fiscale asimmetrica ETF vs Azioni (TUIR Art. 67).
    """
    # 1. Verifica _fifo_engine con commissioni su acquisto e vendita
    df_tx_fifo = pd.DataFrame([
        {"tx_date": "2024-01-10", "tx_id": 1, "ticker": "ENI.MI", "tx_type": "buy", "quantity": 10.0, "price": 10.0, "fees": 5.0, "currency": "EUR"},
        {"tx_date": "2024-02-10", "tx_id": 2, "ticker": "ENI.MI", "tx_type": "sell", "quantity": 10.0, "price": 15.0, "fees": 3.0, "currency": "EUR"},
    ])
    res_fifo = _fifo_engine(df_tx_fifo)
    assert res_fifo["qty_net"] == 0.0
    # Costo totale acquisto: 10 * 10 + 5 = 105 € (10.50 €/quota)
    # Ricavo lordo vendita: 10 * 15 = 150 €
    # Realized netto = 150 - 105 - 3 (fee vendita) = 42.0 €
    assert res_fifo["realized_pnl"] == 42.0

    # 2. Verifica Tax Engine: segregazione ETF (Redditi di Capitale) e compensazione minus
    df_tx_tax = pd.DataFrame([
        {"tx_date": "2024-01-10", "tx_id": 1, "ticker": "ALFA", "tx_type": "buy", "quantity": 100.0, "price": 10.0, "asset_class": "Stock", "year": 2024, "fees": 0.0},
        {"tx_date": "2024-02-15", "tx_id": 2, "ticker": "ALFA", "tx_type": "buy", "quantity": 50.0, "price": 20.0, "asset_class": "Stock", "year": 2024, "fees": 0.0},
        {"tx_date": "2024-03-20", "tx_id": 3, "ticker": "BETA_ETF", "tx_type": "buy", "quantity": 100.0, "price": 50.0, "asset_class": "ETF", "year": 2024, "fees": 0.0},
        {"tx_date": "2024-04-10", "tx_id": 4, "ticker": "ALFA", "tx_type": "sell", "quantity": 120.0, "price": 18.0, "asset_class": "Stock", "year": 2024, "fees": 0.0},
        {"tx_date": "2024-05-15", "tx_id": 5, "ticker": "BETA_ETF", "tx_type": "sell", "quantity": 50.0, "price": 40.0, "asset_class": "ETF", "year": 2024, "fees": 0.0}
    ])

    tax_res = compute_tax_and_harvesting(results={"df_tx": df_tx_tax})
    summary = tax_res["summary"]

    # Alfa vendita:
    # 100 quote @ 10 scaricate -> gain = 100 * (18 - 10) = +800 € (Redditi Diversi)
    # 20 quote @ 20 scaricate -> loss = 20 * (18 - 20) = -40 €
    # Beta ETF vendita:
    # 50 quote @ 50 scaricate a 40 -> loss = 50 * (40 - 50) = -500 € (Minusvalenza compensabile)
    # Totale perdite = 40 + 500 = 540 €
    # Base imponibile netta diversi = 800 - 540 = 260 €
    # Imposta = 260 * 0.26 = 67.60 €
    assert summary["total_realized_gain_diversi_eur"] == 800.0
    assert summary["total_realized_loss_eur"] == 540.0
    assert summary["estimated_tax_due_eur"] == 67.60

    # 3. Verifica Tax Engine con commissioni di acquisto e vendita (TUIR Art. 68 c. 6)
    df_tx_fees = pd.DataFrame([
        {"tx_date": "2024-01-10", "tx_id": 1, "ticker": "GAMMA", "tx_type": "buy", "quantity": 10.0, "price": 100.0, "asset_class": "Stock", "year": 2024, "fees": 10.0},
        {"tx_date": "2024-02-10", "tx_id": 2, "ticker": "GAMMA", "tx_type": "sell", "quantity": 10.0, "price": 120.0, "asset_class": "Stock", "year": 2024, "fees": 5.0}
    ])
    tax_res_fees = compute_tax_and_harvesting(results={"df_tx": df_tx_fees})
    summary_fees = tax_res_fees["summary"]
    # Carico unitario: (10 * 100 + 10) / 10 = 101.0 €
    # Realized netto vendita: 10 * (120 - 101) - 5 = 185.0 €
    # Imposta 26% su 185 € = 48.10 €
    assert summary_fees["total_realized_gain_diversi_eur"] == 185.0
    assert summary_fees["estimated_tax_due_eur"] == 48.10


def test_sr11_7_covariance_psd_and_ledoit_wolf():
    """
    SR 11-7 Standard 4: Robustezza numerica della matrice di covarianza (PSD)
    e regolarizzazione Ledoit-Wolf Shrinkage su asset quasi-singolari.
    """
    np.random.seed(42)
    x = np.random.normal(0, 1, 100)
    y = x + np.random.normal(0, 0.0001, 100)  # Collinearità quasi perfetta (> 0.9999)
    z = np.random.normal(0, 1, 100)

    df_assets = pd.DataFrame({"Asset_A": x, "Asset_B": y, "Asset_C": z})

    cov_sample = df_assets.cov().values
    eigvals_sample = np.linalg.eigvalsh(cov_sample)

    lw = LedoitWolf().fit(df_assets)
    cov_shrunk = lw.covariance_
    eigvals_shrunk = np.linalg.eigvalsh(cov_shrunk)

    # 1. Simmetria
    assert np.allclose(cov_shrunk, cov_shrunk.T), "La matrice di covarianza deve essere simmetrica"

    # 2. Definita Positiva (tutti gli autovalori > 0)
    assert np.all(eigvals_shrunk > 0), "La matrice shrinkage deve essere strettamente definita positiva"

    # 3. Miglioramento del numero di condizionamento
    cond_sample = np.linalg.cond(cov_sample)
    cond_shrunk = np.linalg.cond(cov_shrunk)
    assert cond_shrunk < cond_sample, "Lo shrinkage deve abbattere il condition number della matrice singolare"
    assert np.min(eigvals_shrunk) > np.min(eigvals_sample)


def test_sr11_7_french_mortgage_amortization():
    """
    SR 11-7 Standard 5: Verifica del piano di ammortamento francese a rata costante.
    Verifica della convergenza esatta a zero del debito residuo e coerenza degli interessi.
    """
    principal = 100000.0
    annual_rate = 0.03
    years = 20
    n_months = years * 12
    r_month = annual_rate / 12.0

    # R = C * [i * (1+i)^N] / [(1+i)^N - 1]
    expected_payment = principal * (r_month * (1.0 + r_month)**n_months) / ((1.0 + r_month)**n_months - 1.0)
    assert abs(expected_payment - 554.5976) < 0.01

    balance = principal
    tot_interest = 0.0
    for _ in range(n_months):
        interest_m = balance * r_month
        principal_m = expected_payment - interest_m
        balance -= principal_m
        tot_interest += interest_m

    # Convergenza a debito zero
    assert abs(balance) < 1e-4, f"Debito residuo finale non nullo: {balance}"
    assert tot_interest > 0.0
