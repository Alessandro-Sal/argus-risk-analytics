import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text as sqlt

# Set utf-8 stdout encoding for Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()
from core.fetcher import get_engine

def run_portfolio_deduplication(db_user=None, db_pass=None, db_host=None, db_port=None, db_name=None):
    db_user = db_user or os.getenv("DB_USER", "root")
    db_pass = db_pass or os.getenv("DB_PASS", "root")
    db_host = db_host or os.getenv("DB_HOST", "localhost")
    db_port = int(db_port or os.getenv("DB_PORT", 3306))
    db_name = db_name or os.getenv("DB_NAME", "wealth")

    print(f"=== BONIFICA DATABASE: {db_host}:{db_port}/{db_name} ===")
    try:
        engine = get_engine(db_user, db_pass, db_host, db_port, db_name)
    except Exception as e:
        print(f"[-] Errore di connessione a MySQL ({db_name}): {e}")
        return False

    with engine.begin() as conn:
        try:
            conn.execute(sqlt("SET FOREIGN_KEY_CHECKS = 0;"))
        except Exception:
            pass

        print("[*] Controllo duplicati nella tabella 'portfolios'...")
        duplicates = conn.execute(sqlt("""
            SELECT name, COUNT(*) as cnt, MIN(portfolio_id) as min_id
            FROM portfolios
            GROUP BY name
            HAVING COUNT(*) > 1
        """)).fetchall()

        if not duplicates:
            print("[+] Nessun portafoglio duplicato trovato. Il database e' gia' pulito e allineato!")
        else:
            print(f"[!] Trovati {len(duplicates)} gruppi di portafogli duplicati:")
            for p_name, cnt, min_id in duplicates:
                print(f"   [>] Portafoglio: '{p_name}' -> {cnt} record totali (ID canonico mantenuto: {min_id})")
                
                other_rows = conn.execute(
                    sqlt("SELECT portfolio_id FROM portfolios WHERE name = :n AND portfolio_id != :min_id"),
                    {"n": p_name, "min_id": min_id}
                ).fetchall()
                other_ids = [r[0] for r in other_rows]
                
                for old_id in other_ids:
                    # Rimappa transactions e snapshots sul canonical ID
                    tx_updated = conn.execute(sqlt("UPDATE transactions SET portfolio_id = :min_id WHERE portfolio_id = :old_id"), {"min_id": min_id, "old_id": old_id}).rowcount
                    snaps_updated = conn.execute(sqlt("UPDATE portfolio_snapshots SET portfolio_id = :min_id WHERE portfolio_id = :old_id"), {"min_id": min_id, "old_id": old_id}).rowcount
                    conn.execute(sqlt("DELETE FROM portfolios WHERE portfolio_id = :old_id"), {"old_id": old_id})
                    print(f"      -> Rimappato ID {old_id} su ID {min_id} ({tx_updated} transazioni, {snaps_updated} snapshots aggiornati) ed eliminato ID {old_id}.")

        # Aggiunta vincolo UNIQUE su portfolios(name)
        try:
            conn.execute(sqlt("ALTER TABLE portfolios ADD UNIQUE KEY uq_portfolio_name (name);"))
            print("[+] Vincolo UNIQUE (uq_portfolio_name) applicato con successo su portfolios(name).")
        except Exception as e:
            # Se esiste già, ignora
            pass

        try:
            conn.execute(sqlt("SET FOREIGN_KEY_CHECKS = 1;"))
        except Exception:
            pass

    # Riepilogo finale
    with engine.connect() as conn:
        final_ports = conn.execute(sqlt("SELECT portfolio_id, name, owner, base_currency, created_at FROM portfolios ORDER BY portfolio_id ASC")).fetchall()
        print(f"\n[*] Portafogli attivi post-bonifica ({len(final_ports)} totali):")
        for p in final_ports:
            cnt_snaps = conn.execute(sqlt("SELECT COUNT(*) FROM portfolio_snapshots WHERE portfolio_id = :pid"), {"pid": p[0]}).scalar()
            cnt_tx = conn.execute(sqlt("SELECT COUNT(*) FROM transactions WHERE portfolio_id = :pid"), {"pid": p[0]}).scalar()
            print(f"   [#] ID {p[0]}: '{p[1]}' (Owner: {p[2]}, Cur: {p[3]}) -> {cnt_snaps} snapshots, {cnt_tx} transazioni collegate.")

    print("\n[OK] Bonifica completata con successo al 100%!")
    return True

if __name__ == '__main__':
    run_portfolio_deduplication()
