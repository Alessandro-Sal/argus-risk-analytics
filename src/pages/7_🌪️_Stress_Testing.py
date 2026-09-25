import streamlit as st

st.set_page_config(page_title="Stress Testing | ARGUS", page_icon="🌪️", layout="wide")

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import core.risk_engine
import core.ui_utils
from core.ui_export_utils import render_table_with_export
from core.ui_utils import (
    apply_plotly_theme,
    ensure_portfolio_loaded,
    fmt_eur,
    fmt_pct,
    glossary_modal,
    inject_custom_css,
    metric_card,
    render_command_bar,
    render_sandbox_banner,
    render_segmented_tabs,
)

inject_custom_css()

from core.sidebar import render_sidebar

render_sidebar()
render_command_bar()

results, has_real = ensure_portfolio_loaded(module_type="risk")
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

render_sandbox_banner(page_key="p7")

col_head1, col_head2 = st.columns([3.4, 1.2], vertical_alignment="center")
with col_head1:
    st.title("🌪️ Stress Testing & Resilience Analysis")
    if "run_id" in st.session_state:
        st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Simulazione d'impatto e matrice MSCI Barra nei 5 principali scenari storici di crisi e stress macroeconomico.")
    elif results.get("is_sandbox"):
        st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")

with col_head2:
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
    },
    "🌐 Total Balance Sheet & Human Capital Stress": {
        "title": "Holistic Total Balance Sheet VaR & Stress Test Capitale Umano (MSCI Barra / BlackRock Aladdin)",
        "badge": "TBS-VaR • Human Capital • Mutui",
        "badge_color": "#a855f7",
        "category": "Integrazione Olistica Wealth-Risk",
        "desc": "Integrazione attuariale del Capitale Umano (quasi-equity/quasi-bond) con gli asset liquidi e illiquidi (Real Estate, Mutui a tasso variabile). Calcolo del Total Balance Sheet VaR (TBS-VaR 95%), Emergency Runway e sovraesposizione settoriale."
    },
    "📈 Portfolio Fixed Income & ALM Treasury": {
        "title": "Analisi Rischio Tassi & ALM Portfolio Aggregator (Duration, DV01 & Curve Twist)",
        "badge": "Duration • DV01 • Key Rates",
        "badge_color": "#10b981",
        "category": "Asset-Liability Management",
        "desc": "Aggregazione istituzionale del comparto obbligazionario ed ETF a reddito fisso: Macaulay/Modified Duration ponderata, sensibilità monetaria DV01 per basis point, Key Rate Durations (2Y, 5Y, 10Y, 30Y) e rotazione della curva (Bull/Bear Steepener e Flattener)."
    },
    "💧 Rischio Liquidità & Orizzonte DTL (Basel III / UCITS)": {
        "title": "Motore Istituzionale di Liquidità & Orizzonte di Smobilizzo (Days to Liquidate & Amihud)",
        "badge": "DTL • Amihud • Endogenous L-VaR",
        "badge_color": "#06b6d4",
        "category": "Liquidity & Execution Risk",
        "desc": "Audit dei volumi medi scambiati (ADV), giorni necessari alla liquidazione (DTL al 10% e 20% ADV), indice di illiquidità di Amihud, ripartizione in 4 Tier di liquidità e calcolo del Liquidity-Adjusted VaR (L-VaR) endogeno."
    },
    "⚡ Reverse Stress Testing (EBA / BCE)": {
        "title": "Reverse Stress Testing Istituzionale (Linee Guida EBA & BCE Supervisory Framework)",
        "badge": "Min-Mahalanobis • Soglie di Rottura",
        "badge_color": "#ec4899",
        "category": "Regulatory Supervisory Analytics",
        "desc": "Calcolo inverso del vettore macroeconomico più probabile (minima distanza di Mahalanobis) che genera il superamento di una soglia critica di perdita del portafoglio."
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
elif "stress_active_tab_selectbox" in st.session_state and st.session_state["stress_active_tab_selectbox"] in stress_keys:
    st.session_state["stress_active_tab"] = st.session_state["stress_active_tab_selectbox"]
elif "stress_active_tab" in st.session_state and st.session_state["stress_active_tab"] in stress_keys:
    st.session_state["stress_active_tab_selectbox"] = st.session_state["stress_active_tab"]
else:
    st.session_state["stress_active_tab"] = stress_keys[0]
    st.session_state["stress_active_tab_selectbox"] = stress_keys[0]

curr_idx = stress_keys.index(st.session_state["stress_active_tab"])

# Spaziatura e Respiro Layout
st.markdown("<div style='margin-top: 14px; margin-bottom: 6px;'></div>", unsafe_allow_html=True)

# Barra Selettore Compatta Bloomberg Style
c_sel_s, c_prev_s, c_next_s = st.columns([3.8, 0.6, 0.6], vertical_alignment="center")

with c_prev_s:
    if st.button("◀ Prec.", key="btn_stress_prev", use_container_width=True, help="Modulo precedente"):
        new_i = (curr_idx - 1) % len(stress_keys)
        st.session_state["target_subtab_stress_active_tab"] = stress_keys[new_i]
        st.session_state["stress_active_tab"] = stress_keys[new_i]
        st.session_state["stress_active_tab_selectbox"] = stress_keys[new_i]
        st.rerun()

with c_next_s:
    if st.button("Succ. ▶", key="btn_stress_next", use_container_width=True, help="Modulo successivo"):
        new_i = (curr_idx + 1) % len(stress_keys)
        st.session_state["target_subtab_stress_active_tab"] = stress_keys[new_i]
        st.session_state["stress_active_tab"] = stress_keys[new_i]
        st.session_state["stress_active_tab_selectbox"] = stress_keys[new_i]
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

@st.fragment
def render_whatif_custom_fragment(pos_df: pd.DataFrame, port_val: float) -> None:
    """Fragment reattivo isolato: manovrare gli slider macro ricalcola esclusivamente questo container."""
    col_sim1, col_sim2 = st.columns([1, 2.2])
    with col_sim1:
        st.markdown("##### 🎛️ Manovra Parametri Macro")
        benchmark_shock = st.slider("Shock Mercato Azionario (%)", -50, 30, -15, 1, help="Shock generale indici azionari")
        rate_shock_bps = st.slider("Variazione Tassi BCE/FED (bps)", -200, 300, 100, 25, help="+100 bps = rialzo tassi di 1.00%")
        fx_shock_pct = st.slider("Shock Cambio EUR/USD (%)", -20, 20, -5, 1, help="-5% = svalutazione EUR del 5%")
        oil_shock_pct = st.slider("Shock Petrolio / Materie Prime (%)", -40, 60, 20, 5, help="+20% = impennata prezzi energia")

        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        if st.button("⚖️ Simula Ribilanciamento & Staging Ordini", type="primary", use_container_width=True):
            try:
                from components.action_drawers import render_order_blotter_dialog

                # Generazione ordini di de-risking dinamici sulle posizioni effettive
                orders_sim = []
                turnover_sim = 0.0
                tax_sim = 0.0
                de_risk_factor = min(0.35, max(0.10, abs(benchmark_shock) / 100.0 * 0.7))

                if isinstance(pos_df, pd.DataFrame) and not pos_df.empty:
                    col_t = "ticker" if "ticker" in pos_df.columns else ("Ticker" if "Ticker" in pos_df.columns else None)
                    col_q = "qty_net" if "qty_net" in pos_df.columns else ("shares" if "shares" in pos_df.columns else ("Quantità" if "Quantità" in pos_df.columns else None))
                    col_p = "last_price" if "last_price" in pos_df.columns else ("current_price" if "current_price" in pos_df.columns else ("Prezzo Mkt (€)" if "Prezzo Mkt (€)" in pos_df.columns else None))
                    col_pmc = "wacp" if "wacp" in pos_df.columns else ("pmc" if "pmc" in pos_df.columns else ("Prezzo Carico (€)" if "Prezzo Carico (€)" in pos_df.columns else None))
                    col_ac = "asset_class" if "asset_class" in pos_df.columns else ("Asset Class" if "Asset Class" in pos_df.columns else None)

                    for _, r in pos_df.iterrows():
                        tk = str(r.get(col_t, "ASSET")).strip()
                        sh = float(r.get(col_q, 1.0))
                        px = float(r.get(col_p, 100.0))
                        pmc = float(r.get(col_pmc, px))
                        ac = str(r.get(col_ac, "Equity")).lower()

                        if sh <= 0 or px <= 0:
                            continue

                        t_upper = tk.upper()
                        is_crypto = (
                            ("crypto" in ac)
                            or any(t_upper.endswith(s) for s in ["-EUR", "-USD", "-USDT", "-BTC"])
                            or (t_upper in ["BTC", "ETH", "SOL", "ADA", "XRP", "BNB", "USDT", "DOGE", "AVAX", "DOT", "LINK"])
                        )
                        is_etf = any(k in ac for k in ["etf", "fondo", "oicr"]) or any(k in tk.lower() for k in ["etf", "iwda", "swda"])
                        is_gov = any(k in ac for k in ["bond", "obbligaz", "gov"]) or any(k in t_upper for k in ["BTP", "BOT", "BUND", "TREASURY"])

                        isin_raw = str(r.get("isin", r.get("ISIN", ""))).strip()
                        isin_str = isin_raw if (isin_raw and isin_raw != "None" and len(isin_raw) >= 9) else ("— (Crypto)" if is_crypto else "—")

                        if is_gov:
                            # Titoli governativi/obbligazionari: flight-to-quality
                            raw_buy = round(sh * de_risk_factor)
                            sh_buy = max(1.0, float(raw_buy)) if raw_buy >= 1 else 1.0
                            val_buy = round(sh_buy * px, 2)
                            turnover_sim += val_buy
                            orders_sim.append({
                                "ISIN": isin_str,
                                "Ticker": tk,
                                "Azione": "BUY",
                                "Quantità": str(int(sh_buy)),
                                "Prezzo Stimato": px,
                                "Controvalore": val_buy,
                                "Regime Fiscale": "White List (12.5% Tax)",
                                "Plus/Minus Stima": "N/D (Acquisto)",
                            })
                        else:
                            # Asset equity/crypto/rischiosi: de-risking prudenziale
                            if is_crypto:
                                sh_trim = min(sh, round(sh * de_risk_factor, 4))
                                qty_disp = f"{sh_trim:.4f}".rstrip("0").rstrip(".")
                            else:
                                raw_trim = round(sh * de_risk_factor)
                                sh_trim = min(sh, max(1.0, float(raw_trim)) if raw_trim >= 1 else 0.0)
                                qty_disp = str(int(sh_trim))

                            if sh_trim <= 0:
                                continue

                            val_trim = round(sh_trim * px, 2)
                            gain = (px - pmc) * sh_trim
                            tax_rate = 0.26
                            tax_cost = gain * tax_rate if gain > 0 else gain * 0.26
                            tax_sim += tax_cost
                            turnover_sim += val_trim

                            if is_crypto:
                                tax_regime = "Art. 67 (Plusvalenze Cripto)"
                            elif is_etf:
                                tax_regime = "Art. 44 (OICR - Reddito Cap.)"
                            else:
                                tax_regime = "Art. 67 (CG - Compensabile)"

                            orders_sim.append({
                                "ISIN": isin_str,
                                "Ticker": tk,
                                "Azione": "SELL",
                                "Quantità": qty_disp,
                                "Prezzo Stimato": px,
                                "Controvalore": val_trim,
                                "Regime Fiscale": tax_regime,
                                "Plus/Minus Stima": f"{gain:+.2f} €",
                            })

                render_order_blotter_dialog({
                    "turnover": round(turnover_sim, 2),
                    "net_tax_impact": round(tax_sim, 2),
                    "pre_var": 2.45,
                    "post_var": 1.88,
                    "orders": orders_sim,
                }, portfolio_value=port_val, positions=pos_df)
            except Exception as e:
                st.error(f"Errore apertura drawer ordini: {e}")

    from core.risk_engine import compute_custom_macro_stress
    macro_res = compute_custom_macro_stress(
        pos_df, 
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
            df_macro_disp = macro_res["details_df"].rename(columns={
                "ticker": "Ticker",
                "current_value": "Valore Attuale (€)",
                "simulated_impact_pct": "Impatto Stimato (%)",
                "simulated_loss_eur": "Variazione Stimata (€)"
            })
            macro_cfg = {
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Valore Attuale (€)": st.column_config.NumberColumn("Valore Attuale", format="€ %,.2f"),
                "Impatto Stimato (%)": st.column_config.NumberColumn("Impatto Stimato", format="%+.2f%%"),
                "Variazione Stimata (€)": st.column_config.NumberColumn("Variazione Stimata", format="€ %,.2f"),
            }
            render_table_with_export(
                df_macro_disp,
                table_title="📋 Dettaglio Impatto per Singolo Asset",
                file_prefix="simulazione_macro_whatif_posizioni",
                key_suffix="macro_whatif",
                column_config=macro_cfg,
            )

    st.divider()
    st.markdown("#### 🌋 Visualizzatore 3D della Superficie di Rischio (Rates vs Volatility)")
    st.caption("Esplora la superficie 3D interattiva che mappa la perdita di capitale al variare simultaneo dello Shock sui Tassi di Interesse (bps) e dello Shock sulla Volatilità / VIX (%).")

    from core.risk_engine import compute_3d_stress_surface
    surface_data = compute_3d_stress_surface(pos_df)

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

    df_matrix_disp = df_matrix[["Scenario", "Shock Mercato %", "Impatto Portafoglio %", "Differenziale (Alpha) %", "Perdita Stimata (€)"]].copy()
    matrix_cfg = {
        "Scenario": st.column_config.TextColumn("Scenario", width="medium"),
        "Shock Mercato %": st.column_config.NumberColumn("Shock Mercato", format="%+.2f%%"),
        "Impatto Portafoglio %": st.column_config.NumberColumn("Impatto Portafoglio", format="%+.2f%%"),
        "Differenziale (Alpha) %": st.column_config.NumberColumn("Differenziale (Alpha)", format="%+.2f%%"),
        "Perdita Stimata (€)": st.column_config.NumberColumn("Perdita Stimata", format="€ %,.2f"),
    }
    render_table_with_export(
        df_matrix_disp,
        table_title="📋 Matrice Sinottica Dettagliata degli Scenari",
        file_prefix="matrice_scenari_stress_test",
        key_suffix="stress_mat",
        column_config=matrix_cfg,
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
                sc_slug = active_scenario.lower().replace(" ", "_").replace(":", "").replace("/", "_")
                df_disp = df_det.copy()
                tbl_h = max(360, min(560, len(df_disp) * 35 + 38))
                det_cfg = {
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Beta": st.column_config.NumberColumn("Beta", format="%.2f"),
                    "Shock %": st.column_config.NumberColumn("Shock %", format="%+.2f%%"),
                    "Perdita Stimata (€)": st.column_config.NumberColumn("Perdita Stimata (€)", format="€ %,.2f"),
                }
                if "Dato Storico Reale" in df_disp.columns:
                    df_disp["Dato Storico Reale"] = df_disp["Dato Storico Reale"].apply(lambda x: "✅ Reale" if x else "⚡ Beta")
                    det_cfg["Dato Storico Reale"] = st.column_config.TextColumn("Dato Storico Reale", width="small")
                render_table_with_export(
                    df_disp,
                    table_title="📋 Dettaglio per Singola Posizione",
                    file_prefix=f"stress_test_posizioni_{sc_slug}",
                    key_suffix=f"stress_det_{sc_slug}",
                    column_config=det_cfg,
                    height=tbl_h,
                )
                
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

    # Esecuzione del container isolato via @st.fragment
    render_whatif_custom_fragment(pos, portfolio_value)

# ── TAB 4: TOTAL BALANCE SHEET & HUMAN CAPITAL STRESS ─────────
elif active_stress_tab == "🌐 Total Balance Sheet & Human Capital Stress":
    col_tb1, col_tb2 = st.columns([3.2, 1.1])
    with col_tb1:
        st.markdown("#### 🌐 Total Balance Sheet & Human Capital Stress Testing")
        st.caption("Modello olistico di classe BlackRock Aladdin: integra Capitale Umano (quasi-equity/quasi-bond), Real Estate e debito ipotecario con il portafoglio titoli.")
    with col_tb2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida al Total Balance Sheet VaR (TBS-VaR)", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #a855f7; margin-bottom: 3px;">📌 Cos'è il Total Balance Sheet VaR</div>
  <div>Supera l'approccio miope del solo portafoglio finanziario. L'investitore reale possiede Capitale Umano (stipendi futuri scontati), immobili e mutui. Il TBS-VaR calcola la perdita potenziale aggregata considerando le correlazioni incrociate tra mercato azionario, settore professionale e mercato immobiliare.</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #a855f7; margin-bottom: 3px;">💼 Capitale Umano come Quasi-Equity vs Quasi-Bond</div>
  <div>Se lavori nel settore Tech o Finanza, il tuo stipendio e i tuoi bonus sono correlati all'andamento del mercato azionario (alto Beta: Quasi-Equity). Se lavori nel settore pubblico o nella sanità, il tuo reddito è assimilabile a un BTP o Treasury indicizzato (Quasi-Bond).</div>
</div>
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #a855f7; margin-bottom: 3px;">⚠️ Correlazione Catastrofica (Income-Portfolio Shock)</div>
  <div>Avere il 70% del portafoglio in titoli tecnologici lavorando in una Big Tech crea un rischio sistemico: un crollo settoriale mette a repentaglio contemporaneamente il capitale investito e la sicurezza del posto di lavoro.</div>
</div>
</div>
""", button_label="💡 Come funziona il TBS-VaR?")

    from core.wealth.human_capital_engine import HolisticBalanceSheetEngine, LaborIncomeProfile, TotalBalanceSheetState

    SECTORS_META = {
        "Tecnologia & Software (Big Tech, Start-up)": {"beta": 1.25, "sector": "Technology"},
        "Servizi Finanziari & Investment Banking": {"beta": 1.15, "sector": "Financials"},
        "Consumi Ciclici & Retail": {"beta": 0.85, "sector": "Consumer Cyclicals"},
        "Manifattura Industriale & Automotive": {"beta": 0.90, "sector": "Industrials"},
        "Sanità, Farmaceutico & Biotech": {"beta": 0.45, "sector": "Healthcare"},
        "Pubblica Amministrazione, Istruzione & Difesa": {"beta": 0.08, "sector": "Public Sector"},
        "Consulenza & Libera Professione": {"beta": 1.05, "sector": "Professional Services"}
    }

    c_inputs, c_outputs = st.columns([1.1, 2.1])

    with c_inputs:
        st.markdown("##### 👤 Profilo Professionale & Reddito")
        selected_sector_label = st.selectbox(
            "Settore Lavorativo:",
            options=list(SECTORS_META.keys()),
            index=0,
            key="tbs_sector_sel"
        )
        sector_info = SECTORS_META[selected_sector_label]
        
        income_annual = st.number_input(
            "Reddito Netto Annuo (€):",
            min_value=10000.0,
            max_value=1000000.0,
            value=55000.0,
            step=5000.0,
            key="tbs_income_input"
        )
        years_retire = st.slider(
            "Anni al Pensionamento:",
            min_value=1,
            max_value=45,
            value=22,
            key="tbs_years_retire"
        )
        growth_rate = st.slider(
            "Crescita Reale Annua Stipendio (%):",
            min_value=0.0,
            max_value=6.0,
            value=1.5,
            step=0.25,
            key="tbs_growth_rate"
        ) / 100.0

        st.markdown("##### 🏡 Patrimonio Illiquido & Debito")
        re_val = st.number_input(
            "Valore di Mercato Immobili (€):",
            min_value=0.0,
            max_value=5000000.0,
            value=350000.0,
            step=25000.0,
            key="tbs_re_val"
        )
        mortgage_val = st.number_input(
            "Debito Residuo Mutuo (€):",
            min_value=0.0,
            max_value=2000000.0,
            value=130000.0,
            step=10000.0,
            key="tbs_mortgage_val"
        )
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            is_var_rate = st.checkbox("Mutuo a Tasso Variabile", value=True, key="tbs_is_var")
        with col_m2:
            mortgage_dur = st.number_input("Duration Mutuo (anni):", min_value=1.0, max_value=30.0, value=7.5, step=0.5, key="tbs_mortgage_dur")

        unavoidable_exp = st.number_input(
            "Spese Indispensabili Annue (€):",
            min_value=5000.0,
            max_value=200000.0,
            value=26000.0,
            step=2000.0,
            key="tbs_unavoidable_exp"
        )

    # Engine execution
    lab_prof = LaborIncomeProfile(
        current_annual_net_income=float(income_annual),
        years_to_retirement=int(years_retire),
        income_growth_rate=float(growth_rate),
        industry_sector=sector_info["sector"],
        sector_beta=sector_info["beta"]
    )

    liq_val = float(portfolio_value) if portfolio_value > 0 else 100000.0
    w_vec = np.ones(1)
    cov_mat = np.array([[0.0002]])
    if not pos.empty and "current_value" in pos.columns and liq_val > 0:
        w_vec = (pos["current_value"] / liq_val).to_numpy()
        n_a = len(w_vec)
        cov_mat = np.eye(n_a) * 0.00025

    tbs_state = TotalBalanceSheetState(
        liquid_portfolio_value=liq_val,
        liquid_portfolio_weights=w_vec,
        liquid_covariance_matrix=cov_mat,
        real_estate_value=float(re_val),
        real_estate_volatility=0.08,
        real_estate_beta=0.25,
        mortgage_debt_outstanding=float(mortgage_val),
        mortgage_duration=float(mortgage_dur),
        is_variable_rate=is_var_rate,
        annual_unavoidable_expenses=float(unavoidable_exp),
        labor_profile=lab_prof
    )

    holistic_eng = HolisticBalanceSheetEngine(risk_free_rate=0.03, equity_risk_premium=0.05)
    tbs_res = holistic_eng.compute_total_balance_sheet_var(tbs_state, confidence=0.95, horizon_years=1.0)

    with c_outputs:
        st.markdown("##### 🏛️ Bilancio Patrimoniale Olistico Integrato (TBS KPIs)")
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            metric_card("Patrimonio Netto Totale", fmt_eur(tbs_res["total_net_worth_eur"]), delta="Attivi - Debito", delta_color="normal")
        with kpi_col2:
            metric_card("Valore Capitale Umano", fmt_eur(tbs_res["human_capital_pv_eur"]), delta=f"{years_retire} anni flusso attualizzato", delta_color="normal")
        with kpi_col3:
            metric_card("Volatilità Annua Attivo", f"{tbs_res['total_assets_annual_volatility']*100:.1f}%", delta="Rischio Olistico Blended", delta_color="inverse")

        kpi2_col1, kpi2_col2, kpi2_col3 = st.columns(3)
        with kpi2_col1:
            metric_card("TBS-VaR 95% (1 Anno)", fmt_eur(tbs_res["tbs_var_eur"]), delta=f"{tbs_res['tbs_var_pct_net_worth']:.1f}% del Patrimonio", delta_color="inverse")
        with kpi2_col2:
            metric_card("TBS-CVaR 95% (Shortfall)", fmt_eur(tbs_res["tbs_cvar_eur"]), delta=f"{tbs_res['tbs_cvar_pct_net_worth']:.1f}% del Patrimonio", delta_color="inverse")
        with kpi2_col3:
            metric_card("Emergency Runway", f"{tbs_res['emergency_runway_months']:.1f} Mesi", delta="Autonomia di Cassa", delta_color="normal" if tbs_res['emergency_runway_months'] >= 6 else "inverse")

        # Visualizzazione Waterfall del Bilancio
        st.markdown("###### 📊 Scomposizione del Bilancio Patrimoniale Olistico (€)")
        wf_measures = ["relative", "relative", "relative", "relative", "total"]
        wf_x = ["Portafoglio Liquido", "Immobili", "Capitale Umano", "Debito / Mutuo", "Patrimonio Netto"]
        wf_y = [liq_val, float(re_val), tbs_res["human_capital_pv_eur"], -float(mortgage_val), tbs_res["total_net_worth_eur"]]
        wf_text = [fmt_eur(v) for v in wf_y]

        fig_tbs_wf = go.Figure(go.Waterfall(
            name="TBS",
            orientation="v",
            measure=wf_measures,
            x=wf_x,
            textposition="outside",
            text=wf_text,
            y=wf_y,
            connector={"line": {"color": "rgba(255,255,255,0.25)", "dash": "dot"}},
            decreasing={"marker": {"color": "#f85149"}},
            totals={"marker": {"color": "#a855f7"}},
            increasing={"marker": {"color": "#38bdf8"}},
            width=0.45,
            cliponaxis=False
        ))
        fig_tbs_wf.update_layout(
            template="plotly_dark",
            height=320,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Euro (€)", gridcolor="rgba(255,255,255,0.06)", tickprefix="€ "),
            xaxis=dict(showgrid=False)
        )
        apply_plotly_theme(fig_tbs_wf)
        st.plotly_chart(fig_tbs_wf, use_container_width=True)

        # Decomposizione Capitale Umano: Quasi-Equity vs Quasi-Bond & Alert
        c_don, c_alt = st.columns([1, 1.4])
        with c_don:
            fig_hc_pie = go.Figure(go.Pie(
                labels=["Quasi-Equity (Rischio Azionario)", "Quasi-Bond (Difensivo/Stabile)"],
                values=[tbs_res["human_capital_quasi_equity_eur"], tbs_res["human_capital_quasi_bond_eur"]],
                hole=0.55,
                marker=dict(colors=["#f85149", "#3fb950"]),
                textinfo="label+percent"
            ))
            fig_hc_pie.update_layout(
                title="Natura del Capitale Umano",
                template="plotly_dark",
                height=240,
                margin=dict(l=10, r=10, t=35, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )
            apply_plotly_theme(fig_hc_pie)
            st.plotly_chart(fig_hc_pie, use_container_width=True)

        with c_alt:
            st.markdown("###### 🛡️ Prescrizioni di Hedging & Vulnerabilità")
            if tbs_res["sector_hedging_needed"]:
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.35); border-left: 4px solid #ef4444; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <b style="color: #f87171; font-size: 13px;">⚠️ Rischio di Correlazione Catastrofica Rilevato!</b><br>
                    <span style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                    Il tuo settore lavorativo (<b>{sector_info['sector']}</b>, Beta: {sector_info['beta']:.2f}) espone il tuo Capitale Umano a un rischio implicito azionario pari a <b>{fmt_eur(tbs_res['human_capital_quasi_equity_eur'])}</b>.<br>
                    <b>Raccomandazione di Prescrizione:</b> Sottopesare il settore nel portafoglio liquido di almeno <b>{fmt_eur(tbs_res['recommended_sector_underweight_eur'])}</b> per immunizzare la correlazione lavoro-investimenti.
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: rgba(63, 185, 80, 0.1); border: 1px solid rgba(63, 185, 80, 0.35); border-left: 4px solid #3fb950; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <b style="color: #3fb950; font-size: 13px;">✅ Capitale Umano a Basso Beta Sistemico</b><br>
                    <span style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                    La tua professione in <b>{sector_info['sector']}</b> genera flussi di cassa stabili (Quasi-Bond: {tbs_res['weights_breakdown']['human_capital_pct']:.1f}% dell'attivo). Puoi assumere una quota maggiore di rischio azionario nel portafoglio liquido senza compromettere la resilienza del bilancio.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            if is_var_rate and tbs_res["debt_stress_component_eur"] > 0:
                st.markdown(f"""
                <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.35); border-left: 4px solid #f59e0b; border-radius: 8px; padding: 10px 14px;">
                    <b style="color: #fbbf24; font-size: 13px;">⚡ Shock Rate Stress su Mutuo (+200 bps)</b><br>
                    <span style="font-size: 12px; color: #cbd5e1; line-height: 1.45;">
                    Un rialzo di 200 punti base incrementa il costo attualizzato del debito di <b>{fmt_eur(tbs_res['debt_stress_component_eur'])}</b> (incluso nel TBS-VaR).
                    </span>
                </div>
                """, unsafe_allow_html=True)

# ── TAB 5: PORTFOLIO FIXED INCOME & ALM TREASURY ENGINE ───────
elif active_stress_tab == "📈 Portfolio Fixed Income & ALM Treasury":
    st.markdown("#### 📈 Portfolio Fixed Income & ALM Treasury Engine")
    st.caption("Aggregazione del comparto a reddito fisso: Macaulay/Modified Duration ponderata, DV01/PVBP, Key Rate Durations e scenari di rotazione curva.")

    from core.fixed_income import compute_portfolio_fixed_income_analytics
    fi_res = compute_portfolio_fixed_income_analytics(df_positions=pos, df_prices=results.get("prices"))

    if not fi_res["has_fixed_income"]:
        st.info("ℹ️ " + fi_res.get("message", "Nessuna posizione a reddito fisso individuata."))
    else:
        k_fi1, k_fi2, k_fi3, k_fi4 = st.columns(4)
        with k_fi1:
            metric_card("Controvalore Obbligazionario", fmt_eur(fi_res["fixed_income_value"]), delta=f"{fi_res['fixed_income_weight_pct']:.1f}% del Portafoglio", delta_color="normal")
        with k_fi2:
            metric_card("Modified Duration Ponderata", f"{fi_res['weighted_mod_duration']:.2f} anni", delta=f"Mac: {fi_res['weighted_mac_duration']:.2f}y", delta_color="normal")
        with k_fi3:
            metric_card("Portfolio DV01 (PVBP)", fmt_eur(fi_res["portfolio_dv01"]), delta="€ per +1 bps", delta_color="inverse")
        with k_fi4:
            metric_card("Convessità Effettiva", f"{fi_res['weighted_convexity']:.3f}", delta="2° Ordine Taylor", delta_color="normal")

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_krd, col_scen = st.columns([1.2, 1.8])

        with col_krd:
            st.markdown("##### 📐 Key Rate Durations (2Y, 5Y, 10Y, 30Y)")
            krd_df = pd.DataFrame(list(fi_res["key_rate_durations"].items()), columns=["Nodo Curva", "Key Rate Duration (Anni)"])
            fig_krd = go.Figure(go.Bar(
                x=krd_df["Nodo Curva"],
                y=krd_df["Key Rate Duration (Anni)"],
                marker_color="#10b981",
                text=[f"{v:.2f}y" for v in krd_df["Key Rate Duration (Anni)"]],
                textposition="auto"
            ))
            fig_krd.update_layout(
                template="plotly_dark", height=280,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Duration (Anni)", gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(l=10, r=10, t=20, b=10)
            )
            apply_plotly_theme(fig_krd)
            st.plotly_chart(fig_krd, use_container_width=True, config={"displayModeBar": False})

        with col_scen:
            st.markdown("##### 🌪️ Scenari di Shift & Rotazione Curva (Steepener / Flattener)")
            scen_rows = []
            for sc_k, sc_v in fi_res["curve_stress_scenarios"].items():
                scen_rows.append({
                    "Scenario": sc_v["name"],
                    "Rendimento Comparto (%)": sc_v["fi_return_pct"],
                    "Impatto Monetario (€)": sc_v["fi_pnl_eur"],
                    "Impatto Portafoglio Totale (%)": sc_v["portfolio_impact_pct"],
                })
            df_scen = pd.DataFrame(scen_rows)
            st.dataframe(
                df_scen,
                column_config={
                    "Scenario": st.column_config.TextColumn("Scenario Curva Tassi", width="large"),
                    "Rendimento Comparto (%)": st.column_config.NumberColumn("Impatto Comparto", format="%+.2f%%"),
                    "Impatto Monetario (€)": st.column_config.NumberColumn("PnL Stimato", format="€ %,.2f"),
                    "Impatto Portafoglio Totale (%)": st.column_config.NumberColumn("Incidenza Totale", format="%+.2f%%"),
                },
                use_container_width=True,
                hide_index=True
            )

        if fi_res["fi_positions_breakdown"]:
            st.markdown("##### 📋 Dettaglio Titoli & ETF Obbligazionari")
            df_det_fi = pd.DataFrame(fi_res["fi_positions_breakdown"])
            render_table_with_export(
                df=df_det_fi,
                table_title="Composizione Comparto Reddito Fisso",
                file_prefix="portfolio_fixed_income_breakdown",
                key_suffix="p7_fi_breakdown",
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "name": st.column_config.TextColumn("Nome Strumento", width="medium"),
                    "value_eur": st.column_config.NumberColumn("Valore (€)", format="€ %,.2f"),
                    "weight_fi_pct": st.column_config.NumberColumn("Peso FI (%)", format="%.2f%%"),
                    "modified_duration": st.column_config.NumberColumn("Mod Duration", format="%.2f"),
                    "convexity": st.column_config.NumberColumn("Convessità", format="%.3f"),
                    "ytm_pct": st.column_config.NumberColumn("YTM Stimato", format="%.2f%%"),
                    "dv01_eur": st.column_config.NumberColumn("DV01 (€/bps)", format="€ %,.2f"),
                    "loss_plus_100bps_eur": st.column_config.NumberColumn("Perdita +100bps (€)", format="€ %,.2f"),
                },
                hide_index=True
            )

# ── TAB 6: RISCHIO LIQUIDITA & ORIZZONTE DTL ──────────────────
elif active_stress_tab == "💧 Rischio Liquidità & Orizzonte DTL (Basel III / UCITS)":
    st.markdown("#### 💧 Motore Istituzionale di Liquidità & Orizzonte di Smobilizzo")
    st.caption("Valutazione dei giorni necessari alla liquidazione (DTL), impatto di mercato Almgren-Chriss, indice di Amihud e Liquidity-Adjusted VaR (L-VaR).")

    from core.risk_engine import compute_portfolio_liquidity_risk
    liq_res = compute_portfolio_liquidity_risk(
        df_positions=pos,
        df_prices=results.get("prices"),
        participation_rate=0.10,
        portfolio_var_99_pct=results.get("var_99")
    )

    l_c1, l_c2, l_c3, l_c4 = st.columns(4)
    with l_c1:
        metric_card("Days to Liquidate (Medio)", f"{liq_res['weighted_dtl_days']:.2f} giorni", delta="Limite 10% ADV", delta_color="normal")
    with l_c2:
        metric_card("Bottleneck di Smobilizzo", f"{liq_res['max_dtl_days']:.1f} giorni", delta=f"Asset: {liq_res['bottleneck_ticker']}", delta_color="inverse")
    with l_c3:
        metric_card("L-VaR 99% Endogeno", fmt_eur(liq_res["endogenous_lvar_99_eur"]), delta=f"+{liq_res['liquidity_risk_premium_pct']:.1f}% vs VaR Standard", delta_color="inverse")
    with l_c4:
        metric_card("Costo Totale Smobilizzo", fmt_eur(liq_res["total_liquidation_cost_eur"]), delta="Spread + Market Impact", delta_color="inverse")

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    c_t_chart, c_t_info = st.columns([1.3, 1.7])

    with c_t_chart:
        st.markdown("##### 📊 Ripartizione nei 4 Tier di Liquidità")
        tiers = liq_res["liquidity_tiers_pct"]
        fig_tiers = go.Figure(go.Pie(
            labels=["Tier 1 (< 1 giorno)", "Tier 2 (1-3 giorni)", "Tier 3 (3-7 giorni)", "Tier 4 (> 7 giorni)"],
            values=[tiers["tier_1_sub_1d"], tiers["tier_2_1_to_3d"], tiers["tier_3_3_to_7d"], tiers["tier_4_above_7d"]],
            hole=0.45,
            marker_colors=["#10b981", "#38bdf8", "#f59e0b", "#ef4444"]
        ))
        fig_tiers.update_layout(
            template="plotly_dark", height=280,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="top", y=-0.1)
        )
        apply_plotly_theme(fig_tiers)
        st.plotly_chart(fig_tiers, use_container_width=True, config={"displayModeBar": False})

    with c_t_info:
        st.markdown("##### ℹ️ Prescrizioni di Rischio Liquidità (Basel III Standard)")
        t4_pct = tiers["tier_4_above_7d"]
        if t4_pct > 15.0:
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.35); border-left: 4px solid #ef4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <b style="color: #f87171; font-size: 13.5px;">⚠️ Concentrazione Eccessiva in Asset Illiquidi ({t4_pct:.1f}%)</b><br>
                <span style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
                Oltre il 15% del portafoglio richiede più di 7 giorni di borsa aperta per essere liquidato senza eccedere il 10% del volume medio giornaliero.<br>
                <b>Collo di bottiglia:</b> <code>{liq_res['bottleneck_ticker']}</code> ({liq_res['max_dtl_days']:.1f} giorni). In caso di margin call o shock sistemico, i costi di disinvestimento forzato aumenteranno sensibilmente la perdita effettiva.
                </span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.35); border-left: 4px solid #10b981; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <b style="color: #34d399; font-size: 13.5px;">✅ Profilo di Liquidità Istituzionale Eccellente</b><br>
                <span style="font-size: 12px; color: #cbd5e1; line-height: 1.5;">
                Il <b>{tiers['tier_1_sub_1d']:.1f}%</b> del portafoglio può essere smobilizzato entro 24 ore a un tasso di partecipazione prudenziale del 10% di ADV.<br>
                Il Liquidity-Adjusted VaR (L-VaR) aggiunge un premio di rischio modesto pari a solo il <b>+{liq_res['liquidity_risk_premium_pct']:.1f}%</b> rispetto al VaR non rettificato.
                </span>
            </div>
            """, unsafe_allow_html=True)

    if liq_res["positions_liquidity_breakdown"]:
        st.markdown("##### 📋 Dettaglio Liquidità & Market Impact per Singola Posizione")
        df_liq_pos = pd.DataFrame(liq_res["positions_liquidity_breakdown"])
        render_table_with_export(
            df=df_liq_pos,
            table_title="Analisi Orizzonte di Liquidazione per Asset",
            file_prefix="portfolio_liquidity_risk_breakdown",
            key_suffix="p7_liq_breakdown",
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "name": st.column_config.TextColumn("Nome Asset", width="medium"),
                "value_eur": st.column_config.NumberColumn("Valore (€)", format="€ %,.2f"),
                "adv_eur": st.column_config.NumberColumn("ADV Stimato (€)", format="€ %,.0f"),
                "days_to_liquidate_10pct": st.column_config.NumberColumn("DTL (10% ADV)", format="%.2f g"),
                "days_to_liquidate_20pct": st.column_config.NumberColumn("DTL (20% ADV)", format="%.2f g"),
                "amihud_illiquidity_ratio": st.column_config.NumberColumn("Amihud Ratio", format="%.2e"),
                "bid_ask_spread_bps": st.column_config.NumberColumn("Spread (bps)", format="%.1f"),
                "estimated_liquidation_cost_eur": st.column_config.NumberColumn("Costo Smobilizzo (€)", format="€ %,.2f"),
                "tier": st.column_config.TextColumn("Tier di Liquidità", width="medium"),
            },
            hide_index=True
        )

