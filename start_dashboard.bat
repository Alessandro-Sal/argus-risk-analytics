@echo off
echo Avvio di ARGUS Risk Analytics Platform...
cd /d "%~dp0"
if exist "src\0_Control_Room.py" (
    py -m streamlit run src\0_Control_Room.py
) else if exist "..\src\0_Control_Room.py" (
    cd /d "%~dp0\.."
    py -m streamlit run src\0_Control_Room.py
) else (
    py -m streamlit run app.py
)
pause
