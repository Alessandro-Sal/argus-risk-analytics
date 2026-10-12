# ============================================================
# core/supabase_cloud.py
# ARGUS — Zero-Cost Cloud Platform & Supabase Integration Layer
# Supports:
#   - Supabase PostgreSQL (Transaction Pooler 6543 & Session 5432)
#   - Automatic SSL & Dialect Normalization
#   - Idempotent PostgreSQL DDL & RLS Schema Generation
#   - Free Tier 500 MB Quota Telemetry & Storage Optimizer
#   - 1-Click Local SQLite -> Supabase Cloud Migration
#   - Supabase Auth REST + Single-Owner Gate + Guest Demo Isolation
#   - Supabase Storage Private Vault for PDF Tax Documents
# ============================================================

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import Engine, create_engine
from sqlalchemy import inspect as sqla_inspect
from sqlalchemy import text as sqlt

logger = logging.getLogger("argus.supabase_cloud")

# Free Tier Limits (Supabase Free Plan)
SUPABASE_FREE_TIER_DB_MB = 500.0
SUPABASE_FREE_TIER_STORAGE_MB = 1024.0
SUPABASE_INACTIVITY_PAUSE_DAYS = 7

# Mapping of ARGUS tables to their serial/auto-increment Primary Key column
TABLE_PK_MAP: Dict[str, str] = {
    "portfolios": "portfolio_id",
    "assets": "asset_id",
    "transactions": "tx_id",
    "market_prices": "price_id",
    "portfolio_snapshots": "snapshot_id",
    "snapshot_positions": "id",
    "wealth_profiles": "profile_id",
    "wealth_accounts": "account_id",
    "wealth_categories": "category_id",
    "wealth_cashflow": "tx_id",
    "wealth_physical_assets": "asset_id",
    "wealth_pension_plans": "plan_id",
    "wealth_networth_snapshots": "snapshot_id",
    "wealth_fixed_expenses": "fixed_id",
    "wealth_goals": "goal_id",
    "tax_declarations": "id",
    "tax_loss_carryforward": "id",
    "tax_verification_documents": "id",
}

# Average bytes per row (including B-Tree index overhead) for quota estimation
ESTIMATED_BYTES_PER_ROW: Dict[str, int] = {
    "market_prices": 115,
    "wealth_cashflow": 290,
    "transactions": 240,
    "snapshot_positions": 180,
    "portfolio_snapshots": 320,
    "wealth_networth_snapshots": 450,
    "assets": 380,
    "wealth_accounts": 260,
    "wealth_categories": 180,
    "wealth_physical_assets": 340,
    "wealth_pension_plans": 520,
    "wealth_fixed_expenses": 240,
    "wealth_goals": 260,
    "tax_declarations": 420,
    "tax_loss_carryforward": 220,
    "tax_verification_documents": 480,
    "portfolios": 200,
    "wealth_profiles": 200,
}


# ── 1. URL Normalization & Secrets Discovery ──────────────────


def normalize_supabase_db_url(raw_url: Optional[str], ensure_ssl: bool = True) -> str:
    """
    Normalizza un URI di connessione PostgreSQL/Supabase per SQLAlchemy + psycopg2.
    - Converte 'postgres://' o 'postgresql://' in 'postgresql+psycopg2://'
    - Aggiunge 'sslmode=require' per connessioni cloud remote se non specificato.
    """
    if not raw_url or not str(raw_url).strip():
        return ""

    url = str(raw_url).strip().strip('"').strip("'")

    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg://"):
        url = "postgresql+psycopg2://" + url[len("postgresql+psycopg://") :]

    if not url.startswith("postgresql"):
        return url

    if ensure_ssl and "sslmode=" not in url:
        is_local = any(h in url for h in ["@localhost", "@127.0.0.1", "@0.0.0.0"])
        if not is_local:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"

    return url


def mask_db_url(db_url: Optional[str]) -> str:
    """Maschera la password in un URL di connessione DB per la visualizzazione sicura in UI."""
    if not db_url:
        return "Non configurato"
    try:
        parsed = urllib.parse.urlsplit(str(db_url))
        if parsed.password:
            user_info = parsed.username or "user"
            host_info = f"{parsed.hostname or ''}"
            if parsed.port:
                host_info += f":{parsed.port}"
            netloc = f"{user_info}:****@{host_info}"
            return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))
        return str(db_url)
    except Exception:
        return "postgresql+psycopg2://****"


def _read_secret_or_env(key: str, default: str = "") -> str:
    """Legge una configurazione prioritariamente da os.environ e poi da st.secrets."""
    val = os.getenv(key)
    if val is not None and str(val).strip() != "":
        return str(val).strip()

    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            if key in st.secrets:
                return str(st.secrets[key]).strip()
            if "supabase" in st.secrets and isinstance(st.secrets["supabase"], dict):
                sub_key = key.lower().replace("supabase_", "")
                if sub_key in st.secrets["supabase"]:
                    return str(st.secrets["supabase"][sub_key]).strip()
                if key in st.secrets["supabase"]:
                    return str(st.secrets["supabase"][key]).strip()
    except Exception:
        pass

    return default


