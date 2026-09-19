"""Upload safety guards for archived/structured files.

A 5 MB upload cap bounds the *compressed* size of an upload, but a DOCX is
a ZIP archive and can expand far beyond its on-disk size — the classic
"decompression bomb". Before any parser (python-docx / PyMuPDF) touches the
bytes, we inspect the ZIP central directory and reject anything whose
declared uncompressed footprint, entry count, or compression ratio looks
abusive.

This uses only the standard library, so it adds no dependency to the
document-generation path, and it never mutates or re-writes the upload —
parser failures still surface through the normal error handling.
"""

from __future__ import annotations

import io
import zipfile

from app.config import settings


class UnsafeUploadError(ValueError):
    """Raised when an upload looks like a decompression bomb.

    Subclasses ``ValueError`` so callers can treat it like any other
    "this file is not acceptable" rejection.
    """


def guard_docx_archive(data: bytes) -> None:
    """Reject a DOCX/ZIP upload whose expansion looks abusive.

    A file that is not a readable ZIP is left alone: the parser will report
    it as unreadable through the normal path, and this guard must not turn a
    plain "corrupt file" into a different error class.

    Raises:
        UnsafeUploadError: entry count, uncompressed total, or compression
            ratio exceeds the configured ceiling.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile:
        return
    except Exception:
        # Any other read failure is the parser's problem to report.
        return

    if len(infos) > settings.MAX_ARCHIVE_ENTRIES:
        raise UnsafeUploadError(
            "This file contains too many internal parts to process safely."
        )

    total_uncompressed = 0
    for info in infos:
        total_uncompressed += info.file_size
        if total_uncompressed > settings.MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise UnsafeUploadError(
                "This file is far larger when opened than its upload size suggests."
            )
        # A single highly-compressible member is the signature of a bomb.
        compressed = max(info.compress_size, 1)
        if info.file_size // compressed > settings.MAX_ARCHIVE_RATIO:
            raise UnsafeUploadError(
                "This file is far larger when opened than its upload size suggests."
            )
