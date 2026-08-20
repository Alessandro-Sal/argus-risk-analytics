"""
Unit tests for Volatility Surface, Implied Volatility Solver & Skew/Smile Calibration.
"""

import numpy as np
import pandas as pd

from core.options_hedging import (
    black_scholes_pricing,
    compute_covered_call_yield_enhancement,
    compute_portfolio_delta_hedge,
)
from core.volatility_surface import (
    build_volatility_surface,
    fit_volatility_smile,
    implied_volatility_solver,
)


def test_implied_volatility_solver_exact_inversion():
    """Verifica che l'inversione numerica della formula di Black-Scholes restituisca la IV esatta."""
    S, K, T, r, true_sigma = 500.0, 480.0, 0.25, 0.04, 0.22

    # 1. Test su Put
    bs_put = black_scholes_pricing(S=S, K=K, T=T, r=r, sigma=true_sigma, option_type="put")
    solved_put_iv = implied_volatility_solver(bs_put["price"], S=S, K=K, T=T, r=r, option_type="put")
    assert abs(solved_put_iv - true_sigma) < 1e-4

    # 2. Test su Call
    bs_call = black_scholes_pricing(S=S, K=K, T=T, r=r, sigma=true_sigma, option_type="call")
    solved_call_iv = implied_volatility_solver(bs_call["price"], S=S, K=K, T=T, r=r, option_type="call")
    assert abs(solved_call_iv - true_sigma) < 1e-4


def test_implied_volatility_solver_edge_cases():
    """Testa i valori limite (prezzi nulli, intrinseco e limiti superiori)."""
    assert implied_volatility_solver(0.0, 100.0, 100.0, 0.5, 0.05) == 0.0
    # Prezzo al di sotto del valore intrinseco
    assert implied_volatility_solver(0.001, 100.0, 80.0, 0.5, 0.05, option_type="call") >= 0.001


def test_fit_volatility_smile_calibration():
    spot = 500.0
    T = 0.25
    strikes = np.array([400.0, 450.0, 475.0, 500.0, 525.0, 550.0, 600.0])
    # Skew realistico: Put OTM hanno IV più alta
    ivs = np.array([0.30, 0.25, 0.22, 0.18, 0.16, 0.15, 0.16])

    fit_res = fit_volatility_smile(strikes, ivs, spot, T)
    assert fit_res["atm_iv"] > 0
    assert fit_res["skew_slope"] < 0  # Pendenza negativa per skew azionario
    assert fit_res["smile_curvature"] > 0  # Convessità positiva
    assert fit_res["r_squared"] > 0.80

    # Valutazione su strike OTM Put vs OTM Call
    iv_put_otm = fit_res["eval_func"](450.0)
    iv_atm = fit_res["eval_func"](500.0)
    iv_call_otm = fit_res["eval_func"](550.0)
    assert iv_put_otm > iv_atm
    assert iv_put_otm > iv_call_otm


def test_build_volatility_surface_structure():
    surf = build_volatility_surface(spot=550.0, base_atm_iv=0.18)
    assert "df_surface" in surf
    assert "matrix_iv" in surf
    assert "smile_models" in surf
    assert len(surf["expiries_months"]) == 4
    assert len(surf["strikes"]) == 21

    df = surf["df_surface"]
    assert not df.empty
    assert (df["implied_vol_pct"] > 0).all()


def test_skew_adjusted_delta_hedge():
    """Verifica che la calibrazione dello Skew riconosca il maggior costo delle Put OTM."""
    port_val = 100000.0
    beta = 1.0
    spot = 500.0
    atm_iv = 0.18

    # 1. Delta hedge con Skew
    hedge_skew = compute_portfolio_delta_hedge(
        portfolio_value=port_val,
        portfolio_beta=beta,
        benchmark_spot=spot,
        strike_otm_pct=5.0,
        expiry_months=3.0,
        implied_vol=atm_iv,
        use_skew_calibration=True,
    )

    # 2. Delta hedge Piatto
    hedge_flat = compute_portfolio_delta_hedge(
        portfolio_value=port_val,
        portfolio_beta=beta,
        benchmark_spot=spot,
        strike_otm_pct=5.0,
        expiry_months=3.0,
        implied_vol=atm_iv,
        use_skew_calibration=False,
    )

    # La IV effettiva con skew deve essere superiore alla IV ATM per una Put 5% OTM
    assert hedge_skew["effective_iv_pct"] > hedge_skew["base_atm_iv_pct"]
    assert hedge_skew["put_price"] >= hedge_flat["put_price"]
    assert hedge_skew["skew_cost_premium_eur"] >= 0.0


def test_covered_call_skew_adjusted():
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 100, "last_price": 180.0},
        {"ticker": "MSFT", "qty_net": 50, "last_price": 400.0},
    ])

    df_cov = compute_covered_call_yield_enhancement(df_pos, otm_pct=5.0, implied_vol=0.20, use_skew_calibration=True)
    assert not df_cov.empty
    assert len(df_cov) == 2
    assert "iv_effettiva_pct" in df_cov.columns
    assert (df_cov["extra_rendimento_annuo_pct"] > 0).all()