def get_supabase_config() -> Dict[str, Any]:
    """
    Raccoglie la configurazione Cloud Supabase da session_state, variabili d'ambiente
    o `.streamlit/secrets.toml`.
    """
    session_db_url = ""
    session_supa_url = ""
    session_anon_key = ""
    try:
        import streamlit as st

        session_db_url = str(st.session_state.get("supabase_db_url", "") or "").strip()
        session_supa_url = str(st.session_state.get("supabase_url", "") or "").strip()
        session_anon_key = str(st.session_state.get("supabase_anon_key", "") or "").strip()
    except Exception:
        pass

    raw_db_url = (
        session_db_url
        or _read_secret_or_env("SUPABASE_DB_URL")
        or _read_secret_or_env("DATABASE_URL")
    )
    # Only treat DATABASE_URL as Supabase/Postgres if it starts with postgres
    if raw_db_url and not raw_db_url.lower().startswith("postgres"):
        raw_db_url = ""

    normalized_db_url = normalize_supabase_db_url(raw_db_url)
    supabase_url = (session_supa_url or _read_secret_or_env("SUPABASE_URL")).rstrip("/")
    supabase_anon_key = (
        session_anon_key
        or _read_secret_or_env("SUPABASE_ANON_KEY")
        or _read_secret_or_env("SUPABASE_KEY")
    )
    supabase_service_key = _read_secret_or_env("SUPABASE_SERVICE_ROLE_KEY")
    admin_password = _read_secret_or_env("ARGUS_ADMIN_PASSWORD")
    require_login_str = _read_secret_or_env("ARGUS_REQUIRE_LOGIN", "false").lower()
    require_login = require_login_str in ("1", "true", "yes", "on")
    guest_demo_str = _read_secret_or_env("ARGUS_ENABLE_GUEST_DEMO", "true").lower()
    enable_guest_demo = guest_demo_str in ("1", "true", "yes", "on")
    storage_bucket = _read_secret_or_env("SUPABASE_STORAGE_BUCKET", "tax-documents")

    return {
        "db_url": normalized_db_url,
        "masked_db_url": mask_db_url(normalized_db_url),
        "supabase_url": supabase_url,
        "supabase_anon_key": supabase_anon_key,
        "supabase_service_key": supabase_service_key,
        "admin_password": admin_password,
        "require_login": require_login,
        "enable_guest_demo": enable_guest_demo,
        "storage_bucket": storage_bucket,
        "is_configured": bool(normalized_db_url),
        "has_rest_api": bool(supabase_url and (supabase_anon_key or supabase_service_key)),
    }


def is_supabase_configured() -> bool:
    """Restituisce True se un database PostgreSQL/Supabase è configurato."""
    return bool(get_supabase_config().get("is_configured"))


# ── 2. Engine Creation & Health Diagnostics ───────────────────


def create_supabase_engine(db_url: Optional[str] = None, connect_timeout: int = 8) -> Engine:
    """
    Crea un SQLAlchemy Engine ottimizzato per Supabase PostgreSQL (compatibile con
    Supavisor Transaction Pooler su porta 6543 e Session Pooler su porta 5432).
    """
    cfg = get_supabase_config()
    target_url = normalize_supabase_db_url(db_url or cfg.get("db_url", ""))
    if not target_url:
        raise ValueError("Nessun SUPABASE_DB_URL configurato.")

    connect_args: Dict[str, Any] = {"connect_timeout": connect_timeout}
    if "sslmode=" not in target_url and not any(h in target_url for h in ["@localhost", "@127.0.0.1"]):
        connect_args["sslmode"] = "require"

    engine = create_engine(
        target_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        pool_timeout=15,
        connect_args=connect_args,
    )
    return engine


