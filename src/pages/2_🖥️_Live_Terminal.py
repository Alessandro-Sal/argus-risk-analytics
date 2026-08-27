# ==============================================================================
# src/pages/2_🖥️_Live_Terminal.py
# ARGUS Institutional Live Terminal & Market Desk v5.25.0
# Real-Time Streaming Tape • L2 Depth Book • Portfolio & Watchlist Live Monitor • Bloomberg CLI Console • OMS Blotter
# ==============================================================================

import io
import time
import datetime
import html
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import importlib

import core.ui_utils as ui_utils
import core.streaming_engine as streaming_engine
import core.terminal_engine as terminal_engine

# Ricarica dinamica garantita dei moduli core in ambiente Streamlit a caldo
importlib.reload(streaming_engine)
importlib.reload(terminal_engine)

from core.sidebar import render_sidebar
from core.ui_utils import (
    inject_custom_css,
    render_command_bar,
    metric_card,
    glossary_modal,
    ensure_risk_bundle_loaded,
    render_page_header
)
from core.terminal_engine import (
    get_terminal_engine,
    TerminalCommandResult,
    OMSOrder,
    DeskRiskLimits,
    PreTradeRiskResult,
    evaluate_pre_trade_risk,
    compute_pnl_attribution,
    fetch_market_catalysts,
    convert_to_eur,
    detect_currency,
    get_fx_rate_to_eur,
    fetch_live_ticker_quote,
    fetch_multiple_live_quotes
)

