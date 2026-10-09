# ============================================================
# tests/test_tax_history_engine.py
# Unit tests for ARGUS Tax History Engine, Carryforward Losses & Reconciliation
# ============================================================

import io
import json
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy import text as sqlt

from core.wealth.tax_history_engine import (
    TaxDeclaration,
    TaxLossCarryforward,
    TaxVerificationDocument,
    build_730_predisposition_and_variance_audit,
    build_triangular_tax_audit,
    compute_broker_annual_capital_gains,
    compute_crypto_tax_reporting,
    compute_fire_effective_tax_drag,
    compute_fiscal_reform_2026_etf_harmonization,
    compute_fiscal_reform_multiyear_projection,
    compute_pension_tax_deduction_optimizer,
    compute_ravvedimento_operoso,
    compute_tax_loss_harvesting_signals,
    delete_declaration,
    delete_tax_loss,
    delete_verification_document,
    detect_tax_document_type,
    export_wealth_and_tax_backup_bundle,
    generate_730_precompilata_actionable_guide,
    generate_commercialista_tax_dossier_html,
    generate_f24_payment_slip,
    generate_official_f24_facsimile_html,
    generate_sample_730_json,
    get_declarations,
    get_fiscal_deadlines_calendar,
    get_tax_losses,
    get_unified_tax_document_registry,
    get_verification_documents,
    import_wealth_and_tax_backup_bundle,
    parse_730_pdf_or_json,
    parse_ade_notice_36bis,
    parse_ade_precompilata,
    parse_bank_statement_rw,
    parse_broker_tax_report,
    parse_building_renovation,
    parse_certificazione_unica,
    parse_medical_expenses,
    parse_mortgage_interest,
    parse_rent_expense,
    parse_universal_tax_document,
    reconcile_with_portfolio,
    record_declaration,
    record_tax_loss,
    record_verification_document,
    sync_tax_events_to_cashflow,
    update_tax_loss_offset,
)
from core.wealth.wealth_db import init_wealth_db


@pytest.fixture
def memory_db():
    """Crea un database SQLite in memoria con lo schema wealth inizializzato."""
    engine = create_engine("sqlite:///:memory:")
    init_wealth_db(engine)
    return engine


class TestTaxDeclarationsCRUD:
    def test_record_and_get_declaration(self, memory_db):
        data = {
            "profile_id": "test_user_1",
            "tax_year": 2024,
            "filing_year": 2025,
            "model_type": "730_ORDINARIO",
            "protocol_id": "PROTO-2025-00129",
            "gross_income": 45000.50,
            "taxable_income": 42000.00,
            "net_tax_irpef": 11500.20,
            "capital_gains_declared": 3200.00,
            "capital_losses_offset": 1200.00,
            "substitute_tax_paid": 520.00,
            "ivafe_paid": 68.40,
            "foreign_assets_val": 15000.00,
            "notes": "Test dichiarazione 730 2024",
            "source_filename": "modello_730_2025.pdf",
        }

        decl_id = record_declaration(memory_db, data)
        assert decl_id > 0

        # Recupera dichiarazioni
        decls = get_declarations(memory_db, profile_id="test_user_1")
        assert len(decls) == 1
        d = decls[0]
        assert d["tax_year"] == 2024
        assert d["model_type"] == "730_ORDINARIO"
        assert d["gross_income"] == 45000.50
        assert d["capital_gains_declared"] == 3200.00
        assert d["substitute_tax_paid"] == 520.00

    def test_update_existing_declaration_upsert(self, memory_db):
        data = {
            "profile_id": "test_user_2",
            "tax_year": 2024,
            "model_type": "REDDITI_PF",
            "capital_gains_declared": 5000.0,
            "notes": "Prima versione",
        }
        id1 = record_declaration(memory_db, data)

        # Aggiornamento con lo stesso profile_id, tax_year e model_type
        data_update = {
            "profile_id": "test_user_2",
            "tax_year": 2024,
            "model_type": "REDDITI_PF",
            "capital_gains_declared": 6500.0,
            "notes": "Versione rettificata",
        }
        id2 = record_declaration(memory_db, data_update)
        assert id1 == id2

        decls = get_declarations(memory_db, profile_id="test_user_2", tax_year=2024)
        assert len(decls) == 1
        assert decls[0]["capital_gains_declared"] == 6500.0
        assert decls[0]["notes"] == "Versione rettificata"

    def test_delete_declaration(self, memory_db):
        data = {
            "profile_id": "del_profile",
            "tax_year": 2023,
            "model_type": "730_ORDINARIO",
        }
        decl_id = record_declaration(memory_db, data)
        assert delete_declaration(memory_db, decl_id) is True
        assert len(get_declarations(memory_db, profile_id="del_profile")) == 0


class TestTaxLossCarryforward:
    def test_record_loss_default_expiration(self, memory_db):
        # Regola quadriennale: generazione 2021 -> scadenza 2025
        data = {
            "profile_id": "carry_user",
            "generation_year": 2021,
            "initial_loss_amount": 2000.0,
            "offset_amount": 500.0,
            "is_officially_filed": True,
            "broker_source": "DEGIRO",
        }
        loss_id = record_tax_loss(memory_db, data)
        assert loss_id > 0

        losses = get_tax_losses(memory_db, profile_id="carry_user", current_year=2024)
        assert len(losses) == 1
        l = losses[0]
        assert l["expiration_year"] == 2025
        assert l["remaining_amount"] == 1500.0
        assert l["status"] == "ACTIVE"
        assert l["is_officially_filed"] is True

    def test_loss_expired_after_four_years(self, memory_db):
        # Minusvalenza generata nel 2019 con scadenza nel 2023. Se verificata nel 2024, è EXPIRED
        data = {
            "profile_id": "exp_user",
            "generation_year": 2019,
            "initial_loss_amount": 1000.0,
            "current_year": 2024,
        }
        record_tax_loss(memory_db, data)

        losses = get_tax_losses(memory_db, profile_id="exp_user", current_year=2024)
        assert len(losses) == 1
        assert losses[0]["expiration_year"] == 2023
        assert losses[0]["status"] == "EXPIRED"

    def test_partially_offset_and_exhausted(self, memory_db):
        data = {
            "profile_id": "offset_user",
            "generation_year": 2023,
            "initial_loss_amount": 3000.0,
            "offset_amount": 1000.0,
        }
        loss_id = record_tax_loss(memory_db, data)

        # Compensa ulteriori 1500
        assert update_tax_loss_offset(memory_db, loss_id, 1500.0) is True
        losses = get_tax_losses(memory_db, profile_id="offset_user")
        assert losses[0]["offset_amount"] == 2500.0
        assert losses[0]["remaining_amount"] == 500.0
        assert losses[0]["status"] == "ACTIVE"

        # Compensa i restanti 500 -> EXHAUSTED
        assert update_tax_loss_offset(memory_db, loss_id, 500.0) is True
        losses = get_tax_losses(memory_db, profile_id="offset_user")
        assert losses[0]["offset_amount"] == 3000.0
        assert losses[0]["remaining_amount"] == 0.0
        assert losses[0]["status"] == "EXHAUSTED"

    def test_delete_tax_loss(self, memory_db):
        loss_id = record_tax_loss(
            memory_db,
            {"profile_id": "del_loss_user", "generation_year": 2022, "initial_loss_amount": 400.0},
        )
        assert delete_tax_loss(memory_db, loss_id) is True
        assert len(get_tax_losses(memory_db, profile_id="del_loss_user")) == 0


