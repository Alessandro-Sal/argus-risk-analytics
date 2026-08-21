# ============================================================
# test_enhancements.py — Tests for Platform Enhancements
# Investment Risk BI Platform
# ============================================================

import pytest
import pandas as pd
import numpy as np
from datetime import date
from core.schemas import validate_transaction_records, TransactionContract
from core.risk_engine import _compute_efficient_frontier
from core.pdf_generator import generate_executive_pdf_report


def test_schema_validation():
    records = [
        {
            "tx_date": date(2023, 1, 15),
            "ticker": "AAPL",
            "tx_type": "buy",
            "quantity": 10.0,
            "price": 150.0,
            "currency": "usd",
            "fees": 1.5
        },
        {
            "tx_date": date(2023, 2, 20),
            "ticker": "MSFT",
            "tx_type": "invalid_type",
            "quantity": -5.0,
            "price": 200.0
        }
    ]

    valid, errors = validate_transaction_records(records)
    assert len(valid) == 1
    assert valid[0].ticker == "AAPL"
    assert valid[0].currency == "USD"
    assert len(errors) == 1


def test_ledoit_wolf_optimization():
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100)
    ret_a = np.random.normal(0.001, 0.015, 100)
    ret_b = np.random.normal(0.0008, 0.012, 100)
    
    df_returns = pd.DataFrame({"AAPL": ret_a, "MSFT": ret_b}, index=dates)
    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 10, "weight_pct": 50.0},
        {"ticker": "MSFT", "qty_net": 5, "weight_pct": 50.0}
    ])

    res = _compute_efficient_frontier(df_returns, df_positions)
    assert "cov_type" in res
    assert res["cov_type"] in ["Ledoit-Wolf Shrinkage", "Sample Covariance"]
    assert "max_sharpe" in res
    assert "min_vol" in res
    assert res["max_sharpe"]["sharpe"] >= res["min_vol"]["sharpe"]


def test_pdf_report_generation():
    risk_data = {
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "asset_class": "Equity", "current_value": 1500.0, "weight_pct": 60.0, "unrealized_pnl": 200.0, "yield_on_cost_pct": 2.5, "dividends_total": 50.0, "days_to_liquidate": 0.5},
            {"ticker": "MSFT", "asset_class": "Equity", "current_value": 1000.0, "weight_pct": 40.0, "unrealized_pnl": 100.0, "yield_on_cost_pct": 1.8, "dividends_total": 30.0, "days_to_liquidate": 0.3}
        ]),
        "metrics": {
            "returns": {"cagr_pct": 12.5},
            "market_risk": {
                "sharpe_ratio": 1.4, "max_drawdown_pct": -15.2, "volatility_pct": 18.0, "var_95_pct": -2.1,
                "ulcer_index": 4.25, "ff_alpha_pct": 2.1, "ff_beta_mkt": 1.05, "smb_tilt": 0.15, "hml_tilt": -0.08
            },
            "concentration": {"diversification_ratio": 1.35, "hhi_index": 0.52, "effective_n_assets": 1.9}
        },
        "optimization": {
            "cov_type": "Ledoit-Wolf Shrinkage",
            "max_sharpe": {"return": 0.15, "risk": 0.12, "sharpe": 1.25},
            "min_vol": {"return": 0.08, "risk": 0.07, "sharpe": 1.14}
        },
        "stress_tests": {
            "Dot-Com Crash (Mar 2000 - Ott 2002)": {"portfolio_loss_pct": -48.2},
            "Lehman Brothers (Sep-Nov 2008)": {"portfolio_loss_pct": -35.1},
            "US Downgrade Crisis (Ago 2011)": {"portfolio_loss_pct": -16.5},
            "COVID-19 Crash (Feb-Mar 2020)": {"portfolio_loss_pct": -22.4},
            "Tech & Rate Shock (Gen-Ott 2022)": {"portfolio_loss_pct": -18.2}
        }
    }

    pdf_bytes = generate_executive_pdf_report("Test Portfolio", risk_data, "EUR")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_fama_french_and_ulcer_index():
    from core.risk_engine import _calc_market_risk, _calc_stress_tests
    dates = pd.date_range("2023-01-01", periods=100)
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0.001, 0.015, 100), index=dates)
    sr_bench = pd.Series(np.random.normal(0.0008, 0.012, 100), index=dates)

    res = _calc_market_risk(sr_port, sr_bench, "SPY")
    assert "ulcer_index" in res
    assert "ff_alpha_pct" in res
    assert "ff_beta_mkt" in res
    assert "smb_tilt" in res
    assert "hml_tilt" in res
    assert res["ulcer_index"] >= 0.0

    df_returns = pd.DataFrame({"AAPL": sr_port, "MSFT": sr_bench}, index=dates)
    df_positions = pd.DataFrame([
        {"ticker": "AAPL", "qty_net": 10, "current_value": 1500.0},
        {"ticker": "MSFT", "qty_net": 5, "current_value": 1000.0}
    ])
    stress_res = _calc_stress_tests(df_returns, df_positions, sr_bench)
    assert "Dot-Com Crash (Mar 2000 - Ott 2002)" in stress_res
    assert "US Downgrade Crisis (Ago 2011)" in stress_res


