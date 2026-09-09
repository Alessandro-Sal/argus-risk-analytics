# ============================================================
# 20_⚖️_Pianificazione_Successoria.py
# ARGUS Wealth — Pianificazione Successoria, Quote di Legittima & Estate Planning HNWI
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
from core.wealth import (
    get_wealth_portfolios,
    compute_consolidated_net_worth,
    compute_estate_planning_analytics,
    compute_family_governance_and_patti_di_famiglia,
    GenerationalTransferOptimizer,
    FamilyProfile,
    FamilyHeir,
    PlanningLevers,
    AssetProtectionEngine
)


st.set_page_config(page_title="Pianificazione Successoria | ARGUS Wealth", page_icon="⚖️", layout="wide")
inject_custom_css()
render_sidebar()

st.session_state.argus_portal_mode = "🏛️ Wealth Management"

db_user = st.session_state.get("db_user", "root")
db_pass = st.session_state.get("db_pass", "root")
db_host = st.session_state.get("db_host", "localhost")
db_name = st.session_state.get("wealth_db_name") or st.session_state.get("db_name") or "wealth"
offline_mode = bool(st.session_state.get("offline_mode", False))
db_port = int(st.session_state.get("db_port", 3306))

engine = get_engine(db_user, db_pass, db_host, db_port, db_name, database=db_name, offline=offline_mode)

df_prof = get_wealth_portfolios(engine)
prof_map = {row["portfolio_id"]: row["name"] for _, row in df_prof.iterrows()}
current_pid = st.session_state.get("wealth_active_portfolio_id")

if current_pid is None or current_pid not in prof_map:
    for pid_candidate, pname in prof_map.items():
        if pname.strip().lower() == "personale":
            current_pid = pid_candidate
            break
    if current_pid is None and prof_map:
        current_pid = list(prof_map.keys())[0]
    st.session_state["wealth_active_portfolio_id"] = current_pid

prof_title = prof_map.get(current_pid, "Personale")
render_wealth_command_bar(engine, current_pid=current_pid, prof_name=prof_title, key_suffix="p20")
nw_curr = compute_consolidated_net_worth(engine, portfolio_id=current_pid)
render_wealth_executive_badges(nw_curr)

# Header
render_page_header(
    title="ARGUS Wealth — Pianificazione Successoria & Estate Planning HNWI",
    subtitle="Mappatura dell'Asse Ereditario (Codice Civile art. 536-564), Riunione Fittizia, Azione di Riduzione, Ottimizzazione Fiscale e Asset Protection.",
    icon="⚖️"
)

from core.wealth.wealth_modals import render_succession_methodology_modal

col_est_h1, col_est_h2 = st.columns([3.5, 1.2])
with col_est_h1:
    if len(prof_map) > 1:
        sel_pid = st.selectbox(
            "Profilo Patrimoniale:",
            options=list(prof_map.keys()),
            format_func=lambda pid: f"📁 {prof_map[pid]}",
            index=list(prof_map.keys()).index(current_pid) if current_pid in prof_map else 0,
            key="estate_profile_selector_widget"
        )
        if sel_pid != current_pid:
            st.session_state["wealth_active_portfolio_id"] = sel_pid
            st.rerun()

with col_est_h2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("ℹ️ Guida Successioni & Patti", key="btn_modal_estate_p20", use_container_width=True):
        render_succession_methodology_modal()


nw = compute_consolidated_net_worth(engine, portfolio_id=current_pid)