def test_supabase_connection(db_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifica la connettività verso Supabase PostgreSQL, misura la latenza round-trip,
    rileva la versione server e conta le tabelle attive nello schema public.
    """
    cfg = get_supabase_config()
    raw_target = db_url or cfg.get("db_url", "")
    normalized = normalize_supabase_db_url(raw_target)
    if not normalized:
        return {
            "ok": False,
            "latency_ms": 0.0,
            "pg_version": None,
            "current_db": None,
            "tables_count": 0,
            "masked_url": "Non configurato",
            "error": "SUPABASE_DB_URL vuoto o non valido.",
        }

    t0 = time.perf_counter()
    eng = None
    try:
        eng = create_supabase_engine(normalized, connect_timeout=6)
        with eng.connect() as conn:
            ver = conn.execute(sqlt("SELECT version()")).scalar()
            curr_db = conn.execute(sqlt("SELECT current_database()")).scalar()
            tbl_cnt = conn.execute(
                sqlt(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
            ).scalar()
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return {
            "ok": True,
            "latency_ms": latency_ms,
            "pg_version": str(ver).split(",")[0] if ver else "PostgreSQL",
            "current_db": str(curr_db or "postgres"),
            "tables_count": int(tbl_cnt or 0),
            "masked_url": mask_db_url(normalized),
            "error": None,
        }
    except Exception as ex:
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "pg_version": None,
            "current_db": None,
            "tables_count": 0,
            "masked_url": mask_db_url(normalized),
            "error": str(ex),
        }
    finally:
        if eng is not None:
            try:
                eng.dispose()
            except Exception:
                pass


# ── 3. Idempotent PostgreSQL / Supabase DDL Generator ─────────


def generate_supabase_schema_sql(include_rls: bool = True, include_storage: bool = True) -> str:
    """
    Genera lo script SQL completo e idempotente per PostgreSQL / Supabase (19 tabelle:
    Risk BI, Wealth Management, Tax Engine, Portfolio Links e Cloud Heartbeat).
    Nota architetturale: i campi flag (is_active, is_system, is_recurring, is_split,
    is_officially_filed) sono definiti come INTEGER (0/1) per garantire compatibilità
    al 100% con le query SQL cross-engine (SQLite / MySQL / PostgreSQL).
    """
    ddl_parts = [
        "-- ============================================================",
        "-- ARGUS INSTITUTIONAL PLATFORM — SUPABASE POSTGRESQL SCHEMA",
        "-- Zero-Cost Cloud Architecture (PostgreSQL 15+ / Supabase)",
        "-- ============================================================",
        "",
        "-- 1. CORE RISK & PORTFOLIO TABLES",
        """CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner VARCHAR(100) NOT NULL DEFAULT 'user',
    base_currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);""",
        """CREATE TABLE IF NOT EXISTS assets (
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
);""",
        """CREATE TABLE IF NOT EXISTS transactions (
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
);""",
        """CREATE TABLE IF NOT EXISTS market_prices (
    price_id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    close NUMERIC(18,6) NOT NULL,
    volume BIGINT,
    source VARCHAR(50) NOT NULL DEFAULT 'yfinance',
    CONSTRAINT uq_asset_date UNIQUE (asset_id, price_date)
);""",
        """CREATE TABLE IF NOT EXISTS portfolio_snapshots (
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
);""",
        """CREATE TABLE IF NOT EXISTS snapshot_positions (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(asset_id),
    quantity NUMERIC(18,6) NOT NULL,
    market_val_eur NUMERIC(18,2) NOT NULL,
    weight_pct NUMERIC(8,4) NOT NULL,
    unrealized_pnl NUMERIC(18,2),
    component_var_pct NUMERIC(8,4)
);""",
        "",
        "-- 2. WEALTH MANAGEMENT & FAMILY OFFICE TABLES",
        """CREATE TABLE IF NOT EXISTS wealth_profiles (
    profile_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    owner VARCHAR(100) NOT NULL DEFAULT 'user',
    base_currency VARCHAR(10) NOT NULL DEFAULT 'EUR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);""",
        """CREATE TABLE IF NOT EXISTS wealth_accounts (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    flow_type VARCHAR(20) NOT NULL,
    nature VARCHAR(40) NOT NULL DEFAULT 'essential_need',
    parent_id INTEGER REFERENCES wealth_categories(category_id) ON DELETE SET NULL,
    icon VARCHAR(16) NOT NULL DEFAULT '🏷️',
    color VARCHAR(16) NOT NULL DEFAULT '#6366f1',
    is_system INTEGER NOT NULL DEFAULT 0
);""",
        """CREATE TABLE IF NOT EXISTS wealth_cashflow (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_physical_assets (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_pension_plans (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_networth_snapshots (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_fixed_expenses (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_goals (
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
);""",
        """CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
    wealth_portfolio_id INTEGER NOT NULL,
    risk_portfolio_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wealth_portfolio_id, risk_portfolio_id)
);""",
        "",
        "-- 3. TAX ENGINE & FISCAL AUDIT VAULT TABLES",
        """CREATE TABLE IF NOT EXISTS tax_declarations (
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
);""",
        """CREATE TABLE IF NOT EXISTS tax_loss_carryforward (
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
);""",
        """CREATE TABLE IF NOT EXISTS tax_verification_documents (
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
);""",
        "",
        "-- 4. CLOUD HEARTBEAT TABLE (ANTI-PAUSE KEEP-ALIVE FOR SUPABASE FREE TIER)",
        """CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
    id SERIAL PRIMARY KEY,
    ping_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(80) NOT NULL DEFAULT 'github_actions_keepalive',
    status VARCHAR(40) NOT NULL DEFAULT 'OK',
    details TEXT
);""",
        "",
        "-- 5. HIGH-PERFORMANCE B-TREE INDEXES",
        "CREATE INDEX IF NOT EXISTS idx_tx_portfolio_date ON transactions(portfolio_id, tx_date);",
        "CREATE INDEX IF NOT EXISTS idx_tx_asset ON transactions(asset_id);",
        "CREATE INDEX IF NOT EXISTS idx_price_lookup ON market_prices(asset_id, price_date);",
        "CREATE INDEX IF NOT EXISTS idx_cf_acct_date ON wealth_cashflow(account_id, tx_date DESC);",
        "CREATE INDEX IF NOT EXISTS idx_cf_cat_date ON wealth_cashflow(category_id, tx_date DESC);",
        "CREATE INDEX IF NOT EXISTS idx_cf_port_date ON wealth_cashflow(portfolio_id, tx_date DESC);",
        "CREATE INDEX IF NOT EXISTS idx_cf_port_cat ON wealth_cashflow(portfolio_id, category_id);",
        "CREATE INDEX IF NOT EXISTS idx_cf_tx_hash ON wealth_cashflow(account_id, tx_hash);",
        "CREATE INDEX IF NOT EXISTS idx_snap_port_date ON wealth_networth_snapshots(portfolio_id, snapshot_date DESC);",
        "CREATE INDEX IF NOT EXISTS idx_phys_port ON wealth_physical_assets(portfolio_id);",
        "CREATE INDEX IF NOT EXISTS idx_pens_port ON wealth_pension_plans(portfolio_id);",
        "CREATE INDEX IF NOT EXISTS idx_acct_port ON wealth_accounts(portfolio_id);",
        "CREATE INDEX IF NOT EXISTS idx_verif_profile_year ON tax_verification_documents(profile_id, tax_year);",
        "CREATE INDEX IF NOT EXISTS idx_verif_doc_type ON tax_verification_documents(doc_type);",
    ]

    if include_storage:
        ddl_parts.extend(
            [
                "",
                "-- 6. SUPABASE STORAGE PRIVATE BUCKET FOR FISCAL PDF VAULT",
                """DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        INSERT INTO storage.buckets (id, name, public)
        VALUES ('tax-documents', 'tax-documents', false)
        ON CONFLICT (id) DO NOTHING;
    END IF;
END $$;""",
            ]
        )

    if include_rls:
        ddl_parts.extend(
            [
                "",
                "-- 7. OPTIONAL ROW-LEVEL SECURITY (RLS) HARDENING FOR SUPABASE DATA API",
                "-- Nota: la connessione diretta PostgreSQL (ruolo 'postgres') bypassa RLS,",
                "-- mentre l'attivazione di RLS blocca qualsiasi accesso non autorizzato via PostgREST/Anon Key.",
                "ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_profiles ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_accounts ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_cashflow ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_physical_assets ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_pension_plans ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_networth_snapshots ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_fixed_expenses ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE wealth_goals ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE tax_declarations ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE tax_loss_carryforward ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE tax_verification_documents ENABLE ROW LEVEL SECURITY;",
            ]
        )

    return "\n".join(ddl_parts) + "\n"


