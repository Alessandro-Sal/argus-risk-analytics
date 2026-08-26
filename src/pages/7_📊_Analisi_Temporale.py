import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

import importlib
import core.ui_utils
import core.duckdb_engine
import core.temporal_engine
importlib.reload(core.ui_utils)
importlib.reload(core.duckdb_engine)
importlib.reload(core.temporal_engine)

from core.sidebar import render_sidebar
from core.fetcher import get_engine
from core.db_exporter import get_all_snapshots_history, get_snapshot_positions_by_id
from core.ui_utils import (
    apply_plotly_theme, inject_custom_css, render_command_bar, 
    metric_card, ensure_risk_bundle_loaded, render_sandbox_banner
)
from core.temporal_engine import (
    compute_monthly_return_matrix,
    compute_rolling_risk_metrics,
    compute_underwater_drawdowns,
    compute_seasonality_patterns,
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
render_sandbox_banner(page_key="p7")

sr_port = results.get("portfolio_return", pd.Series(dtype=float))
sr_bm = results.get("benchmark_return", pd.Series(dtype=float))
df_returns = results.get("returns", pd.DataFrame())
pos = results.get("positions", pd.DataFrame())
m = results.get("metrics", {})
ret_m = m.get("returns", {})
mk_m = m.get("market_risk", {})
active_rf_rate = st.session_state.get("active_rf_rate", 0.035)

# ── System Banner ───────────────────────────────────────────
st.title("📊 Analisi Temporale & Dinamica delle Serie Storiche")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: **{st.session_state.get('portfolio_name', 'Master Wealth')}** • Matrice mensile dei rendimenti, curva underwater, rolling risk metrics, stagionalità e audit trail degli snapshot.")
elif results.get("is_sandbox"):
    st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Matrice mensile dei rendimenti, curva underwater, rolling risk metrics e stagionalità.")
else:
    st.caption("Intelligence multi-temporale per tracciare l'evoluzione del patrimonio, dei rendimenti periodici, della volatilità mobile e degli snapshot storici.")
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
    "🗃️ Registro Snapshot DB & Confronto Side-by-Side": {
        "title": "Audit Trail Immutabile degli Snapshot (MySQL / DuckDB) & Confronto Affiancato",
        "badge": "Data Lineage • Delta Pesi • DuckDB SIMD",
        "badge_color": "#3fb950",
        "category": "Audit Trail & Confronto",
        "desc": "Consultazione del registro storico degli snapshot archiviati nel Data Warehouse, confronto differenziale tra due date di rilevazione e aggregazione vettorizzata DuckDB C++ SIMD."
    }
}

# Risoluzione dello stato attivo con priorità alla sidebar o global jump
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
elif "time_active_tab" not in st.session_state or st.session_state["time_active_tab"] not in time_keys:
    st.session_state["time_active_tab"] = time_keys[0]

curr_idx = time_keys.index(st.session_state["time_active_tab"])

