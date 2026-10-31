-- =============================================================================
-- ARGUS INSTITUTIONAL PLATFORM — CANONICAL LOCAL SQLITE SCHEMA
-- Canonical File: sql/02_sqlite_local_schema.sql
-- Complete DDL for local zero-latency embedded analytics database (argus_local.db).
-- Contains all 21 tables: Portfolios, Assets, Transactions, Market Prices,
-- Portfolio Snapshots, Wealth Management, Cashflow, Fixed Expenses, Goals,
-- Real Estate, Illiquid Assets, Pensions, Tax 730/RW, and System Health.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- 1. SYSTEM HEALTH & MIGRATIONS
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    subsystem VARCHAR(50) NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS tombstone_deletions (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    PRIMARY KEY (entity_type, entity_id)
);

-- 2. CORE RISK & PORTFOLIO TABLES
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    owner VARCHAR(100) NOT NULL DEFAULT 'anonymous',
    base_currency CHAR(3) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200),
    asset_class VARCHAR(50) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    gics_sector VARCHAR(100),
    country VARCHAR(50),
    trailing_pe REAL,
    forward_pe REAL,
    price_to_book REAL,
    dividend_yield REAL,
    roe REAL,
    target_mean_price REAL,
    peg_ratio REAL,
    industry VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    tx_date DATE NOT NULL,
    tx_type VARCHAR(10) NOT NULL,
    shares REAL NOT NULL,
    price REAL NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    exchange_rate REAL DEFAULT 1.0,
    fee REAL DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS market_prices (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    price_date DATE NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL NOT NULL,
    adj_close REAL,
    volume REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    UNIQUE(asset_id, price_date)
);

CREATE TABLE IF NOT EXISTS asset_mapping (
    alias VARCHAR(50) PRIMARY KEY,
    canonical_ticker VARCHAR(20) NOT NULL,
    source VARCHAR(50) DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    total_value REAL NOT NULL,
    total_cost REAL,
    cash_balance REAL DEFAULT 0.0,
    currency CHAR(3) NOT NULL DEFAULT 'EUR',
    cagr REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL,
    var_historical_95 REAL,
    cvar_historical_95 REAL,
    volatility_annual REAL,
    beta REAL,
    calmar_ratio REAL,
    omega_ratio REAL,
    benchmark_ticker VARCHAR(20) DEFAULT 'SPY',
    snapshot_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS snapshot_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    shares REAL NOT NULL,
    average_cost REAL,
    current_price REAL NOT NULL,
    current_value REAL NOT NULL,
    unrealized_pnl REAL,
    unrealized_pnl_pct REAL,
    weight_pct REAL,
    asset_class VARCHAR(50),
    sector VARCHAR(100),
    currency CHAR(3) DEFAULT 'EUR',
    user_id TEXT,
    FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
);

-- 3. WEALTH MANAGEMENT TABLES
CREATE TABLE IF NOT EXISTS wealth_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    profile_type VARCHAR(50) NOT NULL DEFAULT 'individual',
    tax_regime VARCHAR(50) NOT NULL DEFAULT 'dichiarativo',
    risk_tolerance VARCHAR(50) NOT NULL DEFAULT 'moderate',
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    target_cash_reserve REAL DEFAULT 10000.0,
    target_equity_pct REAL DEFAULT 60.0,
    target_bond_pct REAL DEFAULT 30.0,
    target_crypto_pct REAL DEFAULT 5.0,
    target_real_estate_pct REAL DEFAULT 0.0,
    target_commodities_pct REAL DEFAULT 5.0,
    target_other_pct REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    institution VARCHAR(100),
    iban_or_id VARCHAR(50),
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    balance REAL NOT NULL DEFAULT 0.0,
    interest_rate REAL DEFAULT 0.0,
    credit_limit REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    category_type VARCHAR(50) NOT NULL,
    macro_group VARCHAR(50) NOT NULL,
    parent_category_id INTEGER,
    icon VARCHAR(10),
    color VARCHAR(20),
    is_system INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_cashflow (
    cashflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    tx_date DATE NOT NULL,
    amount REAL NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    flow_type VARCHAR(20) NOT NULL,
    category_id INTEGER,
    description TEXT,
    is_recurring INTEGER DEFAULT 0,
    recurrence_period VARCHAR(20),
    tx_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (account_id) REFERENCES wealth_accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES wealth_categories(category_id)
);