def reset_postgres_sequences(engine: Engine) -> Dict[str, int]:
    """
    Sincronizza tutte le sequenze SERIAL/BIGSERIAL in PostgreSQL con il valore MAX(pk)
    presente in ciascuna tabella. Indispensabile dopo migrazioni bulk da SQLite/MySQL
    per evitare errori UniqueViolation sui successivi INSERT.
    """
    if getattr(engine, "dialect", None) is None or engine.dialect.name != "postgresql":
        return {}

    synced: Dict[str, int] = {}
    insp = sqla_inspect(engine)
    existing_tables = set(insp.get_table_names())

    with engine.begin() as conn:
        for tbl, pk in TABLE_PK_MAP.items():
            if tbl not in existing_tables:
                continue
            try:
                with conn.begin_nested():
                    max_val = conn.execute(sqlt(f"SELECT COALESCE(MAX({pk}), 0) FROM {tbl}")).scalar()
                    max_int = int(max_val or 0)
                    is_called = True if max_int > 0 else False
                    seq_val = max_int if max_int > 0 else 1
                    conn.execute(
                        sqlt("SELECT setval(pg_get_serial_sequence(:tbl, :pk), :val, :is_called)"),
                        {"tbl": tbl, "pk": pk, "val": seq_val, "is_called": is_called},
                    )
                    synced[tbl] = max_int
            except Exception as ex:
                logger.debug("Impossibile sincronizzare sequenza per %s.%s: %s", tbl, pk, ex)

    return synced


