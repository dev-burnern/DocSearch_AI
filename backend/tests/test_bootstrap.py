from fastapi.testclient import TestClient
import pytest

from backend.app.core.dependency_health import DependencyCheckResult
from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_load_default_values():
    settings = get_settings()

    assert settings.app_name == "DocSearch AI"
    assert settings.app_env == "development"
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.dependency_health_checks_enabled is False
    assert settings.dependency_health_timeout_seconds == 2.0
    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_backend == "memory"
    assert settings.rate_limit_requests == 120
    assert settings.rate_limit_window_seconds == 60
    assert settings.rate_limit_redis_prefix == "docsearch:rate-limit"
    assert settings.rate_limit_fail_open is True
    assert settings.indexing_queue_redis_key == "docsearch:indexing:queue"
    assert settings.indexing_queue_max_attempts == 3
    assert settings.document_max_bytes == 10485760
    assert settings.chat_min_relevance_score == 0.2
    assert settings.llm_max_retries == 2
    assert settings.llm_retry_backoff_seconds == 0.5
    assert settings.embedding_backend == "deterministic"
    assert settings.embedding_base_url == "http://embedding:8002/v1"
    assert settings.embedding_model == "BAAI/bge-m3"
    assert settings.embedding_api_key is None
    assert settings.embedding_timeout_seconds == 10.0


def test_settings_enable_dependency_health_checks_by_default_in_production(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DOCSEARCH_API_KEYS", "prod-key|workspace-prod|Workspace Prod")

    settings = get_settings()

    assert settings.dependency_health_checks_enabled is True
    assert settings.rate_limit_enabled is True


def test_settings_allow_rate_limit_overrides(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "30")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "10")
    monkeypatch.setenv("RATE_LIMIT_REDIS_PREFIX", "test:rate-limit")
    monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "false")

    settings = get_settings()

    assert settings.rate_limit_enabled is True
    assert settings.rate_limit_backend == "redis"
    assert settings.rate_limit_requests == 30
    assert settings.rate_limit_window_seconds == 10
    assert settings.rate_limit_redis_prefix == "test:rate-limit"
    assert settings.rate_limit_fail_open is False


def test_settings_allow_indexing_queue_overrides(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("INDEXING_QUEUE_BACKEND", "redis")
    monkeypatch.setenv("INDEXING_QUEUE_REDIS_KEY", "test:indexing:queue")
    monkeypatch.setenv("INDEXING_QUEUE_MAX_ATTEMPTS", "5")

    settings = get_settings()

    assert settings.indexing_queue_backend == "redis"
    assert settings.indexing_queue_redis_key == "test:indexing:queue"
    assert settings.indexing_queue_max_attempts == 5


def test_settings_allow_dependency_health_timeout_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DEPENDENCY_HEALTH_TIMEOUT_SECONDS", "3.5")

    settings = get_settings()

    assert settings.dependency_health_timeout_seconds == 3.5


def test_settings_allow_document_size_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DOCUMENT_MAX_BYTES", "4096")

    settings = get_settings()

    assert settings.document_max_bytes == 4096


def test_settings_allow_chat_relevance_threshold_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CHAT_MIN_RELEVANCE_SCORE", "0.45")

    settings = get_settings()

    assert settings.chat_min_relevance_score == 0.45


def test_settings_allow_llm_retry_policy_overrides(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "0.25")

    settings = get_settings()

    assert settings.llm_max_retries == 4
    assert settings.llm_retry_backoff_seconds == 0.25


def test_settings_allow_embedding_backend_overrides(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("EMBEDDING_BACKEND", "bge")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://localhost:8002/v1/")
    monkeypatch.setenv("EMBEDDING_MODEL", "custom/embedding")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-secret")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("EMBEDDING_VECTOR_SIZE", "1024")

    settings = get_settings()

    assert settings.embedding_backend == "bge"
    assert settings.embedding_base_url == "http://localhost:8002/v1/"
    assert settings.embedding_model == "custom/embedding"
    assert settings.embedding_api_key == "embedding-secret"
    assert settings.embedding_timeout_seconds == 2.5
    assert settings.embedding_vector_size == 1024


def test_health_route_returns_expected_contract():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "docsearch-ai",
    }


def test_health_route_includes_operational_security_headers():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.headers["X-Request-Id"].startswith("req_")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert (
        response.headers["Permissions-Policy"]
        == "camera=(), microphone=(), geolocation=()"
    )


def test_ready_route_returns_operational_checks():
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "docsearch-ai",
        "checks": [
            {
                "name": "configuration",
                "status": "ready",
                "message": "운영 설정 기준을 통과했습니다.",
            }
        ],
    }


def test_ready_route_includes_dependency_checks_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DEPENDENCY_HEALTH_CHECKS_ENABLED", "true")
    checker = FakeDependencyHealthChecker(
        [
            DependencyCheckResult(
                name="qdrant",
                status="ready",
                message="Qdrant 연결을 확인했습니다.",
            )
        ]
    )
    app = create_app()
    app.state.dependency_health_checker = checker
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"] == [
        {
            "name": "configuration",
            "status": "ready",
            "message": "운영 설정 기준을 통과했습니다.",
        },
        {
            "name": "qdrant",
            "status": "ready",
            "message": "Qdrant 연결을 확인했습니다.",
        },
    ]
    assert checker.called is True


def test_ready_route_returns_503_when_dependency_check_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DEPENDENCY_HEALTH_CHECKS_ENABLED", "true")
    checker = FakeDependencyHealthChecker(
        [
            DependencyCheckResult(
                name="qdrant",
                status="not_ready",
                message="Qdrant 연결에 실패했습니다: connection refused",
            )
        ]
    )
    app = create_app()
    app.state.dependency_health_checker = checker
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"][1] == {
        "name": "qdrant",
        "status": "not_ready",
        "message": "Qdrant 연결에 실패했습니다: connection refused",
    }


def test_ready_route_rejects_production_with_default_api_key(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")

    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == [
        {
            "name": "api_keys",
            "status": "not_ready",
            "message": "운영 환경에서는 개발 기본 API Key를 교체해야 합니다.",
        }
    ]


def test_ready_route_skips_dependency_checks_when_configuration_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEPENDENCY_HEALTH_CHECKS_ENABLED", "true")
    app = create_app()
    app.state.dependency_health_checker = FailingDependencyHealthChecker()
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == [
        {
            "name": "api_keys",
            "status": "not_ready",
            "message": "운영 환경에서는 개발 기본 API Key를 교체해야 합니다.",
        }
    ]


def test_ready_route_rejects_production_with_default_api_key_role_variant(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|local-workspace|Local Workspace|admin",
    )

    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == [
        {
            "name": "api_keys",
            "status": "not_ready",
            "message": "운영 환경에서는 개발 기본 API Key를 교체해야 합니다.",
        }
    ]


class FakeDependencyHealthChecker:
    def __init__(self, checks: list[DependencyCheckResult]) -> None:
        self._checks = checks
        self.called = False

    def check(self, settings) -> list[DependencyCheckResult]:
        self.called = True
        return self._checks


class FailingDependencyHealthChecker:
    def check(self, settings) -> list[DependencyCheckResult]:
        raise AssertionError("의존성 점검기가 호출되면 안 됩니다.")


def test_ready_route_rejects_production_debug_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "prod-key|workspace-prod|Workspace Prod",
    )
    monkeypatch.setenv("DEBUG", "true")

    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == [
        {
            "name": "debug",
            "status": "not_ready",
            "message": "운영 환경에서는 DEBUG를 비활성화해야 합니다.",
        }
    ]
