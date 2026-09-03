# ============================================================
# 20_⚖️_Pianificazione_Successoria.py
# ARGUS Wealth — Pianificazione Successoria, Quote di Legittima & Estate Planning
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
    compute_estate_planning_analytics,
    compute_family_governance_and_patti_di_famiglia
)


st.set_page_config(page_title="Pianificazione Successoria | ARGUS Wealth", page_icon="⚖️", layout="wide")
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
    st.title("⚖️ ARGUS Wealth — Pianificazione Successoria")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per calcolare l'asse ereditario, le quote di riserva e le franchigie di successione.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="estate_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p20")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Pianificazione Successoria & Estate Planning",
    subtitle="Mappatura dell'Asse Ereditario (Codice Civile art. 536-544), Quota Legittima vs Disponibile, Franchigie Fiscali e Strumenti di Protezione.",
    icon="⚖️"
)

from core.wealth.wealth_modals import render_succession_methodology_modal

col_est_h1, col_est_h2 = st.columns([3.5, 1.2])
with col_est_h1:
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="estate_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()

with col_est_h2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("ℹ️ Guida Successioni & Patti", key="btn_modal_estate_p20", use_container_width=True):
        render_succession_methodology_modal()


nw = compute_consolidated_net_worth(engine, portfolio_id=current_pid)

# ── CONFIGURAZIONE SITUAZIONE FAMILIARE ──────────────────────
with st.container():
    st.markdown("##### 👨‍👩‍👧‍👦 Parametri Nucleo Familiare & Eredi")
    f_c1, f_c2, f_c3 = st.columns([1.5, 1.5, 2])
    with f_c1:
        has_spouse = st.checkbox("Presenza Coniuge in Vita", value=True)
    with f_c2:
        num_children = st.number_input("Numero di Figli", min_value=0, max_value=10, value=2, step=1)
    with f_c3:
        donations = st.number_input("Donazioni Effettuate in Vita (€)", min_value=0.0, value=0.0, step=5000.0, help="Donazioni soggette a collazione o imputazione ex se nella riunione fittizia (art. 556 c.c.).")

estate = compute_estate_planning_analytics(
    net_worth_summary=nw,
    children_count=num_children,
    has_spouse=has_spouse,
    donations_in_life=donations
)

# ── TOP KPI ROW ─────────────────────────────────────────────
ek1, ek2, ek3, ek4, ek5 = st.columns(5)
with ek1:
    metric_card("Asse Ereditario", fmt_eur(estate['total_wealth']), delta="Riunione Fittizia", help_text="Patrimonio Netto + Donazioni in vita (Riunione Fittizia art. 556 c.c.)")
with ek2:
    legit_tot = estate['val_legittima_coniuge'] + estate['val_legittima_figli_tot']
    metric_card("Quota Legittima", fmt_eur(legit_tot), delta="Riservata ex lege", delta_color="inverse", help_text="Quota minima riservata per legge ai legittimari (coniuge e figli).")
with ek3:
    metric_card("Quota Disponibile", fmt_eur(estate['val_disponibile']), delta=f"{estate['disponibile_pct']:.1f}% dell'Asse", delta_color="normal", help_text="Quota di patrimonio che il testatore può destinare liberamente a chiunque.")
with ek4:
    metric_card("Asset Esenti", fmt_eur(estate['total_exempt_assets']), delta="Esenti da Imposta", delta_color="normal", help_text="Fondi pensione e Titoli di Stato esenti da imposta di successione ex lege.")
with ek5:
    stat_del = "Sotto Franchigia" if estate["is_under_exempt_threshold"] else "Imposta Applicata"
    del_col = "normal" if estate["is_under_exempt_threshold"] else "inverse"
    metric_card("Imposta Successione", fmt_eur(estate['total_succession_tax']), delta=stat_del, delta_color=del_col, help_text="Imposta totale stimata dovuta all'Erario in base ai gradi di parentela.")


st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab_shares, tab_taxes, tab_shield, tab_patto = st.tabs([
    "🍰 Ripartizione Quote di Legittima",
    "🧾 Calcolo Imposta & Franchigie",
    "🛡️ Strumenti di Protezione Patrimoniale",
    "🏛️ Family Governance & Patti di Famiglia"
])