def record_cloud_heartbeat(engine: Engine, source: str = "argus_app", details: str = "Active ping") -> bool:
    """
    Registra un ping nella tabella `argus_cloud_heartbeat` per mantenere attivo
    il progetto Supabase Free Tier (evitando la pausa automatica dopo 7 giorni).
    """
    try:
        is_sqlite = getattr(engine, "dialect", None) is not None and engine.dialect.name == "sqlite"
        is_postgres = getattr(engine, "dialect", None) is not None and engine.dialect.name == "postgresql"
        with engine.begin() as conn:
            if is_sqlite:
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ping_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT NOT NULL DEFAULT 'argus_app',
                        status TEXT NOT NULL DEFAULT 'OK',
                        details TEXT
                    )
                """)
                )
            elif is_postgres:
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
                        id SERIAL PRIMARY KEY,
                        ping_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        source VARCHAR(80) NOT NULL DEFAULT 'argus_app',
                        status VARCHAR(40) NOT NULL DEFAULT 'OK',
                        details TEXT
                    )
                """)
                )
            else:
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        ping_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        source VARCHAR(80) NOT NULL DEFAULT 'argus_app',
                        status VARCHAR(40) NOT NULL DEFAULT 'OK',
                        details TEXT
                    )
                """)
                )

            conn.execute(
                sqlt("""
                INSERT INTO argus_cloud_heartbeat (source, status, details)
                VALUES (:src, 'OK', :det)
            """),
                {"src": source, "det": details},
            )
            # Keep only last 100 heartbeats so table never grows
            conn.execute(
                sqlt("""
                DELETE FROM argus_cloud_heartbeat
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM argus_cloud_heartbeat ORDER BY id DESC LIMIT 100
                    ) AS recent_hb
                )
            """)
            )
        return True
    except Exception as ex:
        logger.debug("Heartbeat log skipped: %s", ex)
        return False


# ── 4. Free Tier 500 MB Storage Analyzer & Optimizer ─────────


def optimize_supabase_storage_footprint(
    engine: Engine,
    prune_orphan_prices: bool = False,
    max_price_age_years: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Analizza l'impronta di storage del database rispetto al limite di 500 MB del
    piano gratuito Supabase e, se richiesto, ottimizza lo spazio eliminando prezzi
    storici orfani o più vecchi di `max_price_age_years` anni.
    """
    insp = sqla_inspect(engine)
    existing_tables = set(insp.get_table_names())
    is_postgres = getattr(engine, "dialect", None) is not None and engine.dialect.name == "postgresql"

    pruned_orphans = 0
    pruned_aged = 0

    with engine.begin() as conn:
        if prune_orphan_prices and "market_prices" in existing_tables and "transactions" in existing_tables:
            try:
                res_orph = conn.execute(
                    sqlt("""
                    DELETE FROM market_prices
                    WHERE asset_id NOT IN (SELECT DISTINCT asset_id FROM transactions WHERE asset_id IS NOT NULL)
                """)
                )
                pruned_orphans = int(res_orph.rowcount or 0)
            except Exception as ex:
                logger.warning("Errore durante pulizia market_prices orfani: %s", ex)

        if (
            max_price_age_years is not None
            and int(max_price_age_years) > 0
            and "market_prices" in existing_tables
        ):
            cutoff_year = datetime.now().year - int(max_price_age_years)
            cutoff_date = f"{cutoff_year}-01-01"
            try:
                res_age = conn.execute(
                    sqlt("DELETE FROM market_prices WHERE price_date < :cutoff"),
                    {"cutoff": cutoff_date},
                )
                pruned_aged = int(res_age.rowcount or 0)
            except Exception as ex:
                logger.warning("Errore durante pulizia market_prices datati: %s", ex)

    table_stats: List[Dict[str, Any]] = []
    total_rows = 0
    estimated_total_bytes = 0

    with engine.connect() as conn:
        for tbl in sorted(TABLE_PK_MAP.keys()):
            if tbl not in existing_tables:
                continue
            try:
                cnt = int(conn.execute(sqlt(f"SELECT COUNT(*) FROM {tbl}")).scalar() or 0)
            except Exception:
                cnt = 0
            row_weight = ESTIMATED_BYTES_PER_ROW.get(tbl, 250)
            est_bytes = cnt * row_weight
            total_rows += cnt
            estimated_total_bytes += est_bytes
            table_stats.append(
                {
                    "table": tbl,
                    "rows": cnt,
                    "estimated_mb": round(est_bytes / (1024 * 1024), 3),
                }
            )

        # Base catalog/index overhead (~4.5 MB on Postgres, ~0.5 MB on SQLite)
        exact_db_mb: Optional[float] = None
        if is_postgres:
            try:
                raw_bytes = conn.execute(sqlt("SELECT pg_database_size(current_database())")).scalar()
                if raw_bytes:
                    exact_db_mb = round(float(raw_bytes) / (1024 * 1024), 2)
            except Exception:
                pass

    estimated_mb = round((estimated_total_bytes / (1024 * 1024)) + 1.2, 2)
    used_mb = exact_db_mb if exact_db_mb is not None else estimated_mb
    usage_pct = round(min(100.0, (used_mb / SUPABASE_FREE_TIER_DB_MB) * 100.0), 2)
    remaining_mb = round(max(0.0, SUPABASE_FREE_TIER_DB_MB - used_mb), 2)

    if usage_pct < 50.0:
        status_tier = "OPTIMAL"
    elif usage_pct < 75.0:
        status_tier = "MODERATE"
    elif usage_pct < 90.0:
        status_tier = "WARNING"
    else:
        status_tier = "CRITICAL"

    return {
        "used_mb": used_mb,
        "estimated_data_mb": estimated_mb,
        "exact_pg_mb": exact_db_mb,
        "quota_mb": SUPABASE_FREE_TIER_DB_MB,
        "usage_pct": usage_pct,
        "remaining_mb": remaining_mb,
        "status_tier": status_tier,
        "total_rows": total_rows,
        "pruned_orphan_rows": pruned_orphans,
        "pruned_aged_rows": pruned_aged,
        "tables": sorted(table_stats, key=lambda x: x["rows"], reverse=True),
    }


# ── 5. 1-Click Local SQLite -> Supabase Cloud Migration ──────


