# -*- mode: python ; coding: utf-8 -*-
"""
高级打包配置文件 - 使用此文件可以获得更好的打包效果
使用方法: pyinstaller build_exe_advanced.spec
"""

block_cipher = None

a = Analysis(
    ['shop_tools_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('keywords.xlsx', '.'),
    ],
    hiddenimports=[
        'pandas',
        'openpyxl',
        'selenium',
        'webdriver_manager',
        'tqdm',
        'dnspython',
        'dns',
        'phonenumbers',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'data_cleaner',
        'shopify_partners_scraper_auto',
        'shop_contact_scraper_google_login_v7_7',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Shop工具合集',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，可以指定路径
)
