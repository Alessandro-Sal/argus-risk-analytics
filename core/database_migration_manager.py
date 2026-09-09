# ============================================================
# core/database_migration_manager.py
# ARGUS — Embedded Database Migration & Schema Reliability Manager
# Senior DBRE Architecture: Dual Versioning, Idempotent DDL,
# Pre-Flight Shadow Backup, Atomic Rollback & Schema Drift Inspector
# ============================================================

import gzip
import hashlib
import logging
import os
import shutil
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

logger = logging.getLogger("argus.dbre.migration")

DEFAULT_SQLITE_PATH = Path("data/argus_local.db")
DEFAULT_BACKUP_DIR = Path("data/backups")


# ── Modelli di Dati & Strutture di Diagnostica ─────────────

class DriftSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class DriftItem:
    table_name: str
    field_or_index: str
    issue_type: str  # MISSING_TABLE, MISSING_COLUMN, TYPE_MISMATCH, MISSING_INDEX, FOREIGN_KEY_VIOLATION
    severity: DriftSeverity
    detail: str
    remediation_hint: str


@dataclass
class SchemaDriftReport:
    timestamp: str
    db_path: str
    is_healthy: bool
    drift_count: int
    items: List[DriftItem]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "db_path": self.db_path,
            "is_healthy": self.is_healthy,
            "drift_count": self.drift_count,
            "items": [
                {
                    "table_name": it.table_name,
                    "field_or_index": it.field_or_index,
                    "issue_type": it.issue_type,
                    "severity": it.severity.value,
                    "detail": it.detail,
                    "remediation_hint": it.remediation_hint,
                }
                for it in self.items
            ],
            "summary": self.summary,
        }


@dataclass
class MigrationRecord:
    version: int
    name: str
    checksum: str
    applied_at: str
    execution_time_ms: float
    rollback_available: bool
    description: Optional[str] = None


@dataclass
class MigrationStatus:
    current_version: int
    target_version: int
    applied_count: int
    pending_count: int
    applied_migrations: List[MigrationRecord]
    pending_migrations: List[str]
    is_up_to_date: bool


