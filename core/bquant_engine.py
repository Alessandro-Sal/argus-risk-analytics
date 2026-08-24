# ==============================================================================
# core/bquant_engine.py
# ARGUS BQuant Python Sandbox Engine (Bloomberg BQUANT / Jupyter-Style)
# In-memory code executor with DuckDB, Pandas, Plotly and institutional presets.
# ==============================================================================

import sys
import io
import traceback
import contextlib
import time
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import scipy
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    plt = None
    HAS_MATPLOTLIB = False

import duckdb

# ─────────────────────────────────────────────────────────────────────────────
# 1. Institutional Script Snippets & Presets
# ─────────────────────────────────────────────────────────────────────────────

BQUANT_SNIPPETS: Dict[str, Dict[str, str]] = {
    "rolling_correlation": {
        "title": "🔥 Rolling Correlation Matrix (30D vs 90D)",
        "description": "Calcola la matrice di correlazione rolling a breve termine (30D) e a medio termine (90D) tra le posizioni in portafoglio e genera una Heatmap interattiva Plotly.",
        "category": "Market Microstructure & Correlation",
        "code": """# ARGUS BQuant Snippet: Rolling Correlation Matrix
import pandas as pd
import numpy as np
import plotly.express as px

print("📊 Calcolo Matrice di Correlazione Rolling (30D vs 90D)...")

if df_returns is not None and not df_returns.empty and df_returns.shape[1] >= 2:
    # Pulisci colonne e calcola correlazioni
    clean_rets = df_returns.select_dtypes(include=[np.number]).dropna(how="all")
    
    # Correlazione recente a 30 giorni
    corr_30d = clean_rets.iloc[-30:].corr()
    corr_90d = clean_rets.iloc[-90:].corr() if len(clean_rets) >= 90 else clean_rets.corr()
    
    # Delta tra correlazioni (Stress Indicator)
    corr_diff = corr_30d - corr_90d
    
    print(f"✅ Analizzati {len(clean_rets.columns)} asset su {len(clean_rets)} date storiche.")
    print("📈 Matrice Correlazione Recente (ultimi 30 giorni):\\n", corr_30d.round(3))
    
    # Genera Heatmap Plotly
    fig = px.imshow(
        corr_30d,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1.0, zmax=1.0,
        title="🔥 Matrice di Correlazione a 30 Giorni (Plotly BQuant)"
    )
    fig.update_layout(template="plotly_dark", height=450)
    
    # Esponi tabella per la visualizzazione UI
    df_out = corr_30d.reset_index().rename(columns={"index": "Ticker"})
else:
    print("⚠️ Dati rendimenti non disponibili o con meno di 2 asset.")
"""
    },
    
    "duckdb_sql": {
        "title": "🦆 DuckDB SQL Analytics on Portfolio & Prices",
        "description": "Esegue query analitiche SQL ad alta velocità su DataFrame in-memory (df_positions, df_tx, df_prices) con calcolo aggregato di pesi, controvalori e concentrazione HHI.",
        "category": "Database & SQL Querying",
        "code": """# ARGUS BQuant Snippet: DuckDB In-Memory SQL Query
import duckdb
import pandas as pd
import plotly.express as px

print("🦆 Connessione al database DuckDB in-memory ed esecuzione query SQL...")

# Registra i DataFrame pandas nella sessione DuckDB
con = duckdb.connect(database=":memory:")
con.register("df_positions", df_positions)
con.register("df_prices", df_prices)

# Rilevamento dinamico colonne disponibili
pos_cols = list(df_positions.columns)
sec_col = "gics_sector" if "gics_sector" in pos_cols else ("sector" if "sector" in pos_cols else ("asset_class" if "asset_class" in pos_cols else "ticker"))
pnl_col = "unrealized_pnl_pct" if "unrealized_pnl_pct" in pos_cols else "0"

# Query SQL analitica aggregata per settore / asset class
query = f\"\"\"
SELECT 
    COALESCE(CAST({sec_col} AS VARCHAR), 'Non Assegnato') AS Settore,
    COUNT(DISTINCT ticker) AS Num_Titoli,
    ROUND(SUM(current_value), 2) AS Valore_Totale_EUR,
    ROUND(SUM(weight_pct), 2) AS Peso_Totale_PCT,
    ROUND(AVG({pnl_col}), 2) AS PnL_Medio_PCT,
    ROUND(SUM(weight_pct * weight_pct), 2) AS Concentrazione_HHI_Settore
FROM df_positions
WHERE current_value > 0
GROUP BY 1
ORDER BY Valore_Totale_EUR DESC;
\"\"\"

df_out = con.execute(query).df()
print(f"✅ Query SQL eseguita con successo. Righe estratte: {len(df_out)}")
print(df_out.to_string(index=False))

# Genera grafico Treemap o Donut per i settori
if not df_out.empty:
    fig = px.pie(
        df_out, 
        names="Settore", 
        values="Valore_Totale_EUR", 
        title="🌐 Ripartizione Controvalore per Settore (Query DuckDB)",
        hole=0.45,
        template="plotly_dark"
    )
    fig.update_layout(height=420)
"""
    },

    "factor_ols_hedge": {
        "title": "📐 Custom OLS Factor Regression & Optimal Hedge Ratio",
        "description": "Esegue una regressione lineare multivariata tra il portafoglio e i fattori di mercato per stimare Alpha, Beta, Tracking Error e Hedge Ratio ottimale con derivati.",
        "category": "Quantitative Factor Models",
        "code": """# ARGUS BQuant Snippet: OLS Factor Regression & Hedge Ratio
import numpy as np
import pandas as pd
from scipy import stats
import plotly.graph_objects as go

print("📐 Esecuzione Regressione Lineare OLS su Rendimenti...")

if df_returns is not None and not df_returns.empty:
    port_ret = results.get("portfolio_return", pd.Series(dtype=float))
    bench_ret = results.get("benchmark_return", pd.Series(dtype=float))
    
    # Allinea serie storiche
    df_aligned = pd.concat([port_ret.rename("Portfolio"), bench_ret.rename("Benchmark")], axis=1).dropna()
    
    if len(df_aligned) >= 30:
        slope, intercept, r_val, p_val, std_err = stats.linregress(df_aligned["Benchmark"], df_aligned["Portfolio"])
        
        alpha_ann = intercept * 252 * 100
        beta = slope
        r_squared = r_val ** 2
        
        # Calcolo Optimal Hedge Ratio (Euro di Future per neutralizzare il Beta)
        tot_val = float(df_positions["current_value"].sum()) if "current_value" in df_positions.columns else 100000.0
        hedge_notional = tot_val * beta
        
        print(f"✅ Risultati Regressione OLS ({len(df_aligned)} osservazioni):")
        print(f"   • Beta di Mercato (&beta;):      {beta:.3f}")
        print(f"   • Alpha Annualizzato (&alpha;):   {alpha_ann:+.2f}%")
        print(f"   • R-Squared (R²):           {r_squared*100:.1f}%")
        print(f"   • p-value:                  {p_val:.4e}")
        print(f"   • Controvalore Hedge 100%:  € {hedge_notional:,.2f}")
        
        # Grafico Scatter con retta di regressione
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_aligned["Benchmark"] * 100, 
            y=df_aligned["Portfolio"] * 100,
            mode="markers",
            marker=dict(color="#58a6ff", size=6, opacity=0.6),
            name="Rendimenti Giornalieri (%)"
        ))
        
        # Retta OLS
        x_range = np.linspace(df_aligned["Benchmark"].min() * 100, df_aligned["Benchmark"].max() * 100, 100)
        y_ols = (intercept + slope * (x_range / 100)) * 100
        fig.add_trace(go.Scatter(
            x=x_range, y=y_ols,
            mode="lines",
            line=dict(color="#ff9900", width=2.5),
            name=f"Retta OLS (Beta = {beta:.2f}, R² = {r_squared:.2f})"
        ))
        
        fig.update_layout(
            title="🎯 Security Characteristic Line (SCL) — Portfolio vs Benchmark",
            xaxis_title="Rendimento Benchmark (%)",
            yaxis_title="Rendimento Portafoglio (%)",
            template="plotly_dark",
            height=450
        )
        
        df_out = pd.DataFrame([{
            "Parametro": "Beta (Pendenza)", "Valore": round(beta, 3)
        }, {
            "Parametro": "Alpha Annuo (%)", "Valore": f"{alpha_ann:+.2f}%"
        }, {
            "Parametro": "R-Squared", "Valore": f"{r_squared*100:.1f}%"
        }, {
            "Parametro": "Controvalore Hedge Notionale (€)", "Valore": f"€ {hedge_notional:,.2f}"
        }])
    else:
        print("⚠️ Storico sovrapposto insufficiente tra portafoglio e benchmark (< 30 giorni).")
"""
    },

    "drawdown_duration": {
        "title": "📉 Underwater & Drawdown Duration Analytics",
        "description": "Quantifica l'intensità e la durata temporale esatta dei periodi di perdita per ciascun asset in portafoglio, calcolando il tempo medio e massimo di recupero (Recovery Days).",
        "category": "Risk Management & Stress",
        "code": """# ARGUS BQuant Snippet: Drawdown & Underwater Analytics
import pandas as pd
import numpy as np
import plotly.graph_objects as go

print("📉 Analisi Durata e Profondità Drawdown per Asset...")

if df_returns is not None and not df_returns.empty:
    clean_rets = df_returns.select_dtypes(include=[np.number]).dropna(how="all")
    
    rows_dd = []
    fig = go.Figure()
    
    for col in clean_rets.columns[:8]: # Primi 8 asset
        sr = clean_rets[col].fillna(0.0)
        wealth = (1.0 + sr).cumprod()
        peak = wealth.cummax()
        dd = (wealth - peak) / peak
        
        max_dd = float(dd.min() * 100.0)
        curr_dd = float(dd.iloc[-1] * 100.0)
        
        # Giorni passati in stato di drawdown (dd < 0)
        in_dd_days = int((dd < -0.001).sum())
        pct_in_dd = float(in_dd_days / len(dd) * 100.0)
        
        rows_dd.append({
            "Ticker": col,
            "Max Drawdown (%)": round(max_dd, 2),
            "Drawdown Corrente (%)": round(curr_dd, 2),
            "Giorni in Drawdown": in_dd_days,
            "% Tempo Sotto il Picco": round(pct_in_dd, 1)
        })
        
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd * 100.0,
            mode="lines",
            name=col,
            line=dict(width=1.5)
        ))
        
    df_out = pd.DataFrame(rows_dd).sort_values("Max Drawdown (%)")
    print("📋 Tabella Riepilogativa Drawdown:\\n", df_out.to_string(index=False))
    
    fig.update_layout(
        title="🌊 Underwater Plot Multi-Asset (% di Perdita dal Picco Storico)",
        yaxis_title="Drawdown (%)",
        xaxis_title="Data",
        template="plotly_dark",
        height=450
    )
"""
    },

    "risk_parity_rebal": {
        "title": "⚖️ Dynamic Risk-Parity Rebalancing Simulation",
        "description": "Simula un ribilanciamento ad Inverse-Volatility Risk Parity, calcolando i pesi ottimali, il delta rispetto all'allocazione attuale, il turnover e i costi di transazione stimati.",
        "category": "Portfolio Construction & Optimization",
        "code": """# ARGUS BQuant Snippet: Risk Parity Allocation Simulation
import pandas as pd
import numpy as np
import plotly.graph_objects as go

print("⚖️ Simulazione Ribilanciamento a Parità di Rischio (Inverse Volatility)...")

if df_positions is not None and not df_positions.empty and df_returns is not None and not df_returns.empty:
    pos_active = df_positions[df_positions["current_value"] > 0].copy()
    tickers = [t for t in pos_active["ticker"].unique() if t in df_returns.columns]
    
    if len(tickers) >= 2:
        # Calcolo volatilità annua per asset
        vols = df_returns[tickers].std() * np.sqrt(252)
        inv_vols = 1.0 / vols.clip(lower=0.01)
        
        # Pesi Risk-Parity (1/Vol normalizzato)
        rp_weights = (inv_vols / inv_vols.sum()) * 100.0
        
        # Confronto con pesi attuali
        curr_weights = pos_active.set_index("ticker")["weight_pct"].reindex(tickers).fillna(0.0)
        tot_val = float(pos_active["current_value"].sum())
        
        df_comp = pd.DataFrame({
            "Ticker": tickers,
            "Volatilità Annua (%)": vols.round(2).values,
            "Peso Attuale (%)": curr_weights.round(2).values,
            "Peso Risk-Parity (%)": rp_weights.round(2).values,
        })
        df_comp["Delta Peso (%)"] = (df_comp["Peso Risk-Parity (%)"] - df_comp["Peso Attuale (%)"]).round(2)
        df_comp["Trade Reale (€)"] = ((df_comp["Delta Peso (%)"] / 100.0) * tot_val).round(2)
        
        turnover_pct = df_comp["Delta Peso (%)"].abs().sum() / 2.0
        
        print(f"✅ Ribilanciamento Calcolato su {len(tickers)} asset.")
        print(f"   • Turnover Totale Stimato: {turnover_pct:.2f}% (Controvalore: € {turnover_pct/100*tot_val:,.2f})")
        print(df_comp.to_string(index=False))
        
        # Grafico a Barre di Confronto
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_comp["Ticker"], y=df_comp["Peso Attuale (%)"], name="Peso Attuale", marker_color="#58a6ff"))
        fig.add_trace(go.Bar(x=df_comp["Ticker"], y=df_comp["Peso Risk-Parity (%)"], name="Peso Risk-Parity", marker_color="#3fb950"))
        fig.update_layout(
            barmode="group",
            title="⚖️ Confronto Allocazione: Pesi Attuali vs Target Risk-Parity",
            yaxis_title="Allocazione (%)",
            template="plotly_dark",
            height=430
        )
        df_out = df_comp
"""
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. In-Memory Execution Engine & Sandbox
# ─────────────────────────────────────────────────────────────────────────────

def execute_bquant_script(
    script_code: str,
    context_bundle: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Esegue uno script Python analitico in-memory catturando output stdout/stderr,
    figure Plotly/Matplotlib, DataFrame pandas e variabili create.
    """
    t_start = time.perf_counter()
    
    # Preparazione del context bundle
    ctx = context_bundle or {}
    results_obj = ctx.get("results", {})
    df_positions = ctx.get("df_positions", results_obj.get("positions", pd.DataFrame()))
    df_prices = ctx.get("df_prices", results_obj.get("df_prices", pd.DataFrame()))
    df_returns = ctx.get("df_returns", results_obj.get("returns", pd.DataFrame()))
    df_tx = ctx.get("df_tx", results_obj.get("df_tx", pd.DataFrame()))
    portfolio_name = ctx.get("portfolio_name", results_obj.get("portfolio_name", "Portfolio"))
    portfolio_return = ctx.get("portfolio_return", results_obj.get("portfolio_return", pd.Series(dtype=float)))
    benchmark_return = ctx.get("benchmark_return", results_obj.get("benchmark_return", pd.Series(dtype=float)))
    benchmark_ticker = ctx.get("benchmark_ticker", results_obj.get("benchmark_ticker", "SPY"))
    base_currency = ctx.get("base_currency", results_obj.get("base_currency", "EUR"))
    portfolio_value = float(df_positions["current_value"].sum()) if (df_positions is not None and isinstance(df_positions, pd.DataFrame) and not df_positions.empty and "current_value" in df_positions.columns) else 0.0
    
    # Configurazione del Namespace di esecuzione
    namespace = {
        "__name__": "__bquant__",
        "pd": pd,
        "np": np,
        "scipy": scipy,
        "stats": stats,
        "px": px,
        "go": go,
        "plt": plt,
        "duckdb": duckdb,
        "results": results_obj,
        "df_positions": df_positions,
        "df_prices": df_prices,
        "df_returns": df_returns,
        "df_tx": df_tx,
        "portfolio_name": portfolio_name,
        "portfolio_return": portfolio_return,
        "portfolio_returns": portfolio_return,
        "benchmark_return": benchmark_return,
        "benchmark_returns": benchmark_return,
        "benchmark_ticker": benchmark_ticker,
        "base_currency": base_currency,
        "portfolio_value": portfolio_value,
        "df_out": None,
        "fig": None
    }
    
    # Cattura stdout e stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    success = False
    error_msg = None
    output_df = None
    output_fig = None
    
    try:
        # Reset stato matplotlib se disponibile
        if HAS_MATPLOTLIB and plt is not None:
            plt.close("all")
        
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(script_code, namespace)
            
        success = True
        
        # Rileva DataFrame in output
        if namespace.get("df_out") is not None and isinstance(namespace.get("df_out"), pd.DataFrame):
            output_df = namespace["df_out"]
        elif namespace.get("df_result") is not None and isinstance(namespace.get("df_result"), pd.DataFrame):
            output_df = namespace["df_result"]
            
        # Rileva Figure Plotly in output
        if namespace.get("fig") is not None and (isinstance(namespace.get("fig"), go.Figure) or hasattr(namespace.get("fig"), "to_dict")):
            output_fig = namespace["fig"]
        elif namespace.get("figure") is not None and isinstance(namespace.get("figure"), go.Figure):
            output_fig = namespace["figure"]
            
        # Se non c'è una figura Plotly ma c'è una figura Matplotlib attiva
        if output_fig is None and HAS_MATPLOTLIB and plt is not None and plt.get_fignums():
            output_fig = plt.gcf()
            
    except Exception as e:
        success = False
        error_msg = f"{type(e).__name__}: {str(e)}\\n\\n{traceback.format_exc()}"
        
    t_elapsed = time.perf_counter() - t_start
    stdout_text = stdout_capture.getvalue()
    stderr_text = stderr_capture.getvalue()
    
    return {
        "success": success,
        "execution_time_sec": round(t_elapsed, 4),
        "stdout": stdout_text,
        "stderr": stderr_text,
        "error": error_msg,
        "output_df": output_df,
        "output_fig": output_fig,
        "variables_created": [k for k in namespace.keys() if k not in [
            "__name__", "pd", "np", "scipy", "stats", "px", "go", "plt", "duckdb", 
            "results", "df_positions", "df_prices", "df_returns", "df_tx"
        ]]
    }
