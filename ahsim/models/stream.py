"""Stream object — real material flows with full tracking (Spec Sections 10, 49, 50)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.params import DEFAULT_VALUE, DERIVED_VALUE
from .psd import PSD


@dataclass
class Stream:
    stream_id: str
    source_equipment: str = ""
    destination_equipment: str = ""
    wet_mass_flow_t_h: float = 0.0
    moisture_pct: float = 0.0
    fe_grade_pct: float = 0.0
    psd: PSD = field(default_factory=PSD)
    mineralogy: dict = field(default_factory=dict)
    temperature_c: Optional[float] = None
    pressure_bar: Optional[float] = None
    status: str = "OK"
    material: str = "IRON ORE"
    source_class: str = DERIVED_VALUE

    # --- basis system (Section 10) ------------------------------------------
    @property
    def dry_mass_flow_t_h(self) -> float:
        return self.wet_mass_flow_t_h * (1.0 - self.moisture_pct / 100.0)

    def set_dry_mass_flow(self, dry_t_h: float, moisture_pct: float) -> None:
        self.moisture_pct = moisture_pct
        self.wet_mass_flow_t_h = dry_t_h / (1.0 - moisture_pct / 100.0) if moisture_pct < 100 else 0.0

    @property
    def fe_mass_flow_t_h(self) -> float:
        return self.dry_mass_flow_t_h * self.fe_grade_pct / 100.0

    # --- stream algebra ------------------------------------------------------
    def copy(self, new_id: str) -> "Stream":
        return Stream(
            stream_id=new_id, source_equipment=self.source_equipment,
            destination_equipment=self.destination_equipment,
            wet_mass_flow_t_h=self.wet_mass_flow_t_h, moisture_pct=self.moisture_pct,
            fe_grade_pct=self.fe_grade_pct, psd=self.psd.copy(),
            mineralogy=dict(self.mineralogy), temperature_c=self.temperature_c,
            pressure_bar=self.pressure_bar, status=self.status, material=self.material,
            source_class=self.source_class,
        )

    def mix(self, other: "Stream", out_id: str, src: str, dst: str) -> "Stream":
        """Merge two streams conserving dry mass and Fe mass (PSD mass-weighted)."""
        m1, m2 = self.dry_mass_flow_t_h, other.dry_mass_flow_t_h
        tot = m1 + m2
        if tot <= 0:
            out = Stream(stream_id=out_id, source_equipment=src, destination_equipment=dst,
                         wet_mass_flow_t_h=0.0, moisture_pct=0.0, fe_grade_pct=0.0)
            out.status = "ZERO FLOW"
            return out
        fe = (m1 * self.fe_grade_pct + m2 * other.fe_grade_pct) / tot
        psd = self.psd.merge_weighted((self.psd, m1), (other.psd, m2)) \
            if (self.psd.fractions or other.psd.fractions) else PSD()
        w1 = m1 / tot
        wet = self.wet_mass_flow_t_h + other.wet_mass_flow_t_h
        moist = (1.0 - tot / wet) * 100.0 if wet > 0 else 0.0
        out = Stream(stream_id=out_id, source_equipment=src, destination_equipment=dst,
                     wet_mass_flow_t_h=wet, moisture_pct=moist, fe_grade_pct=fe,
                     psd=psd, status="OK")
        out.reconcile_psd_fe()
        return out

    def reconcile_psd_fe(self) -> None:
        """Force PSD-implied Fe to equal the stream Fe grade (audit consistency)."""
        if self.psd.fractions:
            self.psd.scale_fe_to(self.fe_grade_pct)

    def as_dict(self) -> dict:
        return {
            "stream_id": self.stream_id, "source": self.source_equipment,
            "destination": self.destination_equipment,
            "wet_mass_flow_t_h": round(self.wet_mass_flow_t_h, 6),
            "dry_mass_flow_t_h": round(self.dry_mass_flow_t_h, 6),
            "moisture_pct": self.moisture_pct,
            "fe_grade_pct": round(self.fe_grade_pct, 6),
            "fe_mass_flow_t_h": round(self.fe_mass_flow_t_h, 6),
            "material": self.material, "status": self.status,
            "psd_source": self.psd.source,
            "psd": self.psd.as_dict(),
        }
