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

# Default Project Reference & Supavisor Pooler Host (AWS EU-West-1 Ireland)
DEFAULT_SUPABASE_PROJECT_REF = "qsexxzbhtocxvyaijngb"
DEFAULT_SUPABASE_POOLER_HOST = "aws-0-eu-west-1.pooler.supabase.com"
DEFAULT_SUPABASE_POOLER_PORT = 6543
DEFAULT_SUPABASE_URL = f"https://{DEFAULT_SUPABASE_PROJECT_REF}.supabase.co"

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
    "argus_users": "user_id",
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
    "argus_users": 240,
}

# Process-level warm connection pool cache for Supabase PostgreSQL engines
_SUPABASE_ENGINE_CACHE: Dict[str, Engine] = {}


# ── 1. URL Normalization & Secrets Discovery ──────────────────


def build_supabase_db_url(
    project_ref: str = DEFAULT_SUPABASE_PROJECT_REF,
    db_password: str = "",
    pooler_host: str = DEFAULT_SUPABASE_POOLER_HOST,
    port: int = DEFAULT_SUPABASE_POOLER_PORT,
    db_name: str = "postgres",
) -> str:
    """
    Costruisce automaticamente l'URI PostgreSQL Supavisor per un progetto Supabase
    a partire dal `project_ref` (es. `qsexxzbhtocxvyaijngb`) e dalla password DB,
    codificando in modo sicuro eventuali caratteri speciali nella password.
    """
    ref = (project_ref or DEFAULT_SUPABASE_PROJECT_REF).strip()
    pwd = (db_password or "").strip()
    if not ref or not pwd:
        return ""
    host = (pooler_host or DEFAULT_SUPABASE_POOLER_HOST).strip()
    encoded_pwd = urllib.parse.quote_plus(pwd)
    raw = f"postgresql+psycopg2://postgres.{ref}:{encoded_pwd}@{host}:{int(port)}/{db_name}?sslmode=require"
    return normalize_supabase_db_url(raw)


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


def persist_supabase_credentials_to_env(
    db_password: Optional[str] = None,
    db_url: Optional[str] = None,
    project_ref: Optional[str] = None,
    pooler_host: Optional[str] = None,
) -> bool:
    """
    Salva in modo atomico e persistente le credenziali Supabase inserite dall'utente
    in `os.environ` e nel file `.env` locale (gitignored), così che sopravvivano ai
    riavvii dell'app, al cambio pagina e agli script di sincronizzazione.
    """
    try:
        ref = (project_ref or os.getenv("SUPABASE_PROJECT_REF") or DEFAULT_SUPABASE_PROJECT_REF).strip()
        host = (pooler_host or os.getenv("SUPABASE_POOLER_HOST") or DEFAULT_SUPABASE_POOLER_HOST).strip()
        pwd = (db_password or "").strip()
        url = normalize_supabase_db_url(db_url) if db_url else ""

        if pwd and not url:
            url = build_supabase_db_url(project_ref=ref, db_password=pwd, pooler_host=host)

        if pwd:
            os.environ["SUPABASE_DB_PASSWORD"] = pwd
        if url:
            os.environ["SUPABASE_DB_URL"] = url
        if ref:
            os.environ["SUPABASE_PROJECT_REF"] = ref
            os.environ["SUPABASE_URL"] = f"https://{ref}.supabase.co"
        if host:
            os.environ["SUPABASE_POOLER_HOST"] = host

        env_path = Path(__file__).resolve().parent.parent / ".env"
        lines: List[str] = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8", errors="ignore").splitlines()

        updates: Dict[str, str] = {
            "SUPABASE_PROJECT_REF": ref,
            "SUPABASE_POOLER_HOST": host,
            "SUPABASE_URL": f"https://{ref}.supabase.co",
        }
        if pwd:
            updates["SUPABASE_DB_PASSWORD"] = pwd
        if url:
            updates["SUPABASE_DB_URL"] = url

        seen_keys = set()
        new_lines: List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in updates:
                    new_lines.append(f"{k}={updates[k]}")
                    seen_keys.add(k)
                    continue
            new_lines.append(line)

        for k, v in updates.items():
            if k not in seen_keys:
                new_lines.append(f"{k}={v}")

        env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
        return True
    except Exception as ex:
        logger.debug("persist_supabase_credentials_to_env warning: %s", ex)
        return False


