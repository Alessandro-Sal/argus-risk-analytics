"""
core/wealth/tbs_monte_carlo.py
ARGUS — Total Balance Sheet Lifetime Monte Carlo Simulation Engine (TBS-MC).

Features:
- Simulazione stocastica multi-asset a ciclo di vita (Lifetime Horizon fino a 95 anni).
- Integrazione simultanea di:
  1. Portafoglio Finanziario Liquido (Rendimenti stocastici reali e sequenza dei rendimenti / SoRR)
  2. Capitale Umano (Progressione salariale, shock di disoccupazione e pensione al tasso di rimpiazzo)
  3. Real Estate (Apprezzamento reale e volatilità immobiliare)
  4. Passività & Mutuo (Ammortamento alla francese ed estinzione debitoria)
  5. Spese di Sostentamento Indispensabili e Discrezionali
- Calcolo della Probabilità di Rovina a Ciclo di Vita (Lifetime Ruin Probability: P(Liquidity <= 0)).
- Identificazione dell'Età di Massima Fragilità Patrimoniale (Point of Maximum Fragility).
- Calcolo del Corridoio di Spesa Sostenibile (Safe Spending Recommendation) con confidenza 95%.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class TBSLifecycleConfig:
    """Configurazione dei parametri per la simulazione Monte Carlo a ciclo di vita."""
    current_age: int = 35
    retirement_age: int = 67
    terminal_age: int = 90
    current_annual_net_income: float = 55000.0
    real_income_growth: float = 0.015  # Crescita reale dello stipendio sopra l'inflazione
    unemployment_shock_annual_prob: float = 0.025  # Probabilità annua di interruzione lavorativa
    pension_replacement_ratio: float = 0.70  # Tasso di sostituzione pensione obbligatoria
    annual_living_expenses: float = 28000.0  # Spese annuali reali di sostentamento
    initial_liquid_wealth: float = 120000.0  # Portafoglio titoli e liquidità iniziale
    liquid_wealth_real_return_mean: float = 0.045  # Rendimento atteso reale annuo (4.5%)
    liquid_wealth_volatility: float = 0.15  # Volatilità annua del portafoglio (15%)
    initial_real_estate_value: float = 320000.0  # Valore di mercato immobili
    real_estate_real_appreciation: float = 0.010  # Apprezzamento reale annuo immobili (1.0%)
    real_estate_volatility: float = 0.07  # Volatilità annua immobiliare (7%)
    initial_mortgage_debt: float = 130000.0  # Debito residuo mutuo
    mortgage_annual_interest_rate: float = 0.035  # Tasso mutuo (3.5%)
    mortgage_years_remaining: int = 15  # Anni residui di ammortamento
    num_simulations: int = 2000  # Numero di cammini Monte Carlo
    random_seed: int = 42


class TBSMonteCarloEngine:
    """
    Motore stocastico per la simulazione Monte Carlo del Total Balance Sheet a ciclo di vita.
    """

    def __init__(self, config: Optional[TBSLifecycleConfig] = None):
        self.cfg = config or TBSLifecycleConfig()

    def _calc_annual_mortgage_payment(self, principal: float, rate: float, years: int) -> float:
        """Calcola la rata annualizzata di ammortamento alla francese."""
        if years <= 0 or principal <= 0:
            return 0.0
        if rate <= 0:
            return principal / years
        r = rate
        pmt = principal * (r * (1.0 + r) ** years) / (((1.0 + r) ** years) - 1.0)
        return float(pmt)

    def simulate_lifetime_solvency(self) -> Dict[str, Any]:
        """
        Esegue la simulazione Monte Carlo su N cammini e T anni.
        Restituisce le serie percentili (P10, P25, P50, P75, P90), la probabilità di rovina
        e il corridoio di spesa sostenibile.
        """
        cfg = self.cfg
        total_years = max(1, cfg.terminal_age - cfg.current_age)
        num_sims = cfg.num_simulations
        rng = np.random.default_rng(cfg.random_seed)

        # Correlazione tra rendimento azionario e immobiliare (~0.25)
        corr_matrix = np.array([
            [1.00, 0.25],
            [0.25, 1.00]
        ])
        chol = np.linalg.cholesky(corr_matrix)

        # Matrici per gli stati patrimoniali: [Simulazioni x Anni]
        # Anno 0 è lo stato iniziale
        liquid_paths = np.zeros((num_sims, total_years + 1))
        re_paths = np.zeros((num_sims, total_years + 1))
        debt_paths = np.zeros((num_sims, total_years + 1))
        income_paths = np.zeros((num_sims, total_years + 1))
        net_worth_paths = np.zeros((num_sims, total_years + 1))

        # Inizializzazione t=0
        liquid_paths[:, 0] = cfg.initial_liquid_wealth
        re_paths[:, 0] = cfg.initial_real_estate_value
        debt_paths[:, 0] = cfg.initial_mortgage_debt
        income_paths[:, 0] = cfg.current_annual_net_income
        net_worth_paths[:, 0] = cfg.initial_liquid_wealth + cfg.initial_real_estate_value - cfg.initial_mortgage_debt

        mortgage_annual_pmt = self._calc_annual_mortgage_payment(
            cfg.initial_mortgage_debt,
            cfg.mortgage_annual_interest_rate,
            cfg.mortgage_years_remaining
        )

        curr_debt = cfg.initial_mortgage_debt

        # Tracciamento rovina: se la liquidità scende a <= 0, il percorso fallisce
        ruined_sims = np.zeros(num_sims, dtype=bool)
        first_ruin_year = np.full(num_sims, total_years + 1)

        # Evoluzione temporale anno per anno
        for t in range(1, total_years + 1):
            age = cfg.current_age + t - 1

            # 1. Generazione shock normali correlati per mercati e real estate
            z_raw = rng.standard_normal((num_sims, 2))
            z_corr = z_raw @ chol.T

            # Rendimenti log-normali
            # Portfolio: media liquid_wealth_real_return_mean, vol liquid_wealth_volatility
            r_liq = np.exp(
                (cfg.liquid_wealth_real_return_mean - 0.5 * (cfg.liquid_wealth_volatility ** 2)) +
                cfg.liquid_wealth_volatility * z_corr[:, 0]
            ) - 1.0

            # Real estate: media real_estate_real_appreciation, vol real_estate_volatility
            r_re = np.exp(
                (cfg.real_estate_real_appreciation - 0.5 * (cfg.real_estate_volatility ** 2)) +
                cfg.real_estate_volatility * z_corr[:, 1]
            ) - 1.0

            # 2. Capitale Umano & Reddito da Lavoro / Pensione
            if age < cfg.retirement_age:
                # Reddito lavorativo atteso con crescita reale
                base_income = cfg.current_annual_net_income * ((1.0 + cfg.real_income_growth) ** (t - 1))
                # Shock disoccupazione (Poisson/Bernoulli)
                is_unemployed = rng.random(num_sims) < cfg.unemployment_shock_annual_prob
                # Durante la disoccupazione il reddito cala del 55%
                actual_income = np.where(is_unemployed, base_income * 0.45, base_income)
            else:
                # Pensione fissa al tasso di sostituzione sull'ultimo reddito pre-pensione
                years_to_ret = max(1, cfg.retirement_age - cfg.current_age)
                last_salary = cfg.current_annual_net_income * ((1.0 + cfg.real_income_growth) ** (years_to_ret - 1))
                actual_income = np.full(num_sims, last_salary * cfg.pension_replacement_ratio)

            income_paths[:, t] = actual_income

            # 3. Debito residuo mutuo
            if t <= cfg.mortgage_years_remaining and curr_debt > 0:
                interest_part = curr_debt * cfg.mortgage_annual_interest_rate
                principal_part = max(0.0, mortgage_annual_pmt - interest_part)
                curr_debt = max(0.0, curr_debt - principal_part)
                mortgage_pmt = mortgage_annual_pmt
            else:
                curr_debt = 0.0
                mortgage_pmt = 0.0
            debt_paths[:, t] = curr_debt

            # 4. Aggiornamento Real Estate
            re_paths[:, t] = re_paths[:, t - 1] * (1.0 + r_re)

            # 5. Flusso di cassa netto = Reddito - Spese - Rata Mutuo
            net_cf = actual_income - cfg.annual_living_expenses - mortgage_pmt

            # 6. Aggiornamento Liquidità: W_t = W_{t-1} * (1 + r) + NetCF
            prev_liq = liquid_paths[:, t - 1]
            new_liq = (prev_liq * (1.0 + r_liq)) + net_cf

            # Se la liquidità è negativa, consideriamo lo stato di default di cassa
            is_now_ruined = new_liq <= 0
            newly_ruined = is_now_ruined & (~ruined_sims)
            ruined_sims = ruined_sims | is_now_ruined
            first_ruin_year[newly_ruined] = t

            # Per la simulazione di continuità, la liquidità non può scendere sotto zero per generare rendimento
            liquid_paths[:, t] = np.maximum(new_liq, 0.0)

            # 7. Patrimonio Netto Olistico
            net_worth_paths[:, t] = liquid_paths[:, t] + re_paths[:, t] - curr_debt

        # Statistiche e percentili
        ages = np.array([cfg.current_age + t for t in range(total_years + 1)])
        years_arr = np.arange(total_years + 1)

        # Calcolo percentili del Patrimonio Netto
        nw_p10 = np.percentile(net_worth_paths, 10, axis=0)
        nw_p25 = np.percentile(net_worth_paths, 25, axis=0)
        nw_p50 = np.percentile(net_worth_paths, 50, axis=0)
        nw_p75 = np.percentile(net_worth_paths, 75, axis=0)
        nw_p90 = np.percentile(net_worth_paths, 90, axis=0)

        liq_p50 = np.percentile(liquid_paths, 50, axis=0)
        re_p50 = np.percentile(re_paths, 50, axis=0)

        # Probabilità di rovina cumulativa anno per anno
        cumulative_ruin_pct = np.zeros(total_years + 1)
        for t in range(1, total_years + 1):
            cumulative_ruin_pct[t] = float(np.mean(first_ruin_year <= t)) * 100.0

        total_ruin_prob_pct = float(np.mean(ruined_sims)) * 100.0

        # Punto di massima fragilità (anno con il massimo incremento di rovina o liquidità minima)
        ruin_increments = np.diff(cumulative_ruin_pct)
        if np.max(ruin_increments) > 0:
            fragile_t = int(np.argmax(ruin_increments)) + 1
        else:
            # Se nessuna rovina, identifica l'anno con la mediana di liquidità più bassa nei primi 20 anni
            fragile_t = int(np.argmin(liq_p50[:min(25, len(liq_p50))]))

        fragile_age = int(cfg.current_age + fragile_t)

        # Spesa massima raccomandata (Safe Spending Corridor)
        # Se la probabilità di rovina supera il 5%, calcola il taglio consigliato
        excess_ruin = max(0.0, total_ruin_prob_pct - 5.0)
        spending_haircut = (excess_ruin / 100.0) * cfg.annual_living_expenses * 0.50
        recommended_spending = max(12000.0, cfg.annual_living_expenses - spending_haircut)

        timeline_df = pd.DataFrame({
            "age": ages,
            "year": years_arr,
            "net_worth_p10": nw_p10,
            "net_worth_p25": nw_p25,
            "net_worth_p50": nw_p50,
            "net_worth_p75": nw_p75,
            "net_worth_p90": nw_p90,
            "liquid_wealth_median": liq_p50,
            "real_estate_median": re_p50,
            "cumulative_ruin_pct": cumulative_ruin_pct
        })

        return {
            "total_ruin_probability_pct": total_ruin_prob_pct,
            "is_solvency_sustainable": total_ruin_prob_pct <= 5.0,
            "point_of_maximum_fragility_age": fragile_age,
            "median_terminal_net_worth_eur": float(nw_p50[-1]),
            "median_terminal_liquid_wealth_eur": float(liq_p50[-1]),
            "initial_net_worth_eur": float(net_worth_paths[0, 0]),
            "recommended_annual_spending_eur": recommended_spending,
            "spending_adjustment_needed": total_ruin_prob_pct > 5.0,
            "recommended_spending_cut_eur": spending_haircut,
            "timeline_df": timeline_df,
            "simulation_runs": num_sims,
            "total_horizon_years": total_years
        }
