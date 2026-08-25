import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import importlib
import core.ui_utils
import core.risk_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, fmt_pct, glossary_modal, apply_plotly_theme, render_command_bar, render_segmented_tabs, ensure_risk_bundle_loaded, render_sandbox_banner

st.set_page_config(page_title="Stress Testing | ARGUS", page_icon="🌪️", layout="wide")
inject_custom_css()

from core.sidebar import render_sidebar
render_sidebar()
render_command_bar()

results, has_real = ensure_risk_bundle_loaded()
stress = results.get("stress_tests")
pos = results.get("positions", pd.DataFrame())
portfolio_value = pos["current_value"].sum() if not pos.empty and "current_value" in pos.columns else 0

if not stress and not pos.empty:
    from core.risk_engine import _calc_stress_tests
    stress = _calc_stress_tests(
        results.get("returns", pd.DataFrame()),
        pos,
        results.get("benchmark_return", pd.Series(dtype=float))
    )
    if stress:
        results["stress_tests"] = stress

render_sandbox_banner(page_key="p6")

col_head1, col_head2 = st.columns([3.4, 1.2])
with col_head1:
    st.title("🌪️ Stress Testing & Resilience Analysis")
    if "run_id" in st.session_state:
        st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Simulazione d'impatto e matrice MSCI Barra nei 5 principali scenari storici di crisi e stress macroeconomico.")
    elif results.get("is_sandbox"):
        st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")