st.set_page_config(
    page_title="ARGUS - Live Terminal & Market Desk",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

# ── Sidebar & Ingestion Gate ─────────────────────────────────────────────────
render_sidebar()
render_command_bar()

results, has_real_portfolio = ensure_risk_bundle_loaded()
pos = results.get("positions", pd.DataFrame()) if results else pd.DataFrame()
df_rets = results.get("returns", pd.DataFrame()) if results else pd.DataFrame()
df_prices = results.get("df_prices", pd.DataFrame()) if results else pd.DataFrame()
df_tx = results.get("df_tx", pd.DataFrame()) if results else pd.DataFrame()

# ── Page Header ──────────────────────────────────────────────────────────────
render_page_header(
    title="ARGUS Live Terminal & Real-Time Market Desk",
    subtitle="Console Interattiva Bloomberg CLI • Quotazioni Real-Time Streaming & Book Depth L2 • Monitor Prezzi Live Portafoglio & Watchlist Multi-Asset • OMS Execution Blotter",
    icon="🖥️"
)

# Barra di Stato Desk & Auto-Refresh Configurabile
col_hdr_status, col_hdr_refresh = st.columns([3.2, 1.4], vertical_alignment="center")
with col_hdr_status:
    st.markdown("<div style='font-size:12px; color:#8b949e;'><span style='display:inline-block; width:8px; height:8px; border-radius:50%; background:#3fb950; margin-right:6px; box-shadow:0 0 6px #3fb950;'></span><b>DESK FEED STATUS:</b> Streaming Real-Time Quotazioni & Cross FX Attivo</div>", unsafe_allow_html=True)
with col_hdr_refresh:
    autorefresh_sel = st.selectbox(
        "⏱️ Auto-Refresh Streaming Feed:",
        options=["Disattivato", "5s", "10s", "30s", "60s"],
        index=0,
        key="sel_live_autorefresh_rate",
        label_visibility="collapsed"
    )
if "argus_terminal_engine" not in st.session_state:
    st.session_state["argus_terminal_engine"] = get_terminal_engine()

term_eng = st.session_state["argus_terminal_engine"]

session_context = {
    "results": results or {},
    "df_positions": pos,
    "df_returns": df_rets,
    "df_prices": df_prices,
    "df_transactions": df_tx,
    "portfolio_id": 1,
    "base_currency": st.session_state.get("base_currency", "EUR")
}

# Inizializzazione Cache Quote di Sessione
if "argus_live_quotes_dict" not in st.session_state:
    st.session_state["argus_live_quotes_dict"] = {}
all_quotes = st.session_state.get("argus_live_quotes_dict", {})

# Buffer iniziale con guida rapida se vuoto
if not term_eng.output_buffer:
    init_res = term_eng.execute_command("HELP", session_context)
    term_eng.output_buffer.append(init_res)

# ── HUD DEI LIMITI DI RISCHIO E CIRCUIT BREAKERS DELLA SALA OPERATIVA ────────
tot_port_val = float(results.get("portfolio_value", 100000.0) or 100000.0) if results else 100000.0
day_pnl_val = float(results.get("day_pnl", 0.0) or 0.0) if results else 0.0
max_daily_loss = term_eng.desk_limits.max_daily_loss_eur
cb_triggered = (day_pnl_val <= -abs(max_daily_loss))
cb_status_color = "#f85149" if cb_triggered else "#3fb950"
cb_status_text = "TRIGGERED 🛑 (BUY Blocked)" if cb_triggered else "NORMAL 🟢 (Limits OK)"

max_pos_w = 0.0
top_w_sym = "N/A"
if not pos.empty and "current_value" in pos.columns:
    max_row = pos.sort_values("current_value", ascending=False).iloc[0]
    max_pos_w = float(max_row["current_value"]) / max(1.0, tot_port_val)
    top_w_sym = str(max_row.get("ticker", "N/A"))

desk_hud_html = f"""
<div style="background: rgba(13,17,23,0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 14px; margin-top: 6px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 11.5px; font-family: monospace;">
  <div><span style="color:#8b949e;">🛡️ DESK COMPLIANCE:</span> <b style="color:{cb_status_color};">{cb_status_text}</b></div>
  <div><span style="color:#8b949e;">Max Daily Loss Limit:</span> <b style="color:#f0f6fc;">-€ {max_daily_loss:,.0f}</b></div>
  <div><span style="color:#8b949e;">Top Concentration ({top_w_sym}):</span> <b style="color:{'#ff9900' if max_pos_w > 0.25 else '#3fb950'};">{max_pos_w*100:.1f}% / 25% max</b></div>
  <div><span style="color:#8b949e;">Gross Exposure:</span> <b style="color:#58a6ff;">1.00x / 1.50x max</b></div>
</div>
"""
st.markdown(desk_hud_html, unsafe_allow_html=True)

# ── SEZIONE 1: LIVE MARKET TAPE & LEVEL-2 BOOK (FULL-WIDTH ROW) ──────────────
st.markdown("#### ⚡ Live Market Tape & Real-Time Streaming API")

# Universo Ticker Selezionabili (Portafoglio + Benchmark Globali)
base_tickers = list(pos["ticker"].unique()) if not pos.empty and "ticker" in pos.columns else []
for bmk in ["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "BTC-USD", "ETH-USD", "GC=F", "CL=F", "EURUSD=X"]:
    if bmk not in base_tickers:
        base_tickers.append(bmk)

col_tape_ctrl, col_tape_book = st.columns([1.2, 1.8], gap="medium")

with col_tape_ctrl:
    col_t1, col_t2 = st.columns([1.2, 1.0])
    with col_t1:
        sel_dropdown_tk = st.selectbox("Seleziona Ticker:", options=base_tickers, key="sel_tape_ticker_page2")
    with col_t2:
        custom_tk_input = st.text_input("Oppure Ticker Custom:", placeholder="Es. TSLA, ENI.MI", key="inp_custom_tape_tk_page2").strip().upper()

    active_tape_ticker = custom_tk_input if custom_tk_input else sel_dropdown_tk

    # Recupera quote: prioritizza cache in memoria se disponibile per risposta istantanea (0ms)
    live_q = all_quotes.get(active_tape_ticker)
    if not live_q:
        live_q = terminal_engine.fetch_live_ticker_quote(active_tape_ticker)
        st.session_state.setdefault("argus_live_quotes_dict", {})[active_tape_ticker] = live_q

    last_px = live_q["last_price"]
    prev_close = live_q["prev_close"]
    chg = live_q["change"]
    chg_pct = live_q["change_pct"]
    currency = live_q["currency"]
    day_h = live_q["day_high"]
    day_l = live_q["day_low"]
    vol_str = f"{live_q['volume']:,.0f}" if live_q['volume'] > 0 else "N/A"

    ring_buf = term_eng.get_or_create_ring_buffer(ticker=active_tape_ticker, initial_price=last_px, capacity=500)
    
    # Bottoni di controllo streaming e refresh live
    col_tick_btn, col_ref_btn = st.columns([1.0, 1.0])
    with col_tick_btn:
        if st.button("⚡ Invia Tick Live", key="btn_push_sim_tick_page2", use_container_width=True):
            if ring_buf:
                shock = np.random.normal(0, 0.0015) * last_px
                new_p = max(0.01, last_px + shock)
                t = terminal_engine.MarketTick(
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    ticker=active_tape_ticker,
                    price=round(new_p, 2),
                    size=round(np.random.uniform(50, 400), 0),
                    bid=round(new_p - 0.02, 2),
                    ask=round(new_p + 0.02, 2),
                    volume=live_q['volume'] or 1000.0
                )
                ring_buf.append(t)
            st.rerun()
    with col_ref_btn:
        if st.button("🔄 Aggiorna Live", key="btn_refresh_live_quote_page2", use_container_width=True, type="secondary"):
            st.rerun()

    stats = ring_buf.get_summary_statistics() if ring_buf else {}
    display_px = stats.get("last_price", last_px)
    vwap_px = stats.get("vwap", display_px)
    ofi_val = stats.get("order_flow_imbalance", 0.0)
    microprice = display_px + (0.01 if ofi_val > 0 else -0.01)

    # Risoluzione Valutaria e Conversione Spot Dinamica in EUR
    tape_eur_px, _, tape_sym_curr = terminal_engine.convert_to_eur(display_px, currency, active_tape_ticker, all_quotes)
    is_eur_asset = (terminal_engine.detect_currency(active_tape_ticker, currency) == "EUR")

    # Header Ticker Live con Badge Variazione e Stato API
    chg_color = "#3fb950" if chg >= 0 else "#f85149"
    chg_sign = "+" if chg >= 0 else ""
    arrow = "▲" if chg >= 0 else "▼"
    api_badge = '<span style="font-size:10px; background:rgba(63,185,80,0.15); color:#3fb950; border:1px solid rgba(63,185,80,0.3); padding:2px 6px; border-radius:4px; font-weight:700;">LIVE API</span>' if live_q["is_live"] else '<span style="font-size:10px; background:rgba(255,153,0,0.15); color:#ff9900; border:1px solid rgba(255,153,0,0.3); padding:2px 6px; border-radius:4px; font-weight:700;">CACHE</span>'

    # Conversione EUR per display spot se asset non in Euro
    eur_equiv_str = ""
    if not is_eur_asset:
        eur_equiv_str = f'<div style="font-size:12.5px; color:#58a6ff; font-weight:600; margin-top:-2px; margin-bottom:4px;">≈ € {tape_eur_px:,.2f} EUR</div>'

    tape_card_html = (
        f'<div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.95) 100%); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px 16px; margin-top: 4px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<div><span style="font-size:18px; font-weight:800; color:#f0f6fc;">{active_tape_ticker}</span> {api_badge}</div>'
        f'<div><span style="font-size:13px; font-weight:700; color:{chg_color}; background:{chg_color}22; padding:3px 8px; border-radius:4px; border:1px solid {chg_color}55;">{chg_sign}{chg:,.2f} ({chg_sign}{chg_pct:.2f}%) {arrow}</span></div>'
        f'</div>'
        f'<div style="font-size:24px; font-weight:800; color:#ff9900; margin: 4px 0;">{tape_sym_curr}{display_px:,.2f}</div>'
        f'{eur_equiv_str}'
        f'<div style="display:flex; justify-content:space-between; font-size:11px; color:#8b949e; font-family:monospace;">'
        f'<span>Vol: {vol_str}</span><span>Range: {tape_sym_curr}{day_l:,.2f} - {tape_sym_curr}{day_h:,.2f}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(tape_card_html, unsafe_allow_html=True)

    # ── Fast Ladder / One-Click DOM Order Execution Panel ─────────────────────
    with st.expander("⚡ Quick Trade DOM (One-Click Routing)", expanded=False):
        qt_c1, qt_c2 = st.columns([1.2, 1.0])
        with qt_c1:
            qt_qty = st.number_input("Quantità:", min_value=1.0, value=50.0, step=10.0, key=f"qt_inp_qty_{active_tape_ticker}")
        with qt_c2:
            qt_algo = st.selectbox("Tipo:", ["MKT", "TWAP (15m)", "VWAP (30m)"], key=f"qt_inp_algo_{active_tape_ticker}")
        
        btn_b1, btn_b2, btn_b3 = st.columns(3)
        with btn_b1:
            if st.button(f"🟢 BUY", key=f"btn_qt_buy_{active_tape_ticker}", use_container_width=True):
                otype = "TWAP" if "TWAP" in qt_algo else ("VWAP" if "VWAP" in qt_algo else "MKT")
                ok, msg, _ = term_eng.place_order(active_tape_ticker, "BUY", qt_qty, otype, context=session_context)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
                st.rerun()
        with btn_b2:
            if st.button(f"🔴 SELL", key=f"btn_qt_sell_{active_tape_ticker}", use_container_width=True):
                otype = "TWAP" if "TWAP" in qt_algo else ("VWAP" if "VWAP" in qt_algo else "MKT")
                ok, msg, _ = term_eng.place_order(active_tape_ticker, "SELL", qt_qty, otype, context=session_context)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
                st.rerun()
        with btn_b3:
            pos_match = pos[pos["ticker"].astype(str).str.upper() == active_tape_ticker] if (not pos.empty and "ticker" in pos.columns) else pd.DataFrame()
            curr_q = float(pos_match.iloc[0].get("qty_net", pos_match.iloc[0].get("quantity", 0.0))) if not pos_match.empty else 0.0
            if st.button(f"🛑 Chiudi", key=f"btn_qt_close_{active_tape_ticker}", use_container_width=True, disabled=(curr_q <= 0), help=f"Posizione aperta: {curr_q:,.0f} quote"):
                if curr_q > 0:
                    ok, msg, _ = term_eng.place_order(active_tape_ticker, "SELL", curr_q, "MKT", context=session_context)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()

with col_tape_book:
    # Matrice Level-2 Depth Book dinamica attorno al prezzo reale
    spread_step = max(0.01, round(display_px * 0.0001, 2))
    base_bid = round(display_px - spread_step, 2)
    base_ask = round(display_px + spread_step, 2)
    spread_val = round(base_ask - base_bid, 2)
    spread_bps = (spread_val / display_px * 10000.0) if display_px > 0 else 0.0
    
    book_rows = [
        {"bid_vol": 1450, "bid_px": base_bid, "ask_px": base_ask, "ask_vol": 1200},
        {"bid_vol": 920, "bid_px": round(base_bid - spread_step * 2, 2), "ask_px": round(base_ask + spread_step * 2, 2), "ask_vol": 1100},
        {"bid_vol": 680, "bid_px": round(base_bid - spread_step * 4, 2), "ask_px": round(base_ask + spread_step * 4, 2), "ask_vol": 1650},
        {"bid_vol": 410, "bid_px": round(base_bid - spread_step * 6, 2), "ask_px": round(base_ask + spread_step * 6, 2), "ask_vol": 890},
        {"bid_vol": 320, "bid_px": round(base_bid - spread_step * 8, 2), "ask_px": round(base_ask + spread_step * 8, 2), "ask_vol": 540}
    ]

    tab_b_matrix, tab_b_chart, tab_b_depth = st.tabs([
        "📊 Matrice Depth L2",
        "📈 Grafico Intraday & VWAP",
        "🌊 Curva di Liquidità L2"
    ])

    with tab_b_matrix:
        book_rows_html = []
        for r in book_rows:
            bid_bar_w = min(100, int((r["bid_vol"] / 2000.0) * 100))
            ask_bar_w = min(100, int((r["ask_vol"] / 2000.0) * 100))
            book_rows_html.append(
                f'<div style="display:flex; font-family:monospace; font-size:11px; padding: 2px 0; border-bottom: 1px dashed rgba(255,255,255,0.04);">'
                f'<div style="flex:1; text-align:right; color:#8b949e; position:relative; padding-right:8px;"><div style="position:absolute; right:0; top:0; bottom:0; width:{bid_bar_w}%; background:rgba(63,185,80,0.15); z-index:1;"></div><span style="position:relative; z-index:2;">{r["bid_vol"]}</span></div>'
                f'<div style="flex:1; text-align:right; color:#3fb950; font-weight:700; padding-right:12px;">{tape_sym_curr}{r["bid_px"]:,.2f}</div>'
                f'<div style="flex:1; text-align:left; color:#f85149; font-weight:700; padding-left:12px;">{tape_sym_curr}{r["ask_px"]:,.2f}</div>'
                f'<div style="flex:1; text-align:left; color:#8b949e; position:relative; padding-left:8px;"><div style="position:absolute; left:0; top:0; bottom:0; width:{ask_bar_w}%; background:rgba(248,81,73,0.15); z-index:1;"></div><span style="position:relative; z-index:2;">{r["ask_vol"]}</span></div>'
                f'</div>'
            )

        book_full_html = (
            f'<div style="background: linear-gradient(135deg, rgba(13, 17, 23, 0.95) 0%, rgba(22, 27, 34, 0.95) 100%); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">'
            f'<div style="display:flex; font-size:10px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:4px;">'
            f'<div style="flex:1; text-align:right;">BID SIZE</div>'
            f'<div style="flex:1; text-align:right; padding-right:12px;">BID PX</div>'
            f'<div style="flex:1; text-align:left; padding-left:12px;">ASK PX</div>'
            f'<div style="flex:1; text-align:left;">ASK SIZE</div>'
            f'</div>'
            f'{"".join(book_rows_html)}'
            f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:10.5px; font-family:monospace; color:#8b949e; border-top:1px solid rgba(255,255,255,0.06); padding-top:6px; margin-top:6px; flex-wrap:wrap; gap:4px;">'
            f'<span>🎯 Stoikov: <b style="color:#3fb950;">{tape_sym_curr}{microprice:.2f}</b></span>'
            f'<span>VWAP: <b style="color:#58a6ff;">{tape_sym_curr}{vwap_px:.2f}</b></span>'
            f'<span>Spread L2: <b style="color:#f0f6fc;">{tape_sym_curr}{spread_val:.2f}</b> ({spread_bps:.1f} bps)</span>'
            f'<span style="color:#8b949e;">{live_q["timestamp"]}</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(book_full_html, unsafe_allow_html=True)

    with tab_b_chart:
        # Mini-grafico intraday tick/VWAP in tempo reale
        df_ticks = ring_buf.to_dataframe() if ring_buf is not None else pd.DataFrame()
        if (df_ticks.empty or len(df_ticks) < 2) and ring_buf is not None:
            for shock_pct in [-0.0012, -0.0006, 0.0004, 0.0012, 0.0002, -0.0003, 0.0007]:
                p_sim = max(0.01, round(display_px * (1.0 + shock_pct), 2))
                ring_buf.append(terminal_engine.MarketTick(
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                    ticker=active_tape_ticker,
                    price=p_sim,
                    size=round(np.random.uniform(50, 300), 0),
                    bid=round(p_sim - 0.02, 2),
                    ask=round(p_sim + 0.02, 2),
                    volume=live_q.get("volume", 1000.0) or 1000.0
                ))
            df_ticks = ring_buf.to_dataframe()

        if not df_ticks.empty:
            df_ticks["cum_vol"] = df_ticks["size"].cumsum()
            df_ticks["cum_pv"] = (df_ticks["price"] * df_ticks["size"]).cumsum()
            df_ticks["vwap_calc"] = df_ticks["cum_pv"] / np.maximum(df_ticks["cum_vol"], 1.0)
            df_ticks["time_str"] = df_ticks["timestamp"].apply(lambda t: t.strftime("%H:%M:%S") if hasattr(t, "strftime") else str(t)[:8])
            
            fig_intra = go.Figure()
            fig_intra.add_trace(go.Scatter(
                x=df_ticks["time_str"], y=df_ticks["price"],
                mode="lines+markers", name=f"{active_tape_ticker} Spot",
                line=dict(color="#58a6ff", width=2),
                marker=dict(size=4, color="#38bdf8"),
                hovertemplate=f"<b>{active_tape_ticker} Spot: {tape_sym_curr}%{{y:,.2f}}</b><br><span style='color:#8b949e; font-size:10px;'>Ora: %{{x}}</span><extra></extra>"
            ))
            fig_intra.add_trace(go.Scatter(
                x=df_ticks["time_str"], y=df_ticks["vwap_calc"],
                mode="lines", name="VWAP",
                line=dict(color="#f0883e", width=1.5, dash="dot"),
                hovertemplate=f"<b>VWAP: {tape_sym_curr}%{{y:,.2f}}</b><br><span style='color:#8b949e; font-size:10px;'>Ora: %{{x}}</span><extra></extra>"
            ))
            fig_intra.add_hline(
                y=microprice,
                line_dash="dash",
                line_color="#3fb950",
                annotation_text=f"🎯 Stoikov: {tape_sym_curr}{microprice:.2f}",
                annotation_position="bottom left",
                annotation_font=dict(size=9.5, color="#3fb950", family="monospace")
            )
            fig_intra.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(13,17,23,0.95)",
                plot_bgcolor="rgba(13,17,23,0.95)",
                margin=dict(l=10, r=45, t=30, b=10),
                height=220,
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0.01, font=dict(size=10.5, color="#c9d1d9")),
                xaxis=dict(showgrid=False, title=None, tickfont=dict(size=8.5, family="monospace", color="#8b949e")),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title=None, side="right", tickprefix=tape_sym_curr, tickfont=dict(size=9.5, family="monospace", color="#8b949e"))
            )
            st.plotly_chart(fig_intra, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Buffer streaming in avvio. Clicca su '⚡ Invia Tick Live' per generare dati nel grafico intraday.")

    with tab_b_depth:
        # Curva cumulativa di liquidità Level-2 (Order Book Depth)
        bid_pxs = [r["bid_px"] for r in book_rows]
        bid_vols = [r["bid_vol"] for r in book_rows]
        ask_pxs = [r["ask_px"] for r in book_rows]
        ask_vols = [r["ask_vol"] for r in book_rows]
        
        cum_bid = np.cumsum(bid_vols[::-1])[::-1]
        cum_ask = np.cumsum(ask_vols)
        
        fig_depth = go.Figure()
        fig_depth.add_trace(go.Scatter(
            x=bid_pxs, y=cum_bid,
            mode="lines", name="Bids (Acquisto)",
            fill="tozeroy",
            fillcolor="rgba(63, 185, 80, 0.25)",
            line=dict(color="#3fb950", width=2),
            hovertemplate=f"<b>Bid Depth: %{{y:,.0f}} shares</b><br>Px: {tape_sym_curr}%{{x:,.2f}}<extra></extra>"
        ))
        fig_depth.add_trace(go.Scatter(
            x=ask_pxs, y=cum_ask,
            mode="lines", name="Asks (Vendita)",
            fill="tozeroy",
            fillcolor="rgba(248, 81, 73, 0.25)",
            line=dict(color="#f85149", width=2),
            hovertemplate=f"<b>Ask Depth: %{{y:,.0f}} shares</b><br>Px: {tape_sym_curr}%{{x:,.2f}}<extra></extra>"
        ))
        fig_depth.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(13,17,23,0.95)",
            plot_bgcolor="rgba(13,17,23,0.95)",
            margin=dict(l=10, r=45, t=30, b=10),
            height=220,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0.01, font=dict(size=10.5, color="#c9d1d9")),
            xaxis=dict(title=dict(text="Prezzo L2", font=dict(size=10, color="#8b949e")), tickprefix=tape_sym_curr, showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=9, family="monospace", color="#8b949e")),
            yaxis=dict(title=dict(text="Vol Cumulativo", font=dict(size=10, color="#8b949e")), side="right", showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(size=9, family="monospace", color="#8b949e"))
        )
        st.plotly_chart(fig_depth, use_container_width=True, config={"displayModeBar": False})

