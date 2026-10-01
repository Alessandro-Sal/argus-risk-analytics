"""
tests/test_wealth_olap.py
Test suite for ARGUS Wealth Management — Vectorized DuckDB OLAP Analytics Engine
"""

import pandas as pd
import pytest

from core.wealth.wealth_olap import (
    compute_wealth_cashflow_olap_cube,
    compute_wealth_snapshot_trajectory_olap,
    is_wealth_olap_available,
)


def test_wealth_olap_availability():
    """Verifica che la funzione is_wealth_olap_available restituisca un booleano coerente."""
    avail = is_wealth_olap_available()
    assert isinstance(avail, bool)


def test_wealth_cashflow_olap_cube_empty():
    """Verifica che il cubo OLAP gestisca dataset vuoti o None senza eccezioni."""
    res = compute_wealth_cashflow_olap_cube(pd.DataFrame())
    assert isinstance(res, dict)
    assert res["summary"]["total_inflows"] == 0.0
    assert res["summary"]["total_outflows"] == 0.0
    assert res["summary"]["tx_count"] == 0
    assert res["monthly_cube"].empty


def test_wealth_cashflow_olap_cube_computations():
    """Verifica il calcolo corretto di aggregazioni mensili, Pareto categorie e ranking merchant."""
    dates = pd.date_range("2025-01-01", periods=10, freq="15D")
    sample_data = [
        {"tx_date": dates[0], "amount": 3500.0, "direction": "inflow", "category_name": "Stipendio", "merchant": "Datore S.p.A."},
        {"tx_date": dates[1], "amount": 1000.0, "direction": "outflow", "category_name": "Affitto", "merchant": "Proprietario"},
        {"tx_date": dates[2], "amount": 3500.0, "direction": "inflow", "category_name": "Stipendio", "merchant": "Datore S.p.A."},
        {"tx_date": dates[3], "amount": 400.0, "direction": "outflow", "category_name": "Spesa", "merchant": "Esselunga"},
        {"tx_date": dates[4], "amount": 250.0, "direction": "outflow", "category_name": "Ristoranti", "merchant": "Trattoria Milano"},
        {"tx_date": dates[5], "amount": 3500.0, "direction": "inflow", "category_name": "Stipendio", "merchant": "Datore S.p.A."},
        {"tx_date": dates[6], "amount": 500.0, "direction": "outflow", "category_name": "Affitto", "merchant": "Proprietario"},
        {"tx_date": dates[7], "amount": 300.0, "direction": "outflow", "category_name": "Spesa", "merchant": "Esselunga"},
        {"tx_date": dates[8], "amount": 50.0, "direction": "outflow", "category_name": "Svago", "merchant": "Cinema"},
        {"tx_date": dates[9], "amount": 1000.0, "direction": "transfer", "category_name": "Giroconto", "merchant": "Conto Deposito"},
    ]
    df = pd.DataFrame(sample_data)

    res = compute_wealth_cashflow_olap_cube(df)

    assert isinstance(res, dict)
    summary = res["summary"]
    assert summary["total_inflows"] == 10500.0
    assert summary["total_outflows"] == 2500.0
    assert summary["net_savings"] == 8000.0
    assert summary["tx_count"] == 9  # Il transfer/giroconto deve essere escluso dai calcoli di budget

    # Verifica monthly cube
    m_cube = res["monthly_cube"]
    assert not m_cube.empty
    assert "ym" in m_cube.columns
    assert "inflows" in m_cube.columns
    assert "outflows" in m_cube.columns
    assert "rolling_outflow_3m" in m_cube.columns

    # Verifica category cube & Pareto
    c_cube = res["category_cube"]
    assert not c_cube.empty
    assert "category_name" in c_cube.columns
    assert "total_amount" in c_cube.columns
    assert "pareto_class" in c_cube.columns
    assert c_cube.iloc[0]["total_amount"] >= c_cube.iloc[-1]["total_amount"]

    # Verifica merchant cube
    merch_cube = res["merchant_cube"]
    assert not merch_cube.empty
    assert "merchant" in merch_cube.columns
    assert "total_spent" in merch_cube.columns
    assert merch_cube.iloc[0]["merchant"] == "Proprietario"


def test_wealth_snapshot_trajectory_olap():
    """Verifica il calcolo di High-Water Mark, Max Drawdown e CAGR su serie temporali di Net Worth."""
    dates = pd.date_range("2024-01-01", periods=5, freq="90D")
    snapshots = pd.DataFrame([
        {"snapshot_date": dates[0], "total_net_worth": 100000.0, "liquid_assets": 20000.0},
        {"snapshot_date": dates[1], "total_net_worth": 110000.0, "liquid_assets": 25000.0},
        {"snapshot_date": dates[2], "total_net_worth": 95000.0, "liquid_assets": 18000.0},  # Drawdown dal picco 110k
        {"snapshot_date": dates[3], "total_net_worth": 120000.0, "liquid_assets": 30000.0}, # Nuovo HWM
        {"snapshot_date": dates[4], "total_net_worth": 125000.0, "liquid_assets": 35000.0},
    ])

    res = compute_wealth_snapshot_trajectory_olap(snapshots)

    assert isinstance(res, dict)
    assert res["peak_net_worth"] == 125000.0
    assert res["max_drawdown_pct"] < 0.0  # -13.6% circa a data 2
    assert res["cagr_pct"] > 0.0

    traj = res["trajectory_df"]
    assert "hwm" in traj.columns
    assert "drawdown_pct" in traj.columns
    assert "liquidity_ratio_pct" in traj.columns
