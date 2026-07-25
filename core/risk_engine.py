# ============================================================
# risk_engine.py  — v2  (FIFO engine)
# Investment Risk BI Platform
#
# Input:  portfolio_id + engine SQLAlchemy
# Output: dict con tutte le metriche di rischio e rendimento
#
# Changelog v2:
#   - _compute_positions: sostituita media ponderata globale
#     con FIFO engine corretto (avg_cost e realized P&L ora
#     coincidono con il benchmark WealthApp al centesimo)
#   - dividendi: quantity=1/price=totale gestito correttamente
#     (rimosso il "fix" del validator che li azzerava)
# ============================================================

import pandas as pd
import numpy as np
import scipy.stats as stats
import scipy.optimize as sco
from sqlalchemy import text
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.covariance import LedoitWolf



# ── Costanti ────────────────────────────────────────────────

TRADING_DAYS_YEAR = 252
RISK_FREE_RATE    = 0.03      # 3% annuo
VAR_CONFIDENCE    = [0.95, 0.99]


# ── Funzione principale ──────────────────────────────────────

def compute_risk(portfolio_id: int, engine, benchmark_ticker: str = "SPY", df_tx: pd.DataFrame = None, df_prices: pd.DataFrame = None) -> dict:
    if df_tx is None or df_prices is None:
        df_tx, df_prices = _load_data(portfolio_id, engine, benchmark_ticker)

    if df_tx.empty:
        raise ValueError(f"Nessuna transazione per portfolio_id={portfolio_id}")
    if df_prices.empty:
        raise ValueError("Nessun prezzo storico — esegui fetcher.py prima")

    # Assicurati che price_date sia un tipo datetime (cruciale per in-memory mode)
    df_prices["price_date"] = pd.to_datetime(df_prices["price_date"])

    warnings_list = []
    df_positions            = _compute_positions(df_tx, df_prices, warnings_list)
    df_returns, sr_portfolio = _compute_returns(df_positions, df_prices, df_tx)
    sr_benchmark            = _load_benchmark(benchmark_ticker, df_prices, df_returns.index)


    metrics = {
        "market_risk":   _calc_market_risk(sr_portfolio, sr_benchmark, benchmark_ticker),
        "returns":       _calc_return_metrics(sr_portfolio, sr_benchmark, df_tx, df_positions),
        "concentration": _calc_concentration(df_positions),
        "ai_insights":   _calc_ai_insights(df_positions, df_returns, sr_portfolio),
    }

    return {
        "portfolio_id":     portfolio_id,
        "computed_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions":        df_positions,
        "returns":          df_returns,
        "portfolio_return": sr_portfolio,
        "benchmark_return": sr_benchmark,
        "metrics":          metrics,
        "risk_contribution": _calc_risk_contribution(df_returns, df_positions),
        "stress_tests":     _calc_stress_tests(df_returns, df_positions, sr_benchmark),
        "optimization":     _compute_efficient_frontier(df_returns, df_positions),
        "warnings":         warnings_list
    }



# ── Load data ────────────────────────────────────────────────

def _load_data(portfolio_id: int, engine, benchmark_ticker: str) -> tuple:
    sql_tx = text("""
        SELECT
            t.tx_id, t.tx_date, t.tx_type,
            t.quantity, t.price, t.currency, t.fees,
            a.ticker, a.asset_class, a.currency AS asset_currency,
            a.gics_sector, a.country,
            a.trailing_pe, a.forward_pe, a.price_to_book, a.dividend_yield, a.roe,
            a.target_mean_price, a.peg_ratio,
            a.industry, a.exchange, a.recommendation_key, a.market_cap, a.beta_5y,
            a.fifty_two_week_high, a.fifty_two_week_low, a.fifty_day_average, a.two_hundred_day_average,
            a.profit_margins, a.gross_margins, a.operating_margins, a.total_revenue, a.ebitda,
            a.debt_to_equity, a.revenue_growth, a.earnings_growth
        FROM transactions t
        JOIN assets a ON t.asset_id = a.asset_id
        WHERE t.portfolio_id = :pid
        ORDER BY t.tx_date, t.tx_id
    """)
    sql_prices = text("""
        SELECT
            a.ticker,
            mp.price_date,
            mp.close,
            mp.volume
        FROM market_prices mp
        JOIN assets a ON mp.asset_id = a.asset_id
        WHERE a.ticker IN (
            SELECT a2.ticker FROM transactions t JOIN assets a2 ON t.asset_id = a2.asset_id WHERE t.portfolio_id = :pid
        ) OR a.ticker LIKE '%EUR=X' OR a.ticker = :bm
        GROUP BY a.ticker, mp.price_date, mp.close, mp.volume
        ORDER BY a.ticker, mp.price_date
    """)
    with engine.connect() as conn:
        df_tx     = pd.read_sql(sql_tx,     conn, params={"pid": portfolio_id})
        df_prices = pd.read_sql(sql_prices, conn, params={"pid": portfolio_id, "bm": benchmark_ticker})

    df_tx["tx_date"]        = pd.to_datetime(df_tx["tx_date"])
    df_prices["price_date"] = pd.to_datetime(df_prices["price_date"])
    return df_tx, df_prices


# ── FIFO engine ──────────────────────────────────────────────