CREATE TABLE IF NOT EXISTS wealth_physical_assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    asset_category VARCHAR(50) NOT NULL,
    purchase_date DATE,
    purchase_price REAL NOT NULL,
    current_estimated_value REAL NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    appraisal_date DATE,
    address_or_location TEXT,
    ownership_pct REAL DEFAULT 100.0,
    is_income_generating INTEGER DEFAULT 0,
    annual_rental_income REAL DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_pension_plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    plan_type VARCHAR(50) NOT NULL,
    provider VARCHAR(100),
    policy_number VARCHAR(50),
    start_date DATE,
    current_value REAL NOT NULL DEFAULT 0.0,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    monthly_contribution REAL DEFAULT 0.0,
    employer_contribution REAL DEFAULT 0.0,
    employer_match REAL DEFAULT 0.0,
    expected_return_pct REAL DEFAULT 3.0,
    retirement_year INTEGER,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    snapshot_date DATE NOT NULL,
    total_liquidity REAL NOT NULL DEFAULT 0.0,
    total_investments REAL NOT NULL DEFAULT 0.0,
    total_real_estate REAL NOT NULL DEFAULT 0.0,
    total_pension REAL NOT NULL DEFAULT 0.0,
    total_other_assets REAL NOT NULL DEFAULT 0.0,
    total_gross_assets REAL NOT NULL DEFAULT 0.0,
    total_liabilities REAL NOT NULL DEFAULT 0.0,
    net_worth REAL NOT NULL DEFAULT 0.0,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_fixed_expenses (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    category_id INTEGER,
    amount REAL NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    frequency VARCHAR(20) NOT NULL DEFAULT 'monthly',
    due_day INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    auto_pay INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (category_id) REFERENCES wealth_categories(category_id)
);

CREATE TABLE IF NOT EXISTS wealth_goals (
    goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(150) NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0.0,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    target_date DATE NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    is_active INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    wealth_account_id INTEGER NOT NULL,
    risk_portfolio_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (wealth_account_id) REFERENCES wealth_accounts(account_id) ON DELETE CASCADE,
    FOREIGN KEY (risk_portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    UNIQUE(wealth_account_id, risk_portfolio_id)
);

-- 4. FISCAL & TAX TABLES (ITALIAN 730 / REDDITI PF & QUADRO RW)
CREATE TABLE IF NOT EXISTS tax_declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id VARCHAR(50) NOT NULL DEFAULT 'default',
    tax_year INTEGER NOT NULL,
    country_code VARCHAR(3) NOT NULL DEFAULT 'ITA',
    regime VARCHAR(30) NOT NULL DEFAULT 'dichiarativo',
    total_gross_income REAL DEFAULT 0.0,
    total_capital_gains REAL DEFAULT 0.0,
    total_dividends_interest REAL DEFAULT 0.0,
    total_crypto_gains REAL DEFAULT 0.0,
    total_foreign_assets_val REAL DEFAULT 0.0,
    substitute_tax_due REAL DEFAULT 0.0,
    ivie_tax_due REAL DEFAULT 0.0,
    ivafe_tax_due REAL DEFAULT 0.0,
    crypto_tax_due REAL DEFAULT 0.0,
    stamp_duty_due REAL DEFAULT 0.0,
    total_tax_due REAL DEFAULT 0.0,
    tax_paid REAL DEFAULT 0.0,
    tax_credit_foreign REAL DEFAULT 0.0,
    net_tax_payable REAL DEFAULT 0.0,
    calculation_engine_version VARCHAR(30) DEFAULT '10.0.0',
    is_officially_filed INTEGER DEFAULT 0,
    filing_date DATE,
    protocol_number VARCHAR(100),
    summary_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    UNIQUE(profile_id, tax_year)
);

