"""PDF CV generator, intentionally independent from Streamlit."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape


def _text(value: Any) -> str:
    return str(value or "").strip()


def _items(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "body": ParagraphStyle("CVBody", parent=base, fontName="Helvetica", fontSize=9.5,
                               leading=11.2, textColor=colors.black, spaceAfter=1.2),
        "name": ParagraphStyle("CVName", parent=base, fontName="Helvetica-Bold", fontSize=16,
                               leading=18, alignment=TA_CENTER, spaceAfter=2),
        "contact": ParagraphStyle("CVContact", parent=base, fontName="Helvetica", fontSize=9.5,
                                  leading=11, alignment=TA_CENTER, spaceAfter=0),
        "link": ParagraphStyle("CVLink", parent=base, fontName="Helvetica", fontSize=9.5,
                               leading=11, alignment=TA_CENTER, textColor=colors.blue, spaceAfter=2),
        "section": ParagraphStyle("CVSection", parent=base, fontName="Helvetica-Bold", fontSize=10,
                                  leading=11, alignment=TA_LEFT, spaceBefore=4, spaceAfter=1),
        "left_bold": ParagraphStyle("CVLeftBold", parent=base, fontName="Helvetica-Bold", fontSize=9.5,
                                    leading=11, alignment=TA_LEFT),
        "right_bold": ParagraphStyle("CVRightBold", parent=base, fontName="Helvetica-Bold", fontSize=9.5,
                                     leading=11, alignment=TA_RIGHT),
        "italic": ParagraphStyle("CVItalic", parent=base, fontName="Helvetica-BoldOblique", fontSize=9.5,
                                 leading=11, leftIndent=8),
        "bullet": ParagraphStyle("CVBullet", parent=base, fontName="Helvetica", fontSize=9.2,
                                 leading=10.8, leftIndent=13, firstLineIndent=-7, bulletIndent=3, spaceAfter=1),
    }


def _section(story: list[Any], title: str, styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph(escape(title.upper()), styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.7, color=colors.black, spaceBefore=0, spaceAfter=2))


def _header_row(name: str, dates: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[Paragraph(escape(name), styles["left_bold"]),
                    Paragraph(escape(dates), styles["right_bold"])]], colWidths=[5.2 * inch, 2.1 * inch])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return table


def _bullets(values: Iterable[Any], styles: dict[str, ParagraphStyle]) -> list[Paragraph]:
    return [Paragraph(escape(_text(value)), styles["bullet"], bulletText="•")
            for value in values if _text(value)]


def _experiences(story: list[Any], title: str, entries: Any, styles: dict[str, ParagraphStyle]) -> None:
    valid = [entry for entry in _items(entries) if _text(entry.get("organisation"))]
    if not valid:
        return
    _section(story, title, styles)
    for entry in valid:
        organisation = ", ".join(filter(None, [_text(entry.get("organisation")), _text(entry.get("location"))]))
        block: list[Any] = [Paragraph(escape(organisation), styles["italic"]),
                            _header_row(_text(entry.get("role")), _text(entry.get("dates")), styles)]
        bullets = entry.get("bullets", [])
        block.extend(_bullets(bullets if isinstance(bullets, list) else [], styles))
        block.append(Spacer(1, 1.5))
        story.append(KeepTogether(block))


def build_pdf(data: dict[str, Any]) -> BytesIO:
    """Build a compact, professional CV and return a seeked PDF buffer."""
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, leftMargin=0.575 * inch, rightMargin=0.575 * inch,
                                 topMargin=0.42 * inch, bottomMargin=0.35 * inch,
                                 title=f"{_text(data.get('full_name'))} CV")
    styles = _styles()
    story: list[Any] = [Paragraph(escape(_text(data.get("full_name")) or "CURRICULUM VITAE"), styles["name"])]
    contact = " | ".join(filter(None, [_text(data.get("phone")), _text(data.get("email"))]))
    if contact:
        story.append(Paragraph(escape(contact), styles["contact"]))
    linkedin = _text(data.get("linkedin"))
    if linkedin:
        story.append(Paragraph(f"<u>{escape(linkedin)}</u>", styles["link"]))

    education = [entry for entry in _items(data.get("education")) if _text(entry.get("school"))]
    if education:
        _section(story, "Education", styles)
        for entry in education:
            school = ", ".join(filter(None, [_text(entry.get("school")), _text(entry.get("location"))]))
            block: list[Any] = [_header_row(school, _text(entry.get("dates")), styles)]
            if _text(entry.get("degree")):
                block.append(Paragraph(escape(_text(entry.get("degree"))), styles["italic"]))
            if _text(entry.get("detail")):
                block.append(Paragraph(escape(_text(entry.get("detail"))), styles["italic"]))
            story.append(KeepTogether(block))

    _experiences(story, "Work Experience", data.get("work_experience"), styles)
    _experiences(story, "Leadership & Volunteer Experience", data.get("leadership_experience"), styles)
    certifications = [_text(value) for value in data.get("certifications", []) if _text(value)] if isinstance(data.get("certifications"), list) else []
    if certifications:
        _section(story, "Certifications & Courses", styles)
        story.extend(_bullets(certifications, styles))
    technical, strengths = _text(data.get("technical_skills")), _text(data.get("strengths"))
    if technical or strengths:
        _section(story, "Skills & Interests", styles)
        if technical:
            story.append(Paragraph(f"<b>Technical:</b> {escape(technical)}", styles["bullet"], bulletText="•"))
        if strengths:
            story.append(Paragraph(f"<b>Strengths:</b> {escape(strengths)}", styles["bullet"], bulletText="•"))

    document.build(story)
    output.seek(0)
    return output

