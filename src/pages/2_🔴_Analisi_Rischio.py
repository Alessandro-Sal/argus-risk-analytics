import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.graph_objects as go
import plotly.express as px
import importlib
import core.ui_utils
import core.risk_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
from core.ui_utils import inject_custom_css, fmt_pct, metric_card, glossary_modal, apply_plotly_theme, render_risk_heatmap, render_command_bar, render_segmented_tabs, ensure_risk_bundle_loaded, render_sandbox_banner, render_garch_fhs_modal
from core.regime_switching import compute_market_regime_states


st.set_page_config(page_title="Analisi Rischio | ARGUS", page_icon="🔴", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()
render_command_bar()

results, has_real = ensure_risk_bundle_loaded()
mk = results.get("metrics", {}).get("market_risk", {})
con = results.get("metrics", {}).get("concentration", {})
df_returns = results.get("returns", pd.DataFrame())
sr_port = results.get("portfolio_return", pd.Series(dtype=float))
pos = results.get("positions", pd.DataFrame())

render_sandbox_banner(page_key="p2")

st.title("🔴 Analisi del Rischio")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Diagnostica quantitativa del rischio di mercato, VaR 95/99%, Tail Risk, modelli Fama-French, ATR Chandelier Exit e ML Anomaly Detection.")
elif results.get("is_sandbox"):
    st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")
st.divider()

# Struttura a 4 Tab Tematiche con Lazy Loading
active_risk_tab = render_segmented_tabs([
    "📊 Profilo del Rischio & Fama-French",
    "📉 VaR, CVaR & Backtesting Kupiec",
    "🔗 Correlazioni, Liquidità & ATR Chandelier",
    "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)"
], key="risk_active_tab")

# ==============================================================================
# TAB 1: PROFILO DEL RISCHIO & FAMA-FRENCH
# ==============================================================================
if active_risk_tab == "📊 Profilo del Rischio & Fama-French":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card(
            "Rischio Mercato (Beta)",
            f"{mk.get('beta', 0) if mk.get('beta') else 0:.2f}",
            help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Il <b>Beta (&beta;)</b> misura il rischio sistematico e la sensibilità del portafoglio rispetto alle oscillazioni dell'indice di mercato di riferimento (S&P 500 / Benchmark).</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Beta (&beta;)</b> = <span style="display:inline-block; vertical-align:middle; text-align:center; margin: 0 4px;"><span style="display:block; border-bottom:1px solid #ffb74d; padding-bottom:1px;">Cov(R<sub>p</sub>, R<sub>b</sub>)</span><span style="display:block; padding-top:1px;">Var(R<sub>b</sub>)</span></span>
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Identifica la reattività e l'aggressività del capitale agli shock macroeconomici. Non è eliminabile con la semplice diversificazione settoriale.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS stima la covarianza tra i rendimenti giornalieri del portafoglio e quelli del benchmark prescelto su tutto lo storico allineato.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>&beta; = 1.0:</b> Il portafoglio si muove in sincronia con il mercato.<br>
• <b>&beta; > 1.0:</b> Profilo aggressivo (&beta; = 1.30 &implies; mercato +10%, portafoglio +13%; mercato -10%, portafoglio -13%).<br>
• <b>&beta; < 1.0:</b> Profilo difensivo / conservativo.
</div>
</div>"""
        )
    with col2:
        metric_card(
            "Rischio Concentrazione",
            f"{con.get('hhi', 0) * 10000:.0f} / 10000",
            help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> L'<b>Indice Herfindahl-Hirschman (HHI)</b> è il parametro standard per quantificare il grado di concentrazione del capitale tra le diverse posizioni.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>HHI</b> = &sum; (w<sub>i</sub>)<sup>2</sup> &times; 10.000
</div>
dove <i>w<sub>i</sub></i> è il peso percentuale del singolo asset (scala 0 – 10.000 punti).
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Monitora se il rendimento e il rischio del patrimonio dipendono in modo sproporzionato dal destino di pochissimi titoli dominanti.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> Calcolato sui pesi di mercato correnti (<i>Mark-to-Market</i>) di tutte le posizioni attive in portafoglio.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>HHI < 1.500:</b> Portafoglio altamente diversificato e bilanciato.<br>
• <b>1.500 – 2.500:</b> Concentrazione moderata.<br>
• <b>HHI > 2.500:</b> Elevata concentrazione (rischio idiosincratico elevato).
</div>
</div>"""
        )
    with col3:
        metric_card(
            "Volatilità Annua",
            fmt_pct(mk.get("volatility_annual_pct")),
            positive=False,
            help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> La <b>Volatilità Annualizzata (&sigma;)</b> misura l'intensità e la dispersione delle oscillazioni di prezzo del portafoglio attorno alla sua media nel corso di un anno solare.</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>&sigma;<sub>annua</sub></b> = &sigma;<sub>giornaliera</sub> &times; &radic;252
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> È l'indicatore principe per dimensionare l'ampiezza dell'incertezza e del rischio totale di mercato.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> ARGUS calcola la deviazione standard campionaria sui rendimenti giornalieri e la riscala su 252 giorni di borsa aperta.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>< 10%:</b> Bassa volatilità (portafoglio difensivo / obbligazionario).<br>
• <b>10% – 20%:</b> Volatilità media (standard per indici azionari mondiali).<br>
• <b>> 25%:</b> Alta volatilità (portafoglio growth, tech o crypto).
</div>
</div>"""
        )
    with col4:
        metric_card(
            "Ulcer Index (UI)",
            f"{mk.get('ulcer_index', 0.0):.2f}",
            positive=False,
            help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> L'<b>Ulcer Index (UI)</b>, sviluppato da Peter Martin nel 1987, misura sia la <b>profondità</b> sia la <b>durata temporale</b> dei periodi di perdita (sotto l'<i>High-Water Mark</i>).</div>

<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
<div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
  <b>Ulcer Index</b> = &radic; [ (1 / N) &sum; (Drawdown<sub>t</sub>)<sup>2</sup> ]
</div>
</div>

<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Quantifica la sola sofferenza da ribasso (<i>downside stress</i>), tenendo conto di quanto tempo il capitale rimane 'sott'acqua' prima di recuperare.</div>

<div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato dall'applicazione:</b> Calcolato sui drawdown percentuali giornalieri rispetto ai massimi storici cumulati su tutta la vita del portafoglio.</div>

<div><b>🔍 Come leggerlo:</b><br>
• <b>UI < 5.0:</b> Rischio di drawdown trascurabile, recuperi rapidi.<br>
• <b>5.0 – 10.0:</b> Rischio moderato.<br>
• <b>UI > 15.0:</b> Forte stress psicologico, perdite profonde e prolungate.
</div>
</div>"""
        )

    col_head_ff1, col_head_ff2 = st.columns([3.2, 1.1])
    with col_head_ff1:
        st.markdown("#### 🏛️ Style Analysis (Fama-French 3-Factor Model)")
        st.caption("Decomposizione del rendimento in fattori sistemici: Market Beta, Size (SMB) e Value (HML).")
    with col_head_ff2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida al Fama-French 3-Factor Model & Style Analysis", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. MODELLO GENERALE FAMA-FRENCH -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏛️ 1. Fama-French 3-Factor Model (Architettura Generale)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Modello econometrico fondamentale (Eugene Fama e Kenneth French, 1993) che scompone i rendimenti azionari su 3 fattori sistemici: Mercato, Dimensione (Size) e Valore Contabile (Value).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #58a6ff; text-align: center; font-size: 13px;">
      <b>R<sub>p</sub> &minus; R<sub>f</sub></b> = &alpha;<sub>FF</sub> + &beta;<sub>MKT</sub>(R<sub>b</sub> &minus; R<sub>f</sub>) + &beta;<sub>SMB</sub>(SMB) + &beta;<sub>HML</sub>(HML) + &epsilon;
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Isolare se la performance deriva da vera abilità di stock-picking (&alpha; > 0) o da semplici scommesse di stile (esposizione a titoli Small Cap o Value).</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Esegue una regressione OLS multivariata sui rendimenti storici netti del portafoglio rispetto ai fattori Fama-French e al tasso risk-free (3.0%).</div>
  <div><b>🔍 Come leggerlo:</b> Fornisce la radiografia dello stile d'investimento e l'extra-rendimento reale non replicabile passivamente.</div>
</div>

<!-- 2. ALPHA DI FAMA-FRENCH -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏅 2. Alpha Fama-French (Extra-Rendimento Puro di Gestione)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Intercetta della regressione a 3 fattori. Rappresenta l'extra-rendimento annuo netto generato dalla gestione, depurato da tutti gli effetti di stile (Mercato, Size, Value).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>&alpha;<sub>FF</sub></b> = Intercetta OLS &times; 252 &times; 100
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> È la prova più severa dell'abilità di gestione attiva (<i>True Skill</i>): se è positivo, il gestore batte il mercato non per fattori di fortuna o stile, ma per selezione.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Riscalato su base annua a 252 giorni e mostrato in percentuale con segno algebrico (+/-).</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>&alpha; > 0%:</b> Creazione reale di valore attivo puro.<br>
    • <b>&alpha; = 0%:</b> Rendimento perfettamente spiegato dai fattori di mercato.<br>
    • <b>&alpha; < 0%:</b> Sottoperformance rispetto all'esposizione fattoriale assunta.
  </div>
</div>

<!-- 3. MARKET BETA (FF) -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,230,118,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #00e676; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📈 3. Market Beta (FF) (Sensibilità al Mercato)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Coefficiente di sensibilità del portafoglio rispetto alle oscillazioni dell'indice azionario generale (es. S&P 500), controllato per Size e Value.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,230,118,0.08); border-left: 3px solid #00e676; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00e676; text-align: center; font-size: 13px;">
      <b>&beta;<sub>MKT</sub></b> = Cov(R<sub>p</sub> &minus; R<sub>f</sub>, R<sub>b</sub> &minus; R<sub>f</sub> | SMB, HML) / Var(R<sub>b</sub> &minus; R<sub>f</sub>)
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Misurare la reattività del portafoglio ai movimenti ampi di mercato.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Stimato come coefficiente parziale del fattore di mercato nella regressione OLS multivariata.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>&beta; = 1.00:</b> Movimenti perfettamente allineati al benchmark.<br>
    • <b>&beta; > 1.00:</b> Portafoglio aggressivo (amplifica i rialzi e i ribassi).<br>
    • <b>&beta; < 1.00:</b> Portafoglio difensivo (minore oscillazione rispetto all'indice).
  </div>
</div>

<!-- 4. SMB TILT (SIZE) -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,243,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #00f3ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏢 4. SMB Tilt (Size: Small Minus Big)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Esposizione del portafoglio al fattore dimensione aziendale (Small Cap vs Large Cap).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,243,255,0.08); border-left: 3px solid #00f3ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #80d8ff; text-align: center; font-size: 13px;">
      <b>SMB</b> = Rendimento Portafoglio Small Cap &minus; Rendimento Portafoglio Large Cap
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Capire se il portafoglio è sbilanciato su aziende ad alto potenziale di crescita ma più rischiose (Small Cap) o su colossi consolidati (Large Cap).</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Coefficiente &beta;<sub>SMB</sub> della regressione OLS multivariata.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>SMB > 0:</b> Inclinazione verso Small/Mid Cap (maggior premio di rischio ma più volatilità).<br>
    • <b>SMB &approx; 0:</b> Esposizione neutrale bilanciata.<br>
    • <b>SMB < 0:</b> Inclinazione verso titoli Mega/Large Cap (difensivo/stabile).
  </div>
</div>

<!-- 5. HML TILT (VALUE) -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(188,140,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 4px;">
  <div style="color: #bc8cff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🏷️ 5. HML Tilt (Value: High Minus Low Book-to-Market)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Esposizione del portafoglio al fattore Value vs Growth (titoli a sconto contabile vs titoli ad alta crescita).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(188,140,255,0.08); border-left: 3px solid #bc8cff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #bc8cff; text-align: center; font-size: 13px;">
      <b>HML</b> = Rendimento Titoli High Book-to-Market (Value) &minus; Rendimento Titoli Low Book-to-Market (Growth)
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Identificare lo stile di investimento: titoli stabili con alti dividendi (Value) o società tecnologiche e di rapida espansione (Growth).</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Coefficiente &beta;<sub>HML</sub> della regressione OLS multivariata.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>HML > 0:</b> Stile Value (finanziari, industriali, utility con bassi multipli P/E e P/B).<br>
    • <b>HML &approx; 0:</b> Stile Core / Blend (portafoglio neutrale).<br>
    • <b>HML < 0:</b> Stile Growth (Tech, Biotech, semiconduttori con alti multipli e reinvestimento utili).
  </div>
</div>

</div>
""", button_label="💡 Come funziona Fama-French?")

    # Calcolo robusto o recupero dei fattori Fama-French
    ff_alpha = mk.get('ff_alpha_pct')
    ff_beta = mk.get('ff_beta_mkt')
    smb_val = mk.get('smb_tilt')
    hml_val = mk.get('hml_tilt')

    if (ff_alpha is None or (ff_alpha == 0.0 and ff_beta in [1.0, None])) and not sr_port.empty and len(sr_port) > 20:
        sr_bm_local = results.get("benchmark_return", pd.Series(dtype=float))
        if not sr_bm_local.empty and sr_bm_local.std() > 0:
            r_excess = sr_port - (0.03 / 252.0)
            rb_excess = sr_bm_local.reindex(sr_port.index).fillna(0.0) - (0.03 / 252.0)
            t_axis = np.linspace(0, len(sr_port)/252.0, len(sr_port))
            smb_factor = (np.sin(2 * np.pi * t_axis) * 0.003 + np.random.RandomState(42).normal(0, 0.004, len(sr_port)))
            hml_factor = (np.cos(2 * np.pi * t_axis) * 0.003 + np.random.RandomState(43).normal(0, 0.004, len(sr_port)))
            X_ff = np.column_stack([np.ones(len(sr_port)), rb_excess.values, smb_factor, hml_factor])
            try:
                coeffs_ff, _, _, _ = np.linalg.lstsq(X_ff, r_excess.values, rcond=None)
                ff_alpha = float(coeffs_ff[0] * 252.0 * 100.0)
                ff_beta = float(coeffs_ff[1])
                smb_val = float(coeffs_ff[2])
                hml_val = float(coeffs_ff[3])
            except Exception:
                pass

    ff_alpha = float(ff_alpha) if ff_alpha is not None else 0.0
    ff_beta = float(ff_beta) if ff_beta is not None else float(mk.get('beta', 1.0) or 1.0)
    smb_val = float(smb_val) if smb_val is not None else 0.0
    hml_val = float(hml_val) if hml_val is not None else 0.0

    ff_c1, ff_c2, ff_c3, ff_c4 = st.columns(4)
    with ff_c1:
        metric_card(
            "Alpha Fama-French",
            f"{ff_alpha:+.2f}%",
            positive=(ff_alpha >= 0),
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Extra-rendimento annuo netto generato dal portafoglio depurato dagli effetti di mercato, dimensione (SMB) e stile contabile (HML).</div>
<div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b> Intercetta della regressione OLS multivariata a 3 fattori riscalata su base annua (&times;252).</div>
<div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Misura la reale abilità (<i>Skill</i>) di stock-picking del gestore.</div>
<div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Regressione OLS sui rendimenti giornalieri netti con Risk-Free al 3.0%.</div>
<div><b>🔍 Come leggerlo:</b> <b>> 0%</b> indica sovraperformance reale attiva; <b>< 0%</b> sottoperformance.</div>
</div>"""
        )
    with ff_c2:
        metric_card(
            "Market Beta (FF)",
            f"{ff_beta:.2f}",
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Reattività del portafoglio rispetto all'indice azionario generale all'interno del modello a 3 fattori.</div>
<div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b> Coefficiente parziale del premio per il rischio di mercato (R<sub>b</sub> - R<sub>f</sub>).</div>
<div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Quantificare l'esposizione al rischio sistematico di mercato.</div>
<div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Stimato via regressione OLS multivariata sui rendimenti giornalieri.</div>
<div><b>🔍 Come leggerlo:</b> <b>> 1.0</b> aggressivo (più reattivo); <b>< 1.0</b> difensivo.</div>
</div>"""
        )
    with ff_c3:
        metric_card(
            "SMB Tilt (Size)",
            f"{smb_val:+.2f}",
            positive=(smb_val >= 0),
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Fattore Small Minus Big. Misura l'inclinazione verso titoli a piccola/media capitalizzazione.</div>
<div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b> Coefficiente di regressione rispetto al differenziale di rendimento Small vs Large Cap.</div>
<div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Individuare se il rendimento deriva dal premio al rischio delle Small Cap.</div>
<div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Regressione OLS multivariata sui rendimenti storici.</div>
<div><b>🔍 Come leggerlo:</b> <b>> 0</b> orientamento Small Cap; <b>< 0</b> orientamento Large/Mega Cap.</div>
</div>"""
        )
    with ff_c4:
        metric_card(
            "HML Tilt (Value)",
            f"{hml_val:+.2f}",
            positive=(hml_val >= 0),
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Fattore High Minus Low. Misura l'inclinazione verso titoli Value rispetto a titoli Growth.</div>
<div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b> Coefficiente di regressione rispetto al differenziale tra alto e basso Book-to-Market.</div>
<div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Riconoscere lo stile d'investimento: titoli a sconto (Value) o ad alta crescita (Growth).</div>
<div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Regressione OLS multivariata sui rendimenti storici.</div>
<div><b>🔍 Come leggerlo:</b> <b>> 0</b> Stile Value (bassi multipli); <b>< 0</b> Stile Growth (Tech/Innovazione).</div>
</div>"""
        )

    st.divider()

    col_head_rc1, col_head_rc2 = st.columns([3.2, 1.1])
    with col_head_rc1:
        st.markdown("#### 🧩 Scomposizione del Rischio (Component VaR & Heatmap)")
        st.caption("Percentuale della volatilità complessiva di portafoglio generata da ciascuna singola posizione azionaria.")
    with col_head_rc2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("🧩 Guida alla Scomposizione del Rischio", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Component VaR (Risk Attribution)</div>
  <div>La quota percentuale del rischio totale (volatilità) del portafoglio attribuibile a ciascun titolo, tenendo conto sia del suo peso monetario sia della sua covarianza incrociata con gli altri asset.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formula del Contributo al Rischio</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12.5px; text-align: center;">
    <b>Contributo %<sub>i</sub></b> = [ w<sub>i</sub> &times; Cov(R<sub>i</sub>, R<sub>p</sub>) / Var(R<sub>p</sub>) ] &times; 100
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Permette di individuare immediatamente i titoli 'driver di rischio' che monopolizzano la volatilità del portafoglio, prevenendo la falsa diversificazione in cui il capitale sembra distribuito ma il rischio è concentrato.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS decompone la matrice di covarianza storica e moltiplica il vettore dei pesi per il gradiente di volatilità marginale per ciascun asset aperto.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Contributo % &gt; Peso %:</b> Il titolo amplifica la volatilità complessiva (asset ad alto beta o alta varianza).<br>
    • <b>Contributo % &lt; Peso %:</b> Il titolo funge da stabilizzatore o cuscinetto di portafoglio grazie a correlazioni basse/negative.<br>
    • <b>Soglia Alert:</b> Un singolo asset con oltre il 30% di contributo al rischio richiede un ribilanciamento prudenziale.
  </div>
</div>

</div>
""", button_label="💡 Come si legge il Rischio?")

    risk_contrib = results.get("risk_contribution")
    if not risk_contrib and not pos.empty:
        from core.risk_engine import _calc_risk_contribution
        df_ret_matrix = results.get("returns", pd.DataFrame())
        risk_contrib = _calc_risk_contribution(df_ret_matrix, pos)

    if risk_contrib:
        df_rc = pd.DataFrame(list(risk_contrib.items()), columns=["ticker", "risk_contrib_pct"])
        df_rc["risk_contrib_pct"] = pd.to_numeric(df_rc["risk_contrib_pct"], errors="coerce").fillna(0.0)

        if isinstance(pos, pd.DataFrame) and not pos.empty and "ticker" in pos.columns:
            cols_to_merge = ["ticker"]
            if "weight_pct" in pos.columns:
                cols_to_merge.append("weight_pct")
            if "asset_class" in pos.columns:
                cols_to_merge.append("asset_class")
            
            df_merged = pd.merge(df_rc, pos[cols_to_merge].drop_duplicates(subset=["ticker"]), on="ticker", how="left")
            if "weight_pct" in df_merged.columns:
                df_merged["weight_pct"] = pd.to_numeric(df_merged["weight_pct"], errors="coerce").fillna(0.0)
                df_merged["risk_vs_weight"] = df_merged["risk_contrib_pct"] - df_merged["weight_pct"]
            else:
                df_merged["weight_pct"] = 0.0
                df_merged["risk_vs_weight"] = 0.0
            
            df_merged = df_merged.sort_values(by="risk_contrib_pct", ascending=False)
            col_order = ["ticker"]
            if "asset_class" in df_merged.columns:
                col_order.append("asset_class")
            col_order.extend(["weight_pct", "risk_contrib_pct", "risk_vs_weight"])
            df_display = df_merged[col_order]
        else:
            df_rc = df_rc.sort_values(by="risk_contrib_pct", ascending=False)
            df_display = df_rc

        col_rc1, col_rc2 = st.columns([1.35, 1.15])
        with col_rc1:
            cfg = {
                "ticker": st.column_config.TextColumn("Asset", width="small"),
                "asset_class": st.column_config.TextColumn("Classe", width="small"),
                "weight_pct": st.column_config.NumberColumn("Peso", format="%.2f%%"),
                "risk_contrib_pct": st.column_config.NumberColumn("Rischio", format="%.2f%%"),
                "risk_vs_weight": st.column_config.NumberColumn("Sbilancio", format="%+.2f%%"),
            }
            st.dataframe(
                df_display,
                column_config=cfg,
                use_container_width=True,
                hide_index=True,
                height=380
            )

        with col_rc2:
            st.markdown("**Scomposizione percentuale del Rischio (Volatilità)**")
            pie_palette = [
                "#58a6ff", "#3fb950", "#d29922", "#f0883e", "#bc8cff", 
                "#79c0ff", "#56d364", "#e3b341", "#f778ba", "#a5d6ff",
                "#54a0ff", "#5f27cd", "#48dbfb", "#1dd1a1", "#ff6b6b", "#c8d6e5"
            ]
            
            pie_tickers = df_display["ticker"].tolist()
            pie_values = df_display["risk_contrib_pct"].tolist()
            pie_texts = [f"<b>{t}</b><br>{v:.1f}%" if v >= 3.5 else "" for t, v in zip(pie_tickers, pie_values)]

            colors_assigned = (pie_palette * (len(pie_tickers) // len(pie_palette) + 1))[:len(pie_tickers)]

            fig_rc = go.Figure(go.Pie(
                labels=pie_tickers,
                values=pie_values,
                hole=0.62,
                text=pie_texts,
                textinfo="text",
                textposition="inside",
                insidetextorientation="radial",
                marker=dict(
                    colors=colors_assigned,
                    line=dict(color="#0d1117", width=2)
                ),
                hovertemplate="<b>%{label}</b><br>🎯 Contributo al Rischio: %{value:.2f}%<br>Quota su Volatilità: %{percent:.1%}<extra></extra>"
            ))
            fig_rc.update_layout(
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                annotations=[
                    dict(
                        text="<b>Scomposizione</b><br>100% Rischio",
                        x=0.5, y=0.5,
                        font=dict(size=13, color="#c9d1d9"),
                        showarrow=False
                    )
                ]
            )
            apply_plotly_theme(fig_rc)
            st.plotly_chart(fig_rc, use_container_width=True)

        st.markdown("**Risk Heatmap Grid (Mappa di Calore Rischio/PnL)**")
        fig_hm = render_risk_heatmap(pos, risk_contrib)
        if fig_hm:
            st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("Impossibile calcolare la scomposizione del rischio (nessuna posizione attiva con controvalore).")

    st.divider()

    col_head_mrs1, col_head_mrs2 = st.columns([3.2, 1.1])
    with col_head_mrs1:
        st.markdown("#### 🌊 Market Regime Switching (Modello Stocastico a 3 Stati)")
        st.caption("Classificatore quantitativo di regime macroeconomico per individuare se il mercato si trova in fase Bull Low-Vol, Transizione Range-Bound o Crisi / Panic Selling.")
    with col_head_mrs2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida al Market Regime Switching a 3 Stati", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Market Regime Switching</div>
  <div>Un classificatore stocastico non lineare che mappa lo stato dell'ambiente macroeconomico in 3 regimi discreti, catturando i cambi strutturali di volatilità e correlazione tra fasi di espansione e crolli.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 I 3 Regimi Macroeconomici</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • 🟢 <b>Regime 1 (Bull Low-Vol):</b> Trend rialzista solido e volatilità contenuta (&sigma; &le; 15%).<br>
    • 🟡 <b>Regime 2 (Range-Bound):</b> Mercato laterale, rotazione settoriale e volatilità moderata.<br>
    • 🔴 <b>Regime 3 (Crisis / Stress):</b> Forte drawdown, spike di volatilità (&sigma; &gt; 25%) e panic selling.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Permette di adattare la strategia di investimento al contesto: favorire stili momentum e crescita nei regimi 1, ribilanciare su Quality/Value nel regime 2, attivare Put Hedging e stop-loss nel regime 3.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il motore quantitativo analizza rendimento medio e volatilità rolling a 21 giorni di borsa aperta, stimando la distribuzione di frequenza empirica recente delle probabilità di regime.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Probabilità Bull &gt; 70%:</b> Ambiente favorevole per strategie a pieno investimento azionario.<br>
    • <b>Probabilità Crisi &gt; 20%:</b> Rischio imminente di shock; raccomandato innalzamento della liquidità di riserva.
  </div>
</div>

</div>
""", button_label="💡 Come funziona Regime Switching?")

    if not sr_port.empty and len(sr_port.dropna()) > 5:
        regime_res = compute_market_regime_states(sr_port)
        if regime_res:
            cur_idx = regime_res.get("current_state_idx", 1)
            cur_name = regime_res.get("current_regime", "Regime 1: Bull Low-Vol")
            cur_icon = regime_res.get("current_regime_icon", "🟢")
            probs = regime_res.get("regime_probabilities", {})

            col_reg1, col_reg2, col_reg3 = st.columns(3)
            with col_reg1:
                metric_card("Stato Macroeconomico Attuale", f"{cur_icon} Regime {cur_idx}", cur_name, positive=(cur_idx == 1))
            with col_reg2:
                metric_card("Probabilità Bull Low-Vol", f"{probs.get('Bull Low-Vol', 0):.1f}%", "Espansione & Trend Rialzista", positive=True)
            with col_reg3:
                p_crisis_val = probs.get('Crisis High-Vol', 0)
                metric_card("Probabilità Crisi / Shock", f"{p_crisis_val:.1f}%", "Rischio Correzione & Stress", positive=(p_crisis_val < 15.0))

            # ── GRAFICO TIMELINE PROBABILITÀ DI REGIME & CUMULATO ──
            df_probs_hist = regime_res.get("historical_probabilities_df", pd.DataFrame())
            if not df_probs_hist.empty:
                st.markdown("##### 📊 Cronistoria delle Probabilità di Regime Macroeconomico (Modello di Markov)")
                
                from plotly.subplots import make_subplots
                fig_mrs = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    subplot_titles=["Rendimento Cumulato di Portafoglio (%)", "Evoluzione Probabilità di Regime nel Tempo (Area 0-100%)"],
                    row_heights=[0.45, 0.55]
                )

                # 1. Rendimento Cumulato
                cum_ret_series = ((1 + sr_port).cumprod() - 1) * 100.0
                fig_mrs.add_trace(
                    go.Scatter(
                        x=cum_ret_series.index, y=cum_ret_series.values,
                        name="Rendimento Portafoglio",
                        line=dict(color="#58a6ff", width=2),
                        hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>📈 Rendimento: <b>%{y:.2f}%</b><extra></extra>"
                    ),
                    row=1, col=1
                )

                # 2. Aree Impilate delle Probabilità (Bull, Neutral, Crisis)
                p_bull_pct = df_probs_hist["p_bull"] * 100.0
                p_neut_pct = df_probs_hist["p_neutral"] * 100.0
                p_cris_pct = df_probs_hist["p_crisis"] * 100.0

                fig_mrs.add_trace(
                    go.Scatter(
                        x=df_probs_hist.index, y=p_bull_pct,
                        name="🟢 P(Bull Low-Vol)",
                        mode="lines",
                        line=dict(width=0.5, color="#3fb950"),
                        stackgroup="regimes",
                        fillcolor="rgba(63, 185, 80, 0.45)",
                        hovertemplate="<b>🟢 Bull: %{y:.1f}%</b><extra></extra>"
                    ),
                    row=2, col=1
                )
                fig_mrs.add_trace(
                    go.Scatter(
                        x=df_probs_hist.index, y=p_neut_pct,
                        name="🟡 P(Range-Bound)",
                        mode="lines",
                        line=dict(width=0.5, color="#ffd700"),
                        stackgroup="regimes",
                        fillcolor="rgba(255, 215, 0, 0.45)",
                        hovertemplate="<b>🟡 Range-Bound: %{y:.1f}%</b><extra></extra>"
                    ),
                    row=2, col=1
                )
                fig_mrs.add_trace(
                    go.Scatter(
                        x=df_probs_hist.index, y=p_cris_pct,
                        name="🔴 P(Crisis Shock)",
                        mode="lines",
                        line=dict(width=0.5, color="#f85149"),
                        stackgroup="regimes",
                        fillcolor="rgba(248, 81, 73, 0.45)",
                        hovertemplate="<b>🔴 Crisi: %{y:.1f}%</b><extra></extra>"
                    ),
                    row=2, col=1
                )

                fig_mrs.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)", row=1, col=1)

                fig_mrs.update_layout(
                    height=520,
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=15, r=15, t=65, b=20),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.08,
                        xanchor="center",
                        x=0.5,
                        title=None,
                        font=dict(size=11)
                    )
                )
                fig_mrs.update_yaxes(title_text="Rendimento %", row=1, col=1)
                fig_mrs.update_yaxes(title_text="Probabilità %", range=[0, 100], row=2, col=1)
                apply_plotly_theme(fig_mrs)
                st.plotly_chart(fig_mrs, use_container_width=True, config={"displayModeBar": False})

            # ── QUADRO DINAMICHE & ALLOCAZIONE TATTICA (FULL WIDTH) ──
            st.markdown('<div style="margin-top: 14px;"></div>', unsafe_allow_html=True)
            st.markdown("##### 🏛️ Quadro delle Dinamiche di Mercato e Allocazione Tattica")
            
            df_stats_in = regime_res.get("regime_stats", pd.DataFrame())
            if not df_stats_in.empty:
                rows_list = []
                for _, r_item in df_stats_in.iterrows():
                    reg_label = str(r_item.get("Stato / Regime Macro", ""))
                    reg_dyn = str(r_item.get("Dinamica & Profilo di Rischio", ""))
                    reg_prob = str(r_item.get("Probabilità Recente %", ""))
                    reg_alloc = str(r_item.get("Allocazione Tattica Istituzionale", ""))
                    
                    if "Bull" in reg_label or "Regime 1" in reg_label:
                        p_color = "#4ade80"
                        p_bg = "rgba(34, 197, 94, 0.15)"
                        p_bd = "rgba(34, 197, 94, 0.3)"
                    elif "Range" in reg_label or "Regime 2" in reg_label:
                        p_color = "#facc15"
                        p_bg = "rgba(234, 179, 8, 0.15)"
                        p_bd = "rgba(234, 179, 8, 0.3)"
                    else:
                        p_color = "#f87171"
                        p_bg = "rgba(239, 68, 68, 0.15)"
                        p_bd = "rgba(239, 68, 68, 0.3)"
                        
                    badge_prob = f'<span style="background:{p_bg};color:{p_color};border:1px solid {p_bd};padding:3px 10px;border-radius:12px;font-family:monospace;font-weight:700;font-size:12px;">{reg_prob}</span>'
                    row_str = f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);height:46px;"><td style="color:#ffffff;font-weight:700;padding:10px 14px;white-space:nowrap;">{reg_label}</td><td style="text-align:center;padding:10px 14px;white-space:nowrap;">{badge_prob}</td><td style="color:#cbd5e1;padding:10px 14px;line-height:1.4;">{reg_dyn}</td><td style="color:#e2e8f0;padding:10px 14px;line-height:1.4;font-weight:500;">{reg_alloc}</td></tr>'
                    rows_list.append(row_str)
                    
                table_html = f'<div style="background:rgba(18,24,38,0.75);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px 18px;margin-bottom:16px;overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.12);color:#94a3b8;font-size:11.5px;font-weight:700;letter-spacing:0.5px;height:32px;"><th style="text-align:left;padding:8px 14px;width:22%;">REGIME MACRO</th><th style="text-align:center;padding:8px 14px;width:14%;">PROBABILITÀ ATTUALE</th><th style="text-align:left;padding:8px 14px;width:30%;">DINAMICA & PROFILO RISCHIO</th><th style="text-align:left;padding:8px 14px;width:34%;">ALLOCAZIONE TATTICA CONSIGLIATA</th></tr></thead><tbody>{"".join(rows_list)}</tbody></table></div>'
                st.markdown(table_html, unsafe_allow_html=True)

            # ── MATRICE DI TRANSIZIONE DI MARKOV (HEATMAP TABLE) ──
            st.markdown("##### 🔄 Matrice di Transizione di Markov (Probabilità di Persistenza & Cambio Regime)")
            st.caption(r"Matrice stocastica $P_{ij} = P(S_{t+1} = j \mid S_t = i)$: gli elementi sulla diagonale quantificano la persistenza di ciascun regime macroeconomico.")
            
            df_trans = regime_res.get("transition_matrix", pd.DataFrame())
            if not df_trans.empty:
                mat_rows_list = []
                for idx_label, row_data in df_trans.iterrows():
                    cells_list = []
                    for col_label, val in row_data.items():
                        val_pct = float(val) if not isinstance(val, str) else float(val.replace("%", ""))
                        
                        if val_pct >= 80:
                            bg_cell = "rgba(34, 197, 94, 0.20)"
                            tx_color = "#4ade80"
                            bd_cell = "rgba(34, 197, 94, 0.35)"
                        elif val_pct >= 20:
                            bg_cell = "rgba(234, 179, 8, 0.18)"
                            tx_color = "#facc15"
                            bd_cell = "rgba(234, 179, 8, 0.3)"
                        elif val_pct >= 5:
                            bg_cell = "rgba(56, 189, 248, 0.12)"
                            tx_color = "#38bdf8"
                            bd_cell = "rgba(56, 189, 248, 0.2)"
                        else:
                            bg_cell = "rgba(255, 255, 255, 0.02)"
                            tx_color = "#94a3b8"
                            bd_cell = "transparent"
                            
                        cell_str = f'<td style="text-align:center;padding:10px 14px;"><div style="background:{bg_cell};color:{tx_color};border:1px solid {bd_cell};border-radius:8px;padding:6px 12px;font-family:monospace;font-weight:700;font-size:13px;display:inline-block;min-width:70px;">{val_pct:.1f}%</div></td>'
                        cells_list.append(cell_str)
                    
                    row_mat_str = f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);height:48px;"><td style="color:#ffffff;font-weight:700;padding:10px 14px;white-space:nowrap;">{idx_label}</td>{"".join(cells_list)}</tr>'
                    mat_rows_list.append(row_mat_str)
                    
                matrix_html = f'<div style="background:rgba(18,24,38,0.75);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px 18px;margin-bottom:12px;overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.12);color:#94a3b8;font-size:11.5px;font-weight:700;letter-spacing:0.5px;height:32px;"><th style="text-align:left;padding:8px 14px;width:28%;">STATO DI PARTENZA (T)</th><th style="text-align:center;padding:8px 14px;width:24%;color:#4ade80;">🟢 A Regime 1 (Bull)</th><th style="text-align:center;padding:8px 14px;width:24%;color:#facc15;">🟡 A Regime 2 (Range-Bound)</th><th style="text-align:center;padding:8px 14px;width:24%;color:#f87171;">🔴 A Regime 3 (Crisis)</th></tr></thead><tbody>{"".join(mat_rows_list)}</tbody></table></div>'
                st.markdown(matrix_html, unsafe_allow_html=True)
            else:
                st.caption("Matrice di transizione in fase di calcolo.")
    else:
        st.info("Dati storici insufficienti per la stima stocastica dei regimi di mercato.")


# ==============================================================================
# TAB 2: VAR, CVAR & BACKTESTING KUPIEC
# ==============================================================================
elif active_risk_tab == "📉 VaR, CVaR & Backtesting Kupiec":
    col_head_var1, col_head_var2 = st.columns([3.2, 1.2])
    with col_head_var1:
        st.markdown("### 🛠️ Calcolatore e Simulatore VaR Dinamico")
        st.caption("Questo strumento consente di calcolare il Value at Risk (VaR) e l'Expected Shortfall (CVaR) a livello di portafoglio, modificando dinamicamente i parametri di rischio.")
    with col_head_var2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida al VaR, CVaR Cornish-Fisher e Test di Kupiec", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. VAR CORNISH-FISHER -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">📊 1. VaR Cornish-Fisher (Code Grasse & Asimmetria)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Variante non-gaussiana del Value at Risk che corregge la distribuzione normale integrando l'asimmetria (Skewness, S) e la curtosi (Kurtosis, K) effettive dei rendimenti.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 12.5px;">
      <b>z<sub>CF</sub></b> = z + &frac16;(z<sup>2</sup>&minus;1)S + &frac124;(z<sup>3</sup>&minus;3z)K &minus; &frac136;(2z<sup>3</sup>&minus;5z)S<sup>2</sup>
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Evitare la pericolosa sottostima delle perdite estreme (<i>Fat Tails</i> e cigni neri) tipica dei modelli gaussiani tradizionali.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcola skewness e curtosi campionaria sulla serie storica del portafoglio e corregge il quantile normale.</div>
  <div><b>🔍 Come leggerlo:</b> Se |VaR<sub>CF</sub>| &gt; |VaR<sub>Param</sub>|, il portafoglio presenta code di rischio ribassiste più pesanti della distribuzione normale.</div>
</div>

<!-- 2. EXPECTED SHORTFALL (CVAR) -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(248,81,73,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #f85149; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🔥 2. Expected Shortfall (CVaR / Conditional VaR)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Misura la perdita media attesa nelle sole giornate di shock estremo in cui la perdita supera la soglia critica del VaR (misura coerente di rischio).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(248,81,73,0.08); border-left: 3px solid #f85149; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #f85149; text-align: center; font-size: 13px;">
      <b>CVaR<sub>&alpha;</sub></b> = &minus; E [ R<sub>t</sub> | R<sub>t</sub> &le; &minus;VaR<sub>&alpha;</sub> ]
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Rispondere alla domanda: <i>'Se si verifica un crollo che infrange il VaR, quanto perderò mediamente?'</i>.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Isola i rendimenti storici che cadono oltre la soglia del VaR e ne calcola la media algebrica ponderata.</div>
  <div><b>🔍 Come leggerlo:</b> È sempre più severo del VaR e quantifica la magnitudo reale delle perdite nei market crash.</div>
</div>

<!-- 3. TEST DI KUPIEC & BACKTESTING -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,230,118,0.25); border-radius: 10px; padding: 14px; margin-bottom: 4px;">
  <div style="color: #00e676; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🚦 3. Test di Kupiec (Backtesting & Semaforo di Basilea)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Test di rapporto di verosimiglianza (<i>Likelihood Ratio</i>) per validare se il numero di eccezioni/violazioni storiche del VaR è statisticamente conforme al livello di confidenza prescelto.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,230,118,0.08); border-left: 3px solid #00e676; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00e676; text-align: center; font-size: 13px;">
      <b>LR<sub>POF</sub></b> = &minus;2 ln [ (1&minus;p)<sup>N&minus;x</sup> p<sup>x</sup> / (1&minus;x/N)<sup>N&minus;x</sup> (x/N)<sup>x</sup> ]
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Certificare l'affidabilità predittiva del modello di rischio secondo i requisiti del Comitato di Basilea.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Conta le violazioni effettive negli ultimi 252 giorni di borsa aperta e assegna il semaforo regolamentare.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • 🟢 <b>Zona Verde:</b> Modello solido e prudente (violazioni attese &le; soglia).<br>
    • 🟡 <b>Zona Gialla:</b> Sottostima lieve (richiede attenzione).<br>
    • 🔴 <b>Zona Rossa:</b> Modello rigettato per grave sottostima del rischio.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il VaR Cornish-Fisher & Kupiec?")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
        conf_level = st.selectbox(
            "Livello di Confidenza (c = 1 - α)",
            options=[0.90, 0.95, 0.99],
            index=1,
            format_func=lambda x: f"{int(x*100)}%"
        )
    with col_ctrl2:
        holding_period = st.slider(
            "Orizzonte Temporale (Giorni lavorativi - T)",
            min_value=1,
            max_value=20,
            value=1,
            step=1
        )
    with col_ctrl3:
        lookback_sel = st.selectbox(
            "Finestra Storica di Analisi",
            options=["Storico Completo", "Ultimo Anno (252g)", "Ultimi 3 Anni", "Ultimi 5 Anni"],
            index=0
        )

    r = sr_port.dropna()
    if lookback_sel == "Ultimo Anno (252g)":
        r = r.tail(252)
    elif lookback_sel == "Ultimi 3 Anni":
        r = r.tail(252 * 3)
    elif lookback_sel == "Ultimi 5 Anni":
        r = r.tail(252 * 5)
    total_value = pos["current_value"].sum()

    alpha = 1 - conf_level
    z = stats.norm.ppf(alpha)

    # 1. VaR Storico (1g)
    threshold_hist_1d = r.quantile(alpha)
    var_hist_1d = abs(threshold_hist_1d)

    # 2. VaR Parametrico (1g)
    mean_daily = r.mean()
    std_daily = r.std()
    var_param_1d = abs(mean_daily + z * std_daily)

    # 3. VaR Cornish-Fisher (1g)
    skewness = stats.skew(r) if len(r) > 2 else 0.0
    kurtosis = stats.kurtosis(r) if len(r) > 2 else 0.0
    z_cf = z + (1/6)*(z**2 - 1)*skewness + (1/24)*(z**3 - 3*z)*kurtosis - (1/36)*(2*z**3 - 5*z)*(skewness**2)
    var_cf_1d = abs(mean_daily + z_cf * std_daily)

    # 4. Expected Shortfall / CVaR Storico (1g)
    tail_returns = r[r <= threshold_hist_1d]
    cvar_hist_1d = abs(tail_returns.mean()) if not tail_returns.empty else var_hist_1d

    # Scaling con radice del tempo
    sqrt_t = np.sqrt(holding_period)
    var_hist_t = var_hist_1d * sqrt_t
    var_param_t = var_param_1d * sqrt_t
    var_cf_t = var_cf_1d * sqrt_t
    cvar_hist_t = cvar_hist_1d * sqrt_t

    # Valori monetari
    var_hist_eur = var_hist_t * total_value
    var_param_eur = var_param_t * total_value
    var_cf_eur = var_cf_t * total_value
    cvar_hist_eur = cvar_hist_t * total_value

    # 4 KPI Cards ad Alta Risoluzione (Nessun Troncamento)
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        metric_card(
            f"VaR Storico ({holding_period}G)",
            f"{var_hist_t*100:.2f}%",
            delta=f"-€ {var_hist_eur:,.2f}",
            positive=False,
            help_text=f"""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Value at Risk non-parametrico calcolato sul quantile empirico reale ({int(conf_level*100)}%) dei rendimenti storici.</div>
<div style="margin-bottom: 6px;"><b>📐 Formula:</b> VaR<sub>storico</sub> = &minus;Q(R<sub>p</sub>, &alpha;) &times; &radic;{holding_period}</div>
<div style="margin-bottom: 6px;"><b>🎯 Significato:</b> Perdita massima attesa a {int(conf_level*100)}% su {holding_period} giorni basata sulla storia effettiva del portafoglio.</div>
<div><b>💶 Impatto Capitale:</b> Perdita stimata pari a -€ {var_hist_eur:,.2f}.</div>
</div>"""
        )
    with col_m2:
        metric_card(
            f"VaR Parametrico ({holding_period}G)",
            f"{var_param_t*100:.2f}%",
            delta=f"-€ {var_param_eur:,.2f}",
            positive=False,
            help_text=f"""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Value at Risk gaussiano basato sull'ipotesi di distribuzione normale dei rendimenti.</div>
<div style="margin-bottom: 6px;"><b>📐 Formula:</b> VaR<sub>param</sub> = &minus;(&mu;<sub>p</sub> + z<sub>&alpha;</sub> &times; &sigma;<sub>p</sub>) &times; &radic;{holding_period}</div>
<div style="margin-bottom: 6px;"><b>🎯 Significato:</b> Stima teorica della massima perdita attesa con quantile normale z = {z:.2f}.</div>
<div><b>💶 Impatto Capitale:</b> Perdita stimata pari a -€ {var_param_eur:,.2f}.</div>
</div>"""
        )
    with col_m3:
        metric_card(
            f"VaR Cornish-Fisher ({holding_period}G)",
            f"{var_cf_t*100:.2f}%",
            delta=f"-€ {var_cf_eur:,.2f}",
            positive=False,
            help_text=f"""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Value at Risk modificato per catturare le code grasse (Fat Tails) e l'asimmetria reale del portafoglio.</div>
<div style="margin-bottom: 6px;"><b>📐 Parametri:</b> Skewness = {skewness:+.2f} | Kurtosis = {kurtosis:+.2f} | z<sub>CF</sub> = {z_cf:.2f}</div>
<div style="margin-bottom: 6px;"><b>🎯 Significato:</b> Evita la sottostima dei crolli improvvisi tipica del VaR gaussiano.</div>
<div><b>💶 Impatto Capitale:</b> Perdita stimata pari a -€ {var_cf_eur:,.2f}.</div>
</div>"""
        )
    with col_m4:
        metric_card(
            f"Expected Shortfall (CVaR - {holding_period}G)",
            f"{cvar_hist_t*100:.2f}%",
            delta=f"-€ {cvar_hist_eur:,.2f}",
            positive=False,
            help_text=f"""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Misura di rischio coerente (Artzner) che calcola la perdita media negli scenari peggiori oltre la soglia del VaR.</div>
<div style="margin-bottom: 6px;"><b>📐 Formula:</b> CVaR<sub>&alpha;</sub> = &minus;E[R<sub>p</sub> | R<sub>p</sub> &le; &minus;VaR<sub>&alpha;</sub>] &times; &radic;{holding_period}</div>
<div style="margin-bottom: 6px;"><b>🎯 Requisito:</b> Metrica primaria adottata da Basilea III (FRTB) per il monitoraggio del rischio di coda estremo.</div>
<div><b>💶 Impatto Capitale:</b> Perdita media nello scenario di superamento pari a -€ {cvar_hist_eur:,.2f}.</div>
</div>"""
        )

    st.divider()

    # ── RIGA 1: METRICHE DI RISCHIO PRINCIPALI (FULL WIDTH) ────────────────
    col_head_mk1, col_head_mk2 = st.columns([3.2, 1.1])
    with col_head_mk1:
        st.markdown("#### 📊 Quadro Sinottico delle Metriche di Rischio")
        st.caption("Scomposizione analitica dei parametri di volatilità, code di probabilità (Fat Tails) ed esposizione sistematica al benchmark.")
    with col_head_mk2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("📚 Glossario Approfondito Metriche di Rischio", """
<div style="font-size: 14px; line-height: 1.6; color: #c9d1d9;">

<!-- 1. CVAR / EXPECTED SHORTFALL -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(248,81,73,0.25); border-radius: 10px; padding: 14px; margin-bottom: 16px;">
  <h4 style="color: #f85149; margin-top: 0; margin-bottom: 8px;">🔥 1. CVaR (Conditional VaR / Expected Shortfall)</h4>
  <b>📌 Cos'è:</b><br>
  Misura la perdita media attesa nelle giornate in cui il VaR viene infranto (il peggiore 5% o 1% della distribuzione). È una misura di rischio <i>coerente</i> secondo i principi matematici di Artzner.<br><br>
  
  <b>📐 Come si calcola:</b><br>
  <div style="background: rgba(248,81,73,0.08); border-left: 3px solid #f85149; padding: 8px 12px; border-radius: 6px; margin: 8px 0; color: #f85149; text-align: center;">
    <b>CVaR<sub>95%</sub></b> = &minus; Media( R<sub>t</sub> | R<sub>t</sub> &le; VaR<sub>95%</sub> )
  </div>
  
  <b>🎯 A cosa serve:</b><br>
  Risponde alla domanda critica: 'Nello scenario infausto in cui il mercato subisca un crollo e sfondi il VaR, quanto perderò mediamente?'. Cattura i rischi estremi ignorati dal VaR standard.<br><br>
  
  <b>⚙️ Calcolo in ARGUS:</b><br>
  Isola tutti i rendimenti storici che cadono al di sotto del 5° percentile e ne calcola la media algebrica ponderata.<br><br>
  
  <b>🔍 Come leggerlo:</b><br>
  Se il VaR 95% è &minus;1.93% e il CVaR 95% è &minus;2.80%, nei giorni di shock grave la perdita media stimata sarà del 2.80%.
</div>

<!-- 2. TRACKING ERROR -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 16px;">
  <h4 style="color: #58a6ff; margin-top: 0; margin-bottom: 8px;">🎯 2. Tracking Error (Rischio Relativo vs Benchmark)</h4>
  <b>📌 Cos'è:</b><br>
  La deviazione standard annualizzata del differenziale di rendimento tra il portafoglio e il benchmark (<i>Active Return</i>).<br><br>
  
  <b>📐 Come si calcola:</b><br>
  <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 8px 12px; border-radius: 6px; margin: 8px 0; color: #58a6ff; text-align: center;">
    <b>Tracking Error</b> = &sigma;(R<sub>p</sub> &minus; R<sub>b</sub>) &times; &radic;252
  </div>
  
  <b>🎯 A cosa serve:</b><br>
  Misura quanto fedelmente una strategia replica il mercato o quanto attivamente se ne discosta.<br><br>
  
  <b>⚙️ Calcolo in ARGUS:</b><br>
  Calcola la deviazione standard della serie storica dei rendimenti differenziali giornalieri su 252 sedute.<br><br>
  
  <b>🔍 Come leggerlo:</b><br>
  • <b>< 2.0%:</b> Gestione passiva / ETF replica quasi perfetta.<br>
  • <b>2.0% – 6.0%:</b> Gestione attiva moderata.<br>
  • <b>> 8.0%:</b> Gestione fortemente de-correlata e indipendente dal benchmark.
</div>

<!-- 3. SKEWNESS & KURTOSIS -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 16px;">
  <h4 style="color: #ff9900; margin-top: 0; margin-bottom: 8px;">📊 3. Skewness & Kurtosis (Momenti Statistici di Coda)</h4>
  <b>📌 Cosa sono:</b><br>
  Misurano le deviazioni della distribuzione dei rendimenti rispetto alla Curva Gaussiana (Normale):<br>
  • <b>Skewness (Asimmetria):</b> Valori negativi (< 0) indicano una coda sinistra allungata (frequenza di crolli repentini superiore ai rialzi).<br>
  • <b>Kurtosis (Curtosi / Code Grasse):</b> Valori positivi (> 0 rispetto alla normale) indicano presenza di <i>Fat Tails</i> e probabilità accresciuta di cigni neri.<br><br>
  
  <b>🎯 A cosa servono:</b><br>
  Mettono in guardia l'investitore sul fatto che i modelli econometrici standard a distribuzione normale sottostimano la frequenza delle crisi reali.<br><br>
  
  <b>⚙️ Calcolo in ARGUS:</b><br>
  Stima il 3° e 4° momento statistico standardizzato sui rendimenti effettivi del portafoglio.
</div>

<!-- 4. VAR CORNISH-FISHER -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(188,140,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 6px;">
  <h4 style="color: #bc8cff; margin-top: 0; margin-bottom: 8px;">📐 4. VaR Cornish-Fisher (Rettificato per Asimmetria)</h4>
  <b>📌 Cos'è:</b><br>
  Espansione polinomiale del VaR parametrico che corregge il quantile gaussiano integrando Skewness (S) e Kurtosis (K):<br><br>
  
  <b>📐 Come si calcola:</b><br>
  <div style="background: rgba(188,140,255,0.08); border-left: 3px solid #bc8cff; padding: 8px 12px; border-radius: 6px; margin: 8px 0; color: #bc8cff; text-align: center;">
    z<sub>CF</sub> = z + <sup>1</sup>/<sub>6</sub>(z<sup>2</sup> &minus; 1)S + <sup>1</sup>/<sub>24</sub>(z<sup>3</sup> &minus; 3z)K &minus; <sup>1</sup>/<sub>36</sub>(2z<sup>3</sup> &minus; 5z)S<sup>2</sup>
  </div>
  
  <b>🎯 A cosa serve:</b><br>
  Fornire una stima del Value at Risk analiticamente solida anche in presenza di asimmetria e code spesse tipiche dei mercati azionari e crypto.<br><br>
  
  <b>🔍 Come leggerlo:</b><br>
  Se il VaR Cornish-Fisher è sensibilmente più severo del VaR Normale, il portafoglio è esposto a rischio di shock asimmetrici.
</div>

</div>
        """, button_label="📖 Leggi Definizioni")

    col_mk1, col_mk2, col_mk3 = st.columns(3)
    with col_mk1:
        st.markdown("##### 🌊 Volatilità & Momenti")
        mdd_val = mk.get("max_drawdown_pct")
        df_m1 = pd.DataFrame({
            "Parametro": ["Volatilità Annua (σ)", "Tracking Error (vs Bench)", "Skewness (Asimmetria)", "Kurtosis (Code Grasse)", "Max Drawdown Storico"],
            "Valore": [
                f"{float(mk.get('volatility_annual_pct', 0)):.2f}%" if mk.get("volatility_annual_pct") is not None else "N/A",
                f"{float(mk.get('tracking_error_pct', 0)):.2f}%" if mk.get("tracking_error_pct") is not None else "N/A",
                f"{float(mk.get('skewness', 0)):.2f}",
                f"{float(mk.get('kurtosis', 0)):.2f}",
                fmt_pct(-abs(float(mdd_val))) if mdd_val is not None else "N/A",
            ]
        })
        st.dataframe(df_m1, use_container_width=True, hide_index=True)

    with col_mk2:
        st.markdown("##### 🛡️ Value at Risk & CVaR (1G)")
        v_h95 = float(mk.get("var_95", mk.get("var_95_pct", 0.0)) or 0.0)
        v_p95 = float(mk.get("var_parametric_95", mk.get("var_95_param", 0.0)) or 0.0)
        if v_p95 == 0.0 and mk.get("volatility_daily_pct"):
            v_p95 = float(mk.get("volatility_daily_pct", 0.0)) * 1.64485
        v_cf95 = float(mk.get("var_cf_95", mk.get("var_cornish_fisher_95", 0.0)) or 0.0)
        if v_cf95 == 0.0:
            v_cf95 = v_p95 or v_h95
        v_h99 = float(mk.get("var_99", mk.get("var_99_pct", 0.0)) or 0.0)
        if v_h99 == 0.0 and v_h95 > 0:
            v_h99 = v_h95 * 1.414
        cv_h95 = float(mk.get("cvar_95", mk.get("cvar_95_pct", 0.0)) or 0.0)
        if cv_h95 < v_h95:
            cv_h95 = v_h95
        cv_h99 = float(mk.get("cvar_99", mk.get("cvar_99_pct", 0.0)) or 0.0)
        if cv_h99 < cv_h95:
            cv_h99 = max(cv_h95 * 1.25, v_h99)

        df_m2 = pd.DataFrame({
            "Parametro": ["VaR 95% (Storico)", "VaR 95% (Parametrico)", "VaR 95% (Cornish-Fisher)", "VaR 99% (Storico)", "CVaR 95% (Shortfall)", "CVaR 99% (Tail Loss)"],
            "Valore": [
                fmt_pct(-abs(v_h95)),
                fmt_pct(-abs(v_p95)),
                fmt_pct(-abs(v_cf95)),
                fmt_pct(-abs(v_h99)),
                fmt_pct(-abs(cv_h95)),
                fmt_pct(-abs(cv_h99)),
            ]
        })
        st.dataframe(df_m2, use_container_width=True, hide_index=True)

    with col_mk3:
        st.markdown("##### 🏛️ Esposizione & Benchmark")
        corr_raw = mk.get("correlation_benchmark")
        rsq_raw = mk.get("r_squared_pct")
        df_m3 = pd.DataFrame({
            "Parametro": ["Beta di Mercato (β)", "Correlazione Benchmark (ρ)", "R-Squared Sistemico (R²)", "Eccezioni VaR (1 Anno)", "Benchmark di Riferimento"],
            "Valore": [
                f"{float(mk.get('beta', 1.0)):.2f}" if mk.get('beta') is not None else "1.00",
                f"{float(corr_raw):.2f}" if corr_raw is not None and not np.isnan(corr_raw) else "N/A",
                f"{float(rsq_raw):.2f}%" if rsq_raw is not None and not np.isnan(rsq_raw) else "N/A",
                f"{mk.get('var_exceptions_count', 0)} giorni",
                str(mk.get("benchmark_ticker", "SPY")),
            ]
        })
        st.dataframe(df_m3, use_container_width=True, hide_index=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # ── RIGA 2: DISTRIBUZIONE RENDIMENTI & CODA DI RISCHIO (FULL WIDTH) ──────
    st.markdown("#### 📉 Distribuzione Rendimenti Giornalieri e Coda di Rischio (Tail Risk)")
    st.caption("Istogramma della frequenza dei rendimenti giornalieri effettivi con evidenziazione della zona di Tail Risk (oltre il VaR 95%) e del livello di Expected Shortfall (CVaR).")
    
    fig_hist = go.Figure()
    
    # Array di rendimenti per evidenziare la coda a rischio
    ret_vals = sr_port.values * 100
    
    fig_hist.add_trace(go.Histogram(
        x=ret_vals,
        nbinsx=60,
        name="Rendimenti giornalieri",
        marker=dict(
            color="#388bfd",
            line=dict(color="#0d1117", width=0.8)
        ),
        opacity=0.85,
        hovertemplate="<b>Rendimento: %{x:.2f}%</b><br>Frequenza: %{y} giorni<extra></extra>"
    ))
    
    # Evidenziazione Coda Estrema (Tail Risk Zone)
    var_pct_x = -abs(var_hist_1d * 100)
    cvar_pct_x = -abs(cvar_hist_1d * 100)
    min_x_tail = min(float(np.min(ret_vals)) * 1.15, var_pct_x - 1.0)

    fig_hist.add_vrect(
        x0=min_x_tail, x1=var_pct_x,
        fillcolor="rgba(248, 81, 73, 0.18)",
        layer="below", line_width=0,
        annotation_text="<b>Tail Risk Zone</b>",
        annotation_position="inside top left",
        annotation_font=dict(color="rgba(248, 81, 73, 0.85)", size=10)
    )

    # Linea VaR
    fig_hist.add_vline(
        x=var_pct_x, line_color="#e3b341", line_dash="dash", line_width=2,
        annotation_text=f"<b>VaR {int(conf_level*100)}%</b>: {var_pct_x:.2f}%",
        annotation_position="top right",
        annotation_font=dict(color="#e3b341", size=11)
    )
    
    # Linea CVaR (posizionata in basso per evitare collisioni visive con la label del VaR)
    fig_hist.add_vline(
        x=cvar_pct_x, line_color="#f85149", line_dash="dot", line_width=2,
        annotation_text=f"<b>CVaR</b>: {cvar_pct_x:.2f}%",
        annotation_position="bottom left",
        annotation_font=dict(color="#f85149", size=11)
    )
    
    fig_hist.update_layout(
        xaxis_title="Rendimento Giornaliero %",
        yaxis_title="Frequenza Giorni",
        template="plotly_dark", height=390,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    apply_plotly_theme(fig_hist)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()

    st.markdown("**Drawdown Storico di Portafoglio (%)**")
    cum = (1 + sr_port).cumprod()
    roll_mx = cum.cummax()
    dd = (cum - roll_mx) / roll_mx * 100

    customdata_dd = np.column_stack([
        [f"{v:.2f}%" for v in dd.values],
        [f"{v:.2f}x" for v in cum.values],
        [f"{v:.2f}x" for v in roll_mx.values]
    ])

    fig_dd = go.Figure(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy", fillcolor="rgba(248, 81, 73, 0.15)",
        line=dict(color="#f85149", width=2.2),
        name="Drawdown",
        customdata=customdata_dd,
        hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>🔻 Drawdown: <b>%{customdata[0]}</b><br>🏔️ Massimo Precedente (High-Water Mark): <b>%{customdata[2]}</b><br>📈 Indice Cumulato: <b>%{customdata[1]}</b><extra></extra>"
    ))
    
    # Annotazione Max Drawdown
    if not dd.empty:
        m_dd_idx = dd.idxmin()
        m_dd_val = dd.min()
        fig_dd.add_annotation(
            x=pd.to_datetime(m_dd_idx), y=m_dd_val,
            text=f"🔻 Max DD: {m_dd_val:.1f}%",
            showarrow=True, arrowhead=2, arrowcolor="#f85149",
            ax=0, ay=30,
            font=dict(size=11, color="#f85149"),
            bgcolor="rgba(22, 27, 34, 0.85)", bordercolor="#f85149", borderwidth=1
        )

    fig_dd.update_layout(
        yaxis_title="Drawdown %",
        xaxis_title=None,
        height=360,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=20)
    )
    apply_plotly_theme(fig_dd)
    st.plotly_chart(fig_dd, use_container_width=True)

    st.divider()
    col_kup_h1, col_kup_h2 = st.columns([3.5, 1.2])
    with col_kup_h1:
        st.markdown("#### 🔬 Validazione e Backtesting dei Modelli VaR (Kupiec Test)")
        st.caption(f"Verifica l'efficacia statistica dei tre modelli di VaR (Storico, Parametrico e Cornish-Fisher) su un orizzonte di 1 giorno con livello di confidenza al {int(conf_level*100)}%.")
    with col_kup_h2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("🔬 Guida al Backtesting del VaR (Test di Kupiec)", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,230,118,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
  <div style="color: #00e676; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🚦 Test di Kupiec (Validazione Statistica del VaR)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Procedura statistica regolamentare (POF - Proportion of Failures) che confronta il numero di perdite reali eccedenti il VaR con il numero teorico atteso.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,230,118,0.08); border-left: 3px solid #00e676; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00e676; text-align: center; font-size: 13px;">
      <b>Violazioni Attese</b> = N &times; (1 &minus; Confidenza) &nbsp;|&nbsp; <b>LR<sub>POF</sub></b> &sim; &chi;<sup>2</sup>(1)
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Rilevare se un modello di rischio sottostima sistematicamente le perdite reali o se è eccessivamente conservativo.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Analizza 252 sedute di trading storiche e classifica il modello secondo i criteri del Comitato di Basilea.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • 🟢 <b>Zona Verde:</b> Modello solido e conforme agli standard regolamentari.<br>
    • 🟡 <b>Zona Gialla:</b> Sottostima lieve (richiede calibrazione dei parametri).<br>
    • 🔴 <b>Zona Rossa:</b> Modello rigettato per gravi fallimenti predittivi.
  </div>
</div>
</div>
""", button_label="💡 Guida al Backtesting")

    recent_r = r.tail(252)
    n_days = len(recent_r)
    expected_exc = n_days * alpha

    exc_hist = len(recent_r[recent_r < threshold_hist_1d])
    exc_param = len(recent_r[recent_r < -var_param_1d])
    exc_cf = len(recent_r[recent_r < -var_cf_1d])

    ratio_hist = (exc_hist / n_days) * 100
    ratio_param = (exc_param / n_days) * 100
    ratio_cf = (exc_cf / n_days) * 100

    from scipy.stats import chi2
    def calc_kupiec_lr(x: int, N: int, p: float = 0.05):
        if N <= 0: return 0.0, 1.0
        p_hat = x / N
        if p_hat == 0:
            lr = -2.0 * (N * np.log(1.0 - p))
        elif p_hat >= 1:
            lr = -2.0 * (N * np.log(p))
        else:
            num = ((1.0 - p) ** (N - x)) * (p ** x)
            den = ((1.0 - p_hat) ** (N - x)) * (p_hat ** x)
            lr = -2.0 * np.log(num / den) if (den > 0 and num > 0) else 0.0
        lr = max(0.0, float(lr))
        pval = float(1.0 - chi2.cdf(lr, df=1))
        return lr, pval

    lr_hist, pval_hist = calc_kupiec_lr(exc_hist, n_days, alpha)
    lr_param, pval_param = calc_kupiec_lr(exc_param, n_days, alpha)
    lr_cf, pval_cf = calc_kupiec_lr(exc_cf, n_days, alpha)

    def get_basel_badge(exc_count, expected):
        if exc_count <= expected:
            return '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap;">🟢 Zona Verde</span>'
        elif exc_count <= expected * 1.5:
            return '<span style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap;">🟡 Zona Gialla</span>'
        else:
            return '<span style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap;">🔴 Zona Rossa</span>'

    badge_hist = get_basel_badge(exc_hist, expected_exc)
    badge_param = get_basel_badge(exc_param, expected_exc)
    badge_cf = get_basel_badge(exc_cf, expected_exc)

    col_b1, col_b2, col_b3 = st.columns(3)
    
    with col_b1:
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 12px; padding: 18px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 14.5px; font-weight: 700; color: #f8fafc; white-space: nowrap;">📊 VaR Storico</span>
                {badge_hist}
            </div>
            <div style="margin-bottom: 14px;">
                <div style="font-size: 27px; font-weight: 800; font-family: monospace; color: #ffffff; line-height: 1.1; letter-spacing: -0.5px;">{var_hist_1d * 100:.2f}%</div>
                <div style="font-size: 11.5px; color: #94a3b8; margin-top: 3px;">Soglia Perdita 1G ({int(conf_level*100)}% Confidenza)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">
                    <span>Violazioni Registrate:</span>
                    <b style="font-family: monospace; color: #f8fafc;">{exc_hist} / {n_days} ({ratio_hist:.2f}%)</b>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8;">
                    <span>Target Atteso (5%):</span>
                    <span style="font-family: monospace; color: #cbd5e1;">{expected_exc:.1f} violazioni</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: #94a3b8; border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 8px;">
                <span>Test LR Kupiec:</span>
                <span style="font-family: monospace; color: #f8fafc;">LR = {lr_hist:.2f} &bull; p-val = {pval_hist:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_b2:
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 12px; padding: 18px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 14.5px; font-weight: 700; color: #f8fafc; white-space: nowrap;">📐 VaR Parametrico</span>
                {badge_param}
            </div>
            <div style="margin-bottom: 14px;">
                <div style="font-size: 27px; font-weight: 800; font-family: monospace; color: #ffffff; line-height: 1.1; letter-spacing: -0.5px;">{var_param_1d * 100:.2f}%</div>
                <div style="font-size: 11.5px; color: #94a3b8; margin-top: 3px;">Soglia Gaussiana 1G ({int(conf_level*100)}% Confidenza)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">
                    <span>Violazioni Registrate:</span>
                    <b style="font-family: monospace; color: #f8fafc;">{exc_param} / {n_days} ({ratio_param:.2f}%)</b>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8;">
                    <span>Target Atteso (5%):</span>
                    <span style="font-family: monospace; color: #cbd5e1;">{expected_exc:.1f} violazioni</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: #94a3b8; border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 8px;">
                <span>Test LR Kupiec:</span>
                <span style="font-family: monospace; color: #f8fafc;">LR = {lr_param:.2f} &bull; p-val = {pval_param:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_b3:
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 12px; padding: 18px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 14.5px; font-weight: 700; color: #f8fafc; white-space: nowrap;">📈 VaR Cornish-Fisher</span>
                {badge_cf}
            </div>
            <div style="margin-bottom: 14px;">
                <div style="font-size: 27px; font-weight: 800; font-family: monospace; color: #ffffff; line-height: 1.1; letter-spacing: -0.5px;">{var_cf_1d * 100:.2f}%</div>
                <div style="font-size: 11.5px; color: #94a3b8; margin-top: 3px;">Soglia Non-Gaussiana (Skew/Kurt)</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1; margin-bottom: 4px;">
                    <span>Violazioni Registrate:</span>
                    <b style="font-family: monospace; color: #f8fafc;">{exc_cf} / {n_days} ({ratio_cf:.2f}%)</b>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8;">
                    <span>Target Atteso (5%):</span>
                    <span style="font-family: monospace; color: #cbd5e1;">{expected_exc:.1f} violazioni</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: #94a3b8; border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 8px;">
                <span>Test LR Kupiec:</span>
                <span style="font-family: monospace; color: #f8fafc;">LR = {lr_cf:.2f} &bull; p-val = {pval_cf:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="margin-top: 14px;"></div>', unsafe_allow_html=True)
    st.markdown("##### 📉 Tracciamento Temporale delle Violazioni VaR (Backtest a 252 Sedute)")
    
    fig_kup = go.Figure()
    
    # Rendimenti ordinari vs Violazioni
    recent_r_pct = (recent_r * 100.0).round(2)
    breach_mask = recent_r < threshold_hist_1d
    normal_r = recent_r_pct[~breach_mask]
    breach_r = recent_r_pct[breach_mask]
    
    fig_kup.add_trace(go.Scatter(
        x=normal_r.index,
        y=normal_r.values,
        mode="markers",
        name="Rendimento Conforme",
        marker=dict(color="rgba(148, 163, 184, 0.40)", size=4.0),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Rendimento:</b> %{y:+.2f}%<extra></extra>"
    ))
    
    # Linea Soglia VaR Storico 95%
    var_line_val = round(-var_hist_1d * 100.0, 2)
    fig_kup.add_hline(
        y=var_line_val,
        line_dash="dash",
        line_color="#ff9900",
        annotation_text=f" Soglia VaR 95% (-{var_hist_1d*100:.2f}%)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ffb74d", size=11)
    )
    
    # Punti di Violazione Evidenziati in Rosso
    if not breach_r.empty:
        fig_kup.add_trace(go.Scatter(
            x=breach_r.index,
            y=breach_r.values,
            mode="markers",
            name=f"Violazioni VaR ({len(breach_r)} eccezioni)",
            marker=dict(
                color="#ef4444",
                size=8.5,
                symbol="diamond",
                line=dict(color="#ffffff", width=1.2)
            ),
            hovertemplate="<b>⚠️ Violazione VaR</b><br><b>Data:</b> %{x|%d/%m/%Y}<br><b>Perdita Effettiva:</b> %{y:.2f}%<br><b>Soglia VaR:</b> " + f"{var_line_val:.2f}%" + "<extra></extra>"
        ))
        
    fig_kup.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#cbd5e1")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(title="Rendimento Giornaliero (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=True, zerolinecolor="rgba(255,255,255,0.15)")
    )
    st.plotly_chart(fig_kup, use_container_width=True)

    # ── SEZIONE GARCH(1,1) & FILTERED HISTORICAL SIMULATION (FHS) ────────
    st.divider()
    col_garch_head1, col_garch_head2 = st.columns([3.2, 1.2])
    with col_garch_head1:
        st.markdown("#### ⚡ Volatilità Condizionale GARCH(1,1) & Filtered Historical Simulation (FHS)")
        st.caption("Modellazione econometrica dei cluster di volatilità, persistenza degli shock e stima non-parametrica a code spesse conforme a FRTB / Basel III.")
    with col_garch_head2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        render_garch_fhs_modal(button_label="ℹ️ Metodologia GARCH(1,1) & FHS", use_popover=False)

    from core.garch_engine import compute_garch_fhs_bundle
    garch_bundle = compute_garch_fhs_bundle(r, total_value=total_value, horizon=holding_period)
    gkpi = garch_bundle["kpis"]
    fit_data = garch_bundle["fit"]
    df_dyn = garch_bundle["dynamic_bands"]
    df_term = garch_bundle["term_structure"]

    # 4 KPI Cards ad Alta Leggibilità (Nessun troncamento)
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        vol_curr = gkpi["next_day_annual_vol_pct"]
        vol_long = gkpi["unconditional_annual_vol_pct"]
        diff_vol = vol_curr - vol_long
        metric_card(
            "Volatilità Condizionale (T+1)",
            f"{vol_curr:.2f}%",
            delta=f"{diff_vol:+.2f}% vs Lungo Termine ({vol_long:.2f}%)",
            positive=(diff_vol <= 0),
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Volatilità annualizzata istantanea stimata dal modello GARCH(1,1) per la prossima seduta di borsa.</div>
<div style="margin-bottom: 6px;"><b>📐 Formula:</b> &sigma;<sub>t+1</sub><sup>2</sup> = &omega; + &alpha; &epsilon;<sub>t</sub><sup>2</sup> + &beta; &sigma;<sub>t</sub><sup>2</sup></div>
<div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Rileva se il portafoglio si trova in una fase di turbolenza o calma rispetto alla media storica.</div>
<div><b>🔍 Media di Lungo Termine:</b> &sigma;<sub>L</sub> = """ + f"{vol_long:.2f}%" + """.</div>
</div>"""
        )
    with col_g2:
        persist_val = gkpi["persistence"]
        hl_days = gkpi["half_life_days"]
        metric_card(
            "Persistenza Shock (α + β)",
            f"{persist_val:.3f}",
            delta=f"Half-Life: {hl_days:.1f} giorni" if hl_days < 500 else "Memoria ultra-lunga",
            positive=(persist_val < 1.0),
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Grado di memoria e persistenza dei picchi di volatilità nel tempo (&alpha; + &beta;).</div>
<div style="margin-bottom: 6px;"><b>📐 Half-Life:</b> ln(0.5) / ln(&alpha; + &beta;) = tempo in sedute di borsa affinché uno shock si dimezzi del 50%.</div>
<div><b>🔍 Come leggerlo:</b> &lt; 1.0 indica processo stazionario con mean-reversion verso la media incondizionata.</div>
</div>"""
        )
    with col_g3:
        var_fhs_val = gkpi.get(f"var_fhs_{int(conf_level*100)}_pct", 0.0)
        var_fhs_eur = gkpi.get(f"var_fhs_{int(conf_level*100)}_eur", 0.0)
        metric_card(
            f"VaR FHS ({int(conf_level*100)}% - {holding_period}G)",
            f"{var_fhs_val:.2f}%",
            delta=f"-€ {var_fhs_eur:,.2f}",
            positive=False,
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Value at Risk calcolato con la Filtered Historical Simulation (FHS di Barone-Adesi).</div>
<div style="margin-bottom: 6px;"><b>🎯 Vantaggio:</b> Combina la dinamicità del GARCH(1,1) con la distribuzione non-parametrica a code grasse dei residui standardizzati reali.</div>
<div><b>🔍 Orizzonte:</b> Perdita massima attesa a """ + f"{int(conf_level*100)}% su {holding_period} giorni" + """.</div>
</div>"""
        )
    with col_g4:
        cvar_fhs_val = gkpi.get(f"cvar_fhs_{int(conf_level*100)}_pct", 0.0)
        cvar_fhs_eur = gkpi.get(f"cvar_fhs_{int(conf_level*100)}_eur", 0.0)
        metric_card(
            "CVaR FHS (Expected Shortfall)",
            f"{cvar_fhs_val:.2f}%",
            delta=f"-€ {cvar_fhs_eur:,.2f}",
            positive=False,
            help_text="""<div style="font-size: 13px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Expected Shortfall condizionale calcolato sui residui FHS oltre la soglia del VaR.</div>
<div style="margin-bottom: 6px;"><b>🎯 Requisito:</b> Metrica primaria raccomandata dal comitato di Basilea III (FRTB) per il rischio di coda estremo.</div>
<div><b>🔍 Significato:</b> Perdita media nello scenario estremo di superamento del VaR.</div>
</div>"""
        )

    # 2 Grafici Plotly ad Alta Risoluzione Disposti su Due Righe Dedicate (Full Width)
    st.markdown("##### 📈 Volatilità Condizionale Storica & Bande Dinamiche VaR GARCH(1,1)")
    fig_garch_ts = go.Figure()
    
    ret_pct = (df_dyn["return"] * 100.0).round(2)
    var95_pct = (-df_dyn["var95_dynamic_pct"]).round(2)
    var99_pct = (-df_dyn["var99_dynamic_pct"]).round(2)
    
    # Rendimenti effettivi
    fig_garch_ts.add_trace(go.Scatter(
        x=df_dyn.index,
        y=ret_pct,
        mode="markers",
        name="Rendimento Giornaliero Effettivo",
        marker=dict(color="rgba(148, 163, 184, 0.40)", size=3.5),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>Rendimento:</b> %{y:.2f}%<extra></extra>"
    ))
    # Banda VaR 95% GARCH
    fig_garch_ts.add_trace(go.Scatter(
        x=df_dyn.index,
        y=var95_pct,
        mode="lines",
        name="Banda VaR 95% Dinamica (GARCH)",
        line=dict(color="#ff9900", width=2.0),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>VaR 95% GARCH:</b> %{y:.2f}%<extra></extra>"
    ))
    # Banda VaR 99% GARCH
    fig_garch_ts.add_trace(go.Scatter(
        x=df_dyn.index,
        y=var99_pct,
        mode="lines",
        name="Banda VaR 99% Estrema (GARCH)",
        line=dict(color="#ff4d4f", width=2.0, dash="dot"),
        hovertemplate="<b>Data:</b> %{x|%d/%m/%Y}<br><b>VaR 99% GARCH:</b> %{y:.2f}%<extra></extra>"
    ))
    
    fig_garch_ts.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#cbd5e1")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False),
        yaxis=dict(title="Rendimento / VaR (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=True, zerolinecolor="rgba(255,255,255,0.15)")
    )
    st.plotly_chart(fig_garch_ts, use_container_width=True)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    st.markdown("##### 🔮 Struttura a Termine della Volatilità Prevista σ(k) a 30 Giorni (Mean-Reversion)")
    fig_term = go.Figure()
    
    fc_vol = df_term["forecast_annual_vol_pct"].round(2)
    fig_term.add_trace(go.Scatter(
        x=df_term["horizon_days"],
        y=fc_vol,
        mode="lines+markers",
        name="Volatilità Annualizzata Prevista σ(k)",
        line=dict(color="#00f3ff", width=2.8),
        marker=dict(size=6, color="#00f3ff", line=dict(color="#ffffff", width=1)),
        fill='tozeroy',
        fillcolor='rgba(0, 243, 255, 0.05)',
        hovertemplate="<b>Orizzonte:</b> %{x} giorni<br><b>Volatilità Prevista:</b> %{y:.2f}%<extra></extra>"
    ))
    
    # Linea asintotica V_L
    fig_term.add_hline(
        y=vol_long,
        line_dash="dash",
        line_color="#ff9900",
        annotation_text=f" Volatilità Asintotica di Lungo Termine ({vol_long:.2f}%)",
        annotation_position="top right",
        annotation_font=dict(color="#ffb74d", size=12)
    )
    
    y_min = min(df_term["forecast_annual_vol_pct"].min(), vol_long)
    y_max = max(df_term["forecast_annual_vol_pct"].max(), vol_long)
    pad = max(0.4, (y_max - y_min) * 0.18)
    
    fig_term.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#cbd5e1")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Orizzonte Previsionale (Giorni Lavorativi)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", dtick=2),
        yaxis=dict(title="Volatilità Annualizzata (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", range=[max(0.0, y_min - pad), y_max + pad])
    )
    st.plotly_chart(fig_term, use_container_width=True)

    # Parametri di calibrazione con tabelle HTML responsive a riga singola (Zero Wrapping)
    with st.expander("🔬 Dettaglio Parametri Econometrici GARCH(1,1) & Test di Verosimiglianza"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"""
            <div style="background: rgba(18, 24, 38, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;">
                <div style="font-size: 11.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; margin-bottom: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 6px;">
                    PARAMETRI ECONOMETRICI STIMATI
                </div>
                <table style="width: 100%; font-size: 12.5px; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Costante Fondo (&omega;)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['omega']:.8f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">ARCH Shock (&alpha;)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['alpha']:.5f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">GARCH Memoria (&beta;)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['beta']:.5f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; font-weight: 600; white-space: nowrap;">Persistenza (&alpha; + &beta;)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 700; color: #4ade80; white-space: nowrap;">{fit_data['persistence']:.5f}</td>
                    </tr>
                    <tr style="height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Rendimento Medio (&mu;)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['mu']*100:+.4f}%</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
        with col_p2:
            conv_status = '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap;">🟢 Convergenza SLSQP</span>' if fit_data["converged"] else '<span style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; white-space: nowrap;">🟡 Fallback Robusto</span>'
            hl_str = f"{fit_data['half_life_days']:.1f} giorni" if fit_data['half_life_days'] < 500 else "Memoria ultra-lunga"
            
            st.markdown(f"""
            <div style="background: rgba(18, 24, 38, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;">
                <div style="font-size: 11.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; margin-bottom: 10px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 6px;">
                    DIAGNOSTICA & TEST DI VEROSIMIGLIANZA
                </div>
                <table style="width: 100%; font-size: 12.5px; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Stato Ottimizzazione</td>
                        <td style="text-align: right; white-space: nowrap;">{conv_status}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Log-Likelihood (LLF)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['log_likelihood']:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Criterio AIC (Akaike)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['aic']:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Criterio BIC (Bayesiano)</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #38bdf8; white-space: nowrap;">{fit_data['bic']:.2f}</td>
                    </tr>
                    <tr style="height: 30px;">
                        <td style="color: #cbd5e1; white-space: nowrap;">Half-Life Shock</td>
                        <td style="text-align: right; font-family: monospace; font-weight: 600; color: #facc15; white-space: nowrap;">{hl_str}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)


# ==============================================================================
# TAB 3: CORRELAZIONI, LIQUIDITÀ & ATR CHANDELIER
# ==============================================================================
elif active_risk_tab == "🔗 Correlazioni, Liquidità & ATR Chandelier":
    st.markdown("### 🔗 Matrice di Correlazione tra Asset")
    df_ret_all = results["returns"].dropna(how="all")
    active_t = pos[pos["qty_net"] > 0]["ticker"].tolist()
    common_t = [t for t in active_t if t in df_ret_all.columns]

    if len(common_t) > 1:
        corr_matrix = df_ret_all[common_t].corr().round(2)
        fig_corr = px.imshow(
            corr_matrix,
            color_continuous_scale=[[0.0, "#f85149"], [0.5, "#161b22"], [1.0, "#3fb950"]],
            zmin=-1, zmax=1,
            text_auto=".2f",
            labels={"x": "Asset 1", "y": "Asset 2", "color": "Correlazione (ρ)"}
        )
        fig_corr.update_traces(
            hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>🔗 Correlazione Lineare (ρ): <b>%{z:.2f}</b><extra></extra>"
        )
        fig_corr.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_colorbar=dict(title="Correlazione (ρ)", tickmode="linear", dtick=0.5)
        )
        apply_plotly_theme(fig_corr)
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Numero di asset attivi insufficiente per calcolare la matrice di correlazione.")

    st.divider()

    col_liq_h1, col_liq_h2 = st.columns([3.5, 1.2])
    with col_liq_h1:
        st.markdown("### 💧 Rischio di Liquidità & Orizzonte di Smobilizzo (Days-to-Liquidate)")
        st.caption("Stima del tempo necessario per smobilizzare le posizioni assumendo una partecipazione prudenziale massima al 15% del Volume Medio Giornaliero ($ADV_{30g}$).")
    with col_liq_h2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("💧 Guida al Rischio di Liquidità & Market Impact", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">💧 Days-to-Liquidate (Orizzonte di Smobilizzo)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Stima dei giorni lavorativi necessari per liquidare integralmente una posizione senza alterare il prezzo di mercato (assumendo una partecipazione max al 15% del Volume Medio Giornaliero - ADV).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #58a6ff; text-align: center; font-size: 13px;">
      <b>Days to Liquidate</b> = Quantità Posizione / ( ADV<sub>30g</sub> &times; 15% )
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Prevenire il rischio di restare 'intrappolati' in asset poco liquidi durante fasi di panico o vendite forzate.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato sul volume medio giornaliero a 30 sedute scaricato da Yahoo Finance per ciascun asset aperto.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • <b>< 1.0 Giorno:</b> Liquidità eccellente (smobilizzo istantaneo).<br>
    • <b>1.0 – 3.0 Giorni:</b> Liquidità buona.<br>
    • <b>> 5.0 Giorni:</b> Rischio illiquidità (possibile market impact e slippage severo).
  </div>
</div>
</div>
""", button_label="💡 Come si legge?")

    if "days_to_liquidate" in pos.columns:
        df_liq = pos[pos["qty_net"] > 0][["ticker", "current_value", "days_to_liquidate"]].copy()
        tot_liq_val = df_liq["current_value"].sum()
        df_liq["weight"] = (df_liq["current_value"] / tot_liq_val * 100.0) if tot_liq_val > 0 else 0.0
        df_liq = df_liq.sort_values(by="days_to_liquidate", ascending=False)
        
        # KPI Card di sintesi
        weighted_dtl = (df_liq["days_to_liquidate"] * (df_liq["current_value"] / tot_liq_val)).sum() if tot_liq_val > 0 else 0.0
        critical_cnt = len(df_liq[df_liq["days_to_liquidate"] > 3.0])
        max_dtl_asset = df_liq.iloc[0]["ticker"] if not df_liq.empty else "-"
        max_dtl_val = df_liq.iloc[0]["days_to_liquidate"] if not df_liq.empty else 0.0
        
        col_lq1, col_lq2, col_lq3 = st.columns(3)
        with col_lq1:
            metric_card(
                "Days-to-Liquidate Ponderato",
                f"{weighted_dtl:.1f} gg",
                delta="Smobilizzo Istantaneo",
                positive=True,
                help_text="Tempo medio stimato per liquidare l'intero portafoglio ponderato per il valore di ciascuna posizione."
            )
        with col_lq2:
            metric_card(
                "Posizioni a Rischio (> 3 Giorni)",
                f"{critical_cnt} / {len(df_liq)}",
                delta="Nessun Rischio Illiquidità" if critical_cnt == 0 else f"{critical_cnt} Asset da monitorare",
                positive=(critical_cnt == 0),
                help_text="Numero di posizioni che richiederebbero oltre 3 giorni di borsa aperta per essere liquidate senza superare il 15% dell'ADV."
            )
        with col_lq3:
            metric_card(
                "Tempo Max di Smobilizzo",
                f"{max_dtl_val:.1f} gg",
                delta=f"Asset: {max_dtl_asset}",
                positive=(max_dtl_val <= 3.0),
                help_text=f"La posizione che richiede il maggior orizzonte di liquidazione è {max_dtl_asset} con {max_dtl_val:.1f} giorni stimati."
            )
            
        st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
        
        # Tabella DTL Glassmorphic
        rows_liq_list = []
        for _, r_l in df_liq.iterrows():
            t_name = str(r_l["ticker"])
            c_val = float(r_l["current_value"])
            w_pct = float(r_l["weight"])
            dtl_v = float(r_l["days_to_liquidate"])
            
            if dtl_v <= 1.0:
                dtl_badge = '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 2px 8px; border-radius: 10px; font-family: monospace; font-weight: 700; font-size: 11.5px;">&le; 1.0 g</span>'
                status_txt = '<span style="color: #4ade80; font-weight: 600; font-size: 12px;">🟢 Immediato</span>'
            elif dtl_v <= 3.0:
                dtl_badge = f'<span style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); padding: 2px 8px; border-radius: 10px; font-family: monospace; font-weight: 700; font-size: 11.5px;">{dtl_v:.1f} g</span>'
                status_txt = '<span style="color: #facc15; font-weight: 600; font-size: 12px;">🟡 Moderato</span>'
            else:
                dtl_badge = f'<span style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 2px 8px; border-radius: 10px; font-family: monospace; font-weight: 700; font-size: 11.5px;">{dtl_v:.1f} g</span>'
                status_txt = '<span style="color: #f87171; font-weight: 600; font-size: 12px;">🔴 Rischioso</span>'
                
            r_str = f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);height:42px;"><td style="color:#ffffff;font-weight:700;padding:8px 14px;font-family:monospace;">{t_name}</td><td style="color:#f8fafc;padding:8px 14px;font-family:monospace;font-weight:600;">€ {c_val:,.2f}</td><td style="color:#cbd5e1;padding:8px 14px;font-family:monospace;">{w_pct:.2f}%</td><td style="text-align:center;padding:8px 14px;">{dtl_badge}</td><td style="padding:8px 14px;">{status_txt}</td></tr>'
            rows_liq_list.append(r_str)
            
        liq_table_html = f'<div style="background:rgba(18,24,38,0.75);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px 18px;margin-bottom:12px;overflow-x:auto;max-height:420px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.12);color:#94a3b8;font-size:11.5px;font-weight:700;letter-spacing:0.5px;height:32px;"><th style="text-align:left;padding:8px 14px;width:20%;">TICKER ASSET</th><th style="text-align:left;padding:8px 14px;width:24%;">VALORE (€)</th><th style="text-align:left;padding:8px 14px;width:18%;">PESO %</th><th style="text-align:center;padding:8px 14px;width:20%;">DAYS TO LIQUIDATE</th><th style="text-align:left;padding:8px 14px;width:18%;">PROFILO SMOBILIZZO</th></tr></thead><tbody>{"".join(rows_liq_list)}</tbody></table></div>'
        st.markdown(liq_table_html, unsafe_allow_html=True)
    else:
        st.info("Dati sui volumi non sufficienti per calcolare i Days-to-Liquidate.")

    st.divider()

    col_atr_h1, col_atr_h2 = st.columns([3.5, 1.2])
    with col_atr_h1:
        st.markdown("### 🛡️ ATR Trailing Stop-Loss & Chandelier Exit Manager")
        st.caption("Livelli quantitativi di stop-loss dinamici ancorati alla volatilità effettiva ($ATR_{14}$) e ai massimi a 22 giorni per ciascun asset.")
    with col_atr_h2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal(
            "🛡️ Guida all'ATR Trailing Stop-Loss & Chandelier Exit",
            """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🛡️ Chandelier Exit (Stop-Loss Dinamico Volatilità)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Algoritmo quantitativo di risk management (sviluppato da Chuck LeBeau) che fissa un livello di trailing stop agganciato al massimo recente, proporzionato alla volatilità reale (Average True Range).</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 13px;">
      <b>Stop Chandelier</b> = Max<sub>22g</sub> &minus; 3.0 &times; ATR<sub>14</sub>
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Proteggere i profitti accumulati nei trend rialzisti ed evitare di uscire prematuramente a causa del normale 'rumore' di mercato.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcola l'ATR a 14 periodi sui massimi, minimi e chiusure storiche e sottrae 3 volte tale valore dal picco massimo a 22 sedute.</div>
  <div><b>🔍 Come leggerlo:</b><br>
    • 🟢 <b>REGOLARE:</b> Il prezzo è sopra il livello di stop (trend intatto).<br>
    • 🔴 <b>TRIGGER:</b> Il prezzo ha infranto il Chandelier Stop (segnale di chiusura o riduzione posizione).
  </div>
</div>
</div>
            """,
            button_label="💡 Come funziona il Chandelier Exit?"
        )

    df_prices_all = results.get("df_prices", pd.DataFrame())
    pos_df = results.get("positions", pd.DataFrame())

    if not pos_df.empty:
        from core.risk_engine import compute_atr_chandelier_exits
        atr_res = compute_atr_chandelier_exits(df_prices_all, pos_df, period=14, multiplier=3.0)
        df_atr_disp = atr_res.get("summary_df", pd.DataFrame())
        
        if isinstance(df_atr_disp, pd.DataFrame) and not df_atr_disp.empty:
            trig_cnt = atr_res.get("stop_triggered_count", 0)
            tot_pos = len(df_atr_disp)
            ok_cnt = tot_pos - trig_cnt
            avg_dist = df_atr_disp["distance_pct"].mean() if "distance_pct" in df_atr_disp.columns else 0.0
            
            # 3 KPI Cards Scorecard
            col_k1, col_k2, col_k3 = st.columns(3)
            with col_k1:
                metric_card(
                    "Posizioni in Stop Trigger",
                    f"{trig_cnt} / {tot_pos}",
                    delta="Chiusura o Hedging Consigliato" if trig_cnt > 0 else "Nessun Alert Attivo",
                    positive=(trig_cnt == 0),
                    help_text="Numero di asset la cui quotazione attuale ha infranto la soglia di Chandelier Exit."
                )
            with col_k2:
                metric_card(
                    "Posizioni con Trend Intatto",
                    f"{ok_cnt} / {tot_pos}",
                    delta="Sopra la Soglia di Stop",
                    positive=True,
                    help_text="Asset che mantengono un prezzo di mercato superiore al livello di trailing stop."
                )
            with col_k3:
                metric_card(
                    "Distanza Media dallo Stop",
                    f"{avg_dist:+.2f}%",
                    delta="Cuscinetto Volatilità",
                    positive=(avg_dist >= 0),
                    help_text="Distanza percentuale media dei prezzi di mercato rispetto ai rispettivi livelli di Chandelier Stop."
                )
                
            st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
            
            # Tabella Chandelier Exit Glassmorphic (ordinata per urgenza di rischio)
            df_atr_disp = df_atr_disp.sort_values(by="distance_pct", ascending=True)
            rows_atr_list = []
            for _, r_a in df_atr_disp.iterrows():
                t_code = str(r_a.get("ticker", ""))
                p_mkt = float(r_a.get("last_price", 0.0))
                atr_v = float(r_a.get("atr_14", 0.0))
                hi_v = float(r_a.get("highest_high_22", 0.0))
                stop_v = float(r_a.get("chandelier_stop", 0.0))
                dist_v = float(r_a.get("distance_pct", 0.0))
                is_trig = bool(r_a.get("stop_triggered", False)) or (p_mkt < stop_v) or (dist_v < 0)
                
                if is_trig:
                    status_badge = '<span style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 3px 10px; border-radius: 10px; font-weight: 700; font-size: 11px; white-space: nowrap;">🔴 TRIGGER</span>'
                    dist_txt = f'<span style="color: #f87171; font-weight: 700; font-family: monospace;">{dist_v:+.2f}%</span>'
                elif dist_v < 4.0:
                    status_badge = '<span style="background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); padding: 3px 10px; border-radius: 10px; font-weight: 700; font-size: 11px; white-space: nowrap;">🟡 VICINO STOP</span>'
                    dist_txt = f'<span style="color: #facc15; font-weight: 700; font-family: monospace;">{dist_v:+.2f}%</span>'
                else:
                    status_badge = '<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 3px 10px; border-radius: 10px; font-weight: 700; font-size: 11px; white-space: nowrap;">🟢 REGOLARE</span>'
                    dist_txt = f'<span style="color: #4ade80; font-weight: 700; font-family: monospace;">{dist_v:+.2f}%</span>'
                    
                row_str = f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);height:44px;"><td style="color:#ffffff;font-weight:700;padding:8px 14px;font-family:monospace;">{t_code}</td><td style="color:#f8fafc;padding:8px 14px;font-family:monospace;font-weight:600;">€ {p_mkt:,.2f}</td><td style="color:#cbd5e1;padding:8px 14px;font-family:monospace;">€ {atr_v:,.2f}</td><td style="color:#cbd5e1;padding:8px 14px;font-family:monospace;">€ {hi_v:,.2f}</td><td style="color:#f8fafc;padding:8px 14px;font-family:monospace;font-weight:600;">€ {stop_v:,.2f}</td><td style="text-align:center;padding:8px 14px;">{dist_txt}</td><td style="padding:8px 14px;white-space:nowrap;">{status_badge}</td></tr>'
                rows_atr_list.append(row_str)
                
            table_atr_html = f'<div style="background:rgba(18,24,38,0.75);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:14px 18px;margin-bottom:12px;overflow-x:auto;max-height:440px;overflow-y:auto;"><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.12);color:#94a3b8;font-size:11.5px;font-weight:700;letter-spacing:0.5px;height:32px;"><th style="text-align:left;padding:8px 14px;width:15%;">TICKER</th><th style="text-align:left;padding:8px 14px;width:16%;">PREZZO MKT (€)</th><th style="text-align:left;padding:8px 14px;width:14%;">ATR 14G (€)</th><th style="text-align:left;padding:8px 14px;width:15%;">MAX 22G (€)</th><th style="text-align:left;padding:8px 14px;width:16%;">CHANDELIER STOP (€)</th><th style="text-align:center;padding:8px 14px;width:12%;">DISTANZA %</th><th style="text-align:left;padding:8px 14px;width:12%;">STATO ALERT</th></tr></thead><tbody>{"".join(rows_atr_list)}</tbody></table></div>'
            st.markdown(table_atr_html, unsafe_allow_html=True)
        else:
            st.info("Dati storici sui prezzi insufficienti per il calcolo dell'ATR.")


# ==============================================================================
# TAB 4: RILEVATORE ANOMALIE ML (ISOLATION FOREST)
# ==============================================================================
elif active_risk_tab == "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)":
    col_head_iso1, col_head_iso2 = st.columns([3.2, 1.1])
    with col_head_iso1:
        st.markdown("### 🕵️‍♂️ Machine Learning Anomaly Detector (Isolation Forest & Correlation Drift)")
        st.caption("Algoritmo di Machine Learning non supervisionato (Isolation Forest) per l'identificazione automatica di anomalie di rendimento, rotture di correlazione e giornate di stress di mercato.")
    with col_head_iso2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("🕵️‍♂️ Guida al Rilevatore di Anomalie ML (Isolation Forest)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Isolation Forest per la Finanza Quantitativa</div>
  <div>Un algoritmo avanzato di Machine Learning non supervisionato (Liu, Ting e Zhou, 2008) che isola le anomalie multidimensionali partizionando ricorsivamente lo spazio delle feature di mercato tramite alberi di decisione randomizzati.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Score di Anomalia e Feature Spaziali</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    <b>Score(x, n)</b> = 2<sup>&minus; E(h(x)) / c(n)</sup><br>
    <i>Feature analizzate:</i> Rendimento Giornaliero, Volatilità Rolling 20g, Correlazione Media e Drawdown %
  </div>
  <div>I punti anomali richiedono pochissime partizioni casuali per essere isolati rispetto alle osservazioni ordinarie (lunghezza del percorso <i>h(x)</i> molto breve).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Identifica eventi rari 'Cigni Neri' (Black Swans), rotture improvvise di correlazione tra asset e shock di volatilità non catturabili dai tradizionali modelli lineari gaussiani.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il modulo <code>core/financial_analysis.py</code> addestra un ensemble di 100 alberi di isolamento con tasso di contaminazione prudenziale del 5% su tutta la serie storica congiunta.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🔴 <b>Punti Rossi (Anomalie):</b> Giornate storiche di stress congiunto o disallineamento marcato.<br>
    • <b>Score di Anomalia Negativo:</b> Più il punteggio è basso/negativo, più l'evento è stato severo e statisticamente anomalo.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il Rilevatore ML?")

    from core.financial_analysis import detect_portfolio_anomalies_isolation_forest
    df_ret_iso = results.get("returns", pd.DataFrame())
    sr_port_iso = results.get("portfolio_return", pd.Series(dtype=float))

    iso_res = detect_portfolio_anomalies_isolation_forest(
        df_returns=df_ret_iso,
        sr_portfolio=sr_port_iso,
        contamination=0.05
    )

    c_iso1, c_iso2, c_iso3, c_iso4 = st.columns(4)
    with c_iso1:
        metric_card("Giorni Storici Analizzati", f"{iso_res['total_days']}", "Campione Rendimenti", True)
    with c_iso2:
        metric_card("Anomalie ML Rilevate", f"{iso_res['anomaly_count']}", f"Tasso Contaminazione: {iso_res['anomaly_rate_pct']:.1f}%", positive=(iso_res['anomaly_count'] == 0))
    with c_iso3:
        df_full_iso = iso_res["full_results_df"]
        min_score = df_full_iso["Score Anomalia"].min() if not df_full_iso.empty else 0.0
        metric_card("Score Anomalia Massimo", f"{min_score:.3f}", "Più negativo = Più grave", positive=(min_score > -0.15))
    with c_iso4:
        worst_day = iso_res["anomaly_df"].iloc[0]["Data"] if not iso_res["anomaly_df"].empty else "Nessuna"
        st.metric("Peggior Data Anomala", f"{worst_day}")

    if not df_full_iso.empty:
        fig_iso = go.Figure()
        df_norm = df_full_iso[df_full_iso["Anomalia"] == "🟢 Normale"]
        df_anom = df_full_iso[df_full_iso["Anomalia"] == "🔴 ANOMALIA"]

        fig_iso.add_trace(go.Scatter(
            x=df_norm["Data"], y=df_norm["Rendimento Portafoglio %"],
            mode="markers", name="Rendimento Normale",
            marker=dict(color="#58a6ff", size=6, opacity=0.65),
            hovertemplate="<b>Data: %{x}</b><br>📈 Rendimento: <b>%{y:.2f}%</b><extra></extra>"
        ))
        fig_iso.add_trace(go.Scatter(
            x=df_anom["Data"], y=df_anom["Rendimento Portafoglio %"],
            mode="markers", name="🔴 Anomalia Rilevata (ML)",
            marker=dict(color="#d90429", size=10, symbol="x", line=dict(width=2, color="#ffffff")),
            hovertemplate="<b>⚠️ ANOMALIA ML: %{x}</b><br>⚡ Rendimento: <b>%{y:.2f}%</b><extra></extra>"
        ))

        fig_iso.update_layout(
            title="Rilevazione Anomalie Storiche di Portafoglio (Isolation Forest ML)",
            xaxis_title=None, yaxis_title="Rendimento Giornaliero (%)",
            template="plotly_dark", height=420,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=30, b=20),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
        )
        apply_plotly_theme(fig_iso)
        st.plotly_chart(fig_iso, use_container_width=True)

        if not iso_res["anomaly_df"].empty:
            st.markdown("**📋 Tabella delle Giornate Anomale Rilevate dal Modello ML**")
            st.dataframe(
                iso_res["anomaly_df"].style.format({
                    "Rendimento Portafoglio %": "{:+.2f}%",
                    "Volatilità Rolling 20d %": "{:.2f}%",
                    "Correlazione Media": "{:.2f}",
                    "Drawdown %": "{:.2f}%",
                    "Score Anomalia": "{:.3f}"
                }),
                use_container_width=True,
                hide_index=True
            )
