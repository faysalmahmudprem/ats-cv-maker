"""CV file import: parse an uploaded DOCX or PDF into structured CV data.

This powers "Import CV — upload your existing file and keep editing here".
Parsing happens entirely in memory; nothing is written to disk or stored.

Strategy
--------
Parsing a CV is heuristic work. We are honest about it:

1. Extract lines (python-docx paragraphs + bullet text; PyMuPDF text
   blocks per line, top-to-bottom then left-to-right).
2. Detect sections via a heading vocabulary (SUMMARY / EXPERIENCE /
   EDUCATION / SKILLS / PROJECTS / ... and common synonyms like "Work
   History" or "Career Objective").
3. Split section content into entries: a new entry starts at a bold
   line (DOCX) or a larger font line (PDF); otherwise every 2-3rd
   structural gap. Date-like lines attach as the entry's meta.
4. Map bullets ("•", "-", "*" prefixed lines) to the current entry.

The result feeds the same CVRequest validation as the manual form, so
anything malformed is simply dropped — import never fabricates content.
Fields we cannot reliably recover (email/phone on wrapped lines, skills
in two-column PDFs) are left empty rather than guessed.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from docx import Document as DocxDocument

try:  # PyMuPDF
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore


# DOCX mime we generate ourselves; be liberal in what we accept.
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SUPPORTED_EXTENSIONS = {".docx": "docx", ".pdf": "pdf"}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w%-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+", re.IGNORECASE)
URL_RE = re.compile(r"(?:https?://)?(?:www\.)?[\w-]+\.[a-z]{2,}(?:/[\w./%-]*)?", re.IGNORECASE)

DATE_RE = re.compile(
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|\d{4})"
    r"\s*(?:-|–|—|to|until)\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|\d{4}|Present|Current|Now|Date)",
    re.IGNORECASE,
)
YEAR_RANGE_RE = re.compile(r"\b(19|20)\d{2}\s*(?:-|–|—|to)\s*((19|20)\d{2}|Present)", re.IGNORECASE)

# Bullet markers at the start of an extracted line.
BULLET_PREFIX_RE = re.compile(r"^\s*(?:[•‣▪◦*\-–—·]|\(?\d+[.)])\s+")

# Section heading vocabulary: canonical key -> regex of synonyms.
SECTION_PATTERNS: Dict[str, re.Pattern] = {
    "summary": re.compile(
        r"^(career\s+)?(professional\s+|personal\s+)?(summary|objective|profile|about\s*me)\b:?\.?$|"
        r"^career\s+objective\b:?$",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^(work\s+|professional\s+|relevant\s+|employment\s+)?(experience|history|employment)\b|"
        r"^internships?\b.*|.*\bpart[-\s]?time\s+work\b",
        re.IGNORECASE,
    ),
    "education": re.compile(r"^(education|academic(s)?(\s+background)?|qualifications)\b", re.IGNORECASE),
    "skills": re.compile(r"^(technical\s+|key\s+|core\s+|professional\s+)?(skills|competencies|technologies)\b", re.IGNORECASE),
    "projects": re.compile(r"^(selected\s+|key\s+|academic\s+)?(projects|portfolio)\b", re.IGNORECASE),
    "certifications": re.compile(r"^(certifications?|licenses?|courses?|training|additional\s+training)\b", re.IGNORECASE),
    "languages": re.compile(r"^(languages?)\b", re.IGNORECASE),
    "additional_info": re.compile(r"^(additional\s+information|extras?|interests|hobbies|activities|volunteer\w*)\b", re.IGNORECASE),
}

# Headings that look like headings but are just short caps lines we ignore.
_NOISE_HEADINGS = re.compile(r"^(curriculum\s+vitae|resume|cv|references.{0,20})$", re.IGNORECASE)


@dataclass
class ParsedLine:
    text: str
    bold: bool = False
    font_size: float = 0.0
    is_bullet: bool = False


@dataclass
class ParsedSection:
    key: str
    lines: List[ParsedLine] = field(default_factory=list)


@dataclass
class ImportResult:
    """Raw parsed content + quality signals before CVData mapping."""

    name: str = ""
    professional_title: str = ""
    contact: Dict[str, str] = field(default_factory=dict)
    sections: Dict[str, List[ParsedLine]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    # Quality heuristics surfaced to the user (and used by the ATS
    # checker later — the same signals, so both stay consistent).
    word_count: int = 0
    has_email: bool = False
    has_phone: bool = False
    bullet_count: int = 0
    heading_keys_found: List[str] = field(default_factory=list)
    page_count: int = 1


# ---------------------------------------------------------------------------
# Line extraction
# ---------------------------------------------------------------------------


def _docx_lines(data: bytes) -> List[ParsedLine]:
    doc = DocxDocument(io.BytesIO(data))
    lines: List[ParsedLine] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name or "").lower()
        is_bullet = "list" in style_name or bool(BULLET_PREFIX_RE.match(text))
        bold = False
        size = 0.0
        for run in para.runs:
            if run.bold:
                bold = True
            if run.font.size:
                size = max(size, run.font.size.pt)
        if style_name.startswith("heading"):
            bold = True
            size = max(size, 14.0)
        lines.append(ParsedLine(text=text, bold=bold, font_size=size, is_bullet=is_bullet))
    return lines


def _pdf_lines(data: bytes) -> List[ParsedLine]:
    if fitz is None:  # pragma: no cover
        raise RuntimeError("PyMuPDF is not installed")
    lines: List[ParsedLine] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            # Blocks preserve rough reading order; sort within a block
            # top-to-bottom, left-to-right.
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
                spans = []  # font size per line comes from "dict" extract below
                _ = spans
                for raw_line in text.splitlines():
                    t = raw_line.strip()
                    if not t:
                        continue
                    lines.append(ParsedLine(text=t, is_bullet=bool(BULLET_PREFIX_RE.match(t))))
    return lines


def _pdf_lines_sized(data: bytes) -> List[ParsedLine]:
    """PDF extraction with font sizes (for entry splitting)."""
    if fitz is None:  # pragma: no cover
        raise RuntimeError("PyMuPDF is not installed")
    lines: List[ParsedLine] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            d = page.get_text("dict")
            for block in d.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for para in block.get("lines", []):
                    text_parts = []
                    max_size = 0.0
                    bold = False
                    for span in para.get("spans", []):
                        text_parts.append(span.get("text", ""))
                        max_size = max(max_size, float(span.get("size", 0)))
                        flags = int(span.get("flags", 0))
                        bold = bold or bool(flags & 2**4)  # bold bit
                    t = "".join(text_parts).strip()
                    if not t:
                        continue
                    lines.append(
                        ParsedLine(
                            text=t,
                            bold=bold,
                            font_size=round(max_size, 1),
                            is_bullet=bool(BULLET_PREFIX_RE.match(t)),
                        )
                    )
    return lines


# ---------------------------------------------------------------------------
# Structure detection
# ---------------------------------------------------------------------------


def _match_heading(text: str) -> Optional[str]:
    """Return the canonical section key if `text` is a heading line.

    A heading is a SHORT standalone line: no inner "label: content"
    colon (that's a skills line like "Languages: Python, JS"), and at
    most 4 words. This stops content lines that merely START with a
    heading word from splitting sections.
    """
    clean = text.strip().strip(":.•").strip()
    if len(clean) > 48 or _NOISE_HEADINGS.match(clean):
        return None
    if re.search(r":\s*\S", clean):  # "Languages: Python, ..." is content
        return None
    if len(clean.split()) > 4:
        return None
    for key, pattern in SECTION_PATTERNS.items():
        if pattern.match(clean):
            return key
    return None


def _split_sections(lines: List[ParsedLine], doc_kind: str) -> Dict[str, List[ParsedLine]]:
    sections: Dict[str, List[ParsedLine]] = {}
    current: Optional[str] = None
    # Pre-header region (name, title, contact) ends at the first heading.
    header: List[ParsedLine] = []

    for line in lines:
        key = _match_heading(line.text)
        if key:
            current = key
            sections.setdefault(current, [])
            continue
        if current is None:
            header.append(line)
        else:
            sections[current].append(line)

    # If NOTHING matched (headings in unusual wording), treat the whole
    # document as one unparsed blob under "experience" — downstream
    # mapping will still pull contact info from anywhere.
    if not sections:
        sections["experience"] = header + [l for ls in sections.values() for l in ls]
    return sections


def _looks_like_date_meta(text: str) -> bool:
    return bool(DATE_RE.search(text) or YEAR_RANGE_RE.search(text)) and len(text) <= 80


def _split_entries(
    section_lines: List[ParsedLine], doc_kind: str
) -> List[List[ParsedLine]]:
    """Group section lines into entries.

    Strong signals: bold lines and larger-font lines (DOCX style runs,
    PDF font sizes) start a new entry. Weak fallback: a date-bearing line
    after 2+ content lines also starts one.
    """
    sizes = [l.font_size for l in section_lines if l.font_size]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 0.0

    entries: List[List[ParsedLine]] = []
    current: List[ParsedLine] = []
    content_since_start = 0

    for line in section_lines:
        starts_entry = False
        if line.is_bullet:
            starts_entry = False
        elif line.bold or (doc_kind == "pdf" and body_size and line.font_size >= body_size + 0.9):
            starts_entry = content_since_start > 0
        elif _looks_like_date_meta(line.text) and content_since_start >= 2:
            starts_entry = True

        if starts_entry and current:
            entries.append(current)
            current = []
            content_since_start = 0

        current.append(line)
        if not line.is_bullet:
            content_since_start += 1

    if current:
        entries.append(current)
    return entries


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------


def _extract_header(lines: List[ParsedLine], result: ImportResult) -> None:
    """Name, title and contact details from the pre-header region
    (plus a global sweep for emails/links anywhere in the document)."""
    all_text = [l.text for l in lines]

    # Contacts: sweep everywhere (they are often on one wrapped line).
    joined = "\n".join(all_text)
    emails = EMAIL_RE.findall(joined)
    phones = [p.strip() for p in PHONE_RE.findall(joined)]
    linkedin = LINKEDIN_RE.search(joined)
    github = GITHUB_RE.search(joined)

    # Exclude email-like matches that are part of URLs already captured.
    result.contact["email"] = emails[0] if emails else ""
    result.contact["phone"] = phones[0] if phones else ""
    result.contact["linkedin"] = linkedin.group(0) if linkedin else ""
    result.contact["github"] = github.group(0) if github else ""

    # Portfolio: first URL that is not linkedin/github.
    for u in URL_RE.finditer(joined):
        url = u.group(0)
        if "linkedin." in url or "github." in url:
            continue
        result.contact["portfolio"] = url
        break

    result.has_email = bool(result.contact["email"])
    result.has_phone = bool(result.contact["phone"])

    # Name: first header line that is not an email/url/phone and is
    # title-ish (2-5 words, mostly letters). The pre-header region is
    # everything before the first detected section heading.
    header: List[ParsedLine] = []
    for line in lines:
        if _match_heading(line.text):
            break
        header.append(line)

    location = ""
    for line in header[:6]:
        t = line.text
        if EMAIL_RE.search(t) or URL_RE.search(t) or PHONE_RE.search(t):
            continue
        words = t.split()
        if 1 < len(words) <= 5 and sum(c.isalpha() for c in t) / max(len(t.replace(" ", "")), 1) > 0.6:
            if not result.name:
                result.name = t
                continue
            if not result.professional_title and len(words) <= 6 and not _looks_like_date_meta(t):
                result.professional_title = t
                continue
            # Second short line might be a location.
            if "," in t and len(t) <= 60 and not location:
                location = t
                continue
    if location:
        result.contact["location"] = location


def _lines_to_text(section_lines: List[ParsedLine]) -> str:
    texts = [BULLET_PREFIX_RE.sub("", l.text).strip() for l in section_lines]
    return "\n".join(t for t in texts if t)


def _map_summary(lines: List[ParsedLine]) -> str:
    return "\n".join(BULLET_PREFIX_RE.sub("", l.text).strip() for l in lines if not l.is_bullet).strip()


def _map_skills(lines: List[ParsedLine]) -> List[Dict[str, Any]]:
    """Skills: prefer 'Category: a, b, c' lines; fall back to one group."""
    groups: List[Dict[str, Any]] = []
    current_category = ""
    for line in lines:
        text = BULLET_PREFIX_RE.sub("", line.text).strip()
        if not text:
            continue
        m = re.match(r"^([\w /&+-]{2,40}):\s*(.+)$", text)
        if m and not EMAIL_RE.search(text):
            current_category = m.group(1).strip()
            items = [i.strip() for i in m.group(2).split(",") if i.strip()]
            if items:
                groups.append({"category": current_category, "items": items})
        else:
            items = [i.strip() for i in text.split(",") if i.strip()]
            if len(items) > 1:
                groups.append({"category": current_category, "items": items})
            elif items and groups:
                groups[-1]["items"].extend(items)
            elif items:
                groups.append({"category": "", "items": items})
    return groups


def _map_entries(
    section_lines: List[ParsedLine],
    doc_kind: str,
    kind: str,
) -> List[Dict[str, Any]]:
    """Map experience/education/projects entries from grouped lines."""
    out: List[Dict[str, Any]] = []
    for entry_lines in _split_entries(section_lines, doc_kind):
        if not entry_lines:
            continue
        headline_line = entry_lines[0]
        headline = BULLET_PREFIX_RE.sub("", headline_line.text).strip()
        meta = ""
        bullets: List[str] = []
        description_parts: List[str] = []

        for line in entry_lines[1:]:
            clean = BULLET_PREFIX_RE.sub("", line.text).strip()
            if not clean:
                continue
            if line.is_bullet:
                bullets.append(clean)
            elif _looks_like_date_meta(line.text) and not meta:
                meta = clean
            else:
                description_parts.append(clean)

        entry: Dict[str, Any]
        if kind == "experience":
            parts = [p.strip() for p in re.split(r"\s*\|\s*|\s+[–—-]\s+", headline) if p.strip()]
            title = parts[0] if parts else headline
            company = parts[1] if len(parts) > 1 else ""
            # Meta may be "Location  |  Dates" (our own DOCX format) or a
            # bare date range; split it when both parts are present.
            dates = meta
            location = ""
            meta_parts = [p.strip() for p in re.split(r"\s*\|\s*", meta) if p.strip()]
            if len(meta_parts) == 2 and _looks_like_date_meta(meta_parts[1]) and not _looks_like_date_meta(meta_parts[0]):
                location, dates = meta_parts[0], meta_parts[1]
            if not dates:
                dm = DATE_RE.search(headline) or YEAR_RANGE_RE.search(headline)
                dates = dm.group(0) if dm else ""
            entry = {
                "title": title[:80],
                "company": company[:80],
                "location": location[:80],
                "dates": dates[:60],
                "bullets": bullets[:15] or [p for p in description_parts[:1]],
            }
        elif kind == "education":
            parts = [p.strip() for p in re.split(r"\s*\|\s*|\s+[–—-]\s+", headline) if p.strip()]
            degree = parts[0] if parts else headline
            school = parts[1] if len(parts) > 1 else ""
            dates = meta
            entry = {
                "degree": degree[:100],
                "school": school[:100],
                "location": "",
                "dates": dates[:60],
                "details": bullets[:10],
            }
        else:  # projects
            # "CV Generator  |  Python, React" -> name + technologies.
            pipe_parts = [p.strip() for p in headline.split("|") if p.strip()]
            name = pipe_parts[0] if pipe_parts else headline
            technologies = [t.strip() for seg in pipe_parts[1:] for t in seg.split(",") if t.strip()]
            entry = {
                "name": name[:80],
                "technologies": technologies[:20],
                "description": " ".join(description_parts)[:600],
                "details": bullets[:10],
            }
        # Keep only entries with some substance.
        if any(str(v).strip() for v in entry.values() if not isinstance(v, list)) or entry.get(
            "bullets"
        ) or entry.get("details"):
            out.append(entry)
    return out


def _map_certifications(lines: List[ParsedLine]) -> List[Dict[str, str]]:
    certs = []
    for line in lines:
        text = BULLET_PREFIX_RE.sub("", line.text).strip()
        if not text or len(text) < 3:
            continue
        date = ""
        dm = re.search(r"((?:19|20)\d{2})", text)
        if dm:
            date = dm.group(1)
            text = text.replace(dm.group(0), "").strip(" -(),")
        parts = [p.strip() for p in text.split(" - ") if p.strip()]
        title = parts[0] if parts else text
        issuer = parts[1] if len(parts) > 1 else ""
        certs.append({"title": title[:120], "issuer": issuer[:80], "date": date[:40]})
    return certs


def _map_languages(lines: List[ParsedLine]) -> List[str]:
    langs: List[str] = []
    for line in lines:
        text = BULLET_PREFIX_RE.sub("", line.text).strip()
        if not text:
            continue
        # "English — fluent" -> English ; "English, Bangla" -> both
        text = re.split(r"[—–-]\s*", text)[0]
        for part in text.split(","):
            p = part.strip().strip("·")
            if p and len(p) <= 30:
                langs.append(p)
    return langs[:10]


def _map_additional(lines: List[ParsedLine]) -> List[str]:
    out = []
    for line in lines:
        text = BULLET_PREFIX_RE.sub("", line.text).strip()
        if text and len(text) <= 300:
            out.append(text)
    return out[:10]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_cv_file(
    data: bytes,
    doc_kind: str,
    filename: str = "",
) -> Dict[str, Any]:
    """Parse an uploaded CV file into a CVData-shaped dict + warnings.

    Returns: {"cv": {...}, "warnings": [...], "meta": {...}}
    Raises ValueError for unsupported/corrupt files.
    """
    if doc_kind == "pdf":
        if fitz is None:
            raise ValueError("PDF support is not available on the server.")
        try:
            lines = _pdf_lines_sized(data)
        except Exception as exc:
            raise ValueError("Could not read this PDF. Is it a valid file?") from exc
        if not lines:
            raise ValueError(
                "No text found in this PDF — it may be a scan or contain only images. "
                "Try a text-based PDF or the DOCX version."
            )
        page_count = _pdf_page_count(data)
    elif doc_kind == "docx":
        try:
            lines = _docx_lines(data)
        except Exception as exc:
            raise ValueError("Could not read this DOCX file. Is it a valid Word document?") from exc
        if not lines:
            raise ValueError("This DOCX file appears to be empty.")
        page_count = 1
    else:
        raise ValueError("Unsupported file type. Upload a .docx or .pdf file.")

    result = ImportResult()
    result.page_count = page_count
    result.word_count = sum(len(l.text.split()) for l in lines)
    result.bullet_count = sum(1 for l in lines if l.is_bullet)

    _split_sections_into_result(lines, result)
    _extract_header(lines, result)

    cv: Dict[str, Any] = {
        "name": result.name[:80],
        "professional_title": result.professional_title[:80],
        "contact": {
            "location": result.contact.get("location", "")[:80],
            "phone": result.contact.get("phone", "")[:40],
            "email": result.contact.get("email", "")[:120],
            "linkedin": result.contact.get("linkedin", "")[:300],
            "github": result.contact.get("github", "")[:300],
            "portfolio": result.contact.get("portfolio", "")[:300],
        },
        "summary": _map_summary(result.sections.get("summary", []))[:1200],
        "skills": _map_skills(result.sections.get("skills", []))[:25],
        "experience": _map_entries(result.sections.get("experience", []), doc_kind, "experience")[:15],
        "projects": _map_entries(result.sections.get("projects", []), doc_kind, "projects")[:10],
        "education": _map_entries(result.sections.get("education", []), doc_kind, "education")[:10],
        "certifications": _map_certifications(result.sections.get("certifications", []))[:15],
        "languages": _map_languages(result.sections.get("languages", [])),
        "additional_info": _map_additional(result.sections.get("additional_info", [])),
    }

    # Warnings the UI shows next to the imported preview.
    warnings: List[str] = list(result.warnings)
    if not cv["name"]:
        warnings.append("Couldn't confidently detect your name — please check it.")
    if not cv["contact"]["email"]:
        warnings.append("No email found — add it in Personal information.")
    if not cv["experience"] and not cv["projects"]:
        warnings.append("No experience or project entries detected — you may need to add them manually.")
    if result.bullet_count == 0 and result.word_count > 80:
        warnings.append("No bullet points found — achievements may be buried in paragraphs.")

    return {
        "cv": cv,
        "warnings": warnings,
        "meta": {
            "kind": doc_kind,
            "filename": filename,
            "pages": page_count,
            "words": result.word_count,
            "sections_found": result.heading_keys_found,
        },
    }


def _split_sections_into_result(lines: List[ParsedLine], result: ImportResult) -> None:
    sections = _split_sections(lines, "")
    result.sections = sections
    result.heading_keys_found = list(sections.keys())


def _pdf_page_count(data: bytes) -> int:
    if fitz is None:
        return 1
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            return max(1, doc.page_count)
    except Exception:
        return 1
