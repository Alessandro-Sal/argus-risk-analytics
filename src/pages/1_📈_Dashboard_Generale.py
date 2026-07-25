import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, section, metric_card, fmt_pct, fmt_eur, glossary_modal, render_executive_badges, render_command_bar, apply_plotly_theme, render_factor_radar_chart
from core.excel_generator import generate_excel_in_memory

st.set_page_config(page_title="Executive Cockpit | ARGUS", page_icon="📈", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
m   = results["metrics"]
ret = m["returns"]
mk  = m["market_risk"]
sr_port = results["portfolio_return"]
sr_bm   = results["benchmark_return"]
pos = results["positions"]

render_command_bar()
st.title("📈 Dashboard Generale — Executive Cockpit")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Quadro sintetico ad alta densità su performance, allocazione, impronta di rischio e conformità regolamentare.")

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
comp_score = limits_res["compliance_pct"]
cagr_val = float(ret.get("cagr_pct", ret.get("portfolio_cagr_pct", 0.0)) or 0.0)
tot_ret_val = float(ret.get("total_return_pct", 0.0) or 0.0)
var_val = float(mk.get("var_95", 0.0) or 0.0)
if var_val < 0.20 and var_val > 0.0:
    var_val = var_val * 100.0

st.markdown(f"""
<div style="background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(255, 153, 0, 0.25); border-left: 4px solid #ff9900; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px;">
    <div style="font-weight: 700; font-size: 15px; color: #ff9900; margin-bottom: 4px;">⚡ Sintesi Esecutiva Quantitativa — Status Portafoglio</div>
    <div style="font-size: 13.5px; color: #c9d1d9; line-height: 1.5;">
        Portafoglio attivo con controvalore totale di <b>€ {ret['portfolio_value']:,.2f}</b>. 
        Conformità del <b>{comp_score:.1f}%</b> sui 6 limiti di rischio regolamentari. 
        Sharpe Ratio a <b>{ret['sharpe_ratio']:.2f}</b> con rendimento annuo (CAGR) del <b>{cagr_val:.2f}%</b> (totale cumulato: <b>{tot_ret_val:+.2f}%</b>) e VaR 95% giornaliero al <b>{var_val:.2f}%</b>.
    </div>
</div>
""", unsafe_allow_html=True)



st.markdown("#### 💼 Riepilogo Portafoglio")
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Valore Portafoglio", fmt_eur(ret.get("portfolio_value")), help_text="<b>Cosa significa:</b> Il controvalore di mercato (Mark-to-Market) del portafoglio al momento attuale. Riflette la valutazione in tempo reale (o all'ultima chiusura disponibile) di tutti gli asset detenuti.\n\n<b>A cosa serve:</b> È il dato fondamentale per capire la dimensione economica dell'investimento. Risponde alla domanda: 'Se dovessi vendere tutto immediatamente ai prezzi di mercato correnti, quanto capitale otterrei?'\n\n<b>Come si calcola:</b> Si determina moltiplicando le quote nette detenute (acquisti - vendite storiche) di ogni singolo strumento per il rispettivo ultimo prezzo di chiusura ufficiale fornito dal mercato. La somma di tutti questi prodotti genera il valore totale.")
with col2:
    metric_card("PnL Totale", fmt_eur(ret.get("total_pnl")), 
                delta=f"{ret.get('total_pnl_pct', 0)*100:+.2f}%", 
                positive=(ret.get("total_pnl", 0) >= 0),
                help_text="<b>Cosa significa:</b> Profit & Loss (Profitti e Perdite) Totale. Misura la performance monetaria assoluta generata dall'intero portafoglio dall'inizio dell'investimento fino ad oggi.\n\n<b>A cosa serve:</b> A differenza delle percentuali, il PnL ti dà l'impatto economico reale e tangibile (in Euro) sulle tue finanze. Include ogni componente di rendimento: plusvalenze latenti, profitti/perdite già incassati (realizzati) e flussi di cassa (come i dividendi).\n\n<b>Come si calcola:</b> (Valore Attuale di Mercato + Totale PnL Realizzato su posizioni chiuse + Totale Dividendi incassati) diviso/sottratto al Costo Totale d'Acquisto (Cost Basis) iniziale e incrementale.")
with col3:
    metric_card("CAGR", fmt_pct(ret.get("cagr_pct")), help_text="<b>Cosa significa:</b> Compound Annual Growth Rate (Tasso Annuo di Crescita Composto). È il tasso di rendimento annuo costante che l'investimento avrebbe dovuto generare per passare dal saldo iniziale a quello finale.\n\n<b>A cosa serve:</b> È la metrica d'oro per misurare e confrontare le performance su periodi multi-anno. Il CAGR neutralizza la volatilità intermedia e l'effetto base, fornendo un tasso liscio e comparabile (ad esempio, con un conto deposito a tasso fisso o con l'inflazione).\n\n<b>Come si calcola:</b> ((Valore Finale del Portafoglio / Valore Iniziale Investito) elevato alla potenza di (1 / Numero totale di Anni)) - 1. Questo calcolo tiene conto dell'interesse composto (i guadagni che generano altri guadagni).")

st.markdown("#### ⚡ Metriche di Rischio e Rendimento")
col4, col5, col6 = st.columns(3)
with col4:
    metric_card("Sharpe Ratio", f"{ret.get('sharpe_ratio', 0):.2f}", help_text="<b>Cosa significa:</b> Ideato dal premio Nobel William Sharpe, misura l'efficienza del portafoglio in termini di rendimento corretto per il rischio.\n\n<b>A cosa serve:</b> Serve a capire se i tuoi guadagni sono frutto di un'ottima strategia o se stai solo prendendo rischi folli. Un valore < 1 è mediocre, > 1 è buono, > 2 è eccellente, > 3 è rarissimo e indica rendimenti stellari con pochissime oscillazioni. Ti permette di confrontare due portafogli con rendimenti simili ma volatilità diverse.\n\n<b>Come si calcola:</b> (Rendimento Annualizzato del Portafoglio - Tasso di Rendimento Risk-Free, es. Titoli di Stato a breve termine) diviso per la Volatilità Annualizzata (Deviazione Standard) del Portafoglio.")
with col5:
    metric_card("Max Drawdown", fmt_pct(mk.get("max_drawdown_pct")), positive=False, help_text="<b>Cosa significa:</b> Il Massimo Drawdown indica la peggior flessione storica (peak-to-trough) registrata dal portafoglio dal suo punto di massimo storico locale fino al minimo successivo, prima di un nuovo massimo.\n\n<b>A cosa serve:</b> È la misura principe del rischio di capitale e di 'tail risk' (rischio estremo). Risponde alla domanda: 'Se fossi stato così sfortunato da investire tutto nel momento di picco del mercato, quale sarebbe stata la percentuale massima del mio capitale che avrei visto andare in fumo prima di un recupero?'. Fondamentale per misurare la tolleranza emotiva alle perdite.\n\n<b>Come si calcola:</b> Si calcola tracciando la serie storica dei nuovi massimi. Per ogni punto, si misura la discesa percentuale rispetto all'ultimo massimo registrato. Il valore minimo assoluto di questa serie rappresenta il Max Drawdown.")
with col6:
    metric_card("VaR (95%) Storico", fmt_pct(mk.get("var_95")), positive=False, help_text="<b>Cosa significa:</b> Value at Risk (Valore a Rischio). È una stima probabilistica e quantitativa della massima perdita che ci si aspetta di subire in una singola giornata di contrattazione, con un livello di confidenza del 95%.\n\n<b>A cosa serve:</b> Serve per dimensionare il rischio quotidiano in scenari normali (escludendo i famosi 'cigni neri', che cadono nel restante 5%). Ti dice: 'Statisticamente parlando, per 19 giorni su 20 la perdita del mio portafoglio non dovrebbe superare questa precisa soglia percentuale'.\n\n<b>Come si calcola:</b> Ordinando tutti i rendimenti storici giornalieri del portafoglio dal peggiore al migliore, il VaR al 95% corrisponde esattamente al 5° percentile della distribuzione (il valore che separa il peggior 5% dei casi dal restante 95%).")

st.divider()

col_a, col_b = st.columns([2, 1])

with col_a:
    sr_bm_sliced = sr_bm.reindex(sr_port.index).fillna(0.0)
    cum_port = ((1 + sr_port).cumprod() - 1) * 100
    cum_bm   = ((1 + sr_bm_sliced).cumprod() - 1) * 100

    st.markdown("**Rendimento cumulato vs benchmark**")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cum_port.index, y=cum_port.values,
        name="Portafoglio", line=dict(color="#ff9900", width=2),
        hovertemplate="<b>%{x}</b><br>Portafoglio: %{y:.2f}%<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=cum_bm.index, y=cum_bm.values,
        name=mk["benchmark_ticker"],
        line=dict(color="#8fa0ba", width=1.5, dash="dash"),
        hovertemplate="<b>%{x}</b><br>Benchmark: %{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        yaxis_title="Rendimento %",
        height=450,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
    )
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)


