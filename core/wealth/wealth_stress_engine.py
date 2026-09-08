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
        "name": "🌪️ Stagflazione Ipertrofica & Crisi Energetica (2022-Style)",
        "description": "Forte shock dell'offerta, inflazione al 6.5%, rialzo tassi BCE/Fed (+250 bps), calo simultaneo azionario/obbligazionario e aumento rate mutui.",
        "equity_shock_pct": -25.0,
        "bonds_shock_pct": -12.0,
        "real_estate_shock_pct": -8.0,
        "physical_gold_shock_pct": +15.0,
        "pension_shock_pct": -18.0,
        "mortgage_rate_hike_bps": 250.0,
        "living_expenses_hike_pct": +15.0,
        "income_shock_pct": 0.0,
        "extra_expense_cash": 0.0,
        "duration_months": 24
    },
    "REAL_ESTATE_CRISIS": {
        "name": "🏡 Crisi Immobiliare & Stretta Creditizia",
        "description": "Crollo delle valutazioni immobiliari (-20%), contrazione del credito bancario e impennata rate mutui a tasso variabile (+300 bps).",
        "equity_shock_pct": -15.0,
        "bonds_shock_pct": -5.0,
        "real_estate_shock_pct": -20.0,
        "physical_gold_shock_pct": +5.0,
        "pension_shock_pct": -10.0,
        "mortgage_rate_hike_bps": 300.0,
        "living_expenses_hike_pct": +5.0,
        "income_shock_pct": -10.0,
        "extra_expense_cash": 0.0,
        "duration_months": 36
    },
    "BLACK_SWAN": {
        "name": "🦅 Cigno Nero Sistemico & Liquidity Freeze",
        "description": "Crash finanziario globale stile 2008 (-40% azionario, -70% crypto, -15% real estate, congelamento della liquidità interbancaria).",
        "equity_shock_pct": -40.0,
        "bonds_shock_pct": -8.0,
        "real_estate_shock_pct": -15.0,
        "physical_gold_shock_pct": -10.0,
        "pension_shock_pct": -30.0,
        "mortgage_rate_hike_bps": 150.0,
        "living_expenses_hike_pct": +8.0,
        "income_shock_pct": -20.0,
        "extra_expense_cash": 0.0,
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
    },
    "GFC_2008": {
        "name": "📉 Crisi Finanziaria Subprime 2008 (Deflazionaria)",
        "description": "Deleveraging sistemico globale: crollo azionario -45%, contrazione immobiliare -15%, flight-to-safety su oro (+22%) e tagli tassi d'emergenza.",
        "equity_shock_pct": -45.0,
        "bonds_shock_pct": +8.0,
        "real_estate_shock_pct": -15.0,
        "physical_gold_shock_pct": +22.0,
        "pension_shock_pct": -25.0,
        "mortgage_rate_hike_bps": -150.0,
        "living_expenses_hike_pct": -2.0,
        "income_shock_pct": -15.0,
        "extra_expense_cash": 5000.0,
        "duration_months": 24
    },
    "COVID_2020": {
        "name": "🦠 Crash Repentino COVID-19 & Rimbalzo",
        "description": "Vendite violente e repentine in 30 giorni (-34%), congelamento transazioni immobiliari, zero rialzo tassi e spinta su spese essenziali.",
        "equity_shock_pct": -34.0,
        "bonds_shock_pct": +4.0,
        "real_estate_shock_pct": 0.0,
        "physical_gold_shock_pct": +8.0,
        "pension_shock_pct": -15.0,
        "mortgage_rate_hike_bps": 0.0,
        "living_expenses_hike_pct": +12.0,
        "income_shock_pct": -25.0,
        "extra_expense_cash": 10000.0,
        "duration_months": 12
    }
}


# ── CALCOLO NON-LINEARE DELL'AMMORTAMENTO MUTUO SOTTO STRESS ──

