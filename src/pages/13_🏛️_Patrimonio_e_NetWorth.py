# ============================================================
# src/pages/13_🏛️_Patrimonio_e_NetWorth.py
# ARGUS Wealth Management — Consolidated Net Worth & Balance Sheet
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from core.fetcher import get_engine
from core.ui_utils import (
    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    apply_plotly_theme
)
from core.sidebar import render_sidebar
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    generate_executive_tear_sheet_html,
    generate_executive_tear_sheet_pdf,
    generate_advisory_pitchbook_html,
    generate_advisory_pitchbook_pdf,
    compute_family_office_multi_entity_consolidation,
    compute_multi_currency_fx_hedging_engine,
    compute_total_wealth_brinson_attribution
)
from core.wealth.wealth_temporal_engine import (
    compute_wealth_temporal_progression,
    compute_wealth_growth_attribution,
    compute_wealth_benchmark_comparison,
    compute_wealth_monthly_matrix,
    compute_wealth_rolling_metrics,
    compute_wealth_underwater_drawdowns,
    compute_wealth_seasonality_patterns
)
from core.wealth.wealth_db import (
    get_wealth_accounts,
    save_wealth_account,
    get_physical_assets,
    get_pension_plans,
    get_wealth_portfolios,
    get_linked_risk_portfolios_summary
)
from core.wealth.wealth_snapshot import get_wealth_snapshots_history


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



# ── RIGA 1: ALLOCAZIONE GLOBALE DEL PATRIMONIO ─────────────
head_a1, head_a2 = st.columns([1.8, 1.4])
with head_a1:
    section("📊 Allocazione Globale del Patrimonio")
with head_a2:
    chart_view = st.segmented_control(
        "Visualizzazione Grafico:",
        options=["🍩 Donut", "🥧 Sunburst", "🥞 Treemap"],
        default="🍩 Donut",
        label_visibility="collapsed",
        key="alloc_chart_view_mode_seg"
    )
    if not chart_view:
        chart_view = "🍩 Donut"

# Costruzione dettagliata foglie e macro-gruppi
breakdown_items = []
labels = []
parents = []
values = []
colors = []

# 1. Macro-Gruppi
macros_def = [
    ("Investimenti Finanziari", fin_inv, "#4f46e5"),
    ("Liquidità & Cash", liq_cash, "#059669"),
    ("Asset Caveau", phys_assets, "#b45309"),
    ("Previdenza", pens_val, "#be185d")
]
for m_name, m_val, m_col in macros_def:
    if m_val > 0:
        labels.append(m_name)
        parents.append("")
        values.append(m_val)
        colors.append(m_col)

# 2. Investimenti Finanziari (Risk Portfolios)
if is_snapshot_mode:
    snap_risk = details.get("linked_risk_portfolios", [])
    for rk in snap_risk:
        v = float(rk.get("latest_value", 0.0))
        if v > 0:
            r_raw = str(rk.get("name", ""))
            name = "Azioni & ETF" if "stock" in r_raw.lower() else ("Criptovalute" if "crypto" in r_raw.lower() else r_raw)
            col = "#6366f1" if "azioni" in name.lower() or "stock" in name.lower() else "#8b5cf6"
            ic = "📈" if "azioni" in name.lower() or "stock" in name.lower() else "🪙"
            labels.append(name)
            parents.append("Investimenti Finanziari")
            values.append(v)
            colors.append(col)
            breakdown_items.append({"name": name, "macro": "Investimenti Finanziari", "val": v, "color": col, "icon": ic})
    if not snap_risk and fin_inv > 0:
        labels.append("Portafogli Finanziari")
        parents.append("Investimenti Finanziari")
        values.append(fin_inv)
        colors.append("#6366f1")
        breakdown_items.append({"name": "Portafogli Finanziari", "macro": "Investimenti Finanziari", "val": fin_inv, "color": "#6366f1", "icon": "📈"})
