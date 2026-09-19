"""PDF renderer for the shared CV layout (ReportLab).

Presentation-only, like the DOCX renderer: it draws the SAME Layout
object produced by app/services/layout.py, honoring the same
TemplateStyle (font, sizes, accent color, margins, header alignment)
and Profile (section order + headings). Same content, different canvas.

Notes:
- SimpleDocTemplate handles page breaks automatically.
- Hyperlinks use ReportLab's <a href="..."> markup inside paragraphs.
- Fonts: ReportLab's built-in Helvetica family (an ATS-safe classic).
  Unicode coverage beyond Latin is handled by escaping; Bangla shaping
  is not supported by core PDF fonts (a documented limitation — the
  DOCX export remains the fully Unicode-safe option).
"""

from __future__ import annotations

import io
import xml.sax.saxutils as saxutils
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.services.layout import Block, Layout, build_layout
from app.templates import TemplateStyle


# Map template fonts to ReportLab's built-in families.
_FONT_FAMILIES = {
    "Calibri": "Helvetica",
    "Arial": "Helvetica",
    "Helvetica": "Helvetica",
}
_DEFAULT_FAMILY = "Helvetica"


def _escape(text: str) -> str:
    """Escape XML specials for Paragraph markup (&, <, >)."""
    return saxutils.escape(str(text))


def _link_markup(text: str, url: str, color_hex: str) -> str:
    """Clickable, colored, underlined link for use inside a Paragraph."""
    safe_url = saxutils.escape(url, {'"': "&quot;"})
    return f'<a href="{safe_url}" color="{color_hex}"><u>{_escape(text)}</u></a>'


class _PdfStyles:
    """Paragraph styles derived from the template's TemplateStyle."""

    def __init__(self, style: TemplateStyle) -> None:
        family = _FONT_FAMILIES.get(style.font, _DEFAULT_FAMILY)
        accent = colors.HexColor("#" + style.accent_hex)
        self.accent_hex = "#" + style.accent_hex
        self.family = family
        align = TA_CENTER if style.header_align == "center" else TA_LEFT
        self.name = ParagraphStyle(
            "cvName", fontName=family + "-Bold", fontSize=style.name_pt, leading=style.name_pt + 3, alignment=align, textColor=colors.HexColor("#16202e"), spaceAfter=1
        )
        self.title = ParagraphStyle(
            "cvTitle", fontName=family, fontSize=style.title_pt, leading=style.title_pt + 3, alignment=align, textColor=accent, spaceAfter=4
        )
        self.contact = ParagraphStyle(
            "cvContact", fontName=family, fontSize=style.contact_pt, leading=style.contact_pt + 3, alignment=align, textColor=colors.HexColor("#3a4757"), spaceAfter=2
        )
        self.heading = ParagraphStyle(
            "cvHeading", fontName=family + "-Bold", fontSize=style.heading_pt, leading=style.heading_pt + 3, alignment=TA_LEFT, textColor=accent, spaceBefore=style.heading_space_before, spaceAfter=style.heading_space_after - 1
        )
        self.body = ParagraphStyle("cvBody", fontName=family, fontSize=style.body_pt, leading=style.body_pt + 3, alignment=TA_LEFT, textColor=colors.HexColor("#16202e"))
        self.body_bold = ParagraphStyle("cvBodyB", parent=self.body, fontName=family + "-Bold")
        self.meta = ParagraphStyle("cvMeta", parent=self.body, fontName=family + "-Oblique", fontSize=style.contact_pt, textColor=colors.HexColor("#3a4757"))


def _bullet_flowables(block: Block, styles: _PdfStyles) -> List[Paragraph]:
    """Bullets drawn as indented paragraphs with a bullet character."""
    out = []
    for b in block.bullets:
        out.append(
            Paragraph(
                f'<bullet>&bull;</bullet>{_escape(b)}',
                ParagraphStyle(
                    "cvBullet",
                    parent=styles.body,
                    leftIndent=14,
                    bulletIndent=4,
                    spaceAfter=1.5,
                ),
            )
        )
    return out


