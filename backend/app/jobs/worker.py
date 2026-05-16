from dataclasses import replace
import logging

from backend.app.core.operation_events import OperationEvent, OperationEventStore
from backend.app.documents.store import DocumentMetadataStore
from backend.app.indexing.pipeline import IndexingPipeline
from backend.app.jobs.base import IndexDocumentJob, JobStatus
from backend.app.jobs.redis_queue import RedisJobQueue


logger = logging.getLogger("docsearch.worker")


class IndexingJobWorker:
    def __init__(
        self,
        *,
        queue: RedisJobQueue,
        pipeline: IndexingPipeline,
        document_metadata_store: DocumentMetadataStore,
        operation_event_store: OperationEventStore | None = None,
    ) -> None:
        self._queue = queue
        self._pipeline = pipeline
        self._document_metadata_store = document_metadata_store
        self._operation_event_store = operation_event_store

    def process_next(self, *, timeout_seconds: int = 5) -> bool:
        job = self._queue.pop(timeout_seconds=timeout_seconds)
        if job is None:
            return False

        self._update_document_status(job, status="processing")
        try:
            result = self._pipeline.run(job)
        except Exception as exc:
            self._handle_failure(job, exc)
            return True

        self._update_document_status(
            job,
            status="completed",
            indexing_error=None,
            chunk_count=result.chunk_count,
        )
        logger.info(
            "indexing job completed",
            extra={
                "job_id": job.job_id,
                "workspace_id": job.workspace_id,
                "document_id": job.document_id,
            },
        )
        return True

    def _handle_failure(self, job: IndexDocumentJob, exc: Exception) -> None:
        failure_reason = str(exc)
        if job.attempt < job.max_attempts:
            retry_job = replace(job, attempt=job.attempt + 1)
            dispatch = self._queue.enqueue(retry_job)
            if dispatch.status == "queued":
                self._update_document_status(
                    job,
                    status="queued",
                    indexing_error=failure_reason,
                )
                self._record_event(
                    event_type="indexing.retry_scheduled",
                    severity="warning",
                    message=f"Document indexing retry scheduled: {failure_reason}",
                    job=retry_job,
                )
                logger.warning(
                    "indexing job retry scheduled",
                    extra={
                        "job_id": retry_job.job_id,
                        "workspace_id": retry_job.workspace_id,
                        "document_id": retry_job.document_id,
                        "attempt": retry_job.attempt,
                        "max_attempts": retry_job.max_attempts,
                    },
                )
                return

            failure_reason = dispatch.failure_reason or failure_reason

        self._update_document_status(
            job,
            status="failed",
            indexing_error=failure_reason,
            chunk_count=0,
        )
        self._record_event(
            event_type="indexing.failed",
            severity="error",
            message=f"Document indexing failed: {failure_reason}",
            job=job,
        )
        logger.exception(
            "indexing job failed",
            extra={
                "job_id": job.job_id,
                "workspace_id": job.workspace_id,
                "document_id": job.document_id,
                "attempt": job.attempt,
                "max_attempts": job.max_attempts,
            },
        )

    def _update_document_status(
        self,
        job: IndexDocumentJob,
        *,
        status: JobStatus,
        indexing_error: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        record = self._document_metadata_store.get_document(
            workspace_id=job.workspace_id,
            document_id=job.document_id,
        )
        if record is None:
            self._record_event(
                event_type="indexing.metadata_missing",
                severity="warning",
                message="Document metadata was not found for indexing job.",
                job=job,
            )
            logger.warning(
                "document metadata missing for indexing job",
                extra={
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "document_id": job.document_id,
                },
            )
            return

        update: dict[str, object] = {
            "indexing_status": status,
            "indexing_error": indexing_error,
        }
        if chunk_count is not None:
            update["chunk_count"] = chunk_count

        self._document_metadata_store.record_document(record.model_copy(update=update))

    def _record_event(
        self,
        *,
        event_type: str,
        severity: str,
        message: str,
        job: IndexDocumentJob,
    ) -> None:
        if self._operation_event_store is None:
            return

        self._operation_event_store.record(
            OperationEvent(
                event_type=event_type,
                severity=severity,
                source="indexing",
                message=message,
                details={
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "document_id": job.document_id,
                    "filename": job.filename,
                    "attempt": str(job.attempt),
                    "max_attempts": str(job.max_attempts),
                },
            )
        )
