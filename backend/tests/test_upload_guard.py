"""Decompression-bomb guard tests.

A DOCX is a ZIP, so the compressed upload cap alone does not bound what a
crafted file expands to. These tests prove the guard accepts real documents
and rejects abusive archives without touching the parsers.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.services.generator import generate_docx_bytes
from app.services.upload_guard import UnsafeUploadError, guard_docx_archive

SAMPLE_CV = {
    "name": "Alex Example",
    "contact": {"email": "alex@example.com", "phone": "+880 1000-000000"},
    "summary": "Engineer building APIs.",
    "experience": [
        {
            "title": "Dev",
            "company": "Acme",
            "dates": "2022 - 2024",
            "bullets": ["Built things."],
        }
    ],
}


def _zip_with_member(name: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buf.getvalue()


def test_real_generated_docx_is_accepted():
    guard_docx_archive(generate_docx_bytes(SAMPLE_CV, "classic", "experienced"))


def test_non_zip_bytes_are_left_to_the_parser():
    # Not a readable ZIP: the guard must not convert a plain corrupt file
    # into a different error class.
    guard_docx_archive(b"definitely not a zip archive")


def test_highly_compressible_member_is_rejected():
    bomb = _zip_with_member("word/document.xml", b"\x00" * (10 * 1024 * 1024))
    with pytest.raises(UnsafeUploadError):
        guard_docx_archive(bomb)


def test_too_many_entries_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as archive:
        for i in range(6000):
            archive.writestr(f"f{i}.txt", b"x")
    with pytest.raises(UnsafeUploadError):
        guard_docx_archive(buf.getvalue())
