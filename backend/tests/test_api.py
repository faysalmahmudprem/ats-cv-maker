"""API tests: request validation, download response, error handling."""

from __future__ import annotations

import re
import zipfile
import io

import pytest


def _is_docx(raw: bytes) -> bool:
    return raw[:2] == b"PK" and zipfile.ZipFile(io.BytesIO(raw)).testzip() is None


# ---- Health ----


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---- Generate: happy paths ----


def test_generate_returns_docx(client, sample_cv):
    res = client.post("/api/generate-cv", json=sample_cv)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment" in res.headers["content-disposition"]
    assert _is_docx(res.content)


def test_generated_filename_is_clean(client, sample_cv):
    res = client.post("/api/generate-cv", json=sample_cv)
    match = re.search(r'filename="([^"]+)"', res.headers["content-disposition"])
    assert match is not None
    assert match.group(1) == "Alex_Example_CV.docx"


def test_unicode_name_gets_utf8_filename(client, sample_cv):
    """Non-ASCII names must survive via the RFC 5987 filename* parameter."""
    from urllib.parse import unquote

    cv = dict(sample_cv)
    cv["name"] = "José"
    res = client.post("/api/generate-cv", json=cv)
    header = res.headers["content-disposition"]
    utf8 = re.search(r"filename\*=UTF-8''([^;]+)", header)
    assert utf8 is not None
    assert unquote(utf8.group(1)) == "José_CV.docx"


def test_generate_minimal_payload(client):
    res = client.post("/api/generate-cv", json={"name": "Just A Name"})
    assert res.status_code == 200
    assert _is_docx(res.content)


# ---- Generate: validation errors ----


def test_missing_name_is_422(client):
    res = client.post("/api/generate-cv", json={})
    assert res.status_code == 422
    assert res.json()["detail"]


def test_blank_name_is_422(client):
    res = client.post("/api/generate-cv", json={"name": "   "})
    assert res.status_code == 422


def test_invalid_email_is_422(client):
    res = client.post(
        "/api/generate-cv",
        json={"name": "Test", "contact": {"email": "not-an-email"}},
    )
    assert res.status_code == 422


def test_invalid_json_is_422(client):
    res = client.post(
        "/api/generate-cv",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


def test_oversized_body_is_413(client, sample_cv):
    # Build a payload just over MAX_REQUEST_BYTES (default 1,000,000).
    big = dict(sample_cv)
    big["summary"] = "x" * 1_100_000
    res = client.post("/api/generate-cv", json=big)
    assert res.status_code == 413


def test_chunked_oversized_body_is_413(client, sample_cv):
    """Bodies without Content-Length must also be capped (stream check)."""
    import json as _json

    big = dict(sample_cv)
    big["summary"] = "x" * 1_100_000
    body = _json.dumps(big).encode()
    res = client.post(
        "/api/generate-cv",
        content=body,
        headers={"Content-Type": "application/json"},  # no Content-Length
    )
    assert res.status_code == 413


def test_500_does_not_leak_internals(client, sample_cv, monkeypatch):
    """Generation failures must return a generic message, not the traceback."""

    def boom(*args, **kwargs):
        raise RuntimeError("SECRET-INTERNAL-DETAIL should never reach the client")

    # The route imports the function into its own namespace, so patch there.
    monkeypatch.setattr("app.api.routes.generate_docx_bytes", boom)
    res = client.post("/api/generate-cv", json=sample_cv)
    assert res.status_code == 500
    assert "SECRET-INTERNAL-DETAIL" not in res.text
    assert "Something went wrong" in res.text


def test_oversized_link_string_is_422(client, sample_cv):
    """Plain-string contact links are capped like every other field."""
    cv = dict(sample_cv)
    cv["contact"] = dict(cv["contact"])
    cv["contact"]["linkedin"] = "x" * 301
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 422


# ---- Generate: lenient inputs still succeed ----


def test_skills_as_comma_string_accepted(client, sample_cv):
    cv = dict(sample_cv)
    cv["skills"] = [{"category": "Core", "items": "Python, SQL"}]
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 200


def test_unknown_fields_are_ignored(client, sample_cv):
    cv = dict(sample_cv)
    cv["totally_unknown_field"] = "ignored"
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 200


def test_empty_entries_are_dropped(client, sample_cv):
    cv = dict(sample_cv)
    cv["experience"] = cv["experience"] + [{"title": "", "company": "", "bullets": []}]
    res = client.post("/api/generate-cv", json=cv)
    assert res.status_code == 200


def test_cors_headers_on_preflight(client):
    res = client.options(
        "/api/generate-cv",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
