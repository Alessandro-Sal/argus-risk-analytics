# ============================================================
# tests/test_supabase_cloud.py
# Unit & Integration Tests for ARGUS Zero-Cost Supabase Cloud Layer
# ============================================================

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy import text as sqlt

from core.fetcher import _store_prices
from core.supabase_cloud import (
    DEFAULT_SUPABASE_POOLER_HOST,
    DEFAULT_SUPABASE_PROJECT_REF,
    TABLE_PK_MAP,
    SupabaseAuthManager,
    build_supabase_db_url,
    generate_supabase_schema_sql,
    get_supabase_config,
    is_supabase_configured,
    mask_db_url,
    migrate_local_to_supabase,
    normalize_supabase_db_url,
    optimize_supabase_storage_footprint,
    record_cloud_heartbeat,
)
from core.wealth.tax_history_engine import record_declaration
from core.wealth.wealth_db import (
    _get_last_insert_id,
    init_wealth_db,
    save_wealth_account,
    save_wealth_fixed_expense,
    save_wealth_goal,
)


def test_normalize_and_mask_supabase_url():
    raw = "postgres://postgres.abcdefgh:MySecretPass123@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    norm = normalize_supabase_db_url(raw)
    assert norm.startswith("postgresql+psycopg2://postgres.abcdefgh:MySecretPass123@")
    assert "sslmode=require" in norm

    # Localhost should not force sslmode=require
    local_raw = "postgresql://postgres:pass@localhost:5432/argus"
    local_norm = normalize_supabase_db_url(local_raw)
    assert local_norm == "postgresql+psycopg2://postgres:pass@localhost:5432/argus"

    masked = mask_db_url(norm)
    assert "MySecretPass123" not in masked
    assert "postgres.abcdefgh:****@aws-0-eu-central-1.pooler.supabase.com:6543" in masked

    # Auto-builder from project_ref + db_password
    built = build_supabase_db_url(db_password="My#Special@Pass!")
    assert f"postgres.{DEFAULT_SUPABASE_PROJECT_REF}:My%23Special%40Pass%21@{DEFAULT_SUPABASE_POOLER_HOST}:6543" in built


