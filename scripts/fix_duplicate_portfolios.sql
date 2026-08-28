-- ============================================================
-- SCRIPT DI BONIFICA & DEDUPLICAZIONE PORTFOGLI E SNAPSHOT
-- Database: wealth / investment_risk_bi
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Rimappa tutti gli snapshot di 'Wealth Stocks Portfolio' sul canonical ID = 2
UPDATE portfolio_snapshots 
SET portfolio_id = 2 
WHERE portfolio_id IN (
    SELECT portfolio_id FROM (
        SELECT portfolio_id FROM portfolios WHERE name = 'Wealth Stocks Portfolio' AND portfolio_id != 2
    ) as t_stocks
);

-- Rimappa tutte le transazioni di 'Wealth Stocks Portfolio' sul canonical ID = 2
UPDATE transactions 
SET portfolio_id = 2 
WHERE portfolio_id IN (
    SELECT portfolio_id FROM (
        SELECT portfolio_id FROM portfolios WHERE name = 'Wealth Stocks Portfolio' AND portfolio_id != 2
    ) as t_stocks_tx
);

-- Elimina i record duplicati orfani in portfolios per 'Wealth Stocks Portfolio'
DELETE FROM portfolios 
WHERE name = 'Wealth Stocks Portfolio' AND portfolio_id != 2;


-- 2. Rimappa tutti gli snapshot di 'Wealth Crypto Portfolio' sul canonical ID = 31
UPDATE portfolio_snapshots 
SET portfolio_id = 31 
WHERE portfolio_id IN (
    SELECT portfolio_id FROM (
        SELECT portfolio_id FROM portfolios WHERE name = 'Wealth Crypto Portfolio' AND portfolio_id != 31
    ) as t_crypto
);

-- Rimappa tutte le transazioni di 'Wealth Crypto Portfolio' sul canonical ID = 31
UPDATE transactions 
SET portfolio_id = 31 
WHERE portfolio_id IN (
    SELECT portfolio_id FROM (
        SELECT portfolio_id FROM portfolios WHERE name = 'Wealth Crypto Portfolio' AND portfolio_id != 31
    ) as t_crypto_tx
);

-- Elimina i record duplicati orfani in portfolios per 'Wealth Crypto Portfolio'
DELETE FROM portfolios 
WHERE name = 'Wealth Crypto Portfolio' AND portfolio_id != 31;


-- 3. Bonifica generica per qualsiasi altro portafoglio duplicato
DELETE p1 FROM portfolios p1
INNER JOIN portfolios p2 
WHERE p1.portfolio_id > p2.portfolio_id AND p1.name = p2.name;

SET FOREIGN_KEY_CHECKS = 1;

-- 4. Aggiunta vincolo UNIQUE sul nome (ignora se già presente)
ALTER TABLE portfolios ADD UNIQUE KEY uq_portfolio_name (name);
