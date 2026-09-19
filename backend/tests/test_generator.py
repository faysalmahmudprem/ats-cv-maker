"""Unit tests for the DOCX generator service."""

from __future__ import annotations

import io
import zipfile

from app.services.generator import build_cv, generate_docx_bytes


def _docx_xml(raw: bytes) -> str:
    """Extract the main document.xml text from DOCX bytes for assertions."""
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _is_valid_zip(raw: bytes) -> bool:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.testzip() is None


def test_build_cv_returns_nonempty_bytes(sample_cv):
    raw = generate_docx_bytes(sample_cv)
    assert isinstance(raw, bytes)
    assert len(raw) > 1000


def test_build_cv_is_valid_zip(sample_cv):
    raw = generate_docx_bytes(sample_cv)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert zf.testzip() is None


def test_minimal_cv_only_name():
    raw = generate_docx_bytes({"name": "Minimal Person"})
    xml = _docx_xml(raw)
    assert "Minimal Person" in xml


def test_name_title_and_summary_present(sample_cv):
    xml = _docx_xml(generate_docx_bytes(sample_cv))
    assert "Alex Example" in xml
    assert "Software Engineer" in xml
    assert "PROFESSIONAL SUMMARY" in xml.upper()


def test_all_section_headings_present(sample_cv):
    xml = _docx_xml(generate_docx_bytes(sample_cv))
    for h in (
        "TECHNICAL SKILLS",
        "PROFESSIONAL EXPERIENCE",
        "SELECTED PROJECTS",
        "EDUCATION",
        "CERTIFICATIONS",
        "LANGUAGES",
        "ADDITIONAL INFORMATION",
    ):
        assert h in xml, f"missing heading: {h}"


def test_unicode_and_bangla_text(sample_cv):
    cv = dict(sample_cv)
    cv["summary"] = "परिचय পরীক্ষা — naïve café résumé ✓"
    xml = _docx_xml(generate_docx_bytes(cv))
    assert "परिचय পরীক্ষা" in xml
    assert "naïve café résumé ✓" in xml


def test_special_characters_do_not_crash(sample_cv):
    cv = dict(sample_cv)
    cv["name"] = 'O"Brien <&> \\ /'
    # Must not raise, and must produce a valid DOCX. lxml escapes < and &
    # in text nodes; double quotes stay literal there (still valid XML).
    raw = generate_docx_bytes(cv)
    assert _is_valid_zip(raw)
    xml = _docx_xml(raw)
    assert "O&quot;Brien" in xml or "O\"Brien" in xml


def test_skills_comma_string_items(sample_cv):
    """Items arriving as "PHP, React" still render as a list."""
    cv = dict(sample_cv)
    cv["skills"] = [{"category": "Skills", "items": "PHP, React, MySQL"}]
    xml = _docx_xml(generate_docx_bytes(cv))
    assert "PHP, React, MySQL" in xml


def test_hyperlink_present_for_linkedin(sample_cv):
    raw = generate_docx_bytes(sample_cv)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        rels = zf.read("word/_rels/document.xml.rels").decode("utf-8")
    assert "linkedin.com/in/alexexample" in rels


def test_generate_bytes_matches_build_cv(sample_cv):
    assert generate_docx_bytes(sample_cv) == build_cv(sample_cv).getvalue()


# ---- Regression tests: separator and empty-line bugs ----


def test_contact_line_has_no_dangling_separators(sample_cv):
    """With no links, the contact line must be exactly "a  |  b  |  c"."""
    cv = dict(sample_cv)
    cv["contact"] = {
        "location": "Dhaka, Bangladesh",
        "phone": "+880 1000-000000",
        "email": "alex@example.com",
        "linkedin": "",
        "github": "",
        "portfolio": "",
    }
    xml = _docx_xml(generate_docx_bytes(cv))
    # Old bug produced "email  |    |    |  " (adjacent/trailing pipes).
    assert "alex@example.com  |  " not in xml
    assert "  |    |  " not in xml
    # The email is the last contact item on the line.
    assert ">alex@example.com</w:t>" in xml


def test_experience_meta_line_skips_empty_fields(sample_cv):
    """Dates-only meta must not render a leading pipe."""
    cv = dict(sample_cv)
    cv["experience"] = [
        {"title": "Developer", "company": "", "location": "", "dates": "2024", "bullets": ["Worked."]}
    ]
    xml = _docx_xml(generate_docx_bytes(cv))
    assert ">  |  2024" not in xml
    assert ">Developer</w:t>" in xml
    assert ">2024</w:t>" in xml


def test_certification_without_issuer_renders_cleanly(sample_cv):
    cv = dict(sample_cv)
    cv["certifications"] = [{"title": "AWS Cloud Practitioner", "issuer": "", "date": "2024"}]
    xml = _docx_xml(generate_docx_bytes(cv))
    assert "AWS Cloud Practitioner (2024)" in xml
    assert "AWS Cloud Practitioner - " not in xml


def test_empty_title_produces_no_title_line():
    """A CV without professional_title must not emit an empty paragraph run."""
    raw = generate_docx_bytes({"name": "No Title Person"})
    xml = _docx_xml(raw)
    assert "No Title Person" in xml
