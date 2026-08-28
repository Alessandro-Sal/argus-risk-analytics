import pytest
import pandas as pd
from core.report_exporter import generate_pdf_factsheet, generate_excel_report, generate_institutional_audit_dossier
from core.rebalancer import compute_rebalancing_orders
from core.advisor import generate_quant_advisory_report
from core.dividend_engine import compute_dividend_forecast

@pytest.fixture
def mock_risk_results():
    pos = pd.DataFrame([
        {"ticker": "META", "asset_class": "stock", "qty_net": 10, "last_price": 200.0, "current_value": 2000.0, "weight_pct": 50.0, "dividend_yield": 1.5, "trailing_pe": 25.0},
        {"ticker": "KO", "asset_class": "stock", "qty_net": 40, "last_price": 50.0, "current_value": 2000.0, "weight_pct": 50.0, "dividend_yield": 3.0, "trailing_pe": 20.0},
    ])
    return {
        "computed_at": "2026-07-24 12:00:00",
        "portfolio_return": pd.Series([0.01, -0.005, 0.02], index=pd.date_range("2026-07-01", periods=3)),
        "benchmark_return": pd.Series([0.005, -0.002, 0.01], index=pd.date_range("2026-07-01", periods=3)),
        "positions": pos,
        "metrics": {
            "returns": {"portfolio_value": 4000.0, "total_pnl": 500.0, "cagr_pct": 12.5, "sharpe_ratio": 1.45},
            "market_risk": {"volatility_annual_pct": 14.2, "var_95": 120.0, "max_drawdown_pct": -8.5, "beta": 1.05, "benchmark_ticker": "SPY"},
            "concentration": {"hhi": 0.50, "effective_n_assets": 2.0}
        },
        "risk_contribution": {"component_var_pct": {"META": 60.0, "KO": 40.0}},
        "optimization": {
            "tickers": ["META", "KO"],
            "max_sharpe": {"weights": [0.4, 0.6], "sharpe": 1.65, "return": 0.15, "risk": 0.12},
            "min_vol": {"weights": [0.2, 0.8], "sharpe": 1.30, "return": 0.10, "risk": 0.09}
        }
    }

def test_report_exporter_pdf_and_excel(mock_risk_results):
    pdf_bytes = generate_pdf_factsheet(mock_risk_results, portfolio_name="Test Portfolio")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100

    dossier_bytes = generate_institutional_audit_dossier(mock_risk_results, portfolio_name="Test Portfolio")
    assert isinstance(dossier_bytes, bytes)
    assert len(dossier_bytes) > 10000

    excel_bytes = generate_excel_report(mock_risk_results, portfolio_name="Test Portfolio")
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 100

def test_smart_rebalancer_engine(mock_risk_results):
    res = compute_rebalancing_orders(
        mock_risk_results,
        target_mode="max_sharpe",
        new_cash_eur=1000.0,
        integer_shares=True
    )
    df_orders = res["orders"]
    summary = res["summary"]

    assert not df_orders.empty
    assert summary["target_total_value"] == 5000.0
    assert "action" in df_orders.columns

def test_ai_quant_advisor_engine(mock_risk_results):
    advisor_res = generate_quant_advisory_report(mock_risk_results)
    assert "health_score" in advisor_res
    assert "diagnostics" in advisor_res
    assert isinstance(advisor_res["diagnostics"], list)

def test_dividend_forecast_engine(mock_risk_results):
    div_res = compute_dividend_forecast(mock_risk_results["positions"])
    assert div_res["total_annual_dividends_eur"] > 0
    assert not div_res["monthly_forecast"].empty

def test_advisor_with_none_values():
    results_with_nones = {
        "metrics": {
            "returns": {"sharpe_ratio": None},
            "market_risk": {"beta": None, "volatility_annual_pct": None},
            "concentration": {"hhi": None, "effective_n_assets": None}
        },
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "qty_net": 10, "weight_pct": 50.0, "trailing_pe": None},
            {"ticker": "MSFT", "qty_net": 10, "weight_pct": 50.0, "trailing_pe": "N/A"}
        ]),
        "risk_contribution": {"component_var_pct": {"AAPL": None, "MSFT": 30.0}},
        "optimization": {"max_sharpe": {"sharpe": None}}
    }
    advisor_res = generate_quant_advisory_report(results_with_nones)
    assert 0 <= advisor_res["health_score"] <= 100
    assert isinstance(advisor_res["diagnostics"], list)
    assert advisor_res["summary"]["beta"] == 1.0


def test_advisor_page_targets_exist_on_disk():
    """Verifica che tutti i page_target generati dall'advisor esistano fisicamente in src/."""
    import os
    from core.workspace_manager import resolve_page_path

    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
    mock_results = {
        "metrics": {
            "returns": {"sharpe_ratio": 0.5},
            "market_risk": {"beta": 1.8, "volatility_annual_pct": 25.0},
            "concentration": {"hhi": 0.40, "effective_n_assets": 2.5}
        },
        "positions": pd.DataFrame([
            {"ticker": "NVDA", "qty_net": 100, "weight_pct": 60.0, "trailing_pe": 75.0},
            {"ticker": "AAPL", "qty_net": 50, "weight_pct": 40.0, "trailing_pe": 35.0}
        ]),
        "risk_contribution": {"component_var_pct": {"NVDA": 70.0, "AAPL": 30.0}},
        "optimization": {"max_sharpe": {"sharpe": 1.4}}
    }
    advisor_res = generate_quant_advisory_report(mock_results)
    assert len(advisor_res["diagnostics"]) > 0

    for d in advisor_res["diagnostics"]:
        pt = d.get("page_target")
        if pt:
            canonical = resolve_page_path(pt)
            full_path = os.path.join(src_dir, canonical)
            assert os.path.exists(full_path), f"Il file di pagina {canonical} (da {pt}) non esiste in {src_dir}"


