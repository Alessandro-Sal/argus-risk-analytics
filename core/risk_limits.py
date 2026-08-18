"""
ARGUS — Risk Analytics Platform
Core Module: Risk Limits & Early Warning Engine
"""

import pandas as pd
from typing import Dict, Any, List

DEFAULT_RISK_LIMITS = {
    "max_single_asset_pct": {"label": "Peso Max Singola Posizione", "limit": 20.0, "unit": "%", "comparator": "le"},
    "max_sector_pct": {"label": "Concentrazione Max Settoriale", "limit": 35.0, "unit": "%", "comparator": "le"},
    "max_var_95_pct": {"label": "Value at Risk Max (VaR 95%)", "limit": 3.00, "unit": "%", "comparator": "le"},
    "max_beta": {"label": "Beta Sistemico Massimo", "limit": 1.25, "unit": "x", "comparator": "le"},
    "min_diversification_ratio": {"label": "Diversification Ratio Minimo", "limit": 1.20, "unit": "x", "comparator": "ge"},
    "max_hhi": {"label": "Indice Concentrazione HHI Max", "limit": 0.2500, "unit": "", "comparator": "le"},
}

def check_risk_limits(
    results: Dict[str, Any],
    custom_limits: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Evaluates institutional risk limits against active portfolio metrics.
    Returns status per rule (PASS, WARNING, BREACH) and total compliance ratio.
    """
    limits_config = DEFAULT_RISK_LIMITS.copy()
    if custom_limits:
        for k, v in custom_limits.items():
            if k in limits_config:
                limits_config[k]["limit"] = float(v)

    pos = results.get("positions", pd.DataFrame())
    active_pos = pos[pos["qty_net"] > 0] if "qty_net" in pos.columns else pos
    tot_val = active_pos["current_value"].sum() if "current_value" in active_pos.columns else 0.0

    # Metric extractions
    max_asset_w = (active_pos["current_value"].max() / tot_val * 100.0) if tot_val > 0 else 0.0
    
    if "sector" in active_pos.columns and tot_val > 0:
        max_sector_w = (active_pos.groupby("sector")["current_value"].sum().max() / tot_val * 100.0)
    else:
        max_sector_w = max_asset_w

    var_95 = float(results.get("var_95_hist", 0.02) or 0.02) * 100.0
    beta = float(results.get("portfolio_beta", 1.0) or 1.0)
    dr = float(results.get("diversification_ratio", 1.3) or 1.3)
    hhi = float(results.get("hhi", 0.10) or 0.10)

    metric_values = {
        "max_single_asset_pct": max_asset_w,
        "max_sector_pct": max_sector_w,
        "max_var_95_pct": var_95,
        "max_beta": beta,
        "min_diversification_ratio": dr,
        "max_hhi": hhi
    }

    evaluations = []
    pass_count, warn_count, breach_count = 0, 0, 0

    for key, cfg in limits_config.items():
        curr_val = metric_values.get(key, 0.0)
        lim_val = cfg["limit"]
        comp = cfg["comparator"]

        if comp == "le":
            if curr_val <= lim_val:
                if curr_val >= lim_val * 0.85:
                    status = "WARNING"
                    status_icon = "🟡 WARNING"
                    warn_count += 1
                else:
                    status = "PASS"
                    status_icon = "🟢 PASS"
                    pass_count += 1
            else:
                status = "BREACH"
                status_icon = "🔴 BREACH"
                breach_count += 1
        else: # "ge"
            if curr_val >= lim_val:
                if curr_val <= lim_val * 1.15:
                    status = "WARNING"
                    status_icon = "🟡 WARNING"
                    warn_count += 1
                else:
                    status = "PASS"
                    status_icon = "🟢 PASS"
                    pass_count += 1
            else:
                status = "BREACH"
                status_icon = "🔴 BREACH"
                breach_count += 1

        evaluations.append({
            "key": key,
            "rule_name": cfg["label"],
            "status": status,
            "status_icon": status_icon,
            "current_value": round(curr_val, 2),
            "limit_threshold": round(lim_val, 2),
            "unit": cfg["unit"],
            "margin_delta": round(curr_val - lim_val, 2)
        })

    total_rules = len(evaluations)
    compliance_pct = round((pass_count + warn_count * 0.5) / total_rules * 100.0, 1)

    return {
        "compliance_pct": compliance_pct,
        "pass_count": pass_count,
        "warning_count": warn_count,
        "breach_count": breach_count,
        "total_rules": total_rules,
        "evaluations": pd.DataFrame(evaluations)
    }
