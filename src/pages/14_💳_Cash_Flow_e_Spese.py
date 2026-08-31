# ============================================================
# src/pages/14_💳_Cash_Flow_e_Spese.py
# ARGUS Wealth Management — Cash Flow Intelligence & Budgeting
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
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
    insert_cashflow_tx,
    get_wealth_accounts,
    get_wealth_categories,
    get_wealth_portfolios
)
from core.wealth.wealth_engine import (
    compute_cashflow_analytics,
    compute_consolidated_net_worth,
    compute_recurring_subscriptions_analytics,
    compute_cashflow_forecast_and_anomalies
)


st.set_page_config(page_title="Cash Flow & Spese | ARGUS Wealth", page_icon="💳", layout="wide")
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
    st.title("💳 ARGUS Wealth — Cash Flow & Spese")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per visualizzare le entrate, le uscite e il bilancio mensile.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="cf_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

df_cf = get_cashflow_records(engine, portfolio_id=current_pid)
if not df_cf.empty:
    df_cf["tx_date"] = pd.to_datetime(df_cf["tx_date"])
    available_years = sorted([int(y) for y in df_cf["tx_date"].dt.year.dropna().unique()], reverse=True)

else:
    available_years = [2026]

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p14")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Cash Flow & Spese",
    subtitle="Monitoraggio entrate, uscite, bilancio mensile, diagramma Sankey, Sentinel Abbonamenti e Previsione di Cassa.",
    icon="💳"
)

col_f1, col_f2, col_f3, col_f4 = st.columns([1.3, 0.9, 1.1, 1.1])
with col_f1:
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="cf_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()
    else:
        st.selectbox("Profilo Patrimoniale:", [f"📁 {prof_title}"], disabled=True, key="cf_profile_single")

with col_f2:
    year_opts = ["🌐 Tutto lo Storico"] + [str(y) for y in available_years]
    def_idx = year_opts.index("2026") if "2026" in year_opts else 0
    sel_year_str = st.selectbox("Anno di Analisi:", year_opts, index=def_idx, key="cf_year_selector_widget")

with col_f3:
    month_names_map = {
        0: "🌐 Tutto l'Anno",
        1: "01 - Gennaio",
        2: "02 - Febbraio",
        3: "03 - Marzo",
        4: "04 - Aprile",
        5: "05 - Maggio",
        6: "06 - Giugno",
        7: "07 - Luglio",
        8: "08 - Agosto",
        9: "09 - Settembre",
        10: "10 - Ottobre",
        11: "11 - Novembre",
        12: "12 - Dicembre"
    }
    month_opts = list(month_names_map.keys())
    sel_month_num = st.selectbox(
        "Mese di Analisi:",
        options=month_opts,
        format_func=lambda m: month_names_map[m],
        index=0,
        key="cf_month_selector_widget"
    )

with col_f4:
    available_accs = ["🌐 Tutti i Conti"]
    if not df_cf.empty and "account_name" in df_cf.columns:
        acc_list = sorted([str(a) for a in df_cf["account_name"].dropna().unique()])
        available_accs.extend(acc_list)
    sel_acc = st.selectbox("Conto / Carta:", available_accs, index=0, key="cf_account_selector_widget")

# Filtra dataset Cash Flow
df_cf_filtered = df_cf.copy() if not df_cf.empty else pd.DataFrame()
if not df_cf_filtered.empty:
    if sel_year_str != "🌐 Tutto lo Storico":
        sel_y = int(sel_year_str)
        df_cf_filtered = df_cf_filtered[df_cf_filtered["tx_date"].dt.year == sel_y]
    if sel_month_num != 0:
        df_cf_filtered = df_cf_filtered[df_cf_filtered["tx_date"].dt.month == sel_month_num]
    if sel_acc != "🌐 Tutti i Conti":
        df_cf_filtered = df_cf_filtered[df_cf_filtered["account_name"] == sel_acc]

cf_analytics = compute_cashflow_analytics(df_cf_filtered)

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
is_single_month = (sel_month_num != 0)
month_label = month_names_map[sel_month_num].split(" - ")[-1] if is_single_month else ""

with c1:
    kpi_title_in = f"Entrate {month_label}" if is_single_month else "Entrate Totali"
    metric_card(kpi_title_in, fmt_eur(cf_analytics.get("total_inflow", 0.0)), delta="Accrediti & Compensi", delta_color="normal")
with c2:
    kpi_title_out = f"Uscite {month_label}" if is_single_month else "Uscite Totali"
    metric_card(kpi_title_out, fmt_eur(cf_analytics.get("total_outflow", 0.0)), delta="Spese & Oneri", delta_color="inverse")