else:
    _, df_linked_risk = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=current_pid)
    if not df_linked_risk.empty:
        for _, rk in df_linked_risk.iterrows():
            v = float(rk.get("latest_value", 0.0))
            if v > 0:
                r_name = str(rk.get("name", ""))
                name = "Azioni & ETF" if "stock" in r_name.lower() else ("Criptovalute" if "crypto" in r_name.lower() else r_name)
                col = "#6366f1" if "azioni" in name.lower() or "stock" in name.lower() else "#8b5cf6"
                ic = "📈" if "azioni" in name.lower() or "stock" in name.lower() else "🪙"
                labels.append(name)
                parents.append("Investimenti Finanziari")
                values.append(v)
                colors.append(col)
                breakdown_items.append({"name": name, "macro": "Investimenti Finanziari", "val": v, "color": col, "icon": ic})
    elif fin_inv > 0:
        labels.append("Portafogli Finanziari")
        parents.append("Investimenti Finanziari")
        values.append(fin_inv)
        colors.append("#6366f1")
        breakdown_items.append({"name": "Portafogli Finanziari", "macro": "Investimenti Finanziari", "val": fin_inv, "color": "#6366f1", "icon": "📈"})

# 3. Liquidità & Cash
if is_snapshot_mode:
    snap_accs = details.get("accounts", [])
    other_cash_val = 0.0
    for a in snap_accs:
        b = float(a.get("balance", 0.0))
        a_name = str(a.get("name", "Conto"))
        if b >= 1000:
            c_acc = "#10b981" if "intesa" in a_name.lower() else "#14b8a6"
            labels.append(a_name)
            parents.append("Liquidità & Cash")
            values.append(b)
            colors.append(c_acc)
            breakdown_items.append({"name": a_name, "macro": "Liquidità & Cash", "val": b, "color": c_acc, "icon": "💳"})
        elif b > 0:
            other_cash_val += b
    if other_cash_val > 0:
        labels.append("Altri Conti & Wallet")
        parents.append("Liquidità & Cash")
        values.append(other_cash_val)
        colors.append("#06b6d4")
        breakdown_items.append({"name": "Altri Conti & Wallet", "macro": "Liquidità & Cash", "val": other_cash_val, "color": "#06b6d4", "icon": "⚡"})
else:
    if not df_accounts.empty:
        other_cash_val = 0.0
        for _, a in df_accounts.iterrows():
            b = float(a.get("balance", 0.0))
            a_name = str(a.get("name", "Conto"))
            if b >= 1000:
                c_acc = "#10b981" if "intesa" in a_name.lower() else "#14b8a6"
                labels.append(a_name)
                parents.append("Liquidità & Cash")
                values.append(b)
                colors.append(c_acc)
                breakdown_items.append({"name": a_name, "macro": "Liquidità & Cash", "val": b, "color": c_acc, "icon": "💳"})
            elif b > 0:
                other_cash_val += b
        if other_cash_val > 0:
            labels.append("Altri Conti & Wallet")
            parents.append("Liquidità & Cash")
            values.append(other_cash_val)
            colors.append("#06b6d4")
            breakdown_items.append({"name": "Altri Conti & Wallet", "macro": "Liquidità & Cash", "val": other_cash_val, "color": "#06b6d4", "icon": "⚡"})
    elif liq_cash > 0:
        labels.append("Liquidità & Depositi")
        parents.append("Liquidità & Cash")
        values.append(liq_cash)
        colors.append("#10b981")
        breakdown_items.append({"name": "Liquidità & Depositi", "macro": "Liquidità & Cash", "val": liq_cash, "color": "#10b981", "icon": "💳"})

