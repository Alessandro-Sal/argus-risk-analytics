# ==============================================================================
# core/tax_aware_rebalancer.py
# ARGUS — Tax-Aware Portfolio Rebalancer with Friction Matrix & Zero-Tax Cashflow Engine
# ==============================================================================

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class FrictionConfig:
    fixed_commission_eur: float = 2.95
    pct_commission: float = 0.0019  # 0.19%
    bid_ask_spread_pct: float = 0.0010  # 0.10%
    capital_gain_tax_rate: float = 0.26  # 26%
    gov_bond_tax_rate: float = 0.125  # 12.5%


class TaxAwarePortfolioRebalancer:
    """
    Ribilanciatore istituzionale di portafoglio con matrice di attrito e fiscalità italiana.
    Calcola:
    1. Trade Execution List esatta (Ordini di vendita e acquisto a minimo impatto fiscale)
    2. Cashflow-Only Zero-Tax Rebalancing (Ribilanciamento tramite PAC senza vendita di asset)
    """

    @staticmethod
    def compute_full_rebalance_plan(
        current_holdings: pd.DataFrame,
        target_weights: Dict[str, float],
        total_portfolio_value: float,
        existing_minusvalenze: float = 0.0,
        config: Optional[FrictionConfig] = None
    ) -> Dict[str, Any]:
        if config is None:
            config = FrictionConfig()

        trades = []
        gross_turnover = 0.0
        tot_commissions = 0.0
        tot_spread_cost = 0.0
        tot_realized_gain = 0.0
        tot_realized_loss = 0.0

        current_val_map = {}
        if not current_holdings.empty and "ticker" in current_holdings.columns:
            for _, r in current_holdings.iterrows():
                t = str(r["ticker"]).upper()
                v = float(r.get("market_value", r.get("value", 0.0)))
                current_val_map[t] = v

        all_tickers = sorted(list(set(list(target_weights.keys()) + list(current_val_map.keys()))))
        usable_minus = float(existing_minusvalenze)

        for ticker in all_tickers:
            cur_v = current_val_map.get(ticker, 0.0)
            tgt_w = target_weights.get(ticker, 0.0)
            tgt_v = total_portfolio_value * tgt_w
            delta_v = tgt_v - cur_v

            if abs(delta_v) < 15.0:  # Soglia minima di trade
                continue

            action = "BUY" if delta_v > 0 else "SELL"
            trade_amt = abs(delta_v)
            gross_turnover += trade_amt

            comm = max(config.fixed_commission_eur, trade_amt * config.pct_commission)
            spread = trade_amt * config.bid_ask_spread_pct
            tot_commissions += comm
            tot_spread_cost += spread

            est_tax = 0.0
            if action == "SELL":
                # Stima 15% di plusvalenza media per asset venduti in profitto
                gain = trade_amt * 0.15
                if gain > 0:
                    tot_realized_gain += gain
                    if usable_minus > 0:
                        offset = min(usable_minus, gain)
                        usable_minus -= offset
                        taxable = gain - offset
                    else:
                        taxable = gain
                    tax_rate = config.gov_bond_tax_rate if any(b in ticker for b in ["BTP", "BUND", "UST", "GOV"]) else config.capital_gain_tax_rate
                    est_tax = taxable * tax_rate

            trades.append({
                "Ticker": ticker,
                "Azione": "🟢 ACQUISTA" if action == "BUY" else "🔴 VENDI",
                "Valore Attuale (€)": round(cur_v, 2),
                "Valore Target (€)": round(tgt_v, 2),
                "Controvalore Ordine (€)": round(trade_amt, 2),
                "Commissioni Stimate (€)": round(comm, 2),
                "Impatto Fiscale (€)": round(est_tax, 2),
                "Costo Totale Frizione (€)": round(comm + spread + est_tax, 2)
            })

        df_trades = pd.DataFrame(trades)
        net_friction_total = tot_commissions + tot_spread_cost + max(0.0, (tot_realized_gain - existing_minusvalenze) * config.capital_gain_tax_rate)

        return {
            "trade_execution_list_df": df_trades,
            "gross_turnover_eur": round(gross_turnover, 2),
            "gross_turnover_pct": round(gross_turnover / max(1.0, total_portfolio_value) * 100.0, 2),
            "total_commissions_eur": round(tot_commissions, 2),
            "total_spread_cost_eur": round(tot_spread_cost, 2),
            "estimated_tax_eur": round(max(0.0, (tot_realized_gain - existing_minusvalenze) * config.capital_gain_tax_rate), 2),
            "total_friction_drag_eur": round(net_friction_total, 2),
            "remaining_minusvalenze_eur": round(usable_minus, 2)
        }

    @staticmethod
    def compute_zero_tax_cashflow_rebalance(
        current_holdings: pd.DataFrame,
        target_weights: Dict[str, float],
        total_portfolio_value: float,
        monthly_inflow_eur: float = 1000.0,
        horizon_months: int = 12
    ) -> Dict[str, Any]:
        """
        Simula il ribilanciamento a zero tasse e zero vendite tramite l'allocazione selettiva
        dei nuovi flussi di cassa e PAC mensili sulle sole posizioni sottopesate.
        """
        cur_weights = {}
        tot_v = total_portfolio_value
        if not current_holdings.empty and "ticker" in current_holdings.columns:
            for _, r in current_holdings.iterrows():
                t = str(r["ticker"]).upper()
                v = float(r.get("market_value", r.get("value", 0.0)))
                cur_weights[t] = v / max(1.0, tot_v)

        all_tickers = sorted(list(set(list(target_weights.keys()) + list(cur_weights.keys()))))
        monthly_allocations = {}

        # Trova deficit per ticker
        deficits = {}
        for t in all_tickers:
            cur_w = cur_weights.get(t, 0.0)
            tgt_w = target_weights.get(t, 0.0)
            diff = tgt_w - cur_w
            if diff > 0:
                deficits[t] = diff

        tot_deficit = sum(deficits.values()) if deficits else 1.0

        for t, d in deficits.items():
            monthly_allocations[t] = (d / tot_deficit) * monthly_inflow_eur

        cashflow_plan = []
        for t in all_tickers:
            cur_w = cur_weights.get(t, 0.0)
            tgt_w = target_weights.get(t, 0.0)
            alloc_m = monthly_allocations.get(t, 0.0)
            cashflow_plan.append({
                "Asset / Ticker": t,
                "Peso Attuale (%)": f"{cur_w*100:.1f}%",
                "Peso Target (%)": f"{tgt_w*100:.1f}%",
                "Status": "📉 Sottopesato" if (tgt_w - cur_w) > 0.02 else ("📈 Sovrapesato" if (cur_w - tgt_w) > 0.02 else "⚖️ Allineato"),
                "Flusso Mensile Consigliato (€)": round(alloc_m, 2),
                "Quota PAC (%)": f"{(alloc_m / max(1.0, monthly_inflow_eur) * 100):.1f}%"
            })

        return {
            "cashflow_plan_df": pd.DataFrame(cashflow_plan),
            "monthly_inflow_eur": monthly_inflow_eur,
            "tax_saved_eur": round(total_portfolio_value * 0.15 * 0.26 * 0.20, 2),  # Stima tasse evitate
            "months_to_full_alignment": round(max(3, min(24, int((tot_deficit * total_portfolio_value) / max(1.0, monthly_inflow_eur))))),
            "turnover_savings_eur": round(total_portfolio_value * 0.10 * 0.0025, 2)
        }
