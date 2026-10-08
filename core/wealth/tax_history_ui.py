# ============================================================
# core/wealth/tax_history_ui.py
# ARGUS — UI Component: Archivio Storico Fiscale & Riconciliazione (730 / Redditi PF)
# Sezione 1: Gestione & Inserimento (Upload PDF / Form manuale / Data Editor)
# Sezione 2: Dashboard Storica & Zainetto Fiscale (Timeline 5Y & Semafori AdE)
# Sezione 3: Audit & Punti di Miglioria (Advisor Alerts & Art. 36-bis Risk)
# ============================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import Engine

from core.ui_utils import fmt_eur, metric_card, render_table_with_export
from core.wealth.tax_history_engine import (
    delete_declaration,
    delete_tax_loss,
    fmt_eur_it,
    get_declarations,
    get_tax_losses,
    parse_730_pdf_or_json,
    reconcile_with_portfolio,
    record_declaration,
    record_tax_loss,
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

        col_up1, col_up2 = st.columns([1.2, 1])

        # ── TAB A: FILE UPLOADER & SMART PARSER ──
        with col_up1:
            st.markdown("##### 📄 Caricamento File (PDF / JSON)")
            uploaded_file = st.file_uploader(
                "Trascina il PDF o JSON del Modello 730 / Redditi PF:",
                type=["pdf", "json", "txt"],
                key=f"file_uploader_tax_{pid_str}",
                help="Supporta PDF ufficiali rilasciati dall'AdE con Quadri Redditi, T/RT, Quadro W/RW e prospetto di liquidazione.",
            )

            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                filename = uploaded_file.name

                with st.spinner("Analisi ed estrazione automatica dei quadri fiscali in corso..."):
                    parsed_data = parse_730_pdf_or_json(file_bytes, filename=filename)
                    parsed_data["profile_id"] = pid_str

                st.success(f"File **{filename}** elaborato con successo!")

                # Preview e conferma dei dati estratti
                with st.expander("🔍 Verifica Campi Estratti ed Archiviazione", expanded=True):
                    c_p1, c_p2 = st.columns(2)
                    with c_p1:
                        p_year = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=int(parsed_data["tax_year"]), key=f"p_yr_{pid_str}")
                        p_model = st.selectbox("Modello:", ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"], index=0 if parsed_data["model_type"] == "730_ORDINARIO" else (1 if parsed_data["model_type"] == "730_INTEGRATIVO" else 2), key=f"p_md_{pid_str}")
                        p_proto = st.text_input("Protocollo Telematico:", value=str(parsed_data.get("protocol_id") or ""), key=f"p_pr_{pid_str}")
                        p_gross = st.number_input("Reddito Complessivo (€):", value=float(parsed_data["gross_income"]), step=500.0, key=f"p_gr_{pid_str}")
                        p_net_tax = st.number_input("Imposta Netta IRPEF (€):", value=float(parsed_data["net_tax_irpef"]), step=100.0, key=f"p_nt_{pid_str}")
                    with c_p2:
                        p_cg = st.number_input("Plusvalenze Quadro T/RT (€):", value=float(parsed_data["capital_gains_declared"]), step=100.0, key=f"p_cg_{pid_str}")
                        p_cl = st.number_input("Minusvalenze Compensate T13 (€):", value=float(parsed_data["capital_losses_offset"]), step=100.0, key=f"p_cl_{pid_str}")
                        p_sub = st.number_input("Imposta Sostitutiva 26% (Rigo 321) (€):", value=float(parsed_data["substitute_tax_paid"]), step=50.0, key=f"p_sb_{pid_str}")
                        p_ivafe = st.number_input("IVAFE (Rigo 307 / Quadro W) (€):", value=float(parsed_data["ivafe_paid"]), step=10.0, key=f"p_iv_{pid_str}")
                        p_for = st.number_input("Attività Estere Valore Finale (€):", value=float(parsed_data["foreign_assets_val"]), step=1000.0, key=f"p_fa_{pid_str}")

                    if st.button("💾 Conferma & Salva in Archivio", key=f"btn_save_parsed_{pid_str}", type="primary", use_container_width=True):
                        to_save = {
                            "profile_id": pid_str,
                            "tax_year": p_year,
                            "filing_year": p_year + 1,
                            "model_type": p_model,
                            "protocol_id": p_proto,
                            "gross_income": p_gross,
                            "taxable_income": p_gross,
                            "net_tax_irpef": p_net_tax,
                            "capital_gains_declared": p_cg,
                            "capital_losses_offset": p_cl,
                            "substitute_tax_paid": p_sub,
                            "ivafe_paid": p_ivafe,
                            "foreign_assets_val": p_for,
                            "notes": f"Importato da file: {filename}",
                            "source_filename": filename,
                        }
                        decl_id = record_declaration(engine, to_save)
                        st.success(f"✅ Dichiarazione registrata con ID #{decl_id}!")
                        st.rerun()

        # ── TAB B: INSERIMENTO MANUALE RAPIDO ──
        with col_up2:
            st.markdown("##### ✍️ Inserimento Rapido a Mano")
            with st.form(f"manual_decl_form_{pid_str}"):
                fm_year = st.number_input("Anno d'Imposta:", min_value=2015, max_value=2030, value=selected_tax_year)
                fm_model = st.selectbox("Tipologia Modello:", ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"])
                fm_proto = st.text_input("Protocollo AdE (opzionale):", placeholder="es. 2506241029384756100234")
                fm_gross = st.number_input("Reddito Complessivo Lordo (€):", min_value=0.0, value=0.0, step=1000.0)
                fm_cg = st.number_input("Plusvalenze Dichiarate (T11/RT11) (€):", min_value=0.0, value=0.0, step=100.0)
                fm_cl = st.number_input("Minusvalenze Compensate (T13/RT13) (€):", min_value=0.0, value=0.0, step=100.0)
                fm_sub = st.number_input("Imposta Sostitutiva 26% Versata (Rigo 321) (€):", min_value=0.0, value=0.0, step=50.0)
                fm_ivafe = st.number_input("IVAFE Versata (Rigo 307) (€):", min_value=0.0, value=0.0, step=10.0)
                fm_for = st.number_input("Monitoraggio Estero Valore Finale (RW) (€):", min_value=0.0, value=0.0, step=1000.0)
                fm_notes = st.text_input("Note:", placeholder="es. Liquidazione da commercialista")

                submitted = st.form_submit_button("Salva Dichiarazione Manuale", type="primary", use_container_width=True)
                if submitted:
                    to_save_man = {
                        "profile_id": pid_str,
                        "tax_year": int(fm_year),
                        "filing_year": int(fm_year) + 1,
                        "model_type": fm_model,
                        "protocol_id": fm_proto if fm_proto else None,
                        "gross_income": fm_gross,
                        "taxable_income": fm_gross,
                        "net_tax_irpef": 0.0,
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
                            "taxable_income": float(r_dict.get("gross_income", 0.0) or 0.0),
                            "net_tax_irpef": 0.0,
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
        st.markdown("##### 💼 Monitoraggio Tranches Zainetto Fiscale (Art. 68 TUIR)")
        st.caption("Ogni pacchetto di minusvalenza ha una scadenza inderogabile di 4 anni solari. Il semaforo indica la conformità con l'Anagrafe Tributaria.")

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