def calculate_stressed_mortgage_impact(
    total_liabilities: float,
    rate_hike_bps: float,
    base_rate: float = 2.0,
    duration_years: int = 20
) -> Dict[str, Any]:
    """
    Calcola l'impatto non-lineare di uno shock sui tassi Euribor/mutuo applicando
    la formula standard di ammortamento alla francese (rata costante):
    PMT = P * [r*(1+r)^n] / [(1+r)^n - 1]
    """
    if total_liabilities <= 0 or duration_years <= 0:
        return {
            "base_rate": base_rate,
            "stressed_rate": base_rate,
            "pre_monthly_payment": 0.0,
            "post_monthly_payment": 0.0,
            "monthly_payment_delta": 0.0,
            "annual_extra_interest": 0.0,
            "total_extra_interest_scenario": 0.0
        }

    total_months = duration_years * 12
    r0 = (max(0.01, base_rate) / 100.0) / 12.0
    r1 = (max(0.01, base_rate + (rate_hike_bps / 100.0)) / 100.0) / 12.0

    # Rata pre-shock
    if r0 > 0:
        pmt0 = total_liabilities * (r0 * (1 + r0) ** total_months) / ((1 + r0) ** total_months - 1)
    else:
        pmt0 = total_liabilities / total_months

    # Rata post-shock
    if r1 > 0:
        pmt1 = total_liabilities * (r1 * (1 + r1) ** total_months) / ((1 + r1) ** total_months - 1)
    else:
        pmt1 = total_liabilities / total_months

    monthly_delta = pmt1 - pmt0
    annual_extra = monthly_delta * 12.0

    return {
        "base_rate": round(base_rate, 2),
        "stressed_rate": round(max(0.01, base_rate + (rate_hike_bps / 100.0)), 2),
        "pre_monthly_payment": round(pmt0, 2),
        "post_monthly_payment": round(pmt1, 2),
        "monthly_payment_delta": round(monthly_delta, 2),
        "annual_extra_interest": round(annual_extra, 2)
    }


# ── LIQUIDITY SQUEEZE & ANTI-FORCED SELLING PROTOCOL ──

