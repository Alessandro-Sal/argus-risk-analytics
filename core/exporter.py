# ============================================================
# exporter.py
# Investment Risk BI Platform
#
# Genera i CSV ottimizzati per Looker Studio e Power BI
# Input:  results dict da risk_engine.compute_risk()
# Output: 4 file CSV nella cartella /exports/
# ============================================================

import pandas as pd
import numpy as np
import os
from datetime import datetime

EXPORT_DIR = "exports"


# ── Funzione principale ──────────────────────────────────────

def export_all(results: dict, portfolio_name: str = "portfolio") -> dict:
    """
    Genera tutti i file CSV di export.

    Returns
    -------
    dict con i path dei file generati
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)

    slug = portfolio_name.lower().replace(" ", "_")
    ts   = datetime.now().strftime("%Y%m%d")

    paths = {}

    paths["positions"]    = _export_positions(results, slug, ts)
    paths["returns"]      = _export_returns(results, slug, ts)
    paths["metrics"]      = _export_metrics(results, slug, ts)
    paths["transactions"] = _export_transactions(results, slug, ts)
    paths["ai_insights"]  = _export_ai_insights(results, slug, ts)

    print("\n📁 FILE ESPORTATI:")
    for name, path in paths.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f"   {name:<15} → {path}  ({size:.1f} KB)")
        else:
            print(f"   {name:<15} → {path}  (file non generato)")

    return paths


# ── Export 1: positions.csv ──────────────────────────────────

def _export_positions(results: dict, slug: str, ts: str) -> str:
    """
    Una riga per asset. Usato in Looker Studio per:
    - Tabella posizioni
    - Donut chart concentrazione
    - Scorecard P&L per ticker
    - Treemap per asset class / settore
    """
    pos = results["positions"].copy()
    con = results["metrics"]["concentration"]
    ret = results["metrics"]["returns"]

    # Aggiunge campi calcolati utili per i filtri in Looker Studio
    pos["portfolio_name"]    = slug
    pos["export_date"]       = ts
    pos["portfolio_value"]   = ret["portfolio_value"]

    # Colonna semaforo rischio per filtri rapidi
    pos["pnl_status"] = pos["unrealized_pnl"].apply(
        lambda x: "profit" if x > 0 else ("loss" if x < 0 else "neutral")
    )

    # Peso in percentuale già formattato come float (non stringa)
    # Looker Studio lo usa come metrica numerica
    pos["weight_pct"] = pos["weight_pct"].round(4)
    
    # Markowitz Optimal Weights
    opt = results.get("optimization")
    if opt and opt.get("tickers"):
        opt_tickers = opt["tickers"]
        opt_weights = opt["max_sharpe"]["weights"]
        weight_map = {t: round(w * 100, 4) for t, w in zip(opt_tickers, opt_weights)}
        pos["opt_weight_pct"] = pos["ticker"].map(weight_map)
    else:
        pos["opt_weight_pct"] = None

    # Ordine colonne ottimizzato per Looker Studio
    # (dimensioni prima, metriche dopo)
    cols_ordered = [
        # ── Dimensioni (usate come filtri/raggruppamenti) ──
        "portfolio_name",
        "export_date",
        "ticker",
        "asset_class",
        "gics_sector",
        "industry",
        "country",
        "currency",
        "exchange",
        "recommendation_key",
        "pnl_status",
        # ── Metriche quantitative/monetarie ────────────────
        "qty_net",
        "avg_cost",
        "last_price",
        "current_value",
        "cost_basis",
        "weight_pct",
        "opt_weight_pct",
        "unrealized_pnl",
        "realized_pnl",
        "dividends_total",
        "total_return",
        "portfolio_value",
        "days_to_liquidate",
        # ── Metriche fondamentali & BI ──────────────────────
        "market_cap",
        "total_revenue",
        "ebitda",
        "trailing_pe",
        "forward_pe",
        "price_to_book",
        "dividend_yield",
        "roe",
        "profit_margins",
        "gross_margins",
        "operating_margins",
        "debt_to_equity",
        "revenue_growth",
        "earnings_growth",
        "beta_5y",
        "fifty_two_week_high",
        "fifty_two_week_low",
        "fifty_day_average",
        "two_hundred_day_average",
        "target_mean_price",
        "peg_ratio",
    ]

    # Mantieni solo colonne esistenti nell'ordine specificato
    cols = [c for c in cols_ordered if c in pos.columns]
    pos  = pos[cols]

    path = os.path.join(EXPORT_DIR, f"positions_{slug}_{ts}.csv")
    pos.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ── Export 2: returns.csv ────────────────────────────────────

def _export_returns(results: dict, slug: str, ts: str) -> str:
    """
    Serie temporale giornaliera. Usato in Looker Studio per:
    - Grafico rendimento cumulato nel tempo
    - Grafico drawdown
    - Confronto portafoglio vs benchmark
    """
    sr_port = results["portfolio_return"]
    sr_bm   = results["benchmark_return"]
    mk      = results["metrics"]["market_risk"]

    df = pd.DataFrame({
        "date":               sr_port.index.strftime("%Y-%m-%d"),
        "portfolio_name":     slug,
        "daily_return_pct":   (sr_port.values * 100).round(6),
        "benchmark_return_pct": (sr_bm.reindex(sr_port.index).fillna(0).values * 100).round(6),
        "benchmark_ticker":   mk["benchmark_ticker"],
    })

    # Rendimento cumulato (Looker Studio può farlo con campi calcolati,
    # ma averlo già pronto semplifica il setup)
    df["cumulative_return_pct"]   = ((1 + sr_port.values).cumprod() - 1) * 100
    df["cumulative_return_pct"]   = df["cumulative_return_pct"].round(4)

    bm_vals = sr_bm.reindex(sr_port.index).fillna(0).values
    df["benchmark_cumulative_pct"] = ((1 + bm_vals).cumprod() - 1) * 100
    df["benchmark_cumulative_pct"] = df["benchmark_cumulative_pct"].round(4)

    # Drawdown giornaliero
    cum     = (1 + sr_port).cumprod()
    roll_mx = cum.cummax()
    dd      = (cum - roll_mx) / roll_mx * 100
    df["drawdown_pct"] = dd.values.round(4)

    # Anno e mese come dimensioni separate (utili per filtri temporali)
    dates = pd.to_datetime(df["date"])
    df["year"]       = dates.dt.year
    df["month"]      = dates.dt.month
    df["year_month"] = dates.dt.strftime("%Y-%m")

    path = os.path.join(EXPORT_DIR, f"returns_{slug}_{ts}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ── Export 3: metrics.csv ────────────────────────────────────

def _export_metrics(results: dict, slug: str, ts: str) -> str:
    """
    Una singola riga con tutte le metriche aggregate.
    Usato in Looker Studio per:
    - Scorecard (KPI card): Sharpe, VaR, CAGR, etc.
    - Tabella riepilogo rischio

    Nota: una riga per snapshot → se lo script gira ogni giorno
    accumula uno storico delle metriche nel tempo.
    """
    ret = results["metrics"]["returns"]
    mk  = results["metrics"]["market_risk"]
    con = results["metrics"]["concentration"]

    row = {
        # Identificatori
        "portfolio_name":          slug,
        "computed_at":             results["computed_at"],
        "export_date":             ts,

        # Rendimento
        "portfolio_value_eur":     ret["portfolio_value"],
        "cost_basis_eur":          ret["cost_basis_total"],
        "total_pnl_eur":           ret["total_pnl"],
        "dividends_total_eur":     ret["dividends_total"],
        "total_return_pct":        ret["total_return_pct"],
        "cagr_pct":                ret["cagr_pct"],
        "alpha_pct":               ret["alpha_pct"],
        "benchmark_cagr_pct":      ret["benchmark_cagr_pct"],
        "n_years":                 ret["n_years"],

        # Risk-adjusted
        "sharpe_ratio":            ret["sharpe_ratio"],
        "sortino_ratio":           ret["sortino_ratio"],
        "calmar_ratio":            ret["calmar_ratio"],
        "information_ratio":       ret["information_ratio"],

        # Market risk
        "volatility_annual_pct":   mk["volatility_annual_pct"],
        "skewness":                mk.get("skewness"),
        "kurtosis":                mk.get("kurtosis"),
        "tracking_error_pct":      mk.get("tracking_error_pct"),
        "var_95_pct":              mk["var_95"],
        "var_99_pct":              mk["var_99"],
        "var_parametric_95_pct":   mk.get("var_parametric_95"),
        "var_parametric_99_pct":   mk.get("var_parametric_99"),
        "var_cf_95_pct":           mk.get("var_cf_95"),
        "var_cf_99_pct":           mk.get("var_cf_99"),
        "cvar_95_pct":             mk["cvar_95"],
        "cvar_99_pct":             mk["cvar_99"],
        "beta":                    mk["beta"],
        "correlation_benchmark":   mk["correlation_benchmark"],
        "r_squared_pct":           mk.get("r_squared_pct"),
        "max_drawdown_pct":        mk["max_drawdown_pct"],
        "var_exceptions_count":    mk.get("var_exceptions_count"),
        "benchmark_ticker":        mk["benchmark_ticker"],
        "n_trading_days":          mk["n_trading_days"],

        # Concentrazione
        "hhi":                     con["hhi"],
        "effective_n_assets":      con["effective_n_assets"],
        "n_active_positions":      con["n_active_positions"],

        # Label semaforo rischio (utile per filtri colore in Looker Studio)
        "risk_level":              _risk_label(mk["volatility_annual_pct"],
                                               mk["var_95"]),
                                               
        # Ottimizzazione Markowitz
        "opt_max_sharpe_ratio":    results.get("optimization", {}).get("max_sharpe", {}).get("sharpe"),
        "opt_max_sharpe_return":   results.get("optimization", {}).get("max_sharpe", {}).get("return", 0) * 100 if results.get("optimization") else None,
        "opt_max_sharpe_risk":     results.get("optimization", {}).get("max_sharpe", {}).get("risk", 0) * 100 if results.get("optimization") else None,
        "opt_min_vol_ratio":       results.get("optimization", {}).get("min_vol", {}).get("sharpe"),
        "opt_min_vol_return":      results.get("optimization", {}).get("min_vol", {}).get("return", 0) * 100 if results.get("optimization") else None,
        "opt_min_vol_risk":        results.get("optimization", {}).get("min_vol", {}).get("risk", 0) * 100 if results.get("optimization") else None,
        
        # Qualità dati
        "warning_messages":        " | ".join(results.get("warnings", [])),
    }


    df = pd.DataFrame([row])
    path = os.path.join(EXPORT_DIR, f"metrics_{slug}_{ts}.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ── Export 4: transactions.csv ───────────────────────────────

def _export_transactions(results: dict, slug: str, ts: str) -> str:
    """
    Storico transazioni arricchito con il valore corrente.
    """
    path = os.path.join(EXPORT_DIR, f"transactions_{slug}_{ts}.csv")

    if "transactions" not in results:
        pd.DataFrame(columns=[
            "portfolio_name", "export_date", "ticker", "tx_date",
            "tx_type", "quantity", "price", "currency", "fees",
            "notes", "current_value_tx", "tx_cost",
            "year", "month", "year_month"
        ]).to_csv(path, index=False, encoding="utf-8-sig")
        return path

    pos   = results["positions"][["ticker", "last_price"]].copy()
    df_tx = results["transactions"].copy()

    df_tx = df_tx.merge(pos[["ticker", "last_price"]], on="ticker", how="left")

    df_tx["portfolio_name"]   = slug
    df_tx["export_date"]      = ts
    df_tx["current_value_tx"] = (df_tx["quantity"] * df_tx["last_price"]).round(2)
    df_tx["tx_cost"]          = (df_tx["quantity"] * df_tx["price"] + df_tx.get("fees", 0)).round(2)

    df_tx["tx_date"]    = pd.to_datetime(df_tx["tx_date"])
    df_tx["year"]       = df_tx["tx_date"].dt.year
    df_tx["month"]      = df_tx["tx_date"].dt.month
    df_tx["year_month"] = df_tx["tx_date"].dt.strftime("%Y-%m")
    df_tx["tx_date"]    = df_tx["tx_date"].dt.strftime("%Y-%m-%d")

    df_tx.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# ── Helper: etichetta rischio ────────────────────────────────

def _risk_label(vol_annual: float, var_95: float) -> str:
    """
    Classifica il rischio del portafoglio in tre livelli.
    Usato come dimensione colore in Looker Studio.
    """
    if vol_annual is None:
        return "unknown"
    if vol_annual < 10 or var_95 < 1:
        return "low"
    if vol_annual < 20 or var_95 < 2:
        return "medium"
    return "high"


# ── Export 5: ai_insights.csv ────────────────────────────────

def _export_ai_insights(results: dict, slug: str, ts: str) -> str:
    """
    Esporta i cluster K-Means e le simulazioni Monte Carlo in formato tabellare.
    """
    ai = results.get("metrics", {}).get("ai_insights", {})
    path = os.path.join(EXPORT_DIR, f"ai_insights_{slug}_{ts}.csv")
    
    clusters = ai.get("asset_clusters", [])
    mc = ai.get("montecarlo", {})
    
    if not clusters and not mc:
        # Crea un file vuoto con headers
        pd.DataFrame(columns=[
            "portfolio_name", "export_date", "ticker", "volatility", "cagr", 
            "ai_cluster", "mc_expected_return_1y", "mc_var_95", "mc_var_99"
        ]).to_csv(path, index=False, encoding="utf-8-sig")
        return path
        
    rows = []
    
    # Se ci sono cluster, usiamo quelli come base
    if clusters:
        for c in clusters:
            rows.append({
                "portfolio_name": slug,
                "export_date": ts,
                "ticker": c.get("ticker", c.get("index")), # pandas reset_index nomina l'indice "ticker" o "index"
                "volatility": round(c.get("volatility", 0) * 100, 4),
                "cagr": round(c.get("cagr", 0) * 100, 4),
                "ai_cluster": f"Cluster {c.get('cluster', 0)}",
                "mc_expected_return_1y": mc.get("expected_return_1y_pct"),
                "mc_var_95": mc.get("var_95_simulated_pct"),
                "mc_var_99": mc.get("var_99_simulated_pct"),
            })
    else:
        # Solo monte carlo, no clusters
        rows.append({
            "portfolio_name": slug,
            "export_date": ts,
            "ticker": "PORTFOLIO",
            "volatility": None,
            "cagr": None,
            "ai_cluster": None,
            "mc_expected_return_1y": mc.get("expected_return_1y_pct"),
            "mc_var_95": mc.get("var_95_simulated_pct"),
            "mc_var_99": mc.get("var_99_simulated_pct"),
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path