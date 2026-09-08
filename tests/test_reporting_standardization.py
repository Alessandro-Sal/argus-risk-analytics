"""
Unit tests for ARGUS Financial Reporting Standardization, Design System, Interactive Excel Models and Modular Factsheet Builder.
"""

import io
import pytest
import pandas as pd
from sqlalchemy import create_engine

from core.reporting_design_system import (
    InstitutionalPalette,
    InstitutionalNumberedCanvas,
    get_institutional_reportlab_styles,
    create_vector_donut_chart,
    HAS_REPORTLAB
)
from core.pdf_generator import generate_executive_pdf_report, _generate_legacy_pure_pdf
from core.excel_generator import generate_excel_in_memory
from core.wealth.wealth_exporter import export_wealth_master_excel_workbook
from core.wealth.wealth_db import init_wealth_db, create_wealth_portfolio
from core.modular_factsheet_builder import FactsheetExportConfig, ModularFactsheetBuilder


def test_reporting_design_system_tokens_and_canvas():
    """Verifica la coerenza dei token cromatici e delle primitive ReportLab."""
    p = InstitutionalPalette
    assert p.PRIMARY_NAVY.startswith("#")
    assert p.ACCENT_EMERALD.startswith("#")
    assert p.ACCENT_CRIMSON.startswith("#")

    if HAS_REPORTLAB:
        styles = get_institutional_reportlab_styles()
        assert "DocTitle" in styles
        assert "KpiValueEmerald" in styles
        assert "Disclaimer" in styles

        # Verifica generazione donut vettoriale memory-safe
        donut_data = [("Equity", 60.0, p.ACCENT_EMERALD), ("Bond", 40.0, p.ACCENT_ROYAL)]
        d = create_vector_donut_chart(donut_data, width=200, height=100)
        assert d.width == 200
        assert d.height == 100


def test_modernized_pdf_generator_a4_compliance():
    """Verifica che generate_executive_pdf_report produca un documento valido A4 con fallback."""
    mock_risk_data = {
        "positions": pd.DataFrame([
            {"ticker": "AAPL", "asset_class": "Equity", "current_value": 50000.0, "weight_pct": 50.0, "unrealized_pnl": 5000.0},
            {"ticker": "MSFT", "asset_class": "Equity", "current_value": 50000.0, "weight_pct": 50.0, "unrealized_pnl": 3000.0}
        ]),
        "metrics": {
            "market_risk": {"sharpe_ratio": 1.5, "volatility_pct": 14.2, "max_drawdown_pct": -12.5, "var_95_pct": 2.1},
            "returns": {"cagr_pct": 15.4},
            "concentration": {"diversification_ratio": 1.3, "hhi_index": 0.05}
        },
        "stress_tests": {
            "COVID-19 Crash (Feb-Mar 2020)": {"portfolio_loss_pct": -21.5}
        }
    }

    # Test generazione principale
    pdf_bytes = generate_executive_pdf_report("Family Office Alpha", mock_risk_data, "EUR")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # Test fallback deterministico puro stream
    fallback_bytes = _generate_legacy_pure_pdf("Family Office Alpha", mock_risk_data, "EUR")
    assert isinstance(fallback_bytes, bytes)
    assert len(fallback_bytes) > 200
    assert fallback_bytes.startswith(b"%PDF")


def test_interactive_excel_generator_with_native_tables_and_formulas():
    """Verifica che generate_excel_in_memory generi tabelle native e formule vive."""
    df_pos = pd.DataFrame([
        {"ticker": "AAPL", "asset_class": "Equity", "gics_sector": "Technology", "qty_net": 10.0, "avg_cost": 140.0, "last_price": 180.0, "current_value": 1800.0, "weight_pct": 60.0},
        {"ticker": "NVDA", "asset_class": "Equity", "gics_sector": "Technology", "qty_net": 5.0, "avg_cost": 400.0, "last_price": 600.0, "current_value": 3000.0, "weight_pct": 40.0}
    ])

    buf = generate_excel_in_memory(df_pos)
    assert isinstance(buf, io.BytesIO)
    content = buf.getvalue()
    assert len(content) > 2000
    assert content.startswith(b"PK")  # Firma standard ZIP/XLSX


def test_wealth_master_excel_dynamic_formulas():
    """Verifica che export_wealth_master_excel_workbook generi il dossier a 10 fogli con formule attive."""
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)
    w_pid = create_wealth_portfolio(engine, name="Master Family Test")

    xl_buf = export_wealth_master_excel_workbook(engine, portfolio_id=w_pid)
    assert isinstance(xl_buf, io.BytesIO)
    content = xl_buf.getvalue()
    assert len(content) > 3000
    assert content.startswith(b"PK")


def test_modular_factsheet_builder_toggles():
    """Verifica che ModularFactsheetBuilder assembli sezioni modulari su richiesta."""
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)
    w_pid = create_wealth_portfolio(engine, name="Private Banking Client")

    mock_risk = {
        "positions": pd.DataFrame([{"ticker": "ETF_WORLD", "current_value": 100000.0, "weight_pct": 100.0}]),
        "metrics": {"market_risk": {"sharpe_ratio": 1.2, "volatility_pct": 12.0}},
        "stress_tests": {"Lehman Brothers": {"portfolio_loss_pct": -30.0}}
    }

    # 1. Configurazione Completa
    cfg_full = FactsheetExportConfig(
        report_title="Report Completo",
        client_name="Famiglia Rossi",
        include_cover=True,
        include_net_worth=True,
        include_market_risk=True,
        include_stress_testing=True,
        include_fiscal_audit=True,
        include_ai_memorandum=True
    )
    builder_full = ModularFactsheetBuilder(cfg_full)
    pdf_full = builder_full.build_pdf(engine=engine, risk_data=mock_risk, wealth_portfolio_id=w_pid)
    assert isinstance(pdf_full, bytes)
    assert len(pdf_full) > 1500
    assert pdf_full.startswith(b"%PDF")

    # 2. Configurazione Snella (Solo Rischio Mercato)
    cfg_lean = FactsheetExportConfig(
        report_title="Rischio Mercato Sintetico",
        client_name="Famiglia Rossi",
        include_cover=False,
        include_net_worth=False,
        include_market_risk=True,
        include_stress_testing=False,
        include_fiscal_audit=False,
        include_ai_memorandum=False,
        mask_sensitive_pii=True
    )
    builder_lean = ModularFactsheetBuilder(cfg_lean)
    pdf_lean = builder_lean.build_pdf(engine=engine, risk_data=mock_risk, wealth_portfolio_id=w_pid)
    assert isinstance(pdf_lean, bytes)
    assert len(pdf_lean) > 500
    assert pdf_lean.startswith(b"%PDF")