# ── CONFIGURAZIONE SITUAZIONE FAMILIARE & PARAMETRI SUCCESSORI ──
with st.container():
    st.markdown("##### 👨‍👩‍👧‍👦 Parametri Nucleo Familiare, Eredi & Passività Ereditarie")
    f_c1, f_c2, f_c3, f_c4 = st.columns([1.5, 1.2, 1.5, 1.8])
    with f_c1:
        has_spouse = st.checkbox("Presenza Coniuge in Vita", value=True)
        has_ascendants = st.checkbox("Presenza Ascendenti (Genitori)", value=False, help="Rilevante ex artt. 538 e 544 c.c. in assenza di figli.")
    with f_c2:
        num_children = st.number_input("Numero di Figli", min_value=0, max_value=10, value=2, step=1)
        dis_children = st.number_input(
            "Figli con Disabilità (L. 104)",
            min_value=0,
            max_value=max(0, int(num_children)),
            value=0,
            step=1,
            help="Franchigia maggiorata ad € 1.500.000 ex art. 2 c. 49-bis D.L. 262/2006."
        )
    with f_c3:
        donations = st.number_input(
            "Donazioni in Vita (€)",
            min_value=0.0,
            value=0.0,
            step=10000.0,
            help="Donatum storico da riunire all'attivo ereditario ex art. 556 c.c."
        )
        liabilities_val = st.number_input(
            "Passività Deducibili (€)",
            min_value=0.0,
            value=float(getattr(nw, "total_liabilities", 0.0)),
            step=5000.0,
            help="Mutui residui e debiti ereditari deducibili dal relictum ex art. 556 c.c."
        )
    with f_c4:
        first_home_applicable = st.checkbox(
            "Agevolazione 'Prima Casa' per eredi",
            value=True,
            help="Imposte ipotecaria e catastale in misura fissa (€ 200 + € 200) ex art. 69 L. 342/2000."
        )
        st.caption("Normativa: Artt. 536-564 c.c. (Riserva e Riunione Fittizia), D.Lgs. 346/1990 (TUS), D.Lgs. 347/1990.")

estate = compute_estate_planning_analytics(
    net_worth_summary=nw,
    children_count=num_children,
    has_spouse=has_spouse,
    donations_in_life=donations,
    has_ascendants=has_ascendants,
    disabled_children_count=dis_children,
    liabilities_deductible=liabilities_val,
    is_first_home_applicable=first_home_applicable
)

# ── TOP KPI ROW ─────────────────────────────────────────────
ek1, ek2, ek3, ek4, ek5 = st.columns(5)
with ek1:
    metric_card(
        "Asse Ereditario",
        fmt_eur(estate['total_wealth']),
        delta=f"Relictum € {estate['relictum_net']:,.0f}",
        help_text="Patrimonio Netto (Relictum lordo - debiti) + Donazioni in vita (Riunione Fittizia art. 556 c.c.)"
    )
with ek2:
    legit_tot = estate['val_legittima_coniuge'] + estate['val_legittima_figli_tot'] + estate.get('val_legittima_ascendenti', 0.0)
    metric_card(
        "Quota Legittima",
        fmt_eur(legit_tot),
        delta="Riservata ex lege",
        delta_color="inverse",
        help_text="Quota minima riservata per legge ai legittimari (coniuge, discendenti, ascendenti)."
    )
with ek3:
    metric_card(
        "Quota Disponibile",
        fmt_eur(estate['val_disponibile']),
        delta=f"{estate['disponibile_pct']:.1f}% dell'Asse",
        delta_color="normal",
        help_text="Quota di patrimonio che il testatore può destinare liberamente a chiunque tramite testamento."
    )
with ek4:
    metric_card(
        "Asset Esenti ex lege",
        fmt_eur(estate['total_exempt_assets']),
        delta="Esenti art. 12 TUS",
        delta_color="normal",
        help_text="Fondi pensione e Titoli di Stato esenti da imposta di successione."
    )
with ek5:
    stat_del = "Sotto Franchigia" if estate["is_under_exempt_threshold"] else "Imposta Applicata"
    del_col = "normal" if estate["is_under_exempt_threshold"] else "inverse"
    tot_tax_all = estate['total_taxes_with_ipocatastali']
    metric_card(
        "Tributi Totali Ante",
        fmt_eur(tot_tax_all),
        delta=f"Succ: {fmt_eur(estate['total_succession_tax'])} | IpoCat: {fmt_eur(estate['mortgage_cadastral_tax'])}",
        delta_color=del_col,
        help_text="Imposta di successione + imposte ipotecarie e catastali stimate in assenza di ottimizzazione."
    )


