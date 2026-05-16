from fastapi.testclient import TestClient
import pytest
from qdrant_client import QdrantClient

from backend.app.core.config import get_settings
from backend.app.documents.store import InMemoryDocumentMetadataStore
from backend.app.jobs.base import JobDispatchResult
from backend.app.main import create_app


class InMemoryStorage:
    def __init__(self) -> None:
        self.saved: list[dict[str, bytes | str]] = []
        self.by_key: dict[str, bytes] = {}

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
        self.by_key[storage_key] = data
        return storage_key

    def download_document(self, *, storage_key: str) -> bytes:
        return self.by_key[storage_key]


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def document_store() -> InMemoryDocumentMetadataStore:
    return InMemoryDocumentMetadataStore()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    storage: InMemoryStorage,
    document_store: InMemoryDocumentMetadataStore,
) -> TestClient:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.documents.router import (
        get_document_metadata_store,
        get_qdrant_store,
        get_storage_service,
    )
    from backend.app.retrieval.qdrant_store import QdrantVectorStore

    app = create_app()
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_document_metadata_store] = lambda: document_store
    app.dependency_overrides[get_qdrant_store] = lambda: QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=8,
    )

    return TestClient(app)


def test_문서_업로드가_저장소에_파일을_저장하고_메타데이터를_반환한다(
    client: TestClient,
    storage: InMemoryStorage,
    document_store: InMemoryDocumentMetadataStore,
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
    assert response.json()["indexing_job_id"]
    assert response.json()["indexing_status"] == "completed"
    assert response.json()["chunk_count"] == 1

    assert len(storage.saved) == 1
    assert storage.saved[0]["filename"] == "memo.txt"
    assert storage.saved[0]["data"] == b"hello docsearch"
    records = document_store.list_documents(workspace_id="workspace-alpha")
    assert len(records) == 1
    assert records[0].document_id == response.json()["document_id"]
    assert records[0].filename == "memo.txt"
    assert records[0].chunk_count == 1


def test_문서_업로드는_인덱싱_실패_상태와_사유를_메타데이터에_저장한다(
    monkeypatch: pytest.MonkeyPatch,
    storage: InMemoryStorage,
    document_store: InMemoryDocumentMetadataStore,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.documents.router import (
        get_document_metadata_store,
        get_job_queue,
        get_qdrant_store,
        get_storage_service,
    )
    from backend.app.retrieval.qdrant_store import QdrantVectorStore

    app = create_app()
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_document_metadata_store] = lambda: document_store
    app.dependency_overrides[get_qdrant_store] = lambda: QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="docsearch_chunks",
        vector_size=8,
    )
    app.dependency_overrides[get_job_queue] = lambda: FailedJobQueue()
    client = TestClient(app)

    response = client.post(
        "/v1/documents",
        headers={"X-API-Key": "local-dev-key"},
        files={"file": ("memo.txt", b"hello docsearch", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["indexing_status"] == "failed"
    assert body["indexing_error"] == "parser failed"
    assert body["chunk_count"] == 0
    records = document_store.list_documents(workspace_id="workspace-alpha")
    assert records[0].indexing_status == "failed"
    assert records[0].indexing_error == "parser failed"


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


class FailedJobQueue:
    def enqueue(self, job) -> JobDispatchResult:
        return JobDispatchResult(
            job_id=job.job_id,
            status="failed",
            chunk_count=0,
            failure_reason="parser failed",
        )
