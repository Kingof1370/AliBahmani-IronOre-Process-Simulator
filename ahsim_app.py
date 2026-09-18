"""Application entry point (GUI launcher).

Runs the PySide6 desktop application when the GUI layer is importable and falls
back to a console run so the engine stays usable headless - including when the
process is started with pythonw.exe, where there is no console to print to (a
message box is shown instead).

Developer / Manufacturer: Ali Bahmani (علی بهمنی) - Contact: 09915420558
"""
import sys

from ahsim.app.metadata import CONTACT, DEVELOPER_EN, SOFTWARE_NAME, VERSION


def notify(title: str, text: str) -> None:
    """Make a message visible even without a console (pythonw.exe launch)."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x00000040)
        return
    except Exception:  # not Windows, or no user32 available
        pass
    print("%s: %s" % (title, text))


def main() -> int:
    try:
        from ahsim.ui.main_window import run_app

        return run_app()
    except ImportError as exc:
        notify(
            "%s v%s" % (SOFTWARE_NAME, VERSION),
            "The desktop interface could not be started.\n\n%s\n\n"
            "The simulation engine is still fully functional in console mode; "
            "use 'Generate Reports' to produce the engineering outputs "
            "(Excel, DXF, PDF, MP4).\n\n"
            "Developer / Manufacturer: %s\nContact: %s" % (exc, DEVELOPER_EN, CONTACT),
        )
        from ahsim.engine.simulation import PlantConfig, SimulationEngine

        result = SimulationEngine(PlantConfig()).run()
        print("%s v%s - console mode" % (SOFTWARE_NAME, VERSION))
        print("Developer / Manufacturer: %s - Contact: %s" % (DEVELOPER_EN, CONTACT))
        print(
            "Simulation %s: status=%s iterations=%s mass_balance_error=%.6f%%"
            % (result.simulation_id, result.status, result.solver.iterations,
               result.kpis["mass_balance_error_pct"])
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
