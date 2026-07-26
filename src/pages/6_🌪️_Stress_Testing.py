import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, fmt_pct, glossary_modal, render_executive_badges, apply_plotly_theme

st.set_page_config(page_title="Stress Testing | ARGUS", page_icon="🌪️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

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
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#ff3333"}},
                totals={"marker":{"color":"#4361ee"}},
                increasing={"marker":{"color":"#00ff66"}}
            ))
            fig_wf.update_layout(
                template="plotly_dark", height=350,
                margin=dict(l=0, r=0, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified"
            )
            fig_wf.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
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
                    fig.update_layout(
                        template="plotly_dark", height=350,
                        margin=dict(l=0, r=0, t=10, b=30),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        coloraxis_showscale=False
                    )
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
                    st.plotly_chart(fig, use_container_width=True)

# ── TAB 3: SIMULATORE WHAT-IF CUSTOM ──────────────────────────
with tab3:
    st.markdown("#### 🛠️ Simulatore di Stress Test Personalizzato (What-if)")
    st.caption("Ipotizza uno scenario di mercato personalizzato inserendo una variazione teorica del Benchmark. Il sistema stimerà l'impatto sul portafoglio e sui singoli asset basandosi sulla sensibilità attuale (Beta).")

    col_sim1, col_sim2 = st.columns([1, 2])
    with col_sim1:
        benchmark_shock = st.slider(
            "Shock teorico del Benchmark (%)",
            min_value=-50,
            max_value=30,
            value=-15,
            step=1,
            help="Ad esempio, inserisci -15% per simulare una correzione moderata o -30% per simulare un mercato ribassista (bear market) violento."
        )
        
        st.info(r"""
        **Metodologia del calcolo:**
        *   **Impatto Asset** = $\text{Beta dell'Asset} \times \text{Shock Benchmark}$
        *   **Perdita Asset** = $\text{Impatto Asset} \times \text{Valore Attuale dell'Asset}$
        *   **Impatto Portafoglio** = $\sum (\text{Impatto Asset} \times \text{Peso dell'Asset})$ o $\text{Beta di Portafoglio} \times \text{Shock Benchmark}$
        """)

    port_beta = results["metrics"]["market_risk"].get("beta", 1.0)
    if port_beta is None:
        port_beta = 1.0

    port_shock_pct = port_beta * (benchmark_shock / 100)
    port_loss_eur = port_shock_pct * portfolio_value

    first_scenario = list(stress.keys())[0]
    scen_details = stress[first_scenario]["details"]

    active_assets = []
    for ticker, info in scen_details.items():
        pos_row = pos[pos["ticker"] == ticker]
        if not pos_row.empty:
            curr_val = pos_row.iloc[0]["current_value"]
            weight = pos_row.iloc[0]["weight_pct"]
        else:
            curr_val = 0.0
            weight = 0.0
            
        beta = info.get("beta", 1.0)
        asset_shock = beta * (benchmark_shock / 100)
        asset_loss = asset_shock * curr_val
        
        active_assets.append({
            "Ticker": ticker,
            "Peso %": weight,
            "Valore Corrente": curr_val,
            "Beta": beta,
            "Shock Stimato %": asset_shock * 100,
            "Perdita Estimata (€)": asset_loss
        })

    df_sim = pd.DataFrame(active_assets)

    with col_sim2:
        st.markdown("#### Impatto sul Portafoglio")
        
        col_cards1, col_cards2, col_cards3 = st.columns(3)
        with col_cards1:
            metric_card(
                "Shock Benchmark Scelto",
                f"{benchmark_shock:.1f}%",
                positive=benchmark_shock >= 0
            )
        with col_cards2:
            metric_card(
                "Impatto Stimato Portafoglio",
                f"{port_shock_pct * 100:.2f}%",
                positive=port_shock_pct >= 0,
                help_text="Calcolato come: Beta di Portafoglio * Shock Benchmark"
            )
        with col_cards3:
            metric_card(
                "Perdita Stimata Portafoglio",
                fmt_eur(port_loss_eur),
                positive=port_loss_eur >= 0
            )

        final_sim_value = portfolio_value + port_loss_eur
        fig_sim_wf = go.Figure(go.Waterfall(
            name="What-If Simulator", orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Valore Attuale", "Impatto Simulato", "Valore Simulato"],
            textposition="outside",
            text=[fmt_eur(portfolio_value), fmt_eur(port_loss_eur), fmt_eur(final_sim_value)],
            y=[portfolio_value, port_loss_eur, final_sim_value],
            connector={"line":{"color":"rgb(63, 63, 63)"}},
            decreasing={"marker":{"color":"#ff3333"}},
            totals={"marker":{"color":"#4361ee"}},
            increasing={"marker":{"color":"#00ff66"}}
        ))
        fig_sim_wf.update_layout(
            template="plotly_dark", height=280,
            margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified"
        )
        fig_sim_wf.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
        st.plotly_chart(fig_sim_wf, use_container_width=True)

    st.divider()
    st.markdown("#### Impatto Dettagliato per Singolo Asset (Simulato)")
    df_sim_disp = df_sim.copy()
    df_sim_disp = df_sim_disp.sort_values(by="Perdita Estimata (€)", ascending=True)

    df_sim_disp["Peso %"] = df_sim_disp["Peso %"].apply(lambda x: f"{x:.2f}%")
    df_sim_disp["Valore Corrente"] = df_sim_disp["Valore Corrente"].apply(lambda x: f"€ {x:,.2f}")
    df_sim_disp["Beta"] = df_sim_disp["Beta"].apply(lambda x: f"{x:.2f}")
    df_sim_disp["Shock Stimato %"] = df_sim_disp["Shock Stimato %"].apply(lambda x: f"{x:+.2f}%")
    df_sim_disp["Perdita Estimata (€)"] = df_sim_disp["Perdita Estimata (€)"].apply(lambda x: f"€ {x:,.2f}")

    st.dataframe(df_sim_disp, use_container_width=True, hide_index=True)
