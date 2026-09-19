"""Tests for the ATS scoring engine, text extractor and /api/score-cv."""

from __future__ import annotations

import io

import pytest

from app.services.scorer import score_cv_text
from app.services.extractor import extract_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GOOD_CV_TEXT = """
Alex Example
Software Engineer
Dhaka, Bangladesh | +880 1000-000000 | alex@example.com | linkedin.com/in/alexexample

SUMMARY
Software engineer with 4 years of experience building web applications.
Delivered REST APIs and improved deployment pipelines with Docker.

EXPERIENCE
Software Engineer - Example Corp (Jan 2022 - Present)
• Led migration of legacy ERP modules, reducing load time by 30%
• Built REST APIs serving 200+ daily requests
• Managed a team of 3 developers and delivered 12 features
Junior Developer - Startup Co (2020 - 2021)
• Developed customer dashboard used by 500+ users
• Optimized SQL queries, achieving 3x faster reports

EDUCATION
B.Sc. in Computer Science - Example University (2016 - 2020)

SKILLS
Python, JavaScript, React, Django, PostgreSQL, Git, Docker, AWS

PROJECTS
CV Generator - built with Python and React

CERTIFICATIONS
AWS Cloud Practitioner (2023)
"""


# ---------------------------------------------------------------------------
# 1. Empty string -> score 0, grade F
# ---------------------------------------------------------------------------


def test_empty_text_scores_zero_and_f():
    result = score_cv_text("")
    assert result["score"] == 0
    assert result["grade"] == "F"
    assert result["fix_cta"] is True
    assert result["word_count"] == 0


# ---------------------------------------------------------------------------
# 2. email + phone + linkedin -> contact score 15
# ---------------------------------------------------------------------------


def test_full_contact_scores_15():
    text = "alex@example.com +880 1000-000000 linkedin.com/in/alex"
    result = score_cv_text(text)
    assert result["categories"]["contact"]["score"] == 15
    assert result["categories"]["contact"]["max"] == 15
    assert result["categories"]["contact"]["status"] == "good"


def test_missing_contact_scores_0_with_issues():
    result = score_cv_text("nothing here but words " * 20)
    assert result["categories"]["contact"]["score"] == 0
    titles = {i["title"] for i in result["issues"]}
    assert "Email address missing" in titles
    assert "Phone number missing" in titles
    assert "LinkedIn URL missing" in titles


# ---------------------------------------------------------------------------
# 3. Box chars -> format deduction
# ---------------------------------------------------------------------------


def test_box_characters_deduct_format_points():
    clean = score_cv_text(GOOD_CV_TEXT)
    boxed = score_cv_text("┌─────┐\n" + GOOD_CV_TEXT + "\n│ cell │\n╚═════╝")
    assert boxed["categories"]["format"]["score"] <= clean["categories"]["format"]["score"] - 10
    titles = {i["title"] for i in boxed["issues"]}
    assert "Complex formatting detected" in titles


def test_format_full_20_when_clean():
    result = score_cv_text(GOOD_CV_TEXT)
    assert result["categories"]["format"]["score"] == 20


# ---------------------------------------------------------------------------
# 4. Action verbs + tech keywords -> keywords > 15
# ---------------------------------------------------------------------------


def test_keywords_score_with_verbs_and_tech():
    text = (
        "Led, built and developed systems. Managed and created more. "
        "Designed and improved pipelines. python javascript react mysql api rest git docker"
    )
    result = score_cv_text(text)
    kw = result["categories"]["keywords"]
    # 5 (verbs) + 10 (3+ tech) = 15; soft skills/quantification may add more.
    assert kw["score"] >= 15


def test_no_keywords_flags_issue():
    text = "waffle waffle " * 50  # long, but keyword-free
    result = score_cv_text(text)
    titles = {i["title"] for i in result["issues"]}
    assert "No achievement language detected" in titles
    assert "No technical skills detected" in titles


# ---------------------------------------------------------------------------
# 5. 300-900 words -> length score 10
# ---------------------------------------------------------------------------


def test_ideal_length_scores_10():
    text = " ".join(["engineer"] * 400)
    assert score_cv_text(text)["categories"]["length"]["score"] == 10


def test_length_bands():
    assert score_cv_text(" ".join(["word"] * 1000))["categories"]["length"]["score"] == 8
    assert score_cv_text(" ".join(["word"] * 250))["categories"]["length"]["score"] == 5
    assert score_cv_text(" ".join(["word"] * 1500))["categories"]["length"]["score"] == 4
    assert score_cv_text(" ".join(["word"] * 100))["categories"]["length"]["score"] == 0


# ---------------------------------------------------------------------------
# 6. All 6 headings -> headings score 10
# ---------------------------------------------------------------------------


def test_all_headings_score_10():
    text = "experience education skills summary projects certifications"
    result = score_cv_text(text)
    assert result["categories"]["headings"]["score"] == 10


def test_objective_counts_as_summary():
    text = "experience education skills objective projects certifications"
    assert score_cv_text(text)["categories"]["headings"]["score"] == 10


def test_few_headings_flags_issue():
    text = "experience only this"
    result = score_cv_text(text)
    titles = {i["title"] for i in result["issues"]}
    assert "Missing standard sections" in titles