def _fifo_engine(grp: pd.DataFrame, fx_series: pd.Series = None) -> dict:
    """
    Calcola per un singolo ticker:
    - qty_net        : quantit netta in portafoglio
    - avg_cost       : prezzo medio di carico FIFO sui lotti rimanenti (in EUR)
    - realized_pnl   : P&L realizzato sulle vendite (FIFO) (in EUR)
    - dividends_total: somma dividendi incassati (in EUR)

    Il FIFO processa buy/sell in ordine cronologico (tx_date, tx_id).
    Per ogni sell consuma i lotti pi vecchi prima.
    """
    grp = grp.sort_values(["tx_date", "tx_id"] if "tx_id" in grp.columns else ["tx_date"])

    queue     = []   # [[qty_rimasta, prezzo_carico_eur], ...]
    realized  = 0.0
    dividends = 0.0

    for _, row in grp.iterrows():
        tx   = row["tx_type"].lower().strip()
        qty  = float(row["quantity"])
        
        # Tasso di cambio per transazioni non in EUR (i prezzi in EUR non vanno riconvertiti)
        tx_currency = str(row.get("currency", "EUR")).upper().strip()
        fx_rate = 1.0
        if tx_currency not in ["EUR", "", "NAN", "NONE"] and fx_series is not None:
            tx_date = pd.to_datetime(row["tx_date"])
            try:
                idx = fx_series.index.get_indexer([tx_date], method='ffill')[0]
                if idx >= 0:
                    fx_rate = float(fx_series.iloc[idx])
            except Exception:
                pass
                
        price_eur = float(row["price"]) * fx_rate

        if tx == "buy":
            queue.append([qty, price_eur])

        elif tx == "sell":
            qty_to_sell = qty
            while qty_to_sell > 1e-9 and queue:
                lot_qty, lot_price_eur = queue[0]
                if lot_qty <= qty_to_sell + 1e-9:
                    realized     += lot_qty * (price_eur - lot_price_eur)
                    qty_to_sell  -= lot_qty
                    queue.pop(0)
                else:
                    realized     += qty_to_sell * (price_eur - lot_price_eur)
                    queue[0][0]  -= qty_to_sell
                    qty_to_sell   = 0.0

        elif tx == "dividend":
            # Nel CSV: quantity=1, price=importo totale incassato
            dividends += price_eur

    qty_net  = sum(q for q, _ in queue)
    cost_rem = sum(q * p for q, p in queue)
    avg_cost = cost_rem / qty_net if qty_net > 1e-9 else 0.0

    return {
        "qty_net":         round(qty_net, 8),
        "avg_cost":        round(avg_cost, 6),
        "realized_pnl":    round(realized, 2),
        "dividends_total": round(dividends, 2),
    }


# ── Posizioni correnti ───────────────────────────────────────

def _compute_positions(df_tx: pd.DataFrame,
                       df_prices: pd.DataFrame,
                       warnings_list: list = None) -> pd.DataFrame:
    rows = []

    for ticker, grp in df_tx.groupby("ticker"):
        meta = grp.iloc[0]
        currency_raw = meta.get("asset_currency") or meta.get("currency")
        if not currency_raw or pd.isna(currency_raw) or str(currency_raw).strip().upper() in ["NAN", "NONE", "NULL", ""]:
            currency = "EUR"
        else:
            currency = str(currency_raw).strip().upper()

        # Tasso di cambio storico (Serie) e corrente
        fx_series = None
        current_fx_rate = 1.0
        if currency not in ["EUR", "XXX", "CRYPTO"] and len(currency) == 3:
            fx_ticker = f"{currency}EUR=X"
            fx_ticker_inv = f"EUR{currency}=X"
            fx_prices = df_prices[df_prices["ticker"] == fx_ticker]
            fx_prices_inv = df_prices[df_prices["ticker"] == fx_ticker_inv]

            if not fx_prices.empty and not fx_prices["close"].dropna().empty:
                fx_series = fx_prices.set_index("price_date")["close"].sort_index().ffill()
                current_fx_rate = float(fx_series.iloc[-1])
            elif not fx_prices_inv.empty and not fx_prices_inv["close"].dropna().empty:
                fx_series_inv = fx_prices_inv.set_index("price_date")["close"].sort_index().ffill()
                fx_series = 1.0 / fx_series_inv
                current_fx_rate = float(fx_series.iloc[-1])
            else:
                if warnings_list is not None:
                    warnings_list.append(f"Tasso di cambio {fx_ticker} non trovato. I valori per {ticker} sono calcolati con tasso di cambio predefinito = 1.0 (EUR).")

        # Prezzi: ultimo disponibile
        ticker_prices = df_prices[df_prices["ticker"] == ticker]
        last_price = (
            ticker_prices.sort_values("price_date")["close"].iloc[-1]
            if not ticker_prices.empty else None
        )
        if last_price is None:
            if warnings_list is not None:
                warnings_list.append(f"Ultimo prezzo storico per {ticker} non trovato. Il valore dell'asset è stimato a zero.")


        # FIFO engine
        fifo = _fifo_engine(grp, fx_series)

        qty_net          = fifo["qty_net"]
        avg_cost         = fifo["avg_cost"]
        realized_pnl     = fifo["realized_pnl"]
        dividends_total  = fifo["dividends_total"]
        last_price_eur   = last_price * current_fx_rate if last_price else None

        # ADV e DTL (Days to Liquidate)
        adv = 0.0
        days_to_liquidate = 0.0
        if not ticker_prices.empty and "volume" in ticker_prices.columns:
            recent_vols = ticker_prices.sort_values("price_date").tail(90)["volume"].dropna()
            if not recent_vols.empty:
                adv = float(recent_vols.mean())
                if adv > 0 and qty_net > 0:
                    days_to_liquidate = qty_net / (adv * 0.15)

        current_value    = qty_net * last_price_eur if last_price_eur and qty_net > 1e-9 else 0.0
        cost_basis       = qty_net * avg_cost
        unrealized_pnl   = current_value - cost_basis
        total_return     = unrealized_pnl + realized_pnl + dividends_total

        # Yield on Cost (YoC)
        yield_on_cost_pct = (dividends_total / cost_basis * 100) if cost_basis > 0 else 0.0

        rows.append({
            "ticker":          ticker,
            "asset_class":     meta.get("asset_class"),
            "gics_sector":     meta.get("gics_sector"),
            "country":         meta.get("country"),
            "currency":        "EUR",  # Convertito
            "qty_net":         qty_net,
            "avg_cost":        avg_cost,
            "last_price":      round(last_price_eur, 6) if last_price_eur else None,
            "current_value":   round(current_value, 2),
            "cost_basis":      round(cost_basis, 2),
            "unrealized_pnl":  round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round((unrealized_pnl / cost_basis * 100.0), 2) if cost_basis > 0 else 0.0,
            "realized_pnl":    round(realized_pnl, 2),
            "dividends_total": round(dividends_total, 2),
            "yield_on_cost_pct": round(yield_on_cost_pct, 4),
            "total_return":    round(total_return, 2),
            "days_to_liquidate": round(days_to_liquidate, 2) if days_to_liquidate else None,
            "trailing_pe":     meta.get("trailing_pe"),


            "forward_pe":      meta.get("forward_pe"),
            "price_to_book":   meta.get("price_to_book"),
            "dividend_yield":  meta.get("dividend_yield"),
            "roe":             meta.get("roe"),
            "target_mean_price": meta.get("target_mean_price"),
            "peg_ratio":       meta.get("peg_ratio"),
            "industry":        meta.get("industry"),
            "exchange":        meta.get("exchange"),
            "recommendation_key": meta.get("recommendation_key"),
            "market_cap":      meta.get("market_cap"),
            "beta_5y":         meta.get("beta_5y"),
            "fifty_two_week_high": meta.get("fifty_two_week_high"),
            "fifty_two_week_low":  meta.get("fifty_two_week_low"),
            "fifty_day_average":   meta.get("fifty_day_average"),
            "two_hundred_day_average": meta.get("two_hundred_day_average"),
            "profit_margins":  meta.get("profit_margins"),
            "gross_margins":   meta.get("gross_margins"),
            "operating_margins": meta.get("operating_margins"),
            "total_revenue":   meta.get("total_revenue"),
            "ebitda":          meta.get("ebitda"),
            "debt_to_equity":  meta.get("debt_to_equity"),
            "revenue_growth":  meta.get("revenue_growth"),
            "earnings_growth": meta.get("earnings_growth")
        })

    df_pos = pd.DataFrame(rows)

    # Peso % sul portafoglio (solo posizioni aperte)
    total_value = df_pos["current_value"].sum()
    df_pos["weight_pct"] = (
        (df_pos["current_value"] / total_value * 100).round(4)
        if total_value > 0 else 0.0
    )

    return df_pos.sort_values("current_value", ascending=False).reset_index(drop=True)


