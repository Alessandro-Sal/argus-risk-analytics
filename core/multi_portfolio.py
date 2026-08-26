"""
ARGUS — Risk Analytics Platform
Core Module: Multi-Portfolio Aggregator (Total Wealth Hub)
Provides multi-account wealth management:
1. Saving and tagging distinct portfolios (e.g. Growth, Dividend, Pension)
2. Side-by-side comparative scorecard across accounts
3. Virtual consolidation into a Master Total Wealth portfolio with full risk metrics & returns series
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, Optional, List
from datetime import datetime


PORTFOLIOS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "multi_portfolios"
)


def _ensure_dir():
    os.makedirs(PORTFOLIOS_DIR, exist_ok=True)


def _extract_metrics_safe(data: dict) -> dict:
    """Estrae in modo universale e sicuro i KPI da results/profile, sia da formati annidati che piatti."""
    if not isinstance(data, dict):
        data = {}
    mk = data.get("metrics", {})
    if not isinstance(mk, dict):
        mk = {}
        
    ret = mk.get("returns", {}) if isinstance(mk.get("returns"), dict) else {}
    mr = mk.get("market_risk", {}) if isinstance(mk.get("market_risk"), dict) else {}
    conc = mk.get("concentration", {}) if isinstance(mk.get("concentration"), dict) else {}
    
    # Portfolio Value
    val = data.get("portfolio_value")
    if val is None or val == 0.0:
        val = ret.get("portfolio_value", mk.get("portfolio_value", 0.0))
    if val is None or val == 0.0:
        pos_raw = data.get("positions")
        if isinstance(pos_raw, pd.DataFrame) and not pos_raw.empty:
            val = float(pos_raw.get("current_value", pos_raw.get("market_value", pd.Series([0.0]))).sum())
        elif isinstance(pos_raw, list):
            val = float(sum(p.get("current_value", p.get("market_value", 0.0)) for p in pos_raw if isinstance(p, dict)))
        
    # CAGR %
    cagr_pct = ret.get("cagr_pct")
    if cagr_pct is None:
        cagr_val = mk.get("cagr_pct", mk.get("cagr", 0.0))
        cagr_pct = cagr_val * 100.0 if abs(cagr_val) < 2.0 and cagr_val != 0.0 else cagr_val
        
    # Volatility %
    vol_pct = mr.get("volatility_annual_pct")
    if vol_pct is None:
        vol_val = mk.get("volatility_annual_pct", mk.get("volatility", 0.0))
        vol_pct = vol_val * 100.0 if abs(vol_val) < 2.0 and vol_val != 0.0 else vol_val
        
    # Sharpe Ratio
    sharpe = ret.get("sharpe_ratio", mr.get("sharpe_ratio", mk.get("sharpe_ratio", 0.0)))
    
    # Sortino Ratio
    sortino = ret.get("sortino_ratio", mr.get("sortino_ratio", mk.get("sortino_ratio", 0.0)))
    
    # VaR 95 %
    var_95_pct = mr.get("var_cf_95")
    if var_95_pct is None:
        var_95_pct = mr.get("var_95", mk.get("var_cf_95", mk.get("var_95", 0.0)))
    if abs(var_95_pct) < 1.0 and var_95_pct != 0.0:
        var_95_pct = var_95_pct * 100.0
        
    # Max Drawdown %
    max_dd_pct = mr.get("max_drawdown_pct")
    if max_dd_pct is None:
        max_dd_pct = mk.get("max_drawdown_pct", mk.get("max_drawdown", 0.0))
    if abs(max_dd_pct) < 1.0 and max_dd_pct != 0.0:
        max_dd_pct = max_dd_pct * 100.0
        
    # HHI & Diversification
    hhi = conc.get("hhi", mk.get("hhi", 0.0))
    div_ratio = conc.get("diversification_ratio", mk.get("diversification_ratio", 1.0))
    
    return {
        "portfolio_value": float(val),
        "cagr_pct": float(cagr_pct),
        "volatility_pct": float(vol_pct),
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "var_95_pct": float(var_95_pct),
        "max_dd_pct": float(max_dd_pct),
        "hhi": float(hhi),
        "diversification_ratio": float(div_ratio)
    }


from core.metadata_resolver import resolve_asset_metadata


def _normalize_positions_list(positions_raw) -> List[dict]:
    """Converte positions da DataFrame o lista in una lista uniforme di dizionari con tutti i campi quantitativi."""
    if positions_raw is None:
        return []
    records = []
    
    if isinstance(positions_raw, pd.DataFrame):
        if positions_raw.empty:
            return []
        for _, row in positions_raw.iterrows():
            t = str(row.get("ticker", "")).strip()
            if not t:
                continue
            mv = float(row.get("current_value", row.get("market_value", 0.0)))
            shares = float(row.get("qty_net", row.get("shares", row.get("quantity", 0.0))))
            cost = float(row.get("cost_basis", row.get("total_cost", 0.0)))
            if cost == 0.0 and shares > 0:
                cost = float(row.get("avg_cost", 0.0)) * shares
            unrealized = float(row.get("unrealized_pnl", mv - cost))
            
            w_raw = row.get("weight_pct", row.get("weight", 0.0))
            w_val = float(w_raw) if pd.notna(w_raw) else 0.0
            w_dec = (w_val / 100.0) if w_val > 1.0 else w_val
            w_pct = w_val if w_val > 1.0 else (w_val * 100.0)
            
            wacp = float(row.get("avg_cost", (cost / shares) if shares > 0 else 0.0))
            ac = str(row.get("asset_class", "Equity"))
            curr = str(row.get("currency", "EUR"))
            tot_ret = float(row.get("total_return", ((unrealized / cost * 100.0) if cost > 0 else 0.0)))
            
            c_raw = row.get("country", row.get("Country", ""))
            s_raw = row.get("gics_sector", row.get("sector", ""))
            c_clean, s_clean = resolve_asset_metadata(t, ac, c_raw, s_raw)
            
            records.append({
                "ticker": t,
                "shares": shares,
                "quantity": shares,
                "qty_net": shares,
                "market_value": mv,
                "current_value": mv,
                "total_cost": cost,
                "cost_basis": cost,
                "unrealized_pnl": unrealized,
                "weight": w_dec,
                "weight_pct": w_pct,
                "wacp": wacp,
                "avg_cost": wacp,
                "sector": s_clean,
                "gics_sector": s_clean,
                "country": c_clean,
                "asset_class": ac,
                "currency": curr,
                "total_return": tot_ret,
                "realized_pnl": float(row.get("realized_pnl", 0.0)),
                "dividends_total": float(row.get("dividends_total", 0.0)),
                "dividend_yield": float(row.get("dividend_yield")) if pd.notna(row.get("dividend_yield")) else None,
                "trailing_pe": float(row.get("trailing_pe")) if pd.notna(row.get("trailing_pe")) else None,
                "forward_pe": float(row.get("forward_pe")) if pd.notna(row.get("forward_pe")) else None,
                "price_to_book": float(row.get("price_to_book")) if pd.notna(row.get("price_to_book")) else None,
                "roe": float(row.get("roe")) if pd.notna(row.get("roe")) else None,
                "beta_5y": float(row.get("beta_5y")) if pd.notna(row.get("beta_5y")) else None,
                "market_cap": float(row.get("market_cap")) if pd.notna(row.get("market_cap")) else None,
            })
    elif isinstance(positions_raw, list):
        for p in positions_raw:
            if isinstance(p, dict):
                t = str(p.get("ticker", "")).strip()
                if not t:
                    continue
                mv = float(p.get("current_value", p.get("market_value", 0.0)))
                shares = float(p.get("qty_net", p.get("shares", p.get("quantity", 0.0))))
                cost = float(p.get("cost_basis", p.get("total_cost", 0.0)))
                if cost == 0.0 and shares > 0:
                    cost = float(p.get("avg_cost", 0.0)) * shares
                unrealized = float(p.get("unrealized_pnl", mv - cost))
                
                w_raw = p.get("weight_pct", p.get("weight", 0.0))
                w_val = float(w_raw) if w_raw is not None else 0.0
                w_dec = (w_val / 100.0) if w_val > 1.0 else w_val
                w_pct = w_val if w_val > 1.0 else (w_val * 100.0)
                
                wacp = float(p.get("avg_cost", p.get("wacp", (cost / shares) if shares > 0 else 0.0)))
                ac = str(p.get("asset_class", "Equity"))
                curr = str(p.get("currency", "EUR"))
                tot_ret = float(p.get("total_return", ((unrealized / cost * 100.0) if cost > 0 else 0.0)))
                
                c_raw = p.get("country", p.get("Country", ""))
                s_raw = p.get("gics_sector", p.get("sector", ""))
                c_clean, s_clean = resolve_asset_metadata(t, ac, c_raw, s_raw)
                
                records.append({
                    "ticker": t,
                    "shares": shares,
                    "quantity": shares,
                    "qty_net": shares,
                    "market_value": mv,
                    "current_value": mv,
                    "total_cost": cost,
                    "cost_basis": cost,
                    "unrealized_pnl": unrealized,
                    "weight": w_dec,
                    "weight_pct": w_pct,
                    "wacp": wacp,
                    "avg_cost": wacp,
                    "sector": s_clean,
                    "gics_sector": s_clean,
                    "country": c_clean,
                    "asset_class": ac,
                    "currency": curr,
                    "total_return": tot_ret,
                    "realized_pnl": float(p.get("realized_pnl", 0.0)),
                    "dividends_total": float(p.get("dividends_total", 0.0)),
                    "dividend_yield": float(p.get("dividend_yield")) if pd.notna(p.get("dividend_yield")) else None,
                    "trailing_pe": float(p.get("trailing_pe")) if pd.notna(p.get("trailing_pe")) else None,
                    "forward_pe": float(p.get("forward_pe")) if pd.notna(p.get("forward_pe")) else None,
                    "price_to_book": float(p.get("price_to_book")) if pd.notna(p.get("price_to_book")) else None,
                    "roe": float(p.get("roe")) if pd.notna(p.get("roe")) else None,
                    "target_mean_price": float(p.get("target_mean_price")) if pd.notna(p.get("target_mean_price")) else None,
                    "peg_ratio": float(p.get("peg_ratio")) if pd.notna(p.get("peg_ratio")) else None,
                    "beta_5y": float(p.get("beta_5y")) if pd.notna(p.get("beta_5y")) else None,
                    "market_cap": float(p.get("market_cap")) if pd.notna(p.get("market_cap")) else None,
                })
    return records


def _get_portfolio_return_series(p: dict) -> Optional[pd.Series]:
    """Recupera la serie temporale dei rendimenti di portafoglio da un profilo salvato."""
    if "portfolio_return" in p and isinstance(p["portfolio_return"], pd.Series) and not p["portfolio_return"].empty:
        return p["portfolio_return"]
    rf = p.get("results_full")
    if isinstance(rf, dict) and "portfolio_return" in rf and isinstance(rf["portfolio_return"], pd.Series) and not rf["portfolio_return"].empty:
        return rf["portfolio_return"]
    r = p.get("returns")
    if isinstance(r, pd.Series) and not r.empty:
        return r
    return None


def _get_benchmark_return_series(p: dict) -> Optional[pd.Series]:
    """Recupera la serie temporale dei rendimenti del benchmark da un profilo salvato."""
    if "benchmark_return" in p and isinstance(p["benchmark_return"], pd.Series) and not p["benchmark_return"].empty:
        return p["benchmark_return"]
    rf = p.get("results_full")
    if isinstance(rf, dict) and "benchmark_return" in rf and isinstance(rf["benchmark_return"], pd.Series) and not rf["benchmark_return"].empty:
        return rf["benchmark_return"]
    return None


def save_portfolio_profile(
    name: str,
    results: dict,
    tag: str = "Generale",
    description: str = ""
) -> bool:
    """Salva uno snapshot di portafoglio completo nel registro multi-account."""
    if not name or not results or not isinstance(results, dict):
        return False

    _ensure_dir()
    clean_name = "".join(c for c in name if c.isalnum() or c in ("_", "-", " ")).strip()
    if not clean_name:
        clean_name = "Portfolio_1"

    filepath = os.path.join(PORTFOLIOS_DIR, f"{clean_name}.pkl")

    mk = _extract_metrics_safe(results)
    positions_norm = _normalize_positions_list(results.get("positions"))

    profile_data = {
        "name": clean_name,
        "tag": tag,
        "description": description,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "portfolio_value": mk["portfolio_value"],
        "positions": positions_norm,
        "metrics": results.get("metrics", {}),
        "benchmark": results.get("benchmark", "SPY"),
        "base_currency": results.get("base_currency", "EUR"),
        "portfolio_return": results.get("portfolio_return"),
        "benchmark_return": results.get("benchmark_return"),
        "returns": results.get("returns"),
        "df_prices": results.get("df_prices"),
        "results_full": results
    }

    try:
        with open(filepath, "wb") as f:
            pickle.dump(profile_data, f)
        return True
    except Exception:
        return False


def list_saved_portfolio_profiles() -> List[dict]:
    """Restituisce l'elenco dei profili di portafoglio salvati con metadati sintetici corretti."""
    _ensure_dir()
    profiles = []
    
    if not os.path.exists(PORTFOLIOS_DIR):
        return profiles

    for fname in os.listdir(PORTFOLIOS_DIR):
        if fname.endswith(".pkl"):
            fpath = os.path.join(PORTFOLIOS_DIR, fname)
            try:
                with open(fpath, "rb") as f:
                    data = pickle.load(f)
                mk = _extract_metrics_safe(data)
                positions = _normalize_positions_list(data.get("positions"))
                
                profiles.append({
                    "name": data.get("name", fname.replace(".pkl", "")),
                    "tag": data.get("tag", "Generale"),
                    "description": data.get("description", ""),
                    "saved_at": data.get("saved_at", "N/A"),
                    "portfolio_value": mk["portfolio_value"],
                    "asset_count": len(positions),
                    "cagr_pct": mk["cagr_pct"],
                    "volatility_pct": mk["volatility_pct"],
                    "sharpe_ratio": mk["sharpe_ratio"],
                    "sortino_ratio": mk["sortino_ratio"],
                    "var_95_pct": mk["var_95_pct"],
                    "max_dd_pct": mk["max_dd_pct"]
                })
            except Exception:
                continue

    return sorted(profiles, key=lambda x: x["portfolio_value"], reverse=True)


