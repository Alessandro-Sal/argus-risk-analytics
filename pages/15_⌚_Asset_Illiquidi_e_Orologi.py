"""ARGUS Page Proxy: 15_⌚_Asset_Illiquidi_e_Orologi.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
