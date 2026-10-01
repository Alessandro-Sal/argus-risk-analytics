# ==============================================================================
# tests/test_wealth_enhancements.py
# ARGUS — Unit Tests for Universal Bank Parser, Watchdog & Stress Engine
# ==============================================================================

import io

import pandas as pd
import pytest

from core.wealth.universal_bank_parser import (
    categorize_transaction,
    clean_currency_amount,
    detect_bank_format,
    parse_bank_statement_file,
    parse_date_universal,
)
from core.wealth.wealth_stress_engine import (
    PRESET_STRESS_SCENARIOS,
    UnifiedMacroStressEngine,
    calculate_stressed_mortgage_impact,
    create_liquidity_squeeze_timeline_chart,
    create_wealth_waterfall_chart,
    run_wealth_stress_test,
    simulate_wealth_recovery_trajectories,
)
from core.wealth.wealth_watchdog import WatchdogAlert, WealthWatchdog


def test_clean_currency_amount():
    assert clean_currency_amount("1.234,56 €") == 1234.56
    assert clean_currency_amount("-450,00") == -450.00
    assert clean_currency_amount("(100.50)") == -100.50
    assert clean_currency_amount("1,500.00 USD") == 1500.00
    assert clean_currency_amount(150.0) == 150.0
    assert clean_currency_amount(None) == 0.0


def test_parse_date_universal():
    assert parse_date_universal("15/08/2025") == "2025-08-15"
    assert parse_date_universal("2025-12-31") == "2025-12-31"
    assert parse_date_universal("01-05-2024") == "2024-05-01"
    assert parse_date_universal("10.02.2023") == "2023-02-10"
    assert parse_date_universal(None) is None


def test_categorize_transaction():
    cat, pillar, is_tr = categorize_transaction("Supermercato Esselunga Milano", -85.50)
    assert pillar == "Needs"
    assert "Cibo" in cat
    assert not is_tr

    cat, pillar, is_tr = categorize_transaction("Giroconto a mio conto deposito", -2000.0)
    assert is_tr
    assert pillar == "Transfer"

    cat, pillar, is_tr = categorize_transaction("Netflix Subscription", -17.99)
    assert pillar == "Wants"

    cat, pillar, is_tr = categorize_transaction("Bonifico Stipendio Luglio", 3200.0)
    assert pillar == "Income"


def test_parse_bank_statement_fineco_mock():
    csv_sample = """Data Registrazione;Data Valuta;Descrizione Completa;Entrate;Uscite
15/07/2025;15/07/2025;Bonifico Stipendio Societa ABC;3200,00;
18/07/2025;18/07/2025;Esselunga Spesa Alimentare;;85,40
20/07/2025;20/07/2025;Netflix Streaming;;17,99
22/07/2025;22/07/2025;Giroconto verso Revolut;;500,00
"""
    res = parse_bank_statement_file(csv_sample, filename="estratto_fineco.csv")
    assert res["success"] is True
    assert res["rows_count"] == 4
    assert res["total_inflow"] == 3200.00
    assert res["total_outflow"] == 103.39
    assert res["transfers_count"] == 1


def test_parse_bank_statement_revolut_mock():
    csv_sample = """Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State
CARD_PAYMENT,Current,2025-06-10 12:00:00,2025-06-10 12:05:00,Amazon EU Shopping,-45.50,0.00,EUR,COMPLETED
TOPUP,Current,2025-06-01 09:00:00,2025-06-01 09:01:00,Top-up from Card,500.00,0.00,EUR,COMPLETED
TRANSFER,Current,2025-06-15 14:00:00,2025-06-15 14:00:00,Giroconto da Fineco,300.00,0.00,EUR,COMPLETED
"""
    res = parse_bank_statement_file(csv_sample, filename="revolut_statement.csv")
    assert res["success"] is True
    assert res["rows_count"] == 3
    assert res["bank_detected"] == "Revolut"


def test_wealth_watchdog_evaluation():
    # Caso 1: Runway critico e minusvalenze in scadenza
    mock_summary = {
        "total_net_worth": 150000.0,
        "liquid_cash": 2500.0,
        "financial_investments": 80000.0,
        "real_estate_total": 60000.0,
        "total_liabilities": 20000.0,
        "pension_total": 0.0,
        "runway_months": 1.2,
        "savings_rate_pct": 12.0
    }
    mock_fiscal = {
        "minusvalenze": pd.DataFrame([
            {"year": 2021, "amount": 5000.0}
        ])
    }
    alerts = WealthWatchdog.evaluate_all_alerts(mock_summary, fiscal_data=mock_fiscal)
    assert len(alerts) >= 2
    severities = [a.severity for a in alerts]
    assert "CRITICAL" in severities


