import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import importlib
import core.ui_utils
import core.risk_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
from core.ui_utils import inject_custom_css, section, metric_card, fmt_pct, fmt_eur, glossary_modal, render_executive_badges, render_command_bar, apply_plotly_theme, render_factor_radar_chart, render_info_modal, ensure_risk_bundle_loaded, render_sandbox_banner
from core.excel_generator import generate_excel_in_memory

st.set_page_config(page_title="Executive Cockpit | ARGUS", page_icon="📈", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

results, has_real = ensure_risk_bundle_loaded()
m   = results.get("metrics", {})
ret = m.get("returns", {})
mk  = m.get("market_risk", {})
sr_port = results.get("portfolio_return", pd.Series(dtype=float))
sr_bm   = results.get("benchmark_return", pd.Series(dtype=float))
pos = results.get("positions", pd.DataFrame())

render_command_bar()
render_sandbox_banner(page_key="p1")

st.title("📈 Dashboard Generale | Executive Cockpit")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Quadro sintetico ad alta densità su performance, allocazione, impronta di rischio e conformità regolamentare.")
elif results.get("is_sandbox"):
    st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")

render_executive_badges(m)

# Warning Popover if any ingestion warnings exist
has_warnings = bool(results.get("warnings"))
warn_list = results.get("warnings", [])
n_warn = len(warn_list)

if has_warnings:
    with st.popover(f"⚠️ {n_warn} Avvisi di Ingestione", use_container_width=False, help="Dettagli sui dati di mercato e tassi di cambio"):
        st.markdown(f"### ⚠️ Registro Avvisi e Tassi FX ({n_warn})")
        st.info("I seguenti avvisi minori sono stati rilevati durante il recupero dei dati di mercato:")
        for w in warn_list:
            st.warning(f"• {w}")

st.divider()

# ⚡ Sintesi Esecutiva Quantitativa (Executive Callout Box)
from core.risk_limits import check_risk_limits
limits_res = check_risk_limits(results)
comp_score = limits_res.get("compliance_pct", 100.0)
cagr_val = float(ret.get("cagr_pct", ret.get("portfolio_cagr_pct", 0.0)) or 0.0)
tot_ret_val = float(ret.get("total_return_pct", 0.0) or 0.0)
sharpe_val = float(ret.get("sharpe_ratio", mk.get("sharpe_ratio", 0.0)) or 0.0)
port_val = float(ret.get("portfolio_value", results.get("portfolio_value", 0.0)) or 0.0)
var_val = float(mk.get("var_95", 0.0) or 0.0)
if var_val < 0.20 and var_val > 0.0:
    var_val = var_val * 100.0

st.markdown(f"""
<div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 153, 0, 0.25); border-left: 4px solid #ff9900; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
    <div style="font-weight: 700; font-size: 15px; color: #ff9900; margin-bottom: 4px;">⚡ Sintesi Esecutiva Quantitativa | Status Portafoglio</div>
    <div style="font-size: 13.5px; color: #c9d1d9; line-height: 1.5;">
        Portafoglio attivo con controvalore totale di <b>€ {port_val:,.2f}</b>. 
        Conformità del <b>{comp_score:.1f}%</b> sui 6 limiti di rischio regolamentari. 
        Sharpe Ratio a <b>{sharpe_val:.2f}</b> con rendimento annuo (CAGR) del <b>{cagr_val:.2f}%</b> (totale cumulato: <b>{tot_ret_val:+.2f}%</b>) e VaR 95% giornaliero al <b>{var_val:.2f}%</b>.
    </div>
</div>
""", unsafe_allow_html=True)



st.markdown("#### 💼 Riepilogo Portafoglio")
col1, col2, col3 = st.columns(3)
with col1:
    port_value = ret.get("portfolio_value", 0.0)
    metric_card(
        "Valore Portafoglio",
        fmt_eur(port_value),
        delta=fmt_pct(ret.get("total_return_pct")),
        positive=(ret.get("total_return_pct", 0) >= 0),
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Il <b>Mark-to-Market (MtM)</b> corrente del portafoglio: controvalore monetario totale liquidabile istantaneamente delle posizioni aperte calcolato ai prezzi di chiusura o real-time più recenti.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
Si moltiplica la quantità netta di quote per ciascun asset per il prezzo di mercato corrente, convertito in Euro:
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Valore Totale</b> = &sum; (Quote Nette<sub>i</sub> &times; Prezzo<sub>i</sub> &times; Tasso FX<sub>i</sub>)
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Rappresenta la dimensione patrimoniale effettiva dell'investimento. Risponde alla domanda: 'Se dovessi liquidare l'intero portafoglio ai prezzi attuali, quale capitale netto otterrei?'.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS traccia tutti gli ordini storici dal database o CSV, calcola la posizione netta per ISIN/Ticker e scarica le quotazioni in tempo reale via cache persistente con conversione FX automatica.</div>

<div><b>🔍 Come leggerlo:</b> Indica il patrimonio netto investito totale. Confrontato con il costo storico d'acquisto (<i>Cost Basis</i>), evidenzia l'apprezzamento monetario complessivo.</div>
</div>"""
    )
with col2:
    metric_card(
        "PnL Totale",
        fmt_eur(ret.get("total_pnl")),
        delta=f"{ret.get('total_pnl_pct', 0)*100:+.2f}%",
        positive=(ret.get("total_pnl", 0) >= 0),
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Profit & Loss (Profitti e Perdite) Totale, in Euro e in percentuale sul capitale investito. Misura la ricchezza netta generata dal portafoglio dall'inizio dell'operatività.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
Somma algebrica di PnL latente, PnL realizzato e dividendi netti percepiti:
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>PnL Totale</b> = PnL Latente + PnL Realizzato + Dividendi Totali
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Quantifica il ritorno economico effettivo in Euro sul patrimonio investito, integrando sia le plusvalenze che i flussi di cassa cedolari.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS esegue un motore contabile a code FIFO che separa con precisione il costo medio ponderato dei lotti residui, le plusvalenze già liquidate e i dividendi storici accreditati.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>Valore Positivo (Verde):</b> Il portafoglio è in guadagno rispetto al capitale complessivamente impiegato.<br>
• <b>Valore Negativo (Rosso):</b> Il portafoglio registra una perdita netta complessiva.
</div>
</div>"""
    )
with col3:
    metric_card(
        "CAGR",
        fmt_pct(ret.get("cagr_pct")),
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> <b>Compound Annual Growth Rate</b> (Tasso Annuo di Crescita Composto). È il rendimento geometrico annualizzato costante che avrebbe prodotto il passaggio dal capitale iniziale a quello finale.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>CAGR</b> = (1 + R<sub>totale</sub>)<sup>(1 / N<sub>anni</sub>)</sup> &minus; 1
</div>
dove <i>R<sub>totale</sub></i> è il rendimento complessivo e <i>N<sub>anni</sub></i> la durata in anni (frazionaria su 252 giorni/anno).
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Neutralizza le fluttuazioni intermedie e l'effetto volatilità, offrendo un parametro standardizzato annuo per confrontare la performance reale con inflazione e indici di mercato.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> Calcolato dalla prima data di transazione fino all'ultima disponibile, tenendo conto del reinvestimento dei guadagni e dei flussi temporali.</div>

<div><b>🔍 Come leggerlo:</b> Rappresenta il 'tasso d'interesse annuo medio equivalente'. Un CAGR dell'8.5% indica che il portafoglio è cresciuto mediamente dell'8.5% all'anno.</div>
</div>"""
    )

st.markdown("#### ⚡ Metriche di Rischio e Rendimento")
col4, col5, col6 = st.columns(3)
with col4:
    metric_card(
        "Sharpe Ratio (Ex-Post)",
        f"{ret.get('sharpe_ratio', 0) if ret.get('sharpe_ratio') else 0:.2f}",
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Rappresenta lo <b>Sharpe Ratio Storico Realizzato (Ex-Post)</b>. Misura l'extra-rendimento effettivo conseguito dal portafoglio per unità di volatilità durante la sua storia reale, tenendo conto delle date di acquisto, delle vendite e dei flussi di cassa (metodo FIFO).</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Sharpe Ratio<sub>Ex-Post</sub></b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #ffb74d; padding-bottom:1px;">R<sub>p</sub> &minus; R<sub>f</sub></span><span style="display:block; padding-top:1px;">&sigma;<sub>p</sub></span></span> &times; &radic;252
</div>
dove <i>R<sub>p</sub></i> è il rendimento medio giornaliero dei flussi reali, <i>R<sub>f</sub></i> il tasso privo di rischio giornaliero (3.0% annuo) e <i>&sigma;<sub>p</sub></i> la deviazione standard giornaliera.
</div>

<div style="margin-bottom: 8px;"><b>🎯 Differenza con Markowitz (Ex-Ante):</b>
Mentre lo <b>Sharpe Ex-Post (0.51)</b> misura la storia reale con i pesi variabili nel tempo, lo <b>Sharpe Markowitz (0.77)</b> nella scheda Modelli Quantitativi misura l'efficienza teorica dell'allocazione attuale statica (<i>w<sup>T</sup>&mu; / &sigma;</i>).
</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>< 1.0:</b> Efficienza modesta o rendimento insufficiente rispetto al rischio.<br>
• <b>1.0 – 1.99:</b> Ottimo profilo di gestione (standard fondi attivi di qualità).<br>
• <b>&ge; 2.0:</b> Profilo d'eccellenza e rendimento eccezionale corretto per il rischio.
</div>
</div>"""
    )
with col5:
    metric_card(
        "Max Drawdown",
        fmt_pct(mk.get("max_drawdown_pct")),
        positive=False,
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Quantifica la peggior flessione percentuale registrata dal portafoglio tra un massimo storico relativo (<i>Peak / High-Water Mark</i>) e il minimo successivo (<i>Trough</i>), prima di un nuovo picco.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Drawdown<sub>t</sub></b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #ffb74d; padding-bottom:1px;">Valore<sub>t</sub> &minus; Max(Valore)</span><span style="display:block; padding-top:1px;">Max(Valore)</span></span>
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> È la misura principe del <b>rischio di capitale e di coda</b> (<i>Tail Risk</i>). Risponde alla domanda: 'Se avessi investito nel momento peggiore, quanto capitale avrei visto evaporare prima del recupero?'.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS estrae i massimi storici progressivi (<i>High-Water Mark</i>) e misura la flessione percentuale massima registrata su tutto l'orizzonte.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>0% a -10%:</b> Profilo a basso rischio / difensivo.<br>
• <b>-10% a -25%:</b> Profilo bilanciato / azionario moderato.<br>
• <b>< -30%:</b> Profilo ad elevata volatilità o concentrato in asset rischiosi.
</div>
</div>"""
    )
with col6:
    var_95_val = mk.get("var_95")
    var_95_display = fmt_pct(-abs(var_95_val)) if var_95_val is not None else "N/A"
    metric_card(
        "VaR (95%) Storico",
        var_95_display,
        positive=False,
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Il <b>Value at Risk (VaR)</b> al 95% su orizzonte di 1 giorno è una stima quantitativa della perdita massima attesa in una singola seduta ordinaria con confidenza del 95%.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>VaR<sub>95%</sub></b> = 5&deg; Percentile (Rendimenti Storici Giornalieri)
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Dimensionare il rischio quotidiano di perdita. Significa che in <b>19 giorni su 20</b> la perdita non supererà tale soglia.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> Estraendo il 5° percentile della distribuzione dei rendimenti empirici storici.</div>

<div><b>🔍 Come leggerlo:</b> Un VaR del -1.93% indica che solo nel 5% dei casi storici si è registrata una perdita giornaliera peggiore dell'1.93%.</div>
</div>"""
    )

st.divider()

# ── RENDIMENTO CUMULATO VS BENCHMARK (100% FULL-WIDTH CHART) ───
from core.ui_utils import load_benchmark_returns
df_prices_ref = results.get("df_prices", pd.DataFrame())

# Header Ultra-Spazioso e Istituzionale (2-Row Layout)
st.markdown("### 📈 Rendimento cumulato vs benchmark")

c_bm, c_sel = st.columns([3.2, 1.0])

primary_bm = mk.get('benchmark_ticker', 'SPY')
bm_options = ["SPY (S&P 500)", "QQQ (Nasdaq 100)", "ACWI (MSCI World)", "AGG (US Bonds)", "GLD (Gold)", "BTC (Bitcoin)"]
def_idx = 0
for idx, opt in enumerate(bm_options):
    if primary_bm in opt:
        def_idx = idx
        break

with c_bm:
    selected_bms = st.multiselect(
        "Benchmark Attivi",
        options=bm_options,
        default=[bm_options[def_idx]],
        key="multi_bm_selector_p1",
        placeholder="Aggiungi Benchmark...",
        label_visibility="collapsed"
    )
    if not selected_bms:
        selected_bms = [bm_options[def_idx]]

with c_sel:
    horizon_options = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y", "20Y", "TUTTO"]
    selected_horizon = st.selectbox(
        "Orizzonte Temporale",
        options=horizon_options,
        index=9,
        key="horizon_p1_selectbox",
        label_visibility="collapsed"
    )

# Map orizzonti temporali in giorni lavorativi
horizon_days_map = {
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
    "3Y": 756,
    "5Y": 1260,
    "10Y": 2520,
    "20Y": 5040,
}

# Slicing del portafoglio in base all'orizzonte
if selected_horizon in horizon_days_map:
    n_days = horizon_days_map[selected_horizon]
    sr_p_sub = sr_port.tail(n_days)
elif selected_horizon == "YTD":
    if not sr_port.empty:
        max_yr = sr_port.index.max().year
        ytd_mask = sr_port.index.year == max_yr
        sr_p_sub = sr_port[ytd_mask] if ytd_mask.any() else sr_port.copy()
    else:
        sr_p_sub = sr_port.copy()
else:
    sr_p_sub = sr_port.copy()

# Ricalcolo rendimento cumulato Portafoglio (base 0%)
cum_port = ((1 + sr_p_sub).cumprod() - 1) * 100
date_x = pd.to_datetime(cum_port.index)

fig = go.Figure()

# Palette colori istituzionale per i benchmark
bm_colors = {
    "SPY": "#58a6ff",       # Blu Chiaro
    "QQQ": "#bc8cff",       # Viola Neon
    "ACWI": "#3fb950",      # Verde Smeraldo
    "AGG": "#8fa0ba",       # Grigio Ardesia
    "GLD": "#d29922",       # Oro
    "BTC": "#f0883e"        # Arancio Cripto
}

# Plot dei Benchmark selezionati dall'utente
for bm_str in selected_bms:
    bm_code = bm_str.split(" ")[0]
    sr_bm_raw = load_benchmark_returns(bm_code, df_prices_ref, sr_port.index)
    sr_bm_sub = sr_bm_raw.reindex(sr_p_sub.index).fillna(0.0)
    cum_bm_i = ((1 + sr_bm_sub).cumprod() - 1) * 100
    spread_i = cum_port - cum_bm_i

    b_color = bm_colors.get(bm_code, "#8fa0ba")

    customdata_bm = np.column_stack([
        [f"{v:+.2f}%" for v in cum_port.values],
        [f"{v:+.2f}%" for v in spread_i.values],
        [f"{v:+.2f}%" for v in cum_bm_i.values]
    ])

    fig.add_trace(go.Scatter(
        x=date_x, y=cum_bm_i.values,
        name=f"Benchmark ({bm_str})",
        line=dict(color=b_color, width=1.8, dash="dash"),
        customdata=customdata_bm,
        hovertemplate=f"<b>Data: %{{x|%d %b %Y}}</b><br>📊 Benchmark ({bm_code}): %{{customdata[2]}}<br>📈 Portafoglio: %{{customdata[0]}}<br>⚡ Outperformance vs {bm_code} (Δ): %{{customdata[1]}}<extra></extra>"
    ))

# Trace Portafoglio ARGUS (linea principale con riempimento sfumato)
primary_bm_code = selected_bms[0].split(" ")[0]
sr_bm_prim = load_benchmark_returns(primary_bm_code, df_prices_ref, sr_port.index)
sr_bm_prim_sub = sr_bm_prim.reindex(sr_p_sub.index).fillna(0.0)
cum_bm_prim = ((1 + sr_bm_prim_sub).cumprod() - 1) * 100
spread_prim = cum_port - cum_bm_prim

customdata_port = np.column_stack([
    [f"{v:+.2f}%" for v in cum_bm_prim.values],
    [f"{v:+.2f}%" for v in spread_prim.values],
    [f"{v:+.2f}%" for v in cum_port.values]
])

fig.add_trace(go.Scatter(
    x=date_x, y=cum_port.values,
    name="Portafoglio ARGUS",
    fill="tozeroy",
    fillcolor="rgba(255, 153, 0, 0.08)",
    line=dict(color="#ff9900", width=2.8),
    customdata=customdata_port,
    hovertemplate=f"<b>Data: %{{x|%d %b %Y}}</b><br>📈 Portafoglio: %{{customdata[2]}}<br>📊 Benchmark ({primary_bm_code}): %{{customdata[0]}}<br>⚡ Outperformance vs {primary_bm_code} (Δ): %{{customdata[1]}}<extra></extra>"
))

# Indicatore del Picco Massimo (High-Water Mark)
if not cum_port.empty:
    max_idx = cum_port.idxmax()
    max_val = cum_port.max()
    fig.add_annotation(
        x=pd.to_datetime(max_idx), y=max_val,
        text=f"🏆 Max: {max_val:+.1f}%",
        showarrow=True, arrowhead=2, arrowcolor="#ff9900",
        ax=0, ay=-30,
        font=dict(size=11, color="#ff9900"),
        bgcolor="rgba(22, 27, 34, 0.85)", bordercolor="#ff9900", borderwidth=1
    )

fig.update_layout(
    xaxis_title=None,
    height=480,
    legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
    yaxis=dict(
        type="linear",
        title="Rendimento Cumulato %",
        gridcolor="rgba(255,255,255,0.06)"
    ),
    xaxis=dict(
        type="date",
        range=[date_x.min(), date_x.max()] if len(date_x) > 0 else None,
        gridcolor="rgba(255,255,255,0.06)"
    )
)
apply_plotly_theme(fig)
st.plotly_chart(fig, use_container_width=True)

# ── SCORECARD COMPARATIVA MULTI-BENCHMARK (FEATURE 5) ─────────────
if selected_bms:
    st.markdown("#### 🏆 Scorecard Comparativa Multi-Benchmark")
    scorecard_rows = []
    
    # Riga 1: Portafoglio
    p_tot_ret = cum_port.iloc[-1] if not cum_port.empty else 0.0
    p_n_yrs = max(0.1, len(sr_p_sub) / 252.0)
    p_cagr = ((1 + p_tot_ret / 100.0) ** (1.0 / p_n_yrs) - 1.0) * 100.0 if p_tot_ret > -99.0 else -99.0
    p_vol = float(sr_p_sub.std() * np.sqrt(252) * 100.0) if len(sr_p_sub) > 1 else 0.0
    p_sharpe = float((p_cagr - 3.0) / p_vol) if p_vol > 0.0 else 0.0
    p_cum = (1 + sr_p_sub).cumprod()
    p_dd = float(((p_cum - p_cum.cummax()) / p_cum.cummax()).min() * 100.0) if not p_cum.empty else 0.0

    scorecard_rows.append({
        "Asset / Benchmark": "⭐ Portafoglio ARGUS",
        "Rendimento Totale": f"{p_tot_ret:+.2f}%",
        "CAGR Annuo": f"{p_cagr:+.2f}%",
        "Volatilità Annua": f"{p_vol:.2f}%",
        "Sharpe Ratio": f"{p_sharpe:.2f}",
        "Max Drawdown": f"{p_dd:.2f}%",
        "Alpha vs Portafoglio": "Base (0.00%)"
    })

    # Righe per ciascun Benchmark selezionato
    for bm_str in selected_bms:
        bm_code = bm_str.split(" ")[0]
        sr_bm_raw = load_benchmark_returns(bm_code, df_prices_ref, sr_port.index)
        sr_bm_sub = sr_bm_raw.reindex(sr_p_sub.index).fillna(0.0)
        bm_tot_ret = float(((1 + sr_bm_sub).cumprod() - 1).iloc[-1] * 100.0) if not sr_bm_sub.empty else 0.0
        bm_cagr = ((1 + bm_tot_ret / 100.0) ** (1.0 / p_n_yrs) - 1.0) * 100.0 if bm_tot_ret > -99.0 else -99.0
        bm_vol = float(sr_bm_sub.std() * np.sqrt(252) * 100.0) if len(sr_bm_sub) > 1 else 0.0
        bm_sharpe = float((bm_cagr - 3.0) / bm_vol) if bm_vol > 0.0 else 0.0
        bm_cum = (1 + sr_bm_sub).cumprod()
        bm_dd = float(((bm_cum - bm_cum.cummax()) / bm_cum.cummax()).min() * 100.0) if not bm_cum.empty else 0.0
        alpha_delta = p_cagr - bm_cagr

        scorecard_rows.append({
            "Asset / Benchmark": f"📊 {bm_str}",
            "Rendimento Totale": f"{bm_tot_ret:+.2f}%",
            "CAGR Annuo": f"{bm_cagr:+.2f}%",
            "Volatilità Annua": f"{bm_vol:.2f}%",
            "Sharpe Ratio": f"{bm_sharpe:.2f}",
            "Max Drawdown": f"{bm_dd:.2f}%",
            "Alpha vs Portafoglio": f"{alpha_delta:+.2f}%"
        })

    df_scorecard = pd.DataFrame(scorecard_rows)
    st.dataframe(
        df_scorecard,
        use_container_width=True,
        hide_index=True
    )
    st.markdown('<div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)

# ── TABELLA METRICHE E GLOSSARIO (POSIZIONATI SOTTO IL GRAFICO FULL-WIDTH) ──
col_m1, col_m2 = st.columns([1.5, 1.0])

def _fmt_metric_val(v, is_pct=False):
    if v is None:
        return "N/A"
    try:
        val = float(v)
        return f"{val:+.2f}%" if is_pct else f"{val:.2f}"
    except Exception:
        return str(v)

cagr_num = ret.get("cagr_pct")
tot_num = ret.get("total_return_pct")
alpha_num = ret.get("alpha_pct")
sharpe_num = ret.get("sharpe_ratio")
sortino_num = ret.get("sortino_ratio")
calmar_num = ret.get("calmar_ratio")
ir_num = ret.get("information_ratio")
n_yrs_val = ret.get("n_years", 0)

with col_m1:
    st.markdown("#### 📊 Tabella Analitica Metriche di Rendimento")
    data_ret = {
        "Metrica Quantitativa": [
            "CAGR (Tasso Annuo Composto)",
            "Rendimento Totale Cumulato",
            "Alpha di Jensen (vs Benchmark)",
            "Sharpe Ratio (Rendimento/Rischio)",
            "Sortino Ratio (Downside Risk)",
            "Calmar Ratio (CAGR/MaxDD)",
            "Information Ratio (Active Risk)",
            "Orizzonte Temporale Analizzato"
        ],
        "Valore Rilevato": [
            _fmt_metric_val(cagr_num, is_pct=True),
            _fmt_metric_val(tot_num, is_pct=True),
            _fmt_metric_val(alpha_num, is_pct=True),
            _fmt_metric_val(sharpe_num, is_pct=False),
            _fmt_metric_val(sortino_num, is_pct=False),
            _fmt_metric_val(calmar_num, is_pct=False),
            _fmt_metric_val(ir_num, is_pct=False),
            f"{float(n_yrs_val):.2f} Anni" if n_yrs_val else "N/A",
        ],
        "Target / Benchmark": [
            "🟢 Solido (> 7.0%)" if (cagr_num or 0) >= 7.0 else "🟡 Moderato",
            f"Storico reale transazioni",
            "🟢 Creazione Valore" if (alpha_num or 0) > 0 else "🔴 Sottoperformance",
            "Soglia Ottimale ≥ 1.00",
            "Soglia Ottimale ≥ 1.00",
            "Soglia Ottimale ≥ 0.50",
            "Soglia Ottimale ≥ 0.50",
            "Periodo attivo portafoglio"
        ]
    }
    st.dataframe(pd.DataFrame(data_ret), use_container_width=True, hide_index=True)

with col_m2:
    st.markdown("#### 📚 Guida & Glossario Metriche")
    
    # Indicatori di stato sintetici
    s_val = float(sharpe_num) if sharpe_num is not None else 0.0
    a_val = float(alpha_num) if alpha_num is not None else 0.0
    sharpe_badge = "🟢 Efficienza Elevata (≥ 1.0)" if s_val >= 1.0 else ("🟡 Efficienza Moderata (0.5 - 1.0)" if s_val >= 0.5 else "🔴 Efficienza Bassa (< 0.5)")
    alpha_badge = "🟢 Extra-Rendimento Positivo" if a_val > 0 else "🔴 Sottoperformance rispetto al Benchmark"
    
    st.markdown(f"""
    <div style="background: rgba(22,27,34,0.7); border: 1px solid rgba(255,153,0,0.3); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 700; color: #ff9900; margin-bottom: 6px;">💡 Sintesi Efficienza di Gestione</div>
        <div style="font-size: 12.5px; color: #c9d1d9; line-height: 1.45; margin-bottom: 8px;">
            Le metriche quantitative misurano se il rendimento ottenuto deriva dall'abilità di selezione (<b>Alpha</b>) o solo dall'esposizione al rischio di mercato.
        </div>
        <div style="font-size: 12px; color: #8b949e; line-height: 1.5;">
            • <b>Profilo Sharpe:</b> {sharpe_badge}<br>
            • <b>Profilo Alpha:</b> {alpha_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)

    glossary_modal("📚 Glossario Completo Metriche di Rendimento & Efficienza", """
<div style="font-size: 13.5px; line-height: 1.45; color: #c9d1d9;">

<!-- 1. ALPHA DI JENSEN -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏅 1. Alpha di Jensen (Extra-Rendimento Attivo)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Misura la componente di extra-rendimento puro generata dal portafoglio rispetto a quanto atteso in base al modello CAPM e al rischio sistematico di mercato (Beta).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>&alpha;</b> = R<sub>p</sub> &minus; [ R<sub>f</sub> + &beta; &times; (R<sub>b</sub> &minus; R<sub>f</sub>) ]
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Identificare la reale abilità (<i>Skill</i>) di selezione dei titoli e di allocazione del capitale, isolandola dall'andamento generale del mercato.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Confronta il CAGR del portafoglio con il CAGR del benchmark prescelto (es. SPY), depurato dall'effetto Beta e dal tasso privo di rischio al 3.0%.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>&alpha; > 0:</b> Sovraperformance attiva (creazione reale di valore aggiunto).<br>
    • <b>&alpha; = 0:</b> Rendimento perfettamente allineato al rischio assunto.<br>
    • <b>&alpha; < 0:</b> Sottoperformance rispetto al benchmark di riferimento.
  </div>
</div>

<!-- 2. SORTINO RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,255,153,0.25); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
  <div style="color: #00ff99; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🛡️ 2. Sortino Ratio (Efficienza sul Rischio di Perdita)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Variante evoluta dello Sharpe Ratio. Penalizza unicamente la volatilità negativa (<i>Downside Deviation</i>), considerando le oscillazioni rialziste come elemento favorevole.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,255,153,0.08); border-left: 3px solid #00ff99; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00ff99; text-align: center; font-size: 13px;">
      <b>Sortino Ratio</b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #00ff99; padding-bottom:1px;">R<sub>p</sub> &minus; R<sub>f</sub></span><span style="display:block; padding-top:1px;">&sigma;<sub>downside</sub></span></span>
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Valutare con precisione strategie asimmetriche (Growth, ETF tematici, opzioni) dove la volatilità al rialzo non deve essere punita.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Isola i rendimenti giornalieri inferiori al tasso privo di rischio (3.0%/252), calcola la deviazione standard quadratica dei soli ribassi e riscala su base annua con &radic;252.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 1.0:</b> Protezione dai ribassi debole o rendimento insufficiente.<br>
    • <b>1.0 – 2.0:</b> Ottimo profilo asimmetrico (buona difesa nelle correzioni).<br>
    • <b>> 2.0:</b> Profilo d'eccellenza con perdite minime nei mercati orso.
  </div>
</div>

<!-- 3. CALMAR RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🌊 3. Calmar Ratio (Rendimento / Massimo Drawdown)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Rapporto diretto tra il tasso di crescita annuo composto (CAGR) e la peggiore flessione percentuale storica registrata dal portafoglio (<i>Maximum Drawdown</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #58a6ff; text-align: center; font-size: 13px;">
      <b>Calmar Ratio</b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #58a6ff; padding-bottom:1px;">CAGR</span><span style="display:block; padding-top:1px;">|Max Drawdown|</span></span>
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Quantifica quanti punti di rendimento annuo costante si ottengono per ciascun punto percentuale di capitale esposto al rischio di perdita estrema durante i crolli storici.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Rapporto tra il CAGR calcolato dall'inizio dello storico e il massimo drawdown percentuale registrato sulla serie cumulata.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 0.50:</b> Portafoglio fragile (il rendimento non compensa la gravità dei drawdown passati).<br>
    • <b>0.50 – 1.00:</b> Profilo equilibrato e sostenibile.<br>
    • <b>> 1.00:</b> Profilo resiliente (il rendimento annuo supera l'intero drawdown storico massimo).
  </div>
</div>

<!-- 4. INFORMATION RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(188,140,255,0.25); border-radius: 10px; padding: 12px 14px; margin-bottom: 4px;">
  <div style="color: #bc8cff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🎯 4. Information Ratio (Costanza dell'Alpha)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Rapporto tra l'extra-rendimento medio generato rispetto al benchmark e il <i>Tracking Error</i> (la volatilità della differenza dei rendimenti).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(188,140,255,0.08); border-left: 3px solid #bc8cff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #bc8cff; text-align: center; font-size: 13px;">
      <b>Information Ratio</b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #bc8cff; padding-bottom:1px;">Media(R<sub>p</sub> &minus; R<sub>b</sub>)</span><span style="display:block; padding-top:1px;">Tracking Error</span></span> &times; &radic;252
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Valutare la costanza e l'affidabilità con cui una strategia batte il mercato: indica se i sovrarendimenti sono stabili o episodici.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato sulla serie giornaliera dei differenziali di rendimento attivo <i>(R<sub>p,t</sub> &minus; R<sub>b,t</sub>)</i> divisa per la loro deviazione standard annualizzata.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 0.00:</b> Sottoperformance rispetto all'indice di mercato.<br>
    • <b>0.00 – 0.49:</b> Capacità di gestione attiva modesta.<br>
    • <b>0.50 – 0.99:</b> Ottima costanza di sovraperformance.<br>
    • <b>&ge; 1.00:</b> Gestione attiva d'élite (benchmark d'eccellenza istituzionale).
  </div>
</div>

</div>
""", button_label="📖 Apri Glossario Metriche")

st.divider()

# ── IMPRONTA DI RISCHIO 360° (RADAR FATTORIALE) ──────────────────────
col_head_r1, col_head_r2 = st.columns([3.2, 1.1])
with col_head_r1:
    section("🕸️ Impronta di Rischio 360° (Radar Fattoriale)")
    st.caption("Mappa multidimensionale dell'esposizione ai fattori di rischio e di stile rispetto al Benchmark Neutro (50/100).")
with col_head_r2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("🕸️ Guida all'Impronta di Rischio 360° (Radar Fattoriale)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Impronta di Rischio 360°</div>
  <div>Un diagramma Spider/Radar multidimensionale che sintetizza il profilo quantitativo del portafoglio su 6 pilastri fondamentali di rischio sistemico, stile d'investimento (Fama-French) e asimmetria distributiva, confrontandolo con un Benchmark Neutro di riferimento (punteggio 50/100).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Come si calcolano i 6 Pilastri (Normalizzazione 0 – 100)</div>
  <div>Ciascun pilastro viene mappato su una scala standardizzata da 0 a 100 centrata sul valore neutrale 50:</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Market Beta:</b> min(100, max(0, &beta; &times; 50))<br>
    • <b>Size SMB:</b> min(100, max(0, SMB &times; 50 + 50))<br>
    • <b>Value HML:</b> min(100, max(0, HML &times; 50 + 50))<br>
    • <b>Volatilità:</b> min(100, max(0, &sigma;<sub>annua</sub>% &times; 2))<br>
    • <b>Diversificazione DR:</b> min(100, max(0, (DR &minus; 1.0) &times; 100))<br>
    • <b>Asimmetria Skew:</b> min(100, max(0, Skew &times; 25 + 50))
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Permette di identificare istantaneamente sbilanciamenti nascosti, bias dimensionali (Small vs Large Cap), inclinazioni di stile (Value vs Growth) e deficit di diversificazione che un'analisi basata sul solo rendimento complessivo non è in grado di rilevare.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS integra la regressione Fama-French a 3 fattori sui rendimenti storici con il Diversification Ratio (DR di Choueifaty) e la skewness campionaria, calcolando i pesi effettivi e proiettando il poligono arancione sovrapposto al perimetro del benchmark neutro tratteggiato.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Punteggio = 50 (Linea Grigia):</b> Allineato alla neutralità del mercato di riferimento.<br>
    • <b>Punteggio > 50 (Poligono Espanso):</b> Esposizione superiore (es. Beta aggressivo > 1, tilt Small Cap, o alta volatilità).<br>
    • <b>Punteggio < 50 (Poligono Contratto):</b> Esposizione inferiore (es. profilo difensivo, tilt Large Cap/Growth, o bassa volatilità).<br>
    • <b>Simmetria:</b> Un poligono armonico vicino al cerchio a 50 indica una gestione multi-asset bilanciata senza dipendenze critiche da singoli fattori.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Radar 360°?")

col_rd1, col_rd2 = st.columns([1.4, 1.0])

with col_rd1:
    fig_radar = render_factor_radar_chart(results)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_rd2:
    m_info = results.get("metrics", {})
    mk_info = m_info.get("market_risk", {})
    con_info = m_info.get("concentration", {})

    b_val = float(mk_info.get("beta", 1.0) or 1.0)
    smb_val = float(mk_info.get("smb_tilt", 0.0) or 0.0)
    hml_val = float(mk_info.get("hml_tilt", 0.0) or 0.0)
    vol_val = float(mk_info.get("volatility_annual_pct", 15.0) or 15.0)
    dr_val = float(con_info.get("diversification_ratio", 1.2) or 1.2)
    skew_val = float(mk_info.get("skewness", 0.0) or 0.0)

    b_desc = "Sensibile al Mercato" if b_val > 1.10 else ("Difensivo" if b_val < 0.90 else "Neutro")
    smb_desc = "Tilt Small Cap" if smb_val > 0.15 else ("Tilt Large Cap" if smb_val < -0.15 else "Neutro Size")
    hml_desc = "Tilt Value" if hml_val > 0.15 else ("Tilt Growth" if hml_val < -0.15 else "Neutro Stile")
    vol_desc = "Elevata" if vol_val > 20 else ("Moderata" if vol_val >= 12 else "Contenuta")
    dr_desc = "Ottima" if dr_val >= 1.30 else ("Sufficiente" if dr_val >= 1.10 else "Bassa")
    skew_desc = "Favorevole (+)" if skew_val > 0.10 else ("Tail Risk (-)" if skew_val < -0.10 else "Simmetrica")

    st.markdown(f"""
    <div style="background: rgba(22,27,34,0.7); border: 1px solid rgba(255,153,0,0.3); border-radius: 12px; padding: 16px; margin-top: 5px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 14px; font-weight: 700; color: #ffffff;">💡 Diagnostica Fattoriale 360°</span>
            <span style="font-size: 11px; background: rgba(255,153,0,0.15); color: #ffb74d; padding: 2px 8px; border-radius: 8px; border: 1px solid rgba(255,153,0,0.3);">Target 50/100</span>
        </div>
        <div style="font-size: 12px; color: #8b949e; margin-bottom: 12px; line-height: 1.4;">
            Ripartizione quantitativa dell'impronta di rischio su 6 pilastri fondamentali:
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 11.5px;">
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🟢 <b>Market Beta:</b> {b_val:.2f}</span>
                <span style="color: #3fb950; font-weight: 600;">{b_desc}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🔵 <b>Size SMB:</b> {smb_val:+.2f}</span>
                <span style="color: #58a6ff; font-weight: 600;">{smb_desc}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🟣 <b>Value HML:</b> {hml_val:+.2f}</span>
                <span style="color: #bc8cff; font-weight: 600;">{hml_desc}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🟡 <b>Volatilità:</b> {vol_val:.1f}%</span>
                <span style="color: #d29922; font-weight: 600;">{vol_desc}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🟢 <b>Diversificazione DR:</b> {dr_val:.2f}</span>
                <span style="color: #3fb950; font-weight: 600;">{dr_desc}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.03); padding: 5px 10px; border-radius: 6px;">
                <span style="color: #c9d1d9;">🔴 <b>Asimmetria Skew:</b> {skew_val:+.2f}</span>
                <span style="color: {'#3fb950' if skew_val >= 0 else '#f85149'}; font-weight: 600;">{skew_desc}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── ARGUS Smart Risk Advisor Panel ─────────────────────────────
col_head_adv1, col_head_adv2 = st.columns([3.2, 1.1])
with col_head_adv1:
    section("🛡️ ARGUS Quant Advisor & Diagnostica Automatizzata")
    st.caption("Motore di intelligenza analitica per l'audit continuo del portafoglio, l'identificazione di vulnerabilità e raccomandazioni correttive.")
with col_head_adv2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("🛡️ Guida all'ARGUS Quant Advisor & Health Score", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Health Score & Quant Advisor</div>
  <div>Un sistema esperto deterministico che esegue un audit approfondito del portafoglio analizzando 12 vettori quantitativi per sintetizzare un indice globale di salute (0 – 100) e generare suggerimenti operativi mirati.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Come si calcola l'Health Score</div>
  <div>Il punteggio parte da una base ideale di 100 punti ed applica decurtazioni proporzionali alla severità dei rischi riscontrati:</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Violazione Critica:</b> &minus;15 punti ciascuna (es. VaR eccessivo, singola azione > 20%)<br>
    • <b>Warning Moderato:</b> &minus;8 punti ciascuna (es. concentrazione settoriale > 35%)<br>
    • <b>Bonus Efficienza:</b> Fino a +5 punti per Sharpe Ratio elevato e DR ottimale
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Fornisce una sintesi immediata al gestore o all'investitore sulle vulnerabilità prima che shock di mercato impattino il capitale, traducendo metriche complesse in raccomandazioni pratiche.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il modulo <code>core/advisor.py</code> valuta simultaneamente concentrazione HHI, liquidità, asimmetria, stress test storici e conformità ai limiti di rischio, producendo un report prescrittivo.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🟢 <b>Score &ge; 80 / 100:</b> Profilo Eccellente (asset ben bilanciati e rischi controllati).<br>
    • 🟡 <b>Score 60 – 79 / 100:</b> Profilo Attenzionato (presenza di moderati sbilanciamenti).<br>
    • 🔴 <b>Score < 60 / 100:</b> Punti di Vulnerabilità Critici (necessario intervento correttivo).
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Quant Advisor?")

from core.advisor import generate_quant_advisory_report
advisor_data = generate_quant_advisory_report(results)
health_score = advisor_data["health_score"]
diagnostics = advisor_data["diagnostics"]

with st.expander(f"🛡️ ARGUS Quant Advisor & Diagnostica Anomalie (Score Salute: {health_score}/100)", expanded=True):
    col_hs1, col_hs2 = st.columns([1, 3])
    with col_hs1:
        score_color = "#3fb950" if health_score >= 80 else ("#ff9900" if health_score >= 60 else "#f85149")
        st.markdown(f"""
        <div style="background: rgba(22,27,34,0.7); border: 2px solid {score_color}; border-radius: 12px; padding: 20px; text-align: center;">
            <div style="font-size:11px; color:#8b949e;">HEALTH SCORE PORTAFOGLIO</div>
            <div style="font-size:36px; font-weight:800; color:{score_color}; margin: 10px 0;">{health_score} / 100</div>
            <div style="font-size:12px; color:#c9d1d9;">{"Profilo Eccellente" if health_score >= 80 else ("Profilo Attenzionato" if health_score >= 60 else "Punti di Vulnerabilità")}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_hs2:
        if not diagnostics:
            st.success("✅ Nessun elemento di vulnerabilità o anomalia critica rilevato nel portafoglio.")
        else:
            for diag in diagnostics:
                dtype = diag["type"]
                badge_icon = "🟢" if dtype == "SUCCESS" else ("🔴" if dtype == "CRITICAL" else ("🟡" if dtype == "WARNING" else "🔵"))
                border_c = '#3fb950' if dtype == 'SUCCESS' else ('#f85149' if dtype == 'CRITICAL' else ('#ff9900' if dtype == 'WARNING' else '#58a6ff'))
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border-left: 4px solid {border_c}; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#ffffff;">{badge_icon} {diag['title']}</span>
                        <span style="font-size:10px; padding: 2px 8px; border-radius:10px; background:rgba(255,255,255,0.1); color:#8b949e;">{diag['category']}</span>
                    </div>
                    <div style="font-size:13px; color:#c9d1d9; margin-top:6px;">{diag['description']}</div>
                    <div style="font-size:12px; color:#3fb950; font-weight:600; margin-top:4px;">👉 Raccomandazione: {diag['actionable_recommendation']}</div>
                </div>
                """, unsafe_allow_html=True)

st.divider()

# ── PANNELLO RISK THRESHOLDS & EARLY WARNINGS ──────────────────
col_head_lim1, col_head_lim2 = st.columns([3.2, 1.1])
with col_head_lim1:
    section("🚨 Controllo Limiti di Rischio & Early Warning")
    st.caption("Verifica della conformità del portafoglio rispetto ai limiti prudenziali e mandati di gestione del rischio.")
with col_head_lim2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("🚨 Guida al Controllo Limiti di Rischio (Early Warning)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Sistema di Risk Limits</div>
  <div>Un framework di monitoraggio in tempo reale che verifica che l'allocazione rispetti 6 vincoli di controllo del rischio stabiliti secondo le migliori pratiche istituzionali di gestione patrimoniale.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Le 6 Regole di Rischio Istituzionali</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Peso Max Singolo Titolo:</b> &le; 20.0% (limita il rischio emittente)<br>
    • <b>Concentrazione Settoriale GICS:</b> &le; 35.0% (previene shock di settore)<br>
    • <b>Value at Risk 95% (1g):</b> &le; 3.00% (tetto massimo alla perdita giornaliera)<br>
    • <b>Market Beta Sistemico:</b> &le; 1.25 (limita la volatilità rispetto al mercato)<br>
    • <b>Diversification Ratio (DR):</b> &ge; 1.20 (garantisce de-correlazione reale)<br>
    • <b>Indice di Concentrazione HHI:</b> &le; 0.25 (dispersione ottimale del capitale)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Evita il <i>Risk Drift</i> (deriva incontrollata del rischio) e previene crolli di capitale dovuti alla sovraesposizione su singoli titoli o mercati correlati.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il modulo <code>core/risk_limits.py</code> confronta ciascun valore con la rispettiva soglia limite e calcola la percentuale di conformità complessiva: <code>Compliance % = (Regole Rispettate / Totale Regole) &times; 100</code>.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🟢 <b>Pass:</b> Parametro pienamente conforme.<br>
    • 🟡 <b>Warning:</b> Parametro in avvicinamento alla soglia di guardia.<br>
    • 🔴 <b>Breach:</b> Violazione del limite. È consigliato intervenire con un ribilanciamento o una riduzione di posizione.
  </div>
</div>

</div>
""", button_label="💡 Spiegazione Limiti di Rischio")

from core.risk_limits import check_risk_limits
limits_data = check_risk_limits(results)
comp_pct = limits_data["compliance_pct"]
df_eval = limits_data["evaluations"]

col_rl1, col_rl2 = st.columns([1, 2.5])
with col_rl1:
    st.markdown(f"""
    <div style="background: rgba(22,27,34,0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; text-align: center;">
        <div style="font-size:11px; color:#8b949e;">CONFORMITÀ AI LIMITI ISTITUZIONALI</div>
        <div style="font-size:32px; font-weight:800; color:{'#3fb950' if comp_pct >= 80 else '#ff9900'}; margin: 6px 0;">{comp_pct}%</div>
        <div style="font-size:12px; color:#c9d1d9;">🟢 {limits_data['pass_count']} Pass | 🟡 {limits_data['warning_count']} Warning | 🔴 {limits_data['breach_count']} Breach</div>
    </div>
    """, unsafe_allow_html=True)

with col_rl2:
    st.dataframe(
        df_eval[["status_icon", "rule_name", "current_value", "limit_threshold", "unit"]].rename(columns={
            "status_icon": "Stato",
            "rule_name": "Regola di Rischio",
            "current_value": "Valore Rilevato",
            "limit_threshold": "Soglia Limite",
            "unit": "Unità"
        }),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ── ESPOSIZIONE GEOGRAFICA E SETTORIALE (SUNBURST CHART) ──────
col_head_sun1, col_head_sun2 = st.columns([3.2, 1.1])
with col_head_sun1:
    section("🌍 Esposizione Geografica & Settoriale (Sunburst Chart)")
    st.caption("Visualizzazione gerarchica multilivello dell'allocazione del capitale: Paese ➔ Settore GICS ➔ Ticker.")
with col_head_sun2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("🌍 Guida al Grafico Sunburst Multilivello", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Grafico Sunburst</div>
  <div>Un diagramma radiale a cerchi concentrici che visualizza la struttura gerarchica del portafoglio, mostrando simultaneamente la ripartizione geografica, la diversificazione settoriale e le singole posizioni azionarie.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Struttura ad Anelli & Mappa Cromatica PnL</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Anello Centrale:</b> Paese di quotazione / Macro-Area Geografica<br>
    • <b>Anello Intermedio:</b> Settore Industriale GICS (es. Technology, Healthcare)<br>
    • <b>Anello Esterno:</b> Singoli Ticker (angolo proporzionale al controvalore in €)<br>
    • <b>Scala Cromatica:</b> Dal Rosso Cremisi (&minus;20%) al Verde Neon (+20%) per il PnL Latente %
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Permette di cogliere all'istante concentrazioni settoriali o geografiche eccessive e verificare visivamente quali cluster industriali stanno trainando i guadagni o le perdite del portafoglio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS calcola il controvalore di mercato per ogni foglia dell'albero gerarchico, aggrega le posizioni per settore e nazione ed applica il colore continuo basandosi sulle plusvalenze/minusvalenze non realizzate dal motore contabile FIFO.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Ampiezza dello Spicchio:</b> Percentuale del capitale totale allocata nel Paese, Settore o Titolo.<br>
    • <b>Verde Brillante:</b> Posizioni con forti plusvalenze latenti.<br>
    • <b>Grigio Scuro:</b> Posizioni vicine al pareggio (Break-Even).<br>
    • <b>Rosso Intenso:</b> Posizioni in perdita su cui valutare strategie di Tax-Loss Harvesting o Stop-Loss.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Sunburst?")

if not pos.empty:
    active_pos = pos[pos["qty_net"] > 0].copy() if "qty_net" in pos.columns else pos.copy()
    
    # Risoluzione intelligente Paese e Settore per ciascun asset
    try:
        from core.metadata_resolver import resolve_asset_metadata
    except ImportError:
        from core.multi_portfolio import resolve_asset_metadata
    for idx_p, r_p in active_pos.iterrows():
        t_p = str(r_p.get("ticker", "")).strip()
        ac_p = str(r_p.get("asset_class", ""))
        c_p = r_p.get("country")
        s_p = r_p.get("gics_sector") if pd.notna(r_p.get("gics_sector")) else r_p.get("sector")
        c_clean, s_clean = resolve_asset_metadata(t_p, ac_p, c_p, s_p)
        active_pos.at[idx_p, "country_clean"] = c_clean
        active_pos.at[idx_p, "sector_clean"] = s_clean

    import plotly.express as px

    # Palette di colori ad altissimo contrasto per PnL (Rosso Cremisi Intenso -> Grigio Antracite -> Verde Smeraldo Neon)
    vibrant_pnl_scale = [
        [0.0, "#d90429"],   # Rosso Cremisi Intenso per perdite pesanti (< -20%)
        [0.35, "#ff4d6d"],  # Rosso acceso per perdite moderate (-5%)
        [0.5, "#21262d"],   # Grigio scuro per pareggio (0%)
        [0.65, "#2ea043"],  # Verde brillante per profitti moderati (+5%)
        [1.0, "#00e676"]    # Verde Neon per profitti elevati (> +20%)
    ]

    fig_sunburst = px.sunburst(
        active_pos,
        path=["country_clean", "sector_clean", "ticker"],
        values="current_value",
        color="unrealized_pnl_pct" if "unrealized_pnl_pct" in active_pos.columns else None,
        color_continuous_scale=vibrant_pnl_scale,
        color_continuous_midpoint=0,
        labels={
            "current_value": "Controvalore (€)",
            "unrealized_pnl_pct": "PnL Latente (%)",
            "country_clean": "Paese",
            "sector_clean": "Settore",
            "ticker": "Asset"
        }
    )
    fig_sunburst.update_traces(
        textinfo="label+percent root",
        insidetextorientation="horizontal",
        leaf_opacity=0.92,
        marker=dict(line=dict(color="#0d1117", width=1.5)),
        hovertemplate="<b>%{label}</b><br>💰 Controvalore: € %{value:,.2f}<br>📊 Quota Portafoglio: %{percentRoot:.1%}<br>📈 PnL Latente: %{color:+.2f}%<extra></extra>"
    )
    fig_sunburst.update_layout(
        template="plotly_dark",
        coloraxis_colorbar=dict(
            title="PnL Latente %",
            ticksuffix="%",
            len=0.85,
            thickness=16
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=500
    )
    apply_plotly_theme(fig_sunburst)
    st.plotly_chart(fig_sunburst, use_container_width=True)

st.divider()

# ── 🧠 ARGUS AI ANALYST & COPILOT ──
section("🧠 ARGUS AI Analyst | Executive Memorandum & Copilot")
st.caption("Diagnosi narrativa istituzionale e assistente quantitativo basato su intelligenza artificiale dual-engine (LLM Online / NLG Offline Deterministico).")

render_info_modal(
    title="Come Funziona ARGUS AI Analyst & Copilot",
    content="""
<div style="font-size: 13.5px; line-height: 1.6; color: #c9d1d9;">

<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🎯 Architettura Dual-Engine Resiliente</b><br>
  ARGUS AI Analyst non dipende esclusivamente dal cloud: opera con un'architettura ibrida a due livelli per garantire disponibilità e privacy al 100%.
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">1. Motore NLG Quantitativo Deterministico (Offline 100%)</div>
  <div>Analizza matematicamente i dati di portafoglio (VaR 95%, Sharpe Ratio, Volatilità, Drawdown, Indice HHI, Regime Markov e Altman Z-Score) e compone paragrafi discorsivi rigorosi in perfetto italiano finanziario senza inviare alcun dato a server terzi.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">2. Connessione LLM Remota (Google Gemini / OpenAI)</div>
  <div>Se configuri una chiave API (Gemini o OpenAI), ARGUS struttura un prompt istituzionale (CFA/FRM persona) con la sintesi delle metriche per generare un Memorandum ad alta elaborazione semantica e rispondere a domande libere in linguaggio naturale.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔒 Privacy e Sicurezza</div>
  <div>Le chiavi API inserite nell'interfaccia vengono conservate esclusivamente in memoria volatile durante la sessione utente e non vengono mai salvate su file di log o database.</div>
</div>

</div>
""",
    button_label="📖 Guida & Metodologia AI Analyst"
)

from core.ai_analyst import generate_portfolio_narrative_memorandum, query_argus_assistant

col_ai_cfg1, col_ai_cfg2, col_ai_btn = st.columns([2.5, 3.5, 2.5])
with col_ai_cfg1:
    ai_provider = st.selectbox(
        "Motore AI",
        ["Auto (Rileva Chiave / NLG Offline)", "NLG Deterministico Offline (Privacy 100%)", "Google Gemini API", "OpenAI API"],
        key="ai_analyst_provider_sel"
    )
with col_ai_cfg2:
    provider_map = {
        "Auto (Rileva Chiave / NLG Offline)": "auto",
        "NLG Deterministico Offline (Privacy 100%)": "offline",
        "Google Gemini API": "gemini",
        "OpenAI API": "openai"
    }
    sel_prov = provider_map.get(ai_provider, "auto")
    user_api_key = ""
    if sel_prov in ("gemini", "openai", "auto"):
        user_api_key = st.text_input(
            "Chiave API (Opzionale)",
            type="password",
            placeholder="Gemini: AIza... | OpenAI: sk-...",
            help="Incolla la tua chiave API Google Gemini (AIza...) o OpenAI (sk-...). Se lasciata vuota, ARGUS usa le variabili .env o il motore quantitativo deterministico offline.",
            key="ai_analyst_api_key_input"
        )
with col_ai_btn:
    st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
    gen_memo_btn = st.button("🚀 Genera / Aggiorna Memorandum", type="primary", use_container_width=True, key="btn_gen_ai_memo")

# Stato del Memorandum
if "ai_memorandum" not in st.session_state or gen_memo_btn:
    with st.spinner("Elaborazione quantitativa del Memorandum in corso..."):
        memo_dict = generate_portfolio_narrative_memorandum(
            results,
            api_key=user_api_key.strip() if user_api_key else None,
            provider=sel_prov
        )
        st.session_state["ai_memorandum"] = memo_dict

cur_memo = st.session_state.get("ai_memorandum", {})
if cur_memo:
    memo_text = cur_memo.get("full_text", "")
    st.markdown(
        f"""<div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 153, 0, 0.3); border-radius: 12px; padding: 20px 24px; margin-top: 15px; margin-bottom: 20px; backdrop-filter: blur(12px);">
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 15px;">
  <span style="font-size: 12px; color: #8b949e;">⚙️ Motore attivo: <b style="color: #58a6ff;">{cur_memo.get('engine', 'NLG')}</b> | Data: {cur_memo.get('timestamp', '')}</span>
  <span style="font-size: 11px; background: rgba(63, 185, 80, 0.15); color: #3fb950; padding: 3px 10px; border-radius: 12px; border: 1px solid rgba(63, 185, 80, 0.3);">✓ Verificato</span>
</div>
{memo_text}
</div>""",
        unsafe_allow_html=True
    )
    
    st.download_button(
        "📋 Scarica Memorandum in Markdown (.md)",
        data=memo_text.encode("utf-8"),
        file_name=f"ARGUS_Executive_Memorandum_{st.session_state.get('portfolio_name', 'Portfolio').replace(' ', '_')}.md",
        mime="text/markdown",
        key="btn_download_ai_memo"
    )

# ── INTERACTIVE COPILOT CHAT ──
with st.expander("💬 ARGUS Quant Copilot (Fai una domanda sul portafoglio)", expanded=False):
    st.caption("Digita una domanda o clicca su uno dei suggerimenti rapidi:")
    col_chip1, col_chip2, col_chip3, col_chip4 = st.columns(4)
    with col_chip1:
        if st.button("📊 Analisi Rischio & VaR", use_container_width=True, key="chip_var"):
            st.session_state["copilot_query"] = "Qual è la mia perdita massima stimata e il VaR 95%?"
    with col_chip2:
        if st.button("📈 Sharpe & Performance", use_container_width=True, key="chip_sharpe"):
            st.session_state["copilot_query"] = "Come valuti il rendimento e lo Sharpe Ratio del portafoglio?"
    with col_chip3:
        if st.button("🏆 Top Asset & Concentrazione", use_container_width=True, key="chip_pos"):
            st.session_state["copilot_query"] = "Quali sono i titoli principali e il livello di concentrazione?"
    with col_chip4:
        if st.button("💡 Consigli Ribilanciamento", use_container_width=True, key="chip_rebal"):
            st.session_state["copilot_query"] = "Quali operazioni tattiche suggerisci per migliorare il portafoglio?"

    user_query = st.text_input(
        "Domanda all'analista:",
        value=st.session_state.get("copilot_query", ""),
        placeholder="Es: Quale titolo contribuisce di più al rischio? Come posso ottimizzare l'allocazione?",
        key="copilot_text_input"
    )
    
    if st.button("Invia Domanda a Copilot", type="secondary", key="btn_ask_copilot"):
        if user_query.strip():
            with st.spinner("ARGUS Copilot sta analizzando i dati..."):
                answer = query_argus_assistant(
                    user_query,
                    results,
                    api_key=user_api_key.strip() if user_api_key else None,
                    provider=sel_prov
                )
                st.markdown(
                    f"""<div style="background: rgba(13, 17, 23, 0.9); border-left: 4px solid #58a6ff; border-radius: 8px; padding: 14px 18px; margin-top: 10px;">
<div style="font-weight: 700; color: #58a6ff; margin-bottom: 6px;">🤖 Risposta di ARGUS Copilot:</div>
<div style="font-size: 13.5px; line-height: 1.6; color: #e6edf3;">{answer}</div>
</div>""",
                    unsafe_allow_html=True
                )

st.divider()

# ── CENTRO ESPORTAZIONE REPORT & DATI (IN FONDO ALLA PAGINA) ──
section("📥 Centro Esportazione Report & Power BI Data Pack")
st.caption("Esporta il Factsheet Executive HTML interattivo, il Factsheet PDF, il Workbook Excel Multi-Tab completo o il pacchetto Star Schema per Power BI (.zip).")

col_exp_html, col_exp_pdf, col_exp_excel, col_exp_bi = st.columns(4)

with col_exp_html:
    import os
    port_filename = f"ARGUS_Factsheet_{st.session_state.get('portfolio_name', 'Portfolio').replace(' ', '_')}.html"
    file_path = os.path.abspath(os.path.join("exports", port_filename))

    if st.button("🌐 Genera & Apri Factsheet HTML", type="primary", use_container_width=True, key="btn_generate_html_on_demand"):
        try:
            import importlib
            import core.html_exporter
            importlib.reload(core.html_exporter)
            from core.html_exporter import generate_interactive_html_report

            os.makedirs("exports", exist_ok=True)
            generate_interactive_html_report(results, output_path=file_path)
            st.session_state["last_html_export"] = file_path
            
            if os.path.exists(file_path):
                os.startfile(file_path)
                st.toast("Factsheet generato ed aperto nel browser!", icon="✅")
        except Exception as e:
            st.error(f"Errore nella generazione HTML: {e}")

    if st.session_state.get("last_html_export") == file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            st.download_button(
                label="💾 Scarica File HTML (.html)",
                data=f.read(),
                file_name=port_filename,
                mime="text/html",
                use_container_width=True,
                key="btn_download_html_file"
            )
        st.caption(f"📁 Salvato in `exports/{port_filename}`")

with col_exp_pdf:
    try:
        from core.report_exporter import generate_pdf_factsheet
        pdf_bytes = generate_pdf_factsheet(
            results,
            portfolio_name=st.session_state.get("portfolio_name", "Main Portfolio")
        )
        st.download_button(
            label="📄 Scarica Executive PDF Factsheet",
            data=pdf_bytes,
            file_name=f"ARGUS_Factsheet_{st.session_state.get('portfolio_name', 'Portfolio').replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Errore nella generazione PDF: {e}")

with col_exp_excel:
    try:
        from core.report_exporter import generate_excel_report
        excel_bytes = generate_excel_report(
            results,
            portfolio_name=st.session_state.get("portfolio_name", "Main Portfolio")
        )
        st.download_button(
            label="📊 Scarica Report Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"ARGUS_Report_MultiTab_{st.session_state.get('portfolio_name', 'Portfolio').replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Errore nella generazione Excel: {e}")

with col_exp_bi:
    try:
        import importlib
        import scripts.export_star_schema
        importlib.reload(scripts.export_star_schema)
        from scripts.export_star_schema import generate_star_schema_zip
        zip_bytes = generate_star_schema_zip(results)
        st.download_button(
            label="🗃️ Scarica Power BI Star Schema (.zip)",
            data=zip_bytes,
            file_name=f"ARGUS_PowerBI_StarSchema_{st.session_state.get('portfolio_name', 'Portfolio').replace(' ', '_')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Errore Power BI Export: {e}")

st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
col_csv1, col_csv2 = st.columns(2)

with col_csv1:
    if not pos.empty:
        csv_pos = pos.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📋 Esporta CSV Dettaglio Posizioni",
            data=csv_pos,
            file_name=f"posizioni_{st.session_state.get('portfolio_name', 'Portfolio')}.csv",
            mime="text/csv",
            use_container_width=True
        )

with col_csv2:
    if not sr_port.empty:
        sr_bm_sliced = sr_bm.reindex(sr_port.index).fillna(0.0)
        df_ret_exp = pd.DataFrame({
            "date": sr_port.index.strftime("%Y-%m-%d"),
            "portfolio_return_pct": (sr_port.values * 100).round(4),
            "benchmark_return_pct": (sr_bm_sliced.values * 100).round(4)
        })
        csv_ret = df_ret_exp.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📈 Esporta CSV Rendimenti Storici",
            data=csv_ret,
            file_name=f"rendimenti_{st.session_state.get('portfolio_name', 'Portfolio')}.csv",
            mime="text/csv",
            use_container_width=True
        )
