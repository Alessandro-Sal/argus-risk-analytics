# ============================================================
# 8_📈_Analisi_Tecnica.py — Technical Analysis & Quantitative Charting Cockpit
# ARGUS — Risk Analytics & BI Platform
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.sidebar import render_sidebar
from core.ui_utils import inject_custom_css, render_header
from core.technical_analysis import (
    compute_technical_indicators,
    compute_volume_profile,
    detect_candlestick_patterns,
    compute_technical_confluence_score,
    compute_multi_timeframe_analysis
)

# Configurazione della Pagina Streamlit
st.set_page_config(
    page_title="Analisi Tecnica & Quantitative Charting — ARGUS",
    page_icon="📈",
    layout="wide"
)

inject_custom_css()
render_sidebar()

render_header(
    title="📈 Cockpit di Analisi Tecnica & Quantitative Charting",
    subtitle="Indicatori Algoritmici, Volume Profile (POC/VAH/VAL), Pattern Recognition e Confluence Score"
)

# Verifichiamo la presenza dei dati di sessione
results = st.session_state.get("results")
pos_df = results.get("positions", pd.DataFrame()) if results else pd.DataFrame()

# ── SELEZIONE ASSET, ORIZZONTE TEMPORALE & POPOVERS INFORMATIVI ───
col_asset, col_horizon, col_info_popovers = st.columns([3, 2, 3])

with col_asset:
    tickers_available = pos_df["ticker"].dropna().unique().tolist() if not pos_df.empty and "ticker" in pos_df.columns else ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "SPY"]
    tickers_available.append("Altro (Inserisci Ticker Custom)...")
    selected_ticker_choice = st.selectbox("🎯 Seleziona Asset da Analizzare", tickers_available, index=0)
    
    if selected_ticker_choice.startswith("Altro"):
        target_ticker = st.text_input("Inserisci Ticker Yahoo Finance (es. TSLA, BTC-USD, ASML.AS)", value="AAPL").strip().upper()
    else:
        target_ticker = selected_ticker_choice

with col_horizon:
    time_horizon = st.select_slider(
        "📅 Orizzonte Temporale",
        options=["3 Mesi", "6 Mesi", "1 Anno", "2 Anni", "5 Anni"],
        value="1 Anno"
    )

horizon_days_map = {"3 Mesi": 90, "6 Mesi": 180, "1 Anno": 365, "2 Anni": 730, "5 Anni": 1825}
days_count = horizon_days_map[time_horizon]

# ── BOTTONI INFORMATIVI (POPOVERS PULITI SULLA DESTRA) ────────────
with col_info_popovers:
    st.write("")
    st.write("")
    pop1, pop2, pop3 = st.columns(3)

    with pop1:
        with st.popover("ℹ️ Confluence Guide", use_container_width=True):
            st.markdown("""
            ### 📊 Technical Confluence Score (0 - 100)
            Il punteggio di confluenza quantitativa misura la **salute tecnica e la forza del trend** integrando 5 indicatori indipendenti:
            
            1. **EMA 20 vs EMA 50 (+12 / -12 pts)**: Momentum di breve/medio termine.
            2. **Prezzo vs SMA 200 (+13 / -13 pts)**: Trend primario di lungo termine (Toro vs Orso).
            3. **Istogramma MACD (+10 / -10 pts)**: Accelerazione o decelerazione del prezzo.
            4. **RSI 14 (+5 / -8 / +8 pts)**: Valuta zone di ipercomprato (>70) o ipervenduto (<30).
            5. **ADX 14 (+5 pts)**: Presenza di trend forte (> 25).
            
            ---
            ### 🚦 Verdetto Tattico
            * **75 - 100**: 🟢🟢 **Strong Buy**
            * **60 - 74**: 🟢 **Buy**
            * **40 - 59**: 🟡 **Hold / Neutral**
            * **25 - 39**: 🔴 **Sell**
            * **0 - 24**: 🔴🔴 **Strong Sell**
            """)

    with pop2:
        with st.popover("🧱 Volume Profile", use_container_width=True):
            st.markdown("""
            ### 🧱 Guida al Volume Profile
            Mostra **a quali livelli di prezzo** si sono concentrati i volumi reali scambiati:

            * **POC (Point of Control - Linea Oro)**: Livello di prezzo con il volume massimo scambiato. Agisce da calamita o supporto/resistenza.
            * **Value Area (70% del Volume)**: Canale **VAH** (Value Area High) - **VAL** (Value Area Low) dove si è svolto il 70% degli scambi.
            """)

    with pop3:
        with st.popover("🕯️ Pattern Guide", use_container_width=True):
            st.markdown("""
            ### 🕯️ Pattern Candlestick Algoritmitici
            * **Bullish Engulfing 🟢**: Candela verde di inversione che ingloba la precedente rossa.
            * **Bearish Engulfing 🔴**: Candela rossa di inversione che ingloba la precedente verde.
            * **Hammer 🔨**: Ombra inferiore lunga, rigetto dei minimi.
            * **Shooting Star 🌠**: Ombra superiore lunga, rigetto dei massimi.
            * **Doji ⚖️**: Corpo nullo, equilibrio ed indecisione.
            """)