with c3:
    net_cf = cf_analytics.get("net_savings", cf_analytics.get("net_cash_flow", 0.0))
    net_col = "normal" if net_cf >= 0 else "inverse"
    sav_r = cf_analytics.get("savings_rate_pct", cf_analytics.get("savings_rate", 0.0))
    kpi_title_net = f"Risparmio {month_label}" if is_single_month else "Risparmio Netto"
    metric_card(kpi_title_net, fmt_eur(net_cf), delta=f"{sav_r:.1f}% Savings Rate", delta_color=net_col)
with c4:
    if is_single_month:
        tot_out = cf_analytics.get("total_outflow", 0.0)
        daily_burn = tot_out / 30.0
        metric_card("Burn Rate Giornaliero", fmt_eur(daily_burn), delta="Spesa Media / Giorno", delta_color="inverse")
    else:
        burn_r = cf_analytics.get("avg_monthly_expense", cf_analytics.get("monthly_burn_rate", 0.0))
        metric_card("Burn Rate Medio", fmt_eur(burn_r), delta="Spesa Mensile Media", delta_color="inverse")
with c5:
    if is_single_month:
        tx_count = len(df_cf_filtered)
        metric_card("Attività Mese", f"{tx_count} Movimenti", delta="Transazioni Registrate", delta_color="normal")
    else:
        metric_card("Entrata Media Mensile", fmt_eur(cf_analytics.get("avg_monthly_income", 0.0)), delta="Cash Inflow Medio", delta_color="normal")

st.divider()

