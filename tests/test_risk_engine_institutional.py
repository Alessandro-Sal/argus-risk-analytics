# ============================================================
# tests/test_risk_engine_institutional.py
# ARGUS Risk Analytics — Institutional Risk Engine Test Suite
# ============================================================

from datetime import datetime
import numpy as np
import pandas as pd
import pytest

from core.yield_curve import get_active_risk_free_rate, HISTORICAL_ANNUAL_RISK_FREE_RATES
from core.risk_engine import (
    compute_evt_pot_var_cvar,
    compute_basel_traffic_light_backtest,
    compute_maximum_diversification_portfolio,
    compute_cvar_portfolio_optimization,
    compute_fx_risk_decomposition,
)
from core.macro_stress_engine import compute_consolidated_wealth_stress_test


# ──────────────────────────────────────────────────────────
# 1. POINT-IN-TIME HISTORICAL RISK-FREE RATES
# ──────────────────────────────────────────────────────────

def test_historical_point_in_time_risk_free_rates():
    """Verifica la risoluzione Point-in-Time dei tassi privi di rischio (2020-2026)."""
    # 2020 EUR rate was negative (-0.50%)
    rf_eur_2020 = get_active_risk_free_rate("EUR", as_of_date=datetime(2020, 5, 1))["rate"]
    assert rf_eur_2020 < 0.0
    assert rf_eur_2020 == pytest.approx(-0.0050, abs=1e-4)

    # 2023 USD rate was high (+5.25%)
    rf_usd_2023 = get_active_risk_free_rate("USD", as_of_date=datetime(2023, 7, 15))["rate"]
    assert rf_usd_2023 > 0.04
    assert rf_usd_2023 == pytest.approx(0.0525, abs=1e-4)

    # 2024 GBP rate was +5.00%
    rf_gbp_2024 = get_active_risk_free_rate("GBP", as_of_date=datetime(2024, 1, 10))["rate"]
    assert rf_gbp_2024 == pytest.approx(0.0500, abs=1e-4)

    # 2026 EUR rate is projected at +2.75%
    rf_eur_2026 = get_active_risk_free_rate("EUR", as_of_date=datetime(2026, 3, 1))["rate"]
    assert rf_eur_2026 == pytest.approx(0.0275, abs=1e-4)

    # Fallback to current rate when as_of_date is None
    rf_curr = get_active_risk_free_rate("EUR", as_of_date=None)["rate"]
    assert isinstance(rf_curr, float)


# ──────────────────────────────────────────────────────────
# 2. EXTREME VALUE THEORY (EVT POT-GPD)
# ──────────────────────────────────────────────────────────

def test_evt_pot_var_cvar_fat_tails_monotonicity():
    """Verifica che EVT POT-GPD modelli correttamente le code pesanti e rispetti l'ordinamento monotono."""
    np.random.seed(42)
    # Genera rendimenti con coda pesante (Student-t con 4 gradi di libertà)
    raw_rets = np.random.standard_t(df=4, size=1000) * 0.015
    rets_series = pd.Series(raw_rets)

    evt_res = compute_evt_pot_var_cvar(rets_series, threshold_quantile=0.90)

    var_99 = evt_res["evt_var_99_pct"]
    cvar_99 = evt_res["evt_cvar_99_pct"]
    var_999 = evt_res["evt_var_999_pct"]
    cvar_999 = evt_res["evt_cvar_999_pct"]

    # Tutte le misure devono essere positive (espresse in % di perdita)
    assert var_99 > 0.0
    assert cvar_99 > 0.0
    assert var_999 > 0.0
    assert cvar_999 > 0.0

    # Monotonicità: CVaR >= VaR allo stesso livello di confidenza
    assert cvar_99 >= var_99 - 1e-4
    assert cvar_999 >= var_999 - 1e-4

    # Monotonicità estrema: 99.9% VaR >= 99.0% VaR
    assert var_999 >= var_99 - 1e-4
    assert cvar_999 >= cvar_99 - 1e-4

    # Parametri GPD stimati
    assert "tail_index_xi" in evt_res
    assert isinstance(evt_res["tail_index_xi"], float)
    assert evt_res["n_excesses"] > 10


def test_evt_pot_fallback_small_sample():
    """Verifica il fallback grazioso con campioni troppo piccoli."""
    short_rets = pd.Series([0.01, -0.01, 0.02, -0.02])
    res = compute_evt_pot_var_cvar(short_rets)
    assert res["evt_var_99_pct"] >= 0.0
    assert res["n_excesses"] == 0


# ──────────────────────────────────────────────────────────
# 3. BASEL IV REGULATORY TRAFFIC LIGHT BACKTEST
# ──────────────────────────────────────────────────────────