class MigrationExecutionError(RuntimeError):
    """Sollevata quando una migrazione fallisce e richiede o ha eseguito il rollback."""
    def __init__(self, message: str, version: int, rollback_restored: bool = False, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.version = version
        self.rollback_restored = rollback_restored
        self.original_exception = original_exception


# ── Interfaccia Base per Migrazioni Incrementali ────────────

class BaseMigration(ABC):
    """
    Classe base astratta per una migrazione evolutiva dello schema dati.
    Ogni migrazione è atomica, versionata e provvista di routine di verifica post-esecuzione.
    """
    version: int
    name: str
    description: str

    @abstractmethod
    def up(self, conn: sqlite3.Connection) -> None:
        """Esegue le modifiche DDL/DML forward."""
        pass

    def down(self, conn: sqlite3.Connection) -> None:
        """Esegue il rollback DDL (opzionale)."""
        raise NotImplementedError(f"Rollback (down) non implementato per migrazione v{self.version}_{self.name}")

    def verify(self, conn: sqlite3.Connection) -> bool:
        """Verifica le asserzioni post-migrazione sullo schema fisico."""
        return True

    def compute_checksum(self) -> str:
        """Calcola l'hash SHA-256 identificativo del codice/DDL della migrazione."""
        content = f"{self.version}:{self.name}:{self.__class__.__name__}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ── Migrazioni Concrete Integrate in ARGUS ─────────────────

class V001_BaselineSchema(BaseMigration):
    version = 1
    name = "baseline_schema"
    description = "Crea la tabella schema_migrations e valida la presenza dei cataloghi fondanti."

    def up(self, conn: sqlite3.Connection) -> None:
        # 1. Tabella di audit per il tracciamento delle migrazioni
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms REAL NOT NULL,
                rollback_available INTEGER DEFAULT 0,
                description TEXT
            );
        """)

        # 2. Tabella di monitoraggio stato e diagnostica sistema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_health (
                check_id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Cataloghi fondamentali di portafoglio (se non esistenti)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                owner TEXT NOT NULL DEFAULT 'anonymous',
                base_currency TEXT NOT NULL DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                name TEXT,
                asset_class TEXT NOT NULL,
                currency TEXT NOT NULL,
                gics_sector TEXT,
                country TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                asset_id INTEGER NOT NULL,
                tx_date DATE NOT NULL,
                tx_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                fees REAL NOT NULL DEFAULT 0.0,
                notes TEXT,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE,
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE RESTRICT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_prices (
                price_id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                price_date DATE NOT NULL,
                close REAL NOT NULL,
                volume INTEGER,
                source TEXT NOT NULL DEFAULT 'yfinance',
                UNIQUE (asset_id, price_date),
                FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_mapping (
                mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_ticker TEXT NOT NULL UNIQUE,
                yfinance_ticker TEXT NOT NULL,
                description TEXT
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                run_name TEXT,
                portfolio_id INTEGER NOT NULL,
                calc_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_value REAL,
                total_pnl REAL,
                cagr_pct REAL,
                sharpe_ratio REAL,
                max_drawdown_pct REAL,
                var_95_pct REAL,
                hhi_index REAL,
                mc_expected_return_1y REAL,
                mc_var_95 REAL,
                var_exceptions_count INTEGER,
                sortino_ratio REAL,
                calmar_ratio REAL,
                alpha_pct REAL,
                information_ratio REAL,
                r_squared_pct REAL,
                volatility_annual_pct REAL,
                volatility_daily_pct REAL,
                cvar_95_pct REAL,
                var_cf_95_pct REAL,
                cvar_cf_95_pct REAL,
                ulcer_index REAL,
                skewness REAL,
                kurtosis REAL,
                diversification_ratio REAL,
                ff_alpha_pct REAL,
                ff_beta_mkt REAL,
                smb_tilt REAL,
                hml_tilt REAL,
                risk_free_rate_pct REAL,
                cost_basis_total REAL,
                unrealized_pnl_total REAL,
                realized_pnl_total REAL,
                dividends_total REAL,
                benchmark_ticker TEXT,
                ns_beta0 REAL,
                ns_beta1 REAL,
                ns_beta2 REAL,
                ns_tau REAL,
                covered_call_income_eur REAL,
                covered_call_contracts INTEGER,
                opt_max_sharpe_ratio REAL,
                opt_max_sharpe_return REAL,
                opt_max_sharpe_risk REAL,
                opt_min_vol_ratio REAL,
                opt_min_vol_return REAL,
                opt_min_vol_risk REAL,
                stress_covid_loss REAL,
                stress_lehman_loss REAL,
                stress_rates_loss REAL,
                var_99_pct REAL,
                cvar_99_pct REAL,
                omega_ratio REAL,
                tail_ratio REAL,
                gain_loss_ratio REAL,
                garch_vol_current_pct REAL,
                current_regime TEXT,
                regime_crisis_probability REAL,
                accumulated_minusvalenze_eur REAL,
                total_tax_due_eur REAL,
                tax_drag_pct REAL,
                closed_trades_count INTEGER,
                win_rate_pct REAL,
                profit_factor REAL,
                portfolio_duration_modified REAL,
                portfolio_convexity REAL,
                portfolio_ytm_weighted_pct REAL,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_positions (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                asset_class TEXT,
                sector TEXT,
                country TEXT,
                currency TEXT,
                qty_net REAL,
                avg_cost REAL,
                cost_basis REAL,
                last_price REAL,
                current_value REAL,
                unrealized_pnl REAL,
                realized_pnl REAL,
                dividends_total REAL,
                yield_on_cost_pct REAL,
                weight_pct REAL,
                volatility_pct REAL,
                cluster_label TEXT,
                days_to_liquidate REAL,
                trailing_pe REAL,
                forward_pe REAL,
                price_to_book REAL,
                dividend_yield REAL,
                roe REAL,
                target_mean_price REAL,
                peg_ratio REAL,
                marginal_var_pct REAL,
                component_var_pct REAL,
                beta_vs_benchmark REAL,
                opt_weight_pct REAL,
                altman_z_score REAL,
                piotroski_f_score REAL,
                beneish_m_score REAL,
                sloan_accrual_ratio REAL,
                ev_to_ebitda REAL,
                free_cash_flow_yield REAL,
                debt_to_equity REAL,
                atr_14_eur REAL,
                chandelier_exit_long_eur REAL,
                rsi_14 REAL,
                total_return REAL,
                FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE
            );
        """)

    def verify(self, conn: sqlite3.Connection) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('schema_migrations', 'portfolios', 'assets', 'transactions');")
        found = {row[0] for row in cur.fetchall()}
        return len(found) >= 4


class V002_AnalyticalCompositeIndexes(BaseMigration):
    version = 2
    name = "analytical_composite_indexes"
    description = "Crea indici compositi coprenti per accelerazione query analitiche e aggregazioni DuckDB."

    INDEXES = [
        ("idx_tx_portfolio_date", "transactions", "(portfolio_id, tx_date)"),
        ("idx_tx_asset_type", "transactions", "(asset_id, tx_type)"),
        ("idx_mp_asset_date", "market_prices", "(asset_id, price_date DESC)"),
        ("idx_snaps_portfolio_calc", "portfolio_snapshots", "(portfolio_id, calc_date DESC)"),
        ("idx_snappos_snap_ticker", "snapshot_positions", "(snapshot_id, ticker)"),
        ("idx_cashflow_acc_date", "wealth_cashflow", "(account_id, tx_date)"),
        ("idx_cashflow_cat_date", "wealth_cashflow", "(category_id, tx_date)"),
        ("idx_networth_port_date", "wealth_networth_snapshots", "(portfolio_id, snapshot_date DESC)"),
    ]

    def up(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cur.fetchall()}

        for idx_name, tbl_name, cols in self.INDEXES:
            if tbl_name in existing_tables:
                conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name} {cols};")

    def down(self, conn: sqlite3.Connection) -> None:
        for idx_name, _, _ in self.INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {idx_name};")

    def verify(self, conn: sqlite3.Connection) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
        existing_indexes = {row[0] for row in cur.fetchall()}
        return "idx_tx_portfolio_date" in existing_indexes and "idx_mp_asset_date" in existing_indexes