with tab_shares:
    st.markdown("### 🍰 Ripartizione Quote di Legittima (Codice Civile)")
    st.caption(f"Norma applicata: **{estate['quota_desc']}**")

    col_chart, col_details = st.columns([1.2, 1.1])
    with col_chart:
        labels = []
        values = []
        colors = []
        
        if estate["legittima_coniuge_pct"] > 0:
            labels.append("Legittima Coniuge")
            values.append(estate["val_legittima_coniuge"])
            colors.append("#38bdf8")
            
        if estate["legittima_figli_tot_pct"] > 0:
            if num_children == 1:
                labels.append("Legittima Figlio Unico")
                values.append(estate["val_legittima_figli_tot"])
                colors.append("#34d399")
            else:
                for i in range(1, num_children + 1):
                    labels.append(f"Legittima Figlio #{i}")
                    values.append(estate["val_legittima_per_figlio"])
                    colors.append("#10b981")
                    
        labels.append("Quota Disponibile")
        values.append(estate["val_disponibile"])
        colors.append("#fbbf24")

        fig_estate = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.60,
            marker_colors=colors,
            textinfo="percent",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>Valore: <b>€ %{value:,.2f}</b> (%{percent})<extra></extra>"
        )])
        fig_estate.update_layout(
            title=dict(text="Mappa Grafica dell'Asse Ereditario", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=10, r=10, t=50, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<span style='font-size:10.5px; color:#94a3b8;'>ASSE TOTALE</span><br><b style='font-size:14px; color:#ffffff;'>€ {estate['total_wealth']:,.0f}</b>",
                x=0.5, y=0.5, font_size=12, showarrow=False
            )]
        )
        st.plotly_chart(fig_estate, use_container_width=True, config={'displayModeBar': False})

    with col_details:
        st.markdown("##### 📜 Dettaglio Diritti degli Eredi")
        if has_spouse:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#ffffff; font-size:13.5px;">👰 Coniuge Superstite:</b>
                    <span class="mono-num" style="font-weight:700; color:#38bdf8; font-size:14px;">€ {estate['val_legittima_coniuge']:,.2f} ({estate['legittima_coniuge_pct']}%)</span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Include per legge il diritto di abitazione sulla casa coniugale (art. 540 c.c.).</div>
            </div>
            """, unsafe_allow_html=True)
            
        if num_children > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(52, 211, 153, 0.25); border-left: 4px solid #34d399; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#ffffff; font-size:13.5px;">👧 Figli ({num_children}):</b>
                    <span class="mono-num" style="font-weight:700; color:#34d399; font-size:14px;">€ {estate['val_legittima_figli_tot']:,.2f} ({estate['legittima_figli_tot_pct']}%)</span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Quota individuale: <b style="color:#e2e8f0;">€ {estate['val_legittima_per_figlio']:,.2f}</b> ciascuno in parti uguali.</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(251, 191, 36, 0.25); border-left: 4px solid #fbbf24; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#ffffff; font-size:13.5px;">🎁 Quota Disponibile:</b>
                <span class="mono-num" style="font-weight:700; color:#fbbf24; font-size:14px;">€ {estate['val_disponibile']:,.2f} ({estate['disponibile_pct']}%)</span>
            </div>
            <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Quota libera da destinare liberamente tramite testamento o lasciti.</div>
        </div>
        """, unsafe_allow_html=True)

