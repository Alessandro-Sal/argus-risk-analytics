# ==============================================================================
# core/watchdog/unified_notification_center.py
# ARGUS — Unified Enterprise Risk & Wealth Notification Hub
# Omnipresent Compliance, Limit Breaches & Early Warning Sentinel
# ==============================================================================

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from core.risk_limits import check_risk_limits
from core.sidebar import switch_to_page
from core.wealth.wealth_watchdog import WealthWatchdog


@dataclass
class UnifiedNotification:
    """Rappresenta una notifica unificata istituzionale (Risk o Wealth)."""

    notification_id: str
    source: str  # 'RISK', 'WEALTH', 'MACRO'
    severity: str  # 'CRITICAL', 'WARNING', 'INFO', 'OPTIMAL'
    category: str
    title: str
    message: str
    current_value: Optional[float] = None
    limit_value: Optional[float] = None
    unit: str = ""
    impact_amount: float = 0.0
    suggested_action: str = ""
    target_page: str = "0_Control_Room.py"
    target_tab: Optional[str] = None
    action_label: str = "Ispeziona →"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_active_analysis(
    risk_data: Optional[Dict[str, Any]] = None,
    wealth_snapshot: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Determina se è presente un'analisi di portafoglio attiva (Risk o Wealth).
    Verifica parametri espliciti o presenza di dati reali nello stato di sessione.
    """
    # 1. Controllo esplicito risk_data
    if isinstance(risk_data, dict) and bool(risk_data):
        pos = risk_data.get("positions")
        if pos is not None:
            if isinstance(pos, pd.DataFrame):
                if not pos.empty:
                    return True
            elif isinstance(pos, (list, dict)) and len(pos) > 0:
                return True
        if (
            risk_data.get("metrics")
            or risk_data.get("returns") is not None
            or risk_data.get("portfolio_beta") is not None
            or risk_data.get("var_95_hist") is not None
        ):
            return True

    # 2. Controllo esplicito wealth_snapshot
    if isinstance(wealth_snapshot, dict) and bool(wealth_snapshot):
        if bool(
            wealth_snapshot.get("total_net_worth")
            or wealth_snapshot.get("assets")
            or wealth_snapshot.get("accounts")
            or wealth_snapshot.get("liabilities")
            or wealth_snapshot.get("liquid_cash")
            or wealth_snapshot.get("monthly_expenses")
        ):
            return True

    # 3. Controllo session_state Streamlit
    try:
        if st.session_state.get("pipeline_done", False):
            return True

        res = (
            st.session_state.get("results")
            or st.session_state.get("risk_bundle")
            or st.session_state.get("portfolio_results")
        )
        if isinstance(res, dict) and bool(res):
            pos = res.get("positions")
            if pos is not None:
                if isinstance(pos, pd.DataFrame):
                    if not pos.empty:
                        return True
                elif isinstance(pos, (list, dict)) and len(pos) > 0:
                    return True
            if res.get("metrics") or res.get("returns") is not None:
                return True

        w_snap = st.session_state.get("wealth_snapshot")
        if isinstance(w_snap, dict) and bool(w_snap):
            if bool(
                w_snap.get("total_net_worth")
                or w_snap.get("assets")
                or w_snap.get("accounts")
                or w_snap.get("liquid_cash")
            ):
                return True
    except Exception:
        pass

    return False


def get_unified_compliance_notifications(
    risk_data: Optional[Dict[str, Any]] = None,
    wealth_snapshot: Optional[Dict[str, Any]] = None,
    custom_limits: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Raccoglie e unifica in tempo reale tutti i warning e le violazioni di compliance:
    1. Risk Appetite Framework (VaR 95%, Concentrazione Titoli/Settori, Beta, HHI)
    2. Wealth Watchdog (Minusvalenze in scadenza, Runway di emergenza, LTV mutui, Pensione, Spese)
    3. Global Macro Stress Bridge (se uno shock sistemico è attivo nel terminale)
    """
    # Auto-rilevamento contesto se non passato esplicitamente
    if risk_data is None:
        try:
            risk_data = (
                st.session_state.get("results")
                or st.session_state.get("risk_bundle")
                or st.session_state.get("portfolio_results")
            )
        except Exception:
            pass

    if wealth_snapshot is None:
        try:
            wealth_snapshot = st.session_state.get("wealth_snapshot")
        except Exception:
            pass

    has_active_analysis = check_active_analysis(risk_data=risk_data, wealth_snapshot=wealth_snapshot)

    notifications: List[UnifiedNotification] = []

    # Solo se un'analisi è effettivamente attiva procediamo alla valutazione dei limiti
    if has_active_analysis:
        # ── 1. VERIFICA LIMITI RISK APPETITE (RISK PORTAL) ───────────────────────
        if risk_data:
            try:
                limits_res = check_risk_limits(risk_data, custom_limits=custom_limits)
                eval_df = limits_res.get("evaluations", pd.DataFrame())
                if isinstance(eval_df, pd.DataFrame) and not eval_df.empty:
                    for _, row in eval_df.iterrows():
                        st_val = str(row.get("status", "PASS")).upper()
                        if st_val in ["BREACH", "WARNING"]:
                            is_crit = st_val == "BREACH"
                            sev = "CRITICAL" if is_crit else "WARNING"
                            r_name = str(row.get("rule_name", "Limite di Rischio"))
                            c_val = float(row.get("current_value", 0.0))
                            l_val = float(row.get("limit_threshold", 0.0))
                            u_str = str(row.get("unit", ""))

                            action_text = (
                                "Ribilanciare il portafoglio o attivare coperture per ridurre l'esposizione."
                                if is_crit
                                else "Monitorare la metrica o valutare una riduzione tattica."
                            )

                            notifications.append(
                                UnifiedNotification(
                                    notification_id=f"risk_lim_{row.get('key', 'rule')}",
                                    source="RISK",
                                    severity=sev,
                                    category="RISK_LIMIT",
                                    title=f"{'🔴' if is_crit else '🟡'} Violazione: {r_name}",
                                    message=f"Valore rilevato {c_val:.2f}{u_str} rispetto alla soglia di mandato {l_val:.2f}{u_str}.",
                                    current_value=c_val,
                                    limit_value=l_val,
                                    unit=u_str,
                                    suggested_action=action_text,
                                    target_page="pages/3_🔴_Analisi_Rischio.py",
                                    action_label="Apri Modulo Rischio →",
                                )
                            )
            except Exception:
                pass

        # ── 2. VERIFICA WEALTH WATCHDOG (WEALTH PORTAL) ──────────────────────────
        if wealth_snapshot:
            try:
                w_alerts = WealthWatchdog.evaluate_all_alerts(
                    summary_data=wealth_snapshot,
                    cf_analytics=wealth_snapshot.get("cf_analytics"),
                    fiscal_data=wealth_snapshot.get("fiscal_data"),
                )
                for wa in w_alerts:
                    if wa.severity in ["CRITICAL", "WARNING"]:
                        notifications.append(
                            UnifiedNotification(
                                notification_id=f"wealth_{wa.alert_id}",
                                source="WEALTH",
                                severity=wa.severity,
                                category=wa.category,
                                title=f"{'🔴' if wa.severity == 'CRITICAL' else '🟡'} {wa.title}",
                                message=wa.message,
                                impact_amount=wa.impact_amount,
                                suggested_action=wa.suggested_action,
                                target_page=wa.target_page,
                                action_label=wa.action_label,
                            )
                        )
            except Exception:
                pass

        # ── 3. VERIFICA GLOBAL MACRO STRESS ATTIVO ──────────────────────────────
        try:
            active_shock = st.session_state.get("global_macro_shock", "NONE")
            if active_shock and str(active_shock).upper() not in ["NONE", "BASELINE", ""]:
                notifications.append(
                    UnifiedNotification(
                        notification_id="macro_stress_active",
                        source="MACRO",
                        severity="WARNING",
                        category="MACRO_STRESS",
                        title=f"🌪️ Macro Shock Globale Attivo: {active_shock}",
                        message=f"I parametri di stress {active_shock} sono correntemente applicati a Risk e Wealth.",
                        suggested_action="Verifica la tenuta del balance sheet o disattiva il preset dal terminale.",
                        target_page="pages/7_🌪️_Stress_Testing.py",
                        action_label="Gestisci Macro Shock →",
                    )
                )
        except Exception:
            pass

    crit_cnt = sum(1 for n in notifications if n.severity == "CRITICAL")
    warn_cnt = sum(1 for n in notifications if n.severity == "WARNING")
    info_cnt = sum(1 for n in notifications if n.severity == "INFO")

    return {
        "total_count": len(notifications),
        "critical_count": crit_cnt,
        "warning_count": warn_cnt,
        "info_count": info_cnt,
        "notifications": notifications,
        "has_active_analysis": has_active_analysis,
    }


def render_institutional_notification_bell(
    risk_data: Optional[Dict[str, Any]] = None,
    wealth_snapshot: Optional[Dict[str, Any]] = None,
    key_suffix: str = "omni",
    only_when_loaded: bool = False,
) -> None:
    """
    Renderizza il campanello di notifica istituzionale per la command bar.
    Mostra un popover con badge dinamico e visualizzazione di tutti gli alert attivi.
    Se only_when_loaded=True e non ci sono analisi caricate, non viene renderizzato.
    Se non ci sono analisi attive e only_when_loaded=False, mostra lo stato 'STANDBY'.
    """
    # Auto-rilevamento contesto se non passato esplicitamente
    if risk_data is None:
        try:
            risk_data = (
                st.session_state.get("results")
                or st.session_state.get("risk_bundle")
                or st.session_state.get("portfolio_results")
            )
        except Exception:
            pass

    if wealth_snapshot is None:
        try:
            wealth_snapshot = st.session_state.get("wealth_snapshot")
        except Exception:
            pass

    data = get_unified_compliance_notifications(risk_data=risk_data, wealth_snapshot=wealth_snapshot)
    has_active_analysis = data.get("has_active_analysis", False)

    # Se richiesto di mostrare solo con analisi attiva e nessuna analisi è presente, esci senza renderizzare
    if only_when_loaded and not has_active_analysis:
        return

    # CASO 1: NESSUNA ANALISI ATTIVA (STATO STANDBY)
    if not has_active_analysis:
        btn_label = "🔔 Standby"
        btn_help = (
            "Sentinel in Standby: In attesa di caricamento o selezione di un portafoglio per attivare il monitoraggio RAF."
        )

        with st.popover(btn_label, help=btn_help, use_container_width=False):
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.98) 0%, rgba(13, 17, 23, 1) 100%);
                            border-bottom: 2px solid #64748b; padding: 6px 10px 10px 10px; margin-bottom: 10px;">
                    <div style="font-size: 13px; font-weight: 800; color: #94a3b8; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between;">
                        <span>🔔 COMPLIANCE &amp; RISK SENTINEL</span>
                        <span style="font-size: 10px; font-family: monospace; background: rgba(148,163,184,0.15); color: #cbd5e1; padding: 2px 6px; border-radius: 4px;">
                            STANDBY
                        </span>
                    </div>
                    <div style="font-size: 11px; color: #8b949e; margin-top: 3px;">
                        In attesa di caricamento portafoglio per attivare il Risk Appetite Framework (RAF).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_c, col_w, col_ok = st.columns(3)
            with col_c:
                st.markdown(
                    """<div style="background:rgba(148,163,184,0.08); border:1px solid rgba(148,163,184,0.2); border-radius:6px; padding:6px; text-align:center;">
                        <div style="font-size:16px; font-weight:800; color:#64748b;">—</div>
                        <div style="font-size:9.5px; font-weight:700; color:#94a3b8; text-transform:uppercase;">Critici</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_w:
                st.markdown(
                    """<div style="background:rgba(148,163,184,0.08); border:1px solid rgba(148,163,184,0.2); border-radius:6px; padding:6px; text-align:center;">
                        <div style="font-size:16px; font-weight:800; color:#64748b;">—</div>
                        <div style="font-size:9.5px; font-weight:700; color:#94a3b8; text-transform:uppercase;">Warning</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_ok:
                st.markdown(
                    """<div style="background:rgba(148,163,184,0.08); border:1px solid rgba(148,163,184,0.2); border-radius:6px; padding:6px; text-align:center;">
                        <div style="font-size:16px; font-weight:800; color:#94a3b8;">PAUSA</div>
                        <div style="font-size:9.5px; font-weight:700; color:#94a3b8; text-transform:uppercase;">In Standby</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            st.markdown(
                """
                <div style="padding: 14px; text-align: center; color: #94a3b8; font-size: 11.5px; background: rgba(148,163,184,0.06); border-radius: 8px; border: 1px dashed rgba(148,163,184,0.3); margin-top: 10px; line-height: 1.45;">
                    ⏳ <b>Sentinel in Standby</b><br>
                    Nessuna analisi attiva in sessione. Il monitoraggio continuo dei limiti di rischio (VaR 95%, concentrazione titoli, liquidità) e salvaguardia patrimoniale si attiveranno automaticamente dopo aver caricato un portafoglio.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button(
                "📁 Vai a Caricamento / Recall Analisi →",
                key=f"bell_goto_load_{key_suffix}",
                use_container_width=True,
            ):
                switch_to_page("0_Control_Room.py")
        return

    # CASO 2: ANALISI ATTIVA (MONITORAGGIO REAL-TIME OPERATIVO)
    tot = data["total_count"]
    crits = data["critical_count"]
    warns = data["warning_count"]

    if crits > 0:
        btn_label = f"🔔 {tot} ALERT"
        btn_help = f"Centro Notifiche: {crits} Violazioni Critiche e {warns} Warning attivi"
    elif warns > 0:
        btn_label = f"🔔 {tot}"
        btn_help = f"Centro Notifiche: {warns} Segnalazioni di attenzione attive"
    else:
        btn_label = "🔔 0"
        btn_help = "Centro Notifiche: Nessuna violazione o alert attivo. Parametri entro i limiti di mandato."

    with st.popover(btn_label, help=btn_help, use_container_width=False):
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.98) 0%, rgba(13, 17, 23, 1) 100%);
                        border-bottom: 2px solid #ff9900; padding: 6px 10px 10px 10px; margin-bottom: 10px;">
                <div style="font-size: 13px; font-weight: 800; color: #ff9900; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between;">
                    <span>🔔 COMPLIANCE &amp; RISK SENTINEL</span>
                    <span style="font-size: 10px; font-family: monospace; background: rgba(255,153,0,0.15); color: #ffb74d; padding: 2px 6px; border-radius: 4px;">
                        REAL-TIME RAF
                    </span>
                </div>
                <div style="font-size: 11px; color: #8b949e; margin-top: 3px;">
                    Monitoraggio congiunto di limiti di portafoglio, salvaguardia fiscale e liquidità patrimoniale.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_c, col_w, col_ok = st.columns(3)
        with col_c:
            st.markdown(
                f"""<div style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:6px; text-align:center;">
                    <div style="font-size:16px; font-weight:800; color:#ef4444;">{crits}</div>
                    <div style="font-size:9.5px; font-weight:700; color:#f87171; text-transform:uppercase;">Critici</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_w:
            st.markdown(
                f"""<div style="background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:6px; padding:6px; text-align:center;">
                    <div style="font-size:16px; font-weight:800; color:#f59e0b;">{warns}</div>
                    <div style="font-size:9.5px; font-weight:700; color:#fbbf24; text-transform:uppercase;">Warning</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_ok:
            st.markdown(
                """<div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:6px; padding:6px; text-align:center;">
                    <div style="font-size:16px; font-weight:800; color:#10b981;">OK</div>
                    <div style="font-size:9.5px; font-weight:700; color:#34d399; text-transform:uppercase;">RAF Active</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        if not data["notifications"]:
            st.markdown(
                """
                <div style="padding: 14px; text-align: center; color: #10b981; font-size: 12px; background: rgba(16,185,129,0.06); border-radius: 8px; border: 1px dashed rgba(16,185,129,0.3);">
                    ✅ <b>Tutti i limiti sono rispettati</b><br>
                    Nessun breach di VaR, concentrazione o liquidità rilevato.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for idx, n in enumerate(data["notifications"][:8]):
                bd_color = "#ef4444" if n.severity == "CRITICAL" else "#f59e0b"
                bg_color = "rgba(239, 68, 68, 0.08)" if n.severity == "CRITICAL" else "rgba(245, 158, 11, 0.08)"

                st.markdown(
                    f"""
                    <div style="background: {bg_color}; border-left: 3px solid {bd_color}; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 11.5px; font-weight: 700; color: #ffffff;">{n.title}</span>
                            <span style="font-size: 9px; font-family: monospace; background: rgba(0,0,0,0.4); padding: 1px 5px; border-radius: 3px; color: #94a3b8;">{n.source}</span>
                        </div>
                        <div style="font-size: 11px; color: #cbd5e1; margin-top: 3px; line-height: 1.35;">
                            {n.message}
                        </div>
                        <div style="font-size: 10px; color: #94a3b8; font-style: italic; margin-top: 3px;">
                            💡 {n.suggested_action}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                col_btn_l, col_btn_r = st.columns([1, 1])
                with col_btn_r:
                    if st.button(
                        n.action_label,
                        key=f"bell_jump_{key_suffix}_{idx}_{n.notification_id}",
                        use_container_width=True,
                    ):
                        switch_to_page(n.target_page)