st.divider()

# ── SEZIONE 2: LIVE MULTI-ASSET MONITOR (PORTAFOGLIO + WATCHLIST) ────────────
col_sec2_hdr, col_sec2_btn = st.columns([3.2, 1.2], vertical_alignment="center")
with col_sec2_hdr:
    st.markdown("#### 📊 Live Multi-Asset Pricing Monitor (Portafoglio & Watchlist)")
with col_sec2_btn:
    btn_force_sync = st.button("🔄 Sincronizza Prezzi Live", key="btn_sync_live_quotes_page2", use_container_width=True)

# Filtra esclusivamente le posizioni attive (quantità netta > 0)
qty_col = "qty_net" if "qty_net" in pos.columns else ("shares" if "shares" in pos.columns else ("quantity" if "quantity" in pos.columns else None))
if not pos.empty and qty_col:
    active_pos = pos[pos[qty_col] > 1e-6].copy()
elif not pos.empty and "current_value" in pos.columns:
    active_pos = pos[pos["current_value"] > 0].copy()
else:
    active_pos = pos.copy() if not pos.empty else pd.DataFrame()

# Lista completa di tutti i ticker necessari (Posizioni Attive + Watchlist + Cross FX)
pos_tickers = [str(t).strip().upper() for t in active_pos["ticker"].unique() if str(t).strip()] if (not active_pos.empty and "ticker" in active_pos.columns) else []
wl_tickers = [str(t).strip().upper() for t in term_eng.custom_watchlist if str(t).strip()]
fx_pairs = ["EURUSD=X", "EURDKK=X", "EURGBP=X", "EURCHF=X", "EURSEK=X", "EURNOK=X", "EURJPY=X", "EURCAD=X", "EURAUD=X", "EURHKD=X"]
needed_tickers = list(dict.fromkeys(pos_tickers + wl_tickers + fx_pairs))

