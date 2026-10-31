# ============================================================
# src/pages/16_🛡️_Previdenza_e_Pension_Planning.py
# ARGUS Wealth Management — Pension Planning, Dynamic Glide Path & Tax Shield
# ============================================================

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.ui_lifecycle import teardown_view_state
from core.ui_utils import (
    apply_plotly_theme,
    ensure_portal_context,
    ensure_portfolio_loaded,
    fmt_eur,
    fmt_pct,
    inject_custom_css,
    metric_card,
    render_institutional_telemetry_ribbon,
    render_omni_command_bar,
    render_segmented_tabs,
    render_sr117_audit_drawer,
    render_standard_hero,
    render_wealth_executive_badges,
    render_wealth_telemetry_ribbon,
    section,
)
from core.wealth import (
    compute_consolidated_net_worth,
    get_pension_plans,
    get_wealth_portfolios,
    init_wealth_db,
    save_pension_plan,
    simulate_pension_projection,
)
from core.wealth.glidepath_engine import DynamicGlidePathEngine, LifeGoal, render_glidepath_chart
from core.wealth.human_capital_engine import HolisticBalanceSheetEngine, HumanCapitalEngine, LaborIncomeProfile
from core.wealth.wealth_modals import render_goal_methodology_modal

st.set_page_config(page_title="Previdenza & Pensione | ARGUS Wealth", page_icon="🛡️", layout="wide")
st.session_state.argus_portal_mode = "🏛️ Wealth Management"
inject_custom_css()
render_sidebar()

ctx = ensure_portal_context(module="wealth")
ensure_portfolio_loaded(module_type="wealth")
engine = ctx["engine"]
current_pid = ctx["portfolio_id"]
prof_title = ctx["profile_name"]
prof_map = ctx["profile_map"]
nw_curr = ctx["net_worth"]

if current_pid is None:
    render_omni_command_bar(portal="wealth", context_name="Nessun Profilo", key_suffix="p16")
    from core.ui_utils import render_wealth_profile_picker

    render_wealth_profile_picker(engine, prof_map, key_prefix="p16_picker")
    st.stop()

# ── ATOMIC STATE TEARDOWN ───────────────────────────────────
teardown_view_state(current_pid, active_page="16_Previdenza_e_Pension_Planning")

render_omni_command_bar(portal="wealth", context_name=prof_title, key_suffix="p16")
render_wealth_telemetry_ribbon(nw_summary=nw_curr, page_badge="PREVIDENZA & PENSION PLANNING", profile_name=prof_title)
render_wealth_executive_badges(nw_curr)

render_standard_hero(
    title="Previdenza & Pensione Integrativa",
    subtitle="Ottimizzazione fiscale art. 51 TUIR (€ 5.164,57), simulazione Monte Carlo, Dynamic Glide Path 3D e Capitale Umano.",
    icon="🛡️",
    profile_map=prof_map,
    current_pid=current_pid,
    dialog_callback=render_goal_methodology_modal,
    dialog_btn_label="ℹ️ Guida Previdenza",
)

df_plans = get_pension_plans(engine, portfolio_id=current_pid)

# Calcoli aggregati
tot_pension_val = float(df_plans["accumulated_value"].sum()) if not df_plans.empty else 0.0
tot_monthly_contrib = (
    float((df_plans["monthly_employee_contrib"] + df_plans["monthly_employer_contrib"]).sum())
    if not df_plans.empty
    else 0.0
)
annual_deductible = (
    float(df_plans["tax_deductible_annual"].sum()) if not df_plans.empty else (tot_monthly_contrib * 12.0)
)
MAX_TAX_DEDUCTION = 5164.57
tax_shield_used_pct = min(100.0, (annual_deductible / MAX_TAX_DEDUCTION) * 100.0)

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Montante Accumulato", fmt_eur(tot_pension_val), delta="Valore Attuale Fondi", delta_color="normal")
with c2:
    metric_card(
        "Versamento Mensile Totale",
        fmt_eur(tot_monthly_contrib),
        delta="Lavoratore + Datore",
        delta_color="normal",
    )
with c3:
    metric_card(
        "Deducibilità Utilizzata",
        f"{tax_shield_used_pct:.1f}%",
        delta=f"{fmt_eur(annual_deductible)} / {fmt_eur(MAX_TAX_DEDUCTION)}",
        delta_color="normal",
    )
