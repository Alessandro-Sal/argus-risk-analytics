import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from core.ui_utils import inject_custom_css, fmt_pct, metric_card, glossary_modal, apply_plotly_theme, render_risk_heatmap, render_executive_badges


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
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Diagnostica quantitativa del rischio di mercato, VaR 95/99%, Tail Risk, modelli Fama-French e scomposizione della volatilità.")
st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card(
        "Rischio Mercato (Beta)",
        f"{mk.get('beta', 0) if mk.get('beta') else 0:.2f}",
        help_text="<b>Cosa significa:</b> Il Beta misura il rischio sistematico e la sensibilità del portafoglio rispetto al mercato di riferimento (S&P 500).\n\n<b>A cosa serve:</b> Identifica la reattività del capitale agli shock macroeconomici. Un Beta > 1 indica un portafoglio aggressivo che amplifica i movimenti del mercato; Beta < 1 indica un portafoglio difensivo.\n\n<b>Come si calcola:</b> Rapporto tra la covarianza dei rendimenti del portafoglio con il benchmark e la varianza dei rendimenti del benchmark."
    )
with col2:
    metric_card(
        "Rischio Concentrazione",
        f"{con.get('hhi', 0) * 10000:.0f} / 10000",
        help_text="<b>Cosa significa:</b> Indice Herfindahl-Hirschman (HHI) di concentrazione, misurato su scala 0-10.000.\n\n<b>A cosa serve:</b> Monitora se il patrimonio dipende dalle sorti di pochissimi titoli. Un HHI < 1.500 indica un'ottima diversificazione; un HHI > 2.500 segnala una forte concentrazione del rischio.\n\n<b>Come si calcola:</b> Somma dei quadrati dei pesi percentuali di ciascun asset detenuto nel portafoglio."
    )
with col3:
    metric_card(
        "Volatilità Annua",
        fmt_pct(mk.get("volatility_annual_pct")),
        positive=False,
        help_text="<b>Cosa significa:</b> Misura la dispersione dei rendimenti del portafoglio attorno alla loro media su base annua.\n\n<b>A cosa serve:</b> È l'indicatore principe della variabilità di breve-medio termine. Permette di valutare l'ampiezza delle oscillazioni del capitale durante la detenzione.\n\n<b>Come si calcola:</b> Deviazione standard dei rendimenti giornalieri moltiplicata per la radice quadrata di 252 giorni lavorativi (sqrt(252))."
    )
with col4:
    metric_card(
        "Ulcer Index (UI)",
        f"{mk.get('ulcer_index', 0.0):.2f}",
        positive=False,
        help_text="<b>Cosa significa:</b> Indice quantitativo che misura la profondità e la durata temporale delle flessioni sotto i massimi storici (High-Water Mark).\n\n<b>A cosa serve:</b> Valuta lo stress psicologico ed emotivo subito dall'investitore durante le fasi di drawdown. Più il valore è basso, più il recupero dei massimi è stato rapido.\n\n<b>Come si calcola:</b> Radice quadrata della media dei quadrati di tutti i drawdown percentuali giornalieri."
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
        help_text="<b>Cosa significa:</b> L'extra-rendimento annuo puro del portafoglio, depurato dagli effetti di mercato, dimensione (SMB) e valore (HML).\n\n<b>A cosa serve:</b> Isolamento della vera capacità (skill) del gestore o della strategia di generare extra-rendimento indipendente dai fattori di stile.\n\n<b>Come si calcola:</b> Intercetta alfa della regressione lineare multivariata a tre fattori di Fama-French."
    )
with ff_c2:
    metric_card(
        "Market Beta (FF)",
        f"{mk.get('ff_beta_mkt', 1.0):.2f}",
        help_text="<b>Cosa significa:</b> La sensibilità del portafoglio rispetto all'indice di mercato generale all'interno della regressione a 3 fattori.\n\n<b>A cosa serve:</b> Consente di misurare l'esposizione pura al mercato azionario, pulita dalle distorsioni causate dal tilt di dimensione o di stile.\n\n<b>Come si calcola:</b> Coefficiente angolare del fattore di mercato (R_mkt - R_f) nella regressione Fama-French."
    )
