import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, glossary_modal, fmt_pct, render_executive_badges, render_formula_popover, apply_plotly_theme

st.set_page_config(page_title="Valutazione Aziendale | ARGUS", page_icon="🏛️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
pos = results["positions"]

active_pos = pos[pos["qty_net"] > 0].copy()

st.title("🏛️ Valutazione Intrinseca & Fair Value")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Analisi dei fondamentali societari, target price dei mercati (Consensus) e simulazioni di private equity (IRR & TVPI).")
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    render_executive_badges(results["metrics"])
with col_head2:
    glossary_modal("Cos'è la Valutazione Aziendale?",
    "Valutazione rigorosa basata sul <b>Target Price degli Analisti (Consensus)</b> e sul <b>PEG Ratio</b> per emettere un verdetto: l'asset è Sottovalutato o Sopravvalutato rispetto ai fondamentali?", button_label="💡 Come funziona?")

st.divider()


if active_pos.empty:
    st.info("Nessuna posizione aperta in portafoglio.")
    st.stop()

# Estrazione colonne e calcolo dell'Upside / Giudizio
fund_cols = ["ticker", "name", "asset_class", "weight_pct", "last_price", 
             "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]
df_fund = active_pos[[c for c in fund_cols if c in active_pos.columns]].copy()

# Pulizia numerica
for col in ["last_price", "target_mean_price", "peg_ratio", "trailing_pe", "forward_pe", "price_to_book", "dividend_yield", "roe"]:
    if col in df_fund.columns:
        df_fund[col] = pd.to_numeric(df_fund[col], errors='coerce')

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

if df_valued.empty:
    st.warning("⚠️ Impossibile calcolare il Fair Value: i dati degli Analisti e il Target Price non sono disponibili per gli asset attuali.")
    st.stop()

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ ─────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏛️ Fair Value & Consensus Analisti",
    "📈 Potenziale di Rialzo (Upside/Downside)",
    "💼 Private Equity & Waterfall Simulator",
    "📊 Analisi dei Bilanci & Solvibilità (Altman Z-Score & DuPont)",
    "🧮 Valutazione Intrinseca DCF Monte Carlo"
])