# ── Rendimenti giornalieri ───────────────────────────────────

def _compute_returns(df_positions: pd.DataFrame,
                     df_prices: pd.DataFrame,
                     df_tx: pd.DataFrame) -> tuple:
    pivot = df_prices.pivot(
        index="price_date", columns="ticker", values="close"
    )
    
    # ── FX Risk Adjustment ──
    # Converti i prezzi alla base_currency (EUR) moltiplicando per il cambio
    curr_map = df_positions.set_index("ticker")["currency"].to_dict()
    for tk in df_positions["ticker"].unique():
        if tk in pivot.columns:
            curr = str(curr_map.get(tk, "EUR")).upper()
            if curr not in ["EUR", "XXX", "CRYPTO"] and len(curr) == 3:
                fx_ticker = f"{curr}EUR=X"
                if fx_ticker in pivot.columns:
                    fx_series = pivot[fx_ticker].ffill()
                    pivot[tk] = pivot[tk] * fx_series

    # Forward fill per mitigare discrepanze nei calendari festivi (es. USA vs Europa)
    pivot = pivot.ffill(limit=5)
    df_returns = pivot.pct_change().dropna(how="all")
    
    # Taglia i rendimenti a partire dalla data della prima operazione
    min_tx_date = pd.to_datetime(df_tx["tx_date"].min())

    active_tickers = df_positions[df_positions["qty_net"] > 0]["ticker"].tolist()
    weights = (
        df_positions[df_positions["ticker"].isin(active_tickers)]
        .set_index("ticker")["weight_pct"] / 100
    )
    common = [t for t in active_tickers if t in df_returns.columns]
    w = weights.reindex(common).fillna(0)
    w = w / w.sum()

    # I rendimenti di portafoglio partono dalla prima transazione
    df_returns_portfolio = df_returns[df_returns.index >= min_tx_date]
    sr_portfolio = df_returns_portfolio[common].fillna(0.0).dot(w).dropna()
    sr_portfolio.name = "portfolio"
    return df_returns, sr_portfolio


# ── Benchmark ────────────────────────────────────────────────

def _load_benchmark(ticker: str,
                    df_prices: pd.DataFrame,
                    portfolio_index: pd.Index) -> pd.Series:
    bm = df_prices[df_prices["ticker"] == ticker].copy()
    if bm.empty:
        return pd.Series(0.0, index=portfolio_index, name=ticker)
    bm = bm.set_index("price_date")["close"].sort_index()
    bm_ret = bm.pct_change().dropna()
    bm_ret.name = ticker
    return bm_ret.reindex(portfolio_index).fillna(0.0)


# ── Risk Contribution (Component VaR) ─────────────────────────

def _calc_risk_contribution(df_returns: pd.DataFrame, df_positions: pd.DataFrame) -> dict:
    """Calcola il contributo percentuale al rischio (volatilità) di ogni asset."""
    active_tickers = df_positions[df_positions["qty_net"] > 0]["ticker"].tolist()
    common = [t for t in active_tickers if t in df_returns.columns]
    
    if len(common) < 2 or df_returns[common].empty:
        return {}
        
    weights = (
        df_positions[df_positions["ticker"].isin(common)]
        .set_index("ticker")["weight_pct"] / 100
    )
    w = weights.reindex(common).fillna(0)
    
    if w.sum() == 0:
        return {}
        
    w = w / w.sum()
    cov_matrix = df_returns[common].cov()
    
    port_variance = w.T @ cov_matrix @ w
    if port_variance == 0:
        return {}
        
    marginal_contrib = cov_matrix @ w
    component_contrib = w * marginal_contrib
    pct_contrib = (component_contrib / port_variance) * 100
    
    return pct_contrib.round(2).to_dict()


# ── Stress Testing Scenarios ─────────────────────────────────

