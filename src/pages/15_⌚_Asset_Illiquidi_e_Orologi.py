# ============================================================
# src/pages/15_⌚_Asset_Illiquidi_e_Orologi.py
# ARGUS Wealth Management — Luxury Watches, Real Estate & Collectibles
# ============================================================

import importlib
from datetime import date, datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import core.ui_utils

importlib.reload(core.ui_utils)

from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.ui_lifecycle import teardown_view_state
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
    render_institutional_telemetry_ribbon,
    render_kpi_card,
    render_omni_command_bar,
    render_segmented_tabs,
    render_sr117_audit_drawer,
    render_standard_hero,
    render_table_with_export,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_wealth_telemetry_ribbon,
    section,
)
from core.wealth import (
    BULLION_COIN_CATALOG,
    compute_consolidated_net_worth,
    compute_gold_portfolio_historical_trajectory,
    compute_gold_sale_tax_impact,
    compute_private_equity_deal_metrics,
    evaluate_bullion_coin,
    evaluate_metal_asset_dynamically,
    get_bullion_coin_info,
    get_gold_historical_series,
    get_gold_spot_on_date,
    get_live_gold_spot_rates,
    get_physical_assets,
    get_wealth_portfolios,
    parse_precious_metal_specs,
    save_physical_asset,
)
from core.wealth.wealth_modals import render_illiquids_methodology_modal

st.set_page_config(page_title="Asset Illiquidi & Orologi | ARGUS Wealth", page_icon="⌚", layout="wide")
st.session_state.argus_portal_mode = "🏛️ Wealth Management"
inject_custom_css()
render_sidebar()

ctx = ensure_portal_context(module="wealth")
ensure_portfolio_loaded(module_type="wealth")
engine = ctx["engine"]
current_pid = ctx["portfolio_id"]
prof_title = ctx["profile_name"]
prof_map = ctx["profile_map"]
nw_curr = ctx["net_worth"]

if current_pid is None:
    render_omni_command_bar(portal="wealth", context_name="Nessun Profilo", key_suffix="p15")
    from core.ui_utils import render_wealth_profile_picker
    render_wealth_profile_picker(engine, prof_map, key_prefix="p15_picker")
    st.stop()

# ── ATOMIC STATE TEARDOWN ───────────────────────────────────
teardown_view_state(current_pid, active_page="15_Asset_Illiquidi_e_Orologi")

render_omni_command_bar(portal="wealth", context_name=prof_title, key_suffix="p15")
render_wealth_telemetry_ribbon(nw_summary=nw_curr, page_badge="ASSET ILLIQUIDI & OROLOGI", profile_name=prof_title)
render_wealth_executive_badges(nw_curr)

render_standard_hero(
    title="Caveau & Asset Fisici",
    subtitle="Tracciamento, valutazione e rivalutazione di Orologi di Lusso, Immobili, Metalli Preziosi e Private Markets.",
    icon="⌚",
    profile_map=prof_map,
    current_pid=current_pid,
    dialog_callback=render_illiquids_methodology_modal,
    dialog_btn_label="ℹ️ Metodologia Perizie",
)

df_assets = get_physical_assets(engine, portfolio_id=current_pid)

# ── LIVE PRECIOUS METALS FIXING RIBBON ───────────────────────
gold_rates = get_live_gold_spot_rates()
spot_24k = gold_rates.get("gold_eur_per_gram_24k", 112.30)
spot_18k = gold_rates.get("gold_eur_per_gram_18k", 84.22)
spot_ag = gold_rates.get("silver_eur_per_gram", 1.40)
fx_rate = gold_rates.get("eur_usd_rate", 1.1190)
chg_24h = gold_rates.get("change_24h_pct", 0.0)
src_lbl = gold_rates.get("source", "COMEX / LBMA")
is_live = gold_rates.get("is_live", False)
dot_icon = "🟢" if is_live else "🟡"
chg_sign = "+" if chg_24h >= 0 else ""
chg_color = "#10b981" if chg_24h >= 0 else "#f85149"

