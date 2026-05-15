from datetime import UTC, datetime

from backend.app.documents.models import DocumentRecord
from backend.app.documents.postgres_store import PostgresDocumentMetadataStore


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, dict[str, object] | None]] = []
        self.commit_count = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def execute(
        self,
        sql: str,
        params: dict[str, object] | None = None,
    ) -> FakeCursor:
        self.statements.append((sql, params))
        return FakeCursor(self.rows)

    def commit(self) -> None:
        self.commit_count += 1


def _record() -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        workspace_id="workspace-alpha",
        workspace_name="Workspace Alpha",
        filename="policy.md",
        parser="markdown",
        character_count=42,
        text_preview="문서 미리보기",
        storage_key="workspace-alpha/doc-1/policy.md",
        indexing_job_id="job-1",
        indexing_status="completed",
        chunk_count=3,
        uploaded_at=datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )


def test_PostgresDocumentMetadataStore는_스키마를_보장하고_문서를_저장한다() -> None:
    connection = FakeConnection()
    store = PostgresDocumentMetadataStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    store.record_document(_record())

    assert "CREATE TABLE IF NOT EXISTS document_metadata" in connection.statements[0][0]
    insert_sql, insert_params = connection.statements[2]
    assert "INSERT INTO document_metadata" in insert_sql
    assert insert_params is not None
    assert insert_params["document_id"] == "doc-1"
    assert insert_params["workspace_id"] == "workspace-alpha"
    assert insert_params["uploaded_at"] == datetime(2026, 5, 15, 9, 0, tzinfo=UTC)
    assert connection.commit_count == 2


def test_PostgresDocumentMetadataStore는_워크스페이스_문서를_최신순으로_반환한다() -> None:
    record = _record()
    connection = FakeConnection(rows=[record.model_dump(mode="python")])
    store = PostgresDocumentMetadataStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    records = store.list_documents(workspace_id="workspace-alpha", limit=20)

    assert records == [record]
    select_sql, select_params = connection.statements[-1]
    assert "WHERE workspace_id = %(workspace_id)s" in select_sql
    assert "ORDER BY uploaded_at DESC" in select_sql
    assert select_params == {"workspace_id": "workspace-alpha", "limit": 20}


def test_PostgresDocumentMetadataStore는_문서를_조회한다() -> None:
    record = _record()
    connection = FakeConnection(rows=[record.model_dump(mode="python")])
    store = PostgresDocumentMetadataStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    found = store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )

    assert found == record
    select_sql, select_params = connection.statements[-1]
    assert "WHERE workspace_id = %(workspace_id)s" in select_sql
    assert "AND document_id = %(document_id)s" in select_sql
    assert select_params == {
        "workspace_id": "workspace-alpha",
        "document_id": "doc-1",
    }


def test_PostgresDocumentMetadataStore는_문서를_삭제하고_삭제된_레코드를_반환한다() -> None:
    record = _record()
    connection = FakeConnection(rows=[record.model_dump(mode="python")])
    store = PostgresDocumentMetadataStore(
        database_url="postgresql://docsearch:docsearch@postgres:5432/docsearch",
        connection_factory=lambda: connection,
    )

    deleted = store.delete_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )

    assert deleted == record
    delete_sql, delete_params = connection.statements[-1]
    assert "DELETE FROM document_metadata" in delete_sql
    assert "RETURNING" in delete_sql
    assert delete_params == {
        "workspace_id": "workspace-alpha",
        "document_id": "doc-1",
    }
    assert connection.commit_count == 2
