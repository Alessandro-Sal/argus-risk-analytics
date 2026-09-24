"""
core/services/rebalancing_service.py
ARGUS — Application Service Layer: Unified Rebalancing Service.

Headless facade orchestrating portfolio rebalancing calculations
across multiple strategies (autonomous, tax_aware, prescriptive, heuristic),
consumable by both the FastAPI REST endpoints and Streamlit UI pages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from core.rebalancing import (
    AssetHolding,
    PlannedOrder,
    RebalanceResult,
    RebalancingContext,
    RebalancingEngine,
    RebalancingMode,
    TaxCategory,
)


class RebalancingService:
    """
    Unified headless application service for portfolio rebalancing and trade execution planning.
    """

    @staticmethod
    def execute_rebalance(
        positions: Union[pd.DataFrame, List[Dict[str, Any]], List[AssetHolding]],
        target_weights: Dict[str, float],
        strategy: str = "autonomous",
        total_portfolio_value: Optional[float] = None,
        minusvalenze_available: float = 0.0,
        max_turnover_pct: float = 50.0,
        min_trade_eur: float = 50.0,
        cash_injection: float = 0.0,
        cash_available: float = 0.0,
        friction_config: Optional[Any] = None,
        constraints: Optional[Any] = None,
        covariance_matrix: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Esegue il ribilanciamento del portafoglio delegando al RebalancingEngine.
        Restituisce un dizionario serializzabile sia per REST API che per Streamlit.
        """
        # Normalizzazione input posizioni
        holdings_list: List[AssetHolding] = []
        if isinstance(positions, list) and len(positions) > 0 and isinstance(positions[0], AssetHolding):
            holdings_list = positions
        elif isinstance(positions, list):
            for p in positions:
                if isinstance(p, dict):
                    holdings_list.append(
                        AssetHolding(
                            ticker=str(p.get("ticker", "")).strip().upper(),
                            shares=float(p.get("shares", p.get("quantity", p.get("qty", 0.0)))),
                            current_price=float(p.get("current_price", p.get("price", p.get("last_price", 100.0)))),
                            pmc=float(p.get("pmc", p.get("acquisition_price", 0.0))),
                            asset_class=str(p.get("asset_class", "Equity")),
                            tax_category=str(p.get("tax_category", TaxCategory.REDDITI_DIVERSI.value)),
                            adv_eur=float(p.get("adv_eur", 2_000_000.0)),
                            bid_ask_spread_bps=float(p.get("bid_ask_spread_bps", 5.0)),
                        )
                    )
        elif isinstance(positions, pd.DataFrame):
            holdings_list = positions  # Gestito nativamente da RebalancingContext

        context = RebalancingContext(
            holdings=holdings_list,
            target_weights=target_weights,
            total_portfolio_value=total_portfolio_value,
            cash_available=cash_available,
            new_cash_injection=cash_injection,
            minusvalenze_available=minusvalenze_available,
            max_turnover_pct=max_turnover_pct,
            min_trade_eur=min_trade_eur,
            friction_config=friction_config,
            constraints=constraints,
            covariance_matrix=covariance_matrix,
            metadata=metadata or {},
        )

        # Risoluzione strategia (case-insensitive)
        clean_strat = str(strategy).lower().strip()
        if clean_strat in ["mip", "mip_cardinality", "discrete_lot"]:
            from core.mip_rebalancer import solve_mip_rebalance

            current_holdings: Dict[str, float] = {}
            current_prices: Dict[str, float] = {}
            pmc_dict: Dict[str, float] = {}

            if isinstance(positions, pd.DataFrame):
                for _, row in positions.iterrows():
                    t = str(row.get("ticker", row.name)).strip().upper()
                    current_holdings[t] = float(row.get("shares", row.get("quantity", 0.0)))
                    current_prices[t] = float(row.get("current_price", row.get("price", 100.0)))
                    pmc_dict[t] = float(row.get("pmc", current_prices[t]))
            else:
                for h in holdings_list:
                    current_holdings[h.ticker] = float(h.shares)
                    current_prices[h.ticker] = float(h.current_price)
                    pmc_dict[h.ticker] = float(h.pmc)

            max_card = (metadata or {}).get("max_cardinality") or (
                constraints.get("max_cardinality") if isinstance(constraints, dict) else None
            )
            lot_sizes = (metadata or {}).get("lot_sizes") or (
                constraints.get("lot_sizes") if isinstance(constraints, dict) else None
            )
            cgt_budget = (metadata or {}).get("capital_gains_tax_budget_eur")

            mip_res = solve_mip_rebalance(
                current_holdings=current_holdings,
                current_prices=current_prices,
                target_weights=target_weights,
                total_capital=total_portfolio_value,
                cash_available=cash_available + cash_injection,
                max_cardinality=max_card,
                lot_sizes=lot_sizes,
                min_trade_eur=min_trade_eur,
                max_turnover_pct=max_turnover_pct,
                capital_gains_tax_budget_eur=cgt_budget,
                pmc_dict=pmc_dict,
            )

            df_orders = (
                pd.DataFrame(mip_res["orders"])
                if mip_res["orders"]
                else pd.DataFrame(columns=["ticker", "action", "shares", "price", "order_value"])
            )

            return {
                "strategy": "MIP Cardinality & Lot-Sizing",
                "orders": mip_res["orders"],
                "df_orders": df_orders,
                "summary": {
                    "total_orders": len(mip_res["orders"]),
                    "total_volume_eur": mip_res["total_trade_volume_eur"],
                    "total_tax_eur": mip_res["total_tax_incurred_eur"],
                    "active_cardinality": mip_res["cardinality"],
                    "tracking_error_l1": mip_res["tracking_error_l1"],
                    "cash_leftover_eur": mip_res["cash_leftover_eur"],
                    "execution_summary": mip_res["execution_summary"],
                },
                "mip_details": mip_res,
                "tax_report": {"total_tax": mip_res["total_tax_incurred_eur"]},
                "compliance": {"status": "PASS" if mip_res["status"] == "OPTIMAL" else "WARNING"},
                "status": "COMPLETED",
            }

        result: RebalanceResult = RebalancingEngine.rebalance(context=context, strategy=clean_strat)


        # Serializzazione ordini in dizionari
        serialized_orders: List[Dict[str, Any]] = []
        for o in result.orders:
            serialized_orders.append({
                "ticker": o.ticker,
                "action": o.action,
                "shares": float(o.shares),
                "price": float(o.price),
                "order_value": float(o.order_value),
                "tax_category": str(o.tax_category),
                "realized_gain": float(o.realized_gain),
                "estimated_tax": float(o.estimated_tax),
                "estimated_fees": float(o.estimated_fees),
                "current_weight_pct": float(o.current_weight_pct),
                "target_weight_pct": float(o.target_weight_pct),
                "delta_weight_pct": float(o.delta_weight_pct),
                "fix_message": o.fix_message,
                "notes": o.notes,
            })

        return {
            "strategy": result.strategy_name,
            "orders": serialized_orders,
            "df_orders": result.df_orders,
            "summary": result.summary,
            "tax_report": result.tax_report,
            "compliance": result.compliance,
            "status": "COMPLETED",
        }
