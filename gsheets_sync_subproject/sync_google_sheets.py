"""
ARGUS Risk Analytics - Automated Google Sheets Sync & Daily Pipeline Engine
===========================================================================
Subprogetto per la sincronizzazione automatica giornaliera da Google Sheets.
Scarica il foglio 'History B/S stocks', esegue la validazione ed il motore di rischio,
e storicizza lo snapshot analitico nel Data Warehouse MySQL.
"""

import os
import sys
import json
import logging
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Adjust path to import core modules from parent directory
SUBPROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SUBPROJECT_DIR)
sys.path.append(PROJECT_ROOT)

from core.validator import validate_csv
from core.fetcher import fetch_and_store, get_engine
from core.risk_engine import compute_risk
from core.db_exporter import save_snapshot_to_db

# Setup logging
os.makedirs(os.path.join(SUBPROJECT_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    filename=os.path.join(SUBPROJECT_DIR, "logs", "gsheets_sync.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(console_handler)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_PATH = os.path.join(SUBPROJECT_DIR, "google_service_account.json")
DEFAULT_SPREADSHEET = "My All financial Statements"
DEFAULT_SHEET_NAME = "History B/S Stocks"


def get_gspread_client():
    """Autentica il client con il Service Account JSON."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"File credenziali non trovato in: {CREDENTIALS_PATH}")
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def fetch_sheet_dataframe(spreadsheet_identifier: str = None, sheet_tab_name: str = DEFAULT_SHEET_NAME) -> pd.DataFrame:
    """Scarica i dati dal foglio Google Sheet e restituisce un DataFrame."""
    client = get_gspread_client()
    
    if not spreadsheet_identifier:
        spreadsheet_identifier = DEFAULT_SPREADSHEET

    logging.info(f"Connessione a Google Sheets in corso per '{spreadsheet_identifier}'...")

    try:
        if spreadsheet_identifier.startswith("http") or len(spreadsheet_identifier) > 30:
            spreadsheet = client.open_by_key(spreadsheet_identifier.split("/d/")[1].split("/")[0]) if "/d/" in spreadsheet_identifier else client.open_by_key(spreadsheet_identifier)
        else:
            try:
                spreadsheet = client.open(spreadsheet_identifier)
            except Exception:
                all_sheets = client.openall()
                if all_sheets:
                    spreadsheet = all_sheets[0]
                else:
                    raise
    except Exception as e:
        logging.error(f"Errore nell'apertura dello Spreadsheet '{spreadsheet_identifier}': {e}")
        raise

    # Case-insensitive worksheet matching
    worksheet = None
    target_lower = sheet_tab_name.lower().strip()
    all_worksheets = spreadsheet.worksheets()
    
    for ws in all_worksheets:
        if ws.title.lower().strip() == target_lower:
            worksheet = ws
            break
            
    if not worksheet:
        logging.warning(f"Foglio '{sheet_tab_name}' non trovato. Uso il primo foglio ('{all_worksheets[0].title}').")
        worksheet = all_worksheets[0]

    all_vals = worksheet.get_all_values()
    if not all_vals:
        return pd.DataFrame()

    raw_headers = all_vals[0]
    
    # Check for duplicate headers and isolate the primary transaction table
    seen_headers = []
    max_col_idx = len(raw_headers)
    for idx, h in enumerate(raw_headers):
        clean_h = h.strip()
        if clean_h in seen_headers and clean_h in ["Date", "Security", "Action", "Data", "Ticker"]:
            max_col_idx = idx
            break
        if clean_h:
            seen_headers.append(clean_h)

    headers = [h.strip() if h.strip() else f"col_{i}" for i, h in enumerate(raw_headers[:max_col_idx])]
    rows = [r[:max_col_idx] for r in all_vals[1:] if any(r[:max_col_idx])]

    df = pd.DataFrame(rows, columns=headers)
    logging.info(f"Scaricati con successo {len(df)} record dal foglio '{worksheet.title}'.")
    return df


def normalize_gsheet_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizza il foglio Google Sheets secondo le regole del sottoprogetto Wealth:
    - Prende Date, Security (diverso da Cash/CASH), Action (solo Buy, Sell, Dividend),
      Quantity (Dividend forzato a 1), Type (Stock o ETF), Total (calcola prezzo unitario = Total / Quantity).
    """
    clean_rows = []

    for idx, r in df_raw.iterrows():
        # Extracted columns by name or position
        date_str = str(r.get("Date", r.get("Date", r.get("tx_date", "")))).strip()
        security = str(r.get("Security", r.get("ticker", ""))).strip().upper()
        action_str = str(r.get("Action", r.get("tx_type", ""))).strip().lower()
        qty_str = str(r.get("Quantity", r.get("quantity", ""))).strip()
        type_str = str(r.get("Type", r.get("asset_class", ""))).strip().lower()
        total_str = str(r.get("Total", r.get("price", ""))).strip()

        # Rule 1: Security != Cash / CASH / Interest / Empty
        if not security or security in ["CASH", "CASH EUR", "CASH USD", "INTEREST", "FLATEX INTEREST", "CURRENCY", "TOTAL", "X", "NAN"]:
            continue

        # Mappatura Ticker specifica (es. BIT:ISP -> ISP.MI, PRX -> PRX.AS)
        ticker_mapping = {
            "BIT:ISP": "ISP.MI",
            "CPH:NOVO-B": "NOVO-B.CO",
            "LON:NDIA": "NDIA.L",
            "EPA:DFNS": "DFNS.PA",
            "EPA:DFND": "DFND.PA",
            "PRX": "PRX.AS",
            "IMAE": "IMEA.SW",
        }
        security = ticker_mapping.get(security, security)

        # Rule 2: Action in ['buy', 'sell', 'dividend']
        if action_str in ["buy", "acquisto"]:
            tx_type = "buy"
        elif action_str in ["sell", "vendita"]:
            tx_type = "sell"
        elif action_str in ["dividend", "dividendo"]:
            tx_type = "dividend"
        else:
            continue

        # Rule 3: Quantity (Dividend is always 1)
        if tx_type == "dividend":
            quantity = 1.0
        else:
            try:
                clean_q = qty_str.replace(" ", "").replace(",", ".")
                quantity = float(clean_q) if clean_q else 1.0
            except Exception:
                quantity = 1.0

        if quantity <= 0:
            continue

        # Rule 4: Asset class (Stock or ETF)
        asset_class = "etf" if "etf" in type_str else "stock"

        # Rule 5: Total cost & Unit price calculation
        clean_tot = total_str.replace("€", "").replace("$", "").replace("£", "").replace(" ", "").strip()
        if "." in clean_tot and "," in clean_tot:
            clean_tot = clean_tot.replace(".", "").replace(",", ".")
        else:
            clean_tot = clean_tot.replace(",", ".")

        try:
            total_val = float(clean_tot)
        except Exception:
            total_val = 0.0

        if total_val <= 0:
            continue

        unit_price = total_val / quantity

        clean_rows.append({
            "tx_date": date_str,
            "ticker": security,
            "tx_type": tx_type,
            "quantity": quantity,
            "price": round(unit_price, 6),
            "currency": "EUR",
            "asset_class": asset_class,
            "notes": f"Total GSheet: € {total_val:.2f}"
        })

    return pd.DataFrame(clean_rows)


def run_daily_pipeline(spreadsheet_identifier: str, sheet_tab_name: str = DEFAULT_SHEET_NAME):
    """Esegue l'intera pipeline ETL e storicizzazione a DB."""
    logging.info("=== AVVIO PIPELINE GIORNALIERA ARGUS ===")
    
    # 1. Download & Normalize
    df_raw = fetch_sheet_dataframe(spreadsheet_identifier, sheet_tab_name)
    df_raw = normalize_gsheet_columns(df_raw)

    # 2. Validation
    df_clean, report = validate_csv(df_raw)
    if report["errors"]:
        logging.error(f"Validazione fallita con {len(report['errors'])} errori: {report['errors']}")
        return False

    logging.info(f"Validazione completata: {report['stats']['total_rows']} righe valide, {len(report['stats']['tickers'])} ticker.")

    # 3. Database Connection
    try:
        import dotenv
        dotenv.load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    except Exception:
        pass

    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = int(os.environ.get("DB_PORT", 3306))
    db_user = os.environ.get("DB_USER", "root")
    db_pass = os.environ.get("DB_PASS", "root")
    db_name = os.environ.get("DB_NAME", "wealth")

    portfolio_name = os.environ.get("PORTFOLIO_NAME", "Wealth Google Sheets Portfolio")
    benchmark = os.environ.get("BENCHMARK_TICKER", "SPY")

    try:
        from sqlalchemy import create_engine, text as sqlt
        temp_engine = create_engine(f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/", echo=False)
        with temp_engine.begin() as conn:
            conn.execute(sqlt(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))

        engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
        from core.db_exporter import ensure_snapshot_tables
        ensure_snapshot_tables(engine)
        offline_mode = False
    except Exception as e:
        logging.warning(f"Connessione MySQL non disponibile ({e}). Esecuzione in modalità offline.")
        engine = None
        offline_mode = True

    portfolio_id = 1
    if not offline_mode:
        from sqlalchemy import text as sqlt
        with engine.begin() as conn:
            conn.execute(sqlt("""
                INSERT INTO portfolios (name, owner, base_currency, created_at)
                VALUES (:name, 'gsheets_cron', 'EUR', NOW())
                ON DUPLICATE KEY UPDATE name=VALUES(name)
            """), {"name": portfolio_name})
            portfolio_id = conn.execute(sqlt("SELECT portfolio_id FROM portfolios WHERE name=:n"), {"n": portfolio_name}).scalar() or 1

            conn.execute(sqlt("DELETE FROM transactions WHERE portfolio_id = :pid"), {"pid": portfolio_id})

            for _, row in df_clean.iterrows():
                conn.execute(sqlt("""
                    INSERT INTO assets (ticker, name, asset_class, currency)
                    VALUES (:ticker, :ticker, :asset_class, :currency)
                    ON DUPLICATE KEY UPDATE name=VALUES(name)
                """), {
                    "ticker": row["ticker"],
                    "asset_class": "stock" if pd.isna(row.get("asset_class")) else row.get("asset_class"),
                    "currency": row["currency"]
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
                    "pid": portfolio_id,
                    "aid": asset_id,
                    "tx_date": str(row["tx_date"])[:10],
                    "tx_type": row["tx_type"],
                    "quantity": float(row["quantity"]),
                    "price": float(row["price"]),
                    "currency": row["currency"],
                    "fees": 0.0 if pd.isna(row.get("fees")) or str(row.get("fees")).strip() in ["", "nan", "None"] else float(str(row["fees"]).replace(",", ".")),
                    "notes": None if pd.isna(row.get("notes")) else str(row.get("notes")),
                })

    # 4. Fetch Market Data & Compute Risk
    if offline_mode:
        fetch_report, df_tx, df_prices = fetch_and_store(df_clean, None, portfolio_id, benchmark_ticker=benchmark)
        results = compute_risk(portfolio_id, None, benchmark_ticker=benchmark, df_tx=df_tx, df_prices=df_prices)
    else:
        fetch_report = fetch_and_store(df_clean, engine, portfolio_id, benchmark_ticker=benchmark)
        results = compute_risk(portfolio_id, engine, benchmark_ticker=benchmark)

    # 5. Snapshot Persistence
    run_id = f"ANL-CRON-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if not offline_mode and engine:
        save_snapshot_to_db(results, engine, portfolio_id, run_id, "Daily Automatic Sync")
        logging.info(f"Snapshot persisto nel DB con Run ID: {run_id}")

    ret = results.get("metrics", {}).get("returns", {})
    logging.info(f"=== PIPELINE COMPLETATA CON SUCCESSO! CAGR: {ret.get('cagr_pct', 0.0):.2f}%, Sharpe: {results.get('metrics', {}).get('market_risk', {}).get('sharpe_ratio', 0.0):.2f} ===")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ARGUS Google Sheets ETL & Risk Pipeline Sync")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SPREADSHEET, help="Nome o ID dello Spreadsheet Google Sheets")
    parser.add_argument("--tab", type=str, default=DEFAULT_SHEET_NAME, help="Nome del foglio (default: History B/S Stocks)")
    
    args = parser.parse_args()
    run_daily_pipeline(args.sheet, args.tab)