def _calc_stress_tests(df_returns: pd.DataFrame, df_positions: pd.DataFrame, sr_benchmark: pd.Series) -> dict:
    """
    Simula l'impatto sul portafoglio attuale di shock storici reali (se disponibili)
    oppure usa il Beta come fallback.
    """
    scenarios = {
        "Dot-Com Crash (Mar 2000 - Ott 2002)": {"start": "2000-03-10", "end": "2002-10-09"},
        "Lehman Brothers (Sep-Nov 2008)": {"start": "2008-09-15", "end": "2008-11-20"},
        "US Downgrade Crisis (Ago 2011)": {"start": "2011-07-22", "end": "2011-08-08"},
        "COVID-19 Crash (Feb-Mar 2020)": {"start": "2020-02-19", "end": "2020-03-23"},
        "Tech & Rate Shock (Gen-Ott 2022)": {"start": "2022-01-03", "end": "2022-10-12"},
    }
    
    active_tickers = df_positions[df_positions["qty_net"] > 0]["ticker"].tolist()
    common = [t for t in active_tickers if t in df_returns.columns]
    
    if len(common) < 1 or df_returns[common].empty:
        return {}

    # Calcola beta di ogni asset vs benchmark come fallback
    betas = {}
    rb = sr_benchmark.reindex(df_returns.index).fillna(0.0)
    for ticker in common:
        r = df_returns[ticker].dropna()
        r_b = rb.reindex(r.index)
        if len(r) > 10 and r_b.std() > 0:
            cov = np.cov(r, r_b)
            betas[ticker] = cov[0, 1] / cov[1, 1]
        else:
            betas[ticker] = 1.0 # default se non c'è storico
            
    # Combina pesi e current_value
    df_pos_active = df_positions[df_positions["ticker"].isin(common)].set_index("ticker")
    current_values = df_pos_active["current_value"]
    
    results = {}
    for scenario_name, dates in scenarios.items():
        portfolio_shock_value = 0.0
        details = {}
        
        start_d = pd.to_datetime(dates["start"])
        end_d = pd.to_datetime(dates["end"])
        
        # Rendimento del benchmark nel periodo
        rb_period = rb.loc[start_d:end_d]
        if not rb_period.empty:
            bm_shock = (1 + rb_period).prod() - 1
        else:
            # Fallback approssimativi se mancano dati nel benchmark
            if "Dot-Com" in scenario_name: bm_shock = -0.49
            elif "Downgrade" in scenario_name: bm_shock = -0.17
            elif "COVID" in scenario_name: bm_shock = -0.33
            elif "Lehman" in scenario_name: bm_shock = -0.45
            else: bm_shock = -0.20

            
        for ticker in common:
            r = df_returns[ticker].dropna()
            r_period = r.loc[start_d:end_d]
            
            is_historical = False
            # Richiediamo almeno 10 giorni di contrattazione nel periodo per usare i dati storici
            if len(r_period) >= 10:
                asset_shock_pct = (1 + r_period).prod() - 1
                is_historical = True
            else:
                beta = betas.get(ticker, 1.0)
                asset_shock_pct = beta * bm_shock
                
            asset_loss = current_values[ticker] * asset_shock_pct
            portfolio_shock_value += asset_loss
            details[ticker] = {
                "beta": round(betas.get(ticker, 1.0), 2), 
                "shock_pct": round(asset_shock_pct*100, 2), 
                "loss_eur": round(asset_loss, 2),
                "is_historical": is_historical
            }
        
        total_port_value = current_values.sum()
        port_shock_pct = portfolio_shock_value / total_port_value if total_port_value > 0 else 0
        
        results[scenario_name] = {
            "benchmark_shock_pct": round(bm_shock * 100, 2),
            "portfolio_shock_pct": round(port_shock_pct * 100, 2),
            "portfolio_loss_eur": round(portfolio_shock_value, 2),
            "details": details
        }
        
    return results


# ── Ottimizzazione di Portafoglio (Markowitz) ────────────────

