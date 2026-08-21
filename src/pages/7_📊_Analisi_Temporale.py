import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as bg
from plotly.subplots import make_subplots
import os

import importlib
import core.ui_utils
import core.duckdb_engine
importlib.reload(core.ui_utils)
importlib.reload(core.duckdb_engine)
from core.sidebar import render_sidebar
from core.fetcher import get_engine
from core.db_exporter import get_all_snapshots_history, get_snapshot_positions_by_id
from core.ui_utils import apply_plotly_theme, inject_custom_css, render_command_bar, render_segmented_tabs, metric_card
from sqlalchemy import text as sqlt

st.set_page_config(
    page_title="ARGUS - Analisi Temporale & Storico",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()
render_sidebar()
render_command_bar()

# ── System Banner ───────────────────────────────────────────
st.title("📊 Analisi Temporale & Confronto Storico")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Intelligence multi-temporale per tracciare l'evoluzione del patrimonio, dei pesi e dei singoli titoli nel tempo.")
else:
    st.caption("Intelligence multi-temporale per tracciare l'evoluzione del patrimonio, dei pesi e dei singoli titoli nel tempo.")
st.divider()

db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_name = st.session_state.get("db_name", "investment_risk_bi")
offline_mode = st.session_state.get("offline_mode", False)

if offline_mode:
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;">
        <div style="color: #38bdf8; font-weight: 700; font-size: 14px; margin-bottom: 2px;">☁️ Modalità Offline Attiva</div>
        <div style="color: #cbd5e1; font-size: 12.5px; line-height: 1.45;">
            L'Analisi Temporale storicizzata consulta le serie temporali registrate nel database MySQL. Disabilita la modalità offline o salva un nuovo snapshot dalla Control Room.
        </div>
    </div>
    """, unsafe_allow_html=True)
    try:
        st.page_link("0_Control_Room.py", label="📥 Vai alla Control Room", icon="💼")
    except Exception:
        pass
    st.stop()

# ── Database Connection ──────────────────────────────────────
try:
    engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
except Exception as e:
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;">
        <div style="color: #f87171; font-weight: 700; font-size: 14px; margin-bottom: 2px;">❌ Connessione Database MySQL non disponibile</div>
        <div style="color: #cbd5e1; font-size: 12.5px; line-height: 1.45;">
            Impossibile connettersi al Database MySQL <b>{db_name}</b>: {e}.<br>Verifica che il servizio MySQL sia attivo o procedi in modalità Sandbox nelle altre pagine.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Fetch Portfolios List for Selection ─────────────────────
try:
    with engine.connect() as conn:
        port_rows = conn.execute(sqlt("""
            SELECT DISTINCT p.name 
            FROM portfolios p
            JOIN portfolio_snapshots s ON p.portfolio_id = s.portfolio_id
            ORDER BY p.name ASC
        """)).fetchall()
        avail_portfolios = [r[0] for r in port_rows]
except Exception as e:
    avail_portfolios = []

if not avail_portfolios:
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 14px 18px; margin-bottom: 12px;">
        <div style="color: #38bdf8; font-weight: 700; font-size: 14px; margin-bottom: 2px;">ℹ️ Nessun Snapshot Storico Trovato</div>
        <div style="color: #cbd5e1; font-size: 12.5px; line-height: 1.45;">
            Non sono ancora presenti snapshot storici registrati nel Database <b>{db_name}</b>.<br>
            Per iniziare a tracciare l'evoluzione del patrimonio nel tempo, carica o seleziona un portafoglio nella <b>Control Room</b> e salva il tuo primo snapshot.
        </div>
    </div>
    """, unsafe_allow_html=True)
    try:
        st.page_link("0_Control_Room.py", label="📥 Vai alla Control Room", icon="💼")
    except Exception:
        pass
    st.stop()

# ── Filter Header Controls ──────────────────────────────────
col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

with col_f1:
    default_port = st.session_state.get("portfolio_name", avail_portfolios[0])
    if default_port not in avail_portfolios:
        default_port = avail_portfolios[0]
        
    selected_portfolio = st.selectbox(
        "💼 Seleziona Portafoglio Target:",
        avail_portfolios,
        index=avail_portfolios.index(default_port),
        help="Scegli il nome del portafoglio di cui analizzare lo storico temporale."
    )

# Fetch runs for the selected portfolio
try:
    with engine.connect() as conn:
        run_rows = conn.execute(sqlt("""
            SELECT DISTINCT s.run_name 
            FROM portfolio_snapshots s
            JOIN portfolios p ON s.portfolio_id = p.portfolio_id
            WHERE p.name = :pname AND s.run_name IS NOT NULL AND s.run_name != ''
            ORDER BY s.run_name ASC
        """), {"pname": selected_portfolio}).fetchall()
        avail_runs = ["Tutti i nomi run"] + [r[0] for r in run_rows]
