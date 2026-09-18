"""`python -m ahsim` entry point — same behaviour as the legacy ahsim_app.py launcher.

Headless by design: it runs one full plant simulation with the default
PlantConfig and prints the canonical KPI line. Used by CI, by the
self-test in the Windows installer, and as a smoke test after `pip install`.
"""
from __future__ import annotations

import sys

from .engine.simulation import PlantConfig, SimulationEngine
from .app.metadata import CONTACT, DEVELOPER_EN, SOFTWARE_NAME, VERSION


def cli() -> int:
    eng = SimulationEngine(PlantConfig())
    r = eng.run()
    print(
        f"{SOFTWARE_NAME} v{VERSION} - console mode\n"
        f"Developer / Manufacturer: {DEVELOPER_EN} - Contact: {CONTACT}\n"
        f"Simulation {r.simulation_id}: status={r.status} "
        f"iterations={r.solver.iterations} "
        f"mass_balance_error={r.kpis['mass_balance_error_pct']:.6f}% "
        f"fe_balance_error={r.kpis['fe_balance_error_pct']:.6f}% "
        f"product={r.kpis['product_t_h']:.3f} t/h @ "
        f"{r.kpis['product_fe_pct']:.3f}% Fe "
        f"fe_rec={r.kpis['fe_recovery_pct']:.3f}%"
    )
    return 0


if __name__ == "__main__":
    sys.exit(cli())