# ── TAB 7: REVERSE STRESS TESTING (EBA / BCE) ──────────────────
elif active_stress_tab == "⚡ Reverse Stress Testing (EBA / BCE)":
    st.markdown("#### ⚡ Reverse Stress Testing Istituzionale (Linee Guida EBA & BCE)")
    st.caption("Calcolo del vettore macroeconomico più plausibile (minima distanza di Mahalanobis) che causa il superamento della soglia di perdita critica indicata.")

    from core.macro_stress_engine import compute_reverse_stress_test

    col_rev_c1, col_rev_c2 = st.columns([2.5, 1.5])
    with col_rev_c1:
        target_loss_sel = st.slider(
            "Seleziona Soglia di Perdita Critica (%):",
            min_value=-60.0,
            max_value=-10.0,
            value=-25.0,
            step=2.5,
            format="%.1f%%",
            help="Definisce il livello di drawdown o perdita patrimoniale da investigare a ritroso."
        )
    with col_rev_c2:
        st.markdown("""
        <div style="background: rgba(236, 72, 153, 0.1); border-left: 3px solid #ec4899; padding: 10px 14px; border-radius: 6px; font-size: 12.5px; color: #cbd5e1;">
            <b>Obiettivo EBA / BCE:</b> Identificare i punti ciechi di correlazione e i canali di trasmissione sistemica prima che si verifichino.
        </div>
        """, unsafe_allow_html=True)

    rev_res = compute_reverse_stress_test(
        positions_df=pos,
        portfolio_value=float(portfolio_value or 100000.0),
        target_loss_pct=target_loss_sel,
    )

    r_c1, r_c2, r_c3, r_c4 = st.columns(4)
    with r_c1:
        metric_card("Perdita Target", fmt_eur(rev_res["target_loss_eur"]), delta=f"{rev_res['target_loss_pct']:.1f}%", delta_color="inverse")
    with r_c2:
        metric_card("Distanza di Mahalanobis", f"{rev_res['mahalanobis_distance']:.2f} σ", delta="Min-Distance Solver", delta_color="normal")
    with r_c3:
        metric_card("Valutazione Plausibilità", rev_res["severity_badge"], delta=rev_res["implied_frequency_estimate"], delta_color="normal")
    with r_c4:
        metric_card("Valore Post-Shock", fmt_eur(rev_res["post_shock_portfolio_value_eur"]), delta="Capitale Residuo", delta_color="normal")

    st.write("")
    col_chart_rev1, col_chart_rev2 = st.columns([1.6, 1.2])

    with col_chart_rev1:
        st.markdown("##### 🌪️ Shock Ottimali Richiesti per Macro-Fattore")
        df_sh = rev_res["factors_df"].copy()
        fig_sh = px.bar(
            df_sh,
            x="Fattore Macro",
            y="Valore Grezzo",
            color="Impatto su Portafoglio",
            color_continuous_scale="RdBu_r",
            title="Vettore di Shock Macro Più Plausibile (Distanza Minima)",
            template="plotly_dark",
            height=320,
        )
        fig_sh.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=30, b=10))
        apply_plotly_theme(fig_sh)
        st.plotly_chart(fig_sh, use_container_width=True, config={"displayModeBar": False})

    with col_chart_rev2:
        st.markdown("##### 🍰 Quota di Contribuzione alla Perdita Totale")
        df_sh_pie = df_sh[df_sh["Valore Grezzo"] != 0].copy()
        fig_pie = px.pie(
            df_sh_pie,
            names="Fattore Macro",
            values=df_sh_pie["Quota Perdita (%)"].str.rstrip("%").astype(float).abs(),
            title="Scomposizione Causale della Rottura",
            hole=0.45,
            template="plotly_dark",
            height=320,
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=30, b=10))
        apply_plotly_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    st.markdown("##### 📋 Dettaglio Parametrico & Sensibilità ai Fattori Macro")
    render_table_with_export(
        df=rev_res["factors_df"][["Fattore Macro", "Sensibilità (β)", "Shock Ottimale Richiesto", "Impatto su Portafoglio", "Quota Perdita (%)"]],
        table_title="Matrice Reverse Stress Test EBA",
        file_prefix="reverse_stress_test_factors",
        key_suffix="p7_rev_stress_breakdown",
        hide_index=True,
    )

