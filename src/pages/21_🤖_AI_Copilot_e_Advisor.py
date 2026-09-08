# ============================================================
# 21_🤖_AI_Copilot_e_Advisor.py
# ARGUS Wealth — AI Wealth Copilot, Diagnostica Intelligente & Ribilanciamento
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
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
from core.fetcher import get_engine
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_ai_wealth_diagnostics,
    compute_cashflow_analytics,
    compute_tax_smart_rebalancing_watchdog,
    compute_ai_quarterly_wealth_review
)
from core.wealth.wealth_db import (
    get_wealth_portfolios,
    get_cashflow_records
)


st.set_page_config(page_title="AI Copilot & Advisor | ARGUS Wealth", page_icon="🤖", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_name = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
offline_mode = bool(st.session_state.get("offline_mode", False))
db_port = int(st.session_state.get("db_port", 3306))

engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    # Auto-resolve to Personale or first available profile
    for pid_candidate, pname in prof_map.items():
        if pname.strip().lower() == "personale":
            current_pid = pid_candidate
            break
    if current_pid is None and prof_map:
        current_pid = list(prof_map.keys())[0]
    st.session_state["wealth_active_portfolio_id"] = current_pid

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p21")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — AI Copilot & Advisor Intelligente",
    subtitle="Diagnostica Patrimoniale Autonoma, Rilevamento Colli di Bottiglia, Ribilanciamento Asset Allocation e Life Event Simulator.",
    icon="🤖"
)

from core.wealth.wealth_modals import render_ai_health_score_modal

col_ai_h1, col_ai_h2 = st.columns([3.5, 1.2])
with col_ai_h1:
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="ai_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()

with col_ai_h2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("ℹ️ Guida Health Score AI", key="btn_modal_ai_p21", use_container_width=True):
        render_ai_health_score_modal()

# Model Selector Toolbar
col_mod1, col_mod2 = st.columns([3, 1])
with col_mod1:
    target_model_sel = st.selectbox(
        "🎯 Modello di Asset Allocation Istituzionale Target:",
        options=[
            "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)",
            "🚀 Aggressive Wealth Growth (80/20)",
            "🛡️ Ray Dalio All-Weather"
        ],
        index=0
    )
with col_mod2:
    st.write("")
    if st.button("🔄 Ricalcola Diagnosi", use_container_width=True):
        st.rerun()

ai_diag = compute_ai_wealth_diagnostics(engine, portfolio_id=current_pid, target_model_name=target_model_sel)
nw = ai_diag["summary"]

# ── TOP KPI ROW ─────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    h_stat = "Ottimale" if ai_diag['health_score'] >= 80 else "Migliorabile"
    h_col = "normal" if ai_diag['health_score'] >= 80 else "inverse"
    metric_card("Health Score AI", f"{ai_diag['health_score']:.0f} / 100", delta=h_stat, delta_color=h_col, help_text="Punteggio olistico di salute patrimoniale basato su liquidità, risparmio, diversificazione e debito.")
with k2:
    nb = len(ai_diag["bottlenecks"])
    metric_card("Colli di Bottiglia", f"{nb} Alert", delta="Attenzioni Attive" if nb > 0 else "Nessuna Criticità", delta_color="inverse" if nb > 0 else "normal", help_text="Anomalie o inefficienze strutturali rilevate dagli algoritmi diagnostici.")
with k3:
    nr = len(ai_diag["rebalance_orders"])
    metric_card("Ordini Ribilancio", f"{nr} Ordini", delta="Allineamento Target", help_text="Numero di interventi quantitativi per allineare il portafoglio al modello target selezionato.")
with k4:
    metric_card("Emergency Runway", f"{nw.runway_months:.1f} Mesi", delta="Copertura Spese", help_text="Mesi di copertura autonoma a stipendio azzerato (Fondo di Emergenza).")


st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab_diag, tab_rebal, tab_council, tab_life, tab_review, tab_chat, tab_voice = st.tabs([
    "🔍 Diagnostica & Colli di Bottiglia",
    "⚖️ Motore di Ribilanciamento Target",
    "🏛️ Tri-Agent Governance & Conic Rebalancer",
    "🔮 Life Event & Decision Simulator",
    "📑 Executive Quarterly Review (NLG)",
    "💬 Assistente Finanziario Diretto",
    "🎙️ AI Voice Briefing & Audio Podcast"
])