def test_supabase_config_from_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_PASSWORD", "OnlyPasswordNeeded99")
    cfg_pw = get_supabase_config()
    assert cfg_pw["is_configured"] is True
    assert DEFAULT_SUPABASE_PROJECT_REF in cfg_pw["db_url"]
    assert DEFAULT_SUPABASE_POOLER_HOST in cfg_pw["db_url"]
    assert cfg_pw["supabase_url"] == f"https://{DEFAULT_SUPABASE_PROJECT_REF}.supabase.co"

    monkeypatch.setenv(
        "SUPABASE_DB_URL",
        "postgres://postgres.proj:secret@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    )
    monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-123")
    monkeypatch.setenv("ARGUS_REQUIRE_LOGIN", "true")
    monkeypatch.setenv("ARGUS_ADMIN_PASSWORD", "VaultMaster2026!")

    cfg = get_supabase_config()
    assert cfg["is_configured"] is True
    assert cfg["has_rest_api"] is True
    assert cfg["supabase_url"] == "https://proj.supabase.co"
    assert cfg["require_login"] is True
    assert is_supabase_configured() is True

    assert SupabaseAuthManager.verify_admin_password("VaultMaster2026!") is True
    assert SupabaseAuthManager.verify_admin_password("WrongPass") is False
    assert SupabaseAuthManager.verify_admin_password("") is False


def test_generate_supabase_schema_sql_completeness():
    sql_script = generate_supabase_schema_sql(include_rls=True, include_storage=True)
    for tbl in TABLE_PK_MAP.keys():
        assert f"CREATE TABLE IF NOT EXISTS {tbl}" in sql_script

    assert "CREATE TABLE IF NOT EXISTS argus_cloud_heartbeat" in sql_script
    assert "ENABLE ROW LEVEL SECURITY" in sql_script
    assert "tax-documents" in sql_script
    # Verify integer flag types for PostgreSQL compatibility with `WHERE is_active = 1`
    assert "is_active INTEGER NOT NULL DEFAULT 1" in sql_script
    assert "is_system INTEGER NOT NULL DEFAULT 0" in sql_script
    assert "is_officially_filed INTEGER NOT NULL DEFAULT 1" in sql_script


def test_storage_footprint_and_pruning(tmp_path: Path):
    db_file = tmp_path / "quota_test.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    from core.models import Base

    Base.metadata.create_all(engine)
    init_wealth_db(engine)

    with engine.begin() as conn:
        conn.execute(
            sqlt("INSERT INTO assets (asset_id, ticker, name, asset_class, currency) VALUES (1, 'AAPL', 'Apple', 'equity', 'USD')")
        )
        conn.execute(
            sqlt("INSERT INTO assets (asset_id, ticker, name, asset_class, currency) VALUES (2, 'ORPH', 'Orphan', 'equity', 'USD')")
        )
        conn.execute(
            sqlt(
                "INSERT INTO transactions (portfolio_id, asset_id, tx_date, tx_type, quantity, price, fees, currency) "
                "VALUES (1, 1, '2025-01-10', 'BUY', 10, 180, 1, 'USD')"
            )
        )
        # Active asset recent price
        conn.execute(
            sqlt("INSERT INTO market_prices (asset_id, price_date, close, source) VALUES (1, '2025-01-10', 180.0, 'yfinance')")
        )
        # Active asset very old price (2005)
        conn.execute(
            sqlt("INSERT INTO market_prices (asset_id, price_date, close, source) VALUES (1, '2005-01-10', 12.0, 'yfinance')")
        )
        # Orphan asset price (asset_id=2 has no transactions)
        conn.execute(
            sqlt("INSERT INTO market_prices (asset_id, price_date, close, source) VALUES (2, '2025-01-10', 50.0, 'yfinance')")
        )

    initial_stats = optimize_supabase_storage_footprint(engine, prune_orphan_prices=False)
    assert initial_stats["quota_mb"] == 500.0
    assert initial_stats["status_tier"] == "OPTIMAL"
    assert initial_stats["total_rows"] > 0

    pruned_stats = optimize_supabase_storage_footprint(
        engine, prune_orphan_prices=True, max_price_age_years=10
    )
    assert pruned_stats["pruned_orphan_rows"] == 1
    assert pruned_stats["pruned_aged_rows"] == 1

    with engine.connect() as conn:
        rem = conn.execute(sqlt("SELECT COUNT(*) FROM market_prices")).scalar()
        assert rem == 1

    engine.dispose()


def test_migrate_local_to_supabase_and_heartbeat(tmp_path: Path):
    src_path = tmp_path / "src_local.db"
    tgt_path = tmp_path / "tgt_cloud.db"

    src_eng = create_engine(f"sqlite:///{src_path.as_posix()}")
    tgt_eng = create_engine(f"sqlite:///{tgt_path.as_posix()}")

    from core.models import Base

    Base.metadata.create_all(src_eng)
    init_wealth_db(src_eng)

    acc_id = save_wealth_account(
        src_eng,
        {
            "name": "Conto Cloud Test",
            "account_type": "checking",
            "institution": "Fineco",
            "currency": "EUR",
            "balance": 25000.0,
        },
    )
    assert acc_id > 0

    fid = save_wealth_fixed_expense(
        src_eng,
        {"category": "Casa", "note": "Affitto", "amount": 850.0, "payment_day": 5},
    )
    assert fid > 0

    gid = save_wealth_goal(
        src_eng,
        {"name": "Fondo Emergenza", "target_amount": 30000.0, "target_date": "2028-12-31"},
    )
    assert gid > 0

    record_declaration(
        src_eng,
        {
            "profile_id": "default",
            "tax_year": 2024,
            "filing_year": 2025,
            "model_type": "730_ORDINARIO",
            "gross_income": 42000.0,
            "taxable_income": 38000.0,
            "net_tax_irpef": 8200.0,
        },
    )
    src_eng.dispose()

    mig_res = migrate_local_to_supabase(
        sqlite_path=str(src_path),
        target_engine=tgt_eng,
    )
    assert mig_res["ok"] is True
    assert mig_res["tables"].get("wealth_accounts", 0) >= 1
    assert mig_res["tables"].get("wealth_fixed_expenses", 0) == 1
    assert mig_res["tables"].get("wealth_goals", 0) == 1
    assert mig_res["tables"].get("tax_declarations", 0) == 1

    hb_ok = record_cloud_heartbeat(tgt_eng, source="unit_test", details="Ping check")
    assert hb_ok is True

    with tgt_eng.connect() as conn:
        hb_cnt = conn.execute(sqlt("SELECT COUNT(*) FROM argus_cloud_heartbeat")).scalar()
        assert hb_cnt >= 2

    tgt_eng.dispose()


def test_postgres_dialect_sql_generation():
    mock_conn = MagicMock()
    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = 42
    mock_conn.execute.return_value = mock_scalar

    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    # 1. Test _get_last_insert_id uses SELECT LASTVAL() on PostgreSQL
    last_id = _get_last_insert_id(mock_conn, mock_engine)
    assert last_id == 42
    executed_sql = str(mock_conn.execute.call_args[0][0])
    assert "LASTVAL()" in executed_sql

    # 2. Test _store_prices uses ON CONFLICT (asset_id, price_date) DO NOTHING on PostgreSQL
    mock_conn.reset_mock()
    hist_df = pd.DataFrame(
        {"Close": [105.5, 106.2], "Volume": [1000, 1200]},
        index=pd.to_datetime(["2025-02-01", "2025-02-02"]),
    )
    cnt = _store_prices(hist_df, asset_id=7, engine=mock_engine, ticker="MSFT")
    assert cnt == 2
    price_sql = str(mock_conn.execute.call_args[0][0])
    assert "ON CONFLICT (asset_id, price_date) DO NOTHING" in price_sql


def test_multi_user_authentication_and_isolation(tmp_path: Path):
    db_file = tmp_path / "multi_user.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    init_wealth_db(engine)

    # Create 4 users (1 owner + 3 isolated standard users)
    r1 = SupabaseAuthManager.create_or_update_user(
        engine, "alessandro", "OwnerSecret99!", role="owner", display_name="Alessandro"
    )
    r2 = SupabaseAuthManager.create_or_update_user(
        engine, "marco", "MarcoPass2026!", role="user", display_name="Marco Rossi"
    )
    r3 = SupabaseAuthManager.create_or_update_user(
        engine, "sara", "SaraPass2026!", role="user", display_name="Sara Bianchi"
    )
    r4 = SupabaseAuthManager.create_or_update_user(
        engine,
        "luca",
        "LucaPass2026!",
        role="user",
        display_name="Luca Verdi",
        custom_db_url="postgres://postgres.lucaref:LucaDbPass@aws-0-eu-west-1.pooler.supabase.com:6543/postgres",
    )

    assert r1["ok"] and r2["ok"] and r3["ok"] and r4["ok"]
    assert r4["has_custom_db"] is True

    users = SupabaseAuthManager.list_users(engine)
    assert len(users) == 4

    # Authenticate each user
    auth_ok = SupabaseAuthManager.authenticate_user("marco", "MarcoPass2026!", engine=engine)
    assert auth_ok["ok"] is True
    assert auth_ok["username"] == "marco"
    assert auth_ok["role"] == "user"

    auth_bad = SupabaseAuthManager.authenticate_user("marco", "WrongPassword", engine=engine)
    assert auth_bad["ok"] is False

    # Verify isolated wealth_profiles were created for marco and sara
    with engine.connect() as conn:
        marco_prof = conn.execute(
            sqlt("SELECT COUNT(*) FROM wealth_profiles WHERE LOWER(owner) = 'marco'")
        ).scalar()
        sara_prof = conn.execute(
            sqlt("SELECT COUNT(*) FROM wealth_profiles WHERE LOWER(owner) = 'sara'")
        ).scalar()
        assert marco_prof == 1
        assert sara_prof == 1

    engine.dispose()


def test_strict_portfolio_id_1_no_leak_between_users(tmp_path: Path, monkeypatch):
    """Verifica che un utente standard ('marco') non veda MAI i conti/spese/obiettivi di portfolio_id = 1 del Titolare."""
    import streamlit as st

    from core.wealth.wealth_db import (
        get_wealth_accounts,
        get_wealth_fixed_expenses,
        get_wealth_goals,
        get_wealth_portfolios,
    )

    db_file = tmp_path / "strict_isolation.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    init_wealth_db(engine)

    # 1. Seed Owner data in portfolio_id = 1
    monkeypatch.setattr(
        st,
        "session_state",
        {"argus_auth_role": "owner", "argus_auth_user": "alessandro", "argus_auth_display_name": "Alessandro (Titolare)"},
        raising=False,
    )
    save_wealth_account(
        engine,
        {
            "portfolio_id": 1,
            "name": "Conto Privato Alessandro",
            "account_type": "checking",
            "institution": "Intesa",
            "currency": "EUR",
            "balance": 150000.0,
        },
    )
    save_wealth_fixed_expense(
        engine,
        {"portfolio_id": 1, "category": "Casa", "note": "Mutuo Privato", "amount": 1200.0, "payment_day": 1},
    )
    save_wealth_goal(
        engine,
        {"portfolio_id": 1, "name": "Villa Privata", "target_amount": 500000.0, "target_date": "2030-01-01"},
    )

    # 2. Register 'marco' (creates his own isolated profile, e.g. profile_id = 2)
    SupabaseAuthManager.create_or_update_user(
        engine, "marco", "MarcoPass2026!", role="user", display_name="Marco Rossi"
    )

    # 3. Switch active session to 'marco' (role = 'user')
    monkeypatch.setattr(
        st,
        "session_state",
        {"argus_auth_role": "user", "argus_auth_user": "marco", "argus_auth_display_name": "Marco Rossi"},
        raising=False,
    )

    marco_profs = get_wealth_portfolios(engine)
    assert len(marco_profs) == 1
    marco_pid = int(marco_profs.iloc[0]["portfolio_id"])
    assert marco_pid != 1

    # Even if marco queries with portfolio_id=None or portfolio_id=1 or his own marco_pid,
    # he must NEVER see Owner's portfolio_id = 1 data!
    assert get_wealth_accounts(engine, portfolio_id=marco_pid).empty
    assert get_wealth_accounts(engine, portfolio_id=1).empty
    assert get_wealth_accounts(engine, portfolio_id=None).empty
    assert get_wealth_fixed_expenses(engine, portfolio_id=marco_pid).empty
    assert get_wealth_goals(engine, portfolio_id=marco_pid).empty

    engine.dispose()