class TestTax730Parser:
    def test_parse_json_dict(self):
        input_data = {
            "tax_year": 2024,
            "modello": "730_ORDINARIO",
            "protocollo": "123456789012345678",
            "reddito_complessivo": "48.250,50",
            "reddito_imponibile": "45.000,00",
            "imposta_netta": "12.300,00",
            "plusvalenze_dichiarate": "1.500,00",
            "minusvalenze_compensate": "500,00",
            "rigo_321": "260,00",
            "rigo_307": "34,20",
            "quadro_rw_valore_finale": "25.000,00",
        }
        res = parse_730_pdf_or_json(input_data)
        assert res["tax_year"] == 2024
        assert res["gross_income"] == 48250.50
        assert res["taxable_income"] == 45000.00
        assert res["capital_gains_declared"] == 1500.00
        assert res["capital_losses_offset"] == 500.00
        assert res["substitute_tax_paid"] == 260.00
        assert res["ivafe_paid"] == 34.20
        assert res["foreign_assets_val"] == 25000.00
        assert res["protocol_id"] == "123456789012345678"

    def test_parse_text_payload_730(self):
        sample_text = """
        MODELLO 730/2025 redditi 2024
        MINISTERO DELL'ECONOMIA E DELLE FINANZE - AGENZIA DELLE ENTRATE
        Protocollo Telematico: 2506241029384756100234
        REDDITO COMPLESSIVO: 54.300,00
        REDDITO IMPONIBILE: 51.200,00
        IMPOSTA NETTA: 14.850,00
        Totale Plusvalenze T11: 3.400,00
        Minusvalenze Compensate T13: 1.200,00
        Rigo 321 Imposta Sostitutiva Quadro T: 572,00
        Rigo 307 IVAFE: 68,40
        Quadro W Valore Finale: 34.200,00
        """
        res = parse_730_pdf_or_json(sample_text, filename="dichiarazione_2024.txt")
        assert res["tax_year"] == 2024
        assert res["filing_year"] == 2025
        assert res["model_type"] == "730_ORDINARIO"
        assert res["protocol_id"] == "2506241029384756100234"
        assert res["gross_income"] == 54300.00
        assert res["taxable_income"] == 51200.00
        assert res["net_tax_irpef"] == 14850.00
        assert res["capital_gains_declared"] == 3400.00
        assert res["capital_losses_offset"] == 1200.00
        assert res["substitute_tax_paid"] == 572.00
        assert res["ivafe_paid"] == 68.40
        assert res["foreign_assets_val"] == 34200.00

    def test_parse_official_730_2026_layout(self):
        sample_730_2026 = """
        MODELLO 730/2026 redditi 2025
        MINISTERO DELL'ECONOMIA E DELLE FINANZE - AGENZIA DELLE ENTRATE
        CODICE FISCALE DEL CONTRIBUENTE: RSSMRA85M01H501Z
        COGNOME E NOME: ROSSI MARIO
        Protocollo Telematico: 09064865516 - 0001069
        REDDITO COMPLESSIVO: 8.299,00
        REDDITO IMPONIBILE: 8.299,00
        IMPOSTA NETTA: 1.131,00
        Rigo 321 Imposta Sostitutiva: 206,00
        Totale Plusvalenze: 792,31
        Rigo 307 IVAFE: 53,00
        Quadro W Valore Finale: 26.500,00
        """
        res = parse_730_pdf_or_json(sample_730_2026, filename="730_2026_sample.txt")
        assert res["tax_year"] == 2025
        assert res["filing_year"] == 2026
        assert res["model_type"] == "730_ORDINARIO"
        assert res["protocol_id"] == "09064865516 - 0001069"
        assert res["gross_income"] == 8299.00
        assert res["taxable_income"] == 8299.00
        assert res["net_tax_irpef"] == 1131.00
        assert res["substitute_tax_paid"] == 206.00
        assert res["capital_gains_declared"] == 792.31
        assert res["ivafe_paid"] == 53.00
        assert res["foreign_assets_val"] == 26500.00
        assert "ROSSI" in res["notes"]
        assert "RSSMRA85M01H501Z" in res["notes"]

    def test_parse_official_730_2024_layout(self):
        sample_730_2024 = """
        MODELLO 730/2024 redditi 2023
        MINISTERO DELL'ECONOMIA E DELLE FINANZE - AGENZIA DELLE ENTRATE
        CODICE FISCALE DEL CONTRIBUENTE: RSSMRA85M01H501Z
        COGNOME E NOME: ROSSI MARIO
        Protocollo Telematico: 12454842525 - 0000472
        REDDITO COMPLESSIVO: 20.500,00
        REDDITO IMPONIBILE: 20.500,00
        IMPOSTA NETTA: 2.216,00
        Rigo 321 Imposta Sostitutiva: 0,00
        Totale Plusvalenze: 0,00
        Rigo 307 IVAFE: 17,00
        Quadro W Valore Finale: 8.500,00
        """
        res = parse_730_pdf_or_json(sample_730_2024, filename="730_2024_sample.txt")
        assert res["tax_year"] == 2023
        assert res["filing_year"] == 2024
        assert res["model_type"] == "730_ORDINARIO"
        assert res["protocol_id"] == "12454842525 - 0000472"
        assert res["gross_income"] == 20500.00
        assert res["taxable_income"] == 20500.00
        assert res["net_tax_irpef"] == 2216.00
        assert res["substitute_tax_paid"] == 0.00
        assert res["capital_gains_declared"] == 0.00
        assert res["ivafe_paid"] == 17.00
        assert res["foreign_assets_val"] == 8500.00
        assert "ROSSI" in res["notes"]

    def test_parse_official_730_2025_layout(self):
        sample_730_2025 = """
        MODELLO 730/2025 redditi 2024
        MINISTERO DELL'ECONOMIA E DELLE FINANZE - AGENZIA DELLE ENTRATE
        CODICE FISCALE DEL CONTRIBUENTE: RSSMRA85M01H501Z
        COGNOME E NOME: ROSSI MARIO
        Protocollo Telematico: 11423143672 - 0000686
        REDDITO COMPLESSIVO: 22.716,00
        REDDITO IMPONIBILE: 22.716,00
        IMPOSTA NETTA: 2.714,00
        Rigo 321 Imposta Sostitutiva: 115,00
        Totale Plusvalenze: 442,31
        Rigo 307 IVAFE: 34,00
        Quadro W Valore Finale: 17.000,00
        """
        res = parse_730_pdf_or_json(sample_730_2025, filename="730_2025_sample.txt")
        assert res["tax_year"] == 2024
        assert res["filing_year"] == 2025
        assert res["model_type"] == "730_ORDINARIO"
        assert res["protocol_id"] == "11423143672 - 0000686"
        assert res["gross_income"] == 22716.00
        assert res["taxable_income"] == 22716.00
        assert res["net_tax_irpef"] == 2714.00
        assert res["substitute_tax_paid"] == 115.00
        assert res["capital_gains_declared"] == 442.31
        assert res["ivafe_paid"] == 34.00
        assert res["foreign_assets_val"] == 17000.00
        assert "ROSSI" in res["notes"]