def harvest_active_streamlit_sessions_for_supabase() -> Dict[str, str]:
    """
    Ispeziona tutte le sessioni Streamlit attive nel processo corrente per recuperare
    e persistere automaticamente su `.env` eventuali password o URI Supabase inseriti
    dall'utente nella UI (anche prima della chiusura della finestra modale).
    """
    found: Dict[str, str] = {}
    try:
        from streamlit.runtime import get_instance

        rt = get_instance()
        if rt is None or not hasattr(rt, "_session_mgr"):
            return found

        for s_info in rt._session_mgr.list_active_sessions():
            sess = getattr(s_info, "session", s_info)
            ss = getattr(sess, "_session_state", None)
            if ss is None:
                continue
            f_state = getattr(ss, "filtered_state", {}) or {}
            pwd = str(
                f_state.get("supabase_db_password")
                or f_state.get("sb_supabase_db_pass_input")
                or ""
            ).strip()
            url = str(
                f_state.get("supabase_db_url")
                or f_state.get("sb_supabase_db_url_input")
                or ""
            ).strip()
            # Fallback if user typed Supabase password into generic DB password field when not 'root'
            if not pwd and not url:
                alt_pw = str(f_state.get("sb_db_pass") or f_state.get("db_pass") or "").strip()
                if alt_pw and alt_pw != "root":
                    pwd = alt_pw

            if pwd or url:
                found["db_password"] = pwd
                found["db_url"] = url
                persist_supabase_credentials_to_env(db_password=pwd, db_url=url)
                break
    except Exception:
        pass
    return found


def _read_secret_or_env(key: str, default: str = "") -> str:
    """Legge una configurazione prioritariamente da os.environ / .env e poi da st.secrets."""
    val = os.getenv(key)
    if val is not None and str(val).strip() != "":
        return str(val).strip()

    try:
        from dotenv import dotenv_values

        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            d_vals = dotenv_values(env_path)
            if key in d_vals and d_vals[key] is not None and str(d_vals[key]).strip() != "":
                val_disk = str(d_vals[key]).strip()
                os.environ[key] = val_disk
                return val_disk
    except Exception:
        pass

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
    o `.streamlit/secrets.toml`. Se `SUPABASE_DB_URL` non è specificato ma è presente
    `SUPABASE_DB_PASSWORD`, assembla automaticamente l'URI Supavisor per il progetto
    configurato (default: `qsexxzbhtocxvyaijngb` su `aws-0-eu-west-1.pooler.supabase.com`).
    """
    session_db_url = ""
    session_db_pass = ""
    session_supa_url = ""
    session_anon_key = ""
    try:
        import streamlit as st

        session_db_url = str(
            st.session_state.get("supabase_db_url")
            or st.session_state.get("sb_supabase_db_url_input")
            or ""
        ).strip()
        session_db_pass = str(
            st.session_state.get("supabase_db_password")
            or st.session_state.get("sb_supabase_db_pass_input")
            or ""
        ).strip()
        session_supa_url = str(st.session_state.get("supabase_url", "") or "").strip()
        session_anon_key = str(st.session_state.get("supabase_anon_key", "") or "").strip()
    except Exception:
        pass

    if not session_db_pass and not session_db_url and not os.getenv("SUPABASE_DB_PASSWORD") and not os.getenv("SUPABASE_DB_URL"):
        harvested = harvest_active_streamlit_sessions_for_supabase()
        session_db_pass = harvested.get("db_password", "")
        session_db_url = harvested.get("db_url", "")

    project_ref = _read_secret_or_env("SUPABASE_PROJECT_REF", DEFAULT_SUPABASE_PROJECT_REF)
    pooler_host = _read_secret_or_env("SUPABASE_POOLER_HOST", DEFAULT_SUPABASE_POOLER_HOST)
    db_password = session_db_pass or _read_secret_or_env("SUPABASE_DB_PASSWORD")

    if session_db_pass or session_db_url:
        persist_supabase_credentials_to_env(
            db_password=session_db_pass,
            db_url=session_db_url,
            project_ref=project_ref,
            pooler_host=pooler_host,
        )

    raw_db_url = (
        session_db_url
        or _read_secret_or_env("SUPABASE_DB_URL")
        or _read_secret_or_env("DATABASE_URL")
    )
    # Only treat DATABASE_URL as Supabase/Postgres if it starts with postgres
    if raw_db_url and not raw_db_url.lower().startswith("postgres"):
        raw_db_url = ""

    if not raw_db_url and db_password and project_ref:
        raw_db_url = build_supabase_db_url(
            project_ref=project_ref,
            db_password=db_password,
            pooler_host=pooler_host,
        )

    normalized_db_url = normalize_supabase_db_url(raw_db_url)
    default_api_url = f"https://{project_ref}.supabase.co" if project_ref else DEFAULT_SUPABASE_URL
    supabase_url = (
        session_supa_url or _read_secret_or_env("SUPABASE_URL", default_api_url)
    ).rstrip("/")
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
        "project_ref": project_ref,
        "pooler_host": pooler_host,
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


def create_supabase_engine(
    db_url: Optional[str] = None,
    connect_timeout: int = 8,
    use_cache: bool = True,
) -> Engine:
    """
    Crea (o restituisce dal pool warm in-process) un SQLAlchemy Engine ottimizzato
    per Supabase PostgreSQL (compatibile con Supavisor Transaction Pooler su porta 6543
    e Session Pooler su porta 5432).
    """
    cfg = get_supabase_config()
    target_url = normalize_supabase_db_url(db_url or cfg.get("db_url", ""))
    if not target_url:
        raise ValueError("Nessun SUPABASE_DB_URL configurato.")

    if use_cache and target_url in _SUPABASE_ENGINE_CACHE:
        return _SUPABASE_ENGINE_CACHE[target_url]

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
    if use_cache:
        _SUPABASE_ENGINE_CACHE[target_url] = engine
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
        eng = create_supabase_engine(normalized, connect_timeout=6, use_cache=True)
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
        if normalized in _SUPABASE_ENGINE_CACHE:
            bad_eng = _SUPABASE_ENGINE_CACHE.pop(normalized, None)
            if bad_eng is not None:
                try:
                    bad_eng.dispose()
                except Exception:
                    pass
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "pg_version": None,
            "current_db": None,
            "tables_count": 0,
            "masked_url": mask_db_url(normalized),
            "error": str(ex),
        }


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
        "-- 4. CLOUD HEARTBEAT & MULTI-USER AUTHENTICATION TABLES",
        """CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat (
    id SERIAL PRIMARY KEY,
    ping_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(80) NOT NULL DEFAULT 'github_actions_keepalive',
    status VARCHAR(40) NOT NULL DEFAULT 'OK',
    details TEXT
);""",
        """CREATE TABLE IF NOT EXISTS argus_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(160),
    display_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user',
    custom_db_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        "CREATE INDEX IF NOT EXISTS idx_argus_users_uname ON argus_users(username);",
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
                "ALTER TABLE argus_users ENABLE ROW LEVEL SECURITY;",
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
    tgt_engine = target_engine

    try:
        if tgt_engine is None:
            tgt_engine = create_supabase_engine(target_db_url, use_cache=True)

        SupabaseAuthManager.ensure_users_table(tgt_engine)
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


