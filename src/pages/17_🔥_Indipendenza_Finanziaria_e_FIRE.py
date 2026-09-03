# ============================================================
# src/pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py
# ARGUS Wealth Management — Financial Independence, FIRE & Stress Testing
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import importlib
import core.ui_utils
import core.wealth.wealth_db
import core.wealth.wealth_engine
import core.wealth

importlib.reload(core.ui_utils)
importlib.reload(core.wealth.wealth_db)
importlib.reload(core.wealth.wealth_engine)
importlib.reload(core.wealth)

from core.fetcher import get_engine
from core.ui_utils import (
    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_page_header,
    apply_plotly_theme
)
from core.sidebar import render_sidebar
from core.wealth.wealth_db import (
    get_cashflow_records,
    get_wealth_portfolios,
    get_wealth_goals,
    save_wealth_goal,
    delete_wealth_goal
)
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_cashflow_analytics,
    compute_fire_analytics,
    compute_wealth_stress_test,
    compute_wealth_risk_integrated_analytics,
    compute_goal_based_monte_carlo,
    compute_dynamic_glide_path,
    compute_portfolio_tco_and_fee_drag,
    compute_sequence_of_returns_risk_engine
)


st.set_page_config(page_title="Indipendenza & FIRE | ARGUS Wealth", page_icon="🔥", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "wealth")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    st.title("🔥 ARGUS Wealth — Indipendenza Finanziaria & FIRE")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per calcolare il target FIRE, i bucket temporali e lo stress testing macroeconomico.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="fire_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p17")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Indipendenza Finanziaria, FIRE & Risk Bridge",
    subtitle="Simulatore FIRE (Trinity Study / 4% SWR), Liquidity-at-Risk (Anti-Forced Selling), Net Worth-at-Risk e Stress Testing Macro.",
    icon="🔥"
)

if len(prof_map) > 1:
    sel_pid = st.selectbox(
        "Profilo Patrimoniale:",
        options=list(prof_map.keys()),
        format_func=lambda pid: f"📁 {prof_map[pid]}",
        index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
        key="fire_profile_selector_widget"
    )
    if sel_pid != current_pid:
        st.session_state["wealth_active_portfolio_id"] = sel_pid
        st.rerun()


# Recupera dati patrimoniali e cash flow
nw_summary = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
df_cf = get_cashflow_records(engine, portfolio_id=current_pid)
cf_analytics = compute_cashflow_analytics(df_cf)

# Inizializza parametri FIRE
fire_base = compute_fire_analytics(nw_summary, cf_analytics)

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Target FIRE Number", fmt_eur(fire_base["fire_number"]), delta=f"Spesa: {fmt_eur(fire_base['annual_expense'])}/anno", delta_color="normal")
with c2:
    metric_card("Capitale Generatore", fmt_eur(fire_base["invested_assets"]), delta=f"{fire_base['progress_pct']:.1f}% del Target", delta_color="normal")
with c3:
    yr_str = f"{fire_base['years_to_fire']} Anni" if fire_base['years_to_fire'] is not None else "> 45 Anni"
    age_str = f"Età Stimata: {fire_base['fire_age']} Anni" if fire_base['fire_age'] is not None else "Incrementa il risparmio"
    metric_card("Tempo alla Libertà", yr_str, delta=age_str, delta_color="normal")
with c4:
    coast_status = "✅ Raggiunto" if fire_base["is_coast_fire"] else "⏳ In Accumulo"
    metric_card("Coast FIRE (65 Anni)", coast_status, delta=f"Soglia: {fmt_eur(fire_base['coast_fire_number'])}", delta_color="normal")

st.divider()

# ── NAVIGAZIONE A TAB ───────────────────────────────────────
tab_fire, tab_stress, tab_goals, tab_srr, tab_tco = st.tabs([
    "🔥 Simulatore FIRE & Traiettorie",
    "🌪️ Wealth Macro Stress Testing",
    "🎯 Goal-Based Multi-Traguardo & SPI %",
    "🔮 Sequence of Returns Risk (SRR)",
    "💸 Costi Nascosti & TER Drag"
])

