import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, fmt_pct, glossary_modal, render_executive_badges, apply_plotly_theme, render_command_bar

st.set_page_config(page_title="Stress Testing | ARGUS", page_icon="🌪️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()
render_command_bar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
stress = results.get("stress_tests", {})
pos = results.get("positions", pd.DataFrame())
portfolio_value = pos["current_value"].sum() if not pos.empty else 0

st.title("🌪️ Stress Testing & Resilience Analysis")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Simulazione d'impatto e matrice MSCI Barra nei 5 principali scenari storici di crisi e stress macroeconomico.")
col_head1, col_head2 = st.columns([3.5, 1])
with col_head1:
    render_executive_badges(results["metrics"])
with col_head2:
    glossary_modal("Cos'è lo Stress Testing?",
    "Simulazione dell'impatto di eventi di mercato estremi sul valore corrente del tuo portafoglio. <b>L'analisi è basata sui rendimenti storici reali degli asset durante le date specifiche delle crisi.</b> Se un asset non ha dati storici per quel periodo, il modello stima l'impatto usando la sua sensibilità attuale al mercato (Beta).", button_label="💡 Come funziona?")

st.divider()

if not stress:
    st.info("Risultati dello stress test non disponibili (dati insufficienti).")
    st.stop()

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ ─────────────────────
tab1, tab2, tab3 = st.tabs([
    "⚡ Matrice Comparativa MSCI Barra",
    "🏛️ Analisi Scenari Storici Dettagliata",
    "🛠️ Simulatore What-if Custom"
])

# ── TAB 1: MATRICE COMPARATIVA MSCI BARRA ─────────────────────
with tab1:
    st.markdown("#### ⚡ Matrice Comparativa di Stress Test Simultanea (MSCI Barra Style)")
    st.caption("Confronta l'impatto stimato in € e % del tuo portafoglio in tutti gli scenari di crisi contemporaneamente")

    glossary_modal("ℹ️ Guida alla Matrice di Stress Test (MSCI Barra Style)", """
    <p><b>Cos'è la Matrice Comparativa di Stress Test?</b><br>
    Un quadro comparativo completo che affianca simultaneamente tutti i 5 scenari storici di crisi (Dot-Com 2000, Lehman 2008, US Downgrade 2011, COVID 2020, Rate Shock 2022). Permette di valutare l'asimmetria delle perdite e verificare in quali contesti macroeconomici il portafoglio risulta più vulnerabile.</p>
    """, button_label="💡 Come funziona la Matrice di Stress Test?")

    df_matrix_rows = []
    for sc_name, sc_data in stress.items():
        df_matrix_rows.append({
            "Scenario": sc_name,
            "Shock Mercato %": sc_data.get("benchmark_shock_pct", 0.0),
            "Impatto Portafoglio %": sc_data.get("portfolio_shock_pct", 0.0),
            "Perdita Stimata (€)": sc_data.get("portfolio_loss_eur", 0.0),
        })

    df_matrix = pd.DataFrame(df_matrix_rows)

    col_mat1, col_mat2 = st.columns([1.2, 1])
    with col_mat1:
        st.dataframe(
            df_matrix.style.format({
                "Shock Mercato %": "{:.2f}%",
                "Impatto Portafoglio %": "{:.2f}%",
                "Perdita Stimata (€)": "€ {:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )

    with col_mat2:
        fig_mat = px.bar(
            df_matrix,
            x="Scenario",
            y="Impatto Portafoglio %",
            color="Impatto Portafoglio %",
            color_continuous_scale="Reds_r",
            text_auto=".1f"
        )
        fig_mat.update_traces(
            hovertemplate="<b>Scenario: %{x}</b><br>⚡ Impatto Portafoglio: %{y:.2f}%<extra></extra>"
        )
        fig_mat.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
        apply_plotly_theme(fig_mat)
        st.plotly_chart(fig_mat, use_container_width=True)

# ── TAB 2: ANALISI SCENARI STORICI DETTAGLIATA ────────────────
with tab2:
    st.markdown("#### Analisi dei Singoli Scenari Storici di Crisi")
    scenario_names = list(stress.keys())
    sub_tabs = st.tabs(scenario_names)

    for i, scenario in enumerate(scenario_names):
        with sub_tabs[i]:
            data = stress[scenario]
            st.markdown(f"### Scenario: {scenario}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                metric_card("Shock Mercato (S&P500)", fmt_pct(data['benchmark_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> Crollo percentuale effettivo dell'S&P500 durante questo specifico scenario di crisi.")
            with col2:
                metric_card("Impatto Stimato Portafoglio", fmt_pct(data['portfolio_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> Flessione percentuale che il tuo portafoglio attuale subirebbe se si ripetesse questo scenario.")
            with col3:
                metric_card("Perdita Stimata (Euro)", fmt_eur(data['portfolio_loss_eur']), positive=False, help_text="<b>Cosa significa:</b> La traduzione in Euro crudi della potenziale perdita di capitale.")
                
            st.markdown("#### Impatto sul Capitale (Waterfall)")
            loss = data['portfolio_loss_eur']
            final_value = portfolio_value + loss
            
            fig_wf = go.Figure(go.Waterfall(
                name="Stress Test", orientation="v",
                measure=["absolute", "relative", "total"],
                x=["Valore Pre-Crisi", "Impatto Crisi", "Valore Post-Crisi"],
                textposition="outside",
                text=[fmt_eur(portfolio_value), fmt_eur(loss), fmt_eur(final_value)],
                y=[portfolio_value, loss, final_value],
                connector={"line":{"color":"rgba(255,255,255,0.2)"}},
                decreasing={"marker":{"color":"#f85149"}},
                totals={"marker":{"color":"#58a6ff"}},
                increasing={"marker":{"color":"#00e676"}}
            ))
            fig_wf.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=0, r=0, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified"
            )
            fig_wf.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.06)")
            apply_plotly_theme(fig_wf)
            st.plotly_chart(fig_wf, use_container_width=True)

            st.divider()
            st.markdown("#### Impatto per singolo Asset")
            
            details = data["details"]
            if details:
                df_det = pd.DataFrame.from_dict(details, orient="index").reset_index()
                rename_map = {"index": "Ticker", "beta": "Beta Fallback", "shock_pct": "Shock Effettivo %", "loss_eur": "Perdita Stimata (€)", "is_historical": "Dato Storico Reale"}
                df_det.rename(columns={k: v for k, v in rename_map.items() if k in df_det.columns}, inplace=True)
                df_det = df_det.sort_values(by="Perdita Stimata (€)", ascending=True)
                
                col_t, col_c = st.columns([1, 1])
                with col_t:
                    df_disp = df_det.copy()
                    df_disp["Shock Effettivo %"] = df_disp["Shock Effettivo %"].apply(lambda x: f"{x:.2f}%")
                    df_disp["Perdita Stimata (€)"] = df_disp["Perdita Stimata (€)"].apply(lambda x: f"€ {x:,.2f}")
                    if "Dato Storico Reale" in df_disp.columns:
                        df_disp["Dato Storico Reale"] = df_disp["Dato Storico Reale"].apply(lambda x: "✅ Sì" if x else "❌ No (Beta)")
                    st.dataframe(df_disp, use_container_width=True, hide_index=True)
                    
                with col_c:
                    st.markdown("**Perdita per Asset**")
                    fig = px.bar(
                        df_det, 
                        x="Perdita Stimata (€)", 
                        y="Ticker", 
                        orientation='h',
                        color="Perdita Stimata (€)",
                        color_continuous_scale="Reds_r"
                    )
                    fig.update_traces(
                        hovertemplate="<b>Ticker: %{y}</b><br>🔻 Perdita Stimata: € %{x:,.2f}<extra></extra>"
                    )
                    fig.update_layout(
                        template="plotly_dark", height=350,
                        margin=dict(l=0, r=0, t=10, b=30),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        coloraxis_showscale=False
                    )
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.06)")
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.06)")
                    apply_plotly_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)

# ── TAB 3: SIMULATORE WHAT-IF & MACRO SCENARIO BUILDER ─────────
with tab3:
    st.markdown("#### 🛠️ Macro Scenario Builder Multi-Fattoriale & Simulatore What-If")
    st.caption("Manovra i parametri macroeconomici (Tassi d'interesse, Tasso EUR/USD, Prezzo Petrolio, Shock Azionario) per simulare scenari complessi di mercato sul tuo portafoglio.")

    glossary_modal("⚡ Guida al Macro Scenario Builder Multi-Fattoriale", r"""
    <p><b>Cos'è il Macro Scenario Builder?</b><br>
    Un simulatore avanzato di stress test che permette di combinare più shock macroeconomici contemporaneamente per testare la solidità del portafoglio:</p>
    <ul>
        <li><b>Shock Tassi di Interesse ($\Delta r$):</b> Impatta direttamente i titoli obbligazionari in base alla duration ed applica una penalizzazione sui multipli P/E azionari.</li>
        <li><b>Shock Tasso di Cambio EUR/USD ($\Delta \text{FX}$):</b> Simula l'effetto della svalutazione o rivalutazione dell'Euro sugli asset statunitensi.</li>
        <li><b>Shock Petrolio / Materie Prime ($\Delta \text{Commodity}$):</b> Simula picchi inflazionistici e l'impatto sui titoli energetici ed industriali.</li>
        <li><b>Shock Mercato Azionario ($\Delta \text{Equity}$):</b> Correzione generale degli indici azionari mondiali.</li>
    </ul>
    """, button_label="💡 Come funziona il Macro Scenario Builder?")

    col_sim1, col_sim2 = st.columns([1.2, 2.5])
    with col_sim1:
        st.markdown("##### 🎛️ Manovra Parametri Macro")
        benchmark_shock = st.slider("Shock Mercato Azionario (%)", -50, 30, -15, 1, help="Shock generale indici azionari")
        rate_shock_bps = st.slider("Variazione Tassi BCE/FED (bps)", -200, 300, 100, 25, help="+100 bps = rialzo tassi di 1.00%")
        fx_shock_pct = st.slider("Shock Cambio EUR/USD (%)", -20, 20, -5, 1, help="-5% = svalutazione EUR del 5%")
        oil_shock_pct = st.slider("Shock Petrolio / Materie Prime (%)", -40, 60, 20, 5, help="+20% = impennata prezzi energia")

    from core.risk_engine import compute_custom_macro_stress
    macro_res = compute_custom_macro_stress(
        pos, 
        rate_shock_bps=rate_shock_bps, 
        fx_shock_pct=fx_shock_pct, 
        oil_shock_pct=oil_shock_pct, 
        equity_shock_pct=benchmark_shock
    )

    with col_sim2:
        st.markdown("##### 📊 Impatto Stimato sul Portafoglio")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            metric_card("Valore Attuale Portafoglio", fmt_eur(macro_res.get("portfolio_val_before", 0.0)))
        with c_m2:
            metric_card("Impatto Macro Stimato (%)", f"{macro_res.get('portfolio_impact_pct', 0.0):+.2f}%", positive=macro_res.get("portfolio_impact_pct", 0.0) >= 0)
        with c_m3:
            metric_card("Variazione Stimata (€)", fmt_eur(macro_res.get("portfolio_loss_eur", 0.0)), positive=macro_res.get("portfolio_loss_eur", 0.0) >= 0)

        if not macro_res["details_df"].empty:
            st.markdown("##### 📋 Dettaglio Impatto per Singolo Asset")
            df_macro_disp = macro_res["details_df"].rename(columns={
                "ticker": "Ticker",
                "current_value": "Valore Attuale (€)",
                "simulated_impact_pct": "Impatto Stimato (%)",
                "simulated_loss_eur": "Variazione Stimata (€)"
            })
            st.dataframe(
                df_macro_disp.style.format({
                    "Valore Attuale (€)": "€ {:,.2f}",
                    "Impatto Stimato (%)": "{:+.2f}%",
                    "Variazione Stimata (€)": "€ {:,.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.divider()
    st.markdown("#### 🌋 Visualizzatore 3D della Superficie di Rischio (Rates vs Volatility)")
    st.caption("Esplora la superficie 3D interattiva che mappa la perdita di capitale al variare simultaneo dello Shock sui Tassi di Interesse (bps) e dello Shock sulla Volatilità / VIX (%).")

    from core.risk_engine import compute_3d_stress_surface
    surface_data = compute_3d_stress_surface(pos)

    fig_3d = go.Figure(data=[go.Surface(
        x=surface_data["rate_grid"],
        y=surface_data["vol_grid"],
        z=surface_data["z_pnl_eur"],
        colorscale="RdYlGn",
        colorbar=dict(title="PnL (€)", tickformat="€ ,.0f")
    )])

    fig_3d.update_layout(
        title="Superficie 3D di Stress Test: Impatto Capitale (€)",
        scene=dict(
            xaxis_title="Shock Tassi (bps)",
            yaxis_title="Shock Volatilità (%)",
            zaxis_title="Impatto PnL (€)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig_3d, use_container_width=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        metric_card("Punto Peggiore sulla Superficie", fmt_eur(surface_data["worst_pnl_eur"]), positive=False, help_text="La massima perdita stimata sulla griglia di shock tassi x volatilità")
    with col_s2:
        metric_card("Punto Migliore sulla Superficie", fmt_eur(surface_data["best_pnl_eur"]), positive=True, help_text="Il massimo guadagno stimato sulla griglia di shock tassi x volatilità")