st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# ── TABS ────────────────────────────────────────────────────
tab_shares, tab_taxes, tab_optimizer, tab_shield, tab_patto = st.tabs([
    "🍰 Ripartizione Quote di Legittima",
    "🧾 Calcolo Imposta & Franchigie",
    "🚀 Generational Transfer Optimizer (Ante vs Post)",
    "🛡️ Strumenti di Protezione Patrimoniale",
    "🏛️ Family Governance & Patti di Famiglia"
])

with tab_shares:
    st.markdown("### 🍰 Ripartizione Quote di Legittima (Codice Civile Artt. 536-544)")
    st.caption(f"Norma applicata: **{estate['quota_desc']}**")

    col_chart, col_details = st.columns([1.2, 1.1])
    with col_chart:
        labels = []
        values = []
        colors = []

        if estate["legittima_coniuge_pct"] > 0:
            labels.append("Legittima Coniuge")
            values.append(estate["val_legittima_coniuge"])
            colors.append("#38bdf8")

        if estate["legittima_figli_tot_pct"] > 0:
            if num_children == 1:
                labels.append("Legittima Figlio Unico")
                values.append(estate["val_legittima_figli_tot"])
                colors.append("#34d399")
            else:
                for i in range(1, num_children + 1):
                    is_d = (i <= dis_children)
                    labels.append(f"Figlio #{i}" + (" (L. 104)" if is_d else ""))
                    values.append(estate["val_legittima_per_figlio"])
                    colors.append("#10b981")

        if estate.get("legittima_ascendenti_tot_pct", 0.0) > 0:
            labels.append("Legittima Ascendenti")
            values.append(estate["val_legittima_ascendenti"])
            colors.append("#c084fc")

        labels.append("Quota Disponibile")
        values.append(estate["val_disponibile"])
        colors.append("#fbbf24")

        fig_estate = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.60,
            marker_colors=colors,
            textinfo="percent",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>Valore: <b>€ %{value:,.2f}</b> (%{percent})<extra></extra>"
        )])
        fig_estate.update_layout(
            title=dict(text="Mappa Grafica dell'Asse Ereditario Calcolato", font=dict(size=14, color="#ffffff")),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=10, r=10, t=50, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<span style='font-size:10.5px; color:#94a3b8;'>ASSE TOTALE</span><br><b style='font-size:14px; color:#ffffff;'>€ {estate['total_wealth']:,.0f}</b>",
                x=0.5, y=0.5, font_size=12, showarrow=False
            )]
        )
        st.plotly_chart(fig_estate, use_container_width=True, config={'displayModeBar': False})

    with col_details:
        st.markdown("##### 📜 Dettaglio Diritti e Riserve Legali")
        if has_spouse:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#ffffff; font-size:13.5px;">👰 Coniuge Superstite:</b>
                    <span class="mono-num" style="font-weight:700; color:#38bdf8; font-size:14px;">€ {estate['val_legittima_coniuge']:,.2f} ({estate['legittima_coniuge_pct']}%)</span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Include ex lege il diritto di abitazione sulla residenza familiare e d'uso sui mobili (art. 540 c. 2 c.c.).</div>
            </div>
            """, unsafe_allow_html=True)

        if num_children > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(52, 211, 153, 0.25); border-left: 4px solid #34d399; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#ffffff; font-size:13.5px;">👧 Figli ({num_children}):</b>
                    <span class="mono-num" style="font-weight:700; color:#34d399; font-size:14px;">€ {estate['val_legittima_figli_tot']:,.2f} ({estate['legittima_figli_tot_pct']}%)</span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Quota individuale: <b style="color:#e2e8f0;">€ {estate['val_legittima_per_figlio']:,.2f}</b> ciascuno in parti uguali.</div>
            </div>
            """, unsafe_allow_html=True)

        if estate.get("legittima_ascendenti_tot_pct", 0.0) > 0:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(192, 132, 252, 0.25); border-left: 4px solid #c084fc; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#ffffff; font-size:13.5px;">👴 Ascendenti (Genitori):</b>
                    <span class="mono-num" style="font-weight:700; color:#c084fc; font-size:14px;">€ {estate['val_legittima_ascendenti']:,.2f} ({estate['legittima_ascendenti_tot_pct']}%)</span>
                </div>
                <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Riserva spettante in assenza di discendenti (artt. 538 e 544 c.c.).</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(251, 191, 36, 0.25); border-left: 4px solid #fbbf24; padding: 12px 16px; border-radius: 10px; margin-bottom: 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:#ffffff; font-size:13.5px;">🎁 Quota Disponibile:</b>
                <span class="mono-num" style="font-weight:700; color:#fbbf24; font-size:14px;">€ {estate['val_disponibile']:,.2f} ({estate['disponibile_pct']}%)</span>
            </div>
            <div style="font-size:11.5px; color:#94a3b8; margin-top:4px;">Quota libera da destinare a chiunque via testamento senza ledere i legittimari.</div>
        </div>
        """, unsafe_allow_html=True)

with tab_taxes:
    st.markdown("### 🧾 Simulazione Imposte di Successione & Ipotecarie/Catastali")
    st.caption("Normativa applicata: **D.Lgs. 346/1990 (TUS)** e **D.Lgs. 347/1990**. Franchigia di € 1.000.000 (elevata a € 1.500.000 per handicap grave L. 104) con aliquota al 4% oltre soglia per coniuge e parenti in linea retta.")

    if estate["tax_heirs"]:
        df_tax = pd.DataFrame(estate["tax_heirs"])
        st.dataframe(
            df_tax,
            column_config={
                "erede": st.column_config.TextColumn("Erede Legittimo", width="medium"),
                "quota_valore": st.column_config.NumberColumn("Valore Quota Ereditaria (€)", format="€ %,.2f", width="medium"),
                "franchigia": st.column_config.NumberColumn("Franchigia di Legge (€)", format="€ %,.2f", width="medium"),
                "base_imponibile": st.column_config.NumberColumn("Base Imponibile Tassabile (€)", format="€ %,.2f", width="medium"),
                "aliquota": st.column_config.TextColumn("Aliquota", width="small"),
                "imposta_dovuta": st.column_config.NumberColumn("Imposta di Successione (€)", format="€ %,.2f", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nessuna imposta di successione applicabile.")

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if estate["is_under_exempt_threshold"]:
            st.success("🟢 **Patrimonio Sotto Franchigia**: Tutte le quote ereditarie rientrano nelle franchigie di legge. Imposta di successione dovuta pari a **€ 0,00**.")
        else:
            st.warning(f"⚠️ **Imposta di Successione Dovuta**: Totale calcolato pari a **€ {estate['total_succession_tax']:,.2f}**.")
    with t_col2:
        st.info(f"🏛️ **Imposte Ipotecarie e Catastali su Immobili**: Stimate in **€ {estate['mortgage_cadastral_tax']:,.2f}** ({'Fisse € 200+€ 200 Prima Casa' if first_home_applicable else 'Ordinarie 2% + 1%'}). Totale Tributi: **€ {estate['total_taxes_with_ipocatastali']:,.2f}**.")


# ── TAB 3: GENERATIONAL TRANSFER OPTIMIZER ──────────────────
with tab_optimizer:
    st.markdown("### 🚀 Generational Transfer Optimizer (Ante vs. Post Pianificazione HNWI)")
    st.caption("Simulatore quantitativo per la riduzione del carico fiscale successorio, la creazione di liquidità immediata per gli eredi (svincolata dai blocchi bancari) e la blindatura da azioni di riduzione.")

    # Parametri e Leve di Pianificazione
    st.markdown("##### 🎛️ Configurazione Leve di Pianificazione Attiva")
    l_col1, l_col2 = st.columns(2)

    with l_col1:
        re_val_cur = float(getattr(nw, "real_estate_total", 0.0))
        fin_val_cur = float(getattr(nw, "financial_investments", 0.0))
        cash_val_cur = float(getattr(nw, "liquid_cash", 0.0))
        biz_val_cur = float(getattr(nw, "business_equity", 0.0)) or (estate["total_wealth"] * 0.25)

        st.markdown("**🛡️ Leva 1: Polizze Vita Ramo I / Ramo III (Art. 12 TUS & Art. 1923 c.c.)**")
        max_life = float(fin_val_cur + cash_val_cur)
        life_ins_val = st.slider(
            "Capitale da allocare in Polizze Vita (€):",
            min_value=0.0,
            max_value=max(10000.0, max_life),
            value=min(max_life, max_life * 0.40),
            step=25000.0,
            help="Capitale escluso dall'attivo ereditario (0% imposta di successione) e impignorabile/insequestrabile ex art. 1923 c.c."
        )

        st.markdown("**🏡 Leva 2: Donazione Nuda Proprietà Immobili con Riserva di Usufrutto**")
        re_don_val = st.slider(
            "Valore Immobiliari da donare in Nuda Proprietà (€):",
            min_value=0.0,
            max_value=max(10000.0, re_val_cur),
            value=min(re_val_cur, re_val_cur * 0.60),
            step=25000.0,
            help="Donazione in vita con abbattimento della base imponibile in base all'età dell'usufruttuario (D.P.R. 131/1986). Consolidamento esente alla morte."
        )
        donor_age = st.slider("Età del Donante / Usufruttuario (Anni):", min_value=40, max_value=95, value=72, step=1)
        u_pct, b_pct = GenerationalTransferOptimizer.get_usufruct_and_bare_ownership_shares(donor_age)
        st.caption(f"📊 Coefficiente Ministeriale Età {donor_age}: **Usufrutto {u_pct*100:.0f}%** | **Nuda Proprietà {b_pct*100:.0f}%** (Base imponibile donazione: € {re_don_val * b_pct:,.0f}).")

    with l_col2:
        st.markdown("**🏛️ Leva 3: Holding Familiare / Società Semplice / Patto di Famiglia**")
        holding_val = st.slider(
            "Partecipazioni/Asset conferiti in Holding S.s. o Azienda (€):",
            min_value=0.0,
            max_value=max(10000.0, biz_val_cur),
            value=biz_val_cur,
            step=50000.0,
            help="Gestione delle quote e passaggio generazionale agevolato."
        )
        patto_eligible = st.checkbox(
            "Patto di Famiglia (Art. 768-bis c.c. & Art. 3 c. 4-ter TUS)",
            value=True,
            help="Esenzione TOTALE 100% da imposta per trasferimento del controllo con impegno a mantenere l'attività per 5 anni."
        )

        st.markdown("**💳 Leva 4: Cointestazione Conto Corrente a Firma Disgiunta**")
        joint_cash_val = st.slider(
            "Liquidità su Conto Cointestato a Firma Disgiunta (€):",
            min_value=0.0,
            max_value=max(5000.0, cash_val_cur),
            value=min(cash_val_cur, cash_val_cur * 0.50),
            step=5000.0,
            help="Presunzione di contitolarità 50% ex art. 1298 c.c. Svincolo immediato di cassa agli eredi."
        )

    # Costruzione profili e simulazione
    family_prof = FamilyProfile(
        has_spouse=has_spouse,
        children_count=num_children,
        has_ascendants=has_ascendants,
        disabled_children_count=dis_children
    )

    baseline_assets = {
        "real_estate_total": re_val_cur,
        "financial_investments": fin_val_cur,
        "liquidity_cash": cash_val_cur,
        "business_equity": biz_val_cur,
        "physical_assets": float(getattr(nw, "physical_assets", 0.0)),
        "pension_total": float(getattr(nw, "pension_total", 0.0))
    }

    planning_levers = PlanningLevers(
        life_insurance_allocation_eur=life_ins_val,
        holding_family_ss_equity_eur=holding_val,
        patto_di_famiglia_eligible=patto_eligible,
        bare_ownership_donation_re_eur=re_don_val,
        donor_age=donor_age,
        joint_account_cash_eur=joint_cash_val,
        is_first_home_applicable=first_home_applicable
    )

    comp_res = GenerationalTransferOptimizer.simulate_generational_plan(
        baseline_assets=baseline_assets,
        liabilities=liabilities_val,
        donatum=donations,
        family_profile=family_prof,
        levers=planning_levers
    )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.markdown("##### 📊 Cruscotto di Confronto: Ante vs. Post Pianificazione")

    oc1, oc2, oc3, oc4 = st.columns(4)
    with oc1:
        metric_card(
            "Tributi Totali Ante",
            fmt_eur(comp_res.ante_total_taxes_eur),
            delta="Status Quo (Inerzia)",
            delta_color="inverse",
            help_text="Imposta di successione + Ipo-Catastale in assenza di interventi di protezione."
        )
    with oc2:
        metric_card(
            "Tributi Totali Post",
            fmt_eur(comp_res.post_total_taxes_eur),
            delta=f"- € {comp_res.tax_savings_eur:,.0f} (-{comp_res.tax_savings_pct:.1f}%)",
            delta_color="normal",
            help_text="Carico fiscale residuo con le leve di pianificazione attive."
        )
    with oc3:
        metric_card(
            "Liquidità Immediata Eredi",
            fmt_eur(comp_res.immediate_liquidity_generated_eur),
            delta=f"Copertura LCR: {comp_res.liquidity_coverage_ratio:.1f}x",
            delta_color="normal",
            help_text="Liquidità da polizze vita e conti cointestati svincolata dal blocco successorio bancario."
        )
    with oc4:
        metric_card(
            "Score Tutela & Segregazione",
            f"{comp_res.post_protection_score:.0f} / 100",
            delta=f"+{comp_res.post_protection_score - comp_res.ante_protection_score:.0f} Punti vs Ante",
            delta_color="normal",
            help_text="Indice di blindatura giuridica e protezione patrimoniale dai creditori e revocatoria."
        )

    st.write("")

    # Grafico comparativo Ante vs Post
    g_col1, g_col2 = st.columns([1.5, 1.2])
    with g_col1:
        fig_comp = go.Figure()
        categories = ["Imposta Successione", "Imposte Ipo-Catastali", "Carico Fiscale Totale"]
        ante_vals = [comp_res.ante_estate_tax_eur, comp_res.ante_mortgage_cadastral_tax_eur, comp_res.ante_total_taxes_eur]
        post_vals = [comp_res.post_estate_tax_eur, comp_res.post_mortgage_cadastral_tax_eur, comp_res.post_total_taxes_eur]

        fig_comp.add_trace(go.Bar(
            name="Ante-Pianificazione (Status Quo)",
            x=categories,
            y=ante_vals,
            marker_color="#ef4444",
            text=[f"€ {v:,.0f}" for v in ante_vals],
            textposition="auto"
        ))
        fig_comp.add_trace(go.Bar(
            name="Post-Ottimizzazione (Pianificazione Attiva)",
            x=categories,
            y=post_vals,
            marker_color="#10b981",
            text=[f"€ {v:,.0f}" for v in post_vals],
            textposition="auto"
        ))

        fig_comp.update_layout(
            title="Confronto Fiscale: Scenario Ante vs. Post Ottimizzazione",
            barmode="group",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=10, r=10, t=50, b=30),
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
            yaxis=dict(title="Euro (€)", gridcolor="rgba(255,255,255,0.08)")
        )
        st.plotly_chart(fig_comp, use_container_width=True, config={'displayModeBar': False})

    with g_col2:
        st.markdown("##### 🛡️ Diagnosi Lesione di Legittima & Riduzione")
        if comp_res.reduction_risk_mitigated:
            st.success(
                "🟢 **Scudo Totale Attivo (Patto di Famiglia ex Art. 768-bis c.c.)**:\n\n"
                "I beni aziendali e le quote trasferite con patto di famiglia sono **esenti da collazione e da azione di riduzione** (art. 768-quater c. 4 c.c.). "
                "Eventuali liti tra fratelli o con il coniuge sono prevenute per legge."
            )
        else:
            st.info(
                "ℹ️ **Monitoraggio Quota di Riserva**:\n\n"
                "In caso di donazioni consistenti, verificare che non sia superata la quota disponibile (€ "
                f"{estate['val_disponibile']:,.0f}) per evitare azioni di riduzione ex art. 553 c.c. da parte dei legittimari."
            )

        st.markdown("##### 📋 Raccomandazioni Operative del Family Office")
        for rec in comp_res.executive_recommendations:
            st.markdown(f"- {rec}")

    # Expander per Memorandum Istituzionale
    st.write("")
    with st.expander("🏛️ Visualizza Memorandum Istituzionale di Pianificazione Successoria HNWI (Markdown / Export)", expanded=False):
        memo_text = GenerationalTransferOptimizer.generate_executive_succession_memo(comp_res, family_prof)
        st.markdown(memo_text)
        st.download_button(
            label="📥 Scarica Memorandum Successorio (.md)",
            data=memo_text,
            file_name=f"ARGUS_Executive_Succession_Memo_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            use_container_width=True
        )


with tab_shield:
    st.markdown("### 🛡️ Asset Protection, Trust & Holding Familiare Simulator")
    st.caption("Analisi quantitativa e giuridica per la segregazione dei rischi patrimoniali, la protezione dai creditori e la pianificazione tramite Trust o Società Semplice (S.s.).")

    summary_prot_dict = {
        "total_net_worth": float(getattr(nw, "total_net_worth", estate.get("total_wealth", 1000000.0))),
        "real_estate_total": float(getattr(nw, "real_estate_total", 0.0)),
        "financial_investments": float(getattr(nw, "financial_investments", 0.0)),
        "physical_assets": float(getattr(nw, "physical_assets", 0.0))
    }

    prot_res = AssetProtectionEngine.evaluate_protection_matrix(summary_prot_dict)

    pk1, pk2, pk3, pk4 = st.columns(4)
    with pk1:
        metric_card("Fondo Patrimoniale (167 c.c.)", "Score 65 / 100", delta="Protezione Media", delta_color="normal")
    with pk2:
        metric_card("Holding Società Semplice", "Score 85 / 100", delta=f"PEX Risparmio: € {prot_res['estimated_annual_pex_savings']:,.0f}/y", delta_color="normal")
    with pk3:
        metric_card("Trust Familiare (Aja 1985)", "Score 92 / 100", delta="Segregazione Totale", delta_color="normal")
    with pk4:
        metric_card("Scudo Revocatoria", "5 Anni (2901 c.c.)", delta="Consolidamento Giuridico", delta_color="normal")

    st.write("")
    st.markdown("##### 🏛️ Confronto Strutturale dei Veicoli di Protezione")
    st.dataframe(
        prot_res["comparison_df"],
        use_container_width=True,
        hide_index=True
    )

    st.write("")
    c_veh1, c_veh2, c_veh3 = st.columns(3)
    with c_veh1:
        fp_item = prot_res["fondo_patrimoniale"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-left: 4px solid #38bdf8; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#38bdf8; font-size:14px;">{fp_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{fp_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {fp_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {fp_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {fp_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {fp_item.key_advantages[0]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{fp_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_veh2:
        ss_item = prot_res["societa_semplice"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(52, 211, 153, 0.25); border-left: 4px solid #34d399; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#34d399; font-size:14px;">{ss_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{ss_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {ss_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {ss_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {ss_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {ss_item.key_advantages[1]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{ss_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_veh3:
        tr_item = prot_res["trust"]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.9) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(167, 139, 250, 0.25); border-left: 4px solid #a78bfa; border-radius: 12px; padding: 16px; min-height: 280px;">
            <b style="color:#a78bfa; font-size:14px;">{tr_item.vehicle_name}</b><br>
            <span style="font-size:11px; color:#8b949e;">{tr_item.legal_basis}</span>
            <div style="margin: 8px 0; font-size:12px; color:#cbd5e1;">
                <b>Livello Tutela:</b> {tr_item.creditor_shield_level}<br>
                <b>Costi Costituzione:</b> {tr_item.setup_cost_range_eur}<br>
                <b>Costi Annui:</b> {tr_item.annual_maintenance_eur}
            </div>
            <div style="font-size:11.5px; color:#94a3b8;">
                <b>Vantaggio Chiave:</b> {tr_item.key_advantages[0]}<br>
                <b>Vulnerabilità:</b> <span style="color:#f87171;">{tr_item.critical_vulnerabilities[0]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab_patto:
    st.markdown("### 🏛️ Family Governance & Patti di Famiglia (Art. 768-bis c.c.)")
    st.caption("Pianificazione del passaggio del controllo aziendale e societario, calcolo della compensazione liquidatoria per i legittimari non assegnatari e scudo contro future azioni di riduzione.")

    biz_val_calc = float(getattr(nw, "total_net_worth", estate.get("total_wealth", 2000000.0)))
    gov_data = compute_family_governance_and_patti_di_famiglia(
        engine,
        portfolio_id=current_pid,
        business_value_eur=biz_val_calc if biz_val_calc > 100000 else 2000000.0,
        heir_count=num_children,
        has_spouse=has_spouse
    )

    gk1, gk2, gk3, gk4 = st.columns(4)
    with gk1:
        metric_card("Valore Azienda / Holding", fmt_eur(gov_data["business_value_eur"]), delta="Asset Oggetto del Patto", delta_color="normal")
    with gk2:
        metric_card("Erede Designato", gov_data["assigned_heir_name"], delta=f"{gov_data['assigned_quota_pct']:.0f}% Quote Trasferite", delta_color="normal")
    with gk3:
        metric_card("Liquidazione Legittimari", fmt_eur(gov_data["total_compensation_due_eur"]), delta="Compensazione non Assegnatari", delta_color="normal")
    with gk4:
        metric_card("Scudo Riduzione/Collazione", "ATTIVO 🟢", delta="Immunità Ereditaria Blindata", delta_color="normal")

    st.write("")

    g_col_l, g_col_r = st.columns([3, 2])
    with g_col_l:
        st.markdown("##### 👥 Prospetto Liquidazione Legittimari non Assegnatari")
        df_heirs = pd.DataFrame(gov_data["non_assigned_heirs"])
        if not df_heirs.empty:
            st.dataframe(
                df_heirs[["heir_name", "relationship", "statutory_legitimate_share_pct", "compensation_due_eur", "payment_method"]].rename(columns={
                    "heir_name": "Soggetto Legittimario",
                    "relationship": "Grado Parentela",
                    "statutory_legitimate_share_pct": "Quota Riserva (%)",
                    "compensation_due_eur": "Compensazione Dovuta (€)",
                    "payment_method": "Modalità di Regolamento"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("##### 📅 Piano di Donazioni Scaglionate su Orizzonte Pluriennale")
        st.dataframe(
            pd.DataFrame(gov_data["staggered_donations_schedule"]).rename(columns={
                "anno": "Anno",
                "importo_donato_eur": "Importo Donato (€)",
                "franchigia_usata_eur": "Franchigia Utilizzata (€)",
                "imposta_donazione_eur": "Imposta Donazione (€)",
                "note": "Note Operative"
            }),
            use_container_width=True,
            hide_index=True
        )

    with g_col_r:
        st.markdown("##### 📋 Checklist di Conformità Notarile")
        for chk in gov_data["governance_checklist"]:
            st.info(f"⚖️ {chk}")
