# ============================================================
# core/private_debt_engine.py
# ARGUS — Private Debt, Direct Lending & Credit Waterfall Desk
# Multi-tranche waterfall, covenant tracking & PIK capitalization
# ============================================================

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def get_standard_private_debt_deals() -> List[Dict[str, Any]]:
    """Restituisce deal di private debt e direct lending istituzionali esemplificativi."""
    return [
        {
            "deal_id": "PD-2026-MEDTECH",
            "borrower_name": "Aura Medical Technologies S.p.A.",
            "sector": "Healthcare & MedTech",
            "total_facility_eur": 25000000.0,
            "ebitda_eur": 5500000.0,
            "existing_net_debt_eur": 12000000.0,
            "annual_free_cash_flow_eur": 3800000.0,
            "tenor_years": 5,
            "tranches": [
                {"name": "Senior Secured (Term Loan A)", "notional_eur": 15000000.0, "margin_euribor_bps": 450, "euribor_pct": 3.25, "pik_margin_bps": 0, "seniority": 1},
                {"name": "Unitranche (Term Loan B)", "notional_eur": 7000000.0, "margin_euribor_bps": 650, "euribor_pct": 3.25, "pik_margin_bps": 150, "seniority": 2},
                {"name": "Mezzanine Subordinated", "notional_eur": 3000000.0, "margin_euribor_bps": 850, "euribor_pct": 3.25, "pik_margin_bps": 300, "seniority": 3}
            ],
            "covenants": {
                "max_leverage_net_debt_ebitda": 4.20,
                "min_interest_coverage_ratio": 2.75,
                "min_dscr": 1.25
            }
        },
        {
            "deal_id": "PD-2026-CLEANTECH",
            "borrower_name": "Helios Clean Energy Infrastructure",
            "sector": "Renewables & Utilities",
            "total_facility_eur": 40000000.0,
            "ebitda_eur": 9200000.0,
            "existing_net_debt_eur": 22000000.0,
            "annual_free_cash_flow_eur": 6500000.0,
            "tenor_years": 7,
            "tranches": [
                {"name": "Senior Secured Green Loan", "notional_eur": 30000000.0, "margin_euribor_bps": 400, "euribor_pct": 3.25, "pik_margin_bps": 0, "seniority": 1},
                {"name": "Junior Mezzanine Bond", "notional_eur": 10000000.0, "margin_euribor_bps": 750, "euribor_pct": 3.25, "pik_margin_bps": 200, "seniority": 2}
            ],
            "covenants": {
                "max_leverage_net_debt_ebitda": 4.50,
                "min_interest_coverage_ratio": 3.00,
                "min_dscr": 1.30
            }
        }
    ]