with c4:
    tax_savings = annual_deductible * 0.43  # Aliquota marginale IRPEF stimata 43%
    metric_card("Risparmio Fiscale IRPEF", fmt_eur(tax_savings), delta="All'anno (Aliq. 43%)", delta_color="normal")

st.divider()

# ── SELETTORE MODULI PREVIDENZA STILE BLOOMBERG TERMINAL ───────
WEALTH_PENSION_MODELS_CATALOG = {
    "📋 Piani Attivi & Scudo Fiscale": {
        "title": "Piani Pensionistici Attivi & Scudo Fiscale Art. 51 TUIR",
        "badge": "Pillar II & III • Deducibilità €5.164 • Cronistoria",
        "badge_color": "#3b82f6",
        "category": "Previdenza Integrativa",
        "desc": "Monitoraggio dei fondi pensione attivi, calcolo del plafond deducibile residuo (€ 5.164,57 annui) e cronistoria pluriennale dei versamenti con risparmio IRPEF.",
    },
    "🛡️ Deducibilità Post-2007 & Tassazione": {
        "title": "Simulatore Deducibilità Lavoratori Post-2007 & Aliquota 15%->9%",
        "badge": "Art. 8 D.Lgs. 252/05 • Extra Plafond €7.746 • Aliquota 9%",
        "badge_color": "#6366f1",
        "category": "Ottimizzazione Fiscale",
        "desc": "Calcolo del plafond maggiorato per lavoratori di prima occupazione post-2007 (fino a € 7.746,86 annui) e proiezione abbattimento aliquota fiscale finale dal 15% al 9%.",
    },
    "🏢 Comparatore TFR: Azienda vs Fondo & RITA": {
        "title": "Comparatore TFR (In Azienda vs Fondo Pensione) & Requisiti RITA",
        "badge": "TFR • Rivalutazione 1.5%+75% • Contributo Datoriale • RITA",
        "badge_color": "#0ea5e9",
        "category": "Scelte Previdenziali",
        "desc": "Confronto analitico tra mantenimento TFR in azienda (tassazione separata) e conferimento al fondo pensione (contributo datoriale, deduzione e tassazione 9-15%), con simulatore RITA.",
    },
    "📈 Dynamic Glidepath 3D & Life Goals": {
        "title": "Dynamic Glide Path 3D & Target-Date Retirement Allocation",
        "badge": "Curva Sigmoidea • De-risking • Target Date",
        "badge_color": "#10b981",
        "category": "Asset Allocation Dinamica",
        "desc": "Motore stocastico a de-risking temporale sigmoideo di ARGUS per modulare la quota azionaria/obbligazionaria in avvicinamento alla pensione.",
    },
    "👤 Capitale Umano & Total Balance Sheet": {
        "title": "Valutazione Attuariale del Capitale Umano & Total Balance Sheet State",
        "badge": "Human Capital • Sconto Attuariale • Labor Risk",
        "badge_color": "#f59e0b",
        "category": "Patrimonio Olistico",
        "desc": "Modellizzazione dei flussi di reddito da lavoro futuro attualizzati, sensibilità all'inflazione, rischio disoccupazione e VaR patrimoniale complessivo.",
    },
    "🎲 Simulatore Monte Carlo & Cono Evolutivo": {
        "title": "Simulatore Stocastico Monte Carlo & Rendita Vitalizia",
        "badge": "Monte Carlo • Percentili P10/P50/P90 • Annuity",
        "badge_color": "#8b5cf6",
        "category": "Simulazione Attuariale",
        "desc": "Proiezione stocastica del montante pensionistico a scadenza, cono di confidenza (P10, P50, P90), guadagno da capitalizzazione composta e stima della rendita mensile vitalizia.",
    },
    "➕ Censimento & Gestione Fondi": {
        "title": "Registrazione Nuovo Fondo Pensione / PIP / TFR",
        "badge": "Onboarding • PIP • FPA • TFR",
        "badge_color": "#64748b",
        "category": "Anagrafica Piani",
        "desc": "Interfaccia guidata per censire nuovi fondi negoziali di categoria, fondi pensione aperti, piani individuali pensionistici (PIP) o TFR accantonato in azienda.",
    },
}

active_pension_tab = render_segmented_tabs(
    WEALTH_PENSION_MODELS_CATALOG,
    key="wealth_pension_active_tab",
    select_label="Seleziona Modulo Previdenza:",
)

