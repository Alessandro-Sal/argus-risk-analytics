"""Basel III Liquidity Risk Engine (BCBS 238 / LCR & NSFR Standards).

Implements:
1. Liquidity Coverage Ratio (LCR >= 100%):
   - HQLA classification (Level 1, Level 2A, Level 2B) with regulatory haircuts (0%, 15%, 50%)
   - HQLA 40% Level 2 cap and 15% Level 2B cap unwinding adjustments
   - 30-day stressed outflows and 75% inflow cap
2. Net Stable Funding Ratio (NSFR >= 100%):
   - Available Stable Funding (ASF) weighting
   - Required Stable Funding (RSF) weighting
3. Dynamic Multi-Horizon Cash Flow Stress Ladder (30d, 90d, 180d, 360d) with Survival Horizon.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class HQLAComponent:
    """High Quality Liquid Asset item."""

    asset_id: str
    asset_type: str  # "cash", "central_bank_reserves", "sovereign_l1", "corp_bond_l2a", "corp_bond_l2b", "qualifying_equities"
    level: str  # "1", "2A", "2B"
    market_value: float
    haircut: float = 0.0  # 0.0 for L1, 0.15 for L2A, 0.50 for L2B

    def __post_init__(self) -> None:
        """Assign default haircuts if not specified."""
        if self.haircut == 0.0:
            if self.level == "1":
                self.haircut = 0.00
            elif self.level == "2A":
                self.haircut = 0.15
            elif self.level == "2B":
                self.haircut = 0.50

    @property
    def adjusted_value(self) -> float:
        """Value post regulatory haircut."""
        return self.market_value * (1.0 - self.haircut)


@dataclass
class CashFlowItem:
    """Cash flow item for outflow/inflow calculation."""

    item_id: str
    category: str
    amount: float
    rate: float  # Run-off rate for outflows, inflow factor for inflows

    @property
    def stressed_amount(self) -> float:
        """Amount post run-off or inflow rate."""
        return self.amount * self.rate


@dataclass
class BaselLiquidityReport:
    """Consolidated Basel III liquidity risk report."""

    lcr_ratio_pct: float
    lcr_compliant: bool
    total_hqla_eligible: float
    level_1_amount: float
    level_2a_amount: float
    level_2b_amount: float
    cap_deduction: float
    total_gross_outflows: float
    total_stressed_outflows: float
    total_gross_inflows: float
    total_eligible_inflows: float
    net_30d_cash_outflows: float
    nsfr_ratio_pct: float
    nsfr_compliant: bool
    asf_total: float
    rsf_total: float
    survival_horizon_days: int
    stress_ladder: List[Dict[str, Any]]
    hqla_breakdown: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "lcr_ratio_pct": round(self.lcr_ratio_pct, 2),
            "lcr_compliant": self.lcr_compliant,
            "total_hqla_eligible": round(self.total_hqla_eligible, 2),
            "level_1_amount": round(self.level_1_amount, 2),
            "level_2a_amount": round(self.level_2a_amount, 2),
            "level_2b_amount": round(self.level_2b_amount, 2),
            "cap_deduction": round(self.cap_deduction, 2),
            "total_gross_outflows": round(self.total_gross_outflows, 2),
            "total_stressed_outflows": round(self.total_stressed_outflows, 2),
            "total_gross_inflows": round(self.total_gross_inflows, 2),
            "total_eligible_inflows": round(self.total_eligible_inflows, 2),
            "net_30d_cash_outflows": round(self.net_30d_cash_outflows, 2),
            "nsfr_ratio_pct": round(self.nsfr_ratio_pct, 2),
            "nsfr_compliant": self.nsfr_compliant,
            "asf_total": round(self.asf_total, 2),
            "rsf_total": round(self.rsf_total, 2),
            "survival_horizon_days": self.survival_horizon_days,
            "stress_ladder": self.stress_ladder,
            "hqla_breakdown": self.hqla_breakdown,
        }


class BaselLiquidityEngine:
    """Basel III Liquidity metrics and stress ladder engine."""

    def __init__(self) -> None:
        """Initialize Basel Liquidity engine."""
        pass

    def calculate_hqla(self, hqla_items: List[HQLAComponent]) -> Tuple[float, float, float, float, float]:
        """Compute eligible HQLA stock enforcing 40% Level 2 and 15% Level 2B caps.

        Formula (Basel III Annex 1):
        Adjusted L1 = sum(L1 post-haircut)
        Adjusted L2A = sum(L2A post-haircut)
        Adjusted L2B = sum(L2B post-haircut)

        Cap 1: Level 2B cannot exceed 15/85 of (L1 + L2A)
        Cap 2: Total Level 2 (2A + 2B) cannot exceed 40/60 of L1
        """
        l1 = sum(item.adjusted_value for item in hqla_items if item.level == "1")
        l2a = sum(item.adjusted_value for item in hqla_items if item.level == "2A")
        l2b = sum(item.adjusted_value for item in hqla_items if item.level == "2B")

        # Cap for Level 2B assets: max 15% of total HQLA => L2B <= (15 / 85) * (L1 + L2A)
        max_l2b = (15.0 / 85.0) * (l1 + l2a)
        excess_l2b = max(0.0, l2b - max_l2b)
        eligible_l2b = l2b - excess_l2b

        # Cap for Total Level 2 assets (2A + 2B): max 40% of total HQLA => (L2A + eligible_L2B) <= (40 / 60) * L1
        max_l2 = (40.0 / 60.0) * l1
        excess_l2 = max(0.0, (l2a + eligible_l2b) - max_l2)

        total_cap_deduction = excess_l2b + excess_l2
        total_hqla = max(0.0, (l1 + l2a + l2b) - total_cap_deduction)

        return total_hqla, l1, l2a, l2b, total_cap_deduction

    def calculate_lcr(
        self,
        hqla_items: List[HQLAComponent],
        outflows: List[CashFlowItem],
        inflows: List[CashFlowItem],
    ) -> Dict[str, Any]:
        """Compute 30-day Liquidity Coverage Ratio (LCR = HQLA / Net Stressed Outflows)."""
        total_hqla, l1, l2a, l2b, deduction = self.calculate_hqla(hqla_items)

        gross_outflows = sum(item.amount for item in outflows)
        stressed_outflows = sum(item.stressed_amount for item in outflows)

        gross_inflows = sum(item.amount for item in inflows)
        stressed_inflows = sum(item.stressed_amount for item in inflows)

        # 75% cap on inflows: Eligible Inflows = min(Stressed Inflows, 75% of Stressed Outflows)
        max_eligible_inflow = 0.75 * stressed_outflows
        eligible_inflows = min(stressed_inflows, max_eligible_inflow)

        net_outflows = max(1.0, stressed_outflows - eligible_inflows)
        lcr_ratio = (total_hqla / net_outflows) * 100.0

        return {
            "lcr_ratio_pct": lcr_ratio,
            "lcr_compliant": lcr_ratio >= 100.0,
            "total_hqla": total_hqla,
            "level_1": l1,
            "level_2a": l2a,
            "level_2b": l2b,
            "cap_deduction": deduction,
            "gross_outflows": gross_outflows,
            "stressed_outflows": stressed_outflows,
            "gross_inflows": gross_inflows,
            "eligible_inflows": eligible_inflows,
            "net_30d_cash_outflows": net_outflows,
        }

    def calculate_nsfr(
        self,
        asf_items: List[Dict[str, Any]],
        rsf_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute Net Stable Funding Ratio (NSFR = Total ASF / Total RSF)."""
        asf_total = sum(float(item["amount"]) * float(item.get("asf_factor", 1.0)) for item in asf_items)
        rsf_total = sum(float(item["amount"]) * float(item.get("rsf_factor", 1.0)) for item in rsf_items)

        nsfr_ratio = (asf_total / max(1.0, rsf_total)) * 100.0

        return {
            "nsfr_ratio_pct": nsfr_ratio,
            "nsfr_compliant": nsfr_ratio >= 100.0,
            "asf_total": asf_total,
            "rsf_total": rsf_total,
        }

    def compute_stress_ladder(
        self,
        initial_cash: float,
        time_horizons_days: Optional[List[int]] = None,
        daily_inflow_rate: float = 120_000.0,
        daily_outflow_rate: float = 180_000.0,
        stress_multiplier: float = 1.35,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Compute dynamic multi-horizon cash flow ladder and calculate survival horizon in days."""
        if time_horizons_days is None:
            time_horizons_days = [1, 7, 14, 30, 60, 90, 180, 360]

        ladder: List[Dict[str, Any]] = []
        cumulative_balance = initial_cash
        survival_horizon = 360

        for day in time_horizons_days:
            # Baseline inflows and outflows over horizon
            inflows_cum = daily_inflow_rate * day
            outflows_cum = daily_outflow_rate * day * stress_multiplier
            net_cum = inflows_cum - outflows_cum
            horizon_balance = initial_cash + net_cum

            if horizon_balance < 0 and survival_horizon == 360:
                # Interpolate exact day of exhaustion
                daily_burn = (daily_outflow_rate * stress_multiplier) - daily_inflow_rate
                if daily_burn > 0:
                    survival_horizon = int(initial_cash / daily_burn)

            ladder.append(
                {
                    "horizon_days": day,
                    "cumulative_inflows": round(inflows_cum, 2),
                    "cumulative_outflows": round(outflows_cum, 2),
                    "net_cumulative_cash": round(net_cum, 2),
                    "projected_liquidity_buffer": round(horizon_balance, 2),
                    "status": "Solvent" if horizon_balance >= 0 else "Liquidity Deficit",
                }
            )

        return ladder, survival_horizon

    def generate_full_report(
        self,
        hqla_items: Optional[List[HQLAComponent]] = None,
        outflows: Optional[List[CashFlowItem]] = None,
        inflows: Optional[List[CashFlowItem]] = None,
        asf_items: Optional[List[Dict[str, Any]]] = None,
        rsf_items: Optional[List[Dict[str, Any]]] = None,
    ) -> BaselLiquidityReport:
        """Generate comprehensive Basel III Liquidity Report."""
        if hqla_items is None:
            hqla_items = [
                HQLAComponent("CASH_01", "central_bank_reserves", "1", 25_000_000.0, 0.0),
                HQLAComponent("GOV_DE_01", "sovereign_l1", "1", 45_000_000.0, 0.0),
                HQLAComponent("CORP_AAA_01", "corp_bond_l2a", "2A", 30_000_000.0, 0.15),
                HQLAComponent("EQUITY_L2B_01", "qualifying_equities", "2B", 15_000_000.0, 0.50),
            ]

        if outflows is None:
            outflows = [
                CashFlowItem("OUT_RETAIL_STABLE", "retail_deposits_stable", 80_000_000.0, 0.05),
                CashFlowItem("OUT_RETAIL_LESS_STABLE", "retail_deposits_less_stable", 40_000_000.0, 0.10),
                CashFlowItem("OUT_WHOLESALE_NON_OP", "unsecured_wholesale_non_op", 35_000_000.0, 1.00),
                CashFlowItem("OUT_FACILITIES", "committed_credit_facilities", 20_000_000.0, 0.20),
            ]

        if inflows is None:
            inflows = [
                CashFlowItem("IN_FINANCIAL_RECV", "financial_loans_maturing", 15_000_000.0, 1.00),
                CashFlowItem("IN_RETAIL_PAYMENTS", "retail_counterparty_inflows", 10_000_000.0, 0.50),
            ]

        if asf_items is None:
            asf_items = [
                {"name": "Tier 1 Regulatory Capital", "amount": 35_000_000.0, "asf_factor": 1.00},
                {"name": "Stable Retail Deposits (>1Y)", "amount": 75_000_000.0, "asf_factor": 0.95},
                {"name": "Less Stable Retail Deposits", "amount": 30_000_000.0, "asf_factor": 0.90},
                {"name": "Wholesale Funding (6M-1Y)", "amount": 25_000_000.0, "asf_factor": 0.50},
            ]

        if rsf_items is None:
            rsf_items = [
                {"name": "Cash and Central Bank Reserves", "amount": 25_000_000.0, "rsf_factor": 0.00},
                {"name": "Sovereign Debt (0% RW)", "amount": 45_000_000.0, "rsf_factor": 0.05},
                {"name": "Residential Mortgages", "amount": 50_000_000.0, "rsf_factor": 0.65},
                {"name": "Corporate Loans (>1Y)", "amount": 40_000_000.0, "rsf_factor": 0.85},
            ]

        lcr_res = self.calculate_lcr(hqla_items, outflows, inflows)
        nsfr_res = self.calculate_nsfr(asf_items, rsf_items)

        total_hqla_val = lcr_res["total_hqla"]
        stress_ladder, survival_days = self.compute_stress_ladder(
            initial_cash=total_hqla_val,
            time_horizons_days=[1, 7, 14, 30, 60, 90, 180, 360],
            daily_inflow_rate=sum(i.amount for i in inflows) / 30.0,
            daily_outflow_rate=sum(o.amount for o in outflows) / 30.0,
            stress_multiplier=1.20,
        )

        hqla_breakdown = [
            {
                "asset_id": item.asset_id,
                "asset_type": item.asset_type,
                "level": item.level,
                "market_value_eur": round(item.market_value, 2),
                "haircut_pct": round(item.haircut * 100.0, 1),
                "adjusted_value_eur": round(item.adjusted_value, 2),
            }
            for item in hqla_items
        ]

        return BaselLiquidityReport(
            lcr_ratio_pct=lcr_res["lcr_ratio_pct"],
            lcr_compliant=lcr_res["lcr_compliant"],
            total_hqla_eligible=lcr_res["total_hqla"],
            level_1_amount=lcr_res["level_1"],
            level_2a_amount=lcr_res["level_2a"],
            level_2b_amount=lcr_res["level_2b"],
            cap_deduction=lcr_res["cap_deduction"],
            total_gross_outflows=lcr_res["gross_outflows"],
            total_stressed_outflows=lcr_res["stressed_outflows"],
            total_gross_inflows=lcr_res["gross_inflows"],
            total_eligible_inflows=lcr_res["eligible_inflows"],
            net_30d_cash_outflows=lcr_res["net_30d_cash_outflows"],
            nsfr_ratio_pct=nsfr_res["nsfr_ratio_pct"],
            nsfr_compliant=nsfr_res["nsfr_compliant"],
            asf_total=nsfr_res["asf_total"],
            rsf_total=nsfr_res["rsf_total"],
            survival_horizon_days=survival_days,
            stress_ladder=stress_ladder,
            hqla_breakdown=hqla_breakdown,
        )


def compute_basel_liquidity_ratios(
    hqla_data: Optional[List[Dict[str, Any]]] = None,
    outflows_data: Optional[List[Dict[str, Any]]] = None,
    inflows_data: Optional[List[Dict[str, Any]]] = None,
    asf_data: Optional[List[Dict[str, Any]]] = None,
    rsf_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Top-level calculation function for Basel III liquidity ratios."""
    engine = BaselLiquidityEngine()

    hqla_objs = None
    if hqla_data is not None:
        hqla_objs = [
            HQLAComponent(
                asset_id=item["asset_id"],
                asset_type=item.get("asset_type", "sovereign_l1"),
                level=item.get("level", "1"),
                market_value=float(item["market_value"]),
                haircut=float(item.get("haircut", 0.0)),
            )
            for item in hqla_data
        ]

    outflow_objs = None
    if outflows_data is not None:
        outflow_objs = [
            CashFlowItem(
                item_id=item["item_id"],
                category=item.get("category", "unsecured_wholesale"),
                amount=float(item["amount"]),
                rate=float(item.get("rate", 1.0)),
            )
            for item in outflows_data
        ]

    inflow_objs = None
    if inflows_data is not None:
        inflow_objs = [
            CashFlowItem(
                item_id=item["item_id"],
                category=item.get("category", "loan_repayment"),
                amount=float(item["amount"]),
                rate=float(item.get("rate", 1.0)),
            )
            for item in inflows_data
        ]

    report = engine.generate_full_report(
        hqla_items=hqla_objs,
        outflows=outflow_objs,
        inflows=inflow_objs,
        asf_items=asf_data,
        rsf_items=rsf_data,
    )

    res_dict = report.to_dict()
    res_dict["engine_version"] = "9.14.0"
    return res_dict
