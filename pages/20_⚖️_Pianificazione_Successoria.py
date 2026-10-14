"""ARGUS Page Proxy: 20_⚖️_Pianificazione_Successoria.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
