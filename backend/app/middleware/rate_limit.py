from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.app.core.config import Settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    reset_after_seconds: int


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


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:
        super().__init__(app)
        self._enabled = settings.rate_limit_enabled
        self._limiter = RateLimiter(
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._enabled or not request.url.path.startswith("/v1/"):
            return await call_next(request)

        decision = self._limiter.check(self._bucket_key(request))
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
