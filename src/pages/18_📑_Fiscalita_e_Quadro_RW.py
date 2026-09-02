# ============================================================
# 18_📑_Fiscalita_e_Quadro_RW.py
# ARGUS Wealth — Fiscalità, Minusvalenze & Monitoraggio Quadro RW / RT
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
from core.wealth.wealth_db import get_wealth_portfolios
from core.wealth.wealth_engine import (
    compute_fiscal_analytics,
    compute_consolidated_net_worth,
    compute_tax_loss_harvesting_and_latent_taxes
)


st.set_page_config(page_title="Fiscalità & Quadro RW | ARGUS Wealth", page_icon="📑", layout="wide")
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
    st.title("📑 ARGUS Wealth — Fiscalità & Quadro RW / RT")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per calcolare l'IVAFE, l'Imposta di Bollo e lo Zainetto Fiscale.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="fiscal_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p18")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Fiscalità, Quadro RW & Tax-Loss Harvesting",
    subtitle="Calcolo automatico IVAFE (0,20%), Imposta di Bollo, Zainetto Minusvalenze, Tax-Loss Harvesting e Prospetto Fiscale.",
    icon="📑"
)

from core.wealth.wealth_modals import render_fiscal_methodology_modal

col_fisc_h1, col_fisc_h2 = st.columns([3.5, 1.2])
with col_fisc_h1:
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="fiscal_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()

with col_fisc_h2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("ℹ️ Guida Quadro RW & TUIR", key="btn_modal_fisc_p18", use_container_width=True):
        render_fiscal_methodology_modal()

fiscal = compute_fiscal_analytics(engine, portfolio_id=current_pid)

# ── TOP KPI ROW ─────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    metric_card("IVAFE Estero", fmt_eur(fiscal['total_ivafe']), delta="Dossier & C/C Esteri", help_text="Imposta sul valore delle attività finanziarie detenute all'estero (0,20% su dossier esteri + € 34,20 su c/c con giacenza > € 5k).")
with k2:
    metric_card("Imposta Bollo IT", fmt_eur(fiscal['total_bollo']), delta="0.20% + C/C Italia", help_text="0,20% proporzionale su dossier titoli italiani + € 34,20 su c/c italiani con giacenza > € 5k.")
with k3:
    metric_card("Zainetto Minus", fmt_eur(fiscal['total_minusvalenze']), delta="Recuperabili 4 Anni", delta_color="inverse", help_text="Minusvalenze pregresse totali ancora compensabili entro i 4 anni solari successivi.")
with k4:
    metric_card("Scudo Fiscale", fmt_eur(fiscal['tax_shield_potential']), delta="Credito d'Imposta 26%", delta_color="normal", help_text="Valore effettivo del risparmio fiscale recuperabile compensando le minusvalenze.")
with k5:
    metric_card("Costo Fiscale Annuo", fmt_eur(fiscal['estimated_annual_fiscal_cost']), delta="Drag Fiscale Totale", delta_color="inverse", help_text="Somma complessiva di IVAFE e Bollo su base annuale.")


st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab_rw, tab_minus, tab_harvest, tab_split, tab_strat, tab_cross = st.tabs([
    "📑 Prospetto Quadro RW / RT",
    "📉 Zainetto Fiscale & Scadenze",
    "🌾 Tax-Loss Harvesting & Plusvalenze",
    "⚖️ Ripartizione Italia vs Estero",
    "💡 Strategie di Efficienza Fiscale",
    "🌍 Fiscalità Internazionale & Cross-Border"
])