@st.dialog("🌊 Dettaglio Flusso Finanziario & Libro Mastro", width="large")
def render_flow_detail_modal(node_name: str, df_source: pd.DataFrame):
    """Visualizza il modale interattivo istituzionale con statistiche, grafico e transazioni del flusso selezionato."""
    if df_source is None or df_source.empty:
        st.info("Nessuna transazione disponibile per questo flusso.")
        return

    df = df_source.copy()
    clean_df = df[
        (df["direction"] != "transfer") & 
        (~df["category_name"].astype(str).str.contains("Girocont|Trasferiment", case=False, na=False))
    ]
    if clean_df.empty:
        clean_df = df.copy()

    if "Reddito" in node_name or "Inflows" in node_name:
        df_sub = clean_df[clean_df["direction"] == "inflow"].copy()
        flow_desc = "Tutte le entrate, stipendi e accrediti registrati nel periodo."
    elif "Bisogni Primari" in node_name or "Needs" in node_name:
        df_sub = clean_df[(clean_df["direction"] == "outflow") & (clean_df["nature"] == "need")].copy()
        flow_desc = "Spese fisse e necessità primarie (Affitto/Mutuo, Bollette, Spesa Alimentare, Salute)."
    elif "Desideri" in node_name or "Wants" in node_name:
        df_sub = clean_df[(clean_df["direction"] == "outflow") & (clean_df["nature"] == "want")].copy()
        flow_desc = "Spese discrezionali e lifestyle (Ristoranti, Viaggi, Shopping, Svago)."
    elif "Risparmio" in node_name or "Investimenti" in node_name:
        df_sub = clean_df[(clean_df["direction"] == "outflow") & (clean_df["nature"] == "saving")].copy()
        flow_desc = "Accantonamenti, PAC, investimenti e fondo pensione."
    elif "Altre Entrate" in node_name:
        inflows = clean_df[clean_df["direction"] == "inflow"]
        tot_in = inflows["amount"].sum()
        sub_cats = inflows.groupby("category_name")["amount"].sum()
        minor_names = sub_cats[sub_cats < tot_in * 0.04].index.tolist()
        df_sub = inflows[inflows["category_name"].isin(minor_names)].copy()
        flow_desc = "Aggregato di tutte le entrate secondarie sotto la soglia del 4%."
    elif "Altre Spese" in node_name:
        outflows = clean_df[clean_df["direction"] == "outflow"]
        if "Desideri" in node_name:
            p_out = outflows[outflows["nature"] == "want"]
        elif "Bisogni" in node_name:
            p_out = outflows[outflows["nature"] == "need"]
        else:
            p_out = outflows[outflows["nature"] == "saving"]
        p_tot = p_out["amount"].sum()
        sub_cats = p_out.groupby("category_name")["amount"].sum()
        minor_names = sub_cats[sub_cats < p_tot * 0.07].index.tolist()
        df_sub = p_out[p_out["category_name"].isin(minor_names)].copy()
        flow_desc = f"Aggregato delle voci di spesa minori ({', '.join(minor_names[:4]) if minor_names else 'varie'})."
    else:
        df_sub = clean_df[clean_df["category_name"].astype(str) == node_name].copy()
        if df_sub.empty:
            df_sub = clean_df[clean_df["category_name"].astype(str).str.contains(node_name, regex=False, case=False, na=False)].copy()
        flow_desc = f"Dettaglio analitico delle transazioni per la categoria '{node_name}'."

    st.markdown(f"""
    <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="font-size: 16px; font-weight: 700; color: #ffffff;">
                🔍 {node_name}
            </div>
            <div class="splash-pill" style="background: rgba(56, 189, 248, 0.15); border-color: rgba(56, 189, 248, 0.4); color: #38bdf8; font-size: 12px;">
                <b>{len(df_sub)}</b> Movimenti Registrati
            </div>
        </div>
        <div style="font-size: 12.5px; color: #94a3b8; margin-top: 6px;">
            {flow_desc}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if df_sub.empty:
        st.info("Nessun movimento trovato per questo specifico flusso.")
        return

    tot_amt = float(df_sub["amount"].sum())
    tx_count = len(df_sub)
    avg_tx = float(df_sub["amount"].mean()) if tx_count > 0 else 0.0
    max_tx = float(df_sub["amount"].max()) if tx_count > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Totale Flusso", fmt_eur(tot_amt), delta=f"{tx_count} Operazioni", delta_color="normal")
    with m2:
        metric_card("Spesa Media / Tx", fmt_eur(avg_tx), delta="Ticket medio", delta_color="normal")
    with m3:
        metric_card("Picco Massimo", fmt_eur(max_tx), delta="Massima spesa", delta_color="normal")
    with m4:
        top_acc = str(df_sub["account_name"].mode().values[0]) if not df_sub.empty and not df_sub["account_name"].isna().all() else "N/D"
        metric_card("Conto Principale", top_acc[:16], delta="Rapporto bancario", delta_color="normal")

    st.write("")

    # Grafico trend mensile se ci sono più mesi
    df_sub["tx_date"] = pd.to_datetime(df_sub["tx_date"])
    df_sub["year_month"] = df_sub["tx_date"].dt.strftime("%Y-%m")
    m_agg = df_sub.groupby("year_month")["amount"].sum().reset_index()

    if len(m_agg) > 1:
        fig_m = px.bar(
            m_agg,
            x="year_month",
            y="amount",
            labels={"year_month": "Mese", "amount": "Importo (€)"},
            title=f"Distribuzione Mensile — {node_name}",
            color_discrete_sequence=["#38bdf8"]
        )
        fig_m.update_layout(
            height=210,
            margin=dict(t=30, l=10, r=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e6edf3", size=11),
            hoverlabel=dict(bgcolor="#161b22", bordercolor="#38bdf8")
        )
        fig_m.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
        fig_m.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
        st.plotly_chart(fig_m, use_container_width=True)

    # Registro Movimenti
    st.markdown("##### 📋 Registro Movimenti Dettagliato")
    disp_cols = ["tx_date", "merchant", "account_name", "amount", "category_name", "notes"]
    available_cols = [c for c in disp_cols if c in df_sub.columns]
    
    df_disp = df_sub[available_cols].copy()
    df_disp["tx_date"] = df_disp["tx_date"].dt.strftime("%Y-%m-%d")
    df_disp = df_disp.sort_values(by="tx_date", ascending=False)
    df_disp["amount"] = df_disp["amount"].apply(lambda v: fmt_eur(v))

    col_names = {
        "tx_date": "Data",
        "merchant": "Descrizione / Esercente",
        "account_name": "Conto / Carta",
        "amount": "Importo",
        "category_name": "Categoria",
        "notes": "Note"
    }
    df_disp = df_disp.rename(columns=col_names)

    st.dataframe(df_disp, use_container_width=True, hide_index=True)

    csv_bytes = df_sub.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"💾 Scarica Transazioni {node_name} (.CSV)",
        data=csv_bytes,
        file_name=f"argus_flusso_{node_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"btn_dl_flow_modal_{node_name.replace(' ', '_')}"
    )


st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab_sankey, tab_trend, tab_subs, tab_fc, tab_ledger = st.tabs([
    "🌊 Diagramma Sankey & Flussi",
    "📊 Trend Mensile & Statistiche MoM",
    "🔁 Abbonamenti & Costi Fissi (Sentinel)",
    "🔮 Previsione Cassa & Anomalie",
    "📜 Libro Mastro & Inserimento"
])

with tab_sankey:
    section("🌊 Diagramma Sankey dei Flussi Finanziari")
    sankey = cf_analytics.get("sankey_data", {})
    if sankey and sankey.get("nodes") and sankey.get("links"):
        fig_sankey = go.Figure(data=[go.Sankey(
            arrangement="snap",
            valueformat=",.2f",
            valuesuffix=" €",
            node=dict(
                pad=18,
                thickness=18,
                line=dict(color="#0e1117", width=1),
                label=sankey["nodes"],
                color=sankey.get("node_colors", ["#10b981"] * len(sankey["nodes"])),
                hovertemplate="<b>%{label}</b><br>Totale Flusso: <b>€ %{value:,.2f}</b><extra></extra>"
            ),
            link=dict(
                source=[l["source"] for l in sankey["links"]],
                target=[l["target"] for l in sankey["links"]],
                value=[l["value"] for l in sankey["links"]],
                color=[l.get("color", "rgba(99, 102, 241, 0.3)") for l in sankey["links"]],
                hovertemplate="<b>%{source.label}</b> ➔ <b>%{target.label}</b><br>Importo Flusso: <b>€ %{value:,.2f}</b><extra></extra>"
            )
        )])
        fig_sankey.update_layout(
            height=440,
            margin=dict(t=20, l=15, r=15, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#e6edf3", size=12),
            hoverlabel=dict(
                bgcolor="#161b22",
                bordercolor="#38bdf8",
                font=dict(family="Outfit, sans-serif", size=12, color="#ffffff")
            )
        )
        chart_select = st.plotly_chart(
            fig_sankey,
            use_container_width=True,
            on_select="rerun",
            selection_mode=["points"],
            key="sankey_flow_interactive_chart",
            config={'displayModeBar': False}
        )

        # Controller Rapido per Ispezione & Apertura Modale
        c_pck, c_btn = st.columns([3.5, 1.5])
        with c_pck:
            sel_flow_item = st.selectbox(
                "🔍 Ispezione Flusso / Categoria nel Modale:",
                options=sankey["nodes"],
                key="sankey_flow_dropdown_picker",
                help="Scegli un nodo o categoria per aprire il dettaglio analitico"
            )
        with c_btn:
            st.write("")
            if st.button("🔎 Apri Dettaglio Modale", type="primary", use_container_width=True, key="btn_open_flow_dialog"):
                render_flow_detail_modal(sel_flow_item, df_cf_filtered)

        # Se l'utente clicca direttamente su un nodo nel grafico Sankey
        if chart_select and "selection" in chart_select and chart_select["selection"].get("points"):
            pts = chart_select["selection"]["points"]
            if pts and "point_number" in pts[0]:
                pt_idx = pts[0]["point_number"]
                if pt_idx < len(sankey["nodes"]):
                    clicked_label = sankey["nodes"][pt_idx]
                    render_flow_detail_modal(clicked_label, df_cf_filtered)
    else:
        st.info("Nessuna transazione per il periodo selezionato.")

    st.write("")
    tgt_needs = float(st.session_state.get("wealth_budget_needs_pct", 50.0))
    tgt_wants = float(st.session_state.get("wealth_budget_wants_pct", 30.0))
    tgt_savings = float(st.session_state.get("wealth_budget_savings_pct", 20.0))
    rule_str = f"{tgt_needs:.0f}/{tgt_wants:.0f}/{tgt_savings:.0f}"

    section(f"⚖️ Bilanciamento Budget & Destinazione Spese (Regola {rule_str})")
    r50 = cf_analytics.get("rule_50_30_20", {})
    needs_p = r50.get("needs_pct", 0.0)
    wants_p = r50.get("wants_pct", 0.0)
    savings_p = r50.get("savings_pct", 0.0)

    b_c1, b_c2, b_c3 = st.columns(3)
    with b_c1:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #f59e0b; border-radius:10px; padding:14px 18px; min-height:108px; display:flex; flex-direction:column; justify-content:space-between;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">🏠 Bisogni Primari (Needs)</span>
                <span style="font-weight:700; color:#f59e0b; font-size:15px;">{needs_p:.1f}% <span style="font-size:11px; color:#8b949e;">(Target {tgt_needs:.0f}%)</span></span>
            </div>
            <div style="font-size:13px; color:#8b949e; margin-top:6px;">Totale Speso: <b style="color:#ffffff; font-size:15px;">{fmt_eur(r50.get('needs_amount', 0.0))}</b></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, max(0.0, needs_p / 100.0)))

    with b_c2:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #ec4899; border-radius:10px; padding:14px 18px; min-height:108px; display:flex; flex-direction:column; justify-content:space-between;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">🍽️ Desideri & Svago (Wants)</span>
                <span style="font-weight:700; color:#ec4899; font-size:15px;">{wants_p:.1f}% <span style="font-size:11px; color:#8b949e;">(Target {tgt_wants:.0f}%)</span></span>
            </div>
            <div style="font-size:13px; color:#8b949e; margin-top:6px;">Totale Speso: <b style="color:#ffffff; font-size:15px;">{fmt_eur(r50.get('wants_amount', 0.0))}</b></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, max(0.0, wants_p / 100.0)))

    with b_c3:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #06b6d4; border-radius:10px; padding:14px 18px; min-height:108px; display:flex; flex-direction:column; justify-content:space-between;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#ffffff; font-size:14px;">📈 Risparmio & Investimenti</span>
                <span style="font-weight:700; color:#06b6d4; font-size:15px;">{savings_p:.1f}% <span style="font-size:11px; color:#8b949e;">(Target {tgt_savings:.0f}%)</span></span>
            </div>
            <div style="font-size:13px; color:#8b949e; margin-top:6px;">Totale Accumulato: <b style="color:#ffffff; font-size:15px;">{fmt_eur(r50.get('savings_amount', 0.0))}</b></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, max(0.0, savings_p / 100.0)))


with tab_trend:
    st.markdown("### 📊 Evoluzione Mensile & Statistiche MoM (Month-over-Month)")
    st.caption("Confronto dinamico delle entrate, uscite, tasso di risparmio e ripartizione di spesa mese su mese.")
    
    # Dataset per il trend (usa df_cf dell'anno selezionato o globale)
    df_trend_src = df_cf.copy() if not df_cf.empty else pd.DataFrame()
    if not df_trend_src.empty and sel_year_str != "🌐 Tutto lo Storico":
        df_trend_src = df_trend_src[df_trend_src["tx_date"].dt.year == int(sel_year_str)]
    if not df_trend_src.empty and sel_acc != "🌐 Tutti i Conti":
        df_trend_src = df_trend_src[df_trend_src["account_name"] == sel_acc]

    if not df_trend_src.empty:
        df_trend_src["year_month"] = df_trend_src["tx_date"].dt.strftime("%Y-%m")
        
        # Aggregazione mensile
        m_in = df_trend_src[df_trend_src["direction"] == "inflow"].groupby("year_month")["amount"].sum()
        m_out = df_trend_src[df_trend_src["direction"] == "outflow"].groupby("year_month")["amount"].sum()
        
        all_ym = sorted(list(set(m_in.index).union(set(m_out.index))))
        df_monthly = pd.DataFrame({"year_month": all_ym})
        df_monthly["Entrate"] = df_monthly["year_month"].map(m_in).fillna(0.0)
        df_monthly["Uscite"] = df_monthly["year_month"].map(m_out).fillna(0.0)
        df_monthly["Risparmio_Netto"] = df_monthly["Entrate"] - df_monthly["Uscite"]
        df_monthly["Savings_Rate_Pct"] = np.where(
            df_monthly["Entrate"] > 0,
            (df_monthly["Risparmio_Netto"] / df_monthly["Entrate"]) * 100.0,
            0.0
        )
        df_monthly["MoM_Uscite_Pct"] = df_monthly["Uscite"].pct_change() * 100.0

        # Grafico Trend Barre + Linea
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=df_monthly["year_month"],
            y=df_monthly["Entrate"],
            name="Entrate (€)",
            marker_color="#10b981",
            hovertemplate="<b>%{x}</b><br>Entrate: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_trend.add_trace(go.Bar(
            x=df_monthly["year_month"],
            y=df_monthly["Uscite"],
            name="Uscite (€)",
            marker_color="#f43f5e",
            hovertemplate="<b>%{x}</b><br>Uscite: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_trend.add_trace(go.Bar(
            x=df_monthly["year_month"],
            y=df_monthly["Risparmio_Netto"],
            name="Risparmio Netto (€)",
            marker_color="#38bdf8",
            hovertemplate="<b>%{x}</b><br>Risparmio: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_monthly["year_month"],
            y=df_monthly["Savings_Rate_Pct"],
            name="Savings Rate (%)",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=2.5),
            marker=dict(size=6),
            hovertemplate="<b>%{x}</b><br>Savings Rate: <b>%{y:.1f}%</b><extra></extra>"
        ))

        fig_trend.update_layout(
            barmode="group",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Importo (€)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            yaxis2=dict(title="Savings Rate (%)", overlaying="y", side="right", showgrid=False, range=[-20, 100])
        )
        st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})

        # Sezione Dettaglio & Top Categories
        tr_c1, tr_c2 = st.columns([1.3, 1.0])
        with tr_c1:
            st.markdown("##### 📋 Riepilogo Mese per Mese")
            df_m_show = df_monthly.copy()
            df_m_show["Mese"] = df_m_show["year_month"]
            df_m_show["Entrate_fmt"] = df_m_show["Entrate"].apply(lambda v: f"€ {v:,.2f}")
            df_m_show["Uscite_fmt"] = df_m_show["Uscite"].apply(lambda v: f"€ {v:,.2f}")
            df_m_show["Netto_fmt"] = df_m_show["Risparmio_Netto"].apply(lambda v: f"€ {v:,.2f}")
            df_m_show["SR_fmt"] = df_m_show["Savings_Rate_Pct"].apply(lambda v: f"{v:.1f}%")
            df_m_show["MoM_fmt"] = df_m_show["MoM_Uscite_Pct"].apply(lambda v: f"{v:+.1f}%" if pd.notna(v) else "-")

            st.dataframe(
                df_m_show[["Mese", "Entrate_fmt", "Uscite_fmt", "Netto_fmt", "SR_fmt", "MoM_fmt"]].rename(columns={
                    "Entrate_fmt": "Entrate",
                    "Uscite_fmt": "Uscite",
                    "Netto_fmt": "Risparmio Netto",
                    "SR_fmt": "Savings Rate",
                    "MoM_fmt": "Δ Uscite MoM"
                }),
                hide_index=True,
                use_container_width=True
            )

        with tr_c2:
            st.markdown("##### 🏆 Top 10 Categorie di Spesa")
            df_outflows = df_cf_filtered[df_cf_filtered["direction"] == "outflow"]
            if not df_outflows.empty:
                cat_agg = df_outflows.groupby("category_name")["amount"].sum().reset_index()
                cat_agg = cat_agg.sort_values(by="amount", ascending=False).head(10)
                
                fig_top_cat = px.bar(
                    cat_agg,
                    x="amount",
                    y="category_name",
                    orientation="h",
                    color="amount",
                    color_continuous_scale="Blues",
                    labels={"amount": "Speso (€)", "category_name": "Categoria"}
                )
                fig_top_cat.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    margin=dict(l=10, r=10, t=10, b=10),
                    yaxis=dict(autorange="reversed"),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_top_cat, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Nessuna uscita registrata per il periodo selezionato.")
    else:
        st.info("Nessun dato storico per elaborare il trend mensile.")


with tab_subs:
    st.markdown("### 🔁 Subscription Sentinel & Costo Opportunità a Lungo Termine")
    st.caption("Rilevamento autonomo dei costi fissi e degli abbonamenti ricorrenti con calcolo del capitale perso se investito al 7% annuo.")
    
    subs_data = compute_recurring_subscriptions_analytics(df_cf_filtered, engine=engine, portfolio_id=current_pid)
    
    sk1, sk2, sk3, sk4 = st.columns(4)
    with sk1:
        metric_card("Burn Ricorrente", fmt_eur(subs_data["total_monthly_burn"]), delta="Spesa Mensile Fissa", delta_color="inverse", help_text="Somma di tutti i pagamenti ricorrenti e abbonamenti mensilizzati.")
    with sk2:
        metric_card("Costo Annuo Totale", fmt_eur(subs_data["total_annual_burn"]), delta=f"{subs_data['count']} Servizi Attivi", delta_color="inverse", help_text="Costo complessivo proiettato su base annua.")
    with sk3:
        metric_card("Opportunity Drag (10y)", fmt_eur(subs_data["opportunity_cost_10y"]), delta="Capitale Perso a 10 Anni", delta_color="inverse", help_text="Valore futuro del flusso mensile di abbonamenti se investito al 7% annuo composto per 10 anni.")
    with sk4:
        metric_card("Opportunity Drag (20y)", fmt_eur(subs_data["opportunity_cost_20y"]), delta="Capitale Perso a 20 Anni", delta_color="inverse", help_text="Valore futuro del flusso mensile di abbonamenti se investito al 7% annuo composto per 20 anni.")

    st.write("")
    sub_col1, sub_col2 = st.columns([1.9, 1.1])
    with sub_col1:
        st.markdown("##### 📋 Registro Abbonamenti & Costi Fissi Rilevati")
        if subs_data["subscriptions"]:
            df_s_disp = pd.DataFrame(subs_data["subscriptions"])
            
            # Ordine colonne ideale
            cols_to_show = []
            if "status_badge" in df_s_disp.columns:
                cols_to_show.append("status_badge")
            cols_to_show.extend(["merchant", "category"])
            if "payment_day" in df_s_disp.columns:
                cols_to_show.append("payment_day")
            cols_to_show.extend(["monthly_amount", "annual_amount", "opportunity_cost_10y"])
            
            cols_to_show = [c for c in cols_to_show if c in df_s_disp.columns]
                
            st.dataframe(
                df_s_disp[cols_to_show],
                column_config={
                    "status_badge": st.column_config.TextColumn("Stato / Durata", width="medium"),
                    "merchant": st.column_config.TextColumn("Servizio / Beneficiario", width="medium"),
                    "category": st.column_config.TextColumn("Categoria", width="small"),
                    "payment_day": st.column_config.NumberColumn("Giorno", format="%d", width="small"),
                    "monthly_amount": st.column_config.NumberColumn("Costo Mese", format="€ %,.2f", width="small"),
                    "annual_amount": st.column_config.NumberColumn("Costo Anno", format="€ %,.2f", width="small"),
                    "opportunity_cost_10y": st.column_config.NumberColumn("Opportunity 10a", format="€ %,.2f", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nessun abbonamento ricorrente rilevato nelle transazioni caricate.")

    with sub_col2:
        st.markdown("##### 🍩 Ripartizione per Categoria")
        if subs_data["category_breakdown"]:
            cats_sorted = sorted(subs_data["category_breakdown"].items(), key=lambda x: x[1], reverse=True)
            labels = [c[0] for c in cats_sorted]
            values = [c[1] for c in cats_sorted]
            
            fig_sub_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                textinfo="percent",
                textposition="inside",
                insidetextorientation="horizontal",
                hovertemplate="<b>%{label}</b><br>Spesa Mensile: <b>€ %{value:,.2f}</b> (%{percent})<extra></extra>",
                marker=dict(colors=["#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#fb923c", "#34d399", "#94a3b8"])
            )])
            fig_sub_pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
                annotations=[dict(
                    text=f"<span style='font-size:10px; color:#94a3b8;'>BURN MESE</span><br><b style='font-size:13px; color:#ffffff;'>€ {subs_data['total_monthly_burn']:,.0f}</b>",
                    x=0.5, y=0.5, font_size=12, showarrow=False
                )]
            )
            st.plotly_chart(fig_sub_pie, use_container_width=True, config={'displayModeBar': False})


with tab_fc:
    st.markdown("### 🔮 Previsione Cassa Rolling & Rilevamento Anomalie Z-Score")
    st.caption("Proiezione probabilistica della liquidità a 3 e 6 mesi e identificazione automatica di spike o uscite straordinarie.")
    
    fc_data = compute_cashflow_forecast_and_anomalies(df_cf_filtered, current_liquid_cash=nw_curr.liquid_cash)
    
    fck1, fck2, fck3 = st.columns(3)
    with fck1:
        metric_card("Liquidità Attuale", fmt_eur(fc_data["current_liquidity"]), delta="Disponibilità Conti", delta_color="normal")
    with fck2:
        d_3m = fc_data["projected_liquidity_3m"] - fc_data["current_liquidity"]
        metric_card("Previsione Cassa (3 Mesi)", fmt_eur(fc_data["projected_liquidity_3m"]), delta=f"{fmt_eur(d_3m)} Momentum", delta_color="normal" if d_3m >= 0 else "inverse")
    with fck3:
        d_6m = fc_data["projected_liquidity_6m"] - fc_data["current_liquidity"]
        metric_card("Previsione Cassa (6 Mesi)", fmt_eur(fc_data["projected_liquidity_6m"]), delta=f"{fmt_eur(d_6m)} Momentum", delta_color="normal" if d_6m >= 0 else "inverse")

    st.write("")
    # Grafico di previsione Fan Chart
    df_fc_timeline = pd.DataFrame(fc_data["forecast_timeline"])
    if not df_fc_timeline.empty:
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=df_fc_timeline["mese"],
            y=df_fc_timeline["p90_ottimistico"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            name="P90 Ottimistico"
        ))
        fig_fc.add_trace(go.Scatter(
            x=df_fc_timeline["mese"],
            y=df_fc_timeline["p10_conservativo"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(56, 189, 248, 0.15)",
            name="Intervallo di Confidenza (P10 - P90)",
            hovertemplate="<b>%{x}</b><br>Scenario Prudenziale: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_fc.add_trace(go.Scatter(
            x=df_fc_timeline["mese"],
            y=df_fc_timeline["p50_atteso"],
            mode="lines+markers",
            line=dict(color="#38bdf8", width=3),
            name="Traiettoria Attesa (P50)",
            hovertemplate="<b>%{x}</b><br>Saldo Atteso: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_fc.update_layout(
            title=dict(text="Proiezione della Riserva Liquida (6 Mesi Rolling)", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            xaxis_title="Mese",
            yaxis_title="Liquidità (€)",
            margin=dict(l=10, r=10, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_fc, use_container_width=True, config={'displayModeBar': False})

    st.write("")
    st.markdown("##### 🚨 Rilevamento Anomalie & Spike di Spesa (Z-Score > 1.8)")
    if fc_data["anomalies"]:
        df_anom = pd.DataFrame(fc_data["anomalies"])
        st.dataframe(
            df_anom[["data", "categoria", "descrizione", "importo", "media_categoria", "scostamento_pct", "z_score"]],
            column_config={
                "data": st.column_config.TextColumn("Data Spesa", width="small"),
                "categoria": st.column_config.TextColumn("Categoria", width="medium"),
                "descrizione": st.column_config.TextColumn("Esercente / Causale", width="medium"),
                "importo": st.column_config.NumberColumn("Importo Speso (€)", format="€ %,.2f", width="small"),
                "media_categoria": st.column_config.NumberColumn("Media Storica Categoria (€)", format="€ %,.2f", width="small"),
                "scostamento_pct": st.column_config.NumberColumn("Scostamento (%)", format="+%.1f%%", width="small"),
                "z_score": st.column_config.NumberColumn("Z-Score", format="%.2f", width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("🟢 Nessuna spesa anomala rilevata rispetto ai pattern storici del profilo.")


with tab_ledger:
    df_accs = get_wealth_accounts(engine)
    df_cats = get_wealth_categories(engine)

    with st.expander("✍️ Inserimento Manuale Nuova Transazione", expanded=False):
        with st.form("form_add_cashflow_manual"):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                tx_d = st.date_input("Data Transazione *", value=date.today())
                tx_amt = st.number_input("Importo (€) *", min_value=0.01, value=50.0, step=1.0)
                tx_dir = st.selectbox("Direzione *", [("outflow", "Uscita / Spesa"), ("inflow", "Entrata / Accredito")], format_func=lambda x: x[1])
            with fc2:
                if not df_accs.empty:
                    acc_choices = {row["name"]: row["account_id"] for _, row in df_accs.iterrows()}
                    tx_acc = st.selectbox("Conto *", list(acc_choices.keys()))
                else:
                    tx_acc = None
                if not df_cats.empty:
                    cat_dict = {f"{r['icon']} {r['name']}": r['category_id'] for _, r in df_cats.iterrows()}
                    tx_cat = st.selectbox("Categoria *", list(cat_dict.keys()))
                else:
                    tx_cat = None
            with fc3:
                tx_merch = st.text_input("Beneficiario / Merchant", placeholder="es. Esselunga, Amazon, Stipendio...")
                tx_notes = st.text_input("Note / Descrizione", placeholder="es. Spesa settimanale")

            btn_save_tx = st.form_submit_button("💾 Registra Transazione", use_container_width=True)
            if btn_save_tx:
                if tx_amt > 0 and tx_acc and tx_cat:
                    insert_cashflow_tx(engine, {
                        "account_id": acc_choices[tx_acc],
                        "category_id": cat_dict[tx_cat],
                        "tx_date": tx_d,
                        "amount": tx_amt,
                        "direction": tx_dir[0],
                        "merchant": tx_merch,
                        "notes": tx_notes
                    })
                    st.success("Transazione registrata con successo!")
                    st.rerun()

    st.markdown("##### 📜 Libro Mastro Movimenti Completo")
    if not df_cf.empty:
        st.dataframe(
            df_cf[["tx_date", "direction", "amount", "category_name", "merchant", "account_name", "notes"]].rename(columns={
                "tx_date": "Data",
                "direction": "Tipo",
                "amount": "Importo (€)",
                "category_name": "Categoria",
                "merchant": "Beneficiario / Merchant",
                "account_name": "Conto",
                "notes": "Note"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nessuna transazione presente nel libro mastro.")

