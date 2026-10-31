# ============================================================
# 19_🏡_Immobili_e_Mutui.py
# ARGUS Wealth — Immobili, Piani di Ammortamento Mutuo & Buy vs Rent
# ============================================================

import importlib
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import core.ui_utils
import core.wealth
import core.wealth.wealth_db
import core.wealth.wealth_engine

importlib.reload(core.ui_utils)
importlib.reload(core.wealth.wealth_db)
importlib.reload(core.wealth.wealth_engine)
importlib.reload(core.wealth)

from core.fetcher import get_engine
from core.sidebar import render_sidebar
from core.ui_lifecycle import teardown_view_state
from core.ui_utils import (
    apply_plotly_theme,
    ensure_portfolio_loaded,
    fmt_eur,
    fmt_pct,
    inject_custom_css,
    metric_card,
    render_institutional_telemetry_ribbon,
    render_page_header,
    render_segmented_tabs,
    render_sr117_audit_drawer,
    render_table_with_export,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_wealth_telemetry_ribbon,
    resolve_active_subtab,
    section,
)
from core.wealth.personal_balance_sheet import get_physical_assets
from core.wealth.wealth_db import get_wealth_portfolios, init_wealth_db
from core.wealth.wealth_engine import (
    compute_buy_vs_rent_comparison,
    compute_consolidated_net_worth,
    compute_mortgage_amortization,
    compute_real_estate_net_equity_and_ltv,
    compute_real_estate_roi,
)

st.set_page_config(page_title="Immobili & Mutui | ARGUS Wealth", page_icon="🏡", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_name = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
st.session_state.wealth_db_name = db_name
st.session_state.db_name = db_name
offline_mode = bool(st.session_state.get("offline_mode", False))
db_port = int(st.session_state.get("db_port", 3306))

engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)
init_wealth_db(engine)

ensure_portfolio_loaded(module_type="wealth")

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    current_pid = None
    st.session_state["wealth_active_portfolio_id"] = None
    from core.ui_utils import render_wealth_profile_picker
    render_wealth_profile_picker(engine, prof_map, key_prefix="p19_picker")
    st.stop()

# ── ATOMIC STATE TEARDOWN ───────────────────────────────────
teardown_view_state(current_pid, active_page="19_Immobili_e_Mutui")

prof_title = prof_map.get(current_pid, "Nessun Profilo")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p19")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_telemetry_ribbon(nw_summary=nw_curr, page_badge="IMMOBILI & MUTUI", profile_name=prof_title)
render_wealth_executive_badges(nw_curr)

from core.wealth.wealth_modals import render_real_estate_methodology_modal

col_re_h1, col_re_h2 = st.columns([3.5, 1.2])
with col_re_h1:
    render_page_header(
        title="ARGUS Wealth — Immobili, Mutui, DSCR & Buy vs Rent",
        subtitle="Home Equity, Ammortamento alla Francese, Simulatore Surroga vs Estinzione Parziale, DSCR Locazioni e Cedolare Secca 21%/10%.",
        icon="🏡"
    )
with col_re_h2:
    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    if st.button("ℹ️ Guida LTV & Mutui", key="btn_modal_re_p19", use_container_width=True):
        render_real_estate_methodology_modal()

re_ltv_summary = compute_real_estate_net_equity_and_ltv(engine, portfolio_id=current_pid)

