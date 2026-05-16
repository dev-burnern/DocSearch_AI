from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.core.dependency_health import DependencyCheckResult
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_관리자_운영상태_API가_현재_운영_요약을_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|admin",
    )
    monkeypatch.setenv("DEPENDENCY_HEALTH_CHECKS_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "30")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "10")
    checker = FakeDependencyHealthChecker(
        [
            DependencyCheckResult(
                name="qdrant",
                status="ready",
                message="Qdrant 연결이 정상입니다.",
            )
        ]
    )
    app = create_app()
    app.state.dependency_health_checker = checker
    client = TestClient(app)

    response = client.get(
        "/v1/admin/operations",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["service"] == "docsearch-ai"
    assert body["workspace"] == {
        "workspace_id": "workspace-alpha",
        "workspace_name": "Workspace Alpha",
        "role": "admin",
    }
    assert body["checks"][-1] == {
        "name": "qdrant",
        "status": "ready",
        "message": "Qdrant 연결이 정상입니다.",
    }
    assert body["events"] == []
    assert body["settings"]["environment"] == "development"
    assert body["settings"]["dependency_health_checks_enabled"] is True
    assert body["settings"]["retrieval_mode"] == "dense"
    assert body["settings"]["hybrid_dense_weight"] == 0.7
    assert body["settings"]["hybrid_lexical_weight"] == 0.3
    assert body["settings"]["hybrid_candidate_limit"] == 50
    assert body["settings"]["rate_limit"] == {
        "enabled": True,
        "backend": "memory",
        "requests": 30,
        "window_seconds": 10,
        "fail_open": True,
    }
    assert body["settings"]["backends"] == {
        "audit_log": "inmemory",
        "document_metadata": "inmemory",
        "indexing_queue": "inprocess",
        "embedding": "deterministic",
        "reranker": "score",
    }
    assert body["settings"]["models"] == {
        "llm": "google/gemma-4-E4B-it",
        "llm_timeout_seconds": 30.0,
        "llm_max_tokens": 1024,
        "llm_temperature": 0.2,
        "llm_max_retries": 2,
        "llm_retry_backoff_seconds": 0.5,
        "embedding": "BAAI/bge-m3",
        "reranker": "BAAI/bge-reranker-v2-m3",
        "embedding_vector_size": 8,
    }
    assert body["indexing_queue"] == {
        "backend": "inprocess",
        "status": "ready",
        "queue_key": None,
        "pending_jobs": 0,
        "max_attempts": 3,
        "message": "인프로세스 인덱싱은 업로드 요청 중 즉시 처리됩니다.",
    }
    assert checker.called is True


def test_관리자_운영상태_API는_Redis_인덱싱_큐_대기건수를_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.admin import operations

    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|admin",
    )
    monkeypatch.setenv("INDEXING_QUEUE_BACKEND", "redis")
    monkeypatch.setenv("INDEXING_QUEUE_REDIS_KEY", "docsearch:indexing:test")
    monkeypatch.setenv("INDEXING_QUEUE_MAX_ATTEMPTS", "5")
    monkeypatch.setattr(
        operations,
        "create_redis_job_queue",
        lambda settings: FakeRedisQueue(pending_count=7),
    )
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/v1/admin/operations",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200
    assert response.json()["indexing_queue"] == {
        "backend": "redis",
        "status": "ready",
        "queue_key": "docsearch:indexing:test",
        "pending_jobs": 7,
        "max_attempts": 5,
        "message": "Redis 인덱싱 큐 대기건수 조회에 성공했습니다.",
    }


def test_관리자_운영상태_API는_일반_사용자_접근을_거부한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "member-key|workspace-alpha|Workspace Alpha|member",
    )
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/v1/admin/operations",
        headers={"X-API-Key": "member-key"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "AUTH_FORBIDDEN_ROLE",
            "message": "Admin role is required.",
        }
    }


def test_관리자_운영상태_API는_민감한_설정을_노출하지_않는다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|admin",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://secret-user:secret-password@postgres:5432/docsearch",
    )
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio-secret")
    monkeypatch.setenv("LLM_API_KEY", "llm-secret")
    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/v1/admin/operations",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200
    serialized_response = response.text
    assert "admin-key" not in serialized_response
    assert "secret-password" not in serialized_response
    assert "minio-secret" not in serialized_response
    assert "llm-secret" not in serialized_response


def test_관리자_운영상태_API는_dependency_failure_event를_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|admin",
    )
    monkeypatch.setenv("DEPENDENCY_HEALTH_CHECKS_ENABLED", "true")
    checker = FakeDependencyHealthChecker(
        [
            DependencyCheckResult(
                name="qdrant",
                status="not_ready",
                message="Qdrant 연결에 실패했습니다.",
            )
        ]
    )
    app = create_app()
    app.state.dependency_health_checker = checker
    client = TestClient(app)

    response = client.get(
        "/v1/admin/operations",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["events"][0]["event_type"] == "dependency.health_failed"
    assert body["events"][0]["severity"] == "error"
    assert body["events"][0]["source"] == "qdrant"
    assert body["events"][0]["message"] == "Qdrant 연결에 실패했습니다."
    assert body["events"][0]["details"] == {"check": "qdrant"}


class FakeDependencyHealthChecker:
    def __init__(self, checks: list[DependencyCheckResult]) -> None:
        self._checks = checks
        self.called = False

    def check(self, settings) -> list[DependencyCheckResult]:
        self.called = True
        return self._checks


class FakeRedisQueue:
    def __init__(self, *, pending_count: int) -> None:
        self._pending_count = pending_count

    def pending_count(self) -> int:
        return self._pending_count
