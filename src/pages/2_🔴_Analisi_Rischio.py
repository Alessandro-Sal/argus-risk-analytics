import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.graph_objects as go
import plotly.express as px
from core.ui_utils import inject_custom_css, fmt_pct, metric_card, glossary_modal, apply_plotly_theme, render_risk_heatmap


st.set_page_config(page_title="Analisi Rischio | ARGUS", page_icon="🔴", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
mk = results["metrics"]["market_risk"]
con = results["metrics"].get("concentration", {})
sr_port = results["portfolio_return"]
pos = results["positions"]

st.title("🔴 Analisi del Rischio")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Diagnostica quantitativa del rischio di mercato, VaR 95/99%, Tail Risk, modelli Fama-French, ATR Chandelier Exit e ML Anomaly Detection.")
st.divider()

# Struttura a 4 Tab Tematiche
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Profilo del Rischio & Fama-French",
    "📉 VaR, CVaR & Backtesting Kupiec",
    "🔗 Correlazioni, Liquidità & ATR Chandelier",
    "🕵️‍♂️ Rilevatore Anomalie ML (Isolation Forest)"
])

# ==============================================================================
# TAB 1: PROFILO DEL RISCHIO & FAMA-FRENCH
# ==============================================================================
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card(
            "Rischio Mercato (Beta)",
            f"{mk.get('beta', 0) if mk.get('beta') else 0:.2f}",
            help_text="<b>Cosa significa:</b> Il Beta misura il rischio sistematico e la sensibilità del portafoglio rispetto al mercato di riferimento (S&P 500).\n\n<b>A cosa serve:</b> Identifica la reattività del capitale agli shock macroeconomici. Un Beta > 1 indica un portafoglio aggressivo che amplifica i movimenti del mercato; Beta < 1 indica un portafoglio difensivo."
        )
    with col2:
        metric_card(
            "Rischio Concentrazione",
            f"{con.get('hhi', 0) * 10000:.0f} / 10000",
            help_text="<b>Cosa significa:</b> Indice Herfindahl-Hirschman (HHI) di concentrazione, misurato su scala 0-10.000.\n\n<b>A cosa serve:</b> Monitora se il patrimonio dipende dalle sorti di pochissimi titoli. Un HHI < 1.500 indica un'ottima diversificazione; un HHI > 2.500 segnala una forte concentrazione del rischio."
        )
    with col3:
        metric_card(
            "Volatilità Annua",
            fmt_pct(mk.get("volatility_annual_pct")),
            positive=False,
            help_text="<b>Cosa significa:</b> Misura la dispersione dei rendimenti del portafoglio attorno alla loro media su base annua.\n\n<b>A cosa serve:</b> È l'indicatore principe della variabilità di breve-medio termine."
        )
    with col4:
        metric_card(
            "Ulcer Index (UI)",
            f"{mk.get('ulcer_index', 0.0):.2f}",
            positive=False,
            help_text="<b>Cosa significa:</b> Indice quantitativo che misura la profondità e la durata temporale delle flessioni sotto i massimi storici (High-Water Mark)."
        )

    st.markdown("#### 🏛️ Style Analysis (Fama-French 3-Factor Model)")
    glossary_modal("ℹ️ Guida al Fama-French 3-Factor Model & Ulcer Index", """
    <p><b>1. Cos'è il Fama-French 3-Factor Model?</b><br>
    Un modello econometrico premio Nobel che scompone il rendimento del portafoglio in 3 fattori chiave:<br>
    • <b>Market Beta</b>: Esposizione al mercato generale.<br>
    • <b>SMB Tilt (Size)</b>: Inclinazione verso titoli a bassa capitalizzazione (Small Cap).<br>
    • <b>HML Tilt (Value)</b>: Inclinazione verso titoli Value (sottovalutati/alti dividendi) vs Growth.</p>
    <p><b>2. Cos'è l'Ulcer Index?</b><br>
    Un indice quantitativo che penalizza sia la profondità delle perdite sia il tempo necessario per recuperare i massimi storici.</p>
    """, button_label="💡 Come funziona il Fama-French 3-Factor Model?")

    ff_c1, ff_c2, ff_c3, ff_c4 = st.columns(4)
    with ff_c1:
        metric_card(
            "Alpha Fama-French",
            f"{mk.get('ff_alpha_pct', 0.0):+.2f}%",
            positive=(mk.get('ff_alpha_pct', 0.0) >= 0),
            help_text="L'extra-rendimento annuo puro del portafoglio, depurato dagli effetti di mercato, dimensione (SMB) e valore (HML)."
        )
    with ff_c2:
        metric_card(
            "Market Beta (FF)",
            f"{mk.get('ff_beta_mkt', 1.0):.2f}",
            help_text="La sensibilità del portafoglio rispetto all'indice di mercato generale all'interno della regressione a 3 fattori."
        )
    with ff_c3:
        metric_card(
            "SMB Tilt (Size)",
            f"{mk.get('smb_tilt', 0.0):+.2f}",
            positive=(mk.get('smb_tilt', 0.0) >= 0),
            help_text="Fattore Small Minus Big. Misura l'inclinazione del portafoglio verso aziende a piccola capitalizzazione (Small Cap)."
        )
    with ff_c4:
        metric_card(
            "HML Tilt (Value)",
            f"{mk.get('hml_tilt', 0.0):+.2f}",
            positive=(mk.get('hml_tilt', 0.0) >= 0),
            help_text="Fattore High Minus Low. Misura l'orientamento verso azioni Value rispetto a titoli Growth."
        )

    st.divider()

    st.markdown("#### 🧩 Scomposizione del Rischio (Component VaR)")
    glossary_modal("Cos'è la Scomposizione del Rischio?", 
    "Questa sezione mostra quale percentuale del rischio totale (volatilità) del portafoglio è attribuibile a ciascun asset. Ti permette di capire quali sono gli strumenti che stanno trainando l'instabilità del tuo investimento.", 
    button_label="💡 Come si legge?")

    risk_contrib = results.get("risk_contribution", {})
    if risk_contrib:
        df_rc = pd.DataFrame(list(risk_contrib.items()), columns=["Asset", "Contributo %"])
        df_rc = df_rc.sort_values(by="Contributo %", ascending=False)
        col_rc1, col_rc2 = st.columns([1, 2])
        with col_rc1:
            st.dataframe(df_rc, use_container_width=True, hide_index=True, height=350)
        with col_rc2:
            st.markdown("**Scomposizione percentuale del Rischio (Volatilità)**")
            fig_rc = px.pie(
                df_rc, values="Contributo %", names="Asset", hole=0.65,
                color_discrete_sequence=["#58a6ff", "#bc8cff", "#3fb950", "#d29922", "#f0883e", "#ff7b72"]
            )
            fig_rc.update_traces(
                textposition='inside', textinfo='percent+label',
                marker=dict(line=dict(color='#0d1117', width=2)),
                hovertemplate="<b>Asset: %{label}</b><br>🎯 Contributo al Rischio: %{value:.2f}%<extra></extra>"
            )
            fig_rc.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
            )
            apply_plotly_theme(fig_rc)
            st.plotly_chart(fig_rc, use_container_width=True)

        st.markdown("**Risk Heatmap Grid (Mappa di Calore Rischio/PnL)**")
        glossary_modal("ℹ️ Guida alla Risk Heatmap Grid", """
        <p><b>Cos'è la Risk Heatmap Grid?</b><br>
        Una visualizzazione gerarchica a mappa di calore (Treemap) ad alta densità usata nella gestione professionale di portafoglio. La dimensione di ciascun rettangolo rappresenta il <b>controvalore in Euro</b> allocato nel titolo, mentre il colore mostra la <b>plusvalenza/perdenza non realizzata (PnL)</b> ed il contributo al VaR di portafoglio.</p>
        """, button_label="💡 Come funziona la Risk Heatmap Grid?")
        fig_hm = render_risk_heatmap(pos, risk_contrib)
        if fig_hm:
            st.plotly_chart(fig_hm, use_container_width=True)
    else:
        st.info("Impossibile calcolare la scomposizione del rischio (pochi dati storici o troppi pochi asset validi).")