# ── SELETTORE MODULI IMMOBILIARI ─────────────────────────────
WEALTH_RE_MODELS_CATALOG = {
    "🏡 Home Equity & LTV Reale": {
        "title": "Home Equity Netto & Posizione Finanziaria Immobiliare (LTV Dinamico)",
        "badge": "LTV • Equity Reale • Asset Illiquidi",
        "badge_color": "#10b981",
        "category": "Patrimonio Immobiliare",
        "desc": "Integrazione in tempo reale tra valore di mercato degli immobili registrati, ammortamento del debito residuo e LTV complessivo.",
    },
    "🏦 Simulatore Mutuo, Ammortamento & Surroga": {
        "title": "Ammortamento alla Francese, Stress Euribor, Surroga vs Estinzione Anticipata",
        "badge": "Ammortamento • Surroga L. Bersani • Lump-Sum",
        "badge_color": "#38bdf8",
        "category": "Finanziamenti & Mutui",
        "desc": "Simulazione piano di rimborso, extra-rate, estinzione parziale anticipata vs surroga a costo zero (L. Bersani) e shock Euribor.",
    },
    "📈 Redditività da Locazione, DSCR & Cedolare": {
        "title": "Valutazione Buy-to-Let: Cap Rate, Debt Service Coverage Ratio (DSCR) & Cedolare Secca 21%/10%",
        "badge": "Cap Rate • DSCR • IMU • Cedolare 10%/21%",
        "badge_color": "#fbbf24",
        "category": "Rendimento da Locazione",
        "desc": "Calcolo di Cap Rate lordo/netto, Net Operating Income (NOI), sostenibilità del debito DSCR, impatto IMU e confronto Cedolare Secca ordinaria (21%) vs concordata (10%).",
    },
    "⚖️ Buy vs Rent (Affitto vs Acquisto)": {
        "title": "Modello Matematico di Costo Opportunità Affitto vs Acquisto Prima Casa",
        "badge": "Buy vs Rent • Costo Opportunità • Equity Accumulation",
        "badge_color": "#a855f7",
        "category": "Decision Engine",
        "desc": "Confronto attuariale tra acquisto con mutuo e locazione con reinvestimento dell'anticipo e del delta-rata in un portafoglio diversificato.",
    },
}

active_re_tab = render_segmented_tabs(
    WEALTH_RE_MODELS_CATALOG,
    key="wealth_re_active_tab",
    select_label="Seleziona Modulo Immobiliare:",
)

