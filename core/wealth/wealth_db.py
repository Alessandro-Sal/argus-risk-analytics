# ============================================================
# core/wealth/wealth_db.py
# ARGUS — Wealth Management Database Layer & CRUD Engine
# Supports MySQL & SQLite transparently with auto-bootstrap
# ============================================================

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from sqlalchemy import text as sqlt, Engine, Connection

from core.fetcher import get_engine
from core.wealth.wealth_models import (
    WealthAccount,
    WealthCategory,
    WealthCashflowItem,
    PhysicalAssetItem,
    PensionPlanItem,
    AccountType,
    CategoryNature,
    PhysicalAssetCategory
)

# Categorie predefinite di sistema con icone e classificazione per natura
DEFAULT_SYSTEM_CATEGORIES = [
    # Entrate
    {"name": "Stipendio / Compensi", "flow_type": "income", "nature": "inflow_active", "icon": "💼", "color": "#10b981"},
    {"name": "Bonus / Straordinari", "flow_type": "income", "nature": "inflow_active", "icon": "🎁", "color": "#34d399"},
    {"name": "Dividendi & Cedole", "flow_type": "income", "nature": "inflow_passive", "icon": "📈", "color": "#059669"},
    {"name": "Affitti & Rendite Immobiliari", "flow_type": "income", "nature": "inflow_passive", "icon": "🏠", "color": "#047857"},
    {"name": "Rimborsi & Altre Entrate", "flow_type": "income", "nature": "inflow_active", "icon": "💵", "color": "#6ee7b7"},

    # Spese Primarie (50% Needs)
    {"name": "Casa & Mutuo / Affitto", "flow_type": "expense", "nature": "essential_need", "icon": "🏠", "color": "#ef4444"},
    {"name": "Bollette & Utenze (Luce/Gas/Internet)", "flow_type": "expense", "nature": "essential_need", "icon": "⚡", "color": "#f87171"},
    {"name": "Spesa Alimentare & Supermercato", "flow_type": "expense", "nature": "essential_need", "icon": "🛒", "color": "#dc2626"},
    {"name": "Trasporti, Carburante & Mezzi", "flow_type": "expense", "nature": "essential_need", "icon": "🚗", "color": "#b91c1c"},
    {"name": "Salute, Farmaci & Visite", "flow_type": "expense", "nature": "essential_need", "icon": "🏥", "color": "#991b1b"},
    {"name": "Assicurazioni & Bolli", "flow_type": "expense", "nature": "essential_need", "icon": "🛡️", "color": "#7f1d1d"},

    # Spese Discrezionali (30% Wants)
    {"name": "Ristoranti, Bar & Delivery", "flow_type": "expense", "nature": "discretionary_want", "icon": "🍽️", "color": "#f59e0b"},
    {"name": "Viaggi, Vacanze & Weekend", "flow_type": "expense", "nature": "discretionary_want", "icon": "✈️", "color": "#fbbf24"},
    {"name": "Shopping & Abbigliamento", "flow_type": "expense", "nature": "discretionary_want", "icon": "🛍️", "color": "#d97706"},
    {"name": "Svago, Cinema & Eventi", "flow_type": "expense", "nature": "discretionary_want", "icon": "🎟️", "color": "#b45309"},
    {"name": "Abbonamenti, Tech & Streaming", "flow_type": "expense", "nature": "discretionary_want", "icon": "📱", "color": "#92400e"},
    {"name": "Sport, Palestra & Hobby", "flow_type": "expense", "nature": "discretionary_want", "icon": "🎾", "color": "#78350f"},
    {"name": "Lusso & Orologi (Spesa / Manutenzione)", "flow_type": "expense", "nature": "discretionary_want", "icon": "⌚", "color": "#eab308"},

    # Risparmio & Investimenti (20% Savings)
    {"name": "PAC / Investimenti Titoli", "flow_type": "expense", "nature": "saving_investment", "icon": "📊", "color": "#6366f1"},
    {"name": "Versamento Fondo Pensione", "flow_type": "expense", "nature": "saving_investment", "icon": "🛡️", "color": "#818cf8"},
    {"name": "Risparmio Fondo Emergenza", "flow_type": "expense", "nature": "saving_investment", "icon": "💰", "color": "#4f46e5"},

    # Fisco & Oneri Finanziari
    {"name": "Tasse, Imposte & F24", "flow_type": "expense", "nature": "tax", "icon": "🏛️", "color": "#64748b"},
    {"name": "Commissioni Bancarie & Interessi", "flow_type": "expense", "nature": "debt_service", "icon": "🏦", "color": "#475569"},
]