with ff_c3:
    metric_card(
        "SMB Tilt (Size)",
        f"{mk.get('smb_tilt', 0.0):+.2f}",
        positive=(mk.get('smb_tilt', 0.0) >= 0),
        help_text="<b>Cosa significa:</b> Fattore Small Minus Big. Misura l'inclinazione del portafoglio verso aziende a piccola capitalizzazione (Small Cap).\n\n<b>A cosa serve:</b> Un valore positivo (> 0) indica un portafoglio orientato sulle Small Cap per catturare il premio di dimensione; un valore negativo (< 0) indica concentrazione su colossi Large Cap.\n\n<b>Come si calcola:</b> Coefficiente del fattore SMB nella regressione a 3 fattori."
    )
with ff_c4:
    metric_card(
        "HML Tilt (Value)",
        f"{mk.get('hml_tilt', 0.0):+.2f}",
        positive=(mk.get('hml_tilt', 0.0) >= 0),
        help_text="<b>Cosa significa:</b> Fattore High Minus Low. Misura l'orientamento verso azioni Value (alti dividendi/basso P/E) rispetto a titoli Growth.\n\n<b>A cosa serve:</b> Un valore positivo (> 0) segnala uno stile Value conservativo; un valore negativo (< 0) mostra una preferenza per aziende Growth ad alta crescita.\n\n<b>Come si calcola:</b> Coefficiente del fattore HML nella regressione a 3 fattori."
    )

st.divider()


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
        index=1, # 95%
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

# Calcoli a runtime su sr_port
import scipy.stats as stats
import numpy as np

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
       Non fa alcuna ipotesi sulla distribuzione dei rendimenti. Ordina i rendimenti storici e seleziona il percentile corrispondente alla probabilità $\alpha$:
       $$VaR_{storico} = -Q(R_p, \alpha)$$
       
    2. **VaR Parametrico (Varianza-Covarianza)**:
       Assume che i rendimenti seguano una distribuzione Normale $N(\mu_p, \sigma_p^2)$. La formula per il calcolo del VaR giornaliero è:
       $$VaR_{param} = -(\mu_p + z_{\alpha} \cdot \sigma_p)$$
       dove $z_{\alpha}$ è il quantile corrispondente all'area della coda sinistra (es. $-1.645$ per il 95% e $-2.33$ per il 99%).
       
    3. **VaR Cornish-Fisher**:
       Apporta una correzione al VaR Parametrico per tenere conto dell'asimmetria (**Skewness**, $s$) e della curtosi (**Kurtosis**, $k$) dei rendimenti reali del portafoglio (evitando l'assunzione semplificata di normalità). Modifica lo z-score standard $z$ in $z_{cf}$:
       $$z_{cf} = z + \frac{1}{6}(z^2-1)s + \frac{1}{24}(z^3-3z)k - \frac{1}{36}(2z^3-5z)s^2$$
       $$VaR_{cf} = -(\mu_p + z_{cf} \cdot \sigma_p)$$
    
    4. **Expected Shortfall (ES / CVaR)**:
       Mentre il VaR definisce la soglia minima di perdita nel peggiore $\alpha\%$ dei casi, l'Expected Shortfall calcola la perdita media condizionata al superamento di tale soglia. È una misura di rischio coerente e sub-additiva:
       $$ES_{\alpha} = -E[R_p \mid R_p \le -VaR_{\alpha}]$$
       
    5. **Orizzonte Temporale (Regola della Radice del Tempo)**:
       Per estendere il VaR ad un orizzonte di $T$ giorni, si moltiplica il valore giornaliero per la radice quadrata di $T$:
       $$VaR_{T\text{-giorni}} = VaR_{1\text{-giorno}} \cdot \sqrt{T}$$
       *Nota: Questa approssimazione assume che i rendimenti giornalieri siano indipendenti e identicamente distribuiti (i.i.d.).*
    """)

st.divider()

col_r1, col_r2 = st.columns([1, 2])

with col_r1:
    st.markdown("**Metriche di Rischio Principali**")
    glossary_modal("📚 Glossario Approfondito Metriche di Rischio", """
