"""Supervisory Fed CCAR / EBA 9-Quarter Capital Stress & CET1 Trajectory Engine.

Simulates a bank or institutional balance sheet over a 9-quarter forward supervisory horizon
(Q1..Q9) across three regulatory macro scenarios:
1. Supervisory Baseline
2. Supervisory Adverse
3. Supervisory Severely Adverse (Fed CCAR / EBA Adverse with Global Market Shock)

Models:
- Pre-Provision Net Revenue (PPNR): NII + Fee Income - Operating Expenses
- IFRS 9 / CECL 3-Stage Credit Migration (Stage 1 -> Stage 2 SICR -> Stage 3 Default)
- Quarterly Loan Loss Provisions (LLP), Trading/GMS Losses, and RWA migration inflation
- Common Equity Tier 1 (CET1) ratio path vs. Pillar 1 + P2R + CCB + G-SII MDA trigger
- Stress Capital Buffer (SCB) calculation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BankCapitalProfile:
    """Initial institutional balance sheet & regulatory capital position."""

    institution_name: str = "Argus European Systemic Bank S.p.A."
    initial_cet1_capital_eur_m: float = 14_200.0
    initial_rwa_eur_m: float = 100_000.0
    total_loan_book_eur_m: float = 145_000.0
    initial_stage2_share: float = 0.065
    initial_stage3_share: float = 0.022
    quarterly_ppnr_baseline_eur_m: float = 920.0
    trading_book_notional_eur_m: float = 28_000.0
    dividend_payout_ratio: float = 0.35
    tax_rate: float = 0.27
    pillar1_min_cet1_pct: float = 4.5
    pillar2_requirement_pct: float = 1.5
    capital_conservation_buffer_pct: float = 2.5
    gsii_osii_buffer_pct: float = 1.0


class CCARStressEngine:
    """9-Quarter Fed CCAR & EBA Supervisory Capital Stress Testing Engine."""

    SCENARIO_MACROS: dict[str, dict[str, Any]] = {
        "baseline": {
            "label": "Supervisory Baseline",
            "gdp_growth_ann_pct": [2.1, 2.0, 1.9, 1.9, 1.8, 1.8, 1.8, 1.9, 1.9],
            "unemployment_rate_pct": [4.0, 4.0, 4.1, 4.1, 4.1, 4.0, 4.0, 4.0, 3.9],
            "ppnr_multiplier": [1.00, 1.01, 1.01, 1.02, 1.02, 1.03, 1.03, 1.04, 1.04],
            "pd_quarterly_bps": [14.0, 14.0, 15.0, 15.0, 15.0, 14.0, 14.0, 14.0, 14.0],
            "sicr_stage2_Add_bps": [25.0, 25.0, 25.0, 20.0, 20.0, 20.0, 20.0, 15.0, 15.0],
            "lgd_stressed": 0.32,
            "rwa_inflation_path": [1.00, 1.00, 1.01, 1.01, 1.01, 1.02, 1.02, 1.02, 1.02],
            "gms_trading_shock_pct": 0.00,
        },
        "adverse": {
            "label": "Supervisory Adverse (Stagflation / Credit Tightening)",
            "gdp_growth_ann_pct": [-1.2, -1.8, -1.5, -0.8, 0.2, 0.8, 1.2, 1.5, 1.6],
            "unemployment_rate_pct": [4.6, 5.4, 6.1, 6.6, 6.8, 6.6, 6.3, 6.0, 5.7],
            "ppnr_multiplier": [0.88, 0.82, 0.79, 0.80, 0.83, 0.86, 0.89, 0.92, 0.95],
            "pd_quarterly_bps": [32.0, 45.0, 58.0, 62.0, 54.0, 46.0, 38.0, 32.0, 28.0],
            "sicr_stage2_Add_bps": [120.0, 180.0, 210.0, 160.0, 110.0, 70.0, 45.0, 30.0, 25.0],
            "lgd_stressed": 0.44,
            "rwa_inflation_path": [1.03, 1.06, 1.09, 1.11, 1.12, 1.11, 1.09, 1.08, 1.07],
            "gms_trading_shock_pct": 0.022,
        },
        "severely_adverse": {
            "label": "Fed CCAR / EBA Severely Adverse (Global Recession + GMS)",
            "gdp_growth_ann_pct": [-3.4, -4.8, -4.1, -2.5, -0.8, 0.5, 1.2, 1.6, 1.8],
            "unemployment_rate_pct": [5.5, 7.2, 8.8, 9.7, 10.0, 9.6, 9.1, 8.5, 7.9],
            "ppnr_multiplier": [0.74, 0.65, 0.60, 0.62, 0.68, 0.74, 0.80, 0.85, 0.89],
            "pd_quarterly_bps": [68.0, 96.0, 125.0, 132.0, 110.0, 88.0, 68.0, 52.0, 42.0],
            "sicr_stage2_Add_bps": [280.0, 390.0, 450.0, 310.0, 190.0, 110.0, 65.0, 40.0, 30.0],
            "lgd_stressed": 0.54,
            "rwa_inflation_path": [1.06, 1.12, 1.18, 1.22, 1.24, 1.22, 1.19, 1.16, 1.14],
            "gms_trading_shock_pct": 0.058,
        },
    }

    def __init__(self, profile: BankCapitalProfile | None = None) -> None:
        self.profile = profile or BankCapitalProfile()

    @property
    def mda_trigger_pct(self) -> float:
        """Overall Capital Requirement (OCR) / Maximum Distributable Amount (MDA) CET1 hurdle."""
        p = self.profile
        return (
            p.pillar1_min_cet1_pct
            + p.pillar2_requirement_pct
            + p.capital_conservation_buffer_pct
            + p.gsii_osii_buffer_pct
        )

    def simulate_scenario(self, scenario_key: str) -> dict[str, Any]:
        """Simulate 9-quarter balance sheet, IFRS 9 provisions, RWA, and CET1 path."""
        key = scenario_key.lower().strip()
        if key not in self.SCENARIO_MACROS:
            key = "severely_adverse"
        macro = self.SCENARIO_MACROS[key]
        p = self.profile

        initial_cet1_ratio = (p.initial_cet1_capital_eur_m / max(p.initial_rwa_eur_m, 1.0)) * 100.0
        cet1_cap = p.initial_cet1_capital_eur_m
        s2_share = p.initial_stage2_share
        s3_share = p.initial_stage3_share
        lgd = float(macro["lgd_stressed"])

        quarters_path: list[dict[str, Any]] = []
        cum_credit_losses = 0.0
        cum_ppnr = 0.0
        cum_net_income = 0.0

        for q_idx in range(9):
            q_label = f"Q{q_idx + 1}"
            ppnr = p.quarterly_ppnr_baseline_eur_m * float(macro["ppnr_multiplier"][q_idx])

            # IFRS 9 / CECL Stage migration and Expected Credit Loss (ECL) provisioning
            new_default_rate = float(macro["pd_quarterly_bps"][q_idx]) * 1e-4
            new_sicr_rate = float(macro["sicr_stage2_Add_bps"][q_idx]) * 1e-4

            default_flow_eur = p.total_loan_book_eur_m * new_default_rate
            sicr_flow_eur = p.total_loan_book_eur_m * new_sicr_rate

            # Stage 3 Lifetime ECL + Stage 2 incremental Lifetime ECL reserve build
            stage3_provision = default_flow_eur * lgd
            stage2_incremental_provision = sicr_flow_eur * (lgd * 0.28)
            total_llp_eur = stage3_provision + stage2_incremental_provision

            # Update stage shares
            s3_share = min(s3_share + new_default_rate * 0.75, 0.25)
            s2_share = min(max(s2_share + new_sicr_rate * 0.50 - new_default_rate * 0.35, 0.03), 0.35)
            s1_share = max(1.0 - s2_share - s3_share, 0.40)

            # Global Market Shock (GMS) & Counterparty default loss applied in Q1
            trading_loss_eur = (
                p.trading_book_notional_eur_m * float(macro["gms_trading_shock_pct"])
                if q_idx == 0
                else 0.0
            )

            pre_tax_income = ppnr - total_llp_eur - trading_loss_eur
            if pre_tax_income > 0:
                taxes = pre_tax_income * p.tax_rate
                net_income = pre_tax_income - taxes
                dividends = net_income * p.dividend_payout_ratio
            else:
                # Deferred tax asset (DTA) partial tax shield capped under stress
                tax_benefit = abs(pre_tax_income) * (p.tax_rate * 0.50)
                net_income = pre_tax_income + tax_benefit
                dividends = 0.0

            cet1_cap = max(cet1_cap + net_income - dividends, 0.0)
            rwa_q = p.initial_rwa_eur_m * float(macro["rwa_inflation_path"][q_idx])
            cet1_ratio_q = (cet1_cap / max(rwa_q, 1.0)) * 100.0

            cum_credit_losses += total_llp_eur
            cum_ppnr += ppnr
            cum_net_income += net_income

            quarters_path.append(
                {
                    "quarter": q_label,
                    "gdp_growth_ann_pct": round(float(macro["gdp_growth_ann_pct"][q_idx]), 2),
                    "unemployment_rate_pct": round(float(macro["unemployment_rate_pct"][q_idx]), 2),
                    "ppnr_eur_m": round(ppnr, 2),
                    "loan_loss_provisions_eur_m": round(total_llp_eur, 2),
                    "trading_gms_loss_eur_m": round(trading_loss_eur, 2),
                    "net_income_eur_m": round(net_income, 2),
                    "cet1_capital_eur_m": round(cet1_cap, 2),
                    "rwa_eur_m": round(rwa_q, 2),
                    "cet1_ratio_pct": round(cet1_ratio_q, 2),
                    "stage1_share_pct": round(s1_share * 100.0, 2),
                    "stage2_share_pct": round(s2_share * 100.0, 2),
                    "stage3_share_pct": round(s3_share * 100.0, 2),
                }
            )

        min_cet1_node = min(quarters_path, key=lambda item: item["cet1_ratio_pct"])
        min_cet1_ratio = float(min_cet1_node["cet1_ratio_pct"])
        trough_quarter = str(min_cet1_node["quarter"])
        ending_cet1_ratio = float(quarters_path[-1]["cet1_ratio_pct"])
        max_drawdown_bps = round((initial_cet1_ratio - min_cet1_ratio) * 100.0, 1)

        ocr_hurdle = self.mda_trigger_pct
        headroom_pct = round(min_cet1_ratio - ocr_hurdle, 2)
        breaches_mda = min_cet1_ratio < ocr_hurdle
        breaches_pillar1 = min_cet1_ratio < (p.pillar1_min_cet1_pct + p.pillar2_requirement_pct)

        # Fed CCAR Stress Capital Buffer (SCB) = max(2.5%, Initial CET1 - Trough CET1 + 4Q planned dividends/RWA)
        raw_depletion = max(initial_cet1_ratio - min_cet1_ratio, 0.0)
        scb_pct = round(max(2.5, raw_depletion + 0.35), 2)

        return {
            "scenario_key": key,
            "scenario_label": macro["label"],
            "initial_cet1_ratio_pct": round(initial_cet1_ratio, 2),
            "minimum_stressed_cet1_ratio_pct": round(min_cet1_ratio, 2),
            "trough_quarter": trough_quarter,
            "ending_q9_cet1_ratio_pct": round(ending_cet1_ratio, 2),
            "max_cet1_drawdown_bps": max_drawdown_bps,
            "cumulative_9q_ppnr_eur_m": round(cum_ppnr, 2),
            "cumulative_9q_credit_losses_eur_m": round(cum_credit_losses, 2),
            "cumulative_9q_loss_rate_pct": round(
                (cum_credit_losses / max(p.total_loan_book_eur_m, 1.0)) * 100.0, 2
            ),
            "cumulative_9q_net_income_eur_m": round(cum_net_income, 2),
            "implied_stress_capital_buffer_scb_pct": scb_pct,
            "mda_hurdle_pct": round(ocr_hurdle, 2),
            "headroom_vs_mda_pct": headroom_pct,
            "mda_restriction_triggered": breaches_mda,
            "pillar1_p2r_breached": breaches_pillar1,
            "trajectory": quarters_path,
        }

    def run_comprehensive_ccar_assessment(self) -> dict[str, Any]:
        """Run all three supervisory scenarios and synthesize CCAR/EBA regulatory capital report."""
        p = self.profile
        initial_cet1_ratio = (p.initial_cet1_capital_eur_m / max(p.initial_rwa_eur_m, 1.0)) * 100.0

        res_base = self.simulate_scenario("baseline")
        res_adv = self.simulate_scenario("adverse")
        res_sev = self.simulate_scenario("severely_adverse")

        if res_sev["pillar1_p2r_breached"]:
            status = "FAIL - PILLAR 1/2 CAPITAL SHORTFALL"
        elif res_sev["mda_restriction_triggered"]:
            status = "WARNING - MDA DIVIDEND/AT1 RESTRICTION TRIGGERED"
        else:
            status = "PASS - RESILIENT ABOVE OVERALL CAPITAL REQUIREMENT"

        return {
            "institution_name": p.institution_name,
            "initial_cet1_capital_eur_m": round(p.initial_cet1_capital_eur_m, 2),
            "initial_rwa_eur_m": round(p.initial_rwa_eur_m, 2),
            "initial_cet1_ratio_pct": round(initial_cet1_ratio, 2),
            "total_loan_book_eur_m": round(p.total_loan_book_eur_m, 2),
            "regulatory_hurdles": {
                "pillar1_min_cet1_pct": p.pillar1_min_cet1_pct,
                "pillar2_requirement_pct": p.pillar2_requirement_pct,
                "capital_conservation_buffer_pct": p.capital_conservation_buffer_pct,
                "gsii_osii_buffer_pct": p.gsii_osii_buffer_pct,
                "overall_capital_requirement_mda_pct": round(self.mda_trigger_pct, 2),
            },
            "supervisory_assessment_status": status,
            "severely_adverse_min_cet1_pct": res_sev["minimum_stressed_cet1_ratio_pct"],
            "severely_adverse_trough_quarter": res_sev["trough_quarter"],
            "severely_adverse_drawdown_bps": res_sev["max_cet1_drawdown_bps"],
            "required_stress_capital_buffer_scb_pct": res_sev[
                "implied_stress_capital_buffer_scb_pct"
            ],
            "scenarios": {
                "baseline": res_base,
                "adverse": res_adv,
                "severely_adverse": res_sev,
            },
        }


def compute_ccar_capital_stress(
    institution_name: str = "Argus European Systemic Bank S.p.A.",
    initial_cet1_capital_eur_m: float = 14_200.0,
    initial_rwa_eur_m: float = 100_000.0,
    total_loan_book_eur_m: float = 145_000.0,
    quarterly_ppnr_baseline_eur_m: float = 920.0,
    trading_book_notional_eur_m: float = 28_000.0,
    pillar2_requirement_pct: float = 1.5,
    gsii_osii_buffer_pct: float = 1.0,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    profile = BankCapitalProfile(
        institution_name=institution_name,
        initial_cet1_capital_eur_m=initial_cet1_capital_eur_m,
        initial_rwa_eur_m=initial_rwa_eur_m,
        total_loan_book_eur_m=total_loan_book_eur_m,
        quarterly_ppnr_baseline_eur_m=quarterly_ppnr_baseline_eur_m,
        trading_book_notional_eur_m=trading_book_notional_eur_m,
        pillar2_requirement_pct=pillar2_requirement_pct,
        gsii_osii_buffer_pct=gsii_osii_buffer_pct,
    )
    engine = CCARStressEngine(profile=profile)
    return engine.run_comprehensive_ccar_assessment()
