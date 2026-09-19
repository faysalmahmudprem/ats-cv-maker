"""Environment-based configuration.

All settings come from environment variables with sane local defaults,
so the backend runs with zero configuration locally and in production.
No secrets and no hard-coded production URLs live here.
"""

from __future__ import annotations

import os
import sys

# Environments that serve real users. In these, running with the default
# development CORS list would silently break the deployed frontend (browser
# CORS errors), so we refuse to start instead of failing at runtime.
_PRODUCTION_ENVS = {"production", "prod"}


def _csv_env(name: str, default: str = "") -> list[str]:
    """Read a comma-separated env var into a clean list."""
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Simple settings object. Reads env vars once at import time."""

    # App
    APP_NAME: str = os.environ.get("APP_NAME", "CV Generator API")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    DEBUG: bool = os.environ.get("DEBUG", "0") == "1"

    # CORS: comma-separated list of allowed browser origins.
    # Local Vite dev server is allowed by default for development.
    CORS_ORIGINS: list[str] = _csv_env(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    # Requests larger than this (bytes) are rejected with 413.
    # ~1 MB is far above any legitimate CV payload.
    MAX_REQUEST_BYTES: int = int(os.environ.get("MAX_REQUEST_BYTES", "1000000"))

    # Upload cap for file-import endpoints (multipart). CVs are small;
    # 5 MB is generous for real documents while still bounding abuse.
    UPLOAD_MAX_BYTES: int = int(os.environ.get("UPLOAD_MAX_BYTES", "5000000"))

    # Defensive cap on the length of text extracted from an uploaded file.
    # Normal CVs are a few thousand words; this only stops a crafted file
    # from producing an unbounded string.
    MAX_EXTRACT_CHARS: int = int(os.environ.get("MAX_EXTRACT_CHARS", "200000"))

    # Decompression-bomb guards for archived uploads (a DOCX is a ZIP).
    # The 5 MB upload cap bounds the COMPRESSED size; a crafted archive can
    # still expand far beyond it, so the central directory is inspected
    # before any parser reads the bytes.
    MAX_ARCHIVE_ENTRIES: int = int(os.environ.get("MAX_ARCHIVE_ENTRIES", "5000"))
    MAX_ARCHIVE_UNCOMPRESSED_BYTES: int = int(
        os.environ.get("MAX_ARCHIVE_UNCOMPRESSED_BYTES", "50000000")
    )
    MAX_ARCHIVE_RATIO: int = int(os.environ.get("MAX_ARCHIVE_RATIO", "200"))

    # Best-effort, per-IP rate limiting for the CPU-heavy endpoints. It is
    # in-process (per worker), which is enough to blunt casual abuse without
    # a datastore. Set RATE_LIMIT_ENABLED=0 to disable (tests do this).
    RATE_LIMIT_ENABLED: bool = os.environ.get("RATE_LIMIT_ENABLED", "1") == "1"
    RATE_LIMIT_PER_MINUTE: int = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")
    )


settings = Settings()

if settings.ENVIRONMENT in _PRODUCTION_ENVS and not os.environ.get("CORS_ORIGINS"):
    print(
        "FATAL: ENVIRONMENT=production requires CORS_ORIGINS to be set "
        "(comma-separated list of allowed frontend origins). "
        "Refusing to start with development defaults.",
        file=sys.stderr,
    )
    sys.exit(1)
