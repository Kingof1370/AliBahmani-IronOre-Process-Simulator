"""Console + GUI entry point used by both the legacy `ahsim_app.py` workflow
and the `pip install ahsim` console_scripts. Behaviour is identical.

If PySide6 is available, launches the desktop GUI. Otherwise falls back
to a headless console run.

Developer / Manufacturer: Ali Bahmani (علي بهمني) - Contact: 09915420558
"""
from __future__ import annotations

import ctypes
import os
import sys
import traceback

from .app.metadata import CONTACT, DEVELOPER_EN, SOFTWARE_NAME, VERSION


def _notify_win32(title: str, text: str) -> bool:
    """Best-effort MessageBox for pythonw.exe launches (no console)."""
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x00000040)
        return True
    except Exception:
        return False


def main() -> int:
    # 1. Try GUI (PySide6) - identical to legacy ahsim_app.main()
    try:
        from .ui.main_window import run_app
        return run_app()
    except ImportError as exc:
        # 2. Fall back to headless engine
        try:
            _notify_win32(
                f"{SOFTWARE_NAME} v{VERSION}",
                "The desktop interface could not be started.\n\n"
                f"{exc}\n\nThe simulation engine is still fully functional in "
                "console mode; use 'Generate Reports' to produce the engineering "
                "outputs (Excel, DXF, PDF, MP4).\n\n"
                f"Developer / Manufacturer: {DEVELOPER_EN}\nContact: {CONTACT}",
            )
        except Exception:
            pass
        print(f"{SOFTWARE_NAME} v{VERSION} - console mode (PySide6 unavailable: {exc})",
              file=sys.stderr)

    # 3. Always run a real plant simulation to prove the engine works.
    from .engine.simulation import PlantConfig, SimulationEngine
    eng = SimulationEngine(PlantConfig())
    try:
        r = eng.run()
    except Exception:
        traceback.print_exc()
        print(f"{SOFTWARE_NAME} v{VERSION} - FATAL: simulation engine failed",
              file=sys.stderr)
        return 2

    print(f"{SOFTWARE_NAME} v{VERSION} - console mode")
    print(f"Developer / Manufacturer: {DEVELOPER_EN} - Contact: {CONTACT}")
    print(
        "Simulation %s: status=%s iterations=%s mass_balance_error=%.6f%% "
        "fe_balance_error=%.6f%% product=%.3f t/h @ %.3f%% Fe fe_rec=%.3f%%"
        % (
            r.simulation_id, r.status, r.solver.iterations,
            r.kpis["mass_balance_error_pct"],
            r.kpis["fe_balance_error_pct"],
            r.kpis["product_t_h"], r.kpis["product_fe_pct"],
            r.kpis["fe_recovery_pct"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
