import pandas as pd
import numpy as np


def _safe_series_get(row, keys, default=0.0):
    if hasattr(row, "index"):
        for k in keys:
            if k in row.index:
                val = row[k]
                if pd.notna(val):
                    try:
                        return float(val)
                    except Exception:
                        pass
    elif isinstance(row, dict):
        for k in keys:
            if k in row and pd.notna(row[k]):
                try:
                    return float(row[k])
                except Exception:
                    pass
    return default


def compute_rebalancing_orders(
    results: dict,
    target_mode: str = "max_sharpe",
    strategy: str = None,
    custom_target_weights: dict = None,
    target_weights_dict: dict = None,
    new_cash_eur: float = 0.0,
    target_total_value: float = None,
    integer_shares: bool = True
) -> dict:
    """
    Calcola gli ordini puntuali di acquisto / vendita (Rebalancing Plan)
    per allineare il portafoglio attuale a un'allocazione obiettivo.
    """
    if results is None:
        return {"orders": pd.DataFrame(), "summary": {}}

    pos_df = results.get("positions", pd.DataFrame())
    if pos_df.empty:
        return {"orders": pd.DataFrame(), "summary": {}}

    active_pos = pos_df[pos_df["qty_net"] > 0].copy() if "qty_net" in pos_df.columns else pos_df.copy()
    if active_pos.empty:
        return {"orders": pd.DataFrame(), "summary": {}}

    mode = strategy or target_mode
    custom_w = target_weights_dict or custom_target_weights

    curr_total_val = float(active_pos["current_value"].sum()) if "current_value" in active_pos.columns else 100000.0
    if target_total_value is not None and target_total_value > 0:
        tot_target_val = target_total_value
    else:
        tot_target_val = curr_total_val + float(new_cash_eur or 0.0)

    if tot_target_val <= 0:
        tot_target_val = curr_total_val

    # 1. Determinazione Pesi Target
    opt = results.get("optimization", {})
    target_weights = {}

    if custom_w is not None:
        target_weights = custom_w.copy()
    elif opt and opt.get("tickers"):
        opt_tickers = opt.get("tickers", [])
        if mode == "max_sharpe":
            opt_w = opt.get("max_sharpe", {}).get("weights", [])
        elif mode == "min_vol":
            opt_w = opt.get("min_vol", {}).get("weights", [])
        elif mode == "equal_weight":
            opt_w = [1.0 / len(opt_tickers)] * len(opt_tickers)
        else:
            opt_w = []

        if len(opt_w) == len(opt_tickers):
            for tk, w in zip(opt_tickers, opt_w):
                target_weights[tk] = float(w) * 100.0
    else:
        # Fallback al peso attuale
        for _, row in active_pos.iterrows():
            target_weights[row["ticker"]] = _safe_series_get(row, ["weight_pct", "weight"], default=0.0)

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
        price = _safe_series_get(row, ["last_price", "current_price", "price"], default=100.0)
        curr_qty = _safe_series_get(row, ["qty_net", "quantity", "qty"], default=0.0)
        curr_val = _safe_series_get(row, ["current_value", "value"], default=0.0)
        curr_w = _safe_series_get(row, ["weight_pct", "weight"], default=0.0)

        tgt_w = target_weights.get(t, curr_w)
        tgt_val = (tgt_w / 100.0) * tot_target_val

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

        orders_list.append({
            "ticker": t,
            "action": action,
            "current_qty": round(curr_qty, 2) if not integer_shares else int(round(curr_qty)),
            "target_qty": round(tgt_qty, 2) if not integer_shares else int(tgt_qty),
            "qty_delta": round(qty_delta, 2) if not integer_shares else int(round(qty_delta)),
            "last_price": round(price, 2),
            "order_value_eur": round(abs(order_val), 2),
            "current_weight_pct": round(curr_w, 2),
            "target_weight_pct": round(tgt_w, 2),
            "weight_delta_pct": round(tgt_w - curr_w, 2),
            "Ticker": t,
            "Azione": action,
            "Quote Attuali": round(curr_qty, 2) if not integer_shares else int(round(curr_qty)),
            "Quote Target": round(tgt_qty, 2) if not integer_shares else int(tgt_qty),
            "Delta Quote": round(qty_delta, 2) if not integer_shares else int(round(qty_delta)),
            "Prezzo (€/$)": round(price, 2),
            "Valore Ordine (€/$)": round(abs(order_val), 2),
            "Peso Attuale %": round(curr_w, 2),
            "Peso Target %": round(tgt_w, 2),
            "Delta Peso %": round(tgt_w - curr_w, 2)
        })

    df_orders = pd.DataFrame(orders_list)
    net_flow = total_raised - total_spent

    summary = {
        "total_current_value": curr_total_val,
        "target_total_value": tot_target_val,
        "target_total_value_eur": tot_target_val,
        "total_spent": total_spent,
        "total_buy_eur": total_spent,
        "total_buy_value": total_spent,
        "total_raised": total_raised,
        "total_sell_eur": total_raised,
        "total_sell_value": total_raised,
        "net_cash_flow": net_flow,
        "net_cash_delta": net_flow,
        "num_orders": len([o for o in orders_list if "HOLD" not in o["action"]])
    }

    return {"orders": df_orders, "summary": summary}