st.markdown(
    f'''
    <div style="background:linear-gradient(90deg, rgba(245,158,11,0.12) 0%, rgba(22,27,34,0.92) 100%); border:1px solid rgba(245,158,11,0.28); border-radius:10px; padding:10px 18px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:13px; font-weight:800; color:#fbbf24; letter-spacing:0.4px;">🥇 FIXING UFFICIALE METALLI PREZIOSI (COMEX / LBMA SPOT)</span>
            <span style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); padding:2px 7px; border-radius:4px; font-size:10px; color:#94a3b8;">{dot_icon} {src_lbl}</span>
        </div>
        <div style="display:flex; gap:16px; align-items:center; font-size:12px; flex-wrap:wrap;">
            <div>🥇 Oro 24K: <b style="color:#ffffff;">€ {spot_24k:,.2f}/g</b> <span style="color:{chg_color}; font-weight:700;">({chg_sign}{chg_24h:.2f}%)</span></div>
            <div style="color:rgba(255,255,255,0.2);">|</div>
            <div>🥇 Oro 18K (750): <b style="color:#fbbf24;">€ {spot_18k:,.2f}/g</b></div>
            <div style="color:rgba(255,255,255,0.2);">|</div>
            <div>🥈 Argento: <b style="color:#e2e8f0;">€ {spot_ag:,.2f}/g</b></div>
            <div style="color:rgba(255,255,255,0.2);">|</div>
            <div>💱 EUR/USD: <b style="color:#38bdf8;">{fx_rate:.4f}</b></div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)

# Calcolo metriche aggregate (confronto Valore Peritale Statica vs Live Spot)
total_market_val = float(df_assets["current_market_value"].sum()) if not df_assets.empty else 0.0
total_dynamic_val = 0.0
if not df_assets.empty:
    for _, r in df_assets.iterrows():
        specs = parse_precious_metal_specs(r)
        if specs.get("is_precious_metal") and specs.get("weight_grams", 0.0) > 0:
            eval_res = evaluate_metal_asset_dynamically(r)
            total_dynamic_val += eval_res["dynamic_market_value"]
        else:
            total_dynamic_val += float(r.get("current_market_value", 0.0) or 0.0)
else:
    total_dynamic_val = 0.0

total_cost = float(df_assets["purchase_price"].sum()) if not df_assets.empty else 0.0
unrealized_gain = total_market_val - total_cost
gain_pct = (unrealized_gain / total_cost * 100.0) if total_cost > 0 else 0.0
diff_spot = total_dynamic_val - total_market_val
diff_spot_str = f"Live Spot: {fmt_eur(total_dynamic_val)}" if abs(diff_spot) > 1.0 else "Allineato a Spot Live"

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Valore Caveau & Fisico", fmt_eur(total_market_val), delta=diff_spot_str, delta_color="normal")
with c2:
    metric_card("Capitale Investito", fmt_eur(total_cost), delta="Costo Storico d'Acquisto", delta_color="normal")
with c3:
    metric_card("Plusvalenza Latente", fmt_eur(unrealized_gain), delta=f"{gain_pct:+.1f}% Rivalutazione", delta_color="normal" if unrealized_gain >= 0 else "inverse")
with c4:
    watches_cnt = len(df_assets[df_assets["asset_category"] == "luxury_watches"]) if not df_assets.empty else 0
    metals_cnt = len(df_assets[df_assets["asset_category"] == "precious_metals"]) if not df_assets.empty else 0
    other_cnt = len(df_assets) - watches_cnt - metals_cnt if not df_assets.empty else 0
    total_cnt = len(df_assets) if not df_assets.empty else 0

    parts = []
    if watches_cnt > 0:
        parts.append(f"{watches_cnt} {'Orologio' if watches_cnt == 1 else 'Orologi'}")
    if metals_cnt > 0:
        parts.append(f"{metals_cnt} {'Oro/Metallo' if metals_cnt == 1 else 'Metalli Preziosi'}")
    if other_cnt > 0:
        parts.append(f"{other_cnt} {'Altro' if other_cnt == 1 else 'Altri'}")

    delta_comp = " • ".join(parts) if parts else "Nessun Asset Censito"
    cnt_label = f"{total_cnt} {'Pezzo' if total_cnt == 1 else 'Pezzi'}"
    metric_card("Asset nel Caveau", cnt_label, delta=delta_comp, delta_color="normal")

st.divider()

# ── SELETTORE MODULI ASSET ILLIQUIDI STILE BLOOMBERG TERMINAL ───
WEALTH_ILLIQUIDS_MODELS_CATALOG = {
    "👑 Collezione Orologi & Caveau": {
        "title": "Collezione Orologi di Lusso, Caveau & Metalli Preziosi",
        "badge": "Horology • Perizie • Haute Horlogerie",
        "badge_color": "#6366f1",
        "category": "Caveau & Collezionismo",
        "desc": "Tracciamento pezzi da collezione, maison di prestigio, referenze, stato di conservazione e plusvalenze latenti da perizia periodica.",
    },
    "🏠 Immobili & Altri Asset Fisici": {
        "title": "Registro Immobili, Veicoli, Opere d'Arte & Nuovi Asset",
        "badge": "Real Estate • Tangibili • Inserimento",
        "badge_color": "#10b981",
        "category": "Asset Tangibili",
        "desc": "Censimento asset fisici, terreni, metalli preziosi, veicoli e collezionismo con modulo di perizia e registrazione diretta nel Caveau.",
    },
    "💼 Private Equity, VC & J-Curve": {
        "title": "Private Equity, Venture Capital & J-Curve Waterfall",
        "badge": "Illiquid Equity • J-Curve • MOIC/TVPI",
        "badge_color": "#f59e0b",
        "category": "Private Markets",
        "desc": "Monitoraggio partecipazioni non quotate, chiamate di capitale (capital calls), distribuzioni (DPI), TVPI/MOIC e XIRR di portafoglio.",
    },
    "🏛️ Private Debt & Direct Lending": {
        "title": "Private Debt, Direct Lending & Credit Waterfall Desk",
        "badge": "Direct Lending • Covenants • ICR/DSCR",
        "badge_color": "#38bdf8",
        "category": "Credito Privato",
        "desc": "Analisi cascata di pagamenti multi-tranche, monitoraggio covenants contrattuali (Net Debt/EBITDA, ICR, DSCR) e stress test EBITDA.",
    },
}

active_illiquid_tab = render_segmented_tabs(
    WEALTH_ILLIQUIDS_MODELS_CATALOG,
    key="wealth_illiquids_active_tab",
    select_label="Seleziona Modulo Asset Illiquidi:",
)

# ── 1. COLLEZIONE OROLOGI & CAVEAU ─────────────────────────
if active_illiquid_tab == "👑 Collezione Orologi & Caveau":
    # ── 1.A OROLOGI DI LUSSO ──────────────────────────────
    section("👑 Collezione Orologi di Lusso")

    df_watches = df_assets[df_assets["asset_category"] == "luxury_watches"] if not df_assets.empty else pd.DataFrame()
    if not df_watches.empty:
        for _, w in df_watches.iterrows():
            brand = str(w.get("brand_or_location") or "Maison").strip()
            model = str(w.get("model_or_specs") or "").strip()
            ref = str(w.get("reference_number") or "").strip()
            cond = str(w.get("condition_grade") or "Ottimo / Custodito").strip()
            acq_date = str(w.get("acquisition_date") or "").strip()
            if acq_date in ["None", "NaT", "nan"]:
                acq_date = ""

            p_cost = float(w.get("purchase_price", 0.0) or 0.0)
            p_val = float(w.get("current_market_value", 0.0) or 0.0)
            pnl = p_val - p_cost
            pnl_pct = (pnl / p_cost * 100.0) if p_cost > 0 else 0.0

            pnl_color = "#10b981" if pnl >= 0 else "#f85149"
            pnl_sign = "+" if pnl >= 0 else ""

            badges_html = f'<span style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:3px 8px; border-radius:4px; font-size:11px; color:#c9d1d9; margin-right:6px;">🏷️ {brand}</span>'
            if model and model.lower() != brand.lower():
                badges_html += f'<span style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:3px 8px; border-radius:4px; font-size:11px; color:#c9d1d9; margin-right:6px;">⚙️ {model}</span>'
            if ref and ref.lower() not in ["none", "n/d", "nan", ""]:
                badges_html += f'<span style="background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#818cf8; margin-right:6px;">🔖 Ref: {ref}</span>'
            badges_html += f'<span style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#34d399; margin-right:6px;">🟢 {cond}</span>'
            if acq_date:
                badges_html += f'<span style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:3px 8px; border-radius:4px; font-size:11px; color:#8b949e;">📅 {acq_date}</span>'

            st.markdown(
                f"""
            <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #6366f1; border-radius:10px; padding:16px 20px; margin-bottom:14px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        <div style="font-size:17px; font-weight:700; color:#ffffff; margin-bottom:6px;">⌚ {w['name']}</div>
                        <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">{badges_html}</div>
                    </div>
                    <div style="display:flex; gap:24px; align-items:center;">
                        <div style="text-align:right;">
                            <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Valore Attuale Stimato</div>
                            <div style="font-size:19px; font-weight:700; color:#ffffff;">{fmt_eur(p_val)}</div>
                            <div style="font-size:11px; color:#8b949e;">Acquisto: <span style="color:#c9d1d9;">{fmt_eur(p_cost)}</span></div>
                        </div>
                        <div style="text-align:right; min-width:110px;">
                            <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Plusvalenza Latente</div>
                            <div style="font-size:19px; font-weight:700; color:{pnl_color};">{pnl_sign}{fmt_eur(pnl)}</div>
                            <div style="font-size:11px; font-weight:600; color:{pnl_color};">{pnl_sign}{pnl_pct:.1f}%</div>
                        </div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Nessun orologio registrato. Aggiungi il tuo primo segnatempo dal modulo nella sezione 'Immobili & Altri Asset Fisici'.")

    # ── 1.B METALLI PREZIOSI & ORO FISICO NEL CAVEAU ──────────────
    df_metals = df_assets[df_assets["asset_category"] == "precious_metals"] if not df_assets.empty else pd.DataFrame()
    if not df_metals.empty:
        st.write("")
        section("🥇 Caveau Metalli Preziosi & Oro Fisico Dinamico")
        st.caption("Valutazione in tempo reale e allineamento retroattivo dell'oro fisico custodito nel caveau basata sulle quotazioni spot ufficiali COMEX / LBMA.")

        for _, m in df_metals.iterrows():
            metal_name = str(m.get("name") or "Metallo Prezioso").strip()
            material = str(m.get("brand_or_location") or "Oro").strip()
            specs_text = str(m.get("model_or_specs") or "").strip()
            ref_or_seal = str(m.get("reference_number") or "").strip()
            cond = str(m.get("condition_grade") or "Custodito nel Caveau").strip()
            acq_date = str(m.get("acquisition_date") or "").strip()
            if acq_date in ["None", "NaT", "nan"]:
                acq_date = ""

            eval_res = evaluate_metal_asset_dynamically(m)
            specs_info = parse_precious_metal_specs(m)
            carat_val = specs_info.get("carat", "18K")
            weight_g = specs_info.get("weight_grams", 0.0)
            fine_g = specs_info.get("fine_gold_grams", 0.0)
            spot_eur_g = eval_res.get("spot_price_eur_per_g", spot_18k)
            dyn_val = eval_res.get("dynamic_market_value", 0.0)
            static_val = eval_res.get("static_market_value", 0.0)
            delta_spot = eval_res.get("discrepancy_vs_static", 0.0)

            m_cost = float(m.get("purchase_price", 0.0) or 0.0)
            m_pnl = dyn_val - m_cost
            m_pnl_pct = (m_pnl / m_cost * 100.0) if m_cost > 0 else (100.0 if dyn_val > 0 else 0.0)

            pnl_color = "#10b981" if m_pnl >= 0 else "#f85149"
            pnl_sign = "+" if m_pnl >= 0 else ""

            badges_html = f'<span style="background:rgba(245,158,11,0.18); border:1px solid rgba(245,158,11,0.4); padding:3px 9px; border-radius:4px; font-size:11px; font-weight:800; color:#fbbf24; margin-right:6px;">🥇 Oro {carat_val} ({specs_info.get("purity_factor", 0.75)*1000:.0f}/1000)</span>'
            if weight_g > 0:
                badges_html += f'<span style="background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); padding:3px 9px; border-radius:4px; font-size:11px; font-weight:600; color:#f8fafc; margin-right:6px;">⚖️ Peso: {weight_g:.1f}g (Fino 24K: {fine_g:.2f}g)</span>'
            badges_html += f'<span style="background:rgba(56,189,248,0.15); border:1px solid rgba(56,189,248,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#38bdf8; margin-right:6px;">📈 Spot Live: € {spot_eur_g:,.2f}/g</span>'
            badges_html += f'<span style="background:rgba(16,185,129,0.15); border:1px solid rgba(16,185,129,0.3); padding:3px 8px; border-radius:4px; font-size:11px; color:#34d399; margin-right:6px;">🛡️ {cond}</span>'
            if acq_date:
                badges_html += f'<span style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:3px 8px; border-radius:4px; font-size:11px; color:#8b949e;">📅 {acq_date}</span>'

            cost_display = fmt_eur(m_cost) if m_cost > 0 else "€ 0,00 (Donazione / Oro)"
            gain_label = f"{pnl_sign}{m_pnl_pct:.1f}%" if m_cost > 0 else "+100.0% (Oro)"

            st.markdown(
                f'''
            <div style="background:rgba(22,27,34,0.88); border:1px solid rgba(245,158,11,0.3); border-left:4px solid #f59e0b; border-radius:10px; padding:18px 22px; margin-bottom:12px; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-size:18px; font-weight:800; color:#fbbf24; margin-bottom:6px;">🥇 {metal_name}</div>
                        <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">{badges_html}</div>
                    </div>
                    <div style="display:flex; gap:26px; align-items:center;">
                        <div style="text-align:right;">
                            <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Valore Live Spot Fixing</div>
                            <div style="font-size:20px; font-weight:800; color:#ffffff;">{fmt_eur(dyn_val)}</div>
                            <div style="font-size:11px; color:#8b949e;">Perizia a Bilancio: <span style="color:#fbbf24; font-weight:600;">{fmt_eur(static_val)}</span></div>
                        </div>
                        <div style="text-align:right; min-width:115px;">
                            <div style="font-size:11px; font-weight:600; color:#8b949e; text-transform:uppercase; letter-spacing:0.5px;">Plusvalenza Latente</div>
                            <div style="font-size:20px; font-weight:800; color:{pnl_color};">{pnl_sign}{fmt_eur(m_pnl)}</div>
                            <div style="font-size:11px; font-weight:600; color:{pnl_color};">{gain_label}</div>
                        </div>
                    </div>
                </div>
            </div>
            ''',
                unsafe_allow_html=True,
            )

            # Azione di allineamento del valore di bilancio al fixing live se c'è discrepanza
            if abs(delta_spot) >= 1.0:
                align_c1, align_c2 = st.columns([3, 1])
                with align_c1:
                    st.caption(f"💡 Il fixing live di mercato differisce dalla perizia registrata di {fmt_eur(delta_spot)} ({dyn_val:,.2f} € vs {static_val:,.2f} €). Puoi sincronizzare il valore di bilancio.")
                with align_c2:
                    asset_id_val = m.get("asset_id", m.get("id"))
                    btn_key = f"btn_align_gold_spot_{asset_id_val}"
                    if st.button("🔄 Allinea a Spot Live", key=btn_key, use_container_width=True, help="Aggiorna il valore peritale nel database al fixing live odierno"):
                        asset_dict = m.to_dict() if isinstance(m, pd.Series) else dict(m)
                        asset_dict["current_market_value"] = dyn_val
                        asset_dict["portfolio_id"] = current_pid
                        save_physical_asset(engine, asset_dict)
                        st.toast(f"✅ Valore di bilancio allineato al fixing live: {fmt_eur(dyn_val)}!", icon="🥇")
                        st.rerun()

        # ── GRAFICO INTERATTIVO EVOLUZIONE STORICA ORO NEL CAVEAU ───
        st.write("")
        st.markdown("##### 📈 Evoluzione & Rivalutazione Storica dell'Oro Fisico nel Tempo")
        st.caption("Visualizza l'andamento del controvalore del tuo oro nel caveau nel corso degli anni (1Y, 3Y, 5Y, 10Y) basato sulle quotazioni ufficiali spot giornaliere EUR/g.")

        gold_tf_cols = st.columns([2, 2])
        with gold_tf_cols[0]:
            sel_gold_tf = st.segmented_control(
                "Orizzonte Storico:",
                options=["1 Anno (12M)", "3 Anni (36M)", "5 Anni (60M)", "10 Anni (120M)"],
                default="3 Anni (36M)",
                key="gold_hist_tf_select",
            )
        tf_month_map = {
            "1 Anno (12M)": 12,
            "3 Anni (36M)": 36,
            "5 Anni (60M)": 60,
            "10 Anni (120M)": 120,
        }
        target_months = tf_month_map.get(sel_gold_tf, 36)

        df_gold_traj = compute_gold_portfolio_historical_trajectory(df_assets, timeframe_months=target_months)
        if not df_gold_traj.empty:
            fig_gold = go.Figure()
            # Area valore portafoglio
            fig_gold.add_trace(
                go.Scatter(
                    x=df_gold_traj.index,
                    y=df_gold_traj["Total_Gold_Value_EUR"],
                    mode="lines",
                    name="Controvalore Oro nel Caveau (€)",
                    line=dict(color="#f59e0b", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(245, 158, 11, 0.12)",
                    hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Controvalore: <b>€ %{y:,.2f}</b><extra></extra>",
                )
            )
            # Linea quotazione spot 18K al grammo (asse secondario)
            fig_gold.add_trace(
                go.Scatter(
                    x=df_gold_traj.index,
                    y=df_gold_traj["Spot_18K_EUR_g"],
                    mode="lines",
                    name="Quotazione Spot 18K (€/g)",
                    line=dict(color="#38bdf8", width=1.5, dash="dot"),
                    yaxis="y2",
                    hovertemplate="Spot 18K: <b>€ %{y:,.2f}/g</b><extra></extra>",
                )
            )

            fig_gold.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(22,27,34,0.4)",
                height=380,
                margin=dict(l=10, r=10, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickformat="%b %Y"),
                yaxis=dict(
                    title="Valore Portafoglio (€)",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.06)",
                    tickprefix="€ ",
                ),
                yaxis2=dict(
                    title="Spot 18K (€/g)",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickprefix="€ ",
                ),
            )
            st.plotly_chart(fig_gold, use_container_width=True)

            # Metriche di performance oro su orizzonte
            first_val = float(df_gold_traj["Total_Gold_Value_EUR"].iloc[0])
            last_val = float(df_gold_traj["Total_Gold_Value_EUR"].iloc[-1])
            growth_val = last_val - first_val
            growth_pct = ((growth_val / first_val) * 100.0) if first_val > 0 else 0.0
            min_spot = float(df_gold_traj["Spot_18K_EUR_g"].min())
            max_spot = float(df_gold_traj["Spot_18K_EUR_g"].max())

            gk1, gk2, gk3, gk4 = st.columns(4)
            with gk1:
                metric_card("Rivalutazione Periodo", fmt_eur(growth_val), delta=f"{growth_pct:+.1f}% su {sel_gold_tf}")
            with gk2:
                metric_card("Minimo Spot 18K", f"€ {min_spot:,.2f}/g", delta="Nel periodo selezionato", delta_color="normal")
            with gk3:
                metric_card("Massimo Spot 18K", f"€ {max_spot:,.2f}/g", delta="Picco storico nel periodo", delta_color="normal")
            with gk4:
                tot_fine_g = sum(parse_precious_metal_specs(r)["fine_gold_grams"] for _, r in df_metals.iterrows())
                metric_card("Oro Fino 24K Totale", f"{tot_fine_g:.2f}g", delta=f"{tot_fine_g/31.1034768:.3f} oz troy pure", delta_color="normal")

        # ── 1.C TRACKER MONETE BULLION & FISCALITÀ CESSIONE ORO ────
        st.write("")
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            with st.expander("🪙 Tracker Monete da Investimento & Bullion", expanded=False):
                st.caption("Quotazione istantanea con peso fino e spread numismatico di mercato rispetto al fixing LBMA spot.")
                sel_coin_k = st.selectbox(
                    "Seleziona Moneta o Lingotto:",
                    options=list(BULLION_COIN_CATALOG.keys()),
                    format_func=lambda k: f"{BULLION_COIN_CATALOG[k]['icon']} {BULLION_COIN_CATALOG[k]['name']}",
                    key="select_bullion_coin_p15",
                )
                coin_qty = st.number_input("Quantità (Pezzi):", min_value=1, max_value=1000, value=1, step=1, key="num_bullion_coin_qty")
                eval_coin = evaluate_bullion_coin(sel_coin_k, quantity=coin_qty, live_spot_24k_eur_g=spot_24k)

                c_info1, c_info2 = st.columns(2)
                with c_info1:
                    st.markdown(f"**Paese:** {eval_coin['country']}")
                    st.markdown(f"**Titolo:** {eval_coin['fineness']*1000:.1f}/1000")
                    st.markdown(f"**Fino Totale:** {eval_coin['fine_gold_total_g']:.3f}g")
                with c_info2:
                    st.markdown(f"**Melt Value Unitario:** {fmt_eur(eval_coin['melt_value_unit_eur'])}")
                    st.markdown(f"**Premio Bullion:** +{eval_coin['premium_pct']:.1f}%")
                    st.markdown(f"**Prezzo Mercato Unitario:** {fmt_eur(eval_coin['market_price_unit_eur'])}")

                st.markdown(
                    f'''
                    <div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:8px; padding:10px 14px; margin-top:8px;">
                        <div style="font-size:11px; color:#94a3b8; text-transform:uppercase;">Valore Totale di Mercato ({coin_qty} pz)</div>
                        <div style="font-size:22px; font-weight:800; color:#fbbf24;">{fmt_eur(eval_coin['total_market_price_eur'])}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

                if st.button("➕ Aggiungi al Caveau Personale", key="btn_add_bullion_to_caveau", use_container_width=True):
                    new_asset = {
                        "portfolio_id": current_pid,
                        "asset_category": "precious_metals",
                        "name": f"{eval_coin['coin_name']} ({coin_qty} pz)",
                        "brand_or_location": f"Oro ({eval_coin['fineness']*1000:.0f}/1000)",
                        "model_or_specs": f"{eval_coin['gross_weight_total_g']:.2f}g (Fino 24K: {eval_coin['fine_gold_total_g']:.2f}g)",
                        "purchase_price": eval_coin["total_market_price_eur"],
                        "current_market_value": eval_coin["total_market_price_eur"],
                        "condition_grade": "Fior di Conio / Custodito",
                        "notes": f"Acquisto bullion coin {eval_coin['coin_name']} con premio +{eval_coin['premium_pct']:.1f}%",
                    }
                    save_physical_asset(engine, new_asset)
                    st.toast(f"✅ {eval_coin['coin_name']} aggiunto al Caveau!", icon="🥇")
                    st.rerun()

        with b_c2:
            with st.expander("⚖️ Simulatore Fiscale Cessione Oro (L. 7/2000 & L. 213/2023)", expanded=False):
                st.caption("Calcolo delle imposte sulla vendita di oro da investimento in Italia in base alla presenza di documentazione d'acquisto.")
                
                # Selezione asset presente o importo personalizzato
                gold_names = [r["name"] for _, r in df_metals.iterrows()]
                sel_gold_tax_src = st.selectbox("Asset di Riferimento:", ["Inserimento Manuale"] + gold_names, key="sel_gold_tax_src")
                
                def_sale_val = float(df_metals.iloc[0]["current_market_value"]) if not df_metals.empty else 2000.0
                def_cost_val = float(df_metals.iloc[0]["purchase_price"]) if not df_metals.empty else 1200.0
                if sel_gold_tax_src != "Inserimento Manuale":
                    match_row = df_metals[df_metals["name"] == sel_gold_tax_src].iloc[0]
                    def_sale_val = float(match_row["current_market_value"])
                    def_cost_val = float(match_row["purchase_price"])

                tx_sale_px = st.number_input("Prezzo di Vendita Stimato (€):", min_value=0.0, value=def_sale_val, step=100.0, key="inp_gold_tax_sale_px")
                has_doc = st.toggle("Possiedi Fattura / Documento d'Acquisto?", value=def_cost_val > 0.0, key="tgl_gold_has_doc")
                tx_cost_px = 0.0
                if has_doc:
                    tx_cost_px = st.number_input("Costo Storico d'Acquisto Documentato (€):", min_value=0.0, value=def_cost_val, step=100.0, key="inp_gold_tax_cost_px")

                tax_res = compute_gold_sale_tax_impact(sale_price_eur=tx_sale_px, purchase_price_eur=tx_cost_px, has_purchase_document=has_doc)

                t_c1, t_c2, t_c3, t_c4 = st.columns(4)
                with t_c1:
                    metric_card("Base Imponibile Fiscale", fmt_eur(tax_res["taxable_base_eur"]))
                with t_c2:
                    metric_card("Imposta 26% Dovuta", fmt_eur(tax_res["tax_due_eur"]), delta="Aliquota 26%", delta_color="inverse")
                with t_c3:
                    metric_card("Incasso Netto Effettivo", fmt_eur(tax_res["net_proceeds_eur"]))
                with t_c4:
                    metric_card("Aliquota Effettiva", f"{tax_res['effective_tax_pct']:.1f}%")

                if not has_doc:
                    st.warning(
                        f"⚠️ **Riforma Legge di Bilancio 2024 (L. 213/2023):** Senza fattura, l'imposta del 26% si applica "
                        f"sull'**INTERO incasso** ({fmt_eur(tx_sale_px)}), costandoti **{fmt_eur(tax_res['delta_vs_pre_2024_eur'])} in più** "
                        f"rispetto alla vecchia legge pre-2024 (che tassava solo il 25% forfettario). "
                        f"Valuta una perizia giurata di stima per determinare il valore d'acquisto fiscale."
                    )
                else:
                    if tax_res["tax_loss_generated_eur"] > 0:
                        st.info(f"ℹ️ La vendita genera una **minusvalenza di {fmt_eur(tax_res['tax_loss_generated_eur'])}** compensabile nel Quadro RT entro 4 anni.")
                    else:
                        st.success(f"✅ Con fattura l'imposta del 26% si applica unicamente sul capital gain reale ({fmt_eur(tax_res['taxable_base_eur'])}).")

# ── 2. IMMOBILI & ALTRI ASSET FISICI ───────────────────────
elif active_illiquid_tab == "🏠 Immobili & Altri Asset Fisici":
    section("🏠 Immobili, Metalli Preziosi & Altro")
    df_other = df_assets[df_assets["asset_category"] != "luxury_watches"] if not df_assets.empty else pd.DataFrame()
    if not df_other.empty:
        cat_map = {
            "precious_metals": "🥇 Metalli Preziosi (Oro/Argento)",
            "real_estate": "🏠 Immobili / Terreni",
            "collectibles_art": "🎨 Collezionismo & Arte",
            "vehicles": "🚗 Veicoli & Auto",
            "other": "📦 Altro Caveau",
        }

        df_other_disp = df_other.copy()
        df_other_disp["Categoria"] = df_other_disp["asset_category"].map(lambda c: cat_map.get(c, c.replace("_", " ").title()))
        df_other_disp["Prezzo Acquisto"] = df_other_disp["purchase_price"].apply(lambda v: fmt_eur(v) if float(v or 0.0) > 0 else "€ 0,00 (Donazione / Oro)")
        df_other_disp["Valore Attuale"] = df_other_disp["current_market_value"].apply(lambda v: fmt_eur(v))
        df_other_disp["Plusvalenza"] = df_other_disp["unrealized_pnl"].apply(lambda v: f"{'+' if v >= 0 else ''}{fmt_eur(v)}")
        df_other_disp["Rivalutazione"] = df_other_disp.apply(
            lambda r: "+100.0% (Oro / Donazione)"
            if float(r.get("purchase_price", 0.0) or 0.0) == 0.0 and float(r.get("current_market_value", 0.0) or 0.0) > 0
            else (f"{'+' if r['unrealized_pnl_pct'] >= 0 else ''}{r['unrealized_pnl_pct']:.1f}%" if pd.notna(r.get("unrealized_pnl_pct")) else "N/D"),
            axis=1,
        )

        render_table_with_export(
            df_other_disp[["name", "Categoria", "brand_or_location", "model_or_specs", "Prezzo Acquisto", "Valore Attuale", "Plusvalenza", "Rivalutazione"]].rename(columns={
                "name": "Nome Asset",
                "brand_or_location": "Materiale / Maison",
                "model_or_specs": "Dettagli / Specifiche",
            }),
            table_title="Asset Fisici, Orologi & Metalli Preziosi",
            file_prefix="asset_fisici_caveau",
            key_suffix="p15_physical_assets",
        )
    else:
        st.caption("Nessun immobile o metallo prezioso registrato.")

    st.write("")
    # ── FORM AGGIUNGI / MODIFICA ASSET FISICO ────────────────────
    with st.expander("➕ Aggiungi Nuovo Orologio, Immobile o Asset Fisico al Caveau", expanded=df_other.empty):
        with st.form("form_add_physical_asset"):
            pa1, pa2, pa3 = st.columns(3)
            with pa1:
                pa_name = st.text_input("Nome Identificativo *", placeholder="es. Rolex GMT-Master II Batman")
                pa_cat = st.selectbox("Categoria Asset *", [
                    ("luxury_watches", "Orologio di Lusso"),
                    ("real_estate", "Immobile / Terreno"),
                    ("precious_metals", "Metalli Preziosi (Oro/Argento)"),
                    ("collectibles_art", "Collezionismo / Arte / Auto"),
                    ("vehicles", "Veicoli (Auto/Moto)"),
                    ("other", "Altro"),
                ], format_func=lambda x: x[1])
                pa_brand = st.text_input("Maison / Brand o Città", placeholder="es. Rolex, Patek, Milano...")
            with pa2:
                pa_model = st.text_input("Modello / Specifiche", placeholder="es. GMT-Master II Jubilee")
                pa_ref = st.text_input("Numero Referenza / Catasto", placeholder="es. 126710BLNR")
                pa_cond = st.text_input("Condizione & Set", placeholder="es. Mai indossato / Full Set 2024")
            with pa3:
                pa_cost = st.number_input("Prezzo d'Acquisto (€) *", min_value=0.0, value=10000.0, step=500.0)
                pa_val = st.number_input("Valore di Mercato Attuale (€) *", min_value=0.0, value=15000.0, step=500.0)
                pa_date = st.date_input("Data di Acquisto", value=date.today())
                pa_notes = st.text_input("Note", placeholder="Garanzia, revisione, provenienza...")

            btn_save_pa = st.form_submit_button("💾 Salva nel Caveau", use_container_width=True)
            if btn_save_pa:
                if pa_name:
                    save_physical_asset(engine, {
                        "portfolio_id": current_pid,
                        "name": pa_name,
                        "asset_category": pa_cat[0],
                        "brand_or_location": pa_brand,
                        "model_or_specs": pa_model,
                        "reference_number": pa_ref,
                        "condition_grade": pa_cond,
                        "purchase_price": pa_cost,
                        "current_market_value": pa_val,
                        "acquisition_date": pa_date,
                        "notes": pa_notes,
                    })

                    st.success(f"Asset '{pa_name}' salvato con successo!")
                    st.rerun()
                else:
                    st.error("Inserisci il Nome Identificativo dell'asset.")

# ── 3. PRIVATE EQUITY, VC & J-CURVE ────────────────────────
elif active_illiquid_tab == "💼 Private Equity, VC & J-Curve":
    section("💼 Private Equity, Venture Capital & J-Curve Waterfall (Simulazione)")
    st.caption("Monitoraggio delle partecipazioni societarie illiquide, chiamate di capitale (Capital Calls), distribuzioni (DPI) e modellazione stocastica della J-Curve di rendimento atteso.")

    pe_res = compute_private_equity_deal_metrics()

    pe_c1, pe_c2, pe_c3, pe_c4 = st.columns(4)
    with pe_c1:
        metric_card("Capitale Impegnato", fmt_eur(pe_res["total_committed_eur"]), delta=f"{pe_res['deals_count']} Deal Attivi", delta_color="normal")
    with pe_c2:
        metric_card("Capitale Versato (Called)", fmt_eur(pe_res["total_called_eur"]), delta=f"Unfunded: {fmt_eur(pe_res['unfunded_commitment_eur'])}", delta_color="normal")
    with pe_c3:
        metric_card("MOIC / TVPI Multiplo", f"{pe_res['portfolio_moic_tvpi']:.2f}x", delta=f"DPI: {pe_res['portfolio_dpi']:.2f}x | RVPI: {pe_res['portfolio_rvpi']:.2f}x", delta_color="normal")
    with pe_c4:
        metric_card("XIRR Netto di Portafoglio", f"{pe_res['portfolio_xirr_pct']:+.1f}%", delta="Rendimento Attualizzato Flussi", delta_color="normal" if pe_res["portfolio_xirr_pct"] >= 0 else "inverse")

    st.write("")

    c_pe_left, c_pe_right = st.columns([3, 2])
    with c_pe_left:
        render_table_with_export(
            pe_res["deals_df"][["name", "asset_class", "vintage_year", "called_capital_eur", "distributions_received_eur", "current_nav_estimated_eur", "moic_multiple", "irr_net_pct", "status"]].rename(columns={
                "name": "Nome Deal / Fondo",
                "asset_class": "Tipologia",
                "vintage_year": "Vintage",
                "called_capital_eur": "Versato (€)",
                "distributions_received_eur": "Distribuzioni (€)",
                "current_nav_estimated_eur": "NAV Stimato (€)",
                "moic_multiple": "MOIC (x)",
                "irr_net_pct": "XIRR (%)",
                "status": "Stato",
            }),
            table_title="Registro Partecipazioni & Club Deal",
            file_prefix="pe_club_deals",
            key_suffix="p15_pe_deals",
        )

    with c_pe_right:
        st.markdown("##### 📈 Modellazione J-Curve di Portafoglio")
        df_j = pe_res["j_curve_df"]
        fig_j = go.Figure()
        fig_j.add_trace(go.Scatter(
            x=df_j["Anno di Vita Deal"],
            y=df_j["Valore Netto Portafoglio PE (€)"],
            mode="lines+markers",
            name="Valore Netto (J-Curve)",
            line=dict(color="#6366f1", width=3),
        ))
        fig_j.add_trace(go.Scatter(
            x=df_j["Anno di Vita Deal"],
            y=df_j["Capitale Versato Cumulativo (€)"],
            mode="lines",
            name="Capitale Versato Base",
            line=dict(color="#94a3b8", width=1.5, dash="dash"),
        ))
        fig_j.update_layout(
            xaxis_title="Anno di Vita del Deal",
            yaxis_title="Valore (€)",
            height=280,
            margin=dict(t=15, l=10, r=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        apply_chart_theme(fig_j, portal_mode="wealth")
        st.plotly_chart(fig_j, use_container_width=True, config={"displayModeBar": False})

# ── 4. PRIVATE DEBT & DIRECT LENDING ───────────────────────
elif active_illiquid_tab == "🏛️ Private Debt & Direct Lending":
    section("🏛️ Private Debt, Direct Lending & Credit Waterfall Desk")
    st.caption("Analisi della cascata di pagamenti multi-tranche per investimenti in credito privato, monitoraggio contrattuale dei covenants (Leva Net Debt/EBITDA, ICR, DSCR) e capitalizzazione interessi PIK.")

    from core.private_debt_engine import compute_private_debt_waterfall_and_covenants, get_standard_private_debt_deals

    deals_list = get_standard_private_debt_deals()
    deal_names = [d["borrower_name"] for d in deals_list]

    col_pd_sel1, col_pd_sel2 = st.columns([2, 1])
    with col_pd_sel1:
        sel_deal_name = st.selectbox("Seleziona Struttura Private Debt:", deal_names, index=0)
    with col_pd_sel2:
        stress_ebitda_in = st.slider("Stress Test EBITDA Borrower (%):", -40.0, 10.0, 0.0, 5.0)

    chosen_deal = next(d for d in deals_list if d["borrower_name"] == sel_deal_name)
    pd_analysis = compute_private_debt_waterfall_and_covenants(deal_data=chosen_deal, ebitda_stress_pct=stress_ebitda_in)
    cr_m = pd_analysis["credit_metrics"]

    pdk1, pdk2, pdk3, pdk4 = st.columns(4)
    with pdk1:
        metric_card("Stato Covenants", pd_analysis["covenant_status"], delta=f"Leva {cr_m['leverage_net_debt_ebitda']:.2f}x vs {cr_m['max_leverage_allowed']:.1f}x", delta_color="normal" if pd_analysis["is_covenant_compliant"] else "inverse")
    with pdk2:
        metric_card("Facility Totale Deal", fmt_eur(pd_analysis["total_facility_eur"]), delta=f"Settore: {pd_analysis['sector']}", delta_color="normal")
    with pdk3:
        metric_card("Rendimento All-In Medio", f"{pd_analysis['weighted_all_in_yield_pct']:.2f}%", delta="Cash + PIK", delta_color="normal")
    with pdk4:
        metric_card("Copertura Interessi (ICR)", f"{cr_m['interest_coverage_ratio_icr']:.2f}x", delta=f"Min Richiesto: {cr_m['min_icr_allowed']:.2f}x", delta_color="normal" if not cr_m["icr_breached"] else "inverse")

    st.write("")

    col_pd_l, col_pd_r = st.columns([3, 2])
    with col_pd_l:
        render_table_with_export(
            pd_analysis["tranches_df"][["tranche_name", "seniority", "notional_eur", "cash_coupon_pct", "pik_coupon_pct", "all_in_yield_pct", "attachment_leverage", "detachment_leverage"]].rename(columns={
                "tranche_name": "Tranche di Debito",
                "seniority": "Seniority",
                "notional_eur": "Notionale (€)",
                "cash_coupon_pct": "Cedola Cash (%)",
                "pik_coupon_pct": "Cedola PIK (%)",
                "all_in_yield_pct": "Rendimento Totale (%)",
                "attachment_leverage": "Attach Leverage",
                "detachment_leverage": "Detach Leverage",
            }),
            table_title="Scomposizione Tranche & Struttura del Capitale",
            file_prefix="private_debt_tranches",
            key_suffix="p15_pd_tranches",
        )

    with col_pd_r:
        st.markdown("##### 🛡️ Monitoraggio Covenants & DSCR")
        st.markdown(
            f"""
        <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(99, 102, 241, 0.25); border-left: 4px solid #6366f1; border-radius: 10px; padding: 14px 18px;">
            <b style="color: #6366f1; font-size: 14px;">Quadro di Solidità Creditizia:</b><br>
            <span style="font-size: 13px; color: #cbd5e1; line-height: 1.6;">
            • <b>EBITDA Stressed:</b> € {pd_analysis['stressed_ebitda_eur']:,.2f}<br>
            • <b>Interessi Cash Annui:</b> € {pd_analysis['total_cash_interest_eur']:,.2f}<br>
            • <b>Interessi PIK Capitalizzati:</b> € {pd_analysis['total_pik_capitalized_eur']:,.2f}<br>
            • <b>Debt Service Coverage (DSCR):</b> {cr_m['dscr_ratio']:.2f}x (Soglia minima contrattuale: {cr_m['min_dscr_allowed']:.2f}x)<br>
            <b style="color: {'#10b981' if pd_analysis['is_covenant_compliant'] else '#ef4444'};">Esito Monitoraggio: {pd_analysis['covenant_status']}</b>
            </span>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ── SR 11-7 AUDIT TRAIL & MODEL VALIDATION ─────────────────
render_sr117_audit_drawer(
    engine_name="ARGUS Physical Assets, Caveau & Private Markets Engine",
    latex_formulas=[
        r"V_{\text{Caveau}} = \sum_{i \in \text{Watches}} P_i^{\text{mkt}} + \sum_{j \in \text{Metals}} (\text{Weight}_j \times \text{Spot}_j) + \sum_{k \in \text{Tangibles}} V_k",
        r"\Delta_{\text{latente}} = V_{\text{Caveau}} - \sum C_{\text{acquisto}}, \quad \text{MOIC} = \frac{\text{DPI} + \text{RVPI}}{\text{Paid-In Capital}}",
    ],
    inputs_dict={"portfolio_id": current_pid, "assets_count": len(df_assets) if not df_assets.empty else 0},
    outputs_dict={
        "total_market_value_eur": total_market_val,
        "total_cost_eur": total_cost,
        "unrealized_gain_eur": unrealized_gain,
        "luxury_watches_count": len(df_assets[df_assets["asset_category"] == "luxury_watches"]) if not df_assets.empty else 0,
        "precious_metals_count": len(df_assets[df_assets["asset_category"] == "precious_metals"]) if not df_assets.empty else 0,
    },
    regulatory_refs=["Fed SR 11-7", "IVSC International Valuation Standards", "Basel Committee BCBS-352", "IAS 40 / IFRS 13"],
)
