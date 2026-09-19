"""Tests for profile support (Experienced vs Fresher structure)."""

from __future__ import annotations

import io
import zipfile

from app.profiles import DEFAULT_PROFILE, PROFILES, get_profile


def _docx_xml(raw: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _heading_positions(xml: str, heading: str) -> int:
    return xml.upper().find(heading.upper())


# ---- Registry sanity ----


def test_registry_has_unique_keys():
    keys = list(PROFILES)
    assert len(keys) == len(set(keys))
    assert DEFAULT_PROFILE in PROFILES


def test_get_profile_falls_back_to_default():
    assert get_profile(None) is PROFILES[DEFAULT_PROFILE]
    assert get_profile("nope") is PROFILES[DEFAULT_PROFILE]


# ---- Generator honors the profile ----


def test_default_output_matches_experienced(sample_cv):
    from app.services.generator import generate_docx_bytes

    assert generate_docx_bytes(sample_cv) == generate_docx_bytes(
        sample_cv, "classic", "experienced"
    )


def test_fresher_reorders_sections(sample_cv):
    """Education must come BEFORE experience in fresher output."""
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "classic", "fresher"))
    edu = _heading_positions(xml, ">EDUCATION<")
    exp = _heading_positions(xml, ">INTERNSHIPS / PART-TIME WORK<")
    assert edu != -1 and exp != -1
    assert edu < exp


def test_fresher_exactly_matches_profile_order(sample_cv):
    """Full order check: summary, education, projects, skills, experience."""
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "classic", "fresher"))
    positions = [
        _heading_positions(xml, ">CAREER OBJECTIVE<"),
        _heading_positions(xml, ">EDUCATION<"),
        _heading_positions(xml, ">SELECTED PROJECTS<"),
        _heading_positions(xml, ">TECHNICAL SKILLS<"),
        _heading_positions(xml, ">INTERNSHIPS / PART-TIME WORK<"),
    ]
    assert positions == sorted(positions)
    assert -1 not in positions


def test_fresher_uses_career_objective_heading(sample_cv):
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "classic", "fresher"))
    assert "CAREER OBJECTIVE" in xml.upper()
    assert "PROFESSIONAL SUMMARY" not in xml.upper()


def test_experienced_keeps_professional_summary(sample_cv):
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "classic", "experienced"))
    assert "PROFESSIONAL SUMMARY" in xml.upper()
    assert "CAREER OBJECTIVE" not in xml.upper()


def test_profiles_and_templates_combine_independently(sample_cv):
    """Template styling must survive a profile switch and vice versa."""
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "modern", "fresher"))
    assert "0F766E" in xml  # modern teal styling
    assert "CAREER OBJECTIVE" in xml.upper()  # fresher structure


def test_empty_sections_are_skipped_in_any_profile(sample_cv):
    """A fresher CV without experience must not render the section at all."""
    from app.services.generator import generate_docx_bytes

    cv = dict(sample_cv)
    cv["experience"] = []
    cv["projects"] = [dict(sample_cv["projects"][0])]
    xml = _docx_xml(generate_docx_bytes(cv, "classic", "fresher"))
    assert "INTERNSHIPS" not in xml.upper()  # no heading for missing data
    assert "SELECTED PROJECTS" in xml.upper()


# ---- API ----


def test_unknown_profile_is_422(client, sample_cv):
    cv = dict(sample_cv)
    cv["profile"] = "student"
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 422
    assert "unknown profile" in res.json()["detail"][0]["msg"]


def test_profile_passes_through_to_output(client, sample_cv):
    cv = dict(sample_cv)
    cv["profile"] = "fresher"
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 200
    xml = _docx_xml(res.content)
    assert "CAREER OBJECTIVE" in xml.upper()
    edu = _heading_positions(xml, ">EDUCATION<")
    exp = _heading_positions(xml, ">INTERNSHIPS / PART-TIME WORK<")
    assert edu < exp


def test_profile_defaults_keep_old_clients_working(client, sample_cv):
    """Payloads without a profile field must behave exactly as before."""
    res = client.post("/api/generate-cv", json=sample_cv)
    assert res.status_code == 200
    xml = _docx_xml(res.content)
    assert "PROFESSIONAL SUMMARY" in xml.upper()