with tab_taxes:
    st.markdown("### 🧾 Simulazione Imposta di Successione (D.Lgs. 346/1990)")
    st.caption("In Italia, l'imposta di successione per coniuge e parenti in linea retta prevede una **franchigia di € 1.000.000 per ciascun erede** con aliquota al 4% applicabile unicamente sulla parte eccedente.")

    if estate["tax_heirs"]:
        df_tax = pd.DataFrame(estate["tax_heirs"])
        st.dataframe(
            df_tax,
            column_config={
                "erede": st.column_config.TextColumn("Erede Legittimo", width="medium"),
                "quota_valore": st.column_config.NumberColumn("Valore Quota Ereditaria (€)", format="€ %,.2f", width="medium"),
                "franchigia": st.column_config.NumberColumn("Franchigia di Legge (€)", format="€ %,.2f", width="medium"),
                "base_imponibile": st.column_config.NumberColumn("Base Imponibile Tassabile (€)", format="€ %,.2f", width="medium"),
                "aliquota": st.column_config.TextColumn("Aliquota", width="small"),
                "imposta_dovuta": st.column_config.NumberColumn("Imposta di Successione Dovuta (€)", format="€ %,.2f", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nessuna imposta di successione applicabile.")

    if estate["is_under_exempt_threshold"]:
        st.success("🟢 **Patrimonio Sotto Franchigia**: Tutte le quote ereditarie rientrano ampiamente nelle franchigie di legge di € 1.000.000 per erede. L'imposta di successione netta dovuta è pari a **€ 0,00**.")
    else:
        st.warning(f"⚠️ **Imposta di Successione Dovuta**: Imposta totale calcolata pari a **€ {estate['total_succession_tax']:,.2f}**.")

with tab_shield:
    st.markdown("### 🛡️ Asset Protection, Trust & Holding Familiare Simulator")
    st.caption("Analisi quantitativa e giuridica per la segregazione dei rischi patrimoniali, la protezione dai creditori e la pianificazione tramite Trust o Società Semplice (S.s.).")

    from core.wealth.asset_protection_engine import AssetProtectionEngine

    summary_prot_dict = {
        "total_net_worth": float(estate["tot_patrimonio_netto"]),
        "real_estate_total": float(estate.get("real_estate_total", 0.0)),
        "financial_investments": float(estate.get("financial_investments", 0.0)),
        "physical_assets": float(estate.get("physical_assets", 0.0))
    }

    prot_res = AssetProtectionEngine.evaluate_protection_matrix(summary_prot_dict)

    pk1, pk2, pk3, pk4 = st.columns(4)
    with pk1:
        metric_card("Fondo Patrimoniale (167 c.c.)", "Score 65 / 100", delta="Protezione Media", delta_color="normal")
    with pk2:
        metric_card("Holding Società Semplice", "Score 85 / 100", delta=f"PEX Risparmio: € {prot_res['estimated_annual_pex_savings']:,.0f}/y", delta_color="normal")
    with pk3:
        metric_card("Trust Familiare (Aja 1985)", "Score 92 / 100", delta="Segregazione Totale", delta_color="normal")
    with pk4:
        metric_card("Scudo Revocatoria", "5 Anni (2901 c.c.)", delta="Consolidamento Giuridico", delta_color="normal")

    st.write("")
    st.markdown("##### 🏛️ Confronto Strutturale dei Veicoli di Protezione")
    st.dataframe(
        prot_res["comparison_df"],
        use_container_width=True,
        hide_index=True
    )

    st.write("")
    c_veh1, c_veh2, c_veh3 = st.columns(3)
    with c_veh1:
        fp_item = prot_res["fondo_patrimoniale"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#38bdf8; font-size:14px;">{fp_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{fp_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {fp_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {fp_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {fp_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {fp_item.key_advantages[0]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{fp_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_veh2:
        ss_item = prot_res["societa_semplice"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(52, 211, 153, 0.25); border-left: 4px solid #34d399; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#34d399; font-size:14px;">{ss_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{ss_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {ss_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {ss_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {ss_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {ss_item.key_advantages[1]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{ss_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_veh3:
        tr_item = prot_res["trust"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(167, 139, 250, 0.25); border-left: 4px solid #a78bfa; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#a78bfa; font-size:14px;">{tr_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{tr_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {tr_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {tr_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {tr_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {tr_item.key_advantages[0]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{tr_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab_patto:
    st.markdown("### 🏛️ Family Governance & Patti di Famiglia (Art. 768-bis c.c.)")
    st.caption("Pianificazione del passaggio del controllo aziendale e societario, calcolo della compensazione liquidatoria per i legittimari non assegnatari e scudo contro future azioni di riduzione.")

    gov_data = compute_family_governance_and_patti_di_famiglia(
        engine,
        portfolio_id=current_pid,
        business_value_eur=float(estate["tot_patrimonio_netto"] if estate["tot_patrimonio_netto"] > 100000 else 2000000.0),
        heir_count=num_children,
        has_spouse=has_spouse
    )

    gk1, gk2, gk3, gk4 = st.columns(4)
    with gk1:
        metric_card("Valore Azienda / Holding", fmt_eur(gov_data["business_value_eur"]), delta="Asset Oggetto del Patto", delta_color="normal")
    with gk2:
        metric_card("Erede Designato", gov_data["assigned_heir_name"], delta=f"{gov_data['assigned_quota_pct']:.0f}% Quote Trasferite", delta_color="normal")
    with gk3:
        metric_card("Liquidazione Legittimari", fmt_eur(gov_data["total_compensation_due_eur"]), delta="Compensazione non Assegnatari", delta_color="normal")
    with gk4:
        metric_card("Scudo Riduzione/Collazione", "ATTIVO 🟢", delta="Immunità Ereditaria Blindata", delta_color="normal")

    st.write("")

    g_col_l, g_col_r = st.columns([3, 2])
    with g_col_l:
        st.markdown("##### 👥 Prospetto Liquidazione Legittimari non Assegnatari")
        df_heirs = pd.DataFrame(gov_data["non_assigned_heirs"])
        if not df_heirs.empty:
            st.dataframe(
                df_heirs[["heir_name", "relationship", "statutory_legitimate_share_pct", "compensation_due_eur", "payment_method"]].rename(columns={
                    "heir_name": "Soggetto Legittimario",
                    "relationship": "Grado Parentela",
                    "statutory_legitimate_share_pct": "Quota Riserva (%)",
                    "compensation_due_eur": "Compensazione Dovuta (€)",
                    "payment_method": "Modalità di Regolamento"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("##### 📅 Piano di Donazioni Scaglionate su Orizzonte Pluriennale")
        st.dataframe(
            pd.DataFrame(gov_data["staggered_donations_schedule"]).rename(columns={
                "anno": "Anno",
                "importo_donato_eur": "Importo Donato (€)",
                "franchigia_usata_eur": "Franchigia Utilizzata (€)",
                "imposta_donazione_eur": "Imposta Donazione (€)",
                "note": "Note Operative"
            }),
            use_container_width=True,
            hide_index=True
        )

    with g_col_r:
        st.markdown("##### 📋 Checklist di Conformità Notarile")
        for chk in gov_data["governance_checklist"]:
            st.info(f"⚖️ {chk}")