def compute_private_debt_waterfall_and_covenants(
    deal_data: Optional[Dict[str, Any]] = None,
    ebitda_stress_pct: float = 0.0
) -> Dict[str, Any]:
    """
    Simula la cascata di flussi (Cash Flow Waterfall), la conformità dei covenant finanziari
    e la capitalizzazione degli interessi PIK per strumenti di Private Debt & Direct Lending.
    """
    deal = deal_data or get_standard_private_debt_deals()[0]

    base_ebitda = float(deal.get("ebitda_eur", 5000000.0))
    stressed_ebitda = base_ebitda * (1.0 + ebitda_stress_pct / 100.0)
    existing_net_debt = float(deal.get("existing_net_debt_eur", 10000000.0))
    fcf = float(deal.get("annual_free_cash_flow_eur", 3000000.0)) * (1.0 + ebitda_stress_pct / 100.0)

    tranches = deal.get("tranches", [])
    total_facility = sum(t["notional_eur"] for t in tranches) if tranches else float(deal.get("total_facility_eur", 25000000.0))

    # Calcolo interessi tranche e cascata di pagamento
    tranche_results = []
    total_cash_interest = 0.0
    total_pik_interest = 0.0

    cumulative_debt = existing_net_debt
    for tr in tranches:
        notional = float(tr.get("notional_eur", 0.0))
        euribor = float(tr.get("euribor_pct", 3.25)) / 100.0
        cash_margin = float(tr.get("margin_euribor_bps", 400.0)) / 10000.0
        pik_margin = float(tr.get("pik_margin_bps", 0.0)) / 10000.0

        cash_coupon_rate = euribor + cash_margin
        pik_coupon_rate = pik_margin
        all_in_yield = cash_coupon_rate + pik_coupon_rate

        annual_cash_int = notional * cash_coupon_rate
        annual_pik_int = notional * pik_coupon_rate

        total_cash_interest += annual_cash_int
        total_pik_interest += annual_pik_int
        cumulative_debt += notional

        tranche_results.append({
            "tranche_name": tr.get("name", "Tranche"),
            "seniority": tr.get("seniority", 1),
            "notional_eur": notional,
            "cash_coupon_pct": round(cash_coupon_rate * 100.0, 2),
            "pik_coupon_pct": round(pik_coupon_rate * 100.0, 2),
            "all_in_yield_pct": round(all_in_yield * 100.0, 2),
            "annual_cash_interest_eur": round(annual_cash_int, 2),
            "annual_pik_interest_eur": round(annual_pik_int, 2),
            "cumulative_debt_eur": round(cumulative_debt, 2),
            "attachment_leverage": round((cumulative_debt - notional) / max(0.01, stressed_ebitda), 2),
            "detachment_leverage": round(cumulative_debt / max(0.01, stressed_ebitda), 2)
        })

    # Calcolo metriche di credito e Covenants
    total_net_debt = cumulative_debt
    leverage_ratio = total_net_debt / max(0.01, stressed_ebitda)
    icr = stressed_ebitda / max(0.01, total_cash_interest)
    dscr = fcf / max(0.01, total_cash_interest + (total_facility * 0.05))  # Assunta quota capitale 5% annuo

    cov_limits = deal.get("covenants", {
        "max_leverage_net_debt_ebitda": 4.5,
        "min_interest_coverage_ratio": 2.5,
        "min_dscr": 1.2
    })

    leverage_breached = leverage_ratio > cov_limits.get("max_leverage_net_debt_ebitda", 4.5)
    icr_breached = icr < cov_limits.get("min_interest_coverage_ratio", 2.5)
    dscr_breached = dscr < cov_limits.get("min_dscr", 1.2)

    covenant_status = "PASS 🟢" if not (leverage_breached or icr_breached or dscr_breached) else "BREACH 🔴 (Covenant Violato)"

    df_tranches = pd.DataFrame(tranche_results)

    return {
        "deal_id": deal.get("deal_id", "PD-DEFAULT"),
        "borrower_name": deal.get("borrower_name", "Corporate Borrower"),
        "sector": deal.get("sector", "Diversified"),
        "total_facility_eur": round(total_facility, 2),
        "stressed_ebitda_eur": round(stressed_ebitda, 2),
        "ebitda_stress_pct": ebitda_stress_pct,
        "total_cash_interest_eur": round(total_cash_interest, 2),
        "total_pik_capitalized_eur": round(total_pik_interest, 2),
        "weighted_all_in_yield_pct": round((total_cash_interest + total_pik_interest) / max(0.01, total_facility) * 100.0, 2),
        "credit_metrics": {
            "leverage_net_debt_ebitda": round(leverage_ratio, 2),
            "max_leverage_allowed": cov_limits.get("max_leverage_net_debt_ebitda", 4.5),
            "leverage_breached": leverage_breached,
            "interest_coverage_ratio_icr": round(icr, 2),
            "min_icr_allowed": cov_limits.get("min_interest_coverage_ratio", 2.5),
            "icr_breached": icr_breached,
            "dscr_ratio": round(dscr, 2),
            "min_dscr_allowed": cov_limits.get("min_dscr", 1.2),
            "dscr_breached": dscr_breached
        },
        "covenant_status": covenant_status,
        "is_covenant_compliant": not (leverage_breached or icr_breached or dscr_breached),
        "tranches_list": tranche_results,
        "tranches_df": df_tranches
    }
