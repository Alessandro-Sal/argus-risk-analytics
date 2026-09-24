"""
core/climate_stress_engine.py
ARGUS — Climate Transition & Physical Risk Stress Engine (NGFS Phase IV Framework).
Regulatory References:
- Network for Greening the Financial System (NGFS) Climate Scenarios for Central Banks & Supervisors.
- EBA Guidelines on Management and Supervision of ESG Risks (EBA/GL/2021/04).
- TCFD (Task Force on Climate-related Financial Disclosures) & SFDR Regulatory Technical Standards.

Features:
- Standard NGFS Phase IV Scenarios: Orderly Net Zero 2050, Disorderly Delayed Transition, Hot House World
- Portfolio Carbon Accounting: Scope 1, 2, 3 emissions & Weighted Average Carbon Intensity (WACI)
- Carbon Tax Shock Transmission: Corporate EBITDA margin squeeze, equity re-rating, credit spread widening
- Physical Climate Damage Risk: Acute flood/wildfire shocks & chronic heat stress on real estate/assets
- Aggregate Climate Value-at-Risk (Climate VaR in EUR and %)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# NGFS Phase IV Scenario Parameters
NGFS_SCENARIO_CONFIGS = {
    "orderly": {
        "name": "Orderly Net Zero 2050",
        "carbon_price_eur_ton": 150.0,
        "transition_shock_multiplier": 0.80,
        "physical_damage_rate": 0.02,
        "target_warming_deg_c": 1.5,
        "gdp_impact_pct": -1.5,
        "description": "Politiche climatiche tempestive e coordinate. Aumento graduale del prezzo della CO2 e minimizzazione dei danni fisici catastrofici.",
    },
    "disorderly": {
        "name": "Disorderly Delayed Transition",
        "carbon_price_eur_ton": 280.0,
        "transition_shock_multiplier": 1.75,
        "physical_damage_rate": 0.05,
        "target_warming_deg_c": 1.8,
        "gdp_impact_pct": -4.5,
        "description": "Azione climatica tardiva (post-2030). Shock improvviso sul prezzo della CO2, rapido stralcio di asset fossili e shock sui mercati.",
    },
    "hot_house": {
        "name": "Hot House World (Current Policies)",
        "carbon_price_eur_ton": 35.0,
        "transition_shock_multiplier": 0.20,
        "physical_damage_rate": 0.18,
        "target_warming_deg_c": 3.2,
        "gdp_impact_pct": -14.0,
        "description": "Nessuna nuova politica climatica. Basso costo del carbonio ma danni fisici estremi irreversibili su real estate, filiere e infrastrutture.",
    },
}


@dataclass
class ClimateAssetProfile:
    """Asset ESG and climate exposure characteristics."""

    asset_id: str
    name: str
    asset_type: str         # 'equity', 'bond', 'real_estate', 'cash'
    market_value_eur: float
    sector: str = "Broad"
    scope1_tco2e: float = 0.0
    scope2_tco2e: float = 0.0
    scope3_tco2e: float = 0.0
    annual_revenue_meur: float = 100.0
    annual_ebitda_meur: float = 25.0
    physical_hazard_score: float = 30.0   # 0 to 100 flood/fire/heat hazard vulnerability
    carbon_cost_pass_through_pct: float = 0.50  # Capability to pass carbon tax to customers


@dataclass
class ClimateStressReport:
    """Comprehensive output of NGFS climate stress testing."""

    portfolio_value_eur: float
    scenario_selected: str
    scenario_name: str
    carbon_price_used_eur_ton: float
    total_scope1_tco2e: float
    total_scope2_tco2e: float
    total_scope3_tco2e: float
    waci_tco2e_per_meur: float
    transition_loss_eur: float
    physical_damage_loss_eur: float
    total_climate_loss_eur: float
    climate_var_pct: float
    esg_climate_rating: str  # 'AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC'
    asset_breakdown_df: pd.DataFrame
    scenarios_comparison_df: pd.DataFrame

    @property
    def portfolio_loss_pct(self) -> float:
        return -abs(self.climate_var_pct)

    @property
    def portfolio_waci_tco2e_per_meur(self) -> float:
        return self.waci_tco2e_per_meur

    @property
    def transition_risk_loss_eur(self) -> float:
        return self.transition_loss_eur

    @property
    def physical_risk_loss_eur(self) -> float:
        return self.physical_damage_loss_eur

    @property
    def temperature_anomaly_celsius(self) -> float:
        sc = (self.scenario_selected + " " + self.scenario_name).lower()
        if "hot" in sc or "current" in sc:
            return 3.2
        elif "delayed" in sc or "disorderly" in sc:
            return 1.8
        return 1.5

    @property
    def carbon_price_usd_ton(self) -> float:
        return round(self.carbon_price_used_eur_ton * 1.08, 1)


class ClimateStressEngine:
    """
    NGFS Scenario Transmission and Portfolio Climate Risk Calculator.
    """

    def __init__(self, default_scenario: str = "disorderly"):
        self.default_scenario = default_scenario

    def evaluate_portfolio_stress(
        self,
        scenario_name: str = "Net Zero 2050 (Orderly)",
        target_year: int = 2030,
        assets: Optional[List[ClimateAssetProfile]] = None,
    ) -> ClimateStressReport:
        """Evaluates stress on portfolio under named NGFS scenario and target horizon."""
        if assets is None:
            # Canonical institutional multi-asset portfolio with ESG attributes
            assets = [
                ClimateAssetProfile("EQ_ENEL", "Enel SpA (Renewables/Utilities)", "equity", 25_000_000.0, sector="Utilities", scope1_tco2e=3200.0, scope2_tco2e=400.0, annual_revenue_meur=90.0, physical_hazard_score=25.0),
                ClimateAssetProfile("EQ_SHELL", "Shell PLC (Integrated Energy)", "equity", 15_000_000.0, sector="Energy", scope1_tco2e=8500.0, scope2_tco2e=1200.0, annual_revenue_meur=150.0, physical_hazard_score=45.0),
                ClimateAssetProfile("BOND_BTP_GREEN", "BTP Green Sovereign 2035", "bond", 30_000_000.0, sector="Sovereign", scope1_tco2e=100.0, scope2_tco2e=50.0, annual_revenue_meur=500.0, physical_hazard_score=20.0),
                ClimateAssetProfile("RE_LOGISTICS", "Milan Core Logistics Center", "real_estate", 20_000_000.0, sector="Real Estate", scope1_tco2e=450.0, scope2_tco2e=350.0, annual_revenue_meur=18.0, physical_hazard_score=65.0),
                ClimateAssetProfile("EQ_TECH_ASML", "ASML Holding (Semiconductors)", "equity", 10_000_000.0, sector="Tech", scope1_tco2e=200.0, scope2_tco2e=150.0, annual_revenue_meur=80.0, physical_hazard_score=15.0),
            ]

        sc_lower = scenario_name.lower()
        if "hot" in sc_lower or "current" in sc_lower:
            key = "hot_house"
        elif "delayed" in sc_lower or "disorderly" in sc_lower:
            key = "disorderly"
        else:
            key = "orderly"

        rep = self.evaluate_scenario(assets, scenario_key=key)
        # Year scaling factor: if target_year > 2030, physical damage expands
        if target_year >= 2040 and key == "hot_house":
            rep.physical_damage_loss_eur *= 1.45
            rep.total_climate_loss_eur = rep.transition_loss_eur + rep.physical_damage_loss_eur
            rep.climate_var_pct = (rep.total_climate_loss_eur / rep.portfolio_value_eur) * 100.0
        return rep

    def compute_waci(self, assets: List[ClimateAssetProfile]) -> Tuple[float, float, float, float]:
        """
        Calculates Scope 1, 2, 3 totals and Weighted Average Carbon Intensity (WACI):
            WACI = sum(w_i * (Scope1_i + Scope2_i) / Revenue_MEUR_i)
        """
        tot_val = sum(a.market_value_eur for a in assets)
        if tot_val <= 0:
            return 0.0, 0.0, 0.0, 0.0

        tot_s1 = sum(a.scope1_tco2e for a in assets)
        tot_s2 = sum(a.scope2_tco2e for a in assets)
        tot_s3 = sum(a.scope3_tco2e for a in assets)

        waci = 0.0
        for a in assets:
            w_i = a.market_value_eur / tot_val
            rev = max(1.0, a.annual_revenue_meur)
            intensity_i = (a.scope1_tco2e + a.scope2_tco2e) / rev
            waci += w_i * intensity_i

        return float(waci), float(tot_s1), float(tot_s2), float(tot_s3)

    def evaluate_scenario(
        self,
        assets: List[ClimateAssetProfile],
        scenario_key: str = "disorderly",
    ) -> ClimateStressReport:
        """
        Simulates climate stress losses under chosen NGFS scenario.
        """
        cfg = NGFS_SCENARIO_CONFIGS.get(scenario_key.lower(), NGFS_SCENARIO_CONFIGS["disorderly"])
        tot_val = sum(a.market_value_eur for a in assets)
        if tot_val <= 0:
            tot_val = 1.0

        waci, tot_s1, tot_s2, tot_s3 = self.compute_waci(assets)
        carbon_px = cfg["carbon_price_eur_ton"]

        records = []
        trans_tot = 0.0
        phys_tot = 0.0

        for a in assets:
            val = a.market_value_eur
            unabsorbed_carbon = (a.scope1_tco2e + 0.5 * a.scope2_tco2e) * (1.0 - a.carbon_cost_pass_through_pct)
            carbon_cost_eur = unabsorbed_carbon * carbon_px

            # 1. Transition Risk (equity drop / credit widening)
            if a.asset_type == "equity":
                ebitda_eur = max(100_000.0, a.annual_ebitda_meur * 1_000_000.0)
                margin_drop = min(0.60, (carbon_cost_eur / ebitda_eur) * cfg["transition_shock_multiplier"])
                trans_loss = val * margin_drop
            elif a.asset_type == "bond":
                # Credit spread widening proportional to emissions/EBITDA
                ebitda_meur = max(1.0, a.annual_ebitda_meur)
                intensity = a.scope1_tco2e / (ebitda_meur * 1000.0)
                spread_bps = min(350.0, intensity * carbon_px * 0.015 * cfg["transition_shock_multiplier"])
                # Approx duration 5.0
                trans_loss = val * (spread_bps / 10000.0) * 5.0
            else:
                trans_loss = 0.0

            # 2. Physical Risk (acute hazard on real estate/assets)
            if a.asset_type in ["real_estate", "property"]:
                phys_loss = val * (a.physical_hazard_score / 100.0) * cfg["physical_damage_rate"] * 2.0
            else:
                phys_loss = val * (a.physical_hazard_score / 100.0) * cfg["physical_damage_rate"] * 0.5

            trans_tot += trans_loss
            phys_tot += phys_loss
            tot_loss_i = trans_loss + phys_loss

            records.append({
                "Asset": a.name,
                "Tipo": a.asset_type,
                "Valore (€)": val,
                "WACI Asset": round((a.scope1_tco2e + a.scope2_tco2e) / max(1.0, a.annual_revenue_meur), 1),
                "Perdita Transizione (€)": round(trans_loss, 2),
                "Perdita Fisica (€)": round(phys_loss, 2),
                "Perdita Totale (€)": round(tot_loss_i, 2),
                "Impatto %": round((tot_loss_i / max(1.0, val)) * 100.0, 2),
            })

        df_assets = pd.DataFrame(records)
        total_loss = trans_tot + phys_tot
        climate_var = (total_loss / tot_val * 100.0)

        # ESG Climate Rating
        if waci < 50 and climate_var < 5.0:
            rating = "AAA (Climate Leader)"
        elif waci < 120 and climate_var < 8.0:
            rating = "AA (Resilient)"
        elif waci < 200 and climate_var < 12.0:
            rating = "A (Balanced)"
        elif climate_var < 18.0:
            rating = "BBB (Moderate Risk)"
        else:
            rating = "CCC (High Carbon Vulnerability)"

        # Scenario comparison table
        scen_rows = []
        for s_key, s_cfg in NGFS_SCENARIO_CONFIGS.items():
            mult = s_cfg["transition_shock_multiplier"]
            phys_rate = s_cfg["physical_damage_rate"]
            scen_trans = trans_tot * (mult / max(0.01, cfg["transition_shock_multiplier"]))
            scen_phys = phys_tot * (phys_rate / max(0.01, cfg["physical_damage_rate"]))
            scen_tot = scen_trans + scen_phys
            scen_rows.append({
                "Scenario NGFS": s_cfg["name"],
                "Prezzo CO2 (€/t)": s_cfg["carbon_price_eur_ton"],
                "Riscaldamento": f"+{s_cfg['target_warming_deg_c']}°C",
                "Perdita Transizione (€)": round(scen_trans, 2),
                "Danno Fisico (€)": round(scen_phys, 2),
                "Climate VaR Totale (€)": round(scen_tot, 2),
                "Impatto Portafoglio (%)": round((scen_tot / tot_val) * 100.0, 2),
            })
        df_scenarios = pd.DataFrame(scen_rows)

        return ClimateStressReport(
            portfolio_value_eur=tot_val,
            scenario_selected=scenario_key,
            scenario_name=cfg["name"],
            carbon_price_used_eur_ton=carbon_px,
            total_scope1_tco2e=tot_s1,
            total_scope2_tco2e=tot_s2,
            total_scope3_tco2e=tot_s3,
            waci_tco2e_per_meur=waci,
            transition_loss_eur=trans_tot,
            physical_damage_loss_eur=phys_tot,
            total_climate_loss_eur=total_loss,
            climate_var_pct=climate_var,
            esg_climate_rating=rating,
            asset_breakdown_df=df_assets,
            scenarios_comparison_df=df_scenarios,
        )


# Institutional Aliases
NgfsClimateStressEngine = ClimateStressEngine


def compute_ngfs_climate_stress(
    portfolio_holdings: Optional[List[Dict[str, Any]]] = None,
    portfolio_assets: Optional[List[Dict[str, Any]]] = None,
    scenario_name: str = "Net Zero 2050 (Orderly)",
    scenario: Optional[str] = None,
    target_year: int = 2030,
) -> Dict[str, Any]:
    """
    Convenience functional API for NGFS Climate Stress Testing.
    """
    holdings = portfolio_holdings or portfolio_assets
    sc_name = scenario or scenario_name

    engine = ClimateStressEngine()
    if holdings:
        asset_profiles = [
            ClimateAssetProfile(
                asset_id=str(a.get("id", a.get("name", f"asset_{i}"))),
                name=str(a.get("name", f"Asset {i}")),
                asset_type=str(a.get("asset_type", "equity")),
                market_value_eur=float(a.get("market_value_eur", a.get("value", 100_000.0))),
                sector=str(a.get("sector", "General")),
                scope1_tco2e=float(a.get("scope1", a.get("scope1_tco2e", 500.0))),
                scope2_tco2e=float(a.get("scope2", a.get("scope2_tco2e", 200.0))),
                scope3_tco2e=float(a.get("scope3", a.get("scope3_tco2e", 1000.0))),
                annual_revenue_meur=float(a.get("revenue_meur", 50.0)),
                annual_ebitda_meur=float(a.get("ebitda_meur", 12.0)),
                physical_hazard_score=float(a.get("physical_hazard_score", 30.0)),
                carbon_cost_pass_through_pct=float(a.get("pass_through", 0.50)),
            )
            for i, a in enumerate(holdings)
        ]
        report = engine.evaluate_portfolio_stress(scenario_name=sc_name, target_year=target_year, assets=asset_profiles)
    else:
        report = engine.evaluate_portfolio_stress(scenario_name=sc_name, target_year=target_year)

    return {
        "portfolio_value_eur": report.portfolio_value_eur,
        "scenario_selected": report.scenario_selected,
        "scenario_name": report.scenario_name,
        "portfolio_loss_pct": report.portfolio_loss_pct,
        "portfolio_loss_eur": -abs(report.total_climate_loss_eur),
        "transition_risk_loss_eur": report.transition_loss_eur,
        "physical_risk_loss_eur": report.physical_damage_loss_eur,
        "portfolio_waci_tco2e_per_meur": report.waci_tco2e_per_meur,
        "carbon_price_usd_ton": report.carbon_price_usd_ton,
        "temperature_anomaly_celsius": report.temperature_anomaly_celsius,
        "climate_var_pct": report.climate_var_pct,
        "esg_climate_rating": report.esg_climate_rating,
        "scenarios_comparison": report.scenarios_comparison_df.to_dict(orient="records"),
        "asset_breakdown": report.asset_breakdown_df.to_dict(orient="records"),
        "holdings_breakdown": report.asset_breakdown_df.to_dict(orient="records"),
    }
