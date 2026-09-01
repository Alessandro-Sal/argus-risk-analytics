# ============================================================
# src/pages/13_🏛️_Patrimonio_e_NetWorth.py
# ARGUS Wealth Management — Consolidated Net Worth & Balance Sheet
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import importlib
import core.ui_utils
import core.wealth.wealth_db
import core.wealth.wealth_engine
import core.wealth

importlib.reload(core.ui_utils)
importlib.reload(core.wealth.wealth_db)
importlib.reload(core.wealth.wealth_engine)
importlib.reload(core.wealth)

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
    generate_executive_tear_sheet_html
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
    # Modalità Live
    df_prof = get_wealth_portfolios(engine)
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

    nw = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
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

    df_accounts = get_wealth_accounts(engine, portfolio_id=current_pid)

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





# ── TOP KPI ROW ─────────────────────────────────────────────

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    metric_card("Patrimonio Netto", fmt_eur(tot_nw), delta="Consolidato", delta_color="normal")
with c2:
    metric_card("Liquidità & Cash", fmt_eur(liq_cash), delta=f"Runway {runway_m:.1f}m", delta_color="normal")
with c3:
    metric_card("Investimenti", fmt_eur(fin_inv), delta="Stocks + Crypto", delta_color="normal")
with c4:
    metric_card("Asset Caveau", fmt_eur(phys_assets), delta=f"Orologi: {fmt_eur(watches_val)}", delta_color="normal")
with c5:
    metric_card("Previdenza", fmt_eur(pens_val), delta="Fondi Pensione", delta_color="normal")
with c6:
    metric_card("Health Score", f"{health_sc:.0f}/100", delta="Solidità", delta_color="normal")

st.divider()

# ── EXECUTIVE TEAR SHEET REPORT TOOLBAR ──────────────────────
col_ts1, col_ts2 = st.columns([3, 1.5])
with col_ts1:
    st.markdown("""
    <div style="font-size:12px; color:#94a3b8; display:flex; align-items:center; gap:8px;">
        <span>📄 <b>Executive Tear Sheet Dossier:</b> Report patrimoniale formattato per stampa A4 o salvataggio PDF stile Private Banking.</span>
    </div>
    """, unsafe_allow_html=True)
with col_ts2:
    tear_sheet_html = generate_executive_tear_sheet_html(engine, portfolio_id=current_pid)
    st.download_button(
        label="📄 Scarica Executive Tear Sheet (PDF/HTML)",
        data=tear_sheet_html.encode("utf-8"),
        file_name=f"argus_executive_tear_sheet_{prof_map.get(current_pid, 'portfolio')}_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html",
        use_container_width=True
    )

with st.expander("👁️ Anteprima Live Executive Tear Sheet (Goldman Sachs Style)", expanded=False):
    st.components.v1.html(tear_sheet_html, height=520, scrolling=True)

st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)



# ── RIGA 1: ALLOCAZIONE GLOBALE DEL PATRIMONIO ─────────────
# ── RIGA 1: ALLOCAZIONE GLOBALE DEL PATRIMONIO ─────────────
head_a1, head_a2 = st.columns([2.2, 1.8])
with head_a1:
    section("📊 Allocazione Globale del Patrimonio")
with head_a2:
    chart_view = st.radio(
        "Visualizzazione:",
        options=["🍩 Donut Istituzionale", "🥧 Sunburst", "🥞 Treemap"],
        horizontal=True,
        label_visibility="collapsed",
        key="alloc_chart_view_mode"
    )

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

