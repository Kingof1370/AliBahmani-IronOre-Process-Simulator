"""Material & mineralogical model (Spec Sections 09, 13, 14).

Mineral species are open-ended; the seven defaults are seeded only.
Assay components follow Section 09 exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.params import (Parameter, ValidationError, percent_range, non_negative,
                           DEFAULT_VALUE, USER_INPUT, UNKNOWN)

DEFAULT_MINERALS = ["Magnetite", "Hematite", "Goethite", "Gangue", "Quartz", "Clay", "Other"]

ASSAY_COMPONENTS = ["Fe", "FeO", "Fe2O3", "SiO2", "Al2O3", "CaO", "MgO", "Mn", "P", "S", "Other"]

# Fe content inside pure minerals (stoichiometric, PUBLISHED RESEARCH - standard
# chemistry: Fe3O4 = 72.36% Fe, Fe2O3 = 69.94% Fe, FeOOH = 62.86% Fe). These are
# exact stoichiometric constants, not plant data.
MINERAL_FE_PCT = {"Magnetite": 72.36, "Hematite": 69.94, "Goethite": 62.86}


@dataclass
class MineralSpecies:
    name: str
    density_t_m3: float = 0.0      # UNKNOWN unless provided
    fe_pct: float = 0.0            # stoichiometric for known Fe minerals
    magnetic: bool = False
    source: str = DEFAULT_VALUE


class MaterialModel:
    """Feed assay + mineralogy with wet/dry basis handling (Section 10)."""

    def __init__(self):
        self.assay: Dict[str, Parameter] = {}
        for comp in ASSAY_COMPONENTS:
            self.assay[comp] = Parameter(f"assay_{comp}", 0.0, "%", source=USER_INPUT,
                                         validator=percent_range)
        self.assay["Fe"].value = 18.5   # Section 11 example value - user editable, not hard-coded capacity
        self.minerals: Dict[str, MineralSpecies] = {}
        for name in DEFAULT_MINERALS:
            self.minerals[name] = MineralSpecies(
                name=name,
                fe_pct=MINERAL_FE_PCT.get(name, 0.0),
                magnetic=(name == "Magnetite"),
                source=("PUBLISHED RESEARCH" if name in MINERAL_FE_PCT else DEFAULT_VALUE),
            )
        self.mineral_share: Dict[str, Parameter] = {
            name: Parameter(f"mineral_{name}", 0.0, "% of feed", source=USER_INPUT,
                            validator=percent_range)
            for name in DEFAULT_MINERALS
        }
        # Declared example shares (USER INPUT - editable): magnetite-dominant feed
        self.mineral_share["Magnetite"].value = 25.0
        self.mineral_share["Hematite"].value = 5.0
        self.mineral_share["Gangue"].value = 40.0
        self.mineral_share["Quartz"].value = 25.0
        self.mineral_share["Clay"].value = 5.0

    def validate_mineral_share(self) -> float:
        total = sum(p.value for p in self.mineral_share.values())
        if abs(total - 100.0) > 0.1:
            raise ValidationError(f"mineral shares sum to {total:.2f}%, must be 100%")
        return total

    def fe_from_mineralogy(self) -> float:
        """Fe % computed from mineral shares (cross-check of manual assay)."""
        fe = 0.0
        for name, p in self.mineral_share.items():
            fe += (p.value / 100.0) * self.minerals[name].fe_pct
        return fe

    def as_dict(self) -> dict:
        return {
            "assay": {k: v.as_dict() for k, v in self.assay.items()},
            "minerals": {k: v.__dict__ for k, v in self.minerals.items()},
            "mineral_share": {k: v.as_dict() for k, v in self.mineral_share.items()},
        }
