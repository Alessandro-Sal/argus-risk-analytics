# ============================================================
# core/mip_rebalancer.py
# ARGUS — Mixed-Integer Programming (MIP) Cardinality & Lot-Sizing Rebalancer
# Institutional Execution Engine using SciPy HiGHS MILP Solver
# ============================================================

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, milp


def solve_mip_rebalance(
    current_holdings: Dict[str, float],
    current_prices: Dict[str, float],
    target_weights: Dict[str, float],
    total_capital: Optional[float] = None,
    cash_available: float = 0.0,
    max_cardinality: Optional[int] = None,
    lot_sizes: Optional[Dict[str, int]] = None,
    min_trade_eur: float = 50.0,
    max_turnover_pct: Optional[float] = None,
    capital_gains_tax_budget_eur: Optional[float] = None,
    pmc_dict: Optional[Dict[str, float]] = None,
    tax_rate: float = 0.26,
) -> Dict[str, Any]:
    """
    Risolve il problema di ribilanciamento con vincoli discreti e cardinalità
    tramite Mixed-Integer Linear Programming (MILP):
      - Quote intere (o multipli di lotti minimi L_i)
      - Cardinalità massima (massimo K posizioni non nulle a target)
      - Soglia minima di trade in EUR (elimina polvere / mikro-ordini)
      - Budget fiscale massimo sulle plusvalenze realizzate (CGT budget)
      - Minimizzazione della Tracking Error L1 rispetto ai target weights

    Parametri:
    -----------
    current_holdings : Dict[str, float]
        Dizionario {ticker: quantità_iniziale_quote}
    current_prices : Dict[str, float]
        Dizionario {ticker: prezzo_unitario_eur}
    target_weights : Dict[str, float]
        Dizionario {ticker: peso_target [0.0, 1.0]}
    total_capital : Optional[float]
        Capitale complessivo. Se None, calcolato da valore portafoglio + liquidità.
    cash_available : float
        Liquidità libera spendibile.
    max_cardinality : Optional[int]
        Numero massimo di asset nel portafoglio finale.
    lot_sizes : Optional[Dict[str, int]]
        Lotto minimo negoziabile per asset (es. 1, 10, 100 quote). Default: 1.
    min_trade_eur : float
        Dimensione minima per considerare un ordine eseguibile.
    max_turnover_pct : Optional[float]
        Limite massimo di turnover complessivo (%).
    capital_gains_tax_budget_eur : Optional[float]
        Tetto massimo di tasse sulle plusvalenze realizzabili.
    pmc_dict : Optional[Dict[str, float]]
        Prezzo medio di carico per asset (per calcolo plusvalenze).
    tax_rate : float
        Aliquota capital gains (default 26%).

    Ritorna:
    --------
    Dict[str, Any] contenente gli ordini ottimizzati, le nuove quote intere,
    i pesi effettivi e il report di conformità e tracciamento.
    """
    # Universo di tutti i ticker
    all_tickers = sorted(list(set(list(current_holdings.keys()) + list(target_weights.keys()))))
    n = len(all_tickers)
    if n == 0:
        return {
            "status": "EMPTY",
            "orders": [],
            "initial_shares": {},
            "optimal_shares": {},
            "final_weights": {},
            "tracking_error_l1": 0.0,
            "cardinality": 0,
            "execution_summary": "Nessun asset fornito.",
        }

    # Estrazione vettori
    prices = np.array([float(current_prices.get(t, 100.0)) for t in all_tickers], dtype=float)
    prices = np.maximum(prices, 0.01)  # Evita divisione per zero
    init_shares = np.array([float(current_holdings.get(t, 0.0)) for t in all_tickers], dtype=float)
    tw = np.array([float(target_weights.get(t, 0.0)) for t in all_tickers], dtype=float)

    # Normalizzazione target weights
    if tw.sum() > 0:
        tw = tw / tw.sum()
    else:
        tw = np.array([1.0 / n] * n)

    # Calcolo capitale totale
    current_port_val = float(np.sum(init_shares * prices))
    if total_capital is None or total_capital <= 0:
        total_w = current_port_val + max(0.0, float(cash_available))
    else:
        total_w = float(total_capital)
    total_w = max(total_w, 100.0)

    # Target capital per asset
    target_cap = tw * total_w

    # Lot sizes
    lots = np.array([max(1, int((lot_sizes or {}).get(t, 1))) for t in all_tickers], dtype=float)

    # Variabili decisionali MILP:
    # Per ciascun asset i (1..n):
    # k_i (intero >= 0): numero di lotti detenuti, shares x_i = k_i * lot_i
    # z_i (binario in {0, 1}): indicatore di detenzione (1 se k_i > 0, 0 altrimenti)
    # d_i (continuo >= 0): deviazione assoluta in EUR dal target: |k_i * lot_i * p_i - target_cap_i|
    #
    # Vettore decisionale y di lunghezza 3*n:
    # y = [k_0, ..., k_{n-1}, z_0, ..., z_{n-1}, d_0, ..., d_{n-1}]

    # Costo lineare c da minimizzare:
    # sum(d_i) / total_w  (minimizza Tracking Error L1) + piccola penalità di cardinalità 1e-4 * z_i
    c = np.zeros(3 * n)
    c[2 * n : 3 * n] = 1.0 / total_w
    c[n : 2 * n] = 1e-4

    # Integrality:
    # 0 = continuo, 1 = intero
    integrality = np.zeros(3 * n, dtype=int)
    integrality[0 : n] = 1        # k_i interi
    integrality[n : 2 * n] = 1    # z_i binari
    integrality[2 * n : 3 * n] = 0  # d_i continui

    # Bounds:
    # M_i = massimo numero di lotti acquistabili con total_w
    M = np.ceil(total_w / (prices * lots)).astype(int) + 10
    lb = np.zeros(3 * n)
    ub = np.zeros(3 * n)

    ub[0 : n] = M
    ub[n : 2 * n] = 1.0
    ub[2 * n : 3 * n] = np.inf

    # Matrice dei vincoli lineari A e intervalli [lhs, rhs]
    A_rows = []
    lhs_list = []
    rhs_list = []

    # 1. Vincoli su d_i:
    # d_i >= k_i * lot_i * p_i - target_cap_i  ==>  d_i - k_i * (lot_i * p_i) >= -target_cap_i
    # d_i >= target_cap_i - k_i * lot_i * p_i  ==>  d_i + k_i * (lot_i * p_i) >= target_cap_i
    for i in range(n):
        # d_i - k_i * (lot_i * p_i) >= -target_cap[i]
        row1 = np.zeros(3 * n)
        row1[2 * n + i] = 1.0
        row1[i] = -(lots[i] * prices[i])
        A_rows.append(row1)
        lhs_list.append(-target_cap[i])
        rhs_list.append(np.inf)

        # d_i + k_i * (lot_i * p_i) >= target_cap[i]
        row2 = np.zeros(3 * n)
        row2[2 * n + i] = 1.0
        row2[i] = (lots[i] * prices[i])
        A_rows.append(row2)
        lhs_list.append(target_cap[i])
        rhs_list.append(np.inf)

    # 2. Vincolo di accoppiamento lotto-binario:
    # k_i <= M_i * z_i  ==>  k_i - M_i * z_i <= 0
    for i in range(n):
        row = np.zeros(3 * n)
        row[i] = 1.0
        row[n + i] = -float(M[i])
        A_rows.append(row)
        lhs_list.append(-np.inf)
        rhs_list.append(0.0)

    # 3. Vincolo di Budget complessivo:
    # sum(k_i * lot_i * p_i) <= total_w
    row_budget = np.zeros(3 * n)
    row_budget[0 : n] = lots * prices
    A_rows.append(row_budget)
    lhs_list.append(0.0)
    rhs_list.append(total_w)

    # 4. Vincolo di Cardinalità massima (se richiesto):
    # sum(z_i) <= max_cardinality
    if max_cardinality is not None and 1 <= max_cardinality < n:
        row_card = np.zeros(3 * n)
        row_card[n : 2 * n] = 1.0
        A_rows.append(row_card)
        lhs_list.append(0.0)
        rhs_list.append(float(max_cardinality))

    # 5. Vincolo di Tax Budget (se richiesto e PMC fornito):
    # plusvalenza_i per vendite: max(0, p_i - pmc_i) * (init_shares_i - k_i * lot_i) <= TaxBudget / tax_rate
    if capital_gains_tax_budget_eur is not None and capital_gains_tax_budget_eur >= 0 and pmc_dict is not None:
        cgt_row = np.zeros(3 * n)
        taxable_sum_base = 0.0
        has_tax_constraint = False
        for i, t in enumerate(all_tickers):
            pmc = float(pmc_dict.get(t, prices[i]))
            gain_per_share = max(0.0, prices[i] - pmc)
            if gain_per_share > 0 and init_shares[i] > 0:
                has_tax_constraint = True
                # Per share venduta: (init_shares - k*lot) * gain * tax_rate
                # -k * (lot * gain * tax_rate) <= TaxBudget - init_shares * gain * tax_rate
                cgt_row[i] = -(lots[i] * gain_per_share * tax_rate)
                taxable_sum_base += init_shares[i] * gain_per_share * tax_rate

        if has_tax_constraint:
            A_rows.append(cgt_row)
            lhs_list.append(-np.inf)
            rhs_list.append(float(capital_gains_tax_budget_eur) - taxable_sum_base)

    # Assemblaggio vincoli
    A_mat = np.array(A_rows)
    constraints = LinearConstraint(A_mat, lhs_list, rhs_list)

    # Risoluzione con SciPy HiGHS MILP
    opt_res = milp(c=c, integrality=integrality, bounds=(lb, ub), constraints=constraints)

    if opt_res.success:
        y_opt = opt_res.x
        opt_k = np.round(y_opt[0 : n]).astype(int)
        opt_shares = opt_k * lots.astype(int)
        status = "OPTIMAL"
    else:
        # Fallback euristico se non converge o vincoli troppo stringenti
        opt_shares = np.round(target_cap / (prices * lots)).astype(int) * lots.astype(int)
        # Assicura budget
        while np.sum(opt_shares * prices) > total_w and np.sum(opt_shares) > 0:
            idx_max = np.argmax(opt_shares * prices - target_cap)
            if opt_shares[idx_max] >= lots[idx_max]:
                opt_shares[idx_max] -= int(lots[idx_max])
            else:
                break
        status = "FALLBACK"

    # Generazione ordini e metriche
    orders = []
    total_tax = 0.0
    total_vol = 0.0

    final_val_per_asset = opt_shares * prices
    actual_total_val = float(np.sum(final_val_per_asset))
    cash_leftover = float(total_w - actual_total_val)
    final_weights = {}

    for i, t in enumerate(all_tickers):
        init_s = float(init_shares[i])
        new_s = float(opt_shares[i])
        p = float(prices[i])
        delta_s = new_s - init_s
        trade_val = delta_s * p
        pmc = float((pmc_dict or {}).get(t, p))

        final_w = (new_s * p) / actual_total_val if actual_total_val > 0 else 0.0
        final_weights[t] = round(final_w, 4)

        if abs(trade_val) < min_trade_eur:
            action = "HOLD"
            gain = 0.0
            tax = 0.0
        elif delta_s > 0:
            action = "BUY"
            gain = 0.0
            tax = 0.0
            total_vol += trade_val
        else:
            action = "SELL"
            gain = abs(delta_s) * max(0.0, p - pmc)
            tax = gain * tax_rate
            total_tax += tax
            total_vol += abs(trade_val)

        if action != "HOLD":
            orders.append({
                "ticker": t,
                "action": action,
                "shares": abs(round(delta_s, 2)),
                "price": round(p, 2),
                "order_value": round(abs(trade_val), 2),
                "realized_gain": round(gain, 2),
                "estimated_tax": round(tax, 2),
                "current_weight_pct": round((init_s * p) / total_w * 100.0, 2),
                "target_weight_pct": round(tw[i] * 100.0, 2),
                "final_weight_pct": round(final_w * 100.0, 2),
            })

    # Tracking Error L1: sum(|w_final - w_target|)
    tracking_error = float(np.sum(np.abs(np.array(list(final_weights.values())) - tw)))
    active_cardinality = int(np.sum(opt_shares > 0))

    execution_summary = (
        f"MIP Optimizer status: {status}. Cardinalità finale: {active_cardinality}"
        f"{f' (max {max_cardinality})' if max_cardinality else ''}. "
        f"Tracking Error L1: {tracking_error*100:.2f}%. Volume scambiato: €{total_vol:,.2f}. "
        f"Imposta plusvalenze: €{total_tax:,.2f}. Liquidità residua: €{cash_leftover:,.2f}."
    )

    return {
        "status": status,
        "initial_shares": {t: float(init_shares[i]) for i, t in enumerate(all_tickers)},
        "optimal_shares": {t: int(opt_shares[i]) for i, t in enumerate(all_tickers)},
        "orders": orders,
        "final_weights": final_weights,
        "target_weights": {t: round(tw[i], 4) for i, t in enumerate(all_tickers)},
        "tracking_error_l1": round(tracking_error, 4),
        "cardinality": active_cardinality,
        "max_cardinality": max_cardinality or n,
        "total_trade_volume_eur": round(total_vol, 2),
        "total_tax_incurred_eur": round(total_tax, 2),
        "cash_leftover_eur": round(cash_leftover, 2),
        "execution_summary": execution_summary,
    }
