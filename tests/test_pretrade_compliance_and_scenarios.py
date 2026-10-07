# ==============================================================================
# tests/test_pretrade_compliance_and_scenarios.py
# ARGUS — Unit Tests for Pre-Trade Compliance, 2026 Macro Scenarios,
# CRO Institutional Dossier Batch Exporter & Data Vault File Encryption
# ==============================================================================

import json
import os
import tempfile
import zipfile
from datetime import datetime

import pandas as pd
import pytest

from core.compliance_gate import (
    ComplianceStatus,
    PreTradeComplianceConfig,
    PreTradeOrderRequest,
    PreTradeRiskGate,
)
from core.macro_stress_engine import evaluate_macro_stress_scenario, get_standard_macro_scenarios
from core.report_exporter import generate_cro_institutional_dossier_zip
from core.security_engine import ArgusDataVault
from core.trade_staging_blotter import StagedOrder, simulate_fix_routing

# ── 1. PRE-TRADE COMPLIANCE GATE TESTS ─────────────────────────────────────────


def test_compliance_gate_approved_order():
    gate = PreTradeRiskGate()
    req = PreTradeOrderRequest(
        order_id="ORD-001",
        symbol="AAPL",
        side="BUY",
        order_qty=100.0,
        limit_price=150.0,
        reference_price=150.0,
        adv_shares=50_000.0,
        available_cash_eur=50_000.0,
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is True
    assert verdict.status == ComplianceStatus.APPROVED
    assert verdict.notional_eur == 15_000.0
    assert len(verdict.audit_hash) == 64  # Valid SHA-256
    assert len(verdict.rejection_reasons) == 0


def test_compliance_gate_fat_finger_rejection():
    cfg = PreTradeComplianceConfig(max_notional_per_order_eur=100_000.0)
    gate = PreTradeRiskGate(cfg)
    req = PreTradeOrderRequest(
        order_id="ORD-FAT-01",
        symbol="MSFT",
        side="BUY",
        order_qty=1_000.0,
        limit_price=400.0,  # €400,000 > €100,000
        reference_price=400.0,
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is False
    assert verdict.status == ComplianceStatus.REJECTED_FAT_FINGER
    assert any("Fat-Finger" in r for r in verdict.rejection_reasons)


def test_compliance_gate_price_collar_rejection():
    cfg = PreTradeComplianceConfig(max_price_collar_pct=5.0)
    gate = PreTradeRiskGate(cfg)
    req = PreTradeOrderRequest(
        order_id="ORD-COL-01",
        symbol="NVDA",
        side="BUY",
        order_qty=10.0,
        limit_price=120.0,  # +20% deviation from reference 100.0
        reference_price=100.0,
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is False
    assert verdict.status == ComplianceStatus.REJECTED_COLLAR_BREACH
    assert any("collar" in r.lower() for r in verdict.rejection_reasons)


def test_compliance_gate_adv_limit_rejection():
    cfg = PreTradeComplianceConfig(max_adv_participation_pct=10.0)
    gate = PreTradeRiskGate(cfg)
    req = PreTradeOrderRequest(
        order_id="ORD-ADV-01",
        symbol="SMALLCAP",
        side="BUY",
        order_qty=2_000.0,
        limit_price=50.0,
        adv_shares=10_000.0,  # 2,000 / 10,000 = 20% > 10%
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is False
    assert verdict.status == ComplianceStatus.REJECTED_ADV_LIMIT
    assert any("ADV" in r for r in verdict.rejection_reasons)


def test_compliance_gate_insufficient_funds_rejection():
    gate = PreTradeRiskGate()
    req = PreTradeOrderRequest(
        order_id="ORD-CASH-01",
        symbol="SAP",
        side="BUY",
        order_qty=100.0,
        limit_price=180.0,  # €18,000 + 1% = €18,180
        available_cash_eur=10_000.0,  # shortfall
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is False
    assert verdict.status == ComplianceStatus.REJECTED_INSUFFICIENT_FUNDS
    assert any("insufficiente" in r.lower() for r in verdict.rejection_reasons)


def test_compliance_gate_restricted_symbol():
    cfg = PreTradeComplianceConfig(restricted_symbols=["SANCTIONED_CO", "BLOCKED_ASSET"])
    gate = PreTradeRiskGate(cfg)
    req = PreTradeOrderRequest(
        order_id="ORD-REST-01",
        symbol="SANCTIONED_CO",
        side="BUY",
        order_qty=10.0,
        limit_price=100.0,
    )
    verdict = gate.evaluate_order(req)
    assert verdict.passed is False
    assert verdict.status == ComplianceStatus.REJECTED_RESTRICTED_SYMBOL


def test_compliance_gate_batch_evaluation_cash_depletion():
    gate = PreTradeRiskGate()
    orders = [
        PreTradeOrderRequest("O1", "AAPL", "BUY", 50, 100.0),   # €5,000
        PreTradeOrderRequest("O2", "MSFT", "BUY", 40, 100.0),   # €4,000
        PreTradeOrderRequest("O3", "GOOGL", "BUY", 40, 100.0),  # €4,000
    ]
    # Total required ~€13,000 + buffer. Starting cash €8,500.
    verdicts = gate.evaluate_batch(orders, portfolio_cash=8_500.0)
    assert verdicts[0].passed is True  # €8,500 - €5,000 = €3,500 remaining
    assert verdicts[1].passed is False  # Needs €4,040 > €3,500 -> REJECTED (cash stays €3,500)
    assert verdicts[2].passed is False  # Needs €4,040 > €3,500 -> REJECTED


# ── 2. BLOTTER INTEGRATION TESTS ───────────────────────────────────────────────


def test_blotter_compliance_integration():
    staged = [
        StagedOrder(
            cl_ord_id="EMS-OK-01",
            symbol="AAPL",
            side="BUY",
            order_qty=10,
            order_type="LIMIT",
            limit_price=150.0,
        ),
        StagedOrder(
            cl_ord_id="EMS-BAD-02",
            symbol="MSFT",
            side="BUY",
            order_qty=10_000,
            order_type="LIMIT",
            limit_price=500.0,  # €5,000,000 > Fat-finger
        ),
    ]

    res = simulate_fix_routing(staged)
    df_exec = res["executed_dataframe"]
    summary = res["compliance_summary"]

    assert summary["total_orders"] == 2
    assert summary["approved_orders"] == 1
    assert summary["rejected_orders"] == 1
    assert summary["compliance_pass_rate_pct"] == 50.0

    rejected_row = df_exec[df_exec["ClOrdID"] == "EMS-BAD-02"].iloc[0]
    assert rejected_row["Status"] == "REJECTED"
    assert "REJECTED_FAT_FINGER" in rejected_row["Compliance Status"]


# ── 3. 2026 MACRO SCENARIOS TESTS ─────────────────────────────────────────────


def test_standard_macro_scenarios_2026_present():
    scenarios = get_standard_macro_scenarios()
    expected_new_keys = [
        "Global_Tariff_War_2026",
        "AI_CapEx_Bubble_Reset",
        "ECB_Inverted_Curve_Stagflation",
    ]
    for k in expected_new_keys:
        assert k in scenarios, f"Scenario {k} mancante in get_standard_macro_scenarios"
        sc = scenarios[k]
        assert "equity_shock_pct" in sc
        assert "volatility_multiplier" in sc
        assert sc["volatility_multiplier"] > 1.0


def test_evaluate_macro_stress_scenario_execution():
    df_pos = pd.DataFrame(
        [
            {"ticker": "SPY", "current_value": 60_000.0, "asset_class": "equity", "weight_pct": 60.0},
            {"ticker": "BND", "current_value": 40_000.0, "asset_class": "fixed_income", "weight_pct": 40.0},
        ]
    )
    res = evaluate_macro_stress_scenario("Global_Tariff_War_2026", df_positions=df_pos)
    assert "stressed_portfolio_value" in res
    assert res["stressed_portfolio_value"] < 100_000.0
    assert "estimated_pnl_eur" in res
    assert res["estimated_pnl_eur"] < 0.0


# ── 4. 1-CLICK CRO INSTITUTIONAL DOSSIER EXPORT TESTS ──────────────────────────


def test_generate_cro_institutional_dossier_zip():
    results = {
        "positions": pd.DataFrame(
            [
                {"ticker": "AAPL", "qty_net": 10.0, "avg_cost": 140.0, "last_price": 170.0, "current_value": 1700.0, "weight_pct": 0.50},
                {"ticker": "MSFT", "qty_net": 5.0, "avg_cost": 300.0, "last_price": 340.0, "current_value": 1700.0, "weight_pct": 0.50},
            ]
        ),
        "metrics": {
            "returns": {"portfolio_value": 3400.0, "cagr_pct": 12.5, "total_return_pct": 18.0, "sharpe_ratio": 1.45, "sortino_ratio": 1.82},
            "market_risk": {"max_drawdown_pct": 8.4, "var_cf_95": 0.021, "cvar_95": 0.032, "beta": 1.05},
        },
    }

    zip_bytes = generate_cro_institutional_dossier_zip(results, portfolio_name="Test Portfolio")
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 1000

    # Verify ZIP contents
    import io

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert any("Executive_Factsheet.html" in n for n in namelist)
        assert any("Financial_Model.xlsx" in n for n in namelist)
        assert "Star_Schema_BI/dim_assets.csv" in namelist
        assert "Star_Schema_BI/fact_positions.csv" in namelist
        assert "Star_Schema_BI/fact_portfolio_summary.csv" in namelist
        assert "00_Executive_Governance_Manifest.json" in namelist

        # Inspect manifest JSON
        manifest_raw = zf.read("00_Executive_Governance_Manifest.json").decode("utf-8")
        manifest = json.loads(manifest_raw)
        assert manifest["platform"] == "ARGUS Risk Analytics & Wealth Platform"
        assert manifest["version"] == "9.19.0"
        assert "audit_seal_sha256" in manifest
        assert len(manifest["audit_seal_sha256"]) == 64


# ── 5. ARGUS DATA VAULT FILE ENCRYPTION TESTS ─────────────────────────────────


def test_argus_data_vault_file_encryption_and_decryption():
    vault = ArgusDataVault.get_instance()
    original_text = "Sensitive SQLite Database Header or Private Financial Ledger Data €1,000,000"

    with tempfile.TemporaryDirectory() as tmpdir:
        src_file = os.path.join(tmpdir, "test_wallet.db")
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(original_text)

        # Encrypt file
        enc_file = vault.encrypt_file(src_file)
        assert os.path.exists(enc_file)
        assert enc_file.endswith(".argus_vault")

        with open(enc_file, "rb") as f:
            enc_data = f.read()
        assert original_text.encode("utf-8") not in enc_data  # Ciphertext hides original text

        # Decrypt file
        dec_file = vault.decrypt_file(enc_file)
        assert os.path.exists(dec_file)

        with open(dec_file, "r", encoding="utf-8") as f:
            dec_text = f.read()
        assert dec_text == original_text
