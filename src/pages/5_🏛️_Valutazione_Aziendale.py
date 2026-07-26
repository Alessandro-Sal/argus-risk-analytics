import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, glossary_modal, fmt_pct, render_executive_badges

st.set_page_config(page_title="Valutazione Aziendale | ARGUS", page_icon="🏛️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
pos = results["positions"]

active_pos = pos[pos["qty_net"] > 0].copy()

st.title("🏛️ Valutazione Intrinseca & Fair Value")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Analisi dei fondamentali societari, target price dei mercati (Consensus) e simulazioni di private equity (IRR & TVPI).")
col_head1, col_head2 = st.columns([3.5, 1])
with col_head1:
    render_executive_badges(results["metrics"])
with col_head2:
    glossary_modal("Cos'è la Valutazione Aziendale?",
    "Valutazione rigorosa basata sul <b>Target Price degli Analisti (Consensus)</b> e sul <b>PEG Ratio</b> per emettere un verdetto: l'asset è Sottovalutato o Sopravvalutato rispetto ai fondamentali?", button_label="💡 Come funziona?")

st.divider()

if active_pos.empty:
    st.info("Nessuna posizione aperta in portafoglio.")
    st.stop()

# Estrazione colonne e calcolo dell'Upside / Giudizio
fund_cols = ["ticker", "name", "asset_class", "weight_pct", "last_price", 
             "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]
df_fund = active_pos[[c for c in fund_cols if c in active_pos.columns]].copy()

# Pulizia numerica
for col in ["last_price", "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]:
    if col in df_fund.columns:
        df_fund[col] = pd.to_numeric(df_fund[col], errors='coerce')

# Logica di Valutazione (Verdetto)
def get_verdict(row):
    last = row.get("last_price")
    target = row.get("target_mean_price")
    peg = row.get("peg_ratio")
    
    if pd.isna(last) or pd.isna(target):
        return "⚪ N/A"
        
    upside = (target / last) - 1
    
    if pd.notna(peg) and peg > 2.5 and upside < 0.05:
        return "🔴 Sopravvalutata (PEG Alto)"
    
    if upside > 0.10:
        return "🟢 Sottovalutata"
    elif upside < -0.05:
        return "🔴 Sopravvalutata"
    else:
        return "🟡 Fair Value"

df_fund["Upside %"] = np.where(
    (df_fund["target_mean_price"].notna()) & (df_fund["last_price"].notna()) & (df_fund["last_price"] > 0),
    (df_fund["target_mean_price"] / df_fund["last_price"]) - 1,
    np.nan
)

df_fund["Verdetto"] = df_fund.apply(get_verdict, axis=1)
df_valued = df_fund[df_fund["Verdetto"] != "⚪ N/A"]

if df_valued.empty:
    st.warning("⚠️ Impossibile calcolare il Fair Value: i dati degli Analisti e il Target Price non sono disponibili per gli asset attuali.")
    st.stop()

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ ─────────────────────
tab1, tab2, tab3 = st.tabs([
    "🏛️ Fair Value & Consensus Analisti",
    "📈 Potenziale di Rialzo (Upside/Downside)",
    "💼 Private Equity & Waterfall Simulator"
])

# ── TAB 1: FAIR VALUE & CONSENSUS ANALISTI ─────────────────────
with tab1:
    st.markdown("#### Riepilogo Giudizi di Mercato")
    col1, col2, col3 = st.columns(3)

    n_under = len(df_valued[df_valued["Verdetto"].str.contains("Sottovalutata")])
    n_fair  = len(df_valued[df_valued["Verdetto"].str.contains("Fair Value")])
    n_over  = len(df_valued[df_valued["Verdetto"].str.contains("Sopravvalutata")])

    with col1:
        metric_card(
            "Sottovalutate (Buy)",
            str(n_under),
            "Asset a sconto vs target price",
            True,
            help_text="<b>Cosa significa:</b> Azioni che il mercato sta prezzando al di sotto del loro reale potenziale stimato.\n\n<b>A cosa serve:</b> Filtra rapidamente il portafoglio per isolare i 'veri affari'. Segnala su quali strumenti potresti considerare di aumentare la posizione per sfruttare il potenziale di apprezzamento non ancora espresso dal mercato.\n\n<b>Come si calcola:</b> Si contano gli asset per i quali il Target Price Medio a 12 mesi degli analisti istituzionali è superiore al prezzo attuale di mercato di almeno il 10%, purché abbiano multipli di valutazione (es. PEG Ratio) ragionevoli."
        )
    with col2:
        metric_card(
            "Fairly Valued (Hold)",
            str(n_fair),
            "Asset in linea col fair value",
            True,
            help_text="<b>Cosa significa:</b> Azioni il cui prezzo attuale di borsa riflette già perfettamente le stime di utili futuri e il potenziale dell'azienda.\n\n<b>A cosa serve:</b> Indica quegli asset che stanno facendo il loro dovere, prezzati in equilibrio. Solitamente non c'è urgenza né di vendere (perché l'azienda è sana e prezzata giusta) né di comprare aggressivamente (non c'è 'sconto').\n\n<b>Come si calcola:</b> Si contano gli asset la cui distanza tra il Target Price e il Prezzo Attuale oscilla in una fascia di normalità compresa tra il -5% e il +10%."
        )
    with col3:
        metric_card(
            "Sopravvalutate (Sell)",
            str(n_over),
            "Asset a premio vs target price",
            False,
            help_text="<b>Cosa significa:</b> Azioni scambiate a un prezzo eccessivamente alto ('a premio') rispetto ai fondamentali reali dell'azienda (utili e stime).\n\n<b>A cosa serve:</b> È un alert cruciale per il rischio di bolle o per le 'prese di profitto'. Ti suggerisce che l'asset potrebbe aver corso troppo e che il mercato prima o poi potrebbe correggere il prezzo al ribasso per allinearlo alla realtà contabile.\n\n<b>Come si calcola:</b> Si contano gli asset con un Upside negativo (ovvero il Target Price è inferiore di oltre il 5% rispetto al prezzo attuale) oppure che mostrano un PEG Ratio follemente alto (> 2.5), indice di euforia irrazionale."
        )

    st.divider()

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.markdown("#### Tabella Fair Value & Target Price")
        
        df_display = df_valued[["ticker", "Verdetto", "last_price", "target_mean_price", "Upside %", "peg_ratio", "trailing_pe"]].copy()
        df_display.rename(columns={
            "ticker": "Asset",
            "last_price": "Prezzo Attuale",
            "target_mean_price": "Target Price (Analisti)",
            "peg_ratio": "PEG Ratio",
            "trailing_pe": "P/E Ratio"
        }, inplace=True)
        
        df_display["Prezzo Attuale"] = df_display["Prezzo Attuale"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["Target Price (Analisti)"] = df_display["Target Price (Analisti)"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["Upside %"] = df_display["Upside %"].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "N/A")
        df_display["PEG Ratio"] = df_display["PEG Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["P/E Ratio"] = df_display["P/E Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

    with col_b:
        glossary_modal("📚 Glossario Metriche di Valutazione", """
    <ul style="margin-top:0; padding-left:20px;">
        <li style="margin-bottom:12px;"><b>Target Price (Prezzo Obiettivo):</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> È il prezzo futuro a cui gli analisti finanziari ritengono che l'azione debba tendere nei successivi 12 mesi.</li>
                <li><b>A cosa serve:</b> È la bussola del mercato. Ti permette di capire se i grandi player istituzionali vedono l'asset in salita (opportunità) o in stallo.</li>
            </ul>
        </li>
        <li style="margin-bottom:12px;"><b>Upside / Downside %:</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> È il potenziale di guadagno (Upside) o perdita (Downside) necessario affinché il prezzo attuale raggiunga il Target Price.</li>
            </ul>
        </li>
        <li><b>PEG Ratio (Price/Earnings-to-Growth):</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> Mette in relazione il prezzo pagato per gli utili con la velocità a cui questi utili stanno crescendo.</li>
            </ul>
        </li>
    </ul>
    """, button_label="📖 Glossario Metriche")
        
        verdict_counts = df_valued["Verdetto"].value_counts().reset_index()
        verdict_counts.columns = ["Verdetto", "Conteggio"]
        
        color_map = {
            "🟢 Sottovalutata": "#00ff99",
            "🟡 Fair Value": "#ffcc00",
            "🔴 Sopravvalutata (PEG Alto)": "#ff3333",
            "🔴 Sopravvalutata": "#ff3333"
        }
        
        st.markdown("**Distribuzione Valutazioni**")
        fig = px.pie(
            verdict_counts, values="Conteggio", names="Verdetto", hole=0.6,
            color="Verdetto", color_discrete_map=color_map
        )
        fig.update_traces(
            textposition='inside', textinfo='percent+label', showlegend=False,
            hovertemplate="<b>Verdetto: %{label}</b><br>Numero Asset: %{value}<extra></extra>"
        )
        fig.update_layout(
            template="plotly_dark", height=300,
            margin=dict(l=0, r=0, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: POTENZIALE DI RIALZO ──────────────────────────────
with tab2:
    st.markdown("#### Potenziale di Rialzo (Upside/Downside) degli Asset")
    df_upside = df_valued.dropna(subset=["Upside %"]).sort_values("Upside %", ascending=True)

    if not df_upside.empty:
        df_upside["Colore"] = np.where(df_upside["Upside %"] > 0, "#00ff99", "#ff3333")
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_upside["Upside %"] * 100,
            y=df_upside["ticker"],
            orientation='h',
            marker_color=df_upside["Colore"],
            text=df_upside["Upside %"].apply(lambda x: f"{x*100:+.1f}%"),
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Distanza dal Fair Value: %{x:+.1f}%<extra></extra>"
        ))
        
        fig_bar.update_layout(
            template="plotly_dark", height=420,
            xaxis_title="Distanza dal Fair Value degli Analisti (%)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 3: PRIVATE EQUITY SIMULATOR ───────────────────────────
with tab3:
    st.markdown("#### 💼 Private Equity & Private Markets Cash Flow Simulator")
    st.caption("Simulatore dei flussi finanziari di Private Equity: calcolo del Net IRR, TVPI / MOIC, DPI, RVPI e Carried Interest Waterfall Allocation")

    glossary_modal("ℹ️ Guida alle Metriche del Private Equity (TVPI, DPI, IRR)", """
    <p><b>1. TVPI / MOIC (Total Value to Paid-In / Multiple on Invested Capital):</b><br>
    Esprime il moltiplicatore totale di valore generato dal fondo di Private Equity rispetto al capitale richiamato (Capital Calls).</p>

    <p><b>2. DPI (Distributed to Paid-In):</b><br>
    La porzione di capitale e plusvalenze effettivamente già distribuita in cassa agli investitori (Limited Partners).</p>

    <p><b>3. RVPI (Residual Value to Paid-In):</b><br>
    Il valore residuo stimato delle aziende ancora in portafoglio (Net Asset Value - NAV) rispetto al capitale richiamato.</p>

    <p><b>4. Carried Interest & Hurdle Rate Waterfall:</b><br>
    La quota dei profitti (tipicamente il 20%) spettante al General Partner (GP) dopo che gli investitori (LP) hanno ottenuto la restituzione del capitale ed il rendimento minimo garantito (Hurdle Rate, tipicamente 8%).</p>
    """, button_label="💡 Come funziona il Simulatore Private Equity?")

    pe_c1, pe_c2, pe_c3 = st.columns(3)
    with pe_c1:
        cap_calls = st.number_input("Capital Calls (€)", min_value=10000.0, value=1000000.0, step=50000.0)
    with pe_c2:
        distribs = st.number_input("Distributions (€)", min_value=0.0, value=1500000.0, step=50000.0)
    with pe_c3:
        nav_val = st.number_input("NAV Residuo Partecipazioni (€)", min_value=0.0, value=1000000.0, step=50000.0)

    from core.risk_engine import compute_private_equity_waterfall
    pe_res = compute_private_equity_waterfall(cap_calls, distribs, nav_val, hurdle_rate=0.08, carried_interest=0.20)

    if pe_res:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("TVPI / MOIC", f"{pe_res['tvpi_moic']:.2f}x")
        kpi2.metric("DPI (Cassa Distribuita)", f"{pe_res['dpi']:.2f}x")
        kpi3.metric("RVPI (NAV Residuo)", f"{pe_res['rvpi']:.2f}x")
        kpi4.metric("Carried Interest GP (€)", f"€ {pe_res['gp_carried_interest']:,.2f}")
        
        fig_wf = go.Figure(go.Waterfall(
            name="Waterfall PE", orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Capital Calls (LP)", "Distributions (Cassa)", "NAV Residuo", "Valore Creato Netto"],
            text=[f"€ {cap_calls:,.0f}", f"€ {distribs:,.0f}", f"€ {nav_val:,.0f}", f"€ {pe_res['total_gain']:,.0f}"],
            y=[-cap_calls, distribs, nav_val, pe_res['total_gain']],
            connector={"line":{"color":"rgba(255,255,255,0.2)"}},
            decreasing={"marker":{"color":"#ff4b4b"}},
            increasing={"marker":{"color":"#00cc96"}},
            totals={"marker":{"color":"#ff9900"}}
        ))
        fig_wf.update_layout(height=350, yaxis_title="Flussi di Cassa (€)")
        from core.ui_utils import apply_plotly_theme
        apply_plotly_theme(fig_wf)
        st.plotly_chart(fig_wf, use_container_width=True)
