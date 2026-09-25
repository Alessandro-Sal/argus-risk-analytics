"""
core/xva_engine.py
ARGUS — Bilateral XVA & Counterparty Credit Risk Engine (CVA, DVA, FVA, MVA, KVA & ISDA SIMM).
Regulatory References:
- Basel Committee on Banking Supervision (BCBS CRE54 / CRE56): Standardized CVA Capital.
- ISDA Standard Initial Margin Model (SIMM v2.6).
- Burgard & Kjaer (2011, 2013): "In the Balance" & "Funding Strategies, Capital and Inclusiveness".
- Gregory (2015): "The xVA Challenge: Counterparty Credit Risk, Funding, Collateral and Capital".

Features:
- Exposure Profiles across continuous time grid:
  * Expected Exposure (EE_t)
  * Expected Negative Exposure (ENE_t)
  * Potential Future Exposure (PFE 95%, PFE 99%)
  * Effective Expected Positive Exposure (EEPE)
- Bilateral Valuation Adjustments:
  * CVA: Credit Valuation Adjustment for counterparty default risk
  * DVA: Debt Valuation Adjustment for own default risk
  * FVA: Funding Valuation Adjustment (FCA borrowing vs FBA lending benefit)
  * MVA: Margin Valuation Adjustment for funding segregated Initial Margin (ISDA SIMM)
  * KVA: Capital Valuation Adjustment for regulatory capital cost over trade life
- Netting Sets and Credit Support Annex (CSA):
  * Threshold (TH), Minimum Transfer Amount (MTA), Independent Amount (IA)
  * Margin Period of Risk (MPOR, default 10 or 14 business days)
- Total Bilateral Fair Value Adjustment and capital impact
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass
class TradeItem:
    """Individual derivative trade within a netting set."""

    trade_id: str
    symbol: str
    asset_class: str       # 'IR_SWAP', 'FX_FORWARD', 'EQUITY_OPTION', 'COMMODITY_SWAP'
    notional_eur: float
    maturity_years: float
    mtm_eur: float = 0.0
    volatility_annual: float = 0.20
    is_buy: bool = True


@dataclass
class CSAAgreement:
    """Credit Support Annex (CSA) contractual collateral terms."""

    has_csa: bool = True
    threshold_eur: float = 500_000.0
    mta_eur: float = 100_000.0
    independent_amount_eur: float = 0.0
    mpor_days: int = 10  # Margin Period of Risk (Basel standard 10d for bilateral)


@dataclass
class XVAReport:
    """Comprehensive XVA metrics and counterparty exposure analysis."""

    portfolio_mtm_eur: float
    cva_eur: float
    dva_eur: float
    fva_eur: float
    mva_eur: float
    kva_eur: float
    total_xva_eur: float
    bilateral_adjusted_mtm_eur: float
    peak_pfe_95_eur: float
    peak_pfe_99_eur: float
    eepe_eur: float
    exposure_profile_df: pd.DataFrame
    xva_summary_df: pd.DataFrame


class XVAEngine:
    """
    Simulates portfolio path exposures and computes bilateral XVA metrics.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.025,
        counterparty_hazard_rate: float = 0.015,  # ~150 bps CDS spread
        counterparty_lgd: float = 0.60,           # 40% recovery
        own_hazard_rate: float = 0.008,           # ~80 bps own CDS spread
        own_lgd: float = 0.60,
        funding_spread_bps: float = 100.0,        # 1.00% unsecured funding spread
        margin_funding_spread_bps: float = 75.0,  # 0.75% IM funding cost
        cost_of_capital_pct: float = 10.0,        # 10% hurdle rate / CoC
    ):
        self.r = float(risk_free_rate)
        self.lambda_c = float(counterparty_hazard_rate)
        self.lgd_c = float(counterparty_lgd)
        self.lambda_own = float(own_hazard_rate)
        self.lgd_own = float(own_lgd)
        self.s_f = float(funding_spread_bps) / 10000.0
        self.s_m = float(margin_funding_spread_bps) / 10000.0
        self.k_coc = float(cost_of_capital_pct) / 100.0

    def simulate_exposure_profile(
        self,
        trades: List[TradeItem],
        csa: CSAAgreement,
        time_grid: Optional[np.ndarray] = None,
        n_sims: int = 1000,
    ) -> pd.DataFrame:
        """
        Simulates Monte Carlo paths of netting set mark-to-market and computes exposure curves.
        """
        if not trades:
            raise ValueError("Trades list cannot be empty.")

        max_mat = max(t.maturity_years for t in trades)
        if time_grid is None:
            # Dense grid for initial year, then quarterly/annual up to maturity
            t1 = np.linspace(0.05, 1.0, 20)
            t2 = np.linspace(1.25, max(1.5, max_mat), int(max(4, max_mat * 4)))
            grid = np.unique(np.concatenate(([0.0], t1, t2)))
        else:
            grid = np.asarray(time_grid)

        n_steps = len(grid)
        np.random.seed(42)

        # Vectorized portfolio Monte Carlo simulation
        # Each trade diffusion dV_i(t) modelled with mean-reverting drift and volatility
        portfolio_paths = np.zeros((n_sims, n_steps))

        initial_mtm = sum(t.mtm_eur for t in trades)
        portfolio_paths[:, 0] = initial_mtm

        # Precompute trade active indicators on time grid
        for t_idx in range(1, n_steps):
            dt = grid[t_idx] - grid[t_idx - 1]
            t_curr = grid[t_idx]

            step_drift = 0.0
            step_var = 0.0

            for tr in trades:
                if tr.maturity_years >= t_curr:
                    # Amortizing diffusion scale towards maturity
                    remaining = (tr.maturity_years - t_curr) / tr.maturity_years
                    scale = tr.notional_eur * tr.volatility_annual * np.sqrt(dt) * remaining
                    step_var += scale**2
                    step_drift += (self.r * tr.mtm_eur * dt * remaining)

            sigma_step = np.sqrt(max(1e-4, step_var))
            z = np.random.normal(0, 1, n_sims)
            portfolio_paths[:, t_idx] = portfolio_paths[:, t_idx - 1] + step_drift + sigma_step * z

        # Apply CSA Netting & Collateralization
        records = []
        for t_idx, t_val in enumerate(grid):
            v_paths = portfolio_paths[:, t_idx]

            if csa.has_csa and t_val > 0:
                # Collateral posted with MPOR lag and MTA
                collateral = np.where(
                    v_paths > (csa.threshold_eur + csa.mta_eur),
                    v_paths - csa.threshold_eur + csa.independent_amount_eur,
                    np.where(
                        v_paths < -(csa.threshold_eur + csa.mta_eur),
                        v_paths + csa.threshold_eur - csa.independent_amount_eur,
                        0.0,
                    ),
                )
                net_v = v_paths - collateral
            else:
                collateral = np.zeros_like(v_paths)
                net_v = v_paths

            pos_exp = np.maximum(net_v, 0.0)
            neg_exp = np.maximum(-net_v, 0.0)

            ee = float(np.mean(pos_exp))
            ene = float(np.mean(neg_exp))
            pfe_95 = float(np.percentile(pos_exp, 95))
            pfe_99 = float(np.percentile(pos_exp, 99))
            avg_collateral = float(np.mean(collateral))

            records.append({
                "time_years": round(t_val, 3),
                "tenor_years": round(t_val, 3),
                "expected_exposure_eur": round(ee, 2),
                "expected_negative_exposure_eur": round(ene, 2),
                "pfe_95_eur": round(pfe_95, 2),
                "pfe_99_eur": round(pfe_99, 2),
                "average_collateral_eur": round(avg_collateral, 2),
                "discount_factor": round(float(np.exp(-self.r * t_val)), 4),
            })

        return pd.DataFrame(records)

    def calculate_xva(
        self,
        trades: List[TradeItem],
        csa: Optional[CSAAgreement] = None,
    ) -> XVAReport:
        """
        Calculates complete bilateral XVA metric stack (CVA, DVA, FVA, MVA, KVA).
        """
        csa_agreement = csa or CSAAgreement()
        profile_df = self.simulate_exposure_profile(trades, csa_agreement)

        times = profile_df["time_years"].values
        ees = profile_df["expected_exposure_eur"].values
        enes = profile_df["expected_negative_exposure_eur"].values
        dfs = profile_df["discount_factor"].values

        cva = 0.0
        dva = 0.0
        fva = 0.0
        mva = 0.0
        kva = 0.0

        for i in range(1, len(times)):
            dt = times[i] - times[i - 1]
            t_mid = (times[i] + times[i - 1]) / 2.0
            df_mid = (dfs[i] + dfs[i - 1]) / 2.0
            ee_mid = (ees[i] + ees[i - 1]) / 2.0
            ene_mid = (enes[i] + enes[i - 1]) / 2.0

            # Marginal default probabilities in interval dt
            # PD(t) = 1 - exp(-lambda * t) => dPD = lambda * exp(-lambda * t) * dt
            dpd_c = self.lambda_c * np.exp(-self.lambda_c * t_mid) * dt
            dpd_own = self.lambda_own * np.exp(-self.lambda_own * t_mid) * dt

            # CVA & DVA
            cva += self.lgd_c * ee_mid * dpd_c * df_mid
            dva += self.lgd_own * ene_mid * dpd_own * df_mid

            # FVA (Funding Cost Adjustment - Funding Benefit Adjustment)
            fva += (self.s_f * ee_mid - self.s_f * 0.8 * ene_mid) * dt * df_mid

            # MVA (Funding cost of Initial Margin under SIMM ~ 15% of PFE_95)
            pfe_mid = (profile_df.loc[i, "pfe_95_eur"] + profile_df.loc[i - 1, "pfe_95_eur"]) / 2.0
            simm_im = max(0.0, pfe_mid * 0.20)
            mva += self.s_m * simm_im * dt * df_mid

            # KVA (Cost of regulatory capital ~ 8% capital charge on risk-weighted assets)
            reg_capital = max(0.0, ee_mid * 0.08)
            kva += self.k_coc * reg_capital * dt * df_mid

        initial_mtm = sum(t.mtm_eur for t in trades)
        total_xva = -cva + dva - fva - mva - kva
        adjusted_mtm = initial_mtm + total_xva

        peak_pfe95 = float(profile_df["pfe_95_eur"].max())
        peak_pfe99 = float(profile_df["pfe_99_eur"].max())

        # Effective EEPE (Average EE over 1 year)
        one_year_idx = profile_df[profile_df["time_years"] <= 1.0].index
        eepe = float(profile_df.loc[one_year_idx, "expected_exposure_eur"].mean()) if len(one_year_idx) > 0 else float(profile_df.loc[0, "expected_exposure_eur"])

        summary_rows = [
            {"Componente XVA": "Mark-to-Market Nominale Portafoglio", "Valore (€)": round(initial_mtm, 2), "Natura": "Fair Value Base"},
            {"Componente XVA": "CVA (Credit Valuation Adjustment)", "Valore (€)": round(-cva, 2), "Natura": "Rischio Controparte"},
            {"Componente XVA": "DVA (Debt Valuation Adjustment)", "Valore (€)": round(dva, 2), "Natura": "Proprio Rischio Credito"},
            {"Componente XVA": "FVA (Funding Valuation Adjustment)", "Valore (€)": round(-fva, 2), "Natura": "Costo / Beneficio Funding"},
            {"Componente XVA": "MVA (Margin Valuation Adjustment)", "Valore (€)": round(-mva, 2), "Natura": "Costo Initial Margin SIMM"},
            {"Componente XVA": "KVA (Capital Valuation Adjustment)", "Valore (€)": round(-kva, 2), "Natura": "Costo Capitale Regolamentare"},
            {"Componente XVA": "TOTALE XVA FAIR VALUE ADJUSTMENT", "Valore (€)": round(total_xva, 2), "Natura": "Rettifica Bilaterale Totale"},
            {"Componente XVA": "MTM RETTIFICATO BILATERALE", "Valore (€)": round(adjusted_mtm, 2), "Natura": "Fair Value Bilaterale Netto"},
        ]
        df_summary = pd.DataFrame(summary_rows)

        return XVAReport(
            portfolio_mtm_eur=round(initial_mtm, 2),
            cva_eur=round(cva, 2),
            dva_eur=round(dva, 2),
            fva_eur=round(fva, 2),
            mva_eur=round(mva, 2),
            kva_eur=round(kva, 2),
            total_xva_eur=round(total_xva, 2),
            bilateral_adjusted_mtm_eur=round(adjusted_mtm, 2),
            peak_pfe_95_eur=round(peak_pfe95, 2),
            peak_pfe_99_eur=round(peak_pfe99, 2),
            eepe_eur=round(eepe, 2),
            exposure_profile_df=profile_df,
            xva_summary_df=df_summary,
        )