with col_b:
    st.markdown("**Metriche rendimento**")
    data_ret = {
        "Metrica": ["CAGR", "Rendimento totale", "Alpha",
                    "Sharpe", "Sortino", "Calmar",
                    "Information Ratio", "Anni"],
        "Valore":  [
            fmt_pct(ret["cagr_pct"]),
            fmt_pct(ret["total_return_pct"]),
            fmt_pct(ret["alpha_pct"]),
            str(ret["sharpe_ratio"] or "N/A"),
            str(ret["sortino_ratio"] or "N/A"),
            str(ret["calmar_ratio"] or "N/A"),
            str(ret["information_ratio"] or "N/A"),
            str(ret["n_years"]),
        ]
    }
    st.dataframe(pd.DataFrame(data_ret), use_container_width=True, hide_index=True)

    glossary_modal("📚 Glossario Metriche Rendimento", """
<ul style="margin-top:0; padding-left:20px;">
    <li style="margin-bottom:12px;"><b>Alpha (di Jensen):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato:</b> L'Alpha misura la componente di rendimento del portafoglio che è completamente scollegata dai movimenti generali del mercato. È il "valore aggiunto".</li>
            <li><b>Utilità Pratica:</b> Un Alpha positivo (> 0) significa che il portafoglio ha generato un rendimento superiore a quello che ci si aspetterebbe dato il suo livello di rischio sistemico (Beta). È la metrica definitiva per valutare la reale abilità (skill).</li>
            <li><b>Calcolo:</b> <code>Alpha = Rendimento Portafoglio - [Tasso RiskFree + Beta * (Rendimento Benchmark - Tasso RiskFree)]</code>.</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>Sortino Ratio:</b>
        <ul style="margin-top:4px;">
            <li><b>Significato:</b> È un'evoluzione dello Sharpe Ratio. Mentre lo Sharpe penalizza sia la volatilità al rialzo che quella al ribasso, il Sortino penalizza <i>solo</i> la volatilità negativa.</li>
            <li><b>Utilità Pratica:</b> Molto più pertinente per gli investitori reali: nessuno si lamenta della volatilità quando i prezzi salgono bruscamente. Un Sortino alto indica che i rendimenti sono stati ottenuti subendo pochissimi ribassi marcati.</li>
            <li><b>Calcolo:</b> <code>(Rendimento Portafoglio - Tasso Target o RiskFree) / Downside Deviation</code>.</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>Calmar Ratio:</b>
        <ul style="margin-top:4px;">
            <li><b>Significato:</b> Rapporto che relaziona il rendimento annuo composto (CAGR) con il Massimo Drawdown subito negli ultimi 3 o 5 anni (o dall'inizio).</li>
            <li><b>Utilità Pratica:</b> È il rapporto prediletto dai gestori di hedge fund. Mostra quanti punti percentuali di rendimento ottieni per ogni punto percentuale di "sofferenza estrema". Valori > 1 sono considerati eccellenti.</li>
            <li><b>Calcolo:</b> <code>CAGR / |Max Drawdown|</code>.</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>Information Ratio:</b>
        <ul style="margin-top:4px;">
            <li><b>Significato:</b> Misura la capacità del gestore di generare extra-rendimento rispetto al benchmark rapportato al rischio attivo preso per ottenerlo (Tracking Error).</li>
            <li><b>Utilità Pratica:</b> Mostra l'efficienza della gestione attiva. Un valore superiore a 0.5 indica una gestione attiva di alto livello e costante nel tempo.</li>
            <li><b>Calcolo:</b> <code>(Rendimento Portafoglio - Rendimento Benchmark) / Tracking Error</code>.</li>
        </ul>
    </li>
    <li><b>Rendimento Totale (Total Return):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato:</b> La variazione percentuale pura del capitale dal giorno 1 a oggi.</li>
            <li><b>Utilità Pratica:</b> A differenza del CAGR che è annualizzato, il rendimento totale mostra la massa assoluta di crescita del patrimonio. Un CAGR del 10% per 10 anni si traduce in un Rendimento Totale di quasi il 160% grazie all'interesse composto.</li>
            <li><b>Calcolo:</b> <code>(Valore Finale / Valore Iniziale) - 1</code>.</li>
        </ul>
    </li>
</ul>
""", button_label="📖 Glossario Metriche")

