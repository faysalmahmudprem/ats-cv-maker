"""
extract_text(file_bytes, filename) -> str

Extracts plain text from uploaded CV files.
Supports: .docx, .pdf
Returns empty string on failure — never raises to the caller.

This is the PLAIN-TEXT extractor used by the ATS scorer. It is
deliberately separate from services/import_cv.py, whose extractors
preserve per-line formatting metadata (bold/size/bullets) for structure
reconstruction — here we only need the raw words.
"""

from __future__ import annotations

import logging
import re
import io

from app.config import settings

logger = logging.getLogger("cv_generator")

# Single source of truth for the extract cap (same value as the upload cap).
MAX_EXTRACT_BYTES = settings.UPLOAD_MAX_BYTES


def _kind_hint(filename: str) -> str:
    """Non-identifying description of an upload for logs: extension only.

    Filenames frequently contain a person's name ("Jane_Doe_CV.docx"), so
    they must never reach the logs — only the format hint is logged.
    """
    _, _, ext = (filename or "").rpartition(".")
    return f".{ext.lower()}" if ext else "<no-extension>"

try:  # PyMuPDF (imported as `fitz` historically; `pymupdf` is the modern name)
    import fitz  # type: ignore
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore

from docx import Document as DocxDocument


def _normalize(text: str) -> str:
    """Strip excessive whitespace, normalize line breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs but keep line structure.
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ blank lines to one blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_text(data: bytes) -> str:
    if fitz is None:  # pragma: no cover
        logger.warning("PyMuPDF not installed — PDF extraction unavailable")
        return ""
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            pages = [page.get_text("text") for page in doc]
        return _normalize("\n".join(pages))
    except Exception:
        logger.exception("PDF text extraction failed")
        return ""


def _docx_text(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
    except Exception:
        logger.exception("DOCX text extraction failed")
        return ""
    parts: list[str] = [p.text for p in doc.paragraphs]
    # Table cells: ATS-relevant content often hides in tables.
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return _normalize("\n".join(parts))


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a .pdf or .docx upload.

    Returns "" for anything unsupported, oversized, or unreadable —
    callers decide how to present the failure; this never raises.
    """
    if len(file_bytes) > MAX_EXTRACT_BYTES:
        logger.warning(
            "Extraction skipped: %s upload is %d bytes (max %d)",
            _kind_hint(filename),
            len(file_bytes),
            MAX_EXTRACT_BYTES,
        )
        return ""

    filename = (filename or "").lower()
    if filename.endswith(".pdf"):
        text = _pdf_text(file_bytes)
    elif filename.endswith(".docx"):
        text = _docx_text(file_bytes)
    else:
        logger.warning(
            "Extraction skipped: unsupported file type %s", _kind_hint(filename)
        )
        return ""

    # Defensive cap: never hand an unbounded string to the scorer.
    return text[: settings.MAX_EXTRACT_CHARS]
