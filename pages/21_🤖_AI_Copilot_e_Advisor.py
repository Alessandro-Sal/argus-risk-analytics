"""ARGUS Page Proxy: 21_🤖_AI_Copilot_e_Advisor.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
