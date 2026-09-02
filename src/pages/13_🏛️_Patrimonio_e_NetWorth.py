# ============================================================
# src/pages/13_🏛️_Patrimonio_e_NetWorth.py
# ARGUS Wealth Management — Consolidated Net Worth & Balance Sheet
# ============================================================

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.ui_utils import (
    apply_plotly_theme,
    fmt_eur,
    fmt_pct,
    inject_custom_css,
    metric_card,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    section,
)
from core.wealth.wealth_db import (
    get_linked_risk_portfolios_summary,
    get_pension_plans,
    get_physical_assets,
    get_wealth_accounts,
    get_wealth_portfolios,
    save_wealth_account,
)
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_family_office_multi_entity_consolidation,
    compute_multi_currency_fx_hedging_engine,
    compute_total_wealth_brinson_attribution,
    generate_advisory_pitchbook_html,
    generate_advisory_pitchbook_pdf,
    generate_executive_tear_sheet_html,
    generate_executive_tear_sheet_pdf,
)
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
def _load_cached_temporal_suite(_engine, portfolio_id: int, timeframe_months: int, adjust_inflation: bool):
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


st.set_page_config(page_title="Patrimonio & Net Worth | ARGUS Wealth", page_icon="🏛️", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

# Connessione DB
db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "investment_risk_bi")
engine = get_engine(db_user, db_pass, db_host, db_port, db_name)


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
        st.title("🏛️ ARGUS Wealth — Patrimonio & Net Worth")
        st.markdown("""
        <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
            <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
            <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per caricare i dati e visualizzare le metriche del Patrimonio Netto.</p>
        </div>
        """, unsafe_allow_html=True)
        sel_box = st.selectbox(
            "Seleziona Profilo Patrimoniale:",
            options=[None] + list(prof_map.keys()),
            format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
            key="nw_unselected_profile_picker"
        )
        if sel_box is not None:
            st.session_state["wealth_active_portfolio_id"] = sel_box
            st.rerun()
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

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p13")
render_wealth_executive_badges(nw)

head_c1, head_c2 = st.columns([3.8, 1.2])
with head_c1:
    st.title("🏛️ ARGUS Wealth — Patrimonio & Net Worth")
    st.caption(f"Consolidamento olistico del patrimonio netto (Liquidità, Portafogli Titoli, Crypto, Caveau e Previdenza) • Sincronizzato al {datetime.now().strftime('%d/%m/%Y %H:%M')}")
