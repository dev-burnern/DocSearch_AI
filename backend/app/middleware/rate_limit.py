from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import hashlib
from math import ceil
from threading import Lock
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from backend.app.core.config import Settings


REDIS_SLIDING_WINDOW_SCRIPT = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call("ZREMRANGEBYSCORE", KEYS[1], 0, now - window)
local count = redis.call("ZCARD", KEYS[1])
if count >= limit then
  local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
  redis.call("PEXPIRE", KEYS[1], window)
  return {0, count, oldest[2] or now}
end
redis.call("ZADD", KEYS[1], now, ARGV[4])
redis.call("PEXPIRE", KEYS[1], window)
count = count + 1
local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
return {1, count, oldest[2] or now}
"""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int


class RateLimitBackendUnavailable(RuntimeError):
    pass


class RateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._now = now or time.monotonic
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket_key: str) -> RateLimitDecision:
        now = self._now()

        with self._lock:
            bucket = self._buckets[bucket_key]
            self._prune(bucket, now)

            if len(bucket) >= self._limit:
                retry_after_seconds = self._seconds_until_reset(bucket, now)
                return RateLimitDecision(
                    allowed=False,
                    limit=self._limit,
                    remaining=0,
                    retry_after_seconds=retry_after_seconds,
                    reset_after_seconds=retry_after_seconds,
                )

            bucket.append(now)
            return RateLimitDecision(
                allowed=True,
                limit=self._limit,
                remaining=max(self._limit - len(bucket), 0),
                retry_after_seconds=0,
                reset_after_seconds=self._seconds_until_reset(bucket, now),
            )

    def _prune(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self._window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def _seconds_until_reset(self, bucket: deque[float], now: float) -> int:
        if not bucket:
            return self._window_seconds
        return max(1, int(ceil(self._window_seconds - (now - bucket[0]))))


class RedisRateLimitStore:
    def __init__(
        self,
        *,
        redis_client,
        limit: int,
        window_seconds: int,
        key_prefix: str,
        now: Callable[[], float] | None = None,
        member_factory: Callable[[], str] | None = None,
    ) -> None:
        self._redis_client = redis_client
        self._limit = limit
        self._window_seconds = window_seconds
        self._window_milliseconds = window_seconds * 1000
        self._key_prefix = key_prefix.rstrip(":")
        self._now = now or time.monotonic
        self._member_factory = member_factory or (lambda: uuid.uuid4().hex)

    def check(self, bucket_key: str) -> RateLimitDecision:
        now = self._now()
        now_milliseconds = int(now * 1000)

        try:
            result = self._redis_client.eval(
                REDIS_SLIDING_WINDOW_SCRIPT,
                1,
                self._redis_key(bucket_key),
                now_milliseconds,
                self._window_milliseconds,
                self._limit,
                self._member_factory(),
            )
        except Exception as exc:
            raise RateLimitBackendUnavailable(str(exc)) from exc

        allowed = bool(self._to_int(result[0]))
        count = self._to_int(result[1])
        oldest_milliseconds = self._to_int(result[2])
        reset_after_seconds = self._seconds_until_reset(
            oldest_milliseconds=oldest_milliseconds,
            now_milliseconds=now_milliseconds,
        )

        return RateLimitDecision(
            allowed=allowed,
            limit=self._limit,
            remaining=max(self._limit - count, 0) if allowed else 0,
            retry_after_seconds=0 if allowed else reset_after_seconds,
            reset_after_seconds=reset_after_seconds,
        )

    def _redis_key(self, bucket_key: str) -> str:
        hashed_bucket = hashlib.sha256(bucket_key.encode()).hexdigest()
        return f"{self._key_prefix}:{hashed_bucket}"

    def _seconds_until_reset(
        self,
        *,
        oldest_milliseconds: int,
        now_milliseconds: int,
    ) -> int:
        elapsed = now_milliseconds - oldest_milliseconds
        return max(1, int(ceil((self._window_milliseconds - elapsed) / 1000)))

    @staticmethod
    def _to_int(value) -> int:
        if isinstance(value, bytes):
            value = value.decode()
        return int(float(value))


def create_rate_limit_store(settings: Settings):
    if settings.rate_limit_backend == "redis":
        from redis import Redis

        return RedisRateLimitStore(
            redis_client=Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            ),
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            key_prefix=settings.rate_limit_redis_prefix,
        )

    return RateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings, store=None) -> None:
        super().__init__(app)
        self._enabled = settings.rate_limit_enabled
        self._fail_open = settings.rate_limit_fail_open
        self._store = store or create_rate_limit_store(settings)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._enabled or not request.url.path.startswith("/v1/"):
            return await call_next(request)

        try:
            decision = await run_in_threadpool(
                self._store.check,
                self._bucket_key(request),
            )
        except RateLimitBackendUnavailable:
            if self._fail_open:
                response = await call_next(request)
                response.headers["X-RateLimit-Backend"] = "unavailable"
                return response

            return JSONResponse(
                status_code=503,
                content={
                    "detail": {
                        "code": "RATE_LIMIT_BACKEND_UNAVAILABLE",
                        "message": "Rate limit backend is unavailable.",
                    }
                },
            )

        if not decision.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded. Please retry later.",
                    }
                },
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
            self._apply_headers(response, decision)
            return response

        response = await call_next(request)
        self._apply_headers(response, decision)
        return response

    def _bucket_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key.strip():
            return f"api_key:{api_key.strip()}"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",", maxsplit=1)[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _apply_headers(
        self,
        response: Response,
        decision: RateLimitDecision,
    ) -> None:
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Reset"] = str(decision.reset_after_seconds)
