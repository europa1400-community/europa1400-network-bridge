# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_submodules

a_cli = Analysis(
    ['europa1400_network_bridge\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('europa1400_network_bridge'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a_gui = Analysis(
    ['europa1400_network_bridge\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('europa1400_network_bridge'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data, cipher=None)
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=None)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    a_cli.binaries,
    a_cli.datas,
    [],
    name='europa1400-network-bridge',
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
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    a_gui.binaries,
    a_gui.datas,
    [],
    name='europa1400-network-bridge-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


coll_cli = COLLECT(
    exe_cli, a_cli.binaries, a_cli.zipfiles, a_cli.datas, strip=False, upx=True, name='europa1400-network-bridge'
)
coll_gui = COLLECT(
    exe_gui, a_gui.binaries, a_gui.zipfiles, a_gui.datas, strip=False, upx=True, name='europa1400-network-bridge-gui'
)
