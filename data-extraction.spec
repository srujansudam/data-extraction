# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('data_extraction')
hiddenimports += collect_submodules('cryptography')
hiddenimports += collect_submodules('cffi')
hiddenimports += collect_submodules('oracledb')

try:
    hiddenimports += collect_submodules('bcrypt')
except Exception:
    pass

binaries = []
binaries += collect_dynamic_libs('cryptography')
binaries += collect_dynamic_libs('cffi')

try:
    binaries += collect_dynamic_libs('bcrypt')
except Exception:
    pass


a = Analysis(
    ['src\\data_extraction\\main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='data-extraction',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
