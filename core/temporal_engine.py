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
