# ==============================================================================
# tests/test_estate_planning_optimizer.py
# Unit Tests per il Motore di Pianificazione Successoria & Asset Protection HNWI
# ==============================================================================

import pytest
from core.wealth.asset_protection_engine import (
    GenerationalTransferOptimizer,
    FamilyHeir,
    FamilyProfile,
    PlanningLevers,
    SuccessionSharesResult,
    OptimizationComparisonResult,
    AssetProtectionEngine
)
from core.wealth.wealth_models import NetWorthSummary
from core.wealth.wealth_engine import compute_estate_planning_analytics


def test_relictum_donatum_balance_standard():
    """Verifica il calcolo della riunione fittizia ex Art. 556 c.c. in caso ordinario."""
    res = GenerationalTransferOptimizer.compute_relictum_donatum_balance(
        relictum_gross=3000000.0,
        liabilities=500000.0,
        donatum=1000000.0
    )
    assert res["relictum_gross_eur"] == 3000000.0
    assert res["liabilities_deductible_eur"] == 500000.0
    assert res["relictum_net_eur"] == 2500000.0
    assert res["donatum_total_eur"] == 1000000.0
    assert res["fictitious_reunion_estate_eur"] == 3500000.0


def test_relictum_donatum_balance_excess_debt():
    """Verifica che debiti > relictum portino l'attivo netto a 0 senza erodere il donatum."""
    res = GenerationalTransferOptimizer.compute_relictum_donatum_balance(
        relictum_gross=500000.0,
        liabilities=800000.0,
        donatum=1200000.0
    )
    assert res["relictum_net_eur"] == 0.0
    assert res["fictitious_reunion_estate_eur"] == 1200000.0


def test_usufruct_table_consistency():
    """Verifica la tabella attuariale ministeriale usufrutto/nuda proprietà per diverse fasce d'età."""
    test_ages = [18, 25, 35, 45, 55, 63, 68, 72, 78, 83, 88, 95]
    for age in test_ages:
        u_pct, b_pct = GenerationalTransferOptimizer.get_usufruct_and_bare_ownership_shares(age)
        assert round(u_pct + b_pct, 5) == 1.0
        assert 0.0 < u_pct < 1.0
        assert 0.0 < b_pct < 1.0

    # Test specifico: donante a 72 anni -> 40% usufrutto, 60% nuda proprietà
    u72, b72 = GenerationalTransferOptimizer.get_usufruct_and_bare_ownership_shares(72)
    assert u72 == 0.40
    assert b72 == 0.60

    # Donante giovane (<=20 anni) -> 95% usufrutto, 5% nuda proprietà
    u18, b18 = GenerationalTransferOptimizer.get_usufruct_and_bare_ownership_shares(18)
    assert u18 == 0.95
    assert b18 == 0.05

    # Donante centenario (>90 anni) -> 10% usufrutto, 90% nuda proprietà
    u100, b100 = GenerationalTransferOptimizer.get_usufruct_and_bare_ownership_shares(100)
    assert u100 == 0.10
    assert b100 == 0.90


def test_statutory_shares_spouse_only():
    """Art. 540 c.c.: Solo coniuge -> 50% legittima, 50% disponibile."""
    prof = FamilyProfile(has_spouse=True, children_count=0, has_ascendants=False)
    res = GenerationalTransferOptimizer.compute_statutory_shares(2000000.0, prof)
    assert res.disponibile_pct == 50.0
    assert res.total_legitimate_eur == 1000000.0
    assert len(res.legitimate_shares) == 1
    assert res.legitimate_shares[0].relationship == "coniuge"
    assert res.legitimate_shares[0].statutory_pct == 50.0


def test_statutory_shares_spouse_one_child():
    """Art. 542 c. 1 c.c.: Coniuge + 1 Figlio -> 1/3 coniuge, 1/3 figlio, 1/3 disponibile."""
    prof = FamilyProfile(has_spouse=True, children_count=1, has_ascendants=False)
    res = GenerationalTransferOptimizer.compute_statutory_shares(3000000.0, prof)
    assert res.disponibile_pct == 33.33
    assert len(res.legitimate_shares) == 2
    assert res.legitimate_shares[0].statutory_value_eur == 1000000.0
    assert res.legitimate_shares[1].statutory_value_eur == 1000000.0


def test_statutory_shares_spouse_multiple_children():
    """Art. 542 c. 2 c.c.: Coniuge + 3 Figli -> 25% coniuge, 50% figli, 25% disponibile."""
    prof = FamilyProfile(has_spouse=True, children_count=3, has_ascendants=False)
    res = GenerationalTransferOptimizer.compute_statutory_shares(4000000.0, prof)
    assert res.disponibile_pct == 25.0
    assert res.legitimate_shares[0].statutory_pct == 25.0
    assert len(res.legitimate_shares) == 4
    # Ciascun figlio 16.67%
    for f in res.legitimate_shares[1:]:
        assert f.relationship == "figlio"
        assert abs(f.statutory_pct - (50.0 / 3.0)) < 0.1


def test_statutory_shares_spouse_and_ascendants():
    """Art. 544 c.c.: Coniuge + Ascendenti senza figli -> 50% coniuge, 25% ascendenti, 25% disponibile."""
    prof = FamilyProfile(has_spouse=True, children_count=0, has_ascendants=True)
    res = GenerationalTransferOptimizer.compute_statutory_shares(2000000.0, prof)
    assert res.disponibile_pct == 25.0
    assert len(res.legitimate_shares) == 2
    assert res.legitimate_shares[0].statutory_pct == 50.0
    assert res.legitimate_shares[1].statutory_pct == 25.0