# ==============================================================================
# TAB 2: VAR, CVAR & BACKTESTING KUPIEC
# ==============================================================================
with tab2:
    st.markdown("### 🛠️ Calcolatore e Simulatore VaR Dinamico")
    st.caption("Questo strumento consente di calcolare il Value at Risk (VaR) e l'Expected Shortfall (CVaR) a livello di portafoglio, modificando dinamicamente i parametri di rischio.")

    glossary_modal("ℹ️ Guida al VaR, CVaR Cornish-Fisher e Test di Kupiec", """
    <p><b>1. cos'è il VaR Cornish-Fisher?</b><br>
    Il VaR Parametrico classico presuppone che i rendimenti seguano una curva Gaussiana perfetta. Il VaR <b>Cornish-Fisher</b> corregge questa assunzione integrando l'asimmetria (Skewness) e l'eccesso di curtosi (Kurtosis) reali delle serie storiche, catturando meglio la probabilità di perdite estreme nelle "code grasse".</p>

    <p><b>2. Cos'è l'Expected Shortfall (CVaR)?</b><br>
    Mentre il VaR risponde a "Qual è la soglia di perdita minima nel x% dei casi?", il <b>CVaR (Expected Shortfall)</b> indica qual è la perdita media attesa quando quella soglia viene superata.</p>

    <p><b>3. Cos'è il Backtesting di Kupiec (Semaforo di Basilea)?</b><br>
    Valida l'accuratezza del modello VaR valutando quante volte la perdita reale storica ha superato la soglia prevista. 
    <br>• 🟢 <b>Zona Verde</b>: Modello accurato e affidabile (eccezioni sotto la soglia).
    <br>• 🟡 <b>Zona Gialla</b>: Modello sotto osservazione (sottostima lieve).
    <br>• 🔴 <b>Zona Rossa</b>: Modello rigettato (sottostima grave del rischio).</p>
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

    # Layout metriche
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(
            label=f"VaR Storico ({holding_period}g)",
            value=f"{var_hist_t*100:.2f}%",
            delta=f"-€{var_hist_eur:,.2f}",
            delta_color="inverse"
        )
    with col_m2:
        st.metric(
            label=f"VaR Parametrico ({holding_period}g)",
            value=f"{var_param_t*100:.2f}%",
            delta=f"-€{var_param_eur:,.2f}",
            delta_color="inverse"
        )
    with col_m3:
        st.metric(
            label=f"VaR Cornish-Fisher ({holding_period}g)",
            value=f"{var_cf_t*100:.2f}%",
            delta=f"-€{var_cf_eur:,.2f}",
            delta_color="inverse"
        )
    with col_m4:
        st.metric(
            label=f"Expected Shortfall (CVaR - {holding_period}g)",
            value=f"{cvar_hist_t*100:.2f}%",
            delta=f"-€{cvar_hist_eur:,.2f}",
            delta_color="inverse"
        )

    with st.expander("📚 Dettaglio Formule e Teoria Finanziaria"):
        st.markdown(r"""
        ### Value at Risk (VaR)
        Il **Value at Risk (VaR)** rappresenta la massima perdita potenziale che un portafoglio può subire in un determinato orizzonte temporale ($T$) con un certo livello di confidenza ($c = 1 - \alpha$).
        
        1. **VaR Storico (Non-Parametrico)**:
           $$VaR_{storico} = -Q(R_p, \alpha)$$
           
        2. **VaR Parametrico (Varianza-Covarianza)**:
           $$VaR_{param} = -(\mu_p + z_{\alpha} \cdot \sigma_p)$$
           
        3. **VaR Cornish-Fisher**:
           $$z_{cf} = z + \frac{1}{6}(z^2-1)s + \frac{1}{24}(z^3-3z)k - \frac{1}{36}(2z^3-5z)s^2$$
           $$VaR_{cf} = -(\mu_p + z_{cf} \cdot \sigma_p)$$
        
        4. **Expected Shortfall (ES / CVaR)**:
           $$ES_{\alpha} = -E[R_p \mid R_p \le -VaR_{\alpha}]$$
        """)

    st.divider()

    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.markdown("**Metriche di Rischio Principali**")
        glossary_modal("📚 Glossario Approfondito Metriche di Rischio", """
        <ul style="margin-top:0; padding-left:20px;">
            <li><b>Tracking Error</b>: Deviazione standard del rendimento attivo rispetto al benchmark.</li>
            <li><b>Skewness</b>: Asimmetria della distribuzione (valori negativi = rischio crolli).</li>
            <li><b>Kurtosis</b>: Curtosi o concentrazione nelle code grasse.</li>
            <li><b>CVaR</b>: Perdita media attesa condizionata al superamento del VaR.</li>
        </ul>
        """, button_label="📖 Leggi Definizioni")
        data_mk = {
            "Metrica": ["Volatilità annua", "Tracking Error", "Skewness", "Kurtosis",
                        "VaR 95% (Storico)", "VaR 95% (Parametrico)", "VaR 95% (Cornish-Fisher)",
                        "VaR 99% (Storico)", "CVaR 95%", "CVaR 99%",
                        "Beta", "Correlazione", "R-Squared (Sistemico)", "Max Drawdown", "VaR Exceptions (1Y)"],
            "Valore": [
                fmt_pct(mk["volatility_annual_pct"]),
                fmt_pct(mk.get("tracking_error_pct", 0)),
                f"{mk.get('skewness', 0):.2f}",
                f"{mk.get('kurtosis', 0):.2f}",
                fmt_pct(mk["var_95"]),
                fmt_pct(mk.get("var_parametric_95", 0)),
                fmt_pct(mk.get("var_cf_95", 0)),
                fmt_pct(mk["var_99"]),
                fmt_pct(mk["cvar_95"]),
                fmt_pct(mk["cvar_99"]),
                str(mk["beta"] or "N/A"),
                str(mk["correlation_benchmark"] or "N/A"),
                fmt_pct(mk.get("r_squared_pct", 0)),
                fmt_pct(mk["max_drawdown_pct"]),
                f"{mk.get('var_exceptions_count', 0)} giorni",
            ]
        }
        st.dataframe(pd.DataFrame(data_mk), use_container_width=True, hide_index=True, height=520)

    with col_r2:
        st.markdown("**Distribuzione Rendimenti Giornalieri e Coda di Rischio**")
        fig_hist = go.Figure()
        
        # Array di rendimenti per evidenziare la coda a rischio
        ret_vals = sr_port.values * 100
        
        fig_hist.add_trace(go.Histogram(
            x=ret_vals,
            nbinsx=55,
            name="Rendimenti giornalieri",
            marker=dict(
                color="#58a6ff",
                line=dict(color="#0d1117", width=0.8)
            ),
            opacity=0.85,
            hovertemplate="<b>Rendimento: %{x:.2f}%</b><br>Frequenza: %{y}<extra></extra>"
        ))
        
        # Linea VaR
        fig_hist.add_vline(
            x=-var_hist_1d * 100, line_color="#ff9900", line_dash="dash", line_width=2,
            annotation_text=f"VaR {int(conf_level*100)}%: -{var_hist_1d*100:.2f}%",
            annotation_position="top right",
            annotation_font=dict(color="#ff9900", size=11)
        )
        
        # Linea CVaR
        fig_hist.add_vline(
            x=-cvar_hist_1d * 100, line_color="#f85149", line_dash="dot", line_width=2,
            annotation_text=f"CVaR: -{cvar_hist_1d*100:.2f}%",
            annotation_position="top left",
            annotation_font=dict(color="#f85149", size=11)
        )
        
        # Evidenziazione Coda Estrema (Tail Risk Zone)
        fig_hist.add_vrect(
            x0=r.min() * 100, x1=-var_hist_1d * 100,
            fillcolor="rgba(248, 81, 73, 0.20)",
            layer="below", line_width=0
        )
        
        fig_hist.update_layout(
            xaxis_title="Rendimento Giornaliero %",
            yaxis_title="Frequenza Giorni",
            template="plotly_dark", height=370,
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            margin=dict(l=10, r=10, t=15, b=20),
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

    fig_dd = go.Figure(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy", fillcolor="rgba(248, 81, 73, 0.15)",
        line=dict(color="#f85149", width=2.2),
        name="Drawdown",
        hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>🔻 Drawdown: %{y:.2f}%<extra></extra>"
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

    st.markdown("#### 🔬 Validazione e Backtesting dei Modelli VaR (Kupiec Test)")
    st.caption(f"Verifica l'efficacia statistica dei tre modelli di VaR (Storico, Parametrico e Cornish-Fisher) ad un orizzonte di 1 giorno su {int(conf_level*100)}% confidenza.")

    glossary_modal("Cos'è il Backtesting del VaR?", """
    <p>Il <b>Backtesting del VaR</b> (Kupiec Test) verifica quante volte la perdita reale storicamente ha superato la stima del VaR.</p>
    <ul>
        <li><b>🟢 Verde:</b> Modello solido e prudente.</li>
        <li><b>🟡 Giallo:</b> Sotto-stima lieve.</li>
        <li><b>🔴 Rosso:</b> Sotto-stima grave (modello rigettato).</li>
    </ul>
    """, button_label="💡 Come funziona il Backtesting?")

    recent_r = r.tail(252)
    n_days = len(recent_r)
    expected_exc = n_days * alpha

    exc_hist = len(recent_r[recent_r < threshold_hist_1d])
    exc_param = len(recent_r[recent_r < -var_param_1d])
    exc_cf = len(recent_r[recent_r < -var_cf_1d])

    ratio_hist = (exc_hist / n_days) * 100
    ratio_param = (exc_param / n_days) * 100
    ratio_cf = (exc_cf / n_days) * 100

    def get_basel_zone(exc_count, expected):
        if exc_count <= expected:
            return "🟢 Modello Valido (Conservativo)"
        elif exc_count <= expected * 1.5:
            return "🟡 Modello Accettabile (Sotto-stima lieve)"
        else:
            return "🔴 Modello Debole (Sotto-stima grave)"

    df_backtest = pd.DataFrame({
        "Modello VaR": ["Storico", "Parametrico (Gaussiano)", "Cornish-Fisher"],
        "Soglia VaR (1g)": [f"{var_hist_1d * 100:.2f}%", f"{var_param_1d * 100:.2f}%", f"{var_cf_1d * 100:.2f}%"],
        "Eccezioni Reali (252g)": [exc_hist, exc_param, exc_cf],
        "Tasso di Violazione": [f"{ratio_hist:.2f}%", f"{ratio_param:.2f}%", f"{ratio_cf:.2f}%"],
        "Target Violazioni": [f"{alpha * 100:.1f}%", f"{alpha * 100:.1f}%", f"{alpha * 100:.1f}%"],
        "Stato (Basel Accord)": [get_basel_zone(exc_hist, expected_exc), get_basel_zone(exc_param, expected_exc), get_basel_zone(exc_cf, expected_exc)]
    })

    col_bt_tbl, col_bt_desc = st.columns([2, 1])
    with col_bt_tbl:
        st.dataframe(df_backtest, use_container_width=True, hide_index=True)
    with col_bt_desc:
        st.info(f"""
        **Come leggere i risultati:**
        * **Eccezioni Attese**: In {n_days} giorni di trading, ci aspettiamo circa **{expected_exc:.1f} violazioni**.
        * **🟢 Zona Verde**: Modello solido.
        * **🟡 Zona Gialla**: Sottostima lieve.
        * **🔴 Zona Rossa**: Troppe violazioni. Modello inaffidabile.
        """)


# ==============================================================================
# TAB 3: CORRELAZIONI, LIQUIDITÀ & ATR CHANDELIER
# ==============================================================================
with tab3:
    st.markdown("### 🔗 Matrice di Correlazione tra Asset")
    df_ret_all = results["returns"].dropna(how="all")
    active_t = pos[pos["qty_net"] > 0]["ticker"].tolist()
    common_t = [t for t in active_t if t in df_ret_all.columns]

    if len(common_t) > 1:
        corr_matrix = df_ret_all[common_t].corr().round(2)
        fig_corr = px.imshow(
            corr_matrix,
            color_continuous_scale=[[0.0, "#d90429"], [0.5, "#161b22"], [1.0, "#58a6ff"]],
            zmin=-1, zmax=1,
            text_auto=".2f",
            labels={"x": "Asset 1", "y": "Asset 2", "color": "Correlazione (ρ)"}
        )
        fig_corr.update_traces(
            hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>🔗 Correlazione (ρ): %{z:+.2f}<extra></extra>"
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

    st.markdown("### 💧 Rischio di Liquidità (Days-to-Liquidate)")
    glossary_modal("Cos'è il Rischio di Liquidità?", 
    "È la stima dei giorni necessari per liquidare completamente la posizione senza muovere il mercato (ipotizzando di non superare il 15% del Volume Medio Giornaliero).", 
    button_label="💡 Come si legge?")

    if "days_to_liquidate" in pos.columns:
        df_liq = pos[pos["qty_net"] > 0][["ticker", "current_value", "days_to_liquidate"]].copy()
        df_liq = df_liq.sort_values(by="days_to_liquidate", ascending=False)
        
        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            st.dataframe(df_liq, use_container_width=True, hide_index=True)
        with col_l2:
            if df_liq["days_to_liquidate"].max() > 5:
                st.warning(f"Attenzione: alcuni asset richiedono più di 5 giorni per essere liquidati. L'asset più illiquido è **{df_liq.iloc[0]['ticker']}** con **{df_liq.iloc[0]['days_to_liquidate']:.1f} giorni**.")
            else:
                st.success("Il portafoglio è altamente liquido. Tutte le posizioni possono essere smobilizzate in tempi rapidi senza impatto significativo sui prezzi.")
    else:
        st.info("Dati sui volumi non sufficienti per calcolare i Days-to-Liquidate.")

    st.divider()

    st.markdown("### 🛡️ ATR Trailing Stop-Loss & Chandelier Exit Manager")
    st.caption("Livelli quantitativi di stop-loss dinamici ancorati alla volatilità effettiva ($ATR_{14}$) e ai massimi a 22 giorni per ciascun asset.")

    glossary_modal(
        "🛡️ Cos'è l'ATR Trailing Stop-Loss & Chandelier Exit?",
        """
        <p><b>Cos'è il Chandelier Exit?</b><br>
        Un algoritmo quantitativo che calcola un livello di stop-loss dinamico agganciato al massimo degli ultimi 22 giorni, sottratto di un multiplo della volatilità reale ($3 \\times ATR_{14}$).</p>
        """,
        button_label="💡 Come funciona il Chandelier Exit?"
    )

    df_prices_all = results.get("df_prices", pd.DataFrame())
    pos_df = results.get("positions", pd.DataFrame())

    if not pos_df.empty:
        from core.risk_engine import compute_atr_chandelier_exits
        atr_res = compute_atr_chandelier_exits(df_prices_all, pos_df, period=14, multiplier=3.0)
        
        col_atr1, col_atr2 = st.columns([1, 2.5])
        with col_atr1:
            trig_cnt = atr_res.get("stop_triggered_count", 0)
            metric_card(
                "Titoli in Trigger Stop-Loss",
                f"{trig_cnt}",
                positive=(trig_cnt == 0),
                help_text="Numero di asset la cui quotazione attuale ha infranto la soglia di Chandelier Exit."
            )
        with col_atr2:
            df_atr_disp = atr_res.get("summary_df", pd.DataFrame())
            if isinstance(df_atr_disp, pd.DataFrame) and not df_atr_disp.empty:
                df_atr_formatted = df_atr_disp.rename(columns={
                    "ticker": "Ticker",
                    "last_price": "Prezzo Mkt (€)",
                    "atr_14": "ATR 14g (€)",
                    "highest_high_22": "Max 22g (€)",
                    "chandelier_stop": "Chandelier Stop (€)",
                    "distance_pct": "Distanza Stop %",
                    "stop_triggered": "Stato Alert"
                })
                if "Stato Alert" in df_atr_formatted.columns:
                    df_atr_formatted["Stato Alert"] = df_atr_formatted["Stato Alert"].apply(lambda x: "🔴 TRIGGER" if x else "🟢 REGOLARE")
                st.dataframe(
                    df_atr_formatted.style.format({
                        "Prezzo Mkt (€)": "€ {:,.2f}",
                        "ATR 14g (€)": "€ {:,.2f}",
                        "Max 22g (€)": "€ {:,.2f}",
                        "Chandelier Stop (€)": "€ {:,.2f}",
                        "Distanza Stop %": "{:+.2f}%"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Dati storici sui prezzi insufficienti per il calcolo dell'ATR.")


# ==============================================================================
# TAB 4: RILEVATORE ANOMALIE ML (ISOLATION FOREST)
# ==============================================================================
with tab4:
    st.markdown("### 🕵️‍♂️ Machine Learning Anomaly Detector (Isolation Forest & Correlation Drift)")
    st.caption("Algoritmo di Machine Learning non supervisionato (Isolation Forest) per l'identificazione automatica di anomalie di rendimento, rotture di correlazione e giornate di stress di mercato.")

    glossary_modal("🕵️‍♂️ Guida al Rilevatore di Anomalie ML (Isolation Forest)", """
    <p><b>1. Cos'è l'Isolation Forest?</b><br>
    Un algoritmo di Machine Learning non supervisionato che isola le anomalie partizionando in modo casuale le feature (rendimento, volatilità 20g, correlazione media, drawdown).</p>
    """, button_label="💡 Come funziona il Rilevatore di Anomalie ML?")

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
            hovertemplate="<b>Data: %{x}</b><br>📈 Rendimento: %{y:+.2f}%<extra></extra>"
        ))
        fig_iso.add_trace(go.Scatter(
            x=df_anom["Data"], y=df_anom["Rendimento Portafoglio %"],
            mode="markers", name="🔴 Anomalia Rilevata (ML)",
            marker=dict(color="#d90429", size=10, symbol="x", line=dict(width=2, color="#ffffff")),
            hovertemplate="<b>⚠️ ANOMALIA ML: %{x}</b><br>⚡ Rendimento: %{y:+.2f}%<extra></extra>"
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
