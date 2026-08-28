"""
ARGUS Risk Analytics - Automated Google Sheets Sync & Dual Pipeline Engine (Stocks & Crypto)
=============================================================================================
Subprogetto per la sincronizzazione automatica giornaliera da Google Sheets.
Supporta l'estrazione duale sia del foglio azionario ('History B/S Stocks') sia del
foglio criptovalute ('History B/S Crypto'), separando i due portafogli a livello di
Data Warehouse (MySQL/SQLite) e registrandoli nei profili del Total Wealth Hub.
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
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.validator import validate_csv
from core.fetcher import fetch_and_store, get_engine
from core.risk_engine import compute_risk
from core.db_exporter import save_snapshot_to_db, ensure_snapshot_tables
from core.multi_portfolio import save_portfolio_profile, consolidate_multi_portfolios

# Setup logging
os.makedirs(os.path.join(SUBPROJECT_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    filename=os.path.join(SUBPROJECT_DIR, "logs", "gsheets_sync.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
if not logging.getLogger().handlers:
    logging.getLogger().addHandler(console_handler)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_PATH = os.path.join(SUBPROJECT_DIR, "google_service_account.json")
DEFAULT_SPREADSHEET = "My All financial Statements"
DEFAULT_STOCKS_TAB = "History B/S Stocks"
DEFAULT_CRYPTO_TAB = "History B/S Crypto"
DEFAULT_STOCKS_PORTFOLIO = "Wealth Stocks Portfolio"
DEFAULT_CRYPTO_PORTFOLIO = "Wealth Crypto Portfolio"

# Common crypto ticker aliases that require currency suffix on yfinance
CRYPTO_SYMBOLS = {
    "BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "MATIC", "LINK", "XRP",
    "BNB", "DOGE", "NEAR", "ATOM", "SUI", "APT", "RENDER", "FET", "TAO",
    "AAVE", "UNI", "LTC", "BCH", "ALGO", "FIL", "ICP", "TRX", "TON",
    "SHIB", "PEPE", "POL", "ARB", "OP", "TIA", "INJ", "KAS", "RUNE", "HBAR"
}


def get_gspread_client():
    """Autentica il client con il Service Account JSON."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"File credenziali non trovato in: {CREDENTIALS_PATH}")
    
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def fetch_sheet_dataframe(spreadsheet_identifier: str = None, sheet_tab_name: str = DEFAULT_STOCKS_TAB) -> pd.DataFrame:
    """Scarica i dati da uno specifico tab di Google Sheets e restituisce un DataFrame."""
    client = get_gspread_client()
    
    if not spreadsheet_identifier:
        spreadsheet_identifier = DEFAULT_SPREADSHEET

    logging.info(f"Connessione a Google Sheets per '{spreadsheet_identifier}', foglio: '{sheet_tab_name}'...")

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
        # Fallback search for partial name match
        for ws in all_worksheets:
            if target_lower in ws.title.lower().strip() or ws.title.lower().strip() in target_lower:
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
        if clean_h in seen_headers and clean_h in ["Date", "Security", "Action", "Data", "Ticker", "Asset", "Coin"]:
            max_col_idx = idx
            break
        if clean_h:
            seen_headers.append(clean_h)

    headers = [h.strip() if h.strip() else f"col_{i}" for i, h in enumerate(raw_headers[:max_col_idx])]
    rows = [r[:max_col_idx] for r in all_vals[1:] if any(r[:max_col_idx])]

    df = pd.DataFrame(rows, columns=headers)
    logging.info(f"Scaricati con successo {len(df)} record dal foglio '{worksheet.title}'.")
    return df


def parse_numeric_value(val_str: any, default: float = 0.0) -> float:
    """
    Estrae e normalizza valori numerici gestendo formati internazionali ed europei:
    - Rimuove simboli valutari (€, $, £) e caratteri non numerici ('x', '-')
    - Gestisce sia '1.074,92' (migliaia . e decimali ,) sia '0,00232238' (decimali ,)
    """
    if val_str is None or pd.isna(val_str):
        return default
    s = str(val_str).replace("€", "").replace("$", "").replace("£", "").replace("x", "").replace("-", "").strip()
    if not s:
        return default
    s = s.replace(" ", "")
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default


