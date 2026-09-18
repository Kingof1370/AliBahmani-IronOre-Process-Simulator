# Windows Build & Installer Guide - AliBahmani IronOre Process Simulator v1.0.0
Developer / Manufacturer: Ali Bahmani (علی بهمنی) - Contact: 09915420558

## Route A - self-contained installer, cross-built from Linux/macOS (recommended)

No Windows toolchain, no PyInstaller and no wine are needed. The package is
assembled from the official Windows *embeddable* CPython distribution plus
`win_amd64` binary wheels, and compiled with NSIS, which is a genuine Windows
installer compiler that also runs on Linux:

```
sudo apt-get install -y nsis            # Debian/Ubuntu (brew install makensis on macOS)
bash installer/cross_build/build_windows_installer.sh
```

Output: `installer/SETUP_OUTPUT/`
* `AliBahmani_IronOre_Process_Simulator_Setup_v1.0.0.exe` - Windows setup
  (installs for the current user, no admin rights required)
* `..._v1.0.0_portable_win64.zip` - portable copy, run `app\Run_AH-SIM.cmd`

The setup is self-contained (runtime + numpy, reportlab, ezdxf, openpyxl,
Pillow, imageio with bundled ffmpeg 7.1) and runs a post-install self-test on
the target machine, writing `SELF_TEST_LOG.txt` into the installation folder.

## Route B - PyInstaller one-file build (run on Windows)

## 1. Prerequisites (Windows 10/11 x64)
- Python 3.11+ (python.org, "Add to PATH" checked)
- Inno Setup 6 (jrsoftware.org)
- ffmpeg binary on PATH (video engine)

## 2. Build steps
```
py -m venv venv && venv\Scripts\activate
pip install PySide6 openpyxl ezdxf reportlab pillow numpy imageio imageio-ffmpeg pytest pyinstaller
py -m pytest tests/ -v                 :: full test suite must pass
py scripts\make_release.py             :: generates Excel/DXF/PDF/MP4 into RELEASE\
pyinstaller installer\alibahmani_sim.spec   :: produces dist\AliBahmani_IronOre_Process_Simulator.exe
ISCC.exe installer\AliBahmani_IronOre_Process_Simulator.iss
```
Output: `installer\SETUP_OUTPUT\AliBahmani_IronOre_Process_Simulator_Setup.exe`

## 3. Clean-machine acceptance test (Section 108, 132)
Install -> Launch -> New Project -> enter Feed -> run Simulation -> export Excel,
DXF, PDF, MP4 -> close -> reopen. Record results in RELEASE\TEST_REPORTS.

## Note
The PyInstaller/Inno route (B) must be run on a real Windows machine. Route A
is the self-contained route and can be run from Linux or macOS.

`ahsim_app.py` starts the desktop GUI when `ahsim.ui.main_window` is importable
and otherwise falls back to a headless console run of the engine. The GUI layer
is optional; the simulation engine and every export module work without it.
