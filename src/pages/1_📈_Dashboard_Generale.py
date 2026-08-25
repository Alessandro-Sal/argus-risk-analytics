import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import importlib
import core.ui_utils
import core.risk_engine
import core.duckdb_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
importlib.reload(core.duckdb_engine)
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

from core.yield_curve import get_active_risk_free_rate

custom_rf_val = (float(st.session_state.get("custom_rf_rate_pct", 2.75)) / 100.0) if st.session_state.get("rf_mode") == "Manuale" else None
active_rf_resolved = get_active_risk_free_rate(currency=st.session_state.get("base_currency", "EUR"), custom_override=custom_rf_val)

rf_info = results.get("risk_free") or results.get("metrics", {}).get("risk_free")
if not rf_info or not isinstance(rf_info, dict) or "rate_pct" not in rf_info:
    rf_info = active_rf_resolved

rf_rate_pct = float(rf_info.get("rate_pct", active_rf_resolved["rate_pct"]))
rf_source = rf_info.get("source", active_rf_resolved["source"])
rf_currency = rf_info.get("currency", active_rf_resolved["currency"])

import uuid
import re
from core.ui_utils import format_institutional_5point_html

rf_modal_id = str(uuid.uuid4())[:8]
rf_modal_content = format_institutional_5point_html(
    title=f"🏛️ Tasso Privo di Rischio (Risk-Free Rate Rf) — {rf_currency}: {rf_rate_pct:.2f}%",
    what_is=f"Il rendimento teorico di un investimento monetario a rischio di credito e di liquidità nullo su orizzonte a breve termine (1-3 mesi). In ARGUS è attualmente pari a <b>{rf_rate_pct:.2f}%</b> (Fonte: <i>{rf_source}</i>) per la valuta base <b>{rf_currency}</b>.",
    how_calc="• EUR: BCE €STR (Euro Short-Term Rate) / Bund 3M (XEON.DE)<br>• USD: US 3M Treasury Bill (^IRX) / SOFR<br>• GBP: Bank of England SONIA (CSH2.L)<br>• CHF: SNB SARON Swiss Overnight Rate",
    why_useful="Fornisce l'hurdle rate (costo opportunità del capitale) per determinare se la volatilità di un asset o portafoglio è adeguatamente remunerata rispetto al parcheggio monetario.",
    argus_calc="Recupero live dalle banche centrali (BCE, Federal Reserve via Yahoo Finance ^IRX / XEON.DE) con caching orario e conversione algebrica su base giornaliera r_daily = (1 + Rf)^(1/252) - 1.",
    how_to_read="• 🟢 Rendimento Portafoglio > Rf (Creazione reale di ricchezza)<br>• 🟡 Rendimento ≈ Rf (Rendimento assorbito dal tasso monetario)<br>• 🔴 Rendimento < Rf (Distruzione di valore economico rispetto a titoli di stato a brevissimo termine)."
)

cleaned_rf = re.sub(r'<!--.*?-->', '', rf_modal_content, flags=re.DOTALL)
cleaned_rf = re.sub(r'>\s+<', '><', cleaned_rf)
cleaned_rf = re.sub(r'\s*\n\s*', ' ', cleaned_rf)
safe_rf_content = cleaned_rf.strip()

