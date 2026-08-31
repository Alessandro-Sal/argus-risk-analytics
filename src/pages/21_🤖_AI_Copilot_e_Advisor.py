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
from core.wealth import (
    get_wealth_portfolios,
    compute_consolidated_net_worth,
    compute_ai_wealth_diagnostics,
    compute_cashflow_analytics,
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
tab_diag, tab_rebal, tab_life, tab_chat = st.tabs([
    "🔍 Diagnostica & Colli di Bottiglia",
    "⚖️ Motore di Ribilanciamento Target",
    "🔮 Life Event & Decision Simulator",
    "💬 Assistente Finanziario Diretto"
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
    st.markdown(f"### ⚖️ Ordini di Ribilanciamento vs **{target_model_sel}**")
    st.caption("Confronto tra pesi effettivi e target di portafoglio con calcolo dei flussi di capitale necessari.")

    c_chart, c_orders = st.columns([1.15, 1.1])
    with c_chart:
        curr_keys = list(ai_diag["current_allocation"].keys())
        curr_vals = list(ai_diag["current_allocation"].values())
        target_map = ai_diag.get("target_allocation", {})
        target_vals = [target_map.get(k, 0.0) for k in curr_keys]
        
        fig_drift = go.Figure(data=[
            go.Bar(
                name="Allocazione Attuale",
                x=curr_keys,
                y=curr_vals,
                marker_color="#38bdf8",
                hovertemplate="<b>%{x}</b><br>Allocazione Attuale: <b>%{y:.1f}%</b><extra></extra>"
            ),
            go.Bar(
                name="Target Modello",
                x=curr_keys,
                y=target_vals,
                marker_color="#34d399",
                hovertemplate="<b>%{x}</b><br>Target Modello: <b>%{y:.1f}%</b><extra></extra>"
            )
        ])
        fig_drift.update_layout(
            barmode="group",
            title=dict(text="Drift tra Asset Allocation Attuale e Target", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=370,
            xaxis_title="",
            yaxis_title="Percentuale (%)",
            margin=dict(l=10, r=10, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_drift, use_container_width=True, config={'displayModeBar': False})

    with c_orders:
        st.markdown("##### 📋 Ordini di Esecuzione Consigliati")
        if ai_diag["rebalance_orders"]:
            for o in ai_diag["rebalance_orders"]:
                is_buy = "ACQUISTA" in o["azione_suggerita"]
                badge_c = "#34d399" if is_buy else "#fbbf24"
                border_c = "rgba(52, 211, 153, 0.25)" if is_buy else "rgba(251, 191, 36, 0.25)"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid {border_c}; border-left: 4px solid {badge_c}; padding: 11px 15px; border-radius: 9px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#ffffff; font-size:13.5px;">{o['asset_class']}</b>
                        <span class="mono-num" style="color:{badge_c}; font-weight:800; font-size:13.5px;">{o['azione_suggerita']} € {o['importo_ribilanciamento']:,.2f}</span>
                    </div>
                    <div style="font-size:11.5px; color:#94a3b8; margin-top:3px;">
                        Attuale: <b style="color:#e2e8f0;">{o['allocazione_attuale']}</b> &rarr; Target: <b style="color:#e2e8f0;">{o['allocazione_target']}</b> (Scostamento: <span style="color:{badge_c};">{o['scostamento']}</span>)
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Portafoglio perfettamente bilanciato rispetto al modello target!")


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
        else:
            st.success(f"🟢 **Sostenibilità Verificata**: Il tuo patrimonio e la riserva liquida ({new_runway} mesi) sono in grado di assorbire l'evento senza compromettere la stabilità finanziaria.")

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
