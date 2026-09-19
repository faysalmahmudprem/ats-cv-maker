"""End-to-end tests for the ATS score endpoint (POST /api/score-cv).

The strongest test round-trips a real file through the whole pipeline:
our own generator produces DOCX/PDF bytes, the endpoint extracts text
and scores it, and the response carries the full score contract. Error
paths (unsupported type, empty file, unreadable bytes) are covered too,
so the endpoint is proven reachable and well-behaved end to end.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.generator import generate_docx_bytes
from app.services.pdf import generate_pdf_bytes

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

CATEGORY_KEYS = {"format", "contact", "keywords", "experience", "length", "headings"}

# Complete, valid CV — fictional data, no real personal information.
SAMPLE_CV = {
    "name": "Alex Example",
    "professional_title": "Software Engineer",
    "contact": {
        "location": "Dhaka, Bangladesh",
        "phone": "+880 1000-000000",
        "email": "alex@example.com",
        "linkedin": "linkedin.com/in/alexexample",
        "github": "github.com/alexexample",
        "portfolio": "alexexample.dev",
    },
    "summary": (
        "Software engineer with experience building web applications and "
        "business software, focused on clean APIs and measurable results."
    ),
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
            "bullets": [
                "Built REST APIs serving 10k daily requests, cutting latency 30%.",
                "Led migration of legacy ERP modules for 200+ users.",
                "Reduced report generation time by 40% with caching.",
            ],
        },
        {
            "title": "Junior Developer",
            "company": "Startup Co",
            "location": "",
            "dates": "2022 - 2023",
            "bullets": [
                "Developed internal tools in Python and SQL.",
                "Improved deploy pipeline reliability with Docker and Git.",
            ],
        },
    ],
    "projects": [
        {
            "name": "CV Generator",
            "technologies": ["Python", "python-docx"],
            "description": "Generates ATS-friendly Word CVs from JSON.",
            "details": ["Supports Unicode text and hyperlinks."],
        }
    ],
    "education": [
        {
            "degree": "B.Sc. in Computer Science",
            "school": "Example University",
            "location": "Dhaka",
            "dates": "2019 - 2023",
            "details": ["CGPA 3.80/4.00"],
        }
    ],
    "certifications": [{"title": "AWS Cloud Practitioner", "issuer": "Amazon", "date": "2024"}],
    "languages": ["English", "Bangla"],
    "additional_info": ["Open to relocation."],
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _upload(client: TestClient, filename: str, data: bytes, mime: str):
    return client.post("/api/score-cv", files={"file": (filename, io.BytesIO(data), mime)})


def _assert_full_score_contract(body: dict) -> None:
    """Every successful response must satisfy scorer.score_cv_text's shape."""
    assert isinstance(body["score"], int)
    assert 0 <= body["score"] <= 100
    assert body["grade"] in {"A", "B", "C", "D", "F"}
    assert isinstance(body["summary"], str) and body["summary"]
    assert set(body["categories"]) == CATEGORY_KEYS
    for category in body["categories"].values():
        assert isinstance(category["score"], int)
        assert category["max"] > 0
        assert category["status"] in {"good", "warning", "poor"}
    for issue in body["issues"]:
        assert issue["severity"] in {"high", "medium", "low"}
        assert issue["title"] and issue["detail"] and issue["fix"]
    assert isinstance(body["word_count"], int) and body["word_count"] > 0
    assert isinstance(body["fix_cta"], bool)


# ---- Happy paths ---------------------------------------------------------


def test_score_docx_roundtrip(client):
    docx = generate_docx_bytes(SAMPLE_CV, "classic", "experienced")
    res = _upload(client, "me.docx", docx, DOCX_MIME)

    assert res.status_code == 200
    _assert_full_score_contract(res.json())


def test_score_pdf_roundtrip(client):
    pdf = generate_pdf_bytes(SAMPLE_CV, "classic", "experienced")
    res = _upload(client, "me.pdf", pdf, PDF_MIME)

    assert res.status_code == 200
    _assert_full_score_contract(res.json())


def test_complete_cv_earns_full_contact_score(client):
    """The sample has email + phone + LinkedIn, so contact must be maxed."""
    docx = generate_docx_bytes(SAMPLE_CV, "classic", "experienced")
    body = _upload(client, "me.docx", docx, DOCX_MIME).json()

    contact = body["categories"]["contact"]
    assert contact["score"] == contact["max"]
    assert body["score"] > 0


def test_content_type_fallback_when_filename_has_no_extension(client):
    """Clients with odd filenames still work via the Content-Type fallback."""
    pdf = generate_pdf_bytes(SAMPLE_CV, "classic", "experienced")
    res = _upload(client, "upload", pdf, PDF_MIME)

    assert res.status_code == 200
    _assert_full_score_contract(res.json())


# ---- Error paths ---------------------------------------------------------


def test_unsupported_type_is_400(client):
    res = _upload(client, "photo.png", b"\x89PNG fake", "image/png")

    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["error"]


def test_empty_file_is_400(client):
    res = _upload(client, "empty.docx", b"", DOCX_MIME)

    assert res.status_code == 400
    assert "No file uploaded" in res.json()["error"]


def test_unreadable_bytes_are_500_not_a_crash(client):
    """A corrupt file that extracts no text is an honest 500, not a 200."""
    res = _upload(client, "bad.docx", b"garbage bytes", DOCX_MIME)

    assert res.status_code == 500
    assert "Could not read the file" in res.json()["error"]


def test_missing_file_field_is_422(client):
    """The endpoint is registered and validates its required upload field."""
    res = client.post("/api/score-cv")

    assert res.status_code == 422


def test_score_rejects_decompression_bomb(client):
    """A crafted DOCX that expands hugely is rejected before parsing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"\x00" * (10 * 1024 * 1024))

    res = _upload(client, "bomb.docx", buf.getvalue(), DOCX_MIME)

    assert res.status_code == 413


def test_score_does_not_log_upload_filename(client, caplog):
    """Upload filenames can contain a person's name and must not be logged."""
    import logging

    with caplog.at_level(logging.WARNING, logger="cv_generator"):
        _upload(client, "Jane_Doe_CV.docx", b"garbage bytes", DOCX_MIME)

    assert "Jane_Doe_CV" not in caplog.text