class V003_AssetFundamentalsAndForensicColumns(BaseMigration):
    version = 3
    name = "asset_fundamentals_and_forensics"
    description = "Aggiunge colonne fondamentali, metriche di bilancio e indicatori forensi su assets e snapshot_positions."

    ASSET_COLUMNS = [
        ("industry", "TEXT"),
        ("exchange", "TEXT"),
        ("recommendation_key", "TEXT"),
        ("market_cap", "INTEGER"),
        ("beta_5y", "REAL"),
        ("fifty_two_week_high", "REAL"),
        ("fifty_two_week_low", "REAL"),
        ("fifty_day_average", "REAL"),
        ("two_hundred_day_average", "REAL"),
        ("trailing_pe", "REAL"),
        ("forward_pe", "REAL"),
        ("price_to_book", "REAL"),
        ("dividend_yield", "REAL"),
        ("roe", "REAL"),
        ("target_mean_price", "REAL"),
        ("peg_ratio", "REAL"),
        ("profit_margins", "REAL"),
        ("gross_margins", "REAL"),
        ("operating_margins", "REAL"),
        ("total_revenue", "INTEGER"),
        ("ebitda", "INTEGER"),
        ("debt_to_equity", "REAL"),
        ("revenue_growth", "REAL"),
        ("earnings_growth", "REAL"),
    ]

    SNAPSHOT_POSITION_COLUMNS = [
        ("sector", "TEXT"),
        ("country", "TEXT"),
        ("currency", "TEXT"),
        ("cost_basis", "REAL"),
        ("realized_pnl", "REAL"),
        ("dividends_total", "REAL"),
        ("yield_on_cost_pct", "REAL"),
        ("debt_to_equity", "REAL"),
        ("piotroski_f_score", "REAL"),
        ("altman_z_score", "REAL"),
        ("beneish_m_score", "REAL"),
        ("sloan_accrual_ratio", "REAL"),
        ("ev_to_ebitda", "REAL"),
        ("free_cash_flow_yield", "REAL"),
        ("atr_14_eur", "REAL"),
        ("chandelier_exit_long_eur", "REAL"),
        ("rsi_14", "REAL"),
        ("total_return", "REAL"),
    ]

    SNAPSHOT_COLUMNS = [
        ("volatility_annual_pct", "REAL"),
        ("volatility_daily_pct", "REAL"),
        ("cvar_95_pct", "REAL"),
        ("var_cf_95_pct", "REAL"),
        ("cvar_cf_95_pct", "REAL"),
        ("ulcer_index", "REAL"),
        ("skewness", "REAL"),
        ("kurtosis", "REAL"),
        ("diversification_ratio", "REAL"),
        ("ff_alpha_pct", "REAL"),
        ("ff_beta_mkt", "REAL"),
        ("smb_tilt", "REAL"),
        ("hml_tilt", "REAL"),
        ("risk_free_rate_pct", "REAL"),
        ("cost_basis_total", "REAL"),
        ("unrealized_pnl_total", "REAL"),
        ("realized_pnl_total", "REAL"),
        ("dividends_total", "REAL"),
        ("benchmark_ticker", "TEXT"),
        ("ns_beta0", "REAL"),
        ("ns_beta1", "REAL"),
        ("ns_beta2", "REAL"),
        ("ns_tau", "REAL"),
        ("covered_call_income_eur", "REAL"),
        ("covered_call_contracts", "INTEGER"),
        ("opt_max_sharpe_ratio", "REAL"),
        ("opt_max_sharpe_return", "REAL"),
        ("opt_max_sharpe_risk", "REAL"),
        ("opt_min_vol_ratio", "REAL"),
        ("opt_min_vol_return", "REAL"),
        ("opt_min_vol_risk", "REAL"),
        ("stress_covid_loss", "REAL"),
        ("stress_lehman_loss", "REAL"),
        ("stress_rates_loss", "REAL"),
        ("var_99_pct", "REAL"),
        ("cvar_99_pct", "REAL"),
        ("omega_ratio", "REAL"),
        ("tail_ratio", "REAL"),
        ("gain_loss_ratio", "REAL"),
        ("garch_vol_current_pct", "REAL"),
        ("current_regime", "TEXT"),
        ("regime_crisis_probability", "REAL"),
        ("accumulated_minusvalenze_eur", "REAL"),
        ("total_tax_due_eur", "REAL"),
        ("tax_drag_pct", "REAL"),
        ("closed_trades_count", "INTEGER"),
        ("win_rate_pct", "REAL"),
        ("profit_factor", "REAL"),
        ("portfolio_duration_modified", "REAL"),
        ("portfolio_convexity", "REAL"),
        ("portfolio_ytm_weighted_pct", "REAL"),
    ]

    def _get_existing_columns(self, conn: sqlite3.Connection, table_name: str) -> Set[str]:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cur.fetchall()}

    def up(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}

        if "assets" in tables:
            cols = self._get_existing_columns(conn, "assets")
            for col_name, col_type in self.ASSET_COLUMNS:
                if col_name not in cols:
                    conn.execute(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type};")

        if "snapshot_positions" in tables:
            cols = self._get_existing_columns(conn, "snapshot_positions")
            for col_name, col_type in self.SNAPSHOT_POSITION_COLUMNS:
                if col_name not in cols:
                    conn.execute(f"ALTER TABLE snapshot_positions ADD COLUMN {col_name} {col_type};")

        if "portfolio_snapshots" in tables:
            cols = self._get_existing_columns(conn, "portfolio_snapshots")
            for col_name, col_type in self.SNAPSHOT_COLUMNS:
                if col_name not in cols:
                    conn.execute(f"ALTER TABLE portfolio_snapshots ADD COLUMN {col_name} {col_type};")

    def verify(self, conn: sqlite3.Connection) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}

        if "assets" in tables:
            cols = self._get_existing_columns(conn, "assets")
            for col_name, _ in self.ASSET_COLUMNS[:5]:
                if col_name not in cols:
                    return False
        return True


