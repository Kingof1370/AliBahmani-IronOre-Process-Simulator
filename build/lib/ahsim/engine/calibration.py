"""Calibration, Scenario & Sensitivity engines (Spec Sections 27-28, 76-78)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..core.params import SITE_MEASUREMENT, CALIBRATION_DATA
from .simulation import SimulationEngine, PlantConfig


# ---------------------------------------------------------------- calibration
@dataclass
class CalibrationTest:
    test_id: str
    date: str
    feed_mass_t: float
    feed_fe_pct: float
    field_g: float
    rpm: float
    moisture_pct: float
    product_mass_t: float
    product_fe_pct: float
    tail_mass_t: float
    tail_fe_pct: float


def evaluate_test(t: CalibrationTest, predicted_recovery_pct: float) -> dict:
    """Observed / Predicted / Residual / Relative Error (Section 27)."""
    fe_in = t.feed_mass_t * t.feed_fe_pct / 100.0
    fe_prod = t.product_mass_t * t.product_fe_pct / 100.0
    observed = (fe_prod / fe_in * 100.0) if fe_in > 0 else 0.0
    residual = observed - predicted_recovery_pct
    rel_err = (abs(residual) / observed * 100.0) if observed > 0 else 0.0
    return {
        "test_id": t.test_id, "date": t.date, "field_g": t.field_g, "rpm": t.rpm,
        "observed_recovery_pct": observed, "predicted_recovery_pct": predicted_recovery_pct,
        "residual": residual, "relative_error_pct": rel_err,
        "source_classification": SITE_MEASUREMENT,
        "accepted_as_calibration": rel_err <= 10.0,   # site data overrides model (Section 28)
    }


# ---------------------------------------------------------------- scenarios
def run_scenario(scenario_id: str, **cfg_kwargs) -> dict:
    eng = SimulationEngine(PlantConfig(**cfg_kwargs))
    res = eng.run()
    row = res.summary()
    row["scenario_id"] = scenario_id
    return row


def scenario_comparison(base: dict, others: List[dict]) -> List[dict]:
    cols = ["scenario_id", "feed_t_h", "product_t_h", "product_fe_pct", "fe_recovery_pct",
            "mass_recovery_pct", "tail_t_h", "circulating_load_t_h", "status"]
    return [[b[c] for c in cols] for b in [base, *others]]


# ---------------------------------------------------------------- sensitivity
def sensitivity(parameter: str, values: List[float]) -> List[dict]:
    """One-at-a-time sensitivity around base case (Section 78)."""
    rows = []
    for v in values:
        cfg = PlantConfig()
        if parameter == "feed_rate_t_h":
            cfg.feed_rate_t_h = v
        elif parameter == "feed_fe_pct":
            cfg.feed_fe_pct = v
        elif parameter == "moisture_pct":
            cfg.moisture_pct = v
        else:
            raise ValueError(f"parameter '{parameter}' not directly configurable; "
                             f"use equipment parameters via API (field, rpm, css)")
        res = SimulationEngine(cfg).run()
        rows.append({"parameter": parameter, "value": v,
                     "product_t_h": res.kpis["product_t_h"],
                     "fe_recovery_pct": res.kpis["fe_recovery_pct"],
                     "circulating_load_t_h": res.kpis["circulating_load_t_h"]})
    return rows


def magnetic_field_sensitivity(fields_g: List[float]) -> List[dict]:
    """Field sensitivity requires re-tuning the partition curve per field."""
    from ..models.equipment import default_partition_curve
    rows = []
    for g in fields_g:
        eng = SimulationEngine(PlantConfig())
        for sep in eng.plant["pre_separators"] + eng.plant["final_separators"]:
            sep.set_field(g, "G")
        res = eng.run()
        rows.append({"field_g": g, "product_t_h": res.kpis["product_t_h"],
                     "product_fe_pct": res.kpis["product_fe_pct"],
                     "fe_recovery_pct": res.kpis["fe_recovery_pct"],
                     "curve_points": len(default_partition_curve(g))})
    return rows
