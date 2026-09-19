"""Shared CV layout: content decisions independent of any file format.

Both renderers (DOCX via python-docx, PDF via ReportLab) walk the SAME
Layout object, so the two formats can never drift apart:

    cv dict + template + profile
            │
        build_layout()          <- THIS module: what appears, in what order
            │
     ┌────┴────┐
   render_docx()   render_pdf()   <- presentation only

Layout answers CONTENT questions (is this field empty? which heading text
does this profile use? which parts join into the headline?); renderers
answer PRESENTATION questions (fonts, colors, spacing, page size).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from app.profiles import Profile, get_profile, section_heading
from app.templates import TemplateStyle, get_template

# A contact item: ("text", "Dhaka, Bangladesh", "") or ("link", "GitHub", "https://...")
ContactItem = Tuple[str, str, str]

DEFAULT_HEADINGS = {
    "summary": "Professional Summary",
    "skills": "Technical Skills",
    "experience": "Professional Experience",
    "projects": "Selected Projects",
    "education": "Education",
    "certifications": "Certifications / Additional Training",
    "languages": "Languages",
    "additional_info": "Additional Information",
}


@dataclass
class Block:
    """One renderable chunk inside a section.

    Kinds and the fields each one uses:
      para      - text                                     (summary, languages)
      skillline - label + text on one line                 (skills)
      job       - headline + optional meta + bullets       (experience)
      edu       - headline + optional meta + bullets       (education)
      project   - headline + tech + description + bullets  (projects)
      line      - single bullet-style line                 (certifications, additional)
    """

    kind: str
    text: str = ""
    label: str = ""
    headline: str = ""
    headline_tech: str = ""  # italic tech text after a project headline
    meta: str = ""  # italic line under job/edu headlines
    bullets: List[str] = field(default_factory=list)


@dataclass
class Section:
    key: str
    heading: str
    blocks: List[Block]


@dataclass
class Layout:
    """Everything a renderer needs to draw one CV."""

    name: str
    title: str
    contacts: List[ContactItem]
    sections: List[Section]
    # Resolved registries so renderers never re-resolve (or disagree):
    style: TemplateStyle
    profile: Profile


def _parts_join(parts: List[str], separator: str = "  |  ") -> str:
    """Join only the non-empty parts, separator BETWEEN items (never edges)."""
    return separator.join(p for p in parts if p and p.strip())


def _link_of(contact: Dict[str, Any], key: str, default_text: str = "") -> Tuple[str, str]:
    """Contact links may arrive as plain strings or {text,url} dicts."""
    v = (contact or {}).get(key, "")
    if isinstance(v, dict):
        t = v.get("text") or v.get("url") or default_text
        u = v.get("url") or ""
        return t, u
    v = (v or "").strip()
    if not v:
        return default_text, ""
    u = v if v.startswith("http") else "https://" + v
    return v, u


def _contact_items(cv: Dict[str, Any]) -> List[ContactItem]:
    """Contact line items in display order; empty fields are skipped here
    so no renderer ever sees a dangling separator."""
    c = cv.get("contact", {}) or {}
    items: List[ContactItem] = []
    for plain in ("location", "phone", "email"):
        value = str(c.get(plain, ""))
        if value.strip():
            items.append(("text", value, ""))
    for key in ("linkedin", "github", "portfolio"):
        text, url = _link_of(c, key)
        if text.strip():
            items.append(("link", text, url))
    return items


def _clean_list(values: Any) -> List[str]:
    if not values:
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _blocks_for(section_key: str, data: Any) -> List[Block]:
    """Content decisions per section kind — identical to what the DOCX
    generator has always done, now shared with the PDF renderer.
    Always returns a list (possibly empty)."""

    if section_key == "summary":
        text = str(data or "").strip()
        return [Block(kind="para", text=text)] if text else []

    if section_key == "skills":
        blocks = []
        for g in data or []:
            if not isinstance(g, dict):
                continue
            items = g.get("items", [])
            if isinstance(items, str):
                items = [x.strip() for x in items.split(",") if x.strip()]
            items = [str(i).strip() for i in items if str(i).strip()]
            if items:
                blocks.append(
                    Block(kind="skillline", label=str(g.get("category", "") or ""), text=", ".join(items))
                )
        return blocks

    if section_key in ("experience", "education"):
        blocks = []
        for entry in data or []:
            if section_key == "experience":
                headline = _parts_join([entry.get("title", ""), entry.get("company", "")])
                meta = _parts_join([entry.get("location", ""), entry.get("dates", "")])
                bullets = _clean_list(entry.get("bullets"))
            else:
                headline = _parts_join([entry.get("degree", ""), entry.get("school", "")])
                meta = _parts_join([entry.get("location", ""), entry.get("dates", "")])
                bullets = _clean_list(entry.get("details"))
            blocks.append(
                Block(kind="job" if section_key == "experience" else "edu", headline=headline, meta=meta, bullets=bullets)
            )
        return blocks

    if section_key == "projects":
        blocks = []
        for pr in data or []:
            tech = pr.get("technologies", "")
            if isinstance(tech, list):
                tech = ", ".join(str(t) for t in tech)
            blocks.append(
                Block(
                    kind="project",
                    headline=str(pr.get("name", "")),
                    headline_tech=str(tech or ""),
                    text=str(pr.get("description", "") or ""),
                    bullets=_clean_list(pr.get("details")),
                )
            )
        return blocks

    if section_key == "certifications":
        blocks = []
        for cert in data or []:
            if isinstance(cert, dict):
                parts = " - ".join(s for s in (cert.get("title", ""), cert.get("issuer", "")) if s)
                date = cert.get("date", "")
                line_text = f"{parts} ({date})" if parts and date else (parts or date)
            else:
                line_text = str(cert)
            if line_text and line_text.strip():
                blocks.append(Block(kind="line", text=line_text.strip()))
        return blocks

    if section_key == "languages":
        langs = ", ".join(str(lang).strip() for lang in data or [] if str(lang).strip())
        return [Block(kind="para", text=langs)] if langs else []

    if section_key == "additional_info":
        return [Block(kind="line", text=line) for line in _clean_list(data)]

    return []


def build_layout(
    cv: Dict[str, Any],
    template_key: str | None = None,
    profile_key: str | None = None,
) -> Layout:
    """CV dict + registries -> format-independent Layout."""
    style = get_template(template_key)
    profile = get_profile(profile_key)

    sections: List[Section] = []
    for section_key in profile.section_order:
        data = cv.get(section_key)
        if not data:
            continue
        blocks = [b for b in _blocks_for(section_key, data) if b.headline or b.text or b.bullets]
        if blocks:
            sections.append(
                Section(
                    key=section_key,
                    heading=section_heading(profile, section_key, DEFAULT_HEADINGS.get(section_key, section_key)),
                    blocks=blocks,
                )
            )

    return Layout(
        name=str(cv.get("name", "")) or "Your Name",
        title=str(cv.get("professional_title", "")),
        contacts=_contact_items(cv),
        sections=sections,
        style=style,
        profile=profile,
    )