with tab_rw:
    st.markdown("### 📑 Prospetto di Monitoraggio Fiscale (Quadro RW & RT)")
    st.caption("Quadro riassuntivo per la compilazione del Modello Redditi PF o trasmissione al commercialista per le attività finanziarie e conti esteri.")
    
    if fiscal["quadro_rw_rows"]:
        df_rw = pd.DataFrame(fiscal["quadro_rw_rows"])
        
        st.dataframe(
            df_rw,
            column_config={
                "rigo": st.column_config.TextColumn("Rigo RW", width="small"),
                "descrizione": st.column_config.TextColumn("Descrizione / Intermediario", width="large"),
                "codice_investimento": st.column_config.NumberColumn("Cod. Investimento", width="small"),
                "codice_stato_estero": st.column_config.TextColumn("Paese Estero", width="medium"),
                "valore_finale": st.column_config.NumberColumn("Valore al 31/12 (€)", format="€ %,.2f", width="medium"),
                "ivafe_dovuta": st.column_config.NumberColumn("IVAFE Dovuta (€)", format="€ %,.2f", width="medium"),
                "monitoraggio_solo": st.column_config.TextColumn("Solo Monitoraggio", width="small")
            },
            hide_index=True,
            use_container_width=True
        )

        st.write("")
        c_export, c_note = st.columns([1.3, 2.7])
        with c_export:
            csv_data = df_rw.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Scarica CSV Quadro RW",
                data=csv_data,
                file_name=f"argus_quadro_rw_portfolio_{current_pid}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c_note:
            st.info("💡 **Nota Normativa**: I conti correnti esteri con giacenza media annua inferiore a € 5.000 e picco massimo non superiore a € 15.000 non richiedono versamento IVAFE.")
    else:
        st.info("Nessuna attività finanziaria estera o crypto identificata per questo profilo patrimoniale.")


