"""CV template registry.

A template is pure style data: fonts, sizes, colors, spacing and margins.
The document STRUCTURE (sections, order, ATS single-column layout) is
identical for every template — only presentation changes. This keeps the
generator simple and guarantees every template stays ATS-friendly.

To add a new template: add one TemplateStyle entry to TEMPLATES.
API validation (schemas/cv.py) and GET /api/templates pick it up
automatically.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateStyle:
    """Presentation settings for one CV template."""

    key: str
    label: str
    description: str
    accent_hex: str  # headings, title, hyperlinks (hex without "#")
    font: str  # ATS-safe body font (Calibri / Arial)
    name_pt: float
    title_pt: float
    heading_pt: float
    body_pt: float
    contact_pt: float  # contact line, meta lines, hyperlink text
    entry_pt: float  # job / project / education headline
    margins_in: tuple[float, float, float, float]  # top, bottom, left, right
    heading_border: bool  # rule under section headings
    heading_space_before: int  # pt
    heading_space_after: int  # pt
    entry_space_before: int  # experience / projects headlines
    edu_space_before: int  # education headlines
    header_align: str  # "center" or "left"


TEMPLATES: dict[str, TemplateStyle] = {
    "classic": TemplateStyle(
        key="classic",
        label="Classic",
        description="The original balanced layout — navy accents, centered header.",
        accent_hex="1F3B63",
        font="Calibri",
        name_pt=22,
        title_pt=11,
        heading_pt=12,
        body_pt=10,
        contact_pt=9.5,
        entry_pt=10.5,
        margins_in=(0.6, 0.6, 0.65, 0.65),
        heading_border=True,
        heading_space_before=10,
        heading_space_after=4,
        entry_space_before=6,
        edu_space_before=4,
        header_align="center",
    ),
    "compact": TemplateStyle(
        key="compact",
        label="Compact",
        description="Tighter margins and type — fits the most content on one page.",
        accent_hex="333333",
        font="Arial",
        name_pt=17,
        title_pt=10.5,
        heading_pt=11,
        body_pt=9.5,
        contact_pt=9,
        entry_pt=10,
        margins_in=(0.5, 0.5, 0.55, 0.55),
        heading_border=True,
        heading_space_before=8,
        heading_space_after=3,
        entry_space_before=5,
        edu_space_before=3,
        header_align="center",
    ),
    "modern": TemplateStyle(
        key="modern",
        label="Modern",
        description="Left-aligned header with teal accents and open spacing.",
        accent_hex="0F766E",
        font="Calibri",
        name_pt=24,
        title_pt=11.5,
        heading_pt=12,
        body_pt=10,
        contact_pt=9.5,
        entry_pt=10.5,
        margins_in=(0.65, 0.65, 0.7, 0.7),
        heading_border=False,
        heading_space_before=12,
        heading_space_after=4,
        entry_space_before=6,
        edu_space_before=4,
        header_align="left",
    ),
}

DEFAULT_TEMPLATE = "classic"


def get_template(key: str | None) -> TemplateStyle:
    """Resolve a template key, falling back to the default."""
    if key and key in TEMPLATES:
        return TEMPLATES[key]
    return TEMPLATES[DEFAULT_TEMPLATE]
