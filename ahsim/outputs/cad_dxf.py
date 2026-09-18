"""CAD / DXF Engine (Spec Sections 53-58, 125).

Real AutoCAD-standard DXF via ezdxf with the 14 mandatory layers,
engineering annotation (stream IDs, flow rates, grades, arrows) and a
title block carrying the developer identity.
"""
from __future__ import annotations

import math

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

from ..app.metadata import CONTACT, DEVELOPER_EN, PROJECT_NAME_DEFAULT, SOFTWARE_NAME, VERSION

LAYERS = {
    "EQUIPMENT": (7, "CONTINUOUS"),
    "STREAM": (3, "CONTINUOUS"),
    "ARROW": (3, "CONTINUOUS"),
    "TEXT": (2, "CONTINUOUS"),
    "DIMENSION": (8, "CONTINUOUS"),
    "RECYCLE": (30, "DASHED"),
    "FEED": (1, "CONTINUOUS"),
    "PRODUCT": (4, "CONTINUOUS"),
    "TAIL": (250, "CONTINUOUS"),
    "CRUSHING": (11, "CONTINUOUS"),
    "SCREENING": (5, "CONTINUOUS"),
    "MAGNETIC": (6, "CONTINUOUS"),
    "ANNOTATION": (9, "CONTINUOUS"),
    "TITLE": (7, "CONTINUOUS"),
}

# layout: node_id -> (x, y)  [engineering metres, auto layout (Section 54)]
LAYOUT = {
    "RAW_ORE": (0, 40), "GRIZZLY": (12, 40), "GYRATORY": (24, 40), "DISTRIBUTION": (36, 40),
    "SEP-01": (48, 62), "SEP-02": (48, 54), "SEP-03": (48, 46), "SEP-04": (48, 38),
    "SEP-05": (48, 30), "SEP-06": (48, 22), "MERGER": (60, 42),
    "SCR-01": (72, 50), "SCR-02": (72, 42), "SCR-03": (72, 34),
    "HYD-COARSE": (86, 42), "HYD-FINE": (98, 42), "FINAL-SEP": (112, 42),
    "PRODUCT": (128, 50), "TAILINGS": (128, 32),
}
BOX_W, BOX_H = 8.0, 5.0


def _box(msp, x, y, w, h, layer, label, sub=""):
    msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True,
                       dxfattribs={"layer": layer})
    msp.add_text(label, dxfattribs={"layer": "TEXT", "height": 1.1}
                 ).set_placement((x + 0.4, y + h / 2 + (0.9 if sub else 0)), align=TA.MIDDLE_LEFT)
    if sub:
        msp.add_text(sub, dxfattribs={"layer": "ANNOTATION", "height": 0.7}
                     ).set_placement((x + 0.4, y + h / 2 - 1.2), align=TA.MIDDLE_LEFT)


def _arrow(msp, x1, y1, x2, y2, layer):
    msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})
    ang = math.atan2(y2 - y1, x2 - x1)
    L, w = 1.4, 0.7
    p1 = (x2 - L * math.cos(ang) + w * math.sin(ang), y2 - L * math.sin(ang) - w * math.cos(ang))
    p2 = (x2 - L * math.cos(ang) - w * math.sin(ang), y2 - L * math.sin(ang) + w * math.cos(ang))
    msp.add_lwpolyline([p1, (x2, y2), p2], dxfattribs={"layer": "ARROW"})


def _label_stream(msp, x, y, sid, flow, fe, layer="TEXT"):
    msp.add_text(f"{sid}: {flow:.1f} t/h | Fe {fe:.2f}%",
                 dxfattribs={"layer": "ANNOTATION", "height": 0.8}).set_placement((x, y))


