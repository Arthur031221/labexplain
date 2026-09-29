"""CSV and PDF export of a report."""

from __future__ import annotations

import csv
import io
from xml.sax.saxutils import escape as xml_escape

from labexplain import BANNER
from labexplain.models import ReportResult

CSV_FIELDS = ["test", "value", "unit", "status", "low", "high", "source_lab", "source_url"]


def _csv_safe(text: str) -> str:
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def to_csv(result: ReportResult) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"# {BANNER}"])
    writer.writerow(CSV_FIELDS)
    for m in result.rows:
        writer.writerow(
            [_csv_safe(m.display_name), m.value, m.unit, m.status, m.low, m.high, m.source_lab, m.source_url]
        )
    return buf.getvalue()


_STATUS_COLORS = {
    "high": (0.80, 0.15, 0.15),
    "low": (0.85, 0.55, 0.0),
    "normal": (0.10, 0.45, 0.15),
    "unmatched": (0.4, 0.4, 0.4),
}


def to_pdf(result: ReportResult, out_path: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    styles = getSampleStyleSheet()
    banner_style = styles["Normal"].clone("banner")
    banner_style.textColor = colors.red
    banner_style.fontName = "Helvetica-Bold"

    doc = SimpleDocTemplate(out_path, pagesize=letter, title="labexplain report")
    story = [
        Paragraph("labexplain report", styles["Title"]),
        Paragraph(BANNER, banner_style),
        Spacer(1, 0.2 * inch),
    ]

    data = [["Test", "Value", "Unit", "Range", "Status"]]
    for m in result.rows:
        range_text = "" if m.low is None and m.high is None else f"{m.low}-{m.high}"
        data.append(
            [
                m.display_name,
                "" if m.value is None else str(m.value),
                m.unit or "",
                range_text,
                m.status,
            ]
        )
    table = Table(data, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
    ]
    for i, m in enumerate(result.rows, start=1):
        rgb = _STATUS_COLORS.get(m.status)
        if rgb and m.status not in ("normal", "unmatched"):
            style_cmds.append(("TEXTCOLOR", (4, i), (4, i), colors.Color(*rgb)))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    flagged = result.flagged()
    if flagged:
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph("Notes on flagged values", styles["Heading2"]))
        for m in flagged:
            if not m.explanation:
                continue
            name = xml_escape(m.display_name)
            note = xml_escape(m.explanation)
            story.append(Paragraph(f"<b>{name}</b>: {note}", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