def migrate_local_to_supabase(
    sqlite_path: str = "data/argus_local.db",
    target_db_url: Optional[str] = None,
    target_engine: Optional[Engine] = None,
    include_market_prices: bool = False,
) -> Dict[str, Any]:
    """
    Esegue il travaso completo 1-click dal database locale SQLite (`data/argus_local.db`)
    al database cloud Supabase PostgreSQL (o ad un `target_engine` specificato).
    - Inizializza tutte le tabelle sul target.
    - Trasferisce tutti i dati Wealth, Risk e Dichiarazioni/Certificazioni Fiscali.
    - Riallinea le sequenze SERIAL di PostgreSQL (`reset_postgres_sequences`).
    """
    from core.fetcher import get_engine
    from core.wealth.wealth_db import sync_wealth_tables_between_engines

    if not Path(sqlite_path).exists():
        raise FileNotFoundError(f"Database SQLite sorgente non trovato: {sqlite_path}")

    src_engine = get_engine(offline=True, sqlite_path=sqlite_path)
    owns_target = False
    tgt_engine = target_engine

    try:
        if tgt_engine is None:
            tgt_engine = create_supabase_engine(target_db_url)
            owns_target = True

        sync_results = sync_wealth_tables_between_engines(src_engine, tgt_engine)

        if include_market_prices:
            try:
                df_mp = pd.read_sql_table("market_prices", src_engine)
                if df_mp is not None and not df_mp.empty:
                    with tgt_engine.begin() as conn:
                        conn.execute(sqlt("DELETE FROM market_prices"))
                        df_mp.to_sql("market_prices", conn, if_exists="append", index=False, chunksize=2000)
                    sync_results["market_prices"] = len(df_mp)
            except Exception as ex:
                sync_results["market_prices"] = f"Skipped: {ex}"

        seq_synced = reset_postgres_sequences(tgt_engine)
        record_cloud_heartbeat(
            tgt_engine,
            source="sqlite_to_supabase_migration",
            details=f"Migrated {sum(v for v in sync_results.values() if isinstance(v, int))} rows",
        )

        total_migrated = sum(v for v in sync_results.values() if isinstance(v, int))
        return {
            "ok": True,
            "total_rows_migrated": total_migrated,
            "tables": sync_results,
            "sequences_reset": seq_synced,
        }
    finally:
        try:
            src_engine.dispose()
        except Exception:
            pass
        if owns_target and tgt_engine is not None:
            try:
                tgt_engine.dispose()
            except Exception:
                pass


# ── 6. Supabase Storage Private Vault (REST API) ─────────────


def upload_tax_pdf_to_supabase_storage(
    file_bytes: bytes,
    filename: str,
    tax_year: int,
    doc_type: str = "730",
    user_id: str = "owner",
) -> Dict[str, Any]:
    """
    Carica un documento fiscale PDF nel bucket privato Supabase Storage (`tax-documents`)
    tramite le REST API ufficiali di Supabase (zero dipendenze esterne pesanti).
    """
    cfg = get_supabase_config()
    supa_url = cfg.get("supabase_url", "")
    api_key = cfg.get("supabase_service_key") or cfg.get("supabase_anon_key", "")
    bucket = cfg.get("storage_bucket", "tax-documents")

    if not supa_url or not api_key:
        return {
            "ok": False,
            "storage_path": None,
            "error": "SUPABASE_URL o SUPABASE_ANON_KEY non configurati per Supabase Storage.",
        }

    safe_name = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in str(filename))
    object_path = f"{user_id}/{int(tax_year)}/{doc_type}_{safe_name}"
    endpoint = f"{supa_url}/storage/v1/object/{bucket}/{urllib.parse.quote(object_path)}"

    req = urllib.request.Request(
        endpoint,
        data=file_bytes,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": "application/pdf",
            "x-upsert": "true",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
            return {
                "ok": True,
                "bucket": bucket,
                "storage_path": object_path,
                "response": body,
                "error": None,
            }
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="ignore")
        return {
            "ok": False,
            "bucket": bucket,
            "storage_path": object_path,
            "error": f"HTTP {he.code}: {err_body}",
        }
    except Exception as ex:
        return {
            "ok": False,
            "bucket": bucket,
            "storage_path": object_path,
            "error": str(ex),
        }


# ── 7. Multi-User Authentication & Guest Demo Manager ────────