# 4. Asset Caveau
if is_snapshot_mode:
    snap_phys = details.get("physical_assets", [])
    for pa in snap_phys:
        v = float(pa.get("current_market_value", 0.0))
        if v > 0:
            p_name = str(pa.get("name", "Asset"))
            name = "Oro 18K (Bracciali)" if "braccial" in p_name.lower() or "oro" in p_name.lower() else ("Seiko Automatic" if "seiko" in p_name.lower() else p_name)
            col = "#f59e0b" if "oro" in name.lower() or pa.get("asset_category") == "precious_metals" else "#d97706"
            labels.append(name)
            parents.append("Asset Caveau")
            values.append(v)
            colors.append(col)
            breakdown_items.append({"name": name, "macro": "Asset Caveau", "val": v, "color": col, "icon": "👑"})
    if not snap_phys and phys_assets > 0:
        labels.append("Asset Fisici")
        parents.append("Asset Caveau")
        values.append(phys_assets)
        colors.append("#f59e0b")
        breakdown_items.append({"name": "Asset Fisici", "macro": "Asset Caveau", "val": phys_assets, "color": "#f59e0b", "icon": "👑"})
else:
    df_phys = get_physical_assets(engine, portfolio_id=current_pid)
    if not df_phys.empty:
        for _, pa in df_phys.iterrows():
            v = float(pa.get("current_market_value", 0.0))
            if v > 0:
                p_name = str(pa.get("name", "Asset"))
                name = "Oro 18K (Bracciali)" if "braccial" in p_name.lower() or "oro" in p_name.lower() else ("Seiko Automatic" if "seiko" in p_name.lower() else p_name)
                col = "#f59e0b" if "oro" in name.lower() or pa.get("asset_category") == "precious_metals" else "#d97706"
                labels.append(name)
                parents.append("Asset Caveau")
                values.append(v)
                colors.append(col)
                breakdown_items.append({"name": name, "macro": "Asset Caveau", "val": v, "color": col, "icon": "👑"})
    elif phys_assets > 0:
        labels.append("Asset Fisici")
        parents.append("Asset Caveau")
        values.append(phys_assets)
        colors.append("#f59e0b")
        breakdown_items.append({"name": "Asset Fisici", "macro": "Asset Caveau", "val": phys_assets, "color": "#f59e0b", "icon": "👑"})

# 5. Previdenza
if is_snapshot_mode:
    snap_pens = details.get("pension_plans", [])
    for pp in snap_pens:
        v = float(pp.get("accumulated_value", 0.0))
        if v > 0:
            labels.append("Fondo Pensione")
            parents.append("Previdenza")
            values.append(v)
            colors.append("#ec4899")
            breakdown_items.append({"name": "Fondo Pensione", "macro": "Previdenza", "val": v, "color": "#ec4899", "icon": "🛡️"})
    if not snap_pens and pens_val > 0:
        labels.append("Fondo Pensione")
        parents.append("Previdenza")
        values.append(pens_val)
        colors.append("#ec4899")
        breakdown_items.append({"name": "Fondo Pensione", "macro": "Previdenza", "val": pens_val, "color": "#ec4899", "icon": "🛡️"})
else:
    df_pens = get_pension_plans(engine, portfolio_id=current_pid)
    if not df_pens.empty:
        for _, pp in df_pens.iterrows():
            v = float(pp.get("accumulated_value", 0.0))
            if v > 0:
                labels.append("Fondo Pensione")
                parents.append("Previdenza")
                values.append(v)
                colors.append("#ec4899")
                breakdown_items.append({"name": "Fondo Pensione", "macro": "Previdenza", "val": v, "color": "#ec4899", "icon": "🛡️"})
    elif pens_val > 0:
        labels.append("Fondo Pensione")
        parents.append("Previdenza")
        values.append(pens_val)
        colors.append("#ec4899")
        breakdown_items.append({"name": "Fondo Pensione", "macro": "Previdenza", "val": pens_val, "color": "#ec4899", "icon": "🛡️"})

