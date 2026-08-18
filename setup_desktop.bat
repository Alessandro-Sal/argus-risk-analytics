@echo off
echo ============================================================
echo Setup Applicazione Desktop Nativa — ARGUS Risk Analytics
echo ============================================================
cd /d "%~dp0"

echo [1/2] Installazione dipendenze necessarie...
py -m pip install -r requirements.txt

echo.
echo [2/2] Creazione collegamento con icona 'Occhio di Argus' sul Desktop...
py scripts/create_desktop_shortcut.py

echo.
echo ============================================================
echo Setup completato! Troverai l'icona ARGUS sul tuo Desktop.
echo ============================================================
pause
