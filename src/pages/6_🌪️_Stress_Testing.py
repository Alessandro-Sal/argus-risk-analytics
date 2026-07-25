import streamlit as st
import pandas as pd
import plotly.express as px
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, fmt_pct, glossary_modal, render_executive_badges

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

st.title("🌪️ Stress Testing")
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

# ⚡ MSCI Barra Multi-Scenario Stress Test Matrix (Side-by-Side)
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

col_mat1, col_mat2 = st.columns([1, 1])
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
    from core.ui_utils import apply_plotly_theme
    fig_mat = px.bar(
        df_matrix,
        x="Scenario",
        y="Impatto Portafoglio %",
        color="Impatto Portafoglio %",
        color_continuous_scale="Reds_r",
        text_auto=".1f"
    )
    fig_mat.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    apply_plotly_theme(fig_mat)
    st.plotly_chart(fig_mat, use_container_width=True)

st.divider()

# Crea tab per ogni scenario
scenario_names = list(stress.keys())
tabs = st.tabs(scenario_names)


for i, scenario in enumerate(scenario_names):
    with tabs[i]:
        data = stress[scenario]
        st.markdown(f"### Scenario: {scenario}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Shock Mercato (S&P500)", fmt_pct(data['benchmark_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> Rappresenta il crollo percentuale effettivo registrato dall'indice S&P500 (che funge da rappresentante del mercato azionario globale) durante le date esatte di questo specifico scenario di crisi (es. Crisi Finanziaria 2008, Pandemia 2020).\n\n<b>A cosa serve:</b> Funge da 'termometro' di base. Ti permette di capire quanto è stata devastante la crisi a livello macroeconomico, per poi confrontarla con la reazione del tuo portafoglio.\n\n<b>Come si calcola:</b> (Valore di chiusura del Benchmark alla fine del periodo di crisi diviso per il Valore all'inizio della crisi) - 1.")
        with col2:
            metric_card("Impatto Stimato Portafoglio", fmt_pct(data['portfolio_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> La flessione percentuale stimata che il tuo attuale portafoglio subirebbe se quello stesso scenario storico si ripetesse oggi in modo identico.\n\n<b>A cosa serve:</b> È il test di resilienza fondamentale. Se l'impatto stimato è peggiore dello Shock di Mercato, significa che hai un portafoglio molto aggressivo e vulnerabile. Se è nettamente inferiore, il tuo portafoglio è ben difeso (resiliente) contro i grandi crolli.\n\n<b>Come si calcola:</b> Si prendono i crolli percentuali storici reali subiti da ogni singolo asset del tuo portafoglio durante quelle stesse date, e se ne fa la media ponderata in base al peso (in Euro) che l'asset ha oggi nel tuo portafoglio.")
        with col3:
            metric_card("Perdita Stimata (Euro)", fmt_eur(data['portfolio_loss_eur']), positive=False, help_text="<b>Cosa significa:</b> La traduzione in valuta cruda e reale del crollo percentuale. Ti mostra la potenziale distruzione di ricchezza del tuo capitale.\n\n<b>A cosa serve:</b> Le percentuali spesso ingannano la psicologia umana, i soldi veri no. Vedere 'meno 40.000 Euro' ha un impatto emotivo diverso dal leggere 'meno 20%'. Serve per stress-testare la tua effettiva tolleranza psicologica alle perdite e capire se hai bisogno di un portafoglio più conservativo.\n\n<b>Come si calcola:</b> Moltiplicando il Valore Totale del tuo portafoglio attuale per l'Impatto Stimato Portafoglio (in percentuale).")
            
        import plotly.graph_objects as go
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
            # Mappatura delle colonne se presenti
            rename_map = {"index": "Ticker", "beta": "Beta Fallback", "shock_pct": "Shock Effettivo %", "loss_eur": "Perdita Stimata (€)", "is_historical": "Dato Storico Reale"}
            df_det.rename(columns={k: v for k, v in rename_map.items() if k in df_det.columns}, inplace=True)
            
            df_det = df_det.sort_values(by="Perdita Stimata (€)", ascending=True) # Ascending perché le perdite sono negative
            
            col_t, col_c = st.columns([1, 1])
            with col_t:
                # Applica formattazioni per la tabella
                df_disp = df_det.copy()
                df_disp["Shock Effettivo %"] = df_disp["Shock Effettivo %"].apply(lambda x: f"{x:.2f}%")
                df_disp["Perdita Stimata (€)"] = df_disp["Perdita Stimata (€)"].apply(lambda x: f"€ {x:,.2f}")
                if "Dato Storico Reale" in df_disp.columns:
                    df_disp["Dato Storico Reale"] = df_disp["Dato Storico Reale"].apply(lambda x: "✅ Sì" if x else "❌ No (Beta)")
                st.dataframe(df_disp, use_container_width=True, hide_index=True)
                
            with col_c:
                # Grafico a barre orizzontali delle perdite
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

# ── Simulatore Custom di Stress Test (What-if) ───────────────────────────
st.divider()
st.markdown("### 🛠️ Simulatore di Stress Test Personalizzato (What-if)")
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

# Eseguiamo la simulazione dinamica
import plotly.graph_objects as go

port_beta = results["metrics"]["market_risk"].get("beta", 1.0)
if port_beta is None:
    port_beta = 1.0

port_shock_pct = port_beta * (benchmark_shock / 100)
port_loss_eur = port_shock_pct * portfolio_value

# Estraiamo i dettagli degli asset da uno degli scenari storici esistenti
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
    
    # Calcoliamo lo shock stimato dell'asset per lo scenario what-if
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

    # Waterfall per lo scenario What-If
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

# Tabella dettaglio dei singoli asset
st.markdown("#### Impatto Dettagliato per Singolo Asset (Simulato)")
df_sim_disp = df_sim.copy()
df_sim_disp = df_sim_disp.sort_values(by="Perdita Estimata (€)", ascending=True)

df_sim_disp["Peso %"] = df_sim_disp["Peso %"].apply(lambda x: f"{x:.2f}%")
df_sim_disp["Valore Corrente"] = df_sim_disp["Valore Corrente"].apply(lambda x: f"€ {x:,.2f}")
df_sim_disp["Beta"] = df_sim_disp["Beta"].apply(lambda x: f"{x:.2f}")
df_sim_disp["Shock Stimato %"] = df_sim_disp["Shock Stimato %"].apply(lambda x: f"{x:+.2f}%")
df_sim_disp["Perdita Estimata (€)"] = df_sim_disp["Perdita Estimata (€)"].apply(lambda x: f"€ {x:,.2f}")

st.dataframe(df_sim_disp, use_container_width=True, hide_index=True)

