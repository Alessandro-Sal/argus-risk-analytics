-- ============================================================
-- scripts/DB_wealth.sql
-- ARGUS — Wealth Management & Personal Finance Schema
-- Multi-Account, Multi-Currency, Cash Flow & Net Worth
-- ============================================================

CREATE DATABASE IF NOT EXISTS wealth
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE wealth;

-- ------------------------------------------------------------
-- 1. WEALTH ACCOUNTS (Conti Correnti, Risparmio, Carte, Debiti)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_accounts (
    account_id    INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    account_type  ENUM(
                    'checking',        -- Conto Corrente principale
                    'savings',         -- Conto Deposito / Risparmio
                    'emergency_fund',  -- Fondo Emergenza dedicato
                    'brokerage_cash',  -- Liquidità su conto titoli/crypto
                    'credit_card',     -- Carta di Credito (passività a breve)
                    'loan',            -- Prestito personale / finanziamento
                    'mortgage'         -- Mutuo ipotecario
                  ) NOT NULL DEFAULT 'checking',
    institution   VARCHAR(100) NOT NULL DEFAULT 'Banca',
    currency      CHAR(3) NOT NULL DEFAULT 'EUR',
    balance       DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    iban          VARCHAR(35) NULL,
    notes         VARCHAR(255) NULL,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 2. WEALTH CATEGORIES (Albero Categorie di Spesa ed Entrata)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    flow_type     ENUM('income', 'expense', 'transfer') NOT NULL,
    nature        ENUM(
                    'essential_need',      -- 50% Needs (Affitto, bollette, spesa, salute)
                    'discretionary_want',  -- 30% Wants (Ristoranti, viaggi, svago, shopping)
                    'saving_investment',   -- 20% Savings (PAC, fondo pensione, risparmio)
                    'debt_service',        -- Rata mutuo/prestito
                    'tax',                 -- Imposte, bolli, commercialista
                    'inflow_active',       -- Stipendio, fatturato, bonus
                    'inflow_passive'       -- Dividendi, cedole, affitti, interessi
                  ) NOT NULL DEFAULT 'essential_need',
    parent_id     INT NULL,
    icon          VARCHAR(50) NOT NULL DEFAULT '🏷️',
    color         VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    is_system     BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_cat_parent FOREIGN KEY (parent_id)
        REFERENCES wealth_categories (category_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 3. WEALTH CASHFLOW (Libro Mastro Entrate e Uscite)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_cashflow (
    tx_id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id      INT NOT NULL,
    category_id     INT NOT NULL,
    tx_date         DATE NOT NULL,
    amount          DECIMAL(18,2) NOT NULL,
    currency        CHAR(3) NOT NULL DEFAULT 'EUR',
    direction       ENUM('inflow', 'outflow', 'transfer') NOT NULL,
    merchant        VARCHAR(150) NULL,
    notes           VARCHAR(255) NULL,
    is_recurring    BOOLEAN NOT NULL DEFAULT FALSE,
    payment_method  VARCHAR(50) NOT NULL DEFAULT 'Bonifico / Carta',
    tags            VARCHAR(255) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wf_account FOREIGN KEY (account_id)
        REFERENCES wealth_accounts (account_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_wf_category FOREIGN KEY (category_id)
        REFERENCES wealth_categories (category_id)
        ON DELETE RESTRICT,
    INDEX idx_cashflow_date (tx_date),
    INDEX idx_cashflow_account (account_id),
    INDEX idx_cashflow_category (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 4. WEALTH PHYSICAL ASSETS (Orologi di Lusso, Immobili, Metalli)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_physical_assets (
    asset_id             INT AUTO_INCREMENT PRIMARY KEY,
    name                 VARCHAR(150) NOT NULL,
    asset_category       ENUM(
                           'luxury_watches',   -- Orologi da collezione (Rolex, Patek, Omega...)
                           'real_estate',      -- Immobili, terreni, garage
                           'precious_metals',  -- Oro fisico, argento, lingotti
                           'collectibles_art', -- Arte, auto d'epoca, numismatica
                           'vehicles',         -- Auto, moto
                           'other'
                         ) NOT NULL DEFAULT 'luxury_watches',
    brand_or_location    VARCHAR(100) NULL,     -- es. 'Rolex', 'Milano Centro'
    model_or_specs       VARCHAR(150) NULL,     -- es. 'Submariner Date 126610LN', 'Trilocale 90mq'
    reference_number     VARCHAR(100) NULL,     -- Referenza esatta o foglio catastale
    acquisition_date     DATE NULL,
    purchase_price       DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    current_market_value DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    valuation_date       DATE NULL,
    valuation_source     VARCHAR(100) NULL DEFAULT 'Stima di Mercato / Chrono24 / OMI',
    condition_grade      VARCHAR(50) NULL DEFAULT 'Excellent / Full Set',
    currency             CHAR(3) NOT NULL DEFAULT 'EUR',
    notes                TEXT NULL,
    updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 5. WEALTH PENSION PLANS (Fondi Pensione, Previdenza, PIP, TFR)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_pension_plans (
    plan_id                 INT AUTO_INCREMENT PRIMARY KEY,
    plan_name               VARCHAR(150) NOT NULL,
    provider                VARCHAR(100) NOT NULL,
    plan_type               ENUM(
                              'fondo_pensione_aperto',
                              'fondo_negoziale_chiuso',
                              'pip_individuale',
                              'tfr_in_azienda',
                              'gestione_separata'
                            ) NOT NULL DEFAULT 'fondo_pensione_aperto',
    accumulated_value       DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    monthly_employee_contrib DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    monthly_employer_contrib DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    tax_deductible_annual   DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    expected_retirement_age INT NOT NULL DEFAULT 67,
    currency                CHAR(3) NOT NULL DEFAULT 'EUR',
    investment_line         VARCHAR(100) NULL DEFAULT 'Azionario 100% / Crescita',
    notes                   TEXT NULL,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 6. WEALTH BUDGETS & TARGETS (Limiti di Spesa e Regola 50/30/20)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_budgets (
    budget_id          INT AUTO_INCREMENT PRIMARY KEY,
    category_id        INT NOT NULL,
    monthly_cap_amount DECIMAL(18,2) NOT NULL,
    year_month         VARCHAR(7) NOT NULL, -- 'YYYY-MM'
    alert_threshold    DECIMAL(5,2) NOT NULL DEFAULT 85.00, -- Notifica al raggiungimento dell'85%
    CONSTRAINT fk_wb_category FOREIGN KEY (category_id)
        REFERENCES wealth_categories (category_id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_cat_month (category_id, year_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- 7. WEALTH NET WORTH SNAPSHOTS (Storico Patrimonio Netto Globale)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
    snapshot_id               INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date             DATE NOT NULL,
    total_net_worth           DECIMAL(18,2) NOT NULL,
    liquid_assets             DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    financial_investments     DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    physical_assets_total     DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    watches_total             DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    real_estate_total         DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    pension_total             DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    total_liabilities         DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    monthly_income_avg        DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    monthly_expense_avg       DECIMAL(18,2) NOT NULL DEFAULT 0.00,
    savings_rate_pct          DECIMAL(10,4) NOT NULL DEFAULT 0.00,
    emergency_runway_months   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    wealth_health_score       DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    notes                     VARCHAR(255) NULL,
    created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_wealth_snap_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
