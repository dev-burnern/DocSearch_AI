from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.documents.models import DocumentRecord
from backend.app.documents.store import InMemoryDocumentMetadataStore
from backend.app.main import create_app


def _record(
    document_id: str,
    *,
    workspace_id: str,
    workspace_name: str,
    security_level: str = "internal",
) -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        security_level=security_level,
        filename=f"{document_id}.md",
        parser="markdown",
        character_count=42,
        text_preview="문서 미리보기",
        storage_key=f"{workspace_id}/{document_id}/{document_id}.md",
        indexing_job_id=f"job-{document_id}",
        indexing_status="completed",
        chunk_count=3,
        uploaded_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def document_store() -> InMemoryDocumentMetadataStore:
    store = InMemoryDocumentMetadataStore()
    store.record_document(
        _record(
            "doc-alpha",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            security_level="internal",
        ),
    )
    store.record_document(
        _record(
            "doc-restricted",
            workspace_id="workspace-alpha",
            workspace_name="Workspace Alpha",
            security_level="restricted",
        ),
    )
    store.record_document(
        _record(
            "doc-beta",
            workspace_id="workspace-beta",
            workspace_name="Workspace Beta",
        ),
    )
    return store


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    document_store: InMemoryDocumentMetadataStore,
) -> TestClient:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.documents.router import get_document_metadata_store

    app = create_app()
    app.dependency_overrides[get_document_metadata_store] = lambda: document_store

    return TestClient(app)


def test_문서_목록은_인증된_워크스페이스_문서만_반환한다(client: TestClient) -> None:
    response = client.get(
        "/v1/documents",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["documents"][0]["document_id"] == "doc-alpha"
    assert response.json()["documents"][0]["workspace_id"] == "workspace-alpha"
    assert response.json()["documents"][0]["filename"] == "doc-alpha.md"


def test_관리자는_제한_문서까지_목록에서_확인한다(
    monkeypatch: pytest.MonkeyPatch,
    document_store: InMemoryDocumentMetadataStore,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha|admin",
    )

    from backend.app.documents.router import get_document_metadata_store

    app = create_app()
    app.dependency_overrides[get_document_metadata_store] = lambda: document_store
    client = TestClient(app)

    response = client.get(
        "/v1/documents",
        headers={"X-API-Key": "local-dev-key"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert {document["document_id"] for document in response.json()["documents"]} == {
        "doc-alpha",
        "doc-restricted",
    }
