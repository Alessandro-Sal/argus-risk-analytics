# ============================================================
# app.py (Entry point alias)
# ARGUS Risk Analytics Platform — Control Room
# ============================================================

import runpy
import os

entry_point = "src/0_Control_Room.py" if os.path.exists("src/0_Control_Room.py") else "0_Control_Room.py"
runpy.run_path(entry_point, run_name="__main__")