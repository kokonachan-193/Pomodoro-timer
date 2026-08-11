# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Aqua Focus (Windows / macOS / Linux)
# Bundles imageio-ffmpeg so end users need no separate ffmpeg install.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
root = Path(SPECPATH)

ffmpeg_datas = collect_data_files("imageio_ffmpeg")

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "assets"), "assets"),
        (str(root / "docs"), "docs"),
        (str(root / "i18n.py"), "."),
    ]
    + ffmpeg_datas,
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
        "numpy",
        "sounddevice",
        "yt_dlp",
        "imageio_ffmpeg",
        "pygame",
        "certifi",
        "i18n",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_ico = str(root / "assets" / "icons" / "aqua-focus.ico")
icon_icns = root / "build" / "AquaFocus.icns"
icon_arg = str(icon_icns) if icon_icns.exists() else icon_ico

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AquaFocus",
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
    icon=icon_arg if Path(icon_arg).exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AquaFocus",
)

# macOS: ship as .app for drag-and-drop install
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AquaFocus.app",
        icon=icon_arg if Path(icon_arg).exists() else None,
        bundle_identifier="com.kokona.aquafocus",
        info_plist={
            "CFBundleName": "Aqua Focus",
            "CFBundleDisplayName": "Aqua Focus",
            "NSHighResolutionCapable": True,
        },
    )
