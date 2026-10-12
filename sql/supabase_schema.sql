-- ============================================================
-- ARGUS INSTITUTIONAL PLATFORM — SUPABASE POSTGRESQL SCHEMA
-- Zero-Cost Cloud Architecture (PostgreSQL 15+ / Supabase)
-- Paste into: Supabase Dashboard -> SQL Editor -> New Query
-- ============================================================

-- 1. CORE RISK & PORTFOLIO TABLES
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner VARCHAR(100) NOT NULL DEFAULT 'user',
    base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200),
    asset_class VARCHAR(50) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    gics_sector VARCHAR(100),
    country VARCHAR(50),
    trailing_pe NUMERIC(10,2),
    forward_pe NUMERIC(10,2),
    price_to_book NUMERIC(10,2),
    dividend_yield NUMERIC(10,4),
    roe NUMERIC(10,4),
    target_mean_price NUMERIC(18,6),
    peg_ratio NUMERIC(10,2),
    industry VARCHAR(100),
    exchange VARCHAR(50),
    recommendation_key VARCHAR(50),
    market_cap BIGINT,
    beta_5y NUMERIC(10,4),
    fifty_two_week_high NUMERIC(18,6),
    fifty_two_week_low NUMERIC(18,6),
    fifty_day_average NUMERIC(18,6),
    two_hundred_day_average NUMERIC(18,6),
    profit_margins NUMERIC(10,4),
    gross_margins NUMERIC(10,4),
    operating_margins NUMERIC(10,4),
    total_revenue BIGINT,
    ebitda BIGINT,
    debt_to_equity NUMERIC(10,4),
    revenue_growth NUMERIC(10,4),
    earnings_growth NUMERIC(10,4)
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    tx_date DATE NOT NULL,
    tx_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(18,6) NOT NULL,
    price NUMERIC(18,6) NOT NULL,
    fees NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    fx_rate_to_eur NUMERIC(12,6) NOT NULL DEFAULT 1.000000,
    notes VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS market_prices (
    price_id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    close NUMERIC(18,6) NOT NULL,
    volume BIGINT,
    source VARCHAR(50) NOT NULL DEFAULT 'yfinance',
    CONSTRAINT uq_asset_date UNIQUE (asset_id, price_date)
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
    calc_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_nav_eur NUMERIC(18,2) NOT NULL,
    var_95_1d_pct NUMERIC(8,4),
    var_99_1d_pct NUMERIC(8,4),
    cvar_95_1d_pct NUMERIC(8,4),
    volatility_ann NUMERIC(8,4),
    sharpe_ratio NUMERIC(8,4),
    sortino_ratio NUMERIC(8,4),
    max_drawdown_pct NUMERIC(8,4),
    hhi_concentration NUMERIC(8,4),
    effective_n NUMERIC(8,2),
    diversification_ratio NUMERIC(8,4)
);

CREATE TABLE IF NOT EXISTS snapshot_positions (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    quantity NUMERIC(18,6) NOT NULL,
    market_val_eur NUMERIC(18,2) NOT NULL,
    weight_pct NUMERIC(8,4) NOT NULL,
    unrealized_pnl NUMERIC(18,2),
    component_var_pct NUMERIC(8,4)
);

