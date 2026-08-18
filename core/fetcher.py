# ============================================================
# fetcher.py
# Investment Risk BI Platform
#
# Input:  lista di ticker + date range dal DataFrame validato
# Output: prezzi storici scritti su MySQL (tabella market_prices)
#         + asset metadata su tabella assets
# ============================================================

import pandas as pd
import numpy as np
import yfinance as yf
import re
import time
import math
import json
import os
from pathlib import Path
import concurrent.futures
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta


def _get_config_file_path() -> Path:
    root_dir = Path(__file__).resolve().parent.parent
    candidates = [
        root_dir / "config" / "config.json",
        Path.cwd() / "config" / "config.json",
        Path.cwd() / "config.json",
        root_dir / "config.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _clean_val(v):
    if v is None: return None
    try:
        if math.isnan(float(v)) or math.isinf(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v

# ── Costanti ────────────────────────────────────────────────

ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")

# Secondi di attesa tra un ticker e l'altro (evita rate limit yfinance)
FETCH_DELAY = 0.5

# Quanti giorni prima della prima transazione scaricare
# (serve al risk engine per calcolare rendimenti da prima dell'acquisto)
LOOKBACK_EXTRA_DAYS = 365


# ── Connessione MySQL ────────────────────────────────────────

def get_engine(user: str, password: str, host: str,
               port: int = 3306, db: str = "investment_risk_bi", database: str = None):
    """
    Restituisce un engine SQLAlchemy per MySQL. Se MySQL non è disponibile (es. Docker disattivato),
    effettua il fallback automatico su un database locale SQLite (data/argus_local.db).
    """
    if database is not None:
        db = database
    import os
    try:
        import pymysql
        sys_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/"
        sys_engine = create_engine(sys_url, connect_args={"connect_timeout": 3})
        with sys_engine.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
        engine = create_engine(url, echo=False)
    except Exception:
        os.makedirs("data", exist_ok=True)
        sqlite_url = "sqlite:///data/argus_local.db"
        engine = create_engine(sqlite_url, echo=False)

    from core.models import Base
    Base.metadata.create_all(engine)
    
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE assets ADD COLUMN trailing_pe DECIMAL(10,2)"))
            conn.execute(text("ALTER TABLE assets ADD COLUMN forward_pe DECIMAL(10,2)"))
            conn.execute(text("ALTER TABLE assets ADD COLUMN price_to_book DECIMAL(10,2)"))
            conn.execute(text("ALTER TABLE assets ADD COLUMN dividend_yield DECIMAL(10,4)"))
            conn.execute(text("ALTER TABLE assets ADD COLUMN roe DECIMAL(10,4)"))
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE assets ADD COLUMN target_mean_price DECIMAL(18,6)"))
            conn.execute(text("ALTER TABLE assets ADD COLUMN peg_ratio DECIMAL(10,2)"))
        except Exception:
            pass

        new_cols = [
            "industry VARCHAR(100)", "exchange VARCHAR(50)", "recommendation_key VARCHAR(50)",
            "market_cap BIGINT", "beta_5y DECIMAL(10,4)",
            "fifty_two_week_high DECIMAL(18,6)", "fifty_two_week_low DECIMAL(18,6)",
            "fifty_day_average DECIMAL(18,6)", "two_hundred_day_average DECIMAL(18,6)",
            "profit_margins DECIMAL(10,4)", "gross_margins DECIMAL(10,4)", "operating_margins DECIMAL(10,4)",
            "total_revenue BIGINT", "ebitda BIGINT", "debt_to_equity DECIMAL(10,4)",
            "revenue_growth DECIMAL(10,4)", "earnings_growth DECIMAL(10,4)"
        ]
        for col_def in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col_def}"))
            except Exception:
                pass

    return engine


# ── Funzione principale ──────────────────────────────────────

def fetch_and_store(df_clean: pd.DataFrame,
                    engine,
                    portfolio_id: int = None,
                    benchmark_ticker: str = "SPY"):
    """
    Scarica i prezzi storici e i metadati per tutti i ticker
    presenti in df_clean, poi li scrive su MySQL.

    Parameters
    ----------
    df_clean    : DataFrame validato da validator.py
    engine      : SQLAlchemy engine connesso a MySQL
    portfolio_id: opzionale, usato solo per il log

    Returns
    -------
    report : dict con successi, warning ed errori per ticker
    """
    report = {
        "success":  [],   # ticker scaricati correttamente
        "skipped":  [],   # ISIN o ticker non supportati da yfinance
        "errors":   [],   # ticker che hanno dato errore
        "warnings": [],   # warning non bloccanti
        "rows_written": 0
    }

    offline_assets = []
    offline_prices = []

    # Data range: dal 2007 per consentire Stress Testing storici reali sugli asset esistenti
    start_date = "2007-01-01"
    end_date = datetime.today().strftime("%Y-%m-%d")


    # ── Mappatura Ticker (SaaS MVP: normalization) ────────────
    mapping_dict = {}
    try:
        # Load from config.json if exists
        cfg_file = _get_config_file_path()
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "ticker_mapping" in config:
                    mapping_dict.update(config["ticker_mapping"])
                    
        if engine is not None:
            with engine.connect() as conn:
                mapping_rows = conn.execute(text("SELECT input_ticker, yfinance_ticker FROM asset_mapping")).fetchall()
                mapping_dict.update({row[0]: row[1] for row in mapping_rows})
        
        if mapping_dict:
            df_clean["ticker"] = df_clean["ticker"].replace(mapping_dict)
            report["success"].append(f"Applicata mappatura ticker: {mapping_dict}")
    except Exception as e:
        report["warnings"].append(f"Errore durante la lettura del mapping: {e}")

    tickers = df_clean["ticker"].unique().tolist()
    
    # ── Forzatura Benchmark ──────────────────────────────
    if benchmark_ticker not in tickers:
        tickers.append(benchmark_ticker)
        report["success"].append(f"Forzato download di {benchmark_ticker} come benchmark")

    # ── Forzatura Tassi di Cambio (FX Risk) ──────────────────
    common_currencies = ["USD", "DKK", "GBP", "CHF", "SEK", "CAD", "JPY", "MXN"]
    unique_currencies = list(set(df_clean["currency"].dropna().unique().tolist() + common_currencies))
    for c in unique_currencies:
        c_upper = str(c).upper()
        if c_upper not in ["EUR", "XXX", "CRYPTO", "NAN", "NONE", "NULL"] and len(c_upper) == 3:
            fx_ticker = f"{c_upper}EUR=X"
            fx_ticker_inv = f"EUR{c_upper}=X"
            if fx_ticker not in tickers:
                tickers.append(fx_ticker)
            if fx_ticker_inv not in tickers:
                tickers.append(fx_ticker_inv)

    # ── Determinazione date di inizio incrementali per DB ───
    max_dates = {}
    if engine is not None:
        try:
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT a.ticker, MAX(mp.price_date) 
                    FROM market_prices mp 
                    JOIN assets a ON mp.asset_id = a.asset_id 
                    GROUP BY a.ticker
                """)).fetchall()
                max_dates = {row[0]: row[1] for row in rows if row[1] is not None}
        except Exception:
            pass

    print(f"\n[INFO] Fetching {len(tickers)} ticker(s) | {start_date} -> {end_date}\n")

    yfinance_tickers = [t for t in tickers if not ISIN_PATTERN.match(t)]
    downloaded_data = {}

    from core.cache_shield import get_cached_ticker_history, get_cached_ticker_info

    def download_ticker(t):
        try:
            t_start = start_date
            if t in max_dates:
                last_dt = pd.to_datetime(max_dates[t])
                start_dt = (last_dt - timedelta(days=7)).strftime("%Y-%m-%d")
                if start_dt > start_date:
                    t_start = start_dt

            # Chiamata protetta tramite scudo di caching multi-livello (RAM + SQLite con 24h TTL)
            hist = get_cached_ticker_history(t, start_date=t_start, end_date=end_date)
            info = get_cached_ticker_info(t)
            yf_ticker = yf.Ticker(t)
            return t, yf_ticker, hist, info, None
        except Exception as e:
            return t, None, None, None, str(e)

    if yfinance_tickers:
        print(f"  [i] Downloading {len(yfinance_tickers)} ticker(s) concurrently...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(download_ticker, t): t for t in yfinance_tickers}
            for future in concurrent.futures.as_completed(futures):
                t = futures[future]
                try:
                    res_ticker, yf_ticker, hist, info, err = future.result()
                    if err:
                        downloaded_data[t] = (None, None, None, err)
                    else:
                        downloaded_data[t] = (yf_ticker, hist, info, None)
                except Exception as e:
                    downloaded_data[t] = (None, None, None, str(e))

    for ticker in tickers:

        # ── Skip ISIN ───────────────────────────────────────
        if ISIN_PATTERN.match(ticker):
            # Estrae il nome del prodotto dalle note (se disponibile)
            product_name = df_clean.loc[df_clean["ticker"] == ticker, "notes"].dropna().iloc[0] if not df_clean.loc[df_clean["ticker"] == ticker, "notes"].dropna().empty else "Nome sconosciuto"
            report["skipped"].append(
                f"{ticker} ({product_name}) — ISIN non mappato, skip yfinance"
            )
            if engine is None:
                adict, d_p = _store_isin_price(ticker, df_clean, engine, report)
                offline_assets.append(adict)
                offline_prices.append(d_p)
            else:
                _store_isin_price(ticker, df_clean, engine, report)
            continue

        print(f"  [>]  {ticker} ...", end=" ")

        yf_ticker, hist, info, err = downloaded_data.get(ticker, (None, None, None, "Dati non trovati"))
        if err:
            report["errors"].append(f"{ticker}: {err}")
            print(f"[X] {err}")
            continue

        if hist is None or hist.empty:
            report["errors"].append(f"{ticker}: nessun dato restituito da yfinance")
            print("[X] nessun dato")
            continue

        try:
            # ── Metadati asset ───────────────────────────────
            if engine is None:
                adict = _upsert_asset(ticker, yf_ticker, df_clean, engine, info)
                offline_assets.append(adict)
                
                d_p = _store_prices(hist, None, engine, ticker=ticker)
                offline_prices.append(d_p)
                rows = len(d_p)
                report["success"].append(f"{ticker}: {rows} righe (in-memory)")
            else:
                asset_id = _upsert_asset(ticker, yf_ticker, df_clean, engine, info)
                rows = _store_prices(hist, asset_id, engine)
                report["success"].append(f"{ticker}: {rows} righe scritte")
            
            report["rows_written"] += rows
            print(f"[OK] {rows} righe")

        except Exception as e:
            report["errors"].append(f"{ticker}: {str(e)}")
            print(f"[X] {e}")

    _print_fetch_report(report)
    
    if engine is None:
        df_assets = pd.DataFrame(offline_assets) if offline_assets else pd.DataFrame()
        df_prices = pd.concat(offline_prices, ignore_index=True) if offline_prices else pd.DataFrame()
        
        df_tx = df_clean.copy()
        # Merge columns except 'currency' which will overlap, we rename asset's currency to asset_currency
        if not df_assets.empty:
            df_assets_renamed = df_assets.rename(columns={"currency": "asset_currency"})
            # Rimuoviamo colonne duplicate in df_tx per evitare conflitti di merge (es. asset_class)
            cols_to_drop = [col for col in df_assets_renamed.columns if col in df_tx.columns and col != "ticker"]
            if cols_to_drop:
                df_tx = df_tx.drop(columns=cols_to_drop)
            df_tx = df_tx.merge(df_assets_renamed, on="ticker", how="left")
            if "asset_currency" not in df_tx.columns:
                df_tx["asset_currency"] = df_tx["currency"]
        else:
            df_tx["asset_currency"] = df_tx["currency"]
            
        return report, df_tx, df_prices

    return report



# ── Upsert asset metadata ────────────────────────────────────

def _upsert_asset(ticker: str,
                  yf_ticker,
                  df_clean: pd.DataFrame,
                  engine,
                  info: dict = None):
    """
    Inserisce o aggiorna il record in `assets`.
    Restituisce l'asset_id.

    Usa INSERT ... ON DUPLICATE KEY UPDATE per gestire
    il UNIQUE KEY uq_ticker senza errori.
    """
    if info is None:
        info = {}
        try:
            info = yf_ticker.info or {}
        except Exception:
            pass


    # asset_class: dal CSV se presente, altrimenti da yfinance
    asset_class_from_csv = (
        df_clean.loc[df_clean["ticker"] == ticker, "asset_class"]
        .dropna()
        .iloc[0]
        if not df_clean.loc[
            (df_clean["ticker"] == ticker) &
            df_clean["asset_class"].notna()
        ].empty
        else None
    )

    asset_class = asset_class_from_csv or _infer_asset_class(info, ticker)
    currency    = info.get("currency", "USD")
    name        = info.get("longName") or info.get("shortName") or ticker
    
    from core.metadata_resolver import resolve_asset_metadata
    country_raw = info.get("country")
    sector_raw  = info.get("sector")
    country, gics_sector = resolve_asset_metadata(ticker, asset_class, country_raw, sector_raw)
    
    # ── Fondamentali (Valutazione Aziendale) ──
    trailing_pe    = _clean_val(info.get("trailingPE"))
    forward_pe     = _clean_val(info.get("forwardPE"))
    price_to_book  = _clean_val(info.get("priceToBook"))
    dividend_yield = _clean_val(info.get("dividendYield"))
    roe            = _clean_val(info.get("returnOnEquity"))
    target_mean    = _clean_val(info.get("targetMeanPrice"))
    peg_ratio      = _clean_val(info.get("pegRatio"))
    
    # ── Nuove metriche BI ──
    industry          = info.get("industry")
    exchange          = info.get("exchange")
    recommendation_key= info.get("recommendationKey")
    market_cap        = _clean_val(info.get("marketCap"))
    beta_5y           = _clean_val(info.get("beta"))
    fifty_two_week_high = _clean_val(info.get("fiftyTwoWeekHigh"))
    fifty_two_week_low  = _clean_val(info.get("fiftyTwoWeekLow"))
    fifty_day_average   = _clean_val(info.get("fiftyDayAverage"))
    two_hundred_day_average = _clean_val(info.get("twoHundredDayAverage"))
    profit_margins    = _clean_val(info.get("profitMargins"))
    gross_margins     = _clean_val(info.get("grossMargins"))
    operating_margins = _clean_val(info.get("operatingMargins"))
    total_revenue     = _clean_val(info.get("totalRevenue"))
    ebitda            = _clean_val(info.get("ebitda"))
    debt_to_equity    = _clean_val(info.get("debtToEquity"))
    revenue_growth    = _clean_val(info.get("revenueGrowth"))
    earnings_growth   = _clean_val(info.get("earningsGrowth"))

    if engine is None:
        return {
            "ticker":         ticker,
            "name":           name[:200] if name else None,
            "asset_class":    asset_class,
            "currency":       currency[:3] if currency else "USD",
            "gics_sector":    gics_sector,
            "country":        country,
            "trailing_pe":    trailing_pe,
            "forward_pe":     forward_pe,
            "price_to_book":  price_to_book,
            "dividend_yield": dividend_yield,
            "roe":            roe,
            "target_mean_price": target_mean,
            "peg_ratio":      peg_ratio,
            "industry":       industry,
            "exchange":       exchange,
            "recommendation_key": recommendation_key,
            "market_cap":     market_cap,
            "beta_5y":        beta_5y,
            "fifty_two_week_high": fifty_two_week_high,
            "fifty_two_week_low": fifty_two_week_low,
            "fifty_day_average": fifty_day_average,
            "two_hundred_day_average": two_hundred_day_average,
            "profit_margins": profit_margins,
            "gross_margins":  gross_margins,
            "operating_margins": operating_margins,
            "total_revenue":  total_revenue,
            "ebitda":         ebitda,
            "debt_to_equity": debt_to_equity,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth
        }

    sql = text("""
        INSERT INTO assets
            (ticker, name, asset_class, currency, gics_sector, country, 
             trailing_pe, forward_pe, price_to_book, dividend_yield, roe, target_mean_price, peg_ratio,
             industry, exchange, recommendation_key, market_cap, beta_5y,
             fifty_two_week_high, fifty_two_week_low, fifty_day_average, two_hundred_day_average,
             profit_margins, gross_margins, operating_margins, total_revenue, ebitda,
             debt_to_equity, revenue_growth, earnings_growth)
        VALUES
            (:ticker, :name, :asset_class, :currency, :gics_sector, :country,
             :trailing_pe, :forward_pe, :price_to_book, :dividend_yield, :roe, :target_mean, :peg,
             :industry, :exchange, :recommendation_key, :market_cap, :beta_5y,
             :fifty_two_week_high, :fifty_two_week_low, :fifty_day_average, :two_hundred_day_average,
             :profit_margins, :gross_margins, :operating_margins, :total_revenue, :ebitda,
             :debt_to_equity, :revenue_growth, :earnings_growth)
        ON DUPLICATE KEY UPDATE
            name           = VALUES(name),
            asset_class    = VALUES(asset_class),
            currency       = VALUES(currency),
            gics_sector    = VALUES(gics_sector),
            country        = VALUES(country),
            trailing_pe    = VALUES(trailing_pe),
            forward_pe     = VALUES(forward_pe),
            price_to_book  = VALUES(price_to_book),
            dividend_yield = VALUES(dividend_yield),
            roe            = VALUES(roe),
            target_mean_price = VALUES(target_mean_price),
            peg_ratio      = VALUES(peg_ratio),
            industry       = VALUES(industry),
            exchange       = VALUES(exchange),
            recommendation_key = VALUES(recommendation_key),
            market_cap     = VALUES(market_cap),
            beta_5y        = VALUES(beta_5y),
            fifty_two_week_high = VALUES(fifty_two_week_high),
            fifty_two_week_low  = VALUES(fifty_two_week_low),
            fifty_day_average   = VALUES(fifty_day_average),
            two_hundred_day_average = VALUES(two_hundred_day_average),
            profit_margins = VALUES(profit_margins),
            gross_margins  = VALUES(gross_margins),
            operating_margins = VALUES(operating_margins),
            total_revenue  = VALUES(total_revenue),
            ebitda         = VALUES(ebitda),
            debt_to_equity = VALUES(debt_to_equity),
            revenue_growth = VALUES(revenue_growth),
            earnings_growth = VALUES(earnings_growth)
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "ticker":         ticker,
            "name":           name[:200] if name else None,
            "asset_class":    asset_class,
            "currency":       currency[:3] if currency else "USD",
            "gics_sector":    gics_sector,
            "country":        country,
            "trailing_pe":    trailing_pe,
            "forward_pe":     forward_pe,
            "price_to_book":  price_to_book,
            "dividend_yield": dividend_yield,
            "roe":            roe,
            "target_mean":    target_mean,
            "peg":            peg_ratio,
            "industry":       industry,
            "exchange":       exchange,
            "recommendation_key": recommendation_key,
            "market_cap":     market_cap,
            "beta_5y":        beta_5y,
            "fifty_two_week_high": fifty_two_week_high,
            "fifty_two_week_low": fifty_two_week_low,
            "fifty_day_average": fifty_day_average,
            "two_hundred_day_average": two_hundred_day_average,
            "profit_margins": profit_margins,
            "gross_margins":  gross_margins,
            "operating_margins": operating_margins,
            "total_revenue":  total_revenue,
            "ebitda":         ebitda,
            "debt_to_equity": debt_to_equity,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth
        })
        asset_id = conn.execute(
            text("SELECT asset_id FROM assets WHERE ticker = :t"),
            {"t": ticker}
        ).scalar()

    return asset_id