class SupabaseAuthManager:
    """
    Gestisce l'autenticazione per il deployment online a costo zero:
    1. Autenticazione nativa Supabase Auth (GoTrue REST API Email/Password)
    2. Autenticazione Single-Owner tramite `ARGUS_ADMIN_PASSWORD` (HMAC constant-time)
    3. Modalità Ospite / Recruiter Demo 1-Click (isolata su SQLite/Demo, zero accesso ai dati reali)
    """

    @staticmethod
    def authenticate_with_supabase_rest(email: str, password: str) -> Dict[str, Any]:
        """Autentica un utente tramite l'endpoint GoTrue `/auth/v1/token?grant_type=password`."""
        cfg = get_supabase_config()
        supa_url = cfg.get("supabase_url", "")
        anon_key = cfg.get("supabase_anon_key", "")
        if not supa_url or not anon_key:
            return {"ok": False, "error": "SUPABASE_URL e SUPABASE_ANON_KEY non configurati."}

        endpoint = f"{supa_url}/auth/v1/token?grant_type=password"
        payload = json.dumps({"email": email.strip(), "password": password}).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "apikey": anon_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                user_obj = data.get("user", {})
                return {
                    "ok": True,
                    "user_id": user_obj.get("id", email),
                    "email": user_obj.get("email", email),
                    "access_token": data.get("access_token"),
                    "role": "owner",
                    "error": None,
                }
        except urllib.error.HTTPError as he:
            err_json = {}
            try:
                err_json = json.loads(he.read().decode("utf-8", errors="ignore"))
            except Exception:
                pass
            msg = err_json.get("error_description") or err_json.get("msg") or f"HTTP {he.code}"
            return {"ok": False, "error": msg}
        except Exception as ex:
            return {"ok": False, "error": str(ex)}

    @staticmethod
    def verify_admin_password(input_password: str, configured_secret: Optional[str] = None) -> bool:
        """Verifica in tempo costante la password amministratore (`ARGUS_ADMIN_PASSWORD`)."""
        secret = configured_secret if configured_secret is not None else get_supabase_config().get("admin_password", "")
        if not secret or not input_password:
            return False
        a = hashlib.sha256(input_password.encode("utf-8")).digest()
        b = hashlib.sha256(str(secret).encode("utf-8")).digest()
        return hmac.compare_digest(a, b)


