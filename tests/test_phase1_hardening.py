"""
tests/test_phase1_hardening.py
Automated Verification Suite for ARGUS Phase 1 Hardening:
1. TUIR Art. 44 vs 67: Strict separation of ETF (Redditi di Capitale) and Stock (Redditi Diversi) in Autonomous Rebalancing
2. Performance & Invariants: 2D Vectorized Merton Jump-Diffusion Stochastic Simulation
3. Quantitative Robustness: Ledoit-Wolf Shrinkage & Spectral PSD Projection in Euler VaR Decomposition
"""

import time

import numpy as np
import pandas as pd
import pytest

from core.autonomous_rebalancer import generate_autonomous_rebalancing_proposal
from core.risk_engine import (
    calc_euler_var_decomposition,
    compute_merton_jump_diffusion_simulation,
)

# ==============================================================================
# 1. TUIR FISCAL COMPLIANCE: ART. 44 (ETF) vs ART. 67 (STOCKS / BONDS)
# ==============================================================================

def test_autonomous_rebalancer_etf_cannot_offset_minusvalenze():
    """
    Verifica che le plusvalenze generate dalla vendita di ETF (Redditi di Capitale - Art. 44 TUIR)
    NON assorbano lo zainetto delle minusvalenze pregresse, generando debito d'imposta al 26%.
    """
    df_pos = pd.DataFrame([
        {
            "ticker": "VWCE.MI",
            "asset_class": "ETF",
            "controvalore": 50000.0,
            "prezzo_corrente": 120.0,
            "prezzo_medio_carico": 100.0,  # Plusvalenza latente del 20%
        }
    ])

    # Ribilanciamento che vende metà della posizione in ETF per acquistare XEON.MI
    res = generate_autonomous_rebalancing_proposal(
        df_positions=df_pos,
        target_weights={"VWCE.MI": 0.50, "XEON.MI": 0.50},  # Da 100% a 50% -> SELL ~25,000 EUR
        min_trade_eur=100.0,
        available_minusvalenze_eur=10000.0,  # Zainetto fiscale capiente
    )

    trades = res["trades_list"]
    assert len(trades) >= 1
    sell_trade = next(t for t in trades if t["action"] == "SELL")

    assert sell_trade["ticker"] == "VWCE.MI"
    assert sell_trade["gross_capital_gain_eur"] > 0
    # TUIR Art. 44: Nessun assorbimento di minusvalenze per ETF!
    assert sell_trade["minus_offset_used_eur"] == 0.0
    assert sell_trade["tax_saved_eur"] == 0.0
    assert sell_trade["estimated_tax_impact_eur"] > 0
    assert "REDDITI_CAPITALE" in sell_trade["tax_category"]

    # Lo zainetto fiscale deve rimanere intatto (10,000 EUR)
    assert res["remaining_minusvalenze_eur"] == pytest.approx(10000.0, abs=1e-2)
    assert res["total_tax_saved_by_harvesting_eur"] == 0.0
    assert res["total_etf_gains_eur"] > 0
    assert res["total_diversi_gains_eur"] == 0.0


def test_autonomous_rebalancer_stocks_can_offset_minusvalenze():
    """
    Verifica che le plusvalenze generate dalla vendita di Azioni singole (Redditi Diversi - Art. 67 TUIR)
    assorbano regolarmente lo zainetto delle minusvalenze pregresse, azzerando o riducendo l'imposta.
    """
    df_pos = pd.DataFrame([
        {
            "ticker": "AAPL",
            "asset_class": "Equity",
            "controvalore": 50000.0,
            "prezzo_corrente": 200.0,
            "prezzo_medio_carico": 150.0,  # Plusvalenza latente di 50$ per quota
        }
    ])

    # Ribilanciamento che dimezza la quota in AAPL a favore di MSFT
    res = generate_autonomous_rebalancing_proposal(
        df_positions=df_pos,
        target_weights={"AAPL": 0.50, "MSFT": 0.50},  # SELL 25,000 EUR
        min_trade_eur=100.0,
        available_minusvalenze_eur=10000.0,
    )

    trades = res["trades_list"]
    assert len(trades) >= 1
    sell_trade = next(t for t in trades if t["action"] == "SELL")

    assert sell_trade["ticker"] == "AAPL"
    assert sell_trade["gross_capital_gain_eur"] > 0
    # TUIR Art. 67: Azione singola compensa con lo zainetto fiscale!
    assert sell_trade["minus_offset_used_eur"] > 0.0
    assert sell_trade["tax_saved_eur"] > 0.0
    assert "REDDITI_DIVERSI" in sell_trade["tax_category"]

    # Lo zainetto fiscale deve essere diminuito esattamente dell'offset utilizzato
    expected_rem = 10000.0 - sell_trade["minus_offset_used_eur"]
    assert res["remaining_minusvalenze_eur"] == pytest.approx(expected_rem, abs=1e-2)
    assert res["total_tax_saved_by_harvesting_eur"] > 0
    assert res["total_diversi_gains_eur"] > 0


