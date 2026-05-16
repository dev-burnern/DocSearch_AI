from datetime import UTC, datetime

from backend.app.core.operation_events import InMemoryOperationEventStore
from backend.app.documents.models import DocumentRecord
from backend.app.documents.store import InMemoryDocumentMetadataStore
from backend.app.indexing.pipeline import IndexingResult
from backend.app.jobs.base import IndexDocumentJob, JobDispatchResult
from backend.app.jobs.worker import IndexingJobWorker


def test_indexing_worker_marks_job_completed() -> None:
    document_store = InMemoryDocumentMetadataStore()
    document_store.record_document(_record(indexing_status="queued"))
    queue = FakeQueue(jobs=[_job()])
    worker = IndexingJobWorker(
        queue=queue,
        pipeline=SuccessfulPipeline(),
        document_metadata_store=document_store,
    )

    processed = worker.process_next(timeout_seconds=1)

    assert processed is True
    record = document_store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )
    assert record is not None
    assert record.indexing_status == "completed"
    assert record.indexing_error is None
    assert record.chunk_count == 2


def test_indexing_worker_reschedules_failed_job_before_max_attempts() -> None:
    document_store = InMemoryDocumentMetadataStore()
    document_store.record_document(_record(indexing_status="processing"))
    event_store = InMemoryOperationEventStore()
    queue = FakeQueue(jobs=[_job(attempt=1, max_attempts=3)])
    worker = IndexingJobWorker(
        queue=queue,
        pipeline=FailingPipeline(),
        document_metadata_store=document_store,
        operation_event_store=event_store,
    )

    processed = worker.process_next(timeout_seconds=1)

    assert processed is True
    assert queue.enqueued == [_job(attempt=2, max_attempts=3)]
    record = document_store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )
    assert record is not None
    assert record.indexing_status == "queued"
    assert record.indexing_error == "parser failed"
    event = event_store.list_events()[0]
    assert event.event_type == "indexing.retry_scheduled"
    assert event.severity == "warning"
    assert event.details["attempt"] == "2"
    assert event.details["max_attempts"] == "3"


def test_indexing_worker_marks_job_failed_after_max_attempts() -> None:
    document_store = InMemoryDocumentMetadataStore()
    document_store.record_document(_record(indexing_status="processing", chunk_count=2))
    event_store = InMemoryOperationEventStore()
    queue = FakeQueue(jobs=[_job(attempt=3, max_attempts=3)])
    worker = IndexingJobWorker(
        queue=queue,
        pipeline=FailingPipeline(),
        document_metadata_store=document_store,
        operation_event_store=event_store,
    )

    processed = worker.process_next(timeout_seconds=1)

    assert processed is True
    assert queue.enqueued == []
    record = document_store.get_document(
        workspace_id="workspace-alpha",
        document_id="doc-1",
    )
    assert record is not None
    assert record.indexing_status == "failed"
    assert record.indexing_error == "parser failed"
    assert record.chunk_count == 0
    event = event_store.list_events()[0]
    assert event.event_type == "indexing.failed"
    assert event.severity == "error"
    assert event.details["attempt"] == "3"
    assert event.details["max_attempts"] == "3"


def _job(*, attempt: int = 1, max_attempts: int = 3) -> IndexDocumentJob:
    return IndexDocumentJob(
        job_id="job-1",
        workspace_id="workspace-alpha",
        workspace_name="Workspace Alpha",
        document_id="doc-1",
        filename="memo.txt",
        content_type="text/plain",
        storage_key="workspace-alpha/doc-1/memo.txt",
        attempt=attempt,
        max_attempts=max_attempts,
    )


def _record(
    *,
    indexing_status: str,
    chunk_count: int = 0,
) -> DocumentRecord:
    return DocumentRecord(
        document_id="doc-1",
        workspace_id="workspace-alpha",
        workspace_name="Workspace Alpha",
        filename="memo.txt",
        parser="text",
        character_count=15,
        text_preview="hello docsearch",
        storage_key="workspace-alpha/doc-1/memo.txt",
        indexing_job_id="job-1",
        indexing_status=indexing_status,
        indexing_error=None,
        chunk_count=chunk_count,
        uploaded_at=datetime(2026, 5, 16, 9, 0, tzinfo=UTC),
    )


class FakeQueue:
    def __init__(self, *, jobs: list[IndexDocumentJob]) -> None:
        self._jobs = jobs
        self.enqueued: list[IndexDocumentJob] = []

    def pop(self, *, timeout_seconds: int) -> IndexDocumentJob | None:
        return self._jobs.pop(0) if self._jobs else None

    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        self.enqueued.append(job)
        return JobDispatchResult(job_id=job.job_id, status="queued")


class SuccessfulPipeline:
    def run(self, job: IndexDocumentJob) -> IndexingResult:
        return IndexingResult(
            job_id=job.job_id,
            document_id=job.document_id,
            parser="text",
            chunk_count=2,
            chunks=["hello", "docsearch"],
            embeddings=[[0.1], [0.2]],
            embedding_count=2,
            embedding_dimensions=1,
        )


class FailingPipeline:
    def run(self, job: IndexDocumentJob) -> IndexingResult:
        raise RuntimeError("parser failed")
