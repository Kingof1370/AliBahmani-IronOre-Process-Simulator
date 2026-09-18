PORTable / STANDALONE PACKAGE
=============================
AliBahmani IronOre Process Simulator v1.0.0
Developer / Manufacturer: Ali Bahmani (علی بهمنی)  -  Contact: 09915420558
Industrial Mineral Processing Simulation and Engineering Software

This folder is the same self-contained build that the installer deploys, but
without registration: nothing is written to the registry or to Program Files.
You may copy it to a USB stick, a network share, or run it directly from here.

REQUIREMENTS
------------
Windows 10 or Windows 11, 64-bit (x64). Nothing else - Python is included in
the "runtime" folder, together with numpy, reportlab, ezdxf, openpyxl, Pillow
and imageio (which bundles ffmpeg 7.1 for MP4 rendering).

HOW TO RUN
----------
1) Double-click            app\Run_AH-SIM.cmd
   (or, from a command prompt:  runtime\python\python.exe app\ahsim_app.py)
2) To regenerate the engineering deliverables (Excel, DXF, PDF, MP4) from one
   simulation run: double-click   app\Generate_Reports.cmd
3) To verify the environment yourself:
   runtime\python\python.exe bin\selfcheck.py app
   -> the last line must read "SELF_CHECK_OK"

SAMPLE OUTPUTS ALREADY INCLUDED (app\RELEASE)
---------------------------------------------
  EXCEL_REPORTS\Plant_Simulation_Report.xlsx
  CAD_OUTPUT\Process_Flowsheet.dxf
  VIDEO_OUTPUT\Process_Animation.mp4
  TEST_REPORTS\Engineering_Report.pdf
  TEST_REPORTS\Scenario_Sensitivity_Results.json
  SAMPLE_PROJECTS\Scenario_001_600tph.ahsim.json

DOCUMENTATION
-------------
app\docs\USER_MANUAL.md
app\docs\CALIBRATION_MANUAL.md
app\docs\BUILD_WINDOWS.md

UNINSTALL
---------
Delete this folder. Nothing was registered in Windows.

(c) 2026 Ali Bahmani - 09915420558 - All rights reserved.
