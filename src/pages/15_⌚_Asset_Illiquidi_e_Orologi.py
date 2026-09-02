# ============================================================
# src/pages/15_⌚_Asset_Illiquidi_e_Orologi.py
# ARGUS Wealth Management — Luxury Watches, Real Estate & Collectibles
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date
import importlib
import core.ui_utils
importlib.reload(core.ui_utils)

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
from core.wealth import (
    get_physical_assets,
    save_physical_asset,
    get_wealth_portfolios,
    compute_consolidated_net_worth,
    compute_private_equity_deal_metrics
)


st.set_page_config(page_title="Asset Illiquidi & Orologi | ARGUS Wealth", page_icon="⌚", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "investment_risk_bi")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    st.title("⌚ ARGUS Wealth — Caveau & Asset Fisici")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per visualizzare gli asset fisici, orologi e metalli preziosi in custodia.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="phys_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p15")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

head_c1, head_c2 = st.columns([3.5, 1.5])
with head_c1:
    st.title("⌚ ARGUS Wealth — Caveau & Asset Fisici")

    st.caption("Tracciamento, valutazione e rivalutazione di Orologi di Lusso, Immobili, Metalli Preziosi e Collezionismo.")

with head_c2:
    st.write("")
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="phys_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()

df_assets = get_physical_assets(engine, portfolio_id=current_pid)



# Calcolo metriche aggregate
total_market_val = float(df_assets["current_market_value"].sum()) if not df_assets.empty else 0.0
total_cost = float(df_assets["purchase_price"].sum()) if not df_assets.empty else 0.0
unrealized_gain = total_market_val - total_cost
gain_pct = (unrealized_gain / total_cost * 100.0) if total_cost > 0 else 0.0

# ── TOP KPI ROW ─────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Valore Caveau & Fisico", fmt_eur(total_market_val), delta="Valutazione di Mercato Attuale", delta_color="normal")
with c2:
    metric_card("Capitale Investito", fmt_eur(total_cost), delta="Costo Storico d'Acquisto", delta_color="normal")
with c3:
    metric_card("Plusvalenza Latente", fmt_eur(unrealized_gain), delta=f"{gain_pct:+.1f}% Rivalutazione", delta_color="normal" if unrealized_gain >= 0 else "inverse")
with c4:
    watches_cnt = len(df_assets[df_assets["asset_category"] == "luxury_watches"]) if not df_assets.empty else 0
    cnt_label = f"{watches_cnt} Pezzo" if watches_cnt == 1 else f"{watches_cnt} Pezzi"
    metric_card("Orologi in Collezione", cnt_label, delta="Orologeria di Lusso", delta_color="normal")

st.divider()

# ── SEZIONE OROLOGI DA COLLEZIONE ────────────────────────────
section("👑 Collezione Orologi di Lusso")

df_watches = df_assets[df_assets["asset_category"] == "luxury_watches"] if not df_assets.empty else pd.DataFrame()
if not df_watches.empty:
    for _, w in df_watches.iterrows():
        brand = str(w.get("brand_or_location") or "Maison").strip()
        model = str(w.get("model_or_specs") or "").strip()
        ref = str(w.get("reference_number") or "").strip()
        cond = str(w.get("condition_grade") or "Ottimo / Custodito").strip()
        acq_date = str(w.get("acquisition_date") or "").strip()
        if acq_date in ["None", "NaT", "nan"]: acq_date = ""

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

        st.markdown(f"""
        <div style="background:rgba(22,27,34,0.85); border:1px solid rgba(255,255,255,0.08); border-left:4px solid #6366f1; border-radius:10px; padding:16px 20px; margin-bottom:14px;">
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
        """, unsafe_allow_html=True)
else:
    st.info("Nessun orologio registrato. Aggiungi il tuo primo segnatempo dal modulo sottostante.")

