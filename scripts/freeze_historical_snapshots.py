# ============================================================
# scripts/freeze_historical_snapshots.py
# ARGUS — Batch Freezing of Year-End Wealth Snapshots (2021-2025)
# ============================================================

import os
import sys
from datetime import date

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.fetcher import get_engine
from core.wealth.wealth_snapshot import get_wealth_snapshots_history, save_wealth_snapshot_to_db


def freeze_snapshots(portfolio_id: int = 1):
    print(f"=== Congelamento Snapshot di Chiusura Esercizi (2021-2025) - Portfolio {portfolio_id} ===")
    
    engines = []
    try:
        eng_sqlite = get_engine(database="wealth", offline=True)
        engines.append(("SQLite", eng_sqlite))
    except Exception as e:
        print(f"Errore caricamento SQLite: {e}")

    try:
        eng_mysql = get_engine(database="investment_risk_bi", offline=False)
        engines.append(("MySQL", eng_mysql))
    except Exception as e:
        print(f"MySQL non raggiungibile o offline: {e}")

    years_to_freeze = [2021, 2022, 2023, 2024, 2025]

    for eng_label, eng in engines:
        print(f"\n--- Elaborazione su {eng_label} ---")
        try:
            with eng.connect() as conn:
                existing_dates = set()
                try:
                    res = conn.execute(
                        text("SELECT snapshot_date FROM wealth_networth_snapshots WHERE portfolio_id = :pid"),
                        {"pid": portfolio_id}
                    ).fetchall()
                    existing_dates = {str(r[0])[:10] for r in res}
                except Exception:
                    pass

            for yr in years_to_freeze:
                target_date_str = f"{yr}-12-31"
                if target_date_str in existing_dates:
                    print(f"[{yr}] Snapshot 31/12/{yr} già presente nel database. Saltato.")
                    continue

                d_val = date(yr, 12, 31)
                s_name = f"Chiusura Esercizio {yr}"
                notes = f"Snapshot ufficiale di chiusura bilancio personale esercizio {yr}"
                snap_id = save_wealth_snapshot_to_db(
                    engine=eng,
                    portfolio_id=portfolio_id,
                    snapshot_name=s_name,
                    snapshot_date_val=d_val,
                    notes=notes
                )
                print(f"[{yr}] Snapshot 31/12/{yr} congelato con successo (ID: {snap_id})")

            df_hist = get_wealth_snapshots_history(eng, portfolio_id=portfolio_id)
            if not df_hist.empty:
                print("\nSnapshot registrati in archivio:")
                cols = [c for c in ["snapshot_id", "snapshot_date", "snapshot_name", "total_net_worth"] if c in df_hist.columns]
                print(df_hist[cols].to_string(index=False))

        except Exception as e:
            print(f"Errore su {eng_label}: {e}")
            import traceback
            traceback.print_exc()

    print("\n=== Operazione completata ===")


if __name__ == "__main__":
    freeze_snapshots(portfolio_id=1)
