import pandas as pd
from sqlalchemy import text as sqlt
import numpy as np

def _safe_float(val, max_limit=999999.9999, min_limit=-999999.9999):
    """
    Sanitizza i valori numerici prima dell'inserimento nel database,
    prevenendo errori MySQL 1264 (Out of range value) su colonne DECIMAL.
    """
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        # Clamp bounds
        if f > max_limit:
            return float(max_limit)
        if f < min_limit:
            return float(min_limit)
        return round(float(f), 6)
    except (ValueError, TypeError):
        return None

def ensure_snapshot_tables(engine):
    """Crea le tabelle di snapshot a runtime se non esistono e aggiunge eventuali colonne mancanti."""
    from core.models import Base
    Base.metadata.create_all(engine)
    
    with engine.begin() as conn:

        
        # Migrazioni portfolio_snapshots
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN sortino_ratio DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN calmar_ratio DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN alpha_pct DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN information_ratio DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN stress_covid_loss DECIMAL(18,6)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN stress_lehman_loss DECIMAL(18,6)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN stress_rates_loss DECIMAL(18,6)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN var_exceptions_count INT"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN r_squared_pct DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_max_sharpe_ratio DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_max_sharpe_return DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_max_sharpe_risk DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_min_vol_ratio DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_min_vol_return DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE portfolio_snapshots ADD COLUMN opt_min_vol_risk DECIMAL(10,4)"))
        except: pass
        
        # Migrazioni snapshot_positions
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN trailing_pe DECIMAL(10,2)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN forward_pe DECIMAL(10,2)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN price_to_book DECIMAL(10,2)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN dividend_yield DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN roe DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN target_mean_price DECIMAL(18,6)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN peg_ratio DECIMAL(10,2)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN marginal_var_pct DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN component_var_pct DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN beta_vs_benchmark DECIMAL(10,4)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN days_to_liquidate DECIMAL(10,2)"))
        except: pass
        try: conn.execute(sqlt("ALTER TABLE snapshot_positions ADD COLUMN opt_weight_pct DECIMAL(10,4)"))
        except: pass

