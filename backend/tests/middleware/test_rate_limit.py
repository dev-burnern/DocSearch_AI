from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.core.operation_events import InMemoryOperationEventStore
from backend.app.main import create_app
from backend.app.middleware.rate_limit import (
    RateLimitBackendUnavailable,
    RateLimitMiddleware,
    RateLimiter,
    RedisRateLimitStore,
)


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


def test_redis_rate_limit_store_allows_request_with_hashed_bucket_key() -> None:
    redis_client = FakeRedisClient(result=[1, 1, 1000000])
    store = RedisRateLimitStore(
        redis_client=redis_client,
        limit=2,
        window_seconds=60,
        key_prefix="docsearch:test",
        now=lambda: 1000.0,
        member_factory=lambda: "member-1",
    )

    decision = store.check("api_key:secret-key")

    assert decision.allowed is True
    assert decision.remaining == 1
    assert decision.reset_after_seconds == 60
    assert redis_client.calls[0]["key"].startswith("docsearch:test:")
    assert "secret-key" not in redis_client.calls[0]["key"]
    assert redis_client.calls[0]["args"] == (
        1000000,
        60000,
        2,
        "member-1",
    )


def test_redis_rate_limit_store_blocks_after_limit() -> None:
    redis_client = FakeRedisClient(result=[0, 2, 1000000])
    store = RedisRateLimitStore(
        redis_client=redis_client,
        limit=2,
        window_seconds=60,
        key_prefix="docsearch:test",
        now=lambda: 1030.0,
        member_factory=lambda: "member-3",
    )

    decision = store.check("api_key:secret-key")

    assert decision.allowed is False
    assert decision.remaining == 0
    assert decision.retry_after_seconds == 30
    assert decision.reset_after_seconds == 30


def test_redis_rate_limit_store_wraps_backend_errors() -> None:
    store = RedisRateLimitStore(
        redis_client=FailingRedisClient(),
        limit=2,
        window_seconds=60,
        key_prefix="docsearch:test",
        now=lambda: 1000.0,
        member_factory=lambda: "member-1",
    )

    with pytest.raises(RateLimitBackendUnavailable):
        store.check("api_key:secret-key")


def test_rate_limit_middleware_fails_open_when_backend_is_unavailable() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        settings=FailOpenSettings(),
        store=UnavailableRateLimitStore(),
    )

    @app.get("/v1/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/v1/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-RateLimit-Backend"] == "unavailable"


def test_rate_limit_middleware_records_backend_unavailable_event() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    event_store = InMemoryOperationEventStore()
    app.state.operation_event_store = event_store
    app.add_middleware(
        RateLimitMiddleware,
        settings=FailOpenSettings(),
        store=UnavailableRateLimitStore(),
    )

    @app.get("/v1/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)

    response = client.get("/v1/ping")

    assert response.status_code == 200
    event = event_store.list_events()[0]
    assert event.event_type == "rate_limit.backend_unavailable"
    assert event.severity == "error"
    assert event.source == "rate_limit"
    assert event.details == {
        "method": "GET",
        "path": "/v1/ping",
    }


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


def test_v1_routes_are_limited_by_bearer_token() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, settings=LimitByOneSettings())

    @app.get("/v1/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)

    first = client.get("/v1/ping", headers={"Authorization": "Bearer alpha-token"})
    blocked = client.get("/v1/ping", headers={"Authorization": "Bearer alpha-token"})
    other_token = client.get("/v1/ping", headers={"Authorization": "Bearer beta-token"})

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert other_token.status_code == 200


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


class FakeRedisClient:
    def __init__(self, *, result: list[int]) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def eval(self, script, numkeys, key, *args):
        self.calls.append(
            {
                "script": script,
                "numkeys": numkeys,
                "key": key,
                "args": args,
            }
        )
        return self._result


class FailingRedisClient:
    def eval(self, script, numkeys, key, *args):
        raise RuntimeError("redis unavailable")


class UnavailableRateLimitStore:
    def check(self, bucket_key: str):
        raise RateLimitBackendUnavailable("redis unavailable")


class FailOpenSettings:
    rate_limit_enabled = True
    rate_limit_backend = "redis"
    rate_limit_requests = 1
    rate_limit_window_seconds = 60
    rate_limit_redis_prefix = "docsearch:test"
    rate_limit_fail_open = True
    redis_url = "redis://redis:6379/0"


class LimitByOneSettings:
    rate_limit_enabled = True
    rate_limit_backend = "memory"
    rate_limit_requests = 1
    rate_limit_window_seconds = 60
    rate_limit_redis_prefix = "docsearch:test"
    rate_limit_fail_open = True
    redis_url = "redis://redis:6379/0"
