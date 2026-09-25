"""Asset-Liability Management (ALM), Redington Immunization & LDI Cash-Flow Matching LP Engine.

Models multi-decade institutional liabilities (nominal + inflation-linked pension/insurance/family
office obligations) against an asset portfolio:
1. Present Value of Liabilities (PV_L), Funding Ratio (PV_A / PV_L), Accounting Surplus (PV_A - PV_L),
   and 1-Year 99% Surplus-at-Risk (SaR_99%).
2. Redington (1952) Immunization Verification:
   - Modified Duration Matching (D_A == D_L)
   - Convexity Dominance (Convexity_A > Convexity_L)
3. LDI Receiver Swap / Ultra-Long Bond Hedge Sizing to reach 100% Liability Hedge Ratio (LHR).
4. Dedicated Bond Portfolio Cash-Flow Matching via Linear Programming (scipy.optimize.linprog).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import linprog


class AlmLdiEngine:
    """Institutional ALM, LDI Receiver Swap Overlay & Dedicated Cash-Flow Matching LP Engine."""

    def __init__(
        self,
        asset_portfolio_eur: float = 125_000_000.0,
        asset_modified_duration: float = 6.8,
        asset_convexity: float = 62.0,
        asset_annual_vol: float = 0.095,
        discount_rate: float = 0.034,
        inflation_rate: float = 0.021,
        liability_schedule: list[dict[str, float]] | None = None,
    ) -> None:
        self.asset_portfolio_eur = asset_portfolio_eur
        self.asset_modified_duration = asset_modified_duration
        self.asset_convexity = asset_convexity
        self.asset_annual_vol = asset_annual_vol
        self.discount_rate = discount_rate
        self.inflation_rate = inflation_rate
        self.liability_schedule = liability_schedule or self._default_liability_schedule()

    @staticmethod
    def _default_liability_schedule() -> list[dict[str, float]]:
        return [
            {"year": 1.0, "nominal_cashflow_eur": 4_500_000.0, "inflation_linked_share": 0.40},
            {"year": 3.0, "nominal_cashflow_eur": 9_200_000.0, "inflation_linked_share": 0.50},
            {"year": 5.0, "nominal_cashflow_eur": 14_800_000.0, "inflation_linked_share": 0.60},
            {"year": 10.0, "nominal_cashflow_eur": 28_500_000.0, "inflation_linked_share": 0.70},
            {"year": 15.0, "nominal_cashflow_eur": 36_000_000.0, "inflation_linked_share": 0.75},
            {"year": 20.0, "nominal_cashflow_eur": 44_000_000.0, "inflation_linked_share": 0.80},
            {"year": 30.0, "nominal_cashflow_eur": 52_000_000.0, "inflation_linked_share": 0.85},
        ]

    def solve_cashflow_matching_lp(
        self, years: np.ndarray, target_cashflows: np.ndarray
    ) -> dict[str, Any]:
        """Solve a Dedicated Bond Portfolio LP minimizing total purchase cost to match liabilities."""
        n = len(years)
        # Construct N benchmark government bonds maturing at each horizon t_j with coupon c_j
        coupons = np.linspace(0.028, 0.042, n)
        prices = np.zeros(n, dtype=float)
        cf_matrix = np.zeros((n, n), dtype=float)

        for j in range(n):
            t_mat = years[j]
            c_rate = coupons[j]
            # Bond j pays coupon at all buckets i <= j and principal 100 at i == j
            for i in range(j + 1):
                dt_bucket = years[i] - (years[i - 1] if i > 0 else 0.0)
                cf_matrix[i, j] = c_rate * 100.0 * dt_bucket
                if i == j:
                    cf_matrix[i, j] += 100.0
            # Clean price of bond j at discount_rate
            pv_j = 0.0
            for i in range(j + 1):
                pv_j += cf_matrix[i, j] / ((1.0 + self.discount_rate) ** years[i])
            prices[j] = pv_j

        # LP: minimize sum(prices[j] * x[j]) subject to -cf_matrix @ x <= -target_cashflows, x >= 0
        res = linprog(
            c=prices,
            A_ub=-cf_matrix,
            b_ub=-target_cashflows,
            bounds=[(0.0, None)] * n,
            method="highs",
        )
        if res.success and res.x is not None:
            units = res.x
            min_cost_eur = float(np.dot(prices, units))
        else:
            units = target_cashflows / 100.0
            min_cost_eur = float(np.dot(prices, units))

        allocations = [
            {
                "bond_id": f"BTP_LDI_{int(years[j])}Y",
                "maturity_years": float(years[j]),
                "coupon_pct": round(float(coupons[j]) * 100.0, 2),
                "unit_price": round(float(prices[j]), 2),
                "contracts_required": round(float(units[j]), 1),
                "market_value_eur": round(float(prices[j] * units[j]), 2),
                "target_liability_cf_eur": round(float(target_cashflows[j]), 2),
            }
            for j in range(n)
        ]

        return {
            "lp_converged": bool(res.success),
            "dedicated_bond_portfolio_cost_eur": round(min_cost_eur, 2),
            "bond_allocations": allocations,
        }

    def analyze_alm(self) -> dict[str, Any]:
        """Compute full ALM telemetry, Redington immunization check, LDI swap overlay, and LP matching."""
        years_list: list[float] = []
        infl_adj_cf: list[float] = []
        pv_buckets: list[float] = []

        r = self.discount_rate
        pi = self.inflation_rate

        for item in self.liability_schedule:
            t = float(item["year"])
            nom_cf = float(item["nominal_cashflow_eur"])
            idx_share = float(item.get("inflation_linked_share", 0.5))
            # Expected future cash flow including inflation indexation
            cf_t = nom_cf * ((1.0 - idx_share) + idx_share * ((1.0 + pi) ** t))
            pv_t = cf_t / ((1.0 + r) ** t)
            years_list.append(t)
            infl_adj_cf.append(cf_t)
            pv_buckets.append(pv_t)

        years_arr = np.array(years_list, dtype=float)
        cf_arr = np.array(infl_adj_cf, dtype=float)
        pv_arr = np.array(pv_buckets, dtype=float)

        pv_liabilities = float(np.sum(pv_arr))
        pv_assets = float(self.asset_portfolio_eur)
        weights_l = pv_arr / max(pv_liabilities, 1.0)

        macaulay_dur_l = float(np.sum(weights_l * years_arr))
        mod_dur_l = macaulay_dur_l / (1.0 + r)
        convexity_l = float(np.sum(weights_l * years_arr * (years_arr + 1.0)) / ((1.0 + r) ** 2))

        funding_ratio_pct = (pv_assets / max(pv_liabilities, 1.0)) * 100.0
        surplus_eur = pv_assets - pv_liabilities

        # Dollar Duration (DV01) of Assets vs Liabilities
        asset_dv01 = pv_assets * self.asset_modified_duration * 1e-4
        liab_dv01 = pv_liabilities * mod_dur_l * 1e-4
        net_dv01_gap = asset_dv01 - liab_dv01
        liability_hedge_ratio_pct = (asset_dv01 / max(liab_dv01, 1e-6)) * 100.0

        # Required 20Y Receiver IRS Notional (assuming 20Y IRS mod duration ~ 15.2)
        swap_20y_mod_dur = 15.2
        required_receiver_swap_notional_eur = max((liab_dv01 - asset_dv01) / (swap_20y_mod_dur * 1e-4), 0.0)

        # Redington (1952) Immunization conditions
        duration_matched = abs(self.asset_modified_duration - mod_dur_l) <= 0.75
        convexity_dominant = self.asset_convexity >= convexity_l
        redington_immunized = duration_matched and convexity_dominant and (funding_ratio_pct >= 98.0)

        # 1-Year 99% Surplus at Risk (SaR_99%) combining asset vol and 100 bps rate shock
        rate_vol_annual = 0.0085  # 85 bps annual rate volatility
        duration_mismatch_loss_std = abs(pv_assets * self.asset_modified_duration - pv_liabilities * mod_dur_l) * rate_vol_annual
        asset_return_std_eur = pv_assets * self.asset_annual_vol
        total_surplus_std_eur = math.sqrt(asset_return_std_eur**2 + duration_mismatch_loss_std**2)
        surplus_at_risk_99_eur = 2.3263 * total_surplus_std_eur

        lp_res = self.solve_cashflow_matching_lp(years_arr, cf_arr)

        return {
            "pv_assets_eur": round(pv_assets, 2),
            "pv_liabilities_eur": round(pv_liabilities, 2),
            "accounting_surplus_eur": round(surplus_eur, 2),
            "funding_ratio_pct": round(funding_ratio_pct, 2),
            "surplus_at_risk_99_eur": round(surplus_at_risk_99_eur, 2),
            "asset_modified_duration": round(self.asset_modified_duration, 2),
            "liability_modified_duration": round(mod_dur_l, 2),
            "duration_gap_years": round(self.asset_modified_duration - mod_dur_l, 2),
            "asset_convexity": round(self.asset_convexity, 2),
            "liability_convexity": round(convexity_l, 2),
            "asset_dv01_eur": round(asset_dv01, 2),
            "liability_dv01_eur": round(liab_dv01, 2),
            "net_dv01_gap_eur": round(net_dv01_gap, 2),
            "liability_hedge_ratio_pct": round(liability_hedge_ratio_pct, 2),
            "required_20y_receiver_swap_notional_eur": round(required_receiver_swap_notional_eur, 2),
            "redington_immunization_satisfied": redington_immunized,
            "cashflow_matching_lp": lp_res,
        }


def compute_alm_ldi_immunization(
    asset_portfolio_eur: float = 125_000_000.0,
    asset_modified_duration: float = 6.8,
    asset_convexity: float = 62.0,
    asset_annual_vol: float = 0.095,
    discount_rate: float = 0.034,
    inflation_rate: float = 0.021,
) -> dict[str, Any]:
    """Convenience entrypoint for API and Streamlit UI integration."""
    engine = AlmLdiEngine(
        asset_portfolio_eur=asset_portfolio_eur,
        asset_modified_duration=asset_modified_duration,
        asset_convexity=asset_convexity,
        asset_annual_vol=asset_annual_vol,
        discount_rate=discount_rate,
        inflation_rate=inflation_rate,
    )
    return engine.analyze_alm()
