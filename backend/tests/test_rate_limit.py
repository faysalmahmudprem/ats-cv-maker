"""Rate limiter tests.

The functional suite runs with rate limiting disabled (see conftest), so the
limiter is exercised directly and through a purpose-built app. The main
app's configuration is never mutated here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rate_limit import RateLimitMiddleware, SlidingWindowLimiter


# ---- Limiter unit tests --------------------------------------------------


def test_allows_under_limit_then_blocks():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=60)
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_hits_expire_after_the_window(monkeypatch):
    import app.api.rate_limit as rl

    clock = {"t": 1000.0}
    monkeypatch.setattr(rl.time, "monotonic", lambda: clock["t"])
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)

    assert limiter.allow("x") is True
    assert limiter.allow("x") is False
    clock["t"] += 61.0
    assert limiter.allow("x") is True


def test_retry_after_is_positive_while_blocked():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    limiter.allow("x")
    assert limiter.allow("x") is False
    assert limiter.retry_after("x") >= 0


# ---- Middleware integration ---------------------------------------------


def _build_app(limit: int, *, enabled: bool = True) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        enabled=enabled,
        limit=limit,
        window_seconds=60,
        limited_prefixes=("/api/generate-cv",),
    )

    @app.post("/api/generate-cv")
    async def generate() -> dict:
        return {"ok": True}

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    return TestClient(app)


def test_middleware_returns_429_with_retry_after():
    client = _build_app(limit=2)
    assert client.post("/api/generate-cv").status_code == 200
    assert client.post("/api/generate-cv").status_code == 200

    res = client.post("/api/generate-cv")
    assert res.status_code == 429
    assert res.headers.get("Retry-After") is not None
    assert "Too many requests" in res.json()["error"]


def test_middleware_never_limits_exempt_paths():
    client = _build_app(limit=1)
    for _ in range(6):
        assert client.get("/api/health").status_code == 200


def test_middleware_is_a_noop_when_disabled():
    client = _build_app(limit=1, enabled=False)
    for _ in range(6):
        assert client.post("/api/generate-cv").status_code == 200
