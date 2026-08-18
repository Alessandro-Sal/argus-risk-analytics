import pytest
import pandas as pd
from core.html_exporter import generate_interactive_html_report

def test_generate_interactive_html_report():
    sample_results = {
        "computed_at": "2026-08-05 12:00:00",
        "metrics": {
            "market_risk": {"var_95_param": 0.02},
            "returns": {"sharpe_ratio": 1.45, "cagr": 0.12}
        },
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "asset_class": "stock", "market_value": 5000.0, "weight_pct": 50.0, "unrealized_pnl": 500.0},
            {"ticker": "MSFT", "asset_class": "stock", "market_value": 5000.0, "weight_pct": 50.0, "unrealized_pnl": 300.0}
        ]),
        "portfolio_return": pd.Series([0.01, 0.02, -0.005], index=pd.date_range("2026-01-01", periods=3)),
        "benchmark_return": pd.Series([0.005, 0.01, -0.002], index=pd.date_range("2026-01-01", periods=3))
    }
    
    html = generate_interactive_html_report(sample_results)
    assert "<!DOCTYPE html>" in html
    assert "ARGUS Factsheet" in html
    assert "AAPL" in html
    assert "MSFT" in html
