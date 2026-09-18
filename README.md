# AliBahmani IronOre Process Simulator v1.0.0

**Industrial Mineral Processing Simulation and Engineering Software**

Developer / Manufacturer: **Ali Bahmani (علی بهمنی)** — Contact: **09915420558**

---

## What this software is

`AH-SIM` is a steady-state mass-balance and equipment-performance simulator for a
**dry iron-ore beneficiation plant** (crushing → screening → dry magnetic
separation with recycle). From a single `PlantConfig` it produces:

| Output | Module | File |
|---|---|---|
| Solved flowsheet + KPIs | `ahsim.engine.simulation` | — |
| Excel workbook (streams, equipment, KPIs) | `ahsim.outputs.excel_export` | `RELEASE/EXCEL_REPORTS/Plant_Simulation_Report.xlsx` |
| CAD flowsheet (AutoCAD R2010 DXF) | `ahsim.outputs.cad_dxf` | `RELEASE/CAD_OUTPUT/Process_Flowsheet.dxf` |
| Engineering report (PDF, 4 pages) | `ahsim.outputs.pdf_export` | `RELEASE/TEST_REPORTS/Engineering_Report.pdf` |
| Process animation (MP4, H.264) | `ahsim.outputs.video_engine` | `RELEASE/VIDEO_OUTPUT/Process_Animation.mp4` |
| Project file (JSON) | `scripts/make_release.py` | `RELEASE/SAMPLE_PROJECTS/Scenario_001_600tph.ahsim.json` |
| Scenario + sensitivity study | `ahsim.engine.calibration` | `RELEASE/TEST_REPORTS/Scenario_Sensitivity_Results.json` |

Core capabilities:

* **Stream model** (`ahsim.models.stream`) — solids/liquid flow, Fe and SiO₂
  assays, particle-size distributions; `Fe_balance` and `mass_balance` errors are
  computed per node.
* **PSD engine** (`ahsim.models.psd`) — Rosin–Rammler distribution, linear
  interpolation, `d50`/`P80` extraction, mixing and splitting.
* **Equipment models** (`ahsim.models.equipment`) — jaw/cone crusher, vibrating
  screen (efficiency curves), dry drum / LIMS magnetic separator (field-dependent
  recovery), belt conveyor, feeder.
* **Flow-graph + solver** (`ahsim.models.graph`, `ahsim.engine.recycle`) —
  topological order with an iterative recycle-convergence solver (tolerance and
  iteration cap in `ahsim/core/params.py`).
* **Calibration** (`ahsim.engine.calibration`) — scenario batches, one-factor
  sensitivity studies, magnetic-field sensitivity.
* **Units** (`ahsim/core/units`) — t/h ↔ kg/s ↔ t/a, wt% ↔ ppm, mesh ↔ mm,
  Gauss ↔ Tesla, µm ↔ mm.

The package is deterministic: every run records an `input_hash` and a
`result_hash` on the `SimulationResult` for auditability.

## Repository layout

```
ahsim/                 application package (models, engine, outputs, ui)
  app/metadata.py      manufacturer / version identity (single source of truth)
  core/                units and solver parameters
  engine/              simulation, recycle solver, calibration
  models/              material, stream, psd, equipment, graph
  outputs/             excel_export, cad_dxf, pdf_export, video_engine
  ui/                  desktop GUI layer (PySide6 optional)
ahsim_app.py           entry point: GUI when PySide6 is present, else console run
tests/                 test suite (41 tests) covering engine, models, outputs
scripts/make_release.py  one SimulationResult -> Excel + DXF + PDF + MP4 + project
RELEASE/               generated sample deliverables
docs/                  USER_MANUAL.md, CALIBRATION_MANUAL.md, BUILD_WINDOWS.md
installer/             packaging
  AH-SIM_SelfContained_Setup.nsi     self-contained Windows installer script
  alibahmani_sim.spec                PyInstaller one-file build spec
  AliBahmani_IronOre_Process_Simulator.iss   Inno Setup script
  cross_build/                       Linux cross-build pipeline (see below)
```

## Install on Windows

**Option A — self-contained installer (recommended, nothing to install first).**
Run `AliBahmani_IronOre_Process_Simulator_Setup_v1.0.0.exe`. It installs the
application, a private Python 3.11 x64 runtime and all libraries for the current
user (no administrator rights), creates Start-Menu/desktop shortcuts, and runs a
post-install self-test that writes `SELF_TEST_LOG.txt` next to the installation.

**Option B — portable.** Unzip the portable package anywhere and run
`app\Run_AH-SIM.cmd`.

**Option C — from source (developer machine).**

```bat
py -m venv venv && venv\Scripts\activate
pip install PySide6 openpyxl ezdxf reportlab pillow numpy imageio imageio-ffmpeg pytest pyinstaller
py -m pytest tests/ -v
py scripts\make_release.py
pyinstaller installer\alibahmani_sim.spec
```

## Build the installer from source

On Windows, with Inno Setup 6 installed:

```bat
pyinstaller installer\alibahmani_sim.spec
ISCC.exe installer\AliBahmani_IronOre_Process_Simulator.iss
```

On Linux/macOS (no Windows toolchain needed — uses the embeddable CPython
distribution, win_amd64 wheels and the NSIS cross-compiler):

```bash
sudo apt-get install -y nsis
bash installer/cross_build/build_windows_installer.sh
```

Both routes write into `installer/SETUP_OUTPUT/`.

## Verification

```bash
python -m pytest tests/ -q          # 41 passed
python bin/selfcheck.py .           # last line: SELF_CHECK_OK
```

## License

Proprietary — (c) 2026 Ali Bahmani. All rights reserved. See `LICENSE`.