# ── TAB 1: FAIR VALUE & CONSENSUS ANALISTI ─────────────────────
with tab1:
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
            help_text="<b>Cosa significa:</b> Azioni che il mercato sta prezzando al di sotto del loro reale potenziale stimato.\n\n<b>A cosa serve:</b> Filtra rapidamente il portafoglio per isolare i 'veri affari'. Segnala su quali strumenti potresti considerare di aumentare la posizione per sfruttare il potenziale di apprezzamento non ancora espresso dal mercato.\n\n<b>Come si calcola:</b> Si contano gli asset per i quali il Target Price Medio a 12 mesi degli analisti istituzionali è superiore al prezzo attuale di mercato di almeno il 10%, purché abbiano multipli di valutazione (es. PEG Ratio) ragionevoli."
        )
    with col2:
        metric_card(
            "Fairly Valued (Hold)",
            str(n_fair),
            "Asset in linea col fair value",
            True,
            help_text="<b>Cosa significa:</b> Azioni il cui prezzo attuale di borsa riflette già perfettamente le stime di utili futuri e il potenziale dell'azienda.\n\n<b>A cosa serve:</b> Indica quegli asset che stanno facendo il loro dovere, prezzati in equilibrio. Solitamente non c'è urgenza né di vendere (perché l'azienda è sana e prezzata giusta) né di comprare aggressivamente (non c'è 'sconto').\n\n<b>Come si calcola:</b> Si contano gli asset la cui distanza tra il Target Price e il Prezzo Attuale oscilla in una fascia di normalità compresa tra il -5% e il +10%."
        )
    with col3:
        metric_card(
            "Sopravvalutate (Sell)",
            str(n_over),
            "Asset a premio vs target price",
            False,
            help_text="<b>Cosa significa:</b> Azioni scambiate a un prezzo eccessivamente alto ('a premio') rispetto ai fondamentali reali dell'azienda (utili e stime).\n\n<b>A cosa serve:</b> È un alert cruciale per il rischio di bolle o per le 'prese di profitto'. Ti suggerisce che l'asset potrebbe aver corso troppo e che il mercato prima o poi potrebbe correggere il prezzo al ribasso per allinearlo alla realtà contabile.\n\n<b>Come si calcola:</b> Si contano gli asset con un Upside negativo (ovvero il Target Price è inferiore di oltre il 5% rispetto al prezzo attuale) oppure che mostrano un PEG Ratio follemente alto (> 2.5), indice di euforia irrazionale."
        )

    st.divider()

    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.markdown("#### Tabella Fair Value & Target Price")
        
        df_display = df_valued[["ticker", "Verdetto", "last_price", "target_mean_price", "Upside %", "peg_ratio", "trailing_pe"]].copy()
        df_display.rename(columns={
            "ticker": "Asset",
            "last_price": "Prezzo Attuale",
            "target_mean_price": "Target Price (Analisti)",
            "peg_ratio": "PEG Ratio",
            "trailing_pe": "P/E Ratio"
        }, inplace=True)
        
        df_display["Prezzo Attuale"] = df_display["Prezzo Attuale"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["Target Price (Analisti)"] = df_display["Target Price (Analisti)"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["Upside %"] = df_display["Upside %"].apply(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "N/A")
        df_display["PEG Ratio"] = df_display["PEG Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        df_display["P/E Ratio"] = df_display["P/E Ratio"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)

    with col_b:
        glossary_modal("📚 Glossario Metriche di Valutazione", """
    <ul style="margin-top:0; padding-left:20px;">
        <li style="margin-bottom:12px;"><b>Target Price (Prezzo Obiettivo):</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> È il prezzo futuro a cui gli analisti finanziari ritengono che l'azione debba tendere nei successivi 12 mesi.</li>
                <li><b>A cosa serve:</b> È la bussola del mercato. Ti permette di capire se i grandi player istituzionali vedono l'asset in salita (opportunità) o in stallo.</li>
            </ul>
        </li>
        <li style="margin-bottom:12px;"><b>Upside / Downside %:</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> È il potenziale di guadagno (Upside) o perdita (Downside) necessario affinché il prezzo attuale raggiunga il Target Price.</li>
            </ul>
        </li>
        <li><b>PEG Ratio (Price/Earnings-to-Growth):</b>
            <ul style="margin-top:4px;">
                <li><b>Cosa significa:</b> Mette in relazione il prezzo pagato per gli utili con la velocità a cui questi utili stanno crescendo.</li>
            </ul>
        </li>
    </ul>
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
            verdict_counts, values="Conteggio", names="Verdetto", hole=0.65,
            color="Verdetto", color_discrete_map=color_map
        )
        fig.update_traces(
            textposition='inside', textinfo='percent+label', showlegend=False,
            marker=dict(line=dict(color="#0d1117", width=2)),
            hovertemplate="<b>Verdetto: %{label}</b><br>Numero Asset: %{value}<extra></extra>"
        )
        fig.update_layout(
            template="plotly_dark", height=320,
            margin=dict(l=10, r=10, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: POTENZIALE DI RIALZO ──────────────────────────────
with tab2:
    st.markdown("#### Potenziale di Rialzo (Upside/Downside) degli Asset")
    df_upside = df_valued.dropna(subset=["Upside %"]).sort_values("Upside %", ascending=True)

    if not df_upside.empty:
        df_upside["Colore"] = np.where(df_upside["Upside %"] > 0, "#00e676", "#f85149")
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_upside["Upside %"] * 100,
            y=df_upside["ticker"],
            orientation='h',
            marker=dict(color=df_upside["Colore"], line=dict(color="#0d1117", width=1)),
            text=df_upside["Upside %"].apply(lambda x: f"{x*100:+.1f}%"),
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>📈 Distanza dal Fair Value: %{x:+.1f}%<extra></extra>"
        ))
        
        fig_bar.update_layout(
            template="plotly_dark", height=420,
            xaxis_title="Distanza dal Fair Value degli Analisti (%)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        apply_plotly_theme(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 3: PRIVATE EQUITY SIMULATOR ───────────────────────────
with tab3:
    st.markdown("#### 💼 Private Equity & Private Markets Cash Flow Simulator")
    st.caption("Simulatore dei flussi finanziari di Private Equity: calcolo del Net IRR, TVPI / MOIC, DPI, RVPI e Carried Interest Waterfall Allocation")

    glossary_modal("ℹ️ Guida alle Metriche del Private Equity (TVPI, DPI, IRR)", """
    <p><b>1. TVPI / MOIC (Total Value to Paid-In / Multiple on Invested Capital):</b><br>
    Esprime il moltiplicatore totale di valore generato dal fondo di Private Equity rispetto al capitale richiamato (Capital Calls).</p>

    <p><b>2. DPI (Distributed to Paid-In):</b><br>
    La porzione di capitale e plusvalenze effettivamente già distribuita in cassa agli investitori (Limited Partners).</p>

    <p><b>3. RVPI (Residual Value to Paid-In):</b><br>
    Il valore residuo stimato delle aziende ancora in portafoglio (Net Asset Value - NAV) rispetto al capitale richiamato.</p>

    <p><b>4. Carried Interest & Hurdle Rate Waterfall:</b><br>
    La quota dei profitti (tipicamente il 20%) spettante al General Partner (GP) dopo che gli investitori (LP) hanno ottenuto la restituzione del capitale ed il rendimento minimo garantito (Hurdle Rate, tipicamente 8%).</p>
    """, button_label="💡 Come funziona il Simulatore Private Equity?")

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
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("TVPI / MOIC", f"{pe_res['tvpi_moic']:.2f}x")
        kpi2.metric("DPI (Cassa Distribuita)", f"{pe_res['dpi']:.2f}x")
        kpi3.metric("RVPI (NAV Residuo)", f"{pe_res['rvpi']:.2f}x")
        kpi4.metric("Carried Interest GP (€)", f"€ {pe_res['gp_carried_interest']:,.2f}")
        
        fig_wf = go.Figure(go.Waterfall(
            name="Waterfall PE", orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Capital Calls (LP)", "Distributions (Cassa)", "NAV Residuo", "Valore Creato Netto"],
            text=[f"€ {cap_calls:,.0f}", f"€ {distribs:,.0f}", f"€ {nav_val:,.0f}", f"€ {pe_res['total_gain']:,.0f}"],
            y=[-cap_calls, distribs, nav_val, pe_res['total_gain']],
            connector={"line":{"color":"rgba(255,255,255,0.2)"}},
            decreasing={"marker":{"color":"#ff4b4b"}},
            increasing={"marker":{"color":"#00cc96"}},
            totals={"marker":{"color":"#ff9900"}}
        ))
        fig_wf.update_layout(height=350, yaxis_title="Flussi di Cassa (€)")
        from core.ui_utils import apply_plotly_theme
        apply_plotly_theme(fig_wf)
        st.plotly_chart(fig_wf, use_container_width=True)

# ── TAB 4: ANALISI DEI BILANCI & SOLVIBILITÀ ──────────────────
with tab4:
    st.markdown("#### 📊 Diagnostica dei Bilanci Societari & Modelli di Solvibilità")
    st.caption("Analisi quantitativa dei Bilanci di Esercizio: previsione del rischio di insolvenza tramite Altman Z-Score, scomposizione ROE DuPont ed Indici di Liquidità/Solvibilità.")

    glossary_modal("📚 Guida all'Analisi dei Bilanci (Altman Z-Score & DuPont)", """
    <p><b>1. Altman Z-Score Model:</b><br>
    Modello econometrico sviluppato da Edward Altman per stimare la probabilità di bancarotta/insolvenza aziendale su un orizzonte di 24 mesi.<br>
    - <b>Z > 2.99:</b> Zona Sicura (Verde) — bilancio solido e struttura finanziaria equilibrata.<br>
    - <b>1.81 &le; Z &le; 2.99:</b> Zona Grigia (Giallo) — situazione di moderata attenzione.<br>
    - <b>Z < 1.81:</b> Zona di Pericolo (Rosso) — elevata probabilità di stress finanziario.</p>

    <p><b>2. Scomposizione DuPont (DuPont Analysis):</b><br>
    Scompone il Return on Equity (ROE) in tre determinanti fondamentali:<br>
    - <b>Profit Margin (Efficienza Operativa):</b> Quanto utile netto viene generato per ogni euro di fatturato.<br>
    - <b>Asset Turnover (Efficienza Patrimoniale):</b> Quanti euro di vendite produce l'attivo aziendale.<br>
    - <b>Equity Multiplier (Leva Finanziaria):</b> Quanti euro di attivo sono sostenuti da ogni euro di Capitale Netto.</p>
    """, button_label="💡 Come funziona la Diagnostica Bilanci?")

    subtab_single, subtab_compare, subtab_piotroski = st.tabs([
        "👤 Analisi Singola Azienda & Bilanci 10-K",
        "⚔️ Comparativa Multiaziendale (Altman Z-Score, DuPont & Ratios)",
        "🎯 Piotroski F-Score, WACC & Multipli di Mercato"
    ])

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
    with subtab_single:
        search_mode = st.radio(
            "Modalità Selezione Azienda per l'Analisi:",
            ["Azienda dal Portafoglio", "Cerca Qualsiasi Azienda sul Mercato (es. AAPL, NVDA, RACE.MI, TSLA)"],
            horizontal=True
        )

        if search_mode == "Azienda dal Portafoglio":
            selected_ticker = st.selectbox(
                "Seleziona Azienda dal Portafoglio per l'Analisi di Bilancio:",
                list(company_options.keys()),
                format_func=lambda x: f"{x} — {company_options[x]}" if company_options[x] != x else f"{x}"
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
                custom_input = st.text_input("Inserisci Ticker Azionario (es. AAPL, MSFT, NVDA, TSLA, RACE.MI, UCG.MI):", value="AAPL")
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
            max_gauge_val = max(5.0, round(z_val + 1.0, 1))
            val_color = "#00ff99" if z_val > 2.99 else ("#ffcc00" if z_val >= 1.81 else "#ff3333")

            fig_z = go.Figure(go.Indicator(
                mode="gauge",
                value=z_val,
                domain={'x': [0.05, 0.95], 'y': [0.15, 0.95]},
                title={'text': f"Altman Z-Score — {selected_company_name} ({selected_ticker})", 'font': {'size': 16, 'color': "white"}},
                gauge={
                    'axis': {'range': [0, max_gauge_val], 'tickwidth': 1, 'tickcolor': "white"},
                    'bar': {'color': val_color},
                    'steps': [
                        {'range': [0, 1.81], 'color': 'rgba(255, 51, 51, 0.3)'},
                        {'range': [1.81, 2.99], 'color': 'rgba(255, 204, 0, 0.3)'},
                        {'range': [2.99, max_gauge_val], 'color': 'rgba(0, 255, 153, 0.3)'}
                    ],
                    'threshold': {
                        'line': {'color': "white", 'width': 3},
                        'thickness': 0.75,
                        'value': z_val
                    }
                }
            ))

            fig_z.add_annotation(
                x=0.5, y=0.2,
                xref="paper", yref="paper",
                text=f"<b>Z = {z_val:.2f}</b>",
                showarrow=False,
                font=dict(size=30, color=val_color),
                align="center"
            )

            fig_z.update_layout(
                template="plotly_dark", 
                height=260, 
                margin=dict(l=35, r=35, t=45, b=15),
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_z, use_container_width=True)

        with col_z2:
            st.markdown("#### 🔍 Driver del ROE (DuPont 3-Fattori)")
            df_dp = pd.DataFrame([
                {"Fattore": "Profit Margin (Utile/Sales)", "Valore": f"{dp_data['profit_margin_pct']:.2f}%"},
                {"Fattore": "Asset Turnover (Sales/Assets)", "Valore": f"{dp_data['asset_turnover']:.2f}x"},
                {"Fattore": "Equity Multiplier (Assets/Equity)", "Valore": f"{dp_data['equity_multiplier']:.2f}x"},
                {"Fattore": "ROE Risultante", "Valore": f"{dp_data['roe_pct']:.2f}%"}
            ])
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
            name=f"{selected_company_name} ({selected_ticker})", line_color='#00ff99'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            template="plotly_dark", height=380,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)

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
        fig_feat = px.bar(
            ml_eval["feature_importance_df"],
            x="Importanza Relativa (%)",
            y="Feature",
            orientation="h",
            color="Importanza Relativa (%)",
            color_continuous_scale="Purples",
            title="Driver Predittivi di Solvibilità (Random Forest)"
        )
        fig_feat.update_layout(
            template="plotly_dark", height=250,
            margin=dict(l=10, r=10, t=35, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_feat, use_container_width=True)

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

            st.caption("💡 *Tutti i valori dei bilanci ufficiali sono formattati in Milioni (**M €**) con separatori delle migliaia e gestione delle voci non disponibili (—).*")

            st_tab1, st_tab2, st_tab3 = st.tabs([
                "📄 Conto Economico (Income Statement)",
                "🏛️ Stato Patrimoniale (Balance Sheet)",
                "💵 Rendiconto Finanziario (Cash Flow)"
            ])

            with st_tab1:
                if not inc_df.empty:
                    st.dataframe(inc_df, use_container_width=True, height=450)
                else:
                    st.info(f"Conto Economico di esercizio non disponibile offline per {selected_ticker}.")

            with st_tab2:
                if not bal_df.empty:
                    st.dataframe(bal_df, use_container_width=True, height=450)
                else:
                    st.info(f"Stato Patrimoniale di esercizio non disponibile offline per {selected_ticker}.")

            with st_tab3:
                if not cf_df.empty:
                    st.dataframe(cf_df, use_container_width=True, height=450)
                else:
                    st.info(f"Rendiconto Finanziario di esercizio non disponibile offline per {selected_ticker}.")


    # ── SUBTAB 2: COMPARATIVA MULTIAZIENDALE ──────────────────────────────────
    with subtab_compare:
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
                format_func=lambda x: f"{x} — {resolve_company_name(x)}"
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

            # 1. Grafico Comparativo Altman Z-Score
            st.markdown("#### 🛡️ Confronto Solvibilità & Altman Z-Score")
            
            fig_comp_z = go.Figure()
            colors_z = ["#00ff99" if z >= 2.99 else ("#ffcc00" if z >= 1.81 else "#ff3333") for z in z_df["Altman Z-Score"]]
            fig_comp_z.add_trace(go.Bar(
                x=z_df["Ticker"] + " (" + z_df["Azienda"] + ")",
                y=z_df["Altman Z-Score"],
                text=z_df["Altman Z-Score"].apply(lambda v: f"Z = {v:.2f}"),
                textposition='auto',
                marker_color=colors_z
            ))
            fig_comp_z.add_hline(y=2.99, line_dash="dash", line_color="#00ff99", annotation_text="Zona Sicura (2.99)", annotation_position="top right")
            fig_comp_z.add_hline(y=1.81, line_dash="dash", line_color="#ff3333", annotation_text="Zona Pericolo (1.81)", annotation_position="bottom right")
            fig_comp_z.update_layout(template="plotly_dark", height=320, title="Confronto Altman Z-Score aziendale", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_comp_z, use_container_width=True)

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
            radar_colors = ['#00ff99', '#00ccff', '#ff00ff', '#ffcc00', '#ff5555', '#a855f7']
            
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
                fig_comp_radar.add_trace(go.Scatterpolar(
                    r=vals, theta=categories, fill='toself',
                    name=f"{rep['company_name']} ({tk})",
                    line_color=radar_colors[idx % len(radar_colors)]
                ))
                
            fig_comp_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                template="plotly_dark", height=420,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_comp_radar, use_container_width=True)

            st.markdown("##### 📊 Matrice Comparativa degli Indici Fondamentali di Bilancio")
            st.dataframe(r_df, use_container_width=True, hide_index=True)

    # ── SUBTAB 3: PIOTROSKI F-SCORE, WACC & MULTIPLI DI MERCATO ────────────────
    with subtab_piotroski:
        st.markdown("### 🎯 Valutazione Quantitativa: Piotroski F-Score, WACC & Multipli")
        st.caption("Analisi fondamentale avanzata: diagnosi di salute contabile in 9 punti (Stanford Piotroski), stima WACC CAPM e comparazione dei multipli di mercato.")

        c_p1, c_p2 = st.columns([1, 2])
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
                    format_func=lambda x: f"{x} — {company_options[x]}" if company_options[x] != x else f"{x}",
                    key="selectbox_p_portfolio"
                )
            else:
                p_custom = st.text_input("Inserisci Ticker (es. GOOGL, AAPL, MSFT, NVDA, TSLA, RACE.MI):", value="GOOGL", key="text_p_custom")
                p_tk = p_custom.upper().strip()

            p_name = resolve_company_name(p_tk)
            
            wacc_data = compute_wacc_estimation(p_tk)
            st.markdown("#### 🧮 Calcolatore Dinamico WACC")
            st.markdown(f"**WACC Stimato per {p_tk}:** `{wacc_data['wacc_pct']}%`")
            st.caption(f"Cost of Equity ($r_e$): `{wacc_data['cost_of_equity_pct']}%` (Beta: `{wacc_data['beta']}`), Cost of Debt Net Tax ($r_d$): `{wacc_data['cost_of_debt_after_tax_pct']}%`")
            st.caption(f"Struttura Capitale: Equity `{wacc_data['weight_equity_pct']}%` | Debito `{wacc_data['weight_debt_pct']}%`")

        with c_p2:
            f_res = compute_piotroski_f_score(p_tk)
            st.markdown(f"#### 📊 Piotroski F-Score: **{f_res['score']} / {f_res['max_score']}** — {f_res['evaluation']}")
            st.dataframe(f_res["details_df"], use_container_width=True, hide_index=True)

        st.divider()

        st.markdown(f"#### 📊 Matrice dei Multipli di Mercato & Valuation Benchmark — {p_name} ({p_tk})")
        m_data = compute_valuation_multiples_matrix(p_tk)
        st.dataframe(m_data["multiples_table"], use_container_width=True, hide_index=True)


# ── TAB 5: VALUTAZIONE INTRINSECA DCF MONTE CARLO ─────────────────────
with tab5:
    st.markdown("### 🧮 Modello di Valutazione Intrinseca DCF Monte Carlo")
    st.caption("Stima il Fair Value intrinseco aziendale attualizzando i Flussi di Cassa Liberi (FCF) al WACC ed eseguendo 1,000 simulazioni stocastiche sui parametri chiave.")
    
    glossary_modal("📚 Guida al DCF Monte Carlo", """
    <p><b>1. Discounted Cash Flow (DCF):</b><br>
    Modello fondamentale di finanza aziendale che calcola il valore di un'impresa come valore attuale (PV) dei suoi flussi di cassa operativi futuri (FCF) più il valore terminale (Terminal Value).<br>
    - <b>WACC:</b> Costo Medio Ponderato del Capitale, utilizzato come tasso di attualizzazione.<br>
    - <b>Terminal Value:</b> Calcolato tramite la formula di Gordon Growth $TV = \\frac{FCF_5 \\cdot (1 + g)}{WACC - g}$.</p>
    <p><b>2. Simulazione Monte Carlo (1,000 Iterazioni):</b><br>
    A differenza del DCF tradizionale deterministico, il modello stocastico Monte Carlo varia simultaneamente il tasso di crescita del fatturato, il WACC ed il Terminal Growth per generare la distribuzione completa del Fair Value e calcolare la reale probabilità di sottovalutazione.</p>
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
                format_func=lambda x: f"{x} — {company_options[x]}" if company_options[x] != x else f"{x}",
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
        fig_dcf_hist = go.Figure()
        fig_dcf_hist.add_trace(go.Histogram(
            x=sim_vals,
            nbinsx=40,
            name="Fair Value Simulato",
            marker=dict(
                color="rgba(0, 255, 153, 0.6)",
                line=dict(color="#00ff99", width=1)
            )
        ))
        
        # Linee di riferimento
        fig_dcf_hist.add_vline(x=dcf_res["current_price"], line_dash="dash", line_color="#ff3333", annotation_text=f"Prezzo Attuale (€ {dcf_res['current_price']:.2f})", annotation_position="top right", annotation_font_size=11)
        fig_dcf_hist.add_vline(x=dcf_res["fair_value_median"], line_dash="solid", line_color="#00ff99", annotation_text=f"Mediana DCF (€ {dcf_res['fair_value_median']:.2f})", annotation_position="top left", annotation_font_size=11)
        fig_dcf_hist.add_vline(x=dcf_res["p10_bear_case"], line_dash="dot", line_color="#ffcc00", annotation_text=f"Bear Case 10% (€ {dcf_res['p10_bear_case']:.2f})", annotation_position="bottom left", annotation_font_size=11)
        fig_dcf_hist.add_vline(x=dcf_res["p90_bull_case"], line_dash="dot", line_color="#00ccff", annotation_text=f"Bull Case 90% (€ {dcf_res['p90_bull_case']:.2f})", annotation_position="bottom right", annotation_font_size=11)
        
        fig_dcf_hist.update_layout(
            title=f"Distribuzione del Fair Value Intrinseco — {dcf_name} ({dcf_tk})",
            xaxis_title="Fair Value Stimato (€ / $)",
            yaxis_title="Frequenza Simulazioni",
            template="plotly_dark",
            height=340,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_dcf_hist, use_container_width=True)

        st.markdown("##### 📋 Matrice di Sensibilità & Scenari DCF")
        df_dcf_scenarios = pd.DataFrame([
            {"Scenario": "🐻 Bear Case (10° Percentile)", "Fair Value per Azione": f"€ {dcf_res['p10_bear_case']:.2f}", "Upside/Downside": f"{((dcf_res['p10_bear_case']-dcf_res['current_price'])/dcf_res['current_price'])*100:+.1f}%"},
            {"Scenario": "⚖️ Base Case (Mediana Monte Carlo)", "Fair Value per Azione": f"€ {dcf_res['fair_value_median']:.2f}", "Upside/Downside": f"{dcf_res['upside_downside_pct']:+.1f}%"},
            {"Scenario": "🐂 Bull Case (90° Percentile)", "Fair Value per Azione": f"€ {dcf_res['p90_bull_case']:.2f}", "Upside/Downside": f"{((dcf_res['p90_bull_case']-dcf_res['current_price'])/dcf_res['current_price'])*100:+.1f}%"}
        ])
        st.dataframe(df_dcf_scenarios, use_container_width=True, hide_index=True)




