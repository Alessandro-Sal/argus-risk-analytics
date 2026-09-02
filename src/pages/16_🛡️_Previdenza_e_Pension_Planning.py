# ============================================================
# src/pages/16_🛡️_Previdenza_e_Pension_Planning.py
# ARGUS Wealth Management — Pension Planning & Tax Optimization
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import importlib
import core.ui_utils
importlib.reload(core.ui_utils)

from core.fetcher import get_engine
from core.ui_utils import (

    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    apply_plotly_theme
)
from core.sidebar import render_sidebar
from core.wealth import (
    get_pension_plans,
    save_pension_plan,
    simulate_pension_projection,
    get_wealth_portfolios,
    compute_consolidated_net_worth
)


st.set_page_config(page_title="Previdenza & Pensione | ARGUS Wealth", page_icon="🛡️", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "investment_risk_bi")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    st.title("🛡️ ARGUS Wealth — Previdenza & Pensione")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per visualizzare i fondi pensione, lo scudo fiscale e le proiezioni Monte Carlo.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="pension_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p16")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

from core.wealth.wealth_modals import render_goal_methodology_modal

if len(prof_map) > 1:
    head_c1, head_c2, head_c3 = st.columns([3.5, 1.3, 1.2])
    with head_c1:
        st.title("🛡️ ARGUS Wealth — Previdenza & Pensione")
        st.caption("Ottimizzazione fiscale art. 51 TUIR (€ 5.164,57), simulazione Monte Carlo e montante pensionistico.")
    with head_c2:
        st.write("")
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="pension_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()
    with head_c3:
        st.write("")
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("ℹ️ Guida Previdenza", key="btn_modal_pension_p16", use_container_width=True):
            render_goal_methodology_modal()
else:
    head_c1, head_c2 = st.columns([4.2, 0.8])
    with head_c1:
        st.title("🛡️ ARGUS Wealth — Previdenza & Pensione")
        st.caption("Ottimizzazione fiscale art. 51 TUIR (€ 5.164,57), simulazione Monte Carlo e montante pensionistico.")
    with head_c2:
        st.write("")
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("ℹ️ Guida Previdenza", key="btn_modal_pension_p16", use_container_width=True):
            render_goal_methodology_modal()

df_plans = get_pension_plans(engine, portfolio_id=current_pid)



# Calcoli aggregati
tot_pension_val = float(df_plans["accumulated_value"].sum()) if not df_plans.empty else 0.0
tot_monthly_contrib = float((df_plans["monthly_employee_contrib"] + df_plans["monthly_employer_contrib"]).sum()) if not df_plans.empty else 0.0
annual_deductible = float(df_plans["tax_deductible_annual"].sum()) if not df_plans.empty else (tot_monthly_contrib * 12.0)
MAX_TAX_DEDUCTION = 5164.57
tax_shield_used_pct = min(100.0, (annual_deductible / MAX_TAX_DEDUCTION) * 100.0)

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Montante Accumulato", fmt_eur(tot_pension_val), delta="Valore Attuale Fondi", delta_color="normal")
with c2:
    metric_card("Versamento Mensile Totale", fmt_eur(tot_monthly_contrib), delta="Lavoratore + Datore", delta_color="normal")
with c3:
    metric_card("Deducibilità Utilizzata", f"{tax_shield_used_pct:.1f}%", delta=f"{fmt_eur(annual_deductible)} / {fmt_eur(MAX_TAX_DEDUCTION)}", delta_color="normal")
with c4:
    tax_savings = annual_deductible * 0.43 # Aliquota marginale IRPEF stimata 43%
    metric_card("Risparmio Fiscale IRPEF", fmt_eur(tax_savings), delta="All'anno (Aliq. 43%)", delta_color="normal")

st.divider()

# ── SEZIONE 1: PIANI PENSIONISTICI ATTIVI & OTTIMIZZAZIONE FISCALE ───
section("📋 Piani Pensionistici Attivi & Scudo Fiscale (Art. 51 TUIR)")

type_map = {
    "fondo_pensione_aperto": "Fondo Pensione Aperto (FPA)",
    "fondo_negoziale_chiuso": "Fondo Negoziale di Categoria",
    "pip_individuale": "PIP (Piano Individuale Pensionistico)",
    "tfr_in_azienda": "TFR Accantonato in Azienda",
    "gestione_separata": "Gestione Separata Assicurativa"
}