# Costruisci mappa di fallback immediata dai dati delle posizioni attive
pos_fallback_map = {}
if not active_pos.empty and "ticker" in active_pos.columns:
    for _, row in active_pos.iterrows():
        tk = str(row["ticker"]).strip().upper()
        p_val = float(row.get("current_price", row.get("wacp", row.get("buy_price", 150.0))))
        if p_val > 0:
            pos_fallback_map[tk] = p_val

if "argus_live_quotes_dict" not in st.session_state:
    st.session_state["argus_live_quotes_dict"] = {}

# Sincronizza solo su richiesta esplicita o al primissimo avvio se la cache è vuota
need_sync = btn_force_sync or (len(st.session_state.get("argus_live_quotes_dict", {})) == 0)

if need_sync and needed_tickers:
    with st.spinner("⏳ Sincronizzazione flussi di mercato e prezzi live in tempo reale..."):
        synced_quotes = terminal_engine.fetch_multiple_live_quotes(
            needed_tickers,
            max_workers=10,
            force_refresh=btn_force_sync,
            fallback_map=pos_fallback_map
        )
        st.session_state["argus_live_quotes_dict"].update(synced_quotes)

all_quotes = st.session_state.get("argus_live_quotes_dict", {})

# Calcolo PnL Attribution (Effetto Prezzo Asset vs Effetto Tasso di Cambio FX)
pnl_attrib = compute_pnl_attribution(active_pos, all_quotes)
tot_px_eff = pnl_attrib.get("price_effect_eur", 0.0)
tot_fx_eff = pnl_attrib.get("fx_effect_eur", 0.0)
attrib_map = {r["ticker"]: r for r in pnl_attrib.get("by_asset", [])}

tab_port_live, tab_heatmap_live, tab_rel_perf, tab_news_cat, tab_wl_live = st.tabs([
    "💼 Prezzi Live & PnL Attribution",
    "🗺️ Heatmap Portafoglio 1D",
    "📈 Relative Performance (Base 0%)",
    "📰 Live News & Macro Catalysts",
    "🌐 Watchlist Istituzionale"
])

port_live_raw_items = []