# ── Store prezzi storici ─────────────────────────────────────

def _store_prices(hist: pd.DataFrame,
                  asset_id: int,
                  engine,
                  ticker: str = None):
    """
    Scrive i prezzi storici su market_prices.
    Usa INSERT IGNORE per non duplicare righe già presenti
    (grazie a UNIQUE KEY uq_asset_date).
    """
    records = []
    for date, row in hist.iterrows():
        close = row.get("Close") if row.get("Close") is not None else row.get("close")
        volume = row.get("Volume") if row.get("Volume") is not None else row.get("volume")

        if close is None or pd.isna(close):
            continue

        price_date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]

        records.append({
            "asset_id":   asset_id,
            "price_date": price_date_str,
            "close":      round(float(close), 6),
            "volume":     int(volume) if volume and not pd.isna(volume) else None,
            "source":     "yfinance",
        })

    if not records:
        if engine is None: return pd.DataFrame(columns=["ticker", "price_date", "close", "volume"])
        return 0

    if engine is None:
        df_p = pd.DataFrame(records)
        df_p["ticker"] = ticker
        return df_p[["ticker", "price_date", "close", "volume"]]

    sql = text("""
        INSERT IGNORE INTO market_prices
            (asset_id, price_date, close, volume, source)
        VALUES
            (:asset_id, :price_date, :close, :volume, :source)
    """)

    with engine.begin() as conn:
        conn.execute(sql, records)

    return len(records)