except Exception:
    avail_runs = ["Tutti i nomi run"]

with col_f2:
    selected_run_filter = st.selectbox(
        "🏷️ Filtra per Nome Analisi / Run Name:",
        avail_runs,
        index=0,
        help="Filtra solo le analisi identificate da un etichetta specifica."
    )

with col_f3:
    st.markdown(f"""
    <div style="background: rgba(63, 185, 80, 0.08); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 8px; padding: 10px; margin-top: 15px; text-align: center;">
        <span style="font-size: 11px; color: #8b949e;">DATABASE TARGET</span><br>
        <span style="font-size: 15px; font-weight: 700; color: #3fb950;">🗄️ {db_name}</span>
    </div>
    """, unsafe_allow_html=True)

# ── Query Multi-Snapshot DataFrame ───────────────────────────
run_name_param = None if selected_run_filter == "Tutti i nomi run" else selected_run_filter
df_history = get_all_snapshots_history(engine, portfolio_name=selected_portfolio, run_name=run_name_param)

if df_history.empty:
    st.warning(f"Nessuno snapshot trovato per il portafoglio '{selected_portfolio}' con i filtri selezionati nel database '{db_name}'.")
    st.stop()

# Ensure calc_date is datetime
df_history["calc_date"] = pd.to_datetime(df_history["calc_date"])

# Create friendly labels for dropdown selection
df_history["display_label"] = df_history.apply(
    lambda r: f"📅 {r['calc_date'].strftime('%Y-%m-%d %H:%M')} | 🏷️ {r['run_name'] or 'Standard'} | 💰 € {r['total_value']:,.2f} | ID: {r['run_id']}",
    axis=1
)

st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)

# ── Main Tabs con Lazy Loading ───────────────────────────────
active_time_tab = render_segmented_tabs([
    "📈 Serie Storiche Temporali",
    "⚖️ Confronto Affiancato (Side-by-Side)",
    "🗃️ Registro Completo Snapshot Storici"
], key="time_active_tab")

