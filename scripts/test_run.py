import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from core.validator import validate_csv
from core.fetcher import fetch_and_store, get_engine
from core.risk_engine import compute_risk
from core.db_exporter import save_snapshot_to_db
import datetime
from sqlalchemy import text as sqlt
import warnings
warnings.filterwarnings('ignore')

db_user = "root"
db_pass = "root"
db_host = "localhost"
db_port = 3306
db_name = "investment_risk_bi"
benchmark = "SPY"
portfolio_name = "Test Portfolio 500"

print("Connessione a MySQL...")
engine = get_engine(db_user, db_pass, db_host, db_port, db_name)

print("Lettura CSV data/test_portfolio_500.csv...")
df_raw = pd.read_csv("data/test_portfolio_500.csv", dtype=str)

df_clean, report = validate_csv(df_raw)
if report["errors"]:
    print("Errori di validazione:", report["errors"])
    exit(1)

with engine.begin() as conn:
    conn.execute(sqlt("""
        INSERT INTO portfolios (name, owner, base_currency, created_at)
        VALUES (:name, 'test_user', 'EUR', NOW())
    """), {"name": portfolio_name})
    portfolio_id = conn.execute(sqlt("SELECT LAST_INSERT_ID()")).scalar()



    for _, row in df_clean.iterrows():
        conn.execute(sqlt("""
            INSERT INTO assets (ticker, name, asset_class, currency)
            VALUES (:ticker, :ticker, :asset_class, :currency)
            ON DUPLICATE KEY UPDATE ticker=ticker
        """), {
            "ticker":      row["ticker"],
            "asset_class": row.get("asset_class") or "stock",
            "currency":    row["currency"],
        })
        asset_id = conn.execute(
            sqlt("SELECT asset_id FROM assets WHERE ticker=:t"),
            {"t": row["ticker"]}
        ).scalar()

        conn.execute(sqlt("""
            INSERT INTO transactions
                (portfolio_id, asset_id, tx_date, tx_type,
                 quantity, price, currency, fees, notes)
            VALUES
                (:pid, :aid, :tx_date, :tx_type,
                 :quantity, :price, :currency, :fees, :notes)
        """), {
            "pid":      portfolio_id,
            "aid":      asset_id,
            "tx_date":  str(row["tx_date"])[:10],
            "tx_type":  row["tx_type"],
            "quantity": float(row["quantity"]),
            "price":    float(row["price"]),
            "currency": row["currency"],
            "fees":     float(row["fees"]),
            "notes":    row.get("notes"),
        })

print("Avvio fetch_and_store (dati di mercato)...")
fetch_report = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
print(f"Fetch success: {len(fetch_report['success'])} tickers.")

print("Avvio compute_risk...")
try:
    results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark)
    print("====================================")
    print("Calcolo completato con successo! ✅")
    mk = results["metrics"]["market_risk"]
    print(f"Volatilità annua: {mk.get('volatility_annual_pct', 0)*100:.2f}%")
    print(f"VaR 95% Storico: {mk.get('var_95', 0)*100:.2f}%")
    print(f"VaR 95% Parametrico: {mk.get('var_parametric_95', 0)*100:.2f}%")
    print(f"VaR 95% Cornish-Fisher: {mk.get('var_cf_95', 0)*100:.2f}%")
    print(f"Skewness: {mk.get('skewness', 0):.4f}")
    print(f"Kurtosis: {mk.get('kurtosis', 0):.4f}")
    print(f"Tracking Error: {mk.get('tracking_error_pct', 0)*100:.2f}%")
    print("====================================")
except Exception as e:
    import traceback
    print(f"Errore durante compute_risk:")
    traceback.print_exc()
