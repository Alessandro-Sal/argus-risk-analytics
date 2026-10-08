# ============================================================
# tests/test_tax_history_engine.py
# Unit tests for ARGUS Tax History Engine, Carryforward Losses & Reconciliation
# ============================================================

import io

import pytest
from sqlalchemy import create_engine

from core.wealth.tax_history_engine import (
    TaxDeclaration,
    TaxLossCarryforward,
    delete_declaration,
    delete_tax_loss,
    get_declarations,
    get_tax_losses,
    parse_730_pdf_or_json,
    reconcile_with_portfolio,
    record_declaration,
    record_tax_loss,
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
