# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['converter.py'],
    pathex=[],
    binaries=[('ffmpeg/ffmpeg.exe', '.')],
    datas=[],
    hiddenimports=['tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipped_data,
    a.datas,
    [],
    name='MOV2WebM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
