# ============================================================
# core/macro_stress_engine.py
# ARGUS — Institutional Macro Stress Testing & Reverse Stress Engine
# Aligned with EBA Adverse, Fed CCAR & Regulatory Multi-Factor Shocks
# ============================================================

from typing import Any, Dict, List, Optional

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
            "volatility_multiplier": 1.75,
        },
        "Fed_CCAR_Severe": {
            "name": "Fed CCAR Severely Adverse",
            "description": "Scenario severo Federal Reserve: shock azionario globale -45%, calo immobiliare -25%, crollo tassi nominali flight-to-safety (-100 bps).",
            "equity_shock_pct": -45.0,
            "bonds_rate_shock_bps": -100.0,
            "credit_spread_shock_bps": 300.0,
            "commodities_shock_pct": -25.0,
            "fx_usd_shock_pct": -8.0,
            "volatility_multiplier": 2.20,
        },
        "Stagflation_Energy_Spike": {
            "name": "Stagflazione & Shock Energetico",
            "description": "Impennata commodities energetiche +40%, inflazione elevata, rialzo tassi BCE/Fed +200 bps e contrazione multipli azionari -20%.",
            "equity_shock_pct": -20.0,
            "bonds_rate_shock_bps": 200.0,
            "credit_spread_shock_bps": 180.0,
            "commodities_shock_pct": 40.0,
            "fx_usd_shock_pct": 10.0,
            "volatility_multiplier": 1.60,
        },
        "Geopolitical_Risk_Off": {
            "name": "Crisi Geopolitica Globale (Risk-Off)",
            "description": "Fuga verso la liquidità e beni rifugio: oro +25%, petrolio +50%, equity -35%, allargamento spread High Yield +350 bps.",
            "equity_shock_pct": -35.0,
            "bonds_rate_shock_bps": -50.0,
            "credit_spread_shock_bps": 350.0,
            "commodities_shock_pct": 30.0,
            "fx_usd_shock_pct": 12.0,
            "volatility_multiplier": 2.50,
        },
    }


def _extract_portfolio_values_and_weights(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
) -> Tuple[float, Dict[str, float]]:
    """
    Estrae in modo resiliente il controvalore totale e i pesi per macro asset-class
    supportando sia colonne italiane ('controvalore', 'valore') sia inglesi ('current_value', 'weight_pct').
    """
    total_val = 0.0
    val_col = None
    weight_col = None

    if df_positions is not None and not df_positions.empty:
        for c in ["current_value", "controvalore", "valore", "market_value"]:
            if c in df_positions.columns:
                val_col = c
                break
        for w in ["weight_pct", "weight", "peso", "peso_pct"]:
            if w in df_positions.columns:
                weight_col = w
                break

        if val_col:
            total_val = float(df_positions[val_col].dropna().sum())

    if total_val <= 0 and results:
        for k in ["valore_totale", "portfolio_value", "total_val", "nav"]:
            if k in results and results[k]:
                try:
                    total_val = float(results[k])
                    if total_val > 0:
                        break
                except (ValueError, TypeError):
                    pass

    if total_val <= 0:
        total_val = 100000.0

    weights = {"equity": 0.60, "bonds": 0.30, "commodities": 0.05, "cash": 0.05}

    if df_positions is not None and not df_positions.empty:
        ac_col = None
        for ac in ["asset_class", "Asset Class", "macro_asset_class", "classe_asset"]:
            if ac in df_positions.columns:
                ac_col = ac
                break

        if ac_col:
            calc_col = val_col or weight_col
            if calc_col:
                tot_metric = float(df_positions[calc_col].dropna().sum())
                if tot_metric > 0:
                    ac_grp = df_positions.groupby(ac_col)[calc_col].sum() / tot_metric
                    eq_w = 0.0
                    bd_w = 0.0
                    cm_w = 0.0
                    ca_w = 0.0
                    for k, v in ac_grp.items():
                        k_str = str(k).lower()
                        if any(x in k_str for x in ["azion", "equity", "stock"]):
                            eq_w += float(v)
                        elif any(x in k_str for x in ["obblig", "bond", "fixed", "gov", "credit", "titoli di stato"]):
                            bd_w += float(v)
                        elif any(x in k_str for x in ["materie", "commodit", "gold", "oro"]):
                            cm_w += float(v)
                        elif any(x in k_str for x in ["liquid", "cash", "monetar"]):
                            ca_w += float(v)
                        else:
                            eq_w += float(v)

                    sum_w = eq_w + bd_w + cm_w + ca_w
                    if sum_w > 0:
                        weights = {
                            "equity": eq_w / sum_w,
                            "bonds": bd_w / sum_w,
                            "commodities": cm_w / sum_w,
                            "cash": ca_w / sum_w,
                        }

    return total_val, weights


