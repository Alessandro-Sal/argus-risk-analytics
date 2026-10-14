"""ARGUS Page Proxy: 17_🔥_Indipendenza_Finanziaria_e_FIRE.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
