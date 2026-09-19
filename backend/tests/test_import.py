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
    import fitz

    buf = io.BytesIO()
    doc = fitz.open()
    doc.new_page()  # empty page: no text layer
    doc.save(buf)
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
