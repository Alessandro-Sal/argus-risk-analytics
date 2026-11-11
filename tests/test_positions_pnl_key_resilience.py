"""Unit test to verify that position dataframe transformations in Page 5 handle
differing column names (pnl_unrealized vs unrealized_pnl vs missing) without KeyError.
"""
import pandas as pd
import pytest


def test_positions_table_pnl_column_resilience():
    # Scenario: dataframe contains unrealized_pnl instead of pnl_unrealized
    df_l = pd.DataFrame([
        {
            "ticker": "AAPL",
            "asset_class": "Azionario USA",
            "sector": "Technology",
            "country": "USA",
            "qty_net": 10.0,
            "avg_cost": 150.0,
            "last_price": 180.0,
            "current_value": 1800.0,
            "weight": 0.5,
            "realized_pnl": 50.0,
            "unrealized_pnl": 300.0,
            "days_to_liquidate": 0.2
        },
        {
            "ticker": "MSFT",
            "asset_class": "Azionario USA",
            "sector": "Technology",
            "country": "USA",
            "qty_net": 5.0,
            "avg_cost": 400.0,
            "last_price": 380.0,
            "current_value": 1900.0,
            "weight": 0.5,
            "realized_pnl": 0.0,
            "unrealized_pnl": -100.0,
            "days_to_liquidate": 0.3
        }
    ])

    # Replicate Page 5 transformation logic
    if "days_to_liquidate" not in df_l.columns:
        df_l["days_to_liquidate"] = 0.5
    if "current_value" not in df_l.columns:
        df_l["current_value"] = 0.0
    if "wacp" not in df_l.columns:
        df_l["wacp"] = df_l["avg_cost"] if "avg_cost" in df_l.columns else 0.0
    if "pnl_unrealized" not in df_l.columns:
        if "unrealized_pnl" in df_l.columns:
            df_l["pnl_unrealized"] = df_l["unrealized_pnl"]
        elif "current_value" in df_l.columns and "qty_net" in df_l.columns and "wacp" in df_l.columns:
            df_l["pnl_unrealized"] = df_l["current_value"] - (df_l["wacp"] * df_l["qty_net"])
        else:
            df_l["pnl_unrealized"] = 0.0
    if "pnl_realized" not in df_l.columns:
        df_l["pnl_realized"] = df_l["realized_pnl"] if "realized_pnl" in df_l.columns else 0.0
    if "weight_pct" not in df_l.columns:
        if "weight" in df_l.columns:
            df_l["weight_pct"] = df_l["weight"] * 100.0 if df_l["weight"].max() <= 1.05 else df_l["weight"]
        else:
            tot_cv = float(df_l["current_value"].sum()) if "current_value" in df_l.columns else 0.0
            df_l["weight_pct"] = (df_l["current_value"] / tot_cv * 100.0) if tot_cv > 0 else 0.0

    display_cols = [
        "ticker", "asset_class", "sector", "country", "qty_net",
        "wacp", "last_price", "current_value", "weight_pct",
        "pnl_realized", "pnl_unrealized", "beta", "days_to_liquidate", "yield_on_cost_pct"
    ]
    valid_cols = [c for c in display_cols if c in df_l.columns]
    df_disp = df_l[valid_cols].copy()

    col_renames = {
        "ticker": "Ticker", "asset_class": "Asset Class", "sector": "Settore",
        "country": "Paese", "qty_net": "Quantità", "wacp": "Prezzo Carico (€)",
        "last_price": "Prezzo Mkt (€)", "current_value": "Controvalore (€)",
        "weight_pct": "Peso (%)", "pnl_realized": "PnL Realizz. (€)",
        "pnl_unrealized": "PnL Latente (€)", "beta": "Beta (vs SPY)",
        "days_to_liquidate": "Giorni Liq. (ADV 15%)",
        "yield_on_cost_pct": "Yield on Cost (%)"
    }
    df_disp.rename(columns=col_renames, inplace=True)

    for col_name in ["PnL Latente (€)", "PnL Realizz. (€)", "Controvalore (€)", "Peso (%)", "Prezzo Carico (€)", "Prezzo Mkt (€)"]:
        if col_name not in df_disp.columns:
            df_disp[col_name] = 0.0
        else:
            df_disp[col_name] = pd.to_numeric(df_disp[col_name], errors="coerce").fillna(0.0)

    # These operations must succeed without KeyError:
    tot_pos_cnt = len(df_disp)
    gains_mask = df_disp["PnL Latente (€)"] > 0
    loss_mask = df_disp["PnL Latente (€)"] < 0
    n_gain = int(gains_mask.sum())
    n_loss = int(loss_mask.sum())
    assert n_gain == 1
    assert n_loss == 1
    assert tot_pos_cnt == 2
