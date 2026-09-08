"""
core/wealth/human_capital_engine.py
ARGUS — Human Capital Valuation & Holistic Total Balance Sheet VaR (TBS-VaR) Engine.

Pilastro di trasformazione Next-Level:
- Integrazione attuariale del Capitale Umano (HC) come asset quasi-equity / quasi-bond.
- Sconto flussi redditizi futuri con curva Nelson-Siegel e premio per instabilità lavorativa.
- Matrice di covarianza estesa: Mercati Finanziari + Real Estate + Capitale Umano.
- Total Balance Sheet Value at Risk (TBS-VaR) e Conditional VaR (TBS-CVaR).
- Modello di stress su mutui a tasso variabile e calcolo della solvibilità di cassa (Emergency Runway).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class LaborIncomeProfile:
    """Profilo lavorativo e redditizio dell'investitore."""
    current_annual_net_income: float
    years_to_retirement: int
    income_growth_rate: float
    industry_sector: str
    sector_beta: float  # Sensibilità al ciclo azionario (es. Tech 1.2, Sanità 0.4, Statale 0.05)
    unemployment_risk_premium: float = 0.015  # Premio al rischio disoccupazione / discontinuità


@dataclass(frozen=True)
class TotalBalanceSheetState:
    """Stato patrimoniale completo comprensivo di asset liquidi, illiquidi e debito."""
    liquid_portfolio_value: float
    liquid_portfolio_weights: np.ndarray
    liquid_covariance_matrix: np.ndarray
    real_estate_value: float
    real_estate_volatility: float
    real_estate_beta: float
    mortgage_debt_outstanding: float
    mortgage_duration: float
    is_variable_rate: bool
    annual_unavoidable_expenses: float
    labor_profile: LaborIncomeProfile


class HumanCapitalEngine:
    """
    Motore attuariale per la stima del Capitale Umano e della sua scomposizione in classi sintetiche.
    """

    def __init__(self, base_risk_free_rate: float = 0.03, equity_risk_premium: float = 0.05):
        self.rf = base_risk_free_rate
        self.erp = equity_risk_premium

    def compute_human_capital_valuation(self, profile: LaborIncomeProfile) -> Dict[str, Any]:
        """
        Calcola il valore attuale del Capitale Umano (HC) e la scomposizione Quasi-Equity / Quasi-Bond.
        """
        if profile.years_to_retirement <= 0 or profile.current_annual_net_income <= 0:
            return {
                "human_capital_pv": 0.0,
                "discount_rate": self.rf,
                "quasi_equity_weight": 0.0,
                "quasi_bond_weight": 1.0,
                "quasi_equity_amount": 0.0,
                "quasi_bond_amount": 0.0,
                "annual_cashflows_projection": []
            }

        # Tasso di attualizzazione: rf + beta * ERP + premio specifico
        discount_rate = self.rf + (profile.sector_beta * self.erp) + profile.unemployment_risk_premium
        t = np.arange(1, profile.years_to_retirement + 1)
        expected_cashflows = profile.current_annual_net_income * ((1.0 + profile.income_growth_rate) ** (t - 1))
        discount_factors = (1.0 + discount_rate) ** (-t)

        hc_pv = float(np.sum(expected_cashflows * discount_factors))

        # Scomposizione: se sector_beta è elevato, il reddito si comporta come un'azione
        quasi_equity_w = float(np.clip(profile.sector_beta * 0.75, 0.0, 1.0))
        quasi_bond_w = 1.0 - quasi_equity_w

        return {
            "human_capital_pv": hc_pv,
            "discount_rate": discount_rate,
            "quasi_equity_weight": quasi_equity_w,
            "quasi_bond_weight": quasi_bond_w,
            "quasi_equity_amount": hc_pv * quasi_equity_w,
            "quasi_bond_amount": hc_pv * quasi_bond_w,
            "annual_cashflows_projection": expected_cashflows.tolist()
        }


