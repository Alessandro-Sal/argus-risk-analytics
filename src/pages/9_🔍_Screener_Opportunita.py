# ============================================================
# src/pages/9_🔍_Screener_Opportunita.py
# ARGUS | Risk Analytics Platform
# Multi-Factor Market Screener & Pre-Trade Impact Simulator
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

import importlib
import core.ui_utils as ui_utils
import core.risk_engine as risk_engine
import core.screener_engine as screener_engine
importlib.reload(ui_utils)
importlib.reload(risk_engine)
importlib.reload(screener_engine)

from core.sidebar import render_sidebar
from core.ui_utils import (
    inject_custom_css,
    metric_card,
    glossary_modal,
    apply_plotly_theme,
    render_segmented_tabs,
    render_command_bar,
    ensure_risk_bundle_loaded,
    render_sandbox_banner
)
from core.pdf_generator import generate_asset_factsheet_pdf

from core.screener_engine import (
    MARKET_UNIVERSES,
    fetch_screener_universe_data,
    apply_strategy_preset,
    simulate_pre_trade_impact,
    compute_market_and_watchlist_alerts
)

st.set_page_config(
    page_title="ARGUS · Market Screener & Pre-Trade",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()
render_sidebar()
render_command_bar()

# Inizializzazione session_state per Watchlist e Screener Data
if "screener_watchlist" not in st.session_state:
    st.session_state.screener_watchlist = []
if "cached_screener_df" not in st.session_state:
    st.session_state.cached_screener_df = pd.DataFrame()
if "last_screened_universe" not in st.session_state:
    st.session_state.last_screened_universe = None

# Recupero posizioni e benchmark di portafoglio da session_state o Sandbox
results, has_real_portfolio = ensure_risk_bundle_loaded()
pos = results.get("positions", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()

if not has_real_portfolio:
    render_sandbox_banner()

if isinstance(pos, pd.DataFrame) and not pos.empty:
    if "qty_net" in pos.columns:
        active_positions = pos[pos["qty_net"] > 0].copy()
    elif "weight_pct" in pos.columns:
        active_positions = pos[pos["weight_pct"] > 0].copy()
    else:
        active_positions = pos.copy()
else:
    active_positions = pd.DataFrame()

benchmark_ticker = st.session_state.get("benchmark", "SPY")
portfolio_name = st.session_state.get("portfolio_name", "Portafoglio Attivo")

# ── HEADER ISTITUZIONALE & MODALE A 5 PUNTI ──────────────────
col_head1, col_head2 = st.columns([3.2, 1.1])
with col_head1:
    st.title("🔍 Screener Quantitativo & Pre-Trade Simulator")
    st.caption("Asset Discovery Multi-Fattoriale (Valutazione, Qualità Contabile, Rischio, Momentum) e Simulatore What-If di Impatto Pre-Trade su Portafoglio Reale.")
with col_head2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("💡 Come funziona lo Screener Istituzionale & Pre-Trade Simulator", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è lo Screener & Pre-Trade Simulator</div>
  <div>È il motore di <b>Asset Discovery quantitativo</b> di ARGUS. Permette di esplorare universi azionari globali (S&P 500, EuroStoxx 50, FTSE MIB, Dividend Champions) attraverso filtri multi-fattoriali e di <b>simulare l'impatto sul portafoglio prima di eseguire qualsiasi operazione a mercato</b>.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Come si calcola</div>
  <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; margin: 6px 0; font-family: monospace; color: #e6edf3;">
    <b>ARGUS Composite Score:</b><br>
    Score = 0.25 &times; Valutazione + 0.25 &times; Qualità + 0.25 &times; Rischio + 0.25 &times; Momentum<br><br>
    <b>Pre-Trade Re-Weighting:</b><br>
    w_new = (1 - w_cand) &times; w_old + w_cand &times; e_cand<br><br>
    <b>Diversification Ratio (Choueifaty):</b><br>
    DR = (&Sigma; w_i &times; &sigma;_i) / &sigma;_portafoglio
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Consente al gestore/investitore di:
  <ul style="margin: 4px 0 0 16px; padding: 0;">
    <li>Identificare titoli sottovalutati ad alto potenziale di rialzo (Target Price Consensus).</li>
    <li>Filtrare aziende con bilanci solidi (Altman Z-Score &ge; 2.9, Piotroski &ge; 7).</li>
    <li>Testare se l'aggiunta di una posizione riduce la volatilità complessiva (&Delta;&sigma; &lt; 0) o accresce l'indice di Sharpe (&Delta;Sharpe &gt; 0).</li>
  </ul>
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Sfrutta lo <b>Scudo Multi-Tier Cache Shield</b> (L1 RAM + L2 SQLite 24h) per processare istantaneamente bilanci, consensus analisti, indicatori tecnici (RSI, SMA 200) e matrici di covarianza su serie storiche giornaliere.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo / Interpretazione</div>
  <div>
    • <b>Score &ge; 75:</b> Opportunità ad elevata attrattività complessiva (Forte asimmetria rischio/rendimento).<br>
    • <b>&Delta;Sharpe &gt; +0.03:</b> L'inserimento dell'asset migliora l'efficienza globale del portafoglio.<br>
    • <b>&Delta;Volatilità &lt; 0%:</b> L'asset funge da stabilizzatore decorrelato.
  </div>
</div>

</div>
""", button_label="💡 Come funziona lo Screener")

st.divider()

# ── CONTROLLI UNIVERSO DI SCREENING ───────────────────────────
col_u1, col_u2, col_u3 = st.columns([2.2, 2.0, 1.2])

with col_u1:
    univ_choice = st.selectbox(
        "🌐 Seleziona Universo di Mercato",
        list(MARKET_UNIVERSES.keys()) + ["✍️ Lista Personalizzata (Custom Tickers)..."],
        index=0,
        help="Scegli un indice globale pre-configurato o inserisci i tuoi ticker preferiti."
    )

custom_tickers_input = ""
if univ_choice == "✍️ Lista Personalizzata (Custom Tickers)...":
    with col_u2:
        custom_tickers_input = st.text_input(
            "Inserisci Ticker separati da virgola (es. AAPL, NVDA, RACE.MI, ASML, JNJ)",
            value="AAPL, NVDA, MSFT, RACE.MI, ASML, JNJ, MC.PA, ENEL.MI"
        )
    tickers_to_screen = [t.strip().upper() for t in custom_tickers_input.split(",") if t.strip()]
else:
    tickers_to_screen = MARKET_UNIVERSES[univ_choice]["tickers"]
    with col_u2:
        st.caption(f"ℹ️ **{univ_choice}**: {MARKET_UNIVERSES[univ_choice]['description']}")

with col_u3:
    st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
    refresh_btn = st.button("🚀 Esegui Screening", type="primary", use_container_width=True)

# Esecuzione / Caricamento dati
need_fetch = refresh_btn or st.session_state.cached_screener_df.empty or st.session_state.last_screened_universe != univ_choice

if need_fetch and tickers_to_screen:
    with st.spinner("Estrazione e calcolo metriche multi-fattoriali in corso (Cache Shield protetto)..."):
        df_screened = fetch_screener_universe_data(
            tickers=tickers_to_screen,
            benchmark_ticker=benchmark_ticker
        )
        st.session_state.cached_screener_df = df_screened
        st.session_state.last_screened_universe = univ_choice

df_raw = st.session_state.cached_screener_df

if df_raw.empty:
    st.warning("⚠️ Nessun dato disponibile. Clicca su '🚀 Esegui Screening' per caricare le analisi.")
    st.stop()

# ── KPI METRICHE TOP ROW ──────────────────────────────────────
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    metric_card(
        "Titoli Analizzati",
        str(len(df_raw)),
        f"Universo: {univ_choice.split('(')[0].strip()}",
        True,
        help_text="Numero totale di società valutate con metriche fondamentali e tecniche."
    )
with col_m2:
    avg_score = df_raw["argus_score"].mean() if "argus_score" in df_raw.columns else 50.0
    metric_card(
        "Score Medio ARGUS",
        f"{avg_score:.1f} / 100",
        "Punteggio medio dell'universo",
        avg_score >= 60,
        help_text="Punteggio composito aggregato basato su Valutazione, Qualità, Rischio e Momentum."
    )
with col_m3:
    n_undervalued = len(df_raw[df_raw["upside_pct"] > 10.0]) if "upside_pct" in df_raw.columns else 0
    metric_card(
        "Opportunità Sottovalutate",
        str(n_undervalued),
        "Upside Consensus > +10%",
        True,
        help_text="Società con potenziale di rialzo superiore al 10% secondo gli analisti istituzionali."
    )
with col_m4:
    best_tk = df_raw.iloc[0]["ticker"] if not df_raw.empty else "N/A"
    best_score = df_raw.iloc[0]["argus_score"] if not df_raw.empty else 0.0
    metric_card(
        "Top Ranked Candidate",
        f"{best_tk} ({best_score:.0f} pts)",
        "Massimo punteggio composito",
        True,
        help_text="Il titolo dell'universo con il profilo quantitativo complessivamente più favorevole."
    )

st.divider()

# ── STRUTTURA DELLE TAB AD ALTA PERFORMANCE CON LAZY LOADING ───
active_screener_tab = render_segmented_tabs([
    "🔍 Screener Multi-Fattoriale & Archetipi",
    "🧪 Pre-Trade Portfolio Impact Simulator",
    "📊 Radar Comparativo Multi-Titolo",
    "💾 Watchlist & Segnali Operativi"
], key="screener_segmented_subtab")

# ── TAB 1: SCREENER MULTI-FATTORIALE ───────────────────────────
if active_screener_tab == "🔍 Screener Multi-Fattoriale & Archetipi":
    st.markdown("#### 🎯 Selezione Strategica & Filtri Quantitativi")
    
    # Archetipi Istituzionali
    preset_col, reset_col = st.columns([4, 1])
    with preset_col:
        preset_choice = st.radio(
            "⚡ Preset Strategico Istituzionale (One-Click Archetype):",
            [
                "Tutti i Titoli",
                "🚀 GARP (Growth at Reasonable Price)",
                "🛡️ Dividend Fortress (Alto Yield & Safe Z-Score)",
                "💎 Deep Value (Graham Margin of Safety)",
                "🌐 Low Volatility & High Sharpe",
                "⚡ Momentum & Trend Breakout"
            ],
            horizontal=True
        )
    with reset_col:
        st.markdown('<div style="margin-top: 26px;"></div>', unsafe_allow_html=True)
        show_all = st.button("🔄 Reset Filtri", use_container_width=True)

    # Mappatura preset
    preset_key = "all"
    if "GARP" in preset_choice: preset_key = "garp"
    elif "Dividend Fortress" in preset_choice: preset_key = "dividend_fortress"
    elif "Deep Value" in preset_choice: preset_key = "deep_value"
    elif "Low Volatility" in preset_choice: preset_key = "low_volatility"
    elif "Momentum" in preset_choice: preset_key = "momentum_breakout"

    df_filtered = apply_strategy_preset(df_raw, preset_key) if preset_key != "all" else df_raw.copy()

    # Pannello Espandibile di Micro-Filtri Manuali
    with st.expander("🛠️ Filtri Avanzati di Precisione (Personalizza Soglie Fondamentali & Tecniche)", expanded=False):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        
        with f_col1:
            max_pe = st.slider("P/E Massimo", 5.0, 100.0, 45.0, step=1.0)
            max_peg = st.slider("PEG Ratio Massimo", 0.5, 4.0, 2.5, step=0.1)
        with f_col2:
            min_roe = st.slider("ROE Minimo (%)", 0.0, 40.0, 5.0, step=1.0)
            min_yield = st.slider("Dividend Yield Minimo (%)", 0.0, 10.0, 0.0, step=0.5)
        with f_col3:
            min_upside = st.slider("Upside Minimo Target Price (%)", -20.0, 50.0, 0.0, step=5.0)
            min_z = st.slider("Altman Z-Score Minimo", 1.0, 5.0, 1.8, step=0.2)
        with f_col4:
            max_vol = st.slider("Volatilità Annua Massima (%)", 10.0, 60.0, 45.0, step=1.0)
            rsi_range = st.slider("Range RSI (14)", 10, 90, (20, 80))

        # Applicazione micro-filtri
        df_filtered = df_filtered[
            (df_filtered["trailing_pe"].isna() | (df_filtered["trailing_pe"] <= max_pe)) &
            (df_filtered["peg_ratio"].isna() | (df_filtered["peg_ratio"] <= max_peg)) &
            (df_filtered["roe_pct"].isna() | (df_filtered["roe_pct"] >= min_roe)) &
            (df_filtered["dividend_yield_pct"] >= min_yield) &
            (df_filtered["upside_pct"].isna() | (df_filtered["upside_pct"] >= min_upside)) &
            (df_filtered["altman_z_score"].isna() | (df_filtered["altman_z_score"] >= min_z)) &
            (df_filtered["volatility_ann_pct"].isna() | (df_filtered["volatility_ann_pct"] <= max_vol)) &
            (df_filtered["rsi_14"].between(rsi_range[0], rsi_range[1]))
        ]

    st.markdown(f"**Risultati dello Screening:** Trovate **{len(df_filtered)}** opportunità su {len(df_raw)} titoli esaminati.")

    # Dataframe di visualizzazione principale
    cols_display = [
        "ticker", "name", "sector", "last_price", "upside_pct", "trailing_pe", "peg_ratio",
        "dividend_yield_pct", "roe_pct", "altman_z_score", "volatility_ann_pct", "beta", "rsi_14", "argus_score"
    ]
    df_table = df_filtered[[c for c in cols_display if c in df_filtered.columns]].copy()
    df_table.rename(columns={
        "ticker": "Ticker",
        "name": "Azienda",
        "sector": "Settore",
        "last_price": "Prezzo",
        "upside_pct": "Upside Consensus %",
        "trailing_pe": "P/E Ratio",
        "peg_ratio": "PEG Ratio",
        "dividend_yield_pct": "Div. Yield %",
        "roe_pct": "ROE %",
        "altman_z_score": "Altman Z",
        "volatility_ann_pct": "Vol. Annua %",
        "beta": "Beta",
        "rsi_14": "RSI (14)",
        "argus_score": "ARGUS Score"
    }, inplace=True)

    col_sc_h1, col_sc_h2 = st.columns([3.5, 0.9])
    with col_sc_h2:
        csv_sc = df_table.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica CSV", data=csv_sc, file_name="screener_opportunita.csv", mime="text/csv", use_container_width=True)

    scr_cfg = {
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Azienda": st.column_config.TextColumn("Azienda", width="medium"),
        "Settore": st.column_config.TextColumn("Settore", width="small"),
        "Prezzo": st.column_config.NumberColumn("Prezzo (€)", format="€ %.2f"),
        "Upside Consensus %": st.column_config.NumberColumn("Upside Consensus", format="%+.2f%%"),
        "P/E Ratio": st.column_config.NumberColumn("P/E Ratio", format="%.1f"),
        "PEG Ratio": st.column_config.NumberColumn("PEG Ratio", format="%.2f"),
        "Div. Yield %": st.column_config.ProgressColumn("Div. Yield", format="%.2f%%", min_value=0.0, max_value=15.0),
        "ROE %": st.column_config.ProgressColumn("ROE", format="%.1f%%", min_value=0.0, max_value=50.0),
        "Altman Z": st.column_config.NumberColumn("Altman Z", format="%.2f"),
        "Vol. Annua %": st.column_config.NumberColumn("Vol. Annua", format="%.1f%%"),
        "Beta": st.column_config.NumberColumn("Beta", format="%.2f"),
        "RSI (14)": st.column_config.ProgressColumn("RSI (14)", format="%.1f", min_value=0.0, max_value=100.0),
        "ARGUS Score": st.column_config.ProgressColumn("ARGUS Score", format="%.1f / 100", min_value=0.0, max_value=100.0)
    }

    st.dataframe(
        df_table,
        column_config=scr_cfg,
        use_container_width=True,
        hide_index=True,
        height=380
    )

    # Azione rapida: Aggiunta a Watchlist
    col_w_add1, col_w_add2 = st.columns([3, 1])
    with col_w_add1:
        selected_to_watch = st.multiselect(
            "➕ Seleziona titoli da salvare nella Watchlist di sessione:",
            options=df_filtered["ticker"].tolist(),
            default=[]
        )
    with col_w_add2:
        st.markdown('<div style="margin-top: 26px;"></div>', unsafe_allow_html=True)
        if st.button("💾 Salva in Watchlist", use_container_width=True):
            for t in selected_to_watch:
                if t not in st.session_state.screener_watchlist:
                    st.session_state.screener_watchlist.append(t)
            st.success(f"Aggiunti {len(selected_to_watch)} titoli alla Watchlist!")

    # Grafico Interattivo: P/E vs Upside % con bolle colorate per Score ARGUS
    if not df_filtered.empty and "trailing_pe" in df_filtered.columns and "upside_pct" in df_filtered.columns:
        st.markdown("#### 🗺️ Mappa di Valutazione: Multiplo P/E vs Potenziale di Rialzo (Upside %)")
        df_plot = df_filtered.dropna(subset=["trailing_pe", "upside_pct"]).copy()
        if not df_plot.empty:
            customdata = np.stack((
                df_plot["name"].fillna(df_plot["ticker"]),
                df_plot["ticker"],
                df_plot["sector"].fillna("N/D"),
                df_plot["trailing_pe"].fillna(0.0),
                df_plot["upside_pct"].fillna(0.0),
                df_plot["argus_score"].fillna(0.0),
                df_plot["dividend_yield_pct"].fillna(0.0) if "dividend_yield_pct" in df_plot.columns else np.zeros(len(df_plot)),
                df_plot["roe_pct"].fillna(0.0) if "roe_pct" in df_plot.columns else np.zeros(len(df_plot)),
                df_plot["altman_z_score"].fillna(0.0) if "altman_z_score" in df_plot.columns else np.zeros(len(df_plot)),
                df_plot["piotroski_score"].fillna(0) if "piotroski_score" in df_plot.columns else np.zeros(len(df_plot))
            ), axis=-1)

            hover_template = (
                "<b><span style='font-size:13.5px;'>%{customdata[0]}</span></b> (<span style='color:#58a6ff;'>%{customdata[1]}</span>)<br>"
                "<span style='color:#8b949e;'>Settore:</span> <b>%{customdata[2]}</b><br>"
                "<span style='color:rgba(255,255,255,0.2);'>━━━━━━━━━━━━━━━━━━━━</span><br>"
                "• <b>Multiplo P/E Trailing:</b> %{customdata[3]:.1f}x<br>"
                "• <b>Upside Consensus:</b> %{customdata[4]:+.1f}%<br>"
                "• <b>ARGUS Score:</b> <span style='color:#FFD700; font-weight:700;'>%{customdata[5]:.1f} / 100</span><br>"
                "• <b>Dividend Yield:</b> %{customdata[6]:.2f}%<br>"
                "• <b>ROE:</b> %{customdata[7]:.1f}%<br>"
                "• <b>Altman Z-Score:</b> %{customdata[8]:.2f}<br>"
                "• <b>Piotroski F-Score:</b> %{customdata[9]} / 9"
                "<extra></extra>"
            )

            fig_map = go.Figure()
            fig_map.add_trace(go.Scatter(
                x=df_plot["trailing_pe"],
                y=df_plot["upside_pct"],
                mode="markers+text",
                text=df_plot["ticker"],
                textposition="top center",
                textfont=dict(size=11, color="#ffffff"),
                customdata=customdata,
                hovertemplate=hover_template,
                marker=dict(
                    size=df_plot["argus_score"] / 2.3 + 9,
                    color=df_plot["argus_score"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(
                        title=dict(text="ARGUS Score", font=dict(color="#ffffff", size=12)),
                        tickfont=dict(color="#c9d1d9", size=10),
                        thickness=14,
                        len=0.85,
                        outlinewidth=0
                    ),
                    line=dict(width=1.2, color="rgba(255,255,255,0.4)")
                )
            ))

            fig_map.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.25)", annotation_text="Upside Neutro (0%)", annotation_position="bottom right")
            fig_map.add_vline(x=20, line_dash="dot", line_color="#58a6ff", annotation_text="Soglia P/E Benchmark (20x)", annotation_position="top right")

            fig_map.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=480,
                xaxis=dict(
                    title="Multiplo P/E Trailing (Valutazione)",
                    gridcolor="rgba(255,255,255,0.06)",
                    zerolinecolor="rgba(255,255,255,0.1)"
                ),
                yaxis=dict(
                    title="Potenziale di Rialzo Consensus (Upside %)",
                    gridcolor="rgba(255,255,255,0.06)",
                    zerolinecolor="rgba(255,255,255,0.1)"
                ),
                margin=dict(l=10, r=10, t=30, b=20)
            )
            apply_plotly_theme(fig_map)
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

# ── TAB 2: PRE-TRADE PORTFOLIO IMPACT SIMULATOR ────────────────
elif active_screener_tab == "🧪 Pre-Trade Portfolio Impact Simulator":
    col_pre_h1, col_pre_h2 = st.columns([3.2, 1.2])
    with col_pre_h1:
        st.markdown("#### 🧪 Simulatore di Impatto Pre-Trade (Pre-Trade Portfolio Impact)")
        st.caption("Valuta istantaneamente la variazione della frontiera di rischio del tuo portafoglio attuale qualora decidessi di acquistare un asset candidato.")
    with col_pre_h2:
        st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
        glossary_modal("Come funziona il Simulatore Pre-Trade & Handoff Quantitativo", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 1. Cos'è la Simulazione di Impatto Pre-Trade</div>
  <div>Permette al gestore di testare in ambiente protetto ("sandbox") l'effetto dell'acquisto di un nuovo titolo prima di immettere l'ordine a mercato. Il motore ricalcola istantaneamente:
    • <b>Rendimento Atteso:</b> Ritorno atteso ponderato post-allocazione.<br>
    • <b>Volatilità & Beta:</b> Effetto sulla rischiosità complessiva rispetto al benchmark.<br>
    • <b>Sharpe Ratio & Diversification Ratio:</b> Efficienza marginale e grado di decorrelazione della nuova allocazione.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔬 2. Cosa succede cliccando "Invia ad Asset Allocation"?</div>
  <div>
    Quando clicchi su <b>"Invia ad Asset Allocation (Pag. 3)"</b>:<br>
    1. Il ticker candidato (es. <code>GOOGL</code>) e il peso ipotizzato (es. <code>5.0%</code>) vengono registrati nello stato di sessione attivo.<br>
    2. Spostandoti su <b>Pagina 3 (Modelli Quantitativi)</b>, ARGUS rileva automaticamente il candidato e lo include nell'universo di calcolo della <b>Frontiera di Markowitz</b> con stimatore robusto <b>Ledoit-Wolf Shrinkage</b>.<br>
    3. Potrai così confrontare direttamente la Frontiera Efficiente attuale con quella allargata e visualizzare i nuovi pesi ottimali a <i>Max Sharpe</i> o <i>Minima Varianza</i>.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📄 3. Factsheet PDF Istituzionale</div>
  <div>Genera un dossier A4 vettoriale di due diligence contenente profilo societario, metriche di valutazione (P/E, PEG, EV/EBITDA), scorecard forense (Altman Z, Piotroski) e profili di rischio, pronto per comitati investimenti o audit.</div>
</div>

</div>
""", button_label="💡 Come funziona il Pre-Trade & Handoff?")

    if active_positions.empty:
        st.info("💡 Nessun portafoglio attivo rilevato in memoria. Verrà utilizzato un portafoglio bilanciato a scopo dimostrativo.")
        sample_port = pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "JNJ", "PG", "SPY"],
            "current_value": [25000.0, 25000.0, 20000.0, 15000.0, 15000.0],
            "weight_pct": [25.0, 25.0, 20.0, 15.0, 15.0]
        })
    else:
        sample_port = active_positions.copy()
        st.success(f"💼 **Portafoglio Attivo Rilevato**: `{portfolio_name}` ({len(active_positions)} posizioni aperte). La simulazione utilizzerà i tuoi pesi reali.")

    col_sim1, col_sim2, col_sim3 = st.columns([2, 2, 1.2])
    with col_sim1:
        cand_options = df_raw["ticker"].tolist()
        cand_ticker = st.selectbox("Seleziona Titolo Candidato dall'Universo:", cand_options, index=0)
    with col_sim2:
        cand_weight = st.slider("Allocazione Ipotetica nel Portafoglio (%)", min_value=1.0, max_value=30.0, value=5.0, step=0.5)
    with col_sim3:
        st.markdown('<div style="margin-top: 24px;"></div>', unsafe_allow_html=True)
        run_sim = st.button("⚡ Calcola Impatto", type="primary", use_container_width=True)

    # Esecuzione Simulazione Pre-Trade
    with st.spinner(f"Simulazione impatto inserimento {cand_ticker} ({cand_weight}%)..."):
        sim_res = simulate_pre_trade_impact(
            current_positions_df=sample_port,
            candidate_ticker=cand_ticker,
            candidate_weight_pct=cand_weight,
            benchmark_ticker=benchmark_ticker
        )

    if sim_res["valid"]:
        st.markdown(f"### Verdetto Quantitativo: {sim_res['verdict']}")
        st.caption(f"Correlazione dell'asset candidato **{cand_ticker}** con il portafoglio attuale: **{sim_res['correlation_with_portfolio']:.2f}**")

        # KPI Delta Comparison Cards
        kpi_cols = st.columns(len(sim_res["metrics_comparison"]))
        for i, (metric_name, data) in enumerate(sim_res["metrics_comparison"].items()):
            with kpi_cols[i]:
                fmt = data.get("format", "{:.2f}")
                val_after = fmt.format(data["after"])
                val_before = fmt.format(data["before"])
                delta_num = data["delta"]
                delta_str = f"{delta_num:+.2f}"
                
                # Se lower is better (es. volatilità), delta negativo è positivo (verde)
                lower_better = data.get("lower_better", False)
                is_positive = (delta_num < 0) if lower_better else (delta_num > 0)
                
                unit = "%" if ("%" in val_after and "%" not in delta_str) else ""
                metric_card(
                    metric_name,
                    val_after,
                    f"{delta_str}{unit} (ex {val_before})",
                    positive=is_positive,
                    help_text=f"• Valore Ante-Trade: **{val_before}**<br>• Valore Post-Trade (+{cand_weight}% {cand_ticker}): **{val_after}**<br>• Variazione Netta: **{delta_str}{unit}**"
                )

        st.divider()

        # ── RIGA 1: GRAFICO PESI DI PORTAFOGLIO A TUTTA LARGHEZZA ──
        st.markdown("#### ⚖️ Ripartizione Pesi di Portafoglio (Prima vs Dopo)")
        df_weights = sim_res["weights_table"]
        
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(
            name="Allocazione Attuale %",
            x=df_weights["Ticker"],
            y=df_weights["Peso Attuale %"],
            marker_color="rgba(139, 148, 158, 0.7)",
            hovertemplate="<b>%{x}</b><br>Peso Attuale: <b>%{y:.2f}%</b><extra></extra>"
        ))
        fig_w.add_trace(go.Bar(
            name=f"Nuova Allocazione (+{cand_weight}% {cand_ticker})",
            x=df_weights["Ticker"],
            y=df_weights["Nuovo Peso %"],
            marker_color="#58a6ff",
            hovertemplate="<b>%{x}</b><br>Nuovo Peso: <b>%{y:.2f}%</b><extra></extra>"
        ))
        fig_w.update_layout(
            barmode="group",
            template="plotly_dark",
            height=380,
            xaxis=dict(
                title="Asset di Portafoglio",
                tickfont=dict(size=12, color="#ffffff"),
                gridcolor="rgba(255,255,255,0.06)"
            ),
            yaxis=dict(
                title="Peso nel Portafoglio (%)",
                gridcolor="rgba(255,255,255,0.06)"
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color="#ffffff"),
                bgcolor="rgba(22, 27, 34, 0.6)",
                bordercolor="rgba(255,255,255,0.08)",
                borderwidth=1
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=35, b=25)
        )
        apply_plotly_theme(fig_w)
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # ── RIGA 2: TABELLA RIBILANCIAMENTO PRE-TRADE (A TUTTA LARGHEZZA) ──
        st.markdown("#### 📋 Tabella Ribilanciamento Pre-Trade")
        df_table_weights = pd.DataFrame({
            "Ticker": df_weights["Ticker"],
            "Peso Attuale": df_weights["Peso Attuale %"].map(lambda v: f"{v:.2f}%"),
            "Nuovo Peso": df_weights["Nuovo Peso %"].map(lambda v: f"{v:.2f}%"),
            "Delta Allocazione": df_weights["Delta Allocazione %"].map(lambda v: f"{v:+.2f}%")
        })

        st.dataframe(
            df_table_weights,
            use_container_width=True,
            hide_index=True,
            height=260
        )

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # ── RIGA 3: AZIONI OPERATIVE & HANDOFF (A TUTTA LARGHEZZA) ──
        col_act_h1, col_act_h2 = st.columns([3.8, 1.2])
        with col_act_h1:
            st.markdown(f"#### 🚀 Azioni Operative & Handoff | `{cand_ticker}`")
        with col_act_h2:
            st.markdown('<div style="margin-top: 2px;"></div>', unsafe_allow_html=True)
            glossary_modal("Guida alle Azioni Operative & Workflow Inter-Modulo", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔬 1. Handoff ad Asset Allocation (Pagina 3)</div>
  <div>Trasmette il titolo candidato e il peso simulato al motore di ottimizzazione di <b>Markowitz & Ledoit-Wolf Shrinkage</b> per calcolare la nuova Frontiera Efficiente allargata e i pesi a Massimo Sharpe / Minima Varianza.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📈 2. Cross-Check Analisi Tecnica & Volume Profile (Pagina 8)</div>
  <div>Apre istantaneamente il Cockpit Tecnico su questo specifico titolo per verificare livelli di supporto <b>POC (Point of Control)</b>, bande di Bollinger, Confluence Score e pattern candlestick.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🏛️ 3. Due Diligence Fondamentale & Bilanci 10-K (Pagina 5)</div>
  <div>Esamina i bilanci ufficiali dell'azienda, il Fair Value DCF, la solidità contabile (Altman Z-Score, Piotroski) e il rischio forense (Beneish M-Score).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⭐ 4. Gestione Watchlist di Sessione</div>
  <div>Inserisce il titolo tra gli asset sorvegliati speciali per ricevere notifiche e monitorarlo nella dashboard generale.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📄 5. Factsheet PDF Istituzionale</div>
  <div>Esporta un dossier A4 vettoriale completo di anagrafica, multipli e scorecard quantitativa ARGUS.</div>
</div>

</div>
""", button_label="📖 Guida Azioni")

        # Se lo stato handoff è attivo, mostra la card di conferma orizzontale
        cand_handoff_active = st.session_state.get("screener_candidate_to_optimize")
        is_active_handoff = (
            isinstance(cand_handoff_active, dict) and 
            cand_handoff_active.get("ticker") == cand_ticker
        )

        if is_active_handoff:
            col_h_status, col_h_link, col_h_cancel = st.columns([2.5, 2.0, 1.0])
            with col_h_status:
                st.markdown(f"""
                <div style="background: rgba(63, 185, 80, 0.12); border: 1px solid rgba(63, 185, 80, 0.35); border-radius: 8px; padding: 8px 14px;">
                    <div style="color: #3fb950; font-weight: 700; font-size: 13px;">✅ {cand_ticker} ({cand_weight}%) Trasmesso ad Asset Allocation</div>
                    <div style="color: #c9d1d9; font-size: 11.5px;">Incluso nei modelli Ledoit-Wolf & Markowitz su Pagina 3.</div>
                </div>
                """, unsafe_allow_html=True)
            with col_h_link:
                try:
                    st.page_link("pages/3_🔬_Modelli_Quantitativi.py", label="➡️ Apri Modelli Quantitativi (Pag. 3)", icon="🔬")
                except Exception:
                    pass
            with col_h_cancel:
                if st.button("❌ Rimuovi", use_container_width=True, help="Rimuovi simulazione da Pagina 3"):
                    del st.session_state["screener_candidate_to_optimize"]
                    st.rerun()
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

        # 5 Pulsanti operativi disposti su 5 colonne spaziose
        act_col1, act_col2, act_col3, act_col4, act_col5 = st.columns(5)
        
        with act_col1:
            if not is_active_handoff:
                if st.button("🔬 Invia ad Allocation", type="primary", use_container_width=True, help="Invia alla Pagina 3 per ricalcolare la Frontiera di Markowitz"):
                    st.session_state["screener_candidate_to_optimize"] = {
                        "ticker": cand_ticker,
                        "weight_pct": cand_weight
                    }
                    st.rerun()
            else:
                st.button("✅ Trasmesso a Pag. 3", disabled=True, use_container_width=True)

        with act_col2:
            if st.button(f"📈 Analisi Tecnica", use_container_width=True, help=f"Apri il Cockpit Tecnico su {cand_ticker}"):
                st.session_state["ta_target_ticker"] = cand_ticker
                st.switch_page("pages/8_📈_Analisi_Tecnica.py")

        with act_col3:
            if st.button(f"🏛️ Bilanci 10-K", use_container_width=True, help=f"Apri la Valutazione Fondamentale su {cand_ticker}"):
                st.session_state["fund_target_ticker"] = cand_ticker
                st.switch_page("pages/5_🏛️_Valutazione_Aziendale.py")

        with act_col4:
            is_in_watch = cand_ticker in st.session_state.get("screener_watchlist", [])
            if is_in_watch:
                if st.button("⭐ In Watchlist", use_container_width=True, help=f"Rimuovi {cand_ticker} dalla Watchlist"):
                    st.session_state.screener_watchlist.remove(cand_ticker)
                    st.rerun()
            else:
                if st.button("☆ + Watchlist", use_container_width=True, help=f"Aggiungi {cand_ticker} alla Watchlist"):
                    st.session_state.screener_watchlist.append(cand_ticker)
                    st.rerun()

        with act_col5:
            cand_row = df_raw[df_raw["ticker"] == cand_ticker]
            if not cand_row.empty:
                pdf_bytes = generate_asset_factsheet_pdf(cand_row.iloc[0].to_dict())
                st.download_button(
                    label="📄 Factsheet PDF",
                    data=pdf_bytes,
                    file_name=f"ARGUS_Factsheet_{cand_ticker}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    else:
        st.error(f"❌ Impossibile completare la simulazione: {sim_res.get('message', 'Errore sconosciuto')}")

# ── TAB 3: RADAR COMPARATIVO MULTI-TITOLO ─────────────────────
elif active_screener_tab == "📊 Radar Comparativo Multi-Titolo":
    st.markdown("#### 📊 Confronto Multi-Asset Radar Head-to-Head")
    st.caption("Confronta fino a 4 titoli su 6 pilastri quantitativi (Valutazione, Redditività ROE, Solvibilità Z-Score, Dividendi, Difesa Volatilità, Momentum).")

    avail_tickers = df_raw["ticker"].tolist()
    default_select = avail_tickers[:3] if len(avail_tickers) >= 3 else avail_tickers
    selected_comp = st.multiselect(
        "Seleziona fino a 4 titoli per il confronto:",
        options=avail_tickers,
        default=default_select,
        max_selections=4
    )

    if len(selected_comp) >= 2:
        df_comp = df_raw[df_raw["ticker"].isin(selected_comp)].copy()
        
        # Calcolo assi normalizzati [0 - 100] per il Radar
        categories = ["Valutazione (P/E & Upside)", "Redditività (ROE)", "Solvibilità (Z-Score)", "Dividendi (Yield)", "Difesa (Bassa Volatilità)", "Momentum Tecnico"]
        
        fig_radar = go.Figure()
        colors = ["#58a6ff", "#00e676", "#ff9900", "#d2a8ff"]
        
        for idx, (_, r) in enumerate(df_comp.iterrows()):
            # Punteggi 0-100 normalizzati
            val_sc = np.clip(50.0 + (r.get("upside_pct", 0.0) * 1.2) - (r.get("trailing_pe", 20.0) - 20) * 1.5, 10, 95)
            roe_sc = np.clip((r.get("roe_pct", 10.0) / 30.0) * 100.0, 10, 95)
            z_sc = np.clip((r.get("altman_z_score", 2.5) / 4.5) * 100.0, 10, 95)
            div_sc = np.clip((r.get("dividend_yield_pct", 0.0) / 6.0) * 100.0, 5, 95)
            vol_sc = np.clip(100.0 - (r.get("volatility_ann_pct", 25.0) * 2.0), 10, 95)
            mom_sc = np.clip(r.get("rsi_14", 50.0) + (r.get("perf_1y_pct", 0.0) * 0.5), 10, 95)
            
            values = [val_sc, roe_sc, z_sc, div_sc, vol_sc, mom_sc]
            values.append(values[0]) # Chiusura poligono radar
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=f"{r['ticker']} ({r['name']})",
                line=dict(color=colors[idx % len(colors)], width=2),
                opacity=0.6
            ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9, color="#8b949e")),
                angularaxis=dict(tickfont=dict(size=11, color="#e6edf3"))
            ),
            template="plotly_dark",
            height=460,
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        apply_plotly_theme(fig_radar)
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        # Tabella di comparazione analitica
        st.markdown("##### 📑 Scheda Tecnica Comparativa")
        df_comp_view = df_comp[[
            "ticker", "name", "sector", "last_price", "upside_pct", "trailing_pe", "peg_ratio",
            "dividend_yield_pct", "roe_pct", "altman_z_score", "volatility_ann_pct", "beta", "argus_score"
        ]].rename(columns={
            "ticker": "Ticker", "name": "Azienda", "sector": "Settore", "last_price": "Prezzo",
            "upside_pct": "Upside %", "trailing_pe": "P/E", "peg_ratio": "PEG", "dividend_yield_pct": "Yield %",
            "roe_pct": "ROE %", "altman_z_score": "Altman Z", "volatility_ann_pct": "Vol %", "beta": "Beta", "argus_score": "ARGUS Score"
        })
        st.dataframe(df_comp_view, use_container_width=True, hide_index=True)
    else:
        st.info("Seleziona almeno 2 titoli dal menu per generare il Radar di confronto.")

# ── TAB 4: WATCHLIST & ESPORTAZIONE ORDINI ─────────────────────
elif active_screener_tab == "💾 Watchlist & Segnali Operativi":
    st.markdown("#### 💾 Watchlist & Esportazione per il Broker")
    st.caption("Gestisci i titoli salvati durante la sessione di ricerca ed esporta i report quantitativi.")

    # Sezione Segnali e Trigger Quantitativi di Mercato
    st.markdown("#### 🚨 Segnali e Trigger Quantitativi di Mercato")
    st.caption("Rilevamento algoritmico istantaneo di opportunità asimmetriche (Oversold Quality, Deep Value, Momentum Breakout) o alert di bilancio.")
    
    alerts = compute_market_and_watchlist_alerts(df_raw)
    if alerts:
        col_al = st.columns(min(3, len(alerts)))
        for idx, al in enumerate(alerts[:6]):
            with col_al[idx % len(col_al)]:
                st.markdown(f"""
                <div style="background: rgba(22,27,34,0.6); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {al['color']}; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
                    <div style="font-size: 11px; font-weight: 700; color: {al['color']}; margin-bottom: 4px;">{al['badge']}</div>
                    <div style="font-size: 14px; font-weight: 600; color: #ffffff;">{al['ticker']} <span style="font-size: 12px; color: #8b949e;">({al['name']})</span></div>
                    <div style="font-size: 12px; color: #c9d1d9; margin-top: 4px;">{al['description']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Nessun alert quantitativo rilevato sui titoli dell'universo selezionato.")

    st.divider()

    watchlist_tickers = st.session_state.screener_watchlist
    if watchlist_tickers:
        df_wl = df_raw[df_raw["ticker"].isin(watchlist_tickers)].copy()
        
        col_w_head1, col_w_head2 = st.columns([3, 1])
        with col_w_head1:
            st.markdown(f"**Titoli in Watchlist:** {len(df_wl)} asset salvati.")
        with col_w_head2:
            if st.button("🗑️ Svuota Watchlist", use_container_width=True):
                st.session_state.screener_watchlist = []
                st.rerun()

        st.dataframe(
            df_wl[[
                "ticker", "name", "sector", "last_price", "upside_pct", "trailing_pe", "peg_ratio",
                "dividend_yield_pct", "roe_pct", "altman_z_score", "volatility_ann_pct", "beta", "argus_score"
            ]].rename(columns={
                "ticker": "Ticker", "name": "Nome", "sector": "Settore", "last_price": "Prezzo",
                "upside_pct": "Upside %", "trailing_pe": "P/E", "peg_ratio": "PEG", "dividend_yield_pct": "Div. Yield %",
                "roe_pct": "ROE %", "altman_z_score": "Altman Z", "volatility_ann_pct": "Vol %", "beta": "Beta", "argus_score": "Score"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # Esportazione in CSV ed Excel
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv_data = df_wl.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Scarica Watchlist in CSV",
                data=csv_data,
                file_name="ARGUS_Watchlist_Screener.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_wl.to_excel(writer, index=False, sheet_name='Watchlist')
                df_raw.to_excel(writer, index=False, sheet_name='Full_Universe')
            st.download_button(
                label="📊 Scarica Report Completo Screener (Excel)",
                data=output.getvalue(),
                file_name="ARGUS_Market_Screener_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    else:
        st.info("Nessun titolo attualmente salvato nella Watchlist. Vai al Tab 1 (Screener) e seleziona i titoli preferiti per aggiungerli qui.")
