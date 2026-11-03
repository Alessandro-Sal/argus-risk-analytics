# ============================================================
# tests/test_master_pitchbook_pdf.py
# Unit tests for Institutional Family Office Master Pitchbook PDF
# ============================================================

import pytest

from core.fetcher import get_engine
from core.reporting.master_pitchbook_pdf import generate_master_family_office_pitchbook_pdf


def test_master_pitchbook_pdf_generation_valid():
    engine = get_engine()
    pdf_bytes = generate_master_family_office_pitchbook_pdf(
        engine=engine,
        portfolio_id=1,
        client_name="Test Family Office",
        profile_code="TEST-FO",
        reporting_year=2026,
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")


def test_master_pitchbook_pdf_with_defaults():
    engine = get_engine()
    pdf_bytes = generate_master_family_office_pitchbook_pdf(
        engine=engine,
        portfolio_id=1,
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")
