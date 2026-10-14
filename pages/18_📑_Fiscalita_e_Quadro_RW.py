"""ARGUS Page Proxy: 18_📑_Fiscalita_e_Quadro_RW.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
