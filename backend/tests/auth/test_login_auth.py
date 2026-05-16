from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_login_returns_token_and_workspace_context() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/auth/login",
        json={"employee_id": "2301029", "password": "password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["workspace"]["employee_id"] == "2301029"
    assert body["workspace"]["role"] == "admin"

    me = client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me.status_code == 200
    assert me.json()["employee_id"] == "2301029"
    assert me.json()["role"] == "admin"


def test_signup_registers_member_user_and_rejects_duplicates() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/auth/signup",
        json={
            "employee_id": "2001",
            "password": "pass1234",
            "display_name": "Portfolio User",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["workspace"]["employee_id"] == "2001"
    assert body["workspace"]["display_name"] == "Portfolio User"
    assert body["workspace"]["role"] == "member"

    duplicate = client.post(
        "/v1/auth/signup",
        json={"employee_id": "2001", "password": "pass1234"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "AUTH_DUPLICATE_EMPLOYEE_ID"


def test_login_rejects_wrong_password() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/auth/login",
        json={"employee_id": "1001", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID_CREDENTIALS"
