"""
ARGUS Risk Analytics - Daily ETL Daemon Scheduler
=================================================
Esegue la sincronizzazione automatica ogni giorno ad un orario prestabilito (es. 02:00 di notte).
"""

import os
import sys
import time
import datetime
import argparse

SUBPROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SUBPROJECT_DIR)
sys.path.append(PROJECT_ROOT)
sys.path.append(SUBPROJECT_DIR)

from sync_google_sheets import run_daily_pipeline


def run_scheduler(sheet_name: str, tab_name: str, run_at_time: str = "02:00"):
    """Loop infinito che esegue la pipeline ogni giorno all'orario specificato."""
    target_hour, target_minute = map(int, run_at_time.split(":"))
    print(f"⏰ Daemon Scheduler ARGUS avviato per lo Spreadsheet '{sheet_name}' (Foglio: '{tab_name}').")
    print(f"📅 Orario quotidiano schedulato: {run_at_time}")

    while True:
        now = datetime.datetime.now()
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if now >= target_time:
            target_time += datetime.timedelta(days=1)

        seconds_until_run = (target_time - now).total_seconds()
        hours_until_run = seconds_until_run / 3600.0

        print(f"\n⏳ Prossima esecuzione programmata per: {target_time.strftime('%Y-%m-%d %H:%M:%S')} (tra {hours_until_run:.2f} ore)")
        print("💡 Premi Ctrl+C per arrestare il daemon.")

        time.sleep(min(seconds_until_run, 3600))  # check hourly

        now_check = datetime.datetime.now()
        if now_check >= target_time:
            print(f"\n🚀 [CRON TRIGGER {now_check.strftime('%Y-%m-%d %H:%M:%S')}] Avvio sincronizzazione quotidiana...")
            try:
                success = run_daily_pipeline(sheet_name, tab_name)
                if success:
                    print("✅ Sincronizzazione completata con successo ed esportata nel Data Warehouse DB.")
                else:
                    print("❌ Si sono verificati errori durante la sincronizzazione.")
            except Exception as e:
                print(f"🔴 Eccezione non gestita durante il cron run: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARGUS Daily ETL Cron Scheduler Daemon")
    parser.add_argument("--sheet", type=str, required=True, help="Nome o ID dello Spreadsheet Google Sheets")
    parser.add_argument("--tab", type=str, default="History B/S stocks", help="Nome del foglio (default: History B/S stocks)")
    parser.add_argument("--time", type=str, default="02:00", help="Orario giornaliero in formato HH:MM (default: 02:00)")

    args = parser.parse_args()
    run_scheduler(args.sheet, args.tab, args.time)
