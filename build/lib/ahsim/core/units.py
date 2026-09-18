"""Unit conversion engine (Spec Section 08, 22, 100).

All internal computation uses SI-ish base units declared per dimension:
mass/mass-flow in tonnes and t/h, length in m, speed in m/s, field in Gauss.
Conversion factors are exact definitions, not approximations.
"""
from __future__ import annotations

from typing import Dict, Tuple

# dimension -> (unit -> factor to base unit)
_FACTORS: Dict[str, Dict[str, float]] = {
    "mass": {"t": 1.0, "kg": 0.001, "g": 1e-6, "kt": 1000.0, "Mt": 1e6},
    "mass_flow": {
        "kg/s": 3.6, "kg/min": 0.06, "kg/h": 0.001,
        "t/h": 1.0, "t/min": 60.0, "t/day": 1.0 / 24.0,
        "t/month": 1.0 / (24.0 * 30.0),   # 30-day month, declared assumption
        "t/year": 1.0 / (24.0 * 365.0),   # 365-day year, declared assumption
    },
    "field": {"G": 1.0, "gauss": 1.0, "T": 10000.0, "tesla": 10000.0, "mT": 10.0},
    "length": {"m": 1.0, "mm": 0.001, "cm": 0.01, "km": 1000.0, "um": 1e-6},
    "speed": {"m/s": 1.0, "m/min": 1.0 / 60.0, "mm/s": 0.001},
    "area": {"m2": 1.0, "mm2": 1e-6},
    "volume": {"m3": 1.0, "L": 0.001},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0},
    "angle": {"deg": 1.0, "rad": 57.29577951308232},
}


class UnitError(ValueError):
    pass


def dimensions() -> Tuple[str, ...]:
    return tuple(_FACTORS.keys())


def units_for(dim: str) -> Tuple[str, ...]:
    if dim not in _FACTORS:
        raise UnitError(f"unknown dimension '{dim}'")
    return tuple(_FACTORS[dim].keys())


def convert(value: float, frm: str, to: str, dim: str) -> float:
    """Convert value from unit frm to unit to within the given dimension.

    1 Tesla = 10,000 Gauss (exact). kg/s <-> t/h: 1 kg/s = 3.6 t/h (exact).
    """
    if dim not in _FACTORS:
        raise UnitError(f"unknown dimension '{dim}'")
    table = _FACTORS[dim]
    key = frm.strip()
    key2 = to.strip()
    if key not in table:
        raise UnitError(f"unit '{frm}' not valid for dimension '{dim}'")
    if key2 not in table:
        raise UnitError(f"unit '{to}' not valid for dimension '{dim}'")
    base = value * table[key]
    return base / table[key2]


# --- Drum geometry / kinematics (Spec Section 19, 20) ------------------------

def peripheral_speed(diameter_m: float, rpm: float) -> float:
    """V = pi * D * RPM / 60  [m/s]."""
    import math
    if diameter_m <= 0 or rpm < 0:
        raise ValueError("diameter must be > 0 and rpm >= 0")
    return math.pi * diameter_m * rpm / 60.0


def rpm_from_speed(diameter_m: float, v_ms: float) -> float:
    """RPM = V * 60 / (pi * D)."""
    import math
    if diameter_m <= 0:
        raise ValueError("diameter must be > 0")
    return v_ms * 60.0 / (math.pi * diameter_m)


def drum_circumference(diameter_m: float) -> float:
    import math
    return math.pi * diameter_m


def drum_surface_area(diameter_m: float, length_m: float) -> float:
    """Lateral (mantle) surface area of the drum shell, m2."""
    return drum_circumference(diameter_m) * length_m


def drum_internal_volume(diameter_m: float, length_m: float) -> float:
    """Internal geometric volume of drum, m3 (NOT a process capacity)."""
    import math
    return math.pi * (diameter_m / 2.0) ** 2 * length_m
