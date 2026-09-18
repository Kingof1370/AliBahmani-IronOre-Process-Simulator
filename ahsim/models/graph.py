"""Process graph (flowsheet) model (Spec Sections 15-17, 29, 39, 50-51)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..core.params import Parameter, USER_INPUT, ValidationError
from .equipment import MagneticSeparator, Screen, HydroconeCrusher
from .stream import Stream


@dataclass
class GraphNode:
    node_id: str
    ntype: str          # FEED | EQUIPMENT | SPLITTER | MERGER | PRODUCT | TAIL
    equipment: object = None
    position: Tuple[float, float] = (0.0, 0.0)


class ProcessGraph:
    """Directed graph: nodes are equipment/feed/product, edges are streams."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self._streams: Dict[str, Stream] = {}

    def add_node(self, node_id: str, ntype: str, equipment=None, pos=(0.0, 0.0)) -> GraphNode:
        n = GraphNode(node_id, ntype, equipment, pos)
        self.nodes[node_id] = n
        return n

    def remove_node(self, node_id: str):
        self.nodes.pop(node_id, None)
        for sid in [s for s, st in self._streams.items()
                    if st.source_equipment == node_id or st.destination_equipment == node_id]:
            self._streams.pop(sid, None)

    def add_stream(self, stream: Stream):
        self._streams[stream.stream_id] = stream

    def get_stream(self, sid: str) -> Optional[Stream]:
        return self._streams.get(sid)

    def streams(self) -> List[Stream]:
        return list(self._streams.values())

    def downstream_of(self, node_id: str) -> List[Stream]:
        return [s for s in self._streams.values() if s.source_equipment == node_id]

    def upstream_of(self, node_id: str) -> List[Stream]:
        return [s for s in self._streams.values() if s.destination_equipment == node_id]


def build_default_plant() -> dict:
    """Default project circuit (Section 15, 101):
    Grizzly -> Primary Gyratory -> Distribution -> 6 pre-separators -> merger
    -> 3 screens (3 mm) -> coarse+fine hydrocone -> recycle -> 2 final separators."""
    plant = {"grizzly": {"type": "GRIZZLY FEEDER"},
             "gyratory": {"type": "PRIMARY GYRATORY", "css_mm": 200.0, "kind": "PRIMARY"}}
    pre = [MagneticSeparator(f"SEP-0{i}", "PRE-PROCESSING") for i in range(1, 7)]
    for s in pre:
        s.set_field(3000, "G")
    screens = [Screen(f"SCR-0{i}", 3.0) for i in range(1, 4)]
    coarse = HydroconeCrusher("HYD-COARSE", "COARSE")
    fine = HydroconeCrusher("HYD-FINE", "FINE")
    finals = [MagneticSeparator(f"FIN-0{i}", "FINAL") for i in range(1, 3)]
    for s in finals:
        s.set_field(1400, "G")
    return {"pre_separators": pre, "screens": screens,
            "coarse_crusher": coarse, "fine_crusher": fine, "final_separators": finals}


class FeedDistribution:
    """Feed distribution node (Sections 16-17)."""

    MODES = ("EQUAL", "MANUAL", "CALCULATED")

    def __init__(self, n_units: int):
        self.n_units = n_units
        self.mode = "EQUAL"
        self.manual_shares: List[float] = [0.0] * n_units

    def shares(self) -> List[float]:
        if self.mode == "EQUAL":
            return [1.0 / self.n_units] * self.n_units
        if self.mode == "MANUAL":
            total = sum(self.manual_shares)
            if abs(total - 100.0) > 1e-6:
                raise ValidationError(
                    f"manual distribution sums to {total:.4f}%, must be exactly 100%")
            return [s / 100.0 for s in self.manual_shares]
        raise ValidationError("CALCULATED distribution requires the distribution solver "
                              "(data-dependent: requires equipment capacities, see Section 130)")