with head_c2:
    st.write("")
    if not is_snapshot_mode and len(prof_map) > 1:
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
main_tab_alloc, main_tab_sheet, main_tab_temporal, main_tab_fo, main_tab_fx = st.tabs([
    "🏛️ Bilancio & Allocazione",
    "📋 Stato Patrimoniale & Conti",
    "📊 Wealth Temporal Desk",
    "🏢 Family Office & Holding",
    "💱 Rischio FX & Attribuzione Brinson"
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
    head_a1, head_a2, head_a3 = st.columns([1.1, 1.2, 0.9])
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
            styler_alloc = df_alloc_table.style.format({
                "Controvalore (€)": "€ {:,.2f}",
                "Peso sul Net Worth (%)": "{:.1f}%"
            })
            st.dataframe(styler_alloc, use_container_width=True, hide_index=True)
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
# TAB 2: STATO PATRIMONIALE, CONTI & ASSET
# ══════════════════════════════════════════════════════════════
with main_tab_sheet:
    # ── STATO PATRIMONIALE & CONTI ──────────────────────────────
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

    # ── DETTAGLIO PORTAFOGLI RISK COLLEGATI ─────────────────────
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
            if st.button("🎛️ Gestisci Portafogli in Control Room →", type="secondary", use_container_width=True, key="btn_goto_wcr_risk_link"):
                st.switch_page("pages/12_🎛️_Wealth_Control_Room.py")


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
        fig_hist = go.Figure()

        if "100%" in sel_view_style or "Stacked" in sel_view_style or "Area" in sel_view_style:
            st.markdown("##### 📈 Composizione Percentuale del Patrimonio nel Tempo (100% Stacked)")
            total_assets = df_h["financial_investments"] + df_h["liquid_cash"] + df_h["real_estate"] + df_h["physical_assets"] + df_h["pension_plans"]
            total_assets = total_assets.replace(0, 1)

            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=(df_h["financial_investments"] / total_assets) * 100.0,
                name="Investimenti Quotati", stackgroup='one', line=dict(width=0.5, color="#6366f1"),
                fillcolor="rgba(99, 102, 241, 0.70)", hovertemplate="%{y:.1f}%"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=(df_h["liquid_cash"] / total_assets) * 100.0,
                name="Liquidità & Riserve", stackgroup='one', line=dict(width=0.5, color="#38bdf8"),
                fillcolor="rgba(56, 189, 248, 0.70)", hovertemplate="%{y:.1f}%"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=(df_h["real_estate"] / total_assets) * 100.0,
                name="Immobili (Net Equity)", stackgroup='one', line=dict(width=0.5, color="#f59e0b"),
                fillcolor="rgba(245, 158, 11, 0.70)", hovertemplate="%{y:.1f}%"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=(df_h["physical_assets"] / total_assets) * 100.0,
                name="Asset Caveau & Fisici", stackgroup='one', line=dict(width=0.5, color="#eab308"),
                fillcolor="rgba(234, 179, 8, 0.70)", hovertemplate="%{y:.1f}%"
            ))
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
            nw_b100 = (df_h["total_net_worth"] / df_h["total_net_worth"].iloc[0]) * 100.0
            inv_b100 = (df_h["financial_investments"] / max(1.0, df_h["financial_investments"].iloc[0])) * 100.0
            liq_b100 = (df_h["liquid_cash"] / max(1.0, df_h["liquid_cash"].iloc[0])) * 100.0

            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=nw_b100, name="Patrimonio Netto",
                line=dict(color="#10b981", width=3.5, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=inv_b100, name="Investimenti Quotati",
                line=dict(color="#6366f1", width=2, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=liq_b100, name="Liquidità & Riserve",
                line=dict(color="#38bdf8", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
            ))
            if df_h["physical_assets"].iloc[-1] > 0:
                phys_b100 = (df_h["physical_assets"] / max(1.0, df_h["physical_assets"].iloc[0])) * 100.0
                fig_hist.add_trace(go.Scatter(
                    x=df_h["date"], y=phys_b100, name="Asset Caveau & Fisici",
                    line=dict(color="#eab308", width=1.8, shape="spline", smoothing=0.8), hovertemplate="%{y:.2f} (Base 100)"
                ))
            if df_h["pension_plans"].iloc[-1] > 0:
                pens_b100 = (df_h["pension_plans"] / max(1.0, df_h["pension_plans"].iloc[0])) * 100.0
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
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["financial_investments"],
                name="Investimenti Quotati",
                line=dict(color="#6366f1", width=2, shape="spline", smoothing=0.8),
                hovertemplate="€ %{y:,.2f}"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["liquid_cash"],
                name="Liquidità & Riserve",
                line=dict(color="#38bdf8", width=1.8, shape="spline", smoothing=0.8),
                hovertemplate="€ %{y:,.2f}"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["real_estate"],
                name="Immobili (Net Equity)",
                line=dict(color="#f59e0b", width=1.8, shape="spline", smoothing=0.8),
                hovertemplate="€ %{y:,.2f}"
            ))
            fig_hist.add_trace(go.Scatter(
                x=df_h["date"], y=df_h["physical_assets"],
                name="Asset Caveau & Fisici",
                line=dict(color="#eab308", width=1.8, shape="spline", smoothing=0.8),
                hovertemplate="€ %{y:,.2f}"
            ))
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


