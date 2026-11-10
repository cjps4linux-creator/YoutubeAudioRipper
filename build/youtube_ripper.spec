# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec for YouTube Audio Ripper.
Build: pyinstaller build/youtube_ripper.spec
"""

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ["rip_gui.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("android/static", "android/static"),
        ("README.md", "."),
        ("LICENSE", "."),
    ],
    hiddenimports=[
        "customtkinter",
        "yt_dlp",
        "ffmpeg",
        "logging.handlers",
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTube Audio Ripper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YouTube Audio Ripper",
)

app = BUNDLE(
    coll,
    name="YouTube Audio Ripper.app",
    icon="assets/icon.icns",
    bundle_identifier="com.cjps4linux.youtube-audio-ripper",
)
