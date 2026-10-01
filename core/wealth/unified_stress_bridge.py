# ==============================================================================
# core/wealth/unified_stress_bridge.py
# ARGUS — Unified Multi-Asset Factor Stress-Testing Engine
# Holistic Balance Sheet Shock Propagation (Risk ↔ Wealth Convergence)
# ==============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class MacroFactorShock:
    """
    Rappresenta un vettore di shock macroeconomico coerente.
    """

    equity_mkt_pct: float = -0.20  # es. -0.20 (-20% azionario globale)
    yield_curve_shift_bps: float = 150.0  # es. +150 bps rialzo tassi
    inflation_rate_pct: float = 0.04  # es. +0.04 (+4% inflazione aggiuntiva)
    fx_eur_usd_pct: float = 0.0  # es. -0.05 (-5% deprezzamento EUR)
    credit_spread_bps: float = 50.0  # es. +50 bps allargamento spread
    scenario_name: str = "Macro Factor Shock"


class UnifiedCrossAssetStressEngine:
    """
    Motore quantitativo di propagazione congiunta degli shock macroeconomici:
    Collega il portafoglio titoli liquido alle grandezze patrimoniali del bilancio
    familiare/aziendale (debito, immobili, liquidità di riserva e SWR).
    """

    def __init__(self, portfolio_positions: Optional[pd.DataFrame] = None, factor_betas: Optional[pd.DataFrame] = None):
        """
        :param portfolio_positions: DataFrame con colonne [ticker, weight/controvalore, asset_class, duration]
        :param factor_betas: DataFrame opzionale con [ticker, beta_mkt, beta_rates, beta_fx]
        """
        self.positions = portfolio_positions.copy() if portfolio_positions is not None else pd.DataFrame()
        self.betas = factor_betas.copy() if factor_betas is not None else pd.DataFrame()

    def evaluate_integrated_shock(self, shock: MacroFactorShock, wealth_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valuta l'impatto economico olistico su tutte le componenti del Total Balance Sheet.
        """
        # 1. VALUTAZIONE PORTAFOGLIO LIQUIDO (Factor Transmission)
        total_liquid_val = float(wealth_snapshot.get("liquid_investments", 0.0))
        liquid_pnl_pct = 0.0

        if not self.positions.empty and "weight" in self.positions.columns:
            pos = self.positions.copy()
            if not self.betas.empty and "ticker" in self.betas.columns:
                merged = pos.merge(self.betas, on="ticker", how="left")
            else:
                merged = pos.copy()

            # Default betas se non presenti
            if "beta_mkt" not in merged.columns:
                merged["beta_mkt"] = np.where(
                    merged.get("asset_class", "equity").str.lower().isin(["equity", "stock", "etf"]), 1.0, 0.15
                )
            if "beta_rates" not in merged.columns:
                merged["beta_rates"] = 0.0
            if "duration" not in merged.columns:
                merged["duration"] = np.where(
                    merged.get("asset_class", "equity").str.lower().isin(["bond", "fixed_income", "obbligazione"]),
                    5.5,
                    0.0,
                )

            merged["beta_mkt"] = merged["beta_mkt"].fillna(1.0)
            merged["beta_rates"] = merged["beta_rates"].fillna(0.0)
            merged["duration"] = merged["duration"].fillna(0.0)

            # Normalizzazione pesi
            sum_w = merged["weight"].sum()
            if sum_w > 0:
                merged["norm_weight"] = merged["weight"] / sum_w
            else:
                merged["norm_weight"] = 1.0 / len(merged)

            # Contributo Equity
            eq_impact = merged["norm_weight"] * (merged["beta_mkt"] * shock.equity_mkt_pct)

            # Contributo Tassi & Convessità
            rate_shift_dec = shock.yield_curve_shift_bps / 10000.0
            convexity_approx = 35.0  # Convessità tipica portafoglio obbligazionario investment grade
            bond_mask = merged.get("asset_class", "equity").str.lower().isin(["bond", "fixed_income", "obbligazione"])

            rate_impact = np.where(
                bond_mask,
                -merged["duration"] * rate_shift_dec + 0.5 * convexity_approx * (rate_shift_dec**2),
                merged["beta_rates"] * rate_shift_dec,
            )

            # Contributo FX
            fx_impact = np.where(
                merged.get("currency", "EUR").str.upper() == "USD",
                -shock.fx_eur_usd_pct,  # Deprezzamento EUR = rivalutazione USD
                0.0,
            )

            liquid_pnl_pct = float((eq_impact + merged["norm_weight"] * (rate_impact + fx_impact)).sum())
        else:
            # Fallback macro standard se non vi sono posizioni dettagliate
            rate_shift_dec = shock.yield_curve_shift_bps / 10000.0
            liquid_pnl_pct = (0.65 * shock.equity_mkt_pct) - (0.35 * 6.0 * rate_shift_dec)

        stressed_liquid_val = max(0.0, total_liquid_val * (1.0 + liquid_pnl_pct))
        liquid_pnl_eur = stressed_liquid_val - total_liquid_val

        # 2. IMPATTO IMMOBILIARE (Cap-Rate Elasticity Model)
        re_gross = float(wealth_snapshot.get("real_estate_gross", wealth_snapshot.get("real_estate_total", 0.0)))
        # Un aumento dei tassi espande i rendimenti richiesti (cap rate elasticity gamma = 0.5)
        rate_shift_dec = shock.yield_curve_shift_bps / 10000.0
        re_drop_pct = -min(0.40, max(0.0, 0.5 * rate_shift_dec * 10.0))
        stressed_re_val = re_gross * (1.0 + re_drop_pct)
        re_pnl_eur = stressed_re_val - re_gross

        # 3. RICALCOLO RATA MUTUO VARIABILE (Ammortamento alla Francese)
        debts = float(wealth_snapshot.get("variable_debt_principal", wealth_snapshot.get("total_liabilities", 0.0)))
        n_months = int(wealth_snapshot.get("mortgage_months_remaining", 240))
        curr_rate = float(wealth_snapshot.get("mortgage_interest_rate", 0.0275))
        new_rate = max(0.005, curr_rate + rate_shift_dec)

        curr_monthly_payment = float(wealth_snapshot.get("current_monthly_payment", 0.0))
        if curr_monthly_payment <= 0 and debts > 0:
            i_base = curr_rate / 12.0
            curr_monthly_payment = debts * (i_base / (1.0 - (1.0 + i_base) ** (-n_months))) if n_months > 0 else 0.0

        if debts > 0 and n_months > 0:
            i_new = new_rate / 12.0
            new_monthly_payment = debts * (i_new / (1.0 - (1.0 + i_new) ** (-n_months)))
        else:
            new_monthly_payment = 0.0

        delta_monthly_debt = max(0.0, new_monthly_payment - curr_monthly_payment)

        # 4. CASH RUNWAY & POINT OF FORCED LIQUIDATION
        monthly_expenses_base = float(wealth_snapshot.get("monthly_expenses", 2500.0))
        monthly_income_base = float(wealth_snapshot.get("monthly_income", monthly_expenses_base * 1.3))

        stressed_expenses = (monthly_expenses_base * (1.0 + shock.inflation_rate_pct)) + delta_monthly_debt
        stressed_income = monthly_income_base  # Assume reddito fisso nel breve termine

        net_burn = max(0.0, stressed_expenses - stressed_income)
        liquid_cash = float(wealth_snapshot.get("cash_reserves", wealth_snapshot.get("liquid_cash", 15000.0)))

        if net_burn > 0:
            months_to_forced_sale = round(liquid_cash / net_burn, 1)
        else:
            months_to_forced_sale = 999.0

        forced_liquidation_triggered = months_to_forced_sale < 18.0

        # Calcolo del Capital Shortfall e della Perdita Irreversibile da Liquidazione Forzata
        if forced_liquidation_triggered and months_to_forced_sale < 24.0:
            deficit_months = 24.0 - months_to_forced_sale
            capital_shortfall_eur = round(deficit_months * net_burn, 2)
            # Perdita irreversibile: svendere asset al punto di minimo dello shock
            drop_mag = abs(min(0.0, liquid_pnl_pct))
            irreversible_loss_eur = round(capital_shortfall_eur * (drop_mag / max(0.05, 1.0 - drop_mag)), 2)
        else:
            capital_shortfall_eur = 0.0
            irreversible_loss_eur = 0.0

        # 5. DYNAMIC SAFE WITHDRAWAL RATE (Guyton-Klinger Rules)
        base_swr = float(wealth_snapshot.get("fire_swr_base", 3.75))
        eq_penalty = 0.15 if abs(shock.equity_mkt_pct) >= 0.20 else (0.08 if abs(shock.equity_mkt_pct) >= 0.10 else 0.0)
        cpi_penalty = 0.10 if shock.inflation_rate_pct >= 0.04 else 0.0
        stressed_swr = max(2.20, round(base_swr * (1.0 - eq_penalty - cpi_penalty), 2))

        # 6. TOTAL BALANCE SHEET NET WORTH RECONCILIATION
        pre_nw = (total_liquid_val + re_gross + float(wealth_snapshot.get("pension_total", 0.0)) + liquid_cash) - debts
        pension_pnl = float(wealth_snapshot.get("pension_total", 0.0)) * (liquid_pnl_pct * 0.7)  # Proxy bilanciato
        stressed_nw = pre_nw + liquid_pnl_eur + re_pnl_eur + pension_pnl

        return {
            "scenario_name": shock.scenario_name,
            "liquid_pnl_pct": round(liquid_pnl_pct * 100.0, 2),
            "liquid_pnl_eur": round(liquid_pnl_eur, 2),
            "stressed_liquid_val": round(stressed_liquid_val, 2),
            "real_estate_pnl_pct": round(re_drop_pct * 100.0, 2),
            "stressed_re_val": round(stressed_re_val, 2),
            "curr_monthly_payment": round(curr_monthly_payment, 2),
            "new_monthly_payment": round(new_monthly_payment, 2),
            "delta_monthly_debt": round(delta_monthly_debt, 2),
            "stressed_monthly_expenses": round(stressed_expenses, 2),
            "net_monthly_burn": round(net_burn, 2),
            "months_to_forced_liquidation": months_to_forced_sale,
            "forced_liquidation_alert": forced_liquidation_triggered,
            "capital_shortfall_eur": capital_shortfall_eur,
            "irreversible_loss_eur": irreversible_loss_eur,
            "fire_swr_base_pct": base_swr,
            "fire_swr_stressed_pct": stressed_swr,
            "pre_stress_net_worth": round(pre_nw, 2),
            "post_stress_net_worth": round(stressed_nw, 2),
            "total_net_worth_pnl_pct": round(((stressed_nw / max(1.0, pre_nw)) - 1.0) * 100.0, 2),
        }


def map_global_macro_preset_to_factor_shock(preset_key: str) -> MacroFactorShock:
    """Mappa il preset di shock macroeconomico globale di ARGUS su un vettore di shock multi-asset."""
    clean_k = str(preset_key or "NONE").upper().strip()
    if clean_k == "GFC_2008":
        return MacroFactorShock(
            equity_mkt_pct=-0.35,
            yield_curve_shift_bps=-125.0,
            inflation_rate_pct=0.01,
            fx_eur_usd_pct=-0.08,
            credit_spread_bps=350.0,
            scenario_name="Global Financial Crisis 2008 (Deflationary Credit Crunch)",
        )
    elif clean_k == "STAGFLATION_SHOCK":
        return MacroFactorShock(
            equity_mkt_pct=-0.18,
            yield_curve_shift_bps=200.0,
            inflation_rate_pct=0.06,
            fx_eur_usd_pct=-0.04,
            credit_spread_bps=160.0,
            scenario_name="Stagflation & Rate Spike (+200bps / Inflation 6%)",
        )
    elif clean_k == "LIQUIDITY_FREEZE":
        return MacroFactorShock(
            equity_mkt_pct=-0.15,
            yield_curve_shift_bps=50.0,
            inflation_rate_pct=0.02,
            fx_eur_usd_pct=-0.02,
            credit_spread_bps=220.0,
            scenario_name="Flash Crash & Order Flow Toxicity (Liquidity Freeze)",
        )
    else:
        return MacroFactorShock(
            equity_mkt_pct=0.0,
            yield_curve_shift_bps=0.0,
            inflation_rate_pct=0.0,
            fx_eur_usd_pct=0.0,
            credit_spread_bps=0.0,
            scenario_name="Baseline Normal Market",
        )


def evaluate_active_wealth_macro_shock(
    wealth_snapshot: Dict[str, Any],
    session_state_dict: Optional[Dict[str, Any]] = None,
    portfolio_positions: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Valuta l'impatto economico olistico dello shock macro globale attivo sul bilancio consolidato Wealth."""
    import streamlit as st

    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if hasattr(st, "session_state") else {}
    )
    preset_key = str(state.get("global_macro_shock", "NONE")).upper()
    shock = map_global_macro_preset_to_factor_shock(preset_key)
    engine = UnifiedCrossAssetStressEngine(portfolio_positions=portfolio_positions)
    results = engine.evaluate_integrated_shock(shock, wealth_snapshot)
    results["is_shock_active"] = preset_key != "NONE"
    results["global_preset_key"] = preset_key
    return results