-- 2. WEALTH MANAGEMENT & FAMILY OFFICE TABLES
CREATE TABLE IF NOT EXISTS wealth_profiles (
    profile_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    owner VARCHAR(100) NOT NULL DEFAULT 'user',
    base_currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_accounts (
    account_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(120) NOT NULL,
    account_type VARCHAR(50) NOT NULL DEFAULT 'checking',
    institution VARCHAR(120) NOT NULL DEFAULT 'Banca',
    currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    balance DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    is_active INTEGER NOT NULL DEFAULT 1,
    iban VARCHAR(64),
    notes TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    flow_type VARCHAR(20) NOT NULL,
    nature VARCHAR(40) NOT NULL DEFAULT 'essential_need',
    parent_id INTEGER REFERENCES wealth_categories(category_id) ON DELETE SET NULL,
    icon VARCHAR(16) NOT NULL DEFAULT '🏷️',
    color VARCHAR(16) NOT NULL DEFAULT '#6366f1',
    is_system INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wealth_cashflow (
    tx_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    account_id INTEGER NOT NULL REFERENCES wealth_accounts(account_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES wealth_categories(category_id),
    tx_date DATE NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    direction VARCHAR(10) NOT NULL,
    merchant VARCHAR(160),
    notes TEXT,
    is_recurring INTEGER NOT NULL DEFAULT 0,
    payment_method VARCHAR(60) NOT NULL DEFAULT 'Carta / Bonifico',
    tags VARCHAR(250),
    tx_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_physical_assets (
    asset_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(180) NOT NULL,
    asset_category VARCHAR(50) NOT NULL DEFAULT 'luxury_watches',
    brand_or_location VARCHAR(150),
    model_or_specs VARCHAR(200),
    reference_number VARCHAR(100),
    acquisition_date DATE,
    purchase_price DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    current_market_value DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    valuation_date DATE,
    valuation_source VARCHAR(120) DEFAULT 'Stima di Mercato',
    condition_grade VARCHAR(80) DEFAULT 'Eccellente / Full Set',
    currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    notes TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_pension_plans (
    plan_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    plan_name VARCHAR(160) NOT NULL,
    provider VARCHAR(120) NOT NULL,
    plan_type VARCHAR(60) NOT NULL DEFAULT 'fondo_pensione_aperto',
    accumulated_value DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    monthly_employee_contrib DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    monthly_employer_contrib DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    tax_deductible_annual DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    expected_retirement_age INTEGER NOT NULL DEFAULT 67,
    currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    investment_line VARCHAR(120) DEFAULT 'Azionario / Crescita',
    notes TEXT,
    yearly_data_json TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    run_id VARCHAR(64),
    snapshot_date DATE NOT NULL,
    snapshot_name VARCHAR(150) DEFAULT 'Snapshot Patrimoniale',
    total_net_worth DOUBLE PRECISION NOT NULL,
    liquid_assets DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    financial_investments DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    physical_assets_total DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    watches_total DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    real_estate_total DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    pension_total DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    total_liabilities DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    monthly_income_avg DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    monthly_expense_avg DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    savings_rate_pct DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    emergency_runway_months DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    wealth_health_score DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    details_json TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_fixed_expenses (
    fixed_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    category VARCHAR(100) NOT NULL,
    note VARCHAR(255) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payment_day INTEGER,
    start_date DATE,
    end_date DATE,
    is_split INTEGER DEFAULT 0,
    split_details TEXT,
    cadence VARCHAR(50) DEFAULT 'Mensile',
    is_active INTEGER DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_goals (
    goal_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(160) NOT NULL,
    category VARCHAR(60) NOT NULL DEFAULT 'custom',
    target_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    target_date DATE NOT NULL,
    current_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    monthly_contribution DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    priority VARCHAR(30) NOT NULL DEFAULT 'medium',
    risk_tolerance VARCHAR(30) NOT NULL DEFAULT 'moderate',
    inflation_rate DOUBLE PRECISION NOT NULL DEFAULT 0.02,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
    wealth_portfolio_id INTEGER NOT NULL,
    risk_portfolio_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wealth_portfolio_id, risk_portfolio_id)
);

-- 3. TAX ENGINE & FISCAL AUDIT VAULT TABLES
CREATE TABLE IF NOT EXISTS tax_declarations (
    id SERIAL PRIMARY KEY,
    profile_id VARCHAR(100) NOT NULL DEFAULT 'default',
    tax_year INTEGER NOT NULL,
    filing_year INTEGER NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    protocol_id VARCHAR(100),
    gross_income DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    taxable_income DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    net_tax_irpef DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    capital_gains_declared DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    capital_losses_offset DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    substitute_tax_paid DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    ivafe_paid DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    foreign_assets_val DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    notes TEXT,
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tax_profile_year UNIQUE (profile_id, tax_year, model_type)
);

CREATE TABLE IF NOT EXISTS tax_loss_carryforward (
    id SERIAL PRIMARY KEY,
    profile_id VARCHAR(100) NOT NULL DEFAULT 'default',
    generation_year INTEGER NOT NULL,
    expiration_year INTEGER NOT NULL,
    initial_loss_amount DOUBLE PRECISION NOT NULL,
    offset_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    remaining_amount DOUBLE PRECISION NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    is_officially_filed INTEGER NOT NULL DEFAULT 1,
    broker_source VARCHAR(100) DEFAULT 'DEGIRO',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tax_verification_documents (
    id SERIAL PRIMARY KEY,
    profile_id VARCHAR(100) NOT NULL DEFAULT 'default',
    tax_year INTEGER NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    issuer_name VARCHAR(200),
    protocol_or_code VARCHAR(150),
    gross_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    net_taxable_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    tax_withheld_or_due DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    tax_paid DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    penalty_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    interest_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    total_due DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    secondary_amount DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    asset_monitoring_val DOUBLE PRECISION NOT NULL DEFAULT 0.00,
    metadata_json TEXT,
    notes TEXT,
    source_filename VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. CLOUD HEARTBEAT TABLE (ANTI-PAUSE KEEP-ALIVE FOR SUPABASE FREE TIER)
CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
    id SERIAL PRIMARY KEY,
    ping_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(80) NOT NULL DEFAULT 'github_actions_keepalive',
    status VARCHAR(40) NOT NULL DEFAULT 'OK',
    details TEXT
);

-- 5. HIGH-PERFORMANCE B-TREE INDEXES
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

-- 6. SUPABASE STORAGE PRIVATE BUCKET FOR FISCAL PDF VAULT
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('tax-documents', 'tax-documents', false)
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;

-- 7. OPTIONAL ROW-LEVEL SECURITY (RLS) HARDENING FOR SUPABASE DATA API
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_cashflow ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_physical_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_pension_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_networth_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_fixed_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE wealth_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_declarations ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_loss_carryforward ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_verification_documents ENABLE ROW LEVEL SECURITY;
