"""Equipment models: magnetic separator, screen, crushers (Spec Sections 18-39).

All physical/electrical performance numbers that lack real data are declared
UNKNOWN or CALIBRATION_REQUIRED — never invented (Sections 88, 130).
Partition-based separation, not a fixed global recovery (Section 25).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from ..core.params import (Parameter, ValidationError, positive, non_negative,
                           percent_range, fraction_range, MANUFACTURER_DATA, USER_INPUT, DEFAULT_VALUE,
                           ENGINEERING_CORRELATION, CALIBRATION_REQUIRED, UNKNOWN,
                           DERIVED_VALUE)
from ..core import units
from .psd import PSD, PSDFraction
from .stream import Stream


# ---------------------------------------------------------------- magnetic --
@dataclass
class PartitionPoint:
    size_mm: float
    p_magnetic: float       # probability to report to magnetic product
    p_non_magnetic: float   # probability to report to tail

    def __post_init__(self):
        if not math.isclose(self.p_magnetic + self.p_non_magnetic, 1.0, abs_tol=1e-9):
            raise ValidationError("partition probabilities must sum to 1")


def _p_from_model(size_mm: float, field_g: float, liberation_pct: float) -> float:
    """ENGINEERING CORRELATION (Tier 5) for dry drum LIMS on magnetite feed:
    P = field_factor * liberation_factor * fine_loss_factor * coarse_limit_factor.
    Higher field raises recovery; well-liberated magnetite reports to the
    magnetic product; very fine particles suffer air-drag losses; material
    coarser than the drum's proven size limit is rejected to tail.
    MUST be replaced by site calibration (Sections 27-28); limitations in
    Section 112. Valid range: 0.05 mm < d < 50 mm, dry feed, magnetite ore.
    """
    field_factor = 1.0 - math.exp(-max(field_g, 0.0) / 1500.0)
    lib = min(1.0, max(0.0, liberation_pct / 100.0))
    lib_factor = 0.40 + 0.60 * lib
    fine_loss = size_mm / (size_mm + 0.10)          # ultrafine loss proxy
    coarse_limit = max(0.0, min(1.0, 1.0 - (size_mm - 25.0) / 25.0))
    p = field_factor * lib_factor * fine_loss * coarse_limit
    return min(0.98, max(0.01, p))


def default_partition_curve(field_g: float) -> list:
    """Partition curve table (Section 26) generated from the correlation model."""
    sizes = [0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 25.0]
    pts = []
    for d in sizes:
        p = _p_from_model(d, field_g, liberation_pct=70.0)
        pts.append(PartitionPoint(d, p, 1.0 - p))
    return pts


class MagneticSeparator:
    """Custom drum separator (Sections 18, 19, 20, 21, 24, 82, 83)."""

    def __init__(self, sep_id: str, stage: str = "PRE-PROCESSING"):
        self.sep_id = sep_id
        self.stage = stage
        # Single geometry source of truth: radius (Section 18)
        self.radius_m = Parameter(f"{sep_id}.radius", 1.5, "m", source=USER_INPUT, validator=positive)
        self.diameter_m = Parameter(f"{sep_id}.diameter", 3.0, "m", source=DERIVED_VALUE,
                                    validator=positive, editable=False)
        self.length_m = Parameter(f"{sep_id}.length", 3.0, "m", source=USER_INPUT, validator=positive)
        self.shell_thickness_m = Parameter(f"{sep_id}.shell_thickness", 0.010, "m",
                                           source=MANUFACTURER_DATA, validator=positive)
        self.shell_material = Parameter(f"{sep_id}.shell_material", "Stainless Steel", "",
                                        source=MANUFACTURER_DATA, ptype="text")
        self.rpm = Parameter(f"{sep_id}.rpm", 6.37, "rpm", source=USER_INPUT, validator=non_negative)
        self.field_g = Parameter(f"{sep_id}.field_g", 3000 if stage == "PRE-PROCESSING" else 1400,
                                 "G", source=USER_INPUT, validator=non_negative)
        self.field_location = Parameter(f"{sep_id}.field_location", "UNKNOWN", "",
                                        source=UNKNOWN, ptype="text")  # Section 23
        self.pole_pitch_m = Parameter(f"{sep_id}.pole_pitch", 0.0, "m", source=CALIBRATION_REQUIRED)
        self.pole_count = Parameter(f"{sep_id}.pole_count", 0, "-", source=CALIBRATION_REQUIRED)
        self.magnetic_circuit = Parameter(f"{sep_id}.magnetic_circuit", "UNKNOWN", "",
                                          source=UNKNOWN, ptype="text")
        self.feed_layer_thickness_mm = Parameter(f"{sep_id}.feed_layer_mm", 0.0, "mm",
                                                 source=CALIBRATION_REQUIRED)
        self.splitter_position = Parameter(f"{sep_id}.splitter_position", 0.0, "deg",
                                           source=CALIBRATION_REQUIRED)
        self.moisture_max_pct = Parameter(f"{sep_id}.moisture_max", 0.0, "%",
                                          source=CALIBRATION_REQUIRED)
        self.capacity_t_h = Parameter(f"{sep_id}.capacity", 0.0, "t/h",
                                      source=CALIBRATION_REQUIRED)  # Section 130: no invented capacity
        self.power_kw = Parameter(f"{sep_id}.power", 0.0, "kW", source=UNKNOWN)  # Section 88
        self.partition_curve = default_partition_curve(self.field_g.value)
        self.calibration_state = "UNCALIBRATED"
        self._peripheral_speed = None

    # geometry derivation (Section 19)
    def sync_geometry(self):
        self.diameter_m.value = 2.0 * self.radius_m.value
        self._peripheral_speed = units.peripheral_speed(self.diameter_m.value, self.rpm.value)

    @property
    def peripheral_speed_ms(self) -> float:
        return units.peripheral_speed(self.diameter_m.value, self.rpm.value)

    def derived_geometry(self) -> dict:
        d, l = self.diameter_m.value, self.length_m.value
        return {
            "diameter_m": d,
            "circumference_m": units.drum_circumference(d),
            "surface_area_m2": units.drum_surface_area(d, l),
            "drum_volume_m3": units.drum_internal_volume(d, l),
            "peripheral_speed_ms": self.peripheral_speed_ms,
            "note": "Drum internal volume is geometry only, NOT process capacity (Section 19).",
        }

    def set_field(self, value: float, unit: str):
        self.field_g.value = units.convert(value, unit, "G", "field")
        self.partition_curve = default_partition_curve(self.field_g.value)

    def p_magnetic(self, size_mm: float, fe_pct: float, liberation_pct: float) -> float:
        """Partition probability from the correlation model (Sections 25-26).

        MODEL RESULT, not SITE VERIFIED (Section 113).
        """
        return _p_from_model(size_mm, self.field_g.value, liberation_pct)

    # Gangue entrainment to magnetics (ENGINEERING CORRELATION proxy;
    # calibrate with assay testwork - Section 112)
    GANGUE_ENTRAINMENT = 0.05
    MAGNETITE_FE_PCT = 72.36   # stoichiometric Fe3O4 (PUBLISHED RESEARCH)

    def process(self, feed: Stream, out_ids: tuple, magnetite_fe_share: float = 0.75) -> tuple:
        """Mineralogy-driven two-phase partition split (Sections 25, 26, 86).

        Per size fraction (mass m, Fe grade g):
          magnetite mineral mass share  ms = g * magnetite_fe_share / 72.36
          magnetite Fe follows the size/liberation partition P(magnetic);
          gangue mass reports to tail with a small entrainment factor.
        Fe is conserved EXACTLY per fraction. This yields real grade
        upgrading. magnetite_fe_share = share of Fe inside the magnetite
        phase (USER INPUT, default declared as assumption).
        MODEL RESULT - not SITE VERIFIED until calibrated (Section 113).
        """
        self.sync_geometry()
        mag_id, tail_id = out_ids
        dry = feed.dry_mass_flow_t_h
        mag_masses, tail_masses, mag_fes, tail_fes = [], [], [], []
        for f in feed.psd.fractions:
            pm = self.p_magnetic(f.geometric_mean_mm, f.fe_pct, f.liberation_pct)
            g = f.fe_pct / 100.0                    # fraction Fe grade
            ms = min(0.95, (g * magnetite_fe_share) / (self.MAGNETITE_FE_PCT / 100.0)) if g > 0 else 0.0
            ent = self.GANGUE_ENTRAINMENT
            m_frac = f.mass_pct
            fe_in_frac = m_frac * g                 # Fe units per 100 mass units
            # mass split
            mag_m = m_frac * (ms * pm + (1.0 - ms) * ent)
            tail_m = m_frac - mag_m
            # Fe split (exact conservation by subtraction)
            mag_fe = fe_in_frac * (magnetite_fe_share * pm + (1.0 - magnetite_fe_share) * ent)
            tail_fe = fe_in_frac - mag_fe
            mag_masses.append(mag_m); tail_masses.append(tail_m)
            mag_fes.append(mag_fe); tail_fes.append(tail_fe)
        tm, tt = sum(mag_masses), sum(tail_masses)
        mag = Stream(stream_id=mag_id, source_equipment=self.sep_id,
                     destination_equipment="NEXT", material=feed.material)
        tail = Stream(stream_id=tail_id, source_equipment=self.sep_id,
                      destination_equipment="NEXT", material=feed.material)
        mag.psd = PSD([PSDFraction(f.size_lower_mm, f.size_upper_mm, m,
                                   (fe / m * 100.0 if m > 0 else 0.0))
                       for f, m, fe in zip(feed.psd.fractions, mag_masses, mag_fes)],
                      source="DERIVED VALUE")
        tail.psd = PSD([PSDFraction(f.size_lower_mm, f.size_upper_mm, m,
                                    (fe / m * 100.0 if m > 0 else 0.0))
                        for f, m, fe in zip(feed.psd.fractions, tail_masses, tail_fes)],
                       source="DERIVED VALUE")
        mag.set_dry_mass_flow(dry * (tm / 100.0) if tm > 0 else 0.0, feed.moisture_pct)
        mag.fe_grade_pct = (sum(mag_fes) / tm * 100.0) if tm > 0 else 0.0
        tail.set_dry_mass_flow(dry * (tt / 100.0) if tt > 0 else 0.0, feed.moisture_pct)
        tail.fe_grade_pct = (sum(tail_fes) / tt * 100.0) if tt > 0 else 0.0
        return mag, tail


# ------------------------------------------------------------------ screen --
class Screen:
    """Vibrating screen, 3 mm aperture default (Sections 29-31)."""

    def __init__(self, screen_id: str, aperture_mm: float = 3.0):
        self.screen_id = screen_id
        self.width_m = Parameter(f"{screen_id}.width", 2.4, "m", source=USER_INPUT, validator=positive)
        self.length_m = Parameter(f"{screen_id}.length", 6.0, "m", source=USER_INPUT, validator=positive)
        self.aperture_mm = Parameter(f"{screen_id}.aperture", aperture_mm, "mm",
                                     source=USER_INPUT, validator=positive)
        self.open_area_pct = Parameter(f"{screen_id}.open_area", 0.0, "%", source=CALIBRATION_REQUIRED)
        self.inclination_deg = Parameter(f"{screen_id}.inclination", 0.0, "deg", source=USER_INPUT)
        self.stroke_mm = Parameter(f"{screen_id}.stroke", 0.0, "mm", source=CALIBRATION_REQUIRED)
        self.frequency_hz = Parameter(f"{screen_id}.frequency", 0.0, "Hz", source=CALIBRATION_REQUIRED)
        self.efficiency = Parameter(f"{screen_id}.efficiency", 0.85, "-", source=USER_INPUT,
                                    validator=fraction_range)
        self.capacity_t_h = Parameter(f"{screen_id}.capacity", 0.0, "t/h", source=CALIBRATION_REQUIRED)
        self.power_kw = Parameter(f"{screen_id}.power", 0.0, "kW", source=UNKNOWN)
        self.blinding = False
        self.pegging = False

    @property
    def area_m2(self) -> float:
        return self.width_m.value * self.length_m.value

    def process(self, feed: Stream, out_ids: tuple) -> tuple:
        under_id, over_id = out_ids
        ap = self.aperture_mm.value  # mm
        under_psd, over_psd, over_frac = feed.psd.split_by_aperture(
            ap, efficiency=self.efficiency.value)
        dry = feed.dry_mass_flow_t_h
        under = Stream(stream_id=under_id, source_equipment=self.screen_id,
                       wet_mass_flow_t_h=feed.wet_mass_flow_t_h * (1 - over_frac),
                       moisture_pct=feed.moisture_pct,
                       fe_grade_pct=under_psd.weighted_fe() if under_psd.total_mass_pct() > 0 else feed.fe_grade_pct,
                       psd=under_psd, material=feed.material)
        over = Stream(stream_id=over_id, source_equipment=self.screen_id,
                      wet_mass_flow_t_h=feed.wet_mass_flow_t_h * over_frac,
                      moisture_pct=feed.moisture_pct,
                      fe_grade_pct=over_psd.weighted_fe() if over_psd.total_mass_pct() > 0 else feed.fe_grade_pct,
                      psd=over_psd, material=feed.material)
        # guard: graded masses
        if under_psd.total_mass_pct() > 0:
            under.set_dry_mass_flow(dry * (1 - over_frac), feed.moisture_pct)
        if over_psd.total_mass_pct() > 0:
            over.set_dry_mass_flow(dry * over_frac, feed.moisture_pct)
        return under, over


# ----------------------------------------------------------------- crusher --
class HydroconeCrusher:
    """Hydrocone crusher model (Sections 33-35).

    Product PSD: uses a crushing-matrix (Whiten-style B distribution,
    ENGINEERING CORRELATION) anchored to CSS — NOT a fixed reduction ratio.
    Without site data the user must supply/validate the product distribution.
    """
    MODEL_VERSION = "CrusherModel v1"

    def __init__(self, crusher_id: str, kind: str):
        self.crusher_id = crusher_id
        self.kind = kind  # "COARSE" | "FINE"
        self.manufacturer = Parameter(f"{crusher_id}.manufacturer", "UNKNOWN", "",
                                      source=UNKNOWN, ptype="text")
        self.model_name = Parameter(f"{crusher_id}.model", "UNKNOWN", "",
                                    source=UNKNOWN, ptype="text")
        self.max_feed_mm = Parameter(f"{crusher_id}.max_feed", 0.0, "mm", source=CALIBRATION_REQUIRED)
        self.css_mm = Parameter(f"{crusher_id}.css", 5.0 if kind == "FINE" else 35.0, "mm",
                                source=USER_INPUT, validator=positive)
        self.oss_mm = Parameter(f"{crusher_id}.oss", 0.0, "mm", source=CALIBRATION_REQUIRED)
        self.eccentric_throw_mm = Parameter(f"{crusher_id}.throw", 0.0, "mm", source=CALIBRATION_REQUIRED)
        self.speed_rpm = Parameter(f"{crusher_id}.speed", 0.0, "rpm", source=CALIBRATION_REQUIRED)
        self.power_kw = Parameter(f"{crusher_id}.power", 0.0, "kW", source=UNKNOWN)  # Section 88
        self.chamber = Parameter(f"{crusher_id}.chamber", "UNKNOWN", "", source=UNKNOWN, ptype="text")
        self.capacity_t_h = Parameter(f"{crusher_id}.capacity", 0.0, "t/h", source=CALIBRATION_REQUIRED)
        self.user_defined_product = False

    @property
    def reduction_ratio(self) -> float:
        # DERIVED, reported for information only
        f80 = max(self._f80_in, 1e-6)
        return f80 / max(self.css_mm.value, 1e-6) if self._f80_in else 0.0

    _f80_in: float = 0.0

    def product_psd(self, feed_psd: PSD) -> PSD:
        """Crushing matrix: fractions above 3*CSS crushed to a Rosin-Rammler
        distribution around CSS; fines below CSS pass largely uncrushed
        (ENGINEERING CORRELATION, Tier 5 — validate with testwork, Section 112)."""
        css = self.css_mm.value
        out = PSD(source="DERIVED VALUE")
        for f in feed_psd.fractions:
            d = f.geometric_mean_mm
            if d <= css * 0.3:
                # fines pass essentially uncrushed
                out.fractions.append(PSDFraction(f.size_lower_mm, f.size_upper_mm,
                                                 f.mass_pct, f.fe_pct))
            else:
                # crushed portion -> Rosin-Rammler b(x), d63 = 0.75*CSS, n=2.2
                # (ENGINEERING CORRELATION; calibrate with testwork, Section 112)
                rr = PSD(source="ENGINEERING CORRELATION")
                cuts = [50.0, 25.0, 10.0, 5.0, 3.0, 1.0, 0.5, 0.1, 0.05]
                d63 = 0.75 * css
                n = 2.2
                rrp = [100.0 * (1.0 - math.exp(-((c / d63) ** n) * math.log(2))) for c in cuts]
                bands = []
                prev = 100.0
                for p in rrp:
                    bands.append(max(prev - p, 0.0))
                    prev = p
                bands.append(prev)
                m = f.mass_pct
                for (lo, hi, _), bm in zip([ (50,1e9,">50"),(25,50,"25-50"),(10,25,"10-25"),
                                             (5,10,"5-10"),(3,5,"3-5"),(1,3,"1-3"),
                                             (0.5,1,"0.5-1"),(0.1,0.5,"0.1-0.5"),(1e-9,0.1,"<0.1") ], bands):
                    out.fractions.append(PSDFraction(lo, hi, m * bm / 100.0, f.fe_pct))
        # renormalise
        tot = sum(f.mass_pct for f in out.fractions)
        if tot > 0:
            for f in out.fractions:
                f.mass_pct *= 100.0 / tot
        return out

    def process(self, feed: Stream, out_id: str) -> Stream:
        self._f80_in = self._estimate_f80(feed.psd)
        prod_psd = self.product_psd(feed.psd)
        out = Stream(stream_id=out_id, source_equipment=self.crusher_id,
                     wet_mass_flow_t_h=feed.wet_mass_flow_t_h,
                     moisture_pct=feed.moisture_pct,
                     fe_grade_pct=feed.fe_grade_pct,  # crushing conserves Fe mass & grade (no loss model)
                     psd=prod_psd, material=feed.material)
        return out

    @staticmethod
    def _estimate_f80(psd: PSD) -> float:
        cum = 0.0
        for f in sorted(psd.fractions, key=lambda x: x.size_upper_mm):
            cum += f.mass_pct
            if cum >= 80.0:
                return f.size_upper_mm
        return 50.0
