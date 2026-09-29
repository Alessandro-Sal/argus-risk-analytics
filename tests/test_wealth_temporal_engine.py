# ============================================================
# tests/test_wealth_temporal_engine.py
# Unit tests for ARGUS Wealth Temporal Analytics & Modals
# ============================================================

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from core.terminal_engine import get_terminal_engine
from core.wealth.wealth_db import (
    create_wealth_portfolio,
    init_wealth_db,
    insert_cashflow_tx,
    save_wealth_account,
)
from core.wealth.wealth_temporal_engine import (
    compute_wealth_benchmark_comparison,
    compute_wealth_growth_attribution,
    compute_wealth_monthly_matrix,
    compute_wealth_rolling_metrics,
    compute_wealth_seasonality_patterns,
    compute_wealth_temporal_progression,
    compute_wealth_underwater_drawdowns,
)


@pytest.fixture
def temporal_test_env():
    """
    Crea un database SQLite isolato in-memory con un profilo wealth controllato
    e serie storiche coerenti per testare deterministicamente il motore temporale.
    """
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_wealth_db(eng)
    pid = create_wealth_portfolio(eng, name="Test Temporal Portfolio", owner="Test User", base_currency="EUR")

    save_wealth_account(eng, {"portfolio_id": pid, "name": "Conto Fineco", "account_type": "checking", "balance": 25000.0})
    save_wealth_account(eng, {"portfolio_id": pid, "name": "Conto Titoli", "account_type": "investment", "balance": 35000.0})

    # Inserimento snapshot storici certificati (2022-2026) per una traiettoria coerente
    with eng.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO wealth_networth_snapshots (portfolio_id, snapshot_date, total_net_worth, liquid_assets, financial_investments)
                VALUES 
                (:pid, '2022-01-01', 16000.0, 10000.0, 6000.0),
                (:pid, '2022-12-31', 21000.0, 12000.0, 9000.0),
                (:pid, '2023-12-31', 32000.0, 16000.0, 16000.0),
                (:pid, '2024-12-31', 45000.0, 20000.0, 25000.0),
                (:pid, '2025-12-31', 58000.0, 24000.0, 34000.0)
            """),
            {"pid": pid},
        )

    # Inserimento flussi di cassa mensili per i test di flussi e stagionalità
    for m in range(1, 13):
        insert_cashflow_tx(
            eng,
            {
                "portfolio_id": pid,
                "account_id": 1,
                "category_id": 1,
                "tx_date": f"2025-{m:02d}-15",
                "amount": 2500.0,
                "currency": "EUR",
                "direction": "inflow",
            },
        )
        insert_cashflow_tx(
            eng,
            {
                "portfolio_id": pid,
                "account_id": 1,
                "category_id": 2,
                "tx_date": f"2025-{m:02d}-20",
                "amount": 1500.0,
                "currency": "EUR",
                "direction": "outflow",
            },
        )

    return eng, pid


def test_wealth_temporal_progression(temporal_test_env):
    engine, pid = temporal_test_env
    res = compute_wealth_temporal_progression(engine, portfolio_id=pid, timeframe_months=12)
    assert res["months_count"] == 13

    res24_real = compute_wealth_temporal_progression(engine, portfolio_id=pid, timeframe_months=24, adjust_inflation=True)
    assert res24_real["is_inflation_adjusted"] is True
    assert res24_real["months_count"] == 25

    # 5-year trajectory test: verify 2022 values are realistic (~16k - 21k) and not synthetic ~50k
    res60 = compute_wealth_temporal_progression(engine, portfolio_id=pid, timeframe_months=60)
    assert res60["months_count"] == 61
    df_2022 = res60["history_df"].loc["2022-01-01":"2022-12-31"]
    if not df_2022.empty:
        assert df_2022["total_net_worth"].max() < 25000.0
        assert df_2022["total_net_worth"].min() > 14000.0


def test_wealth_growth_attribution(temporal_test_env):
    engine, pid = temporal_test_env
    res = compute_wealth_growth_attribution(engine, portfolio_id=pid, timeframe_months=24)
    assert "attribution_df" in res
    assert not res["attribution_df"].empty
    assert "cumulative_savings_eur" in res
    assert "cumulative_market_pnl_eur" in res
    assert "savings_share_pct" in res
    assert "market_share_pct" in res


def test_wealth_benchmark_comparison(temporal_test_env):
    engine, pid = temporal_test_env
    res = compute_wealth_benchmark_comparison(engine, portfolio_id=pid, timeframe_months=24)
    assert "comparison_df" in res
    assert not res["comparison_df"].empty
    assert "nw_cumulative_return_pct" in res
    assert "bm_cumulative_return_pct" in res
    assert "outperformance_pct" in res
    assert "wealth_beta" in res
    assert res["wealth_beta"] > 0


def test_wealth_monthly_matrix(temporal_test_env):
    engine, pid = temporal_test_env
    df_matrix = compute_wealth_monthly_matrix(engine, portfolio_id=pid)

    assert not df_matrix.empty
    assert "Gen" in df_matrix.columns
    assert "Dic" in df_matrix.columns
    assert "Totale Annuo (€)" in df_matrix.columns


def test_wealth_rolling_metrics(temporal_test_env):
    engine, pid = temporal_test_env
    df_roll = compute_wealth_rolling_metrics(engine, portfolio_id=pid, window_months=6)

    assert not df_roll.empty
    assert "Net_Worth_EUR" in df_roll.columns
    assert "Rolling_Growth_Pct" in df_roll.columns
    assert "Rolling_Wealth_Vol_Pct" in df_roll.columns


def test_wealth_underwater_drawdowns(temporal_test_env):
    engine, pid = temporal_test_env
    res = compute_wealth_underwater_drawdowns(engine, portfolio_id=pid)

    assert "underwater_df" in res
    assert not res["underwater_df"].empty
    assert "max_drawdown_pct" in res
    assert "episodes_df" in res
    assert not res["episodes_df"].empty


def test_wealth_seasonality_patterns(temporal_test_env):
    engine, pid = temporal_test_env
    res = compute_wealth_seasonality_patterns(engine, portfolio_id=pid)

    assert "seasonality_df" in res
    assert len(res["seasonality_df"]) == 12
    assert res["best_accumulation_month"] is not None
    assert res["heaviest_spending_month"] is not None


def test_wealth_time_terminal_command(temporal_test_env):
    engine, pid = temporal_test_env
    term = get_terminal_engine()
    ctx = {"engine": engine, "wealth_portfolio_id": pid, "wealth_active_portfolio_id": pid, "portfolio_id": pid}

    res = term.execute_command("WEALTH TIME", ctx)
    assert res.status == "SUCCESS"
    assert "WEALTH TEMPORAL ANALYTICS" in res.output_text
