"""PDF Report Engine (Spec Sections 67, 126). Built with reportlab."""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from ..app.metadata import (CONTACT, DEVELOPER_EN, DEVELOPER_FA, MODEL_VERSIONS,
                            PROJECT_NAME_DEFAULT, SOFTWARE_NAME, VERSION)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(15 * mm, 10 * mm, f"Developed by {DEVELOPER_EN}  |  Contact: {CONTACT}")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def export_pdf(result, path: str, project_name: str = PROJECT_NAME_DEFAULT) -> str:
    k = result.kpis
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceBefore=10)
    warn = ParagraphStyle("W", parent=styles["Normal"], textColor=colors.red)

    doc = SimpleDocTemplate(path, pagesize=A4, title=SOFTWARE_NAME,
                            author=f"{DEVELOPER_EN} - {CONTACT}")
    story = []

    story.append(Paragraph(SOFTWARE_NAME, h1))
    story.append(Paragraph("Industrial Mineral Processing Simulation and Engineering Software",
                           styles["Heading2"]))
    story.append(Spacer(1, 6 * mm))
    cover = [["Software Version", VERSION],
             ["Model Versions", ", ".join(f"{a} {b}" for a, b in MODEL_VERSIONS.items())],
             ["Project Name", project_name],
             ["Simulation ID", result.simulation_id],
             ["Simulation Date", result.timestamp[:10]],
             ["Developer / Manufacturer", f"{DEVELOPER_EN} ({DEVELOPER_FA})"],
             ["Contact", CONTACT],
             ["Simulation Status", result.status]]
    t = Table(cover, colWidths=[60 * mm, 105 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#DCE6F1"))]))
    story.append(t)
    story.append(Paragraph(
        "MODEL RESULT — this report presents model results, not site-verified results; "
        "site calibration data is required before trusting recovery predictions (Section 113).",
        warn))

    story.append(PageBreak())
    story.append(Paragraph("1. Final Report", h2))
    rows = [["Metric", "Value", "Unit"]]
    for label, key, unit in [
            ("Feed Rate", "feed_t_h", "t/h"), ("Feed Fe Grade", None, "%"),
            ("Final Product Rate", "product_t_h", "t/h"),
            ("Final Product Grade", "product_fe_pct", "%"),
            ("Final Tail Rate", "tail_t_h", "t/h"), ("Final Tail Grade", "tail_fe_pct", "%"),
            ("Mass Recovery", "mass_recovery_pct", "%"), ("Fe Recovery", "fe_recovery_pct", "%"),
            ("Fe Input", "fe_in_t_h", "t/h"), ("Fe Product", "fe_product_t_h", "t/h"),
            ("Fe Tail", "fe_tail_t_h", "t/h"), ("Circulating Load", "circulating_load_t_h", "t/h"),
            ("Circulating Load", "circulating_load_pct", "%"),
            ("Screen Load", "screen_load_t_h", "t/h"), ("Crusher Load", "crusher_load_t_h", "t/h"),
            ("Daily Production", "production_t_day", "t/day"),
            ("Monthly Production", "production_t_month", "t/month"),
            ("Annual Production", "production_t_year", "t/year"),
            ("Mass Balance Error", "mass_balance_error_pct", "%"),
            ("Fe Balance Error", "fe_balance_error_pct", "%")]:
        if key is None:
            rows.append([label, str(result.config.feed_fe_pct), unit])
        else:
            v = k[key]
            rows.append([label, f"{v:,.3f}" if isinstance(v, (int, float)) else str(v), unit])
    rows.append(["Convergence Status", result.status, ""])
    t = Table(rows, colWidths=[70 * mm, 60 * mm, 30 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(t)

    story.append(Paragraph("2. Stream-by-Stream Results", h2))
    rows = [["Stream ID", "Dry t/h", "Wet t/h", "Fe %", "Fe t/h", "Status"]]
    for sid, s in result.streams.items():
        rows.append([sid, f"{s.dry_mass_flow_t_h:,.2f}", f"{s.wet_mass_flow_t_h:,.2f}",
                     f"{s.fe_grade_pct:.3f}", f"{s.fe_mass_flow_t_h:,.2f}", s.status])
    t = Table(rows, colWidths=[45 * mm, 28 * mm, 28 * mm, 25 * mm, 28 * mm, 26 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 7)]))
    story.append(t)

    story.append(Paragraph("3. Warnings & Assumptions", h2))
    for w in (result.warnings or ["No warnings."]):
        story.append(Paragraph(f"- {w}", styles["Normal"]))
    story.append(Paragraph(
        "Assumptions: separator capacity/power/pole geometry are CALIBRATION REQUIRED or "
        "UNKNOWN; screen and crusher models use Tier-5 engineering correlations pending "
        "testwork calibration; month=30 d, year=365 d for period conversions.", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"Developed by {DEVELOPER_EN} — Contact: {CONTACT}", styles["Heading2"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
