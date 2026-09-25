"""CreditMetrics & Vasicek Multi-Obligor Portfolio Credit Risk Engine.

Implements:
1. Vasicek (2002) Asymptotic Single Risk Factor (ASRF) Model & Basel II/III IRB Capital Formula:
   - Regulatory asset correlation rho(PD)
   - Maturity adjustment b(PD)
   - Analytical Expected Loss (EL), Unexpected Loss (UL), and 99.9% Credit Capital (K_IRB).
2. J.P. Morgan CreditMetrics (1997) Multi-State Rating Migration Monte Carlo:
   - 8x8 S&P/Moody's annual credit rating transition matrix (AAA to D)
   - Correlated latent asset return simulation R_i = sqrt(rho_i)*Z_sys + sqrt(1-rho_i)*eps_i
   - Mark-to-Market revaluation across credit spread curves upon downgrade/upgrade
   - Portfolio Credit VaR (99.0%, 99.9%), Expected Shortfall (CVaR 99.9%), and Incremental Risk Charge (IRC).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import norm

# Standard S&P 1-Year Rating Transition Matrix (in %)
# Rows/Cols: AAA, AA, A, BBB, BB, B, CCC, D
RATINGS_SCALE = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"]

TRANSITION_MATRIX_PCT = np.array([
    [90.81,  8.33,  0.68,  0.06,  0.08,  0.02,  0.01,  0.01],  # AAA
    [ 0.70, 90.65,  7.79,  0.64,  0.06,  0.13,  0.02,  0.01],  # AA
    [ 0.09,  2.27, 91.05,  5.52,  0.74,  0.26,  0.01,  0.06],  # A
    [ 0.02,  0.33,  5.95, 86.93,  5.30,  1.17,  0.12,  0.18],  # BBB
    [ 0.03,  0.14,  0.67,  7.73, 80.53,  8.84,  1.00,  1.06],  # BB
    [ 0.01,  0.11,  0.24,  0.43,  6.48, 83.46,  4.07,  5.20],  # B
    [ 0.00,  0.00,  0.22,  1.30,  2.38, 11.24, 64.86, 20.00],  # CCC
    [ 0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00, 100.0],  # D
], dtype=float) / 100.0

# Credit Spreads by Rating (in bps) for MTM migration valuation
CREDIT_SPREADS_BPS = {
    "AAA": 35.0,
    "AA": 60.0,
    "A": 95.0,
    "BBB": 165.0,
    "BB": 310.0,
    "B": 520.0,
    "CCC": 950.0,
    "D": 4000.0,
}


@dataclass
class ObligorPosition:
    """Single corporate obligor credit exposure."""

    obligor_id: str
    name: str
    sector: str
    rating: str  # "AAA", "AA", "A", "BBB", "BB", "B", "CCC"
    ead_eur: float  # Exposure at Default
    lgd: float = 0.45  # Loss Given Default (Basel standard 45% senior unsecured)
    maturity_years: float = 3.0
    pd_override: Optional[float] = None

    @property
    def pd(self) -> float:
        """Annual Probability of Default derived from rating or override."""
        if self.pd_override is not None:
            return max(0.0001, float(self.pd_override))
        idx = RATINGS_SCALE.index(self.rating) if self.rating in RATINGS_SCALE else 3
        return max(0.0001, float(TRANSITION_MATRIX_PCT[idx, -1]))

    @property
    def basel_asset_correlation(self) -> float:
        """Basel II/III IRB supervisory corporate asset correlation rho(PD):

        rho = 0.12 * (1 - exp(-50 * PD)) / (1 - exp(-50)) + 0.24 * [1 - (1 - exp(-50 * PD)) / (1 - exp(-50))]
        """
        w = (1.0 - np.exp(-50.0 * self.pd)) / (1.0 - np.exp(-50.0))
        return float(0.12 * w + 0.24 * (1.0 - w))


@dataclass
class CreditPortfolioReport:
    """Comprehensive CreditMetrics and Vasicek IRB portfolio risk report."""

    total_ead_eur: float
    expected_loss_eur: float
    unexpected_loss_eur: float
    vasicek_irb_capital_999_eur: float
    vasicek_rwa_eur: float
    creditmetrics_var_99_eur: float
    creditmetrics_var_999_eur: float
    creditmetrics_es_999_eur: float
    incremental_risk_charge_eur: float
    diversification_benefit_pct: float
    obligor_contributions: List[Dict[str, Any]]
    migration_matrix_pct: Dict[str, List[float]]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "total_ead_eur": round(self.total_ead_eur, 2),
            "expected_loss_eur": round(self.expected_loss_eur, 2),
            "unexpected_loss_eur": round(self.unexpected_loss_eur, 2),
            "vasicek_irb_capital_999_eur": round(self.vasicek_irb_capital_999_eur, 2),
            "vasicek_rwa_eur": round(self.vasicek_rwa_eur, 2),
            "creditmetrics_var_99_eur": round(self.creditmetrics_var_99_eur, 2),
            "creditmetrics_var_999_eur": round(self.creditmetrics_var_999_eur, 2),
            "creditmetrics_es_999_eur": round(self.creditmetrics_es_999_eur, 2),
            "incremental_risk_charge_eur": round(self.incremental_risk_charge_eur, 2),
            "diversification_benefit_pct": round(self.diversification_benefit_pct, 2),
            "obligor_contributions": self.obligor_contributions,
            "migration_matrix_pct": self.migration_matrix_pct,
        }


class CreditPortfolioEngine:
    """Institutional Multi-Obligor CreditMetrics and Vasicek ASRF Engine."""

    def __init__(self, obligors: List[ObligorPosition], n_simulations: int = 10000, seed: int = 42) -> None:
        """Initialize credit portfolio engine."""
        self.obligors = obligors
        self.n_sims = n_simulations
        self.seed = seed

    def compute_vasicek_irb_obligor(self, ob: ObligorPosition) -> Tuple[float, float, float]:
        """Compute Basel IRB Expected Loss, Capital Requirement K_IRB, and RWA for an obligor."""
        pd = ob.pd
        lgd = ob.lgd
        rho = ob.basel_asset_correlation
        m = max(1.0, min(5.0, ob.maturity_years))

        el = ob.ead_eur * pd * lgd

        # Conditional default probability at 99.9% systematic factor quantile
        z_pd = norm.ppf(pd)
        z_999 = norm.ppf(0.999)
        cond_pd = float(norm.cdf((z_pd + np.sqrt(rho) * z_999) / np.sqrt(1.0 - rho)))

        # Maturity adjustment factor b(PD)
        b_pd = (0.11852 - 0.05478 * np.log(pd)) ** 2
        mat_adj = (1.0 + (m - 2.5) * b_pd) / (1.0 - 1.5 * b_pd)

        k_irb_pct = max(0.0, (lgd * cond_pd - pd * lgd) * mat_adj)
        capital_eur = ob.ead_eur * k_irb_pct
        rwa_eur = capital_eur * 12.5

        return el, capital_eur, rwa_eur

    def simulate_creditmetrics(self) -> Dict[str, Any]:
        """Run CreditMetrics multi-state rating migration and default simulation."""
        rng = np.random.default_rng(self.seed)
        n_ob = len(self.obligors)

        # Precompute normal thresholds for each initial rating (7 states + default)
        # Cumulative probability from worst state (Default) to best state (AAA)
        thresholds = np.zeros((7, 7), dtype=float)
        for r_idx in range(7):
            probs_rev = TRANSITION_MATRIX_PCT[r_idx, ::-1]  # D, CCC, B, BB, BBB, A, AA, AAA
            cum_probs = np.cumsum(probs_rev)[:-1]
            cum_probs = np.clip(cum_probs, 1e-6, 1.0 - 1e-6)
            thresholds[r_idx, :] = norm.ppf(cum_probs)

        # Precompute MTM loss matrix (7 initial ratings x 8 terminal states) per unit EAD
        # Loss = duration * (Spread_new - Spread_old) for non-default, and LGD for Default
        loss_per_unit = np.zeros((n_ob, 8), dtype=float)
        for i, ob in enumerate(self.obligors):
            r_idx = RATINGS_SCALE.index(ob.rating) if ob.rating in RATINGS_SCALE else 3
            s_old = CREDIT_SPREADS_BPS[RATINGS_SCALE[r_idx]] / 10000.0
            dur = max(0.5, ob.maturity_years * 0.88)
            for state_k in range(8):
                if state_k == 7:  # Default state
                    loss_per_unit[i, state_k] = ob.lgd
                else:
                    s_new = CREDIT_SPREADS_BPS[RATINGS_SCALE[state_k]] / 10000.0
                    # MTM loss if spread widens (positive = loss, negative = MTM gain on upgrade)
                    loss_per_unit[i, state_k] = dur * (s_new - s_old)

        # Simulate systematic factor Z_sys and idiosyncratic shocks
        z_sys = rng.standard_normal(self.n_sims)
        eps = rng.standard_normal((self.n_sims, n_ob))

        portfolio_losses = np.zeros(self.n_sims, dtype=float)
        obligor_sim_losses = np.zeros((self.n_sims, n_ob), dtype=float)

        for i, ob in enumerate(self.obligors):
            r_idx = RATINGS_SCALE.index(ob.rating) if ob.rating in RATINGS_SCALE else 3
            rho = ob.basel_asset_correlation
            r_latent = np.sqrt(rho) * z_sys + np.sqrt(1.0 - rho) * eps[:, i]

            # Map latent asset return to terminal state (0=AAA .. 7=D)
            # Thresholds are ordered from D (lowest Z) to AA (highest Z)
            thresh_vec = thresholds[r_idx, :]
            # searchsorted gives 0 if r_latent < thresh_D (so Default -> state 7)
            bucket = np.searchsorted(thresh_vec, r_latent)
            terminal_state = 7 - bucket

            ob_losses = ob.ead_eur * loss_per_unit[i, terminal_state]
            obligor_sim_losses[:, i] = ob_losses
            portfolio_losses += ob_losses

        var_99 = float(np.percentile(portfolio_losses, 99.0))
        var_999 = float(np.percentile(portfolio_losses, 99.9))
        tail_mask = portfolio_losses >= var_99
        es_999 = float(np.mean(portfolio_losses[portfolio_losses >= var_999])) if np.any(portfolio_losses >= var_999) else var_999

        # Tail marginal contributions in top 1% scenarios
        marginal_contribs = []
        for i in range(n_ob):
            mc = float(np.mean(obligor_sim_losses[tail_mask, i])) if np.any(tail_mask) else 0.0
            marginal_contribs.append(mc)

        return {
            "var_99": max(0.0, var_99),
            "var_999": max(0.0, var_999),
            "es_999": max(0.0, es_999),
            "std_loss": float(np.std(portfolio_losses)),
            "marginal_contribs": marginal_contribs,
        }

    def generate_report(self) -> CreditPortfolioReport:
        """Compute full Vasicek IRB and CreditMetrics portfolio report."""
        total_ead = sum(ob.ead_eur for ob in self.obligors)
        total_el = 0.0
        total_irb_cap = 0.0
        total_rwa = 0.0

        cm_res = self.simulate_creditmetrics()
        obligor_rows: List[Dict[str, Any]] = []

        for i, ob in enumerate(self.obligors):
            el, cap, rwa = self.compute_vasicek_irb_obligor(ob)
            total_el += el
            total_irb_cap += cap
            total_rwa += rwa

            obligor_rows.append(
                {
                    "obligor_id": ob.obligor_id,
                    "name": ob.name,
                    "sector": ob.sector,
                    "rating": ob.rating,
                    "ead_eur": round(ob.ead_eur, 2),
                    "pd_pct": round(ob.pd * 100.0, 3),
                    "lgd_pct": round(ob.lgd * 100.0, 1),
                    "asset_correlation_pct": round(ob.basel_asset_correlation * 100.0, 2),
                    "expected_loss_eur": round(el, 2),
                    "vasicek_irb_capital_eur": round(cap, 2),
                    "rwa_eur": round(rwa, 2),
                    "tail_risk_contribution_eur": round(max(0.0, cm_res["marginal_contribs"][i]), 2),
                }
            )

        # Standalone sum of individual 99.9% capitals vs diversified CreditMetrics 99.9% VaR
        standalone_cap_sum = max(1.0, total_irb_cap + total_el)
        diversified_var = cm_res["var_999"]
        div_benefit_pct = max(0.0, (1.0 - diversified_var / max(standalone_cap_sum, diversified_var)) * 100.0)

        mig_dict = {
            RATINGS_SCALE[r]: [round(float(val) * 100.0, 2) for val in TRANSITION_MATRIX_PCT[r]]
            for r in range(7)
        }

        return CreditPortfolioReport(
            total_ead_eur=total_ead,
            expected_loss_eur=total_el,
            unexpected_loss_eur=cm_res["std_loss"],
            vasicek_irb_capital_999_eur=total_irb_cap,
            vasicek_rwa_eur=total_rwa,
            creditmetrics_var_99_eur=cm_res["var_99"],
            creditmetrics_var_999_eur=cm_res["var_999"],
            creditmetrics_es_999_eur=cm_res["es_999"],
            incremental_risk_charge_eur=max(0.0, cm_res["var_999"] - total_el),
            diversification_benefit_pct=div_benefit_pct,
            obligor_contributions=obligor_rows,
            migration_matrix_pct=mig_dict,
        )


def compute_credit_portfolio_risk(
    obligors_data: Optional[List[Dict[str, Any]]] = None,
    n_simulations: int = 8000,
) -> Dict[str, Any]:
    """Top-level calculation function for CreditMetrics & Vasicek Portfolio Credit Risk."""
    if obligors_data:
        obligors = [
            ObligorPosition(
                obligor_id=str(item.get("obligor_id", f"OB_{i+1}")),
                name=str(item.get("name", f"Corporate_{i+1}")),
                sector=str(item.get("sector", "Industrials")),
                rating=str(item.get("rating", "BBB")),
                ead_eur=float(item.get("ead_eur", 5_000_000.0)),
                lgd=float(item.get("lgd", 0.45)),
                maturity_years=float(item.get("maturity_years", 3.0)),
                pd_override=item.get("pd_override"),
            )
            for i, item in enumerate(obligors_data)
        ]
    else:
        obligors = [
            ObligorPosition("OB_01", "ASML Holding NV", "Technology", "AA", 12_000_000.0, 0.40, 4.0),
            ObligorPosition("OB_02", "Enel SpA", "Utilities", "BBB", 15_000_000.0, 0.45, 5.0),
            ObligorPosition("OB_03", "Volkswagen AG", "Automotive", "A", 10_000_000.0, 0.45, 3.0),
            ObligorPosition("OB_04", "Telecom Italia SpA", "Telecom", "BB", 8_000_000.0, 0.50, 3.5),
            ObligorPosition("OB_05", "Air France-KLM", "Airlines", "B", 5_000_000.0, 0.55, 2.5),
            ObligorPosition("OB_06", "LVMH Moet Hennessy", "Luxury", "AA", 14_000_000.0, 0.40, 4.5),
        ]

    engine = CreditPortfolioEngine(obligors=obligors, n_simulations=n_simulations)
    report = engine.generate_report()
    res_dict = report.to_dict()
    res_dict["engine_version"] = "9.15.0"
    return res_dict
