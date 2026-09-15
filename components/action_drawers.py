# ==============================================================================
# components/action_drawers.py
# ARGUS Risk Analytics — Institutional Modal Action Drawers v9.7.0
# ==============================================================================
"""
Reusable modal action drawers built on @st.dialog for institutional workflow continuity:
1. render_order_blotter_dialog: Pre-flight pre-trade impact and FIX staging blotter.
2. render_lot_inspector_dialog: Deep-dive tax lot inspector (TUIR Art. 44 vs 67, LIFO/FIFO, PMC).
3. render_risk_decomposition_dialog: Asset-level marginal VaR and Euler risk attribution.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.chart_framework import ObsidianTheme, apply_argus_theme


@st.dialog("📋 Pre-Trade Pre-Flight & Order Staging Blotter", width="large")
def render_order_blotter_dialog(
    drift_summary: Optional[Dict[str, Any]] = None,
    portfolio_value: float = 0.0,
) -> None:
    """
    Action Drawer modale per la revisione e l'invio degli ordini generati dal rebalancing.
    Consente di visualizzare la conformità normativa (TUIR Art. 44 vs 67), LIFO lotti,
    turnover stimato e impatto VaR post-trade prima di impegnare il book ordini.
    """
    if not drift_summary:
        drift_summary = {
            "turnover": 385_000.0,
            "net_tax_impact": -2_450.0,
            "pre_var": 2.12,
            "post_var": 1.85,
            "orders": [
                {
                    "ISIN": "US0378331005",
                    "Ticker": "AAPL",
                    "Azione": "SELL",
                    "Quantità": 850,
                    "Prezzo Stimato": 195.40,
                    "Controvalore": 166_090.0,
                    "Regime Fiscale": "Art. 67 (CG - Compensabile)",
                    "Plus/Minus Stima": "+€ 14,200",
                },
                {
                    "ISIN": "IE00B4L5Y983",
                    "Ticker": "IWDA.AS",
                    "Azione": "BUY",
                    "Quantità": 1400,
                    "Prezzo Stimato": 89.20,
                    "Controvalore": 124_880.0,
                    "Regime Fiscale": "Art. 44 (OICR - Reddito Cap.)",
                    "Plus/Minus Stima": "N/D (Acquisto)",
                },
                {
                    "ISIN": "IT0005246340",
                    "Ticker": "BTP-10Y",
                    "Azione": "BUY",
                    "Quantità": 950,
                    "Prezzo Stimato": 100.45,
                    "Controvalore": 95_427.5,
                    "Regime Fiscale": "White List (12.5% Tax)",
                    "Plus/Minus Stima": "N/D (Acquisto)",
                },
            ],
        }

    turnover = drift_summary.get("turnover", 0.0)
    net_tax = drift_summary.get("net_tax_impact", 0.0)
    pre_var = drift_summary.get("pre_var", 2.12)
    post_var = drift_summary.get("post_var", 1.85)
    var_delta = post_var - pre_var

    st.caption("Verifica pre-trade conformità normativa TUIR, turnover portafoglio e marginal VaR reduction.")

    # Metriche riassuntive
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Turnover Stimato", f"€ {turnover:,.2f}")
    m2.metric(
        "Impatto Fiscale Netto",
        f"€ {net_tax:,.2f}",
        delta="-€ 1,240 Tax Shield" if net_tax < 0 else None,
        delta_color="normal",
    )
    m3.metric("VaR 99% Pre-Trade", f"{pre_var:.2f}%")
    m4.metric(
        "VaR 99% Post-Trade",
        f"{post_var:.2f}%",
        delta=f"{var_delta:+.2f}%",
        delta_color="inverse",
    )

    st.markdown("##### Ordini Pronti per lo Staging")
    orders_data = drift_summary.get("orders", [])
    if orders_data:
        df_orders = pd.DataFrame(orders_data)
        st.dataframe(
            df_orders,
            column_config={
                "ISIN": st.column_config.TextColumn("ISIN", width="medium"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Azione": st.column_config.TextColumn("Side", width="small"),
                "Quantità": st.column_config.NumberColumn("Quantità", format="%d"),
                "Prezzo Stimato": st.column_config.NumberColumn("Prezzo Stima", format="€ %,.2f"),
                "Controvalore": st.column_config.NumberColumn("Controvalore", format="€ %,.2f"),
                "Regime Fiscale": st.column_config.TextColumn("Regime TUIR", width="medium"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Nessun ordine generato dai vincoli attuali.")

    st.divider()
    c_left, c_right = st.columns([3, 2])
    with c_left:
        routing_mode = st.radio(
            "Routing di Esecuzione",
            ["Stage nel Blotter Locale (Simulazione)", "Invia a FIX Engine / Drop-Copy"],
            horizontal=True,
            label_visibility="collapsed",
        )
    with c_right:
        col_cancel, col_confirm = st.columns(2)
        with col_cancel:
            if st.button("Annulla", use_container_width=True):
                st.rerun()
        with col_confirm:
            if st.button("🚀 Conferma & Staging", type="primary", use_container_width=True):
                st.session_state["staged_orders_active"] = orders_data
                st.session_state["last_staging_timestamp"] = pd.Timestamp.now().isoformat()
                st.toast("✅ Ordini registrati nel Blotter con successo!", icon="📋")
                st.rerun()


@st.dialog("🔍 Dettaglio Titolo & Lotti Fiscali (TUIR)", width="large")
def render_lot_inspector_dialog(
    asset_symbol: str,
    asset_name: Optional[str] = None,
    asset_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Action Drawer modale per l'ispezione approfondita del regime fiscale del singolo titolo:
    - Prezzo Medio di Carico Fiscale (PMC)
    - Distinzione Redditi di Capitale (Art. 44) vs Redditi Diversi (Art. 67)
    - Minusvalenze pregresse compensabili e scadenza quadriennale
    - Storico lotti LIFO / FIFO
    """
    title_name = asset_name or asset_symbol
    st.caption(f"Ispezione anagrafica, lotti storici e zainetto fiscale per lo strumento **{asset_symbol}** ({title_name})")

    # Dati predefiniti o passati dal chiamante
    if not asset_data:
        is_etf = "etf" in asset_symbol.lower() or "iwda" in asset_symbol.lower() or "swda" in asset_symbol.lower()
        regime = "Art. 44 TUIR (Redditi di Capitale - OICR)" if is_etf else "Art. 67 TUIR (Redditi Diversi - Azioni/ETC)"
        compensabile = "❌ No (Le plusvalenze OICR non compensano minusvalenze)" if is_etf else "✅ Sì (Compensa minusvalenze pregresse nello zainetto)"
        aliquota = "26.00%"

        asset_data = {
            "isin": f"US_{asset_symbol}_01",
            "asset_class": "Equity / ETF" if is_etf else "Equity Azionario",
            "regime": regime,
            "compensabile": compensabile,
            "aliquota": aliquota,
            "pmc_fiscale": 142.50,
            "current_price": 178.20,
            "total_qty": 250,
            "lots": [
                {"Data": "2023-04-15", "Quantità": 100, "Prezzo Carico": 135.0, "Prezzo Attuale": 178.20, "P&L Non Realizzato": "+€ 4,320.00", "Lotto": "#1 (LIFO)"},
                {"Data": "2023-11-20", "Quantità": 80, "Prezzo Carico": 145.5, "Prezzo Attuale": 178.20, "P&L Non Realizzato": "+€ 2,616.00", "Lotto": "#2"},
                {"Data": "2024-06-10", "Quantità": 70, "Prezzo Carico": 150.0, "Prezzo Attuale": 178.20, "P&L Non Realizzato": "+€ 1,974.00", "Lotto": "#3 (FIFO)"},
            ],
        }

    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Attuale", f"€ {asset_data.get('current_price', 0.0):,.2f}")
    c2.metric("PMC Fiscale", f"€ {asset_data.get('pmc_fiscale', 0.0):,.2f}")
    pnl_unreal = (asset_data.get("current_price", 0.0) - asset_data.get("pmc_fiscale", 0.0)) * asset_data.get("total_qty", 0)
    c3.metric("Plusvalenza Latente", f"€ {pnl_unreal:,.2f}", delta=f"{(pnl_unreal / (asset_data.get('pmc_fiscale', 1.0) * asset_data.get('total_qty', 1))) * 100:+.2f}%")

    st.markdown(
        f"""
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px 16px; margin: 12px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                <span style="color:#8b949e; font-size:12px; font-weight:600;">INQUADRAMENTO TRIBUTARIO:</span>
                <span style="color:#38bdf8; font-size:12px; font-weight:700;">{asset_data.get('regime')}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                <span style="color:#8b949e; font-size:12px; font-weight:600;">COMPENSABILITÀ MINUSVALENZE:</span>
                <span style="font-size:12px; font-weight:700;">{asset_data.get('compensabile')}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#8b949e; font-size:12px; font-weight:600;">ALIQUOTA APPLICABILE:</span>
                <span style="color:#f59e0b; font-size:12px; font-weight:700;">{asset_data.get('aliquota')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Stratificazione Lotti Fiscali (Metodo LIFO / FIFO)")
    lots = asset_data.get("lots", [])
    if lots:
        df_lots = pd.DataFrame(lots)
        st.dataframe(df_lots, use_container_width=True, hide_index=True)

    if st.button("Chiudi", use_container_width=True):
        st.rerun()


@st.dialog("🔬 Decomposizione Rischio & Attribuzione Euler", width="large")
def render_risk_decomposition_dialog(
    asset_symbol: str,
    risk_metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """Action Drawer modale per la diagnosi del rischio marginale e sensibilità dell'asset."""
    st.caption(f"Decomposizione quantitativa del rischio, correlazione con benchmark e sensibilità per **{asset_symbol}**")

    if not risk_metrics:
        risk_metrics = {
            "marginal_var_bps": 18.5,
            "component_var_eur": 45_200.0,
            "pct_total_risk": 5.34,
            "beta_benchmark": 1.18,
            "volatility_annualized": 24.5,
            "sharpe_standalone": 1.22,
        }

    c1, c2, c3 = st.columns(3)
    c1.metric("Marginal VaR", f"{risk_metrics.get('marginal_var_bps', 0.0):.1f} bps")
    c2.metric("Component VaR", f"€ {risk_metrics.get('component_var_eur', 0.0):,.0f}")
    c3.metric("Beta vs SPY/Benchmark", f"{risk_metrics.get('beta_benchmark', 1.0):.2f}")

    # Micro-grafico della decomposizione
    categories = ["Volatilità", "Sensibilità Tassi", "Correlazione", "Rischio Coda (ES)", "Liquidità"]
    values = [75, 40, 65, 80, 25]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=[ObsidianTheme.ELECTRIC_BLUE, ObsidianTheme.AMBER, ObsidianTheme.PURPLE, ObsidianTheme.CRIMSON, ObsidianTheme.EMERALD],
        text=[f"{v}/100" for v in values],
        textposition="outside",
    ))
    apply_argus_theme(fig, title=f"Profilo di Rischio Multidimensionale - {asset_symbol}", height=260)
    fig.update_layout(yaxis=dict(range=[0, 100]), showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if st.button("Chiudi Analisi", use_container_width=True):
        st.rerun()
