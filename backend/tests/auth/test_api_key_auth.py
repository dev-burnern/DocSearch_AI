from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_workspace_route_requires_api_key() -> None:
    client = TestClient(create_app())

    response = client.get("/v1/workspace")

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "AUTH_MISSING_API_KEY",
            "message": "API key is required.",
        }
    }


def test_workspace_route_rejects_invalid_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    client = TestClient(create_app())

    response = client.get("/v1/workspace", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "AUTH_INVALID_API_KEY",
            "message": "API key is invalid.",
        }
    }


def test_workspace_route_returns_request_context_for_valid_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    client = TestClient(create_app())

    response = client.get("/v1/workspace", headers={"X-API-Key": "local-dev-key"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == response.json()["request_id"]
    assert response.json()["workspace_id"] == "workspace-alpha"
    assert response.json()["workspace_name"] == "Workspace Alpha"
    assert response.json()["role"] == "member"


def test_workspace_route_returns_admin_role_for_four_part_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|admin",
    )

    client = TestClient(create_app())

    response = client.get("/v1/workspace", headers={"X-API-Key": "admin-key"})

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "workspace-alpha"
    assert response.json()["workspace_name"] == "Workspace Alpha"
    assert response.json()["role"] == "admin"


def test_workspace_route_rejects_unknown_api_key_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "admin-key|workspace-alpha|Workspace Alpha|owner",
    )
    client = TestClient(create_app())

    with pytest.raises(ValueError, match="role"):
        client.get("/v1/workspace", headers={"X-API-Key": "admin-key"})