st.divider()

# ── SEZIONE STRESS TEST MACRO NORMATIVO (EBA / FED CCAR) & REVERSE STRESS ──
st.markdown("### 🏛️ Macro Factor Stress Testing Normativo (EBA / Fed CCAR) & Reverse Stress")
st.caption("Valutazione del portafoglio sotto scenari macroeconomici istituzionali congiunti (European Banking Authority, Federal Reserve) e calcolo delle soglie di rottura tramite Reverse Stress Testing.")

from core.macro_stress_engine import compute_macro_scenario_stress_test, compute_reverse_stress_test

macro_res = compute_macro_scenario_stress_test(df_positions=pos, results=results)

m_c1, m_c2, m_c3, m_c4 = st.columns(4)
with m_c1:
    metric_card("Capitale Sottoposto a Test", fmt_eur(macro_res["initial_portfolio_value_eur"]), delta="Valutazione Base", delta_color="normal")
with m_c2:
    metric_card("Scenario Più Severo", macro_res["worst_case_scenario"][:24], delta="EBA / Fed Stress", delta_color="normal")
with m_c3:
    metric_card("Drawdown Max Normativo", f"{macro_res['worst_case_drawdown_pct']:+.2f}%", delta="Shock Combinato Macro", delta_color="inverse")
with m_c4:
    metric_card("Perdita Stimata Max", fmt_eur(macro_res["worst_case_loss_eur"]), delta="Worst Case Loss", delta_color="inverse")

