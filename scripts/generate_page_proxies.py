"""
ARGUS — Page Proxy Generator
Generates lightweight proxies in pages/ and root for full Streamlit Multi-Page App parity.
Ensures both local and Streamlit Cloud environments discover all Risk and Wealth pages.
"""
import os
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SRC_PAGES_DIR = ROOT_DIR / "src" / "pages"
PAGES_DIR = ROOT_DIR / "pages"

PAGES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Generate proxies for all src/pages/*.py
src_pages = sorted([
    f for f in os.listdir(SRC_PAGES_DIR)
    if f.endswith(".py") and not f.startswith("__")
])

for f in src_pages:
    proxy_path = PAGES_DIR / f
    code = f'''"""ARGUS Page Proxy: {f}"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "pages" / Path(__file__).name
runpy.run_path(str(_target), run_name="__main__")
'''
    proxy_path.write_text(code, encoding="utf-8")

# 2. Generate pages/0_Control_Room.py proxy
ctrl_page_proxy = PAGES_DIR / "0_Control_Room.py"
ctrl_page_code = '''"""ARGUS Page Proxy: 0_Control_Room.py"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent.parent / "src" / "0_Control_Room.py"
runpy.run_path(str(_target), run_name="__main__")
'''
ctrl_page_proxy.write_text(ctrl_page_code, encoding="utf-8")

# 3. Generate root 0_Control_Room.py proxy
root_ctrl_proxy = ROOT_DIR / "0_Control_Room.py"
root_ctrl_code = '''"""ARGUS Control Room Entrypoint Proxy"""
import runpy
from pathlib import Path

_target = Path(__file__).resolve().parent / "src" / "0_Control_Room.py"
runpy.run_path(str(_target), run_name="__main__")
'''
root_ctrl_proxy.write_text(root_ctrl_code, encoding="utf-8")

print(f"Successfully generated {len(src_pages)} page proxies in {PAGES_DIR} + root 0_Control_Room.py")