class TestReconciliationEngine:
    def test_reconcile_with_art_36_bis_unfiled_risk(self, memory_db):
        profile_id = "rec_user_risk"
        tax_year = 2024

        # Registra dichiarazione
        record_declaration(
            memory_db,
            {
                "profile_id": profile_id,
                "tax_year": tax_year,
                "capital_gains_declared": 2000.0,
                "capital_losses_offset": 1000.0,
                "substitute_tax_paid": 260.0,
            },
        )

        # Minusvalenza NON formalmente dichiarata in Anagrafe Tributaria (is_officially_filed=False)
        record_tax_loss(
            memory_db,
            {
                "profile_id": profile_id,
                "generation_year": 2023,
                "initial_loss_amount": 1500.0,
                "offset_amount": 0.0,
                "is_officially_filed": False,
                "broker_source": "DEGIRO",
            },
        )

        portfolio_data = {
            "capital_gains": 2000.0,
            "capital_losses": 0.0,
            "foreign_assets_val": 10000.0,
            "ivafe_est": 20.0,
        }

        report = reconcile_with_portfolio(memory_db, profile_id=profile_id, tax_year=tax_year, portfolio_data=portfolio_data)

        # Verifica scostamenti
        assert report.delta_capital_gains == 0.0
        assert report.total_unfiled_losses == 1500.0

        # Verifica allerta e calcolo sanzione 36-bis
        # Imposta recuperata: 1500 * 0.26 = 390€
        # Sanzione 30%: 390 * 0.30 = 117€
        # Interessi 5%: 390 * 0.05 = 19.50€
        # Totale: 526.50€
        assessment = report.art_36_bis_risk_assessment
        assert assessment["has_risk"] is True
        assert assessment["tax_recovery_base_26pct"] == 390.00
        assert assessment["sanzione_amministrativa_30pct"] == 117.00
        assert assessment["total_potential_liability"] == 526.50

        # Verifica presenza dell'alert di tipo 'danger'
        danger_alerts = [a for a in report.alerts if a["type"] == "danger" and "36-bis" in a["title"]]
        assert len(danger_alerts) >= 1

    def test_reconcile_with_expiring_losses_warning(self, memory_db):
        profile_id = "exp_warning_user"
        tax_year = 2024

        # Minusvalenza generata nel 2020: scade nel 2024 (2020 + 4 = 2024)
        record_tax_loss(
            memory_db,
            {
                "profile_id": profile_id,
                "generation_year": 2020,
                "initial_loss_amount": 800.0,
                "offset_amount": 0.0,
                "is_officially_filed": True,
            },
        )

        report = reconcile_with_portfolio(memory_db, profile_id=profile_id, tax_year=tax_year, portfolio_data={})

        assert report.total_expiring_losses == 800.0
        exp_alerts = [a for a in report.alerts if a["code"] == "EXPIRING_LOSS_FOUR_YEAR_LIMIT"]
        assert len(exp_alerts) == 1
        assert "€ 800,00" in exp_alerts[0]["title"]

    def test_reconcile_tax_loss_harvesting_optimization(self, memory_db):
        profile_id = "harvest_user"
        tax_year = 2024

        # Plusvalenze attive sul portafoglio di 4.000€
        portfolio_data = {
            "capital_gains": 4000.0,
            "capital_losses": 0.0,
            "foreign_assets_val": 20000.0,
            "ivafe_est": 40.0,
        }

        # Zainetto fiscale capiente di 2.500€
        record_tax_loss(
            memory_db,
            {
                "profile_id": profile_id,
                "generation_year": 2022,
                "initial_loss_amount": 2500.0,
                "offset_amount": 0.0,
                "is_officially_filed": True,
            },
        )

        report = reconcile_with_portfolio(memory_db, profile_id=profile_id, tax_year=tax_year, portfolio_data=portfolio_data)

        # Risparmio potenziale 26% su 2500€ = 650.00€
        assert len(report.harvesting_opportunities) == 1
        opp = report.harvesting_opportunities[0]
        assert opp["offset_potential"] == 2500.0
        assert opp["tax_savings_eur"] == 650.0

        opt_alerts = [a for a in report.alerts if a["type"] == "optimization"]
        assert len(opt_alerts) >= 1
        assert "€ 650,00" in opt_alerts[0]["title"]


class TestFiscalExtensions:
    def test_compute_ravvedimento_operoso_sprint_and_breve(self):
        # Ritardo di 10 giorni -> Sprint (0.1% * 10 = 1.0%)
        res_sprint = compute_ravvedimento_operoso(unpaid_tax_amount=1000.0, days_delayed=10)
        assert "Sprint" in res_sprint["bracket_name"]
        assert res_sprint["penalty_rate_pct"] == pytest.approx(1.0, rel=1e-3)
        assert res_sprint["reduced_penalty"] == pytest.approx(10.0, abs=0.1)
        assert res_sprint["ordinary_penalty_30pct"] == 300.0
        assert res_sprint["net_savings_eur"] > 280.0

        # Ritardo di 25 giorni -> Breve (1.5%)
        res_breve = compute_ravvedimento_operoso(unpaid_tax_amount=1000.0, days_delayed=25)
        assert "Breve" in res_breve["bracket_name"]
        assert res_breve["penalty_rate_pct"] == 1.5
        assert res_breve["reduced_penalty"] == 15.0

    def test_compute_ravvedimento_operoso_lungo_and_biennale(self):
        # Ritardo di 120 giorni -> Lungo (3.75%)
        res_lungo = compute_ravvedimento_operoso(unpaid_tax_amount=2000.0, days_delayed=120)
        assert "Lungo" in res_lungo["bracket_name"]
        assert res_lungo["penalty_rate_pct"] == 3.75
        assert res_lungo["reduced_penalty"] == 75.0

        # Ritardo di 400 giorni -> Biennale (~4.29%)
        res_biennale = compute_ravvedimento_operoso(unpaid_tax_amount=2000.0, days_delayed=400)
        assert "Biennale" in res_biennale["bracket_name"]
        assert res_biennale["penalty_rate_pct"] == pytest.approx(4.286, abs=0.01)

    def test_compute_ravvedimento_operoso_ivafe_f24(self):
        res_ivafe = compute_ravvedimento_operoso(unpaid_tax_amount=500.0, days_delayed=45, tax_type="IVAFE")
        assert res_ivafe["tax_type"] == "IVAFE"
        codes = [row["codice_tributo"] for row in res_ivafe["f24_rows"]]
        assert "4043" in codes  # Imposta IVAFE
        assert "8943" in codes  # Sanzione IVAFE
        assert "1943" in codes  # Interessi IVAFE

    def test_compute_broker_annual_capital_gains(self):
        # Dataset con acquisti nel 2023 e vendite nel 2024
        df_tx = pd.DataFrame([
            {"tx_id": 1, "tx_date": "2023-05-10", "ticker": "AAPL", "tx_type": "buy", "quantity": 10, "price": 150.0, "currency": "EUR"},
            {"tx_id": 2, "tx_date": "2024-03-15", "ticker": "AAPL", "tx_type": "sell", "quantity": 10, "price": 180.0, "currency": "EUR"}, # +300 EUR gain
            {"tx_id": 3, "tx_date": "2023-06-01", "ticker": "MSFT", "tx_type": "buy", "quantity": 5, "price": 300.0, "currency": "EUR"},
            {"tx_id": 4, "tx_date": "2024-08-20", "ticker": "MSFT", "tx_type": "sell", "quantity": 5, "price": 280.0, "currency": "EUR"}, # -100 EUR loss
        ])

        fiscal_2024 = compute_broker_annual_capital_gains(df_tx, tax_year=2024)
        assert fiscal_2024["status"] == "success"
        assert fiscal_2024["trades_count"] == 2
        assert fiscal_2024["gross_capital_gains"] == 300.0
        assert fiscal_2024["gross_capital_losses"] == 100.0
        assert fiscal_2024["net_gain"] == 200.0
        assert fiscal_2024["substitute_tax_estimate"] == pytest.approx(52.0, abs=0.01) # 200 * 0.26
        assert len(fiscal_2024["ticker_breakdown"]) == 2

    def test_generate_sample_730_json(self):
        json_str = generate_sample_730_json(tax_year=2024)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["tax_year"] == 2024
        assert parsed["filing_year"] == 2025
        assert parsed["model_type"] == "730_ORDINARIO"
        assert "capital_gains_declared" in parsed
        assert "substitute_tax_paid" in parsed


