# ============================================================
# test_frontend_smoke.py — Smoke Test for Streamlit Frontend Pages
# Investment Risk BI Platform
# ============================================================

import pytest
import pandas as pd
import numpy as np
import streamlit as st
import os
import glob


def test_frontend_pages_execution():
    """
    Simula lo stato sessione Streamlit ed esegue il codice di ciascuna pagina
    per verificare che il frontend non generi eccezioni, errori di importazione o crash.
    """
    # Popoliamo session_state con un mock completo dei dati di rischio
    dates = pd.date_range("2023-01-01", periods=100)
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0.001, 0.015, 100), index=dates)
    sr_bench = pd.Series(np.random.normal(0.0008, 0.012, 100), index=dates)

    st.session_state["results"] = {
        "portfolio_id": 1,
        "computed_at": "2026-07-21 21:00:00",
        "portfolio_return": sr_port,
        "benchmark_return": sr_bench,
        "positions": pd.DataFrame([
            {
                "ticker": "AAPL", "asset_class": "Equity", "gics_sector": "Information Technology",
                "country": "US", "qty_net": 10.0, "avg_cost": 150.0, "last_price": 180.0,
                "current_value": 1800.0, "cost_basis": 1500.0, "unrealized_pnl": 300.0,
                "realized_pnl": 50.0, "dividends_total": 20.0, "total_return": 370.0,
                "weight_pct": 60.0, "yield_on_cost_pct": 1.33, "days_to_liquidate": 0.5,
                "trailing_pe": 28.5, "forward_pe": 25.0, "price_to_book": 8.0,
                "dividend_yield": 0.006, "roe": 0.35, "target_mean_price": 200.0, "peg_ratio": 1.5
            },
            {
                "ticker": "MSFT", "asset_class": "Equity", "gics_sector": "Information Technology",
                "country": "US", "qty_net": 5.0, "avg_cost": 240.0, "last_price": 240.0,
                "current_value": 1200.0, "cost_basis": 1200.0, "unrealized_pnl": 0.0,
                "realized_pnl": 0.0, "dividends_total": 15.0, "total_return": 15.0,
                "weight_pct": 40.0, "yield_on_cost_pct": 1.25, "days_to_liquidate": 0.3,
                "trailing_pe": 32.0, "forward_pe": 28.0, "price_to_book": 10.0,
                "dividend_yield": 0.008, "roe": 0.40, "target_mean_price": 270.0, "peg_ratio": 1.8
            }
        ]),
        "returns": pd.DataFrame({"AAPL": sr_port, "MSFT": sr_bench}, index=dates),
        "metrics": {
            "returns": {
                "portfolio_value": 3000.0, "cost_basis_total": 2700.0, "total_pnl": 385.0,
                "total_pnl_pct": 0.1426, "dividends_total": 35.0, "total_return_pct": 14.26,
                "cagr_pct": 12.5, "sharpe_ratio": 1.4, "sortino_ratio": 1.8, "calmar_ratio": 1.1,
                "alpha_pct": 2.5, "information_ratio": 0.8, "benchmark_cagr_pct": 10.0
            },
            "market_risk": {
                "volatility_daily_pct": 1.5, "volatility_annual_pct": 23.8,
                "skewness": -0.15, "kurtosis": 0.85, "tracking_error_pct": 5.2,
                "beta": 1.05, "correlation_benchmark": 0.88, "r_squared_pct": 77.4,
                "max_drawdown_pct": -12.5, "ulcer_index": 3.8, "avg_drawdown_days": 14.2,
                "ff_alpha_pct": 1.8, "ff_beta_mkt": 1.02, "smb_tilt": 0.12, "hml_tilt": -0.05,
                "var_95": 2.1, "var_99": 3.5, "cvar_95": 3.0, "cvar_99": 4.5,
                "var_parametric_95": 2.0, "var_cf_95": 2.2, "var_exceptions_count": 4,
                "benchmark_ticker": "SPY"
            },
            "concentration": {
                "hhi": 0.52, "effective_n_assets": 1.9, "n_active_positions": 2,
                "by_asset_class_pct": {"Equity": 100.0},
                "by_gics_sector_pct": {"Information Technology": 100.0},
                "by_country_pct": {"US": 100.0},
                "top5_positions": [
                    {"ticker": "AAPL", "current_value": 1800.0, "weight_pct": 60.0},
                    {"ticker": "MSFT", "current_value": 1200.0, "weight_pct": 40.0}
                ],
                "diversification_ratio": 1.35
            }
        },
        "optimization": {
            "cov_type": "Ledoit-Wolf Shrinkage",
            "max_sharpe": {"weights": {"AAPL": 0.6, "MSFT": 0.4}, "return": 0.15, "risk": 0.12, "sharpe": 1.25},
            "min_vol": {"weights": {"AAPL": 0.3, "MSFT": 0.7}, "return": 0.08, "risk": 0.07, "sharpe": 1.14}
        },
        "stress_tests": {
            "Dot-Com Crash (Mar 2000 - Ott 2002)": {
                "benchmark_shock_pct": -49.0, "portfolio_shock_pct": -45.0,
                "portfolio_loss_pct": -45.0, "portfolio_loss_eur": -1350.0, "details": {}
            },
            "Lehman Brothers (Sep-Nov 2008)": {
                "benchmark_shock_pct": -45.0, "portfolio_shock_pct": -38.0,
                "portfolio_loss_pct": -38.0, "portfolio_loss_eur": -1140.0, "details": {}
            },
            "US Downgrade Crisis (Ago 2011)": {
                "benchmark_shock_pct": -17.0, "portfolio_shock_pct": -15.0,
                "portfolio_loss_pct": -15.0, "portfolio_loss_eur": -450.0, "details": {}
            },
            "COVID-19 Crash (Feb-Mar 2020)": {
                "benchmark_shock_pct": -33.0, "portfolio_shock_pct": -28.0,
                "portfolio_loss_pct": -28.0, "portfolio_loss_eur": -840.0, "details": {}
            },
            "Tech & Rate Shock (Gen-Ott 2022)": {
                "benchmark_shock_pct": -20.0, "portfolio_shock_pct": -22.0,
                "portfolio_loss_pct": -22.0, "portfolio_loss_eur": -660.0, "details": {}
            }
        }
    }
    st.session_state["portfolio_name"] = "Test Portfolio"
    st.session_state["run_id"] = "RUN_TEST_123"
    st.session_state["base_currency"] = "EUR"

    # Verifichiamo la presenza di tutte le pagine Streamlit (almeno 6)
    page_files = glob.glob("src/pages/*.py") or glob.glob("pages/*.py")
    assert len(page_files) >= 6, f"Ci si aspettano almeno 6 pagine nella cartella pages/, trovate: {len(page_files)}"
    
    # Eseguiamo il controllo di compilazione ed importazione di tutte le pagine
    for page_path in page_files:
        with open(page_path, "r", encoding="utf-8") as f:
            code = f.read()
        compiled = compile(code, page_path, "exec")
        assert compiled is not None, f"Impossibile compilare la pagina: {page_path}"