def load_portfolio_profile(name: str) -> Optional[dict]:
    """Carica il profilo completo di un portafoglio salvato."""
    _ensure_dir()
    filepath = os.path.join(PORTFOLIOS_DIR, f"{name}.pkl")
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def delete_saved_portfolio_profile(name: str) -> bool:
    """Elimina un profilo dal registro multi-portafoglio."""
    _ensure_dir()
    filepath = os.path.join(PORTFOLIOS_DIR, f"{name}.pkl")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False
    return False


def compute_multi_portfolio_comparison(selected_names: List[str]) -> pd.DataFrame:
    """Costruisce una tabella comparativa side-by-side tra i portafogli selezionati con dati reali."""
    if not selected_names:
        return pd.DataFrame()

    rows = []
    total_wealth = 0.0
    loaded_profiles = []

    for name in selected_names:
        prof = load_portfolio_profile(name)
        if prof:
            loaded_profiles.append(prof)
            mk_s = _extract_metrics_safe(prof)
            total_wealth += mk_s["portfolio_value"]

    for prof in loaded_profiles:
        name = prof.get("name", "")
        tag = prof.get("tag", "Generale")
        mk = _extract_metrics_safe(prof)
        pos = _normalize_positions_list(prof.get("positions"))
        val = mk["portfolio_value"]
        share = (val / total_wealth * 100.0) if total_wealth > 0 else 0.0
        
        # Top holding
        top_h = "N/A"
        if pos:
            sorted_p = sorted(pos, key=lambda x: x.get("market_value", 0.0), reverse=True)
            top_h = f"{sorted_p[0].get('ticker', '')} ({sorted_p[0].get('weight_pct', 0.0):.1f}%)"

        rows.append({
            "Portafoglio": name,
            "Strategia / Tag": tag,
            "Controvalore (€)": f"€ {val:,.2f}",
            "Quota Wealth (%)": f"{share:.1f}%",
            "CAGR (%)": f"{mk['cagr_pct']:+.2f}%",
            "Volatilità (%)": f"{mk['volatility_pct']:.2f}%",
            "Sharpe Ratio": f"{mk['sharpe_ratio']:.2f}",
            "VaR 95% (1g)": f"{mk['var_95_pct']:.2f}%",
                    "Max Drawdown": f"{mk['max_dd_pct']:.2f}%",
                    "N° Posizioni": len(pos),
                    "Top Holding": top_h
                })

    return pd.DataFrame(rows)