def calculate_liquidity_squeeze(
    liquid_cash: float,
    monthly_expenses: float,
    monthly_income: float,
    monthly_debt_extra: float,
    cpi_inflation_pct: float,
    income_shock_pct: float,
    extra_expense_cash: float,
    duration_months: int,
    equity_shock_pct: float
) -> Dict[str, Any]:
    """
    Simula l'erosione mese per mese del fondo di liquidità per identificare:
    1. Point of Forced Liquidation (t*): Mesi prima dell'esaurimento della cassa.
    2. Capital Shortfall: Ammontare del deficit che costringe a vendere asset.
    3. Irreversible Loss: Perdita permanente da liquidazione forzata sui minimi di mercato.
    4. Dynamic FIRE SWR: Ricalcolo prudenziale del Safe Withdrawal Rate con regole Guyton-Klinger.
    """
    # Spese mensili con inflazione e maggior costo mutuo
    stressed_expenses = monthly_expenses * (1.0 + max(-0.5, cpi_inflation_pct / 100.0))
    total_monthly_outflow = stressed_expenses + max(0.0, monthly_debt_extra)

    # Reddito mensile ridotto dallo shock
    stressed_income = monthly_income * (1.0 - max(0.0, min(1.0, income_shock_pct / 100.0)))

    # Net Burn Rate (fabbisogno mensile da attingere dalla liquidità)
    net_monthly_burn = max(0.0, total_monthly_outflow - stressed_income)

    # Cassa disponibile dopo eventuale spesa straordinaria
    available_cash = max(0.0, liquid_cash - extra_expense_cash)

    # Mesi prima dell'esaurimento completo (Point of Forced Liquidation)
    if net_monthly_burn > 0:
        months_to_forced_liquidation = round(available_cash / net_monthly_burn, 1)
    else:
        months_to_forced_liquidation = 999.0

    forced_liquidation_triggered = months_to_forced_liquidation < duration_months

    if forced_liquidation_triggered:
        months_in_deficit = max(0.0, duration_months - months_to_forced_liquidation)
        capital_shortfall_eur = round(months_in_deficit * net_monthly_burn, 2)
        # Perdita permanente da svendita ai minimi di mercato
        eq_drop = abs(min(0.0, equity_shock_pct / 100.0))
        if 0 < eq_drop < 0.95:
            irreversible_loss_eur = round(capital_shortfall_eur * (1.0 / (1.0 - eq_drop) - 1.0), 2)
        else:
            irreversible_loss_eur = 0.0
    else:
        capital_shortfall_eur = 0.0
        irreversible_loss_eur = 0.0

    # Dynamic Safe Withdrawal Rate (Guyton-Klinger Rules)
    base_swr = 4.0
    # Decurtazione del prelievo se azionario crolla o se inflazione sale
    eq_penalty = 0.15 if abs(equity_shock_pct) >= 20.0 else (0.08 if abs(equity_shock_pct) >= 10.0 else 0.0)
    cpi_penalty = 0.10 if cpi_inflation_pct >= 5.0 else 0.0
    stressed_swr = max(2.2, round(base_swr * (1.0 - eq_penalty - cpi_penalty), 2))

    return {
        "initial_liquid_cash": round(liquid_cash, 2),
        "monthly_expenses_stressed": round(stressed_expenses, 2),
        "total_monthly_outflow": round(total_monthly_outflow, 2),
        "stressed_monthly_income": round(stressed_income, 2),
        "net_monthly_burn": round(net_monthly_burn, 2),
        "months_to_forced_liquidation": months_to_forced_liquidation,
        "forced_liquidation_triggered": forced_liquidation_triggered,
        "capital_shortfall_eur": capital_shortfall_eur,
        "irreversible_loss_eur": irreversible_loss_eur,
        "fire_swr_base_pct": base_swr,
        "fire_swr_stressed_pct": stressed_swr
    }


# ── ESECUZIONE STRESS TEST PATRIMONIALE COMPLETO ──

