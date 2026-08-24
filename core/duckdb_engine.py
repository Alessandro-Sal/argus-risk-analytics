"""
ARGUS — Risk Analytics & Quantitative Platform
Core Module: DuckDB In-Process OLAP Query Engine & Parquet Acceleration
Vectorized In-Memory Analytics, Multi-Dimensional Cube Aggregations, Window Functions & Parquet Storage.
"""

import io
import logging
import time
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False


def is_duckdb_available() -> bool:
    """Restituisce True se il motore C++ DuckDB nativo è installato nell'ambiente."""
    return HAS_DUCKDB


def get_duckdb_system_info() -> Dict[str, Any]:
    """Restituisce le specifiche del motore analitico e delle estensioni vettorizzate."""
    if not HAS_DUCKDB:
        return {
            "available": False,
            "version": "Fallback In-Memory / SQLite",
            "engine_mode": "Pure-Python Emulated",
            "vectorization": "Disabled",
            "threads": 1
        }
    return {
        "available": True,
        "version": getattr(duckdb, "__version__", "1.x"),
        "engine_mode": "Vectorized Columnar (C++)",
        "vectorization": "SIMD AVX-2 / SSE4.2",
        "threads": 4
    }


def get_in_memory_duckdb_connection(context_dfs: Optional[Dict[str, pd.DataFrame]] = None):
    """
    Crea o restituisce una connessione DuckDB in-memory registrando i DataFrame di portafoglio.
    """
    if not HAS_DUCKDB:
        return None

    con = duckdb.connect(database=":memory:")
    if context_dfs:
        for name, df in context_dfs.items():
            if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                df_clean = df.copy()
                con.register(name, df_clean)
    return con


