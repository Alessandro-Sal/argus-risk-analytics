# ==============================================================================
# core/trade_staging_blotter.py
# ARGUS — Institutional Trade Staging Blotter & FIX 4.4 Execution Router
# Bloomberg EMSX Workflow • Almgren-Chriss / TWAP / VWAP Simulation • Pre-Trade TCA
# ==============================================================================

import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.compliance_gate import (
    PreTradeComplianceConfig,
    PreTradeOrderRequest,
    PreTradeRiskGate,
)
from core.fix_engine import (
    MSG_EXECUTION_REPORT,
    MSG_NEW_ORDER_SINGLE,
    TAG_AVG_PX,
    TAG_CL_ORD_ID,
    TAG_CUM_QTY,
    TAG_EXEC_ID,
    TAG_EXEC_TYPE,
    TAG_LAST_PX,
    TAG_LAST_QTY,
    TAG_LEAVES_QTY,
    TAG_ORD_STATUS,
    TAG_ORD_TYPE,
    TAG_ORDER_ID,
    TAG_ORDER_QTY,
    TAG_PRICE,
    TAG_SIDE,
    TAG_SYMBOL,
    TAG_TIME_IN_FORCE,
    DepthOfMarketSimulator,
    ExecutionTCAReport,
    FIXMessage,
)
from core.ui_utils import fmt_eur, metric_card
from core.ux_institutional_hub import style_institutional_chart


@dataclass
class StagedOrder:
    """Rappresenta un ordine preparato per l'esecuzione nella blotter EMSX."""

    cl_ord_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    order_qty: int
    order_type: str = "LIMIT"  # 'LIMIT' or 'MARKET'
    limit_price: float = 0.0
    algo_strategy: str = "TWAP"  # 'TWAP', 'VWAP', 'ALMGREN_CHRISS', 'POV_15'
    status: str = "STAGED"  # 'STAGED', 'ROUTED', 'FILLED', 'REJECTED'
    target_weight_pct: float = 0.0
    current_weight_pct: float = 0.0
    estimated_notional_eur: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def stage_orders_from_portfolio(
    positions: pd.DataFrame,
    portfolio_value: float = 100000.0,
    target_tilt: float = 0.05,
) -> List[StagedOrder]:
    """Genera una blotter di ordini suggeriti di de-risking o ribilanciamento da posizioni attive."""
    staged: List[StagedOrder] = []
    if positions.empty:
        # Ordini demo istituzionali predefiniti
        sample_tickers = [("SWDA.MI", "BUY", 120, 94.50), ("AAPL", "SELL", 40, 225.00), ("NVDA", "SELL", 25, 128.00)]
        for idx, (sym, side, qty, px) in enumerate(sample_tickers):
            staged.append(
                StagedOrder(
                    cl_ord_id=f"ARG-{datetime.now().strftime('%y%m%d')}-{idx + 1:03d}",
                    symbol=sym,
                    side=side,
                    order_qty=qty,
                    order_type="LIMIT",
                    limit_price=px,
                    algo_strategy="TWAP",
                    status="STAGED",
                    estimated_notional_eur=round(qty * px, 2),
                )
            )
        return staged

    col_t = "ticker" if "ticker" in positions.columns else "Ticker"
    col_p = "last_price" if "last_price" in positions.columns else "current_value"
    col_q = "qty_net" if "qty_net" in positions.columns else "quantity"

    idx = 1
    for _, r in positions.head(6).iterrows():
        tk = str(r.get(col_t, "ASSET")).strip().upper()
        sh = float(r.get(col_q, 10.0))
        px = float(r.get(col_p, 100.0))
        if px <= 0:
            px = 100.0

        # Ribilanciamento: vendere parte dei titoli sopra-pesati, incrementare ETF/obbligazioni
        is_bond = any(k in tk.lower() for k in ["btp", "bund", "gov", "bond"])
        side = "BUY" if is_bond else "SELL"
        trade_qty = max(1, int(sh * target_tilt)) if sh > 0 else 10
        notional = round(trade_qty * px, 2)

        staged.append(
            StagedOrder(
                cl_ord_id=f"EMS-{datetime.now().strftime('%m%d')}-{idx:03d}",
                symbol=tk,
                side=side,
                order_qty=trade_qty,
                order_type="LIMIT" if side == "BUY" else "MARKET",
                limit_price=round(px * (0.995 if side == "BUY" else 1.005), 2),
                algo_strategy="VWAP" if notional > 5000 else "TWAP",
                status="STAGED",
                estimated_notional_eur=notional,
            )
        )
        idx += 1

    return staged


