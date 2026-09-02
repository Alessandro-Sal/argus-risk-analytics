# ============================================================
# 19_🏡_Immobili_e_Mutui.py
# ARGUS Wealth — Immobili, Piani di Ammortamento Mutuo & Buy vs Rent
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
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

from core.ui_utils import (
    inject_custom_css,
    section,
    metric_card,
    fmt_eur,
    fmt_pct,
    render_wealth_command_bar,
    render_wealth_executive_badges,
    render_page_header,
    apply_plotly_theme
)

from core.sidebar import render_sidebar
from core.fetcher import get_engine
from core.wealth.wealth_engine import (
    compute_mortgage_amortization,
    compute_real_estate_roi,
    compute_buy_vs_rent_comparison,
    compute_consolidated_net_worth,
    compute_real_estate_net_equity_and_ltv
)
from core.wealth.wealth_db import get_wealth_portfolios


st.set_page_config(page_title="Immobili & Mutui | ARGUS Wealth", page_icon="🏡", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_port = int(st.session_state.get("db_port", 3306))
db_name = st.session_state.get("db_name", "wealth")

engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    st.title("🏡 ARGUS Wealth — Immobili & Mutui")
    st.markdown("""
    <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(16,185,129,0.3); border-left:4px solid #10b981; border-radius:10px; padding:18px 22px; margin: 18px 0;">
        <h4 style="color:#ffffff; margin:0 0 6px 0;">📁 Nessun Profilo Patrimoniale Selezionato</h4>
        <p style="color:#94a3b8; font-size:13px; margin:0 0 14px 0;">Seleziona un profilo attivo per calcolare i piani di ammortamento, la redditività immobiliare e il simulatore Buy vs Rent.</p>
    </div>
    """, unsafe_allow_html=True)
    sel_box = st.selectbox(
        "Seleziona Profilo Patrimoniale:",
        options=[None] + list(prof_map.keys()),
        format_func=lambda pid: "👉 Seleziona un Profilo..." if pid is None else f"📁 {prof_map[pid]} (ID #{pid})",
        key="re_unselected_profile_picker"
    )
    if sel_box is not None:
        st.session_state["wealth_active_portfolio_id"] = sel_box
        st.rerun()
    st.stop()

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p19")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Immobili, Mutui & Buy vs Rent",
    subtitle="Ammortamento alla Francese con Estinzione Anticipata, Rendimenti da Locazione (Cap Rate) e Modello Costo Opportunità Affitto vs Acquisto.",
    icon="🏡"
)


re_ltv_summary = compute_real_estate_net_equity_and_ltv(engine, portfolio_id=current_pid)

tab_equity, tab_mortgage, tab_roi, tab_bvr = st.tabs([
    "🏡 Home Equity & LTV Reale",
    "🏦 Simulatore Mutuo & Ammortamento",
    "📈 Redditività Immobiliare (Cap Rate & Cash Flow)",
    "⚖️ Buy vs Rent (Affitto vs Acquisto)"
])

# ── TAB 1: HOME EQUITY & DYNAMIC LTV ───────────────────────
with tab_equity:
    st.markdown("### 🏡 Net Home Equity & Posizione Finanziaria Immobiliare")
    st.caption("Integrazione in tempo reale tra il valore di mercato degli immobili registrati nel Caveau/Fisici e il debito residuo dei mutui.")

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

    # Grafico a barre orizzontali Market Value vs Debito vs Equity
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
                st.metric("Rata Mensile Stimata Mutuo", fmt_eur(re_ltv_summary["estimated_monthly_mortgage_payment"]))
    else:
        st.info("Nessun immobile censito in questo profilo patrimoniale. Puoi registrarne uno nella pagina **15. Asset Illiquidi & Caveau**.")

    # Dettaglio immobili
    if re_ltv_summary["properties_detail"]:
        st.markdown("#### 🏢 Dettaglio Immobili & Ripartizione Debito")
        st.dataframe(
            re_ltv_summary["properties_df"],
            column_config={
                "name": "Nome Immobile",
                "market_value": st.column_config.NumberColumn("Valore Mercato", format="€ %,.2f"),
                "allocated_debt": st.column_config.NumberColumn("Debito Allocato", format="€ %,.2f"),
                "net_equity": st.column_config.NumberColumn("Home Equity Netto", format="€ %,.2f"),
                "ltv_pct": st.column_config.NumberColumn("LTV %", format="%.1f%%"),
                "location": "Ubicazione",
                "notes": "Note"
            },
            hide_index=True,
            use_container_width=True
        )

