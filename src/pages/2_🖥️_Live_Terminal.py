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

import core.ui_utils as ui_utils
import core.terminal_engine as terminal_engine

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
    OMSOrder
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

# ── Inizializzazione Session State per Terminal Engine ────────────────────────
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

# Buffer iniziale con guida rapida se vuoto
if not term_eng.output_buffer:
    init_res = term_eng.execute_command("HELP", session_context)
    term_eng.output_buffer.append(init_res)

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

    # Fetch Live Quote in tempo reale via yfinance fast_info API
    live_q = terminal_engine.fetch_live_ticker_quote(active_tape_ticker)
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

    # Header Ticker Live con Badge Variazione e Stato API
    chg_color = "#3fb950" if chg >= 0 else "#f85149"
    chg_sign = "+" if chg >= 0 else ""
    arrow = "▲" if chg >= 0 else "▼"
    api_badge = '<span style="font-size:10px; background:rgba(63,185,80,0.15); color:#3fb950; border:1px solid rgba(63,185,80,0.3); padding:2px 6px; border-radius:4px; font-weight:700;">LIVE API</span>' if live_q["is_live"] else '<span style="font-size:10px; background:rgba(255,153,0,0.15); color:#ff9900; border:1px solid rgba(255,153,0,0.3); padding:2px 6px; border-radius:4px; font-weight:700;">CACHE</span>'

    tape_card_html = (
        f'<div style="background: rgba(22, 27, 34, 0.95); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px 16px; margin-top: 4px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<div><span style="font-size:18px; font-weight:800; color:#f0f6fc;">{active_tape_ticker}</span> {api_badge}</div>'
        f'<div><span style="font-size:13px; font-weight:700; color:{chg_color}; background:{chg_color}22; padding:3px 8px; border-radius:4px; border:1px solid {chg_color}55;">{chg_sign}{chg:,.2f} ({chg_sign}{chg_pct:.2f}%) {arrow}</span></div>'
        f'</div>'
        f'<div style="font-size:24px; font-weight:800; color:#ff9900; margin: 4px 0;">{currency} {display_px:,.2f}</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:11px; color:#8b949e; font-family:monospace;">'
        f'<span>Vol: {vol_str}</span><span>Range: ${day_l:,.2f} - ${day_h:,.2f}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(tape_card_html, unsafe_allow_html=True)

with col_tape_book:
    st.markdown("<div style='font-size:12.5px; font-weight:700; color:#8b949e; margin-bottom:4px;'>📊 Level-2 Depth Book (5 Livelli Bid/Ask)</div>", unsafe_allow_html=True)
    # Matrice Level-2 Depth Book dinamica attorno al prezzo reale
    spread_step = max(0.01, round(display_px * 0.0001, 2))
    base_bid = round(display_px - spread_step, 2)
    base_ask = round(display_px + spread_step, 2)
    
    book_rows = [
        {"bid_vol": 1450, "bid_px": base_bid, "ask_px": base_ask, "ask_vol": 1200},
        {"bid_vol": 920, "bid_px": round(base_bid - spread_step * 2, 2), "ask_px": round(base_ask + spread_step * 2, 2), "ask_vol": 1100},
        {"bid_vol": 680, "bid_px": round(base_bid - spread_step * 4, 2), "ask_px": round(base_ask + spread_step * 4, 2), "ask_vol": 1650},
        {"bid_vol": 410, "bid_px": round(base_bid - spread_step * 6, 2), "ask_px": round(base_ask + spread_step * 6, 2), "ask_vol": 890},
        {"bid_vol": 320, "bid_px": round(base_bid - spread_step * 8, 2), "ask_px": round(base_ask + spread_step * 8, 2), "ask_vol": 540}
    ]

    book_rows_html = []
    for r in book_rows:
        bid_bar_w = min(100, int((r["bid_vol"] / 2000.0) * 100))
        ask_bar_w = min(100, int((r["ask_vol"] / 2000.0) * 100))
        book_rows_html.append(
            f'<div style="display:flex; font-family:monospace; font-size:11px; padding: 2px 0; border-bottom: 1px dashed rgba(255,255,255,0.04);">'
            f'<div style="flex:1; text-align:right; color:#8b949e; position:relative; padding-right:8px;"><div style="position:absolute; right:0; top:0; bottom:0; width:{bid_bar_w}%; background:rgba(63,185,80,0.15); z-index:1;"></div><span style="position:relative; z-index:2;">{r["bid_vol"]}</span></div>'
            f'<div style="flex:1; text-align:right; color:#3fb950; font-weight:700; padding-right:12px;">${r["bid_px"]:,.2f}</div>'
            f'<div style="flex:1; text-align:left; color:#f85149; font-weight:700; padding-left:12px;">${r["ask_px"]:,.2f}</div>'
            f'<div style="flex:1; text-align:left; color:#8b949e; position:relative; padding-left:8px;"><div style="position:absolute; left:0; top:0; bottom:0; width:{ask_bar_w}%; background:rgba(248,81,73,0.15); z-index:1;"></div><span style="position:relative; z-index:2;">{r["ask_vol"]}</span></div>'
            f'</div>'
        )

    book_full_html = (
        f'<div style="background: rgba(13, 17, 23, 0.9); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px;">'
        f'<div style="display:flex; font-size:10px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:4px; margin-bottom:4px;">'
        f'<div style="flex:1; text-align:right;">BID SIZE</div>'
        f'<div style="flex:1; text-align:right; padding-right:12px;">BID PX</div>'
        f'<div style="flex:1; text-align:left; padding-left:12px;">ASK PX</div>'
        f'<div style="flex:1; text-align:left;">ASK SIZE</div>'
        f'</div>'
        f'{"".join(book_rows_html)}'
        f'</div>'
    )
    st.markdown(book_full_html, unsafe_allow_html=True)
    st.caption(f"🎯 **Microprice Stoikov**: `${microprice:.2f}` • **VWAP**: `${vwap_px:.2f}` • **Timestamp Feed**: `{live_q['timestamp']}`")

st.divider()

# ── SEZIONE 2: LIVE MULTI-ASSET MONITOR (PORTAFOGLIO + WATCHLIST) ────────────
col_sec2_hdr, col_sec2_btn = st.columns([3.2, 1.2], vertical_alignment="center")
with col_sec2_hdr:
    st.markdown("#### 📊 Live Multi-Asset Pricing Monitor (Portafoglio & Watchlist)")
with col_sec2_btn:
    btn_force_sync = st.button("🔄 Sincronizza Prezzi Live", key="btn_sync_live_quotes_page2", use_container_width=True)

# Lista completa di tutti i ticker necessari (Portafoglio + Watchlist)
pos_tickers = [str(t).strip().upper() for t in pos["ticker"].unique() if str(t).strip()] if (not pos.empty and "ticker" in pos.columns) else []
wl_tickers = [str(t).strip().upper() for t in term_eng.custom_watchlist if str(t).strip()]
needed_tickers = list(dict.fromkeys(pos_tickers + wl_tickers))

# Costruisci mappa di fallback immediata dai dati del portafoglio caricato
pos_fallback_map = {}
if not pos.empty and "ticker" in pos.columns:
    for _, row in pos.iterrows():
        tk = str(row["ticker"]).strip().upper()
        p_val = float(row.get("current_price", row.get("wacp", row.get("buy_price", 150.0))))
        if p_val > 0:
            pos_fallback_map[tk] = p_val

if "argus_live_quotes_dict" not in st.session_state:
    st.session_state["argus_live_quotes_dict"] = {}

# Sincronizza se esplicitamente richiesto o se la cache di sessione è vuota
need_sync = btn_force_sync or (not st.session_state["argus_live_quotes_dict"]) or any(t not in st.session_state["argus_live_quotes_dict"] for t in needed_tickers)

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

tab_port_live, tab_wl_live = st.tabs([
    "💼 Prezzi Live Intero Portafoglio",
    "🌐 Watchlist Istituzionale di Mercato"
])

with tab_port_live:
    if pos.empty or "ticker" not in pos.columns:
        st.info("Nessun portafoglio attivo caricato. Carica una distinta posizioni per visualizzare i prezzi live.")
    else:
        # Calcolo prezzi live per ogni titolo del portafoglio
        port_live_rows = []
        tot_live_notional = 0.0
        tot_wacp_cost = 0.0
        day_chgs = []

        for _, r in pos.iterrows():
            sym = str(r["ticker"]).strip().upper()
            q_val = float(r.get("quantity", 0.0))
            wacp = float(r.get("wacp", r.get("buy_price", 0.0)))
            live_item = all_quotes.get(sym, terminal_engine.fetch_live_ticker_quote(sym))
            live_px = live_item["last_price"]
            chg_1d = live_item["change_pct"]
            
            mkt_val = q_val * live_px
            cost = q_val * wacp
            pnl = mkt_val - cost
            pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0
            
            tot_live_notional += mkt_val
            tot_wacp_cost += cost
            day_chgs.append(chg_1d)

            port_live_rows.append({
                "Ticker": sym,
                "Prezzo Live Spot": f"${live_px:,.2f}",
                "Var. 1D (%)": f"{'+' if chg_1d>=0 else ''}{chg_1d:.2f}%",
                "Carico FIFO (WACP)": f"${wacp:,.2f}",
                "Quantità": f"{q_val:,.1f}",
                "Controvalore Live (€)": f"€ {mkt_val:,.2f}",
                "PnL Non Realizzato (€)": f"{'+' if pnl>=0 else ''}€ {pnl:,.2f}",
                "Rendimento (%)": f"{'+' if pnl_pct>=0 else ''}{pnl_pct:.2f}%",
                "Day Range (L - H)": f"${live_item['day_low']:.2f} - ${live_item['day_high']:.2f}",
                "Stato Feed": "LIVE API 🟢" if live_item["is_live"] else "ESTIMATE 🟡"
            })

        # KPI Summary
        tot_pnl = tot_live_notional - tot_wacp_cost
        tot_pnl_p = (tot_pnl / tot_wacp_cost * 100.0) if tot_wacp_cost > 0 else 0.0
        avg_1d = np.mean(day_chgs) if day_chgs else 0.0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Controvalore Portafoglio Live", f"€ {tot_live_notional:,.2f}")
        with k2:
            st.metric("PnL Totale Non Realizzato", f"€ {tot_pnl:+,.2f}", delta=f"{tot_pnl_p:+.2f}%")
        with k3:
            st.metric("Variazione Media Intraday (1D)", f"{avg_1d:+.2f}%")
        with k4:
            st.metric("Titoli Sincronizzati", f"{len(pos)} Asset", delta="Real-Time Active")

        st.dataframe(pd.DataFrame(port_live_rows), use_container_width=True, hide_index=True)

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

    wl_rows = []
    for sym in term_eng.custom_watchlist:
        q = all_quotes.get(sym, terminal_engine.fetch_live_ticker_quote(sym))
        vol_s = f"{q['volume']:,.0f}" if q['volume'] > 0 else "—"
        mkt_c = f"${q['market_cap']/1e12:.2f}T" if q['market_cap']>=1e12 else (f"${q['market_cap']/1e9:.2f}B" if q['market_cap']>=1e9 else f"${q['market_cap']/1e6:.2f}M") if q['market_cap']>0 else "—"
        wl_rows.append({
            "Ticker": sym,
            "Prezzo Spot Live": f"{q['currency']} {q['last_price']:,.2f}",
            "Variazione 1D (%)": f"{'+' if q['change_pct']>=0 else ''}{q['change_pct']:.2f}%",
            "Day Low": f"${q['day_low']:,.2f}",
            "Day High": f"${q['day_high']:,.2f}",
            "52-Week Range": f"${q['fifty_two_week_low']:.2f} - ${q['fifty_two_week_high']:.2f}",
            "Volume": vol_s,
            "Market Cap": mkt_c,
            "Feed": "LIVE API 🟢" if q["is_live"] else "CACHE 🟡"
        })

    st.dataframe(pd.DataFrame(wl_rows), use_container_width=True, hide_index=True)

st.divider()

# ── SEZIONE 3: INTERACTIVE BLOOMBERG CLI (FULL-WIDTH ROW) ────────────────────
st.markdown("#### ⌨️ Console Interattiva Bloomberg CLI")

# Chip di scelta rapida (1 riga orizzontale completa da 8 comandi)
st.caption("Comandi Rapidi:")
chips_cols = st.columns(8)
quick_cmds = ["PORT LIVE", "PORT RISK", "WATCHLIST", "QUOTE AAPL", "QUOTE NVDA", "QUOTE BTC", "VAR 95", "TOP"]
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
            placeholder="ARGUS:LIVE> Digita comando e premi INVIO (es. 'PORT LIVE', 'WATCHLIST', 'QUOTE NVDA', 'BTC-USD', 'VAR 95')...",
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
    esc_out = html.escape(str(item.output_text))
    terminal_screen_lines.append(
        f"<span style='color:#8b949e;'>[{item.timestamp.strftime('%H:%M:%S')}]</span> "
        f"<span style='color:{status_color}; font-weight:700;'>ARGUS:LIVE&gt;</span> "
        f"<span style='color:#e6edf3; font-weight:600;'>{esc_cmd}</span>\n"
        f"{esc_out}\n" + "─"*90
    )

terminal_screen_html = "\n\n".join(terminal_screen_lines)

terminal_box_html = (
    f'<div style="background: #090d13; border: 1.5px solid #30363d; border-radius: 8px; padding: 16px 20px; font-family: monospace; font-size: 12.5px; color: #c9d1d9; white-space: pre-wrap; height: 420px; overflow-y: auto; box-shadow: inset 0 2px 12px rgba(0,0,0,0.85); line-height: 1.45;">'
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
        blotter_records.append({
            "Order ID": o.order_id,
            "Time": o.timestamp,
            "Ticker": o.ticker,
            "Side": o.side,
            "Qty": f"{o.qty:,.1f}",
            "Type": o.order_type,
            "Fill Px": f"${o.avg_fill_price:.2f}" if o.avg_fill_price > 0 else "MKT",
            "Status": o.status,
            "Saved (€)": f"€ {o.saved_amount_eur:.2f}" if o.saved_amount_eur > 0 else "—"
        })
    df_blotter_ui = pd.DataFrame(blotter_records)
    st.dataframe(df_blotter_ui, use_container_width=True, hide_index=True)

st.divider()

# ── SEZIONE 5: SYSTEM TELEMETRY (FULL-WIDTH ROW) ─────────────────────────────
st.markdown("#### 📊 Telemetria di Sistema (TOP Monitor)")
top_res = term_eng.execute_command("TOP", session_context)
top_box_html = (
    f'<div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; font-family: monospace; font-size: 11.5px; color: #58a6ff; white-space: pre-wrap; margin-top: 4px;">'
    f'{html.escape(top_res.output_text)}'
    f'</div>'
)
st.markdown(top_box_html, unsafe_allow_html=True)
