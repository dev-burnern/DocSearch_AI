import socket
from typing import Callable, Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from backend.app.core.config import Settings


DependencyStatus = Literal["ready", "not_ready"]
DependencyProbe = Callable[[Settings, float], None]


class DependencyCheckResult(BaseModel):
    name: str
    status: DependencyStatus
    message: str


class DependencyHealthChecker:
    def __init__(
        self,
        *,
        postgres_probe: DependencyProbe | None = None,
        qdrant_probe: DependencyProbe | None = None,
        minio_probe: DependencyProbe | None = None,
        vllm_probe: DependencyProbe | None = None,
        redis_probe: DependencyProbe | None = None,
        reranker_probe: DependencyProbe | None = None,
    ) -> None:
        self._postgres_probe = postgres_probe or _probe_postgres
        self._qdrant_probe = qdrant_probe or _probe_qdrant
        self._minio_probe = minio_probe or _probe_minio
        self._vllm_probe = vllm_probe or _probe_vllm
        self._redis_probe = redis_probe or _probe_redis
        self._reranker_probe = reranker_probe or _probe_reranker

    def check(self, settings: Settings) -> list[DependencyCheckResult]:
        timeout = settings.dependency_health_timeout_seconds
        checks: list[tuple[str, str, DependencyProbe]] = []

        if _uses_postgres(settings):
            checks.append(("postgres", "PostgreSQL", self._postgres_probe))

        checks.extend(
            [
                ("qdrant", "Qdrant", self._qdrant_probe),
                ("minio", "MinIO", self._minio_probe),
                ("vllm", "vLLM", self._vllm_probe),
            ]
        )

        if (
            settings.indexing_queue_backend == "redis"
            or settings.rate_limit_backend == "redis"
        ):
            checks.append(("redis", "Redis", self._redis_probe))

        if settings.reranker_backend == "bge":
            checks.append(("reranker", "BGE Reranker", self._reranker_probe))

        return [
            _run_probe(
                name=name,
                display_name=display_name,
                probe=probe,
                settings=settings,
                timeout=timeout,
            )
            for name, display_name, probe in checks
        ]


def _uses_postgres(settings: Settings) -> bool:
    return (
        settings.audit_log_backend == "postgres"
        or settings.document_metadata_backend == "postgres"
    )


def _run_probe(
    *,
    name: str,
    display_name: str,
    probe: DependencyProbe,
    settings: Settings,
    timeout: float,
) -> DependencyCheckResult:
    try:
        probe(settings, timeout)
    except Exception as exc:
        return DependencyCheckResult(
            name=name,
            status="not_ready",
            message=f"{display_name} 연결에 실패했습니다: {exc}",
        )

    return DependencyCheckResult(
        name=name,
        status="ready",
        message=f"{display_name} 연결을 확인했습니다.",
    )


def _probe_postgres(settings: Settings, timeout: float) -> None:
    from psycopg import connect

    with connect(settings.database_url, connect_timeout=timeout) as connection:
        connection.execute("SELECT 1")


def _probe_qdrant(settings: Settings, timeout: float) -> None:
    _probe_http_endpoint(
        url=f"{settings.qdrant_url.rstrip('/')}/healthz",
        timeout=timeout,
    )


def _probe_minio(settings: Settings, timeout: float) -> None:
    scheme = "https" if settings.minio_secure else "http"
    _probe_http_endpoint(
        url=f"{scheme}://{settings.minio_endpoint}/minio/health/live",
        timeout=timeout,
    )


def _probe_vllm(settings: Settings, timeout: float) -> None:
    _probe_http_endpoint(
        url=f"{settings.llm_base_url.rstrip('/')}/models",
        timeout=timeout,
        api_key=settings.llm_api_key,
    )


def _probe_reranker(settings: Settings, timeout: float) -> None:
    _probe_http_endpoint(
        url=f"{settings.reranker_base_url.rstrip('/')}/models",
        timeout=timeout,
        api_key=settings.reranker_api_key,
    )


def _probe_http_endpoint(
    *,
    url: str,
    timeout: float,
    api_key: str | None = None,
) -> None:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = httpx.get(url, headers=headers, timeout=timeout)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}")


def _probe_redis(settings: Settings, timeout: float) -> None:
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379

    with socket.create_connection((host, port), timeout=timeout) as connection:
        connection.settimeout(timeout)
        if parsed.password:
            _send_redis_command(connection, "AUTH", parsed.password)
        response = _send_redis_command(connection, "PING")
        if not response.startswith(b"+PONG"):
            raise RuntimeError("Redis PING 응답이 올바르지 않습니다.")


def _send_redis_command(connection: socket.socket, *parts: str) -> bytes:
    payload = f"*{len(parts)}\r\n"
    for part in parts:
        encoded = part.encode()
        payload += f"${len(encoded)}\r\n{part}\r\n"

    connection.sendall(payload.encode())
    return connection.recv(1024)