class TestTaxVerificationDocumentsCRUD:
    def test_record_and_get_verification_doc(self, memory_db):
        data = {
            "profile_id": "user_test",
            "tax_year": 2024,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "protocol_or_code": "PROFORMA-DEGIRO-2024",
            "gross_amount": 1335.0,
            "net_taxable_amount": 442.0,
            "tax_withheld_or_due": 115.0,
            "secondary_amount": 34.0,
            "asset_monitoring_val": 23563.0,
            "notes": "Rendiconto Degiro 2024",
            "source_filename": "degiro_2024.pdf",
        }
        doc_id = record_verification_document(memory_db, data)
        assert doc_id > 0

        docs = get_verification_documents(memory_db, profile_id="user_test", tax_year=2024)
        assert len(docs) == 1
        assert docs[0]["doc_type"] == "BROKER_REPORT"
        assert docs[0]["gross_amount"] == 1335.0
        assert docs[0]["net_taxable_amount"] == 442.0
        assert docs[0]["tax_withheld_or_due"] == 115.0
        assert docs[0]["secondary_amount"] == 34.0

    def test_update_verification_doc_upsert(self, memory_db):
        data1 = {
            "profile_id": "user_test",
            "tax_year": 2024,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "protocol_or_code": "PROFORMA-DEGIRO-2024",
            "gross_amount": 1000.0,
        }
        id1 = record_verification_document(memory_db, data1)

        # Update with new values
        data2 = {
            "profile_id": "user_test",
            "tax_year": 2024,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "protocol_or_code": "PROFORMA-DEGIRO-2024",
            "gross_amount": 1335.0,
            "tax_withheld_or_due": 115.0,
        }
        id2 = record_verification_document(memory_db, data2)
        assert id1 == id2

        docs = get_verification_documents(memory_db, profile_id="user_test", tax_year=2024)
        assert len(docs) == 1
        assert docs[0]["gross_amount"] == 1335.0
        assert docs[0]["tax_withheld_or_due"] == 115.0

    def test_delete_verification_doc(self, memory_db):
        data = {
            "profile_id": "user_test",
            "tax_year": 2020,
            "doc_type": "CU",
            "issuer_name": "AZIENDA DIRITTO STUDIO",
            "protocol_or_code": "CU-ERGO-2020",
        }
        doc_id = record_verification_document(memory_db, data)
        assert len(get_verification_documents(memory_db, profile_id="user_test")) == 1

        deleted = delete_verification_document(memory_db, doc_id)
        assert deleted is True
        assert len(get_verification_documents(memory_db, profile_id="user_test")) == 0


class TestUniversalTaxParsers:
    def test_detect_tax_document_types(self):
        assert detect_tax_document_type("CERTIFICAZIONE UNICA 2021 RELATIVA ALL'ANNO 2020") == "CERTIFICAZIONE_UNICA"
        assert detect_tax_document_type("", filename="CUK_T210218120139105620004585_RSSMRA85M01H501Z.pdf") == "CERTIFICAZIONE_UNICA"
        assert detect_tax_document_type("RENDICONTO FISCALE DEGIRO ANNO FISCALE 2024 QUADRO RT") == "BROKER_TAX_REPORT"
        assert detect_tax_document_type("COMUNICAZIONE N. 0011122233344 CODICE ATTO N. 20000000001 ART. 36-BIS") == "ADE_NOTICE_36BIS"
        assert detect_tax_document_type("MODELLO 730/2025 REDDITI 2024") == "OFFICIAL_DECLARATION"
        assert detect_tax_document_type("FARMACIA CENTRALE SCONTRINO PARLANTE DISPOSITIVO MEDICO") == "MEDICAL_EXPENSES"
        assert detect_tax_document_type("CERTIFICAZIONE INTERESSI PASSIVI MUTUO IPOTECARIO PRIMA CASA") == "MORTGAGE_INTEREST"
        assert detect_tax_document_type("BONIFICO PARLANTE RECUPERO DEL PATRIMONIO EDILIZIO DETRAZIONE EDILIZIA") == "BUILDING_RENOVATION"

    def test_parse_certificazione_unica_synthetic_payload(self):
        cu_text = """
        CERTIFICAZIONEUNICA2021
        CERTIFICAZIONE DI CUI ALL'ART. 4 DEL D.P.R. 22 LUGLIO 1998
        RELATIVA ALL'ANNO 2020
        02786551206 AZIENDA DIRITTO STUDIO BOLOGNA BO
        RSSMRA85M01H501Z ROSSI MARIO
        Identificativo dichiarazione: 12013910562 - 0004585 del 18/2/2021
        6 1.028,00
        21 0,00
        22 0,00
        """
        res = parse_certificazione_unica(cu_text, filename="test_cu.txt")
        assert res["doc_type"] == "CU"
        assert res["tax_year"] == 2020
        assert res["filing_year"] == 2021
        assert res["issuer_name"] == "AZIENDA DIRITTO STUDIO"
        assert res["gross_amount"] == 1028.0
        assert res["tax_withheld_or_due"] == 0.0

    def test_parse_broker_tax_report_synthetic_payload(self):
        broker_text = """
        RENDICONTO FISCALE DEGIRO — ANNO FISCALE 2024
        QUADRO RT - Plusvalenze di natura finanziaria
        5.510 4.175
        893
        1.335
        893
        442
        115
        115
        QUADRO RW
        22.992
        """
        res = parse_broker_tax_report(broker_text, filename="degiro_2024.txt")
        assert res["doc_type"] == "BROKER_REPORT"
        assert res["tax_year"] == 2024
        assert res["issuer_name"] == "DEGIRO"
        assert res["gross_amount"] == 1335.0
        assert res["net_taxable_amount"] == 442.0
        assert res["tax_withheld_or_due"] == 115.0
        assert res["secondary_amount"] == 34.0
        assert res["asset_monitoring_val"] == 23563.0

    def test_parse_ade_notice_36bis_synthetic_payload(self):
        ade_text = """
        Divisione Servizi - Ufficio Controllo dichiarazioni
        Comunicazione n. 0011122233344
        Codice atto n. 20000000001
        Gentile Contribuente, dai controlli effettuati sulla sua dichiarazione modello 730 / 2025
        Può regolarizzare la sua posizione versando la somma di euro 261,72 entro 60 giorni.
        art. 36-bis del d.P.R. n. 600 del 1973
        Periodo d'imposta 2024
        Protocollo telematico: T250926114231436720000686
        Dichiarante : RSSMRA85M01H501Z ROSSI MARIO
        CODICE TRIBUTO 1100 (PL321) PLUSVAL. ASSOGGETTATE A IMPOSTA SOST.
        Imposta a debito 348,38
        Imposta versata 115,00
        Imposta e minor credito da versare 9242 233,38
        Sanzioni 9244 19,45
        Interessi 9243 8,89
        TOTALE 261,72
        """
        res = parse_ade_notice_36bis(ade_text, filename="avviso_36bis.txt")
        assert res["doc_type"] == "ADE_NOTICE_36BIS"
        assert res["tax_year"] == 2024
        assert res["tax_withheld_or_due"] == 348.38
        assert res["tax_paid"] == 115.00
        assert res["penalty_amount"] == 19.45
        assert res["interest_amount"] == 8.89
        assert res["total_due"] == 261.72

    def test_parse_universal_tax_document_router(self):
        cu_res = parse_universal_tax_document("CERTIFICAZIONE UNICA 2021 RELATIVA ALL'ANNO 2020 6 1.000,00", "cu.txt")
        assert cu_res["doc_type"] == "CU"

        brk_res = parse_universal_tax_document("RENDICONTO FISCALE DEGIRO ANNO FISCALE 2024 115", "degiro.txt")
        assert brk_res["doc_type"] == "BROKER_REPORT"

        ade_res = parse_universal_tax_document("COMUNICAZIONE N. 100 CODICE ATTO N. 200 ART. 36-BIS 261,72", "notice.txt")
        assert ade_res["doc_type"] == "ADE_NOTICE_36BIS"


