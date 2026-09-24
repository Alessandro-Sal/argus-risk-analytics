"""
core/solvency2_engine.py
ARGUS — Solvency II Standard Formula & Solvency Capital Requirement (SCR) Engine.
Regulatory Reference: EIOPA Delegated Regulation (EU) 2015/35 & Directive 2009/138/EC.

Modules:
- Market Risk (SCR_market):
    * SCR_equity: Type 1 (EEA/OECD listed, 39% + symm adj), Type 2 (PE/unlisted/commodities, 49% + symm adj)
    * SCR_interest_rate: Up & Down shocks with maturity/duration ladders
    * SCR_property: Real estate shock (25%)
    * SCR_spread: Bonds & structured debt by Credit Quality Step (CQS 0-6) & duration
    * SCR_concentration: Excess exposure above threshold (1.5%-3%)
    * SCR_currency: Foreign exchange shocks (+-25% vs EUR)
    * EIOPA Correlation Aggregation Matrix Omega_market
- Counterparty Default Risk (SCR_default): Type 1 (bank deposits/derivatives) & Type 2
- Basic SCR (BSCR) aggregation
- Operational Risk (SCR_op) capped at 30% BSCR
- Loss-Absorbing Capacity of Technical Provisions (LAC_TP) & Deferred Taxes (LAC_DT)
- Eligible Own Funds & Solvency Ratio (EOF / SCR)
- EIOPA Quantitative Reporting Templates (QRT) data export: S.25.01.21 & S.26.01.01
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# EIOPA Standard CQS Spread Shock Parameters (b_i factors per year of duration)
# CQS: 0 (AAA), 1 (AA), 2 (A), 3 (BBB), 4 (BB), 5 (B), 6 (CCC/unrated)
CQS_SPREAD_FACTORS = {
    0: 0.009,   # 0.90% per duration year
    1: 0.011,   # 1.10%
    2: 0.014,   # 1.40%
    3: 0.025,   # 2.50%
    4: 0.045,   # 4.50%
    5: 0.075,   # 7.50%
    6: 0.100,   # 10.0%
}

# EIOPA Standard Market Sub-Module Correlation Matrices
CORR_MKT_UP = np.array([
    # ir,   eq,  prop, spread, conc,  curr
    [1.00, 0.50, 0.50, 0.50,  0.00, 0.25],   # ir
    [0.50, 1.00, 0.75, 0.75,  0.00, 0.45],   # eq
    [0.50, 0.75, 1.00, 0.50,  0.00, 0.25],   # prop
    [0.50, 0.75, 0.50, 1.00,  0.00, 0.25],   # spread
    [0.00, 0.00, 0.00, 0.00,  1.00, 0.00],   # conc
    [0.25, 0.45, 0.25, 0.25,  0.00, 1.00],   # curr
])

CORR_MKT_DOWN = np.array([
    # ir,   eq,  prop, spread, conc,  curr
    [1.00, 0.00, 0.00, 0.00,  0.00, 0.00],   # ir
    [0.00, 1.00, 0.75, 0.75,  0.00, 0.45],   # eq
    [0.00, 0.75, 1.00, 0.50,  0.00, 0.25],   # prop
    [0.00, 0.75, 0.50, 1.00,  0.00, 0.25],   # spread
    [0.00, 0.00, 0.00, 0.00,  1.00, 0.00],   # conc
    [0.00, 0.45, 0.25, 0.25,  0.00, 1.00],   # curr
])


@dataclass
class Solvency2AssetPosition:
    """Standardized institutional balance sheet asset for Solvency II calculation."""

    asset_id: str
    name: str
    asset_type: str       # 'equity_type1', 'equity_type2', 'bond', 'cash', 'property', 'alternative'
    market_value_eur: float
    currency: str = "EUR"
    modified_duration: float = 0.0
    cqs_rating: int = 2   # Credit Quality Step 0 to 6 (default 2 = A)
    issuer_id: str = ""
    is_strategic_equity: bool = False  # Art 171: 22% shock instead of 39%
    custom_shock_pct: Optional[float] = None


@dataclass
class Solvency2SCRReport:
    """Detailed Solvency II SCR Output structure."""

    eligible_own_funds: float
    scr_total: float
    bscr: float
    scr_operational: float
    lac_adjustment: float
    solvency_ratio_pct: float
    solvency_health: str   # 'OPTIMAL (>160%)', 'ADEQUATE (100-160%)', 'CRITICAL (<100%)'
    scr_market_total: float
    scr_market_submodules: Dict[str, float]
    market_diversification_benefit: float
    scr_counterparty_default: float
    bscr_diversification_benefit: float
    qrt_s25_01: Dict[str, Any]
    qrt_s26_01: Dict[str, Any]
    asset_breakdown_df: pd.DataFrame


class Solvency2Engine:
    """
    EIOPA Solvency II Standard Formula Solvency Capital Requirement (SCR) Engine.
    """

    def __init__(
        self,
        symmetric_equity_adjustment: float = 0.0,
        enable_duration_scaling: bool = True,
        concentration_threshold_pct: float = 3.0,
    ):
        # Symmetric adjustment for equity risk (EIOPA range [-10%, +10%])
        self.symm_adj = float(np.clip(symmetric_equity_adjustment, -0.10, 0.10))
        self.enable_duration_scaling = enable_duration_scaling
        self.conc_threshold = concentration_threshold_pct / 100.0

    def compute_scr_interest_rate(self, positions: List[Solvency2AssetPosition]) -> Tuple[float, str]:
        """
        Computes interest rate risk SCR using duration-weighted up and down shocks:
            SCR_ir_up = sum(V_i * ModDur_i * shock_up)
            SCR_ir_down = sum(V_i * ModDur_i * shock_down)
            SCR_ir = max(SCR_ir_up, SCR_ir_down)
        """
        loss_up = 0.0
        loss_down = 0.0

        for pos in positions:
            if pos.modified_duration > 0.0 and pos.asset_type in ["bond", "cash"]:
                dur = pos.modified_duration
                val = pos.market_value_eur
                # Standard EIOPA simplified shock: +100 bps / -100 bps (capped for low rates)
                shock_up = min(1.0, 0.010 * max(1.0, dur * 0.15))
                shock_down = min(1.0, 0.008 * max(1.0, dur * 0.12))
                loss_up += val * dur * shock_up
                loss_down += val * dur * shock_down

        if loss_up >= loss_down:
            return float(loss_up), "UP"
        else:
            return float(loss_down), "DOWN"

    def compute_scr_equity(self, positions: List[Solvency2AssetPosition]) -> float:
        """
        Computes Equity Risk SCR:
            Type 1: 39% + symm_adj
            Type 2: 49% + symm_adj
            Strategic: 22%
            Aggregated via 2x2 correlation matrix (rho = 0.75).
        """
        type1_shock = 0.39 + self.symm_adj
        type2_shock = 0.49 + self.symm_adj
        strat_shock = 0.22

        loss_t1 = 0.0
        loss_t2 = 0.0

        for pos in positions:
            val = pos.market_value_eur
            if pos.asset_type == "equity_type1":
                shock = strat_shock if pos.is_strategic_equity else type1_shock
                loss_t1 += val * shock
            elif pos.asset_type in ["equity_type2", "alternative"]:
                loss_t2 += val * type2_shock

        # Correlazione Type 1 e Type 2: 0.75
        corr_eq = 0.75
        scr_eq = np.sqrt(loss_t1**2 + loss_t2**2 + 2.0 * corr_eq * loss_t1 * loss_t2)
        return float(scr_eq)

    def compute_scr_property(self, positions: List[Solvency2AssetPosition]) -> float:
        """Property risk: 25% direct shock on real estate assets."""
        loss_prop = 0.0
        for pos in positions:
            if pos.asset_type in ["property", "real_estate"]:
                loss_prop += pos.market_value_eur * 0.25
        return float(loss_prop)

    def compute_scr_spread(self, positions: List[Solvency2AssetPosition]) -> float:
        """
        Credit Spread risk on bonds and loans based on Credit Quality Step (CQS 0-6):
            SCR_spread = sum(V_i * b_i(CQS) * Duration_i)
        """
        loss_spread = 0.0
        for pos in positions:
            if pos.asset_type == "bond":
                dur = max(0.5, pos.modified_duration)
                cqs = int(np.clip(pos.cqs_rating, 0, 6))
                factor = CQS_SPREAD_FACTORS.get(cqs, 0.025)
                loss_spread += pos.market_value_eur * factor * dur
        return float(loss_spread)

    def compute_scr_currency(self, positions: List[Solvency2AssetPosition]) -> float:
        """Currency risk: 25% shock on non-EUR assets."""
        loss_curr = 0.0
        for pos in positions:
            curr = pos.currency.strip().upper()
            if curr not in ["EUR", ""]:
                loss_curr += pos.market_value_eur * 0.25
        return float(loss_curr)

    def compute_scr_concentration(self, positions: List[Solvency2AssetPosition], total_assets: float) -> float:
        """
        Concentration risk: excess exposure above threshold per issuer:
            XS_i = max(0, Exposure_i / TotalAssets - Threshold)
            SCR_conc = sqrt(sum((TotalAssets * XS_i * g_i)^2))
        """
        if total_assets <= 0:
            return 0.0

        issuer_exposures: Dict[str, float] = {}
        for pos in positions:
            issuer = pos.issuer_id or pos.name
            issuer_exposures[issuer] = issuer_exposures.get(issuer, 0.0) + pos.market_value_eur

        conc_sq_sum = 0.0
        for issuer, exp in issuer_exposures.items():
            weight = exp / total_assets
            excess = max(0.0, weight - self.conc_threshold)
            if excess > 0:
                # g_i factor: average 21% for investment grade
                g_factor = 0.21
                loss_i = total_assets * excess * g_factor
                conc_sq_sum += loss_i**2

        return float(np.sqrt(conc_sq_sum))

    def compute_scr_counterparty_default(self, positions: List[Solvency2AssetPosition]) -> float:
        """
        Counterparty Default Risk (simplified Standard Formula Type 1 for cash / deposits).
        Probability of default * Loss Given Default (LGD).
        """
        scr_def = 0.0
        for pos in positions:
            if pos.asset_type == "cash":
                # Bank deposit CQS 2 default rate ~0.005, LGD 50%
                scr_def += pos.market_value_eur * 0.025
        return float(scr_def)

    def compute_scr(
        self,
        positions: List[Solvency2AssetPosition],
        eligible_own_funds: float,
        technical_provisions: float = 0.0,
        earned_premiums: float = 0.0,
        lac_tp: float = 0.0,
        lac_dt: float = 0.0,
    ) -> Solvency2SCRReport:
        """
        Executes full Solvency II Standard Formula capital aggregation:
        1. Sub-modules: Interest Rate, Equity, Property, Spread, Concentration, Currency
        2. Market Risk Aggregation via Omega_market
        3. Basic SCR (BSCR)
        4. Operational Risk SCR_op
        5. Loss Absorbing Capacity
        6. Total Net SCR & Solvency Ratio
        7. QRT data export
        """
        total_assets = sum(pos.market_value_eur for pos in positions)
        if total_assets <= 0:
            total_assets = 1.0

        # 1. Market Risk sub-modules
        scr_ir, dominant_ir_scenario = self.compute_scr_interest_rate(positions)
        scr_eq = self.compute_scr_equity(positions)
        scr_prop = self.compute_scr_property(positions)
        scr_spread = self.compute_scr_spread(positions)
        scr_conc = self.compute_scr_concentration(positions, total_assets)
        scr_curr = self.compute_scr_currency(positions)

        sub_vector = np.array([scr_ir, scr_eq, scr_prop, scr_spread, scr_conc, scr_curr])

        # 2. Market Risk Aggregation
        corr_matrix = CORR_MKT_UP if dominant_ir_scenario == "UP" else CORR_MKT_DOWN
        scr_market_sq = float(sub_vector.T @ corr_matrix @ sub_vector)
        scr_market = float(np.sqrt(max(scr_market_sq, 0.0)))
        undiversified_mkt = float(np.sum(sub_vector))
        mkt_diversification = undiversified_mkt - scr_market

        # 3. Counterparty Default Risk
        scr_def = self.compute_scr_counterparty_default(positions)

        # 4. Basic SCR (BSCR) Aggregation
        # Aggregation of Market and Default (corr = 0.25)
        corr_bscr = 0.25
        bscr_sq = scr_market**2 + scr_def**2 + 2.0 * corr_bscr * scr_market * scr_def
        bscr = float(np.sqrt(max(bscr_sq, 0.0)))
        bscr_diversification = (scr_market + scr_def) - bscr

        # 5. Operational Risk
        # 3% of earned premium or 4% of technical provisions, capped at 30% of BSCR
        raw_op = max(0.04 * technical_provisions, 0.03 * earned_premiums, 0.005 * total_assets)
        scr_op = float(min(0.30 * bscr, raw_op))

        # 6. Loss Absorbing Capacity
        lac_total = float(min(bscr + scr_op, lac_tp + lac_dt))

        # 7. Total Net SCR
        scr_total = float(max(0.0, bscr - lac_total + scr_op))

        # 8. Solvency Ratio
        solvency_ratio = (eligible_own_funds / scr_total * 100.0) if scr_total > 0 else 999.0

        if solvency_ratio >= 160.0:
            health = "OPTIMAL (>160%)"
        elif solvency_ratio >= 100.0:
            health = "ADEQUATE (100-160%)"
        else:
            health = "CRITICAL (<100%)"

        # 9. Asset Breakdown DataFrame
        records = []
        for p in positions:
            records.append({
                "Asset": p.name,
                "Type": p.asset_type,
                "Market Value (EUR)": p.market_value_eur,
                "Weight (%)": (p.market_value_eur / total_assets) * 100.0,
                "Duration": p.modified_duration,
                "CQS": p.cqs_rating,
                "Currency": p.currency,
            })
        asset_df = pd.DataFrame(records)

        # 10. QRT Data Structures
        qrt_s25_01 = {
            "template": "S.25.01.21",
            "title": "Solvency Capital Requirement - Standard Formula",
            "R0010_Market_Risk": round(scr_market, 2),
            "R0020_Counterparty_Default_Risk": round(scr_def, 2),
            "R0030_Basic_SCR": round(bscr, 2),
            "R0130_Operational_Risk": round(scr_op, 2),
            "R0140_LAC_TP": round(lac_tp, 2),
            "R0150_LAC_DT": round(lac_dt, 2),
            "R0200_Total_SCR": round(scr_total, 2),
            "R0210_Eligible_Own_Funds": round(eligible_own_funds, 2),
            "R0220_Solvency_Ratio_Pct": round(solvency_ratio, 2),
        }

        qrt_s26_01 = {
            "template": "S.26.01.01",
            "title": "Market Risk Sub-Modules",
            "R0010_Interest_Rate_Risk": round(scr_ir, 2),
            "R0011_Interest_Rate_Scenario": dominant_ir_scenario,
            "R0020_Equity_Risk": round(scr_eq, 2),
            "R0030_Property_Risk": round(scr_prop, 2),
            "R0040_Spread_Risk": round(scr_spread, 2),
            "R0050_Concentration_Risk": round(scr_conc, 2),
            "R0060_Currency_Risk": round(scr_curr, 2),
            "R0070_Market_Diversification_Benefit": round(mkt_diversification, 2),
            "R0080_Total_Market_Risk": round(scr_market, 2),
        }

        return Solvency2SCRReport(
            eligible_own_funds=eligible_own_funds,
            scr_total=scr_total,
            bscr=bscr,
            scr_operational=scr_op,
            lac_adjustment=lac_total,
            solvency_ratio_pct=solvency_ratio,
            solvency_health=health,
            scr_market_total=scr_market,
            scr_market_submodules={
                "interest_rate": scr_ir,
                "equity": scr_eq,
                "property": scr_prop,
                "spread": scr_spread,
                "concentration": scr_conc,
                "currency": scr_curr,
            },
            market_diversification_benefit=mkt_diversification,
            scr_counterparty_default=scr_def,
            bscr_diversification_benefit=bscr_diversification,
            qrt_s25_01=qrt_s25_01,
            qrt_s26_01=qrt_s26_01,
            asset_breakdown_df=asset_df,
        )


def compute_solvency2_standard_formula(
    portfolio_assets: List[Dict[str, Any]],
    eligible_own_funds: float,
    technical_provisions: float = 0.0,
    symmetric_equity_adjustment: float = 0.0,
) -> Dict[str, Any]:
    """
    Convenience functional API for Solvency II Standard Formula SCR evaluation.
    """
    positions = []
    for a in portfolio_assets:
        positions.append(
            Solvency2AssetPosition(
                asset_id=str(a.get("id", a.get("name", "asset"))),
                name=str(a.get("name", "Asset")),
                asset_type=str(a.get("asset_type", "equity_type1")),
                market_value_eur=float(a.get("market_value_eur", a.get("value", 0.0))),
                currency=str(a.get("currency", "EUR")),
                modified_duration=float(a.get("duration", a.get("modified_duration", 0.0))),
                cqs_rating=int(a.get("cqs_rating", 2)),
                issuer_id=str(a.get("issuer_id", "")),
                is_strategic_equity=bool(a.get("is_strategic", False)),
            )
        )

    engine = Solvency2Engine(symmetric_equity_adjustment=symmetric_equity_adjustment)
    report = engine.compute_scr(
        positions=positions,
        eligible_own_funds=eligible_own_funds,
        technical_provisions=technical_provisions,
    )

    return {
        "eligible_own_funds": report.eligible_own_funds,
        "scr_total": report.scr_total,
        "bscr": report.bscr,
        "scr_operational": report.scr_operational,
        "lac_adjustment": report.lac_adjustment,
        "solvency_ratio_pct": report.solvency_ratio_pct,
        "solvency_health": report.solvency_health,
        "scr_market_total": report.scr_market_total,
        "scr_market_submodules": report.scr_market_submodules,
        "market_diversification_benefit": report.market_diversification_benefit,
        "scr_counterparty_default": report.scr_counterparty_default,
        "qrt_s25_01": report.qrt_s25_01,
        "qrt_s26_01": report.qrt_s26_01,
    }
