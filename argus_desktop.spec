# -*- mode: python ; coding: utf-8 -*-

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
    hooksconfig={},
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
    icon=r'C:\Users\Alessandro Personale\Desktop\Progetti Personali e Corsi\CAPSTONE PROJECT\docs\argus_icon.ico',
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
