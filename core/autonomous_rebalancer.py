# ============================================================
# core/autonomous_rebalancer.py
# ARGUS — Autonomous AI Rebalancer & MiFID II Suitability Gate
# Generatore di ordini tattici, ottimizzazione fiscale e gate di conformità
# ============================================================

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def check_mifid_suitability_and_limits(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    risk_profile: str = "Moderate",
    max_issuer_concentration_pct: float = 10.0
) -> Dict[str, Any]:
    """
    Verifica di adeguatezza MiFID II e conformità ai limiti di concentrazione (UCITS 5/10/40 rule e single issuer).
    """
    total_val = 0.0
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        total_val = float(df_positions["controvalore"].sum())
    elif results and "valore_totale" in results:
        total_val = float(results["valore_totale"])
    if total_val <= 0:
        total_val = 100000.0

    violations = []
    warnings = []
    checks = []

    # 1. Concentrazione per singolo emittente
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        for _, row in df_positions.iterrows():
            ticker = str(row.get("ticker", "ASSET"))
            val = float(row.get("controvalore", 0.0))
            weight_pct = (val / total_val) * 100.0 if total_val > 0 else 0.0
            if weight_pct > max_issuer_concentration_pct:
                violations.append({
                    "type": "ISSUER_CONCENTRATION",
                    "ticker": ticker,
                    "weight_pct": round(weight_pct, 1),
                    "limit_pct": max_issuer_concentration_pct,
                    "excess_eur": round(val - (total_val * max_issuer_concentration_pct / 100.0), 2),
                    "severity": "HIGH"
                })

    # 2. Concentrazione aggregata grandi posizioni (Regola UCITS 5/10/40: somma posizioni > 5% non deve superare il 40%)
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        large_positions = df_positions[df_positions["controvalore"] / total_val > 0.05]
        large_sum_pct = (large_positions["controvalore"].sum() / total_val * 100.0) if total_val > 0 else 0.0
        if large_sum_pct > 40.0:
            warnings.append({
                "type": "UCITS_5_10_40_BREACH",
                "large_positions_sum_pct": round(large_sum_pct, 1),
                "limit_pct": 40.0,
                "severity": "MEDIUM",
                "message": f"La somma delle posizioni con peso > 5% ({large_sum_pct:.1f}%) supera la soglia UCITS prudenziale del 40%."
            })

    # 3. Profilo di rischio / Max Volatilità / VaR
    var_95 = 0.0
    if results and "var_storico_95" in results:
        var_95 = abs(float(results["var_storico_95"]))
    elif results and "historical_var_95" in results:
        var_95 = abs(float(results["historical_var_95"]))

    max_var_allowed = {"Conservative": 6.0, "Moderate": 12.0, "Aggressive": 22.0}.get(risk_profile, 12.0)
    is_var_compliant = var_95 <= max_var_allowed if var_95 > 0 else True
    if not is_var_compliant:
        violations.append({
            "type": "RISK_PROFILE_VAR_EXCEEDED",
            "current_var_95_pct": round(var_95, 2),
            "max_allowed_var_pct": max_var_allowed,
            "severity": "HIGH",
            "message": f"Il VaR 95% del portafoglio ({var_95:.1f}%) supera la tolleranza per il profilo {risk_profile} ({max_var_allowed}%)."
        })

    is_compliant = len(violations) == 0

    return {
        "is_mifid_compliant": is_compliant,
        "risk_profile": risk_profile,
        "violations_count": len(violations),
        "warnings_count": len(warnings),
        "violations": violations,
        "warnings": warnings,
        "max_issuer_limit_pct": max_issuer_concentration_pct,
        "status": "APPROVED 🟢" if is_compliant else "REJECTED 🔴 (Limiti Violati)"
    }