# ── TAB 1: SERIE STORICHE TEMPORALI ─────────────────────────
if active_time_tab == "📈 Serie Storiche Temporali":
    st.markdown(f"### 📈 Performance e Rischio nel Tempo | `{selected_portfolio}`")
    st.caption(f"Trovati **{len(df_history)}** snapshot storici registrati per questo portafoglio su `{db_name}`.")
    
    # Macro metrics summary row
    latest_snap = df_history.iloc[-1]
    first_snap = df_history.iloc[0]
    
    val_diff = (latest_snap["total_value"] or 0) - (first_snap["total_value"] or 0)
    val_diff_pct = (val_diff / first_snap["total_value"] * 100) if (first_snap["total_value"] and first_snap["total_value"] > 0) else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Valore Snapshot", f"€ {latest_snap['total_value']:,.2f}", f"{val_diff_pct:+.2f}% da inizio", positive=val_diff_pct >= 0)
    with c2:
        cagr_val = latest_snap.get("cagr_pct")
        cagr_valid = cagr_val is not None and pd.notna(cagr_val)
        metric_card("CAGR Medio", f"{cagr_val:+.2f}%" if cagr_valid else "N/A", "Tasso Annuo Registrato", positive=float(cagr_val or 0) >= 0 if cagr_valid else True)
    with c3:
        sharpe_val = latest_snap.get("sharpe_ratio")
        sh_valid = sharpe_val is not None and pd.notna(sharpe_val)
        metric_card("Sharpe Ratio", f"{sharpe_val:.2f}" if sh_valid else "N/A", "Efficienza del Rischio", positive=float(sharpe_val or 0) >= 1.0 if sh_valid else True)
    with c4:
        var_val = latest_snap.get("var_95_pct")
        var_valid = var_val is not None and pd.notna(var_val)
        metric_card("VaR 95% Giornaliero", f"{var_val:.2f}%" if var_valid else "N/A", "Massima Perdita 95%", positive=False)

    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)

    # 1. Chart: Total Value & PnL
    st.markdown("##### 📈 Evoluzione Patrimonio & PnL Cumulato nel Tempo (€)")
    fig_val = make_subplots(specs=[[{"secondary_y": True}]])
    fig_val.add_trace(
        bg.Scatter(
            x=df_history["calc_date"], y=df_history["total_value"],
            mode="lines+markers", name="Valore Totale Portafoglio (€)",
            line=dict(color="#00e676", width=2.5),
            marker=dict(size=8, color="#00e676"),
            hovertemplate="<b>Valore Totale Portafoglio</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: € %{y:,.2f}<extra></extra>"
        ),
        secondary_y=False
    )
    if "total_pnl" in df_history.columns and df_history["total_pnl"].notna().any():
        fig_val.add_trace(
            bg.Scatter(
                x=df_history["calc_date"], y=df_history["total_pnl"],
                mode="lines+markers", name="PnL Cumulato (€)",
                line=dict(color="#58a6ff", width=2, dash="dash"),
                marker=dict(size=6, color="#58a6ff"),
                hovertemplate="<b>PnL Cumulato</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>PnL: € %{y:,.2f}<extra></extra>"
            ),
            secondary_y=True
        )
    fig_val.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color="#ffffff"),
            bgcolor="rgba(22, 27, 34, 0.6)",
            bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1,
            title=None
        )
    )
    fig_val.update_xaxes(title="Data Snapshot", gridcolor="rgba(255,255,255,0.06)")
    fig_val.update_yaxes(title_text="Valore Portafoglio (€)", secondary_y=False, gridcolor="rgba(255,255,255,0.06)")
    fig_val.update_yaxes(title_text="PnL Cumulato (€)", secondary_y=True, gridcolor="rgba(255,255,255,0.06)")
    apply_plotly_theme(fig_val)
    st.plotly_chart(fig_val, use_container_width=True, key="temporal_val_trend_chart", config={"displayModeBar": "hover", "displaylogo": False})

    # 2. Charts: Sharpe & Sortino + VaR 95% & Max Drawdown
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.markdown("##### ⚡ Efficienza di Rischio (Sharpe & Sortino)")
        df_sh_chart = df_history.rename(columns={
            "sharpe_ratio": "Sharpe Ratio",
            "sortino_ratio": "Sortino Ratio"
        })
        fig_sh = px.line(
            df_sh_chart, x="calc_date", y=["Sharpe Ratio", "Sortino Ratio"],
            labels={"value": "Indice", "calc_date": "Data Snapshot", "variable": "Indice"},
            color_discrete_sequence=["#58a6ff", "#00e676"],
            markers=True,
            template="plotly_dark"
        )
        fig_sh.update_traces(
            line=dict(width=2.2),
            hovertemplate="<b>%{fullData.name}</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: %{y:.2f}<extra></extra>"
        )
        fig_sh.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340,
            margin=dict(l=20, r=20, t=35, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color="#ffffff"),
                bgcolor="rgba(22, 27, 34, 0.6)",
                bordercolor="rgba(255,255,255,0.08)",
                borderwidth=1,
                title=None
            ),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Indice"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Data Snapshot")
        )
        apply_plotly_theme(fig_sh)
        st.plotly_chart(fig_sh, use_container_width=True, key="temporal_sharpe_chart", config={"displayModeBar": "hover", "displaylogo": False})
        
    with col_c2:
        st.markdown("##### 🛡️ Rischi Estremi (VaR 95% & Max Drawdown)")
        df_var_chart = df_history.rename(columns={
            "var_95_pct": "VaR 95% (%)",
            "max_drawdown_pct": "Max Drawdown (%)"
        })
        fig_var = px.line(
            df_var_chart, x="calc_date", y=["VaR 95% (%)", "Max Drawdown (%)"],
            labels={"value": "Percentuale %", "calc_date": "Data Snapshot", "variable": "Metrica"},
            color_discrete_sequence=["#ff9900", "#f85149"],
            markers=True,
            template="plotly_dark"
        )
        fig_var.update_traces(
            line=dict(width=2.2),
            hovertemplate="<b>%{fullData.name}</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: %{y:.2f}%<extra></extra>"
        )
        fig_var.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340,
            margin=dict(l=20, r=20, t=35, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color="#ffffff"),
                bgcolor="rgba(22, 27, 34, 0.6)",
                bordercolor="rgba(255,255,255,0.08)",
                borderwidth=1,
                title=None
            ),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Percentuale (%)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", title="Data Snapshot")
        )
        apply_plotly_theme(fig_var)
        st.plotly_chart(fig_var, use_container_width=True, key="temporal_var_chart", config={"displayModeBar": "hover", "displaylogo": False})

