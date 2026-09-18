"""Recycle / flowsheet solver (Spec Sections 36-38, 51).

Successive substitution with relaxation on the closed screen-hydrocone loop.
Convergence tested on BOTH mass and Fe flows. Never reports a result as
final when NOT CONVERGED (Section 38).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from ..core.params import DEFAULT_VALUE, Parameter


@dataclass
class SolverSettings:
    max_iterations: int = 1000
    mass_tolerance_t_h: float = 1e-3       # absolute, t/h
    fe_tolerance_pct: float = 1e-4         # absolute, Fe %
    relative_tolerance: float = 1e-6
    relaxation_factor: float = 0.5         # omega in [0,1]; 1 = no damping
    tear_stream: str = "RECYCLE"


@dataclass
class SolverResult:
    status: str                            # CONVERGED | NOT CONVERGED
    iterations: int
    final_mass_residual: float
    final_fe_residual: float
    history: List[dict] = field(default_factory=list)


def solve_recycle(tear_guess: float, tear_fe_guess: float,
                  circuit_fn: Callable[[float, float], tuple],
                  settings: SolverSettings) -> SolverResult:
    """Solve the recycle loop.

    circuit_fn(recycle_dry_t_h, recycle_fe_pct) -> (new_recycle_dry_t_h,
    new_recycle_fe_pct, extras_dict). Convergence per Section 37.
    """
    x, fe = tear_guess, tear_fe_guess
    history = []
    status = "NOT CONVERGED"
    for it in range(1, settings.max_iterations + 1):
        nx, nfe, extras = circuit_fn(x, fe)
        # relaxation
        gx = settings.relaxation_factor * nx + (1 - settings.relaxation_factor) * x
        gfe = settings.relaxation_factor * nfe + (1 - settings.relaxation_factor) * fe
        dm = abs(gx - x)
        dfe = abs(gfe - fe)
        rel = dm / max(abs(gx), 1e-9)
        rec = {"iteration": it, "recycle_t_h": round(gx, 8), "recycle_fe_pct": round(gfe, 8),
               "dm": round(dm, 10), "dfe": round(dfe, 10)}
        history.append(rec)
        x, fe = gx, gfe
        if dm < settings.mass_tolerance_t_h and dfe < settings.fe_tolerance_pct:
            status = "CONVERGED"
            return SolverResult(status, it, dm, dfe, history)
        if rel < settings.relative_tolerance and dfe < settings.fe_tolerance_pct:
            status = "CONVERGED"
            return SolverResult(status, it, dm, dfe, history)
    return SolverResult(status, settings.max_iterations, dm, dfe, history)
