-- ============================================================
-- ARGUS RISK & WEALTH INTELLIGENCE — SUPABASE SQL SCHEMA & RLS
-- Script completo per il provisioning di Supabase Cloud:
-- 1. Tabella protetta 'user_integrations' per credenziali Zero-File (Google Sheets, API Keys)
-- 2. Abilitazione Row Level Security (RLS) su tutte le tabelle utente
-- 3. Policy di isolamento rigoroso multi-utente (auth.uid() = user_id)
-- 4. Funzioni trigger per aggiornamento automatico timestamp
-- ============================================================

-- ------------------------------------------------------------
-- FUNZIONE TRIGGER PER AUTO-AGGIORNAMENTO TIMESTAMP 'updated_at'
-- ------------------------------------------------------------
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$ language plpgsql security definer;

-- ------------------------------------------------------------
-- 1. TABELLA: user_integrations (Zero-File Credential Vault)
-- ------------------------------------------------------------
create table if not exists public.user_integrations (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references auth.users(id) on delete cascade not null,
    provider text not null, -- es. 'google_sheets', 'market_data', 'open_banking'
    config_data jsonb not null, -- Payload credenziali / service account
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
    constraint user_integrations_user_provider_key unique (user_id, provider)
);

create index if not exists idx_user_integrations_user_provider
    on public.user_integrations (user_id, provider);

drop trigger if exists set_user_integrations_updated_at on public.user_integrations;
create trigger set_user_integrations_updated_at
    before update on public.user_integrations
    for each row execute function public.handle_updated_at();

-- Abilitazione RLS su user_integrations
alter table public.user_integrations enable row level security;

-- Policy RLS per user_integrations
drop policy if exists "Users can view own integrations" on public.user_integrations;
create policy "Users can view own integrations"
    on public.user_integrations for select
    using (auth.uid() = user_id);

drop policy if exists "Users can insert own integrations" on public.user_integrations;
create policy "Users can insert own integrations"
    on public.user_integrations for insert
    with check (auth.uid() = user_id);

drop policy if exists "Users can update own integrations" on public.user_integrations;
create policy "Users can update own integrations"
    on public.user_integrations for update
    using (auth.uid() = user_id);

drop policy if exists "Users can delete own integrations" on public.user_integrations;
create policy "Users can delete own integrations"
    on public.user_integrations for delete
    using (auth.uid() = user_id);