st.write("")

c_m_l, c_m_r = st.columns([3, 2])
with c_m_l:
    st.markdown("##### 📋 Risultati Scenari Macroeconomici Istituzionali")
    st.dataframe(
        macro_res["scenarios_df"][["scenario_name", "equity_shock_pct", "rate_shock_bps", "credit_spread_bps", "commodities_shock_pct", "portfolio_return_pct", "pnl_impact_eur"]].rename(columns={
            "scenario_name": "Scenario Istituzionale",
            "equity_shock_pct": "Equity Shock (%)",
            "rate_shock_bps": "Tassi (bps)",
            "credit_spread_bps": "Spread (bps)",
            "commodities_shock_pct": "Materie Prime (%)",
            "portfolio_return_pct": "Impatto Portafoglio (%)",
            "pnl_impact_eur": "PnL (€)"
        }),
        use_container_width=True,
        hide_index=True
    )

with c_m_r:
    st.markdown("##### 🎯 Reverse Stress Testing (Break-Even Solver)")
    target_dd_input = st.slider("Seleziona Drawdown Target di Rottura (%):", min_value=-50.0, max_value=-5.0, value=-20.0, step=5.0)
    rev_res = compute_reverse_stress_test(df_positions=pos, results=results, target_drawdown_pct=target_dd_input)
    sol = rev_res["break_even_solutions"]

    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(239, 68, 68, 0.3); border-left: 4px solid #ef4444; border-radius: 10px; padding: 14px 18px;">
        <b style="color: #f87171; font-size: 14px;">Soglie Minime per Causare {target_dd_input:.0f}% di Perdita ({fmt_eur(rev_res['target_loss_eur'])}):</b><br>
        <span style="font-size: 12.5px; color: #cbd5e1; line-height: 1.6;">
        • <b>Solo Azionario:</b> Crollo del <b>{sol['pure_equity_crash_pct']:.1f}%</b> (a tassi invariati)<br>
        • <b>Solo Tassi d'Interesse:</b> Impennata di <b>+{sol['pure_rate_shock_bps']:.0f} bps</b> (a equity stabile)<br>
        • <b>Scenario Congiunto (50/50):</b> Crollo Azionario <b>{sol['combined_scenario']['equity_crash_pct']:.1f}%</b> CON Tassi <b>+{sol['combined_scenario']['rate_shock_bps']:.0f} bps</b><br>
        <b style="color: #38bdf8;">Rarità Statistica Stimata: {rev_res['implied_frequency_estimate']} (Z-Score: {rev_res['implied_z_score']})</b>
        </span>
    </div>
    """, unsafe_allow_html=True)


# ── V9.11.0: REGULATORY STRESS TESTING DOSSIER (4-PAGE PDF) & TOTAL WEALTH REVERSE STRESS ──
st.markdown("---")
st.markdown("#### 🏛️ Regulatory Stress Testing Dossier & Total Wealth Ruin Barrier (EBA / Solvency II)")
st.caption("Generazione documentale ufficiale conforme agli standard European Banking Authority (EBA) e stress inverso multi-asset del bilancio patrimoniale consolidato.")

col_dossier1, col_dossier2 = st.columns([3, 1], vertical_alignment="center")
with col_dossier1:
    st.markdown("""
    Il **Regulatory Stress Testing Dossier** è un report esecutivo ad alta risoluzione (4 Pagine A4) per Comitati Rischi,
    Private Banking e Audit Interno. Include l'impatto degli scenari EBA 2026/Fed CCAR, decomposizione marginale del rischio,
    reverse stress con distanza di Mahalanobis e piano di mitigazione patrimoniale.
    """)
with col_dossier2:
    from core.pdf_generator import generate_regulatory_stress_testing_dossier_pdf
    pdf_stress_data = {
        "portfolio_nav": float(macro_res.get("initial_portfolio_value_eur", 1_000_000.0)),
        "worst_loss_pct": float(macro_res.get("worst_case_drawdown_pct", -28.45)),
        "worst_loss_eur": float(macro_res.get("worst_case_loss_eur", 284500.0)),
        "scenarios": macro_res.get("scenarios_df"),
        "reverse_stress": rev_res,
    }
    dossier_pdf = generate_regulatory_stress_testing_dossier_pdf(
        portfolio_name=st.session_state.get("portfolio_name", "Portafoglio Istituzionale"),
        stress_data=pdf_stress_data,
        base_currency="EUR",
    )
    st.download_button(
        label="📑 Scarica Dossier Regolamentare (4 Pagine PDF)",
        data=dossier_pdf,
        file_name=f"ARGUS_Regulatory_Stress_Dossier_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("##### 🏦 Total Wealth Reverse Stress Testing (Solvency & Ruin Multi-Asset)")
st.caption("Identificazione della combinazione di shock minimi più verosimile (Mahalanobis Distance) sul patrimonio familiare/HNWI.")

with st.expander("🔬 Configura Bilancio Patrimoniale & Vincoli di Solvibilità", expanded=False):
    tw_c1, tw_c2, tw_c3 = st.columns(3)
    with tw_c1:
        tw_liquid = st.number_input("Attivi Finanziari Liquidi (€):", min_value=0.0, value=float(macro_res.get("initial_portfolio_value_eur", 500000.0)), step=50000.0)
        tw_re = st.number_input("Patrimonio Immobiliare (€):", min_value=0.0, value=800000.0, step=50000.0)
    with tw_c2:
        tw_corp = st.number_input("Partecipazioni Aziendali / PMI (€):", min_value=0.0, value=400000.0, step=50000.0)
        tw_illiq = st.number_input("Beni da Collezione & Illiquidi (€):", min_value=0.0, value=100000.0, step=20000.0)
    with tw_c3:
        tw_debt = st.number_input("Debito & Mutui Passivi (€):", min_value=0.0, value=600000.0, step=50000.0)
        tw_target_type = st.selectbox("Modalità di Stress Inverso:", options=["solvency", "ruin"], format_func=lambda x: "Solvency Ruin (Debt-to-Assets)" if x == "solvency" else "Net Worth Ruin (Perdita PN)")
        if tw_target_type == "solvency":
            tw_threshold = st.slider("Soglia Critica Debt-to-Assets (%):", min_value=40.0, max_value=90.0, value=65.0, step=5.0) / 100.0
        else:
            tw_threshold = st.slider("Perdita Minima Net Worth (%):", min_value=20.0, max_value=80.0, value=50.0, step=5.0) / 100.0

from core.wealth.total_wealth_reverse_stress import compute_total_wealth_reverse_stress

tw_balance = {
    "liquid_assets": tw_liquid,
    "real_estate": tw_re,
    "corporate_equity": tw_corp,
    "illiquid_assets": tw_illiq,
    "total_liabilities": tw_debt,
}
tw_res = compute_total_wealth_reverse_stress(
    balance_sheet=tw_balance,
    target_type=tw_target_type,
    target_threshold=tw_threshold,
)

tw_k1, tw_k2, tw_k3, tw_k4 = st.columns(4)
with tw_k1:
    metric_card("Mahalanobis Distance", f"{tw_res['mahalanobis_distance']:.2f}σ", delta="Vulnerabilità Strutturale", delta_color="normal")
with tw_k2:
    metric_card("Probabilità Implicita", f"{tw_res['implied_probability_pct']:.3f}%", delta=f"Ritorno: 1/{tw_res['return_period_years']} anni", delta_color="normal")
with tw_k3:
    metric_card("Fattore Più Vulnerabile", tw_res["most_vulnerable_factor"], delta="Massima Perdita EUR", delta_color="inverse")
with tw_k4:
    metric_card("Perdita Net Worth Stimata", fmt_eur(tw_res["breakdown_loss"]["total_net_worth_loss_eur"]), delta=f"Pre: {fmt_eur(tw_res['pre_stress_balance_sheet']['net_worth_eur'])}", delta_color="inverse")

df_tw_shocks = pd.DataFrame([
    {"Fattore di Rischio Patrimoniale": "Mercati Finanziari Liquidi", "Shock % Richiesto": f"{tw_res['factor_shocks']['liquid_markets_pct']:+.1f}%", "Perdita (€)": fmt_eur(tw_res['breakdown_loss']['liquid_markets_loss_eur'])},
    {"Fattore di Rischio Patrimoniale": "Settore Immobiliare", "Shock % Richiesto": f"{tw_res['factor_shocks']['real_estate_pct']:+.1f}%", "Perdita (€)": fmt_eur(tw_res['breakdown_loss']['real_estate_loss_eur'])},
    {"Fattore di Rischio Patrimoniale": "Partecipazioni / Corporate PMI", "Shock % Richiesto": f"{tw_res['factor_shocks']['corporate_equity_pct']:+.1f}%", "Perdita (€)": fmt_eur(tw_res['breakdown_loss']['corporate_equity_loss_eur'])},
    {"Fattore di Rischio Patrimoniale": "Passività / Mutui (Euribor Spread)", "Shock % Richiesto": f"{tw_res['factor_shocks']['debt_liabilities_pct']:+.1f}%", "Perdita (€)": fmt_eur(tw_res['breakdown_loss']['debt_increase_eur'])},
    {"Fattore di Rischio Patrimoniale": "Beni di Lusso / Illiquidi", "Shock % Richiesto": f"{tw_res['factor_shocks']['illiquid_luxury_pct']:+.1f}%", "Perdita (€)": fmt_eur(tw_res['breakdown_loss']['illiquid_luxury_loss_eur'])},
])
st.table(df_tw_shocks)


# ── V9.12.0: SOLVENCY II STANDARD FORMULA & SCR ENGINE ─────────────
st.markdown("---")
st.markdown("#### 🛡️ Solvency II Standard Formula & SCR Capital Engine (EIOPA QRT S.25.01 / S.26.01)")
st.caption("Calcolo del Requisito Patrimoniale di Solvibilita (SCR) conforme al Regolamento Delegato (UE) 2015/35.")

from core.solvency2_engine import compute_solvency2_standard_formula

with st.expander("⚙️ Parametri Solvency II & Fondi Propri Ammissibili", expanded=False):
    s2_c1, s2_c2 = st.columns(2)
    with s2_c1:
        s2_eof = st.number_input("Eligible Own Funds (Tier 1 + Tier 2) (€):", min_value=100000.0, value=2500000.0, step=100000.0)
        s2_tp = st.number_input("Riserve Tecniche Lorde (€):", min_value=0.0, value=1500000.0, step=100000.0)
    with s2_c2:
        s2_symm = st.slider("Aggiustamento Simmetrico Azionario (%):", min_value=-10.0, max_value=10.0, value=0.0, step=1.0) / 100.0

sample_s2_assets = [
    {"name": "Azioni Core Europa", "asset_type": "equity_type1", "value": 800000.0, "duration": 0.0, "cqs_rating": 2, "currency": "EUR"},
    {"name": "Emerging Markets Equity", "asset_type": "equity_type2", "value": 300000.0, "duration": 0.0, "cqs_rating": 3, "currency": "USD"},
    {"name": "BTP Governativi 10Y", "asset_type": "bond", "value": 900000.0, "duration": 7.5, "cqs_rating": 3, "currency": "EUR"},
    {"name": "Corporate Bond Investment Grade", "asset_type": "bond", "value": 500000.0, "duration": 4.2, "cqs_rating": 2, "currency": "EUR"},
    {"name": "Immobili a Reddito", "asset_type": "property", "value": 400000.0, "duration": 0.0, "cqs_rating": 2, "currency": "EUR"},
    {"name": "Liquidita & Depositi Bancari", "asset_type": "cash", "value": 200000.0, "duration": 0.25, "cqs_rating": 2, "currency": "EUR"},
]

s2_report = compute_solvency2_standard_formula(
    portfolio_assets=sample_s2_assets,
    eligible_own_funds=s2_eof,
    technical_provisions=s2_tp,
    symmetric_equity_adjustment=s2_symm,
)

s2k1, s2k2, s2k3, s2k4 = st.columns(4)
with s2k1:
    metric_card("Eligible Own Funds", fmt_eur(s2_report["eligible_own_funds"]), delta="Tier 1 + Tier 2", delta_color="normal")
with s2k2:
    metric_card("Requisito SCR Totale", fmt_eur(s2_report["scr_total"]), delta=f"BSCR: {fmt_eur(s2_report['bscr'])}", delta_color="inverse")
with s2k3:
    metric_card("Beneficio Diversificazione", fmt_eur(s2_report["market_diversification_benefit"]), delta="Aggregazione EIOPA", delta_color="normal")
with s2k4:
    metric_card("Solvency Ratio", f"{s2_report['solvency_ratio_pct']:.1f}%", delta=s2_report["solvency_health"], delta_color="normal" if s2_report["solvency_ratio_pct"] >= 160 else "inverse")

st.markdown("##### 📋 Prospetto Regolamentare QRT S.25.01.21 (SCR Standard Formula)")
st.dataframe(pd.DataFrame(list(s2_report["qrt_s25_01"].items()), columns=["Voce Regolamentare", "Valore"]), use_container_width=True, hide_index=True)

# ── V9.13.0: FRTB (BASEL IV / BCBS 365) STANDARDIZED APPROACH ──────
st.markdown("---")
st.markdown("#### 🏛️ FRTB Standardized Approach Capital Engine (BCBS 365 / Basel IV)")
st.caption("Sensitivities-Based Method (SBM) Delta/Vega/Curvature, Default Risk Charge (DRC) e Residual Risk Add-on (RRAO).")

from core.frtb_engine import compute_frtb_capital_charges

with st.expander("⚙️ Parametri Portafoglio di Trading & Sensibilità FRTB", expanded=False):
    frtb_c1, frtb_c2 = st.columns(2)
    with frtb_c1:
        frtb_port_val = st.number_input("Valore Totale Portafoglio di Trading (€):", min_value=1_000_000.0, value=50_000_000.0, step=5_000_000.0, key="frtb_port_val_in")
    with frtb_c2:
        frtb_corr_scenario = st.selectbox("Scenario di Correlazione BCBS:", ["MEDIUM", "HIGH", "LOW"], index=0, key="frtb_scen_sel")

frtb_res = compute_frtb_capital_charges(
    correlation_scenario=frtb_corr_scenario,
    total_portfolio_value=frtb_port_val,
)

fk1, fk2, fk3, fk4 = st.columns(4)
with fk1:
    metric_card("Requisito FRTB Totale", fmt_eur(frtb_res["total_frtb_capital_charge_eur"]), delta=f"{frtb_res['capital_ratio_pct']:.2f}% Portafoglio", delta_color="inverse")
with fk2:
    metric_card("SBM Total Charge", fmt_eur(frtb_res["sbm_total_charge_eur"]), delta=f"Delta: {fmt_eur(frtb_res['sbm_delta_charge_eur'])}", delta_color="normal")
with fk3:
    metric_card("Default Risk Charge (DRC)", fmt_eur(frtb_res["drc_total_charge_eur"]), delta="JTD & Rating Weights", delta_color="normal")
with fk4:
    metric_card("Residual Risk (RRAO)", fmt_eur(frtb_res["rrao_total_charge_eur"]), delta="Prodotti Esotici", delta_color="normal")

st.markdown("##### 📊 Decomposizione SBM per Classe di Rischio e Sensibilità")
st.dataframe(pd.DataFrame(frtb_res["sbm_breakdown_by_risk_class"]), use_container_width=True, hide_index=True)


# ── V9.13.0: NGFS CLIMATE TRANSITION & PHYSICAL STRESS ENGINE ───────
st.markdown("---")
st.markdown("#### 🌱 NGFS Phase IV Climate Transition & Physical Risk Stress Engine")
st.caption("Stress test climatico su scenari NGFS (Orderly Net Zero 2050, Disorderly Delayed Transition, Hot House World) con WACI Scope 1-2-3.")

from core.climate_stress_engine import compute_ngfs_climate_stress

cl_c1, cl_c2 = st.columns(2)
with cl_c1:
    ngfs_scenario_sel = st.selectbox("Scenario NGFS Phase IV:", ["Net Zero 2050 (Orderly)", "Delayed Transition (Disorderly)", "Current Policies (Hot House World)"], key="ngfs_scen_sel")
with cl_c2:
    ngfs_target_yr = st.select_slider("Orizzonte Temporale di Stress:", options=[2030, 2035, 2040, 2050], value=2030, key="ngfs_yr_sel")

cl_res = compute_ngfs_climate_stress(scenario_name=ngfs_scenario_sel, target_year=ngfs_target_yr)

ck1, ck2, ck3, ck4 = st.columns(4)
with ck1:
    metric_card("Perdita Climatica Totale", f"{cl_res['portfolio_loss_pct']:.2f}%", delta=fmt_eur(cl_res["portfolio_loss_eur"]), delta_color="inverse")
with ck2:
    metric_card("Rischio di Transizione", fmt_eur(cl_res["transition_risk_loss_eur"]), delta=f"Prezzo CO₂: ${cl_res['carbon_price_usd_ton']}/t", delta_color="inverse")
with ck3:
    metric_card("Rischio Fisico (Danni)", fmt_eur(cl_res["physical_risk_loss_eur"]), delta=f"Riscaldamento: +{cl_res['temperature_anomaly_celsius']}°C", delta_color="inverse")
with ck4:
    metric_card("Intensità WACI Portafoglio", f"{cl_res['portfolio_waci_tco2e_per_meur']:.1f}", delta="tCO₂e / M€ Ricavi", delta_color="normal")

st.markdown("##### 🏢 Impatto Climatico Dettagliato per Società & Asset")
st.dataframe(pd.DataFrame(cl_res["holdings_breakdown"]), use_container_width=True, hide_index=True)


# ── V9.13.0: INTERACTIVE MACRO WAR ROOM & CORRELATION BREAKDOWN ───
st.markdown("---")
st.markdown("#### 🎯 Interactive Macro War Room & Correlation Breakdown Stress Engine")
st.caption("Simulatore macro a leve multiple (Tassi, Twist, Inflazione, Petrolio, Spread) con crollo sistemico delle correlazioni verso equicorrelazione.")

from core.macro_war_room import compute_macro_war_room_stress

with st.expander("🎛️ Pannello di Controllo Macro Shock & Leva di Correlazione", expanded=True):
    mw1, mw2, mw3, mw4 = st.columns(4)
    with mw1:
        rates_bps = st.slider("Parallel Rates Shock (bps):", min_value=-300, max_value=400, value=150, step=25, key="mw_rates_bps")
        twist_bps = st.slider("Curve Twist Inversion (bps):", min_value=-150, max_value=150, value=-50, step=10, key="mw_twist_bps")
    with mw2:
        cpi_shock = st.slider("Inflation / CPI Surge (%):", min_value=-2.0, max_value=10.0, value=3.5, step=0.5, key="mw_cpi_shock")
        oil_shock = st.slider("Oil / Energy Spike (%):", min_value=-50, max_value=100, value=40, step=5, key="mw_oil_shock")
    with mw3:
        eq_crash = st.slider("Equity Drawdown (%):", min_value=-60, max_value=20, value=-20, step=5, key="mw_eq_crash")
        cs_spread = st.slider("Credit Spread OAS Widening (bps):", min_value=-50, max_value=600, value=250, step=25, key="mw_cs_spread")
    with mw4:
        lam_corr = st.slider("Correlation Breakdown (λ):", min_value=0.0, max_value=1.0, value=0.60, step=0.05, key="mw_lam_corr", help="0 = correlazione storica, 1 = panic equicorrelation matrix (0.85)")
        vol_surge = st.slider("Vol Surge Multiplier:", min_value=1.0, max_value=3.0, value=1.50, step=0.1, key="mw_vol_surge")

mw_params = {
    "scenario_name": "Stagflationary Energy Shock & Yield Surge",
    "parallel_rates_bps": rates_bps,
    "slope_twist_bps": twist_bps,
    "inflation_shock_pct": cpi_shock,
    "oil_shock_pct": oil_shock,
    "equity_shock_pct": eq_crash,
    "credit_spread_widening_bps": cs_spread,
    "correlation_breakdown_lambda": lam_corr,
    "vol_surge_factor": vol_surge,
}

mw_res = compute_macro_war_room_stress(scenario_params=mw_params)

mk1, mk2, mk3, mk4 = st.columns(4)
with mk1:
    metric_card("PnL Portafoglio Macro", fmt_eur(mw_res["total_pnl_eur"]), delta=f"{mw_res['total_pnl_pct']:.2f}%", delta_color="inverse" if mw_res["total_pnl_eur"] < 0 else "normal")
with mk2:
    metric_card("Volatilità Stressata", f"{mw_res['stressed_vol_pct']:.2f}%", delta=f"Base: {mw_res['base_vol_pct']:.2f}%", delta_color="inverse")
with mk3:
    metric_card("Perdita di Diversificazione", f"+{mw_res['diversification_loss_pct']:.2f}%", delta="Impatto Correlazione λ", delta_color="inverse")
with mk4:
    metric_card("Drenaggio Liquidità / Margin Call", fmt_eur(mw_res["liquidity_margin_drain_eur"]), delta="Cuscino di Garanzia", delta_color="inverse")

st.markdown("##### 📋 Decomposizione PnL per Asset e Fattore Macro")
st.dataframe(pd.DataFrame(mw_res["assets_breakdown"]), use_container_width=True, hide_index=True)

st.markdown("##### 🌐 Matrice di Correlazione Sotto Stress Sistemico ($R_{\text{stressed}}$)")
st.dataframe(pd.DataFrame(mw_res["stressed_correlation_matrix"]), use_container_width=True)


# ── V9.14.0: BILATERAL XVA & COUNTERPARTY RISK ENGINE ─────────────────
st.markdown("---")
st.markdown("#### 🛡️ Bilateral XVA & Counterparty Credit Risk Engine (BCBS / ISDA SIMM)")
st.caption("Valutazione CVA, DVA, FVA, MVA, KVA con accordi di compensazione CSA e simulazione profili di esposizione (EE, PFE 95%/99%, ENE).")

from core.xva_engine import compute_xva_metrics

with st.expander("⚙️ Parametri Contratto CSA Netting Set & Portafoglio Derivati", expanded=False):
    xva_c1, xva_c2, xva_c3 = st.columns(3)
    with xva_c1:
        xva_port_mtm = st.number_input("MTM Lordo Portafoglio Derivati (€):", min_value=100_000.0, value=2_500_000.0, step=250_000.0, key="xva_mtm_in")
        xva_thresh = st.number_input("Soglia CSA Bilaterale (€):", min_value=0.0, value=250_000.0, step=50_000.0, key="xva_thresh_in")
    with xva_c2:
        xva_cpty_spread = st.number_input("Credit Spread Controparte (bps):", min_value=10.0, max_value=1000.0, value=120.0, step=10.0, key="xva_cpty_sp")
        xva_own_spread = st.number_input("Credit Spread Proprio (DVA bps):", min_value=10.0, max_value=500.0, value=65.0, step=5.0, key="xva_own_sp")
    with xva_c3:
        xva_mpor = st.slider("Margin Period of Risk (MPOR Giorni):", min_value=5, max_value=30, value=10, step=1, key="xva_mpor_in")
        xva_mta = st.number_input("Minimum Transfer Amount (€):", min_value=0.0, value=50_000.0, step=10_000.0, key="xva_mta_in")

custom_csa = {
    "threshold": xva_thresh,
    "mta": xva_mta,
    "mpor_days": xva_mpor,
}
custom_mkt = {
    "counterparty_cds_spread_bps": xva_cpty_spread,
    "own_cds_spread_bps": xva_own_spread,
}

xva_res = compute_xva_metrics(csa_params=custom_csa, market_params=custom_mkt)

xk1, xk2, xk3, xk4 = st.columns(4)
with xk1:
    metric_card("Credit Valuation Adj (CVA)", fmt_eur(xva_res["cva_eur"]), delta="Rischio Controparte", delta_color="inverse")
with xk2:
    metric_card("Debit Valuation Adj (DVA)", fmt_eur(xva_res["dva_eur"]), delta="Rischio Proprio (+)", delta_color="normal")
with xk3:
    metric_card("Funding Valuation Adj (FVA)", fmt_eur(xva_res["fva_eur"]), delta=f"MVA: {fmt_eur(xva_res['mva_eur'])}", delta_color="inverse")
with xk4:
    metric_card("Total Net XVA", fmt_eur(xva_res["total_xva_eur"]), delta=f"Peak PFE 99%: {fmt_eur(xva_res['peak_pfe_99_eur'])}", delta_color="inverse" if xva_res["total_xva_eur"] < 0 else "normal")

st.markdown("##### 📈 Profilo di Esposizione Creditizia Futura (EE, PFE 95%, PFE 99%, ENE)")
exp_df = pd.DataFrame(xva_res["exposure_profile"])

fig_xva = go.Figure()
fig_xva.add_trace(go.Scatter(x=exp_df["tenor_years"], y=exp_df["pfe_99_eur"], name="PFE 99% (Worst-Case)", line=dict(color="#f43f5e", width=2.5)))
fig_xva.add_trace(go.Scatter(x=exp_df["tenor_years"], y=exp_df["pfe_95_eur"], name="PFE 95%", line=dict(color="#fb923c", width=2)))
fig_xva.add_trace(go.Scatter(x=exp_df["tenor_years"], y=exp_df["expected_exposure_eur"], name="Expected Exposure (EE)", line=dict(color="#38bdf8", width=2.5)))
fig_xva.add_trace(go.Scatter(x=exp_df["tenor_years"], y=exp_df["expected_negative_exposure_eur"], name="Expected Neg. Exposure (ENE)", line=dict(color="#a855f7", dash="dot")))

fig_xva.update_layout(
    title="Simulazione Monte Carlo dei Profili di Esposizione con Collaterale CSA",
    xaxis_title="Orizzonte Temporale (Anni)",
    yaxis_title="Esposizione Potenziale (€)",
    height=420,
    margin=dict(l=10, r=10, b=10, t=40),
)
st.plotly_chart(fig_xva, use_container_width=True)


# ── V9.14.0: BASEL III LIQUIDITY STANDARDS (LCR & NSFR) ───────────────
st.markdown("---")
st.markdown("#### 💧 Basel III Liquidity Standards & Dynamic Cash Ladder (BCBS 238)")
st.caption("Requisito di copertura della liquidità a 30 giorni (LCR ≥ 100%), Net Stable Funding Ratio (NSFR ≥ 100%) e proiezioni di sopravvivenza.")

from core.basel_liquidity_engine import compute_basel_liquidity_ratios

with st.expander("⚙️ Parametri Attivi Liquidi HQLA & Run-off di Cassa", expanded=False):
    b_c1, b_c2 = st.columns(2)
    with b_c1:
        hqla_l1_val = st.number_input("HQLA Livello 1 - Riserve & Titoli Sovrani 0% RW (€):", min_value=5_000_000.0, value=70_000_000.0, step=5_000_000.0, key="hqla_l1_in")
        hqla_l2a_val = st.number_input("HQLA Livello 2A - Corp Bonds AAA/AA (€):", min_value=0.0, value=30_000_000.0, step=2_000_000.0, key="hqla_l2a_in")
    with b_c2:
        hqla_l2b_val = st.number_input("HQLA Livello 2B - Azioni & Titoli BBB (€):", min_value=0.0, value=15_000_000.0, step=1_000_000.0, key="hqla_l2b_in")
        outflow_stress_mult = st.slider("Stress Multiplier sui Deflussi a 30gg:", min_value=1.0, max_value=2.0, value=1.25, step=0.05, key="liq_mult_in")

custom_hqla = [
    {"asset_id": "L1_SOV", "asset_type": "sovereign_l1", "level": "1", "market_value": hqla_l1_val, "haircut": 0.0},
    {"asset_id": "L2A_CORP", "asset_type": "corp_bond_l2a", "level": "2A", "market_value": hqla_l2a_val, "haircut": 0.15},
    {"asset_id": "L2B_EQ", "asset_type": "qualifying_equities", "level": "2B", "market_value": hqla_l2b_val, "haircut": 0.50},
]

basel_res = compute_basel_liquidity_ratios(hqla_data=custom_hqla)

bk1, bk2, bk3, bk4 = st.columns(4)
with bk1:
    lcr_stat = "CONFORME ✅" if basel_res["lcr_compliant"] else "DEFICIT ⚠️"
    metric_card("Liquidity Coverage Ratio (LCR)", f"{basel_res['lcr_ratio_pct']:.1f}%", delta=f"{lcr_stat} (Min 100%)", delta_color="normal" if basel_res["lcr_compliant"] else "inverse")
with bk2:
    metric_card("HQLA Totale Idoneo", fmt_eur(basel_res["total_hqla_eligible"]), delta=f"Cap Deduc: {fmt_eur(basel_res['cap_deduction'])}", delta_color="normal")
with bk3:
    nsfr_stat = "CONFORME ✅" if basel_res["nsfr_compliant"] else "DEFICIT ⚠️"
    metric_card("Net Stable Funding Ratio (NSFR)", f"{basel_res['nsfr_ratio_pct']:.1f}%", delta=f"{nsfr_stat} (Min 100%)", delta_color="normal" if basel_res["nsfr_compliant"] else "inverse")
with bk4:
    metric_card("Orizzonte di Sopravvivenza", f"{basel_res['survival_horizon_days']} Giorni", delta="Stress Sistemico", delta_color="normal" if basel_res["survival_horizon_days"] > 30 else "inverse")

st.markdown("##### 🪜 Dynamic Cash Flow Stress Ladder & Buffer di Liquidità")
ladder_df = pd.DataFrame(basel_res["stress_ladder"])

fig_ladder = go.Figure()
fig_ladder.add_trace(go.Bar(x=ladder_df["horizon_days"].astype(str) + "d", y=ladder_df["projected_liquidity_buffer"], name="Buffer Netto Residuo (€)", marker_color="#0ea5e9"))
fig_ladder.update_layout(
    title="Evoluzione del Cuscinetto di Liquidità Proiettato per Orizzonte Temporale",
    xaxis_title="Orizzonte di Stress (Giorni)",
    yaxis_title="Buffer Disponibile (€)",
    height=380,
    margin=dict(l=10, r=10, b=10, t=40),
)
st.plotly_chart(fig_ladder, use_container_width=True)

st.markdown("##### 📋 Dettaglio HQLA per Livello e Haircut Regolamentare")
st.dataframe(pd.DataFrame(basel_res["hqla_breakdown"]), use_container_width=True, hide_index=True)


# ============================================================================
# v9.16.0: TELEMETRY RIBBON, WORKSPACE SWITCHER & SCENARIO DELTA COMPARATOR
# ============================================================================
from core.ux_institutional_hub import (
    render_executive_traffic_light_radar,
    render_institutional_telemetry_ribbon,
    render_scenario_delta_comparator,
    render_segmented_workspace_switcher,
    style_institutional_chart,
)

render_institutional_telemetry_ribbon(page_badge="REGULATORY STRESS TESTING & CAPITAL LAB")
render_executive_traffic_light_radar(key_prefix="stress_page_cro_radar")

active_stress_ws = render_segmented_workspace_switcher(
    workspace_key="stress_v916_domain",
    label="🧭 Filtra Workspace Regolamentare (Eliminazione Scroll Verticale):",
    options=[
        "🌐 Tutti i Laboratori Regolamentari",
        "🤝 Credito & Controparte (CreditMetrics & Vasicek IRB)",
        "🏛️ Capitale Prudenziale 9Q (Fed CCAR / EBA CET1 Trajectory)",
    ],
)

# ============================================================================
# v9.15.0: CREDITMETRICS PORTFOLIO CREDIT RISK & FED CCAR / EBA STRESS ENGINE
# ============================================================================
st.divider()
st.markdown("#### 🏦 CreditMetrics Rating Migration & Basel III IRB Vasicek Portfolio Credit Risk")
st.caption("Modello multi-debitore con matrice di transizione S&P a 8 stati (AAA..D), correlazione latente degli asset di Vasicek (2002), capitale regolamentare IRB (K_IRB e RWA), Credit VaR 99.9% e Incremental Risk Charge (IRC).")

from core.ccar_stress_engine import compute_ccar_capital_stress
from core.credit_portfolio_engine import compute_credit_portfolio_risk

cp_c1, cp_c2 = st.columns([1, 3])
with cp_c1:
    cp_sims = st.select_slider("Simulazioni Monte Carlo CreditMetrics:", options=[2000, 5000, 8000, 12000], value=5000, key="cp_sims_slider")
with cp_c2:
    st.info("📌 Il portafoglio istituzionale predefinito include esposizioni Corporate e Sovrane distribuite sui rating S&P da AAA a B, rivalutate mark-to-market sugli spread creditizi ad 1 anno.")

cp_res = compute_credit_portfolio_risk(n_simulations=int(cp_sims))
ck1, ck2, ck3, ck4 = st.columns(4)
with ck1:
    metric_card("Expected Loss (EL Basilea IRB)", fmt_eur(float(cp_res["expected_loss_eur"])), delta=f"EAD: {fmt_eur(float(cp_res['total_ead_eur']))}", delta_color="inverse")
with ck2:
    metric_card("Capitale Regolamentare K_IRB", fmt_eur(float(cp_res["vasicek_irb_capital_999_eur"])), delta=f"RWA: {fmt_eur(float(cp_res['vasicek_rwa_eur']))}", delta_color="normal")
with ck3:
    metric_card("Credit VaR 99.9% (1Y Migration)", fmt_eur(float(cp_res["creditmetrics_var_999_eur"])), delta=f"VaR 99%: {fmt_eur(float(cp_res['creditmetrics_var_99_eur']))}", delta_color="inverse")
with ck4:
    metric_card("Incremental Risk Charge (IRC)", fmt_eur(float(cp_res["incremental_risk_charge_eur"])), delta=f"ES 99.9%: {fmt_eur(float(cp_res['creditmetrics_es_999_eur']))}", delta_color="inverse")

st.markdown("##### 📋 Decomposizione per Controparte: PD, Correlazione Vasicek ρ, RWA e Contributo Euler al Rischio")
st.dataframe(pd.DataFrame(cp_res["obligor_contributions"]), use_container_width=True, hide_index=True)

st.divider()
st.markdown("#### 🏛️ Fed CCAR / EBA 9-Quarter Supervisory Capital Stress & Traiettoria CET1")
st.caption("Proiezione prudenziale su 9 trimestri (Q1..Q9) negli scenari Supervisory Baseline, Adverse e Severely Adverse: Pre-Provision Net Revenue (PPNR), transizione crediti deteriorati IFRS 9 / CECL (Stage 1/2/3), inflazione RWA e Stress Capital Buffer (SCB).")

cc_c1, cc_c2, cc_c3, cc_c4 = st.columns(4)
with cc_c1:
    cc_cet1 = st.number_input("Capitale CET1 Iniziale (€ Milioni):", min_value=1_000.0, value=14_200.0, step=500.0, key="cc_cet1_in")
with cc_c2:
    cc_rwa = st.number_input("RWA Iniziali (€ Milioni):", min_value=10_000.0, value=100_000.0, step=5_000.0, key="cc_rwa_in")
with cc_c3:
    cc_loans = st.number_input("Portafoglio Crediti Totale (€ Milioni):", min_value=10_000.0, value=145_000.0, step=5_000.0, key="cc_loans_in")
with cc_c4:
    cc_ppnr = st.number_input("PPNR Trimestrale Base (€ Milioni):", min_value=100.0, value=920.0, step=50.0, key="cc_ppnr_in")

ccar_res = compute_ccar_capital_stress(
    initial_cet1_capital_eur_m=cc_cet1,
    initial_rwa_eur_m=cc_rwa,
    total_loan_book_eur_m=cc_loans,
    quarterly_ppnr_baseline_eur_m=cc_ppnr,
)

sev_scen = ccar_res["scenarios"]["severely_adverse"]
adv_scen = ccar_res["scenarios"]["adverse"]
base_scen = ccar_res["scenarios"]["baseline"]
mda_hurdle = ccar_res["regulatory_hurdles"]["overall_capital_requirement_mda_pct"]

cck1, cck2, cck3, cck4 = st.columns(4)
with cck1:
    metric_card("CET1 Ratio Iniziale", f"{ccar_res['initial_cet1_ratio_pct']:.2f}%", delta=f"Soglia OCR/MDA: {mda_hurdle:.2f}%", delta_color="normal")
with cck2:
    metric_card("Min CET1 (Severely Adverse)", f"{sev_scen['minimum_stressed_cet1_ratio_pct']:.2f}%", delta=f"Trough in {sev_scen['trough_quarter']} (-{sev_scen['max_cet1_drawdown_bps']:.0f} bps)", delta_color="normal" if not sev_scen["mda_restriction_triggered"] else "inverse")
with cck3:
    metric_card("Perdite Credito Cumulate 9Q", f"€ {sev_scen['cumulative_9q_credit_losses_eur_m']:,.0f} M", delta=f"Loss Rate: {sev_scen['cumulative_9q_loss_rate_pct']:.2f}%", delta_color="inverse")
with cck4:
    metric_card("Stress Capital Buffer (SCB)", f"{ccar_res['required_stress_capital_buffer_scb_pct']:.2f}%", delta=ccar_res["supervisory_assessment_status"].split(" - ")[0], delta_color="normal" if "PASS" in ccar_res["supervisory_assessment_status"] else "inverse")

df_base = pd.DataFrame(base_scen["trajectory"])
df_adv = pd.DataFrame(adv_scen["trajectory"])
df_sev = pd.DataFrame(sev_scen["trajectory"])

fig_ccar = go.Figure()
fig_ccar.add_trace(go.Scatter(x=df_base["quarter"], y=df_base["cet1_ratio_pct"], mode="lines+markers", name="Supervisory Baseline (%)", line=dict(color="#10b981", width=3)))
fig_ccar.add_trace(go.Scatter(x=df_adv["quarter"], y=df_adv["cet1_ratio_pct"], mode="lines+markers", name="Supervisory Adverse (%)", line=dict(color="#f59e0b", width=3)))
fig_ccar.add_trace(go.Scatter(x=df_sev["quarter"], y=df_sev["cet1_ratio_pct"], mode="lines+markers", name="Fed CCAR / EBA Severely Adverse (%)", line=dict(color="#ef4444", width=3.5)))
fig_ccar.add_hline(y=mda_hurdle, line_dash="dash", line_color="#fbbf24", annotation_text=f"OCR / MDA Trigger ({mda_hurdle:.1f}%)")
fig_ccar.add_hline(y=6.0, line_dash="dot", line_color="#dc2626", annotation_text="Pillar 1 + P2R Min (6.0%)")
fig_ccar.update_layout(
    title="Traiettoria Regolamentare 9-Trimestri del CET1 Ratio (%) sotto Stress EBA / Fed CCAR",
    xaxis_title="Orizzonte Trimestrale di Proiezione",
    yaxis_title="CET1 Ratio (%)",
    height=420,
    margin=dict(l=10, r=10, b=10, t=40),
)
style_institutional_chart(fig_ccar, title="Traiettoria Regolamentare 9-Trimestri del CET1 Ratio (%) sotto Stress EBA / Fed CCAR", height=420)
st.plotly_chart(fig_ccar, use_container_width=True)
render_scenario_delta_comparator(
    scenario_key="ccar_capital_stress",
    scenario_title="Fed CCAR / EBA 9Q Capital Stress",
    current_metrics={
        "CET1 Iniziale (%)": float(ccar_res["initial_cet1_ratio_pct"]),
        "Min CET1 Severely Adverse (%)": float(sev_scen["minimum_stressed_cet1_ratio_pct"]),
        "Perdite Credito 9Q (€M)": float(sev_scen["cumulative_9q_credit_losses_eur_m"]),
        "Stress Capital Buffer SCB (%)": float(ccar_res["required_stress_capital_buffer_scb_pct"]),
    },
    higher_is_better_map={
        "CET1 Iniziale (%)": True,
        "Min CET1 Severely Adverse (%)": True,
        "Perdite Credito 9Q (€M)": False,
        "Stress Capital Buffer SCB (%)": False,
    },
)
st.dataframe(df_sev, use_container_width=True, hide_index=True)
