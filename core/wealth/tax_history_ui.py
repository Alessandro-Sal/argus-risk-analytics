# ============================================================
# core/wealth/tax_history_ui.py
# ARGUS — UI Component: Archivio Storico Fiscale & Riconciliazione (730 / Redditi PF)
# Sezione 1: Gestione & Inserimento (Upload PDF / Form manuale / Data Editor)
# Sezione 2: Dashboard Storica & Zainetto Fiscale (Timeline 5Y & Semafori AdE)
# Sezione 3: Audit & Punti di Miglioria (Advisor Alerts & Art. 36-bis Risk)
# ============================================================

import io
import json
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
    compute_crypto_tax_reporting,
    compute_fire_effective_tax_drag,
    compute_fiscal_reform_2026_etf_harmonization,
    compute_fiscal_reform_multiyear_projection,
    compute_pension_tax_deduction_optimizer,
    compute_ravvedimento_operoso,
    compute_tax_loss_harvesting_signals,
    delete_declaration,
    delete_tax_loss,
    delete_verification_document,
    export_wealth_and_tax_backup_bundle,
    fmt_eur_it,
    generate_730_precompilata_actionable_guide,
    generate_commercialista_tax_dossier_html,
    generate_f24_payment_slip,
    generate_official_f24_facsimile_html,
    generate_sample_730_json,
    get_declarations,
    get_fiscal_deadlines_calendar,
    get_tax_losses,
    get_unified_tax_document_registry,
    get_verification_documents,
    import_wealth_and_tax_backup_bundle,
    parse_730_pdf_or_json,
    parse_building_renovation,
    parse_medical_expenses,
    parse_mortgage_interest,
    parse_universal_tax_document,
    reconcile_with_portfolio,
    record_declaration,
    record_tax_loss,
    record_verification_document,
    sync_tax_events_to_cashflow,
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

    # ── SCADENZIARIO FISCALE GLOBALE (AdE TAX CALENDAR & COUNTDOWN) ──
    deadlines_list = get_fiscal_deadlines_calendar(tax_year=selected_tax_year, profile_id=pid_str, engine=engine)
    with st.expander(f"📅 Scadenziario Tributario AdE & Conto alla Rovescia Adempimenti (Anno {selected_tax_year}/{selected_tax_year + 1})", expanded=False):
        st.caption("Scadenzario cronologico unificato con calcolo dinamico del conto alla rovescia, badge di urgenza, filtri interattivi e codici tributo F24.")

        c_dl_filter, c_dl_alert = st.columns([2.5, 1.5])
        with c_dl_filter:
            dl_filter = st.radio(
                "Filtro Scadenze:",
                ["Tutte le Scadenze", "🚨 In Scadenza (< 30 gg)", "⚠️ Scadute", "📅 Future"],
                horizontal=True,
                key=f"dl_filter_radio_{pid_str}_{selected_tax_year}",
            )
        with c_dl_alert:
            expired_count = sum(1 for d in deadlines_list if d["days_remaining"] < 0)
            urgent_count = sum(1 for d in deadlines_list if 0 <= d["days_remaining"] <= 30)
            if expired_count > 0:
                st.warning(f"⚠️ {expired_count} adempimenti scaduti: regolarizzabili con Ravvedimento Operoso!")
            elif urgent_count > 0:
                st.info(f"🚨 {urgent_count} scadenze nei prossimi 30 giorni!")
            else:
                st.success("🟢 Nessuna urgenza immediata nei prossimi 30 giorni.")

        if dl_filter == "🚨 In Scadenza (< 30 gg)":
            filtered_deadlines = [d for d in deadlines_list if 0 <= d["days_remaining"] <= 30]
        elif dl_filter == "⚠️ Scadute":
            filtered_deadlines = [d for d in deadlines_list if d["days_remaining"] < 0]
        elif dl_filter == "📅 Future":
            filtered_deadlines = [d for d in deadlines_list if d["days_remaining"] > 30]
        else:
            filtered_deadlines = deadlines_list

        c_dl_cols = st.columns(max(1, min(len(filtered_deadlines), 4)))
        for d_i, d_val in enumerate(filtered_deadlines[:4]):
            with c_dl_cols[d_i % len(c_dl_cols)]:
                diff_d = d_val["days_remaining"]
                d_delta = f"{abs(diff_d)} gg {'passati' if diff_d < 0 else 'rimasti'}"
                metric_card(
                    d_val["title"][:25] + "...",
                    d_val["due_date_formatted"],
                    delta=f"{d_val['urgency_badge']} ({d_delta})",
                    delta_color="normal" if diff_d > 15 else ("inverse" if diff_d >= 0 else "off"),
                )

        df_deadlines = pd.DataFrame(filtered_deadlines if filtered_deadlines else deadlines_list)
        st.dataframe(
            df_deadlines[["due_date_formatted", "urgency_badge", "title", "tributo_code", "amount_eur", "desc"]],
            column_config={
                "due_date_formatted": st.column_config.TextColumn("Data Limite", width="small"),
                "urgency_badge": st.column_config.TextColumn("Urgenza", width="small"),
                "title": st.column_config.TextColumn("Adempimento Tributario", width="medium"),
                "tributo_code": st.column_config.TextColumn("Codice Tributo / Canale", width="small"),
                "amount_eur": st.column_config.NumberColumn("Importo Stimato (€)", format="€ %,.2f"),
                "desc": st.column_config.TextColumn("Descrizione & Normativa AdE", width="large"),
            },
            hide_index=True,
            use_container_width=True,
        )

    # ── SUB-TABS DELLA SEZIONE ──────────────────────────────────
    subtab_man, subtab_reg, subtab_dash, subtab_audit = st.tabs([
        "📥 1. Gestione & Inserimento (Upload / Data Editor)",
        "📑 2. Registro Ufficiale Documenti Fiscali (Audit Trail DB)",
        "📊 3. Dashboard Storica & Zainetto Fiscale",
        "🚨 4. Audit Advisor & Riconciliazione Broker (Art. 36-bis)",
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
                    elif v_type in ["MEDICAL_EXPENSES", "SPESE_MEDICHE"]:
                        type_label = f"Spesa Sanitaria ({v_issuer})"
                        badge_color = "#ec4899"
                        detail_line = f"Spesa: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Detrazione 19%: <strong style='color: #10b981;'>+{fmt_eur_it(v_item.get('secondary_amount', 0.0))}</strong>"
                    elif v_type in ["MORTGAGE_INTEREST", "INTERESSI_MUTUO"]:
                        type_label = f"Interessi Mutuo ({v_issuer})"
                        badge_color = "#3b82f6"
                        detail_line = f"Interessi: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Detrazione 19%: <strong style='color: #10b981;'>+{fmt_eur_it(v_item.get('secondary_amount', 0.0))}</strong>"
                    elif v_type in ["BUILDING_RENOVATION", "RISTRUTTURAZIONE"]:
                        type_label = f"Ristrutturazione ({v_issuer})"
                        badge_color = "#14b8a6"
                        detail_line = f"Spesa: <strong style='color: #f8fafc;'>{fmt_eur_it(v_gross)}</strong><br/>Rata 1/10: <strong style='color: #10b981;'>+{fmt_eur_it(v_item.get('secondary_amount', 0.0))}</strong>"
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
            "- **Certificazioni Uniche (CU):** Estrae redditi da lavoro dipendente (Punti 1–6, ritenute P. 21, addizionali) ed eventuali compensi o borse esenti (Punto 465 cod. 23).\n"
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
                help="Supporta PDF ufficiali AdE, Precompilata, Modelli CU (Lavoro Dipendente / Borse Esenti), Rendiconti DEGIRO, Giacenza media N26, Bonifici affitto e Avvisi 36-bis.",
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
                        metric_card("Riferimento Atto", str(meta_r.get("contract_code") or "Atto Registrato"), "Contratto Registrato AdE")

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
                                f"(denominato ad esempio `Modello_730_Completo.pdf` o con protocollo telematico completo)."
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

        # ── SEZIONE BACKUP & RIPRISTINO 1-CLICK ──
        st.markdown("---")
        with st.expander("📦 Backup & Ripristino 1-Click (Export / Import JSON Bundle)", expanded=False):
            st.caption("Esporta l'intero patrimonio e l'archivio fiscale in un unico bundle JSON o ripristina un backup precedente con idempotenza.")
            c_bk_exp, c_bk_imp = st.columns(2)
            with c_bk_exp:
                st.markdown("###### 📤 Esportazione Dati")
                st.write("Genera uno snapshot istantaneo di tutte le tabelle patrimoniali e fiscali.")
                if st.button("📦 Prepara Snapshot di Backup", key=f"btn_prep_backup_{pid_str}"):
                    st.session_state[f"ready_backup_{pid_str}"] = True

                if st.session_state.get(f"ready_backup_{pid_str}"):
                    bundle = export_wealth_and_tax_backup_bundle(engine, profile_id=pid_str)
                    bundle_json = json.dumps(bundle, indent=2, ensure_ascii=False, default=str)
                    tot_rec = bundle.get("backup_metadata", {}).get("total_records_count", 0)
                    st.download_button(
                        "📥 Scarica Backup Completo (.json)",
                        data=bundle_json.encode("utf-8"),
                        file_name=f"argus_backup_wealth_tax_{pid_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key=f"dl_backup_json_{pid_str}",
                        use_container_width=True,
                    )
                    st.caption(f"✅ Snapshot pronto: {tot_rec} record estratti.")

            with c_bk_imp:
                st.markdown("###### 📥 Ripristino da File")
                up_backup = st.file_uploader("Carica file JSON di backup:", type=["json"], key=f"up_backup_json_{pid_str}")
                if up_backup is not None:
                    if st.button("🔄 Esegui Ripristino nel Database", key=f"btn_do_restore_{pid_str}", type="primary", use_container_width=True):
                        try:
                            bundle_data = json.loads(up_backup.read().decode("utf-8"))
                            res_imp = import_wealth_and_tax_backup_bundle(engine, backup_data=bundle_data, profile_id=pid_str)
                            restored_cnt = res_imp.get("total_restored_records", 0)
                            st.success(f"✅ Ripristino completato! {restored_cnt} record fiscali ripristinati con successo.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Errore durante il ripristino: {exc}")

    # ============================================================
    # SUBTAB 2: REGISTRO UFFICIALE DOCUMENTI FISCALI (AUDIT TRAIL DB)
    # ============================================================
    with subtab_reg:
        st.markdown("#### 📑 Registro Ufficiale Documenti Fiscali & Audit Trail a Database")
        st.caption(
            "Protocollo formale e cronologico di tutti i documenti probatori, dichiarazioni e atti "
            "archiviati nel database. Fornisce tracciabilità completa, riscontro degli importi e conservazione documentale."
        )

        reg_entries = get_unified_tax_document_registry(engine, profile_id=pid_str)

        if not reg_entries:
            st.info("Nessun documento fiscale attualmente registrato nel database. Carica o inserisci i file nella Scheda 1 per popolare il Registro.")
        else:
            # ── 1. KPI HIGHLIGHTS DEL REGISTRO ──
            tot_docs = len(reg_entries)
            n_decls = sum(1 for r in reg_entries if r["source_table"] == "tax_declarations")
            n_vdocs = sum(1 for r in reg_entries if r["source_table"] == "tax_verification_documents")
            years_covered = sorted(list({r["tax_year"] for r in reg_entries}))
            years_span = f"{years_covered[0]} – {years_covered[-1]}" if len(years_covered) > 1 else str(years_covered[0]) if years_covered else "N/D"
            tot_gross_tracked = sum(r["gross_amount"] for r in reg_entries)
            tot_taxes_tracked = sum(r["tax_amount"] for r in reg_entries)

            c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
            with c_kpi1:
                metric_card("Atti a Registro", f"{tot_docs} Documenti", f"{n_decls} Dichiarazioni • {n_vdocs} Riscontri")
            with c_kpi2:
                metric_card("Copertura Fiscale", years_span, f"{len(years_covered)} Anni d'Imposta Tracciati")
            with c_kpi3:
                metric_card("Totale Flussi / Lordo", fmt_eur_it(tot_gross_tracked), "Somma imponibili & movimenti registrati")
            with c_kpi4:
                metric_card("Imposte / Ritenute", fmt_eur_it(tot_taxes_tracked), "IRPEF netta, sostitutive & ritenute")

            st.markdown("---")

            # ── 2. FILTRI INTERATTIVI ──
            c_f_yr, c_f_cat, c_f_q = st.columns([1.5, 2.5, 2.5])
            with c_f_yr:
                filter_year_opts = ["Tutti gli Anni"] + [str(y) for y in sorted(years_covered, reverse=True)]
                sel_f_yr = st.selectbox("📅 Filtra per Anno:", filter_year_opts, key=f"reg_f_yr_{pid_str}")
            with c_f_cat:
                cat_unique = sorted(list({r["category_label"] for r in reg_entries}))
                filter_cat_opts = ["Tutte le Categorie"] + cat_unique
                sel_f_cat = st.selectbox("📂 Filtra per Categoria:", filter_cat_opts, key=f"reg_f_cat_{pid_str}")
            with c_f_q:
                search_q = st.text_input("🔍 Cerca per File, Protocollo o Emittente:", value="", placeholder="Es. Datore di Lavoro, DEGIRO, Locazione, 2025...", key=f"reg_search_{pid_str}")

            # Applicazione filtri
            filtered_entries = reg_entries
            if sel_f_yr != "Tutti gli Anni":
                filtered_entries = [r for r in filtered_entries if str(r["tax_year"]) == sel_f_yr]
            if sel_f_cat != "Tutte le Categorie":
                filtered_entries = [r for r in filtered_entries if r["category_label"] == sel_f_cat]
            if search_q.strip():
                sq_lower = search_q.strip().lower()
                filtered_entries = [
                    r for r in filtered_entries
                    if sq_lower in r.get("source_filename", "").lower()
                    or sq_lower in r.get("issuer_name", "").lower()
                    or sq_lower in r.get("protocol_or_code", "").lower()
                    or sq_lower in r.get("registry_id", "").lower()
                    or sq_lower in r.get("notes", "").lower()
                ]

            st.markdown(f"##### 📋 Tabella Ufficiale del Registro ({len(filtered_entries)} di {tot_docs} documenti)")

            # Costruzione DataFrame per la visualizzazione
            df_rows = []
            for r in filtered_entries:
                df_rows.append({
                    "Protocollo": r["registry_id"],
                    "Data Registrazione": r["created_at"],
                    "Anno Fiscale": r["tax_year"],
                    "Categoria Atto": r["category_label"],
                    "Emittente / Sostituto": r["issuer_name"],
                    "Rif. Telematico / Atto": r["protocol_or_code"],
                    "Lordo / Base (€)": r["gross_amount"],
                    "Imposta / Ritenuta (€)": r["tax_amount"],
                    "Rimborsi / Detrazioni (€)": r["secondary_amount"],
                    "File Sorgente": r["source_filename"],
                    "Stato Audit": r["status_badge"],
                })

            df_reg = pd.DataFrame(df_rows)
            st.dataframe(
                df_reg,
                column_config={
                    "Lordo / Base (€)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Imposta / Ritenuta (€)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Rimborsi / Detrazioni (€)": st.column_config.NumberColumn(format="€ %.2f"),
                    "Anno Fiscale": st.column_config.NumberColumn(format="%d"),
                },
                use_container_width=True,
                hide_index=True,
            )

            # ── 3. AZIONI & ESPORTAZIONE AUDIT TRAIL ──
            col_csv, col_exp_all, _ = st.columns([2, 2, 3])
            with col_csv:
                csv_bytes = df_reg.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Esporta Registro Completo (CSV)",
                    data=csv_bytes,
                    file_name=f"registro_fiscale_audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"dl_reg_csv_{pid_str}",
                    use_container_width=True,
                )
            with col_exp_all:
                if st.button("🔄 Ricarica Dati dal Database", key=f"btn_sync_reg_{pid_str}", use_container_width=True):
                    st.rerun()

            st.markdown("---")

            # ── 4. ISPEZIONE METADATI & DETTAGLIO ANALITICO ──
            with st.expander("🔍 Ispezione Analitica / Metadati Completi Documento", expanded=False):
                reg_options = [r["registry_id"] for r in filtered_entries]
                if reg_options:
                    sel_reg_id = st.selectbox(
                        "Seleziona documento da esaminare:",
                        options=reg_options,
                        format_func=lambda x: next(
                            (f"{x} — {r['category_label']} ({r['tax_year']}) | {r['issuer_name']} | File: {r['source_filename']}" for r in filtered_entries if r["registry_id"] == x),
                            x,
                        ),
                        key=f"sel_inspect_reg_{pid_str}",
                    )
                    inspected = next((r for r in filtered_entries if r["registry_id"] == sel_reg_id), None)
                    if inspected:
                        c_in1, c_in2, c_in3 = st.columns([2, 2, 2])
                        with c_in1:
                            st.write(f"**Tipologia:** {inspected['category_label']}")
                            st.write(f"**Anno Fiscale:** {inspected['tax_year']} (Filing {inspected['filing_year']})")
                            st.write(f"**Tabella DB:** `{inspected['source_table']}` (ID #{inspected['raw_id']})")
                        with c_in2:
                            st.write(f"**Emittente:** {inspected['issuer_name']}")
                            st.write(f"**Protocollo / Atto:** `{inspected['protocol_or_code']}`")
                            st.write(f"**Data Ingestione:** {inspected['created_at']}")
                        with c_in3:
                            st.write(f"**Importo Base:** {fmt_eur_it(inspected['gross_amount'])}")
                            st.write(f"**Imposta/Ritenuta:** {fmt_eur_it(inspected['tax_amount'])}")
                            st.write(f"**Rimborsi/Detrazioni:** {fmt_eur_it(inspected['secondary_amount'])}")

                        if inspected.get("notes"):
                            st.info(f"📝 **Note di elaborazione:** {inspected['notes']}")

                        st.markdown("**🔬 Metadati Strutturati (JSON esteso):**")
                        st.json(inspected.get("metadata_json") or {})

                        # Opzione di cancellazione rapida da registro
                        with st.popover("⚠️ Elimina questo Documento dal Database"):
                            st.write(f"Sei sicuro di voler eliminare **{inspected['registry_id']}** ({inspected['source_filename']}) dal database?")
                            if st.button("Conferma Eliminazione", key=f"btn_confirm_del_reg_{inspected['registry_id']}", type="primary"):
                                if inspected["source_table"] == "tax_declarations":
                                    delete_declaration(engine, inspected["raw_id"])
                                else:
                                    delete_verification_document(engine, inspected["raw_id"])
                                st.warning(f"Documento {inspected['registry_id']} eliminato.")
                                st.rerun()

    # ============================================================
    # SUBTAB 3: DASHBOARD STORICA & ZAINETTO FISCALE
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

        # ── 3. SEZIONE STRATEGICA TAX-LOSS HARVESTING ──
        st.markdown("---")
        st.markdown("##### 🌾 Opportunità e Segnali di Tax-Loss Harvesting")
        st.caption(
            "Identifica le minusvalenze in scadenza entro i prossimi 1-2 anni e consiglia prese di profitto tattiche "
            "su posizioni in utile per azzerare l'imposta sostitutiva 26% e rigenerare il prezzo medio di carico (PMC)."
        )

        tlh_data = compute_tax_loss_harvesting_signals(engine, portfolio_id=1, profile_id=pid_str, current_year=selected_tax_year)
        c_tlh1, c_tlh2, c_tlh3, c_tlh4 = st.columns(4)
        with c_tlh1:
            metric_card("Zainetto Attivo Residuo", fmt_eur(tlh_data["total_active_losses"]), f"In scadenza a breve: {fmt_eur(tlh_data['urgent_expiring_losses'])}")
        with c_tlh2:
            metric_card("Plusvalenze Idonee", fmt_eur(tlh_data["eligible_unrealized_gains"]), "Azioni / Redditi Diversi")
        with c_tlh3:
            comp_pot = min(tlh_data["total_active_losses"], tlh_data["eligible_unrealized_gains"])
            metric_card("Quota Compensabile Subito", fmt_eur(comp_pot), "Offset a imposta 0,00 €")
        with c_tlh4:
            metric_card("Risparmio Fiscale 26%", f"+{fmt_eur(tlh_data['potential_tax_savings_26pct'])}", "Imposte azzerabili", delta_color="normal")

        recs = tlh_data.get("harvesting_recommendations", [])
        if recs:
            st.markdown("###### 📋 Azioni Operative Consigliate")
            for sig in recs:
                st.markdown(
                    f"""
                    <div style="background: rgba(22, 27, 34, 0.8); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #10b981; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 700; color: #ffffff; font-size: 14px;">🎯 Ticker: {sig['ticker']}</span>
                                <span style="margin-left: 10px; font-size: 12px; color: #94a3b8;">Quote da cedere: <b>{sig['quote_da_vendere']}</b> • Plusvalenza: <b>{fmt_eur_it(sig['plusvalenza_realizzabile'])}</b></span>
                            </div>
                            <span style="font-size: 11px; font-weight: 700; color: #10b981; background: rgba(16, 185, 129, 0.1); padding: 3px 8px; border-radius: 4px;">Risparmio 26%: +{fmt_eur_it(sig['risparmio_fiscale_26pct'])}</span>
                        </div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-top: 6px;">
                            💡 <b>Strategia:</b> {sig['strategia']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Nessuna minusvalenza in scadenza immediata o posizioni in utile da compensare per questo profilo.")

        # ── 3. SIMULATORE RIFORMA FISCALE 2026 (ARMONIZZAZIONE ETF & TUIR) ──
        st.markdown("---")
        st.markdown("##### 🏛️ Simulatore Riforma Fiscale 2026: Armonizzazione ETF & TUIR (Categoria Unica)")
        st.caption(
            "La Delega Fiscale 2026 unifica i 'Redditi di Capitale' e i 'Redditi Diversi' in un'unica categoria di Redditi Finanziari. "
            "Le plusvalenze da ETF potranno finalmente compensare direttamente le minusvalenze pregresse nello zainetto fiscale "
            "senza dover forzare vendite su azioni o ricorrere a complessi certificates a maxi-cedola."
        )

        c_ref_in1, c_ref_in2 = st.columns([2, 2])
        with c_ref_in1:
            sim_etf_g = st.number_input(
                "Plusvalenza ETF Simulata da Realizzare (€):",
                min_value=0.0,
                value=3500.0,
                step=500.0,
                key=f"reform_sim_etf_in_{pid_str}_{selected_tax_year}",
            )
        with c_ref_in2:
            st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
            use_real_pos = st.checkbox("Analizza posizioni reali in portafoglio (se presenti)", value=True, key=f"reform_use_pos_{pid_str}")

        reform_sim = compute_fiscal_reform_2026_etf_harmonization(
            engine,
            profile_id=pid_str,
            tax_year=selected_tax_year,
            simulated_etf_gain=None if use_real_pos else sim_etf_g,
        )

        c_rf1, c_rf2, c_rf3, c_rf4 = st.columns(4)
        with c_rf1:
            metric_card("Plusvalenze ETF", fmt_eur(reform_sim["etf_unrealized_gains"]), "Base di Calcolo")
        with c_rf2:
            metric_card("Zainetto Fiscale", fmt_eur(reform_sim["total_active_losses"]), "Minusvalenze Attive")
        with c_rf3:
            metric_card(
                "Tax Alpha da Riforma",
                f"+{fmt_eur(reform_sim['immediate_tax_alpha_eur'])}",
                delta=f"Risparmio {reform_sim['delta_tax_pct_points']:.1f}% secco",
                delta_color="normal",
            )
        with c_rf4:
            metric_card(
                "Assorbimento Zainetto",
                f"{reform_sim['reform_2026_regime']['loss_absorption_pct']:.1f}%",
                "Compensato con ETF",
                delta_color="normal",
            )

        # Tabella di confronto regimi
        df_comp_reform = pd.DataFrame([
            {
                "Regime Fiscale": "1. Regime Attuale (TUIR Vigente)",
                "Classificazione ETF": "Reddito di Capitale (Art. 44)",
                "Compensazione Minusvalenze": "NON AMMESSA (0,00 €)",
                "Imposta ETF Dovuta": f"€ {reform_sim['current_system']['etf_tax_due_eur']:,.2f} (26% secco)",
                "Zainetto Perso / Inutilizzato": f"€ {reform_sim['current_regime']['remaining_unshielded_losses']:,.2f}",
            },
            {
                "Regime Fiscale": "2. Riforma 2026 (Armonizzazione)",
                "Classificazione ETF": "Reddito Finanziario Unificato",
                "Compensazione Minusvalenze": f"COMPENSABILE: € {reform_sim['reform_2026_system']['losses_offset_eur']:,.2f}",
                "Imposta ETF Dovuta": f"€ {reform_sim['reform_2026_system']['etf_tax_due_eur']:,.2f} (Netto Compensato)",
                "Zainetto Perso / Inutilizzato": f"€ {reform_sim['reform_2026_regime']['remaining_unshielded_losses']:,.2f}",
            },
        ])
        st.dataframe(df_comp_reform, hide_index=True, use_container_width=True)
        st.info(f"💡 **Verdetto Strategico ARGUS:** {reform_sim['strategic_advice']}")

        # ── 4. PROIEZIONE PLURIENNALE A LUNGO TERMINE (STATUS QUO vs RIFORMA 2026) ──
        with st.expander("📈 Proiezione Pluriennale di Lungo Termine (5 - 20 Anni): Status Quo vs Riforma 2026", expanded=False):
            st.caption(
                "Simulazione quantitativa dell'effetto composto del 'Tax Drag' a lungo termine: "
                "confronta l'accumulo di capitale con l'attuale asimmetria fiscale rispetto alla riforma ad aliquota armonizzata con riporto integrale."
            )
            c_p_in1, c_p_in2, c_p_in3, c_p_in4 = st.columns(4)
            with c_p_in1:
                p_cap = st.number_input("Capitale Iniziale (€):", min_value=5000.0, value=100000.0, step=10000.0, key=f"sim_p_cap_{pid_str}")
            with c_p_in2:
                p_ret = st.slider("Rendimento Annuo Lordo (%):", min_value=2.0, max_value=15.0, value=7.0, step=0.5, key=f"sim_p_ret_{pid_str}")
            with c_p_in3:
                p_trn = st.slider("Turnover Ribilanciamento (%):", min_value=0.0, max_value=50.0, value=15.0, step=5.0, key=f"sim_p_trn_{pid_str}")
            with c_p_in4:
                p_los = st.slider("Frazione Minus Realizzate (%):", min_value=0.0, max_value=80.0, value=30.0, step=5.0, key=f"sim_p_los_{pid_str}")

            proj_res = compute_fiscal_reform_multiyear_projection(
                initial_capital=p_cap,
                annual_return_pct=p_ret,
                annual_turnover_pct=p_trn,
                realized_loss_fraction=p_los / 100.0,
                projection_years=20,
            )

            c_pj1, c_pj2, c_pj3, c_pj4 = st.columns(4)
            with c_pj1:
                metric_card("Delta Capitale a 10 Anni", f"+{fmt_eur(proj_res['milestones'].get('10y', {}).get('delta_wealth', 0.0))}", "Guadagno da Riforma", delta_color="normal")
            with c_pj2:
                metric_card("Delta Capitale a 20 Anni", f"+{fmt_eur(proj_res['total_wealth_alpha_eur'])}", f"CAGR +{proj_res['tax_alpha_basis_points']} bps", delta_color="normal")
            with c_pj3:
                metric_card("Imposte Risparmiate (20A)", fmt_eur(proj_res['total_tax_savings_eur']), "Cash Flow Preservato", delta_color="normal")
            with c_pj4:
                metric_card("Tax Alpha Annuo", f"+{proj_res['tax_alpha_basis_points']} bps", "Rendimento Netto Extra", delta_color="normal")

            # Grafico Plotly dual curve
            df_traj = pd.DataFrame(proj_res["trajectory"])
            fig_proj = go.Figure()
            fig_proj.add_trace(go.Scatter(
                x=[f"Anno {y}" for y in df_traj["year"]],
                y=df_traj["capital_reform"],
                name="Riforma 2026 (Armonizzata)",
                line=dict(color="#10b981", width=3),
                fill=None,
            ))
            fig_proj.add_trace(go.Scatter(
                x=[f"Anno {y}" for y in df_traj["year"]],
                y=df_traj["capital_status_quo"],
                name="Status Quo (TUIR Vigente)",
                line=dict(color="#f59e0b", width=2.5, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(16, 185, 129, 0.12)",
            ))
            fig_proj.update_layout(
                title=dict(text="Crescita Patrimoniale Composta: Riforma 2026 vs Status Quo (20 Anni)", font=dict(size=14, color="#ffffff")),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=380,
                yaxis=dict(title="Patrimonio Netto (€)", gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_proj, use_container_width=True, config={"displayModeBar": False})

            # Tabella milestone
            st.markdown("###### 📋 Proiezione per Scaglioni Temporali")
            df_ms = pd.DataFrame([
                {"Orizzonte": "5 Anni", **proj_res["milestones"].get("5y", {})},
                {"Orizzonte": "10 Anni", **proj_res["milestones"].get("10y", {})},
                {"Orizzonte": "15 Anni", **proj_res["milestones"].get("15y", {})},
                {"Orizzonte": "20 Anni", **proj_res["milestones"].get("20y", {})},
            ])
            st.dataframe(
                df_ms,
                column_config={
                    "capital_status_quo": st.column_config.NumberColumn("Capitale Status Quo (€)", format="€ %,.2f"),
                    "capital_reform": st.column_config.NumberColumn("Capitale Riforma 2026 (€)", format="€ %,.2f"),
                    "delta_wealth": st.column_config.NumberColumn("Extra-Capitale Riforma (€)", format="+€ %,.2f"),
                    "cumulative_tax_saved": st.column_config.NumberColumn("Imposte Risparmiate (€)", format="€ %,.2f"),
                },
                hide_index=True,
                use_container_width=True,
            )

    # ============================================================
    # SUBTAB 4: AUDIT ADVISOR & RICONCILIAZIONE (ART. 36-BIS)
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
                "(Modelli CU Lavoro / Borse Esenti, Rendiconti DEGIRO RT/W, Conti Esteri N26, Ricevute Bonifici e Contratto di Locazione)."
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

            # ── 1. GENERATORE MODELLO F24 & ISTRUZIONI HOME BANKING ──
            st.markdown("---")
            st.markdown("##### 🏛️ Generatore Modello F24 & Home Banking con Piano Rateale")
            st.caption("Genera la delega di pagamento F24 esatta per le imposte finanziarie estere (DEGIRO Quadro RT e Quadro W) con simulazione di rateizzazione da 1 a 6 rate mensili.")

            c_f24_p1, c_f24_p2 = st.columns([2, 2])
            with c_f24_p1:
                n_inst = st.slider("Numero di Rate di Versamento (F24):", min_value=1, max_value=6, value=1, step=1, key=f"f24_inst_pick_{pid_str}_{selected_tax_year}")
            with c_f24_p2:
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
                apply_ext = st.checkbox("Applica maggiorazione dello 0,40% (Scadenza differita al 30 Luglio)", value=False, key=f"f24_ext_cb_{pid_str}_{selected_tax_year}")

            f24_data = generate_f24_payment_slip(engine, profile_id=pid_str, tax_year=selected_tax_year, installments=n_inst)

            c_f_k1, c_f_k2, c_f_k3, c_f_k4 = st.columns(4)
            with c_f_k1:
                base_f24 = float(f24_data.get("total_debt_eur", 0.0))
                tot_f24 = base_f24 * (1.004 if apply_ext else 1.0)
                metric_card("Totale a Debito F24", fmt_eur(tot_f24), f"{len(f24_data.get('payment_rows', []))} Tributi Erariali")
            with c_f_k2:
                deadlines = f24_data.get("deadlines", {})
                scad_label = deadlines.get("differita_con_maggiorazione", {}).get("data", "30/07") if apply_ext else deadlines.get("ordinaria", {}).get("data", "30/06")
                metric_card("Scadenza Prima Rata", scad_label, "+0,40% Applicato" if apply_ext else "Termine Ordinario")
            with c_f_k3:
                plans = f24_data.get("installment_plans", {}).get(n_inst, {})
                dett_rate = plans.get("dettaglio_rate", [])
                first_r_amt = (dett_rate[0].get("importo_totale_rata", tot_f24) * (1.004 if apply_ext else 1.0)) if dett_rate else tot_f24
                metric_card("Importo Singola Rata", fmt_eur(first_r_amt), f"Piano {n_inst} Rate")
            with c_f_k4:
                metric_card("Anno di Imposta", f"{selected_tax_year}", f"Presentazione {selected_tax_year + 1}")

            # Quick copy table for home banking
            st.markdown("###### 📋 Dati per la Compilazione Home Banking (Copia e Incolla Rapido)")
            df_hb = pd.DataFrame(f24_data.get("home_banking_quick_copy", []))
            st.dataframe(
                df_hb,
                column_config={
                    "campo": st.column_config.TextColumn("Campo F24 / Home Banking", width="medium"),
                    "valore": st.column_config.TextColumn("Valore da Inserire", width="medium"),
                    "anno": st.column_config.NumberColumn("Anno Rif.", width="small"),
                    "importo": st.column_config.TextColumn("Importo a Debito (€)", width="small"),
                    "nota": st.column_config.TextColumn("Dettagli / Significato", width="large"),
                },
                hide_index=True,
                use_container_width=True,
            )

            # Fac-simile Grafico Ufficiale F24 (AdE Print-Ready)
            f24_facsimile = generate_official_f24_facsimile_html(
                f24_data,
                taxpayer_name=st.session_state.get(f"dossier_name_{pid_str}_{selected_tax_year}", "Mario Rossi"),
                taxpayer_cf=st.session_state.get(f"dossier_cf_{pid_str}_{selected_tax_year}", "RSSMRA85M01H501Z"),
            )

            c_f24_dl, c_f24_prev = st.columns([2, 2])
            with c_f24_dl:
                st.download_button(
                    "📥 Scarica Modello F24 Ufficiale (.html / PDF-Ready)",
                    data=f24_facsimile,
                    file_name=f"modello_f24_{selected_tax_year}_delega_erario.html",
                    mime="text/html",
                    key=f"dl_f24_facsimile_{pid_str}_{selected_tax_year}",
                    type="primary",
                    use_container_width=True,
                )
            with c_f24_prev:
                show_f24_p = st.checkbox(
                    "👁️ Mostra Fac-Simile F24 a Video",
                    value=False,
                    key=f"cb_show_f24_{pid_str}_{selected_tax_year}",
                )

            if show_f24_p:
                import streamlit.components.v1 as components
                components.html(f24_facsimile, height=650, scrolling=True)

            # Template Home Banking per istituti
            with st.expander("🏦 Template Copia & Incolla Specifico per Home Banking (UniCredit, Intesa, Fineco, BBVA, Poste)", expanded=False):
                st.caption("Seleziona il tuo istituto per copiare il testo formattato esatto richiesto dal relativo form bancario online.")
                b_tab1, b_tab2, b_tab3, b_tab4, b_tab5 = st.tabs(["🔴 UniCredit", "🟢 Intesa Sanpaolo", "🔵 Fineco", "🟣 BBVA", "🟡 Poste Italiane"])
                rows_f24 = f24_data.get("payment_rows", [])

                with b_tab1:
                    uc_text = "MODELLO F24 SEMPLIFICATO / ORDINARIO UNICREDIT\nSezione: ERARIO\n"
                    for r in rows_f24:
                        uc_text += f"• Tributo: {r['tributo_code']} | Rateazione: {r['rateazione']} | Anno: {r['anno_riferimento']} | Debito: {r['debito_eur']:.2f} €\n"
                    uc_text += f"Saldo Finale Addebito: {f24_data.get('net_balance_eur', 0.0):.2f} €"
                    st.text_area("Formato UniCredit Online:", value=uc_text, height=120, key=f"hb_uc_{pid_str}")

                with b_tab2:
                    isp_text = "INTESA SANPAOLO — MODELLO F24 WEB\nTipo Delega: F24 Ordinario -> Sezione Erario\n"
                    for r in rows_f24:
                        isp_text += f"Codice: {r['tributo_code']} | Rif: {r['anno_riferimento']} | Rateaz: {r['rateazione']} | Importo: {r['debito_eur']:.2f}\n"
                    isp_text += f"Totale da Pagare: {f24_data.get('net_balance_eur', 0.0):.2f} €"
                    st.text_area("Formato Intesa Sanpaolo:", value=isp_text, height=120, key=f"hb_isp_{pid_str}")

                with b_tab3:
                    fin_text = "FINECO BANK — F24 ORDINARIO ONLINE\n"
                    for r in rows_f24:
                        fin_text += f"Codice Tributo: {r['tributo_code']} | Anno: {r['anno_riferimento']} | Rateazione: {r['rateazione']} | Debito: {r['debito_eur']:.2f} €\n"
                    fin_text += f"Saldo Netto: {f24_data.get('net_balance_eur', 0.0):.2f} €"
                    st.text_area("Formato Fineco:", value=fin_text, height=120, key=f"hb_fin_{pid_str}")

                with b_tab4:
                    bbva_text = "BBVA ITALIA — PAGAMENTO F24\n"
                    for r in rows_f24:
                        bbva_text += f"Sezione: Erario | Codice: {r['tributo_code']} | Anno: {r['anno_riferimento']} | Rata: {r['rateazione']} | Importo: € {r['debito_eur']:.2f}\n"
                    bbva_text += f"Totale Addebito: € {f24_data.get('net_balance_eur', 0.0):.2f}"
                    st.text_area("Formato BBVA:", value=bbva_text, height=120, key=f"hb_bbva_{pid_str}")

                with b_tab5:
                    poste_text = "POSTE ITALIANE — BANCOPOSTA F24\n"
                    for r in rows_f24:
                        poste_text += f"Tributo: {r['tributo_code']} | Rateazione: {r['rateazione']} | Anno: {r['anno_riferimento']} | Importo a debito: {r['debito_eur']:.2f}\n"
                    poste_text += f"Saldo da quietanzare: {f24_data.get('net_balance_eur', 0.0):.2f} €"
                    st.text_area("Formato Poste Italiane:", value=poste_text, height=120, key=f"hb_poste_{pid_str}")

            # Piano rateale dettagliato se rate > 1
            if n_inst > 1 and dett_rate:
                with st.expander(f"📅 Visualizza Calendario Completo {n_inst} Rate", expanded=False):
                    df_inst = pd.DataFrame(dett_rate)
                    st.dataframe(
                        df_inst,
                        column_config={
                            "numero_rata": st.column_config.TextColumn("Codice Rata", width="small"),
                            "rata_index": st.column_config.NumberColumn("Rata #", width="small"),
                            "quota_capitale": st.column_config.NumberColumn("Quota Capitale (€)", format="€ %,.2f"),
                            "interessi_dilazione": st.column_config.NumberColumn("Interessi Dilazione (€)", format="€ %,.2f"),
                            "importo_totale_rata": st.column_config.NumberColumn("Totale Rata (€)", format="€ %,.2f"),
                        },
                        hide_index=True,
                        use_container_width=True,
                    )

            # ── 2. GUIDA AZIONABILE 730 PRECOMPILATA CON CHECKLIST ──
            st.markdown("---")
            st.markdown("##### 📋 Guida Azionabile Passo-Passo: Rettifica Portale AdE")
            st.caption("Checklist operativa con i righi e codici esatti da compilare sul sito dell'Agenzia delle Entrate per ottenere il massimo rimborso ed evitare sanzioni.")

            guide_730 = generate_730_precompilata_actionable_guide(engine, profile_id=pid_str, tax_year=selected_tax_year)

            for stp in guide_730.get("steps", []):
                st.markdown(
                    f"""
                    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: #38bdf8; font-size: 14px;">Passo {stp['step_num']}: {stp['title']}</span>
                            <span style="font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 2px 8px; border-radius: 4px;">{stp['impact_badge']}</span>
                        </div>
                        <div style="font-size: 13px; color: #cbd5e1; margin-top: 6px; line-height: 1.5;">
                            {stp['action']}
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 6px;">
                            🎯 <b>Esito Atteso:</b> {stp['expected_result']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ── 3. SINCRONIZZAZIONE SALDO FISCALE CON CASH FLOW ENGINE ──
            st.markdown("---")
            c_cf_info, c_cf_btn = st.columns([3, 1.5])
            with c_cf_info:
                st.markdown("##### 💳 Sincronizzazione Flussi Fiscali con il Cash Flow Pianificato")
                st.caption(
                    f"Registra automaticamente come eventi di cassa previsionali: l'accredito del rimborso 730 a busta paga (+{fmt_eur_it(predisp_730['new_irpef_refund'])}) ad Agosto "
                    f"e il versamento della delega F24 (-{fmt_eur_it(predisp_730['f24_foreign_total'])}) a fine Giugno."
                )
            with c_cf_btn:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if st.button("💳 Sincronizza nel Cash Flow", key=f"btn_sync_cf_{pid_str}_{selected_tax_year}", type="primary", use_container_width=True):
                    cf_sync_res = sync_tax_events_to_cashflow(engine, profile_id=pid_str, tax_year=selected_tax_year, portfolio_id=1)
                    st.success(f"✅ {cf_sync_res.get('message', 'Sincronizzazione completata!')}")
                    st.rerun()

            # ── 4. OTTIMIZZATORE DEDUCIBILITÀ PREVIDENZA COMPLEMENTARE (FONDO PENSIONE) ──
            st.markdown("---")
            with st.expander("🛡️ Ottimizzatore Previdenza Complementare (Deducibilità Art. 10 TUIR fino a € 5.164,57)", expanded=False):
                st.caption("Simula il vantaggio fiscale immediato derivante dal versamento a forme pensionistiche complementari per abbattere l'aliquota marginale IRPEF.")

                pension_opt = compute_pension_tax_deduction_optimizer(engine, profile_id=pid_str, tax_year=selected_tax_year)

                c_pen1, c_pen2, c_pen3, c_pen4 = st.columns(4)
                with c_pen1:
                    metric_card("Reddito Imponibile", fmt_eur(pension_opt["gross_taxable_income"]), "Dichiarazione / CU")
                with c_pen2:
                    metric_card("Aliquota Marginale IRPEF", f"{pension_opt['marginal_irpef_rate_pct']:.1f}%", f"+ Addizionali: {pension_opt['total_marginal_benefit_pct']:.1f}% totale")
                with c_pen3:
                    metric_card("Plafond Residuo Ded.", fmt_eur(pension_opt["remaining_deductible_cap"]), f"Cap Max: {fmt_eur(pension_opt['max_statutory_cap'])}")
                with c_pen4:
                    metric_card("Risparmio Max Potenziale", fmt_eur(pension_opt["max_potential_tax_savings"]), "Cashback fiscale in busta paga", delta_color="normal")

                st.markdown("###### 📊 Simulazione di Risparmio su Differenti Quote di Versamento")
                df_pen_sim = pd.DataFrame(pension_opt.get("simulation_table", []))
                if not df_pen_sim.empty:
                    st.dataframe(
                        df_pen_sim,
                        column_config={
                            "versamento_volontario": st.column_config.NumberColumn("Versamento Effettuato (€)", format="€ %,.2f"),
                            "quota_deducibile": st.column_config.NumberColumn("Quota Deducibile (€)", format="€ %,.2f"),
                            "risparmio_imposte_irpef": st.column_config.NumberColumn("Rimborso IRPEF Generato (€)", format="€ %,.2f"),
                            "costo_effettivo_uscita": st.column_config.NumberColumn("Costo Reale al Netto del Fisco (€)", format="€ %,.2f"),
                            "ritorno_fiscale_immediato_pct": st.column_config.NumberColumn("Ritorno Fiscale Immediato (%)", format="%.1f %%"),
                        },
                        hide_index=True,
                        use_container_width=True,
                    )
            st.markdown("---")

            # ── 5. DOSSIER FISCALE COMMERCIALISTA (1-CLICK PRINT & PDF) ──
            st.markdown("##### 📑 Dossier Fiscale Ufficiale per Commercialista / CAF (1-Click Print & PDF)")
            st.caption(
                "Fascicolo probatorio di liquidazione asseverato pronto per la stampa o la trasmissione telematica al professionista: "
                "include anagrafica, liquidazione d'imposta, righi Quadri E/RT/W, prospetto delega F24 e certificato di consistenza zainetto fiscale."
            )

            c_dos_in1, c_dos_in2 = st.columns([2, 2])
            with c_dos_in1:
                tp_name = st.text_input("Nominativo Contribuente:", value="Mario Rossi", key=f"dossier_name_{pid_str}_{selected_tax_year}")
            with c_dos_in2:
                tp_cf = st.text_input("Codice Fiscale:", value="RSSMRA85M01H501Z", key=f"dossier_cf_{pid_str}_{selected_tax_year}")

            dossier_html = generate_commercialista_tax_dossier_html(
                engine,
                profile_id=pid_str,
                tax_year=selected_tax_year,
                taxpayer_name=tp_name,
                taxpayer_cf=tp_cf,
            )

            c_dos_btn1, c_dos_btn2 = st.columns([2, 2])
            with c_dos_btn1:
                st.download_button(
                    "📥 Scarica Dossier Fiscale (.html / PDF-Ready)",
                    data=dossier_html,
                    file_name=f"dossier_fiscale_commercialista_{tp_cf}_{selected_tax_year}.html",
                    mime="text/html",
                    key=f"dl_dossier_btn_{pid_str}_{selected_tax_year}",
                    type="primary",
                    use_container_width=True,
                )
            with c_dos_btn2:
                show_preview = st.checkbox("👁️ Mostra Anteprima Documento nel Browser", value=False, key=f"preview_dossier_cb_{pid_str}_{selected_tax_year}")

            if show_preview:
                import streamlit.components.v1 as components
                components.html(dossier_html, height=750, scrolling=True)

            # ── 6. MONITORAGGIO & LIQUIDAZIONE CRIPTO-ATTIVITÀ (L. 197/2022) ──
            st.markdown("---")
            with st.expander("₿ Monitoraggio & Liquidazione Cripto-Attività (L. 197/2022 — Quadro RW Cod. 21 & Quadro RT Sez. II-B)", expanded=False):
                st.caption(
                    "Quadro fiscale asseverato per le cripto-attività detenute su wallet o exchange esteri (Binance, Kraken, Ledger): "
                    "imposta sul valore delle cripto-attività del 2‰ (Codice F24 1727) e imposta sostitutiva del 26% sulle plusvalenze eccedenti la franchigia (Codice F24 1715)."
                )
                crypto_rep = compute_crypto_tax_reporting(engine, profile_id=pid_str, tax_year=selected_tax_year)
                c_cr1, c_cr2, c_cr3, c_cr4 = st.columns(4)
                with c_cr1:
                    metric_card("Controvalore al 31/12", fmt_eur(crypto_rep["crypto_balance_31_12"]), "Consistenza Totale")
                with c_cr2:
                    metric_card("Picco Massimo Anno", fmt_eur(crypto_rep["crypto_peak_value"]), "Rilevazione RW")
                with c_cr3:
                    metric_card("Imposta Valore (0,20%)", fmt_eur(crypto_rep["imposta_valore_crypto_2_permille"]), "Codice F24 1727", delta_color="inverse")
                with c_cr4:
                    metric_card("Sostitutiva Capital Gains (26%)", fmt_eur(crypto_rep["substitute_tax_26pct"]), "Codice F24 1715", delta_color="inverse")

                st.markdown("###### 📋 Quadro RW (Codice Investimento 21 — Valute Virtuali / Cripto-Attività)")
                df_cr_rw = pd.DataFrame(crypto_rep["quadro_rw_rows"])
                st.dataframe(df_cr_rw, hide_index=True, use_container_width=True)

                st.markdown("###### 📈 Quadro RT Sezione II-B (Plusvalenze Realizzate Cripto)")
                df_cr_rt = pd.DataFrame(crypto_rep["quadro_rt_rows"])
                st.dataframe(df_cr_rt, hide_index=True, use_container_width=True)

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

