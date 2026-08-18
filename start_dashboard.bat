@echo off
setlocal enabledelayedexpansion
title ARGUS — Risk Analytics Platform
echo ============================================================
echo  Avvio di ARGUS Risk Analytics Platform
echo ============================================================
cd /d "%~dp0"

:: 1. Rilevamento interprete Python valido sul sistema
set "PY_CMD="

:: Prova comando 'py' (Python Launcher standard Windows)
py --version >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PY_CMD=py"
    goto :PYTHON_FOUND
)

:: Prova comando 'python'
python --version >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PY_CMD=python"
    goto :PYTHON_FOUND
)

:: Prova percorsi di installazione tipici Windows
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :PYTHON_FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :PYTHON_FOUND
)

:PYTHON_FOUND
if "%PY_CMD%"=="" (
    echo.
    echo [ERRORE CRITICO] Python non e' stato trovato nel sistema!
    echo Per favore installa Python da https://www.python.org/downloads/
    echo e assicurati di spuntare l'opzione "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [INFO] Interprete Python rilevato con successo: %PY_CMD%

:: 2. Tentativo avvio Finestra Desktop Nativa (pywebview)
if exist "desktop_launcher.py" (
    echo [INFO] Avvio applicazione Desktop nativa...
    "%PY_CMD%" desktop_launcher.py
    if !ERRORLEVEL! EQU 0 goto :DONE
    echo.
    echo [AVVISO] Chiusura o fallback su interfaccia browser web...
)

:: 3. Avvio diretto Streamlit nel browser predefinito
echo [INFO] Avvio server Streamlit nel browser web predefinito...
if exist "src\0_Control_Room.py" (
    "%PY_CMD%" -m streamlit run src\0_Control_Room.py --browser.gatherUsageStats=false
) else (
    "%PY_CMD%" -m streamlit run app.py --browser.gatherUsageStats=false
)

:DONE
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo [ERRORE] Il server o l'applicazione si e' interrotta con codice di errore !ERRORLEVEL!.
    pause
)