# ── TAB 2: CONFRONTO AFFIANCATO (SIDE-BY-SIDE) ───────────────
elif active_time_tab == "⚖️ Confronto Affiancato (Side-by-Side)":
    st.markdown("### ⚖️ Confronto Diretto Affiancato tra 2 Snapshot")
    st.caption("Seleziona due momenti temporali per analizzare nel dettaglio l'evoluzione del patrimonio, dei pesi e dei singoli titoli.")

    options_list = list(df_history["display_label"])
    
    idx_a = len(options_list) - 1
    idx_b = max(0, len(options_list) - 2)

    col_sel_a, col_sel_b = st.columns(2)
    
    with col_sel_a:
        label_a = st.selectbox("🅰️ Seleziona Snapshot A (es. Recente / Target):", options_list, index=idx_a)
        snap_a = df_history[df_history["display_label"] == label_a].iloc[0]
        
    with col_sel_b:
        label_b = st.selectbox("🅱️ Seleziona Snapshot B (es. Precedente / Benchmark):", options_list, index=idx_b)
        snap_b = df_history[df_history["display_label"] == label_b].iloc[0]

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    # Delta Comparison Cards
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
            <div style="font-size:20px; font-weight:700; color:#f85149;">€ {d_var:+,.2f}</div>
            <div style="font-size:12px;" class="{'metric-delta-neg' if d_var > 0 else 'metric-delta-pos'}">{"Rischio +" if d_var > 0 else "Rischio -"}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_pos_a = get_snapshot_positions_by_id(engine, snap_a["snapshot_id"])
    df_pos_b = get_snapshot_positions_by_id(engine, snap_b["snapshot_id"])

    col_chart_a, col_chart_b = st.columns(2)
    
    with col_chart_a:
        st.markdown(f"#### 🅰️ Allocation Snapshot A (`{snap_a['calc_date'].strftime('%Y-%m-%d %H:%M')}`)")
        if not df_pos_a.empty:
            fig_pie_a = px.pie(
                df_pos_a, names="asset_class", values="current_value",
                hole=0.62,
                color_discrete_sequence=["#58a6ff", "#00e676", "#bc8cff", "#ff9900", "#f85149"]
            )
            fig_pie_a.update_traces(
                textposition='inside', textinfo='percent',
                insidetextorientation='horizontal',
                marker=dict(line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>Asset Class: %{label}</b><br>Valore: € %{value:,.2f} (%{percent})<extra></extra>"
            )
            fig_pie_a.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=310,
                legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(size=11, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=40)
            )
            apply_plotly_theme(fig_pie_a)
            st.plotly_chart(fig_pie_a, use_container_width=True, key="temporal_pie_chart_a", config={"displayModeBar": "hover", "displaylogo": False})
            
    with col_chart_b:
        st.markdown(f"#### 🅱️ Allocation Snapshot B (`{snap_b['calc_date'].strftime('%Y-%m-%d %H:%M')}`)")
        if not df_pos_b.empty:
            fig_pie_b = px.pie(
                df_pos_b, names="asset_class", values="current_value",
                hole=0.62,
                color_discrete_sequence=["#58a6ff", "#00e676", "#bc8cff", "#ff9900", "#f85149"]
            )
            fig_pie_b.update_traces(
                textposition='inside', textinfo='percent',
                insidetextorientation='horizontal',
                marker=dict(line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>Asset Class: %{label}</b><br>Valore: € %{value:,.2f} (%{percent})<extra></extra>"
            )
            fig_pie_b.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=310,
                legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5, font=dict(size=11, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=40)
            )
            apply_plotly_theme(fig_pie_b)
            st.plotly_chart(fig_pie_b, use_container_width=True, key="temporal_pie_chart_b", config={"displayModeBar": "hover", "displaylogo": False})

    st.markdown("#### 📋 Confronto Dettagliato Titolo per Titolo")
    
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
            use_container_width=True
        )

# ── TAB 3: REGISTRO COMPLETO SNAPSHOT ─────────────────────────
elif active_time_tab == "🗃️ Registro Completo Snapshot Storici":
    st.markdown("### 🗃️ Registro Completo degli Snapshot Storici")
    st.caption("Consultazione analitica di tutti i punti storici registrati nel Data Warehouse MySQL.")
    
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
            "Valore Totale (€)": "€ {:,.2f}",
            "PnL Cumulato (€)": "€ {:+,.2f}",
            "CAGR %": "{:+.2f}%",
            "Sharpe Ratio": "{:.2f}",
            "Max Drawdown %": "{:.2f}%",
            "VaR 95% %": "{:.2f}%",
            "Indice HHI": "{:.4f}"
        }),
        use_container_width=True, hide_index=True
    )

    # ⚡ DuckDB Analytics su Variazioni Step-by-Step & Medie Mobili
    st.markdown("---")
    with st.expander("⚡ Vista Analitica Aggregata DuckDB (Trend Vettorizzato & Medie Mobili)", expanded=False):
        from core.duckdb_engine import compute_duckdb_temporal_snapshot_analytics
        duck_snap = compute_duckdb_temporal_snapshot_analytics(df_history)
        if duck_snap.get("success") and not duck_snap["df"].empty:
            st.caption(f"🚀 Esecuzione C++ SIMD Vettorizzata in **{duck_snap['latency_ms']:.2f} ms**")
            st.dataframe(duck_snap["df"], use_container_width=True, hide_index=True)
        else:
            st.info("Dati insufficienti per l'analisi del trend temporale.")
