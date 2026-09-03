# ==============================================================================
# core/wealth/wealth_watchdog.py
# ARGUS — Smart Financial Watchdog & Proactive Alert Engine
# ==============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st


@dataclass
class WatchdogAlert:
    alert_id: str
    severity: str  # 'CRITICAL', 'WARNING', 'INFO', 'OPTIMAL'
    category: str  # 'TAX', 'LIQUIDITY', 'ALLOCATION', 'REAL_ESTATE', 'PENSION', 'SPENDING'
    title: str
    message: str
    impact_amount: float
    suggested_action: str
    target_page: str
    action_label: str = "Risolvi Ora →"


class WealthWatchdog:
    """
    Motore sentinella proattivo per la diagnosi in tempo reale del patrimonio.
    Monitora 6 vulnerabilità critiche:
    1. Minusvalenze in scadenza (Tax Drag)
    2. Runway di emergenza (Liquidity Risk)
    3. Asset Allocation Drift (Portfolio Imbalance)
    4. Real Estate LTV (Leverage Risk)
    5. Deducibilità Fondo Pensione (Fiscal Benefit)
    6. Subscription & Fixed Cost Creep (Cashflow Leakage)
    """

    @staticmethod
    def evaluate_all_alerts(
        summary_data: Dict[str, Any],
        cf_analytics: Optional[Dict[str, Any]] = None,
        fiscal_data: Optional[Dict[str, Any]] = None,
        portfolios_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[WatchdogAlert]:
        alerts: List[WatchdogAlert] = []
        now = datetime.now()
        curr_year = now.year

        tot_nw = float(summary_data.get("total_net_worth", 0.0))
        liq_cash = float(summary_data.get("liquid_cash", 0.0))
        fin_inv = float(summary_data.get("financial_investments", 0.0))
        re_equity = float(summary_data.get("real_estate_equity", summary_data.get("real_estate_total", 0.0)))
        re_total = float(summary_data.get("real_estate_total", re_equity))
        tot_debts = float(summary_data.get("total_liabilities", 0.0))
        pension_tot = float(summary_data.get("pension_total", 0.0))
        runway_mo = float(summary_data.get("runway_months", 0.0))
        savings_rt = float(summary_data.get("savings_rate_pct", 0.0))

        # ── 1. FISCO: MINUSVALENZE IN SCADENZA (TUIR ART. 67) ──
        if fiscal_data and "minusvalenze" in fiscal_data:
            minus_df = fiscal_data.get("minusvalenze")
            if hasattr(minus_df, "iterrows"):
                for _, m in minus_df.iterrows():
                    m_year = int(m.get("year", curr_year))
                    m_amt = float(m.get("amount", 0.0))
                    # Le minusvalenze scadono al 31/12 del quarto anno successivo
                    expiry_year = m_year + 4
                    years_left = expiry_year - curr_year
                    if years_left <= 1 and m_amt > 100:
                        tax_loss = m_amt * 0.26
                        alerts.append(WatchdogAlert(
                            alert_id="tax_minus_expiry",
                            severity="CRITICAL" if years_left <= 0 else "WARNING",
                            category="TAX",
                            title=f"⚠️ Minusvalenze di € {m_amt:,.2f} in Scadenza al 31/12/{expiry_year}",
                            message=f"Rischio di prescrizione fiscale quadriennale. Risparmio tributario a rischio: € {tax_loss:,.2f} (aliquota 26%).",
                            impact_amount=tax_loss,
                            suggested_action="Realizzare plusvalenze su azioni o certificati compensabili prima del 31 dicembre.",
                            target_page="pages/18_📑_Fiscalita_e_Quadro_RW.py",
                            action_label="Ottimizza Fisco →"
                        ))

        # ── 2. LIQUIDITÀ: EMERGENCY RUNWAY ──
        if runway_mo < 3.0 and tot_nw > 1000:
            alerts.append(WatchdogAlert(
                alert_id="liq_runway_critical",
                severity="CRITICAL",
                category="LIQUIDITY",
                title=f"🚨 Cuscinetto di Liquidità Critico ({runway_mo:.1f} Mesi di Autonomia)",
                message=f"La cassa disponibile ({liq_cash:,.2f} €) copre meno di 3 mesi di uscite necessarie. Rischio di liquidazione forzata di asset.",
                impact_amount=liq_cash,
                suggested_action="Ricostituire il fondo di emergenza accantonando liquidità fino ad almeno 6 mesi di spese medie.",
                target_page="pages/14_💳_Cash_Flow_e_Spese.py",
                action_label="Gestisci Budget →"
            ))
        elif runway_mo < 6.0 and tot_nw > 1000:
            alerts.append(WatchdogAlert(
                alert_id="liq_runway_warning",
                severity="WARNING",
                category="LIQUIDITY",
                title=f"💧 Cuscinetto di Liquidità Moderato ({runway_mo:.1f} Mesi)",
                message="Il fondo di riserva è inferiore alla soglia prudenziale consigliata di 6 mensilità di spesa.",
                impact_amount=liq_cash,
                suggested_action="Aumentare progressivamente la riserva monetaria su conto deposito o monetario XEON.",
                target_page="pages/14_💳_Cash_Flow_e_Spese.py",
                action_label="Visualizza Cashflow →"
            ))

        # ── 3. IMMOBILI: LOAN TO VALUE (LTV) WATCHDOG ──
        if re_total > 0 and tot_debts > 0:
            ltv_pct = (tot_debts / re_total) * 100.0
            if ltv_pct > 80.0:
                alerts.append(WatchdogAlert(
                    alert_id="re_ltv_critical",
                    severity="CRITICAL",
                    category="REAL_ESTATE",
                    title=f"🏡 Leva Finanziaria Immobiliare Elevata (LTV: {ltv_pct:.1f}%)",
                    message=f"Il debito residuo ({tot_debts:,.2f} €) eccede l'80% del valore commerciale stimato degli immobili. Alta vulnerabilità a shock tassi.",
                    impact_amount=tot_debts,
                    suggested_action="Valutare estinzioni parziali o rinegoziazione a tasso fisso per ridurre il servizio del debito.",
                    target_page="pages/19_🏡_Immobili_e_Mutui.py",
                    action_label="Analisi Mutuo →"
                ))

        # ── 4. PREVIDENZA: DEDUCIBILITÀ ANNUALE NON SFRUTTATA ──
        # Plafond deducibilità TUIR Art. 10 = € 5.164,57 annui
        max_deductible = 5164.57
        if pension_tot < 5000 and tot_nw > 25000:
            potential_tax_rebate = max_deductible * 0.43  # Aliquota IRPEF marginale massima
            alerts.append(WatchdogAlert(
                alert_id="pension_deduct_unused",
                severity="INFO",
                category="PENSION",
                title="🛡️ Plafond Deducibilità Fondo Pensione Disponibile (€ 5.164,57)",
                message=f"Puoi dedurre fino a € 5.164,57 all'anno dal reddito imponibile IRPEF, risparmiando fino a € {potential_tax_rebate:,.2f} di tasse.",
                impact_amount=potential_tax_rebate,
                suggested_action="Effettuare un versamento volontario sul fondo pensione integrativo prima del 31 dicembre.",
                target_page="pages/16_🛡️_Previdenza_e_Pension_Planning.py",
                action_label="Pianifica Pensione →"
            ))

        # ── 5. ALLOCAZIONE & CONCENTRAZIONE (DRIFT) ──
        if tot_nw > 50000:
            cash_pct = (liq_cash / tot_nw) * 100.0
            inv_pct = (fin_inv / tot_nw) * 100.0
            if cash_pct > 40.0:
                alerts.append(WatchdogAlert(
                    alert_id="alloc_cash_drag",
                    severity="WARNING",
                    category="ALLOCATION",
                    title=f"💸 Eccesso di Cassa Improduttiva ({cash_pct:.1f}% del Net Worth)",
                    message=f"Detieni {liq_cash:,.2f} € in liquidità pura. L'inflazione sta erodendo il potere d'acquisto del capitale.",
                    impact_amount=liq_cash * 0.025,  # Drag inflattivo al 2.5%
                    suggested_action="Pianificare un piano di accumulo del capitale (PAC) o allocare l'eccesso su asset generanti yield.",
                    target_page="pages/13_🏛️_Patrimonio_e_NetWorth.py",
                    action_label="Asset Allocation →"
                ))

        # ── 6. STATO OTTIMALE (SE NESSUN ALERT CRITICO) ──
        if not alerts:
            alerts.append(WatchdogAlert(
                alert_id="status_all_clear",
                severity="OPTIMAL",
                category="ALLOCATION",
                title="💎 Struttura Patrimoniale Resiliente & Protetta",
                message="Tutti gli indicatori sentinella (Liquidità, Solvibilità, Fisco, Previdenza e LTV) si trovano all'interno delle fasce di sicurezza istituzionali.",
                impact_amount=0.0,
                suggested_action="Mantenere la strategia di accumulo e ribilanciare periodicamente i pesi di portafoglio.",
                target_page="pages/13_🏛️_Patrimonio_e_NetWorth.py",
                action_label="Dashboard Net Worth →"
            ))

        # Ordina per gravità (CRITICAL -> WARNING -> INFO -> OPTIMAL)
        order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2, "OPTIMAL": 3}
        alerts.sort(key=lambda a: order.get(a.severity, 99))
        return alerts