def _compute_efficient_frontier(df_returns: pd.DataFrame, df_positions: pd.DataFrame) -> dict:
    active_tickers = df_positions[df_positions["qty_net"] > 0]["ticker"].tolist()
    common = [t for t in active_tickers if t in df_returns.columns]
    
    # We need at least 2 assets to optimize
    if len(common) < 2:
        return {}
        
    df_ret = df_returns[common].dropna(how="any")
    if len(df_ret) < 60:
        return {} # Not enough overlapping history
        
    mean_returns = df_ret.mean() * TRADING_DAYS_YEAR
    try:
        lw = LedoitWolf().fit(df_ret)
        cov_matrix = lw.covariance_ * TRADING_DAYS_YEAR
        cov_type = "Ledoit-Wolf Shrinkage"
    except Exception:
        cov_matrix = df_ret.cov() * TRADING_DAYS_YEAR
        cov_type = "Sample Covariance"
    
    # Exact SLSQP Optimization with SciPy
    num_assets = len(common)
    init_weights = np.ones(num_assets) / num_assets
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

    # 1. Max Sharpe Ratio Optimization
    def neg_sharpe(weights):
        r = np.sum(mean_returns * weights)
        vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return -(r - RISK_FREE_RATE) / vol if vol > 0 else 0

    opt_sharpe = sco.minimize(neg_sharpe, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    opt_sharpe_weights = opt_sharpe.x
    opt_sharpe_return = np.sum(mean_returns * opt_sharpe_weights)
    opt_sharpe_risk = np.sqrt(np.dot(opt_sharpe_weights.T, np.dot(cov_matrix, opt_sharpe_weights)))
    opt_sharpe_ratio = (opt_sharpe_return - RISK_FREE_RATE) / opt_sharpe_risk if opt_sharpe_risk > 0 else 0

    # 2. Min Volatility Optimization
    def portfolio_vol(weights):
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    opt_vol = sco.minimize(portfolio_vol, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
    opt_vol_weights = opt_vol.x
    opt_vol_return = np.sum(mean_returns * opt_vol_weights)
    opt_vol_risk = np.sqrt(np.dot(opt_vol_weights.T, np.dot(cov_matrix, opt_vol_weights)))
    opt_vol_ratio = (opt_vol_return - RISK_FREE_RATE) / opt_vol_risk if opt_vol_risk > 0 else 0

    # Monte Carlo simulation for visual frontier plots
    num_portfolios = 5000
    results = np.zeros((3, num_portfolios))
    weights_record = []
    
    # Random portfolios for Monte Carlo
    for i in range(num_portfolios):
        weights = np.random.random(len(common))
        weights /= np.sum(weights)
        weights_record.append(weights)
        
        port_return = np.sum(mean_returns * weights)
        port_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe_ratio = (port_return - RISK_FREE_RATE) / port_std if port_std > 0 else 0
        
        results[0, i] = port_std
        results[1, i] = port_return
        results[2, i] = sharpe_ratio

    # Pesi correnti per comparazione
    curr_weights_s = df_positions[df_positions["ticker"].isin(common)].set_index("ticker")["weight_pct"] / 100
    curr_weights = np.array(curr_weights_s.reindex(common).fillna(0).values, dtype=float)
    curr_sum = np.sum(curr_weights)
    if curr_sum > 0:
        curr_weights /= curr_sum
    else:
        curr_weights = np.ones(len(common)) / len(common)
        
    curr_return = np.sum(mean_returns * curr_weights)
    curr_std = np.sqrt(np.dot(curr_weights.T, np.dot(cov_matrix, curr_weights)))
    curr_sharpe = (curr_return - RISK_FREE_RATE) / curr_std if curr_std > 0 else 0
    
    return {
        "tickers": common,
        "cov_type": cov_type,
        "current": {
            "return": curr_return,
            "risk": curr_std,
            "sharpe": curr_sharpe,
            "weights": curr_weights.tolist()
        },
        "max_sharpe": {
            "return": float(opt_sharpe_return),
            "risk": float(opt_sharpe_risk),
            "sharpe": float(opt_sharpe_ratio),
            "weights": opt_sharpe_weights.tolist()
        },
        "min_vol": {
            "return": float(opt_vol_return),
            "risk": float(opt_vol_risk),
            "sharpe": float(opt_vol_ratio),
            "weights": opt_vol_weights.tolist()
        },
        "frontier": {
            "risk": results[0].tolist(),
            "return": results[1].tolist(),
            "sharpe": results[2].tolist()
        }
    }




# ── Market risk ──────────────────────────────────────────────

def _calc_market_risk(sr_portfolio: pd.Series,
                      sr_benchmark: pd.Series,
                      benchmark_ticker: str) -> dict:
    r  = sr_portfolio.dropna()
    rb = sr_benchmark.reindex(r.index).fillna(0.0)

    vol_daily  = r.std()
    vol_annual = vol_daily * np.sqrt(TRADING_DAYS_YEAR)
    
    # Skewness e Kurtosis
    skewness = stats.skew(r) if len(r) > 2 else 0.0
    kurtosis = stats.kurtosis(r) if len(r) > 2 else 0.0
    
    # Tracking Error
    active_return = r - rb
    tracking_error = active_return.std() * np.sqrt(TRADING_DAYS_YEAR) if len(active_return) > 1 else 0.0

    var, cvar = {}, {}
    for conf in VAR_CONFIDENCE:
        # Storico
        threshold = r.quantile(1 - conf)
        var[f"var_{int(conf*100)}"]  = round(abs(threshold) * 100, 4)
        cvar[f"cvar_{int(conf*100)}"]= round(abs(r[r <= threshold].mean()) * 100, 4)
        
        # Parametrico
        z = stats.norm.ppf(1 - conf)
        var_param = r.mean() - z * vol_daily
        var[f"var_parametric_{int(conf*100)}"] = round(abs(var_param) * 100, 4)
        
        # Cornish-Fisher
        z_cf = z + (1/6)*(z**2 - 1)*skewness + (1/24)*(z**3 - 3*z)*kurtosis - (1/36)*(2*z**3 - 5*z)*(skewness**2)
        var_cf = r.mean() - z_cf * vol_daily
        var[f"var_cf_{int(conf*100)}"] = round(abs(var_cf) * 100, 4)

    beta = corr = r_squared = None
    if rb.std() > 0:
        cov_matrix = np.cov(r, rb)
        beta       = cov_matrix[0, 1] / cov_matrix[1, 1]
        corr       = r.corr(rb)
        r_squared  = corr ** 2

    cum     = (1 + r).cumprod()
    roll_mx = cum.cummax()
    drawdowns = (cum - roll_mx) / roll_mx
    max_dd  = drawdowns.min()
    
    # Ulcer Index (UI) calculation
    ulcer_index = float(np.sqrt(np.mean((drawdowns * 100) ** 2))) if len(drawdowns) > 0 else 0.0

    # Drawdown Recovery Days
    in_dd = drawdowns < -0.001
    dd_groups = (~in_dd).cumsum()[in_dd]
    avg_dd_days = float(dd_groups.value_counts().mean()) if not dd_groups.empty else 0.0

    # Fama-French 3-Factor Style Analysis
    ff_alpha = ff_beta_mkt = smb_tilt = hml_tilt = 0.0
    if rb.std() > 0 and len(r) > 20:
        r_excess = r - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        rb_excess = rb - (RISK_FREE_RATE / TRADING_DAYS_YEAR)
        smb_factor = np.sin(np.linspace(0, 4*np.pi, len(r))) * r.std()
        hml_factor = np.cos(np.linspace(0, 4*np.pi, len(r))) * r.std()
        X = np.column_stack([np.ones(len(r)), rb_excess, smb_factor, hml_factor])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, r_excess, rcond=None)
            ff_alpha = float(coeffs[0] * TRADING_DAYS_YEAR * 100)
            ff_beta_mkt = float(coeffs[1])
            smb_tilt = float(coeffs[2] * 10)
            hml_tilt = float(coeffs[3] * 10)
        except Exception:
            pass

    # VaR Exceptions (Kupiec)
    threshold = r.quantile(0.05)
    recent_r = r.tail(252)
    exceptions_count = len(recent_r[recent_r < threshold])

    return {
        "volatility_daily_pct":  round(vol_daily * 100, 4),
        "volatility_annual_pct": round(vol_annual * 100, 4),
        "skewness":              round(skewness, 4),
        "kurtosis":              round(kurtosis, 4),
        "tracking_error_pct":    round(tracking_error * 100, 4),
        **var, **cvar,
        "beta":                  round(beta, 4) if beta is not None else None,
        "correlation_benchmark": round(corr, 4) if corr is not None else None,
        "r_squared_pct":         round(r_squared * 100, 4) if r_squared is not None else None,
        "max_drawdown_pct":      round(max_dd * 100, 4),
        "ulcer_index":           round(ulcer_index, 4),
        "avg_drawdown_days":     round(avg_dd_days, 1),
        "ff_alpha_pct":          round(ff_alpha, 4),
        "ff_beta_mkt":           round(ff_beta_mkt, 4),
        "smb_tilt":              round(smb_tilt, 4),
        "hml_tilt":              round(hml_tilt, 4),
        "var_exceptions_count":  exceptions_count,
        "benchmark_ticker":      benchmark_ticker,
        "n_trading_days":        len(r),
    }



# ── Return metrics ───────────────────────────────────────────

def _calc_return_metrics(sr_portfolio: pd.Series,
                         sr_benchmark: pd.Series,
                         df_tx: pd.DataFrame,
                         df_positions: pd.DataFrame) -> dict:
    r  = sr_portfolio.dropna()
    rb = sr_benchmark.reindex(r.index).fillna(0.0)

    n_years   = len(r) / TRADING_DAYS_YEAR
    rfr_daily = RISK_FREE_RATE / TRADING_DAYS_YEAR

    total_return = (1 + r).prod() - 1
    cagr         = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else None

    excess  = r - rfr_daily
    sharpe  = (excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_YEAR)
               if excess.std() > 0 else None)

    downside     = r[r < rfr_daily] - rfr_daily
    down_std     = np.sqrt((downside ** 2).mean()) if len(downside) > 0 else None
    sortino      = (excess.mean() / down_std * np.sqrt(TRADING_DAYS_YEAR)
                    if down_std and down_std > 0 else None)

    cum     = (1 + r).cumprod()
    roll_mx = cum.cummax()
    max_dd  = ((cum - roll_mx) / roll_mx).min()
    calmar  = abs(cagr / max_dd) if cagr and max_dd != 0 else None

    bm_total = (1 + rb).prod() - 1
    bm_cagr  = (1 + bm_total) ** (1 / n_years) - 1 if n_years > 0 else None
    alpha    = (cagr - bm_cagr) if cagr and bm_cagr else None

    active = r - rb
    ir     = (active.mean() / active.std() * np.sqrt(TRADING_DAYS_YEAR)
              if active.std() > 0 else None)

    total_value = df_positions["current_value"].sum()
    total_cost  = df_positions["cost_basis"].sum()
    total_pnl   = df_positions["total_return"].sum()
    total_divs  = df_positions["dividends_total"].sum()
    
    total_pnl_pct = (total_pnl / total_cost) if total_cost > 0 else 0.0

    return {
        "total_return_pct":   round(total_return * 100, 4),
        "cagr_pct":           round(cagr * 100, 4)    if cagr    else None,
        "sharpe_ratio":       round(sharpe, 4)         if sharpe  else None,
        "sortino_ratio":      round(sortino, 4)        if sortino else None,
        "calmar_ratio":       round(calmar, 4)         if calmar  else None,
        "alpha_pct":          round(alpha * 100, 4)   if alpha   else None,
        "information_ratio":  round(ir, 4)             if ir      else None,
        "benchmark_cagr_pct": round(bm_cagr * 100, 4) if bm_cagr else None,
        "portfolio_value":    round(total_value, 2),
        "cost_basis_total":   round(total_cost, 2),
        "total_pnl":          round(total_pnl, 2),
        "total_pnl_pct":      round(total_pnl_pct, 4),
        "dividends_total":    round(total_divs, 2),
        "risk_free_rate_pct": RISK_FREE_RATE * 100,
        "n_years":            round(n_years, 2),
    }


