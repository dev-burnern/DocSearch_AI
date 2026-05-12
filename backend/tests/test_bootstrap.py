from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import create_app


def test_settings_load_default_values():
    settings = get_settings()

    assert settings.app_name == "DocSearch AI V2"
    assert settings.app_env == "development"


def test_health_route_returns_expected_contract():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "docsearch-ai-v2",
    }