# ── Gestione ISIN (prezzi da CSV) ────────────────────────────

def _store_isin_price(ticker: str,
                      df_clean: pd.DataFrame,
                      engine,
                      report: dict):
    """
    Per gli ISIN yfinance non funziona.
    Usiamo il prezzo presente nel CSV come unico punto dati.
    L'asset viene comunque registrato in `assets` come bond.
    """
    rows = df_clean[df_clean["ticker"] == ticker]

    # asset_class dal CSV, default bond per ISIN
    asset_class = (
        rows["asset_class"].dropna().iloc[0]
        if not rows["asset_class"].dropna().empty
        else "bond"
    )
    currency = rows["currency"].iloc[0] if not rows.empty else "EUR"

    if engine is None:
        adict = {
            "ticker": ticker,
            "name": ticker,
            "asset_class": asset_class,
            "currency": currency[:3]
        }
        precords = []
        for _, r in rows.iterrows():
            precords.append({
                "ticker": ticker,
                "price_date": str(r["tx_date"])[:10],
                "close": float(r["price"]),
                "volume": None
            })
        report["skipped"].append(
            f"{ticker}: {len(precords)} prezzi da CSV (ISIN, no yfinance)"
        )
        return adict, pd.DataFrame(precords)
    sql_asset = text("""
        INSERT INTO assets (ticker, name, asset_class, currency, gics_sector, country)
        VALUES (:ticker, :name, :asset_class, :currency, NULL, NULL)
        ON DUPLICATE KEY UPDATE
            name        = VALUES(name),
            asset_class = VALUES(asset_class),
            currency    = VALUES(currency)
    """)

    currency = rows["currency"].iloc[0] if not rows.empty else "EUR"

    with engine.begin() as conn:
        conn.execute(sql_asset, {
            "ticker":      ticker,
            "name":        ticker,
            "asset_class": asset_class,
            "currency":    currency[:3],
        })
        asset_id = conn.execute(
            text("SELECT asset_id FROM assets WHERE ticker = :t"),
            {"t": ticker}
        ).scalar()

    # Inserisce i prezzi dal CSV (una riga per transazione)
    sql_price = text("""
        INSERT IGNORE INTO market_prices
            (asset_id, price_date, close, volume, source)
        VALUES
            (:asset_id, :price_date, :close, NULL, 'csv_manual')
    """)

    records = [
        {
            "asset_id":   asset_id,
            "price_date": str(r["tx_date"])[:10],
            "close":      float(r["price"]),
        }
        for _, r in rows.iterrows()
    ]

    with engine.begin() as conn:
        conn.execute(sql_price, records)

    report["skipped"].append(
        f"{ticker}: {len(records)} prezzi da CSV (ISIN, no yfinance)"
    )


