# ==============================================================================
# core/wealth/glidepath_engine.py
# ARGUS — Goal-Based Dynamic Glide Path 3D & Life Events Probabilistic Engine
# ==============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.graph_objects as go


@dataclass
class LifeGoal:
    goal_id: str
    name: str
    target_amount: float
    horizon_years: int
    initial_capital: float
    monthly_contribution: float
    priority: str = "ALTA"  # 'ALTA', 'MEDIA', 'FLESSIBILE'


class DynamicGlidePathEngine:
    """
    Motore di pianificazione finanziaria Goal-Based con Glide Path dinamico.
    Ricalcola anno per anno l'asset allocation ottimale per minimizzare il rischio di
    mancato raggiungimento del target all'avvicinarsi della data dell'evento.
    """

    @staticmethod
    def compute_goal_glide_path(goal: LifeGoal, n_sims: int = 1000) -> Dict[str, Any]:
        years = np.arange(0, goal.horizon_years + 1)
        tot_years = goal.horizon_years

        # ── FORMULA GLIDE PATH DINAMICO ──
        # Più ci si avvicina alla scadenza (t -> tot_years), più la quota equity si riduce
        # Da max 85% equity (a 15+ anni) fino a 15% equity (a scadenza 0-1 anni)
        equity_weights = []
        bond_weights = []
        cash_weights = []

        for y in years:
            years_left = tot_years - y
            if years_left >= 10:
                eq = 0.85
                bnd = 0.15
                csh = 0.00
            elif years_left >= 5:
                eq = 0.55
                bnd = 0.35
                csh = 0.10
            elif years_left >= 2:
                eq = 0.30
                bnd = 0.50
                csh = 0.20
            else:
                eq = 0.15
                bnd = 0.45
                csh = 0.40

            equity_weights.append(eq)
            bond_weights.append(bnd)
            cash_weights.append(csh)

        # ── SIMULAZIONE MONTE CARLO PROBABILISTICA ──
        np.random.seed(101)
        trajectories = np.zeros((n_sims, len(years)))
        trajectories[:, 0] = goal.initial_capital

        # Rendimenti attesi e volatilità per asset class
        mu_eq, vol_eq = 0.08, 0.16
        mu_bnd, vol_bnd = 0.035, 0.06
        mu_csh, vol_csh = 0.025, 0.005

        annual_savings = goal.monthly_contribution * 12.0

        for t in range(1, len(years)):
            eq_w = equity_weights[t - 1]
            bnd_w = bond_weights[t - 1]
            csh_w = cash_weights[t - 1]

            port_mu = eq_w * mu_eq + bnd_w * mu_bnd + csh_w * mu_csh
            port_vol = np.sqrt((eq_w * vol_eq) ** 2 + (bnd_w * vol_bnd) ** 2 + (csh_w * vol_csh) ** 2)

            shocks = np.random.normal(port_mu - 0.5 * port_vol ** 2, port_vol, n_sims)
            trajectories[:, t] = trajectories[:, t - 1] * np.exp(shocks) + annual_savings

        final_values = trajectories[:, -1]
        success_prob = float(np.mean(final_values >= goal.target_amount) * 100.0)

        p10 = np.percentile(trajectories, 10, axis=0)
        p50 = np.percentile(trajectories, 50, axis=0)
        p90 = np.percentile(trajectories, 90, axis=0)

        # Grafico Plotly Proiezione e Glide Path
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=p90, mode="lines",
            line=dict(color="rgba(16, 185, 129, 0.3)", width=1),
            name="Scenario Favorevole (90° Pct)"
        ))
        fig.add_trace(go.Scatter(
            x=years, y=p10, mode="lines",
            line=dict(color="rgba(239, 68, 68, 0.3)", width=1),
            fill="tonexty", fillcolor="rgba(255, 153, 0, 0.08)",
            name="Scenario Prudente (10° Pct)"
        ))
        fig.add_trace(go.Scatter(
            x=years, y=p50, mode="lines+markers",
            line=dict(color="#ff9900", width=3),
            name="Traiettoria Mediana Attesa (50° Pct)"
        ))
        fig.add_trace(go.Scatter(
            x=[0, tot_years], y=[goal.target_amount, goal.target_amount],
            mode="lines", line=dict(color="#ef4444", width=2, dash="dash"),
            name=f"Target (€ {goal.target_amount:,.0f})"
        ))

        fig.update_layout(
            title=f"<b>Proiezione Goal '{goal.name}' — Probabilità di Successo: {success_prob:.1f}%</b>",
            xaxis_title="Orizzonte Temporale (Anni)",
            yaxis_title="Capitale Accumulato (€)",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=30),
            height=360,
            font=dict(family="Outfit, sans-serif", color="#e6edf3")
        )

        glide_df = pd.DataFrame({
            "Anno": years,
            "Anni Residui": tot_years - years,
            "Azioni (%)": [f"{w*100:.0f}%" for w in equity_weights],
            "Obbligazioni (%)": [f"{w*100:.0f}%" for w in bond_weights],
            "Liquidità / XEON (%)": [f"{w*100:.0f}%" for w in cash_weights],
            "Capitale Mediano (€)": [f"€ {val:,.0f}" for val in p50]
        })

        return {
            "goal": goal,
            "success_probability_pct": success_prob,
            "expected_final_value": float(p50[-1]),
            "p10_final_value": float(p10[-1]),
            "p90_final_value": float(p90[-1]),
            "plot_figure": fig,
            "glide_path_df": glide_df
        }
