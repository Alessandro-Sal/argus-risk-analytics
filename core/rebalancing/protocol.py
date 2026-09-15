"""
core/rebalancing/protocol.py
ARGUS — Unified Portfolio Rebalancing Protocol & Data Contracts.

Defines standardized data structures, Enums, and Strategy Protocols
for portfolio rebalancing across heuristic, autonomous, tax-aware, and prescriptive engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

import numpy as np
import pandas as pd


class TaxCategory(str, Enum):
    """
    Classificazione fiscale degli strumenti finanziari secondo il TUIR italiano.
    """
    REDDITI_CAPITALE = "Redditi di Capitale"        # ETF, OICR, Cedole obbligazionarie (TUIR Art. 44)
    REDDITI_DIVERSI = "Redditi Diversi"              # Azioni singole, ETC, Certificati, Derivati (TUIR Art. 67)
    MINUSVALENZA_GENERATA = "Minusvalenza Generata" # Posizione chiusa in perdita (TUIR Art. 68 c. 5)
    EXEMPT_OR_NA = "N/A / Esente"                   # Liquidità o strumenti esenti


class RebalancingMode(str, Enum):
    """
    Modalità/Strategie di ribilanciamento supportate dal motore unificato ARGUS.
    """
    TAX_AWARE = "tax_aware"
    PRESCRIPTIVE = "prescriptive"
    AUTONOMOUS = "autonomous"
    HEURISTIC = "heuristic"


@dataclass
class AssetHolding:
    """
    Rappresentazione unificata di una posizione di portafoglio.
    """
    ticker: str
    shares: float
    current_price: float
    pmc: float = 0.0
    asset_class: str = "Equity"
    tax_category: str = TaxCategory.REDDITI_DIVERSI.value
    market_value: Optional[float] = None
    adv_eur: float = 2_000_000.0
    bid_ask_spread_bps: float = 5.0

    @property
    def value(self) -> float:
        if self.market_value is not None and self.market_value > 0:
            return float(self.market_value)
        return float(self.shares * self.current_price)

    @property
    def unrealized_pnl(self) -> float:
        if self.pmc > 0:
            return float((self.current_price - self.pmc) * self.shares)
        return 0.0


@dataclass
class PlannedOrder:
    """
    Rappresentazione unificata di un ordine generato dalla procedura di ribilanciamento.
    """
    ticker: str
    action: str  # "BUY", "SELL", "HOLD"
    shares: float
    price: float
    order_value: float
    tax_category: str = TaxCategory.REDDITI_DIVERSI.value
    realized_gain: float = 0.0
    estimated_tax: float = 0.0
    estimated_fees: float = 0.0
    current_weight_pct: float = 0.0
    target_weight_pct: float = 0.0
    delta_weight_pct: float = 0.0
    fix_message: Optional[str] = None
    notes: str = ""


@dataclass
class RebalancingContext:
    """
    Contesto unificato contenente lo stato del portafoglio, vincoli e obiettivi di allocazione.
    """
    holdings: Union[pd.DataFrame, List[AssetHolding], Dict[str, Any]]
    target_weights: Dict[str, float]
    total_portfolio_value: Optional[float] = None
    cash_available: float = 0.0
    new_cash_injection: float = 0.0
    minusvalenze_available: float = 0.0
    max_turnover_pct: float = 50.0
    min_trade_eur: float = 50.0
    friction_config: Optional[Any] = None
    constraints: Optional[Any] = None
    covariance_matrix: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_holdings_df(self) -> pd.DataFrame:
        """Restituisce le posizioni normalizzate come DataFrame pandas."""
        if isinstance(self.holdings, pd.DataFrame):
            return self.holdings.copy()
        elif isinstance(self.holdings, list) and len(self.holdings) > 0:
            records = []
            for h in self.holdings:
                if isinstance(h, AssetHolding):
                    records.append({
                        "ticker": h.ticker,
                        "shares": h.shares,
                        "qty_net": h.shares,
                        "quantity": h.shares,
                        "current_price": h.current_price,
                        "last_price": h.current_price,
                        "pmc": h.pmc,
                        "prezzo_medio_carico": h.pmc,
                        "asset_class": h.asset_class,
                        "market_value": h.value,
                        "current_value": h.value,
                        "controvalore": h.value,
                        "tax_category": h.tax_category,
                        "adv_eur": h.adv_eur,
                        "bid_ask_spread_bps": h.bid_ask_spread_bps,
                    })
                elif isinstance(h, dict):
                    h_copy = dict(h)
                    sh = float(h_copy.get("shares", h_copy.get("quantity", h_copy.get("qty", h_copy.get("qty_net", 0.0)))))
                    px = float(h_copy.get("current_price", h_copy.get("last_price", h_copy.get("price", 100.0))))
                    val = float(h_copy.get("market_value", h_copy.get("current_value", h_copy.get("controvalore", h_copy.get("value", sh * px)))))
                    h_copy["market_value"] = val
                    h_copy["current_value"] = val
                    h_copy["controvalore"] = val
                    h_copy["value"] = val
                    records.append(h_copy)
            return pd.DataFrame(records)
        elif isinstance(self.holdings, dict):
            if "positions" in self.holdings and isinstance(self.holdings["positions"], pd.DataFrame):
                return self.holdings["positions"].copy()
            return pd.DataFrame(self.holdings)
        return pd.DataFrame()

    def get_normalized_target_weights(self) -> Dict[str, float]:
        """Restituisce pesi target normalizzati in scala unitaria (0.0 - 1.0) con somma 1.0."""
        if not self.target_weights:
            return {}
        w_dict = {str(k).strip(): float(v) for k, v in self.target_weights.items()}
        total_w = sum(w_dict.values())
        if total_w > 0:
            return {k: v / total_w for k, v in w_dict.items()}
        return w_dict

    def get_total_value(self) -> float:
        """Calcola o restituisce il valore totale del portafoglio."""
        if self.total_portfolio_value is not None and self.total_portfolio_value > 0:
            return float(self.total_portfolio_value)
        df = self.get_holdings_df()
        if not df.empty:
            for col in ["controvalore", "current_value", "market_value", "value"]:
                if col in df.columns:
                    val = float(df[col].sum())
                    if val > 0:
                        return val
        return 100_000.0


@dataclass
class RebalanceResult:
    """
    Risultato unificato generato da una qualsiasi strategia di ribilanciamento ARGUS.
    """
    strategy_name: str
    orders: List[PlannedOrder]
    df_orders: pd.DataFrame
    summary: Dict[str, Any]
    tax_report: Dict[str, Any] = field(default_factory=dict)
    compliance: Dict[str, Any] = field(default_factory=dict)
    raw_result: Optional[Dict[str, Any]] = None


@runtime_checkable
class RebalancingStrategy(Protocol):
    """
    Protocollo formale per qualsiasi strategia o motore di ribilanciamento.
    """
    name: str

    def generate_plan(self, context: RebalancingContext) -> RebalanceResult:
        """Genera il piano di ordini e la rendicontazione partendo dal contesto."""
        ...