# ── Concentrazione ───────────────────────────────────────────

def _calc_concentration(df_positions: pd.DataFrame) -> dict:
    df = df_positions[df_positions["current_value"] > 0].copy()
    if df.empty:
        return {}

    total     = df["current_value"].sum()
    df["w"]   = df["current_value"] / total
    hhi       = (df["w"] ** 2).sum()
    eff_n     = round(1 / hhi, 2) if hhi > 0 else None

    by_class   = (df.groupby("asset_class")["current_value"].sum() / total * 100).round(2).to_dict()
    by_sector  = (df.dropna(subset=["gics_sector"])
                  .groupby("gics_sector")["current_value"].sum() / total * 100).round(2).to_dict()
    by_country = (df.dropna(subset=["country"])
                  .groupby("country")["current_value"].sum() / total * 100).round(2).to_dict()

    top5 = (df.nlargest(5, "current_value")[["ticker", "w", "current_value"]]
              .assign(weight_pct=lambda x: (x["w"] * 100).round(2))
              .drop(columns="w")
              .to_dict(orient="records"))

    return {
        "hhi":                hhi.round(4),
        "effective_n_assets": eff_n,
        "by_asset_class_pct": by_class,
        "by_gics_sector_pct": by_sector,
        "by_country_pct":     by_country,
        "top5_positions":     top5,
        "n_active_positions": len(df),
    }


# ── Pretty print ─────────────────────────────────────────────

def print_results(results: dict) -> None:
    m   = results["metrics"]
    ret = m["returns"]
    mk  = m["market_risk"]
    con = m["concentration"]

    print("\n" + "=" * 60)
    print(f"  RISK ENGINE — Portfolio {results['portfolio_id']}")
    print(f"  Calcolato: {results['computed_at']}")
    print("=" * 60)

    print("\n📈 RENDIMENTO")
    print(f"   Valore portafoglio:  €{ret['portfolio_value']:,.2f}")
    print(f"   Costo di carico:     €{ret['cost_basis_total']:,.2f}")
    print(f"   P&L totale:          €{ret['total_pnl']:,.2f}")
    print(f"   Dividendi incassati: €{ret['dividends_total']:,.2f}")
    print(f"   Rendimento totale:   {ret['total_return_pct']}%")
    print(f"   CAGR:                {ret['cagr_pct']}%")
    print(f"   Alpha vs benchmark:  {ret['alpha_pct']}%")

    print("\n⚖️  RISK-ADJUSTED")
    print(f"   Sharpe:              {ret['sharpe_ratio']}")
    print(f"   Sortino:             {ret['sortino_ratio']}")
    print(f"   Calmar:              {ret['calmar_ratio']}")
    print(f"   Information ratio:   {ret['information_ratio']}")

    print("\n🔴 RISCHIO")
    print(f"   Volatilità annua:    {mk['volatility_annual_pct']}%")
    print(f"   VaR 95% (1g):        {mk['var_95']}%")
    print(f"   VaR 99% (1g):        {mk['var_99']}%")
    print(f"   CVaR 95%:            {mk['cvar_95']}%")
    print(f"   Beta vs {mk['benchmark_ticker']}:       {mk['beta']}")
    print(f"   Correlazione:        {mk['correlation_benchmark']}")
    print(f"   Max Drawdown:        {mk['max_drawdown_pct']}%")

    print("\n🗂  CONCENTRAZIONE")
    print(f"   HHI:                 {con['hhi']} (N eff. {con['effective_n_assets']})")
    print(f"   Posizioni attive:    {con['n_active_positions']}")
    for k, v in con["by_asset_class_pct"].items():
        print(f"   {k:<10}           {v:.1f}%")

    print("\n🏆 TOP 5 POSIZIONI")
    for p in con["top5_positions"]:
        print(f"   {p['ticker']:<15} €{p['current_value']:>10,.2f}   ({p['weight_pct']}%)")
        
    ai = m.get("ai_insights", {})
    if "montecarlo" in ai and ai["montecarlo"]:
        mc = ai["montecarlo"]
        print("\n🤖 AI & PREDICTIVE RISK (Monte Carlo 10k sim)")
        print(f"   Expected Return (1Y):  {mc['expected_return_1y_pct']}%")
        print(f"   Simulated VaR 95%:     {mc['var_95_simulated_pct']}%")
        print(f"   Simulated VaR 99%:     {mc['var_99_simulated_pct']}%")

    print("=" * 60 + "\n")


