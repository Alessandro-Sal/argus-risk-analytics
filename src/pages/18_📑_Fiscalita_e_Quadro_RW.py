# ============================================================
# 18_📑_Fiscalita_e_Quadro_RW.py
# ARGUS Wealth — Fiscalità, Minusvalenze & Monitoraggio Quadro RW / RT
# ============================================================

import importlib
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import core.ui_utils
import core.wealth
import core.wealth.wealth_db
import core.wealth.wealth_engine

importlib.reload(core.ui_utils)
importlib.reload(core.wealth.wealth_db)
importlib.reload(core.wealth.wealth_engine)
importlib.reload(core.wealth)

from core.cross_border_tax_engine import (
    compute_cross_border_wealth_tax_comparison,
    get_international_tax_jurisdictions,
)
from core.crypto_tax_engine import compute_crypto_tax_report
from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.tax_engine import (
    compute_modello_redditi_pf,
    compute_riforma_fiscale_comparison,
    compute_tax_loss_harvesting_strategy,
    compute_zainetto_timeline,
)
from core.ui_lifecycle import teardown_view_state
from core.ui_utils import (
    apply_plotly_theme,
    ensure_portfolio_loaded,
    fmt_eur,
    fmt_pct,
    inject_custom_css,
    metric_card,
    render_institutional_telemetry_ribbon,
    render_page_header,
    render_segmented_tabs,
    render_sr117_audit_drawer,
    render_table_with_export,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_wealth_telemetry_ribbon,
    resolve_active_subtab,
    section,
)
from core.wealth.tax_history_engine import (
    compute_crypto_tax_reporting,
    compute_fiscal_reform_2026_etf_harmonization,
)
from core.wealth.tax_history_ui import render_tax_history_tab
from core.wealth.wealth_db import get_wealth_portfolios, init_wealth_db
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_fiscal_analytics,
    compute_tax_loss_harvesting_and_latent_taxes,
)

st.set_page_config(page_title="Fiscalità & Quadro RW | ARGUS Wealth", page_icon="📑", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_name = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
st.session_state.wealth_db_name = db_name
st.session_state.db_name = db_name
offline_mode = bool(st.session_state.get("offline_mode", False))
db_port = int(st.session_state.get("db_port", 3306))

engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)
init_wealth_db(engine)

ensure_portfolio_loaded(module_type="wealth")

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    current_pid = None
    st.session_state["wealth_active_portfolio_id"] = None
    from core.ui_utils import render_wealth_profile_picker
    render_wealth_profile_picker(engine, prof_map, key_prefix="p18_picker")
    st.stop()

# ── ATOMIC STATE TEARDOWN ───────────────────────────────────
teardown_view_state(current_pid, active_page="18_Fiscalita_e_Quadro_RW")

prof_title = prof_map.get(current_pid, "Nessun Profilo")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p18")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_telemetry_ribbon(nw_summary=nw_curr, page_badge="FISCALITÀ & QUADRO RW", profile_name=prof_title)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Fiscalità Istituzionale, Quadro RW & Tax Optimization",
    subtitle="Calcolo automatico IVAFE (0,20%), Imposta di Bollo, Zainetto Minusvalenze, Cripto-Attività (L. 197/2022) e Dichiarazioni 730/Redditi PF.",
    icon="📑"
)

from core.wealth.wealth_modals import render_fiscal_methodology_modal

col_fisc_h1, col_fisc_h2 = st.columns([3.5, 1.2])
with col_fisc_h1:
    if len(prof_map) > 1:
        if current_pid in prof_map and st.session_state.get("fiscal_profile_selector_widget") != current_pid:
            st.session_state["fiscal_profile_selector_widget"] = current_pid
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="fiscal_profile_selector_widget",
        )
        if sel_pid != current_pid:
            from core.workspace_context import WorkspaceContext
            WorkspaceContext.set_active_workspace(sel_pid)
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.session_state["argus_active_portfolio_id"] = sel_pid
            st.rerun()
with col_fisc_h2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("📘 Metodologia di Calcolo Fiscale", use_container_width=True, key="btn_fisc_method"):
        render_fiscal_methodology_modal()

# Calcolo Dati Fiscali Consolidati
fiscal = compute_fiscal_analytics(engine, portfolio_id=current_pid)