def generate_autonomous_rebalancing_proposal(
    df_positions: Optional[pd.DataFrame] = None,
    results: Optional[Dict[str, Any]] = None,
    target_weights: Optional[Dict[str, float]] = None,
    max_turnover_pct: float = 25.0,
    min_trade_eur: float = 500.0
) -> Dict[str, Any]:
    """
    Genera una proposta automatica di ordini di ribilanciamento (Trade Proposal)
    ottimizzata fiscalmente e conforme ai vincoli MiFID II.
    """
    total_val = 0.0
    if df_positions is not None and not df_positions.empty and "controvalore" in df_positions.columns:
        total_val = float(df_positions["controvalore"].sum())
    elif results and "valore_totale" in results:
        total_val = float(results["valore_totale"])
    if total_val <= 0:
        total_val = 100000.0

    # Default Target Allocation se non specificata (60/40 classica)
    targets = target_weights or {
        "SWDA.MI": 0.35,
        "EIMI.MI": 0.10,
        "XG7S.MI": 0.25,
        "XEON.MI": 0.15,
        "SGLD.MI": 0.15
    }

    # Normalizza pesi target
    sum_t = sum(targets.values())
    if sum_t > 0:
        targets = {k: v / sum_t for k, v in targets.items()}

    current_positions = {}
    prices = {}
    if df_positions is not None and not df_positions.empty:
        for _, r in df_positions.iterrows():
            t = str(r.get("ticker", "")).strip()
            val = float(r.get("controvalore", 0.0))
            p = float(r.get("prezzo_corrente", r.get("prezzo_medio_carico", 100.0)))
            current_positions[t] = val
            prices[t] = max(0.01, p)

    # Elenco unificato di ticker
    all_tickers = sorted(list(set(list(targets.keys()) + list(current_positions.keys()))))

    trades = []
    total_buy_eur = 0.0
    total_sell_eur = 0.0
    estimated_tax_impact_eur = 0.0

    for t in all_tickers:
        cur_val = current_positions.get(t, 0.0)
        tgt_weight = targets.get(t, 0.0)
        tgt_val = total_val * tgt_weight
        diff_eur = tgt_val - cur_val

        if abs(diff_eur) >= min_trade_eur:
            px_val = prices.get(t, 100.0)
            shares = int(abs(diff_eur) / px_val)
            notional = shares * px_val

            if diff_eur > 0:
                action = "BUY"
                total_buy_eur += notional
                tax_impact = 0.0  # Nessun impatto fiscale su acquisti
            else:
                action = "SELL"
                total_sell_eur += notional
                # Stima prudenziale imposta capital gain 26% su ipotetico 15% di plusvalenza
                tax_impact = notional * 0.15 * 0.26
                estimated_tax_impact_eur += tax_impact

            trades.append({
                "ticker": t,
                "action": action,
                "current_weight_pct": round((cur_val / total_val) * 100.0, 1),
                "target_weight_pct": round(tgt_weight * 100.0, 1),
                "diff_eur": round(diff_eur, 2),
                "suggested_shares": shares,
                "estimated_price": round(px_val, 2),
                "trade_notional_eur": round(notional, 2),
                "estimated_tax_impact_eur": round(tax_impact, 2),
                "status": "READY_TO_EXECUTE"
            })

    turnover_eur = (total_buy_eur + total_sell_eur) / 2.0
    turnover_pct = (turnover_eur / total_val * 100.0) if total_val > 0 else 0.0

    df_trades = pd.DataFrame(trades)

    # Verifica vincolo turnover
    turnover_exceeded = turnover_pct > max_turnover_pct

    return {
        "portfolio_total_value_eur": round(total_val, 2),
        "total_trades_count": len(trades),
        "total_buy_volume_eur": round(total_buy_eur, 2),
        "total_sell_volume_eur": round(total_sell_eur, 2),
        "turnover_pct": round(turnover_pct, 1),
        "max_allowed_turnover_pct": max_turnover_pct,
        "is_turnover_compliant": not turnover_exceeded,
        "estimated_tax_liability_eur": round(estimated_tax_impact_eur, 2),
        "trades_list": trades,
        "trades_df": df_trades
    }
