from backend.app.core.config import Settings
from backend.app.documents.router import create_document_metadata_store
from backend.app.documents.store import InMemoryDocumentMetadataStore


class FakeConnection:
    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(self, sql: str, params=None):
        return self

    def commit(self) -> None:
        return None


def test_문서_메타데이터_저장소_factory는_inmemory_기본값을_사용한다() -> None:
    store = create_document_metadata_store(Settings())

    assert isinstance(store, InMemoryDocumentMetadataStore)


def test_문서_메타데이터_저장소_factory는_postgres_설정을_반영한다() -> None:
    store = create_document_metadata_store(
        Settings(
            document_metadata_backend="postgres",
            database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        ),
        connection_factory=lambda: FakeConnection(),
    )

    assert store.__class__.__name__ == "PostgresDocumentMetadataStore"
