from datetime import UTC, datetime, timedelta

from backend.app.documents.models import DocumentRecord
from backend.app.documents.store import InMemoryDocumentMetadataStore


def _record(
    document_id: str,
    *,
    workspace_id: str = "workspace-alpha",
    uploaded_at: datetime | None = None,
) -> DocumentRecord:
    return DocumentRecord(
        document_id=document_id,
        workspace_id=workspace_id,
        workspace_name="Workspace Alpha",
        filename=f"{document_id}.txt",
        parser="text",
        character_count=15,
        text_preview="hello docsearch",
        storage_key=f"{workspace_id}/{document_id}/{document_id}.txt",
        indexing_job_id=f"job-{document_id}",
        indexing_status="completed",
        chunk_count=1,
        uploaded_at=uploaded_at or datetime(2026, 5, 15, 9, 0, tzinfo=UTC),
    )


def test_인메모리_문서_저장소는_워크스페이스별_최신순으로_목록을_반환한다() -> None:
    store = InMemoryDocumentMetadataStore()
    base_time = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)

    store.record_document(
        _record("doc-old", uploaded_at=base_time - timedelta(minutes=10)),
    )
    store.record_document(_record("doc-other", workspace_id="workspace-beta"))
    store.record_document(_record("doc-new", uploaded_at=base_time))

    records = store.list_documents(workspace_id="workspace-alpha")

    assert [record.document_id for record in records] == ["doc-new", "doc-old"]


def test_인메모리_문서_저장소는_조회_개수를_제한한다() -> None:
    store = InMemoryDocumentMetadataStore()
    base_time = datetime(2026, 5, 15, 9, 0, tzinfo=UTC)
    store.record_document(_record("doc-1", uploaded_at=base_time))
    store.record_document(_record("doc-2", uploaded_at=base_time + timedelta(minutes=1)))

    records = store.list_documents(workspace_id="workspace-alpha", limit=1)

    assert [record.document_id for record in records] == ["doc-2"]