with tab_diag:
    st.markdown("### 🔍 Report Diagnostico Autonomo ARGUS")
    st.caption("Il motore AI analizza liquidità, flussi di cassa, scudo fiscale e concentrazione degli asset per identificare inefficienze.")

    if ai_diag["bottlenecks"]:
        for b in ai_diag["bottlenecks"]:
            if b["severita"] == "CRITICA":
                c_border = "#ef4444"
                c_bg = "rgba(239, 68, 68, 0.12)"
                icon = "🚨"
            elif b["severita"] == "ATTENZIONE":
                c_border = "#f59e0b"
                c_bg = "rgba(245, 158, 11, 0.12)"
                icon = "⚠️"
            elif b["severita"] == "OPPORTUNITÀ":
                c_border = "#34d399"
                c_bg = "rgba(16, 185, 129, 0.12)"
                icon = "💡"
            else:
                c_border = "#38bdf8"
                c_bg = "rgba(56, 189, 248, 0.12)"
                icon = "ℹ️"

            st.markdown(f"""
            <div style="background:{c_bg}; border:1px solid {c_border}40; border-left: 5px solid {c_border}; padding: 14px 18px; border-radius: 10px; margin-bottom: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <span style="font-size:14px; font-weight:800; color:#ffffff;">{icon} {b['titolo']}</span>
                    <span style="background:{c_border}30; color:{c_border}; font-size:10px; font-weight:800; padding:2px 8px; border-radius:6px; text-transform:uppercase;">{b['severita']} &bull; {b['categoria']}</span>
                </div>
                <div style="font-size: 12.5px; color: #cbd5e1; line-height: 1.5;">{b['dettaglio']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("🎉 **Nessun collo di bottiglia critico rilevato!** Il tuo profilo patrimoniale rispetta pienamente tutti i parametri di liquidità, risparmio 50/30/20 e diversificazione.")

with tab_rebal:
    st.markdown(f"### ⚖️ Tax-Smart Rebalancing Watchdog & Drift Monitor")
    st.caption("Monitoraggio in tempo reale dello scostamento (drift) dall'Asset Allocation Target con ottimizzazione fiscale vincolante (TUIR Art. 67).")

    watchdog_res = compute_tax_smart_rebalancing_watchdog(engine, portfolio_id=current_pid)

    wb_c1, wb_c2, wb_c3, wb_c4 = st.columns(4)
    with wb_c1:
        metric_card("Indice di Allineamento", f"{watchdog_res['portfolio_health_alignment_pct']:.1f}%", delta="Sintonia con il Target", delta_color="normal")
    with wb_c2:
        metric_card("Drift Critici", f"{watchdog_res['critical_drifts_count']}", delta="Asset con Drift > 4.5%" if watchdog_res['critical_drifts_count'] > 0 else "Nessun Drift Critico", delta_color="inverse" if watchdog_res['critical_drifts_count'] > 0 else "normal")
    with wb_c3:
        metric_card("Turnover Necessario", fmt_eur(watchdog_res['total_turnover_eur']), delta="Capitale da Ribilanciare", delta_color="normal")
    with wb_c4:
        cd_col = "inverse" if watchdog_res['cash_drag_alert'] else "normal"
        cd_txt = f"Eccesso {fmt_eur(watchdog_res['excess_cash_eur'])}" if watchdog_res['cash_drag_alert'] else "Livello Ottimale"
        metric_card("Cash Drag Alert", "⚠️ Rilevato" if watchdog_res['cash_drag_alert'] else "✅ Assente", delta=cd_txt, delta_color=cd_col)

    if watchdog_res['cash_drag_alert']:
        st.warning(f"**Attenzione Cash Drag:** Rilevata liquidità in eccesso per **{fmt_eur(watchdog_res['excess_cash_eur'])}**. L'impatto stimato in mancato rendimento da costo opportunità è di circa **{fmt_eur(watchdog_res['estimated_annual_cash_drag_eur'])} / anno**.")

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    c_chart, c_orders = st.columns([1.15, 1.1])
    with c_chart:
        df_d = watchdog_res["drift_df"]
        if not df_d.empty:
            fig_drift = go.Figure(data=[
                go.Bar(
                    name="Allocazione Attuale (%)",
                    x=df_d["asset_name"],
                    y=df_d["current_weight_pct"],
                    marker_color="#38bdf8",
                    hovertemplate="<b>%{x}</b><br>Attuale: <b>%{y:.1f}%</b><extra></extra>"
                ),
                go.Bar(
                    name="Target Modello (%)",
                    x=df_d["asset_name"],
                    y=df_d["target_weight_pct"],
                    marker_color="#34d399",
                    hovertemplate="<b>%{x}</b><br>Target: <b>%{y:.1f}%</b><extra></extra>"
                )
            ])
            fig_drift.update_layout(
                barmode="group",
                title=dict(text="Drift tra Asset Allocation Attuale e Target", font=dict(size=14, color="#ffffff")),
                height=350,
                xaxis_title="",
                yaxis_title="Percentuale (%)",
                margin=dict(l=10, r=10, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            apply_plotly_theme(fig_drift)
            st.plotly_chart(fig_drift, use_container_width=True, config={'displayModeBar': False})

    with c_orders:
        st.markdown("##### 📋 Piano Ordini con Ottimizzazione Fiscale")
        for d in watchdog_res.get("drift_table", []):
            if d["action_type"] != "HOLD":
                is_buy = d["action_type"] == "BUY"
                b_color = "#34d399" if is_buy else "#f87171"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {b_color}; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#ffffff; font-size:13px;">{d['asset_name']}</b>
                        <span style="color:{b_color}; font-weight:800; font-size:13px;">{d['action_type']} € {abs(d['target_delta_eur']):,.2f}</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:2px;">
                        Attuale: <b>{d['current_weight_pct']:.1f}%</b> &rarr; Target: <b>{d['target_weight_pct']:.1f}%</b> (Drift: <span style="color:{b_color}; font-weight:bold;">{d['drift_pct']:+.1f}%</span>)
                    </div>
                    <div style="font-size:10.5px; color:#cbd5e1; margin-top:4px; font-style:italic;">
                        💡 {d['notes']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        if all(d["action_type"] == "HOLD" for d in watchdog_res.get("drift_table", [])):
            st.success("✅ Portafoglio perfettamente allineato! Nessun ordine di ribilanciamento richiesto.")

with tab_council:
    st.markdown("### 🏛️ Tri-Agent Quantitative Governance Council & Prescriptive Conic Rebalancer")
    st.caption("Comitato di investimento multi-agente autonomo (Tier-1 Institutional standard: BlackRock Aladdin & Bloomberg AIM). Ottimizzazione convessa vincolata su Tracking Error, Minusvalenze e Slippage Almgren-Chriss.")

    from core.prescriptive_rebalancer import (
        PositionLot,
        TaxWalletState,
        RebalanceConstraints,
        PrescriptiveConicRebalancer
    )
    from core.ai_analyst import TriAgentQuantitativeGovernance

    col_cfg1, col_cfg2, col_cfg3 = st.columns([1.2, 1.2, 1.2])
    with col_cfg1:
        st.markdown("##### 💼 Zainetto Fiscale & Tassazione")
        minus_eur = st.number_input(
            "Minusvalenze Pregresse Disponibili (€):",
            min_value=0.0,
            max_value=500000.0,
            value=3200.0,
            step=500.0,
            key="p21_minus_input"
        )
        tax_rate_sel = st.selectbox(
            "Regime Fiscale Ordinario:",
            options=["Italiano TUIR (26% Azioni / 12.5% Titoli di Stato)", "Flat Tax 26%", "Esenzione Istituzionale (0%)"],
            index=0,
            key="p21_tax_sel"
        )
    with col_cfg2:
        st.markdown("##### 💧 Liquidità & Riserva Minima")
        cash_avail_eur = st.number_input(
            "Liquidità Libera Disponibile sul Conto (€):",
            min_value=0.0,
            max_value=1000000.0,
            value=15000.0,
            step=1000.0,
            key="p21_cash_avail"
        )
        min_cash_buf = st.number_input(
            "Buffer di Cassa Indispensabile (€):",
            min_value=500.0,
            max_value=100000.0,
            value=3000.0,
            step=500.0,
            key="p21_min_cash"
        )
    with col_cfg3:
        st.markdown("##### ⚙️ Vincoli di Ribilanciamento")
        max_turnover_lim = st.slider(
            "Limite Massimo di Turnover (%):",
            min_value=10.0,
            max_value=100.0,
            value=45.0,
            step=5.0,
            key="p21_turnover_lim"
        )
        max_asset_w = st.slider(
            "Tetto Massimo Singolo Titolo (%):",
            min_value=10.0,
            max_value=60.0,
            value=35.0,
            step=5.0,
            key="p21_max_w"
        )

    # Posizioni candidate
    sample_lots = []
    res_bundle = st.session_state.get("results", {})
    pos_df = res_bundle.get("positions", pd.DataFrame()) if isinstance(res_bundle, dict) else pd.DataFrame()

    if not pos_df.empty and "ticker" in pos_df.columns and "current_value" in pos_df.columns:
        for _, r in pos_df.iterrows():
            tkr = str(r["ticker"])
            px = float(r.get("price", r.get("current_price", 100.0)))
            val = float(r["current_value"])
            sh = float(r.get("shares", val / max(px, 1.0)))
            pmc_val = float(r.get("pmc", px * 0.92))
            ac = "Bond_Gov" if "BTP" in tkr or "T-BOND" in tkr else "Equity"
            sample_lots.append(PositionLot(
                ticker=tkr,
                shares=sh,
                current_price=px,
                pmc=pmc_val,
                asset_class=ac,
                adv_eur=10_000_000.0,
                bid_ask_spread_bps=4.0
            ))

    if not sample_lots:
        sample_lots = [
            PositionLot(ticker="CSPX.MI", shares=80, current_price=540.0, pmc=460.0, asset_class="Equity", adv_eur=35_000_000.0, bid_ask_spread_bps=3.0),
            PositionLot(ticker="MEUD.PA", shares=250, current_price=175.0, pmc=160.0, asset_class="Equity", adv_eur=20_000_000.0, bid_ask_spread_bps=4.0),
            PositionLot(ticker="BTP-10Y.MI", shares=180, current_price=101.5, pmc=98.0, asset_class="Bond_Gov", adv_eur=50_000_000.0, bid_ask_spread_bps=2.5),
            PositionLot(ticker="EMIM.AS", shares=350, current_price=32.0, pmc=34.5, asset_class="Equity", adv_eur=15_000_000.0, bid_ask_spread_bps=5.0),
            PositionLot(ticker="XEON.MI", shares=70, current_price=142.0, pmc=140.0, asset_class="Bond_Corp", adv_eur=12_000_000.0, bid_ask_spread_bps=2.0)
        ]

    target_weights_map = {}
    if "80/20" in target_model_sel:
        target_weights_map = {"CSPX.MI": 0.50, "MEUD.PA": 0.20, "EMIM.AS": 0.10, "BTP-10Y.MI": 0.10, "XEON.MI": 0.05}
    elif "All-Weather" in target_model_sel:
        target_weights_map = {"CSPX.MI": 0.30, "MEUD.PA": 0.10, "BTP-10Y.MI": 0.40, "XEON.MI": 0.10, "EMIM.AS": 0.05}
    else:
        target_weights_map = {"CSPX.MI": 0.35, "MEUD.PA": 0.15, "EMIM.AS": 0.10, "BTP-10Y.MI": 0.25, "XEON.MI": 0.10}

    for p in sample_lots:
        if p.ticker not in target_weights_map:
            target_weights_map[p.ticker] = 1.0 / len(sample_lots)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    btn_exec_council = st.button("🚀 Esegui Ribilanciamento Prescrittivo Conico & Convocazione Tri-Agente", type="primary", use_container_width=True, key="btn_run_triagent_rebal")

    if btn_exec_council or "triagent_last_results" in st.session_state:
        if btn_exec_council:
            tax_w = TaxWalletState(minusvalenze_available_eur=float(minus_eur))
            rebal_eng = PrescriptiveConicRebalancer(tax_wallet=tax_w)
            cons_obj = RebalanceConstraints(
                min_cash_buffer_eur=float(min_cash_buf),
                max_turnover_pct=float(max_turnover_lim),
                max_single_weight=float(max_asset_w) / 100.0
            )

            reb_res = rebal_eng.optimize_rebalance(
                positions=sample_lots,
                target_weights=target_weights_map,
                available_cash_eur=float(cash_avail_eur),
                constraints=cons_obj
            )

            council = TriAgentQuantitativeGovernance()
            gov_audit = council.audit_rebalance_plan(
                portfolio_context={"portfolio_value_eur": reb_res["total_wealth_eur"]},
                rebalance_results=reb_res
            )

            st.session_state["triagent_last_results"] = {
                "reb_res": reb_res,
                "gov_audit": gov_audit
            }

        cached = st.session_state.get("triagent_last_results")
        if cached:
            reb_res = cached["reb_res"]
            gov_audit = cached["gov_audit"]

            st.divider()

            v_badge = gov_audit["consensus_badge"]
            v_score = gov_audit["consensus_score"]
            bg_col = "rgba(63, 185, 80, 0.15)" if "APPROVATO ALL'UNANIMITÀ" in v_badge else ("rgba(245, 158, 11, 0.15)" if "CONDIZIONATA" in v_badge else "rgba(239, 68, 68, 0.15)")
            border_col = "#3fb950" if "APPROVATO ALL'UNANIMITÀ" in v_badge else ("#f59e0b" if "CONDIZIONATA" in v_badge else "#ef4444")

            st.markdown(f"""
            <div style="background: {bg_col}; border: 1px solid {border_col}66; border-left: 6px solid {border_col}; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <div style="font-size: 18px; font-weight: 800; color: #ffffff;">{v_badge}</div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-top: 4px;">Deliberazione collegiale del Comitato di Quantitative Governance MiFID II</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 26px; font-weight: 900; color: {border_col};">{v_score:.1f}</span>
                        <span style="font-size: 14px; color: #94a3b8;">/ 100</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            ag_c1, ag_c2, ag_c3 = st.columns(3)
            with ag_c1:
                ra = gov_audit["agents"]["risk_auditor"]
                ra_col = "#3fb950" if ra["verdict"] == "APPROVED" else "#f59e0b"
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(255,255,255,0.08); border-top: 4px solid {ra_col}; border-radius: 8px; padding: 12px 16px; height: 100%;">
                    <b style="color: #38bdf8; font-size: 14px;">🛡️ {ra['name']}</b>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: {ra_col}; background: {ra_col}22; padding: 2px 8px; border-radius: 6px;">{ra['verdict']}</span>
                        <span style="font-size: 12px; font-weight: 700; color: #ffffff;">Score: {ra['score']:.0f}/100</span>
                    </div>
                    <div style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                        {'<br>'.join(['• ' + f for f in ra['findings']])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with ag_c2:
                ta = gov_audit["agents"]["tax_specialist"]
                ta_col = "#3fb950" if ta["verdict"] == "APPROVED" else "#f59e0b"
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(255,255,255,0.08); border-top: 4px solid {ta_col}; border-radius: 8px; padding: 12px 16px; height: 100%;">
                    <b style="color: #a855f7; font-size: 14px;">💼 {ta['name']}</b>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: {ta_col}; background: {ta_col}22; padding: 2px 8px; border-radius: 6px;">{ta['verdict']}</span>
                        <span style="font-size: 12px; font-weight: 700; color: #ffffff;">Score: {ta['score']:.0f}/100</span>
                    </div>
                    <div style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                        {'<br>'.join(['• ' + f for f in ta['findings']])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with ag_c3:
                ma = gov_audit["agents"]["macro_execution"]
                ma_col = "#3fb950" if ma["verdict"] == "APPROVED" else "#f59e0b"
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.9); border: 1px solid rgba(255,255,255,0.08); border-top: 4px solid {ma_col}; border-radius: 8px; padding: 12px 16px; height: 100%;">
                    <b style="color: #34d399; font-size: 14px;">⚡ {ma['name']}</b>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: {ma_col}; background: {ma_col}22; padding: 2px 8px; border-radius: 6px;">{ma['verdict']}</span>
                        <span style="font-size: 12px; font-weight: 700; color: #ffffff;">Score: {ma['score']:.0f}/100</span>
                    </div>
                    <div style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                        {'<br>'.join(['• ' + f for f in ma['findings']])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            st.markdown("##### 📊 Metriche Sintetiche del Ribilanciamento")
            rk1, rk2, rk3, rk4, rk5 = st.columns(5)
            with rk1:
                metric_card("Turnover Ottimizzato", f"{reb_res['turnover_pct']:.1f}%", delta="Inerzia Preservata", delta_color="normal")
            with rk2:
                metric_card("Minus Assorbite", fmt_eur(reb_res['total_minusvalenze_absorbed_eur']), delta="Compensazione Fiscale", delta_color="normal")
            with rk3:
                metric_card("Imposta Capital Gain", fmt_eur(reb_res['total_tax_due_eur']), delta="Tax Drag Effettivo", delta_color="normal" if reb_res['total_tax_due_eur'] == 0 else "inverse")
            with rk4:
                metric_card("Slippage Almgren-Chriss", fmt_eur(reb_res['total_market_impact_slippage_eur']), delta="Impatto di Mercato", delta_color="normal")
            with rk5:
                metric_card("Cassa Residua Stimata", fmt_eur(reb_res['projected_cash_after_eur']), delta="Buffer Liquido Post-Trade", delta_color="normal")

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📋 Blotter Ordini Prescrittivo (Execution Plan)")
            if not reb_res["trades_df"].empty:
                df_tr_disp = reb_res["trades_df"].copy()
                st.dataframe(
                    df_tr_disp[[
                        "cl_ord_id", "ticker", "side", "shares", "market_price",
                        "limit_price", "trade_eur", "minus_absorbed_eur", "tax_bill_eur", "slippage_eur"
                    ]].rename(columns={
                        "cl_ord_id": "Order ID",
                        "ticker": "Ticker",
                        "side": "Verso",
                        "shares": "Quantità",
                        "market_price": "Prezzo Mercato (€)",
                        "limit_price": "Prezzo Limite (€)",
                        "trade_eur": "Controvalore (€)",
                        "minus_absorbed_eur": "Minus Assorbita (€)",
                        "tax_bill_eur": "Imposta (€)",
                        "slippage_eur": "Slippage (€)"
                    }).style.format({
                        "Prezzo Mercato (€)": "€ {:,.2f}",
                        "Prezzo Limite (€)": "€ {:,.2f}",
                        "Controvalore (€)": "€ {:,.2f}",
                        "Minus Assorbita (€)": "€ {:,.2f}",
                        "Imposta (€)": "€ {:,.2f}",
                        "Slippage (€)": "€ {:,.2f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nessuna compravendita necessaria: l'allocazione attuale è ottimale rispetto ai vincoli.")

            with st.expander("📡 Visualizza Flusso Ordini Serializzato FIX Protocol 4.4 (Bloomberg AIM / OMS Ready)"):
                st.code(reb_res["fix_blotter_raw"] or "Nessun ordine FIX generato.", language="text")

            st.download_button(
                label="📥 Esporta Verbale di Deliberazione Esecutiva MiFID II (.MD)",
                data=gov_audit["signoff_memo"],
                file_name=f"ARGUS_Governance_Council_Signoff_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True
            )

with tab_life:
    st.markdown("### 🔮 Life Event & Decision Simulator")
    st.caption("Simula l'impatto di eventi di vita straordinari o decisioni di acquisto sul tuo Patrimonio Netto e sulla sicurezza del Fondo di Emergenza.")

    c_ev1, c_ev2 = st.columns([1.5, 2.5])
    with c_ev1:
        ev_type = st.selectbox(
            "Seleziona Evento di Vita:",
            options=[
                "🚗 Acquisto Auto Nuova",
                "🏡 Anticipo Acquisto Casa",
                "✈️ Anno Sabbatico / Viaggio",
                "💼 Aumento di Stipendio (+15%)",
                "⚡ Spesa Straordinaria Improvvisa"
            ]
        )
        if "Auto" in ev_type:
            ev_cost = st.number_input("Costo Acquisto (€)", value=25000.0, step=1000.0)
            ev_recurring = st.number_input("Spese Manutenzione/Assicurazione Annuali (€)", value=1200.0, step=100.0)
        elif "Casa" in ev_type:
            ev_cost = st.number_input("Anticipo Versato (€)", value=40000.0, step=5000.0)
            ev_recurring = st.number_input("Rata Mutuo Mensile (€)", value=650.0, step=50.0)
        elif "Sabbatico" in ev_type:
            ev_cost = st.number_input("Costo Totale Viaggio (€)", value=15000.0, step=1000.0)
            ev_recurring = 0.0
        elif "Stipendio" in ev_type:
            ev_cost = 0.0
            ev_recurring = -st.number_input("Aumento Entrate Mensili Nette (€)", value=350.0, step=50.0)
        else:
            ev_cost = st.number_input("Importo Spesa Improvvisa (€)", value=8000.0, step=500.0)
            ev_recurring = 0.0

    with c_ev2:
        new_nw = max(0.0, nw.total_net_worth - ev_cost)
        new_liquid = max(0.0, nw.liquid_cash - ev_cost)
        new_burn = nw.monthly_burn_rate + (ev_recurring / 12.0 if "Auto" in ev_type else ev_recurring)
        new_runway = round(new_liquid / new_burn, 1) if new_burn > 0 else 99.0

        st.markdown("##### 📊 Impatto Immediato Post-Evento")
        c_k1, c_k2, c_k3 = st.columns(3)
        with c_k1:
            metric_card("Nuovo Net Worth", fmt_eur(new_nw), delta=fmt_eur(ev_cost), delta_color="inverse" if ev_cost > 0 else "off", help_text="Patrimonio netto ricalcolato tenendo conto dell'uscita immediata.")
        with c_k2:
            l_diff = new_liquid - nw.liquid_cash
            l_col = "inverse" if l_diff < 0 else ("normal" if l_diff > 0 else "off")
            l_delta = fmt_eur(abs(l_diff)) if l_diff != 0 else "Nessuna Variazione"
            metric_card("Nuova Liquidità", fmt_eur(new_liquid), delta=l_delta, delta_color=l_col, help_text="Disponibilità liquide residue dopo il saldo dell'evento.")
        with c_k3:
            r_diff = round(new_runway - nw.runway_months, 1)
            r_col = "normal" if r_diff > 0 else ("inverse" if r_diff < 0 else "off")
            metric_card("Nuovo Runway", f"{new_runway} Mesi", delta=f"{abs(r_diff):.1f} Mesi" if r_diff != 0 else "Invariato", delta_color=r_col, help_text="Nuova autonomia in mesi di copertura delle spese.")



        if new_runway < 6.0:
            st.error(f"⚠️ **Attenzione**: Questa operazione ridurrebbe il tuo Fondo Emergenza a **{new_runway} mesi**, portandolo al di sotto della soglia di sicurezza consigliata (6 mesi).")

    st.divider()
    st.markdown("### 🏛️ Total Balance Sheet Lifetime Solvency & Ruin Simulator (TBS-MC)")
    st.caption("Simulatore stocastico Monte Carlo a ciclo di vita (fino a 90 anni). Mappa l'evoluzione correlata del Portafoglio Liquido, Capitale Umano, Valore Immobiliare e Mutuo per stimare la Probabilità di Rovina e l'Età di Massima Fragilità.")

    from core.wealth.tbs_monte_carlo import TBSLifecycleConfig, TBSMonteCarloEngine

    c_mc1, c_mc2, c_mc3 = st.columns([1.1, 1.1, 1.1])
    with c_mc1:
        st.markdown("##### 👤 Parametri Ciclo di Vita")
        mc_cur_age = st.slider("Età Attuale:", 20, 60, 35, key="p21_mc_age")
        mc_ret_age = st.slider("Età Pensionamento Target:", 55, 75, 67, key="p21_mc_ret")
        mc_term_age = st.slider("Orizzonte di Vita Finale:", 75, 100, 90, key="p21_mc_term")
    with c_mc2:
        st.markdown("##### 💶 Flussi Redditizi & Spese")
        mc_inc = st.number_input("Reddito Netto Annuo (€):", 15000.0, 500000.0, 55000.0, 5000.0, key="p21_mc_inc")
        mc_exp = st.number_input("Spese Annue di Sostentamento (€):", 10000.0, 300000.0, 28000.0, 2000.0, key="p21_mc_exp")
        mc_rep = st.slider("Tasso di Sostituzione Pensione (%):", 40, 90, 70, key="p21_mc_rep") / 100.0
    with c_mc3:
        st.markdown("##### 📈 Rendimenti & Volatilità Reale")
        mc_ret_mean = st.slider("Rendimento Reale Portafoglio (%/anno):", 1.0, 9.0, 4.5, 0.25, key="p21_mc_ret_mean") / 100.0
        mc_vol = st.slider("Volatilità Annua Portafoglio (%):", 5.0, 30.0, 15.0, 1.0, key="p21_mc_vol") / 100.0
        mc_re_apprec = st.slider("Apprezzamento Reale Immobili (%/anno):", 0.0, 4.0, 1.0, 0.25, key="p21_mc_re_apprec") / 100.0

    init_liq = max(10000.0, float(getattr(nw, "liquid_cash", 120000.0) + getattr(nw, "financial_investments", 0.0)))
    init_re = max(0.0, float(getattr(nw, "real_estate_total", 320000.0)))
    init_debt = max(0.0, float(getattr(nw, "total_liabilities", 130000.0)))

    mc_cfg = TBSLifecycleConfig(
        current_age=int(mc_cur_age),
        retirement_age=int(mc_ret_age),
        terminal_age=int(mc_term_age),
        current_annual_net_income=float(mc_inc),
        annual_living_expenses=float(mc_exp),
        pension_replacement_ratio=float(mc_rep),
        initial_liquid_wealth=init_liq,
        liquid_wealth_real_return_mean=float(mc_ret_mean),
        liquid_wealth_volatility=float(mc_vol),
        initial_real_estate_value=init_re,
        real_estate_real_appreciation=float(mc_re_apprec),
        initial_mortgage_debt=init_debt,
        num_simulations=1500
    )

    tbs_mc_eng = TBSMonteCarloEngine(mc_cfg)
    mc_res = tbs_mc_eng.simulate_lifetime_solvency()

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    mk1, mk2, mk3, mk4 = st.columns(4)
    with mk1:
        r_pct = mc_res["total_ruin_probability_pct"]
        r_col = "normal" if r_pct <= 5.0 else ("off" if r_pct <= 15.0 else "inverse")
        metric_card("Probabilità di Rovina a Vita", f"{r_pct:.1f}%", delta="P(Liquidità <= 0€)", delta_color=r_col, help_text="Percentuale di cammini stocastici in cui la liquidità si esaurisce prima dell'età terminale.")
    with mk2:
        metric_card("Età di Massima Fragilità", f"Età: {mc_res['point_of_maximum_fragility_age']} Anni", delta="Picco Vulnerabilità Solvibilità", delta_color="normal")
    with mk3:
        metric_card("Patrimonio Netto Terminale (P50)", fmt_eur(mc_res["median_terminal_net_worth_eur"]), delta=f"Valore a {mc_term_age} anni", delta_color="normal")
    with mk4:
        metric_card("Spesa Sostenibile Raccomandata", fmt_eur(mc_res["recommended_annual_spending_eur"]), delta="Max Tetto Spesa / Anno (95% Conf)", delta_color="normal" if not mc_res["spending_adjustment_needed"] else "inverse")

    if mc_res["spending_adjustment_needed"]:
        st.warning(f"⚠️ **Rischio di Sovraspesa Rilevato:** La probabilità di rovina patrimoniale ({r_pct:.1f}%) supera la soglia di tolleranza prudenziale (5.0%). Si raccomanda di contenere la spesa annuale a **{fmt_eur(mc_res['recommended_annual_spending_eur'])}** (risparmio annuo suggerito: {fmt_eur(mc_res['recommended_spending_cut_eur'])}).")
    else:
        st.success(f"✅ **Piano di Solvibilità Sostenibile:** Il piano di vita presenta un margine di sicurezza eccellente (probabilità di rovina {r_pct:.1f}% &le; 5.0%).")

    df_tl = mc_res["timeline_df"]
    fig_fan = go.Figure()

    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["net_worth_p90"],
        mode='lines',
        line=dict(color='rgba(56, 189, 248, 0.05)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["net_worth_p10"],
        mode='lines',
        line=dict(color='rgba(56, 189, 248, 0.05)'),
        fill='tonexty',
        fillcolor='rgba(56, 189, 248, 0.12)',
        name='Cono 80% (P10 - P90)',
        hoverinfo='skip'
    ))

    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["net_worth_p75"],
        mode='lines',
        line=dict(color='rgba(56, 189, 248, 0.1)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["net_worth_p25"],
        mode='lines',
        line=dict(color='rgba(56, 189, 248, 0.1)'),
        fill='tonexty',
        fillcolor='rgba(56, 189, 248, 0.22)',
        name='Intervallo Interquartile (P25 - P75)',
        hoverinfo='skip'
    ))

    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["net_worth_p50"],
        mode='lines+markers',
        line=dict(color='#38bdf8', width=3),
        marker=dict(size=4),
        name='Patrimonio Netto Mediano (P50)',
        hovertemplate='<b>Età: %{x} anni</b><br>Patrimonio Mediano: € %{y:,.0f}<extra></extra>'
    ))

    fig_fan.add_trace(go.Scatter(
        x=df_tl["age"],
        y=df_tl["liquid_wealth_median"],
        mode='lines',
        line=dict(color='#34d399', width=2, dash='dot'),
        name='Liquidità Mediana Disponibile',
        hovertemplate='<b>Età: %{x} anni</b><br>Liquidità: € %{y:,.0f}<extra></extra>'
    ))

    fig_fan.add_hline(y=0, line_dash="dash", line_color="#ef4444", annotation_text="Soglia Rovina (0€)", annotation_position="bottom right")

    fig_fan.update_layout(
        title="Proiezione Monte Carlo a Ciclo di Vita: Fan Chart del Patrimonio Netto Olistico (€)",
        template="plotly_dark",
        height=420,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Patrimonio Netto Reale (€)", gridcolor="rgba(255,255,255,0.06)", tickprefix="€ "),
        xaxis=dict(title="Età dell'Investitore (Anni)", gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    apply_plotly_theme(fig_fan)
    st.plotly_chart(fig_fan, use_container_width=True)

with tab_review:
    st.markdown("### 📑 AI Executive Quarterly Review (NLG & Client Commentary)")
    st.caption("Genera una relazione esecutiva trimestrale istituzionale in linguaggio naturale, pronta per la consultazione del Family Office o per presentazioni a clienti.")

    col_q1, col_q2 = st.columns([2, 1])
    with col_q1:
        sel_quarter = st.selectbox("Seleziona Trimestre di Riferimento:", ["Q1 2026", "Q4 2025", "Q3 2025", "Q2 2025", "Q1 2025"], index=0)
    with col_q2:
        advisor_title = st.text_input("Firma / Team di Advisory:", value="ARGUS Family Office & Wealth Advisory")

    review_res = compute_ai_quarterly_wealth_review(engine, portfolio_id=current_pid, quarter=sel_quarter, advisor_name=advisor_title)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(review_res["full_markdown"])

    from core.quarterly_report_generator import generate_white_label_quarterly_pdf_report
    pdf_bytes = generate_white_label_quarterly_pdf_report(engine, portfolio_id=current_pid, client_name="Family Office & HNWI Client", quarter=sel_quarter, advisor_firm=advisor_title)

    col_btn_md, col_btn_pdf = st.columns(2)
    with col_btn_md:
        st.download_button(
            label=f"📥 Esporta Relazione {sel_quarter} (Markdown)",
            data=review_res["full_markdown"],
            file_name=f"ARGUS_Executive_Review_{sel_quarter.replace(' ','_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col_btn_pdf:
        st.download_button(
            label=f"📄 Scarica Dossier Stampabile {sel_quarter} (PDF)",
            data=pdf_bytes,
            file_name=f"ARGUS_Client_Report_{sel_quarter.replace(' ','_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )


with tab_chat:
    st.markdown("### 🧠 Neural Wealth Advisor & Conversational Action Memo")
    st.caption("Consulente patrimoniale neurale connesso in tempo reale ai tuoi dati di bilancio. Esegue simulazioni 'What-If' istantanee e redige Action Memo esecutivi.")

    from core.wealth.neural_advisor_engine import NeuralWealthAdvisor

    re_tot_val = float(getattr(nw, "real_estate_total", 0.0))
    liab_tot_val = float(getattr(nw, "total_liabilities", 0.0))
    re_eq_val = max(0.0, re_tot_val - liab_tot_val)

    summary_ai_dict = {
        "total_net_worth": float(getattr(nw, "total_net_worth", 0.0)),
        "liquid_cash": float(getattr(nw, "liquid_cash", 0.0)),
        "financial_investments": float(getattr(nw, "financial_investments", 0.0)),
        "real_estate_total": re_tot_val,
        "real_estate_equity": re_eq_val,
        "physical_assets": float(getattr(nw, "physical_assets", 0.0)),
        "pension_total": float(getattr(nw, "pension_total", 0.0)),
        "total_liabilities": liab_tot_val,
        "wealth_health_score": float(ai_diag.get("health_score", 85.0)),
        "runway_months": float(getattr(nw, "runway_months", 6.0))
    }

    # Query Chips
    col_chip1, col_chip2, col_chip3, col_chip4 = st.columns(4)
    with col_chip1:
        if st.button("⚖️ Ottimizza Zainetto Fiscale", use_container_width=True, key="chip_tax"):
            st.session_state["neural_advisor_query_input"] = "ottimizza zainetto fiscale e minusvalenze"
    with col_chip2:
        if st.button("🏡 Simula Acquisto Immobile", use_container_width=True, key="chip_re"):
            st.session_state["neural_advisor_query_input"] = "simula acquisto immobile con mutuo 80%"
    with col_chip3:
        if st.button("⌚ Estinzione Debito con Caveau", use_container_width=True, key="chip_phys"):
            st.session_state["neural_advisor_query_input"] = "liquidazione orologi caveau per estinzione debito"
    with col_chip4:
        if st.button("🔥 Roadmap Verso il FIRE", use_container_width=True, key="chip_fire"):
            st.session_state["neural_advisor_query_input"] = "pianifica indipendenza finanziaria e rendita FIRE"

    user_query = st.text_input(
        "💬 Chiedi al Neural Advisor o scrivi una simulazione personalizzata:",
        value=st.session_state.get("neural_advisor_query_input", "Qual è lo stato di salute e la resilienza del mio patrimonio?"),
        key="neural_advisor_text_box",
        placeholder="es. Cosa succede se spendo 50.000€ per comprare casa? Oppure: come azzero le minusvalenze?"
    )

    if user_query:
        sim_res = NeuralWealthAdvisor.evaluate_scenario_query(user_query, summary_ai_dict)

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-left: 4px solid #10b981; border-radius: 12px; padding: 16px 20px; margin: 15px 0;">
            <div style="font-size: 15px; font-weight: 800; color: #34d399; margin-bottom: 4px;">
                🎯 {sim_res['title']}
            </div>
            <div style="font-size: 13px; color: #e2e8f0; line-height: 1.6;">
                {sim_res['summary_text']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # KPI Proiettati
        qk1, qk2, qk3 = st.columns(3)
        with qk1:
            delta_nw = sim_res["projected_nw"] - sim_res["pre_shock_nw"]
            metric_card("Net Worth Proiettato", fmt_eur(sim_res["projected_nw"]), delta=f"Delta: {fmt_eur(delta_nw)}", delta_color="normal" if delta_nw >= 0 else "inverse")
        with qk2:
            delta_run = sim_res["projected_runway"] - float(nw.runway_months)
            metric_card("Runway Proiettato", f"{sim_res['projected_runway']:.1f} Mesi", delta=f"Pre: {nw.runway_months:.1f} Mesi", delta_color="normal" if sim_res["projected_runway"] >= 6.0 else "inverse")
        with qk3:
            delta_h = sim_res["projected_health"] - float(ai_diag["health_score"])
            metric_card("Health Score Proiettato", f"{sim_res['projected_health']:.0f} / 100", delta=f"Pre: {ai_diag['health_score']:.0f}/100", delta_color="normal" if delta_h >= 0 else "inverse")

        st.markdown("##### 📌 Metriche & Parametri di Scenario")
        col_m1, col_m2 = st.columns(2)
        m_items = list(sim_res["key_metrics"].items())
        mid_pt = (len(m_items) + 1) // 2
        with col_m1:
            for k, v in m_items[:mid_pt]:
                st.markdown(f"- **{k}:** `{v}`")
        with col_m2:
            for k, v in m_items[mid_pt:]:
                st.markdown(f"- **{k}:** `{v}`")

        st.markdown("##### 📋 Piano d'Azione Consigliato (Sequence of Execution)")
        for act in sim_res["action_plan"]:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-left: 3px solid #38bdf8; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 12.5px; color: #cbd5e1;">
                {act}
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        memo_content = NeuralWealthAdvisor.generate_executive_action_memo(summary_ai_dict, [sim_res], prof_name=prof_title)
        st.download_button(
            label="📥 Scarica Executive Action Memo (.MD)",
            data=memo_content,
            file_name=f"ARGUS_Action_Memo_{prof_title.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True,
            type="primary"
        )

with tab_voice:
    st.markdown("### 🎙️ AI Voice Executive Briefing & Wealth Audio Podcast")
    st.caption("Genera un briefing audio e un copione esecutivo a due voci (Chief Investment Officer & Chief Risk Officer) sincronizzato sui dati reali del patrimonio.")

    from core.voice_advisor_engine import generate_ai_voice_executive_briefing

    vb_res = generate_ai_voice_executive_briefing(engine, portfolio_id=current_pid, client_name=prof_title)

    vk1, vk2, vk3 = st.columns(3)
    with vk1:
        metric_card("Durata Briefing", vb_res["estimated_duration_formatted"], delta=f"{vb_res['word_count']} parole", delta_color="normal")
    with vk2:
        metric_card("Data Aggiornamento", vb_res["as_of_date"], delta="Live Snapshot", delta_color="normal")
    with vk3:
        metric_card("Formato Trasmissione", "Podcast a 2 Voci (CIO & CRO)", delta="Broadcast Ready", delta_color="normal")

    st.write("")
    st.markdown("##### 🎧 Copione Broadcast & Dialogo Esecutivo")

    for dia in vb_res["dialogue_script"]:
        is_cio = "CIO" in dia["speaker"]
        avatar_icon = "👔" if is_cio else "🛡️"
        border_col = "#6366f1" if is_cio else "#38bdf8"
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {border_col}; border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;">
            <b style="color: {border_col}; font-size: 13.5px;">{avatar_icon} {dia['speaker']}:</b><br>
            <span style="font-size: 13px; color: #e2e8f0; line-height: 1.6;">"{dia['text']}"</span>
        </div>
        """, unsafe_allow_html=True)

    st.download_button(
        label="📥 Esporta Copione Audio (Testo per Sintesi TTS / Podcast)",
        data=vb_res["full_text_transcript"],
        file_name=f"ARGUS_Voice_Briefing_{prof_title.replace(' ','_')}.txt",
        mime="text/plain",
        use_container_width=True
    )
