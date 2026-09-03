# ==============================================================================
# tests/test_wealth_enhancements.py
# ARGUS — Unit Tests for Universal Bank Parser, Watchdog & Stress Engine
# ==============================================================================

import pytest
import io
import pandas as pd
from core.wealth.universal_bank_parser import (
    parse_bank_statement_file,
    detect_bank_format,
    clean_currency_amount,
    parse_date_universal,
    categorize_transaction
)
from core.wealth.wealth_watchdog import WealthWatchdog, WatchdogAlert
from core.wealth.wealth_stress_engine import (
    run_wealth_stress_test,
    PRESET_STRESS_SCENARIOS,
    create_wealth_waterfall_chart,
    simulate_wealth_recovery_trajectories
)


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

    # Verifica generazione grafici Plotly
    fig_waterfall = create_wealth_waterfall_chart(res)
    assert fig_waterfall is not None
    assert len(fig_waterfall.data) > 0

    fig_montecarlo = simulate_wealth_recovery_trajectories(res["post_shock"]["net_worth"])
    assert fig_montecarlo is not None
    assert len(fig_montecarlo.data) == 3
