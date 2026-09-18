"""Animation & Video Engine (Spec Sections 68-75, 124).

Renders process animation frames from the REAL process graph and the REAL
SimulationResult (stream flows drive particle density), then encodes
1920x1080 H.264 MP4 via ffmpeg. NOT a pre-recorded animation.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

from ..app.metadata import CONTACT, DEVELOPER_EN, PROJECT_NAME_DEFAULT, SOFTWARE_NAME, VERSION

W, H = 1920, 1080
FPS = 24

FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def _font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# node positions on 1920x1080 canvas (Section 15 circuit layout)
NODES = {
    "RAW_ORE": (70, 560, 150, 640), "GRIZZLY": (280, 560, 430, 640),
    "GYRATORY": (490, 560, 640, 640), "DIST": (700, 560, 800, 640),
    "SEP-01": (880, 130, 1020, 190), "SEP-02": (880, 230, 1020, 290),
    "SEP-03": (880, 330, 1020, 390), "SEP-04": (880, 430, 1020, 490),
    "SEP-05": (880, 530, 1020, 590), "SEP-06": (880, 630, 1020, 690),
    "MERGE": (1080, 560, 1160, 640),
    "SCR-01": (1230, 300, 1350, 360), "SCR-02": (1230, 430, 1350, 490),
    "SCR-03": (1230, 560, 1350, 620),
    "HYD-C": (1420, 430, 1560, 490), "HYD-F": (1420, 560, 1560, 620),
    "FIN": (1630, 480, 1750, 560),
    "PRODUCT": (1790, 380, 1900, 440), "TAILING": (1790, 640, 1900, 700),
}


def _center(k):
    x1, y1, x2, y2 = NODES[k]
    return (x1 + x2) / 2, (y1 + y2) / 2


EDGES = [
    ("RAW_ORE", "GRIZZLY"), ("GRIZZLY", "GYRATORY"), ("GYRATORY", "DIST"),
    ("DIST", "SEP-01"), ("DIST", "SEP-02"), ("DIST", "SEP-03"),
    ("DIST", "SEP-04"), ("DIST", "SEP-05"), ("DIST", "SEP-06"),
    ("SEP-01", "MERGE"), ("SEP-02", "MERGE"), ("SEP-03", "MERGE"),
    ("SEP-04", "MERGE"), ("SEP-05", "MERGE"), ("SEP-06", "MERGE"),
    ("MERGE", "SCR-01"), ("MERGE", "SCR-02"), ("MERGE", "SCR-03"),
    ("SCR-01", "HYD-C"), ("SCR-02", "HYD-C"), ("SCR-03", "HYD-C"),
    ("HYD-C", "HYD-F"), ("HYD-F", "SCR-01"),   # recycle
    ("SCR-01", "FIN"), ("SCR-02", "FIN"), ("SCR-03", "FIN"),
    ("FIN", "PRODUCT"), ("FIN", "TAILING"),
]
RECYCLE_EDGE = ("HYD-F", "SCR-01")


def _edge_path(a, b):
    """Polyline route avoiding equipment boxes (Section 54)."""
    ax, ay = _center(a)
    bx, by = _center(b)
    if abs(ay - by) < 5:
        return [(ax, ay), (bx, by)]
    midx = ax + (bx - ax) * 0.5
    return [(ax, ay), (midx, ay), (midx, by), (bx, by)]


def _draw_frame(result, t: float, title, intro_lines=None, summary_lines=None):
    img = Image.new("RGB", (W, H), (18, 22, 28))
    d = ImageDraw.Draw(img)
    f_big, f_med, f_sm = _font(44), _font(26), _font(20)

    if intro_lines is not None:
        y = H // 3
        for line, style in intro_lines:
            f = f_big if style == "big" else f_med
            d.text((W / 2, y), line, font=f, fill=(240, 240, 240), anchor="mm")
            y += 80
        return img
    if summary_lines is not None:
        y = 160
        for line, style in summary_lines:
            f = f_big if style == "big" else f_med
            color = (255, 200, 90) if style == "warn" else (240, 240, 240)
            d.text((100, y), line, font=f, fill=color, anchor="lm")
            y += 90
        return img

    # flowsheet
    for key, (x1, y1, x2, y2) in NODES.items():
        fill = (40, 80, 130)
        if key.startswith("SEP") or key == "FIN":
            fill = (120, 60, 130)
        if key in ("HYD-C", "HYD-F"):
            fill = (130, 90, 40)
        if key in ("PRODUCT",):
            fill = (30, 110, 60)
        if key in ("TAILING",):
            fill = (90, 90, 90)
        d.rectangle([x1, y1, x2, y2], fill=fill, outline=(200, 200, 200), width=2)
        d.text(((x1 + x2) / 2, (y1 + y2) / 2), key, font=_font(20), fill=(255, 255, 255),
               anchor="mm")

    k = result.kpis
    max_flow = max(k["screen_load_t_h"], k["circulating_load_t_h"], k["feed_t_h"], 1.0)

    # animated material particles along edges, density ~ flow rate (Section 70)
    for a, b in EDGES:
        pts = _edge_path(a, b)
        color = (255, 170, 60)
        width = 3
        if (a, b) == RECYCLE_EDGE:
            color = (255, 100, 100)
        if b == "PRODUCT":
            color = (80, 255, 130)
        if b == "TAILING":
            color = (160, 160, 160)
        # polyline length
        seg = []
        for i in range(len(pts) - 1):
            seg.append((pts[i], pts[i + 1]))
        total = sum(math.dist(p1, p2) for p1, p2 in seg)
        n_particles = 4
        for j in range(n_particles):
            u = ((t * 0.5) + j / n_particles) % 1.0
            dist = u * total
            acc = 0.0
            for p1, p2 in seg:
                L = math.dist(p1, p2)
                if acc + L >= dist:
                    f = (dist - acc) / L if L > 0 else 0
                    x = p1[0] + (p2[0] - p1[0]) * f
                    y = p1[1] + (p2[1] - p1[1]) * f
                    d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)
                    break
                acc += L
        # line + arrowhead
        d.line(pts, fill=color, width=width)

    # labels from real result
    d.text((70, 60), f"{SOFTWARE_NAME} v{VERSION}", font=f_big, fill=(255, 255, 255))
    d.text((70, 115), f"Feed {k['feed_t_h']:.0f} t/h | Product {k['product_t_h']:.1f} t/h @ "
                      f"{k['product_fe_pct']:.2f}% Fe | Fe Rec {k['fe_recovery_pct']:.2f}%",
           font=f_med, fill=(200, 220, 255))
    d.text((70, 150), f"Circulating Load {k['circulating_load_t_h']:.0f} t/h "
                      f"({k['circulating_load_pct']:.0f}%)  |  Status: {result.status}",
           font=f_med, fill=(120, 255, 140) if "CONVERGED" == result.status.split()[0] else (255, 160, 90))
    d.text((70, H - 60), f"Developed by: {DEVELOPER_EN}  |  Contact: {CONTACT}",
           font=f_sm, fill=(180, 180, 180))
    if result.status != "CONVERGED":
        d.text((W - 60, 40), "WARNING: NOT CONVERGED", font=f_med, fill=(255, 80, 80), anchor="ra")
    return img


def export_video(result, path: str, project_name: str = PROJECT_NAME_DEFAULT,
                 seconds: float = 8.0, fps: int = FPS) -> str:
    """Render frames from the real graph/result and encode H.264 MP4."""
    if not shutil.which("ffmpeg") and not os.path.exists("/usr/bin/ffmpeg"):
        raise RuntimeError("ffmpeg not found - video engine cannot run")
    tmp = tempfile.mkdtemp(prefix="ahsim_video_")
    n_frames = int(seconds * fps)
    intro_lines = [
        ("Industrial Mineral Processing Simulation", "big"),
        (project_name, "med"),
        ("Simulation Scenario: Scenario-001", "med"),
        (f"Developed by: {DEVELOPER_EN}   Contact: {CONTACT}", "med"),
    ]
    k = result.kpis
    summary_lines = [
        ("FINAL SUMMARY", "big"),
        (f"Feed: {k['feed_t_h']:.1f} t/h @ {result.config.feed_fe_pct:.2f}% Fe", "med"),
        (f"Final Product: {k['product_t_h']:.2f} t/h @ {k['product_fe_pct']:.2f}% Fe", "med"),
        (f"Fe Recovery: {k['fe_recovery_pct']:.2f}%   Mass Recovery: {k['mass_recovery_pct']:.2f}%", "med"),
        (f"Tailings: {k['tail_t_h']:.1f} t/h @ {k['tail_fe_pct']:.2f}% Fe", "med"),
        (f"Circulating Load: {k['circulating_load_t_h']:.1f} t/h ({k['circulating_load_pct']:.1f}%)", "med"),
        (f"Simulation Status: {result.status}", "warn" if result.status != "CONVERGED" else "med"),
        (f"Developed by: {DEVELOPER_EN}   Contact: {CONTACT}", "med"),
    ]
    for i in range(n_frames):
        t = i / fps
        if i < fps:  # 1 s intro
            frame = _draw_frame(result, t, project_name, intro_lines=intro_lines)
        elif i >= n_frames - 2 * fps:  # 2 s summary
            frame = _draw_frame(result, t, project_name, summary_lines=summary_lines)
        else:
            frame = _draw_frame(result, t, project_name)
        frame.save(os.path.join(tmp, f"f{i:05d}.png"))
    out = os.path.abspath(path)
    subprocess.run(["ffmpeg", "-y", "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), out],
                   check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out
