import httpx

from backend.app.core.config import Settings
from backend.app.core.dependency_health import DependencyHealthChecker


def test_dependency_health_checker_reports_required_dependencies_ready() -> None:
    called: list[str] = []

    checker = DependencyHealthChecker(
        postgres_probe=lambda settings, timeout: called.append("postgres"),
        qdrant_probe=lambda settings, timeout: called.append("qdrant"),
        minio_probe=lambda settings, timeout: called.append("minio"),
        vllm_probe=lambda settings, timeout: called.append("vllm"),
        redis_probe=lambda settings, timeout: called.append("redis"),
        reranker_probe=lambda settings, timeout: called.append("reranker"),
    )
    settings = Settings(
        audit_log_backend="postgres",
        document_metadata_backend="postgres",
        indexing_queue_backend="inprocess",
        reranker_backend="score",
    )

    checks = checker.check(settings)

    assert [check.name for check in checks] == [
        "postgres",
        "qdrant",
        "minio",
        "vllm",
    ]
    assert [check.status for check in checks] == ["ready", "ready", "ready", "ready"]
    assert called == ["postgres", "qdrant", "minio", "vllm"]


def test_dependency_health_checker_checks_optional_backends_when_enabled() -> None:
    called: list[str] = []

    checker = DependencyHealthChecker(
        postgres_probe=lambda settings, timeout: None,
        qdrant_probe=lambda settings, timeout: None,
        minio_probe=lambda settings, timeout: None,
        vllm_probe=lambda settings, timeout: None,
        redis_probe=lambda settings, timeout: called.append("redis"),
        reranker_probe=lambda settings, timeout: called.append("reranker"),
    )
    settings = Settings(
        indexing_queue_backend="redis",
        reranker_backend="bge",
    )

    checks = checker.check(settings)

    assert [check.name for check in checks] == [
        "qdrant",
        "minio",
        "vllm",
        "redis",
        "reranker",
    ]
    assert called == ["redis", "reranker"]


def test_dependency_health_checker_keeps_collecting_after_failure() -> None:
    def fail_postgres(settings: Settings, timeout: float) -> None:
        raise RuntimeError("connection refused")

    checker = DependencyHealthChecker(
        postgres_probe=fail_postgres,
        qdrant_probe=lambda settings, timeout: None,
        minio_probe=lambda settings, timeout: None,
        vllm_probe=lambda settings, timeout: None,
    )
    settings = Settings(
        audit_log_backend="postgres",
        document_metadata_backend="postgres",
    )

    checks = checker.check(settings)

    assert [check.name for check in checks] == [
        "postgres",
        "qdrant",
        "minio",
        "vllm",
    ]
    assert checks[0].status == "not_ready"
    assert "PostgreSQL 연결에 실패했습니다: connection refused" == checks[0].message
    assert [check.status for check in checks[1:]] == ["ready", "ready", "ready"]


def test_dependency_health_checker_uses_expected_http_endpoints(
    monkeypatch,
) -> None:
    calls: list[tuple[str, dict[str, str], float]] = []

    def fake_get(
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response:
        calls.append((url, headers, timeout))
        return httpx.Response(200)

    monkeypatch.setattr("backend.app.core.dependency_health.httpx.get", fake_get)
    checker = DependencyHealthChecker()
    settings = Settings(
        qdrant_url="http://qdrant:6333/",
        minio_endpoint="minio:9000",
        minio_secure=False,
        llm_base_url="http://llm:8000/v1/",
        llm_api_key="local-secret",
        dependency_health_timeout_seconds=1.5,
    )

    checks = checker.check(settings)

    assert [check.status for check in checks] == ["ready", "ready", "ready"]
    assert calls == [
        ("http://qdrant:6333/healthz", {}, 1.5),
        ("http://minio:9000/minio/health/live", {}, 1.5),
        (
            "http://llm:8000/v1/models",
            {"Authorization": "Bearer local-secret"},
            1.5,
        ),
    ]