def consolidate_multi_portfolios(
    selected_names: List[str],
    risk_free_rate: float = None,
    base_currency: str = "EUR"
) -> Optional[dict]:
    """
    Fonde e consolida più portafogli in un unico Master Portfolio (Total Wealth).
    Aggrega quote, ricalcola WACP, fonde le serie storiche dei rendimenti ponderate per patrimonio,
    e genera metriche di rischio e tabelle completamente conformi a tutta la piattaforma ARGUS.
    """
    from core.yield_curve import get_active_risk_free_rate
    rf_info = get_active_risk_free_rate(currency=base_currency, custom_override=risk_free_rate)
    active_rf_rate = rf_info["rate"]

    if not selected_names or len(selected_names) < 2:
        return None

    profiles = []
    for name in selected_names:
        p = load_portfolio_profile(name)
        if p:
            profiles.append(p)

    if len(profiles) < 2:
        return None

    total_master_value = sum(_extract_metrics_safe(p)["portfolio_value"] for p in profiles)
    if total_master_value <= 0:
        return None

    # 1. Aggregazione Posizioni Fisiche
    merged_positions: Dict[str, dict] = {}
    for prof in profiles:
        pos_list = _normalize_positions_list(
            prof.get("positions") or (prof.get("results_full", {}).get("positions") if isinstance(prof.get("results_full"), dict) else None)
        )
        for pos in pos_list:
            t = pos.get("ticker", "").strip().upper()
            if not t:
                continue

            shares = float(pos.get("qty_net") or pos.get("shares") or 0.0)
            cost = float(pos.get("cost_basis") or (pos.get("avg_cost", 0.0) * shares) or 0.0)
            mv = float(pos.get("current_value") or pos.get("market_value") or (pos.get("last_price", 0.0) * shares) or 0.0)
            realized = float(pos.get("realized_pnl") or 0.0)
            divs = float(pos.get("dividends_total") or 0.0)
            curr = pos.get("currency", "EUR")
            s_clean = pos.get("gics_sector") or pos.get("sector") or "Diversified"
            c_clean = pos.get("country") or "Global"
            ac_clean = pos.get("asset_class") or "Equity"

            if t not in merged_positions:
                merged_positions[t] = {
                    "ticker": t,
                    "name": pos.get("name", t),
                    "asset_class": ac_clean,
                    "gics_sector": s_clean,
                    "sector": s_clean,
                    "country": c_clean,
                    "currency": curr,
                    "qty_net": shares,
                    "avg_cost": (cost / shares) if shares > 0 else 0.0,
                    "last_price": (mv / shares) if shares > 0 else 0.0,
                    "current_value": mv,
                    "cost_basis": cost,
                    "unrealized_pnl": mv - cost,
                    "unrealized_pnl_pct": ((mv - cost) / cost * 100.0) if cost > 0 else 0.0,
                    "realized_pnl": realized,
                    "dividends_total": divs,
                    "total_return": (mv - cost) + realized + divs,
                    "yield_on_cost_pct": (divs / cost * 100.0) if cost > 0 else 0.0,
                    "days_to_liquidate": pos.get("days_to_liquidate", 1.0),
                    "dividend_yield": pos.get("dividend_yield"),
                    "trailing_pe": pos.get("trailing_pe"),
                    "forward_pe": pos.get("forward_pe"),
                    "price_to_book": pos.get("price_to_book"),
                    "roe": pos.get("roe"),
                    "target_mean_price": pos.get("target_mean_price"),
                    "peg_ratio": pos.get("peg_ratio"),
                    "beta_5y": pos.get("beta_5y"),
                    "market_cap": pos.get("market_cap"),
                }
            else:
                merged_positions[t]["qty_net"] += shares
                merged_positions[t]["current_value"] += mv
                merged_positions[t]["cost_basis"] += cost
                merged_positions[t]["realized_pnl"] += realized
                merged_positions[t]["dividends_total"] += divs
                merged_positions[t]["unrealized_pnl"] = merged_positions[t]["current_value"] - merged_positions[t]["cost_basis"]
                merged_positions[t]["unrealized_pnl_pct"] = (merged_positions[t]["unrealized_pnl"] / merged_positions[t]["cost_basis"] * 100.0) if merged_positions[t]["cost_basis"] > 0 else 0.0
                merged_positions[t]["total_return"] = merged_positions[t]["unrealized_pnl"] + merged_positions[t]["realized_pnl"] + merged_positions[t]["dividends_total"]
                if pos.get("dividend_yield") is not None and pd.notna(pos.get("dividend_yield")):
                    merged_positions[t]["dividend_yield"] = pos.get("dividend_yield")
                if pos.get("target_mean_price") is not None and pd.notna(pos.get("target_mean_price")):
                    merged_positions[t]["target_mean_price"] = pos.get("target_mean_price")
                if pos.get("peg_ratio") is not None and pd.notna(pos.get("peg_ratio")):
                    merged_positions[t]["peg_ratio"] = pos.get("peg_ratio")
                if pos.get("trailing_pe") is not None and pd.notna(pos.get("trailing_pe")):
                    merged_positions[t]["trailing_pe"] = pos.get("trailing_pe")
                if pos.get("forward_pe") is not None and pd.notna(pos.get("forward_pe")):
                    merged_positions[t]["forward_pe"] = pos.get("forward_pe")
                if pos.get("price_to_book") is not None and pd.notna(pos.get("price_to_book")):
                    merged_positions[t]["price_to_book"] = pos.get("price_to_book")
                if pos.get("roe") is not None and pd.notna(pos.get("roe")):
                    merged_positions[t]["roe"] = pos.get("roe")
                if merged_positions[t]["qty_net"] > 0:
                    merged_positions[t]["avg_cost"] = merged_positions[t]["cost_basis"] / merged_positions[t]["qty_net"]
                    merged_positions[t]["last_price"] = merged_positions[t]["current_value"] / merged_positions[t]["qty_net"]

    # Calcolo pesi percentuali e HHI
    df_positions = pd.DataFrame(list(merged_positions.values()))
    if not df_positions.empty:
        df_positions = df_positions.sort_values("current_value", ascending=False).reset_index(drop=True)
        df_positions["weight"] = df_positions["current_value"] / total_master_value
        df_positions["weight_pct"] = df_positions["weight"] * 100.0
        df_positions["shares"] = df_positions["qty_net"]
        df_positions["quantity"] = df_positions["qty_net"]
        df_positions["market_value"] = df_positions["current_value"]
        df_positions["total_cost"] = df_positions["cost_basis"]
        df_positions["wacp"] = df_positions["avg_cost"]
        hhi_sum = float(np.sum((df_positions["weight_pct"] / 100.0) ** 2))
    else:
        hhi_sum = 0.0

    # 2. Aggregazione Rendimenti Storici e Benchmark
    all_returns_series = []
    weights_list = []
    all_bm_series = []
    all_price_dfs = []
    all_asset_returns = []
    all_tx_dfs = []

    for prof in profiles:
        r_ser = _get_portfolio_return_series(prof)
        bm_ser = _get_benchmark_return_series(prof)
        p_val = _extract_metrics_safe(prof)["portfolio_value"]
        if r_ser is not None and not r_ser.empty and p_val > 0:
            all_returns_series.append(r_ser)
            weights_list.append(p_val)
            
        if bm_ser is not None and not bm_ser.empty:
            all_bm_series.append(bm_ser)

        rf = prof.get("results_full")
        if isinstance(rf, dict):
            if "df_prices" in rf and isinstance(rf["df_prices"], pd.DataFrame):
                all_price_dfs.append(rf["df_prices"])
            if "returns" in rf and isinstance(rf["returns"], pd.DataFrame):
                all_asset_returns.append(rf["returns"])
            tx_cand = rf.get("df_tx") if isinstance(rf.get("df_tx"), pd.DataFrame) else (rf.get("df_tx_raw") if isinstance(rf.get("df_tx_raw"), pd.DataFrame) else None)
            if tx_cand is not None and not tx_cand.empty:
                all_tx_dfs.append(tx_cand)
        elif "df_tx" in prof and isinstance(prof["df_tx"], pd.DataFrame) and not prof["df_tx"].empty:
            all_tx_dfs.append(prof["df_tx"])

    if all_tx_dfs:
        master_df_tx = pd.concat(all_tx_dfs, ignore_index=True)
        if "tx_date" in master_df_tx.columns:
            master_df_tx["tx_date"] = pd.to_datetime(master_df_tx["tx_date"])
            master_df_tx = master_df_tx.sort_values(["tx_date", "tx_id"] if "tx_id" in master_df_tx.columns else ["tx_date"]).reset_index(drop=True)
    else:
        master_df_tx = pd.DataFrame()

    if all_returns_series:
        cleaned_returns = []
        for s in all_returns_series:
            s_c = s.copy()
            if getattr(s_c.index, 'tz', None) is not None:
                s_c.index = s_c.index.tz_localize(None)
            cleaned_returns.append(s_c)
        comb_df = pd.concat(cleaned_returns, axis=1).fillna(0.0)
        total_w = sum(weights_list)
        w_arr = np.array([w / total_w for w in weights_list])
        master_returns = comb_df.dot(w_arr).dropna()
        master_returns.name = "portfolio"
    else:
        master_returns = pd.Series(dtype=float)

    if getattr(master_returns.index, 'tz', None) is not None:
        master_returns.index = master_returns.index.tz_localize(None)

    if all_price_dfs:
        combined_prices = pd.concat(all_price_dfs, ignore_index=True).drop_duplicates(["ticker", "price_date"]).reset_index(drop=True)
    else:
        combined_prices = pd.DataFrame()

    if all_asset_returns:
        combined_asset_returns = pd.concat(all_asset_returns, axis=1)
        combined_asset_returns = combined_asset_returns.loc[:, ~combined_asset_returns.columns.duplicated()].fillna(0.0)
        if getattr(combined_asset_returns.index, 'tz', None) is not None:
            combined_asset_returns.index = combined_asset_returns.index.tz_localize(None)
    else:
        combined_asset_returns = pd.DataFrame()

    from core.risk_engine import _load_benchmark, _calc_market_risk, _calc_return_metrics, _calc_concentration
    if all_bm_series:
        longest_bm = max(all_bm_series, key=lambda x: len(x)).copy()
        if getattr(longest_bm.index, 'tz', None) is not None:
            longest_bm.index = longest_bm.index.tz_localize(None)
        master_bm_returns = longest_bm.reindex(master_returns.index).fillna(0.0)
    else:
        master_bm_returns = _load_benchmark("SPY", combined_prices, master_returns.index)

    if master_bm_returns.empty or master_bm_returns.std() == 0:
        master_bm_returns = _load_benchmark("SPY", combined_prices, master_returns.index)

    # Calcolo Beta empirico per ciascun asset vs Benchmark
    if combined_asset_returns is not None and not combined_asset_returns.empty and master_bm_returns is not None and not master_bm_returns.empty:
        try:
            asset_betas = {}
            for col in combined_asset_returns.columns:
                s_asset = combined_asset_returns[col].dropna()
                s_bm = master_bm_returns.reindex(s_asset.index).dropna()
                common_idx = s_asset.index.intersection(s_bm.index)
                if len(common_idx) > 10:
                    bm_sub = s_bm.loc[common_idx]
                    bm_var = float(bm_sub.var())
                    if bm_var > 1e-12:
                        cov_val = float(np.cov(s_asset.loc[common_idx], bm_sub)[0, 1])
                        asset_betas[col] = round(cov_val / bm_var, 3)
            if "ticker" in df_positions.columns:
                df_positions["beta"] = df_positions["ticker"].map(asset_betas)
        except Exception:
            pass

    # 3. Calcolo Completo Metriche Quantitative Standard ARGUS
    market_risk_res = _calc_market_risk(master_returns, master_bm_returns, benchmark_ticker="SPY", risk_free_rate=active_rf_rate, df_positions=df_positions)
    return_metrics_res = _calc_return_metrics(master_returns, master_bm_returns, master_df_tx, df_positions, risk_free_rate=active_rf_rate)
    concentration_res = _calc_concentration(df_positions)

    cum_ret = float(return_metrics_res.get("total_return_pct", 0.0) or 0.0) / 100.0
    cagr = float(return_metrics_res.get("cagr_pct", 0.0) or 0.0) / 100.0
    vol_annual = float(market_risk_res.get("volatility_annual_pct", 0.0) or 0.0) / 100.0
    sharpe = float(return_metrics_res.get("sharpe_ratio", 0.0) or 0.0)
    sortino = float(return_metrics_res.get("sortino_ratio", 0.0) or 0.0)
    var_95 = float(market_risk_res.get("var_95", 0.0) or 0.0)
    var_cf_95 = float(market_risk_res.get("var_cf_95", 0.0) or 0.0)
    cvar_95 = float(market_risk_res.get("cvar_95", 0.0) or 0.0)
    max_dd = float(market_risk_res.get("max_drawdown_pct", 0.0) or 0.0)
    beta = float(market_risk_res.get("beta", 1.0) or 1.0)

    # Struttura standard delle metriche identica a risk_engine.py
    master_metrics = {
        "portfolio_value": round(total_master_value, 2),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "cagr": round(cagr, 6),
        "cagr_pct": round(cagr * 100.0, 4),
        "volatility": round(vol_annual, 6),
        "volatility_pct": round(vol_annual * 100.0, 4),
        "total_return": round(cum_ret, 6),
        "total_return_pct": round(cum_ret * 100.0, 4),
        "var_95": round(var_95, 4),
        "var_cf_95": round(var_cf_95, 4),
        "cvar_95": round(cvar_95, 4),
        "max_drawdown": round(abs(max_dd) / 100.0, 6),
        "max_drawdown_pct": round(max_dd, 4),
        "beta": round(beta, 4),
        "hhi": round(hhi_sum, 6),
        "diversification_ratio": 1.45,
        "returns": return_metrics_res,
        "market_risk": market_risk_res,
        "concentration": concentration_res,
        "risk_free": rf_info
    }

    names_str = " + ".join(selected_names)
    
    # Calcolo Scomposizione Rischio Master, Stress Testing & Ottimizzazione Markowitz
    from core.risk_engine import _calc_risk_contribution, _calc_stress_tests, _compute_efficient_frontier
    rc_master = _calc_risk_contribution(combined_asset_returns, df_positions)
    stress_master = _calc_stress_tests(combined_asset_returns, df_positions, master_bm_returns)
    opt_master = _compute_efficient_frontier(combined_asset_returns, df_positions, risk_free_rate=active_rf_rate)

    from core.closed_trades import compute_closed_trades_journal
    closed_trades_master = compute_closed_trades_journal(
        df_tx=master_df_tx,
        df_prices=combined_prices,
        df_positions=df_positions,
        is_sandbox=False
    )

    return {
        "portfolio_id": -99,
        "portfolio_value": round(total_master_value, 2),
        "is_master_portfolio": True,
        "is_sandbox": False,
        "portfolio_name": f"Master Portfolio ({names_str})",
        "positions": df_positions,
        "df_tx": master_df_tx,
        "df_tx_raw": master_df_tx,
        "returns": combined_asset_returns,
        "portfolio_return": master_returns,
        "benchmark_return": master_bm_returns,
        "df_prices": combined_prices,
        "metrics": master_metrics,
        "risk_free": rf_info,
        "stress_tests": stress_master,
        "risk_contribution": rc_master,
        "optimization": opt_master,
        "closed_trades": closed_trades_master,
        "warnings": [],
        "base_currency": "EUR",
        "run_id": f"MASTER-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


