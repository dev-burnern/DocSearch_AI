from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.documents.models import DocumentRecord
from backend.app.documents.store import InMemoryDocumentMetadataStore
from backend.app.main import create_app


class InMemoryStorage:
    def __init__(self) -> None:
        self.by_key: dict[str, bytes] = {}
        self.deleted_keys: list[str] = []

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
        self.by_key[storage_key] = data
        return storage_key

    def download_document(self, *, storage_key: str) -> bytes:
        return self.by_key[storage_key]

    def delete_document(self, *, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)
        self.by_key.pop(storage_key, None)


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, str]] = []
        self.upserted_document_ids: list[str] = []

    def delete_document(self, *, workspace_id: str, document_id: str) -> None:
        self.deleted.append((workspace_id, document_id))

    def upsert_chunks(self, *, job, parser_name, chunks, embeddings) -> None:
        self.upserted_document_ids.append(job.document_id)


def _record(
    document_id: str = "doc-1",
    *,
    workspace_id: str = "workspace-alpha",
) -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        workspace_id=workspace_id,
        workspace_name="Workspace Alpha",
        filename="memo.txt",
        parser="text",
        character_count=15,
        text_preview="hello docsearch",
        storage_key=f"{workspace_id}/{document_id}/memo.txt",
        indexing_job_id="job-1",
        indexing_status="completed",
        chunk_count=1,
        uploaded_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def storage() -> InMemoryStorage:
    storage = InMemoryStorage()
    storage.by_key["workspace-alpha/doc-1/memo.txt"] = b"hello docsearch"
    return storage


@pytest.fixture
def document_store() -> InMemoryDocumentMetadataStore:
    store = InMemoryDocumentMetadataStore()
    store.record_document(_record())
    store.record_document(_record("doc-beta", workspace_id="workspace-beta"))
    return store


@pytest.fixture
def vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    storage: InMemoryStorage,
    document_store: InMemoryDocumentMetadataStore,
    vector_store: FakeVectorStore,
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

    app = create_app()
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_document_metadata_store] = lambda: document_store
    app.dependency_overrides[get_qdrant_store] = lambda: vector_store

    return TestClient(app)


def test_문서_삭제가_원본_벡터_메타데이터를_정리한다(
    client: TestClient,
    storage: InMemoryStorage,
    document_store: InMemoryDocumentMetadataStore,
    vector_store: FakeVectorStore,
) -> None:
    response = client.delete(
        "/v1/documents/doc-1",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": "doc-1",
        "workspace_id": "workspace-alpha",
        "deleted": True,
    }
    assert storage.deleted_keys == ["workspace-alpha/doc-1/memo.txt"]
    assert vector_store.deleted == [("workspace-alpha", "doc-1")]
    assert document_store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    ) is None


def test_다른_워크스페이스_문서_삭제는_404를_반환한다(
    client: TestClient,
) -> None:
    response = client.delete(
        "/v1/documents/doc-beta",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DOCUMENT_NOT_FOUND"


def test_문서_재인덱싱이_기존_원본으로_새_작업을_실행하고_메타데이터를_갱신한다(
    client: TestClient,
    document_store: InMemoryDocumentMetadataStore,
    vector_store: FakeVectorStore,
) -> None:
    response = client.post(
        "/v1/documents/doc-1/reindex",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == "doc-1"
    assert body["indexing_job_id"] != "job-1"
    assert body["indexing_status"] == "completed"
    assert body["chunk_count"] == 1
    assert body["text_preview"] == "hello docsearch"
    assert vector_store.deleted == [("workspace-alpha", "doc-1")]
    assert vector_store.upserted_document_ids == ["doc-1"]
    stored = document_store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )
    assert stored is not None
    assert stored.indexing_job_id == body["indexing_job_id"]
