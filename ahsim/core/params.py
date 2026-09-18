"""Parameter metadata system (Spec Sections 05, 79, 80, 84, 85).

Every engineering number in the software is a Parameter carrying:
value, unit, type, source classification, confidence, timestamp,
editability and a validation hook. Numbers without a source are
registered as UNKNOWN / USER_DEFINED / CALIBRATION_REQUIRED — never invented.
"""
from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Source Classification (Spec Section 05)
MANUFACTURER_DATA = "MANUFACTURER DATA"
PUBLISHED_RESEARCH = "PUBLISHED RESEARCH"
SITE_MEASUREMENT = "SITE MEASUREMENT"
USER_INPUT = "USER INPUT"
CALIBRATION_DATA = "CALIBRATION DATA"
ENGINEERING_CORRELATION = "ENGINEERING CORRELATION"
DERIVED_VALUE = "DERIVED VALUE"
DEFAULT_VALUE = "DEFAULT VALUE"
USER_DEFINED = "USER DEFINED"
UNKNOWN = "UNKNOWN"
CALIBRATION_REQUIRED = "CALIBRATION REQUIRED"

# Engineering source hierarchy tiers (Spec Section 84) - lower number = higher priority
TIER = {
    SITE_MEASUREMENT: 1,
    MANUFACTURER_DATA: 2,
    CALIBRATION_DATA: 2,       # validated plant test data
    PUBLISHED_RESEARCH: 4,
    ENGINEERING_CORRELATION: 5,
    USER_INPUT: 6,
    USER_DEFINED: 6,
    DEFAULT_VALUE: 7,
    DERIVED_VALUE: 7,
    UNKNOWN: 99,
    CALIBRATION_REQUIRED: 99,
}

# Confidence levels (Spec Section 85)
HIGH, MEDIUM, LOW = "High", "Medium", "Low"
CONF_UNKNOWN = "Unknown"


class ValidationError(ValueError):
    pass


@dataclass
class Parameter:
    name: str
    value: Any
    unit: str = ""
    ptype: str = "scalar"          # scalar | text | list | table
    source: str = DEFAULT_VALUE
    confidence: str = LOW
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    editable: bool = True
    validator: Optional[Callable[[Any], None]] = None
    note: str = ""

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.validator is not None:
            self.validator(self.value)
        if isinstance(self.value, float) and (math.isnan(self.value) or math.isinf(self.value)):
            raise ValidationError(f"parameter '{self.name}' is NaN/Inf")

    def as_dict(self) -> dict:
        return {
            "name": self.name, "value": self.value, "unit": self.unit,
            "type": self.ptype, "source": self.source,
            "confidence": self.confidence, "timestamp": self.timestamp,
            "editable": self.editable, "note": self.note,
        }


def positive(v: float) -> None:
    if v is None or float(v) <= 0:
        raise ValidationError(f"value must be > 0 (got {v})")


def non_negative(v: float) -> None:
    if v is None or float(v) < 0:
        raise ValidationError(f"value must be >= 0 (got {v})")


def percent_range(v: float) -> None:
    if v is None or not (0.0 <= float(v) <= 100.0):
        raise ValidationError(f"percent value must be in [0, 100] (got {v})")


def fraction_range(v: float) -> None:
    if v is None or not (0.0 <= float(v) <= 1.0):
        raise ValidationError(f"fraction value must be in [0, 1] (got {v})")


def audit_entry(name: str, old: Any, new: Any, scenario: str, actor: str = "user") -> dict:
    """Audit trail record (Spec Section 92)."""
    return {
        "parameter": name, "old_value": old, "new_value": new,
        "date": datetime.datetime.utcnow().date().isoformat(),
        "time": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "scenario": scenario, "actor": actor,
    }