# ============================================================
# TAB 1: SIMULATORE FIRE & TRAIETTORIE
# ============================================================
with tab_fire:
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        age_in = st.slider("Età Attuale", min_value=18, max_value=60, value=28)
        swr_val_default = float(st.session_state.get("wealth_fire_swr", 4.0))
        swr_in = st.slider("Safe Withdrawal Rate (%)", min_value=2.0, max_value=6.0, value=swr_val_default, step=0.1)
    with fc2:
        exp_ret_in = st.slider("Rendimento Portafoglio Atteso (%)", min_value=3.0, max_value=12.0, value=7.5, step=0.5)
        inf_in = st.slider("Inflazione Attesa (%)", min_value=1.0, max_value=6.0, value=2.0, step=0.5)
    with fc3:
        use_custom_exp = st.checkbox("Personalizza Spesa Annua", value=False)
        custom_exp_val = st.number_input("Spesa Annua (€)", min_value=5000.0, value=float(round(fire_base["annual_expense"], 0)), step=1000.0, disabled=not use_custom_exp)
    with fc4:
        use_custom_sav = st.checkbox("Personalizza Risparmio Annuo", value=False)
        custom_sav_val = st.number_input("Risparmio Annuo (€)", min_value=0.0, value=float(round(fire_base["annual_savings"], 0)), step=1000.0, disabled=not use_custom_sav)

    # Ricalcola FIRE con input interattivi
    fire_calc = compute_fire_analytics(
        nw_summary,
        cf_analytics,
        current_age=age_in,
        swr_pct=swr_in,
        exp_return_pct=exp_ret_in,
        inflation_pct=inf_in,
        custom_annual_expense=custom_exp_val if use_custom_exp else None,
        custom_annual_savings=custom_sav_val if use_custom_sav else None
    )

    # 4 Archetipi FIRE Cards
    st.write("")
    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #6366f1; border-radius:10px; padding:14px 16px; min-height:100px;">
            <div style="font-size:12px; font-weight:600; color:#8b949e; text-transform:uppercase;">Standard FIRE (100%)</div>
            <div style="font-size:18px; font-weight:700; color:#ffffff; margin:4px 0;">{fmt_eur(fire_calc['fire_number'])}</div>
            <div style="font-size:11px; color:#8b949e;">Mantiene lo stile di vita attuale ({fmt_eur(fire_calc['annual_expense'])}/anno)</div>
        </div>
        """, unsafe_allow_html=True)
    with bc2:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #10b981; border-radius:10px; padding:14px 16px; min-height:100px;">
            <div style="font-size:12px; font-weight:600; color:#8b949e; text-transform:uppercase;">Lean FIRE (70%)</div>
            <div style="font-size:18px; font-weight:700; color:#10b981; margin:4px 0;">{fmt_eur(fire_calc['lean_fire_number'])}</div>
            <div style="font-size:11px; color:#8b949e;">Copre solo i bisogni primari essenziali ({fmt_eur(fire_calc['annual_expense']*0.7)}/anno)</div>
        </div>
        """, unsafe_allow_html=True)
    with bc3:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #ec4899; border-radius:10px; padding:14px 16px; min-height:100px;">
            <div style="font-size:12px; font-weight:600; color:#8b949e; text-transform:uppercase;">Fat FIRE (135%)</div>
            <div style="font-size:18px; font-weight:700; color:#ec4899; margin:4px 0;">{fmt_eur(fire_calc['fat_fire_number'])}</div>
            <div style="font-size:11px; color:#8b949e;">Stile di vita agiato con extra viaggi & lusso ({fmt_eur(fire_calc['annual_expense']*1.35)}/anno)</div>
        </div>
        """, unsafe_allow_html=True)
    with bc4:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #f59e0b; border-radius:10px; padding:14px 16px; min-height:100px;">
            <div style="font-size:12px; font-weight:600; color:#8b949e; text-transform:uppercase;">Coast FIRE (Target 65a)</div>
            <div style="font-size:18px; font-weight:700; color:#f59e0b; margin:4px 0;">{fmt_eur(fire_calc['coast_fire_number'])}</div>
            <div style="font-size:11px; color:#8b949e;">Capitale sufficiente per crescere autonomamente</div>
        </div>
        """, unsafe_allow_html=True)

    # Grafico Traiettoria FIRE
    st.write("")
    section("📈 Traiettoria di Accumulo Patrimoniale verso il FIRE Number")
    
    fig_fire = go.Figure()
    
    # Curva di accumulo
    fig_fire.add_trace(go.Scatter(
        x=fire_calc["timeline_ages"],
        y=fire_calc["proj_cap"],
        mode="lines+markers",
        name="Capitale Investito Proiettato",
        line=dict(color="#38bdf8", width=3),
        fill="tozeroy",
        fillcolor="rgba(56, 189, 248, 0.08)",
        hovertemplate="<b>Età: %{x} Anni</b><br>Patrimonio: €%{y:,.2f}<extra></extra>"
    ))

    # Linea FIRE Number
    fig_fire.add_hline(
        y=fire_calc["fire_number"],
        line_dash="dash",
        line_color="#6366f1",
        line_width=2,
        annotation_text=f"🎯 Standard FIRE: {fmt_eur(fire_calc['fire_number'])}",
        annotation_position="top left",
        annotation_font_color="#818cf8"
    )

    # Linea Lean FIRE
    fig_fire.add_hline(
        y=fire_calc["lean_fire_number"],
        line_dash="dot",
        line_color="#10b981",
        line_width=1.5,
        annotation_text=f"🌱 Lean FIRE: {fmt_eur(fire_calc['lean_fire_number'])}",
        annotation_position="bottom left",
        annotation_font_color="#34d399"
    )

    fig_fire.update_layout(
        xaxis_title="Età Anagrafica (Anni)",
        yaxis_title="Patrimonio Investito Netto (€)",
        height=390,
        margin=dict(t=20, l=15, r=15, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_fire, use_container_width=True)

# ============================================================
# TAB 2: WEALTH MACRO STRESS TESTING & RISK ENGINE BRIDGE
# ============================================================
with tab_stress:
    st.markdown("### 🌪️ Ponte Wealth ⇄ Risk: Liquidity-at-Risk & Net Worth Stress Testing")
    st.caption("Integrazione quantitativa diretta con i modelli di rischio: calibrazione del fondo di emergenza su CVaR 95% (Anti-Forced Selling) e stress test macroeconomici consolidati.")

    wr = compute_wealth_risk_integrated_analytics(engine, wealth_portfolio_id=current_pid)
    lar = wr["liquidity_at_risk"]
    swr_dyn = wr["dynamic_fire_swr"]

    # 1. Top KPI Row Ponte Risk
    rk1, rk2, rk3, rk4 = st.columns(4)
    with rk1:
        metric_card("Fondo Anti-Forced Selling", fmt_eur(lar["risk_adjusted_emergency_fund_target_eur"]), delta=f"Target: {lar['risk_adjusted_runway_target_months']} Mesi Runway", delta_color="normal", help_text="Dimensionamento ottimale del fondo emergenza calcolato dinamicamente sulla base della volatilità e del CVaR 95% del portafoglio per impedire liquidazioni forzate in drawdown.")
    with rk2:
        metric_card("Riserva Liquida Attuale", fmt_eur(nw_summary.liquid_cash), delta=f"Copertura: {nw_summary.runway_months:.1f} Mesi", delta_color="normal" if nw_summary.runway_months >= lar['risk_adjusted_runway_target_months'] else "inverse", help_text="Liquidità totale presente sui conti correnti del profilo patrimoniale.")
    with rk3:
        metric_card("Rischio Vendita Forzata", lar["forced_selling_risk_level"].split(" (")[0], delta="Protezione Drawdown", delta_color="normal" if "BASSO" in lar["forced_selling_risk_level"] else "inverse", help_text="Valutazione del rischio di dover vendere asset finanziari in perdita durante un crash di mercato per coprire spese correnti.")
    with rk4:
        metric_card("Dynamic FIRE SWR", f"{swr_dyn['dynamic_swr_pct']:.1f}% / Anno", delta=f"{fmt_eur(swr_dyn['monthly_safe_budget_eur'])} / Mese", delta_color="normal", help_text="Safe Withdrawal Rate calibrato in tempo reale sul regime di volatilità del mercato per neutralizzare il Sequence of Returns Risk.")

    st.write("")
    
    # 2. Dynamic SWR Regime Banner
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 14px 18px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
            <span style="font-weight: 750; color: #ffffff; font-size: 13.5px;">Regime Macro / Volatilità Rilevato:</span>
            <span style="margin-left: 8px; font-weight: 700; color: #38bdf8;">{swr_dyn['market_regime']}</span>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 3px;">{swr_dyn['regime_advice']}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Prelievo Annuo Sostenibile:</div>
            <div class="mono-num" style="font-size: 17px; font-weight: 800; color: #34d399;">€ {swr_dyn['annual_safe_income_eur']:,.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Tabella Scenari Macro Net Worth-at-Risk
    st.markdown("##### 🏛️ Matrice di Stress Macroeconomico Consolidato (Net Worth-at-Risk)")
    df_nwar = pd.DataFrame(wr["net_worth_at_risk_scenarios"])
    st.dataframe(
        df_nwar[["scenario", "descrizione", "net_worth_post_shock", "perdita_patrimonio_eur", "impatto_pct", "runway_post_shock"]],
        column_config={
            "scenario": st.column_config.TextColumn("Scenario Storico", width="medium"),
            "descrizione": st.column_config.TextColumn("Dinamica Macro", width="large"),
            "net_worth_post_shock": st.column_config.NumberColumn("Patrimonio Stressed (€)", format="€ %,.2f", width="medium"),
            "perdita_patrimonio_eur": st.column_config.NumberColumn("Perdita Netta (€)", format="€ %,.2f", width="small"),
            "impatto_pct": st.column_config.NumberColumn("Impatto NW (%)", format="%.1f%%", width="small"),
            "runway_post_shock": st.column_config.NumberColumn("Runway Residua", format="%.1f Mesi", width="small")
        },
        hide_index=True,
        use_container_width=True
    )

    st.write("")
    st.divider()

    # 4. Simulatore Interattivo di Shock Singolo
    section("🌪️ Simulatore Interattivo Dettagliato sul Patrimonio")
    
    st_c1, st_c2 = st.columns([1.1, 1.9], gap="medium")
    with st_c1:
        st.markdown("<span style='font-size:13px; font-weight:600; color:#e6edf3;'>Seleziona Scenario di Stress:</span>", unsafe_allow_html=True)
        scenario_choice = st.radio(
            "Seleziona Scenario di Stress Interattivo:",
            options=[
                ("crisis_2008", "📉 Crisi Finanziaria 2008"),
                ("stagflation", "⚡ Shock Stagflattivo"),
                ("crypto_winter", "❄️ Crypto Winter Estremo"),
                ("job_loss", "💼 Job Loss (6 Mesi Zero Entrate)")
            ],
            format_func=lambda x: x[1],
            label_visibility="collapsed",
            key="fire_stress_interactive_radio"
        )
        
        stress_res = compute_wealth_stress_test(nw_summary, scenario=scenario_choice[0])

    with st_c2:
        border_col = "#10b981" if stress_res['pnl_impact'] >= 0 else "#ef4444"
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid {border_col}; border-radius:10px; padding:16px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
            <div style="font-size:15.5px; font-weight:700; color:#ffffff; margin-bottom:4px;">{stress_res['title']}</div>
            <div style="font-size:12.5px; color:#8b949e; margin-bottom:14px; line-height: 1.4;">{stress_res['description']}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; background:rgba(0,0,0,0.25); border-radius:8px; padding:12px 16px;">
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Patrimonio Post-Shock</div>
                    <div style="font-size:19px; font-weight:700; color:#ffffff;">{fmt_eur(stress_res['stressed_net_worth'])}</div>
                </div>
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Variazione Net Worth</div>
                    <div style="font-size:19px; font-weight:700; color:{border_col};">{'+' if stress_res['pnl_impact']>=0 else ''}{fmt_eur(stress_res['pnl_impact'])} <span style="font-size:12.5px; font-weight:600;">({stress_res['pnl_pct']:+.1f}%)</span></div>
                </div>
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Runway di Sicurezza</div>
                    <div style="font-size:19px; font-weight:700; color:#38bdf8;">{stress_res['stressed_runway_months']} Mesi</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    section("📊 Confronto Asset Allocation: Prima vs Dopo lo Shock")
    
    df_comp = pd.DataFrame([
        {"Classe Asset": "Liquidità & Cash", "Pre-Shock": nw_summary.liquid_cash, "Post-Shock": stress_res["stressed_liquid"]},
        {"Classe Asset": "Investimenti Finanziari", "Pre-Shock": nw_summary.financial_investments, "Post-Shock": stress_res["stressed_financial"]},
        {"Classe Asset": "Caveau & Fisico (Oro/Orologi)", "Pre-Shock": nw_summary.physical_assets, "Post-Shock": stress_res["stressed_physical"]},
        {"Classe Asset": "Fondo Pensione", "Pre-Shock": nw_summary.pension_total, "Post-Shock": stress_res["stressed_pension"]}
    ])

    fig_stress_bar = go.Figure()
    fig_stress_bar.add_trace(go.Bar(
        x=df_comp["Classe Asset"],
        y=df_comp["Pre-Shock"],
        name="Pre-Shock (Attuale)",
        marker_color="#6366f1"
    ))
    fig_stress_bar.add_trace(go.Bar(
        x=df_comp["Classe Asset"],
        y=df_comp["Post-Shock"],
        name="Post-Shock (Stressed)",
        marker_color="#ef4444" if stress_res["pnl_impact"] < 0 else "#10b981"
    ))

    fig_stress_bar.update_layout(
        barmode="group",
        yaxis_title="Valore (€)",
        height=320,
        margin=dict(t=15, l=15, r=15, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_stress_bar, use_container_width=True, config={'displayModeBar': False})


# ============================================================
# TAB 3: GOAL-BASED MULTI-TRAGUARDO & STOCHASTIC MONTE CARLO (SPI %)
# ============================================================
with tab_goals:
    st.markdown("### 🎯 Goal-Based Investing & Struttura a 3 Bucket Temporali")
    st.caption("Pianificazione stocastica per traguardi di vita (Merton Jump-Diffusion), calcolo dell'indice di successo SPI % e Glide Path.")
    st.write("")

    bk1, bk2, bk3 = st.columns(3, gap="medium")
    
    # Bucket 1: Breve Termine (< 2 Anni)
    with bk1:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #10b981; border-radius:10px; padding:16px 18px; min-height:200px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">🛡️ Bucket 1 — Breve Termine</span>
                <span style="font-size:11px; background:rgba(16,185,129,0.15); color:#34d399; padding:2px 6px; border-radius:4px;">0–2 Anni</span>
            </div>
            <div style="font-size:11.5px; color:#8b949e; margin-top:4px;">Fondo Emergenza & Spese Immediate</div>
            <div style="font-size:22px; font-weight:700; color:#ffffff; margin:10px 0 4px 0;">{fmt_eur(nw_summary.liquid_cash)}</div>
            <div style="font-size:11px; color:#8b949e;">Copertura Spese: <b style="color:#34d399;">{nw_summary.runway_months} Mesi</b> di Runway</div>
            <hr style="border-color:rgba(255,255,255,0.08); margin:8px 0;">
            <div style="font-size:11px; color:#c9d1d9;">• Conti Correnti & Depositi<br>• Zero Volatilità / Massima Liquidità</div>
        </div>
        """, unsafe_allow_html=True)

    # Bucket 2: Medio Termine (2–7 Anni)
    with bk2:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #f59e0b; border-radius:10px; padding:16px 18px; min-height:200px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">🎯 Bucket 2 — Medio Termine</span>
                <span style="font-size:11px; background:rgba(245,158,11,0.15); color:#fbbf24; padding:2px 6px; border-radius:4px;">2–7 Anni</span>
            </div>
            <div style="font-size:11.5px; color:#8b949e; margin-top:4px;">Obiettivi di Vita & Beni Rifugio</div>
            <div style="font-size:22px; font-weight:700; color:#ffffff; margin:10px 0 4px 0;">{fmt_eur(nw_summary.physical_assets)}</div>
            <div style="font-size:11px; color:#8b949e;">Caveau & Metalli: <b style="color:#fbbf24;">{fmt_eur(nw_summary.precious_metals_total)}</b> Oro 18K</div>
            <hr style="border-color:rgba(255,255,255,0.08); margin:8px 0;">
            <div style="font-size:11px; color:#c9d1d9;">• Oro da Investimento, Immobili & Orologi<br>• Preservazione Reale del Capitale</div>
        </div>
        """, unsafe_allow_html=True)

    # Bucket 3: Lungo Termine (> 7 Anni)
    with bk3:
        b3_tot = nw_summary.financial_investments + nw_summary.pension_total
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #6366f1; border-radius:10px; padding:16px 18px; min-height:200px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">🚀 Bucket 3 — Crescita & FIRE</span>
                <span style="font-size:11px; background:rgba(99,102,241,0.15); color:#818cf8; padding:2px 6px; border-radius:4px;">> 7 Anni</span>
            </div>
            <div style="font-size:11.5px; color:#8b949e; margin-top:4px;">Mercati Finanziari & Previdenza</div>
            <div style="font-size:22px; font-weight:700; color:#ffffff; margin:10px 0 4px 0;">{fmt_eur(b3_tot)}</div>
            <div style="font-size:11px; color:#8b949e;">Azioni + Crypto + Fondo Pensione</div>
            <hr style="border-color:rgba(255,255,255,0.08); margin:8px 0;">
            <div style="font-size:11px; color:#c9d1d9;">• Portafogli Titoli ({fmt_eur(nw_summary.financial_investments)})<br>• Pensione Integrativa ({fmt_eur(nw_summary.pension_total)})</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.divider()

    # ── REGISTRO TRAGUARDI DI VITA ─────────────────────────────
    st.markdown("#### 🎯 Traguardi di Vita Registrati")
    
    df_goals = get_wealth_goals(engine, portfolio_id=current_pid)
    
    with st.expander("➕ Crea o Modifica Nuovo Obiettivo di Vita", expanded=df_goals.empty):
        with st.form("form_create_wealth_goal"):
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                g_name = st.text_input("Nome Obiettivo", value="Acquisto Prima Casa / Anticipo Mutuo")
                g_cat = st.selectbox("Categoria", ["real_estate", "fire", "education", "retirement", "luxury", "emergency_buffer", "custom"], format_func=lambda x: {
                    "real_estate": "🏠 Immobile / Casa",
                    "fire": "🔥 Indipendenza Finanziaria (FIRE)",
                    "education": "🎓 Istruzione Figli / Master",
                    "retirement": "🛡️ Pensione Integrativa",
                    "luxury": "⌚ Orologi & Beni di Lusso",
                    "emergency_buffer": "🛡️ Fondo Emergenza",
                    "custom": "⭐ Obiettivo Personalizzato"
                }.get(x, x))
                g_target = st.number_input("Capitale Obiettivo (€)", min_value=1000.0, value=150000.0, step=5000.0)
                g_curr = st.number_input("Capitale Attualmente Dedicato (€)", min_value=0.0, value=float(min(nw_summary.financial_investments, 25000.0)), step=1000.0)
            with g_col2:
                g_date = st.date_input("Data Target Raggiungimento", value=datetime.now().date().replace(year=datetime.now().year + 7))
                g_pac = st.number_input("Apporto Mensile Previsto (€/mese)", min_value=0.0, value=650.0, step=50.0)
                g_prio = st.selectbox("Priorità", ["high", "medium", "low"], format_func=lambda x: {"high": "🔴 Alta Priorità", "medium": "🟡 Media Priorità", "low": "🟢 Bassa Priorità"}.get(x, x))
                g_risk = st.selectbox("Profilo di Rischio", ["conservative", "moderate", "aggressive"], format_func=lambda x: {"conservative": "Conservativo (Bassa Volatilità)", "moderate": "Bilanciato (Volatilità Media)", "aggressive": "Aggressivo (Massima Crescita)"}.get(x, x), index=1)

            g_notes = st.text_input("Note & Strategia", value="PAC dedicato su ETF Azionario Globale + Obbligazionario")
            submit_goal = st.form_submit_button("💾 Salva Obiettivo nel Database", type="primary")
            if submit_goal:
                save_wealth_goal(engine, {
                    "portfolio_id": current_pid,
                    "name": g_name,
                    "category": g_cat,
                    "target_amount": g_target,
                    "target_date": g_date,
                    "current_amount": g_curr,
                    "monthly_contribution": g_pac,
                    "priority": g_prio,
                    "risk_tolerance": g_risk,
                    "notes": g_notes
                })
                st.success("✅ Obiettivo salvato con successo!")
                st.rerun()

    # Visualizzazione Card Traguardi
    if not df_goals.empty:
        goal_cols = st.columns(min(len(df_goals), 3))
        for i, (_, g_row) in enumerate(df_goals.iterrows()):
            with goal_cols[i % 3]:
                t_amt = float(g_row["target_amount"])
                c_amt = float(g_row["current_amount"])
                pct_reach = (c_amt / t_amt * 100.0) if t_amt > 0 else 0.0
                st.markdown(f"""
                <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #38bdf8; border-radius:10px; padding:14px 16px; margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#ffffff; font-size:13.5px;">{g_row['name']}</span>
                        <span style="font-size:11px; color:#38bdf8; font-weight:750;">{pct_reach:.1f}%</span>
                    </div>
                    <div style="font-size:11px; color:#8b949e; margin:4px 0 8px 0;">Scadenza: <b>{g_row['target_date']}</b> | PAC: <b>{fmt_eur(g_row['monthly_contribution'])}/m</b></div>
                    <div style="display:flex; justify-content:space-between; font-size:12px; color:#ffffff; margin-bottom:6px;">
                        <span>Attuale: {fmt_eur(c_amt)}</span>
                        <span>Target: {fmt_eur(t_amt)}</span>
                    </div>
                    <div style="width:100%; height:5px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                        <div style="width:{min(100.0, pct_reach):.1f}%; height:100%; background:#38bdf8; border-radius:3px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🗑️ Rimuovi #{g_row['goal_id']}", key=f"btn_del_goal_{g_row['goal_id']}", type="secondary"):
                    delete_wealth_goal(engine, int(g_row['goal_id']))
                    st.rerun()

    st.write("")
    st.divider()

    # ── MOTORE STOCASTICO MONTE CARLO & SPI % ──────────────────
    st.markdown("#### 🎲 Simulatore Stocastico Monte Carlo (Merton Jump-Diffusion)")
    st.caption("Valutazione del cono di probabilità reale su 5.000 iterazioni stocastiche con shock a salto negativi.")

    # Seleziona o configura parametri obiettivo per la simulazione
    sim_c1, sim_c2, sim_c3, sim_c4 = st.columns(4)
    with sim_c1:
        sim_curr_val = st.number_input("Capitale Iniziale (€)", min_value=0.0, value=float(nw_summary.financial_investments if nw_summary.financial_investments > 0 else 25000.0), step=5000.0, key="sim_curr_in")
        sim_target_val = st.number_input("Target Capitale Finale (€)", min_value=1000.0, value=150000.0, step=10000.0, key="sim_target_in")
    with sim_c2:
        sim_pac_val = st.number_input("Apporto Mensile PAC (€)", min_value=0.0, value=600.0, step=50.0, key="sim_pac_in")
        sim_years_val = st.slider("Orizzonte Temporale (Anni)", min_value=1.0, max_value=30.0, value=7.0, step=0.5, key="sim_years_in")
    with sim_c3:
        sim_ret_val = st.slider("Rendimento Annuo Atteso (%)", min_value=2.0, max_value=14.0, value=7.0, step=0.5, key="sim_ret_in")
        sim_vol_val = st.slider("Volatilità Annua (%)", min_value=5.0, max_value=30.0, value=15.0, step=1.0, key="sim_vol_in")
    with sim_c4:
        sim_infl_val = st.slider("Inflazione Annua (%)", min_value=0.0, max_value=8.0, value=2.0, step=0.5, key="sim_infl_in")
        sim_risk_profile = st.selectbox("Profilo Glide Path", ["conservative", "moderate", "aggressive"], index=1, key="sim_risk_prof_in")

    # Esecuzione simulazione Monte Carlo
    mc_goal_res = compute_goal_based_monte_carlo(
        current_amount=sim_curr_val,
        monthly_contribution=sim_pac_val,
        target_amount=sim_target_val,
        years=sim_years_val,
        mean_annual_return=sim_ret_val / 100.0,
        annual_volatility=sim_vol_val / 100.0,
        inflation_rate=sim_infl_val / 100.0,
        n_simulations=5000
    )

    # Indicatori di sintesi
    spi = mc_goal_res["spi_pct"]
    spi_color = "#10b981" if spi >= 85.0 else ("#f59e0b" if spi >= 65.0 else "#ef4444")
    
    st.write("")
    mc_k1, mc_k2, mc_k3, mc_k4 = st.columns(4)
    with mc_k1:
        metric_card("Success Probability Index (SPI)", f"{spi:.1f}%", delta=mc_goal_res["status_verdict"], delta_color="normal")
    with mc_k2:
        metric_card("Capitale Mediano Stimato (P50)", fmt_eur(mc_goal_res["p50_median_final"]), delta=f"Base Risparmio: {fmt_eur(mc_goal_res['deterministic_capital'])}", delta_color="normal")
    with mc_k3:
        metric_card("Worst-Case 5° Percentile (P5)", fmt_eur(mc_goal_res["p5_final"]), delta=f"Best-Case P95: {fmt_eur(mc_goal_res['p95_final'])}", delta_color="normal")
    with mc_k4:
        rec_pac = mc_goal_res["recommended_monthly_contribution"]
        metric_card("PAC Raccomandato (SPI ≥ 85%)", fmt_eur(rec_pac) + "/mese", delta="Ottimale con buffer" if rec_pac > sim_pac_val else "Target Raggiunto", delta_color="normal")

    # Grafico a ventaglio (Fan Chart Plotly)
    df_tl = mc_goal_res["timeline_df"]
    fig_fan = go.Figure()

    # Fascia P5 - P95 (90% Confidenza)
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["p95"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
    ))
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["p5"],
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(99, 102, 241, 0.12)", name="Intervallo P5–P95 (90% Confidenza)"
    ))

    # Fascia P25 - P75 (50% Confidenza centrale)
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["p75"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
    ))
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["p25"],
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(99, 102, 241, 0.25)", name="Intervallo Centrale P25–P75"
    ))

    # Mediana P50
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["p50"],
        mode="lines+markers", line=dict(color="#818cf8", width=3),
        marker=dict(size=4), name="Traiettoria Mediana (P50)"
    ))

    # Risparmio Deterministico
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["deterministic_savings"],
        mode="lines", line=dict(color="#64748b", width=1.5, dash="dot"),
        name="Capitale Versato (Senza Rendimento)"
    ))

    # Linea Target Orizzontale
    fig_fan.add_trace(go.Scatter(
        x=df_tl["year"], y=df_tl["target"],
        mode="lines", line=dict(color="#10b981" if spi >= 85 else "#ef4444", width=2, dash="dash"),
        name=f"Capitale Obiettivo ({fmt_eur(sim_target_val)})"
    ))

    fig_fan.update_layout(
        title="Ventaglio delle Traiettorie Patrimoniali Stocastiche (Merton Jump-Diffusion Monte Carlo)",
        xaxis_title="Orizzonte Temporale (Anni)",
        yaxis_title="Patrimonio Stimato (€)",
        height=400,
        margin=dict(t=35, l=15, r=15, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_fan, use_container_width=True, config={'displayModeBar': False})

    # Glide Path Curve & Dynamic Allocation Schedule
    st.write("")
    st.markdown("#### 📉 Dynamic Glide Path 3D (Curva di De-risking & Allocazione Temporale)")
    st.caption("Ripartizione automatica progressiva tra Azioni, Obbligazioni e Liquidità/XEON all'avvicinarsi della data dell'evento per garantire probabilità di successo ≥ 85%.")

    from core.wealth.glidepath_engine import DynamicGlidePathEngine, LifeGoal

    goal_obj = LifeGoal(
        goal_id="g_sim",
        name="Traguardo Selezionato",
        target_amount=sim_target_val,
        horizon_years=int(sim_years_val),
        initial_capital=sim_curr_val,
        monthly_contribution=sim_pac_val
    )
    gp_engine_out = DynamicGlidePathEngine.compute_goal_glide_path(goal_obj)

    st.plotly_chart(gp_engine_out["plot_figure"], use_container_width=True, config={'displayModeBar': False})

    with st.expander("📊 Tabella di Asset Allocation Glide Path Anno per Anno", expanded=False):
        st.dataframe(
            gp_engine_out["glide_path_df"],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# TAB 4: SEQUENCE OF RETURNS RISK (SRR) & DECUMULATION CRASH TEST
# ============================================================
with tab_srr:
    st.markdown("### 🔮 Sequence of Returns Risk (SRR) & Stress Test di Decumulo")
    st.caption("Simulazione avanzata dell'impatto di un Bear Market concentrato nei primi 3 anni di pensionamento/FIRE vs rendimenti stabili, e dimensionamento del Glide Cash Buffer per prevenire liquidazioni forzate.")
    st.write("")

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        srr_init_w = st.number_input("Capitale a Inizio Decumulo (€)", value=float(nw_summary.total_net_worth if nw_summary.total_net_worth > 50000 else 1000000.0), step=50000.0, format="%.2f")
    with sc2:
        srr_wd = st.number_input("Prelievo Annuo Desiderato (€)", value=float(nw_summary.monthly_burn_rate * 12.0 if nw_summary.monthly_burn_rate > 0 else 40000.0), step=5000.0, format="%.2f")
    with sc3:
        srr_shock = st.slider("Shock Anno 1-3 (Early Crash %)", min_value=-45.0, max_value=-10.0, value=-25.0, step=5.0)
    with sc4:
        srr_buf_yrs = st.slider("Cuscinetto Cash Buffer (Anni di Spese)", min_value=1.0, max_value=5.0, value=2.5, step=0.5)

    srr_res = compute_sequence_of_returns_risk_engine(
        initial_wealth=srr_init_w,
        annual_withdrawal=srr_wd,
        early_shock_pct=srr_shock,
        cash_buffer_years=srr_buf_yrs,
        max_years=30
    )

    sk1, sk2, sk3, sk4 = st.columns(4)
    with sk1:
        metric_card("Initial SWR", f"{srr_res['initial_swr_pct']:.2f}%", delta=srr_res["swr_safety_level"], delta_color="normal" if "Conservativo" in srr_res["swr_safety_level"] else "inverse")
    with sk2:
        metric_card("Cash Buffer Consigliato", fmt_eur(srr_res["cash_buffer_recommended_eur"]), delta=f"{srr_buf_yrs:.1f} Anni Spese Protette", delta_color="normal")
    with sk3:
        ruin_status = f"🔴 Rovina Anno {srr_res['early_crash_result']['ruin_year']}" if srr_res['early_crash_result']['is_ruined'] else "🟢 Nessuna Rovina"
        metric_card("Early Crash Sproteggi", fmt_eur(srr_res["early_crash_result"]["final_wealth"]), delta=ruin_status, delta_color="inverse" if srr_res['early_crash_result']['is_ruined'] else "normal")
    with sk4:
        metric_card("Early Crash + Buffer", fmt_eur(srr_res["early_crash_with_buffer_result"]["final_wealth"]), delta="🟢 Capitale Protetto", delta_color="normal")

    st.write("")
    
    # Grafico Traiettorie SRR a 30 anni
    df_srr_traj = srr_res["trajectory_df"]
    fig_srr = go.Figure()
    fig_srr.add_trace(go.Scatter(
        x=df_srr_traj["Anno"],
        y=df_srr_traj["Early Crash (-25% Y1-Y3)"],
        mode="lines",
        name="1. Early Bear Market (Senza Buffer)",
        line=dict(color="#ef4444", width=3, dash="dot")
    ))
    fig_srr.add_trace(go.Scatter(
        x=df_srr_traj["Anno"],
        y=df_srr_traj["Rendimento Costante (+6%)"],
        mode="lines",
        name="2. Rendimento Costante (+6%/a)",
        line=dict(color="#3b82f6", width=2)
    ))
    fig_srr.add_trace(go.Scatter(
        x=df_srr_traj["Anno"],
        y=df_srr_traj["Late Crash (-25% Y11)"],
        mode="lines",
        name="3. Late Bear Market (Crash ad Anno 11)",
        line=dict(color="#8b5cf6", width=2)
    ))
    fig_srr.add_trace(go.Scatter(
        x=df_srr_traj["Anno"],
        y=df_srr_traj["Early Crash + Buffer Protettivo"],
        mode="lines",
        name="4. Early Crash CON Glide Buffer",
        line=dict(color="#10b981", width=3.5)
    ))
    fig_srr.update_layout(
        title="Traiettoria del Capitale a 30 Anni sotto Diversi Regimi di Sequenza Rendimenti",
        xaxis_title="Anno di Decumulo / Pensionamento",
        yaxis_title="Patrimonio Residuo (€)",
        height=380,
        margin=dict(t=35, l=15, r=15, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    apply_plotly_theme(fig_srr)
    st.plotly_chart(fig_srr, use_container_width=True, config={'displayModeBar': False})

    st.markdown("##### 💡 Analisi Chiave del Sequence of Returns Risk")
    for takeaway in srr_res["key_takeaways"]:
        st.info(f"📌 {takeaway}")


# ============================================================
# TAB 5: COSTI NASCOSTI, TER LOOKTHROUGH & FEE DRAG (TCO)
# ============================================================
with tab_tco:
    st.markdown("### 💸 Total Cost of Ownership (TCO) & Analisi del Fee Drag")
    st.caption("Misurazione dell'impatto cumulativo dei costi di gestione degli strumenti (TER fondi/ETF) e quantificazione dell'erosione da commissioni su orizzonti decennali.")
    st.write("")

    # Calcolo TCO sul portafoglio reale
    tco_res = compute_portfolio_tco_and_fee_drag(
        initial_wealth=nw_summary.financial_investments if nw_summary.financial_investments > 0 else 100000.0,
        monthly_contribution=cf_analytics.get("savings_amount_eur", 500.0) if cf_analytics else 500.0,
        holding_years=[5, 10, 20, 30]
    )

    tco_c1, tco_c2, tco_c3, tco_c4 = st.columns(4)
    with tco_c1:
        metric_card("TER Medio Ponderato", f"{tco_res['weighted_average_ter_pct']:.2f}%", delta="Costi Gestione Strumenti", delta_color="normal")
    with tco_c2:
        metric_card("Costo Annuo Immediato", fmt_eur(tco_res["current_annual_cost_eur"]), delta="Fee annuale stimata", delta_color="normal")
    with tco_c3:
        metric_card("Capitale Eroso a 10 Anni", fmt_eur(tco_res["drag_10y_eur"]), delta="Fee Drag Composto", delta_color="inverse")
    with tco_c4:
        metric_card("Capitale Eroso a 30 Anni", fmt_eur(tco_res["drag_30y_eur"]), delta="Erosione di Lungo Periodo", delta_color="inverse")

    st.write("")
    
    # Grafico di confronto FV tra Zero Fee, Benchmark Low Cost e Portafoglio Reale
    df_comp_tco = tco_res["comparison_table"]
    
    fig_tco = go.Figure()
    fig_tco.add_trace(go.Bar(
        x=[f"{y} Anni" for y in df_comp_tco["years"]],
        y=df_comp_tco["fv_zero_fees"],
        name="Lordo Teorico (0.00% Fee)",
        marker_color="#10b981"
    ))
    fig_tco.add_trace(go.Bar(
        x=[f"{y} Anni" for y in df_comp_tco["years"]],
        y=df_comp_tco["fv_low_cost_bench"],
        name="Benchmark Low-Cost ETF (0.15% TER)",
        marker_color="#38bdf8"
    ))
    fig_tco.add_trace(go.Bar(
        x=[f"{y} Anni" for y in df_comp_tco["years"]],
        y=df_comp_tco["fv_current_portfolio"],
        name=f"Portafoglio Reale ({tco_res['weighted_average_ter_pct']:.2f}% TER)",
        marker_color="#f59e0b"
    ))

    fig_tco.update_layout(
        barmode="group",
        title="Confronto Capitale Finale Reale vs Benchmark per Orizzonte Temporale",
        yaxis_title="Valore Finale Composto (€)",
        height=340,
        margin=dict(t=35, l=15, r=15, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_tco, use_container_width=True, config={'displayModeBar': False})

    # Tabella analitica
    st.markdown("##### 📊 Dettaglio Numerico dell'Erosione da Fee Drag")
    st.dataframe(
        df_comp_tco.rename(columns={
            "years": "Orizzonte (Anni)",
            "fv_zero_fees": "Capitale a Zero Fee (€)",
            "fv_low_cost_bench": "Benchmark ETF 0.15% (€)",
            "fv_current_portfolio": "Portafoglio Attuale (€)",
            "fee_drag_total_eur": "Fee Drag Totale (€)",
            "fee_drag_pct_of_capital": "Erosione Capitale (%)",
            "excess_fee_vs_etf_eur": "Extra-Costo vs ETF (€)"
        }),
        use_container_width=True,
        hide_index=True
    )
