"""
ARGUS Risk Analytics - Daily ETL Daemon Scheduler (Stocks & Crypto)
===================================================================
Esegue la sincronizzazione automatica ogni giorno ad un orario prestabilito (es. 02:00 di notte),
estraendo sia Stocks sia Crypto e separandoli nel Data Warehouse DB.
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

from sync_google_sheets import (
    run_daily_pipeline,
    DEFAULT_SPREADSHEET,
    DEFAULT_STOCKS_TAB,
    DEFAULT_CRYPTO_TAB
)


def run_scheduler(
    sheet_name: str,
    mode: str = "both",
    stocks_tab: str = DEFAULT_STOCKS_TAB,
    crypto_tab: str = DEFAULT_CRYPTO_TAB,
    run_at_time: str = "02:00"
):
    """Loop infinito che esegue la pipeline ogni giorno all'orario specificato."""
    target_hour, target_minute = map(int, run_at_time.split(":"))
    print(f"⏰ Daemon Scheduler ARGUS avviato per lo Spreadsheet '{sheet_name}'.")
    print(f"📊 Modalità di estrazione: {mode.upper()} (Stocks: '{stocks_tab}', Crypto: '{crypto_tab}')")
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
                success = run_daily_pipeline(
                    spreadsheet_identifier=sheet_name,
                    mode=mode,
                    stocks_tab=stocks_tab,
                    crypto_tab=crypto_tab
                )
                if success:
                    print("✅ Sincronizzazione completata con successo ed esportata nel Data Warehouse DB.")
                else:
                    print("❌ Si sono verificati errori durante la sincronizzazione.")
            except Exception as e:
                print(f"🔴 Eccezione non gestita durante il cron run: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARGUS Daily ETL Cron Scheduler Daemon")
    parser.add_argument("--sheet", type=str, default=DEFAULT_SPREADSHEET, help="Nome o ID dello Spreadsheet Google Sheets")
    parser.add_argument("--mode", type=str, default="both", choices=["both", "stocks", "crypto", "custom"], help="Modalità (default: both)")
    parser.add_argument("--stocks-tab", type=str, default=DEFAULT_STOCKS_TAB, help=f"Nome del foglio Stocks (default: {DEFAULT_STOCKS_TAB})")
    parser.add_argument("--crypto-tab", type=str, default=DEFAULT_CRYPTO_TAB, help=f"Nome del foglio Crypto (default: {DEFAULT_CRYPTO_TAB})")
    parser.add_argument("--tab", type=str, default=None, help="Nome del foglio singolo per retrocompatibilità")
    parser.add_argument("--time", type=str, default="02:00", help="Orario giornaliero in formato HH:MM (default: 02:00)")

    args = parser.parse_args()
    if args.tab:
        run_scheduler(args.sheet, mode="custom", stocks_tab=args.tab, crypto_tab=args.tab, run_at_time=args.time)
    else:
        run_scheduler(args.sheet, mode=args.mode, stocks_tab=args.stocks_tab, crypto_tab=args.crypto_tab, run_at_time=args.time)