# ── GENERAZIONE / RECUPERO SERIE STORICA PREZZI CON CACHE SHIELD ──
@st.cache_data(ttl=3600)
def load_price_history_for_ta(ticker: str, days: int) -> pd.DataFrame:
    """Scarica i prezzi storici tramite lo scudo di caching multi-tier (RAM + SQLite 24h)."""
    try:
        from core.cache_shield import get_cached_ticker_history
        start_dt = (pd.Timestamp.today() - pd.Timedelta(days=min(days, 1800))).strftime("%Y-%m-%d")
        df_hist = get_cached_ticker_history(ticker, start_date=start_dt)
        if not df_hist.empty and "close" in df_hist.columns:
            df_out = pd.DataFrame({
                "open": df_hist.get("open", df_hist["close"]),
                "high": df_hist.get("high", df_hist["close"]),
                "low": df_hist.get("low", df_hist["close"]),
                "close": df_hist["close"],
                "volume": df_hist.get("volume", 1000000)
            }, index=df_hist.index)
            return df_out.dropna()
    except Exception:
        pass

    # Fallback sintetico robusto per test o offline
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="B")
    np.random.seed(abs(hash(ticker)) % 10000)
    returns = np.random.normal(0.0006, 0.015, days)
    price_paths = 150.0 * np.exp(np.cumsum(returns))
    
    highs = price_paths * (1.0 + np.abs(np.random.normal(0, 0.008, days)))
    lows = price_paths * (1.0 - np.abs(np.random.normal(0, 0.008, days)))
    opens = lows + (highs - lows) * np.random.uniform(0.2, 0.8, days)
    volumes = np.random.randint(1000000, 50000000, days)

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": price_paths,
        "volume": volumes
    }, index=dates)

df_prices = load_price_history_for_ta(target_ticker, days_count)

if df_prices.empty:
    st.error(f"❌ Impossibile recuperare i dati dei prezzi per il ticker **{target_ticker}**.")
    st.stop()

# ── CALCOLO ENGINE TECNICO ────────────────────────────────────────
tech_res = compute_technical_indicators(df_prices)
vol_res = compute_volume_profile(df_prices, n_bins=25)
patterns_res = detect_candlestick_patterns(df_prices)
confluence_res = compute_technical_confluence_score(df_prices)
mtf_res = compute_multi_timeframe_analysis(df_prices)

df_ind = tech_res["df_indicators"]
df_prof = vol_res["df_profile"]

# ── METRICHE E SCORECARD DI TESTATA ────────────────────────────────
st.divider()

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric(
        "Prezzo Attuale",
        f"{tech_res['last_close']:.2f} €",
        delta=f"{(df_prices['close'].iloc[-1] / df_prices['close'].iloc[-2] - 1)*100:+.2f}%" if len(df_prices) > 1 else None
    )
with m2:
    st.metric("Technical Confluence Score", f"{confluence_res['score']:.0f} / 100", delta=confluence_res["verdict_icon"] + " " + confluence_res["verdict"])
with m3:
    st.metric("RSI (14)", f"{tech_res['rsi_latest']:.1f}", delta=tech_res["rsi_status"])
with m4:
    st.metric("Point of Control (POC)", f"{vol_res['poc_price']:.2f} €", help="Livello di prezzo con il maggior volume scambiato")
with m5:
    st.metric("Forza Trend (ADX 14)", f"{tech_res['adx_latest']:.1f}", delta=tech_res["adx_strength"])

st.divider()