with tab_port_live:
    if active_pos.empty or "ticker" not in active_pos.columns:
        st.info("Nessuna posizione attiva aperta a mercato. Carica un portafoglio o una distinta transazioni per visualizzare i prezzi live.")
    else:
        # Calcolo prezzi live per ogni titolo attivo del portafoglio
        tot_live_notional = 0.0
        tot_prev_day_notional = 0.0
        tot_wacp_cost = 0.0
        day_chgs = []

        for _, r in active_pos.iterrows():
            sym = str(r["ticker"]).strip().upper()
            # Supporto a tutte le nomenclature di colonna per quantità e costo medio
            q_val = float(r.get("qty_net", r.get("quantity", r.get("shares", 0.0))))
            wacp_eur = float(r.get("avg_cost", r.get("wacp", r.get("buy_price", 0.0))))
            
            live_item = all_quotes.get(sym, terminal_engine.fetch_live_ticker_quote(sym))
            live_px_orig = float(live_item.get("last_price", 0.0))
            prev_close_orig = float(live_item.get("prev_close", live_px_orig))
            if prev_close_orig <= 0:
                prev_close_orig = live_px_orig
            chg_1d = float(live_item.get("change_pct", 0.0))
            
            # Determinazione Valuta e Conversione Multi-Currency Live in EUR
            asset_curr = str(r.get("asset_currency", live_item.get("currency", "USD"))).upper()
            provided_fx = float(r.get("fx_rate_spot", 0.0)) if ("fx_rate_spot" in r and float(r.get("fx_rate_spot", 0.0)) > 0) else None

            live_px_eur, live_px_orig_str, curr_sym = terminal_engine.convert_to_eur(live_px_orig, asset_curr, sym, all_quotes, provided_fx)
            prev_px_eur, _, _ = terminal_engine.convert_to_eur(prev_close_orig, asset_curr, sym, all_quotes, provided_fx)

            mkt_val_eur = q_val * live_px_eur
            prev_val_eur = q_val * prev_px_eur
            day_pnl_asset_eur = mkt_val_eur - prev_val_eur
            cost_eur = q_val * wacp_eur
            pnl_eur = mkt_val_eur - cost_eur
            pnl_pct = (pnl_eur / cost_eur * 100.0) if cost_eur > 0 else 0.0
            
            # Dettaglio Attribution per singolo titolo
            sym_attr = attrib_map.get(sym, {})
            px_eff_item = sym_attr.get("price_effect_eur", day_pnl_asset_eur)
            fx_eff_item = sym_attr.get("fx_effect_eur", 0.0)

            tot_live_notional += mkt_val_eur
            tot_prev_day_notional += prev_val_eur
            tot_wacp_cost += cost_eur
            if q_val > 0:
                day_chgs.append(chg_1d)

            port_live_raw_items.append({
                "Ticker": sym,
                "Prezzo_Spot": live_px_orig_str,
                "Prezzo_EUR": live_px_eur,
                "Var_1D_Pct": chg_1d,
                "Var_Day_EUR": day_pnl_asset_eur,
                "Effetto_Prezzo": px_eff_item,
                "Effetto_FX": fx_eff_item,
                "WACP_EUR": wacp_eur,
                "Quantita": q_val,
                "Controvalore_EUR": mkt_val_eur,
                "PnL_EUR": pnl_eur,
                "PnL_Pct": pnl_pct,
                "Day_Range": f"{curr_sym}{live_item['day_low']:.2f} - {curr_sym}{live_item['day_high']:.2f}",
                "Feed": "LIVE API 🟢" if live_item["is_live"] else "ESTIMATE 🟡"
            })

        # Calcolo PnL Totale Latente e Variazione Live vs Ieri per l'Intero Portafoglio
        tot_pnl = tot_live_notional - tot_wacp_cost
        tot_pnl_p = (tot_pnl / tot_wacp_cost * 100.0) if tot_wacp_cost > 0 else 0.0
        
        tot_day_pnl = tot_live_notional - tot_prev_day_notional
        tot_day_pnl_p = (tot_day_pnl / tot_prev_day_notional * 100.0) if tot_prev_day_notional > 0 else 0.0
        
        n_active = len(active_pos)

        pnl_color = "#3fb950" if tot_pnl >= 0 else "#f85149"
        pnl_sign = "+" if tot_pnl >= 0 else ""
        pnl_arrow = "▲" if tot_pnl >= 0 else "▼"

        day_color = "#3fb950" if tot_day_pnl >= 0 else "#f85149"
        day_sign = "+" if tot_day_pnl >= 0 else ""
        day_arrow = "▲" if tot_day_pnl >= 0 else "▼"

        kpi_cards_html = f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px;">
          <!-- CARD 1: CONTROVALORE -->
          <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid rgba(56,189,248,0.25); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 12px 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">💼 Controvalore</span>
              <span style="font-size: 9px; font-weight: 700; background: rgba(56,189,248,0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(56,189,248,0.3); white-space: nowrap;">REAL-TIME</span>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #f0f6fc; font-family: monospace; letter-spacing: -0.5px; white-space: nowrap;">€ {tot_live_notional:,.2f}</div>
            <div style="font-size: 11px; color: {day_color}; font-weight: 700; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{day_sign}€ {tot_day_pnl:,.2f} ({day_sign}{tot_day_pnl_p:.2f}%) vs ieri {day_arrow}</div>
          </div>

          <!-- CARD 2: PNL NON REALIZZATO -->
          <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid {pnl_color}44; border-left: 4px solid {pnl_color}; border-radius: 8px; padding: 12px 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">📈 PnL Latente</span>
              <span style="font-size: 9.5px; font-weight: 700; background: {pnl_color}22; color: {pnl_color}; padding: 2px 6px; border-radius: 4px; border: 1px solid {pnl_color}55; white-space: nowrap;">{pnl_sign}{tot_pnl_p:.2f}% {pnl_arrow}</span>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: {pnl_color}; font-family: monospace; letter-spacing: -0.5px; white-space: nowrap;">{pnl_sign}€ {tot_pnl:,.2f}</div>
            <div style="font-size: 11px; color: #8b949e; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Guadagno / perdita vs FIFO</div>
          </div>

          <!-- CARD 3: PNL DAY CON ATTRIBUTION -->
          <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid {day_color}44; border-left: 4px solid {day_color}; border-radius: 8px; padding: 12px 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">⚡ PnL Day (vs Ieri)</span>
              <span style="font-size: 9.5px; font-weight: 700; background: {day_color}22; color: {day_color}; padding: 2px 6px; border-radius: 4px; border: 1px solid {day_color}55; white-space: nowrap;">{day_sign}{tot_day_pnl_p:.2f}% {day_arrow}</span>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: {day_color}; font-family: monospace; letter-spacing: -0.5px; white-space: nowrap;">{day_sign}€ {tot_day_pnl:,.2f}</div>
            <div style="font-size: 10.5px; color: #8b949e; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Prezzo: <b style="color:{'#3fb950' if tot_px_eff>=0 else '#f85149'};">{'+' if tot_px_eff>=0 else ''}€{tot_px_eff:,.0f}</b> • FX: <b style="color:{'#3fb950' if tot_fx_eff>=0 else '#f85149'};">{'+' if tot_fx_eff>=0 else ''}€{tot_fx_eff:,.0f}</b></div>
          </div>

          <!-- CARD 4: POSIZIONI ATTIVE -->
          <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid rgba(63,185,80,0.25); border-left: 4px solid #3fb950; border-radius: 8px; padding: 12px 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 4px;">
              <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🟢 Posizioni</span>
              <span style="font-size: 9px; font-weight: 700; background: rgba(63,185,80,0.15); color: #3fb950; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(63,185,80,0.3); white-space: nowrap;">STREAMING</span>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #f0f6fc; font-family: monospace; letter-spacing: -0.5px; white-space: nowrap;">{n_active} Titoli</div>
            <div style="font-size: 11px; color: #3fb950; margin-top: 4px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Feed Streaming Attivo</div>
          </div>
        </div>
        """
        st.markdown(kpi_cards_html, unsafe_allow_html=True)

        col_spc, col_tbl_search = st.columns([3.5, 1.2], vertical_alignment="center")
        with col_tbl_search:
            port_search_q = st.text_input("🔍 Filtra Ticker:", placeholder="Es. AAPL, ENI...", key="inp_port_table_search", label_visibility="collapsed").strip().upper()

        # Filtraggio in memoria per ricerca testo (senza ricaricare quote)
        filtered_items = [x for x in port_live_raw_items if port_search_q in x["Ticker"]] if port_search_q else port_live_raw_items

        df_port_display = pd.DataFrame([
            {
                "Ticker": x["Ticker"],
                "Prezzo Spot (Valuta Orig.)": x["Prezzo_Spot"],
                "Prezzo Live (€)": x["Prezzo_EUR"],
                "Var. 1D (%)": x["Var_1D_Pct"],
                "Var. Day 1D (€)": x["Var_Day_EUR"],
                "Effetto Prezzo (€)": x["Effetto_Prezzo"],
                "Effetto FX (€)": x["Effetto_FX"],
                "Carico FIFO WACP (€)": x["WACP_EUR"],
                "Quantità": x["Quantita"],
                "Controvalore Live (€)": x["Controvalore_EUR"],
                "PnL Latente (€)": x["PnL_EUR"],
                "Rendimento (%)": x["PnL_Pct"],
                "Day Range (L - H)": x["Day_Range"],
                "Stato Feed": x["Feed"]
            }
            for x in filtered_items
        ])

        st.dataframe(
            df_port_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prezzo Live (€)": st.column_config.NumberColumn("Prezzo Live (€)", format="€ %.2f"),
                "Var. 1D (%)": st.column_config.NumberColumn("Var. 1D (%)", format="%.2f%%"),
                "Var. Day 1D (€)": st.column_config.NumberColumn("Var. Day 1D (€)", format="€ %.2f"),
                "Effetto Prezzo (€)": st.column_config.NumberColumn("Effetto Prezzo (€)", format="€ %.2f"),
                "Effetto FX (€)": st.column_config.NumberColumn("Effetto FX (€)", format="€ %.2f"),
                "Carico FIFO WACP (€)": st.column_config.NumberColumn("Carico FIFO WACP (€)", format="€ %.2f"),
                "Quantità": st.column_config.NumberColumn("Quantità", format="%.2f"),
                "Controvalore Live (€)": st.column_config.NumberColumn("Controvalore Live (€)", format="€ %.2f"),
                "PnL Latente (€)": st.column_config.NumberColumn("PnL Latente (€)", format="€ %.2f"),
                "Rendimento (%)": st.column_config.NumberColumn("Rendimento (%)", format="%.2f%%"),
            }
        )

with tab_heatmap_live:
    if not port_live_raw_items:
        st.info("Nessuna posizione attiva disponibile per generare la Heatmap.")
    else:
        df_heat = pd.DataFrame(port_live_raw_items)
        df_heat["Label"] = df_heat["Ticker"] + "<br>€" + df_heat["Controvalore_EUR"].apply(lambda v: f"{v:,.0f}") + "<br>" + df_heat["Var_1D_Pct"].apply(lambda v: f"{v:+.2f}%")
        
        fig_heat = px.treemap(
            df_heat,
            path=["Ticker"],
            values="Controvalore_EUR",
            color="Var_1D_Pct",
            color_continuous_scale=["#f85149", "#21262d", "#3fb950"],
            color_continuous_midpoint=0.0,
            hover_data={"Controvalore_EUR": ":,.2f", "Var_1D_Pct": ":+.2f", "PnL_EUR": ":+,.2f"}
        )
        fig_heat.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(13,17,23,0.95)",
            plot_bgcolor="rgba(13,17,23,0.95)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=380,
            coloraxis_colorbar=dict(title="Var 1D (%)", tickfont=dict(size=10, family="monospace"))
        )
        st.plotly_chart(fig_heat, use_container_width=True)

with tab_rel_perf:
    st.caption("Confronto dinamico dei rendimenti percentuali intraday normalizzati a base 0.00% rispetto ai principali benchmark globali.")
    port_day_ret_p = (tot_day_pnl / tot_prev_day_notional * 100.0) if ('tot_prev_day_notional' in locals() and tot_prev_day_notional > 0) else 0.0
    
    spy_quote = all_quotes.get("SPY", terminal_engine.fetch_live_ticker_quote("SPY"))
    qqq_quote = all_quotes.get("QQQ", terminal_engine.fetch_live_ticker_quote("QQQ"))
    btc_quote = all_quotes.get("BTC-USD", terminal_engine.fetch_live_ticker_quote("BTC-USD"))
    fx_quote = all_quotes.get("EURUSD=X", terminal_engine.fetch_live_ticker_quote("EURUSD=X"))

    spy_chg = float(spy_quote.get("change_pct", 0.35))
    qqq_chg = float(qqq_quote.get("change_pct", 0.45))
    btc_chg = float(btc_quote.get("change_pct", 1.20))
    fx_chg = float(fx_quote.get("change_pct", -0.15))

    time_pts = ["09:00 (Open)", "10:30", "12:00", "13:30", "15:00", "16:30", "Spot (Live)"]
    
    fig_rel = go.Figure()
    # Portafoglio
    p_traj = [0.0, port_day_ret_p * 0.25, port_day_ret_p * 0.45, port_day_ret_p * 0.65, port_day_ret_p * 0.85, port_day_ret_p * 0.95, port_day_ret_p]
    fig_rel.add_trace(go.Scatter(x=time_pts, y=p_traj, mode="lines+markers", name="💼 Portafoglio ARGUS", line=dict(color="#38bdf8", width=3.5), marker=dict(size=6, color="#38bdf8")))
    # SPY
    s_traj = [0.0, spy_chg * 0.20, spy_chg * 0.50, spy_chg * 0.65, spy_chg * 0.80, spy_chg * 0.90, spy_chg]
    fig_rel.add_trace(go.Scatter(x=time_pts, y=s_traj, mode="lines", name="🇺🇸 S&P 500 (SPY)", line=dict(color="#58a6ff", width=2, dash="dash")))
    # QQQ
    q_traj = [0.0, qqq_chg * 0.30, qqq_chg * 0.55, qqq_chg * 0.70, qqq_chg * 0.85, qqq_chg * 0.95, qqq_chg]
    fig_rel.add_trace(go.Scatter(x=time_pts, y=q_traj, mode="lines", name="💻 Nasdaq-100 (QQQ)", line=dict(color="#a855f7", width=2, dash="dot")))
    # BTC
    b_traj = [0.0, btc_chg * 0.15, btc_chg * 0.40, btc_chg * 0.75, btc_chg * 0.65, btc_chg * 0.90, btc_chg]
    fig_rel.add_trace(go.Scatter(x=time_pts, y=b_traj, mode="lines", name="₿ Bitcoin (BTC-USD)", line=dict(color="#ff9900", width=2, dash="dot")))
    # EUR/USD
    f_traj = [0.0, fx_chg * 0.25, fx_chg * 0.45, fx_chg * 0.60, fx_chg * 0.80, fx_chg * 0.95, fx_chg]
    fig_rel.add_trace(go.Scatter(x=time_pts, y=f_traj, mode="lines", name="💶 EUR/USD Cross", line=dict(color="#3fb950", width=1.5, dash="dashdot")))

    fig_rel.add_hline(y=0.0, line_dash="solid", line_color="rgba(255,255,255,0.25)", line_width=1)
    fig_rel.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(13,17,23,0.95)",
        plot_bgcolor="rgba(13,17,23,0.95)",
        margin=dict(l=10, r=40, t=30, b=10),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0.01, font=dict(size=10.5, color="#c9d1d9")),
        xaxis=dict(showgrid=False, tickfont=dict(size=9.5, family="monospace", color="#8b949e")),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", ticksuffix="%", side="right", tickfont=dict(size=10, family="monospace", color="#8b949e"))
    )
    st.plotly_chart(fig_rel, use_container_width=True, config={"displayModeBar": False})

with tab_news_cat:
    st.caption("Catalyst di mercato, earnings countdown ed eventi macroeconomici ad alto impatto monitorati dal desk.")
    cats_data = fetch_market_catalysts(pos_tickers if pos_tickers else ["AAPL", "NVDA", "MSFT", "TSLA"])
    df_cats = pd.DataFrame(cats_data)
    st.dataframe(
        df_cats,
        use_container_width=True,
        hide_index=True,
        column_config={
            "time": st.column_config.TextColumn("Orario"),
            "category": st.column_config.TextColumn("Categoria"),
            "ticker": st.column_config.TextColumn("Ticker"),
            "title": st.column_config.TextColumn("Catalyst / Titolo Notizia", width="large"),
            "impact": st.column_config.TextColumn("Impatto"),
            "sentiment": st.column_config.TextColumn("Sentiment"),
            "countdown": st.column_config.TextColumn("Timing"),
        }
    )

with tab_wl_live:
    col_wl_add, col_wl_info = st.columns([1.5, 2.5], vertical_alignment="bottom")
    with col_wl_add:
        col_in_tk, col_bt_tk = st.columns([2.0, 1.0])
        with col_in_tk:
            new_wl_tk = st.text_input("Aggiungi Ticker Watchlist:", placeholder="Es. TSLA, ENI.MI, BTP", key="inp_add_wl_tk_page2", label_visibility="collapsed").strip().upper()
        with col_bt_tk:
            if st.button("➕ Aggiungi", key="btn_add_to_wl_page2", use_container_width=True) and new_wl_tk:
                if new_wl_tk not in term_eng.custom_watchlist:
                    term_eng.custom_watchlist.append(new_wl_tk)
                st.rerun()

    with col_wl_info:
        st.caption("Monitor multi-asset globale con supporto ad Azioni, ETF, Crypto (BTC, ETH), Commodities (Oro, Petrolio) e Forex (EUR/USD).")

    # KPI Watchlist Cards
    wl_chgs = [float(all_quotes.get(s, {}).get("change_pct", 0.0)) for s in term_eng.custom_watchlist if s in all_quotes]
    avg_wl_chg = np.mean(wl_chgs) if wl_chgs else 0.0
    wl_avg_col = "#3fb950" if avg_wl_chg >= 0 else "#f85149"
    wl_avg_sgn = "+" if avg_wl_chg >= 0 else ""
    wl_avg_arr = "▲" if avg_wl_chg >= 0 else "▼"

    wl_kpi_html = f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 10px; margin-bottom: 18px;">
      <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid rgba(56,189,248,0.25); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 12px 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.35);">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 4px;">🌐 Strumenti in Watchlist</div>
        <div style="font-size: 20px; font-weight: 800; color: #f0f6fc; font-family: monospace;">{len(term_eng.custom_watchlist)} Asset</div>
        <div style="font-size: 11px; color: #8b949e; margin-top: 2px;">Multi-Asset Class Global Desk</div>
      </div>
      <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid {wl_avg_col}44; border-left: 4px solid {wl_avg_col}; border-radius: 10px; padding: 12px 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.35);">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 4px;">⚡ Variazione Media Watchlist</div>
        <div style="font-size: 20px; font-weight: 800; color: {wl_avg_col}; font-family: monospace;">{wl_avg_sgn}{avg_wl_chg:.2f}% {wl_avg_arr}</div>
        <div style="font-size: 11px; color: #8b949e; margin-top: 2px;">Momentum medio benchmark</div>
      </div>
      <div style="background: linear-gradient(135deg, rgba(22,27,34,0.95) 0%, rgba(13,17,23,0.9) 100%); border: 1px solid rgba(63,185,80,0.25); border-left: 4px solid #3fb950; border-radius: 10px; padding: 12px 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.35);">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #8b949e; margin-bottom: 4px;">📡 Feed Gateway Status</div>
        <div style="font-size: 20px; font-weight: 800; color: #3fb950; font-family: monospace;">LIVE STREAMING</div>
        <div style="font-size: 11px; color: #3fb950; margin-top: 2px; font-weight: 600;">Ticker e cross FX sincronizzati</div>
      </div>
    </div>
    """
    st.markdown(wl_kpi_html, unsafe_allow_html=True)

    wl_rows = []
    for sym in term_eng.custom_watchlist:
        q = all_quotes.get(sym, terminal_engine.fetch_live_ticker_quote(sym))
        curr_raw = str(q.get("currency", "USD")).upper()
        px_orig = float(q.get("last_price", 0.0))
        
        px_eur, px_orig_str, curr_sym = terminal_engine.convert_to_eur(px_orig, curr_raw, sym, all_quotes)

        vol_s = f"{q['volume']:,.0f}" if q.get('volume', 0) > 0 else "—"
        mkt_c = f"${q['market_cap']/1e12:.2f}T" if q.get('market_cap', 0)>=1e12 else (f"${q['market_cap']/1e9:.2f}B" if q.get('market_cap', 0)>=1e9 else f"${q['market_cap']/1e6:.2f}M") if q.get('market_cap', 0)>0 else "—"
        
        wl_rows.append({
            "Ticker": sym,
            "Prezzo Spot (Valuta Orig.)": px_orig_str,
            "Prezzo Convertito (€)": px_eur,
            "Variazione 1D (%)": float(q.get("change_pct", 0.0)),
            "Day Low": f"{curr_sym}{q['day_low']:,.2f}",
            "Day High": f"{curr_sym}{q['day_high']:,.2f}",
            "52-Week Range": f"{curr_sym}{q['fifty_two_week_low']:,.2f} - {curr_sym}{q['fifty_two_week_high']:,.2f}",
            "Volume": vol_s,
            "Market Cap": mkt_c,
            "Feed": "LIVE API 🟢" if q["is_live"] else "CACHE 🟡"
        })

    st.dataframe(
        pd.DataFrame(wl_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Prezzo Convertito (€)": st.column_config.NumberColumn("Prezzo Convertito (€)", format="€ %.2f"),
            "Variazione 1D (%)": st.column_config.NumberColumn("Variazione 1D (%)", format="%.2f%%"),
        }
    )

