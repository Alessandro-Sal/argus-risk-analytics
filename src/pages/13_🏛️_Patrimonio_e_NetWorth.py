# ============================================================
# src/pages/13_🏛️_Patrimonio_e_NetWorth.py
# ARGUS Wealth Management — Consolidated Net Worth & Balance Sheet
# ============================================================

from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.ui_utils import (
    apply_chart_theme,
    apply_plotly_theme,
    ensure_portal_context,
    ensure_portfolio_loaded,
    fmt_eur,
    fmt_pct,
    inject_custom_css,
    metric_card,
    render_data_table,
    render_kpi_card,
    render_omni_command_bar,
    render_segmented_tabs,
    render_table_with_export,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    section,
)
from core.wealth.wealth_db import (
    get_cashflow_records,
    get_linked_risk_portfolios_summary,
    get_pension_plans,
    get_physical_assets,
    get_wealth_accounts,
    get_wealth_portfolios,
    init_wealth_db,
    save_wealth_account,
)
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_family_office_multi_entity_consolidation,
    compute_multi_currency_fx_hedging_engine,
    compute_multi_year_balance_comparison,
    compute_personal_balance_sheet,
    compute_total_wealth_brinson_attribution,
    generate_advisory_pitchbook_html,
    generate_advisory_pitchbook_pdf,
    generate_executive_tear_sheet_html,
    generate_executive_tear_sheet_pdf,
    generate_personal_balance_sheet_html,
    generate_personal_balance_sheet_pdf,
    generate_personal_balance_sheet_tearsheet_html,
    generate_personal_balance_sheet_tearsheet_pdf,
)
from core.wealth.wealth_modals import render_balance_sheet_methodology_modal
from core.wealth.wealth_snapshot import get_wealth_snapshots_history
from core.wealth.wealth_temporal_engine import (
    compute_wealth_benchmark_comparison,
    compute_wealth_growth_attribution,
    compute_wealth_monthly_matrix,
    compute_wealth_rolling_metrics,
    compute_wealth_seasonality_patterns,
    compute_wealth_temporal_progression,
    compute_wealth_underwater_drawdowns,
)


# ── HIGH-PERFORMANCE STREAMLIT CACHING LAYER ─────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_wealth_portfolios(_engine):
    return get_wealth_portfolios(_engine)


@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_consolidated_net_worth(_engine, portfolio_id: int):
    return compute_consolidated_net_worth(_engine, portfolio_id=portfolio_id)


@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_wealth_accounts(_engine, portfolio_id: int):
    return get_wealth_accounts(_engine, portfolio_id=portfolio_id)


@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_family_office_suite(_engine, portfolio_id: int):
    fo = compute_family_office_multi_entity_consolidation(_engine, portfolio_id=portfolio_id)
    fx = compute_multi_currency_fx_hedging_engine(_engine, portfolio_id=portfolio_id)
    br = compute_total_wealth_brinson_attribution(_engine, portfolio_id=portfolio_id)
    return fo, fx, br


