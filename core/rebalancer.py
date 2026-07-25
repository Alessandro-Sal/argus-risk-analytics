import pandas as pd
import numpy as np

def compute_rebalancing_orders(
    results: dict,
    target_mode: str = "max_sharpe",
    custom_target_weights: dict = None,
    new_cash_eur: float = 0.0,
    integer_shares: bool = True
) -> dict:
    """
    Simulatore di Ribilanciamento & Generatore di Ordini.
    
    Parameters
    ----------
    results : dict
        Dizionario di output da compute_risk()
    target_mode : str
        'max_sharpe', 'min_vol', 'equal_weight', 'custom'
    custom_target_weights : dict
        Dizionario {ticker: peso_pct} per target_mode='custom'
    new_cash_eur : float
        Capitale aggiuntivo da depositare (+) o ritirare (-)
    integer_shares : bool
        Se True, arrotonda gli ordini ad azioni intere
        
    Returns
    -------
    dict con 'orders' (DataFrame) e 'summary' (dict)
    """
    pos = results.get("positions", pd.DataFrame()).copy()
    if pos.empty:
        return {"orders": pd.DataFrame(), "summary": {}}

    active_pos = pos[pos["qty_net"] > 0].copy()
    tickers = list(active_pos["ticker"])
    n_assets = len(tickers)

    curr_total_value = float(active_pos["current_value"].sum())
    target_total_value = curr_total_value + float(new_cash_eur)
    
    if target_total_value <= 0:
        target_total_value = curr_total_value

    # 1. Determinazione Pesi Target (%)
    target_weights = {}
    opt = results.get("optimization")

    if target_mode == "max_sharpe" and opt and opt.get("tickers"):
        opt_tickers = opt["tickers"]
        opt_w = opt["max_sharpe"]["weights"]
        for t, w in zip(opt_tickers, opt_w):
            target_weights[t] = w * 100
    elif target_mode == "min_vol" and opt and opt.get("tickers"):
        opt_tickers = opt["tickers"]
        opt_w = opt["min_vol"]["weights"]
        for t, w in zip(opt_tickers, opt_w):
            target_weights[t] = w * 100
    elif target_mode == "equal_weight":
        eq_w = 100.0 / n_assets
        for t in tickers:
            target_weights[t] = eq_w
    elif target_mode == "custom" and custom_target_weights:
        target_weights = custom_target_weights
    else:
        # Fallback al peso attuale
        for _, row in active_pos.iterrows():
            target_weights[row["ticker"]] = float(row["weight_pct"])

    # Normalizza pesi target affinché la somma sia 100%
    total_w_sum = sum(target_weights.values())
    if total_w_sum > 0 and abs(total_w_sum - 100.0) > 0.01:
        target_weights = {t: (w / total_w_sum) * 100 for t, w in target_weights.items()}

    # 2. Calcolo Ordini
    orders_list = []
    total_spent = 0.0
    total_raised = 0.0

    for _, row in active_pos.iterrows():
        t = row["ticker"]
        price = float(row["last_price"])
        curr_qty = float(row["qty_net"])
        curr_val = float(row["current_value"])
        curr_w = float(row["weight_pct"])

        tgt_w = target_weights.get(t, curr_w)
        tgt_val = (tgt_w / 100.0) * target_total_value

        if price > 0:
            raw_tgt_qty = tgt_val / price
            if integer_shares:
                tgt_qty = max(0, round(raw_tgt_qty))
            else:
                tgt_qty = max(0.0, raw_tgt_qty)
        else:
            tgt_qty = curr_qty

        qty_delta = tgt_qty - curr_qty
        order_val = qty_delta * price

        if qty_delta > 0.0001:
            action = "BUY 🟢"
            total_spent += abs(order_val)
        elif qty_delta < -0.0001:
            action = "SELL 🔴"
            total_raised += abs(order_val)
        else:
            action = "HOLD ⚪"

        new_val = tgt_qty * price
        
        orders_list.append({
            "ticker": t,
            "asset_class": row.get("asset_class", "Stock"),
            "action": action,
            "current_qty": curr_qty,
            "target_qty": tgt_qty,
            "qty_delta": qty_delta,
            "last_price": price,
            "order_value_eur": order_val,
            "current_weight_pct": curr_w,
            "target_weight_pct": tgt_w,
            "new_value_eur": new_val
        })

    df_orders = pd.DataFrame(orders_list)
    
    # Recalculate new total & final weights
    final_total_val = float(df_orders["new_value_eur"].sum()) if not df_orders.empty else target_total_value
    if final_total_val > 0:
        df_orders["new_weight_pct"] = (df_orders["new_value_eur"] / final_total_val * 100).round(2)
    else:
        df_orders["new_weight_pct"] = 0.0

    cash_remaining = (curr_total_value + new_cash_eur + total_raised) - (curr_total_value + total_spent)

    summary = {
        "current_total_value": curr_total_value,
        "new_cash_input": new_cash_eur,
        "target_total_value": target_total_value,
        "final_total_value": final_total_val,
        "total_buy_value": total_spent,
        "total_sell_value": total_raised,
        "net_cash_delta": total_spent - total_raised,
        "cash_remaining_buffer": max(0.0, cash_remaining),
        "target_mode": target_mode
    }

    return {
        "orders": df_orders,
        "summary": summary
    }