def export_dxf(result, path: str, project_name: str = PROJECT_NAME_DEFAULT,
               drawing_number: str = "AH-SIM-001", revision: str = "A") -> str:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = 6  # meters
    for name, (color, lt) in LAYERS.items():
        doc.layers.add(name=name, color=color, linetype=lt)
    doc.header["$INSUNITS"] = 6

    # equipment boxes
    for nid, (x, y) in LAYOUT.items():
        layer = "MAGNETIC" if nid.startswith(("SEP", "FIN")) else \
            "SCREENING" if nid.startswith("SCR") else \
            "CRUSHING" if nid.startswith(("HYD", "GYRATORY")) else "EQUIPMENT"
        sub = {"GYRATORY": "PRIMARY GYRATORY", "DISTRIBUTION": "6-WAY DISTRIBUTION",
               "MERGER": "6-1 MERGER", "FINAL-SEP": "FIN-01 / FIN-02 1400-2000 G"}.get(nid, "")
        _box(doc.modelspace(), x, y, BOX_W, BOX_H, layer, nid, sub)

    # stream arrows from result data
    k = result.kpis
    streams = result.streams

    def s_by_id(sid):
        return streams.get(sid)

    msp = doc.modelspace()
    _arrow(msp, 8, 40 + 2.5, 12, 40 + 2.5, "FEED")
    _arrow(msp, 20, 42.5, 24, 42.5, "FEED")
    _arrow(msp, 32, 42.5, 36, 42.5, "EQUIPMENT")
    for i, sx in enumerate([62, 54, 46, 38, 30, 22]):
        _arrow(msp, 44, 42.5, 48, sx, "MAGNETIC")
        _arrow(msp, 56, sx, 60, 44.5, "MAGNETIC")
    for i, (sx, sy) in enumerate([(68, 52.5), (68, 44.5), (68, 36.5)]):
        _arrow(msp, 60, 44.5, 72, sy, "SCREENING")
        _arrow(msp, 80, sy, 86, 44.5, "SCREENING")
    _arrow(msp, 94, 44.5, 98, 44.5, "CRUSHING")
    _arrow(msp, 104, 44.5, 110, 47, "RECYCLE")   # fine cone -> back to screens (recycle)
    _arrow(msp, 98, 47, 72, 47, "RECYCLE")
    _arrow(msp, 110, 44.5, 112, 44.5, "MAGNETIC")
    _arrow(msp, 120, 44.5, 128, 52.5, "PRODUCT")
    _arrow(msp, 120, 44.5, 128, 34.5, "TAIL")

    # engineering annotations from the actual simulation result
    _label_stream(msp, 1, 44, "S-FEED", k["feed_t_h"], result.config.feed_fe_pct, "FEED")
    _label_stream(msp, 122, 54, "S-PRODUCT", k["product_t_h"], k["product_fe_pct"], "PRODUCT")
    _label_stream(msp, 122, 30, "S-TAIL", k["tail_t_h"], k["tail_fe_pct"], "TAIL")
    _label_stream(msp, 99, 40, "S-FINE-OUT (RECYCLE)", k["circulating_load_t_h"],
                  s_by_id("S-FINE-OUT").fe_grade_pct if "S-FINE-OUT" in streams else 0, "RECYCLE")
    msp.add_text(f"CONVERGENCE: {result.status} | SIM ID: {result.simulation_id}",
                 dxfattribs={"layer": "ANNOTATION", "height": 1.2}).set_placement((0, 6))
    msp.add_text("MODEL RESULT - requires calibration before site verification (Section 113)",
                 dxfattribs={"layer": "ANNOTATION", "height": 1.0}).set_placement((0, 3))

    # ---------------- title block (Section 58, 125) ----------------
    tx, ty, tw, th = 150, 0, 45, 22
    msp.add_lwpolyline([(tx, ty), (tx + tw, ty), (tx + tw, ty + th), (tx, ty + th)],
                       close=True, dxfattribs={"layer": "TITLE"})
    rows = [
        ("PROJECT NAME", project_name), ("PLANT NAME", "Dry Magnetite Processing Plant"),
        ("DRAWING NAME", "PROCESS FLOW SCHEMATIC - DRY MAGNETIC CIRCUIT"),
        ("DRAWING NUMBER", drawing_number), ("REVISION", revision),
        ("DATE", result.timestamp[:10]), ("SOFTWARE", f"{SOFTWARE_NAME} v{VERSION}"),
        ("DEVELOPER", DEVELOPER_EN.upper()), ("CONTACT", CONTACT),
        ("CONVERGENCE", result.status),
    ]
    for i, (label, value) in enumerate(rows):
        yy = ty + th - (i + 1) * (th / len(rows))
        msp.add_line((tx, yy), (tx + tw, yy), dxfattribs={"layer": "TITLE"})
        msp.add_text(label, dxfattribs={"layer": "TITLE", "height": 0.8}
                     ).set_placement((tx + 0.8, yy + th / len(rows) - 1.1), align=TA.MIDDLE_LEFT)
        msp.add_text(str(value), dxfattribs={"layer": "TEXT", "height": 1.0}
                     ).set_placement((tx + 14, yy + th / len(rows) - 1.1), align=TA.MIDDLE_LEFT)

    doc.saveas(path)
    return path