# ============================================================
# TAB 1: HOME EQUITY & DYNAMIC LTV
# ============================================================
if active_re_tab == "🏡 Home Equity & LTV Reale":
    st.markdown("### 🏡 Net Home Equity & Posizione Finanziaria Immobiliare")
    st.caption("Integrazione in tempo reale tra il valore di mercato degli immobili registrati e il debito residuo dei mutui associati.")

    eq_c1, eq_c2, eq_c3, eq_c4 = st.columns(4)
    with eq_c1:
        metric_card("Valore Immobili", fmt_eur(re_ltv_summary["total_property_market_value"]), delta=f"{re_ltv_summary['property_count']} Immobili Registrati", delta_color="normal")
    with eq_c2:
        metric_card("Debito Mutui Residuo", fmt_eur(re_ltv_summary["total_mortgage_debt_remaining"]), delta=f"{re_ltv_summary['mortgage_count']} Finanziamenti Attivi", delta_color="normal")
    with eq_c3:
        metric_card("Net Home Equity", fmt_eur(re_ltv_summary["net_home_equity_eur"]), delta="Capitale Reale Posseduto", delta_color="normal")
    with eq_c4:
        metric_card("Loan-to-Value (LTV)", f"{re_ltv_summary['weighted_ltv_pct']:.1f}%", delta=re_ltv_summary["ltv_status"], delta_color="normal")

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    if re_ltv_summary["total_property_market_value"] > 0:
        col_g1, col_g2 = st.columns([1.5, 1.0])
        with col_g1:
            section("📊 Composizione Valore Immobiliare vs Debito Residuo")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="Net Home Equity (Capitale Tuo)",
                y=["Patrimonio Immobiliare"],
                x=[re_ltv_summary["net_home_equity_eur"]],
                orientation='h',
                marker=dict(color="#10b981")
            ))
            fig_bar.add_trace(go.Bar(
                name="Debito Mutui (Banca)",
                y=["Patrimonio Immobiliare"],
                x=[re_ltv_summary["total_mortgage_debt_remaining"]],
                orientation='h',
                marker=dict(color="#ef4444")
            ))
            fig_bar.update_layout(
                barmode='stack',
                height=220,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            apply_plotly_theme(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            section("🛡️ Stress Test Solidità Finanziaria")
            ltv_val = re_ltv_summary["weighted_ltv_pct"]
            if ltv_val <= 50.0:
                st.success(f"**LTV al {ltv_val:.1f}% — Profilo Virtuoso:** Il patrimonio immobiliare è protetto da un cuscinetto di equity superiore al 50%. Basso rischio di insolvenza o margin call creditizia.")
            elif ltv_val <= 80.0:
                st.info(f"**LTV al {ltv_val:.1f}% — Profilo Standard:** Indebitamento conforme ai benchmark bancari (sotto l'80%).")
            else:
                st.warning(f"**LTV al {ltv_val:.1f}% — Elevato Indebitamento:** Si consiglia di valutare estinzioni anticipate parziali o accantonamenti di liquidità.")

            if re_ltv_summary["estimated_monthly_mortgage_payment"] > 0:
                metric_card("Rata Mensile Stimata Mutuo", fmt_eur(re_ltv_summary["estimated_monthly_mortgage_payment"]), delta="Ammortamento Francese", delta_color="normal")
    else:
        st.info("Nessun immobile censito in questo profilo patrimoniale. Puoi registrarne uno nella pagina **15. Asset Illiquidi & Caveau**.")

    if re_ltv_summary["properties_detail"]:
        render_table_with_export(
            re_ltv_summary["properties_df"],
            table_title="Dettaglio Patrimonio Immobiliare & Mutui",
            file_prefix="immobili_e_mutui",
            key_suffix="p19_re_summary",
            column_config={
                "name": "Nome Immobile",
                "market_value": st.column_config.NumberColumn("Valore Mercato", format="€ %,.2f"),
                "allocated_debt": st.column_config.NumberColumn("Debito Allocato", format="€ %,.2f"),
                "net_equity": st.column_config.NumberColumn("Home Equity Netto", format="€ %,.2f"),
                "ltv_pct": st.column_config.NumberColumn("LTV %", format="%.1f%%"),
                "location": "Ubicazione",
                "notes": "Note"
            }
        )

# ============================================================
# TAB 2: AMMORTAMENTO MUTUO, SHOCK & SURROGA
# ============================================================
elif active_re_tab == "🏦 Simulatore Mutuo, Ammortamento & Surroga":
    st.markdown("### 🏦 Piano di Ammortamento alla Francese, Surroga vs Estinzione Parziale")
    st.caption("Ammortamento a rata costante con quota capitale crescente e quota interessi decrescente, confronto tra surroga a costo zero (L. Bersani) ed estinzione anticipata straordinaria.")

    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        m_principal = st.number_input("Importo Mutuo / Debito Residuo (€)", min_value=10000.0, max_value=2000000.0, value=float(nw_curr.debt_total if nw_curr.debt_total > 20000 else 160000.0), step=5000.0)
    with col_in2:
        m_rate = st.number_input("Tasso Annuo Attuale (%)", min_value=0.1, max_value=15.0, value=3.20, step=0.05)
    with col_in3:
        m_years = st.slider("Durata Residua (Anni)", min_value=3, max_value=35, value=20, step=1)
    with col_in4:
        m_extra = st.number_input("Rata Extra Mensile (€)", min_value=0.0, max_value=2000.0, value=100.0, step=50.0, help="Importo aggiuntivo versato a riduzione diretta del capitale residuo ogni mese.")

    with st.expander("➕ Rimborso Straordinario Una Tantum (Estinzione Parziale Anticipata)", expanded=False):
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            lump_amount = st.number_input("Importo Estinzione Parziale (€)", min_value=0.0, max_value=200000.0, value=15000.0, step=1000.0)
        with c_l2:
            lump_yr = st.slider("Eseguita all'Anno n°", min_value=1, max_value=m_years, value=3)

    mort_res = compute_mortgage_amortization(
        principal=m_principal,
        annual_rate=m_rate,
        duration_years=m_years,
        extra_monthly_payment=m_extra,
        extra_lump_sum=lump_amount,
        lump_sum_year=lump_yr
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Rata Mensile Base", fmt_eur(mort_res['monthly_payment']), delta="Ammortamento Francese", delta_color="normal")
    with k2:
        metric_card("Interessi Base Totali", fmt_eur(mort_res['total_interest']), delta="Costo Finanziamento", delta_color="inverse")
    with k3:
        metric_card("Interessi Risparmiati", fmt_eur(mort_res['interest_saved']), delta=f"Anticipo: {mort_res['years_saved']:.1f} Anni", delta_color="normal")
    with k4:
        metric_card("Durata Effettiva Post-Extra", f"{int(mort_res['actual_duration_years'])} Anni", delta=f"{mort_res['months_saved']} Mesi Risparmiati", delta_color="normal")

    st.write("")
    df_eff = pd.DataFrame(mort_res["effective_schedule"])
    if not df_eff.empty:
        fig_sched = go.Figure()
        fig_sched.add_trace(go.Scatter(
            x=df_eff["year"], y=df_eff["remaining_balance"],
            mode="lines", name="Debito Residuo",
            line=dict(color="#38bdf8", width=3),
            fill="tozeroy", fillcolor="rgba(56, 189, 248, 0.08)",
            hovertemplate="<b>Anno %{x}</b><br>Debito Residuo: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_sched.add_trace(go.Scatter(
            x=df_eff["year"], y=df_eff["principal"].cumsum(),
            mode="lines", name="Capitale Rimborsato",
            line=dict(color="#34d399", width=2.5),
            hovertemplate="<b>Anno %{x}</b><br>Capitale Rimborsato: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_sched.add_trace(go.Scatter(
            x=df_eff["year"], y=df_eff["interest"].cumsum(),
            mode="lines", name="Interessi Cumulati",
            line=dict(color="#f59e0b", width=2, dash="dash"),
            hovertemplate="<b>Anno %{x}</b><br>Interessi Cumulati: <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        fig_sched.update_layout(
            title=dict(text="Curva di Ammortamento e Riduzione Debito Residuo", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            xaxis_title="Anni",
            yaxis_title="Controvalore (€)",
            margin=dict(l=10, r=10, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_sched, use_container_width=True, config={'displayModeBar': False})

    st.write("")
    st.divider()

    # ── SIMULATORE SURROGA (L. BERSANI) VS ESTINZIONE PARZIALE ──
    section("🔄 Simulatore Surroga (L. Bersani / Art. 120-quater TUB) vs Estinzione Parziale")
    st.caption("Confronta il mutuo in corso con una proposta di surroga a costo zero (spese notarili, perizia e istruttoria a carico della nuova banca) rispetto al versamento anticipato sul capitale residuo.")

    surr_c1, surr_c2, surr_c3 = st.columns(3)
    with surr_c1:
        surr_new_rate = st.number_input("Nuovo Tasso Offerto Surroga (%)", min_value=0.5, max_value=10.0, value=2.45, step=0.05)
    with surr_c2:
        surr_new_years = st.slider("Nuova Durata Surroga (Anni)", min_value=5, max_value=35, value=m_years)
    with surr_c3:
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        st.markdown("<span style='font-size:12px; color:#38bdf8;'><b>Nota L. Bersani</b>: Costi surroga = 0 € per legge.</span>", unsafe_allow_html=True)

    # Calcolo Surroga
    r_old = m_rate / 100.0 / 12.0
    n_old = m_years * 12
    pmt_old = m_principal * (r_old * (1.0 + r_old) ** n_old) / (((1.0 + r_old) ** n_old) - 1.0)
    tot_int_old = (pmt_old * n_old) - m_principal

    r_new = surr_new_rate / 100.0 / 12.0
    n_new = surr_new_years * 12
    pmt_new = m_principal * (r_new * (1.0 + r_new) ** n_new) / (((1.0 + r_new) ** n_new) - 1.0)
    tot_int_new = (pmt_new * n_new) - m_principal

    delta_monthly_pmt = pmt_old - pmt_new
    net_interest_savings_surroga = tot_int_old - tot_int_new

    sk1, sk2, sk3, sk4 = st.columns(4)
    with sk1:
        metric_card("Nuova Rata con Surroga", fmt_eur(pmt_new), delta=f"{delta_monthly_pmt:+,.2f} €/mese", delta_color="normal" if delta_monthly_pmt >= 0 else "inverse")
    with sk2:
        metric_card("Risparmio Interessi Totale", fmt_eur(net_interest_savings_surroga), delta="Tax Free (L. Bersani)", delta_color="normal" if net_interest_savings_surroga > 0 else "inverse")
    with sk3:
        metric_card("Risparmio Annuo Cassa", fmt_eur(delta_monthly_pmt * 12.0), delta="Delta Liquidità Annua", delta_color="normal" if delta_monthly_pmt > 0 else "inverse")
    with sk4:
        conv_verdict = "✅ Conveniente" if net_interest_savings_surroga > 1000.0 else "⚠️ Margine Ridotto"
        metric_card("Verdetto Surroga", conv_verdict, delta=f"Tasso: {m_rate:.2f}% → {surr_new_rate:.2f}%", delta_color="normal")

    st.write("")
    st.divider()

    # ── SHOCK EURIBOR TASSO VARIABILE ──
    st.markdown("##### 🌪️ Shock Test Tasso Variabile (Euribor Stress)")
    st.caption("Impatto sulla rata mensile in caso di mutuo a tasso variabile in funzione delle variazioni dei tassi di riferimento BCE.")

    shk_cols = st.columns(len(mort_res["rate_shocks"]))
    for col, (s_lbl, s_data) in zip(shk_cols, mort_res["rate_shocks"].items()):
        with col:
            d_val = s_data["monthly_delta"]
            clean_title = s_lbl.split("(")[0].strip()
            metric_card(
                f"Shock {clean_title}",
                fmt_eur(s_data["new_monthly_payment"]),
                delta=f"{d_val:+,.2f} €/m ({s_data['new_rate']}%)",
                delta_color="inverse" if d_val > 0 else "normal",
                help_text=f"Rata mensile attesa a seguito dello shock sui tassi: {s_lbl}."
            )

# ============================================================
# TAB 3: REDDITIVITÀ DA LOCAZIONE, DSCR & CEDOLARE SECCA
# ============================================================
elif active_re_tab == "📈 Redditività da Locazione, DSCR & Cedolare":
    st.markdown("### 📈 Redditività Buy-to-Let, DSCR & Regimi Cedolare Secca")
    st.caption("Valutazione quantitativa del flusso da locazione: Net Operating Income (NOI), Debt Service Coverage Ratio (DSCR), incidenza IMU e confronto Cedolare Secca 21% vs 10% (Canone Concordato).")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        p_val = st.number_input("Valore Immobile Locato (€)", min_value=30000.0, value=220000.0, step=10000.0)
        p_down = st.number_input("Capitale Proprio Versato (€)", min_value=5000.0, value=60000.0, step=5000.0)
        m_rate_roi = st.number_input("Tasso Mutuo (%)", value=3.20, step=0.05)
    with rc2:
        p_rent = st.number_input("Canone Mensile di Locazione (€)", min_value=100.0, value=950.0, step=50.0)
        condo_mo = st.number_input("Spese Condominiali a Carico Proprietario (€/mese)", value=50.0, step=10.0)
        maint_pct = st.slider("Fondo Manutenzione Straordinaria (% annuo)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)
    with rc3:
        p_imu = st.number_input("IMU Annua Dovuta (€)", min_value=0.0, value=850.0, step=50.0, help="IMU ordinaria calcolata su rendita catastale rivalutata del 5% per moltiplicatore 160 per aliquota comunale.")
        tax_regime_choice = st.selectbox(
            "Regime Fiscale di Locazione:",
            options=["cedolare_21", "cedolare_10", "irpef"],
            format_func=lambda x: {
                "cedolare_21": "Cedolare Secca 21% (Canone Libero 4+4)",
                "cedolare_10": "Cedolare Secca 10% (Canone Concordato 3+2)",
                "irpef": "Regime IRPEF Ordinario (Marginale ~35%)"
            }.get(x, x)
        )

    roi = compute_real_estate_roi(
        property_val=p_val,
        down_payment=p_down,
        mortgage_rate=m_rate_roi,
        mortgage_years=25,
        monthly_rent=p_rent,
        condo_fees_monthly=condo_mo,
        imu_annual=p_imu,
        maintenance_pct=maint_pct,
        tax_regime=tax_regime_choice
    )

    # Calcolo DSCR (Debt Service Coverage Ratio)
    annual_noi = roi["noi"]
    annual_mortgage_pmt = roi.get("annual_mortgage_payment", (p_rent - roi["monthly_net_cashflow"]) * 12.0)
    if annual_mortgage_pmt > 0:
        dscr_val = annual_noi / annual_mortgage_pmt
        if dscr_val >= 1.25:
            dscr_status = "🟢 Solido (≥ 1.25)"
            dscr_color = "normal"
        elif dscr_val >= 1.0:
            dscr_status = "🟡 Neutro (1.00–1.24)"
            dscr_color = "normal"
        else:
            dscr_status = "🔴 Vulnerabile (< 1.00)"
            dscr_color = "inverse"
    else:
        dscr_val = 99.0
        dscr_status = "🟢 Senza Debito"
        dscr_color = "normal"

    st.write("")
    rk1, rk2, rk3, rk4, rk5 = st.columns(5)
    with rk1:
        metric_card("Cap Rate Netto", f"{roi['cap_rate']:.2f}%", delta=f"Lordo: {roi['gross_yield']:.2f}%", delta_color="normal", help_text="NOI diviso per il valore di mercato dell'immobile.")
    with rk2:
        metric_card("NOI Annuo (Pre-Rata)", fmt_eur(roi['noi']), delta="Post-IMU & Spese", delta_color="normal", help_text="Entrate da locazione al netto di imposte, IMU, condominio e manutenzioni.")
    with rk3:
        dscr_disp = f"{dscr_val:.2f}x" if dscr_val < 50 else "N/A (Cash)"
        metric_card("DSCR Affitti", dscr_disp, delta=dscr_status, delta_color=dscr_color, help_text="Debt Service Coverage Ratio: NOI / Rata Mutuo Annua. Soglia bancaria ottimale: >= 1.25.")
    with rk4:
        metric_card("Cash Flow Netto", f"{fmt_eur(roi['monthly_net_cashflow'])}/m", delta="Post-Rata Mutuo", delta_color="normal" if roi["is_cashflow_positive"] else "inverse", help_text="Flusso di cassa mensile effettivo al netto di tutte le spese e della rata del mutuo.")
    with rk5:
        metric_card("Cash-on-Cash Return", f"{roi['cash_on_cash_pct']:.2f}%", delta="Ritorno Equity", delta_color="normal", help_text="Rendimento percentuale sul solo capitale iniziale proprio versato (equity).")

    st.write("")
    st.divider()

    # Confronto Regimi Fiscali (Cedolare 21% vs 10% vs IRPEF)
    section("⚖️ Confronto Fiscale: Cedolare Secca 21% vs 10% (Canone Concordato) vs IRPEF")
    gross_annual = p_rent * 12.0
    tax_21 = gross_annual * 0.21
    tax_10 = gross_annual * 0.10
    tax_irpef = gross_annual * 0.95 * 0.35  # Deduzione forfettaria 5% su IRPEF 35%

    df_tax_comp = pd.DataFrame([
        {
            "Regime Fiscale": "Cedolare Secca 21% (Canone Libero 4+4)",
            "Imposta Annua (€)": fmt_eur(tax_21),
            "IMU Agevolata": "No (Aliquota Ordinaria)",
            "Net Yield Stimato": f"{((gross_annual - tax_21 - p_imu - condo_mo*12 - p_val*maint_pct/100)/p_val*100):.2f}%",
            "Risparmio vs 21%": "€ 0,00"
        },
        {
            "Regime Fiscale": "Cedolare Secca 10% (Canone Concordato 3+2)",
            "Imposta Annua (€)": fmt_eur(tax_10),
            "IMU Agevolata": "Sì (-25% IMU per legge statale)",
            "Net Yield Stimato": f"{((gross_annual - tax_10 - p_imu*0.75 - condo_mo*12 - p_val*maint_pct/100)/p_val*100):.2f}%",
            "Risparmio vs 21%": f"+{fmt_eur(tax_21 - tax_10 + p_imu*0.25)}/anno"
        },
        {
            "Regime Fiscale": "IRPEF Ordinaria (Aliquota Marginale ~35%)",
            "Imposta Annua (€)": fmt_eur(tax_irpef),
            "IMU Agevolata": "No (Aliquota Ordinaria)",
            "Net Yield Stimato": f"{((gross_annual - tax_irpef - p_imu - condo_mo*12 - p_val*maint_pct/100)/p_val*100):.2f}%",
            "Risparmio vs 21%": f"-{fmt_eur(tax_irpef - tax_21)}/anno"
        }
    ])
    st.dataframe(df_tax_comp, hide_index=True, use_container_width=True)

# ============================================================
# TAB 4: BUY VS RENT
# ============================================================
elif active_re_tab == "⚖️ Buy vs Rent (Affitto vs Acquisto)":
    st.markdown("### ⚖️ Buy vs Rent — Modello Matematico sul Costo Opportunità")
    st.caption("Confronta la crescita del patrimonio netto tra l'acquisto della prima casa e l'affitto con investimento del capitale iniziale in un portafoglio azionario globale diversificato.")

    b_c1, b_c2, b_c3 = st.columns(3)
    with b_c1:
        bvr_val = st.number_input("Valore Immobile Casa (€)", min_value=50000.0, value=250000.0, step=10000.0)
        bvr_down = st.number_input("Anticipo per Acquisto (€)", min_value=10000.0, value=50000.0, step=5000.0)
    with b_c2:
        bvr_rent = st.number_input("Affitto Mensile Alternativo (€)", min_value=200.0, value=850.0, step=50.0)
        bvr_m_rate = st.number_input("Tasso Mutuo Acquisto (%)", value=3.20, step=0.05)
    with b_c3:
        bvr_mkt_ret = st.slider("Rendimento Mercato Azionario (% annuo)", min_value=3.0, max_value=12.0, value=7.5, step=0.5, help="Rendimento nominale atteso da un ETF azionario globale (es. MSCI World).")
        bvr_inf = st.slider("Tasso Inflazione Stimato (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5)

    bvr = compute_buy_vs_rent_comparison(
        property_val=bvr_val,
        down_payment=bvr_down,
        mortgage_rate=bvr_m_rate,
        mortgage_years=25,
        monthly_rent=bvr_rent,
        investment_return_rate=bvr_mkt_ret / 100.0,
        inflation_rate=bvr_inf / 100.0,
        years_horizon=25
    )

    bv_k1, bv_k2, bv_k3, bv_k4 = st.columns(4)
    with bv_k1:
        metric_card("Scenario Vincitore", str(bvr["winner"]), delta="Orizzonte 25 Anni", help_text="Strategia ottimale che massimizza il Patrimonio Netto al termine dell'orizzonte.")
    with bv_k2:
        metric_card("Net Worth Acquisto", fmt_eur(bvr['final_buy_net_worth']), delta="Equity Immobile", help_text="Valore rivalutato dell'immobile al termine del periodo.")
    with bv_k3:
        metric_card("Net Worth Affitto", fmt_eur(bvr['final_rent_net_worth']), delta="Capitale ETF Mercati", help_text="Capitale accumulato investendo l'anticipo e il delta canone/rata nei mercati azionari.")
    with bv_k4:
        c_yr = f"{bvr['crossover_year']} Anni" if isinstance(bvr['crossover_year'], int) else str(bvr['crossover_year'])
        metric_card("Punto Pareggio", c_yr, delta="Crossover Year", help_text="Anno in cui una strategia supera definitivamente l'altra in termini di patrimonio netto.")

    fig_bvr = go.Figure()
    years = list(range(1, bvr["years_horizon"] + 1))
    fig_bvr.add_trace(go.Scatter(
        x=years, y=bvr["buy_equity_trajectory"],
        mode="lines", name="Acquisto (Equity Immobile)",
        line=dict(color="#10b981", width=3),
        hovertemplate="<b>Anno %{x}</b><br>Equity Immobile: <b>€ %{y:,.2f}</b><extra>Acquisto</extra>"
    ))
    fig_bvr.add_trace(go.Scatter(
        x=years, y=bvr["rent_invested_trajectory"],
        mode="lines", name="Affitto + Investimento ETF Mercati",
        line=dict(color="#6366f1", width=3, dash="dash"),
        hovertemplate="<b>Anno %{x}</b><br>Capitale ETF: <b>€ %{y:,.2f}</b><extra>Affitto + ETF</extra>"
    ))
    fig_bvr.update_layout(
        title=dict(text="Evoluzione del Patrimonio Netto: Acquisto vs Affitto + Investimento", font=dict(size=14, color="#ffffff")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        xaxis_title="Anni dall'inizio",
        yaxis_title="Patrimonio Netto Consolidato (€)",
        margin=dict(l=10, r=10, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bvr, use_container_width=True, config={'displayModeBar': False})

render_sr117_audit_drawer(engine, model_name="ARGUS Real Estate & Mortgage Analytics", audit_metrics=re_ltv_summary)