def render_cloud_auth_gate() -> bool:
    """
    Se `ARGUS_REQUIRE_LOGIN=true`, mostra un gate istituzionale prima di accedere
    alla piattaforma online, offrendo:
    - Login Titolare (Supabase Auth o Admin Password) per accedere al DB Cloud reale.
    - Accesso 1-Click Ospite / Recruiter in ambiente Demo isolato.
    Restituisce True se l'utente è autorizzato a proseguire.
    """
    import streamlit as st

    cfg = get_supabase_config()
    if not cfg.get("require_login", False):
        return True

    if st.session_state.get("argus_auth_verified", False):
        return True

    st.markdown(
        """
        <div style="max-width:540px;margin:48px auto 20px auto;padding:28px 32px;
                    background:linear-gradient(145deg,rgba(15,23,42,0.95),rgba(30,41,59,0.90));
                    border:1px solid rgba(99,102,241,0.30);border-radius:16px;
                    box-shadow:0 20px 50px rgba(0,0,0,0.45);text-align:center;">
            <div style="font-size:0.75rem;letter-spacing:0.14em;text-transform:uppercase;
                        color:#818cf8;font-weight:700;margin-bottom:6px;">
                ARGUS CLOUD PLATFORM • ZERO-COST EDITION
            </div>
            <h2 style="margin:0 0 8px 0;color:#f8fafc;font-size:1.55rem;font-weight:800;">
                🏛️ Accesso Istituzionale & Family Office
            </h2>
            <p style="color:#94a3b8;font-size:0.88rem;line-height:1.5;margin:0;">
                Questa istanza online è protetta. Accedi con le tue credenziali Supabase/Admin
                per connetterti al tuo patrimonio reale, oppure esplora la piattaforma in
                <b>Modalità Demo Ospite</b> isolata.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([1, 2.2, 1])
    with col_c:
        tab_owner, tab_guest = st.tabs(["🔐 Accesso Titolare (Cloud DB)", "🚀 Esplora Demo Ospite (1-Click)"])
        with tab_owner:
            email_in = st.text_input("Email (opzionale se usi Admin Password)", key="auth_gate_email")
            pass_in = st.text_input("Password", type="password", key="auth_gate_pass")
            if st.button("Accedi al Vault Cloud", type="primary", use_container_width=True, key="btn_auth_owner"):
                if cfg.get("admin_password") and SupabaseAuthManager.verify_admin_password(pass_in):
                    st.session_state.argus_auth_verified = True
                    st.session_state.argus_auth_role = "owner"
                    st.session_state.argus_auth_user = email_in or "owner@argus.cloud"
                    st.rerun()
                elif cfg.get("has_rest_api") and email_in:
                    res = SupabaseAuthManager.authenticate_with_supabase_rest(email_in, pass_in)
                    if res.get("ok"):
                        st.session_state.argus_auth_verified = True
                        st.session_state.argus_auth_role = "owner"
                        st.session_state.argus_auth_user = res.get("email", email_in)
                        st.rerun()
                    else:
                        st.error(f"Autenticazione fallita: {res.get('error')}")
                else:
                    st.error("Credenziali non valide.")

        with tab_guest:
            st.info(
                "La **Modalità Demo Ospite** carica un ambiente sandbox locale/dimostrativo "
                "senza leggere né modificare il database privato Supabase del titolare."
            )
            if st.button("🚀 Entra in Modalità Demo Ospite", use_container_width=True, key="btn_auth_guest"):
                st.session_state.argus_auth_verified = True
                st.session_state.argus_auth_role = "guest_demo"
                st.session_state.argus_auth_user = "guest@demo.local"
                st.session_state.offline_mode = True
                st.rerun()

    return False


def render_supabase_cloud_panel(engine: Optional[Engine] = None) -> None:
    """
    Renderizza il pannello di controllo Cloud Supabase (€0/mese) all'interno
    della finestra Impostazioni di ARGUS (`core/sidebar.py`).
    """
    import streamlit as st

    cfg = get_supabase_config()
    is_pg_active = (
        engine is not None
        and getattr(engine, "dialect", None) is not None
        and engine.dialect.name == "postgresql"
    )

    st.markdown(
        """
        <div style="padding:10px 14px;border-radius:10px;
                    background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(59,130,246,0.10));
                    border:1px solid rgba(16,185,129,0.28);margin-bottom:10px;">
            <div style="font-size:0.78rem;font-weight:700;color:#34d399;letter-spacing:0.04em;">
                ☁️ SUPABASE CLOUD & DEPLOYMENT ZERO-COST (€0/MESE)
            </div>
            <div style="font-size:0.74rem;color:#cbd5e1;margin-top:2px;">
                PostgreSQL 15+ gestito (500 MB Free Tier) • Supavisor Connection Pooler • Backup & Migrazione 1-Click
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    curr_supa_url = st.session_state.get("supabase_db_url", cfg.get("db_url", ""))
    new_supa_url = st.text_input(
        "Supabase PostgreSQL Connection URI (`SUPABASE_DB_URL`)",
        value=curr_supa_url,
        type="password",
        key="sb_supabase_db_url_input",
        placeholder="postgresql://postgres.[project-ref]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
        help="Incolla la stringa URI da Supabase Dashboard -> Connect -> Transaction/Session Pooler.",
    ).strip()

    if new_supa_url != curr_supa_url:
        st.session_state.supabase_db_url = normalize_supabase_db_url(new_supa_url)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔍 Testa Connessione Cloud", use_container_width=True, key="sb_btn_test_supa"):
            diag = test_supabase_connection(new_supa_url or cfg.get("db_url"))
            if diag["ok"]:
                st.success(
                    f"✅ Connesso a **{diag['current_db']}** ({diag['pg_version']}) "
                    f"in **{diag['latency_ms']} ms** — {diag['tables_count']} tabelle attive."
                )
            else:
                st.error(f"❌ Connessione fallita: {diag['error']}")

    with col_b2:
        if st.button(
            "🚀 Migra SQLite Locale ➔ Supabase",
            use_container_width=True,
            key="sb_btn_migrate_supa",
            disabled=not bool(new_supa_url or cfg.get("db_url")),
            help="Copia tutti i tuoi conti, movimenti, asset, obiettivi e dichiarazioni fiscali dal DB locale SQLite a Supabase.",
        ):
            try:
                with st.spinner("Migrazione crittografata TLS verso Supabase in corso..."):
                    mig_res = migrate_local_to_supabase(
                        sqlite_path="data/argus_local.db",
                        target_db_url=new_supa_url or cfg.get("db_url"),
                    )
                st.success(
                    f"🎉 Migrazione completata! **{mig_res['total_rows_migrated']}** record trasferiti su Supabase."
                )
            except Exception as ex:
                st.error(f"Errore durante la migrazione verso Supabase: {ex}")

    if engine is not None:
        try:
            quota = optimize_supabase_storage_footprint(engine, prune_orphan_prices=False)
            dialect_lbl = "PostgreSQL (Supabase Cloud)" if is_pg_active else engine.dialect.name.upper()
            st.caption(
                f"📊 **Quota Storage Stimata ({dialect_lbl})**: `{quota['used_mb']:.2f} MB` / "
                f"`{quota['quota_mb']:.0f} MB` ({quota['usage_pct']:.1f}%) — "
                f"**{quota['total_rows']:,}** righe totali (`{quota['status_tier']}`)"
            )
            st.progress(min(1.0, max(0.01, quota["usage_pct"] / 100.0)))

            if st.button(
                "🧹 Ottimizza Spazio Free Tier (Pulisci Prezzi Orfani)",
                key="sb_btn_prune_supa",
                use_container_width=True,
            ):
                opt_res = optimize_supabase_storage_footprint(
                    engine, prune_orphan_prices=True, max_price_age_years=10
                )
                st.success(
                    f"Ottimizzazione completata: rimossi {opt_res['pruned_orphan_rows']} prezzi orfani "
                    f"e {opt_res['pruned_aged_rows']} prezzi >10 anni. Spazio attuale: {opt_res['used_mb']:.2f} MB."
                )
        except Exception:
            pass

    schema_sql = generate_supabase_schema_sql(include_rls=True, include_storage=True)
    st.download_button(
        label="📜 Scarica Schema SQL Supabase (`supabase_schema.sql`)",
        data=schema_sql.encode("utf-8"),
        file_name="supabase_schema.sql",
        mime="text/sql",
        use_container_width=True,
        key="sb_dl_supabase_schema",
        help="Script DDL pronto da incollare nel SQL Editor di Supabase (include 19 tabelle, indici B-Tree, Storage Bucket e RLS).",
    )