def test_basel_traffic_light_backtest_green_zone():
    """Verifica backtest con poche eccezioni -> Zona Verde e moltiplicatore 3.00."""
    np.random.seed(123)
    n = 250
    # Rendimenti normali standard
    rets = pd.Series(np.random.normal(0.0, 0.01, size=n))
    # VaR al 99% molto prudente (superato solo 2 volte)
    var_series = pd.Series(0.028, index=rets.index)

    bt = compute_basel_traffic_light_backtest(rets, var_series)

    assert bt["zone"] == "Verde"
    assert bt["basel_multiplier"] == 3.00
    assert bt["exceptions_count"] <= 4
    # Nel test di Kupiec il p-value deve essere non significativo (accetta H0)
    assert bt["kupiec_p_value"] > 0.05
    assert 0.0 <= bt["christoffersen_p_value"] <= 1.0
    assert 0.0 <= bt["conditional_coverage_p_value"] <= 1.0


def test_basel_traffic_light_backtest_red_zone():
    """Verifica backtest con molte eccezioni -> Zona Rossa e moltiplicatore 4.00."""
    n = 250
    # VaR troppo basso: molte violazioni
    rets = pd.Series(-0.02, index=range(n))
    var_val = 0.01

    bt = compute_basel_traffic_light_backtest(rets, var_val)

    assert bt["zone"] == "Rossa"
    assert bt["basel_multiplier"] == 4.00
    assert bt["exceptions_count"] >= 10
    # Kupiec rifiuta nettamente
    assert bt["kupiec_p_value"] < 0.01


# ──────────────────────────────────────────────────────────
# 4. MAXIMUM DIVERSIFICATION PORTFOLIO (MDP)
# ──────────────────────────────────────────────────────────

def test_maximum_diversification_portfolio():
    """Verifica l'ottimizzatore MDP di Choueifaty (Diversification Ratio)."""
    # Matrice di covarianza per 4 asset: 2 correlati, 2 decorrelati
    vol = np.array([0.15, 0.20, 0.10, 0.25])
    corr = np.array([
        [1.00, 0.80, 0.10, -0.10],
        [0.80, 1.00, 0.15, -0.05],
        [0.10, 0.15, 1.00,  0.05],
        [-0.10, -0.05, 0.05, 1.00],
    ])
    cov_matrix = np.outer(vol, vol) * corr

    res = compute_maximum_diversification_portfolio(cov_matrix)
    weights = np.array(res["weights_list"])
    dr = res["diversification_ratio"]

    # I pesi devono sommare a 1.0
    assert np.sum(weights) == pytest.approx(1.0, abs=1e-3)
    # Long-only: tutti i pesi >= 0
    assert np.all(weights >= -1e-5)

    # Il Diversification Ratio deve essere >= 1.0
    assert dr >= 1.0

    # DR dell'MDP deve essere maggiore o uguale a quello di un equal-weight
    w_eq = np.array([0.25, 0.25, 0.25, 0.25])
    vol_eq = np.sqrt(w_eq @ cov_matrix @ w_eq)
    weighted_vol_eq = np.sum(w_eq * np.sqrt(np.diag(cov_matrix)))
    dr_eq = weighted_vol_eq / max(vol_eq, 1e-8)

    assert dr >= dr_eq - 1e-4


# ──────────────────────────────────────────────────────────
# 5. MIN-CVAR LINEAR PROGRAMMING (ROCKAFELLAR-URYASEV)
# ──────────────────────────────────────────────────────────

def test_min_cvar_portfolio_optimization():
    """Verifica l'ottimizzazione Min-CVaR esatta tramite Linear Programming HiGHS."""
    np.random.seed(99)
    # 250 giorni, 3 asset: A rischioso e con fat-tail, B difensivo, C decorrelato
    ret_a = np.random.standard_t(df=3, size=250) * 0.025
    ret_b = np.random.normal(0.0002, 0.005, size=250)
    ret_c = np.random.normal(0.0003, 0.008, size=250)

    df_rets = pd.DataFrame({"AssetA": ret_a, "AssetB": ret_b, "AssetC": ret_c})

    res = compute_cvar_portfolio_optimization(df_rets, confidence=0.95)
    w_opt = np.array(res["weights_list"])
    opt_cvar_pct = res["cvar_daily_pct"]

    # I pesi devono sommare a 1.0
    assert np.sum(w_opt) == pytest.approx(1.0, abs=1e-3)
    # Long-only
    assert np.all(w_opt >= -1e-5)

    # CVaR del portafoglio ottimizzato deve essere minore o uguale a quello di un portafoglio equal-weight
    w_eq = np.array([1/3, 1/3, 1/3])
    port_eq = df_rets.values @ w_eq
    losses_eq = -port_eq
    var_95_eq = np.percentile(losses_eq, 95)
    cvar_95_eq_pct = np.mean(losses_eq[losses_eq >= var_95_eq]) * 100.0

    assert opt_cvar_pct <= cvar_95_eq_pct + 0.05
    # L'asset difensivo B deve avere un'allocazione significativa
    assert w_opt[1] > 0.10


