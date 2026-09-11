"""
ARGUS — Quantitative Risk & Wealth Intelligence Platform
Core Module: UX Onboarding Guard & Intelligent Empty State Experience
Prevents cold-start application crashes, provides institutional empty states,
and delivers one-click demo portfolio initialization across all 21 pages.
"""

from typing import Callable, Optional

import pandas as pd
import streamlit as st

from core.unified_demo_seeder import seed_unified_demo_scenario


def render_empty_state_screen(
    portal: str = "risk",
    custom_title: Optional[str] = None,
    custom_desc: Optional[str] = None
) -> None:
    """
    Renderizza un placeholder grafico elegante e istituzionale con invito
    all'azione (One-Click Demo 5 Pilastri o Upload File CSV Broker).
    """
    title = custom_title or ("Cockpit Quantitativo & Risk Analytics" if portal == "risk" else "Total Wealth & Family Office Hub")

    st.markdown(f"""
        <div style="text-align: center; padding: 42px 24px; background: linear-gradient(180deg, rgba(15,23,42,0.6) 0%, rgba(15,23,42,0.2) 100%);
                    border: 1px dashed rgba(56,189,248,0.3); border-radius: 14px; margin-bottom: 28px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);">
            <div style="font-size: 52px; margin-bottom: 12px; filter: drop-shadow(0 2px 8px rgba(56,189,248,0.4));">🛡️</div>
            <h2 style="margin: 0 0 8px 0; color: #F8FAFC; font-weight: 800; font-size: 24px; letter-spacing: -0.5px;">
                Nessun Portafoglio Attivo Rilevato per {title}
            </h2>
            <p style="color: #94A3B8; max-width: 680px; margin: 0 auto 24px auto; font-size: 14.5px; line-height: 1.6;">
                Benvenuto in <b>ARGUS</b>. Per sbloccare l'intera potenza del motore di calcolo, esplora subito
                lo scenario dimostrativo a 5 pilastri patrimoniali oppure carica le transazioni dei tuoi broker.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col_demo, col_upload = st.columns([1, 1], gap="large")

    with col_demo:
        st.markdown("### ⚡ Opzione 1: One-Click Demo Istituzionale")
        st.caption("Esplora istantaneamente entrambi i moduli con dati sintetici realistici pre-calcolati:")

        st.markdown("""
            - 💼 **Liquidità & Depositi**: €95.000 (Cassa operativa + Conto 3%)
            - 📈 **Azioni & ETF Globali**: VWCE.DE, Apple, ASML (€115.750)
            - 🏛️ **Obbligazioni Governative**: BTP 10Y Italia (€99.200)
            - 🏡 **Real Estate & Mutuo**: Immobile Milano Centro (€650k) con debito passivo (€220k)
            - ⌚ **Alternative & Previdenza**: Rolex Daytona (€24.5k) e Fondo Pensione (€38k)
        """)

        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        if st.button("🚀 Carica Portafoglio Demo (5 Pilastri)", type="primary", use_container_width=True, key="btn_onboarding_seed_demo"):
            with st.spinner("⏳ Inizializzazione dati quantitativi e patrimoniali multi-asset..."):
                seed_unified_demo_scenario()
                st.toast("✅ Portafoglio Demo Istituzionale caricato con successo!", icon="🚀")
                st.rerun()

    with col_upload:
        st.markdown("### 📂 Opzione 2: Carica Portafoglio Reale")
        st.caption("Trascina il report transazioni o posizioni esportato dal tuo broker:")

        uploaded_file = st.file_uploader(
            "File CSV o Excel (Directa, DeGiro, IBKR, Fineco, Scalable):",
            type=["csv", "xlsx"],
            key="onboarding_file_uploader"
        )

        if uploaded_file is not None:
            try:
                from core.broker_hub import detect_broker_format, parse_broker_csv
                file_bytes = uploaded_file.getvalue()
                detected_broker = detect_broker_format(file_bytes)
                st.success(f"🎯 Broker rilevato: **{detected_broker.upper()}**")

                # Pre-validazione
                df_parsed = parse_broker_csv(file_bytes, broker=detected_broker)
                if df_parsed is not None and not df_parsed.empty:
                    st.info(f"📊 Righe valide lette: **{len(df_parsed)}** | Ticker unici: **{df_parsed['ticker'].nunique()}**")
                    if st.button("📥 Importa ed Elabora con ARGUS", type="secondary", use_container_width=True, key="btn_onboarding_import_parsed"):
                        st.session_state["positions_raw"] = df_parsed
                        st.session_state["pipeline_done"] = True
                        st.session_state["portfolio_name"] = f"Portafoglio {detected_broker.capitalize()}"
                        st.rerun()
                else:
                    st.warning("⚠️ Impossibile estrarre righe valide dal file. Verifica il formato.")
            except Exception as e:
                st.error(f"Errore durante l'ispezione del file: {e}")


def empty_state_guard(portal: str = "risk") -> bool:
    """
    Guard di protezione da inserire in cima a tutte le 21 pagine Streamlit:
    Se nessun portafoglio o bundle è presente, disegna l'empty state e interrompe l'esecuzione pulita (st.stop()).
    Ritorna True se i dati sono disponibili e la pagina può continuare il rendering ordinario.
    """
    results = st.session_state.get("results")
    has_results = (
        results is not None
        and isinstance(results, dict)
        and bool(results.get("positions") is not None and not results.get("positions").empty)
    )

    pipeline_done = bool(st.session_state.get("pipeline_done", False))

    if not has_results and not pipeline_done:
        render_empty_state_screen(portal=portal)
        st.stop()
        return False

    return True