def init_wealth_db(engine: Engine) -> None:
    """Inizializza automaticamente le tabelle del Wealth Management se non presenti."""
    is_sqlite = (getattr(engine, "dialect", None) is not None and engine.dialect.name == "sqlite")

    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_profiles (
                    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner TEXT NOT NULL DEFAULT 'user',
                    base_currency TEXT NOT NULL DEFAULT 'EUR',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_accounts (

                    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    account_type TEXT NOT NULL DEFAULT 'checking',
                    institution TEXT NOT NULL DEFAULT 'Banca',
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    balance REAL NOT NULL DEFAULT 0.0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    iban TEXT,
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_categories (
                    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    flow_type TEXT NOT NULL,
                    nature TEXT NOT NULL DEFAULT 'essential_need',
                    parent_id INTEGER,
                    icon TEXT NOT NULL DEFAULT '🏷️',
                    color TEXT NOT NULL DEFAULT '#6366f1',
                    is_system INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (parent_id) REFERENCES wealth_categories(category_id)
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_cashflow (
                    tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    tx_date DATE NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    direction TEXT NOT NULL,
                    merchant TEXT,
                    notes TEXT,
                    is_recurring INTEGER NOT NULL DEFAULT 0,
                    payment_method TEXT NOT NULL DEFAULT 'Carta / Bonifico',
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES wealth_accounts(account_id),
                    FOREIGN KEY (category_id) REFERENCES wealth_categories(category_id)
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_physical_assets (
                    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    asset_category TEXT NOT NULL DEFAULT 'luxury_watches',
                    brand_or_location TEXT,
                    model_or_specs TEXT,
                    reference_number TEXT,
                    acquisition_date DATE,
                    purchase_price REAL NOT NULL DEFAULT 0.0,
                    current_market_value REAL NOT NULL DEFAULT 0.0,
                    valuation_date DATE,
                    valuation_source TEXT DEFAULT 'Stima di Mercato',
                    condition_grade TEXT DEFAULT 'Eccellente / Full Set',
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_pension_plans (
                    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    plan_type TEXT NOT NULL DEFAULT 'fondo_pensione_aperto',
                    accumulated_value REAL NOT NULL DEFAULT 0.0,
                    monthly_employee_contrib REAL NOT NULL DEFAULT 0.0,
                    monthly_employer_contrib REAL NOT NULL DEFAULT 0.0,
                    tax_deductible_annual REAL NOT NULL DEFAULT 0.0,
                    expected_retirement_age INTEGER NOT NULL DEFAULT 67,
                    currency TEXT NOT NULL DEFAULT 'EUR',
                    investment_line TEXT DEFAULT 'Azionario / Crescita',
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL DEFAULT 1,
                    run_id TEXT,
                    snapshot_date DATE NOT NULL,
                    snapshot_name TEXT DEFAULT 'Snapshot Patrimoniale',
                    total_net_worth REAL NOT NULL,
                    liquid_assets REAL NOT NULL DEFAULT 0.0,
                    financial_investments REAL NOT NULL DEFAULT 0.0,
                    physical_assets_total REAL NOT NULL DEFAULT 0.0,
                    watches_total REAL NOT NULL DEFAULT 0.0,
                    real_estate_total REAL NOT NULL DEFAULT 0.0,
                    pension_total REAL NOT NULL DEFAULT 0.0,
                    total_liabilities REAL NOT NULL DEFAULT 0.0,
                    monthly_income_avg REAL NOT NULL DEFAULT 0.0,
                    monthly_expense_avg REAL NOT NULL DEFAULT 0.0,
                    savings_rate_pct REAL NOT NULL DEFAULT 0.0,
                    emergency_runway_months REAL NOT NULL DEFAULT 0.0,
                    wealth_health_score REAL NOT NULL DEFAULT 0.0,
                    details_json TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_fixed_expenses (
                    fixed_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL DEFAULT 1,
                    category TEXT NOT NULL,
                    note TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_day INTEGER,
                    start_date DATE,
                    end_date DATE,
                    is_split INTEGER DEFAULT 0,
                    split_details TEXT,
                    cadence TEXT DEFAULT 'Mensile',
                    is_active INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))

        else:
            # MySQL DDL
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_profiles (
                    profile_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    description TEXT NULL,
                    owner VARCHAR(100) NOT NULL DEFAULT 'user',
                    base_currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_accounts (

                    account_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    account_type VARCHAR(50) NOT NULL DEFAULT 'checking',
                    institution VARCHAR(100) NOT NULL DEFAULT 'Banca',
                    currency CHAR(3) NOT NULL DEFAULT 'EUR',
                    balance DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    iban VARCHAR(35) NULL,
                    notes VARCHAR(255) NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_categories (
                    category_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    flow_type VARCHAR(20) NOT NULL,
                    nature VARCHAR(50) NOT NULL DEFAULT 'essential_need',
                    parent_id INT NULL,
                    icon VARCHAR(50) NOT NULL DEFAULT '🏷️',
                    color VARCHAR(20) NOT NULL DEFAULT '#6366f1',
                    is_system BOOLEAN NOT NULL DEFAULT FALSE,
                    CONSTRAINT fk_cat_parent FOREIGN KEY (parent_id)
                        REFERENCES wealth_categories (category_id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_cashflow (
                    tx_id INT AUTO_INCREMENT PRIMARY KEY,
                    account_id INT NOT NULL,
                    category_id INT NOT NULL,
                    tx_date DATE NOT NULL,
                    amount DECIMAL(18,2) NOT NULL,
                    currency CHAR(3) NOT NULL DEFAULT 'EUR',
                    direction VARCHAR(20) NOT NULL,
                    merchant VARCHAR(150) NULL,
                    notes VARCHAR(255) NULL,
                    is_recurring BOOLEAN NOT NULL DEFAULT FALSE,
                    payment_method VARCHAR(50) NOT NULL DEFAULT 'Carta / Bonifico',
                    tags VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_wf_account FOREIGN KEY (account_id)
                        REFERENCES wealth_accounts (account_id) ON DELETE CASCADE,
                    CONSTRAINT fk_wf_category FOREIGN KEY (category_id)
                        REFERENCES wealth_categories (category_id) ON DELETE RESTRICT,
                    INDEX idx_cashflow_date (tx_date),
                    INDEX idx_cashflow_acc_date (account_id, tx_date DESC),
                    INDEX idx_cashflow_cat_date (category_id, tx_date DESC)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_physical_assets (
                    asset_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    asset_category VARCHAR(50) NOT NULL DEFAULT 'luxury_watches',
                    brand_or_location VARCHAR(100) NULL,
                    model_or_specs VARCHAR(150) NULL,
                    reference_number VARCHAR(100) NULL,
                    acquisition_date DATE NULL,
                    purchase_price DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    current_market_value DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    valuation_date DATE NULL,
                    valuation_source VARCHAR(100) NULL DEFAULT 'Stima di Mercato',
                    condition_grade VARCHAR(50) NULL DEFAULT 'Eccellente / Full Set',
                    currency CHAR(3) NOT NULL DEFAULT 'EUR',
                    notes TEXT NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_pension_plans (
                    plan_id INT AUTO_INCREMENT PRIMARY KEY,
                    plan_name VARCHAR(150) NOT NULL,
                    provider VARCHAR(100) NOT NULL,
                    plan_type VARCHAR(50) NOT NULL DEFAULT 'fondo_pensione_aperto',
                    accumulated_value DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    monthly_employee_contrib DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    monthly_employer_contrib DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    tax_deductible_annual DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    expected_retirement_age INT NOT NULL DEFAULT 67,
                    currency CHAR(3) NOT NULL DEFAULT 'EUR',
                    investment_line VARCHAR(100) NULL DEFAULT 'Azionario / Crescita',
                    notes TEXT NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
                    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
                    portfolio_id INT NOT NULL DEFAULT 1,
                    run_id VARCHAR(64) NULL,
                    snapshot_date DATE NOT NULL,
                    snapshot_name VARCHAR(150) NULL DEFAULT 'Snapshot Patrimoniale',
                    total_net_worth DECIMAL(18,2) NOT NULL,
                    liquid_assets DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    financial_investments DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    physical_assets_total DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    watches_total DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    real_estate_total DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    pension_total DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    total_liabilities DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    monthly_income_avg DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    monthly_expense_avg DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                    savings_rate_pct DECIMAL(10,4) NOT NULL DEFAULT 0.00,
                    emergency_runway_months DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    wealth_health_score DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    details_json LONGTEXT NULL,
                    notes VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_wealth_snap_date (snapshot_date),
                    INDEX idx_wealth_snap_run (run_id),
                    INDEX idx_snap_port_date (portfolio_id, snapshot_date DESC)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(sqlt("""
                CREATE TABLE IF NOT EXISTS wealth_fixed_expenses (
                    fixed_id INT AUTO_INCREMENT PRIMARY KEY,
                    portfolio_id INT NOT NULL DEFAULT 1,
                    category VARCHAR(100) NOT NULL,
                    note VARCHAR(255) NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    payment_day INT NULL,
                    start_date DATE NULL,
                    end_date DATE NULL,
                    is_split BOOLEAN NOT NULL DEFAULT FALSE,
                    split_details VARCHAR(255) NULL,
                    cadence VARCHAR(50) NOT NULL DEFAULT 'Mensile',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_fixed_port (portfolio_id, is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))


        # Migrazione colonne snapshot_name, details_json, run_id e portfolio_id se mancanti
        try:
            if is_sqlite:
                cols = [r[1] for r in conn.execute(sqlt("PRAGMA table_info(wealth_networth_snapshots)")).fetchall()]
                if "snapshot_name" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN snapshot_name TEXT DEFAULT 'Snapshot Patrimoniale'"))
                if "details_json" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN details_json TEXT"))
                if "run_id" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN run_id TEXT"))
                
                # Migrazione portfolio_id su tutte le tabelle wealth
                for t in ["wealth_accounts", "wealth_cashflow", "wealth_physical_assets", "wealth_pension_plans", "wealth_networth_snapshots"]:
                    t_cols = [r[1] for r in conn.execute(sqlt(f"PRAGMA table_info({t})")).fetchall()]
                    if "portfolio_id" not in t_cols:
                        conn.execute(sqlt(f"ALTER TABLE {t} ADD COLUMN portfolio_id INTEGER DEFAULT 1"))
            else:
                cols = [r[0] for r in conn.execute(sqlt("SHOW COLUMNS FROM wealth_networth_snapshots")).fetchall()]
                if "snapshot_name" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN snapshot_name VARCHAR(150) NULL DEFAULT 'Snapshot Patrimoniale'"))
                if "details_json" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN details_json LONGTEXT NULL"))
                if "run_id" not in cols:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots ADD COLUMN run_id VARCHAR(64) NULL"))
                
                try:
                    conn.execute(sqlt("ALTER TABLE wealth_networth_snapshots DROP INDEX uq_wealth_snap_date"))
                except Exception:
                    pass

                # Migrazione portfolio_id su tutte le tabelle wealth
                for t in ["wealth_accounts", "wealth_cashflow", "wealth_physical_assets", "wealth_pension_plans", "wealth_networth_snapshots"]:
                    t_cols = [r[0] for r in conn.execute(sqlt(f"SHOW COLUMNS FROM {t}")).fetchall()]
                    if "portfolio_id" not in t_cols:
                        conn.execute(sqlt(f"ALTER TABLE {t} ADD COLUMN portfolio_id INT NOT NULL DEFAULT 1"))
        except Exception:
            pass

        # Assicura la presenza della tabella portfolios e di almeno un portafoglio di default
        try:
            if is_sqlite:
                conn.execute(sqlt("""
                    CREATE TABLE IF NOT EXISTS portfolios (
                        portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        owner TEXT NOT NULL DEFAULT 'user',
                        base_currency TEXT NOT NULL DEFAULT 'EUR',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """))
            else:
                conn.execute(sqlt("""
                    CREATE TABLE IF NOT EXISTS portfolios (
                        portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        owner VARCHAR(100) NOT NULL DEFAULT 'user',
                        base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        description TEXT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                try:
                    conn.execute(sqlt("ALTER TABLE portfolios MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"))
                except Exception:
                    pass
            
            p_cnt = conn.execute(sqlt("SELECT COUNT(*) FROM portfolios")).scalar()
            if p_cnt == 0:
                conn.execute(sqlt("""
                    INSERT INTO portfolios (name, owner, base_currency, description, created_at)
                    VALUES ('Patrimonio Personale', 'user', 'EUR', 'Portafoglio e Profilo Patrimoniale Principale', CURRENT_TIMESTAMP)
                """))
        except Exception:
            pass

        # Tabella di collegamento tra Profili Wealth e Portafogli Risk
        try:
            if is_sqlite:
                conn.execute(sqlt("""
                    CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
                        wealth_portfolio_id INTEGER NOT NULL,
                        risk_portfolio_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (wealth_portfolio_id, risk_portfolio_id)
                    );
                """))
            else:
                conn.execute(sqlt("""
                    CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
                        wealth_portfolio_id INT NOT NULL,
                        risk_portfolio_id INT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (wealth_portfolio_id, risk_portfolio_id),
                        INDEX idx_wprl_w (wealth_portfolio_id),
                        INDEX idx_wprl_r (risk_portfolio_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
        except Exception:
            pass

    seed_default_categories(engine)




def seed_default_categories(engine: Engine) -> None:
    """Popola le categorie di default se la tabella è vuota."""
    with engine.begin() as conn:
        cnt = conn.execute(sqlt("SELECT COUNT(*) FROM wealth_categories")).scalar()
        if cnt == 0:
            for cat in DEFAULT_SYSTEM_CATEGORIES:
                conn.execute(sqlt("""
                    INSERT INTO wealth_categories (name, flow_type, nature, icon, color, is_system)
                    VALUES (:name, :flow_type, :nature, :icon, :color, 1)
                """), cat)


def _get_last_insert_id(conn: Connection, engine: Engine) -> int:
    """Ritorna l'ultimo ID inserito in modo compatibile sia con SQLite che con MySQL."""
    is_sqlite = (getattr(engine, "dialect", None) is not None and engine.dialect.name == "sqlite")
    sql = "SELECT last_insert_rowid()" if is_sqlite else "SELECT LAST_INSERT_ID()"
    val = conn.execute(sqlt(sql)).scalar()
    return int(val) if val else 1


# ── CATEGORIES CRUD ─────────────────────────────────────────


def get_wealth_categories(engine: Engine) -> pd.DataFrame:
    """Recupera tutte le categorie di spesa ed entrata."""
    init_wealth_db(engine)
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM wealth_categories ORDER BY flow_type ASC, name ASC", conn)


def save_wealth_category(engine: Engine, category: Dict[str, Any]) -> int:
    """Crea o aggiorna una categoria."""
    init_wealth_db(engine)
    cat_id = category.get("category_id")
    params = {
        "name": category["name"],
        "flow_type": category.get("flow_type", "expense"),
        "nature": category.get("nature", "essential_need"),
        "parent_id": category.get("parent_id"),
        "icon": category.get("icon", "🏷️"),
        "color": category.get("color", "#6366f1"),
    }
    with engine.begin() as conn:
        if cat_id:
            params["cid"] = cat_id
            conn.execute(sqlt("""
                UPDATE wealth_categories
                SET name=:name, flow_type=:flow_type, nature=:nature,
                    parent_id=:parent_id, icon=:icon, color=:color
                WHERE category_id = :cid
            """), params)
            return cat_id
        else:
            conn.execute(sqlt("""
                INSERT INTO wealth_categories (name, flow_type, nature, parent_id, icon, color, is_system)
                VALUES (:name, :flow_type, :nature, :parent_id, :icon, :color, 0)
            """), params)
            return _get_last_insert_id(conn, engine)


# ── PORTFOLIOS & PROFILES CRUD ──────────────────────────────


def get_wealth_portfolios(engine: Engine) -> pd.DataFrame:
    """Recupera l'elenco dei profili patrimoniali dalla tabella dedicata wealth_profiles."""
    init_wealth_db(engine)
    with engine.connect() as conn:
        df = pd.read_sql("""
            SELECT profile_id AS portfolio_id, name, owner, base_currency, created_at, description 
            FROM wealth_profiles 
            WHERE name IS NOT NULL AND TRIM(name) != ''
            ORDER BY profile_id ASC
        """, conn)
    
    if df.empty:
        with engine.begin() as wconn:
            wconn.execute(sqlt("""
                INSERT INTO wealth_profiles (name, owner, base_currency, description, created_at)
                VALUES ('Personale', 'user', 'EUR', 'Profilo Patrimoniale Principale', CURRENT_TIMESTAMP)
            """))
        with engine.connect() as conn2:
            df = pd.read_sql("""
                SELECT profile_id AS portfolio_id, name, owner, base_currency, created_at, description 
                FROM wealth_profiles 
                WHERE name IS NOT NULL AND TRIM(name) != ''
                ORDER BY profile_id ASC
            """, conn2)
    return df



def cleanup_empty_wealth_portfolios(engine: Engine) -> int:
    """Elimina i profili con nome vuoto o non valido dalla tabella wealth_profiles."""
    init_wealth_db(engine)
    with engine.begin() as conn:
        res = conn.execute(sqlt("DELETE FROM wealth_profiles WHERE (name IS NULL OR TRIM(name) = '') AND profile_id != 1"))
        return res.rowcount if hasattr(res, "rowcount") else 0


def create_wealth_portfolio(engine: Engine, name: str, description: Optional[str] = None, owner: str = "user") -> int:
    """Crea un nuovo profilo patrimoniale dedicato nella tabella wealth_profiles."""
    init_wealth_db(engine)
    clean_name = (name or "").strip()
    if not clean_name:
        clean_name = "Nuovo Profilo"
    with engine.begin() as conn:
        existing_id = conn.execute(
            sqlt("SELECT profile_id FROM wealth_profiles WHERE LOWER(TRIM(name)) = LOWER(TRIM(:name)) ORDER BY profile_id ASC LIMIT 1"),
            {"name": clean_name}
        ).scalar()
        if existing_id:
            return int(existing_id)

        conn.execute(sqlt("""
            INSERT INTO wealth_profiles (name, owner, base_currency, description, created_at)
            VALUES (:name, :owner, 'EUR', :desc, CURRENT_TIMESTAMP)
        """), {"name": clean_name, "owner": owner, "desc": description or ""})
        return _get_last_insert_id(conn, engine)


def delete_wealth_portfolio(engine: Engine, portfolio_id: int) -> bool:
    """Elimina un profilo patrimoniale e tutti i dati associati (conti, cashflow, asset, snapshot, link risk).
    NON tocca in alcun modo le tabelle del modulo Risk (portfolios, portfolio_snapshots, transactions)."""
    init_wealth_db(engine)
    with engine.begin() as conn:
        for tbl in [
            "wealth_cashflow", "wealth_accounts", "wealth_physical_assets",
            "wealth_pension_plans", "wealth_networth_snapshots",
            "wealth_portfolio_risk_links"
        ]:
            try:
                conn.execute(
                    sqlt(f"DELETE FROM {tbl} WHERE wealth_portfolio_id = :pid" if tbl == "wealth_portfolio_risk_links" else f"DELETE FROM {tbl} WHERE portfolio_id = :pid"),
                    {"pid": portfolio_id}
                )
            except Exception:
                pass
        try:
            conn.execute(sqlt("DELETE FROM wealth_profiles WHERE profile_id = :pid"), {"pid": portfolio_id})
        except Exception:
            pass
    return True



# ── RISK PORTFOLIOS DYNAMIC LINKAGE ─────────────────────────

def get_available_risk_portfolios(engine: Engine, exclude_wealth_portfolio_id: Optional[int] = None) -> pd.DataFrame:
    """Recupera tutti i portafogli di investimento censiti nel modulo Risk Analytics dal database attivo."""
    init_wealth_db(engine)
    exclude_clause = f"AND p.portfolio_id != {int(exclude_wealth_portfolio_id)}" if exclude_wealth_portfolio_id else ""
    with engine.connect() as conn:
        df = pd.read_sql(f"""
            SELECT 
                p.portfolio_id,
                p.name,
                p.owner,
                p.base_currency,
                p.created_at,
                MAX(s.calc_date) as last_calc_date,
                COUNT(s.snapshot_id) as snapshot_count,
                COALESCE(
                    (SELECT s2.total_value 
                     FROM portfolio_snapshots s2 
                     WHERE s2.portfolio_id = p.portfolio_id 
                     ORDER BY s2.calc_date DESC, s2.snapshot_id DESC LIMIT 1),
                    0.0
                ) as latest_value
            FROM portfolios p
            INNER JOIN portfolio_snapshots s ON p.portfolio_id = s.portfolio_id
            WHERE p.name IS NOT NULL AND TRIM(p.name) != '' {exclude_clause}
            GROUP BY p.portfolio_id, p.name, p.owner, p.base_currency, p.created_at
            HAVING COUNT(s.snapshot_id) > 0
            ORDER BY latest_value DESC, p.portfolio_id ASC
        """, conn)
        return df


def get_linked_risk_portfolios(engine: Engine, wealth_portfolio_id: int = 1) -> List[int]:
    """Recupera la lista degli ID dei portafogli Risk Analytics collegati al profilo Wealth."""
    init_wealth_db(engine)
    with engine.connect() as conn:
        rows = conn.execute(
            sqlt("""
                SELECT risk_portfolio_id 
                FROM wealth_portfolio_risk_links 
                WHERE wealth_portfolio_id = :wpid AND risk_portfolio_id != :wpid 
                ORDER BY risk_portfolio_id ASC
            """),
            {"wpid": wealth_portfolio_id}
        ).fetchall()
        return [int(r[0]) for r in rows]


def set_linked_risk_portfolios(engine: Engine, wealth_portfolio_id: int, risk_portfolio_ids: List[int]) -> bool:
    """Imposta atomicamente i portafogli Risk Analytics collegati al profilo Wealth (escludendo se stesso)."""
    init_wealth_db(engine)
    clean_rpids = [int(rpid) for rpid in risk_portfolio_ids if int(rpid) != int(wealth_portfolio_id)]
    with engine.begin() as conn:
        conn.execute(
            sqlt("DELETE FROM wealth_portfolio_risk_links WHERE wealth_portfolio_id = :wpid"),
            {"wpid": wealth_portfolio_id}
        )
        for rpid in clean_rpids:
            try:
                conn.execute(
                    sqlt("""
                        INSERT INTO wealth_portfolio_risk_links (wealth_portfolio_id, risk_portfolio_id, created_at)
                        VALUES (:wpid, :rpid, CURRENT_TIMESTAMP)
                    """),
                    {"wpid": wealth_portfolio_id, "rpid": rpid}
                )
            except Exception:
                pass
    return True



def get_linked_risk_portfolios_summary(engine: Engine, wealth_portfolio_id: int = 1) -> Tuple[float, pd.DataFrame]:
    """Ritorna il valore totale aggregato e il dataframe dettagliato dei portafogli Risk collegati al profilo Wealth."""
    init_wealth_db(engine)
    linked_ids = get_linked_risk_portfolios(engine, wealth_portfolio_id)
    if not linked_ids:
        return 0.0, pd.DataFrame()
    
    df_all = get_available_risk_portfolios(engine)
    df_linked = df_all[df_all["portfolio_id"].isin(linked_ids)].copy()
    tot_val = float(df_linked["latest_value"].sum()) if not df_linked.empty else 0.0
    return tot_val, df_linked




# ── DATA LIFECYCLE & RESET UTILITIES ────────────────────────

def clear_wealth_cashflow(
    engine: Engine,
    portfolio_id: Optional[int] = None,
    account_id: Optional[int] = None,
    year: Optional[int] = None
) -> int:
    """Svuota le transazioni del libro mastro cassa secondo i filtri specificati."""
    init_wealth_db(engine)
    query = "DELETE FROM wealth_cashflow WHERE 1=1"
    params = {}
    if portfolio_id is not None:
        query += " AND portfolio_id = :pid"
        params["pid"] = portfolio_id
    if account_id is not None:
        query += " AND account_id = :aid"
        params["aid"] = account_id
    if year is not None:
        query += " AND tx_date >= :sdate AND tx_date <= :edate"
        params["sdate"] = f"{year}-01-01"
        params["edate"] = f"{year}-12-31"

    with engine.begin() as conn:
        res = conn.execute(sqlt(query), params)
        return res.rowcount if hasattr(res, "rowcount") else 0


def clear_wealth_snapshots(engine: Engine, portfolio_id: Optional[int] = None) -> int:
    """Elimina tutti gli snapshot patrimoniali salvati."""
    init_wealth_db(engine)
    query = "DELETE FROM wealth_networth_snapshots WHERE 1=1"
    params = {}
    if portfolio_id is not None:
        query += " AND portfolio_id = :pid"
        params["pid"] = portfolio_id

    with engine.begin() as conn:
        res = conn.execute(sqlt(query), params)
        return res.rowcount if hasattr(res, "rowcount") else 0


def clear_wealth_accounts(engine: Engine, portfolio_id: Optional[int] = None) -> int:
    """Elimina tutti i conti bancari censiti per il profilo (o tutti se portfolio_id è None)."""
    init_wealth_db(engine)
    where_clause = ""
    params = {}
    if portfolio_id is not None:
        if portfolio_id == 1:
            where_clause = " WHERE (portfolio_id = 1 OR portfolio_id IS NULL)"
        else:
            where_clause = " WHERE portfolio_id = :pid"
            params["pid"] = portfolio_id

    with engine.begin() as conn:
        res = conn.execute(sqlt(f"DELETE FROM wealth_accounts{where_clause}"), params)
        return res.rowcount if hasattr(res, "rowcount") else 0


def reset_wealth_portfolio_data(
    engine: Engine,
    portfolio_id: Optional[int] = None,
    keep_accounts: bool = False
) -> Dict[str, int]:
    """
    Esegue il reset totale o parziale dei dati patrimoniali per il profilo selezionato (o globale se portfolio_id è None).
    """
    init_wealth_db(engine)
    results = {}
    where_clause = ""
    params = {}
    if portfolio_id is not None:
        if portfolio_id == 1:
            where_clause = " WHERE (portfolio_id = 1 OR portfolio_id IS NULL)"
        else:
            where_clause = " WHERE portfolio_id = :pid"
            params["pid"] = portfolio_id

    with engine.begin() as conn:
        # 1. Transazioni di cassa
        res_cf = conn.execute(sqlt(f"DELETE FROM wealth_cashflow{where_clause}"), params)
        results["cashflow_deleted"] = res_cf.rowcount if hasattr(res_cf, "rowcount") else 0

        # 2. Snapshot
        res_sn = conn.execute(sqlt(f"DELETE FROM wealth_networth_snapshots{where_clause}"), params)
        results["snapshots_deleted"] = res_sn.rowcount if hasattr(res_sn, "rowcount") else 0

        # 3. Asset fisici
        res_ph = conn.execute(sqlt(f"DELETE FROM wealth_physical_assets{where_clause}"), params)
        results["physical_assets_deleted"] = res_ph.rowcount if hasattr(res_ph, "rowcount") else 0

        # 4. Fondi pensione
        res_pn = conn.execute(sqlt(f"DELETE FROM wealth_pension_plans{where_clause}"), params)
        results["pension_plans_deleted"] = res_pn.rowcount if hasattr(res_pn, "rowcount") else 0

        # 5. Conti (opzionale)
        if not keep_accounts:
            res_ac = conn.execute(sqlt(f"DELETE FROM wealth_accounts{where_clause}"), params)
            results["accounts_deleted"] = res_ac.rowcount if hasattr(res_ac, "rowcount") else 0
        else:
            # Azzera solo i saldi dei conti se vengono mantenuti
            conn.execute(sqlt(f"UPDATE wealth_accounts SET balance = 0.0{where_clause}"), params)
            results["accounts_reset"] = 1

    return results


def reset_all_wealth_database(engine: Engine) -> Dict[str, int]:
    """
    Cancella INCONDIZIONATAMENTE e TOTALMENTE tutti i dati da tutte le tabelle Wealth del database:
    - wealth_cashflow
    - wealth_networth_snapshots
    - wealth_physical_assets
    - wealth_pension_plans
    - wealth_accounts
    """
    init_wealth_db(engine)
    results = {}
    with engine.begin() as conn:
        for tbl in ["wealth_cashflow", "wealth_networth_snapshots", "wealth_physical_assets", "wealth_pension_plans", "wealth_accounts"]:
            try:
                res = conn.execute(sqlt(f"DELETE FROM {tbl}"))
                results[tbl] = res.rowcount if hasattr(res, "rowcount") else 0
            except Exception:
                results[tbl] = 0
    return results


# ── ACCOUNTS CRUD ───────────────────────────────────────────



def get_wealth_accounts(
    engine: Engine,
    portfolio_id: Optional[int] = None,
    is_active_only: bool = False
) -> pd.DataFrame:
    """Recupera tutti i conti censiti per il portafoglio/profilo specificato."""
    init_wealth_db(engine)
    query = "SELECT * FROM wealth_accounts WHERE 1=1"
    params = {}
    if portfolio_id is not None:
        query += " AND (portfolio_id = :pid OR portfolio_id IS NULL OR portfolio_id = 1)"
        params["pid"] = portfolio_id
    if is_active_only:
        query += " AND is_active = 1"
    query += " ORDER BY is_active DESC, name ASC"

    with engine.connect() as conn:
        return pd.read_sql(sqlt(query), conn, params=params)


def save_wealth_account(engine: Engine, account: Dict[str, Any]) -> int:
    """Crea o aggiorna un conto."""
    init_wealth_db(engine)
    acc_id = account.get("account_id")
    p_id = account.get("portfolio_id", 1) or 1
    params = {
        "portfolio_id": p_id,
        "name": account["name"],
        "account_type": account.get("account_type", "checking"),
        "institution": account.get("institution", "Banca"),
        "currency": account.get("currency", "EUR"),
        "balance": float(account.get("balance", 0.0)),
        "is_active": 1 if account.get("is_active", True) else 0,
        "iban": account.get("iban"),
        "notes": account.get("notes"),
    }
    with engine.begin() as conn:
        if not acc_id:
            existing_id = conn.execute(
                sqlt("SELECT account_id FROM wealth_accounts WHERE LOWER(TRIM(name)) = LOWER(TRIM(:name))"),
                {"name": account["name"]}
            ).scalar()
            if existing_id:
                acc_id = existing_id

        if acc_id:
            params["aid"] = acc_id
            conn.execute(sqlt("""
                UPDATE wealth_accounts 
                SET portfolio_id=:portfolio_id, name=:name, account_type=:account_type, institution=:institution,
                    currency=:currency, balance=:balance, is_active=:is_active,
                    iban=:iban, notes=:notes
                WHERE account_id = :aid
            """), params)
            return acc_id
        else:
            conn.execute(sqlt("""
                INSERT INTO wealth_accounts (portfolio_id, name, account_type, institution, currency, balance, is_active, iban, notes)
                VALUES (:portfolio_id, :name, :account_type, :institution, :currency, :balance, :is_active, :iban, :notes)
            """), params)
            return _get_last_insert_id(conn, engine)


def delete_wealth_account(engine: Engine, account_id: int) -> bool:
    """Elimina un conto dall'anagrafica e riassegna eventuali movimenti al primo conto disponibile."""
    init_wealth_db(engine)
    with engine.begin() as conn:
        fallback_id = conn.execute(sqlt("""
            SELECT account_id FROM wealth_accounts 
            WHERE account_id != :aid 
            ORDER BY account_id ASC LIMIT 1
        """), {"aid": account_id}).scalar()
        
        if fallback_id:
            conn.execute(sqlt("UPDATE wealth_cashflow SET account_id = :fid WHERE account_id = :aid"), {"fid": fallback_id, "aid": account_id})
        else:
            conn.execute(sqlt("DELETE FROM wealth_cashflow WHERE account_id = :aid"), {"aid": account_id})
            
        conn.execute(sqlt("DELETE FROM wealth_accounts WHERE account_id = :aid"), {"aid": account_id})
    return True


def deduplicate_wealth_accounts(engine: Engine, portfolio_id: Optional[int] = None) -> int:
    """Raggruppa e fonde i conti con lo stesso nome, eliminando duplicati e riallineando le transazioni."""
    init_wealth_db(engine)
    removed_count = 0
    with engine.begin() as conn:
        q = "SELECT account_id, name, balance FROM wealth_accounts"
        params = {}
        if portfolio_id is not None:
            q += " WHERE portfolio_id = :pid"
            params["pid"] = portfolio_id
        q += " ORDER BY account_id ASC"

        accounts = conn.execute(sqlt(q), params).fetchall()
        canonical_map = {}
        id_to_canonical = {}

        for aid, name, bal in accounts:
            norm = name.strip().lower()
            if norm not in canonical_map:
                canonical_map[norm] = aid
                id_to_canonical[aid] = aid
            else:
                id_to_canonical[aid] = canonical_map[norm]
                removed_count += 1

        for old_id, can_id in id_to_canonical.items():
            if old_id != can_id:
                conn.execute(sqlt("UPDATE wealth_cashflow SET account_id = :can WHERE account_id = :old"), {"can": can_id, "old": old_id})
                conn.execute(sqlt("DELETE FROM wealth_accounts WHERE account_id = :old"), {"old": old_id})

    return removed_count


# ── CASH FLOW CRUD ──────────────────────────────────────────

def get_cashflow_records(
    engine: Engine,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    portfolio_id: Optional[int] = None,
    account_id: Optional[int] = None
) -> pd.DataFrame:
    """Recupera le transazioni di cassa unite alle categorie e ai conti."""
    init_wealth_db(engine)
    query = """
        SELECT c.tx_id, c.tx_date, c.amount, c.currency, c.direction, 
               c.merchant, c.notes, c.payment_method, c.is_recurring, c.tags,
               c.portfolio_id, a.name as account_name, a.institution,
               cat.name as category_name, cat.flow_type, cat.nature, cat.icon, cat.color
        FROM wealth_cashflow c
        JOIN wealth_accounts a ON c.account_id = a.account_id
        JOIN wealth_categories cat ON c.category_id = cat.category_id
        WHERE 1=1
    """
    params = {}
    if portfolio_id is not None:
        query += " AND (c.portfolio_id = :pid OR c.portfolio_id IS NULL OR c.portfolio_id = 1)"
        params["pid"] = portfolio_id
    if account_id is not None:
        query += " AND c.account_id = :aid"
        params["aid"] = account_id
    if start_date:
        query += " AND c.tx_date >= :sdate"
        params["sdate"] = start_date
    if end_date:
        query += " AND c.tx_date <= :edate"
        params["edate"] = end_date
    query += " ORDER BY c.tx_date DESC, c.tx_id DESC"

    with engine.connect() as conn:
        return pd.read_sql(sqlt(query), conn, params=params)


def insert_cashflow_tx(engine: Engine, tx_data: Dict[str, Any]) -> int:
    """Inserisce una nuova transazione nel libro mastro e aggiorna il saldo del conto."""
    init_wealth_db(engine)
    params = {
        "portfolio_id": int(tx_data.get("portfolio_id", 1) or 1),
        "account_id": int(tx_data["account_id"]),
        "category_id": int(tx_data["category_id"]),
        "tx_date": str(tx_data["tx_date"]),
        "amount": float(tx_data["amount"]),
        "currency": tx_data.get("currency", "EUR"),
        "direction": tx_data.get("direction", "outflow"),
        "merchant": tx_data.get("merchant"),
        "notes": tx_data.get("notes"),
        "is_recurring": 1 if tx_data.get("is_recurring") else 0,
        "payment_method": tx_data.get("payment_method", "Carta / Bonifico"),
        "tags": tx_data.get("tags"),
    }
    with engine.begin() as conn:
        conn.execute(sqlt("""
            INSERT INTO wealth_cashflow (portfolio_id, account_id, category_id, tx_date, amount, currency, direction, merchant, notes, is_recurring, payment_method, tags)
            VALUES (:portfolio_id, :account_id, :category_id, :tx_date, :amount, :currency, :direction, :merchant, :notes, :is_recurring, :payment_method, :tags)
        """), params)
        tx_id = _get_last_insert_id(conn, engine)

        # Aggiorna il saldo del conto
        delta = params["amount"] if params["direction"] == "inflow" else -params["amount"]
        conn.execute(sqlt("UPDATE wealth_accounts SET balance = balance + :delta WHERE account_id = :aid"), {"delta": delta, "aid": params["account_id"]})
        return tx_id


# ── PHYSICAL ASSETS & WATCHES CRUD ─────────────────────────

def get_physical_assets(
    engine: Engine,
    category: Optional[str] = None,
    portfolio_id: Optional[int] = None
) -> pd.DataFrame:
    """Recupera tutti gli asset fisici (orologi, immobili, metalli, collezioni)."""
    init_wealth_db(engine)
    query = "SELECT * FROM wealth_physical_assets WHERE 1=1"
    params = {}
    if portfolio_id is not None:
        query += " AND (portfolio_id = :pid OR portfolio_id IS NULL OR portfolio_id = 1)"
        params["pid"] = portfolio_id
    if category:
        query += " AND asset_category = :cat"
        params["cat"] = category
    query += " ORDER BY current_market_value DESC"

    with engine.connect() as conn:
        df = pd.read_sql(sqlt(query), conn, params=params)
        if not df.empty:
            df["unrealized_pnl"] = df["current_market_value"] - df["purchase_price"]
            df["unrealized_pnl_pct"] = (df["unrealized_pnl"] / df["purchase_price"].replace(0, pd.NA)) * 100.0
        return df


def save_physical_asset(engine: Engine, asset: Dict[str, Any]) -> int:
    """Crea o aggiorna un asset fisico (es. Orologio di Lusso o Immobile)."""
    init_wealth_db(engine)
    aid = asset.get("asset_id")
    params = {
        "portfolio_id": int(asset.get("portfolio_id", 1) or 1),
        "name": asset["name"],
        "asset_category": asset.get("asset_category", "luxury_watches"),
        "brand_or_location": asset.get("brand_or_location"),
        "model_or_specs": asset.get("model_or_specs"),
        "reference_number": asset.get("reference_number"),
        "acquisition_date": str(asset["acquisition_date"]) if asset.get("acquisition_date") else None,
        "purchase_price": float(asset.get("purchase_price", 0.0)),
        "current_market_value": float(asset.get("current_market_value", 0.0)),
        "valuation_date": str(asset["valuation_date"]) if asset.get("valuation_date") else str(date.today()),
        "valuation_source": asset.get("valuation_source", "Stima di Mercato"),
        "condition_grade": asset.get("condition_grade", "Eccellente / Full Set"),
        "currency": asset.get("currency", "EUR"),
        "notes": asset.get("notes"),
    }
    with engine.begin() as conn:
        if aid:
            params["aid"] = aid
            conn.execute(sqlt("""
                UPDATE wealth_physical_assets
                SET portfolio_id=:portfolio_id, name=:name, asset_category=:asset_category, brand_or_location=:brand_or_location,
                    model_or_specs=:model_or_specs, reference_number=:reference_number,
                    acquisition_date=:acquisition_date, purchase_price=:purchase_price,
                    current_market_value=:current_market_value, valuation_date=:valuation_date,
                    valuation_source=:valuation_source, condition_grade=:condition_grade,
                    currency=:currency, notes=:notes
                WHERE asset_id = :aid
            """), params)
            return aid
        else:
            conn.execute(sqlt("""
                INSERT INTO wealth_physical_assets (portfolio_id, name, asset_category, brand_or_location, model_or_specs, reference_number, acquisition_date, purchase_price, current_market_value, valuation_date, valuation_source, condition_grade, currency, notes)
                VALUES (:portfolio_id, :name, :asset_category, :brand_or_location, :model_or_specs, :reference_number, :acquisition_date, :purchase_price, :current_market_value, :valuation_date, :valuation_source, :condition_grade, :currency, :notes)
            """), params)
            return _get_last_insert_id(conn, engine)


# ── PENSION PLANS CRUD ─────────────────────────────────────

def get_pension_plans(engine: Engine, portfolio_id: Optional[int] = None) -> pd.DataFrame:
    """Recupera tutti i fondi pensione e piani di previdenza complementare."""
    init_wealth_db(engine)
    query = "SELECT * FROM wealth_pension_plans WHERE 1=1"
    params = {}
    if portfolio_id is not None:
        query += " AND (portfolio_id = :pid OR portfolio_id IS NULL OR portfolio_id = 1)"
        params["pid"] = portfolio_id
    query += " ORDER BY accumulated_value DESC"

    with engine.connect() as conn:
        return pd.read_sql(sqlt(query), conn, params=params)


def save_pension_plan(engine: Engine, plan: Dict[str, Any]) -> int:
    """Crea o aggiorna un fondo pensione."""
    init_wealth_db(engine)
    pid = plan.get("plan_id")
    params = {
        "portfolio_id": int(plan.get("portfolio_id", 1) or 1),
        "plan_name": plan["plan_name"],
        "provider": plan.get("provider", "Fondo Pensione"),
        "plan_type": plan.get("plan_type", "fondo_pensione_aperto"),
        "accumulated_value": float(plan.get("accumulated_value", 0.0)),
        "monthly_employee_contrib": float(plan.get("monthly_employee_contrib", 0.0)),
        "monthly_employer_contrib": float(plan.get("monthly_employer_contrib", 0.0)),
        "tax_deductible_annual": float(plan.get("tax_deductible_annual", 0.0)),
        "expected_retirement_age": int(plan.get("expected_retirement_age", 67)),
        "currency": plan.get("currency", "EUR"),
        "investment_line": plan.get("investment_line", "Azionario / Crescita"),
        "notes": plan.get("notes"),
    }
    with engine.begin() as conn:
        if pid:
            params["pid"] = pid
            conn.execute(sqlt("""
                UPDATE wealth_pension_plans
                SET portfolio_id=:portfolio_id, plan_name=:plan_name, provider=:provider, plan_type=:plan_type,
                    accumulated_value=:accumulated_value, monthly_employee_contrib=:monthly_employee_contrib,
                    monthly_employer_contrib=:monthly_employer_contrib, tax_deductible_annual=:tax_deductible_annual,
                    expected_retirement_age=:expected_retirement_age, currency=:currency,
                    investment_line=:investment_line, notes=:notes
                WHERE plan_id = :pid
            """), params)
            return pid
        else:
            conn.execute(sqlt("""
                INSERT INTO wealth_pension_plans (portfolio_id, plan_name, provider, plan_type, accumulated_value, monthly_employee_contrib, monthly_employer_contrib, tax_deductible_annual, expected_retirement_age, currency, investment_line, notes)
                VALUES (:portfolio_id, :plan_name, :provider, :plan_type, :accumulated_value, :monthly_employee_contrib, :monthly_employer_contrib, :tax_deductible_annual, :expected_retirement_age, :currency, :investment_line, :notes)
            """), params)
            return _get_last_insert_id(conn, engine)


# ── NET WORTH SNAPSHOTS CRUD & RECALL ──────────────────────

def save_wealth_snapshot_to_db(
    engine: Engine,
    snapshot_name: Optional[str] = None,
    notes: Optional[str] = None,
    snapshot_date_val: Optional[date] = None,
    portfolio_id: Optional[int] = None,
    risk_portfolio_ids: Optional[List[int]] = None,
    run_id: Optional[str] = None,
    run_name: Optional[str] = None
) -> int:
    """
    Calcola e salva una fotografia completa (snapshot) del patrimonio netto consolidato nel database.
    Ogni esecuzione o ingestione crea un nuovo snapshot storico indicizzato con run_id.
    """
    from core.wealth.wealth_engine import compute_consolidated_net_worth, compute_cashflow_analytics

    init_wealth_db(engine)
    p_id = portfolio_id or 1
    nw = compute_consolidated_net_worth(engine, portfolio_id=p_id, risk_portfolio_ids=risk_portfolio_ids)
    df_cf = get_cashflow_records(engine, portfolio_id=p_id)
    cf_metrics = compute_cashflow_analytics(df_cf)

    df_accs = get_wealth_accounts(engine, portfolio_id=p_id)
    df_phys = get_physical_assets(engine, portfolio_id=p_id)
    df_pens = get_pension_plans(engine, portfolio_id=p_id)
    _, df_linked_risk = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=p_id)

    s_date = snapshot_date_val or date.today()
    s_name = run_name or snapshot_name or f"Snapshot Patrimoniale {s_date.strftime('%d/%m/%Y %H:%M')}"
    s_run_id = run_id or f"RUN-WLT-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


    details_payload = {
        "snapshot_date": str(s_date),
        "snapshot_name": s_name,
        "run_id": s_run_id,
        "portfolio_id": p_id,
        "summary": {
            "total_net_worth": nw.total_net_worth,
            "liquid_cash": nw.liquid_cash,
            "financial_investments": nw.financial_investments,
            "physical_assets": nw.physical_assets,
            "luxury_watches_total": nw.luxury_watches_total,
            "real_estate_total": nw.real_estate_total,
            "precious_metals_total": nw.precious_metals_total,
            "pension_total": nw.pension_total,
            "total_liabilities": nw.total_liabilities,
            "savings_rate_pct": nw.savings_rate_pct,
            "runway_months": nw.runway_months,
            "wealth_health_score": nw.wealth_health_score
        },
        "linked_risk_portfolios": df_linked_risk.to_dict(orient="records") if not df_linked_risk.empty else [],
        "cashflow_analytics": cf_metrics,
        "accounts": df_accs.to_dict(orient="records") if not df_accs.empty else [],
        "physical_assets": df_phys.to_dict(orient="records") if not df_phys.empty else [],
        "pension_plans": df_pens.to_dict(orient="records") if not df_pens.empty else []
    }

    details_str = json.dumps(details_payload, default=str)

    params = {
        "portfolio_id": p_id,
        "run_id": s_run_id,
        "s_date": str(s_date),
        "s_name": s_name,
        "tot_nw": float(nw.total_net_worth),
        "liq": float(nw.liquid_cash),
        "fin": float(nw.financial_investments),
        "phys": float(nw.physical_assets),
        "watches": float(nw.luxury_watches_total),
        "re": float(nw.real_estate_total),
        "pens": float(nw.pension_total),
        "liab": float(nw.total_liabilities),
        "inc_avg": float(cf_metrics.get("avg_monthly_income", 0.0)),
        "exp_avg": float(cf_metrics.get("avg_monthly_expense", 0.0)),
        "sav_rate": float(nw.savings_rate_pct),
        "runway": float(nw.runway_months),
        "score": float(nw.wealth_health_score),
        "details": details_str,
        "notes": notes
    }

    with engine.begin() as conn:
        conn.execute(sqlt("""
            INSERT INTO wealth_networth_snapshots (
                portfolio_id, run_id, snapshot_date, snapshot_name, total_net_worth, liquid_assets,
                financial_investments, physical_assets_total, watches_total,
                real_estate_total, pension_total, total_liabilities,
                monthly_income_avg, monthly_expense_avg, savings_rate_pct,
                emergency_runway_months, wealth_health_score, details_json, notes
            ) VALUES (
                :portfolio_id, :run_id, :s_date, :s_name, :tot_nw, :liq,
                :fin, :phys, :watches,
                :re, :pens, :liab,
                :inc_avg, :exp_avg, :sav_rate,
                :runway, :score, :details, :notes
            )
        """), params)
        return _get_last_insert_id(conn, engine)


def get_wealth_snapshots_history(engine: Engine, portfolio_id: Optional[int] = None) -> pd.DataFrame:
    """Recupera l'elenco cronologico di tutti gli snapshot patrimoniali salvati con nome profilo."""
    init_wealth_db(engine)
    query = """
        SELECT s.*, p.name as portfolio_name
        FROM wealth_networth_snapshots s
        LEFT JOIN portfolios p ON s.portfolio_id = p.portfolio_id
        WHERE 1=1
    """
    params = {}
    if portfolio_id is not None:
        query += " AND (s.portfolio_id = :pid OR s.portfolio_id IS NULL OR s.portfolio_id = 1)"
        params["pid"] = portfolio_id
    query += " ORDER BY s.snapshot_date DESC, s.snapshot_id DESC"

    with engine.connect() as conn:
        return pd.read_sql(sqlt(query), conn, params=params)



def delete_wealth_snapshot(engine: Engine, snapshot_id: int) -> bool:
    """Elimina uno snapshot patrimoniale dal database."""
    init_wealth_db(engine)
    with engine.begin() as conn:
        res = conn.execute(
            sqlt("DELETE FROM wealth_networth_snapshots WHERE snapshot_id = :sid"),
            {"sid": snapshot_id}
        )
        return (res.rowcount > 0)


def load_wealth_snapshot_details(engine: Engine, snapshot_id: int) -> Optional[Dict[str, Any]]:
    """Carica il payload completo di dettagli di uno snapshot patrimoniale salvato."""
    init_wealth_db(engine)
    with engine.connect() as conn:
        row = conn.execute(
            sqlt("SELECT * FROM wealth_networth_snapshots WHERE snapshot_id = :sid"),
            {"sid": snapshot_id}
        ).mappings().fetchone()
        if not row:
            return None
        res_dict = dict(row)
        if res_dict.get("details_json"):
            try:
                res_dict["details"] = json.loads(res_dict["details_json"])
            except Exception:
                res_dict["details"] = {}
        else:
            res_dict["details"] = {}
        return res_dict


# ============================================================
# ── GESTIONE SPESE FISSE & SUBSCRIPTIONS DA CONFIG_FIXEDEXPENSES
# ============================================================

def save_wealth_fixed_expense(engine: Engine, data: Dict[str, Any]) -> int:
    """Salva o aggiorna una spesa fissa/abbonamento nel database."""
    init_wealth_db(engine)
    is_sqlite = (getattr(engine, "dialect", None) is not None and engine.dialect.name == "sqlite")
    
    with engine.begin() as conn:
        fixed_id = data.get("fixed_id")
        params = {
            "pid": int(data.get("portfolio_id", 1)),
            "cat": str(data.get("category", "Subscriptions")).strip(),
            "note": str(data.get("note", "")).strip(),
            "amt": float(data.get("amount", 0.0)),
            "p_day": int(data["payment_day"]) if data.get("payment_day") is not None and str(data["payment_day"]).isdigit() else None,
            "s_date": str(data["start_date"])[:10] if data.get("start_date") else None,
            "e_date": str(data["end_date"])[:10] if data.get("end_date") else None,
            "is_split": 1 if data.get("is_split") else 0,
            "s_det": str(data.get("split_details", "")) if data.get("split_details") else None,
            "cadence": str(data.get("cadence", "Mensile")),
            "active": 1 if data.get("is_active", True) else 0
        }

        if fixed_id:
            params["fid"] = int(fixed_id)
            conn.execute(sqlt("""
                UPDATE wealth_fixed_expenses
                SET portfolio_id = :pid, category = :cat, note = :note, amount = :amt,
                    payment_day = :p_day, start_date = :s_date, end_date = :e_date,
                    is_split = :is_split, split_details = :s_det, cadence = :cadence, is_active = :active
                WHERE fixed_id = :fid
            """), params)
            return fixed_id
        else:
            q_ins = """
                INSERT INTO wealth_fixed_expenses 
                (portfolio_id, category, note, amount, payment_day, start_date, end_date, is_split, split_details, cadence, is_active)
                VALUES (:pid, :cat, :note, :amt, :p_day, :s_date, :e_date, :is_split, :s_det, :cadence, :active)
            """
            res = conn.execute(sqlt(q_ins), params)
            if is_sqlite:
                return conn.execute(sqlt("SELECT last_insert_rowid()")).scalar() or 0
            else:
                return res.lastrowid or 0


def get_wealth_fixed_expenses(engine: Engine, portfolio_id: Optional[int] = None) -> pd.DataFrame:
    """Recupera l'elenco delle spese fisse/abbonamenti per il profilo patrimoniale specificato."""
    init_wealth_db(engine)
    query = "SELECT * FROM wealth_fixed_expenses WHERE is_active = 1"
    params = {}
    if portfolio_id is not None:
        query += " AND (portfolio_id = :pid OR portfolio_id IS NULL OR portfolio_id = 1)"
        params["pid"] = portfolio_id
    query += " ORDER BY amount DESC, fixed_id ASC"

    with engine.connect() as conn:
        return pd.read_sql(sqlt(query), conn, params=params)


def clear_wealth_fixed_expenses(engine: Engine, portfolio_id: Optional[int] = None) -> int:
    """Rimuove tutte le spese fisse dal database per il profilo patrimoniale."""
    init_wealth_db(engine)
    query = "DELETE FROM wealth_fixed_expenses"
    params = {}
    if portfolio_id is not None:
        query += " WHERE portfolio_id = :pid"
        params["pid"] = portfolio_id

    with engine.begin() as conn:
        res = conn.execute(sqlt(query), params)
        return res.rowcount or 0