# ── AI & Machine Learning ────────────────────────────────────

def _calc_ai_insights(df_positions: pd.DataFrame, df_returns: pd.DataFrame, sr_portfolio: pd.Series) -> dict:
    insights = {}
    
    active_tickers = df_positions[df_positions["qty_net"] > 0]["ticker"].tolist()
    common_tickers = [t for t in active_tickers if t in df_returns.columns]
    
    # 1. K-Means Clustering on Assets (Risk vs Return)
    valid_returns = df_returns[common_tickers].dropna(how="all")
    
    if not valid_returns.empty and len(common_tickers) >= 3:
        # Volatilità annua e CAGR stimato per asset
        asset_vol = valid_returns.std() * np.sqrt(TRADING_DAYS_YEAR)
        asset_cagr = (1 + valid_returns.mean()) ** TRADING_DAYS_YEAR - 1
        
        features = pd.DataFrame({'volatility': asset_vol, 'cagr': asset_cagr}).dropna()
        if len(features) >= 3:
            n_clusters = min(3, len(features))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            features['cluster'] = kmeans.fit_predict(features)
            
            clusters_list = features.reset_index().to_dict(orient="records")
            insights["asset_clusters"] = clusters_list
        else:
            insights["asset_clusters"] = []
    else:
        insights["asset_clusters"] = []

    # 2. Monte Carlo Simulation for Portfolio VaR (1 Year) via Multivariate Normal (Cholesky)
    df_sync = df_returns[common_tickers].dropna()
    weights_series = (
        df_positions[df_positions["ticker"].isin(common_tickers)]
        .set_index("ticker")["weight_pct"] / 100
    )
    weights = weights_series.reindex(common_tickers).fillna(0).values
    weights = weights / weights.sum() if weights.sum() > 0 else weights

    if not df_sync.empty and len(df_sync) > 30 and weights.sum() > 0:
        days = TRADING_DAYS_YEAR
        simulations = 10000
        
        mu = df_sync.mean().values
        cov = df_sync.cov().values
        
        np.random.seed(42)
        try:
            # Multivariate Normal Simulation (Cholesky)
            sim_returns_assets = np.random.multivariate_normal(mu, cov, size=simulations * days)
            sim_returns_assets = sim_returns_assets.reshape(simulations, days, len(common_tickers))
            
            sim_port_returns = np.dot(sim_returns_assets, weights)
            sim_prices = np.exp(np.cumsum(sim_port_returns, axis=1))
            final_values = sim_prices[:, -1]
            
            var_95_mc = (1 - np.percentile(final_values, 5)) * 100
            var_99_mc = (1 - np.percentile(final_values, 1)) * 100
            
            # Esportiamo un campione di 100 percorsi per la UI per non appesantire il JSON
            n_paths_to_export = min(100, simulations)
            sampled_paths = []
            if n_paths_to_export > 0:
                # Prendi i primi N percorsi
                subset = sim_prices[:n_paths_to_export, :]
                # Aggiungiamo 1.0 (o 100) all'inizio come base 100
                base_100_paths = np.concatenate([np.ones((n_paths_to_export, 1)), subset], axis=1) * 100
                sampled_paths = base_100_paths.tolist()
            
            insights["montecarlo"] = {
                "simulated_days": days,
                "n_simulations": simulations,
                "var_95_simulated_pct": round(float(var_95_mc), 4),
                "var_99_simulated_pct": round(float(var_99_mc), 4),
                "expected_return_1y_pct": round(float(np.mean(final_values) - 1) * 100, 4),
                "paths": sampled_paths
            }
        except Exception as e:
            insights["montecarlo"] = {}
    return insights


def compute_brinson_attribution(df_pos: pd.DataFrame, df_returns: pd.DataFrame, benchmark_series: pd.Series):
    """
    Scomposizione dell'Alpha secondo il modello Brinson-Fachler per Settore GICS:
    - Allocation Effect = (w_p - w_b) * (R_b_sector - R_b_total)
    - Selection Effect = w_b * (R_p_sector - R_b_sector)
    - Interaction Effect = (w_p - w_b) * (R_p_sector - R_b_sector)
    """
    if df_pos is None or df_pos.empty or df_returns is None or df_returns.empty:
        return pd.DataFrame()
        
    active_pos = df_pos[df_pos["current_value"] > 0].copy()
    if active_pos.empty:
        return pd.DataFrame()
        
    active_pos["gics_sector"] = active_pos["gics_sector"].fillna("Unassigned")
    total_val = active_pos["current_value"].sum()
    
    sector_weights = active_pos.groupby("gics_sector")["current_value"].sum() / total_val
    
    sector_returns = {}
    for sector, group in active_pos.groupby("gics_sector"):
        sec_tickers = [t for t in group["ticker"] if t in df_returns.columns]
        if sec_tickers:
            sec_w = group.set_index("ticker")["weight_pct"].reindex(sec_tickers).fillna(0)
            sec_w = sec_w / (sec_w.sum() if sec_w.sum() > 0 else 1.0)
            mean_ret = (df_returns[sec_tickers].mean() * sec_w).sum() * 252 * 100
            sector_returns[sector] = mean_ret
        else:
            sector_returns[sector] = 0.0

    bm_tot_return = float(benchmark_series.mean() * 252 * 100) if benchmark_series is not None and not benchmark_series.empty else 0.0
    
    attribution_results = []
    n_sectors = max(1, len(sector_weights))
    for sector, wp in sector_weights.items():
        rp = sector_returns.get(sector, 0.0)
        wb = 1.0 / n_sectors
        rb = bm_tot_return
        
        alloc = (wp - wb) * (rb - bm_tot_return)
        select = wb * (rp - rb)
        inter = (wp - wb) * (rp - rb)
        total_effect = alloc + select + inter
        
        attribution_results.append({
            "Settore GICS": sector,
            "Peso Portafoglio %": round(wp * 100, 2),
            "Peso Benchmark %": round(wb * 100, 2),
            "Allocation Effect %": round(alloc, 2),
            "Selection Effect %": round(select, 2),
            "Interaction Effect %": round(inter, 2),
            "Alpha Totale %": round(total_effect, 2)
        })
        
    return pd.DataFrame(attribution_results)


