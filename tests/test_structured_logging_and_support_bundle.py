# ===========================================================
# tests/test_structured_logging_and_support_bundle.py
# ARGUS — Risk Analytics & BI Platform
# Unit Tests for Structured Logging, PII Sanitization, Channels & Support Bundle
# ==========================================================

import os
import sys
import io
import json
import logging
import zipfile
import pytest
from pathlib import Path

from core.diagnostics import (
    sanitize_text,
    sanitize_dict,
    FinancialAndPIISanitizingFilter,
    StructuredJsonFormatter,
    setup_logging,
    get_system_logger,
    get_audit_logger,
    log_audit_event,
    measure_latency,
    get_hardware_and_environment_specs,
    get_database_integrity_details,
    get_recent_logs,
    generate_support_bundle,
)


def test_sanitize_text_financial_and_pii():
    """Verifica loscuramento di coordinate bancarie, codici fiscali, carte e importi."""
    raw = (
        "Cliente RSSMRA85M01H501Z con IBAN IT60X05428111101000000123456 e carta 4532-1234-5678-9012. "
        "Saldo disponibile: € 1.250.000,50 e balance = 45000 USD. "
        "Password: MySuperSecretPass123! con api_key: sk_test_99887766 and Bearer eyJhbGciOiJIUzI1Ni. "
        "Email: client@wealth.com e cell: +39 347 1234567."
    )
    sanitized = sanitize_text(raw)

    # Dati in chiaro devono essere oscurati
    assert "RSSMRA95M01H501Z" not in sanitized
    assert "[REDACTED_CF]" in sanitized

    assert "IT60X05428111101000000123456" not in sanitized
    assert "IT60" in sanitized and "3456" in sanitized and "*" in sanitized

    assert "4532-1234-5678-9012" not in sanitized
    assert "****-****-****-9012" in sanitized

    assert "1.250.000,50" not in sanitized
    assert "[REDACTED_FINANCIAL]" in sanitized

    assert "MySuperSecretPass123!" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized

    assert "sk_test_99887766" not in sanitized
    assert "eyJhbGciOiJIUzI1Ni" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized

    assert "client@wealth.com" not in sanitized
    assert "REDACTED_EMAIL]" in sanitized

    assert "347 1234567" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized


def test_sanitize_dict_recursive():
    """Verifica la sanificazione ricorsiva di dizionari e liste nidificate."""
    data = {
        "user": "RSSMRA85M01H501Z",
        "account": {"iban": "IT60X054281111101000000123456", "saldo": 50000.0},
        "credentials": {"password": "SecretPass!", "api_key": "key_abc123"},
        "transactions": [
            {"amount": "1500  ", "note": "Bonifico da IT60X0542811111101000000123456"},
            {"recipient_email": "tax@advisor.it"}
        ]
    }
    clean = sanitize_dict(data)

    assert clean["user"] == "[REDACTED_CF]"
    assert "IT60" in clean["account"]["iban"] and "*" in clean["account"]["iban"]
    assert clean["account"]["saldo"] == "[REDACTED_FINANCIAL]"
    assert clean["credentials"]["password"] == "[REDACTED_SECRET]"
    assert clean["credentials"]["api_key"] == "[REDACTED_SECRET]"
    assert clean["transactions"][0]["amount"] == "[REDACTED_FINANCIAL]"
    assert clean["transactions"][1]["recipient_email"] == "[REDACTED_EMAIL]"


def test_financial_and_pii_sanitizing_filter():
    """Verifica che il filtro logging alteri il LogRecord prima del rendering."""
    s_filter = FinancialAndPIISanitizingFilter()
    record = logging.LogRecord(
        name="argus.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Accesso conto IBAN IT60X0542811111101000000123456 per CF RSSMRA85M01H501Z con saldo € 900.000",
        args=(),
        exc_info=None
    )
    record.secret_token = "my_secret_token_123"

    assert s_filter.filter(record) is True
    assert "RSSMRA85M01H501Z" not in record.msg
    assert "[REDACTED_CF]" in record.msg
    assert "900.000" not in record.msg
    assert "[REDACTED_FINANCIAL]" in record.msg
    assert record.secret_token == "[REDACTED_SECRET]"


