#!/bin/bash
echo "======================================================================"
echo "👁️ ARGUS Risk Analytics - Daily Google Sheets Sync Daemon"
echo "======================================================================"
echo ""

read -p "Inserisci il NOME o l'URL del tuo Google Sheet: " SHEET_NAME

if [ -z "$SHEET_NAME" ]; then
    echo "[ERRORE] Il nome dello Spreadsheet non può essere vuoto."
    exit 1
fi

echo ""
echo "Avvio del daemon in corso... Orario predefinito: 02:00 ogni notte."
echo ""

python3 run_daily_scheduler.py --sheet "$SHEET_NAME" --tab "History B/S stocks" --time "02:00"