with col_head2:
    st.markdown('<div style="display: flex; justify-content: flex-end; margin-top: 24px;">', unsafe_allow_html=True)
    glossary_modal("Cos'è lo Stress Testing Istituzionale?", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è lo Stress Testing</div>
  <div>La metodologia quantitativa fondamentale prescritta dagli standard di Basilea III per testare la vulnerabilità del portafoglio di fronte a crolli storici di mercato o combinazioni ipotetiche di shock macroeconomici avversi.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 I 5 Scenari Storici Benchmark</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Bolla Dot-Com (2000-2002):</b> Crollo tech (&minus;49.1% S&P 500)<br>
    • <b>Crisi Mutui Subprime Lehman (2007-2009):</b> Crollo sistemico (&minus;56.8%)<br>
    • <b>Crisi Debito Sovrano US/UE (2011):</b> Taglio rating USA & Spread BTP (&minus;19.4%)<br>
    • <b>Flash Crash Pandemia COVID-19 (2020):</b> Shock di liquidità globale (&minus;33.9%)<br>
    • <b>Shock Inflazione & Rialzo Tassi (2022):</b> Bear market combinato equity/bond (&minus;25.4%)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Quantificare la massima perdita monetaria in Euro (€) e percentuale (%) in caso di shock estremi per predisporre buffer di liquidità o coperture asimmetriche.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS applica la serie storica reale per i titoli con track record durante le crisi ed esegue stime parametriche basate su Beta e Duration per gli asset più recenti.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Se l'impatto stimato in uno scenario supera il 35%, il portafoglio presenta un'elevata convessità negativa e vulnerabilità a quel fattore di rischio.</div>
</div>

</div>
""", button_label="💡 Come funziona lo Stress Testing?")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)

if not stress:
    st.info("Risultati dello stress test non disponibili (dati insufficienti).")
    st.stop()

# ── SELETTORE MODULI DI STRESS TESTING STILE BLOOMBERG TERMINAL ─────────
STRESS_MODELS_CATALOG = {
    "⚡ Matrice Comparativa MSCI Barra": {
        "title": "Matrice Comparativa di Stress Test Simultanea (MSCI Barra Multi-Asset)",
        "badge": "5 Crisi Storiche • P&L Totale",
        "badge_color": "#ff9900",
        "category": "Visione Sinottica Macro",
        "desc": "Confronto orizzontale istantaneo della resilienza patrimoniale nei 5 maggiori crash sistemici moderni: COVID Crash 2020, Crisi Subprime 2008, Dot-Com Bubble 2000, Taper Tantrum 2013 e Inflazione 2022."
    },
    "🏛️ Analisi Scenari Storici Dettagliata": {
        "title": "Audit di Profondità per Singolo Scenario di Crisi Storica & Decomposizione Asset",
        "badge": "Decomposizione per Titolo • Drawdown",
        "badge_color": "#f85149",
        "category": "Dissezione per Posizione",
        "desc": "Scomposizione analitica per singolo titolo della perdita stimata, identificazione dei driver principali di drawdown e valutazione del comportamento asimmetrico delle classi di attivo."
    },
    "🛠️ Simulatore What-if Custom": {
        "title": "Simulatore di Shock Macro Personalizzato (Tassi, Volatilità, Indici & FX)",
        "badge": "Stress Ipotetico • Shock Simultanei",
        "badge_color": "#38bdf8",
        "category": "Simulazione What-If",
        "desc": "Configuratore interattivo di shock ipotetici: imposta variazioni arbitrarie su indici azionari, curva dei tassi d'interesse, spread creditizi e volatilità con calcolo istantaneo del P&L marginale."
    }
}

# Risoluzione dello stato attivo con priorità alla sidebar o global jump
target_tab = None
if "target_subtab_stress_active_tab" in st.session_state:
    target_tab = st.session_state.pop("target_subtab_stress_active_tab")
elif "global_target_subtab" in st.session_state:
    target_tab = st.session_state.pop("global_target_subtab")
elif "target_stress_module" in st.session_state:
    target_tab = st.session_state.pop("target_stress_module")

stress_keys = list(STRESS_MODELS_CATALOG.keys())

if target_tab and target_tab in stress_keys:
    st.session_state["stress_active_tab"] = target_tab
    st.session_state["stress_active_tab_selectbox"] = target_tab
elif "stress_active_tab" not in st.session_state or st.session_state["stress_active_tab"] not in stress_keys:
    st.session_state["stress_active_tab"] = stress_keys[0]

curr_idx = stress_keys.index(st.session_state["stress_active_tab"])

# Spaziatura e Respiro Layout
st.markdown("<div style='margin-top: 14px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# Barra Selettore Compatta Bloomberg Style
c_sel_s, c_prev_s, c_next_s = st.columns([3.8, 0.6, 0.6], vertical_alignment="center")

with c_prev_s:
    if st.button("◀ Prec.", key="btn_stress_prev", use_container_width=True, help="Modulo precedente"):
        new_i = (curr_idx - 1) % len(stress_keys)
        st.session_state["target_stress_module"] = stress_keys[new_i]
        st.rerun()

with c_next_s:
    if st.button("Succ. ▶", key="btn_stress_next", use_container_width=True, help="Modulo successivo"):
        new_i = (curr_idx + 1) % len(stress_keys)
        st.session_state["target_stress_module"] = stress_keys[new_i]
        st.rerun()

with c_sel_s:
    selected_stress_key = st.selectbox(
        "Seleziona Modulo di Stress Testing:",
        options=stress_keys,
        index=curr_idx,
        format_func=lambda k: f"{k}  —  {STRESS_MODELS_CATALOG[k]['category']} [{STRESS_MODELS_CATALOG[k]['badge']}]",
        key="stress_active_tab_selectbox",
        label_visibility="collapsed"
    )
    st.session_state["stress_active_tab"] = selected_stress_key

active_stress_tab = st.session_state["stress_active_tab"]
active_stress_info = STRESS_MODELS_CATALOG[active_stress_tab]

# Bloomberg Terminal Header Banner per il Modulo Attivo
st.markdown(f"""
<div style="background: linear-gradient(90deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.85) 100%); border: 1px solid rgba(255,255,255,0.08); border-left: 4px solid {active_stress_info['badge_color']}; border-radius: 8px; padding: 12px 18px; margin-top: 10px; margin-bottom: 22px;">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
    <div style="font-size: 15px; font-weight: 700; color: #f0f6fc;">
      {active_stress_info['title']}
    </div>
    <div style="display: flex; gap: 8px; align-items: center;">
      <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 12px; background: rgba(255,255,255,0.06); color: #8b949e; border: 1px solid rgba(255,255,255,0.08);">
        {active_stress_info['category']}
      </span>
      <span style="font-size: 11.5px; font-weight: 600; padding: 2px 10px; border-radius: 12px; background: {active_stress_info['badge_color']}22; color: {active_stress_info['badge_color']}; border: 1px solid {active_stress_info['badge_color']}55;">
        {active_stress_info['badge']}
      </span>
    </div>
  </div>
  <div style="font-size: 13px; color: #8b949e; line-height: 1.45;">
    {active_stress_info['desc']}
  </div>
</div>
""", unsafe_allow_html=True)

# ── TAB 1: MATRICE COMPARATIVA MSCI BARRA ─────────────────────
if active_stress_tab == "⚡ Matrice Comparativa MSCI Barra":
    col_head_mb1, col_head_mb2 = st.columns([3.2, 1.1])
    with col_head_mb1:
        st.markdown("#### ⚡ Matrice Comparativa di Stress Test Simultanea (MSCI Barra Style)")
        st.caption("Confronta l'impatto stimato in € e % del tuo portafoglio in tutti gli scenari di crisi contemporaneamente")
    with col_head_mb2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida alla Matrice di Stress Test (MSCI Barra Style)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è la Matrice Comparativa MSCI Barra</div>
  <div>Una visione sinottica orizzontale che affianca simultaneamente i 5 grandi eventi di crisi dei mercati finanziari moderni, permettendo di valutare a colpo d'occhio la resilienza comparata del portafoglio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Metodologia di Calcolo</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Drawdown Benchmark:</b> Shock percentuale registrato dall'indice S&P 500 / MSCI World<br>
    • <b>Drawdown Portafoglio:</b> &sum; (w<sub>i</sub> &times; Rendimento Storico<sub>i, crisi</sub>)<br>
    • <b>Perdita Monetaria:</b> Controvalore Attuale &times; Impatto Portafoglio %
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Identificare quale tipologia di shock macro (crollo tecnologico, crisi bancaria/creditizia, shock tassi o pandemia) infligge il danno maggiore al portafoglio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il motore carica i rendimenti storici effettivi dal database e genera la matrice comparativa con gradiente cromatico ad alto contrasto.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Una perdita di portafoglio inferiore allo shock di mercato indica una solida componente difensiva o di decorrelazione efficace.</div>
</div>

</div>
""", button_label="💡 Come funziona la Matrice MSCI Barra?")

    df_matrix_rows = []
    for sc_name, sc_data in stress.items():
        mkt_shock = float(sc_data.get("benchmark_shock_pct", 0.0))
        port_shock = float(sc_data.get("portfolio_shock_pct", 0.0))
        loss_eur = float(sc_data.get("portfolio_loss_eur", 0.0))
        diff_pct = port_shock - mkt_shock
        df_matrix_rows.append({
            "Scenario": sc_name,
            "Shock Mercato %": mkt_shock,
            "Impatto Portafoglio %": port_shock,
            "Differenziale (Alpha) %": diff_pct,
            "Perdita Stimata (€)": loss_eur,
        })

    df_matrix = pd.DataFrame(df_matrix_rows)

    if not df_matrix.empty:
        worst_sc = df_matrix.loc[df_matrix["Impatto Portafoglio %"].idxmin()]
        best_sc = df_matrix.loc[df_matrix["Impatto Portafoglio %"].idxmax()]
        avg_impact = df_matrix["Impatto Portafoglio %"].mean()
        avg_alpha = df_matrix["Differenziale (Alpha) %"].mean()

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card(
                "Scenario Più Severo",
                f"{worst_sc['Impatto Portafoglio %']:.2f}%",
                f"Perdita: € {abs(worst_sc['Perdita Stimata (€)']):,.0f}",
                positive=False,
                help_text=f"Scenario con la massima contrazione: {worst_sc['Scenario']}"
            )
        with k2:
            metric_card(
                "Scenario Più Resiliente",
                f"{best_sc['Impatto Portafoglio %']:.2f}%",
                f"Perdita: € {abs(best_sc['Perdita Stimata (€)']):,.0f}",
                positive=False,
                help_text=f"Scenario con la minore contrazione: {best_sc['Scenario']}"
            )
        with k3:
            metric_card(
                "Drawdown Medio Scenari",
                f"{avg_impact:.2f}%",
                "Media sui 5 Eventi Storici",
                positive=avg_impact >= 0,
                help_text="Impatto medio stimato calcolato su tutti i 5 crash storici considerati"
            )
        with k4:
            metric_card(
                "Alpha Difensivo Medio",
                f"{avg_alpha:+.2f}%",
                "vs Benchmark Mercato",
                positive=avg_alpha >= 0,
                help_text="Differenziale medio tra la perdita di portafoglio e quella del mercato (valore positivo = sovraperformance difensiva)"
            )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    st.markdown("##### 📊 Confronto Shock: Portafoglio vs Mercato (Benchmark)")
    fig_mat = go.Figure()
    
    fig_mat.add_trace(go.Bar(
        y=df_matrix["Scenario"],
        x=df_matrix["Impatto Portafoglio %"],
        name="Portafoglio",
        orientation="h",
        marker=dict(color="#ff4d4d", line=dict(color="#ff6b6b", width=1)),
        text=[f"{v:.1f}%" for v in df_matrix["Impatto Portafoglio %"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{y}</b><br>⚡ Impatto Portafoglio: <b>%{x:.2f}%</b><extra></extra>"
    ))
    fig_mat.add_trace(go.Bar(
        y=df_matrix["Scenario"],
        x=df_matrix["Shock Mercato %"],
        name="Mercato (Benchmark)",
        orientation="h",
        marker=dict(color="rgba(88, 166, 255, 0.45)", line=dict(color="#58a6ff", width=1)),
        text=[f"{v:.1f}%" for v in df_matrix["Shock Mercato %"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{y}</b><br>🌐 Shock Mercato: <b>%{x:.2f}%</b><extra></extra>"
    ))
    
    fig_mat.update_layout(
        barmode="group",
        xaxis=dict(
            title="Variazione (%)",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.2)",
            gridcolor="rgba(255,255,255,0.06)"
        ),
        yaxis=dict(
            autorange="reversed",
            gridcolor="rgba(255,255,255,0.06)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=320,
        margin=dict(l=235, r=30, t=20, b=10)
    )
    apply_plotly_theme(fig_mat)
    st.plotly_chart(fig_mat, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    col_syn1, col_syn2 = st.columns([3.2, 1.0])
    with col_syn1:
        st.markdown("##### 📋 Matrice Sinottica Dettagliata degli Scenari")
    with col_syn2:
        csv_syn = df_matrix.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica CSV", data=csv_syn, file_name="matrice_scenari_stress_test.csv", mime="text/csv", use_container_width=True, key="btn_download_stress_matrix")

    st.dataframe(
        df_matrix[["Scenario", "Shock Mercato %", "Impatto Portafoglio %", "Differenziale (Alpha) %", "Perdita Stimata (€)"]].style.format({
            "Shock Mercato %": "{:+.2f}%",
            "Impatto Portafoglio %": "{:+.2f}%",
            "Differenziale (Alpha) %": "{:+.2f}%",
            "Perdita Stimata (€)": "€ {:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# ── TAB 2: ANALISI SCENARI STORICI DETTAGLIATA ────────────────
elif active_stress_tab == "🏛️ Analisi Scenari Storici Dettagliata":
    st.markdown("#### Analisi dei Singoli Scenari Storici di Crisi")
    scenario_names = list(stress.keys())
    active_scenario = render_segmented_tabs(scenario_names, key="stress_scenario_subtab")

    if active_scenario in stress:
        data = stress[active_scenario]
        st.markdown(f"### Scenario: {active_scenario}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card("Shock Mercato (S&P500)", fmt_pct(data['benchmark_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> Crollo percentuale effettivo dell'S&P500 durante questo specifico scenario di crisi.")
        with col2:
            metric_card("Impatto Stimato Portafoglio", fmt_pct(data['portfolio_shock_pct']), positive=False, help_text="<b>Cosa significa:</b> Flessione percentuale che il tuo portafoglio attuale subirebbe se si ripetesse questo scenario.")
        with col3:
            metric_card("Perdita Stimata (Euro)", fmt_eur(data['portfolio_loss_eur']), positive=False, help_text="<b>Cosa significa:</b> La traduzione in Euro crudi della potenziale perdita di capitale.")
            
        st.markdown("#### Impatto sul Capitale (Waterfall)")
        loss = data['portfolio_loss_eur']
        final_value = portfolio_value + loss
        max_cap = max(portfolio_value, final_value)
        
        fig_wf = go.Figure(go.Waterfall(
            name="Stress Test", orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Valore Pre-Crisi", "Impatto Crisi", "Valore Post-Crisi"],
            textposition="outside",
            text=[f"€ {portfolio_value:,.2f}", f"€ {loss:,.2f}", f"€ {final_value:,.2f}"],
            y=[portfolio_value, loss, final_value],
            connector={"line": {"color": "rgba(255,255,255,0.25)", "dash": "dot", "width": 1.5}},
            decreasing={"marker": {"color": "#f85149", "line": {"color": "#0d1117", "width": 1.5}}},
            totals={"marker": {"color": "#58a6ff", "line": {"color": "#0d1117", "width": 1.5}}},
            increasing={"marker": {"color": "#3fb950", "line": {"color": "#0d1117", "width": 1.5}}},
            width=0.42,
            cliponaxis=False
        ))
        fig_wf.update_layout(
            template="plotly_dark", height=350,
            margin=dict(l=30, r=30, t=35, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(
                title="Valore (€)",
                range=[0, max_cap * 1.18],
                gridcolor="rgba(255,255,255,0.06)",
                tickprefix="€ "
            ),
            xaxis=dict(showgrid=False),
            hovermode="x unified"
        )
        apply_plotly_theme(fig_wf)
        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        st.divider()
        st.markdown("#### Impatto per singolo Asset")
        
        details = data["details"]
        if details:
            df_det = pd.DataFrame.from_dict(details, orient="index").reset_index()
            rename_map = {"index": "Ticker", "beta": "Beta", "shock_pct": "Shock %", "loss_eur": "Perdita Stimata (€)", "is_historical": "Dato Storico Reale"}
            df_det.rename(columns={k: v for k, v in rename_map.items() if k in df_det.columns}, inplace=True)
            df_det = df_det.sort_values(by="Perdita Stimata (€)", ascending=True)
            
            col_t, col_c = st.columns([1.15, 1.15])
            with col_t:
                col_hd1, col_hd2 = st.columns([2.0, 1.1])
                with col_hd1:
                    st.markdown("##### 📋 Dettaglio per Singola Posizione")
                with col_hd2:
                    csv_det = df_det.to_csv(index=False).encode('utf-8')
                    sc_slug = active_scenario.lower().replace(" ", "_").replace(":", "").replace("/", "_")
                    st.download_button("📥 Scarica CSV", data=csv_det, file_name=f"stress_test_posizioni_{sc_slug}.csv", mime="text/csv", use_container_width=True, key="btn_download_stress_positions")
                
                df_disp = df_det.copy()
                df_disp["Shock %"] = df_disp["Shock %"].apply(lambda x: f"{x:.2f}%")
                df_disp["Perdita Stimata (€)"] = df_disp["Perdita Stimata (€)"].apply(lambda x: f"€ {x:,.2f}")
                if "Beta" in df_disp.columns:
                    df_disp["Beta"] = df_disp["Beta"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "1.00")
                if "Dato Storico Reale" in df_disp.columns:
                    df_disp["Dato Storico Reale"] = df_disp["Dato Storico Reale"].apply(lambda x: "✅ Reale" if x else "⚡ Beta")
                
                tbl_h = max(360, min(560, len(df_disp) * 35 + 38))
                st.dataframe(df_disp, use_container_width=True, hide_index=True, height=tbl_h)
                
            with col_c:
                st.markdown("##### 🔻 Distribuzione della Perdita per Singolo Asset")
                max_loss_abs = abs(float(df_det["Perdita Stimata (€)"].min())) if not df_det.empty else 1000.0
                chart_h = max(360, min(560, len(df_det) * 28 + 40))
                
                fig_asset_loss = go.Figure()
                fig_asset_loss.add_trace(go.Bar(
                    y=df_det["Ticker"],
                    x=df_det["Perdita Stimata (€)"],
                    orientation='h',
                    marker=dict(
                        color="#f85149",
                        line=dict(color="#0d1117", width=1.2)
                    ),
                    text=df_det["Perdita Stimata (€)"].apply(lambda v: f"-€ {abs(v):,.0f}"),
                    textposition="outside",
                    textfont=dict(size=10, color="#ffffff"),
                    cliponaxis=False,
                    hovertemplate="<b>Ticker: %{y}</b><br>Perdita Stimata: <b>€ %{x:,.2f}</b><extra></extra>"
                ))
                
                fig_asset_loss.update_layout(
                    template="plotly_dark", height=chart_h,
                    margin=dict(l=10, r=55, t=15, b=25),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        title="Perdita Stimata (€)",
                        range=[-max_loss_abs * 1.22, 0],
                        gridcolor="rgba(255,255,255,0.06)",
                        tickprefix="€ "
                    ),
                    yaxis=dict(title=None, showgrid=False)
                )
                apply_plotly_theme(fig_asset_loss)
                st.plotly_chart(fig_asset_loss, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

# ── TAB 3: SIMULATORE WHAT-IF & MACRO SCENARIO BUILDER ─────────
elif active_stress_tab == "🛠️ Simulatore What-if Custom":
    col_head_sb1, col_head_sb2 = st.columns([3.2, 1.1])
    with col_head_sb1:
        st.markdown("#### 🛠️ Macro Scenario Builder Multi-Fattoriale & Simulatore What-If")
        st.caption("Manovra i parametri macroeconomici (Tassi d'interesse, Tasso EUR/USD, Prezzo Petrolio, Shock Azionario) per simulare scenari complessi di mercato sul tuo portafoglio.")
    with col_head_sb2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("⚡ Guida al Macro Scenario Builder Multi-Fattoriale", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Macro Scenario Builder Multi-Fattoriale</div>
  <div>Un potente motore di stress testing causale che permette di costruire scenari macroeconomici combinati su misura, stimando l'impatto contemporaneo di shock azionari, monetari, valutari ed energetici.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 I 4 Canali di Trasmissione Macroeconomica</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Shock Tassi (&Delta;r):</b> &minus;Duration &times; &Delta;r sui bond e compressione dei multipli P/E azionari<br>
    • <b>Shock Valutario (&Delta;FX EUR/USD):</b> Rivalutazione/svalutazione delle posizioni denominate in dollari<br>
    • <b>Shock Materie Prime (&Delta;Commodity):</b> Impatto inflattivo e pressione sui margini aziendali<br>
    • <b>Shock Azionario (&Delta;Equity):</b> &beta; &times; Shock Mercato per ciascun titolo azionario
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Testare scenari di "Stagflazione", "Taglio Tassi & Boom Tech" o "Crisi Geopolitica Petrolifera" calibrando liberamente l'intensità di ogni singola variabile macroeconomica.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>La funzione <code>compute_custom_macro_stress</code> aggrega i flussi di sensitività titolo per titolo producendo il conto economico simulato del portafoglio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Usa i 4 slider interattivi a sinistra: i KPI a destra e la tabella dettagliata per asset si aggiornano istantaneamente mostrando la scomposizione della perdita/guadagno.</div>
</div>

</div>
""", button_label="💡 Come funziona il Macro Scenario Builder?")

    col_sim1, col_sim2 = st.columns([1, 2.2])
    with col_sim1:
        st.markdown("##### 🎛️ Manovra Parametri Macro")
        benchmark_shock = st.slider("Shock Mercato Azionario (%)", -50, 30, -15, 1, help="Shock generale indici azionari")
        rate_shock_bps = st.slider("Variazione Tassi BCE/FED (bps)", -200, 300, 100, 25, help="+100 bps = rialzo tassi di 1.00%")
        fx_shock_pct = st.slider("Shock Cambio EUR/USD (%)", -20, 20, -5, 1, help="-5% = svalutazione EUR del 5%")
        oil_shock_pct = st.slider("Shock Petrolio / Materie Prime (%)", -40, 60, 20, 5, help="+20% = impennata prezzi energia")

    from core.risk_engine import compute_custom_macro_stress
    macro_res = compute_custom_macro_stress(
        pos, 
        rate_shock_bps=rate_shock_bps, 
        fx_shock_pct=fx_shock_pct, 
        oil_shock_pct=oil_shock_pct, 
        equity_shock_pct=benchmark_shock
    )

    with col_sim2:
        st.markdown("##### 📊 Impatto Stimato sul Portafoglio")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            metric_card("Valore Attuale Portafoglio", fmt_eur(macro_res.get("portfolio_val_before", 0.0)))
        with c_m2:
            metric_card("Impatto Macro Stimato (%)", f"{macro_res.get('portfolio_impact_pct', 0.0):+.2f}%", positive=macro_res.get("portfolio_impact_pct", 0.0) >= 0)
        with c_m3:
            metric_card("Variazione Stimata (€)", fmt_eur(macro_res.get("portfolio_loss_eur", 0.0)), positive=macro_res.get("portfolio_loss_eur", 0.0) >= 0)

        if not macro_res["details_df"].empty:
            col_mhd1, col_mhd2 = st.columns([2.8, 1.2])
            with col_mhd1:
                st.markdown("##### 📋 Dettaglio Impatto per Singolo Asset")
            with col_mhd2:
                csv_mac = macro_res["details_df"].to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_mac, file_name="simulazione_macro_whatif_posizioni.csv", mime="text/csv", use_container_width=True, key="btn_download_macro_whatif")
            
            df_macro_disp = macro_res["details_df"].rename(columns={
                "ticker": "Ticker",
                "current_value": "Valore Attuale (€)",
                "simulated_impact_pct": "Impatto Stimato (%)",
                "simulated_loss_eur": "Variazione Stimata (€)"
            })
            st.dataframe(
                df_macro_disp.style.format({
                    "Valore Attuale (€)": "€ {:,.2f}",
                    "Impatto Stimato (%)": "{:+.2f}%",
                    "Variazione Stimata (€)": "€ {:,.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.divider()
    st.markdown("#### 🌋 Visualizzatore 3D della Superficie di Rischio (Rates vs Volatility)")
    st.caption("Esplora la superficie 3D interattiva che mappa la perdita di capitale al variare simultaneo dello Shock sui Tassi di Interesse (bps) e dello Shock sulla Volatilità / VIX (%).")

    from core.risk_engine import compute_3d_stress_surface
    surface_data = compute_3d_stress_surface(pos)

    fig_3d = go.Figure(data=[go.Surface(
        x=surface_data["rate_grid"],
        y=surface_data["vol_grid"],
        z=surface_data["z_pnl_eur"],
        colorscale="RdYlGn",
        colorbar=dict(title="PnL (€)", tickformat="€ ,.0f"),
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor="#ffffff", project=dict(z=True))
        ),
        lighting=dict(ambient=0.75, diffuse=0.85, roughness=0.45, specular=0.25),
        hovertemplate="<b>Tassi:</b> %{x:+d} bps<br><b>Volatilità:</b> %{y:+d}%<br><b>PnL:</b> € %{z:,.2f}<extra></extra>"
    )])

    fig_3d.update_layout(
        title="Superficie 3D di Stress Test: Impatto Capitale (€)",
        scene=dict(
            xaxis=dict(title="Shock Tassi (bps)", gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.3)"),
            yaxis=dict(title="Shock Volatilità (%)", gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.3)"),
            zaxis=dict(title="Impatto PnL (€)", gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.3)"),
            camera=dict(eye=dict(x=1.7, y=-1.6, z=1.05)),
            aspectratio=dict(x=1, y=1, z=0.65)
        ),
        template="plotly_dark",
        height=540,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    apply_plotly_theme(fig_3d)
    st.plotly_chart(fig_3d, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        metric_card("Punto Peggiore sulla Superficie", fmt_eur(surface_data["worst_pnl_eur"]), positive=False, help_text="La massima perdita stimata sulla griglia di shock tassi x volatilità")
    with col_s2:
        metric_card("Punto Migliore sulla Superficie", fmt_eur(surface_data["best_pnl_eur"]), positive=True, help_text="Il massimo guadagno stimato sulla griglia di shock tassi x volatilità")
