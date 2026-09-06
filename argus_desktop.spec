# -*- mode: python ; coding: utf-8 -*-
# ==============================================================================
# argus_desktop.spec — Hardened PyInstaller Specification for ARGUS Desktop
# Optimized bundle size, portable paths for CI/CD, and full template assets
# ==============================================================================

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Risoluzione portabile della root del progetto (senza path hardcodati)
spec_dir = os.path.abspath(SPECPATH) if "SPECPATH" in globals() else os.path.abspath(".")

# 1. Riconoscimento Icona Portabile
icon_candidates = [
    os.path.join(spec_dir, "docs", "argus_icon.ico"),
    os.path.join(spec_dir, "docs", "argus_logo.png"),
]
icon_path = next((p for p in icon_candidates if os.path.exists(p)), None)

# 2. Inclusione Dati, Template CSV e Sorgenti
datas = [
    (os.path.join(spec_dir, "src"), "src"),
    (os.path.join(spec_dir, "core"), "core"),
    (os.path.join(spec_dir, "docs"), "docs"),
    (os.path.join(spec_dir, "app.py"), "."),
]

# Template di importazione Wealth
templates_dir = os.path.join(spec_dir, "data", "wealth")
if os.path.exists(templates_dir):
    datas.append((templates_dir, os.path.join("data", "wealth")))

# Asset essenziali di Streamlit e Altair
datas += collect_data_files("streamlit")
datas += collect_data_files("altair")

# 3. Hidden Imports per Esecuzione Dinamica & WebView2
hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_expressions",
    "webview",
    "pydantic",
    "pydantic_core",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.mysql",
    "scipy.spatial.transform._rotation_groups",
    "sklearn.utils._typedefs",
    "duckdb",
    "gzip",
    "shutil",
    "hashlib",
]
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("core")

# 4. Esclusioni Selettive per Ridurre il Bundle Size (Risparmio > 800 MB)
excludes = [
    "tkinter", "tcl", "_tkinter",
    "torch", "torchvision", "torchaudio",
    "tensorflow", "tensorboard", "keras",
    "IPython", "jupyter", "jupyter_core", "notebook", "ipykernel", "nbformat",
    "matplotlib.tests", "numpy.tests", "scipy.tests", "pandas.tests",
    "pytest", "_pytest", "unittest",
    "sphinx", "pygments", "docutils",
    "curses", "tornado.test",
]

a = Analysis(
    [os.path.join(spec_dir, "desktop_launcher.py")],
    pathex=[spec_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ARGUS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python*.dll"],
    name="ARGUS_Desktop",
)
