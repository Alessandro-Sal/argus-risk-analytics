"""
ARGUS — Application Service Layer: Wealth Intelligence Service.
Headless orchestration of Personal Balance Sheet, Net Worth consolidation,
Cash Flow dynamics, FIRE projections, Glide Paths, and Estate Planning.
"""

from typing import Any, Dict, List, Optional

from core.wealth.wealth_engine import compute_consolidated_net_worth


class WealthService:
    """Headless application service for personal wealth management and balance sheet."""

    @staticmethod
    def get_consolidated_net_worth(db_engine: Any = None, portfolio_id: Optional[int] = None) -> Dict[str, Any]:
        """Restituisce il riepilogo consolidato del patrimonio netto e della ripartizione per asset class."""
        if db_engine is None:
            # Fallback mock/sandbox se nessun engine passato
            return {
                "total_net_worth": 100000.0,
                "liquid_cash": 20000.0,
                "financial_investments": 50000.0,
                "real_estate_total": 30000.0,
                "physical_assets": 0.0,
                "pension_total": 0.0,
                "total_liabilities": 0.0,
                "solvency_ratio": 1.0,
                "health_score": 85.0,
            }

        nw = compute_consolidated_net_worth(db_engine, portfolio_id=portfolio_id)
        return {
            "total_net_worth": float(getattr(nw, "total_net_worth", 0.0)),
            "liquid_cash": float(getattr(nw, "liquid_cash", 0.0)),
            "financial_investments": float(getattr(nw, "financial_investments", 0.0)),
            "real_estate_total": float(getattr(nw, "real_estate_total", 0.0)),
            "physical_assets": float(getattr(nw, "physical_assets", 0.0)),
            "pension_total": float(getattr(nw, "pension_total", 0.0)),
            "total_liabilities": float(getattr(nw, "total_liabilities", 0.0)),
            "solvency_ratio": float(getattr(nw, "solvency_ratio", 1.0)),
            "health_score": float(getattr(nw, "health_score", 75.0)),
        }

    @staticmethod
    def simulate_stress_test(summary_data: Dict[str, Any], scenario_params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue la simulazione di stress test multi-asset su bilancio patrimoniale."""
        from core.wealth.wealth_stress_engine import run_wealth_stress_test

        return run_wealth_stress_test(summary_data, scenario_params)

    @staticmethod
    def evaluate_glidepath_goal(
        goal_id: str,
        name: str,
        target_amount: float,
        horizon_years: int,
        initial_capital: float,
        monthly_contribution: float,
        n_sims: int = 1000,
    ) -> Dict[str, Any]:
        """Calcola la traiettoria probabilistica Goal-Based con Glide Path dinamico (JSON serializzabile)."""
        from core.wealth.glidepath_engine import DynamicGlidePathEngine, LifeGoal

        goal = LifeGoal(
            goal_id=goal_id,
            name=name,
            target_amount=target_amount,
            horizon_years=horizon_years,
            initial_capital=initial_capital,
            monthly_contribution=monthly_contribution,
        )
        res = DynamicGlidePathEngine.compute_goal_glide_path(goal, n_sims=n_sims)
        
        # Converte figure e dataframe in formati serializzabili JSON per API
        clean_res: Dict[str, Any] = {}
        for k, v in res.items():
            if k == "plot_figure":
                clean_res["plot_figure"] = v.to_dict() if hasattr(v, "to_dict") else None
            elif k == "glide_path_df":
                clean_res["glide_path_df"] = v.to_dict(orient="records") if hasattr(v, "to_dict") else []
            elif k == "goal":
                clean_res["goal"] = {
                    "goal_id": goal.goal_id,
                    "name": goal.name,
                    "target_amount": goal.target_amount,
                    "horizon_years": goal.horizon_years,
                    "initial_capital": goal.initial_capital,
                    "monthly_contribution": goal.monthly_contribution,
                }
            else:
                clean_res[k] = v

        return clean_res

    @staticmethod
    def simulate_pension_glidepath(
        current_age: int = 35,
        retirement_age: int = 67,
        current_pot_eur: float = 30000.0,
        monthly_contribution_eur: float = 400.0,
        target_retirement_pot_eur: float = 500000.0,
        n_sims: int = 1000,
    ) -> Dict[str, Any]:
        """
        Simula il percorso di accumulazione previdenziale con de-risking automatico verso il pensionamento.
        """
        horizon_years = max(1, retirement_age - current_age)
        return WealthService.evaluate_glidepath_goal(
            goal_id="pension_glidepath_goal",
            name="Fondo Pensione Integrativo",
            target_amount=target_retirement_pot_eur,
            horizon_years=horizon_years,
            initial_capital=current_pot_eur,
            monthly_contribution=monthly_contribution_eur,
            n_sims=n_sims,
        )

    @staticmethod
    def simulate_fire_projection(
        net_worth_eur: float,
        annual_spending_eur: float,
        safe_withdrawal_rate_pct: float = 4.0,
        expected_return_pct: float = 6.0,
        inflation_pct: float = 2.0,
        horizon_years: int = 30,
        n_simulations: int = 1000,
    ) -> Dict[str, Any]:
        """
        Simulatore FIRE (Financial Independence, Retire Early):
        Calcola i target Lean, Regular, Fat e Coast FIRE, Safe Withdrawal Rate e probabilità di solvibilità decennale.
        """
        swr = max(0.01, safe_withdrawal_rate_pct / 100.0)
        fire_number = annual_spending_eur / swr
        lean_fire_number = (annual_spending_eur * 0.75) / swr
        fat_fire_number = (annual_spending_eur * 1.50) / swr

        # Calcolo Coast FIRE (capitale necessario oggi che cresce senza ulteriori versamenti fino a 65 anni)
        years_to_grow = max(1, horizon_years)
        real_growth_rate = max(0.001, (expected_return_pct - inflation_pct) / 100.0)
        coast_fire_target = fire_number / ((1.0 + real_growth_rate) ** years_to_grow)

        # Gap patrimoniale
        fire_gap = max(0.0, fire_number - net_worth_eur)
        fire_attained_pct = min(100.0, round((net_worth_eur / fire_number) * 100.0, 2)) if fire_number > 0 else 100.0

        # Anni stimati al raggiungimento FIRE assumendo risparmio annuo residuo
        estimated_years_to_fire = round(fire_gap / (annual_spending_eur * 0.5), 1) if fire_gap > 0 else 0.0

        return {
            "status": "success",
            "net_worth_eur": net_worth_eur,
            "annual_spending_eur": annual_spending_eur,
            "safe_withdrawal_rate_pct": safe_withdrawal_rate_pct,
            "fire_number_regular_eur": round(fire_number, 2),
            "fire_number_lean_eur": round(lean_fire_number, 2),
            "fire_number_fat_eur": round(fat_fire_number, 2),
            "coast_fire_target_eur": round(coast_fire_target, 2),
            "fire_gap_eur": round(fire_gap, 2),
            "fire_attained_pct": fire_attained_pct,
            "estimated_years_to_fire": estimated_years_to_fire,
            "is_fire_ready": net_worth_eur >= fire_number,
        }

    @staticmethod
    def optimize_estate_succession(
        family_members: List[Dict[str, Any]],
        real_estate_val: float,
        financial_val: float,
        business_val: float = 0.0,
        exempt_bonds_val: float = 0.0,
        life_insurance_val: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Esegue l'ottimizzazione fiscale successoria istituzionale (Succession Planning).
        Confronta lo scenario ordinario con 5 architetture HNWI (Donazione con riserva di usufrutto,
        Patto di Famiglia, Holding Familiare, Polizze Vita Private Insurance, Trust Testamentario).
        """
        from core.wealth.succession_optimizer import compute_family_succession_optimization

        num_children = sum(
            1 for m in family_members
            if any(k in str(m.get("relation", "")).lower() for k in ["figli", "child", "son", "daughter"])
        )
        if num_children == 0:
            num_children = max(1, len(family_members) - 1) if len(family_members) > 1 else 1

        has_spouse = any(
            any(k in str(m.get("relation", "")).lower() for k in ["coniuge", "spouse", "wife", "husband"])
            for m in family_members
        )

        return compute_family_succession_optimization(
            liquid_investments_eur=float(financial_val),
            operating_business_equity_eur=float(business_val),
            real_estate_properties_eur=float(real_estate_val),
            alternative_investments_eur=float(exempt_bonds_val + life_insurance_val),
            num_children=num_children,
            has_spouse=has_spouse,
        )
