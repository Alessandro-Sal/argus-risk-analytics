# ============================================================
# tests/test_fase3_screener_almgren_factors.py
# ARGUS | Risk Analytics Platform
# Unit Tests for Fase 3: EQS Formula Engine, Almgren-Chriss Impact & Factor Quintiles
# ============================================================

import pytest
import numpy as np
import pandas as pd

from core.screener_engine import (
    evaluate_custom_screener_query,
    SCREENER_FIELD_ALIASES,
    SCREENER_FORMULA_PRESETS
)
from core.risk_engine import (
    compute_almgren_chriss_optimal_execution,
    compute_almgren_chriss_market_impact
)
from core.factor_library import (
    run_factor_quintile_backtest,
    FACTOR_PRESET_DEFINITIONS
)


# ── TEST 1: EQS FORMULA SCREENER ENGINE ───────────────────────
def test_screener_formula_engine_evaluation():
    # Creazione DataFrame di test con 5 titoli
    data = {
        "ticker": ["AAPL", "MSFT", "GOOGL", "AMZN", "JNJ"],
        "piotroski_score": [8, 7, 5, 6, 8],
        "altman_z_score": [3.5, 4.2, 2.1, 1.9, 3.8],
        "roe_pct": [25.0, 30.0, 14.0, 18.0, 22.0],
        "debt_to_equity": [0.5, 0.4, 0.9, 1.2, 0.6],
        "trailing_pe": [28.0, 32.0, 20.0, 45.0, 16.0],
        "dividend_yield_pct": [0.6, 0.8, 0.0, 0.0, 3.2],
        "beta": [1.1, 0.95, 1.05, 1.25, 0.65],
        "volatility_ann_pct": [22.0, 20.0, 26.0, 32.0, 15.0],
        "sharpe_ratio": [1.1, 1.3, 0.6, 0.5, 0.9],
        "rsi_14": [55.0, 60.0, 42.0, 68.0, 35.0],
        "upside_pct": [12.0, 15.0, 25.0, 8.0, 6.0],
        "argus_score": [82.0, 88.0, 65.0, 68.0, 78.0]
    }
    df = pd.DataFrame(data)

    # Test 1.1: Query complessa con operatori logici AND e alias case-insensitive
    query_1 = "Piotroski >= 7 AND Altman > 2.9 AND ROE > 15 AND DebtToEquity < 0.8"
    df_res1, is_valid1, msg1 = evaluate_custom_screener_query(df, query_1)
    assert is_valid1 is True
    assert len(df_res1) == 3 # AAPL, MSFT, JNJ
    assert set(df_res1["ticker"]) == {"AAPL", "MSFT", "JNJ"}

    # Test 1.2: Query con OR, parentesi e operatori relazionali
    query_2 = "(PE < 25 OR DivYield > 2.0) AND Beta < 1.0"
    df_res2, is_valid2, msg2 = evaluate_custom_screener_query(df, query_2)
    assert is_valid2 is True
    assert "JNJ" in df_res2["ticker"].values

    # Test 1.3: Query vuota restituisce tutti i titoli
    df_res3, is_valid3, _ = evaluate_custom_screener_query(df, "")
    assert is_valid3 is True
    assert len(df_res3) == 5

    # Test 1.4: Query con errore di sintassi gestita senza crash
    query_err = "Piotroski >= >= 7 AND"
    df_res_err, is_valid_err, msg_err = evaluate_custom_screener_query(df, query_err)
    assert is_valid_err is False
    assert "Errore" in msg_err
    assert len(df_res_err) == 5 # Fallback sicuro


def test_screener_formula_presets_validity():
    # Verifica che tutti i preset istituzionali siano sintatticamente validi
    dummy_df = pd.DataFrame({
        "ticker": ["DUMMY"],
        "piotroski_score": [7],
        "altman_z_score": [3.0],
        "roe_pct": [16.0],
        "debt_to_equity": [0.7],
        "peg_ratio": [1.1],
        "upside_pct": [18.0],
        "trailing_pe": [15.0],
        "price_to_book": [1.8],
        "dividend_yield_pct": [3.2],
        "beta": [0.8],
        "volatility_ann_pct": [18.0],
        "sharpe_ratio": [0.8],
        "rsi_14": [55.0],
        "perf_1y_pct": [20.0],
        "price_to_sma200_pct": [5.0],
        "argus_score": [75.0]
    })
    
    for pkey, pdata in SCREENER_FORMULA_PRESETS.items():
        formula = pdata["formula"]
        df_f, is_valid, msg = evaluate_custom_screener_query(dummy_df, formula)
        assert is_valid is True, f"Preset '{pkey}' formula '{formula}' non è valida: {msg}"


