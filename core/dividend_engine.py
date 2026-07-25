import pandas as pd
import numpy as np

def compute_dividend_forecast(positions: pd.DataFrame) -> dict:
    """
    Calcola la proiezione dei flussi di cassa da dividendi per il portafoglio.
    Supporta sia i dividendi storici incassati sia i dividendi stimati a 12 mesi.
    
    Parameters
    ----------
    positions : pd.DataFrame
        DataFrame delle posizioni correnti da compute_risk()
        
    Returns
    -------
    dict con 'total_annual_dividends_eur', 'historical_dividends_total_eur', 'portfolio_yield_pct', 'monthly_forecast', 'dividend_breakdown'
    """
    empty_breakdown = pd.DataFrame(columns=[
        "ticker", "asset_class", "qty_net", "current_value_eur", 
        "dividend_yield_pct", "annual_payout_eur", "historical_payout_eur", "weight_pct"
    ])

    if positions.empty:
        return {
            "total_annual_dividends_eur": 0.0,
            "historical_dividends_total_eur": 0.0,
            "portfolio_yield_pct": 0.0,
            "monthly_forecast": pd.DataFrame(),
            "dividend_breakdown": empty_breakdown
        }

    pos = positions[positions["qty_net"] > 0].copy() if "qty_net" in positions.columns else positions.copy()
    total_port_val = float(pos["current_value"].sum()) if "current_value" in pos.columns else 0.0
    hist_div_total = float(pos["dividends_total"].sum()) if "dividends_total" in pos.columns else 0.0

    if total_port_val <= 0 or pos.empty:
        return {
            "total_annual_dividends_eur": 0.0,
            "historical_dividends_total_eur": round(hist_div_total, 2),
            "portfolio_yield_pct": 0.0,
            "monthly_forecast": pd.DataFrame(),
            "dividend_breakdown": empty_breakdown
        }

    breakdown_list = []
    total_annual_div = 0.0

    for _, row in pos.iterrows():
        t = row["ticker"]
        cval = float(row.get("current_value", 0))
        qty = float(row.get("qty_net", 0))
        hist_div = float(row.get("dividends_total", 0)) if "dividends_total" in row and not pd.isna(row.get("dividends_total")) else 0.0
        
        dy_raw = row.get("dividend_yield")
        
        # dy_raw is stored in DB assets table as percentage (e.g. 0.26 = 0.26%, 6.05 = 6.05%, 0.90 = 0.90%)
        if dy_raw is not None and not pd.isna(dy_raw) and float(dy_raw) > 0:
            val_f = float(dy_raw)
            dy_display = val_f
            dy_pct = val_f / 100.0
        else:
            dy_pct = 0.0
            dy_display = 0.0

        annual_div_eur = cval * dy_pct
        total_annual_div += annual_div_eur

        breakdown_list.append({
            "ticker": t,
            "asset_class": row.get("asset_class", "Stock"),
            "qty_net": qty,
            "current_value_eur": cval,
            "dividend_yield_pct": round(dy_display, 2),
            "annual_payout_eur": round(annual_div_eur, 2),
            "historical_payout_eur": round(hist_div, 2),
            "weight_pct": float(row.get("weight_pct", 0))
        })

    df_breakdown = pd.DataFrame(breakdown_list)
    portfolio_yield_pct = (total_annual_div / total_port_val * 100.0) if total_port_val > 0 else 0.0

    # ── Generazione distribuzione mensile (Stagionalità Dividendi per Azienda) ───
    TICKER_PAYOUT_MONTHS = {
        "ISP.MI": [5, 11],
        "NOVO-B.CO": [3, 8],
        "MSFT": [3, 6, 9, 12],
        "META": [3, 6, 9, 12],
        "AAPL": [2, 5, 8, 11],
        "KO": [4, 7, 10, 12],
        "T": [2, 5, 8, 11],
        "C": [2, 5, 8, 11],
        "QCOM": [3, 6, 9, 12],
        "BABA": [6, 12],
        "GOOGL": [6, 12],
        "PYPL": [6, 12],
        "PRX.AS": [12],
    }

    month_names = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    month_payouts = {m: 0.0 for m in range(1, 13)}
    month_companies = {m: [] for m in range(1, 13)}

    for b in breakdown_list:
        t = b["ticker"]
        payout = b["annual_payout_eur"]
        if payout <= 0:
            continue
        months = TICKER_PAYOUT_MONTHS.get(t, [3, 6, 9, 12])
        pm_amount = payout / len(months)
        for m in months:
            month_payouts[m] += pm_amount
            month_companies[m].append(f"{t} (€ {pm_amount:.2f})")

    monthly_rows = []
    for m in range(1, 13):
        m_name = month_names[m - 1]
        tot = month_payouts[m]
        comps = ", ".join(month_companies[m]) if month_companies[m] else "-"
        w_ratio = (tot / total_annual_div) if total_annual_div > 0 else 0.0
        monthly_rows.append({
            "month_num": m,
            "month_name": m_name,
            "projected_payout_eur": round(tot, 2),
            "pct_of_annual": round(w_ratio * 100, 1),
            "paying_companies": comps
        })

    df_monthly = pd.DataFrame(monthly_rows)

    return {
        "total_annual_dividends_eur": round(total_annual_div, 2),
        "historical_dividends_total_eur": round(hist_div_total, 2),
        "portfolio_yield_pct": round(portfolio_yield_pct, 2),
        "monthly_forecast": df_monthly,
        "dividend_breakdown": df_breakdown.sort_values(by="annual_payout_eur", ascending=False)
    }
