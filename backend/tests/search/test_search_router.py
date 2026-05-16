from fastapi.testclient import TestClient
import pytest

from backend.app.core.config import get_settings
from backend.app.indexing.embedder import EmbeddingProviderError
from backend.app.main import create_app
from backend.app.retrieval.qdrant_store import RetrievedChunk


class FakeRetriever:
    def __init__(self) -> None:
        self.query_text: str | None = None
        self.workspace_id: str | None = None
        self.document_ids: list[str] | None = None
        self.limit: int | None = None

    def retrieve(self, *, query_text, filters, limit):
        self.query_text = query_text
        self.workspace_id = filters.workspace_id
        self.document_ids = filters.document_ids
        self.limit = limit
        return [
            RetrievedChunk(
                workspace_id=filters.workspace_id,
                document_id="doc-1",
                filename="policy.md",
                parser="markdown",
                chunk_index=2,
                chunk_text="권한 정책 문서 일부",
                score=0.87,
            )
        ]


class FailingRetriever:
    def retrieve(self, *, query_text, filters, limit):
        raise EmbeddingProviderError("embedding unavailable")


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_검색_API가_워크스페이스_필터로_청크를_반환한다(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.search.router import get_search_retriever

    fake_retriever = FakeRetriever()
    app = create_app()
    app.dependency_overrides[get_search_retriever] = lambda: fake_retriever
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        headers={"X-API-Key": "local-dev-key"},
        json={
            "query": "권한 정책",
            "document_ids": ["doc-1"],
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert fake_retriever.query_text == "권한 정책"
    assert fake_retriever.workspace_id == "workspace-alpha"
    assert fake_retriever.document_ids == ["doc-1"]
    assert fake_retriever.limit == 5
    assert response.json() == {
        "query": "권한 정책",
        "total": 1,
        "results": [
            {
                "document_id": "doc-1",
                "filename": "policy.md",
                "parser": "markdown",
                "chunk_index": 2,
                "score": 0.87,
                "snippet": "권한 정책 문서 일부",
            }
        ],
    }


def test_검색_API는_API_Key가_없으면_거부한다() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        json={"query": "권한 정책"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_MISSING_API_KEY"


def test_search_api_returns_502_when_embedding_backend_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DOCSEARCH_API_KEYS",
        "local-dev-key|workspace-alpha|Workspace Alpha",
    )

    from backend.app.search.router import get_search_retriever

    app = create_app()
    app.dependency_overrides[get_search_retriever] = lambda: FailingRetriever()
    client = TestClient(app)

    response = client.post(
        "/v1/search",
        headers={"X-API-Key": "local-dev-key"},
        json={"query": "question"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "code": "SEARCH_EMBEDDING_UNAVAILABLE",
        "message": "embedding unavailable",
    }
