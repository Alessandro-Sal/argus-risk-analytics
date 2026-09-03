# ==============================================================================
# core/wealth/wealth_stress_engine.py
# ARGUS — Global Wealth Stress-Testing 3D & Waterfall Engine
# ==============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ── SCENARI MACROECONOMICI ISTITUZIONALI PREDEFINITI ──
PRESET_STRESS_SCENARIOS = {
    "STAGFLATION": {
        "name": "🌪️ Stagflazione Ipertrofica & Crisi Energetica",
        "description": "Forte shock dell'offerta, inflazione al 6.5%, rialzo tassi BCE/Fed (+250 bps), calo azionario e aumento costi fissi.",
        "equity_shock_pct": -25.0,
        "bonds_shock_pct": -12.0,
        "real_estate_shock_pct": -8.0,
        "physical_gold_shock_pct": +15.0,
        "pension_shock_pct": -18.0,
        "mortgage_rate_hike_bps": 250.0,
        "living_expenses_hike_pct": +15.0,
        "income_shock_pct": 0.0,
        "duration_months": 24
    },
    "REAL_ESTATE_CRISIS": {
        "name": "🏡 Crisi Immobiliare & Stretta Creditizia",
        "description": "Crollo delle valutazioni immobiliari (-20%), aumento insolvenze affitti (-30%) e impennata rate mutui variabili (+300 bps).",
        "equity_shock_pct": -15.0,
        "bonds_shock_pct": -5.0,
        "real_estate_shock_pct": -20.0,
        "physical_gold_shock_pct": +5.0,
        "pension_shock_pct": -10.0,
        "mortgage_rate_hike_bps": 300.0,
        "living_expenses_hike_pct": +5.0,
        "income_shock_pct": -10.0,
        "duration_months": 36
    },
    "BLACK_SWAN": {
        "name": "🦅 Cigno Nero Sistemico & Liquidity Freeze",
        "description": "Crash finanziario globale stile 2008 / Lehman (-40% azionario, -70% crypto, -30% collezionismo/caveau, liquidità bloccata).",
        "equity_shock_pct": -40.0,
        "bonds_shock_pct": -8.0,
        "real_estate_shock_pct": -15.0,
        "physical_gold_shock_pct": -10.0,
        "pension_shock_pct": -30.0,
        "mortgage_rate_hike_bps": 150.0,
        "living_expenses_hike_pct": +8.0,
        "income_shock_pct": -20.0,
        "duration_months": 18
    },
    "INCOME_SHOCK": {
        "name": "⚡ Shock Reddituale & Spesa Straordinaria",
        "description": "Interruzione improvvisa del reddito da lavoro per 12 mesi combinata con un esborso straordinario di emergenza di € 25.000.",
        "equity_shock_pct": -10.0,
        "bonds_shock_pct": -2.0,
        "real_estate_shock_pct": 0.0,
        "physical_gold_shock_pct": 0.0,
        "pension_shock_pct": -5.0,
        "mortgage_rate_hike_bps": 0.0,
        "living_expenses_hike_pct": +10.0,
        "income_shock_pct": -100.0,
        "extra_expense_cash": 25000.0,
        "duration_months": 12
    }
}


