from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.main import create_app


class InMemoryStorage:
    def __init__(self) -> None:
        self.saved: list[dict[str, bytes | str]] = []

    def upload_document(
        self,
        *,
        workspace_id: str,
        document_id: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> str:
        storage_key = f"{workspace_id}/{document_id}/{filename}"
        self.saved.append(
            {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "filename": filename,
                "content_type": content_type,
                "data": data,
                "storage_key": storage_key,
            },
        )
        return storage_key


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, storage: InMemoryStorage) -> TestClient:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.documents.router import get_storage_service

    app = create_app()
    app.dependency_overrides[get_storage_service] = lambda: storage

    return TestClient(app)


def test_문서_업로드가_저장소에_파일을_저장하고_메타데이터를_반환한다(
    client: TestClient,
    storage: InMemoryStorage,
) -> None:
    response = client.post(
        "/v1/documents",
        headers={"X-API-Key": "local-dev-key"},
        files={"file": ("memo.txt", b"hello docsearch", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["workspace_id"] == "workspace-alpha"
    assert response.json()["workspace_name"] == "Workspace Alpha"
    assert response.json()["filename"] == "memo.txt"
    assert response.json()["parser"] == "text"
    assert response.json()["character_count"] == len("hello docsearch")
    assert response.json()["text_preview"] == "hello docsearch"
    assert response.json()["storage_key"].startswith("workspace-alpha/")

    assert len(storage.saved) == 1
    assert storage.saved[0]["filename"] == "memo.txt"
    assert storage.saved[0]["data"] == b"hello docsearch"


def test_지원하지_않는_확장자는_거부한다(client: TestClient) -> None:
    response = client.post(
        "/v1/documents",
        headers={"X-API-Key": "local-dev-key"},
        files={"file": ("table.csv", b"a,b,c", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": {
            "code": "DOCUMENT_UNSUPPORTED_TYPE",
            "message": "Unsupported document type: .csv",
        }
    }
