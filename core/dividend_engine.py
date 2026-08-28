import pandas as pd
import numpy as np

def compute_dividend_forecast(positions: pd.DataFrame) -> dict:
    """
    Calcola la proiezione dettagliata dei flussi di cassa da dividendi per il portafoglio.
    Supporta sia i dividendi storici incassati sia i dividendi stimati a 12 mesi,
    con dettaglio puntuale di chi paga, quando e quanto per ogni singolo mese.
    
    Parameters
    ----------
    positions : pd.DataFrame
        DataFrame delle posizioni correnti da compute_risk()
        
    Returns
    -------
    dict con totali, medie, calendario mensile, breakdown per società e matrice annuale.
    """
    empty_breakdown = pd.DataFrame(columns=[
        "ticker", "asset_class", "qty_net", "current_value_eur", 
        "dividend_yield_pct", "yield_on_cost_pct", "frequency", 
        "payout_months_str", "installment_payout_eur", "annual_payout_eur", 
        "historical_payout_eur", "weight_pct"
    ])

    if positions.empty:
        return {
            "total_annual_dividends_eur": 0.0,
            "historical_dividends_total_eur": 0.0,
            "portfolio_yield_pct": 0.0,
            "monthly_average_eur": 0.0,
            "monthly_forecast": pd.DataFrame(),
            "dividend_breakdown": empty_breakdown,
            "calendar_events": pd.DataFrame(),
            "monthly_matrix": pd.DataFrame()
        }

    pos = positions[positions["qty_net"] > 0].copy() if "qty_net" in positions.columns else positions.copy()
    total_port_val = float(pos["current_value"].sum()) if "current_value" in pos.columns else 0.0
    hist_div_total = float(positions["dividends_total"].sum()) if "dividends_total" in positions.columns else 0.0

    if total_port_val <= 0 or pos.empty:
        return {
            "total_annual_dividends_eur": 0.0,
            "historical_dividends_total_eur": round(hist_div_total, 2),
            "portfolio_yield_pct": 0.0,
            "monthly_average_eur": 0.0,
            "monthly_forecast": pd.DataFrame(),
            "dividend_breakdown": empty_breakdown,
            "calendar_events": pd.DataFrame(),
            "monthly_matrix": pd.DataFrame()
        }

    MONTH_LABELS = {1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu", 7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"}
    MONTH_FULL_NAMES = {1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile", 5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto", 9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"}
    
    # Stagionalità tipica dei dividendi per i principali asset
    TICKER_PAYOUT_MONTHS = {
        "ISP.MI": [5, 11],
        "NOVO-B.CO": [3, 8],
        "BMW.DE": [5],
        "ASML.AS": [2, 5, 8, 11],
        "MSFT": [3, 6, 9, 12],
        "META": [3, 6, 9, 12],
        "AAPL": [2, 5, 8, 11],
        "KO": [4, 7, 10, 12],
        "PEP": [1, 3, 6, 9],
        "JNJ": [3, 6, 9, 12],
        "PG": [2, 5, 8, 11],
        "IBM": [3, 6, 9, 12],
        "WMT": [1, 4, 6, 9],
        "T": [2, 5, 8, 11],
        "C": [2, 5, 8, 11],
        "QCOM": [3, 6, 9, 12],
        "BABA": [6, 12],
        "GOOGL": [6, 12],
        "PYPL": [6, 12],
        "PRX.AS": [12],
        "VWRL.L": [3, 6, 9, 12],
        "BND": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "SPY": [3, 6, 9, 12],
        "QQQ": [3, 6, 9, 12],
    }

    KNOWN_DIVIDEND_YIELDS = {
        "ISP.MI": 5.58,
        "NOVO-B.CO": 3.95,
        "BMW.DE": 7.20,
        "BMW": 7.20,
        "ASML.AS": 1.20,
        "MSFT": 0.76,
        "META": 0.38,
        "AAPL": 0.50,
        "KO": 3.10,
        "PEP": 3.00,
        "JNJ": 3.20,
        "PG": 2.40,
        "IBM": 3.30,
        "WMT": 1.40,
        "T": 6.20,
        "C": 3.60,
        "QCOM": 2.10,
        "BABA": 1.80,
        "GOOGL": 0.45,
        "PYPL": 0.90,
        "PRX.AS": 0.74,
        "VWRL.L": 1.85,
        "BND": 3.40,
        "SPY": 1.25,
        "QQQ": 0.60,
        "NDIA.L": 0.80,
        "DFNS.PA": 1.10,
        "DFND.PA": 1.10,
        "INTC": 1.50,
    }

    breakdown_list = []
    total_annual_div = 0.0
    calendar_events_list = []

    for _, row in pos.iterrows():
        t = str(row.get("ticker", "")).strip().upper()
        cval = float(row.get("current_value", row.get("market_value", 0.0)))
        qty = float(row.get("qty_net", row.get("shares", row.get("quantity", 0.0))))
        hist_div = float(row.get("dividends_total", 0.0)) if "dividends_total" in row and not pd.isna(row.get("dividends_total")) else 0.0
        
        # Calcolo Invested Capital per Yield on Cost
        avg_price = float(row.get("avg_cost", row.get("avg_price", 0.0)))
        invested_cap = (qty * avg_price) if (qty > 0 and avg_price > 0) else cval
        
        dy_raw = row.get("dividend_yield")
        if (dy_raw is None or pd.isna(dy_raw) or float(dy_raw) <= 0) and t in KNOWN_DIVIDEND_YIELDS:
            dy_raw = KNOWN_DIVIDEND_YIELDS[t]

        if dy_raw is not None and not pd.isna(dy_raw) and float(dy_raw) > 0:
            val_f = float(dy_raw)
            if val_f <= 0.20:
                dy_pct = val_f
                dy_display = val_f * 100.0
            else:
                dy_pct = val_f / 100.0
                dy_display = val_f
        else:
            dy_pct = 0.0
            dy_display = 0.0

        annual_div_eur = cval * dy_pct
        total_annual_div += annual_div_eur

        yoc_pct = (annual_div_eur / invested_cap * 100.0) if invested_cap > 0 else dy_display

        # Mesi di stacco
        if dy_pct > 0 or annual_div_eur > 0:
            months = TICKER_PAYOUT_MONTHS.get(t, [3, 6, 9, 12])
        else:
            months = []

        if len(months) == 12:
            freq_label = "Mensile (12x)"
        elif len(months) == 4:
            freq_label = "Trimestrale (4x)"
        elif len(months) == 2:
            freq_label = "Semestrale (2x)"
        elif len(months) == 1:
            freq_label = "Annuale (1x)"
        else:
            freq_label = "Nessuno (0x)"

        months_str = ", ".join([MONTH_LABELS[m] for m in months]) if months else "Nessuno stacco previsto"
        installment_eur = (annual_div_eur / len(months)) if months else 0.0

        breakdown_list.append({
            "ticker": t,
            "asset_class": row.get("asset_class", "Stock"),
            "qty_net": qty,
            "current_value_eur": cval,
            "dividend_yield_pct": round(dy_display, 2),
            "yield_on_cost_pct": round(yoc_pct, 2),
            "frequency": freq_label,
            "payout_months_str": months_str,
            "installment_payout_eur": round(installment_eur, 2),
            "annual_payout_eur": round(annual_div_eur, 2),
            "historical_payout_eur": round(hist_div, 2),
            "weight_pct": float(row.get("weight_pct", 0))
        })

        if annual_div_eur > 0:
            for m in months:
                calendar_events_list.append({
                    "month_num": m,
                    "month_name": MONTH_LABELS[m],
                    "month_full": MONTH_FULL_NAMES[m],
                    "ticker": t,
                    "qty_net": qty,
                    "dividend_yield_pct": round(dy_display, 2),
                    "installment_payout_eur": round(installment_eur, 2),
                    "annual_payout_eur": round(annual_div_eur, 2)
                })

    df_breakdown = pd.DataFrame(breakdown_list)
    df_events = pd.DataFrame(calendar_events_list, columns=[
        "month_num", "month_name", "month_full", "ticker", "qty_net", 
        "dividend_yield_pct", "installment_payout_eur", "annual_payout_eur"
    ])
    portfolio_yield_pct = (total_annual_div / total_port_val * 100.0) if total_port_val > 0 else 0.0
    monthly_avg_eur = total_annual_div / 12.0

    # ── Generazione distribuzione mensile aggregata ───
    month_names_list = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    monthly_rows = []

    for m in range(1, 13):
        m_name = month_names_list[m - 1]
        if not df_events.empty:
            m_events = df_events[df_events["month_num"] == m]
            tot = float(m_events["installment_payout_eur"].sum()) if not m_events.empty else 0.0
            comps = ", ".join([f"{r['ticker']} (€ {r['installment_payout_eur']:.2f})" for _, r in m_events.iterrows()]) if not m_events.empty else "-"
            n_paying = len(m_events)
        else:
            tot = 0.0
            comps = "-"
            n_paying = 0

        w_ratio = (tot / total_annual_div) if total_annual_div > 0 else 0.0
        monthly_rows.append({
            "month_num": m,
            "month_name": m_name,
            "projected_payout_eur": round(tot, 2),
            "pct_of_annual": round(w_ratio * 100, 1),
            "num_paying_companies": n_paying,
            "paying_companies": comps
        })

    df_monthly = pd.DataFrame(monthly_rows)

    # ── Matrice Annuale Dividendi (Titolo x Mese) ───
    matrix_rows = []
    if not df_breakdown.empty:
        paying_df = df_breakdown[df_breakdown["annual_payout_eur"] > 0]
        for _, b in paying_df.iterrows():
            t = b["ticker"]
            t_events = df_events[df_events["ticker"] == t] if not df_events.empty else pd.DataFrame()
            row_dict = {"Ticker": t, "Yield %": b["dividend_yield_pct"], "Frequenza": b["frequency"]}
            for m in range(1, 13):
                m_label = MONTH_LABELS[m]
                m_ev = t_events[t_events["month_num"] == m] if not t_events.empty else pd.DataFrame()
                row_dict[m_label] = float(m_ev["installment_payout_eur"].sum()) if not m_ev.empty else 0.0
            row_dict["Totale Annuo (€)"] = b["annual_payout_eur"]
            matrix_rows.append(row_dict)
    
    df_matrix = pd.DataFrame(matrix_rows)
    if not df_matrix.empty:
        df_matrix = df_matrix.sort_values(by="Totale Annuo (€)", ascending=False)

    return {
        "total_annual_dividends_eur": round(total_annual_div, 2),
        "historical_dividends_total_eur": round(hist_div_total, 2),
        "portfolio_yield_pct": round(portfolio_yield_pct, 2),
        "monthly_average_eur": round(monthly_avg_eur, 2),
        "monthly_forecast": df_monthly,
        "dividend_breakdown": df_breakdown.sort_values(by="annual_payout_eur", ascending=False),
        "calendar_events": df_events,
        "monthly_matrix": df_matrix
    }
