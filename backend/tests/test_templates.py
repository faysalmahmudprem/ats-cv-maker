"""Tests for multi-template support (registry + API + generator)."""

from __future__ import annotations

import io
import zipfile

from app.templates import DEFAULT_TEMPLATE, TEMPLATES, get_template


def _docx_xml(raw: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _docx_xml_with_rels(raw: bytes) -> tuple[str, str]:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return (
            zf.read("word/document.xml").decode("utf-8"),
            zf.read("word/_rels/document.xml.rels").decode("utf-8"),
        )


# ---- Registry sanity ----


def test_registry_has_unique_keys_and_labels():
    keys = list(TEMPLATES)
    assert len(keys) == len(set(keys))
    labels = [t.label for t in TEMPLATES.values()]
    assert len(labels) == len(set(labels))
    for t in TEMPLATES.values():
        assert 0.5 <= t.body_pt <= 12
        assert len(t.accent_hex) == 6
        assert t.header_align in ("center", "left")


def test_default_template_exists():
    assert DEFAULT_TEMPLATE in TEMPLATES
    assert get_template(None) is TEMPLATES[DEFAULT_TEMPLATE]
    assert get_template("nope") is TEMPLATES[DEFAULT_TEMPLATE]


# ---- Generator honors the template ----


def test_default_output_matches_classic(sample_cv):
    """No template key -> identical to requesting classic explicitly."""
    from app.services.generator import generate_docx_bytes

    assert generate_docx_bytes(sample_cv) == generate_docx_bytes(sample_cv, "classic")


def test_modern_uses_teal_and_left_header(sample_cv):
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "modern"))
    assert "0F766E" in xml  # teal accent
    assert "1F3B63" not in xml  # classic navy gone
    assert 'w:val="left"' in xml  # left-aligned header


def test_compact_uses_smaller_body_font(sample_cv):
    from app.services.generator import generate_docx_bytes

    xml = _docx_xml(generate_docx_bytes(sample_cv, "compact"))
    assert 'w:val="19"' in xml  # 9.5pt body
    assert "Arial" in xml


def test_hyperlink_accent_matches_template(sample_cv):
    from app.services.generator import generate_docx_bytes

    xml, rels = _docx_xml_with_rels(generate_docx_bytes(sample_cv, "modern"))
    assert "linkedin.com/in/alexexample" in rels  # link still works
    assert "0F766E" in xml  # link color follows template


# ---- API ----


def test_templates_endpoint_lists_all(client):
    res = client.get("/api/templates")
    assert res.status_code == 200
    data = res.json()
    keys = {t["key"] for t in data["templates"]}
    assert keys == set(TEMPLATES)
    for t in data["templates"]:
        assert set(t) == {"key", "label", "description", "accent_hex"}
        assert t["accent_hex"].startswith("#")


def test_unknown_template_is_422(client, sample_cv):
    cv = dict(sample_cv)
    cv["template"] = "fancy"
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 422
    assert "unknown template" in res.json()["detail"][0]["msg"]


def test_template_passes_through_to_output(client, sample_cv):
    cv = dict(sample_cv)
    cv["template"] = "modern"
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 200
    xml = _docx_xml(res.content)
    assert "0F766E" in xml
    assert "Alex Example" in xml