# ── SEZIONE ALTRI ASSET (IMMOBILI, METALLI) ──────────────────
section("🏠 Immobili, Metalli Preziosi & Altro")
df_other = df_assets[df_assets["asset_category"] != "luxury_watches"] if not df_assets.empty else pd.DataFrame()
if not df_other.empty:
    cat_map = {
        "precious_metals": "🥇 Metalli Preziosi (Oro/Argento)",
        "real_estate": "🏠 Immobili / Terreni",
        "collectibles_art": "🎨 Collezionismo & Arte",
        "vehicles": "🚗 Veicoli & Auto",
        "other": "📦 Altro Caveau"
    }
    
    df_other_disp = df_other.copy()
    df_other_disp["Categoria"] = df_other_disp["asset_category"].map(lambda c: cat_map.get(c, c.replace("_", " ").title()))
    df_other_disp["Prezzo Acquisto"] = df_other_disp["purchase_price"].apply(lambda v: fmt_eur(v) if float(v or 0.0) > 0 else "€ 0,00 (Donazione / Oro)")
    df_other_disp["Valore Attuale"] = df_other_disp["current_market_value"].apply(lambda v: fmt_eur(v))
    df_other_disp["Plusvalenza"] = df_other_disp["unrealized_pnl"].apply(lambda v: f"{'+' if v >= 0 else ''}{fmt_eur(v)}")
    df_other_disp["Rivalutazione"] = df_other_disp.apply(
        lambda r: "+100.0% (Oro / Donazione)" if float(r.get("purchase_price", 0.0) or 0.0) == 0.0 and float(r.get("current_market_value", 0.0) or 0.0) > 0
        else (f"{'+' if r['unrealized_pnl_pct'] >= 0 else ''}{r['unrealized_pnl_pct']:.1f}%" if pd.notna(r.get("unrealized_pnl_pct")) else "N/D"),
        axis=1
    )
    
    st.dataframe(
        df_other_disp[["name", "Categoria", "brand_or_location", "model_or_specs", "Prezzo Acquisto", "Valore Attuale", "Plusvalenza", "Rivalutazione"]].rename(columns={
            "name": "Nome Asset",
            "brand_or_location": "Materiale / Maison",
            "model_or_specs": "Dettagli / Specifiche"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.caption("Nessun immobile o metallo prezioso registrato.")


# ── FORM AGGIUNGI / MODIFICA ASSET FISICO ────────────────────
with st.expander("➕ Aggiungi Nuovo Orologio, Immobile o Asset Fisico"):
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
                ("other", "Altro")
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
                    "notes": pa_notes
                })

                st.success(f"Asset '{pa_name}' salvato con successo!")
                st.rerun()
            else:
                st.error("Inserisci il Nome Identificativo dell'asset.")

st.divider()

# ── SEZIONE PRIVATE EQUITY, VENTURE CAPITAL & J-CURVE ────────
section("💼 Private Equity, Venture Capital & J-Curve Waterfall")
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
    st.markdown("##### 🏛️ Registro Partecipazioni & Club Deal")
    st.dataframe(
        pe_res["deals_df"][["name", "asset_class", "vintage_year", "called_capital_eur", "distributions_received_eur", "current_nav_estimated_eur", "moic_multiple", "irr_net_pct", "status"]].rename(columns={
            "name": "Nome Deal / Fondo",
            "asset_class": "Tipologia",
            "vintage_year": "Vintage",
            "called_capital_eur": "Versato (€)",
            "distributions_received_eur": "Distribuzioni (€)",
            "current_nav_estimated_eur": "NAV Stimato (€)",
            "moic_multiple": "MOIC (x)",
            "irr_net_pct": "XIRR (%)",
            "status": "Stato"
        }),
        use_container_width=True,
        hide_index=True
    )

with c_pe_right:
    st.markdown("##### 📈 Modellazione J-Curve di Portafoglio")
    import plotly.graph_objects as go
    df_j = pe_res["j_curve_df"]
    fig_j = go.Figure()
    fig_j.add_trace(go.Scatter(
        x=df_j["Anno di Vita Deal"],
        y=df_j["Valore Netto Portafoglio PE (€)"],
        mode="lines+markers",
        name="Valore Netto (J-Curve)",
        line=dict(color="#6366f1", width=3)
    ))
    fig_j.add_trace(go.Scatter(
        x=df_j["Anno di Vita Deal"],
        y=df_j["Capitale Versato Cumulativo (€)"],
        mode="lines",
        name="Capitale Versato Base",
        line=dict(color="#94a3b8", width=1.5, dash="dash")
    ))
    fig_j.update_layout(
        xaxis_title="Anno di Vita del Deal",
        yaxis_title="Valore (€)",
        height=280,
        margin=dict(t=15, l=10, r=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    apply_plotly_theme(fig_j)
    st.plotly_chart(fig_j, use_container_width=True, config={'displayModeBar': False})