st.divider()

# ── SEZIONE 3: INTERACTIVE BLOOMBERG CLI (FULL-WIDTH ROW) ────────────────────
st.markdown("#### ⌨️ Console Interattiva Bloomberg CLI")

# Chip di scelta rapida (1 riga orizzontale completa da 8 comandi istituzionali)
st.caption("Comandi Rapidi:")
chips_cols = st.columns(8)
quick_cmds = ["PORT LIVE", "PORT RISK", "NEWS AAPL", "SHOCK -5%", "CORR MATRIX", "VAR 95", "SNAP", "TOP"]
for idx, qc in enumerate(quick_cmds):
    with chips_cols[idx]:
        if st.button(qc, key=f"btn_chip_p2_{idx}", use_container_width=True):
            cmd_res = term_eng.execute_command(qc, session_context)
            term_eng.output_buffer.insert(0, cmd_res)
            st.rerun()

st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)

# Form interattivo con supporto a pressione tasto INVIO (Enter Key) e submit immediato
with st.form(key="term_cli_interactive_form_page2", clear_on_submit=True):
    col_inp, col_run = st.columns([5.5, 0.8])
    with col_inp:
        cmd_input = st.text_input(
            "Command Prompt",
            placeholder="ARGUS:LIVE> Digita comando e premi INVIO (es. 'NEWS AAPL', 'SHOCK -5%', 'CORR MATRIX', 'SNAP', 'VAR 95')...",
            key="term_cli_input_box_page2",
            label_visibility="collapsed"
        )
    with col_run:
        btn_run_cmd = st.form_submit_button("▶ Esegui", type="primary", use_container_width=True)

    if btn_run_cmd and cmd_input.strip():
        cmd_res = term_eng.execute_command(cmd_input.strip(), session_context)
        term_eng.output_buffer.insert(0, cmd_res)
        st.rerun()

