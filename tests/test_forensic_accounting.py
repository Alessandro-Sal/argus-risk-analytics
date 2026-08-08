import pytest

from core.forensic_accounting import compute_beneish_m_score, compute_sloan_accrual_ratio


def test_beneish_m_score_safe_and_manipulator():
    # Caso 1: Azienda sana / conforme (indici standard eccellenti)
    res_safe = compute_beneish_m_score(
        dsri=0.95, gmi=0.95, aqi=0.90, sgi=1.0, depi=1.0, sgai=0.95, lvgi=0.95, tata=-0.05
    )
    assert res_safe["m_score"] < -1.78
    assert res_safe["is_manipulator"] is False
    assert "🟢" in res_safe["icon"]

    # Caso 2: Azienda con indici anomali (gonfiamento crediti e ricavi, es. Enron profile)
    res_fraud = compute_beneish_m_score(
        dsri=2.5, gmi=1.8, aqi=2.0, sgi=2.2, depi=0.7, sgai=1.5, lvgi=1.8, tata=0.15
    )
    assert res_fraud["m_score"] > -1.78
    assert res_fraud["is_manipulator"] is True
    assert "🔴" in res_fraud["icon"]


def test_sloan_accrual_ratio():
    # Caso 1: Alta qualità degli utili (Cash Flow > Net Income)
    res_high = compute_sloan_accrual_ratio(
        net_income=100.0,
        operating_cash_flow=150.0,
        total_assets=1000.0
    )
    assert res_high["accrual_ratio"] < 0
    assert "Eccellente" in res_high["quality"]

    # Caso 2: Bassa qualità degli utili (Accruals gonfiati)
    res_low = compute_sloan_accrual_ratio(
        net_income=250.0,
        operating_cash_flow=50.0,
        total_assets=1000.0
    )
    assert res_low["accrual_ratio"] > 0.10
    assert "Bassa Qualità" in res_low["quality"]
