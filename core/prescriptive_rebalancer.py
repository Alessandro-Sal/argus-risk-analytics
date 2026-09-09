"""
core/prescriptive_rebalancer.py
ARGUS — Prescriptive Conic/Convex Rebalancing Engine & FIX Protocol Order Blotter.

Features:
- Multi-objective constrained portfolio rebalancing (Tracking Error vs Turnover vs Tax Drag vs Market Impact).
- Tax-Aware Minusvalenze Absorption (Italian fiscal framework: 26% vs 12.5% whitelist).
- Almgren-Chriss non-linear market impact & bid-ask slippage estimation.
- FIX 4.4 Protocol compliant order blotter generation (Tag 35=D, Tag 54, Tag 38, Tag 44).
- Deterministic and robust optimization via SciPy SLSQP.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import datetime
import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class PositionLot:
    """Rappresentazione di una posizione con parametri di costo fiscale e liquidità di mercato."""
    ticker: str
    shares: float
    current_price: float
    pmc: float  # Prezzo Medio di Carico (Acquisition Price)
    asset_class: str = "Equity"  # Equity, Bond_Gov, Bond_Corp, ETF
    adv_eur: float = 2_000_000.0  # Average Daily Volume in EUR
    bid_ask_spread_bps: float = 5.0  # Spread bid-ask in basis points

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def unrealized_gain_eur(self) -> float:
        return (self.current_price - self.pmc) * self.shares


@dataclass
class TaxWalletState:
    """Zainetto fiscale con minusvalenze pregresse compensabili."""
    minusvalenze_available_eur: float = 0.0
    minusvalenze_expiry_year: int = 2028
    capital_gains_tax_rate: float = 0.26
    gov_bond_tax_rate: float = 0.125


@dataclass
class RebalanceConstraints:
    """Vincoli e pesi di penalizzazione della funzione obiettivo."""
    min_cash_buffer_eur: float = 2000.0
    max_turnover_pct: float = 50.0
    max_single_weight: float = 0.40
    tracking_error_weight: float = 10.0
    tax_penalty_weight: float = 0.02
    turnover_penalty_weight: float = 0.01
    impact_penalty_weight: float = 0.01


@dataclass
class FIXOrder:
    """Ordine conforme allo standard FIX Protocol 4.4 per sistemi OMS/EMS."""
    cl_ord_id: str
    symbol: str
    side: str  # 1 = BUY, 2 = SELL
    order_qty: int
    order_type: str  # 1 = MARKET, 2 = LIMIT
    limit_price: float
    estimated_tax_eur: float
    estimated_slippage_eur: float
    time_in_force: str = "0"  # 0 = DAY, 3 = IOC, 4 = FOK
    sending_time: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H:%M:%S"))

    def to_fix_string(self) -> str:
        """Serializza in formato standard FIX delimitato da pipe (rappresentante SOH)."""
        side_tag = "1" if self.side.upper() in ["BUY", "1"] else "2"
        ord_type_tag = "2" if self.order_type.upper() in ["LIMIT", "2"] else "1"
        body = (
            f"8=FIX.4.4|35=D|11={self.cl_ord_id}|55={self.symbol}|54={side_tag}|"
            f"38={self.order_qty}|40={ord_type_tag}|44={self.limit_price:.2f}|"
            f"59={self.time_in_force}|60={self.sending_time}"
        )
        # Checksum fittizio a 3 cifre conforme FIX
        checksum = sum(ord(c) for c in body) % 256
        return f"{body}|10={checksum:03d}|"


class PrescriptiveConicRebalancer:
    """
    Motore prescrittivo di ribilanciamento multi-obiettivo con ottimizzazione convessa/SLSQP.
    """

    def __init__(self, tax_wallet: Optional[TaxWalletState] = None):
        self.tax_wallet = tax_wallet or TaxWalletState()

    def _estimate_almgren_chriss_impact(
        self,
        trade_val_eur: float,
        adv_eur: float,
        vol_daily: float = 0.015,
        gamma: float = 0.10,
        eta: float = 0.15
    ) -> float:
        """
        Stima dell'impatto di mercato temporaneo e permanente secondo il modello Almgren-Chriss (2000).
        """
        if adv_eur <= 0 or trade_val_eur <= 0:
            return 0.0
        participation_rate = trade_val_eur / max(adv_eur, 1e-4)
        permanent_impact = gamma * vol_daily * participation_rate
        temporary_impact = eta * vol_daily * (participation_rate ** 0.5)
        return trade_val_eur * (permanent_impact + temporary_impact)

    def optimize_rebalance(
        self,
        positions: List[PositionLot],
        target_weights: Dict[str, float],
        available_cash_eur: float,
        constraints: Optional[RebalanceConstraints] = None,
        covariance_matrix: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Esegue l'ottimizzazione vincolata del ribilanciamento:
        minimizza Tracking Error, Tasse su Plusvalenze (con assorbimento minus), Turnover e Market Impact.
        """
        cons = constraints or RebalanceConstraints()
        tickers = [p.ticker for p in positions]
        n_assets = len(positions)

        curr_prices = np.array([p.current_price for p in positions])
        curr_shares = np.array([p.shares for p in positions])
        curr_values = curr_shares * curr_prices
        total_portfolio_equity = float(np.sum(curr_values))
        total_wealth = total_portfolio_equity + available_cash_eur

        if total_wealth <= 0 or n_assets == 0:
            return {"error": "Patrimonio insufficiente o posizioni vuote."}

        initial_weights = curr_values / total_wealth
        target_w_arr = np.array([target_weights.get(t, 0.0) for t in tickers])
        # Normalizza target se somma > 1 - min_cash_pct
        max_investable_pct = max(0.0, 1.0 - (cons.min_cash_buffer_eur / total_wealth))
        if np.sum(target_w_arr) > max_investable_pct and np.sum(target_w_arr) > 0:
            target_w_arr = target_w_arr / np.sum(target_w_arr) * max_investable_pct

        # Se covarianza non fornita, usa matrice identità scalata
        if covariance_matrix is None or covariance_matrix.shape != (n_assets, n_assets):
            cov = np.eye(n_assets) * 0.0003
        else:
            cov = covariance_matrix

        cov_annual = cov * 252.0 if (float(np.trace(cov)) / n_assets) < 0.01 else cov

        # Funzione Obiettivo Multi-Criterio
        # w: vettore dei nuovi pesi investiti
        def objective(w: np.ndarray) -> float:
            diff_w = w - target_w_arr
            tracking_error_pen = float(diff_w.T @ cov_annual @ diff_w)

            # Turnover
            trade_w = np.abs(w - initial_weights)
            turnover_pen = float(np.sum(trade_w))

            # Impatto fiscale approssimato per vendite (w_i < w_0,i)
            tax_est = 0.0
            for i, p in enumerate(positions):
                if w[i] < initial_weights[i]:
                    sold_fraction = (initial_weights[i] - w[i]) / max(initial_weights[i], 1e-6)
                    sold_shares = sold_fraction * p.shares
                    gain = max(0.0, (p.current_price - p.pmc) * sold_shares)
                    tax_rate = self.tax_wallet.gov_bond_tax_rate if "Gov" in p.asset_class else self.tax_wallet.capital_gains_tax_rate
                    tax_est += gain * tax_rate

            tax_pen = tax_est / total_wealth

            # Market Impact
            impact_pen = 0.0
            for i, p in enumerate(positions):
                trade_val = abs(w[i] - initial_weights[i]) * total_wealth
                impact = self._estimate_almgren_chriss_impact(trade_val, p.adv_eur)
                spread_cost = trade_val * (p.bid_ask_spread_bps / 10000.0)
                impact_pen += (impact + spread_cost) / total_wealth

            return (
                cons.tracking_error_weight * tracking_error_pen +
                cons.turnover_penalty_weight * turnover_pen +
                cons.tax_penalty_weight * tax_pen +
                cons.impact_penalty_weight * impact_pen
            )

        # Vincoli SLSQP
        # 1. Somma pesi <= max_investable_pct
        bounds = [(0.0, min(cons.max_single_weight, 1.0)) for _ in range(n_assets)]
        scipy_cons = [
            {"type": "ineq", "fun": lambda w: max_investable_pct - np.sum(w)},
            {"type": "ineq", "fun": lambda w: (cons.max_turnover_pct / 100.0) - np.sum(np.abs(w - initial_weights))}
        ]

        # Soluzione iniziale = target w
        x0 = np.clip(target_w_arr, 0.0, cons.max_single_weight)
        if np.sum(x0) > max_investable_pct:
            x0 = x0 / np.sum(x0) * max_investable_pct

        res = minimize(
            objective,
            x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=scipy_cons,
            options={"maxiter": 200, "ftol": 1e-7}
        )

        final_w = res.x if res.success else x0
        final_w = np.clip(final_w, 0.0, cons.max_single_weight)

        # Generazione Operazioni & Ordini FIX
        blotter: List[FIXOrder] = []
        trade_items: List[Dict[str, Any]] = []

        remaining_minus = self.tax_wallet.minusvalenze_available_eur
        total_tax_due = 0.0
        total_minus_absorbed = 0.0
        total_slippage_cost = 0.0
        net_cash_flow = 0.0

        for i, p in enumerate(positions):
            target_val = final_w[i] * total_wealth
            diff_val = target_val - curr_values[i]
            if abs(diff_val) < 50.0:  # Soglia di micro-movimentazione ignorata
                continue

            side = "BUY" if diff_val > 0 else "SELL"
            trade_shares = int(round(abs(diff_val) / p.current_price))
            if trade_shares == 0:
                continue

            trade_eur = trade_shares * p.current_price
            slippage_eur = self._estimate_almgren_chriss_impact(trade_eur, p.adv_eur) + (trade_eur * p.bid_ask_spread_bps / 10000.0)
            total_slippage_cost += slippage_eur

            # Calcolo Fiscale Esatto con Minusvalenze
            tax_bill = 0.0
            minus_absorbed = 0.0
            if side == "SELL":
                realized_pnl = (p.current_price - p.pmc) * trade_shares
                tax_rate = self.tax_wallet.gov_bond_tax_rate if "Gov" in p.asset_class else self.tax_wallet.capital_gains_tax_rate
                
                if realized_pnl > 0:
                    # Plusvalenza: compensabile se equity/ETC/bond con minus disponibili (TUIR Art. 67)
                    # Gli ETF generano Redditi di Capitale (TUIR Art. 44) e NON possono assorbire minusvalenze
                    from core.tax_engine import is_etf
                    is_etf_flag = "ETF" in str(p.asset_class).upper() or is_etf(p.asset_class, p.ticker)

                    if not is_etf_flag and remaining_minus > 0:
                        absorbed = min(remaining_minus, realized_pnl)
                        minus_absorbed = absorbed
                        remaining_minus -= absorbed
                        taxable = realized_pnl - absorbed
                    else:
                        taxable = realized_pnl
                    tax_bill = taxable * tax_rate
                else:
                    # Nuova minusvalenza generata
                    remaining_minus += abs(realized_pnl)

                total_tax_due += tax_bill
                total_minus_absorbed += minus_absorbed
                net_cash_flow += (trade_eur - tax_bill - slippage_eur)
            else:
                net_cash_flow -= (trade_eur + slippage_eur)

            # Prezzo limite di esecuzione difensivo (±10 bps per limit order)
            limit_px = p.current_price * 1.001 if side == "BUY" else p.current_price * 0.999
            cl_ord_id = f"ARGUS-{p.ticker}-{side[:1]}-{int(datetime.datetime.now().timestamp())}"

            order = FIXOrder(
                cl_ord_id=cl_ord_id,
                symbol=p.ticker,
                side=side,
                order_qty=trade_shares,
                order_type="LIMIT",
                limit_price=limit_px,
                estimated_tax_eur=tax_bill,
                estimated_slippage_eur=slippage_eur
            )
            blotter.append(order)

            trade_items.append({
                "cl_ord_id": cl_ord_id,
                "ticker": p.ticker,
                "side": side,
                "shares": trade_shares,
                "market_price": p.current_price,
                "limit_price": limit_px,
                "trade_eur": trade_eur,
                "realized_gain_eur": (p.current_price - p.pmc) * trade_shares if side == "SELL" else 0.0,
                "minus_absorbed_eur": minus_absorbed,
                "tax_bill_eur": tax_bill,
                "slippage_eur": slippage_eur,
                "weight_before_pct": initial_weights[i] * 100.0,
                "weight_after_pct": final_w[i] * 100.0,
                "fix_msg": order.to_fix_string()
            })

        projected_cash = available_cash_eur + net_cash_flow
        final_turnover_pct = float(np.sum(np.abs(final_w - initial_weights))) * 50.0

        return {
            "success": res.success,
            "iterations": res.nit,
            "total_wealth_eur": total_wealth,
            "available_cash_before_eur": available_cash_eur,
            "projected_cash_after_eur": projected_cash,
            "turnover_pct": final_turnover_pct,
            "total_tax_due_eur": total_tax_due,
            "total_minusvalenze_absorbed_eur": total_minus_absorbed,
            "remaining_minusvalenze_eur": remaining_minus,
            "total_market_impact_slippage_eur": total_slippage_cost,
            "trades_count": len(trade_items),
            "trades_df": pd.DataFrame(trade_items),
            "fix_blotter_raw": "\n".join([o.to_fix_string() for o in blotter]),
            "optimized_weights": dict(zip(tickers, final_w.tolist()))
        }