def _heading_rule(styles: _PdfStyles, style: TemplateStyle) -> Optional[HRFlowable]:
    """Bottom border under headings for templates that use one (classic)."""
    if not style.heading_border:
        return None
    return HRFlowable(
        width="100%",
        thickness=0.75,
        color=colors.HexColor("#" + style.accent_hex),
        spaceBefore=0,
        spaceAfter=2,
    )


def build_pdf(
    cv: Dict[str, Any],
    template_key: str | None = None,
    profile_key: str | None = None,
) -> io.BytesIO:
    """Main entry: CV dict + template + profile -> BytesIO pdf."""
    layout = build_layout(cv, template_key, profile_key)
    style = layout.style
    styles = _PdfStyles(style)

    top, bottom, left, right = style.margins_in
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=left * 72,
        rightMargin=right * 72,
        topMargin=top * 72,
        bottomMargin=bottom * 72,
        title=f"{layout.name} - CV",
        author=layout.name,
        subject=layout.title,
    )

    story: List[Any] = []

    # ---- Header ----
    story.append(Paragraph(_escape(layout.name), styles.name))
    if layout.title:
        story.append(Paragraph(_escape(layout.title), styles.title))
    # Contact line: items separated by "  |  ", links clickable.
    parts: List[str] = []
    for kind, text, url in layout.contacts:
        if kind == "link":
            parts.append(_link_markup(text, url, styles.accent_hex))
        else:
            parts.append(_escape(text))
    if parts:
        story.append(Paragraph("  |  ".join(parts), styles.contact))
    story.append(Spacer(1, 6))

    # ---- Body sections in PROFILE order (from the shared layout) ----
    for i, section in enumerate(layout.sections):
        story.append(Paragraph(_escape(section.heading.upper()), styles.heading))
        rule = _heading_rule(styles, style)
        if rule:
            story.append(rule)
        for block in section.blocks:
            flow = _section_block_flowables(block, styles)
            story.extend(flow)
        if i < len(layout.sections) - 1:
            story.append(Spacer(1, 4))

    doc.build(story)
    buf.seek(0)
    return buf


def _section_block_flowables(block: Block, styles: _PdfStyles) -> List[Any]:
    """Turn one layout Block into ReportLab flowables."""
    out: List[Any] = []
    if block.kind == "para":
        out.append(Paragraph(_escape(block.text), styles.body))
    elif block.kind == "skillline":
        label = f"<b>{_escape(block.label)}:</b> " if block.label else ""
        out.append(Paragraph(label + _escape(block.text), styles.body))
    elif block.kind == "line":
        out.extend(_bullet_flowables(block, styles))
    elif block.kind in ("job", "edu"):
        head = [Paragraph(f"<b>{_escape(block.headline)}</b>", styles.body)]
        if block.meta:
            head.append(Paragraph(_escape(block.meta), styles.meta))
        head.extend(_bullet_flowables(block, styles))
        out.append(KeepTogether(head))
    elif block.kind == "project":
        tech = (
            f' <font size="{styles.body.fontSize - 1}" color="#3a4757"><i>| {_escape(block.headline_tech)}</i></font>'
            if block.headline_tech
            else ""
        )
        head = [Paragraph(f"<b>{_escape(block.headline)}</b>{tech}", styles.body)]
        if block.text:
            head.append(Paragraph(_escape(block.text), styles.body))
        head.extend(_bullet_flowables(block, styles))
        out.append(KeepTogether(head))
    out.append(Spacer(1, 2))
    return out


def generate_pdf_bytes(
    cv: Dict[str, Any],
    template_key: str | None = None,
    profile_key: str | None = None,
) -> bytes:
    """CV dict + template + profile -> raw PDF bytes."""
    return build_pdf(cv, template_key, profile_key).getvalue()
