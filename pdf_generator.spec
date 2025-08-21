# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# --- PyQt5 Configuration ---
# Collect only the necessary PyQt5 modules to reduce size
pyqt5_modules = [
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
]
hiddenimports = ['sip']
for module in pyqt5_modules:
    hiddenimports.extend(collect_submodules(module))

# --- Exclusions Configuration ---
# Exclude unused PyQt5 and Pillow modules
excludes = [
    # PyQt5 Exclusions
    'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebKit', 'PyQt5.QtWebKitWidgets', 'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets', 'PyQt5.QtOpenGL', 'PyQt5.QtPrintSupport',
    'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtSql', 'PyQt5.QtTest',
    'PyQt5.QtNetwork', 'PyQt5.QtXml', 'PyQt5.QtSvg',
    
    # Pillow (PIL) Exclusions for unused image formats
    'PIL.BmpImagePlugin', 'PIL.GifImagePlugin', 'PIL.TiffImagePlugin',
    'PIL.PpmImagePlugin', 'PIL.IcnsImagePlugin', 'PIL.IcoImagePlugin',
    'PIL.ImImagePlugin', 'PIL.MspImagePlugin', 'PIL.SgiImagePlugin',
    'PIL.SpiderImagePlugin', 'PIL.TgaImagePlugin', 'PIL.XbmImagePlugin',
    'PIL.XpmImagePlugin', 'PIL.WebPImagePlugin',
]

# --- IMPORTANT: Path to Conda Environment Binaries ---
# This path assumes a standard Anaconda installation. 
# PLEASE VERIFY this path is correct for your system.
conda_bin_path = 'D:\\anaconda3\\envs\\pdf_env\\Library\\bin'


a = Analysis(
    ['pdf_generator.py'],
    pathex=['c:\\Users\\YAYOI\\Desktop\\myproject\\PDF-Generator'],
    binaries=[
        # Fix libdeflate.dll dependency issue by mapping deflate.dll to libdeflate.dll
        (conda_bin_path + '\\deflate.dll', 'vendor\\libdeflate.dll'),
    ],
    # --- Data Files Configuration ---
    # This section bundles necessary external files like icons and PDF tools.
    datas=[
        ('icon.ico', '.'),
        # The following line bundles Poppler and Ghostscript from the conda env.
        (conda_bin_path, 'vendor')
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pdf_generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)