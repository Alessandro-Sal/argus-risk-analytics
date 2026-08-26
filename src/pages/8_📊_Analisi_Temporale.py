import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

import importlib
import core.ui_utils
import core.duckdb_engine
import core.temporal_engine
import core.multi_portfolio
importlib.reload(core.ui_utils)
importlib.reload(core.duckdb_engine)
importlib.reload(core.temporal_engine)
importlib.reload(core.multi_portfolio)

from core.sidebar import render_sidebar
from core.fetcher import get_engine
from core.db_exporter import get_all_snapshots_history, get_snapshot_positions_by_id
from core.multi_portfolio import list_saved_portfolio_profiles, load_portfolio_profile
from core.ui_utils import (
    apply_plotly_theme, inject_custom_css, render_command_bar, 
    metric_card, ensure_risk_bundle_loaded, render_sandbox_banner
)
from core.temporal_engine import (
    compute_monthly_return_matrix,
    compute_rolling_risk_metrics,
    compute_underwater_drawdowns,
    compute_seasonality_patterns,
    compute_side_by_side_comparison,
    reconstruct_point_in_time_portfolio,
)
from sqlalchemy import text as sqlt

st.set_page_config(
    page_title="Analisi Temporale | ARGUS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()
render_sidebar()
render_command_bar()

# ── Load In-Memory Portfolio Bundle ───────────────────────────
results, has_real = ensure_risk_bundle_loaded()

raw_sr_port = results.get("portfolio_return", pd.Series(dtype=float))
raw_sr_bm = results.get("benchmark_return", pd.Series(dtype=float))
df_returns = results.get("returns", pd.DataFrame())
pos = results.get("positions", pd.DataFrame())
m = results.get("metrics", {})
ret_m = m.get("returns", {})
mk_m = m.get("market_risk", {})
active_rf_rate = st.session_state.get("active_rf_rate", 0.035)

# Lista dei ticker attivi
if not pos.empty and "ticker" in pos.columns:
    active_tickers = sorted(list(pos[pos.get("current_value", 0) > 0]["ticker"].unique()))
    if not active_tickers:
        active_tickers = sorted(list(pos["ticker"].unique()))
elif df_returns is not None and not df_returns.empty:
    active_tickers = sorted(list(df_returns.columns))
else:
    active_tickers = []

# ── Header & Titolo ──────────────────────────────────────────
st.title("📊 Analisi Temporale & Dinamica delle Serie Storiche")

saved_profiles_list = list_saved_portfolio_profiles()
saved_profile_names = [p.get("name") for p in saved_profiles_list if p.get("name")]

# ── COCKPIT DI STATO & GESTIONE DUAL-MODE (ANALISI CARICATA vs NON CARICATA) ───
if has_real:
    tot_port_val = float(pos["current_value"].sum()) if not pos.empty and "current_value" in pos.columns else float(results.get("portfolio_value", 0.0))
    p_name = st.session_state.get("portfolio_name", "Master Wealth")
    p_run = st.session_state.get("run_id", "LIVE")
    n_assets = len(pos) if not pos.empty else len(df_returns.columns)
    
    with st.expander(f"🟢 **Portafoglio Live Attivo: {p_name}** | Valore: **€ {tot_port_val:,.2f}** | {n_assets} Asset • *Opzioni di cambio portafoglio*", expanded=False):
        c_sw1, c_sw2, c_sw3 = st.columns([2.5, 1.5, 1.2], vertical_alignment="center")
        with c_sw1:
            if saved_profile_names:
                sel_switch_name = st.selectbox("Seleziona altro Portafoglio Salvato:", saved_profile_names, index=saved_profile_names.index(p_name) if p_name in saved_profile_names else 0, key="sw_active_port_p7")
            else:
                st.caption("Nessun altro portafoglio salvato nel Wealth Hub.")
        with c_sw2:
            st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
            if saved_profile_names and st.button("⚡ Attiva Portafoglio", key="btn_sw_port_p7", use_container_width=True):
                prof_data = load_portfolio_profile(sel_switch_name)
                if prof_data:
                    st.session_state["results"] = prof_data.get("results_full") or prof_data
                    st.session_state["pipeline_done"] = True
                    st.session_state["portfolio_name"] = sel_switch_name
                    st.session_state["run_id"] = f"LOAD-{sel_switch_name[:10]}"
                    try:
                        from core.workspace_manager import save_session_snapshot_to_cache
                        save_session_snapshot_to_cache()
                    except Exception:
                        pass
                    st.rerun()
        with c_sw3:
            st.markdown('<div style="height: 24px;"></div>', unsafe_allow_html=True)
            try:
                st.page_link("0_Control_Room.py", label="💼 Control Room", icon="📥", use_container_width=True)
            except Exception:
                pass
else:
    # Modalità Sandbox / Nessun portafoglio reale caricato
    st.markdown("""
    <div style="background: linear-gradient(90deg, rgba(234, 179, 8, 0.12) 0%, rgba(20, 24, 33, 0.85) 100%); border: 1px solid rgba(234, 179, 8, 0.4); border-left: 4px solid #eab308; border-radius: 8px; padding: 12px 18px; margin-bottom: 14px;">
        <div style="font-size: 14px; font-weight: 700; color: #facc15; margin-bottom: 4px;">
            ⚠️ Nessun Portafoglio Reale Attivo in Memoria (Modalità Sandbox Dimostrativa)
        </div>
        <div style="font-size: 12.5px; color: #cbd5e1; line-height: 1.4;">
            I grafici sottostanti mostrano un benchmark simulato. Puoi caricare all'istante un portafoglio salvato dal Wealth Hub, importare un nuovo file o cambiare il preset dimostrativo.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_sb_act1, col_sb_act2, col_sb_act3 = st.columns([2.5, 1.8, 1.7])
    with col_sb_act1:
        if saved_profile_names:
            sel_load_wh = st.selectbox("📂 Portafogli nel Wealth Hub:", saved_profile_names, index=0, key="sel_wh_load_sb_p7")
            if st.button("⚡ Carica Questo Portafoglio", key="btn_load_wh_sb_p7", type="primary", use_container_width=True):
                prof_data = load_portfolio_profile(sel_load_wh)
                if prof_data:
                    st.session_state["results"] = prof_data.get("results_full") or prof_data
                    st.session_state["pipeline_done"] = True
                    st.session_state["portfolio_name"] = sel_load_wh
                    st.session_state["run_id"] = f"LOAD-{sel_load_wh[:10]}"
                    try:
                        from core.workspace_manager import save_session_snapshot_to_cache
                        save_session_snapshot_to_cache()
                    except Exception:
                        pass
                    st.rerun()
        else:
            st.info("Nessun portafoglio salvato trovato nel Wealth Hub.")
            
    with col_sb_act2:
        st.markdown("**📥 Importa Nuovo File:**")
        try:
            st.page_link("0_Control_Room.py", label="Apri Control Room (Importa File)", icon="🚀", use_container_width=True)
        except Exception:
            pass
            
    with col_sb_act3:
        sandbox_opts = [
            "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)",
            "🚀 Mega-Cap Tech & AI Growth",
            "🛡️ Ray Dalio All-Weather",
            "🇪🇺 Euro Blue Chips & Value"
        ]
        curr_sb = st.session_state.get("sandbox_preset_name", sandbox_opts[0])
        sel_sb_preset = st.selectbox("🧪 Scegli Benchmark Demo:", sandbox_opts, index=sandbox_opts.index(curr_sb) if curr_sb in sandbox_opts else 0, key="sel_sb_preset_p7")
        if sel_sb_preset != curr_sb:
            if st.button("🔄 Applica Preset Demo", key="btn_apply_sb_p7", use_container_width=True):
                from core.risk_engine import compute_sandbox_risk_bundle
                sb_presets_map = {
                    "🏦 Bilanciato Istituzionale (60/40 Equity/Bond)": ["AAPL", "MSFT", "JNJ", "PG", "BND", "SPY"],
                    "🚀 Mega-Cap Tech & AI Growth": ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META"],
                    "🛡️ Ray Dalio All-Weather": ["SPY", "TLT", "IEF", "GLD", "DBC"],
                    "🇪🇺 Euro Blue Chips & Value": ["ENEL.MI", "MC.PA", "SAP", "ASML", "SAN.MC"],
                }
                tks = sb_presets_map.get(sel_sb_preset, ["AAPL", "MSFT", "SPY"])
                rf_v = st.session_state.get("active_rf_rate", 0.035)
                base_c = "EUR" if "Euro" in sel_sb_preset else "USD"
                sb_bundle = compute_sandbox_risk_bundle(tickers=tks, sandbox_name=sel_sb_preset, risk_free_rate=rf_v, base_currency=base_c)
                st.session_state["results"] = sb_bundle
                st.session_state["sandbox_preset_name"] = sel_sb_preset
                st.rerun()

st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)


# ── SELETTORE MODULI ANALISI TEMPORALE BLOOMBERG STYLE ─────────
TIME_MODELS_CATALOG = {
    "📈 Curva Cumulata & Drawdown Underwater": {
        "title": "Evoluzione Patrimoniale Cumulata, High-Water Mark & Analisi Underwater Drawdown",
        "badge": "Equity Line • HWM • Top 5 Drawdowns",
        "badge_color": "#00e676",
        "category": "Curva di Crescita & Crisi",
        "desc": "Tracciamento dell'equity curve del capitale, linea High-Water Mark, profondità dei drawdown storici, Ulcer Index e ranking analitico dei 5 peggiori episodi di perdita con giorni esatti di ripresa."
    },
    "🗓️ Matrice Rendimenti Mensili & Annuali": {
        "title": "Heatmap Mensile dei Rendimenti Storici & Performance YTD (Quant Performance Matrix)",
        "badge": "Monthly Heatmap • YTD • Win Rate",
        "badge_color": "#58a6ff",
        "category": "Matrice di Rendimento",
        "desc": "Tavola periodica dei rendimenti mese per mese (Gen-Dic) con scala cromatica condizionale, rendimento complessivo per anno solare (YTD), percentuale di mesi positivi e miglior/peggior mese."
    },
    "🌊 Rischio Mobile Dinamico (Rolling Metrics)": {
        "title": "Evoluzione a Finestra Mobile di Volatilità, Sharpe Ratio, Beta & Tracking Error",
        "badge": "Rolling 30d/60d/90d/252d • Beta Drift",
        "badge_color": "#ff9900",
        "category": "Dinamica del Rischio",
        "desc": "Ispezione della stabilità temporale: misura come variano nel tempo la volatilità annualizzata, l'indice di Sharpe, il Beta verso il mercato e la correlazione con SPY su orizzonti selezionabili."
    },
    "📊 Stagionalità & Pattern Calendari": {
        "title": "Analisi di Stagionalità Temporale: Effetto Giorno della Settimana & Mese dell'Anno",
        "badge": "Day-of-Week • Month-of-Year • Win Rate",
        "badge_color": "#a855f7",
        "category": "Pattern Comportamentali",
        "desc": "Distribuzione statistica dei rendimenti per giorno operativo (Lunedì-Venerdì) e per mese solare per intercettare anomalie di calendario (Effetto Gennaio, rally di fine anno, volatilità infrasettimanale)."
    },
    "⚖️ Confronto Side-by-Side & Snapshot DB": {
        "title": "Audit Differenziale Point-in-Time, Turnover Ratio, Allocation Shift & Registro Snapshot",
        "badge": "Side-by-Side • Delta Pesi • Turnover • DuckDB",
        "badge_color": "#3fb950",
        "category": "Audit Trail & Confronto",
        "desc": "Confronto analitico affiancato tra due momenti storici o profili: calcolo del turnover di ribilanciamento, delta controvalore per asset, spostamento pesi, waterfall dei flussi, drill-down dei lotti FIFO e audit trail DuckDB C++ SIMD."
    }
}

target_tab = None
if "target_subtab_time_active_tab" in st.session_state:
    target_tab = st.session_state.pop("target_subtab_time_active_tab")
elif "global_target_subtab" in st.session_state:
    target_tab = st.session_state.pop("global_target_subtab")
elif "target_time_module" in st.session_state:
    target_tab = st.session_state.pop("target_time_module")

time_keys = list(TIME_MODELS_CATALOG.keys())

if target_tab and target_tab in time_keys:
    st.session_state["time_active_tab"] = target_tab
    st.session_state["time_active_tab_selectbox"] = target_tab
elif "time_active_tab_selectbox" in st.session_state and st.session_state["time_active_tab_selectbox"] in time_keys:
    st.session_state["time_active_tab"] = st.session_state["time_active_tab_selectbox"]
elif "time_active_tab" in st.session_state and st.session_state["time_active_tab"] in time_keys:
    st.session_state["time_active_tab_selectbox"] = st.session_state["time_active_tab"]
else:
    st.session_state["time_active_tab"] = time_keys[0]
    st.session_state["time_active_tab_selectbox"] = time_keys[0]

curr_idx = time_keys.index(st.session_state["time_active_tab"])

st.markdown("<div style='margin-top: 6px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# Barra Selettore Compatta Bloomberg Style
c_sel_tm, c_prev_tm, c_next_tm = st.columns([3.8, 0.6, 0.6], vertical_alignment="center")

with c_prev_tm:
    if st.button("◀ Prec.", key="btn_time_prev", use_container_width=True, help="Modulo precedente"):
        new_i = (curr_idx - 1) % len(time_keys)
        st.session_state["target_subtab_time_active_tab"] = time_keys[new_i]
        st.session_state["time_active_tab"] = time_keys[new_i]
        st.session_state["time_active_tab_selectbox"] = time_keys[new_i]
        st.rerun()

with c_next_tm:
    if st.button("Succ. ▶", key="btn_time_next", use_container_width=True, help="Modulo successivo"):
        new_i = (curr_idx + 1) % len(time_keys)
        st.session_state["target_subtab_time_active_tab"] = time_keys[new_i]
        st.session_state["time_active_tab"] = time_keys[new_i]
        st.session_state["time_active_tab_selectbox"] = time_keys[new_i]
        st.rerun()

with c_sel_tm:
    selected_time_key = st.selectbox(
        "Seleziona Modulo di Analisi Temporale:",
        options=time_keys,
        index=curr_idx,
        format_func=lambda k: f"{k}  —  {TIME_MODELS_CATALOG[k]['category']} [{TIME_MODELS_CATALOG[k]['badge']}]",
        key="time_active_tab_selectbox",
        label_visibility="collapsed"
    )
    st.session_state["time_active_tab"] = selected_time_key

active_time_tab = st.session_state["time_active_tab"]
active_time_info = TIME_MODELS_CATALOG[active_time_tab]

st.markdown(f"""
<div style="background: linear-gradient(90deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.85) 100%); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {active_time_info['badge_color']}; border-radius: 8px; padding: 12px 18px; margin-top: 10px; margin-bottom: 16px;">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
    <div style="font-size: 15px; font-weight: 700; color: #f0f6fc;">
      {active_time_info['title']}
    </div>
    <div style="display: flex; gap: 8px; align-items: center;">
      <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 12px; background: rgba(255,255,255,0.06); color: #8b949e; border: 1px solid rgba(255,255,255,0.08);">
        {active_time_info['category']}
      </span>
      <span style="font-size: 11.5px; font-weight: 600; padding: 2px 10px; border-radius: 12px; background: {active_time_info['badge_color']}22; color: {active_time_info['badge_color']}; border: 1px solid {active_time_info['badge_color']}55;">
        {active_time_info['badge']}
      </span>
    </div>
  </div>
  <div style="font-size: 13px; color: #8b949e; line-height: 1.45;">
    {active_time_info['desc']}
  </div>
</div>
""", unsafe_allow_html=True)


# ── BARRA DI CONTROLLO ORIZZONTE TEMPORALE (SOLO PER SCHEDE 1, 2, 3, 4) ─────────
# Date minime e massime disponibili
if not raw_sr_port.empty:
    idx_dates = pd.to_datetime(raw_sr_port.index)
    min_avail_date = idx_dates.min().to_pydatetime().date()
    max_avail_date = idx_dates.max().to_pydatetime().date()
else:
    min_avail_date = (datetime.now() - timedelta(days=365)).date()
    max_avail_date = datetime.now().date()

calc_start = min_avail_date
calc_end = max_avail_date

def filter_series_by_date(sr: pd.Series, start_d, end_d) -> pd.Series:
    if sr is None or sr.empty:
        return sr
    s_dt = sr.copy()
    if getattr(s_dt.index, 'tz', None) is not None:
        s_dt.index = s_dt.index.tz_localize(None)
    s_dt.index = pd.to_datetime(s_dt.index)
    mask = (s_dt.index.date >= start_d) & (s_dt.index.date <= end_d)
    return s_dt[mask]

if active_time_tab != "⚖️ Confronto Side-by-Side & Snapshot DB":
    with st.container():
        col_t1, col_t2 = st.columns([1.8, 2.2], vertical_alignment="center")

        with col_t1:
            time_preset = st.selectbox(
                "⏳ Orizzonte Temporale di Analisi Grafici & Matrici:",
                options=["Tutto lo Storico (MAX)", "Anno in Corso (YTD)", "Ultimi 12 Mesi (1Y)", "Ultimi 6 Mesi (6M)", "Ultimi 3 Mesi (3M)", "Intervallo Personalizzato (Calendario)"],
                index=0,
                key="temporal_time_preset",
                help="Filtra l'orizzonte temporale applicato ai grafici, alla matrice mensile e all'intervallo storico."
            )

        if time_preset == "Anno in Corso (YTD)":
            calc_start = datetime(max_avail_date.year, 1, 1).date()
            calc_end = max_avail_date
        elif time_preset == "Ultimi 12 Mesi (1Y)":
            calc_start = max(min_avail_date, max_avail_date - timedelta(days=365))
            calc_end = max_avail_date
        elif time_preset == "Ultimi 6 Mesi (6M)":
            calc_start = max(min_avail_date, max_avail_date - timedelta(days=182))
            calc_end = max_avail_date
        elif time_preset == "Ultimi 3 Mesi (3M)":
            calc_start = max(min_avail_date, max_avail_date - timedelta(days=91))
            calc_end = max_avail_date
        elif time_preset == "Intervallo Personalizzato (Calendario)":
            calc_start = min_avail_date
            calc_end = max_avail_date
        else:
            calc_start = min_avail_date
            calc_end = max_avail_date

        sr_port_tmp = filter_series_by_date(raw_sr_port, calc_start, calc_end)
        active_trading_days = len(sr_port_tmp) if not sr_port_tmp.empty else 0

        with col_t2:
            if time_preset == "Intervallo Personalizzato (Calendario)":
                date_range_picked = st.date_input(
                    "📅 Seleziona Intervallo Date Personalizzato:",
                    value=(calc_start, calc_end),
                    min_value=min_avail_date,
                    max_value=max_avail_date,
                    key="temporal_date_range_picker"
                )
                if isinstance(date_range_picked, (tuple, list)) and len(date_range_picked) == 2:
                    calc_start, calc_end = date_range_picked
            else:
                delta_days_selected = max(1, (calc_end - calc_start).days)
                y_span = delta_days_selected / 365.25
                if y_span >= 1.0:
                    y_int = int(delta_days_selected // 365.25)
                    m_int = int((delta_days_selected % 365.25) // 30.4375)
                    dur_str = f"{y_int} Anni e {m_int} Mesi" if m_int > 0 else f"{y_int} Anni"
                else:
                    m_int = max(1, int(round(delta_days_selected / 30.4375)))
                    dur_str = f"{m_int} Mesi"

                st.markdown(f"""
                <div style="background: linear-gradient(90deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%); border: 1px solid rgba(56, 189, 248, 0.35); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 10px 16px; margin-top: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <div>
                            <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 600;">📅 Finestra Attiva:</span>
                            <span style="font-size: 14px; font-weight: 700; color: #38bdf8; margin-left: 4px;">{calc_start.strftime('%d/%m/%Y')}</span>
                            <span style="color: #64748b; margin: 0 4px;">➔</span>
                            <span style="font-size: 14px; font-weight: 700; color: #38bdf8;">{calc_end.strftime('%d/%m/%Y')}</span>
                        </div>
                        <div>
                            <span style="font-size: 11.5px; padding: 2px 8px; border-radius: 6px; background: rgba(56, 189, 248, 0.12); color: #7dd3fc; font-weight: 600; border: 1px solid rgba(56, 189, 248, 0.25);">
                                {active_trading_days:,} Sedute • {dur_str} ({delta_days_selected} gg)
                            </span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom: 12px;"></div>', unsafe_allow_html=True)

sr_port = filter_series_by_date(raw_sr_port, calc_start, calc_end)
sr_bm = filter_series_by_date(raw_sr_bm, calc_start, calc_end)
if df_returns is not None and not df_returns.empty:
    df_ret_dt = df_returns.copy()
    if getattr(df_ret_dt.index, 'tz', None) is not None:
        df_ret_dt.index = df_ret_dt.index.tz_localize(None)
    df_ret_dt.index = pd.to_datetime(df_ret_dt.index)
    mask_df = (df_ret_dt.index.date >= calc_start) & (df_ret_dt.index.date <= calc_end)
    df_returns_filtered = df_ret_dt[mask_df]
else:
    df_returns_filtered = pd.DataFrame()


# ==============================================================================
# TAB 1: CURVA CUMULATA & DRAWDOWN UNDERWATER
# ==============================================================================
if active_time_tab == "📈 Curva Cumulata & Drawdown Underwater":
    if sr_port.empty:
        st.warning("Serie storica dei rendimenti non disponibile per il periodo selezionato.")
        st.stop()

    all_instrument_options = ["🏛️ Portafoglio Completo", "🎯 Benchmark (SPY)"] + [f"🔹 {t}" for t in active_tickers]
    
    col_sel_i1, col_sel_i2 = st.columns([3, 1])
    with col_sel_i1:
        selected_instruments = st.multiselect(
            "🔍 Scegli gli strumenti da visualizzare ed esaminare:",
            options=all_instrument_options,
            default=["🏛️ Portafoglio Completo", "🎯 Benchmark (SPY)"],
            help="Puoi isolare il portafoglio o confrontare l'andamento di specifici titoli azionari/crypto."
        )
    with col_sel_i2:
        underwater_focus = st.selectbox(
            "🔻 Strumento Focus Underwater:",
            options=["🏛️ Portafoglio Completo"] + [f"🔹 {t}" for t in active_tickers],
            index=0,
            help="Scegli quale asset sottoporre all'analisi analitica dei Drawdown e Top 5 Crisi."
        )

    if underwater_focus == "🏛️ Portafoglio Completo":
        focus_sr = sr_port
        focus_label = "Portafoglio Completo"
    else:
        tk_clean = underwater_focus.replace("🔹 ", "").strip()
        if not df_returns_filtered.empty and tk_clean in df_returns_filtered.columns:
            focus_sr = df_returns_filtered[tk_clean].dropna()
        else:
            focus_sr = sr_port
        focus_label = tk_clean

    uw_data = compute_underwater_drawdowns(focus_sr)
    cum_nav = uw_data["cumulative_nav"]
    hwm = uw_data["hwm"]
    dd_series = uw_data["drawdown_series"]
    max_dd = uw_data["max_drawdown_pct"]
    ulcer = uw_data["ulcer_index"]
    top_episodes = uw_data["top_episodes"]

    tot_val = float(results.get("portfolio_value", pos["current_value"].sum() if not pos.empty and "current_value" in pos.columns else 100000.0))
    n_days = max(1, len(focus_sr))
    period_tot_ret = (cum_nav.iloc[-1] - 1.0) if not cum_nav.empty else 0.0
    cagr_period = ((1.0 + period_tot_ret) ** (252.0 / n_days) - 1.0) * 100.0 if period_tot_ret > -1.0 else 0.0
    calmar = abs(cagr_period / max_dd) if max_dd > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(f"Rendimento Periodo ({focus_label})", f"{period_tot_ret*100.0:+.2f}%", f"CAGR Ann.: {cagr_period:+.2f}%", positive=period_tot_ret >= 0)
    with c2:
        metric_card("Max Drawdown Nel Periodo", f"-{max_dd:.2f}%", "Massimo Picco-Valle", positive=False)
    with c3:
        metric_card("Ulcer Index (UI)", f"{ulcer:.2f}", "Stress e Logorio Temporale", positive=ulcer < 8.0)
    with c4:
        metric_card("Calmar Ratio (CAGR/MDD)", f"{calmar:.2f}", "Efficienza sui Drawdown", positive=calmar >= 1.0)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # 1. Chart: Cumulative Equity Line Multi-Asset
    st.markdown(f"##### 📈 Performance Comparativa Cumulata (Base 100)")
    palette = ["#00e676", "#ff9900", "#38bdf8", "#bc8cff", "#f85149", "#e3b341", "#f0883e", "#2ea043", "#58a6ff", "#db61a2"]
    fig_equity = go.Figure()

    if "🏛️ Portafoglio Completo" in selected_instruments and not sr_port.empty:
        p_cum = (1.0 + sr_port).cumprod() * 100.0
        fig_equity.add_trace(go.Scatter(
            x=p_cum.index, y=p_cum,
            mode="lines", name="🏛️ Portafoglio Completo",
            line=dict(color="#00e676", width=2.6),
            hovertemplate="<b>Portafoglio:</b> %{y:.2f}<br>Data: %{x|%Y-%m-%d}<extra></extra>"
        ))
        p_hwm = p_cum.cummax()
        fig_equity.add_trace(go.Scatter(
            x=p_hwm.index, y=p_hwm,
            mode="lines", name="High-Water Mark (Portafoglio)",
            line=dict(color="#00e676", width=1.0, dash="dash"),
            opacity=0.6,
            hovertemplate="<b>HWM:</b> %{y:.2f}<extra></extra>"
        ))

    if "🎯 Benchmark (SPY)" in selected_instruments and not sr_bm.empty:
        bm_cum = (1.0 + sr_bm).cumprod() * 100.0
        fig_equity.add_trace(go.Scatter(
            x=bm_cum.index, y=bm_cum,
            mode="lines", name="🎯 Benchmark (SPY)",
            line=dict(color="#ff9900", width=2.0),
            hovertemplate="<b>SPY:</b> %{y:.2f}<extra></extra>"
        ))

    color_idx = 2
    for inst in selected_instruments:
        if inst.startswith("🔹 "):
            tk = inst.replace("🔹 ", "").strip()
            if not df_returns_filtered.empty and tk in df_returns_filtered.columns:
                s_asset = df_returns_filtered[tk].dropna()
                if not s_asset.empty:
                    s_cum = (1.0 + s_asset).cumprod() * 100.0
                    c_color = palette[color_idx % len(palette)]
                    color_idx += 1
                    fig_equity.add_trace(go.Scatter(
                        x=s_cum.index, y=s_cum,
                        mode="lines", name=f"🔹 {tk}",
                        line=dict(color=c_color, width=1.6),
                        hovertemplate=f"<b>{tk}:</b> %{{y:.2f}}<extra></extra>"
                    ))

    fig_equity.update_layout(
        template="plotly_dark", height=390,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=11, color="#ffffff"), bgcolor="rgba(22, 27, 34, 0.6)",
            bordercolor="rgba(255,255,255,0.08)", borderwidth=1
        ),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Valore Base 100")
    )
    apply_plotly_theme(fig_equity)
    st.plotly_chart(fig_equity, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    # 2. Chart: Underwater Drawdown Area
    st.markdown(f"##### 🔻 Curva Underwater Drawdown per `{focus_label}` (% da Massimo Precedente)")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dd_series.index, y=dd_series,
        mode="lines", name=f"Drawdown ({focus_label})",
        line=dict(color="#f85149", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(248, 81, 73, 0.25)",
        hovertemplate="<b>Drawdown:</b> %{y:.2f}%<br>Data: %{x|%Y-%m-%d}<extra></extra>"
    ))
    fig_dd.add_hline(y=-max_dd, line_dash="dot", line_color="#ff4444", annotation_text=f"Max DD: -{max_dd:.2f}%", annotation_position="bottom right", annotation_font_color="#ff4444")
    fig_dd.update_layout(
        template="plotly_dark", height=240,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Drawdown %", ticksuffix="%")
    )
    apply_plotly_theme(fig_dd)
    st.plotly_chart(fig_dd, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    # 3. Top 5 Drawdown Episodes Table
    st.markdown(f"##### 🏆 Top 5 Crisi / Episodi di Drawdown Storico per `{focus_label}`")
    if not top_episodes.empty:
        col_cfg_dd = {
            "start_date": st.column_config.TextColumn("Inizio Crisi"),
            "trough_date": st.column_config.TextColumn("Minimo Toccato (Valle)"),
            "recovery_date": st.column_config.TextColumn("Data Recupero Totale"),
            "max_drawdown_pct": st.column_config.NumberColumn("Perdita Massima (%)", format="-%.2f%%"),
            "days_to_trough": st.column_config.NumberColumn("Giorni alla Valle", format="%d gg"),
            "recovery_days": st.column_config.NumberColumn("Giorni per Recupero", format="%d gg"),
            "total_days": st.column_config.NumberColumn("Durata Totale", format="%d gg"),
            "status": st.column_config.TextColumn("Stato Episodio")
        }
        st.dataframe(top_episodes, column_config=col_cfg_dd, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun episodio di drawdown rilevante (> 0.01%) nella serie temporale analizzata.")


# ==============================================================================
# TAB 2: MATRICE RENDIMENTI MENSILI & ANNUALI (QUANT HEATMAP)
# ==============================================================================
elif active_time_tab == "🗓️ Matrice Rendimenti Mensili & Annuali":
    matrix_instrument_options = ["🏛️ Portafoglio Completo", "🎯 Benchmark (SPY)"] + [f"🔹 {t}" for t in active_tickers]
    
    col_hm1, col_hm2 = st.columns([2.5, 2.5])
    with col_hm1:
        selected_matrix_inst = st.selectbox(
            "🔍 Scegli quale strumento analizzare nella Matrice Mensile:",
            options=matrix_instrument_options,
            index=0,
            help="Puoi visualizzare la tavola periodica dei rendimenti dell'intero portafoglio oppure di qualsiasi singolo titolo azionario o crypto."
        )
    with col_hm2:
        st.markdown(r"""
        <div style="padding-top: 25px; font-size: 12.5px; color: #8b949e;">
            💡 <i>I rendimenti mensili sono calcolati con capitalizzazione geometrica continua \(\prod (1 + r_t) - 1\).</i>
        </div>
        """, unsafe_allow_html=True)

    if selected_matrix_inst == "🏛️ Portafoglio Completo":
        target_series = sr_port
        target_label = "Portafoglio Completo"
    elif selected_matrix_inst == "🎯 Benchmark (SPY)":
        target_series = sr_bm
        target_label = "Benchmark SPY"
    else:
        tk_name = selected_matrix_inst.replace("🔹 ", "").strip()
        target_series = df_returns_filtered[tk_name].dropna() if (not df_returns_filtered.empty and tk_name in df_returns_filtered.columns) else sr_port
        target_label = tk_name

    if target_series.empty:
        st.warning(f"Serie storica insufficiente per `{target_label}`.")
        st.stop()

    df_matrix = compute_monthly_return_matrix(target_series)
    if df_matrix.empty:
        st.warning("Dati storici insufficienti per costruire la matrice mensile dei rendimenti.")
        st.stop()

    all_months = df_matrix.drop(columns=["YTD"]).values.flatten()
    valid_months = all_months[~np.isnan(all_months)]
    
    pos_months = np.sum(valid_months > 0)
    win_rate = (pos_months / len(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    best_m = float(np.max(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    worst_m = float(np.min(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    mean_m = float(np.mean(valid_months) * 100.0) if len(valid_months) > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(f"Mesi Positivi ({target_label})", f"{win_rate:.1f}%", f"{pos_months} su {len(valid_months)} mesi", positive=win_rate >= 55.0)
    with c2:
        metric_card("Miglior Mese Storico", f"+{best_m:.2f}%", "Picco di rendimento mensile", positive=True)
    with c3:
        metric_card("Peggior Mese Storico", f"{worst_m:.2f}%", "Maggiore contrazione mensile", positive=False)
    with c4:
        metric_card("Rendimento Medio Mensile", f"{mean_m:+.2f}%", "Media aritmetica dei mesi", positive=mean_m >= 0)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # 1. Performance Table Heatmap Style
    st.markdown(f"##### 🗓️ Matrice Rendimenti Mensili & YTD per `{target_label}` (% Geometrica)")
    df_disp_mat = (df_matrix * 100.0).copy()
    
    def color_returns(val):
        if pd.isna(val):
            return "color: #484f58; background-color: rgba(255,255,255,0.02);"
        if val > 0:
            intensity = min(0.6, val / 15.0)
            return f"background-color: rgba(0, 230, 118, {intensity:.2f}); color: #ffffff; font-weight: 600;"
        elif val < 0:
            intensity = min(0.6, abs(val) / 15.0)
            return f"background-color: rgba(248, 81, 73, {intensity:.2f}); color: #ffffff; font-weight: 600;"
        return "color: #c9d1d9;"

    styler_mat = df_disp_mat.style.format("{:+.2f}%", na_rep="-")
    if hasattr(styler_mat, "map"):
        styler_mat = styler_mat.map(color_returns)
    elif hasattr(styler_mat, "applymap"):
        styler_mat = styler_mat.applymap(color_returns)

    st.dataframe(styler_mat, use_container_width=True)

    # 2. Bar Chart YTD Annual Returns
    st.markdown(f"##### 📊 Rendimento Cumulato per Anno Solare (YTD Comparison - `{target_label}`)")
    df_ytd = df_matrix[["YTD"]].reset_index().rename(columns={"Year": "Anno", "YTD": "Rendimento %"})
    df_ytd["Rendimento %"] = df_ytd["Rendimento %"] * 100.0
    df_ytd["Colore"] = np.where(df_ytd["Rendimento %"] >= 0, "#00e676", "#f85149")

    fig_ytd = go.Figure(go.Bar(
        x=df_ytd["Anno"].astype(str),
        y=df_ytd["Rendimento %"],
        marker_color=df_ytd["Colore"],
        text=df_ytd["Rendimento %"].apply(lambda v: f"{v:+.2f}%"),
        textposition="outside",
        cliponaxis=False
    ))
    fig_ytd.update_layout(
        template="plotly_dark", height=280,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Rendimento Annuale %", ticksuffix="%")
    )
    apply_plotly_theme(fig_ytd)
    st.plotly_chart(fig_ytd, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})


# ==============================================================================
# TAB 3: RISCHIO MOBILE DINAMICO (ROLLING METRICS)
# ==============================================================================
elif active_time_tab == "🌊 Rischio Mobile Dinamico (Rolling Metrics)":
    rolling_target_options = ["🏛️ Portafoglio Completo"] + [f"🔹 {t}" for t in active_tickers]
    
    col_w1, col_w2, col_w3 = st.columns([2, 1.5, 2.5])
    with col_w1:
        roll_window_opt = st.select_slider(
            "⏱️ Finestra Mobile (Rolling Window):",
            options=[21, 60, 90, 126, 252],
            value=60,
            format_func=lambda w: {21: "21 Giorni (1 Mese)", 60: "60 Giorni (Bimestre)", 90: "90 Giorni (Trimestre)", 126: "126 Giorni (Semestre)", 252: "252 Giorni (1 Anno)"}[w],
            help="Definisce il numero di sedute consecutive su cui calcolare le metriche dinamiche."
        )
    with col_w2:
        selected_roll_target = st.selectbox(
            "🎯 Strumento Target:",
            options=rolling_target_options,
            index=0,
            help="Scegli quale strumento sottoporre al calcolo delle metriche rolling."
        )
    with col_w3:
        st.markdown("""
        <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 6px; margin-top: 5px; font-size: 12.5px; color: #ffb74d;">
            <b>💡 Perché l'analisi Rolling?</b> Evidenzia i cambi di regime e il <i>Risk Drift</i> temporale, isolando picchi anomali di volatilità o di Beta.
        </div>
        """, unsafe_allow_html=True)

    if selected_roll_target == "🏛️ Portafoglio Completo":
        target_roll_sr = sr_port
        target_roll_label = "Portafoglio Completo"
    else:
        tk_roll = selected_roll_target.replace("🔹 ", "").strip()
        target_roll_sr = df_returns_filtered[tk_roll].dropna() if (not df_returns_filtered.empty and tk_roll in df_returns_filtered.columns) else sr_port
        target_roll_label = tk_roll

    df_roll = compute_rolling_risk_metrics(target_roll_sr, sr_bm, window=roll_window_opt, rf_rate=active_rf_rate)

    if df_roll.empty:
        st.warning(f"Storico insufficiente per `{target_roll_label}` con finestra mobile di {roll_window_opt} sedute.")
        st.stop()

    # 1. Chart: Rolling Volatility vs Rolling Sharpe
    st.markdown(f"##### ⚡ Volatilità Annualizzata & Sharpe Ratio Mobile per `{target_roll_label}` ({roll_window_opt} Giorni)")
    fig_roll1 = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_roll1.add_trace(
        go.Scatter(
            x=df_roll.index, y=df_roll["Rolling_Vol_Ann"],
            mode="lines", name="Volatilità Annualizzata (%)",
            line=dict(color="#f85149", width=2.0),
            hovertemplate="<b>Volatilità:</b> %{y:.2f}%<br>Data: %{x|%Y-%m-%d}<extra></extra>"
        ),
        secondary_y=False
    )
    fig_roll1.add_trace(
        go.Scatter(
            x=df_roll.index, y=df_roll["Rolling_Sharpe"],
            mode="lines", name="Sharpe Ratio Mobile",
            line=dict(color="#00e676", width=2.2),
            hovertemplate="<b>Sharpe:</b> %{y:.2f}<extra></extra>"
        ),
        secondary_y=True
    )
    fig_roll1.add_hline(y=1.0, line_dash="dot", line_color="rgba(0,230,118,0.5)", secondary_y=True)
    fig_roll1.update_layout(
        template="plotly_dark", height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=11, color="#ffffff"), bgcolor="rgba(22, 27, 34, 0.6)",
            bordercolor="rgba(255,255,255,0.08)", borderwidth=1
        ),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None)
    )
    fig_roll1.update_yaxes(title_text="Volatilità Annualizzata (%)", secondary_y=False, ticksuffix="%", gridcolor="rgba(255,255,255,0.06)")
    fig_roll1.update_yaxes(title_text="Sharpe Ratio", secondary_y=True, gridcolor="rgba(255,255,255,0.06)")
    apply_plotly_theme(fig_roll1)
    st.plotly_chart(fig_roll1, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    # 2. Chart: Rolling Beta & Correlation with SPY
    if "Rolling_Beta" in df_roll.columns:
        st.markdown(f"##### 🎯 Beta di Mercato & Correlazione Mobile vs Benchmark ({roll_window_opt} Giorni)")
        fig_roll2 = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig_roll2.add_trace(
            go.Scatter(
                x=df_roll.index, y=df_roll["Rolling_Beta"],
                mode="lines", name="Market Beta (vs SPY)",
                line=dict(color="#38bdf8", width=2.0),
                hovertemplate="<b>Beta:</b> %{y:.2f}<br>Data: %{x|%Y-%m-%d}<extra></extra>"
            ),
            secondary_y=False
        )
        fig_roll2.add_trace(
            go.Scatter(
                x=df_roll.index, y=df_roll["Rolling_Correlation"],
                mode="lines", name="Correlazione Pearson (ρ)",
                line=dict(color="#bc8cff", width=1.8, dash="dash"),
                hovertemplate="<b>Correlazione:</b> %{y:.2f}<extra></extra>"
            ),
            secondary_y=True
        )
        fig_roll2.add_hline(y=1.0, line_dash="dot", line_color="rgba(56,189,248,0.5)", secondary_y=False)
        fig_roll2.update_layout(
            template="plotly_dark", height=320,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                font=dict(size=11, color="#ffffff"), bgcolor="rgba(22, 27, 34, 0.6)",
                bordercolor="rgba(255,255,255,0.08)", borderwidth=1
            ),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None)
        )
        fig_roll2.update_yaxes(title_text="Beta di Mercato (β)", secondary_y=False, gridcolor="rgba(255,255,255,0.06)")
        fig_roll2.update_yaxes(title_text="Correlazione (ρ)", secondary_y=True, gridcolor="rgba(255,255,255,0.06)", range=[-0.2, 1.05])
        apply_plotly_theme(fig_roll2)
        st.plotly_chart(fig_roll2, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})


# ==============================================================================
# TAB 4: STAGIONALITÀ & PATTERN CALENDARI
# ==============================================================================
elif active_time_tab == "📊 Stagionalità & Pattern Calendari":
    seas_target_options = ["🏛️ Portafoglio Completo", "🎯 Benchmark (SPY)"] + [f"🔹 {t}" for t in active_tickers]
    selected_seas_target = st.selectbox(
        "🔍 Seleziona Strumento per la Stagionalità:",
        options=seas_target_options,
        index=0
    )

    if selected_seas_target == "🏛️ Portafoglio Completo":
        target_seas_sr = sr_port
        target_seas_label = "Portafoglio Completo"
    elif selected_seas_target == "🎯 Benchmark (SPY)":
        target_seas_sr = sr_bm
        target_seas_label = "Benchmark SPY"
    else:
        tk_s = selected_seas_target.replace("🔹 ", "").strip()
        target_seas_sr = df_returns_filtered[tk_s].dropna() if (not df_returns_filtered.empty and tk_s in df_returns_filtered.columns) else sr_port
        target_seas_label = tk_s

    if target_seas_sr.empty:
        st.warning(f"Dati insufficienti per `{target_seas_label}`.")
        st.stop()

    seas = compute_seasonality_patterns(target_seas_sr)
    day_df = seas["day_stats"]
    month_df = seas["month_stats"]

    st.markdown(f"##### 📅 Rendimenti Medi & Win Rate per Giorno della Settimana (`{target_seas_label}`)")
    c_d1, c_d2 = st.columns([1.5, 1.0])
    
    with c_d1:
        fig_day = go.Figure(go.Bar(
            x=day_df["day_name"],
            y=day_df["Mean_Pct"],
            marker_color=np.where(day_df["Mean_Pct"] >= 0, "#00e676", "#f85149"),
            text=day_df["Mean_Pct"].apply(lambda v: f"{v:+.2f}%"),
            textposition="outside",
            cliponaxis=False
        ))
        fig_day.update_layout(
            template="plotly_dark", height=290,
            margin=dict(l=20, r=20, t=25, b=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Rendimento Medio %", ticksuffix="%")
        )
        apply_plotly_theme(fig_day)
        st.plotly_chart(fig_day, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with c_d2:
        st.markdown("**Statistiche Dettagliate Infrasettimanali**")
        cfg_d = {
            "day_name": st.column_config.TextColumn("Giorno"),
            "Mean_Pct": st.column_config.NumberColumn("Rendimento Medio", format="%+.2f%%"),
            "Win_Rate": st.column_config.ProgressColumn("Win Rate", format="%.1f%%", min_value=0, max_value=100),
            "Vol_Ann": st.column_config.NumberColumn("Volatilità Ann.", format="%.1f%%"),
            "Count": st.column_config.NumberColumn("Sedute", format="%d")
        }
        st.dataframe(day_df, column_config=cfg_d, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(f"##### 🗓️ Rendimenti Medi per Mese dell'Anno (`{target_seas_label}`)")
    fig_m = go.Figure(go.Bar(
        x=month_df["month_name"],
        y=month_df["Mean_Pct"],
        marker_color=np.where(month_df["Mean_Pct"] >= 0, "#58a6ff", "#f85149"),
        text=month_df["Mean_Pct"].apply(lambda v: f"{v:+.2f}%"),
        textposition="outside",
        cliponaxis=False
    ))
    fig_m.update_layout(
        template="plotly_dark", height=290,
        margin=dict(l=20, r=20, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Rendimento Medio Mensile %", ticksuffix="%")
    )
    apply_plotly_theme(fig_m)
    st.plotly_chart(fig_m, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})


# ==============================================================================
# TAB 5: CONFRONTO SIDE-BY-SIDE & SNAPSHOT DB
# ==============================================================================
elif active_time_tab == "⚖️ Confronto Side-by-Side & Snapshot DB":
    st.markdown("### ⚖️ Studio Differenziale Point-in-Time & Audit Snapshot")
    st.caption("Confronta due punti storici, esamina la rotazione dei pesi, il Portfolio Turnover Ratio, i flussi di capitale e i lotti FIFO.")

    db_host = st.session_state.get("db_host", "localhost")
    db_port = int(st.session_state.get("db_port", 3306))
    db_user = st.session_state.get("db_user", "root")
    db_pass = st.session_state.get("db_pass", "root")
    db_name = st.session_state.get("db_name", "investment_risk_bi")
    offline_mode = st.session_state.get("offline_mode", False)

    engine = None
    avail_portfolios = []

    if not offline_mode:
        try:
            engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
            with engine.connect() as conn:
                port_rows = conn.execute(sqlt("""
                    SELECT DISTINCT p.name 
                    FROM portfolios p
                    JOIN portfolio_snapshots s ON p.portfolio_id = s.portfolio_id
                    ORDER BY p.name ASC
                """)).fetchall()
                avail_portfolios = [r[0] for r in port_rows]
        except Exception:
            avail_portfolios = []

    df_pos_a = pd.DataFrame()
    df_pos_b = pd.DataFrame()
    label_a_title = "Snapshot A"
    label_b_title = "Snapshot B"
    meta_a = {}
    meta_b = {}

    saved_profiles_list = list_saved_portfolio_profiles()
    saved_profile_names = [p.get("name") for p in saved_profiles_list if p.get("name")]

    # Selettore Modalità Origine Dati a 3 Vie
    comp_sources = [
        "💾 Snapshot Archiviati su Database MySQL", 
        "⚡ Confronto Live Point-in-Time (Oggi vs Data Storica)",
        "📂 Confronto tra Profili Multi-Portafoglio (Wealth Hub)"
    ]
    def_source_idx = 1 if has_real else (2 if len(saved_profile_names) >= 2 else (0 if avail_portfolios else 1))
    selected_source = st.radio("Seleziona Sorgente del Confronto:", comp_sources, index=def_source_idx, horizontal=True)

    if selected_source == "💾 Snapshot Archiviati su Database MySQL":
        if not avail_portfolios:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 16px 20px; margin-top: 10px; margin-bottom: 15px;">
                <div style="color: #38bdf8; font-weight: 700; font-size: 15px; margin-bottom: 4px;">🗄️ Database Snapshot & Data Warehouse Lineage</div>
                <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                    Nessuno snapshot archiviato trovato su <b>{db_name}</b> (MySQL offline o primo avvio).<br>
                    Puoi salvare uno snapshot permanente dalla <b>Control Room</b> oppure utilizzare le altre 2 modalità qui sopra per confrontare il portafoglio corrente o profili salvati.
                </div>
            </div>
            """, unsafe_allow_html=True)
            try:
                st.page_link("0_Control_Room.py", label="💼 Vai alla Control Room per archiviare uno snapshot", icon="📥")
            except Exception:
                pass
        else:
            c_db_p1, c_db_p2 = st.columns(2)
            with c_db_p1:
                default_p = st.session_state.get("portfolio_name", avail_portfolios[0])
                if default_p not in avail_portfolios:
                    default_p = avail_portfolios[0]
                selected_db_port = st.selectbox("💼 Scegli Portafoglio DB:", avail_portfolios, index=avail_portfolios.index(default_p))
            
            try:
                with engine.connect() as conn:
                    run_rows = conn.execute(sqlt("""
                        SELECT DISTINCT s.run_name 
                        FROM portfolio_snapshots s
                        JOIN portfolios p ON s.portfolio_id = p.portfolio_id
                        WHERE p.name = :pname AND s.run_name IS NOT NULL AND s.run_name != ''
                        ORDER BY s.run_name ASC
                    """), {"pname": selected_db_port}).fetchall()
                    avail_runs = ["Tutte le Run"] + [r[0] for r in run_rows]
            except Exception:
                avail_runs = ["Tutte le Run"]

            with c_db_p2:
                selected_run_tag = st.selectbox("🏷️ Filtra per Run Tag / Operazione:", avail_runs, index=0)

            run_param = None if selected_run_tag == "Tutte le Run" else selected_run_tag
            df_history = get_all_snapshots_history(engine, portfolio_name=selected_db_port, run_name=run_param)

            if not df_history.empty:
                df_history["calc_date"] = pd.to_datetime(df_history["calc_date"])
                df_history["display_label"] = df_history.apply(
                    lambda r: f"📅 {r['calc_date'].strftime('%Y-%m-%d %H:%M')} | 🏷️ {r['run_name'] or 'Standard'} | 💰 € {r['total_value']:,.2f} | ID: {r['run_id']}",
                    axis=1
                )

                options_list = list(df_history["display_label"])
                idx_a = len(options_list) - 1
                idx_b = max(0, len(options_list) - 2)

                col_sel_a, col_sel_b = st.columns(2)
                with col_sel_a:
                    label_a = st.selectbox("🅰️ Seleziona Snapshot A (Target / Recente):", options_list, index=idx_a)
                    snap_a = df_history[df_history["display_label"] == label_a].iloc[0]
                    label_a_title = f"Snapshot A ({snap_a['calc_date'].strftime('%d/%m/%Y %H:%M')})"
                    meta_a = snap_a.to_dict()
                with col_sel_b:
                    label_b = st.selectbox("🅱️ Seleziona Snapshot B (Confronto / Precedente):", options_list, index=idx_b)
                    snap_b = df_history[df_history["display_label"] == label_b].iloc[0]
                    label_b_title = f"Snapshot B ({snap_b['calc_date'].strftime('%d/%m/%Y %H:%M')})"
                    meta_b = snap_b.to_dict()

                df_pos_a = get_snapshot_positions_by_id(engine, snap_a["snapshot_id"])
                df_pos_b = get_snapshot_positions_by_id(engine, snap_b["snapshot_id"])

    elif selected_source == "📂 Confronto tra Profili Multi-Portafoglio (Wealth Hub)":
        if len(saved_profile_names) < 2:
            st.info("Salva almeno 2 profili di portafoglio nel Wealth Hub (es. Portafoglio Azionario, Crypto, o Master) per confrontarli direttamente.")
        else:
            col_mp1, col_mp2 = st.columns(2)
            with col_mp1:
                sel_p_a = st.selectbox("🅰️ Seleziona Profilo A:", saved_profile_names, index=0)
                prof_a_data = load_portfolio_profile(sel_p_a)
                df_pos_a = pd.DataFrame(prof_a_data.get("positions", [])) if prof_a_data else pd.DataFrame()
                label_a_title = sel_p_a
                meta_a = prof_a_data.get("metrics", {}) if prof_a_data else {}
            with col_mp2:
                sel_p_b = st.selectbox("🅱️ Seleziona Profilo B:", saved_profile_names, index=min(1, len(saved_profile_names) - 1))
                prof_b_data = load_portfolio_profile(sel_p_b)
                df_pos_b = pd.DataFrame(prof_b_data.get("positions", [])) if prof_b_data else pd.DataFrame()
                label_b_title = sel_p_b
                meta_b = prof_b_data.get("metrics", {}) if prof_b_data else {}

    else:
        # Modalità Live Point-in-Time con Ricostruzione Matematica Reale
        col_lp1, col_lp2 = st.columns(2)
        with col_lp1:
            tot_today_val = float(pos["current_value"].sum()) if not pos.empty and "current_value" in pos.columns else 0.0
            st.markdown(f"**🅰️ Snapshot A**: Stato Attivo Oggi (**€ {tot_today_val:,.2f}**)")
            df_pos_a = pos.copy()
            label_a_title = "Portafoglio Live (Oggi)"
            meta_a = {
                "sharpe_ratio": float(ret_m.get("sharpe_ratio", 0.0) or 0.0),
                "volatility_ann_pct": float(ret_m.get("volatility_ann_pct", 0.0) or 0.0),
                "var_95_pct": float(mk_m.get("var_historical_95", 0.0) or mk_m.get("var_parametric_95", 0.0) or 0.0),
                "hhi_index": float(results.get("metrics", {}).get("concentration", {}).get("hhi", 0.0) or 0.0)
            }
            
        with col_lp2:
            hist_compare_mode = st.selectbox(
                "🅱️ Scegli Data Storica di Riferimento per Snapshot B:",
                options=["6 Mesi Fa", "12 Mesi Fa (1 Anno)", "Inizio Anno Corrente (YTD)", "3 Mesi Fa", "Data Personalizzata (Calendario)"],
                index=0
            )

            if not raw_sr_port.empty:
                max_dt = pd.to_datetime(raw_sr_port.index.max()).date()
            else:
                max_dt = datetime.now().date()

            if hist_compare_mode == "6 Mesi Fa":
                target_dt_b = max_dt - timedelta(days=182)
            elif hist_compare_mode == "12 Mesi Fa (1 Anno)":
                target_dt_b = max_dt - timedelta(days=365)
            elif hist_compare_mode == "Inizio Anno Corrente (YTD)":
                target_dt_b = datetime(max_dt.year, 1, 1).date()
            elif hist_compare_mode == "3 Mesi Fa":
                target_dt_b = max_dt - timedelta(days=91)
            else:
                target_dt_b = st.date_input("Scegli Data Storica Esatta:", value=max_dt - timedelta(days=182), max_value=max_dt)

            active_df_tx = results.get("df_tx") if (results.get("df_tx") is not None and not results.get("df_tx").empty) else results.get("df_tx_raw")
            active_df_prices = results.get("df_prices")

            reconst_res = reconstruct_point_in_time_portfolio(
                pos_today=pos,
                sr_port=raw_sr_port,
                returns_df=df_returns,
                target_date=target_dt_b,
                df_tx=active_df_tx,
                df_prices=active_df_prices,
                rf_rate=active_rf_rate
            )
            df_pos_b = reconst_res["df_positions"]
            meta_b = reconst_res["metrics"]
            label_b_title = f"Riferimento ({target_dt_b.strftime('%d/%m/%Y')})"

    # ── ESECUZIONE DEL CONFRONTO MATEMATICO SIDE-BY-SIDE ─────────
    if not df_pos_a.empty or not df_pos_b.empty:
        comp_res = compute_side_by_side_comparison(df_pos_a, df_pos_b)
        df_merged = comp_res["df_merged"]
        tot_val_a = comp_res["tot_val_a"]
        tot_val_b = comp_res["tot_val_b"]
        d_val = comp_res["delta_nav"]
        d_val_pct = comp_res["delta_nav_pct"]
        turnover = comp_res["turnover_pct"]
        cap_reb = comp_res["capital_rebalanced"]
        n_new = comp_res["new_entries_count"]
        n_closed = comp_res["closed_entries_count"]
        n_mod = comp_res["modified_count"]

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        # 1. Cockpit Card Differenziali Top
        st.markdown("##### 🎛️ Cockpit di Variazione Patrimoniale & Ribilanciamento")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card(f"Valore {label_a_title[:18]}", f"€ {tot_val_a:,.2f}", f"Diff vs B: € {d_val:+,.2f}", positive=d_val >= 0)
        with c2:
            metric_card("Variazione Capitale (Δ)", f"{d_val_pct:+.2f}%", f"Valore B: € {tot_val_b:,.2f}", positive=d_val_pct >= 0)
        with c3:
            metric_card("Portfolio Turnover Ratio", f"{turnover:.2f}%", "Intensità di rotazione pesi", positive=turnover < 25.0)
        with c4:
            if cap_reb > 0:
                metric_card("Capitale Transato (Trading)", f"€ {cap_reb:,.2f}", f"{n_new} Ingressi • {n_closed} Uscite", positive=True)
            else:
                n_up = comp_res.get('appreciated_count', 0)
                n_dn = comp_res.get('depreciated_count', 0)
                metric_card("Dinamica Prezzi Mercato", f"€ {d_val:+,.2f}", f"{n_up} 📈 Saliti • {n_dn} 📉 Scesi", positive=d_val >= 0)

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        # 2. Risk & Concentration Drift Matrix
        sh_a = float(meta_a.get("sharpe_ratio") if meta_a.get("sharpe_ratio") is not None else (m.get("sharpe_ratio") or ret_m.get("sharpe_ratio", 0.0) or 0.0))
        sh_b = float(meta_b.get("sharpe_ratio") if meta_b.get("sharpe_ratio") is not None else (m.get("sharpe_ratio") or ret_m.get("sharpe_ratio", 0.0) or 0.0))
        
        vol_a = float(meta_a.get("volatility_ann_pct") if meta_a.get("volatility_ann_pct") is not None else (m.get("volatility_annual_pct") or m.get("volatility_pct") or (m.get("volatility", 0.0)*100) or 0.0))
        vol_b = float(meta_b.get("volatility_ann_pct") if meta_b.get("volatility_ann_pct") is not None else (m.get("volatility_annual_pct") or m.get("volatility_pct") or (m.get("volatility", 0.0)*100) or 0.0))
        
        var_a = float(meta_a.get("var_95_pct") if meta_a.get("var_95_pct") is not None else (m.get("var_95") or m.get("var_parametric_95") or mk_m.get("var_95", 0.0) or 0.0))
        var_b = float(meta_b.get("var_95_pct") if meta_b.get("var_95_pct") is not None else (m.get("var_95") or m.get("var_parametric_95") or mk_m.get("var_95", 0.0) or 0.0))
        
        hhi_a = float(meta_a.get("hhi_index") if meta_a.get("hhi_index") is not None else (m.get("hhi") or m.get("concentration", {}).get("hhi", 0.0) or 0.0))
        hhi_b = float(meta_b.get("hhi_index") if meta_b.get("hhi_index") is not None else (m.get("hhi") or m.get("concentration", {}).get("hhi", 0.0) or 0.0))

        st.markdown("##### ⚡ Matrice di Risk Drift & Concentrazione (Delta Metriche A vs B)")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            metric_card("Sharpe Ratio A vs B", f"{sh_a:.2f} vs {sh_b:.2f}", f"Δ: {sh_a - sh_b:+.2f}", positive=(sh_a - sh_b) >= 0)
        with r2:
            metric_card("Volatilità Ann. A vs B", f"{vol_a:.1f}% vs {vol_b:.1f}%", f"Δ: {vol_a - vol_b:+.1f}%", positive=(vol_a - vol_b) <= 0)
        with r3:
            metric_card("VaR 95% A vs B", f"{var_a:.2f}% vs {var_b:.2f}%", f"Δ: {var_a - var_b:+.2f}%", positive=(var_a - var_b) <= 0)
        with r4:
            metric_card("Indice HHI (Concentrazione)", f"{hhi_a:.4f} vs {hhi_b:.4f}", f"Δ: {hhi_a - hhi_b:+.4f}", positive=(hhi_a - hhi_b) <= 0)

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        # 3. Due Donut Chart Affiancati per Allocazione Asset Class
        st.markdown(f"##### 🍩 Confronto Asset Allocation: {label_a_title} vs {label_b_title}")
        c_pie1, c_pie2 = st.columns(2)

        def make_alloc_pie(df_p, title_str):
            if df_p.empty:
                return go.Figure()
            df_g = df_p.groupby("asset_class")["current_value"].sum().reset_index()
            fig = px.pie(
                df_g, values="current_value", names="asset_class",
                hole=0.45,
                color_discrete_sequence=["#38bdf8", "#00e676", "#ff9900", "#bc8cff", "#f85149", "#e3b341"]
            )
            fig.update_layout(
                template="plotly_dark", height=260,
                title=dict(text=title_str, font=dict(size=13, color="#f0f6fc"), x=0.5, xanchor="center"),
                margin=dict(l=10, r=10, t=35, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10, color="#ffffff"))
            )
            apply_plotly_theme(fig)
            return fig

        with c_pie1:
            st.plotly_chart(make_alloc_pie(df_pos_a, f"Allocazione {label_a_title}"), use_container_width=True)
        with c_pie2:
            st.plotly_chart(make_alloc_pie(df_pos_b, f"Allocazione {label_b_title}"), use_container_width=True)

        # 4. Bar Chart Waterfall / Top Gainers & Losers Contributo Delta Controvalore
        if not df_merged.empty:
            st.markdown("##### 📊 Variazione Netta di Controvalore per Singolo Titolo (Δ €)")
            df_bar_diff = df_merged[df_merged["delta_val"].abs() > 0.01].sort_values(by="delta_val", ascending=True)
            
            fig_bar_diff = go.Figure(go.Bar(
                y=df_bar_diff["ticker"],
                x=df_bar_diff["delta_val"],
                orientation="h",
                marker_color=np.where(df_bar_diff["delta_val"] >= 0, "#00e676", "#f85149"),
                text=df_bar_diff["delta_val"].apply(lambda v: f"€ {v:+,.2f}"),
                textposition="outside",
                cliponaxis=False
            ))
            fig_bar_diff.update_layout(
                template="plotly_dark", height=max(280, len(df_bar_diff) * 26),
                margin=dict(l=20, r=40, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Δ Controvalore Netto (€)", tickprefix="€ "),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title=None)
            )
            apply_plotly_theme(fig_bar_diff)
            st.plotly_chart(fig_bar_diff, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        # 5. Tabella Dettagliata Asset-by-Asset con Filtro e Badge
        st.markdown("---")
        st.markdown(f"##### 📋 Tabella Differenziale Analitica Posizioni: `{label_a_title}` vs `{label_b_title}`")
        
        all_status_opts = [
            "🟢 Nuovo Ingresso", 
            "🔴 Chiusura Totale", 
            "⬆️ Acquisto Quote (+Qty)", 
            "⬇️ Vendita Quote (-Qty)", 
            "📈 Apprezzamento (Prezzo +)", 
            "📉 Deprezzamento (Prezzo -)", 
            "⚪ Invariato"
        ]
        
        # Clean unique hash for state binding
        clean_key_suffix = f"{label_a_title}_{label_b_title}".replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").replace(":", "_")

        col_tf1, col_tf2 = st.columns([2, 2])
        with col_tf1:
            search_tk = st.text_input("🔍 Filtra per Ticker o Asset Class:", "", placeholder="Es. GOOGL, PYPL, Crypto, AAPL...", key=f"sbs_search_{clean_key_suffix}")
        with col_tf2:
            avail_statuses = [s for s in all_status_opts if s in df_merged["status"].unique()]
            status_filter = st.multiselect(
                "🚦 Filtra per Stato Posizione:",
                options=all_status_opts,
                default=avail_statuses if avail_statuses else all_status_opts,
                key=f"sbs_status_{clean_key_suffix}"
            )

        df_table_disp = df_merged.copy()
        if search_tk:
            df_table_disp = df_table_disp[
                df_table_disp["ticker"].str.contains(search_tk, case=False, na=False) |
                df_table_disp["asset_class"].str.contains(search_tk, case=False, na=False)
            ]
        if status_filter and len(status_filter) > 0:
            df_table_disp = df_table_disp[df_table_disp["status"].isin(status_filter)]

        col_config_diff = {
            "status": st.column_config.TextColumn("Stato Operativo"),
            "ticker": st.column_config.TextColumn("Ticker"),
            "asset_class": st.column_config.TextColumn("Classe"),
            "qty_net_A": st.column_config.NumberColumn("Quantità A", format="%.4f"),
            "qty_net_B": st.column_config.NumberColumn("Quantità B", format="%.4f"),
            "delta_qty": st.column_config.NumberColumn("Δ Quantità", format="%+.4f"),
            "last_price_A": st.column_config.NumberColumn("Prezzo A (€)", format="€ %.2f"),
            "last_price_B": st.column_config.NumberColumn("Prezzo B (€)", format="€ %.2f"),
            "delta_price": st.column_config.NumberColumn("Δ Prezzo (€)", format="€ %+.2f"),
            "current_value_A": st.column_config.NumberColumn("Valore A (€)", format="€ %.2f"),
            "current_value_B": st.column_config.NumberColumn("Valore B (€)", format="€ %.2f"),
            "delta_val": st.column_config.NumberColumn("Δ Valore (€)", format="€ %+.2f"),
            "weight_pct_A": st.column_config.NumberColumn("Peso A (%)", format="%.2f%%"),
            "weight_pct_B": st.column_config.NumberColumn("Peso B (%)", format="%.2f%%"),
            "delta_weight": st.column_config.NumberColumn("Δ Peso (%)", format="%+.2f%%")
        }

        cols_to_show = [
            "status", "ticker", "asset_class", 
            "qty_net_A", "qty_net_B", "delta_qty",
            "last_price_A", "last_price_B", "delta_price",
            "current_value_A", "current_value_B", "delta_val",
            "weight_pct_A", "weight_pct_B", "delta_weight"
        ]
        
        st.dataframe(
            df_table_disp[cols_to_show],
            column_config=col_config_diff,
            use_container_width=True,
            hide_index=True,
            key=f"sbs_grid_{clean_key_suffix}"
        )

        # Download CSV Audit Report
        csv_diff_bytes = df_table_disp[cols_to_show].to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Esporta Report Differenziale (CSV)",
            data=csv_diff_bytes,
            file_name="ARGUS_SideBySide_Audit.csv",
            mime="text/csv",
            key=f"sbs_csv_btn_{clean_key_suffix}"
        )

        # 6. 🔎 ISPEZIONE SINGOLO TITOLO (ASSET DRILL-DOWN & LOTTI FIFO)
        st.markdown("---")
        st.markdown("##### 🔎 Deep-Dive Singolo Titolo & Audit Lotti FIFO")
        st.caption("Ispeziona nel dettaglio i prezzi di carico, le vendite e i lotti fiscali di qualsiasi titolo coinvolto nel confronto:")

        all_diff_tickers = sorted(list(df_merged["ticker"].unique()))
        selected_drill_tk = st.selectbox(
            "Seleziona Ticker per il Deep-Dive:",
            options=["-- Seleziona Titolo --"] + all_diff_tickers,
            index=0,
            help="Mostra il dettaglio dei lotti acquistati, venduti e l'impatto fiscale/PMC."
        )

        if selected_drill_tk != "-- Seleziona Titolo --":
            drill_row = df_merged[df_merged["ticker"] == selected_drill_tk].iloc[0]
            
            c_d1, c_d2, c_d3, c_d4 = st.columns(4)
            with c_d1:
                metric_card("Stato Transazione", drill_row["status"], f"Classe: {drill_row['asset_class']}")
            with c_d2:
                metric_card("Variazione Quantità", f"{drill_row['delta_qty']:+.4f}", f"A: {drill_row['qty_net_A']:.2f} | B: {drill_row['qty_net_B']:.2f}")
            with c_d3:
                metric_card("Variazione Controvalore", f"€ {drill_row['delta_val']:+,.2f}", f"Valore A: € {drill_row['current_value_A']:,.2f}", positive=drill_row['delta_val'] >= 0)
            with c_d4:
                metric_card("Variazione Peso", f"{drill_row['delta_weight']:+.2f}%", f"Peso A: {drill_row['weight_pct_A']:.2f}% | B: {drill_row['weight_pct_B']:.2f}%")

            # Controllo se ci sono trade chiusi registrati nel bundle
            closed_dict = results.get("closed_trades", {})
            df_closed_all = closed_dict.get("df_closed_all", pd.DataFrame()) if isinstance(closed_dict, dict) else pd.DataFrame()
            if not df_closed_all.empty and "ticker" in df_closed_all.columns:
                drill_closed = df_closed_all[df_closed_all["ticker"] == selected_drill_tk]
                if not drill_closed.empty:
                    st.markdown(f"**📜 Lotti Fiscali Chiusi / Liquidati per `{selected_drill_tk}` (Audit FIFO)**")
                    cfg_cl = {
                        "buy_date": st.column_config.TextColumn("Data Acquisto Origine"),
                        "sell_date": st.column_config.TextColumn("Data Liquidazione"),
                        "qty": st.column_config.NumberColumn("Quantità Chiusa", format="%.4f"),
                        "buy_price_eur": st.column_config.NumberColumn("Prezzo Carico (€)", format="€ %.2f"),
                        "sell_price_eur": st.column_config.NumberColumn("Prezzo Vendita (€)", format="€ %.2f"),
                        "cost_basis_eur": st.column_config.NumberColumn("Costo Base (€)", format="€ %.2f"),
                        "proceeds_eur": st.column_config.NumberColumn("Incasso Vendita (€)", format="€ %.2f"),
                        "realized_pnl_eur": st.column_config.NumberColumn("Plus/Minusvalenza (€)", format="€ %+.2f"),
                        "realized_pnl_pct": st.column_config.NumberColumn("Rendimento (%)", format="%+.2f%%"),
                        "holding_days": st.column_config.NumberColumn("Giorni Detenzione", format="%d gg"),
                        "outcome": st.column_config.TextColumn("Esito Fiscale")
                    }
                    st.dataframe(drill_closed, column_config=cfg_cl, use_container_width=True, hide_index=True)
                else:
                    st.info(f"Nessun lotto chiuso/venduto registrato per `{selected_drill_tk}` (posizione accumulata o aperta).")

        # 7. Registro Completo DuckDB
        if selected_source == "💾 Snapshot Archiviati su Database MySQL" and 'df_history' in locals() and not df_history.empty:
            st.markdown("---")
            with st.expander("⚡ Vista Analitica Aggregata DuckDB (Trend Vettorizzato & Medie Mobili)", expanded=False):
                from core.duckdb_engine import compute_duckdb_temporal_snapshot_analytics
                duck_snap = compute_duckdb_temporal_snapshot_analytics(df_history)
                if duck_snap.get("success") and not duck_snap["df"].empty:
                    st.caption(f"🚀 Esecuzione C++ SIMD Vettorizzata in **{duck_snap['latency_ms']:.2f} ms**")
                    cfg_duck = {
                        "calc_date": st.column_config.TextColumn("Data e Ora Snapshot"),
                        "run_name": st.column_config.TextColumn("Nome Rilevazione"),
                        "valore_portafoglio_eur": st.column_config.NumberColumn("Valore Portafoglio (€)", format="€ %.2f"),
                        "delta_valore_step_eur": st.column_config.NumberColumn("Δ Valore Step (€)", format="€ %+.2f"),
                        "delta_pct_step": st.column_config.NumberColumn("Δ % Step", format="%+.2f%%"),
                        "media_mobile_3_snapshot": st.column_config.NumberColumn("Media Mobile (3 Snap)", format="€ %.2f")
                    }
                    st.dataframe(duck_snap["df"], column_config=cfg_duck, use_container_width=True, hide_index=True)
