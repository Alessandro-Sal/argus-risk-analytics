# ============================================================
# tests/test_wealth_reporting_hub.py
# Unit tests for Wealth Reporting Hub & Multi-Format Exporters
# ============================================================

import pytest
import io
import json
import pandas as pd
from core.fetcher import get_engine
from core.wealth.wealth_reporting_hub import render_wealth_reporting_and_exports_hub
from core.wealth.wealth_exporter import export_wealth_master_excel_workbook
from core.quarterly_report_generator import generate_white_label_quarterly_pdf_report
from core.wealth.wealth_engine import (
    generate_advisory_pitchbook_pdf,
    generate_executive_tear_sheet_pdf,
    compute_fiscal_analytics
)
from core.voice_advisor_engine import generate_ai_voice_executive_briefing


def test_white_label_quarterly_pdf_generation():
    engine = get_engine()
    pdf_bytes = generate_white_label_quarterly_pdf_report(
        engine, portfolio_id=1, client_name="Family Office Test", quarter="Q1 2026"
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_advisory_pitchbook_pdf_generation():
    engine = get_engine()
    pdf_bytes = generate_advisory_pitchbook_pdf(engine, portfolio_id=1)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_executive_tear_sheet_pdf_generation():
    engine = get_engine()
    pdf_bytes = generate_executive_tear_sheet_pdf(engine, portfolio_id=1)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_master_excel_workbook_export():
    engine = get_engine()
    xl_buf = export_wealth_master_excel_workbook(engine, portfolio_id=1)
    assert isinstance(xl_buf, io.BytesIO)
    xl_bytes = xl_buf.getvalue()
    assert len(xl_bytes) > 2000
    # Check valid zip/xlsx signature (PK)
    assert xl_bytes.startswith(b"PK")


def test_parquet_and_csv_export_structures():
    engine = get_engine()
    from core.wealth.wealth_db import get_cashflow_records
    df_tx = get_cashflow_records(engine, portfolio_id=1)
    
    # Parquet
    pq_buf = io.BytesIO()
    df_tx.to_parquet(pq_buf, index=False)
    assert len(pq_buf.getvalue()) > 0

    # CSV
    csv_bytes = df_tx.to_csv(index=False).encode("utf-8")
    assert len(csv_bytes) > 0


def test_voice_script_generation_for_reporting_hub():
    engine = get_engine()
    vb = generate_ai_voice_executive_briefing(engine, portfolio_id=1, client_name="Family Office Test")
    assert "full_text_transcript" in vb
    assert len(vb["full_text_transcript"]) > 100
    assert "dialogue_script" in vb
    assert len(vb["dialogue_script"]) >= 2