@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_temporal_suite(_engine, portfolio_id: int, timeframe_months: int, adjust_inflation: bool, cache_bust: str = "v3_exact_split_phys_pens"):
    prog = compute_wealth_temporal_progression(_engine, portfolio_id=portfolio_id, timeframe_months=timeframe_months, adjust_inflation=adjust_inflation)
    attr = compute_wealth_growth_attribution(_engine, portfolio_id=portfolio_id, timeframe_months=timeframe_months, adjust_inflation=adjust_inflation)
    bench = compute_wealth_benchmark_comparison(_engine, portfolio_id=portfolio_id, timeframe_months=timeframe_months)
    roll = compute_wealth_rolling_metrics(_engine, portfolio_id=portfolio_id, timeframe_months=timeframe_months)
    under = compute_wealth_underwater_drawdowns(_engine, portfolio_id=portfolio_id, timeframe_months=timeframe_months)
    seas = compute_wealth_seasonality_patterns(_engine, portfolio_id=portfolio_id)
    matrix = compute_wealth_monthly_matrix(_engine, portfolio_id=portfolio_id)
    return prog, attr, bench, roll, under, seas, matrix


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_pitchbook_pdf(_engine, pid: int) -> bytes:
    return generate_advisory_pitchbook_pdf(_engine, portfolio_id=pid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_tear_sheet_pdf(_engine, pid: int) -> bytes:
    return generate_executive_tear_sheet_pdf(_engine, portfolio_id=pid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_pitchbook_html(_engine, pid: int) -> str:
    return generate_advisory_pitchbook_html(_engine, portfolio_id=pid)



@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_personal_balance_sheet(_engine, pid: int = 1, yr: Optional[int] = None) -> Dict[str, Any]:
    return compute_personal_balance_sheet(_engine, portfolio_id=pid, year=yr)


@st.cache_data(ttl=60, show_spinner=False)
def _load_cached_multi_year_balance_comparison(_engine, pid: int = 1) -> Dict[str, Any]:
    return compute_multi_year_balance_comparison(_engine, portfolio_id=pid)



@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_balance_sheet_pdf(_engine, pid: int, yr: Optional[int] = None) -> bytes:
    return generate_personal_balance_sheet_pdf(_engine, portfolio_id=pid, year=yr)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_balance_sheet_tearsheet_pdf(_engine, pid: int, yr: Optional[int] = None) -> bytes:
    return generate_personal_balance_sheet_tearsheet_pdf(_engine, portfolio_id=pid, year=yr)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_balance_sheet_html(_engine, pid: int, yr: Optional[int] = None) -> str:
    return generate_personal_balance_sheet_html(_engine, portfolio_id=pid, year=yr)


st.set_page_config(page_title="Patrimonio & Net Worth | ARGUS Wealth", page_icon="🏛️", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

# Connessione DB
offline_mode = bool(st.session_state.get("offline_mode", False))
db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
raw_db = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
db_name = raw_db if raw_db else "wealth"
st.session_state.wealth_db_name = db_name
st.session_state.db_name = db_name
engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)
init_wealth_db(engine)

ensure_portfolio_loaded(module_type="wealth")


# ── CONTROLLO MODALITÀ SNAPSHOT STORICO O LIVE ───────────────
is_snapshot_mode = ("wealth_active_snapshot" in st.session_state and st.session_state["wealth_active_snapshot"] is not None)

if is_snapshot_mode:
    act_snap = st.session_state["wealth_active_snapshot"]
    details = act_snap.get("details", {})
    summary = details.get("summary", {})

    st.markdown(f"""
    <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-weight:800; color:#818cf8; font-size:14px;">📸 MODALITÀ RECALL SNAPSHOT STORICO:</span>
            <span style="color:#ffffff; font-weight:700; font-size:14px; margin-left:8px;">{act_snap.get('snapshot_name')}</span>
            <span style="color:#94a3b8; font-size:12px; margin-left:8px;">(Data Riferimento: {act_snap.get('snapshot_date')})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔄 Ripristina Dati Live / Esci da Snapshot Storico", type="secondary", key="btn_exit_snap_nw"):
        st.session_state.pop("wealth_active_snapshot", None)
        st.cache_data.clear()
        st.rerun()

    tot_nw = float(summary.get("total_net_worth", act_snap.get("total_net_worth", 0.0)))
    liq_cash = float(summary.get("liquid_cash", act_snap.get("liquid_assets", 0.0)))
    fin_inv = float(summary.get("financial_investments", act_snap.get("financial_investments", 0.0)))
    phys_assets = float(summary.get("physical_assets", act_snap.get("physical_assets_total", 0.0)))
    watches_val = float(summary.get("luxury_watches_total", act_snap.get("watches_total", 0.0)))
    re_val = float(summary.get("real_estate_total", act_snap.get("real_estate_total", 0.0)))
    metals_val = float(summary.get("precious_metals_total", 0.0))
    pens_val = float(summary.get("pension_total", act_snap.get("pension_total", 0.0)))
    liab_val = float(summary.get("total_liabilities", act_snap.get("total_liabilities", 0.0)))
    health_sc = float(summary.get("wealth_health_score", act_snap.get("wealth_health_score", 0.0)))
    runway_m = float(summary.get("runway_months", act_snap.get("emergency_runway_months", 0.0)))
    sav_rate = float(summary.get("savings_rate_pct", act_snap.get("savings_rate_pct", 0.0)))

    df_accounts = pd.DataFrame(details.get("accounts", []))
else:
    # Modalità Live ad alte prestazioni con Caching
    df_prof = _load_cached_wealth_portfolios(engine)
    prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
    current_pid = st.session_state.get("wealth_active_portfolio_id")

    if current_pid is None or current_pid not in prof_map:
        current_pid = None
        st.session_state["wealth_active_portfolio_id"] = None

    if current_pid is None:
        render_omni_command_bar(portal="wealth", context_name="Nessun Profilo", key_suffix="p13")
        from core.ui_utils import render_wealth_profile_picker
        render_wealth_profile_picker(engine, prof_map, key_prefix="p13_picker")
        st.stop()

    nw = _load_cached_consolidated_net_worth(engine, portfolio_id=current_pid)
    tot_nw = nw.total_net_worth
    liq_cash = nw.liquid_cash
    fin_inv = nw.financial_investments
    phys_assets = nw.physical_assets
    watches_val = nw.luxury_watches_total
    re_val = nw.real_estate_total
    metals_val = nw.precious_metals_total
    pens_val = nw.pension_total
    liab_val = nw.total_liabilities
    health_sc = nw.wealth_health_score
    runway_m = nw.runway_months
    sav_rate = nw.savings_rate_pct

    df_accounts = _load_cached_wealth_accounts(engine, portfolio_id=current_pid)

prof_title = prof_map.get(current_pid, "Nessun Profilo")
render_omni_command_bar(portal="wealth", context_name=prof_title, key_suffix="p13")
render_wealth_executive_badges(nw)

# ── SMART FINANCIAL WATCHDOG SENTINEL ────────────────────────
from core.wealth.wealth_watchdog import WealthWatchdog, render_wealth_watchdog_banner

summary_watchdog_dict = {
    "total_net_worth": tot_nw,
    "liquid_cash": liq_cash,
    "financial_investments": fin_inv,
    "physical_assets": phys_assets,
    "real_estate_total": re_val,
    "real_estate_equity": re_val - liab_val,
    "pension_total": pens_val,
    "total_liabilities": liab_val,
    "wealth_health_score": health_sc,
    "runway_months": runway_m,
    "savings_rate_pct": sav_rate
}
watchdog_alerts = WealthWatchdog.evaluate_all_alerts(summary_watchdog_dict)
render_wealth_watchdog_banner(watchdog_alerts)

if not is_snapshot_mode and len(prof_map) > 1:
    head_c1, head_c2, head_c3 = st.columns([3.2, 1.0, 1.0])
    with head_c1:
        st.title("🏛️ ARGUS Wealth — Patrimonio & Net Worth")
        st.caption(f"Consolidamento olistico del patrimonio netto • Aggiornato al {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    with head_c2:
        st.write("")
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="nw_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()
    with head_c3:
        st.write("")
        boardroom_mode = st.toggle("🏛️ Boardroom", value=st.session_state.get("wealth_boardroom_mode", False), key="wealth_boardroom_toggle", help="Attiva la modalità presentazione esecutiva per CDA e riunioni di famiglia.")
        st.session_state["wealth_boardroom_mode"] = boardroom_mode
else:
    head_c1, head_c2 = st.columns([4.0, 1.2])
    with head_c1:
        st.title("🏛️ ARGUS Wealth — Patrimonio & Net Worth")
        st.caption(f"Consolidamento olistico del patrimonio netto • Aggiornato al {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    with head_c2:
        st.write("")
        boardroom_mode = st.toggle("🏛️ Boardroom Mode", value=st.session_state.get("wealth_boardroom_mode", False), key="wealth_boardroom_toggle_single", help="Attiva la modalità presentazione esecutiva per CDA e riunioni di famiglia.")
        st.session_state["wealth_boardroom_mode"] = boardroom_mode

if st.session_state.get("wealth_boardroom_mode", False):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(22,27,34,0.98) 100%); border: 1px solid rgba(255, 153, 0, 0.4); border-radius: 16px; padding: 24px 30px; margin: 15px 0 25px 0; box-shadow: 0 20px 50px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">🏛️</span>
                <div>
                    <div style="font-size: 18px; font-weight: 800; color: #ff9900; letter-spacing: 1px;">ARGUS FAMILY OFFICE &bull; EXECUTIVE BOARDROOM</div>
                    <div style="font-size: 12px; color: #8b949e;">Presentazione Istituzionale Consolidata &bull; Profilo: <b>{prof_title}</b> &bull; Data: <b>{datetime.now().strftime('%d/%m/%Y')}</b></div>
                </div>
            </div>
            <div style="display: flex; gap: 10px;">
                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 12px; font-weight: 700; padding: 6px 14px; border-radius: 20px;">
                    🛡️ Health Score: {health_sc:.0f}/100
                </div>
            </div>
        </div>
        <div style="text-align: center; padding: 20px 0; border-top: 1px solid rgba(255,255,255,0.06); border-bottom: 1px solid rgba(255,255,255,0.06);">
            <div style="font-size: 13px; font-weight: 600; color: #8b949e; letter-spacing: 1.5px; text-transform: uppercase;">Patrimonio Netto Consolidato Globale</div>
            <div style="font-size: 46px; font-weight: 850; color: #f0f6fc; font-family: 'Outfit', sans-serif; letter-spacing: -0.5px; margin: 4px 0;">{fmt_eur(tot_nw)}</div>
            <div style="font-size: 13px; color: #34d399; font-weight: 600;">💧 Runway Liquidità: <b>{runway_m:.1f} Mesi</b> &nbsp;|&nbsp; 💰 Tasso di Risparmio: <b>{sav_rate:.1f}%</b> &nbsp;|&nbsp; 📉 Debito/Attivo: <b>{(liab_val / max(1.0, tot_nw + liab_val) * 100):.1f}%</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6 Monumental Bento Cards
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        metric_card("💧 Liquidità & Depositi a Vista", fmt_eur(liq_cash), delta=f"{liq_cash/max(1.0, tot_nw)*100:.1f}% del Net Worth", delta_color="normal")
    with bc2:
        metric_card("📈 Investimenti Finanziari (Titoli/Crypto)", fmt_eur(fin_inv), delta=f"{fin_inv/max(1.0, tot_nw)*100:.1f}% del Net Worth", delta_color="normal")
    with bc3:
        metric_card("🏡 Net Equity Immobiliare", fmt_eur(re_val - liab_val), delta=f"Lordo: {fmt_eur(re_val)} | Debiti: {fmt_eur(liab_val)}", delta_color="normal")

    st.write("")
    bc4, bc5, bc6 = st.columns(3)
    with bc4:
        metric_card("⌚ Caveau, Orologi & Metalli", fmt_eur(phys_assets), delta=f"Orologi: {fmt_eur(watches_val)}", delta_color="normal")
    with bc5:
        metric_card("🛡️ Previdenza Complementare", fmt_eur(pens_val), delta="Fondi Pensione & PIP", delta_color="normal")
    with bc6:
        metric_card("📉 Passività & Mutui Residui", fmt_eur(liab_val), delta="DSTI Sostenibile", delta_color="inverse" if liab_val > 0 else "normal")

    st.write("")
    # Grafici Istituzionali Boardroom
    col_bg1, col_bg2 = st.columns([1.2, 1.8])
    with col_bg1:
        st.markdown("##### 🌐 Allocazione Olistica del Patrimonio")
        labels = ["Liquidità", "Investimenti", "Immobili", "Caveau", "Previdenza"]
        values = [max(0.0, liq_cash), max(0.0, fin_inv), max(0.0, re_val - liab_val), max(0.0, phys_assets), max(0.0, pens_val)]
        colors = ["#38bdf8", "#818cf8", "#10b981", "#fbbf24", "#a78bfa"]
        fig_donut = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.55,
            marker=dict(colors=colors),
            textinfo="label+percent",
            hoverinfo="label+value+percent"
        )])
        fig_donut.update_layout(height=320, showlegend=False)
        apply_chart_theme(fig_donut, portal_mode="wealth")
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_bg2:
        st.markdown("##### 🏛️ Stato Patrimoniale & Solvibilità (Attivo vs Passivo)")
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Attività Totali", x=["Patrimonio"], y=[tot_nw + liab_val], marker_color="#10b981", text=[fmt_eur(tot_nw + liab_val)], textposition="auto"))
        fig_bar.add_trace(go.Bar(name="Debiti / Mutui", x=["Patrimonio"], y=[liab_val], marker_color="#ef4444", text=[fmt_eur(liab_val)], textposition="auto"))
        fig_bar.add_trace(go.Bar(name="Patrimonio Netto", x=["Patrimonio"], y=[tot_nw], marker_color="#ff9900", text=[fmt_eur(tot_nw)], textposition="auto"))
        fig_bar.update_layout(
            barmode="group",
            height=320,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        apply_chart_theme(fig_bar, portal_mode="wealth")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Toolbar Esportazione e Uscita Boardroom
    st.divider()
    col_b_act1, col_b_act2, col_b_act3 = st.columns([1.5, 1.5, 1.0])
    with col_b_act1:
        pitchbook_pdf = _get_cached_pitchbook_pdf(engine, current_pid)
        date_slug = datetime.now().strftime('%Y%m%d')
        st.download_button(
            label="📥 Scarica Advisory Pitchbook PDF (300 DPI)",
            data=pitchbook_pdf,
            file_name=f"argus_boardroom_dossier_{date_slug}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    with col_b_act2:
        tear_sheet_pdf = _get_cached_tear_sheet_pdf(engine, current_pid)
        st.download_button(
            label="📑 Scarica Executive Tear Sheet (PDF)",
            data=tear_sheet_pdf,
            file_name=f"argus_tear_sheet_{date_slug}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_b_act3:
        if st.button("❌ Esci da Boardroom Mode", use_container_width=True):
            st.session_state["wealth_boardroom_mode"] = False
            st.rerun()

    st.stop()

# ── TOP KPI ROW (DUE RIGHE X 3 COLONNE) ─────────────────────
r1_c1, r1_c2, r1_c3 = st.columns(3)
with r1_c1:
    metric_card("Patrimonio Netto", fmt_eur(tot_nw), delta="Consolidato Globale", delta_color="normal")
with r1_c2:
    metric_card("Liquidità & Cash", fmt_eur(liq_cash), delta=f"Runway {runway_m:.1f} Mesi", delta_color="normal")
with r1_c3:
    metric_card("Investimenti Finanziari", fmt_eur(fin_inv), delta="Portafogli Titoli + Crypto", delta_color="normal")

st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

r2_c1, r2_c2, r2_c3 = st.columns(3)
with r2_c1:
    metric_card("Asset Caveau & Fisici", fmt_eur(phys_assets), delta=f"Orologi: {fmt_eur(watches_val)}", delta_color="normal")
with r2_c2:
    metric_card("Previdenza Integrativa", fmt_eur(pens_val), delta="Fondi Pensione & PIP", delta_color="normal")
with r2_c3:
    metric_card("Wealth Health Score", f"{health_sc:.0f} / 100", delta="Indice di Solidità", delta_color="normal")

st.divider()

# ── MACRO-TAB DEL PATRIMONIO PER MASSIMA EFFICIENZA & CHIAREZZA ───
main_tab_alloc, main_tab_sheet, main_tab_temporal, main_tab_fo, main_tab_fx, main_tab_stress, main_tab_struct = st.tabs([
    "📊 Bilancio & Allocazione",
    "📑 Bilancio Personale & Stato Patrimoniale",
    "⏳ Wealth Temporal Desk",
    "🏛️ Family Office & Holding",
    "💱 Rischio FX & Attribuzione Brinson",
    "🌪️ Global Wealth Stress-Testing",
    "💎 Prodotti Strutturati & PRIIPs/SFDR"
])

# ══════════════════════════════════════════════════════════════
# TAB 1: BILANCIO, ALLOCAZIONE & HEALTH SCORE
# ══════════════════════════════════════════════════════════════
with main_tab_alloc:
    # ── EXECUTIVE TEAR SHEET & ADVISORY PITCHBOOK TOOLBAR ──────────
    pitchbook_pdf = _get_cached_pitchbook_pdf(engine, current_pid)
    tear_sheet_pdf = _get_cached_tear_sheet_pdf(engine, current_pid)
    tear_sheet_html = _get_cached_pitchbook_html(engine, current_pid)
    date_slug = datetime.now().strftime('%Y%m%d')
    prof_slug = str(prof_map.get(current_pid, 'portfolio')).lower().replace(' ', '_')

    st.markdown("""
    <div style="background:rgba(22,27,34,0.75); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #10b981; border-radius:10px; padding:12px 16px; margin-bottom:10px;">
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:34px; height:34px; border-radius:8px; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0;">
                📑
            </div>
            <div>
                <div style="font-size:13.5px; font-weight:750; color:#ffffff; letter-spacing:0.3px;">Executive Advisory Dossier &amp; Pitchbook (Family Office / Private Banking)</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:1px;">Report patrimoniale istituzionale multipagina con Stato Patrimoniale 360°, Goal-Based Probability, Real Estate LTV e Tax-Smart Rebalancing.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    from core.wealth.wealth_modals import render_wealth_methodology_modal

    ts_c1, ts_c2, ts_c3, ts_c4, ts_c5 = st.columns([1.3, 1.1, 0.8, 0.8, 1.1])
    with ts_c1:
        st.download_button(
            label="📥 Scarica Pitchbook PDF",
            data=pitchbook_pdf,
            file_name=f"argus_advisory_pitchbook_{prof_slug}_{date_slug}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )
    with ts_c2:
        st.download_button(
            label="📑 Tear-Sheet Sintetica",
            data=tear_sheet_pdf,
            file_name=f"argus_tear_sheet_{prof_slug}_{date_slug}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with ts_c3:
        st.download_button(
            label="🌐 HTML",
            data=tear_sheet_html.encode("utf-8"),
            file_name=f"argus_advisory_pitchbook_{prof_slug}_{date_slug}.html",
            mime="text/html",
            use_container_width=True
        )
    with ts_c4:
        show_ts_preview = st.toggle("📑 Anteprima", value=False, key="toggle_ts_preview_p13")
    with ts_c5:
        if st.button("ℹ️ Guida IFRS/GIPS", key="btn_modal_methodology_p13", use_container_width=True):
            render_wealth_methodology_modal()

    if show_ts_preview:
        st.components.v1.html(tear_sheet_html, height=600, scrolling=True)

    from core.wealth.wealth_reporting_hub import render_wealth_reporting_and_exports_hub

    with st.expander("📑 Hub Esportazioni Istituzionali & Dossier Multi-Formato (9 Formati)", expanded=False):
        render_wealth_reporting_and_exports_hub(engine, portfolio_id=current_pid, prof_name=prof_title)

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # ── RIGA 1: ALLOCAZIONE GLOBALE DEL PATRIMONIO MULTI-DIMENSIONE ─────
    head_a1, head_a2, head_a3 = st.columns([0.85, 1.25, 1.25])
    with head_a1:
        section("📊 Allocazione Globale")
    with head_a2:
        alloc_dim = st.segmented_control(
            "Dimensione Analitica:",
            options=["🏷️ Macro", "💧 Liquidità", "🎯 Strategia"],
            default="🏷️ Macro",
            label_visibility="collapsed",
            key="alloc_dim_selector_seg"
        ) or "🏷️ Macro"
    with head_a3:
        chart_view = st.segmented_control(
            "Visualizzazione Grafico:",
            options=["🍩 Donut", "🥧 Sunburst", "🥞 Treemap"],
            default="🍩 Donut",
            label_visibility="collapsed",
            key="alloc_chart_view_mode_seg"
        ) or "🍩 Donut"

    # Costruzione atomica e granulare di tutti i singoli asset
    breakdown_items = []

    # 1. Liquidità & Cash / Depositi
    if is_snapshot_mode:
        snap_accs = details.get("accounts", [])
        for a in snap_accs:
            b = float(a.get("balance", 0.0))
            if b > 0:
                a_name = str(a.get("name", "Conto Bancario"))
                a_type = str(a.get("account_type", "checking")).lower()
                is_deposit = ("deposito" in a_name.lower() or "savings" in a_type)
                breakdown_items.append({
                    "name": a_name,
                    "macro": "Liquidità & Depositi",
                    "liquidity": "📅 T+30 (Differita / Vincolata)" if is_deposit else "⚡ T0 (Liquidità Immediata)",
                    "strategic": "🛡️ Fondo Sicurezza & Riserve",
                    "risk": "Basso",
                    "val": b,
                    "color": "#14b8a6" if is_deposit else "#10b981",
                    "icon": "🏦" if is_deposit else "💳"
                })
        if not snap_accs and liq_cash > 0:
            breakdown_items.append({
                "name": "Liquidità & Depositi Bancari",
                "macro": "Liquidità & Depositi",
                "liquidity": "⚡ T0 (Liquidità Immediata)",
                "strategic": "🛡️ Fondo Sicurezza & Riserve",
                "risk": "Basso",
                "val": liq_cash,
                "color": "#10b981",
                "icon": "💳"
            })
    else:
        if not df_accounts.empty:
            for _, a in df_accounts.iterrows():
                b = float(a.get("balance", 0.0))
                if b > 0:
                    a_name = str(a.get("name", "Conto Bancario"))
                    a_type = str(a.get("account_type", "checking")).lower()
                    is_deposit = ("deposito" in a_name.lower() or "savings" in a_type or "vincolato" in a_name.lower())
                    breakdown_items.append({
                        "name": a_name,
                        "macro": "Liquidità & Depositi",
                        "liquidity": "📅 T+30 (Differita / Vincolata)" if is_deposit else "⚡ T0 (Liquidità Immediata)",
                        "strategic": "🛡️ Fondo Sicurezza & Riserve",
                        "risk": "Basso",
                        "val": b,
                        "color": "#14b8a6" if is_deposit else "#10b981",
                        "icon": "🏦" if is_deposit else "💳"
                    })
        elif liq_cash > 0:
            breakdown_items.append({
                "name": "Liquidità & Depositi Bancari",
                "macro": "Liquidità & Depositi",
                "liquidity": "⚡ T0 (Liquidità Immediata)",
                "strategic": "🛡️ Fondo Sicurezza & Riserve",
                "risk": "Basso",
                "val": liq_cash,
                "color": "#10b981",
                "icon": "💳"
            })

    # 2. Investimenti Finanziari (Quotati, ETF, Bond, Crypto)
    if is_snapshot_mode:
        snap_risk = details.get("linked_risk_portfolios", [])
        for rk in snap_risk:
            v = float(rk.get("latest_value", 0.0))
            if v > 0:
                r_raw = str(rk.get("name", "Portafoglio"))
                r_low = r_raw.lower()
                if "crypto" in r_low or "bitcoin" in r_low or "btc" in r_low:
                    m_cls = "Criptovalute & Digital Assets"
                    l_cls = "⏱️ T+2 (Breve Termine)"
                    s_cls = "🚀 Capitale di Crescita"
                    r_lvl = "Alto"
                    c_col = "#8b5cf6"
                    c_ic = "🪙"
                elif "bond" in r_low or "obbligaz" in r_low or "btp" in r_low or "fixed" in r_low:
                    m_cls = "Obbligazioni & Fixed Income"
                    l_cls = "⏱️ T+2 (Breve Termine)"
                    s_cls = "⚖️ Protezione & Beni Rifugio"
                    r_lvl = "Basso/Medio"
                    c_col = "#0284c7"
                    c_ic = "🏛️"
                else:
                    m_cls = "Investimenti Finanziari (Azioni/ETF)"
                    l_cls = "⏱️ T+2 (Breve Termine)"
                    s_cls = "🚀 Capitale di Crescita"
                    r_lvl = "Medio/Alto"
                    c_col = "#6366f1"
                    c_ic = "📈"

                breakdown_items.append({
                    "name": r_raw,
                    "macro": m_cls,
                    "liquidity": l_cls,
                    "strategic": s_cls,
                    "risk": r_lvl,
                    "val": v,
                    "color": c_col,
                    "icon": c_ic
                })
        if not snap_risk and fin_inv > 0:
            breakdown_items.append({
                "name": "Investimenti Finanziari (Quotati)",
                "macro": "Investimenti Finanziari (Azioni/ETF)",
                "liquidity": "⏱️ T+2 (Breve Termine)",
                "strategic": "🚀 Capitale di Crescita",
                "risk": "Medio/Alto",
                "val": fin_inv,
                "color": "#6366f1",
                "icon": "📈"
            })
    else:
        _, df_linked_risk = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=current_pid)
        if not df_linked_risk.empty:
            for _, rk in df_linked_risk.iterrows():
                v = float(rk.get("latest_value", 0.0))
                if v > 0:
                    r_name = str(rk.get("name", "Portafoglio"))
                    r_low = r_name.lower()
                    if "crypto" in r_low or "bitcoin" in r_low or "btc" in r_low:
                        m_cls = "Criptovalute & Digital Assets"
                        l_cls = "⏱️ T+2 (Breve Termine)"
                        s_cls = "🚀 Capitale di Crescita"
                        r_lvl = "Alto"
                        c_col = "#8b5cf6"
                        c_ic = "🪙"
                    elif "bond" in r_low or "obbligaz" in r_low or "btp" in r_low or "fixed" in r_low:
                        m_cls = "Obbligazioni & Fixed Income"
                        l_cls = "⏱️ T+2 (Breve Termine)"
                        s_cls = "⚖️ Protezione & Beni Rifugio"
                        r_lvl = "Basso/Medio"
                        c_col = "#0284c7"
                        c_ic = "🏛️"
                    else:
                        m_cls = "Investimenti Finanziari (Azioni/ETF)"
                        l_cls = "⏱️ T+2 (Breve Termine)"
                        s_cls = "🚀 Capitale di Crescita"
                        r_lvl = "Medio/Alto"
                        c_col = "#6366f1"
                        c_ic = "📈"

                    breakdown_items.append({
                        "name": r_name,
                        "macro": m_cls,
                        "liquidity": l_cls,
                        "strategic": s_cls,
                        "risk": r_lvl,
                        "val": v,
                        "color": c_col,
                        "icon": c_ic
                    })
        elif fin_inv > 0:
            breakdown_items.append({
                "name": "Investimenti Finanziari (Quotati)",
                "macro": "Investimenti Finanziari (Azioni/ETF)",
                "liquidity": "⏱️ T+2 (Breve Termine)",
                "strategic": "🚀 Capitale di Crescita",
                "risk": "Medio/Alto",
                "val": fin_inv,
                "color": "#6366f1",
                "icon": "📈"
            })

    # 3. Immobili & Real Estate (Net Equity)
    if re_val > 0:
        breakdown_items.append({
            "name": "Immobili & Proprietà (Net Equity)",
            "macro": "Immobili & Real Estate",
            "liquidity": "🔒 Illiquido / Strutturale",
            "strategic": "🚀 Capitale di Crescita",
            "risk": "Medio",
            "val": re_val,
            "color": "#f59e0b",
            "icon": "🏠"
        })

    # 4. Asset Caveau & Metalli Preziosi & Orologi
    if is_snapshot_mode:
        snap_phys = details.get("physical_assets", [])
        for pa in snap_phys:
            v = float(pa.get("current_market_value", 0.0))
            if v > 0:
                p_name = str(pa.get("name", "Asset"))
                p_cat = str(pa.get("asset_category", "")).lower()
                p_low = p_name.lower()
                if "oro" in p_low or "gold" in p_low or "silver" in p_low or "metalli" in p_cat or "metal" in p_low:
                    m_cls = "Metalli Preziosi & Caveau"
                    l_cls = "📅 T+30 (Differita / Vincolata)"
                    s_cls = "⚖️ Protezione & Beni Rifugio"
                    r_lvl = "Medio (Hedge)"
                    c_col = "#eab308"
                    c_ic = "👑"
                elif "orolog" in p_low or "watch" in p_cat or "rolex" in p_low or "seiko" in p_low or "omega" in p_low or "patek" in p_low:
                    m_cls = "Orologi di Lusso & Collezioni"
                    l_cls = "📅 T+30 (Differita / Vincolata)"
                    s_cls = "⚖️ Protezione & Beni Rifugio"
                    r_lvl = "Medio/Alto"
                    c_col = "#d97706"
                    c_ic = "⌚"
                else:
                    m_cls = "Beni Fisici & Collezionismo"
                    l_cls = "🔒 Illiquido / Strutturale"
                    s_cls = "⚖️ Protezione & Beni Rifugio"
                    r_lvl = "Medio"
                    c_col = "#ca8a04"
                    c_ic = "🏺"

                breakdown_items.append({
                    "name": p_name,
                    "macro": m_cls,
                    "liquidity": l_cls,
                    "strategic": s_cls,
                    "risk": r_lvl,
                    "val": v,
                    "color": c_col,
                    "icon": c_ic
                })
        if not snap_phys and phys_assets > 0:
            breakdown_items.append({
                "name": "Asset Caveau & Metalli",
                "macro": "Metalli Preziosi & Caveau",
                "liquidity": "📅 T+30 (Differita / Vincolata)",
                "strategic": "⚖️ Protezione & Beni Rifugio",
                "risk": "Medio",
                "val": phys_assets,
                "color": "#eab308",
                "icon": "👑"
            })
    else:
        df_phys = get_physical_assets(engine, portfolio_id=current_pid)
        if not df_phys.empty:
            for _, pa in df_phys.iterrows():
                v = float(pa.get("current_market_value", 0.0))
                if v > 0:
                    p_name = str(pa.get("name", "Asset"))
                    p_cat = str(pa.get("asset_category", "")).lower()
                    p_low = p_name.lower()
                    if "oro" in p_low or "gold" in p_low or "silver" in p_low or "metalli" in p_cat or "metal" in p_low:
                        m_cls = "Metalli Preziosi & Caveau"
                        l_cls = "📅 T+30 (Differita / Vincolata)"
                        s_cls = "⚖️ Protezione & Beni Rifugio"
                        r_lvl = "Medio (Hedge)"
                        c_col = "#eab308"
                        c_ic = "👑"
                    elif "orolog" in p_low or "watch" in p_cat or "rolex" in p_low or "seiko" in p_low or "omega" in p_low or "patek" in p_low:
                        m_cls = "Orologi di Lusso & Collezioni"
                        l_cls = "📅 T+30 (Differita / Vincolata)"
                        s_cls = "⚖️ Protezione & Beni Rifugio"
                        r_lvl = "Medio/Alto"
                        c_col = "#d97706"
                        c_ic = "⌚"
                    else:
                        m_cls = "Beni Fisici & Collezionismo"
                        l_cls = "🔒 Illiquido / Strutturale"
                        s_cls = "⚖️ Protezione & Beni Rifugio"
                        r_lvl = "Medio"
                        c_col = "#ca8a04"
                        c_ic = "🏺"

                    breakdown_items.append({
                        "name": p_name,
                        "macro": m_cls,
                        "liquidity": l_cls,
                        "strategic": s_cls,
                        "risk": r_lvl,
                        "val": v,
                        "color": c_col,
                        "icon": c_ic
                    })
        elif phys_assets > 0:
            breakdown_items.append({
                "name": "Asset Caveau & Metalli",
                "macro": "Metalli Preziosi & Caveau",
                "liquidity": "📅 T+30 (Differita / Vincolata)",
                "strategic": "⚖️ Protezione & Beni Rifugio",
                "risk": "Medio",
                "val": phys_assets,
                "color": "#eab308",
                "icon": "👑"
            })

    # 5. Previdenza Integrativa & Fondi Pensione
    if is_snapshot_mode:
        snap_pens = details.get("pension_plans", [])
        for pp in snap_pens:
            v = float(pp.get("accumulated_value", 0.0))
            if v > 0:
                p_name = str(pp.get("fund_name", pp.get("name", "Fondo Pensione")))
                breakdown_items.append({
                    "name": p_name,
                    "macro": "Previdenza Integrativa",
                    "liquidity": "🔒 Illiquido / Strutturale",
                    "strategic": "🔮 Patrimonio Previdenziale",
                    "risk": "Medio",
                    "val": v,
                    "color": "#ec4899",
                    "icon": "🛡️"
                })
        if not snap_pens and pens_val > 0:
            breakdown_items.append({
                "name": "Previdenza Integrativa & PIP",
                "macro": "Previdenza Integrativa",
                "liquidity": "🔒 Illiquido / Strutturale",
                "strategic": "🔮 Patrimonio Previdenziale",
                "risk": "Medio",
                "val": pens_val,
                "color": "#ec4899",
                "icon": "🛡️"
            })
    else:
        df_pens = get_pension_plans(engine, portfolio_id=current_pid)
        if not df_pens.empty:
            for _, pp in df_pens.iterrows():
                v = float(pp.get("accumulated_value", 0.0))
                if v > 0:
                    p_name = str(pp.get("fund_name", pp.get("name", "Fondo Pensione")))
                    breakdown_items.append({
                        "name": p_name,
                        "macro": "Previdenza Integrativa",
                        "liquidity": "🔒 Illiquido / Strutturale",
                        "strategic": "🔮 Patrimonio Previdenziale",
                        "risk": "Medio",
                        "val": v,
                        "color": "#ec4899",
                        "icon": "🛡️"
                    })
        elif pens_val > 0:
            breakdown_items.append({
                "name": "Previdenza Integrativa & PIP",
                "macro": "Previdenza Integrativa",
                "liquidity": "🔒 Illiquido / Strutturale",
                "strategic": "🔮 Patrimonio Previdenziale",
                "risk": "Medio",
                "val": pens_val,
                "color": "#ec4899",
                "icon": "🛡️"
            })

    if breakdown_items and tot_nw > 0:
        # Raggruppamento dinamico in base alla dimensione selezionata
        dim_key_map = {
            "🏷️ Macro": "macro",
            "💧 Liquidità": "liquidity",
            "🎯 Strategia": "strategic",
            "🏷️ Macro-Classi": "macro",
            "💧 Profilo Liquidità": "liquidity",
            "🎯 Destinazione Strategica": "strategic"
        }
        active_dim_key = dim_key_map.get(alloc_dim, "macro")

        dim_title_map = {
            "🏷️ Macro": "Macro Asset Classes",
            "💧 Liquidità": "Profilo di Liquidità (IFRS 13)",
            "🎯 Strategia": "Destinazione Strategica"
        }
        dim_label_display = dim_title_map.get(alloc_dim, alloc_dim)

        # Palette colore coerente per dimensione
        dim_color_palette = {
            "Liquidità & Depositi": "#10b981",
            "Investimenti Finanziari (Azioni/ETF)": "#6366f1",
            "Obbligazioni & Fixed Income": "#0284c7",
            "Criptovalute & Digital Assets": "#8b5cf6",
            "Immobili & Real Estate": "#f59e0b",
            "Metalli Preziosi & Caveau": "#eab308",
            "Orologi di Lusso & Collezioni": "#d97706",
            "Beni Fisici & Collezionismo": "#ca8a04",
            "Previdenza Integrativa": "#ec4899",
            "⚡ T0 (Liquidità Immediata)": "#10b981",
            "⏱️ T+2 (Breve Termine)": "#6366f1",
            "📅 T+30 (Differita / Vincolata)": "#f59e0b",
            "🔒 Illiquido / Strutturale": "#ec4899",
            "🛡️ Fondo Sicurezza & Riserve": "#10b981",
            "🚀 Capitale di Crescita": "#6366f1",
            "⚖️ Protezione & Beni Rifugio": "#f59e0b",
            "🔮 Patrimonio Previdenziale": "#ec4899"
        }

        # Calcolo aggregati per gruppo
        group_totals = {}
        group_items = {}
        for it in breakdown_items:
            g = it[active_dim_key]
            group_totals[g] = group_totals.get(g, 0.0) + it["val"]
            if g not in group_items:
                group_items[g] = []
            group_items[g].append(it)

        col_chart, col_breakdown = st.columns([1.4, 1.6])

        with col_chart:
            if "Treemap" in chart_view:
                tm_labels = []
                tm_parents = []
                tm_values = []
                tm_colors = []
                for g_name, g_val in group_totals.items():
                    tm_labels.append(g_name)
                    tm_parents.append("")
                    tm_values.append(g_val)
                    tm_colors.append(dim_color_palette.get(g_name, "#6366f1"))
                    for sub in group_items[g_name]:
                        tm_labels.append(f"{sub['name']}")
                        tm_parents.append(g_name)
                        tm_values.append(sub["val"])
                        tm_colors.append(sub["color"])

                fig_alloc = go.Figure(go.Treemap(
                    labels=tm_labels,
                    parents=tm_parents,
                    values=tm_values,
                    branchvalues="total",
                    marker=dict(colors=tm_colors, line=dict(color="#0e1117", width=1.5)),
                    hovertemplate="<b>%{label}</b><br>Controvalore: <b>€%{value:,.2f}</b><br>Quota: <b>%{percentRoot:.1%}</b><extra></extra>"
                ))
                fig_alloc.update_layout(
                    margin=dict(t=10, l=10, r=10, b=10),
                    height=390,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit, sans-serif", color="#c9d1d9")
                )
            elif "Sunburst" in chart_view:
                sb_labels = []
                sb_parents = []
                sb_values = []
                sb_colors = []
                for g_name, g_val in group_totals.items():
                    sb_labels.append(g_name)
                    sb_parents.append("")
                    sb_values.append(g_val)
                    sb_colors.append(dim_color_palette.get(g_name, "#6366f1"))
                    for sub in group_items[g_name]:
                        sb_labels.append(f"{sub['name']}")
                        sb_parents.append(g_name)
                        sb_values.append(sub["val"])
                        sb_colors.append(sub["color"])

                fig_alloc = go.Figure(go.Sunburst(
                    labels=sb_labels,
                    parents=sb_parents,
                    values=sb_values,
                    branchvalues="total",
                    marker=dict(colors=sb_colors, line=dict(color="#0e1117", width=1.5)),
                    insidetextorientation="auto",
                    hovertemplate="<b>%{label}</b><br>Controvalore: <b>€%{value:,.2f}</b><br>Quota: <b>%{percentRoot:.1%}</b><extra></extra>"
                ))
                fig_alloc.update_layout(
                    margin=dict(t=10, l=10, r=10, b=10),
                    height=390,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit, sans-serif", color="#c9d1d9")
                )
            else: # Donut Istituzionale (Default)
                d_labels = list(group_totals.keys())
                d_vals = list(group_totals.values())
                d_cols = [dim_color_palette.get(k, "#6366f1") for k in d_labels]

                fig_alloc = go.Figure(go.Pie(
                    labels=d_labels,
                    values=d_vals,
                    hole=0.62,
                    marker=dict(colors=d_cols, line=dict(color="#0e1117", width=2)),
                    textinfo="percent",
                    textposition="outside",
                    textfont=dict(size=11, color="#94a3b8"),
                    hovertemplate="<b>%{label}</b><br>Controvalore: <b>€ %{value:,.2f}</b><br>Quota: <b>%{percent}</b><extra></extra>"
                ))

                fig_alloc.update_layout(
                    showlegend=False,
                    margin=dict(t=20, l=20, r=20, b=20),
                    height=390,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit, sans-serif", color="#c9d1d9"),
                    annotations=[
                        dict(
                            text=f"<b style='font-size:22px; color:#ffffff;'>€ {tot_nw:,.0f}</b><br><span style='font-size:10px; color:#94a3b8; letter-spacing:0.8px; font-weight:700;'>PATRIMONIO NETTO</span>",
                            x=0.5, y=0.5,
                            font_size=14,
                            showarrow=False
                        )
                    ]
                )
            st.plotly_chart(fig_alloc, use_container_width=True)

        with col_breakdown:
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13px; font-weight:700; color:#ffffff; text-transform:uppercase; letter-spacing:0.3px;">Ripartizione ({dim_label_display})</span>
                <span style="background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); color:#818cf8; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px;">{len(breakdown_items)} Voci Attive</span>
            </div>
            """, unsafe_allow_html=True)

            sorted_groups = sorted(group_totals.items(), key=lambda x: x[1], reverse=True)
            for g_name, g_val in sorted_groups:
                g_share = (g_val / tot_nw) * 100.0
                g_col = dim_color_palette.get(g_name, "#6366f1")
                subs = group_items[g_name]

                st.markdown(f"""
                <div style="background:rgba(22, 27, 34, 0.85); border:1px solid rgba(255,255,255,0.06); border-left:4px solid {g_col}; border-radius:8px; padding:8px 12px; margin-bottom:6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:13px; font-weight:700; color:#ffffff;">{g_name}</span>
                        <span style="font-size:13px; font-weight:800; color:#ffffff;">€ {g_val:,.2f} <span style="font-size:11px; color:{g_col}; font-weight:700;">({g_share:.1f}%)</span></span>
                    </div>
                    <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:4px;">
                        {' '.join([f"<span style='font-size:10px; color:#cbd5e1; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:1px 6px; border-radius:4px;'>{s['icon']} {s['name']}: €{s['val']:,.0f}</span>" for s in subs])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("📋 Tabella Istituzionale di Sintesi Asset Allocation & Pesi", expanded=False):
            df_alloc_table = pd.DataFrame([
                {
                    "Attivo / Voce": f"{it['icon']} {it['name']}",
                    "Macro Asset Class": it["macro"],
                    "Profilo Liquidità (IFRS 13)": it["liquidity"],
                    "Destinazione Strategica": it["strategic"],
                    "Livello Rischio": it["risk"],
                    "Controvalore (€)": it["val"],
                    "Peso sul Net Worth (%)": (it["val"] / tot_nw) * 100.0
                }
                for it in sorted(breakdown_items, key=lambda x: x["val"], reverse=True)
            ])
            alloc_cfg = {
                "Macro Asset Class": st.column_config.TextColumn("Macro Asset Class", width="medium"),
                "Profilo Liquidità (IFRS 13)": st.column_config.TextColumn("Profilo Liquidità", width="medium"),
                "Destinazione Strategica": st.column_config.TextColumn("Destinazione Strategica", width="medium"),
                "Livello Rischio": st.column_config.TextColumn("Livello Rischio", width="small"),
                "Controvalore (€)": st.column_config.NumberColumn("Controvalore (€)", format="€ %,.2f"),
                "Peso sul Net Worth (%)": st.column_config.ProgressColumn("Peso sul Net Worth (%)", format="%.1f%%", min_value=0.0, max_value=100.0)
            }
            render_table_with_export(
                df=df_alloc_table,
                table_title="Composizione Patrimonio Complessivo",
                file_prefix="asset_allocation_net_worth",
                key_suffix="nw_alloc_table",
                column_config=alloc_cfg,
                hide_index=True
            )
    else:
        st.info("Nessun dato di allocazione disponibile. Aggiungi conti o asset fisici.")

    st.divider()

    # ── RIGA 2: WEALTH HEALTH SCORE & ROBUSTEZZA FINANZIARIA ─────
    section("🛡️ Wealth Health Score & Indici di Robustezza Finanziaria")

    col_gauge, col_score_cards = st.columns([1.5, 2.5])

    with col_gauge:
        score_val = round(health_sc, 1)
        score_color = "#10b981" if score_val >= 75 else ("#f59e0b" if score_val >= 50 else "#ef4444")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score_val,
            number={'suffix': "/100", 'font': {'size': 38, 'color': '#ffffff', 'family': 'Outfit, sans-serif'}},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Indice di Robustezza Finanziaria", 'font': {'size': 13, 'color': '#8b949e'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': 'rgba(255,255,255,0.2)', 'tickfont': {'color': '#8b949e', 'size': 10}},
                'bar': {'color': score_color, 'thickness': 0.28},
                'bgcolor': "rgba(22, 27, 34, 0.6)",
                'borderwidth': 1,
                'bordercolor': "rgba(255, 255, 255, 0.08)",
                'steps': [
                    {'range': [0, 50], 'color': "rgba(239, 68, 68, 0.12)"},
                    {'range': [50, 75], 'color': "rgba(245, 158, 11, 0.12)"},
                    {'range': [75, 100], 'color': "rgba(16, 185, 129, 0.12)"}
                ],
                'threshold': {
                    'line': {'color': "#ffffff", 'width': 3},
                    'thickness': 0.8,
                    'value': score_val
                }
            }
        ))
        fig_gauge.update_layout(
            height=260,
            margin=dict(t=25, b=10, l=15, r=15),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_score_cards:
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #10b981; border-radius: 10px; padding: 12px 16px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; font-weight:700; letter-spacing:0.3px;">Tasso di Risparmio (Savings Rate)</div>
                    <div style="font-size:17px; font-weight:800; color:#ffffff; margin-top:2px;">{sav_rate:.1f}%</div>
                </div>
                <div style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); color:#34d399; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">{'🟢 Ottimo (≥20%)' if sav_rate >= 20 else ('🟡 In crescita (≥5%)' if sav_rate >= 5 else '⚪ Base (<5%)')}</div>
            </div>
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #6366f1; border-radius: 10px; padding: 12px 16px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; font-weight:700; letter-spacing:0.3px;">Autonomia Liquidità (Runway Emergenze)</div>
                    <div style="font-size:17px; font-weight:800; color:#ffffff; margin-top:2px;">{runway_m:.1f} Mesi</div>
                </div>
                <div style="background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); color:#818cf8; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">{'🛡️ Copertura Solida (≥6m)' if runway_m >= 6 else ('⚖️ Fondo Adeguato (≥3m)' if runway_m >= 3 else '🔴 Riserva Vulnerabile (<3m)')}</div>
            </div>
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #f59e0b; border-radius: 10px; padding: 12px 16px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:11px; color:#8b949e; text-transform:uppercase; font-weight:700; letter-spacing:0.3px;">Passività, Prestiti & Debiti Residui</div>
                    <div style="font-size:17px; font-weight:800; color:#ffffff; margin-top:2px;">{fmt_eur(liab_val)}</div>
                </div>
                <div style="background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.3); color:#fbbf24; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">{'✅ Zero Debiti (100% Solvibile)' if liab_val == 0 else '⚠️ Esposizione Debitoria Attiva'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 2: BILANCIO PERSONALE & STATO PATRIMONIALE ISTITUZIONALE
# ══════════════════════════════════════════════════════════════
with main_tab_sheet:
    # ── SONDAGGIO ESERCIZI FISCALI DISPONIBILI ────────────────
    df_cf_probe = get_cashflow_records(engine, portfolio_id=current_pid)
    curr_yr = datetime.now().year
    if not df_cf_probe.empty:
        df_cf_probe["tx_date"] = pd.to_datetime(df_cf_probe["tx_date"], errors="coerce")
        avail_years = sorted([int(y) for y in df_cf_probe["tx_date"].dt.year.dropna().unique()], reverse=True)
    else:
        avail_years = [curr_yr]
    if curr_yr not in avail_years:
        avail_years = sorted(list(set(avail_years + [curr_yr])), reverse=True)

    # ── BARRA DI CONTROLLO ESERCIZIO MASTER ────────────────────
    col_yr1, col_yr2, col_yr3 = st.columns([1.6, 2.2, 1.2])
    with col_yr1:
        selected_pbs_year = st.selectbox(
            "📅 Esercizio Fiscale / Anno di Bilancio:",
            options=avail_years,
            index=0,
            key="master_pbs_year_selector"
        )
    with col_yr2:
        is_past = selected_pbs_year < curr_yr
        badge_status = (
            f"🔒 Esercizio Chiuso al 31/12/{selected_pbs_year}"
            if is_past
            else f"🟢 Esercizio in Corso (Aggiornato al {datetime.now().strftime('%d/%m/%Y')})"
        )
        st.markdown(f"""
        <div style="padding-top:28px;">
            <span style="background:{'rgba(59,130,246,0.15)' if is_past else 'rgba(16,185,129,0.15)'}; border:1px solid {'rgba(59,130,246,0.4)' if is_past else 'rgba(16,185,129,0.4)'}; padding:6px 14px; border-radius:18px; font-size:12px; font-weight:700; color:{'#60a5fa' if is_past else '#34d399'};">
                {badge_status}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col_yr3:
        if is_past:
            st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
            if st.button("📸 Salva Chiusura", key="btn_save_year_close_snap", use_container_width=True, help=f"Salva e congela formalmente lo snapshot di bilancio al 31/12/{selected_pbs_year} nel database"):
                from datetime import date as d_date

                from core.wealth.wealth_snapshot import save_wealth_snapshot_to_db
                snap_id = save_wealth_snapshot_to_db(
                    engine=engine,
                    portfolio_id=current_pid,
                    snapshot_name=f"Chiusura Esercizio {selected_pbs_year}",
                    snapshot_date_val=d_date(selected_pbs_year, 12, 31),
                    notes=f"Snapshot ufficiale di chiusura bilancio personale esercizio {selected_pbs_year}"
                )
                st.toast(f"✅ Snapshot di chiusura {selected_pbs_year} archiviato con successo!", icon="🏛️")
                st.cache_data.clear()
                st.rerun()

    # ── CARICAMENTO DATI BILANCIO PERSONALE PER L'ANNO SELEZIONATO ──
    pbs_data = _load_cached_personal_balance_sheet(engine, pid=current_pid, yr=selected_pbs_year)
    sp_data = pbs_data["stato_patrimoniale"]
    ind_data = pbs_data["indici_bilancio"]

    tot_att = sp_data["attivo"]["totale_attivo"]
    tot_pas = sp_data["passivo"]["totale_passivo"]
    tot_pn = sp_data["patrimonio_netto"]["totale_patrimonio_netto"]
    tot_pareggio = sp_data["pareggio"]["totale_pareggio"]
    is_quadrato = sp_data["pareggio"]["is_quadrato"]

    # ── HERO HEADER ISTITUZIONALE ──────────────────────────────
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(22,27,34,0.98) 100%); border: 1px solid rgba(16,185,129,0.35); border-radius: 14px; padding: 18px 24px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:14px;">
                <div style="width:44px; height:44px; border-radius:12px; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.35); display:flex; align-items:center; justify-content:center; font-size:22px;">
                    📋
                </div>
                <div>
                    <div style="font-size:17px; font-weight:800; color:#f8fafc; letter-spacing:0.3px;">Bilancio Personale Istituzionale &bull; {pbs_data.get('period_title', 'Esercizio ' + str(selected_pbs_year))}</div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:2px;">Prospetto contabile a sezioni contrapposte, Conto Economico di gestione e indici di solidità conforme agli standard CFP Board &amp; Private Banking</div>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); padding:6px 14px; border-radius:20px; font-size:12px; font-weight:750; color:#34d399;">
                    🛡️ {ind_data.get('overall_rating', 'AAA')}
                </div>
                <div style="font-size:11.5px; color:#64748b; font-family:'JetBrains Mono', monospace;">
                    Rif: {pbs_data.get('as_of_date')}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── EXECUTIVE PERSONAL BALANCE SHEET TOOLBAR ──────────────────
    pbs_pdf = _get_cached_balance_sheet_pdf(engine, current_pid, selected_pbs_year)
    pbs_tearsheet_pdf = _get_cached_balance_sheet_tearsheet_pdf(engine, current_pid, selected_pbs_year)
    pbs_html = _get_cached_balance_sheet_html(engine, current_pid, selected_pbs_year)
    pbs_date_slug = f"{selected_pbs_year}" if is_past else datetime.now().strftime('%Y%m%d')
    pbs_prof_slug = str(prof_map.get(current_pid, 'portfolio')).lower().replace(' ', '_')

    st.markdown(f"""
    <div style="background:rgba(22,27,34,0.75); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #10b981; border-radius:10px; padding:12px 16px; margin-bottom:10px;">
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:34px; height:34px; border-radius:8px; background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0;">
                📋
            </div>
            <div>
                <div style="font-size:13.5px; font-weight:750; color:#ffffff; letter-spacing:0.3px;">Executive Balance Sheet Dossier &amp; Financial Statements ({selected_pbs_year})</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:1px;">Prospetto contabile certificato a sezioni contrapposte, Conto Economico di gestione, pareggio di bilancio e indici di solidità patrimoniale per l'anno {selected_pbs_year}.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    pb_c1, pb_c2, pb_c3, pb_c4, pb_c5 = st.columns([1.3, 1.1, 0.8, 0.8, 1.1])
    with pb_c1:
        st.download_button(
            label=f"📥 Scarica Bilancio PDF ({selected_pbs_year})",
            data=pbs_pdf,
            file_name=f"argus_bilancio_personale_{pbs_prof_slug}_{selected_pbs_year}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key="dl_pbs_pdf_btn"
        )
    with pb_c2:
        st.download_button(
            label=f"📑 Tear-Sheet Contabile ({selected_pbs_year})",
            data=pbs_tearsheet_pdf,
            file_name=f"argus_tearsheet_contabile_{pbs_prof_slug}_{selected_pbs_year}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="dl_pbs_ts_pdf_btn"
        )
    with pb_c3:
        st.download_button(
            label="🌐 HTML",
            data=pbs_html.encode("utf-8"),
            file_name=f"argus_bilancio_personale_{pbs_prof_slug}_{selected_pbs_year}.html",
            mime="text/html",
            use_container_width=True,
            key="dl_pbs_html_btn"
        )
    with pb_c4:
        show_pbs_preview = st.toggle("📑 Anteprima", value=False, key="toggle_pbs_preview_p13")
    with pb_c5:
        if st.button("ℹ️ Guida IFRS/CFP", key="btn_modal_pbs_methodology_p13", use_container_width=True):
            render_balance_sheet_methodology_modal()

    if show_pbs_preview:
        st.components.v1.html(pbs_html, height=620, scrolling=True)

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # ── SUB-TABS DEL BILANCIO PERSONALE ────────────────────────
    sub_sp, sub_ce, sub_ind, sub_conti, sub_multi, sub_stress = st.tabs([
        "🏛️ Stato Patrimoniale a Sezioni Contrapposte",
        "📈 Conto Economico di Gestione",
        "🎯 Indici di Bilancio & Benchmark",
        "🏦 Dettaglio Conti & Portafogli Risk",
        "📊 Bilancio Comparativo Pluriennale",
        "🌪️ Stress Test sul Patrimonio Netto"
    ])


    # ──────────────────────────────────────────────────────────
    # SUB-TAB 1: STATO PATRIMONIALE A SEZIONI CONTRAPPOSTE
    # ──────────────────────────────────────────────────────────
    with sub_sp:
        # Top KPI Summary Bar
        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        with kpi_c1:
            metric_card("Totale Attivo (Assets)", fmt_eur(tot_att), delta="Impieghi di ricchezza", delta_color="normal")
        with kpi_c2:
            metric_card("Totale Passività (Debiti)", fmt_eur(tot_pas), delta="Fonti di terzi", delta_color="inverse" if tot_pas > 0 else "normal")
        with kpi_c3:
            metric_card("Patrimonio Netto", fmt_eur(tot_pn), delta="Fonti proprie (Capitale netto)", delta_color="normal")
        with kpi_c4:
            quad_label = "✅ Perfetto (Δ = €0,00)" if is_quadrato else "⚠️ Sbilancio"
            metric_card("Pareggio di Bilancio", fmt_eur(tot_pareggio), delta=quad_label, delta_color="normal")

        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)

        # Sezioni Contrapposte
        col_attivo, col_passivo = st.columns(2)

        # ── COLONNA SINISTRA: ATTIVO ───────────────────────────
        with col_attivo:
            st.markdown("""
            <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:12px 16px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:800; color:#34d399; font-size:14px; letter-spacing:0.5px;">🏛️ ATTIVO (IMPIEGHI DI RICCHEZZA)</span>
                <span style="font-weight:700; color:#94a3b8; font-size:12px;">INCIDENZA</span>
            </div>
            """, unsafe_allow_html=True)

            for sez in sp_data["attivo"]["sezioni"]:
                with st.container():
                    st.markdown(f"""
                    <div style="background:rgba(22,27,34,0.6); border:1px solid rgba(255,255,255,0.07); border-radius:8px; padding:10px 14px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <div>
                                <span style="font-weight:750; color:#f1f5f9; font-size:13px;">{sez['codice']}. {sez['titolo']}</span>
                                <div style="font-size:10.5px; color:#64748b;">{sez['descrizione']}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:800; color:#f8fafc; font-size:13.5px; font-family:'JetBrains Mono', monospace;">{fmt_eur(sez['totale'])}</div>
                                <div style="font-size:10.5px; color:#10b981; font-weight:700;">{sez['incidenza_pct']:.1f}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if sez["voci"]:
                        voci_rows = []
                        for v in sez["voci"]:
                            voci_rows.append({
                                "Voce Contabile": v["nome"],
                                "Tipologia / Dettaglio": f"{v['categoria']} • {v['dettaglio']}",
                                "Valore (€)": fmt_eur(v["valore"]),
                                "Incidenza": f"{(v['valore'] / max(1.0, tot_att) * 100):.1f}%"
                            })
                        st.dataframe(pd.DataFrame(voci_rows), use_container_width=True, hide_index=True)

            # Footer Totale Attivo
            st.markdown(f"""
            <div style="background:linear-gradient(90deg, rgba(16,185,129,0.18) 0%, rgba(16,185,129,0.08) 100%); border:1px solid rgba(16,185,129,0.45); border-radius:10px; padding:14px 18px; margin-top:16px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:850; color:#f8fafc; font-size:14.5px; letter-spacing:0.5px;">TOTALE ATTIVO (ASSETS)</span>
                <span style="font-weight:900; color:#10b981; font-size:19px; font-family:'JetBrains Mono', monospace;">{fmt_eur(tot_att)}</span>
            </div>
            """, unsafe_allow_html=True)

        # ── COLONNA DESTRA: PASSIVO & PATRIMONIO NETTO ────────
        with col_passivo:
            st.markdown("""
            <div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.3); border-radius:10px; padding:12px 16px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:800; color:#60a5fa; font-size:14px; letter-spacing:0.5px;">⚖️ PASSIVO &amp; PATRIMONIO NETTO (FONTI)</span>
                <span style="font-weight:700; color:#94a3b8; font-size:12px;">INCIDENZA</span>
            </div>
            """, unsafe_allow_html=True)

            # A. Sezioni Passivo (Debiti)
            st.markdown("<div style='font-size:12px; font-weight:750; color:#94a3b8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;'>A. Passività &amp; Debiti Personali (Fonti di Terzi)</div>", unsafe_allow_html=True)
            has_liab = False
            for sez in sp_data["passivo"]["sezioni"]:
                if sez["totale"] > 0 or sez["voci"]:
                    has_liab = True
                    st.markdown(f"""
                    <div style="background:rgba(22,27,34,0.6); border:1px solid rgba(255,255,255,0.07); border-radius:8px; padding:10px 14px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:750; color:#f1f5f9; font-size:13px;">{sez['codice']}. {sez['titolo']}</span>
                                <div style="font-size:10.5px; color:#64748b;">{sez['descrizione']}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-weight:800; color:#ef4444; font-size:13.5px; font-family:'JetBrains Mono', monospace;">{fmt_eur(sez['totale'])}</div>
                                <div style="font-size:10.5px; color:#94a3b8;">{sez['incidenza_pct']:.1f}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if sez["voci"]:
                        voci_p_rows = []
                        for v in sez["voci"]:
                            voci_p_rows.append({
                                "Debito": v["nome"],
                                "Tipologia": f"{v['categoria']} • {v['dettaglio']}",
                                "Debito Residuo (€)": fmt_eur(v["valore"]),
                                "Incidenza": f"{(v['valore'] / max(1.0, tot_att) * 100):.1f}%"
                            })
                        st.dataframe(pd.DataFrame(voci_p_rows), use_container_width=True, hide_index=True)

            if not has_liab:
                st.markdown("""
                <div style="background:rgba(16,185,129,0.06); border:1px dashed rgba(16,185,129,0.3); border-radius:8px; padding:12px 14px; margin-bottom:12px; color:#34d399; font-size:12px;">
                    🛡️ <b>Assenza Totale di Debiti:</b> Nessun mutuo, prestito personale, scoperto o debito da carte di credito registrato a carico del patrimonio.
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background:rgba(22,27,34,0.4); border-radius:6px; padding:8px 12px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:12px; font-weight:700; color:#94a3b8;">SUBTOTALE PASSIVITÀ TOTALI</span>
                <span style="font-size:13px; font-weight:800; color:{'#ef4444' if tot_pas > 0 else '#94a3b8'}; font-family:'JetBrains Mono', monospace;">{fmt_eur(tot_pas)}</span>
            </div>
            """, unsafe_allow_html=True)

            # B. Patrimonio Netto
            st.markdown("<div style='font-size:12px; font-weight:750; color:#94a3b8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;'>B. Patrimonio Netto Personale (Fonti Proprie)</div>", unsafe_allow_html=True)
            
            pn_comp = sp_data["patrimonio_netto"]["composizione"]
            comp_rows = []
            for item in pn_comp:
                comp_rows.append({
                    "Voce di Patrimonio Netto": item["voce"],
                    "Dettaglio / Origine": item["descrizione"],
                    "Valore (€)": fmt_eur(item["valore"]),
                    "Quota PN": f"{item['incidenza_pct']:.1f}%"
                })
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div style="background:rgba(30,41,59,0.6); border:1px solid rgba(59,130,246,0.3); border-radius:8px; padding:10px 14px; margin-top:8px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:12.5px; font-weight:750; color:#93c5fd;">SUBTOTALE PATRIMONIO NETTO</span>
                <span style="font-size:15px; font-weight:850; color:#60a5fa; font-family:'JetBrains Mono', monospace;">{fmt_eur(tot_pn)}</span>
            </div>
            """, unsafe_allow_html=True)

            # Footer Totale a Pareggio
            st.markdown(f"""
            <div style="background:linear-gradient(90deg, rgba(59,130,246,0.18) 0%, rgba(59,130,246,0.08) 100%); border:1px solid rgba(59,130,246,0.45); border-radius:10px; padding:14px 18px; margin-top:16px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:850; color:#f8fafc; font-size:14.5px; letter-spacing:0.5px;">TOTALE PAREGGIO (PASSIVO + NET WORTH)</span>
                <span style="font-weight:900; color:#38bdf8; font-size:19px; font-family:'JetBrains Mono', monospace;">{fmt_eur(tot_pareggio)}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # Sezione Riconciliazione & Quadratura Contabile
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:12px 18px; display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:18px;">{'✅' if is_quadrato else '⚠️'}</span>
                <span style="font-weight:750; color:#34d399; font-size:13px;">EQUAZIONE CONTABILE FONDAMENTALE: ATTIVO = PASSIVO + PATRIMONIO NETTO</span>
            </div>
            <div style="font-size:12px; font-weight:700; color:#e2e8f0; font-family:'JetBrains Mono', monospace;">
                {fmt_eur(tot_att)} = {fmt_eur(tot_pas)} + {fmt_eur(tot_pn)} &nbsp;(Discrepanza: €0,00)
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    # SUB-TAB 2: CONTO ECONOMICO DI GESTIONE
    # ──────────────────────────────────────────────────────────
    with sub_ce:
        c_ce_head1, c_ce_head2 = st.columns([3.2, 1.3])
        with c_ce_head1:
            st.markdown("##### 📈 Conto Economico Personale (Rendiconto di Gestione)")
            st.caption("Prospetto economico di entrate correnti vs costi di vita, surplus di risparmio e destinazione agli investimenti.")
        with c_ce_head2:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:8px 14px; text-align:right; margin-top:4px;">
                <span style="font-size:11px; color:#94a3b8;">Esercizio Attivo:</span>
                <span style="font-weight:800; color:#34d399; font-size:13.5px; margin-left:6px;">{selected_pbs_year}</span>
            </div>
            """, unsafe_allow_html=True)

        # Conto Economico per l'anno selezionato a monte
        ce_year_data = pbs_data["conto_economico"]


        ce_inflow = ce_year_data["totale_entrate"]
        ce_outflow = ce_year_data["totale_uscite"]
        ce_savings = ce_year_data["risparmio_netto"]
        ce_sr = ce_year_data["savings_rate_pct"]
        ce_inv = ce_year_data["allocazione_capitale"]["totale_investimenti"]
        ce_liq_var = ce_year_data["allocazione_capitale"]["variazione_liquidita"]

        # KPI Cards Conto Economico
        cek1, cek2, cek3, cek4 = st.columns(4)
        with cek1:
            metric_card(f"Totale Entrate {selected_pbs_year}", fmt_eur(ce_inflow), delta="Inflows ordinari & attivi", delta_color="normal")
        with cek2:
            metric_card(f"Costi di Gestione {selected_pbs_year}", fmt_eur(ce_outflow), delta="Spese di vita (Consumi)", delta_color="inverse")
        with cek3:
            metric_card("Risparmio Netto Annuo", fmt_eur(ce_savings), delta="Surplus d'esercizio", delta_color="normal" if ce_savings >= 0 else "inverse")
        with cek4:
            metric_card("Personal Savings Rate", f"{ce_sr:.1f}%", delta="Target ≥ 20%", delta_color="normal" if ce_sr >= 20 else "off")

        st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)

        # Prospetto Scalare Entrate vs Spese
        col_ce_in, col_ce_out = st.columns(2)
        with col_ce_in:
            st.markdown("""
            <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:10px 16px; margin-bottom:12px;">
                <span style="font-weight:800; color:#34d399; font-size:13.5px;">VALORE DELLA PRODUZIONE PERSONALE (ENTRATE)</span>
            </div>
            """, unsafe_allow_html=True)

            if ce_year_data["entrate_sezioni"]:
                in_rows = []
                for item in ce_year_data["entrate_sezioni"]:
                    in_rows.append({
                        "Voce di Entrata": item["sezione"],
                        "Tipologia": item["categoria"],
                        "Importo (€)": fmt_eur(item["valore"]),
                        "Incidenza": f"{(item['valore'] / max(1.0, ce_inflow) * 100):.1f}%"
                    })
                st.dataframe(pd.DataFrame(in_rows), use_container_width=True, hide_index=True)
            else:
                st.info(f"Nessuna entrata registrata per l'anno {selected_pbs_year}.")

            st.markdown(f"""
            <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(16,185,129,0.4); border-radius:8px; padding:12px 16px; margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:800; color:#f8fafc; font-size:13px;">TOTALE ENTRATE PERSONALI</span>
                <span style="font-weight:850; color:#10b981; font-size:16px; font-family:'JetBrains Mono', monospace;">{fmt_eur(ce_inflow)}</span>
            </div>
            """, unsafe_allow_html=True)

        with col_ce_out:
            st.markdown("""
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:10px 16px; margin-bottom:12px;">
                <span style="font-weight:800; color:#f87171; font-size:13.5px;">COSTI DI GESTIONE &amp; CONSUMI (USCITE)</span>
            </div>
            """, unsafe_allow_html=True)

            if ce_year_data["uscite_sezioni"]:
                out_rows = []
                for item in ce_year_data["uscite_sezioni"]:
                    out_rows.append({
                        "Categoria di Spesa": item["sezione"],
                        "Movimenti": item.get("num_movimenti", 1),
                        "Importo (€)": fmt_eur(item["valore"]),
                        "Incidenza": f"{(item['valore'] / max(1.0, ce_outflow) * 100):.1f}%"
                    })
                st.dataframe(pd.DataFrame(out_rows), use_container_width=True, hide_index=True)
            else:
                st.info(f"Nessuna uscita registrata per l'anno {selected_pbs_year}.")

            st.markdown(f"""
            <div style="background:rgba(22,27,34,0.7); border:1px solid rgba(239,68,68,0.4); border-radius:8px; padding:12px 16px; margin-top:10px; display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:800; color:#f8fafc; font-size:13px;">TOTALE SPESE DI VITA (CONSUMI)</span>
                <span style="font-weight:850; color:#f87171; font-size:16px; font-family:'JetBrains Mono', monospace;">{fmt_eur(ce_outflow)}</span>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Waterfall Chart: Flusso Economico e Allocazione del Capitale
        st.markdown(f"##### 🌊 Waterfall di Gestione Economica & Allocazione del Capitale ({selected_pbs_year})")
        st.caption("Dalle entrate lorde ai consumi, fino alla quota convertita in investimenti patrimoniali o riserva liquida.")

        wf_measures = ["relative", "relative", "total", "relative", "total"]
        wf_x = ["Entrate Lorde", "Consumi di Vita", "Risparmio Netto", "Flussi Investiti", "Accantonamento Cassa"]
        wf_y = [ce_inflow, -ce_outflow, ce_savings, -ce_inv, ce_liq_var]
        wf_text = [fmt_eur(ce_inflow), fmt_eur(-ce_outflow), fmt_eur(ce_savings), fmt_eur(-ce_inv), fmt_eur(ce_liq_var)]

        fig_wf = go.Figure(go.Waterfall(
            name="Flusso Economico",
            orientation="v",
            measure=wf_measures,
            x=wf_x,
            textposition="outside",
            text=wf_text,
            y=wf_y,
            connector={"line": {"color": "rgba(255,255,255,0.2)"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#38bdf8"}}
        ))
        fig_wf.update_layout(height=340, margin=dict(l=30, r=30, t=30, b=30))
        apply_chart_theme(fig_wf, portal_mode="wealth")
        st.plotly_chart(fig_wf, use_container_width=True)

        # Box Allocazione del Risparmio
        if ce_year_data["allocazione_capitale"]["voci_investimenti"]:
            st.markdown("##### 🚀 Destinazione del Surplus: Investimenti Eseguiti nel Periodo")
            inv_alloc_cols = st.columns(len(ce_year_data["allocazione_capitale"]["voci_investimenti"]) + 1)
            for i, inv_item in enumerate(ce_year_data["allocazione_capitale"]["voci_investimenti"]):
                with inv_alloc_cols[i]:
                    metric_card(inv_item["nome"], fmt_eur(inv_item["valore"]), delta=f"{(inv_item['valore']/max(1.0, ce_inv)*100):.1f}% del capitale investito", delta_color="normal")
            with inv_alloc_cols[-1]:
                metric_card("💧 Variazione Cassa", fmt_eur(ce_liq_var), delta="Accantonamento cassa", delta_color="normal" if ce_liq_var >= 0 else "off")

    # ──────────────────────────────────────────────────────────
    # SUB-TAB 3: INDICI DI BILANCIO & BENCHMARK PRIVATE BANKING
    # ──────────────────────────────────────────────────────────
    with sub_ind:
        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.8); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:18px 22px; margin-bottom:18px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <div style="font-size:16px; font-weight:800; color:#f8fafc;">🏛️ Rating di Solidità del Bilancio Personale: <span style="color:#34d399;">{ind_data.get('overall_rating')}</span></div>
                    <div style="font-size:12px; color:#94a3b8; margin-top:4px;">{ind_data.get('overall_description')}</div>
                </div>
                <div style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.4); padding:6px 14px; border-radius:20px; font-size:12px; font-weight:800; color:#34d399;">
                    KPI Ottimali: {ind_data.get('optimal_kpi_count')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 6 KPI Cards Ratios
        r_r1_c1, r_r1_c2, r_r1_c3 = st.columns(3)
        with r_r1_c1:
            sr_k = ind_data["solvency_ratio"]
            metric_card(f"🛡️ {sr_k['label']}", sr_k["formattato"], delta=f"Target: {sr_k['target']}", delta_color="normal" if sr_k["status"] == "OPTIMAL" else ("off" if sr_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{sr_k['descrizione']}_")
        with r_r1_c2:
            da_k = ind_data["debt_to_assets"]
            metric_card(f"📉 {da_k['label']}", da_k["formattato"], delta=f"Target: {da_k['target']}", delta_color="normal" if da_k["status"] == "OPTIMAL" else ("off" if da_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{da_k['descrizione']}_")
        with r_r1_c3:
            rw_k = ind_data["emergency_runway"]
            metric_card(f"💧 {rw_k['label']}", rw_k["formattato"], delta=f"Target: {rw_k['target']}", delta_color="normal" if rw_k["status"] == "OPTIMAL" else ("off" if rw_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{rw_k['descrizione']}_")

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        r_r2_c1, r_r2_c2, r_r2_c3 = st.columns(3)
        with r_r2_c1:
            sav_k = ind_data["savings_rate"]
            metric_card(f"💰 {sav_k['label']}", sav_k["formattato"], delta=f"Target: {sav_k['target']}", delta_color="normal" if sav_k["status"] == "OPTIMAL" else ("off" if sav_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{sav_k['descrizione']}_")
        with r_r2_c2:
            ds_k = ind_data["dsti"]
            metric_card(f"💳 {ds_k['label']}", ds_k["formattato"], delta=f"Target: {ds_k['target']}", delta_color="normal" if ds_k["status"] == "OPTIMAL" else ("off" if ds_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{ds_k['descrizione']}_")
        with r_r2_c3:
            inv_k = ind_data["invested_assets_ratio"]
            metric_card(f"🚀 {inv_k['label']}", inv_k["formattato"], delta=f"Target: {inv_k['target']}", delta_color="normal" if inv_k["status"] == "OPTIMAL" else ("off" if inv_k["status"] == "ACCEPTABLE" else "inverse"))
            st.caption(f"_{inv_k['descrizione']}_")

        st.divider()

        # Radar Chart di Solidità Finanziaria
        st.markdown("##### 🕸️ Radar di Robustezza Patrimoniale vs Benchmark Private Banking")
        categories_radar = [
            "Solvibilità",
            "Controllo Debito",
            "Runway Emergenza",
            "Tasso Risparmio",
            "Capacità Rimborso (DSTI)",
            "Asset Produttivi"
        ]

        # Normalizzazione indici su scala 0-100 per il radar
        score_solv = min(100.0, sr_k["valore"])
        score_debt = max(0.0, 100.0 - da_k["valore"] * 2)
        score_runway = min(100.0, (rw_k["valore"] / 12.0) * 100.0)
        score_sav = min(100.0, (sav_k["valore"] / 40.0) * 100.0)
        score_dsti = max(0.0, 100.0 - ds_k["valore"] * 2.5)
        score_inv = min(100.0, (inv_k["valore"] / 70.0) * 100.0)

        actual_scores = [score_solv, score_debt, score_runway, score_sav, score_dsti, score_inv]
        benchmark_scores = [70.0, 80.0, 50.0, 50.0, 75.0, 70.0]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=actual_scores,
            theta=categories_radar,
            fill='toself',
            name='Profilo Reale',
            line_color='#10b981',
            fillcolor='rgba(16,185,129,0.25)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=benchmark_scores,
            theta=categories_radar,
            fill='toself',
            name='Benchmark Private Banking',
            line_color='#f59e0b',
            fillcolor='rgba(245,158,11,0.1)'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=380,
            margin=dict(l=40, r=40, t=30, b=30)
        )
        apply_chart_theme(fig_radar, portal_mode="wealth")
        st.plotly_chart(fig_radar, use_container_width=True)

    # ──────────────────────────────────────────────────────────
    # SUB-TAB 4: DETTAGLIO CONTI & PORTAFOGLI RISK
    # ──────────────────────────────────────────────────────────
    with sub_conti:
        section("🏦 Dettaglio Conti Correnti, Depositi e Carte")
        if not df_accounts.empty:
            cols_to_show = [c for c in ["name", "institution", "account_type", "currency", "balance", "iban"] if c in df_accounts.columns]
            st.dataframe(
                df_accounts[cols_to_show].rename(columns={
                    "name": "Nome Conto",
                    "institution": "Istituto Bancario",
                    "account_type": "Tipo Conto",
                    "currency": "Valuta",
                    "balance": "Saldo (€)",
                    "iban": "IBAN"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Nessun conto bancario registrato.")

        st.divider()

        section("📈 Portafogli Risk Analytics Collegati")
        if is_snapshot_mode:
            snap_risk_ports = details.get("linked_risk_portfolios", [])
            if snap_risk_ports:
                df_snap_risk = pd.DataFrame(snap_risk_ports)
                st.caption("Portafogli Risk Analytics catturati in questo snapshot storico:")
                st.dataframe(
                    df_snap_risk[["portfolio_id", "name", "base_currency", "last_calc_date", "latest_value"]].rename(columns={
                        "portfolio_id": "ID Portafoglio",
                        "name": "Nome Portafoglio",
                        "base_currency": "Valuta",
                        "last_calc_date": "Data Snapshot Calcolato",
                        "latest_value": "Controvalore (€)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.caption("Nessun portafoglio Risk registrato nello snapshot storico.")
        else:
            tot_risk_live, df_linked_risk = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=current_pid)
            col_rk1, col_rk2 = st.columns([3.5, 1.5])
            with col_rk1:
                if not df_linked_risk.empty:
                    st.markdown(f"Controvalore totale consolidato da Risk Analytics: **{fmt_eur(tot_risk_live)}**")
                    st.dataframe(
                        df_linked_risk[["portfolio_id", "name", "base_currency", "last_calc_date", "latest_value"]].rename(columns={
                            "portfolio_id": "ID Portafoglio Risk",
                            "name": "Nome Portafoglio",
                            "base_currency": "Valuta",
                            "last_calc_date": "Ultimo Calcolo",
                            "latest_value": "Controvalore (€)"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("ℹ️ Nessun portafoglio del modulo Risk collegato a questo profilo patrimoniale. Puoi selezionarli dalla Control Room.")
            with col_rk2:
                st.write("")
                if st.button("🎛️ Gestisci Portafogli in Control Room →", type="secondary", use_container_width=True, key="btn_goto_wcr_risk_link_p13"):
                    st.switch_page("pages/12_🎛️_Wealth_Control_Room.py")

    # ──────────────────────────────────────────────────────────
    # SUB-TAB 5: BILANCIO COMPARATIVO PLURIENNALE
    # ──────────────────────────────────────────────────────────
    with sub_multi:
        section("📊 Bilancio Comparativo Pluriennale (Trend Storico degli Esercizi)")
        st.caption("Prospetto comparativo di Stato Patrimoniale, Conto Economico e indici di solidità anno su anno, con evidenza dei delta di ricchezza netta.")

        comp_res = _load_cached_multi_year_balance_comparison(engine, pid=current_pid)
        df_comp = comp_res.get("comparison_df", pd.DataFrame())

        if not df_comp.empty:
            # KPI Pluriennali di Sintesi
            kpi_m1, kpi_m2, kpi_m3, kpi_m4 = st.columns(4)
            latest_row = df_comp.iloc[0]
            oldest_row = df_comp.iloc[-1]
            cum_delta_pn = float(latest_row["patrimonio_netto"] - oldest_row["patrimonio_netto"])
            cum_delta_pct = (cum_delta_pn / oldest_row["patrimonio_netto"] * 100.0) if oldest_row["patrimonio_netto"] > 0 else 0.0

            with kpi_m1:
                metric_card("Esercizi Esaminati", f"{len(df_comp)} Anni", delta=f"{oldest_row['anno']} - {latest_row['anno']}", delta_color="normal")
            with kpi_m2:
                metric_card("Patrimonio Netto Attuale", fmt_eur(latest_row["patrimonio_netto"]), delta=f"Esercizio {latest_row['anno']}", delta_color="normal")
            with kpi_m3:
                metric_card("Crescita Netta Cumulata", fmt_eur(cum_delta_pn), delta=f"{cum_delta_pct:+.1f}% nel periodo", delta_color="normal" if cum_delta_pn >= 0 else "inverse")
            with kpi_m4:
                avg_sr = df_comp["savings_rate_pct"].mean()
                metric_card("Savings Rate Medio", f"{avg_sr:.1f}%", delta="Media Pluriennale", delta_color="normal" if avg_sr >= 20 else "off")

            st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)

            # Tabella di Sintesi Comparativa
            show_cols = [
                "anno", "totale_attivo", "tot_liquidita", "tot_investimenti", "tot_previdenza",
                "totale_passivo", "patrimonio_netto", "delta_pn_eur", "delta_pn_pct",
                "totale_entrate", "totale_uscite", "risparmio_netto", "savings_rate_pct"
            ]
            valid_cols = [c for c in show_cols if c in df_comp.columns]
            df_disp = df_comp[valid_cols].copy()
            df_disp["anno"] = df_disp["anno"].astype(str)

            st.dataframe(
                df_disp.rename(columns={
                    "anno": "Esercizio",
                    "totale_attivo": "Attivo Totale (€)",
                    "tot_liquidita": "Liquidità (€)",
                    "tot_investimenti": "Investimenti (€)",
                    "tot_previdenza": "Previdenza (€)",
                    "totale_passivo": "Passivo Totale (€)",
                    "patrimonio_netto": "Patrimonio Netto (€)",
                    "delta_pn_eur": "Δ PN Annuo (€)",
                    "delta_pn_pct": "Δ PN Annuo (%)",
                    "totale_entrate": "Entrate (€)",
                    "totale_uscite": "Costi di Vita (€)",
                    "risparmio_netto": "Risparmio Netto (€)",
                    "savings_rate_pct": "Savings Rate (%)"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="📥 Esporta Bilancio Comparativo (CSV)",
                data=df_disp.to_csv(index=False).encode("utf-8"),
                file_name=f"argus_bilancio_comparativo_pluriennale_{current_pid}.csv",
                mime="text/csv",
                key="dl_multi_year_csv"
            )

            st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)

            # Grafico Comparativo Evolutivo
            df_chart = df_comp.sort_values("anno", ascending=True).copy()
            fig_multi = go.Figure()
            fig_multi.add_trace(go.Bar(
                name="Attivo Totale",
                x=df_chart["anno"].astype(str),
                y=df_chart["totale_attivo"],
                marker_color="#10b981",
                text=[fmt_eur(v) for v in df_chart["totale_attivo"]],
                textposition="auto"
            ))
            fig_multi.add_trace(go.Bar(
                name="Passivo Totale",
                x=df_chart["anno"].astype(str),
                y=df_chart["totale_passivo"],
                marker_color="#ef4444",
                text=[fmt_eur(v) for v in df_chart["totale_passivo"]],
                textposition="auto"
            ))
            fig_multi.add_trace(go.Scatter(
                name="Patrimonio Netto",
                x=df_chart["anno"].astype(str),
                y=df_chart["patrimonio_netto"],
                mode="lines+markers+text",
                line=dict(color="#f59e0b", width=3),
                marker=dict(size=8, color="#f59e0b"),
                text=[fmt_eur(v) for v in df_chart["patrimonio_netto"]],
                textposition="top center"
            ))
            fig_multi.update_layout(
                title="Evoluzione Pluriennale: Attivo, Passivo e Patrimonio Netto",
                barmode="group",
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            apply_chart_theme(fig_multi, portal_mode="wealth")
            st.plotly_chart(fig_multi, use_container_width=True)
        else:
            st.info("Dati insufficienti per costruire il bilancio comparativo pluriennale.")

    # ──────────────────────────────────────────────────────────
    # SUB-TAB 6: STRESS TEST CONSOLIDATO SUL PATRIMONIO NETTO
    # ──────────────────────────────────────────────────────────
    with sub_stress:
        from core.macro_stress_engine import compute_consolidated_wealth_stress_test

        section("🌪️ Stress Testing Macroeconomico Consolidato sul Patrimonio Netto (Total Wealth)")
        st.caption(
            "Simulazione regolamentare (EBA Regulatory Adverse 2026, Fed CCAR Severe, Stagflazione e Risk-Off Geopolitico) "
            "applicata simultaneamente a tutte le macro-classi dell'Attivo (Liquidità, Investimenti, Immobili, Previdenza, Beni di Lusso) "
            "per quantificare la perdita di capitale netto e l'amplificazione della leva finanziaria (Debt-to-Assets)."
        )

        wealth_stress_res = compute_consolidated_wealth_stress_test(pbs_data)

        # Top KPI Cards
        stk1, stk2, stk3, stk4 = st.columns(4)
        with stk1:
            metric_card(
                "Patrimonio Netto Base",
                fmt_eur(wealth_stress_res["initial_net_worth_eur"]),
                delta=f"Attivo: {fmt_eur(wealth_stress_res['initial_total_assets_eur'])}",
                delta_color="normal",
            )
        with stk2:
            worst_dd = wealth_stress_res["worst_net_worth_drawdown_pct"]
            metric_card(
                "Peggior Scenario Stress",
                wealth_stress_res["worst_scenario_name"],
                delta=f"Drawdown: {worst_dd:+.1f}%",
                delta_color="inverse",
            )
        with stk3:
            worst_loss = wealth_stress_res["worst_net_worth_loss_eur"]
            metric_card(
                "Massima Perdita di Ricchezza",
                fmt_eur(worst_loss),
                delta="Perdita di Capitale Netto",
                delta_color="inverse",
            )
        with stk4:
            post_dta = wealth_stress_res["worst_post_debt_to_assets_pct"]
            init_dta = wealth_stress_res["initial_debt_to_assets_pct"]
            delta_dta = post_dta - init_dta
            metric_card(
                "Debt-to-Assets Post-Stress",
                f"{post_dta:.1f}%",
                delta=f"+{delta_dta:.1f}% (Base: {init_dta:.1f}%)",
                delta_color="inverse" if post_dta > 30 else "normal",
            )

        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

        scen_df = wealth_stress_res.get("scenarios_df", pd.DataFrame())
        if not scen_df.empty:
            base_nw = wealth_stress_res["initial_net_worth_eur"]

            # Grafico a Barre Orizzontale dei 4 Scenari di Stress
            fig_wstress = go.Figure()
            fig_wstress.add_trace(go.Bar(
                name="Patrimonio Netto Post-Stress",
                y=scen_df["scenario_name"],
                x=scen_df["post_shock_net_worth_eur"],
                orientation="h",
                marker_color="#ef4444",
                text=[f"{fmt_eur(v)} ({dd:+.1f}%)" for v, dd in zip(scen_df["post_shock_net_worth_eur"], scen_df["net_worth_drawdown_pct"])],
                textposition="auto",
            ))

            fig_wstress.add_vline(
                x=base_nw,
                line_width=2,
                line_dash="dash",
                line_color="#10b981",
                annotation_text=f"Base: {fmt_eur(base_nw)}",
                annotation_position="top right"
            )

            fig_wstress.update_layout(
                title="Resilienza del Patrimonio Netto per Scenario Macroeconomico Istituzionale",
                xaxis_title="Patrimonio Netto (€)",
                yaxis_title="",
                height=340,
                margin=dict(l=10, r=10, t=40, b=20),
            )
            apply_chart_theme(fig_wstress, portal_mode="wealth")
            st.plotly_chart(fig_wstress, use_container_width=True)

            # Tabella Dettagliata per Scenario
            st.markdown("##### 📋 Prospetto Analitico di Impatto Patrimoniale")
            show_cols = [
                "scenario_name", "description", "post_shock_assets_eur",
                "post_shock_net_worth_eur", "net_worth_delta_eur",
                "net_worth_drawdown_pct", "post_shock_debt_to_assets_pct"
            ]
            valid_cols = [c for c in show_cols if c in scen_df.columns]
            disp_scen = scen_df[valid_cols].copy()

            st.dataframe(
                disp_scen.rename(columns={
                    "scenario_name": "Scenario Macro",
                    "description": "Descrizione",
                    "post_shock_assets_eur": "Attivo Post-Stress (€)",
                    "post_shock_net_worth_eur": "Patrimonio Netto (€)",
                    "net_worth_delta_eur": "Δ Ricchezza (€)",
                    "net_worth_drawdown_pct": "Drawdown (%)",
                    "post_shock_debt_to_assets_pct": "Debt-to-Assets (%)",
                }),
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="📥 Esporta Stress Test Consolidato (CSV)",
                data=disp_scen.to_csv(index=False).encode("utf-8"),
                file_name=f"argus_consolidated_wealth_stress_{selected_pbs_year}.csv",
                mime="text/csv",
                key="dl_consolidated_wealth_stress_csv"
            )
        else:
            st.info("Nessun dato disponibile per il calcolo dello stress test patrimoniale.")


# ══════════════════════════════════════════════════════════════
# TAB 3: WEALTH TEMPORAL DESK (DINAMICHE TEMPORALI)
# ══════════════════════════════════════════════════════════════

with main_tab_temporal:
    # ── SEZIONE: ANALISI TEMPORALE & DINAMICA STORICA DEL PATRIMONIO ────
    section("📊 Analisi Temporale & Dinamica Storica del Patrimonio (Wealth Temporal Desk)")
    st.caption("Evoluzione di lungo termine del Net Worth, scomposizione della crescita (Risparmio vs Mercato), benchmark 60/40, matrici mensili e drawdown.")

    # Control Bar Interattiva ad Alto Impatto Visivo
    c_tf, c_inf, c_sty = st.columns([1.1, 1.35, 1.55])
    with c_tf:
        sel_tf_label = st.segmented_control(
            "⏱️ Orizzonte:",
            options=["1Y", "2Y", "3Y", "5Y"],
            default="2Y",
            key="wealth_temporal_timeframe"
        ) or "2Y"
    with c_inf:
        sel_val_mode = st.segmented_control(
            "💶 Modalità Valuta:",
            options=["Nominale (€)", "Reale (Netto Infl.)"],
            default="Nominale (€)",
            key="wealth_temporal_val_mode"
        ) or "Nominale (€)"
    with c_sty:
        sel_view_style = st.segmented_control(
            "📊 Stile Traiettoria:",
            options=["Assoluta (€)", "100% Stacked", "Base 100"],
            default="Assoluta (€)",
            key="wealth_temporal_view_style"
        ) or "Assoluta (€)"

    # Parsing opzioni
    tf_map = {"1Y": 12, "2Y": 24, "3Y": 36, "5Y": 60, "1 Anno (1Y)": 12, "2 Anni (2Y)": 24, "3 Anni (3Y)": 36, "5 Anni (5Y)": 60}
    active_tf_months = tf_map.get(sel_tf_label, 24)
    is_real_inflation = ("Reale" in sel_val_mode)

    prog_res, attr_res, bench_res, roll_df, under_res, seas_res, matrix_df = _load_cached_temporal_suite(
        engine, portfolio_id=current_pid, timeframe_months=active_tf_months, adjust_inflation=is_real_inflation
    )

    # Top KPI temporali
    wt_k1, wt_k2, wt_k3, wt_k4, wt_k5 = st.columns(5)
    growth_title = f"Crescita ({sel_tf_label})"
    if is_real_inflation:
        growth_title += " Reale"

    with wt_k1:
        metric_card(growth_title, fmt_eur(prog_res["total_growth_eur"]), delta=f"{prog_res['total_growth_pct']:+.1f}% Totale", delta_color="normal")
    with wt_k2:
        metric_card("Quota da Risparmio", fmt_eur(attr_res["cumulative_savings_eur"]), delta=f"{attr_res['savings_share_pct']:.1f}% della Crescita", delta_color="normal")
    with wt_k3:
        metric_card("Quota da Mercato", fmt_eur(attr_res["cumulative_market_pnl_eur"]), delta=f"{attr_res['market_share_pct']:.1f}% PnL / Alpha", delta_color="normal")
    with wt_k4:
        metric_card("Max Drawdown", f"{under_res['max_drawdown_pct']:.1f}%", delta=fmt_eur(under_res['max_drawdown_eur']), delta_color="inverse")
    with wt_k5:
        metric_card("Beta vs 60/40", f"{bench_res['wealth_beta']:.2f}", delta=f"Alpha: {bench_res['outperformance_pct']:+.1f}%", delta_color="normal" if bench_res['outperformance_pct'] >= 0 else "inverse")

    st.write("")

    # Sottotab temporali
    tab_traj, tab_attr, tab_bench, tab_mat, tab_under, tab_roll, tab_seas = st.tabs([
        "📈 Traiettoria & Asset Classes",
        "🔬 Attribuzione Crescita (Risparmio vs Mercato)",
        "⚖️ Resilienza vs Benchmark 60/40",
        "🗓️ Matrice Mensile di Risparmio",
        "📉 Curva Underwater & High-Water Mark",
        "🔄 Metriche Rolling (6 Mesi)",
        "🍂 Pattern di Stagionalità"
    ])

    with tab_traj:
        df_h = prog_res["history_df"].reset_index()
        # Fallback difensivo proporzionale per cache Streamlit o DataFrame legacy
        if "physical_assets" not in df_h.columns or "pension_plans" not in df_h.columns:
            tot_illiq = df_h.get("illiquid_and_pension", pd.Series(0.0, index=df_h.index))
            tot_act = phys_assets + pens_val
            if tot_act > 0:
                p_ratio = phys_assets / tot_act
                pe_ratio = pens_val / tot_act
            else:
                p_ratio = 1.0
                pe_ratio = 0.0
            if "physical_assets" not in df_h.columns:
                df_h["physical_assets"] = tot_illiq * p_ratio
            if "pension_plans" not in df_h.columns:
                df_h["pension_plans"] = tot_illiq * pe_ratio

        if "real_estate" not in df_h.columns:
            df_h["real_estate"] = pd.Series(0.0, index=df_h.index)
        if "financial_investments" not in df_h.columns:
            df_h["financial_investments"] = pd.Series(0.0, index=df_h.index)
        if "liquid_cash" not in df_h.columns:
            df_h["liquid_cash"] = pd.Series(0.0, index=df_h.index)
        if "total_net_worth" not in df_h.columns:
            df_h["total_net_worth"] = pd.Series(0.0, index=df_h.index)

        has_inv = bool(df_h["financial_investments"].max() > 0)
        has_liq = bool(df_h["liquid_cash"].max() > 0)
        has_re = bool(df_h["real_estate"].max() > 0)
        has_phys = bool(df_h["physical_assets"].max() > 0)
        has_pens = bool(df_h["pension_plans"].max() > 0)

        fig_hist = go.Figure()

        if "100%" in sel_view_style or "Stacked" in sel_view_style or "Area" in sel_view_style:
            st.markdown("##### 📈 Composizione Percentuale del Patrimonio nel Tempo (100% Stacked)")
            total_assets = df_h["financial_investments"] + df_h["liquid_cash"] + df_h["real_estate"] + df_h["physical_assets"] + df_h["pension_plans"]
            total_assets = total_assets.replace(0, 1)

            if has_inv:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=(df_h["financial_investments"] / total_assets) * 100.0,
                    name="Investimenti Quotati", stackgroup='one', line=dict(width=0.5, color="#6366f1"),
                    fillcolor="rgba(99, 102, 241, 0.70)", hovertemplate="%{y:.1f}%"
                ))
            if has_liq:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=(df_h["liquid_cash"] / total_assets) * 100.0,
                    name="Liquidità & Riserve", stackgroup='one', line=dict(width=0.5, color="#38bdf8"),
                    fillcolor="rgba(56, 189, 248, 0.70)", hovertemplate="%{y:.1f}%"
                ))
            if has_re:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=(df_h["real_estate"] / total_assets) * 100.0,
                    name="Immobili (Net Equity)", stackgroup='one', line=dict(width=0.5, color="#f59e0b"),
                    fillcolor="rgba(245, 158, 11, 0.70)", hovertemplate="%{y:.1f}%"
                ))
            if has_phys:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=(df_h["physical_assets"] / total_assets) * 100.0,
                    name="Asset Caveau & Fisici", stackgroup='one', line=dict(width=0.5, color="#eab308"),
                    fillcolor="rgba(234, 179, 8, 0.70)", hovertemplate="%{y:.1f}%"
                ))
            if has_pens:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=(df_h["pension_plans"] / total_assets) * 100.0,
                    name="Previdenza Integrativa", stackgroup='one', line=dict(width=0.5, color="#ec4899"),
                    fillcolor="rgba(236, 72, 153, 0.70)", hovertemplate="%{y:.1f}%"
                ))
            fig_hist.update_layout(
                xaxis_title="Data", yaxis_title="Quota sul Totale Asset (%)",
                yaxis_range=[0, 100], height=380, margin=dict(t=35, l=10, r=10, b=10),
                hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )
        elif "Base 100" in sel_view_style:
            st.markdown("##### 📈 Rendimento e Dinamica Cumulativa (Base 100)")
            nw_b100 = (df_h["total_net_worth"] / max(1.0, df_h["total_net_worth"].iloc[0])) * 100.0

            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=nw_b100, name="Patrimonio Netto",
                line=dict(color="#10b981", width=3.5, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
            ))
            if has_inv and df_h["financial_investments"].iloc[0] > 0:
                inv_b100 = (df_h["financial_investments"] / df_h["financial_investments"].iloc[0]) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=inv_b100, name="Investimenti Quotati",
                    line=dict(color="#6366f1", width=2, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            if has_liq and df_h["liquid_cash"].iloc[0] > 0:
                liq_b100 = (df_h["liquid_cash"] / df_h["liquid_cash"].iloc[0]) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=liq_b100, name="Liquidità & Riserve",
                    line=dict(color="#38bdf8", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            if has_re and df_h["real_estate"].iloc[0] > 0:
                re_b100 = (df_h["real_estate"] / df_h["real_estate"].iloc[0]) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=re_b100, name="Immobili (Net Equity)",
                    line=dict(color="#f59e0b", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            if has_phys and df_h["physical_assets"].iloc[0] > 0:
                phys_b100 = (df_h["physical_assets"] / df_h["physical_assets"].iloc[0]) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=phys_b100, name="Asset Caveau & Fisici",
                    line=dict(color="#eab308", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            if has_pens and df_h["pension_plans"].iloc[0] > 0:
                pens_b100 = (df_h["pension_plans"] / df_h["pension_plans"].iloc[0]) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=pens_b100, name="Previdenza Integrativa",
                    line=dict(color="#ec4899", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            fig_hist.update_layout(
                xaxis_title="Data", yaxis_title="Indice (Base 100)",
                height=380, margin=dict(t=35, l=10, r=10, b=10),
                hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )
        else:
            st.markdown("##### 📈 Evoluzione Storica del Patrimonio per Asset Class (€)")
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["total_net_worth"],
                name="Patrimonio Netto",
                line=dict(color="#10b981", width=3.5, shape="spline", smoothing=0.8),
                hovertemplate="€ %{y:,.2f}"
            ))
            if has_inv:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["financial_investments"],
                    name="Investimenti Quotati",
                    line=dict(color="#6366f1", width=2, shape="spline", smoothing=0.8),
                    hovertemplate="€ %{y:,.2f}"
                ))
            if has_liq:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["liquid_cash"],
                    name="Liquidità & Riserve",
                    line=dict(color="#38bdf8", width=1.8, shape="spline", smoothing=0.8),
                    hovertemplate="€ %{y:,.2f}"
                ))
            if has_re:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["real_estate"],
                    name="Immobili (Net Equity)",
                    line=dict(color="#f59e0b", width=1.8, shape="spline", smoothing=0.8),
                    hovertemplate="€ %{y:,.2f}"
                ))
            if has_phys:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["physical_assets"],
                    name="Asset Caveau & Fisici",
                    line=dict(color="#eab308", width=1.8, shape="spline", smoothing=0.8),
                    hovertemplate="€ %{y:,.2f}"
                ))
            if has_pens:
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=df_h["pension_plans"],
                    name="Previdenza Integrativa",
                    line=dict(color="#ec4899", width=1.8, shape="spline", smoothing=0.8),
                    hovertemplate="€ %{y:,.2f}"
                ))
            fig_hist.update_layout(
                xaxis_title="Data",
                yaxis_title="Valore (€)",
                height=380,
                margin=dict(t=35, l=10, r=10, b=10),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )

        apply_plotly_theme(fig_hist)
        st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})

    with tab_attr:
        col_at_g, col_at_t = st.columns([13, 10])
        with col_at_g:
            st.markdown("##### 🔬 Scomposizione della Crescita Patrimoniale Cumulata")
            df_at = attr_res["attribution_df"].reset_index()
            fig_attr = go.Figure()
            fig_attr.add_trace(go.Bar(
                x=df_at["date"], y=df_at["Risparmio_Cumulato"],
                name="Risparmio da Lavoro (Inflows)", marker_color="#10b981", hovertemplate="€ %{y:,.2f}"
            ))
            fig_attr.add_trace(go.Bar(
                x=df_at["date"], y=df_at["Mercato_PnL_Cumulato"],
                name="Rendimento di Mercato (PnL)", marker_color="#6366f1", hovertemplate="€ %{y:,.2f}"
            ))
            if df_at["Altri_Asset_Cumulato"].abs().sum() > 0:
                fig_attr.add_trace(go.Bar(
                    x=df_at["date"], y=df_at["Altri_Asset_Cumulato"],
                    name="Rivalutazione Altri Asset / Debiti", marker_color="#f59e0b", hovertemplate="€ %{y:,.2f}"
                ))
            fig_attr.update_layout(
                barmode="relative", xaxis_title="Data", yaxis_title="Contributo Cumulato (€)",
                height=340, margin=dict(t=35, l=10, r=10, b=10), hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )
            apply_plotly_theme(fig_attr)
            st.plotly_chart(fig_attr, use_container_width=True, config={"displayModeBar": False})

        with col_at_t:
            st.markdown("##### 📋 Riepilogo Fonti di Crescita")
            metric_card("Totale Crescita Periodo", fmt_eur(attr_res["total_growth_eur"]), delta="100.0% Variazione Net Worth", delta_color="normal")
            st.write("")
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px 16px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #10b981; font-weight: 600;">🟢 Risparmio da Lavoro (Inflows):</span>
                    <span style="font-weight: 700;">{fmt_eur(attr_res['cumulative_savings_eur'])} ({attr_res['savings_share_pct']:.1f}%)</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #6366f1; font-weight: 600;">🟣 Rendimento Mercato (PnL):</span>
                    <span style="font-weight: 700;">{fmt_eur(attr_res['cumulative_market_pnl_eur'])} ({attr_res['market_share_pct']:.1f}%)</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #f59e0b; font-weight: 600;">🟡 Rivalutazione Asset / Debiti:</span>
                    <span style="font-weight: 700;">{fmt_eur(attr_res['cumulative_other_eur'])} ({attr_res['other_share_pct']:.1f}%)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab_bench:
        col_bm_g, col_bm_t = st.columns([13, 10])
        with col_bm_g:
            st.markdown("##### ⚖️ Dinamica vs Benchmark Globale 60/40 (Base 100)")
            df_bc = bench_res["comparison_df"].reset_index()
            fig_bench = go.Figure()
            fig_bench.add_trace(go.Scatter(
                x=df_bc["date"], y=df_bc["Patrimonio_Base100"],
                name="Patrimonio Net Worth", line=dict(color="#10b981", width=3.2, shape="spline", smoothing=0.8),
                hovertemplate="%{y:.2f}"
            ))
            fig_bench.add_trace(go.Scatter(
                x=df_bc["date"], y=df_bc["Benchmark_60_40_Base100"],
                name="Benchmark 60/40 (MSCI World + Global Agg)", line=dict(color="#94a3b8", width=2, dash="dot", shape="spline", smoothing=0.8),
                hovertemplate="%{y:.2f}"
            ))
            fig_bench.update_layout(
                xaxis_title="Data", yaxis_title="Indice Base 100", height=340,
                margin=dict(t=35, l=10, r=10, b=10), hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
            )
            apply_plotly_theme(fig_bench)
            st.plotly_chart(fig_bench, use_container_width=True, config={"displayModeBar": False})

        with col_bm_t:
            st.markdown("##### 📊 Metriche Comparative di Resilienza")
            df_bm_table = pd.DataFrame([
                {"Metrica": "Rendimento Cumulativo", "Patrimonio": f"{bench_res['nw_cumulative_return_pct']:+.2f}%", "Benchmark 60/40": f"{bench_res['bm_cumulative_return_pct']:+.2f}%", "Differenziale (Alpha)": f"{bench_res['outperformance_pct']:+.2f}%"},
                {"Metrica": "Volatilità Annualizzata", "Patrimonio": f"{bench_res['nw_volatility_annual_pct']:.2f}%", "Benchmark 60/40": f"{bench_res['bm_volatility_annual_pct']:.2f}%", "Differenziale (Alpha)": f"{bench_res['nw_volatility_annual_pct'] - bench_res['bm_volatility_annual_pct']:+.2f}%"},
                {"Metrica": "Max Drawdown Storico", "Patrimonio": f"-{bench_res['nw_max_drawdown_pct']:.2f}%", "Benchmark 60/40": f"-{bench_res['bm_max_drawdown_pct']:.2f}%", "Differenziale (Alpha)": f"{bench_res['bm_max_drawdown_pct'] - bench_res['nw_max_drawdown_pct']:+.2f}%"},
                {"Metrica": "Beta Patrimoniale", "Patrimonio": f"{bench_res['wealth_beta']:.2f}", "Benchmark 60/40": "1.00", "Differenziale (Alpha)": f"{bench_res['wealth_beta'] - 1.0:+.2f}"}
            ])
            st.dataframe(df_bm_table, use_container_width=True, hide_index=True)

    with tab_mat:
        st.markdown("##### 🗓️ Matrice Mensile dei Flussi Netti di Risparmio (€)")

        def color_wealth_flows(val):
            if pd.isna(val) or val == 0:
                return "color: #484f58; background-color: rgba(255,255,255,0.02);"
            if val > 0:
                intensity = min(0.55, max(0.10, val / 5000.0))
                return f"background-color: rgba(16, 185, 129, {intensity:.2f}); color: #ffffff; font-weight: 600;"
            else:
                intensity = min(0.55, max(0.10, abs(val) / 5000.0))
                return f"background-color: rgba(239, 68, 68, {intensity:.2f}); color: #ffffff; font-weight: 600;"

        styler_mat = matrix_df.style.format("€ {:,.2f}", na_rep="-")
        if hasattr(styler_mat, "map"):
            styler_mat = styler_mat.map(color_wealth_flows)
        elif hasattr(styler_mat, "applymap"):
            styler_mat = styler_mat.applymap(color_wealth_flows)

        st.dataframe(styler_mat, use_container_width=True)

    with tab_under:
        col_u_g, col_u_t = st.columns([13, 10])
        with col_u_g:
            st.markdown("##### 📉 Curva Underwater (Drawdown vs HWM)")
            df_u = under_res["underwater_df"].reset_index()
            fig_under = go.Figure()
            fig_under.add_trace(go.Scatter(
                x=df_u["date"], y=df_u["Drawdown_Pct"],
                name="Drawdown",
                fill="tozeroy",
                fillcolor="rgba(239, 68, 68, 0.20)",
                line=dict(color="#ef4444", width=2.2, shape="spline", smoothing=0.9),
                hovertemplate="%{y:.2f}%"
            ))
            fig_under.update_layout(
                xaxis_title="Data",
                yaxis_title="Contrazione dal Massimo (%)",
                height=320,
                margin=dict(t=15, l=10, r=10, b=10),
                hovermode="x unified"
            )
            apply_plotly_theme(fig_under)
            st.plotly_chart(fig_under, use_container_width=True, config={"displayModeBar": False})
        with col_u_t:
            st.markdown("##### 🔍 Episodi Storici di Drawdown")
            df_ep_disp = under_res["episodes_df"].rename(columns={
                "peak_date": "Picco (HWM)",
                "trough_date": "Minimo",
                "recovery_date": "Recupero",
                "drawdown_pct": "Max DD (%)",
                "is_recovered": "Stato"
            })
            df_ep_disp["Stato"] = df_ep_disp["Stato"].apply(lambda x: "✅ Risolto" if x is True or str(x).lower() == 'true' else "⏳ In Corso")
            styler_ep = df_ep_disp.style.format({
                "Max DD (%)": "-{:.2f}%"
            })
            st.dataframe(
                styler_ep,
                use_container_width=True,
                hide_index=True
            )

    with tab_roll:
        st.markdown("##### 🔄 Metriche Rolling a Finestra Mobile (6 Mesi)")
        df_r = roll_df.reset_index()
        fig_roll = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=["Tasso di Crescita Rolling Net Worth (% Ann.)", "Volatilità Rolling del Patrimonio (% Ann.)"])
        fig_roll.add_trace(go.Scatter(
            x=df_r["date"], y=df_r["Rolling_Growth_Pct"],
            name="Crescita Ann.",
            line=dict(color="#10b981", width=2, shape="spline", smoothing=0.8),
            hovertemplate="%{y:+.2f}%"
        ), row=1, col=1)
        fig_roll.add_trace(go.Scatter(
            x=df_r["date"], y=df_r["Rolling_Wealth_Vol_Pct"],
            name="Volatilità Ann.",
            line=dict(color="#f59e0b", width=2, shape="spline", smoothing=0.8),
            hovertemplate="%{y:.2f}%"
        ), row=2, col=1)
        fig_roll.update_layout(
            height=360,
            margin=dict(t=30, l=10, r=10, b=10),
            showlegend=False,
            hovermode="x unified"
        )
        apply_plotly_theme(fig_roll)
        st.plotly_chart(fig_roll, use_container_width=True, config={"displayModeBar": False})

    with tab_seas:
        st.markdown("##### 🍂 Stagionalità dei Flussi di Cassa & Tasso di Risparmio Medio Mensile")
        df_seas_disp = seas_res["seasonality_df"][["month_name", "avg_inflow_eur", "avg_outflow_eur", "avg_net_savings_eur", "savings_rate_pct", "status"]].rename(columns={
            "month_name": "Mese",
            "avg_inflow_eur": "Entrate Medie (€)",
            "avg_outflow_eur": "Uscite Medie (€)",
            "avg_net_savings_eur": "Risparmio Netto (€)",
            "savings_rate_pct": "Tasso di Risparmio (%)",
            "status": "Valutazione Stagionale"
        })
        styler_seas = df_seas_disp.style.format({
            "Entrate Medie (€)": "€ {:,.2f}",
            "Uscite Medie (€)": "€ {:,.2f}",
            "Risparmio Netto (€)": "€ {:+,.2f}",
            "Tasso di Risparmio (%)": "{:+.1f}%"
        })

        def color_seas_savings(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: #10b981; font-weight: 600;"
                elif val < 0:
                    return "color: #ef4444; font-weight: 600;"
            return ""

        if hasattr(styler_seas, "map"):
            styler_seas = styler_seas.map(color_seas_savings, subset=["Risparmio Netto (€)", "Tasso di Risparmio (%)"])
        elif hasattr(styler_seas, "applymap"):
            styler_seas = styler_seas.applymap(color_seas_savings, subset=["Risparmio Netto (€)", "Tasso di Risparmio (%)"])

        st.dataframe(styler_seas, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# TAB 4: FAMILY OFFICE & STRUTTURE GIURIDICHE
# ══════════════════════════════════════════════════════════════
# TAB 4: FAMILY OFFICE & STRUTTURE GIURIDICHE
# ══════════════════════════════════════════════════════════════
with main_tab_fo:
    # ── FAMILY OFFICE MULTI-ENTITY & HOLDING CONSOLIDATOR ───────
    section("🏢 Family Office Multi-Entity & Holding Consolidator")
    st.caption("Consolidamento patrimoniale tra diverse entità giuridiche del nucleo familiare (Persona Fisica, Holding SRL, Società Semplice, Trust) con elisione automatica delle partite infragruppo (finanziamenti soci) e analisi convenienza fiscale PEX (1.2% vs 26%).")

    fo_data, _, _ = _load_cached_family_office_suite(engine, portfolio_id=current_pid)

    fo_k1, fo_k2, fo_k3, fo_k4 = st.columns(4)
    with fo_k1:
        metric_card("Patrimonio Consolidato Gruppo", fmt_eur(fo_data["consolidated_family_office_net_worth"]), delta=f"{fo_data['entities_count']} Entità Segregate", delta_color="normal")
    with fo_k2:
        metric_card("Attivi Lordi Totali", fmt_eur(fo_data["total_gross_assets_eur"]), delta="Somma Lorda Entità", delta_color="normal")
    with fo_k3:
        metric_card("Partite Infragruppo Elise", fmt_eur(fo_data["eliminated_intercompany_amount_eur"]), delta="Elisione Finanziamenti Soci", delta_color="normal")
    with fo_k4:
        metric_card("Risparmio Fiscale PEX Annuo", fmt_eur(fo_data["tax_efficiency_pex"]["annual_tax_saving_eur"]), delta=f"{fo_data['tax_efficiency_pex']['tax_saving_pct']:.1f}% vs Persona Fisica", delta_color="normal")

    st.write("")

    c_fo_t, c_fo_p = st.columns([3, 2])
    with c_fo_t:
        st.markdown("##### 🏛️ Dettaglio Entità Giuridiche del Nucleo Familiare")
        st.dataframe(
            fo_data["entities_df"][["name", "entity_type", "gross_assets_eur", "third_party_liabilities_eur", "intercompany_receivables_eur", "intercompany_liabilities_eur", "consolidated_net_equity_eur", "weight_on_consolidated_pct", "effective_tax_rate_est"]].rename(columns={
                "name": "Denominazione Entità",
                "entity_type": "Forma Giuridica",
                "gross_assets_eur": "Attivo Lordo (€)",
                "third_party_liabilities_eur": "Debiti Terzi (€)",
                "intercompany_receivables_eur": "Crediti Infragruppo (€)",
                "intercompany_liabilities_eur": "Debiti Infragruppo (€)",
                "consolidated_net_equity_eur": "Net Equity Consolidata (€)",
                "weight_on_consolidated_pct": "Peso Gruppo (%)",
                "effective_tax_rate_est": "Tax Rate (%)"
            }),
            use_container_width=True,
            hide_index=True
        )

    with c_fo_p:
        st.markdown("##### 💡 Analisi Fiscale Comparativa (PEX Art. 87 TUIR)")
        st.markdown(f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 10px; padding: 14px 18px;">
            <b style="color: #38bdf8; font-size: 14px;">Vantaggio Fiscale Holding di Famiglia:</b><br>
            <span style="font-size: 12px; color: #cbd5e1;">
            Su una base imponibile di <b>€ {fo_data['tax_efficiency_pex']['reference_capital_gain_eur']:,.0f}</b> di dividendi e plusvalenze societarie reinvestite:<br>
            • <b>Persona Fisica (Ritenuta 26%):</b> Imposta € {fo_data['tax_efficiency_pex']['tax_persona_fisica_eur']:,.2f} &rarr; Netti reinvestibili: € {fo_data['tax_efficiency_pex']['reference_capital_gain_eur'] - fo_data['tax_efficiency_pex']['tax_persona_fisica_eur']:,.2f}<br>
            • <b>Holding SRL (PEX 1.2% effettivo):</b> Imposta € {fo_data['tax_efficiency_pex']['tax_holding_pex_eur']:,.2f} &rarr; Netti reinvestibili: € {fo_data['tax_efficiency_pex']['reference_capital_gain_eur'] - fo_data['tax_efficiency_pex']['tax_holding_pex_eur']:,.2f}<br>
            <b style="color: #34d399;">Risparmio Fiscale per Ciclo: € {fo_data['tax_efficiency_pex']['annual_tax_saving_eur']:,.2f} ({fo_data['tax_efficiency_pex']['tax_saving_pct']:.1f}% di sgravio)</b>
            </span>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 5: RISCHIO FX & ATTRIBUZIONE BRINSON MULTI-ASSET
# ══════════════════════════════════════════════════════════════
with main_tab_fx:
    # ── RISCHIO DI CAMBIO & FX FORWARD HEDGING OVERLAY ───────────
    section("💱 Rischio di Cambio & FX Forward Hedging Overlay")
    st.caption("Mappatura dell'esposizione valutaria estera (USD, GBP, CHF, JPY), stima del costo dei Forward Points (Covered Interest Parity) e simulazione di strategie di copertura a confronto.")

    _, fx_res, br_res = _load_cached_family_office_suite(engine, portfolio_id=current_pid)

    fx_k1, fx_k2, fx_k3, fx_k4 = st.columns(4)
    with fx_k1:
        metric_card("Esposizione Valute Estere", fmt_eur(fx_res["foreign_exposure_eur"]), delta=f"{fx_res['foreign_exposure_pct']:.1f}% del Patrimonio", delta_color="normal")
    with fx_k2:
        metric_card("Costo Annuo Hedging Stimato", fmt_eur(fx_res["annual_hedging_cost_eur"]), delta="Differenziale Tassi Interbancari", delta_color="normal")
    with fx_k3:
        metric_card("Drawdown Shock FX (-15%)", fmt_eur(fx_res["unhedged_fx_shock_loss_eur"]), delta="Senza Copertura (Unhedged)", delta_color="inverse")
    with fx_k4:
        metric_card("Drawdown con Hedging", fmt_eur(fx_res["hedged_fx_shock_loss_eur"]), delta="Con Copertura Parziale 50%", delta_color="normal")

    st.write("")

    if not fx_res["exposures_df"].empty:
        st.dataframe(
            fx_res["exposures_df"][["currency", "nominal_amount_eur", "weight_pct", "local_interest_rate_pct", "annual_forward_points_cost_pct", "hedged_ratio_pct", "annual_cost_eur"]].rename(columns={
                "currency": "Divisa Estera",
                "nominal_amount_eur": "Controvalore (€)",
                "weight_pct": "Peso (%)",
                "local_interest_rate_pct": "Tasso Locale (%)",
                "annual_forward_points_cost_pct": "Costo Fwd Points (%)",
                "hedged_ratio_pct": "Quota Coperta (%)",
                "annual_cost_eur": "Costo Annuo Copertura (€)"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Patrimonio interamente denominato in Euro (EUR). Rischio di cambio nullo.")

    st.divider()

    # ── ATTRIBUZIONE DI PERFORMANCE BRINSON MULTI-ASSET ──────────
    section("🎯 Attribuzione di Performance Brinson Multi-Asset (Total Wealth)")
    st.caption("Scomposizione matematica dell'extra-rendimento patrimoniale (Alpha) rispetto a un Composite Benchmark Strategico in Effetto Allocazione (Asset Class), Effetto Selezione (Strumenti) ed Effetto Interazione.")

    br_k1, br_k2, br_k3, br_k4 = st.columns(4)
    with br_k1:
        metric_card("Rendimento Patrimonio", f"{br_res['portfolio_total_return_pct']:+.2f}%", delta=f"Benchmark: {br_res['benchmark_total_return_pct']:+.2f}%", delta_color="normal")
    with br_k2:
        metric_card("Extra-Rendimento (Alpha)", f"{br_res['excess_return_pct']:+.2f}%", delta="Rendimento Netto Attivo", delta_color="normal" if br_res["excess_return_pct"] >= 0 else "inverse")
    with br_k3:
        metric_card("Effetto Allocazione", f"{br_res['allocation_effect_total_pct']:+.2f}%", delta="Scelta Macro Asset Classes", delta_color="normal" if br_res["allocation_effect_total_pct"] >= 0 else "inverse")
    with br_k4:
        metric_card("Effetto Selezione", f"{br_res['selection_effect_total_pct']:+.2f}%", delta="Scelta Singoli Strumenti", delta_color="normal" if br_res["selection_effect_total_pct"] >= 0 else "inverse")

    st.write("")

    st.dataframe(
        br_res["breakdown_df"][["asset_class", "portfolio_weight_pct", "benchmark_weight_pct", "portfolio_return_pct", "benchmark_return_pct", "allocation_effect_pct", "selection_effect_pct", "total_contribution_pct"]].rename(columns={
            "asset_class": "Classe di Attivo",
            "portfolio_weight_pct": "Peso Portafoglio (%)",
            "benchmark_weight_pct": "Peso Benchmark (%)",
            "portfolio_return_pct": "Rendimento Portafoglio (%)",
            "benchmark_return_pct": "Rendimento Benchmark (%)",
            "allocation_effect_pct": "Effetto Allocazione (%)",
            "selection_effect_pct": "Effetto Selezione (%)",
            "total_contribution_pct": "Contributo Totale (%)"
        }),
        use_container_width=True,
        hide_index=True
    )


# ══════════════════════════════════════════════════════════════
# TAB 6: GLOBAL WEALTH STRESS-TESTING & RESILIENZA
# ══════════════════════════════════════════════════════════════
with main_tab_stress:
    from core.wealth.wealth_stress_engine import (
        PRESET_STRESS_SCENARIOS,
        create_liquidity_squeeze_timeline_chart,
        create_wealth_waterfall_chart,
        run_wealth_stress_test,
        simulate_wealth_recovery_trajectories,
    )

    st.markdown("""
    <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-left: 4px solid #ef4444; border-radius: 10px; padding: 14px 18px; margin-bottom: 15px;">
        <div style="font-size: 14.5px; font-weight: 750; color: #f87171;">🌪️ Global Wealth Stress-Testing 3D &amp; Waterfall Breakdown</div>
        <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Simula l'impatto di shock macroeconomici estremi e congiunti (crisi immobiliare, stagflazione, cigno nero, shock reddituale) su tutte le componenti del patrimonio.</div>
    </div>
    """, unsafe_allow_html=True)

    scen_keys = list(PRESET_STRESS_SCENARIOS.keys()) + ["CUSTOM"]
    scen_labels = {k: PRESET_STRESS_SCENARIOS[k]["name"] for k in PRESET_STRESS_SCENARIOS}
    scen_labels["CUSTOM"] = "⚙️ Scenario Personalizzato (Custom Shocks)"

    col_sc_picker, col_sc_info = st.columns([1.5, 2.5])
    with col_sc_picker:
        sel_scen_key = st.selectbox(
            "Seleziona Scenario di Stress:",
            options=scen_keys,
            format_func=lambda k: scen_labels[k],
            key="nw_stress_scen_picker"
        )

    if sel_scen_key != "CUSTOM":
        active_params = dict(PRESET_STRESS_SCENARIOS[sel_scen_key])
        with col_sc_info:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-top: 5px; font-size: 12px; color: #c9d1d9;">
                <b>Dettagli Scenario:</b> {active_params['description']}<br>
                <span style="color:#8b949e;">Durata prevista: <b>{active_params.get('duration_months', 12)} mesi</b> &bull; Shock Azioni: <b style="color:#ef4444;">{active_params['equity_shock_pct']:+.1f}%</b> &bull; Immobili: <b style="color:#ef4444;">{active_params['real_estate_shock_pct']:+.1f}%</b> &bull; Tassi: <b style="color:#fbbf24;">+{active_params['mortgage_rate_hike_bps']:.0f} bps</b></span>
            </div>
            """, unsafe_allow_html=True)
    else:
        with col_sc_info:
            st.markdown("""
            <div style="background: rgba(255,153,0,0.06); border: 1px solid rgba(255,153,0,0.2); border-radius: 8px; padding: 10px 14px; margin-top: 5px; font-size: 12px; color: #ffb74d;">
                <b>Configurazione Parametrica:</b> Calibra gli slider sottostanti per testare qualsiasi shock combinato.
            </div>
            """, unsafe_allow_html=True)

        c_sl1, c_sl2, c_sl3, c_sl4 = st.columns(4)
        with c_sl1:
            eq_s = st.slider("📉 Shock Azionario (%):", -60.0, 20.0, -25.0, 5.0, key="sl_eq_s")
            bnd_s = st.slider("📉 Shock Obbligazionario (%):", -30.0, 10.0, -10.0, 2.0, key="sl_bnd_s")
        with c_sl2:
            re_s = st.slider("🏡 Shock Immobili (%):", -40.0, 20.0, -15.0, 5.0, key="sl_re_s")
            gold_s = st.slider("⌚ Oro / Caveau (%):", -30.0, 50.0, 10.0, 5.0, key="sl_gold_s")
        with c_sl3:
            pen_s = st.slider("🛡️ Shock Previdenza (%):", -50.0, 10.0, -15.0, 5.0, key="sl_pen_s")
            rate_s = st.slider("📈 Rialzo Tassi Mutuo (bps):", 0, 500, 200, 25, key="sl_rate_s")
        with c_sl4:
            exp_s = st.slider("🛒 Aumento Spese Fisse (%):", 0.0, 30.0, 10.0, 2.0, key="sl_exp_s")
            extra_c = st.number_input("⚡ Spesa Extra Cash (€):", 0.0, 100000.0, 10000.0, 5000.0, key="sl_extra_c")

        active_params = {
            "name": "Scenario Personalizzato",
            "equity_shock_pct": eq_s,
            "bonds_shock_pct": bnd_s,
            "real_estate_shock_pct": re_s,
            "physical_gold_shock_pct": gold_s,
            "pension_shock_pct": pen_s,
            "mortgage_rate_hike_bps": rate_s,
            "living_expenses_hike_pct": exp_s,
            "extra_expense_cash": extra_c,
            "duration_months": 12
        }

    stress_summary_dict = {
        "total_net_worth": tot_nw,
        "liquid_cash": liq_cash,
        "financial_investments": fin_inv,
        "physical_assets": phys_assets,
        "real_estate_total": re_val,
        "real_estate_equity": re_val - liab_val,
        "pension_total": pens_val,
        "total_liabilities": liab_val,
        "wealth_health_score": health_sc,
        "monthly_expenses": max(500.0, liq_cash / max(0.1, runway_m))
    }

    # Passaggio del contesto di rischio per trasmissione ticker-level se disponibile
    risk_sub = getattr(st.session_state.get("workspace_context"), "risk", None)
    stress_out = run_wealth_stress_test(stress_summary_dict, active_params, risk_context=risk_sub)

    # KPI Pre vs Post Stress
    st.write("")
    sk1, sk2, sk3, sk4 = st.columns(4)
    with sk1:
        metric_card(
            "Net Worth Post-Shock",
            fmt_eur(stress_out["post_shock"]["net_worth"]),
            delta=f"{stress_out['deltas']['net_worth_pct']:+.1f}% ({fmt_eur(stress_out['deltas']['net_worth'])})",
            delta_color="inverse"
        )
    with sk2:
        metric_card(
            "Cassa Residua Post-Stress",
            fmt_eur(stress_out["post_shock"]["liquid_cash"]),
            delta=f"Runway {stress_out['post_shock']['runway_months']:.1f} Mesi",
            delta_color="normal" if stress_out["post_shock"]["runway_months"] >= 6 else "inverse"
        )
    with sk3:
        metric_card(
            "Investimenti Post-Shock",
            fmt_eur(stress_out["post_shock"]["financial_investments"]),
            delta=fmt_eur(stress_out["deltas"]["financial_investments"]),
            delta_color="inverse"
        )
    with sk4:
        metric_card(
            "Health Score Stressato",
            f"{stress_out['post_shock']['health_score']:.0f} / 100",
            delta=f"Pre: {stress_out['pre_shock']['health_score']:.0f}/100",
            delta_color="normal" if stress_out["post_shock"]["health_score"] >= 70 else "inverse"
        )

    # Indicatori Istituzionali di Liquidity Squeeze & Trasmissione Mutui
    lq = stress_out.get("liquidity_squeeze", {})
    mtg = stress_out.get("mortgage_impact", {})
    st.write("")
    lq1, lq2, lq3, lq4 = st.columns(4)
    with lq1:
        t_star = float(lq.get("months_to_forced_liquidation", 999.0))
        t_text = f"{t_star:.1f} Mesi" if t_star < 999 else "Nessuna Vendita Forzata"
        metric_card(
            "Point of Forced Liquidation (t*)",
            t_text,
            delta="Rischio Liquidazione" if lq.get("forced_liquidation_triggered") else "Buffer Capiente",
            delta_color="inverse" if lq.get("forced_liquidation_triggered") else "normal"
        )
    with lq2:
        shortfall = float(lq.get("capital_shortfall_eur", 0.0))
        metric_card(
            "Deficit di Liquidità Stress",
            fmt_eur(shortfall),
            delta=f"Perdita Irrev. {fmt_eur(lq.get('irreversible_loss_eur', 0.0))}" if shortfall > 0 else "Nessun Deficit",
            delta_color="inverse" if shortfall > 0 else "normal"
        )
    with lq3:
        swr_val = float(lq.get("fire_swr_stressed_pct", 4.0))
        swr_base = float(lq.get("fire_swr_base_pct", 4.0))
        metric_card(
            "Dynamic FIRE SWR (Stress)",
            f"{swr_val:.1f}%",
            delta=f"Pre-Stress: {swr_base:.1f}% (Guyton-Klinger)",
            delta_color="normal" if swr_val >= 3.5 else "inverse"
        )
    with lq4:
        delta_pmt = float(mtg.get("monthly_payment_delta", 0.0))
        stressed_r = float(mtg.get("stressed_rate", 2.0))
        metric_card(
            "Impatto Rata Mutuo",
            f"+€ {delta_pmt:,.2f}/m" if delta_pmt > 0 else "€ 0/m",
            delta=f"Tasso Stressato: {stressed_r:.2f}%" if delta_pmt > 0 else "Tasso Invariato",
            delta_color="inverse" if delta_pmt > 0 else "normal"
        )

    st.write("")
    tab_wf, tab_sq, tab_mc = st.tabs([
        "📊 Waterfall Scomposizione Net Worth",
        "⏳ Liquidity Squeeze & Forced Selling",
        "📈 Proiezione Ripresa Monte Carlo (10 Anni)"
    ])

    with tab_wf:
        st.plotly_chart(create_wealth_waterfall_chart(stress_out), use_container_width=True)

    with tab_sq:
        st.plotly_chart(create_liquidity_squeeze_timeline_chart(stress_out), use_container_width=True)

    with tab_mc:
        st.plotly_chart(simulate_wealth_recovery_trajectories(stress_out["post_shock"]["net_worth"]), use_container_width=True)




# ── V9.12.0: FAMILY OFFICE GENERATIONAL SUCCESSION OPTIMIZER ────────
st.markdown("---")
st.markdown("#### 🌳 Ottimizzatore Successorio Generazionale Multi-Veicolo (Patto di Famiglia vs Trust vs Polizze)")
st.caption("Confronto probabilistico a 30 anni tra Regime Ordinario, Holding Familiare (PEX 95% Art. 87 TUIR / Patto ex Art. 768-bis c.c.), Trust Fiduciario (AdE 34/E/2022) e Polizze Vita PPLI (Art. 12 TUS).")

from core.wealth.succession_optimizer import compute_family_succession_optimization

with st.expander("⚙️ Configura Asse Ereditario & Profilo Familiare", expanded=False):
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        succ_liq = st.number_input("Liquidita & Titoli Finanziari (€):", min_value=0.0, value=5000000.0, step=500000.0)
        succ_biz = st.number_input("Partecipazione Azienda / Holding (€):", min_value=0.0, value=10000000.0, step=1000000.0)
    with f_c2:
        succ_re = st.number_input("Patrimonio Immobiliare Privato (€):", min_value=0.0, value=4000000.0, step=500000.0)
        succ_heirs = st.number_input("Numero di Eredi / Figli:", min_value=1, max_value=6, value=2, step=1)

succ_res = compute_family_succession_optimization(
    liquid_investments_eur=succ_liq,
    operating_business_equity_eur=succ_biz,
    real_estate_properties_eur=succ_re,
    num_children=succ_heirs,
)

succ_k1, succ_k2, succ_k3 = st.columns(3)
with succ_k1:
    metric_card("Patrimonio Iniziale", fmt_eur(succ_res["initial_estate_total_eur"]), delta="G1 Fondatore", delta_color="normal")
with succ_k2:
    metric_card("Architettura Raccomandata", succ_res["recommended_strategy"], delta="Ottimizzazione Fiscale", delta_color="normal")
with succ_k3:
    best_tax_alpha = succ_res["strategies"][succ_res["recommended_strategy"]]["tax_alpha_eur"]
    metric_card("Tax Alpha Generazionale", fmt_eur(best_tax_alpha), delta="Risparmio Fiscale 30Y", delta_color="normal")

st.markdown("##### 📊 Confronto Architetture di Protezione & Successione")
st.dataframe(pd.DataFrame(succ_res["summary_table"]), use_container_width=True, hide_index=True)

# ── V9.13.0: PRIVATE MARKETS PACING & DE-SMOOTHING (YALE ENDOWMENT) ──
st.markdown("---")
st.markdown("#### 🏛️ Private Markets Cash Flow Pacing (Takahashi-Alexander) & De-smoothing Econometrico")
st.caption("Modellazione J-Curve a 10 anni (Chiamate, Distribuzioni, NAV) secondo Takahashi-Alexander (2001) e correzione econometrica di Geltner-Fisher per la reale volatilita non quotata.")

from core.wealth.private_markets_engine import compute_private_markets_analytics

with st.expander("⚙️ Parametri Impegno Fondo Private Equity / Venture Capital", expanded=True):
    pe_c1, pe_c2, pe_c3 = st.columns(3)
    with pe_c1:
        pe_commit = st.number_input("Impegno Totale di Capitale (Commitment €):", min_value=100_000.0, value=5_000_000.0, step=500_000.0, key="pe_comm_in")
    with pe_c2:
        pe_life = st.slider("Durata Vita del Fondo (Anni):", min_value=5, max_value=15, value=10, step=1, key="pe_life_in")
    with pe_c3:
        pe_growth = st.slider("Tasso di Crescita Atteso Asset (% annuo):", min_value=2.0, max_value=25.0, value=10.0, step=0.5, key="pe_g_in") / 100.0

# Esecuzione simulazione pacing
pe_res = compute_private_markets_analytics(
    commitment_eur=pe_commit,
    fund_life_years=pe_life,
    growth_rate=pe_growth,
    observed_returns=[0.02, 0.025, 0.018, 0.022, 0.031, 0.015, 0.028, 0.019],
)

pek1, pek2, pek3, pek4 = st.columns(4)
with pek1:
    metric_card("Net IRR Atteso", f"{pe_res['net_irr_pct']:.2f}%", delta="Rendimento Annuo Interno", delta_color="normal")
with pek2:
    metric_card("Multiplo TVPI", f"{pe_res['tvpi']:.2f}x", delta=f"DPI: {pe_res['dpi']:.2f}x", delta_color="normal")
with pek3:
    metric_card("Picco Fabbisogno Capitale", fmt_eur(pe_res["peak_capital_deficit_eur"]), delta=f"Trough Anno {pe_res['j_curve_trough_year']}", delta_color="inverse")
with pek4:
    metric_card("PME Kaplan-Schoar", f"{pe_res['pme_kaplan_schoar']:.2f}x", delta=f"Direct Alpha: {pe_res['direct_alpha_pct']:+.2f}%", delta_color="normal")

st.markdown("##### 📈 Profilo Temporale J-Curve: Flussi di Cassa & Valutazione NAV (€)")
sched_df = pd.DataFrame(pe_res["schedule"])

fig_pe = go.Figure()
fig_pe.add_trace(go.Bar(x=sched_df["Anno"], y=sched_df["Capital Call (€)"], name="Capital Calls (Versamenti)", marker_color="#f87171"))
fig_pe.add_trace(go.Bar(x=sched_df["Anno"], y=sched_df["Distribuzioni (€)"], name="Distribuzioni (Rimborsi)", marker_color="#34d399"))
fig_pe.add_trace(go.Scatter(x=sched_df["Anno"], y=sched_df["NAV (€)"], name="NAV Fondo (Valore Residuo)", mode="lines+markers", line=dict(color="#38bdf8", width=3)))
fig_pe.update_layout(
    title="Dinamica dei Flussi di Cassa Annuali e Crescita NAV",
    xaxis_title="Anno di Vita del Fondo",
    yaxis_title="Euro (€)",
    barmode="group",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=400,
)
st.plotly_chart(apply_plotly_theme(fig_pe), use_container_width=True)

st.markdown("##### 📉 Correzione Econometrica di De-smoothing (Geltner-Fisher)")
ds_info = pe_res["desmoothing"]
if ds_info:
    dsk1, dsk2, dsk3 = st.columns(3)
    with dsk1:
        metric_card("Volatilità Osservata (Appraisal)", f"{ds_info['observed_vol_pct']:.2f}%", delta="Artificialmente Bassa", delta_color="normal")
    with dsk2:
        metric_card("Volatilità De-smoothed Reale", f"{ds_info['desmoothed_vol_pct']:.2f}%", delta=f"Sottostima: {ds_info['understatement_ratio']:.2f}x", delta_color="inverse")
    with dsk3:
        metric_card("Autocorrelazione Lag-1 (ρ)", f"{ds_info['autocorrelation_rho']:.3f}", delta="Inerzia delle Perizie", delta_color="normal")

st.markdown("##### 📋 Piano Annuale Dettagliato dei Flussi di Cassa del Fondo")
st.dataframe(sched_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════
# TAB 7: PRODOTTI STRUTTURATI & REPORTING REGOLAMENTARE PRIIPs / SFDR
# ══════════════════════════════════════════════════════════════
with main_tab_struct:
    st.markdown("### 💎 Ingegneria Finanziaria: Certificati Strutturati & Reporting PRIIPs/SFDR")
    st.caption("Pricing Monte Carlo multi-asset Worst-Of (Phoenix & Reverse Convertible) e compliance disclosure regolamentare (PRIIPs RTS & SFDR RTS).")

    sub_struct_prod, sub_reg_rep = st.tabs([
        "💎 Prezzatore Prodotti Strutturati & Greche",
        "📋 Reporting PRIIPs KID (SRI) & SFDR ESG (Annex I)"
    ])

    with sub_struct_prod:
        from core.structured_products_engine import compute_structured_product_pricing

        st.markdown("#### 💎 Valutazione Worst-Of Phoenix Autocallable & Reverse Convertible")
        sp_c1, sp_c2, sp_c3 = st.columns(3)
        with sp_c1:
            prod_choice = st.selectbox("Tipologia Certificato:", ["phoenix_autocallable", "reverse_convertible"], format_func=lambda x: "Phoenix Autocallable (Memory Coupon)" if x == "phoenix_autocallable" else "Reverse Convertible (Cedola Fissa)", key="sp_type_sel")
            sp_nominal = st.number_input("Valore Nominale per Titolo (€):", min_value=100.0, value=1000.0, step=100.0, key="sp_nom_in")
            sp_mat_yrs = st.slider("Scadenza Totale (Anni):", min_value=0.5, max_value=5.0, value=2.0, step=0.5, key="sp_mat_slider")
        with sp_c2:
            sp_coupon_pa = st.number_input("Cedola Annua (%):", min_value=1.0, max_value=25.0, value=8.5, step=0.5, key="sp_coup_in") / 100.0
            sp_obs_freq = st.selectbox("Frequenza Rilevazione Cedola/Autocall:", [3, 6, 12], format_func=lambda x: f"Ogni {x} Mesi", index=1, key="sp_freq_sel")
            sp_mem_toggle = st.checkbox("Effetto Memoria Cedole", value=True, key="sp_mem_check")
        with sp_c3:
            sp_bar_autocall = st.slider("Barriera Autocall (% Spot Iniziale):", min_value=80, max_value=120, value=100, step=5, key="sp_bar_auto") / 100.0
            sp_bar_coupon = st.slider("Barriera Cedola (% Spot Iniziale):", min_value=50, max_value=90, value=70, step=5, key="sp_bar_coup") / 100.0
            sp_bar_prot = st.slider("Barriera Protezione a Scadenza (%):", min_value=40, max_value=80, value=60, step=5, key="sp_bar_prot") / 100.0

        if st.button("🚀 Valuta Certificato & Calcola Greche", key="btn_run_struct", type="primary", use_container_width=True):
            with st.spinner("Simulazione Monte Carlo correlata su paniere Worst-Of (SX5E, SPX, NKY)..."):
                sp_res = compute_structured_product_pricing(
                    product_type=prod_choice,
                    nominal=sp_nominal,
                    maturity_years=sp_mat_yrs,
                    observation_frequency_months=sp_obs_freq,
                    coupon_rate_p_a=sp_coupon_pa,
                    has_memory_coupon=sp_mem_toggle,
                    coupon_barrier_pct=sp_bar_coupon,
                    autocall_barrier_pct=sp_bar_autocall,
                    protection_barrier_pct=sp_bar_prot,
                    n_simulations=10000,
                )
                st.session_state["struct_prod_last"] = sp_res

        if "struct_prod_last" in st.session_state:
            s_res = st.session_state["struct_prod_last"]
            grk = s_res["greeks"]

            spk1, spk2, spk3, spk4 = st.columns(4)
            with spk1:
                metric_card("Fair Value / Prezzo", fmt_eur(s_res["present_value"]), delta=f"{s_res['price_pct_nominal']:.2f}% del Nominale", delta_color="normal")
            with spk2:
                metric_card("Vita Media Attesa", f"{s_res['expected_duration_years']:.2f} Anni", delta=f"Autocall Prob: {s_res['autocall_probability_total']*100:.1f}%", delta_color="normal")
            with spk3:
                metric_card("Rendimento Cedolare Atteso", f"{s_res['expected_coupon_yield_p_a']*100:.2f}% p.a.", delta=f"Nominale: {sp_coupon_pa*100:.1f}%", delta_color="normal")
            with spk4:
                metric_card("Rischio Perdita Capitale", f"{s_res['knock_in_loss_probability']*100:.2f}%", delta="Prob. Knock-In", delta_color="inverse")

            st.markdown("##### 📐 Greche di Primo e Secondo Ordine & Sensibilità Barriera")
            g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns(5)
            with g_col1:
                st.metric("Delta (Δ)", f"{grk['delta']:.4f}")
            with g_col2:
                st.metric("Gamma (Γ)", f"{grk['gamma']:.6f}")
            with g_col3:
                st.metric("Vega (ν)", f"{grk['vega']:.4f} €/%")
            with g_col4:
                st.metric("Theta (θ)", f"{grk['theta']:.4f} €/m")
            with g_col5:
                st.metric("Sens. Barriera", f"{grk['barrier_sensitivity']:.4f} €/+1%")

            st.markdown("##### 📅 Programma Cedole & Probabilità di Rimborso Anticipato per Data di Rilevazione")
            st.dataframe(pd.DataFrame(s_res["observation_schedule"]), use_container_width=True, hide_index=True)

    with sub_reg_rep:
        from core.regulatory_reporting_engine import compute_regulatory_dossier

        st.markdown("#### 📋 Prospetto Regolamentare PRIIPs KID & SFDR ESG (Annex I)")
        r_c1, r_c2, r_c3 = st.columns(3)
        with r_c1:
            kid_rating = st.selectbox("Rating Creditizio Emittente (CRM):", ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"], index=2, key="kid_rat_sel")
            kid_rhp = st.number_input("Periodo di Detenzione Raccomandato (RHP Anni):", min_value=1.0, max_value=10.0, value=5.0, step=1.0, key="kid_rhp_in")
        with r_c2:
            kid_inv_eur = st.number_input("Investimento di Riferimento (€):", min_value=1000.0, value=10000.0, step=1000.0, key="kid_inv_in")
            sfdr_art_sel = st.selectbox("Classificazione SFDR:", ["Article 6", "Article 8", "Article 9"], index=1, key="sfdr_art_sel")
        with r_c3:
            taxo_align = st.slider("Allineamento Tassonomia UE (%):", min_value=0.0, max_value=100.0, value=25.0, step=5.0, key="taxo_align_in")
            sust_inv_pct = st.slider("Quota Investimenti Sostenibili SFDR (%):", min_value=0.0, max_value=100.0, value=35.0, step=5.0, key="sust_inv_in")

        reg_res = compute_regulatory_dossier(
            issuer_credit_rating=kid_rating,
            rhp_years=kid_rhp,
            investment_amount_eur=kid_inv_eur,
            sfdr_article=sfdr_art_sel,
            taxonomy_alignment_pct=taxo_align,
            sustainable_investment_pct=sust_inv_pct,
        )

        kid_info = reg_res["priips_kid"]
        sfdr_info = reg_res["sfdr_disclosures"]

        rk1, rk2, rk3, rk4 = st.columns(4)
        with rk1:
            metric_card("Summary Risk Indicator (SRI)", f"Livello {kid_info['sri_score']} / 7", delta=f"MRM {kid_info['mrm_score']} | CRM {kid_info['crm_score']}", delta_color="normal")
        with rk2:
            metric_card("PRIIPs VEV (Volatilità)", f"{kid_info['vev_percent']:.2f}%", delta="Cornish-Fisher VEV", delta_color="normal")
        with rk3:
            metric_card("Classificazione SFDR", sfdr_info["sfdr_classification"], delta="Light Green" if sfdr_info["sfdr_classification"] == "Article 8" else ("Dark Green" if sfdr_info["sfdr_classification"] == "Article 9" else "Standard"), delta_color="normal")
        with rk4:
            metric_card("Allineamento Tassonomia UE", f"{sfdr_info['taxonomy_alignment_pct']:.1f}%", delta=f"Sostenibile: {sfdr_info['sustainable_investment_pct']:.1f}%", delta_color="normal")

        st.markdown("##### 🎯 Scenari di Performance PRIIPs RTS (1 Anno, Metà RHP, Scadenza RHP)")
        perf_data = []
        for scen_name, horizons_dict in kid_info["performance_scenarios"].items():
            row = {"Scenario": scen_name.capitalize()}
            for h_label, h_val in horizons_dict.items():
                row[f"{h_label} (€)"] = fmt_eur(h_val["terminal_value_eur"])
                row[f"{h_label} (%)"] = f"{h_val['annualized_return_pct']:+.2f}%"
            perf_data.append(row)
        st.dataframe(pd.DataFrame(perf_data), use_container_width=True, hide_index=True)

        st.markdown("##### 🌍 Tabella SFDR Annex I: 14 Indicatori Principali degli Effetti Negativi (PAI)")
        st.dataframe(pd.DataFrame(sfdr_info["pai_indicators"]), use_container_width=True, hide_index=True)


        # ── v9.16.0: TELEMETRY RIBBON, LIVE PORTFOLIO AUTO-BINDING & DELTA COMPARATOR ──
        from core.ux_institutional_hub import (
            render_institutional_telemetry_ribbon,
            render_live_portfolio_autobind_banner,
            render_scenario_delta_comparator,
            render_segmented_workspace_switcher,
            style_institutional_chart,
        )

        render_institutional_telemetry_ribbon(page_badge="WEALTH MANAGEMENT, COMMODITIES & EXECUTION DESK")
        live_bind = render_live_portfolio_autobind_banner(
            key_prefix="p13_wealth_exec",
            model_label="Optimal Liquidation & Commodity Desk",
        )
        _ = render_segmented_workspace_switcher(
            workspace_key="p13_v916_domain",
            label="🧭 Selettore Rapido Desk Istituzionale:",
            options=[
                "🌐 Vista Integrata (Commodity + Optimal Liquidation)",
                "🛢️ Schwartz 2-Factor Commodity Futures & Spread Options",
                "⚡ Intraday Optimal Liquidation (Almgren-Chriss vs VWAP/TWAP)",
            ],
        )

        # ── v9.15.0: SCHWARTZ 2-FACTOR COMMODITY FUTURES & OPTIMAL LIQUIDATION ──
        st.divider()
        section("🛢️ Schwartz (1997) 2-Factor Commodity Futures & Convenience Yield Term Structure")
        st.caption("Modellazione stocastica a 2 fattori di Gibson-Schwartz per materie prime: prezzo spot S_t e convenience yield mean-reverting δ_t, classificazione Contango/Backwardation, Roll Yield implicito e opzioni Calendar/Storage Spread (Kirk 1995).")

        from core.commodity_engine import compute_commodity_term_structure
        from core.optimal_liquidation_engine import compute_optimal_execution_schedule

        cm_c1, cm_c2, cm_c3, cm_c4 = st.columns(4)
        with cm_c1:
            cm_name = st.selectbox("Materia Prima:", ["Brent Crude Oil (ICE)", "TTF Natural Gas", "Gold Bullion (LBMA)", "Copper LME Grade A"], index=0, key="cm_name_sel")
            cm_spot = st.number_input("Prezzo Spot S0 ($/€):", min_value=1.0, value=82.50, step=2.5, key="cm_spot_in")
        with cm_c2:
            cm_cy0 = st.slider("Convenience Yield Iniziale δ0 (%):", min_value=-10.0, max_value=25.0, value=8.5, step=0.5, key="cm_cy0_in") / 100.0
            cm_cylr = st.slider("Convenience Yield Long-Run α (%):", min_value=-5.0, max_value=15.0, value=4.5, step=0.5, key="cm_cylr_in") / 100.0
        with cm_c3:
            cm_kappa = st.slider("Velocità Mean-Reversion κ:", min_value=0.20, max_value=4.0, value=1.45, step=0.10, key="cm_kappa_in")
            cm_vol1 = st.slider("Volatilità Spot σ1 (%):", min_value=5.0, max_value=80.0, value=32.0, step=1.0, key="cm_vol1_in") / 100.0
        with cm_c4:
            cm_vol2 = st.slider("Volatilità Convenience Yield σ2 (%):", min_value=5.0, max_value=80.0, value=24.0, step=1.0, key="cm_vol2_in") / 100.0
            cm_seas = st.slider("Ampiezza Stagionalità (%):", min_value=0.0, max_value=8.0, value=1.8, step=0.2, key="cm_seas_in") / 100.0

        cm_res = compute_commodity_term_structure(
            commodity_name=cm_name,
            spot_price=cm_spot,
            initial_convenience_yield=cm_cy0,
            long_run_convenience_yield=cm_cylr,
            mean_reversion_speed=cm_kappa,
            spot_volatility=cm_vol1,
            convenience_yield_volatility=cm_vol2,
            seasonality_amplitude=cm_seas,
        )

        cmk1, cmk2, cmk3, cmk4 = st.columns(4)
        with cmk1:
            metric_card("Regime Struttura a Termine", cm_res["market_regime"], delta=f"Half-Life: {cm_res['half_life_months']:.1f} mesi", delta_color="normal")
        with cmk2:
            metric_card("Futures 1 Anno F(0, 1Y)", f"$ {cm_res['one_year_futures_price']:.2f}", delta=f"Spot: $ {cm_res['spot_price']:.2f}", delta_color="normal")
        with cmk3:
            metric_card("Roll Yield Implicito (1Y)", f"{cm_res['one_year_roll_yield_pct']:+.2f}%", delta="Rendimento da Rullaggio", delta_color="normal" if cm_res["one_year_roll_yield_pct"] >= 0 else "inverse")
        with cmk4:
            sp_opt = cm_res["calendar_spread_option_3m_12m"]
            metric_card("Opzione Calendar Spread (3M-12M)", f"$ {sp_opt['option_price']:.2f}", delta=f"Kirk Vol: {sp_opt['kirk_composite_vol_pct']:.1f}%", delta_color="normal")

        cm_df = pd.DataFrame(cm_res["term_structure"])
        fig_cm = go.Figure()
        fig_cm.add_trace(go.Scatter(x=cm_df["tenor_label"], y=cm_df["futures_price_seasonal"], mode="lines+markers", name="Curva Futures 2-Fattori (Stagionale)", line=dict(color="#f59e0b", width=3)))
        fig_cm.add_trace(go.Scatter(x=cm_df["tenor_label"], y=cm_df["futures_price_structural"], mode="lines", name="Curva Strutturale Schwartz", line=dict(color="#38bdf8", width=2, dash="dash")))
        fig_cm.add_trace(go.Scatter(x=cm_df["tenor_label"], y=cm_df["cost_of_carry_benchmark"], mode="lines", name="Cost-of-Carry Classico", line=dict(color="#94a3b8", width=1.8, dash="dot")))
        fig_cm.update_layout(
            title=f"Curva Futures a Termine {cm_name}: Modello a 2 Fattori di Schwartz vs Cost-of-Carry",
            xaxis_title="Scadenza Contratto",
            yaxis_title="Prezzo Futures ($/€)",
            height=380,
            margin=dict(l=10, r=10, b=10, t=40),
        )
        style_institutional_chart(fig_cm, title=f"Curva Futures a Termine {cm_name}: Modello a 2 Fattori di Schwartz vs Cost-of-Carry", height=380)
        st.plotly_chart(fig_cm, use_container_width=True)
        st.dataframe(cm_df, use_container_width=True, hide_index=True)

        st.divider()
        section("⚡ Intraday Optimal Liquidation & Algorithmic Slicing (Almgren-Chriss vs VWAP/TWAP)")
        st.caption("Ottimizzazione dell'esecuzione intraday con legge dell'impatto temporaneo a radice quadrata h(v) = η·σ·(v/V)^0.5, profilo volumetrico a U e confronto tra traiettoria risk-averse Almgren-Chriss, Dynamic VWAP (POV-Capped) e TWAP.")

        ol_c1, ol_c2, ol_c3, ol_c4 = st.columns(4)
        with ol_c1:
            ol_ticker = st.text_input("Ticker Ordine Istituzionale:", value=live_bind["top_ticker"] if live_bind.get("autobind_enabled") else "ENI.MI", key="ol_tk_in")
            ol_shares = st.number_input("Quantità Azioni da Liquidare:", min_value=0.01, value=max(0.01, float(live_bind.get("top_shares", 250_000.0))) if live_bind.get("autobind_enabled") else 250_000.0, step=10.0, key="ol_sh_in")
        with ol_c2:
            ol_px = st.number_input("Prezzo Spot Mid (€):", min_value=0.01, value=max(0.01, float(live_bind["top_spot_price"])) if live_bind.get("autobind_enabled") else 14.80, step=0.5, key="ol_px_in")
            ol_adv = st.number_input("Volume Medio Giornaliero (ADV Azioni):", min_value=1_000.0, value=float(live_bind.get("adv_shares", 5_000_000.0)) if live_bind.get("autobind_enabled") else 5_000_000.0, step=50_000.0, key="ol_adv_in")
        with ol_c3:
            _def_ol_vol = round(float(np.clip(float(live_bind.get("daily_volatility", 0.018)) * 100.0, 0.5, 6.0)), 1) if live_bind.get("autobind_enabled") else 1.8
            ol_vol = st.slider("Volatilità Giornaliera (%):", min_value=0.5, max_value=6.0, value=_def_ol_vol, step=0.1, key="ol_vol_in") / 100.0
            ol_pov = st.slider("Limite Max Participation Rate (POV %):", min_value=5, max_value=35, value=15, step=1, key="ol_pov_in") / 100.0
        with ol_c4:
            ol_eta = st.slider("Coefficiente Impatto Temporaneo (η):", min_value=0.05, max_value=0.40, value=0.14, step=0.01, key="ol_eta_in")
            ol_lambda = st.select_slider("Avversione al Rischio di Mercato (λ):", options=[1e-7, 1e-6, 2.5e-6, 5e-6, 1e-5], value=2.5e-6, key="ol_lam_in")

        ol_res = compute_optimal_execution_schedule(
            ticker=ol_ticker,
            order_shares=ol_shares,
            spot_price=ol_px,
            adv_shares=ol_adv,
            daily_volatility=ol_vol,
            temp_impact_eta=ol_eta,
            risk_aversion_lambda=float(ol_lambda),
            max_pov_cap=ol_pov,
        )
        s_opt = ol_res["strategies"]["almgren_chriss_optimal"]
        s_vwap = ol_res["strategies"]["dynamic_vwap"]
        s_twap = ol_res["strategies"]["uniform_twap"]

        ok1, ok2, ok3, ok4 = st.columns(4)
        with ok1:
            metric_card("Controvalore Ordine & % ADV", fmt_eur(ol_res["order_notional_eur"]), delta=f"{ol_res['order_pct_of_adv']:.2f}% dell'ADV giornaliero", delta_color="normal")
        with ok2:
            metric_card("Implementation Shortfall (AC Optimal)", f"{s_opt['expected_cost_bps']:.2f} bps", delta=f"{fmt_eur(s_opt['expected_cost_eur'])} | Urgency κ={ol_res['urgency_parameter_kappa']:.2f}", delta_color="normal")
        with ok3:
            metric_card("Dynamic VWAP (POV-Capped)", f"{s_vwap['expected_cost_bps']:.2f} bps", delta=f"Max POV: {s_vwap['max_pov_rate_pct']:.1f}%", delta_color="normal")
        with ok4:
            metric_card("Algoritmo Raccomandato", ol_res["recommended_algorithm"].split(" (")[0], delta=f"Timing Risk: ±{s_opt['timing_risk_std_bps']:.1f} bps", delta_color="normal")

        sched_df = pd.DataFrame(ol_res["intraday_schedule"])
        fig_ol = go.Figure()
        fig_ol.add_trace(go.Scatter(x=sched_df["time_bucket"], y=sched_df["inventory_optimal"], mode="lines+markers", name="Inventario Almgren-Chriss (IS)", line=dict(color="#10b981", width=3)))
        fig_ol.add_trace(go.Scatter(x=sched_df["time_bucket"], y=sched_df["inventory_vwap"], mode="lines+markers", name="Inventario Dynamic VWAP", line=dict(color="#6366f1", width=2.5)))
        fig_ol.add_trace(go.Scatter(x=sched_df["time_bucket"], y=sched_df["inventory_twap"], mode="lines", name="Inventario Uniform TWAP", line=dict(color="#94a3b8", width=2, dash="dash")))
        fig_ol.update_layout(
            title="Curva di Decadimento dell'Inventario Intraday (Almgren-Chriss vs Dynamic VWAP vs TWAP)",
            xaxis_title="Fascia Oraria Intraday",
            yaxis_title="Azioni Residue in Portafoglio",
            height=380,
            margin=dict(l=10, r=10, b=10, t=40),
        )
        style_institutional_chart(fig_ol, title="Curva di Decadimento dell'Inventario Intraday (Almgren-Chriss vs Dynamic VWAP vs TWAP)", height=380)
        st.plotly_chart(fig_ol, use_container_width=True)
        render_scenario_delta_comparator(
            scenario_key="optimal_liquidation_p13",
            scenario_title="Intraday Optimal Liquidation",
            current_metrics={
                "AC Optimal Cost (bps)": float(s_opt["expected_cost_bps"]),
                "Dynamic VWAP Cost (bps)": float(s_vwap["expected_cost_bps"]),
                "TWAP Benchmark Cost (bps)": float(s_twap["expected_cost_bps"]),
                "Timing Risk Std (bps)": float(s_opt["timing_risk_std_bps"]),
            },
            higher_is_better_map={
                "AC Optimal Cost (bps)": False,
                "Dynamic VWAP Cost (bps)": False,
                "TWAP Benchmark Cost (bps)": False,
                "Timing Risk Std (bps)": False,
            },
        )
        st.dataframe(sched_df, use_container_width=True, hide_index=True)


        # ── v9.17.0 / v9.18.0: ALM / LDI IMMUNIZATION & AVELLANEDA-STOIKOV VPIN ENGINE ──
        st.divider()
        section("🏛️ Asset-Liability Management (ALM), Immunizzazione di Redington & Cash-Flow Matching LP")
        st.caption("Copertura attuariale delle passività pluriennali, Funding Ratio, Surplus-at-Risk 99%, dimensionamento Receiver IRS 20Y (LDI) e portafoglio obbligazionario dedicato calcolato via Programmazione Lineare (scipy.optimize.linprog).")

        from core.alm_ldi_engine import compute_alm_ldi_immunization
        from core.market_making_vpin_engine import compute_market_making_and_vpin
        from core.ux_institutional_hub import (
            apply_macro_shock_to_inputs,
            render_bento_kpi_card,
            render_sr117_audit_drawer,
        )
        from core.ux_quant_canvas import (
            build_alm_cashflow_and_surplus_chart,
            build_avellaneda_stoikov_microstructure_chart,
        )

        al_c1, al_c2, al_c3 = st.columns(3)
        with al_c1:
            _def_al_assets = max(1_000.0, round(float(live_bind.get("total_nav_eur", 64_233.0)), 2)) if live_bind.get("autobind_enabled") else 125_000_000.0
            al_assets = st.number_input("Valore Attuale Attivi ALM (€):", min_value=1_000.0, value=float(_def_al_assets), step=10_000.0, key="al_assets_in")
        with al_c2:
            al_dur = st.slider("Modified Duration Attivi (Anni):", min_value=1.0, max_value=22.0, value=6.8, step=0.2, key="al_dur_in")
        with al_c3:
            al_disc = st.slider("Tasso di Sconto Attuariale (%):", min_value=1.0, max_value=6.5, value=3.4, step=0.1, key="al_disc_in") / 100.0

        shocked_alm = apply_macro_shock_to_inputs({"asset_value": al_assets, "discount_rate": al_disc})
        eff_al_assets = float(shocked_alm["asset_value"])
        eff_al_disc = float(shocked_alm["discount_rate"])
        alm_prov = "GLOBAL SHOCK OVERRIDE" if shocked_alm.get("macro_shock_active") else "LIVE BALANCE SHEET"

        alm_res = compute_alm_ldi_immunization(
            asset_portfolio_eur=eff_al_assets,
            asset_modified_duration=al_dur,
            discount_rate=eff_al_disc,
        )

        alk1, alk2, alk3, alk4 = st.columns(4)
        with alk1:
            render_bento_kpi_card(
                "ALM Funding Ratio",
                f"{alm_res['funding_ratio_pct']:.1f}%",
                f"Surplus: {fmt_eur(alm_res['accounting_surplus_eur'])}",
                provenance=alm_prov,
                limit_utilization_pct=min(100.0, float(alm_res["funding_ratio_pct"])),
                sparkline_values=[94.0, 97.5, 101.2, 104.0, float(alm_res["funding_ratio_pct"])],
                accent_color="#10b981" if alm_res["funding_ratio_pct"] >= 100.0 else "#ef4444",
            )
        with alk2:
            render_bento_kpi_card(
                "Duration Gap (A vs L)",
                f"{alm_res['duration_gap_years']:+.2f} Anni",
                f"Liab Duration: {alm_res['liability_modified_duration']:.2f}Y",
                provenance=alm_prov,
                accent_color="#3b82f6" if abs(alm_res["duration_gap_years"]) <= 1.0 else "#f59e0b",
            )
        with alk3:
            render_bento_kpi_card(
                "LDI Receiver Swap 20Y",
                fmt_eur(alm_res["required_20y_receiver_swap_notional_eur"]),
                f"Hedge Ratio: {alm_res['liability_hedge_ratio_pct']:.1f}%",
                provenance=alm_prov,
                accent_color="#10b981",
            )
        with alk4:
            render_bento_kpi_card(
                "Surplus-at-Risk 99% (1Y)",
                fmt_eur(alm_res["surplus_at_risk_99_eur"]),
                "Redington OK ✅" if alm_res["redington_immunization_satisfied"] else "Duration Mismatch ⚠️",
                provenance=alm_prov,
                accent_color="#10b981" if alm_res["redington_immunization_satisfied"] else "#ef4444",
            )

        fig_alm_cf = build_alm_cashflow_and_surplus_chart(alm_res)
        st.plotly_chart(fig_alm_cf, use_container_width=True)
        st.dataframe(pd.DataFrame(alm_res["cashflow_matching_lp"]["bond_allocations"]), use_container_width=True, hide_index=True)
        render_sr117_audit_drawer(
            engine_name="ALM Redington Immunization & Cash-Flow Matching LP Engine",
            latex_formulas=[
                r"\text{Redington Conditions: } PV_A \ge PV_L, \quad D_A^{\text{mod}} = D_L^{\text{mod}}, \quad C_A > C_L",
                r"\min_{\mathbf{x} \ge 0} \mathbf{p}^\top \mathbf{x} \quad \text{s.t.} \quad \mathbf{C}\,\mathbf{x} \ge \mathbf{L}",
            ],
            inputs_dict={"assets_eur": eff_al_assets, "asset_duration": al_dur, "discount_rate": eff_al_disc},
            outputs_dict={"funding_ratio_pct": alm_res["funding_ratio_pct"], "sar_99_eur": alm_res["surplus_at_risk_99_eur"]},
            regulatory_refs=["IORP II Pension Directive", "Solvency II ALM", "Redington (1952)"],
        )

        st.divider()
        section("⚡ Avellaneda-Stoikov (2008) Market-Making & Tossicità Ordini VPIN / Hawkes")
        st.caption("Calcolo del Reservation Price r(s,q,t) e dello spread Bid/Ask ottimo asimmetrico in funzione dell'inventario q, combinato con la metrica di selezione avversa VPIN e il processo auto-eccitante di Hawkes per l'allerta precoce di Flash-Crash.")

        mm_c1, mm_c2, mm_c3 = st.columns(3)
        with mm_c1:
            mm_inv = st.slider("Inventario Attuale Market-Maker q (Azioni):", min_value=-5000.0, max_value=5000.0, value=1500.0, step=250.0, key="mm_inv_in")
        with mm_c2:
            mm_gam = st.slider("Avversione al Rischio Inventario (γ):", min_value=0.01, max_value=0.30, value=0.08, step=0.01, key="mm_gam_in")
        with mm_c3:
            mm_alp = st.slider("Eccitazione Processo di Hawkes (α):", min_value=0.20, max_value=1.30, value=0.85, step=0.05, key="mm_alp_in")

        mm_res = compute_market_making_and_vpin(inventory_q=mm_inv, risk_aversion_gamma=mm_gam, hawkes_alpha=mm_alp)

        mmk1, mmk2, mmk3, mmk4 = st.columns(4)
        with mmk1:
            render_bento_kpi_card(
                "Reservation Price r(s,q,t)",
                f"€ {mm_res['reservation_price']:.4f}",
                f"Skew: {mm_res['inventory_skew_bps']:+.1f} bps vs Mid",
                provenance=alm_prov,
                accent_color="#f59e0b",
            )
        with mmk2:
            render_bento_kpi_card(
                "Quote Ottime Bid / Ask",
                f"€ {mm_res['optimal_bid_price']:.3f} / € {mm_res['optimal_ask_price']:.3f}",
                f"Spread: {mm_res['optimal_spread_bps']:.1f} bps",
                provenance=alm_prov,
                accent_color="#10b981",
            )
        with mmk3:
            render_bento_kpi_card(
                "VPIN Order-Flow Toxicity",
                f"{mm_res['current_vpin_score']:.3f}",
                f"Picco VPIN: {mm_res['peak_vpin_score']:.3f}",
                provenance=alm_prov,
                limit_utilization_pct=min(100.0, float(mm_res["peak_vpin_score"]) * 100.0),
                accent_color="#10b981" if mm_res["peak_vpin_score"] < 0.40 else "#ef4444",
            )
        with mmk4:
            render_bento_kpi_card(
                "Hawkes Branching Ratio (α/β)",
                f"{mm_res['hawkes_branching_ratio_eta']:.2f}",
                mm_res["toxicity_regime"].split(" - ")[0],
                provenance=alm_prov,
                accent_color="#10b981" if "BENIGN" in mm_res["toxicity_regime"] else "#ef4444",
            )

        fig_mm_lob = build_avellaneda_stoikov_microstructure_chart(
            {
                "mid_price": 100.0,
                "reservation_price": mm_res["reservation_price"],
                "optimal_bid": mm_res["optimal_bid_price"],
                "optimal_ask": mm_res["optimal_ask_price"],
                "inventory_units": mm_inv,
            }
        )
        st.plotly_chart(fig_mm_lob, use_container_width=True)
        st.dataframe(pd.DataFrame(mm_res["inventory_quote_schedule"]), use_container_width=True, hide_index=True)
        render_sr117_audit_drawer(
            engine_name="Avellaneda-Stoikov Market-Making & Hawkes VPIN Engine",
            latex_formulas=[
                r"r(s, q, t) = s - q\,\gamma\,\sigma^2\,(T - t), \quad \delta^a + \delta^b = \gamma\,\sigma^2\,(T - t) + \frac{2}{\gamma}\ln\!\left(1 + \frac{\gamma}{\kappa}\right)",
                r"\text{VPIN} = \frac{\sum_{\tau=1}^n |V_\tau^B - V_\tau^S|}{n \cdot V_{\text{bucket}}}, \quad \eta_{\text{Hawkes}} = \frac{\alpha}{\beta}",
            ],
            inputs_dict={"inventory_q": mm_inv, "gamma": mm_gam, "hawkes_alpha": mm_alp},
            outputs_dict={"reservation_price": mm_res["reservation_price"], "vpin_score": mm_res["current_vpin_score"]},
            regulatory_refs=["Avellaneda & Stoikov (2008)", "Easley, López de Prado & O'Hara (2012)", "MiFID II RTS 6"],
        )
