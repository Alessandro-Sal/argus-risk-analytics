# ============================================================
# core/wealth/tax_history_ui.py
# ARGUS — UI Component: Archivio Storico Fiscale & Riconciliazione (730 / Redditi PF)
# Sezione 1: Gestione & Inserimento (Upload PDF / Form manuale / Data Editor)
# Sezione 2: Dashboard Storica & Zainetto Fiscale (Timeline 5Y & Semafori AdE)
# Sezione 3: Audit & Punti di Miglioria (Advisor Alerts & Art. 36-bis Risk)
# ============================================================

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import Engine

from core.adapters.broker_hub import parse_broker_csv
from core.ui_utils import fmt_eur, metric_card, render_table_with_export
from core.wealth.tax_history_engine import (
    build_730_predisposition_and_variance_audit,
    build_triangular_tax_audit,
    compute_broker_annual_capital_gains,
    compute_ravvedimento_operoso,
    delete_declaration,
    delete_tax_loss,
    delete_verification_document,
    fmt_eur_it,
    generate_sample_730_json,
    get_declarations,
    get_tax_losses,
    get_verification_documents,
    parse_730_pdf_or_json,
    parse_universal_tax_document,
    reconcile_with_portfolio,
    record_declaration,
    record_tax_loss,
    record_verification_document,
    update_tax_loss_offset,
)