def render_cross_portal_stress_bridge_banner(
    wealth_snapshot: Optional[Dict[str, Any]] = None,
    portfolio_id: Optional[int] = None,
    key_suffix: str = "",
) -> Optional[Dict[str, Any]]:
    """Renderizza il banner istituzionale del Cross-Portal Macro Stress Bridge se uno shock globale è attivo."""
    import streamlit as st

    from core.ui_utils import fmt_eur, metric_card

    preset_key = str(st.session_state.get("global_macro_shock", "NONE")).upper().strip()
    if preset_key == "NONE" or not preset_key:
        return None

    # Costruisci snapshot di base se non fornito
    snap = wealth_snapshot
    if snap is None:
        snap = {
            "total_net_worth": float(st.session_state.get("wealth_total_net_worth", 1_250_000.0)),
            "liquid_cash": float(st.session_state.get("wealth_liquid_cash", 120_000.0)),
            "financial_investments": float(st.session_state.get("wealth_financial_investments", 650_000.0)),
            "real_estate_total": float(st.session_state.get("wealth_real_estate_total", 480_000.0)),
            "total_liabilities": float(st.session_state.get("wealth_total_liabilities", 110_000.0)),
            "runway_months": float(st.session_state.get("wealth_runway_months", 14.5)),
            "fixed_mortgages_balance": float(st.session_state.get("wealth_total_liabilities", 110_000.0) * 0.7),
            "variable_mortgages_balance": float(st.session_state.get("wealth_total_liabilities", 110_000.0) * 0.3),
        }

    pos_df = None
    last_res = st.session_state.get("last_portfolio_result")
    if isinstance(last_res, dict) and "positions" in last_res:
        pos_df = last_res["positions"]

    res = evaluate_active_wealth_macro_shock(snap, portfolio_positions=pos_df)
    s_name = res.get("scenario_name", preset_key)
    pnl_pct = res.get("total_net_worth_pnl_pct", 0.0)
    pnl_eur = res.get("total_wealth_pnl_eur", 0.0)
    s_nw = res.get("post_stress_net_worth", snap.get("total_net_worth", 0.0))
    s_runway = res.get("stressed_runway_months", snap.get("runway_months", 0.0))
    pmt_delta = res.get("pmt_monthly_delta_eur", 0.0)
    re_haircut = res.get("real_estate_haircut_eur", 0.0)

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(30, 27, 46, 0.95) 100%);
                    border: 1px solid rgba(239, 68, 68, 0.45);
                    border-left: 4px solid #ef4444;
                    border-radius: 10px;
                    padding: 12px 18px;
                    margin-bottom: 14px;
                    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="background: #ef4444; color: #ffffff; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;">
                        ⚡ MACRO STRESS BRIDGE ATTIVO
                    </span>
                    <span style="color: #f87171; font-weight: 700; font-size: 13.5px;">
                        {s_name}
                    </span>
                </div>
                <div style="font-size: 11.5px; color: #94a3b8; font-family: 'JetBrains Mono', monospace;">
                    Simulazione trasversale dal Terminale Rischio
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card(
            "Patrimonio Netto Stressed",
            fmt_eur(s_nw),
            delta=f"{pnl_eur:+,.0f} € ({pnl_pct:+.2f}%)".replace(",", "."),
            delta_color="inverse" if pnl_pct < 0 else "normal",
        )
    with k2:
        metric_card(
            "Shock Portafoglio Liquido",
            fmt_eur(res.get("liquid_portfolio_shock_eur", 0.0)),
            delta="Beta & Duration Trasmesse",
            delta_color="inverse",
        )
    with k3:
        metric_card(
            "Haircut Immobiliare",
            fmt_eur(-abs(re_haircut)),
            delta=f"Valore Stressed: {fmt_eur(res.get('post_stress_real_estate', 0.0))}",
            delta_color="inverse",
        )
    with k4:
        r_delta_str = f"Runway: {s_runway:.1f}m (era {snap.get('runway_months', 0.0):.1f}m)"
        metric_card(
            "Rata Mutuo Variabile (Δ PMT)",
            f"{pmt_delta:+,.0f} €/mese".replace(",", "."),
            delta=r_delta_str,
            delta_color="inverse" if pmt_delta > 0 else "normal",
        )

    b1, b2, _ = st.columns([1.5, 2.0, 4.0])
    with b1:
        if st.button("🔄 Reset Shock (Baseline)", key=f"btn_reset_macro_bridge_{key_suffix}", use_container_width=True):
            st.session_state["global_macro_shock"] = "NONE"
            st.rerun()
    with b2:
        if st.button("🌪️ Approfondisci in Stress Testing →", key=f"btn_goto_stress_bridge_{key_suffix}", use_container_width=True):
            st.session_state["target_subtab_stress_active_tab"] = "🌐 Total Balance Sheet & Human Capital Stress"
            st.switch_page("pages/7_🌪️_Stress_Testing.py")

    return res


