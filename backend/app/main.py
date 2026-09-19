"""FastAPI application entrypoint.

Run locally from the backend/ directory:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from app.api.rate_limit import RateLimitMiddleware
from app.api.routes import router
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Generate ATS-friendly CV (.docx) files from structured JSON.",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


class BodyTooLarge(Exception):
    """Raised internally when the request body exceeds the byte cap."""


class BodySizeLimitMiddleware:
    """Reject oversized request bodies with 413.

    Pure-ASGI middleware: it wraps the raw `receive` callable so BOTH cases
    are covered —
    - Content-Length known up front -> rejected before reading anything.
    - Chunked / streaming bodies (no Content-Length) -> at most
      max_bytes is ever buffered in memory.

    The upload path (file imports) allows a larger cap than JSON endpoints.
    The cap is read per-request via `max_bytes_fn` so tests can adjust it.

    This middleware is added FIRST so CORS (added after, hence outermost)
    still decorates 413 responses with the right headers for the browser.
    """

    def __init__(self, app, max_bytes: int, upload_max_bytes: int | None = None,
                 upload_paths: tuple[str, ...] = ("/api/import-cv", "/api/score-cv")):
        self.app = app
        self.max_bytes = max_bytes
        self.upload_max_bytes = upload_max_bytes if upload_max_bytes is not None else max_bytes
        self.upload_paths = upload_paths

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return

        # Upload endpoints use the larger cap.
        max_bytes = (
            self.upload_max_bytes
            if scope.get("path", "").startswith(self.upload_paths)
            else self.max_bytes
        )

        # Fast path: declared size already too big.
        content_length = Headers(scope=scope).get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large."},
                )
                await response(scope, receive, send)
                return

        received = 0

        async def capped_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise BodyTooLarge()
            return message

        try:
            await self.app(scope, capped_receive, send)
        except BodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"error": "Request body too large."},
            )
            await response(scope, receive, send)


app.add_middleware(
    BodySizeLimitMiddleware,
    max_bytes=settings.MAX_REQUEST_BYTES,
    upload_max_bytes=settings.UPLOAD_MAX_BYTES,
)


# Best-effort per-IP rate limiting for the CPU-heavy endpoints. Added BEFORE
# CORS, so CORS stays outermost and still decorates a 429 with the right
# headers (Starlette applies the last-added middleware outermost).
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.RATE_LIMIT_ENABLED,
    limit=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    limited_prefixes=("/api/generate-cv", "/api/import-cv", "/api/score-cv"),
)


# CORS: origins come from the CORS_ORIGINS environment variable
# (comma-separated). Local Vite dev origins are the development default;
# production startup fails fast when it is missing (see app.config).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(router)
