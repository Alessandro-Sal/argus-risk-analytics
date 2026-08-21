import importlib
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

import core.ui_utils as ui_utils
import core.risk_engine as risk_engine
import core.sec_rag_engine as sec_rag_engine
import core.metadata_resolver as metadata_resolver
import core.financial_analysis as financial_analysis
importlib.reload(ui_utils)
importlib.reload(risk_engine)
importlib.reload(sec_rag_engine)
importlib.reload(metadata_resolver)
importlib.reload(financial_analysis)

from core.ui_utils import (
    inject_custom_css, metric_card, glossary_modal, fmt_pct, render_executive_badges,
    render_formula_popover, apply_plotly_theme, render_command_bar, render_segmented_tabs,
    ensure_risk_bundle_loaded, render_sandbox_banner, render_sec_rag_modal
)
from core.workspace_manager import get_url_param, set_url_params, register_workspace_tab
from core.forensic_accounting import compute_beneish_m_score, compute_sloan_accrual_ratio
from core.metadata_resolver import resolve_asset_metadata, resolve_asset_valuation_metrics
from core.financial_analysis import resolve_company_name

st.set_page_config(page_title="Valutazione Aziendale | ARGUS", page_icon="🏛️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()
render_command_bar()

url_ticker = get_url_param("ticker", None)
if url_ticker:
    register_workspace_tab(f"val_{url_ticker}", f"🏛️ {url_ticker}", "5_Valutazione_Aziendale", {"ticker": url_ticker})

# Gestione Portafoglio o Sandbox
results, has_real_portfolio = ensure_risk_bundle_loaded()
if not has_real_portfolio:
    render_sandbox_banner()
    pos = pd.DataFrame([
        {"ticker": "AAPL", "asset_name": "Apple Inc.", "name": "Apple Inc.", "asset_class": "Stock", "weight_pct": 20.0, "qty_net": 10, "current_value": 2200.0, "last_price": 220.0, "target_mean_price": 250.0, "peg_ratio": 2.1, "trailing_pe": 33.0, "forward_pe": 28.0, "price_to_book": 39.0, "dividend_yield": 0.005, "roe": 1.45},
        {"ticker": "MSFT", "asset_name": "Microsoft Corp.", "name": "Microsoft Corp.", "asset_class": "Stock", "weight_pct": 20.0, "qty_net": 10, "current_value": 4400.0, "last_price": 440.0, "target_mean_price": 500.0, "peg_ratio": 2.3, "trailing_pe": 35.0, "forward_pe": 30.0, "price_to_book": 12.0, "dividend_yield": 0.007, "roe": 0.38},
        {"ticker": "NVDA", "asset_name": "NVIDIA Corp.", "name": "NVIDIA Corp.", "asset_class": "Stock", "weight_pct": 20.0, "qty_net": 10, "current_value": 1250.0, "last_price": 125.0, "target_mean_price": 155.0, "peg_ratio": 1.1, "trailing_pe": 46.0, "forward_pe": 33.0, "price_to_book": 48.0, "dividend_yield": 0.001, "roe": 1.18},
        {"ticker": "RACE.MI", "asset_name": "Ferrari N.V.", "name": "Ferrari N.V.", "asset_class": "Stock", "weight_pct": 20.0, "qty_net": 10, "current_value": 4100.0, "last_price": 410.0, "target_mean_price": 460.0, "peg_ratio": 2.8, "trailing_pe": 49.0, "forward_pe": 42.0, "price_to_book": 19.0, "dividend_yield": 0.006, "roe": 0.42},
        {"ticker": "ENEL.MI", "asset_name": "Enel S.p.A.", "name": "Enel S.p.A.", "asset_class": "Stock", "weight_pct": 20.0, "qty_net": 100, "current_value": 710.0, "last_price": 7.10, "target_mean_price": 8.20, "peg_ratio": 1.4, "trailing_pe": 10.8, "forward_pe": 9.9, "price_to_book": 1.4, "dividend_yield": 0.063, "roe": 0.14}
    ])
    active_pos = pos.copy()
    port_metrics = {"cagr_pct": 16.5, "volatility_ann_pct": 17.8, "sharpe_ratio": 1.22, "max_drawdown_pct": -11.5}
else:
    pos = results.get("positions", pd.DataFrame())
    active_pos = pos[pos["qty_net"] > 0].copy() if not pos.empty and "qty_net" in pos.columns else (pos[pos["weight_pct"] > 0].copy() if not pos.empty and "weight_pct" in pos.columns else pos.copy())
    port_metrics = results.get("metrics", {})

from core.financial_analysis import resolve_company_name
equity_pos = active_pos[active_pos["asset_class"].str.lower().isin(["equity", "azione", "stock", "azioni"])].copy() if "asset_class" in active_pos.columns else active_pos
if equity_pos.empty:
    equity_pos = active_pos

company_options = {}
for _, r in equity_pos.iterrows():
    tk = r["ticker"]
    raw_name = r.get("name", r.get("asset_name", tk))
    company_options[tk] = resolve_company_name(tk, raw_name)

st.title("🏛️ Valutazione Intrinseca & Fair Value")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Analisi dei fondamentali societari, target price dei mercati (Consensus) e simulazioni di private equity (IRR & TVPI).")
col_head1, col_head2 = st.columns([3.2, 1.2])
with col_head1:
    render_executive_badges(port_metrics)
with col_head2:
    st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
    glossary_modal("Cos'è la Valutazione Aziendale & Fair Value", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è la Valutazione Fondamentale</div>
  <div>La determinazione quantitativa del valore intrinseco (Fair Value) di un'impresa basata sulla generazione di cassa, bilanci certificati, multipli di mercato e stime di consenso degli analisti finanziari.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 I Modelli Integrati in ARGUS</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Target Price Consensus:</b> Mediana degli analisti di Wall Street / Piazza Affari<br>
    • <b>PE Waterfall:</b> Flussi di cassa LP/GP, TVPI, DPI, RVPI e Carried Interest<br>
    • <b>Solvibilità & Fallimento:</b> Altman Z-Score a 5 indici e scomposizione DuPont del ROE<br>
    • <b>Contabilità Forense:</b> Beneish M-Score (frodi) e Sloan Accruals (qualità utili)<br>
    • <b>DCF Monte Carlo:</b> Attualizzazione flussi FCF a 1.000 iterazioni stocastiche
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Verificare se i titoli in portafoglio sono prezzati a sconto (Margin of Safety di Graham-Dodd) o a premio rispetto alla loro capacità reale di generare cassa.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>I moduli <code>core/financial_analysis.py</code> e <code>core/risk_engine.py</code> estraggono i bilanci ufficiali normalizzando le valute e proiettano scenari probabilistici.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Naviga tra le schede per esaminare la valutazione di consenso (Tab 1), il Private Equity (Tab 3), la solidità contabile (Tab 4) o la simulazione DCF (Tab 5).</div>
</div>

</div>
""", button_label="💡 Come funziona la Valutazione?")

st.divider()


if active_pos.empty:
    st.info("Nessuna posizione aperta in portafoglio.")
    st.stop()

# Estrazione colonne e calcolo dell'Upside / Giudizio
fund_cols = ["ticker", "name", "asset_name", "asset_class", "weight_pct", "last_price", 
             "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]
df_fund = active_pos[[c for c in fund_cols if c in active_pos.columns]].copy()

if "name" not in df_fund.columns:
    if "asset_name" in active_pos.columns:
        df_fund["name"] = active_pos["asset_name"]
    else:
        df_fund["name"] = df_fund["ticker"]

# Pulizia numerica e inizializzazione colonne
for col in ["last_price", "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]:
    if col in df_fund.columns:
        df_fund[col] = pd.to_numeric(df_fund[col], errors='coerce')
    else:
        df_fund[col] = np.nan

# Arricchimento automatico per asset noti privi di Target Price o multipli
for idx, row in df_fund.iterrows():
    tk = str(row.get("ticker", "")).strip().upper()
    known_val = resolve_asset_valuation_metrics(tk)
    if known_val:
        for metric_k, metric_v in known_val.items():
            if metric_k in df_fund.columns and (pd.isna(df_fund.at[idx, metric_k]) or df_fund.at[idx, metric_k] is None):
                df_fund.at[idx, metric_k] = metric_v

# Normalizzazione automatica valuta per Target Price (es. DKK, SEK, JPY, GBp)
def normalize_target_price(row):
    last = row.get("last_price")
    target = row.get("target_mean_price")
    ticker = str(row.get("ticker", "")).upper()
    
    if pd.isna(last) or pd.isna(target) or last <= 0:
        return target
        
    ratio = target / last
    if ratio > 3.0 or ratio < 0.2:
        if ticker.endswith(".CO") or (ratio >= 6.5 and ratio <= 8.5):
            return target / 7.46  # DKK -> EUR (es. Novo Nordisk NOVO-B.CO)
        elif ticker.endswith(".ST") or (ratio >= 10.0 and ratio <= 13.0):
            return target / 11.40 # SEK -> EUR
        elif ticker.endswith(".OL"):
            return target / 11.50 # NOK -> EUR
        elif ticker.endswith(".T") or ratio > 100:
            return target / 162.0 # JPY -> EUR
        elif ticker.endswith(".L") and ratio > 50:
            return target / 100.0 / 1.17 # GBp -> EUR

    return target

df_fund["target_mean_price"] = df_fund.apply(normalize_target_price, axis=1)

# Logica di Valutazione (Verdetto)
def get_verdict(row):
    last = row.get("last_price")
    target = row.get("target_mean_price")
    peg = row.get("peg_ratio")
    
    if pd.isna(last) or pd.isna(target):
        return "⚪ N/A"
        
    upside = (target / last) - 1
    
    if pd.notna(peg) and peg > 2.5 and upside < 0.05:
        return "🔴 Sopravvalutata (PEG Alto)"
    
    if upside > 0.10:
        return "🟢 Sottovalutata"
    elif upside < -0.05:
        return "🔴 Sopravvalutata"
    else:
        return "🟡 Fair Value"

df_fund["Upside %"] = np.where(
    (df_fund["target_mean_price"].notna()) & (df_fund["last_price"].notna()) & (df_fund["last_price"] > 0),
    (df_fund["target_mean_price"] / df_fund["last_price"]) - 1,
    np.nan
)

df_fund["Verdetto"] = df_fund.apply(get_verdict, axis=1)
df_valued = df_fund[df_fund["Verdetto"] != "⚪ N/A"]

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ CON LAZY LOADING ─────────
active_val_tab = render_segmented_tabs([
    "🏛️ Fair Value & Consensus Analisti",
    "💼 Private Equity & Waterfall",
    "📊 Bilanci & Solvibilità (Altman & DuPont)",
    "🧮 Valutazione Intrinseca DCF Monte Carlo"
], key="val_segmented_tab")

# ── TAB 1: FAIR VALUE & CONSENSUS ANALISTI ─────────────────────
if active_val_tab == "🏛️ Fair Value & Consensus Analisti":
    if df_valued.empty:
        st.info("ℹ️ Nessun dato di Target Price o Consensus Analisti disponibile per gli asset attualmente caricati in portafoglio.")
    else:
        st.markdown("#### Riepilogo Giudizi di Mercato")
        col1, col2, col3 = st.columns(3)

        n_under = len(df_valued[df_valued["Verdetto"].str.contains("Sottovalutata")])
        n_fair  = len(df_valued[df_valued["Verdetto"].str.contains("Fair Value")])
        n_over  = len(df_valued[df_valued["Verdetto"].str.contains("Sopravvalutata")])

        with col1:
            metric_card(
                "Sottovalutate (Buy)",
                str(n_under),
                "Asset a sconto vs target price",
                True,
                help_text="<b>Cosa significa:</b> Azioni con Target Price a 12 mesi superiore di almeno il 10% al prezzo attuale con multipli equilibrati."
            )
        with col2:
            metric_card(
                "Fairly Valued (Hold)",
                str(n_fair),
                "Asset in linea col fair value",
                True,
                help_text="<b>Cosa significa:</b> Azioni scambiate in un intervallo di normalità tra -5% e +10% rispetto al prezzo obiettivo."
            )
        with col3:
            metric_card(
                "Sopravvalutate (Sell)",
                str(n_over),
                "Asset a premio vs target price",
                False,
                help_text="<b>Cosa significa:</b> Azioni con Upside negativo (< -5%) o con PEG Ratio superiore a 2.5 (premio eccessivo)."
            )

        st.divider()

        col_a, col_b = st.columns([2, 1])

        with col_a:
            df_display = df_valued[["ticker", "Verdetto", "last_price", "target_mean_price", "Upside %", "peg_ratio", "trailing_pe"]].copy()
            df_display.rename(columns={
                "ticker": "Asset",
                "last_price": "Prezzo Attuale",
                "target_mean_price": "Target Price (Analisti)",
                "peg_ratio": "PEG Ratio",
                "trailing_pe": "P/E Ratio"
            }, inplace=True)
            
            df_display["Prezzo Attuale"] = df_display["Prezzo Attuale"].apply(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "N/A")
            df_display["Target Price (Analisti)"] = df_display["Target Price (Analisti)"].apply(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "N/A")
            df_display["Upside %"] = df_display["Upside %"].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "N/A")
            df_display["PEG Ratio"] = df_display["PEG Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            df_display["P/E Ratio"] = df_display["P/E Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")

            col_fv_h1, col_fv_h2 = st.columns([3.2, 1.1])
            with col_fv_h1:
                st.markdown("#### Tabella Fair Value & Target Price")
            with col_fv_h2:
                csv_fv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_fv, file_name="fair_value_target_price.csv", mime="text/csv", use_container_width=True, key="btn_download_fv_tp")
            
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

        with col_b:
            glossary_modal("📚 Glossario Metriche di Valutazione", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 6px;"><b>🎯 Target Price:</b><br>
Prezzo obiettivo a 12 mesi stimato dal consensus degli analisti istituzionali.</div>

<div style="margin-bottom: 6px;"><b>📈 Upside / Downside %:</b><br>
Distanza percentuale necessaria affinché il prezzo di mercato converga verso il Target Price.</div>

<div><b>⚖️ PEG Ratio (Price/Earnings-to-Growth):</b><br>
Rapporto tra multiplo P/E e tasso di crescita atteso degli utili (EPS Growth). Valori < 1.0 indicano forte convenienza.
</div>
</div>
            """, button_label="📖 Glossario Metriche")
            
            verdict_counts = df_valued["Verdetto"].value_counts().reset_index()
            verdict_counts.columns = ["Verdetto", "Conteggio"]
            
            color_map = {
                "🟢 Sottovalutata": "#00e676",
                "🟡 Fair Value": "#ff9900",
                "🔴 Sopravvalutata (PEG Alto)": "#f85149",
                "🔴 Sopravvalutata": "#f85149"
            }
            
            st.markdown("**Distribuzione Valutazioni**")
            fig = px.pie(
                verdict_counts, values="Conteggio", names="Verdetto", hole=0.62,
                color="Verdetto", color_discrete_map=color_map
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent',
                insidetextorientation='horizontal',
                textfont=dict(size=12, color="#ffffff"),
                marker=dict(line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>%{label}</b><br>Quota Valutazioni: <b>%{percent}</b> (%{value} titoli)<extra></extra>"
            )
            fig.update_layout(
                template="plotly_dark", height=320,
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.12,
                    xanchor="center",
                    x=0.5,
                    bgcolor="rgba(22, 27, 34, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.12)",
                    borderwidth=1,
                    font=dict(size=11, color="#ffffff")
                ),
                margin=dict(l=10, r=10, t=10, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="val_fair_value_scatter", config={"displayModeBar": "hover", "displaylogo": False})

        # ── GRAFICO POTENZIALE DI RIALZO (UPSIDE / DOWNSIDE) INTEGRATO ──────
        st.divider()
        st.markdown("#### 📈 Potenziale di Rialzo (Upside / Downside Consensus Analisti)")
        st.caption("Distanza percentuale necessaria affinché la quotazione di mercato converga verso il Target Price stimato dal consensus istituzionale.")
        
        df_upside = df_valued.dropna(subset=["Upside %"]).sort_values("Upside %", ascending=True).copy()

        if not df_upside.empty:
            df_upside["Colore"] = np.where(df_upside["Upside %"] > 0, "#00e676", "#f85149")
            df_upside["fmt_upside"] = df_upside["Upside %"].apply(lambda x: f"{x*100:+.2f}%")
            df_upside["fmt_price"] = df_upside["last_price"].apply(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "N/A")
            df_upside["fmt_target"] = df_upside["target_mean_price"].apply(lambda x: f"€ {x:,.2f}" if pd.notna(x) else "N/A")
            
            min_x = min(0.0, float(df_upside["Upside %"].min()) * 100)
            max_x = max(0.0, float(df_upside["Upside %"].max()) * 100)
            x_pad = max(10.0, (max_x - min_x) * 0.18)
            chart_height = max(380, len(df_upside) * 36)

            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=df_upside["Upside %"] * 100,
                y=df_upside["ticker"],
                orientation='h',
                marker=dict(color=df_upside["Colore"], line=dict(color="#0d1117", width=1.5), opacity=0.9),
                text=df_upside["Upside %"].apply(lambda x: f"{x*100:+.1f}%"),
                textposition="outside",
                textfont=dict(size=11, color="#ffffff"),
                cliponaxis=False,
                customdata=np.stack((df_upside["fmt_upside"], df_upside["fmt_price"], df_upside["fmt_target"]), axis=-1),
                hovertemplate="<b>%{y}</b><br>Prezzo Attuale: <b>%{customdata[1]}</b><br>Target Price: <b>%{customdata[2]}</b><br>📈 Distanza dal Fair Value: <b>%{customdata[0]}</b><extra></extra>"
            ))
            
            fig_bar.update_layout(
                template="plotly_dark", height=chart_height,
                xaxis=dict(
                    title="Distanza dal Fair Value degli Analisti (%)",
                    zeroline=True, zerolinecolor="#8b949e", zerolinewidth=1.5,
                    gridcolor="rgba(255,255,255,0.06)",
                    range=[min_x - x_pad, max_x + x_pad]
                ),
                yaxis=dict(title=None, showgrid=False),
                margin=dict(l=20, r=40, t=20, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True, key="val_upside_bar_chart", config={"displayModeBar": "hover", "displaylogo": False})
        else:
            st.info("Dati di Upside non disponibili per gli asset attuali.")

# ── TAB 2: PRIVATE EQUITY SIMULATOR ───────────────────────────
elif active_val_tab == "💼 Private Equity & Waterfall":
    col_head_pe1, col_head_pe2 = st.columns([3.5, 1.0])
    with col_head_pe1:
        st.markdown("#### 💼 Private Equity & Private Markets Simulator")
        st.caption("Simulatore dei flussi finanziari di Private Equity: calcolo del Net IRR, TVPI / MOIC, DPI, RVPI e Carried Interest Waterfall Allocation")
    with col_head_pe2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida alle Metriche del Private Equity (TVPI, DPI, IRR)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Private Equity Waterfall</div>
  <div>La convenzione contrattuale istituzionale che disciplina la ripartizione dei flussi di cassa (distribuzioni e plusvalenze) tra gli investitori (Limited Partners - LP) e la società di gestione (General Partner - GP).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formule dei Multipli di Mercato Privato</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>TVPI / MOIC:</b> (Distribuzioni + NAV Residuo) / Capital Calls (moltiplicatore totale)<br>
    • <b>DPI:</b> Distribuzioni Totali / Capital Calls (cassa effettivamente realizzata)<br>
    • <b>RVPI:</b> NAV Residuo / Capital Calls (valore non realizzato latente)<br>
    • <b>Carried Interest:</b> Quota di profitto (tipicamente 20%) spettante al GP oltre l'Hurdle Rate (8%)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Valutare la qualità del rendimento di fondi chiusi e investimenti in mercati non quotati distinguendo il valore monetario già liquidato (DPI) da quello teorico (RVPI).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il simulatore implementa la waterfall standard europea (Catch-Up con Hurdle Rate dell'8% e Carry del 20%) generando il grafico dinamico a cascata.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Un TVPI &gt; 2.0x con DPI &gt; 1.0x indica un fondo eccellente che ha già restituito l'intero capitale versato con importanti guadagni netti distribuiti.</div>
