import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as bg
from plotly.subplots import make_subplots
import os

from core.sidebar import render_sidebar
from core.fetcher import get_engine
from core.db_exporter import get_all_snapshots_history, get_snapshot_positions_by_id
from sqlalchemy import text as sqlt

st.set_page_config(
    page_title="ARGUS - Analisi Temporale & Storico",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    
    .glass-card {
        background: rgba(22, 27, 34, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(63, 185, 80, 0.4);
    }

    .metric-delta-pos {
        color: #3fb950;
        font-weight: 700;
    }
    
    .metric-delta-neg {
        color: #f85149;
        font-weight: 700;
    }

    .argus-command-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(63, 185, 80, 0.1);
        border: 1px solid rgba(63, 185, 80, 0.3);
        color: #3fb950;
    }
</style>
""", unsafe_allow_html=True)

render_sidebar()

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
    st.warning("☁️ **Modalità Offline Attiva.** L'Analisi Temporale richiede l'accesso a MySQL per consultare lo storico degli snapshot. Disabilita la modalità offline nella barra laterale per accedere ai dati salvati.")
    st.stop()

# ── Database Connection ──────────────────────────────────────
try:
    engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
except Exception as e:
    st.error(f"❌ Impossibile connettersi al Database MySQL '{db_name}': {e}")
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
    st.info(f"ℹ️ Nessun portafoglio con storico salvato trovato nel Database **`{db_name}`**.\n\nPer iniziare, vai nella **Control Room**, seleziona o carica un portafoglio ed esegui l'analisi quantitativa!")
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

# ── Main Tabs ────────────────────────────────────────────────
tab_ts, tab_cmp, tab_rec = st.tabs([
    "📈 Serie Storiche Temporali",
    "⚖️ Confronto Affiancato (Side-by-Side)",
    "🗃️ Registro Completo Snapshot Storici"
])

# ── TAB 1: SERIE STORICHE TEMPORALI ─────────────────────────
with tab_ts:
    st.markdown(f"### 📈 Performance e Rischio nel Tempo — `{selected_portfolio}`")
    st.caption(f"Trovati **{len(df_history)}** snapshot storici registrati per questo portafoglio su `{db_name}`.")
    
    # Macro metrics summary row
    latest_snap = df_history.iloc[-1]
    first_snap = df_history.iloc[0]
    
    val_diff = (latest_snap["total_value"] or 0) - (first_snap["total_value"] or 0)
    val_diff_pct = (val_diff / first_snap["total_value"] * 100) if (first_snap["total_value"] and first_snap["total_value"] > 0) else 0
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Valore Attuale Snapshot", f"€ {latest_snap['total_value']:,.2f}", delta=f"{val_diff_pct:+.2f}% da inizio storico")
    with c2:
        cagr_val = latest_snap.get("cagr_pct")
        st.metric("CAGR Medio Registrato", f"{cagr_val:+.2f}%" if cagr_val is not None else "N/A")
    with c3:
        sharpe_val = latest_snap.get("sharpe_ratio")
        st.metric("Sharpe Ratio Attuale", f"{sharpe_val:.2f}" if sharpe_val is not None else "N/A")
    with c4:
        var_val = latest_snap.get("var_95_pct")
        st.metric("VaR 95% Giornaliero", f"€ {var_val:,.2f}" if var_val is not None else "N/A")

    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)

    # 1. Chart: Total Value & PnL
    fig_val = make_subplots(specs=[[{"secondary_y": True}]])
    fig_val.add_trace(
        bg.Scatter(
            x=df_history["calc_date"], y=df_history["total_value"],
            mode="lines+markers", name="Valore Totale Portafoglio (€)",
            line=dict(color="#3fb950", width=3),
            marker=dict(size=8, color="#3fb950"),
            hovertemplate="<b>Valore Totale Portafoglio</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: € %{y:,.2f}<extra></extra>"
        ),
        secondary_y=False
    )
    if "total_pnl" in df_history.columns and df_history["total_pnl"].notna().any():
        fig_val.add_trace(
            bg.Scatter(
                x=df_history["calc_date"], y=df_history["total_pnl"],
                mode="lines+markers", name="PnL Cumulato (€)",
                line=dict(color="#00f3ff", width=2, dash="dash"),
                marker=dict(size=6, color="#00f3ff"),
                hovertemplate="<b>PnL Cumulato</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>PnL: € %{y:,.2f}<extra></extra>"
            ),
            secondary_y=True
        )
    fig_val.update_layout(
        title="<b>Evoluzione Patrimonio & PnL Cumulato nel Tempo (€)</b>",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
    )
    fig_val.update_xaxes(title="Data Snapshot")
    fig_val.update_yaxes(title_text="Valore Portafoglio (€)", secondary_y=False)
    fig_val.update_yaxes(title_text="PnL Cumulato (€)", secondary_y=True)
    st.plotly_chart(fig_val, use_container_width=True)

    # 2. Charts: Sharpe & Sortino + VaR 95% & Max Drawdown
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        df_sh_chart = df_history.rename(columns={
            "sharpe_ratio": "Sharpe Ratio",
            "sortino_ratio": "Sortino Ratio"
        })
        fig_sh = px.line(
            df_sh_chart, x="calc_date", y=["Sharpe Ratio", "Sortino Ratio"],
            labels={"value": "Indice", "calc_date": "Data Snapshot", "variable": "Indice di Rischio"},
            title="<b>Andamento Efficienza di Rischio (Sharpe & Sortino)</b>",
            markers=True,
            template="plotly_dark"
        )
        fig_sh.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: %{y:.2f}<extra></extra>"
        )
        fig_sh.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
        )
        st.plotly_chart(fig_sh, use_container_width=True)
        
    with col_c2:
        df_var_chart = df_history.rename(columns={
            "var_95_pct": "VaR 95% (%)",
            "max_drawdown_pct": "Max Drawdown (%)"
        })
        fig_var = px.line(
            df_var_chart, x="calc_date", y=["VaR 95% (%)", "Max Drawdown (%)"],
            labels={"value": "Percentuale %", "calc_date": "Data Snapshot", "variable": "Metrica di Rischio"},
            title="<b>Evoluzione dei Rischi Estremi (VaR 95% & Max Drawdown)</b>",
            markers=True,
            template="plotly_dark"
        )
        fig_var.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>Data Snapshot: %{x|%Y-%m-%d %H:%M}<br>Valore: %{y:.2f}%<extra></extra>"
        )
        fig_var.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
        )
        st.plotly_chart(fig_var, use_container_width=True)

# ── TAB 2: CONFRONTO AFFIANCATO (SIDE-BY-SIDE) ───────────────
with tab_cmp:
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
                title="Ripartizione per Asset Class A", hole=0.4
            )
            fig_pie_a.update_traces(
                hovertemplate="<b>Asset Class: %{label}</b><br>Valore: € %{value:,.2f} (%{percent})<extra></extra>"
            )
            fig_pie_a.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(fig_pie_a, use_container_width=True)
            
    with col_chart_b:
        st.markdown(f"#### 🅱️ Allocation Snapshot B (`{snap_b['calc_date'].strftime('%Y-%m-%d %H:%M')}`)")
        if not df_pos_b.empty:
            fig_pie_b = px.pie(
                df_pos_b, names="asset_class", values="current_value",
                title="Ripartizione per Asset Class B", hole=0.4
            )
            fig_pie_b.update_traces(
                hovertemplate="<b>Asset Class: %{label}</b><br>Valore: € %{value:,.2f} (%{percent})<extra></extra>"
            )
            fig_pie_b.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(fig_pie_b, use_container_width=True)

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
with tab_rec:
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