def test_statutory_shares_ascendants_only():
    """Art. 538 c.c.: Solo ascendenti (senza coniuge e figli) -> 1/3 ascendenti, 2/3 disponibile."""
    prof = FamilyProfile(has_spouse=False, children_count=0, has_ascendants=True)
    res = GenerationalTransferOptimizer.compute_statutory_shares(3000000.0, prof)
    assert res.disponibile_pct == 66.67
    assert len(res.legitimate_shares) == 1
    assert res.legitimate_shares[0].statutory_value_eur == 1000000.0


def test_statutory_shares_disabled_child_allowance():
    """Verifica franchigia maggiorata a € 1.500.000 per erede disabile ex L. 104/1992."""
    prof = FamilyProfile(has_spouse=False, children_count=1, disabled_children_count=1)
    res = GenerationalTransferOptimizer.compute_statutory_shares(2800000.0, prof)
    child_share = res.legitimate_shares[0]
    assert child_share.tax_allowance_eur == 1500000.0
    # Quota legittima = 1.400.000 < franchigia 1.500.000 -> imposta = 0
    assert child_share.imposta_successione_eur == 0.0


def test_check_reduction_risk():
    """Verifica il rilevamento della lesione di legittima per azione di riduzione."""
    prof = FamilyProfile(has_spouse=True, children_count=2)
    estate_tot = 4000000.0
    shares = GenerationalTransferOptimizer.compute_statutory_shares(estate_tot, prof)

    # Simuliamo che il Figlio #2 ha ricevuto solo 200.000 € invece della riserva di 1.000.000 €
    custom_heirs = [
        FamilyHeir(name="Coniuge Superstite", relationship="coniuge", donations_received_in_life=1000000.0),
        FamilyHeir(name="Figlio #1", relationship="figlio", donations_received_in_life=2000000.0),
        FamilyHeir(name="Figlio #2", relationship="figlio", donations_received_in_life=200000.0),
    ]
    audit = GenerationalTransferOptimizer.check_reduction_risk(shares, custom_heirs)
    assert audit["is_legitimate_injured"] is True
    assert audit["injured_heirs_count"] == 1
    assert audit["total_injury_eur"] == 800000.0  # 1.000.000 - 200.000


def test_simulate_generational_plan_hnwi():
    """Verifica l'ottimizzazione complessiva Ante vs. Post su patrimonio HNWI di € 6.5M."""
    assets = {
        "real_estate_total": 2000000.0,
        "financial_investments": 2500000.0,
        "liquidity_cash": 500000.0,
        "business_equity": 1500000.0,
        "physical_assets": 0.0,
        "pension_total": 200000.0
    }
    prof = FamilyProfile(has_spouse=True, children_count=2)

    levers = PlanningLevers(
        life_insurance_allocation_eur=1000000.0,
        holding_family_ss_equity_eur=1500000.0,
        patto_di_famiglia_eligible=True,  # 0% imposta ex art. 3 c. 4-ter TUS
        bare_ownership_donation_re_eur=1200000.0,
        donor_age=72,  # 40% usufrutto, 60% nuda proprietà
        joint_account_cash_eur=300000.0,
        is_first_home_applicable=True
    )

    comp = GenerationalTransferOptimizer.simulate_generational_plan(
        baseline_assets=assets,
        liabilities=0.0,
        donatum=0.0,
        family_profile=prof,
        levers=levers
    )

    # Verifica che lo scenario post abbatta significativamente le imposte
    assert comp.post_total_taxes_eur < comp.ante_total_taxes_eur
    assert comp.tax_savings_eur > 0.0
    assert comp.tax_savings_pct > 0.0
    # Verifica che la liquidità immediata (polizze vita + cointestazione) sia creata
    assert comp.immediate_liquidity_generated_eur >= 1000000.0
    # Score di protezione patrimoniale aumentato
    assert comp.post_protection_score > comp.ante_protection_score
    assert comp.reduction_risk_mitigated is True

    # Generazione Memorandum
    memo = GenerationalTransferOptimizer.generate_executive_succession_memo(comp, prof)
    assert "# 🏛️ MEMORANDUM ISTITUZIONALE DI PIANIFICAZIONE SUCCESSORIA" in memo
    assert "Carico Tributario Totale" in memo
    assert "Polizza Vita Ramo I/III" in memo


def test_wealth_engine_estate_planning_backward_compatibility():
    """Verifica che compute_estate_planning_analytics in wealth_engine funzioni con vecchi e nuovi parametri."""
    mock_nw = NetWorthSummary(
        total_net_worth=3000000.0,
        liquid_cash=500000.0,
        financial_investments=1500000.0,
        physical_assets=1000000.0,
        pension_total=200000.0
    )

    # Chiamata con signature originale
    res1 = compute_estate_planning_analytics(
        net_worth_summary=mock_nw,
        children_count=2,
        has_spouse=True
    )
    assert res1["legittima_coniuge_pct"] == 25.0
    assert res1["legittima_figli_tot_pct"] == 50.0
    assert res1["disponibile_pct"] == 25.0
    assert "mortgage_cadastral_tax" in res1
    assert "total_taxes_with_ipocatastali" in res1

    # Chiamata con nuovi parametri opzionali (ascendenti e disabilità)
    res2 = compute_estate_planning_analytics(
        net_worth_summary=mock_nw,
        children_count=0,
        has_spouse=True,
        has_ascendants=True,
        liabilities_deductible=200000.0
    )
    assert res2["legittima_coniuge_pct"] == 50.0
    assert res2["val_legittima_coniuge"] > 0
    assert res2["liabilities_deductible"] == 200000.0
    assert res2["relictum_net"] == 2800000.0