st.divider()

# ── IMPRONTA DI RISCHIO 360° (RADAR FATTORIALE - SLEEK SINGLE ROW) ────
section("🕸️ Impronta di Rischio 360° (Radar Fattoriale)")

col_rd1, col_rd2 = st.columns([1.4, 1.0])

with col_rd1:
    fig_radar = render_factor_radar_chart(results)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_rd2:
    st.markdown("""
    <div style="background: rgba(22,27,34,0.7); border: 1px solid rgba(255,153,0,0.3); border-radius: 12px; padding: 18px; margin-top: 5px;">
        <div style="font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 6px;">💡 Diagnostica Fattoriale 360°</div>
        <div style="font-size: 12px; color: #8b949e; margin-bottom: 12px; line-height: 1.4;">
            Mappa l'impronta quantitativa del portafoglio identificando la distribuzione del rischio su 6 pilastri fondamentali:
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; font-size: 11px; margin-bottom: 14px;">
            <span style="background: rgba(63,185,80,0.15); border: 1px solid rgba(63,185,80,0.4); color: #3fb950; padding: 4px 8px; border-radius: 12px;">🟢 Market Beta</span>
            <span style="background: rgba(88,166,255,0.15); border: 1px solid rgba(88,166,255,0.4); color: #58a6ff; padding: 4px 8px; border-radius: 12px;">🔵 Size SMB</span>
            <span style="background: rgba(188,140,255,0.15); border: 1px solid rgba(188,140,255,0.4); color: #bc8cff; padding: 4px 8px; border-radius: 12px;">🟣 Value HML</span>
            <span style="background: rgba(210,153,34,0.15); border: 1px solid rgba(210,153,34,0.4); color: #d29922; padding: 4px 8px; border-radius: 12px;">🟡 Volatilità</span>
            <span style="background: rgba(63,185,80,0.15); border: 1px solid rgba(63,185,80,0.4); color: #3fb950; padding: 4px 8px; border-radius: 12px;">🟢 Diversificazione DR</span>
            <span style="background: rgba(248,81,73,0.15); border: 1px solid rgba(248,81,73,0.4); color: #f85149; padding: 4px 8px; border-radius: 12px;">🔴 Skewness</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    glossary_modal("🕸️ Guida all'Impronta di Rischio 360° (Radar Fattoriale)", """
<p>Un grafico Spider/Radar che mappa l'impronta digitale del portafoglio su 6 fattori di rischio fondamentali:</p>
<ul style="padding-left:20px;">
    <li style="margin-bottom:8px;"><b>Market Beta:</b> Sensibilità al mercato azionario generale (S&P 500).</li>
    <li style="margin-bottom:8px;"><b>Size SMB:</b> Inclinazione verso titoli Small Cap (> 0) o Large Cap (< 0).</li>
    <li style="margin-bottom:8px;"><b>Value HML:</b> Inclinazione verso titoli Value (> 0) o Growth (< 0).</li>
    <li style="margin-bottom:8px;"><b>Volatilità:</b> Ampiezza delle oscillazioni annue del capitale.</li>
    <li style="margin-bottom:8px;"><b>Diversificazione DR:</b> Beneficio di de-correlazione tra gli asset (Diversification Ratio).</li>
    <li style="margin-bottom:8px;"><b>Asimmetria Skew:</b> Tendenza verso guadagni regolari vs perdite estreme (tail risk).</li>
</ul>
""", button_label="📖 Guida al Radar 360°")

st.divider()

# ── ARGUS Smart Risk Advisor Panel ─────────────────────────────
section("🛡️ ARGUS Quant Advisor & Diagnostica Automatizzata")

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
section("🚨 Controllo Limiti di Rischio & Early Warning")
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
    
    glossary_modal("📖 Guida al Controllo Limiti di Rischio", """
<p>Il sistema di <b>Early Warning</b> confronta il portafoglio rispetto a 6 limiti di rischio istituzionali stabiliti dai gestori per la protezione del capitale:</p>
<ul>
    <li><b>Peso Max Singola Posizione (≤ 20%):</b> Limita il rischio di fallimento di una singola azienda.</li>
    <li><b>Concentrazione Settoriale (≤ 35%):</b> Previene l'esposizione eccessiva a uno specifico settore.</li>
    <li><b>Value at Risk Max (VaR 95% ≤ 3%):</b> Monitora che la massima perdita giornaliera attesa non superi la tolleranza.</li>
    <li><b>Beta Sistemico Max (≤ 1.25):</b> Limita la sensibilità del portafoglio alle fasi di crollo di mercato.</li>
    <li><b>Diversification Ratio Min (≥ 1.20):</b> Garantisce un reale beneficio di decorrelazione tra i titoli.</li>
    <li><b>Indice HHI Max (≤ 0.25):</b> Controlla la dispersione matematica del capitale.</li>
</ul>
""", button_label="💡 Spiegazione Limiti di Rischio")

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
section("🌍 Esposizione Geografica & Settoriale (Sunburst Chart)")
st.caption("Visualizzazione gerarchica multilivello dell'allocazione del capitale: Paese ➔ Settore GICS ➔ Ticker.")

if not pos.empty:
    active_pos = pos[pos["qty_net"] > 0].copy() if "qty_net" in pos.columns else pos.copy()
    if "country" not in active_pos.columns:
        active_pos["country"] = "Stati Uniti"
    if "sector" not in active_pos.columns:
        active_pos["sector"] = "Tecnologia"
    
    active_pos["country"] = active_pos["country"].fillna("Stati Uniti")
    active_pos["sector"] = active_pos["sector"].fillna("Diversificato")

    import plotly.express as px
    fig_sunburst = px.sunburst(
        active_pos,
        path=["country", "sector", "ticker"],
        values="current_value",
        color="unrealized_pnl_pct" if "unrealized_pnl_pct" in active_pos.columns else None,
        color_continuous_scale=["#f85149", "#d29922", "#3fb950"],
        color_continuous_midpoint=0,
        labels={
            "current_value": "Controvalore (€)",
            "unrealized_pnl_pct": "PnL Latente (%)",
            "country": "Paese",
            "sector": "Settore",
            "ticker": "Asset"
        }
    )
    fig_sunburst.update_traces(
        hovertemplate="<b>%{label}</b><br>Controvalore: € %{value:,.2f}<br>PnL Latente: %{color:+.2f}%<extra></extra>"
    )
    fig_sunburst.update_layout(
        template="plotly_dark",
        coloraxis_colorbar=dict(title="PnL Latente %"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=20),
        height=400
    )
    st.plotly_chart(fig_sunburst, use_container_width=True)

    glossary_modal("🌍 Guida al Grafico Sunburst", """
<p>Il diagramma <b>Sunburst</b> organizza graficamente la struttura del capitale in anelli concentrici:</p>
<ul>
    <li><b>Anello Interno:</b> Distribuzione geografica per Paese/Regione (es. USA, Italia, Danimarca).</li>
    <li><b>Anello Intermedio:</b> Suddivisione in Settori GICS (es. Technology, Financials, Healthcare).</li>
    <li><b>Anello Esterno:</b> Singoli titoli detenuti (size proporzionale al valore in €).</li>
    <li><b>Colore:</b> PnL non realizzato % (Verde = Profitto, Rosso = Perdata).</li>
</ul>
""", button_label="💡 Come leggere il Sunburst?")

st.divider()

# ── CENTRO ESPORTAZIONE REPORT & DATI (IN FONDO ALLA PAGINA) ──
section("📥 Centro Esportazione Report & Power BI Data Pack")
st.caption("Esporta il Factsheet Executive PDF, il Workbook Excel Multi-Tab completo o scarica il pacchetto Star Schema per Power BI (.zip).")

col_exp_pdf, col_exp_excel, col_exp_bi = st.columns(3)

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
