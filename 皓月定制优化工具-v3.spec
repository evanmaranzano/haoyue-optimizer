# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('haoyue_optimizer')

# Read version from package
import importlib.util, os
_spec = importlib.util.spec_from_file_location('_init', os.path.join(r'F:\haoyue-optimizer', 'haoyue_optimizer', '__init__.py'))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_version = getattr(_mod, 'VERSION', 'dev')

a = Analysis(
    ['F:\\haoyue-optimizer\\haoyue_optimizer\\main.py'],
    pathex=['F:\\haoyue-optimizer'],
    binaries=[],
    datas=[('F:\\haoyue-optimizer\\haoyue_optimizer\\data', 'haoyue_optimizer\\data')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=f'皓月定制优化工具-v{_version}',
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