CREATE TABLE IF NOT EXISTS tax_loss_carryforward (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id VARCHAR(50) NOT NULL DEFAULT 'default',
    asset_class VARCHAR(50) NOT NULL,
    loss_year INTEGER NOT NULL,
    expiry_year INTEGER NOT NULL,
    initial_amount REAL NOT NULL,
    used_amount REAL NOT NULL DEFAULT 0.0,
    remaining_amount REAL NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

CREATE TABLE IF NOT EXISTS tax_verification_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL DEFAULT 'default',
    tax_year INTEGER NOT NULL,
    doc_type TEXT NOT NULL,
    issuer_name TEXT,
    protocol_or_code TEXT,
    gross_amount REAL DEFAULT 0.00,
    net_taxable_amount REAL DEFAULT 0.00,
    tax_withheld_or_due REAL DEFAULT 0.00,
    tax_paid REAL DEFAULT 0.00,
    penalty_amount REAL DEFAULT 0.00,
    interest_amount REAL DEFAULT 0.00,
    total_due REAL DEFAULT 0.00,
    secondary_amount REAL DEFAULT 0.00,
    asset_monitoring_val REAL DEFAULT 0.00,
    metadata_json TEXT,
    notes TEXT,
    source_filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    workspace_id TEXT DEFAULT 'default'
);

-- 5. PERFORMANCE B-TREE INDEXES
CREATE INDEX IF NOT EXISTS idx_tx_portfolio_date ON transactions(portfolio_id, tx_date);
CREATE INDEX IF NOT EXISTS idx_tx_asset ON transactions(asset_id);
CREATE INDEX IF NOT EXISTS idx_price_lookup ON market_prices(asset_id, price_date);
CREATE INDEX IF NOT EXISTS idx_cf_acct_date ON wealth_cashflow(account_id, tx_date DESC);
CREATE INDEX IF NOT EXISTS idx_cf_cat_date ON wealth_cashflow(category_id, tx_date DESC);
CREATE INDEX IF NOT EXISTS idx_cf_port_date ON wealth_cashflow(portfolio_id, tx_date DESC);
CREATE INDEX IF NOT EXISTS idx_cf_port_cat ON wealth_cashflow(portfolio_id, category_id);
CREATE INDEX IF NOT EXISTS idx_cf_tx_hash ON wealth_cashflow(account_id, tx_hash);
CREATE INDEX IF NOT EXISTS idx_snap_port_date ON wealth_networth_snapshots(portfolio_id, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_phys_port ON wealth_physical_assets(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_pens_port ON wealth_pension_plans(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_acct_port ON wealth_accounts(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_verif_profile_year ON tax_verification_documents(profile_id, tax_year);
CREATE INDEX IF NOT EXISTS idx_verif_doc_type ON tax_verification_documents(doc_type);

-- 6. DEFAULT CATEGORY & PROFILE SEED DATA
INSERT OR IGNORE INTO wealth_profiles (profile_id, name, profile_type, tax_regime, risk_tolerance, currency, is_active)
VALUES (1, 'Personale', 'individual', 'dichiarativo', 'moderate', 'EUR', 1);

INSERT OR IGNORE INTO wealth_categories (name, category_type, macro_group, icon, color, is_system) VALUES
('Stipendio & Bonus', 'income', 'needs', '💼', '#10b981', 1),
('Rendite da Investimenti', 'income', 'savings', '📈', '#3b82f6', 1),
('Dividendi & Cedole', 'income', 'savings', '💰', '#6366f1', 1),
('Rimborsi & Altre Entrate', 'income', 'needs', '🔄', '#8b5cf6', 1),
('Casa & Utenze', 'expense', 'needs', '🏠', '#f59e0b', 1),
('Alimentari & Spesa', 'expense', 'needs', '🛒', '#ec4899', 1),
('Trasporti & Auto', 'expense', 'needs', '🚗', '#06b6d4', 1),
('Salute & Cura Personale', 'expense', 'needs', '🏥', '#14b8a6', 1),
('Svago & Ristoranti', 'expense', 'wants', '🍕', '#f97316', 1),
('Viaggi & Vacanze', 'expense', 'wants', '✈️', '#e11d48', 1),
('Shopping & Tecnologia', 'expense', 'wants', '🛍️', '#84cc16', 1),
('Imposte & Tasse', 'expense', 'needs', '📑', '#ef4444', 1),
('Investimenti PAC', 'transfer', 'savings', '🌱', '#10b981', 1),
('Risparmio & Fondo Emergenza', 'transfer', 'savings', '🛡️', '#0ea5e9', 1);