# ── GRAFICO COCKPIT MULTI-PANNELLO (PLOTLY) ────────────────────────
chart_tab1, chart_tab2 = st.tabs(["📊 Cockpit Tecnico Completo (Candlestick + Overlays + Volume Profile)", "🧱 Analisi Dettagliata Volume Profile"])

with chart_tab1:
    col_chart, col_side_profile = st.columns([3, 1])

    with col_chart:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[
                f"Analisi Prezzi, Medie Mobili (EMA20/EMA50/SMA200) e Bande di Bollinger — {target_ticker}",
                "Momentum MACD (Linea, Segnale e Istogramma)",
                "Relative Strength Index (RSI 14) con Zone 70 / 30"
            ],
            row_heights=[0.55, 0.23, 0.22]
        )

        # ── SUBPLOT 1: PREZZO & OVERLAYS ────────────────────────────
        fig.add_trace(go.Candlestick(
            x=df_prices.index,
            open=df_prices["open"],
            high=df_prices["high"],
            low=df_prices["low"],
            close=df_prices["close"],
            name="OHLC",
            showlegend=True
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["ema20"], line=dict(color="#00E5FF", width=1.5), name="EMA 20", showlegend=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["ema50"], line=dict(color="#FF9100", width=1.5), name="EMA 50", showlegend=True), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["sma200"], line=dict(color="#E91E63", width=2, dash="dash"), name="SMA 200", showlegend=True), row=1, col=1)

        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_upper"], line=dict(color="rgba(100, 181, 246, 0.3)"), name="BB Upper", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_lower"], line=dict(color="rgba(100, 181, 246, 0.3)"), fill="tonexty", fillcolor="rgba(100, 181, 246, 0.08)", name="Bollinger (20, 2.0)", showlegend=True), row=1, col=1)

        # POC Price Line
        fig.add_hline(y=vol_res["poc_price"], line_dash="dash", line_color="#FFD700", annotation_text=f"POC: {vol_res['poc_price']:.2f}€", row=1, col=1)

        # ── SUBPLOT 2: MACD (INDICATORE AUTOCONTENUTO) ─────────────
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd_line"], line=dict(color="#29B6F6", width=1.5), name="MACD Line", showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd_signal"], line=dict(color="#FFA726", width=1.5), name="Signal", showlegend=False), row=2, col=1)
        colors_macd = ["#00E676" if val >= 0 else "#FF5252" for val in df_ind["macd_hist"]]
        fig.add_trace(go.Bar(x=df_ind.index, y=df_ind["macd_hist"], marker_color=colors_macd, name="MACD Hist", showlegend=False), row=2, col=1)

        # ── SUBPLOT 3: RSI 14 (INDICATORE AUTOCONTENUTO) ────────────
        fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["rsi14"], line=dict(color="#AB47BC", width=2), name="RSI 14", showlegend=False), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#FF5252", annotation_text="70", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00E676", annotation_text="30", row=3, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=750,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.01,
                font=dict(size=11),
                bgcolor="rgba(13, 17, 23, 0.6)"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_side_profile:
        st.subheader("🧱 Volume Profile")
        fig_profile = go.Figure()

        colors_profile = []
        for _, row_p in df_prof.iterrows():
            if row_p["is_poc"]:
                colors_profile.append("#FFD700")  # Oro POC
            elif row_p["in_value_area"]:
                colors_profile.append("#00E5FF")  # Ciano Value Area
            else:
                colors_profile.append("#424242")  # Grigio scuro fuori Value Area

        fig_profile.add_trace(go.Bar(
            y=df_prof["price_bin_mid"],
            x=df_prof["volume_pct"],
            orientation="h",
            marker=dict(color=colors_profile),
            hovertemplate="Prezzo: %{y:.2f}€<br>Volume: %{x:.1f}%<extra></extra>",
            showlegend=False
        ))

        fig_profile.add_hline(y=vol_res["poc_price"], line_dash="dash", line_color="#FFD700", annotation_text="POC")
        fig_profile.add_hline(y=vol_res["vah_price"], line_dash="dot", line_color="#00E676", annotation_text="VAH")
        fig_profile.add_hline(y=vol_res["val_price"], line_dash="dot", line_color="#FF5252", annotation_text="VAL")

        fig_profile.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=750,
            title="Volume % per Prezzo",
            xaxis_title="Volume %",
            yaxis_title="Prezzo €",
            margin=dict(l=10, r=10, t=60, b=20)
        )
        st.plotly_chart(fig_profile, use_container_width=True)

