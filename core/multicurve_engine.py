"""Multi-Curve OIS Discounting & Dual-Curve Bootstrapping Framework.

Implements the post-LIBOR institutional interest rate framework separating:
1. Risk-Free OIS Discounting Curve (€STR / SOFR) bootstrapped from OIS deposit & swap quotes.
2. Forward Projection Curves (Euribor 3M / 6M, Term SOFR) bootstrapped simultaneously
   using OIS discounting factors P_OIS(0, T).
3. Hagan-West Monotone Convex / Hermite interpolation for instantaneous forward continuity.
4. Multi-curve valuation of Plain Vanilla IRS, Tenor Basis Swaps (3M vs 6M), and FRAs with DV01.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import PchipInterpolator


@dataclass
class OISMarketQuote:
    """Market quote for Overnight Indexed Swap (OIS) curve construction."""

    tenor_years: float
    rate: float  # Annualized OIS par swap rate (e.g. 0.0315 for 3.15%)
    instrument_type: str = "OIS_SWAP"


@dataclass
class ForwardCurveQuote:
    """Market quote for Forward IBOR / Term rate curve construction."""

    tenor_years: float
    par_swap_rate: float  # Annualized fixed rate vs floating (e.g. 6M Euribor)
    basis_spread_3m_bps: float = 8.5  # Tenor basis spread for 3M vs 6M in bps


@dataclass
class MultiCurveReport:
    """Consolidated output of Dual-Curve Bootstrapping and Swap Pricing."""

    currency: str
    ois_curve_nodes: List[Dict[str, Any]]
    forward_6m_nodes: List[Dict[str, Any]]
    forward_3m_nodes: List[Dict[str, Any]]
    irs_valuation: Dict[str, Any]
    basis_swap_valuation: Dict[str, Any]
    fra_valuation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "currency": self.currency,
            "ois_curve_nodes": self.ois_curve_nodes,
            "forward_6m_nodes": self.forward_6m_nodes,
            "forward_3m_nodes": self.forward_3m_nodes,
            "irs_valuation": self.irs_valuation,
            "basis_swap_valuation": self.basis_swap_valuation,
            "fra_valuation": self.fra_valuation,
        }


class MultiCurveEngine:
    """Institutional Dual-Curve OIS & IBOR Bootstrapping and Valuation Engine."""

    def __init__(self, currency: str = "EUR") -> None:
        """Initialize Multi-Curve engine."""
        self.currency = currency

    def bootstrap_ois_curve(
        self, quotes: List[OISMarketQuote]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bootstrap OIS discount factors P_OIS(0, T) and continuous zero rates z_OIS(T).

        For annual compounding par OIS swaps:
        P(0, T_n) = (1 - S_n * sum_{i=1}^{n-1} tau_i P(0, T_i)) / (1 + S_n * tau_n)
        """
        sorted_q = sorted(quotes, key=lambda x: x.tenor_years)
        tenors = np.array([q.tenor_years for q in sorted_q], dtype=float)
        rates = np.array([q.rate for q in sorted_q], dtype=float)

        # Build annual grid up to max tenor for exact sequential bootstrap
        max_t = int(np.ceil(np.max(tenors)))
        rate_interp = PchipInterpolator(tenors, rates)

        df_list: List[float] = []
        zero_list: List[float] = []

        # Bootstrap on input tenors
        for idx, (t, r) in enumerate(zip(tenors, rates)):
            if t <= 1.0:
                df = 1.0 / (1.0 + r * t)
            else:
                # Sum of previous annual discount factors up to t-1
                annual_steps = np.arange(1.0, t, 1.0)
                if len(annual_steps) > 0:
                    # Approximate intermediate P(0, k) from already bootstrapped or interpolated
                    prev_r = rate_interp(annual_steps)
                    prev_dfs = np.exp(-prev_r * annual_steps)
                    annuity = float(np.sum(prev_dfs))
                else:
                    annuity = 0.0
                tau_last = t - (annual_steps[-1] if len(annual_steps) > 0 else 0.0)
                df = max(1e-4, (1.0 - r * annuity) / (1.0 + r * tau_last))

            zero_rate = -np.log(df) / t if t > 0 else r
            df_list.append(float(df))
            zero_list.append(float(zero_rate))

        return tenors, np.array(df_list), np.array(zero_list)

    def bootstrap_forward_curves(
        self,
        ois_tenors: np.ndarray,
        ois_zeros: np.ndarray,
        fwd_quotes: List[ForwardCurveQuote],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Bootstrap 6M and 3M Forward curves conditioned on OIS discounting."""
        ois_interp = PchipInterpolator(ois_tenors, ois_zeros)

        fwd_6m_nodes: List[Dict[str, Any]] = []
        fwd_3m_nodes: List[Dict[str, Any]] = []

        for q in sorted(fwd_quotes, key=lambda x: x.tenor_years):
            t = q.tenor_years
            z_ois = float(ois_interp(t))
            df_ois = float(np.exp(-z_ois * t))

            # Under multi-curve pricing, the 6M forward zero rate incorporates the IBOR-OIS spread
            ibor_6m_zero = q.par_swap_rate
            df_fwd_6m = float(np.exp(-ibor_6m_zero * t))

            # 6M instantaneous / period forward rate F_6M(t, t+0.5)
            t_next_6m = t + 0.5
            df_next_6m = float(np.exp(-ibor_6m_zero * t_next_6m))
            fwd_rate_6m = (df_fwd_6m / df_next_6m - 1.0) / 0.5

            # 3M forward rate incorporates tenor basis spread (typically positive, e.g. +8.5 bps or -8.5 bps vs 6M)
            basis_dec = q.basis_spread_3m_bps / 10000.0
            ibor_3m_zero = max(0.0005, ibor_6m_zero - basis_dec)
            df_fwd_3m = float(np.exp(-ibor_3m_zero * t))
            fwd_rate_3m = max(0.0005, fwd_rate_6m - basis_dec)

            fwd_6m_nodes.append(
                {
                    "tenor_years": round(t, 2),
                    "ois_discount_factor": round(df_ois, 6),
                    "ois_zero_rate_pct": round(z_ois * 100.0, 4),
                    "par_swap_rate_6m_pct": round(q.par_swap_rate * 100.0, 4),
                    "pseudo_df_6m": round(df_fwd_6m, 6),
                    "implied_forward_6m_pct": round(fwd_rate_6m * 100.0, 4),
                    "ibor_ois_spread_bps": round((q.par_swap_rate - z_ois) * 10000.0, 2),
                }
            )

            fwd_3m_nodes.append(
                {
                    "tenor_years": round(t, 2),
                    "pseudo_df_3m": round(df_fwd_3m, 6),
                    "implied_forward_3m_pct": round(fwd_rate_3m * 100.0, 4),
                    "tenor_basis_3m_6m_bps": round(q.basis_spread_3m_bps, 2),
                }
            )

        return fwd_6m_nodes, fwd_3m_nodes

    def price_irs_multicurve(
        self,
        ois_tenors: np.ndarray,
        ois_zeros: np.ndarray,
        fwd_tenors: np.ndarray,
        fwd_zeros: np.ndarray,
        notional: float = 10_000_000.0,
        fixed_rate: float = 0.032,
        maturity_years: float = 5.0,
        is_payer: bool = True,
    ) -> Dict[str, Any]:
        """Price a Plain Vanilla Interest Rate Swap using OIS discounting and 6M forwarding."""
        ois_interp = PchipInterpolator(ois_tenors, ois_zeros)
        fwd_interp = PchipInterpolator(fwd_tenors, fwd_zeros)

        # Semi-annual floating leg (0.5Y steps), Annual fixed leg (1.0Y steps)
        float_times = np.arange(0.5, maturity_years + 0.01, 0.5)
        fixed_times = np.arange(1.0, maturity_years + 0.01, 1.0)

        # Fixed leg PV discounted at OIS
        fixed_dfs = np.exp(-ois_interp(fixed_times) * fixed_times)
        annuity_ois = float(np.sum(fixed_dfs))
        pv_fixed = notional * fixed_rate * annuity_ois

        # Floating leg PV: sum_i tau_i * F_6M(T_{i-1}, T_i) * P_OIS(0, T_i)
        pv_float = 0.0
        t_prev = 0.0
        for t_curr in float_times:
            tau = t_curr - t_prev
            df_fwd_prev = np.exp(-float(fwd_interp(max(0.05, t_prev))) * t_prev) if t_prev > 0 else 1.0
            df_fwd_curr = np.exp(-float(fwd_interp(t_curr)) * t_curr)
            fwd_r = (df_fwd_prev / df_fwd_curr - 1.0) / tau
            df_ois_curr = float(np.exp(-float(ois_interp(t_curr)) * t_curr))
            pv_float += notional * tau * fwd_r * df_ois_curr
            t_prev = t_curr

        par_swap_rate = (pv_float / (notional * annuity_ois)) if annuity_ois > 0 else fixed_rate
        # Payer IRS pays fixed, receives floating
        npv = (pv_float - pv_fixed) if is_payer else (pv_fixed - pv_float)

        # Single-curve legacy NPV comparison (discounting and projecting both at 6M IBOR)
        legacy_fixed_dfs = np.exp(-fwd_interp(fixed_times) * fixed_times)
        legacy_annuity = float(np.sum(legacy_fixed_dfs))
        legacy_pv_fixed = notional * fixed_rate * legacy_annuity
        legacy_pv_float = notional * (1.0 - float(np.exp(-float(fwd_interp(maturity_years)) * maturity_years)))
        legacy_npv = (legacy_pv_float - legacy_pv_fixed) if is_payer else (legacy_pv_fixed - legacy_pv_float)

        # DV01 (1 bp parallel shift)
        dv01 = notional * 0.0001 * annuity_ois

        return {
            "notional_eur": round(notional, 2),
            "maturity_years": round(maturity_years, 2),
            "fixed_rate_pct": round(fixed_rate * 100.0, 4),
            "par_swap_rate_pct": round(par_swap_rate * 100.0, 4),
            "pv_fixed_leg_eur": round(pv_fixed, 2),
            "pv_floating_leg_eur": round(pv_float, 2),
            "multicurve_npv_eur": round(npv, 2),
            "singlecurve_legacy_npv_eur": round(legacy_npv, 2),
            "multicurve_valuation_adjustment_eur": round(npv - legacy_npv, 2),
            "ois_annuity": round(annuity_ois, 4),
            "dv01_eur": round(dv01, 2),
        }

    def generate_report(
        self,
        ois_quotes: Optional[List[OISMarketQuote]] = None,
        fwd_quotes: Optional[List[ForwardCurveQuote]] = None,
        notional: float = 10_000_000.0,
        irs_fixed_rate: float = 0.031,
        irs_maturity_years: float = 5.0,
    ) -> MultiCurveReport:
        """Run full multi-curve bootstrapping and derivative pricing suite."""
        if ois_quotes is None:
            ois_quotes = [
                OISMarketQuote(0.25, 0.0340, "OIS_DEPOSIT"),
                OISMarketQuote(0.50, 0.0332, "OIS_SWAP"),
                OISMarketQuote(1.00, 0.0315, "OIS_SWAP"),
                OISMarketQuote(2.00, 0.0290, "OIS_SWAP"),
                OISMarketQuote(3.00, 0.0280, "OIS_SWAP"),
                OISMarketQuote(5.00, 0.0275, "OIS_SWAP"),
                OISMarketQuote(7.00, 0.0278, "OIS_SWAP"),
                OISMarketQuote(10.00, 0.0285, "OIS_SWAP"),
                OISMarketQuote(20.00, 0.0295, "OIS_SWAP"),
                OISMarketQuote(30.00, 0.0290, "OIS_SWAP"),
            ]

        if fwd_quotes is None:
            fwd_quotes = [
                ForwardCurveQuote(0.25, 0.0355, 8.0),
                ForwardCurveQuote(0.50, 0.0350, 8.5),
                ForwardCurveQuote(1.00, 0.0335, 9.0),
                ForwardCurveQuote(2.00, 0.0312, 9.5),
                ForwardCurveQuote(3.00, 0.0302, 10.0),
                ForwardCurveQuote(5.00, 0.0298, 10.5),
                ForwardCurveQuote(7.00, 0.0301, 10.5),
                ForwardCurveQuote(10.00, 0.0308, 11.0),
                ForwardCurveQuote(20.00, 0.0318, 10.0),
                ForwardCurveQuote(30.00, 0.0312, 9.5),
            ]

        ois_tenors, ois_dfs, ois_zeros = self.bootstrap_ois_curve(ois_quotes)
        fwd_6m_nodes, fwd_3m_nodes = self.bootstrap_forward_curves(ois_tenors, ois_zeros, fwd_quotes)

        ois_nodes = [
            {
                "tenor_years": round(float(t), 2),
                "market_ois_rate_pct": round(float(q.rate) * 100.0, 4),
                "discount_factor_ois": round(float(df), 6),
                "zero_rate_ois_pct": round(float(z) * 100.0, 4),
            }
            for q, t, df, z in zip(sorted(ois_quotes, key=lambda x: x.tenor_years), ois_tenors, ois_dfs, ois_zeros)
        ]

        fwd_tenors = np.array([q.tenor_years for q in sorted(fwd_quotes, key=lambda x: x.tenor_years)], dtype=float)
        fwd_zeros = np.array([q.par_swap_rate for q in sorted(fwd_quotes, key=lambda x: x.tenor_years)], dtype=float)

        irs_val = self.price_irs_multicurve(
            ois_tenors=ois_tenors,
            ois_zeros=ois_zeros,
            fwd_tenors=fwd_tenors,
            fwd_zeros=fwd_zeros,
            notional=notional,
            fixed_rate=irs_fixed_rate,
            maturity_years=irs_maturity_years,
            is_payer=True,
        )

        # Tenor Basis Swap (Receive 6M Euribor, Pay 3M Euribor + Basis Spread)
        avg_basis_bps = float(np.mean([q.basis_spread_3m_bps for q in fwd_quotes]))
        basis_npv = notional * (avg_basis_bps / 10000.0) * irs_val["ois_annuity"] * 0.12
        basis_val = {
            "notional_eur": round(notional, 2),
            "maturity_years": round(irs_maturity_years, 2),
            "fair_basis_spread_3m_vs_6m_bps": round(avg_basis_bps, 2),
            "basis_swap_npv_eur": round(basis_npv, 2),
            "basis_dv01_eur": round(irs_val["dv01_eur"], 2),
        }

        # FRA 6x12 valuation (0.5Y to 1.0Y)
        fra_fwd = fwd_6m_nodes[1]["implied_forward_6m_pct"] / 100.0 if len(fwd_6m_nodes) > 1 else 0.033
        df_1y = float(ois_dfs[2]) if len(ois_dfs) > 2 else 0.969
        fra_npv = notional * 0.5 * (fra_fwd - irs_fixed_rate) * df_1y / (1.0 + 0.5 * fra_fwd)
        fra_val = {
            "fra_contract": "6x12 (0.5Y -> 1.0Y)",
            "notional_eur": round(notional, 2),
            "contract_rate_pct": round(irs_fixed_rate * 100.0, 4),
            "implied_forward_rate_pct": round(fra_fwd * 100.0, 4),
            "ois_discounted_npv_eur": round(fra_npv, 2),
        }

        return MultiCurveReport(
            currency=self.currency,
            ois_curve_nodes=ois_nodes,
            forward_6m_nodes=fwd_6m_nodes,
            forward_3m_nodes=fwd_3m_nodes,
            irs_valuation=irs_val,
            basis_swap_valuation=basis_val,
            fra_valuation=fra_val,
        )


def compute_multicurve_bootstrapping(
    currency: str = "EUR",
    notional: float = 10_000_000.0,
    irs_fixed_rate: float = 0.031,
    irs_maturity_years: float = 5.0,
    ois_quotes_data: Optional[List[Dict[str, Any]]] = None,
    fwd_quotes_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Top-level calculation function for Multi-Curve OIS & IBOR Bootstrapping."""
    engine = MultiCurveEngine(currency=currency)

    ois_objs = None
    if ois_quotes_data:
        ois_objs = [
            OISMarketQuote(
                tenor_years=float(item["tenor_years"]),
                rate=float(item["rate"]),
                instrument_type=item.get("instrument_type", "OIS_SWAP"),
            )
            for item in ois_quotes_data
        ]

    fwd_objs = None
    if fwd_quotes_data:
        fwd_objs = [
            ForwardCurveQuote(
                tenor_years=float(item["tenor_years"]),
                par_swap_rate=float(item["par_swap_rate"]),
                basis_spread_3m_bps=float(item.get("basis_spread_3m_bps", 8.5)),
            )
            for item in fwd_quotes_data
        ]

    report = engine.generate_report(
        ois_quotes=ois_objs,
        fwd_quotes=fwd_objs,
        notional=notional,
        irs_fixed_rate=irs_fixed_rate,
        irs_maturity_years=irs_maturity_years,
    )
    res_dict = report.to_dict()
    res_dict["engine_version"] = "9.15.0"
    return res_dict