# ==============================================================================
# 2. VECTORIZED MERTON JUMP-DIFFUSION SIMULATION
# ==============================================================================

def test_merton_jump_diffusion_vectorized_invariants():
    """
    Verifica correttezza statistica e invarianti della simulazione vettorizzata di Merton:
    - Conservazione delle dimensioni di output
    - Monotonia dei percentili: p5 <= p25 <= p50 <= p75 <= p95
    - Coerenza del Tail Risk: CVaR_99 >= VaR_99 > 0
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=120, freq="B")
    sr_portfolio = pd.Series(np.random.normal(0.0006, 0.012, 120), index=dates)

    t0 = time.perf_counter()
    res = compute_merton_jump_diffusion_simulation(
        sr_portfolio=sr_portfolio,
        n_sims=1000,
        time_horizon_days=63,
        lambda_j=1.8,
        mu_j=-0.07,
        sigma_j=0.03,
        initial_value=1000.0
    )
    elapsed = time.perf_counter() - t0

    # Deve completarsi in meno di 1 secondo per 1000 simulazioni vettorizzate
    assert elapsed < 1.0, f"Simulazione troppo lenta: {elapsed:.3f}s"

    assert len(res["days"]) == 64
    assert len(res["p50"]) == 64
    assert res["p50"][0] == pytest.approx(1000.0, abs=1e-3)

    # Monotonia dei percentili lungo la traiettoria
    p5 = np.array(res["p5"])
    p25 = np.array(res["p25"])
    p50 = np.array(res["p50"])
    p75 = np.array(res["p75"])
    p95 = np.array(res["p95"])

    assert np.all(p5 <= p25 + 1e-6)
    assert np.all(p25 <= p50 + 1e-6)
    assert np.all(p50 <= p75 + 1e-6)
    assert np.all(p75 <= p95 + 1e-6)

    # Tail risk checks
    assert res["var_99_jump_pct"] > 0
    assert res["cvar_99_jump_pct"] >= res["var_99_jump_pct"]
    assert res["mean_jumps_per_year"] >= 0


# ==============================================================================
# 3. EULER VAR DECOMPOSITION & LEDOIT-WOLF SHRINKAGE
# ==============================================================================

def test_calc_euler_var_decomposition_singular_matrix_resilience():
    """
    Verifica che calc_euler_var_decomposition gestisca correttamente matrici
    con asset perfettamente colineari (determinante nullo) grazie allo shrinkage
    di Ledoit-Wolf e alla proiezione spettrale PSD, rispettando la legge di Eulero.
    """
    np.random.seed(99)
    dates = pd.date_range("2024-01-01", periods=40, freq="B")
    base_ret = np.random.normal(0.001, 0.015, 40)

    # Due asset colineari (es. due classi dello stesso fondo) e uno indipendente
    df_returns = pd.DataFrame({
        "ASSET_A": base_ret,
        "ASSET_B": base_ret,  # Perfetta colinearità (correlazione 1.0)
        "ASSET_C": np.random.normal(0.0005, 0.010, 40),
    }, index=dates)

    df_pos = pd.DataFrame([
        {"ticker": "ASSET_A", "current_value": 40000.0, "weight_pct": 40.0},
        {"ticker": "ASSET_B", "current_value": 30000.0, "weight_pct": 30.0},
        {"ticker": "ASSET_C", "current_value": 30000.0, "weight_pct": 30.0},
    ])

    decomp = calc_euler_var_decomposition(
        df_positions=df_pos,
        df_returns=df_returns,
        confidence_level=0.95,
        total_portfolio_value=100000.0,
        time_horizon=1
    )

    assert decomp["portfolio_var_pct"] > 0.0
    assert decomp["portfolio_var_amount"] > 0.0
    assert decomp["euler_check_passed"] is True

    # Verifica teorema di Eulero: somma dei component VaR == VaR Totale di portafoglio
    df_res = decomp["decomposition_df"]
    assert not df_res.empty
    assert len(df_res) == 3

    sum_component_var = float(df_res["component_var_amount"].sum())
    total_var = float(decomp["portfolio_var_amount"])
    assert sum_component_var == pytest.approx(total_var, rel=1e-3, abs=0.1)
