# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\kacper.urbanowicz\\PycharmProjects\\PSU_HiPot\\models.json', '.'), ('C:\\Users\\kacper.urbanowicz\\PycharmProjects\\PSU_HiPot\\operators.json', '.'), ('C:\\Users\\kacper.urbanowicz\\PycharmProjects\\PSU_HiPot\\config.json', '.')],
    hiddenimports=['tkinter', 'tkinter.messagebox', 'tkinter.ttk', 'serial', 'serial.tools.list_ports', 'serial.tools.list_ports_windows', 'threading', 'time', 'json', 'csv', 'os', 're', 'datetime', 'hashlib', 'pathlib', 'config', 'models', 'gui', 'test_screen', 'admin_panel', 'hipot_device', 'interlock', 'arduino', 'logger', 'settings_manager', 'stats_manager', 'shift_stats', 'screenshot_helper'],
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
    [],
    exclude_binaries=True,
    name='Hi-Pot PSU',
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
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Hi-Pot PSU',
)
