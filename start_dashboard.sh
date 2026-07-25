#!/usr/bin/env bash
# Script di avvio per ARGUS Risk Analytics Platform su Linux/macOS

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "👁️ Avvio di ARGUS Risk Analytics Platform..."

if [ -f "src/0_Control_Room.py" ]; then
    streamlit run src/0_Control_Room.py
else
    streamlit run app.py
fi