with tab_minus:
    st.markdown("### 📉 Monitoraggio Zainetto Fiscale & Scadenza Minusvalenze (Art. 68 TUIR)")
    st.caption("Le minusvalenze realizzate hanno una durata di validità di 4 anni solari oltre all'anno di realizzo. Se non compensate entro il 31 dicembre del 4° anno, decadono definitivamente.")
    
    col_m1, col_m2 = st.columns([3, 2])
    with col_m1:
        df_min = pd.DataFrame(fiscal["minusvalenze_schedule"])
        fig_min = go.Figure()
        fig_min.add_trace(go.Bar(
            x=[f"Anno {r['anno_origine']} (Scad. {r['scadenza']})" for _, r in df_min.iterrows()],
            y=df_min["importo"],
            text=[f"€ {val:,.2f}" for val in df_min["importo"]],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Minusvalenza: <b>€ %{y:,.2f}</b><extra></extra>",
            marker_color=["#ef4444" if "Quest'Anno" in r["stato"] else "#f59e0b" for _, r in df_min.iterrows()]
        ))
        fig_min.update_layout(
            title=dict(text="Distribuzione Temporale Minusvalenze", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=10, r=10, t=50, b=10)
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

with tab_harvest:
    st.markdown("### 🌾 Tax-Loss Harvesting & Gestione Plusvalenze Latenti")
    st.caption("Ottimizzazione quantitativa del carico fiscale: calcolo del debito fiscale latente da liquidazione e strategie di compensazione minusvalenze prima del 31 dicembre.")

    tlh = compute_tax_loss_harvesting_and_latent_taxes(engine, portfolio_id=current_pid)

    th1, th2, th3, th4 = st.columns(4)
    with th1:
        metric_card("Imposte Latenti", fmt_eur(tlh["total_latent_tax_liability"]), delta="Debito Fiscale Teorico", delta_color="inverse", help_text="Imposte complessive stimate in caso di liquidazione integrale delle posizioni in plusvalenza (26% su azioni/crypto/ETF + 12.5% su titoli di stato).")
    with th2:
        metric_card("Patrimonio Reale Netto", fmt_eur(tlh["net_worth_post_latent_tax"]), delta="Net Worth Post-Tasse", delta_color="normal", help_text="Valore effettivo del patrimonio netto al netto del debito fiscale latente stimato.")
    with th3:
        metric_card("Minusvalenze Latenti", fmt_eur(tlh["total_unrealized_losses"]), delta="Potenziale Harvesting", delta_color="normal", help_text="Minusvalenze latenti non ancora realizzate presenti nei dossier del portafoglio.")
    with th4:
        metric_card("Scudo Recuperabile", fmt_eur(tlh["tax_shield_recoverable"]), delta="Risparmio Fiscale 26%", delta_color="normal", help_text="Credito d'imposta netto generabile realizzando le minusvalenze a compensazione delle plusvalenze.")

    st.write("")
    st.write("")
    # RIGA 1: Opportunità di Tax-Loss Harvesting (Full Width)
    st.markdown("##### 🎯 Opportunità di Tax-Loss Harvesting Rilevate")
    if tlh["harvesting_opportunities"]:
        df_th = pd.DataFrame(tlh["harvesting_opportunities"])
        st.dataframe(
            df_th[["asset", "tipo", "minus_latente", "risparmio_fiscale_26", "azione_consigliata", "priorita"]],
            column_config={
                "asset": st.column_config.TextColumn("Asset / Posizione", width="medium"),
                "tipo": st.column_config.TextColumn("Classe", width="small"),
                "minus_latente": st.column_config.NumberColumn("Minus Latente (€)", format="€ %,.2f", width="small"),
                "risparmio_fiscale_26": st.column_config.NumberColumn("Risparmio 26% (€)", format="€ %,.2f", width="small"),
                "azione_consigliata": st.column_config.TextColumn("Azione Consigliata", width="large"),
                "priorita": st.column_config.TextColumn("Priorità", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nessuna minusvalenza latente rilevata nel portafoglio.")

    st.write("")
    # RIGA 2: Simulatore Deduzione IRPEF Fondo Pensione (Full Width)
    st.markdown("##### 🛡️ Simulatore Deduzione IRPEF Fondo Pensione (Art. 51 TUIR)")
    irp = tlh["irpef_pension_optimization"]
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 18px 22px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; flex-wrap: wrap; gap: 10px;">
            <div>
                <span style="font-size: 14px; font-weight: 750; color: #ffffff;">Plafond Fiscale Deducibile Annuo (Art. 51 TUIR):</span>
                <span class="mono-num" style="font-weight: 800; color: #38bdf8; font-size: 16px; margin-left: 8px;">€ {irp['deduction_ceiling']:,.2f}</span>
            </div>
            <div style="font-size: 12.5px; color: #94a3b8;">
                Versamenti Stimati: <b style="color:#ffffff;">€ {irp['current_annual_contributions']:,.2f}</b> &nbsp;|&nbsp; Plafond Residuo: <b style="color:#fbbf24;">€ {irp['remaining_deductible_ceiling']:,.2f}</b>
            </div>
        </div>
        <div>
            <div style="font-size: 11.5px; font-weight: 700; color: #94a3b8; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Rimborso IRPEF Stimato in Busta Paga (Modello 730):</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                <div style="background: rgba(0,0,0,0.25); border-radius: 8px; padding: 10px 14px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 11px; color: #94a3b8;">Scaglione 43% (Redditi &gt; € 50.000)</div>
                    <div class="mono-num" style="font-size: 17px; font-weight: 800; color: #34d399; margin-top: 2px;">+ € {irp['tax_refund_scaglione_43']:,.2f}</div>
                </div>
                <div style="background: rgba(0,0,0,0.25); border-radius: 8px; padding: 10px 14px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 11px; color: #94a3b8;">Scaglione 35% (Redditi € 28k - € 50k)</div>
                    <div class="mono-num" style="font-size: 17px; font-weight: 800; color: #38bdf8; margin-top: 2px;">+ € {irp['tax_refund_scaglione_35']:,.2f}</div>
                </div>
                <div style="background: rgba(0,0,0,0.25); border-radius: 8px; padding: 10px 14px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 11px; color: #94a3b8;">Scaglione 23% (Redditi &le; € 28.000)</div>
                    <div class="mono-num" style="font-size: 17px; font-weight: 800; color: #fbbf24; margin-top: 2px;">+ € {irp['tax_refund_scaglione_23']:,.2f}</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


with tab_split:

    st.markdown("### ⚖️ Ripartizione Patrimoniale Fiscale (Italia vs Estero)")
    st.caption("Confronto della localizzazione geografica degli asset e dell'incidenza delle imposte patrimoniali applicate (Bollo IT vs IVAFE).")
    
    tot_fisc_assets = fiscal["total_domestic_assets"] + fiscal["total_foreign_assets"]
    cs1, cs2 = st.columns([1.1, 1.2])
    with cs1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Attività Italia", "Attività Estero & Crypto"],
            values=[fiscal["total_domestic_assets"], fiscal["total_foreign_assets"]],
            hole=0.60,
            marker_colors=["#3b82f6", "#10b981"],
            textinfo="percent",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>Controvalore: <b>€ %{value:,.2f}</b> (%{percent})<extra></extra>"
        )])
        fig_pie.update_layout(
            title=dict(text="Localizzazione Geografica del Patrimonio", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=10, r=10, t=50, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<span style='font-size:11px; color:#94a3b8;'>TOTALE</span><br><b style='font-size:14px; color:#ffffff;'>€ {tot_fisc_assets:,.0f}</b>",
                x=0.5, y=0.5, font_size=12, showarrow=False
            )]
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

    with cs2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);">
            <div style="font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;">
                🏛️ Confronto Imposte Patrimoniali Annuali
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Outfit', sans-serif;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 9px 0; color: #e2e8f0;"><span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 4px; padding: 1px 6px; font-size: 10.5px; font-weight: 700; margin-right: 6px;">IT</span> Patrimonio Domiciliato Italia:</td>
                    <td class="mono-num" style="padding: 9px 0; font-weight: 700; text-align: right; color: #ffffff;">€ {fiscal['total_domestic_assets']:,.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 9px 0 9px 24px; color: #94a3b8; font-size: 12px;">&bull; Imposta di Bollo IT (0,20% + C/C):</td>
                    <td class="mono-num" style="padding: 9px 0; font-weight: 700; text-align: right; color: #38bdf8;">€ {fiscal['total_bollo']:,.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 9px 0; color: #e2e8f0;"><span style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 4px; padding: 1px 6px; font-size: 10.5px; font-weight: 700; margin-right: 6px;">EST</span> Patrimonio Domiciliato Estero:</td>
                    <td class="mono-num" style="padding: 9px 0; font-weight: 700; text-align: right; color: #ffffff;">€ {fiscal['total_foreign_assets']:,.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.08);">
                    <td style="padding: 9px 0 9px 24px; color: #94a3b8; font-size: 12px;">&bull; IVAFE Estero (0,20% + C/C):</td>
                    <td class="mono-num" style="padding: 9px 0; font-weight: 700; text-align: right; color: #34d399;">€ {fiscal['total_ivafe']:,.2f}</td>
                </tr>
                <tr style="font-weight: 800; font-size: 13.5px;">
                    <td style="padding: 12px 0; color: #f8fafc;">Totale Imposte Patrimoniali Ricorrenti:</td>
                    <td class="mono-num" style="padding: 12px 0; text-align: right; color: #fbbf24; font-size: 15px;">€ {fiscal['estimated_annual_fiscal_cost']:,.2f}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)




with tab_strat:
    st.markdown("### 💡 Strategie Istituzionali di Ottimizzazione Fiscale")
    st.caption("Linee guida e best practice operative per massimizzare il rendimento netto e minimizzare il drag fiscale del patrimonio.")
    
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; margin-top: 10px;">
        <!-- Card 1 -->
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); display: flex; flex-direction: column;">
            <h5 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 14.5px; font-weight: 750;">1. Compensazione Minusvalenze con ETC / Certificati</h5>
            <p style="color: #cbd5e1; font-size: 13px; margin: 0; line-height: 1.6; flex: 1;">
                In Italia, le plusvalenze da <b>ETF</b> sono considerate <i>Redditi di Capitale</i> e <u>non compensano</u> le minusvalenze pregresse. Per recuperare il credito dello zainetto fiscale prima della scadenza, è possibile utilizzare <b>Singoli Titoli Azionari</b>, <b>ETC/ETN</b> o <b>Certificates con Maxi-Cedola</b> (<i>Redditi Diversi</i>).
            </p>
        </div>
        <!-- Card 2 -->
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(52, 211, 153, 0.25); border-left: 4px solid #34d399; border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); display: flex; flex-direction: column;">
            <h5 style="color: #34d399; margin: 0 0 10px 0; font-size: 14.5px; font-weight: 750;">2. Deducibilità Previdenza Integrativa (Art. 51 TUIR)</h5>
            <p style="color: #cbd5e1; font-size: 13px; margin: 0; line-height: 1.6; flex: 1;">
                Saturare ogni anno il plafond di <b>€ 5.164,57</b> sui Fondi Pensione garantisce una deduzione diretta dal reddito imponibile IRPEF, generando un risparmio immediato dal <b>23% al 43%</b> in base al proprio scaglione marginale.
            </p>
        </div>
        <!-- Card 3 -->
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(251, 191, 36, 0.25); border-left: 4px solid #fbbf24; border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); display: flex; flex-direction: column;">
            <h5 style="color: #fbbf24; margin: 0 0 10px 0; font-size: 14.5px; font-weight: 750;">3. Aliquota Agevolata White List (12,50%)</h5>
            <p style="color: #cbd5e1; font-size: 13px; margin: 0; line-height: 1.6; flex: 1;">
                I rendimenti dei Titoli di Stato italiani (BTP, BOT, CCT) e dei Paesi White List UE/OCSE sono tassati con aliquota agevolata al <b>12,50%</b> invece del <b>26,00%</b> ordinario. Inoltre, i titoli di stato sono <u>completamente esenti da imposta di successione</u>.
            </p>
        </div>
        <!-- Card 4 -->
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(167, 139, 250, 0.25); border-left: 4px solid #a78bfa; border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25); display: flex; flex-direction: column;">
            <h5 style="color: #a78bfa; margin: 0 0 10px 0; font-size: 14.5px; font-weight: 750;">4. Asset Location &amp; Ottimizzazione IVAFE</h5>
            <p style="color: #cbd5e1; font-size: 13px; margin: 0; line-height: 1.6; flex: 1;">
                Mantenere i conti correnti liquidi esteri sotto la soglia di giacenza media di <b>€ 5.000</b> evita l'addebito dell'IVAFE di € 34,20 su ciascun conto senza penalizzare l'operatività quotidiana.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab_cross:
    st.markdown("### 🌍 Cross-Border Tax & Global Wealth Structuring Engine")
    st.caption("Confronto comparato del carico fiscale e successorio su grandi patrimoni tra regimi e giurisdizioni internazionali (Italia Ordinaria, Art. 24-bis Neo-Residenti, Svizzera Zugo, Lussemburgo SOPARFI, Dubai Zero-Tax).")

    from core.cross_border_tax_engine import compute_cross_border_wealth_tax_comparison

    col_cb_in1, col_cb_in2, col_cb_in3 = st.columns(3)
    with col_cb_in1:
        cb_wealth_in = st.number_input("Patrimonio Complessivo (€):", min_value=500000.0, value=10000000.0, step=500000.0, format="%.2f")
    with col_cb_in2:
        cb_cgt_in = st.number_input("Plusvalenze Realizzate Annue (€):", min_value=0.0, value=400000.0, step=50000.0, format="%.2f")
    with col_cb_in3:
        cb_div_in = st.number_input("Rendite / Dividendi Esteri Annui (€):", min_value=0.0, value=250000.0, step=25000.0, format="%.2f")

    cb_res = compute_cross_border_wealth_tax_comparison(
        total_wealth_eur=cb_wealth_in,
        annual_capital_gain_eur=cb_cgt_in,
        annual_foreign_income_eur=cb_div_in
    )

    cb_k1, cb_k2, cb_k3 = st.columns(3)
    with cb_k1:
        metric_card("Giurisdizione Ottimale", cb_res["lowest_tax_jurisdiction"], delta="Minimo Carico Fiscale", delta_color="normal")
    with cb_k2:
        metric_card("Risparmio Annuo Max vs IT", fmt_eur(cb_res["max_annual_tax_savings_eur"]), delta="Tax Alpha Annuo", delta_color="normal")
    with cb_k3:
        metric_card("Patrimonio Simulato", fmt_eur(cb_res["simulated_wealth_eur"]), delta="Total Wealth Base", delta_color="normal")

    st.write("")
    st.markdown("##### 📊 Benchmark Comparativo dei Regimi Fiscali Internazionali")
    st.dataframe(
        cb_res["comparison_df"][["name", "annual_cgt_eur", "annual_income_tax_eur", "annual_wealth_tax_eur", "total_annual_tax_eur", "effective_annual_tax_rate_pct", "estimated_estate_succession_tax_eur"]].rename(columns={
            "name": "Giurisdizione / Regime Fiscale",
            "annual_cgt_eur": "Imposta CGT (€)",
            "annual_income_tax_eur": "Imposta Dividendi (€)",
            "annual_wealth_tax_eur": "Imposta Patrimoniale (€)",
            "total_annual_tax_eur": "Totale Imposte Annue (€)",
            "effective_annual_tax_rate_pct": "Aliquota Effettiva (%)",
            "estimated_estate_succession_tax_eur": "Imposta Successione (€)"
        }),
        use_container_width=True,
        hide_index=True
    )

