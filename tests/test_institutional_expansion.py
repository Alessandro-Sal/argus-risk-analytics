# ============================================================
# tests/test_institutional_expansion.py
# Unit tests for ARGUS v6.2.0 Institutional Quant & Wealth Expansion
# ============================================================

import pytest
import pandas as pd
import numpy as np
from core.macro_stress_engine import (
    get_standard_macro_scenarios,
    compute_macro_scenario_stress_test,
    compute_reverse_stress_test
)
from core.autonomous_rebalancer import (
    generate_autonomous_rebalancing_proposal,
    check_mifid_suitability_and_limits
)
from core.esg_engine import (
    compute_portfolio_esg_and_sfdr_metrics
)
from core.options_workbench import (
    get_options_strategy_presets,
    build_options_strategy_payoff
)
from core.quarterly_report_generator import (
    generate_white_label_quarterly_pdf_report
)
from core.terminal_engine import get_terminal_engine
from core.fetcher import get_engine


@pytest.fixture
def dummy_positions_df():
    return pd.DataFrame([
        {"ticker": "SWDA.MI", "nome": "iShares Core MSCI World", "asset_class": "Azionario", "controvalore": 50000.0, "prezzo_corrente": 95.0},
        {"ticker": "XG7S.MI", "nome": "Xtrackers Global Govt Bond", "asset_class": "Obbligazionario", "controvalore": 30000.0, "prezzo_corrente": 105.0},
        {"ticker": "SGLD.MI", "nome": "Invesco Physical Gold", "asset_class": "Materie Prime", "controvalore": 10000.0, "prezzo_corrente": 80.0},
        {"ticker": "XEON.MI", "nome": "Xtrackers EUR Overnight Rate", "asset_class": "Liquidità", "controvalore": 10000.0, "prezzo_corrente": 140.0}
    ])


@pytest.fixture
def dummy_results(dummy_positions_df):
    return {
        "valore_totale": 100000.0,
        "positions": dummy_positions_df,
        "var_storico_95": -8.5
    }


def test_standard_macro_scenarios():
    sc = get_standard_macro_scenarios()
    assert "EBA_Adverse_2026" in sc
    assert "Fed_CCAR_Severe" in sc
    assert sc["EBA_Adverse_2026"]["equity_shock_pct"] == -30.0


def test_macro_scenario_stress_test(dummy_positions_df, dummy_results):
    res = compute_macro_scenario_stress_test(df_positions=dummy_positions_df, results=dummy_results)
    assert res["scenarios_count"] >= 4
    assert res["initial_portfolio_value_eur"] == 100000.0
    assert res["worst_case_drawdown_pct"] < 0.0
    assert not res["scenarios_df"].empty


def test_reverse_stress_test(dummy_positions_df, dummy_results):
    rev = compute_reverse_stress_test(df_positions=dummy_positions_df, results=dummy_results, target_drawdown_pct=-25.0)
    assert rev["target_drawdown_pct"] == -25.0
    assert rev["break_even_solutions"]["pure_equity_crash_pct"] < 0.0
    assert rev["break_even_solutions"]["pure_rate_shock_bps"] > 0.0


def test_mifid_suitability_check(dummy_positions_df, dummy_results):
    mif = check_mifid_suitability_and_limits(df_positions=dummy_positions_df, results=dummy_results, risk_profile="Moderate")
    assert "is_mifid_compliant" in mif
    assert mif["risk_profile"] == "Moderate"


def test_autonomous_rebalancing_proposal(dummy_positions_df, dummy_results):
    reb = generate_autonomous_rebalancing_proposal(df_positions=dummy_positions_df, results=dummy_results)
    assert reb["portfolio_total_value_eur"] == 100000.0
    assert isinstance(reb["trades_list"], list)
    assert not reb["trades_df"].empty


def test_esg_and_sfdr_metrics(dummy_positions_df, dummy_results):
    esg = compute_portfolio_esg_and_sfdr_metrics(df_positions=dummy_positions_df, results=dummy_results)
    assert esg["portfolio_esg_score"] > 0
    assert "art_8_esg_promoting_pct" in esg["sfdr_breakdown"]
    assert not esg["holdings_esg_df"].empty


def test_options_strategy_workbench():
    presets = get_options_strategy_presets()
    assert "Iron Condor" in presets
    assert "Protective Collar" in presets

    res = build_options_strategy_payoff(strategy_name="Iron Condor", underlying_price=100.0)
    assert res["strategy_name"] == "Iron Condor"
    assert "greeks" in res
    assert not res["payoff_df"].empty
    assert len(res["legs"]) == 4


def test_white_label_quarterly_pdf_report():
    engine = get_engine()
    pdf_data = generate_white_label_quarterly_pdf_report(engine, portfolio_id=1, client_name="Test FO", quarter="Q1 2026")
    assert isinstance(pdf_data, bytes)
    assert len(pdf_data) > 100


def test_terminal_institutional_commands(dummy_positions_df, dummy_results):
    term = get_terminal_engine()
    ctx = {
        "df_positions": dummy_positions_df,
        "results": dummy_results
    }

    # Macro Stress & Reverse Stress
    r1 = term.execute_command("STRESS MACRO", ctx)
    assert r1.status == "SUCCESS"
    assert "EBA" in r1.output_text

    r2 = term.execute_command("RSTRESS 25", ctx)
    assert r2.status == "SUCCESS"
    assert "REVERSE STRESS" in r2.output_text

    # Rebalance & MiFID
    r3 = term.execute_command("PROP REBAL", ctx)
    assert r3.status == "SUCCESS"
    assert "AUTONOMOUS REBALANCING" in r3.output_text

    r4 = term.execute_command("MIFID CHECK", ctx)
    assert r4.status == "SUCCESS"
    assert "MIFID II" in r4.output_text

    # ESG
    r5 = term.execute_command("ESG", ctx)
    assert r5.status == "SUCCESS"
    assert "SFDR" in r5.output_text

    # Options Workbench
    r6 = term.execute_command("OPTS CONDOR", ctx)
    assert r6.status == "SUCCESS"
    assert "OPTIONS STRATEGY" in r6.output_text

    # Report QTR
    r7 = term.execute_command("REPORT QTR", ctx)
    assert r7.status == "SUCCESS"
    assert "WHITE-LABEL" in r7.output_text