# ── 7. Multi-User Authentication, Data Isolation & Guest Demo ──


class SupabaseAuthManager:
    """
    Gestisce l'autenticazione Multi-Utente e l'isolamento dei dati sensibili su ARGUS:
    1. Multi-Utente Nativo (`argus_users` con PBKDF2-HMAC-SHA256 120.000 iterazioni):
       - Supporta 3, 4 o più utenti distinti (`role='owner'` oppure `role='user'`).
       - Isolamento Multi-Tenant sullo stesso DB Supabase (ogni utente vede esclusivamente
         i propri `wealth_profiles`, conti, movimenti, asset e `portfolios` Risk filtrati per `owner`).
       - Supporto opzionale BYOD (`custom_db_url`): ogni utente può anche collegare un
         proprio database Supabase gratuito dedicato (500 MB personali).
    2. Autenticazione nativa Supabase Auth (GoTrue REST API Email/Password).
    3. Autenticazione Master Owner tramite `ARGUS_ADMIN_PASSWORD` o `SUPABASE_DB_PASSWORD`.
    4. Modalità Ospite / Recruiter Demo 1-Click (isolata su sandbox locale `data/argus_demo_sandbox.db`,
       zero accesso ai dati reali di alcun utente).
    """

    @staticmethod
    def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
        """Calcola l'hash PBKDF2-HMAC-SHA256 (120.000 iterazioni) con salt crittografico."""
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return f"pbkdf2_sha256$120000${salt.hex()}${dk.hex()}"

    @staticmethod
    def verify_password_hash(password: str, stored_hash: str) -> bool:
        """Verifica in tempo costante una password rispetto a un hash PBKDF2 salvato."""
        if not password or not stored_hash:
            return False
        try:
            parts = str(stored_hash).split("$")
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_hex = parts[3]
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(dk.hex(), expected_hex)
        except Exception:
            return False

    @staticmethod
    def ensure_users_table(engine: Engine) -> None:
        """Crea la tabella `argus_users` in modo idempotente su PostgreSQL, SQLite o MySQL."""
        if engine is None:
            return
        dialect = getattr(getattr(engine, "dialect", None), "name", "sqlite")
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        email TEXT,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        custom_db_url TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            elif dialect == "postgresql":
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_users (
                        user_id SERIAL PRIMARY KEY,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(160),
                        display_name VARCHAR(120) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(30) NOT NULL DEFAULT 'user',
                        custom_db_url TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
            else:
                conn.execute(
                    sqlt("""
                    CREATE TABLE IF NOT EXISTS argus_users (
                        user_id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(80) NOT NULL UNIQUE,
                        email VARCHAR(160),
                        display_name VARCHAR(120) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(30) NOT NULL DEFAULT 'user',
                        custom_db_url TEXT,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                )

    @classmethod
    def create_or_update_user(
        cls,
        engine: Engine,
        username: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        custom_db_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra o aggiorna un utente in `argus_users` e, se `role == 'user'`,
        inizializza automaticamente il suo profilo patrimoniale isolato in `wealth_profiles`.
        """
        uname = (username or "").strip().lower()
        if not uname or len(uname) < 2:
            return {"ok": False, "error": "Username troppo corto (minimo 2 caratteri)."}
        if not password or len(password) < 4:
            return {"ok": False, "error": "La password deve contenere almeno 4 caratteri."}

        cls.ensure_users_table(engine)
        pwd_hash = cls.hash_password(password)
        disp = (display_name or username).strip()
        clean_role = role if role in ("owner", "user") else "user"
        clean_custom_db = normalize_supabase_db_url(custom_db_url) if custom_db_url else ""

        with engine.begin() as conn:
            existing = conn.execute(
                sqlt("SELECT user_id FROM argus_users WHERE LOWER(username) = :u"),
                {"u": uname},
            ).scalar()
            if existing:
                conn.execute(
                    sqlt("""
                        UPDATE argus_users
                        SET display_name = :d,
                            email = :e,
                            password_hash = :p,
                            role = :r,
                            custom_db_url = :c,
                            is_active = 1
                        WHERE user_id = :uid
                    """),
                    {
                        "d": disp,
                        "e": (email or "").strip(),
                        "p": pwd_hash,
                        "r": clean_role,
                        "c": clean_custom_db,
                        "uid": int(existing),
                    },
                )
            else:
                conn.execute(
                    sqlt("""
                        INSERT INTO argus_users (username, email, display_name, password_hash, role, custom_db_url, is_active)
                        VALUES (:u, :e, :d, :p, :r, :c, 1)
                    """),
                    {
                        "u": uname,
                        "e": (email or "").strip(),
                        "d": disp,
                        "p": pwd_hash,
                        "r": clean_role,
                        "c": clean_custom_db,
                    },
                )

        # Ensure standard user has an isolated wealth_profile if using shared DB
        if clean_role == "user" and not clean_custom_db:
            try:
                from core.wealth.wealth_db import create_wealth_portfolio, init_wealth_db

                init_wealth_db(engine)
                create_wealth_portfolio(
                    engine,
                    name=f"Patrimonio {disp}",
                    description=f"Spazio patrimoniale privato di {disp} (@{uname})",
                    owner=uname,
                    base_currency="EUR",
                )
            except Exception as ex:
                logger.debug("Auto-create wealth profile for %s skipped: %s", uname, ex)

        return {
            "ok": True,
            "username": uname,
            "display_name": disp,
            "role": clean_role,
            "has_custom_db": bool(clean_custom_db),
        }

    @classmethod
    def list_users(cls, engine: Engine) -> List[Dict[str, Any]]:
        """Restituisce l'elenco degli utenti registrati su `argus_users`."""
        if engine is None:
            return []
        try:
            cls.ensure_users_table(engine)
            with engine.connect() as conn:
                rows = (
                    conn.execute(
                        sqlt("""
                        SELECT user_id, username, email, display_name, role, custom_db_url, is_active, created_at
                        FROM argus_users
                        ORDER BY CASE WHEN role = 'owner' THEN 0 ELSE 1 END, username ASC
                    """)
                    )
                    .mappings()
                    .fetchall()
                )
                return [
                    {
                        "user_id": int(r["user_id"]),
                        "username": str(r["username"]),
                        "email": str(r["email"] or ""),
                        "display_name": str(r["display_name"]),
                        "role": str(r["role"]),
                        "custom_db_url": str(r["custom_db_url"] or ""),
                        "masked_custom_db": mask_db_url(r["custom_db_url"]) if r["custom_db_url"] else "DB Condiviso (Isolato per Owner)",
                        "is_active": int(r["is_active"] or 0),
                        "created_at": str(r["created_at"] or ""),
                    }
                    for r in rows
                ]
        except Exception as ex:
            logger.debug("list_users warning: %s", ex)
            return []

    @classmethod
    def delete_user(cls, engine: Engine, username: str) -> bool:
        """Elimina un utente dalla tabella `argus_users`."""
        if engine is None or not username:
            return False
        try:
            cls.ensure_users_table(engine)
            with engine.begin() as conn:
                conn.execute(
                    sqlt("DELETE FROM argus_users WHERE LOWER(username) = LOWER(:u)"),
                    {"u": username.strip()},
                )
            return True
        except Exception:
            return False

    @classmethod
    def authenticate_user(
        cls,
        username_or_email: str,
        password: str,
        engine: Optional[Engine] = None,
    ) -> Dict[str, Any]:
        """
        Autentica un utente verificando nell'ordine:
        1. Tabella `argus_users` sul database attivo (Supabase PostgreSQL o SQLite).
        2. Credenziali Master Owner (`ARGUS_ADMIN_PASSWORD` o `SUPABASE_DB_PASSWORD`).
        3. Supabase Auth GoTrue REST API (se configurata).
        """
        ident = (username_or_email or "").strip().lower()
        pwd = password or ""
        if not pwd:
            return {"ok": False, "error": "Inserisci la password."}

        # 1. Check argus_users table
        target_eng = engine
        if target_eng is None:
            try:
                cfg = get_supabase_config()
                if cfg.get("is_configured"):
                    target_eng = create_supabase_engine(cfg["db_url"], use_cache=True)
            except Exception:
                target_eng = None

        if target_eng is not None and ident:
            try:
                cls.ensure_users_table(target_eng)
                with target_eng.connect() as conn:
                    row = (
                        conn.execute(
                            sqlt("""
                            SELECT user_id, username, email, display_name, password_hash, role, custom_db_url, is_active
                            FROM argus_users
                            WHERE LOWER(username) = :ident OR (email IS NOT NULL AND email != '' AND LOWER(email) = :ident)
                            LIMIT 1
                        """),
                            {"ident": ident},
                        )
                        .mappings()
                        .fetchone()
                    )
                if row:
                    if not int(row["is_active"] or 0):
                        return {"ok": False, "error": "Account utente disabilitato."}
                    if cls.verify_password_hash(pwd, str(row["password_hash"])):
                        return {
                            "ok": True,
                            "username": str(row["username"]),
                            "display_name": str(row["display_name"]),
                            "email": str(row["email"] or ""),
                            "role": str(row["role"] or "user"),
                            "custom_db_url": str(row["custom_db_url"] or ""),
                            "error": None,
                        }
                    return {"ok": False, "error": "Password non valida per questo utente."}
            except Exception as ex:
                logger.debug("argus_users auth lookup skipped: %s", ex)

        # 2. Check Master Owner password (ARGUS_ADMIN_PASSWORD or SUPABASE_DB_PASSWORD)
        cfg = get_supabase_config()
        supa_db_pwd = _read_secret_or_env("SUPABASE_DB_PASSWORD")
        is_owner_ident = ident in ("", "owner", "admin", "alessandro", "user", "owner@argus.cloud")
        if is_owner_ident:
            if cfg.get("admin_password") and cls.verify_admin_password(pwd, cfg["admin_password"]):
                return {
                    "ok": True,
                    "username": "user",
                    "display_name": "Alessandro (Titolare)",
                    "email": ident if "@" in ident else "owner@argus.cloud",
                    "role": "owner",
                    "custom_db_url": "",
                    "error": None,
                }
            if supa_db_pwd and cls.verify_admin_password(pwd, supa_db_pwd):
                return {
                    "ok": True,
                    "username": "user",
                    "display_name": "Alessandro (Titolare)",
                    "email": ident if "@" in ident else "owner@argus.cloud",
                    "role": "owner",
                    "custom_db_url": "",
                    "error": None,
                }

        # 3. Check Supabase GoTrue REST API if configured
        if cfg.get("has_rest_api") and "@" in ident:
            rest_res = cls.authenticate_with_supabase_rest(ident, pwd)
            if rest_res.get("ok"):
                return {
                    "ok": True,
                    "username": ident.split("@")[0],
                    "display_name": ident.split("@")[0].capitalize(),
                    "email": rest_res.get("email", ident),
                    "role": "owner",
                    "custom_db_url": "",
                    "error": None,
                }

        return {"ok": False, "error": "Credenziali non valide o utente non trovato."}

    @staticmethod
    def set_security_settings(require_login: bool, admin_password: Optional[str] = None) -> bool:
        """Salva in `.env` e `os.environ` le impostazioni del Login Gate di ARGUS."""
        try:
            req_str = "true" if require_login else "false"
            os.environ["ARGUS_REQUIRE_LOGIN"] = req_str
            if admin_password is not None and admin_password.strip():
                os.environ["ARGUS_ADMIN_PASSWORD"] = admin_password.strip()

            env_path = Path(__file__).resolve().parent.parent / ".env"
            lines = env_path.read_text(encoding="utf-8", errors="ignore").splitlines() if env_path.exists() else []
            updates = {"ARGUS_REQUIRE_LOGIN": req_str}
            if admin_password is not None and admin_password.strip():
                updates["ARGUS_ADMIN_PASSWORD"] = admin_password.strip()

            seen = set()
            new_lines = []
            for line in lines:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k in updates:
                        new_lines.append(f"{k}={updates[k]}")
                        seen.add(k)
                        continue
                new_lines.append(line)
            for k, v in updates.items():
                if k not in seen:
                    new_lines.append(f"{k}={v}")
            env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
            return True
        except Exception as ex:
            logger.debug("set_security_settings error: %s", ex)
            return False

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


def apply_authenticated_user_session(auth_res: Dict[str, Any]) -> None:
    """Applica il contesto dell'utente autenticato a `st.session_state` isolando cache e profili."""
    import streamlit as st

    st.session_state.argus_auth_verified = True
    st.session_state.argus_auth_role = auth_res.get("role", "user")
    st.session_state.argus_auth_user = auth_res.get("username", "user")
    st.session_state.argus_auth_display_name = auth_res.get("display_name", auth_res.get("username", "Utente"))
    custom_db = auth_res.get("custom_db_url", "")
    st.session_state.argus_user_custom_db_url = custom_db
    if auth_res.get("role") == "guest_demo":
        st.session_state.offline_mode = True
    else:
        st.session_state.offline_mode = False
    # Reset cached engines & active profile selection so the new user sees only their own profiles
    for k in ("engine", "db_engine", "active_wealth_portfolio_id", "active_wealth_profile_name", "portfolio_id"):
        st.session_state.pop(k, None)
    st.cache_data.clear()
    st.cache_resource.clear()


def logout_argus_user() -> None:
    """Effettua il logout sicuro dell'utente corrente e pulisce tutti i dati in RAM."""
    import streamlit as st

    for k in list(st.session_state.keys()):
        if k.startswith("argus_auth_") or k in (
            "argus_user_custom_db_url",
            "engine",
            "db_engine",
            "active_wealth_portfolio_id",
            "active_wealth_profile_name",
            "portfolio_id",
            "data_loaded",
            "positions_df",
            "returns_df",
        ):
            st.session_state.pop(k, None)
    st.cache_data.clear()
    st.cache_resource.clear()


def render_cloud_auth_gate() -> bool:
    """
    Se `ARGUS_REQUIRE_LOGIN=true`, mostra un gate istituzionale prima di accedere
    alla piattaforma online, offrendo:
    - Login Multi-Utente / Titolare (`argus_users` + Admin Password + Supabase Auth).
    - Registrazione Nuovo Utente (con spazio isolato o DB Supabase personale).
    - Accesso 1-Click Ospite / Recruiter in ambiente Demo Sandbox isolato.
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
        <div style="max-width:600px;margin:36px auto 18px auto;padding:28px 32px;
                    background:linear-gradient(145deg,rgba(15,23,42,0.96),rgba(30,41,59,0.92));
                    border:1px solid rgba(99,102,241,0.32);border-radius:16px;
                    box-shadow:0 20px 50px rgba(0,0,0,0.45);text-align:center;">
            <div style="font-size:0.75rem;letter-spacing:0.14em;text-transform:uppercase;
                        color:#818cf8;font-weight:700;margin-bottom:6px;">
                ARGUS CLOUD PLATFORM • MULTI-USER VAULT
            </div>
            <h2 style="margin:0 0 8px 0;color:#f8fafc;font-size:1.55rem;font-weight:800;">
                🏛️ Accesso Sicuro & Isolamento Patrimoniale
            </h2>
            <p style="color:#94a3b8;font-size:0.88rem;line-height:1.5;margin:0;">
                Ogni utente dispone di uno spazio patrimoniale crittograficamente isolato
                (o del proprio database Supabase dedicato). Nessun dato sensibile è condiviso.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_l, col_c, col_r = st.columns([0.8, 2.6, 0.8])
    with col_c:
        tab_login, tab_reg, tab_guest = st.tabs(
            [
                "🔐 Accedi (Utente / Owner)",
                "➕ Crea Account Utente",
                "🚀 Demo Ospite (Sandbox)",
            ]
        )
        with tab_login:
            user_in = st.text_input(
                "Username o Email (lascia vuoto o `owner` per accesso Titolare)",
                key="auth_gate_email",
                placeholder="es. alessandro, marco, sara...",
            )
            pass_in = st.text_input("Password", type="password", key="auth_gate_pass")
            if st.button("🔓 Accedi al tuo Spazio Privato", type="primary", use_container_width=True, key="btn_auth_owner"):
                res = SupabaseAuthManager.authenticate_user(user_in, pass_in)
                if res.get("ok"):
                    apply_authenticated_user_session(res)
                    st.rerun()
                else:
                    st.error(f"Autenticazione fallita: {res.get('error')}")

        with tab_reg:
            st.caption(
                "Crea un account personale isolato: vedrai esclusivamente i tuoi portafogli e conti, "
                "senza alcun accesso ai dati degli altri utenti."
            )
            reg_uname = st.text_input("Username univoco", key="auth_reg_uname", placeholder="es. marco")
            reg_disp = st.text_input("Nome visualizzato", key="auth_reg_disp", placeholder="es. Marco Rossi")
            reg_pass = st.text_input("Scegli una Password", type="password", key="auth_reg_pass")
            reg_custom_db = st.text_input(
                "URI Database Supabase Personale (Opzionale — BYOD)",
                type="password",
                key="auth_reg_db",
                placeholder="Lascia vuoto per usare il Cloud condiviso in modalità isolata",
            )
            if st.button("✨ Crea Account & Entra", type="primary", use_container_width=True, key="btn_auth_register"):
                try:
                    eng = create_supabase_engine(cfg["db_url"], use_cache=True) if cfg.get("is_configured") else None
                    if eng is None:
                        from core.fetcher import get_engine

                        eng = get_engine(offline=True)
                    c_res = SupabaseAuthManager.create_or_update_user(
                        engine=eng,
                        username=reg_uname,
                        password=reg_pass,
                        role="user",
                        display_name=reg_disp or reg_uname,
                        custom_db_url=reg_custom_db,
                    )
                    if c_res.get("ok"):
                        apply_authenticated_user_session(
                            {
                                "username": c_res["username"],
                                "display_name": c_res["display_name"],
                                "role": c_res["role"],
                                "custom_db_url": normalize_supabase_db_url(reg_custom_db) if reg_custom_db else "",
                            }
                        )
                        st.rerun()
                    else:
                        st.error(c_res.get("error", "Errore durante la registrazione."))
                except Exception as ex:
                    st.error(f"Errore registrazione: {ex}")

        with tab_guest:
            st.info(
                "La **Modalità Demo Ospite** avvia un database sandbox separato (`argus_demo_sandbox.db`) "
                "senza leggere né modificare il database privato Supabase di alcun utente."
            )
            if st.button("🚀 Entra in Modalità Demo Ospite", use_container_width=True, key="btn_auth_guest"):
                apply_authenticated_user_session(
                    {
                        "username": "guest_demo",
                        "display_name": "Ospite Demo (Sandbox)",
                        "role": "guest_demo",
                        "custom_db_url": "",
                    }
                )
                st.rerun()

    return False


def render_supabase_cloud_panel(engine: Optional[Engine] = None) -> None:
    """
    Renderizza il pannello di controllo Cloud Supabase (€0/mese) e la gestione
    Multi-Utente & Isolamento Dati all'interno delle Impostazioni di ARGUS.
    """
    import streamlit as st

    cfg = get_supabase_config()
    is_pg_active = (
        engine is not None
        and getattr(engine, "dialect", None) is not None
        and engine.dialect.name == "postgresql"
    )

    proj_ref = cfg.get("project_ref", DEFAULT_SUPABASE_PROJECT_REF)
    pooler_host = cfg.get("pooler_host", DEFAULT_SUPABASE_POOLER_HOST)

    st.markdown(
        f"""
        <div style="padding:10px 14px;border-radius:10px;
                    background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(59,130,246,0.10));
                    border:1px solid rgba(16,185,129,0.28);margin-bottom:10px;">
            <div style="font-size:0.78rem;font-weight:700;color:#34d399;letter-spacing:0.04em;">
                ☁️ SUPABASE CLOUD & DEPLOYMENT ZERO-COST (€0/MESE)
            </div>
            <div style="font-size:0.74rem;color:#cbd5e1;margin-top:2px;">
                Project Ref: <code>{proj_ref}</code> • Region Pooler: <code>{pooler_host}:6543</code> •
                Stato Engine Attivo: <b>{'🟢 PostgreSQL Cloud' if is_pg_active else '💾 Locale / Ibrido'}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    curr_db_pass = st.session_state.get("supabase_db_password", "") or _read_secret_or_env("SUPABASE_DB_PASSWORD")
    new_db_pass = st.text_input(
        f"🔑 Password Database Supabase (Progetto `{proj_ref}`)",
        value=curr_db_pass,
        type="password",
        key="sb_supabase_db_pass_input",
        placeholder="Inserisci solo la password del database Supabase...",
        help=(
            f"Costruisce in automatico l'URI Supavisor: "
            f"postgresql://postgres.{proj_ref}:[PASSWORD]@{pooler_host}:6543/postgres?sslmode=require"
        ),
    ).strip()

    if new_db_pass != curr_db_pass:
        st.session_state.supabase_db_password = new_db_pass
        if new_db_pass:
            built_url = build_supabase_db_url(
                project_ref=proj_ref,
                db_password=new_db_pass,
                pooler_host=pooler_host,
            )
            st.session_state.supabase_db_url = built_url
            persist_supabase_credentials_to_env(
                db_password=new_db_pass,
                db_url=built_url,
                project_ref=proj_ref,
                pooler_host=pooler_host,
            )

    curr_supa_url = st.session_state.get("supabase_db_url", cfg.get("db_url", ""))
    with st.expander("⚙️ URI PostgreSQL Completo (`SUPABASE_DB_URL` — Avanzato)", expanded=False):
        new_supa_url = st.text_input(
            "Supabase PostgreSQL Connection URI (`SUPABASE_DB_URL`)",
            value=curr_supa_url,
            type="password",
            key="sb_supabase_db_url_input",
            placeholder=f"postgresql://postgres.{proj_ref}:[password]@{pooler_host}:6543/postgres",
            help="Incolla la stringa URI da Supabase Dashboard -> Connect -> Transaction/Session Pooler.",
        ).strip()

        if new_supa_url != curr_supa_url:
            norm_url = normalize_supabase_db_url(new_supa_url)
            st.session_state.supabase_db_url = norm_url
            persist_supabase_credentials_to_env(db_url=norm_url, project_ref=proj_ref, pooler_host=pooler_host)

    active_target_url = (
        st.session_state.get("supabase_db_url")
        or new_supa_url
        or cfg.get("db_url")
    )

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🔍 Testa Connessione Cloud", use_container_width=True, key="sb_btn_test_supa"):
            diag = test_supabase_connection(active_target_url)
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
            disabled=not bool(active_target_url),
            help="Copia tutti i tuoi conti, movimenti, asset, obiettivi e dichiarazioni fiscali dal DB locale SQLite a Supabase.",
        ):
            try:
                with st.spinner("Migrazione crittografata TLS verso Supabase in corso..."):
                    mig_res = migrate_local_to_supabase(
                        sqlite_path="data/argus_local.db",
                        target_db_url=active_target_url,
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

    # ── MULTI-USER LOGIN & DATA ISOLATION PANEL ──────────────
    with st.expander("👥 Gestione Utenti, Login & Isolamento Dati (3–4+ Utenti)", expanded=False):
        st.markdown(
            "**Come funziona per 3 o 4 utenti:**\n"
            "1. **Modalità Multi-Tenant su Singolo Supabase (Consigliata, €0)**: tutti gli utenti accedono alla stessa app, "
            "ma ciascuno ha il proprio **Username e Password** (`argus_users`) e vede **esclusivamente** i propri portafogli e conti (`owner` isolato).\n"
            "2. **Modalità Database Dedicato per Utente (BYOD, €0)**: puoi assegnare a un utente un suo URI Supabase gratuito dedicato (500 MB personali) per isolamento fisico totale."
        )
        curr_req_login = cfg.get("require_login", False)
        new_req_login = st.toggle(
            "🔒 Richiedi Schermata di Login all'Avvio di ARGUS (`ARGUS_REQUIRE_LOGIN`)",
            value=curr_req_login,
            key="sb_toggle_require_login",
            help="Se attivo, chiunque apra l'app (in locale o online) deve autenticarsi con il proprio utente e password prima di vedere qualsiasi dato.",
        )
        if new_req_login != curr_req_login:
            SupabaseAuthManager.set_security_settings(require_login=new_req_login)
            if new_req_login and not st.session_state.get("argus_auth_verified"):
                st.session_state.argus_auth_verified = True
                st.session_state.argus_auth_role = "owner"
                st.session_state.argus_auth_user = "user"
                st.session_state.argus_auth_display_name = "Alessandro (Titolare)"
            st.success(f"Login all'avvio {'ATTIVATO 🔒' if new_req_login else 'DISATTIVATO 🔓'}.")

        active_u = st.session_state.get("argus_auth_display_name") or st.session_state.get("argus_auth_user") or "Alessandro (Titolare)"
        active_r = st.session_state.get("argus_auth_role", "owner")
        col_uinfo, col_ulogout = st.columns([2, 1])
        with col_uinfo:
            st.caption(f"👤 Sessione corrente: **{active_u}** (`ruolo: {active_r}`)")
        with col_ulogout:
            if st.button("🚪 Cambia Utente / Logout", key="sb_btn_logout_user", use_container_width=True):
                SupabaseAuthManager.set_security_settings(require_login=True)
                logout_argus_user()
                st.rerun()

        target_user_eng = engine
        if target_user_eng is None and active_target_url:
            try:
                target_user_eng = create_supabase_engine(active_target_url, use_cache=True)
            except Exception:
                target_user_eng = None

        if target_user_eng is not None:
            users_list = SupabaseAuthManager.list_users(target_user_eng)
            if users_list:
                st.dataframe(
                    pd.DataFrame(users_list)[["username", "display_name", "role", "masked_custom_db"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("Nessun utente secondario registrato. Crea qui sotto gli account per gli altri 3-4 utenti.")

            st.markdown("##### ➕ Aggiungi o Aggiorna Utente")
            cu1, cu2, cu3 = st.columns(3)
            with cu1:
                nu_name = st.text_input("Username", key="sb_nu_uname", placeholder="es. marco")
            with cu2:
                nu_disp = st.text_input("Nome Completo", key="sb_nu_disp", placeholder="es. Marco")
            with cu3:
                nu_role = st.selectbox(
                    "Ruolo & Visibilità",
                    ["user", "owner"],
                    format_func=lambda r: "Utente Isolato (Solo i suoi dati)" if r == "user" else "Owner / Admin (Tutti i profili)",
                    key="sb_nu_role",
                )
            cu4, cu5 = st.columns([1.2, 1.8])
            with cu4:
                nu_pass = st.text_input("Password Utente", type="password", key="sb_nu_pass")
            with cu5:
                nu_db = st.text_input(
                    "DB Supabase Dedicato (Opzionale)",
                    type="password",
                    key="sb_nu_db",
                    placeholder="Lascia vuoto per isolamento automatico sullo stesso DB",
                )
            if st.button("💾 Salva Utente & Crea Spazio Isolato", key="sb_btn_save_user", use_container_width=True):
                res_u = SupabaseAuthManager.create_or_update_user(
                    engine=target_user_eng,
                    username=nu_name,
                    password=nu_pass,
                    role=nu_role,
                    display_name=nu_disp or nu_name,
                    custom_db_url=nu_db,
                )
                if res_u.get("ok"):
                    st.success(
                        f"✅ Utente **@{res_u['username']}** ({res_u['display_name']}) configurato con spazio isolato!"
                    )
                    st.rerun()
                else:
                    st.error(res_u.get("error", "Errore creazione utente."))

    schema_sql = generate_supabase_schema_sql(include_rls=True, include_storage=True)
    st.download_button(
        label="📜 Scarica Schema SQL Supabase (`supabase_schema.sql`)",
        data=schema_sql.encode("utf-8"),
        file_name="supabase_schema.sql",
        mime="text/sql",
        use_container_width=True,
        key="sb_dl_supabase_schema",
        help="Script DDL pronto da incollare nel SQL Editor di Supabase (include 20 tabelle, indici B-Tree, Storage Bucket e RLS).",
    )
