#!/usr/bin/env python3
# ============================================================
# scripts/migrate_to_supabase.py
# ARGUS — 1-Click Local SQLite -> Supabase Cloud Migration CLI
# Usage:
#   py scripts/migrate_to_supabase.py
#   py scripts/migrate_to_supabase.py --sqlite data/argus_local.db --include-prices
# ============================================================

import argparse
import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.supabase_cloud import (  # noqa: E402
    build_supabase_db_url,
    create_supabase_engine,
    generate_supabase_schema_sql,
    get_supabase_config,
    migrate_local_to_supabase,
    optimize_supabase_storage_footprint,
    test_supabase_connection,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ARGUS 1-Click Migration: Local SQLite -> Supabase PostgreSQL Cloud"
    )
    parser.add_argument(
        "--sqlite",
        default="data/argus_local.db",
        help="Percorso al database SQLite locale sorgente (default: data/argus_local.db)",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="URI PostgreSQL Supabase (default: legge SUPABASE_DB_URL da .env o secrets.toml)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password del DB Supabase per il progetto configurato (es. qsexxzbhtocxvyaijngb)",
    )
    parser.add_argument(
        "--include-prices",
        action="store_true",
        help="Include anche la tabella storica market_prices nella migrazione (opzionale)",
    )
    parser.add_argument(
        "--export-schema",
        default=None,
        help="Salva solo lo schema SQL su file ed esce (es. sql/supabase_schema.sql)",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="UUID dell'utente Supabase proprietario dei dati migrati (per RLS auth.uid())",
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="Username o email dell'owner dei dati migrati",
    )
    args = parser.parse_args()

    if args.export_schema:
        out_path = Path(args.export_schema)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(generate_supabase_schema_sql(), encoding="utf-8")
        print(f"[OK] Schema SQL Supabase esportato in: {out_path}")
        return 0

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    cfg = get_supabase_config()
    target_url = args.db_url
    if not target_url and args.password:
        target_url = build_supabase_db_url(
            project_ref=cfg.get("project_ref", "qsexxzbhtocxvyaijngb"),
            db_password=args.password,
            pooler_host=cfg.get("pooler_host", "aws-0-eu-west-1.pooler.supabase.com"),
        )
    if not target_url:
        target_url = cfg.get("db_url") or os.getenv("SUPABASE_DB_URL")
    if not target_url:
        print(
            "[ERRORE] Nessun SUPABASE_DB_URL o SUPABASE_DB_PASSWORD trovato.\n"
            "Configura SUPABASE_DB_PASSWORD nel file .env oppure passa --password '<LA_TUA_PASSWORD>'."
        )
        return 1

    print("=" * 68)
    print("  ARGUS CLOUD MIGRATION — SQLITE LOCALE -> SUPABASE POSTGRESQL")
    print("=" * 68)
    diag = test_supabase_connection(target_url)
    if not diag.get("ok"):
        print(f"[ERRORE] Connessione a Supabase fallita: {diag.get('error')}")
        return 1

    print(f"  Target Cloud : {diag.get('masked_url')}")
    print(f"  Server       : {diag.get('pg_version')} (DB: {diag.get('current_db')})")
    print(f"  Latenza TLS  : {diag.get('latency_ms')} ms")
    print("-" * 68)

    res = migrate_local_to_supabase(
        sqlite_path=args.sqlite,
        target_db_url=target_url,
        include_market_prices=args.include_prices,
        user_id=args.user_id,
        owner=args.owner,
    )

    print(f"  Totale Righe Migrate : {res.get('total_rows_migrated', 0)}")
    for tbl, cnt in res.get("tables", {}).items():
        print(f"    - {tbl:<32} : {cnt}")

    eng = create_supabase_engine(target_url)
    try:
        quota = optimize_supabase_storage_footprint(eng)
        print("-" * 68)
        print(
            f"  Spazio Free Tier Usato: {quota['used_mb']:.2f} MB / {quota['quota_mb']:.0f} MB "
            f"({quota['usage_pct']:.1f}% - {quota['status_tier']})"
        )
    finally:
        eng.dispose()

    print("=" * 68)
    print("  [COMPLETATO] Migrazione Cloud Supabase terminata con successo!")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