with chart_tab2:
    st.subheader("🧱 Dettaglio Distribuzione Volume Profile & Value Area (70%)")
    col_v1, col_v2 = st.columns([1, 2])

    with col_v1:
        st.markdown(f"""
        * **POC (Point of Control)**: <span style='color:#FFD700; font-weight:bold; font-size:18px;'>{vol_res['poc_price']:.2f} €</span>
        * **VAH (Value Area High)**: <span style='color:#00E676; font-weight:bold; font-size:18px;'>{vol_res['vah_price']:.2f} €</span>
        * **VAL (Value Area Low)**: <span style='color:#FF5252; font-weight:bold; font-size:18px;'>{vol_res['val_price']:.2f} €</span>
        * **Volume Totale Calcolato**: `{vol_res['total_volume']:,.0f}` unità
        """, unsafe_allow_html=True)
        st.caption("Il 70% di tutte le contrattazioni storiche è avvenuto all'interno del canale VAH - VAL.")

    with col_v2:
        df_prof_display = df_prof.copy()
        df_prof_display["is_poc_str"] = df_prof_display["is_poc"].map({True: "⭐ Point of Control", False: "—"})
        df_prof_display["in_va_str"] = df_prof_display["in_value_area"].map({True: "🟢 Value Area (70%)", False: "⚪ Fuori Canale"})

        df_prof_renamed = df_prof_display[[
            "price_bin_mid", "price_bin_min", "price_bin_max", "volume", "volume_pct", "is_poc_str", "in_va_str"
        ]].rename(columns={
            "price_bin_mid": "Livello Prezzo (€)",
            "price_bin_min": "Fascia Minima (€)",
            "price_bin_max": "Fascia Massima (€)",
            "volume": "Volume Scambiato",
            "volume_pct": "Volume Relativo %",
            "is_poc_str": "Stato POC",
            "in_va_str": "Canale Value Area"
        })

        st.dataframe(
            df_prof_renamed.style.format({
                "Livello Prezzo (€)": "{:.2f} €",
                "Fascia Minima (€)": "{:.2f} €",
                "Fascia Massima (€)": "{:.2f} €",
                "Volume Scambiato": "{:,.0f}",
                "Volume Relativo %": "{:.2f}%"
            }),
            use_container_width=True,
            hide_index=True,
            height=300
        )

# ── CONFLUENCE SCORE & PATTERN RECOGNITION ────────────────────────
st.divider()

col_conf, col_patt = st.columns([1, 1])

with col_conf:
    st.subheader("🚦 Technical Confluence Score Card")
    st.markdown(f"### Score Totale: **{confluence_res['score']:.0f} / 100** — {confluence_res['verdict_icon']} **{confluence_res['verdict']}**")
    
    st.progress(int(confluence_res['score']) / 100)

    df_factors = pd.DataFrame(confluence_res["factors"])
    if not df_factors.empty:
        df_factors_display = df_factors.rename(columns={
            "indicator": "Indicatore Tecnico",
            "status": "Segnale / Stato",
            "impact": "Punteggio Confluenza",
            "note": "Dettaglio & Condizione"
        })
        st.dataframe(df_factors_display, use_container_width=True, hide_index=True, height=260)

with col_patt:
    st.subheader("🕯️ Pattern Candlestick Rilevati")
    if patterns_res:
        df_patt = pd.DataFrame(patterns_res)
        df_patt_display = df_patt.rename(columns={
            "date": "Data Rilevazione",
            "pattern": "Pattern Candlestick",
            "bias": "Direzione / Bias",
            "description": "Significato & Implicazione Operativa"
        })
        st.dataframe(df_patt_display, use_container_width=True, hide_index=True, height=260)
    else:
        st.info("ℹ️ Nessun pattern candlestick rilevante individuato sulle ultime barre.")

    st.subheader("⏳ Trend Multi-Timeframe Alignment")
    mtf_c1, mtf_c2 = st.columns(2)
    with mtf_c1:
        st.metric("Trend Giornaliero (1D)", mtf_res["trend_daily"])
    with mtf_c2:
        st.metric("Trend Settimanale (1W)", mtf_res["trend_weekly"])
    st.caption(mtf_res["alignment_text"])
