@echo off
echo ============================================================
echo Avvio di ARGUS Risk Analytics Platform — Desktop App
echo ============================================================
cd /d "%~dp0"

if exist "dist\ARGUS_Desktop\ARGUS.exe" (
    echo Avvio eseguibile nativo ARGUS.exe...
    start "" "dist\ARGUS_Desktop\ARGUS.exe"
) else if exist "desktop_launcher.py" (
    echo Avvio applicazione Desktop Nativa via pywebview...
    py desktop_launcher.py
) else if exist "src\0_Control_Room.py" (
    py -m streamlit run src\0_Control_Room.py
) else (
    py -m streamlit run app.py
)
pause