# ──────────────────────────────────────────────────────────
# 6. FX RISK DECOMPOSITION
# ──────────────────────────────────────────────────────────

def test_fx_risk_decomposition():
    """Verifica la scomposizione della varianza del rischio di cambio (Local vs FX vs Interazione)."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    
    # Prezzi sintetici per AAPL (USD), XEON.DE (EUR) e USDEUR=X
    p_aapl = 150.0 * np.cumprod(1.0 + np.random.normal(0.0005, 0.015, size=100))
    p_xeon = 100.0 * np.cumprod(1.0 + np.random.normal(0.0001, 0.001, size=100))
    p_fx = 0.92 * np.cumprod(1.0 + np.random.normal(0.0000, 0.005, size=100))

    df_prices = pd.concat([
        pd.DataFrame({"price_date": dates, "ticker": "AAPL", "close": p_aapl}),
        pd.DataFrame({"price_date": dates, "ticker": "XEON.DE", "close": p_xeon}),
        pd.DataFrame({"price_date": dates, "ticker": "USDEUR=X", "close": p_fx}),
    ], ignore_index=True)

    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "asset_currency": "USD", "current_value": 60_000.0, "qty_net": 400},
        {"ticker": "XEON.DE", "asset_currency": "EUR", "current_value": 40_000.0, "qty_net": 400},
    ])

    fx_decomp = compute_fx_risk_decomposition(
        df_positions,
        df_prices,
        base_currency="EUR",
    )

    assert fx_decomp["base_currency"] == "EUR"
    assert fx_decomp["foreign_currency_exposure_eur"] == pytest.approx(60_000.0, abs=1.0)
    assert fx_decomp["foreign_currency_share_pct"] == pytest.approx(60.0, abs=0.5)
    assert "hedging_simulation" in fx_decomp
    assert len(fx_decomp["assets_breakdown"]) >= 1

    item = fx_decomp["assets_breakdown"][0]
    assert item["ticker"] == "AAPL"
    assert item["currency"] == "USD"
    # Le quote percentuali di varianza devono sommare al 100%
    tot_var_pct = item["variance_share_local_pct"] + item["variance_share_fx_pct"] + item["variance_share_interaction_pct"]
    assert tot_var_pct == pytest.approx(100.0, abs=1.0)


# ──────────────────────────────────────────────────────────
# 7. CONSOLIDATED TOTAL WEALTH STRESS TESTING
# ──────────────────────────────────────────────────────────

def test_consolidated_wealth_stress_test_calculation():
    """Verifica lo stress test su patrimonio totale consolidato (Attivo vs Passivo vs Net Worth)."""
    pbs_mock = {
        "liquid_assets": 50_000.0,
        "financial_investments": 200_000.0,
        "real_estate": 400_000.0,
        "pension_funds": 80_000.0,
        "luxury_goods": 30_000.0,
        "private_equity_other": 0.0,
        "liabilities": 150_000.0,  # Mutuo residuo
    }

    res = compute_consolidated_wealth_stress_test(pbs_mock)

    assert res["initial_total_assets_eur"] == 760_000.0
    assert res["initial_liabilities_eur"] == 150_000.0
    assert res["initial_net_worth_eur"] == 610_000.0
    assert res["initial_debt_to_assets_pct"] == pytest.approx(150_000 / 760_000 * 100, abs=0.1)

    # Scenari devono includere EBA, Fed CCAR, Stagflazione, Geopolitico
    scens = res["scenarios_results"]
    assert len(scens) == 4

    for sc in scens:
        # Il debito nominale deve rimanere invariato
        assert sc["post_shock_liabilities_eur"] == 150_000.0
        # Gli asset devono diminuire (shock negativi)
        assert sc["post_shock_assets_eur"] < 760_000.0
        # Il Net Worth post-shock deve essere Attivo - Passivo
        assert sc["post_shock_net_worth_eur"] == pytest.approx(
            sc["post_shock_assets_eur"] - sc["post_shock_liabilities_eur"], abs=0.01
        )
        # La variazione deve essere negativa
        assert sc["net_worth_delta_eur"] < 0.0
        assert sc["net_worth_drawdown_pct"] < 0.0
        # Il Debt-to-Assets deve salire (effetto leva)
        assert sc["post_shock_debt_to_assets_pct"] > res["initial_debt_to_assets_pct"]

    # Peggior scenario (CCAR o EBA)
    assert res["worst_net_worth_drawdown_pct"] < 0.0
    assert res["worst_net_worth_loss_eur"] < 0.0