<ul style="margin-top:0; padding-left:20px;">
    <li style="margin-bottom:12px;"><b>Tracking Error (Rischio Attivo):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> È la deviazione standard della <i>differenza</i> tra i tuoi rendimenti e quelli del mercato. Se compri esattamente le stesse cose dell'S&P500, il tuo Tracking Error sarà 0. Più è alto, più il tuo portafoglio sta prendendo strade diverse (e rischi diversi) rispetto al mercato globale.</li>
            <li><b>Calcolo:</b> Deviazione standard annualizzata della serie storica [Rendimento Portafoglio - Rendimento Benchmark].</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>Skewness (Asimmetria):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> Valuta se la distribuzione dei rendimenti pende verso i guadagni o le perdite. Una Skewness <i>negativa</i> è tipica del mercato azionario: significa che ci sono tanti piccoli guadagni frequenti, ma le perdite, quando arrivano, sono rapide e molto violente (crash di mercato).</li>
            <li><b>Calcolo:</b> Momento terzo standardizzato (misura di quanto la curva sia "storta" rispetto alla perfetta campana normale).</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>Kurtosis (Curtosi):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> Misura la probabilità di eventi estremi, i cosiddetti "Cigni Neri". Una distribuzione Normale ha curtosi = 3. Se la curtosi è > 3 (code grasse), le grandi sorprese (crash devastanti o rally improvvisi) accadono molto più spesso di quanto preveda la statistica classica.</li>
            <li><b>Calcolo:</b> Momento quarto standardizzato.</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>VaR Parametrico vs Cornish-Fisher:</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> Il VaR Parametrico si basa sull'illusione che i mercati siano "Normali" (Curva di Gauss). Sottostima il rischio reale. Il VaR di <i>Cornish-Fisher</i> applica una complessa correzione matematica che tiene conto dell'asimmetria (Skewness) e delle code grasse (Kurtosis). Se il Cornish-Fisher è molto più alto del Parametrico, il portafoglio ha un forte rischio di crolli improvvisi.</li>
            <li><b>Calcolo:</b> Espansione di Taylor-Cornish-Fisher applicata alla distribuzione normale.</li>
        </ul>
    </li>
    <li style="margin-bottom:12px;"><b>CVaR (Conditional VaR o Expected Shortfall):</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> Il VaR ti dice: "Nel peggiore 5% dei giorni, perderai <i>almeno</i> X". Il CVaR risponde alla domanda successiva: "Ok, e in quei giorni disastrosi, <i>in media</i>, quanto perderò?". È una misura molto più sicura e prudente del VaR.</li>
            <li><b>Calcolo:</b> Valore Atteso (media aritmetica) di tutti i rendimenti che si collocano al di sotto della soglia critica del VaR.</li>
        </ul>
    </li>
    <li><b>Correlazione & R-Squared:</b>
        <ul style="margin-top:4px;">
            <li><b>Significato/Utilità:</b> La Correlazione va da -1 a +1. L'R-Squared è il suo quadrato (da 0 a 1, o 0-100%). Un R-Squared dell'80% significa che l'80% dei movimenti del tuo portafoglio è puramente dettato da cosa fa il mercato quel giorno. Il restante 20% è il frutto delle tue scelte specifiche sugli asset.</li>
        </ul>
    </li>
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
    st.dataframe(pd.DataFrame(data_mk), use_container_width=True, hide_index=True, height=540)
    

