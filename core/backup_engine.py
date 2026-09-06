# ============================================================
# core/backup_engine.py
# ARGUS — Database Backup, Versioning & Disaster Recovery Engine
# Zero-Downtime Hot Backup (SQLite Online Backup API), Integrity Check & Point-In-Time Rollback
# ============================================================

import os
import gzip
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("argus.backup")

DEFAULT_BACKUP_DIR = Path("data/backups")
DEFAULT_DB_FILE = Path("data/argus_local.db")


def verify_db_integrity(db_path: Path) -> bool:
    """
    Verifica l'integrità strutturale del database SQLite tramite PRAGMA integrity_check.
    Restituisce True se integro ('ok'), solleva eccezione altrimenti.
    """
    if not db_path.exists():
        return False

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        res = cursor.fetchone()
        status = res[0] if res else "failed"
        if status != "ok":
            logger.error("Integrità database compromessa su %s: %s", db_path, status)
            return False
        return True
    except Exception as e:
        logger.error("Errore durante l'integrity check su %s: %s", db_path, e)
        return False
    finally:
        conn.close()


def perform_hot_backup(
    db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
    max_retention_days: int = 30
) -> Path:
    """
    Esegue un backup online atomico e consistente di SQLite senza bloccare letture/scritture.
    1. Esegue PRAGMA wal_checkpoint(TRUNCATE) per svuotare il Write-Ahead Log.
    2. Utilizza l'API nativa sqlite3.Connection.backup() a caldo.
    3. Esegue un integrity check sul file di destinazione.
    4. Comprime l'archivio con gzip.
    5. Esegue il pruning automatico dei backup più vecchi di max_retention_days.
    """
    target_src = db_path if db_path is not None else DEFAULT_DB_FILE
    target_dir = backup_dir if backup_dir is not None else DEFAULT_BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if not target_src.exists():
        # Se il database principale non esiste ancora su disco, crea una cartella e un db minimale
        target_src.parent.mkdir(parents=True, exist_ok=True)
        init_conn = sqlite3.connect(str(target_src))
        init_conn.execute("CREATE TABLE IF NOT EXISTS _system_ping (id INTEGER PRIMARY KEY);")
        init_conn.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_backup_file = target_dir / f"argus_backup_{timestamp}.db"
    compressed_file = target_dir / f"argus_backup_{timestamp}.db.gz"

    # 1. Checkpoint WAL preventivo
    src_conn = sqlite3.connect(str(target_src), timeout=15.0)
    try:
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception as e:
        logger.warning("WAL checkpoint warning (continuo comunque): %s", e)

    # 2. SQLite Online Backup API
    dest_conn = sqlite3.connect(str(temp_backup_file))
    try:
        with dest_conn:
            src_conn.backup(dest_conn, pages=250)
    finally:
        dest_conn.close()
        src_conn.close()

    # 3. Integrity Check
    if not verify_db_integrity(temp_backup_file):
        if temp_backup_file.exists():
            temp_backup_file.unlink()
        raise RuntimeError(f"Backup integrity verification failed per {temp_backup_file}")

    # 4. Compressione Gzip
    with open(temp_backup_file, "rb") as f_in, gzip.open(compressed_file, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out)

    # Rimozione file intermedio non compresso
    if temp_backup_file.exists():
        temp_backup_file.unlink()

    # 5. Pruning retention
    prune_old_backups(target_dir, max_retention_days)

    logger.info("Hot Backup creato con successo: %s", compressed_file)
    return compressed_file


def restore_snapshot(
    backup_archive_path: Path,
    target_db_path: Optional[Path] = None
) -> bool:
    """
    Ripristina il database a partire da un archivio compresso .db.gz.
    Crea preliminarmente una copia di emergenza (.emergency_pre_restore) e valida
    l'integrità del database prima di renderlo operativo.
    """
    dest_db = target_db_path if target_db_path is not None else DEFAULT_DB_FILE

    if not backup_archive_path.exists():
        raise FileNotFoundError(f"File di backup non trovato: {backup_archive_path}")

    emergency_copy = dest_db.with_suffix(".emergency_pre_restore")
    if dest_db.exists():
        shutil.copy2(dest_db, emergency_copy)

    temp_restored = dest_db.with_suffix(".tmp_restore")
    try:
        with gzip.open(backup_archive_path, "rb") as f_in, open(temp_restored, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # Validazione strutturale
        if not verify_db_integrity(temp_restored):
            raise RuntimeError(f"Snapshot non integro o corrotto: {backup_archive_path}")

        # Sostituzione atomica del file DB
        shutil.move(str(temp_restored), str(dest_db))

        # Pulizia file WAL/SHM associati
        for suffix in ["-wal", "-shm"]:
            wal_file = Path(f"{dest_db}{suffix}")
            if wal_file.exists():
                try:
                    wal_file.unlink()
                except Exception:
                    pass

        if emergency_copy.exists():
            emergency_copy.unlink()

        logger.info("Database ripristinato con successo dallo snapshot: %s", backup_archive_path)
        return True

    except Exception as e:
        logger.error("Errore durante il ripristino del database: %s", e)
        # Rollback d'emergenza
        if emergency_copy.exists():
            shutil.copy2(emergency_copy, dest_db)
            emergency_copy.unlink()
        if temp_restored.exists():
            temp_restored.unlink()
        raise


def list_available_backups(backup_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Restituisce l'elenco cronologico di tutti i backup disponibili con metadati e dimensioni."""
    target_dir = backup_dir if backup_dir is not None else DEFAULT_BACKUP_DIR
    if not target_dir.exists():
        return []

    backups = []
    for f in sorted(target_dir.glob("argus_backup_*.db.gz"), reverse=True):
        try:
            stat = f.stat()
            backups.append({
                "path": str(f.resolve()),
                "filename": f.name,
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size_kb": round(stat.st_size / 1024.0, 2),
                "timestamp_slug": f.name.replace("argus_backup_", "").replace(".db.gz", "")
            })
        except Exception:
            pass
    return backups


def prune_old_backups(backup_dir: Path, max_retention_days: int = 30) -> int:
    """Elimina i file di backup più vecchi di max_retention_days."""
    if not backup_dir.exists() or max_retention_days <= 0:
        return 0

    now = datetime.now()
    pruned_count = 0
    for f in backup_dir.glob("argus_backup_*.db.gz"):
        try:
            age_days = (now - datetime.fromtimestamp(f.stat().st_mtime)).days
            if age_days > max_retention_days:
                f.unlink()
                pruned_count += 1
        except Exception:
            pass
    return pruned_count
