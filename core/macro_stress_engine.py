# ============================================================
# core/macro_stress_engine.py
# ARGUS — Institutional Macro Stress Testing & Reverse Stress Engine
# Aligned with EBA Adverse, Fed CCAR & Regulatory Multi-Factor Shocks
# ============================================================

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def get_standard_macro_scenarios() -> Dict[str, Dict[str, Any]]:
    """Restituisce gli scenari di stress macroeconomico istituzionali standard."""
    return {
        "EBA_Adverse_2026": {
            "name": "EBA Regulatory Adverse 2026",
            "description": "Scenario avverso European Banking Authority: contrazione PIL -2.5%, crash azionario -30%, allargamento spread governativi e corporate.",
            "equity_shock_pct": -30.0,
            "bonds_rate_shock_bps": 150.0,
            "credit_spread_shock_bps": 120.0,
            "commodities_shock_pct": -10.0,
            "fx_usd_shock_pct": 5.0,
            "volatility_multiplier": 1.75
        },
        "Fed_CCAR_Severe": {
            "name": "Fed CCAR Severely Adverse",
            "description": "Scenario severo Federal Reserve: shock azionario globale -45%, calo immobiliare -25%, crollo tassi nominali flight-to-safety (-100 bps).",
            "equity_shock_pct": -45.0,
            "bonds_rate_shock_bps": -100.0,
            "credit_spread_shock_bps": 300.0,
            "commodities_shock_pct": -25.0,
            "fx_usd_shock_pct": -8.0,
            "volatility_multiplier": 2.20
        },
        "Stagflation_Energy_Spike": {
            "name": "Stagflazione & Shock Energetico",
            "description": "Impennata commodities energetiche +40%, inflazione elevata, rialzo tassi BCE/Fed +200 bps e contrazione multipli azionari -20%.",
            "equity_shock_pct": -20.0,
            "bonds_rate_shock_bps": 200.0,
            "credit_spread_shock_bps": 180.0,
            "commodities_shock_pct": 40.0,
            "fx_usd_shock_pct": 10.0,
            "volatility_multiplier": 1.60
        },
        "Geopolitical_Risk_Off": {
            "name": "Crisi Geopolitica Globale (Risk-Off)",
            "description": "Fuga verso la liquidità e beni rifugio: oro +25%, petrolio +50%, equity -35%, allargamento spread High Yield +350 bps.",
            "equity_shock_pct": -35.0,
            "bonds_rate_shock_bps": -50.0,
            "credit_spread_shock_bps": 350.0,
            "commodities_shock_pct": 30.0,
            "fx_usd_shock_pct": 12.0,
            "volatility_multiplier": 2.50
        }
    }


