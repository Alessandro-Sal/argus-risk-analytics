-- ============================================================
-- Investment Risk BI Platform — Schema MySQL
-- Generic multi-asset, multi-currency, multi-portfolio
-- ============================================================

CREATE DATABASE IF NOT EXISTS investment_risk_bi
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE investment_risk_bi;

-- ------------------------------------------------------------
-- 1. PORTFOLIOS
--    Un record per ogni portafoglio caricato nel sistema.
--    base_currency = valuta di riferimento per i report.
-- ------------------------------------------------------------
CREATE TABLE portfolios (
    portfolio_id  INT            NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100)   NOT NULL,
    owner         VARCHAR(100)   NOT NULL DEFAULT 'anonymous',
    base_currency CHAR(3)        NOT NULL DEFAULT 'EUR',
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description   TEXT,
    PRIMARY KEY (portfolio_id)
);

-- ------------------------------------------------------------
-- 2. ASSETS
--    Anagrafica degli strumenti finanziari.
--    Un record per ticker — condiviso tra portafogli diversi.
--    gics_sector e country vengono popolati via yfinance.
-- ------------------------------------------------------------
CREATE TABLE assets (
    asset_id    INT           NOT NULL AUTO_INCREMENT,
    ticker      VARCHAR(20)   NOT NULL,
    name        VARCHAR(200),
    asset_class ENUM(
                    'stock',
                    'etf',
                    'bond',
                    'crypto',
                    'cash'
                ) NOT NULL,
    currency    CHAR(3)       NOT NULL,
    gics_sector VARCHAR(100),
    country     VARCHAR(100),
    
    -- Metriche fondamentali & BI
    industry                VARCHAR(100),
    exchange                VARCHAR(50),
    recommendation_key      VARCHAR(50),
    market_cap              BIGINT,
    beta_5y                 DECIMAL(10,4),
    fifty_two_week_high     DECIMAL(18,6),
    fifty_two_week_low      DECIMAL(18,6),
    fifty_day_average       DECIMAL(18,6),
    two_hundred_day_average DECIMAL(18,6),
    profit_margins          DECIMAL(10,4),
    gross_margins           DECIMAL(10,4),
    operating_margins       DECIMAL(10,4),
    total_revenue           BIGINT,
    ebitda                  BIGINT,
    debt_to_equity          DECIMAL(10,4),
    revenue_growth          DECIMAL(10,4),
    earnings_growth         DECIMAL(10,4),
    
    PRIMARY KEY (asset_id),
    UNIQUE KEY uq_ticker (ticker)
);

-- ------------------------------------------------------------
-- 3. TRANSACTIONS
--    Storico completo: acquisti, vendite, dividendi.
--    DECIMAL(18,8) per quantity → supporta crypto (8 decimali).
--    fees incluse per calcolo costo medio preciso.
-- ------------------------------------------------------------
CREATE TABLE transactions (
    tx_id        INT              NOT NULL AUTO_INCREMENT,
    portfolio_id INT              NOT NULL,
    asset_id     INT              NOT NULL,
    tx_date      DATE             NOT NULL,
    tx_type      ENUM(
                     'buy',
                     'sell',
                     'dividend'
                 ) NOT NULL,
    quantity     DECIMAL(18,8)    NOT NULL,
    price        DECIMAL(18,6)    NOT NULL,
    currency     CHAR(3)          NOT NULL,
    fees         DECIMAL(10,4)    NOT NULL DEFAULT 0.0000,
    notes        VARCHAR(255),
    PRIMARY KEY (tx_id),
    CONSTRAINT fk_tx_portfolio FOREIGN KEY (portfolio_id)
        REFERENCES portfolios (portfolio_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_tx_asset FOREIGN KEY (asset_id)
        REFERENCES assets (asset_id)
        ON DELETE RESTRICT,
    INDEX idx_tx_portfolio (portfolio_id),
    INDEX idx_tx_asset     (asset_id),
    INDEX idx_tx_date      (tx_date)
);

-- ------------------------------------------------------------
-- 4. MARKET_PRICES
--    Prezzi storici giornalieri per ogni asset.
--    Popolato automaticamente da yfinance.
--    UNIQUE su (asset_id, price_date) → no duplicati.
-- ------------------------------------------------------------
CREATE TABLE market_prices (
    price_id   INT           NOT NULL AUTO_INCREMENT,
    asset_id   INT           NOT NULL,
    price_date DATE          NOT NULL,
    close      DECIMAL(18,6) NOT NULL,
    volume     BIGINT,
    source     VARCHAR(50)   NOT NULL DEFAULT 'yfinance',
    PRIMARY KEY (price_id),
    CONSTRAINT fk_prices_asset FOREIGN KEY (asset_id)
        REFERENCES assets (asset_id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_asset_date (asset_id, price_date),
    INDEX idx_prices_date (price_date)
);

-- ------------------------------------------------------------
-- 5. ASSET_MAPPING
--    Mappatura per convertire ticker input (es. NOVO-B.CO) 
--    nel formato yfinance corretto (es. NOV.DE).
-- ------------------------------------------------------------
CREATE TABLE asset_mapping (
    mapping_id      INT           NOT NULL AUTO_INCREMENT,
    input_ticker    VARCHAR(50)   NOT NULL,
    yfinance_ticker VARCHAR(50)   NOT NULL,
    description     VARCHAR(255),
    PRIMARY KEY (mapping_id),
    UNIQUE KEY uq_input_ticker (input_ticker)
);

-- ------------------------------------------------------------
-- 6. PORTFOLIO_SNAPSHOTS
--    Snapshot salvato automaticamente al termine della pipeline.
--    Contiene le macro-metriche e i risultati globali dei modelli.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    snapshot_id             INT           NOT NULL AUTO_INCREMENT,
    run_id                  VARCHAR(50)   NOT NULL,
    run_name                VARCHAR(100),
    portfolio_id            INT           NOT NULL,
    calc_date               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_value             DECIMAL(18,6),
    total_pnl               DECIMAL(18,6),
    cagr_pct                DECIMAL(10,4),
    sharpe_ratio            DECIMAL(10,4),
    max_drawdown_pct        DECIMAL(10,4),
    var_95_pct              DECIMAL(10,4),
    hhi_index               DECIMAL(10,4),
    mc_expected_return_1y   DECIMAL(10,4),
    mc_var_95               DECIMAL(10,4),
    PRIMARY KEY (snapshot_id),
    CONSTRAINT fk_snapshot_portfolio FOREIGN KEY (portfolio_id)
        REFERENCES portfolios (portfolio_id)
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 7. SNAPSHOT_POSITIONS
--    Dettaglio riga per riga (asset) collegato a uno snapshot.
--    Unisce le posizioni tradizionali e i cluster dell'algoritmo.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS snapshot_positions (
    record_id        INT           NOT NULL AUTO_INCREMENT,
    snapshot_id      INT           NOT NULL,
    ticker           VARCHAR(20)   NOT NULL,
    asset_class      VARCHAR(50),
    qty_net          DECIMAL(18,8),
    avg_cost         DECIMAL(18,6),
    last_price       DECIMAL(18,6),
    current_value    DECIMAL(18,6),
    unrealized_pnl   DECIMAL(18,6),
    weight_pct       DECIMAL(10,4),
    volatility_pct   DECIMAL(10,4),
    cluster_label    VARCHAR(50),
    PRIMARY KEY (record_id),
    CONSTRAINT fk_sp_snapshot FOREIGN KEY (snapshot_id)
        REFERENCES portfolio_snapshots (snapshot_id)
        ON DELETE CASCADE
);