# ── TEST 2: ALMGREN-CHRISS OPTIMAL EXECUTION ───────────────────
def test_almgren_chriss_optimal_execution_math():
    order_val = 500_000.0
    adv = 5_000_000.0
    vol_ann = 25.0
    horizon = 5.0
    intervals = 10
    
    res = compute_almgren_chriss_optimal_execution(
        order_value=order_val,
        adv_value=adv,
        volatility_ann_pct=vol_ann,
        horizon_days=horizon,
        n_intervals=intervals,
        risk_aversion_lambda=1e-6,
        bid_ask_spread_bps=10.0
    )
    
    assert res["order_value"] == order_val
    assert res["expected_cost_amount"] > 0
    assert res["expected_cost_bps"] > 0
    assert res["execution_std_amount"] > 0
    assert res["execution_var_95_amount"] > res["expected_cost_amount"]
    assert res["half_life_days"] > 0
    
    # Verifica schedule
    sched = res["schedule_df"]
    assert len(sched) == intervals
    # Posizione finale deve essere 0.0
    assert sched.iloc[-1]["Posizione Residua (€)"] == 0.0
    assert sched.iloc[-1]["% Liquidata"] == 100.0
    
    # Traiettoria deve essere strettamente decrescente
    pos_residua = sched["Posizione Residua (€)"].values
    assert all(pos_residua[i] >= pos_residua[i+1] for i in range(len(pos_residua)-1))
    
    # Verifica scomposizione costi
    bd = res["cost_breakdown"]
    total_calc = bd["temporary_impact_amount"] + bd["permanent_impact_amount"] + bd["spread_cost_amount"]
    assert np.isclose(res["expected_cost_amount"], total_calc, rtol=1e-4)


def test_almgren_chriss_risk_aversion_monotonicity():
    # Un'avversione al rischio maggiore deve ridurre la varianza a fronte di un costo atteso maggiore
    res_neutral = compute_almgren_chriss_optimal_execution(
        order_value=200_000.0,
        risk_aversion_lambda=0.0
    )
    res_averse = compute_almgren_chriss_optimal_execution(
        order_value=200_000.0,
        risk_aversion_lambda=1e-5
    )
    
    # Lambda alto -> esecuzione più rapida all'inizio -> minore incertezza di prezzo V[x]
    assert res_averse["execution_std_amount"] <= res_neutral["execution_std_amount"]
    # Lambda alto -> velocità iniziale più alta -> maggiore impatto temporaneo
    assert res_averse["expected_cost_amount"] >= res_neutral["expected_cost_amount"]


# ── TEST 3: FACTOR QUINTILES BACKTESTING ────────────────────────
def test_factor_quintiles_backtest_execution():
    # Generazione dataset di 15 asset su 252 giorni
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="B")
    np.random.seed(42)
    data = np.random.normal(0.0005, 0.015, (len(dates), 15))
    df_rets = pd.DataFrame(data, index=dates, columns=[f"STOCK_{i+1:02d}" for i in range(15)])
    
    res = run_factor_quintile_backtest(
        df_returns=df_rets,
        factor_type="qmj",
        rebalance_freq="M",
        lookback_window=63
    )
    
    assert res["valid"] is True
    assert res["factor_key"] == "qmj"
    assert "cumulative_df" in res
    assert "metrics_df" in res
    
    # Verifica che metrics_df contenga tutti i 5 quintili e lo spread
    m_df = res["metrics_df"]
    assert len(m_df) == 7 # Q1..Q5 + Long_Short_Spread + Equal_Weight_Univ
    
    # Monotonicity score compreso tra -1 e 1
    assert -1.0 <= res["monotonicity_score"] <= 1.0
    
    # Curve cumulative
    cum_df = res["cumulative_df"]
    assert "Q1" in cum_df.columns
    assert "Q5" in cum_df.columns
    assert "Long_Short_Spread" in cum_df.columns
    assert len(cum_df) > 0


def test_factor_quintiles_all_preset_types():
    dates = pd.date_range("2023-01-01", "2024-06-30", freq="B")
    np.random.seed(42)
    data = np.random.normal(0.0004, 0.012, (len(dates), 10))
    df_rets = pd.DataFrame(data, index=dates, columns=[f"TK_{i}" for i in range(10)])
    
    for ftype in ["qmj", "low_beta", "profitability", "momentum", "value"]:
        res = run_factor_quintile_backtest(df_returns=df_rets, factor_type=ftype, rebalance_freq="M")
        assert res["valid"] is True, f"Backtest per fattore '{ftype}' non valido: {res.get('message')}"
        assert res["factor_key"] == ftype