# ── TAB 2: AMMORTAMENTO MUTUO ───────────────────────────────
with tab_mortgage:
    st.markdown("### 🏦 Piano di Ammortamento alla Francese & Estinzione Anticipata")
    
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        m_principal = st.number_input("Importo Mutuo (€)", min_value=10000.0, max_value=2000000.0, value=160000.0, step=5000.0)
    with col_in2:
        m_rate = st.number_input("Tasso Annuo Fisso (%)", min_value=0.1, max_value=15.0, value=3.10, step=0.05)
    with col_in3:
        m_years = st.slider("Durata (Anni)", min_value=5, max_value=40, value=25, step=1)
    with col_in4:
        m_extra = st.number_input("Rata Extra Mensile (€)", min_value=0.0, max_value=2000.0, value=100.0, step=50.0, help="Importo aggiuntivo versato a riduzione diretta del capitale residuo ogni mese.")

    with st.expander("➕ Rimborso Straordinario Una Tantum (Lump-Sum)", expanded=False):
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            lump_amount = st.number_input("Importo Una Tantum (€)", min_value=0.0, max_value=100000.0, value=0.0, step=1000.0)
        with c_l2:
            lump_yr = st.slider("All'anno n°", min_value=1, max_value=m_years, value=5)

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
        metric_card("Rata Mensile", fmt_eur(mort_res['monthly_payment']), delta="Ammortamento Francese", delta_color="gray", help_text="Rata periodica costante comprensiva di quota capitale e quota interessi.")
    with k2:
        metric_card("Interessi Base", fmt_eur(mort_res['total_interest']), delta="Costo Finanziamento", delta_color="inverse", help_text="Totale interessi dovuti alla banca senza versamenti extra.")
    with k3:
        metric_card("Interessi Risparmiati", fmt_eur(mort_res['interest_saved']), delta=f"Risparmio {mort_res['years_saved']:.1f} Anni", delta_color="normal", help_text="Risparmio netto di interessi grazie agli ammortamenti straordinari.")
    with k4:
        metric_card("Durata Effettiva", f"{int(mort_res['actual_duration_years'])} Anni", delta=f"Anticipo {mort_res['months_saved']} Mesi", delta_color="normal", help_text=f"Il mutuo si estingue con {mort_res['months_saved']} mesi di anticipo.")



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
            height=360,
            xaxis_title="Anni",
            yaxis_title="Controvalore (€)",
            margin=dict(l=10, r=10, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_sched, use_container_width=True, config={'displayModeBar': False})

    st.write("")
    st.markdown("##### 🌪️ Shock Test Tasso Variabile (Euribor Stress)")
    st.caption("Impatto sulla rata mensile in caso di mutuo a tasso variabile in funzione delle variazioni dei tassi di riferimento BCE.")
    
    shk_cols = st.columns(len(mort_res["rate_shocks"]))
    for col, (s_lbl, s_data) in zip(shk_cols, mort_res["rate_shocks"].items()):
        with col:
            d_val = s_data["monthly_delta"]
            delta_stat = f"{d_val:+,.2f} €/m"
            d_col = "inverse" if d_val > 0 else "normal"
            clean_title = s_lbl.split("(")[0].strip()
            metric_card(
                f"Shock {clean_title}",
                fmt_eur(s_data["new_monthly_payment"]),
                delta=f"{delta_stat} ({s_data['new_rate']}%)",
                delta_color=d_col,
                help_text=f"Rata mensile attesa a seguito dello shock sui tassi: {s_lbl} (Nuovo tasso nominale stimato: {s_data['new_rate']}%)."
            )


# ── TAB 2: REDDITIVITÀ IMMOBILIARE (BUY-TO-LET) ─────────────
with tab_roi:
    st.markdown("### 📈 Valutazione Redditività da Locazione (Buy-to-Let)")
    st.caption("Calcolo del Cap Rate, Rendimento Lordo, Net Operating Income (NOI) e Cash-on-Cash Return al netto di IMU, spese e cedolare secca.")

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        p_val = st.number_input("Prezzo di Acquisto Immobile (€)", min_value=20000.0, value=200000.0, step=5000.0)
        p_down = st.number_input("Capitale Proprio / Anticipo (€)", min_value=0.0, value=40000.0, step=5000.0)
    with rc2:
        r_rent = st.number_input("Canone Mensile di Affitto (€)", min_value=100.0, value=900.0, step=50.0)
        r_condo = st.number_input("Spese Condominiali non addebitabili (€/m)", min_value=0.0, value=50.0, step=10.0)
    with rc3:
        r_imu = st.number_input("IMU Annuale Stimata (€)", min_value=0.0, value=750.0, step=50.0)
        r_maint = st.number_input("Riserva Manutenzioni (% annuo)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)
    with rc4:
        r_tax_regime = st.selectbox(
            "Regime Fiscale:",
            options=["cedolare_21", "cedolare_10", "irpef_ordinaria"],
            format_func=lambda x: "Cedolare Secca 21% (Libero)" if x == "cedolare_21" else ("Cedolare Secca 10% (Concordato)" if x == "cedolare_10" else "IRPEF Ordinaria (35%)")
        )
        r_m_rate = st.number_input("Tasso Mutuo (%)", value=3.20, step=0.05)

    roi = compute_real_estate_roi(
        property_val=p_val,
        down_payment=p_down,
        mortgage_rate=r_m_rate,
        monthly_rent=r_rent,
        condo_fees_monthly=r_condo,
        imu_annual=r_imu,
        maintenance_pct=r_maint,
        tax_regime=r_tax_regime
    )

    rk1, rk2, rk3, rk4, rk5 = st.columns(5)
    with rk1:
        metric_card("Gross Yield", f"{roi['gross_yield_pct']:.2f}%", delta="Rendimento Lordo", help_text="Affitto annuo / Prezzo di acquisto immobile.")
    with rk2:
        metric_card("Cap Rate Netto", f"{roi['net_yield_pct']:.2f}%", delta="Net Yield", help_text="NOI (Reddito Operativo Netto) / Prezzo immobile.")
    with rk3:
        metric_card("NOI Annuale", fmt_eur(roi['noi']), delta="Reddito Netto", help_text="Entrate da locazione al netto di imposte, IMU, condominio e manutenzioni.")
    with rk4:
        metric_card("Cash Flow Netto", f"{fmt_eur(roi['monthly_net_cashflow'])}/m", delta="Post Rata Mutuo", delta_color="normal" if roi["is_cashflow_positive"] else "inverse", help_text="Flusso di cassa mensile residuo al netto della rata del mutuo.")
    with rk5:
        metric_card("Cash-on-Cash", f"{roi['cash_on_cash_pct']:.2f}%", delta="Ritorno Capitale", help_text="Rendimento sul solo capitale effettivamente versato (Anticipo + Spese notarili).")

# ── TAB 3: BUY VS RENT ──────────────────────────────────────
with tab_bvr:
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

