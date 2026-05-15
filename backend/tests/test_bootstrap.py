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


def test_settings_enable_dependency_health_checks_by_default_in_production(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DOCSEARCH_API_KEYS", "prod-key|workspace-prod|Workspace Prod")

    settings = get_settings()

    assert settings.dependency_health_checks_enabled is True


def test_settings_allow_dependency_health_timeout_override(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DEPENDENCY_HEALTH_TIMEOUT_SECONDS", "3.5")

    settings = get_settings()

    assert settings.dependency_health_timeout_seconds == 3.5


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
