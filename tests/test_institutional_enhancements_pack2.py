# ==============================================================================
# tests/test_institutional_enhancements_pack2.py
# ARGUS — Unit Tests for Optimal Liquidation Lab, PRIIPs KID & Morning Briefing
# ==============================================================================

import pandas as pd
import pytest

from core.morning_meeting_engine import (
    generate_daily_committee_note_pdf,
    generate_morning_meeting_script,
)
from core.optimal_liquidation_engine import (
    OptimalLiquidationConfig,
    OptimalLiquidationEngine,
    compute_optimal_execution_schedule,
)
from core.priips_kid_generator import (
    generate_priips_kid_data,
    generate_priips_kid_html,
    generate_priips_kid_pdf,
)


def test_optimal_liquidation_engine_schedule():
    """Verifica il calcolo della schedulazione ottima Almgren-Chriss, VWAP e TWAP."""
    cfg = OptimalLiquidationConfig(
        ticker="ENI.MI",
        order_shares=200_000.0,
        spot_price=14.50,
        adv_shares=4_000_000.0,
        daily_volatility=0.018,
        bid_ask_spread_bps=4.0,
        risk_aversion_lambda=2.5e-6,
        horizon_hours=6.5,
        n_slices=13,
        max_pov_cap=0.15,
    )
    engine = OptimalLiquidationEngine(config=cfg)
    res = engine.compute_schedule()

    assert res["ticker"] == "ENI.MI"
    assert res["order_shares"] == 200_000.0
    assert res["order_pct_of_adv"] == 5.0
    assert res["urgency_parameter_kappa"] > 0.0

    # Verifica strategie presenti
    strats = res["strategies"]
    assert "almgren_chriss_optimal" in strats
    assert "dynamic_vwap" in strats
    assert "uniform_twap" in strats

    opt = strats["almgren_chriss_optimal"]
    assert opt["expected_cost_eur"] > 0.0
    assert opt["expected_cost_bps"] > 0.0
    assert opt["timing_risk_std_eur"] > 0.0
    assert len(opt["inventory_path"]) == 14  # initial + 13 slices
    assert opt["inventory_path"][-1] == 0.0  # complete liquidation

    # Verifica tabella schedulazione
    sched = res["intraday_schedule"]
    assert len(sched) == 13
    assert sched[0]["time_bucket"] == "09:00-09:30"
    total_opt_trades = sum(item["optimal_shares"] for item in sched)
    assert pytest.approx(total_opt_trades, rel=1e-3) == 200_000.0


def test_convenience_entrypoint_compute_optimal_execution_schedule():
    """Verifica la convenience function compute_optimal_execution_schedule."""
    res = compute_optimal_execution_schedule(
        ticker="ISP.MI",
        order_shares=100_000.0,
        spot_price=3.20,
        adv_shares=20_000_000.0,
    )
    assert res["ticker"] == "ISP.MI"
    assert res["recommended_algorithm"] != ""
    assert len(res["intraday_schedule"]) == 13


def test_priips_kid_dataset_generation():
    """Verifica la generazione del dataset normativo PRIIPs KID e SFDR."""
    mock_risk = {
        "portfolio_return": pd.Series([0.001, -0.002, 0.003, 0.0015, -0.001] * 20),
        "portfolio_beta": 1.10,
        "var_95_hist": 0.021,
    }
    kid_data = generate_priips_kid_data(
        portfolio_name="Portafoglio ESG Private Banking",
        risk_data=mock_risk,
        base_currency="EUR",
        rhp_years=5.0,
        investment_amount=10_000.0,
    )

    assert kid_data["portfolio_name"] == "Portafoglio ESG Private Banking"
    assert kid_data["base_currency"] == "EUR"
    assert kid_data["rhp_years"] == 5.0
    assert kid_data["investment_amount_eur"] == 10_000.0
    assert kid_data["audit_signature"] != ""

    priips = kid_data["priips"]
    assert 1 <= priips["sri_score"] <= 7
    assert 1 <= priips["mrm_score"] <= 7
    assert 1 <= priips["crm_score"] <= 6
    assert priips["vev_percent"] > 0.0

    scenarios = priips["performance_scenarios"]
    for sc in ["stress", "unfavourable", "moderate", "favourable"]:
        assert sc in scenarios
        assert "1_year" in scenarios[sc]
        assert "rhp" in scenarios[sc]
        assert scenarios[sc]["1_year"]["terminal_value_eur"] > 0.0

    sfdr = kid_data["sfdr"]
    assert sfdr["sfdr_classification"] in ["Article 6", "Article 8", "Article 9"]
    assert sfdr["taxonomy_alignment_pct"] > 0.0
    assert len(sfdr["pai_indicators"]) >= 5


