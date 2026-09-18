"""Particle Size Distribution model (Spec Section 12, PSD Engine).

PSD is a first-class object. Fractions are user-definable; the default
project PSD uses the 9 standard classes. Sum of Mass % must equal 100.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.params import ValidationError, DEFAULT_VALUE, USER_DEFINED

DEFAULT_SIZES = [
    (50.0, 1e9, ">50 mm"),
    (25.0, 50.0, "25-50 mm"),
    (10.0, 25.0, "10-25 mm"),
    (5.0, 10.0, "5-10 mm"),
    (3.0, 5.0, "3-5 mm"),
    (1.0, 3.0, "1-3 mm"),
    (0.5, 1.0, "0.5-1 mm"),
    (0.1, 0.5, "0.1-0.5 mm"),
    (1e-9, 0.1, "<0.1 mm"),
]


@dataclass
class PSDFraction:
    size_lower_mm: float
    size_upper_mm: float
    mass_pct: float = 0.0
    fe_pct: float = 0.0
    mineral_pct: Dict[str, float] = field(default_factory=dict)  # mineral -> % of fraction
    liberation_pct: float = 0.0            # liberated magnetite %, USER DEFINED
    liberation_state: str = "UNKNOWN"      # Liberated | Partially Liberated | Locked | Composite
    density_t_m3: float = 2.9              # DEFAULT; per-fraction override
    magnetic_class: str = "mixed"          # magnetic | non_magnetic | mixed

    @property
    def name(self) -> str:
        return f"{self.size_lower_mm:g}-{self.size_upper_mm:g} mm" if self.size_lower_mm > 1e-8 else f"<{self.size_upper_mm:g} mm"

    @property
    def geometric_mean_mm(self) -> float:
        lo = max(self.size_lower_mm, 1e-6)
        return (lo * self.size_upper_mm) ** 0.5

    def as_dict(self) -> dict:
        return {
            "size_lower_mm": self.size_lower_mm, "size_upper_mm": self.size_upper_mm,
            "mass_pct": self.mass_pct, "fe_pct": self.fe_pct,
            "mineral_pct": dict(self.mineral_pct),
            "liberation_pct": self.liberation_pct, "liberation_state": self.liberation_state,
            "density_t_m3": self.density_t_m3, "magnetic_class": self.magnetic_class,
        }


class PSD:
    """Particle size distribution with validation (Section 12, 66)."""

    def __init__(self, fractions: Optional[List[PSDFraction]] = None, source: str = DEFAULT_VALUE):
        self.source = source
        self.fractions: List[PSDFraction] = fractions or []

    @classmethod
    def default(cls) -> "PSD":
        # Default project PSD (DEFAULT VALUE - user must replace with site sieve data).
        masses = [18.0, 22.0, 20.0, 12.0, 8.0, 8.0, 5.0, 4.0, 3.0]
        fe = [14.0, 16.0, 17.5, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0]
        fr = [
            PSDFraction(lo, hi, m, f, liberation_pct=lib, liberation_state="UNKNOWN")
            for (lo, hi, _), m, f, lib in zip(DEFAULT_SIZES, masses, fe, [30, 40, 50, 60, 65, 70, 75, 80, 85])
        ]
        return cls(fr)

    def validate(self, tol: float = 1e-6) -> None:
        if not self.fractions:
            raise ValidationError("PSD is empty (EMPTY PSD)")
        total = sum(f.mass_pct for f in self.fractions)
        if abs(total - 100.0) > 1e-3:
            raise ValidationError(f"PSD mass fractions sum to {total:.4f}%, must equal 100%")
        for f in self.fractions:
            if f.size_upper_mm <= f.size_lower_mm:
                raise ValidationError(f"fraction {f.name}: upper size <= lower size")
            if f.mass_pct < 0 or f.fe_pct < 0:
                raise ValidationError(f"fraction {f.name}: negative mass/Fe")

    def split_by_aperture(self, aperture_mm: float, efficiency: float = 1.0,
                          d50: Optional[float] = None) -> tuple["PSD", "PSD", float]:
        """Partition-based screen split (Section 31).

        Returns (undersize_psd, oversize_psd, oversize_fraction_of_mass).
        Logistic partition around d50 (default = aperture) with sharpness
        derived from declared efficiency. Logistic screen partition is an
        ENGINEERING CORRELATION (Tier 5), calibrated by screen testwork.
        """
        import math
        d50 = d50 if d50 is not None else aperture_mm
        # sharpness from efficiency: eff=1 -> sharp (s=6), lower eff -> more misplacement
        s = 6.0 * max(0.05, min(1.0, efficiency))
        under_f, over_f = [], []
        for f in self.fractions:
            d = max(f.geometric_mean_mm, 1e-6)
            p_under = 1.0 / (1.0 + (d / d50) ** s) if d > 0 else 1.0
            p_under = min(1.0, max(0.0, p_under))
            under_f.append(p_under * f.mass_pct)
            over_f.append((1.0 - p_under) * f.mass_pct)
        u_mass = sum(under_f)
        o_mass = sum(over_f)
        total = u_mass + o_mass
        under = PSD([], source="DERIVED VALUE")
        over = PSD([], source="DERIVED VALUE")
        for f, mu, mo in zip(self.fractions, under_f, over_f):
            under.fractions.append(PSDFraction(f.size_lower_mm, f.size_upper_mm, mu, f.fe_pct,
                                               dict(f.mineral_pct), f.liberation_pct, f.liberation_state,
                                               f.density_t_m3, f.magnetic_class))
            over.fractions.append(PSDFraction(f.size_lower_mm, f.size_upper_mm, mo, f.fe_pct,
                                              dict(f.mineral_pct), f.liberation_pct, f.liberation_state,
                                              f.density_t_m3, f.magnetic_class))
        return under, over, (o_mass / total if total > 0 else 0.0)

    def merge_weighted(self, *weighted: tuple["PSD", float]) -> "PSD":
        """Merge PSDs weighted by actual dry mass flows (Fe-conserving)."""
        all_fr: Dict[tuple, List[float]] = {}
        all_fe: Dict[tuple, List[float]] = {}
        wsum = 0.0
        for psd, w in weighted:
            if w <= 0 or not psd.fractions:
                continue
            wsum += w
        if wsum <= 0:
            return PSD(source="DERIVED VALUE")
        for psd, w in weighted:
            if w <= 0 or not psd.fractions:
                continue
            share = w / wsum
            for f in psd.fractions:
                key = (f.size_lower_mm, f.size_upper_mm)
                all_fr[key] = all_fr.get(key, 0.0) + f.mass_pct * share
                all_fe[key] = all_fe.get(key, 0.0) + f.mass_pct * share * f.fe_pct
        merged = PSD(source="DERIVED VALUE")
        for key in sorted(all_fr.keys(), reverse=True):
            m = all_fr[key]
            fe = (all_fe[key] / m) if m > 0 else 0.0
            merged.fractions.append(PSDFraction(key[0], key[1], m, fe))
        total = sum(f.mass_pct for f in merged.fractions)
        if total > 0:
            for f in merged.fractions:
                f.mass_pct *= 100.0 / total
        return merged

    def merge(self, *others: "PSD") -> "PSD":
        """Unweighted merge (kept for compatibility); prefer merge_weighted."""
        return self.merge_weighted(*[(o, 1.0) for o in others])

    def implied_fe(self) -> float:
        return self.weighted_fe()

    def scale_fe_to(self, target_fe: float) -> None:
        """Scale fraction Fe grades so PSD-implied Fe == stream Fe grade
        (keeps Stream grade and PSD traceably consistent)."""
        cur = self.implied_fe()
        if self.fractions and cur > 0 and target_fe >= 0:
            k = target_fe / cur
            for f in self.fractions:
                f.fe_pct *= k

    def total_mass_pct(self) -> float:
        return sum(f.mass_pct for f in self.fractions)

    def weighted_fe(self) -> float:
        tot = self.total_mass_pct()
        if tot <= 0:
            return 0.0
        return sum(f.mass_pct * f.fe_pct for f in self.fractions) / tot

    def as_dict(self) -> list:
        return [f.as_dict() for f in self.fractions]

    @classmethod
    def from_dict(cls, d: list, source: str = USER_DEFINED) -> "PSD":
        fr = [PSDFraction(**x) for x in d]
        p = cls(fr, source)
        return p

    def copy(self) -> "PSD":
        return PSD([PSDFraction(f.size_lower_mm, f.size_upper_mm, f.mass_pct, f.fe_pct,
                                dict(f.mineral_pct), f.liberation_pct, f.liberation_state,
                                f.density_t_m3, f.magnetic_class) for f in self.fractions], self.source)
