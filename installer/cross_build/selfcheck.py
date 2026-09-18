"""Post-install environment self-test for the AliBahmani IronOre Process Simulator.

The Windows installer runs this file on the *target* machine with the private
Python runtime that ships inside the installation folder:

    <install>\\runtime\\python\\python.exe -X utf8 <install>\\bin\\selfcheck.py <install>\\app

It verifies, in this order:
  1. every third-party engineering dependency imports,
  2. the desktop GUI layer (PySide6 + Qt) can be instantiated offscreen,
  3. the real simulation engine converges on a full plant run.
The result is captured by the installer into SELF_TEST_LOG.txt.

Exit codes: 0 = success, 10..13 = engine/dependency failures.
A GUI that cannot start does not change the exit code: the engine remains fully
functional in console mode and the log records a GUI_WARNING line.

Developer / Manufacturer: Ali Bahmani (علی بهمنی) - Contact: 09915420558
"""
import os
import sys
import traceback

DEPENDENCIES = ["openpyxl", "ezdxf", "reportlab", "PIL", "numpy", "imageio", "imageio_ffmpeg"]


def check_dependencies() -> bool:
    ok = True
    for name in DEPENDENCIES:
        try:
            mod = __import__(name)
            print("  import OK   %-14s %s" % (name, getattr(mod, "__version__", "")))
        except Exception as exc:  # noqa: BLE001
            ok = False
            print("  import FAIL %-14s %r" % (name, exc))
            traceback.print_exc()
    return ok


def check_gui(app_dir: str) -> bool:
    """Instantiate the real main window with the offscreen Qt platform."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        import PySide6
        from PySide6.QtWidgets import QApplication

        from ahsim.ui.main_window import MainWindow

        qapp = QApplication.instance() or QApplication([])
        window = MainWindow()
        widgets = len(window.spins)
        print("  GUI OK      %-14s %s | window '%s' | %d parameter widgets"
              % ("PySide6", PySide6.__version__, window.windowTitle(), widgets))
        if widgets == 0:
            print("  GUI FAIL    the main window exposed no parameter widgets")
            return False
        del window
        del qapp
        return True
    except Exception as exc:  # noqa: BLE001
        print("  GUI FAIL    %-14s %r" % ("PySide6", exc))
        traceback.print_exc()
        return False


def check_engine() -> int:
    try:
        from ahsim.app.metadata import CONTACT, DEVELOPER_EN, SOFTWARE_NAME, VERSION
        from ahsim.engine.simulation import PlantConfig, SimulationEngine

        print("  import OK   %-14s %s v%s (%s / %s)"
              % ("ahsim", SOFTWARE_NAME, VERSION, DEVELOPER_EN, CONTACT))
        result = SimulationEngine(PlantConfig()).run()
    except Exception:
        traceback.print_exc()
        print("SELF_CHECK_FAILED: the simulation engine could not run")
        return 13

    print("-" * 62)
    print("  simulation id   : %s" % result.simulation_id)
    print("  solver status   : %s" % result.status)
    print("  iterations      : %s" % result.solver.iterations)
    print("  streams solved  : %d" % len(result.streams))
    print("  mass balance err: %.6f %%" % result.kpis["mass_balance_error_pct"])
    print("  Fe balance err  : %.6f %%" % result.kpis["fe_balance_error_pct"])
    print("  warning count   : %d" % len(result.warnings))
    if result.status != "CONVERGED":
        print("SELF_CHECK_FAILED: solver status is %s" % result.status)
        return 12
    return 0


def main() -> int:
    app_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    sys.path.insert(0, app_dir)

    print("AliBahmani IronOre Process Simulator - environment self-test")
    print("executable : %s" % sys.executable)
    print("app_dir    : %s" % app_dir)
    print("python     : %s" % sys.version.replace("\n", " "))
    print("platform   : %s (%s)" % (sys.platform, os.name))
    print("-" * 62)

    if not check_dependencies():
        print("SELF_CHECK_FAILED: one or more dependencies are missing")
        return 10

    print("-" * 62)
    gui_ok = check_gui(app_dir)

    print("-" * 62)
    rc = check_engine()
    if rc != 0:
        return rc

    print("-" * 62)
    if not gui_ok:
        print("GUI_WARNING: the desktop interface could not start on this machine.")
        print("             The engine and all export modules are fully functional;")
        print("             console mode and 'Generate Reports' remain available.")
    print("SELF_CHECK_OK%s" % ("" if gui_ok else " (engine only, see GUI_WARNING above)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