# Spaziatura e Respiro Layout
st.markdown("<div style='margin-top: 14px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# Barra Selettore Compatta Bloomberg Style
c_sel_tm, c_prev_tm, c_next_tm = st.columns([3.8, 0.6, 0.6], vertical_alignment="center")

with c_prev_tm:
    if st.button("◀ Prec.", key="btn_time_prev", use_container_width=True, help="Modulo precedente"):
        new_i = (curr_idx - 1) % len(time_keys)
        st.session_state["target_time_module"] = time_keys[new_i]
        st.rerun()

with c_next_tm:
    if st.button("Succ. ▶", key="btn_time_next", use_container_width=True, help="Modulo successivo"):
        new_i = (curr_idx + 1) % len(time_keys)
        st.session_state["target_time_module"] = time_keys[new_i]
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

# Bloomberg Terminal Header Banner per il Modulo Attivo
st.markdown(f"""
<div style="background: linear-gradient(90deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.85) 100%); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {active_time_info['badge_color']}; border-radius: 8px; padding: 12px 18px; margin-top: 10px; margin-bottom: 22px;">
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


# ==============================================================================
# TAB 1: CURVA CUMULATA & UNDERWATER DRAWDOWN
# ==============================================================================
if active_time_tab == "📈 Curva Cumulata & Drawdown Underwater":
    if sr_port.empty:
        st.warning("Serie storica dei rendimenti di portafoglio non disponibile.")
        st.stop()

    uw_data = compute_underwater_drawdowns(sr_port)
    cum_nav = uw_data["cumulative_nav"]
    hwm = uw_data["hwm"]
    dd_series = uw_data["drawdown_series"]
    max_dd = uw_data["max_drawdown_pct"]
    ulcer = uw_data["ulcer_index"]
    top_episodes = uw_data["top_episodes"]

    tot_val = float(results.get("portfolio_value", pos["current_value"].sum() if not pos.empty and "current_value" in pos.columns else 100000.0))
    cagr = float(ret_m.get("cagr_pct", 0.0) or 0.0)
    sharpe = float(ret_m.get("sharpe_ratio", 0.0) or 0.0)
    calmar = abs(cagr / max_dd) if max_dd > 0 else 0.0

    # Macro KPI Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Patrimonio Attuale", f"€ {tot_val:,.2f}", f"CAGR: {cagr:+.2f}%", positive=cagr >= 0)
    with c2:
        metric_card("Max Drawdown Storico", f"-{max_dd:.2f}%", "Massimo Picco-Valle", positive=False)
    with c3:
        metric_card("Ulcer Index (UI)", f"{ulcer:.2f}", "Indice di Stress Temporale", positive=ulcer < 8.0)
    with c4:
        metric_card("Calmar Ratio (CAGR/MDD)", f"{calmar:.2f}", "Efficienza sui Drawdown", positive=calmar >= 1.0)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # 1. Chart: Cumulative Equity Line + HWM + Benchmark
    st.markdown("##### 📈 Equity Line Cumulata vs High-Water Mark & Benchmark (Base 100)")
    
    fig_equity = go.Figure()
    nav_base100 = cum_nav / cum_nav.iloc[0] * 100.0 if not cum_nav.empty and cum_nav.iloc[0] != 0 else cum_nav * 100.0
    hwm_base100 = hwm / cum_nav.iloc[0] * 100.0 if not cum_nav.empty and cum_nav.iloc[0] != 0 else hwm * 100.0

    fig_equity.add_trace(go.Scatter(
        x=cum_nav.index, y=nav_base100,
        mode="lines", name="Portafoglio (NAV Base 100)",
        line=dict(color="#00e676", width=2.5),
        hovertemplate="<b>Portafoglio:</b> %{y:.2f}<br>Data: %{x|%Y-%m-%d}<extra></extra>"
    ))
    fig_equity.add_trace(go.Scatter(
        x=hwm.index, y=hwm_base100,
        mode="lines", name="High-Water Mark (HWM)",
        line=dict(color="#38bdf8", width=1.5, dash="dash"),
        hovertemplate="<b>HWM:</b> %{y:.2f}<extra></extra>"
    ))

    if sr_bm is not None and not sr_bm.empty:
        bm_cum = (1.0 + sr_bm.reindex(cum_nav.index).fillna(0.0)).cumprod()
        bm_base100 = bm_cum / bm_cum.iloc[0] * 100.0 if not bm_cum.empty and bm_cum.iloc[0] != 0 else bm_cum * 100.0
        fig_equity.add_trace(go.Scatter(
            x=cum_nav.index, y=bm_base100,
            mode="lines", name="Benchmark SPY (Base 100)",
            line=dict(color="#ff9900", width=1.8),
            hovertemplate="<b>Benchmark SPY:</b> %{y:.2f}<extra></extra>"
        ))

    fig_equity.update_layout(
        template="plotly_dark", height=380,
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
    st.markdown("##### 🔻 Curva Underwater Drawdown (% Perdita da Massimo Precedente)")
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dd_series.index, y=dd_series,
        mode="lines", name="Drawdown (%)",
        line=dict(color="#f85149", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(248, 81, 73, 0.25)",
        hovertemplate="<b>Drawdown:</b> %{y:.2f}%<br>Data: %{x|%Y-%m-%d}<extra></extra>"
    ))
    fig_dd.add_hline(y=-max_dd, line_dash="dot", line_color="#ff4444", annotation_text=f"Max Drawdown: -{max_dd:.2f}%", annotation_position="bottom right", annotation_font_color="#ff4444")
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
    st.markdown("##### 🏆 Top 5 Crisi / Episodi di Drawdown Storico")
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
    if sr_port.empty:
        st.warning("Serie storica dei rendimenti non disponibile.")
        st.stop()

    df_matrix = compute_monthly_return_matrix(sr_port)
    if df_matrix.empty:
        st.warning("Dati storici insufficienti per costruire la matrice mensile dei rendimenti.")
        st.stop()

    # KPI Sintetici Mensili
    all_months = df_matrix.drop(columns=["YTD"]).values.flatten()
    valid_months = all_months[~np.isnan(all_months)]
    
    pos_months = np.sum(valid_months > 0)
    win_rate = (pos_months / len(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    best_m = float(np.max(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    worst_m = float(np.min(valid_months) * 100.0) if len(valid_months) > 0 else 0.0
    mean_m = float(np.mean(valid_months) * 100.0) if len(valid_months) > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Mesi Positivi (Win Rate)", f"{win_rate:.1f}%", f"{pos_months} su {len(valid_months)} mesi", positive=win_rate >= 55.0)
    with c2:
        metric_card("Miglior Mese Storico", f"+{best_m:.2f}%", "Picco di rendimento mensile", positive=True)
    with c3:
        metric_card("Peggior Mese Storico", f"{worst_m:.2f}%", "Maggiore contrazione mensile", positive=False)
    with c4:
        metric_card("Rendimento Medio Mensile", f"{mean_m:+.2f}%", "Media aritmetica dei mesi", positive=mean_m >= 0)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # 1. Performance Table Heatmap Style
    st.markdown("##### 🗓️ Matrice Rendimenti Mensili & YTD (% Geometrica)")
    
    # Format dataframe for display with color coding
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

    st.dataframe(
        df_disp_mat.style.format("{:+.2f}%", na_rep="-").applymap(color_returns),
        use_container_width=True
    )

    # 2. Bar Chart YTD Annual Returns
    st.markdown("##### 📊 Rendimento Cumulato per Anno Solare (YTD Comparison)")
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
    if sr_port.empty:
        st.warning("Serie storica dei rendimenti non disponibile.")
        st.stop()

    col_w1, col_w2 = st.columns([2, 3])
    with col_w1:
        roll_window_opt = st.select_slider(
            "⏱️ Finestra Mobile di Calcolo (Rolling Window):",
            options=[21, 60, 90, 126, 252],
            value=60,
            format_func=lambda w: {21: "21 Giorni (1 Mese)", 60: "60 Giorni (Bimestre)", 90: "90 Giorni (Trimestre)", 126: "126 Giorni (Semestre)", 252: "252 Giorni (1 Anno)"}[w],
            help="Definisce il numero di sedute consecutive su cui calcolare le metriche dinamiche."
        )
    with col_w2:
        st.markdown(f"""
        <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 6px; margin-top: 5px; font-size: 12.5px; color: #ffb74d;">
            <b>💡 Perché l'analisi Rolling?</b> Evidenzia i cambi di regime e il <i>Risk Drift</i> temporale, isolando periodi in cui la volatilità o il Beta del portafoglio hanno subito spike anomali.
        </div>
        """, unsafe_allow_html=True)

    df_roll = compute_rolling_risk_metrics(sr_port, sr_bm, window=roll_window_opt, rf_rate=active_rf_rate)

    if df_roll.empty:
        st.warning(f"Storico insufficiente per la finestra mobile di {roll_window_opt} sedute.")
        st.stop()

    # 1. Chart: Rolling Volatility vs Rolling Sharpe
    st.markdown(f"##### ⚡ Volatilità Annualizzata & Sharpe Ratio Mobile ({roll_window_opt} Giorni)")
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
    if sr_port.empty:
        st.warning("Serie storica dei rendimenti non disponibile.")
        st.stop()

    seas = compute_seasonality_patterns(sr_port)
    day_df = seas["day_stats"]
    month_df = seas["month_stats"]

    st.markdown("##### 📅 Rendimenti Medi & Win Rate per Giorno della Settimana (Trading Days)")
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
    st.markdown("##### 🗓️ Rendimenti Medi per Mese dell'Anno (Seasonality Pattern)")
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
# TAB 5: REGISTRO SNAPSHOT DB & CONFRONTO SIDE-BY-SIDE
# ==============================================================================
elif active_time_tab == "🗃️ Registro Snapshot DB & Confronto Side-by-Side":
    db_host = st.session_state.get("db_host", "localhost")
    db_port = int(st.session_state.get("db_port", 3306))
    db_user = st.session_state.get("db_user", "root")
    db_pass = st.session_state.get("db_pass", "root")
    db_name = st.session_state.get("db_name", "investment_risk_bi")
    offline_mode = st.session_state.get("offline_mode", False)

    engine = None
    df_history = pd.DataFrame()

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
                
            if avail_portfolios:
                default_p = st.session_state.get("portfolio_name", avail_portfolios[0])
                if default_p not in avail_portfolios:
                    default_p = avail_portfolios[0]
                df_history = get_all_snapshots_history(engine, portfolio_name=default_p)
        except Exception:
            df_history = pd.DataFrame()

    if df_history.empty:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;">
            <div style="color: #38bdf8; font-weight: 700; font-size: 15px; margin-bottom: 4px;">🗄️ Database Snapshot & Data Warehouse Lineage</div>
            <div style="color: #cbd5e1; font-size: 13px; line-height: 1.5;">
                Nessuno snapshot archiviato trovato su <b>{db_name}</b> (MySQL offline o primo avvio).<br>
                Puoi salvare un nuovo snapshot immutabile con data e ora corrente direttamente dalla <b>Control Room</b>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        try:
            st.page_link("0_Control_Room.py", label="💼 Vai alla Control Room per salvare uno snapshot", icon="📥")
        except Exception:
            pass
    else:
        df_history["calc_date"] = pd.to_datetime(df_history["calc_date"])
        df_history["display_label"] = df_history.apply(
            lambda r: f"📅 {r['calc_date'].strftime('%Y-%m-%d %H:%M')} | 🏷️ {r['run_name'] or 'Standard'} | 💰 € {r['total_value']:,.2f} | ID: {r['run_id']}",
            axis=1
        )

        st.markdown("### ⚖️ Confronto Diretto Affiancato tra 2 Snapshot")
        options_list = list(df_history["display_label"])
        idx_a = len(options_list) - 1
        idx_b = max(0, len(options_list) - 2)

        col_sel_a, col_sel_b = st.columns(2)
        with col_sel_a:
            label_a = st.selectbox("🅰️ Seleziona Snapshot A (Target):", options_list, index=idx_a)
            snap_a = df_history[df_history["display_label"] == label_a].iloc[0]
        with col_sel_b:
            label_b = st.selectbox("🅱️ Seleziona Snapshot B (Precedente):", options_list, index=idx_b)
            snap_b = df_history[df_history["display_label"] == label_b].iloc[0]

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        val_a = snap_a["total_value"] or 0
        val_b = snap_b["total_value"] or 0
        d_val = val_a - val_b
        d_val_pct = (d_val / val_b * 100) if val_b > 0 else 0

        pnl_a = snap_a["total_pnl"] or 0
        pnl_b = snap_b["total_pnl"] or 0
        d_pnl = pnl_a - pnl_b

        sh_a = snap_a["sharpe_ratio"] or 0
        sh_b = snap_b["sharpe_ratio"] or 0
        d_sh = sh_a - sh_b

        var_a = snap_a["var_95_pct"] or 0
        var_b = snap_b["var_95_pct"] or 0
        d_var = var_a - var_b

        st.markdown(f"""
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:11px; color:#8b949e; margin-bottom:4px;">VARIAZIONE VALORE PORTAFOGLIO</div>
                <div style="font-size:20px; font-weight:700; color:#ffffff;">€ {d_val:+,.2f}</div>
                <div style="font-size:12px;" class="{'metric-delta-pos' if d_val >= 0 else 'metric-delta-neg'}">{d_val_pct:+.2f}%</div>
            </div>
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:11px; color:#8b949e; margin-bottom:4px;">VARIAZIONE PnL CUMULATO</div>
                <div style="font-size:20px; font-weight:700; color:#ffffff;">€ {d_pnl:+,.2f}</div>
                <div style="font-size:12px; color:#8b949e;">Diff A vs B</div>
            </div>
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:11px; color:#8b949e; margin-bottom:4px;">VARIAZIONE SHARPE RATIO</div>
                <div style="font-size:20px; font-weight:700; color:#ff9900;">{d_sh:+.2f}</div>
                <div style="font-size:12px;" class="{'metric-delta-pos' if d_sh >= 0 else 'metric-delta-neg'}">{"Migliorato" if d_sh >= 0 else "Peggiorato"}</div>
            </div>
            <div class="glass-card" style="text-align:center;">
                <div style="font-size:11px; color:#8b949e; margin-bottom:4px;">VARIAZIONE VaR 95%</div>
                <div style="font-size:20px; font-weight:700; color:#f85149;">{d_var:+.2f}%</div>
                <div style="font-size:12px;" class="{'metric-delta-neg' if d_var > 0 else 'metric-delta-pos'}">{"Rischio +" if d_var > 0 else "Rischio -"}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        df_pos_a = get_snapshot_positions_by_id(engine, snap_a["snapshot_id"])
        df_pos_b = get_snapshot_positions_by_id(engine, snap_b["snapshot_id"])

        if not df_pos_a.empty or not df_pos_b.empty:
            merged = pd.merge(
                df_pos_a[["ticker", "qty_net", "avg_cost", "last_price", "current_value", "weight_pct"]],
                df_pos_b[["ticker", "qty_net", "avg_cost", "last_price", "current_value", "weight_pct"]],
                on="ticker", how="outer", suffixes=("_A", "_B")
            ).fillna(0)
            
            merged["delta_qty"] = merged["qty_net_A"] - merged["qty_net_B"]
            merged["delta_val"] = merged["current_value_A"] - merged["current_value_B"]
            merged["delta_weight"] = merged["weight_pct_A"] - merged["weight_pct_B"]
            
            merged_display = merged[[
                "ticker", "qty_net_A", "qty_net_B", "delta_qty",
                "current_value_A", "current_value_B", "delta_val",
                "weight_pct_A", "weight_pct_B", "delta_weight"
            ]].copy()
            
            merged_display.columns = [
                "Ticker", "Quantità A", "Quantità B", "Δ Qty",
                "Valore A (€)", "Valore B (€)", "Δ Valore (€)",
                "Peso A (%)", "Peso B (%)", "Δ Peso (%)"
            ]
            
            st.dataframe(
                merged_display.style.format({
                    "Quantità A": "{:,.2f}", "Quantità B": "{:,.2f}", "Δ Qty": "{:+,.2f}",
                    "Valore A (€)": "€ {:,.2f}", "Valore B (€)": "€ {:,.2f}", "Δ Valore (€)": "€ {:+,.2f}",
                    "Peso A (%)": "{:.2f}%", "Peso B (%)": "{:.2f}%", "Δ Peso (%)": "{:+.2f}%"
                }),
                use_container_width=True, hide_index=True
            )

        # Registro Completo DuckDB
        st.markdown("---")
        st.markdown("##### 🗃️ Registro Completo Snapshot Storici")
        df_history_disp = df_history[[
            "calc_date", "run_id", "run_name", "total_value", "total_pnl", 
            "cagr_pct", "sharpe_ratio", "max_drawdown_pct", "var_95_pct", "hhi_index"
        ]].sort_values(by="calc_date", ascending=False).rename(columns={
            "calc_date": "Data e Ora Snapshot",
            "run_id": "Run ID",
            "run_name": "Nome Analisi",
            "total_value": "Valore Totale (€)",
            "total_pnl": "PnL Cumulato (€)",
            "cagr_pct": "CAGR %",
            "sharpe_ratio": "Sharpe Ratio",
            "max_drawdown_pct": "Max Drawdown %",
            "var_95_pct": "VaR 95% %",
            "hhi_index": "Indice HHI"
        })
        st.dataframe(
            df_history_disp.style.format({
                "Valore Totale (€)": "€ {:,.2f}", "PnL Cumulato (€)": "€ {:+,.2f}",
                "CAGR %": "{:+.2f}%", "Sharpe Ratio": "{:.2f}", "Max Drawdown %": "{:.2f}%",
                "VaR 95% %": "{:.2f}%", "Indice HHI": "{:.4f}"
            }),
            use_container_width=True, hide_index=True
        )

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