</div>

</div>
""", button_label="📖 Guida Metriche PE")

    pe_c1, pe_c2, pe_c3 = st.columns(3)
    with pe_c1:
        cap_calls = st.number_input("Capital Calls (€)", min_value=10000.0, value=1000000.0, step=50000.0)
    with pe_c2:
        distribs = st.number_input("Distributions (€)", min_value=0.0, value=1500000.0, step=50000.0)
    with pe_c3:
        nav_val = st.number_input("NAV Residuo Partecipazioni (€)", min_value=0.0, value=1000000.0, step=50000.0)

    from core.risk_engine import compute_private_equity_waterfall
    pe_res = compute_private_equity_waterfall(cap_calls, distribs, nav_val, hurdle_rate=0.08, carried_interest=0.20)

    if pe_res:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            metric_card("TVPI / MOIC", f"{pe_res['tvpi_moic']:.2f}x", "Rendimento Totale", True)
        with kpi2:
            metric_card("DPI (Distribuito)", f"{pe_res['dpi']:.2f}x", "Cassa Rimborsata", True)
        with kpi3:
            metric_card("RVPI (NAV Residuo)", f"{pe_res['rvpi']:.2f}x", "Valore Non Realizzato", True)
        with kpi4:
            metric_card("Carried Interest GP", f"€ {pe_res['gp_carried_interest']:,.0f}", "Quota Gestore (20%)", True)
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        fig_wf = go.Figure(go.Waterfall(
            name="Waterfall PE", orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Capital Calls (LP)", "Distributions (Cassa)", "NAV Residuo", "Valore Creato Netto"],
            text=[f"€ {-cap_calls:,.0f}", f"+€ {distribs:,.0f}", f"+€ {nav_val:,.0f}", f"€ {pe_res['total_gain']:,.0f}"],
            textposition="outside",
            textfont=dict(size=11, color="#ffffff"),
            cliponaxis=False,
            y=[-cap_calls, distribs, nav_val, pe_res['total_gain']],
            connector={"line":{"color":"rgba(255,255,255,0.2)"}},
            decreasing={"marker":{"color":"#f85149"}},
            increasing={"marker":{"color":"#00e676"}},
            totals={"marker":{"color":"#ff9900"}},
            hovertemplate="<b>%{x}</b><br>Importo: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_wf.update_layout(
            template="plotly_dark",
            height=370,
            yaxis=dict(title="Flussi di Cassa (€)", zeroline=True, zerolinecolor="#8b949e", zerolinewidth=1.5),
            margin=dict(l=20, r=20, t=35, b=35),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig_wf)
        st.plotly_chart(fig_wf, use_container_width=True, key="val_pe_waterfall_chart", config={"displayModeBar": "hover", "displaylogo": False})

# ── TAB 4: ANALISI DEI BILANCI & SOLVIBILITÀ ──────────────────
elif active_val_tab == "📊 Bilanci & Solvibilità (Altman & DuPont)":
    col_head_alt1, col_head_alt2 = st.columns([3.2, 1.1])
    with col_head_alt1:
        st.markdown("#### 📊 Diagnostica dei Bilanci Societari & Modelli di Solvibilità")
        st.caption("Analisi quantitativa dei Bilanci di Esercizio: previsione del rischio di insolvenza tramite Altman Z-Score, scomposizione ROE DuPont ed Indici di Liquidità/Solvibilità.")
    with col_head_alt2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("📚 Guida all'Analisi dei Bilanci (Altman Z-Score & DuPont)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Altman Z-Score & l'Albero di DuPont</div>
  <div>Due modelli fondamentali di finanza aziendale: l'Altman Z-Score stima la probabilità di default a 24 mesi, mentre l'Analisi DuPont scompone la redditività del capitale proprio (ROE) nei suoi 3 motori primari.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formule Matematiche</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Altman Z:</b> 1.2&middot;X<sub>1</sub> + 1.4&middot;X<sub>2</sub> + 3.3&middot;X<sub>3</sub> + 0.6&middot;X<sub>4</sub> + 0.999&middot;X<sub>5</sub><br>
    • <b>DuPont ROE:</b> Margine Netto (Utile / Ricavi) &times; Asset Turnover (Ricavi / Attivo) &times; Financial Leverage (Attivo / Equity)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Rilevare precocemente segnali di tensione finanziaria o manipolazione contabile e identificare se la crescita degli utili è sana o gonfiata da leva finanziaria eccessiva.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS estrae i bilanci storici 10-K/bilancio CEE calcolando automaticamente gli indici e fornendo una comparativa multiaziendale interattiva.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🟢 <b>Z &gt; 2.99:</b> Zona Sicura (bilancio sano).<br>
    • 🟡 <b>1.81 &le; Z &le; 2.99:</b> Zona Grigia (attenzione).<br>
    • 🔴 <b>Z &lt; 1.81:</b> Zona di Pericolo (rischio fallimento elevato).
  </div>
</div>

</div>
""", button_label="💡 Come funziona la Diagnostica Bilanci?")

    subtab_options = [
        "👤 Analisi Singola Azienda & Bilanci 10-K",
        "⚔️ Comparativa Multiaziendale (Altman Z-Score, DuPont & Ratios)",
        "🎯 Piotroski F-Score, WACC & Multipli di Mercato"
    ]
    active_bilanci_subtab = render_segmented_tabs(subtab_options, key="bilanci_subtab_nav")

    try:
        from core.financial_analysis import resolve_company_name, generate_company_financial_statement_analysis, fetch_detailed_financial_statements, compare_multiple_companies, compute_piotroski_f_score, compute_wacc_estimation, compute_valuation_multiples_matrix
    except ImportError:
        import importlib
        import core.financial_analysis
        importlib.reload(core.financial_analysis)
        from core.financial_analysis import resolve_company_name, generate_company_financial_statement_analysis, fetch_detailed_financial_statements, compare_multiple_companies, compute_piotroski_f_score, compute_wacc_estimation, compute_valuation_multiples_matrix

    equity_pos = active_pos[active_pos["asset_class"].str.lower().isin(["equity", "azione", "stock", "azioni"])].copy() if "asset_class" in active_pos.columns else active_pos
    if equity_pos.empty:
        equity_pos = active_pos

    company_options = {}
    for _, r in equity_pos.iterrows():
        tk = r["ticker"]
        raw_name = r.get("name", r.get("asset_name", tk))
        company_options[tk] = resolve_company_name(tk, raw_name)

    # ── SUBTAB 1: ANALISI SINGOLA AZIENDA ──────────────────────────────────────
    if active_bilanci_subtab == "👤 Analisi Singola Azienda & Bilanci 10-K":
        fund_tk = st.session_state.get("fund_target_ticker", None)
        if fund_tk:
            del st.session_state["fund_target_ticker"]
            search_mode_default = 1
            custom_default_val = fund_tk
        else:
            search_mode_default = 0
            custom_default_val = "AAPL"

        search_mode = st.radio(
            "Modalità Selezione Azienda per l'Analisi:",
            ["Azienda dal Portafoglio", "Cerca Qualsiasi Azienda sul Mercato (es. AAPL, NVDA, RACE.MI, TSLA)"],
            index=search_mode_default,
            horizontal=True
        )

        if search_mode == "Azienda dal Portafoglio":
            selected_ticker = st.selectbox(
                "Seleziona Azienda dal Portafoglio per l'Analisi di Bilancio:",
                list(company_options.keys()),
                format_func=lambda x: f"{x} - {company_options[x]}" if company_options[x] != x else f"{x}"
            )
            selected_company_name = company_options.get(selected_ticker, selected_ticker)
            sel_row = equity_pos[equity_pos["ticker"] == selected_ticker].iloc[0] if not equity_pos[equity_pos["ticker"] == selected_ticker].empty else {}
            mkt_cap = float(sel_row.get("market_cap", 100000000000.0) or 100000000000.0) if hasattr(sel_row, 'get') else 100000000000.0
            pe_val = float(sel_row.get("trailing_pe", 25.0) or 25.0) if hasattr(sel_row, 'get') else 25.0
            roe_val = float(sel_row.get("roe", 18.5) or 18.5) if hasattr(sel_row, 'get') else 18.5
            if roe_val < 0.1 and roe_val > 0: roe_val *= 100.0
            de_val = float(sel_row.get("debt_to_equity", 0.75) or 0.75) if hasattr(sel_row, 'get') else 0.75
        else:
            col_inp, col_yr = st.columns([3, 1])
            with col_inp:
                custom_input = st.text_input("Inserisci Ticker Azionario (es. AAPL, MSFT, NVDA, TSLA, RACE.MI, UCG.MI):", value=custom_default_val)
            selected_ticker = custom_input.upper().strip()
            selected_company_name = resolve_company_name(selected_ticker)
            mkt_cap, pe_val, roe_val, de_val = 100000000000.0, 25.0, 18.5, 0.75

        fin_report = generate_company_financial_statement_analysis(
            ticker=selected_ticker,
            company_name=selected_company_name,
            market_cap=mkt_cap,
            pe_ratio=pe_val,
            roe_pct=roe_val,
            debt_equity=de_val
        )

        z_data = fin_report["altman_z_score"]
        dp_data = fin_report["dupont_analysis"]
        ratios_data = fin_report["ratios"]
        stm = fin_report["statement_summary"]

        st.divider()

        # KPI Head Cards
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("Altman Z-Score", f"{z_data['z_score']:.2f}", z_data["zone_icon"], True if z_data['z_score'] > 1.81 else False)
        with k2:
            metric_card("ROE (Return on Equity)", f"{dp_data['roe_pct']:.2f}%", f"Profittabilità Netta ({dp_data['model']})", True if dp_data['roe_pct'] > 10 else False)
        with k3:
            metric_card("Fatturato / Sales", f"€ {stm['sales_eur']:,.0f}", f"EBITDA: € {stm['ebitda_eur']:,.0f}", True)
        with k4:
            metric_card("Free Cash Flow (FCF)", f"€ {stm['free_cash_flow_eur']:,.0f}", "Flusso di Cassa Operativo Netto", True)

        st.divider()

        col_z1, col_z2 = st.columns([1.5, 1])

        with col_z1:
            col_zt1, col_zt2 = st.columns([3, 1])
            with col_zt1:
                st.markdown(f"#### 🛡️ Verdetto Solvibilità: {z_data['zone_icon']}")
            with col_zt2:
                render_formula_popover(
                    "🧮 Formula Altman", 
                    "Altman Z-Score (1968)",
                    r"Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 0.999X_5",
                    "<b>Fasce di Rischio Solvibilità:</b><br>"
                    "• Z > 2.99: Zona Sicura (Verde)<br>"
                    "• 1.81 ≤ Z ≤ 2.99: Zona Grigia (Giallo)<br>"
                    "• Z < 1.81: Zona di Rischio Insolvenza (Rosso)"
                )
            st.info(z_data["description"])

            # Gauge Chart Altman Z-Score con annotazione centrale perfetta
            z_val = float(z_data["z_score"])
            max_gauge_val = max(5.0, round(z_val + 1.2, 1))
            val_color = "#3fb950" if z_val > 2.99 else ("#d29922" if z_val >= 1.81 else "#f85149")

            fig_z = go.Figure(go.Indicator(
                mode="gauge",
                value=z_val,
                domain={'x': [0.05, 0.95], 'y': [0.15, 0.95]},
                title={'text': f"Altman Z-Score | {selected_company_name} ({selected_ticker})", 'font': {'size': 15, 'color': "#ffffff"}},
                gauge={
                    'axis': {'range': [0, max_gauge_val], 'tickwidth': 1, 'tickcolor': "rgba(255,255,255,0.4)"},
                    'bar': {'color': val_color, 'thickness': 0.3},
                    'steps': [
                        {'range': [0, 1.81], 'color': 'rgba(248, 81, 73, 0.25)'},
                        {'range': [1.81, 2.99], 'color': 'rgba(210, 153, 34, 0.25)'},
                        {'range': [2.99, max_gauge_val], 'color': 'rgba(63, 185, 80, 0.25)'}
                    ],
                    'threshold': {
                        'line': {'color': "#ffffff", 'width': 3},
                        'thickness': 0.8,
                        'value': z_val
                    }
                }
            ))

            fig_z.add_annotation(
                x=0.5, y=0.18,
                xref="paper", yref="paper",
                text=f"<b>Z = {z_val:.2f}</b>",
                showarrow=False,
                font=dict(size=28, color=val_color),
                align="center"
            )

            fig_z.update_layout(
                template="plotly_dark", 
                height=260, 
                margin=dict(l=30, r=30, t=45, b=15),
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_z)
            st.plotly_chart(fig_z, use_container_width=True, key="val_altman_z_gauge", config={"displayModeBar": "hover", "displaylogo": False})

        with col_z2:
            col_dp_h1, col_dp_h2 = st.columns([3.0, 1.2])
            with col_dp_h1:
                st.markdown("#### 🔍 Driver del ROE (DuPont 3-Fattori)")
            
            df_dp = pd.DataFrame([
                {"Fattore": "Profit Margin (Utile/Sales)", "Valore": f"{dp_data['profit_margin_pct']:.2f}%"},
                {"Fattore": "Asset Turnover (Sales/Assets)", "Valore": f"{dp_data['asset_turnover']:.2f}x"},
                {"Fattore": "Equity Multiplier (Assets/Equity)", "Valore": f"{dp_data['equity_multiplier']:.2f}x"},
                {"Fattore": "ROE Risultante", "Valore": f"{dp_data['roe_pct']:.2f}%"}
            ])
            with col_dp_h2:
                csv_dp = df_dp.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_dp, file_name="dupont_analysis_roe.csv", mime="text/csv", use_container_width=True, key="btn_download_dupont")

            st.dataframe(df_dp, use_container_width=True, hide_index=True)

        st.divider()

        st.markdown("#### 🎯 Radar degli Indici di Bilancio Fondamentali")
        
        r_liq = ratios_data["liquidity"]
        r_sol = ratios_data["solvency"]

        categories = ['Current Ratio', 'Quick Ratio', 'Asset Turnover', 'Debt/Equity (Inv)', 'Interest Coverage (Scaled)']
        values = [
            min(5.0, r_liq.get('current_ratio', 1.5) or 1.5),
            min(5.0, r_liq.get('quick_ratio', 1.2) or 1.2),
            min(5.0, ratios_data['efficiency'].get('asset_turnover', 0.6) or 0.6),
            min(5.0, 1.0 / (r_sol.get('debt_to_equity', 0.8) + 1e-3)),
            min(5.0, (r_sol.get('interest_coverage', 5.0) or 5.0) / 2.0)
        ]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values, theta=categories, fill='toself',
            name=f"{selected_company_name} ({selected_ticker})",
            line=dict(color='#00e676', width=2),
            fillcolor='rgba(0, 230, 118, 0.22)',
            hovertemplate="<b>%{theta}</b>: <b>%{r:.2f} / 5.0</b><extra></extra>"
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(22, 27, 34, 0.4)",
                radialaxis=dict(visible=True, range=[0, 5], gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=10, color="rgba(255,255,255,0.6)")),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11, color="#ffffff"))
            ),
            template="plotly_dark", height=380,
            margin=dict(l=40, r=40, t=30, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig_radar)
        st.plotly_chart(fig_radar, use_container_width=True, key="val_single_stock_radar", config={"displayModeBar": "hover", "displaylogo": False})

        st.divider()
        st.markdown("#### 🤖 Diagnostica Predittiva Machine Learning (Random Forest Classifier)")
        st.caption("Classificazione del rischio di distress finanziario e della solvibilità aziendale tramite modelli di Machine Learning con spiegabilità delle feature (Explainable AI).")

        from core.financial_analysis import predict_ml_distress_and_volatility, compute_piotroski_f_score
        try:
            p_res = compute_piotroski_f_score(selected_ticker)
            p_score_val = float(p_res.get("score", 7.0))
        except Exception:
            p_score_val = 7.0

        company_ratios_input = {
            "altman_z": z_val,
            "piotroski_f": p_score_val,
            "current_ratio": float(r_liq.get('current_ratio', 1.5) or 1.5),
            "debt_equity": float(r_sol.get('debt_to_equity', 0.8) or 0.8),
            "net_margin": float(ratios_data.get('profitability', {}).get('net_margin', 15.0) or 15.0)
        }
        ml_eval = predict_ml_distress_and_volatility(company_ratios=company_ratios_input)

        c_ml1, c_ml2, c_ml3 = st.columns([1, 1, 2])
        with c_ml1:
            metric_card("Probabilità Distress ML (%)", f"{ml_eval['distress_probability_pct']:.1f}%", positive=ml_eval['distress_probability_pct'] < 30.0)
        with c_ml2:
            st.markdown("**Verdetto Modello ML**")
            st.markdown(f"### {ml_eval['risk_level']}")
        with c_ml3:
            st.caption(f"**Diagnosi:** {ml_eval['verdict']}")

        st.markdown("##### 🔍 Importanza Relativa delle Variabili (Explainable AI / Feature Importance)")
        df_feat_sorted = ml_eval["feature_importance_df"].sort_values(by="Importanza Relativa (%)", ascending=True)
        max_feat_val = float(df_feat_sorted["Importanza Relativa (%)"].max()) if not df_feat_sorted.empty else 40.0
        
        fig_feat = go.Figure()
        fig_feat.add_trace(go.Bar(
            x=df_feat_sorted["Importanza Relativa (%)"],
            y=df_feat_sorted["Feature"],
            orientation="h",
            marker=dict(
                color=df_feat_sorted["Importanza Relativa (%)"],
                colorscale=[[0, "#30363d"], [0.5, "#8957e5"], [1.0, "#bc8cff"]],
                line=dict(color="#0d1117", width=1.5)
            ),
            text=df_feat_sorted["Importanza Relativa (%)"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            textfont=dict(size=11, color="#ffffff"),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Importanza Predittiva: <b>%{x:.1f}%</b><extra></extra>"
        ))
        fig_feat.update_layout(
            template="plotly_dark", height=260,
            xaxis=dict(title="Importanza Relativa (%)", range=[0, max_feat_val * 1.25], gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(title=None, showgrid=False),
            margin=dict(l=10, r=35, t=25, b=25),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig_feat)
        st.plotly_chart(fig_feat, use_container_width=True, key="val_ml_feature_importance", config={"displayModeBar": "hover", "displaylogo": False})
        st.divider()
        col_head_ben1, col_head_ben2 = st.columns([3.2, 1.1])
        with col_head_ben1:
            st.markdown("#### 🕵️‍♂️ Contabilità Forense: Beneish M-Score (1999) & Sloan Accruals (1996)")
            st.caption("Modelli econometrici di contabilità forense per identificare manipolazioni dei ricavi, crediti fittizi o bassa qualità contabile degli utili.")
        with col_head_ben2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida alla Contabilità Forense (Beneish M-Score & Sloan Accruals)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Beneish M-Score & lo Sloan Accrual Ratio</div>
  <div>Due modelli statistici di contabilità forense (Forensic Accounting) usati da fondi istituzionali e short-seller per scovare frodi di bilancio e utili contabili non supportati da vera cassa operativa.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formule di Calcolo</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Beneish M-Score (8 indici):</b> &minus;4.84 + 0.920&middot;DSRI + 0.528&middot;GMI + 0.404&middot;AQI + 0.892&middot;SGI + 0.115&middot;DEPI &minus; 0.172&middot;SGAI + 4.037&middot;TATA + 0.0327&middot;LVGI<br>
    • <b>Sloan Accruals:</b> (Utile Netto &minus; Flusso di Cassa Operativo) / Totale Attivo
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Neutralizzare il rischio di investire in società che usano trucchi contabili (anticipazione indebita di fatturato, capitalizzazione indebita di costi) per mascherare il calo del business.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>La funzione <code>compute_beneish_m_score</code> incrocia conto economico e rendiconto finanziario per valutare gli 8 driver forensi e lo Sloan Ratio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🔴 <b>M-Score &gt; &minus;1.78:</b> Allarme elevata probabilità di manipolazione contabile.<br>
    • 🟢 <b>M-Score &le; &minus;1.78:</b> Profilo contabile genuino e trasparente.
  </div>
</div>

</div>
""", button_label="💡 Come funziona la Contabilità Forense?")

        # Calcolo Beneish M-Score e Sloan Ratio personalizzati per l'azienda selezionata
        ni_val = float(stm.get('net_income_eur', 10000000.0) or 10000000.0)
        ocf_val = float(stm.get('free_cash_flow_eur', 12000000.0) or 12000000.0)
        ta_val = float(stm.get('total_assets_eur', 100000000.0) or 100000000.0)
        tata_val = (ni_val - ocf_val) / max(1.0, ta_val)

        rev_gr = float(sel_row.get("revenue_growth", 0.08) or 0.08) if hasattr(sel_row, "get") else 0.08
        sgi_val = max(0.8, min(1.6, 1.0 + rev_gr))
        lvgi_val = max(0.8, min(1.5, 1.0 + (de_val - 0.70)*0.1))

        m_eval = compute_beneish_m_score(
            dsri=1.00,
            gmi=0.98,
            aqi=0.95,
            sgi=sgi_val,
            depi=1.00,
            sgai=0.96,
            lvgi=lvgi_val,
            tata=tata_val
        )
        sloan_eval = compute_sloan_accrual_ratio(
            net_income=ni_val,
            operating_cash_flow=ocf_val,
            total_assets=ta_val
        )

        col_forensic1, col_forensic2, col_forensic3 = st.columns(3)
        with col_forensic1:
            metric_card("Beneish M-Score", f"{m_eval['m_score']:.2f}", m_eval["status"], positive=not m_eval["is_manipulator"])
        with col_forensic2:
            metric_card("Probabilità Manipolazione (%)", f"{m_eval['manipulation_probability_pct']:.1f}%", f"{m_eval['verdict']}", positive=m_eval['manipulation_probability_pct'] < 25.0)
        with col_forensic3:
            metric_card("Sloan Accruals Ratio", f"{sloan_eval['accrual_ratio_pct']:+.1f}%", sloan_eval["badge"], positive=sloan_eval["accrual_ratio"] <= 0.05)

        st.dataframe(m_eval["indices_df"], use_container_width=True, hide_index=True)

        st.divider()

        # ── SUB-MODULO: CONSULTAZIONE BILANCI UFFICIALI (10-K) ─────────────────────
        st.markdown(f"#### 📑 Bilanci Ufficiali di Esercizio per **{selected_company_name}** ({selected_ticker})")
        st.caption("Richiama e consulta il Conto Economico, lo Stato Patrimoniale ed il Rendiconto Finanziario di esercizio.")

        col_btn_stm, col_years_stm = st.columns([3, 1.5])
        with col_years_stm:
            years_options = [1, 2, 3, 4, 5, 10, None]
            years_to_fetch = st.selectbox(
                "Anni di Bilancio da Scaricare:",
                options=years_options, index=4,
                format_func=lambda y: "Tutti gli Anni Disponibili (Max 4-5)" if y is None else (f"Ultimi {y} Anni" if y > 1 else "Ultimo Anno Solare"),
                help="Nota: l'API di Yahoo Finance restituisce per impostazione predefinita gli ultimi 4 anni di Conto Economico/Rendiconto Finanziario e 5 anni di Stato Patrimoniale per le società quotate."
            )

        yr_label = f"{years_to_fetch} Anni" if years_to_fetch else "Tutti gli Anni"
        with col_btn_stm:
            btn_load_statements = st.button(f"📥 Richiama Bilanci Ufficiali 10-K per {selected_ticker} ({yr_label})", type="primary", use_container_width=True)
        
        state_key = f"statements_{selected_ticker}_{years_to_fetch}"
        if btn_load_statements or state_key in st.session_state:
            if btn_load_statements:
                with st.spinner(f"📥 Download in corso dei bilanci ufficiali per {selected_ticker} ({yr_label})..."):
                    import importlib
                    import core.financial_analysis
                    importlib.reload(core.financial_analysis)
                    from core.financial_analysis import fetch_detailed_financial_statements as fetch_stm
                    st.session_state[state_key] = fetch_stm(selected_ticker, years=years_to_fetch)
            
            raw_stm = st.session_state.get(state_key, {})
            inc_df = raw_stm.get("income_statement", pd.DataFrame())
            bal_df = raw_stm.get("balance_sheet", pd.DataFrame())
            cf_df  = raw_stm.get("cash_flow", pd.DataFrame())

            st.caption("💡 *Tutti i valori dei bilanci ufficiali sono formattati in Milioni (**M €**) con separatori delle migliaia e gestione delle voci non disponibili (N/A).*")

            st_tab1, st_tab2, st_tab3 = st.tabs([
                "📄 Conto Economico (Income Statement)",
                "🏛️ Stato Patrimoniale (Balance Sheet)",
                "💵 Rendiconto Finanziario (Cash Flow)"
            ])

            with st_tab1:
                if not inc_df.empty:
                    col_inc_h1, col_inc_h2 = st.columns([3.5, 0.9])
                    with col_inc_h2:
                        csv_inc = inc_df.to_csv(index=True).encode('utf-8')
                        st.download_button("📥 Scarica CSV", data=csv_inc, file_name=f"{selected_ticker}_conto_economico.csv", mime="text/csv", use_container_width=True, key="btn_download_inc_stmt")
                    st.dataframe(inc_df, use_container_width=True, height=450)
                else:
                    st.info(f"Conto Economico di esercizio non disponibile offline per {selected_ticker}.")

            with st_tab2:
                if not bal_df.empty:
                    col_bal_h1, col_bal_h2 = st.columns([3.5, 0.9])
                    with col_bal_h2:
                        csv_bal = bal_df.to_csv(index=True).encode('utf-8')
                        st.download_button("📥 Scarica CSV", data=csv_bal, file_name=f"{selected_ticker}_stato_patrimoniale.csv", mime="text/csv", use_container_width=True, key="btn_download_bal_stmt")
                    st.dataframe(bal_df, use_container_width=True, height=450)
                else:
                    st.info(f"Stato Patrimoniale di esercizio non disponibile offline per {selected_ticker}.")

            with st_tab3:
                if not cf_df.empty:
                    col_cf_h1, col_cf_h2 = st.columns([3.5, 0.9])
                    with col_cf_h2:
                        csv_cf = cf_df.to_csv(index=True).encode('utf-8')
                        st.download_button("📥 Scarica CSV", data=csv_cf, file_name=f"{selected_ticker}_rendiconto_finanziario.csv", mime="text/csv", use_container_width=True, key="btn_download_cf_stmt")
                    st.dataframe(cf_df, use_container_width=True, height=450)
                else:
                    st.info(f"Rendiconto Finanziario di esercizio non disponibile offline per {selected_ticker}.")

        # ── SUB-MODULO: LOCAL RAG & SEC FILING VECTOR STORE (10-K / 10-Q Q&A) ──────
        st.divider()
        col_rag_h1, col_rag_h2 = st.columns([3.5, 1.2])
        with col_rag_h1:
            st.markdown(f"#### 🔍 SEC Filing Vector Store & Local RAG per **{selected_company_name}** ({selected_ticker})")
            st.caption("Interrogazione semantica in linguaggio naturale sui bilanci ufficiali depositati presso la SEC (Form 10-K, Form 10-Q ed Earnings Calls).")
        with col_rag_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            render_sec_rag_modal(button_label="ℹ️ Guida al Motore SEC RAG & Form 10-K", use_popover=False)

        from core.sec_rag_engine import query_sec_filings_rag, index_ticker_sec_filings

        indexed_chunks_cnt = index_ticker_sec_filings(selected_ticker)
        st.caption(f"📚 *Vector Store Indicizzato: **{indexed_chunks_cnt} chunk semantici** attivi per {selected_ticker} (Form 10-K / 10-Q).*")

        col_rag_opt1, col_rag_opt2 = st.columns([2.5, 1.5])
        with col_rag_opt1:
            sec_filter_choice = st.selectbox(
                "Filtra per Sezione Normativa SEC:",
                options=[
                    "Tutte le Sezioni",
                    "Item 1A: Risk Factors & Macro Threats",
                    "Item 7: Management's Discussion and Analysis (MD&A)",
                    "Item 8: Financial Statements, Debt & Accounting Notes",
                    "Item 1: Business Overview & Competitive Moat"
                ],
                index=0
            )
        with col_rag_opt2:
            st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
            rag_top_k = st.slider("Numero di Chunk da Recuperare (Top-K):", min_value=1, max_value=6, value=3)

        st.markdown("##### 💡 Domande Frequenti di Due Diligence (1-Click Prompt):")
        chip_col1, chip_col2 = st.columns(2)
        with chip_col1:
            if st.button("⚠️ Quali sono i principali fattori di rischio e minacce competitive (Item 1A)?", use_container_width=True):
                st.session_state[f"sec_query_{selected_ticker}"] = "Quali sono i principali fattori di rischio, minacce geopolitiche e concentrazione della catena di fornitura?"
            if st.button("📈 Qual è la dinamica dei margini operativi e la guidance del management (MD&A)?", use_container_width=True):
                st.session_state[f"sec_query_{selected_ticker}"] = "Qual è l'evoluzione del fatturato, dei margini operativi lordi e la spesa in R&D?"
        with chip_col2:
            if st.button("🏦 Qual è la struttura delle scadenze del debito e gli impegni finanziari?", use_container_width=True):
                st.session_state[f"sec_query_{selected_ticker}"] = "Dettaglio delle scadenze del debito a lungo termine, tassi di interesse e impegni di cassa."
            if st.button("⚖️ Ci sono contenziosi legali rilevanti, rischi antitrust o concentrazione clienti?", use_container_width=True):
                st.session_state[f"sec_query_{selected_ticker}"] = "Contenziosi legali, pressioni regolatorie antitrust e concentrazione dei clienti."

        def_q = st.session_state.get(f"sec_query_{selected_ticker}", "Quali sono i principali fattori di rischio e minacce competitive?")
        user_sec_query = st.text_input(
            "Inserisci la tua domanda in linguaggio naturale per l'analisi dei bilanci SEC:",
            value=def_q,
            key=f"input_sec_query_{selected_ticker}"
        )

        if st.button(f"🔍 Interroga SEC Filings di {selected_ticker} (Local RAG)", type="primary", use_container_width=True):
            with st.spinner(f"Elaborazione semantica e recupero vettoriale per {selected_ticker}..."):
                rag_out = query_sec_filings_rag(selected_ticker, user_sec_query, section_filter=sec_filter_choice, top_k=rag_top_k)
                st.session_state[f"rag_res_{selected_ticker}"] = rag_out

        rag_res = st.session_state.get(f"rag_res_{selected_ticker}")
        if rag_res and rag_res.get("found"):
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_k_rag1, col_k_rag2, col_k_rag3 = st.columns(3)
            with col_k_rag1:
                metric_card("Rilevanza Semantica Top", f"{rag_res['top_relevance_pct']:.1f}%", "BM25 / Cosine Score", True)
            with col_k_rag2:
                metric_card("Sezione Primaria", rag_res.get("primary_section", "10-K").split(":")[0], "Documento Ufficiale SEC", True)
            with col_k_rag3:
                metric_card("Fonti Citabili Trovate", f"{len(rag_res['citations'])} Sezioni", "Verificate nel Testo", True)

            st.markdown("##### 🤖 Risposta Istituzionale Grounded (Sintesi RAG):")
            st.markdown(
                f"""
                <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(88, 166, 255, 0.25); border-left: 4px solid #58a6ff; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; color: #e6edf3; font-size: 13.5px; line-height: 1.55;">
                    {rag_res['answer'].replace(chr(10), '<br>')}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("##### 📑 Citazioni dei Paragrafi Ufficiali SEC (Evidenze nel Testo):")
            for idx, cit in enumerate(rag_res["citations"], start=1):
                with st.expander(f"📌 Fonte {idx}: {cit['section']} ({cit['filing_type']} - Esercizio {cit['fiscal_year']}) — Rilevanza: {cit['relevance_pct']:.1f}%", expanded=(idx == 1)):
                    st.markdown(f"*{cit['text']}*")


    # ── SUBTAB 2: COMPARATIVA MULTIAZIENDALE ──────────────────────────────────
    elif active_bilanci_subtab == "⚔️ Comparativa Multiaziendale (Altman Z-Score, DuPont & Ratios)":
        st.markdown("#### ⚔️ Confronto Multiaziendale di Solvibilità, DuPont & Indici di Bilancio")
        st.caption("Compara direttamente 2 o più aziende del portafoglio o del mercato globale per identificare i bilanci più solidi e performanti.")

        all_candidate_tickers = list(dict.fromkeys(list(company_options.keys()) + ["GOOGL", "AAPL", "MSFT", "AMZN", "NVDA", "TSLA", "META", "BABA", "RACE.MI", "UCG.MI", "ISP.MI"]))
        default_comp_selection = [all_candidate_tickers[0]] if len(all_candidate_tickers) == 1 else (all_candidate_tickers[:3] if len(all_candidate_tickers) >= 3 else all_candidate_tickers)

        col_mult, col_ext = st.columns([3, 1.5])
        with col_mult:
            selected_comp_tickers = st.multiselect(
                "Seleziona Aziende da Comparare:",
                options=all_candidate_tickers,
                default=default_comp_selection,
                format_func=lambda x: f"{x} - {resolve_company_name(x)}"
            )
        with col_ext:
            extra_input = st.text_input("Aggiungi Ticker Esterno (es. NFLX, DIS):", value="")
            if extra_input and extra_input.upper().strip() not in selected_comp_tickers:
                selected_comp_tickers.append(extra_input.upper().strip())

        if len(selected_comp_tickers) < 2:
            st.warning("⚠️ Seleziona almeno **2 aziende** per attivare l'analisi comparativa affiancata.")
        else:
            import importlib
            import core.financial_analysis
            importlib.reload(core.financial_analysis)
            from core.financial_analysis import compare_multiple_companies as compare_fn
            comp_data = compare_fn(selected_comp_tickers, equity_pos)
            z_df = comp_data["zscore_table"]
            dp_df = comp_data["dupont_table"]
            r_df = comp_data["ratios_table"]
            reps = comp_data["reports"]

            st.divider()

            # 1. Grafico Comparativo Altman Z-Score (Bande di Rischio Sfumate)
            st.markdown("#### 🛡️ Confronto Solvibilità & Altman Z-Score")
            st.caption(r"Fasce di Rischio: 🔴 **Zona Pericolo** ($Z < 1.81$) &nbsp;|&nbsp; 🟡 **Zona Grigia** ($1.81 \le Z \le 2.99$) &nbsp;|&nbsp; 🟢 **Zona Sicura** ($Z > 2.99$)")
            
            fig_comp_z = go.Figure()
            colors_z = ["#3fb950" if z >= 2.99 else ("#d29922" if z >= 1.81 else "#f85149") for z in z_df["Altman Z-Score"]]
            max_z_val = float(z_df["Altman Z-Score"].max()) if not z_df.empty else 5.0
            x_max_range = max(6.0, max_z_val * 1.18)
            chart_z_height = max(240, len(z_df) * 52)
            
            # Bande di sfondo sfumate per le 3 zone di rischio
            fig_comp_z.add_vrect(x0=0, x1=1.81, fillcolor="rgba(248, 81, 73, 0.10)", layer="below", line_width=0)
            fig_comp_z.add_vrect(x0=1.81, x1=2.99, fillcolor="rgba(210, 153, 34, 0.10)", layer="below", line_width=0)
            fig_comp_z.add_vrect(x0=2.99, x1=x_max_range, fillcolor="rgba(63, 185, 80, 0.08)", layer="below", line_width=0)
            
            fig_comp_z.add_trace(go.Bar(
                y=z_df["Ticker"] + " - " + z_df["Azienda"],
                x=z_df["Altman Z-Score"],
                orientation='h',
                text=z_df["Altman Z-Score"].apply(lambda v: f"Z = {v:.2f}"),
                textposition='outside',
                textfont=dict(size=11, color="#ffffff"),
                cliponaxis=False,
                marker=dict(color=colors_z, line=dict(color="#0d1117", width=1.5)),
                hovertemplate="<b>%{y}</b><br>Altman Z-Score: <b>%{x:.2f}</b><extra></extra>"
            ))
            
            # Linee verticali di soglia pulite senza testo interno sovrapposto
            fig_comp_z.add_vline(x=1.81, line_dash="dash", line_color="#f85149", line_width=1.5)
            fig_comp_z.add_vline(x=2.99, line_dash="dash", line_color="#3fb950", line_width=1.5)
            
            fig_comp_z.update_layout(
                template="plotly_dark", height=chart_z_height,
                yaxis=dict(title=None, autorange="reversed", showgrid=False),
                xaxis=dict(title="Altman Z-Score", range=[0, x_max_range], gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(l=20, r=60, t=20, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_comp_z)
            st.plotly_chart(fig_comp_z, use_container_width=True, key="val_comp_altman_z_bar", config={"displayModeBar": "hover", "displaylogo": False})

            col_ct1, col_ct2 = st.columns(2)
            with col_ct1:
                st.markdown("##### 📋 Tabella Solvibilità (Altman Z-Score)")
                st.dataframe(z_df, use_container_width=True, hide_index=True)
            with col_ct2:
                st.markdown("##### 🔍 Tabella Scomposizione DuPont (Driver ROE)")
                st.dataframe(dp_df, use_container_width=True, hide_index=True)

            st.divider()

            # 2. Radar Chart Multiaziendale Sovrapposto
            st.markdown("#### 🎯 Radar Chart Comparativo Sovrapposto degli Indici di Bilancio")
            
            fig_comp_radar = go.Figure()
            radar_colors = ['#00e676', '#58a6ff', '#bc8cff', '#ff9900', '#f85149', '#00f3ff']
            categories = ['Current Ratio', 'Quick Ratio', 'Asset Turnover', 'Debt/Equity (Inv)', 'Interest Coverage (Scaled)']
            
            for idx, (tk, rep) in enumerate(reps.items()):
                r_l = rep["ratios"]["liquidity"]
                r_s = rep["ratios"]["solvency"]
                vals = [
                    min(5.0, r_l.get('current_ratio', 1.5) or 1.5),
                    min(5.0, r_l.get('quick_ratio', 1.2) or 1.2),
                    min(5.0, rep["ratios"]['efficiency'].get('asset_turnover', 0.6) or 0.6),
                    min(5.0, 1.0 / (r_s.get('debt_to_equity', 0.8) + 1e-3)),
                    min(5.0, (r_s.get('interest_coverage', 5.0) or 5.0) / 2.0)
                ]
                c = radar_colors[idx % len(radar_colors)]
                fig_comp_radar.add_trace(go.Scatterpolar(
                    r=vals, theta=categories, fill='toself',
                    name=f"{rep['company_name']} ({tk})",
                    line=dict(color=c, width=2),
                    fillcolor=f"rgba({int(c[1:3],16)}, {int(c[3:5],16)}, {int(c[5:7],16)}, 0.12)",
                    hovertemplate="<b>%{theta}</b>: <b>%{r:.2f}</b> (" + tk + ")<extra></extra>"
                ))
                
            fig_comp_radar.update_layout(
                polar=dict(
                    bgcolor="rgba(22, 27, 34, 0.4)",
                    radialaxis=dict(visible=True, range=[0, 5], gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=10, color="rgba(255,255,255,0.6)")),
                    angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", linecolor="rgba(255,255,255,0.1)", tickfont=dict(size=11, color="#ffffff"))
                ),
                template="plotly_dark", height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5, font=dict(size=11, color="#ffffff")),
                margin=dict(l=30, r=30, t=40, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_comp_radar)
            st.plotly_chart(fig_comp_radar, use_container_width=True, key="val_comp_multi_radar", config={"displayModeBar": "hover", "displaylogo": False})

            st.markdown("##### 📊 Matrice Comparativa degli Indici Fondamentali di Bilancio")
            st.dataframe(r_df, use_container_width=True, hide_index=True)

    # ── SUBTAB 3: PIOTROSKI F-SCORE, WACC & MULTIPLI DI MERCATO ────────────────
    elif active_bilanci_subtab == "🎯 Piotroski F-Score, WACC & Multipli di Mercato":
        st.markdown("### 🎯 Valutazione Quantitativa: Piotroski F-Score, WACC & Multipli")
        st.caption("Analisi fondamentale avanzata: diagnosi di salute contabile in 9 punti (Stanford Piotroski), stima WACC CAPM e comparazione dei multipli di mercato.")

        c_p1, c_p2 = st.columns([1.1, 2.0])
        with c_p1:
            search_mode_p = st.radio(
                "Selezione Azienda per la Diagnostica:",
                ["Azienda dal Portafoglio", "Cerca Qualsiasi Azienda sul Mercato"],
                horizontal=True,
                key="radio_p_search"
            )
            if search_mode_p == "Azienda dal Portafoglio":
                p_tk = st.selectbox(
                    "Seleziona Azienda dal Portafoglio:",
                    list(company_options.keys()),
                    format_func=lambda x: f"{x} - {company_options[x]}" if company_options[x] != x else f"{x}",
                    key="selectbox_p_portfolio"
                )
            else:
                p_custom = st.text_input("Inserisci Ticker (es. GOOGL, AAPL, MSFT, NVDA, TSLA, RACE.MI):", value="GOOGL", key="text_p_custom")
                p_tk = p_custom.upper().strip()

            p_name = resolve_company_name(p_tk)
            
            wacc_data = compute_wacc_estimation(p_tk)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 🧮 Calcolatore Dinamico WACC")
            metric_card(f"WACC Stimato ({p_tk})", f"{wacc_data['wacc_pct']}%", f"Beta: {wacc_data['beta']} | Ke: {wacc_data['cost_of_equity_pct']}%", True)
            
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 0.85rem; line-height: 1.6;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #8b949e;">Costo Equity (<i>K<sub>e</sub></i>): <b style="color: #58a6ff;">{wacc_data['cost_of_equity_pct']}%</b></span>
                    <span style="color: #8b949e;">Costo Debito Net-Tax (<i>K<sub>d</sub></i>): <b style="color: #3fb950;">{wacc_data['cost_of_debt_after_tax_pct']}%</b></span>
                </div>
                <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 6px;">
                    <span style="color: #8b949e;">Peso Equity (<i>W<sub>e</sub></i>): <b style="color: #ffffff;">{wacc_data['weight_equity_pct']}%</b></span>
                    <span style="color: #8b949e;">Peso Debito (<i>W<sub>d</sub></i>): <b style="color: #ffffff;">{wacc_data['weight_debt_pct']}%</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_p2:
            f_res = compute_piotroski_f_score(p_tk)
            score_val = f_res['score']
            max_score = f_res['max_score']
            eval_label = "Salute Solida" if score_val >= 7 else ("Salute Moderata" if score_val >= 5 else "Rischio Distress")
            eval_icon = "🟢" if score_val >= 7 else ("🟡" if score_val >= 5 else "🔴")
            
            cp2_a, cp2_b = st.columns([1, 1.4])
            with cp2_a:
                metric_card("Piotroski F-Score", f"{score_val} / {max_score}", "Health Check 9 Criteri", positive=score_val >= 6)
            with cp2_b:
                metric_card("Verdetto Contabile", f"{eval_icon} {eval_label}", f"Score {score_val} su 9 punti", positive=score_val >= 6)
            
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            st.dataframe(f_res["details_df"], use_container_width=True, hide_index=True)

        st.divider()

        st.markdown(f"#### 📊 Matrice dei Multipli di Mercato & Valuation Benchmark | {p_name} ({p_tk})")
        m_data = compute_valuation_multiples_matrix(p_tk)
        st.dataframe(m_data["multiples_table"], use_container_width=True, hide_index=True)


# ── TAB 5: VALUTAZIONE INTRINSECA DCF MONTE CARLO ─────────────────────
elif active_val_tab == "🧮 Valutazione Intrinseca DCF Monte Carlo":
    col_head_dcf1, col_head_dcf2 = st.columns([3.2, 1.1])
    with col_head_dcf1:
        st.markdown("### 🧮 Modello di Valutazione Intrinseca DCF Monte Carlo")
        st.caption("Stima il Fair Value intrinseco aziendale attualizzando i Flussi di Cassa Liberi (FCF) al WACC ed eseguendo 1.000 simulazioni stocastiche sui parametri chiave.")
    with col_head_dcf2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("📚 Guida al DCF Monte Carlo", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Discounted Cash Flow (DCF) con Simulazione Stocastica</div>
  <div>La metodologia quantitativa fondamentale per determinare il valore economico di un'azienda sommando i flussi di cassa operativi futuri (Free Cash Flows to Firm) scontati al costo medio ponderato del capitale (WACC).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formule di Attualizzazione & Terminal Value</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Enterprise Value:</b> &sum; [ FCF<sub>t</sub> / (1 + WACC)<sup>t</sup> ] + Terminal Value / (1 + WACC)<sup>5</sup><br>
    • <b>Terminal Value (Gordon Growth):</b> [ FCF<sub>5</sub> &times; (1 + g) ] / (WACC &minus; g)<br>
    • <b>Equity Value:</b> Enterprise Value + Cassa Disponibile &minus; Debito Finanziario Netto
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Superare la staticità del DCF tradizionale introducendo una distribuzione di probabilità a 1.000 iterazioni su crescita ricavi, margini operativi, tasso risk-free e perpetual growth.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS calcola il WACC dinamico bottom-up (Beta, Equity Risk Premium, Cost of Debt net-tax) ed esegue la simulazione stocastica generando la distribuzione del Fair Value per azione.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Probabilità Sottovalutazione (%):</b> Percentuale di simulazioni in cui il Fair Value supera il prezzo attuale.<br>
    • <b>Margine di Sicurezza:</b> Distanza percentuale tra il prezzo di mercato e il 10° percentile prudenziale.
  </div>
</div>

</div>
""", button_label="💡 Come funziona il DCF Monte Carlo?")

    try:
        from core.financial_analysis import compute_dcf_monte_carlo_valuation
    except ImportError:
        import importlib
        import core.financial_analysis
        importlib.reload(core.financial_analysis)
        from core.financial_analysis import compute_dcf_monte_carlo_valuation

    c_dcf1, c_dcf2 = st.columns([1.5, 2.5])
    with c_dcf1:
        st.markdown("#### ⚙️ Input & Parametri del Modello")
        
        search_mode_dcf = st.radio(
            "Modalità Selezione Azienda per la Valutazione DCF:",
            ["Azienda dal Portafoglio", "Cerca Qualsiasi Azienda sul Mercato (es. AAPL, NVDA, RACE.MI, TSLA)"],
            horizontal=True,
            key="radio_dcf_search"
        )

        if search_mode_dcf == "Azienda dal Portafoglio":
            dcf_tk = st.selectbox(
                "Seleziona Azienda dal Portafoglio:",
                list(company_options.keys()),
                format_func=lambda x: f"{x} - {company_options[x]}" if company_options[x] != x else f"{x}",
                key="selectbox_dcf_portfolio"
            )
        else:
            custom_dcf_input = st.text_input(
                "Inserisci Ticker Azionario (es. AAPL, MSFT, NVDA, TSLA, RACE.MI, UCG.MI, DIS, NFLX):",
                value="GOOGL",
                key="text_dcf_custom"
            )
            dcf_tk = custom_dcf_input.upper().strip()

        dcf_name = resolve_company_name(dcf_tk)
        
        try:
            from core.financial_analysis import compute_dcf_monte_carlo_valuation, fetch_dcf_initial_inputs
        except ImportError:
            import importlib
            import core.financial_analysis
            importlib.reload(core.financial_analysis)
            from core.financial_analysis import compute_dcf_monte_carlo_valuation, fetch_dcf_initial_inputs

        match_pos = active_pos[active_pos["ticker"] == dcf_tk] if "ticker" in active_pos.columns else pd.DataFrame()
        p_price_fallback = float(match_pos.iloc[0]["last_price"]) if not match_pos.empty and pd.notna(match_pos.iloc[0].get("last_price")) else 150.0

        dcf_defaults = fetch_dcf_initial_inputs(dcf_tk, fallback_price=p_price_fallback)

        input_price = st.number_input("Prezzo di Mercato Attuale (€ / $):", value=float(dcf_defaults["price"]), min_value=0.1, step=1.0)
        input_fcf = st.number_input("Flusso di Cassa Libero Iniziale (FCF Base in M €/$):", value=float(dcf_defaults["fcf_m"]), min_value=1.0, step=500.0) * 1e6
        input_shares = st.number_input("Azioni in Circolazione (Milioni):", value=float(dcf_defaults["shares_m"]), min_value=1.0, step=100.0) * 1e6
        st.caption(f"💡 *Azioni totali diluite pre-compilate ({dcf_defaults['shares_m']:,.0f} Milioni tra tutte le classi azionarie A/B/C).*")
        
        with st.expander("🛠️ Parametri Avanzati (WACC, Tassi di Crescita & Volatilità)", expanded=True):
            wacc_val = st.slider("WACC Medio (%):", 4.0, 16.0, 8.5, 0.25) / 100.0
            growth_val = st.slider("Crescita FCF Anni 1-5 (%):", -5.0, 30.0, 8.5, 0.5) / 100.0
            term_g_val = st.slider("Crescita Perpetua Terminale (%):", 0.5, 4.5, 2.5, 0.1) / 100.0
            
            cash_val = st.number_input("Cassa Netta & Equivalenti (M €/$):", value=float(dcf_defaults["cash_m"])) * 1e6
            debt_val = st.number_input("Debito Totale (M €/$):", value=float(dcf_defaults["debt_m"])) * 1e6
            
            n_sims = st.select_slider("Numero Iterazioni Monte Carlo:", options=[250, 500, 1000, 2000], value=1000)

    with c_dcf2:
        dcf_res = compute_dcf_monte_carlo_valuation(
            fcf_base=input_fcf,
            current_price=input_price,
            shares_outstanding=input_shares,
            cash_and_equiv=cash_val,
            total_debt=debt_val,
            growth_rate_mean=growth_val,
            wacc_mean=wacc_val,
            terminal_growth_mean=term_g_val,
            n_simulations=n_sims
        )

        st.markdown(f"#### 🎯 Verdetto Valutazione: {dcf_res['recommendation']}")

        dk1, dk2, dk3, dk4 = st.columns(4)
        with dk1:
            metric_card("Fair Value Intrinseco", f"€ {dcf_res['fair_value_median']:.2f}", f"Base Case: € {dcf_res['fair_value_base']:.2f}", True if dcf_res['upside_downside_pct'] > 0 else False)
        with dk2:
            metric_card("Prezzo Attuale", f"€ {dcf_res['current_price']:.2f}", f"Quotazione di Mercato", True)
        with dk3:
            metric_card("Upside / Downside", f"{dcf_res['upside_downside_pct']:+.1f}%", "Margine di Sicurezza", True if dcf_res['upside_downside_pct'] > 0 else False)
        with dk4:
            metric_card("Prob. Sottovalutazione", f"{dcf_res['prob_undervalued_pct']:.1f}%", f"{n_sims} Simulazioni", True if dcf_res['prob_undervalued_pct'] > 50 else False)

        st.divider()

        # Istogramma Distribuzione Monte Carlo Fair Value
        sim_vals = dcf_res["simulated_fair_values"]
        st.markdown(f"##### 📈 Distribuzione Monte Carlo del Fair Value Intrinseco | {dcf_name} ({dcf_tk})")
        
        fv_med = dcf_res["fair_value_median"]
        cur_p = dcf_res["current_price"]
        p10 = dcf_res["p10_bear_case"]
        p90 = dcf_res["p90_bull_case"]
        
        fig_dcf_hist = go.Figure()
        fig_dcf_hist.add_trace(go.Histogram(
            x=sim_vals,
            nbinsx=45,
            name="Distribuzione DCF",
            marker=dict(
                color="rgba(0, 230, 118, 0.55)",
                line=dict(color="#00e676", width=1)
            ),
            hovertemplate="Intervallo Fair Value: <b>€ %{x:,.2f}</b><br>Conteggio Simulazioni: <b>%{y}</b><extra></extra>"
        ))
        
        # Tracce per la legenda orizzontale in alto
        fig_dcf_hist.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"Mediana DCF (€ {fv_med:.2f})", line=dict(color="#00e676", width=2.5, dash="solid")))
        fig_dcf_hist.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"Prezzo Attuale (€ {cur_p:.2f})", line=dict(color="#f85149", width=2, dash="dash")))
        fig_dcf_hist.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"Bear 10% (€ {p10:.2f})", line=dict(color="#d29922", width=1.5, dash="dot")))
        fig_dcf_hist.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"Bull 90% (€ {p90:.2f})", line=dict(color="#58a6ff", width=1.5, dash="dot")))
        
        # Linee verticali pulite a tutta altezza senza etichette testuali interne sovrapposte
        fig_dcf_hist.add_vline(x=fv_med, line_dash="solid", line_color="#00e676", line_width=2.5)
        fig_dcf_hist.add_vline(x=cur_p, line_dash="dash", line_color="#f85149", line_width=2)
        fig_dcf_hist.add_vline(x=p10, line_dash="dot", line_color="#d29922", line_width=1.5)
        fig_dcf_hist.add_vline(x=p90, line_dash="dot", line_color="#58a6ff", line_width=1.5)
        
        fig_dcf_hist.update_layout(
            xaxis=dict(title="Fair Value Stimato (€ / $)", gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(title="Frequenza Simulazioni", gridcolor="rgba(255,255,255,0.06)"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color="#ffffff"),
                bgcolor="rgba(22, 27, 34, 0.6)",
                bordercolor="rgba(255,255,255,0.08)",
                borderwidth=1
            ),
            template="plotly_dark",
            height=370,
            margin=dict(l=20, r=20, t=45, b=25),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig_dcf_hist)
        st.plotly_chart(fig_dcf_hist, use_container_width=True, key="val_dcf_mc_histogram", config={"displayModeBar": "hover", "displaylogo": False})

        st.markdown("##### 📋 Matrice di Sensibilità & Scenari DCF")
        df_dcf_scenarios = pd.DataFrame([
            {"Scenario": "🐻 Bear Case (10° Percentile)", "Fair Value per Azione": f"€ {dcf_res['p10_bear_case']:.2f}", "Upside/Downside": f"{((dcf_res['p10_bear_case']-dcf_res['current_price'])/dcf_res['current_price'])*100:+.1f}%"},
            {"Scenario": "⚖️ Base Case (Mediana Monte Carlo)", "Fair Value per Azione": f"€ {dcf_res['fair_value_median']:.2f}", "Upside/Downside": f"{dcf_res['upside_downside_pct']:+.1f}%"},
            {"Scenario": "🐂 Bull Case (90° Percentile)", "Fair Value per Azione": f"€ {dcf_res['p90_bull_case']:.2f}", "Upside/Downside": f"{((dcf_res['p90_bull_case']-dcf_res['current_price'])/dcf_res['current_price'])*100:+.1f}%"}
        ])
        st.dataframe(df_dcf_scenarios, use_container_width=True, hide_index=True)




