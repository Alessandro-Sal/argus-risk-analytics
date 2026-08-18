@echo off
title ARGUS Risk Analytics - Daily Google Sheets Sync Daemon (Stocks & Crypto)
echo ======================================================================
echo ARGUS Risk Analytics - Daemon Giornaliero per "My All financial Statements"
echo Sincronizzazione duale automatica: Stocks e Crypto
echo ======================================================================
echo.
cd /d "%~dp0"
echo Avvio sincronizzazione automatica programmata...
py run_daily_scheduler.py --sheet "My All financial Statements" --mode both --stocks-tab "History B/S Stocks" --crypto-tab "History B/S Crypto" --time "18:00"
pause


