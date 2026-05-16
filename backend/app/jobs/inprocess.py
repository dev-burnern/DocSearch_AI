from collections.abc import Callable

from backend.app.core.operation_events import OperationEvent, OperationEventStore
from backend.app.indexing.pipeline import IndexingResult
from backend.app.jobs.base import IndexDocumentJob, JobDispatchResult


class InProcessJobQueue:
    def __init__(
        self,
        *,
        processor: Callable[[IndexDocumentJob], IndexingResult],
        operation_event_store: OperationEventStore | None = None,
    ) -> None:
        self._processor = processor
        self._operation_event_store = operation_event_store

    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        try:
            result = self._processor(job)
        except Exception as exc:
            self._record_failure_event(job, exc)
            return JobDispatchResult(
                job_id=job.job_id,
                status="failed",
                chunk_count=0,
                failure_reason=str(exc),
            )

        return JobDispatchResult(
            job_id=job.job_id,
            status="completed",
            chunk_count=result.chunk_count,
        )

    def _record_failure_event(
        self,
        job: IndexDocumentJob,
        exc: Exception,
    ) -> None:
        if self._operation_event_store is None:
            return

        self._operation_event_store.record(
            OperationEvent(
                event_type="indexing.failed",
                severity="error",
                source="indexing",
                message=f"Document indexing failed: {exc}",
                details={
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "document_id": job.document_id,
                    "filename": job.filename,
                },
            )
        )