def compute_macro_scenario_stress_test(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    custom_scenarios: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Calcola l'impatto sul valore di portafoglio sotto scenari macroeconomici istituzionali (EBA/Fed CCAR).
    """
    scenarios = custom_scenarios or get_standard_macro_scenarios()

    total_val = 0.0
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        total_val = float(df_positions["controvalore"].sum())
    elif results and "valore_totale" in results:
        total_val = float(results["valore_totale"])
    if total_val <= 0:
        total_val = 100000.0

    weights = {"equity": 0.60, "bonds": 0.30, "commodities": 0.05, "cash": 0.05}
    if df_positions is not None and not df_positions.empty:
        if "asset_class" in df_positions.columns and "controvalore" in df_positions.columns:
            tot = df_positions["controvalore"].sum()
            if tot > 0:
                ac_grp = df_positions.groupby("asset_class")["controvalore"].sum() / tot
                eq_w = float(ac_grp.get("Azionario", ac_grp.get("Equity", 0.0)))
                bd_w = float(ac_grp.get("Obbligazionario", ac_grp.get("Bond", 0.0)))
                cm_w = float(ac_grp.get("Materie Prime", ac_grp.get("Commodity", 0.0)))
                ca_w = float(ac_grp.get("Liquidità", ac_grp.get("Cash", 0.0)))
                sum_w = eq_w + bd_w + cm_w + ca_w
                if sum_w > 0:
                    weights = {"equity": eq_w / sum_w, "bonds": bd_w / sum_w, "commodities": cm_w / sum_w, "cash": ca_w / sum_w}

    scenario_results = []
    duration_assumed = 5.5

    for sc_key, sc in scenarios.items():
        eq_shock = float(sc.get("equity_shock_pct", -20.0)) / 100.0
        rate_bps = float(sc.get("bonds_rate_shock_bps", 100.0))
        spread_bps = float(sc.get("credit_spread_shock_bps", 50.0))
        comm_shock = float(sc.get("commodities_shock_pct", 0.0)) / 100.0

        bond_yield_delta = (rate_bps + spread_bps) / 10000.0
        bond_impact = -duration_assumed * bond_yield_delta

        port_return = (
            weights["equity"] * eq_shock +
            weights["bonds"] * bond_impact +
            weights["commodities"] * comm_shock +
            weights["cash"] * 0.0
        )

        loss_eur = total_val * port_return
        post_shock_val = total_val + loss_eur

        scenario_results.append({
            "scenario_key": sc_key,
            "scenario_name": sc.get("name", sc_key),
            "description": sc.get("description", ""),
            "equity_shock_pct": sc.get("equity_shock_pct", 0.0),
            "rate_shock_bps": rate_bps,
            "credit_spread_bps": spread_bps,
            "commodities_shock_pct": sc.get("commodities_shock_pct", 0.0),
            "portfolio_return_pct": round(port_return * 100.0, 2),
            "pnl_impact_eur": round(loss_eur, 2),
            "post_shock_value_eur": round(post_shock_val, 2),
            "volatility_multiplier": sc.get("volatility_multiplier", 1.5)
        })

    df_out = pd.DataFrame(scenario_results)
    worst = min(scenario_results, key=lambda x: x["portfolio_return_pct"]) if scenario_results else {}

    return {
        "initial_portfolio_value_eur": round(total_val, 2),
        "scenarios_count": len(scenario_results),
        "scenario_results": scenario_results,
        "scenarios_df": df_out,
        "worst_case_scenario": worst.get("scenario_name", "N/D"),
        "worst_case_drawdown_pct": worst.get("portfolio_return_pct", 0.0),
        "worst_case_loss_eur": worst.get("pnl_impact_eur", 0.0),
        "asset_weights_used": {k: round(v * 100.0, 1) for k, v in weights.items()}
    }


def compute_reverse_stress_test(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    target_drawdown_pct: float = -20.0
) -> Dict[str, Any]:
    """
    Reverse Stress Testing: Determina la combinazione minima di shock congiunti (Azionario & Tassi)
    necessaria per causare una perdita target specificata.
    """
    total_val = 0.0
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        total_val = float(df_positions["controvalore"].sum())
    elif results and "valore_totale" in results:
        total_val = float(results["valore_totale"])
    if total_val <= 0:
        total_val = 100000.0

    eq_weight = 0.65
    bd_weight = 0.35
    duration = 5.5

    if df_positions is not None and not df_positions.empty and "asset_class" in df_positions.columns:
        tot = df_positions["controvalore"].sum()
        if tot > 0:
            ac_grp = df_positions.groupby("asset_class")["controvalore"].sum() / tot
            eq_weight = float(ac_grp.get("Azionario", ac_grp.get("Equity", 0.65)))
            bd_weight = max(0.01, 1.0 - eq_weight)

    target_loss = abs(target_drawdown_pct) / 100.0

    pure_eq_crash = -(target_loss / max(eq_weight, 0.01)) * 100.0
    pure_rate_shock_bps = (target_loss / (max(bd_weight, 0.01) * duration)) * 10000.0

    half_loss = target_loss / 2.0
    comb_eq_crash = -(half_loss / max(eq_weight, 0.01)) * 100.0
    comb_rate_bps = (half_loss / (max(bd_weight, 0.01) * duration)) * 10000.0

    vol_eq = 0.18
    z_score = abs(comb_eq_crash / 100.0) / vol_eq
    implied_event_rarity = f"1 evento ogni {max(1, int(np.exp(min(z_score**2 / 2, 20))))} anni"

    return {
        "target_drawdown_pct": target_drawdown_pct,
        "target_loss_eur": round(total_val * (target_drawdown_pct / 100.0), 2),
        "initial_portfolio_value_eur": round(total_val, 2),
        "break_even_solutions": {
            "pure_equity_crash_pct": round(pure_eq_crash, 1),
            "pure_rate_shock_bps": round(pure_rate_shock_bps, 0),
            "combined_scenario": {
                "equity_crash_pct": round(comb_eq_crash, 1),
                "rate_shock_bps": round(comb_rate_bps, 0)
            }
        },
        "implied_z_score": round(float(z_score), 2),
        "implied_frequency_estimate": implied_event_rarity,
        "risk_weights": {"equity_pct": round(eq_weight * 100.0, 1), "bonds_pct": round(bd_weight * 100.0, 1)}
    }
