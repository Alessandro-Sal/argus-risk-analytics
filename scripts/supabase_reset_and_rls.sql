-- =============================================================================
-- ARGUS ENTERPRISE — SUPABASE SQL REMOTE RESET & MULTI-TENANT RLS SETUP
-- Eseguire questo script nel SQL Editor del progetto Supabase per:
-- 1. Svuotare in sicurezza tutti i dati remoti (TRUNCATE) senza toccare il filesystem locale.
-- 2. Creare la tabella user_integrations per le credenziali in-memory (Zero-Disk Secrets).
-- 3. Garantire la colonna user_id UUID su tutte le tabelle tenant-specifiche.
-- 4. Blindare tutte le tabelle con Row Level Security (RLS) associata ad auth.uid().
-- =============================================================================

-- =============================================================================
-- 1. RESET TOTALE DATI REMOTI (SENZA MODIFICARE IL FILESYSTEM LOCALE)
-- =============================================================================
SET session_replication_role = 'replica';

DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'portfolio_transactions', 'transactions', 'portfolio_snapshots', 'portfolios',
        'wealth_cashflow', 'wealth_accounts', 'wealth_physical_assets',
        'wealth_pension_plans', 'wealth_networth_snapshots', 'wealth_snapshots',
        'wealth_portfolio_risk_links', 'wealth_profiles', 'tax_verification_documents',
        'tax_f24_entries', 'tax_deductible_expenses', 'user_integrations', 'workspaces'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('TRUNCATE TABLE public.%I CASCADE;', tbl);
        END IF;
    END LOOP;
END $$;

SET session_replication_role = 'origin';

-- =============================================================================
-- 2. TABELLA INTEGRAZIONI E CREDENZIALI DINAMICHE (ZERO-FILE DEPENDENCY)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.user_integrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    provider TEXT NOT NULL, -- es. 'google_sheets', 'market_data'
    config_data JSONB NOT NULL, -- credenziali di servizio in JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, provider)
);

-- =============================================================================
-- 3. GARANZIA COLONNA user_id UUID SU TUTTE LE TABELLE APPLICATIVE
-- =============================================================================
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'portfolios', 'portfolio_transactions', 'transactions', 'portfolio_snapshots',
        'wealth_profiles', 'wealth_accounts', 'wealth_cashflow',
        'wealth_pension_plans', 'wealth_physical_assets', 'wealth_networth_snapshots',
        'wealth_snapshots', 'wealth_portfolio_risk_links', 'tax_verification_documents',
        'tax_f24_entries', 'tax_deductible_expenses', 'user_integrations'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = tbl AND column_name = 'user_id'
            ) THEN
                EXECUTE format('ALTER TABLE public.%I ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;', tbl);
            END IF;
        END IF;
    END LOOP;
END $$;

-- =============================================================================
-- 4. ABILITAZIONE ROW LEVEL SECURITY (RLS) RIGOROSA SU TUTTE LE TABELLE
-- =============================================================================
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'portfolios', 'portfolio_transactions', 'transactions', 'portfolio_snapshots',
        'wealth_profiles', 'wealth_accounts', 'wealth_cashflow',
        'wealth_pension_plans', 'wealth_physical_assets', 'wealth_networth_snapshots',
        'wealth_snapshots', 'wealth_portfolio_risk_links', 'tax_verification_documents',
        'tax_f24_entries', 'tax_deductible_expenses', 'user_integrations'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
            EXECUTE format('DROP POLICY IF EXISTS "tenant_isolation_policy" ON public.%I;', tbl);
            EXECUTE format('
                CREATE POLICY "tenant_isolation_policy" ON public.%I
                FOR ALL
                USING (auth.uid() = user_id)
                WITH CHECK (auth.uid() = user_id);
            ', tbl);
        END IF;
    END LOOP;
END $$;