def save_snapshot_to_db(results: dict, engine, portfolio_id: int, run_id: str, run_name: str = None):
    """
    Salva i risultati analitici e quantitativi del portafoglio nel database.
    """
    ensure_snapshot_tables(engine)
    
    m   = results["metrics"]
    ret = m["returns"]
    mk  = m["market_risk"]
    con = m["concentration"]
    ai  = m.get("ai_insights", {})
    mc  = ai.get("montecarlo", {})
    clusters = ai.get("asset_clusters", [])
    pos = results["positions"]
    
    risk_contrib = results.get("risk_contribution", {})
    stress_tests = results.get("stress_tests", {})

    # 1. Inserimento Macro-Metriche (portfolio_snapshots)
    insert_snapshot = """
        INSERT INTO portfolio_snapshots (
            calc_date, run_id, run_name, portfolio_id, total_value, total_pnl, cagr_pct, sharpe_ratio, 
            max_drawdown_pct, var_95_pct, hhi_index, mc_expected_return_1y, mc_var_95,
            sortino_ratio, calmar_ratio, alpha_pct, information_ratio, r_squared_pct,
            stress_covid_loss, stress_lehman_loss, stress_rates_loss, var_exceptions_count,
            opt_max_sharpe_ratio, opt_max_sharpe_return, opt_max_sharpe_risk,
            opt_min_vol_ratio, opt_min_vol_return, opt_min_vol_risk
        ) VALUES (
            NOW(), :rid, :rname, :pid, :val, :pnl, :cagr, :sharpe,
            :mdd, :var, :hhi, :mc_ret, :mc_var,
            :sortino, :calmar, :alpha, :info_r, :rsq,
            :covid, :lehman, :rates, :vexc,
            :opt_max_s_ratio, :opt_max_s_ret, :opt_max_s_risk,
            :opt_min_v_ratio, :opt_min_v_ret, :opt_min_v_risk
        )
    """
    
    covid_loss = stress_tests.get("COVID-19 Crash (Feb-Mar 2020)", {}).get("portfolio_loss_eur")
    lehman_loss = stress_tests.get("Lehman Brothers (Sep-Nov 2008)", {}).get("portfolio_loss_eur")
    rates_loss = stress_tests.get("Tech & Rate Shock (Gen-Ott 2022)", {}).get("portfolio_loss_eur")

    MAX_DECIMAL_18 = 999999999999.999999
    MIN_DECIMAL_18 = -999999999999.999999
    
    with engine.begin() as conn:
        conn.execute(sqlt(insert_snapshot), {
            "rid":    run_id,
            "rname":  run_name,
            "pid":    portfolio_id,
            "val":    _safe_float(ret.get("portfolio_value"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "pnl":    _safe_float(ret.get("total_pnl"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "cagr":   _safe_float(ret.get("cagr_pct")),
            "sharpe": _safe_float(ret.get("sharpe_ratio")),
            "mdd":    _safe_float(mk.get("max_drawdown_pct")),
            "var":    _safe_float(mk.get("var_95")),
            "hhi":    _safe_float(con.get("hhi")),
            "mc_ret": _safe_float(mc.get("expected_return_1y_pct")),
            "mc_var": _safe_float(mc.get("var_95_simulated_pct")),
            "sortino": _safe_float(ret.get("sortino_ratio")),
            "calmar": _safe_float(ret.get("calmar_ratio")),
            "alpha":  _safe_float(ret.get("alpha_pct")),
            "info_r": _safe_float(ret.get("information_ratio")),
            "rsq":    _safe_float(mk.get("r_squared_pct")),
            "covid":  _safe_float(covid_loss, MAX_DECIMAL_18, MIN_DECIMAL_18),
            "lehman": _safe_float(lehman_loss, MAX_DECIMAL_18, MIN_DECIMAL_18),
            "rates":  _safe_float(rates_loss, MAX_DECIMAL_18, MIN_DECIMAL_18),
            "vexc":   mk.get("var_exceptions_count"),
            "opt_max_s_ratio": _safe_float(results.get("optimization", {}).get("max_sharpe", {}).get("sharpe")),
            "opt_max_s_ret":   _safe_float(results.get("optimization", {}).get("max_sharpe", {}).get("return", 0) * 100 if results.get("optimization") else None),
            "opt_max_s_risk":  _safe_float(results.get("optimization", {}).get("max_sharpe", {}).get("risk", 0) * 100 if results.get("optimization") else None),
            "opt_min_v_ratio": _safe_float(results.get("optimization", {}).get("min_vol", {}).get("sharpe")),
            "opt_min_v_ret":   _safe_float(results.get("optimization", {}).get("min_vol", {}).get("return", 0) * 100 if results.get("optimization") else None),
            "opt_min_v_risk":  _safe_float(results.get("optimization", {}).get("min_vol", {}).get("risk", 0) * 100 if results.get("optimization") else None)
        })
        
        snapshot_id = conn.execute(sqlt("SELECT LAST_INSERT_ID()")).scalar()

        
        # Dizionario di lookup per i cluster e volatilità dai modelli quantitativi
        cl_map = {}
        for c in clusters:
            tk = c.get("ticker", c.get("index"))
            cl_map[tk] = {
                "volatility": c.get("volatility", 0) * 100,  # converto in %
                "cluster": f"Cluster {c.get('cluster', 0)}"
            }
        
        # Dizionario Beta da Stress Test
        betas = {}
        covid_details = stress_tests.get("COVID-19 Crash (Feb-Mar 2020)", {}).get("details", {})
        for tk, tk_data in covid_details.items():
            betas[tk] = tk_data.get("beta")
            
        # Dizionario Risk Contribution
        rc_marginal = risk_contrib.get("marginal_var", {})
        rc_component = risk_contrib.get("component_var_pct", {})
        
        # 2. Inserimento Posizioni (snapshot_positions)
        insert_pos = """
            INSERT INTO snapshot_positions (
                snapshot_id, ticker, asset_class, qty_net, avg_cost, 
                last_price, current_value, unrealized_pnl, weight_pct, 
                volatility_pct, cluster_label, days_to_liquidate,
                trailing_pe, forward_pe, price_to_book, dividend_yield, roe, 
                target_mean_price, peg_ratio,
                marginal_var_pct, component_var_pct, beta_vs_benchmark, opt_weight_pct
            ) VALUES (
                :sid, :tk, :ac, :qty, :avgc,
                :lp, :cval, :upnl, :wpct,
                :vol, :cl, :dtl,
                :t_pe, :f_pe, :pb, :dy, :roe,
                :target, :peg,
                :mvar, :cvar, :beta, :opt_weight
            )
        """
        for _, r in pos.iterrows():
            if r["qty_net"] <= 0: continue
            
            tk = r["ticker"]
            tk_metrics = cl_map.get(tk, {})
            
            conn.execute(sqlt(insert_pos), {
                "sid":  snapshot_id,
                "tk":   tk,
                "ac":   r.get("asset_class"),
                "qty":  _safe_float(r.get("qty_net"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "avgc": _safe_float(r.get("avg_cost"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "lp":   _safe_float(r.get("last_price"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "cval": _safe_float(r.get("current_value"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "upnl": _safe_float(r.get("unrealized_pnl"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "wpct": _safe_float(r.get("weight_pct")),
                "vol":  _safe_float(tk_metrics.get("volatility")),
                "cl":   tk_metrics.get("cluster"),
                "dtl":  _safe_float(r.get("days_to_liquidate")),
                
                "t_pe":   _safe_float(r.get("trailing_pe")),
                "f_pe":   _safe_float(r.get("forward_pe")),
                "pb":     _safe_float(r.get("price_to_book")),
                "dy":     _safe_float(r.get("dividend_yield")),
                "roe":    _safe_float(r.get("roe")),
                "target": _safe_float(r.get("target_mean_price"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                "peg":    _safe_float(r.get("peg_ratio")),
                
                "mvar":   _safe_float(rc_marginal.get(tk)),
                "cvar":   _safe_float(rc_component.get(tk)),
                "beta":   _safe_float(betas.get(tk)),
                "opt_weight": _safe_float(
                    results.get("optimization", {}).get("max_sharpe", {}).get("weights", [])[
                        results.get("optimization", {}).get("tickers", []).index(tk)
                    ] * 100 
                    if results.get("optimization") and tk in results.get("optimization", {}).get("tickers", []) 
                    else None
                )
            })
            
    return True


def get_all_snapshots_history(engine, portfolio_name: str = None, run_name: str = None):
    """
    Recupera lo storico completo di tutti gli snapshot salvati nel database attivo,
    con filtri opzionali su Nome Portafoglio (p.name) e Nome Analisi (s.run_name).
    """
    if engine is None:
        return pd.DataFrame()

    query = """
        SELECT 
            s.snapshot_id, s.calc_date, s.run_id, s.run_name, s.portfolio_id, p.name as portfolio_name,
            s.total_value, s.total_pnl, s.cagr_pct, s.sharpe_ratio, s.max_drawdown_pct, s.var_95_pct, s.hhi_index,
            s.sortino_ratio, s.calmar_ratio, s.alpha_pct, s.information_ratio, s.r_squared_pct,
            s.opt_max_sharpe_ratio, s.opt_max_sharpe_return, s.opt_max_sharpe_risk
        FROM portfolio_snapshots s
        JOIN portfolios p ON s.portfolio_id = p.portfolio_id
        WHERE 1=1
    """
    params = {}
    if portfolio_name:
        query += " AND p.name = :pname"
        params["pname"] = portfolio_name
    if run_name:
        query += " AND s.run_name = :rname"
        params["rname"] = run_name

    query += " ORDER BY s.calc_date ASC"

    try:
        with engine.connect() as conn:
            df = pd.read_sql(sqlt(query), conn, params=params)
            return df
    except Exception:
        return pd.DataFrame()


def get_snapshot_positions_by_id(engine, snapshot_id: int):
    """
    Recupera il dettaglio delle posizioni salvate per uno specifico snapshot_id.
    """
    if engine is None or not snapshot_id:
        return pd.DataFrame()

    query = """
        SELECT 
            sp.*, a.name as asset_name, a.currency as asset_currency
        FROM snapshot_positions sp
        LEFT JOIN assets a ON sp.ticker = a.ticker
        WHERE sp.snapshot_id = :sid
        ORDER BY sp.current_value DESC
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(sqlt(query), conn, params={"sid": int(snapshot_id)})
            return df
    except Exception:
        return pd.DataFrame()
