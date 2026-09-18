#!/usr/bin/env python3
"""Offscreen smoke test of the AH-SIM desktop GUI.

Launches the real MainWindow with a headless Qt platform, runs one simulation
through the GUI, performs the exports and then quits. Used to prove the GUI
layer is functional without a physical display.

Usage:  QT_QPA_PLATFORM=offscreen python gui_smoke_test.py /path/to/repo_root
"""
import os
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
sys.path.insert(0, repo)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ahsim.ui.main_window import MainWindow  # noqa: E402

app = QApplication(sys.argv)
win = MainWindow()
win.show()


def step():
    print("[gui] window title      :", win.windowTitle())
    print("[gui] parameter widgets :", len(win.spins))
    win.run_simulation()
    r = win.result
    assert r is not None, "GUI produced no simulation result"
    print("[gui] simulation id     :", r.simulation_id)
    print("[gui] solver status     :", r.status)
    print("[gui] stream rows shown :", win.tbl_streams.rowCount())
    print("[gui] KPI rows shown    :", win.tbl_kpis.rowCount())
    assert win.tbl_streams.rowCount() == len(r.streams)
    assert win.tbl_kpis.rowCount() == len(r.kpis)
    print("[gui] GUI_SMOKE_OK")
    app.quit()


QTimer.singleShot(200, step)
rc = app.exec()
print("exit code:", rc)
sys.exit(rc)
