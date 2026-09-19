"""Dependency-free, best-effort per-IP rate limiting.

In-process and approximate, by design: with multiple workers each process
keeps its own counters, so the effective ceiling is roughly
``limit x workers``. That is enough to blunt casual abuse of the CPU-heavy
endpoints (generate, import, score) without adding a datastore or a
dependency. A distributed limiter belongs with the Phase 2 infrastructure;
at the edge (CDN/WAF) it would complement this.

The limiter is opt-out via ``settings.RATE_LIMIT_ENABLED`` so the functional
test suite can run unaffected while the behaviour is covered directly.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Iterable, MutableMapping

from fastapi.responses import JSONResponse


class SlidingWindowLimiter:
    """A tiny sliding-window counter keyed by an opaque string (IP address)."""

    def __init__(self, limit: int, window_seconds: float = 60.0, max_keys: int = 20000):
        self.limit = max(1, int(limit))
        self.window = float(window_seconds)
        self.max_keys = max(1, int(max_keys))
        self._hits: MutableMapping[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Record a hit and return True if it is within the limit."""
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            # Crude memory bound: if we are tracking too many keys, reset.
            # (A flood of unique IPs is itself the abuse we are bounding.)
            if len(self._hits) > self.max_keys:
                self._hits.clear()
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True

    def retry_after(self, key: str) -> int:
        """Whole seconds until the oldest hit ages out (0 when free now)."""
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.get(key)
            oldest = bucket[0] if bucket else now
        return max(0, int(self.window - (now - oldest) + 0.999))


class RateLimitMiddleware:
    """ASGI middleware: 429 for abusive traffic on the expensive paths.

    Only requests whose path starts with ``limited_prefixes`` are counted, so
    health checks, template listing, and static-ish endpoints are never
    affected.
    """

    def __init__(
        self,
        app,
        *,
        enabled: bool = True,
        limit: int = 30,
        window_seconds: float = 60.0,
        limited_prefixes: Iterable[str] = (),
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.limited_prefixes = tuple(limited_prefixes)
        self.limiter = SlidingWindowLimiter(limit, window_seconds)

    @staticmethod
    def _client_ip(scope) -> str:
        """Best-effort client IP, honouring the first X-Forwarded-For hop.

        The app runs behind Render's proxy, so the socket peer is the proxy;
        the forwarded header carries the real client.
        """
        headers = dict(scope.get("headers") or [])
        forwarded = headers.get(b"x-forwarded-for")
        if forwarded:
            first = forwarded.split(b",")[0].strip().decode("latin-1", "ignore")
            if first:
                return first
        client = scope.get("client")
        if client:
            return str(client[0])
        return "unknown"

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not self.limited_prefixes or not path.startswith(self.limited_prefixes):
            await self.app(scope, receive, send)
            return

        ip = self._client_ip(scope)
        if self.limiter.allow(ip):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests. Please wait a moment and try again."
            },
            headers={"Retry-After": str(self.limiter.retry_after(ip))},
        )
        await response(scope, receive, send)