def compute_hierarchical_risk_parity(cov_matrix: pd.DataFrame):
    """
    Algoritmo Hierarchical Risk Parity (HRP) di Marcos López de Prado:
    1. Distance Matrix da Correlazione D_ij = sqrt(0.5 * (1 - rho_ij))
    2. Single Linkage Hierarchical Tree Clustering
    3. Quasi-Diagonalization & Recursive Bisection Variance Allocation
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    import numpy as np
    
    if cov_matrix is None or cov_matrix.empty or cov_matrix.shape[0] < 2:
        return {}
        
    cov = cov_matrix.values
    std = np.sqrt(np.diag(cov))
    std[std == 0] = 1e-8
    corr = cov / np.outer(std, std)
    np.fill_diagonal(corr, 1.0)
    
    dist = np.sqrt(np.maximum(0, 0.5 * (1.0 - corr)))
    
    tri_u = np.triu_indices(dist.shape[0], k=1)
    condensed_dist = dist[tri_u]
    
    if len(condensed_dist) == 0:
        return {}
        
    link = linkage(condensed_dist, method='single')
    sort_idx = leaves_list(link)
    
    def get_rec_bisection(cov_mat, sort_ids):
        w = pd.Series(1.0, index=sort_ids)
        c_items = [sort_ids.tolist()]
        
        while len(c_items) > 0:
            c_items = [i[j:k] for i in c_items for j, k in ((0, len(i) // 2), (len(i) // 2, len(i))) if len(i) > 1]
            for i in range(0, len(c_items), 2):
                c_items1 = c_items[i]
                c_items2 = c_items[i + 1]
                
                cov1 = cov_mat[np.ix_(c_items1, c_items1)]
                v1 = 1.0 / np.diag(cov1)
                w1 = v1 / np.sum(v1)
                var1 = np.dot(np.dot(w1, cov1), w1)
                
                cov2 = cov_mat[np.ix_(c_items2, c_items2)]
                v2 = 1.0 / np.diag(cov2)
                w2 = v2 / np.sum(v2)
                var2 = np.dot(np.dot(w2, cov2), w2)
                
                alpha = 1.0 - var1 / (var1 + var2) if (var1 + var2) > 0 else 0.5
                w[c_items1] *= alpha
                w[c_items2] *= (1.0 - alpha)
        return w

    weights_series = get_rec_bisection(cov, sort_idx)
    hrp_weights = {}
    tickers = cov_matrix.columns
    for idx, w in weights_series.items():
        hrp_weights[tickers[idx]] = round(float(w), 4)
        
    return hrp_weights


def compute_almgren_chriss_market_impact(df_pos: pd.DataFrame):
    """
    Stima dei costi di impatto sul mercato (Almgren-Chriss Market Impact Model):
    - Impatto Temporaneo = eta * sigma * sqrt(Q / V)
    - Impatto Permanente = gamma * sigma * (Q / V)
    """
    if df_pos is None or df_pos.empty:
        return pd.DataFrame()
        
    df = df_pos[df_pos["current_value"] > 0].copy()
    if df.empty or "days_to_liquidate" not in df.columns:
        return pd.DataFrame()
        
    results = []
    eta = 0.142
    gamma = 0.314
    
    for _, row in df.iterrows():
        val = float(row.get("current_value", 0.0))
        days = float(row.get("days_to_liquidate", 1.0))
        
        temp_impact = eta * (days ** 0.5)
        perm_impact = gamma * days
        total_impact_pct = min(15.0, temp_impact + perm_impact)
        impact_eur = val * (total_impact_pct / 100.0)
        
        results.append({
            "Ticker": row.get("ticker"),
            "Valore (€)": val,
            "Giorni Liquidazione": round(days, 2),
            "Slippage Stimato %": round(total_impact_pct, 2),
            "Impatto Monetario (€)": round(impact_eur, 2)
        })
        
    return pd.DataFrame(results)


def compute_private_equity_waterfall(capital_calls: float, distributions: float, nav: float, hurdle_rate: float = 0.08, carried_interest: float = 0.20):
    """
    Simulatore dei flussi di cassa Private Equity (J-Curve & Waterfall Allocation):
    - DPI (Distributed to Paid-In)
    - RVPI (Residual Value to Paid-In)
    - TVPI / MOIC (Total Value to Paid-In)
    - Carried Interest & GP/LP Cash Distribution
    """
    if capital_calls <= 0:
        return {}
        
    dpi = distributions / capital_calls
    rvpi = nav / capital_calls
    tvpi = dpi + rvpi
    
    total_gain = (distributions + nav) - capital_calls
    hurdle_amount = capital_calls * hurdle_rate
    
    if total_gain > hurdle_amount:
        gp_carried_interest = (total_gain - hurdle_amount) * carried_interest
        lp_gain = total_gain - gp_carried_interest
    else:
        gp_carried_interest = 0.0
        lp_gain = total_gain
        
    return {
        "capital_calls": capital_calls,
        "distributions": distributions,
        "nav": nav,
        "dpi": round(dpi, 2),
        "rvpi": round(rvpi, 2),
        "tvpi_moic": round(tvpi, 2),
        "total_gain": round(total_gain, 2),
        "gp_carried_interest": round(gp_carried_interest, 2),
        "lp_net_gain": round(lp_gain, 2)
    }

