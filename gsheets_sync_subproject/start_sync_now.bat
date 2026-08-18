@echo off
title ARGUS Risk Analytics - Synchronize Google Sheets Now (Stocks & Crypto)
echo ======================================================================
echo ARGUS Risk Analytics - Sincronizzazione Immediata Google Sheets
echo Estrazione Duale: Stocks ("History B/S Stocks") e Crypto ("History B/S Crypto")
echo ======================================================================
echo.
cd /d "%~dp0"
py sync_google_sheets.py --sheet "My All financial Statements" --mode both
echo.
echo [OK] Sincronizzazione completata! Premi un tasto per chiudere.
pause