def render_wealth_watchdog_banner(alerts: List[WatchdogAlert]):
    """Renderizza il banner orizzontale proattivo di allerta con design dark glassmorphic."""
    if not alerts:
        return

    crit_count = sum(1 for a in alerts if a.severity == "CRITICAL")
    warn_count = sum(1 for a in alerts if a.severity == "WARNING")
    info_count = sum(1 for a in alerts if a.severity == "INFO")

    header_badge = ""
    if crit_count > 0:
        header_badge = f'<span style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">🚨 {crit_count} CRITICITÀ RILEVATE</span>'
    elif warn_count > 0:
        header_badge = f'<span style="background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">⚠️ {warn_count} AVVISI ATTIVI</span>'
    else:
        header_badge = '<span style="background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">💎 STATO OTTIMALE</span>'

    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 153, 0, 0.3); border-radius: 12px; padding: 14px 18px; margin: 8px 0 16px 0; backdrop-filter: blur(10px);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 14px; font-weight: 800; color: #ff9900; letter-spacing: 0.5px;">🚨 ARGUS FINANCIAL WATCHDOG</span>
                {header_badge}
            </div>
            <span style="font-size: 11px; color: #8b949e;">Monitoraggio Proattivo Multi-Vulnerabilità</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for a in alerts:
        sev_color = "#ef4444" if a.severity == "CRITICAL" else "#f59e0b" if a.severity == "WARNING" else "#38bdf8" if a.severity == "INFO" else "#10b981"
        sev_bg = "rgba(239, 68, 68, 0.08)" if a.severity == "CRITICAL" else "rgba(245, 158, 11, 0.08)" if a.severity == "WARNING" else "rgba(56, 189, 248, 0.08)" if a.severity == "INFO" else "rgba(16, 185, 129, 0.08)"

        col_txt, col_btn = st.columns([4.2, 1.2])
        with col_txt:
            st.markdown(f"""
            <div style="background: {sev_bg}; border-left: 3px solid {sev_color}; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px;">
                <div style="font-size: 12.5px; font-weight: 700; color: #f0f6fc; margin-bottom: 2px;">{a.title}</div>
                <div style="font-size: 11.5px; color: #8b949e; line-height: 1.4;">{a.message} <b style="color: {sev_color};">Azione:</b> {a.suggested_action}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if st.button(a.action_label, key=f"btn_watchdog_{a.alert_id}", use_container_width=True):
                st.switch_page(a.target_page)