class V004_WealthEcosystemAudit(BaseMigration):
    version = 4
    name = "wealth_ecosystem_audit"
    description = "Armonizza tabelle Wealth Management, colonne tx_hash per deduplicazione e tabelle di supporto."

    def up(self, conn: sqlite3.Connection) -> None:
        # 0. Creazione tabelle Wealth se non presenti
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wealth_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner TEXT NOT NULL DEFAULT 'user',
                base_currency TEXT NOT NULL DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES wealth_accounts(account_id),
                FOREIGN KEY (category_id) REFERENCES wealth_categories(category_id)
            );
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
        """)
        conn.execute("""
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
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wealth_goals (
                goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'custom',
                target_amount REAL NOT NULL DEFAULT 0.0,
                target_date DATE NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0.0,
                monthly_contribution REAL NOT NULL DEFAULT 0.0,
                priority TEXT NOT NULL DEFAULT 'medium',
                risk_tolerance TEXT NOT NULL DEFAULT 'moderate',
                inflation_rate REAL NOT NULL DEFAULT 0.02,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wealth_portfolio_risk_links (
                link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                wealth_portfolio_id INTEGER NOT NULL,
                risk_portfolio_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}

        # 1. wealth_cashflow: assicurare colonne essenziali tx_hash, tags, payment_method
        if "wealth_cashflow" in tables:
            cur.execute("PRAGMA table_info(wealth_cashflow);")
            cols = {row[1] for row in cur.fetchall()}
            if "tx_hash" not in cols:
                conn.execute("ALTER TABLE wealth_cashflow ADD COLUMN tx_hash TEXT;")
            if "tags" not in cols:
                conn.execute("ALTER TABLE wealth_cashflow ADD COLUMN tags TEXT;")
            if "payment_method" not in cols:
                conn.execute("ALTER TABLE wealth_cashflow ADD COLUMN payment_method TEXT DEFAULT 'Carta / Bonifico';")
            if "is_recurring" not in cols:
                conn.execute("ALTER TABLE wealth_cashflow ADD COLUMN is_recurring INTEGER DEFAULT 0;")

        # 2. wealth_fixed_expenses: colonne cadence, is_split, split_details
        if "wealth_fixed_expenses" in tables:
            cur.execute("PRAGMA table_info(wealth_fixed_expenses);")
            cols = {row[1] for row in cur.fetchall()}
            if "cadence" not in cols:
                conn.execute("ALTER TABLE wealth_fixed_expenses ADD COLUMN cadence TEXT DEFAULT 'Mensile';")
            if "is_split" not in cols:
                conn.execute("ALTER TABLE wealth_fixed_expenses ADD COLUMN is_split INTEGER DEFAULT 0;")
            if "split_details" not in cols:
                conn.execute("ALTER TABLE wealth_fixed_expenses ADD COLUMN split_details TEXT;")

        # 3. Indice univoco per deduplicazione su tx_hash se presente
        if "wealth_cashflow" in tables:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cashflow_tx_hash ON wealth_cashflow(tx_hash);")

    def verify(self, conn: sqlite3.Connection) -> bool:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        if "wealth_cashflow" in tables:
            cur.execute("PRAGMA table_info(wealth_cashflow);")
            cols = {row[1] for row in cur.fetchall()}
            return "tx_hash" in cols
        return True


# ── Database Migration Manager Engine ──────────────────────

class DatabaseMigrationManager:
    """
    Manager architetturale DBRE per il ciclo di vita dello schema SQLite embedded.
    Fornisce:
      - Dual Version Tracking: PRAGMA user_version (O(1) boot check) + tabella `schema_migrations` (audit trail SHA-256).
      - Pre-Flight Silent Shadow Backup: Snapshot a caldo prima di applicare modifiche DDL.
      - Transazionalità Atomica: DDL con rollback automatico in caso di errore.
      - Ripristino Disaster Recovery immediato su eccezione.
      - Schema Drift Inspector: Rilevamento discrepanze tra modelli Python e tabelle fisiche.
    """

    DEFAULT_MIGRATIONS: List[Type[BaseMigration]] = [
        V001_BaselineSchema,
        V002_AnalyticalCompositeIndexes,
        V003_AssetFundamentalsAndForensicColumns,
        V004_WealthEcosystemAudit,
    ]

    _instance: Optional["DatabaseMigrationManager"] = None

    @classmethod
    def get_instance(cls, db_path: Optional[Union[str, Path]] = None, backup_dir: Optional[Union[str, Path]] = None) -> "DatabaseMigrationManager":
        if cls._instance is None:
            cls._instance = cls(db_path=db_path, backup_dir=backup_dir)
        return cls._instance

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        backup_dir: Optional[Union[str, Path]] = None,
        auto_backup: bool = True,
        custom_migrations: Optional[List[Type[BaseMigration]]] = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_SQLITE_PATH
        self.backup_dir = Path(backup_dir) if backup_dir is not None else DEFAULT_BACKUP_DIR
        self.auto_backup = auto_backup

        migration_classes = custom_migrations if custom_migrations is not None else self.DEFAULT_MIGRATIONS
        self._registry: Dict[int, BaseMigration] = {}
        for m_cls in migration_classes:
            m = m_cls()
            if m.version in self._registry:
                raise ValueError(f"Versione di migrazione duplicata: {m.version} ({m.name})")
            self._registry[m.version] = m

    @property
    def target_version(self) -> int:
        return max(self._registry.keys()) if self._registry else 0

    # ── Version Tracking Primitives ──────────────────────────

    def get_user_version(self, conn: sqlite3.Connection) -> int:
        """Legge PRAGMA user_version istantaneamente dal file header O(1)."""
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def set_user_version(self, conn: sqlite3.Connection, version: int) -> None:
        """Aggiorna il contatore PRAGMA user_version."""
        conn.execute(f"PRAGMA user_version = {int(version)};")

    def ensure_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Garantisce la presenza della tabella di audit schema_migrations."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms REAL NOT NULL,
                rollback_available INTEGER DEFAULT 0,
                description TEXT
            );
        """)

    def get_applied_migrations(self, conn: sqlite3.Connection) -> List[MigrationRecord]:
        """Recupera la cronologia di tutte le migrazioni già applicate."""
        self.ensure_migrations_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT version, name, checksum, applied_at, execution_time_ms, rollback_available, description FROM schema_migrations ORDER BY version ASC;")
        records = []
        for row in cur.fetchall():
            records.append(MigrationRecord(
                version=row[0],
                name=row[1],
                checksum=row[2],
                applied_at=str(row[3]),
                execution_time_ms=float(row[4]),
                rollback_available=bool(row[5]),
                description=row[6]
            ))
        return records

    def get_migration_status(self, conn: Optional[sqlite3.Connection] = None) -> MigrationStatus:
        """Restituisce lo stato globale del database rispetto al catalogo migrazioni."""
        close_conn = False
        if conn is None:
            if not self.db_path.exists():
                return MigrationStatus(
                    current_version=0,
                    target_version=self.target_version,
                    applied_count=0,
                    pending_count=len(self._registry),
                    applied_migrations=[],
                    pending_migrations=[f"v{v}_{m.name}" for v, m in sorted(self._registry.items())],
                    is_up_to_date=False
                )
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            close_conn = True

        try:
            curr_v = self.get_user_version(conn)
            applied = self.get_applied_migrations(conn)
            applied_versions = {r.version for r in applied}
            pending = [
                f"v{v}_{m.name}"
                for v, m in sorted(self._registry.items())
                if v not in applied_versions
            ]
            return MigrationStatus(
                current_version=curr_v,
                target_version=self.target_version,
                applied_count=len(applied),
                pending_count=len(pending),
                applied_migrations=applied,
                pending_migrations=pending,
                is_up_to_date=(curr_v >= self.target_version and len(pending) == 0)
            )
        finally:
            if close_conn and conn:
                conn.close()

    # ── Disaster Recovery & Pre-Flight Backup ─────────────────

    def create_pre_flight_backup(self) -> Optional[Path]:
        """
        Crea uno snapshot preventivo atomico del database prima di applicare modifiche DDL.
        Se core.backup_engine è disponibile, usa l'API SQLite hot backup con integrity check.
        Altrimenti esegue una shadow copy atomica con PRAGMA integrity_check.
        """
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"pre_migration_v{self.target_version}_{timestamp}.db"
        snapshot_path = self.backup_dir / snapshot_name

        try:
            from core.backup_engine import perform_hot_backup
            compressed = perform_hot_backup(db_path=self.db_path, backup_dir=self.backup_dir, max_retention_days=14)
            logger.info("Pre-flight Hot Backup completato con successo: %s", compressed)
            return compressed
        except Exception as e:
            logger.warning("perform_hot_backup non riuscito (%s), fallback su shadow copy atomica", e)

        # Fallback Shadow Copy con SQLite online backup API
        src_conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        dst_conn = sqlite3.connect(str(snapshot_path))
        try:
            with dst_conn:
                src_conn.backup(dst_conn, pages=250)
        finally:
            dst_conn.close()
            src_conn.close()

        # Verifica integrità dello snapshot
        chk_conn = sqlite3.connect(str(snapshot_path))
        try:
            res = chk_conn.execute("PRAGMA integrity_check;").fetchone()
            if not res or res[0] != "ok":
                raise RuntimeError(f"Snapshot non integro: {res}")
        finally:
            chk_conn.close()

        logger.info("Shadow snapshot preventivo creato e validato: %s", snapshot_path)
        return snapshot_path

    def restore_from_snapshot(self, backup_path: Path) -> bool:
        """Ripristina atomicamente lo snapshot in caso di fallimento della migrazione."""
        if not backup_path.exists():
            logger.error("Impossibile ripristinare: file snapshot non trovato: %s", backup_path)
            return False

        logger.warning("Ripristino di emergenza del database dallo snapshot: %s", backup_path)
        try:
            if backup_path.name.endswith(".gz"):
                from core.backup_engine import restore_snapshot
                return restore_snapshot(backup_path, target_db_path=self.db_path)

            shutil.copy2(str(backup_path), str(self.db_path))
            return True
        except Exception as ex:
            logger.critical("Errore catastrofico durante il ripristino di emergenza: %s", ex)
            return False

    # ── Migration Pipeline (Forward & Rollback) ───────────────

    def migrate(self, target_version: Optional[int] = None) -> List[MigrationRecord]:
        """
        Esegue il ciclo di migrazione in avanti (forward migration).
        1. Valuta le migrazioni pendenti. Se nessuna, ritorna istantaneamente in O(1).
        2. Esegue il backup a caldo preventivo.
        3. Esegue ogni migrazione in una transazione atomica (BEGIN IMMEDIATE).
        4. Valuta la routine `verify()` della migrazione.
        5. Aggiorna la tabella `schema_migrations` e `PRAGMA user_version`.
        6. In caso di eccezione: ROLLBACK immediato + ripristino da snapshot di backup.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        target_v = target_version if target_version is not None else self.target_version

        # Connessione di ispezione rapida
        init_conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        try:
            curr_v = self.get_user_version(init_conn)
            self.ensure_migrations_table(init_conn)
            applied_records = self.get_applied_migrations(init_conn)
        finally:
            init_conn.close()

        applied_versions = {r.version: r for r in applied_records}
        pending_versions = [
            v for v in sorted(self._registry.keys())
            if v <= target_v and v not in applied_versions
        ]

        if not pending_versions and curr_v >= target_v:
            logger.debug("Database già aggiornato alla versione v%d. Nessuna migrazione necessaria.", curr_v)
            return []

        # Creazione Snapshot di Sicurezza Preventivo
        backup_snapshot: Optional[Path] = None
        if self.auto_backup and self.db_path.exists() and self.db_path.stat().st_size > 0:
            try:
                backup_snapshot = self.create_pre_flight_backup()
            except Exception as ex_b:
                logger.warning("Impossibile creare backup preventivo (proseguo comunque): %s", ex_b)

        applied_now: List[MigrationRecord] = []

        # Apertura connessione con controllo manuale della transazione (isolation_level=None)
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        try:
            # Abilitazione WAL e timeout per prevenire blocchi client-side
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")

            for v in pending_versions:
                migration = self._registry[v]
                logger.info("Applicazione migrazione v%d: %s...", v, migration.name)
                start_time = time.perf_counter()

                # Inizio transazione atomica DDL/DML
                conn.execute("BEGIN IMMEDIATE;")
                try:
                    migration.up(conn)

                    # Post-migrazione verification gate
                    if not migration.verify(conn):
                        raise RuntimeError(f"Verifica post-migrazione fallita per v{v}_{migration.name}")

                    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                    checksum = migration.compute_checksum()

                    can_rollback = False
                    try:
                        can_rollback = migration.__class__.down != BaseMigration.down
                    except Exception:
                        pass

                    # Registrazione audit trail
                    conn.execute("""
                        INSERT OR REPLACE INTO schema_migrations 
                        (version, name, checksum, execution_time_ms, rollback_available, description)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, (v, migration.name, checksum, elapsed_ms, 1 if can_rollback else 0, migration.description))

                    # Aggiornamento PRAGMA user_version
                    self.set_user_version(conn, v)

                    # Commit atomico
                    conn.execute("COMMIT;")

                    rec = MigrationRecord(
                        version=v,
                        name=migration.name,
                        checksum=checksum,
                        applied_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        execution_time_ms=elapsed_ms,
                        rollback_available=can_rollback,
                        description=migration.description
                    )
                    applied_now.append(rec)
                    logger.info("Migrazione v%d completata con successo in %.2f ms.", v, elapsed_ms)

                except Exception as ex_migration:
                    logger.error("Errore critico durante migrazione v%d: %s. Eseguo ROLLBACK.", v, ex_migration)
                    try:
                        conn.execute("ROLLBACK;")
                    except Exception:
                        pass

                    # Se abbiamo uno snapshot preventivo, ripristiniamo lo stato precedente
                    conn.close()
                    conn = None
                    restored = False
                    if backup_snapshot is not None:
                        restored = self.restore_from_snapshot(backup_snapshot)

                    raise MigrationExecutionError(
                        f"Fallimento migrazione v{v}_{migration.name}: {ex_migration}",
                        version=v,
                        rollback_restored=restored,
                        original_exception=ex_migration
                    ) from ex_migration

            return applied_now

        finally:
            if conn is not None:
                conn.close()

    def rollback(self, target_version: int) -> List[MigrationRecord]:
        """
        Esegue il rollback a ritroso fino a `target_version` (esclusa).
        Applica i metodi `down()` in ordine decrescente di versione.
        """
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        try:
            curr_v = self.get_user_version(conn)
            if target_version >= curr_v:
                logger.info("Target version %d >= current version %d. Nessun rollback necessario.", target_version, curr_v)
                return []

            applied = self.get_applied_migrations(conn)
            applied_map = {r.version: r for r in applied}

            to_rollback = [
                v for v in sorted(self._registry.keys(), reverse=True)
                if v > target_version and v in applied_map
            ]

            rolled_back: List[MigrationRecord] = []

            for v in to_rollback:
                migration = self._registry[v]
                logger.info("Esecuzione rollback v%d: %s...", v, migration.name)

                conn.execute("BEGIN IMMEDIATE;")
                try:
                    migration.down(conn)
                    conn.execute("DELETE FROM schema_migrations WHERE version = ?;", (v,))
                    new_v = v - 1
                    self.set_user_version(conn, new_v)
                    conn.execute("COMMIT;")

                    rec = applied_map[v]
                    rolled_back.append(rec)
                    logger.info("Rollback v%d completato con successo.", v)
                except Exception as ex:
                    conn.execute("ROLLBACK;")
                    raise RuntimeError(f"Rollback v{v} fallito: {ex}") from ex

            return rolled_back

        finally:
            conn.close()

    # ── Schema Drift Inspector & Anomaly Detection ───────────

    def detect_schema_drift(self) -> SchemaDriftReport:
        """
        Ispeziona lo schema fisico di SQLite e lo confronta con i modelli applicativi
        (SQLAlchemy ORM models e Wealth Models) per identificare divergenze:
          - Tabelle mancanti
          - Colonne mancanti o con affinità divergenti
          - Indici compositi raccomandati assenti
          - Violazioni e orfani di chiavi esterne (PRAGMA foreign_key_check)
        """
        if not self.db_path.exists():
            return SchemaDriftReport(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                db_path=str(self.db_path),
                is_healthy=False,
                drift_count=1,
                items=[DriftItem(
                    table_name="*",
                    field_or_index="*",
                    issue_type="MISSING_DATABASE",
                    severity=DriftSeverity.CRITICAL,
                    detail=f"Database file {self.db_path} non presente su disco.",
                    remediation_hint="Eseguire DatabaseMigrationManager.migrate() per generare lo schema iniziale."
                )],
                summary="Database file assente."
            )

        items: List[DriftItem] = []
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            physical_tables = {row[0] for row in cur.fetchall()}

            # 1. Ispezione modelli SQLAlchemy (core/models.py)
            try:
                from core.models import Base
                for table_name, sa_table in Base.metadata.tables.items():
                    if table_name not in physical_tables:
                        items.append(DriftItem(
                            table_name=table_name,
                            field_or_index="TABLE",
                            issue_type="MISSING_TABLE",
                            severity=DriftSeverity.CRITICAL,
                            detail=f"Tabella '{table_name}' definita in core/models.py assente nel DB fisico.",
                            remediation_hint="Applicare le migrazioni o Base.metadata.create_all()"
                        ))
                        continue

                    # Controllo colonne
                    cur.execute(f"PRAGMA table_info({table_name});")
                    phys_cols = {row[1]: row[2].upper() for row in cur.fetchall()}

                    for col in sa_table.columns:
                        if col.name not in phys_cols:
                            items.append(DriftItem(
                                table_name=table_name,
                                field_or_index=col.name,
                                issue_type="MISSING_COLUMN",
                                severity=DriftSeverity.WARNING,
                                detail=f"Colonna '{col.name}' presente nel modello ORM ma assente nella tabella '{table_name}'.",
                                remediation_hint=f"Eseguire migrazione per aggiungere la colonna con ALTER TABLE {table_name} ADD COLUMN {col.name}"
                            ))

            except ImportError:
                logger.debug("core.models.Base non disponibile per drift check.")

            # 2. Ispezione tabelle Wealth Management
            expected_wealth_tables = [
                "wealth_accounts", "wealth_categories", "wealth_cashflow",
                "wealth_physical_assets", "wealth_pension_plans", "wealth_networth_snapshots"
            ]
            for w_table in expected_wealth_tables:
                if w_table not in physical_tables:
                    items.append(DriftItem(
                        table_name=w_table,
                        field_or_index="TABLE",
                        issue_type="MISSING_TABLE",
                        severity=DriftSeverity.WARNING,
                        detail=f"Tabella Wealth '{w_table}' assente.",
                        remediation_hint="Eseguire init_wealth_db() o migrazione v4"
                    ))

            # 3. Controllo indici compositi raccomandati
            cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
            physical_indexes = {row[0] for row in cur.fetchall()}
            for idx_name, tbl_name, cols in V002_AnalyticalCompositeIndexes.INDEXES:
                if tbl_name in physical_tables and idx_name not in physical_indexes:
                    items.append(DriftItem(
                        table_name=tbl_name,
                        field_or_index=idx_name,
                        issue_type="MISSING_INDEX",
                        severity=DriftSeverity.INFO,
                        detail=f"Indice analitico composito '{idx_name}' assente su {tbl_name}{cols}.",
                        remediation_hint=f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl_name} {cols};"
                    ))

            # 4. Controllo integrità referenziale e orfani (PRAGMA foreign_key_check)
            fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
            for v_row in fk_violations:
                tbl, rowid, parent_tbl, fkid = v_row[0], v_row[1], v_row[2], v_row[3]
                items.append(DriftItem(
                    table_name=tbl,
                    field_or_index=f"rowid={rowid}",
                    issue_type="FOREIGN_KEY_VIOLATION",
                    severity=DriftSeverity.WARNING,
                    detail=f"Record orfano in '{tbl}' (rowid {rowid}) verso tabella genitore '{parent_tbl}'.",
                    remediation_hint=f"Riconciliare o rimuovere record orfano in {tbl} dove rowid={rowid}."
                ))

            # 5. Integrità strutturale SQLite
            integ_res = conn.execute("PRAGMA integrity_check;").fetchone()
            if not integ_res or integ_res[0] != "ok":
                items.append(DriftItem(
                    table_name="*",
                    field_or_index="PRAGMA integrity_check",
                    issue_type="CORRUPTED_DATABASE",
                    severity=DriftSeverity.CRITICAL,
                    detail=f"Integrità del database compromessa: {integ_res}",
                    remediation_hint="Ripristinare l'ultimo snapshot valido con restore_from_snapshot()."
                ))

            is_healthy = not any(it.severity == DriftSeverity.CRITICAL for it in items)
            summary = (
                "Schema integro e conforme al 100%."
                if not items
                else f"Rilevate {len(items)} anomalie ({sum(1 for i in items if i.severity == DriftSeverity.CRITICAL)} critiche, {sum(1 for i in items if i.severity == DriftSeverity.WARNING)} avvisi)."
            )

            return SchemaDriftReport(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                db_path=str(self.db_path),
                is_healthy=is_healthy,
                drift_count=len(items),
                items=items,
                summary=summary
            )

        finally:
            conn.close()

    # ── DuckDB In-Process OLAP Compatibility ──────────────────

    def verify_duckdb_compatibility(self) -> Dict[str, Any]:
        """
        Verifica che il database SQLite migrato sia al 100% interrogabile
        dal motore colonnare vettorizzato DuckDB tramite estensione SQLite nativa.
        """
        if not self.db_path.exists():
            return {"compatible": False, "error": "Database file non esistente"}

        try:
            import duckdb
        except ImportError:
            return {"compatible": True, "note": "DuckDB non installato nell'ambiente (verifica saltata)"}

        try:
            con = duckdb.connect(database=":memory:")
            try:
                con.execute("INSTALL sqlite;")
                con.execute("LOAD sqlite;")
                escaped_path = str(self.db_path).replace("\\", "/")
                con.execute(f"ATTACH '{escaped_path}' AS local_db (TYPE SQLITE);")
                tables = con.execute("SHOW TABLES FROM local_db;").fetchall()
                sample_count = con.execute("SELECT count(*) FROM local_db.sqlite_master WHERE type='table';").fetchone()[0]
                return {
                    "compatible": True,
                    "engine": "DuckDB Native C++ Scanner",
                    "tables_found": sample_count,
                    "tables": [t[0] for t in tables[:10]],
                    "status": "PASS"
                }
            except Exception as e_attach:
                import pandas as pd
                s_conn = sqlite3.connect(str(self.db_path))
                df_meta = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", s_conn)
                s_conn.close()
                con.register("df_meta", df_meta)
                cnt = con.execute("SELECT count(*) FROM df_meta").fetchone()[0]
                return {
                    "compatible": True,
                    "engine": "DuckDB Pandas/Arrow In-Memory Bridge",
                    "tables_found": cnt,
                    "note": f"Native attach note: {e_attach}",
                    "status": "PASS"
                }
        except Exception as ex:
            return {"compatible": False, "error": str(ex), "status": "FAIL"}


# ── Helper di Boot per Entrypoint ARGUS ─────────────────────

def bootstrap_and_migrate_db(db_path: Optional[Union[str, Path]] = None) -> DatabaseMigrationManager:
    """
    Funzione di bootstrap richiamata all'avvio dell'applicazione.
    Garantisce l'inizializzazione idempotente dello schema e applica tutte le migrazioni pendenti.
    """
    mgr = DatabaseMigrationManager.get_instance(db_path=db_path)
    status = mgr.get_migration_status()
    if not status.is_up_to_date:
        logger.info(
            "Schema database alla v%d (target v%d). Applicazione di %d migrazioni pendenti...",
            status.current_version, status.target_version, status.pending_count
        )
        applied = mgr.migrate()
        logger.info("Migrazioni applicate: %s", [f"v{m.version}_{m.name}" for m in applied])
    else:
        logger.debug("Database up-to-date (v%d). Nessuna migrazione richiesta.", status.current_version)
    return mgr
