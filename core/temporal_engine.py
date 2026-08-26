"""
core/temporal_engine.py - Motore di Analisi Temporale, Rolling Risk & Performance Matrix
Modulo quantitativo per l'elaborazione di serie storiche, matrici mensili/annuali di rendimento,
curva underwater di drawdown con ranking degli episodi critici, metriche rolling e stagionalità.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


def compute_monthly_return_matrix(sr_returns: pd.Series) -> pd.DataFrame:
    """
    Calcola la matrice dei rendimenti mensili (Gennaio..Dicembre) e il rendimento cumulato annuo (YTD)
    per ciascun anno solare registrato nella serie storica.
    """
    if sr_returns is None or sr_returns.empty:
        return pd.DataFrame()
        
    s = sr_returns.copy().dropna()
    if getattr(s.index, 'tz', None) is not None:
        s.index = s.index.tz_localize(None)
    s.index = pd.to_datetime(s.index)

    if len(s) < 5:
        return pd.DataFrame()

    # Rendimento geometrico per mese: prod(1 + r) - 1
    monthly_ret = (1.0 + s).groupby([s.index.year, s.index.month]).prod() - 1.0
    monthly_ret.index.names = ["Year", "Month"]
    
    month_names = {
        1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu", 
        7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
    }
    
    df_matrix = monthly_ret.unstack(level="Month")
    df_matrix.columns = [month_names.get(m, str(m)) for m in df_matrix.columns]
    
    # Assicura la presenza di tutte le 12 colonne
    for m_name in month_names.values():
        if m_name not in df_matrix.columns:
            df_matrix[m_name] = np.nan
    df_matrix = df_matrix[list(month_names.values())]

    # Rendimento totale YTD per ciascun anno solare
    yearly_ret = (1.0 + s).groupby(s.index.year).prod() - 1.0
    df_matrix["YTD"] = yearly_ret

    return df_matrix.sort_index(ascending=False)


def compute_rolling_risk_metrics(
    sr_port: pd.Series, 
    sr_bm: Optional[pd.Series] = None, 
    window: int = 60, 
    rf_rate: float = 0.035
) -> pd.DataFrame:
    """
    Calcola l'evoluzione temporale a finestra mobile (rolling) di rendimenti,
    volatilità annualizzata, Sharpe ratio, Beta, correlazione e Tracking Error.
    """
    if sr_port is None or len(sr_port.dropna()) < max(15, window // 2):
        return pd.DataFrame()
    
    p = sr_port.copy().dropna()
    p.index = pd.to_datetime(p.index)
    if getattr(p.index, 'tz', None) is not None:
        p.index = p.index.tz_localize(None)

    min_periods = max(10, window // 3)
    df_out = pd.DataFrame(index=p.index)
    
    daily_rf = (1.0 + rf_rate) ** (1.0 / 252.0) - 1.0
    roll_mean = p.rolling(window, min_periods=min_periods).mean() * 252.0
    roll_vol = p.rolling(window, min_periods=min_periods).std() * np.sqrt(252.0)
    roll_excess = (p - daily_rf).rolling(window, min_periods=min_periods).mean() * 252.0
    roll_sharpe = roll_excess / roll_vol.replace(0, np.nan)
    
    df_out["Rolling_Return_Ann"] = roll_mean * 100.0
    df_out["Rolling_Vol_Ann"] = roll_vol * 100.0
    df_out["Rolling_Sharpe"] = roll_sharpe

    if sr_bm is not None and not sr_bm.empty:
        bm = sr_bm.copy().dropna()
        if getattr(bm.index, 'tz', None) is not None:
            bm.index = bm.index.tz_localize(None)
        bm = bm.reindex(p.index).fillna(0.0)
        
        roll_cov = p.rolling(window, min_periods=min_periods).cov(bm) * 252.0
        roll_bm_var = (bm.rolling(window, min_periods=min_periods).var() * 252.0).replace(0, np.nan)
        roll_beta = roll_cov / roll_bm_var
        roll_corr = p.rolling(window, min_periods=min_periods).corr(bm)
        
        diff = p - bm
        roll_te = diff.rolling(window, min_periods=min_periods).std() * np.sqrt(252.0) * 100.0
        
        df_out["Rolling_Beta"] = roll_beta
        df_out["Rolling_Correlation"] = roll_corr
        df_out["Rolling_Tracking_Error"] = roll_te

    return df_out.dropna(subset=["Rolling_Vol_Ann"])


def compute_underwater_drawdowns(sr_port: pd.Series) -> Dict[str, Any]:
    """
    Costruisce la curva Underwater, l'High-Water-Mark (HWM), l'Ulcer Index e 
    identifica analiticamente i Top episodi di drawdown storico con data di picco, 
    minimo, data di ripresa (recovery) e durata complessiva.
    """
    if sr_port is None or sr_port.empty:
        return {
            "cumulative_nav": pd.Series(dtype=float),
            "hwm": pd.Series(dtype=float),
            "drawdown_series": pd.Series(dtype=float),
            "max_drawdown_pct": 0.0,
            "ulcer_index": 0.0,
            "top_episodes": pd.DataFrame()
        }
        
    p = sr_port.copy().dropna()
    p.index = pd.to_datetime(p.index)
    if getattr(p.index, 'tz', None) is not None:
        p.index = p.index.tz_localize(None)

    cum = (1.0 + p).cumprod()
    hwm = cum.cummax()
    dd = (cum - hwm) / hwm
    
    # Identificazione Top 5 Drawdown Episodes
    episodes = []
    in_drawdown = False
    start_date = None
    trough_date = None
    trough_val = 0.0

    for dt, val in dd.items():
        if val < -0.0001:
            if not in_drawdown:
                in_drawdown = True
                start_date = dt
                trough_date = dt
                trough_val = val
            else:
                if val < trough_val:
                    trough_val = val
                    trough_date = dt
        else:
            if in_drawdown:
                recovery_date = dt
                episodes.append({
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "trough_date": trough_date.strftime("%Y-%m-%d"),
                    "recovery_date": recovery_date.strftime("%Y-%m-%d"),
                    "max_drawdown_pct": round(abs(float(trough_val)) * 100.0, 2),
                    "days_to_trough": max(1, (trough_date - start_date).days),
                    "recovery_days": max(1, (recovery_date - trough_date).days),
                    "total_days": max(1, (recovery_date - start_date).days),
                    "status": "Recuperato"
                })
                in_drawdown = False

    if in_drawdown and start_date is not None:
        episodes.append({
            "start_date": start_date.strftime("%Y-%m-%d"),
            "trough_date": trough_date.strftime("%Y-%m-%d") if trough_date else start_date.strftime("%Y-%m-%d"),
            "recovery_date": "In corso",
            "max_drawdown_pct": round(abs(float(trough_val)) * 100.0, 2),
            "days_to_trough": max(1, (trough_date - start_date).days) if trough_date else 1,
            "recovery_days": np.nan,
            "total_days": max(1, (dd.index[-1] - start_date).days),
            "status": "Attivo (In corso)"
        })

    df_ep = pd.DataFrame(episodes)
    if not df_ep.empty:
        df_ep = df_ep.sort_values(by="max_drawdown_pct", ascending=False).head(5).reset_index(drop=True)

    return {
        "cumulative_nav": cum,
        "hwm": hwm,
        "drawdown_series": dd * 100.0,
        "max_drawdown_pct": abs(float(dd.min())) * 100.0 if not dd.empty else 0.0,
        "ulcer_index": float(np.sqrt(np.mean((dd * 100.0) ** 2))) if not dd.empty else 0.0,
        "top_episodes": df_ep
    }


def compute_seasonality_patterns(sr_port: pd.Series) -> Dict[str, pd.DataFrame]:
    """
    Estrae le statistiche di stagionalità per giorno della settimana (Lunedì-Venerdì)
    e per mese dell'anno (Gennaio-Dicembre).
    """
    if sr_port is None or sr_port.empty:
        return {"day_stats": pd.DataFrame(), "month_stats": pd.DataFrame()}
        
    p = sr_port.copy().dropna()
    p.index = pd.to_datetime(p.index)
    if getattr(p.index, 'tz', None) is not None:
        p.index = p.index.tz_localize(None)

    # 1. Per Giorno della Settimana
    days_map = {0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì", 4: "Venerdì"}
    df_days = pd.DataFrame({"return": p, "day_idx": p.index.dayofweek})
    df_days = df_days[df_days["day_idx"].isin(days_map.keys())]
    df_days["day_name"] = df_days["day_idx"].map(days_map)
    
    day_stats = df_days.groupby("day_name")["return"].agg(
        Mean_Pct=lambda x: float(x.mean() * 100.0),
        Win_Rate=lambda x: float((x > 0).mean() * 100.0),
        Vol_Ann=lambda x: float(x.std() * np.sqrt(252) * 100.0) if len(x) > 1 else 0.0,
        Count="count"
    ).reindex(["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]).reset_index()

    # 2. Per Mese dell'Anno
    months_map = {
        1: "Gen", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mag", 6: "Giu", 
        7: "Lug", 8: "Ago", 9: "Set", 10: "Ott", 11: "Nov", 12: "Dic"
    }
    df_months = pd.DataFrame({"return": p, "month_idx": p.index.month})
    df_months["month_name"] = df_months["month_idx"].map(months_map)

    month_stats = df_months.groupby("month_name")["return"].agg(
        Mean_Pct=lambda x: float(((1.0 + x).prod() ** (21.0 / max(1, len(x))) - 1.0) * 100.0) if len(x) > 0 else 0.0,
        Win_Rate=lambda x: float((x > 0).mean() * 100.0),
        Count="count"
    ).reindex(list(months_map.values())).reset_index()

    return {
        "day_stats": day_stats,
        "month_stats": month_stats
    }


def compute_side_by_side_comparison(df_a: pd.DataFrame, df_b: pd.DataFrame) -> Dict[str, Any]:
    """
    Esegue il confronto analitico approfondito tra due insiemi di posizioni/snapshot.
    Calcola delta quantità, delta controvalore, delta peso di allocazione,
    turnover ratio di ribilanciamento e classifica gli status (nuovo ingresso, chiusura, incremento, riduzione).
    """
    if (df_a is None or df_a.empty) and (df_b is None or df_b.empty):
        return {
            "df_merged": pd.DataFrame(),
            "tot_val_a": 0.0,
            "tot_val_b": 0.0,
            "delta_nav": 0.0,
            "delta_nav_pct": 0.0,
            "turnover_pct": 0.0,
            "capital_rebalanced": 0.0,
            "new_entries_count": 0,
            "closed_entries_count": 0,
            "modified_count": 0
        }

    cols_a = [c for c in ["ticker", "asset_class", "qty_net", "avg_cost", "last_price", "current_value", "weight_pct"] if df_a is not None and c in df_a.columns]
    cols_b = [c for c in ["ticker", "asset_class", "qty_net", "avg_cost", "last_price", "current_value", "weight_pct"] if df_b is not None and c in df_b.columns]
    
    merged = pd.merge(
        df_a[cols_a] if (df_a is not None and not df_a.empty) else pd.DataFrame(columns=["ticker"]),
        df_b[cols_b] if (df_b is not None and not df_b.empty) else pd.DataFrame(columns=["ticker"]),
        on="ticker", how="outer", suffixes=("_A", "_B")
    ).fillna(0.0)

    if merged.empty:
        return {
            "df_merged": pd.DataFrame(),
            "tot_val_a": 0.0,
            "tot_val_b": 0.0,
            "delta_nav": 0.0,
            "delta_nav_pct": 0.0,
            "turnover_pct": 0.0,
            "capital_rebalanced": 0.0,
            "new_entries_count": 0,
            "closed_entries_count": 0,
            "modified_count": 0
        }

    # Class reconciliation
    if "asset_class_A" in merged.columns and "asset_class_B" in merged.columns:
        merged["asset_class"] = merged["asset_class_A"].where(merged["asset_class_A"] != 0, merged["asset_class_B"])
        merged["asset_class"] = merged["asset_class"].replace(0, "Stock")
    elif "asset_class_A" in merged.columns:
        merged["asset_class"] = merged["asset_class_A"]
    else:
        merged["asset_class"] = "Stock"

    merged["delta_qty"] = merged.get("qty_net_A", 0.0) - merged.get("qty_net_B", 0.0)
    merged["delta_price"] = merged.get("last_price_A", 0.0) - merged.get("last_price_B", 0.0)
    merged["delta_val"] = merged.get("current_value_A", 0.0) - merged.get("current_value_B", 0.0)
    merged["delta_weight"] = merged.get("weight_pct_A", 0.0) - merged.get("weight_pct_B", 0.0)

    # Accurate status categorization distinguishing trading activity vs organic price movements
    def get_status(row):
        q_a = float(row.get("qty_net_A", 0.0))
        q_b = float(row.get("qty_net_B", 0.0))
        d_q = float(row.get("delta_qty", 0.0))
        d_val = float(row.get("delta_val", 0.0))
        
        if q_b <= 0.0001 and q_a > 0.0001:
            return "🟢 Nuovo Ingresso"
        elif q_a <= 0.0001 and q_b > 0.0001:
            return "🔴 Chiusura Totale"
        elif d_q > 0.0001:
            return "⬆️ Acquisto Quote (+Qty)"
        elif d_q < -0.0001:
            return "⬇️ Vendita Quote (-Qty)"
        elif d_val > 1.0:
            return "📈 Apprezzamento (Prezzo +)"
        elif d_val < -1.0:
            return "📉 Deprezzamento (Prezzo -)"
        return "⚪ Invariato"

    merged["status"] = merged.apply(get_status, axis=1)

    # Portfolio Turnover ratio: 0.5 * sum(|w_A - w_B|)
    # Since weight_pct is in [0, 100], sum(|delta_weight|) is in [0, 200]
    # turnover_pct = 0.5 * sum(|delta_weight|) is between 0% and 100%
    turnover_pct = 0.5 * float(merged["delta_weight"].abs().sum())
    
    # Trading Capital Rebalanced (sum of absolute quantity changes times estimated price):
    trading_capital = float((merged["delta_qty"].abs() * merged.apply(lambda r: (float(r.get("current_value_A", 0)) / max(0.0001, float(r.get("qty_net_A", 1)))) if float(r.get("qty_net_A", 0)) > 0 else (float(r.get("current_value_B", 0)) / max(0.0001, float(r.get("qty_net_B", 1)))), axis=1)).sum())
    
    tot_val_a = float(df_a["current_value"].sum()) if (df_a is not None and not df_a.empty and "current_value" in df_a.columns) else 0.0
    tot_val_b = float(df_b["current_value"].sum()) if (df_b is not None and not df_b.empty and "current_value" in df_b.columns) else 0.0
    delta_nav = tot_val_a - tot_val_b
    delta_nav_pct = (delta_nav / tot_val_b * 100.0) if tot_val_b > 0 else 0.0

    return {
        "df_merged": merged.sort_values(by="delta_val", ascending=False).reset_index(drop=True),
        "tot_val_a": tot_val_a,
        "tot_val_b": tot_val_b,
        "delta_nav": delta_nav,
        "delta_nav_pct": delta_nav_pct,
        "turnover_pct": turnover_pct,
        "capital_rebalanced": trading_capital,
        "new_entries_count": int((merged["status"] == "🟢 Nuovo Ingresso").sum()),
        "closed_entries_count": int((merged["status"] == "🔴 Chiusura Totale").sum()),
        "modified_count": int((merged["status"].isin(["⬆️ Acquisto Quote (+Qty)", "⬇️ Vendita Quote (-Qty)"])).sum()),
        "appreciated_count": int((merged["status"] == "📈 Apprezzamento (Prezzo +)").sum()),
        "depreciated_count": int((merged["status"] == "📉 Deprezzamento (Prezzo -)").sum())
    }


def reconstruct_point_in_time_portfolio(
    pos_today: pd.DataFrame,
    sr_port: pd.Series,
    returns_df: pd.DataFrame,
    target_date: Any,
    rf_rate: float = 0.035
) -> Dict[str, Any]:
    """
    Ricostruisce con precisione contabile lo stato storico (prezzi, pesi, controvalori e metriche di rischio)
    del portafoglio a una specifica data passata (target_date), basandosi sui rendimenti reali degli asset.
    """
    if pos_today is None or pos_today.empty or sr_port is None or sr_port.empty:
        return {"df_positions": pos_today.copy() if pos_today is not None else pd.DataFrame(), "metrics": {}, "total_value": 0.0}

    s_p = sr_port.copy().dropna()
    if getattr(s_p.index, 'tz', None) is not None:
        s_p.index = s_p.index.tz_localize(None)
    s_p.index = pd.to_datetime(s_p.index)

    target_dt = pd.to_datetime(target_date)

    # Fattore cumulato di crescita del portafoglio dal passato ad oggi
    sr_after = s_p[s_p.index > target_dt]
    port_cum_factor = float((1.0 + sr_after).prod()) if not sr_after.empty else 1.0
    if port_cum_factor <= 0.0001:
        port_cum_factor = 1.0

    tot_today = float(pos_today["current_value"].sum()) if "current_value" in pos_today.columns else 0.0
    true_past_nav = tot_today / port_cum_factor

    df_hist = pos_today.copy()
    
    # Ricostruzione asset-by-asset
    if returns_df is not None and not returns_df.empty:
        r_df = returns_df.copy().dropna(how="all")
        if getattr(r_df.index, 'tz', None) is not None:
            r_df.index = r_df.index.tz_localize(None)
        r_df.index = pd.to_datetime(r_df.index)
        r_after = r_df[r_df.index > target_dt]
        asset_cum_factors = (1.0 + r_after).prod() if not r_after.empty else pd.Series(1.0, index=r_df.columns)
    else:
        asset_cum_factors = pd.Series()

    raw_past_vals = []
    for idx, row in df_hist.iterrows():
        tk = row.get("ticker")
        val_now = float(row.get("current_value", 0.0))
        if not asset_cum_factors.empty and tk in asset_cum_factors.index and float(asset_cum_factors[tk]) > 0.0001:
            f_asset = float(asset_cum_factors[tk])
        else:
            f_asset = port_cum_factor
        
        raw_past_vals.append(val_now / max(0.001, f_asset))

    raw_sum = sum(raw_past_vals)
    scaling_ratio = (true_past_nav / raw_sum) if raw_sum > 0 else 1.0

    for idx, row in df_hist.iterrows():
        past_val = raw_past_vals[idx] * scaling_ratio
        df_hist.at[idx, "current_value"] = past_val
        if true_past_nav > 0:
            df_hist.at[idx, "weight_pct"] = (past_val / true_past_nav) * 100.0
        else:
            df_hist.at[idx, "weight_pct"] = 0.0

        if "last_price" in df_hist.columns:
            price_now = float(row.get("last_price", 1.0))
            tk = row.get("ticker")
            f_asset = float(asset_cum_factors[tk]) if (not asset_cum_factors.empty and tk in asset_cum_factors.index and float(asset_cum_factors[tk]) > 0.0001) else port_cum_factor
            df_hist.at[idx, "last_price"] = price_now / max(0.001, f_asset)

    # Calcolo metriche di rischio storiche reali fino alla target_date
    sr_past = s_p[s_p.index <= target_dt]
    if len(sr_past) >= 15:
        vol_ann = float(sr_past.std() * np.sqrt(252.0) * 100.0)
        daily_rf = (1.0 + rf_rate) ** (1.0 / 252.0) - 1.0
        excess_mean = float((sr_past - daily_rf).mean() * 252.0)
        sharpe = excess_mean / (vol_ann / 100.0) if vol_ann > 0 else 0.0
        var_95 = float(abs(sr_past.quantile(0.05)) * 100.0)
    else:
        vol_ann = float(s_p.std() * np.sqrt(252.0) * 100.0)
        sharpe = 0.0
        var_95 = 2.0

    hhi = float(((df_hist["weight_pct"] / 100.0) ** 2).sum())

    return {
        "df_positions": df_hist,
        "total_value": true_past_nav,
        "metrics": {
            "sharpe_ratio": sharpe,
            "volatility_ann_pct": vol_ann,
            "var_95_pct": var_95,
            "hhi_index": hhi
        }
    }


