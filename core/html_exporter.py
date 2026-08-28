# ============================================================
# core/html_exporter.py
# ARGUS — Risk Analytics Platform
# Generator of Standalone Interactive HTML Portfolio Factsheets
# ============================================================

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

def generate_interactive_html_report(results: Dict[str, Any], output_path: str = None) -> str:
    """
    Generates a high-tech standalone HTML executive factsheet with embedded 
    interactive Plotly charts, metric cards, and positions table.
    """
    metrics = results.get("metrics", {}) if isinstance(results, dict) else {}
    m_risk = metrics.get("market_risk", {}) if isinstance(metrics, dict) else {}
    returns = metrics.get("returns", {}) if isinstance(metrics, dict) else {}
    pos = results.get("positions", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    
    calc_date = results.get("computed_at", datetime.now().strftime("%Y-%m-%d %H:%M")) if isinstance(results, dict) else datetime.now().strftime("%Y-%m-%d %H:%M")
    port_return = results.get("portfolio_return", pd.Series(dtype=float)) if isinstance(results, dict) else pd.Series(dtype=float)
    
    # 1. Plotly Performance Chart
    chart_perf_html = "<div>Nessun dato di performance disponibile</div>"
    try:
        fig_perf = go.Figure()
        if isinstance(port_return, pd.Series) and not port_return.empty:
            cum_ret = (1 + port_return.fillna(0)).cumprod() - 1
            x_dates = [str(d)[:10] for d in cum_ret.index]
            fig_perf.add_trace(go.Scatter(
                x=x_dates, 
                y=(cum_ret.values * 100).tolist(), 
                mode='lines', 
                name='Portafoglio ARGUS',
                line=dict(color='#00f3ff', width=2.5)
            ))
        
        benchmark_return = results.get("benchmark_return", pd.Series(dtype=float)) if isinstance(results, dict) else pd.Series(dtype=float)
        if isinstance(benchmark_return, pd.Series) and not benchmark_return.empty:
            cum_bm = (1 + benchmark_return.fillna(0)).cumprod() - 1
            x_bm_dates = [str(d)[:10] for d in cum_bm.index]
            fig_perf.add_trace(go.Scatter(
                x=x_bm_dates, 
                y=(cum_bm.values * 100).tolist(), 
                mode='lines', 
                name='Benchmark (SPY)',
                line=dict(color='#8b949e', width=1.5, dash='dash')
            ))
            
        fig_perf.update_layout(
            title="Evoluzione Cumulativa Portafoglio vs Benchmark (%)",
            template="plotly_dark",
            paper_bgcolor='rgba(13, 17, 23, 0.8)',
            plot_bgcolor='rgba(13, 17, 23, 0.8)',
            margin=dict(l=40, r=40, t=50, b=40),
            height=380
        )
        chart_perf_html = fig_perf.to_html(full_html=False, include_plotlyjs='cdn')
    except Exception:
        pass

    # 2. Allocation Donut Chart
    chart_alloc_html = "<div>Nessuna posizione attiva disponibile</div>"
    try:
        fig_alloc = go.Figure()
        if isinstance(pos, pd.DataFrame) and not pos.empty:
            val_col = "current_value" if "current_value" in pos.columns else ("market_value" if "market_value" in pos.columns else None)
            if val_col:
                active_pos = pos[(pos.get("qty_net", 1) > 1e-6) & (pos[val_col] > 0)]
                if not active_pos.empty:
                    fig_alloc.add_trace(go.Pie(
                        labels=[str(t) for t in active_pos["ticker"]], 
                        values=active_pos[val_col].tolist(),
                        hole=0.4,
                        textinfo='label+percent'
                    ))
        fig_alloc.update_layout(
            title="Ripartizione Asset per Valore di Mercato",
            template="plotly_dark",
            paper_bgcolor='rgba(13, 17, 23, 0.8)',
            plot_bgcolor='rgba(13, 17, 23, 0.8)',
            margin=dict(l=40, r=40, t=50, b=40),
            height=380
        )
        chart_alloc_html = fig_alloc.to_html(full_html=False, include_plotlyjs=False)
    except Exception:
        pass

    # 3. Position Rows HTML Table
    table_rows = ""
    if isinstance(pos, pd.DataFrame) and not pos.empty:
        val_col = "current_value" if "current_value" in pos.columns else ("market_value" if "market_value" in pos.columns else None)
        active_pos = pos[(pos.get("qty_net", 1) > 1e-6) & (pos[val_col] > 0)] if val_col else pos[pos.get("qty_net", 1) > 1e-6]
        for idx, row in active_pos.iterrows():
            ticker = str(row.get("ticker", "N/A"))
            ac = str(row.get("asset_class", "N/A"))
            
            mv_raw = row.get("current_value", row.get("market_value", 0.0))
            mv = float(mv_raw) if mv_raw is not None and not pd.isna(mv_raw) else 0.0
            
            w_raw = row.get("weight_pct", 0.0)
            weight = float(w_raw) if w_raw is not None and not pd.isna(w_raw) else 0.0
            
            pnl_raw = row.get("unrealized_pnl", 0.0)
            pnl = float(pnl_raw) if pnl_raw is not None and not pd.isna(pnl_raw) else 0.0
            
            pnl_color = "#00e676" if pnl >= 0 else "#ff5252"
            
            table_rows += f"""
            <tr>
                <td style="font-weight: 600; color: #ffffff;">{ticker}</td>
                <td><span style="background: rgba(255,255,255,0.08); padding: 3px 8px; border-radius: 12px; font-size: 12px;">{ac}</span></td>
                <td>€ {mv:,.2f}</td>
                <td>{weight:.2f}%</td>
                <td style="color: {pnl_color}; font-weight: 600;">€ {pnl:+,.2f}</td>
            </tr>
            """

    tot_val = float(pos["current_value"].sum()) if isinstance(pos, pd.DataFrame) and not pos.empty and "current_value" in pos.columns else (float(pos["market_value"].sum()) if isinstance(pos, pd.DataFrame) and not pos.empty and "market_value" in pos.columns else 0.0)
    
    sharpe_raw = returns.get("sharpe_ratio", returns.get("sharpe", 0.0))
    sharpe = float(sharpe_raw) if sharpe_raw is not None and not pd.isna(sharpe_raw) else 0.0

    var95_raw = m_risk.get("var_95_param", m_risk.get("var_95_hist", 0.0))
    var95 = float(var95_raw) if var95_raw is not None and not pd.isna(var95_raw) else 0.0
    if abs(var95) > 5.0:
        var95 = var95 / 100.0

    cagr_raw = returns.get("cagr", returns.get("cagr_pct", returns.get("portfolio_cagr_pct", 0.0)))
    cagr = float(cagr_raw) if cagr_raw is not None and not pd.isna(cagr_raw) else 0.0
    if abs(cagr) > 5.0:
        cagr = cagr / 100.0

    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARGUS Factsheet | Portfolio Executive Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background-color: #090d16;
            color: #e6edf3;
            margin: 0;
            padding: 30px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .brand {{
            font-size: 28px;
            font-weight: 700;
            color: #00f3ff;
            letter-spacing: 1px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: rgba(22, 27, 34, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .kpi-title {{
            font-size: 12px;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            margin-top: 8px;
            color: #ffffff;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        @media (max-width: 900px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}
        .table-container {{
            background: rgba(22, 27, 34, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        th {{
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 12px;
            color: #8b949e;
            font-size: 13px;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="brand">👁️ ARGUS — Risk Analytics Platform</div>
            <div style="color: #8b949e; margin-top: 5px;">Executive Factsheet | Generato il {calc_date}</div>
        </div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Valore di Portafoglio</div>
            <div class="kpi-value">€ {tot_val:,.2f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">CAGR (Rendimento Annuo)</div>
            <div class="kpi-value" style="color: {'#00e676' if cagr>=0 else '#ff5252'};">{cagr*100:+.2f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Sharpe Ratio</div>
            <div class="kpi-value" style="color: #00f3ff;">{sharpe:.2f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Value at Risk (VaR 95%)</div>
            <div class="kpi-value" style="color: #ffab40;">{var95*100:.2f}%</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="kpi-card">{chart_perf_html}</div>
        <div class="kpi-card">{chart_alloc_html}</div>
    </div>

    <div class="table-container">
        <h3 style="margin-top: 0; color: #ffffff;">Composizione & Posizioni Attive</h3>
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Asset Class</th>
                    <th>Valore Mercato</th>
                    <th>Peso %</th>
                    <th>PnL Non Realizzato</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
    return html_content


def generate_html_report_bytes(results: Dict[str, Any]) -> bytes:
    """Returns HTML report content as encoded bytes ready for Streamlit download_button."""
    try:
        content = generate_interactive_html_report(results)
        if isinstance(content, bytes):
            return content
        return str(content).encode("utf-8")
    except Exception as e:
        err_html = f"<html><body><h3>Errore durante la generazione del report HTML: {e}</h3></body></html>"
        return err_html.encode("utf-8")