def compute_macro_scenario_matrix(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    custom_scenarios: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Calcola l'impatto sul valore di portafoglio sotto scenari macroeconomici istituzionali (EBA/Fed CCAR).
    """
    scenarios = custom_scenarios or get_standard_macro_scenarios()
    total_val, weights = _extract_portfolio_values_and_weights(df_positions=df_positions, results=results)

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
            weights["equity"] * eq_shock
            + weights["bonds"] * bond_impact
            + weights["commodities"] * comm_shock
            + weights["cash"] * 0.0
        )

        loss_eur = total_val * port_return
        post_shock_val = total_val + loss_eur

        scenario_results.append(
            {
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
                "volatility_multiplier": sc.get("volatility_multiplier", 1.5),
            }
        )

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
        "asset_weights_used": {k: round(v * 100.0, 1) for k, v in weights.items()},
    }


# Alias per retrocompatibilità con le pagine e i test
compute_macro_scenario_stress_test = compute_macro_scenario_matrix


def compute_reverse_stress_test(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    target_drawdown_pct: float = -20.0,
) -> Dict[str, Any]:
    """
    Reverse Stress Testing: Determina la combinazione minima di shock congiunti (Azionario & Tassi)
    necessaria per causare una perdita target specificata.
    """
    total_val, weights = _extract_portfolio_values_and_weights(df_positions=df_positions, results=results)
    eq_weight = max(0.01, weights.get("equity", 0.65))
    bd_weight = max(0.01, weights.get("bonds", 0.35))
    duration = 5.5

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
                "rate_shock_bps": round(comb_rate_bps, 0),
            },
        },
        "implied_z_score": round(float(z_score), 2),
        "implied_frequency_estimate": implied_event_rarity,
        "risk_weights": {"equity_pct": round(eq_weight * 100.0, 1), "bonds_pct": round(bd_weight * 100.0, 1)},
    }


# ── Total Consolidated Wealth Macro Stress Engine ────────────────


def compute_consolidated_wealth_stress_test(
    net_worth_data: Any,
    custom_scenarios: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Stress Testing Macroeconomico Consolidato sull'Intero Patrimonio Netto (Total Wealth).
    Applica gli shock EBA/Fed CCAR/Stagflazione a tutte le macro-classi dell'Attivo
    (Liquidità, Investimenti Finanziari, Immobili, Fondi Pensione, Beni di Lusso/Orologi, Partecipazioni)
    e valuta la resilienza del Patrimonio Netto e l'effetto leva dell'indebitamento (Debt-to-Assets).
    """
    # 1. Estrazione delle componenti patrimoniali
    cat_vals = {
        "liquidita": 0.0,
        "investimenti": 0.0,
        "immobili": 0.0,
        "previdenza": 0.0,
        "beni_lusso": 0.0,
        "partecipazioni": 0.0,
        "passivo": 0.0,
    }

    if isinstance(net_worth_data, dict):
        if "stato_patrimoniale" in net_worth_data:
            sp = net_worth_data["stato_patrimoniale"]
            att = sp.get("attivo", {})
            for sez in att.get("sezioni", []):
                cod = str(sez.get("codice", "")).upper()
                tot = float(sez.get("totale", 0.0) or 0.0)
                if cod == "A":
                    cat_vals["liquidita"] += tot
                elif cod == "B":
                    cat_vals["investimenti"] += tot
                elif cod == "C":
                    cat_vals["immobili"] += tot
                elif cod == "D":
                    cat_vals["previdenza"] += tot
                elif cod == "E":
                    cat_vals["beni_lusso"] += tot
                elif cod == "F":
                    cat_vals["partecipazioni"] += tot
                else:
                    cat_vals["investimenti"] += tot
            pas = sp.get("passivo", {})
            cat_vals["passivo"] = float(pas.get("totale_passivo", 0.0) or 0.0)
        else:
            cat_vals["liquidita"] = float(net_worth_data.get("liquid_assets", net_worth_data.get("liquidita", 0.0)) or 0.0)
            cat_vals["investimenti"] = float(net_worth_data.get("financial_investments", net_worth_data.get("investimenti", 0.0)) or 0.0)
            cat_vals["immobili"] = float(net_worth_data.get("real_estate", net_worth_data.get("immobili", 0.0)) or 0.0)
            cat_vals["previdenza"] = float(net_worth_data.get("pension_funds", net_worth_data.get("previdenza", 0.0)) or 0.0)
            cat_vals["beni_lusso"] = float(net_worth_data.get("luxury_goods", net_worth_data.get("beni_lusso", 0.0)) or 0.0)
            cat_vals["partecipazioni"] = float(net_worth_data.get("private_equity_other", net_worth_data.get("partecipazioni", 0.0)) or 0.0)
            cat_vals["passivo"] = float(net_worth_data.get("liabilities", net_worth_data.get("passivo", 0.0)) or 0.0)

    tot_assets = sum(v for k, v in cat_vals.items() if k != "passivo")
    tot_liab = cat_vals["passivo"]
    tot_nw = tot_assets - tot_liab
    init_dta = (tot_liab / tot_assets * 100.0) if tot_assets > 0 else 0.0

    # 2. Definizione Scenari Macro Consolidati
    wealth_scenarios = custom_scenarios or {
        "EBA_Adverse_2026": {
            "name": "EBA Regulatory Adverse 2026",
            "description": "Contrazione PIL UE, crash azionario -30%, allargamento spread e calo immobiliare del 15%.",
            "shocks": {
                "liquidita": 0.0,
                "investimenti": -28.0,
                "immobili": -15.0,
                "previdenza": -16.0,
                "beni_lusso": -20.0,
                "partecipazioni": -30.0,
            },
        },
        "Fed_CCAR_Severe": {
            "name": "Fed CCAR Severely Adverse",
            "description": "Crisi sistemica globale: azionario -45%, crollo immobiliare del 25% e compressione beni di lusso.",
            "shocks": {
                "liquidita": 0.0,
                "investimenti": -42.0,
                "immobili": -25.0,
                "previdenza": -24.0,
                "beni_lusso": -35.0,
                "partecipazioni": -45.0,
            },
        },
        "Stagflation_Energy_Spike": {
            "name": "Stagflazione & Shock Tassi",
            "description": "Rialzo tassi banche centrali (+200 bps), inflazione elevata e contrazione multipli immobiliari ed equity.",
            "shocks": {
                "liquidita": 0.0,
                "investimenti": -18.0,
                "immobili": -10.0,
                "previdenza": -14.0,
                "beni_lusso": -10.0,
                "partecipazioni": -20.0,
            },
        },
        "Geopolitical_Risk_Off": {
            "name": "Crisi Geopolitica Globale",
            "description": "Fuga verso la liquidità e beni rifugio: oro e orologi tengono meglio, equity -35%, real estate -8%.",
            "shocks": {
                "liquidita": 0.0,
                "investimenti": -32.0,
                "immobili": -8.0,
                "previdenza": -18.0,
                "beni_lusso": -12.0,
                "partecipazioni": -30.0,
            },
        },
    }

    results_list = []
    for sc_key, sc in wealth_scenarios.items():
        shocks = sc.get("shocks", {})
        post_cat = {}
        delta_cat = {}
        for cat_k, init_v in cat_vals.items():
            if cat_k == "passivo":
                continue
            shk_pct = float(shocks.get(cat_k, -15.0))
            post_v = init_v * (1.0 + shk_pct / 100.0)
            post_cat[cat_k] = post_v
            delta_cat[cat_k] = post_v - init_v

        post_assets = sum(post_cat.values())
        post_liab = tot_liab  # Debiti nominali non diminuiscono
        post_nw = post_assets - post_liab
        delta_nw = post_nw - tot_nw
        nw_dd_pct = (delta_nw / tot_nw * 100.0) if tot_nw > 0 else 0.0
        post_dta = (post_liab / post_assets * 100.0) if post_assets > 0 else 0.0

        results_list.append(
            {
                "scenario_key": sc_key,
                "scenario_name": sc.get("name", sc_key),
                "description": sc.get("description", ""),
                "post_shock_assets_eur": round(post_assets, 2),
                "post_shock_liabilities_eur": round(post_liab, 2),
                "post_shock_net_worth_eur": round(post_nw, 2),
                "net_worth_delta_eur": round(delta_nw, 2),
                "net_worth_drawdown_pct": round(nw_dd_pct, 2),
                "post_shock_debt_to_assets_pct": round(post_dta, 2),
                "breakdown_deltas_eur": {k: round(v, 2) for k, v in delta_cat.items()},
                "breakdown_post_values_eur": {k: round(v, 2) for k, v in post_cat.items()},
            }
        )

    df_res = pd.DataFrame(results_list)
    worst = min(results_list, key=lambda x: x["net_worth_drawdown_pct"]) if results_list else {}

    return {
        "initial_total_assets_eur": round(tot_assets, 2),
        "initial_liabilities_eur": round(tot_liab, 2),
        "initial_net_worth_eur": round(tot_nw, 2),
        "initial_debt_to_assets_pct": round(init_dta, 2),
        "scenarios_results": results_list,
        "scenarios_df": df_res,
        "worst_scenario_name": worst.get("scenario_name", "N/D"),
        "worst_net_worth_loss_eur": worst.get("net_worth_delta_eur", 0.0),
        "worst_net_worth_drawdown_pct": worst.get("net_worth_drawdown_pct", 0.0),
        "worst_post_debt_to_assets_pct": worst.get("post_shock_debt_to_assets_pct", init_dta),
    }