class TestTriangularTaxAudit:
    def test_build_triangular_tax_audit_with_discrepancy_and_civis(self, memory_db):
        profile = "prof_audit"
        year = 2024

        # 1. 730
        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "capital_gains_declared": 442.31,
            "substitute_tax_paid": 115.0,
            "gross_income": 22716.0,
            "foreign_assets_val": 17000.0,
            "ivafe_paid": 34.0,
            "protocol_id": "T250926114231436720000686",
        })

        # 2. Broker Report
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "gross_amount": 1335.0,
            "net_taxable_amount": 442.0,
            "tax_withheld_or_due": 115.0,
            "secondary_amount": 34.0,
            "asset_monitoring_val": 23563.0,
            "metadata_json": {
                "gross_capital_gains": 1335.0,
                "offset_losses": 893.0,
                "net_capital_gains": 442.0,
            },
        })

        # 3. AdE 36-bis notice
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "ADE_NOTICE_36BIS",
            "issuer_name": "AGENZIA DELLE ENTRATE",
            "protocol_or_code": "Atto #20000000001",
            "tax_withheld_or_due": 348.38,
            "tax_paid": 115.0,
            "total_due": 261.72,
            "metadata_json": {
                "notice_number": "0011122233344",
                "act_code": "20000000001",
                "challenged_protocol": "T250926114231436720000686",
            },
        })

        audit = build_triangular_tax_audit(memory_db, profile_id=profile, tax_year=year)
        assert audit["has_audit_data"] is True
        assert "BROKER_REPORT" in audit["sources_found"]
        assert "OFFICIAL_730" in audit["sources_found"]
        assert "ADE_NOTICE_36BIS" in audit["sources_found"]
        assert audit["has_ade_notice"] is True
        assert audit["ade_total_disputed"] == 261.72
        assert audit["civis_defense_draft"] is not None
        assert "art. 68, comma 5, del D.P.R. 917/1986" in audit["civis_defense_draft"]
        assert "DEGIRO" in audit["civis_defense_draft"]
        assert len(audit["metrics_table"]) >= 6


class Test730PredispositionAndNewParsers:
    def test_parse_ade_precompilata(self):
        sample_precompilata = """
        MODELLO 730 PRECOMPILATO 2026 - AGENZIA DELLE ENTRATE
        Codice fiscale del dichiarante: RSSMRA85M01H501Z
        DATI UTILIZZATI:
        PL, Rigo 11 (Reddito complessivo): 8.299,00 €
        PL, Rigo 50 (Imposta netta): 1.163,00 €
        PL, Rigo 59 (Ritenute): 1.671,00 €
        PL, Rigo 91, colonna 3 (di cui da rimborsare): 625,00 €
        DATI NON UTILIZZATI:
        Contratto di locazione abitativo Atto TGU-2025-3T-000001
        Spese per canone di locazione studenti fuori sede: 519,45 €
        """
        res = parse_ade_precompilata(sample_precompilata, filename="precompilata_2026.txt")
        assert res["doc_type"] == "PRECOMPILATA_ADE"
        assert res["tax_year"] == 2025
        assert res["filing_year"] == 2026
        assert res["gross_amount"] == 8299.00
        assert res["tax_withheld_or_due"] == 1163.00
        assert res["tax_paid"] == 1671.00
        assert res["secondary_amount"] == 625.00
        assert res["metadata_json"]["unused_data"]["rent_contract"]["detected"] is True
        assert res["metadata_json"]["unused_data"]["rent_contract"]["contract_code"] == "TGU-2025-3T-000001"
        assert res["metadata_json"]["unused_data"]["rent_contract"]["potential_deduction_eur"] == 98.70

    def test_parse_bank_statement_rw(self):
        sample_n26 = """
        N26 Bank AG - Certificazione Giacenza Media e Saldi ai fini ISEE / Fiscali
        Periodo: Anno 2025 (01.01.2025 - 31.12.2025)
        Titolare: Mario Rossi (RSSMRA85M01H501Z)
        Giacenza media annua: 734,91 EUR
        Saldo contabile al 31/12/2025: 1.382,11 EUR
        """
        res = parse_bank_statement_rw(sample_n26, filename="n26_statement.txt")
        assert res["doc_type"] == "BANK_STATEMENT_RW"
        assert res["tax_year"] == 2025
        assert res["gross_amount"] == 734.91
        assert res["asset_monitoring_val"] == 1382.11
        assert res["tax_withheld_or_due"] == 0.0
        assert res["metadata_json"]["is_exempt_under_5k"] is True
        assert res["metadata_json"]["quadro_w_compilation_required"] is True

    def test_parse_rent_expense(self):
        sample_bonifico = """
        RICEVUTA DISPOSIZIONE BONIFICO SEPA
        Data esecuzione: 28/11/2025
        Importo: 270,00 EUR
        Causale: Pagamento canone di locazione Novembre 2025 contr. TGU-2025-3T-000001
        Beneficiario: Mario Rossi
        """
        res = parse_rent_expense(sample_bonifico, filename="bonifico_affitto_nov.txt")
        assert res["doc_type"] == "RENT_EXPENSE"
        assert res["tax_year"] == 2025
        assert res["gross_amount"] == 270.00
        assert res["secondary_amount"] == pytest.approx(51.30, abs=0.01)
        assert res["metadata_json"]["contract_code"] == "TGU-2025-3T-000001"
        assert "Codice 18" in res["metadata_json"]["quadro_rigo"]

    def test_build_730_predisposition_and_variance_audit(self, memory_db):
        profile = "prof_predisp"
        year = 2025

        # 1. Registra Precompilata AdE
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "PRECOMPILATA_ADE",
            "issuer_name": "AGENZIA DELLE ENTRATE",
            "gross_amount": 8299.0,
            "tax_withheld_or_due": 1163.0,
            "tax_paid": 1671.0,
            "secondary_amount": 625.0, # Rimborso AdE
            "metadata_json": {
                "ade_refund": 625.0,
                "unused_data": {
                    "rent_contract": {"detected": True, "amount": 519.45, "potential_deduction_eur": 98.70},
                },
            },
        })

        # 2. Registra CU Datore di Lavoro
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "CU",
            "issuer_name": "DATORE DI LAVORO SPA",
            "gross_amount": 8299.14,
            "tax_withheld_or_due": 1670.61,
            "secondary_amount": 168.0,
        })

        # 3. Registra Spesa Affitto
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "RENT_EXPENSE",
            "issuer_name": "LOCAZIONE IMMOBILE",
            "gross_amount": 519.45,
            "secondary_amount": 98.70,
            "metadata_json": {
                "contract_code": "TGU-2025-3T-000001",
                "eligible_deduction_19pct": 98.70,
            },
        })

        # 4. Registra Report Broker DEGIRO
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "gross_amount": 793.0,
            "net_taxable_amount": 793.0,
            "tax_withheld_or_due": 206.0,
            "secondary_amount": 62.0,
            "asset_monitoring_val": 36098.0,
            "metadata_json": {
                "substitute_tax_due": 206.0,
                "ivafe_due": 62.0,
            },
        })

        # Costruisce audit di predisposizione
        audit = build_730_predisposition_and_variance_audit(memory_db, profile_id=profile, tax_year=year)
        assert audit["has_audit_data"] is True
        assert audit["ade_precompilata_refund"] == 625.00
        assert audit["rent_deduction_to_add"] == 98.70
        assert audit["argus_optimized_refund"] == 723.70
        assert audit["net_additional_refund"] == 98.70
        assert audit["foreign_rt_substitute_tax"] == 206.00
        assert audit["foreign_ivafe_tax"] == 62.00
        assert audit["foreign_f24_to_pay"] == 268.00
        assert audit["final_net_cash_flow"] == 455.70
        assert len(audit["variance_matrix"]) >= 4