def run_wealth_stress_test(
    summary_data: Dict[str, Any],
    scenario_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Simula l'impatto economico completo di uno shock patrimoniale multi-asset.
    Restituisce metriche Pre-Shock e Post-Shock con dettaglio per ciascuna asset class.
    """
    pre_cash = float(summary_data.get("liquid_cash", 0.0))
    pre_inv = float(summary_data.get("financial_investments", 0.0))
    pre_phys = float(summary_data.get("physical_assets", 0.0))
    pre_re = float(summary_data.get("real_estate_total", summary_data.get("real_estate_equity", 0.0)))
    pre_pen = float(summary_data.get("pension_total", 0.0))
    pre_debts = float(summary_data.get("total_liabilities", 0.0))
    pre_nw = (pre_cash + pre_inv + pre_phys + pre_re + pre_pen) - pre_debts

    # Estrazione percentuali di shock
    eq_shock = float(scenario_params.get("equity_shock_pct", 0.0)) / 100.0
    phys_shock = float(scenario_params.get("physical_gold_shock_pct", 0.0)) / 100.0
    re_shock = float(scenario_params.get("real_estate_shock_pct", 0.0)) / 100.0
    pen_shock = float(scenario_params.get("pension_shock_pct", 0.0)) / 100.0
    extra_expense = float(scenario_params.get("extra_expense_cash", 0.0))
    rate_hike_bps = float(scenario_params.get("mortgage_rate_hike_bps", 0.0))

    # Calcolo Post-Shock per componente
    post_inv = max(0.0, pre_inv * (1.0 + eq_shock))
    delta_inv = post_inv - pre_inv

    post_phys = max(0.0, pre_phys * (1.0 + phys_shock))
    delta_phys = post_phys - pre_phys

    post_re = max(0.0, pre_re * (1.0 + re_shock))
    delta_re = post_re - pre_re

    post_pen = max(0.0, pre_pen * (1.0 + pen_shock))
    delta_pen = post_pen - pre_pen

    # Calcolo impatto su cassa (extra spesa e incremento oneri debito)
    debt_extra_cost = pre_debts * (rate_hike_bps / 10000.0) * (float(scenario_params.get("duration_months", 12)) / 12.0)
    post_cash = max(0.0, pre_cash - extra_expense - debt_extra_cost)
    delta_cash = post_cash - pre_cash

    post_debts = pre_debts  # Il debito nominale capitale residuo non diminuisce
    delta_debts = 0.0

    post_nw = (post_cash + post_inv + post_phys + post_re + post_pen) - post_debts
    delta_nw = post_nw - pre_nw
    pct_nw_change = (delta_nw / pre_nw * 100.0) if pre_nw > 0 else 0.0

    # Calcolo Health Score Post-Shock
    post_runway = post_cash / max(100.0, float(summary_data.get("monthly_expenses", 2500.0)) * (1.0 + float(scenario_params.get("living_expenses_hike_pct", 0.0)) / 100.0))
    post_health_score = max(5.0, min(100.0, (post_nw / max(1.0, pre_nw)) * 85.0))

    return {
        "scenario_name": scenario_params.get("name", "Stress Test Personalizzato"),
        "pre_shock": {
            "net_worth": pre_nw,
            "liquid_cash": pre_cash,
            "financial_investments": pre_inv,
            "physical_assets": pre_phys,
            "real_estate": pre_re,
            "pension": pre_pen,
            "debts": pre_debts,
            "health_score": float(summary_data.get("wealth_health_score", 85.0))
        },
        "post_shock": {
            "net_worth": post_nw,
            "liquid_cash": post_cash,
            "financial_investments": post_inv,
            "physical_assets": post_phys,
            "real_estate": post_re,
            "pension": post_pen,
            "debts": post_debts,
            "health_score": round(post_health_score, 1),
            "runway_months": round(post_runway, 1)
        },
        "deltas": {
            "net_worth": delta_nw,
            "net_worth_pct": pct_nw_change,
            "liquid_cash": delta_cash,
            "financial_investments": delta_inv,
            "physical_assets": delta_phys,
            "real_estate": delta_re,
            "pension": delta_pen,
            "debts": delta_debts
        }
    }


def create_wealth_waterfall_chart(stress_result: Dict[str, Any]) -> go.Figure:
    """Genera un grafico Waterfall Plotly istituzionale della scomposizione dello shock."""
    pre_nw = stress_result["pre_shock"]["net_worth"]
    post_nw = stress_result["post_shock"]["net_worth"]
    d = stress_result["deltas"]

    x_labels = [
        "Net Worth Iniziale",
        "Investimenti Finanziari",
        "Immobili",
        "Caveau / Fisico",
        "Previdenza",
        "Cassa & Spese Extra",
        "Net Worth Stressato"
    ]
    y_values = [
        pre_nw,
        d["financial_investments"],
        d["real_estate"],
        d["physical_assets"],
        d["pension"],
        d["liquid_cash"],
        post_nw
    ]
    measures = [
        "absolute",
        "relative",
        "relative",
        "relative",
        "relative",
        "relative",
        "total"
    ]

    fig = go.Figure(go.Waterfall(
        name="Stress Breakdown",
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        text=[f"€ {v:+,.0f}" if i not in [0, 6] else f"€ {v:,.0f}" for i, v in enumerate(y_values)],
        textposition="outside",
        connector={"line": {"color": "rgba(255, 255, 255, 0.2)", "dash": "dot"}},
        decreasing={"marker": {"color": "#ef4444"}},
        increasing={"marker": {"color": "#10b981"}},
        totals={"marker": {"color": "#ff9900"}}
    ))

    fig.update_layout(
        title=f"<b>Scomposizione dello Shock Patrimoniale — {stress_result['scenario_name']}</b>",
        template="plotly_dark",
        plot_bgcolor="rgba(10, 14, 20, 0.6)",
        paper_bgcolor="rgba(10, 14, 20, 0.0)",
        margin=dict(l=20, r=20, t=50, b=30),
        height=380,
        font=dict(family="Outfit, -apple-system, sans-serif", color="#e6edf3")
    )
    return fig


def simulate_wealth_recovery_trajectories(
    post_net_worth: float,
    base_cagr: float = 0.065,
    volatility: float = 0.12,
    horizon_years: int = 10,
    n_sims: int = 1000
) -> go.Figure:
    """Simula 1,000 traiettorie Monte Carlo della ripresa del Net Worth post-stress."""
    dt = 1.0
    time_steps = np.arange(0, horizon_years + 1)
    
    np.random.seed(42)
    shocks = np.random.normal(
        (base_cagr - 0.5 * volatility ** 2) * dt,
        volatility * np.sqrt(dt),
        (n_sims, horizon_years)
    )
    
    trajectories = np.zeros((n_sims, horizon_years + 1))
    trajectories[:, 0] = post_net_worth
    for t in range(1, horizon_years + 1):
        trajectories[:, t] = trajectories[:, t - 1] * np.exp(shocks[:, t - 1])

    p10 = np.percentile(trajectories, 10, axis=0)
    p50 = np.percentile(trajectories, 50, axis=0)
    p90 = np.percentile(trajectories, 90, axis=0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_steps, y=p90, mode="lines", line=dict(color="rgba(16, 185, 129, 0.3)", width=1),
        name="Scenario Ottimistico (90° Pct)"
    ))
    fig.add_trace(go.Scatter(
        x=time_steps, y=p10, mode="lines", line=dict(color="rgba(239, 68, 68, 0.3)", width=1),
        fill="tonexty", fillcolor="rgba(255, 153, 0, 0.08)",
        name="Scenario Prudente (10° Pct)"
    ))
    fig.add_trace(go.Scatter(
        x=time_steps, y=p50, mode="lines+markers", line=dict(color="#ff9900", width=3),
        name="Traiettoria Mediana Attesa (50° Pct)"
    ))

    fig.update_layout(
        title="<b>Proiezione Monte Carlo della Ripresa del Net Worth a 10 Anni</b>",
        xaxis_title="Anni dallo Shock",
        yaxis_title="Patrimonio Netto Stimato (€)",
        template="plotly_dark",
        plot_bgcolor="rgba(10, 14, 20, 0.6)",
        paper_bgcolor="rgba(10, 14, 20, 0.0)",
        margin=dict(l=20, r=20, t=50, b=30),
        height=360,
        font=dict(family="Outfit, -apple-system, sans-serif", color="#e6edf3")
    )
    return fig