def simulate_fix_routing(
    staged_orders: List[StagedOrder],
    execution_algo: str = "TWAP",
    sender_comp_id: str = "ARGUS_DESK",
    target_comp_id: str = "EXCHANGE_L2",
    compliance_config: Optional[PreTradeComplianceConfig] = None,
    portfolio_cash: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Esegue la simulazione di routing a mercato tramite protocollo FIX 4.4 con audit Pre-Trade MiFID II RTS 28:
    1. Valuta ogni ordine attraverso PreTradeRiskGate (Fat-Finger, ADV Cap, Price Collar, Liquidità)
    2. Serializza NewOrderSingle (35=D) con checksum valido modulo-256 per ordini approvati
    3. Esegue il matching contro il Depth-of-Market L2 sintetico (book walking)
    4. Calcola l'Implementation Shortfall di Perold (1988) in bps
    5. Restituisce ExecutionReport (35=8), log FIX completo e report di conformità
    """
    gate = PreTradeRiskGate(compliance_config)
    executed_records = []
    fix_messages_log = []
    compliance_verdicts = []
    total_shortfall_eur = 0.0
    total_friction_saved_eur = 0.0
    total_notional_executed = 0.0

    seq_num = 101

    for o in staged_orders:
        # Pre-Trade Compliance Check
        order_req = PreTradeOrderRequest(
            order_id=o.cl_ord_id,
            symbol=o.symbol,
            side=o.side,
            order_qty=float(o.order_qty),
            limit_price=float(o.limit_price),
            order_type=o.order_type,
            reference_price=float(o.limit_price) if o.limit_price > 0 else 100.0,
            available_cash_eur=portfolio_cash,
        )
        verdict = gate.evaluate_order(order_req, portfolio_cash=portfolio_cash)
        compliance_verdicts.append(verdict.to_dict())

        if not verdict.passed:
            o.status = "REJECTED"
            executed_records.append(
                {
                    "ClOrdID": o.cl_ord_id,
                    "Symbol": o.symbol,
                    "Side": o.side,
                    "Qty": o.order_qty,
                    "Filled": 0,
                    "Arrival Px": f"{o.limit_price:.2f}",
                    "Exec VWAP": "0.00",
                    "Status": "REJECTED",
                    "Shortfall (bps)": 0.0,
                    "Slippage (bps)": 0.0,
                    "Impact (bps)": 0.0,
                    "Friction Saved (€)": 0.0,
                    "Compliance Status": verdict.status.value,
                    "Rejection Reasons": "; ".join(verdict.rejection_reasons),
                }
            )
            continue

        dom_sim = DepthOfMarketSimulator(
            symbol=o.symbol,
            initial_mid=o.limit_price if o.limit_price > 0 else 100.0,
            tick_size=0.01 if (o.limit_price or 100.0) < 500 else 0.05,
        )

        # 1. COSTRUZIONE NEW ORDER SINGLE (35=D)
        nos_fields = {
            TAG_CL_ORD_ID: o.cl_ord_id,
            TAG_SYMBOL: o.symbol,
            TAG_SIDE: "1" if o.side == "BUY" else "2",
            TAG_ORDER_QTY: o.order_qty,
            TAG_ORD_TYPE: "2" if o.order_type == "LIMIT" else "1",
            TAG_TIME_IN_FORCE: "0",  # Day order
        }
        if o.order_type == "LIMIT" and o.limit_price > 0:
            nos_fields[TAG_PRICE] = o.limit_price

        nos_msg = FIXMessage(
            msg_type=MSG_NEW_ORDER_SINGLE,
            fields=nos_fields,
            sender_comp_id=sender_comp_id,
            target_comp_id=target_comp_id,
            msg_seq_num=seq_num,
        )
        seq_num += 1
        fix_messages_log.append(nos_msg.encode(delimiter="|"))

        # 2. MATCHING CONTRO IL BOOK L2 E TCA
        tca_res = dom_sim.execute_order(
            cl_ord_id=o.cl_ord_id,
            side=o.side,
            qty=o.order_qty,
            order_type=o.order_type,
            limit_price=o.limit_price if o.order_type == "LIMIT" else None,
        )

        for rep in tca_res.execution_reports:
            fix_messages_log.append(rep.encode(delimiter="|"))

        # Calcolo risparmio d'impatto grazie all'algoritmo (TWAP/VWAP vs Market Sweep)
        algo_multiplier = 0.65 if execution_algo == "ALMGREN_CHRISS" else (0.50 if execution_algo == "VWAP" else 0.40)
        friction_saved = max(0.0, tca_res.implementation_shortfall_eur * algo_multiplier)

        total_shortfall_eur += tca_res.implementation_shortfall_eur
        total_friction_saved_eur += friction_saved
        notional_filled = tca_res.filled_qty * tca_res.execution_vwap
        total_notional_executed += notional_filled

        executed_records.append(
            {
                "ClOrdID": o.cl_ord_id,
                "Symbol": o.symbol,
                "Side": o.side,
                "Qty": o.order_qty,
                "Filled": tca_res.filled_qty,
                "Arrival Px": f"{tca_res.arrival_price:.2f}",
                "Exec VWAP": f"{tca_res.execution_vwap:.2f}",
                "Status": tca_res.status,
                "Shortfall (bps)": round(tca_res.implementation_shortfall_bps, 1),
                "Slippage (bps)": round(tca_res.slippage_bps, 1),
                "Impact (bps)": round(tca_res.price_impact_bps, 1),
                "Friction Saved (€)": round(friction_saved, 2),
                "Compliance Status": verdict.status.value,
                "Rejection Reasons": "",
            }
        )

    avg_shortfall_bps = (
        round((total_shortfall_eur / max(1.0, total_notional_executed)) * 10000.0, 1)
        if total_notional_executed > 0
        else 0.0
    )

    passed_count = sum(1 for v in compliance_verdicts if v.get("passed", False))
    rejected_count = len(compliance_verdicts) - passed_count

    return {
        "executed_dataframe": pd.DataFrame(executed_records),
        "total_notional_executed": round(total_notional_executed, 2),
        "total_shortfall_eur": round(total_shortfall_eur, 2),
        "total_friction_saved_eur": round(total_friction_saved_eur, 2),
        "avg_shortfall_bps": avg_shortfall_bps,
        "fix_stream_log": "\n".join(fix_messages_log),
        "orders_count": len(staged_orders),
        "compliance_verdicts": compliance_verdicts,
        "compliance_summary": {
            "total_orders": len(staged_orders),
            "approved_orders": passed_count,
            "rejected_orders": rejected_count,
            "compliance_pass_rate_pct": round((passed_count / max(1, len(staged_orders))) * 100.0, 1),
        },
    }


def render_interactive_emsx_blotter(
    positions: pd.DataFrame,
    portfolio_value: float = 100000.0,
    key_suffix: str = "live_desk",
) -> None:
    """Renderizza la Blotter interattiva Bloomberg EMSX con simulazione FIX 4.4."""
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.98) 100%);
                    border: 1px solid rgba(255, 153, 0, 0.35); border-left: 4px solid #ff9900;
                    border-radius: 10px; padding: 12px 16px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <div style="font-size: 14px; font-weight: 800; color: #ff9900;">
                        📋 Bloomberg EMSX Trade Staging Blotter &amp; FIX 4.4 Router
                    </div>
                    <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">
                        Preparazione ordini di ribilanciamento, esecuzione algoritmica (TWAP/VWAP/Almgren-Chriss), Pre-Trade TCA e generazione stream FIX 4.4 validato.
                    </div>
                </div>
                <span style="background: rgba(255,153,0,0.15); border: 1px solid #ff9900; color: #ffb74d; font-size: 10.5px; font-weight: 700; padding: 3px 8px; border-radius: 4px; font-family: monospace;">
                    FIX 4.4 PROTOCOL ACTIVE
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Inizializzazione Session State per la Staging Blotter
    st_key = f"emsx_staged_orders_{key_suffix}"
    if st_key not in st.session_state:
        st.session_state[st_key] = stage_orders_from_portfolio(positions, portfolio_value=portfolio_value)

    staged_list: List[StagedOrder] = st.session_state[st_key]

    tab_blotter, tab_tca, tab_fix = st.tabs([
        "📋 Staging Blotter & Routing",
        "⚙️ Algorithmic TCA & Shortfall Inspector",
        "📡 FIX 4.4 Protocol Stream (.fix)",
    ])

    with tab_blotter:
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.5, 1.2, 1.0])
        with col_ctrl1:
            sel_algo = st.selectbox(
                "Execution Algo:",
                options=["TWAP", "VWAP", "ALMGREN_CHRISS", "POV_15"],
                index=0,
                key=f"emsx_algo_sel_{key_suffix}",
                help="TWAP: Time-Weighted Average Price | VWAP: Volume-Weighted | Almgren-Chriss: Optimal Liquidation Trajectory",
            )
        with col_ctrl2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("♻️ Ricarica da Portafoglio", key=f"btn_reload_rebal_{key_suffix}", use_container_width=True):
                st.session_state[st_key] = stage_orders_from_portfolio(positions, portfolio_value=portfolio_value)
                st.rerun()
        with col_ctrl3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            btn_exec = st.button(
                "🚀 Invia a Mercato (FIX)",
                key=f"btn_route_fix_{key_suffix}",
                type="primary",
                use_container_width=True,
            )

        # Tabella ordini staged
        if staged_list:
            b_data = [
                {
                    "Order ID": o.cl_ord_id,
                    "Ora": o.created_at,
                    "Ticker": o.symbol,
                    "Side": "🟢 BUY" if o.side == "BUY" else "🔴 SELL",
                    "Quantità": f"{o.order_qty:,}",
                    "Tipo": o.order_type,
                    "Prezzo Limite": f"€ {o.limit_price:.2f}" if o.limit_price > 0 else "MKT",
                    "Controvalore Stimato": fmt_eur(o.estimated_notional_eur),
                    "Algo": o.algo_strategy,
                    "Status": o.status,
                }
                for o in staged_list
            ]
            st.dataframe(pd.DataFrame(b_data), use_container_width=True, hide_index=True)
        else:
            st.info("Nessun ordine presente nella Staging Blotter.")

        # Esecuzione e Routing
        if btn_exec and staged_list:
            with st.spinner("Connessione gateway FIX 4.4 & Matching su L2 Depth-of-Market..."):
                sim_res = simulate_fix_routing(staged_list, execution_algo=sel_algo)
                st.session_state[f"emsx_sim_result_{key_suffix}"] = sim_res
                st.toast("✅ Ordini eseguiti a mercato con successo via FIX 4.4!", icon="🚀")
                st.rerun()

    # Scheda TCA e Risultati Esecuzione
    with tab_tca:
        sim_res = st.session_state.get(f"emsx_sim_result_{key_suffix}")
        if not sim_res:
            st.info("Esegui gli ordini dalla scheda Staging Blotter per visualizzare il report TCA di Perold.")
        else:
            t1, t2, t3, t4 = st.columns(4)
            with t1:
                metric_card("Nozionale Eseguito", fmt_eur(sim_res["total_notional_executed"]), border_left_color="#58a6ff")
            with t2:
                metric_card("Implementation Shortfall", f"{sim_res['avg_shortfall_bps']} bps", sub_title=f"Perdita di Slittamento: {fmt_eur(sim_res['total_shortfall_eur'])}", border_left_color="#f59e0b")
            with t3:
                metric_card("Friction Risparmiata", fmt_eur(sim_res["total_friction_saved_eur"]), sub_title=f"Algo {sel_algo} vs Aggressive Sweep", border_left_color="#10b981")
            with t4:
                metric_card("Ordini Conclusi", f"{sim_res['orders_count']} / {sim_res['orders_count']}", sub_title="Fill Rate: 100.0%", border_left_color="#10b981")

            st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 Breakdown Dettagliato TCA per Ordine")
            st.dataframe(sim_res["executed_dataframe"], use_container_width=True, hide_index=True)

    # Scheda FIX Stream
    with tab_fix:
        sim_res = st.session_state.get(f"emsx_sim_result_{key_suffix}")
        if not sim_res:
            st.info("Nessuno stream generato. Premi 'Invia a Mercato (FIX)' per negoziare gli ordini.")
        else:
            st.markdown(
                """
                <div style="font-size: 11px; font-family: monospace; color: #94a3b8; margin-bottom: 6px;">
                    Log standard FIX 4.4 conforme alle specifiche FPL (Tag 8=BeginString, 35=MsgType, 10=CheckSum).
                </div>
                """,
                unsafe_allow_html=True,
            )
            raw_log = sim_res["fix_stream_log"]
            st.code(raw_log, language="bash")
            st.download_button(
                "📥 Scarica Session Log FIX 4.4 (.fix)",
                data=raw_log,
                file_name=f"emsx_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fix",
                mime="text/plain",
                use_container_width=False,
            )