def render_tax_history_tab(engine: Engine, portfolio_id: Any) -> None:
    """
    Rende l'interfaccia completa per l'Archivio Storico Fiscale e la Riconciliazione Dichiarazioni.
    """
    pid_str = str(portfolio_id)
    current_year = datetime.now().year

    st.markdown("### 🏛️ Archivio Storico Fiscale, Riconciliazione Dichiarazioni & Zainetto 730")
    st.caption(
        "Motore istituzionale per la gestione pluriennale dei Modelli 730 e Redditi PF, "
        "riconciliazione con i flussi reali dei broker, monitoraggio scadenze quadriennali delle minusvalenze "
        "e prevenzione automatica di avvisi di irregolarità ex art. 36-bis d.P.R. 600/1973."
    )

    # ── SELETTORE ANNO DI RICONCILIAZIONE & STATUS RAPIDO ────────
    c_head1, c_head2, c_head3 = st.columns([2.5, 1.5, 1.5])
    with c_head1:
        years_list = [current_year - i for i in range(7)]
        default_idx = 1 if len(years_list) > 1 else 0  # Predefinito: anno precedente (es. 2024 o 2025)
        selected_tax_year = st.selectbox(
            "📅 Anno d'Imposta di Riconciliazione:",
            options=years_list,
            index=default_idx,
            key=f"tax_hist_year_picker_{pid_str}",
            format_func=lambda y: f"Anno d'Imposta {y} (Presentazione {y + 1})",
        )
    with c_head2:
        decls = get_declarations(engine, profile_id=pid_str)
        st.metric("Dichiarazioni Archiviate", f"{len(decls)} Anni")
    with c_head3:
        losses = get_tax_losses(engine, profile_id=pid_str, current_year=selected_tax_year)
        tot_active_losses = sum(float(l["remaining_amount"]) for l in losses if l["status"] == "ACTIVE")
        st.metric("Zainetto Fiscale Residuo", fmt_eur(tot_active_losses))

    st.markdown("---")

    # ── SUB-TABS DELLA SEZIONE ──────────────────────────────────
    subtab_man, subtab_dash, subtab_audit = st.tabs([
        "📥 1. Gestione & Inserimento (Upload / Data Editor)",
        "📊 2. Dashboard Storica & Zainetto Fiscale",
        "🚨 3. Audit Advisor & Riconciliazione Broker (Art. 36-bis)",
    ])

    # ============================================================
    # SUBTAB 1: GESTIONE & INSERIMENTO (UPLOAD PDF / FORM / EDITOR)
    # ============================================================
    with subtab_man:
        st.markdown("#### 📥 Gestione Documentale & Inserimento Dichiarazioni")
        st.caption("Carica il file PDF o JSON della dichiarazione oppure utilizza l'editor tabellare interattivo per modifiche rapide.")

        # ── STATO STORICO ARCHIVIATO (TRIENNIO OVERVIEW) ──
        decls_history = get_declarations(engine, profile_id=pid_str)
        if decls_history:
            st.markdown("##### 📚 Riepilogo Dichiarazioni Attualmente in Archivio")
            sorted_decls = sorted(decls_history, key=lambda x: int(x.get("tax_year", 0)))
            c_stat_cols = st.columns(max(1, min(len(sorted_decls), 4)))
            for c_idx, d_item in enumerate(sorted_decls[-4:]):
                with c_stat_cols[c_idx % len(c_stat_cols)]:
                    yr = d_item.get("tax_year")
                    gross = float(d_item.get("gross_income", 0.0) or 0.0)
                    net_irpef = float(d_item.get("net_tax_irpef", 0.0) or 0.0)
                    cg = float(d_item.get("capital_gains_declared", 0.0) or 0.0)
                    iv = float(d_item.get("ivafe_paid", 0.0) or 0.0)
                    st.markdown(
                        f"""<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-weight: 700; font-size: 14px; color: #38bdf8;">Anno d'Imposta {yr}</span>
                                <span style="font-size: 11px; background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3);">Archiviato</span>
                            </div>
                            <div style="font-size: 12px; color: #94a3b8; line-height: 1.6;">
                                Reddito: <strong style="color: #f8fafc;">{fmt_eur_it(gross)}</strong><br/>
                                Imposta IRPEF: <strong style="color: #f8fafc;">{fmt_eur_it(net_irpef)}</strong><br/>
                                Plusvalenze: <strong style="color: #10b981;">{fmt_eur_it(cg)}</strong> | IVAFE: <strong style="color: #38bdf8;">{fmt_eur_it(iv)}</strong>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        # ── STATO DOCUMENTI DI VERIFICA & RISCONTRO (CU, BROKER, 36-BIS) ──
        vdocs_history = get_verification_documents(engine, profile_id=pid_str)
        if vdocs_history:
            st.markdown("##### 📁 Documenti di Riscontro & Verifica in Archivio (CU, Broker, AdE 36-bis)")
            sorted_vdocs = sorted(vdocs_history, key=lambda x: int(x.get("tax_year", 0)))
            c_v_cols = st.columns(max(1, min(len(sorted_vdocs), 4)))
            for v_idx, v_item in enumerate(sorted_vdocs[-4:]):
                with c_v_cols[v_idx % len(c_v_cols)]:
                    v_type = v_item.get("doc_type", "DOC")
                    v_yr = v_item.get("tax_year")
                    v_issuer = v_item.get("issuer_name") or "Intermediario"
                    v_gross = float(v_item.get("gross_amount", 0.0) or 0.0)
                    v_tax = float(v_item.get("tax_withheld_or_due", 0.0) or 0.0)
                    v_tot = float(v_item.get("total_due", 0.0) or 0.0)

                    if v_type == "CU":
                        type_label = f"CU ({v_issuer})"
                        badge_color = "#10b981"
                        detail_line = f"Reddito: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Ritenute: <strong style='color: #38bdf8;'>{fmt_eur_it(v_tax)}</strong>"
                    elif v_type == "PRECOMPILATA_ADE":
                        type_label = "Mod. 730 Precompilato"
                        badge_color = "#3b82f6"
                        detail_line = f"Rimborso AdE: <strong style='color: #10b981;'>{fmt_eur_it(v_item.get('secondary_amount', 0.0))}</strong><br/>Reddito: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong>"
                    elif v_type in ["BROKER_REPORT", "BROKER_TAX_REPORT"]:
                        type_label = f"Rendiconto {v_issuer}"
                        badge_color = "#f59e0b"
                        detail_line = f"Plusvalenze: <strong style='color: #10b981;'>{fmt_eur_it(v_gross)}</strong><br/>Imposta 26%: <strong style='color: #f59e0b;'>{fmt_eur_it(v_tax)}</strong>"
                    elif v_type == "BANK_STATEMENT_RW":
                        type_label = f"Conto Estero ({v_issuer})"
                        badge_color = "#06b6d4"
                        detail_line = f"Giacenza: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Saldo 31/12: <strong style='color: #38bdf8;'>{fmt_eur_it(v_item.get('net_taxable_amount', 0.0))}</strong>"
                    elif v_type == "RENT_EXPENSE":
                        type_label = f"Locazione ({v_issuer})"
                        badge_color = "#a855f7"
                        detail_line = f"Canone: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Detrazione 19%: <strong style='color: #10b981;'>+{fmt_eur_it(v_item.get('secondary_amount', 0.0))}</strong>"
                    elif v_type == "ADE_NOTICE_36BIS":
                        type_label = "Avviso AdE 36-bis"
                        badge_color = "#ef4444"
                        detail_line = f"Contestato: <strong style='color: #ef4444;'>{fmt_eur_it(v_tot or v_tax)}</strong><br/>Atto: <i>{v_item.get('protocol_or_code') or 'N/D'}</i>"
                    else:
                        type_label = f"Doc {v_type}"
                        badge_color = "#38bdf8"
                        detail_line = f"Importo: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong>"

                    st.markdown(
                        f"""<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-weight: 700; font-size: 13px; color: {badge_color};">{type_label}</span>
                                <span style="font-size: 11px; background: rgba(255, 255, 255, 0.08); color: #cbd5e1; padding: 2px 6px; border-radius: 4px;">{v_yr}</span>
                            </div>
                            <div style="font-size: 12px; color: #94a3b8; line-height: 1.6;">
                                {detail_line}
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

            with st.expander("🗑️ Gestione / Eliminazione Documenti di Riscontro", expanded=False):
                col_vd1, col_vd2 = st.columns([3, 1])
                with col_vd1:
                    sel_del_vd_id = st.selectbox(
                        "Seleziona documento di verifica da rimuovere:",
                        options=[v["id"] for v in vdocs_history],
                        format_func=lambda vid: next(
                            (f"ID #{vid} — {v.get('doc_type')} {v.get('tax_year')} ({v.get('issuer_name') or 'N/D'})" for v in vdocs_history if v["id"] == vid),
                            str(vid),
                        ),
                        key=f"sel_del_vdoc_{pid_str}",
                    )
                with col_vd2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Elimina Documento", key=f"btn_del_vdoc_{pid_str}"):
                        delete_verification_document(engine, sel_del_vd_id)
                        st.warning(f"Documento #{sel_del_vd_id} eliminato con successo.")
                        st.rerun()

        st.markdown("---")

        # ── SEZIONE PRINCIPALE: CARICAMENTO INTELLIGENTE MULTI-DOCUMENTO (FULL WIDTH) ──
        st.markdown("##### 📄 Hub Intelligente Ingestione Fiscale (730 / Precompilata / CU / DEGIRO / Conti Esteri / Locazione)")
        st.info(
            "💡 **Hub Universale di Ingestione Fiscale & Predisposizione Modello 730:**\n\n"
            "- **Precompilata AdE & 730 Ufficiale:** Trascina il prospetto precompilato (testuale o grafico) o il 730 definitivo. Riconosce oneri Quadro E e isola i 'Dati non utilizzati'.\n"
            "- **Certificazioni Uniche (CU):** Estrae redditi da lavoro (Sixtema Punti 1–6, ritenute P. 21, addizionali) e borse di studio esenti (ER.GO Punto 465 cod. 23).\n"
            "- **Rendiconti Fiscali Broker:** Acquisisce i prospetti DEGIRO (Modello Unico / Calcoli) per Quadro RT (plusvalenze 26%) e Quadro W/RW (IVAFE 2‰).\n"
            "- **Conti Correnti Esteri:** Analizza estratti conto N26 e Revolut per monitoraggio fiscale e verifica automatica della soglia di esenzione IVAFE (€ 5.000,00).\n"
            "- **Spese e Contratti di Locazione:** Ricevute bonifici affitto e contratto studenti fuori sede (Art. 15 TUIR) per sbloccare la detrazione al 19% (Rigo E8 cod. 18).\n"
            "- **Avvisi AdE Art. 36-bis:** Rileva le comunicazioni di liquidazione automatica con codice atto, debito contestato, sanzioni e interessi."
        )

        c_up_box, c_up_tpl = st.columns([3.5, 1.2])
        with c_up_box:
            uploaded_files = st.file_uploader(
                "Trascina i tuoi documenti fiscali (Precompilata, CU, DEGIRO, Conti Esteri N26/Revolut, Affitto, 730, Avvisi 36-bis):",
                type=["pdf", "json", "txt"],
                accept_multiple_files=True,
                key=f"file_uploader_tax_{pid_str}",
                help="Supporta PDF ufficiali AdE, Precompilata, CU Sixtema ed ER.GO, Rendiconti DEGIRO, Giacenza media N26, Bonifici affitto e Avvisi 36-bis.",
            )
        with c_up_tpl:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            sample_json_str = generate_sample_730_json(selected_tax_year)
            st.download_button(
                "📥 Template JSON d'Esempio",
                data=sample_json_str,
                file_name=f"argus_730_template_{selected_tax_year}.json",
                mime="application/json",
                key=f"dl_template_json_{pid_str}",
                use_container_width=True,
                help="Scarica un file JSON pre-compilato con le chiavi fiscali richieste per test rapido.",
            )

        if uploaded_files:
            parsed_list = []
            for up_file in uploaded_files:
                file_bytes = up_file.read()
                filename = up_file.name
                with st.spinner(f"Analisi automatica e classificazione di {filename}..."):
                    p_data = parse_universal_tax_document(file_bytes, filename=filename)
                    p_data["profile_id"] = pid_str
                    parsed_list.append((filename, p_data))

            st.success(f"Caricati ed elaborati con successo **{len(parsed_list)} file**!")

            # Pulsante salvataggio cumulativo per più file
            if len(parsed_list) > 1:
                if st.button("💾 Conferma & Salva Tutti i Documenti nel Database (Batch)", key=f"btn_save_all_batch_{pid_str}", type="primary", use_container_width=True):
                    saved_cnt = 0
                    for fname, p_data in parsed_list:
                        dt = p_data.get("doc_type", "OFFICIAL_DECLARATION")
                        if dt == "OFFICIAL_DECLARATION":
                            if p_data.get("gross_income", 0.0) > 0 or p_data.get("capital_gains_declared", 0.0) > 0:
                                record_declaration(engine, p_data)
                                saved_cnt += 1
                        else:
                            record_verification_document(engine, p_data)
                            saved_cnt += 1
                    st.success(f"✅ Registrati con successo {saved_cnt} documenti fiscali nel database!")
                    st.rerun()

            for idx, (filename, parsed_data) in enumerate(parsed_list):
                dt = parsed_data.get("doc_type", "OFFICIAL_DECLARATION")

                if dt == "CU":
                    st.markdown(
                        f"""<div style="background: rgba(16, 185, 129, 0.04); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #10b981;">📄 File #{idx+1}: Certificazione Unica {parsed_data.get('filing_year', int(parsed_data.get('tax_year', 2024))+1)} (Redditi {parsed_data.get('tax_year', 2024)})</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 3px 8px; border-radius: 4px; font-weight: 600;">✅ Certificazione Unica Riconosciuta</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Sostituto d'Imposta", parsed_data.get("issuer_name") or "Datore di Lavoro", f"CF: {parsed_data.get('taxpayer_cf') or 'N/D'}")
                    with c_m2:
                        days = parsed_data.get("metadata_json", {}).get("days_worked", 0) if isinstance(parsed_data.get("metadata_json"), dict) else 0
                        metric_card("Redditi Lavoro (Punti 1-6)", fmt_eur(parsed_data.get("gross_amount", 0.0)), f"{days} giorni lavoro" if days else "Assimilati")
                    with c_m3:
                        metric_card("Ritenute IRPEF (Punto 21)", fmt_eur(parsed_data.get("tax_withheld_or_due", 0.0)), "Trattenute a titolo d'acconto")
                    with c_m4:
                        metric_card("Addizionali Reg./Com.", fmt_eur(parsed_data.get("secondary_amount", 0.0)), "Regionale e Comunale")

                    with st.expander(f"🔍 Dettagli & Modifica Campi CU {parsed_data.get('tax_year')}", expanded=False):
                        c_cu1, c_cu2 = st.columns(2)
                        with c_cu1:
                            cu_yr = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2024)), key=f"cu_yr_{pid_str}_{idx}")
                            cu_iss = st.text_input("Sostituto d'Imposta:", value=str(parsed_data.get("issuer_name") or ""), key=f"cu_iss_{pid_str}_{idx}")
                            cu_gross = st.number_input("Reddito Lordo (€):", value=float(parsed_data.get("gross_amount", 0.0)), step=500.0, key=f"cu_gr_{pid_str}_{idx}")
                        with c_cu2:
                            cu_wh = st.number_input("Ritenute IRPEF (P. 21) (€):", value=float(parsed_data.get("tax_withheld_or_due", 0.0)), step=100.0, key=f"cu_wh_{pid_str}_{idx}")
                            cu_add = st.number_input("Addizionali Regionali/Comunali (€):", value=float(parsed_data.get("secondary_amount", 0.0)), step=50.0, key=f"cu_add_{pid_str}_{idx}")
                            cu_notes = st.text_input("Note:", value=str(parsed_data.get("notes") or ""), key=f"cu_notes_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button(f"💾 Salva CU Anno {parsed_data.get('tax_year')} in Archivio", key=f"btn_save_cu_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_cu = {
                                "profile_id": pid_str,
                                "tax_year": int(cu_yr),
                                "doc_type": "CU",
                                "issuer_name": cu_iss,
                                "protocol_or_code": parsed_data.get("protocol_or_code"),
                                "gross_amount": cu_gross,
                                "tax_withheld_or_due": cu_wh,
                                "secondary_amount": cu_add,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": cu_notes,
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_cu)
                            st.success(f"✅ Certificazione Unica registrata con ID #{v_id}!")
                            st.rerun()

                elif dt == "BROKER_REPORT":
                    b_name = parsed_data.get("issuer_name") or "DEGIRO"
                    st.markdown(
                        f"""<div style="background: rgba(245, 158, 11, 0.04); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #f59e0b;">📄 File #{idx+1}: Rendiconto Fiscale {b_name} (Anno {parsed_data.get('tax_year', 2024)})</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 3px 8px; border-radius: 4px; font-weight: 600;">✅ Rendiconto Broker Riconosciuto</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Plusvalenze Lorde", fmt_eur(parsed_data.get("gross_amount", 0.0)), f"Minusvalenze: {fmt_eur(parsed_data.get('secondary_amount', 0.0))}")
                    with c_m2:
                        metric_card("Imponibile Netto", fmt_eur(parsed_data.get("net_taxable_amount", 0.0)), "Art. 68 c. 5 TUIR")
                    with c_m3:
                        metric_card("Imposta Sostitutiva 26%", fmt_eur(parsed_data.get("tax_withheld_or_due", 0.0)), "Quadro RT / Rigo 321")
                    with c_m4:
                        metric_card("Monitoraggio Quadro RW", fmt_eur(parsed_data.get("asset_monitoring_val", 0.0)), f"IVAFE 2‰: {fmt_eur(parsed_data.get('total_due', 0.0))}")

                    with st.expander(f"🔍 Dettagli & Modifica Campi Broker {b_name} {parsed_data.get('tax_year')}", expanded=False):
                        c_br1, c_br2 = st.columns(2)
                        with c_br1:
                            br_yr = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2024)), key=f"br_yr_{pid_str}_{idx}")
                            br_iss = st.text_input("Intermediario / Broker:", value=b_name, key=f"br_iss_{pid_str}_{idx}")
                            br_cg = st.number_input("Plusvalenze Lorde (€):", value=float(parsed_data.get("gross_amount", 0.0)), step=100.0, key=f"br_cg_{pid_str}_{idx}")
                            br_cl = st.number_input("Minusvalenze Compensate (€):", value=float(parsed_data.get("secondary_amount", 0.0)), step=100.0, key=f"br_cl_{pid_str}_{idx}")
                        with c_br2:
                            br_net = st.number_input("Base Imponibile Netta (€):", value=float(parsed_data.get("net_taxable_amount", 0.0)), step=100.0, key=f"br_net_{pid_str}_{idx}")
                            br_tax = st.number_input("Imposta Sostitutiva 26% (€):", value=float(parsed_data.get("tax_withheld_or_due", 0.0)), step=50.0, key=f"br_tax_{pid_str}_{idx}")
                            br_rw = st.number_input("Attività Estere RW (€):", value=float(parsed_data.get("asset_monitoring_val", 0.0)), step=1000.0, key=f"br_rw_{pid_str}_{idx}")
                            br_ivafe = st.number_input("IVAFE Versata (€):", value=float(parsed_data.get("total_due", 0.0)), step=10.0, key=f"br_ivafe_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button(f"💾 Salva Rendiconto Broker ({b_name} {parsed_data.get('tax_year')}) in Archivio", key=f"btn_save_brk_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_brk = {
                                "profile_id": pid_str,
                                "tax_year": int(br_yr),
                                "doc_type": "BROKER_REPORT",
                                "issuer_name": br_iss,
                                "gross_amount": br_cg,
                                "secondary_amount": br_cl,
                                "net_taxable_amount": br_net,
                                "tax_withheld_or_due": br_tax,
                                "asset_monitoring_val": br_rw,
                                "total_due": br_ivafe,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": parsed_data.get("notes") or f"Rendiconto {br_iss}",
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_brk)
                            st.success(f"✅ Rendiconto Broker {br_iss} registrato con ID #{v_id}!")
                            st.rerun()

                elif dt == "ADE_NOTICE_36BIS":
                    proto_code = parsed_data.get("protocol_or_code") or "Atto AdE"
                    tot_req = float(parsed_data.get("total_due", 0.0))
                    st.markdown(
                        f"""<div style="background: rgba(239, 68, 68, 0.06); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #ef4444;">🚨 File #{idx+1}: Comunicazione di Irregolarità AdE Art. 36-bis ({proto_code})</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 3px 8px; border-radius: 4px; font-weight: 600;">⚠️ Controllo Automatizzato d.P.R. 600/73</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Imposta Ricalcolata a Debito", fmt_eur(parsed_data.get("tax_withheld_or_due", 0.0)), f"Versata a Modello: {fmt_eur(parsed_data.get('tax_paid', 0.0))}")
                    with c_m2:
                        unpaid = max(0.0, float(parsed_data.get("tax_withheld_or_due", 0.0)) - float(parsed_data.get("tax_paid", 0.0)))
                        metric_card("Differenza Imposta Richiesta", fmt_eur(unpaid), "Codice Tributo 1100")
                    with c_m3:
                        sanz_int = float(parsed_data.get("penalty_amount", 0.0)) + float(parsed_data.get("interest_amount", 0.0))
                        metric_card("Sanzioni & Interessi", fmt_eur(sanz_int), f"Sanz: {fmt_eur(parsed_data.get('penalty_amount', 0.0))} | Int: {fmt_eur(parsed_data.get('interest_amount', 0.0))}")
                    with c_m4:
                        metric_card("Somma Complessiva Richiesta", fmt_eur(tot_req), "Da sgravare via CIVIS", delta_color="inverse")

                    with st.expander(f"🔍 Dettagli & Modifica Campi Avviso AdE {parsed_data.get('tax_year')}", expanded=False):
                        c_ad1, c_ad2 = st.columns(2)
                        with c_ad1:
                            ad_yr = st.number_input("Periodo d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2024)), key=f"ad_yr_{pid_str}_{idx}")
                            ad_code = st.text_input("Codice Atto / Protocollo:", value=str(proto_code), key=f"ad_code_{pid_str}_{idx}")
                            ad_due = st.number_input("Imposta a Debito Ricalcolata (€):", value=float(parsed_data.get("tax_withheld_or_due", 0.0)), step=50.0, key=f"ad_due_{pid_str}_{idx}")
                            ad_paid = st.number_input("Imposta Già Versata (€):", value=float(parsed_data.get("tax_paid", 0.0)), step=50.0, key=f"ad_paid_{pid_str}_{idx}")
                        with c_ad2:
                            ad_sanz = st.number_input("Sanzioni (€):", value=float(parsed_data.get("penalty_amount", 0.0)), step=10.0, key=f"ad_sanz_{pid_str}_{idx}")
                            ad_int = st.number_input("Interessi di Mora (€):", value=float(parsed_data.get("interest_amount", 0.0)), step=5.0, key=f"ad_int_{pid_str}_{idx}")
                            ad_tot = st.number_input("Totale Complessivo Richiesto (€):", value=float(tot_req), step=50.0, key=f"ad_tot_{pid_str}_{idx}")
                            ad_notes = st.text_input("Note:", value=str(parsed_data.get("notes") or ""), key=f"ad_notes_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button("💾 Salva Avviso AdE 36-bis in Archivio", key=f"btn_save_ade_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_ade = {
                                "profile_id": pid_str,
                                "tax_year": int(ad_yr),
                                "doc_type": "ADE_NOTICE_36BIS",
                                "issuer_name": "AGENZIA DELLE ENTRATE",
                                "protocol_or_code": ad_code,
                                "tax_withheld_or_due": ad_due,
                                "tax_paid": ad_paid,
                                "penalty_amount": ad_sanz,
                                "interest_amount": ad_int,
                                "total_due": ad_tot,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": ad_notes,
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_ade)
                            st.success(f"✅ Comunicazione AdE 36-bis registrata con ID #{v_id}!")
                            st.rerun()

                elif dt == "PRECOMPILATA_ADE":
                    ref_ade = float(parsed_data.get("secondary_amount", 0.0))
                    unused = parsed_data.get("metadata_json", {}).get("unused_data", {}) if isinstance(parsed_data.get("metadata_json"), dict) else {}
                    rent_info = unused.get("rent_contract", {})
                    rw_info = unused.get("foreign_monitoring_rw", {})

                    st.markdown(
                        f"""<div style="background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #3b82f6;">🏛️ File #{idx+1}: Modello 730 Precompilato AdE (Redditi {parsed_data.get('tax_year', 2025)})</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 3px 8px; border-radius: 4px; font-weight: 600;">ℹ️ Precompilata Agenzia delle Entrate</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Reddito Complessivo", fmt_eur(parsed_data.get("gross_amount", 0.0)), "Prospetto di Liquidazione")
                    with c_m2:
                        metric_card("Imposta Netta IRPEF", fmt_eur(parsed_data.get("tax_withheld_or_due", 0.0)), "Calcolata dall'AdE")
                    with c_m3:
                        metric_card("Ritenute Subite (CU)", fmt_eur(parsed_data.get("tax_paid", 0.0)), "Certificate dai sostituti")
                    with c_m4:
                        metric_card("Rimborso Spettante AdE", fmt_eur(ref_ade), "A Credito del Contribuente", delta_color="normal")

                    # Sezione Dati non utilizzati AdE
                    if rent_info.get("detected") or rw_info.get("detected"):
                        st.warning(
                            "⚠️ **DATI NON UTILIZZATI RILEVATI DALL'AGENZIA DELLE ENTRATE:**\n\n"
                            + (f"- 🏠 **Canone di Locazione (Art. 15 TUIR):** Contratto registrato Atto `{rent_info.get('act_code')}` (Attivo per {rent_info.get('active_days')} gg, canone € {rent_info.get('rent_amount')}). "
                               f"L'AdE **non** lo ha inserito automaticamente. Integrando la detrazione studenti fuori sede in **Quadro E (Rigo E8 cod. 18)**, recuperi **+€ {rent_info.get('recoverable_deduction_19pct'):.2f} di maggior rimborso**!\n" if rent_info.get("detected") else "")
                            + ("- 🌐 **Monitoraggio Estero & Investimenti:** L'AdE segnala attività estere pregresse non riportate nei quadri precompilati. Integra i dati del rendiconto DEGIRO (Quadri RT e W) per evitare avvisi di irregolarità 36-bis con sanzioni 30%.\n" if rw_info.get("detected") else "")
                        )

                    with st.expander(f"🔍 Dettagli & Modifica Campi Precompilata {parsed_data.get('tax_year')}", expanded=False):
                        c_adp1, c_adp2 = st.columns(2)
                        with c_adp1:
                            adp_yr = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2025)), key=f"adp_yr_{pid_str}_{idx}")
                            adp_gross = st.number_input("Reddito Complessivo (€):", value=float(parsed_data.get("gross_amount", 0.0)), step=500.0, key=f"adp_gr_{pid_str}_{idx}")
                            adp_net = st.number_input("Imposta Netta (€):", value=float(parsed_data.get("tax_withheld_or_due", 0.0)), step=100.0, key=f"adp_net_{pid_str}_{idx}")
                        with c_adp2:
                            adp_wh = st.number_input("Ritenute CU (€):", value=float(parsed_data.get("tax_paid", 0.0)), step=100.0, key=f"adp_wh_{pid_str}_{idx}")
                            adp_ref = st.number_input("Rimborso Calcolato AdE (€):", value=float(ref_ade), step=50.0, key=f"adp_ref_{pid_str}_{idx}")
                            adp_notes = st.text_input("Note:", value=str(parsed_data.get("notes") or ""), key=f"adp_notes_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button(f"💾 Salva Precompilata AdE Anno {parsed_data.get('tax_year')} in Archivio", key=f"btn_save_adp_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_adp = {
                                "profile_id": pid_str,
                                "tax_year": int(adp_yr),
                                "doc_type": "PRECOMPILATA_ADE",
                                "issuer_name": "AGENZIA DELLE ENTRATE",
                                "protocol_or_code": "PRECOMPILATA-730-2026",
                                "gross_amount": adp_gross,
                                "net_taxable_amount": adp_gross,
                                "tax_withheld_or_due": adp_net,
                                "tax_paid": adp_wh,
                                "secondary_amount": adp_ref,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": adp_notes,
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_adp)
                            st.success(f"✅ Modello 730 Precompilato registrato con ID #{v_id}!")
                            st.rerun()

                elif dt == "BANK_STATEMENT_RW":
                    b_name = parsed_data.get("issuer_name") or "Banca Estera"
                    meta_b = parsed_data.get("metadata_json", {}) if isinstance(parsed_data.get("metadata_json"), dict) else {}
                    is_ex = meta_b.get("is_ivafe_exempt", True)

                    st.markdown(
                        f"""<div style="background: rgba(6, 182, 212, 0.05); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #06b6d4;">🌐 File #{idx+1}: Conto Corrente Estero ({b_name}) — Quadro RW / IVAFE</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(6, 182, 212, 0.2); color: #22d3ee; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{'🟢 ESENTE IVAFE (< € 5.000)' if is_ex else '🟡 IVAFE DOVUTA'}</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Giacenza Media Annua", fmt_eur(parsed_data.get("gross_amount", 0.0)), "Rilevante ai fini IVAFE")
                    with c_m2:
                        metric_card("Saldo al 31/12", fmt_eur(parsed_data.get("net_taxable_amount", 0.0)), "Consistenza finale Quadro RW")
                    with c_m3:
                        metric_card("Stato IVAFE", "ESENTE (€ 0,00)" if is_ex else "DOVUTA (€ 34,20)", "Art. 19 c. 18 D.L. 201/2011")
                    with c_m4:
                        metric_card("IBAN / Identificativo", str(meta_b.get("iban") or "Estero"), "Monitoraggio Fiscale")

                    with st.expander(f"🔍 Dettagli & Modifica Campi Conto {b_name} {parsed_data.get('tax_year')}", expanded=False):
                        c_bk1, c_bk2 = st.columns(2)
                        with c_bk1:
                            bk_yr = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2025)), key=f"bk_yr_{pid_str}_{idx}")
                            bk_iss = st.text_input("Banca:", value=str(b_name), key=f"bk_iss_{pid_str}_{idx}")
                            bk_gm = st.number_input("Giacenza Media (€):", value=float(parsed_data.get("gross_amount", 0.0)), step=100.0, key=f"bk_gm_{pid_str}_{idx}")
                        with c_bk2:
                            bk_sf = st.number_input("Saldo Finale (€):", value=float(parsed_data.get("net_taxable_amount", 0.0)), step=100.0, key=f"bk_sf_{pid_str}_{idx}")
                            bk_iv = st.number_input("IVAFE Dovuta (€):", value=float(parsed_data.get("secondary_amount", 0.0)), step=10.0, key=f"bk_iv_{pid_str}_{idx}")
                            bk_notes = st.text_input("Note:", value=str(parsed_data.get("notes") or ""), key=f"bk_notes_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button(f"💾 Salva Conto Estero ({b_name} {parsed_data.get('tax_year')}) in Archivio", key=f"btn_save_bk_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_bk = {
                                "profile_id": pid_str,
                                "tax_year": int(bk_yr),
                                "doc_type": "BANK_STATEMENT_RW",
                                "issuer_name": bk_iss,
                                "protocol_or_code": meta_b.get("iban") or f"ESTERO-{bk_iss[:10]}-{bk_yr}",
                                "gross_amount": bk_gm,
                                "net_taxable_amount": bk_sf,
                                "secondary_amount": bk_iv,
                                "asset_monitoring_val": bk_sf,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": bk_notes,
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_bk)
                            st.success(f"✅ Conto Estero {bk_iss} registrato con ID #{v_id}!")
                            st.rerun()

                elif dt == "RENT_EXPENSE":
                    r_amt = float(parsed_data.get("gross_amount", 0.0))
                    r_ded = float(parsed_data.get("secondary_amount", 0.0))
                    r_ben = parsed_data.get("issuer_name") or "Locatore"
                    meta_r = parsed_data.get("metadata_json", {}) if isinstance(parsed_data.get("metadata_json"), dict) else {}

                    st.markdown(
                        f"""<div style="background: rgba(168, 85, 247, 0.05); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-size: 16px; font-weight: 700; color: #a855f7;">🏠 File #{idx+1}: Spesa di Locazione / Contratto Studenti Fuori Sede ({r_ben})</span>
                                    <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                </div>
                                <span style="font-size: 11px; background: rgba(168, 85, 247, 0.2); color: #c084fc; padding: 3px 8px; border-radius: 4px; font-weight: 600;">✨ Detrazione 19% Sbloccata</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                    with c_m1:
                        metric_card("Canone Pagato / Maturato", fmt_eur(r_amt), "Comprovato da Bonifico/Atto")
                    with c_m2:
                        metric_card("Detrazione IRPEF 19%", f"+{fmt_eur(r_ded)}", "Art. 15 c. 1 lett. i-sexies TUIR", delta_color="normal")
                    with c_m3:
                        metric_card("Rigo Destinazione 730", "Quadro E, Rigo E8 cod. 18", "Spese alloggio studenti")
                    with c_m4:
                        metric_card("Riferimento Atto", str(meta_r.get("contract_code") or "TGU-2025-3T-016522"), "Contratto Registrato AdE")

                    with st.expander(f"🔍 Dettagli & Modifica Campi Locazione {parsed_data.get('tax_year')}", expanded=False):
                        c_rn1, c_rn2 = st.columns(2)
                        with c_rn1:
                            rn_yr = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data.get("tax_year", 2025)), key=f"rn_yr_{pid_str}_{idx}")
                            rn_ben = st.text_input("Beneficiario / Locatore:", value=str(r_ben), key=f"rn_ben_{pid_str}_{idx}")
                            rn_amt = st.number_input("Canone Pagato (€):", value=float(r_amt), step=50.0, key=f"rn_amt_{pid_str}_{idx}")
                        with c_rn2:
                            rn_ded = st.number_input("Detrazione 19% Spettante (€):", value=float(r_ded), step=10.0, key=f"rn_ded_{pid_str}_{idx}")
                            rn_notes = st.text_input("Note:", value=str(parsed_data.get("notes") or ""), key=f"rn_notes_{pid_str}_{idx}")

                    col_save_b1, _ = st.columns([1.5, 3])
                    with col_save_b1:
                        if st.button("💾 Salva Spesa Locazione in Archivio", key=f"btn_save_rn_{pid_str}_{idx}", type="primary", use_container_width=True):
                            to_save_rn = {
                                "profile_id": pid_str,
                                "tax_year": int(rn_yr),
                                "doc_type": "RENT_EXPENSE",
                                "issuer_name": rn_ben,
                                "protocol_or_code": parsed_data.get("protocol_or_code"),
                                "gross_amount": rn_amt,
                                "net_taxable_amount": rn_amt,
                                "secondary_amount": rn_ded,
                                "metadata_json": parsed_data.get("metadata_json"),
                                "notes": rn_notes,
                                "source_filename": filename,
                            }
                            v_id = record_verification_document(engine, to_save_rn)
                            st.success(f"✅ Spesa di Locazione registrata con ID #{v_id}!")
                            st.rerun()

                else:
                    # Modello 730 / Redditi PF standard
                    is_730_4 = "730-4" in str(parsed_data.get("notes") or "") or "MOD 730/4" in filename.upper() or "730-4" in filename.upper()
                    has_zero_income = (parsed_data.get("gross_income", 0.0) == 0.0 and parsed_data.get("net_tax_irpef", 0.0) == 0.0)

                    with st.container():
                        if is_730_4 or has_zero_income:
                            st.error(
                                f"⚠️ **ATTENZIONE SU {filename} (Modello 730-4 Conguaglio, 1 Pagina)**\n\n"
                                f"Questo file ha dimensione ridotta (~258 KB, 1 pagina) ed è il **Modello 730-4** (comunicazione di conguaglio per il sostituto d'imposta).\n\n"
                                f"In questo prospetto **non sono presenti i quadri dei redditi** (C, D, E, W/RW, T), per questo motivo tutti i campi risultano a 0,00.\n\n"
                                f"👉 **Come risolvere:** Seleziona dalla tua cartella *Download* il file PDF completo da **1,5 MB (16 pagine)** "
                                f"(denominato `730_T25092611423143672686_SLDLSN00P19M208Y.pdf` senza spazi o variante `(4).pdf`)."
                            )
                        else:
                            st.markdown(
                                f"""<div style="background: rgba(16, 185, 129, 0.04); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 14px 18px; margin-top: 10px; margin-bottom: 8px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <span style="font-size: 16px; font-weight: 700; color: #10b981;">📄 File #{idx+1}: Modello {parsed_data.get('filing_year', int(parsed_data.get('tax_year', 2024))+1)} (Redditi {parsed_data['tax_year']})</span>
                                            <span style="font-size: 12px; color: #94a3b8; margin-left: 10px;">{filename}</span>
                                        </div>
                                        <span style="font-size: 11px; background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 3px 8px; border-radius: 4px; font-weight: 600;">✅ Dati Estratti con Successo</span>
                                    </div>
                                </div>""",
                                unsafe_allow_html=True,
                            )

                            # Bento Grid Metriche Estratte
                            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                            with c_m1:
                                metric_card("Reddito Complessivo", fmt_eur(parsed_data["gross_income"]), f"Imponibile: {fmt_eur(parsed_data['taxable_income'])}")
                            with c_m2:
                                metric_card("Imposta Netta IRPEF", fmt_eur(parsed_data["net_tax_irpef"]), f"Modello {parsed_data['model_type']}")
                            with c_m3:
                                metric_card("Plusvalenze Quadro T/RT", fmt_eur(parsed_data["capital_gains_declared"]), f"Sostitutiva 26%: {fmt_eur(parsed_data['substitute_tax_paid'])}")
                            with c_m4:
                                metric_card("Attività Estere Monitorate", fmt_eur(parsed_data["foreign_assets_val"]), f"IVAFE 0,20%: {fmt_eur(parsed_data['ivafe_paid'])}")

                        # Expander opzionale per verifica o rettifica dettagliata
                        exp_label = f"🔍 Dettagli & Modifica Manuale Campi Anno {parsed_data['tax_year']}"
                        with st.expander(exp_label, expanded=False):
                            c_p1, c_p2 = st.columns(2)
                            with c_p1:
                                p_year = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data["tax_year"]), key=f"p_yr_{pid_str}_{idx}")
                                p_model = st.selectbox("Modello:", ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"], index=0 if parsed_data["model_type"] == "730_ORDINARIO" else (1 if parsed_data["model_type"] == "730_INTEGRATIVO" else 2), key=f"p_md_{pid_str}_{idx}")
                                p_proto = st.text_input("Protocollo Telematico:", value=str(parsed_data.get("protocol_id") or ""), key=f"p_pr_{pid_str}_{idx}")
                                p_gross = st.number_input("Reddito Complessivo (€):", value=float(parsed_data["gross_income"]), step=500.0, key=f"p_gr_{pid_str}_{idx}")
                                p_taxable = st.number_input("Reddito Imponibile (€):", value=float(parsed_data.get("taxable_income", parsed_data["gross_income"])), step=500.0, key=f"p_tx_{pid_str}_{idx}")
                                p_net_tax = st.number_input("Imposta Netta IRPEF (€):", value=float(parsed_data["net_tax_irpef"]), step=100.0, key=f"p_nt_{pid_str}_{idx}")
                            with c_p2:
                                p_cg = st.number_input("Plusvalenze Quadro T/RT (€):", value=float(parsed_data["capital_gains_declared"]), step=100.0, key=f"p_cg_{pid_str}_{idx}")
                                p_cl = st.number_input("Minusvalenze Compensate T13 (€):", value=float(parsed_data["capital_losses_offset"]), step=100.0, key=f"p_cl_{pid_str}_{idx}")
                                p_sub = st.number_input("Imposta Sostitutiva 26% (Rigo 321) (€):", value=float(parsed_data["substitute_tax_paid"]), step=50.0, key=f"p_sb_{pid_str}_{idx}")
                                p_ivafe = st.number_input("IVAFE (Rigo 307 / Quadro W) (€):", value=float(parsed_data["ivafe_paid"]), step=10.0, key=f"p_iv_{pid_str}_{idx}")
                                p_for = st.number_input("Attività Estere Valore Finale (€):", value=float(parsed_data["foreign_assets_val"]), step=1000.0, key=f"p_fa_{pid_str}_{idx}")

                        col_save_b1, _ = st.columns([1.5, 3])
                        with col_save_b1:
                            if st.button(f"💾 Salva Dichiarazione Anno {parsed_data['tax_year']} in Archivio", key=f"btn_save_parsed_{pid_str}_{idx}", type="primary", use_container_width=True):
                                to_save = {
                                    "profile_id": pid_str,
                                    "tax_year": int(parsed_data["tax_year"]),
                                    "filing_year": int(parsed_data["tax_year"]) + 1,
                                    "model_type": str(parsed_data["model_type"]),
                                    "protocol_id": str(parsed_data.get("protocol_id") or "") if parsed_data.get("protocol_id") else None,
                                    "gross_income": float(parsed_data["gross_income"]),
                                    "taxable_income": float(parsed_data.get("taxable_income", parsed_data["gross_income"])),
                                    "net_tax_irpef": float(parsed_data["net_tax_irpef"]),
                                    "capital_gains_declared": float(parsed_data["capital_gains_declared"]),
                                    "capital_losses_offset": float(parsed_data["capital_losses_offset"]),
                                    "substitute_tax_paid": float(parsed_data["substitute_tax_paid"]),
                                    "ivafe_paid": float(parsed_data["ivafe_paid"]),
                                    "foreign_assets_val": float(parsed_data["foreign_assets_val"]),
                                    "notes": str(parsed_data.get("notes") or f"Importato da file: {filename}"),
                                    "source_filename": filename,
                                }
                                decl_id = record_declaration(engine, to_save)
                                st.success(f"✅ Dichiarazione Anno {parsed_data['tax_year']} registrata con ID #{decl_id}!")
                                st.rerun()

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ── SEZIONE SECONDARIA: INSERIMENTO MANUALE COLLASSATO ──
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        with st.expander("✍️ Inserimento Manuale a Modulo (Senza File PDF)", expanded=False):
            st.caption("Compila manualmente i dati della dichiarazione nel caso tu non disponga del file PDF originale rilasciato dall'AdE.")
            with st.form(f"manual_decl_form_{pid_str}"):
                c_m1, c_m2, c_m3 = st.columns(3)
                with c_m1:
                    st.markdown("###### 📋 Dati Generali")
                    fm_year = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=selected_tax_year)
                    fm_model = st.selectbox("Tipologia Modello:", ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"])
                    fm_proto = st.text_input("Protocollo AdE (opzionale):", placeholder="es. 2506241029384756100234")
                with c_m2:
                    st.markdown("###### 💼 Redditi & IRPEF")
                    fm_gross = st.number_input("Reddito Complessivo Lordo (€):", min_value=0.0, value=0.0, step=1000.0)
                    fm_taxable = st.number_input("Reddito Imponibile (€):", min_value=0.0, value=0.0, step=1000.0)
                    fm_net_irpef = st.number_input("Imposta Netta IRPEF (€):", min_value=0.0, value=0.0, step=100.0)
                with c_m3:
                    st.markdown("###### 📈 Finanza & Estero (Quadro W/T)")
                    fm_cg = st.number_input("Plusvalenze Dichiarate (T11) (€):", min_value=0.0, value=0.0, step=100.0)
                    fm_cl = st.number_input("Minusvalenze Compensate (T13) (€):", min_value=0.0, value=0.0, step=100.0)
                    fm_sub = st.number_input("Imposta Sostitutiva 26% (321) (€):", min_value=0.0, value=0.0, step=50.0)
                    fm_ivafe = st.number_input("IVAFE Versata (307) (€):", min_value=0.0, value=0.0, step=10.0)
                    fm_for = st.number_input("Monitoraggio Estero RW (€):", min_value=0.0, value=0.0, step=1000.0)

                fm_notes = st.text_input("Note aggiuntive:", placeholder="es. Inserito da prospetto commercialista")

                submitted = st.form_submit_button("Salva Dichiarazione Manuale", type="primary", use_container_width=True)
                if submitted:
                    to_save_man = {
                        "profile_id": pid_str,
                        "tax_year": int(fm_year),
                        "filing_year": int(fm_year) + 1,
                        "model_type": fm_model,
                        "protocol_id": fm_proto if fm_proto else None,
                        "gross_income": fm_gross,
                        "taxable_income": fm_taxable if fm_taxable > 0 else fm_gross,
                        "net_tax_irpef": fm_net_irpef,
                        "capital_gains_declared": fm_cg,
                        "capital_losses_offset": fm_cl,
                        "substitute_tax_paid": fm_sub,
                        "ivafe_paid": fm_ivafe,
                        "foreign_assets_val": fm_for,
                        "notes": fm_notes,
                        "source_filename": "Inserimento manuale",
                    }
                    new_id = record_declaration(engine, to_save_man)
                    st.success(f"✅ Dichiarazione Anno {fm_year} salvata con successo (ID #{new_id})!")
                    st.rerun()

        # ── TAB C: TABELLA MODIFICABILE (DATA EDITOR) ──
        st.markdown("---")
        st.markdown("##### 📝 Registro Storico Dichiarazioni (Data Editor Persistente)")
        st.caption("Modifica direttamente i valori nelle celle e premi 'Salva Modifiche' per aggiornare il database SQLite/MySQL.")

        current_decls = get_declarations(engine, profile_id=pid_str)
        if current_decls:
            df_decls = pd.DataFrame(current_decls)
            cols_show = [
                "id",
                "tax_year",
                "model_type",
                "gross_income",
                "taxable_income",
                "net_tax_irpef",
                "capital_gains_declared",
                "capital_losses_offset",
                "substitute_tax_paid",
                "ivafe_paid",
                "foreign_assets_val",
                "protocol_id",
                "notes",
            ]
            cols_avail = [c for c in cols_show if c in df_decls.columns]
            df_edit_src = df_decls[cols_avail].copy()

            cfg_decls = {
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "tax_year": st.column_config.NumberColumn("Anno Imposta", disabled=True, width="small"),
                "model_type": st.column_config.SelectboxColumn("Modello", options=["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"], width="medium"),
                "gross_income": st.column_config.NumberColumn("Reddito Lordo (€)", format="€ %,.2f"),
                "taxable_income": st.column_config.NumberColumn("Reddito Imponibile (€)", format="€ %,.2f"),
                "net_tax_irpef": st.column_config.NumberColumn("Imposta Netta IRPEF (€)", format="€ %,.2f"),
                "capital_gains_declared": st.column_config.NumberColumn("Plusvalenze T11 (€)", format="€ %,.2f"),
                "capital_losses_offset": st.column_config.NumberColumn("Minusvalenze T13 (€)", format="€ %,.2f"),
                "substitute_tax_paid": st.column_config.NumberColumn("Sostitutiva 321 (€)", format="€ %,.2f"),
                "ivafe_paid": st.column_config.NumberColumn("IVAFE 307 (€)", format="€ %,.2f"),
                "foreign_assets_val": st.column_config.NumberColumn("Estero RW (€)", format="€ %,.2f"),
                "protocol_id": st.column_config.TextColumn("Protocollo Telematico", width="medium"),
                "notes": st.column_config.TextColumn("Note", width="large"),
            }

            edited_df = st.data_editor(
                df_edit_src,
                column_config=cfg_decls,
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_decls_{pid_str}",
            )

            col_btn_ed1, col_btn_ed2 = st.columns([1, 4])
            with col_btn_ed1:
                if st.button("💾 Salva Modifiche Tabella", key=f"btn_save_grid_{pid_str}", type="primary"):
                    # Salva le righe aggiornate
                    for _, row in edited_df.iterrows():
                        r_dict = row.to_dict()
                        if pd.isna(r_dict.get("tax_year")):
                            continue
                        to_up = {
                            "profile_id": pid_str,
                            "tax_year": int(r_dict["tax_year"]),
                            "filing_year": int(r_dict["tax_year"]) + 1,
                            "model_type": str(r_dict.get("model_type", "730_ORDINARIO")),
                            "protocol_id": str(r_dict.get("protocol_id", "")) if not pd.isna(r_dict.get("protocol_id")) else None,
                            "gross_income": float(r_dict.get("gross_income", 0.0) or 0.0),
                            "taxable_income": float(r_dict.get("taxable_income") or r_dict.get("gross_income", 0.0) or 0.0),
                            "net_tax_irpef": float(r_dict.get("net_tax_irpef", 0.0) or 0.0),
                            "capital_gains_declared": float(r_dict.get("capital_gains_declared", 0.0) or 0.0),
                            "capital_losses_offset": float(r_dict.get("capital_losses_offset", 0.0) or 0.0),
                            "substitute_tax_paid": float(r_dict.get("substitute_tax_paid", 0.0) or 0.0),
                            "ivafe_paid": float(r_dict.get("ivafe_paid", 0.0) or 0.0),
                            "foreign_assets_val": float(r_dict.get("foreign_assets_val", 0.0) or 0.0),
                            "notes": str(r_dict.get("notes", "")) if not pd.isna(r_dict.get("notes")) else None,
                        }
                        record_declaration(engine, to_up)
                    st.success("Tutte le modifiche sono state sincronizzate con il database!")
                    st.rerun()

            with col_btn_ed2:
                # Opzione di cancellazione per ID
                ids_list = [int(r["id"]) for r in current_decls]
                col_d1, col_d2 = st.columns([2, 1])
                with col_d1:
                    del_id = st.selectbox("Seleziona dichiarazione da rimuovere:", ids_list, format_func=lambda x: f"ID #{x} (Anno {next((r['tax_year'] for r in current_decls if r['id']==x), '')})", key=f"sel_del_{pid_str}")
                with col_d2:
                    if st.button("🗑️ Elimina Record", key=f"btn_del_decl_{pid_str}"):
                        delete_declaration(engine, del_id)
                        st.warning(f"Dichiarazione ID #{del_id} eliminata.")
                        st.rerun()
        else:
            st.info("Nessuna dichiarazione ancora salvata in archivio. Carica un PDF o usa l'inserimento manuale in alto.")

    # ============================================================
    # SUBTAB 2: DASHBOARD STORICA & ZAINETTO FISCALE
    # ============================================================
    with subtab_dash:
        st.markdown("#### 📊 Dashboard Storica Pluriennale & Zainetto Fiscale")
        st.caption("Analisi a cascata dell'imponibile finanziario e monitoraggio delle tranches di minusvalenze con scadenza a 4 anni.")

        # ── 1. GRAFICO A CASCATA PLUSVALENZE VS MINUSVALENZE ──
        all_decls = get_declarations(engine, profile_id=pid_str)
        if all_decls:
            df_chart = pd.DataFrame(all_decls).sort_values("tax_year")
            # Considera gli ultimi 5-7 anni
            df_chart = df_chart.tail(6)

        # ── 1. GRAFICO A CASCATA PLUSVALENZE VS MINUSVALENZE ──
        all_decls = get_declarations(engine, profile_id=pid_str)
        if all_decls:
            df_chart = pd.DataFrame(all_decls).sort_values("tax_year")
            # Considera gli ultimi 5-7 anni
            df_chart = df_chart.tail(6)

            col_ch_t1, col_ch_t2 = st.columns([1.5, 1.5])
            with col_ch_t1:
                st.markdown("##### 📈 Dinamica Fiscale Pluriennale")
            with col_ch_t2:
                chart_type = st.radio(
                    "Modalità Grafico:",
                    ["📊 Confronto Pluriennale", "🌊 Cascata Fiscale (Waterfall)"],
                    horizontal=True,
                    key=f"chart_mode_sel_{pid_str}",
                )

            if chart_type == "🌊 Cascata Fiscale (Waterfall)":
                decl_cur = next((d for d in all_decls if int(d.get("tax_year", 0)) == int(selected_tax_year)), all_decls[-1])
                cg_val = float(decl_cur.get("capital_gains_declared", 0.0) or 0.0)
                cl_val = float(decl_cur.get("capital_losses_offset", 0.0) or 0.0)
                sub_val = float(decl_cur.get("substitute_tax_paid", 0.0) or 0.0)
                taxable_net = max(0.0, cg_val - cl_val)
                final_net = max(0.0, taxable_net - sub_val)

                fig_wf = go.Figure(go.Waterfall(
                    name=f"Liquidazione {decl_cur.get('tax_year', selected_tax_year)}",
                    orientation="v",
                    measure=["relative", "relative", "total", "relative", "total"],
                    x=[
                        "Plusvalenze Lorde (T11)",
                        "Minus Compensate (T13)",
                        "Base Imponibile Netta",
                        "Imposta Sostitutiva 26% (321)",
                        "Utile Netto Rimasto",
                    ],
                    textposition="outside",
                    text=[fmt_eur_it(cg_val), f"-{fmt_eur_it(cl_val)}", fmt_eur_it(taxable_net), f"-{fmt_eur_it(sub_val)}", fmt_eur_it(final_net)],
                    y=[cg_val, -cl_val, 0, -sub_val, 0],
                    connector={"line": {"color": "rgba(255, 255, 255, 0.25)"}},
                    decreasing={"marker": {"color": "#ef4444"}},
                    increasing={"marker": {"color": "#10b981"}},
                    totals={"marker": {"color": "#38bdf8"}},
                ))
                fig_wf.update_layout(
                    title=dict(
                        text=f"Cascata di Liquidazione Fiscale — Anno d'Imposta {decl_cur.get('tax_year', selected_tax_year)} (Art. 68 TUIR)",
                        font=dict(size=14, color="#ffffff"),
                    ),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=390,
                    yaxis=dict(title="Importo (€)", gridcolor="rgba(255,255,255,0.08)"),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})
            else:
                fig_bar = go.Figure()
                # Plusvalenze
                fig_bar.add_trace(go.Bar(
                    x=[f"Anno {y}" for y in df_chart["tax_year"]],
                    y=df_chart["capital_gains_declared"],
                    name="Plusvalenze Dichiarate (T11)",
                    marker_color="#10b981",
                    text=[fmt_eur_it(v) for v in df_chart["capital_gains_declared"]],
                    textposition="auto",
                ))
                # Minusvalenze compensate
                fig_bar.add_trace(go.Bar(
                    x=[f"Anno {y}" for y in df_chart["tax_year"]],
                    y=df_chart["capital_losses_offset"],
                    name="Minusvalenze Compensate (T13)",
                    marker_color="#f59e0b",
                    text=[fmt_eur_it(v) for v in df_chart["capital_losses_offset"]],
                    textposition="auto",
                ))
                # Imposta Sostitutiva 26%
                fig_bar.add_trace(go.Scatter(
                    x=[f"Anno {y}" for y in df_chart["tax_year"]],
                    y=df_chart["substitute_tax_paid"],
                    name="Sostitutiva Versata (Rigo 321)",
                    mode="lines+markers",
                    line=dict(color="#38bdf8", width=3),
                    marker=dict(size=8),
                    yaxis="y2",
                ))

                fig_bar.update_layout(
                    title=dict(text="Confronto Pluriennale Plusvalenze, Minusvalenze e Imposta Sostitutiva", font=dict(size=14, color="#ffffff")),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    yaxis=dict(title="Importo (€)", gridcolor="rgba(255,255,255,0.08)"),
                    yaxis2=dict(title="Imposta Versata (€)", overlaying="y", side="right", showgrid=False),
                    margin=dict(l=10, r=10, t=50, b=10),
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Carica almeno una dichiarazione per visualizzare il grafico temporale delle plusvalenze.")

        # ── 2. SEZIONE ZAINETTO FISCALE & BADGES SEMAFORICI ──
        st.markdown("---")
        c_z_head1, c_z_head2 = st.columns([2.5, 1.5])
        with c_z_head1:
            st.markdown("##### 💼 Monitoraggio Tranches Zainetto Fiscale (Art. 68 TUIR)")
            st.caption("Ogni pacchetto di minusvalenza ha una scadenza inderogabile di 4 anni solari. Il semaforo indica la conformità con l'Anagrafe Tributaria.")
        with c_z_head2:
            loss_items_all = get_tax_losses(engine, profile_id=pid_str, current_year=selected_tax_year)
            if loss_items_all:
                df_loss_csv = pd.DataFrame(loss_items_all)
                csv_bytes = df_loss_csv.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Esporta Zainetto (CSV Commercialista)",
                    data=csv_bytes,
                    file_name=f"argus_zainetto_fiscale_{pid_str}_{selected_tax_year}.csv",
                    mime="text/csv",
                    key=f"dl_zainetto_csv_{pid_str}",
                    help="Scarica l'estratto delle tranches dello zainetto con scadenza e stato AdE per la dichiarazione dei redditi.",
                )

        # Modale / Form aggiunta nuova tranche
        with st.expander("➕ Registra Nuova Tranche di Minusvalenza (Broker o Certificazione)", expanded=False):
            with st.form(f"form_new_loss_{pid_str}"):
                c_l1, c_l2, c_l3 = st.columns(3)
                with c_l1:
                    l_gen_yr = st.number_input("Anno di Generazione:", min_value=2018, max_value=2030, value=current_year - 1)
                    l_broker = st.selectbox("Intermediario / Broker:", ["DEGIRO", "DIRECTA", "IBKR", "FINECO", "TRADE REPUBLIC", "SCALABLE", "ALTRO"])
                with c_l2:
                    l_init_amt = st.number_input("Minusvalenza Originaria (€):", min_value=0.0, value=1000.0, step=100.0)
                    l_off_amt = st.number_input("Quota Già Compensata (€):", min_value=0.0, value=0.0, step=100.0)
                with c_l3:
                    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                    l_filed = st.checkbox(
                        "Dichiarata all'Agenzia delle Entrate (Quadro RT / F24)",
                        value=True,
                        help="Deseleziona se la minusvalenza è presente solo sul broker estero ma non è stata inclusa nel Modello Redditi.",
                    )

                btn_add_loss = st.form_submit_button("Registra Tranche nello Zainetto", type="primary", use_container_width=True)
                if btn_add_loss:
                    new_l_id = record_tax_loss(
                        engine,
                        {
                            "profile_id": pid_str,
                            "generation_year": int(l_gen_yr),
                            "initial_loss_amount": float(l_init_amt),
                            "offset_amount": float(l_off_amt),
                            "is_officially_filed": l_filed,
                            "broker_source": l_broker,
                            "current_year": current_year,
                        },
                    )
                    st.success(f"Tranche registrata con successo (ID #{new_l_id})!")
                    st.rerun()

        # Visualizzazione Card Tranches con Semafori
        loss_items = get_tax_losses(engine, profile_id=pid_str, current_year=selected_tax_year)
        if loss_items:
            for l_item in loss_items:
                rem = float(l_item["remaining_amount"])
                init = float(l_item["initial_loss_amount"])
                off = float(l_item["offset_amount"])
                gen_y = int(l_item["generation_year"])
                exp_y = int(l_item["expiration_year"])
                broker = str(l_item.get("broker_source", "DEGIRO"))
                status = str(l_item["status"])
                is_filed = bool(l_item["is_officially_filed"])
                l_id = int(l_item["id"])

                # Badge semaforico
                if is_filed:
                    ade_badge = "<span style='background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;'>🟢 REGISTRATA ALL'AdE (Quadro RT)</span>"
                else:
                    ade_badge = "<span style='background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;'>🔴 NON DICHIARATA (Rischio 36-bis)</span>"

                # Status Scadenza
                if status == "EXPIRED":
                    status_badge = "<span style='background: rgba(100, 116, 139, 0.2); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px;'>⚪ DECADUTA</span>"
                elif status == "EXHAUSTED":
                    status_badge = "<span style='background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px;'>⚫ ESAURITA</span>"
                elif exp_y <= selected_tax_year:
                    status_badge = "<span style='background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: 700;'>⏳ SCADE ENTRO L'ANNO</span>"
                else:
                    years_left = exp_y - selected_tax_year
                    status_badge = f"<span style='background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px;'>🟢 VALIDA ({years_left} Anni)</span>"

                pct_used = (off / init * 100.0) if init > 0 else 100.0

                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%);
                                border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;
                                box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <span style="font-weight: 700; color: #ffffff; font-size: 14px; margin-right: 10px;">
                                    Tranche #{l_id} • Origine: Anno {gen_y} ({broker})
                                </span>
                                {status_badge}
                            </div>
                            <div>
                                {ade_badge}
                            </div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 13px; color: #cbd5e1; margin-top: 10px;">
                            <div><b>Minusvalenza Iniziale:</b><br><span style="color: #ffffff; font-weight: 700;">{fmt_eur_it(init)}</span></div>
                            <div><b>Già Compensata:</b><br><span style="color: #f59e0b; font-weight: 700;">{fmt_eur_it(off)} ({pct_used:.1f}%)</span></div>
                            <div><b>Residuo Spendibile:</b><br><span style="color: #10b981; font-weight: 800; font-size: 14px;">{fmt_eur_it(rem)}</span></div>
                            <div><b>Scadenza Fiscale:</b><br><span style="color: #38bdf8; font-weight: 700;">31/12/{exp_y}</span></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Pulsanti di gestione inline
                c_act1, c_act2, c_act3 = st.columns([1.5, 1.5, 4])
                with c_act1:
                    off_input = st.number_input(f"Compensa quota (€) [#{l_id}]:", min_value=0.0, max_value=rem, value=0.0, step=100.0, key=f"inp_off_{l_id}")
                with c_act2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Applica Compensazione", key=f"btn_apply_off_{l_id}") and off_input > 0:
                        update_tax_loss_offset(engine, l_id, off_input)
                        st.success(f"Compensati {fmt_eur_it(off_input)} sulla tranche #{l_id}!")
                        st.rerun()
                with c_act3:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Rimuovi Tranche", key=f"btn_del_loss_{l_id}"):
                        delete_tax_loss(engine, l_id)
                        st.warning(f"Tranche #{l_id} eliminata.")
                        st.rerun()
        else:
            st.info("Nessuna tranche di minusvalenza registrata. Inseriscine una tramite il pannello in alto.")

    # ============================================================
    # SUBTAB 3: AUDIT ADVISOR & RICONCILIAZIONE (ART. 36-BIS)
    # ============================================================
    with subtab_audit:
        st.markdown("#### 🚨 Audit di Riconciliazione Tributaria & Advisor Alert")
        st.caption(
            "Confronto tra i conteggi contabili di ARGUS (broker DeGiro, Directa, IBKR) e quanto formalmente dichiarato all'AdE. "
            "Rileva tempestivamente discrepanze e stima il rischio sanzionatorio ex art. 36-bis d.P.R. 600/1973."
        )

        with st.spinner("Elaborazione audit fiscale in corso..."):
            report = reconcile_with_portfolio(engine, profile_id=pid_str, tax_year=selected_tax_year)

        # ── KPI COMPARATIVI ──
        k_a1, k_a2, k_a3, k_a4 = st.columns(4)
        with k_a1:
            metric_card(
                "Delta Plusvalenze",
                fmt_eur(report.delta_capital_gains),
                delta="Broker vs Dichiarato",
                delta_color="inverse" if abs(report.delta_capital_gains) > 50 else "normal",
                help_text="Differenza tra plusvalenze calcolate dai broker ARGUS e plusvalenze indicate nel Modello 730/Redditi.",
            )
        with k_a2:
            metric_card(
                "Delta IVAFE Estero",
                fmt_eur(report.delta_ivafe),
                delta="Dovuta vs Versata",
                delta_color="inverse" if abs(report.delta_ivafe) > 10 else "normal",
                help_text="Differenza tra IVAFE teorica (0,20% + bolli c/c) e importo versato a modello (Rigo 307).",
            )
        with k_a3:
            metric_card(
                "Minusvalenze in Scadenza",
                fmt_eur(report.total_expiring_losses),
                delta=f"Entro 31/12/{selected_tax_year}",
                delta_color="inverse" if report.total_expiring_losses > 0 else "normal",
                help_text="Minusvalenze che decadono definitivamente al 31 dicembre se non compensate.",
            )
        with k_a4:
            metric_card(
                "Rischio Art. 36-bis",
                fmt_eur(report.art_36_bis_risk_assessment.get("total_potential_liability", 0.0)),
                delta="Sanzione 30% + Recupero",
                delta_color="inverse" if report.total_unfiled_losses > 0 else "normal",
                help_text="Carico tributario potenziale in caso di controllo automatico su minusvalenze non registrate all'AdE.",
            )

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # ── SEZIONE SPECIALE: PREDISPOSIZIONE MODELLO 730 & MATRICE SCOSTAMENTI (AdE vs REALE ARGUS) ──
        predisp_730 = build_730_predisposition_and_variance_audit(engine, profile_id=pid_str, tax_year=selected_tax_year)
        if predisp_730:
            st.markdown("##### 📋 Predisposizione Modello 730 & Matrice Scostamenti (Precompilata AdE vs Dati Reali ARGUS)")
            st.caption(
                "Riconciliazione integrata tra il prospetto grezzo dell'Agenzia delle Entrate e la documentazione probatoria archiviata "
                "(CU Sixtema/ER.GO, Rendiconti DEGIRO RT/W, Conti Esteri N26, Ricevute Bonifici e Contratto di Locazione)."
            )

            c_pd1, c_pd2, c_pd3, c_pd4 = st.columns(4)
            with c_pd1:
                metric_card(
                    "Rimborso 730 Spettante",
                    fmt_eur(predisp_730["new_irpef_refund"]),
                    delta=f"+{fmt_eur(predisp_730['rent_recovered_deduction'])} vs AdE",
                    delta_color="normal",
                    help_text=f"Rimborso IRPEF totale comprensivo del recupero della detrazione affitto (+{fmt_eur_it(predisp_730['rent_recovered_deduction'])}).",
                )
            with c_pd2:
                metric_card(
                    "F24 Debiti Esteri (RT + W)",
                    fmt_eur(predisp_730["f24_foreign_total"]),
                    delta=f"RT 26%: € {predisp_730['rt_sub_tax']:.2f} | W: € {predisp_730['w_ivafe']:.2f}",
                    delta_color="inverse",
                    help_text="Imposte finanziarie estere da versare tramite F24 (Cod. 1100 per imposta sostitutiva 26% e Cod. 4043 per IVAFE).",
                )
            with c_pd3:
                metric_card(
                    "SALDO NETTO EFFETTIVO",
                    fmt_eur(predisp_730["net_tax_balance"]),
                    delta="Credito Netto in Busta Paga",
                    delta_color="normal",
                    help_text="Rimborso netto effettivo a favore del contribuente (Rimborso 730 meno totale versamenti F24).",
                )
            with c_pd4:
                pot_savings = round(predisp_730["rent_recovered_deduction"] + predisp_730["f24_foreign_total"] * 0.3, 2)
                metric_card(
                    "Vantaggio Fiscale ARGUS",
                    f"+{fmt_eur(pot_savings)}",
                    delta="Recupero + Zero Sanzioni",
                    delta_color="normal",
                    help_text="Beneficio economico generato: recupero detrazione locazione ignorata da AdE + prevenzione sanzioni 30% su investimenti esteri.",
                )

            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
                            border: 1px solid rgba(59, 130, 246, 0.3); border-left: 4px solid #3b82f6; border-radius: 10px; padding: 16px 20px; margin: 12px 0 16px 0;">
                    <div style="font-weight: 700; color: #60a5fa; font-size: 15px; margin-bottom: 8px;">
                        💡 Sintesi di Predisposizione & Ottimizzazione Fiscale ARGUS (Anno {selected_tax_year}):
                    </div>
                    <ul style="color: #cbd5e1; font-size: 13px; line-height: 1.7; margin: 0; padding-left: 18px;">
                        <li><b>Recupero Canoni di Locazione (+{fmt_eur_it(predisp_730['rent_recovered_deduction'])}):</b> L'AdE ha escluso il contratto registrato classificandolo come <i>'Dato non utilizzato'</i>.
                        Inserendo la detrazione studenti universitari fuori sede in <b>Quadro E (Rigo E8/E10 cod. 18)</b>, il rimborso sale da <b>{fmt_eur_it(predisp_730['ade_refund'])}</b> a <b>{fmt_eur_it(predisp_730['new_irpef_refund'])}</b>!</li>
                        <li><b>Integrazione Obbligatoria DEGIRO (Zero Sanzioni):</b> La precompilata ometteva i quadri finanziari. Integrando il <b>Quadro RT</b> (plusvalenze € 793,00, imposta 26% <b>€ {predisp_730['rt_sub_tax']:.2f}</b>) e il <b>Quadro W</b> (attività estere € 36.098,00, IVAFE <b>€ {predisp_730['w_ivafe']:.2f}</b>), si evitano avvisi 36-bis e sanzioni dal 30% al 90%.</li>
                        <li><b>Esclusione IVAFE Conti Esteri:</b> N26 Bank presenta una giacenza media di € 734,91, ampiamente sotto la soglia di € 5.000,00: <b>esente da IVAFE</b> ex art. 19 c. 18 D.L. 201/2011.</li>
                        <li><b>Esito Netto Conclusivo:</b> Incassi <b>{fmt_eur_it(predisp_730['new_irpef_refund'])}</b> di rimborso IRPEF e versi <b>{fmt_eur_it(predisp_730['f24_foreign_total'])}</b> tramite F24, chiudendo l'anno fiscale con un <b>saldo positivo reale di +{fmt_eur_it(predisp_730['net_tax_balance'])}</b> in piena conformità tributaria.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

            df_p = pd.DataFrame(predisp_730["metrics_table"])
            df_p["ade_fmt"] = df_p["ade_val"].apply(lambda v: fmt_eur_it(float(v)) if float(v) > 0 or v == 0.0 else "—")
            df_p["argus_fmt"] = df_p["argus_val"].apply(lambda v: fmt_eur_it(float(v)) if float(v) > 0 or v == 0.0 else "—")
            df_p["delta_fmt"] = df_p["delta"].apply(lambda v: f"{'+' if float(v)>0 else ''}{fmt_eur_it(float(v))}")
            def _map_p_badge(s):
                if s == "ADVANTAGE":
                    return "🟢 Ottimizzazione (+€)"
                elif s == "WARNING":
                    return "🟡 Da Integrare (F24)"
                elif s == "DANGER":
                    return "🔴 Rischio 36-bis"
                return "🟢 Conforme"
            df_p["status_badge"] = df_p["status"].apply(_map_p_badge)

            st.dataframe(
                df_p[["category", "item", "ade_fmt", "argus_fmt", "delta_fmt", "status_badge", "notes"]],
                column_config={
                    "category": st.column_config.TextColumn("Ambito", width="small"),
                    "item": st.column_config.TextColumn("Voce Fiscale", width="medium"),
                    "ade_fmt": st.column_config.TextColumn("1. Precompilata AdE", width="small"),
                    "argus_fmt": st.column_config.TextColumn("2. Predisposizione ARGUS", width="small"),
                    "delta_fmt": st.column_config.TextColumn("Scostamento (Delta)", width="small"),
                    "status_badge": st.column_config.TextColumn("Stato Audit", width="small"),
                    "notes": st.column_config.TextColumn("Diagnosi & Riferimenti Normativi", width="large"),
                },
                hide_index=True,
                use_container_width=True,
            )

            with st.expander("📋 Istruzioni Operative: Modifica Portale AdE & Compilazione Modello F24", expanded=False):
                st.markdown(
                    f"""
                    **1. Modifica sul Portale dell'Agenzia delle Entrate (Modello 730 Precompilato):**
                    - Accedi a *dichiarazioneprecompilata.agenziaentrate.gov.it* con SPID o CIE.
                    - Seleziona **Modifica 730**.
                    - Accedi al **Quadro E (Oneri e Spese)** -> Sezione I (Spese per le quali spetta la detrazione d'imposta del 19%).
                    - Al Rigo **E8 / E10**, inserisci Codice Spesa **18** (*Spese per canoni di locazione sostenute da studenti universitari fuori sede*) e importo **€ 519,00** (o € 519,45).
                    - Verifica che nel prospetto di liquidazione il rimborso a tuo favore salga da **€ 625,00** a **€ 723,70**!

                    **2. Compilazione e Versamento Modello F24 (Investimenti Esteri DEGIRO):**
                    - Sezione Erario:
                      * **Codice Tributo 1100:** Imposta sostitutiva su plusvalenze di natura finanziaria — Anno di riferimento: `{selected_tax_year}` — Importo a debito: **€ {predisp_730['rt_sub_tax']:.2f}**
                      * **Codice Tributo 4043:** IVAFE - Imposta sul valore delle attività finanziarie detenute all'estero — Anno di riferimento: `{selected_tax_year}` — Importo a debito: **€ {predisp_730['w_ivafe']:.2f}**
                    - **Totale Modello F24:** **€ {predisp_730['f24_foreign_total']:.2f}** da versare entro il termine ordinario delle imposte sui redditi.
                    """
                )
            st.markdown("---")

        # ── 1. MATRICE DI AUDIT TRIANGOLARE (ARGUS vs BROKER vs 730 vs AdE 36-BIS) ──
        tri_audit = build_triangular_tax_audit(engine, profile_id=pid_str, tax_year=selected_tax_year)
        if tri_audit.get("has_audit_data"):
            st.markdown(f"##### 📐 Matrice di Riconciliazione Triangolare Inter-Fonte (Anno d'Imposta {selected_tax_year})")
            st.caption(
                "Audit incrociato multilivello per certificare la coerenza fiscale tra Ledger Argus, "
                "Rendiconto Ufficiale del Broker, Modello 730/Redditi e risultanze dei controlli automatizzati AdE."
            )

            # Badge fonti verificate
            src_labels = {
                "LEDGER_ARGUS": "📘 Ledger ARGUS",
                "BROKER_REPORT": "📙 Rendiconto Broker",
                "OFFICIAL_730": "📗 Modello 730",
                "ADE_NOTICE_36BIS": "📕 Avviso AdE 36-bis",
                "CU": "📓 Certificazione Unica",
            }
            src_badges = [src_labels.get(s, s) for s in tri_audit.get("sources_found", [])]
            st.markdown(f"**Fonti analizzate per l'anno {selected_tax_year}:** " + " • ".join(f"`{b}`" for b in src_badges))

            # Se rilevata contestazione AdE 36-bis, mostra card rossa e CIVIS Defense Assistant
            if tri_audit.get("has_ade_notice"):
                st.error(
                    f"### 🚨 CONTESTAZIONE FISCALE ADE RILEVATA EX ART. 36-BIS\n\n"
                    f"**Somma Complessiva Richiesta dall'Agenzia delle Entrate:** **{fmt_eur_it(tri_audit['ade_total_disputed'])}**\n\n"
                    f"**Diagnosi della Causa Radice (Root Cause):** L'Agenzia delle Entrate ha ricalcolato l'imposta applicando il 26% sull'intero importo delle plusvalenze lorde, "
                    f"omettendo o disconoscendo la compensazione delle minusvalenze certificate nel Rendiconto del broker.\n\n"
                    f"Tale liquidazione automatica viola il principio di tassazione al netto ex **art. 68, comma 5 del D.P.R. 917/1986 (TUIR)**. "
                    f"È possibile richiedere lo sgravio totale in autotutela tramite il canale telematico **CIVIS** senza versare la somma richiesta."
                )

                if tri_audit.get("civis_defense_draft"):
                    with st.expander("📝 Generatore di Memoria Difensiva per Canale CIVIS (Istanza di Autotutela)", expanded=True):
                        st.caption(
                            "Istanza formale di autotutela redatta automaticamente da ARGUS con riferimenti precisi all'atto, al protocollo e alla normativa TUIR. "
                            "Copia e incolla direttamente nella schermata CIVIS dell'Agenzia delle Entrate oppure scarica il file di testo."
                        )
                        civis_txt = tri_audit["civis_defense_draft"]
                        st.text_area(
                            "Testo Istanza di Autotutela CIVIS:",
                            value=civis_txt,
                            height=260,
                            key=f"civis_txt_box_{pid_str}_{selected_tax_year}",
                        )
                        c_civis_dl, _ = st.columns([1.5, 3])
                        with c_civis_dl:
                            st.download_button(
                                "📥 Scarica Istanza di Autotutela (.txt)",
                                data=civis_txt,
                                file_name=f"istanza_autotutela_civis_36bis_{selected_tax_year}.txt",
                                mime="text/plain",
                                key=f"dl_civis_file_{pid_str}_{selected_tax_year}",
                                use_container_width=True,
                            )

            df_tri = pd.DataFrame(tri_audit["metrics_table"])
            for c in ["argus", "broker", "decl_730", "ade_36bis", "delta"]:
                if c in df_tri.columns:
                    df_tri[c + "_fmt"] = df_tri[c].apply(lambda v: fmt_eur_it(float(v)) if float(v) > 0 or v == 0.0 else "—")

            def _map_badge(s):
                if s == "OK":
                    return "🟢 Conforme"
                elif s == "WARNING":
                    return "🟡 Attenzione"
                else:
                    return "🔴 Disallineato"

            df_tri["status_badge"] = df_tri["status"].apply(_map_badge)

            st.dataframe(
                df_tri[["item", "argus_fmt", "broker_fmt", "decl_730_fmt", "ade_36bis_fmt", "delta_fmt", "status_badge", "notes"]],
                column_config={
                    "item": st.column_config.TextColumn("Parametro Fiscale", width="medium"),
                    "argus_fmt": st.column_config.TextColumn("1. Ledger ARGUS", width="small"),
                    "broker_fmt": st.column_config.TextColumn("2. Broker (Degiro)", width="small"),
                    "decl_730_fmt": st.column_config.TextColumn("3. Modello 730", width="small"),
                    "ade_36bis_fmt": st.column_config.TextColumn("4. AdE (36-bis)", width="small"),
                    "delta_fmt": st.column_config.TextColumn("Delta Rilevato", width="small"),
                    "status_badge": st.column_config.TextColumn("Stato Audit", width="small"),
                    "notes": st.column_config.TextColumn("Diagnosi & Riferimenti Normativi", width="large"),
                },
                hide_index=True,
                use_container_width=True,
            )
            st.markdown("---")

        # ── ADVISOR ALERT BOXES INTELLIGENTI ──
        if report.alerts:
            for alert in report.alerts:
                a_type = alert.get("type", "info")
                a_title = alert.get("title", "")
                a_msg = alert.get("message", "")

                if a_type == "danger":
                    st.error(f"### {a_title}\n\n{a_msg}")
                elif a_type == "warning":
                    st.warning(f"### {a_title}\n\n{a_msg}")
                elif a_type == "optimization":
                    st.info(f"### {a_title}\n\n{a_msg}")
                else:
                    st.info(f"### {a_title}\n\n{a_msg}")
        else:
            st.success("✅ **Nessuna anomalia riscontrata**: Tutti i dati dichiarati collimano perfettamente con le risultanze dei broker e non vi sono minusvalenze a rischio.")

        # ── SEZIONE DETTAGLIATA RISCHIO ART. 36-BIS ──
        if report.total_unfiled_losses > 0.0:
            st.markdown("---")
            st.markdown("##### 🔍 Dettaglio Sanzionatorio: Controllo Automatico Art. 36-bis d.P.R. 600/1973")
            assess = report.art_36_bis_risk_assessment
            st.markdown(
                f"""
                <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); border-left: 4px solid #ef4444; border-radius: 10px; padding: 16px 20px;">
                    <div style="font-weight: 700; color: #f87171; font-size: 15px; margin-bottom: 8px;">
                        ⚠️ Analisi di Rischio Fiscale: Minusvalenze Esterne Non Registrate
                    </div>
                    <p style="color: #cbd5e1; font-size: 13px; line-height: 1.6; margin: 0 0 12px 0;">
                        L'articolo 36-bis, comma 2, lett. c) del d.P.R. 600/1973 autorizza l'Agenzia delle Entrate ad eseguire
                        <b>liquidazioni automatiche</b> a mezzo telematico. Se un contribuente porta in compensazione minusvalenze
                        che non sono state certificate nei quadri RT degli anni precedenti, il sistema emette un
                        <b>avviso bonario di irregolarità</b> con disconoscimento integrale della detrazione.
                    </p>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                            <td style="padding: 6px 0; color: #94a3b8;">Minusvalenze non registrate in Anagrafe Tributaria:</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 700; color: #ffffff;">{fmt_eur_it(assess['unfiled_loss_amount'])}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                            <td style="padding: 6px 0; color: #94a3b8;">Recupero Imposta Sostitutiva (26%):</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 700; color: #f87171;">{fmt_eur_it(assess['tax_recovery_base_26pct'])}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                            <td style="padding: 6px 0; color: #94a3b8;">Sanzione Amministrativa (30% ex art. 13 D.Lgs. 471/1997):</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 700; color: #f87171;">{fmt_eur_it(assess['sanzione_amministrativa_30pct'])}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.06);">
                            <td style="padding: 6px 0; color: #94a3b8;">Interessi Legali di Mora (stima 5% annuo):</td>
                            <td style="padding: 6px 0; text-align: right; font-weight: 700; color: #f87171;">{fmt_eur_it(assess['interessi_mora_stimati'])}</td>
                        </tr>
                        <tr style="font-weight: 800; font-size: 14px;">
                            <td style="padding: 10px 0; color: #ffffff;">Totale Richiesta AdE Stimata:</td>
                            <td style="padding: 10px 0; text-align: right; color: #ef4444; font-size: 16px;">{fmt_eur_it(assess['total_potential_liability'])}</td>
                        </tr>
                    </table>
                    <div style="margin-top: 12px; font-size: 12.5px; color: #38bdf8;">
                        💡 <b>Advisor Action:</b> Effettuare una <i>dichiarazione integrativa a favore</i> per l'anno di maturazione della perdita
                        oppure ricorrere al <i>ravvedimento operoso</i> (art. 13 D.Lgs. 472/1997) per abbattere le sanzioni fino a 1/8.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── OPPORTUNITÀ TAX-LOSS HARVESTING ──
        if report.harvesting_opportunities:
            st.markdown("---")
            st.markdown("##### 🌾 Piano Operativo di Tax-Loss Harvesting")
            df_opp = pd.DataFrame(report.harvesting_opportunities)
            render_table_with_export(
                df=df_opp,
                table_title="Opportunità di Risparmio Fiscale entro il 31/12",
                file_prefix=f"argus_tax_loss_harvesting_{pid_str}_{selected_tax_year}",
                key_suffix=f"tlh_audit_{pid_str}_{selected_tax_year}",
                column_config={
                    "strategy": st.column_config.TextColumn("Strategia"),
                    "available_losses": st.column_config.NumberColumn("Zainetto Disponibile", format="€ %,.2f"),
                    "current_capital_gains": st.column_config.NumberColumn("Plusvalenze da Abbattere", format="€ %,.2f"),
                    "offset_potential": st.column_config.NumberColumn("Quota Compensabile", format="€ %,.2f"),
                    "tax_savings_eur": st.column_config.NumberColumn("Risparmio Netto (26%)", format="€ %,.2f"),
                    "action_deadline": st.column_config.TextColumn("Termine Operativo"),
                },
                hide_index=True,
            )

        # ── RICONCILIAZIONE DIRETTA DA FILE ESTRATTO CONTO BROKER ──
        st.markdown("---")
        st.markdown("##### 📂 Riconciliazione Real-Time da File Broker (DeGiro, Directa, IBKR, Fineco, ecc.)")
        st.caption(
            "Carica l'estratto conto o le transazioni scaricate dal broker per verificare immediatamente la coerenza "
            f"con i valori dichiarati nel Quadro T/RT del Modello 730/Redditi per l'Anno d'Imposta {selected_tax_year}."
        )

        broker_file = st.file_uploader(
            f"Trascina il CSV transazioni del broker per l'anno {selected_tax_year}:",
            type=["csv", "xlsx", "txt"],
            key=f"broker_tx_uploader_{pid_str}_{selected_tax_year}",
            help="Supporta automaticamente DeGiro, Directa SIM, Interactive Brokers, Fineco, Scalable, Trade Republic, eToro, Revolut.",
        )

        if broker_file is not None:
            try:
                # Lettura file
                if broker_file.name.endswith(".xlsx") or broker_file.name.endswith(".xls"):
                    df_raw_broker = pd.read_excel(broker_file)
                else:
                    content_raw = broker_file.read()
                    try:
                        df_raw_broker = pd.read_csv(io.BytesIO(content_raw), sep=None, engine="python")
                    except Exception:
                        df_raw_broker = pd.read_csv(io.BytesIO(content_raw), sep=";")

                with st.spinner("Rilevamento formato intermediario ed estrazione lotti FIFO..."):
                    df_parsed_b, b_key, b_rep = parse_broker_csv(df_raw_broker, broker_key="auto")
                    broker_fiscal = compute_broker_annual_capital_gains(df_parsed_b, tax_year=selected_tax_year)

                b_icon = b_rep.get("broker_icon", "📄")
                b_name = b_rep.get("broker_name", b_key.title())

                st.success(f"Intermediario rilevato: **{b_icon} {b_name}** • {b_rep.get('rows_parsed', 0)} movimenti elaborati.")

                b_cg = broker_fiscal["gross_capital_gains"]
                b_cl = broker_fiscal["gross_capital_losses"]
                b_net = broker_fiscal["net_gain"]
                b_tax = broker_fiscal["substitute_tax_estimate"]
                dec_cg = report.declared_capital_gains
                diff_cg = b_cg - dec_cg

                c_brk1, c_brk2, c_brk3, c_brk4 = st.columns(4)
                with c_brk1:
                    metric_card("Plusvalenze Broker", fmt_eur(b_cg), delta=f"{broker_fiscal['trades_count']} trade chiusi")
                with c_brk2:
                    metric_card("Minusvalenze Broker", fmt_eur(b_cl), delta="Zainetto potenziale")
                with c_brk3:
                    metric_card("Plusvalenze Dichiarate 730", fmt_eur(dec_cg), delta=f"Anno {selected_tax_year}")
                with c_brk4:
                    metric_card("Delta (Broker - 730)", fmt_eur(diff_cg), delta="Anomalia" if abs(diff_cg) > 20 else "Allineato", delta_color="inverse" if abs(diff_cg) > 20 else "normal")

                if abs(diff_cg) > 20.0:
                    st.warning(
                        f"⚠️ **Discrepanza Rilevata ({fmt_eur_it(diff_cg)})**: Le plusvalenze calcolate dai trade del broker {b_name} "
                        f"differiscono da quanto dichiarato nel Quadro RT/T11 ({fmt_eur_it(dec_cg)}). "
                        "Verifica se sono state effettuate compensazioni interne dal broker (se in regime amministrato) "
                        "o se è necessaria una dichiarazione integrativa."
                    )
                else:
                    st.success(f"✅ **Dati Allineati**: Le risultanze del broker {b_name} combaciano con la dichiarazione archiviata!")

                if broker_fiscal.get("ticker_breakdown"):
                    with st.expander("📋 Dettaglio Plus/Minusvalenze Realizzate per Singolo Strumento", expanded=False):
                        df_tk_brk = pd.DataFrame(broker_fiscal["ticker_breakdown"])
                        st.dataframe(
                            df_tk_brk,
                            column_config={
                                "ticker": st.column_config.TextColumn("Ticker / Titolo"),
                                "asset_class": st.column_config.TextColumn("Classe Attivo"),
                                "trades": st.column_config.NumberColumn("Trade Chiusi"),
                                "realized_pnl_eur": st.column_config.NumberColumn("PnL Realizzato Netto (€)", format="€ %,.2f"),
                            },
                            hide_index=True,
                            use_container_width=True,
                        )

            except Exception as e:
                st.error(f"Errore durante l'elaborazione del file broker: {e}")

        # ── SIMULATORE F24 & RAVVEDIMENTO OPEROSO (ART. 13 D.LGS. 472/1997) ──
        st.markdown("---")
        st.markdown("##### ⚖️ Simulatore F24 & Ravvedimento Operoso (Art. 13 D.Lgs. 472/1997)")
        st.caption(
            "In caso di omesso o parziale versamento delle imposte sostitutive (Quadro RT / Rigo 321) o di IVAFE, "
            "è possibile sanare la violazione spontaneamente prima della ricezione della cartella o dell'avviso ex art. 36-bis, "
            "beneficiando di una riduzione drastica delle sanzioni (fino a 1/10 o 1/8 del minimo)."
        )

        with st.expander("🛠️ Calcola Ravvedimento Operoso e Genera Prospetto F24", expanded=False):
            col_rav1, col_rav2, col_rav3 = st.columns(3)
            with col_rav1:
                default_unpaid = float(report.art_36_bis_risk_assessment.get("tax_recovery_base_26pct", 0.0) or abs(report.delta_substitute_tax) or 500.0)
                sim_tax_amt = st.number_input(
                    "Imposta da Regolarizzare (€):",
                    min_value=1.0,
                    value=max(10.0, default_unpaid),
                    step=50.0,
                    key=f"rav_tax_amt_{pid_str}_{selected_tax_year}",
                )
            with col_rav2:
                sim_days = st.slider(
                    "Giorni di Ritardo nel Versamento:",
                    min_value=1,
                    max_value=730,
                    value=45,
                    step=1,
                    key=f"rav_days_{pid_str}_{selected_tax_year}",
                    help="Numero di giorni trascorsi dalla scadenza originaria di versamento (es. 30 giugno).",
                )
            with col_rav3:
                sim_tributo_type = st.selectbox(
                    "Tributo da Versare:",
                    ["CAPITAL_GAIN", "IVAFE"],
                    format_func=lambda x: "Cod. 1100 (Sostitutiva Capital Gain 26%)" if x == "CAPITAL_GAIN" else "Cod. 4043 (IVAFE Estero Saldo)",
                    key=f"rav_trib_sel_{pid_str}_{selected_tax_year}",
                )

            rav_res = compute_ravvedimento_operoso(
                unpaid_tax_amount=sim_tax_amt,
                days_delayed=sim_days,
                annual_legal_interest_rate=0.025,
                tax_type=sim_tributo_type,
            )

            c_r_res1, c_r_res2, c_r_res3 = st.columns(3)
            with c_r_res1:
                metric_card("Totale con Ravvedimento", fmt_eur(rav_res["total_ravvedimento"]), delta=f"Sanzione {rav_res['penalty_rate_pct']:.2f}%")
            with c_r_res2:
                metric_card("AdE Art. 36-bis Ordinario", fmt_eur(rav_res["ordinary_total_liability"]), delta="Sanzione 30% + Mora", delta_color="inverse")
            with c_r_res3:
                metric_card("Risparmio con Ravvedimento", fmt_eur(rav_res["net_savings_eur"]), delta="Denaro Risparmiato", delta_color="normal")

            st.info(f"📌 **Scaglione di Ravvedimento:** {rav_res['bracket_name']} • Riferimento normativo: *{rav_res['legal_reference']}*")

            # Tabella compilazione delega F24
            st.markdown("###### 📋 Prospetto di Compilazione Delega F24 (Sezione Erario)")
            df_f24 = pd.DataFrame(rav_res["f24_rows"])
            df_f24["importo_debito_fmt"] = df_f24["importo_debito"].apply(lambda v: fmt_eur_it(float(v)))

            st.dataframe(
                df_f24[["sezione", "codice_tributo", "anno_riferimento", "importo_debito_fmt", "descrizione"]],
                column_config={
                    "sezione": st.column_config.TextColumn("Sezione"),
                    "codice_tributo": st.column_config.TextColumn("Codice Tributo"),
                    "anno_riferimento": st.column_config.NumberColumn("Anno Rif."),
                    "importo_debito_fmt": st.column_config.TextColumn("Importo a Debito (€)"),
                    "descrizione": st.column_config.TextColumn("Causale F24"),
                },
                hide_index=True,
                use_container_width=True,
            )

