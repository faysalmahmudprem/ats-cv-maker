"""HTTP API routes for the CV Generator backend."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict
from urllib.parse import quote

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.schemas.cv import CVRequest
from app.services.generator import DOCX_MIME, generate_docx_bytes
from app.services.import_cv import SUPPORTED_EXTENSIONS, parse_cv_file
from app.services.pdf import generate_pdf_bytes
from app.services.scorer import score_cv_text
from app.services.upload_guard import UnsafeUploadError, guard_docx_archive
from app.services.extractor import extract_text
from app.templates import TEMPLATES

router = APIRouter(prefix="/api")

logger = logging.getLogger("cv_generator")

PDF_MIME = "application/pdf"

_DOWNLOAD_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}


def _safe_filename(name: str, extension: str = "docx") -> str:
    """Turn a person's name into a clean, safe file filename.

    Keeps Unicode letters (Bangla, accents, etc.) so names around the
    world produce sensible filenames; strips characters that are unsafe
    in file names. Falls back to "CV" when nothing usable remains.
    """
    cleaned = re.sub(r"[^\w \-]", "", name, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", "_", cleaned).strip("_-")
    return f"{cleaned or 'CV'}_CV.{extension}"


def _content_disposition(name: str, extension: str = "docx") -> str:
    """Attachment header with an ASCII fallback plus RFC 5987 UTF-8 name.

    Example: attachment; filename="CV_CV.docx"; filename*=UTF-8''%E2%80%A6_CV.docx
    Modern browsers use the UTF-8 form; older clients use the ASCII one.
    """
    filename = _safe_filename(name, extension)
    ascii_name = filename.encode("ascii", "ignore").decode().strip("_-")
    ascii_name = ascii_name or f"CV_CV.{extension}"
    header = f'attachment; filename="{ascii_name}"'
    if ascii_name != filename:
        header += f"; filename*=UTF-8''{quote(filename)}"
    return header


@router.post(
    "/score-cv",
    responses={
        200: {"description": "ATS score + category breakdown + fix list."},
        400: {"description": "No file or unsupported type."},
        413: {"description": "File too large (max 5 MB)."},
        500: {"description": "File unreadable/corrupted."},
    },
    summary="Score an uploaded CV (PDF or DOCX) for ATS readiness",
)
async def score_cv(file: UploadFile = File(...)) -> JSONResponse:
    """Extract text from an uploaded CV and return its ATS score.

    In-memory only — nothing is stored. A file that cannot be read at all
    is a 500; a file that reads but scores badly is a perfectly normal 200.
    """
    filename = file.filename or ""
    extension = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if extension not in (".pdf", ".docx"):
        # Content-Type fallback for clients that send odd filenames.
        ctype = (file.content_type or "").lower()
        if "pdf" in ctype:
            extension = ".pdf"
        elif "wordprocessingml" in ctype or "msword" in ctype:
            extension = ".docx"
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Unsupported file type. Upload a .pdf or .docx"},
            )

    data = await file.read()
    if len(data) > settings.UPLOAD_MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "File too large. Maximum size is 5MB"},
        )
    if not data:
        return JSONResponse(
            status_code=400, content={"error": "No file uploaded"}
        )

    # Guard against decompression bombs before any parser reads the bytes.
    if extension == ".docx":
        try:
            guard_docx_archive(data)
        except UnsafeUploadError as exc:
            return JSONResponse(status_code=413, content={"error": str(exc)})

    # extract_text infers the format from the filename extension, so hand it
    # the resolved extension — the Content-Type fallback above may have
    # corrected a filename that carried none.
    extract_name = filename if filename.lower().endswith(extension) else f"{filename}{extension}"
    text = extract_text(data, extract_name)
    if not text.strip():
        # Never log the filename — it can contain the person's name.
        logger.warning("score-cv: no text extracted (extension %s)", extension)
        return JSONResponse(
            status_code=500,
            content={"error": "Could not read the file. It may be corrupted."},
        )

    return JSONResponse(content=score_cv_text(text))


@router.post(
    "/import-cv",
    responses={
        200: {"description": "Parsed CV data + warnings."},
        413: {"description": "File too large."},
        415: {"description": "Unsupported file type."},
        422: {"description": "Unreadable/corrupt file."},
    },
    summary="Import an existing CV file (DOCX or PDF) into editable data",
)
async def import_cv(file: UploadFile = File(...)) -> JSONResponse:
    """Parse an uploaded CV into structured data for the editor.

    In-memory only: the file is parsed and discarded, nothing stored.
    Malformed input returns 422 with a human explanation; a parsed-but-
    imperfect CV returns 200 with `warnings` the UI shows the user.
    """
    filename = file.filename or ""
    extension = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    doc_kind = SUPPORTED_EXTENSIONS.get(extension, "")

    # Content-Type fallback for clients that send odd filenames.
    if not doc_kind:
        ctype = (file.content_type or "").lower()
        if "pdf" in ctype:
            doc_kind = "pdf"
        elif "wordprocessingml" in ctype or "msword" in ctype:
            doc_kind = "docx"

    if not doc_kind:
        return JSONResponse(
            status_code=415,
            content={"error": "Unsupported file type. Upload a .docx or .pdf file."},
        )

    data = await file.read()
    if len(data) > settings.UPLOAD_MAX_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "File too large (max 5 MB)."},
        )
    if not data:
        return JSONResponse(status_code=422, content={"error": "The uploaded file is empty."})

    # Guard against decompression bombs before parsing untrusted bytes.
    if doc_kind == "docx":
        try:
            guard_docx_archive(data)
        except UnsafeUploadError as exc:
            return JSONResponse(status_code=413, content={"error": str(exc)})

    try:
        result = parse_cv_file(data, doc_kind, filename)
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    except Exception:
        logger.exception("CV import failed")
        return JSONResponse(
            status_code=500,
            content={"error": "Something went wrong while reading your file. Please try again."},
        )

    # Round-trip through the same validation as the manual form: anything
    # malformed is dropped, lengths are capped, defaults are filled.
    # `name` is required by CVRequest, so a missing name is validated with a
    # placeholder and then restored (the UI asks the user to fill it in).
    cv_raw = result["cv"]
    try:
        validated = CVRequest(
            **{**cv_raw, "name": cv_raw.get("name") or "Your Name", "template": "classic", "profile": "experienced"},
        )
    except Exception:
        logger.exception("Imported CV failed validation")
        return JSONResponse(
            status_code=422,
            content={"error": "Could not interpret this CV. Try editing it here manually."},
        )
    cv_data = validated.model_dump()
    for key in ("template", "profile", "format"):
        cv_data.pop(key, None)
    cv_data["name"] = cv_raw.get("name", "")

    return JSONResponse(content={"cv": cv_data, "warnings": result["warnings"], "meta": result["meta"]})


@router.get("/health")
async def health() -> Dict[str, str]:
    """Liveness probe for deployment platforms and uptime checks."""
    return {"status": "ok"}


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """Available CV templates for the frontend template picker."""
    return {
        "templates": [
            {
                "key": t.key,
                "label": t.label,
                "description": t.description,
                "accent_hex": f"#{t.accent_hex}",
            }
            for t in TEMPLATES.values()
        ]
    }


@router.post(
    "/generate-cv",
    response_class=Response,
    responses={
        200: {
            "content": {
                DOCX_MIME: {},
                PDF_MIME: {},
            },
            "description": "Generated CV file download (DOCX or PDF, per 'format').",
        },
        422: {"description": "Validation error (JSON detail)."},
        413: {"description": "Request body too large."},
    },
    summary="Generate a CV as a downloadable DOCX or PDF file",
)
async def generate_cv(request: Request, payload: CVRequest) -> Response:
    """Validate a CV payload and return the generated file as a download.

    The optional `format` field selects "docx" (default) or "pdf". Both
    formats render the same layout (app/services/layout.py), so content,
    section order and headings are identical.

    Request size is capped by middleware (see app.main). Generation happens
    in memory; no files are written to disk, so there is nothing to clean up.
    """
    # 1) Request size protection (checked before parsing heavy work).
    body = await request.body()
    if len(body) > settings.MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "Request body too large."},
        )

    # 2) Build the file from the validated payload.
    try:
        if payload.format == "pdf":
            file_bytes = generate_pdf_bytes(
                payload.model_dump(), payload.template, payload.profile
            )
            media_type = PDF_MIME
            extension = "pdf"
        else:
            file_bytes = generate_docx_bytes(
                payload.model_dump(), payload.template, payload.profile
            )
            media_type = DOCX_MIME
            extension = "docx"
    except Exception:  # pragma: no cover - defensive
        # Log the full traceback server-side; never leak internals to clients.
        logger.exception("CV generation failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong while generating your document. Please try again."
            },
        )

    # 3) Return as a browser download with a sensible filename.
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            **_DOWNLOAD_HEADERS,
            "Content-Disposition": _content_disposition(payload.name, extension),
            "Content-Length": str(len(file_bytes)),
        },
    )
