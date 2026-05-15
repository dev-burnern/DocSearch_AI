from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.main import create_app
from backend.app.middleware.rate_limit import RateLimiter


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_rate_limiter_blocks_bucket_after_limit() -> None:
    now = 1000.0
    limiter = RateLimiter(limit=2, window_seconds=60, now=lambda: now)

    first = limiter.check("api-key:alpha")
    second = limiter.check("api-key:alpha")
    third = limiter.check("api-key:alpha")

    assert first.allowed is True
    assert second.allowed is True
    assert second.remaining == 0
    assert third.allowed is False
    assert third.retry_after_seconds == 60
    assert third.remaining == 0


def test_rate_limiter_allows_bucket_after_window_expires() -> None:
    current_time = 1000.0

    def now() -> float:
        return current_time

    limiter = RateLimiter(limit=1, window_seconds=10, now=now)

    assert limiter.check("api-key:alpha").allowed is True
    assert limiter.check("api-key:alpha").allowed is False

    current_time = 1011.0

    decision = limiter.check("api-key:alpha")

    assert decision.allowed is True
    assert decision.remaining == 0


def test_v1_routes_are_limited_by_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "alpha-key|workspace-alpha|Workspace Alpha;beta-key|workspace-beta|Workspace Beta",
    )
    client = TestClient(create_app())

    first = client.get("/v1/workspace", headers={"X-API-Key": "alpha-key"})
    second = client.get("/v1/workspace", headers={"X-API-Key": "alpha-key"})
    blocked = client.get("/v1/workspace", headers={"X-API-Key": "alpha-key"})
    other_key = client.get("/v1/workspace", headers={"X-API-Key": "beta-key"})

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "2"
    assert first.headers["X-RateLimit-Remaining"] == "1"
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "0"
    assert blocked.status_code == 429
    assert blocked.headers["X-Request-Id"].startswith("req_")
    assert blocked.headers["X-Content-Type-Options"] == "nosniff"
    assert blocked.headers["Retry-After"] == "60"
    assert blocked.headers["X-RateLimit-Limit"] == "2"
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert blocked.json() == {
        "detail": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded. Please retry later.",
        }
    }
    assert other_key.status_code == 200
    assert other_key.headers["X-RateLimit-Remaining"] == "1"


def test_v1_routes_are_limited_by_ip_when_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())

    first = client.get("/v1/workspace")
    blocked = client.get("/v1/workspace")

    assert first.status_code == 401
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_operational_routes_are_not_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())

    first = client.get("/health")
    second = client.get("/health")

    assert first.status_code == 200
    assert second.status_code == 200
    assert "X-RateLimit-Limit" not in second.headers
