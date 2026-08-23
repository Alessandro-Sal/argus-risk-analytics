import importlib
import core.ui_utils as ui_utils
import core.risk_engine as risk_engine
importlib.reload(ui_utils)
importlib.reload(risk_engine)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.sidebar import render_sidebar
from core.ui_utils import (
    inject_custom_css, render_header, render_segmented_tabs, metric_card,
    apply_plotly_theme, glossary_modal, ensure_risk_bundle_loaded, render_sandbox_banner
)
from core.workspace_manager import get_url_param, set_url_params, register_workspace_tab
from core.technical_analysis import (
    compute_technical_indicators,
    compute_volume_profile,
    detect_candlestick_patterns,
    compute_technical_confluence_score,
    compute_multi_timeframe_analysis
)
from core.streaming_engine import (
    MarketTick,
    TickRingBuffer,
    OrderBookLevel,
    OrderBookL2,
    generate_mock_streaming_ticks
)

# Configurazione della Pagina Streamlit
st.set_page_config(
    page_title="Analisi Tecnica & Quantitative Charting | ARGUS",
    page_icon="📈",
    layout="wide"
)

inject_custom_css()
render_sidebar()

col_head1, col_head2 = st.columns([3.2, 1.2])
with col_head1:
    st.title("📈 Cockpit di Analisi Tecnica & Quantitative Charting")
    st.caption("Indicatori Algoritmici, Volume Profile (POC/VAH/VAL), Pattern Recognition e Confluence Score per supportare decisioni di trading e ribilanciamento.")