if not df_plans.empty:
    for _, p in df_plans.iterrows():
        p_name = p.get("plan_name", "Fondo Pensione Integrativo")
        provider = p.get("provider", "GSheets")
        p_type_code = p.get("plan_type", "fondo_pensione_aperto")
        p_type_label = type_map.get(p_type_code, p_type_code.replace("_", " ").title())
        inv_line = p.get("investment_line", "Azionario / Crescita")
        
        acc_val = float(p.get("accumulated_value", 0.0) or 0.0)
        m_emp = float(p.get("monthly_employee_contrib", 0.0) or 0.0)
        m_comp = float(p.get("monthly_employer_contrib", 0.0) or 0.0)
        m_tot = m_emp + m_comp
        annual_ded = float(p.get("tax_deductible_annual", 0.0) or (m_tot * 12.0))
        rem_cap = max(0.0, MAX_TAX_DEDUCTION - annual_ded)
        tax_pot_saving = rem_cap * 0.43

        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #3b82f6; border-radius:10px; padding:18px 22px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
                <div>
                    <div style="font-size:18px; font-weight:700; color:#ffffff; margin-bottom:4px;">🛡️ {p_name}</div>
                    <div style="display:flex; flex-wrap:wrap; gap:6px;">
                        <span style="background:rgba(59,130,246,0.15); border:1px solid rgba(59,130,246,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#60a5fa;">🏛️ {provider}</span>
                        <span style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:3px 8px; border-radius:4px; font-size:11px; color:#c9d1d9;">📜 {p_type_label}</span>
                        <span style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#34d399;">📈 {inv_line}</span>
                    </div>
                </div>
                <div style="display:flex; gap:20px; align-items:center;">
                    <div style="text-align:right;">
                        <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Montante Accumulato</div>
                        <div style="font-size:20px; font-weight:700; color:#ffffff;">{fmt_eur(acc_val)}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Versamento Mensile</div>
                        <div style="font-size:20px; font-weight:700; color:#38bdf8;">{fmt_eur(m_tot)}<span style="font-size:12px; color:#8b949e;">/m</span></div>
                    </div>
                </div>
            </div>
            <div style="background:rgba(0,0,0,0.25); border-radius:8px; padding:12px 16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:12px; color:#c9d1d9; font-weight:600;">Deducibilità IRPEF Utilizzata nel 2026: <b style="color:#ffffff;">{fmt_eur(annual_ded)} / {fmt_eur(MAX_TAX_DEDUCTION)}</b> ({tax_shield_used_pct:.1f}%)</span>
                    <span style="font-size:11.5px; color:#34d399;">Risparmio Fiscale Immediato: <b>{fmt_eur(annual_ded * 0.43)}</b></span>
                </div>
                <div style="background:rgba(255,255,255,0.08); border-radius:4px; height:8px; overflow:hidden; margin-bottom:8px;">
                    <div style="background:#3b82f6; width:{min(100.0, tax_shield_used_pct)}%; height:100%; border-radius:4px;"></div>
                </div>
                <div style="font-size:11.5px; color:#8b949e;">
                    💡 <i>Plafond residuo deducibile: <b style="color:#ffffff;">{fmt_eur(rem_cap)}</b> entro il 31/12. Versando l'intero importo residuo otterresti un ulteriore rimborso IRPEF di <b style="color:#34d399;">{fmt_eur(tax_pot_saving)}</b>.</i>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nessun fondo pensione registrato. Registra il tuo fondo dal modulo sottostante.")

st.divider()

# ── SEZIONE 2: SIMULATORE MONTE CARLO & PROIEZIONE ───────────
section("🎲 Simulatore Monte Carlo Pensione Integrativa")

sc1, sc2, sc3 = st.columns(3)
with sc1:
    years_retire = st.slider("Anni al Pensionamento", min_value=5, max_value=40, value=25)
with sc2:
    exp_ret = st.slider("Rendimento Annuo Atteso (%)", min_value=1.0, max_value=12.0, value=6.0, step=0.5)
with sc3:
    vol_pct = st.slider("Volatilità Annua (%)", min_value=2.0, max_value=20.0, value=10.0, step=1.0)

sim_res = simulate_pension_projection(
    current_pot=max(1000.0, tot_pension_val),
    monthly_contrib=max(100.0, tot_monthly_contrib),
    years_to_retirement=years_retire,
    expected_return_pct=exp_ret,
    volatility_pct=vol_pct
)

# 3 Metric Cards Spaziose a Piena Larghezza (No Troncamenti)
rc1, rc2, rc3 = st.columns(3)
with rc1:
    metric_card(
        "Montante Reale Mediano (Oggi)",
        fmt_eur(sim_res["real_pot_median"]),
        delta=f"Nominale a scadenza: {fmt_eur(sim_res['nominal_pot_median'])}",
        delta_color="normal"
    )
with rc2:
    metric_card(
        "Rendita Mensile Vitalizia Stimata",
        f"{fmt_eur(sim_res['estimated_monthly_annuity_real'])} / mese",
        delta="Al netto dell'inflazione (Coeff. 5.575%)",
        delta_color="normal"
    )