with col_r2:
    st.markdown("**Distribuzione rendimenti giornalieri**")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(
        x=sr_port.values * 100,
        nbinsx=50,
        name="Rendimenti giornalieri",
        marker_color="#ff9900",
        opacity=0.75,
        hovertemplate="<b>Rendimento: %{x:.2f}%</b><br>Frequenza: %{y}<extra></extra>"
    ))
    # Mostriamo la linea del VaR Storico 1g dinamico
    fig_hist.add_vline(
        x=-var_hist_1d * 100, line_color="#ff3333", line_dash="dash",
        annotation_text=f"VaR {int(conf_level*100)}%: -{var_hist_1d*100:.2f}%",
        annotation_position="top right"
    )
    # Mostriamo la linea del CVaR Storico 1g dinamico
    fig_hist.add_vline(
        x=-cvar_hist_1d * 100, line_color="#ff9999", line_dash="dot",
        annotation_text=f"CVaR: -{cvar_hist_1d*100:.2f}%",
        annotation_position="top left"
    )
    # Evidenziamo l'area di perdita estrema (coda della distribuzione)
    fig_hist.add_vrect(
        x0=r.min() * 100, x1=-var_hist_1d * 100,
        fillcolor="rgba(255, 51, 51, 0.15)",
        layer="below", line_width=0
    )
    fig_hist.update_layout(
        xaxis_title="Rendimento %",
        template="plotly_dark", height=360,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=0, r=0, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    apply_plotly_theme(fig_hist)
    st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

col_bot1, col_bot2 = st.columns(2)

with col_bot1:
    st.markdown("**Drawdown storico**")
    cum     = (1 + sr_port).cumprod()
    roll_mx = cum.cummax()
    dd      = (cum - roll_mx) / roll_mx * 100

    fig_dd = go.Figure(go.Scatter(
        x=dd.index, y=dd.values,
        fill="tozeroy", fillcolor="rgba(255,51,51,0.2)",
        line=dict(color="#ff3333", width=1.5),
        name="Drawdown",
        hovertemplate="<b>%{x}</b><br>Drawdown: %{y:.2f}%<extra></extra>"
    ))
    fig_dd.update_layout(
        yaxis_title="Drawdown %",
        height=350,
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
    )
    apply_plotly_theme(fig_dd)
    st.plotly_chart(fig_dd, use_container_width=True)

with col_bot2:
    st.markdown("**Matrice di correlazione tra asset**")
    df_ret_all = results["returns"].dropna(how="all")
    active_t   = pos[pos["qty_net"] > 0]["ticker"].tolist()
    common_t   = [t for t in active_t if t in df_ret_all.columns]

    if len(common_t) > 1:
        corr_matrix = df_ret_all[common_t].corr().round(2)
        fig_corr = px.imshow(
            corr_matrix,
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1,
            text_auto=True,
            labels={
                "x": "Asset 1",
                "y": "Asset 2",
                "color": "Correlazione (ρ)"
            }
        )
        fig_corr.update_traces(
            hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>Correlazione (ρ): %{z:+.2f}<extra></extra>"
        )
        fig_corr.update_layout(
            height=350,
            coloraxis_colorbar=dict(title="Correlazione (ρ)")
        )
        apply_plotly_theme(fig_corr)
        st.plotly_chart(fig_corr, use_container_width=True)

st.divider()

st.markdown("#### Scomposizione del Rischio (Component VaR)")
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
            df_rc, values="Contributo %", names="Asset", hole=0.6
        )
        fig_rc.update_traces(
            textposition='inside', textinfo='percent+label',
            hovertemplate="<b>Asset: %{label}</b><br>Contributo Rischio: %{value:.2f}%<extra></extra>"
        )
        fig_rc.update_layout(height=350)
        apply_plotly_theme(fig_rc)
        st.plotly_chart(fig_rc, use_container_width=True)

    st.markdown("**Risk Heatmap Grid (Mappa di Calore Rischio/PnL)**")
    glossary_modal("ℹ️ Guida alla Risk Heatmap Grid", """
    <p><b>Cos'è la Risk Heatmap Grid?</b><br>
    Una visualizzazione gerarchica a mappa di calore (Treemap) ad alta densità usata nella gestione professionale di portafoglio. La dimensione di ciascun rettangolo rappresenta il <b>controvalore in Euro</b> allocato nel titolo, mentre il colore (dal verde brillante al rosso cremisi) mostra la <b>plusvalenza/perdenza non realizzata (PnL)</b> ed il contributo al VaR di portafoglio.</p>
    """, button_label="💡 Come funziona la Risk Heatmap Grid?")
    fig_hm = render_risk_heatmap(pos, risk_contrib)
    if fig_hm:
        st.plotly_chart(fig_hm, use_container_width=True)



else:
    st.info("Impossibile calcolare la scomposizione del rischio (pochi dati storici o troppi pochi asset validi).")

st.divider()

st.markdown("#### Rischio di Liquidità (Days-to-Liquidate)")
glossary_modal("Cos'è il Rischio di Liquidità?", 
"È la stima dei giorni necessari per liquidare completamente la posizione senza muovere il mercato (ipotizzando di non superare il 15% del Volume Medio Giornaliero scambiato in borsa). Utile per valutare se si è bloccati in asset illiquidi.", 
button_label="💡 Come si legge?")

# Dati liquidità
if "days_to_liquidate" in pos.columns:
    df_liq = pos[pos["qty_net"] > 0][["ticker", "current_value", "days_to_liquidate"]].copy()
    df_liq = df_liq.sort_values(by="days_to_liquidate", ascending=False)
    
    col_l1, col_l2 = st.columns([1, 1])
    with col_l1:
        st.dataframe(df_liq, use_container_width=True, hide_index=True)
    with col_l2:
        if df_liq["days_to_liquidate"].max() > 5:
            st.warning(f"Attenzione: alcuni asset richiedono più di 5 giorni per essere liquidati in sicurezza. L'asset più illiquido è **{df_liq.iloc[0]['ticker']}** con **{df_liq.iloc[0]['days_to_liquidate']:.1f} giorni** stimati.")
        else:
            st.success("Il portafoglio è altamente liquido. Tutte le posizioni possono essere smobilizzate in tempi rapidi senza impatto significativo sui prezzi.")