# ---------------------------------------------------------------------------
# 7. Full good CV text -> score >= 80, grade A or B
# ---------------------------------------------------------------------------


def test_good_cv_scores_at_least_80():
    result = score_cv_text(GOOD_CV_TEXT)
    assert result["score"] >= 80
    assert result["grade"] in ("A", "B")


# ---------------------------------------------------------------------------
# 8. issues ordered high -> medium -> low
# ---------------------------------------------------------------------------


def test_issues_ordered_by_severity():
    result = score_cv_text(GOOD_CV_TEXT)
    order = {"high": 0, "medium": 1, "low": 2}
    severities = [order[i["severity"]] for i in result["issues"]]
    assert severities == sorted(severities)


# ---------------------------------------------------------------------------
# 9. fix_cta True < 80, False >= 80
# ---------------------------------------------------------------------------


def test_fix_cta_threshold():
    good = score_cv_text(GOOD_CV_TEXT)
    bad = score_cv_text("")
    assert good["fix_cta"] == (good["score"] < 80)
    assert bad["fix_cta"] is True
    if good["score"] >= 80:
        assert good["fix_cta"] is False


def test_status_thresholds():
    result = score_cv_text(GOOD_CV_TEXT)
    for cat in result["categories"].values():
        pct = cat["score"] / cat["max"]
        if pct >= 0.75:
            assert cat["status"] == "good"
        elif pct >= 0.40:
            assert cat["status"] == "warning"
        else:
            assert cat["status"] == "poor"


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def test_extract_docx_generated_by_our_own_generator():
    from app.services.generator import generate_docx_bytes

    cv = {
        "name": "Alex Example",
        "professional_title": "Software Engineer",
        "contact": {"email": "alex@example.com", "phone": "+880 1000-000000"},
        "summary": "Engineer with experience building APIs and leading teams.",
        "skills": [{"category": "Languages", "items": ["Python", "SQL"]}],
        "experience": [
            {
                "title": "Engineer",
                "company": "Example Corp",
                "dates": "Jan 2022 - Present",
                "bullets": ["Built REST APIs serving 200+ users"],
            }
        ],
    }
    docx_bytes = generate_docx_bytes(cv)
    text = extract_text(docx_bytes, "alex_cv.docx")
    assert "Alex Example" in text
    assert "alex@example.com" in text
    assert "200+ users" in text


def test_extract_rejects_oversized_file():
    big = b"x" * (5_000_001)
    assert extract_text(big, "big.docx") == ""


def test_extract_unsupported_type_returns_empty():
    assert extract_text(b"hello", "notes.txt") == ""
    assert extract_text(b"hello", "") == ""


def test_extract_corrupt_docx_returns_empty():
    assert extract_text(b"not a real docx", "broken.docx") == ""


def test_extract_corrupt_pdf_returns_empty():
    assert extract_text(b"not a real pdf", "broken.pdf") == ""


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


def _docx_upload() -> bytes:
    from app.services.generator import generate_docx_bytes

    cv = {
        "name": "Alex Example",
        "professional_title": "Software Engineer",
        "contact": {"email": "alex@example.com", "phone": "+880 1000-000000",
                     "linkedin": "linkedin.com/in/alex"},
        "summary": "Engineer building APIs, led teams, improved results by 30%.",
        "skills": [{"category": "Languages", "items": ["Python", "SQL", "Git"]}],
        "experience": [
            {
                "title": "Engineer",
                "company": "Example Corp",
                "dates": "Jan 2022 - Present",
                "bullets": ["Built APIs", "Led team of 3", "Reduced costs 20%"],
            }
        ],
        "education": [{"degree": "B.Sc.", "school": "Example University",
                        "dates": "2016 - 2020"}],
    }
    return generate_docx_bytes(cv)


def test_score_cv_endpoint_scores_docx(client):
    response = client.post(
        "/api/score-cv",
        files={"file": ("cv.docx", io.BytesIO(_docx_upload()), "application/octet-stream")},
    )
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["grade"] in ("A", "B", "C", "D", "F")
    assert set(body["categories"]) == {
        "format", "contact", "keywords", "experience", "length", "headings",
    }
    assert isinstance(body["issues"], list)
    assert body["word_count"] > 0


def test_score_cv_rejects_unsupported_type(client):
    response = client.post(
        "/api/score-cv",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["error"]


def test_score_cv_rejects_empty_upload(client):
    response = client.post(
        "/api/score-cv",
        files={"file": ("cv.docx", io.BytesIO(b""), "application/octet-stream")},
    )
    assert response.status_code == 400


def test_score_cv_unreadable_file_is_500(client):
    response = client.post(
        "/api/score-cv",
        files={"file": ("cv.docx", io.BytesIO(b"garbage-not-docx"), "application/octet-stream")},
    )
    assert response.status_code == 500
    assert "corrupted" in response.json()["error"]


# ---------------------------------------------------------------------------
# Stats endpoint removed (Phase 1: no file-based runtime state)
# ---------------------------------------------------------------------------


def test_stats_endpoint_no_longer_exists(client):
    # The counter (and its filesystem-backed store) was removed deliberately;
    # the endpoint must be gone rather than silently returning stale data.
    assert client.get("/api/stats").status_code == 404