st.markdown(f"""
<style>
#modal-toggle-{rf_modal_id} {{ display: none; }}
.modal-overlay-{rf_modal_id} {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 999999;
    align-items: center;
    justify-content: center;
}}
#modal-toggle-{rf_modal_id}:checked ~ .modal-overlay-{rf_modal_id} {{
    display: flex;
}}
.modal-backdrop-{rf_modal_id} {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(10, 14, 20, 0.85);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    cursor: pointer;
    z-index: 1;
}}
.modal-content-{rf_modal_id} {{
    background: #161b22;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 24px 28px;
    border-radius: 16px;
    width: 92%;
    max-width: 720px;
    max-height: 85vh;
    overflow-y: auto;
    color: #e6edf3;
    position: relative;
    z-index: 2;
    box-shadow: 0 24px 60px rgba(0,0,0,0.9), 0 0 30px rgba(255, 153, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    text-align: left;
    animation: modalScaleIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}}
.modal-close-{rf_modal_id} {{
    position: absolute;
    top: 16px;
    right: 18px;
    font-size: 24px;
    color: #8b949e;
    cursor: pointer;
    line-height: 1;
    transition: color 0.2s ease;
}}
.modal-close-{rf_modal_id}:hover {{ color: #ffffff; }}
.rf-badge-btn-{rf_modal_id} {{
    font-size: 11.5px;
    background: rgba(255,153,0,0.15);
    border: 1px solid rgba(255,153,0,0.4);
    color: #ff9900;
    padding: 3px 10px;
    border-radius: 12px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s ease;
    user-select: none;
}}
.rf-badge-btn-{rf_modal_id}:hover {{
    background: rgba(255,153,0,0.28);
    border-color: #ff9900;
    box-shadow: 0 0 12px rgba(255,153,0,0.35);
    transform: translateY(-1px);
}}
</style>
<div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 153, 0, 0.25); border-left: 4px solid #ff9900; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
        <span style="font-weight: 700; font-size: 14.5px; color: #ff9900;">⚡ Sintesi Esecutiva Quantitativa | Status Portafoglio</span>
        <label for="modal-toggle-{rf_modal_id}" class="rf-badge-btn-{rf_modal_id}" title="Clicca per aprire la Guida Metodologica al Tasso Risk-Free">
            <span>🏛️ Risk-Free {rf_currency}: {rf_rate_pct:.2f}%</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#ff9900" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-left: 2px; opacity: 0.95;">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
        </label>
    </div>
    <input type="checkbox" id="modal-toggle-{rf_modal_id}">
    <div class="modal-overlay-{rf_modal_id}">
        <label for="modal-toggle-{rf_modal_id}" class="modal-backdrop-{rf_modal_id}"></label>
        <div class="modal-content-{rf_modal_id}">
            <label for="modal-toggle-{rf_modal_id}" class="modal-close-{rf_modal_id}">&times;</label>
            <div style="font-size: 18px; font-weight: 700; color: #ff9900; margin-bottom: 16px; border-bottom: 1px solid rgba(255, 153, 0, 0.2); padding-bottom: 8px;">
                🏛️ Metodologia Tasso Risk-Free ({rf_currency}: {rf_rate_pct:.2f}%)
            </div>
            <div>{safe_rf_content}</div>
        </div>
    </div>
    <div style="font-size: 13.5px; color: #c9d1d9; line-height: 1.5;">
        Portafoglio attivo con controvalore totale di <b>€ {port_val:,.2f}</b>. 
        Conformità del <b>{comp_score:.1f}%</b> sui 6 limiti di rischio regolamentari. 
        Sharpe Ratio a <b>{sharpe_val:.2f}</b> (hurdle rate Rf: <b>{rf_rate_pct:.2f}%</b>) con rendimento annuo (CAGR) del <b>{cagr_val:.2f}%</b> e VaR 95% al <b>{var_val:.2f}%</b>.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("#### 💼 Riepilogo Portafoglio")
col1, col2, col3 = st.columns(3)
with col1:
    port_value = ret.get("portfolio_value", 0.0)
    twr_pct = ret.get("total_return_pct", 0.0) or 0.0
    metric_card(
        "Valore Portafoglio",
        fmt_eur(port_value),
        delta=f"{twr_pct:+.2f}% TWR (Cumulato)",
        positive=(twr_pct >= 0),
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Il <b>Mark-to-Market (MtM)</b> corrente del portafoglio: controvalore monetario totale liquidabile istantaneamente delle posizioni aperte calcolato ai prezzi di chiusura o real-time più recenti.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
Si moltiplica la quantità netta di quote per ciascun asset per il prezzo di mercato corrente, convertito in Euro:
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Valore Totale</b> = &sum; (Quote Nette<sub>i</sub> &times; Prezzo<sub>i</sub> &times; Tasso FX<sub>i</sub>)
</div>
Il delta mostrato sotto (<b>TWR Cumulato</b>) rappresenta il rendimento ponderato nel tempo calcolato dalla combinazione delle quote lungo la storia del portafoglio.
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Rappresenta la dimensione patrimoniale effettiva dell'investimento. Risponde alla domanda: 'Se dovessi liquidare l'intero portafoglio ai prezzi attuali, quale capitale netto otterrei?'.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS traccia tutti gli ordini storici dal database o CSV, calcola la posizione netta per ISIN/Ticker e scarica le quotazioni in tempo reale via cache persistente con conversione FX automatica.</div>

<div><b>🔍 Come leggerlo:</b> Indica il patrimonio netto investito totale. Confrontato con il costo storico d'acquisto (<i>Cost Basis</i>), evidenzia l'apprezzamento monetario complessivo.</div>
</div>"""
    )