class TestUnifiedTaxDocumentRegistry:
    def test_get_unified_tax_document_registry(self, memory_db):
        profile = "prof_registry"

        # Inserisce 1 dichiarazione ufficiale
        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": 2024,
            "filing_year": 2025,
            "gross_income": 22000.0,
            "net_tax_irpef": 2600.0,
            "source_filename": "730_2025.pdf",
            "protocol_id": "T250926-0001",
        })

        # Inserisce 2 documenti di verifica
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "doc_type": "CU",
            "issuer_name": "DATORE DI LAVORO SPA",
            "gross_amount": 8300.0,
            "tax_withheld_or_due": 1670.0,
            "source_filename": "CU_2026.pdf",
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "doc_type": "RENT_EXPENSE",
            "issuer_name": "LOCATORE",
            "gross_amount": 519.45,
            "secondary_amount": 98.70,
            "source_filename": "contratto_affitto.pdf",
        })

        reg = get_unified_tax_document_registry(memory_db, profile_id=profile)
        assert len(reg) == 3

        # Verifica ordinamento per tax_year desc
        assert reg[0]["tax_year"] == 2025
        assert reg[1]["tax_year"] == 2025
        assert reg[2]["tax_year"] == 2024

        # Verifica campi unificati
        decl_item = next(r for r in reg if r["source_table"] == "tax_declarations")
        assert decl_item["registry_id"].startswith("DECL-")
        assert decl_item["gross_amount"] == 22000.0
        assert decl_item["status_badge"] == "Archiviato Ufficiale"

        cu_item = next(r for r in reg if r["doc_type"] == "CU")
        assert cu_item["registry_id"].startswith("VDOC-")
        assert cu_item["issuer_name"] == "DATORE DI LAVORO SPA"
        assert cu_item["gross_amount"] == 8300.0
        assert "Validati" in cu_item["status_badge"]

        rent_item = next(r for r in reg if r["doc_type"] == "RENT_EXPENSE")
        assert rent_item["secondary_amount"] == 98.70
        assert "E8" in rent_item["status_badge"]


class TestF24PaymentSlipAnd730Guide:
    def test_generate_f24_payment_slip(self, memory_db):
        profile = "prof_f24"
        year = 2025

        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "DEGIRO",
            "gross_amount": 793.0,
            "tax_withheld_or_due": 206.18,
            "secondary_amount": 62.00,
            "metadata_json": {
                "substitute_tax_due": 206.18,
                "ivafe_due": 62.00,
            },
        })

        f24 = generate_f24_payment_slip(memory_db, profile_id=profile, tax_year=year)
        assert f24["tax_year"] == 2025
        assert f24["filing_year"] == 2026
        assert f24["has_liabilities"] is True
        assert f24["total_debt_eur"] == 268.18
        assert f24["net_balance_eur"] == 268.18
        assert len(f24["payment_rows"]) == 2
        assert any(r["tributo_code"] == "1100" and r["debito_eur"] == 206.18 for r in f24["payment_rows"])
        assert any(r["tributo_code"] == "4043" and r["debito_eur"] == 62.00 for r in f24["payment_rows"])
        assert f24["deadlines"]["ordinaria"]["data"] == "30/06/2026"
        assert f24["deadlines"]["differita_con_maggiorazione"]["importo"] == pytest.approx(269.25, abs=0.05)
        assert len(f24["installment_plans"]) == 6

    def test_generate_730_precompilata_actionable_guide(self, memory_db):
        profile = "prof_guide"
        year = 2025

        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "PRECOMPILATA_ADE",
            "gross_amount": 8299.0,
            "secondary_amount": 625.0,
            "metadata_json": {"unused_data": {"rent_contract": {"detected": True, "amount": 519.45, "potential_deduction_eur": 98.70}}},
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "RENT_EXPENSE",
            "gross_amount": 519.45,
            "secondary_amount": 98.70,
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "BROKER_REPORT",
            "gross_amount": 793.0,
            "tax_withheld_or_due": 206.18,
            "secondary_amount": 62.00,
        })

        guide = generate_730_precompilata_actionable_guide(memory_db, profile_id=profile, tax_year=year)
        assert guide["total_steps"] == 5
        assert guide["summary"]["initial_ade_refund"] == 625.00
        assert guide["summary"]["optimized_refund"] == 723.70
        assert guide["summary"]["f24_liabilities"] == 268.18
        assert guide["summary"]["net_cash_inflow"] == 455.52
        step_titles = [s["title"] for s in guide["steps"]]
        assert any("Quadro E" in t for t in step_titles)
        assert any("Quadro RT" in t for t in step_titles)
        assert any("Quadro W" in t for t in step_titles)


class TestCashflowSyncAndPensionOptimizer:
    def test_sync_tax_events_to_cashflow(self, memory_db):
        profile = "prof_cashflow"
        year = 2025

        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "PRECOMPILATA_ADE",
            "secondary_amount": 625.0,
            "metadata_json": {"unused_data": {"rent_contract": {"detected": True, "amount": 519.45, "potential_deduction_eur": 98.70}}},
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "RENT_EXPENSE",
            "gross_amount": 519.45,
            "secondary_amount": 98.70,
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "doc_type": "BROKER_REPORT",
            "tax_withheld_or_due": 206.18,
            "secondary_amount": 62.00,
        })

        sync_res = sync_tax_events_to_cashflow(memory_db, profile_id=profile, tax_year=year, portfolio_id=1)
        assert sync_res["status"] == "success"
        assert sync_res["records_synced"] == 2
        assert sync_res["net_cash_impact"] == 455.52

    def test_compute_pension_tax_deduction_optimizer(self, memory_db):
        profile = "prof_pension"
        year = 2025

        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": year,
            "gross_income": 35000.0,
            "net_tax_irpef": 4500.0,
        })

        pension = compute_pension_tax_deduction_optimizer(memory_db, profile_id=profile, tax_year=year)
        assert pension["gross_taxable_income"] == 35000.0
        assert pension["max_statutory_cap"] == 5164.57
        assert pension["remaining_deductible_cap"] == 5164.57
        assert pension["marginal_irpef_rate_pct"] == 35.0
        assert len(pension["simulation_table"]) >= 4
        assert pension["max_potential_tax_savings"] > 1000.0