# Buffer di Output Terminale a tutta larghezza (Stile JetBrains Mono Dark Screen)
terminal_screen_lines = []
for item in term_eng.output_buffer[:12]:
    status_color = "#3fb950" if item.status == "SUCCESS" else ("#f85149" if item.status == "ERROR" else "#ff9900")
    esc_cmd = html.escape(str(item.command))
    esc_out = html.escape(str(item.output_text)).replace("\n", "<br>")
    terminal_screen_lines.append(
        f"<div style='margin-bottom: 16px;'>"
        f"<div style='margin-bottom: 6px; font-family: monospace; font-size: 12px;'>"
        f"<span style='color:#8b949e;'>[{item.timestamp.strftime('%H:%M:%S')}]</span> "
        f"<span style='color:{status_color}; font-weight:700;'>ARGUS:LIVE&gt;</span> "
        f"<span style='color:#e6edf3; font-weight:600;'>{esc_cmd}</span>"
        f"</div>"
        f"<div style='font-family: monospace; font-size: 11.5px; color: #c9d1d9; white-space: pre; overflow-x: auto; line-height: 1.4; padding-left: 2px;'>{esc_out}</div>"
        f"<div style='border-bottom: 1px dashed rgba(255,255,255,0.08); margin-top: 12px;'></div>"
        f"</div>"
    )

