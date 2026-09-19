"""Tests for the PDF renderer (format=pdf).

Content parity with DOCX comes from the shared layout, so here we verify
PDF-specific behavior: valid file structure, text present, profile order,
template styling, and graceful handling of empty/minimal input.
"""

from __future__ import annotations

import base64
import re
import zlib

import pytest

from app.services.pdf import generate_pdf_bytes


def _pdf_text(data: bytes) -> str:
    """Extract readable text from the generated PDF's content streams.

    ReportLab compresses content streams with ASCII85 + Flate by default;
    we decode every stream and concatenate. Good enough for assertions.
    """
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.DOTALL):
        raw = match.group(1).strip()
        decoded = None
        for attempt in ("zlib", "a85+zlib", "raw"):
            try:
                if attempt == "zlib":
                    decoded = zlib.decompress(raw)
                elif attempt == "a85+zlib":
                    decoded = zlib.decompress(base64.a85decode(raw, adobe=True))
                else:
                    decoded = raw
                break
            except Exception:
                continue
        if decoded is not None:
            chunks.append(decoded.decode("latin-1", "ignore"))
    return "\n".join(chunks)


@pytest.fixture
def sample_cv() -> dict:
    return {
        "name": "Alex Example",
        "professional_title": "Software Engineer",
        "contact": {
            "location": "Dhaka",
            "phone": "+880 1000-000000",
            "email": "alex@example.com",
            "linkedin": "linkedin.com/in/alexexample",
            "github": "",
            "portfolio": "",
        },
        "summary": "Engineer with experience building web applications.",
        "skills": [{"category": "Languages", "items": ["Python", "JavaScript"]}],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Example Corp",
                "location": "Dhaka",
                "dates": "Jan 2024 - Present",
                "bullets": ["Built REST APIs.", "Led migration."],
            }
        ],
        "projects": [
            {
                "name": "CV Generator",
                "technologies": ["Python"],
                "description": "Generates CVs.",
                "details": ["Unicode safe."],
            }
        ],
        "education": [
            {"degree": "B.Sc. CS", "school": "Example U", "location": "Dhaka", "dates": "2019 - 2023", "details": ["CGPA 3.8"]}
        ],
        "certifications": [{"title": "AWS CP", "issuer": "Amazon", "date": "2024"}],
        "languages": ["English", "Bangla"],
        "additional_info": ["Open to relocation."],
    }


def test_pdf_is_valid_and_has_content(sample_cv):
    data = generate_pdf_bytes(sample_cv, "classic", "experienced")
    assert data.startswith(b"%PDF-")
    assert b"%%EOF" in data[-64:]
    text = _pdf_text(data)
    assert "Alex Example" in text
    assert "Software Engineer" in text
    assert "PROFESSIONAL SUMMARY" in text.upper()


def test_pdf_contains_all_sections_in_order(sample_cv):
    data = generate_pdf_bytes(sample_cv, "classic", "experienced")
    text = _pdf_text(data).upper()
    # NOTE: use rfind for LANGUAGES — the word also appears inside the
    # skills line ("Languages: Python, ...") before the real heading.
    positions = [
        text.find("PROFESSIONAL SUMMARY"),
        text.find("TECHNICAL SKILLS"),
        text.find("PROFESSIONAL EXPERIENCE"),
        text.find("SELECTED PROJECTS"),
        text.find("EDUCATION"),
        text.find("CERTIFICATIONS"),
        text.rfind("LANGUAGES"),
    ]
    assert all(p >= 0 for p in positions), text
    assert positions == sorted(positions)


def test_pdf_fresher_order_matches_docx(sample_cv):
    data = generate_pdf_bytes(sample_cv, "classic", "fresher")
    text = _pdf_text(data).upper()
    edu = text.find("EDUCATION")
    proj = text.find("SELECTED PROJECTS")
    skills = text.find("TECHNICAL SKILLS")
    exp = text.find("INTERNSHIPS / PART-TIME WORK")
    objective = text.find("CAREER OBJECTIVE")
    assert all(p >= 0 for p in (edu, proj, skills, exp, objective))
    assert objective < edu < proj < skills < exp


def test_pdf_template_accent_color(sample_cv):
    classic = generate_pdf_bytes(sample_cv, "classic", "experienced")
    modern = generate_pdf_bytes(sample_cv, "modern", "experienced")
    # Accent colors are emitted as "r g b rg" fill operators; ReportLab
    # prints components without leading zeros (e.g. ".121569").
    def color_pattern(hex6: str) -> str:
        comps = [int(hex6[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        return " ".join(f"{c:.6f}".lstrip("0") for c in comps) + " rg"
    assert color_pattern("1F3B63") in _pdf_text(classic)
    assert color_pattern("0F766E") in _pdf_text(modern)
    # And each template must NOT contain the other's accent.
    assert color_pattern("0F766E") not in _pdf_text(classic)
    assert color_pattern("1F3B63") not in _pdf_text(modern)


def test_pdf_minimal_cv_only_name():
    data = generate_pdf_bytes({"name": "Just A Name"}, "classic", "experienced")
    assert data.startswith(b"%PDF-")
    text = _pdf_text(data)
    assert "Just A Name" in text


def test_pdf_empty_contact_no_dangling_separator(sample_cv):
    sample_cv["contact"] = {"location": "", "phone": "", "email": "only@example.com", "linkedin": "", "github": "", "portfolio": ""}
    text = _pdf_text(generate_pdf_bytes(sample_cv, "classic", "experienced"))
    # The contact line contains the email with no leading/trailing separator.
    assert "only@example.com" in text
    assert "|  |" not in text
