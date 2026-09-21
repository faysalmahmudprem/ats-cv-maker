"""Tests for CV file import (POST /api/import-cv).

The strongest test here is the round-trip: generate a DOCX from known
data with our own generator, import it back, and assert the fields
survived. PDF follows the same idea via our PDF renderer.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.services.generator import generate_docx_bytes
from app.services.import_cv import parse_cv_file
from app.services.pdf import generate_pdf_bytes

SAMPLE_CV = {
    "name": "Alex Example",
    "professional_title": "Software Engineer",
    "contact": {
        "location": "Dhaka, Bangladesh",
        "phone": "+880 1000-000000",
        "email": "alex@example.com",
        "linkedin": "linkedin.com/in/alexexample",
        "github": "github.com/alexexample",
        "portfolio": "",
    },
    "summary": "Engineer building web applications and business software.",
    "skills": [
        {"category": "Languages", "items": ["Python", "JavaScript"]},
        {"category": "Frameworks", "items": ["FastAPI", "React"]},
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Example Corp",
            "location": "Dhaka",
            "dates": "Jan 2024 - Present",
            "bullets": ["Built REST APIs serving 10k daily requests.", "Led migration of legacy ERP modules."],
        },
        {
            "title": "Junior Developer",
            "company": "Startup Co",
            "location": "",
            "dates": "2022 - 2023",
            "bullets": ["Fixed bugs across the stack."],
        },
    ],
    "projects": [
        {"name": "CV Generator", "technologies": ["Python"], "description": "Generates ATS CVs.", "details": ["Unicode support."]}
    ],
    "education": [
        {"degree": "B.Sc. in Computer Science", "school": "Example University", "location": "Dhaka", "dates": "2019 - 2023", "details": ["CGPA 3.80"]}
    ],
    "certifications": [{"title": "AWS Cloud Practitioner", "issuer": "Amazon", "date": "2024"}],
    "languages": ["English", "Bangla"],
    "additional_info": ["Open to relocation."],
}


# ---------------------------------------------------------------------------
# Service-level round-trips
# ---------------------------------------------------------------------------


def test_docx_roundtrip_preserves_fields():
    docx = generate_docx_bytes(SAMPLE_CV, "classic", "experienced")
    result = parse_cv_file(docx, "docx", "x.docx")
    cv = result["cv"]

    assert cv["name"] == "Alex Example"
    assert cv["professional_title"] == "Software Engineer"
    assert cv["contact"]["email"] == "alex@example.com"
    assert cv["contact"]["phone"] == "+880 1000-000000"
    assert "linkedin.com/in/alexexample" in cv["contact"]["linkedin"]
    assert "Engineer building web applications" in cv["summary"]
    assert cv["skills"][0]["category"] == "Languages"
    assert "Python" in cv["skills"][0]["items"]
    assert len(cv["experience"]) == 2
    first = cv["experience"][0]
    assert first["title"] == "Software Engineer"
    assert first["company"] == "Example Corp"
    assert first["dates"] == "Jan 2024 - Present"
    assert len(first["bullets"]) == 2
    assert cv["education"][0]["degree"] == "B.Sc. in Computer Science"
    assert cv["projects"][0]["name"] == "CV Generator"
    assert "Python" in cv["projects"][0]["technologies"]
    assert cv["certifications"][0]["title"] == "AWS Cloud Practitioner"
    assert "English" in cv["languages"]
    assert not result["warnings"]


def test_pdf_roundtrip_recovers_core_fields():
    pdf = generate_pdf_bytes(SAMPLE_CV, "classic", "experienced")
    result = parse_cv_file(pdf, "pdf", "x.pdf")
    cv = result["cv"]

    assert cv["name"] == "Alex Example"
    assert cv["contact"]["email"] == "alex@example.com"
    assert len(cv["experience"]) == 2
    assert cv["experience"][0]["title"] == "Software Engineer"
    assert len(cv["education"]) >= 1
    assert result["meta"]["pages"] >= 1


def test_scanned_pdf_gets_honest_error():
    # A PDF with no text (image-only/scan) is the classic failure case:
    # a page with nothing extractable behaves identically to a scan.
    # Built with pypdf (BSD-3-Clause) so the suite runs without PyMuPDF.
    from pypdf import PdfWriter

    buf = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)  # empty page: no text layer
    writer.write(buf)
    data = buf.getvalue()
    with pytest.raises(ValueError) as exc:
        parse_cv_file(data, "pdf", "scan.pdf")
    assert "No text" in str(exc.value)


def test_corrupt_docx_raises_valueerror():
    with pytest.raises(ValueError):
        parse_cv_file(b"not a real docx", "docx", "bad.docx")


# ---------------------------------------------------------------------------
# API contract
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_api_import_roundtrip(client):
    docx = generate_docx_bytes(SAMPLE_CV, "classic", "experienced")
    res = client.post(
        "/api/import-cv",
        files={"file": ("me.docx", io.BytesIO(docx), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cv"]["name"] == "Alex Example"
    assert body["cv"]["experience"][0]["company"] == "Example Corp"
    assert isinstance(body["warnings"], list)
    assert body["meta"]["kind"] == "docx"


def test_api_rejects_unsupported_type(client):
    res = client.post(
        "/api/import-cv",
        files={"file": ("photo.png", io.BytesIO(b"\x89PNG fake"), "image/png")},
    )
    assert res.status_code == 415


def test_api_rejects_empty_file(client):
    res = client.post(
        "/api/import-cv",
        files={"file": ("empty.docx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 422


def test_api_rejects_corrupt_docx(client):
    res = client.post(
        "/api/import-cv",
        files={"file": ("bad.docx", io.BytesIO(b"garbage bytes"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 422
    assert "Could not read" in res.json()["error"]


def test_api_import_response_has_no_template_fields(client):
    docx = generate_docx_bytes(SAMPLE_CV, "classic", "experienced")
    res = client.post(
        "/api/import-cv",
        files={"file": ("me.docx", io.BytesIO(docx), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    cv = res.json()["cv"]
    assert "template" not in cv
    assert "profile" not in cv
    assert "format" not in cv


def test_api_import_rejects_decompression_bomb(client):
    """A DOCX that expands hugely is rejected before the parser runs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"\x00" * (10 * 1024 * 1024))

    res = client.post(
        "/api/import-cv",
        files={"file": ("bomb.docx", io.BytesIO(buf.getvalue()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert res.status_code == 413


# ---------------------------------------------------------------------------
# pypdf-based PDF fixture tests (no PyMuPDF anywhere in this suite)
# ---------------------------------------------------------------------------


def _canvas_pdf(lines_per_page) -> bytes:
    """Build a text PDF with reportlab canvas (BSD-licensed prod dep).

    `lines_per_page`: list of pages, each a list of text lines.
    """
    from reportlab.pdfgen.canvas import Canvas

    buf = io.BytesIO()
    c = Canvas(buf)
    for page in lines_per_page:
        y = 800
        for line in page:
            c.drawString(50, y, line)
            y -= 15
        c.showPage()
    c.save()
    return buf.getvalue()


SIMPLE_CV_PAGES = [
    [
        "Alex Example",
        "Software Engineer",
        "alex@example.com | +1 555-0100",
        "EXPERIENCE",
        "Software Engineer | Example Corp",
        "Jan 2020 - Present",
        "- Built public APIs.",
        "* Cut latency 40%.",
        "EDUCATION",
        "B.Sc. CS | Example U",
        "2015 - 2019",
        "SKILLS",
        "Languages: Python, Go",
        "PROJECTS",
        "Demo App | Python",
        "A demo app.",
        "- Shipped v1.",
    ]
]


def test_pdf_simple_text_sections():
    result = parse_cv_file(_canvas_pdf(SIMPLE_CV_PAGES), "pdf", "simple.pdf")
    cv = result["cv"]
    assert cv["name"] == "Alex Example"
    assert cv["contact"]["email"] == "alex@example.com"
    assert "experience" in result["meta"]["sections_found"]
    assert "education" in result["meta"]["sections_found"]
    assert "skills" in result["meta"]["sections_found"]
    assert "projects" in result["meta"]["sections_found"]
    assert result["meta"]["pages"] == 1


def test_pdf_contact_extraction():
    result = parse_cv_file(_canvas_pdf(SIMPLE_CV_PAGES), "pdf", "c.pdf")
    contact = result["cv"]["contact"]
    assert contact["email"] == "alex@example.com"
    assert contact["phone"] == "+1 555-0100"


def test_pdf_experience_entries_and_bullets():
    result = parse_cv_file(_canvas_pdf(SIMPLE_CV_PAGES), "pdf", "e.pdf")
    exp = result["cv"]["experience"]
    assert len(exp) == 1
    assert exp[0]["title"] == "Software Engineer"
    assert exp[0]["company"] == "Example Corp"
    assert exp[0]["dates"] == "Jan 2020 - Present"
    assert len(exp[0]["bullets"]) == 2


def test_pdf_education_skills_projects():
    result = parse_cv_file(_canvas_pdf(SIMPLE_CV_PAGES), "pdf", "s.pdf")
    cv = result["cv"]
    assert cv["education"][0]["degree"] == "B.Sc. CS"
    assert cv["education"][0]["school"] == "Example U"
    assert cv["skills"][0]["category"] == "Languages"
    assert "Python" in cv["skills"][0]["items"]
    assert cv["projects"][0]["name"] == "Demo App"
    assert "Python" in cv["projects"][0]["technologies"]


def test_pdf_multi_page_merges_and_counts():
    data = _canvas_pdf(
        [
            ["Alex Example", "EXPERIENCE", "Software Engineer | Example Corp", "Jan 2020 - Present"],
            ["- Built APIs on page two.", "EDUCATION", "B.Sc. CS | Example U", "2015 - 2019"],
        ]
    )
    result = parse_cv_file(data, "pdf", "multi.pdf")
    assert result["meta"]["pages"] == 2
    assert result["cv"]["experience"][0]["bullets"] == ["Built APIs on page two."]
    assert result["cv"]["education"][0]["degree"] == "B.Sc. CS"


def test_pdf_unicode_text():
    data = _canvas_pdf([["Jose Garcia", "Software Engineer", "SKILLS", "Languages: Python"]])
    result = parse_cv_file(data, "pdf", "u.pdf")
    assert result["cv"]["name"] == "Jose Garcia"


def test_pdf_unicode_accents():
    # Latin-1 accents survive Helvetica/WinAnsi encoding end to end.
    data = _canvas_pdf([["Renée Müller", "Software Engineer", "SKILLS", "Languages: Python"]])
    result = parse_cv_file(data, "pdf", "acc.pdf")
    assert result["cv"]["name"] == "Renée Müller"


def test_pdf_malformed_raises_valueerror():
    with pytest.raises(ValueError) as exc:
        parse_cv_file(b"%PDF-1.4 not really a pdf \x00\x01\x02", "pdf", "bad.pdf")
    assert "Could not read" in str(exc.value)


def test_pdf_empty_bytes_raise_valueerror():
    with pytest.raises(ValueError):
        parse_cv_file(b"", "pdf", "empty.pdf")


def test_api_pdf_import_roundtrip(client):
    data = _canvas_pdf(SIMPLE_CV_PAGES)
    res = client.post(
        "/api/import-cv",
        files={"file": ("cv.pdf", io.BytesIO(data), "application/pdf")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cv"]["name"] == "Alex Example"
    assert body["meta"]["kind"] == "pdf"
    assert body["meta"]["pages"] == 1


def test_api_pdf_rejects_malformed(client):
    res = client.post(
        "/api/import-cv",
        files={"file": ("bad.pdf", io.BytesIO(b"garbage bytes"), "application/pdf")},
    )
    assert res.status_code == 422
