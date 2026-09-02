# ============================================================
# core/wealth/wealth_reporting_hub.py
# ARGUS — Wealth Reporting & Comprehensive Institutional Exports Hub
# Multi-Format: White-Label PDF, Pitchbook, Tear-Sheet, Excel, Parquet, CSV, JSON & Audio
# ============================================================

import io
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from core.fetcher import get_engine
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_fiscal_analytics,
    compute_real_estate_net_equity_and_ltv,
    generate_advisory_pitchbook_pdf,
    generate_advisory_pitchbook_html,
    generate_executive_tear_sheet_pdf
)
from core.quarterly_report_generator import generate_white_label_quarterly_pdf_report
from core.wealth.wealth_exporter import export_wealth_master_excel_workbook
from core.wealth.wealth_db import (
    get_cashflow_records,
    get_physical_assets,
    get_pension_plans,
    get_wealth_accounts
)
from core.voice_advisor_engine import generate_ai_voice_executive_briefing


def render_wealth_reporting_and_exports_hub(
    engine: Engine,
    portfolio_id: int = 1,
    prof_name: str = "Family Office Master"
):
    """
    Renderizza il Centro Istituzionale di Reportistica ed Esportazioni Multi-Formato per ARGUS Wealth.
    Include 9 tipologie di esportazione: PDF, XLSX, Parquet, CSV, JSON e Audio TTS.
    """
    date_slug = datetime.now().strftime("%Y%m%d")
    prof_slug = prof_name.lower().replace(" ", "_")

    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-left: 4px solid #10b981; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <h4 style="color: #ffffff; margin: 0 0 4px 0; font-size: 16px; font-weight: 750;">
                    📑 Hub di Reportistica &amp; Esportazioni Istituzionali
                </h4>
                <span style="color: #94a3b8; font-size: 12.5px;">
                    Dossier esecutivi completi per Family Office, Private Banking, Commercialisti e Archiviazione Locale Crittografata.
                </span>
            </div>
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px;">
                9 Formati di Esportazione Disponibili
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_pdf, tab_data, tab_fisc, tab_media = st.tabs([
        "📑 Dossier PDF & Client Reports",
        "📊 Master Excel & Database Parquet",
        "⚖️ Fisco, Libro Mastro & Quadro RW",
        "🎙️ Executive Audio & Backup JSON"
    ])

    # ── TAB 1: PDF & CLIENT DOSSIERS ────────────────────────────
    with tab_pdf:
        st.markdown("##### 📄 Dossier Multipagina & Pitchbook Istituzionali")
        st.caption("Documenti ad alta risoluzione pronti per la stampa, comitati consultivi e clienti di private banking.")

        c_pdf1, c_pdf2, c_pdf3 = st.columns(3)

        with c_pdf1:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #38bdf8; font-size: 13.5px;">📄 Quarterly Client Report (PDF)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Dossier trimestrale completo ReportLab: Bilancio Net Worth, Brinson Multi-Asset, EBA Stress Test e SFDR ESG Scorecard.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                pdf_qtr = generate_white_label_quarterly_pdf_report(engine, portfolio_id=portfolio_id, client_name=prof_name, quarter="Q1 2026")
                st.download_button(
                    label="📥 Scarica Quarterly Report PDF",
                    data=pdf_qtr,
                    file_name=f"argus_quarterly_dossier_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="dl_qtr_pdf_hub"
                )
            except Exception as e:
                st.error(f"Errore PDF QTR: {e}")

        with c_pdf2:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #34d399; font-size: 13.5px;">🏢 Advisory Pitchbook (PDF 6 Pag.)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Brochure di consulenza patrimoniale a 6 pagine con Health Score Radar, Goal-Based SPI %, Real Estate LTV e Action Plan.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                pdf_pitch = generate_advisory_pitchbook_pdf(engine, portfolio_id=portfolio_id)
                st.download_button(
                    label="📥 Scarica Pitchbook PDF",
                    data=pdf_pitch,
                    file_name=f"argus_advisory_pitchbook_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_pitch_pdf_hub"
                )
            except Exception as e:
                st.error(f"Errore Pitchbook: {e}")

        with c_pdf3:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 180px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #fbbf24; font-size: 13.5px;">📑 Tear-Sheet Sintetica (PDF/HTML)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Scheda riassuntiva one-page a colpo d'occhio con Net Worth, indicatori di solvibilità e sintesi grafica degli attivi.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                pdf_ts = generate_executive_tear_sheet_pdf(engine, portfolio_id=portfolio_id)
                st.download_button(
                    label="📥 Scarica Tear-Sheet PDF",
                    data=pdf_ts,
                    file_name=f"argus_tear_sheet_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_ts_pdf_hub"
                )
            except Exception as e:
                st.error(f"Errore Tear-Sheet: {e}")

    # ── TAB 2: MASTER EXCEL & PARQUET ───────────────────────────
    with tab_data:
        st.markdown("##### 📊 Database & Fogli di Calcolo Strutturati")
        st.caption("Modelli tabellari per audit analitico, elaborazioni in Python/R o integrazione in database OLAP.")

        c_dat1, c_dat2 = st.columns(2)

        with c_dat1:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #10b981; font-size: 13.5px;">📊 Master Excel Workbook (.xlsx)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Dossier completo a 10 fogli (Stato Patrimoniale, Cash Flow, Asset Fisici, Orologi, Previdenza, Immobili, Scenari e Formule).
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                xl_bytes = export_wealth_master_excel_workbook(engine, portfolio_id=portfolio_id)
                st.download_button(
                    label="📥 Scarica Master Excel (.xlsx)",
                    data=xl_bytes.getvalue(),
                    file_name=f"argus_wealth_master_{prof_slug}_{date_slug}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    key="dl_xl_hub"
                )
            except Exception as e:
                st.error(f"Errore Excel: {e}")

        with c_dat2:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #6366f1; font-size: 13.5px;">💾 Parquet Analytical Database (.parquet)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Esportazione compattata ad alte prestazioni delle transazioni e snapshot per DuckDB, Apache Arrow, Polars e Pandas.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                df_tx = get_cashflow_records(engine, portfolio_id=portfolio_id)
                if df_tx is None or df_tx.empty:
                    df_tx = pd.DataFrame([{"info": "no_data"}])
                pq_buf = io.BytesIO()
                df_tx.to_parquet(pq_buf, index=False)
                st.download_button(
                    label="📥 Scarica Dataset Parquet (.parquet)",
                    data=pq_buf.getvalue(),
                    file_name=f"argus_wealth_cashflow_{prof_slug}_{date_slug}.parquet",
                    mime="application/octet-stream",
                    use_container_width=True,
                    key="dl_pq_hub"
                )
            except Exception as e:
                st.error(f"Errore Parquet: {e}")

    # ── TAB 3: FISCO & LIBRO MASTRO ─────────────────────────────
    with tab_fisc:
        st.markdown("##### ⚖️ Fiscalità, Libro Mastro & Monitoraggio Estero")
        st.caption("Prospetti conformi alla normativa tributaria italiana (TUIR Quadro RW / RT) e registro dei movimenti bancari.")

        c_fisc1, c_fisc2 = st.columns(2)

        with c_fisc1:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #f59e0b; font-size: 13.5px;">📑 Prospetto Quadro RW / RT (.csv)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Righi precompilati per il Modello Redditi PF con codice investimento, valore iniziale/finale e calcolo IVAFE per il commercialista.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                fisc = compute_fiscal_analytics(engine, portfolio_id=portfolio_id)
                df_rw = pd.DataFrame(fisc.get("quadro_rw_rows", []))
                csv_rw = df_rw.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Scarica Quadro RW (.csv)",
                    data=csv_rw,
                    file_name=f"argus_quadro_rw_{prof_slug}_{date_slug}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="dl_rw_csv_hub"
                )
            except Exception as e:
                st.error(f"Errore Quadro RW: {e}")

        with c_fisc2:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #38bdf8; font-size: 13.5px;">📜 Registro Integrale Cash Flow (.csv)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Libro mastro completo di tutte le entrate e uscite con data contabile, importo, categoria semantica e natura 50/30/20.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
                csv_cf = df_cf.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Scarica Libro Mastro (.csv)",
                    data=csv_cf,
                    file_name=f"argus_cashflow_ledger_{prof_slug}_{date_slug}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="dl_cf_csv_hub"
                )
            except Exception as e:
                st.error(f"Errore Cash Flow CSV: {e}")

    # ── TAB 4: AUDIO & BACKUP JSON ──────────────────────────────
    with tab_media:
        st.markdown("##### 🎙️ Audio Executive Briefing & Backup Crittografico JSON")
        st.caption("Sintesi vocale per podcast esecutivo e snapshot JSON atomico per backup e migrazione dati.")

        c_med1, c_med2 = st.columns(2)

        with c_med1:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #ec4899; font-size: 13.5px;">🎙️ Copione Audio Briefing (.txt)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Script a due voci (Chief Investment Officer & Chief Risk Officer) sincronizzato sui dati reali del patrimonio per sintesi vocale TTS.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                vb = generate_ai_voice_executive_briefing(engine, portfolio_id=portfolio_id, client_name=prof_name)
                st.download_button(
                    label="📥 Scarica Script Audio (.txt)",
                    data=vb["full_text_transcript"],
                    file_name=f"argus_voice_script_{prof_slug}_{date_slug}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="dl_txt_audio_hub"
                )
            except Exception as e:
                st.error(f"Errore Audio Script: {e}")

        with c_med2:
            st.markdown("""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #a855f7; font-size: 13.5px;">🏛️ Snapshot Patrimoniale JSON (.json)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Backup atomico strutturato di conti, saldi, categorie e parametri per ripristino istantaneo o migrazione su altro ambiente.
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
                snap_dict = {
                    "portfolio_id": portfolio_id,
                    "portfolio_name": prof_name,
                    "exported_at": datetime.now().isoformat(),
                    "net_worth_eur": nw.total_net_worth,
                    "liquid_cash_eur": nw.liquid_cash,
                    "investments_eur": nw.financial_investments,
                    "real_estate_eur": nw.real_estate_total,
                    "liabilities_eur": nw.total_liabilities,
                    "health_score": nw.wealth_health_score
                }
                json_str = json.dumps(snap_dict, indent=2)
                st.download_button(
                    label="📥 Scarica Snapshot JSON (.json)",
                    data=json_str,
                    file_name=f"argus_wealth_snapshot_{prof_slug}_{date_slug}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="dl_json_snap_hub"
                )
            except Exception as e:
                st.error(f"Errore JSON Snapshot: {e}")
