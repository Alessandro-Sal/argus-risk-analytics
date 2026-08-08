@echo off
title ARGUS Risk Analytics - Daily Google Sheets Sync Daemon
echo ======================================================================
echo ARGUS Risk Analytics - Daemon Giornaliero per "My All financial Statements"
echo ======================================================================
echo.
cd /d "%~dp0"
echo Avvio sincronizzazione automatica programmata...
py run_daily_scheduler.py --sheet "My All financial Statements" --tab "History B/S stocks" --time "18:00"
pause