if breakdown_items and tot_nw > 0:
    col_chart, col_breakdown = st.columns([1.5, 1.5])
    
    with col_chart:
        if "Treemap" in chart_view:
            fig_alloc = go.Figure(go.Treemap(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker=dict(colors=colors, line=dict(color="#0e1117", width=1.5)),
                hovertemplate="<b>%{label}</b><br>Controvalore: <b>€%{value:,.2f}</b><br>Quota sul Totale: <b>%{percentRoot:.1%}</b><extra></extra>"
            ))
            fig_alloc.update_layout(
                margin=dict(t=10, l=10, r=10, b=10),
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", color="#c9d1d9")
            )
        elif "Sunburst" in chart_view:
            fig_alloc = go.Figure(go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker=dict(colors=colors, line=dict(color="#0e1117", width=1.5)),
                insidetextorientation="auto",
                hovertemplate="<b>%{label}</b><br>Controvalore: <b>€%{value:,.2f}</b><br>Quota sul Patrimonio: <b>%{percentRoot:.1%}</b><extra></extra>"
            ))
            fig_alloc.update_layout(
                margin=dict(t=10, l=10, r=10, b=10),
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", color="#c9d1d9")
            )
        else: # Donut Istituzionale (Default)
            d_labels = [it["name"] for it in breakdown_items]
            d_vals = [it["val"] for it in breakdown_items]
            d_cols = [it["color"] for it in breakdown_items]
            
            fig_alloc = go.Figure(go.Pie(
                labels=d_labels,
                values=d_vals,
                hole=0.62,
                marker=dict(colors=d_cols, line=dict(color="#0e1117", width=2)),
                textinfo="percent",
                textposition="outside",
                textfont=dict(size=11, color="#94a3b8"),
                hovertemplate="<b>%{label}</b><br>Controvalore: <b>€ %{value:,.2f}</b><br>Quota sul Patrimonio: <b>%{percent}</b><extra></extra>"
            ))
            
            fig_alloc.update_layout(
                showlegend=False,
                margin=dict(t=20, l=20, r=20, b=20),
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit, sans-serif", color="#c9d1d9"),
                annotations=[
                    dict(
                        text=f"<b style='font-size:22px; color:#ffffff;'>€ {tot_nw:,.0f}</b><br><span style='font-size:10.5px; color:#94a3b8; letter-spacing:0.8px; font-weight:700;'>PATRIMONIO NETTO</span>",
                        x=0.5, y=0.5,
                        font_size=14,
                        showarrow=False
                    )
                ]
            )
        st.plotly_chart(fig_alloc, use_container_width=True)

    with col_breakdown:
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; font-weight:700; color:#ffffff; text-transform:uppercase; letter-spacing:0.3px;">Dettaglio Asset Classes</span>
            <span style="background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); color:#818cf8; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px;">{len(breakdown_items)} Voci Attive</span>
        </div>
        """, unsafe_allow_html=True)
        
        sorted_breakdown = sorted(breakdown_items, key=lambda x: x["val"], reverse=True)
        for it in sorted_breakdown:
            pct_share = (it["val"] / tot_nw) * 100.0
            st.markdown(f"""
            <div style="background:rgba(22, 27, 34, 0.85); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; box-shadow:0 2px 8px rgba(0,0,0,0.15);">
                <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:10px; height:10px; border-radius:50%; background:{it['color']}; box-shadow:0 0 6px {it['color']};"></div>
                    <div>
                        <div style="font-size:13.5px; font-weight:700; color:#f8fafc;">{it['icon']} {it['name']}</div>
                        <div style="font-size:10.5px; color:#94a3b8; font-weight:500;">{it['macro']}</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:14px; font-weight:800; color:#ffffff;">€ {it['val']:,.2f}</div>
                    <div style="font-size:11px; font-weight:700; color:{it['color']};">{pct_share:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
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

st.divider()


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

st.divider()

# ── FAMILY OFFICE MULTI-ENTITY & HOLDING CONSOLIDATOR ───────
section("🏢 Family Office Multi-Entity & Holding Consolidator")
st.caption("Consolidamento patrimoniale tra diverse entità giuridiche del nucleo familiare (Persona Fisica, Holding SRL, Società Semplice, Trust) con elisione automatica delle partite infragruppo (finanziamenti soci) e analisi convenienza fiscale PEX (1.2% vs 26%).")

fo_data, fx_res, br_res = _load_cached_family_office_suite(engine, portfolio_id=current_pid)

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

st.divider()

# ── RISCHIO DI CAMBIO & FX FORWARD HEDGING OVERLAY ───────────
section("💱 Rischio di Cambio & FX Forward Hedging Overlay")
st.caption("Mappatura dell'esposizione valutaria estera (USD, GBP, CHF, JPY), stima del costo dei Forward Points (Covered Interest Parity) e simulazione di strategie di copertura a confronto.")

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

st.divider()

# ── SEZIONE: ANALISI TEMPORALE & DINAMICA STORICA DEL PATRIMONIO ────
section("📊 Analisi Temporale & Dinamica Storica del Patrimonio (Wealth Temporal Desk)")
st.caption("Evoluzione di lungo termine del Net Worth, scomposizione della crescita (Risparmio vs Mercato), benchmark 60/40, matrici mensili e drawdown.")

# Control Bar Interattiva
c_tf, c_inf, c_sty = st.columns([1.3, 1.3, 1.8])
with c_tf:
    sel_tf_label = st.segmented_control(
        "⏱️ Orizzonte Temporale:",
        options=["1 Anno (1Y)", "2 Anni (2Y)", "3 Anni (3Y)", "5 Anni (5Y)"],
        default="2 Anni (2Y)",
        key="wealth_temporal_timeframe"
    ) or "2 Anni (2Y)"
with c_inf:
    sel_val_mode = st.segmented_control(
        "💶 Modalità Valore:",
        options=["Nominale (€)", "Reale (Netto Inflazione)"],
        default="Nominale (€)",
        key="wealth_temporal_val_mode"
    ) or "Nominale (€)"
with c_sty:
    sel_view_style = st.segmented_control(
        "📊 Stile Traiettoria:",
        options=["Linee Assolute (€)", "Area 100% Ponderata", "Base 100 (% Cumulata)"],
        default="Linee Assolute (€)",
        key="wealth_temporal_view_style"
    ) or "Linee Assolute (€)"

# Parsing opzioni
tf_map = {"1 Anno (1Y)": 12, "2 Anni (2Y)": 24, "3 Anni (3Y)": 36, "5 Anni (5Y)": 60}
active_tf_months = tf_map.get(sel_tf_label, 24)
is_real_inflation = (sel_val_mode == "Reale (Netto Inflazione)")

prog_res, attr_res, bench_res, roll_df, under_res, seas_res, matrix_df = _load_cached_temporal_suite(
    engine, portfolio_id=current_pid, timeframe_months=active_tf_months, adjust_inflation=is_real_inflation
)

# Top KPI temporali
wt_k1, wt_k2, wt_k3, wt_k4, wt_k5 = st.columns(5)
growth_title = f"Crescita ({sel_tf_label.split()[0]} {sel_tf_label.split()[1]})"
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

    if sel_view_style == "Area 100% Ponderata":
        st.markdown("##### 📈 Composizione Percentuale del Patrimonio nel Tempo (100% Stacked)")
        total_assets = df_h["financial_investments"] + df_h["liquid_cash"] + df_h["real_estate"] + df_h["illiquid_and_pension"]
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
            x=df_h["date"], y=(df_h["illiquid_and_pension"] / total_assets) * 100.0,
            name="Asset Fisici & Previdenza", stackgroup='one', line=dict(width=0.5, color="#a855f7"),
            fillcolor="rgba(168, 85, 247, 0.70)", hovertemplate="%{y:.1f}%"
        ))
        fig_hist.update_layout(
            xaxis_title="Data", yaxis_title="Quota sul Totale Asset (%)",
            yaxis_range=[0, 100], height=380, margin=dict(t=35, l=10, r=10, b=10),
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )
    elif sel_view_style == "Base 100 (% Cumulata)":
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
            x=df_h["date"], y=df_h["illiquid_and_pension"], 
            name="Asset Fisici & Previdenza", 
            line=dict(color="#a855f7", width=1.5, shape="spline", smoothing=0.8),
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