else:
    st.info("Dati sui volumi non sufficienti per calcolare i Days-to-Liquidate.")

st.divider()

st.markdown("#### 🔬 Validazione e Backtesting dei Modelli VaR (Kupiec Test)")
st.caption(f"Verifica l'efficacia statistica dei tre modelli di VaR (Storico, Parametrico e Cornish-Fisher) ad un orizzonte di 1 giorno, analizzando le eccezioni (breaches) registrate negli ultimi 252 giorni di trading rispetto al livello di confidenza selezionato del {int(conf_level*100)}% (target di violazioni: {alpha * 100:.1f}%).")

glossary_modal("Cos'è il Backtesting del VaR?", """
<p>Il <b>Backtesting del VaR</b> (noto anche come Kupiec Proportion of Failures Test o test di copertura incondizionata) è la procedura regolamentare utilizzata per verificare se le stime di rischio prodotte dai modelli matematici sono accurate.</p>
<ul style="padding-left: 20px;">
    <li style="margin-bottom:8px;"><b>Eccezione (Breach):</b> Si verifica ogni volta che la perdita reale di portafoglio in una giornata supera la perdita massima stimata dal VaR a 1 giorno per quella data.</li>
    <li style="margin-bottom:8px;"><b>Target Statistico:</b> Con un VaR al 95%, ci si aspetta che solo il 5% delle giornate storiche superi la soglia (1 giorno su 20). Con un VaR al 99%, ci si aspetta l'1% (1 giorno su 100).</li>
    <li style="margin-bottom:8px;"><b>Il Semaforo di Basilea:</b>
        <ul style="margin-top:4px;">
            <li><b>🟢 Verde:</b> Il modello stima il rischio in modo ottimale o conservativo.</li>
            <li><b>🟡 Giallo:</b> Sotto-stima lieve. Il modello va monitorato (possibili 'code grasse' non considerate).</li>
            <li><b>🔴 Rosso:</b> Sotto-stima grave. Il modello è statisticamente fallito e deve essere scartato.</li>
        </ul>
    </li>
</ul>
""", button_label="💡 Come funziona il Backtesting?")

recent_r = r.tail(252)
n_days = len(recent_r)
expected_exc = n_days * alpha

# Calcolo eccezioni a runtime per ciascun modello
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

zone_hist = get_basel_zone(exc_hist, expected_exc)
zone_param = get_basel_zone(exc_param, expected_exc)
zone_cf = get_basel_zone(exc_cf, expected_exc)

df_backtest = pd.DataFrame({
    "Modello VaR": ["Storico", "Parametrico (Gaussiano)", "Cornish-Fisher"],
    "Soglia VaR (1g)": [f"{var_hist_1d * 100:.2f}%", f"{var_param_1d * 100:.2f}%", f"{var_cf_1d * 100:.2f}%"],
    "Eccezioni Reali (252g)": [exc_hist, exc_param, exc_cf],
    "Tasso di Violazione": [f"{ratio_hist:.2f}%", f"{ratio_param:.2f}%", f"{ratio_cf:.2f}%"],
    "Target Violazioni": [f"{alpha * 100:.1f}%", f"{alpha * 100:.1f}%", f"{alpha * 100:.1f}%"],
    "Stato (Basel Accord)": [zone_hist, zone_param, zone_cf]
})

col_bt_tbl, col_bt_desc = st.columns([2, 1])

with col_bt_tbl:
    st.dataframe(df_backtest, use_container_width=True, hide_index=True)

with col_bt_desc:
    st.info(f"""
    **Come leggere i risultati:**
    *   **Eccezioni Attese**: In {n_days} giorni di trading, con un livello di confidenza del {int(conf_level*100)}%, ci aspettiamo circa **{expected_exc:.1f} violazioni**.
    *   **🟢 Zona Verde**: Il numero di crolli reali è inferiore o pari all'attesa statistica. Il modello è solido.
    *   **🟡 Zona Gialla**: Il modello sottostima leggermente il rischio estremo, ma rientra nei limiti accettabili.
    *   **🔴 Zona Rossa**: Troppe violazioni. Il modello ignora le code spesse e non è affidabile per proteggere il capitale.
    """)