def test_institutional_and_pe_engines():
    from core.risk_engine import (
        compute_brinson_attribution,
        compute_hierarchical_risk_parity,
        compute_almgren_chriss_market_impact,
        compute_private_equity_waterfall
    )
    
    # 1. HRP Test
    cov_matrix = pd.DataFrame([[0.04, 0.01], [0.01, 0.09]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"])
    hrp_w = compute_hierarchical_risk_parity(cov_matrix)
    assert "AAPL" in hrp_w
    assert "MSFT" in hrp_w
    assert abs(sum(hrp_w.values()) - 1.0) < 1e-3

    # 2. Brinson Attribution Test
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "gics_sector": "Technology", "current_value": 600.0, "weight_pct": 60.0},
        {"ticker": "JPM", "gics_sector": "Financials", "current_value": 400.0, "weight_pct": 40.0}
    ])
    dates = pd.date_range("2023-01-01", periods=50)
    df_ret = pd.DataFrame({"AAPL": np.random.normal(0.001, 0.01, 50), "JPM": np.random.normal(0.0005, 0.01, 50)}, index=dates)
    bm_series = pd.Series(np.random.normal(0.0008, 0.008, 50), index=dates)
    df_brinson = compute_brinson_attribution(df_pos, df_ret, bm_series)
    assert not df_brinson.empty
    assert "Allocation Effect %" in df_brinson.columns

    # 3. Almgren-Chriss Impact Test
    df_pos_ac = pd.DataFrame([
        {"ticker": "AAPL", "current_value": 100000.0, "days_to_liquidate": 2.5}
    ])
    df_ac = compute_almgren_chriss_market_impact(df_pos_ac)
    assert not df_ac.empty
    assert df_ac.iloc[0]["Slippage Stimato %"] > 0

    # 4. Private Equity Waterfall Test
    pe_res = compute_private_equity_waterfall(capital_calls=1000000.0, distributions=1500000.0, nav=500000.0, hurdle_rate=0.08, carried_interest=0.20)
    assert pe_res["tvpi_moic"] == 2.0
    assert pe_res["dpi"] == 1.5
    assert pe_res["gp_carried_interest"] > 0


def test_optimize_plotly_figure_memory():
    """Verifica che optimize_plotly_figure_memory arrotondi i dati float e riduca il payload."""
    import plotly.graph_objects as go
    from core.ui_utils import optimize_plotly_figure_memory, apply_plotly_theme

    fig = go.Figure(data=[
        go.Scatter(
            x=[1.123456789, 2.987654321],
            y=[10.55555555, 20.88888888],
            marker=dict(color=[0.11111111, 0.99999999])
        )
    ])
    fig_opt = apply_plotly_theme(fig)
    assert fig_opt is not None
    # Verifica arrotondamento coordinate x, y
    assert list(fig_opt.data[0].x) == [1.1235, 2.9877]
    assert list(fig_opt.data[0].y) == [10.5556, 20.8889]
    assert list(fig_opt.data[0].marker.color) == [0.1111, 1.0]




