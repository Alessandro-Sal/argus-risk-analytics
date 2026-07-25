"""
ARGUS — Risk Analytics Platform
Script: Star Schema Data Exporter for Power BI & Looker Studio (In-Memory ZIP Package)
"""

import os
import io
import zipfile
import pandas as pd
from typing import Dict, Any

def generate_star_schema_zip(results: Dict[str, Any]) -> bytes:
    """
    Generates an in-memory ZIP package containing all 3 Star Schema CSV tables:
      1. dim_assets.csv
      2. fact_positions.csv
      3. fact_portfolio_summary.csv
      4. README_POWERBI.md
    """
    pos = results.get("positions", pd.DataFrame())
    m = results.get("metrics", {})
    ret = m.get("returns", {})
    mk = m.get("market_risk", {})

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Dimension Assets Table
        if not pos.empty:
            dim_assets = pos[[
                "ticker", "asset_class", "country", "currency"
            ]].copy() if "country" in pos.columns else pos[["ticker", "asset_class", "currency"]].copy()
            
            sec_col = "sector" if "sector" in pos.columns else ("gics_sector" if "gics_sector" in pos.columns else None)
            if sec_col:
                dim_assets["sector"] = pos[sec_col]
            else:
                dim_assets["sector"] = "Technology"
                
            dim_assets = dim_assets.drop_duplicates(subset=["ticker"])
            zf.writestr("dim_assets.csv", dim_assets.to_csv(index=False))

            # 2. Fact Positions Table
            cols_fact = [c for c in [
                "ticker", "qty_net", "avg_cost", "last_price", "current_value",
                "cost_basis", "unrealized_pnl", "unrealized_pnl_pct", "realized_pnl", "dividends_total", "weight_pct"
            ] if c in pos.columns]
            fact_pos = pos[cols_fact].copy()
            zf.writestr("fact_positions.csv", fact_pos.to_csv(index=False))

        # 3. Fact Portfolio Summary Table
        df_summary = pd.DataFrame([{
            "portfolio_value_eur": ret.get("portfolio_value", 0.0),
            "cagr_pct": ret.get("cagr_pct", 0.0),
            "total_return_pct": ret.get("total_return_pct", 0.0),
            "sharpe_ratio": ret.get("sharpe_ratio", 0.0),
            "sortino_ratio": ret.get("sortino_ratio", 0.0),
            "calmar_ratio": ret.get("calmar_ratio", 0.0),
            "max_drawdown_pct": mk.get("max_drawdown_pct", 0.0),
            "var_95_pct": mk.get("var_95", 0.0) * 100.0 if mk.get("var_95") else 0.0,
            "beta": mk.get("beta", 1.0)
        }])
        zf.writestr("fact_portfolio_summary.csv", df_summary.to_csv(index=False))

        # 4. Power BI Import Instructions
        readme_txt = """# ARGUS — Power BI Star Schema Import Guide

1. Open Microsoft Power BI Desktop.
2. Click 'Get Data' -> 'Text/CSV'.
3. Import `dim_assets.csv`, `fact_positions.csv`, and `fact_portfolio_summary.csv`.
4. Create relationship: `dim_assets[ticker]` 1 <---> * `fact_positions[ticker]`.
5. Enjoy your institutional Power BI Risk Dashboard!
"""
        zf.writestr("README_POWERBI.md", readme_txt)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def export_star_schema_tables(
    results: Dict[str, Any],
    output_dir: str = "exports/powerbi"
) -> Dict[str, str]:
    """Saves Star Schema CSV files to disk."""
    os.makedirs(output_dir, exist_ok=True)
    zip_bytes = generate_star_schema_zip(results)
    
    pos = results.get("positions", pd.DataFrame())
    exported_files = {}
    if not pos.empty:
        p1 = os.path.join(output_dir, "dim_assets.csv")
        p2 = os.path.join(output_dir, "fact_positions.csv")
        p3 = os.path.join(output_dir, "fact_portfolio_summary.csv")
        
        pos[["ticker", "asset_class", "currency"]].drop_duplicates().to_csv(p1, index=False)
        pos.to_csv(p2, index=False)
        exported_files = {"dim_assets": p1, "fact_positions": p2}
        
    return exported_files