def normalize_gsheet_columns(df_raw: pd.DataFrame, is_crypto: bool = False, default_currency: str = "EUR") -> pd.DataFrame:
    """
    Normalizza il foglio Google Sheets secondo le regole ARGUS & Wealth:
    - Supporta sia Stocks/ETF sia Criptovalute.
    - Gestisce colonne A-H: Date, Security, Action, Quantity, Price, Price£, Price$/Price£ - Comm, Total.
    - Esclude esplicitamente movimenti di cassa/deposito/prelievo (Deposit, Withdrawal).
    - Calcola la quantità esatta ad alta precisione e il costo totale unitario.
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    clean_rows = []

    # Mappatura Ticker specifica per borse europee e crypto
    stock_ticker_mapping = {
        "BIT:ISP": "ISP.MI",
        "CPH:NOVO-B": "NOVO-B.CO",
        "LON:NDIA": "NDIA.L",
        "EPA:DFNS": "DFNS.PA",
        "EPA:DFND": "DFND.PA",
        "PRX": "PRX.AS",
        "IMAE": "IMEA.SW",
    }

    for idx, r in df_raw.iterrows():
        # Lookups flessibili per nome colonna
        date_str = str(r.get("Date", r.get("Data", r.get("tx_date", "")))).strip()
        security = str(r.get("Security", r.get("Ticker", r.get("Asset", r.get("Coin", r.get("ticker", "")))))).strip().upper()
        action_str = str(r.get("Action", r.get("Tipo", r.get("Type", r.get("tx_type", ""))))).strip().lower()
        qty_str = r.get("Quantity", r.get("Quantità", r.get("Amount", r.get("Qty", r.get("quantity", "")))))
        type_str = str(r.get("Type", r.get("Categoria", r.get("Asset Class", r.get("asset_class", ""))))).strip().lower()
        
        # Colonne Prezzo e Totale
        price_unit_str = r.get("Price£", r.get("Price€", r.get("PriceEUR", r.get("Price", ""))))
        total_str = r.get("Total", r.get("Totale", r.get("Cost", r.get("Importo", ""))))
        curr_str = str(r.get("Currency", r.get("Valuta", r.get("currency", default_currency)))).strip().upper()
        fees_str = r.get("Fees", r.get("Commissioni", r.get("fees", "0")))

        # Rule 1: Esclusione movimenti non di mercato (Cash, Depositi, Prelievi, Cassa)
        if not security or security in [
            "CASH", "CASH EUR", "CASH USD", "EUR", "USD", "INTEREST",
            "FLATEX INTEREST", "CURRENCY", "TOTAL", "TOTALE", "X", "NAN", "NONE", "NULL", "DEPOSIT", "WITHDRAWAL"
        ]:
            continue

        if action_str in [
            "deposit", "withdrawal", "deposito", "prelievo", "transfer", "trasferimento",
            "cash deposit", "cash withdrawal"
        ]:
            continue

        currency = curr_str if curr_str in ["EUR", "USD", "GBP", "CHF", "BTC", "ETH", "USDT"] else default_currency

        # Determine if this row is Crypto
        row_is_crypto = is_crypto or ("crypto" in type_str) or ("coin" in type_str) or (security in CRYPTO_SYMBOLS)

        if row_is_crypto:
            asset_class = "crypto"
            # Format crypto ticker with currency pair (e.g. BTC -> BTC-EUR or BTC-USD)
            if not "-" in security:
                pair_curr = currency if currency in ["EUR", "USD"] else "EUR"
                security = f"{security}-{pair_curr}"
        else:
            security = stock_ticker_mapping.get(security, security)
            asset_class = "etf" if "etf" in type_str else "stock"

        # Rule 2: Action mapping
        if action_str in ["buy", "acquisto", "acquistato", "buy/long", "staking", "reward", "airdrop"]:
            tx_type = "buy"
        elif action_str in ["sell", "vendita", "venduto", "sell/short"]:
            tx_type = "sell"
        elif action_str in ["dividend", "dividendo", "distribution", "cedola"]:
            tx_type = "dividend"
        else:
            continue

        # Rule 3: Quantity Parsing
        if tx_type == "dividend":
            quantity = 1.0
        else:
            quantity = parse_numeric_value(qty_str, 0.0)

        if quantity <= 0:
            continue

        # Rule 4: Total cost & Unit price calculation
        total_val = parse_numeric_value(total_str, 0.0)
        unit_price_val = parse_numeric_value(price_unit_str, 0.0)

        if total_val > 0 and quantity > 0:
            unit_price = total_val / quantity
        elif unit_price_val > 0:
            unit_price = unit_price_val
            total_val = unit_price * quantity
        else:
            # Staking reward / airdrop a costo nominale zero
            unit_price = 0.000001
            total_val = 0.0

        # Parse fees
        fees = parse_numeric_value(fees_str, 0.0)

        clean_rows.append({
            "tx_date": date_str,
            "ticker": security,
            "tx_type": tx_type,
            "quantity": quantity,
            "price": round(unit_price, 6),
            "currency": currency,
            "fees": fees,
            "asset_class": asset_class,
            "notes": f"Total GSheet ({'Crypto' if row_is_crypto else 'Stocks'}): {total_val:.2f} {currency}"
        })

    return pd.DataFrame(clean_rows)


def sync_single_tab(
    spreadsheet_identifier: str,
    sheet_tab_name: str,
    portfolio_name: str,
    portfolio_tag: str = "Generale",
    is_crypto: bool = False,
    benchmark: str = "SPY",
    db_engine = None,
    offline_mode: bool = False,
    run_name: str = "Daily Automatic Sync"
) -> dict:
    """
    Esegue l'intero ciclo ETL per un singolo tab (Stocks o Crypto):
    1. Scarica e normalizza i dati da Google Sheets
    2. Valida i dati tramite core/validator.py
    3. Inserisce/aggiorna il portafoglio dedicato su MySQL/SQLite
    4. Calcola il profilo di rischio quantitativo
    5. Persiste lo snapshot nel DB e salva il profilo nel registro Multi-Portafoglio.
    """
    logging.info(f"--- Sincronizzazione Tab '{sheet_tab_name}' -> Portafoglio '{portfolio_name}' ---")
    
    # 1. Download & Normalize
    df_raw = fetch_sheet_dataframe(spreadsheet_identifier, sheet_tab_name)
    df_norm = normalize_gsheet_columns(df_raw, is_crypto=is_crypto)

    if df_norm.empty:
        raise ValueError(f"Nessuna transazione valida trovata nel foglio '{sheet_tab_name}'.")

    # 2. Validation
    df_clean, report = validate_csv(df_norm)
    if report["errors"]:
        logging.error(f"Validazione fallita per '{sheet_tab_name}': {report['errors']}")
        raise ValueError(f"Validazione fallita: {report['errors']}")

    logging.info(f"Tab '{sheet_tab_name}' validato con successo ({len(df_clean)} righe, {len(report['stats']['tickers'])} ticker).")

    portfolio_id = 1
    if not offline_mode and db_engine:
        from sqlalchemy import text as sqlt
        from core.db_exporter import get_or_create_portfolio_id
        with db_engine.begin() as conn:
            portfolio_id = get_or_create_portfolio_id(conn, name=portfolio_name, owner="gsheets_cron", base_currency="EUR")

            conn.execute(sqlt("DELETE FROM transactions WHERE portfolio_id = :pid"), {"pid": portfolio_id})

            for _, row in df_clean.iterrows():
                conn.execute(sqlt("""
                    INSERT INTO assets (ticker, name, asset_class, currency)
                    VALUES (:ticker, :ticker, :asset_class, :currency)
                    ON DUPLICATE KEY UPDATE name=VALUES(name)
                """), {
                    "ticker": row["ticker"],
                    "asset_class": "crypto" if is_crypto else ("stock" if pd.isna(row.get("asset_class")) else row.get("asset_class")),
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
                    "fees": float(row.get("fees", 0.0)),
                    "notes": str(row.get("notes", ""))[:255] if row.get("notes") else None,
                })

    # 3. Fetch Market Data & Compute Risk
    if offline_mode or not db_engine:
        fetch_report, df_tx, df_prices = fetch_and_store(df_clean, None, portfolio_id, benchmark_ticker=benchmark)
        results = compute_risk(portfolio_id, None, benchmark_ticker=benchmark, df_tx=df_tx, df_prices=df_prices)
    else:
        fetch_report = fetch_and_store(df_clean, db_engine, portfolio_id, benchmark_ticker=benchmark)
        results = compute_risk(portfolio_id, db_engine, benchmark_ticker=benchmark)

    # 4. Snapshot Persistence su DB
    run_id = f"ANL-CRON-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    if not offline_mode and db_engine:
        save_snapshot_to_db(results, db_engine, portfolio_id, run_id, run_name)
        logging.info(f"Snapshot salvato nel DB per '{portfolio_name}' (Run ID: {run_id}).")

    # 5. Registrazione Automatica nel Total Wealth Hub (Multi-Portafoglio)
    try:
        save_portfolio_profile(
            name=portfolio_name,
            results=results,
            tag=portfolio_tag,
            description=f"Sincronizzazione automatica Google Sheets ({sheet_tab_name}) — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        logging.info(f"Profilo '{portfolio_name}' salvato con successo nel registro Multi-Portafoglio.")
    except Exception as e:
        logging.warning(f"Salvataggio profilo Multi-Portafoglio per '{portfolio_name}' fallito: {e}")

    return {
        "success": True,
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio_name,
        "results": results,
        "run_id": run_id,
        "report": report,
        "fetch_report": fetch_report,
        "tab_name": sheet_tab_name
    }


def run_daily_pipeline(
    spreadsheet_identifier: str = DEFAULT_SPREADSHEET,
    sheet_tab_name: str = None,
    mode: str = "both",
    stocks_tab: str = DEFAULT_STOCKS_TAB,
    crypto_tab: str = DEFAULT_CRYPTO_TAB,
    stocks_portfolio_name: str = DEFAULT_STOCKS_PORTFOLIO,
    crypto_portfolio_name: str = DEFAULT_CRYPTO_PORTFOLIO,
    custom_tab: str = None,
    custom_portfolio_name: str = None,
    benchmark: str = "SPY",
    return_results: bool = False
):
    """
    Esegue l'intera pipeline ETL per Google Sheets:
    - mode='both': Sincronizza sia Stocks che Crypto separatamente su DB e registra entrambi in Multi-Portafoglio.
    - mode='stocks': Sincronizza solo il tab Stocks.
    - mode='crypto': Sincronizza solo il tab Crypto.
    - mode='custom': Sincronizza un tab personalizzato.
    """
    logging.info(f"=== AVVIO PIPELINE GOOGLE SHEETS ARGUS (Modalità: {mode.upper()}) ===")
    
    # Rilevamento automatico modalità se sheet_tab_name è passato in modo esplicito (retrocompatibilità)
    if sheet_tab_name:
        tab_clean = sheet_tab_name.strip().lower()
        if "crypto" in tab_clean:
            mode = "crypto"
            crypto_tab = sheet_tab_name
        elif "stock" in tab_clean:
            mode = "stocks"
            stocks_tab = sheet_tab_name
        elif tab_clean in ["both", "tutti"]:
            mode = "both"
        else:
            mode = "custom"
            custom_tab = sheet_tab_name
            if not custom_portfolio_name:
                custom_portfolio_name = f"Wealth {sheet_tab_name} Portfolio"

    # Inizializzazione connessione Database
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

    try:
        from sqlalchemy import create_engine, text as sqlt
        temp_engine = create_engine(f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/", echo=False)
        with temp_engine.begin() as conn:
            conn.execute(sqlt(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))

        engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
        ensure_snapshot_tables(engine)
        offline_mode = False
    except Exception as e:
        logging.warning(f"Connessione MySQL non disponibile ({e}). Esecuzione in modalità offline/in-memory.")
        engine = None
        offline_mode = True

    # Esecuzione in base alla modalità selezionata
    if mode == "both":
        res_stocks = sync_single_tab(
            spreadsheet_identifier=spreadsheet_identifier,
            sheet_tab_name=stocks_tab,
            portfolio_name=stocks_portfolio_name,
            portfolio_tag="Azionario & ETF",
            is_crypto=False,
            benchmark=benchmark,
            db_engine=engine,
            offline_mode=offline_mode,
            run_name="Daily Automatic Sync"
        )
        
        res_crypto = sync_single_tab(
            spreadsheet_identifier=spreadsheet_identifier,
            sheet_tab_name=crypto_tab,
            portfolio_name=crypto_portfolio_name,
            portfolio_tag="Crypto Assets",
            is_crypto=True,
            benchmark=benchmark,
            db_engine=engine,
            offline_mode=offline_mode,
            run_name="Daily Automatic Sync"
        )

        # Consolidamento virtuale Master Wealth
        master_results = None
        try:
            master_results = consolidate_multi_portfolios([stocks_portfolio_name, crypto_portfolio_name])
            if master_results:
                save_portfolio_profile(
                    name="Master Wealth Google Sheets",
                    results=master_results,
                    tag="Consolidato Multi-Asset",
                    description=f"Consolidamento Master Wealth (Stocks + Crypto) — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
        except Exception as e:
            logging.warning(f"Consolidamento Master Wealth automatico non riuscito: {e}")

        dual_info = {
            "stocks": res_stocks,
            "crypto": res_crypto,
            "master": master_results
        }
        
        logging.info("=== PIPELINE DUALE COMPLETATA CON SUCCESSO (Stocks & Crypto) ===")
        if return_results:
            active_results = master_results if master_results else res_stocks["results"]
            active_name = "Master Wealth (Stocks + Crypto)" if master_results else stocks_portfolio_name
            return True, active_results, res_stocks["run_id"], active_name, res_stocks["fetch_report"], dual_info
        return True

    elif mode == "stocks":
        res = sync_single_tab(
            spreadsheet_identifier=spreadsheet_identifier,
            sheet_tab_name=stocks_tab,
            portfolio_name=stocks_portfolio_name,
            portfolio_tag="Azionario & ETF",
            is_crypto=False,
            benchmark=benchmark,
            db_engine=engine,
            offline_mode=offline_mode,
            run_name="Daily Automatic Sync"
        )
        if return_results:
            return True, res["results"], res["run_id"], res["portfolio_name"], res["fetch_report"], {"stocks": res}
        return True

    elif mode == "crypto":
        res = sync_single_tab(
            spreadsheet_identifier=spreadsheet_identifier,
            sheet_tab_name=crypto_tab,
            portfolio_name=crypto_portfolio_name,
            portfolio_tag="Crypto Assets",
            is_crypto=True,
            benchmark=benchmark,
            db_engine=engine,
            offline_mode=offline_mode,
            run_name="Daily Automatic Sync"
        )
        if return_results:
            return True, res["results"], res["run_id"], res["portfolio_name"], res["fetch_report"], {"crypto": res}
        return True

    else:  # Custom
        tab = custom_tab or DEFAULT_STOCKS_TAB
        p_name = custom_portfolio_name or f"Wealth {tab} Portfolio"
        is_cr = "crypto" in tab.lower()
        res = sync_single_tab(
            spreadsheet_identifier=spreadsheet_identifier,
            sheet_tab_name=tab,
            portfolio_name=p_name,
            portfolio_tag="Crypto Assets" if is_cr else "Azionario & ETF",
            is_crypto=is_cr,
            benchmark=benchmark,
            db_engine=engine,
            offline_mode=offline_mode,
            run_name="Daily Automatic Sync"
        )
        if return_results:
            return True, res["results"], res["run_id"], res["portfolio_name"], res["fetch_report"], {"custom": res}
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ARGUS Google Sheets ETL & Dual Risk Pipeline Sync")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SPREADSHEET, help="Nome o ID dello Spreadsheet Google Sheets")
    parser.add_argument("--mode", type=str, default="both", choices=["both", "stocks", "crypto", "custom"], help="Modalità di estrazione (default: both)")
    parser.add_argument("--stocks-tab", type=str, default=DEFAULT_STOCKS_TAB, help=f"Nome del foglio Stocks (default: {DEFAULT_STOCKS_TAB})")
    parser.add_argument("--crypto-tab", type=str, default=DEFAULT_CRYPTO_TAB, help=f"Nome del foglio Crypto (default: {DEFAULT_CRYPTO_TAB})")
    parser.add_argument("--tab", type=str, default=None, help="Nome del foglio per modalità custom o retrocompatibilità")
    parser.add_argument("--stocks-name", type=str, default=DEFAULT_STOCKS_PORTFOLIO, help="Nome portafoglio Stocks su DB")
    parser.add_argument("--crypto-name", type=str, default=DEFAULT_CRYPTO_PORTFOLIO, help="Nome portafoglio Crypto su DB")
    
    args = parser.parse_args()
    run_daily_pipeline(
        spreadsheet_identifier=args.sheet,
        sheet_tab_name=args.tab,
        mode=args.mode,
        stocks_tab=args.stocks_tab,
        crypto_tab=args.crypto_tab,
        stocks_portfolio_name=args.stocks_name,
        crypto_portfolio_name=args.crypto_name
    )