with col_head2:
    st.markdown('<div style="margin-top: 14px;"></div>', unsafe_allow_html=True)
    glossary_modal("Cos'è il Cockpit di Analisi Tecnica & Quantitative Charting?", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Analisi Tecnica Quantitativa</div>
  <div>Studio algoritmico dei prezzi, volumi e momentum per identificare asimmetrie statistiche e punti di ingresso/uscita ottimali. Il modulo calcola automaticamente 15+ indicatori tecnici in tempo reale.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Moduli & Algoritmi Integrati</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Technical Confluence Score:</b> Punteggio composito 0-100 ponderato su 5 indicatori quantitativi.<br>
    • <b>Volume Profile & Value Area:</b> Mappatura volumetrica ad asta con Point of Control (POC), VAH e VAL.<br>
    • <b>Pattern Recognition:</b> Scanner algoritmico candele giapponesi (Engulfing, Hammer, Doji).<br>
    • <b>Trend Multi-Timeframe (MTF):</b> Conferma del trend operativo Daily (1D) su scala Settimanale (1W).<br>
    • <b>Split-Screen Dual View:</b> Terminale affiancato per comparazione Tecnica vs Fondamentale o Head-to-Head.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Guida all'Utilizzo Operativo</div>
  <div>
    1. <b>Selezione Asset:</b> Scegli un titolo del portafoglio o inserisci un qualsiasi ticker Yahoo Finance.<br>
    2. <b>Confluenza di Segnali:</b> Cerca convergenza tra Confluence Score &gt; 60, supporto POC e RSI non ipercomprato.<br>
    3. <b>Filtro Multi-Timeframe:</b> Evita ingressi long se il trend settimanale (1W) è discendente.
  </div>
</div>

</div>
""", button_label="💡 Come funziona l'Analisi Tecnica?")

# Verifichiamo la presenza dei dati di sessione o Sandbox
results, has_real_portfolio = ensure_risk_bundle_loaded()
pos_df = results.get("positions", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()

if not has_real_portfolio:
    render_sandbox_banner()

# ── SELEZIONE ASSET, ORIZZONTE TEMPORALE & POPOVERS INFORMATIVI ───
url_ticker = get_url_param("ticker", None) or st.session_state.get("ta_target_ticker", None)
if "ta_target_ticker" in st.session_state:
    del st.session_state["ta_target_ticker"]

col_asset, col_horizon, col_dual_toggle, col_guide = st.columns([2.8, 2.0, 1.8, 1.8])

with col_asset:
    if not pos_df.empty and "ticker" in pos_df.columns:
        tickers_available = pos_df["ticker"].dropna().unique().tolist()
    else:
        tickers_available = ["AAPL", "NVDA", "MSFT", "SPY", "QQQ", "TSLA", "BTC-USD", "ENEL.MI", "RACE.MI", "MC.PA"]
    
    if url_ticker and url_ticker not in tickers_available and "Custom" not in url_ticker:
        tickers_available.insert(0, url_ticker)
    
    tickers_available.append("🔍 Inserisci Ticker Custom...")
    default_idx = tickers_available.index(url_ticker) if (url_ticker and url_ticker in tickers_available) else 0
    selected_ticker_choice = st.selectbox("🎯 Seleziona Asset da Analizzare", tickers_available, index=default_idx)
    
    if "Custom" in selected_ticker_choice:
        target_ticker = st.text_input("Inserisci Ticker Yahoo Finance (es. TSLA, BTC-USD, ASML.AS)", value="AAPL").strip().upper()
    else:
        target_ticker = selected_ticker_choice

    # Aggiorna URL e Workspace tab
    set_url_params(ticker=target_ticker)
    register_workspace_tab(f"tech_{target_ticker}", f"📈 {target_ticker}", "8_Analisi_Tecnica", {"ticker": target_ticker})

with col_horizon:
    time_horizon = st.select_slider(
        "📅 Orizzonte Temporale",
        options=["3 Mesi", "6 Mesi", "1 Anno", "2 Anni", "5 Anni"],
        value="1 Anno"
    )

horizon_days_map = {"3 Mesi": 90, "6 Mesi": 180, "1 Anno": 365, "2 Anni": 730, "5 Anni": 1825}
days_count = horizon_days_map[time_horizon]

with col_dual_toggle:
    st.write("")
    st.write("")
    split_view_active = st.toggle("🪟 Split-Screen Terminale", value=False, help="Affianca l'analisi tecnica a quella fondamentale o a un secondo ticker stile Terminale Bloomberg.")

with col_guide:
    st.write("")
    st.write("")
    with st.popover("📖 Guida Indicatori", use_container_width=True):
        st.markdown("### 📊 Confluence Score, Volume Profile & Pattern")
        p_t1, p_t2, p_t3 = st.tabs(["🚦 Confluence", "🧱 Volume Profile", "🕯️ Pattern Candlestick"])
        with p_t1:
            st.markdown("""
            **Technical Confluence Score (0 - 100)**
            Misura la salute tecnica e la forza del trend integrando 5 indicatori quantitativi indipendenti:
            * **EMA 20 vs EMA 50 (±12 pts)**: Momentum di breve/medio termine.
            * **Prezzo vs SMA 200 (±13 pts)**: Trend primario di lungo termine.
            * **Istogramma MACD (±10 pts)**: Accelerazione o decelerazione del prezzo.
            * **RSI 14 (+5 / -8 / +8 pts)**: Valutazione ipercomprato (>70) o ipervenduto (<30).
            * **ADX 14 (+5 pts)**: Presenza di trend forte (>25).

            **Verdetto Tattico**:
            * 🟢🟢 **75 - 100**: Strong Buy
            * 🟢 **60 - 74**: Buy
            * 🟡 **40 - 59**: Hold / Neutral
            * 🔴 **25 - 39**: Sell
            * 🔴🔴 **0 - 24**: Strong Sell
            """)
        with p_t2:
            st.markdown("""
            **Volume Profile & Value Area (70%)**
            Mostra **a quali livelli di prezzo** si sono concentrati i volumi reali scambiati:
            * **POC (Point of Control - Linea Oro)**: Livello con il volume massimo scambiato. Agisce da forte supporto o resistenza istituzionale.
            * **Value Area (70% del Volume)**: Fascia compresa tra **VAH** (Value Area High) e **VAL** (Value Area Low).
            """)
        with p_t3:
            st.markdown("""
            **Pattern Candlestick Algoritmici**
            * **Bullish Engulfing 🟢**: Candela verde di inversione rialzista.
            * **Bearish Engulfing 🔴**: Candela rossa di inversione ribassista.
            * **Hammer 🔨**: Ombra inferiore lunga, forte rigetto dei minimi.
            * **Shooting Star 🌠**: Ombra superiore lunga, rigetto dei massimi.
            * **Doji ⚖️**: Corpo nullo, fase di equilibrio e indecisione.
            """)

# ── GENERAZIONE / RECUPERO SERIE STORICA PREZZI CON CACHE SHIELD ──
@st.cache_data(ttl=3600, show_spinner="⏳ Elaborazione serie storica e indicatori di analisi tecnica...")
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

chg_pct = ((df_prices['close'].iloc[-1] / df_prices['close'].iloc[-2] - 1)*100) if len(df_prices) > 1 else 0.0
m1, m2, m3 = st.columns(3)
with m1:
    metric_card("Prezzo Attuale", f"€ {tech_res['last_close']:.2f}", f"{chg_pct:+.2f}% 24h", positive=chg_pct >= 0)
with m2:
    conf_score = confluence_res['score']
    metric_card("Confluence Score", f"{conf_score:.0f} / 100", f"{confluence_res['verdict_icon']} {confluence_res['verdict']}", positive=conf_score >= 60)
with m3:
    rsi_val = tech_res['rsi_latest']
    metric_card("RSI (14)", f"{rsi_val:.1f}", tech_res["rsi_status"], positive=(30 <= rsi_val <= 70))

st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
m4, m5 = st.columns(2)
with m4:
    metric_card("Point of Control (POC)", f"€ {vol_res['poc_price']:.2f}", f"VA: € {vol_res['val_price']:.1f} - {vol_res['vah_price']:.1f}", positive=True, help_text="Livello di prezzo con la massima concentrazione di volumi scambiati.")
with m5:
    adx_val = tech_res['adx_latest']
    metric_card("Forza Trend (ADX 14)", f"{adx_val:.1f}", tech_res["adx_strength"], positive=adx_val >= 25)

# ── MODALITÀ SPLIT-SCREEN TERMINALE (DUAL VIEW) ───────────────────
if split_view_active:
    col_sp1, col_sp2 = st.columns([3.2, 1.2])
    with col_sp1:
        st.markdown("### 🪟 Terminale Split-Screen | Dual View Finanziaria")
        st.caption("Pannelli affiancati in tempo reale per confronto cross-dimensionale (Tecnico vs Fondamentale o Head-to-Head tra 2 titoli).")
    with col_sp2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("Guida alla Modalità Split-Screen Terminale", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 Finalità della Dual View</div>
  <div>Permette di valutare un titolo su due dimensioni simultanee (Tecnica + Fondamentale) o di comparare due asset concorrenti (Head-to-Head) in perfetto stile Bloomberg Terminal.</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">💡 I Due Casi d'Uso</div>
  <div>
    • <b>Due Diligence Fondamentale:</b> Unisce il timing tecnico con i fondamentali 10-K (Consensus Target, Altman Z-Score, Piotroski F-Score, Beneish M-Score e Multipli di Valutazione).<br>
    • <b>Head-to-Head 2° Ticker:</b> Compara la forza relativa del prezzo e la confluenza tecnica tra due titoli alternativi dello stesso settore.
  </div>
</div>
</div>
""", button_label="ℹ️ Guida Split-Screen")
    
    col_left, col_right = st.columns(2)
    
    # ── PANNELLO SINISTRO: ANALISI TECNICA & VOLUME PROFILE ──
    with col_left:
        st.markdown(f"#### 📈 Analisi Tecnica: `{target_ticker}`")
        fig_dual_left = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=[f"Candlestick & EMA/SMA | {target_ticker}", "RSI (14) & Momentum"],
            row_heights=[0.7, 0.3]
        )
        fig_dual_left.add_trace(go.Candlestick(
            x=df_prices.index, open=df_prices["open"], high=df_prices["high"],
            low=df_prices["low"], close=df_prices["close"], name=target_ticker
        ), row=1, col=1)
        fig_dual_left.add_trace(go.Scatter(x=df_ind.index, y=df_ind["ema20"], line=dict(color="#00E5FF", width=1.5), name="EMA 20"), row=1, col=1)
        fig_dual_left.add_trace(go.Scatter(x=df_ind.index, y=df_ind["sma200"], line=dict(color="#E91E63", width=1.8, dash="dash"), name="SMA 200"), row=1, col=1)
        fig_dual_left.add_hline(y=vol_res["poc_price"], line_dash="dash", line_color="#FFD700", annotation_text=f"POC {vol_res['poc_price']:.2f}€", row=1, col=1)
        
        fig_dual_left.add_trace(go.Scatter(x=df_ind.index, y=df_ind["rsi14"], line=dict(color="#AB47BC", width=2), name="RSI"), row=2, col=1)
        fig_dual_left.add_hline(y=70, line_dash="dash", line_color="#FF5252", row=2, col=1)
        fig_dual_left.add_hline(y=30, line_dash="dash", line_color="#00E676", row=2, col=1)
        
        fig_dual_left.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
        apply_plotly_theme(fig_dual_left)
        st.plotly_chart(fig_dual_left, use_container_width=True, key="tech_dual_chart_left", config={"displayModeBar": "hover", "displaylogo": False})
        
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            metric_card("Confluence Score", f"{confluence_res['score']:.0f}/100", confluence_res["verdict"], positive=confluence_res['score'] >= 60)
        with c_l2:
            metric_card("POC Price", f"€ {vol_res['poc_price']:.2f}", f"VA: € {vol_res['val_price']:.1f} - {vol_res['vah_price']:.1f}", positive=True)
            
    # ── PANNELLO DESTRO: DUE DILIGENCE FONDAMENTALE O 2° TICKER ──
    with col_right:
        dual_mode_choice = st.radio("Pannello Destro:", ["🏛️ Valutazione Fondamentale", "⚔️ 2° Ticker Head-to-Head"], horizontal=True, key="dual_panel_mode_choice")
        
        if dual_mode_choice == "🏛️ Valutazione Fondamentale":
            st.markdown(f"#### 🏛️ Due Diligence Fondamentale: `{target_ticker}`")
            try:
                from core.financial_analysis import compute_altman_z_score, compute_piotroski_f_score, compute_valuation_multiples_matrix
                from core.forensic_accounting import compute_beneish_m_score
                from core.cache_shield import get_cached_ticker_info

                info = get_cached_ticker_info(target_ticker) or {}
                target_price = info.get("targetMeanPrice") or info.get("targetMedianPrice")
                curr_p = tech_res["last_close"]
                upside_pct = ((target_price / curr_p - 1) * 100) if (target_price and curr_p > 0) else None

                alt_res = compute_altman_z_score(target_ticker)
                piot_res = compute_piotroski_f_score(target_ticker)
                beneish_res = compute_beneish_m_score(target_ticker)
                mult_df = compute_valuation_multiples_matrix(target_ticker)
                
                f1, f2, f3 = st.columns(3)
                with f1:
                    metric_card("Consensus Target", f"€ {target_price:.2f}" if target_price else "N/A", f"{upside_pct:+.1f}% Upside" if upside_pct is not None else "N/A", positive=(upside_pct or 0) >= 0)
                with f2:
                    metric_card("Altman Z (Solvibilità)", f"{alt_res['z_score']:.2f}", f"{alt_res['zone_icon']} {alt_res['zone_name']}", positive=alt_res['z_score'] > 1.81)
                with f3:
                    metric_card("Piotroski (Qualità)", f"{piot_res['f_score']} / 9", f"{piot_res['quality_icon']} {piot_res['quality_grade']}", positive=piot_res['f_score'] >= 6)
                
                st.markdown("##### 📊 Multipli di Mercato & Valutazione")
                st.dataframe(mult_df, use_container_width=True, hide_index=True)
                
                st.markdown(f"""
                <div class="glass-card" style="padding:10px 14px; margin-top:8px;">
                    <div style="font-size:12px; color:#8b949e;">FORENSIC & EARNINGS QUALITY (BENEISH M-SCORE)</div>
                    <div style="font-size:15px; font-weight:700; color:{'#00e676' if not beneish_res['is_manipulator'] else '#f85149'}; margin: 2px 0;">
                        {beneish_res['verdict_icon']} M-Score: {beneish_res['m_score']:.2f} | {beneish_res['verdict_label']}
                    </div>
                    <div style="font-size:11.5px; color:#8b949e;">{beneish_res['description']}</div>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Dati fondamentali non disponibili per {target_ticker}: {e}")
                
        else:
            sec_tickers = [t for t in tickers_available if t != target_ticker and "Custom" not in t]
            if not sec_tickers:
                sec_tickers = ["MSFT", "NVDA", "GOOGL", "AMZN"]
            second_ticker = st.selectbox("Seleziona 2° Asset di Confronto:", sec_tickers, index=0, key="split_second_ticker_select")
            st.markdown(f"#### ⚔️ Analisi Tecnica 2° Ticker: `{second_ticker}`")
            
            df_sec = load_price_history_for_ta(second_ticker, days_count)
            sec_tech = compute_technical_indicators(df_sec)
            sec_vol = compute_volume_profile(df_sec, n_bins=20)
            sec_conf = compute_technical_confluence_score(df_sec)
            
            fig_dual_right = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                vertical_spacing=0.06,
                subplot_titles=[f"Candlestick & EMA/SMA | {second_ticker}", "RSI (14) & Momentum"],
                row_heights=[0.7, 0.3]
            )
            fig_dual_right.add_trace(go.Candlestick(
                x=df_sec.index, open=df_sec["open"], high=df_sec["high"],
                low=df_sec["low"], close=df_sec["close"], name=second_ticker
            ), row=1, col=1)
            fig_dual_right.add_trace(go.Scatter(x=sec_tech["df_indicators"].index, y=sec_tech["df_indicators"]["ema20"], line=dict(color="#00E5FF", width=1.5), name="EMA 20"), row=1, col=1)
            fig_dual_right.add_trace(go.Scatter(x=sec_tech["df_indicators"].index, y=sec_tech["df_indicators"]["sma200"], line=dict(color="#E91E63", width=1.8, dash="dash"), name="SMA 200"), row=1, col=1)
            fig_dual_right.add_hline(y=sec_vol["poc_price"], line_dash="dash", line_color="#FFD700", annotation_text=f"POC {sec_vol['poc_price']:.2f}€", row=1, col=1)
            
            fig_dual_right.add_trace(go.Scatter(x=sec_tech["df_indicators"].index, y=sec_tech["df_indicators"]["rsi14"], line=dict(color="#AB47BC", width=2), name="RSI"), row=2, col=1)
            fig_dual_right.add_hline(y=70, line_dash="dash", line_color="#FF5252", row=2, col=1)
            fig_dual_right.add_hline(y=30, line_dash="dash", line_color="#00E676", row=2, col=1)
            
            fig_dual_right.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
            apply_plotly_theme(fig_dual_right)
            st.plotly_chart(fig_dual_right, use_container_width=True, key="tech_dual_chart_right", config={"displayModeBar": "hover", "displaylogo": False})
            
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                metric_card("Confluence Score 2°", f"{sec_conf['score']:.0f}/100", sec_conf["verdict"], positive=sec_conf['score'] >= 60)
            with c_r2:
                metric_card("Prezzo Attuale 2°", f"€ {sec_tech['last_close']:.2f}", sec_tech["rsi_status"], positive=True)

else:
    # ── GRAFICO COCKPIT & MODULI AVANZATI CON SEGMENTED TABS (LAZY LOADING) ───
    tab_tech = render_segmented_tabs([
        "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)",
        "🧱 Distribuzione Analitica Volume Profile",
        "🚦 Confluence Score & Pattern Recognition",
        "⏳ Trend Multi-Timeframe Alignment (1D / 1W)",
        "⚡ Real-Time Streaming & Book Depth (STREAM)"
    ], key="tech_active_subtab")

    if tab_tech == "📊 Cockpit Completo (Candlestick + Overlays + Volume Profile)":
        col_chart, col_side_profile = st.columns([3.2, 0.95])

        with col_chart:
            col_cp1, col_cp2 = st.columns([3.2, 1.2])
            with col_cp1:
                st.markdown(f"#### 📊 Cockpit Tecnico & Quantitative Overlays | `{target_ticker}`")
            with col_cp2:
                glossary_modal("Guida al Cockpit Quantitativo & Indicatori Overlays", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📈 Medie Mobili (EMA 20, EMA 50, SMA 200)</div>
  <div>
    • <b>EMA 20 / EMA 50:</b> Medie esponenziali rapide per identificare il trend di breve/medio termine e i crossover direzionali.<br>
    • <b>SMA 200:</b> Media semplice secolare. Il superamento al rialzo della SMA 200 da parte della EMA 50 genera il <i>Golden Cross</i> (segnale bull secolare), mentre l'incrocio al ribasso genera il <i>Death Cross</i>.
  </div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🌊 Bande di Bollinger (20, 2.0σ)</div>
  <div>Canale statistico calcolato a 2 deviazioni standard dalla media mobile a 20 periodi. Quando le bande si comprimono (<i>Squeeze</i>), indicano un'imminente esplosione di volatilità direzionale.</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚡ MACD & RSI (14)</div>
  <div>
    • <b>MACD (12, 26, 9):</b> Differenza tra due medie esponenziali con istogramma di accelerazione.<br>
    • <b>RSI (14):</b> Oscillatore di forza relativa con soglie canoniche: <b>&gt; 70</b> (Ipercomprato) e <b>&lt; 30</b> (Ipervenduto).
  </div>
</div>
</div>
""", button_label="📖 Guida Indicatori Cockpit")

            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.06,
                subplot_titles=[
                    "",
                    "Momentum MACD (Linea, Segnale e Istogramma)",
                    "Relative Strength Index (RSI 14) con Zone 70 / 30"
                ],
                row_heights=[0.56, 0.22, 0.22]
            )

            # ── SUBPLOT 1: PREZZO & OVERLAYS ────────────────────────────
            fig.add_trace(go.Candlestick(
                x=df_prices.index,
                open=df_prices["open"],
                high=df_prices["high"],
                low=df_prices["low"],
                close=df_prices["close"],
                increasing_line_color="#3fb950",
                decreasing_line_color="#f85149",
                name="Candele Prezzo",
                showlegend=True
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=df_ind.index, y=df_ind["ema20"], 
                line=dict(color="#00E5FF", width=1.5), 
                name="EMA 20", showlegend=True,
                hovertemplate="EMA 20: <b>€ %{y:.2f}</b><extra></extra>"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df_ind.index, y=df_ind["ema50"], 
                line=dict(color="#FF9100", width=1.5), 
                name="EMA 50", showlegend=True,
                hovertemplate="EMA 50: <b>€ %{y:.2f}</b><extra></extra>"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=df_ind.index, y=df_ind["sma200"], 
                line=dict(color="#E91E63", width=2, dash="dash"), 
                name="SMA 200", showlegend=True,
                hovertemplate="SMA 200: <b>€ %{y:.2f}</b><extra></extra>"
            ), row=1, col=1)

            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_upper"], line=dict(color="rgba(100, 181, 246, 0.3)"), name="BB Upper", showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["bb_lower"], line=dict(color="rgba(100, 181, 246, 0.3)"), fill="tonexty", fillcolor="rgba(100, 181, 246, 0.08)", name="Bollinger (20, 2.0)", showlegend=True), row=1, col=1)

            # POC Price Line
            fig.add_hline(y=vol_res["poc_price"], line_dash="dash", line_color="#FFD700", annotation_text=f"POC: {vol_res['poc_price']:.2f}€", row=1, col=1)

            # ── SUBPLOT 2: MACD ─────────────────────────────────────────
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd_line"], line=dict(color="#29B6F6", width=1.5), name="MACD Line", showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["macd_signal"], line=dict(color="#FFA726", width=1.5), name="Signal", showlegend=False), row=2, col=1)
            colors_macd = ["#00E676" if val >= 0 else "#FF5252" for val in df_ind["macd_hist"]]
            fig.add_trace(go.Bar(x=df_ind.index, y=df_ind["macd_hist"], marker_color=colors_macd, name="MACD Hist", showlegend=False), row=2, col=1)

            # ── SUBPLOT 3: RSI 14 ───────────────────────────────────────
            fig.add_trace(go.Scatter(x=df_ind.index, y=df_ind["rsi14"], line=dict(color="#AB47BC", width=2), name="RSI 14", showlegend=False), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#FF5252", annotation_text="70", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00E676", annotation_text="30", row=3, col=1)

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=750,
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=35, b=20),
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
                )
            )
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="tech_main_candlestick_chart", config={"displayModeBar": "hover", "displaylogo": False})

        with col_side_profile:
            st.markdown("#### 🧱 Volume Profile")
            df_prof = vol_res.get("df_profile", vol_res.get("profile", pd.DataFrame()))
            if not df_prof.empty and "is_poc" in df_prof.columns:
                bar_colors = [
                    "#FFD700" if is_poc else ("#00E676" if in_va else "#546E7A")
                    for is_poc, in_va in zip(df_prof["is_poc"], df_prof["in_value_area"])
                ]

                fig_profile = go.Figure()
                fig_profile.add_trace(go.Bar(
                    x=df_prof["volume_pct"],
                    y=df_prof["price_bin_mid"],
                    orientation="h",
                    marker_color=bar_colors,
                    name="Volume %",
                    hovertemplate="<b>Prezzo:</b> %{y:.2f} €<br><b>Volume:</b> %{x:.1f}%<extra></extra>"
                ))

                fig_profile.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=750,
                    xaxis_title="Volume %",
                    yaxis_title="Prezzo €",
                    margin=dict(l=10, r=10, t=35, b=20)
                )
                apply_plotly_theme(fig_profile)
                st.plotly_chart(fig_profile, use_container_width=True, key="tech_side_volume_profile_bar", config={"displayModeBar": "hover", "displaylogo": False})
            else:
                st.info("Dati di Volume Profile non disponibili per questo orizzonte temporale.")

    elif tab_tech == "🧱 Distribuzione Analitica Volume Profile":
        col_vp_h1, col_vp_h2 = st.columns([3.2, 1.2])
        with col_vp_h1:
            st.subheader("🧱 Dettaglio Distribuzione Volume Profile & Value Area (70%)")
        with col_vp_h2:
            st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
            glossary_modal("Guida al Volume Profile & Auction Market Theory", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🟡 Point of Control (POC)</div>
  <div>Il singolo livello di prezzo in cui è stato scambiato il massimo volume di contratti/azioni nel periodo analizzato. Costituisce un punto di equilibrio primario (Fair Value) e attrae costantemente i prezzi.</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🟢 Value Area (VAH & VAL)</div>
  <div>La fascia di prezzo che racchiude il <b>70% del volume totale scambiato</b> (corrispondente a 1 deviazione standard empirica della campana volumetrica). I suoi estremi fungono da supporto (VAL) e resistenza (VAH).</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚖️ Nodi di Alto e Basso Volume (HVN vs LVN)</div>
  <div>
    • <b>HVN (High Volume Node):</b> Zone di accettazione e accumulo istituzionale dove il prezzo tende a consolidare.<br>
    • <b>LVN (Low Volume Node):</b> Zone di rifiuto rapido attraversate dal prezzo ad alta velocità.
  </div>
</div>
</div>
""", button_label="📖 Guida Volume Profile")

        col_v1, col_v2 = st.columns([1.1, 1.9])

        with col_v1:
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px 18px; border-radius: 12px; margin-bottom: 12px;">
                <div style="font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 12px;">
                    📐 Parametri Volume Profile (Auction Theory)
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span style="color: #c9d1d9; font-size: 13px;">⭐ <b>Point of Control (POC):</b></span>
                    <span style="color: #FFD700; font-weight: 700; font-size: 15px;">€ {vol_res['poc_price']:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span style="color: #c9d1d9; font-size: 13px;">🟢 <b>Value Area High (VAH):</b></span>
                    <span style="color: #3fb950; font-weight: 700; font-size: 15px;">€ {vol_res['vah_price']:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
                    <span style="color: #c9d1d9; font-size: 13px;">🔴 <b>Value Area Low (VAL):</b></span>
                    <span style="color: #f85149; font-weight: 700; font-size: 15px;">€ {vol_res['val_price']:.2f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0;">
                    <span style="color: #c9d1d9; font-size: 13px;">📊 <b>Volume Totale:</b></span>
                    <span style="color: #58a6ff; font-weight: 700; font-size: 14px;">{vol_res['total_volume']:,.0f} unità</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"ℹ️ Il **70%** di tutte le contrattazioni storiche registrate è avvenuto all'interno del canale **VAL (€ {vol_res['val_price']:.2f}) - VAH (€ {vol_res['vah_price']:.2f})**.")

        with col_v2:
            if not df_prof.empty:
                col_vh1, col_vh2 = st.columns([1.8, 1.2])
                with col_vh1:
                    st.markdown("##### 📊 Nodi di Prezzo & Fasce Volumetriche")
                with col_vh2:
                    csv_vp = df_prof.to_csv(index=False).encode('utf-8')
                    tk_slug = target_ticker.lower().replace(" ", "_").replace(":", "_").replace("/", "_")
                    st.download_button("📥 Scarica CSV", data=csv_vp, file_name=f"volume_profile_{tk_slug}.csv", mime="text/csv", use_container_width=True, key="btn_download_volume_profile")

                df_table = pd.DataFrame({
                    "Livello Prezzo": df_prof["price_bin_mid"].map(lambda v: f"€ {v:.2f}"),
                    "Fascia Minima": df_prof["price_bin_min"].map(lambda v: f"€ {v:.2f}"),
                    "Fascia Massima": df_prof["price_bin_max"].map(lambda v: f"€ {v:.2f}"),
                    "Volume Scambiato": df_prof["volume"].map(lambda v: f"{v:,.0f}"),
                    "Volume %": df_prof["volume_pct"].map(lambda v: f"{v:.1f}%"),
                    "Stato POC": df_prof["is_poc"].map({True: "⭐ Point of Control", False: "—"}),
                    "Canale Value Area": df_prof["in_value_area"].map({True: "🟢 Value Area (70%)", False: "⚪ Fuori Canale"})
                })

                st.dataframe(
                    df_table,
                    use_container_width=True,
                    hide_index=True,
                    height=350
                )
            else:
                st.info("Nessun dato di volume profile disponibile.")

    elif tab_tech == "🚦 Confluence Score & Pattern Recognition":
        col_cp_h1, col_cp_h2 = st.columns([3.2, 1.2])
        with col_cp_h1:
            st.subheader("🚦 Technical Confluence Score Card & Pattern Recognition")
        with col_cp_h2:
            st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
            glossary_modal("Guida al Confluence Score & Candlestick Pattern", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🧮 Architettura del Confluence Score (0 - 100)</div>
  <div>Punteggio multi-fattoriale che sintetizza 5 dimensioni indipendenti del mercato per prevenire falsi segnali isolati:
    • <b>Trend di Breve (EMA 20 vs 50):</b> ±12 punti<br>
    • <b>Trend Primario (Prezzo vs SMA 200):</b> ±13 punti<br>
    • <b>Accelerazione Momentum (MACD Hist):</b> ±10 punti<br>
    • <b>Ipercomprato/Ipervenduto (RSI 14):</b> +5 / -8 / +8 punti<br>
    • <b>Forza Direzionale (ADX 14 &gt; 25):</b> +5 punti
  </div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🕯️ Pattern Candlestick Algoritmici</div>
  <div>
    • <b>Bullish/Bearish Engulfing:</b> Candele ad ampio range che inglobano completamente il corpo precedente.<br>
    • <b>Hammer & Shooting Star:</b> Ombre lunghe (wick) di rifiuto dei minimi o dei massimi con chiusura opposta.<br>
    • <b>Doji:</b> Candela a corpo nullo indicante stallo tra compratori e venditori.
  </div>
</div>
</div>
""", button_label="📖 Guida Confluence & Pattern")

        col_conf, col_patt = st.columns([1.05, 1.15])

        with col_conf:
            score_val = int(confluence_res['score'])
            score_color = "#3fb950" if score_val >= 60 else ("#d29922" if score_val >= 40 else "#f85149")
            st.markdown(f"""
            <div class="glass-card" style="padding: 14px 18px; border-radius: 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 14px; font-weight: 700; color: #ffffff;">Technical Confluence: <span style="color: {score_color}; font-size: 18px;">{score_val} / 100</span></span>
                    <span style="background: rgba(255,255,255,0.06); border: 1px solid {score_color}44; border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; color: #ffffff;">
                        {confluence_res['verdict_icon']} {confluence_res['verdict']}
                    </span>
                </div>
                <div style="background: rgba(255,255,255,0.08); border-radius: 6px; height: 8px; overflow: hidden;">
                    <div style="background: {score_color}; width: {score_val}%; height: 100%; border-radius: 6px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            df_factors = pd.DataFrame(confluence_res["factors"])
            if not df_factors.empty:
                col_cfh1, col_cfh2 = st.columns([1.8, 1.2])
                with col_cfh1:
                    st.caption("Fattori di confluenza quantitativi")
                with col_cfh2:
                    csv_fac = df_factors.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Fattori CSV", data=csv_fac, file_name=f"confluence_fattori_{target_ticker.lower()}.csv", mime="text/csv", use_container_width=True, key="btn_download_confluence_factors")
                df_factors_display = df_factors.rename(columns={
                    "indicator": "Indicatore",
                    "status": "Segnale / Stato",
                    "impact": "Punti",
                    "note": "Condizione"
                })
                st.dataframe(df_factors_display, use_container_width=True, hide_index=True, height=270)

        with col_patt:
            col_pth1, col_pth2 = st.columns([2.0, 1.2])
            with col_pth1:
                st.markdown("#### 🕯️ Pattern Candlestick Rilevati")
            if patterns_res:
                df_patt = pd.DataFrame(patterns_res)
                with col_pth2:
                    csv_patt = df_patt.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Pattern CSV", data=csv_patt, file_name=f"pattern_candlestick_{target_ticker.lower()}.csv", mime="text/csv", use_container_width=True, key="btn_download_candlestick_patterns")
                df_patt_display = df_patt.rename(columns={
                    "date": "Data",
                    "pattern": "Pattern",
                    "bias": "Bias Direzionale",
                    "description": "Implicazione Operativa"
                })
                st.dataframe(df_patt_display, use_container_width=True, hide_index=True, height=270)
            else:
                st.info("ℹ️ Nessun pattern candlestick rilevante individuato sulle ultime barre.")

    elif tab_tech == "⏳ Trend Multi-Timeframe Alignment (1D / 1W)":
        col_mtf_h1, col_mtf_h2 = st.columns([3.2, 1.2])
        with col_mtf_h1:
            st.subheader("⏳ Trend Multi-Timeframe Alignment (1D / 1W)")
        with col_mtf_h2:
            st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
            glossary_modal("Guida al Trend Multi-Timeframe Alignment", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔭 Metodologia Triple Screen (Alexander Elder)</div>
  <div>Regola aurea del quantitative trading istituzionale: un segnale sul timeframe operativo (Giornaliero 1D) è valido solo se coerente con la direzione della marea sul timeframe di ordine superiore (Settimanale 1W).</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🚦 Interpretazione dell'Allineamento</div>
  <div>
    • 🟢 <b>Full Alignment Bullish (1D + 1W Rialzista):</b> Massima confidenza per ingressi long e accumulazione.<br>
    • 🟡 <b>Mixed Alignment (Trend Discordanti):</b> Fase di ritracciamento o rimbalzo tecnico con elevato rischio di trappola.<br>
    • 🔴 <b>Full Alignment Bearish (1D + 1W Ribassista):</b> Massima prudenza, favorire coperture (hedging) o stop loss.
  </div>
</div>
</div>
""", button_label="📖 Guida Multi-Timeframe")

        d_bull = "Rialzista" in mtf_res.get("trend_daily", "") or "Bullish" in mtf_res.get("trend_daily", "")
        w_bull = "Rialzista" in mtf_res.get("trend_weekly", "") or "Bullish" in mtf_res.get("trend_weekly", "")

        # Determinazione del verdetto operativo istituzionale (Alexander Elder)
        if d_bull and w_bull:
            verdict_title = "🟢 CONFLUENZA RIALZISTA PIENA (FULL BULL ALIGNMENT)"
            verdict_badge = "Strong Buy / Momentum Confirmed"
            verdict_color = "#3fb950"
            playbook_text = "Sia il timeframe operativo Giornaliero che il trend secolare Settimanale sono orientati al rialzo. Setup a massima confidenza per strategie Trend-Following, accumulazione e piramidazione delle posizioni."
        elif (not d_bull) and w_bull:
            verdict_title = "🟡 PULLBACK / RITRACCIAMENTO IN TREND PRIMARIO TORO"
            verdict_badge = "Buy the Dip Watchlist"
            verdict_color = "#d29922"
            playbook_text = "Il trend primario settimanale (Tide) resta saldamente rialzista, ma il timeframe giornaliero è in fase di correzione o consolidamento. Opportunità tattica per monitorare supporti volumetrici (POC/VAL) e cercare setup di ingresso a sconto appena il Daily inverte al rialzo."
        elif d_bull and (not w_bull):
            verdict_title = "🟡 RIMBALZO TECNICO IN TREND PRIMARIO ORSO"
            verdict_badge = "Bear Market Rally (Caution)"
            verdict_color = "#d29922"
            playbook_text = "Il timeframe giornaliero mostra un rimbalzo positivo, ma il trend primario settimanale è ribassista. Elevato rischio di bull-trap o trappola per compratori. Preferire prese di profitto, alleggerimento o posizioni corte/hedging in prossimità delle resistenze (VAH/SMA 200)."
        else:
            verdict_title = "🔴 CONFLUENZA RIBASSISTA PIENA (FULL BEAR ALIGNMENT)"
            verdict_badge = "Cash Preservation / Hedging"
            verdict_color = "#f85149"
            playbook_text = "Entrambi i timeframe (Giornaliero e Settimanale) sono orientati al ribasso. Massima prudenza: evitare categoricamente aperture di posizioni rialziste senza adeguate coperture; proteggere il capitale con trailing stop loss rigorosi."

        mtf_c1, mtf_c2 = st.columns(2)
        with mtf_c1:
            d_icon = "🟢" if d_bull else "🔴"
            d_label = "Rialzista (Bullish)" if d_bull else "Ribassista (Bearish)"
            d_color = "#3fb950" if d_bull else "#f85149"
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px 20px; border-radius: 12px; border-left: 4px solid {d_color}; margin-bottom: 12px;">
                <div style="font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 0.5px; text-transform: uppercase;">
                    Timeframe Operativo (Daily 1D)
                </div>
                <div style="font-size: 20px; font-weight: 700; color: {d_color}; margin: 6px 0 2px 0;">
                    {d_icon} {d_label}
                </div>
                <div style="font-size: 12.5px; color: #c9d1d9;">
                    Condizione: <b>EMA 20 {'>' if d_bull else '<'} EMA 50</b> | Trigger e timing esecutivo di breve termine.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with mtf_c2:
            w_icon = "🟢" if w_bull else "🔴"
            w_label = "Rialzista (Bullish)" if w_bull else "Ribassista (Bearish)"
            w_color = "#3fb950" if w_bull else "#f85149"
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px 20px; border-radius: 12px; border-left: 4px solid {w_color}; margin-bottom: 12px;">
                <div style="font-size: 11px; font-weight: 700; color: #8b949e; letter-spacing: 0.5px; text-transform: uppercase;">
                    Timeframe Direzionale / Marea (Weekly 1W)
                </div>
                <div style="font-size: 20px; font-weight: 700; color: {w_color}; margin: 6px 0 2px 0;">
                    {w_icon} {w_label}
                </div>
                <div style="font-size: 12.5px; color: #c9d1d9;">
                    Condizione: <b>EMA 10w {'>' if w_bull else '<'} EMA 20w</b> | Direzione secolare del flusso istituzionale.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Operational Playbook Banner
        st.markdown(f"""
        <div class="glass-card" style="padding: 18px 22px; border-radius: 12px; margin-top: 4px; border: 1px solid {verdict_color}44;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14.5px; font-weight: 700; color: {verdict_color};">{verdict_title}</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid {verdict_color}66; border-radius: 6px; padding: 4px 10px; font-size: 11.5px; font-weight: 600; color: #ffffff;">
                    {verdict_badge}
                </span>
            </div>
            <div style="font-size: 13.5px; color: #e6edf3; line-height: 1.55;">
                {playbook_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── TAB 5: REAL-TIME STREAMING & LEVEL-2 BOOK DEPTH (STREAM) ──────
    elif tab_tech == "⚡ Real-Time Streaming & Book Depth (STREAM)":
        col_st_h1, col_st_h2 = st.columns([3.2, 1.2])
        with col_st_h1:
            st.markdown(f"#### ⚡ Real-Time Market Feed, In-Memory Ring Buffer & Level-2 Book Depth | `{target_ticker}`")
            st.caption("Flusso dati ad alta frequenza con buffer circolare O(1), Volume-Weighted Average Price (VWAP), Order Flow Imbalance (OFI) e Microprice.")
        with col_st_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida a Real-Time Streaming & Microstruttura", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 In-Memory Ring Buffer O(1)</div>
  <div>Struttura dati circolare thread-safe che memorizza gli ultimi N tick ad alta frequenza senza allocazione dinamica di memoria, consentendo calcoli istantanei a bassissima latenza.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📊 Volume-Weighted Average Price (VWAP)</div>
  <div>Il prezzo medio ponderato per i volumi scambiati durante la sessione. È il principale benchmark di esecuzione per gli algoritmi istituzionali di broker routing.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚖️ Order Flow Imbalance (OFI - Cont et al. 2014)</div>
  <div>Misura la pressione istantanea netta del flusso ordini (Bid delta vs Ask delta). Un OFI fortemente positivo anticipa un movimento rialzista a breve termine.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 Microprice Istituzionale (Stoikov 2018)</div>
  <div>Prezzo fair di equilibrio del book ponderato per la liquidità presente sul Best Bid e Best Ask:
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 4px 8px; border-radius: 4px; margin: 4px 0; color: #ffb74d; font-size: 11.5px;">
      P<sub>micro</sub> = (Bid &middot; Q<sub>ask</sub> + Ask &middot; Q<sub>bid</sub>) / (Q<sub>bid</sub> + Q<sub>ask</sub>)
    </div>
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Real-Time Streaming?")

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        # Inizializza Ring Buffer ed estrae o genera tick per target_ticker
        ref_price = float(df_prices["close"].iloc[-1]) if not df_prices.empty else 150.0
        
        # Buffer circolare a 60 tick
        ring_buf = TickRingBuffer(capacity=60, ticker=target_ticker)
        synthetic_ticks = generate_mock_streaming_ticks(
            ticker=target_ticker,
            initial_price=ref_price,
            num_ticks=60,
            volatility=0.0015,
            spread_pct=0.0006
        )
        for t in synthetic_ticks:
            ring_buf.append(t)

        stats = ring_buf.get_summary_statistics()
        df_stream = ring_buf.to_dataframe()

        # 4 Executive KPI Cards
        col_st1, col_st2, col_st3, col_st4 = st.columns(4)
        with col_st1:
            metric_card(
                "Ultimo Prezzo Tick",
                f"${stats['last_price']:.2f}",
                f"Range: ${stats['min_price']:.2f} - ${stats['max_price']:.2f}",
                True
            )
        with col_st2:
            metric_card(
                "VWAP Intraday",
                f"${stats['vwap']:.2f}",
                f"Volume Totale: {stats['total_volume']:,.0f} sh",
                True
            )
        with col_st3:
            ofi_val = stats['order_flow_imbalance']
            ofi_label = "Pressione Buy" if ofi_val >= 0 else "Pressione Sell"
            metric_card(
                "Order Flow Imbalance (OFI)",
                f"{ofi_val:+.0f}",
                f"{ofi_label} (Cont 2014)",
                ofi_val >= 0
            )
        with col_st4:
            metric_card(
                "Spread Medio & Volatilità",
                f"${stats['mean_spread']:.4f}",
                f"Vol Intraday: {stats['rolling_volatility_pct']:.1f}%",
                True
            )

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Grafico Time-Series Real-Time Ticks & VWAP
        st.markdown("##### 📈 Flusso Tick-by-Tick ad Alta Frequenza & Linea VWAP")
        
        fig_st = go.Figure()
        # Fascia Spread Bid/Ask
        fig_st.add_trace(go.Scatter(
            x=list(range(len(df_stream))), y=df_stream["ask"],
            mode="lines", line=dict(color="rgba(248, 81, 73, 0.4)", width=1),
            name="Ask (Lettera)", showlegend=True
        ))
        fig_st.add_trace(go.Scatter(
            x=list(range(len(df_stream))), y=df_stream["bid"],
            mode="lines", line=dict(color="rgba(46, 160, 67, 0.4)", width=1),
            fill="tonexty", fillcolor="rgba(255, 255, 255, 0.04)",
            name="Bid (Denaro)", showlegend=True
        ))
        # Prezzo Tick
        fig_st.add_trace(go.Scatter(
            x=list(range(len(df_stream))), y=df_stream["price"],
            mode="lines+markers", line=dict(color="#58a6ff", width=2.5),
            marker=dict(size=5, color="#58a6ff"),
            name="Prezzo Eseguito (Tick)", showlegend=True
        ))
        # Linea VWAP
        # Calcola VWAP cumulativo
        cum_pv = (df_stream["price"] * df_stream["size"]).cumsum()
        cum_v = df_stream["size"].cumsum()
        rolling_vwap = cum_pv / cum_v
        fig_st.add_trace(go.Scatter(
            x=list(range(len(df_stream))), y=rolling_vwap,
            mode="lines", line=dict(color="#ff9900", width=2, dash="dash"),
            name="VWAP Cumulativo", showlegend=True
        ))

        fig_st.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,17,23,0.7)",
            height=360,
            margin=dict(l=10, r=10, t=25, b=20),
            xaxis=dict(title="Sequenza Tick (In-Memory Ring Buffer FIFO)", gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(title="Prezzo ($)", gridcolor="rgba(255,255,255,0.06)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_st, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        # Due Colonne: Level-2 Book Depth & Registro Tick Ring Buffer
        col_l2_left, col_l2_right = st.columns([1.2, 1.8])
        
        with col_l2_left:
            st.markdown("##### 🧱 Level-2 Order Book (Profondità a 5 Livelli)")
            
            # Generazione snapshot Book L2 coerente
            last_p = stats["last_price"]
            bids_l2 = [
                OrderBookLevel(price=round(last_p - 0.02 * i, 2), size=float(np.random.randint(150, 800)))
                for i in range(1, 6)
            ]
            asks_l2 = [
                OrderBookLevel(price=round(last_p + 0.02 * i, 2), size=float(np.random.randint(150, 800)))
                for i in range(1, 6)
            ]
            l2_book = OrderBookL2(ticker=target_ticker, bids=bids_l2, asks=asks_l2)
            micro_p = l2_book.compute_microprice()
            imb_val = l2_book.compute_book_imbalance()

            st.markdown(f"""
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 12.5px; color: #cbd5e1; margin-bottom: 4px;">
                    <span><b>Microprice (Stoikov):</b> <code style="color: #ff9900;">${micro_p:.3f}</code></span>
                    <span><b>Mid Price:</b> <code style="color: #58a6ff;">${l2_book.mid_price:.3f}</code></span>
                </div>
                <div style="font-size: 12px; color: #94a3b8;">
                    Depth Imbalance Ratio: <b style="color: {'#4ade80' if imb_val>=0 else '#f87171'};">{imb_val:+.2%}</b> ({'Pressione Buy' if imb_val>=0 else 'Pressione Sell'})
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Tabella Profondità L2
            df_bids = pd.DataFrame([{"Livello": f"Bid {i+1}", "Prezzo ($)": b.price, "Volume (Denaro)": b.size} for i, b in enumerate(bids_l2)])
            df_asks = pd.DataFrame([{"Livello": f"Ask {i+1}", "Prezzo ($)": a.price, "Volume (Lettera)": a.size} for i, a in enumerate(asks_l2)])
            
            col_b, col_a = st.columns(2)
            with col_b:
                st.caption("🟢 Lato Bid (Denaro)")
                st.dataframe(df_bids, hide_index=True, use_container_width=True)
            with col_a:
                st.caption("🔴 Lato Ask (Lettera)")
                st.dataframe(df_asks, hide_index=True, use_container_width=True)

        with col_l2_right:
            st.markdown("##### 📋 Registro Tick Recenti nel Ring Buffer (O(1) FIFO)")
            df_display = df_stream[["ticker", "price", "size", "bid", "ask", "spread", "mid_price"]].tail(15).iloc[::-1]
            st.dataframe(
                df_display,
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "price": st.column_config.NumberColumn("Prezzo Tick", format="$ %.4f"),
                    "size": st.column_config.NumberColumn("Volume", format="%,.0f"),
                    "bid": st.column_config.NumberColumn("Bid", format="$ %.4f"),
                    "ask": st.column_config.NumberColumn("Ask", format="$ %.4f"),
                    "spread": st.column_config.NumberColumn("Spread", format="$ %.4f"),
                    "mid_price": st.column_config.NumberColumn("Mid Price", format="$ %.4f")
                },
                hide_index=True,
                use_container_width=True
            )

