import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import importlib

import core.ui_utils
importlib.reload(core.ui_utils)

try:
    from core.ui_utils import fmt_eur_it
except ImportError:
    def fmt_eur_it(v, decimals: int = 0) -> str:
        if v is None:
            return "N/A"
        try:
            val = float(v)
        except (ValueError, TypeError):
            return "N/A"
        if decimals == 0:
            return f"€ {val:,.0f}".replace(",", ".")
        formatted = f"{val:,.{decimals}f}"
        int_p, dec_p = formatted.split(".")
        return f"€ {int_p.replace(',', '.')},{dec_p}"

from core.ui_utils import inject_custom_css, metric_card, fmt_pct, glossary_modal, section, apply_plotly_theme, render_command_bar, render_segmented_tabs, render_info_modal, render_volatility_smile_modal, render_fama_french_modal
from core.hrp_optimizer import compute_hrp_portfolio
from core.options_hedging import black_scholes_pricing, compute_portfolio_delta_hedge, compute_covered_call_yield_enhancement
from core.volatility_surface import build_volatility_surface, fit_volatility_smile
from core.advanced_quant import compute_tail_copula_matrix, compute_kelly_criterion_sizing, compute_equal_risk_contribution_portfolio
from core.fixed_income import (
    compute_bond_cash_flows,
    compute_bond_price_from_ytm,
    compute_bond_ytm,
    compute_bond_analytics,
    compute_z_spread,
    compute_cds_implied_default_probability,
    INSTITUTIONAL_BOND_PRESETS
)
from core.yield_curve import (
    evaluate_nelson_siegel_svensson_curve,
    compute_key_rate_durations,
    get_institutional_yield_curve
)

st.set_page_config(page_title="Modelli Quantitativi | ARGUS", page_icon="🔬", layout="wide")
inject_custom_css()

# Cache bust
from core.sidebar import render_sidebar
render_sidebar()
import core.risk_engine
import core.options_hedging
import core.volatility_surface
import core.factor_library
importlib.reload(core.risk_engine)
importlib.reload(core.options_hedging)
importlib.reload(core.volatility_surface)
importlib.reload(core.factor_library)
from core.ui_utils import ensure_risk_bundle_loaded, render_sandbox_banner

results, has_real = ensure_risk_bundle_loaded()
has_portfolio = results is not None and isinstance(results, dict) and bool(results.get("positions") is not None and not results.get("positions").empty)
m = results.get("metrics", {})
pos = results.get("positions", pd.DataFrame())
# Filtro rigoroso: solo asset ATTUALMENTE APERTI in portafoglio (escludi posizioni liquidate e cambi FX)
if isinstance(pos, pd.DataFrame) and not pos.empty and "ticker" in pos.columns:
    mask_open = (pos["qty_net"] > 1e-6) if "qty_net" in pos.columns else pd.Series(True, index=pos.index)
    if "current_value" in pos.columns:
        mask_open = mask_open & (pos["current_value"] > 0)
    active_tickers_set = set([t for t in pos[mask_open]["ticker"].dropna().unique() if not str(t).endswith("=X")])
else:
    active_tickers_set = set()

ai = m.get("ai_insights", {})
mc = ai.get("montecarlo", {})
raw_clusters = ai.get("asset_clusters", [])
# Filtra clusters per soli asset aperti ed elimina cambi FX
if raw_clusters and active_tickers_set:
    clusters = [c for c in raw_clusters if (c.get("ticker") or c.get("index")) in active_tickers_set and not str(c.get("ticker", c.get("index"))).endswith("=X")]
elif raw_clusters and not active_tickers_set:
    clusters = [c for c in raw_clusters if not str(c.get("ticker", c.get("index"))).endswith("=X")]
else:
    clusters = []

opt = results.get("optimization", {})

render_sandbox_banner(page_key="p3")

col_head1, col_head2 = st.columns([3.0, 1.3])
with col_head1:
    st.title("🔬 Modelli Quantitativi & Frontiera di Portafoglio")
    if "run_id" in st.session_state:
        st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Frontiera Markowitz/Ledoit-Wolf, Equal Risk Contribution, Tail Copula, Kelly Sizing, Monte Carlo e Black-Scholes.")
    elif results.get("is_sandbox"):
        st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")