type_map = {
    "fondo_pensione_aperto": "Fondo Pensione Aperto (FPA)",
    "fondo_negoziale_chiuso": "Fondo Negoziale di Categoria",
    "pip_individuale": "PIP (Piano Individuale Pensionistico)",
    "tfr_in_azienda": "TFR Accantonato in Azienda",
    "gestione_separata": "Gestione Separata Assicurativa",
}

# ── 1. PIANI ATTIVI & SCUDO FISCALE ────────────────────────
if active_pension_tab == "📋 Piani Attivi & Scudo Fiscale":
    section("📋 Piani Pensionistici Attivi & Scudo Fiscale (Art. 51 TUIR)")

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

            st.markdown(
                f"""
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
                        <span style="font-size:12px; color:#c9d1d9; font-weight:600;">Deducibilità IRPEF Utilizzata (Esercizio {datetime.now().year}): <b style="color:#ffffff;">{fmt_eur(annual_ded)} / {fmt_eur(MAX_TAX_DEDUCTION)}</b> ({tax_shield_used_pct:.1f}%)</span>
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
            """,
                unsafe_allow_html=True,
            )

            yearly_json = p.get("yearly_data_json")
            if yearly_json:
                try:
                    yd = json.loads(yearly_json) if isinstance(yearly_json, str) else yearly_json
                    hist_rows = []
                    for yr_k, yr_info in sorted(yd.items()):
                        tot_y = yr_info.get("tot_year", 0.0) or 0.0
                        if tot_y > 0 or yr_k in ["2023", "2024", "2025", "2026"]:
                            tot_cum = yr_info.get("tot_cumulato", 0.0) or 0.0
                            tax_ded = min(tot_y, MAX_TAX_DEDUCTION)
                            tax_sav = tax_ded * 0.43
                            plaf_res = max(0.0, MAX_TAX_DEDUCTION - tax_ded)
                            hist_rows.append({
                                "Esercizio": yr_k,
                                "Versamenti Annui (€)": fmt_eur(tot_y),
                                "Cumulato Versato (€)": fmt_eur(tot_cum),
                                "Deducibilità Fiscale (€)": fmt_eur(tax_ded),
                                "Risparmio IRPEF 43% (€)": fmt_eur(tax_sav),
                                "Plafond Residuo (€)": fmt_eur(plaf_res),
                                "_raw_y": tot_y,
                                "_raw_cum": tot_cum,
                                "_year": yr_k,
                            })

                    if hist_rows:
                        st.markdown(
                            f"###### 📊 Cronistoria Versamenti & Ottimizzazione Fiscale ({hist_rows[0]['_year']} - {hist_rows[-1]['_year']})"
                        )
                        df_h = pd.DataFrame(hist_rows)
                        st.dataframe(
                            df_h[[
                                "Esercizio",
                                "Versamenti Annui (€)",
                                "Cumulato Versato (€)",
                                "Deducibilità Fiscale (€)",
                                "Risparmio IRPEF 43% (€)",
                                "Plafond Residuo (€)",
                            ]],
                            use_container_width=True,
                            hide_index=True,
                        )

                        fig_prev = go.Figure()
                        fig_prev.add_trace(
                            go.Bar(
                                x=[r["_year"] for r in hist_rows],
                                y=[r["_raw_y"] for r in hist_rows],
                                name="Versamento Annuo",
                                marker_color="#3b82f6",
                                text=[fmt_eur(r["_raw_y"]) for r in hist_rows],
                                textposition="auto",
                            )
                        )
                        fig_prev.add_trace(
                            go.Scatter(
                                x=[r["_year"] for r in hist_rows],
                                y=[r["_raw_cum"] for r in hist_rows],
                                name="Montante Cumulato",
                                mode="lines+markers+text",
                                line=dict(color="#10b981", width=3),
                                marker=dict(size=8, color="#10b981"),
                                text=[fmt_eur(r["_raw_cum"]) for r in hist_rows],
                                textposition="top center",
                                yaxis="y2",
                            )
                        )
                        fig_prev.update_layout(
                            height=280,
                            margin=dict(l=30, r=30, t=30, b=20),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            yaxis=dict(title="Versamento Annuo (€)"),
                            yaxis2=dict(title="Cumulato (€)", overlaying="y", side="right"),
                        )
                        apply_plotly_theme(fig_prev)
                        st.plotly_chart(fig_prev, use_container_width=True)
                except Exception:
                    pass
    else:
        st.info("Nessun fondo pensione registrato. Registra il tuo fondo dalla scheda '➕ Censimento & Gestione Fondi'.")

