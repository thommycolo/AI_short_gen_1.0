# -*- mode: python ; coding: utf-8 -*-
"""
AI Short Generator 1.0 - PyInstaller .spec Configuration File
Architettura: Native Windows 64-bit Desktop Application (--onedir)
Zero WebApp, Zero Electron, Zero %TEMP% bloat.
"""

import sys
import os
from pathlib import Path

block_cipher = None

project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, 'assets'), 'assets'),
]

# Aggiungi cartella app_data con DB template se presente
app_data_path = os.path.join(project_dir, 'app_data')
if os.path.exists(app_data_path):
    datas.append((app_data_path, 'app_data'))

hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'sqlite3',
    'json',
    'multiprocessing',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'inflect',
    'yt_dlp',
]

binaries = []

# Se ffmpeg è presente in app_data/bin/, includilo nei binaries
ffmpeg_bin = os.path.join(project_dir, 'app_data', 'bin')
if os.path.exists(ffmpeg_bin):
    for f in os.listdir(ffmpeg_bin):
        if f.endswith('.exe'):
            binaries.append((os.path.join(ffmpeg_bin, f), 'app_data/bin'))

a = Analysis(
    ['app/main.py'],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'IPython', 'notebook', 'pytest'],
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
    name='AI_Short_Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Nessuna console nera - Interfaccia GUI pura
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'assets', 'icons', 'app.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_Short_Generator',
)

