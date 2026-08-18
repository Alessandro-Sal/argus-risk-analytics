#!/bin/bash
echo "======================================================================"
echo "👁️ ARGUS Risk Analytics - Daily Google Sheets Sync Daemon (Stocks & Crypto)"
echo "======================================================================"
echo ""

read -p "Inserisci il NOME o l'URL del tuo Google Sheet (default: My All financial Statements): " SHEET_NAME
SHEET_NAME=${SHEET_NAME:-"My All financial Statements"}

echo ""
echo "Avvio del daemon in corso per Stocks e Crypto... Orario predefinito: 02:00 ogni notte."
echo ""

python3 run_daily_scheduler.py --sheet "$SHEET_NAME" --mode both --time "02:00"

