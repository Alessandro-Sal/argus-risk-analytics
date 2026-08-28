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
        cols_to_add_snapshots = [
            ("sortino_ratio", "DECIMAL(10,4)"),
            ("calmar_ratio", "DECIMAL(10,4)"),
            ("alpha_pct", "DECIMAL(10,4)"),
            ("information_ratio", "DECIMAL(10,4)"),
            ("r_squared_pct", "DECIMAL(10,4)"),
            ("stress_covid_loss", "DECIMAL(18,6)"),
            ("stress_lehman_loss", "DECIMAL(18,6)"),
            ("stress_rates_loss", "DECIMAL(18,6)"),
            ("var_exceptions_count", "INT"),
            ("opt_max_sharpe_ratio", "DECIMAL(10,4)"),
            ("opt_max_sharpe_return", "DECIMAL(10,4)"),
            ("opt_max_sharpe_risk", "DECIMAL(10,4)"),
            ("opt_min_vol_ratio", "DECIMAL(10,4)"),
            ("opt_min_vol_return", "DECIMAL(10,4)"),
            ("opt_min_vol_risk", "DECIMAL(10,4)"),
            ("volatility_annual_pct", "DECIMAL(10,4)"),
            ("volatility_daily_pct", "DECIMAL(10,4)"),
            ("cvar_95_pct", "DECIMAL(10,4)"),
            ("var_cf_95_pct", "DECIMAL(10,4)"),
            ("cvar_cf_95_pct", "DECIMAL(10,4)"),
            ("var_99_pct", "DECIMAL(10,4)"),
            ("cvar_99_pct", "DECIMAL(10,4)"),
            ("omega_ratio", "DECIMAL(10,4)"),
            ("tail_ratio", "DECIMAL(10,4)"),
            ("gain_loss_ratio", "DECIMAL(10,4)"),
            ("ulcer_index", "DECIMAL(10,4)"),
            ("skewness", "DECIMAL(10,4)"),
            ("kurtosis", "DECIMAL(10,4)"),
            ("diversification_ratio", "DECIMAL(10,4)"),
            ("ff_alpha_pct", "DECIMAL(10,4)"),
            ("ff_beta_mkt", "DECIMAL(10,4)"),
            ("smb_tilt", "DECIMAL(10,4)"),
            ("hml_tilt", "DECIMAL(10,4)"),
            ("risk_free_rate_pct", "DECIMAL(10,4)"),
            ("cost_basis_total", "DECIMAL(18,6)"),
            ("unrealized_pnl_total", "DECIMAL(18,6)"),
            ("realized_pnl_total", "DECIMAL(18,6)"),
            ("dividends_total", "DECIMAL(18,6)"),
            ("benchmark_ticker", "VARCHAR(50)"),
            ("ns_beta0", "DECIMAL(10,4)"),
            ("ns_beta1", "DECIMAL(10,4)"),
            ("ns_beta2", "DECIMAL(10,4)"),
            ("ns_tau", "DECIMAL(10,4)"),
            ("covered_call_income_eur", "DECIMAL(18,6)"),
            ("covered_call_contracts", "INT"),
            ("garch_vol_current_pct", "DECIMAL(10,4)"),
            ("current_regime", "VARCHAR(50)"),
            ("regime_crisis_probability", "DECIMAL(10,4)"),
            ("accumulated_minusvalenze_eur", "DECIMAL(18,6)"),
            ("total_tax_due_eur", "DECIMAL(18,6)"),
            ("tax_drag_pct", "DECIMAL(10,4)"),
            ("closed_trades_count", "INT"),
            ("win_rate_pct", "DECIMAL(10,4)"),
            ("profit_factor", "DECIMAL(10,4)"),
            ("portfolio_duration_modified", "DECIMAL(10,4)"),
            ("portfolio_convexity", "DECIMAL(10,4)"),
            ("portfolio_ytm_weighted_pct", "DECIMAL(10,4)")
        ]
        for col_name, col_type in cols_to_add_snapshots:
            try:
                conn.execute(sqlt(f"ALTER TABLE portfolio_snapshots ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass

        # Migrazioni snapshot_positions
        cols_to_add_positions = [
            ("trailing_pe", "DECIMAL(10,2)"),
            ("forward_pe", "DECIMAL(10,2)"),
            ("price_to_book", "DECIMAL(10,2)"),
            ("dividend_yield", "DECIMAL(10,4)"),
            ("roe", "DECIMAL(10,4)"),
            ("target_mean_price", "DECIMAL(18,6)"),
            ("peg_ratio", "DECIMAL(10,2)"),
            ("marginal_var_pct", "DECIMAL(10,4)"),
            ("component_var_pct", "DECIMAL(10,4)"),
            ("beta_vs_benchmark", "DECIMAL(10,4)"),
            ("days_to_liquidate", "DECIMAL(10,2)"),
            ("opt_weight_pct", "DECIMAL(10,4)"),
            ("realized_pnl", "DECIMAL(18,6)"),
            ("dividends_total", "DECIMAL(18,6)"),
            ("yield_on_cost_pct", "DECIMAL(10,4)"),
            ("sector", "VARCHAR(100)"),
            ("country", "VARCHAR(100)"),
            ("currency", "VARCHAR(3)"),
            ("cost_basis", "DECIMAL(18,6)"),
            ("altman_z_score", "DECIMAL(10,4)"),
            ("piotroski_f_score", "DECIMAL(10,2)"),
            ("beneish_m_score", "DECIMAL(10,4)"),
            ("sloan_accrual_ratio", "DECIMAL(10,4)"),
            ("ev_to_ebitda", "DECIMAL(10,2)"),
            ("free_cash_flow_yield", "DECIMAL(10,4)"),
            ("debt_to_equity", "DECIMAL(10,4)"),
            ("atr_14_eur", "DECIMAL(18,6)"),
            ("chandelier_exit_long_eur", "DECIMAL(18,6)"),
            ("rsi_14", "DECIMAL(10,2)"),
            ("total_return", "DECIMAL(18,6)")
        ]
        for col_name, col_type in cols_to_add_positions:
            try:
                conn.execute(sqlt(f"ALTER TABLE snapshot_positions ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass

        # Deduplicazione portfolios e unificazione ID orfani/ridondanti
        try:
            port_duplicates = conn.execute(sqlt("""
                SELECT name, COUNT(*) as cnt, MIN(portfolio_id) as min_id
                FROM portfolios
                GROUP BY name
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            for p_name, cnt, min_id in port_duplicates:
                other_ids = conn.execute(
                    sqlt("SELECT portfolio_id FROM portfolios WHERE name = :n AND portfolio_id != :min_id"),
                    {"n": p_name, "min_id": min_id}
                ).fetchall()
                other_ids_list = [r[0] for r in other_ids]
                for old_id in other_ids_list:
                    # Rimappa transactions e snapshots sul canonical ID prima di eliminare i duplicati
                    conn.execute(sqlt("UPDATE transactions SET portfolio_id = :min_id WHERE portfolio_id = :old_id"), {"min_id": min_id, "old_id": old_id})
                    conn.execute(sqlt("UPDATE portfolio_snapshots SET portfolio_id = :min_id WHERE portfolio_id = :old_id"), {"min_id": min_id, "old_id": old_id})
                    conn.execute(sqlt("DELETE FROM portfolios WHERE portfolio_id = :old_id"), {"old_id": old_id})
        except Exception:
            pass


def get_or_create_portfolio_id(engine_or_conn, name: str, owner: str = "streamlit_user", base_currency: str = "EUR") -> int:
    """
    Risolve in modo univoco e deterministico l'ID del portafoglio per nome.
    Se esiste già un portafoglio con questo nome, riutilizza l'ID canonico (il più basso).
    Se non esiste, crea un nuovo record in 'portfolios' e ne restituisce l'ID.
    """
    if not name or not str(name).strip():
        name = "Portafoglio Quantitativo"
    name = str(name).strip()
    
    def _execute_with_conn(conn):
        existing_id = conn.execute(
            sqlt("SELECT portfolio_id FROM portfolios WHERE name = :n ORDER BY portfolio_id ASC LIMIT 1"),
            {"n": name}
        ).scalar()
        if existing_id:
            # Assicura valuta base aggiornata
            conn.execute(
                sqlt("UPDATE portfolios SET base_currency = :curr WHERE portfolio_id = :pid"),
                {"curr": base_currency, "pid": int(existing_id)}
            )
            return int(existing_id)
        
        # Inserimento nuovo portafoglio univoco
        conn.execute(sqlt("""
            INSERT INTO portfolios (name, owner, base_currency, created_at)
            VALUES (:name, :owner, :curr, CURRENT_TIMESTAMP)
        """), {
            "name": name,
            "owner": owner,
            "curr": base_currency
        })
        
        try:
            if hasattr(conn, "dialect") and conn.dialect.name == "sqlite":
                new_id = conn.execute(sqlt("SELECT last_insert_rowid()")).scalar()
            else:
                new_id = conn.execute(sqlt("SELECT LAST_INSERT_ID()")).scalar()
        except Exception:
            new_id = None
            
        if not new_id:
            new_id = conn.execute(
                sqlt("SELECT portfolio_id FROM portfolios WHERE name = :n ORDER BY portfolio_id DESC LIMIT 1"),
                {"n": name}
            ).scalar()
            
        return int(new_id or 1)

    from sqlalchemy.engine import Engine, Connection
    if isinstance(engine_or_conn, Connection):
        return _execute_with_conn(engine_or_conn)
    elif isinstance(engine_or_conn, Engine) or hasattr(engine_or_conn, "connect"):
        with engine_or_conn.begin() as conn:
            return _execute_with_conn(conn)
    else:
        return _execute_with_conn(engine_or_conn)


def save_snapshot_to_db(results: dict, engine, portfolio_id: int, run_id: str, run_name: str = None):
    """
    Salva i risultati analitici e quantitativi del portafoglio nel database.
    """
    ensure_snapshot_tables(engine)
    
    m   = results.get("metrics", {})
    ret = m.get("returns", {})
    mk  = m.get("market_risk", {})
    con = m.get("concentration", {})
    ai  = m.get("ai_insights", {})
    mc  = ai.get("montecarlo", {})
    clusters = ai.get("asset_clusters", [])
    pos = results.get("positions", pd.DataFrame())
    
    risk_contrib = results.get("risk_contribution", {})
    stress_tests = results.get("stress_tests", {})
    yield_params = results.get("yield_curve_params", {})
    options_hedging = results.get("options_hedging", {})
    cc_data = options_hedging.get("covered_call", {}) if isinstance(options_hedging, dict) else {}
    
    garch_data = results.get("garch_fhs", {})
    regime_data = results.get("regime_summary", {})
    tax_data = results.get("tax_summary", {})
    closed_data = results.get("closed_trades", {})
    fi_data = results.get("fixed_income_summary", {})

    # 1. Inserimento Macro-Metriche (portfolio_snapshots)
    insert_snapshot = """
        INSERT INTO portfolio_snapshots (
            calc_date, run_id, run_name, portfolio_id, total_value, total_pnl, cagr_pct, sharpe_ratio, 
            max_drawdown_pct, var_95_pct, hhi_index, mc_expected_return_1y, mc_var_95,
            sortino_ratio, calmar_ratio, alpha_pct, information_ratio, r_squared_pct,
            volatility_annual_pct, volatility_daily_pct, cvar_95_pct, var_cf_95_pct, cvar_cf_95_pct,
            var_99_pct, cvar_99_pct, omega_ratio, tail_ratio, gain_loss_ratio,
            ulcer_index, skewness, kurtosis, diversification_ratio,
            ff_alpha_pct, ff_beta_mkt, smb_tilt, hml_tilt, risk_free_rate_pct,
            cost_basis_total, unrealized_pnl_total, realized_pnl_total, dividends_total,
            benchmark_ticker, ns_beta0, ns_beta1, ns_beta2, ns_tau,
            covered_call_income_eur, covered_call_contracts,
            garch_vol_current_pct, current_regime, regime_crisis_probability,
            accumulated_minusvalenze_eur, total_tax_due_eur, tax_drag_pct,
            closed_trades_count, win_rate_pct, profit_factor,
            portfolio_duration_modified, portfolio_convexity, portfolio_ytm_weighted_pct,
            stress_covid_loss, stress_lehman_loss, stress_rates_loss, var_exceptions_count,
            opt_max_sharpe_ratio, opt_max_sharpe_return, opt_max_sharpe_risk,
            opt_min_vol_ratio, opt_min_vol_return, opt_min_vol_risk
        ) VALUES (
            CURRENT_TIMESTAMP, :rid, :rname, :pid, :val, :pnl, :cagr, :sharpe,
            :mdd, :var, :hhi, :mc_ret, :mc_var,
            :sortino, :calmar, :alpha, :info_r, :rsq,
            :vol_ann, :vol_day, :cvar95, :var_cf, :cvar_cf,
            :var99, :cvar99, :omega_r, :tail_r, :gl_ratio,
            :ulcer, :skew, :kurt, :dr,
            :ff_a, :ff_b, :smb, :hml, :rf,
            :cost_b, :unreal_pnl, :real_pnl, :divs_tot,
            :bm, :ns_b0, :ns_b1, :ns_b2, :ns_t,
            :cc_inc, :cc_cnt,
            :garch_v, :regime_cur, :regime_prob,
            :minus_acc, :tax_due, :tax_drag,
            :closed_cnt, :win_rate, :prof_fact,
            :fi_dur, :fi_conv, :fi_ytm,
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
            "val":    _safe_float(ret.get("portfolio_value", results.get("portfolio_value")), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "pnl":    _safe_float(ret.get("total_pnl"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "cagr":   _safe_float(ret.get("cagr_pct")),
            "sharpe": _safe_float(ret.get("sharpe_ratio", mk.get("sharpe_ratio"))),
            "mdd":    _safe_float(mk.get("max_drawdown_pct")),
            "var":    _safe_float(mk.get("var_95")),
            "hhi":    _safe_float(con.get("hhi", con.get("hhi_index"))),
            "mc_ret": _safe_float(mc.get("expected_return_1y_pct")),
            "mc_var": _safe_float(mc.get("var_95_simulated_pct")),
            "sortino": _safe_float(ret.get("sortino_ratio")),
            "calmar": _safe_float(ret.get("calmar_ratio")),
            "alpha":  _safe_float(ret.get("alpha_pct")),
            "info_r": _safe_float(ret.get("information_ratio")),
            "rsq":    _safe_float(mk.get("r_squared_pct")),
            
            # Rischio e Distribuzione
            "vol_ann": _safe_float(mk.get("volatility_annual_pct", mk.get("volatility_pct"))),
            "vol_day": _safe_float(mk.get("volatility_daily_pct")),
            "cvar95":  _safe_float(mk.get("cvar_95")),
            "var_cf":  _safe_float(mk.get("var_cf_95")),
            "cvar_cf": _safe_float(mk.get("cvar_cf_95")),
            "var99":   _safe_float(mk.get("var_99")),
            "cvar99":  _safe_float(mk.get("cvar_99")),
            "omega_r": _safe_float(mk.get("omega_ratio")),
            "tail_r":  _safe_float(mk.get("tail_ratio")),
            "gl_ratio": _safe_float(mk.get("gain_loss_ratio")),
            "ulcer":   _safe_float(mk.get("ulcer_index")),
            "skew":    _safe_float(mk.get("skewness")),
            "kurt":    _safe_float(mk.get("kurtosis")),
            "dr":      _safe_float(con.get("diversification_ratio", mk.get("diversification_ratio", 1.0))),
            
            # Fattori Fama-French & Risk-Free
            "ff_a": _safe_float(mk.get("ff_alpha_pct", ret.get("alpha_pct"))),
            "ff_b": _safe_float(mk.get("ff_beta_mkt", mk.get("beta"))),
            "smb":  _safe_float(mk.get("smb_tilt")),
            "hml":  _safe_float(mk.get("hml_tilt")),
            "rf":   _safe_float(results.get("risk_free", {}).get("rate_pct", ret.get("risk_free_rate_pct"))),
            
            # Contabilità Aggregata
            "cost_b":     _safe_float(ret.get("cost_basis_total"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "unreal_pnl": _safe_float(ret.get("unrealized_pnl_total"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "real_pnl":   _safe_float(ret.get("realized_pnl_total"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "divs_tot":   _safe_float(ret.get("dividends_total"), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "bm":         str(results.get("benchmark", mk.get("benchmark_ticker", "SPY"))),
            
            # Parametri Term Structure Nelson-Siegel
            "ns_b0": _safe_float(yield_params.get("beta0")),
            "ns_b1": _safe_float(yield_params.get("beta1")),
            "ns_b2": _safe_float(yield_params.get("beta2")),
            "ns_t":  _safe_float(yield_params.get("tau")),
            
            # Opzioni Covered Call
            "cc_inc": _safe_float(cc_data.get("incasso_eseguibile_eur", cc_data.get("incasso_totale_eur")), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "cc_cnt": int(cc_data.get("contratti_eseguibili", 0)) if cc_data.get("contratti_eseguibili") is not None else 0,

            # GARCH, Regimi & Fisco
            "garch_v":     _safe_float(garch_data.get("kpis", {}).get("current_annual_vol_pct", garch_data.get("current_volatility_pct", garch_data.get("garch_vol_current_pct")))),
            "regime_cur":  str(regime_data.get("current_regime", "Normal")),
            "regime_prob": _safe_float(regime_data.get("regime_crisis_probability")),
            "minus_acc":   _safe_float(tax_data.get("accumulated_minusvalenze_eur", tax_data.get("minusvalenze_totali_eur")), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "tax_due":     _safe_float(tax_data.get("total_tax_due_eur", tax_data.get("imposta_totale_dovuta_eur")), MAX_DECIMAL_18, MIN_DECIMAL_18),
            "tax_drag":    _safe_float(tax_data.get("tax_drag_pct")),

            # Closed Trades Journal
            "closed_cnt": int(closed_data.get("summary", {}).get("total_trades", closed_data.get("closed_trades_count", 0)) or 0),
            "win_rate":   _safe_float(closed_data.get("summary", {}).get("win_rate_pct", closed_data.get("win_rate_pct"))),
            "prof_fact":  _safe_float(closed_data.get("summary", {}).get("profit_factor", closed_data.get("profit_factor"))),

            # Fixed Income
            "fi_dur":  _safe_float(fi_data.get("portfolio_duration_modified", fi_data.get("modified_duration"))),
            "fi_conv": _safe_float(fi_data.get("portfolio_convexity", fi_data.get("convexity"))),
            "fi_ytm":  _safe_float(fi_data.get("portfolio_ytm_weighted_pct", fi_data.get("weighted_ytm_pct"))),

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
        
        # Recupero ID generato compatibile sia con SQLite che MySQL
        try:
            if hasattr(engine, "dialect") and engine.dialect.name == "sqlite":
                snapshot_id = conn.execute(sqlt("SELECT last_insert_rowid()")).scalar()
            else:
                snapshot_id = conn.execute(sqlt("SELECT LAST_INSERT_ID()")).scalar()
        except Exception:
            snapshot_id = None

        if not snapshot_id:
            snapshot_id = conn.execute(sqlt("SELECT MAX(snapshot_id) FROM portfolio_snapshots")).scalar()

        # Lookup cluster e volatilità
        cl_map = {}
        for c in clusters:
            tk = c.get("ticker", c.get("index"))
            cl_map[tk] = {
                "volatility": c.get("volatility", 0) * 100,
                "cluster": f"Cluster {c.get('cluster', 0)}"
            }
        
        # Lookup Beta da Stress Test
        betas = {}
        covid_details = stress_tests.get("COVID-19 Crash (Feb-Mar 2020)", {}).get("details", {})
        for tk, tk_data in covid_details.items():
            betas[tk] = tk_data.get("beta")
            
        # Lookup Risk Contribution
        rc_marginal = risk_contrib.get("marginal_var", {}) if isinstance(risk_contrib, dict) else {}
        rc_component = risk_contrib.get("component_var_pct", {}) if isinstance(risk_contrib, dict) else {}
        if not rc_component and isinstance(risk_contrib, dict):
            rc_component = risk_contrib
        
        # 2. Inserimento Posizioni (snapshot_positions)
        insert_pos = """
            INSERT INTO snapshot_positions (
                snapshot_id, ticker, asset_class, sector, country, currency,
                qty_net, avg_cost, cost_basis,
                last_price, current_value, unrealized_pnl, realized_pnl, dividends_total, total_return, yield_on_cost_pct, weight_pct, 
                volatility_pct, cluster_label, days_to_liquidate,
                trailing_pe, forward_pe, price_to_book, dividend_yield, roe, 
                target_mean_price, peg_ratio,
                marginal_var_pct, component_var_pct, beta_vs_benchmark, opt_weight_pct,
                altman_z_score, piotroski_f_score, beneish_m_score, sloan_accrual_ratio,
                ev_to_ebitda, free_cash_flow_yield, debt_to_equity,
                atr_14_eur, chandelier_exit_long_eur, rsi_14
            ) VALUES (
                :sid, :tk, :ac, :sec, :cntry, :curr,
                :qty, :avgc, :cb,
                :lp, :cval, :upnl, :rpnl, :divs, :tot_ret, :yoc, :wpct,
                :vol, :cl, :dtl,
                :t_pe, :f_pe, :pb, :dy, :roe,
                :target, :peg,
                :mvar, :cvar, :beta, :opt_weight,
                :altman, :piotroski, :beneish, :sloan,
                :ev_ebitda, :fcf_y, :de_ratio,
                :atr, :chandelier, :rsi
            )
        """
        if isinstance(pos, pd.DataFrame) and not pos.empty:
            for _, r in pos.iterrows():
                if r.get("qty_net", 1) <= 0 and r.get("current_value", 0) <= 0:
                    continue
                
                tk = r["ticker"]
                tk_metrics = cl_map.get(tk, {})

                mvar_val = r.get("marginal_var_pct") if pd.notna(r.get("marginal_var_pct")) else rc_marginal.get(tk)
                cvar_val = r.get("component_var_pct") if pd.notna(r.get("component_var_pct")) else rc_component.get(tk)
                
                conn.execute(sqlt(insert_pos), {
                    "sid":  snapshot_id,
                    "tk":   tk,
                    "ac":   r.get("asset_class"),
                    "sec":  r.get("sector", r.get("gics_sector")),
                    "cntry": r.get("country"),
                    "curr": r.get("currency"),
                    "qty":  _safe_float(r.get("qty_net"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "avgc": _safe_float(r.get("avg_cost"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "cb":   _safe_float(r.get("cost_basis"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "lp":   _safe_float(r.get("last_price"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "cval": _safe_float(r.get("current_value"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "upnl": _safe_float(r.get("unrealized_pnl"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "rpnl": _safe_float(r.get("realized_pnl"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "divs": _safe_float(r.get("dividends_total"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "tot_ret": _safe_float(r.get("total_return", (r.get("unrealized_pnl", 0) or 0) + (r.get("realized_pnl", 0) or 0)), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "yoc":  _safe_float(r.get("yield_on_cost_pct")),
                    "wpct": _safe_float(r.get("weight_pct")),
                    "vol":  _safe_float(tk_metrics.get("volatility", r.get("volatility_pct"))),
                    "cl":   tk_metrics.get("cluster", r.get("cluster_label")),
                    "dtl":  _safe_float(r.get("days_to_liquidate")),
                    
                    "t_pe":   _safe_float(r.get("trailing_pe")),
                    "f_pe":   _safe_float(r.get("forward_pe")),
                    "pb":     _safe_float(r.get("price_to_book")),
                    "dy":     _safe_float(r.get("dividend_yield")),
                    "roe":    _safe_float(r.get("roe")),
                    "target": _safe_float(r.get("target_mean_price"), MAX_DECIMAL_18, MIN_DECIMAL_18),
                    "peg":    _safe_float(r.get("peg_ratio")),
                    
                    "mvar":   _safe_float(mvar_val),
                    "cvar":   _safe_float(cvar_val),
                    "beta":   _safe_float(r.get("beta", betas.get(tk))),
                    "opt_weight": _safe_float(
                        results.get("optimization", {}).get("max_sharpe", {}).get("weights", [])[
                            results.get("optimization", {}).get("tickers", []).index(tk)
                        ] * 100 
                        if results.get("optimization") and tk in results.get("optimization", {}).get("tickers", []) 
                        else None
                    ),

                    # Metriche Forensi & Analisi Tecnica
                    "altman":    _safe_float(r.get("altman_z_score", r.get("altman_z"))),
                    "piotroski": _safe_float(r.get("piotroski_f_score", r.get("piotroski_score"))),
                    "beneish":   _safe_float(r.get("beneish_m_score", r.get("beneish_m"))),
                    "sloan":     _safe_float(r.get("sloan_accrual_ratio", r.get("sloan_accrual"))),
                    "ev_ebitda": _safe_float(r.get("ev_to_ebitda", r.get("enterprise_to_ebitda"))),
                    "fcf_y":     _safe_float(r.get("free_cash_flow_yield", r.get("fcf_yield"))),
                    "de_ratio":  _safe_float(r.get("debt_to_equity")),
                    "atr":       _safe_float(r.get("atr_14_eur", r.get("atr_14"))),
                    "chandelier": _safe_float(r.get("chandelier_exit_long_eur", r.get("chandelier_exit"))),
                    "rsi":       _safe_float(r.get("rsi_14", r.get("rsi")))
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
            s.volatility_annual_pct, s.volatility_daily_pct, s.cvar_95_pct, s.var_cf_95_pct, s.cvar_cf_95_pct,
            s.var_99_pct, s.cvar_99_pct, s.omega_ratio, s.tail_ratio, s.gain_loss_ratio,
            s.ulcer_index, s.skewness, s.kurtosis, s.diversification_ratio,
            s.ff_alpha_pct, s.ff_beta_mkt, s.smb_tilt, s.hml_tilt, s.risk_free_rate_pct,
            s.cost_basis_total, s.unrealized_pnl_total, s.realized_pnl_total, s.dividends_total,
            s.benchmark_ticker, s.ns_beta0, s.ns_beta1, s.ns_beta2, s.ns_tau,
            s.covered_call_income_eur, s.covered_call_contracts,
            s.garch_vol_current_pct, s.current_regime, s.regime_crisis_probability,
            s.accumulated_minusvalenze_eur, s.total_tax_due_eur, s.tax_drag_pct,
            s.closed_trades_count, s.win_rate_pct, s.profit_factor,
            s.portfolio_duration_modified, s.portfolio_convexity, s.portfolio_ytm_weighted_pct,
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
