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
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "wealth")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    st.title("🤖 ARGUS Wealth — AI Copilot & Advisor")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per avviare la diagnostica patrimoniale autonoma e il motore di ribilanciamento.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="ai_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

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
tab_diag, tab_rebal, tab_life, tab_review, tab_chat, tab_voice = st.tabs([
    "🔍 Diagnostica & Colli di Bottiglia",
    "⚖️ Motore di Ribilanciamento Target",
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
    st.markdown("### 💬 Assistente Finanziario & Domande Rapide")
    st.caption("Fai domande istantanee sui tuoi dati reali memorizzati nel database.")

    quick_q = st.selectbox(
        "💡 Domande Frequenti Preimpostate:",
        options=[
            "Seleziona una domanda rapida...",
            "Qual è il mio tasso di risparmio e rispetto la regola 50/30/20?",
            "Quanto capitale posso investire subito senza rischiare la riserva?",
            "Qual è la mia esposizione a mercati volatili (Azioni + Crypto)?",
            "Quanto tempo potrei vivere senza stipendio con la mia liquidità attuale?"
        ]
    )

    if quick_q == "Qual è il mio tasso di risparmio e rispetto la regola 50/30/20?":
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.8); border-left:4px solid #38bdf8; padding:14px 18px; border-radius:8px;">
            <b>Analisi 50/30/20:</b><br>
            Il tuo attuale tasso di risparmio è pari al <b>{nw.savings_rate_pct:.1f}%</b>. La regola raccomanda almeno il 20% destinato a risparmi e investimenti. Con questo ritmo di accumulazione, il tuo patrimonio è in una traiettoria di crescita solida.
        </div>
        """, unsafe_allow_html=True)
    elif quick_q == "Quanto capitale posso investire subito senza rischiare la riserva?":
        safe_cash = nw.monthly_burn_rate * 6.0
        investable = max(0.0, nw.liquid_cash - safe_cash)
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.8); border-left:4px solid #34d399; padding:14px 18px; border-radius:8px;">
            <b>Capitale Investibile in Sicurezza:</b><br>
            La tua riserva minima di sicurezza a 6 mesi ammonta a <b>€ {safe_cash:,.2f}</b>. Avendo una liquidità totale di <b>€ {nw.liquid_cash:,.2f}</b>, puoi investire immediatamente fino a <b>€ {investable:,.2f}</b> senza intaccare il cuscinetto di emergenza.
        </div>
        """, unsafe_allow_html=True)
    elif quick_q == "Qual è la mia esposizione a mercati volatili (Azioni + Crypto)?":
        vol_pct = (nw.financial_investments / (nw.total_net_worth or 1)) * 100.0
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.8); border-left:4px solid #fbbf24; padding:14px 18px; border-radius:8px;">
            <b>Esposizione Volatilità:</b><br>
            I tuoi investimenti finanziari ammontano a <b>€ {nw.financial_investments:,.2f}</b>, rappresentando il <b>{vol_pct:.1f}%</b> del tuo patrimonio netto complessivo.
        </div>
        """, unsafe_allow_html=True)
    elif quick_q == "Quanto tempo potrei vivere senza stipendio con la mia liquidità attuale?":
        st.markdown(f"""
        <div style="background:rgba(15,23,42,0.8); border-left:4px solid #a78bfa; padding:14px 18px; border-radius:8px;">
            <b>Autonomia Finanziaria (Runway):</b><br>
            Con la liquidità attuale nei conti correnti (€ {nw.liquid_cash:,.2f}) e un tasso di spesa mensile di € {nw.monthly_burn_rate:,.2f}, puoi coprire esattamente <b>{nw.runway_months:.1f} mesi</b> di spese a entrate zero.
        </div>
        """, unsafe_allow_html=True)

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