class TestTaxLossHarvestingAndBackupBundle:
    def test_compute_tax_loss_harvesting_signals(self, memory_db):
        profile = "prof_tlh"
        record_tax_loss(memory_db, {
            "profile_id": profile,
            "generation_year": 2022,
            "expiration_year": 2026,
            "initial_loss_amount": 800.0,
            "remaining_amount": 800.0,
            "status": "ACTIVE",
        })

        signals = compute_tax_loss_harvesting_signals(memory_db, portfolio_id=1, profile_id=profile, current_year=2025)
        assert signals["total_active_losses"] == 800.0
        assert signals["urgent_expiring_losses"] == 800.0
        assert signals["has_harvesting_opportunity"] is True
        assert len(signals["harvesting_recommendations"]) > 0

    def test_export_and_import_backup_bundle(self, memory_db):
        profile = "prof_backup"
        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": 2024,
            "gross_income": 20000.0,
            "protocol_id": "TEST-PROTO",
        })
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "doc_type": "CU",
            "issuer_name": "TEST ISSUER",
            "gross_amount": 5000.0,
        })

        # Insert a fixed expense with a real date object to test JSON serialization
        from datetime import date
        with memory_db.begin() as conn:
            conn.execute(
                sqlt("INSERT INTO wealth_fixed_expenses (portfolio_id, category, note, amount, payment_day, start_date) "
                     "VALUES (1, 'Fisco', 'Test Note', 100.0, 1, :dt)"),
                {"dt": date(2025, 6, 30)},
            )

        bundle = export_wealth_and_tax_backup_bundle(memory_db, profile_id=profile)
        assert bundle["backup_metadata"]["version"] == "2.0"
        assert bundle["backup_metadata"]["total_records_count"] >= 2
        assert "tax_declarations" in bundle["tables"]
        assert len(bundle["tables"]["tax_declarations"]) >= 1

        # Test full JSON serialization with indent
        bundle_json_str = json.dumps(bundle, indent=2, ensure_ascii=False)
        assert "2025-06-30" in bundle_json_str

        restore_res = import_wealth_and_tax_backup_bundle(memory_db, bundle, profile_id="restored_user")
        assert restore_res["status"] == "success"
        assert restore_res["total_restored_records"] >= 2


class TestStrategicFiscalExtensions:
    def test_generate_commercialista_tax_dossier_html(self, memory_db):
        profile = "prof_dossier"
        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "gross_income": 48000.0,
            "taxable_income": 45000.0,
            "net_tax_irpef": 11200.0,
            "capital_gains_declared": 2500.0,
            "capital_losses_offset": 800.0,
            "substitute_tax_paid": 442.0,
            "ivafe_paid": 54.0,
            "notes": "Dichiarazione ufficiale 2025",
        })
        record_tax_loss(memory_db, {
            "profile_id": profile,
            "generation_year": 2023,
            "expiration_year": 2027,
            "initial_loss_amount": 1500.0,
            "offset_amount": 300.0,
            "remaining_amount": 1200.0,
            "status": "ACTIVE",
        })

        html = generate_commercialista_tax_dossier_html(
            memory_db, profile_id=profile, tax_year=2025, taxpayer_name="Mario Rossi", cf="RSSMRA85M01H501Z"
        )
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html
        assert "DOSSIER FISCALE COMPLETO" in html
        assert "Mario Rossi" in html
        assert "RSSMRA85M01H501Z" in html
        assert "F24" in html
        assert "Quadro RW" in html
        assert "window.print()" in html

    def test_compute_fiscal_reform_2026_etf_harmonization(self, memory_db):
        profile = "prof_reform"
        # Inserisci una minusvalenza attiva di 1500€
        record_tax_loss(memory_db, {
            "profile_id": profile,
            "generation_year": 2023,
            "expiration_year": 2027,
            "initial_loss_amount": 2000.0,
            "offset_amount": 500.0,
            "remaining_amount": 1500.0,
            "status": "ACTIVE",
        })

        res = compute_fiscal_reform_2026_etf_harmonization(
            memory_db, profile_id=profile, tax_year=2025, simulated_etf_gain=3000.0
        )
        assert res["simulated_etf_gain_eur"] == 3000.0
        assert res["total_active_losses_eur"] == 1500.0
        # Nel sistema attuale le minusvalenze non compensano gli ETF: imposta dovuta 3000 * 0.26 = 780€
        assert res["current_system"]["etf_tax_due_eur"] == 780.0
        assert res["current_system"]["losses_usable_eur"] == 0.0
        # Nel sistema 2026 riformato (compensazione redditi diversi e di capitale): 3000 - 1500 = 1500 imponibile
        assert res["reform_2026_system"]["losses_offset_eur"] == 1500.0
        assert res["reform_2026_system"]["net_taxable_eur"] == 1500.0
        assert res["reform_2026_system"]["etf_tax_due_eur"] == 390.0
        # Tax Alpha immediato da riforma: 780 - 390 = 390€ risparmio secco
        assert res["immediate_tax_alpha_eur"] == 390.0
        assert res["delta_tax_pct_points"] == 13.0

    def test_compute_fire_effective_tax_drag(self, memory_db):
        profile = "prof_fire"
        # Registra una dichiarazione per il profilo con reddito e imposte
        record_declaration(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "gross_income": 40000.0,
            "capital_gains_declared": 5000.0,
            "substitute_tax_paid": 800.0,
            "ivafe_paid": 50.0,
        })

        res = compute_fire_effective_tax_drag(
            memory_db, profile_id=profile, tax_year=2025, annual_portfolio_gain=25000.0, swr_base=0.04
        )
        assert "effective_tax_rate_actual_pct" in res
        assert res["effective_tax_rate_actual_pct"] <= 26.0
        assert res["effective_tax_rate_actual_pct"] >= 0.0
        assert res["fire_target_flat_26_eur"] > res["fire_target_actual_eur"]
        assert res["capital_savings_eur"] > 0
        assert res["years_advanced_to_fire"] >= 1.0
        assert res["effective_swr_net_pct"] > 0

    def test_compute_crypto_tax_reporting(self, memory_db):
        profile = "prof_crypto"
        # Test con dati di default dimostrativi
        res_default = compute_crypto_tax_reporting(memory_db, profile_id=profile, tax_year=2025)
        assert res_default["tax_year"] == 2025
        assert res_default["crypto_balance_31_12"] > 0
        assert res_default["imposta_valore_crypto_2_permille"] > 0
        assert res_default["substitute_tax_26pct"] > 0
        assert len(res_default["quadro_rw_rows"]) == 1
        assert res_default["quadro_rw_rows"][0]["codice_tributo_f24"] == "1727"
        assert len(res_default["quadro_rt_rows"]) == 1
        assert res_default["quadro_rt_rows"][0]["codice_tributo_f24"] == "1715"

        # Test inserendo un documento di verifica specifico per crypto
        record_verification_document(memory_db, {
            "profile_id": profile,
            "tax_year": 2025,
            "doc_type": "BROKER_REPORT",
            "issuer_name": "BINANCE IRELAND",
            "asset_monitoring_val": 10000.0,
            "gross_amount": 15000.0,
            "net_taxable_amount": 2000.0,
            "notes": "CRYPTO WALLET EXCHANGES",
        })
        res_doc = compute_crypto_tax_reporting(memory_db, profile_id=profile, tax_year=2025)
        assert res_doc["crypto_balance_31_12"] == 10000.0
        assert res_doc["imposta_valore_crypto_2_permille"] == 20.0  # 10000 * 0.002
        assert res_doc["substitute_tax_26pct"] == 520.0  # 2000 * 0.26
        assert res_doc["total_crypto_tax_eur"] == 540.0

    def test_get_fiscal_deadlines_calendar(self, memory_db):
        deadlines = get_fiscal_deadlines_calendar(tax_year=2025, profile_id="test_user", engine=memory_db)
        assert isinstance(deadlines, list)
        assert len(deadlines) >= 6
        # Verifica campi presenti in ogni scadenza
        for d in deadlines:
            assert "id" in d
            assert "title" in d
            assert "due_date_str" in d
            assert "due_date_formatted" in d
            assert "days_remaining" in d
            assert "urgency_badge" in d
            assert d["urgency_badge"] in ["PASSATO", "CRITICO", "IN SCADENZA", "PROGRAMMATO"]
            assert "badge_color" in d
            assert "tributo_code" in d