def test_priips_kid_html_and_pdf_generation():
    """Verifica la formattazione dell'HTML e la generazione del PDF PRIIPs KID."""
    kid_data = generate_priips_kid_data(portfolio_name="Test Portfolio")

    # Verifica HTML
    html_output = generate_priips_kid_html(kid_data)
    assert "<!DOCTYPE html>" in html_output
    assert "REGOLAMENTO (UE) N. 1286/2014" in html_output
    assert "Test Portfolio" in html_output
    assert "Scenario di Stress" in html_output

    # Verifica PDF
    pdf_bytes = generate_priips_kid_pdf(kid_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # Valid binary document
    assert pdf_bytes.startswith(b"%PDF") or b"REGOLAMENTO" in pdf_bytes


def test_morning_meeting_briefing_script_and_pdf():
    """Verifica il motore di briefing vocale Morning Meeting e la Daily Committee Note."""
    mock_risk = {
        "portfolio_return": pd.Series([0.0042]),
        "benchmark_return": pd.Series([0.0028]),
        "var_95_hist": 0.0185,
        "portfolio_beta": 1.08,
        "cagr_pct": 14.2,
    }
    briefing = generate_morning_meeting_script(
        portfolio_name="Argus Institutional Alpha",
        risk_data=mock_risk,
        base_currency="EUR",
    )

    assert briefing["portfolio_name"] == "Argus Institutional Alpha"
    assert "Buongiorno al Comitato Investimenti" in briefing["script_text"]
    assert "Argus Institutional Alpha" in briefing["script_text"]
    assert briefing["duration_seconds"] == 85
    assert briefing["audit_signature"] != ""
    assert len(briefing["key_takeaways"]) >= 4

    m = briefing["metrics"]
    assert m["portfolio_1d_pct"] == 0.42
    assert m["benchmark_1d_pct"] == 0.28
    assert m["alpha_1d_pct"] == 0.14
    assert m["var_95_pct"] == 1.85

    # Verifica PDF A4
    pdf_bytes = generate_daily_committee_note_pdf(briefing)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF") or b"Buongiorno" in pdf_bytes


def test_optimal_liquidation_small_share_quantities():
    """Verifica che la liquidazione ottima funzioni correttamente anche per piccole quote (es. 28 azioni o frazionarie)."""
    cfg = OptimalLiquidationConfig(
        ticker="AAPL",
        order_shares=28.0,
        spot_price=220.0,
        adv_shares=50_000_000.0,
        daily_volatility=0.015,
        bid_ask_spread_bps=2.0,
        risk_aversion_lambda=2.5e-6,
        horizon_hours=6.5,
        n_slices=13,
        max_pov_cap=0.15,
    )
    engine = OptimalLiquidationEngine(config=cfg)
    res = engine.compute_schedule()
    assert res["order_shares"] == 28.0
    assert "almgren_chriss_optimal" in res["strategies"]


def test_render_optimal_liquidation_lab_with_28_shares():
    """Verifica che render_optimal_liquidation_lab gestisca posizioni con 28 azioni senza eccezioni di min_value."""
    from unittest.mock import MagicMock, patch

    from core.optimal_liquidation_engine import render_optimal_liquidation_lab

    pos = pd.DataFrame({
        "ticker": ["AAPL"],
        "qty_net": [28.0],
        "last_price": [220.0],
        "current_value": [6160.0],
    })

    mock_st = MagicMock()
    mock_st.session_state = {}

    def fake_columns(spec, **kwargs):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [MagicMock() for _ in range(n)]

    mock_st.columns.side_effect = fake_columns

    def fake_selectbox(label, options, index=0, **kwargs):
        if options and index < len(options):
            return options[index]
        return options[0] if options else "AAPL"

    mock_st.selectbox.side_effect = fake_selectbox

    def fake_number_input(label, *args, **kwargs):
        val = kwargs.get("value")
        min_v = kwargs.get("min_value")
        max_v = kwargs.get("max_value")
        if min_v is None and len(args) >= 1:
            min_v = args[0]
        if max_v is None and len(args) >= 2:
            max_v = args[1]
        if val is None and len(args) >= 3:
            val = args[2]
        if val is None:
            val = min_v if min_v is not None else 1.0
        if min_v is not None and val is not None:
            assert val >= min_v, f"StreamlitValueBelowMinError: value {val} < min_value {min_v}"
        if max_v is not None and val is not None:
            assert val <= max_v, f"StreamlitValueAboveMaxError: value {val} > max_value {max_v}"
        return val

    mock_st.number_input.side_effect = fake_number_input
    mock_st.slider.return_value = 13
    mock_st.select_slider.return_value = 2.5e-6

    with patch("streamlit.columns", mock_st.columns), \
         patch("streamlit.selectbox", mock_st.selectbox), \
         patch("streamlit.number_input", mock_st.number_input), \
         patch("streamlit.slider", mock_st.slider), \
         patch("streamlit.select_slider", mock_st.select_slider), \
         patch("streamlit.session_state", mock_st.session_state), \
         patch("streamlit.markdown", mock_st.markdown), \
         patch("streamlit.expander", mock_st.expander), \
         patch("streamlit.plotly_chart", mock_st.plotly_chart), \
         patch("streamlit.dataframe", mock_st.dataframe):
        render_optimal_liquidation_lab(positions=pos, key_prefix="test_liq")

