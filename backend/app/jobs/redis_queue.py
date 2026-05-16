import json
from dataclasses import asdict, replace

from redis.exceptions import TimeoutError as RedisTimeoutError

from backend.app.core.config import Settings
from backend.app.core.operation_events import OperationEvent, OperationEventStore
from backend.app.jobs.base import IndexDocumentJob, JobDispatchResult


class RedisJobQueue:
    def __init__(
        self,
        *,
        redis_client,
        queue_key: str,
        max_attempts: int = 3,
        operation_event_store: OperationEventStore | None = None,
    ) -> None:
        self._redis_client = redis_client
        self._queue_key = queue_key
        self._max_attempts = max_attempts
        self._operation_event_store = operation_event_store

    def enqueue(self, job: IndexDocumentJob) -> JobDispatchResult:
        job = replace(job, max_attempts=self._max_attempts)
        try:
            self._redis_client.rpush(self._queue_key, self.serialize(job))
        except Exception as exc:
            self._record_enqueue_failure_event(job, exc)
            return JobDispatchResult(
                job_id=job.job_id,
                status="failed",
                chunk_count=0,
                failure_reason=str(exc),
            )

        return JobDispatchResult(
            job_id=job.job_id,
            status="queued",
            chunk_count=0,
        )

    def pop(self, *, timeout_seconds: int = 5) -> IndexDocumentJob | None:
        try:
            result = self._redis_client.brpop(
                self._queue_key,
                timeout=timeout_seconds,
            )
        except RedisTimeoutError:
            return None
        if result is None:
            return None

        _, payload = result
        return self.deserialize(payload)

    def pending_count(self) -> int:
        return int(self._redis_client.llen(self._queue_key))

    @staticmethod
    def serialize(job: IndexDocumentJob) -> str:
        return json.dumps(asdict(job))

    @staticmethod
    def deserialize(payload: str | bytes) -> IndexDocumentJob:
        if isinstance(payload, bytes):
            payload = payload.decode()
        return IndexDocumentJob(**json.loads(payload))

    def _record_enqueue_failure_event(
        self,
        job: IndexDocumentJob,
        exc: Exception,
    ) -> None:
        if self._operation_event_store is None:
            return

        self._operation_event_store.record(
            OperationEvent(
                event_type="indexing.queue_unavailable",
                severity="error",
                source="indexing",
                message=f"Indexing queue is unavailable: {exc}",
                details={
                    "job_id": job.job_id,
                    "workspace_id": job.workspace_id,
                    "document_id": job.document_id,
                    "filename": job.filename,
                },
            )
        )


def create_redis_job_queue(
    settings: Settings,
    *,
    operation_event_store: OperationEventStore | None = None,
) -> RedisJobQueue:
    from redis import Redis

    return RedisJobQueue(
        redis_client=Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        ),
        queue_key=settings.indexing_queue_redis_key,
        max_attempts=settings.indexing_queue_max_attempts,
        operation_event_store=operation_event_store,
    )