# ── 2. DEDUCIBILITÀ POST-2007 & TASSAZIONE FINALE ───────────
elif active_pension_tab == "🛡️ Deducibilità Post-2007 & Tassazione":
    section("🛡️ Deducibilità Fiscale Lavoratori Post-2007 & Curva Fiscale 15% ➔ 9%")

    col_ded1, col_ded2 = st.columns([1.2, 1])
    with col_ded1:
        st.markdown("""
        ##### 📜 Disciplina Fiscale di Favore (Art. 8, comma 6, D.Lgs. 252/2005)
        Per i **lavoratori di prima occupazione successiva al 1° gennaio 2007**:
        - Nei primi **5 anni** di partecipazione alla previdenza complementare, il plafond ordinario è di **€ 5.164,57** annui.
        - Se in tali primi 5 anni non si è saturato l'intero plafond (totale € 25.822,85), la differenza non fruita può essere
          recuperata nei **20 anni successivi**, elevando la deducibilità massima annua fino a **€ 7.746,86** (plafond ordinario € 5.164,57 + extra € 2.582,29).
        """)

        is_post_2007 = st.checkbox("Lavoratore di prima occupazione post-2007", value=True)
        years_in_service = st.slider("Anni di contribuzione effettivi", min_value=1, max_value=40, value=8)
        unclaimed_first_5 = st.number_input(
            "Plafond residuo non dedotto nei primi 5 anni (€)",
            min_value=0.0,
            max_value=25822.85,
            value=8500.0,
            step=500.0,
            disabled=not is_post_2007 or years_in_service < 6,
        )

        taxable_income = st.number_input(
            "Reddito Lordo Annuo Imponibile IRPEF (€)", min_value=15000.0, max_value=300000.0, value=55000.0, step=2500.0
        )

        # Scaglioni IRPEF 2024-2026: 23% fino a 28k, 35% tra 28k e 50k, 43% oltre 50k
        if taxable_income > 50000:
            marginal_irpef = 0.43
        elif taxable_income > 28000:
            marginal_irpef = 0.35
        else:
            marginal_irpef = 0.23

        extra_deductible = min(2582.29, unclaimed_first_5) if (is_post_2007 and years_in_service >= 6) else 0.0
        max_effective_ceiling = MAX_TAX_DEDUCTION + extra_deductible

        st.markdown(
            f"""
        <div style="background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); border-radius:8px; padding:14px; margin-top:12px;">
            <div style="font-size:12px; color:#a5b4fc; text-transform:uppercase; font-weight:700;">Massimale Deducibile Personalizzato ({datetime.now().year})</div>
            <div style="font-size:24px; font-weight:800; color:#ffffff;">{fmt_eur(max_effective_ceiling)}</div>
            <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                Ordinario: <b>{fmt_eur(MAX_TAX_DEDUCTION)}</b> | Extra Post-2007 recuperabile quest'anno: <b style="color:#34d399;">+{fmt_eur(extra_deductible)}</b>
            </div>
            <div style="font-size:12px; color:#38bdf8; margin-top:4px;">
                Aliquota marginale IRPEF applicata: <b>{marginal_irpef * 100:.0f}%</b> ➔ Risparmio d'imposta massimo: <b>{fmt_eur(max_effective_ceiling * marginal_irpef)}</b>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col_ded2:
        st.markdown("##### 📉 Aliquota Agevolata Finale (15% ➔ 9%)")
        st.markdown("""
        All'atto dell'erogazione della prestazione pensionistica (capitale o rendita), la parte imponibile
        è assoggettata a **ritenuta a titolo d'imposta del 15%**, ridotta di **0,30 punti percentuali** per ogni anno
        di partecipazione eccedente il 15°, fino a un'aliquota minima del **9%** (dopo 35 anni).
        """)

        # Calcolo aliquota per anni di partecipazione
        part_years = np.arange(1, 41)
        tax_rates = np.clip(15.0 - np.maximum(0, part_years - 15) * 0.30, 9.0, 15.0)

        current_tax_rate = max(9.0, min(15.0, 15.0 - max(0, years_in_service - 15) * 0.30))

        fig_tax = go.Figure()
        fig_tax.add_trace(
            go.Scatter(
                x=part_years,
                y=tax_rates,
                mode="lines",
                line=dict(color="#6366f1", width=3),
                name="Aliquota d'Imposta (%)",
                hovertemplate="Anni: %{x}<br>Aliquota Finale: %{y:.2f}%<extra></extra>",
            )
        )
        fig_tax.add_trace(
            go.Scatter(
                x=[years_in_service],
                y=[current_tax_rate],
                mode="markers+text",
                marker=dict(size=12, color="#34d399"),
                text=[f"{current_tax_rate:.2f}% ({years_in_service} anni)"],
                textposition="top center",
                name="Posizione Attuale",
            )
        )
        fig_tax.update_layout(
            height=260,
            margin=dict(l=30, r=20, t=20, b=30),
            xaxis_title="Anni di Iscrizione alla Previdenza",
            yaxis_title="Aliquota Finale (%)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        apply_plotly_theme(fig_tax)
        st.plotly_chart(fig_tax, use_container_width=True)

        st.caption(
            f"Con {years_in_service} anni di iscrizione, l'aliquota finale sulla prestazione è del **{current_tax_rate:.2f}%** (rispetto al 26% ordinario delle rendite finanziarie o 43% IRPEF)."
        )

# ── 3. COMPARATORE TFR IN AZIENDA VS FONDO & RITA ──────────
elif active_pension_tab == "🏢 Comparatore TFR: Azienda vs Fondo & RITA":
    section("🏢 Comparatore TFR (Azienda vs Fondo Pensione) & Requisiti RITA")

    tfr_c1, tfr_c2 = st.columns(2)
    with tfr_c1:
        st.markdown("##### ⚖️ Parametri di Confronto TFR")
        gross_salary = st.number_input(
            "Retribuzione Annua Lorda (RAL €)", min_value=15000.0, max_value=250000.0, value=45000.0, step=2500.0
        )
        inflation_est = st.slider(
            "Inflazione media annua attesa (%)", min_value=1.0, max_value=6.0, value=2.0, step=0.2
        )
        fund_return_est = st.slider(
            "Rendimento medio annuo fondo pensione (%)", min_value=1.0, max_value=10.0, value=5.5, step=0.5
        )
        employer_match_pct = st.slider(
            "Contributo datoriale aggiuntivo CCNL (%)", min_value=1.0, max_value=4.0, value=2.0, step=0.2
        )
        sim_years = st.slider("Orizzonte lavorativo residuo (anni)", min_value=5, max_value=35, value=20)

        # Accantonamento annuo TFR: RAL / 13.5 = ~7.41%
        annual_tfr = gross_salary / 13.5
        employer_annual_euro = gross_salary * (employer_match_pct / 100.0)

        # Rivalutazione TFR in azienda: 1.5% fisso + 75% inflazione
        company_tfr_rate = (1.5 + 0.75 * inflation_est) / 100.0
        fund_rate = fund_return_est / 100.0

        # Proiezione capitale
        pot_company = 0.0
        pot_fund = 0.0
        for _ in range(sim_years):
            pot_company = (pot_company + annual_tfr) * (1.0 + company_tfr_rate)
            pot_fund = (pot_fund + annual_tfr + employer_annual_euro) * (1.0 + fund_rate)

        # Tassazione: TFR azienda a tassazione separata (stima media 27%), fondo pensione al 15% -> 9% (stima 10%)
        net_company = pot_company * (1.0 - 0.27)
        net_fund = pot_fund * (1.0 - 0.10)
        delta_net = net_fund - net_company

    with tfr_c2:
        st.markdown("##### 📊 Verdetto Finanziario & Delta Netto a Scadenza")
        st.markdown(
            f"""
        <div style="display:flex; gap:12px; margin-bottom:12px;">
            <div style="flex:1; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:11px; color:#fca5a5; font-weight:700;">TFR IN AZIENDA (Netto)</div>
                <div style="font-size:20px; font-weight:800; color:#ffffff;">{fmt_eur(net_company)}</div>
                <div style="font-size:10.5px; color:#94a3b8; margin-top:4px;">Tassazione separata IRPEF (~27%)</div>
            </div>
            <div style="flex:1; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:12px; text-align:center;">
                <div style="font-size:11px; color:#86efac; font-weight:700;">FONDO PENSIONE (Netto)</div>
                <div style="font-size:20px; font-weight:800; color:#ffffff;">{fmt_eur(net_fund)}</div>
                <div style="font-size:10.5px; color:#94a3b8; margin-top:4px;">Aliquota agevolata (~10%) + Datoriale</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.success(
            f"🚀 **Vantaggio Fondo Pensione:** +**{fmt_eur(delta_net)}** netti (+{(delta_net / max(1.0, net_company)) * 100:.1f}%), grazie all'effetto moltiplicatore del contributo datoriale ({fmt_eur(employer_annual_euro)}/anno) e alla tassazione agevolata."
        )

        st.divider()
        st.markdown("##### 🕊️ Idoneità R.I.T.A. (Rendita Integrativa Temporanea Anticipata)")
        st.markdown("""
        La **R.I.T.A.** consente di fruire del montante del fondo pensione come ponte previdenziale prima del raggiungimento della pensione di vecchiaia:
        - **Anticipo fino a 5 anni:** Cessazione dell'attività lavorativa, almeno 20 anni di contribuzione INPS e almeno 5 anni nel fondo pensione.
        - **Anticipo fino a 10 anni:** Inoccupati da oltre 24 mesi a seguito di cessazione lavorativa e almeno 5 anni nel fondo.
        - **Regime Fiscale Super-Agevolato:** La R.I.T.A. è tassata con ritenuta a titolo d'imposta dal **15% al 9%** (esente da IRPEF ordinaria).
        """)

# ── 4. DYNAMIC GLIDEPATH 3D & LIFE GOALS ────────────────────
elif active_pension_tab == "📈 Dynamic Glidepath 3D & Life Goals":
    section("📈 Dynamic Glide Path 3D & De-risking Sigmoideo per Traguardi di Vita")

    gl_c1, gl_c2, gl_c3 = st.columns(3)
    with gl_c1:
        target_amt = st.number_input(
            "Obiettivo Capitale a Scadenza (€)", min_value=50000.0, max_value=3000000.0, value=400000.0, step=25000.0
        )
    with gl_c2:
        init_cap = st.number_input(
            "Capitale Iniziale Dedicato (€)",
            min_value=0.0,
            max_value=1000000.0,
            value=float(tot_pension_val) if tot_pension_val > 0 else 25000.0,
            step=5000.0,
        )
    with gl_c3:
        m_contrib = st.number_input(
            "Versamento Mensile (€)",
            min_value=50.0,
            max_value=5000.0,
            value=float(tot_monthly_contrib) if tot_monthly_contrib > 0 else 400.0,
            step=50.0,
        )

    horiz_yrs = st.slider("Orizzonte di Accumulo Residuo (Anni)", min_value=5, max_value=35, value=22)

    goal_obj = LifeGoal(
        goal_id="pension_goal",
        name="Obiettivo Pensione e Decumulo Sereno",
        target_amount=float(target_amt),
        horizon_years=int(horiz_yrs),
        initial_capital=float(init_cap),
        monthly_contribution=float(m_contrib),
        priority="high",
    )

    try:
        glide_res = DynamicGlidePathEngine.compute_goal_glide_path(goal_obj, n_sims=1000)

        gk1, gk2, gk3 = st.columns(3)
        with gk1:
            metric_card(
                "Probabilità di Successo (SPI %)",
                f"{glide_res['success_probability_pct']:.1f}%",
                delta="Simulazione Stocastica 1.000 Scenari",
                delta_color="normal",
            )
        with gk2:
            metric_card(
                "Capitale Atteso Mediano (P50)",
                fmt_eur(glide_res["expected_final_value"]),
                delta=f"Target: {fmt_eur(target_amt)}",
                delta_color="normal",
            )
        with gk3:
            metric_card(
                "Range Scenario (P10 - P90)",
                f"{fmt_eur(glide_res['p10_final_value'])}",
                delta=f"Ottimistico P90: {fmt_eur(glide_res['p90_final_value'])}",
                delta_color="normal",
            )

        st.write("")
        fig_gp = glide_res.get("plot_figure")
        if fig_gp:
            apply_plotly_theme(fig_gp)
            st.plotly_chart(fig_gp, use_container_width=True)
    except Exception as ex_gp:
        st.warning(f"Simulatore Glide Path in elaborazione: {ex_gp}")

# ── 5. CAPITALE UMANO & TOTAL BALANCE SHEET ────────────────
elif active_pension_tab == "👤 Capitale Umano & Total Balance Sheet":
    section("👤 Valutazione Attuariale del Capitale Umano (Human Capital Asset)")

    st.markdown("""
    Nei moderni modelli di **Total Wealth Management (CFA Institute & Ibbotson-Chen)**, la ricchezza complessiva di un individuo
    è data dalla somma di **Capitale Finanziario** (Asset liquidi + Immobili) e **Capitale Umano** (Valore attuale scontato dei redditi da lavoro futuri):
    $$\\text{Total Wealth} = \\text{Financial Capital} + \\text{Human Capital}$$
    """)

    hc_c1, hc_c2 = st.columns([1.2, 1])
    with hc_c1:
        net_inc = st.number_input(
            "Reddito Netto da Lavoro Annuo (€)", min_value=15000.0, max_value=250000.0, value=42000.0, step=2500.0
        )
        work_years = st.slider("Anni di lavoro fino al pensionamento", min_value=3, max_value=40, value=25)
        wage_growth = st.slider("Crescita salariale annua reale attesa (%)", min_value=0.0, max_value=5.0, value=1.5, step=0.25)
        sector_opt = st.selectbox(
            "Settore Lavorativo & Ciclicità:",
            [
                ("tech", "Tecnologia / Finanza (Alta ciclicità, Beta 1.3)"),
                ("consulting", "Consulenza / Servizi (Media ciclicità, Beta 1.0)"),
                ("public", "Pubblica Amministrazione / Sanità (Bassa ciclicità, Beta 0.4)"),
                ("manufacturing", "Manifattura / Industria (Beta 0.9)"),
            ],
            format_func=lambda x: x[1],
        )

        sec_beta = 1.3 if sector_opt[0] == "tech" else (0.4 if sector_opt[0] == "public" else 1.0)
        unemp_prem = 0.015 if sector_opt[0] == "public" else 0.035

        profile_hc = LaborIncomeProfile(
            current_annual_net_income=float(net_inc),
            years_to_retirement=int(work_years),
            income_growth_rate=float(wage_growth / 100.0),
            industry_sector=sector_opt[0],
            sector_beta=sec_beta,
            unemployment_risk_premium=unemp_prem,
        )

        hc_engine = HumanCapitalEngine()
        hc_res = hc_engine.compute_human_capital_valuation(profile_hc)

        st.markdown(
            f"""
        <div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:16px; margin-top:12px;">
            <div style="font-size:12px; color:#fbbf24; text-transform:uppercase; font-weight:700;">Valore Attuale Capitale Umano</div>
            <div style="font-size:28px; font-weight:800; color:#ffffff;">{fmt_eur(hc_res.get('human_capital_value_eur', 0.0))}</div>
            <div style="font-size:12px; color:#cbd5e1; margin-top:6px;">
                Tasso di Sconto Attuariale Reale: <b>{hc_res.get('discount_rate_pct', 3.5):.2f}%</b> (Risk-Free + Premio Lavorativo)
            </div>
            <div style="font-size:12px; color:#94a3b8; margin-top:4px;">
                Equivalent Bond Asset: <b>{fmt_eur(hc_res.get('quasi_debt_value_eur', 0.0))}</b> | Quasi-Equity: <b>{fmt_eur(hc_res.get('quasi_equity_value_eur', 0.0))}</b>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with hc_c2:
        st.markdown("##### 🏛️ Scomposizione della Ricchezza Olistica")
        fin_cap = float(nw_curr.get("net_worth", 150000.0) or 150000.0)
        hc_val = float(hc_res.get("human_capital_value_eur", 500000.0))
        tot_wealth = fin_cap + hc_val

        fig_pie = go.Figure(
            go.Pie(
                labels=["Capitale Umano (Redditi Futuri)", "Capitale Finanziario Netto"],
                values=[hc_val, max(1.0, fin_cap)],
                hole=0.45,
                marker=dict(colors=["#f59e0b", "#3b82f6"]),
                textinfo="label+percent",
            )
        )
        fig_pie.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        apply_plotly_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.caption(
            f"Il tuo Capitale Umano rappresenta il **{(hc_val / max(1.0, tot_wealth)) * 100:.1f}%** della tua ricchezza complessiva ({fmt_eur(tot_wealth)}). Con il passare degli anni, il Capitale Umano si converte progressivamente in Capitale Finanziario tramite il risparmio."
        )

# ── 6. SIMULATORE MONTE CARLO & CONO EVOLUTIVO ─────────────
elif active_pension_tab == "🎲 Simulatore Monte Carlo & Cono Evolutivo":
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
        volatility_pct=vol_pct,
    )

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        metric_card(
            "Montante Reale Mediano (Oggi)",
            fmt_eur(sim_res["real_pot_median"]),
            delta=f"Nominale a scadenza: {fmt_eur(sim_res['nominal_pot_median'])}",
            delta_color="normal",
        )
    with rc2:
        metric_card(
            "Rendita Mensile Vitalizia Stimata",
            f"{fmt_eur(sim_res['estimated_monthly_annuity_real'])} / mese",
            delta="Al netto dell'inflazione (Coeff. 5.575%)",
            delta_color="normal",
        )
    with rc3:
        metric_card(
            "Guadagno da Capitalizzazione",
            fmt_eur(sim_res["estimated_capital_gain"]),
            delta=f"Capitale Versato: {fmt_eur(sim_res['total_contributions'])}",
            delta_color="normal",
        )

    year_ticks = sim_res["year_ticks"]
    p10_curve = sim_res["p10_curve"]
    p50_curve = sim_res["p50_curve"]
    p90_curve = sim_res["p90_curve"]
    contrib_curve = sim_res["contrib_curve"]

    st.write("")
    section(f"📈 Proiezione Evolutiva Montante Pensionistico nei Prossimi {years_retire} Anni")

    fig_cone = go.Figure()
    fig_cone.add_trace(
        go.Scatter(
            x=year_ticks,
            y=p90_curve,
            mode="lines",
            line=dict(color="#10b981", width=1.5, dash="dot"),
            name="Scenario Ottimistico (90° %)",
            hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>",
        )
    )
    fig_cone.add_trace(
        go.Scatter(
            x=year_ticks,
            y=p10_curve,
            mode="lines",
            line=dict(color="#f59e0b", width=1.5, dash="dot"),
            name="Scenario Conservativo (10° %)",
            hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>",
        )
    )
    fig_cone.add_trace(
        go.Scatter(
            x=year_ticks,
            y=p50_curve,
            mode="lines",
            line=dict(color="#38bdf8", width=3),
            fill="tonexty",
            fillcolor="rgba(56, 189, 248, 0.12)",
            name="Scenario Base Mediano (50° %)",
            hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Montante: €%{y:,.2f}<extra></extra>",
        )
    )
    fig_cone.add_trace(
        go.Scatter(
            x=year_ticks,
            y=contrib_curve,
            mode="lines",
            line=dict(color="#94a3b8", width=2, dash="dash"),
            name="Capitale Versato Cumulativo",
            hovertemplate="<b>%{fullData.name}</b><br>Anno: %{x}<br>Totale Versato: €%{y:,.2f}<extra></extra>",
        )
    )
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
            font=dict(size=11, color="#c9d1d9"),
        ),
        font=dict(family="Outfit, sans-serif", color="#c9d1d9", size=11),
    )
    st.plotly_chart(fig_cone, use_container_width=True)

# ── 7. CENSIMENTO & GESTIONE FONDI ─────────────────────────
elif active_pension_tab == "➕ Censimento & Gestione Fondi":
    section("➕ Censimento & Registrazione Nuovo Fondo Pensione / PIP / TFR")
    st.caption("Aggiungi o aggiorna i piani previdenziali integrativi associati al profilo patrimoniale attivo.")

    with st.form("form_add_pension"):
        pf1, pf2, pf3 = st.columns(3)
        with pf1:
            p_name = st.text_input("Nome Fondo *", placeholder="es. Fondo Pensione Aperto Amundi SecondaPensione")
            p_prov = st.text_input("Società / Provider *", placeholder="es. Amundi, Allianz, Fonchim, Cometa...")
        with pf2:
            p_type = st.selectbox(
                "Tipologia Fondo *",
                [
                    ("fondo_pensione_aperto", "Fondo Pensione Aperto"),
                    ("fondo_negoziale_chiuso", "Fondo Negoziale di Categoria"),
                    ("pip_individuale", "PIP (Piano Individuale Pensionistico)"),
                    ("tfr_in_azienda", "TFR Accantonato"),
                    ("gestione_separata", "Gestione Separata"),
                ],
                format_func=lambda x: x[1],
            )
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
                    "investment_line": p_line,
                })

                st.success(f"Fondo '{p_name}' registrato con successo!")
                st.rerun()
            else:
                st.error("Compila i campi obbligatori (Nome Fondo e Provider).")

pension_summary = {
    "total_accumulated_value": float(tot_pension_val) if "tot_pension_val" in locals() else 0.0,
    "pension_plans_count": int(len(df_plans)) if ("df_plans" in locals() and not df_plans.empty) else 0,
    "portfolio_id": current_pid if "current_pid" in locals() else None,
}
render_sr117_audit_drawer(engine, model_name="ARGUS Pension Planning & Human Capital Engine", audit_metrics=pension_summary)
