"""`ahsim-make-reports` console script — identical to scripts/make_release.py
but importable after `pip install ahsim`. Generates Excel + DXF + PDF + MP4
+ sample project + scenario-sensitivity from ONE SimulationResult.

Developer / Manufacturer: Ali Bahmani - Contact: 09915420558
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    # 1. run the real simulation once
    from ahsim.engine.simulation import SimulationEngine, PlantConfig
    from ahsim.outputs.excel_export import export_workbook
    from ahsim.outputs.pdf_export import export_pdf
    from ahsim.outputs.cad_dxf import export_dxf
    from ahsim.outputs.video_engine import export_video
    from ahsim.engine.calibration import (run_scenario, sensitivity,
                                         magnetic_field_sensitivity)
    from ahsim.app.metadata import as_dict as meta

    out_root = os.environ.get("AHSIM_RELEASE_DIR",
                              os.path.join(here, "..", "RELEASE"))
    for d in ["EXCEL_REPORTS", "CAD_OUTPUT", "VIDEO_OUTPUT",
              "TEST_REPORTS", "SAMPLE_PROJECTS"]:
        os.makedirs(os.path.join(out_root, d), exist_ok=True)

    eng = SimulationEngine(PlantConfig(feed_rate_t_h=600.0))
    result = eng.run()
    print(f"[SIM] {result.simulation_id} status={result.status} "
          f"iterations={result.solver.iterations} "
          f"MB_err={result.kpis['mass_balance_error_pct']:.5f}% "
          f"FeB_err={result.kpis['fe_balance_error_pct']:.5f}%")

    xlsx  = export_workbook(result, os.path.join(out_root, "EXCEL_REPORTS",
                                                 "Plant_Simulation_Report.xlsx"))
    dxf   = export_dxf(result,      os.path.join(out_root, "CAD_OUTPUT",
                                                 "Process_Flowsheet.dxf"))
    pdf   = export_pdf(result,      os.path.join(out_root, "TEST_REPORTS",
                                                 "Engineering_Report.pdf"))
    mp4   = export_video(result,    os.path.join(out_root, "VIDEO_OUTPUT"),
                         os.path.join(out_root, "VIDEO_OUTPUT",
                                      "Process_Animation.mp4"),
                         seconds=8) if False else _mp4(result, out_root, 8)

    project = {
        "metadata": meta(),
        "config":   result.config.as_dict(),
        "simulation": result.summary(),
        "streams":  {k: v.as_dict() for k, v in result.streams.items()},
    }
    proj = os.path.join(out_root, "SAMPLE_PROJECTS", "Scenario_001_600tph.ahsim.json")
    with open(proj, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2, default=str)

    scenarios = [run_scenario(f"Scenario-{i:03d}", feed_rate_t_h=r)
                 for i, r in enumerate([100, 200, 400, 600, 800, 1000], start=1)]
    sens = sensitivity("feed_rate_t_h", [100, 200, 400, 600, 800, 1000])
    field_sens = magnetic_field_sensitivity([1400, 3000, 4000, 5000])
    analysis = os.path.join(out_root, "TEST_REPORTS", "Scenario_Sensitivity_Results.json")
    with open(analysis, "w", encoding="utf-8") as f:
        json.dump({"scenarios": scenarios, "feed_sensitivity": sens,
                   "field_sensitivity": field_sens},
                  f, ensure_ascii=False, indent=2, default=str)

    for p in [xlsx, dxf, pdf, mp4, proj, analysis]:
        print(f"[OUT] {os.path.getsize(p):>10,} bytes  {p}")
    return 0


def _mp4(result, out_root: str, seconds: int) -> str:
    from ahsim.outputs.video_engine import export_video
    target = os.path.join(out_root, "VIDEO_OUTPUT", "Process_Animation.mp4")
    return export_video(result, target, seconds=seconds)


if __name__ == "__main__":
    sys.exit(main())