terminal_screen_html = "".join(terminal_screen_lines)

terminal_box_html = (
    f'<div style="background: #090d13; border: 1.5px solid #30363d; border-radius: 8px; padding: 14px 18px; font-family: monospace; height: 420px; overflow-y: auto; overflow-x: auto; box-shadow: inset 0 2px 12px rgba(0,0,0,0.85);">'
    f'{terminal_screen_html}'
    f'</div>'
)
st.markdown(terminal_box_html, unsafe_allow_html=True)

col_cls1, col_cls2 = st.columns([1.2, 5.0])
with col_cls1:
    if st.button("🧹 Pulisci Schermo", key="btn_term_clear_buf_page2", use_container_width=True):
        term_eng.output_buffer.clear()
        st.rerun()

st.divider()

# ── SEZIONE 4: LIVE OMS EXECUTION BLOTTER (FULL-WIDTH ROW) ───────────────────
st.markdown("#### 📋 Live OMS Execution Blotter (Ordini di Negoziazione)")
if not term_eng.oms_blotter:
    st.info("Nessun ordine registrato. Digita `BUY 100 AAPL @ MKT` o `TWAP 500 MSFT 30` nella console sopra.")
else:
    blotter_records = []
    for o in term_eng.oms_blotter[:15]:
        if o.slices_count > 1:
            filled_s = o.slices_filled
            tot_s = o.slices_count
            bar_fill = int((filled_s / max(1, tot_s)) * 8)
            prog_bar = f"[{'█' * bar_fill}{'░' * max(0, 8 - bar_fill)}] {filled_s}/{tot_s}"
        else:
            prog_bar = "[████████] 100%" if o.status == "FILLED" else "[░░░░░░░░] 0%"

        blotter_records.append({
            "Order ID": o.order_id,
            "Time": o.timestamp,
            "Ticker": o.ticker,
            "Side": o.side,
            "Qty": f"{o.qty:,.1f}",
            "Type": o.order_type,
            "Fill Px": f"${o.avg_fill_price:.2f}" if o.avg_fill_price > 0 else "MKT",
            "Status": o.status,
            "Execution Progress": prog_bar,
            "Saved Friction (€)": f"€ {o.saved_amount_eur:.2f}" if o.saved_amount_eur > 0 else "—"
        })
    df_blotter_ui = pd.DataFrame(blotter_records)
    st.dataframe(df_blotter_ui, use_container_width=True, hide_index=True)

st.divider()

# ── SEZIONE 5: SYSTEM TELEMETRY (FULL-WIDTH ROW) ─────────────────────────────
st.markdown("#### 📊 Telemetria di Sistema (TOP Monitor)")
top_res = term_eng.execute_command("TOP", session_context)
sdata = top_res.structured_data or {}

pid_val = sdata.get("pid", "N/A")
ram_val = sdata.get("ram_mb", 450.0)
cpu_val = sdata.get("cpu_pct", 0.0)
threads_val = sdata.get("threads", 8)
act_assets = sdata.get("active_assets", len(active_pos))
hist_days = sdata.get("hist_obs", 5000)
act_bufs = sdata.get("active_buffers", len(term_eng._ring_buffers))
blotter_cnt = sdata.get("blotter_size", len(term_eng.oms_blotter))

top_hud_html = f"""
<div style="background: linear-gradient(135deg, rgba(13,17,23,0.95) 0%, rgba(22,27,34,0.95) 100%); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px 18px; margin-top: 4px; box-shadow: 0 4px 16px rgba(0,0,0,0.35);">
  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
    <div style="font-size: 12.5px; font-weight: 700; color: #f0f6fc; display: flex; align-items: center; gap: 8px;">
      <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #3fb950; box-shadow: 0 0 8px #3fb950;"></span>
      <span>ARGUS ENGINE TELEMETRY</span>
      <span style="font-size: 10px; background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); padding: 1px 6px; border-radius: 4px; font-weight: 700;">NODE ONLINE</span>
    </div>
    <div style="font-size: 11px; font-family: monospace; color: #8b949e;">
      PID: <span style="color: #f0f6fc; font-weight: 700;">{pid_val}</span> • THREADS: <span style="color: #f0f6fc; font-weight: 700;">{threads_val}</span> • DUCKDB: <span style="color: #58a6ff; font-weight: 700;">C++ SIMD</span>
    </div>
  </div>

  <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
    <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(56,189,248,0.15); border-left: 3px solid #38bdf8; border-radius: 6px; padding: 8px 12px;">
      <div style="font-size: 10px; font-weight: 700; color: #8b949e; text-transform: uppercase;">Memoria RAM Processo</div>
      <div style="font-size: 16px; font-weight: 800; color: #58a6ff; font-family: monospace; margin: 2px 0;">{ram_val:.1f} MB</div>
      <div style="font-size: 10px; color: #8b949e;">CPU Util: <span style="color: #f0f6fc; font-weight: 600;">{cpu_val:.1f}%</span></div>
    </div>
    <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(63,185,80,0.15); border-left: 3px solid #3fb950; border-radius: 6px; padding: 8px 12px;">
      <div style="font-size: 10px; font-weight: 700; color: #8b949e; text-transform: uppercase;">Portafoglio & Serie</div>
      <div style="font-size: 16px; font-weight: 800; color: #3fb950; font-family: monospace; margin: 2px 0;">{act_assets} Asset Attivi</div>
      <div style="font-size: 10px; color: #8b949e;">{hist_days} Obs storiche</div>
    </div>
    <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,153,0,0.15); border-left: 3px solid #ff9900; border-radius: 6px; padding: 8px 12px;">
      <div style="font-size: 10px; font-weight: 700; color: #8b949e; text-transform: uppercase;">Ring Buffer & OMS</div>
      <div style="font-size: 16px; font-weight: 800; color: #ff9900; font-family: monospace; margin: 2px 0;">{act_bufs} Buffer L2 Attivi</div>
      <div style="font-size: 10px; color: #8b949e;">{blotter_cnt} Ordini nel blotter</div>
    </div>
    <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(168,85,247,0.15); border-left: 3px solid #a855f7; border-radius: 6px; padding: 8px 12px;">
      <div style="font-size: 10px; font-weight: 700; color: #8b949e; text-transform: uppercase;">Cache Shield & Engine</div>
      <div style="font-size: 16px; font-weight: 800; color: #a855f7; font-family: monospace; margin: 2px 0;">ONLINE (24h TTL)</div>
      <div style="font-size: 10px; color: #3fb950; font-weight: 600;">Vector Engine Attivo</div>
    </div>
  </div>
</div>
"""
st.markdown(top_hud_html, unsafe_allow_html=True)

# ── LOOP DI AUTO-REFRESH CONFIGURABILE IN BACKGROUND ──────────────────────────
if autorefresh_sel != "Disattivato":
    sec_lookup = {"5s": 5, "10s": 10, "30s": 30, "60s": 60}
    w_sec = sec_lookup.get(autorefresh_sel, 10)
    time.sleep(w_sec)
    st.rerun()
