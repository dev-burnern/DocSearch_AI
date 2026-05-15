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
    assert body["settings"]["environment"] == "development"
    assert body["settings"]["dependency_health_checks_enabled"] is True
    assert body["settings"]["rate_limit"] == {
        "enabled": True,
        "requests": 30,
        "window_seconds": 10,
    }
    assert body["settings"]["backends"] == {
        "audit_log": "inmemory",
        "document_metadata": "inmemory",
        "indexing_queue": "inprocess",
        "reranker": "score",
    }
    assert body["settings"]["models"]["llm"] == "google/gemma-4-E4B-it"
    assert checker.called is True


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


class FakeDependencyHealthChecker:
    def __init__(self, checks: list[DependencyCheckResult]) -> None:
        self._checks = checks
        self.called = False

    def check(self, settings) -> list[DependencyCheckResult]:
        self.called = True
        return self._checks
