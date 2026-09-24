"""
core/wealth/succession_optimizer.py
ARGUS — Family Office Generational Wealth Succession & Asset Protection Optimizer.
Normative Framework:
- Codice Civile: Artt. 536-564 (Legittima), Art. 768-bis (Patto di Famiglia), Art. 1923 (Polizze Vita)
- Fiscale: D.Lgs. 346/1990 (TUS), D.Lgs. 347/1990 (Ipotecaria/Catastale), Art. 87 TUIR (PEX 95%)
- Giurisprudenza: Circolare Agenzia delle Entrate 34/E/2022 (Trust ed effetti successori)

Simulates & compares 5 multi-generational succession architectures over 30 years:
1. Regime Ordinario (Direct Succession & standard progressive inheritance taxes)
2. Holding Familiare (Societa Semplice / S.r.l. with Patto di Famiglia & PEX 95%)
3. Trust Fiduciario (Asset segregation, delayed distribution taxation under AdE 34/E/2022)
4. Polizze Vita Ramo I / III (PPLI with 100% inheritance tax exemption ex Art. 12 TUS)
5. Ottimizzazione Ibrida (Patto di Famiglia + PPLI + Trust)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass
class FamilyProfileInput:
    """Family tree & succession configuration."""

    num_children: int = 2
    has_spouse: bool = True
    disabled_heirs_count: int = 0
    g1_current_age: int = 65
    g1_transfer_year: int = 15
    g2_transfer_year: int = 30
    annual_family_consumption_eur: float = 120_000.0


@dataclass
class ConsolidatedEstateInput:
    """Consolidated asset breakdown of the Family Office."""

    liquid_investments_eur: float = 5_000_000.0
    operating_business_equity_eur: float = 10_000_000.0
    real_estate_properties_eur: float = 4_000_000.0
    alternative_investments_eur: float = 1_000_000.0

    @property
    def total_estate_eur(self) -> float:
        return (
            self.liquid_investments_eur
            + self.operating_business_equity_eur
            + self.real_estate_properties_eur
            + self.alternative_investments_eur
        )


@dataclass
class VehicleStrategyResult:
    """Output metrics for a single succession architecture."""

    strategy_name: str
    final_wealth_eur_median: float
    final_wealth_eur_p10: float
    final_wealth_eur_p90: float
    total_taxes_paid_eur: float
    inheritance_tax_g1_eur: float
    inheritance_tax_g2_eur: float
    capital_gains_tax_eur: float
    maintenance_costs_total_eur: float
    tax_alpha_eur: float
    tax_alpha_pct: float
    capital_preservation_prob: float
    protection_score: int  # 0 to 100
    yearly_trajectory: List[float] = field(default_factory=list)


@dataclass
class MultiGenerationalSuccessionReport:
    """Comprehensive comparative succession report."""

    initial_estate_total_eur: float
    time_horizon_years: int
    family_profile: FamilyProfileInput
    strategies: Dict[str, VehicleStrategyResult]
    recommended_strategy: str
    summary_comparison_df: pd.DataFrame


class FamilyOfficeSuccessionOptimizer:
    """
    30-Year Multi-Generational Succession & Tax Architecture Optimizer.
    """

    def __init__(
        self,
        n_mc_sims: int = 2000,
        expected_gross_return: float = 0.055,
        expected_volatility: float = 0.100,
        inflation_rate: float = 0.020,
        random_seed: int = 42,
    ):
        self.n_mc_sims = n_mc_sims
        self.mu = expected_gross_return
        self.sigma = expected_volatility
        self.inflation = inflation_rate
        self.seed = random_seed

    def _compute_direct_inheritance_tax(
        self,
        estate_value: float,
        num_children: int,
        has_spouse: bool,
        disabled_count: int = 0,
        re_cadastral_fraction: float = 0.20,
    ) -> float:
        """
        Calculates Italian Statutory Inheritance Tax (Art. 2 D.Lgs. 346/1990):
        Spouse & Children: 4% on value exceeding €1,000,000 allowance each (€1.5M for disabled).
        Real estate mortgage & cadastral taxes: 3% (2% ipotecaria + 1% catastale).
        """
        num_heirs = num_children + (1 if has_spouse else 0)
        if num_heirs <= 0:
            num_heirs = 1

        share_per_heir = estate_value / num_heirs
        tot_tax = 0.0

        for i in range(num_heirs):
            is_dis = (i < disabled_count)
            allowance = 1_500_000.0 if is_dis else 1_000_000.0
            taxable_share = max(0.0, share_per_heir - allowance)
            tot_tax += taxable_share * 0.04

        # Real Estate Ipotecaria & Catastale (3% on estimated real estate fraction)
        re_tax = estate_value * re_cadastral_fraction * 0.03
        return tot_tax + re_tax

    def simulate(
        self,
        estate: ConsolidatedEstateInput,
        family: FamilyProfileInput,
    ) -> MultiGenerationalSuccessionReport:
        """
        Executes 30-year multi-generational stochastic Monte Carlo simulation across 5 vehicles.
        """
        t_years = 30
        w0 = estate.total_estate_eur
        rng = np.random.default_rng(self.seed)

        # Pre-generate annual lognormal market shocks (T x N_sims)
        dt = 1.0
        shocks = rng.normal(
            loc=(self.mu - 0.5 * self.sigma**2) * dt,
            scale=self.sigma * np.sqrt(dt),
            size=(t_years, self.n_mc_sims),
        )
        gross_multipliers = np.exp(shocks)

        # Vehicle Parameters: (setup_cost, annual_fee, tax_efficiency_multiplier, g1_exemption, g2_exemption)
        # tax_efficiency_multiplier: reduces recurring capital gains drag
        # g1_exemption: % exemption on G1 -> G2 inheritance tax
        # g2_exemption: % exemption on G2 -> G3 inheritance tax
        configs = {
            "Regime Ordinario": {
                "setup": 0.0,
                "annual_fee": 0.0,
                "tax_drag_pct": 0.012,  # 26% on ~4.5% realized gains + 0.20% bollo
                "g1_exemption": 0.00,
                "g2_exemption": 0.00,
                "prot_score": 25,
            },
            "Holding Familiare (PEX & Patto di Famiglia)": {
                "setup": 10_000.0,
                "annual_fee": 4_000.0,
                "tax_drag_pct": 0.004,  # PEX 95% ex art. 87 TUIR reduces CGT drastically
                "g1_exemption": 0.65,   # Business & holding shares 100% exempt under Art. 3 c. 4-ter
                "g2_exemption": 0.65,
                "prot_score": 75,
            },
            "Trust Fiduciario (AdE 34/E/2022)": {
                "setup": 25_000.0,
                "annual_fee": 7_500.0,
                "tax_drag_pct": 0.005,  # Trust gross compounding
                "g1_exemption": 0.80,   # Taxation deferred until final distribution
                "g2_exemption": 0.40,
                "prot_score": 90,
            },
            "Polizze Vita Ramo I/III (PPLI Art. 12)": {
                "setup": 2_000.0,
                "annual_fee": 0.0035 * w0,  # 35 bps institutional wrapper fee
                "tax_drag_pct": 0.002,      # Full deferral until surrender
                "g1_exemption": 0.85,       # Total exemption on liquid wealth portion
                "g2_exemption": 0.85,
                "prot_score": 85,
            },
            "Ottimizzazione Ibrida (Patto + PPLI + Trust)": {
                "setup": 30_000.0,
                "annual_fee": 9_000.0,
                "tax_drag_pct": 0.003,      # Best of all worlds
                "g1_exemption": 0.95,       # Operating equity in Patto, Liquid in PPLI, RE in Trust
                "g2_exemption": 0.90,
                "prot_score": 98,
            },
        }

        results_dict: Dict[str, VehicleStrategyResult] = {}
        baseline_final_median = 0.0

        for strat_name, cfg in configs.items():
            # Wealth paths matrix: (T+1, N_sims)
            paths = np.zeros((t_years + 1, self.n_mc_sims))
            paths[0, :] = w0 - cfg["setup"]

            tot_tax_paid = 0.0
            inh_tax_g1 = 0.0
            inh_tax_g2 = 0.0
            cgt_total = 0.0

            for yr in range(1, t_years + 1):
                # 1. Gross capital growth
                prev_w = paths[yr - 1, :]
                gross_w = prev_w * gross_multipliers[yr - 1, :]

                # 2. Family living consumption (inflated)
                cons = family.annual_family_consumption_eur * ((1.0 + self.inflation) ** yr)

                # 3. Recurring tax drag & vehicle maintenance fee
                ann_fee = cfg["annual_fee"] if not callable(cfg["annual_fee"]) else cfg["annual_fee"](prev_w.mean())
                cgt = gross_w * cfg["tax_drag_pct"]
                cgt_total += float(cgt.mean())

                net_w = np.maximum(0.0, gross_w - cons - ann_fee - cgt)

                # 4. Generational Transfer 1 (G1 -> G2 at g1_transfer_year)
                if yr == family.g1_transfer_year:
                    avg_w = float(net_w.mean())
                    std_tax = self._compute_direct_inheritance_tax(
                        avg_w, family.num_children, family.has_spouse, family.disabled_heirs_count
                    )
                    actual_tax = std_tax * (1.0 - cfg["g1_exemption"])
                    inh_tax_g1 = actual_tax
                    net_w = np.maximum(0.0, net_w - actual_tax)

                # 5. Generational Transfer 2 (G2 -> G3 at g2_transfer_year)
                if yr == family.g2_transfer_year:
                    avg_w = float(net_w.mean())
                    # G2 has no spouse assumed, 2 children
                    std_tax = self._compute_direct_inheritance_tax(
                        avg_w, family.num_children, False, family.disabled_heirs_count
                    )
                    actual_tax = std_tax * (1.0 - cfg["g2_exemption"])
                    inh_tax_g2 = actual_tax
                    net_w = np.maximum(0.0, net_w - actual_tax)

                paths[yr, :] = net_w

            final_values = paths[-1, :]
            final_med = float(np.median(final_values))
            final_p10 = float(np.percentile(final_values, 10.0))
            final_p90 = float(np.percentile(final_values, 90.0))
            prob_pres = float(np.mean(final_values >= w0))
            tot_tax = inh_tax_g1 + inh_tax_g2 + cgt_total

            if strat_name == "Regime Ordinario":
                baseline_final_median = final_med
                tax_alpha_eur = 0.0
                tax_alpha_pct = 0.0
            else:
                tax_alpha_eur = final_med - baseline_final_median
                tax_alpha_pct = (tax_alpha_eur / baseline_final_median * 100.0) if baseline_final_median > 0 else 0.0

            yearly_median = [float(np.median(paths[y, :])) for y in range(t_years + 1)]

            results_dict[strat_name] = VehicleStrategyResult(
                strategy_name=strat_name,
                final_wealth_eur_median=final_med,
                final_wealth_eur_p10=final_p10,
                final_wealth_eur_p90=final_p90,
                total_taxes_paid_eur=tot_tax,
                inheritance_tax_g1_eur=inh_tax_g1,
                inheritance_tax_g2_eur=inh_tax_g2,
                capital_gains_tax_eur=cgt_total,
                maintenance_costs_total_eur=cfg["setup"] + (cfg["annual_fee"] * t_years),
                tax_alpha_eur=tax_alpha_eur,
                tax_alpha_pct=tax_alpha_pct,
                capital_preservation_prob=prob_pres,
                protection_score=cfg["prot_score"],
                yearly_trajectory=yearly_median,
            )

        # Comparison DataFrame
        summary_rows = []
        for name, r in results_dict.items():
            summary_rows.append({
                "Architettura Successoria": name,
                "Patrimonio Finale Mediano (EUR)": round(r.final_wealth_eur_median, 2),
                "Imposte Totali 30Y (EUR)": round(r.total_taxes_paid_eur, 2),
                "Tax Alpha vs Ordinario (EUR)": round(r.tax_alpha_eur, 2),
                "Incremento Net Worth (%)": round(r.tax_alpha_pct, 2),
                "Prob. Preservazione Capitale": f"{round(r.capital_preservation_prob * 100, 1)}%",
                "Asset Protection Score": f"{r.protection_score}/100",
            })
        summary_df = pd.DataFrame(summary_rows)

        best_strat = max(results_dict.keys(), key=lambda k: results_dict[k].final_wealth_eur_median)

        return MultiGenerationalSuccessionReport(
            initial_estate_total_eur=w0,
            time_horizon_years=t_years,
            family_profile=family,
            strategies=results_dict,
            recommended_strategy=best_strat,
            summary_comparison_df=summary_df,
        )


def compute_family_succession_optimization(
    liquid_investments_eur: float = 5_000_000.0,
    operating_business_equity_eur: float = 10_000_000.0,
    real_estate_properties_eur: float = 4_000_000.0,
    alternative_investments_eur: float = 1_000_000.0,
    num_children: int = 2,
    has_spouse: bool = True,
    annual_consumption_eur: float = 120_000.0,
) -> Dict[str, Any]:
    """
    Convenience functional API for Succession & Asset Protection optimization.
    """
    estate = ConsolidatedEstateInput(
        liquid_investments_eur=liquid_investments_eur,
        operating_business_equity_eur=operating_business_equity_eur,
        real_estate_properties_eur=real_estate_properties_eur,
        alternative_investments_eur=alternative_investments_eur,
    )
    family = FamilyProfileInput(
        num_children=num_children,
        has_spouse=has_spouse,
        annual_family_consumption_eur=annual_consumption_eur,
    )

    optimizer = FamilyOfficeSuccessionOptimizer()
    report = optimizer.simulate(estate, family)

    strats_payload = {}
    for k, v in report.strategies.items():
        strats_payload[k] = {
            "final_wealth_eur_median": v.final_wealth_eur_median,
            "final_wealth_eur_p10": v.final_wealth_eur_p10,
            "final_wealth_eur_p90": v.final_wealth_eur_p90,
            "total_taxes_paid_eur": v.total_taxes_paid_eur,
            "tax_alpha_eur": v.tax_alpha_eur,
            "tax_alpha_pct": v.tax_alpha_pct,
            "capital_preservation_prob": v.capital_preservation_prob,
            "protection_score": v.protection_score,
            "trajectory_median_sample": v.yearly_trajectory[::5],
        }

    return {
        "initial_estate_total_eur": report.initial_estate_total_eur,
        "recommended_strategy": report.recommended_strategy,
        "strategies": strats_payload,
        "summary_table": report.summary_comparison_df.to_dict(orient="records"),
    }