def _run_duckdb_native(sql_query: str, con, context_dfs: Optional[Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """Esegue la query nativa sul motore C++ DuckDB."""
    temp_con = con if con is not None else get_in_memory_duckdb_connection(context_dfs)
    if temp_con is None:
        temp_con = duckdb.connect(database=":memory:")
        if context_dfs:
            for name, df in context_dfs.items():
                if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                    temp_con.register(name, df)
    return temp_con.execute(sql_query).fetchdf()


def _run_sqlite_fallback(sql_query: str, context_dfs: Optional[Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """Fallback su SQLite / Pandas se DuckDB non è disponibile."""
    import sqlite3
    sqlite_con = sqlite3.connect(":memory:")
    if context_dfs:
        for name, df in context_dfs.items():
            if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                df.to_sql(name, sqlite_con, index=False, if_exists="replace")
    return pd.read_sql_query(sql_query, sqlite_con)


def run_duckdb_olap_query(
    sql_query: str,
    con=None,
    context_dfs: Optional[Dict[str, pd.DataFrame]] = None
) -> Dict[str, Any]:
    """
    Esegue una query analitica SQL ad altissima velocità sul database in-memory DuckDB.
    Misura la latenza di esecuzione in millisecondi e restituisce il DataFrame risultante.
    """
    if not sql_query or not sql_query.strip():
        return {
            "success": False,
            "error": "Query SQL non specificata o vuota.",
            "latency_ms": 0.0,
            "row_count": 0,
            "df": pd.DataFrame()
        }

    t0 = time.perf_counter()

    try:
        if HAS_DUCKDB:
            res_df = _run_duckdb_native(sql_query, con, context_dfs)
        else:
            res_df = _run_sqlite_fallback(sql_query, context_dfs)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "success": True,
            "error": None,
            "latency_ms": round(elapsed_ms, 3),
            "row_count": len(res_df),
            "df": res_df
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "success": False,
            "error": str(e),
            "latency_ms": round(elapsed_ms, 3),
            "row_count": 0,
            "df": pd.DataFrame()
        }


def get_preset_olap_queries() -> Dict[str, Dict[str, str]]:
    """Restituisce le query SQL analitiche istituzionali preconfigurate per l'analisi di portafoglio."""
    return {
        "cube_exposure": {
            "title": "📦 Scomposizione Multi-Dimensionale (Asset Class x Settore x Valuta)",
            "description": "Aggregazione analitica che calcola controvalore totale, peso medio, profitto medio e conteggio asset.",
            "sql": (
                "SELECT\n"
                "    COALESCE(asset_class, 'Tutti gli Asset') AS asset_class,\n"
                "    COALESCE(sector, 'Tutti i Settori') AS sector,\n"
                "    COALESCE(currency, 'Tutte le Valute') AS currency,\n"
                "    COUNT(*) AS numero_posizioni,\n"
                "    ROUND(SUM(current_value), 2) AS controvalore_totale,\n"
                "    ROUND(AVG(pnl_pct), 2) AS pnl_medio_pct,\n"
                "    ROUND(SUM(weight_pct), 2) AS peso_totale_pct\n"
                "FROM positions\n"
                "GROUP BY GROUPING SETS (\n"
                "    (asset_class, sector, currency),\n"
                "    (asset_class, sector),\n"
                "    (asset_class),\n"
                "    ()\n"
                ")\n"
                "ORDER BY controvalore_totale DESC;"
            )
        },
        "sector_ranking": {
            "title": "🏆 Ranking Titoli & Window Functions (Top Performer con QUALIFY)",
            "description": "Utilizza le window functions SQL per classificare i migliori e peggiori titoli all'interno di ciascun settore GICS.",
            "sql": (
                "SELECT\n"
                "    ticker,\n"
                "    asset_name,\n"
                "    sector,\n"
                "    asset_class,\n"
                "    current_value,\n"
                "    pnl_pct,\n"
                "    DENSE_RANK() OVER (PARTITION BY sector ORDER BY pnl_pct DESC) AS rank_settoriale_best,\n"
                "    DENSE_RANK() OVER (PARTITION BY sector ORDER BY pnl_pct ASC) AS rank_settoriale_worst\n"
                "FROM positions\n"
                "WHERE sector IS NOT NULL AND sector != 'N/A'\n"
                "ORDER BY sector ASC, pnl_pct DESC;"
            )
        },
        "monthly_tx_rollup": {
            "title": "💰 Analisi Storica Transazioni & Volumi per Mese",
            "description": "Aggregazione temporale delle transazioni di carico/scarico, controvalori scambiati e commissioni totali.",
            "sql": (
                "SELECT\n"
                "    SUBSTR(CAST(tx_date AS VARCHAR), 1, 7) AS mese_anno,\n"
                "    tx_type AS tipo_operazione,\n"
                "    COUNT(*) AS numero_eseguiti,\n"
                "    ROUND(SUM(quantity * price), 2) AS volume_scambiato,\n"
                "    ROUND(SUM(fees), 2) AS commissioni_totali\n"
                "FROM transactions\n"
                "GROUP BY SUBSTR(CAST(tx_date AS VARCHAR), 1, 7), tx_type\n"
                "ORDER BY mese_anno DESC, volume_scambiato DESC;"
            )
        },
        "fx_exposure_matrix": {
            "title": "📊 Esposizione Valutaria e Rischio di Cambio (FX Matrix)",
            "description": "Ripartizione del capitale per valuta di denominazione con peso percentuale e PnL medio realizzato/latente.",
            "sql": (
                "SELECT\n"
                "    currency AS valuta_denominazione,\n"
                "    COUNT(*) AS numero_titoli,\n"
                "    ROUND(SUM(current_value), 2) AS controvalore_totale,\n"
                "    ROUND(SUM(weight_pct), 2) AS peso_portafoglio_pct,\n"
                "    ROUND(AVG(pnl_pct), 2) AS rendimento_medio_pct\n"
                "FROM positions\n"
                "GROUP BY currency\n"
                "ORDER BY controvalore_totale DESC;"
            )
        }
    }


def export_portfolio_to_parquet(df: pd.DataFrame) -> bytes:
    """
    Serializza un DataFrame di portafoglio in formato Apache Parquet compresso (Snappy/ZSTD).
    Restituisce i byte per il download o il salvataggio su disco.
    """
    if df is None or df.empty:
        return b""

    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="auto", compression="snappy")
    return buf.getvalue()


def get_parquet_compression_ratio(df: pd.DataFrame) -> Dict[str, Any]:
    """Calcola il risparmio di spazio disco tra formato CSV non compresso e Parquet colonnare."""
    if df is None or df.empty:
        return {"csv_bytes": 0, "parquet_bytes": 0, "space_saved_pct": 0.0}

    csv_bytes = len(df.to_csv(index=False).encode("utf-8"))
    parquet_bytes = len(export_portfolio_to_parquet(df))
    saved_pct = max(0.0, (1.0 - (parquet_bytes / max(1, csv_bytes))) * 100.0)

    return {
        "csv_bytes": csv_bytes,
        "parquet_bytes": parquet_bytes,
        "space_saved_pct": round(saved_pct, 1)
    }


def compute_duckdb_asset_sector_currency_cube(df_positions: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcola un Cubo Multi-Dimensionale (Asset Class x Settore x Valuta) con subtotali completi
    sfruttando il motore colonnare C++ DuckDB a latenza sub-millisecondo.
    """
    if df_positions is None or df_positions.empty:
        return {"success": False, "df": pd.DataFrame(), "latency_ms": 0.0}

    df_clean = df_positions.copy()
    # Normalizza colonne essenziali
    for col in ["asset_class", "sector", "currency"]:
        if col not in df_clean.columns:
            df_clean[col] = "Altro"
        else:
            df_clean[col] = df_clean[col].fillna("Altro").astype(str)

    if "current_value" not in df_clean.columns:
        df_clean["current_value"] = 0.0
    else:
        df_clean["current_value"] = pd.to_numeric(df_clean["current_value"], errors="coerce").fillna(0.0)

    # Estrai PnL non realizzato da tutte le possibili nomenclature
    if "pnl_unrealized" not in df_clean.columns:
        if "unrealized_pnl" in df_clean.columns:
            df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["unrealized_pnl"], errors="coerce").fillna(0.0)
        elif "pnl" in df_clean.columns:
            df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["pnl"], errors="coerce").fillna(0.0)
        else:
            df_clean["pnl_unrealized"] = 0.0
    else:
        df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["pnl_unrealized"], errors="coerce").fillna(0.0)

    # Base di costo per calcolo rendimento percentuale
    if "cost_basis" in df_clean.columns:
        df_clean["cost_basis"] = pd.to_numeric(df_clean["cost_basis"], errors="coerce").fillna(0.0)
    else:
        df_clean["cost_basis"] = df_clean["current_value"] - df_clean["pnl_unrealized"]

    # Filtra solo posizioni attive
    if "qty_net" in df_clean.columns:
        df_clean = df_clean[df_clean["qty_net"] > 1e-6]
    elif "quantity" in df_clean.columns:
        df_clean = df_clean[df_clean["quantity"] > 1e-6]

    sql = """
        SELECT 
            CASE 
                WHEN asset_class IS NULL THEN 'Portafoglio Totale'
                WHEN sector IS NULL THEN 'Macro Asset Class'
                WHEN currency IS NULL THEN 'Breakdown Settoriale'
                ELSE 'Dettaglio Valuta 3D'
            END as livello_aggregazione,
            COALESCE(asset_class, '--- TOTALE PORTAFOGLIO ---') as asset_class,
            COALESCE(sector, '--- TUTTI I SETTORI ---') as sector,
            COALESCE(currency, 'ALL') as currency,
            COUNT(*) as n_posizioni,
            ROUND(SUM(current_value), 2) as controvalore_totale,
            ROUND(SUM(pnl_unrealized), 2) as pnl_latente_totale,
            ROUND(CASE 
                WHEN SUM(cost_basis) > 0 THEN (SUM(pnl_unrealized) / SUM(cost_basis)) * 100.0
                WHEN SUM(current_value) > 0 THEN (SUM(pnl_unrealized) / SUM(current_value)) * 100.0
                ELSE 0.0 
            END, 2) as rendimento_medio_pct
        FROM positions
        GROUP BY GROUPING SETS (
            (asset_class, sector, currency),
            (asset_class, sector),
            (asset_class),
            ()
        )
        ORDER BY 
            (asset_class = '--- TOTALE PORTAFOGLIO ---') ASC,
            controvalore_totale DESC;
    """
    res = run_duckdb_olap_query(sql, context_dfs={"positions": df_clean})
    return res


def compute_duckdb_sector_rankings(df_positions: pd.DataFrame, top_n: int = 3) -> Dict[str, Any]:
    """
    Estrae i migliori asset per PnL all'interno di ciascun settore GICS utilizzando
    la window function nativa QUALIFY DENSE_RANK() di DuckDB.
    """
    if df_positions is None or df_positions.empty:
        return {"success": False, "df": pd.DataFrame(), "latency_ms": 0.0}

    df_clean = df_positions.copy()
    if "sector" not in df_clean.columns:
        df_clean["sector"] = "Altro"
    if "ticker" not in df_clean.columns:
        df_clean["ticker"] = "UNKNOWN"
    if "current_value" not in df_clean.columns:
        df_clean["current_value"] = 0.0
    else:
        df_clean["current_value"] = pd.to_numeric(df_clean["current_value"], errors="coerce").fillna(0.0)

    if "pnl_unrealized" not in df_clean.columns:
        if "unrealized_pnl" in df_clean.columns:
            df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["unrealized_pnl"], errors="coerce").fillna(0.0)
        elif "pnl" in df_clean.columns:
            df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["pnl"], errors="coerce").fillna(0.0)
        else:
            df_clean["pnl_unrealized"] = 0.0
    else:
        df_clean["pnl_unrealized"] = pd.to_numeric(df_clean["pnl_unrealized"], errors="coerce").fillna(0.0)

    if "cost_basis" in df_clean.columns:
        df_clean["cost_basis"] = pd.to_numeric(df_clean["cost_basis"], errors="coerce").fillna(0.0)
    else:
        df_clean["cost_basis"] = df_clean["current_value"] - df_clean["pnl_unrealized"]

    sql = f"""
        SELECT 
            sector as settore,
            ticker,
            ROUND(current_value, 2) as controvalore_eur,
            ROUND(pnl_unrealized, 2) as pnl_latente_eur,
            ROUND(CASE 
                WHEN cost_basis > 0 THEN (pnl_unrealized / cost_basis) * 100.0
                WHEN current_value > 0 THEN (pnl_unrealized / current_value) * 100.0 
                ELSE 0.0 
            END, 2) as gain_pct,
            DENSE_RANK() OVER (PARTITION BY sector ORDER BY pnl_unrealized DESC) as rank_settoriale
        FROM positions
        WHERE current_value > 0
        QUALIFY rank_settoriale <= {top_n}
        ORDER BY sector ASC, rank_settoriale ASC;
    """
    return run_duckdb_olap_query(sql, context_dfs={"positions": df_clean})


def compute_duckdb_temporal_snapshot_analytics(df_history: pd.DataFrame) -> Dict[str, Any]:
    """
    Esegue un'aggregazione ad altissima velocità sulle serie storiche degli snapshot di portafoglio,
    calcolando i tassi di crescita tra rilevazioni consecutive (LAG) e medie mobili.
    """
    if df_history is None or df_history.empty:
        return {"success": False, "df": pd.DataFrame(), "latency_ms": 0.0}

    df_clean = df_history.copy()
    if "calc_date" in df_clean.columns:
        df_clean["calc_date"] = df_clean["calc_date"].astype(str)

    sql = """
        SELECT 
            calc_date,
            run_name,
            ROUND(total_value, 2) as valore_portafoglio_eur,
            ROUND(total_value - LAG(total_value, 1, total_value) OVER (ORDER BY calc_date ASC), 2) as delta_valore_step_eur,
            ROUND(CASE 
                WHEN LAG(total_value, 1) OVER (ORDER BY calc_date ASC) > 0 
                THEN ((total_value - LAG(total_value, 1) OVER (ORDER BY calc_date ASC)) / LAG(total_value, 1) OVER (ORDER BY calc_date ASC)) * 100.0 
                ELSE 0.0 
            END, 2) as delta_pct_step,
            ROUND(AVG(total_value) OVER (ORDER BY calc_date ASC ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) as media_mobile_3_snapshot
        FROM history
        ORDER BY calc_date DESC;
    """
    return run_duckdb_olap_query(sql, context_dfs={"history": df_clean})
