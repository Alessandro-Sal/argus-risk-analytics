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