with rc3:
    metric_card(
        "Guadagno da Capitalizzazione",
        fmt_eur(sim_res["estimated_capital_gain"]),
        delta=f"Capitale Versato: {fmt_eur(sim_res['total_contributions'])}",
        delta_color="normal"
    )

# Recupera curve evolutive calcolate dal simulatore deterministico
year_ticks = sim_res["year_ticks"]
p10_curve = sim_res["p10_curve"]
p50_curve = sim_res["p50_curve"]
p90_curve = sim_res["p90_curve"]
contrib_curve = sim_res["contrib_curve"]

section(f"📈 Proiezione Evolutiva Montante Pensionistico nei Prossimi {years_retire} Anni")


fig_cone = go.Figure()

# 1. Limite superiore (90° percentile)
fig_cone.add_trace(go.Scatter(
    x=year_ticks, y=p90_curve,
    mode="lines", line=dict(color="#10b981", width=1.5, dash="dot"),
    name="Scenario Ottimistico (90° %)",
    hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>"
))

# 2. Limite inferiore (10° percentile)
fig_cone.add_trace(go.Scatter(
    x=year_ticks, y=p10_curve,
    mode="lines", line=dict(color="#f59e0b", width=1.5, dash="dot"),
    name="Scenario Conservativo (10° %)",
    hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>"
))

# 3. Mediana (50° percentile) con area cono sfumata
fig_cone.add_trace(go.Scatter(
    x=year_ticks, y=p50_curve,
    mode="lines", line=dict(color="#38bdf8", width=3),
    fill="tonexty", fillcolor="rgba(56, 189, 248, 0.12)",
    name="Scenario Base Mediano (50° %)",
    hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>"
))

# 4. Capitale versato
fig_cone.add_trace(go.Scatter(
    x=year_ticks, y=contrib_curve,
    mode="lines", line=dict(color="#94a3b8", width=2, dash="dash"),
    name="Capitale Versato Cumulativo",
    hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Totale Versato: €%{y:,.2f}<extra></extra>"
))

fig_cone.update_layout(
    xaxis_title="Anni da Oggi",
    yaxis_title="Montante Stimato (€)",
    height=380,
    margin=dict(t=15, l=15, r=15, b=45),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.18,
        xanchor="center",
        x=0.5,
        font=dict(size=11, color="#c9d1d9")
    ),
    font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11)
)
st.plotly_chart(fig_cone, use_container_width=True)

st.divider()



# ── FORM AGGIUNGI PIANO PENSIONISTICO ───────────────────────
with st.expander("➕ Registra Nuovo Fondo Pensione / PIP / TFR"):
    with st.form("form_add_pension"):
        pf1, pf2, pf3 = st.columns(3)
        with pf1:
            p_name = st.text_input("Nome Fondo *", placeholder="es. Fondo Pensione Aperto Amundi SecondaPensione")
            p_prov = st.text_input("Società / Provider *", placeholder="es. Amundi, Allianz, Fonchim, Cometa...")
        with pf2:
            p_type = st.selectbox("Tipologia Fondo *", [
                ("fondo_pensione_aperto", "Fondo Pensione Aperto"),
                ("fondo_negoziale_chiuso", "Fondo Negoziale di Categoria"),
                ("pip_individuale", "PIP (Piano Individuale Pensionistico)"),
                ("tfr_in_azienda", "TFR Accantonato"),
                ("gestione_separata", "Gestione Separata")
            ], format_func=lambda x: x[1])
            p_val = st.number_input("Montante Attuale Accumulato (€) *", min_value=0.0, value=15000.0, step=500.0)
        with pf3:
            p_contr_emp = st.number_input("Versamento Mensile Lavoratore (€)", min_value=0.0, value=300.0, step=50.0)
            p_contr_com = st.number_input("Contributo Datore di Lavoro (€)", min_value=0.0, value=100.0, step=50.0)
            p_line = st.text_input("Linea di Investimento", placeholder="es. 100% Azionario Sviluppo")

        btn_save_p = st.form_submit_button("💾 Salva Fondo Pensione", use_container_width=True)
        if btn_save_p:
            if p_name and p_prov:
                save_pension_plan(engine, {
                    "portfolio_id": current_pid,
                    "plan_name": p_name,
                    "provider": p_prov,
                    "plan_type": p_type[0],
                    "accumulated_value": p_val,
                    "monthly_employee_contrib": p_contr_emp,
                    "monthly_employer_contrib": p_contr_com,
                    "tax_deductible_annual": (p_contr_emp * 12.0),
                    "investment_line": p_line
                })

                st.success(f"Fondo '{p_name}' registrato con successo!")
                st.rerun()
            else:
                st.error("Compila i campi obbligatori (Nome Fondo e Provider).")