def run_wealth_stress_test(
    summary_data: Dict[str, Any],
    scenario_params: Dict[str, Any],
    risk_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Simula l'impatto economico completo di uno shock patrimoniale congiunto multi-asset.
    Supporta la trasmissione ticker-level e calcola ammortamento alla francese e liquidity squeeze.
    """
    pre_cash = float(summary_data.get("liquid_cash", 0.0))
    pre_inv = float(summary_data.get("financial_investments", 0.0))
    pre_phys = float(summary_data.get("physical_assets", 0.0))
    pre_re = float(summary_data.get("real_estate_total", summary_data.get("real_estate_equity", 0.0)))
    pre_pen = float(summary_data.get("pension_total", 0.0))
    pre_debts = float(summary_data.get("total_liabilities", 0.0))
    pre_expenses = float(summary_data.get("monthly_expenses", 2500.0))
    pre_income = float(summary_data.get("monthly_income", pre_expenses * 1.35))
    pre_nw = (pre_cash + pre_inv + pre_phys + pre_re + pre_pen) - pre_debts

    # Estrazione percentuali di shock
    eq_shock = float(scenario_params.get("equity_shock_pct", 0.0)) / 100.0
    phys_shock = float(scenario_params.get("physical_gold_shock_pct", 0.0)) / 100.0
    re_shock = float(scenario_params.get("real_estate_shock_pct", 0.0)) / 100.0
    pen_shock = float(scenario_params.get("pension_shock_pct", 0.0)) / 100.0
    extra_expense = float(scenario_params.get("extra_expense_cash", 0.0))
    rate_hike_bps = float(scenario_params.get("mortgage_rate_hike_bps", 0.0))
    cpi_inflation = float(scenario_params.get("living_expenses_hike_pct", 0.0))
    income_shock = float(scenario_params.get("income_shock_pct", 0.0))
    duration_m = int(scenario_params.get("duration_months", 12))

    # 1. Calcolo Asset Finanziari con Trasmissione Ticker-Level se disponibile
    ticker_details = []
    df_positions = getattr(risk_context, "df_positions", None)
    if df_positions is not None and not df_positions.empty and "current_value" in df_positions.columns:
        tot_pos_val = float(df_positions["current_value"].sum())
        if tot_pos_val > 0:
            post_inv = 0.0
            for _, row in df_positions.iterrows():
                tk = str(row.get("ticker", "ASSET"))
                v = float(row.get("current_value", 0.0))
                tk_shock = eq_shock
                post_v = max(0.0, v * (1.0 + tk_shock))
                post_inv += post_v
                ticker_details.append({
                    "ticker": tk,
                    "pre_value": v,
                    "post_value": round(post_v, 2),
                    "shock_pct": round(tk_shock * 100.0, 1),
                    "delta": round(post_v - v, 2)
                })
        else:
            post_inv = max(0.0, pre_inv * (1.0 + eq_shock))
    else:
        post_inv = max(0.0, pre_inv * (1.0 + eq_shock))
    delta_inv = post_inv - pre_inv

    # 2. Calcolo Altri Asset Patrimoniali
    post_phys = max(0.0, pre_phys * (1.0 + phys_shock))
    delta_phys = post_phys - pre_phys

    post_re = max(0.0, pre_re * (1.0 + re_shock))
    delta_re = post_re - pre_re

    post_pen = max(0.0, pre_pen * (1.0 + pen_shock))
    delta_pen = post_pen - pre_pen

    # 3. Calcolo Impatto Mutuo / Debito Non-Lineare (Ammortamento alla Francese)
    mortgage_impact = calculate_stressed_mortgage_impact(
        total_liabilities=pre_debts,
        rate_hike_bps=rate_hike_bps,
        base_rate=2.0,
        duration_years=20
    )
    monthly_debt_delta = mortgage_impact["monthly_payment_delta"]
    debt_extra_cost = max(0.0, monthly_debt_delta * duration_m)

    # 4. Calcolo Liquidity Squeeze & Anti-Forced Selling
    liquidity_squeeze = calculate_liquidity_squeeze(
        liquid_cash=pre_cash,
        monthly_expenses=pre_expenses,
        monthly_income=pre_income,
        monthly_debt_extra=monthly_debt_delta,
        cpi_inflation_pct=cpi_inflation,
        income_shock_pct=income_shock,
        extra_expense_cash=extra_expense,
        duration_months=duration_m,
        equity_shock_pct=scenario_params.get("equity_shock_pct", 0.0)
    )

    # 5. Calcolo Cassa Residua Post-Shock
    post_cash = max(0.0, pre_cash - extra_expense - debt_extra_cost)
    delta_cash = post_cash - pre_cash

    post_debts = pre_debts
    delta_debts = 0.0

    post_nw = (post_cash + post_inv + post_phys + post_re + post_pen) - post_debts
    delta_nw = post_nw - pre_nw
    pct_nw_change = (delta_nw / pre_nw * 100.0) if pre_nw > 0 else 0.0

    # Runway Post-Shock
    stressed_monthly_burn = max(100.0, (pre_expenses * (1.0 + cpi_inflation / 100.0)) + max(0.0, monthly_debt_delta))
    post_runway = post_cash / stressed_monthly_burn
    post_health_score = max(5.0, min(100.0, (post_nw / max(1.0, pre_nw)) * 85.0))

    return {
        "scenario_name": scenario_params.get("name", "Stress Test Personalizzato"),
        "scenario_duration_months": duration_m,
        "pre_shock": {
            "net_worth": pre_nw,
            "liquid_cash": pre_cash,
            "financial_investments": pre_inv,
            "physical_assets": pre_phys,
            "real_estate": pre_re,
            "pension": pre_pen,
            "debts": pre_debts,
            "health_score": float(summary_data.get("wealth_health_score", 85.0)),
            "monthly_expenses": pre_expenses,
            "monthly_income": pre_income
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
        },
        "mortgage_impact": mortgage_impact,
        "liquidity_squeeze": liquidity_squeeze,
        "ticker_breakdown": ticker_details
    }


# ── UNIFIED MACRO STRESS ENGINE CLASS ──

class UnifiedMacroStressEngine:
    """
    Classe istituzionale che orchestra l'integrazione Risk-Wealth per simulare
    scenari macro congiunti su portafoglio titoli, mutui, liquidità e FIRE SWR.
    """
    def __init__(self, workspace_context: Optional[Any] = None):
        self.ctx = workspace_context

    def execute_stress_test(
        self,
        summary_data: Dict[str, Any],
        scenario_key_or_params: Any
    ) -> Dict[str, Any]:
        """Esegue lo stress test integrato."""
        if isinstance(scenario_key_or_params, str):
            scenario_params = PRESET_STRESS_SCENARIOS.get(
                scenario_key_or_params,
                PRESET_STRESS_SCENARIOS["STAGFLATION"]
            )
        else:
            scenario_params = scenario_key_or_params

        risk_ctx = getattr(self.ctx, "risk", None) if self.ctx else None
        return run_wealth_stress_test(summary_data, scenario_params, risk_context=risk_ctx)


# ── GENERAZIONE GRAFICI PLOTLY ISTITUZIONALI ──

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


def create_liquidity_squeeze_timeline_chart(stress_result: Dict[str, Any]) -> go.Figure:
    """
    Genera un grafico Plotly istituzionale dell'erosione temporale della liquidità
    e dell'eventuale Point of Forced Liquidation (t*).
    """
    lq = stress_result.get("liquidity_squeeze", {})
    init_cash = float(lq.get("initial_liquid_cash", stress_result["pre_shock"]["liquid_cash"]))
    net_burn = float(lq.get("net_monthly_burn", 2000.0))
    duration = int(stress_result.get("scenario_duration_months", 24))
    months = np.arange(0, duration + 1)

    # Traiettoria cassa mese per mese
    cash_trajectory = [max(0.0, init_cash - (net_burn * m)) for m in months]

    fig = go.Figure()

    # Area di liquidità
    fig.add_trace(go.Scatter(
        x=months,
        y=cash_trajectory,
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2.5),
        marker=dict(size=5, color="#60a5fa"),
        name="Cassa Residua (€)",
        fill="tozeroy",
        fillcolor="rgba(59, 130, 246, 0.12)"
    ))

    # Soglia critica di esaurimento (Zero Cassa)
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text="Soglia Zero Cassa (Vendita Forzata)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ef4444", size=11)
    )

    # Annotazione Point of Forced Liquidation
    t_star = float(lq.get("months_to_forced_liquidation", 999.0))
    if t_star <= duration:
        fig.add_vline(
            x=t_star,
            line_dash="dot",
            line_color="#f59e0b",
            annotation_text=f"Point of Forced Liquidation: {t_star:.1f} Mesi",
            annotation_position="top left",
            annotation_font=dict(color="#f59e0b", size=11, family="Outfit")
        )
        fig.add_trace(go.Scatter(
            x=[t_star],
            y=[0],
            mode="markers",
            marker=dict(color="#ef4444", size=12, symbol="x"),
            name="Inizio Liquidazione Forzata"
        ))

    fig.update_layout(
        title=f"<b>Liquidity Squeeze Timeline & Point of Forced Liquidation — {stress_result['scenario_name']}</b>",
        xaxis_title="Mesi dallo Shock Iniziale",
        yaxis_title="Liquidità Residua (€)",
        template="plotly_dark",
        plot_bgcolor="rgba(10, 14, 20, 0.6)",
        paper_bgcolor="rgba(10, 14, 20, 0.0)",
        margin=dict(l=20, r=20, t=50, b=30),
        height=380,
        font=dict(family="Outfit, -apple-system, sans-serif", color="#e6edf3"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
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
