# PyInstaller spec - build Windows executable
# Build on Windows:  pyinstaller installer/alibahmani_sim.spec
# Entry point: ahsim_app.py (GUI launcher)

import os

block_cipher = None

a = Analysis(
    ["../ahsim_app.py"],
    pathex=[os.path.abspath("..")],
    binaries=[],
    datas=[("../docs", "docs"), ("../RELEASE/SAMPLE_PROJECTS", "SAMPLE_PROJECTS")],
    hiddenimports=["PySide6", "openpyxl", "ezdxf", "reportlab",
                   "PIL", "numpy", "imageio", "imageio_ffmpeg"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="AliBahmani_IronOre_Process_Simulator",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, icon=None, version="version_info.txt",
)
