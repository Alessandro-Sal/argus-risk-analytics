@echo off
title ARGUS Risk Analytics - Synchronize Google Sheets Now
echo ======================================================================
echo ARGUS Risk Analytics - Sincronizzazione Immediata Google Sheets
echo ======================================================================
echo.
cd /d "%~dp0"
py sync_google_sheets.py --sheet "My All financial Statements" --tab "History B/S stocks"
echo.
echo [OK] Sincronizzazione completata! Premi un tasto per chiudere.
pause