def test_structured_json_formatter():
    """Verifica che il formatter generi una riga JSON valida con tutti i campi standard."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="argus.test",
        level=logging.WARNING,
        pathname="core/diagnostics.py",
        lineno=42,
        msg="Connessione al database ripristinata per saldo: 15000 EUR",
        args=(),
        exc_info=None
    )
    record.execution_time_ms = 14.85
    record.custom_metric = "db_reconnect"

    formatted_str = formatter.format(record)
    assert "\n" not in formatted_str.strip()  # Single-line JSONL

    payload = json.loads(formatted_str)
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "argus.test"
    assert payload["module"] == "diagnostics"
    assert payload["line"] == 42
    assert payload["execution_time_ms"] == 14.85
    assert "timestamp" in payload
    assert "15000 EUR" not in payload["message"]
    assert "[REDACTED_FINANCIAL]" in payload["message"]
    assert payload["extra"]["custom_metric"] == "db_reconnect"


def test_structured_json_formatter_exception():
    """Verifica che le eccezioni e gli stack trace vengano serializzati in JSON."""
    formatter = StructuredJsonFormatter()
    try:
        raise ValueError("Test failure con secret password: mypassword123")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="argus.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=99,
            msg="Errore irreversibile durante il calcolo",
            args=(),
            exc_info=exc_info
        )
        payload = json.loads(formatter.format(record))
        assert payload["level"] == "ERROR"
        assert payload["error_type"] == "ValueError"
        assert "stack_trace" in payload
        assert "mypassword123" not in payload["stack_trace"]
        assert "[REDACTED_SECRET]" in payload["stack_trace"]



def test_setup_logging_and_channel_separation():
    """Verifica la separazione netta tra canale System e canale Audit."""
    cfg = setup_logging()
    assert cfg["status"] in ("initialized", "already_initialized")

    sys_logger = get_system_logger("argus.system.test")
    sys_logger.info("System diagnostic test event - I/O normal")

    log_audit_event(
        action="UPDATE_PORTFOLIO",
        entity_type="PORTFOLIO",
        entity_id="99",
        details={"notes": "Ribilanciamento effettuato per saldo: € 50.000"},
        status="SUCCESS"
    )

    from core.diagnostics import SYSTEM_LOG_PATH, AUDIT_LOG_PATH
    assert SYSTEM_LOG_PATH.exists()
    assert AUDIT_LOG_PATH.exists()

    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
        audit_content = f.read()
    assert "UPDATE_PORTFOLIO" in audit_content
    assert "PORTFOLIO:99" in audit_content
    assert "[REDACTED_FINANCIAL]" in audit_content
    assert "50.000" not in audit_content



def test_measure_latency_decorator():
    """Verifica che il decorator tracci i millisecondi di esecuzione computazionale."""
    @measure_latency(metric_name="test_computation")
    def compute_fast(x: int) -> int:
        return x * 2

    res = compute_fast(21)
    assert res == 42

    @measure_latency(metric_name="test_failure")
    def compute_fail():
        raise RuntimeError("Simulated failure")

    with pytest.raises(RuntimeError):
        compute_fail()


def test_get_hardware_and_environment_specs():
    """Verifica la raccolta delle specifiche hardware e software."""
    specs = get_hardware_and_environment_specs()
    assert "timestamp_utc" in specs
    assert "python_version" in specs
    assert "cpu" in specs
    assert "memory" in specs
    assert "packages" in specs
    assert "pandas" in specs["packages"]
    assert "numpy" in specs["packages"]
    assert "streamlit" in specs["packages"]


def test_get_database_integrity_details():
    """Verifica lispezione dello stato dei database locali."""
    report = get_database_integrity_details()
    assert isinstance(report, dict)
    for db_name, status in report.items():
        if status.get("exists"):
            assert "integrity" in status
            assert "schema_version" in status
            assert "tables" in status


def test_get_recent_logs():
    """Verifica la lettura a ritroso degli ultimi log sanificati."""
    sys_log = get_system_logger()
    sys_log.info("Log history test entry 1")
    sys_log.warning("Log history test entry 2")

    logs = get_recent_logs(channel="system", limit=10, min_level="INFO")
    assert isinstance(logs, list)
    if logs:
        assert "level" in logs[0]
        assert "message" in logs[0]
        assert "timestamp" in logs[0]


def test_generate_support_bundle():
    """Verifica la generazione dellarchivio compresso ZIP del Support Bundle."""
    bundle_bytes = generate_support_bundle(include_logs=True, max_log_lines=50)
    assert isinstance(bundle_bytes, bytes)
    assert len(bundle_bytes) > 0

    zip_buf = io.BytesIO(bundle_bytes)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        expected_files = [
            "system_diagnostics.json",
            "environment_and_hardware.json",
            "database_status.json",
            "system_logs.sanitized.jsonl",
            "audit_logs.sanitized.jsonl",
            "README_SUPPORT.txt"
        ]
        for ef in expected_files:
            assert ef in namelist, f"File mancante nel Support Bundle: {ef}"


        diag_data = json.loads(zf.read("system_diagnostics.json").decode("utf-8"))
        assert "overall_status" in diag_data
        assert "health_score" in diag_data

        env_data = json.loads(zf.read("environment_and_hardware.json").decode("utf-8"))
        assert "os_platform" in env_data

        readme = zf.read("README_SUPPORT.txt").decode("utf-8")
        assert "ARGUS" in readme
        assert "PRIVACY & SANITIZATION ASSURANCE" in readme