with col_head2:
    st.markdown('<div style="display: flex; justify-content: flex-end; margin-top: 24px;">', unsafe_allow_html=True)
    glossary_modal("📚 Glossario Istituzionale dei Modelli Quantitativi", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Suite di Ingegneria Finanziaria ARGUS</div>
  <div>Una collezione integrata di modelli econometrici, stocastici e di machine learning per l'ottimizzazione dell'asset allocation, la simulazione del rischio di coda e la copertura dinamica.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Modelli Quantitativi di Frontiera</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Markowitz & Ledoit-Wolf:</b> Frontiera efficiente con covarianza a shrinkage antirumore.<br>
    • <b>Equal Risk Contribution (ERC):</b> Parità pura di rischio dove ogni asset contribuisce 1/N alla volatilità.<br>
    • <b>Hierarchical Risk Parity (HRP):</b> Clustering ad albero (López de Prado) senza matrice inversa.<br>
    • <b>Tail Copula Asimmetriche:</b> Dipendenza di coda (Clayton/Gumbel) per quantificare il rischio di crash congiunto.<br>
    • <b>Kelly Criterion Sizing:</b> Dimensionamento matematico per la massima crescita del capitale.<br>
    • <b>Monte Carlo Multivariato:</b> Decomposizione Cholesky & code Student-t su 3.000 percorsi.<br>
    • <b>Merton Jump-Diffusion:</b> Processo a salti Poissoniani per shock estremi di mercato.<br>
    • <b>Black-Scholes Delta-Hedging:</b> Neutralizzazione del Beta con opzioni Put e Covered Call.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>I moduli <code>core/risk_engine.py</code> e <code>core/financial_analysis.py</code> eseguono simulazioni stocastiche vettorializzate ad alte prestazioni.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come navigare la sezione</div>
  <div>Utilizza le schede superiori per passare dall'ottimizzazione di allocazione (Tab 1), alle proiezioni stocastiche (Tab 2), alle strategie di copertura attiva (Tab 3), all'attribuzione Brinson/Fattori (Tab 4) e al Fixed Income (Tab 5).</div>
</div>

</div>
""", button_label="📚 Guida Quant")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ CON LAZY LOADING ─────────
active_quant_tab = render_segmented_tabs([
    "📊 Markowitz & Rebalancing",
    "🧬 Tail Copula & Kelly",
    "🎲 Monte Carlo & Merton",
    "🛡️ Hedging & Opzioni",
    "🎯 Attribuzione & Fattori",
    "🏛️ Fixed Income & Z-Spread"
], key="quant_active_tab")

# ── TAB 1: MARKOWITZ & LEDOIT-WOLF ────────────────────────────
if active_quant_tab == "📊 Markowitz & Rebalancing":
    if not has_portfolio:
        st.warning("⚠️ Carica prima un portafoglio nella Control Room per calcolare la Frontiera Efficiente di Markowitz.")
    elif opt and opt.get("tickers"):
        col_head_opt1, col_head_opt2 = st.columns([3.0, 1.3])
        with col_head_opt1:
            st.markdown("#### Ottimizzazione di Portafoglio (Markowitz Efficient Frontier)")
            st.caption(f"Confronta il tuo portafoglio attuale con le allocazioni ottimali (Stima Covarianza: **{opt.get('cov_type', 'Ledoit-Wolf Shrinkage')}**)")
        with col_head_opt2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida all'Ottimizzazione Ledoit-Wolf & Ribilanciamento", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è la Frontiera Efficiente di Markowitz</div>
  <div>Il luogo geometrico dei portafogli ottimali che massimizzano il rendimento atteso per ogni livello di volatilità (o minimizzano il rischio per un dato rendimento target).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Matrice di Covarianza Ledoit-Wolf Shrinkage</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12.5px; text-align: center;">
    <b>&Sigma;<sub>LW</sub></b> = &delta; &middot; <b>F</b> + (1 &minus; &delta;) &middot; <b>S</b>
  </div>
  <div>dove <i>S</i> è la covarianza campionaria, <i>F</i> è la matrice target strutturata a singolo fattore e <i>&delta;</i> è il parametro ottimale di contrazione (shrinkage) che minimizza l'errore quadratico medio.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Risolve l'instabilità dell'ottimizzazione classica (l'effetto "error-maximizer"), producendo pesi di ribilanciamento concreti ed eseguibili senza pesi estremi.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS risolve l'ottimizzazione quadratica vincolata (Long-Only, sum(w)=1) calcolando i due portafogli cardine: <b>Max Sharpe Ratio</b> e <b>Minima Varianza</b>.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • 🟢 <b>Stella Verde:</b> Il tuo portafoglio attuale.<br>
    • 🟠 <b>Stella Arancione:</b> Portafoglio a Massimo Sharpe Ratio (massima efficienza rendimento/rischio).<br>
    • 🔵 <b>Stella Azzurra:</b> Portafoglio a Minima Volatilità (massima stabilità del capitale).
  </div>
</div>
""", button_label="💡 Guida Markowitz")
        
        cand_handoff = st.session_state.get("screener_candidate_to_optimize")
        if cand_handoff:
            cand_tk = cand_handoff.get("ticker", "")
            cand_w = cand_handoff.get("weight_pct", 5.0)
            col_cand1, col_cand2 = st.columns([3.5, 1])
            with col_cand1:
                st.info(f"🧪 **Integrazione Screener Attiva**: Ricevuto asset candidato **{cand_tk}** (Allocazione Ipotetica: **{cand_w}%**). Puoi confrontare la frontiera con il portafoglio attuale o rimuovere la simulazione.")
            with col_cand2:
                if st.button("❌ Rimuovi Simulazione", use_container_width=True):
                    del st.session_state["screener_candidate_to_optimize"]
                    st.rerun()

        raw_frontier = opt.get("frontier", {})
        frontier = pd.DataFrame(raw_frontier)
        if not frontier.empty:
            v_col = "volatility" if "volatility" in frontier.columns else ("risk" if "risk" in frontier.columns else frontier.columns[0])
            r_col = "return" if "return" in frontier.columns else (frontier.columns[1] if len(frontier.columns) > 1 else frontier.columns[0])
            
            frontier["vol_pct"] = frontier[v_col] * 100.0
            frontier["ret_pct"] = frontier[r_col] * 100.0
            
            fig_f = px.scatter(
                frontier, x="vol_pct", y="ret_pct",
                labels={"vol_pct": "Volatilità Annua %", "ret_pct": "Rendimento Atteso %"},
                template="plotly_dark", height=490
            )
            # Cloud di punti Monte Carlo traslucida per non nascondere i marcatori chiave
            fig_f.update_traces(
                marker=dict(opacity=0.32, size=5, color="#58a6ff"),
                hovertemplate="<b>Portafoglio Simulato</b><br>Volatilità: %{x:.2f}%<br>Rendimento Atteso: %{y:.2f}%<extra></extra>"
            )
            
            cur = opt.get("current", {})
            cur_v = cur.get("risk", cur.get("volatility", opt.get("current_vol", 0))) * 100.0
            cur_r = cur.get("return", opt.get("current_ret", 0)) * 100.0
            cur_s = cur.get("sharpe", 0.0)
            
            ms = opt.get("max_sharpe", {})
            ms_v = ms.get("volatility", ms.get("risk", 0.0)) * 100.0 if ms else 0.0
            ms_r = ms.get("return", 0.0) * 100.0 if ms else 0.0
            ms_s = ms.get("sharpe", 0.0) if ms else 0.0

            mv = opt.get("min_vol", {})
            mv_v = mv.get("volatility", mv.get("risk", 0.0)) * 100.0 if mv else 0.0
            mv_r = mv.get("return", 0.0) * 100.0 if mv else 0.0
            mv_s = mv.get("sharpe", 0.0) if mv else 0.0

            # 1. Portafoglio Attuale (Stella Verde Smeraldo in primo piano con bordo luminoso)
            fig_f.add_trace(go.Scatter(
                x=[cur_v], y=[cur_r], mode="markers+text",
                name="Portafoglio Attuale", text=["⭐ Attuale"], textposition="top center",
                marker=dict(
                    size=20,
                    color="#00e676",
                    symbol="star",
                    line=dict(width=2.5, color="#ffffff")
                ),
                textfont=dict(color="#00e676", size=13),
                hovertemplate=f"<b>⭐ Portafoglio Attuale</b><br>Rendimento Atteso: <b>{cur_r:+.2f}%</b><br>Volatilità Annua: <b>{cur_v:.2f}%</b><br>Sharpe Ratio: <b>{cur_s:.2f}</b><extra></extra>"
            ))

            # 2. Max Sharpe Ratio
            if ms:
                fig_f.add_trace(go.Scatter(
                    x=[ms_v], y=[ms_r], mode="markers+text",
                    name="Max Sharpe Ratio", text=["🏆 Max Sharpe"], textposition="top right",
                    marker=dict(
                        size=17,
                        color="#ff9900",
                        symbol="diamond",
                        line=dict(width=2, color="#ffffff")
                    ),
                    textfont=dict(color="#ff9900", size=13),
                    hovertemplate=f"<b>🏆 Max Sharpe Ratio</b><br>Rendimento Atteso: <b>{ms_r:+.2f}%</b><br>Volatilità Annua: <b>{ms_v:.2f}%</b><br>Sharpe Ratio: <b>{ms_s:.2f}</b><extra></extra>"
                ))
                
            # 3. Minima Volatilità
            if mv:
                fig_f.add_trace(go.Scatter(
                    x=[mv_v], y=[mv_r], mode="markers+text",
                    name="Min Volatility", text=["🛡️ Min Vol"], textposition="bottom right",
                    marker=dict(
                        size=18,
                        color="#00f3ff",
                        symbol="circle",
                        line=dict(width=2.5, color="#ffffff")
                    ),
                    textfont=dict(color="#00f3ff", size=13),
                    hovertemplate=f"<b>🛡️ Minima Volatilità</b><br>Rendimento Atteso: <b>{mv_r:+.2f}%</b><br>Volatilità Annua: <b>{mv_v:.2f}%</b><br>Sharpe Ratio: <b>{mv_s:.2f}</b><extra></extra>"
                ))

            # Dynamic axis range calculation so ALL points fit perfectly
            all_vols = [frontier["vol_pct"].min(), frontier["vol_pct"].max(), cur_v, ms_v, mv_v]
            all_rets = [frontier["ret_pct"].min(), frontier["ret_pct"].max(), cur_r, ms_r, mv_r]
            all_vols = [v for v in all_vols if v > 0]
            all_rets = [r for r in all_rets]

            min_x = max(0, min(all_vols) - 2.0) if all_vols else 0
            max_x = max(all_vols) + 3.0 if all_vols else 30
            min_y = min(0, min(all_rets) - 2.0) if all_rets else 0
            max_y = max(all_rets) + 5.0 if all_rets else 40

            fig_f.update_xaxes(range=[min_x, max_x], gridcolor="rgba(255,255,255,0.06)")
            fig_f.update_yaxes(range=[min_y, max_y], gridcolor="rgba(255,255,255,0.06)")
                
            fig_f.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=65, b=40, l=45, r=30),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="left",
                    x=0.0,
                    bgcolor="rgba(22, 27, 34, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.15)",
                    borderwidth=1,
                    font=dict(size=12, color="#ffffff"),
                    title=None
                )
            )
            apply_plotly_theme(fig_f)
            st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

            # ── 3 CARDS SOTTO IL GRAFICO: CONFRONTO ALLOCAZIONI ────────
            st.markdown('<div style="margin-top: 6px; margin-bottom: 10px; font-weight: 700; font-size: 14px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px;">Confronto Allocazioni Ottimali</div>', unsafe_allow_html=True)
            col_c1, col_c2, col_c3 = st.columns(3)

            with col_c1:
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.85); backdrop-filter: blur(14px); border: 1px solid rgba(234, 179, 8, 0.35); border-left: 4px solid #eab308; border-radius: 12px; padding: 16px 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); height: 100%;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <div style="font-weight: 700; font-size: 15px; color: #ffffff;">⭐ Portafoglio Attuale</div>
                        <span class="argus-command-pill" style="border-color: rgba(234, 179, 8, 0.5); color: #eab308; font-size: 10.5px; font-weight: 700;">ATTUALE</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center;">
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">RENDIMENTO</div>
                            <div style="font-size: 16px; font-weight: 800; color: #eab308;">{cur_r:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">VOLATILITÀ</div>
                            <div style="font-size: 16px; font-weight: 800; color: #58a6ff;">{cur_v:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">SHARPE</div>
                            <div style="font-size: 16px; font-weight: 800; color: #3fb950;">{cur_s:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_c2:
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.85); backdrop-filter: blur(14px); border: 1px solid rgba(255, 153, 0, 0.35); border-left: 4px solid #ff9900; border-radius: 12px; padding: 16px 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); height: 100%;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <div style="font-weight: 700; font-size: 15px; color: #ffffff;">🏆 Max Sharpe Ratio</div>
                        <span class="argus-command-pill" style="border-color: rgba(255, 153, 0, 0.5); color: #ff9900; font-size: 10.5px; font-weight: 700;">OTTIMALE</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center;">
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">RENDIMENTO</div>
                            <div style="font-size: 16px; font-weight: 800; color: #ff9900;">{ms_r:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">VOLATILITÀ</div>
                            <div style="font-size: 16px; font-weight: 800; color: #58a6ff;">{ms_v:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">SHARPE</div>
                            <div style="font-size: 16px; font-weight: 800; color: #3fb950;">{ms_s:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_c3:
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.85); backdrop-filter: blur(14px); border: 1px solid rgba(0, 243, 255, 0.35); border-left: 4px solid #00f3ff; border-radius: 12px; padding: 16px 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); height: 100%;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <div style="font-weight: 700; font-size: 15px; color: #ffffff;">🛡️ Minima Volatilità</div>
                        <span class="argus-command-pill" style="border-color: rgba(0, 243, 255, 0.5); color: #00f3ff; font-size: 10.5px; font-weight: 700;">DIFENSIVO</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center;">
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">RENDIMENTO</div>
                            <div style="font-size: 16px; font-weight: 800; color: #00f3ff;">{mv_r:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">VOLATILITÀ</div>
                            <div style="font-size: 16px; font-weight: 800; color: #58a6ff;">{mv_v:.2f}%</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 4px; border-radius: 8px;">
                            <div style="font-size: 10px; color: #8b949e; font-weight: 600;">SHARPE</div>
                            <div style="font-size: 16px; font-weight: 800; color: #3fb950;">{mv_s:.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # ── LIVE REBALANCING SANDBOX (FEATURE 3) ───────────────────────
        st.divider()
        st.markdown("#### 🧪 Live Rebalancing Sandbox & Simulatore Real-Time (What-If Weight & Shares Matrix)")
        st.caption("Simula variazioni di portafoglio regolando **Pesi Percentuali (%)**, **Quantità di Quote (Vendi / Compra Azioni)** o **Importo Monetario (€)** con ricalcolo istantaneo di Rendimento, Volatilità, VaR 95%, Sharpe Ratio e Cash Flow.")

        tickers_in_opt = opt.get("tickers", [])
        if tickers_in_opt and not pos.empty:
            def _to_weight_map(raw_weights, tickers):
                if isinstance(raw_weights, dict):
                    return raw_weights
                if isinstance(raw_weights, (list, tuple, np.ndarray)) and len(raw_weights) == len(tickers):
                    return {t: float(w) for t, w in zip(tickers, raw_weights)}
                return {t: 1.0 / len(tickers) for t in tickers}

            cur_w_map = _to_weight_map(opt.get("current", {}).get("weights"), tickers_in_opt)
            ms_w_map = _to_weight_map(opt.get("max_sharpe", {}).get("weights"), tickers_in_opt)
            mv_w_map = _to_weight_map(opt.get("min_vol", {}).get("weights"), tickers_in_opt)

            # Mappa prezzi e quote attuali
            price_map = {}
            qty_map = {}
            val_map = {}
            for _, r in pos.iterrows():
                tk = str(r.get("ticker", ""))
                lp = float(r.get("last_price", 0.0) or 0.0)
                qn = float(r.get("qty_net", 0.0) or 0.0)
                cv = float(r.get("current_value", 0.0) or (qn * lp if lp > 0 else 0.0))
                price_map[tk] = lp if lp > 0 else 100.0
                qty_map[tk] = qn
                val_map[tk] = cv

            for t in tickers_in_opt:
                if t not in price_map: price_map[t] = 100.0
                if t not in qty_map: qty_map[t] = 10.0
                if t not in val_map: val_map[t] = qty_map[t] * price_map[t]

            tot_cur_val = sum(qty_map.get(t, 0.0) * price_map.get(t, 100.0) for t in tickers_in_opt)

            sbx_mode = st.radio(
                "Modalità di Simulazione Operativa:",
                ["🔢 Variazione Quote (Vendi / Compra N Azioni)", "📊 Pesi Percentuali (%)", "💶 Importo Monetario (€)"],
                horizontal=True,
                key="sbx_simulation_mode"
            )

            sim_weights = {}
            sim_qtys = {}
            sim_vals = {}

            if sbx_mode == "🔢 Variazione Quote (Vendi / Compra N Azioni)":
                col_q1, col_q2, col_q3, col_q4 = st.columns(4)
                with col_q1:
                    if st.button("⭐ Ripristina Quote Attuali", key="sbx_q_reset", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_q_{t}"] = float(qty_map.get(t, 0.0))
                        st.rerun()
                with col_q2:
                    if st.button("➕ +10 Quote su Tutti", key="sbx_q_plus10", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_q_{t}"] = float(qty_map.get(t, 0.0) + 10.0)
                        st.rerun()
                with col_q3:
                    if st.button("➖ -10 Quote (o Max Disp.)", key="sbx_q_minus10", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_q_{t}"] = max(0.0, float(qty_map.get(t, 0.0) - 10.0))
                        st.rerun()
                with col_q4:
                    if st.button("🧹 Azzera Tutto (0 Quote)", key="sbx_q_zero", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_q_{t}"] = 0.0
                        st.rerun()

                st.markdown('<div style="font-size:12px; font-weight:700; color:#8b949e; margin: 10px 0 4px 0;">REGOLATORE QUOTE AZIONI:</div>', unsafe_allow_html=True)
                grid_cols = st.columns(min(4, len(tickers_in_opt)))
                for i, t in enumerate(tickers_in_opt):
                    cur_q = float(qty_map.get(t, 0.0))
                    cur_px = float(price_map.get(t, 100.0))
                    step_val = 1.0 if cur_q >= 1.0 and cur_q.is_integer() else 0.1
                    with grid_cols[i % len(grid_cols)]:
                        new_q = st.number_input(
                            f"**{t}** (Attuali: {cur_q:,.1f})",
                            min_value=0.0,
                            value=float(st.session_state.get(f"sbx_q_{t}", cur_q)),
                            step=step_val,
                            key=f"sbx_q_{t}",
                            help=f"Prezzo: € {cur_px:,.2f} | Valore Attuale: € {cur_q * cur_px:,.2f}"
                        )
                        sim_qtys[t] = new_q
                        delta_q = new_q - cur_q
                        delta_val = delta_q * cur_px
                        if delta_q < 0:
                            st.markdown(f"<span style='font-size:11px; color:#00e676; font-weight:700;'>🟢 VENDI {abs(delta_q):,.1f} (Libera € {abs(delta_val):,.2f})</span>", unsafe_allow_html=True)
                        elif delta_q > 0:
                            st.markdown(f"<span style='font-size:11px; color:#58a6ff; font-weight:700;'>🔵 COMPRA +{delta_q:,.1f} (Costa € {delta_val:,.2f})</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span style='font-size:11px; color:#8b949e;'>⚪ Invariato</span>", unsafe_allow_html=True)

                        sim_vals[t] = new_q * cur_px

                tot_sim_val = sum(sim_vals.values())
                net_cash_flow = sum((qty_map.get(t, 0.0) - sim_qtys[t]) * price_map.get(t, 100.0) for t in tickers_in_opt)
                if tot_sim_val > 0:
                    norm_sim_weights = {t: sim_vals[t] / tot_sim_val for t in tickers_in_opt}
                else:
                    norm_sim_weights = {t: 1.0 / len(tickers_in_opt) for t in tickers_in_opt}

            elif sbx_mode == "💶 Importo Monetario (€)":
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    if st.button("⭐ Ripristina Valori Attuali", key="sbx_m_reset", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_m_{t}"] = float(val_map.get(t, 1000.0))
                        st.rerun()
                with col_m2:
                    if st.button("⚖️ Equi-Valore (€ 5.000 / asset)", key="sbx_m_eq", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_m_{t}"] = 5000.0
                        st.rerun()

                st.markdown('<div style="font-size:12px; font-weight:700; color:#8b949e; margin: 10px 0 4px 0;">REGOLATORE CONTROVALORE (€):</div>', unsafe_allow_html=True)
                grid_cols = st.columns(min(4, len(tickers_in_opt)))
                for i, t in enumerate(tickers_in_opt):
                    cur_v = float(val_map.get(t, 0.0))
                    cur_px = float(price_map.get(t, 100.0))
                    with grid_cols[i % len(grid_cols)]:
                        new_v = st.number_input(
                            f"**{t} (€)** (Attuale: € {cur_v:,.0f})",
                            min_value=0.0,
                            value=float(st.session_state.get(f"sbx_m_{t}", cur_v)),
                            step=250.0,
                            key=f"sbx_m_{t}"
                        )
                        sim_vals[t] = new_v
                        sim_qtys[t] = new_v / cur_px if cur_px > 0 else 0.0

                tot_sim_val = sum(sim_vals.values())
                net_cash_flow = tot_cur_val - tot_sim_val
                if tot_sim_val > 0:
                    norm_sim_weights = {t: sim_vals[t] / tot_sim_val for t in tickers_in_opt}
                else:
                    norm_sim_weights = {t: 1.0 / len(tickers_in_opt) for t in tickers_in_opt}

            else:  # Pesi Percentuali (%)
                col_pre1, col_pre2, col_pre3, col_pre4, col_pre5 = st.columns(5)
                with col_pre1:
                    if st.button("⭐ Pesi Attuali", key="sbx_preset_cur", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_w_{t}"] = float(cur_w_map.get(t, 0.0) * 100.0)
                        st.rerun()
                with col_pre2:
                    if st.button("⚖️ Equipesato (1/N)", key="sbx_preset_eq", use_container_width=True):
                        eq_w = 100.0 / len(tickers_in_opt)
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_w_{t}"] = float(eq_w)
                        st.rerun()
                with col_pre3:
                    if st.button("🏆 Max Sharpe", key="sbx_preset_ms", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_w_{t}"] = float(ms_w_map.get(t, 0.0) * 100.0)
                        st.rerun()
                with col_pre4:
                    if st.button("🛡️ Minima Vol.", key="sbx_preset_mv", use_container_width=True):
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_w_{t}"] = float(mv_w_map.get(t, 0.0) * 100.0)
                        st.rerun()
                with col_pre5:
                    if st.button("🧬 Equal Risk (ERC)", key="sbx_preset_erc", use_container_width=True):
                        df_ret_temp = results.get("returns", pd.DataFrame())
                        erc_res = compute_equal_risk_contribution_portfolio(df_ret_temp[tickers_in_opt] if not df_ret_temp.empty and all(t in df_ret_temp.columns for t in tickers_in_opt) else None)
                        erc_w = erc_res.get("weights", {})
                        for t in tickers_in_opt:
                            st.session_state[f"sbx_w_{t}"] = float(erc_w.get(t, 1.0 / len(tickers_in_opt)) * 100.0)
                        st.rerun()

                st.markdown('<div style="font-size:12px; font-weight:700; color:#8b949e; margin: 10px 0 4px 0;">REGOLATORE PESI ASSET:</div>', unsafe_allow_html=True)
                grid_cols = st.columns(min(4, len(tickers_in_opt)))
                for i, t in enumerate(tickers_in_opt):
                    default_w = float(cur_w_map.get(t, 1.0 / len(tickers_in_opt)) * 100.0)
                    with grid_cols[i % len(grid_cols)]:
                        sim_weights[t] = st.slider(
                            f"**{t}**", 
                            min_value=0.0, 
                            max_value=100.0, 
                            value=float(st.session_state.get(f"sbx_w_{t}", default_w)), 
                            step=0.5,
                            key=f"sbx_w_{t}"
                        )

                tot_raw_w = sum(sim_weights.values())
                if tot_raw_w > 0:
                    norm_sim_weights = {t: w / tot_raw_w for t, w in sim_weights.items()}
                else:
                    norm_sim_weights = {t: 1.0 / len(tickers_in_opt) for t in tickers_in_opt}
                
                tot_sim_val = tot_cur_val
                net_cash_flow = 0.0
                for t in tickers_in_opt:
                    sim_vals[t] = norm_sim_weights[t] * tot_sim_val
                    sim_qtys[t] = sim_vals[t] / price_map[t] if price_map[t] > 0 else 0.0

            df_ret_sim = results.get("returns", pd.DataFrame())
            if df_ret_sim.empty or not all(t in df_ret_sim.columns for t in tickers_in_opt):
                df_pr = results.get("df_prices", pd.DataFrame())
                if not df_pr.empty and "ticker" in df_pr.columns:
                    piv = df_pr.pivot(index="price_date", columns="ticker", values="close")
                    df_ret_sim = piv[[t for t in tickers_in_opt if t in piv.columns]].pct_change().dropna()

            valid_ts = [t for t in tickers_in_opt if t in df_ret_sim.columns]
            if len(valid_ts) >= 2:
                mu_vec = df_ret_sim[valid_ts].mean().values * 252.0
                cov_mat = df_ret_sim[valid_ts].cov().values * 252.0
                w_sim_arr = np.array([norm_sim_weights[t] for t in valid_ts])
                w_cur_arr = np.array([cur_w_map.get(t, 0.0) for t in valid_ts])
                
                if w_cur_arr.sum() > 0:
                    w_cur_arr = w_cur_arr / w_cur_arr.sum()

                ret_sim = float(np.dot(w_sim_arr, mu_vec) * 100.0)
                vol_sim = float(np.sqrt(np.dot(w_sim_arr, np.dot(cov_mat, w_sim_arr))) * 100.0)
                var_sim = float(1.645 * (vol_sim / np.sqrt(252.0)))
                rf = 3.0
                sharpe_sim = float((ret_sim - rf) / vol_sim) if vol_sim > 0 else 0.0

                ret_cur = float(np.dot(w_cur_arr, mu_vec) * 100.0)
                vol_cur = float(np.sqrt(np.dot(w_cur_arr, np.dot(cov_mat, w_cur_arr))) * 100.0)
                var_cur = float(1.645 * (vol_cur / np.sqrt(252.0)))
                sharpe_cur = float((ret_cur - rf) / vol_cur) if vol_cur > 0 else 0.0

                d_ret = ret_sim - ret_cur
                d_vol = vol_sim - vol_cur
                d_var = var_sim - var_cur
                d_sharpe = sharpe_sim - sharpe_cur

                if sbx_mode == "🔢 Variazione Quote (Vendi / Compra N Azioni)" or sbx_mode == "💶 Importo Monetario (€)":
                    cf_color = "#00e676" if net_cash_flow > 0.01 else ("#f85149" if net_cash_flow < -0.01 else "#8b949e")
                    cf_label = f"🟢 +€ {net_cash_flow:,.2f} (Liquidità netta liberata)" if net_cash_flow > 0.01 else (f"🔴 -€ {abs(net_cash_flow):,.2f} (Capitale aggiuntivo richiesto)" if net_cash_flow < -0.01 else "⚪ € 0.00 (Operazione bilanciata)")
                    st.markdown(f"""
                    <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 14px; margin: 12px 0; display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; align-items:center;">
                        <div>
                            <span style="font-size:12px; color:#8b949e;">Patrimonio Attuale: <b>€ {tot_cur_val:,.2f}</b></span> &nbsp;→&nbsp; 
                            <span style="font-size:12px; color:#58a6ff;">Patrimonio Simulato: <b>€ {tot_sim_val:,.2f}</b></span>
                        </div>
                        <div>
                            <span style="font-size:12px; color:#8b949e;">Cash Flow Operazione:</span> 
                            <b style="font-size:12.5px; color:{cf_color}; margin-left:4px;">{cf_label}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:rgba(22,27,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:8px 12px; margin: 10px 0;">
                        <span style="font-size:12px; color:#8b949e;">Somma Pesi Regolati: <b>{tot_raw_w:.1f}%</b> (Normalizzato automaticamente al <b>100.0%</b>)</span>
                    </div>
                    """, unsafe_allow_html=True)

                c_sb1, c_sb2, c_sb3, c_sb4 = st.columns(4)
                with c_sb1:
                    metric_card(
                        "Rendimento Atteso",
                        f"{ret_sim:.2f}%",
                        delta=f"{d_ret:+.2f}% vs Attuale",
                        positive=(d_ret >= 0),
                        help_text="Rendimento annuo atteso del portafoglio post-ribilanciamento simulato."
                    )
                with c_sb2:
                    metric_card(
                        "Volatilità Annua",
                        f"{vol_sim:.2f}%",
                        delta=f"{d_vol:+.2f}% vs Attuale",
                        positive=(d_vol <= 0),
                        help_text="Volatilità annua stimata del portafoglio simulato."
                    )
                with c_sb3:
                    metric_card(
                        "VaR 95% Giornaliero",
                        f"{var_sim:.2f}%",
                        delta=f"{d_var:+.2f}% vs Attuale",
                        positive=(d_var <= 0),
                        help_text="Value at Risk 95% su orizzonte di 1 giorno post-ribilanciamento."
                    )
                with c_sb4:
                    metric_card(
                        "Sharpe Ratio Simulato",
                        f"{sharpe_sim:.2f}",
                        delta=f"{d_sharpe:+.2f} vs Attuale",
                        positive=(d_sharpe >= 0),
                        help_text="Indice di Sharpe atteso del portafoglio post-ribilanciamento."
                    )

                df_compare_w = pd.DataFrame({
                    "Ticker": valid_ts,
                    "Peso Attuale (%)": [cur_w_map.get(t, 0.0) * 100.0 for t in valid_ts],
                    "Peso Sandbox (%)": [norm_sim_weights[t] * 100.0 for t in valid_ts]
                })

                fig_sbx = go.Figure()
                fig_sbx.add_trace(go.Bar(
                    x=df_compare_w["Ticker"],
                    y=df_compare_w["Peso Attuale (%)"],
                    name="Allocazione Attuale (%)",
                    marker=dict(color="#64748b", line=dict(color="rgba(255,255,255,0.1)", width=1)),
                    hovertemplate="<b>%{x}</b><br>Allocazione Attuale: <b>%{y:.2f}%</b><extra></extra>"
                ))
                fig_sbx.add_trace(go.Bar(
                    x=df_compare_w["Ticker"],
                    y=df_compare_w["Peso Sandbox (%)"],
                    name="Allocazione Sandbox (%)",
                    marker=dict(color="#ff9900", line=dict(color="rgba(255,153,0,0.4)", width=1)),
                    hovertemplate="<b>%{x}</b><br>Allocazione Sandbox: <b>%{y:.2f}%</b><extra></extra>"
                ))
                fig_sbx.update_layout(
                    barmode="group",
                    height=340,
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=35, b=30),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11.5)
                    ),
                    xaxis=dict(
                        title=None,
                        tickangle=-45,
                        tickfont=dict(size=11, family="monospace")
                    ),
                    yaxis=dict(
                        title="Peso %",
                        gridcolor="rgba(255,255,255,0.06)",
                        zerolinecolor="rgba(255,255,255,0.12)"
                    )
                )
                apply_plotly_theme(fig_sbx)
                st.plotly_chart(fig_sbx, use_container_width=True)

                # Tabella Operativa Dettagliata What-If
                with st.expander("📋 Tabella di Dettaglio Operativo & Ticket What-If", expanded=True):
                    table_rows = []
                    for t in valid_ts:
                        cq = float(qty_map.get(t, 0.0))
                        sq = float(sim_qtys.get(t, 0.0))
                        asset_px = float(price_map.get(t, 100.0))
                        cv = cq * asset_px
                        sv = sq * asset_px
                        dq = sq - cq
                        dv = sv - cv
                        cw = cur_w_map.get(t, 0.0) * 100.0
                        sw = norm_sim_weights.get(t, 0.0) * 100.0

                        if dq < -1e-4:
                            action = f"🟢 VENDI {abs(dq):,.1f} quote"
                        elif dq > 1e-4:
                            action = f"🔵 COMPRA +{dq:,.1f} quote"
                        else:
                            action = "⚪ MANTIENI"

                        table_rows.append({
                            "Ticker": t,
                            "Prezzo (€)": f"€ {asset_px:,.2f}",
                            "Quote Attuali": f"{cq:,.1f}",
                            "Quote Simulate": f"{sq:,.1f}",
                            "Delta Quote": f"{dq:+,.1f}" if abs(dq) > 1e-4 else "0.0",
                            "Valore Attuale": f"€ {cv:,.2f}",
                            "Valore Simulato": f"€ {sv:,.2f}",
                            "Delta Controvalore": f"€ {dv:+,.2f}" if abs(dv) > 0.01 else "€ 0.00",
                            "Peso Attuale": f"{cw:.2f}%",
                            "Peso Simulato": f"{sw:.2f}%",
                            "Azione": action
                        })

                    col_wi_f1, col_wi_f2, col_wi_f3 = st.columns([2.0, 1.3, 0.9])
                    with col_wi_f1:
                        search_wi = st.text_input("🔍 Cerca Ticker What-If:", placeholder="Digita ticker per filtrare...", key="search_whatif_t")
                    with col_wi_f2:
                        filter_wi_act = st.selectbox("🏷️ Azione What-If:", ["Tutte le Azioni", "🔵 Solo COMPRA (+)", "🟢 Solo VENDI (-)", "⚪ Solo MANTIENI"], key="filter_whatif_a")

                    df_wi_tbl = pd.DataFrame(table_rows)
                    if not df_wi_tbl.empty:
                        if search_wi:
                            df_wi_tbl = df_wi_tbl[df_wi_tbl["Ticker"].astype(str).str.contains(search_wi.strip(), case=False, na=False)]
                        if filter_wi_act == "🔵 Solo COMPRA (+)":
                            df_wi_tbl = df_wi_tbl[df_wi_tbl["Azione"].astype(str).str.contains("COMPRA", case=False, na=False)]
                        elif filter_wi_act == "🟢 Solo VENDI (-)":
                            df_wi_tbl = df_wi_tbl[df_wi_tbl["Azione"].astype(str).str.contains("VENDI", case=False, na=False)]
                        elif filter_wi_act == "⚪ Solo MANTIENI":
                            df_wi_tbl = df_wi_tbl[df_wi_tbl["Azione"].astype(str).str.contains("MANTIENI", case=False, na=False)]

                    with col_wi_f3:
                        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                        csv_wi = df_wi_tbl.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Scarica CSV",
                            data=csv_wi,
                            file_name="what_if_simulator_orders.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                    if df_wi_tbl.empty:
                        st.info("ℹ️ Nessun titolo corrisponde ai filtri selezionati.")
                    else:
                        st.dataframe(df_wi_tbl, use_container_width=True, hide_index=True)

        st.divider()
        col_head_hrp1, col_head_hrp2 = st.columns([3.2, 1.1])
        with col_head_hrp1:
            st.markdown("#### 🧬 Hierarchical Risk Parity (HRP - Marcos López de Prado)")
            st.caption("Allocazione robusta basata su Machine Learning & Clustering Gerarchico ad Albero (Tree Clustering & Recursive Bisection) senza inversione di matrice.")
        with col_head_hrp2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida all'Hierarchical Risk Parity (HRP)", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è l'Hierarchical Risk Parity (HRP)</div>
  <div>Un algoritmo quantitativo di allocazione sviluppato da Marcos López de Prado (2016) che sfrutta la teoria dei grafi e il machine learning non supervisionato per superare l'instabilità dell'inversione di matrice (&Sigma;<sup>&minus;1</sup>) di Markowitz.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Il Processo in 3 Fasi Matematiche</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    1. <b>Tree Clustering:</b> Calcola la distanza di correlazione <b>D<sub>i,j</sub> = &radic;[ (1 &minus; &rho;<sub>i,j</sub>) / 2 ]</b> e costruisce il dendrogramma gerarchico.<br>
    2. <b>Quasi-Diagonalization:</b> Riordina la matrice affinché gli asset simili e correlati siano contigui.<br>
    3. <b>Recursive Bisection:</b> Alloca il capitale bipartendo ricorsivamente i cluster in modo inversamente proporzionale alla loro varianza aggregata.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Garantisce una diversificazione gerarchica genuina ed evita l'iper-concentrazione su singoli asset quando la matrice di covarianza presenta collinearità elevata o campioni ridotti.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il modulo <code>core/risk_engine.py</code> calcola la matrice delle distanze informative e genera il dendrogramma dei legami gerarchici con i pesi di allocazione paritaria ottimali.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Confronta i pesi calcolati da HRP con l'allocazione attuale: gli scostamenti evidenziano cluster di titoli con sovraesposizione di rischio non compensata.</div>
</div>

</div>
""", button_label="💡 Come funziona l'HRP?")

        df_returns_hrp = results.get("returns", pd.DataFrame())
        if df_returns_hrp.empty or df_returns_hrp.shape[1] < 2:
            df_pr = results.get("df_prices", pd.DataFrame())
            if not df_pr.empty and "ticker" in df_pr.columns and "close" in df_pr.columns:
                piv = df_pr.pivot(index="price_date", columns="ticker", values="close").sort_index()
                df_returns_hrp = piv.pct_change().dropna(how="all")

        # Filtro per isolare SOLO i titoli ATTIVAMENTE DETENUTI (qty_net > 0) ed escludere posizioni chiuse e tassi FX (es. DKKEUR=X)
        if not df_returns_hrp.empty and not pos.empty:
            active_mask = (pos["qty_net"] > 1e-6) if "qty_net" in pos.columns else pd.Series(True, index=pos.index)
            port_tickers = [t for t in pos[active_mask]["ticker"].dropna().unique() if not str(t).endswith("=X")]
            valid_cols = [c for c in df_returns_hrp.columns if c in port_tickers]
            if len(valid_cols) >= 2:
                df_returns_hrp = df_returns_hrp[valid_cols]

        # Sanitizzazione outlier estremi nei rendimenti giornalieri (es. split non rettificati o anomalie decimali)
        if not df_returns_hrp.empty:
            df_returns_hrp = df_returns_hrp.replace([np.inf, -np.inf], np.nan).clip(lower=-0.50, upper=1.0)

        if not df_returns_hrp.empty and df_returns_hrp.shape[1] >= 2:
            hrp_res = compute_hrp_portfolio(df_returns_hrp)
            if hrp_res:
                col_hrp1, col_hrp2 = st.columns([1.5, 1])
                with col_hrp1:
                    df_hrp_w = hrp_res.get("df_weights", pd.DataFrame()).sort_values("hrp_weight_pct", ascending=False)
                    fig_hrp = px.bar(
                        df_hrp_w, x="ticker", y="hrp_weight_pct",
                        labels={"ticker": "Asset in Portafoglio", "hrp_weight_pct": "Allocazione Ottima HRP %"},
                        title="Allocazione Ottima Hierarchical Risk Parity (HRP)",
                        color="hrp_weight_pct", color_continuous_scale="Viridis",
                        template="plotly_dark", height=340
                    )
                    fig_hrp.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    st.plotly_chart(fig_hrp, use_container_width=True)

                with col_hrp2:
                    st.markdown(f"""
                    * **Rendimento Atteso HRP**: <span style='color:#00e676; font-weight:bold;'>{hrp_res['expected_return_pct']:.2f}%</span>
                    * **Volatilità Annua HRP**: <span style='color:#ffab40; font-weight:bold;'>{hrp_res['volatility_annual_pct']:.2f}%</span>
                    * **Sharpe Ratio HRP**: <span style='color:#00f3ff; font-weight:bold;'>{hrp_res['sharpe_ratio']:.2f}</span>
                    """, unsafe_allow_html=True)
                    
                    df_hrp_display = df_hrp_w.rename(columns={
                        "ticker": "Asset / Titolo",
                        "hrp_weight": "Peso Frazionario",
                        "hrp_weight_pct": "Allocazione Ottima HRP %"
                    })
                    csv_hrp = df_hrp_display.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_hrp, file_name="pesi_ottimali_hrp.csv", mime="text/csv", use_container_width=True, key="btn_download_hrp_weights")
                    st.dataframe(
                        df_hrp_display.style.format({
                            "Allocazione Ottima HRP %": "{:.2f}%",
                            "Peso Frazionario": "{:.4f}"
                        }),
                        use_container_width=True,
                        hide_index=True,
                        height=240
                    )
        # ── SEZIONE ERC (EQUAL RISK CONTRIBUTION) ──
        st.markdown('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True)
        col_erc_t1, col_erc_t2 = st.columns([3.2, 1.1])
        with col_erc_t1:
            st.markdown("##### ⚖️ Equal Risk Contribution (ERC / Parità di Rischio Pura)")
            st.caption("Allocazione dove ogni singolo asset contribuisce esattamente per la stessa quota (1/N) alla volatilità totale di portafoglio.")
        with col_erc_t2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            render_info_modal(
                title="Come Funziona Equal Risk Contribution (ERC)",
                content="""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🎯 Differenza tra 1/N ed Equal Risk Contribution</b><br>
  Un portafoglio equipesato in capitale (1/N) non è equipesato in rischio: un titolo molto volatile (es. Tech o Crypto) dominerà l'80% delle oscillazioni totali.
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Formulazione Matematica</div>
  <div>ARGUS risolve il problema di ottimizzazione non lineare (SLSQP):</div>
  <div style="background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 4px; font-family: monospace; margin: 4px 0; color: #79c0ff;">
    min<sub>w</sub> &sum;<sub>i,j</sub> ( RC<sub>i</sub> &minus; RC<sub>j</sub> )<sup>2</sup> &nbsp;&nbsp;s.t.&nbsp;&nbsp; &sum; w<sub>i</sub> = 1, w<sub>i</sub> &ge; 0
  </div>
  <div>dove il contributo marginale al rischio è <b>RC<sub>i</sub> = w<sub>i</sub> &middot; (&Sigma;w)<sub>i</sub> / &sigma;<sub>p</sub> = &sigma;<sub>p</sub> / N</b>.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Vantaggi Istituzionali</div>
  <div>Evita la concentrazione nei titoli più volatili e non richiede la stima dei rendimenti attesi futuri &mu; (che è notoriamente rumorosa), massimizzando la stabilità e la diversificazione nei mercati avversi.</div>
</div>

</div>
""",
                button_label="📖 Metodologia Equal Risk (ERC)"
            )

        erc_res = compute_equal_risk_contribution_portfolio(df_returns_hrp)
        if erc_res and erc_res.get("weights"):
            col_erc1, col_erc2 = st.columns([1.5, 1])
            with col_erc1:
                df_erc_w = pd.DataFrame([
                    {"ticker": t, "erc_weight_pct": round(w * 100.0, 2), "risk_contrib_pct": erc_res.get("risk_contributions_pct", {}).get(t, 0.0)}
                    for t, w in erc_res["weights"].items()
                ]).sort_values("erc_weight_pct", ascending=False)

                fig_erc = px.bar(
                    df_erc_w, x="ticker", y="erc_weight_pct",
                    labels={"ticker": "Asset in Portafoglio", "erc_weight_pct": "Peso ERC %"},
                    title="Pesi Ottimali Equal Risk Contribution (ERC)",
                    color="erc_weight_pct", color_continuous_scale="Teal",
                    template="plotly_dark", height=330
                )
                fig_erc.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=40, b=10))
                apply_plotly_theme(fig_erc)
                st.plotly_chart(fig_erc, use_container_width=True)

            with col_erc2:
                st.markdown(f"""
                * **Rendimento Atteso ERC**: <span style='color:#00e676; font-weight:bold;'>{erc_res['expected_return']*100:.2f}%</span>
                * **Volatilità Annua ERC**: <span style='color:#ffab40; font-weight:bold;'>{erc_res['volatility']*100:.2f}%</span>
                * **Sharpe Ratio ERC**: <span style='color:#00f3ff; font-weight:bold;'>{erc_res['sharpe_ratio']:.2f}</span>
                """, unsafe_allow_html=True)

                df_erc_disp = df_erc_w.rename(columns={
                    "ticker": "Asset",
                    "erc_weight_pct": "Peso ERC (%)",
                    "risk_contrib_pct": "Contributo al Rischio (%)"
                })
                csv_erc = df_erc_disp.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_erc, file_name="pesi_ottimali_erc.csv", mime="text/csv", use_container_width=True, key="btn_download_erc_weights")
                st.dataframe(
                    df_erc_disp.style.format({
                        "Peso ERC (%)": "{:.2f}%",
                        "Contributo al Rischio (%)": "{:.2f}%"
                    }),
                    use_container_width=True,
                    hide_index=True,
                    height=230
                )

        st.divider()
        st.markdown("#### 🧮 Calcolatore di Ribilanciamento Tattico (Pesi & Quote Operative)")
        st.caption("Calcola gli ordini esatti di acquisto/vendita per riallineare il tuo portafoglio ai pesi ottimi di Markowitz o ad una strategia custom.")

        import importlib
        import core.rebalancer
        importlib.reload(core.rebalancer)
        from core.rebalancer import compute_rebalancing_orders

        col_reb1, col_reb2, col_reb3 = st.columns([3.3, 1.3, 0.8])
        with col_reb1:
            target_strategy = st.segmented_control(
                "Profilo Bersaglio di Ribilanciamento:",
                options=["🎯 Max Sharpe (Markowitz)", "🛡️ Minima Volatilità", "⚖️ Equi-peso (Equal Weight)"],
                default="🎯 Max Sharpe (Markowitz)",
                key="seg_target_strategy"
            )
            if not target_strategy:
                target_strategy = "🎯 Max Sharpe (Markowitz)"
        with col_reb2:
            new_cash_input = st.number_input(
                "Iniezione Cassa (€):",
                value=0.0, step=500.0, format="%.2f",
                help="Inserisci un valore positivo per nuovi versamenti o negativo per prelievi di cassa."
            )
        with col_reb3:
            st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)
            int_shares_flag = st.checkbox("Quote Intere", value=True, help="Arrotonda le quote operative agli interi.")

        mode_key = "max_sharpe" if "Max Sharpe" in target_strategy else ("min_vol" if "Minima" in target_strategy else "equal_weight")

        rebal_res = compute_rebalancing_orders(
            results,
            target_mode=mode_key,
            new_cash_eur=new_cash_input,
            integer_shares=int_shares_flag
        )

        df_orders = rebal_res.get("orders", pd.DataFrame())
        summary_orders = rebal_res.get("summary", {})

        if not df_orders.empty:
            def highlight_action(val):
                if str(val).startswith("BUY"):
                    return "color: #00ff66; font-weight: bold;"
                elif str(val).startswith("SELL"):
                    return "color: #ff3333; font-weight: bold;"
                return "color: #8b949e;"

            col_om1, col_om2, col_om3 = st.columns(3)
            with col_om1:
                t_val = summary_orders.get('target_total_value_eur', summary_orders.get('target_total_value', 0.0))
                t_val_str = f"€ {t_val:,.2f}".replace(",", ".")
                metric_card("Valore Portafoglio Target", t_val_str, delta="Allocazione Ottimale", positive=True, help_text="Valore target complessivo del portafoglio post-ribilanciamento.")
            with col_om2:
                b_val = summary_orders.get('total_buy_eur', summary_orders.get('total_buy_value', 0.0))
                b_val_str = f"€ {b_val:,.2f}".replace(",", ".")
                metric_card("Totale Acquisti", b_val_str, delta="Liquidità Richiesta", positive=True, help_text="Somma del controvalore di tutti gli ordini di acquisto generati dal ribilanciatore.")
            with col_om3:
                s_val = summary_orders.get('total_sell_eur', summary_orders.get('total_sell_value', 0.0))
                s_val_str = f"€ {s_val:,.2f}".replace(",", ".")
                metric_card("Totale Vendite", s_val_str, delta="Liquidità Liberata", positive=True, help_text="Somma del controvalore di tutti gli ordini di vendita generati dal ribilanciatore.")

            req_cols = ["ticker", "action", "current_qty", "target_qty", "qty_delta", "last_price", "order_value_eur", "current_weight_pct", "target_weight_pct"]
            df_disp_orders = df_orders.reindex(columns=req_cols).fillna(0).rename(columns={
                "ticker": "Ticker", "action": "Azione Tattica", "current_qty": "Quote Attuali", "target_qty": "Quote Target",
                "qty_delta": "Quote Operative", "last_price": "Prezzo (€)", "order_value_eur": "Controvalore Ordine (€)",
                "current_weight_pct": "Peso Attuale %", "target_weight_pct": "Peso Target %"
            })

            col_ro_f1, col_ro_f2, col_ro_f3 = st.columns([2.0, 1.3, 0.9])
            with col_ro_f1:
                search_ro = st.text_input("🔍 Cerca Ordine:", placeholder="Filtra per Ticker (es. AAPL, BTC, ISP.MI)...", key="search_rebal_ord")
            with col_ro_f2:
                filter_ro_act = st.selectbox("🏷️ Direzione Ordine:", ["Tutti gli Ordini", "🟢 Solo ACQUISTO (BUY)", "🔴 Solo VENDITA (SELL)", "⚪ Solo MANTIENI (HOLD)"], key="filter_rebal_act")

            df_disp_orders_filt = df_disp_orders.copy()
            if search_ro:
                df_disp_orders_filt = df_disp_orders_filt[df_disp_orders_filt["Ticker"].astype(str).str.contains(search_ro.strip(), case=False, na=False)]
            if filter_ro_act == "🟢 Solo ACQUISTO (BUY)":
                df_disp_orders_filt = df_disp_orders_filt[df_disp_orders_filt["Azione Tattica"].astype(str).str.contains("ACQUISTO|BUY", case=False, na=False)]
            elif filter_ro_act == "🔴 Solo VENDITA (SELL)":
                df_disp_orders_filt = df_disp_orders_filt[df_disp_orders_filt["Azione Tattica"].astype(str).str.contains("VENDITA|SELL", case=False, na=False)]
            elif filter_ro_act == "⚪ Solo MANTIENI (HOLD)":
                df_disp_orders_filt = df_disp_orders_filt[df_disp_orders_filt["Azione Tattica"].astype(str).str.contains("MANTIENI|HOLD", case=False, na=False)]

            with col_ro_f3:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                csv_ro = df_disp_orders_filt.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Scarica CSV",
                    data=csv_ro,
                    file_name="ordini_ribilanciamento_tattico.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_download_rebal_csv"
                )

            if df_disp_orders_filt.empty:
                st.info("ℹ️ Nessun ordine corrisponde ai criteri di filtro impostati.")
            else:
                st.dataframe(
                    df_disp_orders_filt.style.map(highlight_action, subset=["Azione Tattica"]).format({
                        "Quote Attuali": "{:,.2f}", "Quote Target": "{:,.2f}", "Quote Operative": "{:+,.2f}",
                        "Prezzo (€)": "€ {:,.2f}", "Controvalore Ordine (€)": "€ {:+,.2f}",
                        "Peso Attuale %": "{:.2f}%", "Peso Target %": "{:.2f}%"
                    }),
                    use_container_width=True, hide_index=True
                )
            
        # ── BACKTESTING ESTRATTO (HRP / MARKOWITZ / EQUI-PESO) ────────
        bt_data = opt.get("backtest", {})
        if bt_data:
            st.divider()
            st.markdown("#### ⏳ Backtesting Storico: Portafoglio vs Markowitz vs HRP vs S&P 500")
            st.caption("Verifica la performance out-of-sample storicizzata dei modelli di allocazione rispetto al mercato.")
            
            glossary_modal("ℹ️ Cos'è l'Hierarchical Risk Parity (HRP)?", """
<div style="font-size: 13.5px; line-height: 1.45;">
L'<b>Hierarchical Risk Parity (HRP)</b> è un algoritmo quantitativo sviluppato da Marcos López de Prado che supera i limiti dell'ottimizzazione classica di Markowitz sfruttando il <b>clustering gerarchico e la bisezione ricorsiva</b>. Produce pesi out-of-sample solidi senza invertire matrici di covarianza.
</div>
            """, button_label="💡 Cos'è l'Hierarchical Risk Parity?")
            
            df_bt = pd.DataFrame(bt_data.get("equity_curves", {}))
            if not df_bt.empty and "date" in df_bt.columns:
                df_bt["date"] = pd.to_datetime(df_bt["date"])
                
                fig_bt = px.line(
                    df_bt, x="date", y=[c for c in df_bt.columns if c != "date"],
                    labels={"value": "Valore Indiciato (Base 100)", "date": "Data", "variable": "Strategia"},
                    title="Confronto Curve di Equity Storiche (Base 100)",
                    color_discrete_sequence=["#58a6ff", "#00e676", "#ff9900", "#bc8cff"],
                    template="plotly_dark", height=420
                )
                fig_bt.update_traces(
                    line=dict(width=2.2),
                    hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>%{fullData.name}: %{y:.2f}<extra></extra>"
                )
                fig_bt.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)")
                )
                apply_plotly_theme(fig_bt)
                st.plotly_chart(fig_bt, use_container_width=True)

    else:
        st.info("Dati di ottimizzazione di Markowitz non disponibili.")

# ── TAB 2: TAIL COPULA & KELLY SIZING ────────────────────────────
elif active_quant_tab == "🧬 Tail Copula & Kelly":
    if not has_portfolio:
        st.warning("⚠️ Carica prima un portafoglio per calcolare le Copule di Coda e il dimensionamento di Kelly.")
    else:
        col_cop_h1, col_cop_h2 = st.columns([3.0, 1.3])
        with col_cop_h1:
            st.markdown("### 🧬 Modelli di Dipendenza di Coda (Tail Copula) & Kelly Criterion")
            st.caption("Quantifica il rischio di crash congiunto asimmetrico (Clayton/Gumbel Copulas) e calcola il dimensionamento matematico ottimale delle posizioni (Half-Kelly).")
        with col_cop_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal(
                "ℹ️ Guida Metodologica: Tail Copula & Criterio di Kelly",
                """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 1. COS'È</div>
  <div>
    • <b>Dipendenza di Coda (Tail Copulas):</b> Misura quantitativa non lineare della tendenza di due asset a crollare contemporaneamente durante shock sistemici di mercato, superando i limiti della classica correlazione lineare di Pearson.<br>
    • <b>Criterio di Kelly (Trade Sizing):</b> Algoritmo di teoria dell'informazione che determina la percentuale ottimale di capitale da rischiare su ciascuna operazione per massimizzare la crescita geometrica di lungo termine.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 2. COME SI CALCOLA</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px;">
    <b>Lower Tail Dependence:</b> &lambda;<sub>L</sub> = lim<sub>q&rarr;0<sup>+</sup></sub> P(U<sub>j</sub> &le; q | U<sub>i</sub> &le; q) = 2<sup>&minus;1/&theta;</sup> (Clayton)<br>
    <b>Kelly Formula (Discreta):</b> f<sup>*</sup> = [p &middot; (b + 1) &minus; 1] / b &nbsp;&nbsp;|&nbsp;&nbsp; <b>Half-Kelly:</b> f<sup>*</sup><sub>half</sub> = f<sup>*</sup> / 2
  </div>
  <div>dove <i>p</i> è il Win Rate (%), <i>b</i> è il Payoff Ratio (Avg Win / Avg Loss) e <i>f<sup>*</sup></i> è la frazione di capitale ottimale.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 3. A COSA SERVE</div>
  <div>
    • <b>Prevenzione del Crash Contagion:</b> Rileva le coppie di asset che sembrano decorrelate in tempi normali ma perdono completamente la diversificazione durante i crash.<br>
    • <b>Dimensionamento Scientifico:</b> Elimina il sovradimensionamento (overbetting) e azzera il rischio matematico di rovina (Gambler's Ruin).
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ 4. COME VIENE CALCOLATO DA ARGUS</div>
  <div>
    • <b>Copule:</b> ARGUS trasforma i rendimenti storici in ranghi uniformi empirici (CDF) e stima il parametro di copula archimedea &theta; e &lambda;<sub>L</sub> sulla soglia di percentile estremo <i>q</i>.<br>
    • <b>Kelly Simulator:</b> ARGUS estrae in tempo reale dal motore <b>FIFO del Graveyard</b> il Win Rate reale e il Payoff Ratio storico, calcolando il dimensionamento monetario (€) esatto in base allo Stop-Loss inserito.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 5. COME LEGGERLO</div>
  <div>
    • 🚨 <b>&lambda;<sub>L</sub> &ge; 0.30:</b> Allerta Diversification Breakdown (in crollo la correlazione sale verso 1).<br>
    • 🟢 <b>Half-Kelly (Raccomandato):</b> Ottiene il 75% del rendimento geometrico massimo riducendo la volatilità del 50% e proteggendo dai drawdown estremi.<br>
    • ⚠️ <b>Edge &le; 0%:</b> Se l'edge statistico è negativo, il Kelly formula consiglia zero esposizione (non operare).
  </div>
</div>

</div>
""",
                button_label="💡 Guida Copula & Kelly"
            )

        df_returns_all = results.get("returns", pd.DataFrame())
        if df_returns_all.empty or not isinstance(df_returns_all, pd.DataFrame) or df_returns_all.shape[1] < 2:
            df_pr_t = results.get("df_prices", pd.DataFrame())
            if not df_pr_t.empty and "ticker" in df_pr_t.columns:
                piv_t = df_pr_t.pivot(index="price_date", columns="ticker", values="close")
                df_returns_all = piv_t.pct_change().dropna()

        pos = results.get("positions", pd.DataFrame())
        # Filtro per isolare SOLO le posizioni attive attualmente in portafoglio
        if not df_returns_all.empty and not pos.empty:
            active_mask = (pos["qty_net"] > 1e-6) if "qty_net" in pos.columns else pd.Series(True, index=pos.index)
            active_tickers_list = [t for t in pos[active_mask]["ticker"].dropna().unique() if not str(t).endswith("=X")]
            common_active = [c for c in df_returns_all.columns if c in active_tickers_list]
            if len(common_active) >= 2:
                df_returns_all = df_returns_all[common_active]

        # ── SEZIONE 1: TAIL COPULA MATRIX ──
        section("1. 🧬 Matrice di Dipendenza di Coda Asimmetrica (Tail Copulas)")
        st.caption("Quantifica la dipendenza non lineare e la probabilità di shock simultaneo sulle code di distribuzione.")

        col_cop_q, col_cop_k1, col_cop_k2, col_cop_k3 = st.columns([1.4, 1, 1, 1])
        with col_cop_q:
            q_thresh = st.slider(
                "Soglia Percentile di Coda (q):",
                min_value=0.01,
                max_value=0.15,
                value=0.05,
                step=0.01,
                help="q=0.05 analizza il 5% delle giornate di mercato peggiori (Tail Risk al 95%)."
            )
        
        copula_res = compute_tail_copula_matrix(df_returns_all, quantile_threshold=q_thresh)
        mean_tl = copula_res.get('mean_tail_dependence', 0.0)
        df_l = copula_res.get("lambda_lower_df", pd.DataFrame())
        df_u = copula_res.get("lambda_upper_df", pd.DataFrame())
        df_asym = copula_res.get("asymmetry_df", pd.DataFrame())
        contagion = copula_res.get("contagion_pairs", [])
        
        if not df_u.empty:
            upper_vals = df_u.values[np.triu_indices_from(df_u.values, k=1)]
            mean_tu = float(np.mean(upper_vals)) if len(upper_vals) > 0 else 0.0
        else:
            mean_tu = 0.0

        with col_cop_k1:
            metric_card(
                "Dipendenza Coda Inferiore (λ_L)",
                f"{mean_tl:.3f}",
                delta="Rischio Crash Congiunto",
                positive=(mean_tl < 0.20),
                help_text="Media della probabilità di crash congiunto tra tutte le coppie di asset durante shock ribassisti."
            )
        with col_cop_k2:
            metric_card(
                "Dipendenza Coda Superiore (λ_U)",
                f"{mean_tu:.3f}",
                delta="Co-Boom Rialzista",
                positive=True,
                help_text="Media della probabilità di rally congiunto tra tutte le coppie di asset durante fasi di espansione."
            )
        with col_cop_k3:
            metric_card(
                "Coppie ad Alto Contagio (λ_L ≥ 0.30)",
                f"{len(contagion)}",
                delta="Breakdown Diversificazione" if len(contagion) > 0 else "Nessun Alert Critico",
                positive=(len(contagion) == 0),
                help_text="Numero di coppie di asset che perdono la diversificazione durante i crolli di mercato."
            )

        st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
        tab_cl, tab_cu, tab_asym = st.tabs([
            "🔻 Lower Tail Dependence (λ_L - Rischio Crash)",
            "🔺 Upper Tail Dependence (λ_U - Co-Boom)",
            "⚖️ Matrice Asimmetria di Coda (λ_L - λ_U)"
        ])
        
        n_assets = len(df_l) if not df_l.empty else 0
        show_matrix_text = (n_assets <= 12)
        
        with tab_cl:
            if not df_l.empty:
                fig_cl = px.imshow(
                    df_l,
                    color_continuous_scale=[[0.0, "#0f172a"], [0.4, "#d97706"], [1.0, "#ef4444"]],
                    zmin=0.0, zmax=1.0,
                    text_auto=".2f" if show_matrix_text else False,
                    labels={"x": "Asset", "y": "Asset", "color": "λ_L"}
                )
                fig_cl.update_traces(
                    hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>🔻 Lower Tail Copula (λ_L): <b>%{z:.3f}</b><br><i>Probabilità di crash simultaneo nei sell-off</i><extra></extra>"
                )
                fig_cl.update_layout(
                    height=480, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=20, b=10),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=11, family="monospace")),
                    yaxis=dict(tickfont=dict(size=11, family="monospace"))
                )
                apply_plotly_theme(fig_cl)
                st.plotly_chart(fig_cl, use_container_width=True)

        with tab_cu:
            if not df_u.empty:
                fig_cu = px.imshow(
                    df_u,
                    color_continuous_scale=[[0.0, "#0f172a"], [0.4, "#0284c7"], [1.0, "#22c55e"]],
                    zmin=0.0, zmax=1.0,
                    text_auto=".2f" if show_matrix_text else False,
                    labels={"x": "Asset", "y": "Asset", "color": "λ_U"}
                )
                fig_cu.update_traces(
                    hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>🔺 Upper Tail Copula (λ_U): <b>%{z:.3f}</b><br><i>Probabilità di co-boom rialzista simultaneo</i><extra></extra>"
                )
                fig_cu.update_layout(
                    height=480, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=20, b=10),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=11, family="monospace")),
                    yaxis=dict(tickfont=dict(size=11, family="monospace"))
                )
                apply_plotly_theme(fig_cu)
                st.plotly_chart(fig_cu, use_container_width=True)

        with tab_asym:
            if not df_asym.empty:
                fig_asym = px.imshow(
                    df_asym,
                    color_continuous_scale=[[0.0, "#22c55e"], [0.5, "#0f172a"], [1.0, "#ef4444"]],
                    zmin=-0.5, zmax=0.5,
                    text_auto=".2f" if show_matrix_text else False,
                    labels={"x": "Asset", "y": "Asset", "color": "Δ (λ_L - λ_U)"}
                )
                fig_asym.update_traces(
                    hovertemplate="<b>Coppia: %{x} ↔ %{y}</b><br>⚖️ Asimmetria Coda: <b>%{z:+.3f}</b><br><i>Valori positivi indicano maggiore rischio di crash congiunto rispetto ai rally</i><extra></extra>"
                )
                fig_asym.update_layout(
                    height=480, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=20, b=10),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=11, family="monospace")),
                    yaxis=dict(tickfont=dict(size=11, family="monospace"))
                )
                apply_plotly_theme(fig_asym)
                st.plotly_chart(fig_asym, use_container_width=True)

        # Tabella Coppie a Rischio Contagio & Indice di Rottura della Diversificazione
        contagion = copula_res.get("contagion_pairs", [])
        if contagion:
            col_cont_h1, col_cont_h2 = st.columns([3.5, 0.9])
            with col_cont_h1:
                st.markdown(r"##### ⚠️ Alert Coppie ad Alto Contagio di Coda ($\lambda_L \ge 0.30$)")
                st.caption("Queste coppie mostrano un picco di correlazione durante i crolli di mercato (*'In a crisis, all correlations go to 1'*), azzerando l'effetto protettivo della diversificazione.")
            
            df_cont = pd.DataFrame(contagion).rename(columns={
                "pair": "Coppia Asset", "lambda_lower": "Lower Tail (λ_L)",
                "lambda_upper": "Upper Tail (λ_U)", "asymmetry": "Asimmetria di Coda", "risk_level": "Livello Rischio"
            })

            with col_cont_h2:
                st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
                csv_cont = df_cont.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_cont, file_name="coppie_contagio_tail_risk.csv", mime="text/csv", use_container_width=True)

            cont_cfg = {
                "Coppia Asset": st.column_config.TextColumn("Coppia Asset", width="medium"),
                "Lower Tail (λ_L)": st.column_config.ProgressColumn("Lower Tail (λ_L)", format="%.3f", min_value=0.0, max_value=1.0),
                "Upper Tail (λ_U)": st.column_config.ProgressColumn("Upper Tail (λ_U)", format="%.3f", min_value=0.0, max_value=1.0),
                "Asimmetria di Coda": st.column_config.NumberColumn("Asimmetria (λ_L - λ_U)", format="%+.3f"),
                "Livello Rischio": st.column_config.TextColumn("Livello Rischio", width="small")
            }
            st.dataframe(df_cont, column_config=cont_cfg, use_container_width=True, hide_index=True)

        st.divider()

        # ── SEZIONE 2: KELLY CRITERION SIZING ──
        st.markdown('<div style="margin-top: 25px;"></div>', unsafe_allow_html=True)
        section("2. 🎯 Ottimizzazione dei Pesi con Criterio di Kelly (Half-Kelly)")
        st.caption("Confronto tra pesi effettivi di portafoglio e allocazione ottimale Half-Kelly per la massimizzazione del tasso di crescita del capitale.")

        col_k_rf, col_k_info = st.columns([2, 4])
        with col_k_rf:
            rf_rate = st.slider("Tasso Risk-Free Annuo (Rf %):", 0.0, 6.0, 2.0, 0.5) / 100.0
        
        # Mappa pesi attuali solo posizioni attive
        pos_df = results.get("positions", pd.DataFrame())
        cur_w_k = {}
        if not pos_df.empty and "ticker" in pos_df.columns:
            active_pos = pos_df[pos_df["qty_net"] > 1e-6] if "qty_net" in pos_df.columns else pos_df
            w_col = "weight_pct" if "weight_pct" in active_pos.columns else ("weight" if "weight" in active_pos.columns else None)
            if w_col:
                cur_w_k = dict(zip(active_pos["ticker"], active_pos[w_col] / (100.0 if w_col == "weight_pct" else 1.0)))

        df_kelly = compute_kelly_criterion_sizing(df_returns_all, current_weights=cur_w_k, risk_free_rate=rf_rate)
        
        if not df_kelly.empty:
            col_k_f1, col_k_f2, col_k_f3 = st.columns([2.0, 1.3, 0.9])
            with col_k_f1:
                search_k = st.text_input("🔍 Cerca Ticker:", placeholder="Filtra per Ticker (es. AAPL, BTC, ETH, GOOGL)...", key="search_kelly_ticker")
            with col_k_f2:
                filter_k_diag = st.selectbox("🏷️ Diagnostica Allocazione:", ["Tutti gli Stati", "🔴 Sovra-Allocati", "🟢 Sotto-Allocati", "⚪ Equilibrati", "⛔ Zero Edge"], key="filter_kelly_diag")

            df_k_filt = df_kelly.copy()
            if search_k:
                df_k_filt = df_k_filt[df_k_filt["Ticker"].astype(str).str.contains(search_k.strip(), case=False, na=False)]
            if filter_k_diag == "🔴 Sovra-Allocati":
                df_k_filt = df_k_filt[df_k_filt["Stato Allocazione"].astype(str).str.contains("Sovra", case=False, na=False)]
            elif filter_k_diag == "🟢 Sotto-Allocati":
                df_k_filt = df_k_filt[df_k_filt["Stato Allocazione"].astype(str).str.contains("Sotto", case=False, na=False)]
            elif filter_k_diag == "⚪ Equilibrati":
                df_k_filt = df_k_filt[df_k_filt["Stato Allocazione"].astype(str).str.contains("Equilibrat", case=False, na=False)]
            elif filter_k_diag == "⛔ Zero Edge":
                df_k_filt = df_k_filt[df_k_filt["Stato Allocazione"].astype(str).str.contains("Nessun|Zero", case=False, na=False)]

            with col_k_f3:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                csv_k = df_k_filt.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Scarica CSV",
                    data=csv_k,
                    file_name="kelly_criterion_sizing.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            if df_k_filt.empty:
                st.info("ℹ️ Nessun asset corrisponde ai criteri di filtro selezionati.")
            else:
                # Tabella Interattiva con Sorting su ogni colonna e Column Config
                df_k_interactive = pd.DataFrame({
                    "Ticker": df_k_filt["Ticker"],
                    "Rendimento Annuo (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Rendimento Annuo"]],
                    "Volatilità Annua (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Volatilità Annua"]],
                    "Win Rate (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Win Rate"]],
                    "Win/Loss (B)": df_k_filt["Win/Loss Ratio"],
                    "Peso Attuale (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Peso Attuale"]],
                    "Target Kelly (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Half-Kelly (Target)"]],
                    "Leva Full Kelly (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Full Kelly"]],
                    "Diagnostica": df_k_filt["Stato Allocazione"]
                })

                kelly_cfg = {
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Rendimento Annuo (%)": st.column_config.NumberColumn("Rendimento Annuo", format="%+.2f%%"),
                    "Volatilità Annua (%)": st.column_config.NumberColumn("Volatilità Annua", format="%.2f%%"),
                    "Win Rate (%)": st.column_config.ProgressColumn("Win Rate", format="%.1f%%", min_value=0.0, max_value=100.0),
                    "Win/Loss (B)": st.column_config.TextColumn("Payoff (B)", width="small"),
                    "Peso Attuale (%)": st.column_config.NumberColumn("Peso Attuale", format="%.2f%%"),
                    "Target Kelly (%)": st.column_config.ProgressColumn("Target Kelly", format="%.2f%%", min_value=0.0, max_value=100.0),
                    "Leva Full Kelly (%)": st.column_config.NumberColumn("Leva Full Kelly", format="%.2f%%"),
                    "Diagnostica": st.column_config.TextColumn("Diagnostica Allocazione", width="medium")
                }

                st.dataframe(
                    df_k_interactive,
                    column_config=kelly_cfg,
                    use_container_width=True,
                    hide_index=True
                )

                # Grafico a barre comparative: Peso Attuale vs Half-Kelly Target
                df_k_plot = pd.DataFrame({
                    "Ticker": df_k_filt["Ticker"],
                    "Peso Attuale (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Peso Attuale"]],
                    "Half-Kelly Target (%)": [float(str(w).replace("%", "").replace("+", "")) for w in df_k_filt["Half-Kelly (Target)"]]
                })

                fig_k_bar = go.Figure()
                fig_k_bar.add_trace(go.Bar(
                    x=df_k_plot["Ticker"],
                    y=df_k_plot["Peso Attuale (%)"],
                    name="⭐ Peso Attuale",
                    marker=dict(color="#58a6ff", line=dict(color="rgba(255,255,255,0.1)", width=1)),
                    hovertemplate="<b>%{x}</b><br>Peso Attuale: <b>%{y:.2f}%</b><extra></extra>"
                ))
                fig_k_bar.add_trace(go.Bar(
                    x=df_k_plot["Ticker"],
                    y=df_k_plot["Half-Kelly Target (%)"],
                    name="🎯 Target Kelly Normalizzato",
                    marker=dict(color="#ff9900", line=dict(color="rgba(255,153,0,0.4)", width=1)),
                    hovertemplate="<b>%{x}</b><br>Target Kelly: <b>%{y:.2f}%</b><extra></extra>"
                ))
                fig_k_bar.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    barmode="group",
                    height=340,
                    margin=dict(l=10, r=10, t=30, b=30),
                    yaxis=dict(title="Allocazione (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    xaxis=dict(title=None, tickangle=-45, tickfont=dict(size=11, family="monospace")),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11.5))
                )
                apply_plotly_theme(fig_k_bar)
                st.plotly_chart(fig_k_bar, use_container_width=True)

        # ── SEZIONE 3: SIMULATORE INTERATTIVO DI TRADE SIZING (KELLY) ─
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("#### ⚖️ Simulatore Interattivo Trade Sizing (Kelly Criterion)")
        st.caption("Calcola il dimensionamento matematico ideale di una nuova posizione (o strategia) per massimizzare la crescita geometrica del capitale a zero rischio di rovina statistica.")

        from core.advanced_quant import compute_interactive_trade_kelly
        from core.closed_trades import compute_closed_trades_journal

        # Pre-popola con statistiche reali del Graveyard se disponibili
        gy_stats = compute_closed_trades_journal(
            df_tx=results.get("df_tx"),
            df_prices=results.get("df_prices"),
            df_positions=results.get("positions"),
            is_sandbox=bool(results.get("is_sandbox"))
        )
        real_wr = gy_stats.get("win_rate_pct", 55.0) if gy_stats.get("has_closed_trades") else 55.0
        real_pr = gy_stats.get("payoff_ratio", 1.8) if gy_stats.get("has_closed_trades") else 1.8

        with st.expander("⚙️ Parametri della Nuova Idea di Trading", expanded=True):
            col_k_in1, col_k_in2, col_k_in3, col_k_in4 = st.columns(4)
            with col_k_in1:
                k_win_rate = st.slider("Probabilità di Successo (Win Rate %):", 10.0, 90.0, float(real_wr), 1.0, help="Percentuale storica o stimata di trade vincenti.")
            with col_k_in2:
                k_payoff = st.slider("Payoff Ratio (Avg Win / Avg Loss):", 0.5, 5.0, float(real_pr), 0.1, help="Rapporto tra profitto medio su trade vincenti e perdita media su trade perdenti.")
            with col_k_in3:
                k_capital = st.number_input("Capitale di Riferimento Portafoglio (€):", min_value=1000.0, value=100000.0, step=5000.0)
            with col_k_in4:
                k_sl = st.slider("Stop-Loss Previsto (% sull'asset):", 1.0, 25.0, 5.0, 0.5, help="Distanza percentuale del livello di stop loss dal prezzo di ingresso.")

        k_res = compute_interactive_trade_kelly(k_win_rate, k_payoff, k_capital, k_sl)

        col_kr1, col_kr2, col_kr3, col_kr4 = st.columns(4)
        with col_kr1:
            metric_card("🎯 Half-Kelly (Consigliato)", f"{k_res['half_kelly_pct']:.2f}%", f"Rischio: € {k_res['risk_half_eur']:,.2f}", True)
        with col_kr2:
            metric_card("🔥 Full Kelly (Massima Leva)", f"{k_res['full_kelly_pct']:.2f}%", f"Rischio: € {k_res['risk_full_eur']:,.2f}", False)
        with col_kr3:
            metric_card("🛡️ Quarter-Kelly (Prudente)", f"{k_res['quarter_kelly_pct']:.2f}%", f"Rischio: € {k_res['risk_quarter_eur']:,.2f}", True)
        with col_kr4:
            metric_card("📦 Nozionale Suggerito (Half-K)", f"€ {k_res['pos_size_half_eur']:,.2f}", f"Con Stop al {k_sl:.1f}%", True)

        st.info(f"💡 **Edge Matematico della Strategia:** **{k_res['edge_pct']:+.2f}%** | **Tasso di Crescita Geometrico Teorico:** **{k_res['expected_growth_rate']:+.3f}% per operazione** | Profilo di Rischio Drawdown: **{k_res['drawdown_risk']}**")

# ── TAB 3: SIMULAZIONI STOCASTICHE ────────────────────────────
elif active_quant_tab == "🎲 Monte Carlo & Merton":
    col_head_mc1, col_head_mc2 = st.columns([3.0, 1.3])
    with col_head_mc1:
        st.markdown("### 🎲 Simulatore Stocastico Monte Carlo Multivariato & Clustering")
        st.caption("Proietta 3.000 traiettorie causali del portafoglio nel tempo tramite Decomposizione di Cholesky, con supporto per regimi di stress, distribuzioni a code grasse (Student-t) e metriche di Tail Risk (VaR & CVaR).")
    with col_head_mc2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("📚 Guida alla Simulazione Monte Carlo Multivariata", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Simulatore Monte Carlo Multivariato</div>
  <div>Un generatore di percorsi stocastici casuali che simula migliaia di possibili evoluzioni future del valore di portafoglio, preservando la reale matrice di covarianza storica tra tutti i titoli componenti.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Decomposizione di Cholesky & Code Grasse (Student-t)</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Fattorizzazione di Cholesky:</b> &Sigma; = <b>L &middot; L<sup>T</sup></b> per generare shock correlati <b>&epsilon;<sub>corr</sub> = L &middot; z</b><br>
    • <b>Distribuzione Student-t (&nu; = 5):</b> Introduce code pesanti per simulare cigni neri e shock estremi
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Stimare la probabilità di perdita del capitale a 1, 2 o 3 anni, calcolare il VaR/CVaR terminale e valutare la resilienza del portafoglio sotto stress di volatilità o calo del drift.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS esegue 3.000 iterazioni stocastiche vettorializzate con NumPy, proiettando percentili 5°, 25°, 50° (mediana), 75° e 95° e aggregando i cluster K-Means degli asset.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>
    • <b>Linea Blu Centrale:</b> Traiettoria mediana attesa (scenario base).<br>
    • <b>Banda Ombreggiata (5° - 95° percentile):</b> Intervallo di confidenza al 90% del controvalore finale.<br>
    • <b>Probabilità di Perdita (%):</b> Quota di simulazioni che chiudono sotto il capitale iniziale.
  </div>
</div>

</div>
""", button_label="💡 Guida Monte Carlo")

    try:
        from core.risk_engine import run_advanced_monte_carlo_simulation
    except ImportError:
        import importlib
        import core.risk_engine
        importlib.reload(core.risk_engine)
        from core.risk_engine import run_advanced_monte_carlo_simulation

    if not has_portfolio or results is None:
        st.warning("⚠️ Carica prima un portafoglio nella Control Room per eseguire le simulazioni Monte Carlo & Merton.")
    else:
        with st.expander("⚙️ Pannello di Controllo Scenario Monte Carlo & Regimi di Stress", expanded=True):
            mc_c1, mc_c2, mc_c3, mc_c4 = st.columns(4)
            with mc_c1:
                horizon_opt = st.selectbox(
                    "Orizzonte Temporale Proiettato:",
                    options=[63, 126, 252, 504, 756],
                    index=2,
                    format_func=lambda x: {63: "3 Mesi (63 gg)", 126: "6 Mesi (126 gg)", 252: "1 Anno (252 gg)", 504: "2 Anni (504 gg)", 756: "3 Anni (756 gg)"}[x]
                )
            with mc_c2:
                vol_mult = st.slider("Moltiplicatore Volatilità (Stress):", 0.50, 2.50, 1.00, 0.25, help="1.0x = Condizioni Normali; 1.5x - 2.0x = Regime di Alta Volatilità / Crisi")
            with mc_c3:
                drift_shift = st.slider("Aggiustamento Trend / Drift Anno (%):", -20.0, 20.0, 0.0, 1.0, help="Shift % sul rendimento atteso anno")
            with mc_c4:
                dist_type = st.radio("Distribuzione Shock:", ["Gaussiana (Normale)", "Student-t (Code Grasse)"], horizontal=True)
                dist_key = "student_t" if "Student-t" in dist_type else "gaussian"

        # Esecuzione della Simulazione Monte Carlo
        mc_adv = run_advanced_monte_carlo_simulation(
            results_dict=results,
            horizon_days=horizon_opt,
            volatility_multiplier=vol_mult,
            drift_shift_pct=drift_shift,
            distribution_type=dist_key,
            n_simulations=3000
        )

        if mc_adv:
            # Head KPI Cards
            mk1, mk2, mk3, mk4, mk5 = st.columns(5)
            with mk1:
                metric_card(
                    "Valore Iniziale",
                    fmt_eur_it(mc_adv['initial_portfolio_value']),
                    "Capitale Base",
                    True,
                    help_text="Valore attuale complessivo del portafoglio utilizzato come base di simulazione."
                )
            with mk2:
                metric_card(
                    "Mediana Attesa (1Y)",
                    fmt_eur_it(mc_adv['expected_value_median']),
                    f"Rendimento: {mc_adv['expected_return_median_pct']:+.2f}%",
                    mc_adv['expected_return_median_pct'] >= 0,
                    help_text="Valore mediano del portafoglio al termine dell'orizzonte temporale."
                )
            with mk3:
                metric_card(
                    "VaR 95% (Rischio)",
                    fmt_eur_it(mc_adv['var_95_val_eur']),
                    f"Perdita Max: -{mc_adv['var_95_pct']:.2f}%",
                    False,
                    help_text="Perdita massima stimata al 95% di confidenza statistica."
                )
            with mk4:
                metric_card(
                    "CVaR 95% (Shortfall)",
                    fmt_eur_it(mc_adv['cvar_95_val_eur']),
                    f"Perdita Media: -{mc_adv['cvar_95_pct']:.2f}%",
                    False,
                    help_text="Expected Shortfall: perdita media attesa qualora si verifichi uno shock oltre il VaR 95%."
                )
            with mk5:
                metric_card(
                    "Probabilità Profitto",
                    f"{mc_adv['prob_profit_pct']:.1f}%",
                    "3.000 Simulazioni",
                    mc_adv['prob_profit_pct'] >= 50.0,
                    help_text="Frazione di percorsi stocastici che registrano un valore finale superiore al capitale iniziale."
                )

            st.divider()

            # Grafico a Nastro (Ribbon & Path Generator Chart)
            st.markdown("#### 📈 Proiezione Stocastica delle Traiettorie nel Tempo (Fan / Ribbon Chart)")
            st.caption(f"Fascio stocastico di 3.000 traiettorie simulate su orizzonte di **{horizon_opt} giorni** ({dist_type}) con intervalli di confidenza percentili (P01 – P99).")
            
            t_days = mc_adv["time_axis"]
            fig_fan = go.Figure()

            # 80 sample paths traslucidi per evidenziare il fascio esteso
            sample_paths = mc_adv["sample_paths"]
            for s_idx in range(sample_paths.shape[1]):
                fig_fan.add_trace(go.Scatter(
                    x=t_days, y=sample_paths[:, s_idx],
                    mode="lines",
                    line=dict(color="rgba(72, 149, 239, 0.07)", width=1),
                    showlegend=False,
                    hoverinfo="skip"
                ))

            # Fasce a nastro (Ribbon Fills)
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p99_path"], mode="lines", name="P99 (Scenario Ultra-Rialzista)",
                line=dict(color="rgba(0, 255, 153, 0.6)", width=1.5, dash="dot"),
                hovertemplate="<b>P99 (Scenario Ultra-Rialzista)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p75_path"], mode="lines", name="P75 (Scenario Positivo)",
                line=dict(color="rgba(0, 204, 255, 0.5)", width=1), fill="tonexty", fillcolor="rgba(0, 255, 153, 0.05)",
                hovertemplate="<b>P75 (Scenario Positivo)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p50_path"], mode="lines", name="P50 (Mediana Attesa)",
                line=dict(color="#00ff99", width=3),
                hovertemplate="<b>P50 (Mediana Attesa)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p25_path"], mode="lines", name="P25 (Scenario Conservativo)",
                line=dict(color="rgba(255, 204, 0, 0.5)", width=1), fill="tonexty", fillcolor="rgba(255, 204, 0, 0.05)",
                hovertemplate="<b>P25 (Scenario Conservativo)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p05_path"], mode="lines", name="P05 (VaR 95%)",
                line=dict(color="#ff9900", width=2, dash="dash"),
                hovertemplate="<b>P05 (VaR 95%)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=mc_adv["p01_path"], mode="lines", name="P01 (Worst Case / VaR 99%)",
                line=dict(color="#ff3333", width=2.5, dash="dash"),
                hovertemplate="<b>P01 (Worst Case / VaR 99%)</b><br>Giorno: %{x}<br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
            ))

            fig_fan.update_layout(
                xaxis_title="Giorni di Contrattazione (Trading Days)",
                yaxis_title="Valore stimato di Portafoglio (€)",
                template="plotly_dark",
                height=480,
                margin=dict(t=50, b=40, l=55, r=25),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0.0,
                    bgcolor="rgba(22, 27, 34, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.12)",
                    borderwidth=1,
                    font=dict(size=11, color="#ffffff")
                )
            )
            apply_plotly_theme(fig_fan)
            st.plotly_chart(fig_fan, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

            # ── RIGA 1: ISTOGRAMMA DEL VALORE FINALE & SOGLIE DI RISCHIO ───
            st.markdown("#### 📊 Istogramma del Valore Finale & Soglie di Rischio (VaR / CVaR)")
            st.caption("Distribuzione di frequenza empirica del capitale stimato a fine orizzonte con indicazione del capitale iniziale, della mediana attesa e dei livelli di VaR 95% e CVaR 95%.")
            
            final_vals = mc_adv["final_values"]
            fig_hist_mc = go.Figure()
            
            fig_hist_mc.add_trace(go.Histogram(
                x=final_vals, nbinsx=55, name="Valore Finale",
                marker=dict(
                    color="rgba(0, 243, 255, 0.45)",
                    line=dict(color="#00f3ff", width=0.8)
                ),
                hovertemplate="<b>Capitale Finale: € %{x:,.0f}</b><br>Frequenza: %{y} simulazioni<extra></extra>"
            ))

            init_v = mc_adv["initial_portfolio_value"]
            med_v = mc_adv["expected_value_median"]
            var95_v = init_v - mc_adv["var_95_val_eur"]
            cvar95_v = init_v - mc_adv["cvar_95_val_eur"]

            fig_hist_mc.add_vline(
                x=cvar95_v, line_dash="dot", line_color="#ff3333", line_width=2,
                annotation_text=f"<b>CVaR 95%</b>: {fmt_eur_it(cvar95_v)}", 
                annotation_position="top left",
                annotation=dict(bgcolor="rgba(22, 27, 34, 0.90)", bordercolor="#ff3333", borderwidth=1, borderpad=4, font=dict(color="#ff5252", size=11))
            )
            fig_hist_mc.add_vline(
                x=var95_v, line_dash="dash", line_color="#ff9900", line_width=2,
                annotation_text=f"<b>VaR 95%</b>: {fmt_eur_it(var95_v)}", 
                annotation_position="top left",
                annotation=dict(bgcolor="rgba(22, 27, 34, 0.90)", bordercolor="#ff9900", borderwidth=1, borderpad=4, font=dict(color="#ffab40", size=11), yshift=-35)
            )
            fig_hist_mc.add_vline(
                x=init_v, line_dash="dash", line_color="#ffffff", line_width=1.8,
                annotation_text=f"<b>Capitale Iniziale</b>: {fmt_eur_it(init_v)}", 
                annotation_position="top right",
                annotation=dict(bgcolor="rgba(22, 27, 34, 0.90)", bordercolor="rgba(255, 255, 255, 0.35)", borderwidth=1, borderpad=4, font=dict(color="#ffffff", size=11))
            )
            fig_hist_mc.add_vline(
                x=med_v, line_dash="solid", line_color="#00ff99", line_width=2.2,
                annotation_text=f"<b>Mediana Attesa</b>: {fmt_eur_it(med_v)}", 
                annotation_position="top right",
                annotation=dict(bgcolor="rgba(22, 27, 34, 0.90)", bordercolor="#00ff99", borderwidth=1, borderpad=4, font=dict(color="#00e676", size=11), yshift=-35)
            )

            fig_hist_mc.update_layout(
                xaxis_title="Valore Finale Stimato di Portafoglio (€)",
                yaxis_title="Frequenza Simulazioni",
                template="plotly_dark", height=415,
                margin=dict(t=45, b=40, l=55, r=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_hist_mc)
            st.plotly_chart(fig_hist_mc, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

            # ── RIGA 2: MATRICE DELLE PROBABILITÀ & RISK PROFILE ───────────
            col_mo_h1, col_mo_h2 = st.columns([3.5, 0.9])
            with col_mo_h1:
                st.markdown("#### 🎯 Matrice delle Probabilità & Risk Profile")
                st.caption("Valutazione quantitativa delle probabilità di successo e degli scenari di stress drawdown su 3.000 path simulati.")
            
            df_odds = pd.DataFrame([
                {"Scenario Stocastico": "🟢 Probabilità di Profitto", "Probabilità / Valore": f"{mc_adv['prob_profit_pct']:.1f}%", "Condizione": "Rendimento Finale > 0%"},
                {"Scenario Stocastico": "🚀 Target Moderato (≥ +10%)", "Probabilità / Valore": f"{mc_adv['prob_gain_10_pct']:.1f}%", "Condizione": "Guadagno Finale ≥ +10%"},
                {"Scenario Stocastico": "🔥 Target Rialzista (≥ +20%)", "Probabilità / Valore": f"{mc_adv['prob_gain_20_pct']:.1f}%", "Condizione": "Guadagno Finale ≥ +20%"},
                {"Scenario Stocastico": "⚠️ Rischio Ribasso (≤ -10%)", "Probabilità / Valore": f"{mc_adv['prob_loss_10_pct']:.1f}%", "Condizione": "Perdita Finale ≤ -10%"},
                {"Scenario Stocastico": "🔴 Rischio Crollo (≤ -20%)", "Probabilità / Valore": f"{mc_adv['prob_loss_20_pct']:.1f}%", "Condizione": "Perdita Finale ≤ -20%"},
                {"Scenario Stocastico": "📉 Max Drawdown Simulato Medio", "Probabilità / Valore": f"{mc_adv['avg_max_drawdown_pct']:.2f}%", "Condizione": "Perdita massima media registrata lungo il path"},
                {"Scenario Stocastico": "💥 Max Drawdown Simulato Worst 1%", "Probabilità / Valore": f"{mc_adv['p99_max_drawdown_pct']:.2f}%", "Condizione": "Peggior drawdown nell'1% dei percorsi estremi"}
            ])

            with col_mo_h2:
                st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
                csv_odds = df_odds.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_odds, file_name="monte_carlo_odds_matrix.csv", mime="text/csv", use_container_width=True)

            odds_cfg = {
                "Scenario Stocastico": st.column_config.TextColumn("Scenario Stocastico", width="medium"),
                "Probabilità / Valore": st.column_config.TextColumn("Probabilità / Valore", width="small"),
                "Condizione": st.column_config.TextColumn("Condizione di Verifica", width="large")
            }
            st.dataframe(df_odds, column_config=odds_cfg, use_container_width=True, hide_index=True)

        else:
            st.info("Simulazione Monte Carlo non disponibile per gli asset selezionati.")

        st.divider()

        col_km_h1, col_km_h2 = st.columns([3.2, 1.1])
        with col_km_h1:
            st.markdown("#### 🧬 K-Means Clustering: Segmentazione Asset per Profilo di Rischio & Rendimento")
            st.caption("Algoritmo di machine learning non supervisionato che raggruppa gli asset di portafoglio in cluster omogenei in base al tradeoff tra Volatilità Annua e CAGR.")
        with col_km_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("💡 Guida al K-Means Clustering", r"""
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
  <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 8px;">
    <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 8px;">🧬 K-Means Clustering degli Asset</div>
    <div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Algoritmo di Machine Learning non supervisionato che partiziona gli $N$ asset del portafoglio in $k$ cluster omogenei, minimizzando la varianza interna a ciascun gruppo (Within-Cluster Sum of Squares).</div>
    <div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b>
      <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; font-family: monospace; font-size: 12.5px;">
        argmin_S &Sigma;_{i=1}^k &Sigma;_{x \in S_i} || x - &mu;_i ||^2 &nbsp;|&nbsp; Features: [Volatilità Annua, CAGR]
      </div>
    </div>
    <div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Identificare categorie funzionali di rischio (Core difensivi, Motori di crescita, Outlier volatili) evitando di trattare tutti i titoli azionari o obbligazionari come un blocco monolitico.</div>
    <div style="margin-bottom: 8px;"><b>⚙️ Come viene calcolato da ARGUS:</b> Estrazione della volatilità storica annualizzata (252 gg) e del CAGR per ciascun asset attivo, standardizzazione delle feature e applicazione di k-means (k=2..3 con metodo Elbow/Silhouette).</div>
    <div><b>🔍 Come leggerlo:</b><br>
      • 🟢 <b>Cluster 1 (Core / Bassa Volatilità):</b> Asset stabilizzatori con moderata oscillazione.<br>
      • 🟡 <b>Cluster 2 (Crescita / Rendimento):</b> Titoli ad alto CAGR e profilo di rischio equilibrato.<br>
      • 🔴 <b>Cluster 3 (Alta Volatilità / Outlier):</b> Asset speculativi o fortemente oscillanti da monitorare.
    </div>
  </div>
</div>
""", button_label="💡 Come funziona K-Means?")

        # Fallback computazionale dinamico se clusters non è presente o è vuoto
        if not clusters or len(clusters) == 0:
            df_returns_all = results.get("df_returns", pd.DataFrame())
            df_prices_all = results.get("df_prices", pd.DataFrame())
            pos_active = results.get("positions", pd.DataFrame())
            
            # 1. Prova di calcolo da df_returns usando SOLO asset attivi
            if isinstance(df_returns_all, pd.DataFrame) and not df_returns_all.empty:
                candidate_tickers = list(active_tickers_set) if active_tickers_set else [t for t in df_returns_all.columns if not str(t).endswith("=X")]
                common_t = [t for t in candidate_tickers if t in df_returns_all.columns and not str(t).endswith("=X")]
                if len(common_t) >= 2:
                    v_rets = df_returns_all[common_t].replace([np.inf, -np.inf], np.nan).dropna(how="all")
                    v_rets = v_rets.clip(lower=-0.75, upper=2.0)
                    vol_s = (v_rets.std() * np.sqrt(252)).clip(0.001, 3.0)
                    mean_r = v_rets.mean().clip(lower=-0.05, upper=0.05)
                    cagr_s = ((1 + mean_r) ** 252 - 1).clip(-0.90, 5.0)
                    f_df = pd.DataFrame({'volatility': vol_s, 'cagr': cagr_s})
                    f_df = f_df.replace([np.inf, -np.inf], np.nan).dropna()
                    f_df = f_df[np.isfinite(f_df).all(axis=1)]
                    f_df.index.name = "ticker"
                    if len(f_df) >= 2:
                        try:
                            from sklearn.cluster import KMeans
                            X = f_df[['volatility', 'cagr']].values
                            std_X = X.std(axis=0)
                            std_X[std_X == 0] = 1.0
                            X_scaled = (X - X.mean(axis=0)) / std_X
                            n_c = min(3, len(f_df))
                            km = KMeans(n_clusters=n_c, random_state=42, n_init=10)
                            f_df['cluster'] = km.fit_predict(X_scaled)
                            clusters = f_df.reset_index().to_dict(orient="records")
                        except Exception:
                            clusters = []
            
            # 2. Prova di calcolo da df_prices se df_returns era vuoto
            if (not clusters or len(clusters) == 0) and isinstance(df_prices_all, pd.DataFrame) and not df_prices_all.empty and "ticker" in df_prices_all.columns and "close" in df_prices_all.columns:
                cand_p = df_prices_all[df_prices_all["ticker"].isin(active_tickers_set)] if active_tickers_set else df_prices_all
                p_piv = cand_p.pivot_table(index="price_date", columns="ticker", values="close").pct_change()
                p_piv = p_piv.replace([np.inf, -np.inf], np.nan).dropna(how="all").clip(lower=-0.75, upper=2.0)
                p_piv = p_piv[[c for c in p_piv.columns if not str(c).endswith("=X") and (not active_tickers_set or c in active_tickers_set)]]
                if not p_piv.empty and len(p_piv.columns) >= 2:
                    vol_s = (p_piv.std() * np.sqrt(252)).clip(0.001, 3.0)
                    mean_p = p_piv.mean().clip(lower=-0.05, upper=0.05)
                    cagr_s = ((1 + mean_p) ** 252 - 1).clip(-0.90, 5.0)
                    f_df = pd.DataFrame({'volatility': vol_s, 'cagr': cagr_s})
                    f_df = f_df.replace([np.inf, -np.inf], np.nan).dropna()
                    f_df = f_df[np.isfinite(f_df).all(axis=1)]
                    f_df.index.name = "ticker"
                    if len(f_df) >= 2:
                        try:
                            from sklearn.cluster import KMeans
                            X = f_df[['volatility', 'cagr']].values
                            std_X = X.std(axis=0)
                            std_X[std_X == 0] = 1.0
                            X_scaled = (X - X.mean(axis=0)) / std_X
                            n_c = min(3, len(f_df))
                            km = KMeans(n_clusters=n_c, random_state=42, n_init=10)
                            f_df['cluster'] = km.fit_predict(X_scaled)
                            clusters = f_df.reset_index().to_dict(orient="records")
                        except Exception:
                            clusters = []

        if clusters and len(clusters) > 0:
            df_cl = pd.DataFrame(clusters)
            if "ticker" not in df_cl.columns and "index" in df_cl.columns:
                df_cl = df_cl.rename(columns={"index": "ticker"})
            elif "ticker" not in df_cl.columns:
                df_cl["ticker"] = [f"Asset {i+1}" for i in range(len(df_cl))]

            # Filtra rigorosamente solo asset aperti
            if active_tickers_set:
                df_cl = df_cl[df_cl["ticker"].isin(active_tickers_set)]
            df_cl = df_cl[~df_cl["ticker"].astype(str).str.endswith("=X")]

            # Sanitizzazione preventiva valori
            df_cl = df_cl.replace([np.inf, -np.inf], np.nan).dropna(subset=["volatility", "cagr"])
            df_cl["volatility"] = pd.to_numeric(df_cl["volatility"], errors="coerce").fillna(0.0)
            df_cl["cagr"] = pd.to_numeric(df_cl["cagr"], errors="coerce").fillna(0.0)

            # Rilevamento scala percentuale basato sulla mediana dei valori (robusto contro outlier)
            is_decimal = float(df_cl["volatility"].median()) < 2.0
            if is_decimal:
                df_cl["volatility"] = df_cl["volatility"] * 100.0
                df_cl["cagr"] = df_cl["cagr"] * 100.0

            df_cl["volatility"] = df_cl["volatility"].clip(lower=0.1, upper=250.0)
            df_cl["cagr"] = df_cl["cagr"].clip(lower=-99.0, upper=500.0)

            # Dynamic meaningful cluster naming based on average volatility
            stats = df_cl.groupby("cluster")[["volatility", "cagr"]].mean()
            sorted_c = stats.sort_values("volatility").index.tolist()
            
            label_map = {}
            for i, cid in enumerate(sorted_c):
                if i == 0:
                    label_map[cid] = "🛡️ Cluster 1: Bassa Volatilità / Core"
                elif i == len(sorted_c) - 1 and len(sorted_c) > 1:
                    label_map[cid] = f"⚡ Cluster {i+1}: Alta Volatilità / Outlier"
                else:
                    label_map[cid] = f"🚀 Cluster {i+1}: Crescita / Moderato"

            df_cl["cluster_label"] = df_cl["cluster"].map(label_map)
            df_cl = df_cl.sort_values(by=["volatility", "cagr"]).reset_index(drop=True)

            # Smart label offsetting to eliminate overlapping text for nearby points
            pos_options = ["top center", "bottom right", "top right", "bottom left", "top left"]
            df_cl["text_pos"] = [pos_options[i % len(pos_options)] for i in range(len(df_cl))]

            fig_cl = go.Figure()
            colors = ["#58a6ff", "#00e676", "#ff9900", "#f85149", "#bc8cff", "#00f3ff"]

            for idx, cl_name in enumerate(df_cl["cluster_label"].unique()):
                sub = df_cl[df_cl["cluster_label"] == cl_name]
                fig_cl.add_trace(go.Scatter(
                    x=sub["volatility"],
                    y=sub["cagr"],
                    mode="markers+text",
                    name=cl_name,
                    text=sub["ticker"],
                    textposition=sub["text_pos"].tolist(),
                    marker=dict(
                        size=14,
                        color=colors[idx % len(colors)],
                        line=dict(width=1.5, color="#ffffff")
                    ),
                    textfont=dict(size=11, color="#e6edf3"),
                    hovertemplate="<b>%{text}</b><br>" + cl_name + "<br>Volatilità Annua: <b>%{x:.2f}%</b><br>CAGR: <b>%{y:.2f}%</b><extra></extra>"
                ))

            # Quadrant reference lines (Medians)
            med_v = float(df_cl["volatility"].median())
            med_r = float(df_cl["cagr"].median())
            fig_cl.add_vline(x=med_v, line_dash="dot", line_color="rgba(255,255,255,0.18)", line_width=1)
            fig_cl.add_hline(y=med_r, line_dash="dot", line_color="rgba(255,255,255,0.18)", line_width=1)

            fig_cl.update_layout(
                xaxis_title="Volatilità Annua % (Rischio)",
                yaxis_title="CAGR % (Rendimento Composto Annuo)",
                template="plotly_dark",
                height=450,
                margin=dict(t=50, b=40, l=55, r=25),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0.0,
                    bgcolor="rgba(22, 27, 34, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.12)",
                    borderwidth=1,
                    font=dict(size=11, color="#ffffff")
                )
            )
            apply_plotly_theme(fig_cl)
            st.plotly_chart(fig_cl, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

            # Tabella Interattiva Dettaglio Cluster
            df_cl_table = pd.DataFrame({
                "Ticker": df_cl["ticker"].astype(str),
                "Segmento Cluster": df_cl["cluster_label"].astype(str),
                "Volatilità Annua %": df_cl["volatility"].astype(float),
                "CAGR %": df_cl["cagr"].astype(float),
                "Sharpe Implicito": ((df_cl["cagr"] - 2.75) / df_cl["volatility"].replace(0, np.nan)).fillna(0.0).round(2)
            })

            col_cl_t1, col_cl_t2, col_cl_t3 = st.columns([2.4, 1.2, 0.9])
            with col_cl_t1:
                st.markdown("##### 📋 Dettaglio Asset per Cluster di Rischio")
            with col_cl_t2:
                search_cl = st.text_input("🔍 Cerca Ticker:", placeholder="Filtra per Ticker...", key="search_km_cluster", label_visibility="collapsed")
            with col_cl_t3:
                csv_cl = df_cl_table.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_cl, file_name="asset_clusters_kmeans.csv", mime="text/csv", use_container_width=True, key="btn_download_kmeans_clusters")

            df_cl_filt = df_cl_table.copy()
            if search_cl:
                df_cl_filt = df_cl_filt[df_cl_filt["Ticker"].str.contains(search_cl.strip(), case=False, na=False)]

            cl_col_config = {
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Segmento Cluster": st.column_config.TextColumn("Segmento Cluster", width="medium"),
                "Volatilità Annua %": st.column_config.NumberColumn("Volatilità Annua %", format="%.2f%%"),
                "CAGR %": st.column_config.NumberColumn("CAGR %", format="%+.2f%%"),
                "Sharpe Implicito": st.column_config.NumberColumn("Sharpe Implicito", format="%.2f")
            }

            st.dataframe(
                df_cl_filt,
                column_config=cl_col_config,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("ℹ️ Il modello K-Means Clustering richiede almeno 2 asset attivi con serie storica dei prezzi per calcolare la segmentazione del profilo rischio/rendimento.")

        st.divider()
        col_head_mer1, col_head_mer2 = st.columns([3.2, 1.1])
        with col_head_mer1:
            st.markdown("#### ⚡ Simulatore Jump-Diffusion di Merton (Shock Stocastici & Tail Risk)")
            st.caption("Modellizzazione stocastica avanzata non-gaussiana che integra salti di Poisson (Crash Shock) per misurare perdite catastrofiche di coda (Fat Tails).")
        with col_head_mer2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("⚡ Guida al Modello Merton Jump-Diffusion", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Processo Jump-Diffusion di Merton (1976)</div>
  <div>Un'estensione del moto browniano geometrico sviluppata dal premio Nobel Robert C. Merton che combina una dinamica continua di diffusione con salti discontinui discreti governati da un processo di Poisson.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Equazione Differenziale Stocastica (SDE)</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12.5px; text-align: center;">
    <b>dS<sub>t</sub></b> = &mu; S<sub>t</sub> dt + &sigma; S<sub>t</sub> dW<sub>t</sub> + (e<sup>Y<sub>t</sub></sup> &minus; 1) S<sub>t</sub> dN<sub>t</sub>
  </div>
  <div>
    • <b>&lambda;:</b> Frequenza media annua di arrivo dei salti (Processo di Poisson <i>N<sub>t</sub></i>)<br>
    • <b>&mu;<sub>J</sub>, &sigma;<sub>J</sub>:</b> Media e deviazione standard logaritmica dell'ampiezza dello shock (<i>Y<sub>t</sub> ~ N(&mu;<sub>J</sub>, &sigma;<sub>J</sub><sup>2</sup>)</i>)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Modellizzare i crash istantanei (Flash Crash, eventi geopolitici, default bancari improvvisi) che i modelli gaussiani standard non possono fisicamente generare.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>Il modulo <code>core/risk_engine.py</code> calibra i salti sui rendimenti storici e calcola la discrepanza percentuale tra il VaR normale e il VaR sotto processo di Merton.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Se il VaR Merton è significativamente più severo del VaR normale, il portafoglio è esposto a grave rischio di salto asimmetrico e richiede strategie di tail hedging.</div>
</div>

</div>
""", button_label="💡 Come funziona Merton Jump-Diffusion?")

        with st.expander("⚙️ Configurazione Parametri Merton Jump Shocks", expanded=False):
            col_mj1, col_mj2, col_mj3 = st.columns(3)
            with col_mj1:
                lambda_in = st.slider("Frequenza Salto Poisson (salti/anno):", 0.1, 5.0, 1.5, 0.1, help="Numero medio di shock improvvisi attesi all'anno")
            with col_mj2:
                mu_j_in = st.slider("Dimensione Media Salto (%)", -30.0, 5.0, -8.0, 1.0, help="Shock medio in % (valori negativi = crolli)") / 100.0
            with col_mj3:
                sigma_j_in = st.slider("Volatilità Salto (%)", 1.0, 20.0, 5.0, 1.0) / 100.0

        from core.risk_engine import compute_merton_jump_diffusion_simulation
        sr_p_merton = results.get("portfolio_return", pd.Series(dtype=float)) if results else pd.Series(dtype=float)
        merton_res = compute_merton_jump_diffusion_simulation(
            sr_portfolio=sr_p_merton,
            n_sims=500,
            time_horizon_days=horizon_opt,
            lambda_j=lambda_in,
            mu_j=mu_j_in,
            sigma_j=sigma_j_in,
            initial_value=mc_adv['initial_portfolio_value'] if mc_adv else 100000.0
        )

        cmj1, cmj2, cmj3, cmj4 = st.columns(4)
        with cmj1:
            metric_card("VaR 99% Gaussiano", f"{merton_res['var_99_gauss_pct']:.2f}%", "Benchmark Normale", True)
        with cmj2:
            merton_diff = merton_res['var_99_jump_pct'] - merton_res['var_99_gauss_pct']
            metric_card("VaR 99% Merton Jump", f"{merton_res['var_99_jump_pct']:.2f}%", f"{merton_diff:+.2f}% vs Gauss", False)
        with cmj3:
            metric_card("CVaR 99% Shortfall", f"{merton_res['cvar_99_jump_pct']:.2f}%", "Coda Estrema Fat Tail", False)
        with cmj4:
            metric_card("Frequenza Salti", f"{merton_res['mean_jumps_per_year']:.1f} / anno", "Processo di Poisson", True)

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 📈 Traiettorie Stocastiche Merton Jump-Diffusion")
        st.caption(f"Fascio stocastico simulato con Poisson Jump Shocks (λ = {lambda_in} salti/anno, ampiezza media shock μ_J = {mu_j_in*100:.1f}%, σ_J = {sigma_j_in*100:.1f}%).")

        m_days = merton_res["days"]
        fig_merton = go.Figure()
        fig_merton.add_trace(go.Scatter(
            x=m_days, y=merton_res["p95"], mode="lines", name="P95 Scenario Rialzista",
            line=dict(color="rgba(0,255,153,0.6)", width=1.2),
            hovertemplate="<b>P95 (Scenario Rialzista)</b><br>Giorno: <b>%{x}</b><br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_merton.add_trace(go.Scatter(
            x=m_days, y=merton_res["p75"], mode="lines", name="P75 Scenario Positivo",
            line=dict(color="rgba(0,204,255,0.5)", width=1), fill="tonexty", fillcolor="rgba(0,255,153,0.05)",
            hovertemplate="<b>P75 (Scenario Positivo)</b><br>Giorno: <b>%{x}</b><br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_merton.add_trace(go.Scatter(
            x=m_days, y=merton_res["p50"], mode="lines", name="P50 Mediana Jump-Diffusion",
            line=dict(color="#00f3ff", width=2.5),
            hovertemplate="<b>P50 (Mediana Jump-Diffusion)</b><br>Giorno: <b>%{x}</b><br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_merton.add_trace(go.Scatter(
            x=m_days, y=merton_res["p25"], mode="lines", name="P25 Scenario Conservativo",
            line=dict(color="rgba(255,204,0,0.5)", width=1), fill="tonexty", fillcolor="rgba(255,204,0,0.05)",
            hovertemplate="<b>P25 (Scenario Conservativo)</b><br>Giorno: <b>%{x}</b><br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_merton.add_trace(go.Scatter(
            x=m_days, y=merton_res["p5"], mode="lines", name="P05 Tail Crash Zone",
            line=dict(color="#ff3333", width=2, dash="dash"),
            hovertemplate="<b>P05 (Tail Crash Zone)</b><br>Giorno: <b>%{x}</b><br>Valore: <b>€ %{y:,.2f}</b><extra></extra>"
        ))

        fig_merton.update_layout(
            xaxis_title="Giorni di Contrattazione (Trading Days)",
            yaxis_title="Valore Portafoglio (€)",
            template="plotly_dark",
            height=450,
            margin=dict(t=50, b=40, l=55, r=25),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.0,
                bgcolor="rgba(22, 27, 34, 0.85)",
                bordercolor="rgba(255, 255, 255, 0.12)",
                borderwidth=1,
                font=dict(size=11, color="#ffffff")
            )
        )
        apply_plotly_theme(fig_merton)
        st.plotly_chart(fig_merton, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

# ── TAB 4: HEDGING TATTICO & TAIL RISK ────────────────────────
elif active_quant_tab == "🛡️ Hedging & Opzioni":
    section("🛡️ Simulatore di Copertura & Hedging Tattico (Beta-Neutral & Tail Protection)")
    st.caption("Calcola le coperture esatte con ETF inversi o micro-futures per azzerare o ridurre la sensibilità al rischio sistemico senza vendere gli asset.")

    if not has_portfolio or results is None:
        st.warning("⚠️ Carica prima un portafoglio nella Control Room per calcolare le coperture di Hedging Tattico.")
    else:
        from core.hedging import compute_beta_neutral_hedge, HEDGE_INSTRUMENTS

        col_hd1, col_hd2 = st.columns(2)
        with col_hd1:
            target_beta_input = st.slider(
                "Target Beta Desiderato:",
                min_value=-0.50, max_value=1.50, value=0.00, step=0.10,
                help="Imposta 0.00 per renderti immune ai movimenti del mercato generale (Beta-Neutral)."
            )
        with col_hd2:
            hedge_inst_input = st.selectbox(
                "Strumento di Copertura:",
                options=list(HEDGE_INSTRUMENTS.keys()),
                format_func=lambda k: f"{k} - {HEDGE_INSTRUMENTS[k]['name']} ({HEDGE_INSTRUMENTS[k]['underlying']})"
            )

        hedge_res = compute_beta_neutral_hedge(results, target_beta=target_beta_input, hedge_ticker=hedge_inst_input)

        col_hm1, col_hm2, col_hm3, col_hm4 = st.columns(4)
        with col_hm1:
            metric_card(
                "Beta Attuale Portafoglio",
                f"{hedge_res['current_beta']:.2f}",
                delta=f"Target: {target_beta_input:.2f}",
                positive=True,
                help_text="Sensibilità complessiva del portafoglio alle oscillazioni del mercato benchmark."
            )
        with col_hm2:
            val_eur_str = f"€ {hedge_res['hedge_value_eur']:,.2f}".replace(",", ".")
            metric_card(
                "Valore Copertura",
                val_eur_str,
                delta="Controvalore Reale",
                positive=True,
                help_text="Controvalore finanziario totale dello strumento short necessario per azzerare il Beta."
            )
        with col_hm3:
            metric_card(
                f"Quote {hedge_inst_input}",
                f"{hedge_res['hedge_shares']} quote",
                delta=f"Prezzo: € {hedge_res['instrument_price']:.2f}".replace(",", "."),
                positive=True,
                help_text="Numero esatto di quote/azioni dello strumento di copertura da acquistare a mercato."
            )
        with col_hm4:
            tail_eur_str = f"€ {hedge_res['tail_risk_var99_eur']:,.2f}".replace(",", ".")
            metric_card(
                "Protezione Tail Risk (99%)",
                tail_eur_str,
                delta="Scudo anti-crash",
                positive=True,
                help_text="Perdita massima stimata al 99% coperta dal posizionamento di hedging."
            )

        st.info(f"""
        💡 **Indicazione Operativa di Copertura**:
        Per portare il Beta di portafoglio da **{hedge_res['current_beta']:.2f}** a **{target_beta_input:.2f}**, acquista **{hedge_res['hedge_shares']} quote** dello strumento **{hedge_res['instrument_name']} ({hedge_inst_input})** ad un prezzo indicativo di **€ {hedge_res['instrument_price']:.2f}** per un investimento protettivo di **€ {hedge_res['hedge_value_eur']:,.2f}**.
        """)

        st.divider()
        col_head_bs1, col_head_bs2 = st.columns([3.5, 1.0])
        with col_head_bs1:
            st.markdown("#### 🛡️ Copertura Delta-Hedging & Volatility Skew (Black-Scholes 1973)")
            st.caption("Dimensionamento matematico dei contratti Put per immunizzare il Beta di portafoglio, calcolo analitico dei 5 Greci ($\\Delta, \\Gamma, \\Theta, \\text{Vega}, \\rho$) e calibrazione dello Skew reale.")
        with col_head_bs2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("💡 Guida a Black-Scholes, Greci & Skew", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 1. Modello di Black-Scholes-Merton (1973) & Greci</div>
  <div>
    • <b>Delta (&Delta;):</b> Sensibilità del premio al sottostante (Hedge Ratio)<br>
    • <b>Gamma (&Gamma;):</b> Curvatura e derivata seconda del prezzo rispetto allo Spot<br>
    • <b>Theta (&Theta;):</b> Decadimento temporale giornaliero (<i>Time Decay</i>)<br>
    • <b>Vega:</b> Sensibilità all'1% di variazione della volatilità implicita (&sigma;)<br>
    • <b>Rho (&rho;):</b> Reattività alle variazioni dei tassi d'interesse
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 2. Volatility Smile & Skew Reale</div>
  <div>Black-Scholes assume volatilità costante. Nella realtà, le Put OTM incorporano un premio di crash risk (&sigma;<sub>IV</sub> più elevata). ARGUS calibra la curva di Skew reale &sigma;(m) = a + b&middot;m + c&middot;m<sup>2</sup> per un pricing rigoroso dei contratti.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 3. Dimensionamento Contratti Put</div>
  <div><code>Contratti = (Valore Portafoglio &times; &beta; &times; Copertura %) / (Spot &times; 100 &times; |&Delta;|)</code></div>
</div>

</div>
""", button_label="💡 Come funziona Black-Scholes & Greci?")

        col_opt_in1, col_opt_in2, col_opt_in3, col_opt_in4 = st.columns(4)
        with col_opt_in1:
            bm_spot_in = st.number_input("Prezzo Spot Benchmark (SPY/SPX $):", value=550.0, step=10.0)
        with col_opt_in2:
            iv_in = st.slider("Volatilità Base ATM (%):", 10.0, 60.0, 18.0, 1.0) / 100.0
        with col_opt_in3:
            target_hedge_pct = st.slider("Copertura Portafoglio (%):", 25.0, 100.0, 100.0, 25.0)
        with col_opt_in4:
            expiry_m_in = st.selectbox("Scadenza Opzioni:", [1.0, 3.0, 6.0, 12.0], index=1, format_func=lambda x: f"{int(x)} Mesi")

        use_skew = st.toggle("⚡ Calibrazione Volatility Skew & Smile Reale", value=True, help="Applica la pendenza dello Skew per strike OTM (le Put OTM costano di più per il premio al crash risk)")

        port_val_tot = float(pos["current_value"].sum()) if (isinstance(pos, pd.DataFrame) and not pos.empty and "current_value" in pos.columns) else 100000.0
        port_b = float(results.get("metrics", {}).get("market_risk", {}).get("beta", 1.10) or 1.10) if results else 1.10

        bs_hedge = compute_portfolio_delta_hedge(
            portfolio_value=port_val_tot,
            portfolio_beta=port_b,
            benchmark_spot=bm_spot_in,
            target_hedge_pct=target_hedge_pct,
            strike_otm_pct=5.0,
            expiry_months=expiry_m_in,
            implied_vol=iv_in,
            use_skew_calibration=use_skew
        )

        col_bs1, col_bs2, col_bs3, col_bs4 = st.columns(4)
        with col_bs1:
            metric_card(
                "Contratti Put Necessari",
                f"{bs_hedge['contracts_needed']} Contratti",
                delta=f"Strike ${bs_hedge['strike_price']:.1f} (5% OTM)",
                positive=True,
                help_text=f"Numero di contratti di opzione Put 5% OTM necessari per sterilizzare il Beta al {target_hedge_pct:.0f}% del portafoglio."
            )
        with col_bs2:
            skew_diff = bs_hedge['put_price'] - bs_hedge['flat_put_price']
            metric_card(
                "Premio Put (Per Azione)",
                f"${bs_hedge['put_price']:.2f}",
                delta=f"+${skew_diff:.2f} Skew Prem." if use_skew else "IV Piatta ATM",
                positive=(not use_skew or skew_diff <= 0),
                help_text="Costo unitario del premio dell'opzione Put per singola azione del sottostante."
            )
        with col_bs3:
            cost_usd_str = f"${bs_hedge['total_hedge_cost']:,.2f}".replace(",", ".")
            metric_card(
                "Costo Totale Copertura",
                cost_usd_str,
                delta=f"{bs_hedge['cost_pct_of_portfolio']:.2f}% del Portafoglio",
                positive=(bs_hedge['cost_pct_of_portfolio'] < 5.0),
                help_text="Esborso finanziario totale per l'acquisto di tutti i contratti Put di copertura."
            )
        with col_bs4:
            metric_card(
                f"IV Effettiva ({bs_hedge['effective_iv_pct']:.1f}%)",
                f"Δ: {bs_hedge['put_delta']:.3f}",
                delta=f"Vega: {bs_hedge['put_vega']:.2f} | Γ: {bs_hedge['put_gamma']:.4f}",
                positive=True,
                help_text="Greci di Black-Scholes: Delta (Δ), Vega (sensibilità all'1% di IV) e Gamma (Γ, curvatura)."
            )

        # Superficie e Smile Plotly
        surf_model = build_volatility_surface(spot=bm_spot_in, base_atm_iv=iv_in)
        
        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)
        tab_opt_2d, tab_opt_3d = st.tabs([
            "📉 Curva Volatility Smile & Skew (2D)",
            "🌐 Superficie di Volatilità Implicita 3D (Term Structure x Moneyness)"
        ])
        
        with tab_opt_2d:
            fig_smile = go.Figure()
            exp_key = f"{int(expiry_m_in)}M"
            smile_fit = surf_model["smile_models"].get(exp_key, list(surf_model["smile_models"].values())[0])
            k_range = np.linspace(bm_spot_in * 0.75, bm_spot_in * 1.25, 60)
            iv_curve = [smile_fit["eval_func"](k) * 100.0 for k in k_range]
            
            fig_smile.add_trace(go.Scatter(
                x=k_range,
                y=iv_curve,
                mode="lines",
                name=f"Skew Calibrato ({int(expiry_m_in)} Mesi)",
                line=dict(color="#00f3ff", width=2.8),
                hovertemplate="<b>Strike: $%{x:.1f}</b><br>IV Calibrata: <b>%{y:.2f}%</b><extra></extra>"
            ))
            
            # Strike di Copertura Put
            fig_smile.add_trace(go.Scatter(
                x=[bs_hedge["strike_price"]],
                y=[bs_hedge["effective_iv_pct"]],
                mode="markers+text",
                name="Strike Put Hedging (5% OTM)",
                text=["Put Strike"],
                textposition="top left",
                textfont=dict(color="#f87171", size=11),
                marker=dict(color="#ef4444", size=12, symbol="diamond", line=dict(color="#ffffff", width=1.5)),
                hovertemplate="<b>Strike Put Hedging: $%{x:.1f}</b><br>IV Skew Effettiva: <b>%{y:.2f}%</b><extra></extra>"
            ))
            
            # Strike Spot ATM
            fig_smile.add_trace(go.Scatter(
                x=[bm_spot_in],
                y=[iv_in * 100.0],
                mode="markers+text",
                name=f"Spot ATM (${bm_spot_in:.0f})",
                text=["Spot ATM"],
                textposition="top right",
                textfont=dict(color="#ffb74d", size=11),
                marker=dict(color="#ff9900", size=11, symbol="circle", line=dict(color="#ffffff", width=1.5)),
                hovertemplate="<b>Spot Benchmark: $%{x:.1f}</b><br>IV Base ATM: <b>%{y:.2f}%</b><extra></extra>"
            ))
            
            fig_smile.update_layout(
                height=380,
                margin=dict(l=15, r=15, t=30, b=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11.5)
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Strike Price ($)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(family="monospace")),
                yaxis=dict(title="Volatilità Implicita (%)", showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickfont=dict(family="monospace"))
            )
            apply_plotly_theme(fig_smile)
            st.plotly_chart(fig_smile, use_container_width=True)

        with tab_opt_3d:
            matrix_z = surf_model["matrix_iv"].values
            strikes_x = surf_model["matrix_iv"].columns.values
            expiries_y = surf_model["matrix_iv"].index.values
            
            fig_surf3d = go.Figure(data=[go.Surface(
                z=matrix_z,
                x=strikes_x,
                y=expiries_y,
                colorscale="Viridis",
                colorbar=dict(
                    title=dict(text="IV (%)", font=dict(color="#ffffff", size=12)),
                    tickfont=dict(color="#cbd5e1", size=10),
                    len=0.75,
                    thickness=16
                ),
                hovertemplate="<b>Strike: $%{x:.1f}</b><br>Scadenza: %{y} Mesi<br>Volatilità Implicita: <b>%{z:.2f}%</b><extra></extra>"
            )])
            fig_surf3d.update_layout(
                height=480,
                margin=dict(l=10, r=10, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                scene=dict(
                    xaxis=dict(title="Strike ($)", gridcolor="rgba(255,255,255,0.08)", tickfont=dict(family="monospace")),
                    yaxis=dict(title="Scadenza (Mesi)", gridcolor="rgba(255,255,255,0.08)", tickfont=dict(family="monospace")),
                    zaxis=dict(title="IV (%)", gridcolor="rgba(255,255,255,0.08)", tickfont=dict(family="monospace")),
                    camera=dict(eye=dict(x=-1.65, y=-1.65, z=1.25))
                )
            )
            apply_plotly_theme(fig_surf3d)
            st.plotly_chart(fig_surf3d, use_container_width=True)

        st.markdown("##### 💵 Strategia Covered Call Yield Enhancer sui Titoli in Portafoglio")
        st.caption("Simula la vendita sistematica di opzioni Call Out-of-The-Money (+5% Strike) a 30 giorni per monetizzare la volatilità implicita ed estrarre rendimento addizionale (*Yield Enhancement*).")
        
        df_ret_hedging = results.get("returns", pd.DataFrame()) if results else pd.DataFrame()
        if (df_ret_hedging.empty or not isinstance(df_ret_hedging, pd.DataFrame) or df_ret_hedging.shape[1] < 2) and results:
            df_pr_h = results.get("df_prices", pd.DataFrame())
            if not df_pr_h.empty and "ticker" in df_pr_h.columns and "price_date" in df_pr_h.columns:
                piv_h = df_pr_h.pivot(index="price_date", columns="ticker", values="close")
                df_ret_hedging = piv_h.pct_change().dropna(how="all")

        vol_map_pos = (df_ret_hedging.std() * np.sqrt(252.0)).to_dict() if (isinstance(df_ret_hedging, pd.DataFrame) and not df_ret_hedging.empty) else {}
        pos_active_cc = pos[(pos["qty_net"] > 1e-6) & (pos["current_value"] > 0)] if (isinstance(pos, pd.DataFrame) and not pos.empty and "qty_net" in pos.columns and "current_value" in pos.columns) else pos
        df_cov_call = compute_covered_call_yield_enhancement(
            pos_active_cc,
            otm_pct=5.0,
            implied_vol=iv_in,
            use_skew_calibration=use_skew,
            vol_map=vol_map_pos
        ) if isinstance(pos_active_cc, pd.DataFrame) and not pos_active_cc.empty else pd.DataFrame()

        if not df_cov_call.empty:
            col_cc_f1, col_cc_f2, col_cc_f3 = st.columns([2.0, 1.3, 0.9])
            with col_cc_f1:
                search_cc = st.text_input("🔍 Cerca Ticker:", placeholder="Digita ticker per filtrare (es. BTC, GOOGL, AMZN)...", key="search_cov_call")
            with col_cc_f2:
                filter_cc_type = st.selectbox("🏷️ Filtro Lotti:", ["Tutti gli Asset", "🟢 Solo Lotti Standard (≥100 quote)", "⚪ Solo Frazionari (<100 quote)"], key="filter_cov_call_type")

            df_cov_filtered = df_cov_call.copy()
            if search_cc:
                df_cov_filtered = df_cov_filtered[df_cov_filtered["ticker"].astype(str).str.contains(search_cc.strip(), case=False, na=False)]
            if filter_cc_type == "🟢 Solo Lotti Standard (≥100 quote)":
                df_cov_filtered = df_cov_filtered[df_cov_filtered["contratti_eseguibili"] > 0]
            elif filter_cc_type == "⚪ Solo Frazionari (<100 quote)":
                df_cov_filtered = df_cov_filtered[df_cov_filtered["contratti_eseguibili"] == 0]

            if df_cov_filtered.empty:
                st.info("ℹ️ Nessuna posizione trovata corrispondente ai criteri di ricerca.")
            else:
                df_cov_show = pd.DataFrame({
                    "Ticker": df_cov_filtered["ticker"],
                    "Quote Posizione": df_cov_filtered["quantita_totale"],
                    "Prezzo Spot (€)": df_cov_filtered["prezzo_spot"],
                    "Strike Call (+5%)": df_cov_filtered["strike_call_otm"],
                    "IV Specifica (%)": df_cov_filtered["iv_effettiva_pct"],
                    "Premio / Azione (€)": df_cov_filtered["premio_per_azione"],
                    "Incasso Mensile (€)": df_cov_filtered["incasso_premio_totale"],
                    "Extra Yield Annuo (%)": df_cov_filtered["extra_rendimento_annuo_pct"],
                    "Lotti Opzioni": df_cov_filtered.apply(
                        lambda r: f"🟢 {int(r['contratti_eseguibili'])} Contratti ({int(r['contratti_eseguibili']*100)} quote)"
                        if r['contratti_eseguibili'] > 0
                        else f"⚪ Frazionario ({r['quantita_totale']:g}/100)",
                        axis=1
                    )
                })

                with col_cc_f3:
                    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                    csv_cov = df_cov_show.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Scarica CSV",
                        data=csv_cov,
                        file_name="strategia_covered_call.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="btn_download_covered_call"
                    )

                cov_cfg = {
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Quote Posizione": st.column_config.NumberColumn("Quote Posizione", format="%.2f"),
                    "Prezzo Spot (€)": st.column_config.NumberColumn("Prezzo Spot (€)", format="€ %.2f"),
                    "Strike Call (+5%)": st.column_config.NumberColumn("Strike OTM (+5%)", format="€ %.2f"),
                    "IV Specifica (%)": st.column_config.ProgressColumn("IV Specifica", format="%.1f%%", min_value=0.0, max_value=100.0),
                    "Premio / Azione (€)": st.column_config.NumberColumn("Premio / Azione", format="€ %.2f"),
                    "Incasso Mensile (€)": st.column_config.NumberColumn("Incasso Stimato", format="€ %.2f"),
                    "Extra Yield Annuo (%)": st.column_config.NumberColumn("Extra Yield Annuo", format="+%.2f%%"),
                    "Lotti Opzioni": st.column_config.TextColumn("Lotti Opzioni (x100)", width="medium")
                }

                st.dataframe(
                    df_cov_show,
                    column_config=cov_cfg,
                    use_container_width=True,
                    hide_index=True
                )

# ── TAB 5: ATTRIBUZIONE BRINSON & FATTORI MULTI-FATTORIALI ────────
elif active_quant_tab == "🎯 Attribuzione & Fattori":
    section("🎯 Attribuzione della Performance & Modelli Multi-Fattoriali (Brinson, Barra & ML)")
    st.caption("Scompone l'extra-rendimento di portafoglio rispetto al Benchmark ed analizza l'esposizione ai fattori di rischio Barra/Carhart, Black-Litterman e Volatilità ML.")

    if not has_portfolio or results is None:
        st.warning("⚠️ Carica prima un portafoglio nella Control Room per visualizzare l'attribuzione di performance e i fattori Barra.")
    else:
        from core.attribution import compute_brinson_attribution

        attr_res = compute_brinson_attribution(results)
        attr_summary = attr_res.get("summary", {})
        attr_df = attr_res.get("attribution_df", pd.DataFrame())
        if not attr_df.empty:
            st.markdown("**Scomposizione per Settore (Allocation vs Selection vs Interaction)**")
            fig_attr = px.bar(
                attr_df, x="sector", y=["allocation_effect_pct", "selection_effect_pct", "interaction_effect_pct"],
                barmode="group",
                color_discrete_sequence=["#58a6ff", "#3fb950", "#bc8cff"],
                labels={
                    "value": "Impatto %", "sector": "Settore GICS", "variable": "Fattore Attribuzione",
                    "allocation_effect_pct": "Allocation Effect",
                    "selection_effect_pct": "Selection Effect",
                    "interaction_effect_pct": "Interaction Effect"
                },
                template="plotly_dark", height=430
            )
            new_names = {
                "allocation_effect_pct": "Allocation Effect",
                "selection_effect_pct": "Selection Effect",
                "interaction_effect_pct": "Interaction Effect"
            }
            fig_attr.for_each_trace(lambda t: t.update(name=new_names.get(t.name, t.name)))
            fig_attr.update_traces(
                hovertemplate="<b>Settore: %{x}</b><br>%{fullData.name}: <b>%{y:.2f}%</b><extra></extra>"
            )
            fig_attr.update_layout(
                xaxis_title="Settore GICS",
                yaxis_title="Impatto su Extra-Rendimento %",
                margin=dict(t=50, b=40, l=55, r=25),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0.0,
                    bgcolor="rgba(22, 27, 34, 0.85)",
                    bordercolor="rgba(255, 255, 255, 0.12)",
                    borderwidth=1,
                    font=dict(size=11, color="#ffffff")
                ),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_attr)
            st.plotly_chart(fig_attr, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})
        else:
            st.info("Dati di settore insufficienti per calcolare l'attribuzione Brinson-Fachler.")

        st.divider()

        from core.risk_engine import compute_black_litterman_optimization, compute_carhart_4factor_exposures

        sr_p = results.get("portfolio_return", pd.Series(dtype=float)) if results else pd.Series(dtype=float)

        # ── RIGA 1: OTTIMIZZAZIONE BLACK-LITTERMAN ────────────────
        st.markdown("#### 🏛️ Ottimizzazione Black-Litterman (Equilibrio Implicito & Pesi)")
        st.caption("Stima i rendimenti attesi di equilibrio inverso (Reverse Optimization) a partire dalla matrice di covarianza e dai pesi correnti di portafoglio.")

        cov_df = None
        if opt and "cov_matrix" in opt and isinstance(opt["cov_matrix"], pd.DataFrame) and not opt["cov_matrix"].empty:
            cov_df = opt["cov_matrix"]
        else:
            df_returns_all = results.get("returns", pd.DataFrame()) if results else pd.DataFrame()
            if isinstance(df_returns_all, pd.DataFrame) and not df_returns_all.empty:
                active_tickers = []
                if isinstance(pos, pd.DataFrame) and not pos.empty and "qty_net" in pos.columns and "ticker" in pos.columns:
                    active_tickers = pos[pos["qty_net"] > 0]["ticker"].tolist()
                common = [t for t in active_tickers if t in df_returns_all.columns]
                if len(common) >= 1:
                    cov_df = df_returns_all[common].cov() * 252

        if cov_df is not None and not cov_df.empty:
            mkt_w = None
            if isinstance(pos, pd.DataFrame) and not pos.empty and "weight_pct" in pos.columns and "ticker" in pos.columns:
                active_pos = pos[pos["qty_net"] > 1e-6] if "qty_net" in pos.columns else pos
                mkt_w = active_pos.set_index("ticker")["weight_pct"] / 100.0
            else:
                mkt_w = pd.Series(1.0 / len(cov_df), index=cov_df.index)
            
            # Opzionale: Input interattivo delle Views dell'Investitore
            custom_views = {}
            with st.expander("🎯 Personalizza Views dell'Investitore (Opzionale)", expanded=False):
                st.caption("Inserisci le tue aspettative soggettive di rendimento su specifici titoli per osservare come il modello Black-Litterman aggiorna i rendimenti attesi a posteriori e ricalibra i pesi ottimali.")
                col_v1, col_v2 = st.columns([2, 2])
                with col_v1:
                    view_asset = st.selectbox("Seleziona Titolo per la View:", options=list(cov_df.index), key="bl_view_asset")
                with col_v2:
                    view_return_pct = st.number_input(f"Rendimento Atteso Annuo per {view_asset} (%):", min_value=-50.0, max_value=150.0, value=15.0, step=1.0, key="bl_view_return")
                
                enable_view = st.checkbox("Applica questa View soggettiva al Modello", value=False, key="bl_enable_view")
                if enable_view and view_asset:
                    custom_views[view_asset] = view_return_pct / 100.0

            bl_res = compute_black_litterman_optimization(cov_df, mkt_w, views_dict=custom_views if custom_views else None)
            if bl_res:
                df_bl = pd.DataFrame({
                    "Ticker": cov_df.index,
                    "Equilibrium Return %": bl_res["implied_equilibrium_returns"].values * 100,
                    "BL Return %": bl_res["black_litterman_returns"].values * 100,
                    "BL Weight %": bl_res["black_litterman_weights"].values * 100
                })
                # ── RIGA 1: GRAFICI INTERATTIVI AD ALTA DENSITÀ (TREEMAP & BARRE RAGGRUPPATE) ──
                tab_bl_tm, tab_bl_bar = st.tabs([
                    "🗺️ Mappa di Allocazione Ottimale (Treemap)",
                    "📊 Confronto Pesi (Peso Attuale vs Target Black-Litterman)"
                ])

                with tab_bl_tm:
                    fig_bl_tm = px.treemap(
                        df_bl,
                        path=[px.Constant("Allocazione Black-Litterman"), "Ticker"],
                        values="BL Weight %",
                        color="BL Return %",
                        color_continuous_scale=[[0.0, "#0f172a"], [0.5, "#1e3a8a"], [1.0, "#38bdf8"]],
                        labels={"BL Weight %": "Peso Target %", "BL Return %": "Rendimento BL %"}
                    )
                    fig_bl_tm.update_traces(
                        textinfo="label+value",
                        texttemplate="<b>%{label}</b><br>%{value:.2f}%<br><span style='font-size:10.5px;'>Ret: %{color:.2f}%</span>",
                        hovertemplate="<b>Asset: %{label}</b><br>🎯 Peso Target BL: <b>%{value:.2f}%</b><br>📈 Rendimento Atteso: <b>%{color:.2f}%</b><extra></extra>"
                    )
                    fig_bl_tm.update_layout(
                        height=310,
                        margin=dict(t=25, b=15, l=10, r=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    apply_plotly_theme(fig_bl_tm)
                    st.plotly_chart(fig_bl_tm, use_container_width=True)

                with tab_bl_bar:
                    cur_w_map = (mkt_w * 100.0).to_dict() if isinstance(mkt_w, pd.Series) else {}
                    df_bl_comp = df_bl.copy()
                    df_bl_comp["Peso Attuale %"] = df_bl_comp["Ticker"].map(cur_w_map).fillna(0.0)

                    fig_bl_bar = go.Figure()
                    fig_bl_bar.add_trace(go.Bar(
                        x=df_bl_comp["Ticker"],
                        y=df_bl_comp["Peso Attuale %"],
                        name="⭐ Peso Attuale",
                        marker=dict(color="#58a6ff", line=dict(color="rgba(255,255,255,0.1)", width=1)),
                        hovertemplate="<b>%{x}</b><br>Peso Attuale: <b>%{y:.2f}%</b><extra></extra>"
                    ))
                    fig_bl_bar.add_trace(go.Bar(
                        x=df_bl_comp["Ticker"],
                        y=df_bl_comp["BL Weight %"],
                        name="🎯 Target Black-Litterman",
                        marker=dict(color="#ff9900", line=dict(color="rgba(255,153,0,0.4)", width=1)),
                        hovertemplate="<b>%{x}</b><br>Target BL: <b>%{y:.2f}%</b><extra></extra>"
                    ))
                    fig_bl_bar.update_layout(
                        height=310,
                        barmode="group",
                        margin=dict(t=20, b=35, l=40, r=15),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis=dict(tickangle=-45, tickfont=dict(size=10.5, family="monospace")),
                        yaxis=dict(title="Allocazione %", ticksuffix="%", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11))
                    )
                    apply_plotly_theme(fig_bl_bar)
                    st.plotly_chart(fig_bl_bar, use_container_width=True)

                # ── RIGA 2: TABELLA INTERATTIVA AD ALTEZZA COMPATTA CON FILTRI ───────
                col_bl_f1, col_bl_f2 = st.columns([3.2, 0.9])
                with col_bl_f1:
                    search_bl = st.text_input("🔍 Cerca Ticker nella Tabella Black-Litterman:", placeholder="Filtra per Ticker (es. GOOGL, BTC, ETH)...", key="search_bl_ticker")
                with col_bl_f2:
                    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                    csv_bl = df_bl.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_bl, file_name="black_litterman_weights.csv", mime="text/csv", use_container_width=True)

                df_bl_filt = df_bl.copy()
                if search_bl:
                    df_bl_filt = df_bl_filt[df_bl_filt["Ticker"].astype(str).str.contains(search_bl.strip(), case=False, na=False)]

                bl_cfg = {
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Equilibrium Return %": st.column_config.NumberColumn("Equilibrium Return", format="%.2f%%"),
                    "BL Return %": st.column_config.NumberColumn("BL Return", format="%.2f%%"),
                    "BL Weight %": st.column_config.ProgressColumn("BL Target Weight", format="%.2f%%", min_value=0.0, max_value=100.0)
                }
                st.dataframe(
                    df_bl_filt,
                    column_config=bl_cfg,
                    use_container_width=True,
                    hide_index=True,
                    height=280
                )
            else:
                st.info("Dati di covarianza insufficienti per Black-Litterman.")
        else:
            st.info("Matrice di covarianza non disponibile. Assicurati di aver calcolato i rendimenti per le posizioni attive.")

        st.divider()

        # ── RIGA 2: ANALISI FATTORIALE KENNETH FRENCH & CARHART ────
        col_c_head1, col_c_head2 = st.columns([3.5, 1.2])
        with col_c_head1:
            st.markdown("#### 🧠 Analisi Fattoriale Kenneth French (Fama-French 5-Factor & Momentum)")
            st.caption("Regressione econometrica multivariata OLS su serie storiche ufficiali di Dartmouth: isolamento dell'Alpha puro di gestione, attribuzione del rendimento e significatività statistica (t-stat & p-value).")
        with col_c_head2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            render_fama_french_modal(button_label="ℹ️ Teoria Fama-French & Formule", use_popover=False)

        from core.factor_library import compute_fama_french_factor_model

        st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
        ff_model_sel = render_segmented_tabs([
            "🏛️ Fama-French 5-Factor + Momentum",
            "📊 Carhart 4-Factor (Mkt, SMB, HML, MOM)",
            "📐 Fama-French 3-Factor (Mkt, SMB, HML)"
        ], key="ff_model_selector_tab")

        if "5-Factor" in ff_model_sel:
            m_code = "5_factor_mom"
        elif "Carhart" in ff_model_sel:
            m_code = "4_factor"
        else:
            m_code = "3_factor"

        ff_res = compute_fama_french_factor_model(sr_p, model_type=m_code)
        df_ff_factors = ff_res.get("df_factors", pd.DataFrame())

        # KPI Cards Dinamiche e Bilanciate
        alpha_ann = ff_res.get("alpha_annualized", 0.0)
        alpha_t = ff_res.get("alpha_t_stat", 0.0)
        r2_val = ff_res.get("r_squared", 0.0)
        adj_r2 = ff_res.get("adj_r_squared", 0.0)

        # Mappatura rapida dei beta
        betas_by_name = {}
        if not df_ff_factors.empty:
            for _, r in df_ff_factors.iterrows():
                betas_by_name[r["factor"]] = r["beta"]

        b_mkt = betas_by_name.get("Mkt-RF", 1.0)
        b_smb = betas_by_name.get("SMB", 0.0)
        b_hml = betas_by_name.get("HML", 0.0)
        b_rmw = betas_by_name.get("RMW")
        b_cma = betas_by_name.get("CMA")
        b_mom = betas_by_name.get("MOM")

        # Riga 1: Alpha, Mercato, Size, Value
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        with col_kpi1:
            metric_card(
                "Alpha Puro (α)",
                f"{alpha_ann*100:+.2f}%",
                f"t = {alpha_t:+.2f} ({'Significativo' if abs(alpha_t)>=1.96 else 'Non Sig.'})",
                alpha_ann >= 0
            )
        with col_kpi2:
            metric_card(
                "Beta Mkt-RF",
                f"{b_mkt:+.2f}",
                "Esposizione Sistemica",
                b_mkt >= 0
            )
        with col_kpi3:
            metric_card(
                "Beta Size (SMB)",
                f"{b_smb:+.2f}",
                "Small Cap Tilt" if b_smb > 0 else "Large Cap Tilt",
                b_smb >= 0
            )
        with col_kpi4:
            metric_card(
                "Beta Value (HML)",
                f"{b_hml:+.2f}",
                "Value Tilt" if b_hml > 0 else "Growth Tilt",
                b_hml >= 0
            )

        # Riga 2: Fattori Aggiuntivi & Bontà del Modello
        if b_rmw is not None and b_cma is not None:
            st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
            col_kpi5, col_kpi6, col_kpi7, col_kpi8 = st.columns(4)
            with col_kpi5:
                metric_card(
                    "Beta Profit (RMW)",
                    f"{b_rmw:+.2f}",
                    "Alta Redditività" if b_rmw > 0 else "Margini Deboli",
                    b_rmw >= 0
                )
            with col_kpi6:
                metric_card(
                    "Beta Inv (CMA)",
                    f"{b_cma:+.2f}",
                    "Capex Conservativo" if b_cma > 0 else "Capex Aggressivo",
                    b_cma >= 0
                )
            with col_kpi7:
                b_m_val = b_mom if b_mom is not None else 0.0
                metric_card(
                    "Beta Momentum (MOM)",
                    f"{b_m_val:+.2f}",
                    "Trend Winner" if b_m_val > 0 else "Trend Loser",
                    b_m_val >= 0
                )
            with col_kpi8:
                metric_card(
                    "Bontà Modello (R²)",
                    f"{r2_val*100:.1f}%",
                    f"Adj R²: {adj_r2*100:.1f}%",
                    True
                )
        elif b_mom is not None:
            st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
            col_kpi5, col_kpi6 = st.columns(2)
            with col_kpi5:
                metric_card(
                    "Beta Momentum (MOM)",
                    f"{b_mom:+.2f}",
                    "Trend Winner (12M)" if b_mom > 0 else "Trend Loser (12M)",
                    b_mom >= 0
                )
            with col_kpi6:
                metric_card(
                    "Bontà Modello (R²)",
                    f"{r2_val*100:.1f}%",
                    f"Adj R²: {adj_r2*100:.1f}%",
                    True
                )
        else:
            st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
            col_kpi5, _ = st.columns([1, 3])
            with col_kpi5:
                metric_card(
                    "Bontà Modello (R²)",
                    f"{r2_val*100:.1f}%",
                    f"Adj R²: {adj_r2*100:.1f}%",
                    True
                )

        # Grafici e Attribuzione
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_ff_g1, col_ff_g2 = st.columns([1.6, 1.1])

        with col_ff_g1:
            st.markdown("##### 🌊 Factor Return Attribution (% Rendimento Annuo Spiegato)")
            attrib = ff_res.get("factor_attribution", {})
            if attrib:
                df_attr = pd.DataFrame([
                    {"Fattore": k, "Contributo %": v * 100.0} for k, v in attrib.items()
                ])
                colors_attr = ["#3fb950" if val >= 0 else "#f85149" for val in df_attr["Contributo %"]]

                fig_attr = go.Figure(go.Bar(
                    x=df_attr["Fattore"],
                    y=df_attr["Contributo %"],
                    marker_color=colors_attr,
                    text=df_attr["Contributo %"].apply(lambda x: f"{x:+.2f}%"),
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Contributo al Rendimento: <b>%{text}</b><extra></extra>"
                ))
                fig_attr.update_layout(
                    template="plotly_dark",
                    height=290,
                    margin=dict(l=10, r=10, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(title="Contributo Annuo %", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                    xaxis=dict(title="")
                )
                apply_plotly_theme(fig_attr)
                st.plotly_chart(fig_attr, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        with col_ff_g2:
            st.markdown("##### 🍩 Decomposizione Varianza del Rischio")
            sys_ff_pct = ff_res.get("systematic_risk_pct", 85.0)
            spec_ff_pct = ff_res.get("specific_risk_pct", 15.0)

            fig_pie_ff = go.Figure(data=[go.Pie(
                labels=["Rischio Sistemico (Fattori)", "Rischio Specifico (Alpha/Idiosincratico)"],
                values=[sys_ff_pct, spec_ff_pct],
                hole=0.6,
                marker=dict(colors=["#58a6ff", "#f59e0b"], line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>%{label}</b><br>Quota Varianza: <b>%{percent}</b><extra></extra>"
            )])
            fig_pie_ff.update_layout(
                template="plotly_dark",
                height=230,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(orientation="h", y=-0.1)
            )
            apply_plotly_theme(fig_pie_ff)
            st.plotly_chart(fig_pie_ff, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})
            st.caption(f"Bontà di Adattamento OLS: **R² = {r2_val*100:.1f}%** | **Adj R² = {ff_res.get('adj_r_squared', 0.0)*100:.1f}%**")

        # Tabella Econometrica dei Parametri
        # Tabella Econometrica dei Parametri
        if not df_ff_factors.empty:
            col_ff_h1, col_ff_h2 = st.columns([3.5, 0.9])
            with col_ff_h1:
                st.markdown("##### 📋 Tabella Econometrica di Regressione OLS & Test di Ipotesi")
            with col_ff_h2:
                csv_ff = df_ff_factors.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_ff, file_name="fama_french_factor_regression.csv", mime="text/csv", use_container_width=True)

            df_ff_show = df_ff_factors.rename(columns={
                "factor": "Fattore di Rischio",
                "beta": "Coefficiente Beta (β)",
                "std_err": "Errore Standard",
                "t_stat": "Statistica t",
                "p_value": "p-value",
                "ci_95": "Intervallo Confidenza 95%",
                "is_significant": "Significatività (95%)",
                "annual_return_contrib_pct": "Contributo Rendimento Annuo (%)"
            })
            df_ff_show["Significatività (95%)"] = df_ff_show["Significatività (95%)"].apply(
                lambda x: "🟢 Significativo (|t| ≥ 1.96)" if x else "⚪ Non Significativo"
            )
            ff_cfg = {
                "Fattore di Rischio": st.column_config.TextColumn("Fattore di Rischio", width="medium"),
                "Coefficiente Beta (β)": st.column_config.NumberColumn("Beta (β)", format="%+.4f"),
                "Errore Standard": st.column_config.NumberColumn("Std Error", format="%.4f"),
                "Statistica t": st.column_config.NumberColumn("Statistica t", format="%+.2f"),
                "p-value": st.column_config.NumberColumn("p-value", format="%.4f"),
                "Intervallo Confidenza 95%": st.column_config.TextColumn("CI 95%", width="medium"),
                "Significatività (95%)": st.column_config.TextColumn("Significatività (95%)", width="medium"),
                "Contributo Rendimento Annuo (%)": st.column_config.NumberColumn("Contributo Rend. Annuo", format="%+.2f%%")
            }
            st.dataframe(
                df_ff_show,
                column_config=ff_cfg,
                use_container_width=True,
                hide_index=True
            )

        # Grafico Rolling Factor Exposures (se presente)
        df_roll_b = ff_res.get("rolling_betas", pd.DataFrame())
        if not df_roll_b.empty:
            st.markdown("##### 📈 Evoluzione Dinamica delle Esposizioni Fattoriali (Rolling OLS 60 Giorni)")
            st.caption("Traccia nel tempo come cambiano i Beta di rischio sistemico e di stile del portafoglio (evidenziando cambi di regime o drift stilistici).")
            
            all_factors = [c for c in df_roll_b.columns if c != "Alpha (Ann)"]
            col_rf1, col_rf2 = st.columns([3.2, 1.0])
            with col_rf1:
                selected_factors = st.multiselect(
                    "🔍 Filtra Fattori da visualizzare nel Grafico:",
                    options=all_factors,
                    default=all_factors,
                    key="rolling_factors_filter"
                )
            with col_rf2:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                csv_roll = df_roll_b.to_csv().encode('utf-8')
                st.download_button("📥 Scarica Serie CSV", data=csv_roll, file_name="rolling_factor_betas_60d.csv", mime="text/csv", use_container_width=True)

            factors_to_show = selected_factors if selected_factors else all_factors

            color_map = {
                "Mkt-RF": "#58a6ff",
                "SMB": "#f59e0b",
                "HML": "#3fb950",
                "RMW": "#bc8cff",
                "CMA": "#f43f5e",
                "MOM": "#00f3ff"
            }

            df_plot_r = df_roll_b.reset_index()
            fig_roll = go.Figure()

            # Linea neutra y=0
            fig_roll.add_hline(
                y=0.0,
                line_dash="dash",
                line_color="rgba(255, 255, 255, 0.25)",
                line_width=1.2,
                annotation_text="Neutrale (β = 0.0)",
                annotation_position="bottom right",
                annotation_font=dict(size=10, color="#8b949e")
            )

            for f_name in factors_to_show:
                if f_name in df_plot_r.columns:
                    fig_roll.add_trace(go.Scatter(
                        x=df_plot_r["Date"],
                        y=df_plot_r[f_name],
                        mode="lines",
                        name=f_name,
                        line=dict(color=color_map.get(f_name, "#58a6ff"), width=2),
                        hovertemplate=f"<b>{f_name}</b>: %{{y:+.3f}}<extra></extra>"
                    ))

            fig_roll.update_layout(
                template="plotly_dark",
                height=350,
                hovermode="x unified",
                margin=dict(l=10, r=15, t=25, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    title=None,
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.06)",
                    rangeselector=dict(
                        buttons=[
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1A", step="year", stepmode="backward"),
                            dict(count=3, label="3A", step="year", stepmode="backward"),
                            dict(step="all", label="Tutto")
                        ],
                        bgcolor="rgba(22, 27, 34, 0.9)",
                        font=dict(color="#ffffff", size=10.5),
                        activecolor="#ff9900"
                    )
                ),
                yaxis=dict(
                    title="Beta Rolling (60G)",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.06)",
                    tickformat="+.2f"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.04,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, family="monospace")
                )
            )
            apply_plotly_theme(fig_roll)
            st.plotly_chart(fig_roll, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        st.divider()
        col_head_bar1, col_head_bar2 = st.columns([3.2, 1.1])
        with col_head_bar1:
            st.markdown("#### 🏛️ Modello Macro-Fattoriale MSCI Barra (5 Fattori Ortogonalizzati)")
            st.caption("Decomposizione avanzata ed ortogonale delle esposizioni fattoriali del portafoglio (Market, Size SMB, Value HML, Momentum WML, Term Premium).")
        with col_head_bar2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida al Modello Fattoriale MSCI Barra & Forecast ML", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Modello Macro-Fattoriale MSCI Barra</div>
  <div>Lo standard quantitativo dell'industria per l'attribuzione del rischio istituzionale, che scompone la varianza totale del portafoglio in 5 macro-fattori ortogonalizzati e rischio specifico.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 I 5 Macro-Fattori Ortogonali</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>MKT (Equity Systematic):</b> Esposizione al mercato azionario globale<br>
    • <b>SMB (Small Minus Big):</b> Sensibilità al fattore dimensione d'impresa<br>
    • <b>HML (High Minus Low):</b> Esposizione a titoli Value vs Growth<br>
    • <b>WML (Winners Minus Losers):</b> Inerzia di Momentum a 12 mesi<br>
    • <b>TERM (Term Premium):</b> Sensibilità all'inclinazione della curva dei tassi sovrani
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Separare la componente di rischio sistemico (spiegata dai fattori) dal rischio specifico non diversificato, stimando la vera abilità gestionale (&alpha; puro).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS & Forecast ML</div>
  <div>ARGUS esegue la regressione ortogonale con calcolo delle t-stat al 95% e combina un modello Random Forest per prevedere la volatilità attesa sui successivi 30 giorni.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>I fattori con <code>|t-stat| &ge; 1.96</code> sono statisticamente significativi; una quota di Rischio Specifico &gt; 40% indica una marcata esposizione a eventi societari idiosincratici.</div>
</div>

</div>
""", button_label="💡 Come funziona il Modello MSCI Barra?")

        from core.risk_engine import compute_msci_barra_multifactor_model
        barra_res = compute_msci_barra_multifactor_model(sr_p)

        betas_dict = barra_res.get("factor_betas", {})
        t_dict = barra_res.get("t_stats", {})

        factor_names_map = {
            "MKT": "Mercato (Equity Systematic)",
            "SMB": "Dimensione (Small Caps)",
            "HML": "Valore (High Book-to-Market)",
            "WML": "Inerzia (12M Momentum)",
            "TERM": "Macro Curva Tassi (Term Premium)"
        }

        df_barra = pd.DataFrame({
            "Fattore": list(betas_dict.keys()),
            "Nome Esteso": [factor_names_map.get(k, k) for k in betas_dict.keys()],
            "Beta Fattoriale": [betas_dict[k] for k in betas_dict.keys()],
            "Statistica t": [t_dict.get(k, 0.0) for k in betas_dict.keys()],
            "Significatività (95%)": ["🟢 Significativo" if abs(t_dict.get(k, 0.0)) >= 1.96 else "⚪ In Linea" for k in betas_dict.keys()]
        })

        col_bar1, col_bar2 = st.columns([1.5, 1])

        with col_bar1:
            colors = ["#3fb950" if b >= 0 else "#f85149" for b in df_barra["Beta Fattoriale"]]

            fig_barra = go.Figure(go.Bar(
                x=df_barra["Fattore"],
                y=df_barra["Beta Fattoriale"],
                marker_color=colors,
                text=df_barra["Beta Fattoriale"].apply(lambda b: f"{b:+.2f}"),
                textposition="outside",
                textfont=dict(size=12, color="white"),
                hovertemplate="<b>Fattore: %{x}</b><br>Beta Fattoriale: <b>%{text}</b><extra></extra>"
            ))

            fig_barra.update_layout(
                template="plotly_dark",
                height=350,
                margin=dict(l=10, r=10, t=20, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="Esposizione (Beta)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                xaxis=dict(title="Fattori Stile & Macro")
            )
            apply_plotly_theme(fig_barra)
            st.plotly_chart(fig_barra, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        with col_bar2:
            st.markdown("##### 🍩 Decomposizione Varianza Rischio")
            sys_pct = barra_res.get("systematic_risk_pct", 88.0)
            spec_pct = barra_res.get("specific_risk_pct", 12.0)

            fig_pie = go.Figure(data=[go.Pie(
                labels=["Rischio Sistemico (Fattori)", "Rischio Specifico (Residuo)"],
                values=[sys_pct, spec_pct],
                hole=0.6,
                marker=dict(colors=["#58a6ff", "#bc8cff"], line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>%{label}</b><br>Quota Varianza: <b>%{percent}</b><extra></extra>"
            )])
            fig_pie.update_layout(
                template="plotly_dark",
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(orientation="h", y=-0.1)
            )
            apply_plotly_theme(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})
            metric_card("Alpha Multi-Fattoriale (α)", f"{barra_res.get('alpha_annualized', 0.0)*100:+.2f}%", "MSCI Barra 5-Factor", True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_bar_h1, col_bar_h2 = st.columns([3.5, 0.9])
        with col_bar_h1:
            st.markdown("##### 📋 Tabella di Dettaglio dei Fattori MSCI Barra")
        with col_bar_h2:
            csv_barra = df_barra.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica CSV", data=csv_barra, file_name="msci_barra_factors.csv", mime="text/csv", use_container_width=True)

        barra_cfg = {
            "Fattore Barra": st.column_config.TextColumn("Fattore Barra", width="medium"),
            "Beta Fattoriale": st.column_config.NumberColumn("Beta Fattoriale", format="%+.3f"),
            "Statistica t": st.column_config.NumberColumn("Statistica t", format="%+.2f"),
            "Significatività (95%)": st.column_config.TextColumn("Significatività (95%)", width="medium")
        }
        st.dataframe(
            df_barra,
            column_config=barra_cfg,
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.markdown("##### 🤖 Forecast Volatilità a 30 Giorni (Machine Learning Ensemble)")
        from core.financial_analysis import predict_ml_distress_and_volatility
        df_p_ml = st.session_state.get("df_prices")
        ml_res = predict_ml_distress_and_volatility(df_prices=df_p_ml)

        col_ml1, col_ml2 = st.columns([1, 2.5])
        with col_ml1:
            metric_card("Volatilità Predetta 30G", f"{ml_res['predicted_volatility_30d_pct']:.2f}%", "Random Forest Regressor", True)
        with col_ml2:
            st.markdown(f"**Verdetto ML:** {ml_res['verdict']}")
            st.caption("Stima avanzata della volatilità annualizzata a 30 giorni basata su Random Forest Regressor e indicatori tecnici di mercato.")

        # ── SEZIONE FACTOR QUINTILES BACKTESTING ────────────────────────
        st.divider()
        col_fq_h1, col_fq_h2 = st.columns([3.2, 1.1])
        with col_fq_h1:
            st.markdown("#### 🔬 Backtesting di Strategie Multi-Fattoriali (Analisi a 5 Quintili)")
            st.caption("Simulatore di ordinamento periodico su fattori istituzionali (QMJ, Low-Beta BAB, Gross Profitability, Momentum, Deep Value) con scomposizione in 5 quantili e calcolo dello Spread Long-Short (Q1 - Q5).")
        with col_fq_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("ℹ️ Guida al Backtesting Fattoriale a Quintili", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Metodologia a Quintili di Fama-French & AQR</div>
  <div>A ogni intervallo di ribilanciamento (mensile o trimestrale), tutti i titoli dell'universo vengono ordinati in base al punteggio del fattore prescelto e divisi in 5 panieri equi-ponderati:
  <ul style="margin: 4px 0 0 16px; padding: 0;">
    <li><b>Q1 (Top 20%):</b> Massima esposizione al fattore positivo (es. Alta Qualità, Basso Beta, Alto Momentum).</li>
    <li><b>Q2, Q3, Q4:</b> Quintili intermedi di transizione.</li>
    <li><b>Q5 (Bottom 20%):</b> Titoli speculativi o ad esposizione avversa (Junk, High Beta, Neglect).</li>
  </ul>
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Spread Long-Short & Test di Monotonicità</div>
  <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; margin: 6px 0; font-family: monospace; color: #e6edf3;">
    <b>Spread Long-Short:</b> R<sub>L/S</sub> = R<sub>Q1</sub> - R<sub>Q5</sub><br>
    <b>Monotonicità di Spearman:</b> Correlazione di rango tra Quintile (1..5) e Rendimento Annuo (Ideale = +1.0).
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Interpretazione Istituzionale</div>
  <div>Un fattore è statisticamente robusto e sfruttabile quando genera uno <b>Spread Long-Short positivo e persistente</b> e una curva di rendimento <b>strettamente decrescente</b> da Q1 a Q5 (nessun incrocio di stile).</div>
</div>

</div>
""", button_label="💡 Come funziona il Backtest a Quintili")

        from core.factor_library import run_factor_quintile_backtest, FACTOR_PRESET_DEFINITIONS
        
        col_fq_c1, col_fq_c2, col_fq_c3 = st.columns([2.0, 1.2, 1.2])
        with col_fq_c1:
            fact_choice = st.selectbox(
                "Seleziona Strategia Fattoriale da Testare:",
                list(FACTOR_PRESET_DEFINITIONS.keys()),
                format_func=lambda k: FACTOR_PRESET_DEFINITIONS[k]["name"],
                index=0,
                key="sel_factor_quintile_strategy"
            )
        with col_fq_c2:
            rebal_choice = st.radio("Frequenza Ribilanciamento:", ["Mensile (M)", "Trimestrale (Q)"], horizontal=True, key="sel_fq_rebal")
            rebal_code = "Q" if "Trimestrale" in rebal_choice else "M"
        with col_fq_c3:
            lb_choice = st.slider("Lookback Calcolo Score (Giorni):", min_value=30, max_value=252, value=126, step=21, key="sel_fq_lookback")

        st.caption(f"ℹ️ **Razionale Accademico:** {FACTOR_PRESET_DEFINITIONS[fact_choice]['rationale']}")

        # Esecuzione del Backtest a Quintili
        df_rets_port = results.get("returns", pd.DataFrame()) if results else pd.DataFrame()
        if not isinstance(df_rets_port, pd.DataFrame) or df_rets_port.empty:
            df_pr = results.get("df_prices", pd.DataFrame()) if results else pd.DataFrame()
            if isinstance(df_pr, pd.DataFrame) and not df_pr.empty and "price_date" in df_pr.columns:
                df_rets_port = df_pr.pivot(index="price_date", columns="ticker", values="close").pct_change().dropna(how="all")

        fq_res = run_factor_quintile_backtest(
            df_returns=df_rets_port,
            factor_type=fact_choice,
            rebalance_freq=rebal_code,
            lookback_window=lb_choice
        )

        if fq_res.get("valid", False):
            # KPI Cards
            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            with col_k1:
                metric_card("Spread Long-Short (Q1 - Q5)", f"{fq_res['spread_cagr']:+.2f}%", "Extra-rendimento annuo fattore", fq_res['spread_cagr'] > 0)
            with col_k2:
                q1_row = fq_res["metrics_df"][fq_res["metrics_df"]["Quintile"].str.contains("Q1")]
                q1_sharpe = q1_row["Sharpe Ratio"].iloc[0] if not q1_row.empty else 0.0
                metric_card("Sharpe Ratio Q1 (Top 20%)", f"{q1_sharpe:.2f}", "Efficienza paniere alta qualità", q1_sharpe >= 0.7)
            with col_k3:
                q1_ir = q1_row["Information Ratio vs Univ"].iloc[0] if not q1_row.empty else 0.0
                metric_card("Information Ratio Q1 vs Univ", f"{q1_ir:.2f}", "Consistenza rispetto al benchmark", q1_ir >= 0.5)
            with col_k4:
                metric_card("Monotonicità di Spearman", f"{fq_res['monotonicity_score']:+.2f}", fq_res["monotonicity_verdict"].split("(")[0].strip(), fq_res["monotonicity_score"] >= 0.4)

            # Grafico Curve Cumulative dei 5 Quintili + Spread Long-Short
            col_g1, col_g2 = st.columns([2.2, 1.1])
            with col_g1:
                st.markdown("##### 📈 Curve di Crescita Patrimoniale dei 5 Quintili (Base 100)")
                df_cum_q = fq_res["cumulative_df"].reset_index()
                date_col_name = df_cum_q.columns[0]
                
                fig_fq = go.Figure()
                q_colors = {
                    "Q1": "#3fb950",
                    "Q2": "#58a6ff",
                    "Q3": "#d2a8ff",
                    "Q4": "#f59e0b",
                    "Q5": "#f85149",
                    "Long_Short_Spread": "#ff9900",
                    "Equal_Weight_Univ": "#8b949e"
                }
                q_labels = {
                    "Q1": "Q1 (Top 20% · High Factor)",
                    "Q2": "Q2 (Quintile 2)",
                    "Q3": "Q3 (Mediano)",
                    "Q4": "Q4 (Quintile 4)",
                    "Q5": "Q5 (Bottom 20% · Junk)",
                    "Long_Short_Spread": "⚡ Spread Long-Short (Q1 - Q5)",
                    "Equal_Weight_Univ": "🌐 Universo Equi-Ponderato"
                }

                for col_k in ["Q1", "Q2", "Q3", "Q4", "Q5", "Equal_Weight_Univ", "Long_Short_Spread"]:
                    if col_k in df_cum_q.columns:
                        is_main = col_k in ["Q1", "Q5", "Long_Short_Spread"]
                        fig_fq.add_trace(go.Scatter(
                            x=df_cum_q[date_col_name],
                            y=df_cum_q[col_k],
                            mode="lines",
                            name=q_labels.get(col_k, col_k),
                            line=dict(
                                color=q_colors.get(col_k, "#ffffff"),
                                width=3.0 if is_main else 1.5,
                                dash="solid" if col_k != "Equal_Weight_Univ" else "dash"
                            ),
                            hovertemplate=f"<b>{q_labels.get(col_k, col_k)}</b>: %{{y:.1f}}<extra></extra>"
                        ))

                fig_fq.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(13,17,23,0.7)",
                    margin=dict(l=15, r=15, t=25, b=15),
                    height=360,
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(title="Valore Portafoglio (Base 100)", gridcolor="rgba(255,255,255,0.06)"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                apply_plotly_theme(fig_fq)
                st.plotly_chart(fig_fq, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

            with col_g2:
                st.markdown("##### 📊 Rendimento Annuo per Quintile")
                df_bar_q = fq_res["metrics_df"][fq_res["metrics_df"]["Quintile"].str.startswith("Q")].copy()
                fig_bar_q = px.bar(
                    df_bar_q,
                    x="Quintile",
                    y="Rendimento Annuo CAGR %",
                    color="Rendimento Annuo CAGR %",
                    color_continuous_scale=["#f85149", "#58a6ff", "#3fb950"],
                    template="plotly_dark",
                    height=360
                )
                fig_bar_q.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=25, b=10),
                    xaxis=dict(title=None, tickangle=-25),
                    coloraxis_showscale=False
                )
                fig_bar_q.update_traces(hovertemplate="<b>%{x}</b><br>CAGR: <b>%{y:+.2f}%</b><extra></extra>")
                apply_plotly_theme(fig_bar_q)
                st.plotly_chart(fig_bar_q, use_container_width=True, config={"displayModeBar": False})

            # Tabella Dettagliata Analytics per Quintile
            col_t_h1, col_t_h2 = st.columns([3.2, 1.0])
            with col_t_h1:
                st.markdown("##### 📋 Tabella Comparativa di Performance e Rischio per Quintile")
            with col_t_h2:
                csv_fq = fq_res["metrics_df"].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Scarica Analytics CSV",
                    data=csv_fq,
                    file_name=f"factor_quintile_analysis_{fact_choice}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_factor_quintiles"
                )

            st.dataframe(
                fq_res["metrics_df"],
                column_config={
                    "Quintile": st.column_config.TextColumn("Paniere Quintile", width="medium"),
                    "Rendimento Annuo CAGR %": st.column_config.NumberColumn("CAGR Ann %", format="%+.2f%%"),
                    "Volatilità Annua %": st.column_config.NumberColumn("Volatilità %", format="%.2f%%"),
                    "Sharpe Ratio": st.column_config.NumberColumn("Sharpe Ratio", format="%.2f"),
                    "Max Drawdown %": st.column_config.NumberColumn("Max Drawdown", format="%.2f%%"),
                    "Win Rate Mensile %": st.column_config.NumberColumn("Win Rate Mensile", format="%.1f%%"),
                    "Information Ratio vs Univ": st.column_config.NumberColumn("Information Ratio", format="%.2f")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info(fq_res.get("message", "Dati non sufficienti per calcolare il backtest a quintili."))

# ── TAB 6: FIXED INCOME, YTM & Z-SPREAD (YAS) ──────────────────────
elif active_quant_tab == "🏛️ Fixed Income & Z-Spread":
    col_fi_h1, col_fi_h2 = st.columns([3.0, 1.3])
    with col_fi_h1:
        st.markdown("#### 🏛️ Fixed Income Istituzionale & Z-Spread Cockpit (Bloomberg YAS Style)")
        st.caption("Analisi quantitativa per Titoli di Stato ed Obbligazioni Corporate • Yield to Maturity (YTM), Duration, Convessità, DV01, Z-Spread e Probabilità di Default CDS.")
    with col_fi_h2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida a Fixed Income, Duration & Z-Spread", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Metriche di Sensibilità Obbligazionaria</div>
  <div>
    • <b>Yield to Maturity (YTM):</b> Tasso interno di rendimento (TIR) che eguaglia il valore attuale dei flussi al prezzo di mercato.<br>
    • <b>Macaulay Duration:</b> Scadenza media ponderata per il valore attuale dei flussi di cassa.<br>
    • <b>Modified Duration:</b> Sensibilità percentuale del prezzo per una variazione dell'1% (100 bps) nei tassi di interesse.<br>
    • <b>Convexity:</b> Curvatura di 2° ordine che quantifica il vantaggio per cui i bond guadagnano di più quando i tassi scendono e perdono di meno quando i tassi salgono.<br>
    • <b>DV01 / PVBP:</b> Variazione del valore monetario del titolo per ogni movimento di 1 punto base (0.01%) di rendimento.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Z-Spread (Zero-Volatility Spread)</div>
  <div>Lo spread costante in punti base (bps) da aggiungere a ciascun nodo della curva spot sovrana per riprodurre esattamente il prezzo di mercato del bond.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🛡️ Probabilità di Default Implicita (CDS)</div>
  <div>Stima dell'intensità di default (Hazard Rate &lambda; = Spread / (1 - Recovery Rate)) e probabilità cumulativa di insolvenza su orizzonti da 1 a 30 anni.</div>
</div>

</div>
""", button_label="💡 Guida Fixed Income")

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # Selezione Titolo Benchmark o Custom
    preset_keys = ["IT10Y", "DE10Y", "US10Y", "CORP_ENI", "CUSTOM"]
    preset_names = [
        "🇮🇹 BTP Decennale 4.00% (Italia)",
        "🇩🇪 Bund Decennale 2.50% (Germania)",
        "🇺🇸 US 10-Year Treasury 4.25% (USA)",
        "🏢 ENI SpA Sustainability 3.875% (Corporate)",
        "✏️ Obbligazione Personalizzata (Custom)"
    ]
    
    col_sel1, col_sel2 = st.columns([2.5, 1.5])
    with col_sel1:
        selected_idx = st.selectbox(
            "Seleziona Strumento Obbligazionario Benchmark o Personalizzato:",
            options=range(len(preset_names)),
            format_func=lambda i: preset_names[i],
            index=0,
            key="fi_preset_choice"
        )
    
    preset_choice = preset_keys[selected_idx]
    
    # Parametri iniziali
    if preset_choice != "CUSTOM":
        p_data = INSTITUTIONAL_BOND_PRESETS[preset_choice]
        def_face = float(p_data.get("face_value", 100.0))
        def_coupon = float(p_data["coupon_rate"] * 100.0)
        def_mat = float(p_data["maturity_years"])
        def_price = float(p_data["market_price"])
        def_freq = int(p_data["coupon_freq"])
        def_cds = float(p_data.get("cds_5y_bps", 80.0))
        curr_symbol = "€" if p_data.get("currency") == "EUR" else "$"
    else:
        def_face = 100.0
        def_coupon = 4.50
        def_mat = 7.0
        def_price = 99.50
        def_freq = 2
        def_cds = 110.0
        curr_symbol = "€"

    # Input interattivi
    with st.expander("⚙️ Parametri Finanziari dell'Obbligazione", expanded=True):
        col_inp1, col_inp2, col_inp3, col_inp4, col_inp5, col_inp6 = st.columns(6)
        with col_inp1:
            inp_face = st.number_input("Valore Nominale", min_value=1.0, value=def_face, step=10.0, key="fi_face_val")
        with col_inp2:
            inp_coupon = st.number_input("Tasso Cedolare (%)", min_value=0.0, max_value=25.0, value=def_coupon, step=0.10, key="fi_coupon_val")
        with col_inp3:
            inp_mat = st.number_input("Scadenza (Anni)", min_value=0.1, max_value=50.0, value=def_mat, step=0.5, key="fi_mat_val")
        with col_inp4:
            inp_price = st.number_input("Prezzo di Mercato", min_value=1.0, max_value=300.0, value=def_price, step=0.25, key="fi_price_val")
        with col_inp5:
            inp_freq = st.selectbox("Frequenza Cedola", options=[1, 2, 4], format_func=lambda x: "Annuale (1x)" if x==1 else ("Semestrale (2x)" if x==2 else "Trimestrale (4x)"), index=(0 if def_freq==1 else (1 if def_freq==2 else 2)), key="fi_freq_val")
        with col_inp6:
            inp_cds = st.number_input("Spread CDS 5Y (bps)", min_value=0.0, max_value=2000.0, value=def_cds, step=5.0, key="fi_cds_val")

    # Calcolo metriche
    coupon_dec = inp_coupon / 100.0
    bond_res = compute_bond_analytics(
        face_value=inp_face,
        coupon_rate=coupon_dec,
        maturity_years=inp_mat,
        market_price=inp_price,
        coupon_frequency=inp_freq
    )
    z_spread_bps = compute_z_spread(
        face_value=inp_face,
        coupon_rate=coupon_dec,
        maturity_years=inp_mat,
        market_price=inp_price,
        spot_curve_fn_or_params=None,
        coupon_frequency=inp_freq
    )
    cds_res = compute_cds_implied_default_probability(
        cds_spread_bps=inp_cds,
        recovery_rate=0.40
    )

    # 4 Executive KPI Cards
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        metric_card(
            "Yield to Maturity (YTM)",
            f"{bond_res['ytm_pct']:.3f}%",
            f"Cedola Corrente: {bond_res['current_yield_pct']:.2f}%",
            True
        )
    with col_kpi2:
        metric_card(
            "Modified Duration",
            f"{bond_res['modified_duration']:.2f}x",
            f"Macaulay Duration: {bond_res['macaulay_duration_years']:.2f} Anni",
            True
        )
    with col_kpi3:
        metric_card(
            "Convexity (Convessità)",
            f"{bond_res['convexity']:.2f}",
            f"DV01 / PVBP: {curr_symbol} {bond_res['dv01']:.4f} / bp",
            True
        )
    with col_kpi4:
        metric_card(
            "Z-Spread & Hazard Rate",
            f"{z_spread_bps:+.1f} bps",
            f"Hazard Rate CDS: {cds_res['implied_hazard_rate_pct']:.2f}%/anno",
            True
        )

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # Simulatore Interattivo Shock di Rendimento & Price-Yield Curve
    col_plot1, col_plot2 = st.columns([1.8, 1.2])
    with col_plot1:
        st.markdown("##### 📈 Curva Prezzo-Rendimento & Guadagno di Convessità")
        st.caption("Confronto tra Curva di Prezzo Esatta, Approssimazione di 1° Ordine (Sola Duration) e di 2° Ordine (Duration + Convessità).")
        
        # Genera punti per la curva continua
        ytm_center = bond_res['ytm_pct'] / 100.0
        y_shifts = np.linspace(-0.03, 0.03, 60)
        y_points = (ytm_center + y_shifts) * 100.0
        exact_prices = [compute_bond_price_from_ytm(inp_face, coupon_dec, inp_mat, ytm_center + dy, inp_freq) for dy in y_shifts]
        
        # Taylor 1 (Duration) e Taylor 2 (Duration + Convexity)
        taylor_1_prices = [inp_price * (1.0 - bond_res['modified_duration'] * dy) for dy in y_shifts]
        taylor_2_prices = [inp_price * (1.0 - bond_res['modified_duration'] * dy + 0.5 * bond_res['convexity'] * (dy**2)) for dy in y_shifts]

        fig_py = go.Figure()
        fig_py.add_trace(go.Scatter(
            x=y_points, y=exact_prices,
            mode='lines', name='Prezzo Esatto P(y)',
            line=dict(color='#ff9900', width=3.5)
        ))
        fig_py.add_trace(go.Scatter(
            x=y_points, y=taylor_2_prices,
            mode='lines', name='Taylor 2° Ordine (Duration + Convexity)',
            line=dict(color='#00c853', width=2, dash='dash')
        ))
        fig_py.add_trace(go.Scatter(
            x=y_points, y=taylor_1_prices,
            mode='lines', name='Taylor 1° Ordine (Solo Duration)',
            line=dict(color='#f85149', width=1.5, dash='dot')
        ))
        # Punto di prezzo corrente
        fig_py.add_trace(go.Scatter(
            x=[bond_res['ytm_pct']], y=[inp_price],
            mode='markers+text', name='Prezzo Attuale',
            marker=dict(color='#ffffff', size=10, symbol='diamond'),
            text=[f"YTM {bond_res['ytm_pct']:.2f}%"], textposition='top center'
        ))

        fig_py.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(13,17,23,0.7)',
            margin=dict(l=20, r=20, t=30, b=20),
            height=360,
            xaxis=dict(title="Yield to Maturity (%)", gridcolor='rgba(255,255,255,0.06)'),
            yaxis=dict(title=f"Prezzo Obbligazione ({curr_symbol})", gridcolor='rgba(255,255,255,0.06)'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_py, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with col_plot2:
        df_cds = cds_res["default_probability_curve"]
        col_cds_h1, col_cds_h2 = st.columns([2.0, 1.2])
        with col_cds_h1:
            st.markdown("##### 🛡️ Curva Default Implicita (CDS)")
        with col_cds_h2:
            csv_cds = df_cds.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica CDS CSV", data=csv_cds, file_name=f"cds_default_curve_{preset_choice.lower()}.csv", mime="text/csv", use_container_width=True, key="btn_dl_cds_curve")
        st.caption(f"Term structure cumulativa di default basata sullo spread CDS di **{inp_cds:.0f} bps** (Recovery: 40%).")
        
        fig_cds = go.Figure()
        fig_cds.add_trace(go.Scatter(
            x=df_cds["tenor_years"], y=df_cds["cumulative_default_prob_pct"],
            mode='lines+markers', name='Probabilità di Default Cumulativa (%)',
            line=dict(color='#f85149', width=3),
            fill='tozeroy', fillcolor='rgba(248,81,73,0.12)',
            marker=dict(size=7, color='#f85149')
        ))
        fig_cds.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(13,17,23,0.7)',
            margin=dict(l=20, r=20, t=30, b=20),
            height=360,
            xaxis=dict(title="Scadenza (Anni)", gridcolor='rgba(255,255,255,0.06)'),
            yaxis=dict(title="Probabilità Cumulativa Default (%)", gridcolor='rgba(255,255,255,0.06)'),
            showlegend=False
        )
        st.plotly_chart(fig_cds, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    # Tabella di Sensibilità a Shock di Rendimento
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    df_sens = bond_res["sensitivity_table"].copy()
    col_sens_h1, col_sens_h2 = st.columns([3.0, 1.0])
    with col_sens_h1:
        st.markdown("##### 📋 Matrice di Sensibilità Istituzionale a Shock di Tasso (Basis Points Shock)")
    with col_sens_h2:
        csv_sens = df_sens.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica Sensibilità CSV", data=csv_sens, file_name=f"bond_sensitivity_{preset_choice.lower()}.csv", mime="text/csv", use_container_width=True, key="btn_dl_bond_sens")
    
    sens_cfg = {
        "shift_bps": st.column_config.NumberColumn("Shock Tasso", format="%+d bps"),
        "new_ytm_pct": st.column_config.NumberColumn("Nuovo YTM", format="%.3f%%"),
        "exact_price": st.column_config.NumberColumn(f"Prezzo Esatto ({curr_symbol})", format="%.2f"),
        "pct_change_exact": st.column_config.NumberColumn("Var % Prezzo Esatta", format="%+.2f%%"),
        "pct_change_duration_only": st.column_config.NumberColumn("Stima Solo Duration", format="%+.2f%%"),
        "pct_change_duration_plus_convexity": st.column_config.NumberColumn("Stima Duration + Convexity", format="%+.2f%%"),
        "convexity_gain_pct": st.column_config.NumberColumn("Vantaggio Convessità", format="%+.2f%%")
    }
    st.dataframe(
        df_sens,
        column_config=sens_cfg,
        use_container_width=True,
        hide_index=True
    )