# ── Inferisce asset_class da yfinance info ───────────────────

def _infer_asset_class(info: dict, ticker: str) -> str:
    """
    Inferisce l'asset_class dai metadati yfinance
    quando l'utente non l'ha specificata nel CSV.
    """
    quote_type = info.get("quoteType", "").upper()

    mapping = {
        "EQUITY":       "stock",
        "ETF":          "etf",
        "MUTUALFUND":   "etf",
        "BOND":         "bond",
        "FIXED_INCOME": "bond",
        "CRYPTOCURRENCY": "crypto",
        "CURRENCY":     "cash",
    }

    if quote_type in mapping:
        return mapping[quote_type]

    # Fallback: crypto da ticker
    if "-USD" in ticker or "-EUR" in ticker or "-BTC" in ticker:
        return "crypto"

    return "stock"  # default sicuro


# ── Pretty print report ───────────────────────────────────────

def _print_fetch_report(report: dict) -> None:
    print("\n" + "="*60)
    print("  FETCH REPORT")
    print("="*60)

    if report["success"]:
        print(f"\n[OK] SUCCESSO ({len(report['success'])}):")
        for s in report["success"]:
            print(f"   • {s}")

    if report["skipped"]:
        print(f"\n[SKIP] SKIPPATI ({len(report['skipped'])}):")
        for s in report["skipped"]:
            print(f"   • {s}")

    if report["errors"]:
        print(f"\n[ERROR] ERRORI ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"   • {e}")

    if report.get("warnings"):
        print(f"\n[WARN] WARNING ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"   • {w}")

    print(f"\n[DB] Totale righe scritte su MySQL: {report['rows_written']}")
    print("="*60 + "\n")