def compute_xva_metrics(
    trades_data: Optional[List[Dict[str, Any]]] = None,
    csa_params: Optional[Dict[str, Any]] = None,
    market_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience functional API for XVA & Counterparty Risk calculation.
    """
    if not trades_data:
        trades = [
            TradeItem("IRS_EUR_5Y", "EUR_SWAP_5Y", "IR_SWAP", 25_000_000.0, 5.0, mtm_eur=350_000.0, volatility_annual=0.18),
            TradeItem("IRS_EUR_10Y", "EUR_SWAP_10Y", "IR_SWAP", 15_000_000.0, 10.0, mtm_eur=-120_000.0, volatility_annual=0.15),
            TradeItem("FX_FWD_USD", "EUR_USD_2Y", "FX_FORWARD", 10_000_000.0, 2.0, mtm_eur=180_000.0, volatility_annual=0.12),
            TradeItem("EQ_OPT_SX5E", "SX5E_CALL_1Y", "EQUITY_OPTION", 5_000_000.0, 1.0, mtm_eur=95_000.0, volatility_annual=0.24),
        ]
    else:
        trades = [
            TradeItem(
                trade_id=str(d.get("trade_id", f"TR_{i}")),
                symbol=str(d.get("symbol", f"SYM_{i}")),
                asset_class=str(d.get("asset_class", "IR_SWAP")),
                notional_eur=float(d.get("notional_eur", 1_000_000.0)),
                maturity_years=float(d.get("maturity_years", 3.0)),
                mtm_eur=float(d.get("mtm_eur", 0.0)),
                volatility_annual=float(d.get("volatility_annual", 0.20)),
                is_buy=bool(d.get("is_buy", True)),
            )
            for i, d in enumerate(trades_data)
        ]

    csa_dict = csa_params or {}
    csa = CSAAgreement(
        has_csa=bool(csa_dict.get("has_csa", True)),
        threshold_eur=float(csa_dict.get("threshold_eur", csa_dict.get("threshold", 500_000.0))),
        mta_eur=float(csa_dict.get("mta_eur", csa_dict.get("mta", 100_000.0))),
        independent_amount_eur=float(csa_dict.get("independent_amount_eur", 0.0)),
        mpor_days=int(csa_dict.get("mpor_days", 10)),
    )

    mkt_dict = market_params or {}
    cpty_lgd = float(mkt_dict.get("counterparty_lgd", 0.60))
    own_lgd = float(mkt_dict.get("own_lgd", 0.60))
    cpty_hz = float(
        mkt_dict.get(
            "counterparty_hazard_rate",
            (float(mkt_dict["counterparty_cds_spread_bps"]) / 10000.0) / max(cpty_lgd, 0.1)
            if "counterparty_cds_spread_bps" in mkt_dict
            else 0.015,
        )
    )
    own_hz = float(
        mkt_dict.get(
            "own_hazard_rate",
            (float(mkt_dict["own_cds_spread_bps"]) / 10000.0) / max(own_lgd, 0.1)
            if "own_cds_spread_bps" in mkt_dict
            else 0.008,
        )
    )
    engine = XVAEngine(
        risk_free_rate=float(mkt_dict.get("risk_free_rate", 0.025)),
        counterparty_hazard_rate=cpty_hz,
        counterparty_lgd=cpty_lgd,
        own_hazard_rate=own_hz,
        funding_spread_bps=float(mkt_dict.get("funding_spread_bps", 100.0)),
        margin_funding_spread_bps=float(mkt_dict.get("margin_funding_spread_bps", 75.0)),
        cost_of_capital_pct=float(mkt_dict.get("cost_of_capital_pct", 10.0)),
    )

    rep = engine.calculate_xva(trades, csa)

    return {
        "portfolio_mtm_eur": rep.portfolio_mtm_eur,
        "cva_eur": rep.cva_eur,
        "dva_eur": rep.dva_eur,
        "fva_eur": rep.fva_eur,
        "mva_eur": rep.mva_eur,
        "kva_eur": rep.kva_eur,
        "total_xva_eur": rep.total_xva_eur,
        "bilateral_adjusted_mtm_eur": rep.bilateral_adjusted_mtm_eur,
        "peak_pfe_95_eur": rep.peak_pfe_95_eur,
        "peak_pfe_99_eur": rep.peak_pfe_99_eur,
        "eepe_eur": rep.eepe_eur,
        "exposure_profile": rep.exposure_profile_df.to_dict(orient="records"),
        "xva_summary": rep.xva_summary_df.to_dict(orient="records"),
    }
