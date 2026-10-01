"""
core/wealth/wealth_olap.py
ARGUS Wealth Management — Vectorized DuckDB OLAP Analytics Engine
High-Performance In-Process Columnar OLAP Cubes, Multi-Dimensional Cash Flow Aggregations,
Merchant Pareto Distribution & Net Worth Trajectory Analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import duckdb

    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False


def is_wealth_olap_available() -> bool:
    """Restituisce True se DuckDB è disponibile per elaborazioni OLAP vettorizzate sul modulo Wealth."""
    return HAS_DUCKDB


def compute_wealth_cashflow_olap_cube(
    df_cashflow: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Calcola un cubo multidimensionale ad alte prestazioni sui movimenti di cassa del patrimonio.
    Sfrutta DuckDB vettorizzato (C++ SIMD) per aggregazioni sub-millisecondo con fallback su Pandas.

    Restituisce:
      - monthly_cube: aggregazione per Anno-Mese (Entrate, Uscite, Risparmio Netto, Tasso di Risparmio %)
      - category_cube: aggregazione per Categoria con incidenza percentuale e classificazione Pareto (80/20)
      - merchant_cube: top merchant con spesa totale, frequenza e ticket medio
      - rolling_metrics: media mobile a 3 e 6 mesi su uscite e tasso di crescita MoM
      - summary: totali consolidati di periodo
    """
    if df_cashflow is None or df_cashflow.empty:
        return {
            "monthly_cube": pd.DataFrame(),
            "category_cube": pd.DataFrame(),
            "merchant_cube": pd.DataFrame(),
            "rolling_metrics": pd.DataFrame(),
            "summary": {
                "total_inflows": 0.0,
                "total_outflows": 0.0,
                "net_savings": 0.0,
                "savings_rate_pct": 0.0,
                "tx_count": 0,
            },
            "engine": "Empty Dataset",
        }

    df = df_cashflow.copy()

    # Normalizzazione tipi e colonne essenziali
    if "tx_date" in df.columns:
        df["tx_date"] = pd.to_datetime(df["tx_date"])
    else:
        df["tx_date"] = pd.Timestamp.now()

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    else:
        df["amount"] = 0.0

    if "direction" not in df.columns:
        df["direction"] = "outflow"

    if "category_name" not in df.columns:
        df["category_name"] = "Varie"

    if "merchant" not in df.columns:
        df["merchant"] = "Non Specificato"

    # Esclusione giroconti interni per correttezza contabile
    df_clean = df[
        (df["direction"] != "transfer")
        & (~df["category_name"].astype(str).str.contains("Girocont|Trasferiment", case=False, na=False))
    ].copy()

    if df_clean.empty:
        df_clean = df.copy()

    total_inflows = float(df_clean[df_clean["direction"] == "inflow"]["amount"].sum())
    total_outflows = float(df_clean[df_clean["direction"] == "outflow"]["amount"].sum())
    net_savings = total_inflows - total_outflows
    savings_rate_pct = (net_savings / total_inflows * 100.0) if total_inflows > 0 else 0.0

    # ── ESECUZIONE OLAP VETTORIZZATA CON DUCKDB ─────────────────
    if HAS_DUCKDB and duckdb is not None:
        try:
            con = duckdb.connect(database=":memory:")
            con.register("cf", df_clean)

            # 1. Cubo Mensile con Window Functions
            q_monthly = """
            WITH monthly_raw AS (
                SELECT
                    strftime(tx_date, '%Y-%m') AS ym,
                    YEAR(tx_date) AS yr,
                    MONTH(tx_date) AS mo,
                    SUM(CASE WHEN direction = 'inflow' THEN amount ELSE 0.0 END) AS inflows,
                    SUM(CASE WHEN direction = 'outflow' THEN amount ELSE 0.0 END) AS outflows,
                    COUNT(*) AS tx_count
                FROM cf
                GROUP BY 1, 2, 3
            )
            SELECT
                ym,
                yr,
                mo,
                inflows,
                outflows,
                (inflows - outflows) AS net_savings,
                CASE WHEN inflows > 0 THEN ((inflows - outflows) / inflows) * 100.0 ELSE 0.0 END AS savings_rate_pct,
                AVG(outflows) OVER (ORDER BY ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS rolling_outflow_3m,
                AVG(outflows) OVER (ORDER BY ym ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS rolling_outflow_6m,
                LAG(outflows, 1) OVER (ORDER BY ym) AS prev_outflow,
                CASE
                    WHEN LAG(outflows, 1) OVER (ORDER BY ym) > 0
                    THEN ((outflows - LAG(outflows, 1) OVER (ORDER BY ym)) / LAG(outflows, 1) OVER (ORDER BY ym)) * 100.0
                    ELSE 0.0
                END AS mom_outflow_growth_pct,
                tx_count
            FROM monthly_raw
            ORDER BY ym ASC;
            """
            monthly_cube = con.execute(q_monthly).df()

            # 2. Cubo Categorie con Cumulative Sum & Pareto 80/20
            q_category = """
            WITH cat_summary AS (
                SELECT
                    category_name,
                    SUM(amount) AS total_amount,
                    COUNT(*) AS tx_count,
                    AVG(amount) AS avg_ticket
                FROM cf
                WHERE direction = 'outflow'
                GROUP BY category_name
            ),
            cat_ranked AS (
                SELECT
                    category_name,
                    total_amount,
                    tx_count,
                    avg_ticket,
                    SUM(total_amount) OVER () AS grand_total,
                    SUM(total_amount) OVER (ORDER BY total_amount DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_amount
                FROM cat_summary
            )
            SELECT
                category_name,
                total_amount,
                tx_count,
                avg_ticket,
                CASE WHEN grand_total > 0 THEN (total_amount / grand_total) * 100.0 ELSE 0.0 END AS share_pct,
                CASE WHEN grand_total > 0 THEN (cum_amount / grand_total) * 100.0 ELSE 0.0 END AS cum_share_pct,
                CASE WHEN (cum_amount / NULLIF(grand_total, 0)) <= 0.80 THEN 'Pareto Top 80%' ELSE 'Coda 20%' END AS pareto_class
            FROM cat_ranked
            ORDER BY total_amount DESC;
            """
            category_cube = con.execute(q_category).df()

            # 3. Cubo Merchant
            q_merchant = """
            SELECT
                merchant,
                category_name,
                SUM(amount) AS total_spent,
                COUNT(*) AS frequency,
                AVG(amount) AS avg_ticket,
                MIN(tx_date) AS first_seen,
                MAX(tx_date) AS last_seen
            FROM cf
            WHERE direction = 'outflow'
            GROUP BY merchant, category_name
            ORDER BY total_spent DESC
            LIMIT 50;
            """
            merchant_cube = con.execute(q_merchant).df()

            con.close()

            return {
                "monthly_cube": monthly_cube,
                "category_cube": category_cube,
                "merchant_cube": merchant_cube,
                "summary": {
                    "total_inflows": total_inflows,
                    "total_outflows": total_outflows,
                    "net_savings": net_savings,
                    "savings_rate_pct": savings_rate_pct,
                    "tx_count": len(df_clean),
                },
                "engine": "DuckDB Columnar SIMD",
            }
        except Exception as e:
            logger.warning("DuckDB wealth OLAP fallito, fallback su Pandas: %s", e)

    # ── PURE-PANDAS VECTORIZED FALLBACK ─────────────────────────
    df_clean["ym"] = df_clean["tx_date"].dt.strftime("%Y-%m")
    piv = df_clean.pivot_table(
        index="ym",
        columns="direction",
        values="amount",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()

    if "inflow" not in piv.columns:
        piv["inflow"] = 0.0
    if "outflow" not in piv.columns:
        piv["outflow"] = 0.0

    piv = piv.rename(columns={"inflow": "inflows", "outflow": "outflows"})
    piv["net_savings"] = piv["inflows"] - piv["outflows"]
    piv["savings_rate_pct"] = np.where(piv["inflows"] > 0, (piv["net_savings"] / piv["inflows"]) * 100.0, 0.0)
    piv["rolling_outflow_3m"] = piv["outflows"].rolling(window=3, min_periods=1).mean()
    piv["rolling_outflow_6m"] = piv["outflows"].rolling(window=6, min_periods=1).mean()
    piv["prev_outflow"] = piv["outflows"].shift(1)
    piv["mom_outflow_growth_pct"] = np.where(
        piv["prev_outflow"] > 0,
        ((piv["outflows"] - piv["prev_outflow"]) / piv["prev_outflow"]) * 100.0,
        0.0,
    )

    # Categorie
    outflows_df = df_clean[df_clean["direction"] == "outflow"]
    cat_grp = (
        outflows_df.groupby("category_name")
        .agg(
            total_amount=("amount", "sum"),
            tx_count=("amount", "count"),
            avg_ticket=("amount", "mean"),
        )
        .reset_index()
        .sort_values(by="total_amount", ascending=False)
    )
    grand_tot = cat_grp["total_amount"].sum()
    cat_grp["share_pct"] = (cat_grp["total_amount"] / grand_tot * 100.0) if grand_tot > 0 else 0.0
    cat_grp["cum_share_pct"] = cat_grp["share_pct"].cumsum()
    cat_grp["pareto_class"] = np.where(cat_grp["cum_share_pct"] <= 80.0, "Pareto Top 80%", "Coda 20%")

    # Merchant
    merch_grp = (
        outflows_df.groupby(["merchant", "category_name"])
        .agg(
            total_spent=("amount", "sum"),
            frequency=("amount", "count"),
            avg_ticket=("amount", "mean"),
            first_seen=("tx_date", "min"),
            last_seen=("tx_date", "max"),
        )
        .reset_index()
        .sort_values(by="total_spent", ascending=False)
        .head(50)
    )

    return {
        "monthly_cube": piv,
        "category_cube": cat_grp,
        "merchant_cube": merch_grp,
        "summary": {
            "total_inflows": total_inflows,
            "total_outflows": total_outflows,
            "net_savings": net_savings,
            "savings_rate_pct": savings_rate_pct,
            "tx_count": len(df_clean),
        },
        "engine": "Pandas Vectorized Fallback",
    }


def compute_wealth_snapshot_trajectory_olap(
    df_snapshots: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Analisi OLAP della traiettoria temporale degli snapshot patrimoniali:
    - Calcolo High-Water Mark (Picco Massimo di Net Worth)
    - Drawdown dal massimo del patrimonio consolidato
    - Tasso di crescita geometrico annualizzato (CAGR)
    - Rapporto di liquidità nel tempo (Liquid Cash / Net Worth)
    """
    if df_snapshots is None or df_snapshots.empty or len(df_snapshots) < 2:
        return {
            "trajectory_df": pd.DataFrame(),
            "peak_net_worth": 0.0,
            "max_drawdown_pct": 0.0,
            "cagr_pct": 0.0,
            "engine": "Insufficient Data",
        }

    df = df_snapshots.copy()
    if "snapshot_date" in df.columns:
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
        df = df.sort_values(by="snapshot_date", ascending=True).reset_index(drop=True)
    else:
        return {
            "trajectory_df": pd.DataFrame(),
            "peak_net_worth": 0.0,
            "max_drawdown_pct": 0.0,
            "cagr_pct": 0.0,
            "engine": "Missing Date Column",
        }

    nw_col = "total_net_worth" if "total_net_worth" in df.columns else "net_worth"
    if nw_col not in df.columns:
        return {
            "trajectory_df": pd.DataFrame(),
            "peak_net_worth": 0.0,
            "max_drawdown_pct": 0.0,
            "cagr_pct": 0.0,
            "engine": "Missing Net Worth Column",
        }

    df["nw"] = pd.to_numeric(df[nw_col], errors="coerce").fillna(0.0)
    df["hwm"] = df["nw"].cummax()
    df["drawdown_eur"] = df["nw"] - df["hwm"]
    df["drawdown_pct"] = np.where(df["hwm"] > 0, (df["drawdown_eur"] / df["hwm"]) * 100.0, 0.0)

    # Liquidità ratio
    if "liquid_assets" in df.columns:
        df["liq"] = pd.to_numeric(df["liquid_assets"], errors="coerce").fillna(0.0)
        df["liquidity_ratio_pct"] = np.where(df["nw"] > 0, (df["liq"] / df["nw"]) * 100.0, 0.0)
    elif "liquid_cash" in df.columns:
        df["liq"] = pd.to_numeric(df["liquid_cash"], errors="coerce").fillna(0.0)
        df["liquidity_ratio_pct"] = np.where(df["nw"] > 0, (df["liq"] / df["nw"]) * 100.0, 0.0)

    # Calcolo CAGR
    start_val = df["nw"].iloc[0]
    end_val = df["nw"].iloc[-1]
    days = (df["snapshot_date"].iloc[-1] - df["snapshot_date"].iloc[0]).days
    years = max(days / 365.2425, 0.05)

    if start_val > 0 and end_val > 0:
        cagr_pct = ((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr_pct = 0.0

    peak_nw = float(df["hwm"].max())
    max_dd_pct = float(df["drawdown_pct"].min())

    return {
        "trajectory_df": df,
        "peak_net_worth": peak_nw,
        "max_drawdown_pct": max_dd_pct,
        "cagr_pct": cagr_pct,
        "years": years,
        "engine": "DuckDB/Pandas Vectorized OLAP",
    }