class TestAdvancedFiscalEnhancements:
    """Test suite per le nuove funzionalità fiscali strategiche (Spese Mediche, Mutui, Ristrutturazioni, Facsimile F24, Proiezione Riforma 2026)."""

    def test_parse_medical_expenses_payload(self):
        medical_text = """
        FARMACIA SAN CARLO - SCONTRINO PARLANTE
        DATA: 15/05/2024
        CODICE FISCALE: RSSMRA85M01H501Z
        DISPOSITIVO MEDICO CE: 150,00 €
        FARMACIA / MEDICINALI: 79,11 €
        TOTALE: 229,11 €
        """
        res = parse_medical_expenses(medical_text, filename="scontrino_farmacia.txt")
        assert res["doc_type"] == "MEDICAL_EXPENSES"
        assert res["gross_amount"] == 229.11
        # Franchigia 129.11 -> eccedenza = 229.11 - 129.11 = 100.00
        assert res["net_taxable_amount"] == 100.00
        # Detrazione 19% su 100.00 = 19.00
        assert res["secondary_amount"] == 19.00
        assert res["metadata_json"]["franchigia_eur"] == 129.11
        assert res["metadata_json"]["eligible_deduction_19pct"] == 19.00
        assert res["taxpayer_cf"] == "RSSMRA85M01H501Z"

    def test_parse_mortgage_interest_payload(self):
        mortgage_text = """
        INTESA SANPAOLO - ATTESTAZIONE INTERESSI PASSIVI MUTUO
        ANNO D'IMPOSTA: 2024
        CONTRATTO MUTUO N.: MUT-2021-9988
        OGGETTO: MUTUO IPOTECARIO ACQUISTO ABITAZIONE PRINCIPALE
        QUOTA INTERESSI PAGATA NEL 2024: 4.800,00 €
        TOTALE PAGATO: 4.800,00 €
        """
        res = parse_mortgage_interest(mortgage_text, filename="certificazione_mutuo.txt")
        assert res["doc_type"] == "MORTGAGE_INTEREST"
        assert res["gross_amount"] == 4800.00
        # Cap normativo a 4.000,00 € -> base ammessa = 4000.00
        assert res["net_taxable_amount"] == 4000.00
        # Detrazione 19% su 4000.00 = 760.00
        assert res["secondary_amount"] == 760.00
        assert res["metadata_json"]["max_statutory_cap_eur"] == 4000.00
        assert res["metadata_json"]["eligible_deduction_19pct"] == 760.00

    def test_parse_building_renovation_payload(self):
        renovation_text = """
        BONIFICO PARLANTE RECUPERO PATRIMONIO EDILIZIO (ART. 16-BIS TUIR)
        DATA: 20/09/2024
        BENEFICIARIO: EDIL COSTRUZIONI SRL
        IMPORTO FATTURA: 12.000,00 €
        DETRAZIONE EDILIZIA 50%
        RIQUALIFICAZIONE
        """
        res = parse_building_renovation(renovation_text, filename="bonifico_edilizio.txt")
        assert res["doc_type"] == "BUILDING_RENOVATION"
        assert res["gross_amount"] == 12000.00
        # 50% di 12.000 = 6.000 totale bonus
        assert res["net_taxable_amount"] == 6000.00
        # 1/10 rata annua = 600.00
        assert res["secondary_amount"] == 600.00
        assert res["metadata_json"]["rate_label"] == "50%"
        assert res["metadata_json"]["annual_installment_eur"] == 600.00

    def test_universal_router_with_new_documents(self):
        med_raw = "FARMACIA CENTRALE SCONTRINO PARLANTE 250,00 €"
        res_med = parse_universal_tax_document(med_raw, filename="doc_med.txt")
        assert res_med["doc_type"] == "MEDICAL_EXPENSES"
        assert res_med["gross_amount"] > 0

        mort_raw = "INTESA SANPAOLO CERTIFICAZIONE INTERESSI PASSIVI MUTUO PRIMA CASA 3.200,00 €"
        res_mort = parse_universal_tax_document(mort_raw, filename="doc_mutuo.txt")
        assert res_mort["doc_type"] == "MORTGAGE_INTEREST"
        assert res_mort["net_taxable_amount"] == 3200.00

        reno_raw = "BONIFICO PARLANTE RECUPERO DEL PATRIMONIO EDILIZIO 50% 8.000,00 €"
        res_reno = parse_universal_tax_document(reno_raw, filename="doc_ristr.txt")
        assert res_reno["doc_type"] == "BUILDING_RENOVATION"
        assert res_reno["secondary_amount"] == 400.00

    def test_official_f24_facsimile_html(self, memory_db):
        f24_data = generate_f24_payment_slip(memory_db, profile_id="test_user", tax_year=2025)
        html = generate_official_f24_facsimile_html(
            f24_data=f24_data,
            taxpayer_name="MARIO ROSSI",
            taxpayer_cf="RSSMRA85M01H501Z",
        )
        assert "<!DOCTYPE html>" in html
        assert "Modello di Pagamento Unificato" in html
        assert "RSSMRA85M01H501Z" in html
        assert "SEZIONE ERARIO" in html
        assert "1100" in html
        assert "4043" in html
        assert "@media print" in html

    def test_compute_fiscal_reform_multiyear_projection(self):
        res = compute_fiscal_reform_multiyear_projection(
            initial_capital=50000.0,
            annual_return_pct=8.0,
            annual_turnover_pct=20.0,
            realized_loss_fraction=0.35,
            projection_years=10,
        )
        assert res["initial_capital"] == 50000.0
        assert res["projection_years"] == 10
        assert len(res["trajectory"]) == 10
        assert res["final_capital_reform"] > res["final_capital_status_quo"]
        assert res["total_wealth_alpha_eur"] > 0
        assert res["total_tax_savings_eur"] > 0
        assert res["tax_alpha_basis_points"] > 0
        assert "5y" in res["milestones"]
        assert "10y" in res["milestones"]