with col2:
    pnl_unrealized_val = ret.get("unrealized_pnl_total")
    if pnl_unrealized_val is None and not pos.empty and "unrealized_pnl" in pos.columns:
        pnl_unrealized_val = float(pos["unrealized_pnl"].sum())
    pnl_unrealized_val = pnl_unrealized_val or 0.0

    pnl_realized_val = ret.get("realized_pnl_total")
    if pnl_realized_val is None and not pos.empty and "realized_pnl" in pos.columns:
        pnl_realized_val = float(pos["realized_pnl"].sum())
    pnl_realized_val = pnl_realized_val or 0.0

    pnl_divs_val = ret.get("dividends_total")
    if pnl_divs_val is None and not pos.empty and "dividends_total" in pos.columns:
        pnl_divs_val = float(pos["dividends_total"].sum())
    pnl_divs_val = pnl_divs_val or 0.0

    tot_pnl_val = ret.get("total_pnl", pnl_unrealized_val + pnl_realized_val + pnl_divs_val)

    metric_card(
        "PnL Totale",
        fmt_eur(tot_pnl_val),
        delta=f"{ret.get('total_pnl_pct', 0)*100:+.2f}% sul Capitale",
        positive=(tot_pnl_val >= 0),
        help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Profit & Loss (Profitti e Perdite) Totale, in Euro e in percentuale sul capitale investito. Misura la ricchezza netta generata dal portafoglio dall'inizio dell'operatività.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
Somma algebrica di PnL latente, PnL realizzato sulle vendite e dividendi netti percepiti:
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>PnL Totale</b> = PnL Latente + PnL Realizzato (FIFO) + Dividendi Totali
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Quantifica il ritorno economico effettivo in Euro sul patrimonio investito, integrando sia le plusvalenze latenti che le operazioni già liquidate e i flussi cedolari.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS esegue un motore contabile a code FIFO che separa con precisione il costo medio ponderato dei lotti residui, le plusvalenze già liquidate e i dividendi storici accreditati.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>Valore Positivo (Verde):</b> Il portafoglio è in guadagno complessivo rispetto al capitale investito.<br>
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

# ── SCOMPOSIZIONE PNL A MERCATO (LIVE BREAKDOWN VISIBILE IN PAGINA) ────────
st.markdown(f"""
<div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 153, 0, 0.25); border-radius: 12px; padding: 12px 18px; margin-top: 10px; margin-bottom: 20px; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 14px;">
        <div style="font-size: 13.5px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 6px;">
            <span>📊 Scomposizione PnL Portafoglio:</span>
        </div>
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 16px; font-size: 13px;">
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(63,185,80,0.25); border-radius: 8px; padding: 5px 12px;">
                <span style="color: #8b949e;">🟢 PnL Latente (Aperte):</span>
                <b style="color: {'#3fb950' if pnl_unrealized_val >= 0 else '#f85149'}; margin-left: 6px;">€ {pnl_unrealized_val:+,.2f}</b>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 8px; padding: 5px 12px;">
                <span style="color: #8b949e;">🔵 PnL Realizzato (Chiuse):</span>
                <b style="color: {'#3fb950' if pnl_realized_val >= 0 else '#f85149'}; margin-left: 6px;">€ {pnl_realized_val:+,.2f}</b>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,215,0,0.25); border-radius: 8px; padding: 5px 12px;">
                <span style="color: #8b949e;">🟡 Cedole & Dividendi:</span>
                <b style="color: #ffd700; margin-left: 6px;">€ {pnl_divs_val:+,.2f}</b>
            </div>
            <div style="background: rgba(255,153,0,0.08); border: 1px solid rgba(255,153,0,0.4); border-radius: 8px; padding: 5px 12px;">
                <span style="color: #ff9900; font-weight: 600;">💰 PnL Netto Totale:</span>
                <b style="color: {'#3fb950' if tot_pnl_val >= 0 else '#f85149'}; margin-left: 6px;">€ {tot_pnl_val:+,.2f}</b>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("#### ⚡ Metriche di Rischio e Rendimento")
col4, col5, col6 = st.columns(3)
with col4:
    metric_card(
        "Sharpe Ratio (Ex-Post)",
        f"{ret.get('sharpe_ratio', 0) if ret.get('sharpe_ratio') else 0:.2f}",
        help_text=f"""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Rappresenta lo <b>Sharpe Ratio Storico Realizzato (Ex-Post)</b>. Misura l'extra-rendimento effettivo conseguito dal portafoglio per unità di volatilità durante la sua storia reale, tenendo conto delle date di acquisto, delle vendite e dei flussi di cassa (metodo FIFO).</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Sharpe Ratio<sub>Ex-Post</sub></b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #ffb74d; padding-bottom:1px;">R<sub>p</sub> &minus; R<sub>f</sub></span><span style="display:block; padding-top:1px;">&sigma;<sub>p</sub></span></span> &times; &radic;252
</div>
dove <i>R<sub>p</sub></i> è il rendimento medio giornaliero dei flussi reali, <i>R<sub>f</sub></i> il tasso privo di rischio giornaliero ({rf_rate_pct:.2f}% annuo) e <i>&sigma;<sub>p</sub></i> la deviazione standard giornaliera.
</div>

<div style="margin-bottom: 8px;"><b>🎯 Differenza con Markowitz (Ex-Ante):</b>
Mentre lo <b>Sharpe Ex-Post</b> misura la storia reale con i pesi variabili nel tempo, lo <b>Sharpe Markowitz</b> nella scheda Modelli Quantitativi misura l'efficienza teorica dell'allocazione attuale statica (<i>w<sup>T</sup>&mu; / &sigma;</i>).
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

<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0 8px 0; color: #ffb74d;">
  <b>💡 Perché non è la semplice differenza sull'asse Y?</b><br>
  Il Drawdown misura la <b>perdita percentuale del capitale dal picco</b>, non la sottrazione di punti percentuali.<br>
  <i>Esempio reale su 10.000 €:</i><br>
  • Il portafoglio sale a <b>+98.4%</b> valendo <b>19.840 €</b> (High-Water Mark).<br>
  • Poi scende al <b>+20.6%</b> valendo <b>12.060 €</b>.<br>
  • Sull'asse Y la linea scende di 77.8 p.p., ma la perdita reale dal picco è: <br>
  <code style="color:#ffb74d;">(12.060 € &minus; 19.840 €) / 19.840 € = &minus;39.21%</code>
</div>

<div style="margin-bottom: 8px;"><b>📐 Formula Ufficiale (GIPS / CFA):</b>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 5px 10px; border-radius: 6px; margin: 4px 0; text-align: center;">
  <b>Drawdown<sub>t</sub></b> = (Valore<sub>t</sub> &minus; HighWaterMark<sub>t</sub>) / HighWaterMark<sub>t</sub>
</div>
</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>0% a -10%:</b> Profilo a basso rischio / difensivo.<br>
• <b>-10% a -25%:</b> Profilo bilanciato / azionario moderato.<br>
• <b>< -30%:</b> Profilo ad elevata volatilità o concentrato in asset azionari/crypto.
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

c_bm, c_view, c_sel = st.columns([2.4, 1.4, 1.0])

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
        default=bm_options,
        key="multi_bm_selector_p1",
        placeholder="Aggiungi Benchmark...",
        label_visibility="collapsed"
    )
    if not selected_bms:
        selected_bms = bm_options

with c_view:
    chart_view_mode = st.selectbox(
        "Modalità Grafico",
        options=["📈 Rendimento Cumulato %", "📉 Curva di Drawdown (Underwater %)"],
        index=0,
        key="chart_view_mode_p1",
        label_visibility="collapsed"
    )

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

# Palette colori istituzionale per i benchmark
bm_colors = {
    "SPY": "#58a6ff",       # Blu Chiaro
    "QQQ": "#bc8cff",       # Viola Neon
    "ACWI": "#3fb950",      # Verde Smeraldo
    "AGG": "#8fa0ba",       # Grigio Ardesia
    "GLD": "#d29922",       # Oro
    "BTC": "#f0883e"        # Arancio Cripto
}

fig = go.Figure()

if "Drawdown" in chart_view_mode:
    # ── MODALITÀ UNDERWATER PLOT (CURVA DI DRAWDOWN) ──
    cum_p_raw = (1 + sr_p_sub).cumprod()
    roll_max_p = cum_p_raw.cummax()
    dd_port = ((cum_p_raw - roll_max_p) / roll_max_p) * 100.0

    # Benchmark Underwater curves
    for bm_str in selected_bms:
        bm_code = bm_str.split(" ")[0]
        sr_bm_raw = load_benchmark_returns(bm_code, df_prices_ref, sr_port.index)
        sr_bm_sub = sr_bm_raw.reindex(sr_p_sub.index).fillna(0.0)
        cum_bm_raw = (1 + sr_bm_sub).cumprod()
        roll_max_bm = cum_bm_raw.cummax()
        dd_bm_i = ((cum_bm_raw - roll_max_bm) / roll_max_bm) * 100.0
        b_color = bm_colors.get(bm_code, "#8fa0ba")

        fig.add_trace(go.Scatter(
            x=date_x, y=dd_bm_i.values,
            name=f"Drawdown {bm_code}",
            line=dict(color=b_color, width=1.5, dash="dash"),
            hovertemplate=f"<b>Data: %{{x|%d %b %Y}}</b><br>📉 Drawdown {bm_code}: %{{y:.2f}}%<extra></extra>"
        ))

    # Portafoglio Underwater Area
    fig.add_trace(go.Scatter(
        x=date_x, y=dd_port.values,
        name="Drawdown Portafoglio ARGUS",
        fill="tozeroy",
        fillcolor="rgba(248, 81, 73, 0.12)",
        line=dict(color="#f85149", width=2.6),
        hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>🔴 Drawdown Portafoglio: %{y:.2f}%<extra></extra>"
    ))

    # Annotazione Max Drawdown nel punto di minimo esatto
    if not dd_port.empty:
        min_dd_idx = dd_port.idxmin()
        min_dd_val = dd_port.min()
        fig.add_annotation(
            x=pd.to_datetime(min_dd_idx), y=min_dd_val,
            text=f"📉 Max Drawdown: {min_dd_val:.2f}%",
            showarrow=True, arrowhead=2, arrowcolor="#f85149",
            ax=0, ay=35,
            font=dict(size=11, color="#f85149"),
            bgcolor="rgba(22, 27, 34, 0.90)", bordercolor="#f85149", borderwidth=1
        )

    fig.update_layout(
        xaxis_title=None,
        height=480,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        yaxis=dict(
            type="linear",
            title="Drawdown dal Massimo (%)",
            ticksuffix="%",
            range=[min(dd_port.min() * 1.15, -10.0), 2.0] if not dd_port.empty else [-50, 0],
            gridcolor="rgba(255,255,255,0.06)"
        ),
        xaxis=dict(
            type="date",
            range=[date_x.min(), date_x.max()] if len(date_x) > 0 else None,
            gridcolor="rgba(255,255,255,0.06)"
        )
    )

else:
    # ── MODALITÀ RENDIMENTO CUMULATO STANDARD ──

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

    # Trace Portafoglio ARGUS
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

with st.expander("💡 Guida Rapida: Perché il Max Drawdown non coincide con la differenza sull'asse Y?", expanded=False):
    st.markdown("""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 6px;">📌 Differenza tra 'Differenza in Punti Percentuali' e 'Drawdown Reale'</div>
  <div>
    Nel grafico di <b>Rendimento Cumulato</b> (asse Y indicizzato a base 0%), l'occhio tende a misurare la distanza verticale sottraendo i valori (es. un calo dal <code>+98.4%</code> al <code>+20.6%</code> sembra una caduta di <code>77.8%</code>).
    Tuttavia, il <b>Max Drawdown</b> misura la <b>perdita percentuale di ricchezza subita rispetto al picco massimo (High-Water Mark)</b>:
  </div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 8px 12px; border-radius: 6px; margin: 8px 0; color: #ffb74d;">
    <b>Esempio con Capitale di 10.000 €:</b><br>
    1. Al picco (<code>+98.4%</code>), il portafoglio vale <b>19.840 €</b> (High-Water Mark).<br>
    2. Al minimo successivo (<code>+20.6%</code>), il portafoglio vale <b>12.060 €</b>.<br>
    3. Il capitale perso è <code>12.060 € &minus; 19.840 € = &minus;7.780 €</code>.<br>
    4. <b>Max Drawdown = &minus;7.780 € / 19.840 € = &minus;39.21%</b>.<br>
    Hai perso il <b>39.2% del patrimonio massimo raggiunto</b>, non il 77%!
  </div>
  <div>
    💡 <i>Suggerimento:</i> Seleziona la vista <b>'📉 Curva di Drawdown (Underwater %)'</b> dal menu a tendina sopra il grafico per visualizzare la profondità reale di ogni flessione rispetto al pelo dell'acqua (0%).
  </div>
</div>
""", unsafe_allow_html=True)

# ── SCORECARD COMPARATIVA MULTI-BENCHMARK (FEATURE 5) ─────────────
if selected_bms:
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
        "Rendimento Tot": f"{p_tot_ret:+.2f}%",
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
            "Rendimento Tot": f"{bm_tot_ret:+.2f}%",
            "CAGR Annuo": f"{bm_cagr:+.2f}%",
            "Volatilità Annua": f"{bm_vol:.2f}%",
            "Sharpe Ratio": f"{bm_sharpe:.2f}",
            "Max Drawdown": f"{bm_dd:.2f}%",
            "Alpha vs Portafoglio": f"{alpha_delta:+.2f}%"
        })

    df_scorecard = pd.DataFrame(scorecard_rows)
    col_sc_h1, col_sc_h2 = st.columns([3.8, 1.0])
    with col_sc_h1:
        st.markdown("#### 🏆 Scorecard Comparativa Multi-Benchmark")
    with col_sc_h2:
        csv_sc = df_scorecard.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica CSV", data=csv_sc, file_name="benchmark_scorecard.csv", mime="text/csv", use_container_width=True, key="btn_download_bm_scorecard")

    sc_cfg = {
        "Asset / Benchmark": st.column_config.TextColumn("Asset / Benchmark", width="medium"),
        "Rendimento Tot": st.column_config.TextColumn("Rendimento Tot", width="small"),
        "CAGR Annuo": st.column_config.TextColumn("CAGR Annuo", width="small"),
        "Volatilità Annua": st.column_config.TextColumn("Volatilità Annua", width="small"),
        "Sharpe Ratio": st.column_config.TextColumn("Sharpe Ratio", width="small"),
        "Max Drawdown": st.column_config.TextColumn("Max Drawdown", width="small"),
        "Alpha vs Portafoglio": st.column_config.TextColumn("Alpha vs Portafoglio", width="medium")
    }
    st.dataframe(
        df_scorecard,
        column_config=sc_cfg,
        use_container_width=True,
        hide_index=True
    )
    st.markdown('<div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)

# ── VISTA ANALITICA AGGREGATA DUCKDB (OLAP ACCELERATION) ──────────
if not pos.empty:
    st.markdown("---")
    st.markdown("#### ⚡ Vista Analitica Aggregata DuckDB (Cubo OLAP Multi-Dimensionale)")
    st.caption("Aggregazione colonnare ad alta performance per Asset Class × Settore GICS × Valuta con scomposizione gerarchica del rischio e rendimento.")
    from core.ui_utils import render_duckdb_olap_cube_widget
    render_duckdb_olap_cube_widget(pos, key_prefix="p1_dash")
    st.markdown("---")

# ── ANALISI DI EFFICIENZA, RISCHIO & PERFORMANCE ATTIVA (BENTO & MODAL) ──
col_head_m1, col_head_m2 = st.columns([3.2, 1.2])

with col_head_m1:
    st.markdown("#### 🏛️ Analisi di Efficienza, Rischio & Performance Attiva")
    st.caption("Valutazione quantitativa dell'efficienza di gestione, asimmetria dei rendimenti e decomposizione dell'Alpha vs Benchmark.")

with col_head_m2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("📚 Glossario Completo Metriche di Rendimento & Efficienza", f"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. ALPHA DI JENSEN -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏅 1. Alpha di Jensen (Extra-Rendimento Attivo CAPM)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Misura la componente di extra-rendimento puro generata dal portafoglio rispetto a quanto atteso in base al modello CAPM e al rischio sistematico di mercato (Beta).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>&alpha;</b> = R<sub>p</sub> &minus; [ R<sub>f</sub> + &beta; &times; (R<sub>b</sub> &minus; R<sub>f</sub>) ]
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Identificare la reale abilità (<i>Skill</i>) di selezione dei titoli e di allocazione del capitale, isolandola dall'andamento generale del mercato.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Confronta il CAGR del portafoglio con il CAGR del benchmark prescelto (es. SPY), depurato dall'effetto Beta e dal tasso privo di rischio al {rf_rate_pct:.2f}%.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>&alpha; > 0:</b> Sovraperformance attiva (creazione reale di valore aggiunto).<br>
    • <b>&alpha; = 0:</b> Rendimento perfettamente allineato al rischio assunto.<br>
    • <b>&alpha; < 0:</b> Sottoperformance rispetto al benchmark di riferimento.
  </div>
</div>

<!-- 2. SHARPE RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,215,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ffd700; font-size: 15px; font-weight: 700; margin-bottom: 6px;">⚖️ 2. Sharpe Ratio (Efficienza Rischio Totale Ex-Post)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> L'indicatore universale di efficienza finanziaria. Quantifica il premio al rendimento ottenuto per ogni unità di volatilità complessiva assunta.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,215,0,0.08); border-left: 3px solid #ffd700; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffe082; text-align: center; font-size: 13px;">
      <b>Sharpe Ratio</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>totale</sub> &times; &radic;252
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Capire se i rendimenti del portafoglio sono una reale ricompensa per il rischio o se dipendono da oscillazioni eccessive e insostenibili.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato sulla serie storica dei rendimenti logaritmici giornalieri netti rispetto al Risk-Free rate ({rf_rate_pct:.2f}% annuo) e riscalato su base annua con &radic;252.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 0.50:</b> Efficienza debole (rischio eccessivo rispetto al rendimento).<br>
    • <b>0.50 – 0.99:</b> Efficienza moderata / standard di mercato.<br>
    • <b>1.00 – 1.99:</b> Ottima efficienza (standard di gestione istituzionale).<br>
    • <b>&ge; 2.00:</b> Profilo d'eccellenza assoluta.
  </div>
</div>

<!-- 3. SORTINO RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,255,153,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #00ff99; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🛡️ 3. Sortino Ratio (Efficienza sul Rischio di Perdita)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Variante evoluta dello Sharpe Ratio. Penalizza unicamente la volatilità negativa (<i>Downside Deviation</i>), considerando le oscillazioni rialziste come elemento favorevole.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,255,153,0.08); border-left: 3px solid #00ff99; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00ff99; text-align: center; font-size: 13px;">
      <b>Sortino Ratio</b> = (R<sub>p</sub> &minus; R<sub>f</sub>) / &sigma;<sub>downside</sub> &times; &radic;252
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Valutare con precisione strategie asimmetriche (Growth, ETF tematici, opzioni) dove la volatilità al rialzo non deve essere punita.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Isola i rendimenti giornalieri inferiori al tasso privo di rischio ({rf_rate_pct:.2f}%/252), calcola la deviazione standard quadratica dei soli ribassi e riscala su base annua con &radic;252.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 1.0:</b> Protezione dai ribassi debole o rendimento insufficiente.<br>
    • <b>1.0 – 2.0:</b> Ottimo profilo asimmetrico (buona difesa nelle correzioni).<br>
    • <b>> 2.0:</b> Profilo d'eccellenza con perdite minime nei mercati orso.
  </div>
</div>

<!-- 4. CALMAR RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🌊 4. Calmar Ratio (Rendimento / Massimo Drawdown)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Rapporto diretto tra il tasso di crescita annuo composto (CAGR) e la peggiore flessione percentuale storica registrata dal portafoglio (<i>Maximum Drawdown</i>).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #58a6ff; text-align: center; font-size: 13px;">
      <b>Calmar Ratio</b> = CAGR / |Max Drawdown|
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

<!-- 5. INFORMATION RATIO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(188,140,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #bc8cff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🎯 5. Information Ratio (Costanza dell'Alpha)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Rapporto tra l'extra-rendimento medio generato rispetto al benchmark e il <i>Tracking Error</i> (la volatilità della differenza dei rendimenti).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(188,140,255,0.08); border-left: 3px solid #bc8cff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #bc8cff; text-align: center; font-size: 13px;">
      <b>Information Ratio</b> = Media(R<sub>p</sub> &minus; R<sub>b</sub>) / Tracking Error &times; &radic;252
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

<!-- 6. CAGR & RENDIMENTO CUMULATO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,243,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 4px;">
  <div style="color: #00f3ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📈 6. CAGR & Rendimento Totale Cumulato</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Il CAGR (<i>Compound Annual Growth Rate</i>) è il tasso di crescita annuo costante equivalente che porterebbe il capitale iniziale al valore finale nell'orizzonte considerato.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,243,255,0.08); border-left: 3px solid #00f3ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #80d8ff; text-align: center; font-size: 13px;">
      <b>CAGR</b> = ( V<sub>finale</sub> / V<sub>iniziale</sub> )<sup>(1 / Anni)</sup> &minus; 1
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Standardizzare la performance su base annua, consentendo il confronto omogeneo tra portafogli con durate storiche differenti.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato sul time-weighted value del portafoglio tenendo conto del numero esatto di anni trascorsi dalla prima operazione.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 5.0%:</b> Rendimento moderato (rischio erosione inflattiva).<br>
    • <b>7.0% – 12.0%:</b> Rendimento azionario solido a lungo termine.<br>
    • <b>> 15.0%:</b> Crescita del capitale di fascia alta.
  </div>
</div>

</div>
""", button_label="📖 Apri Glossario & Formule")

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

s_val = float(sharpe_num) if sharpe_num is not None else 0.0
so_val = float(sortino_num) if sortino_num is not None else 0.0
c_val = float(calmar_num) if calmar_num is not None else 0.0
a_val = float(alpha_num) if alpha_num is not None else 0.0
ir_val = float(ir_num) if ir_num is not None else 0.0

# 1. Top Bento Matrix (4 Quick Intelligence KPI Cards)
b_col1, b_col2, b_col3, b_col4 = st.columns(4)

with b_col1:
    alpha_bg = "rgba(0, 230, 118, 0.12)" if a_val >= 0 else "rgba(248, 81, 73, 0.12)"
    alpha_border = "#00e676" if a_val >= 0 else "#f85149"
    alpha_tag = "🟢 Extra-Rendimento" if a_val >= 0 else "🔴 Sottoperformance"
    st.markdown(f"""
    <div style="background: {alpha_bg}; border: 1px solid {alpha_border}; border-radius: 10px; padding: 12px 14px; min-height: 108px;">
        <div style="font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Alpha di Jensen (CAPM)</div>
        <div style="font-size: 22px; font-weight: 800; color: {alpha_border}; margin: 2px 0;">{_fmt_metric_val(alpha_num, is_pct=True)}</div>
        <div style="font-size: 11px; color: #c9d1d9;">{alpha_tag} vs Benchmark</div>
    </div>
    """, unsafe_allow_html=True)

with b_col2:
    s_color = "#00e676" if s_val >= 1.0 else ("#ff9900" if s_val >= 0.5 else "#f85149")
    s_tag = "🟢 Elevato (≥1.0)" if s_val >= 1.0 else ("🟡 Moderato (0.5-1.0)" if s_val >= 0.5 else "🔴 Basso (<0.5)")
    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 153, 0, 0.3); border-radius: 10px; padding: 12px 14px; min-height: 108px;">
        <div style="font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Sharpe Ratio (Ex-Post)</div>
        <div style="font-size: 22px; font-weight: 800; color: {s_color}; margin: 2px 0;">{_fmt_metric_val(sharpe_num)}</div>
        <div style="font-size: 11px; color: #c9d1d9;">Efficienza: {s_tag}</div>
    </div>
    """, unsafe_allow_html=True)

with b_col3:
    so_color = "#00e676" if so_val >= 1.0 else ("#ff9900" if so_val >= 0.5 else "#f85149")
    asym_note = "🛡️ Difesa Ribassi Superiore" if so_val > s_val + 0.05 else "⚖️ Volatilità Simmetrica"
    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(0, 243, 255, 0.3); border-radius: 10px; padding: 12px 14px; min-height: 108px;">
        <div style="font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Sortino Ratio (Downside)</div>
        <div style="font-size: 22px; font-weight: 800; color: #00f3ff; margin: 2px 0;">{_fmt_metric_val(sortino_num)}</div>
        <div style="font-size: 11px; color: #c9d1d9;">{asym_note}</div>
    </div>
    """, unsafe_allow_html=True)

with b_col4:
    c_color = "#00e676" if c_val >= 0.5 else ("#ff9900" if c_val >= 0.3 else "#f85149")
    c_tag = "🟢 Resiliente (≥0.5)" if c_val >= 0.5 else "🟡 Recupero Moderato"
    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(188, 140, 255, 0.3); border-radius: 10px; padding: 12px 14px; min-height: 108px;">
        <div style="font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Calmar Ratio (CAGR/MaxDD)</div>
        <div style="font-size: 22px; font-weight: 800; color: #bc8cff; margin: 2px 0;">{_fmt_metric_val(calmar_num)}</div>
        <div style="font-size: 11px; color: #c9d1d9;">Resilienza: {c_tag}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="margin-bottom: 14px;"></div>', unsafe_allow_html=True)

# 2. Main Content Grid (Tabella Analitica Affiancata al Barometro Visivo)
col_t1, col_t2 = st.columns([1.35, 1.0])

with col_t1:
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
        "Target / Benchmark Istituzionale": [
            "🟢 Solido (> 7.0%)" if (cagr_num or 0) >= 7.0 else "🟡 Moderato",
            f"Storico reale transazioni ({float(n_yrs_val):.1f} anni)",
            "🟢 Creazione Valore (> 0%)" if (alpha_num or 0) > 0 else "🔴 Sottoperformance",
            "Soglia Ottimale ≥ 1.00",
            "Soglia Ottimale ≥ 1.00",
            "Soglia Ottimale ≥ 0.50",
            "Soglia Ottimale ≥ 0.50",
            "Periodo attivo portafoglio"
        ]
    }
    st.dataframe(pd.DataFrame(data_ret), use_container_width=True, hide_index=True)
    
with col_t2:
    # Mini Barometro Visivo Plotly delle Metriche di Efficienza
    metrics_names = ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio", "Info Ratio"]
    metrics_vals = [s_val, so_val, c_val, ir_val]
    bar_colors = [
        "#00e676" if s_val >= 1.0 else ("#ff9900" if s_val >= 0.5 else "#f85149"),
        "#00f3ff" if so_val >= 1.0 else ("#58a6ff" if so_val >= 0.5 else "#f85149"),
        "#bc8cff" if c_val >= 0.5 else "#ff9900",
        "#00e676" if ir_val >= 0.5 else ("#ff9900" if ir_val >= 0 else "#f85149")
    ]
    
    fig_barometer = go.Figure()
    fig_barometer.add_trace(go.Bar(
        x=metrics_vals,
        y=metrics_names,
        orientation='h',
        marker=dict(color=bar_colors, line=dict(color="rgba(255,255,255,0.2)", width=1)),
        text=[f"{v:.2f}" for v in metrics_vals],
        textposition="auto",
        textfont=dict(color="#ffffff", size=11, family="Roboto, monospace"),
        hovertemplate="<b>%{y}</b>: %{x:.2f}<extra></extra>"
    ))
    
    fig_barometer.update_layout(
        title=dict(text="🎯 Barometro Efficienza vs Soglie Target", font=dict(size=13, color="#ffffff")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(22, 27, 34, 0.4)",
        margin=dict(l=10, r=15, t=32, b=10),
        height=280,
        xaxis=dict(
            title=dict(text="Valore Coefficiente", font=dict(size=10, color="#8b949e")),
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.2)",
            tickfont=dict(size=10, color="#8b949e")
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=11, color="#c9d1d9")
        )
    )
    st.plotly_chart(fig_barometer, use_container_width=True, config={"displayModeBar": False}, key="perf_barometer_chart")

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
                <div style="background: rgba(255,255,255,0.03); border-left: 4px solid {border_c}; padding: 12px; border-radius: 6px; margin-bottom: 6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#ffffff;">{badge_icon} {diag['title']}</span>
                        <span style="font-size:10px; padding: 2px 8px; border-radius:10px; background:rgba(255,255,255,0.1); color:#8b949e;">{diag['category']}</span>
                    </div>
                    <div style="font-size:13px; color:#c9d1d9; margin-top:6px;">{diag['description']}</div>
                    <div style="font-size:12px; color:#3fb950; font-weight:600; margin-top:4px;">👉 Raccomandazione: {diag['actionable_recommendation']}</div>
                </div>
                """, unsafe_allow_html=True)
                target_page = diag.get("page_target")
                if target_page:
                    st.page_link(
                        target_page,
                        label=diag.get("page_label", "Apri Sezione Dedicata"),
                        icon=diag.get("page_icon", "🔬")
                    )
                    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

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
    col_rl_h1, col_rl_h2 = st.columns([3.5, 0.9])
    with col_rl_h2:
        csv_eval = df_eval.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica CSV", data=csv_eval, file_name="risk_compliance_limits.csv", mime="text/csv", use_container_width=True)

    df_eval_show = df_eval[["status_icon", "rule_name", "current_value", "limit_threshold", "unit"]].rename(columns={
        "status_icon": "Stato",
        "rule_name": "Regola di Rischio",
        "current_value": "Valore Rilevato",
        "limit_threshold": "Soglia Limite",
        "unit": "Unità"
    })
    eval_cfg = {
        "Stato": st.column_config.TextColumn("Stato", width="small"),
        "Regola di Rischio": st.column_config.TextColumn("Regola di Rischio", width="medium"),
        "Valore Rilevato": st.column_config.TextColumn("Valore Rilevato", width="small"),
        "Soglia Limite": st.column_config.TextColumn("Soglia Limite", width="small"),
        "Unità": st.column_config.TextColumn("Unità", width="small")
    }
    st.dataframe(
        df_eval_show,
        column_config=eval_cfg,
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
    if hasattr(fig_sunburst.data[0], "marker") and getattr(fig_sunburst.data[0].marker, "colors", None) is not None:
        colors_arr = np.asarray(fig_sunburst.data[0].marker.colors, dtype=float)
        fig_sunburst.data[0].customdata = np.column_stack([
            [f"{c:+.2f}%" if not np.isnan(c) else "0.00%" for c in colors_arr]
        ])

    fig_sunburst.update_traces(
        textinfo="label+percent root",
        insidetextorientation="horizontal",
        leaf_opacity=0.92,
        marker=dict(line=dict(color="#0d1117", width=1.5)),
        hovertemplate="<b>%{label}</b><br>💰 Controvalore: € %{value:,.2f}<br>📊 Quota Portafoglio: %{percentRoot:.1%}<br>📈 PnL Latente: %{customdata[0]}<extra></extra>"
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
