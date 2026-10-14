"""ARGUS Control Room Entrypoint Proxy"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent / "src" / "0_Control_Room.py"
runpy.run_path(str(_target), run_name="__main__")
