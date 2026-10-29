"""
core/rebalancing/engine.py
ARGUS — Unified Multi-Strategy Rebalancing Engine & Dispatcher.

Orchestrates and dispatches rebalancing calculations across:
1. Autonomous AI Rebalancer (MiFID II + Italian TUIR Art. 44 vs 67 compliance)
2. Tax-Aware Friction Rebalancer (Commissions, bid-ask spread, zero-tax cashflow rebalancing)
3. Prescriptive Conic Rebalancer (SLSQP optimization, tracking error, FIX 4.4 blotter)
4. Heuristic Target Weights Rebalancer (Direct rebalance to target weights/efficient frontier)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from core.rebalancing.protocol import (
    AssetHolding,
    PlannedOrder,
    RebalanceResult,
    RebalancingContext,
    RebalancingMode,
    RebalancingStrategy,
    TaxCategory,
)


class AutonomousStrategyAdapter:
    """
    Adapter per core.autonomous_rebalancer.generate_autonomous_rebalancing_proposal.
    Applica le regole fiscali TUIR Art. 44 (ETF) vs Art. 67 (Azioni/ETC/Bond) e gate MiFID II.
    """
    name = "autonomous"

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        from core.autonomous_rebalancer import (
            check_mifid_suitability_and_limits,
            generate_autonomous_rebalancing_proposal,
        )

        df_pos = context.get_holdings_df()
        targets = context.get_normalized_target_weights()
        tot_val = context.get_total_value()

        raw = generate_autonomous_rebalancing_proposal(
            df_positions=df_pos,
            results={"valore_totale": tot_val, "positions": df_pos},
            target_weights=targets,
            max_turnover_pct=context.max_turnover_pct,
            min_trade_eur=context.min_trade_eur,
            available_minusvalenze_eur=context.minusvalenze_available,
        )

        # MiFID suitability check
        mifid_check = check_mifid_suitability_and_limits(
            df_positions=df_pos,
            results={"valore_totale": tot_val},
            risk_profile=context.metadata.get("risk_profile", "Moderate"),
        )

        trades_list = raw.get("trades_list", [])
        orders: List[PlannedOrder] = []
        for t in trades_list:
            orders.append(
                PlannedOrder(
                    ticker=t.get("ticker", ""),
                    action=t.get("action", "HOLD"),
                    shares=float(t.get("suggested_shares", 0)),
                    price=float(t.get("estimated_price", 0.0)),
                    order_value=float(t.get("trade_notional_eur", 0.0)),
                    tax_category=t.get("tax_category", TaxCategory.REDDITI_DIVERSI.value),
                    realized_gain=float(t.get("gross_capital_gain_eur", 0.0)),
                    estimated_tax=float(t.get("estimated_tax_impact_eur", 0.0)),
                    current_weight_pct=float(t.get("current_weight_pct", 0.0)),
                    target_weight_pct=float(t.get("target_weight_pct", 0.0)),
                    delta_weight_pct=round(float(t.get("target_weight_pct", 0.0)) - float(t.get("current_weight_pct", 0.0)), 2),
                    notes=f"Tax saved: {t.get('tax_saved_eur', 0.0):.2f} €",
                )
            )

        summary = {
            "portfolio_total_value_eur": raw.get("portfolio_total_value_eur", tot_val),
            "total_trades_count": raw.get("total_trades_count", len(orders)),
            "total_buy_volume_eur": raw.get("total_buy_volume_eur", 0.0),
            "total_sell_volume_eur": raw.get("total_sell_volume_eur", 0.0),
            "turnover_pct": raw.get("turnover_pct", 0.0),
            "is_turnover_compliant": raw.get("is_turnover_compliant", True),
            "net_cash_flow": raw.get("total_sell_volume_eur", 0.0) - raw.get("total_buy_volume_eur", 0.0),
        }

        tax_report = {
            "initial_minusvalenze_eur": raw.get("initial_minusvalenze_eur", context.minusvalenze_available),
            "remaining_minusvalenze_eur": raw.get("remaining_minusvalenze_eur", 0.0),
            "total_tax_saved_by_harvesting_eur": raw.get("total_tax_saved_by_harvesting_eur", 0.0),
            "estimated_tax_liability_eur": raw.get("estimated_tax_liability_eur", 0.0),
            "total_etf_gains_eur": raw.get("total_etf_gains_eur", 0.0),
            "total_diversi_gains_eur": raw.get("total_diversi_gains_eur", 0.0),
        }

        return RebalanceResult(
            strategy_name=self.name,
            orders=orders,
            df_orders=raw.get("trades_df", pd.DataFrame()),
            summary=summary,
            tax_report=tax_report,
            compliance=mifid_check,
            raw_result=raw,
        )


class TaxAwareStrategyAdapter:
    """
    Adapter per core.tax_aware_rebalancer.TaxAwarePortfolioRebalancer.
    Include la matrice di attrito (commissioni, spread bid-ask) e l'ottimizzazione fiscale.
    """
    name = "tax_aware"

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        from core.tax_aware_rebalancer import FrictionConfig, TaxAwarePortfolioRebalancer

        df_pos = context.get_holdings_df()
        targets = context.get_normalized_target_weights()
        tot_val = context.get_total_value()

        friction_cfg = context.friction_config
        if friction_cfg is None:
            friction_cfg = FrictionConfig()

        raw = TaxAwarePortfolioRebalancer.compute_full_rebalance_plan(
            current_holdings=df_pos,
            target_weights=targets,
            total_portfolio_value=tot_val,
            existing_minusvalenze=context.minusvalenze_available,
            config=friction_cfg,
        )

        df_trades = raw.get("trade_execution_list_df", raw.get("df_trades", pd.DataFrame()))
        orders: List[PlannedOrder] = []

        if isinstance(df_trades, pd.DataFrame) and not df_trades.empty:
            for _, t in df_trades.iterrows():
                act_str = str(t.get("Azione", t.get("action", "HOLD")))
                clean_act = "BUY" if ("ACQUISTA" in act_str or "BUY" in act_str) else ("SELL" if ("VENDI" in act_str or "SELL" in act_str) else "HOLD")
                tk = str(t.get("Ticker", t.get("ticker", "")))
                trade_val = float(t.get("Controvalore Ordine (€)", t.get("trade_amount_eur", 0.0)))
                comm = float(t.get("Commissioni Stimate (€)", t.get("commission_eur", 0.0)))
                tax_cost = float(t.get("Impatto Fiscale (€)", t.get("tax_cost_eur", 0.0)))
                cur_v = float(t.get("Valore Attuale (€)", t.get("cur_value_eur", 0.0)))
                tgt_v = float(t.get("Valore Target (€)", t.get("tgt_value_eur", 0.0)))

                orders.append(
                    PlannedOrder(
                        ticker=tk,
                        action=clean_act,
                        shares=0.0,
                        price=0.0,
                        order_value=trade_val,
                        tax_category=TaxCategory.REDDITI_DIVERSI.value,
                        realized_gain=0.0,
                        estimated_tax=tax_cost,
                        estimated_fees=comm,
                        current_weight_pct=round(cur_v / max(tot_val, 1e-4) * 100.0, 2),
                        target_weight_pct=round(tgt_v / max(tot_val, 1e-4) * 100.0, 2),
                        delta_weight_pct=round((tgt_v - cur_v) / max(tot_val, 1e-4) * 100.0, 2),
                        notes=f"Friction: {comm + tax_cost:.2f} €",
                    )
                )

        gross_turnover = float(raw.get("gross_turnover_eur", raw.get("summary", {}).get("gross_turnover", 0.0)))
        tot_commissions = float(raw.get("total_commissions_eur", raw.get("summary", {}).get("total_commissions", 0.0)))
        tot_spread = float(raw.get("total_spread_cost_eur", raw.get("summary", {}).get("total_spread_cost", 0.0)))
        tot_friction = float(raw.get("total_friction_drag_eur", raw.get("summary", {}).get("total_friction_cost", 0.0)))
        est_tax = float(raw.get("estimated_tax_eur", raw.get("summary", {}).get("total_tax_cost", 0.0)))
        rem_minus = float(raw.get("remaining_minusvalenze_eur", raw.get("summary", {}).get("remaining_minusvalenze", 0.0)))

        summary = {
            "portfolio_total_value_eur": tot_val,
            "total_trades_count": len(orders),
            "total_buy_volume_eur": sum(o.order_value for o in orders if o.action == "BUY"),
            "total_sell_volume_eur": sum(o.order_value for o in orders if o.action == "SELL"),
            "gross_turnover_eur": gross_turnover,
            "turnover_pct": float(raw.get("gross_turnover_pct", (gross_turnover / max(1.0, tot_val) * 100.0))),
            "total_commissions_eur": tot_commissions,
            "total_spread_cost_eur": tot_spread,
            "total_friction_cost_eur": tot_friction,
        }

        tax_report = {
            "initial_minusvalenze_eur": context.minusvalenze_available,
            "remaining_minusvalenze_eur": rem_minus,
            "estimated_tax_liability_eur": est_tax,
        }

        return RebalanceResult(
            strategy_name=self.name,
            orders=orders,
            df_orders=df_trades,
            summary=summary,
            tax_report=tax_report,
            compliance={},
            raw_result=raw,
        )


class PrescriptiveStrategyAdapter:
    """
    Adapter per core.prescriptive_rebalancer.PrescriptiveConicRebalancer.
    Ottimizzazione convessa multi-obiettivo (Tracking error, fiscalità, market impact Almgren-Chriss, FIX 4.4 blotter).
    """
    name = "prescriptive"

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        from core.prescriptive_rebalancer import (
            FIXOrder,
            PositionLot,
            PrescriptiveConicRebalancer,
            RebalanceConstraints,
            TaxWalletState,
        )

        df_pos = context.get_holdings_df()
        targets = context.get_normalized_target_weights()
        tot_val = context.get_total_value()

        # Build PositionLots
        position_lots: List[PositionLot] = []
        if not df_pos.empty:
            for _, r in df_pos.iterrows():
                t = str(r.get("ticker", "")).strip()
                sh = float(r.get("shares", r.get("qty_net", r.get("quantity", 0.0))))
                px = float(r.get("current_price", r.get("last_price", r.get("prezzo_corrente", 100.0))))
                pmc = float(r.get("pmc", r.get("prezzo_medio_carico", px)))
                ac = str(r.get("asset_class", "Equity"))
                adv = float(r.get("adv_eur", 2_000_000.0))
                spread = float(r.get("bid_ask_spread_bps", 5.0))
                if sh > 0:
                    position_lots.append(
                        PositionLot(
                            ticker=t,
                            shares=sh,
                            current_price=px,
                            pmc=pmc,
                            asset_class=ac,
                            adv_eur=adv,
                            bid_ask_spread_bps=spread,
                        )
                    )

        tax_wallet = TaxWalletState(
            minusvalenze_available_eur=context.minusvalenze_available,
        )
        engine = PrescriptiveConicRebalancer(tax_wallet=tax_wallet)

        cons = context.constraints
        if not isinstance(cons, RebalanceConstraints):
            cons = RebalanceConstraints(
                max_turnover_pct=context.max_turnover_pct,
            )

        raw = engine.optimize_rebalance(
            positions=position_lots,
            target_weights=targets,
            available_cash_eur=context.cash_available + context.new_cash_injection,
            constraints=cons,
            covariance_matrix=context.covariance_matrix,
        )

        orders: List[PlannedOrder] = []
        for fo in raw.get("orders", []):
            if isinstance(fo, FIXOrder):
                side = "BUY" if str(fo.side) in ["1", "BUY"] else "SELL"
                orders.append(
                    PlannedOrder(
                        ticker=fo.symbol,
                        action=side,
                        shares=float(fo.order_qty),
                        price=float(fo.limit_price),
                        order_value=round(fo.order_qty * fo.limit_price, 2),
                        tax_category=TaxCategory.REDDITI_DIVERSI.value,
                        estimated_tax=float(fo.estimated_tax_eur),
                        estimated_fees=float(fo.estimated_slippage_eur),
                        fix_message=fo.to_fix_string(),
                    )
                )

        summary = {
            "portfolio_total_value_eur": tot_val,
            "total_trades_count": len(orders),
            "tracking_error_bps": raw.get("tracking_error_bps", 0.0),
            "turnover_pct": raw.get("turnover_pct", 0.0),
            "market_impact_eur": raw.get("market_impact_eur", 0.0),
            "fix_blotter": raw.get("fix_blotter", ""),
        }

        tax_report = {
            "initial_minusvalenze_eur": context.minusvalenze_available,
            "remaining_minusvalenze_eur": tax_wallet.minusvalenze_available_eur,
            "minusvalenze_offset_eur": raw.get("minusvalenze_offset_eur", 0.0),
            "estimated_tax_liability_eur": raw.get("tax_drag_eur", 0.0),
            "gross_gain_eur": raw.get("gross_gain_eur", 0.0),
        }

        return RebalanceResult(
            strategy_name=self.name,
            orders=orders,
            df_orders=raw.get("df_orders", pd.DataFrame()),
            summary=summary,
            tax_report=tax_report,
            compliance={"turnover_compliant": raw.get("turnover_pct", 0.0) <= cons.max_turnover_pct},
            raw_result=raw,
        )


class HeuristicStrategyAdapter:
    """
    Adapter per core.rebalancer.compute_rebalancing_orders.
    Generazione lineare e deterministica degli ordini target per quantitativi di quote.
    """
    name = "heuristic"

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        from core.rebalancer import compute_rebalancing_orders

        df_pos = context.get_holdings_df()
        targets = context.get_normalized_target_weights()
        tot_val = context.get_total_value()

        # Convert target weights to percentage (0 - 100) for compute_rebalancing_orders
        targets_pct = {k: v * 100.0 for k, v in targets.items()}

        raw = compute_rebalancing_orders(
            results={"positions": df_pos},
            strategy="custom",
            custom_target_weights=targets_pct,
            new_cash_eur=context.new_cash_injection,
            target_total_value=tot_val + context.new_cash_injection,
            integer_shares=True,
        )

        df_orders = raw.get("orders", pd.DataFrame())
        raw_summary = raw.get("summary", {})

        orders: List[PlannedOrder] = []
        if not df_orders.empty:
            for _, r in df_orders.iterrows():
                act = str(r.get("action", r.get("Azione", "HOLD")))
                clean_act = "BUY" if "BUY" in act else ("SELL" if "SELL" in act else "HOLD")
                if clean_act == "HOLD":
                    continue
                orders.append(
                    PlannedOrder(
                        ticker=str(r.get("ticker", r.get("Ticker", ""))),
                        action=clean_act,
                        shares=abs(float(r.get("qty_delta", r.get("Delta Quote", 0.0)))),
                        price=float(r.get("last_price", r.get("Prezzo (€/$)", 0.0))),
                        order_value=float(r.get("order_value_eur", r.get("Valore Ordine (€/$)", 0.0))),
                        current_weight_pct=float(r.get("current_weight_pct", r.get("Peso Attuale %", 0.0))),
                        target_weight_pct=float(r.get("target_weight_pct", r.get("Peso Target %", 0.0))),
                        delta_weight_pct=float(r.get("weight_delta_pct", r.get("Delta Peso %", 0.0))),
                    )
                )

        summary = {
            "portfolio_total_value_eur": raw_summary.get("total_current_value", tot_val),
            "target_total_value_eur": raw_summary.get("target_total_value", tot_val),
            "total_trades_count": len(orders),
            "total_buy_volume_eur": raw_summary.get("total_spent", 0.0),
            "total_sell_volume_eur": raw_summary.get("total_raised", 0.0),
            "net_cash_flow": raw_summary.get("net_cash_flow", 0.0),
        }

        return RebalanceResult(
            strategy_name=self.name,
            orders=orders,
            df_orders=df_orders,
            summary=summary,
            tax_report={},
            compliance={},
            raw_result=raw,
        )




class MIPStrategyAdapter:
    """
    Adapter per core.rebalancing.mip.solve_mip_rebalance.
    Ottimizzazione discreta a numeri interi con vincoli di cardinalita, lotti minimi e budget CGT.
    """
    name = "mip"

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        from core.rebalancing.mip import solve_mip_rebalance

        df_pos = context.get_holdings_df()
        targets = context.get_normalized_target_weights()
        tot_val = context.get_total_value()

        current_holdings: Dict[str, float] = {}
        current_prices: Dict[str, float] = {}
        pmc_dict: Dict[str, float] = {}

        if isinstance(df_pos, pd.DataFrame) and not df_pos.empty:
            for _, row in df_pos.iterrows():
                tk = str(row.get("ticker", "")).strip().upper()
                sh = float(row.get("shares", row.get("qty_net", row.get("quantity", 0.0))))
                px = float(row.get("current_price", row.get("last_price", row.get("prezzo_corrente", 100.0))))
                pmc = float(row.get("pmc", row.get("prezzo_medio_carico", px)))
                if tk:
                    current_holdings[tk] = sh
                    current_prices[tk] = px
                    pmc_dict[tk] = pmc

        for tk in targets.keys():
            if tk not in current_prices:
                current_prices[tk] = 100.0
            if tk not in current_holdings:
                current_holdings[tk] = 0.0
            if tk not in pmc_dict:
                pmc_dict[tk] = current_prices[tk]

        meta = context.metadata or {}
        raw = solve_mip_rebalance(
            current_holdings=current_holdings,
            current_prices=current_prices,
            target_weights=targets,
            total_capital=tot_val,
            cash_available=context.cash_available,
            max_cardinality=meta.get("max_cardinality"),
            lot_sizes=meta.get("lot_sizes"),
            min_trade_eur=context.min_trade_eur,
            max_turnover_pct=context.max_turnover_pct,
            capital_gains_tax_budget_eur=meta.get("capital_gains_tax_budget_eur"),
            pmc_dict=pmc_dict,
            tax_rate=meta.get("tax_rate", 0.26),
        )

        raw_orders = raw.get("orders", [])
        orders: List[PlannedOrder] = []
        for o in raw_orders:
            orders.append(
                PlannedOrder(
                    ticker=o.get("ticker", ""),
                    action=o.get("action", "HOLD"),
                    shares=float(o.get("shares_to_trade", 0.0)),
                    price=float(o.get("price", 0.0)),
                    order_value=float(o.get("trade_value_eur", 0.0)),
                    realized_gain=float(o.get("estimated_gain_eur", 0.0)),
                    estimated_tax=float(o.get("estimated_tax_eur", 0.0)),
                    current_weight_pct=float(o.get("current_weight_pct", 0.0)),
                    target_weight_pct=float(o.get("target_weight_pct", 0.0)),
                    delta_weight_pct=round(float(o.get("target_weight_pct", 0.0)) - float(o.get("current_weight_pct", 0.0)), 2),
                    notes=f"Post shares: {o.get('new_shares', 0)}",
                )
            )

        summary = {
            "portfolio_total_value_eur": raw.get("summary", {}).get("total_portfolio_value_eur", tot_val),
            "total_trades_count": len(orders),
            "turnover_pct": raw.get("summary", {}).get("turnover_pct", 0.0),
            "is_turnover_compliant": True,
            "cardinality": raw.get("summary", {}).get("final_cardinality", len(current_holdings)),
            "cash_remaining_eur": raw.get("summary", {}).get("cash_remaining_eur", 0.0),
        }

        tax_report = {
            "estimated_tax_liability_eur": raw.get("summary", {}).get("total_tax_liability_eur", 0.0),
            "capital_gains_realized_eur": raw.get("summary", {}).get("total_capital_gains_eur", 0.0),
        }

        return RebalanceResult(
            strategy_name=self.name,
            orders=orders,
            df_orders=pd.DataFrame(raw_orders) if raw_orders else pd.DataFrame(),
            summary=summary,
            tax_report=tax_report,
            compliance=raw.get("milp_diagnostics", {}),
            raw_result=raw,
        )


class RebalancingEngine:
    """
    Dispatcher e orchestratore centrale di ribilanciamento per ARGUS.
    Supporta l'iniezione dinamica di strategie e la selezione polimorfica.
    """

    _REGISTRY: Dict[str, type] = {
        RebalancingMode.AUTONOMOUS.value: AutonomousStrategyAdapter,
        RebalancingMode.TAX_AWARE.value: TaxAwareStrategyAdapter,
        RebalancingMode.PRESCRIPTIVE.value: PrescriptiveStrategyAdapter,
        RebalancingMode.HEURISTIC.value: HeuristicStrategyAdapter,
    }

    def __init__(self, strategy: Union[str, RebalancingStrategy] = RebalancingMode.AUTONOMOUS.value):
        if isinstance(strategy, str):
            strategy_key = strategy.lower().strip()
            if strategy_key not in self._REGISTRY:
                raise ValueError(
                    f"Strategia di ribilanciamento '{strategy}' non riconosciuta. "
                    f"Disponibili: {list(self._REGISTRY.keys())}"
                )
            self._strategy: RebalancingStrategy = self._REGISTRY[strategy_key]()
        elif isinstance(strategy, RebalancingStrategy):
            self._strategy = strategy
        else:
            raise TypeError(f"Il tipo di strategia fornito non implementa RebalancingStrategy: {type(strategy)}")

    @property
    def strategy(self) -> RebalancingStrategy:
        return self._strategy

    @classmethod
    def register_strategy(cls, name: str, strategy_cls: type) -> None:
        """Registra una nuova strategia custom nel motore unificato."""
        cls._REGISTRY[name.lower().strip()] = strategy_cls

    def execute(self, context: RebalancingContext) -> RebalanceResult:
        """Esegue il calcolo del ribilanciamento delegando alla strategia selezionata."""
        return self._strategy.generate_plan(context)

    @classmethod
    def rebalance(
        cls,
        context: RebalancingContext,
        strategy: Union[str, RebalancingStrategy] = RebalancingMode.AUTONOMOUS.value,
    ) -> RebalanceResult:
        """Convenience method per eseguire un ribilanciamento con una singola chiamata."""
        engine = cls(strategy=strategy)
        return engine.execute(context)