# ── TOP KPI ROW FISCALITÀ ──────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(
        "Zainetto Minusvalenze",
        fmt_eur(fiscal["total_active_losses"]),
        delta="Credito Fiscale Attivo (4Y)",
        delta_color="normal",
        help_text="Minusvalenze complessive ancora compensabili entro il quadriennio fiscale solare (Art. 68 TUIR)."
    )
with c2:
    metric_card(
        "Risparmio Potenziale 26%",
        fmt_eur(fiscal["total_tax_shield_eur"]),
        delta="Scudo Fiscale Totale",
        delta_color="normal",
        help_text="Controvalore effettivo delle imposte risparmiabili mediante compensazione delle minusvalenze con plusvalenze future."
    )
with c3:
    urgent_lbl = f"{fmt_eur(fiscal['urgent_losses_amount'])} In Decadenza" if fiscal['urgent_losses_amount'] > 0 else "Nessuna Urgenza"
    metric_card(
        "Minusvalenze in Scadenza",
        fmt_eur(fiscal["urgent_losses_amount"]),
        delta=urgent_lbl,
        delta_color="inverse" if fiscal['urgent_losses_amount'] > 0 else "normal",
        help_text="Quota parte dello stock minusvalenze in scadenza definitiva al 31 dicembre dell'anno solare corrente."
    )
with c4:
    metric_card(
        "Imposte Patrimoniali Totali",
        fmt_eur(fiscal["estimated_annual_fiscal_cost"]),
        delta=f"Bollo IT: {fmt_eur(fiscal['total_bollo'])} | IVAFE: {fmt_eur(fiscal['total_ivafe'])}",
        delta_color="inverse",
        help_text="Carico fiscale patrimoniale annuo stimato: Imposta di Bollo (0,20% su dossier italiani) + IVAFE (0,20% su broker e conti esteri)."
    )

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── I 4 PILASTRI FISCALI UNIFICATI (LAZY-LOADED) ───────────────
WEALTH_TAX_MODELS_CATALOG = {
    "💼 Zainetto Fiscale, Capital Gain & Riforma 2026": {
        "title": "Zainetto Minusvalenze, Capital Gain, White List (12,5%) & Riforma 2026",
        "badge": "Zainetto 4Y • TUIR Art. 67 • Armonizzazione 2026",
        "badge_color": "#f85149",
        "category": "Compensazione & Capital Gain",
        "desc": "Stock minusvalenze quadriennale, asimmetria Redditi di Capitale (ETF) vs Diversi (Azioni/ETC/Bond), White List al 12,5%, Tax-Loss Harvesting e simulatore della Riforma Tributaria 2026.",
    },
    "🌍 Simulatore Quadro RW / IVAFE & Conti Esteri": {
        "title": "Prospetto Monitoraggio Fiscale (Quadro RW), IVAFE & Structuring Cross-Border",
        "badge": "Quadro RW • IVAFE 0,20% • DTT Esteri",
        "badge_color": "#10b981",
        "category": "Monitoraggio Internazionale",
        "desc": "Attività estere, conti correnti esteri (soglie €5k/€15k), calcolo IVAFE e confronto quantitativo del carico fiscale su giurisdizioni internazionali (Svizzera, Lussemburgo, UAE, Art. 24-bis).",
    },
    "₿ Fiscalità Crypto (L. 197/2022) & Soglie": {
        "title": "Liquidazione Fiscale Cripto-Attività, Quadro RT Sez. II-B & Soglia € 2.000",
        "badge": "L. 197/2022 • Franchigia 2k • Bollo Virtuale 2‰",
        "badge_color": "#f59e0b",
        "category": "Digital Assets",
        "desc": "Verifica della soglia di franchigia di € 2.000 per le plusvalenze cripto (26%), monitoraggio Quadro RW Codice 21 (self-custody ed exchange), imposta di bollo virtuale del 2‰ e zainetto cripto separato.",
    },
    "📑 Storico Dichiarazioni 730, IRPEF & Audit": {
        "title": "Archivio Storico Dichiarazioni (730 / Redditi PF), Alert Art. 36-bis & Triangolazione",
        "badge": "Modello 730 • Redditi PF • Audit Fiscale",
        "badge_color": "#38bdf8",
        "category": "Dichiarazione & Audit",
        "desc": "Archivio storico dei modelli 730 e Redditi PF, importazione PDF/JSON, alert su anomalie art. 36-bis D.P.R. 600/73 e riconciliazione automatica con le contabili broker.",
    },
}