def test_wealth_stress_engine_stagflation():
    mock_summary = {
        "total_net_worth": 500000.0,
        "liquid_cash": 50000.0,
        "financial_investments": 250000.0,
        "physical_assets": 50000.0,
        "real_estate_total": 200000.0,
        "pension_total": 50000.0,
        "total_liabilities": 100000.0,
        "wealth_health_score": 88.0,
        "monthly_expenses": 3000.0
    }
    res = run_wealth_stress_test(mock_summary, PRESET_STRESS_SCENARIOS["STAGFLATION"])
    assert res["post_shock"]["net_worth"] < res["pre_shock"]["net_worth"]
    assert res["deltas"]["financial_investments"] < 0
    assert res["deltas"]["physical_assets"] > 0  # Oro sale in stagflazione
    assert res["post_shock"]["health_score"] <= 88.0

    # Verifica calcolo mutuo non-lineare
    assert "mortgage_impact" in res
    assert res["mortgage_impact"]["monthly_payment_delta"] > 0
    assert res["mortgage_impact"]["annual_extra_interest"] > 0

    # Verifica Liquidity Squeeze & Dynamic SWR
    assert "liquidity_squeeze" in res
    lq = res["liquidity_squeeze"]
    assert lq["months_to_forced_liquidation"] > 0
    assert lq["fire_swr_stressed_pct"] < 4.0

    # Verifica generazione grafici Plotly
    fig_waterfall = create_wealth_waterfall_chart(res)
    assert fig_waterfall is not None
    assert len(fig_waterfall.data) > 0

    fig_montecarlo = simulate_wealth_recovery_trajectories(res["post_shock"]["net_worth"])
    assert fig_montecarlo is not None
    assert len(fig_montecarlo.data) == 3

    fig_timeline = create_liquidity_squeeze_timeline_chart(res)
    assert fig_timeline is not None
    assert len(fig_timeline.data) >= 1


def test_unified_macro_stress_engine_with_risk_positions():
    """Verifica l'integrazione Risk -> Wealth con ticker e beta azionari reali."""
    class MockRiskSubContext:
        def __init__(self):
            self.df_positions = pd.DataFrame([
                {"ticker": "AAPL", "current_value": 150000.0, "qty_net": 100},
                {"ticker": "NVDA", "current_value": 100000.0, "qty_net": 200}
            ])
            self.df_returns = None

    class MockWorkspaceContext:
        def __init__(self):
            self.risk = MockRiskSubContext()

    mock_ws = MockWorkspaceContext()
    engine = UnifiedMacroStressEngine(workspace_context=mock_ws)

    mock_summary = {
        "total_net_worth": 600000.0,
        "liquid_cash": 60000.0,
        "financial_investments": 250000.0,
        "physical_assets": 40000.0,
        "real_estate_total": 300000.0,
        "pension_total": 50000.0,
        "total_liabilities": 100000.0,
        "wealth_health_score": 90.0,
        "monthly_expenses": 3500.0
    }

    res = engine.execute_stress_test(mock_summary, "STAGFLATION")
    assert res["post_shock"]["net_worth"] < res["pre_shock"]["net_worth"]
    assert len(res["ticker_breakdown"]) == 2
    tickers = [t["ticker"] for t in res["ticker_breakdown"]]
    assert "AAPL" in tickers and "NVDA" in tickers
    assert res["deltas"]["financial_investments"] == pytest.approx(-62500.0, 1.0)


def test_cross_portal_macro_stress_bridge():
    """Verifica il calcolo dello shock macro cross-portal e l'haircut patrimoniale."""
    from core.wealth.unified_stress_bridge import (
        evaluate_active_wealth_macro_shock,
        map_global_macro_preset_to_factor_shock,
    )

    shocks = map_global_macro_preset_to_factor_shock("GFC_2008")
    assert shocks.equity_mkt_pct == -0.35
    assert shocks.yield_curve_shift_bps == -125.0
    assert shocks.inflation_rate_pct >= 0

    wealth_snapshot = {
        "liquid_investments": 400_000.0,
        "cash_reserves": 100_000.0,
        "real_estate_gross": 500_000.0,
        "total_liabilities": 200_000.0,
        "variable_debt_principal": 150_000.0,
        "mortgage_interest_rate": 0.025,
        "mortgage_months_remaining": 180,
    }
    result = evaluate_active_wealth_macro_shock(
        wealth_snapshot, session_state_dict={"global_macro_shock": "GFC_2008"}
    )
    assert result["is_shock_active"] is True
    assert result["global_preset_key"] == "GFC_2008"
    assert result["post_stress_net_worth"] < result["pre_stress_net_worth"]
    assert result["total_net_worth_pnl_pct"] < 0


def test_webgl_acceleration():
    """Verifica la conversione automatica di Scatter in Scattergl oltre 2000 punti."""
    import plotly.graph_objects as go

    from core.ux_institutional_hub import ensure_webgl_scatter, style_institutional_chart

    # Scatter piccolo (< 2000 punti) deve rimanere scatter
    fig_small = go.Figure(data=go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
    fig_small_opt = ensure_webgl_scatter(fig_small, threshold=2000)
    assert fig_small_opt.data[0].type == "scatter"

    # Scatter denso (>= 2000 punti) deve convertirsi in scattergl
    large_x = list(range(2500))
    large_y = [x * 0.5 for x in large_x]
    fig_large = go.Figure(data=go.Scatter(x=large_x, y=large_y))
    fig_large_opt = ensure_webgl_scatter(fig_large, threshold=2000)
    assert fig_large_opt.data[0].type == "scattergl"

    # style_institutional_chart converte automaticamente
    fig_styled = style_institutional_chart(fig_large)
    assert fig_styled.data[0].type == "scattergl"


def test_master_board_pack_generation():
    """Verifica la generazione dell'Executive Master Board Pack HTML e struttura."""
    from sqlalchemy import create_engine

    from core.wealth.wealth_db import init_wealth_db
    from core.wealth.wealth_reporting_hub import generate_master_board_pack_html

    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)

    html = generate_master_board_pack_html(
        engine,
        portfolio_id=1,
        prof_name="Family Office Test",
    )
    assert "<!DOCTYPE html>" in html
    assert "Master Board Pack" in html
    assert "Family Office Test" in html