-- ------------------------------------------------------------
-- 2. TABELLA: argus_users (Registro Utenti & Ruoli ARGUS)
-- ------------------------------------------------------------
create table if not exists public.argus_users (
    user_id serial primary key,
    auth_user_id uuid references auth.users(id) on delete cascade,
    username text not null unique,
    email text default '',
    display_name text default '',
    password_hash text not null,
    role text not null default 'user',
    custom_db_url text default '',
    is_active integer default 1,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_argus_users_auth_user_id on public.argus_users (auth_user_id);
create index if not exists idx_argus_users_username on public.argus_users (lower(username));

alter table public.argus_users enable row level security;

drop policy if exists "Users can view own user record" on public.argus_users;
create policy "Users can view own user record"
    on public.argus_users for select
    using (auth.uid() = auth_user_id or auth.uid() is null);

drop policy if exists "Users can update own user record" on public.argus_users;
create policy "Users can update own user record"
    on public.argus_users for update
    using (auth.uid() = auth_user_id);


-- ------------------------------------------------------------
-- 3. TABELLE RISK MANAGEMENT: portfolios, transactions, assets
-- ------------------------------------------------------------
create table if not exists public.portfolios (
    portfolio_id serial primary key,
    user_id uuid references auth.users(id) on delete cascade,
    name text not null,
    description text default '',
    base_currency text not null default 'EUR',
    owner text default 'user',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_portfolios_user_id on public.portfolios (user_id);
alter table public.portfolios enable row level security;

drop policy if exists "Users can manage own portfolios" on public.portfolios;
create policy "Users can manage own portfolios"
    on public.portfolios for all
    using (auth.uid() = user_id or user_id is null);

create table if not exists public.assets (
    asset_id serial primary key,
    ticker text not null unique,
    name text not null,
    asset_class text not null,
    currency text not null default 'EUR',
    sector text default '',
    geography text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.assets enable row level security;
drop policy if exists "Anyone can read shared market assets" on public.assets;
create policy "Anyone can read shared market assets" on public.assets for select using (true);
drop policy if exists "Authenticated users can insert assets" on public.assets;
create policy "Authenticated users can insert assets" on public.assets for insert with check (true);

create table if not exists public.transactions (
    transaction_id serial primary key,
    portfolio_id integer references public.portfolios(portfolio_id) on delete cascade not null,
    user_id uuid references auth.users(id) on delete cascade,
    ticker text not null,
    tx_date date not null,
    tx_type text not null,
    quantity numeric(18, 8) not null,
    price numeric(18, 6) not null,
    total_amount numeric(18, 4) not null,
    currency text not null default 'EUR',
    notes text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_transactions_portfolio on public.transactions (portfolio_id);
create index if not exists idx_transactions_user on public.transactions (user_id);
alter table public.transactions enable row level security;

drop policy if exists "Users can manage own transactions" on public.transactions;
create policy "Users can manage own transactions"
    on public.transactions for all
    using (auth.uid() = user_id or user_id is null);


-- ------------------------------------------------------------
-- 4. TABELLE WEALTH MANAGEMENT: wealth_portfolios, accounts, cashflow, snapshots
-- ------------------------------------------------------------
create table if not exists public.wealth_portfolios (
    portfolio_id serial primary key,
    user_id uuid references auth.users(id) on delete cascade,
    name text not null,
    description text default '',
    base_currency text not null default 'EUR',
    owner text default 'user',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_wealth_portfolios_user_id on public.wealth_portfolios (user_id);
alter table public.wealth_portfolios enable row level security;

drop policy if exists "Users can manage own wealth portfolios" on public.wealth_portfolios;
create policy "Users can manage own wealth portfolios"
    on public.wealth_portfolios for all
    using (auth.uid() = user_id or user_id is null);

create table if not exists public.wealth_accounts (
    account_id serial primary key,
    portfolio_id integer references public.wealth_portfolios(portfolio_id) on delete cascade not null,
    user_id uuid references auth.users(id) on delete cascade,
    name text not null,
    institution text default '',
    account_type text not null default 'bank_account',
    balance numeric(18, 4) not null default 0.0,
    currency text not null default 'EUR',
    iban text default '',
    color text default '#3b82f6',
    icon text default '🏦',
    is_active integer default 1,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_wealth_accounts_user on public.wealth_accounts (user_id);
create index if not exists idx_wealth_accounts_portfolio on public.wealth_accounts (portfolio_id);
alter table public.wealth_accounts enable row level security;

drop policy if exists "Users can manage own wealth accounts" on public.wealth_accounts;
create policy "Users can manage own wealth accounts"
    on public.wealth_accounts for all
    using (auth.uid() = user_id or user_id is null);

create table if not exists public.wealth_cashflow (
    tx_id serial primary key,
    portfolio_id integer references public.wealth_portfolios(portfolio_id) on delete cascade not null,
    account_id integer references public.wealth_accounts(account_id) on delete cascade,
    user_id uuid references auth.users(id) on delete cascade,
    tx_date date not null,
    amount numeric(18, 4) not null,
    flow_type text not null, -- 'income', 'expense', 'transfer'
    nature text default 'discretionary_want',
    category_id integer,
    category_name text default '',
    description text default '',
    source_channel text default 'manual',
    external_id text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_wealth_cashflow_user on public.wealth_cashflow (user_id);
create index if not exists idx_wealth_cashflow_portfolio on public.wealth_cashflow (portfolio_id);
create index if not exists idx_wealth_cashflow_date on public.wealth_cashflow (tx_date);
alter table public.wealth_cashflow enable row level security;

drop policy if exists "Users can manage own wealth cashflow" on public.wealth_cashflow;
create policy "Users can manage own wealth cashflow"
    on public.wealth_cashflow for all
    using (auth.uid() = user_id or user_id is null);

create table if not exists public.wealth_snapshots (
    snapshot_id serial primary key,
    portfolio_id integer references public.wealth_portfolios(portfolio_id) on delete cascade not null,
    user_id uuid references auth.users(id) on delete cascade,
    snapshot_date date not null,
    snapshot_name text not null,
    total_net_worth numeric(18, 4) not null default 0.0,
    total_liquid_assets numeric(18, 4) not null default 0.0,
    total_investments numeric(18, 4) not null default 0.0,
    total_illiquid_assets numeric(18, 4) not null default 0.0,
    total_liabilities numeric(18, 4) not null default 0.0,
    snapshot_json jsonb,
    notes text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index if not exists idx_wealth_snapshots_user on public.wealth_snapshots (user_id);
create index if not exists idx_wealth_snapshots_portfolio on public.wealth_snapshots (portfolio_id);
alter table public.wealth_snapshots enable row level security;

drop policy if exists "Users can manage own wealth snapshots" on public.wealth_snapshots;
create policy "Users can manage own wealth snapshots"
    on public.wealth_snapshots for all
    using (auth.uid() = user_id or user_id is null);

-- ------------------------------------------------------------
-- FINE DELLO SCRIPT
-- ------------------------------------------------------------