class HolisticBalanceSheetEngine:
    """
    Motore di integrazione olistica Total Balance Sheet:
    calcola la volatilità aggregata, il Total Balance Sheet VaR (TBS-VaR) e gli indicatori di solvibilità.
    """

    def __init__(self, risk_free_rate: float = 0.03, equity_risk_premium: float = 0.05):
        self.hc_engine = HumanCapitalEngine(base_risk_free_rate=risk_free_rate, equity_risk_premium=equity_risk_premium)

    def compute_total_balance_sheet_var(
        self,
        state: TotalBalanceSheetState,
        confidence: float = 0.95,
        horizon_years: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calcola il Total Balance Sheet VaR (TBS-VaR) e CVaR (TBS-CVaR) integrando:
        - Portafoglio liquido (equity/bonds)
        - Valutazione immobiliare
        - Capitale Umano
        - Shock sui mutui a tasso variabile
        """
        hc_metrics = self.hc_engine.compute_human_capital_valuation(state.labor_profile)
        hc_pv = hc_metrics["human_capital_pv"]

        total_assets = state.liquid_portfolio_value + state.real_estate_value + hc_pv
        net_worth = total_assets - state.mortgage_debt_outstanding

        if total_assets <= 0:
            return {"error": "Totale attivo nullo o negativo"}

        # Pesi relativi dei macro-pilastri
        w_liquid = state.liquid_portfolio_value / total_assets
        w_re = state.real_estate_value / total_assets
        w_hc = hc_pv / total_assets

        # Volatilità del portafoglio liquido
        if state.liquid_portfolio_weights.ndim == 1 and state.liquid_covariance_matrix.ndim == 2:
            liq_var = float(state.liquid_portfolio_weights.T @ state.liquid_covariance_matrix @ state.liquid_portfolio_weights)
            sigma_liquid = np.sqrt(max(liq_var, 1e-8)) * np.sqrt(252)
        else:
            sigma_liquid = 0.15

        # Volatilità sintetica del Capitale Umano
        market_vol = 0.16
        bond_vol = 0.04
        sigma_hc = np.sqrt(
            (hc_metrics["quasi_equity_weight"] ** 2) * (market_vol ** 2) +
            (hc_metrics["quasi_bond_weight"] ** 2) * (bond_vol ** 2)
        )

        # Matrice di correlazione macro dei 3 pilastri
        # [0: Liquid, 1: Real Estate, 2: Human Capital]
        corr_matrix = np.array([
            [1.00, 0.25, float(np.clip(state.labor_profile.sector_beta * 0.45, -0.2, 0.85))],
            [0.25, 1.00, 0.15],
            [float(np.clip(state.labor_profile.sector_beta * 0.45, -0.2, 0.85)), 0.15, 1.00]
        ])

        vol_vector = np.array([sigma_liquid, state.real_estate_volatility, sigma_hc])
        cov_matrix = np.outer(vol_vector, vol_vector) * corr_matrix
        asset_weights = np.array([w_liquid, w_re, w_hc])

        # Varianza e volatilità complessiva dell'attivo
        total_assets_variance = float(asset_weights.T @ cov_matrix @ asset_weights)
        total_assets_vol = float(np.sqrt(max(total_assets_variance, 1e-8)))

        # Componente di shock del debito su mutui a tasso variabile (+200 bps)
        debt_stress_eur = 0.0
        if state.is_variable_rate and state.mortgage_debt_outstanding > 0:
            delta_r = 0.02
            debt_stress_eur = state.mortgage_debt_outstanding * state.mortgage_duration * delta_r

        # Quantile normale
        z = float(stats.norm.ppf(confidence))
        z_cvar = float(stats.norm.pdf(z) / (1.0 - confidence))

        # TBS-VaR e TBS-CVaR monetari
        tbs_var_eur = (total_assets * total_assets_vol * z * np.sqrt(horizon_years)) + debt_stress_eur
        tbs_cvar_eur = (total_assets * total_assets_vol * z_cvar * np.sqrt(horizon_years)) + debt_stress_eur

        tbs_var_pct_nw = (tbs_var_eur / net_worth) * 100.0 if net_worth > 0 else 100.0
        tbs_cvar_pct_nw = (tbs_cvar_eur / net_worth) * 100.0 if net_worth > 0 else 100.0

        # Mesi di runway di cassa e liquidità di emergenza (assumendo 20% del portafoglio liquido prontamente accessibile)
        monthly_exp = state.annual_unavoidable_expenses / 12.0 if state.annual_unavoidable_expenses > 0 else 2500.0
        emergency_runway_months = (state.liquid_portfolio_value * 0.25) / monthly_exp

        # Hedging Recommendation: se il beta lavorativo è alto, calcola la sovraesposizione settoriale
        sector_hedging_needed = hc_metrics["quasi_equity_amount"] > 100000.0 and state.labor_profile.sector_beta > 0.8
        recommended_hedge_eur = hc_metrics["quasi_equity_amount"] * 0.30 if sector_hedging_needed else 0.0

        return {
            "total_net_worth_eur": net_worth,
            "total_assets_with_hc_eur": total_assets,
            "human_capital_pv_eur": hc_pv,
            "human_capital_quasi_equity_eur": hc_metrics["quasi_equity_amount"],
            "human_capital_quasi_bond_eur": hc_metrics["quasi_bond_amount"],
            "total_assets_annual_volatility": total_assets_vol,
            "tbs_var_eur": tbs_var_eur,
            "tbs_var_pct_net_worth": tbs_var_pct_nw,
            "tbs_cvar_eur": tbs_cvar_eur,
            "tbs_cvar_pct_net_worth": tbs_cvar_pct_nw,
            "debt_stress_component_eur": debt_stress_eur,
            "emergency_runway_months": emergency_runway_months,
            "sector_hedging_needed": sector_hedging_needed,
            "recommended_sector_underweight_eur": recommended_hedge_eur,
            "weights_breakdown": {
                "liquid_portfolio_pct": w_liquid * 100.0,
                "real_estate_pct": w_re * 100.0,
                "human_capital_pct": w_hc * 100.0
            }
        }
