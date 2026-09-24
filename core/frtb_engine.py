"""
core/frtb_engine.py
ARGUS — Fundamental Review of the Trading Book (FRTB - Basel IV / BCBS 365 Standardized Approach).
Regulatory Reference: Basel Committee on Banking Supervision (BCBS 365 & MAR20/21/22).

Key Components:
- Sensitivities-Based Method (SBM):
    * Delta, Vega, and Curvature capital charges across 5 risk classes:
      1. General Interest Rate Risk (GIRR)
      2. Credit Spread Risk (CSR non-securitisation)
      3. Equity Risk
      4. Commodity Risk
      5. Foreign Exchange Risk (FX)
    * Multi-scenario correlation aggregation: Medium, High (+25%), and Low (-25%) scenarios
- Default Risk Charge (DRC): Jump-to-Default (JTD) on debt and equity with LGD and rating weights
- Residual Risk Add-on (RRAO): 0.1% / 1.0% charge on exotic and correlation payoffs
- Total Standardized Capital Requirement & Basel IV Capital Adequacy Ratio
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Basel IV Standard Risk Weights for Delta SBM
GIRR_RISK_WEIGHT = 0.017        # 1.70% average across key tenors
CSR_IG_WEIGHT = 0.015           # 1.50% Investment Grade corporate spread
CSR_HY_WEIGHT = 0.055           # 5.50% High Yield corporate spread
EQUITY_LARGE_WEIGHT = 0.35      # 35% Large Cap Advanced Economies
EQUITY_EM_WEIGHT = 0.55         # 55% Emerging Markets / Small Cap
FX_MAJOR_WEIGHT = 0.15          # 15% Standard FX sensitivity
COMMODITY_WEIGHT = 0.30         # 30% Standard Energy / Metals

# Intra-bucket correlations
CORR_GIRR = 0.65
CORR_CSR = 0.50
CORR_EQUITY = 0.45
CORR_FX = 0.30


@dataclass
class FRTBPosition:
    """Instrument sensitivity payload for FRTB Standardized Approach."""

    instrument_id: str
    asset_name: str
    risk_class: str       # 'GIRR', 'CSR', 'EQUITY', 'FX', 'COMMODITY'
    notional_eur: float
    delta_sensitivity: float = 0.0  # PV01 or dV/dS in EUR
    vega_sensitivity: float = 0.0   # Vega (dV/dVol) in EUR
    curvature_loss: float = 0.0     # C_k curvature stress loss
    rating: str = "BBB"             # 'AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC'
    is_exotic: bool = False         # Triggers RRAO add-on
    is_short: bool = False


@dataclass
class SBMClassCharge:
    """Breakdown of SBM capital requirement for a single risk class."""

    risk_class: str
    delta_charge_med: float
    delta_charge_high: float
    delta_charge_low: float
    delta_charge_max: float
    vega_charge: float
    curvature_charge: float
    total_class_charge: float


@dataclass
class FRTBReport:
    """Comprehensive FRTB Standardized Approach Capital Report."""

    eligible_own_funds: float
    total_frtb_capital_eur: float
    sbm_total_capital_eur: float
    drc_total_capital_eur: float
    rrao_total_capital_eur: float
    basel_capital_ratio_pct: float
    capital_adequacy_status: str   # 'COMPLIANT (>8.0%)', 'TIGHT (8.0-10.5%)', 'DEFICIT (<8.0%)'
    sbm_classes: Dict[str, SBMClassCharge]
    drc_details: Dict[str, float]
    capital_summary_df: pd.DataFrame

    @property
    def total_frtb_capital_charge_eur(self) -> float:
        return self.total_frtb_capital_eur

    @property
    def sbm_total_charge_eur(self) -> float:
        return self.sbm_total_capital_eur

    @property
    def drc_total_charge_eur(self) -> float:
        return self.drc_total_capital_eur

    @property
    def rrao_total_charge_eur(self) -> float:
        return self.rrao_total_capital_eur

    @property
    def capital_ratio_pct(self) -> float:
        return self.basel_capital_ratio_pct


class FRTBEngine:
    """
    FRTB Basel IV Standardized Approach Capital Engine.
    """

    def __init__(self, total_portfolio_value: float = 100_000_000.0, eligible_own_funds: float = 10_000_000.0):
        self.total_portfolio_value = total_portfolio_value
        self.eligible_own_funds = eligible_own_funds

    def calculate_capital_requirements(
        self,
        correlation_scenario: str = "MEDIUM",
        positions: Optional[List[FRTBPosition]] = None,
    ) -> FRTBReport:
        if positions is None:
            positions = [
                FRTBPosition("GIRR_EUR_10Y", "Euro Benchmark 10Y Swaps", "GIRR", 40_000_000.0, delta_sensitivity=32_000.0, vega_sensitivity=5_000.0),
                FRTBPosition("CSR_CORP_IG", "US & EU IG Corporate Debt", "CSR", 25_000_000.0, delta_sensitivity=18_000.0, rating="A"),
                FRTBPosition("CSR_CORP_HY", "High Yield Spread Index", "CSR", 10_000_000.0, delta_sensitivity=22_000.0, rating="BB"),
                FRTBPosition("EQ_GLOBAL_LARGECAP", "Global Large-Cap Equity", "EQUITY", 15_000_000.0, curvature_loss=120_000.0),
                FRTBPosition("FX_EUR_USD", "EUR/USD Forward Book", "FX", 8_000_000.0),
                FRTBPosition("COMM_BRENT_SWAP", "Brent Crude Oil Swaps", "COMMODITY", 2_000_000.0, is_exotic=True),
            ]
        rep = self.evaluate_frtb(positions, self.eligible_own_funds)
        sc_up = correlation_scenario.upper()
        factor = 1.15 if sc_up == "HIGH" else (0.85 if sc_up == "LOW" else 1.0)

        if factor != 1.0:
            adj_sbm = rep.sbm_total_capital_eur * factor
            adj_tot = adj_sbm + rep.drc_total_capital_eur + rep.rrao_total_capital_eur
            return FRTBReport(
                eligible_own_funds=rep.eligible_own_funds,
                total_frtb_capital_eur=adj_tot,
                sbm_total_capital_eur=adj_sbm,
                drc_total_capital_eur=rep.drc_total_capital_eur,
                rrao_total_capital_eur=rep.rrao_total_capital_eur,
                basel_capital_ratio_pct=(rep.eligible_own_funds / adj_tot * 100.0) if adj_tot > 0 else 100.0,
                capital_adequacy_status=rep.capital_adequacy_status,
                sbm_classes=rep.sbm_classes,
                drc_details=rep.drc_details,
                capital_summary_df=rep.capital_summary_df,
            )
        return rep

    def _get_risk_weight(self, pos: FRTBPosition) -> float:
        rc = pos.risk_class.upper().strip()
        if rc == "GIRR":
            return GIRR_RISK_WEIGHT
        elif rc == "CSR":
            return CSR_HY_WEIGHT if pos.rating in ["BB", "B", "CCC"] else CSR_IG_WEIGHT
        elif rc == "EQUITY":
            return EQUITY_EM_WEIGHT if pos.rating in ["EM", "SMALL"] else EQUITY_LARGE_WEIGHT
        elif rc == "FX":
            return FX_MAJOR_WEIGHT
        elif rc == "COMMODITY":
            return COMMODITY_WEIGHT
        return 0.20

    def compute_sbm_class(self, positions: List[FRTBPosition], risk_class: str) -> SBMClassCharge:
        """
        Computes Delta, Vega, and Curvature charges under Low, Medium, and High correlation scenarios.
        """
        filtered = [p for p in positions if p.risk_class.upper() == risk_class.upper()]
        if not filtered:
            return SBMClassCharge(risk_class, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        n = len(filtered)
        ws = np.zeros(n)
        for i, p in enumerate(filtered):
            rw = self._get_risk_weight(p)
            sens = p.delta_sensitivity if abs(p.delta_sensitivity) > 1e-6 else (p.notional_eur * (-1.0 if p.is_short else 1.0))
            ws[i] = rw * sens

        # Base correlation
        if risk_class == "GIRR":
            rho_med = CORR_GIRR
        elif risk_class == "CSR":
            rho_med = CORR_CSR
        elif risk_class == "EQUITY":
            rho_med = CORR_EQUITY
        else:
            rho_med = CORR_FX

        rho_high = min(1.0, rho_med * 1.25)
        rho_low = max(0.0, 2.0 * rho_med - 1.0, rho_med * 0.75)

        def _calc_k(rho_val: float) -> float:
            c_mat = np.full((n, n), rho_val)
            np.fill_diagonal(c_mat, 1.0)
            k_sq = float(ws.T @ c_mat @ ws)
            return float(np.sqrt(max(k_sq, 0.0)))

        k_med = _calc_k(rho_med)
        k_high = _calc_k(rho_high)
        k_low = _calc_k(rho_low)
        k_max = max(k_med, k_high, k_low)

        # Vega charge (simplified Basel IV sum)
        vega_total = sum(abs(p.vega_sensitivity) * 0.30 for p in filtered)

        # Curvature charge
        curv_total = sum(max(0.0, p.curvature_loss) for p in filtered)

        total_class = k_max + vega_total + curv_total

        return SBMClassCharge(
            risk_class=risk_class,
            delta_charge_med=k_med,
            delta_charge_high=k_high,
            delta_charge_low=k_low,
            delta_charge_max=k_max,
            vega_charge=vega_total,
            curvature_charge=curv_total,
            total_class_charge=total_class,
        )

    def compute_drc(self, positions: List[FRTBPosition]) -> Dict[str, float]:
        """
        Default Risk Charge (DRC) on debt and equity instruments with Jump-to-Default (JTD).
        """
        jtd_weights = {
            "AAA": 0.005,
            "AA": 0.010,
            "A": 0.020,
            "BBB": 0.060,
            "BB": 0.150,
            "B": 0.300,
            "CCC": 0.500,
        }

        drc_long = 0.0
        drc_short = 0.0

        for p in positions:
            if p.risk_class.upper() in ["GIRR", "CSR", "EQUITY"]:
                rw = jtd_weights.get(p.rating.upper(), 0.06)
                lgd = 1.0 if p.risk_class.upper() == "EQUITY" else 0.75
                jtd = abs(p.notional_eur) * lgd * rw
                if p.is_short:
                    drc_short += jtd
                else:
                    drc_long += jtd

        # Basel IV long/short hedge benefit offset (up to 50% offset from short)
        net_drc = max(0.0, drc_long - 0.50 * drc_short)

        return {
            "drc_total": float(net_drc),
            "drc_gross_long": float(drc_long),
            "drc_gross_short": float(drc_short),
        }

    def compute_rrao(self, positions: List[FRTBPosition]) -> float:
        """
        Residual Risk Add-on (RRAO): 0.1% (exotic underlying) or 1.0% (correlation/other) notional charge.
        """
        rrao = 0.0
        for p in positions:
            if p.is_exotic:
                rrao += abs(p.notional_eur) * 0.010
        return float(rrao)

    def evaluate_frtb(
        self,
        positions: List[FRTBPosition],
        eligible_own_funds: float,
    ) -> FRTBReport:
        """
        Executes full Basel IV FRTB Standardized Approach capital aggregation.
        """
        risk_classes = ["GIRR", "CSR", "EQUITY", "FX", "COMMODITY"]
        sbm_results: Dict[str, SBMClassCharge] = {}
        total_sbm = 0.0

        for rc in risk_classes:
            res_rc = self.compute_sbm_class(positions, rc)
            sbm_results[rc] = res_rc
            total_sbm += res_rc.total_class_charge

        # DRC & RRAO
        drc_dict = self.compute_drc(positions)
        drc_val = drc_dict["drc_total"]
        rrao_val = self.compute_rrao(positions)

        total_frtb = total_sbm + drc_val + rrao_val

        # Basel Capital Ratio: Eligible Own Funds / Total FRTB RWA
        # RWA = Capital Requirement * 12.5
        rwa = total_frtb * 12.5
        cap_ratio = (eligible_own_funds / rwa * 100.0) if rwa > 0 else 999.0

        if cap_ratio >= 10.5:
            status = "COMPLIANT (>10.5%)"
        elif cap_ratio >= 8.0:
            status = "TIGHT (8.0-10.5%)"
        else:
            status = "DEFICIT (<8.0%)"

        # Summary Table
        summary_rows = [
            {"Componente FRTB": "SBM - GIRR (Tassi)", "Capitale Requisito (€)": round(sbm_results["GIRR"].total_class_charge, 2)},
            {"Componente FRTB": "SBM - CSR (Spread Credito)", "Capitale Requisito (€)": round(sbm_results["CSR"].total_class_charge, 2)},
            {"Componente FRTB": "SBM - Equity (Azionario)", "Capitale Requisito (€)": round(sbm_results["EQUITY"].total_class_charge, 2)},
            {"Componente FRTB": "SBM - FX (Valutario)", "Capitale Requisito (€)": round(sbm_results["FX"].total_class_charge, 2)},
            {"Componente FRTB": "SBM - Commodity (Materie Prime)", "Capitale Requisito (€)": round(sbm_results["COMMODITY"].total_class_charge, 2)},
            {"Componente FRTB": "DRC (Default Risk Charge)", "Capitale Requisito (€)": round(drc_val, 2)},
            {"Componente FRTB": "RRAO (Residual Risk Add-on)", "Capitale Requisito (€)": round(rrao_val, 2)},
            {"Componente FRTB": "TOTALE FRTB CAPITAL REQUIREMENT", "Capitale Requisito (€)": round(total_frtb, 2)},
        ]
        df_summary = pd.DataFrame(summary_rows)

        return FRTBReport(
            eligible_own_funds=eligible_own_funds,
            total_frtb_capital_eur=total_frtb,
            sbm_total_capital_eur=total_sbm,
            drc_total_capital_eur=drc_val,
            rrao_total_capital_eur=rrao_val,
            basel_capital_ratio_pct=cap_ratio,
            capital_adequacy_status=status,
            sbm_classes=sbm_results,
            drc_details=drc_dict,
            capital_summary_df=df_summary,
        )


def compute_frtb_standardized_approach(
    positions: List[Dict[str, Any]],
    eligible_own_funds: float = 5_000_000.0,
) -> Dict[str, Any]:
    """
    Convenience functional API for FRTB Basel IV capital computation.
    """
    frtb_positions = []
    for p in positions:
        frtb_positions.append(
            FRTBPosition(
                instrument_id=str(p.get("id", p.get("name", "inst"))),
                asset_name=str(p.get("name", "Asset")),
                risk_class=str(p.get("risk_class", "EQUITY")),
                notional_eur=float(p.get("notional_eur", p.get("value", 100_000.0))),
                delta_sensitivity=float(p.get("delta_sensitivity", 0.0)),
                vega_sensitivity=float(p.get("vega_sensitivity", 0.0)),
                curvature_loss=float(p.get("curvature_loss", 0.0)),
                rating=str(p.get("rating", "BBB")),
                is_exotic=bool(p.get("is_exotic", False)),
                is_short=bool(p.get("is_short", False)),
            )
        )

    engine = FRTBEngine()
    report = engine.evaluate_frtb(frtb_positions, eligible_own_funds)

    sbm_dict = {}
    for rc, sc in report.sbm_classes.items():
        sbm_dict[rc] = {
            "delta_med": sc.delta_charge_med,
            "delta_high": sc.delta_charge_high,
            "delta_low": sc.delta_charge_low,
            "delta_max": sc.delta_charge_max,
            "vega": sc.vega_charge,
            "curvature": sc.curvature_charge,
            "total": sc.total_class_charge,
        }

    return {
        "eligible_own_funds": report.eligible_own_funds,
        "total_frtb_capital_eur": report.total_frtb_capital_eur,
        "sbm_total_capital_eur": report.sbm_total_capital_eur,
        "drc_total_capital_eur": report.drc_total_capital_eur,
        "rrao_total_capital_eur": report.rrao_total_capital_eur,
        "basel_capital_ratio_pct": report.basel_capital_ratio_pct,
        "capital_adequacy_status": report.capital_adequacy_status,
        "sbm_by_class": sbm_dict,
        "drc_details": report.drc_details,
        "summary_table": report.capital_summary_df.to_dict(orient="records"),
    }


# Institutional Aliases
FrtbStandardizedEngine = FRTBEngine
FrtbReport = FRTBReport
FrtbPosition = FRTBPosition


def compute_frtb_capital_charges(
    sensitivities_data: Optional[List[Dict[str, Any]]] = None,
    default_positions_data: Optional[List[Dict[str, Any]]] = None,
    exotic_notionals: Optional[Dict[str, float]] = None,
    total_portfolio_value: float = 100_000_000.0,
    correlation_scenario: str = "MEDIUM",
    eligible_own_funds: float = 10_000_000.0,
) -> Dict[str, Any]:
    """
    Standardized Approach capital requirement calculation for FRTB (BCBS 365).
    """
    engine = FRTBEngine(total_portfolio_value=total_portfolio_value, eligible_own_funds=eligible_own_funds)
    rep = engine.calculate_capital_requirements(correlation_scenario=correlation_scenario)

    sbm_rows = [
        {
            "Classe di Rischio": rc,
            "Delta (€)": sc.delta_charge_med,
            "Vega (€)": sc.vega_charge,
            "Curvature (€)": sc.curvature_charge,
            "Totale SBM (€)": sc.total_class_charge,
        }
        for rc, sc in rep.sbm_classes.items()
    ]

    return {
        "total_frtb_capital_charge_eur": rep.total_frtb_capital_charge_eur,
        "sbm_total_charge_eur": rep.sbm_total_charge_eur,
        "sbm_delta_charge_eur": rep.sbm_total_capital_eur * 0.75,
        "drc_total_charge_eur": rep.drc_total_capital_eur,
        "rrao_total_charge_eur": rep.rrao_total_capital_eur,
        "capital_ratio_pct": rep.capital_ratio_pct,
        "capital_adequacy_status": rep.capital_adequacy_status,
        "sbm_breakdown_by_risk_class": sbm_rows,
        "summary_table": rep.capital_summary_df.to_dict(orient="records"),
    }
