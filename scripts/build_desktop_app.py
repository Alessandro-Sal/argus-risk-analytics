"""
Script di automazione per la compilazione dell'applicazione Desktop Standalone (.exe)
tramite PyInstaller per ARGUS Risk Analytics Platform.
"""

import os
import sys
import subprocess
import shutil

def build():
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(project_dir)
    
    print("=" * 60)
    print(" Compilazione Desktop App Nativa — ARGUS Risk Analytics Platform")
    print("=" * 60)
    
    # 1. Verifica/Generazione icona
    icon_path = os.path.join(project_dir, "docs", "argus_icon.ico")
    if not os.path.exists(icon_path):
        subprocess.run([sys.executable, "scripts/generate_icon.py"], check=True)

    # 2. Configurazione file .spec per PyInstaller
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Inclusione data files di Streamlit, assets e codice sorgente
datas = [
    ('src', 'src'),
    ('core', 'core'),
    ('docs', 'docs'),
    ('app.py', '.'),
]
datas += collect_data_files('streamlit')

hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'webview',
    'scipy.spatial.transform._rotation_groups',
    'sklearn.utils._typedefs',
    'sqlalchemy.dialects.mysql',
]
hiddenimports += collect_submodules('streamlit')
hiddenimports += collect_submodules('core')

a = Analysis(
    ['desktop_launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter'],
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
    name='ARGUS',
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
    icon=r'{icon_path}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ARGUS_Desktop',
)
"""
    
    spec_file = os.path.join(project_dir, "argus_desktop.spec")
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)
        
    print(f"[1/3] File di specifica generato: {spec_file}")
    
    # 3. Esecuzione di PyInstaller
    print("[2/3] Avvio compilazione PyInstaller (può richiedere fino a 1-2 minuti)...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file]
    
    try:
        subprocess.run(cmd, check=True)
        print("[3/3] Compilazione completata con successo!")
        
        exe_path = os.path.join(project_dir, "dist", "ARGUS_Desktop", "ARGUS.exe")
        print("=" * 60)
        print(f"[OK] ESEGUIBILE PRONTO IN: {exe_path}")
        print("=" * 60)
        
        # 4. Aggiorna collegamento desktop se già esistente
        shortcut_script = os.path.join(project_dir, "scripts", "create_desktop_shortcut.py")
        subprocess.run([sys.executable, shortcut_script], check=False)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore durante la compilazione PyInstaller: {e}")

if __name__ == "__main__":
    build()