active_tax_tab = render_segmented_tabs(
    WEALTH_TAX_MODELS_CATALOG,
    key="wealth_tax_active_tab",
    select_label="Seleziona Modulo Fiscale:",
)


# ============================================================
# TAB 1: ZAINETTO FISCALE, CAPITAL GAIN & RIFORMA 2026
# ============================================================
@st.fragment
def _render_tab_zainetto_and_reform():
    st.markdown("### 💼 Zainetto Fiscale, Capital Gain TUIR & Armonizzazione 2026")
    st.caption("Disciplina asimmetrica TUIR (Art. 67 e 68): distinzione tra Redditi di Capitale (ETF non compensabili) e Redditi Diversi (Azioni, ETC, Obbligazioni), White List 12,50% e simulatore Riforma 2026.")

    # 1. Timeline Scadenza Minusvalenze
    st.markdown("#### ⏳ Stock Minusvalenze & Calendario di Decadenza Quinquennale")
    col_m1, col_m2 = st.columns([3, 2])
    with col_m1:
        df_min = pd.DataFrame(fiscal["minusvalenze_schedule"])
        fig_min = go.Figure()
        fig_min.add_trace(go.Bar(
            x=[f"Origine {r['anno_origine']} (Scad. {r['scadenza']})" for _, r in df_min.iterrows()],
            y=df_min["importo"],
            text=[f"€ {val:,.2f}" for val in df_min["importo"]],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Minusvalenza: <b>€ %{y:,.2f}</b><extra></extra>",
            marker_color=["#ef4444" if "Quest'Anno" in r["stato"] else "#f59e0b" for _, r in df_min.iterrows()]
        ))
        fig_min.update_layout(
            title=dict(text="Distribuzione Temporale Minusvalenze Pregresse", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_min, use_container_width=True, config={'displayModeBar': False})

    with col_m2:
        st.markdown("##### ⏳ Dettaglio Scadenze e Urgenza")
        for m in fiscal["minusvalenze_schedule"]:
            color = "#ef4444" if "Quest'Anno" in m["stato"] else "#34d399"
            bg = "rgba(239, 68, 68, 0.12)" if "Quest'Anno" in m["stato"] else "rgba(16, 185, 129, 0.10)"
            st.markdown(f"""
            <div style="background:{bg}; border-left: 4px solid {color}; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between;">
                    <b>Anno {m['anno_origine']} &rarr; Scadenza: {m['scadenza']}</b>
                    <span style="color:{color}; font-weight:800;">€ {m['importo']:,.2f}</span>
                </div>
                <div style="font-size: 11.5px; color: #94a3b8;">Stato: {m['stato']} &bull; Risparmio potenziale: <b>€ {m['importo'] * 0.26:,.2f}</b></div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.divider()

    # 2. Tax-Loss Harvesting & Debito Fiscale Latente
    st.markdown("#### 🌾 Tax-Loss Harvesting Proattivo & Debito Fiscale Latente")
    st.caption("Quantificazione del debito fiscale teorico da liquidazione totale e identificazione di minusvalenze latenti da monetizzare a compensazione.")

    tlh = compute_tax_loss_harvesting_and_latent_taxes(engine, portfolio_id=current_pid)
    th1, th2, th3, th4 = st.columns(4)
    with th1:
        metric_card("Imposte Latenti da Realizzo", fmt_eur(tlh["total_latent_tax_liability"]), delta="Debito Fiscale Teorico", delta_color="inverse")
    with th2:
        metric_card("Patrimonio Reale Post-Tax", fmt_eur(tlh["net_worth_post_latent_tax"]), delta="Net Worth al Netto Tasse", delta_color="normal")
    with th3:
        metric_card("Minusvalenze Latenti nei Dossier", fmt_eur(tlh["total_unrealized_losses"]), delta="Potenziale Harvesting", delta_color="normal")
    with th4:
        metric_card("Scudo Fiscale Recuperabile", fmt_eur(tlh["tax_shield_recoverable"]), delta="Risparmio 26%", delta_color="normal")

    st.write("")
    st.divider()

    # 3. Asimmetria Fiscale TUIR & White List 12,5%
    section("⚖️ Asimmetria Fiscale TUIR (Redditi di Capitale vs Diversi) & White List")
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-top: 10px;">
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #ef4444; border-radius: 10px; padding: 16px 18px;">
            <div style="color: #ef4444; font-weight: 750; font-size: 14px; margin-bottom: 6px;">❌ Redditi di Capitale (Non Compensabili)</div>
            <div style="font-size: 12.5px; color: #c9d1d9; line-height: 1.5;">
                • <b>ETF / OICR UCITS</b>: Le plusvalenze sono tassate al 26% come redditi di capitale e <u>non</u> possono essere usate per assorbire lo zainetto fiscale pregresso.<br>
                • <b>Dividendi azionari</b>: Tassati alla fonte con ritenuta a titolo d'imposta del 26%.
            </div>
        </div>
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #10b981; border-radius: 10px; padding: 16px 18px;">
            <div style="color: #10b981; font-weight: 750; font-size: 14px; margin-bottom: 6px;">✅ Redditi Diversi (Compensano lo Zainetto)</div>
            <div style="font-size: 12.5px; color: #c9d1d9; line-height: 1.5;">
                • <b>Singole Azioni</b>: Plusvalenze da cessione compensabili integralmente.<br>
                • <b>ETC / ETN su Materie Prime</b>: Considerati contratti aperti (redditi diversi) e adatti al recupero minus.<br>
                • <b>Certificates con Cedola Incondizionata / Maxi-Cedola</b>: Strumento primario di tax planning.
            </div>
        </div>
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 16px 18px;">
            <div style="color: #38bdf8; font-weight: 750; font-size: 14px; margin-bottom: 6px;">🏛️ White List Titoli di Stato (Aliquota 12,50%)</div>
            <div style="font-size: 12.5px; color: #c9d1d9; line-height: 1.5;">
                • Rendimenti di <b>BTP, BOT, CCT</b> e Titoli Sovrani UE/OCSE tassati al <b>12,50%</b> (risparmio di 13,5 punti percentuali vs 26%).<br>
                • <u>Totale esenzione da Imposta di Successione</u> (Art. 12 D.Lgs. 346/1990).
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.divider()

    # 4. Simulatore Riforma Fiscale 2026
    section("🏛️ Simulatore Riforma Fiscale 2026: Armonizzazione ETF & Superamento Asimmetria")
    st.caption("La delega fiscale approvata dal Parlamento prevede la convergenza in un'unica categoria di redditi finanziari: le plusvalenze da ETF potranno finalmente compensare le minusvalenze pregresse.")

    col_rf1, col_rf2 = st.columns([2, 2])
    with col_rf1:
        etf_sim_val = st.number_input(
            "Plusvalenze ETF da Realizzare Simulate (€):",
            min_value=0.0,
            value=float(min(nw_curr.financial_investments * 0.15, 25000.0) if nw_curr.financial_investments > 0 else 5000.0),
            step=1000.0,
            key=f"p18_rf_etf_{current_pid}",
        )
    with col_rf2:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        use_port_pos = st.checkbox("Carica plusvalenze effettive dal portafoglio", value=True, key=f"p18_rf_chk_{current_pid}")

    rf_res = compute_fiscal_reform_2026_etf_harmonization(
        engine,
        profile_id=str(current_pid),
        tax_year=datetime.now().year - 1,
        simulated_etf_gain=None if use_port_pos else etf_sim_val,
    )

    c_rf_k1, c_rf_k2, c_rf_k3, c_rf_k4 = st.columns(4)
    with c_rf_k1:
        metric_card("Plusvalenze ETF Rilevate", fmt_eur(rf_res["etf_unrealized_gains"]), "Base Imponibile")
    with c_rf_k2:
        metric_card("Zainetto Minusvalenze", fmt_eur(rf_res["total_active_losses"]), "Capitale Compensabile")
    with c_rf_k3:
        metric_card("Tax Alpha Riforma 2026", f"+{fmt_eur(rf_res['immediate_tax_alpha_eur'])}", delta=f"-{rf_res['delta_tax_pct_points']:.1f}% Aliquota Reale", delta_color="normal")
    with c_rf_k4:
        metric_card("Assorbimento Minus", f"{rf_res['reform_2026_regime']['loss_absorption_pct']:.1f}%", "Compensato con ETF", delta_color="normal")

    st.info(f"💡 **Verdetto Strategico ARGUS:** {rf_res['strategic_advice']}")


# ============================================================
# TAB 2: SIMULATORE QUADRO RW, IVAFE & CONTI ESTERI
# ============================================================
@st.fragment
def _render_tab_quadro_rw():
    st.markdown("### 🌍 Monitoraggio Fiscale (Quadro RW), IVAFE & Structuring Cross-Border")
    st.caption("Prospetto analitico delle consistenze estere, giacenze medie, picchi massimi, liquidazione IVAFE (2‰) e confronto comparativo con giurisdizioni fiscali globali.")

    # 1. Prospetto Quadro RW Intermediari Esteri
    if fiscal["quadro_rw_rows"]:
        df_rw = pd.DataFrame(fiscal["quadro_rw_rows"])
        rw_cfg = {
            "rigo": st.column_config.TextColumn("Rigo RW", width="small"),
            "descrizione": st.column_config.TextColumn("Descrizione / Intermediario", width="large"),
            "codice_investimento": st.column_config.NumberColumn("Cod. Investimento", width="small"),
            "codice_stato_estero": st.column_config.TextColumn("Paese Estero", width="medium"),
            "giacenza_media": st.column_config.NumberColumn("Giacenza Media (€)", format="€ %,.2f", width="medium"),
            "valore_massimo": st.column_config.NumberColumn("Picco Max (€)", format="€ %,.2f", width="medium"),
            "valore_finale": st.column_config.NumberColumn("Valore al 31/12 (€)", format="€ %,.2f", width="medium"),
            "ivafe_dovuta": st.column_config.NumberColumn("IVAFE Dovuta (€)", format="€ %,.2f", width="medium"),
            "monitoraggio_solo": st.column_config.TextColumn("Monitoraggio", width="medium")
        }
        render_table_with_export(
            df=df_rw,
            table_title="Quadro RW (Monitoraggio Attività Finanziarie Estere)",
            file_prefix=f"argus_quadro_rw_{current_pid}",
            key_suffix=f"p18_rw_{current_pid}",
            column_config=rw_cfg,
            hide_index=True
        )
    else:
        st.info("ℹ️ Nessuna posizione su broker esteri o wallet esteri rilevata per questo profilo.")

    st.write("")
    st.divider()

    # 2. Asset Location (Italia vs Estero) & Bollo IT vs IVAFE
    section("⚖️ Asset Location & Confronto Imposte Patrimoniali Ricorrenti")
    tot_fisc_assets = fiscal["total_domestic_assets"] + fiscal["total_foreign_assets"]
    cs1, cs2 = st.columns([1.1, 1.2])
    with cs1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Dossier Italia (Amministrato)", "Conti & Broker Estero (Dichiarativo)"],
            values=[fiscal["total_domestic_assets"], fiscal["total_foreign_assets"]],
            hole=0.60,
            marker_colors=["#3b82f6", "#10b981"],
            textinfo="percent",
            textposition="inside"
        )])
        fig_pie.update_layout(
            title=dict(text="Ripartizione Geografica del Patrimonio", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(l=10, r=10, t=40, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<span style='font-size:11px; color:#94a3b8;'>TOTALE</span><br><b style='font-size:14px; color:#ffffff;'>€ {tot_fisc_assets:,.0f}</b>",
                x=0.5, y=0.5, font_size=12, showarrow=False
            )]
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

    with cs2:
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 16px 18px;">
            <div style="font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 6px;">
                🏛️ Riepilogo Imposte Patrimoniali
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 8px 0; color: #e2e8f0;">Dossier Italia (Regime Amministrato):</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #ffffff;">{fmt_eur(fiscal['total_domestic_assets'])}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 8px 0 8px 16px; color: #94a3b8; font-size: 12px;">• Imposta di Bollo IT (0,20%):</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #38bdf8;">{fmt_eur(fiscal['total_bollo'])}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 8px 0; color: #e2e8f0;">Dossier Estero (Regime Dichiarativo):</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #ffffff;">{fmt_eur(fiscal['total_foreign_assets'])}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.08);">
                    <td style="padding: 8px 0 8px 16px; color: #94a3b8; font-size: 12px;">• IVAFE Estero (0,20%):</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #34d399;">{fmt_eur(fiscal['total_ivafe'])}</td>
                </tr>
                <tr style="font-weight: 800;">
                    <td style="padding: 10px 0; color: #f8fafc;">Totale Imposte Patrimoniali:</td>
                    <td style="padding: 10px 0; text-align: right; color: #fbbf24; font-size: 15px;">{fmt_eur(fiscal['estimated_annual_fiscal_cost'])}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.divider()

    # 3. Cross-Border Wealth Tax Comparison
    section("🌍 Global Wealth Structuring & Benchmark Giurisdizioni Estere")
    st.caption("Confronto del carico tributario aggregato (Capital Gain, Dividendi, Imposta sulla Sostanza e Successione) simulando una riallocazione internazionale.")

    cb_c1, cb_c2, cb_c3 = st.columns(3)
    with cb_c1:
        cb_wealth_in = st.number_input("Patrimonio Complessivo Simulato (€):", min_value=100000.0, value=float(max(nw_curr.total_net_worth, 500000.0)), step=100000.0, format="%.2f")
    with cb_c2:
        cb_cgt_in = st.number_input("Plusvalenze Realizzate Annue (€):", min_value=0.0, value=float(max(nw_curr.total_net_worth * 0.05, 25000.0)), step=10000.0, format="%.2f")
    with cb_c3:
        cb_div_in = st.number_input("Dividendi & Rendite Estere (€/a):", min_value=0.0, value=float(max(nw_curr.total_net_worth * 0.02, 10000.0)), step=5000.0, format="%.2f")

    cb_res = compute_cross_border_wealth_tax_comparison(
        total_wealth_eur=cb_wealth_in,
        annual_capital_gain_eur=cb_cgt_in,
        annual_foreign_income_eur=cb_div_in
    )

    cb_k1, cb_k2, cb_k3 = st.columns(3)
    with cb_k1:
        metric_card("Giurisdizione Ottimale", cb_res["lowest_tax_jurisdiction"], delta="Minimo Carico Fiscale Globale", delta_color="normal")
    with cb_k2:
        metric_card("Risparmio Annuo vs IT Ordinaria", fmt_eur(cb_res["max_annual_tax_savings_eur"]), delta="Tax Alpha Internazionale", delta_color="normal")
    with cb_k3:
        metric_card("Patrimonio Base", fmt_eur(cb_res["simulated_wealth_eur"]), delta="Asset Base Simulati", delta_color="normal")

    st.write("")
    st.dataframe(
        cb_res["comparison_df"][["name", "annual_cgt_eur", "annual_income_tax_eur", "annual_wealth_tax_eur", "total_annual_tax_eur", "effective_annual_tax_rate_pct", "estimated_estate_succession_tax_eur"]].rename(columns={
            "name": "Giurisdizione Fiscale",
            "annual_cgt_eur": "CGT (€)",
            "annual_income_tax_eur": "Dividendi (€)",
            "annual_wealth_tax_eur": "Patrimoniale (€)",
            "total_annual_tax_eur": "Totale Annue (€)",
            "effective_annual_tax_rate_pct": "Aliquota Effettiva (%)",
            "estimated_estate_succession_tax_eur": "Successione (€)"
        }),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 3: FISCALITÀ CRYPTO & SOGLIE (L. 197/2022)
# ============================================================
@st.fragment
def _render_tab_crypto():
    st.markdown("### ₿ Fiscalità Cripto-Attività (Legge di Bilancio 197/2022)")
    st.caption("Disciplina tributaria completa ex Art. 67 co. 1 lett. c-sexies TUIR: verifica della soglia di franchigia a € 2.000, imposta sostitutiva del 26%, monitoraggio Quadro RW Codice 21 e imposta di bollo virtuale del 2‰.")

    # 1. Calcolo Prospetto Cripto Integrato
    crypto_res = compute_crypto_tax_report({}, db_engine=engine, tax_year=datetime.now().year - 1)
    crypto_data_legacy = compute_crypto_tax_reporting(engine, profile_id=str(current_pid), tax_year=datetime.now().year - 1)
    c_summary = crypto_res.get("summary", {})

    bal_3112 = c_summary.get("total_crypto_portfolio_val_eur") or crypto_data_legacy.get("crypto_balance_31_12", 0.0)
    gains = c_summary.get("total_realized_gains_eur") or 0.0
    sost_tax = c_summary.get("total_tax_due_rt_eur") or crypto_data_legacy.get("substitute_tax_26pct", 0.0)
    bollo_virt = c_summary.get("total_ivafe_rw_eur") or crypto_data_legacy.get("imposta_valore_crypto_2_permille", 0.0)

    # Verifica Soglia 2.000 €
    is_above_threshold = gains >= 2000.0
    thresh_status = f"🔴 Superata ({fmt_eur(gains)})" if is_above_threshold else f"🟢 Esente ({fmt_eur(gains)} < € 2.000)"

    cr_k1, cr_k2, cr_k3, cr_k4 = st.columns(4)
    with cr_k1:
        metric_card("Controvalore al 31/12", fmt_eur(bal_3112), delta="Consistenza Quadro RW", delta_color="normal")
    with cr_k2:
        metric_card("Plusvalenze Nette Realizzate", fmt_eur(gains), delta=thresh_status, delta_color="inverse" if is_above_threshold else "normal")
    with cr_k3:
        metric_card("Sostitutiva 26% (RT Sez. II-B)", fmt_eur(sost_tax), delta="Tributo F24 1715", delta_color="inverse")
    with cr_k4:
        metric_card("Bollo Virtuale 2‰ (RW)", fmt_eur(bollo_virt), delta="Tributo F24 1727", delta_color="inverse")

    st.write("")
    st.divider()

    # Normativa & Linee Guida
    st.markdown("""
    <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #f59e0b; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;">
        <div style="font-weight: 700; color: #f59e0b; font-size: 13.5px; margin-bottom: 4px;">📌 Principali Regole Fiscali Cripto (L. 197/2022)</div>
        <div style="font-size: 12px; color: #c9d1d9; line-height: 1.5;">
            1. <b>Soglia di Esenzione € 2.000</b>: Le plusvalenze realizzate complessivamente nel periodo d'imposta non concorrono alla formazione del reddito se inferiori a 2.000 euro. Se la soglia viene superata anche di 1 euro, la tassazione al 26% si applica sull'<u>intero importo</u>.<br>
            2. <b>Zainetto Minusvalenze Cripto Separato</b>: Le minusvalenze cripto eccedenti 2.000 euro possono essere portate in deduzione nei 4 anni successivi, ma <u>esclusivamente</u> contro plusvalenze da cripto-attività (non compensabili con azioni/ETF).<br>
            3. <b>Crypto-to-Crypto Esente</b>: La permuta tra cripto-attività aventi medesime caratteristiche non costituisce realizzo di plusvalenza.<br>
            4. <b>Imposta di Bollo Virtuale (2‰)</b>: Si applica annualmente sul valore di mercato al 31/12 di tutte le cripto detenute su wallet esteri o in cold storage.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabelle RT ed RW
    col_crt1, col_crt2 = st.columns(2)
    with col_crt1:
        st.markdown("##### 📋 Quadro RW — Monitoraggio Cripto & Cold Storage (Cod. 21)")
        df_rw_cr = pd.DataFrame(crypto_data_legacy.get("quadro_rw_rows", []))
        if not df_rw_cr.empty:
            st.dataframe(df_rw_cr, hide_index=True, use_container_width=True)
        else:
            st.info("Nessuna riga RW cripto registrata.")
    with col_crt2:
        st.markdown("##### 📈 Quadro RT Sez. II-B — Plusvalenze / Minusvalenze")
        df_rt_cr = pd.DataFrame(crypto_data_legacy.get("quadro_rt_rows", []))
        if not df_rt_cr.empty:
            st.dataframe(df_rt_cr, hide_index=True, use_container_width=True)
        else:
            st.info("Nessuna riga RT cripto registrata.")


# ============================================================
# TAB 4: STORICO DICHIARAZIONI 730, IRPEF & AUDIT
# ============================================================
@st.fragment
def _render_tab_history_730():
    render_tax_history_tab(engine, current_pid)


# ── ROUTING INTERNO DELLE SCHEDE ─────────────────────────────
if active_tax_tab == "💼 Zainetto Fiscale, Capital Gain & Riforma 2026":
    _render_tab_zainetto_and_reform()
elif active_tax_tab == "🌍 Simulatore Quadro RW / IVAFE & Conti Esteri":
    _render_tab_quadro_rw()
elif active_tax_tab == "₿ Fiscalità Crypto (L. 197/2022) & Soglie":
    _render_tab_crypto()
elif active_tax_tab == "📑 Storico Dichiarazioni 730, IRPEF & Audit":
    _render_tab_history_730()

render_sr117_audit_drawer(engine, model_name="ARGUS Unified Wealth Tax & RW Engine", audit_metrics=fiscal)
