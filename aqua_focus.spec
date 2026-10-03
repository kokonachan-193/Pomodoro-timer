# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Aqua Focus
# Bundles imageio-ffmpeg binaries so users need no separate ffmpeg install.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
root = Path(SPECPATH)

# Ship ffmpeg binary inside the app (_internal/imageio_ffmpeg/binaries/...)
ffmpeg_datas = collect_data_files("imageio_ffmpeg")

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'assets'), 'assets'),
        (str(root / 'docs'), 'docs'),
        (str(root / 'i18n.py'), '.'),
        (str(root / 'sitecustomize.py'), '.'),
        (str(root / 'pc_runtime_fixes.py'), '.'),
        (str(root / 'pc_water_fixes.py'), '.'),
    ] + ffmpeg_datas,
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'numpy',
        'sounddevice',
        'yt_dlp',
        'imageio_ffmpeg',
        'pygame',
        'certifi',
        'i18n',
        'agiu',
        'settings_store',
        'pc_runtime_fixes',
        'pc_water_fixes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(root / 'pyinstaller_runtime_hook.py')],
    excludes=[],
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
    name='AquaFocus',
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
    icon=str(root / 'assets' / 'icons' / 'aqua-focus.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AquaFocus',
)
